"""Frozen v3 diagnostic identities and conservative paired statistics.

This module cannot generate the sealed formal D_test. A manifest is a sampling
contract, not proof of observed input equality or scientific acceptance.
"""
from __future__ import annotations

import hashlib
import math


NAMESPACE = 'afdm-v3-20260907'
SYSTEM = dict(N=1024, rho=.5, P_phys=8, k_leak=2, k_max=2, l_max=102,
              receiver_shell='direct40', active_cap=40, receiver_extension=0,
              snr=8., outer_iterations=10, bp_iterations=20, ldpc_iterations=50,
              ldpc_seed=20260726, ldpc_dv=3, ldpc_dc=6)
COMPONENTS = ('channel', 'message', 'noise', 'order', 'gaussian')


def seed_words(dataset, stream, frame, component, repetition=0):
    if dataset not in ('holdout', 'color_engineering', 'color_repeat'):
        raise ValueError('only registered v3 diagnostic datasets are available')
    if component not in COMPONENTS:
        raise ValueError('unknown random component')
    if any(type(value) is not int or value < 0 for value in (stream, frame, repetition)):
        raise ValueError('random identities must be nonnegative integers')
    name = f'{NAMESPACE}|{dataset}|{stream}|{frame}|{component}|{repetition}'
    digest = hashlib.sha256(name.encode('ascii')).digest()
    return [int.from_bytes(digest[i:i+4], 'big') for i in range(0, 32, 4)]


def identity_manifest(dataset):
    if dataset == 'holdout':
        pairs = [(stream, frame) for stream in range(3) for frame in range(128)]
    elif dataset == 'color_engineering':
        pairs = [(0, frame) for frame in range(8)]
    elif dataset == 'color_repeat':
        pairs = [(stream, frame) for stream in (30, 31, 32) for frame in range(16)]
    else:
        raise ValueError('unregistered dataset, including sealed D_test')
    return [dict(dataset=dataset, stream=stream, frame=frame,
                 seeds={component: seed_words(dataset, stream, frame, component)
                        for component in COMPONENTS}) for stream, frame in pairs]


def binomial_interval(successes, trials, alpha=.05):
    """Two-sided Clopper-Pearson, including nondegenerate zero-error bounds."""
    from scipy.stats import beta
    if (type(successes) is not int or type(trials) is not int or
            trials <= 0 or not 0 <= successes <= trials or not 0 < alpha < 1):
        raise ValueError('invalid binomial counts or alpha')
    lower = 0. if successes == 0 else float(beta.ppf(alpha/2, successes, trials-successes+1))
    upper = 1. if successes == trials else float(beta.ppf(1-alpha/2, successes+1, trials-successes))
    return lower, upper


def paired_fer_interval(reference, candidate, comparisons=1, alpha=.05):
    """Conservative simultaneous interval for P(candidate wrong)-P(ref wrong).

    Wins and harms have binomial marginals. Applying CP at alpha/(2*m)
    to each marginal then the union bound gives simultaneous coverage at
    least 1-alpha across m prespecified contrasts, with no independence of
    wins/harms required. Independent channels are still required.
    """
    if (not reference or len(reference) != len(candidate) or
            type(comparisons) is not int or comparisons < 1 or not 0 < alpha < 1):
        raise ValueError('invalid paired sample or family')
    if any(type(value) is not bool for value in [*reference, *candidate]):
        raise ValueError('FER outcomes must be explicit booleans, including failure policy')
    wins = sum(r and not c for r, c in zip(reference, candidate))
    harms = sum(c and not r for r, c in zip(reference, candidate))
    n = len(reference)
    wl, wu = binomial_interval(wins, n, alpha/(2*comparisons))
    hl, hu = binomial_interval(harms, n, alpha/(2*comparisons))
    return dict(n=n, wins=wins, harms=harms, both_wrong=sum(r and c for r,c in zip(reference,candidate)),
                neither_wrong=sum(not r and not c for r,c in zip(reference,candidate)),
                delta=(harms-wins)/n, interval=[hl-wu, hu-wl], comparisons=comparisons,
                method='CP marginal union bound; independent channels')


def classify_interval(interval, margin):
    lower, upper = interval
    if not all(math.isfinite(v) for v in (lower, upper, margin)) or lower > upper or margin <= 0:
        raise ValueError('invalid interval or margin')
    if upper < -margin:
        return 'IMPROVEMENT_BEYOND_MARGIN'
    if lower > margin:
        return 'DEGRADATION_BEYOND_MARGIN'
    if lower >= -margin and upper <= margin:
        return 'EQUIVALENT_WITHIN_MARGIN'
    return 'INCONCLUSIVE'


def color_cells():
    return [dict(arm=arm, capacity=k, power=power)
            for power in (1., .25) for k in (16, 40) for arm in ('A','G','W')]


def frozen_contract():
    return dict(schema='afdm-v3-contract-1', namespace=NAMESPACE, system=SYSTEM,
                baseline='a0 (B0); baseline/A2 is a separate historical repair arm',
                grids=dict(size=[.5,1.,2.],ridge=[1e-3,1e-2,1e-1],sbl=[1e-4,1e-3,1e-2]),
                sbl=dict(iterations=20,relative_tolerance=1e-4,scope='same S40',noise='fixed'),
                sample_counts=dict(fit=192,holdout=384,color_channels=48,color_repeats=4,engineering_channels=8),
                maxima=dict(initial=4224,full_receiver=4496,terminal=4704,position_inner=1920),
                resources=dict(gpu_busy_seconds=28800,host_busy_seconds=28800,cpu_core_seconds=460800,
                               packet_seconds=7200,gpu_memory_mib=22528,margin=.2),
                color_family_comparisons=20, sigma_family_comparisons=6,
                fer_margin=.01, energy_margin=.001, relative_nmse_margin=.05,
                near_zero_nmse=.0001, absolute_nmse_margin=.0001,
                full_receiver_failure=dict(FER=1,BER='worst-case 1 separately; never invent decoded bits'),
                continuous_failure='null metric; retain failure denominator and finite subset',
                confirmatory_access='D_test sealed; holdout recipe and analysis freeze required',
                novelty='not asserted; formal G1/G2/G3 deferred')


def coherent_error_components(truth, components):
    """Evaluate an exact matrix-error decomposition without dropping cross terms.

    Caller supplies missing, gain, false and representation matrices, after
    complex merging of coincident dictionary IDs. This is evaluation only.
    """
    import numpy as np
    required = ('missing', 'gain', 'false', 'representation')
    truth = np.asarray(truth)
    if set(components) != set(required) or truth.ndim != 2 or not np.isfinite(truth).all():
        raise ValueError('four finite matrix error components required')
    parts = {name: np.asarray(components[name]) for name in required}
    if any(v.shape != truth.shape or not np.isfinite(v).all() for v in parts.values()):
        raise ValueError('error components must match truth shape and be finite')
    denominator = float(np.vdot(truth, truth).real)
    if denominator <= 0:
        raise ValueError('normalized channel error requires nonzero truth')
    energies = {name: float(np.vdot(v, v).real)/denominator for name, v in parts.items()}
    crosses = {f'{a}:{b}': float(2*np.vdot(parts[a], parts[b]).real)/denominator
               for i, a in enumerate(required) for b in required[i+1:]}
    total = sum(parts.values())
    direct = float(np.vdot(total, total).real)/denominator
    return dict(energies=energies, cross_terms=crosses, total=direct,
                closure_error=direct-sum(energies.values())-sum(crosses.values()))
