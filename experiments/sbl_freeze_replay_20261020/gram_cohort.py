#!/usr/bin/env python3
"""Bounded ten-arm matched replay on immutable actual-support SBL outputs; no SBL."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation')
OLD = ROOT/'afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2'
THREE = ROOT/'afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1'
OUT = OLD.parent/'gram_cohort1'
VARIANTS, MODES = ('L-diag', 'L-cov'), ('fixed', 'point', 'joint', 'full', 'diag')
ARMS = tuple((v, m) for v in VARIANTS for m in MODES)
FRAMES = range(9100, 9150)
EXPECTED = {(sc, 300, snr, f) for sc in ('U', 'G') for snr in (700, 800) for f in FRAMES}
KEY = ('U', 300, 700, 9100)
RTOL, ATOL = 1e-10, 1e-12
BLOCK_MD5 = '00658a71ef07e1921997b369d568658e'


def load_references(args, ctx, helper, trajectory):
    """Return three/run2 key maps and the aggregator-shared {'three','run2'} receipt."""
    rows, three_receipt, _ = trajectory.load(args.three_rows, args.three_rows.parent/'analysis_fix/summary.json')
    three = {helper.e3d.key_of(row):row for row in rows}
    run2, run2_receipt = helper.aggregate.load_reference(args.old_rows)
    helper.qualify_sources(ctx, run2_receipt)
    if len(rows) != 200 or set(three) != EXPECTED or set(run2) != EXPECTED:
        raise ValueError('registered paired 200-key reference coverage')
    if three_receipt['raw_sha256'] != run2_receipt['identity']['old_raw_sha256']:
        raise ValueError('three-mode/run2 raw binding')
    for key in EXPECTED:
        _, prior = helper.aggregate.restore_inputs(run2[key])
        prior_hash = helper.aggregate.array_sha(prior)
        if prior_hash != run2[key]['input_sha256']['prior']:
            raise ValueError('run2 restored prior binding')
        for variant in VARIANTS:
            saved = three[key]['three_mode'][variant]
            if saved['prior_sha256'] != prior_hash:
                raise ValueError(f'variant prior binding: {key}/{variant}')
            h0 = helper.replay.complex_array(saved['h0'])
            if (not np.isfinite(h0).all() or len(h0) != len(saved['support']['delays'])
                    or len(h0) != len(saved['support']['dopplers'])):
                raise ValueError('saved support/h0 dimensions or values')
        scalar = three[key]['three_mode']['L-diag']
        if scalar['h0'] != run2[key]['h0'] or scalar['support'] != run2[key]['support']:
            raise ValueError('run2 scalar support/h0 binding')
    return three, run2, dict(three=three_receipt, run2=run2_receipt)


def arm_order(meta):
    key = (meta['scenario'], meta['rho_permille'], meta['snr_centi_db'], meta['frame'])
    if key not in EXPECTED:
        raise ValueError('unregistered key')
    offset = ((key[3]-9100)*4+('U', 'G').index(key[0])*2+(700, 800).index(key[2])) % len(ARMS)
    return ARMS[offset:]+ARMS[:offset]


def observer_payload(det):
    # Timing varies between calls; the covariance and all other returned values remain checked.
    payload = {k:v for k,v in det.items() if k != 'states'}
    if 'gain_blocks' in payload:
        payload['gain_blocks'] = [{k:v for k,v in item.items() if k not in ('seconds', 'solve_seconds')}
                                  for item in payload['gain_blocks']]
    return payload


def validate_detection(det, mode, channel, noise):
    block_mode = mode in ('full', 'diag')
    if (det['iterations'] != 20 or len(det['states']) != 20 or len(det['trace']) != 20
            or det['fft_count'] != (61 if block_mode else 41)):
        raise ValueError('detector trajectory/FFT coverage')
    for field in ('extrinsic', 'app', 'mu', 'variance', 'gains', 'gain_variance'):
        if not np.isfinite(det[field]).all():
            raise ValueError(f'nonfinite detector {field}')
    for i, (state, trace) in enumerate(zip(det['states'], det['trace'])):
        if (trace['iteration'] != i or trace['fft_count'] != (3 if block_mode else 2)
                or not all(np.isfinite(v).all() for v in state.values())
                or not all(np.isfinite(v).all() for v in trace.values())):
            raise ValueError('invalid detector states/trace')
        if mode != 'joint' and (state['vh'] != 0 or trace['gain_variance'] != 0):
            raise ValueError('nonzero point/fixed gain variance')
        if mode == 'fixed' and not np.array_equal(state['h'], channel.gains):
            raise ValueError('fixed gains moved')
    if mode != 'joint' and np.any(det['gain_variance'] != 0):
        raise ValueError('nonzero returned point/fixed gain variance')
    if block_mode:
        if (len(det['gain_blocks']) != 20 or det['gain_solve_calls'] != 20
                or det['covariance_solve_calls'] != 20 or det['gamma_fft_count'] != 20):
            raise ValueError('gain-block primitive coverage')
        for i, diagnostic in enumerate(det['gain_blocks']):
            if (diagnostic['iteration'] != i or diagnostic['gamma_fft_count'] != 1
                    or not all(np.isfinite(v).all() for v in diagnostic.values())
                    or not np.isclose(diagnostic['alpha'], noise*channel.p, rtol=RTOL, atol=ATOL)
                    or diagnostic['normal_relative_residual'] > RTOL
                    or diagnostic['covariance_relative_residual'] > RTOL
                    or diagnostic['seconds'] < 0 or diagnostic['solve_seconds'] < 0):
                raise ValueError('invalid gain-block diagnostics')


def validate_baseline(score, saved):
    for field in ('decoded_sha256', 'info_errors', 'fer', 'ldpc_iters'):
        if score[field] != saved[field]:
            raise AssertionError(f'old baseline {field}')
    terminal = saved['trajectory'][-1]
    expected = dict(extrinsic_bit_logloss=saved['extrinsic_bit_logloss'], nmse_final=terminal['channel_nmse'],
                    data_mse_final=terminal['data_mse'], symbol_variance_final=terminal['symbol_variance'])
    for field, value in expected.items():
        if not np.isclose(score[field], value, rtol=RTOL, atol=ATOL):
            raise AssertionError(f'old baseline {field}')
    if not np.allclose(score['final_gains'], terminal['h'], rtol=RTOL, atol=ATOL):
        raise AssertionError('old baseline final gains')


def validate_score(score):
    fields = ('extrinsic_bit_logloss', 'nmse_final', 'data_mse_final', 'symbol_variance_final',
              'detect_seconds', 'decode_seconds')
    if (type(score['info_errors']) is not int or score['info_errors'] < 0
            or score['fer'] != int(score['info_errors'] > 0)
            or type(score['ldpc_iters']) is not int or not 1 <= score['ldpc_iters'] <= 50
            or any(not np.isfinite(score[k]) or score[k] < 0 for k in fields)):
        raise ValueError('invalid terminal score')


def process_key(ctx, helper, block, native, physical, meta, obs, data_af, truth, old, run2, gate=False):
    row = dict(meta, status='running', three_row_sha256=helper.aggregate.row_sha(old),
        run2_row_sha256=helper.aggregate.row_sha(run2), input_sha256=run2['input_sha256'],
        inputs={}, arms={v:{} for v in VARIANTS}, attempts=[], receiver_calls=0, decoder_calls=0,
        gate_receiver_calls=0, gate_decoder_calls=0, observer_parity=False)
    try:
        _, prior = helper.aggregate.restore_inputs(run2)
        coded = ctx.encode(ctx.code, truth['info'])
        if prior.shape != (2*len(obs['y']),) or not np.array_equal(coded, truth['coded']):
            raise ValueError('prior/codeword dimensions or reconstruction')
        channels = {}
        for variant in VARIANTS:
            saved = old['three_mode'][variant]
            if saved['prior_sha256'] != run2['input_sha256']['prior']:
                raise ValueError('per-key variant prior binding')
            row['inputs'][variant] = {k:saved[k] for k in ('support', 'h0', 'prior_sha256')}
            channels[variant] = helper.e3d.make_channel(ctx, len(obs['y']), saved['support']['delays'],
                saved['support']['dopplers'], helper.replay.complex_array(saved['h0']))
        order = arm_order(meta)
        row['arm_order'] = [list(arm) for arm in order]
        common = dict(pd=1-ctx.system.rho, prior=prior, iterations=20, damping=.3, record_states=True)
        for variant, mode in order:
            channel = channels[variant]
            attempt = dict(variant=variant, mode=mode, status='detecting', detect_seconds=None, score_seconds=None)
            row['attempts'].append(attempt)
            row['receiver_calls'] += 1
            started = time.perf_counter()
            try:
                if mode in ('full', 'diag'):
                    det = block.scalar_point(obs['y'], obs['pilot'], channel, obs['sigma2'],
                        native=native, physical=physical, gain_block=mode, **common)
                else:
                    det = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], gain_mode=mode, **common)
            finally:
                attempt['detect_seconds'] = time.perf_counter()-started
            validate_detection(det, mode, channel, obs['sigma2'])
            attempt['status'] = 'scoring'
            row['decoder_calls'] += 1
            started = time.perf_counter()
            try:
                score = helper.replay.score_arm(ctx, det, channel, truth, data_af, coded, attempt['detect_seconds'])
            finally:
                attempt['score_seconds'] = time.perf_counter()-started
            validate_score(score)
            score.update(final_gains=helper.replay.oldd.pairs(det['gains']), trace=det['trace'],
                fft_count=det['fft_count'], recorded_states=len(det['states']),
                gain_solve_calls=det.get('gain_solve_calls', 0), covariance_solve_calls=det.get('covariance_solve_calls', 0),
                gamma_fft_count=det.get('gamma_fft_count', 0), native_symbol_fft_count=41,
                block_diagnostics=[{k:v for k,v in item.items() if k != 'covariance'} for item in det.get('gain_blocks', [])])
            if mode in ('fixed', 'point', 'joint'):
                validate_baseline(score, old['three_mode'][variant]['modes'][mode])
            if gate and mode in ('full', 'diag'):
                row['gate_receiver_calls'] += 1
                plain = block.scalar_point(obs['y'], obs['pilot'], channel, obs['sigma2'], native=native,
                    physical=physical, gain_block=mode, **dict(common, record_states=False))
                if helper.e3d.e3_lib.deep_equal(observer_payload(det), observer_payload(plain)):
                    raise AssertionError('new arm observer-on/off parity')
            if gate and mode == 'point':
                row['gate_receiver_calls'] += 1
                cloned = block.scalar_point(obs['y'], obs['pilot'], channel, obs['sigma2'],
                    native=native, physical=physical, gain_block='native', **common)
                if helper.e3d.e3_lib.deep_equal(det, cloned):
                    raise AssertionError('native clone exact parity')
            row['arms'][variant][mode] = score
            attempt['status'] = 'ok'
        row.update(status='ok', observer_parity=bool(gate), old_baseline_replay=True,
            observation_sha256={k:helper.aggregate.array_sha(obs[k]) for k in ('y', 'pilot')})
    except Exception as exc:
        if row['attempts'] and row['attempts'][-1]['status'] != 'ok':
            row['attempts'][-1]['status'] = 'error'
        row.update(status='error', error=repr(exc), error_trace=traceback.format_exc()[-4000:])
    return row


def run(args):
    if args.nshard != 12 or not 0 <= args.shard < 12 or not 0 < args.deadline_seconds <= 700:
        raise ValueError('registered 12-shard cohort with <=700s shard deadline only')
    if args.gate_only and args.shard != 0:
        raise ValueError('gate uses shard0')
    out = args.out.resolve()
    if not out.is_relative_to(ROOT) or out in (args.old_rows.resolve(), args.three_rows.resolve()):
        raise ValueError('new output must be separate and under /data/guoyikun')
    spec = importlib.util.spec_from_file_location('__cohort_restart', HERE/'restart_point.py')
    helper = importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    spec = importlib.util.spec_from_file_location('__cohort_trajectory', HERE/'trajectory_analysis.py')
    trajectory = importlib.util.module_from_spec(spec);spec.loader.exec_module(trajectory)
    spec = importlib.util.spec_from_file_location('__cohort_block', HERE/'gram_block.py')
    block = importlib.util.module_from_spec(spec);spec.loader.exec_module(block)
    if helper.e3d.e3_lib.md5_file(Path(block.__file__)) != BLOCK_MD5:
        raise ValueError('qualified gain-block source changed')
    ctx = helper.e3d.p1ctx.load()
    three, run2, reference = load_references(args, ctx, helper, trajectory)
    native, physical = sys.modules[ctx.native.scalar_joint.__module__], sys.modules['physical']
    wrappers = (helper, helper.replay, helper.aggregate, helper.aggregate.base, helper.replay.oldd,
                helper.replay.oldagg, trajectory, trajectory.reference, block, native, physical)
    own = {str(Path(m.__file__).resolve().relative_to(ROOT)):helper.e3d.e3_lib.md5_file(Path(m.__file__)) for m in wrappers}
    own.update({f'experiments/sbl_freeze_replay_20261020/{name}':helper.e3d.e3_lib.md5_file(HERE/name)
                for name in ('gram_cohort.py', 'test_gram_cohort.py', 'launch_gram_cohort.sh',
                             'aggregate_gram_cohort.py', 'test_aggregate_gram_cohort.py')})
    config = dict(shard=args.shard, nshard=12, frames=[9100, 9150], variants=VARIANTS, modes=MODES,
        reference=reference, source_md5=ctx.source_md5,
        frozen_actual_paths=reference['run2']['identity']['frozen_actual_paths'], own_md5=own,
        old_rows=str(args.old_rows.resolve()), three_rows=str(args.three_rows.resolve()), out=str(out),
        environment=ctx.environment, deadline_seconds=args.deadline_seconds, rtol=RTOL, atol=ATOL,
        timing_scope='matched instrumented receivers; block covariance/eigenvalue/Cholesky qualification retained')
    out.mkdir(parents=True, exist_ok=True)
    row_path = out/('gate.json' if args.gate_only else f'rows_shard{args.shard:03d}.jsonl')
    config_path = out/('config_gate.json' if args.gate_only else f'config_shard{args.shard:03d}.json')
    if row_path.exists() or config_path.exists():
        raise FileExistsError('cohort/gate output exists')
    with config_path.open('x') as handle:
        handle.write(json.dumps(dict(_argv=sys.argv[1:], _config=config), allow_nan=False, indent=1)+'\n')
    started = time.monotonic()
    with row_path.open('x') as handle:
        for frame in ([9100] if args.gate_only else list(FRAMES)[args.shard::12]):
            for meta, obs, data_af, truth in helper.e3d.cells_of_frame(ctx, frame, helper.replay.GRID, None):
                key = helper.e3d.key_of(meta)
                if args.gate_only and key != KEY:
                    continue
                if time.monotonic()-started > args.deadline_seconds:
                    row = dict(meta, status='error', error='cohort shard deadline', receiver_calls=0, decoder_calls=0)
                else:
                    row = process_key(ctx, helper, block, native, physical, meta, obs, data_af, truth, three[key], run2[key], gate=args.gate_only)
                helper.e3d.write_row(handle, dict(passed=row['status']=='ok', row=row, _config=config,
                    _argv=sys.argv[1:]) if args.gate_only else row)
                if row['status'] != 'ok':
                    raise RuntimeError(f'cohort failed key {key}: {row["error"]}')
                print(f'{key} ok', flush=True)
    print(f'completed in {time.monotonic()-started:.3f}s', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-rows', type=Path, default=OLD)
    parser.add_argument('--three-rows', type=Path, default=THREE)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--nshard', type=int, default=12)
    parser.add_argument('--deadline-seconds', type=float, default=700)
    parser.add_argument('--gate-only', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
