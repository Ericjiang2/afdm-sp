"""Frozen shortlist repair; reuse the previously qualified physical/likelihood core.

The older estimator remains immutable. This entry point changes only the
shortlist and excludes standalone FOURTH; every complete call owns preprocessing.
"""
import numpy as np

from experiments.afdm_acquisition_performance_20261007.core import (
    fourth_scores, gain_grid, profile_likelihood, row_chirp, simulate,
)

__all__ = ['ARMS', 'METHODS', 'estimate', 'simulate']
ARMS = ('quadratic', 'random')
METHODS = ('SCREEN128', 'FULL')


def estimate(y, v, sigma2, method):
    """Complete call: validate, construct transforms/templates, search, output.

    Only observations, known code, known noise and fixed method enter. No cache.
    """
    y, v = np.asarray(y), np.asarray(v)
    if y.ndim != 2 or y.shape[0] < 1 or y.shape[1] < 4 or y.shape[1] % 4:
        raise ValueError('finite T by N observation with N divisible by four required')
    n = y.shape[1]
    if v.shape != (n,) or not np.isfinite(v).all() or not np.allclose(np.abs(v), 1., atol=1e-12, rtol=0):
        raise ValueError('known unit-modulus code of length N required')
    if not np.isfinite(y).all() or not np.isscalar(sigma2) or not np.isfinite(sigma2) or sigma2 <= 0:
        raise ValueError('finite observations and positive noise variance required')
    if method not in METHODS:
        raise ValueError('unknown acquisition method')
    x = np.fft.fft(y*np.conj(row_chirp(n)), axis=1, norm='ortho')
    fourth = fourth_scores(x, v) if method != 'FULL' else np.empty((0,))
    hypotheses = np.arange(n*(n//4))
    if method == 'SCREEN128':
        shortlist = np.argsort(-fourth.ravel(), kind='stable')[:128]
        hypotheses = np.sort(shortlist)
    scores, best_gains = profile_likelihood(x, v, sigma2, hypotheses)
    index = int(np.argmax(scores))
    selected, gain_index = int(hypotheses[index]), int(best_gains[index])
    objective, ties = float(scores[index]), int(np.count_nonzero(scores == scores[index]))
    physical_gain = gain_grid()[gain_index]*np.exp(5j*np.pi*(selected % (n//4))**2/n)
    physical_gain = [float(physical_gain.real), float(physical_gain.imag)]
    a, delay = divmod(selected, n//4)
    if not np.isfinite(objective) or not np.isfinite(scores).all() or not np.isfinite(fourth).all():
        raise FloatingPointError('nonfinite acquisition score')
    return dict(a=a, delay=delay, cfo=(a-5*delay) % n, objective=objective,
                gain_index=gain_index, physical_gain_mod_C4=physical_gain, exact_ties=ties,
                hypotheses=hypotheses, profile_scores=scores, best_gain_indices=best_gains,
                fourth_scores=fourth, likelihood_hypotheses=len(hypotheses),
                gain_grid_evaluations=48*len(hypotheses))
