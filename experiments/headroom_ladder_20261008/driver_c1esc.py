#!/usr/bin/env python
"""C1 escalation schedules for the A' online-scheduling test (task 10-08-doppler-cluster; research/c1-escalation-A-prime.md, FROZEN).

Question: does "start at T = 20 inner updates, escalate to T = 40 when the frame is not decoded by round e" realise the per-frame
T-choice part of the oracle headroom found in T1 (c1-online-headroom-T123.md)?  With syndrome early stop, frames decoded by
round e never escalate, so the policy equals the fixed per-round schedule [20]*e + [40]*(R - e); early stop, round cap and the
give-up rule are applied afterwards from the per-round syndromes (c1esc_analyze.py).

Receiver: SPg_flat FULL (genie delays, flat prior, K = 8L), rounds R = 10, unchanged except the inner-update count of round r,
which a thin wrapper over the routed native.scalar_joint sets from the schedule (call r of the native loop = round r).
Arms  E<e>: T = 20 in rounds 1..e, T = 40 afterwards.  E10 = all 20 (must equal the stored FULL_R10 rows), E0 = all 40 (must
equal the stored R10T40 rows); E1, E2, E3 = escalation arms.  Per-round inner trace length is asserted equal to the schedule.
Row fields: driver_c1ib2 fields per round (cerr/ierr/syn/dsha/ll_in, eps_ce/eps_det, t_cum, sec_*_r) + schedule.
Observations identical to driver_c1 / driver_c1ib2 for the same (entropy 129abc..., frame, L, rho, SNR).
Preset main: 6.5 dB, rho .3, L {16, 20}, frames 0-599, arms E10, E0, E1, E2, E3.  Run one single-thread process per shard.

--shuffle-arms (A'/(b) strict run, research/aprime-b-manifest-20261013.md; default off = old behaviour, rows bit-identical):  per (frame, L) the
arm execution order is a permutation drawn by np.random.default_rng(SeedSequence(entropy_words + [0x41505242 ('APRB'), frame, L])).permutation(n)
of the arm list as given on the command line; recorded per row as `arm_order` (list) and `arm_rank` (position of the row's arm).
Timing balance only; no numeric of any arm changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
import driver_c1ib2 as ib2
import dpss_rx

HERE = base.HERE
CODE_FILES = ('driver_c1esc.py', 'driver_c1ib2.py', 'driver_c1ib.py', 'driver_c1i.py', 'driver_c1.py', 'driver.py', 'dpss_rx.py',
              'tapchannel.py', 'arms.py', 'orders.py')
ROUNDS, T_LO, T_HI = 10, 20, 40
ARM_ORDER_DOMAIN = 0x41505242  # ASCII 'APRB'
PRESETS = {'main': dict(cells=[(6.5, 0.3, [16, 20])], arms=['E10', 'E0', 'E1', 'E2', 'E3'], frames=600)}
ESC_PARAMS = dict(
    pairing='observations identical to driver_c1 / driver_c1ib2 for the same (entropy_hex 129abc..., frame, L, rho, SNR)',
    receiver='SPg_flat FULL (genie delays, flat prior, K = 8 L), rounds 10; inner-update count of round r set by the schedule through '
             'a wrapper over the routed native.scalar_joint; nothing else changed',
    arms='E<e>: T = 20 in rounds 1..e, 40 afterwards; E10 = all 20, E0 = all 40',
    eps='eps_of semantics of driver_c1: ||H - H^||_F^2 / N')


def schedule(arm):
    m = re.fullmatch(r'E(\d+)', arm)
    if not m or not 0 <= int(m.group(1)) <= ROUNDS:
        raise ValueError(f'unknown arm {arm} (expected E<e>, 0 <= e <= {ROUNDS})')
    e = int(m.group(1))
    return [T_LO] * e + [T_HI] * (ROUNDS - e)


def shuffled_arms(entropy_hex, frame, L, arms):
    """Execution order of the arms for (frame, L): permutation from SeedSequence(entropy_words + [APRB, frame, L])."""
    rng = np.random.default_rng(np.random.SeedSequence(base.entropy_words(entropy_hex) + [ARM_ORDER_DOMAIN, int(frame), int(L)]))
    return [arms[int(i)] for i in rng.permutation(len(arms))]


def run_arm_esc(ctx, obs, truth, arm, genie_delays, cfg, a_true):
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    sched = schedule(arm)
    refiner = c1i.IntervenedRefine(genie_delays, cfg, mode='full', lam=None, a_true=None)
    used = []
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        routed = ctx.native.scalar_joint

        def scheduled(*args, **kwargs):
            if 'iterations' not in kwargs or len(used) >= ROUNDS:
                raise RuntimeError('unexpected scalar_joint call (iterations not a keyword, or more calls than rounds)')
            kwargs['iterations'] = sched[len(used)]
            used.append(sched[len(used)])
            return routed(*args, **kwargs)

        ctx.native.scalar_joint = scheduled
        try:
            result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1i_full', rounds=ROUNDS, iterations=sched[0],
                                                gain_mode='joint', refine_override=refiner)
        finally:
            ctx.native.scalar_joint = routed
    seconds = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != ROUNDS or used != sched:
        raise RuntimeError(f'schedule not applied: refits {len(refiner.snaps)}, used {used}')
    inner = [len(ar[f'r{r}_inference_trace']) for r in range(ROUNDS)]
    if inner != sched:
        raise RuntimeError(f'inner trace lengths {inner} differ from schedule {sched}')
    events = result.timing['events']
    diag = c1.reliability(ctx, ar, truth['coded'])
    for r, snap in enumerate(refiner.snaps, start=1):
        diag[f'eps_ce{r}'] = c1.eps_of(snap, snap['h'], a_true, n)
        diag[f'eps_det{r}'] = c1.eps_of(snap, ar[f'r{r - 1}_gains'], a_true, n)
        diag.update(c1i.decision_diag(ctx, ar, truth, r))
    diag.update(R=ROUNDS, schedule=sched, inner_iters=inner, sec_pilot=float(result.trace['acquisition_seconds']),
                t_cum=[float(e['ready']) for e in events], sec_ce_r=[float(e['ce']) for e in events],
                sec_inf_r=[float(e['inference']) for e in events], sec_dec_r=[float(e['decoder']) for e in events],
                dec_iters_r=[int(e['decoder_iterations']) for e in events])
    return dict(arm=arm, decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds, triggered=None, diag=diag)


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--preset', choices=tuple(PRESETS), default=None)
    p.add_argument('--cells', default=None, help="'snr:rho:L,L,...;...' (overrides the preset)")
    p.add_argument('--arms', default=None, help='comma list of E<e> (overrides the preset)')
    p.add_argument('--frames', type=int, default=None)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--shuffle-arms', action='store_true', help='per (frame, L) permuted arm execution order (APRB stream); default off')
    p.add_argument('--entropy-hex', default=c1i.C1_MAP_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1esc'  # base.fingerprint keys cluster params on 'clustered' only
    return args


def resolve(args):
    pre = PRESETS.get(args.preset, {})
    cells = ib2.parse_cells(args.cells) if args.cells else pre.get('cells')
    arms = base.parse_list(args.arms, str) if args.arms else pre.get('arms')
    frames = args.frames if args.frames else pre.get('frames')
    if not cells or not arms or not frames:
        raise ValueError('give --preset or all of --cells --arms --frames')
    for arm in arms:
        schedule(arm)
    if any(L < 1 or L > 101 for (_, _, Ls) in cells for L in Ls):
        raise ValueError('unknown L')
    return cells, arms, int(frames)


def code_md5():
    out = {name: ib.md5_file(HERE / name) for name in CODE_FILES}
    for name in ib.CODE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            out[f'{name}.py'] = ib.md5_file(module.__file__)
    return out


# --------------------------------------------------------------------- shard i/o (driver_c1ib2.run_shard with E<e> arms)
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    cells, arms_wanted, n_frames = resolve(args)
    base.entropy_words(args.entropy_hex)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    for name in ('driver_c1i.py', 'driver_c1ib.py', 'driver_c1ib2.py', 'driver_c1esc.py'):
        ctx.sources[name] = base.sha256_file(HERE / name)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, c1i=c1i.C1I_PARAMS, c1esc=ESC_PARAMS,
                  resolved=dict(cells=[[s, r, Ls] for (s, r, Ls) in cells], arms=arms_wanted, frames=n_frames,
                                schedules={a: schedule(a) for a in arms_wanted}),
                  code_md5=code_md5(), entropy_hex=args.entropy_hex, sp_cfg=cfg, m2_config_sha256=m2_digest,
                  dpss_defaults=dpss_rx.CFG_DEFAULT)
    if args.shuffle_arms:
        config.update(arm_order_stream=f'SeedSequence(entropy_words + [{ARM_ORDER_DOMAIN:#x}, frame, L]).permutation(len(arms)) over the arm list as given',
                      arm_order_domain=ARM_ORDER_DOMAIN)
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
    load_start = list(os.getloadavg())
    n_cells = 0
    entropy = args.entropy_hex
    all_L = sorted({L for (_, _, Ls) in cells for L in Ls})
    frames = list(range(args.frame_offset, args.frame_offset + n_frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None
            for L in all_L:
                todo = [(s, r) for (s, r, Ls) in cells if L in Ls
                        and (f'L{L:02d}', int(round(r * 1000)), int(round(s * 100)), frame) not in done]
                if not todo:
                    continue
                paths = c1.draw_c1_paths(entropy, frame, L)
                H = c1.c1_physical_h(ctx, paths)
                a_true = c1.tap_sequences(paths, int(ctx.system.N_total))
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
                        genie = sorted(set(int(x) for x in truth['l_i']))
                        rows = []
                        order = shuffled_arms(entropy, frame, L, arms_wanted) if args.shuffle_arms else list(arms_wanted)
                        extra = dict(arm_order=order) if args.shuffle_arms else {}
                        for rank, arm in enumerate(order):
                            if args.shuffle_arms:
                                extra['arm_rank'] = rank
                            try:
                                res = run_arm_esc(ctx, obs, truth, arm, genie, cfg, a_true)
                                rows.append(dict(head, arm=arm, status='ok', **base.score(ctx, res, truth), **res['diag'], **extra))
                            except Exception as error:  # recorded, never silently dropped
                                rows.append(dict(head, arm=arm, status='error', error=repr(error), trace=traceback.format_exc()[-1500:], **extra))
                        base.append_rows(handle, rows)
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] c1esc snr={snr_centi} rho={rho} L={L} frame={frame} '
                              + ' '.join(f"{r['arm']}:{r.get('info_errors', 'E')}({r.get('seconds', 0.):.1f}s)" for r in rows), flush=True)
    rows_all = [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    (out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=list(argv), _config=config, shard=args.shard, nshard=args.nshard,
        cells_run_this_invocation=n_cells, n_rows=len(rows_all),
        n_error_rows=sum(r['status'] != 'ok' for r in rows_all),
        rows_sha256=base.sha256_file(jsonl), wall_seconds=time.perf_counter() - started,
        loadavg_start=load_start, loadavg_end=list(os.getloadavg())),
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
