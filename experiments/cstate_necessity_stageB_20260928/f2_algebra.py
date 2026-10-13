"""Algebra-only checks for printed D-GAMP-GESBL formulas; no receiver."""

from __future__ import annotations

import numpy as np


def gaussian_input_posterior(u: complex, v_u: float, delta: float) -> tuple[complex, float]:
    """CN(0, delta) times CN(u, v_u), with delta a variance."""
    if v_u <= 0 or delta <= 0:
        raise ValueError("Gaussian variances must be positive")
    variance = 1.0 / (1.0 / delta + 1.0 / v_u)
    return variance * u / v_u, variance


def gaussian_output_precision(beta: float, v_p: float) -> float:
    """Negative derivative of g_S=(y-p)/(beta^-1+v_p)."""
    if beta <= 0 or v_p < 0:
        raise ValueError("noise precision/latent variance must be nonnegative")
    return 1.0 / (1.0 / beta + v_p)


def complex_adjoint(phi: np.ndarray, residual: np.ndarray) -> np.ndarray:
    """The complex-linear adjoint required by z=Phi h."""
    return np.asarray(phi).conj().T @ np.asarray(residual)
