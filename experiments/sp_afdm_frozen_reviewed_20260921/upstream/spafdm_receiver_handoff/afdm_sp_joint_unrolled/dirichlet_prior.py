"""Fixed-support Dirichlet shrinkage prior for integer Doppler gains.

The prior integrates a single fractional Doppler offset per delay group.  Group
centres are selected once from the initial gains; this module does not estimate
continuous Doppler or inspect channel truth.
"""

from __future__ import annotations

import numbers

import numpy as np


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{label} must be a positive integer")
    value = int(value)
    if value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _integer_vector(value: object, label: str, *, nonempty: bool = True) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != 1 or (nonempty and array.size == 0):
        raise ValueError(f"{label} must be a nonempty one-dimensional array")
    if array.dtype.kind == "b" or array.dtype.kind not in "iuf":
        raise ValueError(f"{label} must contain finite integers")
    if not np.isfinite(array).all() or not np.equal(array, np.floor(array)).all():
        raise ValueError(f"{label} must contain finite integers")
    return array.astype(np.int64, copy=False)


def _dirichlet_coefficients(n: int, offsets: np.ndarray, kappa: np.ndarray) -> np.ndarray:
    """Evaluate alpha(-m, kappa) using a cancellation-safe sinc ratio."""
    x = kappa[:, None] - offsets[None, :]
    denominator = np.sinc(x / n)
    ratio = np.empty_like(x, dtype=np.float64)
    regular = np.abs(denominator) > 32 * np.finfo(np.float64).eps
    ratio[regular] = np.sinc(x[regular]) / denominator[regular]

    # The ratio limit at x=qN is (-1) ** (q * (N - 1)).  Gauss nodes do not
    # normally land there, but handling it makes the closed form complete.
    if not regular.all():
        quotient = np.rint(x[~regular] / n).astype(np.int64)
        ratio[~regular] = np.where((quotient * (n - 1)) % 2 == 0, 1.0, -1.0)
    phase = np.exp(1j * np.pi * (n - 1) * x / n)
    return phase * ratio


def covariance(n: int, integer_offsets: object, quadrature: int = 128) -> np.ndarray:
    """Return ``E[b(kappa)b(kappa)^H]`` for uniform ``kappa`` in [-.5, .5].

    ``b_m(kappa)`` is the physical finite-DFT coefficient
    ``N^-1 sum_t exp(2j*pi*(kappa-m)*t/N)``, equivalently the production
    generator's ``dirichlet_alpha(-m, kappa, N)``.
    """
    n = _positive_integer(n, "n")
    quadrature = _positive_integer(quadrature, "quadrature")
    offsets = _integer_vector(integer_offsets, "integer_offsets")
    if np.unique(offsets).size != offsets.size:
        raise ValueError("integer_offsets must be unique")

    nodes, weights = np.polynomial.legendre.leggauss(quadrature)
    kappa = nodes / 2.0
    weights = weights / 2.0
    coefficients = _dirichlet_coefficients(n, offsets, kappa)
    result = coefficients.T @ (weights[:, None] * coefficients.conj())
    return (result + result.conj().T) / 2.0


def build_precision(
    n: int,
    delays: object,
    dopplers: object,
    initial_gains: object,
    kind: str = "dirichlet",
    epsilon: float = 0.05,
) -> dict[str, np.ndarray]:
    """Build a trace-matched zero-centred precision on a fixed integer support.

    Each delay group freezes its centre at the largest initial gain magnitude;
    exact ties choose the smallest Doppler bin.  The returned ``centers`` array
    follows the input support order and repeats the group centre for each atom.
    """
    n = _positive_integer(n, "n")
    if not isinstance(kind, str) or kind not in {"dirichlet", "diagonal", "ridge"}:
        raise ValueError("kind must be 'dirichlet', 'diagonal', or 'ridge'")
    if isinstance(epsilon, (bool, np.bool_)) or not isinstance(epsilon, numbers.Real):
        raise ValueError("epsilon must be positive and finite")
    epsilon = float(epsilon)
    if not np.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("epsilon must be positive and finite")

    delays_array = _integer_vector(delays, "delays")
    dopplers_array = _integer_vector(dopplers, "dopplers")
    gains = np.asarray(initial_gains)
    size = delays_array.size
    if dopplers_array.shape != (size,) or gains.shape != (size,):
        raise ValueError("delays, dopplers, and initial_gains must have equal lengths")
    if (delays_array < 0).any() or (delays_array >= n).any():
        raise ValueError("delays must be in the range [0, n)")
    if gains.dtype.kind not in "iufc" or not np.isfinite(gains).all():
        raise ValueError("initial_gains must contain finite numeric values")
    # Integer DFT atoms are periodic in Doppler.  Reject modulo-N aliases even
    # when their literal Doppler labels differ, so each support pair is physical.
    pairs = np.column_stack((delays_array, np.mod(dopplers_array, n)))
    if np.unique(pairs, axis=0).shape[0] != size:
        raise ValueError("delay-Doppler support pairs must be unique modulo n")

    identity = np.eye(size, dtype=np.complex128)
    centers = np.empty(size, dtype=np.int64)
    covariance_matrix = np.zeros((size, size), dtype=np.complex128)

    for delay in np.unique(delays_array):
        group = np.flatnonzero(delays_array == delay)
        magnitudes = np.abs(gains[group])
        candidates = group[magnitudes == magnitudes.max()]
        center = int(dopplers_array[candidates].min())
        centers[group] = center
        offsets = dopplers_array[group] - center
        covariance_matrix[np.ix_(group, group)] = covariance(n, offsets)

    if kind == "ridge":
        return {"precision": identity.copy(), "covariance": identity, "centers": centers}

    trace = float(np.trace(covariance_matrix).real)
    if not np.isfinite(trace) or trace <= 0:
        raise ValueError("Dirichlet covariance has invalid trace")
    covariance_matrix *= size / trace
    if kind == "diagonal":
        covariance_matrix = np.diag(np.diag(covariance_matrix)).astype(np.complex128)
    covariance_matrix += epsilon * identity
    covariance_matrix = (covariance_matrix + covariance_matrix.conj().T) / 2.0

    precision = np.linalg.inv(covariance_matrix)
    precision = (precision + precision.conj().T) / 2.0
    precision_trace = float(np.trace(precision).real)
    if not np.isfinite(precision_trace) or precision_trace <= 0:
        raise ValueError("Dirichlet precision has invalid trace")
    precision *= size / precision_trace
    return {
        "precision": precision,
        "covariance": covariance_matrix,
        "centers": centers,
    }
