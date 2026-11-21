#!/usr/bin/env python
"""Frozen C1 inner-loop acceleration headroom screen (six paired cells, R=1)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback

import numpy as np

import driver as base
import driver_c1 as c1
import driver_c1B as b
import c1B_rx
import c1ACC_rx

HERE = base.HERE
# Reuse every B observation stream. The arm-order stream is separate below.
ENTROPY = b.ENTROPY
CELLS = b.CELLS
FRAMES = tuple(range(32))
ARMS = ('BASE20', 'BASE25', 'BASE30', 'BASE40', 'DAMP20', 'AA2', 'AA4', 'ADPT')
SPEC = {
    'schema': 'c1-acc-headroom-20261014-v1',
    'observation_entropy_sha256': ENTROPY,
    'arm_order_component': 'C1-ACC-ARM-ORDER-20261014-v1',
    'cells_snr_rho_L': [list(cell) for cell in CELLS], 'frames': [0, 32], 'rounds': 1,
    'arms': list(ARMS), 'reference_damping': .3, 'damp_control': .5,
    'anderson_memory': {'AA2': 2, 'AA4': 4},
    'anderson_mixing': 1., 'anderson_tikhonov': 1e-8,
    'adaptive_initial': .3, 'adaptive_increase': 1.25,
    'adaptive_decrease': .5, 'adaptive_min': .1, 'adaptive_max': .9,
}
PAIR_FIELDS = ('physical_gains_sha256', 'info_sha256', 'noise_sha256',
               'observation_y_sha256', 'observation_pilot_sha256',
               'observation_sigma2')


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    args = p.parse_args(argv)
    args.channel_model = 'c1B'
    if not (1 <= args.nshard <= 32 and 0 <= args.shard < args.nshard):
        raise ValueError('shards must be 1..32 and shard must be in range')
    return args


def arm_spec(arm):
    if arm in ('BASE20', 'BASE25', 'BASE30', 'BASE40'):
        return 'OFF', int(arm[4:]), .3
    if arm == 'DAMP20':
        return 'OFF', 20, .5
    if arm in ('AA2', 'AA4', 'ADPT'):
        return arm, 20, .3
    raise ValueError(f'unregistered arm {arm}')


def arm_order(cell_index, frame):
    if not (0 <= cell_index < len(CELLS) and frame in FRAMES):
        raise ValueError('arm-order coordinate outside registered scope')
    seed = hashlib.sha256(bytes.fromhex(ENTROPY) +
                          b'C1-ACC-ARM-ORDER-20261014-v1' +
                          cell_index.to_bytes(2, 'little') +
                          frame.to_bytes(2, 'little')).digest()
    rng = np.random.default_rng(np.random.SeedSequence(np.frombuffer(seed, dtype='<u4')))
    return tuple(ARMS[i] for i in rng.permutation(len(ARMS)))


def order_sha256(order):
    return hashlib.sha256(json.dumps(list(order), separators=(',', ':')).encode()).hexdigest()


def assigned_pairs(shard, nshard):
    return [(ci, frame) for ci in range(len(CELLS)) for frame in FRAMES
            if (ci * len(FRAMES) + frame) % nshard == shard]


def run_arm(ctx, obs, truth, arm, genie, cfg, a_true):
    mode, iterations, damping = arm_spec(arm)
    reference = mode == 'OFF'
    gains = []

    def observer(snapshot):
        gains.append(np.asarray(snapshot['h'], complex).copy())

    refiner = c1.GenieRefine(genie, 'flat', cfg)
    started = time.perf_counter()
    route = (c1B_rx.route(ctx.native, mode='BASE', damping=damping, observer=observer)
             if reference else c1ACC_rx.route(ctx.native, mode=mode, damping=damping, observer=observer))
    with route:
        result = ctx.wrappers._instrumented(
            ctx.native, obs, ctx.system, ctx.code, arm='c1j12_round1', rounds=1,
            iterations=iterations, gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - started
    if len(refiner.snaps) != 1:
        raise RuntimeError(f'expected one genie refit, got {len(refiner.snaps)}')
    arrays = result.arrays
    trace = arrays['r0_inference_trace']
    if len(gains) != iterations or len(trace) != iterations:
        raise RuntimeError(f'expected {iterations} committed updates, got {len(gains)} gains/{len(trace)} traces')
    if reference:
        # Frozen B BASE arithmetic and clock. These counts are the B map's
        # registered two FFTs per committed update plus the initial Y FFT.
        trace = [dict(step, overhead_seconds=0., map_evaluations=1) for step in trace]
    if any(not {'overhead_seconds', 'map_evaluations', 'fft_count'} <= set(step) for step in trace):
        raise RuntimeError('ACC step accounting absent from receiver trace')
    h_t = np.asarray(arrays['r0_gains'], complex)
    snap = refiner.snaps[0]
    h_o, norm = b.truth_projection(snap, a_true)
    diag = c1.reliability(ctx, arrays, truth['coded'])
    diag.update(
        n_cols=len(h_t),
        eps_ce1=c1.eps_of(snap, snap['h'], a_true, len(obs['y'])),
        eps_det1=c1.eps_of(snap, h_t, a_true, len(obs['y'])),
        sec_pilot=float(result.trace['acquisition_seconds']),
        sec_ce=float(sum(e['ce'] for e in result.timing['events'])),
        sec_inference=float(sum(e['inference'] for e in result.timing['events'])),
        orthogonal_trajectory=[b.perp_energy(h, h_o, norm) for h in gains],
        orthogonal_risk=b.perp_energy(h_t, h_o, norm),
        trace=trace,
        per_step_overhead_seconds=[float(step['overhead_seconds']) for step in trace],
        overhead_seconds=float(sum(step['overhead_seconds'] for step in trace)),
        map_evaluations=int(sum(step['map_evaluations'] for step in trace)),
        fft_count=1 + int(sum(step['fft_count'] for step in trace)),
        committed_iterations=len(trace),
    )
    return dict(arm=arm, decoded=result.decoder['decoded'], llr=result.decoder['incoming_llr'],
                iters=int(result.decoder['iterations']), seconds=seconds,
                triggered=None, diag=diag)


def manifest(args, ctx, cfg_digest):
    names = ('driver_c1ACC.py', 'c1ACC_rx.py', 'driver_c1B.py', 'c1B_rx.py',
             'driver_c1.py', 'driver.py', 'dpss_rx.py', 'tapchannel.py', 'orders.py')
    sources = {name: base.sha256_file(HERE / name) for name in names}
    sources.update(ctx.sources)
    return dict(spec=SPEC, cfg_sha256=cfg_digest, sources=sources,
                code_g_sha256=ctx.header['code_g_sha256'],
                args=dict(project=str(args.project), native_dir=args.native_dir,
                          baseline_dir=args.baseline_dir, m2_config=str(args.m2_config),
                          nshard=args.nshard, mode='generate'))


def validate_row(row, ci, frame, arm, order):
    if (row.get('cell'), row.get('frame'), row.get('arm')) != (ci + 1, frame, arm):
        raise ValueError(f'row coordinate mismatch at {(ci + 1, frame, arm)}')
    if (row.get('arm_order') != list(order) or row.get('arm_order_sha256') != order_sha256(order)
            or row.get('arm_position') != order.index(arm)):
        raise ValueError(f'arm order mismatch at {(ci + 1, frame, arm)}')
    if row.get('status') not in ('ok', 'error'):
        raise ValueError(f'invalid status at {(ci + 1, frame, arm)}')
    if not isinstance(row.get('seconds'), (int, float)) or row['seconds'] < 0 or not np.isfinite(row['seconds']):
        raise ValueError(f'invalid receiver time at {(ci + 1, frame, arm)}')
    if row['status'] == 'ok':
        if not all(key in row for key in ('orthogonal_risk', 'info_errors', 'logloss_bits',
                                          'map_evaluations', 'fft_count', 'committed_iterations',
                                          'per_step_overhead_seconds', 'orthogonal_trajectory')):
            raise ValueError(f'incomplete success row at {(ci + 1, frame, arm)}')
    elif not all(key in row for key in ('error', 'traceback')):
        raise ValueError(f'incomplete error row at {(ci + 1, frame, arm)}')


def read_rows(path, shard, nshard, *, require_complete=False):
    rows = {}
    encountered = {}
    sequence = []
    assigned = assigned_pairs(shard, nshard)
    assigned_set = set(assigned)
    if path.exists():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            ci, frame, arm = row['cell'] - 1, row['frame'], row['arm']
            if (ci, frame) not in assigned_set or arm not in ARMS:
                raise ValueError(f'saved row outside assigned scope: {(ci, frame, arm)}')
            key = (ci, frame, arm)
            if key in rows:
                raise ValueError(f'duplicate saved row: {key}')
            validate_row(row, ci, frame, arm, arm_order(ci, frame))
            rows[key] = row
            encountered.setdefault((ci, frame), []).append(arm)
            sequence.append(key)
    for ci, frame in assigned:
        order = arm_order(ci, frame)
        seen = encountered.get((ci, frame), [])
        if seen != list(order[:len(seen)]):
            raise ValueError(f'non-prefix resume at cell {ci + 1}, frame {frame}')
    required = {(ci, frame, arm) for ci, frame in assigned for arm in ARMS}
    scheduled = [(ci, frame, arm) for ci, frame in assigned for arm in arm_order(ci, frame)]
    if sequence != scheduled[:len(sequence)]:
        raise ValueError(f'shard {shard} rows do not follow registered execution order')
    if require_complete and set(rows) != required:
        raise ValueError(f'shard {shard} incomplete: {len(rows)} of {len(required)}')
    return rows


def run_shard(args):
    cfgs, cfg_digest, _ = c1.load_cfgs(args)
    ctx = c1.load_context(args)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    expected = manifest(args, ctx, cfg_digest)
    config_path = out / f'config_shard{args.shard:03d}.json'
    path = out / f'rows_shard{args.shard:03d}.jsonl'
    receipt_path = out / f'results_shard{args.shard:03d}.json'
    if path.exists() and not config_path.exists():
        raise ValueError('resume refused: rows exist without source/config manifest')
    if config_path.exists():
        if json.loads(config_path.read_text()) != expected:
            raise ValueError('resume refused: source/config manifest mismatch')
    else:
        config_path.write_text(json.dumps(expected, indent=1, allow_nan=False) + '\n')
    completed = read_rows(path, args.shard, args.nshard)
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        read_rows(path, args.shard, args.nshard, require_complete=True)
        if (receipt.get('schema') != SPEC['schema'] or receipt.get('shard') != args.shard
                or receipt.get('nshard') != args.nshard or receipt.get('rows') != len(completed)
                or receipt.get('errors') != sum(r['status'] != 'ok' for r in completed.values())
                or receipt.get('manifest_sha256') != base.sha256_file(config_path)
                or receipt.get('rows_sha256') != base.sha256_file(path)):
            raise ValueError('resume refused: completed shard receipt differs')
        return
    started = time.perf_counter()
    with path.open('a') as stream:
        for ci, frame in assigned_pairs(args.shard, args.nshard):
            order = arm_order(ci, frame)
            pending = [arm for arm in order if (ci, frame, arm) not in completed]
            if not pending:
                continue
            snr, rho, L = CELLS[ci]
            paths = c1.draw_c1_paths(ENTROPY, frame, L)
            H = c1.c1_physical_h(ctx, paths)
            a_true = c1.tap_sequences(paths, int(ctx.system.N_total))
            msg = c1.c1_message(ctx, ENTROPY, frame, rho)
            raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
            raw = base.cluster_at_snr(raw_base, snr)
            obs = base.observe(raw, rho, snr)
            truth = base.truth_from_raw(raw, diag_base)
            head = dict(b.fp_head(paths, truth, rho, snr, frame, L, obs), cell=ci + 1,
                        arm_order=list(order), arm_order_sha256=order_sha256(order))
            for arm in pending:
                call_start = time.perf_counter()
                position = order.index(arm)
                try:
                    result = run_arm(ctx, obs, truth, arm, sorted(a_true), cfgs['SPg_flat'], a_true)
                    row = dict(head, arm=arm, arm_position=position, status='ok',
                               **base.score(ctx, result, truth), **result['diag'])
                except Exception as exc:
                    row = dict(head, arm=arm, arm_position=position, status='error',
                               error=repr(exc), traceback=traceback.format_exc()[-3000:],
                               seconds=time.perf_counter() - call_start)
                base.append_rows(stream, [row])
                completed[(ci, frame, arm)] = row
                print(f'ACC cell={ci + 1} frame={frame} arm={arm} {row["status"]}', flush=True)
    read_rows(path, args.shard, args.nshard, require_complete=True)
    receipt = dict(schema=SPEC['schema'], mode='generate', shard=args.shard,
                   nshard=args.nshard, rows=len(completed),
                   errors=sum(r['status'] != 'ok' for r in completed.values()),
                   rows_sha256=base.sha256_file(path), manifest_sha256=base.sha256_file(config_path),
                   wall_seconds=time.perf_counter() - started)
    receipt_path.write_text(json.dumps(receipt, indent=1, allow_nan=False) + '\n')


def merge(args):
    out = args.out.resolve()
    receipts = [json.loads(p.read_text()) for p in sorted(out.glob('results_shard*.json'))]
    if not receipts:
        raise FileNotFoundError('no shard receipts')
    nshard = receipts[0]['nshard']
    if not (1 <= nshard <= 32 and len(receipts) == nshard
            and sorted(r['shard'] for r in receipts) == list(range(nshard))):
        raise ValueError('incomplete shard receipts')
    manifests = []
    rows = {}
    for receipt in receipts:
        shard = receipt['shard']
        cp = out / f'config_shard{shard:03d}.json'
        rp = out / f'rows_shard{shard:03d}.jsonl'
        if (receipt.get('schema') != SPEC['schema'] or receipt.get('mode') != 'generate'
                or receipt.get('nshard') != nshard
                or base.sha256_file(cp) != receipt.get('manifest_sha256')
                or base.sha256_file(rp) != receipt.get('rows_sha256')):
            raise ValueError(f'shard {shard} receipt/hash mismatch')
        manifests.append(json.loads(cp.read_text()))
        part = read_rows(rp, shard, nshard, require_complete=True)
        if (receipt.get('rows') != len(part)
                or receipt.get('errors') != sum(r['status'] != 'ok' for r in part.values())):
            raise ValueError(f'shard {shard} receipt count mismatch')
        overlap = set(rows) & set(part)
        if overlap:
            raise ValueError(f'duplicate rows across shards: {sorted(overlap)[:1]}')
        rows.update(part)
    first = manifests[0]
    if first.get('spec') != SPEC or first.get('args', {}).get('mode') != 'generate' or first['args'].get('nshard') != nshard:
        raise ValueError('wrong experiment manifest')
    if any(other != first for other in manifests[1:]):
        raise ValueError('shard manifests differ')
    expected = {(ci, frame, arm) for ci in range(len(CELLS)) for frame in FRAMES for arm in ARMS}
    if set(rows) != expected or len(rows) != 1536:
        raise ValueError(f'row allocation mismatch: {len(rows)} vs 1536')
    for ci in range(len(CELLS)):
        for frame in FRAMES:
            part = [rows[ci, frame, arm] for arm in ARMS]
            fp = tuple(part[0][field] for field in PAIR_FIELDS)
            if any(tuple(row[field] for field in PAIR_FIELDS) != fp for row in part[1:]):
                raise ValueError(f'paired observation mismatch at cell {ci + 1}, frame {frame}')
    for frame in FRAMES:
        common = {(rows[ci, frame, ARMS[0]]['info_sha256'], rows[ci, frame, ARMS[0]]['noise_sha256'])
                  for ci in range(len(CELLS))}
        if len(common) != 1:
            raise ValueError(f'cross-cell message/noise mismatch at frame {frame}')
        a, z = rows[1, frame, ARMS[0]], rows[2, frame, ARMS[0]]
        if a['physical_gains_sha256'] != z['physical_gains_sha256'] or a['channel_seed'] != z['channel_seed']:
            raise ValueError(f'cross-rho channel mismatch at frame {frame}')
    summary = []
    for ci in range(len(CELLS)):
        for arm in ARMS:
            sample = [rows[ci, frame, arm] for frame in FRAMES]
            errors = sum(row['status'] != 'ok' for row in sample)
            summary.append(dict(cell=ci + 1, arm=arm, rows=len(sample), errors=errors,
                                mean_seconds=float(np.mean([row['seconds'] for row in sample])),
                                mean_orthogonal_risk=(float(np.mean([row['orthogonal_risk'] for row in sample]))
                                                      if errors == 0 else None),
                                fer=(float(np.mean([row['info_errors'] > 0 for row in sample]))
                                     if errors == 0 else None)))
    result = dict(schema=SPEC['schema'], mode='generate', n_rows=len(rows),
                  n_error_rows=sum(row['status'] != 'ok' for row in rows.values()),
                  manifest=first, shard_receipts=receipts, summary=summary)
    target = out / 'results.json'
    if target.exists() and json.loads(target.read_text()) != result:
        raise ValueError('merge refused: existing result differs')
    target.write_text(json.dumps(result, indent=1, allow_nan=False) + '\n')


def main(argv=None):
    args = parse_args(argv)
    if args.mode == 'merge':
        merge(args)
    else:
        run_shard(args)


if __name__ == '__main__':
    main()
