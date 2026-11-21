#!/usr/bin/env python3
"""Bounded uniform-duplicate representation probe; original receivers remain unchanged."""
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
ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation')
OLD = ROOT / 'afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2'
OUT = OLD.parent / 'representation_probe1'
KEY, SEED, K = ('U', 300, 700, 9100), 20261024, 2
RTOL, ATOL, SENSITIVITY = 1e-10, 1e-12, 1e-8


def close(actual, expected, label):
    if (np.shape(actual) != np.shape(expected) or not np.isfinite(actual).all()
            or not np.isfinite(expected).all() or not np.allclose(actual, expected, rtol=RTOL, atol=ATOL)):
        raise AssertionError(label)


def pairs(value):
    value = np.asarray(value)
    return np.stack((value.real, value.imag), axis=-1).tolist()


def duplicate(delays, dopplers, gains):
    return np.repeat(delays, K), np.repeat(dopplers, K), np.repeat(gains, K)/K


def aggregate(gains):
    return np.asarray(gains).reshape(-1, K).sum(axis=1)


def first_update(h, a, d, tau, q):
    original = tau/(tau+q)*(h+q*a-q*d)
    duplicated = tau/(tau+K*q)*(h+K*q*a-q*d)
    difference = tau*(K-1)*q/((tau+q)*(tau+K*q))*(tau*a+q*d-h)
    return original, duplicated, difference


def dense_atoms(fixture):
    """Independent explicit DFT/shift construction, confined to the n32 fixture."""
    n = fixture['n']
    if n != 32:
        raise ValueError('dense construction is only for the frozen n32 fixture')
    k = np.arange(n)
    transform = (np.exp(2j*np.pi*fixture['c2']*k*k)[:, None]
                 * np.exp(-2j*np.pi*k[:, None]*k[None, :]/n)/np.sqrt(n)
                 * np.exp(2j*np.pi*fixture['c1']*k*k)[None, :])
    atoms = []
    for delay, doppler in zip(fixture['delays'], fixture['dopplers']):
        wrap = k-delay
        phase = np.where(wrap < 0, np.exp(2j*np.pi*fixture['c1']*(n*n+2*n*wrap)), 1.)
        shift = np.zeros((n, n), complex)
        shift[k, wrap % n] = phase*np.exp(2j*np.pi*k*doppler/n)
        atoms.append(transform @ shift @ transform.conj().T)
    return np.stack(atoms)


def synthetic_fixture():
    # Frozen before execution: RNG calls/order, physical values and dimensions.
    rng = np.random.default_rng(SEED)
    n = 32
    fixture = dict(n=n, c1=5/64, c2=np.sqrt(2)/1024,
                   delays=np.array([1, 1]), dopplers=np.array([.25, -.45]),
                   gains=np.array([.7+.1j, -.25+.4j]), pd=.7, sigma2=.2)
    fixture['pilot'] = np.sqrt(.3/2)*(rng.choice([-1, 1], n)+1j*rng.choice([-1, 1], n))
    fixture['prior'] = rng.normal(0., .4, 2*n)
    fixture['x'] = fixture['pilot']+np.sqrt(.7/2)*(rng.choice([-1, 1], n)+1j*rng.choice([-1, 1], n))
    atoms = dense_atoms(fixture)
    fixture['y'] = np.einsum('p,pij,j->i', fixture['gains'], atoms, fixture['x'])
    fixture['y'] += np.sqrt(.2/2)*(rng.normal(size=n)+1j*rng.normal(size=n))
    return fixture, atoms


def gaussian_posterior(B, y, variance, noise):
    precision = B.conj().T @ B/noise+np.eye(B.shape[1])/variance
    covariance = np.linalg.solve(precision, np.eye(B.shape[1]))
    mean = np.linalg.solve(precision, B.conj().T @ y/noise)
    return mean, covariance


def synthetic_posterior(fixture, atoms):
    p = len(fixture['gains'])
    D = np.kron(np.eye(p), np.ones((1, K)))
    B = np.column_stack([atom @ fixture['x'] for atom in atoms])
    mean, covariance = gaussian_posterior(B, fixture['y'], 1/p, fixture['sigma2'])
    new_mean, new_covariance = gaussian_posterior(B @ D, fixture['y'], 1/(K*p), fixture['sigma2'])
    close(D @ new_mean, mean, 'synthetic exact posterior mean pushforward')
    close(D @ new_covariance @ D.T, covariance, 'synthetic exact posterior covariance pushforward')
    return dict(mean=pairs(mean), covariance=pairs(covariance),
                aggregate_duplicate_mean=pairs(D @ new_mean),
                aggregate_duplicate_covariance=pairs(D @ new_covariance @ D.T), passed=True)


def difference(actual, expected):
    actual, expected = np.asarray(actual), np.asarray(expected)
    delta = actual-expected
    denominator = float(np.linalg.norm(expected))
    return dict(max_abs=float(np.max(np.abs(delta))), l2=float(np.linalg.norm(delta)),
                relative_l2=float(np.linalg.norm(delta)/denominator) if denominator > 0 else None)


def native_probe(native, physical, channel, observation, prior, pd, atoms=None):
    delays, dopplers, gains = duplicate(channel.delays, channel.dopplers, channel.gains)
    duplicated = physical.Channel(channel.n, channel.c1, channel.c2, delays, dopplers, gains)
    ops, dup_ops = native.TimePathOps(channel), native.TimePathOps(duplicated)
    D = np.kron(np.eye(channel.p), np.ones((1, K)))
    close(D @ gains, channel.gains, 'initial aggregate gains')
    close(D @ (np.eye(K*channel.p)/(K*channel.p)) @ D.T, np.eye(channel.p)/channel.p, 'physical prior pushforward')
    close(dup_ops.R, D.T @ ops.R @ D, 'duplicate physical Gram')
    close(dup_ops.power(gains), ops.power(channel.gains), 'initial physical power')
    index = np.arange(channel.n)
    probes = [np.ones(channel.n, complex)/np.sqrt(channel.n),
              np.exp(2j*np.pi*index/channel.n)/np.sqrt(channel.n),
              (1+index/channel.n)*np.exp(1j*index/7)/np.sqrt(channel.n)]
    action_differences = []
    for probe in probes:
        original_action, duplicate_action = channel.apply(probe), duplicated.apply(probe)
        close(duplicate_action, original_action, 'initial physical action')
        action_differences.append(difference(duplicate_action, original_action))
    if atoms is not None:
        gram = np.einsum('pij,qij->pq', atoms.conj(), atoms)/channel.n
        close(ops.R, gram, 'independent dense physical Gram')
        dense = np.einsum('p,pij->ij', channel.gains, atoms)
        close(ops.power(channel.gains), np.linalg.norm(dense)**2/channel.n, 'dense physical Frobenius norm')
        for probe in probes:
            close(channel.apply(probe), dense @ probe, 'independent dense channel action')
    common = dict(pd=pd, prior=prior, iterations=20, damping=.3, record_states=True)
    results = {}
    for mode in ('fixed', 'point'):
        results[mode] = [native.scalar_joint(observation['y'], observation['pilot'], c, observation['sigma2'],
                                            gain_mode=mode, **common) for c in (channel, duplicated)]
        for result in results[mode]:
            if (len(result['states']) != 20 or np.any(result['gain_variance'] != 0)
                    or any(s['vh'] != 0 for s in result['states'])):
                raise AssertionError('complete zero-variance fixed/point trajectories')
    fixed, fixed_dup = results['fixed']
    for field in ('extrinsic', 'app', 'mu', 'variance', 'iterations', 'fft_count'):
        close(fixed_dup[field], fixed[field], f'fixed output {field}')
    non_gain_fields = tuple(k for k in fixed['states'][0] if k != 'h')
    for original_state, duplicate_state in zip(fixed['states'], fixed_dup['states']):
        close(original_state['h'], channel.gains, 'original fixed gains')
        close(aggregate(duplicate_state['h']), channel.gains, 'duplicate fixed aggregate gains')
        for field in non_gain_fields:
            close(duplicate_state[field], original_state[field], f'fixed state {field}')
    for original_trace, duplicate_trace in zip(fixed['trace'], fixed_dup['trace']):
        for field in original_trace:
            close(duplicate_trace[field], original_trace[field], f'fixed trace {field}')
    first = [native.scalar_joint(observation['y'], observation['pilot'], c, observation['sigma2'],
                pd=pd, prior=prior, iterations=1, damping=.3, gain_mode='point', record_states=True)
             for c in (channel, duplicated)]
    for field in ('extrinsic', 'app', 'mu', 'variance'):
        close(first[1][field], first[0][field], f'first point symbol {field}')
    for field in non_gain_fields:
        close(first[1]['states'][0][field], first[0]['states'][0][field], f'first point state {field}')
    point, point_dup = results['point']
    close(first[0]['gains'], point['states'][0]['h'], 'point1/point20 initial prefix')
    close(first[1]['gains'], point_dup['states'][0]['h'], 'duplicate point1/point20 initial prefix')
    mu0, v0, _ = native.moments(prior, pd)
    x0 = observation['pilot']+mu0
    B = ops.responses_time(physical.daft(x0, channel.c1, channel.c2, True))
    state = first[0]['states'][0]
    q, tau = float(state['vq']), 1/channel.p
    close(q, 1/max(state['sv']*np.vdot(x0, x0).real, 1e-12), 'first q from prior x0')
    a = B.conj().T @ state['s']
    d = channel.gains*state['sv']*channel.n*float(v0.mean())
    predicted, predicted_dup, predicted_difference = first_update(channel.gains, a, d, tau, q)
    original_h1, duplicate_h1 = first[0]['gains'], aggregate(first[1]['gains'])
    close(original_h1, predicted, 'first original gain formula')
    close(duplicate_h1, predicted_dup, 'first duplicate gain formula')
    close(duplicate_h1-original_h1, predicted_difference, 'first gain difference formula')
    first_power = ops.power(original_h1)
    relative_physical = float(np.sqrt(ops.power(duplicate_h1-original_h1)/first_power)) if first_power > 0 else None
    original_first_channel = physical.Channel(channel.n, channel.c1, channel.c2, channel.delays, channel.dopplers, original_h1)
    duplicate_first_channel = physical.Channel(channel.n, channel.c1, channel.c2, delays, dopplers, first[1]['gains'])
    first_action_differences = [difference(duplicate_first_channel.apply(p), original_first_channel.apply(p)) for p in probes]
    if atoms is not None:
        dense_original = np.einsum('p,pij->ij', original_h1, atoms)
        dense_delta = np.einsum('p,pij->ij', duplicate_h1-original_h1, atoms)
        close(ops.power(duplicate_h1-original_h1), np.linalg.norm(dense_delta)**2/channel.n, 'first physical delta dense Frobenius')
        close(first_power, np.linalg.norm(dense_original)**2/channel.n, 'first reference dense Frobenius')
    final_power = ops.power(point['gains'])
    state_differences = [{field:difference(new[field], old[field]) for field in non_gain_fields}
                         for old, new in zip(point['states'], point_dup['states'])]
    report = dict(initial_operator_action_differences=action_differences, prior_pushforward=True,
        initial_power=ops.power(channel.gains), fixed_output_and_state_parity=True,
        fixed_llr_difference=difference(fixed_dup['extrinsic'], fixed['extrinsic']),
        first_symbol_parity=True, first_llr_difference=difference(first[1]['extrinsic'], first[0]['extrinsic']),
        first_update=dict(q=q, tau=tau, duplicate_tau=tau/K, prior_variance_mean=float(v0.mean()),
            original=pairs(original_h1), duplicate_aggregate=pairs(duplicate_h1),
            predicted_difference=pairs(predicted_difference),
            formula_residual=difference(duplicate_h1-original_h1, predicted_difference),
            relative_physical_frobenius=relative_physical,
            action_differences=first_action_differences,
            sensitivity=relative_physical is not None and relative_physical > SENSITIVITY),
        point_state_differences=state_differences,
        final_point_llr_difference=difference(point_dup['extrinsic'], point['extrinsic']),
        final_point_relative_physical_frobenius=float(np.sqrt(ops.power(aggregate(point_dup['gains'])-point['gains'])/final_power)) if final_power > 0 else None,
        point_traces=dict(original=point['trace'], duplicate=point_dup['trace']))
    return report, results, duplicated


def run(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    if not args.out.resolve().is_relative_to(ROOT):
        raise ValueError('probe output must stay under /data/guoyikun project root')
    spec = importlib.util.spec_from_file_location('__representation_restart', HERE / 'restart_point.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    old_rows, receipt = helper.aggregate.load_reference(args.old_rows)
    ctx = helper.e3d.p1ctx.load()
    paths = helper.qualify_sources(ctx, receipt)
    native = sys.modules[ctx.native.scalar_joint.__module__]
    physical = sys.modules['physical']
    wrappers = (helper, helper.replay, helper.aggregate, helper.aggregate.base,
                helper.replay.oldd, helper.replay.oldagg, native, physical)
    used = {str(Path(m.__file__).resolve()): hashlib.md5(Path(m.__file__).read_bytes()).hexdigest() for m in wrappers}
    used.update({str(HERE/name): hashlib.md5((HERE/name).read_bytes()).hexdigest()
                 for name in ('representation_probe.py', 'test_representation_probe.py')})
    config = dict(old_rows=str(args.old_rows.resolve()), out=str(args.out.resolve()), key=list(KEY),
        seed=SEED, k=K, rtol=RTOL, atol=ATOL, sensitivity_threshold=SENSITIVITY,
        helper_own_md5=used, source_md5=ctx.source_md5, frozen_actual_paths=paths,
        environment=ctx.environment, reference=receipt)
    args.out.mkdir(parents=True)
    with (args.out/'config.json').open('x') as handle:
        handle.write(json.dumps(dict(_argv=sys.argv[1:], _config=config), indent=1, allow_nan=False)+'\n')
    try:
        fixture, atoms = synthetic_fixture()
        posterior = synthetic_posterior(fixture, atoms)
        channel = physical.Channel(fixture['n'], fixture['c1'], fixture['c2'], fixture['delays'], fixture['dopplers'], fixture['gains'])
        synthetic, _, _ = native_probe(native, physical, channel, fixture, fixture['prior'], fixture['pd'], atoms=atoms)
        synthetic.update(exact_fixed_x_posterior=posterior,
            fixture=dict(n=32, delays=fixture['delays'].tolist(), dopplers=fixture['dopplers'].tolist(),
                gains=pairs(fixture['gains']), c1=fixture['c1'], c2=fixture['c2'], pd=fixture['pd'], sigma2=fixture['sigma2'],
                input_sha256={k:helper.aggregate.array_sha(fixture[k]) for k in ('pilot', 'prior', 'x', 'y')}))
        old = old_rows[KEY]
        _, prior = helper.aggregate.restore_inputs(old)
        h0 = helper.replay.complex_array(old['h0'])
        raw, diag = helper.e3d.p1ctx.base(ctx, 'U', .3, 9100)
        meta, obs, data_af, truth = helper.e3d.observe_key(ctx, raw, diag, *KEY)
        if helper.e3d.key_of(meta) != KEY:
            raise AssertionError('predetermined key changed')
        channel = helper.e3d.make_channel(ctx, len(obs['y']), old['support']['delays'], old['support']['dopplers'], h0)
        real, results, duplicate_channel = native_probe(native, physical, channel, obs, prior, 1-ctx.system.rho)
        coded = ctx.encode(ctx.code, truth['info'])
        if not np.array_equal(coded, truth['coded']):
            raise AssertionError('saved real codeword reconstruction')
        scores = {}
        for mode in ('fixed', 'point'):
            scores[mode] = [helper.replay.score_arm(ctx, result, c, truth, data_af, coded, None)
                           for result, c in zip(results[mode], (channel, duplicate_channel))]
            expected = old['baseline'][mode+'20']
            for field, value in expected.items():
                if field in ('decoded_sha256', 'info_errors', 'fer'):
                    if scores[mode][0][field] != value:
                        raise AssertionError(f'original {mode} saved {field}')
                else:
                    close(scores[mode][0][field], value, f'original {mode} saved {field}')
        close(results['point'][0]['gains'], helper.replay.complex_array(old['h20']), 'original point saved h20')
        real.update(original_saved_baseline_parity=True, scores=scores,
                    old_row_sha256=helper.aggregate.row_sha(old), input_sha256=old['input_sha256'],
                    observation_sha256={k:helper.aggregate.array_sha(obs[k]) for k in ('y', 'pilot')})
        report = dict(status='ok', _argv=sys.argv[1:], _config=config, synthetic=synthetic, real=real,
            interpretation='One synthetic fixture and one predetermined old key; representation sensitivity only, not FER evidence or a Gamma-reversal mechanism.')
        with (args.out/'summary.json').open('x') as handle:
            handle.write(json.dumps(report, indent=1, allow_nan=False)+'\n')
        print('representation probe qualified', flush=True)
    except Exception as exc:
        (args.out/'failure.json').write_text(json.dumps(dict(status='error', error=repr(exc), trace=traceback.format_exc()), indent=1)+'\n')
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-rows', type=Path, default=OLD)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    started = time.monotonic()
    run(args)
    print(f'wall_seconds={time.monotonic()-started:.3f}', flush=True)


if __name__ == '__main__':
    main()
