"""Paired cluster bootstrap for saved, complete observations (NumPy only).

The estimand is the pooled row mean, not the unweighted mean of cluster means.
One multinomial draw is shared by every arm/metric. Callers own the scientific
cluster definition, key completeness and the provenance of observations.
"""
from __future__ import annotations

import numpy as np


def cluster_totals(values, cluster_ids):
    names = list(values)
    if not names:
        raise ValueError('no metrics')
    ids = np.asarray(cluster_ids, dtype=str)
    if ids.ndim != 1 or len(ids) == 0:
        raise ValueError('cluster_ids must be a nonempty one-dimensional sequence')
    labels, inverse = np.unique(ids, return_inverse=True)
    sums = np.empty((len(labels), len(names)), float)
    for j, name in enumerate(names):
        v = np.asarray(values[name], float)
        if v.shape != ids.shape or not np.all(np.isfinite(v)):
            raise ValueError(f'{name}: nonfinite values or shape mismatch')
        sums[:, j] = np.bincount(inverse, weights=v, minlength=len(labels))
    sizes = np.bincount(inverse, minlength=len(labels)).astype(float)
    return names, sums, sizes


def bootstrap_means(values, cluster_ids, n_boot=20000, seed=20261017, batch_size=256):
    """Return ({metric: bootstrap draws}, cluster count), using bounded batches.

    RNG and sorted string labels match the frozen E1 bootstrap implementation.
    All rows of one cluster are always resampled jointly, including reused
    scenario/rho/SNR strata. Input order does not change the cluster sums.
    """
    if not isinstance(n_boot, int) or n_boot <= 0 or batch_size <= 0:
        raise ValueError('n_boot and batch_size must be positive integers')
    names, sums, sizes = cluster_totals(values, cluster_ids)
    m = len(sizes)
    result = np.empty((n_boot, len(names)), float)
    rng = np.random.default_rng(seed)
    for start in range(0, n_boot, batch_size):
        n = min(batch_size, n_boot - start)
        counts = rng.multinomial(m, np.full(m, 1. / m), size=n).astype(float)
        result[start:start+n] = (counts @ sums) / (counts @ sizes)[:, None]
    return {name: result[:, j] for j, name in enumerate(names)}, m


def interval(values):
    v = np.asarray(values, float)
    if not len(v) or not np.all(np.isfinite(v)):
        raise ValueError('interval requires nonempty finite draws')
    lo, hi = np.percentile(v, [2.5, 97.5])
    return dict(ci_lo=float(lo), ci_hi=float(hi), ci_width=float(hi-lo),
                contains_0=bool(lo <= 0 <= hi))


def combine(values, weights):
    if not weights:
        raise ValueError('empty linear contrast')
    return sum(weight * values[name] for name, weight in weights.items())


def linear_summary(point, draws, weights):
    return dict(point=float(combine(point, weights)), **interval(combine(draws, weights)))


def ratio_summary(point, draws, numerator, denominator, limit=.01):
    """Conditional CI plus explicit denominator failures; never certify bad ratios.

    The CI over positive-denominator draws is retained for historical comparison
    even when >limit fails, and must not be treated as an evaluable interval.
    """
    np_, dp = float(combine(point, numerator)), float(combine(point, denominator))
    nb, db = combine(draws, numerator), combine(draws, denominator)
    valid = db > 0
    fraction = float(np.mean(~valid))
    ci = interval(nb[valid] / db[valid]) if np.any(valid) else dict(
        ci_lo=None, ci_hi=None, ci_width=None, contains_0=None)
    return dict(point=np_/dp if dp > 0 else None, **ci,
                denominator_point=dp, denominator_nonpositive_fraction=fraction,
                evaluable=bool(dp > 0 and fraction <= limit and np.any(valid)),
                ci_condition='bootstrap denominator > 0', failure_limit=limit)
