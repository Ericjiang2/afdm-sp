#!/usr/bin/env python3
"""Minimal dense-Gamma/native-replay/uniform-duplicate gates, never a cohort run."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__gram_block', HERE/'gram_block.py')
block = importlib.util.module_from_spec(spec)
spec.loader.exec_module(block)
spec = importlib.util.spec_from_file_location('__gram_representation', HERE/'representation_probe.py')
rep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rep)
GAMMA_SEED = 20261025
OUT = rep.OLD.parent/'gram_block_gate1'


def gamma_fixture():
    fixture = dict(n=32, c1=5/64, c2=np.sqrt(2)/1024,
                   delays=np.array([1, 1, 3]), dopplers=np.array([.25, -.45, .7]))
    v = .05+.9*np.random.default_rng(GAMMA_SEED).random(32)
    atoms = rep.dense_atoms(fixture)
    Gamma = np.einsum('prk,qrk,k->pq', atoms.conj(), atoms, v)
    return fixture, v, Gamma


def gamma_gate(physical):
    fixture, v, expected = gamma_fixture()
    actual = physical.projected_variance(v, fixture['delays'], fixture['dopplers'], fixture['c1'])
    rep.close(actual, expected, 'mixed-delay nonuniform-v dense Gamma')
    rep.close(actual, actual.conj().T, 'dense Gamma Hermitian')
    rep.close(np.diag(actual), np.full(3, v.sum()), 'dense Gamma diagonal')
    eigenvalues = np.linalg.eigvalsh(actual)
    if eigenvalues[0] < -(rep.ATOL+rep.RTOL*np.max(np.abs(eigenvalues))):
        raise AssertionError('dense Gamma PSD')
    D = np.kron(np.eye(3), np.ones((1, rep.K)))
    duplicate = physical.projected_variance(v, np.repeat(fixture['delays'], rep.K),
                                            np.repeat(fixture['dopplers'], rep.K), fixture['c1'])
    rep.close(duplicate, D.T @ expected @ D, 'duplicate dense Gamma covariance')
    return dict(seed=GAMMA_SEED, delays=fixture['delays'].tolist(), dopplers=fixture['dopplers'].tolist(),
        v=v.tolist(), eigenvalues=eigenvalues.tolist(), dense_difference=rep.difference(actual, expected),
        gamma_fft_calls=2, passed=True)


def physical_difference(ops, actual, expected):
    absolute = float(np.sqrt(ops.power(actual-expected)))
    denominator = float(np.sqrt(ops.power(expected)))
    return dict(absolute=absolute, relative=absolute/denominator if denominator > 0 else None,
                reference=denominator)


def frozen_block_gate(native, physical, channel, duplicate, observation, prior, pd, atoms=None):
    mu, v, _ = native.moments(prior, pd)
    x = observation['pilot']+mu
    Y = physical.daft(observation['y'], channel.c1, channel.c2, True)
    xt = physical.daft(x, channel.c1, channel.c2, True)
    D = np.kron(np.eye(channel.p), np.ones((1, rep.K)))
    solutions = {}
    for name, c in (('original', channel), ('duplicate', duplicate)):
        B = native.TimePathOps(c).responses_time(xt)
        Gamma = physical.projected_variance(v, c.delays, c.dopplers, c.c1)
        rep.close(np.diag(Gamma), np.full(c.p, v.sum()), 'frozen pre-v Gamma diagonal')
        solutions[name] = {mode:block.solve_gain(B, Y, Gamma, observation['sigma2'], mode)
                           for mode in ('full', 'diag')}
        full, diagonal = solutions[name]['full'][1], solutions[name]['diag'][1]
        for field in ('M', 'b', 'alpha'):
            rep.close(diagonal[field], full[field], f'matched frozen {field}')
        rep.close(diagonal['Q'], np.diag(np.diag(full['Q'])), 'only normal-system off-diagonals change')
        if name == 'original':
            original_B, original_Gamma = B, Gamma
        else:
            rep.close(B, original_B @ D, 'duplicate frozen B')
            rep.close(Gamma, D.T @ original_Gamma @ D, 'duplicate frozen Gamma')
    if atoms is not None:
        dense_B = np.column_stack([atom @ x for atom in atoms])
        dense_Gamma = np.einsum('prk,qrk,k->pq', atoms.conj(), atoms, v)
        rep.close(original_Gamma, dense_Gamma, 'synthetic working-v dense Gamma')
        rep.close(original_B.conj().T @ original_B, dense_B.conj().T @ dense_B, 'dense B normal matrix')
        rep.close(original_B.conj().T @ Y, dense_B.conj().T @ observation['y'], 'dense B right-hand side')
    full, full_dup = solutions['original']['full'], solutions['duplicate']['full']
    rep.close(D @ full_dup[0], full[0], 'frozen full mean pushforward')
    rep.close(D @ full_dup[1]['covariance'] @ D.T, full[1]['covariance'], 'frozen full covariance pushforward')
    diagonal, diag_dup = solutions['original']['diag'], solutions['duplicate']['diag']
    m, b, alpha = np.diag(diagonal[1]['M']), diagonal[1]['b'], diagonal[1]['alpha']
    rep.close(D @ diag_dup[0], rep.K*b/(m+rep.K*alpha), 'diagonal duplicate aggregate formula')
    report = dict(pre_v_sum=float(v.sum()), gamma_fft_calls=2, full_mean_covariance_invariant=True,
                  matched_full_diag_inputs=True, systems={})
    for name, modes in solutions.items():
        report['systems'][name] = {mode:dict(h=rep.pairs(h), M=rep.pairs(detail['M']), b=rep.pairs(detail['b']),
            alpha=detail['alpha'], normal_relative_residual=detail['normal_relative_residual'],
            covariance_relative_residual=detail['covariance_relative_residual'], seconds=detail['seconds'])
            for mode, (h, detail) in modes.items()}
    return report, solutions


def case_gate(helper, native, physical, channel, observation, prior, pd, atoms=None):
    delays, dopplers, gains = rep.duplicate(channel.delays, channel.dopplers, channel.gains)
    duplicate = physical.Channel(channel.n, channel.c1, channel.c2, delays, dopplers, gains)
    ops = native.TimePathOps(channel)
    D = np.kron(np.eye(channel.p), np.ones((1, rep.K)))
    rep.close(D @ gains, channel.gains, 'initial gains aggregate')
    rep.close(D @ (np.eye(duplicate.p)/duplicate.p) @ D.T, np.eye(channel.p)/channel.p, 'initial prior pushforward')
    rep.close(native.TimePathOps(duplicate).R, D.T @ ops.R @ D, 'initial physical Gram')
    k = np.arange(channel.n)
    probes = [np.ones(channel.n, complex)/np.sqrt(channel.n),
              np.exp(2j*np.pi*k/channel.n)/np.sqrt(channel.n),
              (1+k/channel.n)*np.exp(1j*k/7)/np.sqrt(channel.n)]
    for probe in probes:
        rep.close(duplicate.apply(probe), channel.apply(probe), 'initial physical action')
    if atoms is not None:
        rep.close(ops.R, np.einsum('pij,qij->pq', atoms.conj(), atoms)/channel.n, 'independent dense physical Gram')
    frozen_report, frozen = frozen_block_gate(native, physical, channel, duplicate, observation, prior, pd, atoms)
    common = dict(pd=pd, prior=prior, iterations=20, damping=.3, record_states=True)
    timings = {}
    start = time.perf_counter()
    canonical = native.scalar_joint(observation['y'], observation['pilot'], channel, observation['sigma2'], gain_mode='point', **common)
    timings['canonical'] = time.perf_counter()-start
    start = time.perf_counter()
    cloned = block.scalar_point(observation['y'], observation['pilot'], channel, observation['sigma2'],
                                native=native, physical=physical, gain_block='native', **common)
    timings['native_clone'] = time.perf_counter()-start
    mismatches = helper.e3d.e3_lib.deep_equal(canonical, cloned)
    if mismatches:
        raise AssertionError(f'canonical native clone mismatch: {mismatches[:3]}')
    results = {}
    for mode in ('full', 'diag'):
        results[mode], timings[mode] = [], []
        for c in (channel, duplicate):
            start = time.perf_counter()
            result = block.scalar_point(observation['y'], observation['pilot'], c, observation['sigma2'],
                                       native=native, physical=physical, gain_block=mode, **common)
            timings[mode].append(time.perf_counter()-start)
            if (len(result['states']) != 20 or len(result['gain_blocks']) != 20
                    or np.any(result['gain_variance'] != 0) or any(s['vh'] != 0 for s in result['states'])):
                raise AssertionError('complete point block with zero propagated gain variance')
            results[mode].append(result)
        for name, result in zip(('original', 'duplicate'), results[mode]):
            rep.close(result['states'][0]['h'], frozen[name][mode][0], 'first update uses the same pre-symbol moments')
            rep.close(result['gain_blocks'][0]['v_pre_sum'], frozen_report['pre_v_sum'], 'first pre-v snapshot')
    report = dict(native_clone_exact_parity=True, initial_H_prior_parity=True, frozen_moment_gate=frozen_report,
                  receiver_seconds=timings, arms={})
    non_gain_fields = tuple(k for k in canonical['states'][0] if k != 'h')
    for mode, (original, duplicated) in results.items():
        physical_differences, state_differences, covariance_differences = [], [], []
        for i, (old_state, new_state) in enumerate(zip(original['states'], duplicated['states'])):
            aggregated = rep.aggregate(new_state['h'])
            physical_diff = physical_difference(ops, aggregated, old_state['h'])
            physical_differences.append(physical_diff)
            state_differences.append({field:rep.difference(new_state[field], old_state[field]) for field in non_gain_fields})
            if mode == 'full':
                rep.close(aggregated, old_state['h'], 'full all-step aggregate gain invariance')
                if physical_diff['absolute'] > rep.ATOL+rep.RTOL*physical_diff['reference']:
                    raise AssertionError('full all-step physical-H invariance')
                for field in non_gain_fields:
                    rep.close(new_state[field], old_state[field], f'full all-step state {field}')
                for field in original['trace'][i]:
                    rep.close(duplicated['trace'][i][field], original['trace'][i][field], f'full trace {field}')
                C = original['gain_blocks'][i]['covariance']
                C_new = D @ duplicated['gain_blocks'][i]['covariance'] @ D.T
                rep.close(C_new, C, 'full all-step local covariance pushforward')
                covariance_differences.append(rep.difference(C_new, C))
        if mode == 'full':
            for field in ('extrinsic', 'app', 'mu', 'variance', 'iterations', 'fft_count'):
                rep.close(duplicated[field], original[field], f'full output {field}')
        report['arms'][mode] = dict(physical_differences=physical_differences,
            representation_sensitive=any(d['relative'] is not None and d['relative'] > rep.SENSITIVITY for d in physical_differences),
            non_gain_state_differences=state_differences, local_covariance_differences=covariance_differences,
            final_llr_difference=rep.difference(duplicated['extrinsic'], original['extrinsic']),
            final_gains=dict(original=rep.pairs(original['gains']), duplicate_aggregate=rep.pairs(rep.aggregate(duplicated['gains']))),
            runs=[dict(fft_count=r['fft_count'], native_symbol_fft_count=r['native_symbol_fft_count'],
                gamma_fft_count=r['gamma_fft_count'], gain_solve_calls=r['gain_solve_calls'],
                covariance_solve_calls=r['covariance_solve_calls'], trace=r['trace'],
                gain_blocks=[{k:v for k,v in item.items() if k != 'covariance'} for item in r['gain_blocks']]) for r in (original, duplicated)])
    return report, canonical, results, duplicate


def run(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    if not args.out.resolve().is_relative_to(rep.ROOT):
        raise ValueError('all probe outputs must stay under /data/guoyikun project root')
    spec = importlib.util.spec_from_file_location('__gram_restart', HERE/'restart_point.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    old_rows, receipt = helper.aggregate.load_reference(args.old_rows)
    ctx = helper.e3d.p1ctx.load()
    paths = helper.qualify_sources(ctx, receipt)
    native, physical = sys.modules[ctx.native.scalar_joint.__module__], sys.modules['physical']
    wrappers = (block, rep, helper, helper.replay, helper.aggregate, helper.aggregate.base,
                helper.replay.oldd, helper.replay.oldagg, native, physical)
    hashes = {str(Path(m.__file__).resolve()):hashlib.md5(Path(m.__file__).read_bytes()).hexdigest() for m in wrappers}
    hashes.update({str(HERE/name):hashlib.md5((HERE/name).read_bytes()).hexdigest()
                   for name in ('gram_block.py', 'gram_block_probe.py', 'test_gram_block.py')})
    config = dict(old_rows=str(args.old_rows.resolve()), out=str(args.out.resolve()), key=list(rep.KEY),
        synthetic_seed=rep.SEED, gamma_seed=GAMMA_SEED, rtol=rep.RTOL, atol=rep.ATOL,
        sensitivity_threshold=rep.SENSITIVITY, own_helper_md5=hashes, source_md5=ctx.source_md5,
        frozen_actual_paths=paths, reference=receipt, environment=ctx.environment,
        timing_scope='instrumented qualification; covariance diagnostics included, no speed claim')
    args.out.mkdir(parents=True)
    with (args.out/'config.json').open('x') as handle:
        handle.write(json.dumps(dict(_argv=sys.argv[1:], _config=config), allow_nan=False, indent=1)+'\n')
    start = time.perf_counter()
    try:
        gamma = gamma_gate(physical)
        fixture, atoms = rep.synthetic_fixture()
        channel = physical.Channel(fixture['n'], fixture['c1'], fixture['c2'], fixture['delays'], fixture['dopplers'], fixture['gains'])
        synthetic, _, _, _ = case_gate(helper, native, physical, channel, fixture, fixture['prior'], fixture['pd'], atoms)
        old = old_rows[rep.KEY]
        _, prior = helper.aggregate.restore_inputs(old)
        raw, diag = helper.e3d.p1ctx.base(ctx, 'U', .3, 9100)
        meta, obs, data_af, truth = helper.e3d.observe_key(ctx, raw, diag, *rep.KEY)
        if helper.e3d.key_of(meta) != rep.KEY:
            raise AssertionError('predetermined key changed')
        channel = helper.e3d.make_channel(ctx, len(obs['y']), old['support']['delays'], old['support']['dopplers'], helper.replay.complex_array(old['h0']))
        real, canonical, results, duplicate = case_gate(helper, native, physical, channel, obs, prior, 1-ctx.system.rho)
        coded = ctx.encode(ctx.code, truth['info'])
        if not np.array_equal(coded, truth['coded']):
            raise AssertionError('real codeword reconstruction')
        score = helper.replay.score_arm(ctx, canonical, channel, truth, data_af, coded, real['receiver_seconds']['canonical'])
        for field, expected in old['baseline']['point20'].items():
            if field in ('decoded_sha256', 'info_errors', 'fer'):
                if score[field] != expected:
                    raise AssertionError(f'native saved baseline {field}')
            else:
                rep.close(score[field], expected, f'native saved baseline {field}')
        rep.close(canonical['gains'], helper.replay.complex_array(old['h20']), 'native saved h20')
        real.update(native_saved_baseline_parity=True, native_score=score,
            old_row_sha256=helper.aggregate.row_sha(old), input_sha256=old['input_sha256'],
            observation_sha256={k:helper.aggregate.array_sha(obs[k]) for k in ('y', 'pilot')})
        for mode, records in results.items():
            real['arms'][mode]['scores'] = [helper.replay.score_arm(ctx, result, c, truth, data_af, coded, seconds)
                for result, c, seconds in zip(records, (channel, duplicate), real['receiver_seconds'][mode])]
        report = dict(status='ok', _argv=sys.argv[1:], _config=config, gamma_gate=gamma,
            synthetic=synthetic, real=real, gate_seconds=time.perf_counter()-start,
            interpretation='Local expected-log Gaussian surrogate; covariance not propagated. One old key is descriptive; no 200-key study or global AMP/VI repair.')
        with (args.out/'summary.json').open('x') as handle:
            handle.write(json.dumps(report, allow_nan=False, indent=1)+'\n')
        print('soft-Gram minimal gate qualified', flush=True)
    except Exception as exc:
        (args.out/'failure.json').write_text(json.dumps(dict(status='error', error=repr(exc), trace=traceback.format_exc()), indent=1)+'\n')
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-rows', type=Path, default=rep.OLD)
    parser.add_argument('--out', type=Path, default=OUT)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
