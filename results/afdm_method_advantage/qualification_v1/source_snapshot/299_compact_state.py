"""Exact CPP correlation field and compact fixed-q replacement scores.

This is an algebraic implementation of the existing ridge objective, not a
posterior approximation.  Production path actions and Gamma are supplied by
the caller; beta is frozen for the structural stage.
"""

from dataclasses import dataclass

import numpy as np
from scipy.fft import fft, ifft, next_fast_len
from scipy.linalg import cho_factor, cho_solve


class CPPField:
    """Return phi(delay, Doppler)^H z in delay-major grid order."""

    def __init__(self, x_time, c1, max_delay, dopplers):
        self.x = np.asarray(x_time, dtype=np.complex128)
        self.n = len(self.x)
        self.L = int(max_delay)
        self.nus = np.asarray(dopplers, dtype=float)
        if (self.x.ndim != 1 or self.n < 2 or not np.isfinite(self.x).all()
                or not np.isfinite(c1) or self.L != max_delay
                or not 0 <= self.L < self.n or self.nus.ndim != 1
                or not len(self.nus) or not np.isfinite(self.nus).all()):
            raise ValueError("invalid CPP correlation field input")
        t = np.arange(-self.L, self.n)
        extended = self.x[t % self.n].copy()
        wrapped = t < 0
        extended[wrapped] *= np.exp(
            2j * np.pi * c1 * (self.n * self.n + 2 * self.n * t[wrapped]))
        self.length = next_fast_len(2 * self.n + self.L - 1)
        self.kernel = fft(np.conj(extended[::-1]), self.length)
        self.demod = np.exp(-2j * np.pi * self.nus[:, None]
                            * np.arange(self.n)[None, :] / self.n)
        self.calls = 0

    def correlate(self, z):
        z = np.asarray(z, dtype=np.complex128)
        if z.shape != (self.n,) or not np.isfinite(z).all():
            raise ValueError("invalid CPP correlation vector")
        product = fft(self.demod * z[None, :], self.length, axis=1)
        result = ifft(product * self.kernel[None, :], axis=1)
        self.calls += 1
        return result[:, self.n - 1:self.n + self.L].T.reshape(-1).copy()


@dataclass
class CompactState:
    normal: np.ndarray
    inverse: np.ndarray
    rhs: np.ndarray
    gains: np.ndarray
    objective: float


def state_from_normal(normal, rhs, y_energy):
    A = np.asarray(normal, dtype=np.complex128)
    rhs = np.asarray(rhs, dtype=np.complex128)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or rhs.shape != (len(A),):
        raise ValueError("invalid compact normal equations")
    A = (A + A.conj().T) / 2
    factor = cho_factor(A, lower=True, check_finite=True)
    inverse = cho_solve(factor, np.eye(len(A)), check_finite=True)
    inverse = (inverse + inverse.conj().T) / 2
    gains = cho_solve(factor, rhs, check_finite=True)
    value = float(y_energy - np.vdot(rhs, gains).real)
    if not np.isfinite(value):
        raise FloatingPointError("nonfinite compact objective")
    return CompactState(A, inverse, rhs, gains, value)


def exchange_scores(state, cross, beta, diagonal):
    """Every slot-by-candidate replacement score from one compact state."""
    K = np.asarray(cross, dtype=np.complex128)
    beta = np.asarray(beta, dtype=np.complex128)
    if K.ndim != 2 or K.shape[0] != len(state.gains) or beta.shape != (K.shape[1],):
        raise ValueError("invalid compact cross-kernel")
    u = state.inverse @ K
    slack = diagonal - np.sum(K.conj() * u, axis=0).real
    if not np.isfinite(slack).all() or np.any(slack <= 0):
        raise FloatingPointError("nonpositive/nonfinite compact Schur complement")
    innovation = beta - K.conj().T @ state.gains
    gain_new = innovation / slack
    old_after_add = state.gains[:, None] - u * gain_new[None, :]
    cavity = np.diag(state.inverse).real[:, None] + abs(u) ** 2 / slack[None, :]
    if not np.isfinite(cavity).all() or np.any(cavity <= 0):
        raise FloatingPointError("nonpositive/nonfinite compact cavity")
    deletion = abs(old_after_add) ** 2 / cavity
    addition = abs(innovation) ** 2 / slack
    values = state.objective - addition[None, :] + deletion
    if not np.isfinite(values).all():
        raise FloatingPointError("nonfinite compact replacement score")
    return values, dict(minimum_slack=float(slack.min()),
                        minimum_cavity=float(cavity.min()))
