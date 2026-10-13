#!/usr/bin/env python
"""C1 inner-update budget, second batch (IB2; task 10-08-doppler-cluster; research/c1-inner-budget.md section "IB2", FROZEN 2026-10-10).

Sibling of driver_c1ib.py (which is untouched, so the IB rows stay reproducible).  Same receiver, same observation generator, same row schema:
the only differences are (i) arbitrary (SNR, rho, L) cells per invocation and (ii) the arm name carries both knobs, `R<rounds>T<updates>`
(R4T20 == IB_T20, R4T40 == IB_T40, R10T40 = ten rounds at 40 inner updates).  Per arm the call is exactly driver_c1ib.run_arm_ib with
rounds = R and iterations = T:
    with dpss_rx.vector_prior(ctx.native):
        ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1i_full', rounds=R, iterations=T, gain_mode='joint', refine_override=refiner)
Observations are those of driver_c1 / driver_c1i for the same (entropy 129abc..., frame, L, rho, SNR): c1_boot (8 / 11 dB), c1_map (5 / 6.5 dB) and c1i /
c1f_r10 / c1g_r10lo (6.5 dB rho .3) used the same generator and entropy, so the rows of a given cell are paired with those stored runs.

Row fields: the c1i FULL fields (cerr/ierr/syn/dsha/ll_in/eps_ce/eps_det per round r = 1..R, r1_* reliability, eps_init/eps_pilot1/eps_proj, base.score fields,
head fields incl. e_real) plus R, T, inner_iters (kernel trace length per round, asserted == T), inference_iterations (asserted == T) and per-round timing
t_cum (receiver-clock seconds at the end of round r, incl. the pilot front), sec_ce_r, sec_inf_r, sec_dec_r (the compute-frontier input).

Presets (the frozen IB2 run definitions; --cells / --arms / --frames override them for smoke tests):
  rep    REP: rounds 4, T in {20, 40}, frames 0-199, 5 conditions (6.5 dB rho .2; 8 dB rho .2 / .3 / .5; 9.5 dB rho .3); L4 included at 6.5 dB rho .2 and 8 dB rho .5
  sweep  SWEEP: 6.5 dB rho .3, L 8-24, rounds 4, T in {30, 50}, frames 0-299
  r10    R10: 6.5 dB rho .3, L 16-32, rounds 10, T = 40, frames 0-299
  det    IB2-0 internal determinism: the REP cells without stored c1_boot / c1_map rows, R4T20, frames 0-9 (compare with the rep run)
  time   compute-frontier timing reference: 6.5 dB rho .3, L 8-32, R10 at T in {20, 30, 40, 50}, frames 0-9 (run alone on a quiet server)
Run one process per shard, single thread (launch_c1ib2.sh).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import traceback

import numpy as np

import driver as base
import driver_c1 as c1
import driver_c1i as c1i
import driver_c1ib as ib
import dpss_rx

HERE = base.HERE
CODE_FILES = ('driver_c1ib2.py', 'driver_c1ib.py', 'driver_c1i.py', 'driver_c1.py', 'driver.py', 'dpss_rx.py', 'tapchannel.py', 'arms.py', 'orders.py')


def _L(a, b, step=4):
    return list(range(a, b + 1, step))


# cell = (snr_db, rho, [L, ...])
# IB2 amendment (2026-10-10): L4 added at 6.5 dB rho .2 and 8 dB rho .5 (their R1 cliff lies at or below L8)
REP_CELLS = [(6.5, 0.2, _L(4, 28)), (8.0, 0.2, _L(12, 36)), (8.0, 0.3, _L(12, 36)), (8.0, 0.5, _L(4, 32)), (9.5, 0.3, _L(16, 40))]
# stored c1_boot SPg_flat rows exist for 8 dB, rho .2 / .3 / .5, L in {4, 8, 12, 16, 24, 32} (frames 0-999); nothing for 6.5 dB rho .2 / 9.5 dB
C1_BOOT_L = {4, 8, 12, 16, 24, 32}
DET_CELLS = [(s, r, [L for L in Ls if not (s == 8.0 and L in C1_BOOT_L)]) for (s, r, Ls) in REP_CELLS]
DET_CELLS = [c for c in DET_CELLS if c[2]]
PRESETS = {
    'rep': dict(cells=REP_CELLS, arms=['R4T20', 'R4T40'], frames=200),
    'sweep': dict(cells=[(6.5, 0.3, _L(8, 24))], arms=['R4T30', 'R4T50'], frames=300),
    'r10': dict(cells=[(6.5, 0.3, _L(16, 32))], arms=['R10T40'], frames=300),
    'det': dict(cells=DET_CELLS, arms=['R4T20'], frames=10),
    'time': dict(cells=[(6.5, 0.3, _L(8, 32))], arms=['R10T20', 'R10T30', 'R10T40', 'R10T50'], frames=10),
}
IB2_PARAMS = dict(
    pairing='observations identical to driver_c1 / driver_c1i / driver_c1ib for the same (entropy_hex 129abc..., frame, L, rho, SNR); arms differ only in (rounds R, inner updates T)',
    receiver='SPg_flat FULL (genie delays, flat prior, K = 8 L): IntervenedRefine(mode=full) under dpss_rx.vector_prior, interventions._instrumented(rounds=R, iterations=T, gain_mode=joint)',
    arms='R<rounds>T<updates>; rows 1..R of an R-round run equal the R\'-round run for R\' <= R (sequential rounds; checked in the analysis)',
    presets={k: dict(cells=[[s, r, Ls] for (s, r, Ls) in v['cells']], arms=v['arms'], frames=v['frames']) for k, v in PRESETS.items()},
    eps='eps_of semantics of driver_c1: ||H - H^||_F^2 / N')


def arm_RT(arm):
    m = re.fullmatch(r'R(\d+)T(\d+)', arm)
    if not m or not 1 <= int(m.group(1)) <= 20 or int(m.group(2)) < 1:
        raise ValueError(f'unknown arm {arm} (expected R<rounds 1..20>T<updates >= 1>)')
    return int(m.group(1)), int(m.group(2))


def parse_cells(text):
    """'6.5:0.2:8,12,16;8:0.3:12,16' -> [(6.5, 0.2, [8, 12, 16]), (8.0, 0.3, [12, 16])]"""
    out = []
    for part in text.split(';'):
        snr, rho, Ls = part.strip().split(':')
        out.append((float(snr), float(rho), [int(x) for x in Ls.split(',')]))
    return out


def code_md5():
    out = {name: ib.md5_file(HERE / name) for name in CODE_FILES}
    for name in ib.CODE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            out[f'{name}.py'] = ib.md5_file(module.__file__)
    return out


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--preset', choices=tuple(PRESETS), default=None)
    p.add_argument('--cells', default=None, help="'snr:rho:L,L,...;snr:rho:L,...' (overrides the preset)")
    p.add_argument('--arms', default=None, help='comma list of R<rounds>T<updates> (overrides the preset)')
    p.add_argument('--frames', type=int, default=None)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--entropy-hex', default=c1i.C1_MAP_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1ib2'  # base.fingerprint keys cluster params on 'clustered' only
    return args


def resolve(args):
    pre = PRESETS.get(args.preset, {})
    cells = parse_cells(args.cells) if args.cells else pre.get('cells')
    arms = base.parse_list(args.arms, str) if args.arms else pre.get('arms')
    frames = args.frames if args.frames else pre.get('frames')
    if not cells or not arms or not frames:
        raise ValueError('give --preset or all of --cells --arms --frames')
    for arm in arms:
        arm_RT(arm)
    if any(L < 1 or L > 101 for (_, _, Ls) in cells for L in Ls):
        raise ValueError('unknown L')
    return cells, arms, int(frames)


# ------------------------------------------------------------------------ receiver
def run_arm_ib2(ctx, obs, truth, arm, genie_delays, cfg, a_true):
    """driver_c1ib.run_arm_ib with rounds = R, iterations = T (arm R<R>T<T>) and per-round timing."""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    R, T = arm_RT(arm)
    refiner = c1i.IntervenedRefine(genie_delays, cfg, mode='full', lam=None, a_true=None)
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1i_full', rounds=R, iterations=T,
                                            gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != R:
        raise RuntimeError(f'expected {R} refits, got {len(refiner.snaps)}')
    events = result.timing['events']
    inner = [len(ar[f'r{r}_inference_trace']) for r in range(R)]
    infer = [int(e['inference_iterations']) for e in events]
    if inner != [T] * R or infer != [T] * R:
        raise RuntimeError(f'inner-update count differs from T = {T}: trace lengths {inner}, event inference_iterations {infer}')
    log = refiner.log
    diag = c1.reliability(ctx, ar, truth['coded'])
    for r, snap in enumerate(refiner.snaps, start=1):
        diag[f'eps_ce{r}'] = c1.eps_of(snap, snap['h'], a_true, n)
        diag[f'eps_det{r}'] = c1.eps_of(snap, ar[f'r{r - 1}_gains'], a_true, n)
        diag.update(c1i.decision_diag(ctx, ar, truth, r))
    s1 = refiner.snaps[0]
    proj = np.zeros(len(s1['h']), complex)
    for delay, sl in s1['taps']:
        proj[sl] = np.linalg.lstsq(s1['M'][:, sl], a_true[delay], rcond=None)[0]
    diag.update(
        mode='full', lam=None, rounds=R, eps_init=diag['eps_ce1'],
        eps_pilot1=c1.eps_of(s1, s1.get('h_pilot', s1['h']), a_true, n), eps_proj=c1.eps_of(s1, proj, a_true, n),
        first_mu_ms=refiner.first_call['mu_ms'], first_v_mean=refiner.first_call['v_mean'],
        n_cols=int(log[0]['n_cols']), n_taps_kept=int(log[0]['n_taps_kept']), s2_r1=float(log[0]['s2']),
        tau_sum_r1=float(log[0]['tau_sum']), sec_pilot=float(result.trace['acquisition_seconds']),
        sec_ce=float(sum(e['ce'] for e in events)), sec_inference=float(sum(e['inference'] for e in events)),
        R=R, T=T, inner_iters=inner, inference_iterations=infer,
        t_cum=[float(e['ready']) for e in events], sec_ce_r=[float(e['ce']) for e in events],
        sec_inf_r=[float(e['inference']) for e in events], sec_dec_r=[float(e['decoder']) for e in events])
    return dict(arm=arm, decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, diag=diag)


def run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfg):
    rows = []
    genie = sorted(set(int(x) for x in truth['l_i']))
    for arm in arms_wanted:
        try:
            res = run_arm_ib2(ctx, obs, truth, arm, genie, cfg, a_true)
            rows.append(dict(head, arm=arm, status='ok', **base.score(ctx, res, truth), **res['diag']))
        except Exception as error:  # recorded, never silently dropped
            rows.append(dict(head, arm=arm, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
    return rows


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    cells, arms_wanted, n_frames = resolve(args)
    if not args.entropy_hex:
        raise ValueError('--entropy-hex required')
    base.entropy_words(args.entropy_hex)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    for name in ('driver_c1i.py', 'driver_c1ib.py', 'driver_c1ib2.py'):
        ctx.sources[name] = base.sha256_file(HERE / name)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, c1i=c1i.C1I_PARAMS, c1ib2=IB2_PARAMS,
                  resolved=dict(cells=[[s, r, Ls] for (s, r, Ls) in cells], arms=arms_wanted, frames=n_frames),
                  code_md5=code_md5(), entropy_hex=args.entropy_hex, sp_cfg=cfg, m2_config_sha256=m2_digest,
                  dpss_defaults=dpss_rx.CFG_DEFAULT)
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment',)}
    if config_path.exists():
        previous = json.loads(config_path.read_text())
        if previous.get('_config_cmp') != json.loads(json.dumps(comparable, default=base.to_jsonable)):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable),
                                          indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = c1i.load_done(jsonl, arms_wanted)
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    n = int(ctx.system.N_total)
    all_L = sorted({L for (_, _, Ls) in cells for L in Ls})
    frames = list(range(args.frame_offset, args.frame_offset + n_frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None  # (info, noise) fingerprint: identical across L, rho, snr
            for L in all_L:
                todo = [(s, r) for (s, r, Ls) in cells if L in Ls
                        and (f'L{L:02d}', int(round(r * 1000)), int(round(s * 100)), frame) not in done]
                if not todo:
                    continue
                paths = c1.draw_c1_paths(entropy, frame, L)
                H = c1.c1_physical_h(ctx, paths)
                a_true = c1.tap_sequences(paths, n)
                e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                pair = None
                for rho in sorted({r for (_, r) in todo}):
                    msg = c1.c1_message(ctx, entropy, frame, rho)
                    raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
                    for snr in sorted({s for (s, r) in todo if r == rho}):
                        snr_centi = int(round(snr * 100))
                        raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                        obs = base.observe(raw, rho, snr_centi / 100)
                        truth = base.truth_from_raw(raw, diag_base)
                        fp = (truth['channel_seed'], truth['physical_gains_sha256'])
                        if pair is None:
                            pair = fp
                        assert fp == pair, 'pairing across rho/snr broken'
                        mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
                        if frame_fp is None:
                            frame_fp = mfp
                        assert mfp == frame_fp, 'message/noise pairing across L/rho/snr broken'
                        head = c1.head_fields(paths, truth, rho, snr_centi, frame, L)
                        rows = run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfg)
                        base.append_rows(handle, rows)
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] c1ib2 snr={snr_centi} rho={rho} L={L} frame={frame} '
                              f'P={len(truth["l_i"])} ' + ' '.join(f"{r['arm']}:{r.get('info_errors', 'E')}({r.get('seconds', 0.):.1f}s)" for r in rows),
                              flush=True)
    rows_all = [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    (out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=list(argv), _config=config, shard=args.shard, nshard=args.nshard,
        cells_run_this_invocation=n_cells, n_rows=len(rows_all),
        n_error_rows=sum(r['status'] != 'ok' for r in rows_all),
        rows_sha256=base.sha256_file(jsonl), wall_seconds=time.perf_counter() - started),
        indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    print(f'shard {args.shard} done: {len(rows_all)} rows', flush=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parse_args(argv)
    if args.mode == 'merge':
        base.merge(args, argv)
    else:
        run_shard(args, argv)


if __name__ == '__main__':
    main()
