"""Fixed-state CE derivatives; no receiver performance claim or truth input."""
import numpy as np


def ce_direction(A, y, previous, regularization, dA):
    """Differentiate a complex proximal LS solve along a real scalar stimulus.

    Support, y, previous gains and regularization are held fixed. This is the
    mean-only CE objective, not a derivative through the entire receiver.
    """
    A, y, previous, dA = [np.asarray(v, dtype=np.complex128)
                           for v in (A, y, previous, dA)]
    if (A.ndim != 2 or min(A.shape) < 1 or y.shape != (A.shape[0],)
            or previous.shape != (A.shape[1],) or dA.shape != A.shape
            or type(regularization) not in (float, int)
            or not np.isfinite(regularization) or regularization <= 0
            or any(not np.isfinite(v).all() for v in (A, y, previous, dA))):
        raise ValueError('finite matched proximal CE inputs and positive lambda required')
    lhs = A.conj().T @ A + regularization * np.eye(A.shape[1])
    rhs = A.conj().T @ y + regularization * previous
    gain = np.linalg.solve(lhs, rhs)
    tangent_rhs = dA.conj().T @ (y - A @ gain) - A.conj().T @ dA @ gain
    derivative = np.linalg.solve(lhs, tangent_rhs)
    return gain, derivative


def mean_design_direction(app, bit, delays, dopplers, c1, c2, k_max=2):
    """QPSK tanh moment derivative through the registered integer AFDM atoms."""
    app = np.asarray(app)
    dl, dk = np.asarray(delays), np.asarray(dopplers)
    if (app.ndim != 1 or len(app) % 2 or not len(app) or np.iscomplexobj(app)
            or not np.isfinite(app).all() or type(bit) is not int or not 0 <= bit < len(app)
            or abs(app[bit]) >= 8 or dl.ndim != 1 or not len(dl) or dk.shape != dl.shape
            or not np.issubdtype(dl.dtype, np.integer) or not np.issubdtype(dk.dtype, np.integer)
            or not np.isfinite([c1, c2]).all() or type(k_max) is not int or k_max < 0):
        raise ValueError('unsaturated bit, integer support and finite chirp parameters required')
    n = len(app) // 2
    symbol = bit % n
    out = (symbol + (2 * k_max + 1) * dl + dk) % n
    phase = np.exp(2j * np.pi * (-c1 * dl ** 2 + c2 * (out ** 2 - symbol ** 2)
                                 - symbol * dl / n))
    tangent = .25 / np.cosh(app[bit] / 2) ** 2
    if bit >= n:
        tangent *= 1j
    result = np.zeros((n, len(dl)), dtype=np.complex128)
    result[out, np.arange(len(dl))] = phase * tangent
    return result


def eligible_bits(channel, prior):
    """First unsaturated I and Q bits; ordering is independent of truth/errors."""
    channel, prior = np.asarray(channel), np.asarray(prior)
    if (channel.ndim != 1 or not len(channel) or len(channel) % 2
            or prior.shape != channel.shape or np.iscomplexobj(channel) or np.iscomplexobj(prior)
            or not np.isfinite(channel).all() or not np.isfinite(prior).all()):
        raise ValueError('finite matched real channel and prior LLR vectors required')
    allowed = (np.abs(channel + prior) < 8) & (np.abs(prior) < 19.9)
    n = len(channel) // 2
    result = []
    for start in (0, n):
        indices = np.flatnonzero(allowed[start:start + n])
        if indices.size:
            result.append(start + int(indices[0]))
    return result
