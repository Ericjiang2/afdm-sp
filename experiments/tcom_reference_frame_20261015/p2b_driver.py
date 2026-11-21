#!/usr/bin/env python
"""P2b driver: SP (F0, B, A3 at rho {.3, .5}) versus the embedded-pilot baseline (EP, EP-genie) in scenario S
(protocol.md section 5 + implementation note I2, task 10-15-tcom-reference-frame).

Scenario S = gen_fixed flags D1 + D2 + geometric Doppler + fix_energy + delay_scale 25/102 + truncation at l = 25 (redraw).
One JSONL row per (SNR, frame).  Channel (l, k, g) and noise come from the same stream coordinates for every arm, so SP and EP
see the identical channel realisation and the identical noise vector; the information bits differ (1024 for SP, k = 767 for EP).
Streams: numpy.SeedSequence(8 uint32 words of the entropy, domain, frame, component).  Entropy sets:
  test  ENTROPY_TEST / DOMAIN_TEST  (frames 0..1999 of the P2b test run, never touched before that run)
  dev   ENTROPY_DEV  / DOMAIN_DEV   (rho_EP tuning on 500 frames at 6.0 dB; also every gate and the timing probe)
Report-only arm SPG (SP-genie-LMMSE, protocol I3) calibrates the LMMSE turbo detector against A3 and against EP-genie.
rho_EP (pilot energy fraction of the EP frame) is chosen on the dev frames only and frozen below as RHO_EP.

Run one process per shard, single thread (launch_p2b.sh).  Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ep_rx as E  # noqa: E402
import gen_fixed  # noqa: E402
import p1_driver as P  # noqa: E402
from gen_fixed import Flags  # noqa: E402

# --- frozen constants (protocol.md section 5, implementation note I2) ------------------------------------------
ENTROPY_TEST = 'e0f4a8f31b265a62e0a9f1ab4076a4a189f046acecec5d4c920b0a5cf64bee80'  # os.urandom(32).hex(), 2026-10-15, before any P2b data
DOMAIN_TEST = 0x54435032   # "TCP2"
ENTROPY_DEV = 'ca68a12bfdb5c0a5e797efb26e6c71c4c4f30cc46113c33e8b8c962da6a789b8'   # separate dev entropy (tuning, gates, timing)
DOMAIN_DEV = 0x54434450    # "TCDP"; both domains are distinct from HRLD, CLUS, CSTA, GEOM, TCRF and every [20260920, ...] stream
SETS = {'test': (ENTROPY_TEST, DOMAIN_TEST), 'dev': (ENTROPY_DEV, DOMAIN_DEV)}
RHO_EP_GRID = (0.05, 0.10, 0.20, 0.30)
# Dev tuning (dev entropy, 500 frames, 6.0 dB, scenario S, EP only; out/p2b_dev/dev_result.json): mean goodput (info bits per frame) / frame errors
#   rho_EP .05: 693.37 (48 errors)   .10: 765.47 (1)   .20: 767.00 (0)   .30: 767.00 (0)  -> .20 and .30 tie at k = 767, the smaller value is frozen.
RHO_EP = 0.20
FLAGS_S = Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='geometric', fix_energy=True,
                delay_scale=25. / 102., l_trunc=25)
SP_RHOS = (0.3, 0.5)
SP_ARMS = ('F0', 'B', 'A3')
EP_ARMS = ('EP', 'EPG')
SPG_ARM = 'SPG'   # report-only calibration arm (protocol I3): SP frame, true H, the EP LMMSE-turbo detector, n = 2048 code
DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
CODE_CACHE = HERE / 'out' / 'ep_code'
RECEIVER_CONFIG = dict(
    SP='p1_driver.compute_arms F0 / B / A3 on scenario-S frames, frozen receivers unchanged (their banks still span delays 0..102)',
    EP='ep_rx.estimate_paths (successive window-energy detection P_FA 1e-3, 0.05-bin Doppler grid + polish, joint LS) + ep_rx.detect '
       '(soft-input LMMSE turbo, 2 rounds, LDPC BP 50) on the pilot-cancelled data positions',
    EPG='ep_rx.detect with the true (l, k, g)',
    SPG='report-only calibration (protocol I3): SP frame at the cell rho, true H, pilot cancelled with H, ep_rx.lmmse_turbo (2 rounds, BP 50) '
        'on all 1024 data symbols with the n = 2048 code; seconds exclude the per-frame Gram H^H H (shared cost)',
    goodput='info_bits x (1 - FER) per frame; SP 1024 bits, EP k = 767 bits (actual k of the n = 1530 code)')


def arm_key(arm, rho=None, rho_ep=None):
    if arm in SP_ARMS or arm == SPG_ARM:
        return f'{arm}_r{int(round(rho * 1000))}'
    return arm if rho_ep is None else f'{arm}_p{int(round(rho_ep * 1000)):03d}'


def build_ep(ctx):
    CODE_CACHE.mkdir(parents=True, exist_ok=True)
    return E.EP(ctx.system, E.build_ep_code(CODE_CACHE))


def ep_record(res, truth_l, truth_k, k):
    rec = dict(status='ok', fer=int(res['info_errors'] > 0), info_errors=int(res['info_errors']), info_bits=int(k),
               seconds=float(res['seconds']), decode_ok=bool(res['ok']), iterations=[int(x) for x in res['iterations']])
    if 'est' in res:
        est = res['est']
        rec.update(estimate_seconds=float(res['estimate_seconds']), n_paths_est=int(est['n_paths']), n_paths_true=int(len(truth_l)),
                   **E.path_match(est, truth_l, truth_k))
    return rec


def spg_record(res, info, seconds):
    errors = int(np.count_nonzero(res['info_hat'] != info))
    return dict(status='ok', fer=int(errors > 0), info_errors=errors, info_bits=1024, seconds=float(seconds),
                decode_ok=bool(res['ok']), iterations=[int(x) for x in res['iterations']])


def sp_record(rec):
    out = dict(rec)
    out['info_bits'] = 1024
    return out


def frame_cells(ctx, ep, frame, snr_centis, sp_rhos, arms, rho_ep_list, seed_fn):
    """All cells of one frame: dict(cells={snr_centi: {arm: record}}, truth=truth fields, shared_seconds, snr_seconds={snr: wall});
    channel and noise are shared by every arm.  shared_seconds = SP bases + true operator + genie Gram (once per frame)."""
    t_shared = time.perf_counter()
    want_sp = [a for a in SP_ARMS if a in arms]
    want_spg = SPG_ARM in arms
    bases = {}
    for rho in (sp_rhos if (want_sp or want_spg) else sp_rhos[:1]):
        bases[rho] = P.generate(ctx, FLAGS_S, rho, snr_centis[0] / 100, frame, seed_fn)
    first = next(iter(bases.values()))
    raw0 = first[0]
    for raw, _ in bases.values():  # the SP bases at different rho share one channel realisation
        for key in ('l_i', 'k_real', 'g_i'):
            assert np.array_equal(raw['params'][key], raw0['params'][key]), 'channel differs across rho'
        assert np.array_equal(raw['noise'], raw0['noise']), 'noise differs across rho'
    params, noise = raw0['params'], raw0['noise']
    want_ep = [a for a in EP_ARMS if a in arms]
    out = {}
    ep_state = None
    if want_ep:
        rf = gen_fixed.make_rng_factory(seed_fn, frame)
        info = rf(0, frame, 2, split=2).integers(0, 2, size=ep.k).astype(np.uint8)
        H_true = E.channel_matrix(ep, params['l_i'], params['k_real'], params['g_i'])
        genie_gram = E.gram(ep, H_true)
        frames_x = {r: E.make_frame(ep, info, r)[0] for r in rho_ep_list}
        ep_state = (info, H_true, genie_gram, frames_x)
    spg_gram, spg_gram_seconds = None, 0.
    if want_spg:  # the true operator is the same at every rho and SNR: one Gram per frame (counted in the shared cost, like EP-genie)
        t_gram = time.perf_counter()
        H_sp = raw0['H']
        spg_gram = (H_sp, H_sp.conj().T @ H_sp)
        spg_gram_seconds = time.perf_counter() - t_gram
    shared_seconds = time.perf_counter() - t_shared
    snr_seconds = {}
    for snr in snr_centis:
        t_snr = time.perf_counter()
        recs = {}
        sigma2 = 10 ** (-snr / 100 / 10)
        for rho, (raw_base, diag_base) in bases.items():
            if not (want_sp or want_spg):
                break
            raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr / 100)
            if want_sp:
                obs = ctx.hd.observe(raw, rho, snr / 100)
                truth = ctx.hd.truth_from_raw(raw, diag)
                for arm, rec in P.compute_arms(ctx, obs, truth, want_sp).items():
                    recs[arm_key(arm, rho)] = sp_record(rec) if rec.get('status') == 'ok' else rec
            if want_spg:
                t_spg = time.perf_counter()
                try:
                    res = E.detect_sp(ctx.code, raw['H'], raw['y'], raw['pilot'], float(raw['sigma2']), rho, hd_gram=spg_gram)
                    recs[arm_key(SPG_ARM, rho)] = spg_record(res, raw['info'], time.perf_counter() - t_spg)
                except Exception as error:  # recorded, never silently dropped
                    recs[arm_key(SPG_ARM, rho)] = P._err(error)
        if want_ep:
            info, H_true, genie_gram, frames_x = ep_state
            for r in rho_ep_list:
                y = E.observe(ep, H_true, frames_x[r], noise, sigma2)
                res = E.run_ep(ep, y, sigma2, r, info, H_true=H_true, genie_gram=genie_gram,
                               arms=tuple(a for a in EP_ARMS if a in arms))
                for arm, rr in res.items():
                    recs[arm_key(arm, rho_ep=(r if len(rho_ep_list) > 1 else None))] = ep_record(
                        rr, params['l_i'], params['k_real'], ep.k)
        out[snr] = recs
        snr_seconds[snr] = time.perf_counter() - t_snr
    raw_t, diag_t = first
    truth0 = ctx.hd.truth_from_raw(*ctx.reuse_at_snr(raw_t, diag_t, snr_centis[0] / 100))
    return dict(cells=out, truth=P.truth_fields(ctx, truth0, diag_t), shared_seconds=shared_seconds, snr_seconds=snr_seconds,
                spg_gram_seconds=spg_gram_seconds)


# ----------------------------------------------------------------------------- shard i/o
def cell_key(row):
    return (row['snr_centi_db'], row['frame'])


def load_done(path):
    path = Path(path)
    if not path.exists():
        return set()
    data = path.read_bytes()
    cut = data.rfind(b'\n') + 1
    if cut != len(data):
        path.write_bytes(data[:cut])
    return {cell_key(json.loads(x)) for x in data[:cut].decode().splitlines() if x.strip()}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--set', choices=tuple(SETS), default='test', help='entropy / domain set')
    p.add_argument('--frames', type=int, required=True, help='frames per SNR point')
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--snr-list', default=DEFAULT_SNR)
    p.add_argument('--arms', default='F0,B,A3,SPG,EP,EPG')
    p.add_argument('--rho-ep-list', default='', help='EP pilot energy fractions; default: the frozen RHO_EP')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--label', default='')
    return p.parse_args(argv)


def fingerprint(args, ctx, argv, rho_ep_list):
    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    entropy, domain = SETS[args.set]
    config.update(ENTROPY_HEX=entropy, DOMAIN=domain, RHO_EP=RHO_EP, rho_ep_list=rho_ep_list, RHO_EP_GRID=RHO_EP_GRID,
                  flags_S=dict(fix_delay_cap=FLAGS_S.fix_delay_cap, fix_delay_grid=FLAGS_S.fix_delay_grid, doppler_law=FLAGS_S.doppler_law,
                               fix_energy=FLAGS_S.fix_energy, delay_scale=FLAGS_S.delay_scale, l_trunc=FLAGS_S.l_trunc, tag=FLAGS_S.tag()),
                  nu_max_99=gen_fixed.UWA_NU_MAX_99, receiver=RECEIVER_CONFIG,
                  ep_layout=dict(N=E.N, pilot=E.PILOT, guard_per_side=E.Q_GUARD, data=E.N_DATA, code_n=E.CODE_N, code_seed=E.CODE_SEED,
                                 p_fa=E.P_FA, nu_grid_step=0.05, max_paths=E.MAX_PATHS, rounds=2, bp_iterations=50),
                  source_md5=ctx.source_md5, source_sha256=ctx.source_sha256, code_g_sha256=ctx.header['code_g_sha256'],
                  checkpoint_sha256=ctx.header.get('checkpoint_sha256'), environment=ctx.environment)
    return list(argv), config


def add_sources(ctx):
    for name, path in (('ep_rx', HERE / 'ep_rx.py'), ('p2b_driver', HERE / 'p2b_driver.py')):
        ctx.source_md5[name] = P.md5_file(path)
        ctx.source_sha256[name] = P.sha256_file(path)
        ctx.source_paths[name] = str(path.relative_to(P.PROJECT))


def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    arms = P.parse_list(args.arms, str)
    if not set(arms) <= set(SP_ARMS) | set(EP_ARMS) | {SPG_ARM}:
        raise ValueError('unknown arm')
    snr_cells = [int(round(float(x) * 100)) for x in P.parse_list(args.snr_list, str)]
    if args.rho_ep_list:
        rho_ep_list = P.parse_list(args.rho_ep_list, float)
    else:
        if RHO_EP is None and any(a in EP_ARMS for a in arms):
            raise ValueError('RHO_EP has not been frozen: run the dev tuning first or pass --rho-ep-list')
        rho_ep_list = [RHO_EP]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ctx = P.load_context()
    add_sources(ctx)
    ep = build_ep(ctx)
    _, config = fingerprint(args, ctx, argv, rho_ep_list)
    jsonable = lambda v: json.loads(json.dumps(v, default=ctx.hd.to_jsonable))  # noqa: E731
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment', 'shard', 'out')}
    if config_path.exists():
        if json.loads(config_path.read_text()).get('_config_cmp') != jsonable(comparable):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable), indent=1,
                                          default=ctx.hd.to_jsonable, allow_nan=False) + '\n')
    entropy, domain = SETS[args.set]
    seed_fn = P.make_seed_fn(entropy, domain)
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = load_done(jsonl)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    started = time.perf_counter()
    n_cells = 0
    with jsonl.open('a') as handle:
        for frame in frames:
            todo = [s for s in snr_cells if (s, frame) not in done]
            if not todo:
                continue
            result = frame_cells(ctx, ep, frame, todo, SP_RHOS, arms, rho_ep_list, seed_fn)
            cells, truth = result['cells'], result['truth']
            for snr in todo:
                row = dict(scenario='S', snr_centi_db=int(snr), snr_db=snr / 100, frame=int(frame), set=args.set, label=args.label,
                           shared_seconds=result['shared_seconds'], snr_seconds=result['snr_seconds'][snr], arms=cells[snr], **truth)
                handle.write(json.dumps(row, sort_keys=True, allow_nan=False, default=ctx.hd.to_jsonable) + '\n')
                handle.flush()
                os.fsync(handle.fileno())
                n_cells += 1
            print(f'[{time.perf_counter() - started:8.1f}s] frame={frame} snrs={len(todo)} redraws={truth["gen_redraws"]} '
                  + ' '.join(f"{k}:{v.get('info_errors', 'ERR')}" for k, v in cells[todo[-1]].items()), flush=True)
    print(f'shard {args.shard}/{args.nshard} done: {n_cells} cells in {time.perf_counter() - started:.1f}s', flush=True)


if __name__ == '__main__':
    run_shard(parse_args(), sys.argv[1:])
