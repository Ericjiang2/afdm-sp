#!/usr/bin/env python3
"""Uniform-symbol Gamma intervention on the immutable full soft-Gram loop."""
from __future__ import annotations
import argparse
import importlib.util
import json
import hashlib
import re
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


gamma = module('__uniform_gamma_reference', 'gamma_ablation.py')
gamma_aggregate = module('__uniform_gamma_aggregate_reference', 'aggregate_gamma_ablation.py')
cohort, oldagg = gamma.cohort, gamma.oldagg
ROOT, VARIANTS, FULL = gamma.ROOT, gamma.VARIANTS, gamma.FULL
DIAG, OUT = FULL.parent/'gamma_ablation1', FULL.parent/'uniform_gamma1'
DIAG_SUMMARY_SHA = '384c53bbb2f02feba40e8e147102a90fd377bc3e16fdd9e253a37d39cf710fdc'
DIAG_VERIFICATION_SHA = '40896c235fe8976a4ce8ef411b9b8bebece1ed6ae8d250014bb4f6e7c1a5e19f'
SCHEMA = 'uniform-symbol-gamma-v1'
OWN = ('uniform_gamma.py', 'aggregate_uniform_gamma.py', 'launch_uniform_gamma.sh',
       'test_uniform_gamma.py', 'test_aggregate_uniform_gamma.py')
NORMAL = 'BHB + Gamma(mean(v_pre)*ones) + noise*P*I; full BHB retained; zero gain variance'
TIMING = 'instrumented cross-run descriptive only; original and uniform Gamma FFTs, PSD and covariance diagnostics retained'


def covariance(matrix, p):
    matrix = np.asarray(matrix)
    if (matrix.shape != (p, p) or p < 1 or not np.isfinite(matrix).all()
            or not np.allclose(matrix, matrix.conj().T, rtol=cohort.RTOL, atol=cohort.ATOL)):
        raise ValueError('invalid original/uniform Gamma before projection')
    eigenvalues = np.linalg.eigvalsh(matrix)
    if eigenvalues[0] < -(cohort.ATOL+cohort.RTOL*np.max(np.abs(eigenvalues))):
        raise ValueError('non-PSD original/uniform Gamma before projection')
    return matrix, float(eigenvalues[0])


class UniformGamma:
    """Only covariance input changes; transforms and the frozen loop are delegated."""
    def __init__(self, physical):
        self.physical, self.diagnostics = physical, []

    def daft(self, *args, **kwargs):
        return self.physical.daft(*args, **kwargs)

    def projected_variance(self, v, delays, dopplers, c1):
        v, delays, dopplers = np.asarray(v, float), np.asarray(delays), np.asarray(dopplers, float)
        if (v.ndim != 1 or not len(v) or not np.isfinite(v).all() or np.any(v < 0)
                or delays.ndim != 1 or not len(delays) or dopplers.shape != delays.shape
                or not np.isfinite(delays).all() or not np.isfinite(dopplers).all()
                or np.any(delays != np.floor(delays)) or np.any(delays < 0) or np.any(delays >= len(v))):
            raise ValueError('uniform Gamma requires finite variance and integer delays in [0,N)')
        original, minimum = covariance(self.physical.projected_variance(v, delays, dopplers, c1), len(delays))
        uniform, uniform_minimum = covariance(self.physical.projected_variance(
            np.full(v.shape, float(v.mean())), delays, dopplers, c1), len(delays))
        same_delay = original * (delays[:, None] == delays[None, :])
        scale = float(v.sum()*np.sqrt(len(delays)))
        absolute = float(np.linalg.norm(uniform-same_delay))
        relative = absolute/scale if scale > 0 else absolute
        if (relative > cohort.RTOL if scale > 0 else absolute > cohort.ATOL):
            raise AssertionError('Gamma(mean(v)) versus same-delay Gamma identity')
        self.diagnostics.append(dict(original_min_eigenvalue=minimum, uniform_min_eigenvalue=uniform_minimum,
            identity_absolute=absolute, identity_scale=scale, identity_relative=relative,
            gamma_projected_variance_calls=2, actual_gamma_fft_count=2))
        return uniform


def validate_projection(items):
    if len(items) != 20:
        raise ValueError('uniform Gamma projection coverage')
    for d in items:
        if (not all(np.isfinite(x) for x in d.values())
                or d['identity_absolute'] < 0 or d['identity_scale'] < 0
                or d['identity_relative'] < 0
                or (d['identity_relative'] > cohort.RTOL if d['identity_scale'] > 0 else d['identity_absolute'] > cohort.ATOL)
                or d['identity_relative'] != (d['identity_absolute']/d['identity_scale'] if d['identity_scale'] > 0 else d['identity_absolute'])
                or d['gamma_projected_variance_calls'] != 2 or d['actual_gamma_fft_count'] != 2):
            raise ValueError('invalid uniform Gamma projection diagnostic')


def load_diag(directory, three, old, full, receipt, full_receipt):
    if (oldagg.reference.file_sha(directory/'summary.json') != DIAG_SUMMARY_SHA
            or oldagg.reference.file_sha(directory/'verification.json') != DIAG_VERIFICATION_SHA):
        raise ValueError('immutable Gamma-only summary/verification changed')
    rows, hashes, identity, _ = gamma_aggregate.load(directory, three, old, full, receipt, full_receipt)
    summary = json.loads((directory/'summary.json').read_text())
    if summary['raw_sha256'] != hashes or summary['source_identity'] != identity or summary['n_keys'] != 200:
        raise ValueError('Gamma-only raw/config/summary binding')
    return {oldagg.key(r):r for r in rows}, dict(summary_sha256=DIAG_SUMMARY_SHA,
        verification_sha256=DIAG_VERIFICATION_SHA, raw_sha256=hashes, identity=identity)


def actual_sources(modules):
    """Bind actual imported files, including private dynamically loaded helpers."""
    records = {}
    for name, value in modules.items():
        path = Path(value.__file__).resolve()
        if name in ('gamma', 'gamma_aggregate', 'cohort', 'oldagg', 'helper', 'trajectory', 'block'):
            expected = HERE/({'gamma':'gamma_ablation.py', 'gamma_aggregate':'aggregate_gamma_ablation.py',
                'cohort':'gram_cohort.py', 'oldagg':'aggregate_gram_cohort.py', 'helper':'restart_point.py',
                'trajectory':'trajectory_analysis.py', 'block':'gram_block.py'}[name])
            if path != expected.resolve(): raise ValueError(f'actual source path changed: {name}')
        records[name] = dict(path=str(path), md5=hashlib.md5(path.read_bytes()).hexdigest())
    for name in OWN:
        path = (HERE/name).resolve()
        records[name] = dict(path=str(path), md5=hashlib.md5(path.read_bytes()).hexdigest())
    return records


def process_key(ctx, helper, block, native, physical, meta, obs, data_af, truth, old, run2, full, diag, gate=False):
    row = dict(meta, schema=SCHEMA, status='running', three_row_sha256=oldagg.row_sha(old),
        run2_row_sha256=oldagg.row_sha(run2), full_row_sha256=oldagg.row_sha(full), diag_row_sha256=oldagg.row_sha(diag),
        input_sha256=run2['input_sha256'], inputs={}, arms={v:{} for v in VARIANTS}, attempts=[],
        receiver_calls=0, decoder_calls=0, observer_receiver_calls=0, observer_parity=False, full_replay=False, sbl_calls=0)
    try:
        _, prior = helper.aggregate.restore_inputs(run2)
        observed = {k:helper.aggregate.array_sha(obs[k]) for k in ('y', 'pilot')}
        if observed != full['observation_sha256'] or diag['full_row_sha256'] != oldagg.row_sha(full):
            raise ValueError('observation hash differs from full reference')
        row['observation_sha256'] = observed
        coded = ctx.encode(ctx.code, truth['info'])
        if prior.shape != (2*len(obs['y']),) or not np.array_equal(coded, truth['coded']):
            raise ValueError('prior/codeword reconstruction')
        common = dict(pd=1-ctx.system.rho, prior=prior, iterations=20, damping=.3, record_states=True)
        variants = VARIANTS if (meta['frame']+meta['snr_centi_db']//100+('U','G').index(meta['scenario']))%2 else VARIANTS[::-1]
        modes = ('full', 'uniform_gamma') if gate else ('uniform_gamma',)
        for variant in variants:
            saved = old['three_mode'][variant]
            inputs = {k:saved[k] for k in ('support', 'h0', 'prior_sha256')}
            if inputs != full['inputs'][variant] or inputs['prior_sha256'] != run2['input_sha256']['prior']:
                raise ValueError('saved upstream/prior drift')
            row['inputs'][variant] = inputs
            channel = helper.e3d.make_channel(ctx, len(obs['y']), saved['support']['delays'],
                saved['support']['dopplers'], helper.replay.complex_array(saved['h0']))
            for mode in modes:
                facade = UniformGamma(physical) if mode == 'uniform_gamma' else physical
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
                    gamma.validate_full(score, full['arms'][variant]['full'])
                else:
                    validate_projection(facade.diagnostics)
                    score.update(projection_diagnostics=facade.diagnostics, actual_gamma_fft_count=40, gamma_projected_variance_calls=40, actual_fft_count=81, logical_fft_count=61)
                if mode == 'uniform_gamma' and gate:
                    row['observer_receiver_calls'] += 1
                    observer_attempt = dict(variant=variant, mode=mode, status='observing', record_states=False)
                    row['attempts'].append(observer_attempt)
                    plain = block.scalar_point(obs['y'], obs['pilot'], channel, obs['sigma2'], native=native,
                        physical=UniformGamma(physical), gain_block='full', **dict(common, record_states=False))
                    if helper.e3d.e3_lib.deep_equal(cohort.observer_payload(det), cohort.observer_payload(plain)):
                        raise AssertionError('uniform_gamma observer parity')
                    observer_attempt['status'] = 'ok'
                row['arms'][variant][mode] = score; attempt['status'] = 'ok'
        row.update(status='ok', observer_parity=bool(gate), full_replay=bool(gate))
    except Exception as exc:
        for attempt in row['attempts']:
            if attempt['status'] != 'ok': attempt['status'] = 'error'
        row.update(status='error', error=repr(exc), error_trace=traceback.format_exc()[-4000:])
    return row


def run(args):
    if not re.fullmatch(r'[0-9a-f]{40}', args.producing_commit):
        raise ValueError('full producing commit required')
    if not 0 <= args.shard < 12 or not 0 < args.deadline_seconds <= 690 or (args.gate_only and args.shard != 0):
        raise ValueError('registered12 shards, <=690s deadline; gate shard0')
    out = args.out.resolve()
    if out != OUT: raise ValueError('registered fresh /data output only')
    helper = module('__uniform_helper', 'restart_point.py')
    trajectory = module('__uniform_trajectory', 'trajectory_analysis.py')
    block = module('__uniform_block', 'gram_block.py')
    if helper.e3d.e3_lib.md5_file(Path(block.__file__)) != cohort.BLOCK_MD5:
        raise ValueError('immutable block changed')
    ctx = helper.e3d.p1ctx.load()
    three, run2, receipt = cohort.load_references(args, ctx, helper, trajectory)
    full, full_receipt = gamma.load_full(args.full_rows, three, run2, receipt)
    diag, diag_receipt = load_diag(args.diag_rows, three, run2, full, receipt, full_receipt)
    native, physical = sys.modules[ctx.native.scalar_joint.__module__], sys.modules['physical']
    for identity in (full_receipt['identity'], diag_receipt['identity']):
        for name, digest in identity['own_md5'].items():
            if helper.e3d.e3_lib.md5_file(ROOT/name) != digest:
                raise ValueError(f'frozen producing helper changed: {name}')
    wrappers = dict(gamma=gamma, gamma_aggregate=gamma_aggregate, cohort=cohort, oldagg=oldagg,
        helper=helper, trajectory=trajectory, block=block, native=native, physical=physical,
        replay=helper.replay, aggregate=helper.aggregate, base=helper.aggregate.base,
        oldd=helper.replay.oldd, oldagg_replay=helper.replay.oldagg, reference=trajectory.reference)
    config = dict(schema=SCHEMA, producing_commit=args.producing_commit, shard=args.shard,
        reference=receipt, full_reference=full_receipt, diag_reference=diag_receipt,
        source_md5=ctx.source_md5, frozen_actual_paths=receipt['run2']['identity']['frozen_actual_paths'],
        own_md5={name:helper.e3d.e3_lib.md5_file(HERE/name) for name in OWN},
        actual_sources=actual_sources(wrappers), environment=ctx.environment,
        out=str(out), deadline_seconds=args.deadline_seconds, normal_system=NORMAL, timing_scope=TIMING)
    if not args.gate_only:
        gate = json.loads((out/'config_gate.json').read_text())['_config']
        if any(gate[k] != config[k] for k in config if k != 'shard'):
            raise ValueError('gate source/config drift')
        consumer = module('__uniform_gate_consumer', 'aggregate_uniform_gamma.py')
        consumer.validate([json.loads(x) for x in (out/'gate.jsonl').read_text().splitlines() if x.strip()],
            three, run2, full, diag, gate=True)
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
                    row = dict(meta, status='error', error='shard deadline', receiver_calls=0, decoder_calls=0, sbl_calls=0)
                else:
                    row = process_key(ctx, helper, block, native, physical, meta, obs, data_af, truth,
                        three[key], run2[key], full[key], diag[key], gate=args.gate_only)
                helper.e3d.write_row(handle, row)
                if row['status'] != 'ok': raise RuntimeError(f'failed {key}: {row["error"]}')
                print(f'{key} ok', flush=True)


def main():
    parser = argparse.ArgumentParser()
    for name, default in (('old-rows', cohort.OLD), ('three-rows', cohort.THREE), ('full-rows', FULL),
                          ('diag-rows', DIAG), ('out', OUT)):
        parser.add_argument('--'+name, type=Path, default=default)
    parser.add_argument('--producing-commit', required=True)
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--deadline-seconds', type=float, default=690)
    parser.add_argument('--gate-only', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__': main()
