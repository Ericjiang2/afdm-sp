"""Comparator-only TF refit that preserves every ordered F1 physical slot."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

from physical import Channel, daft, dkernel
from f1 import NumericalFailure


def _valid_slots(delays: np.ndarray, dopplers: np.ndarray, *, exclude: int | None = None,
                 candidate: float | None = None) -> bool:
    values = dopplers.copy()
    if exclude is not None:
        values[exclude] = float(candidate)
    for i in range(len(delays)):
        for j in range(i):
            if delays[i] == delays[j] and abs(values[i] - values[j]) < 1e-6:
                return False
    return True


def time_refine_keep_slots(y, pilot, mu, v, ls, ks, gs, c1, c2, noise,
                           mode='soft', max_paths=8, rounds=2):
    """The frozen two-FFT objective with no `np.unique`/one-center compression.

    Every local bracket is anchored to the incoming Doppler, including round 1.
    The gain/physical covariance is solved with all cross terms intact.
    """
    n = len(y)
    delays = np.asarray(ls, int).copy()
    centers = np.asarray(ks, float).copy()
    gains = np.asarray(gs, complex)
    if (not 1 <= len(delays) <= max_paths or delays.shape != centers.shape
            or delays.shape != gains.shape or np.any(delays < 0) or np.any(delays >= n)
            or not np.isfinite(centers).all() or not np.isfinite(gains).all()
            or not _valid_slots(delays, centers)):
        raise ValueError('invalid F1 physical slots')
    if mode not in ('mean', 'scalar', 'soft') or rounds != 2 or noise <= 0:
        raise ValueError('comparator refinement configuration differs')
    nu = centers.copy()
    k = np.arange(n)
    xt = daft(np.asarray(pilot) + mu, c1, c2, True)
    Y = daft(y, c1, c2, True)
    wrap = k[:, None] - delays
    base = xt[wrap % n] * np.where(wrap < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * wrap)), 1.)
    vv = np.zeros(n) if mode == 'mean' else np.full(n, np.mean(v)) if mode == 'scalar' else np.asarray(v)
    dl = delays[None, :] - delays[:, None]
    gv = np.exp(2j * np.pi * c1 * (delays[:, None] ** 2 - delays[None, :] ** 2)) * np.fft.fft(vv)[dl % n]
    calls = 0
    conditions: list[float] = []

    def ev(candidate):
        nonlocal calls
        calls += 1
        B = base * np.exp(2j * np.pi * k[:, None] * candidate / n)
        G = gv * dkernel(candidate[None, :] - candidate[:, None] + 2 * n * c1 * dl, n)
        G = (G + G.conj().T) * .5
        Q = B.conj().T @ B + G + noise * np.eye(len(delays))
        b = B.conj().T @ Y
        condition = float(np.linalg.cond(Q))
        conditions.append(condition)
        if not np.isfinite(condition) or condition > 1e12:
            raise NumericalFailure(f'keep-slots working solve condition {condition}')
        try:
            h = np.linalg.solve(Q, b)
        except np.linalg.LinAlgError as exc:
            raise NumericalFailure('keep-slots working solve failed') from exc
        relative = np.linalg.norm(Q @ h - b) / max(np.linalg.norm(b), 1e-30)
        value = float((np.vdot(Y, Y) - np.vdot(b, h)).real)
        if not np.isfinite(h).all() or not np.isfinite(value) or relative > 1e-10:
            raise NumericalFailure(f'keep-slots nonfinite/working residual {relative}')
        return value, h, G

    val, h, G = ev(nu)
    history = [val]
    for _ in range(rounds):
        for j, center in enumerate(centers):
            lo, hi = max(-3., center - .75), min(3., center + .75)

            def f(value, index=j):
                if not _valid_slots(delays, nu, exclude=index, candidate=value):
                    return np.inf
                trial = nu.copy()
                trial[index] = value
                return ev(trial)[0]

            opt = minimize_scalar(f, bounds=(lo, hi), method='bounded',
                                  options={'xatol': .002, 'maxiter': 16})
            if opt.fun < val and _valid_slots(delays, nu, exclude=j, candidate=opt.x):
                nu[j] = opt.x
                val, h, G = ev(nu)
                history.append(val)
    val, h, G = ev(nu)
    return Channel(n, c1, c2, delays, nu, h), dict(
        history=history, objective=val, gamma=G, evaluations=calls,
        fft_count=3, conditions=conditions, input_delays=delays.copy(),
        input_dopplers=centers.copy(), output_delays=delays.copy())
