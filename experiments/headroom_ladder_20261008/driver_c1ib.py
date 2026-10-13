#!/usr/bin/env python
"""C1 inner-update budget run (IB; task 10-08-doppler-cluster; research/c1-inner-budget.md, FROZEN 2026-10-10).

Question: does a longer inner loop (T joint updates per round instead of 20) move the round-R cliff of the unmodified SPg_flat FULL receiver?

Observations are IDENTICAL to driver_c1i FULL_R4 (same entropy 129abc..., c1 domain / streams, frame indices, rho .3, SNR 6.5 dB; the generator, seeds,
head fields, IntervenedRefine(mode='full') == GenieRefine (genie delays + flat prior, K = 8 L), eps_of, reliability, decision_diag, shard/resume/merge logic
are imported from driver / driver_c1 / driver_c1i).  Nothing frozen is edited.  The ONLY change against c1i's FULL_R4 call is `iterations = T` (applied to
every round by native.receive):
    with dpss_rx.vector_prior(ctx.native):
        ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1i_full', rounds=4, iterations=T, gain_mode='joint', refine_override=refiner)
run_arm_ib below is the minimal copy of driver_c1i.run_arm (mode 'full' branch only); IB_T20 must therefore equal the stored c1i FULL_R4 rows bit for bit.

Arms (one JSONL row per (L, rho, snr, frame, arm)):  IB_T<T>, T >= 1, rounds = 4.   Defaults: IB_T40,IB_T80; the determinism set is a separate
invocation (--arms IB_T20 --frames 30 -> out/c1ib_det).
Per row: the c1i FULL fields (eps_ce<r>, eps_det<r>, cerr<r>, ierr<r>, syn<r>, dsha<r>, ll_in<r>, r = 1..4; r1_* reliability; eps_init, eps_pilot1, eps_proj;
base.score fields incl. seconds; head fields incl. e_real) plus T, inner_iters (len of the kernel trace of each round, asserted == T) and
inference_iterations (the receiver's per-round event field, asserted == T).
Run one process per shard, single thread (launch_c1ib.sh).
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
import dpss_rx

HERE = base.HERE
ROUNDS = 4
DEFAULT_ARMS = ('IB_T40', 'IB_T80')
CODE_FILES = ('driver_c1ib.py', 'driver_c1i.py', 'driver_c1.py', 'driver.py', 'dpss_rx.py', 'tapchannel.py', 'arms.py', 'orders.py')
CODE_MODULES = ('twofft', 'native_twofft', 'messages', 'receiver', 'interventions', 'physical')
IB_PARAMS = dict(
    pairing='observations identical to driver_c1i FULL_R4 (entropy_hex 129abc..., c1 domain/streams, rho .3, snr 6.5, frames from --frame-offset); '
            'arms differ only in the inner-update count T',
    receiver='SPg_flat FULL: IntervenedRefine(mode=full) under dpss_rx.vector_prior, interventions._instrumented(rounds=4, iterations=T, gain_mode=joint); '
             'T applies to every round (native_twofft.receive loop -> scalar_joint_cols range(iterations), no early exit)',
    determinism='IB_T20 re-run must equal stored c1i FULL_R4 rows exactly (cerr, ierr, dsha, ll_in, rounds 1-4)',
    eps='eps_of semantics of driver_c1: ||H - H^||_F^2 / N')


def arm_T(arm):
    m = re.fullmatch(r'IB_T(\d+)', arm)
    if not m or int(m.group(1)) < 1:
        raise ValueError(f'unknown arm {arm} (expected IB_T<T>, T >= 1)')
    return int(m.group(1))


def md5_file(path):
    digest = hashlib.md5()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def code_md5():
    out = {name: md5_file(HERE / name) for name in CODE_FILES}
    for name in CODE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            out[f'{name}.py'] = md5_file(module.__file__)
    return out


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--Ls', default='8,12,16,20,24')
    p.add_argument('--rho-list', default='0.3')
    p.add_argument('--snr-list', default='6.5')
    p.add_argument('--frames', type=int, default=300)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--arms', default=','.join(DEFAULT_ARMS))
    p.add_argument('--entropy-hex', default=c1i.C1_MAP_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1ib'  # base.fingerprint keys cluster params on 'clustered' only
    return args


# ------------------------------------------------------------------------ receiver
def run_arm_ib(ctx, obs, truth, arm, genie_delays, cfg, a_true):
    """driver_c1i.run_arm (mode 'full') with iterations = T.  Count-blind DPSS-BEM SP receiver, genie delay support, flat prior; truth only for scoring / eps."""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    T = arm_T(arm)
    refiner = c1i.IntervenedRefine(genie_delays, cfg, mode='full', lam=None, a_true=None)
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1i_full', rounds=ROUNDS, iterations=T,
                                            gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != ROUNDS:
        raise RuntimeError(f'expected {ROUNDS} refits, got {len(refiner.snaps)}')
    inner = [len(ar[f'r{r}_inference_trace']) for r in range(ROUNDS)]
    infer = [int(e['inference_iterations']) for e in result.timing['events']]
    if inner != [T] * ROUNDS or infer != [T] * ROUNDS:
        raise RuntimeError(f'inner-update count differs from T = {T}: trace lengths {inner}, event inference_iterations {infer}')
    log = refiner.log
    diag = c1.reliability(ctx, ar, truth['coded'])
    for r, snap in enumerate(refiner.snaps, start=1):
        diag[f'eps_ce{r}'] = c1.eps_of(snap, snap['h'], a_true, n)
        diag[f'eps_det{r}'] = c1.eps_of(snap, ar[f'r{r - 1}_gains'], a_true, n)
        diag.update(c1i.decision_diag(ctx, ar, truth, r))
    s1 = refiner.snaps[0]
    proj = np.zeros(len(s1['h']), complex)  # eps_proj, as c1i for non-WARM arms
    for delay, sl in s1['taps']:
        proj[sl] = np.linalg.lstsq(s1['M'][:, sl], a_true[delay], rcond=None)[0]
    diag.update(
        mode='full', lam=None, rounds=ROUNDS, eps_init=diag['eps_ce1'],
        eps_pilot1=c1.eps_of(s1, s1.get('h_pilot', s1['h']), a_true, n), eps_proj=c1.eps_of(s1, proj, a_true, n),
        first_mu_ms=refiner.first_call['mu_ms'], first_v_mean=refiner.first_call['v_mean'],
        n_cols=int(log[0]['n_cols']), n_taps_kept=int(log[0]['n_taps_kept']), s2_r1=float(log[0]['s2']),
        tau_sum_r1=float(log[0]['tau_sum']), sec_pilot=float(result.trace['acquisition_seconds']),
        sec_ce=float(sum(e['ce'] for e in result.timing['events'])),
        sec_inference=float(sum(e['inference'] for e in result.timing['events'])),
        T=T, inner_iters=inner, inference_iterations=infer)
    return dict(arm=arm, decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, diag=diag)


def run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfg):
    rows = []
    genie = sorted(set(int(x) for x in truth['l_i']))
    for arm in arms_wanted:
        try:
            res = run_arm_ib(ctx, obs, truth, arm, genie, cfg, a_true)
            rows.append(dict(head, arm=arm, status='ok', **base.score(ctx, res, truth), **res['diag']))
        except Exception as error:  # recorded, never silently dropped
            rows.append(dict(head, arm=arm, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
    return rows


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    arms_wanted = base.parse_list(args.arms, str)
    for arm in arms_wanted:
        arm_T(arm)
    Ls = base.parse_list(args.Ls, int)
    rhos = base.parse_list(args.rho_list, float)
    if any(L < 1 or L > 101 for L in Ls):
        raise ValueError('unknown L')
    if not args.frames or not args.entropy_hex:
        raise ValueError('--frames and --entropy-hex required')
    base.entropy_words(args.entropy_hex)
    snr_cells = [int(round(float(x) * 100)) for x in base.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    ctx.sources['driver_c1i.py'] = base.sha256_file(HERE / 'driver_c1i.py')
    ctx.sources['driver_c1ib.py'] = base.sha256_file(HERE / 'driver_c1ib.py')
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, c1i=c1i.C1I_PARAMS, c1ib=IB_PARAMS,
                  c1ib_default_arms=list(DEFAULT_ARMS), rounds=ROUNDS, code_md5=code_md5(), entropy_hex=args.entropy_hex,
                  sp_cfg=cfg, m2_config_sha256=m2_digest, dpss_defaults=dpss_rx.CFG_DEFAULT)
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
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None  # (info, noise) fingerprint: identical across L, rho, snr
            for L in Ls:
                cfg_name = f'L{L:02d}'
                todo = [(rho, s) for rho in rhos for s in snr_cells
                        if (cfg_name, int(round(rho * 1000)), s, frame) not in done]
                if not todo:
                    continue
                paths = c1.draw_c1_paths(entropy, frame, L)
                H = c1.c1_physical_h(ctx, paths)
                a_true = c1.tap_sequences(paths, n)
                e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                pair = None
                for rho in rhos:
                    todo_r = [s for (r, s) in todo if r == rho]
                    if not todo_r:
                        continue
                    msg = c1.c1_message(ctx, entropy, frame, rho)
                    raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
                    for snr_centi in todo_r:
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
                        print(f'[{time.perf_counter() - started:8.1f}s] c1ib L={L} rho={rho} snr={snr_centi} frame={frame} '
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
