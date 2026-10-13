#!/usr/bin/env python
"""F2 order test driver (task 10-08-doppler-cluster).  Uses the F1 generator of driver.py UNCHANGED
(same CL_DOMAIN, same entropy => frames pair bit-for-bit with F1 at overlapping SNR) and adds arms.

Arms (one JSONL row per (config, snr, frame, arm); A0 also emits F0 as in F1; PS also emits PS0)
  A0  production B = F0 + TF + CSTATE20 on trigger          (driver.run_a0, as F1)
  A3  true H fixed, TF20R2                                   (driver.run_a3, as F1)
  PS  strongest existing multi-slot-per-delay parametric receiver = Stage-A arm D:
      native_f1.receive_f1 (PhysicalF1.acquire + keep_slots.time_refine_keep_slots + scalar_joint + LDPC, 2 rounds)
      then CSTATE20 branch iff final native syndrome != 0 (run_stage_a.py arm D).  PS0 = same without continuation
      (Stage-A arm C).  Used unchanged, count-blind (8-slot cap, up to 25 Doppler centres per delay in the bank).
  O1 O2 O3 O5  oracle representation ladder (orders.py): true delays, D sub-paths at the power-weighted Doppler
      centroid + (k-(D-1)/2)*1.0 bin, LS gains of the true tap sequence; detection = fixed-H TF20R2 (same as A3).
Nothing frozen is edited.  Run one process per shard, single thread (launch_f2.sh).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

import driver as base
import orders

HERE = base.HERE
F2_ARMS = ('A0', 'A3', 'PS', 'O1', 'O2', 'O3', 'O5')
ORACLE_ORDER = {'O1': 1, 'O2': 2, 'O3': 3, 'O5': 5}
STAGE_A_DIR = 'cstate_necessity_stageA_20260928'
F2_CONFIGS = ('D1', 'N4a', 'N4b', 'J4')
F2_SPEC = dict(
    ps='native_f1.receive_f1 (PhysicalF1(1024,c1,c2,102).acquire -> time_refine_keep_slots x2 rounds -> scalar_joint '
       'joint-gain TF20 -> LDPC50) + CSTATE20 branch iff final syndrome != 0 (run_stage_a.py arm D); PS0 = arm C',
    ps_slot_budget='max 8 slots (acquire loop range(8), time_refine_keep_slots max_paths=8); bank = 103 delays x 25 '
                   'Doppler centres (-3..3 step .25); duplicate = same delay and |dnu|<1e-6 only, so >1 slot per delay allowed',
    oracle='true delays; D sub-paths at power-weighted centroid + (k-(D-1)/2)*1.0 bin; LS gains over n=0..N-1; '
           'detection = interventions.run_fixed_channel(detector=tf); misfit = sum_l||a_l-fit_l||^2/sum_l||a_l||^2 '
           '(= ||H-H_D||_F^2/||H||_F^2, checked against explicit matrices)',
    oracle_orders=ORACLE_ORDER)


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--stagea-dir', default=STAGE_A_DIR)
    p.add_argument('--snr-list', default='6,7,8,9,10,11,12')
    p.add_argument('--frames', type=int, default=0)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--arms', default=','.join(F2_ARMS))
    p.add_argument('--entropy-hex', default='')
    p.add_argument('--configs', default=','.join(F2_CONFIGS))
    p.add_argument('--matrix-check-every', type=int, default=100,
                   help='explicit-H misfit cross-check on frames with frame %% k == 0 at the lowest SNR (0 = off)')
    args = p.parse_args(argv)
    args.channel_model = 'clustered'  # base.fingerprint keys cluster params on this
    return args


# ---------------------------------------------------------------------- context
def load_context(args):
    stage_a = args.project.resolve() / 'experiments' / args.stagea_dir
    if not stage_a.is_dir():
        raise FileNotFoundError(str(stage_a))
    sys.path.insert(0, str(stage_a))  # base.setup_paths prepends its own dirs ahead of this one
    ctx = base.load_context(args)
    from native_f1 import receive_f1
    ctx.receive_f1 = receive_f1
    for name in ('f1.py', 'keep_slots.py', 'native_f1.py'):
        ctx.sources['stageA/' + name] = base.sha256_file(stage_a / name)
    ctx.sources['driver_f2.py'] = base.sha256_file(HERE / 'driver_f2.py')
    ctx.sources['orders.py'] = base.sha256_file(HERE / 'orders.py')
    return ctx


# ------------------------------------------------------------------------- arms
def run_ps(ctx, obs):
    """Stage-A arm D (PS) and arm C (PS0) from one F1 prefix.  Branch failure -> PS result carries 'error'."""
    start = time.perf_counter()
    dec0, arrays, timing = ctx.receive_f1(obs, ctx.system, ctx.code)
    f1_seconds = time.perf_counter() - start
    syn0 = base.syndrome_weight(ctx, dec0['decoded'])
    acq = timing['acquisition']
    common = dict(fit_delays=np.asarray(arrays['r1_delays']), fit_dopplers=np.asarray(arrays['r1_dopplers']),
                  f0_syndrome=syn0, ps_stopping_reason=str(acq['stopping_reason']),
                  ps_acq_seconds=float(timing['pilot_seconds']))
    ps0 = dict(arm='PS0', decoded=dec0['decoded'], llr=dec0['incoming_llr'], iters=int(dec0['iterations']),
               seconds=f1_seconds, triggered=None, **common)
    if syn0 == 0:
        ps = dict(ps0, arm='PS', triggered=False, seconds=time.perf_counter() - start)
        return [ps0, ps]
    try:
        branch = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, 'CSTATE20')
        final = branch['decoder']
        ps = dict(arm='PS', decoded=final['decoded'], llr=final['incoming_llr'], iters=int(final['iterations']),
                  seconds=time.perf_counter() - start, triggered=True, **common)
    except Exception as error:  # recorded as an error row for PS only; PS0 stays valid
        ps = dict(arm='PS', error=repr(error), trace=traceback.format_exc()[-1500:])
    return [ps0, ps]


def run_oracle(ctx, obs, truth, order):
    n = len(obs['y'])
    ls, nus, gs, misfit = orders.oracle_paths(truth['l_i'], truth['k_real'], truth['g_i'], order, n)
    channel = ctx.Channel(n, ctx.system.c1, ctx.system.c2, ls, nus, gs)
    start = time.perf_counter()
    result = ctx.wrappers.run_fixed_channel(obs, ctx.system, ctx.code, ctx.native, channel=channel, detector='tf')
    seconds = time.perf_counter() - start
    d = result.decoder
    return [dict(arm=f'O{order}', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']),
                 seconds=seconds, triggered=None, misfit=float(misfit), oracle_order=order,
                 oracle_n_paths=int(len(ls)), oracle_paths=(ls, nus, gs))]


def explicit_misfit(ctx, truth, paths):
    """||H_true - H_alt||_F^2/||H_true||_F^2 from explicit physical matrices (cross-check of orders.py identity)."""
    s = ctx.system
    n, prefix = int(s.N_total), int(s.l_max_cap)
    ht = ctx.physical_channel_matrix(n, s.c1, s.c2, truth['l_i'], truth['k_real'], truth['g_i'], prefix_length=prefix)
    ha = ctx.physical_channel_matrix(n, s.c1, s.c2, *paths, prefix_length=prefix)
    return float(np.linalg.norm(ht - ha) ** 2 / np.linalg.norm(ht) ** 2)


def ps_geometry_fields(truth, res, ctx):
    """Slot budget / placement of the PS fit relative to the true taps (descriptive)."""
    fd = np.asarray(res['fit_delays'], int)
    counts = {int(d): int(np.count_nonzero(fd == d)) for d in np.unique(fd)}
    true_taps = [int(d) for d in np.unique(truth['l_i'])]
    lost, underfit = ctx.arms.missed_energy(truth['l_i'], truth['k_real'], truth['g_i'], fd)
    return dict(ps_n_slots=int(len(fd)), ps_n_fit_delays=len(counts), ps_max_slots_per_delay=max(counts.values()),
                ps_n_multi_slot_delays=sum(c > 1 for c in counts.values()),
                ps_taps_covered=sum(d in counts for d in true_taps),
                ps_slots_off_truth_delays=int(sum(c for d, c in counts.items() if d not in true_taps)),
                ps_missed_energy_fraction=float(lost), ps_same_delay_underfit=bool(underfit),
                ps_stopping_reason=res['ps_stopping_reason'], ps_acq_seconds=res['ps_acq_seconds'],
                ps_f0_syndrome=int(res['f0_syndrome']),
                fit_delays=[int(x) for x in fd], fit_dopplers=[float(x) for x in res['fit_dopplers']])


def run_cell_f2(ctx, arms_wanted, obs, truth, snr_centi, frame, matrix_check):
    rows = []
    shared = [a for a in ('A0', 'A3') if a in arms_wanted]
    if shared:  # byte-identical row schema/values to F1 (F0, A0, A3)
        rows += base.run_cell(ctx, shared, obs, truth, .5, snr_centi, frame)
    head = dict(rho=.5, rho_permille=500, snr_centi_db=int(snr_centi), snr_db=snr_centi / 100, frame=int(frame),
                **base.truth_summary(truth))
    head.update(base.cluster_row_fields(truth))
    for key in ('truth_l', 'truth_k', 'truth_g2'):
        head.pop(key, None)  # heavy per-ray lists live on the A0 row only
    for arm in F2_ARMS:
        if arm not in arms_wanted or arm in ('A0', 'A3'):
            continue
        try:
            results = run_ps(ctx, obs) if arm == 'PS' else run_oracle(ctx, obs, truth, ORACLE_ORDER[arm])
        except Exception as error:
            rows.append(dict(head, arm=arm, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
            continue
        for res in results:
            if 'error' in res:
                rows.append(dict(head, arm=res['arm'], status='error', error=res['error'], trace=res['trace']))
                continue
            row = dict(head, arm=res['arm'], status='ok', **base.score(ctx, res, truth))
            if res['arm'] in ('PS0', 'PS'):
                row.update(ps_geometry_fields(truth, res, ctx))
            if res['arm'].startswith('O'):
                row.update(misfit=res['misfit'], oracle_order=res['oracle_order'],
                           oracle_n_paths=res['oracle_n_paths'])
                if matrix_check:
                    mm = explicit_misfit(ctx, truth, res['oracle_paths'])
                    row.update(misfit_matrix=mm, misfit_matrix_abs_diff=abs(mm - res['misfit']))
            rows.append(row)
    return rows


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    arms_wanted = base.parse_list(args.arms, str)
    configs = base.parse_list(args.configs, str)
    if not set(arms_wanted) <= set(F2_ARMS) or not set(configs) <= set(base.CLUSTER_CONFIGS):
        raise ValueError('unknown arm or config')
    if not args.frames or not args.entropy_hex:
        raise ValueError('--frames and --entropy-hex required')
    base.entropy_words(args.entropy_hex)
    snr_cells = [int(round(float(x) * 100)) for x in base.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ctx = load_context(args)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(f2=F2_SPEC, f2_arms=list(F2_ARMS))
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
    done = base.load_done(jsonl)
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    low = min(snr_cells)
    with jsonl.open('a') as handle:
        for frame in frames:
            msg = None
            for cfg_name in configs:
                todo = [s for s in snr_cells if (cfg_name, 500, s, frame) not in done]
                if not todo:
                    continue
                if msg is None:
                    msg = base.cluster_message(ctx, entropy, frame)
                raw_base, diag_base = base.cluster_base(ctx, msg, base.draw_cluster_geometry(entropy, frame), cfg_name)
                pair = None
                for snr_centi in todo:
                    raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                    obs = base.observe(raw, .5, snr_centi / 100)
                    truth = base.truth_from_raw(raw, diag_base)
                    fp = (truth['channel_seed'], truth['physical_gains_sha256'],
                          hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(),
                          truth['noise_sha256'])
                    if pair is None:
                        pair = fp
                    assert fp == pair, 'pairing across snr broken'
                    check = bool(args.matrix_check_every) and frame % args.matrix_check_every == 0 and snr_centi == low
                    rows = run_cell_f2(ctx, arms_wanted, obs, truth, snr_centi, frame, check)
                    base.append_rows(handle, rows)
                    n_cells += 1
                    print(f'[{time.perf_counter() - started:8.1f}s] f2 {cfg_name} snr={snr_centi} frame={frame} '
                          f'P={len(truth["l_i"])} ' + ' '.join(f"{r['arm']}:{r.get('info_errors', 'E')}" for r in rows),
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
