#!/usr/bin/env python
"""Genie-support driver (protocol.md sections 1-2, task 10-16-tcom-genie-support).

Frames: P1 frames (same entropy/domain/generator, via tcom_channel_crb_20261016/p1ctx).  Per (scenario, rho, snr, frame) one
JSONL row with two arms:
  GS-set    true delay SET (one slot per distinct delay, ordered by true per-delay energy, descending)
  GS-multi  true delay MULTISET (= headroom-ladder A1, arms.make_a1_refine(truth['l_i']) unchanged)
Both run native_twofft.receive (rounds=2, iterations=20, soft CE, joint gains) through interventions._instrumented with only
the refit's delay list replaced (arms.refine_fixed_delays); no CSTATE.  Row: FER, decoded_sha256, syndrome, r0/r1 geometry,
channel NMSE of r1_gains (primary) and r1_ce_gains, refit log, seconds.  Assertion S4 is checked on every row.
Run one process per shard, single thread (launch_gs.sh).  Nothing frozen is edited.
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
CRB_DIR = HERE.parent / 'tcom_channel_crb_20261016'
sys.path.insert(0, str(CRB_DIR))
import crb  # noqa: E402
import p1ctx  # noqa: E402

SCENARIOS = ('U', 'G')
ARMS = ('GS-set', 'GS-multi')
DEFAULT_RHO = '0.3,0.5'
DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'


def bits_sha(decoded):
    return hashlib.sha256(np.asarray(decoded, np.uint8).tobytes()).hexdigest()


def genie_delays(truth, arm):
    l = np.asarray(truth['l_i'], int)
    if arm == 'GS-multi':
        return l.copy()
    g2 = np.abs(np.asarray(truth['g_i'])) ** 2
    u = np.unique(l)
    energy = np.array([g2[l == d].sum() for d in u])
    return u[np.argsort(-energy, kind='stable')]


def run_gs(ctx, obs, refine, gain_mode='joint', arm='genie_support'):
    """Production schedule with the refit replaced by ``refine``; front, detector and decoder unchanged."""
    return ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm=arm, rounds=2, iterations=20,
                                      gain_mode=gain_mode, refine_override=refine)


def observe(ctx, raw_base, diag_base, rho, snr_centi):
    raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_centi / 100)
    return raw, ctx.hd.observe(raw, rho, snr_centi / 100), ctx.hd.truth_from_raw(raw, diag)


def score(ctx, decoded, truth):
    return int(np.count_nonzero(ctx.extract_info(ctx.code, np.asarray(decoded)) != truth['info']))


def paths(delays, dopplers, gains):
    return dict(delays=[int(x) for x in np.asarray(delays)], dopplers=[float(x) for x in np.asarray(dopplers)],
                gains=np.asarray(gains, complex))


def gs_arm(ctx, obs, truth, arm, n):
    delays = genie_delays(truth, arm)
    log = []
    t0 = time.perf_counter()
    res = run_gs(ctx, obs, ctx.arms.make_a1_refine(delays, log))
    seconds = time.perf_counter() - t0
    a = res.arrays
    # S4: the supplied delay list is used verbatim in both rounds; both refits logged; geometry finite and in range
    for r in (0, 1):
        assert np.array_equal(np.asarray(a[f'r{r}_delays'], int), delays), f'S4 delay list changed ({arm}, round {r})'
        nu = np.asarray(a[f'r{r}_dopplers'], float)
        assert np.all(np.abs(nu) <= 3) and np.isfinite(nu).all(), f'S4 Doppler out of range ({arm})'
        assert np.isfinite(a[f'r{r}_gains']).all() and np.isfinite(a[f'r{r}_ce_gains']).all(), f'S4 nonfinite gains ({arm})'
    assert len(log) == 2, f'S4 expected 2 refits, got {len(log)} ({arm})'
    truth_p = dict(delays=np.asarray(truth['l_i'], int), dopplers=np.asarray(truth['k_real'], float),
                   gains=np.asarray(truth['g_i'], complex))
    dec = res.decoder['decoded']
    return dict(fer=int(score(ctx, dec, truth) > 0), info_errors=score(ctx, dec, truth),
                syndrome=int(ctx.hd.syndrome_weight(ctx, dec)), decoded_sha256=bits_sha(dec),
                ldpc_iters=int(res.decoder['iterations']), seconds=seconds,
                delays=[int(x) for x in delays], r1_dopplers=[float(x) for x in a['r1_dopplers']],
                nmse=crb.channel_nmse(paths(a['r1_delays'], a['r1_dopplers'], a['r1_gains']), truth_p, n),
                nmse_ce=crb.channel_nmse(paths(a['r1_delays'], a['r1_dopplers'], a['r1_ce_gains']), truth_p, n),
                n_missing_slots=[int(x['n_missing_slots']) for x in log],
                q_min_eig_over_noise=[float(x['q_min_eig_over_noise']) for x in log],
                refit_evaluations=[int(x['evaluations']) for x in log])


def parse_list(text, cast):
    return [cast(x) for x in str(text).split(',') if str(x).strip()]


def load_done(path):
    if not path.exists():
        return set()
    data = path.read_bytes()
    cut = data.rfind(b'\n') + 1
    if cut != len(data):
        path.write_bytes(data[:cut])
    return {(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
            for r in map(json.loads, data[:cut].decode().splitlines()) if r}


def source_md5(ctx):
    own = {f: hashlib.md5((HERE / f).read_bytes()).hexdigest() for f in ('gs_driver.py',)}
    own.update({f: hashlib.md5((CRB_DIR / f).read_bytes()).hexdigest() for f in ('crb.py', 'p1ctx.py')})
    arms_file = getattr(ctx.arms, '__file__', None)
    if arms_file:
        own['headroom_arms.py'] = hashlib.md5(Path(arms_file).read_bytes()).hexdigest()
    return {**ctx.source_md5, **own}


def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rho_list = parse_list(args.rho_list, float)
    snr_cells = [int(round(float(x) * 100)) for x in parse_list(args.snr_list, str)]
    scenarios = parse_list(args.scenarios, str)
    config = dict(vars(args), out=str(args.out), entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN,
                  arms=dict(zip(ARMS, ('unique true delays, ordered by true per-delay energy desc; arms.make_a1_refine',
                                       "truth['l_i'] multiset as given; arms.make_a1_refine (headroom A1)"))),
                  schedule='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint; no CSTATE',
                  source_md5=source_md5(ctx), environment=ctx.environment)
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    if not cfg_path.exists():
        cfg_path.write_text(json.dumps(dict(_argv=list(argv), _config=config), indent=1, default=str) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = load_done(jsonl)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    started = time.perf_counter()
    with jsonl.open('a') as handle:
        for frame in frames:
            for scenario in scenarios:
                for rho in rho_list:
                    rho_pm = int(round(rho * 1000))
                    todo = [s for s in snr_cells if (scenario, rho_pm, s, frame) not in done]
                    if not todo:
                        continue
                    raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
                    for snr_centi in todo:
                        raw, obs, truth = observe(ctx, raw_base, diag_base, rho, snr_centi)
                        n = len(raw['y'])
                        l, nu, g = (np.asarray(truth['l_i'], int), np.asarray(truth['k_real'], float),
                                    np.asarray(truth['g_i'], complex))
                        arms = {arm: gs_arm(ctx, obs, truth, arm, n) for arm in ARMS}
                        row = dict(scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=int(snr_centi),
                                   snr_db=snr_centi / 100, frame=int(frame), sigma2=float(raw['sigma2']),
                                   frob=crb.frob2(l, nu, g, n), n_paths=len(g), distinct_delays=int(len(set(l.tolist()))),
                                   arms=arms)
                        handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
                        handle.flush()
                        os.fsync(handle.fileno())
                        print(f"[{time.perf_counter() - started:8.1f}s] {scenario} rho={rho} snr={snr_centi} frame={frame} "
                              + ' '.join(f"{a}:{r['fer']} {10 * np.log10(r['nmse']):.1f}dB" for a, r in arms.items()),
                              flush=True)
    print(f'shard {args.shard}/{args.nshard} done in {time.perf_counter() - started:.1f}s', flush=True)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--scenarios', default=','.join(SCENARIOS))
    p.add_argument('--rho-list', default=DEFAULT_RHO)
    p.add_argument('--snr-list', default=DEFAULT_SNR)
    p.add_argument('--frames', type=int, required=True)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    return p.parse_args(argv)


if __name__ == '__main__':
    run_shard(parse_args(), sys.argv[1:])
