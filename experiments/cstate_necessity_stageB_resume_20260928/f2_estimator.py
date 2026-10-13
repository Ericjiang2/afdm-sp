"""Outcome-blind corrected SISO GAMP-GESBL specialization.

The numerical choices are frozen in F2_METHOD_CONTRACT.md. This module accepts
only observation arrays; it does not import a receiver, decoder, or truth store.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor, log
import time

import numpy as np
from scipy.optimize import minimize

from physical import Channel, daft, projected_variance, regressors


@dataclass(frozen=True)
class F2Config:
    qmax: int = 100
    imax: int = 20
    tmax: int = 4
    epsilon_q: float = 1e-6
    epsilon_g: float = 1e-6
    epsilon_t: float = 1e-6
    damping_s: float = 0.5
    damping_h: float = 0.5
    qp_maxiter: int = 100
    qp_ftol: float = 1e-12
    qp_gtol: float = 1e-8


FROZEN = F2Config()


def hard_qpsk(values: np.ndarray) -> np.ndarray:
    """Project to the project's power-0.5 QPSK, positive at an exact tie."""
    x = np.asarray(values, dtype=np.complex128)
    if not np.isfinite(x).all():
        raise FloatingPointError("nonfinite data estimate")
    return 0.5 * np.where(x.real >= 0, 1, -1) + 0.5j * np.where(x.imag >= 0, 1, -1)


def initial_grid(max_delay: int, nu_min: float, nu_max: float,
                 nu_step: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    if max_delay < 0 or nu_step <= 0 or nu_max <= nu_min:
        raise ValueError("invalid physical grid")
    count = int(round((nu_max - nu_min) / nu_step)) + 1
    centers = nu_min + nu_step * np.arange(count, dtype=float)
    if not np.isclose(centers[-1], nu_max, rtol=0, atol=1e-12):
        raise ValueError("Doppler interval must close on the frozen grid")
    return np.repeat(np.arange(max_delay + 1), count), np.tile(centers, max_delay + 1)


def active_indices(delta: np.ndarray, n: int) -> np.ndarray:
    """Paper communications top-Rbar rule; grid index resolves ties."""
    m = len(delta)
    if m < 2 or n < 2 or np.any(~np.isfinite(delta)) or np.any(delta <= 0):
        raise ValueError("invalid active-set prior")
    count = min(m, floor(n / log(m)))
    if count < 1:
        raise ValueError("empty communications support")
    return np.lexsort((np.arange(m), -delta))[:count]


def _relative_change(current: np.ndarray, previous: np.ndarray) -> float:
    return float(np.vdot(current - previous, current - previous).real /
                 max(float(np.vdot(previous, previous).real), 1e-30))


def _posterior(phi: np.ndarray, y: np.ndarray, delta: np.ndarray, beta: float,
               mode: str, config: F2Config) -> tuple[np.ndarray, np.ndarray, dict]:
    """Full GESBL reference or corrected Alg.3 diagonal GAMP posterior."""
    m = len(delta)
    if mode == "full":
        if m > 64:
            raise ValueError("full covariance is a small synthetic reference only")
        covariance = np.linalg.solve(
            beta * (phi.conj().T @ phi) + np.diag(1 / delta), np.eye(m))
        covariance = (covariance + covariance.conj().T) * 0.5
        mean = beta * (covariance @ phi.conj().T @ y)
        variance = np.diag(covariance).real
        if np.any(variance <= 0) or not np.isfinite(mean).all():
            raise FloatingPointError("invalid full Gaussian posterior")
        return mean, covariance, {"iterations": 1, "converged": True,
                                  "variance": variance}
    if mode != "gamp":
        raise ValueError("unknown posterior mode")

    power = abs(phi) ** 2
    phi_h = phi.conj().T
    mean = np.zeros(m, dtype=np.complex128)
    variance = delta.copy()
    s = np.zeros(len(y), dtype=np.complex128)
    converged = False
    for iteration in range(1, config.qmax + 1):
        old = mean.copy()
        v_p = power @ variance
        denominator = 1 / beta + v_p
        if np.any(denominator <= 0) or not np.isfinite(denominator).all():
            raise FloatingPointError("invalid GAMP output variance")
        p = phi @ mean - v_p * s
        s = (1 - config.damping_s) * s + config.damping_s * (y - p) / denominator
        v_s = 1 / denominator  # positive -partial g_S / partial P
        precision = power.T @ v_s
        if np.any(precision <= 0) or not np.isfinite(precision).all():
            raise FloatingPointError("unobserved or nonfinite GAMP coefficient")
        v_u = 1 / precision
        u = mean + v_u * (phi_h @ s)
        candidate = delta * u / (delta + v_u)
        mean = (1 - config.damping_h) * mean + config.damping_h * candidate
        variance = delta * v_u / (delta + v_u)
        if (not np.isfinite(mean).all() or not np.isfinite(variance).all()
                or np.any(variance <= 0)):
            raise FloatingPointError("nonfinite corrected GAMP posterior")
        if iteration >= 2 and _relative_change(mean, old) <= config.epsilon_q:
            converged = True
            break
    return mean, variance, {"iterations": iteration,
                            "converged": converged, "variance": variance}


def _solve_grid_qp(quadratic: np.ndarray, alpha: np.ndarray,
                   bounds: list[tuple[float, float]],
                   config: F2Config) -> tuple[np.ndarray, dict]:
    """Solve the unchanged real box QP in diagonally scaled coordinates."""
    diagonal = np.diag(quadratic)
    if not np.isfinite(diagonal).all() or np.any(diagonal <= 0):
        raise FloatingPointError("grid QP has nonpositive diagonal scale")
    scale = np.sqrt(diagonal)
    scaled_q = (quadratic / scale[:, None]) / scale[None, :]
    scaled_alpha = alpha / scale
    scaled_bounds = [(lo * scale[j], hi * scale[j])
                     for j, (lo, hi) in enumerate(bounds)]

    def objective(z: np.ndarray) -> tuple[float, np.ndarray]:
        qz = scaled_q @ z
        return float(z @ qz - 2 * scaled_alpha @ z), 2 * (qz - scaled_alpha)

    solved = minimize(objective, np.zeros(len(alpha)), jac=True,
                      bounds=scaled_bounds, method="L-BFGS-B",
                      options={"maxiter": config.qp_maxiter, "ftol": config.qp_ftol,
                               "gtol": config.qp_gtol})
    if not solved.success or not np.isfinite(solved.x).all():
        raise FloatingPointError(f"grid QP failed: {solved.message}")
    kappa = solved.x / scale
    original_gradient = 2 * (quadratic @ kappa - alpha)
    scaled_gradient = 2 * (scaled_q @ solved.x - scaled_alpha)
    original_lo, original_hi = np.asarray(bounds).T
    scaled_lo, scaled_hi = np.asarray(scaled_bounds).T
    original_kkt = np.max(abs(kappa - np.clip(kappa - original_gradient,
                                            original_lo, original_hi)))
    scaled_kkt = np.max(abs(solved.x - np.clip(solved.x - scaled_gradient,
                                              scaled_lo, scaled_hi)))
    return kappa, {"iterations": int(solved.nit),
                   "objective": float(kappa @ quadratic @ kappa - 2 * alpha @ kappa),
                   "max_shift": float(np.max(abs(kappa))),
                   "termination_reason": str(solved.message),
                   "original_kkt_projected_inf": float(original_kkt),
                   "scaled_kkt_projected_inf": float(scaled_kkt)}


def _grid_update(y: np.ndarray, x: np.ndarray, phi: np.ndarray,
                 delays: np.ndarray, nus: np.ndarray, mean: np.ndarray,
                 covariance: np.ndarray, selected: np.ndarray, c1: float,
                 c2: float, nu_min: float, nu_max: float,
                 config: F2Config) -> tuple[np.ndarray, dict]:
    """Simultaneous real expected-loss QP on selected Doppler offsets."""
    derivative = Channel(len(y), c1, c2, delays[selected], nus[selected],
                         np.ones(len(selected), complex)).regressors(x, derivative=True)
    residual = y - phi @ mean
    chosen_mean = mean[selected]
    if covariance.ndim == 1:
        correction = covariance[selected] * np.einsum(
            "nj,nj->j", derivative.conj(), phi[:, selected])
        moment = (np.diag(covariance[selected])
                  + np.outer(chosen_mean, chosen_mean.conj()))
    else:
        correction = np.einsum("nj,nj->j", derivative.conj(),
                               phi @ covariance[:, selected])
        moment = (covariance[np.ix_(selected, selected)]
                  + np.outer(chosen_mean, chosen_mean.conj()))
    alpha = np.real(chosen_mean.conj() * (derivative.conj().T @ residual)
                    - correction)
    quadratic = np.real((derivative.conj().T @ derivative) * moment.T)
    quadratic = 0.5 * (quadratic + quadratic.T)
    bounds = [(max(-0.5, nu_min - nus[j]), min(0.5, nu_max - nus[j]))
              for j in selected]
    if any(lo > hi for lo, hi in bounds):
        raise FloatingPointError("empty grid coordinate interval")
    if not np.isfinite(alpha).all() or not np.isfinite(quadratic).all():
        raise FloatingPointError("nonfinite grid expected loss")

    kappa, grid = _solve_grid_qp(quadratic, alpha, bounds, config)
    updated = nus.copy()
    updated[selected] += kappa
    if np.any(updated < nu_min - 1e-12) or np.any(updated > nu_max + 1e-12):
        raise AssertionError("grid step left physical Doppler interval")
    return updated, grid


def dense_channel(channel: Channel) -> np.ndarray:
    """Exact CPP/DAFT matrix, charging construction before dense LMMSE."""
    n = channel.n
    index = np.arange(n)
    inverse_basis = daft(np.eye(n, dtype=complex), channel.c1, channel.c2, True)
    time_matrix = np.zeros((n, n), dtype=np.complex128)
    for delay, nu, gain in zip(channel.delays, channel.dopplers, channel.gains):
        d = int(delay)
        cp = np.where(index < d,
                      np.exp(2j * np.pi * channel.c1 * (n * n + 2 * n * (index - d))), 1)
        time_matrix += (gain * cp * np.exp(2j * np.pi * index * nu / n))[:, None] * \
            inverse_basis[(index - d) % n]
    return daft(time_matrix, channel.c1, channel.c2)


def lmmse_hard_data(y: np.ndarray, pilot: np.ndarray, channel_matrix: np.ndarray,
                    sigma2: float, pd: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """Paper hard feedback with project-symbol power: ridge sigma2/pd."""
    h = np.asarray(channel_matrix, dtype=np.complex128)
    observed = np.asarray(y, dtype=np.complex128)
    known = np.asarray(pilot, dtype=np.complex128)
    if (h.shape != (len(observed), len(observed)) or known.shape != observed.shape
            or not np.isfinite(h).all() or not np.isfinite(observed).all()
            or not np.isfinite(known).all() or sigma2 <= 0 or pd <= 0):
        raise ValueError("invalid hard-data feedback inputs")
    rhs = h.conj().T @ (observed - h @ known)
    estimate = np.linalg.solve(h.conj().T @ h + (sigma2 / pd) * np.eye(len(observed)), rhs)
    if not np.isfinite(estimate).all():
        raise FloatingPointError("nonfinite LMMSE data estimate")
    return hard_qpsk(estimate), estimate


def _frobenius_squared(channel: Channel) -> float:
    gram = projected_variance(np.ones(channel.n), channel.delays,
                              channel.dopplers, channel.c1)
    value = float(np.vdot(channel.gains, gram @ channel.gains).real)
    if value < -1e-8:
        raise FloatingPointError("negative physical channel norm")
    return max(0.0, value)


def channel_change_squared(current: Channel, previous: Channel) -> float:
    if (current.n != previous.n or current.c1 != previous.c1
            or current.c2 != previous.c2):
        raise ValueError("incompatible physical channels")
    combined = Channel(current.n, current.c1, current.c2,
                       np.r_[current.delays, previous.delays],
                       np.r_[current.dopplers, previous.dopplers],
                       np.r_[current.gains, -previous.gains])
    return _frobenius_squared(combined) / max(_frobenius_squared(previous), 1e-30)


def estimate(y: np.ndarray, pilot: np.ndarray, sigma2: float, c1: float, c2: float,
             *, max_delay: int, nu_min: float, nu_max: float,
             initial_data: np.ndarray | None = None, mode: str = "gamp",
             config: F2Config = FROZEN) -> dict:
    """Complete fixed loop; ``full`` mode is limited to small synthetic grids.

    ``initial_data=None`` is F2E pilot-only; a hard initial vector is the F2T
    observed native-APP specialization. Neither path accepts truth or labels.
    """
    started = time.perf_counter()
    component_seconds = {key: 0.0 for key in
                         ("matrix", "posterior", "grid", "dense_h", "lmmse")}
    component_calls = {key: 0 for key in component_seconds}
    observed = np.asarray(y, dtype=np.complex128)
    known = np.asarray(pilot, dtype=np.complex128)
    n = len(observed)
    if (n < 2 or known.shape != (n,) or not np.isfinite(observed).all()
            or not np.isfinite(known).all() or sigma2 <= 0
            or not np.isfinite([sigma2, c1, c2]).all()):
        raise ValueError("invalid observed physical model")
    if initial_data is None:
        feedback = np.zeros(n, dtype=np.complex128)
        policy = "F2E"
    else:
        feedback = np.asarray(initial_data, dtype=np.complex128)
        if feedback.shape != (n,) or not np.isfinite(feedback).all():
            raise ValueError("invalid charged native-APP hard feedback")
        if not np.all(np.isin(feedback.real, [-0.5, 0.5])) or not np.all(
                np.isin(feedback.imag, [-0.5, 0.5])):
            raise ValueError("F2T initial feedback must be hard project QPSK")
        policy = "F2T"
    delays, nus = initial_grid(max_delay, nu_min, nu_max)
    m = len(nus)
    if mode == "full" and m > 64:
        raise ValueError("full GESBL reference is synthetic-only")
    pilot_energy = float(np.vdot(known, known).real)
    if pilot_energy <= 0:
        raise ValueError("nonzero known pilot required")
    delta0 = max(1e-12, n * max(float(np.vdot(observed, observed).real) / n - sigma2,
                               sigma2) / (m * pilot_energy))
    delta = np.full(m, delta0)
    delta_floor = max(1e-15, 1e-12 * delta0)
    b = 1e-6 / delta0
    d, e = 1.0, 1e-6 * sigma2
    beta = 1 / sigma2
    previous_channel = None
    passes = []
    cap_hits = {"gamp": 0, "em": 0, "data": False}
    for t in range(config.tmax):
        input_symbols = known + feedback
        em_trace = []
        em_converged = False
        for iteration in range(1, config.imax + 1):
            stamp = time.perf_counter()
            phi = regressors(input_symbols, delays, nus, c1, c2)
            component_seconds["matrix"] += time.perf_counter() - stamp
            component_calls["matrix"] += 1
            stamp = time.perf_counter()
            mean, covariance, inner = _posterior(phi, observed, delta, beta, mode, config)
            component_seconds["posterior"] += time.perf_counter() - stamp
            component_calls["posterior"] += 1
            if mode == "gamp" and not inner["converged"]:
                cap_hits["gamp"] += 1
            variance = covariance if covariance.ndim == 1 else np.diag(covariance).real
            energy = abs(mean) ** 2 + variance
            new_delta = 2 * energy / (np.sqrt(1 + 4 * b * energy) + 1)
            if np.any(new_delta <= 0) or not np.isfinite(new_delta).all():
                raise FloatingPointError("invalid EM hypervariance")
            new_delta = np.maximum(new_delta, delta_floor)
            residual = observed - phi @ mean
            uncertainty = (float(np.dot(np.sum(abs(phi) ** 2, axis=0), covariance))
                           if covariance.ndim == 1 else
                           float(np.einsum("nm,mk,nk->", phi, covariance,
                                           phi.conj(), optimize=True).real))
            expected_residual = float(np.vdot(residual, residual).real + uncertainty)
            beta = (n + d - 1) / (e + expected_residual)
            if not np.isfinite(beta) or beta <= 0:
                raise FloatingPointError("invalid EM likelihood precision")
            selected = active_indices(new_delta, n)
            stamp = time.perf_counter()
            new_nus, grid = _grid_update(observed, input_symbols, phi, delays, nus,
                                         mean, covariance, selected, c1, c2,
                                         nu_min, nu_max, config)
            component_seconds["grid"] += time.perf_counter() - stamp
            component_calls["grid"] += 1
            change = _relative_change(new_delta, delta)
            em_trace.append({"iteration": iteration, "gamp": inner["iterations"],
                             "gamp_converged": inner["converged"],
                             "grid_iterations": grid["iterations"],
                             "grid_max_shift": grid["max_shift"],
                             "grid_termination_reason": grid["termination_reason"],
                             "grid_original_kkt_projected_inf":
                                 grid["original_kkt_projected_inf"],
                             "grid_scaled_kkt_projected_inf":
                                 grid["scaled_kkt_projected_inf"],
                             "delta_change_squared": change})
            delta, nus = new_delta, new_nus
            if iteration >= 2 and change <= config.epsilon_g:
                em_converged = True
                break
        if not em_converged:
            cap_hits["em"] += 1

        # Charged final posterior at the actual updated grid and hyperparameters.
        stamp = time.perf_counter()
        phi = regressors(input_symbols, delays, nus, c1, c2)
        component_seconds["matrix"] += time.perf_counter() - stamp
        component_calls["matrix"] += 1
        stamp = time.perf_counter()
        mean, covariance, reconciliation = _posterior(phi, observed, delta, beta,
                                                       mode, config)
        component_seconds["posterior"] += time.perf_counter() - stamp
        component_calls["posterior"] += 1
        if mode == "gamp" and not reconciliation["converged"]:
            cap_hits["gamp"] += 1
        selected = active_indices(delta, n)
        channel = Channel(n, c1, c2, delays[selected], nus[selected], mean[selected])
        predictive_residual = float(np.linalg.norm(observed - phi @ mean))
        relative_channel_change = None if previous_channel is None else \
            channel_change_squared(channel, previous_channel)
        passes.append({"pass": t, "em_iterations": len(em_trace),
                       "em_converged": em_converged, "em": em_trace,
                       "reconciliation_iterations": reconciliation["iterations"],
                       "reconciliation_converged": reconciliation["converged"],
                       "beta": float(beta), "predictive_residual": predictive_residual,
                       "relative_channel_change_squared": relative_channel_change,
                       "active_indices": selected.copy(),
                       "feedback": feedback.copy()})
        if relative_channel_change is not None and relative_channel_change <= config.epsilon_t:
            break
        if t == config.tmax - 1:
            cap_hits["data"] = True
            break
        stamp = time.perf_counter()
        h_dense = dense_channel(channel)
        component_seconds["dense_h"] += time.perf_counter() - stamp
        component_calls["dense_h"] += 1
        stamp = time.perf_counter()
        feedback, _ = lmmse_hard_data(observed, known, h_dense, sigma2)
        component_seconds["lmmse"] += time.perf_counter() - stamp
        component_calls["lmmse"] += 1
        previous_channel = channel

    total_seconds = time.perf_counter() - started
    other_seconds = total_seconds - sum(component_seconds.values())
    if other_seconds < -1e-8:
        raise AssertionError("exclusive F2 component clocks exceed total")
    return {"policy": policy, "mode": mode, "channel": channel,
            "delays": delays, "dopplers": nus, "delta": delta,
            "posterior_mean": mean,
            "posterior_variance": covariance if covariance.ndim == 1 else np.diag(covariance).real,
            "beta": float(beta), "initial_delta": delta0,
            "selected": selected, "passes": passes, "cap_hits": cap_hits,
            "final_feedback": feedback.copy(),
            "timing": {"total_seconds": total_seconds,
                       "component_seconds": {**component_seconds,
                                             "other": max(0.0, other_seconds)},
                       "component_calls": component_calls}}
