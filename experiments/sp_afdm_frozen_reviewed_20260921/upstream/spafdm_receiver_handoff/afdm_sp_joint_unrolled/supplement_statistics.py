"""Conservative CP/union-bound inference on independent exogenous binary blocks.

Arms within a block may be arbitrarily dependent. n is blocks, never bits or
pooled SNR records. Joint nuisance models are scenarios, not receiver evidence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shlex
import sys

import numpy as np
import scipy
from scipy.stats import beta


FAMILY_ALPHA = 0.05 / 7


def _integer(value, name, minimum=1):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return int(value)


def _prob(value, name):
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or not np.isfinite(value) or not 0 < value < 1:
        raise ValueError(f'{name} must be finite and in (0, 1)')
    return float(value)


def _counts(counts, n):
    a = np.asarray(counts)
    if a.dtype.kind not in 'iu' or np.any(a < 0) or np.any(a > n):
        raise ValueError('counts must be integers in [0,n]')
    return a.astype(np.int64)


def cp_bounds(counts, n, tail):
    """Each marginal tail has probability at most tail; exact endpoints.

    Evaluate only unique counts (a per-call vectorized cache), avoiding either
    R scalar beta calls or a huge n-sized lookup for large sufficient n.
    """
    n = _integer(n, 'n')
    tail = _prob(tail, 'tail')
    c = _counts(counts, n)
    u, inverse = np.unique(c, return_inverse=True)
    lo = np.zeros(u.size)
    hi = np.ones(u.size)
    low_mask, high_mask = u > 0, u < n
    lo[low_mask] = beta.ppf(tail, u[low_mask], n-u[low_mask]+1)
    hi[high_mask] = beta.isf(tail, u[high_mask]+1, n-u[high_mask])
    if not np.all(np.isfinite(lo)) or not np.all(np.isfinite(hi)):
        raise ArithmeticError('nonfinite CP quantile')
    return lo[inverse].reshape(c.shape), hi[inverse].reshape(c.shape)


def _tail(alpha_family, m, k):
    return _prob(alpha_family, 'alpha_family') / (2 * _integer(m, 'm') * k)


def _combine(counts, coefficients, n, tail):
    lo, hi = cp_bounds(counts, n, tail)
    c = np.asarray(coefficients, dtype=float)
    lower = np.sum(np.where(c > 0, lo, hi) * c, axis=-1)
    upper = np.sum(np.where(c > 0, hi, lo) * c, axis=-1)
    return {'delta': np.sum(counts*c, axis=-1)/n, 'lower': lower,
            'upper': upper, 'tail': tail, 'n': n}


def paired_delta(W, L, n, alpha_family=FAMILY_ALPHA, m=1):
    """Positive delta is FER_ref - FER_arm; W+L <= n is mandatory."""
    n = _integer(n, 'n')
    W, L = np.broadcast_arrays(_counts(W, n), _counts(L, n))
    if np.any(W > n-L):
        raise ValueError('W+L exceeds independent block count n')
    return _combine(np.stack([W, L], axis=-1), [1, -1], n,
                    _tail(alpha_family, m, 2))


def _coefficients(coefficients):
    c = np.asarray(coefficients, dtype=float)
    if c.ndim != 1 or not c.size or not np.all(np.isfinite(c)) or not np.any(c):
        raise ValueError('coefficients must be a nonzero finite vector')
    return c


def linear_contrast(counts, coefficients, n, alpha_family=FAMILY_ALPHA, m=1):
    """Last axis: binary error counts for each arm, all from the same n blocks."""
    n = _integer(n, 'n')
    c = _coefficients(coefficients)
    counts = _counts(counts, n)
    if counts.ndim < 1 or counts.shape[-1] != c.size:
        raise ValueError('count and coefficient dimensions differ')
    active = c != 0
    return _combine(counts[..., active], c[active], n,
                    _tail(alpha_family, m, int(active.sum())))


def decisions(lower, upper):
    """Strict boundary tests; propositions may hold simultaneously."""
    lo, hi = np.broadcast_arrays(np.asarray(lower, float), np.asarray(upper, float))
    if not np.all(np.isfinite(lo)) or not np.all(np.isfinite(hi)) or np.any(lo > hi):
        raise ValueError('invalid interval')
    return {'BENEFIT': lo > .02, 'EXCLUDE_PRACTICAL_BENEFIT': hi < .02,
            'HARM': hi < -.01, 'EQUIVALENT': (lo > -.01) & (hi < .01),
            'NONHARM': lo > -.01,
            'INTERACTION': (lo > .02) | (hi < -.02),
            'NO_PRACTICAL_INTERACTION': (lo > -.02) & (hi < .02)}


def _mc_summary(bounds, truth, repetitions):
    events = decisions(bounds['lower'], bounds['upper'])
    events['coverage'] = (bounds['lower'] <= truth) & (truth <= bounds['upper'])
    result = {}
    for name, mask in events.items():
        count = int(np.count_nonzero(mask))
        lo, hi = cp_bounds(count, repetitions, .025)
        result[name] = {'count': count, 'estimate': count/repetitions,
                        'mc_ci95': [float(lo), float(hi)]}
    return result


def _simulation(repetitions, seed, quick):
    if not isinstance(quick, bool):
        raise ValueError('quick must be boolean')
    repetitions = _integer(repetitions, 'repetitions')
    if repetitions < 10000 and not quick:
        raise ValueError('scientific MC requires >=10000 repetitions; quick is engineering only')
    _integer(seed, 'seed', 0)
    return np.random.default_rng(seed)


def paired_power(n, q, delta, m=1, alpha_family=FAMILY_ALPHA,
                 repetitions=10000, seed=0, quick=False):
    n = _integer(n, 'n')
    if not np.isfinite(q) or not np.isfinite(delta) or not 0 <= q <= 1 or abs(delta) > q:
        raise ValueError('require 0<=q<=1 and |delta|<=q')
    rng = _simulation(repetitions, seed, quick)
    probabilities = [(q+delta)/2, (q-delta)/2, 1-q]
    samples = rng.multinomial(n, probabilities, size=repetitions)
    b = paired_delta(samples[:, 0], samples[:, 1], n, alpha_family, m)
    return {'model': 'paired_trinomial_blocks', 'n': n, 'q': q, 'truth': delta,
            'probabilities': probabilities, 'm': m, 'alpha_family': alpha_family,
            'repetitions': repetitions, 'seed': seed, 'engineering_only': quick,
            'results': _mc_summary(b, delta, repetitions)}


def joint_states(k):
    """Lexicographic binary states: first arm is most significant bit."""
    if _integer(k, 'k') not in (4, 8):
        raise ValueError('joint model requires four or eight arms')
    return ((np.arange(2**k)[:, None] >> np.arange(k-1, -1, -1)) & 1)


def joint_probabilities(k, probabilities):
    states = joint_states(k)
    p = np.asarray(probabilities, dtype=float)
    if p.shape != (len(states),) or not np.all(np.isfinite(p)) or np.any(p < 0) or not np.isclose(p.sum(), 1, rtol=0, atol=1e-12):
        raise ValueError('joint probabilities must be nonnegative, finite, and sum to one')
    return states, p


def joint_power(n, probabilities, coefficients, m=1, alpha_family=FAMILY_ALPHA,
                repetitions=10000, seed=0, quick=False):
    n = _integer(n, 'n')
    c = _coefficients(coefficients)
    states, p = joint_probabilities(len(c), probabilities)
    rng = _simulation(repetitions, seed, quick)
    # Every replicate draws n whole joint states, preserving all arm dependence.
    counts = rng.multinomial(n, p, size=repetitions) @ states
    truth = float(p @ states @ c)
    b = linear_contrast(counts, c, n, alpha_family, m)
    return {'model': 'joint_binary_blocks', 'n': n, 'truth': truth,
            'marginals': (p @ states).tolist(), 'probabilities': p.tolist(),
            'coefficients': c.tolist(), 'm': m, 'alpha_family': alpha_family,
            'repetitions': repetitions, 'seed': seed, 'engineering_only': quick,
            'results': _mc_summary(b, truth, repetitions)}


def sufficient_n(coefficients, gap, m=1, alpha_family=FAMILY_ALPHA, beta_error=.1):
    """Finite-sample sufficient n, not optimal n.

    Inverting Hoeffding's binomial tails bounds each CP endpoint's distance
    from its sample mean by w. A 2k union bound gives simultaneous estimation
    error r with probability >=1-beta_error. Thus L*(w+r)<gap suffices.
    """
    c = _coefficients(coefficients)
    if not np.isfinite(gap) or gap <= 0:
        raise ValueError('gap must be finite and positive')
    k = int(np.count_nonzero(c))
    a = _tail(alpha_family, m, k)
    b = _prob(beta_error, 'beta_error')
    constant = float(np.abs(c).sum()) * (math.sqrt(math.log(1/a)/2) + math.sqrt(math.log(2*k/b)/2))
    critical = (constant/gap)**2
    if not math.isfinite(critical):
        raise ValueError('required n exceeds numerical range')
    n = max(1, math.floor(critical)+1)
    while constant/math.sqrt(n) >= gap:
        n += 1
    while n > 1 and constant/math.sqrt(n-1) < gap:
        n -= 1
    return {'n': n, 'gap': gap, 'L': float(np.abs(c).sum()), 'k': k,
            'tail': a, 'beta_error': b, 'width_plus_error': constant/math.sqrt(n),
            'critical_n': critical}


def search_power(evaluate, proposition, target=.9, start=1024, max_n=None):
    """Doubling search, using MC lower bound; not a minimal-n or optional-stop test.

    evaluate(n) must generate a fixed-size planning MC, never receiver data.
    An explicit budget max_n returns unresolved. No implicit 4096 ceiling.
    """
    target = _prob(target, 'target')
    n = _integer(start, 'start')
    if max_n is not None and _integer(max_n, 'max_n') < n:
        raise ValueError('max_n below start')
    history = []
    while True:
        result = evaluate(n)
        if result['n'] != n or result['engineering_only'] or result['repetitions'] < 10000:
            raise ValueError('search requires scientific MC at the requested n')
        history.append(result)
        if result['results'][proposition]['mc_ci95'][0] >= target:
            return {'status': 'SUFFICIENT_ON_SEARCH_GRID', 'n': n, 'history': history}
        if max_n is not None and n == max_n:
            return {'status': 'UNRESOLVED', 'n': None, 'history': history}
        n = n*2 if max_n is None else min(n*2, max_n)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--repetitions', type=int, default=10000)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--n', type=int, default=1024)
    parser.add_argument('--q', type=float, default=.15)
    parser.add_argument('--delta', type=float, default=.05)
    parser.add_argument('--m', type=int, default=1)
    parser.add_argument('--seed', type=int, default=20260909)
    args = parser.parse_args()
    result = paired_power(args.n, args.q, args.delta, args.m,
                          repetitions=args.repetitions, seed=args.seed, quick=args.quick)
    payload = {'command': shlex.join([sys.executable, *sys.argv]),
               'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'numpy': np.__version__, 'scipy': scipy.__version__, 'exit_code': 0,
               'scope': 'one planning scenario; not the full STAT-01 grid', 'simulation': result}
    with Path(args.out).open('x') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
