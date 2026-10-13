"""Observed-only cancellation working covariance and fixed whitening transforms.

Sigma is a working approximation, not an estimator posterior. A is sensing on
pilot+x_soft and P is pilot sensing on the same ordered legal support. The caller
owns support provenance. Row scaling/whitening can change the graph selected by
BP's fixed absolute threshold; covariance identities do not imply an unchanged
BP graph or improved receiver performance.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import solve_triangular


def _array(value, ndim, name):
    result = np.asarray(value, dtype=np.complex128)
    if result.ndim != ndim or not np.isfinite(result).all():
        raise ValueError(f'{name} must be a finite {ndim}-dimensional array')
    return result


def _positive(value, name):
    if isinstance(value, (bool, complex)) or np.ndim(value) != 0:
        raise ValueError(f'{name} must be a positive real scalar')
    result = float(value)
    if not np.isfinite(result) or result <= 0:
        raise ValueError(f'{name} must be a positive real scalar')
    return result


def working_factor(A, P, sigma_base, ridge_relative=.01):
    """Return B with B B^H = P [sigma_base (A^H A+lambda I)^-1] P^H."""
    A = _array(A, 2, 'A')
    P = _array(P, 2, 'P')
    sigma = _positive(sigma_base, 'sigma_base')
    ridge = _positive(ridge_relative, 'ridge_relative')
    n, k = A.shape
    if n == 0 or P.shape != (n, k) or k > 40:
        raise ValueError('A/P must share nonempty observation rows and K<=40 columns')
    if k == 0:
        return {'B': np.zeros((n, 0), dtype=np.complex128), 'diagnostics': {
            'model': 'working covariance, not posterior', 'N': n, 'K': 0,
            'rank_A': 0, 'rank_B': 0, 'ridge_relative': ridge, 'ridge_lambda': 0.,
            'regularized_condition': None, 'trace_BBH': 0., 'zero_support': True}}
    gram = A.conj().T @ A
    lam = ridge * float(np.trace(gram).real) / k
    if not np.isfinite(lam) or lam <= 0:
        raise ValueError('zero/nonfinite sensing energy cannot define the registered ridge')
    regularized = gram + lam * np.eye(k)
    chol = np.linalg.cholesky(regularized)
    B = np.sqrt(sigma) * solve_triangular(chol, P.conj().T, lower=True).conj().T
    if not np.isfinite(B).all():
        raise ValueError('working factor is nonfinite')
    return {'B': B, 'diagnostics': {
        'model': 'working covariance, not posterior', 'N': n, 'K': k,
        'rank_A': int(np.linalg.matrix_rank(A)), 'rank_B': int(np.linalg.matrix_rank(B)),
        'ridge_relative': ridge, 'ridge_lambda': lam,
        'regularized_condition': float(np.linalg.cond(regularized)),
        'trace_BBH': float(np.sum(np.abs(B)**2)), 'zero_support': False}}


def transform(z, H, B, sigma_base, mode):
    """Apply scalar, diagonal or low-rank cancellation-noise working model."""
    z = _array(z, 1, 'z')
    H = _array(H, 2, 'H')
    B = _array(B, 2, 'B')
    sigma = _positive(sigma_base, 'sigma_base')
    n = len(z)
    if n == 0 or H.shape[0] != n or H.shape[1] == 0 or B.shape[0] != n or B.shape[1] > 40:
        raise ValueError('incompatible observation dimensions or K>40')
    if mode not in ('scalar', 'diagonal', 'lowrank'):
        raise ValueError('unknown cancellation covariance mode')
    diagonal = np.sum(np.abs(B)**2, axis=1)
    sigma_out = sigma
    if mode == 'scalar':
        zout, hout = z.copy(), H.copy()
        sigma_out = sigma + float(np.mean(diagonal))
        factors = np.ones(n)
    elif mode == 'diagonal':
        factors = np.sqrt(sigma / (sigma + diagonal))
        zout, hout = factors*z, factors[:, None]*H
    else:
        U, singular, _ = np.linalg.svd(B, full_matrices=False)
        factors = 1 / np.sqrt(1 + singular**2/sigma)
        correction = factors - 1
        zout = z + U @ (correction * (U.conj().T @ z))
        hout = H + U @ (correction[:, None] * (U.conj().T @ H))
    if not np.isfinite(zout).all() or not np.isfinite(hout).all() or not np.isfinite(sigma_out):
        raise ValueError('nonfinite cancellation transform')
    return {'z': zout, 'H': hout, 'sigma_out': sigma_out, 'diagnostics': {
        'mode': mode, 'N': n, 'H_columns': H.shape[1], 'K': B.shape[1],
        'rank_B': int(np.linalg.matrix_rank(B)) if B.shape[1] else 0,
        'trace_BBH': float(np.sum(diagonal)), 'sigma_base': sigma,
        'scale_min': float(np.min(factors)) if factors.size else 1.,
        'scale_max': float(np.max(factors)) if factors.size else 1.,
        'zero_support': B.shape[1] == 0,
        'graph_limitation': 'transform may change fixed-threshold BP graph'}}
