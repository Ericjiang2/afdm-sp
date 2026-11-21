#!/usr/bin/env python3
"""Only Gamma offdiagonals removed, via a facade on the immutable full loop."""
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


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE/filename)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


cohort = module('__gamma_old_cohort', 'gram_cohort.py')
oldagg = module('__gamma_old_aggregate', 'aggregate_gram_cohort.py')
ROOT, VARIANTS = cohort.ROOT, cohort.VARIANTS
FULL = cohort.OUT
OUT = FULL.parent/'gamma_ablation1'
FULL_SUMMARY_SHA = 'eabf7b1f5e134e5d0e02456aaa851a74965590de3471aef2b62e92047da2b443'
FULL_VERIFICATION_SHA = 'f62b62826af2650eca05e3d26aca06f6082db1be9f3ec9d9ef583cba315d38db'
SCHEMA = 'gamma-only-diagonal-v1'
OWN = ('gamma_ablation.py', 'aggregate_gamma_ablation.py', 'launch_gamma_ablation.sh',
       'test_gamma_ablation.py', 'test_aggregate_gamma_ablation.py')


class DiagonalGamma:
    """Delegate transforms; remove only offdiagonals of the actual full Gamma."""
    def __init__(self, physical):
        self.physical = physical

    def daft(self, *args, **kwargs):
        return self.physical.daft(*args, **kwargs)

    def projected_variance(self, *args, **kwargs):
        gamma = np.asarray(self.physical.projected_variance(*args, **kwargs))
        # Do not let diagonalization hide invalid covariance output.
        if (gamma.ndim != 2 or gamma.shape[0] != gamma.shape[1]
                or not np.isfinite(gamma).all()
                or not np.allclose(gamma, gamma.conj().T, rtol=cohort.RTOL, atol=cohort.ATOL)):
            raise ValueError('invalid original Gamma before diagonalization')
        eigenvalues = np.linalg.eigvalsh(gamma)
        if eigenvalues[0] < -(cohort.ATOL+cohort.RTOL*np.max(np.abs(eigenvalues))):
            raise ValueError('non-PSD original Gamma before diagonalization')
        return np.diag(np.diag(gamma))


def load_full(directory, three, run2, receipt):
    if oldagg.reference.file_sha(directory/'summary.json') != FULL_SUMMARY_SHA:
        raise ValueError('immutable full cohort summary changed')
    if oldagg.reference.file_sha(directory/'verification.json') != FULL_VERIFICATION_SHA:
        raise ValueError('immutable full cohort verification changed')
    rows, hashes, identity, _ = oldagg.load(directory, three, run2, receipt)
    summary = json.loads((directory/'summary.json').read_text())
    if summary['raw_sha256'] != hashes or summary['source_identity'] != identity or summary['n_keys'] != 200:
        raise ValueError('full cohort raw/config/summary binding')
    return {oldagg.key(r):r for r in rows}, dict(summary_sha256=FULL_SUMMARY_SHA, verification_sha256=FULL_VERIFICATION_SHA, raw_sha256=hashes,
        identity=identity, config_sha256={p.name:oldagg.reference.file_sha(p) for p in sorted(directory.glob('config_shard*.json'))})


def validate_full(score, saved):
    for field in ('decoded_sha256', 'info_errors', 'fer', 'ldpc_iters', 'fft_count',
                  'gain_solve_calls', 'covariance_solve_calls', 'gamma_fft_count', 'native_symbol_fft_count'):
        if score[field] != saved[field]:
            raise AssertionError(f'full replay drift {field}')
    for field in oldagg.FLOATS+('final_gains',):
        if not np.allclose(score[field], saved[field], rtol=cohort.RTOL, atol=cohort.ATOL):
            raise AssertionError(f'full replay drift {field}')


def process_key(ctx, helper, block, native, physical, meta, obs, data_af, truth, old, run2, full, gate=False):
    row = dict(meta, schema=SCHEMA, status='running', three_row_sha256=oldagg.row_sha(old),
        run2_row_sha256=oldagg.row_sha(run2), full_row_sha256=oldagg.row_sha(full),
        input_sha256=run2['input_sha256'], inputs={}, arms={v:{} for v in VARIANTS}, attempts=[],
        receiver_calls=0, decoder_calls=0, observer_receiver_calls=0, observer_parity=False, full_replay=False)
    try:
        _, prior = helper.aggregate.restore_inputs(run2)
        observed = {k:helper.aggregate.array_sha(obs[k]) for k in ('y', 'pilot')}
        if observed != full['observation_sha256']:
            raise ValueError('observation hash differs from full reference')
        row['observation_sha256'] = observed
        coded = ctx.encode(ctx.code, truth['info'])
        if prior.shape != (2*len(obs['y']),) or not np.array_equal(coded, truth['coded']):
            raise ValueError('prior/codeword reconstruction')
        common = dict(pd=1-ctx.system.rho, prior=prior, iterations=20, damping=.3, record_states=True)
        variants = VARIANTS if (meta['frame']+meta['snr_centi_db']//100+('U','G').index(meta['scenario']))%2 else VARIANTS[::-1]
        modes = ('full', 'gamma_diag') if gate else ('gamma_diag',)
        for variant in variants:
            saved = old['three_mode'][variant]
            inputs = {k:saved[k] for k in ('support', 'h0', 'prior_sha256')}
            if inputs != full['inputs'][variant] or inputs['prior_sha256'] != run2['input_sha256']['prior']:
                raise ValueError('saved upstream/prior drift')
            row['inputs'][variant] = inputs
            channel = helper.e3d.make_channel(ctx, len(obs['y']), saved['support']['delays'],
                saved['support']['dopplers'], helper.replay.complex_array(saved['h0']))
            for mode in modes:
                facade = DiagonalGamma(physical) if mode == 'gamma_diag' else physical
                attempt = dict(variant=variant, mode=mode, status='detecting', detect_seconds=None, score_seconds=None)
                row['attempts'].append(attempt); row['receiver_calls'] += 1
                start = time.perf_counter()
                try:
                    det = block.scalar_point(obs['y'], obs['pilot'], channel, obs['sigma2'], native=native,
                        physical=facade, gain_block='full', **common)
                finally:
                    attempt['detect_seconds'] = time.perf_counter()-start
                cohort.validate_detection(det, 'full', channel, obs['sigma2'])
                attempt['status'] = 'scoring'; row['decoder_calls'] += 1
                start = time.perf_counter()
                try:
                    score = helper.replay.score_arm(ctx, det, channel, truth, data_af, coded, attempt['detect_seconds'])
                finally:
                    attempt['score_seconds'] = time.perf_counter()-start
                cohort.validate_score(score)
                score.update(final_gains=helper.replay.oldd.pairs(det['gains']), trace=det['trace'],
                    fft_count=det['fft_count'], recorded_states=len(det['states']), gain_solve_calls=det['gain_solve_calls'],
                    covariance_solve_calls=det['covariance_solve_calls'], gamma_fft_count=det['gamma_fft_count'],
                    native_symbol_fft_count=det['native_symbol_fft_count'],
                    block_diagnostics=[{k:v for k,v in d.items() if k != 'covariance'} for d in det['gain_blocks']])
                if mode == 'full':
                    validate_full(score, full['arms'][variant]['full'])
                elif gate:
                    row['observer_receiver_calls'] += 1
                    observer_attempt = dict(variant=variant, mode=mode, status='observing', record_states=False)
                    row['attempts'].append(observer_attempt)
                    plain = block.scalar_point(obs['y'], obs['pilot'], channel, obs['sigma2'], native=native,
                        physical=facade, gain_block='full', **dict(common, record_states=False))
                    if helper.e3d.e3_lib.deep_equal(cohort.observer_payload(det), cohort.observer_payload(plain)):
                        raise AssertionError('gamma_diag observer parity')
                    observer_attempt['status'] = 'ok'
                row['arms'][variant][mode] = score; attempt['status'] = 'ok'
        row.update(status='ok', observer_parity=bool(gate), full_replay=bool(gate))
    except Exception as exc:
        for attempt in row['attempts']:
            if attempt['status'] != 'ok': attempt['status'] = 'error'
        row.update(status='error', error=repr(exc), error_trace=traceback.format_exc()[-4000:])
    return row


def run(args):
    if not 0 <= args.shard < 12 or not 0 < args.deadline_seconds <= 700 or (args.gate_only and args.shard != 0):
        raise ValueError('registered12 shards, <=700s deadline; gate shard0')
    out = args.out.resolve()
    if out != OUT or any(out == p.resolve() for p in (args.old_rows, args.three_rows, args.full_rows)):
        raise ValueError('registered fresh /data output only')
    helper = module('__gamma_helper', 'restart_point.py')
    trajectory = module('__gamma_trajectory', 'trajectory_analysis.py')
    block = module('__gamma_block', 'gram_block.py')
    if helper.e3d.e3_lib.md5_file(Path(block.__file__)) != cohort.BLOCK_MD5:
        raise ValueError('immutable block changed')
    ctx = helper.e3d.p1ctx.load()
    three, run2, receipt = cohort.load_references(args, ctx, helper, trajectory)
    full, full_receipt = load_full(args.full_rows, three, run2, receipt)
    native, physical = sys.modules[ctx.native.scalar_joint.__module__], sys.modules['physical']
    # Check the actual loaded frozen paths through existing strict source qualifier.
    for name, digest in full_receipt['identity']['own_md5'].items():
        if helper.e3d.e3_lib.md5_file(ROOT/name) != digest:
            raise ValueError(f'full producing helper changed: {name}')
    own = {f'experiments/sbl_freeze_replay_20261020/{name}':helper.e3d.e3_lib.md5_file(HERE/name) for name in OWN}
    config = dict(schema=SCHEMA, shard=args.shard, reference=receipt, full_reference=full_receipt,
        source_md5=ctx.source_md5, frozen_actual_paths=receipt['run2']['identity']['frozen_actual_paths'], own_md5=own,
        environment=ctx.environment, out=str(out), deadline_seconds=args.deadline_seconds,
        normal_system='BHB + diag(Gamma(v_pre)) + noise*P*I; full BHB retained; zero gain variance',
        timing_scope='instrumented cross-run descriptive only; full Gamma FFT, original-Gamma PSD check and covariance diagnostics retained')
    out.mkdir(parents=True, exist_ok=True)
    row_path = out/('gate.jsonl' if args.gate_only else f'rows_shard{args.shard:03d}.jsonl')
    config_path = out/('config_gate.json' if args.gate_only else f'config_shard{args.shard:03d}.json')
    if row_path.exists() or config_path.exists(): raise FileExistsError('fresh output required')
    with config_path.open('x') as handle:
        handle.write(json.dumps(dict(_argv=sys.argv[1:], _config=config), allow_nan=False, indent=1)+'\n')
    start = time.monotonic()
    with row_path.open('x') as handle:
        for frame in ([9100] if args.gate_only else list(cohort.FRAMES)[args.shard::12]):
            for meta, obs, data_af, truth in helper.e3d.cells_of_frame(ctx, frame, helper.replay.GRID, None):
                key = helper.e3d.key_of(meta)
                if time.monotonic()-start > args.deadline_seconds:
                    row = dict(meta, status='error', error='shard deadline', receiver_calls=0, decoder_calls=0)
                else:
                    row = process_key(ctx, helper, block, native, physical, meta, obs, data_af, truth,
                        three[key], run2[key], full[key], gate=args.gate_only)
                helper.e3d.write_row(handle, row)
                if row['status'] != 'ok': raise RuntimeError(f'failed {key}: {row["error"]}')
                print(f'{key} ok', flush=True)


def main():
    parser = argparse.ArgumentParser()
    for name, default in (('old-rows', cohort.OLD), ('three-rows', cohort.THREE), ('full-rows', FULL), ('out', OUT)):
        parser.add_argument('--'+name, type=Path, default=default)
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--deadline-seconds', type=float, default=690)
    parser.add_argument('--gate-only', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__': main()
