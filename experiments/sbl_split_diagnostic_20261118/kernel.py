"""Frozen detector adapters and physical comparisons for the saved-key split diagnostic."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

EXPERIMENTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENTS / 'sbl_freeze_replay_20261020'))
import gram_block
import representation_probe as probe

MODES = ('fixed', 'point', 'joint', 'eG')


def duplicate(channel):
    paths = probe.duplicate(channel.delays, channel.dopplers, channel.gains)
    return type(channel)(channel.n, channel.c1, channel.c2, *paths)


def detect(native, physical, channel, obs, prior, pd, mode):
    """Record the native first-update state without changing the replay schedule."""
    args = obs['y'], obs['pilot'], channel, obs['sigma2']
    common = dict(pd=pd, prior=prior, iterations=20, damping=.3, record_states=True)
    if mode == 'eG':
        result = gram_block.scalar_point(*args, native=native, physical=physical,
                                         gain_block='full', **common)
    else:
        result = native.scalar_joint(*args, gain_mode=mode, **common)
    return result


def operator_error(native, original, variant):
    """Relative Frobenius error from time-domain cyclic diagonals.

    The DAFT similarity is unitary. Distinct integer delays occupy disjoint
    cyclic diagonals, so subtracting before squaring avoids Gram cancellation.
    """
    original_ops = native.TimePathOps(original)
    variant_ops = native.TimePathOps(variant)
    norm_squared = 0.
    error_squared = 0.
    for delay in np.union1d(original.delays, variant.delays):
        old = original.delays == delay
        new = variant.delays == delay
        baseline = original_ops.phase[:, old] @ original.gains[old]
        candidate = variant_ops.phase[:, new] @ variant.gains[new]
        difference = candidate - baseline
        norm_squared += np.vdot(baseline, baseline).real
        error_squared += np.vdot(difference, difference).real
    if norm_squared == 0:
        raise ValueError('zero reference physical operator')
    return float(np.sqrt(error_squared / norm_squared))


def pushforward(path_count):
    return np.repeat(np.eye(path_count), probe.K, axis=1)


def initial_split_metrics(native, original, split):
    D = pushforward(original.p)
    prior = np.eye(original.p) / original.p
    split_prior = np.eye(split.p) / split.p
    return dict(operator_relative=operator_error(native, original, split),
                gain_aggregate_max=float(np.max(np.abs(D @ split.gains - original.gains))),
                prior_aggregate_max=float(np.max(np.abs(D @ split_prior @ D.T - prior))))


def compare_split(native, original, split, orig_result, split_result):
    orig_first = type(original)(original.n, original.c1, original.c2, original.delays,
                                original.dopplers, orig_result['states'][0]['h'])
    split_first = type(split)(split.n, split.c1, split.c2, split.delays,
                              split.dopplers, split_result['states'][0]['h'])
    index = np.arange(original.n)
    vectors = (
        np.ones(original.n, complex),
        np.exp(2j * np.pi * index / original.n),
        (1 + index / original.n) * np.exp(1j * index / 7),
    )
    actions = []
    for vector in vectors:
        x = vector / np.sqrt(original.n)
        actions.append(probe.difference(split_first.apply(x), orig_first.apply(x)))
    extrinsic = probe.difference(split_result['extrinsic'], orig_result['extrinsic'])
    operator_relative = operator_error(native, orig_first, split_first)
    return dict(operator_relative=operator_relative, actions=actions, extrinsic=extrinsic,
                invariant=operator_relative <= 1e-10 and extrinsic['max_abs'] <= 1e-9)


def synthetic_checks(native, physical):
    """Test the actual full soft-Gram and native point first updates."""
    fixture, _ = probe.synthetic_fixture()
    n, c1, c2 = fixture['n'], fixture['c1'], fixture['c2']
    channel = physical.Channel(n, c1, c2, fixture['delays'], fixture['dopplers'], fixture['gains'])
    split = duplicate(channel)
    original_ops = native.TimePathOps(channel)
    split_ops = native.TimePathOps(split)
    D = pushforward(channel.p)
    prior, pd, noise = fixture['prior'], fixture['pd'], fixture['sigma2']
    mu, v, _ = native.moments(prior, pd)
    x = fixture['pilot'] + mu
    xt = physical.daft(x, c1, c2, True)
    Y = physical.daft(fixture['y'], c1, c2, True)
    B = original_ops.responses_time(xt)
    B_split = split_ops.responses_time(xt)
    gamma = physical.projected_variance(v, channel.delays, channel.dopplers, c1)
    gamma_split = physical.projected_variance(v, split.delays, split.dopplers, c1)
    probe.close(B_split, B @ D, 'response-column pushforward')
    probe.close(gamma_split, D.T @ gamma @ D, 'Gamma pushforward')
    gain, full = gram_block.solve_gain(B, Y, gamma, noise, 'full')
    gain_split, full_split = gram_block.solve_gain(B_split, Y, gamma_split, noise, 'full')
    probe.close(full_split['alpha'], probe.K * full['alpha'], 'split ridge')
    probe.close(D @ gain_split, gain, 'eG mean pushforward')
    probe.close(D @ full_split['covariance'] @ D.T, full['covariance'], 'eG covariance pushforward')

    common = dict(pd=pd, prior=prior, iterations=1, damping=.3, gain_mode='point', record_states=True)
    point, point_split = [native.scalar_joint(fixture['y'], fixture['pilot'], c, noise, **common)
                          for c in (channel, split)]
    state = point['states'][0]
    q = state['vq']
    probe.close(q, 1 / max(state['sv'] * np.vdot(x, x).real, 1e-12), 'point first pseudo-variance')
    a = B.conj().T @ state['s']
    d = channel.gains * state['sv'] * n * float(v.mean())
    predicted, predicted_split, predicted_delta = probe.first_update(channel.gains, a, d, 1 / channel.p, q)
    agg_first = D @ point_split['gains']
    probe.close(point['gains'], predicted, 'point original first update')
    probe.close(agg_first, predicted_split, 'point aggregate first update')
    probe.close(agg_first - point['gains'], predicted_delta, 'point first-update difference')
    return dict(passed=True,
                eg_gamma_max=probe.difference(gamma_split, D.T @ gamma @ D)['max_abs'],
                eg_mean_max=probe.difference(D @ gain_split, gain)['max_abs'],
                eg_covariance_max=probe.difference(D @ full_split['covariance'] @ D.T,
                                                   full['covariance'])['max_abs'],
                point_original_max=probe.difference(point['gains'], predicted)['max_abs'],
                point_aggregate_max=probe.difference(agg_first, predicted_split)['max_abs'],
                point_delta_max=probe.difference(agg_first - point['gains'], predicted_delta)['max_abs'])


if __name__ == '__main__':
    sys.path.insert(0, str(EXPERIMENTS / 'sp_afdm_native_joint_20260921' / 'src'))
    sys.path.insert(0, str(EXPERIMENTS / 'sp_afdm_frozen_20260920' / 'src'))
    import physical
    import twofft

    print(json.dumps(synthetic_checks(twofft, physical), indent=2))
