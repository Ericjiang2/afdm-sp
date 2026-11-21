#!/usr/bin/env python
"""E-3 driver (task 10-17-external-sbl-e3; PROTOCOL.md = design.md + execution facts).

Luo-style two-stage data-aided EM-SBL receiver (sbl_rx.py) on P1 frames; per key one row with four stage-2 variants that differ ONLY in the
data model of the dictionary:
  L-hard   hard-decision remodulation Mod[Demod(mu_d)], Gamma = 0,        beta0 = 1/(sigma2 + mean v)     (Luo as published)
  L-diag   soft mean mu_d,           Gamma = sum(v) I (= diag Gamma),     beta0 = 1/(sigma2 + mean v)
  L-cov    soft mean mu_d,           Gamma = full projected covariance,   beta0 = 1/(sigma2 + mean v)
  L-genie  true data,                Gamma = 0,                           beta0 = 1/sigma2                (grid-mismatch baseline)
Flow: stage 1 (pilot-only SBL) -> detection+LDPC (fixed gains, prior 0) -> stage 2 (variant SBL on a shared candidate set) -> detection+LDPC
(fixed gains, prior = round-1 check) -> unconditional FER.

Modes: gate / gate-merge (T3 on P1 frames 0..19, dictionary-convention check, data-scaling check, T2 on a real frame, T4 on real frames) |
       calibrate / calibrate-merge (frames 6000..6099, L-hard only -> GRID.json) | run (frames 4000..4399; --smoke for smoke runs) |
       riter (report-only robustness check after the main run: 200 frozen keys, L-diag and L-cov with max_iter = 400, PROTOCOL.md section 11 O2).
Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path.insert(0, str(HERE))
import e3_lib  # noqa: E402

e3_lib.prepare_paths()
sys.path.insert(0, str(EXPERIMENTS / 'tcom_genie_support_20261016'))
import e3_calib  # noqa: E402
import gs_driver as gd  # noqa: E402
import sbl_rx as sbl  # noqa: E402
from gs_driver import crb, p1ctx  # noqa: E402

P1_ROWS = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'out' / 'p1'
VARIANTS = ('L-hard', 'L-diag', 'L-cov', 'L-genie')
MAIN_FRAMES = (4000, 4400)
CAL_FRAMES = (6000, 6100)
SMOKE_FRAMES_MIN = 8000
CELLS = (('U', 300), ('U', 500), ('G', 300), ('G', 500))
CAL_SNR_LIST = ','.join(str(s) for s in e3_calib.CAL_SNRS)


def cell_name(scenario, rho_permille):
    return f'{scenario}_{rho_permille}'


# ----------------------------------------------------------------------------- provenance
def check_frozen_md5(ctx):
    """Every file in SOURCE_MD5.txt must have the recorded md5 (the loaded module of the same stem if there is one, else the file on disk)."""
    results, bad = {}, []
    for line in (HERE / 'SOURCE_MD5.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        digest, rel = line.split()
        path = EXPERIMENTS / rel
        loaded = ctx.source_md5.get(Path(rel).stem) if rel.endswith('.py') else None
        if loaded is not None:
            actual, how = loaded, 'loaded-module'
        elif path.exists():
            actual, how = e3_lib.md5_file(path), 'file'
        else:
            actual, how = None, 'absent'
        results[rel] = dict(expected=digest, actual=actual, via=how)
        if actual is None:
            results[rel]['status'] = 'unchecked'
        elif actual != digest:
            results[rel]['status'] = 'MISMATCH'
            bad.append(rel)
        else:
            results[rel]['status'] = 'ok'
    if bad:
        raise RuntimeError(f'frozen source md5 mismatch: {bad}')
    return results


def own_md5():
    names = ('e3_driver.py', 'e3_lib.py', 'e3_calib.py', 'sbl_rx.py', 'e3_agg.py', 'PROTOCOL.md', 'SOURCE_MD5.txt')
    return {n: e3_lib.md5_file(HERE / n) for n in names if (HERE / n).exists()}


def write_config(out, shard, argv, args, ctx, extra=None):
    path = out / f'config_shard{shard:03d}.json'
    if path.exists():
        return
    cfg = dict(vars(args), out=str(args.out), variants=VARIANTS, hyper=sbl.HYPER,
               receiver='sbl_rx.py: Luo-style 2-stage EM-SBL, K=2575 fine grid, M=256 screening, <=24 output atoms, co-delay atoms allowed; detection '
                        'scalar_joint(iterations=20, damping=.3, gain_mode=fixed), LDPC decoder_messages(maxiter=50)',
               family_P1=dict(entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN),
               frozen_md5_check=check_frozen_md5(ctx), own_md5=own_md5(), source_md5=ctx.source_md5, environment=ctx.environment, **(extra or {}))
    path.write_text(json.dumps(dict(_argv=list(argv), _config=cfg), indent=1, default=str) + '\n')


# ----------------------------------------------------------------------------- dictionary cache (pilot dictionary is frame independent)
class PilotCache:
    def __init__(self):
        self.store = {}

    def columns(self, pilot, c1, c2, delays, dopplers):
        key = np.asarray(pilot).tobytes()
        if key not in self.store:
            self.store[key] = sbl.columns(self_xt(pilot, c1, c2), delays, dopplers, c1, c2)
        return self.store[key]


def self_xt(x_af, c1, c2):
    from physical import daft
    return daft(x_af, c1, c2, True)


# ----------------------------------------------------------------------------- the two-round pipeline for one key
def detect_decode(ctx, obs, channel, prior):
    t0 = time.perf_counter()
    det = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - ctx.system.rho, prior=prior, iterations=20,
                                  damping=.3, gain_mode='fixed')
    t1 = time.perf_counter()
    dec = ctx.native.decoder_messages(ctx.code, np.clip(det['extrinsic'], -20, 20), maxiter=50)
    return det, dec, t1 - t0, time.perf_counter() - t1


def make_channel(ctx, n, delays, dopplers, gains):
    from physical import Channel
    return Channel(n, ctx.system.c1, ctx.system.c2, [int(x) for x in delays], [float(x) for x in dopplers], np.asarray(gains, complex))


def truth_paths(truth):
    return dict(delays=[int(x) for x in np.asarray(truth['l_i'])], dopplers=[float(x) for x in np.asarray(truth['k_real'])],
                gains=np.asarray(truth['g_i'], complex))


def atoms_record(delays, dopplers, energies):
    return [[int(l), float(nu), float(e)] for l, nu, e in zip(delays, dopplers, energies)]


def process_key(ctx, cache, grid, obs, data_true_af, truth, meta, variants=VARIANTS, max_iter=sbl.MAX_ITER):
    """Both rounds for one key; returns the row.  ``data_true_af`` = true data in the internal convention (genie only).
    ``max_iter`` applies to the stage-2 SBL runs only (stage 1 always uses the frozen 100); the R-iter check passes 400."""
    from messages import moments
    from physical import daft
    t_all = time.perf_counter()
    s, native = ctx.system, ctx.native
    n, c1, c2 = len(obs['y']), s.c1, s.c2
    pd = 1 - s.rho
    sigma2 = float(obs['sigma2'])
    delays_g, nus_g = grid
    tp = truth_paths(truth)
    true_delays = set(tp['delays'])
    sec = {}
    Y = daft(obs['y'], c1, c2, True)
    # ---- stage 1: pilot-only SBL (Gamma = 0, data = white interference)
    t = time.perf_counter()
    Bp = cache.columns(obs['pilot'], c1, c2, delays_g, nus_g)
    cand1 = sbl.screen(Bp, Y, sbl.N_SCREEN)
    sec['stage1_screen'] = time.perf_counter() - t
    t = time.perf_counter()
    r1 = sbl.sbl_em(Bp[:, cand1], Y, beta0=1.0 / (sigma2 + pd), Gamma=None)
    g1_idx, g1_mu, g1_e = sbl.select_output(cand1[r1['idx']], r1['mu'])
    sec['stage1_sbl'] = time.perf_counter() - t
    ch1 = make_channel(ctx, n, delays_g[g1_idx], nus_g[g1_idx], g1_mu)
    # ---- round 1
    det1, dec1, t_det, t_dec = detect_decode(ctx, obs, ch1, None)
    sec['round1_detect'], sec['round1_decode'] = t_det, t_dec
    mu_d, v, _ = moments(np.clip(dec1['raw_app'], -20, 20), pd)
    check = np.clip(dec1['raw_check_extrinsic'], -20, 20)
    err1 = gd.score(ctx, dec1['decoded'], truth)
    # ---- stage 2 shared candidate set (soft-mean dictionary, plus the full Doppler rows of the stage-1 delays)
    t = time.perf_counter()
    Bs = sbl.columns(self_xt(obs['pilot'] + mu_d, c1, c2), delays_g, nus_g, c1, c2)
    top2 = sbl.screen(Bs, Y, sbl.N_SCREEN)
    cand2 = sbl.candidate_union(top2, set(int(x) for x in delays_g[g1_idx]), delays_g)
    cd, cn = delays_g[cand2], nus_g[cand2]
    sec['stage2_screen'] = time.perf_counter() - t
    mean_v = float(np.mean(v))
    beta0_soft = 1.0 / (sigma2 + mean_v)
    row = dict(meta, sigma2=sigma2,
               truth=dict(delays=tp['delays'], dopplers=tp['dopplers'], gains=[[float(g.real), float(g.imag)] for g in tp['gains']]),
               stage1=dict(n_candidates=int(len(cand1)), iterations=r1['iterations'], converged=r1['converged'], n_final=r1['n_final'], beta=r1['beta'],
                           jitter_events=r1['jitter_events'], atoms=atoms_record(delays_g[g1_idx], nus_g[g1_idx], g1_e),
                           nmse=float(crb.channel_nmse(dict(delays=delays_g[g1_idx], dopplers=nus_g[g1_idx], gains=g1_mu), tp, n))),
               round1=dict(info_errors=int(err1), syndrome=int(ctx.hd.syndrome_weight(ctx, dec1['decoded'])), decoded_sha256=gd.bits_sha(dec1['decoded']),
                           ldpc_iters=int(dec1['iterations'])),
               mean_v=mean_v, n_candidates_stage2=int(len(cand2)), kept_delays_stage1=int(len(set(int(x) for x in delays_g[g1_idx]))), variants={})
    gamma = None
    for name in variants:
        t_v = time.perf_counter()
        vsec = {}
        t = time.perf_counter()
        if name == 'L-hard':
            B = sbl.columns(self_xt(obs['pilot'] + sbl.hard_decision(mu_d, pd), c1, c2), cd, cn, c1, c2)
            G, beta0 = None, beta0_soft
        elif name == 'L-genie':
            B = sbl.columns(self_xt(obs['pilot'] + data_true_af, c1, c2), cd, cn, c1, c2)
            G, beta0 = None, 1.0 / sigma2
        else:
            B = Bs[:, cand2]
            beta0 = beta0_soft
            if name == 'L-diag':
                G = float(v.sum())
            else:
                if gamma is None:
                    t_g = time.perf_counter()
                    gamma = sbl.gamma_full(cd, cn, v, c1)
                    row['gamma_diag_rel_err'] = float(np.max(np.abs(np.diag(gamma).real - v.sum()) / v.sum()))
                    row['gamma_seconds'] = time.perf_counter() - t_g
                G = gamma
        vsec['columns'] = time.perf_counter() - t
        t = time.perf_counter()
        res = sbl.sbl_em(B, Y, beta0=beta0, Gamma=G, max_iter=max_iter)
        idx, mu, e = sbl.select_output(cand2[res['idx']], res['mu'])
        vsec['sbl'] = time.perf_counter() - t
        ch2 = make_channel(ctx, n, delays_g[idx], nus_g[idx], mu)
        det2, dec2, t_det, t_dec = detect_decode(ctx, obs, ch2, check)
        vsec['detect'], vsec['decode'] = t_det, t_dec
        err2 = gd.score(ctx, dec2['decoded'], truth)
        pairs = sbl.codelay_pairs(delays_g[idx], nus_g[idx], n, true_delays)
        vsec['total'] = time.perf_counter() - t_v
        row['variants'][name] = dict(
            info_errors=int(err2), fer=int(err2 > 0), syndrome=int(ctx.hd.syndrome_weight(ctx, dec2['decoded'])), decoded_sha256=gd.bits_sha(dec2['decoded']),
            ldpc_iters=int(dec2['iterations']), n_atoms=int(len(idx)), atoms=atoms_record(delays_g[idx], nus_g[idx], e), n_pair=len(pairs), pairs=pairs,
            nmse=float(crb.channel_nmse(dict(delays=delays_g[idx], dopplers=nus_g[idx], gains=mu), tp, n)),
            sbl=dict(max_iter=int(max_iter), iterations=res['iterations'], converged=res['converged'], n_start=res['n_start'], n_final=res['n_final'], beta=res['beta'],
                     jitter_events=res['jitter_events']), seconds=vsec)
    sec['total'] = time.perf_counter() - t_all
    row['seconds'] = sec
    return row


def write_row(handle, row):
    handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
    handle.flush()
    os.fsync(handle.fileno())


def key_of(row):
    return (row['scenario'], row['rho_permille'], row['snr_centi_db'], row['frame'])


def observe_key(ctx, raw_base, diag_base, scenario, rho_pm, snr, frame, gen_seconds=0.):
    """(meta, obs, data_true_af, truth) of one key from a generated P1 base frame (SNR in centi-dB)."""
    rho = rho_pm / 1000
    scale = np.sqrt(2. * (1. - rho))
    raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
    meta = dict(family='P1', scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=int(snr), snr_db=snr / 100, frame=int(frame),
                gen_seconds=gen_seconds)
    return meta, obs, np.asarray(raw['data']) / scale, truth


def cells_of_frame(ctx, frame, grid_by_cell, snr_default):
    """Yield (meta, obs, data_true_af, truth) for every (cell, SNR) of one P1 frame."""
    for scenario, rho_pm in CELLS:
        snrs = grid_by_cell.get(cell_name(scenario, rho_pm), snr_default) if grid_by_cell is not None else snr_default
        if not snrs:
            continue
        g0 = time.perf_counter()
        raw_base, diag_base = p1ctx.base(ctx, scenario, rho_pm / 1000, frame)
        gen_seconds = time.perf_counter() - g0
        for k, snr in enumerate(snrs):
            yield observe_key(ctx, raw_base, diag_base, scenario, rho_pm, int(round(float(snr) * 100)), frame, gen_seconds if k == 0 else 0.)


def run_frames(ctx, args, frames, variants, grid_by_cell, snr_default, jsonl):
    cache = PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    done = gd.load_done(jsonl)
    started = time.perf_counter()
    n_rows = 0
    with jsonl.open('a') as handle:
        for frame in frames:
            if args.max_keys and n_rows >= args.max_keys:
                break
            for meta, obs, data_af, truth in cells_of_frame(ctx, frame, grid_by_cell, snr_default):
                if key_of(meta) in done:
                    continue
                if args.max_keys and n_rows >= args.max_keys:
                    break
                if args.smoke:
                    meta['smoke'] = True
                try:
                    row = process_key(ctx, cache, grid, obs, data_af, truth, meta, variants)
                except Exception as error:  # recorded, never silently dropped
                    row = dict(meta, status='error', error=repr(error), trace=traceback.format_exc()[-1500:])
                write_row(handle, row)
                n_rows += 1
                print(f"[{time.perf_counter() - started:8.1f}s] {key_of(meta)} "
                      + (' '.join(f"{v}:{r['info_errors']}/{r['n_pair']}" for v, r in row.get('variants', {}).items()) if 'variants' in row else row.get('error', '')),
                      flush=True)
    return n_rows, time.perf_counter() - started


# ----------------------------------------------------------------------------- run / calibrate
def parse_grid(args):
    if args.smoke_snr:
        return {cell_name(*c): [float(x) for x in args.smoke_snr.split(',')] for c in CELLS}, None
    grid = json.loads(Path(args.grid).read_text())
    out = {}
    for c in CELLS:
        e = grid['cells'][cell_name(*c)]
        out[cell_name(*c)] = [] if e['status'] != 'OK' else [float(x) for x in e['grid_db']]
    return out, grid


def run_mode(args, argv):
    lo, hi = MAIN_FRAMES
    f_lo, f_hi = args.frame_offset, args.frame_offset + args.frames
    if not args.smoke and not (lo <= f_lo and f_hi <= hi):
        raise ValueError(f'main run frames must lie in [{lo}, {hi}); use --smoke for other frames')
    if args.smoke and f_lo < SMOKE_FRAMES_MIN and not args.smoke_any_frames:
        raise ValueError(f'smoke frames must be >= {SMOKE_FRAMES_MIN} (disjoint from calibration and main)')
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    grid_by_cell, grid_doc = parse_grid(args)
    if not any(grid_by_cell.values()):
        raise SystemExit('no informative cell in GRID.json; nothing to run')
    write_config(out, args.shard, argv, args, ctx, extra=dict(smoke_only=bool(args.smoke), grid_by_cell=grid_by_cell,
                                                              grid_md5=None if not args.grid or args.smoke else e3_lib.md5_file(args.grid)))
    frames = list(range(f_lo, f_hi))[args.shard::args.nshard]
    n, secs = run_frames(ctx, args, frames, VARIANTS, grid_by_cell, None, out / f'rows_shard{args.shard:03d}.jsonl')
    print(f'shard {args.shard}/{args.nshard} done: {n} keys in {secs:.1f}s', flush=True)


def calibrate_mode(args, argv):
    lo, hi = CAL_FRAMES
    f_lo, f_hi = args.frame_offset, args.frame_offset + args.frames
    if not args.smoke and not (lo <= f_lo and f_hi <= hi):
        raise ValueError(f'calibration frames must lie in [{lo}, {hi}); use --smoke for timing runs on other frames')
    if args.smoke and f_lo < SMOKE_FRAMES_MIN and not args.smoke_any_frames:
        raise ValueError(f'smoke frames must be >= {SMOKE_FRAMES_MIN}')
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx, extra=dict(smoke_only=bool(args.smoke), candidate_snr_db=list(e3_calib.CAL_SNRS), variant='L-hard only'))
    snrs = [float(x) for x in gd.parse_list(args.snr_list or CAL_SNR_LIST, str)]
    frames = list(range(f_lo, f_hi))[args.shard::args.nshard]
    n, secs = run_frames(ctx, args, frames, ('L-hard',), None, snrs, out / f'cal_rows_shard{args.shard:03d}.jsonl')
    print(f'calibration shard {args.shard}/{args.nshard} done: {n} keys in {secs:.1f}s', flush=True)


def calibrate_merge(args):
    rows = []
    for p in sorted(glob.glob(str(args.out / 'cal_rows_shard*.jsonl'))):
        rows += [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
    lo, hi = CAL_FRAMES
    want = {(sc, rho, int(s * 100), f) for sc, rho in CELLS for s in e3_calib.CAL_SNRS for f in range(lo, hi)}
    got = [key_of(r) for r in rows]
    errors = [r for r in rows if r.get('status') == 'error']
    if len(got) != len(set(got)) or set(got) != want or errors:
        raise SystemExit(f'calibration incomplete, duplicated or with errors: {len(set(got))} of {len(want)} keys, {len(errors)} error rows')
    doc = dict(rule='per (scenario, rho) cell: s0 = smallest candidate SNR in {4..14} dB with L-hard unconditional FER <= .9; grid {s0..s0+5} truncated at 14; '
                    'L-hard FER(14 dB) > .9 -> UNINFORMATIVE', fer_metric='fraction of calibration frames with >= 1 information-bit error after round 2 (L-hard)',
               frames=[lo, hi], cells={}, n_rows=len(rows),
               rows_md5={Path(p).name: e3_lib.md5_file(p) for p in sorted(glob.glob(str(args.out / 'cal_rows_shard*.jsonl')))})
    for sc, rho in CELLS:
        fer = {s: float(np.mean([r['variants']['L-hard']['fer'] for r in rows if r['scenario'] == sc and r['rho_permille'] == rho
                                 and r['snr_centi_db'] == s * 100])) for s in e3_calib.CAL_SNRS}
        doc['cells'][cell_name(sc, rho)] = dict(fer_by_snr={str(s): v for s, v in fer.items()}, **e3_calib.decide_grid(fer))
    (args.out / 'GRID.json').write_text(json.dumps(doc, indent=1) + '\n')
    print(json.dumps(doc['cells'], indent=1))


# ----------------------------------------------------------------------------- R-iter robustness check (report-only; PROTOCOL.md section 11 O2)
def riter_mode(args, argv):
    """Re-run the frozen 200-key subsample with max_iter = 400 for L-diag and L-cov only.  Stage 1, the round-1 decode, the candidate set, beta0
    and Gamma are recomputed by the identical deterministic code (e3_agg cross-checks them against the main rows)."""
    if args.smoke and args.frame_offset < SMOKE_FRAMES_MIN and not args.smoke_any_frames:
        raise ValueError(f'smoke frames must be >= {SMOKE_FRAMES_MIN}')
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    grid_by_cell, _ = parse_grid(args)
    if args.smoke:   # smoke-only code-path check on other frames (never the main frames)
        keys = e3_calib.riter_sample({k: v for k, v in grid_by_cell.items() if v}, n=args.max_keys or e3_calib.RITER_N,
                                     frames=(args.frame_offset, args.frame_offset + args.frames))
    else:
        keys = e3_calib.riter_sample({k: v for k, v in grid_by_cell.items() if v})
    mine = keys[args.shard::args.nshard]
    write_config(out, args.shard, argv, args, ctx, extra=dict(riter=True, riter_max_iter=e3_calib.RITER_MAX_ITER, riter_n_keys=len(keys), smoke_only=bool(args.smoke),
                                                               riter_variants=['L-diag', 'L-cov'],
                                                               grid_md5=None if (args.smoke or not args.grid) else e3_lib.md5_file(args.grid)))
    cache = PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    started = time.perf_counter()
    base_key, base = None, None
    n_rows = 0
    with jsonl.open('a') as handle:
        for scenario, rho_pm, snr, frame in mine:
            if (scenario, rho_pm, snr, frame) in done:
                continue
            if base_key != (scenario, rho_pm, frame):
                base_key, base = (scenario, rho_pm, frame), p1ctx.base(ctx, scenario, rho_pm / 1000, frame)
            meta, obs, data_af, truth = observe_key(ctx, base[0], base[1], scenario, rho_pm, snr, frame)
            meta['riter'] = True
            if args.smoke:
                meta['smoke'] = True
            try:
                row = process_key(ctx, cache, grid, obs, data_af, truth, meta, ('L-diag', 'L-cov'), max_iter=e3_calib.RITER_MAX_ITER)
            except Exception as error:  # recorded, never silently dropped
                row = dict(meta, status='error', error=repr(error), trace=traceback.format_exc()[-1500:])
            write_row(handle, row)
            n_rows += 1
            print(f"[{time.perf_counter() - started:8.1f}s] {key_of(meta)} "
                  + (' '.join(f"{v}:{r['info_errors']}/{r['n_pair']}/{r['sbl']['iterations']}" for v, r in row.get('variants', {}).items()) if 'variants' in row else row.get('error', '')),
                  flush=True)
    print(f'riter shard {args.shard}/{args.nshard} done: {n_rows} keys in {time.perf_counter() - started:.1f}s', flush=True)


# ----------------------------------------------------------------------------- gate mode
def load_ledger_a3(p1_rows, frames):
    out = {}
    for p in sorted(glob.glob(str(Path(p1_rows) / 'rows_shard*.jsonl.gz'))):
        with gzip.open(p, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if r['frame'] in frames:
                    a3 = r['arms']['A3']
                    if a3.get('status') != 'ok':
                        raise ValueError('ledger A3 row not ok')
                    out[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = dict(sha=a3['decoded_sha256'], info_errors=int(a3['info_errors']))
    return out


def true_channel_two_rounds(ctx, obs, truth):
    """The T3 call path: the E-3 detector/decoder sequence with the TRUE paths and fixed gains in both rounds (== P1 arm A3: rounds=2,
    iterations=20, gain_mode='fixed', prior 0 then clip(check))."""
    n = len(obs['y'])
    tc = make_channel(ctx, n, truth['l_i'], truth['k_real'], truth['g_i'])
    _, dec1, _, _ = detect_decode(ctx, obs, tc, None)
    _, dec2, _, _ = detect_decode(ctx, obs, tc, np.clip(dec1['raw_check_extrinsic'], -20, 20))
    return dec2


def dictionary_convention_check(ctx, obs, data_af, raw, truth, rho):
    """Sum over the true paths of (dictionary column of the path with the true data, scaled by the true gain) must equal the noiseless
    observation: Y0 = daft(noiseless_y/scale, inverse) -- same Y / xt convention as run_validation._branch / reopen_geometry."""
    from physical import daft
    c1, c2 = ctx.system.c1, ctx.system.c2
    scale = np.sqrt(2. * (1. - rho))
    xt = daft(obs['pilot'] + data_af, c1, c2, True)
    B = sbl.columns(xt, np.asarray(truth['l_i'], dtype=np.int64), np.asarray(truth['k_real'], dtype=float), c1, c2)
    Y0 = daft(np.asarray(raw['noiseless']) / scale, c1, c2, True)
    model = B @ np.asarray(truth['g_i'], complex)
    rel = float(np.linalg.norm(model - Y0) / np.linalg.norm(Y0))
    # the received Y differs from Y0 by the (scaled, transformed) noise only
    noise = daft(np.asarray(raw['noise']) / scale * np.sqrt(float(raw['sigma2'])), c1, c2, True)
    rel_y = float(np.linalg.norm(daft(obs['y'], c1, c2, True) - Y0 - noise) / np.linalg.norm(Y0))
    return rel, rel_y


def data_scaling_check(data_af, pd, mu_probe=None):
    from messages import alphabet
    a, _ = alphabet(pd)
    dist = float(max(np.min(np.abs(a - z)) for z in data_af))
    hard = sbl.hard_decision(data_af, pd)
    return dist, float(np.max(np.abs(hard - data_af)))


def mc_gamma_real(ctx, cache, grid, obs, truth, samples=4000):
    """T2 on a real frame: Gamma of 24 atoms (true delays, near-duplicates, co-delay pairs) from the round-1 decoder APP vs Monte Carlo of
    E[(B(x)-B(mu))^H (B(x)-B(mu))] with x drawn from the per-symbol QPSK posterior (the distribution `moments` integrates)."""
    from messages import alphabet, logprior, moments
    from physical import daft
    s = ctx.system
    n, c1, c2 = len(obs['y']), s.c1, s.c2
    pd = 1 - s.rho
    delays_g, nus_g = grid
    Y = daft(obs['y'], c1, c2, True)
    Bp = cache.columns(obs['pilot'], c1, c2, delays_g, nus_g)
    cand1 = sbl.screen(Bp, Y, sbl.N_SCREEN)
    r1 = sbl.sbl_em(Bp[:, cand1], Y, beta0=1.0 / (obs['sigma2'] + pd), Gamma=None)
    gi, gm, _ = sbl.select_output(cand1[r1['idx']], r1['mu'])
    ch1 = make_channel(ctx, n, delays_g[gi], nus_g[gi], gm)
    _, dec1, _, _ = detect_decode(ctx, obs, ch1, None)
    L = np.clip(dec1['raw_app'], -20, 20)
    mu, v, _ = moments(L, pd)
    tl, tn = np.asarray(truth['l_i']), np.asarray(truth['k_real'])
    dl = np.concatenate([tl, tl, tl[:4]])
    dn_ = np.concatenate([tn, tn + .25, tn[:4] - 1.5])        # true atoms, same-delay near-duplicates (dnu .25), same-delay pairs (dnu 1.5)
    gam = sbl.gamma_full(dl, dn_, v, c1)
    rng = np.random.default_rng(7)
    a, _ = alphabet(pd)
    cum = np.cumsum(np.exp(logprior(L, pd)), axis=1)
    acc = np.zeros((len(dl), len(dl)), complex)
    for _ in range(samples):
        sym = np.minimum((rng.random(n)[:, None] > cum).sum(axis=1), 3)
        D = sbl.columns(daft(a[sym] - mu, c1, c2, True), dl, dn_, c1, c2)
        acc += D.conj().T @ D
    mc = acc / samples
    off = ~np.eye(len(dl), dtype=bool)
    eig = np.linalg.eigvalsh((gam + gam.conj().T) / 2)
    return dict(atoms=len(dl), samples=samples, diag_rel_err=float(np.max(np.abs(np.diag(gam).real - v.sum()) / v.sum())),
                hermitian_rel=float(np.linalg.norm(gam - gam.conj().T) / np.linalg.norm(gam)), min_eig_over_max=float(eig.min() / eig.max()),
                mc_rel_frobenius_error=float(np.linalg.norm(mc - gam) / np.linalg.norm(gam)),
                mc_rel_error_offdiagonal=float(np.linalg.norm((mc - gam)[off]) / np.linalg.norm(gam[off])), mean_v=float(v.mean()))


def strip_seconds(row):
    r = json.loads(json.dumps(row))
    for k in ('seconds', 'gamma_seconds', 'gen_seconds'):
        r.pop(k, None)
    for v in r.get('variants', {}).values():
        v.pop('seconds', None)
    return r


def gate_mode(args, argv):
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    ledger = load_ledger_a3(args.p1_rows, set(frames))
    cache = PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    records, extras, n_t4 = [], dict(), 0
    started = time.perf_counter()
    for frame in frames:
        for scenario, rho_pm in CELLS:
            rho = rho_pm / 1000
            raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
            scale = np.sqrt(2. * (1. - rho))
            for snr in snr_cells:
                raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
                data_af = np.asarray(raw['data']) / scale
                k = (scenario, rho_pm, snr, frame)
                dec = true_channel_two_rounds(ctx, obs, truth)
                rec = dict(key=list(k), t3_sha_match=bool(gd.bits_sha(dec['decoded']) == ledger[k]['sha']),
                           t3_info_errors=int(gd.score(ctx, dec['decoded'], truth)), ledger_info_errors=ledger[k]['info_errors'])
                if frame < 3 and snr in (500, 800):
                    rel, rel_y = dictionary_convention_check(ctx, obs, data_af, raw, truth, rho)
                    dist, hard_err = data_scaling_check(data_af, 1 - ctx.system.rho)
                    rec.update(conv_rel_err=rel, conv_rel_err_y=rel_y, data_alphabet_dist=dist, data_hard_self_err=hard_err)
                records.append(rec)
            # T2 on a real frame (once per shard, first cell/frame), T4 on two real keys per shard
            if 'mc' not in extras:
                raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, 600)
                extras['mc'] = dict(key=[scenario, rho_pm, 600, frame], **mc_gamma_real(ctx, cache, grid, obs, truth, samples=args.mc_samples))
            if n_t4 < args.t4_keys:
                snr = 600
                raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
                data_af = np.asarray(raw['data']) / scale
                meta = dict(family='P1', scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=snr, snr_db=snr / 100, frame=int(frame))
                r1 = process_key(ctx, cache, grid, obs, data_af, truth, dict(meta))
                r2 = process_key(ctx, cache, grid, obs, data_af, truth, dict(meta))
                diff = e3_lib.deep_equal(strip_seconds(r1), strip_seconds(r2))
                extras.setdefault('t4', []).append(dict(key=[scenario, rho_pm, snr, frame], identical=not diff, mismatch=diff[:3],
                                                        gamma_diag_rel_err=r1.get('gamma_diag_rel_err'), n_pair={v: x['n_pair'] for v, x in r1['variants'].items()},
                                                        sec=r1['seconds']))
                n_t4 += 1
        print(f'[{time.perf_counter() - started:8.1f}s] frame {frame} gate records {len(records)}', flush=True)
    (out / f'gate_shard{args.shard:03d}.json').write_text(json.dumps(dict(records=records, **extras)) + '\n')
    print(f'gate shard {args.shard}: {len(records)} states', flush=True)


def gate_merge(args):
    recs, mcs, t4 = [], [], []
    for p in sorted(args.out.glob('gate_shard*.json')):
        d = json.loads(p.read_text())
        recs += d['records']
        if 'mc' in d:
            mcs.append(d['mc'])
        t4 += d.get('t4', [])
    conv = [r for r in recs if 'conv_rel_err' in r]
    gates = dict(n_states=len(recs))
    gates['T3'] = dict(states=len(recs), sha_match=sum(r['t3_sha_match'] for r in recs),
                       info_errors_equal=sum(r['t3_info_errors'] == r['ledger_info_errors'] for r in recs),
                       note='E-3 detector/decoder call path with the TRUE paths (fixed gains) == P1 ledger arm A3 (run_fixed_channel detector=tf, rounds=2)')
    gates['T3']['pass_'] = bool(len(recs) >= 640 and gates['T3']['sha_match'] == len(recs))
    gates['CONV'] = dict(states=len(conv), worst_rel_err_noiseless=max([r['conv_rel_err'] for r in conv] or [1.]),
                         worst_rel_err_observation=max([r['conv_rel_err_y'] for r in conv] or [1.]),
                         worst_data_alphabet_dist=max([r['data_alphabet_dist'] for r in conv] or [1.]),
                         worst_hard_self_err=max([r['data_hard_self_err'] for r in conv] or [1.]))
    gates['CONV']['pass_'] = bool(len(conv) >= 8 and gates['CONV']['worst_rel_err_noiseless'] < 1e-10 and gates['CONV']['worst_rel_err_observation'] < 1e-10
                                  and gates['CONV']['worst_data_alphabet_dist'] < 1e-12 and gates['CONV']['worst_hard_self_err'] < 1e-12)
    gates['T2_real'] = dict(frames=len(mcs), worst_mc_rel_frobenius_error=max([m['mc_rel_frobenius_error'] for m in mcs] or [1.]),
                            worst_mc_rel_error_offdiagonal=max([m['mc_rel_error_offdiagonal'] for m in mcs] or [1.]),
                            worst_diag_rel_err=max([m['diag_rel_err'] for m in mcs] or [1.]), worst_hermitian_rel=max([m['hermitian_rel'] for m in mcs] or [1.]),
                            worst_min_eig_over_max=min([m['min_eig_over_max'] for m in mcs] or [-1.]), mean_v=[m['mean_v'] for m in mcs])
    T = gates['T2_real']
    T['pass_'] = bool(len(mcs) >= 1 and T['worst_mc_rel_frobenius_error'] <= .05 and T['worst_diag_rel_err'] < 1e-10 and T['worst_hermitian_rel'] < 1e-10
                      and T['worst_min_eig_over_max'] > -1e-9)
    gates['T4_real'] = dict(keys=len(t4), identical=sum(x['identical'] for x in t4), worst_gamma_diag_rel_err=max([x['gamma_diag_rel_err'] or 0. for x in t4] or [1.]),
                            mismatches=[x['mismatch'] for x in t4 if not x['identical']][:3])
    gates['T4_real']['pass_'] = bool(len(t4) >= 8 and gates['T4_real']['identical'] == len(t4) and gates['T4_real']['worst_gamma_diag_rel_err'] < 1e-10)
    gates['all_pass'] = all(gates[k]['pass_'] for k in ('T3', 'CONV', 'T2_real', 'T4_real'))
    (args.out / 'gates.json').write_text(json.dumps(gates, indent=1) + '\n')
    print(json.dumps(gates, indent=1))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('gate', 'gate-merge', 'calibrate', 'calibrate-merge', 'run', 'riter'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--p1-rows', type=Path, default=P1_ROWS)
    p.add_argument('--grid', type=Path, help='run / riter: GRID.json from calibrate-merge')
    p.add_argument('--snr-list', default=None, help='gate: P1 ledger SNRs (default 4.5..8.0); calibrate: default 4..14 dB')
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--smoke-snr', default='', help='run smoke only: provisional SNR list (dB) for every cell')
    p.add_argument('--smoke-any-frames', action='store_true')
    p.add_argument('--frames', type=int, default=400)
    p.add_argument('--frame-offset', type=int, default=MAIN_FRAMES[0])
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--max-keys', type=int, default=0, help='smoke: stop the shard after this many keys')
    p.add_argument('--mc-samples', type=int, default=4000)
    p.add_argument('--t4-keys', type=int, default=1, help='gate: keys per shard processed twice (T4)')
    a = p.parse_args(argv)
    if a.mode == 'gate' and a.snr_list is None:
        a.snr_list = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
    return a


if __name__ == '__main__':
    A = parse_args()
    if A.mode == 'gate':
        gate_mode(A, sys.argv[1:])
    elif A.mode == 'gate-merge':
        gate_merge(A)
    elif A.mode == 'calibrate':
        calibrate_mode(A, sys.argv[1:])
    elif A.mode == 'calibrate-merge':
        calibrate_merge(A)
    elif A.mode == 'riter':
        riter_mode(A, sys.argv[1:])
    else:
        run_mode(A, sys.argv[1:])
