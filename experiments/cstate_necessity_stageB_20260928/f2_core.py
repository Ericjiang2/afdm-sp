"""Corrected SISO Gaussian posterior kernels for synthetic F2 reference checks.

This module does not select support, evolve grids, feed back data, or run a
receiver. Its fixed-parameter inputs are supplied by an external test.
"""

from __future__ import annotations

import numpy as np


def _inputs(phi: np.ndarray, y: np.ndarray, delta: np.ndarray,
            beta: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    matrix = np.asarray(phi, dtype=np.complex128)
    observed = np.asarray(y, dtype=np.complex128)
    variances = np.asarray(delta, dtype=np.float64)
    if (matrix.ndim != 2 or observed.shape != (matrix.shape[0],)
            or variances.shape != (matrix.shape[1],) or matrix.shape[1] < 1
            or not np.isfinite(matrix).all() or not np.isfinite(observed).all()
            or not np.isfinite(variances).all() or np.any(variances <= 0)
            or not np.isfinite(beta) or beta <= 0):
        raise ValueError("invalid fixed-parameter complex Gaussian model")
    return matrix, observed, variances


def full_gesbl_posterior(phi: np.ndarray, y: np.ndarray,
                         delta: np.ndarray, beta: float) -> tuple[np.ndarray, np.ndarray]:
    """Paper's full posterior Eqs. sigma/miu for one receive antenna."""
    matrix, observed, variances = _inputs(phi, y, delta, beta)
    precision = beta * (matrix.conj().T @ matrix) + np.diag(1 / variances)
    covariance = np.linalg.solve(precision, np.eye(len(variances)))
    mean = beta * (covariance @ matrix.conj().T @ observed)
    return mean, covariance


def corrected_gamp_posterior(phi: np.ndarray, y: np.ndarray, delta: np.ndarray,
                             beta: float, *, iterations: int,
                             damping_s: float, damping_h: float) -> tuple[np.ndarray, np.ndarray]:
    """Alg.3 Gaussian inner messages with explicit variance/adjoint repairs.

    Executes exactly ``iterations``; this algebra-only kernel does not choose
    the paper's unreported convergence threshold or iteration cap.
    """
    matrix, observed, variances = _inputs(phi, y, delta, beta)
    if (iterations < 1 or not 0 < damping_s <= 1 or not 0 < damping_h <= 1):
        raise ValueError("invalid synthetic GAMP iteration configuration")
    power = abs(matrix) ** 2
    mean = np.zeros(len(variances), dtype=np.complex128)
    variance = variances.copy()
    s = np.zeros(len(observed), dtype=np.complex128)
    for _ in range(iterations):
        v_p = power @ variance
        p = matrix @ mean - v_p * s
        s = (1 - damping_s) * s + damping_s * (observed - p) / (1 / beta + v_p)
        v_s = 1 / (1 / beta + v_p)
        denominator = power.T @ v_s
        if np.any(denominator <= 0):
            raise ValueError("unobserved Gaussian coefficient")
        v_u = 1 / denominator
        u = mean + v_u * (matrix.conj().T @ s)
        candidate = variances * u / (variances + v_u)
        mean = (1 - damping_h) * mean + damping_h * candidate
        variance = variances * v_u / (variances + v_u)
        if not np.isfinite(mean).all() or not np.isfinite(variance).all():
            raise FloatingPointError("nonfinite Gaussian GAMP message")
    return mean, variance
