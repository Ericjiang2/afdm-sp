"""Frozen pilot-only F1 physical NOMP comparator.

This module accepts observed AF-domain y, known pilot, noise, and the declared
AFDM geometry. It never imports a decoder, a truth record, or CSTATE scores.
"""
from __future__ import annotations

import time

import numpy as np

from physical import Channel, daft


class NumericalFailure(FloatingPointError):
    """A charged F1 arithmetic failure, not an acquisition stopping rule."""


def response(time_pilot: np.ndarray, delay: int, doppler: float, c1: float) -> np.ndarray:
    n = len(time_pilot)
    t = np.arange(n)
    shifted = t - delay
    cpp = np.where(shifted < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * shifted)), 1)
    return time_pilot[shifted % n] * cpp * np.exp(2j * np.pi * t * doppler / n)


def derivatives(b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    factor = 2j * np.pi * np.arange(len(b)) / len(b)
    return factor * b, factor * factor * b


def score(b: np.ndarray, residual: np.ndarray, energy: float, noise: float) -> tuple[float, float, complex]:
    q = np.vdot(b, residual)
    reduction = float(abs(q) ** 2 / (energy + noise))
    normalized = reduction / noise
    if not np.isfinite(normalized):
        raise NumericalFailure('nonfinite F1 physical score')
    return normalized, reduction, q


def score_derivatives(
    b: np.ndarray, residual: np.ndarray, energy: float, noise: float,
) -> tuple[float, float, float]:
    first, second = derivatives(b)
    q = np.vdot(b, residual)
    qp = np.vdot(first, residual)
    qpp = np.vdot(second, residual)
    denominator = noise * (energy + noise)
    values = (float(abs(q) ** 2 / denominator),
              float(2 * np.real(np.conj(q) * qp) / denominator),
              float(2 * (abs(qp) ** 2 + np.real(np.conj(q) * qpp)) / denominator))
    if not np.isfinite(values).all():
        raise NumericalFailure('nonfinite F1 score derivative')
    return values


def refit(
    z: np.ndarray, time_pilot: np.ndarray, delays: list[int], dopplers: list[float],
    c1: float, noise: float,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    if not delays:
        return np.empty(0, complex), z.copy(), float(np.vdot(z, z).real), 1.0
    bank = np.column_stack([response(time_pilot, delay, nu, c1)
                            for delay, nu in zip(delays, dopplers, strict=True)])
    matrix = bank.conj().T @ bank + noise * np.eye(len(delays))
    rhs = bank.conj().T @ z
    condition = float(np.linalg.cond(matrix))
    if not np.isfinite(condition) or condition > 1e12:
        raise NumericalFailure(f'F1 ridge condition {condition}')
    try:
        gains = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError as exc:
        raise NumericalFailure('F1 ridge solve failed') from exc
    relative = np.linalg.norm(matrix @ gains - rhs) / max(np.linalg.norm(rhs), 1e-30)
    residual = z - bank @ gains
    objective = float(np.vdot(residual, residual).real + noise * np.vdot(gains, gains).real)
    if not np.isfinite(gains).all() or not np.isfinite(objective) or relative > 1e-10:
        raise NumericalFailure(f'F1 ridge residual {relative}')
    return gains, residual, objective, condition


class PhysicalF1:
    """One observed-pilot F1 acquisition; production uses N=1024, lmax=102."""

    def __init__(self, n: int, c1: float, c2: float, lmax: int):
        if n < 2 or not 0 <= lmax < n or not np.isfinite([c1, c2]).all():
            raise ValueError('invalid declared AFDM geometry')
        self.n, self.c1, self.c2, self.lmax = n, c1, c2, lmax
        self.delays = np.repeat(np.arange(lmax + 1), 25)
        self.centers = np.tile(np.arange(-3., 3.00001, .25), lmax + 1)
        if len(self.centers) != 25 * (lmax + 1):
            raise AssertionError('F1 bank geometry differs')

    @staticmethod
    def _duplicate(delay: int, doppler: float, delays: list[int], dopplers: list[float],
                   exclude: int | None = None) -> bool:
        return any(i != exclude and delay == existing_delay and abs(doppler - nu) < 1e-6
                   for i, (existing_delay, nu) in enumerate(zip(delays, dopplers, strict=True)))

    def _coordinate(
        self, z: np.ndarray, time_pilot: np.ndarray, delays: list[int],
        dopplers: list[float], gains: np.ndarray, index: int, center: float,
        energy: float, noise: float, counters: dict[str, int],
    ) -> tuple[list[float], np.ndarray, float]:
        delay = delays[index]
        old = dopplers[index]
        other = z - sum((gains[k] * response(time_pilot, delay_k, dopplers[k], self.c1)
                         for k, delay_k in enumerate(delays) if k != index),
                        np.zeros(self.n, complex))
        lo, hi = max(-3., center - .75), min(3., center + .75)
        evaluated: dict[float, float] = {}

        def evaluate(value: float) -> float:
            if value in evaluated:
                return evaluated[value]
            counters['coordinate_scores'] += 1
            if self._duplicate(delay, value, delays, dopplers, exclude=index):
                evaluated[value] = -np.inf
            else:
                evaluated[value] = score(response(time_pilot, delay, value, self.c1),
                                         other, energy, noise)[0]
            return evaluated[value]

        best_nu = old
        best = evaluate(old)
        start = best
        # Bracket endpoints are checked exactly once per coordinate visit.
        for endpoint in (lo, hi):
            val = evaluate(endpoint)
            if val > best:
                best_nu, best = endpoint, val
        candidate = best_nu
        for _ in range(4):
            b = response(time_pilot, delay, candidate, self.c1)
            _, slope, curvature = score_derivatives(b, other, energy, noise)
            counters['newton_steps'] += 1
            if curvature >= 0:
                continue
            proposed = float(np.clip(candidate - slope / curvature, lo, hi))
            local_nu, local = candidate, evaluate(candidate)
            for multiplier in (1., .5, .25, .125):
                trial = candidate + multiplier * (proposed - candidate)
                val = evaluate(trial)
                if val > local:
                    local_nu, local = trial, val
            candidate = local_nu
            if local > best:
                best_nu, best = local_nu, local
        if best <= start + 1e-12 * max(1., start):
            return dopplers, gains, np.nan
        proposal = dopplers.copy()
        proposal[index] = best_nu
        new_gains, _, new_objective, _ = refit(z, time_pilot, delays, proposal, self.c1, noise)
        counters['joint_solves'] += 1
        return proposal, new_gains, new_objective

    def acquire(self, y: np.ndarray, pilot: np.ndarray, sigma2: float) -> dict:
        start = time.perf_counter()
        y = np.asarray(y, complex)
        pilot = np.asarray(pilot, complex)
        if (y.shape != (self.n,) or pilot.shape != (self.n,) or not np.isfinite(y).all()
                or not np.isfinite(pilot).all() or not np.isfinite(sigma2) or sigma2 <= 0):
            raise ValueError('F1 accepts only finite observed y, pilot and positive sigma2')
        z = daft(y, self.c1, self.c2, True)
        time_pilot = daft(pilot, self.c1, self.c2, True)
        energy = float(np.vdot(time_pilot, time_pilot).real)
        if energy <= 0 or not np.isfinite(energy):
            raise ValueError('zero/nonfinite known pilot energy')
        t = np.arange(self.n)
        base = np.column_stack([response(time_pilot, delay, 0., self.c1)
                                for delay in range(self.lmax + 1)])
        modulation = np.exp(2j * np.pi * t[:, None] * np.arange(-3., 3.00001, .25) / self.n)
        bank = (base[:, :, None] * modulation[:, None, :]).reshape(self.n, -1)
        bank_build_seconds = time.perf_counter() - start
        delays: list[int] = []
        dopplers: list[float] = []
        centers: list[float] = []
        gains = np.empty(0, complex)
        residual = z.copy()
        objective = float(np.vdot(z, z).real)
        history = [objective]
        counters = {'bank_scans': 0, 'bank_scores': 0, 'coordinate_scores': 0,
                    'newton_steps': 0, 'joint_solves': 0, 'coordinate_visits': 0,
                    'accepted_coordinates': 0}

        def visit(index: int, anchored_center: float) -> None:
            nonlocal dopplers, gains, residual, objective
            counters['coordinate_visits'] += 1
            proposal, new_gains, new_objective = self._coordinate(
                z, time_pilot, delays, dopplers, gains, index, anchored_center,
                energy, sigma2, counters)
            if np.isnan(new_objective):
                return
            if new_objective > objective + 1e-10 * max(1., objective):
                raise NumericalFailure('F1 accepted coordinate increased joint objective')
            dopplers, gains, objective = proposal, new_gains, new_objective
            residual = z - sum((gains[j] * response(time_pilot, delay_j, dopplers[j], self.c1)
                                for j, delay_j in enumerate(delays)), np.zeros(self.n, complex))
            counters['accepted_coordinates'] += 1
            history.append(objective)

        stopping = 'eight_slots'
        for _ in range(8):
            correlations = bank.conj().T @ residual
            scores = abs(correlations) ** 2 / (sigma2 * (energy + sigma2))
            counters['bank_scans'] += 1
            counters['bank_scores'] += len(scores)
            if not np.isfinite(scores).all():
                raise NumericalFailure('nonfinite F1 bank score')
            for j, (delay, nu) in enumerate(zip(self.delays, self.centers, strict=True)):
                if self._duplicate(int(delay), float(nu), delays, dopplers):
                    scores[j] = -np.inf
            if not np.isfinite(scores).any():
                stopping = 'no_valid_bank_item'
                break
            winner = int(np.argmax(scores))  # ascending delay/Doppler tie order
            reduction = float(scores[winner] * sigma2)
            if reduction <= 1e-12 * max(1., float(np.vdot(z, z).real)):
                stopping = 'numerical_no_improvement'
                break
            delay, center = int(self.delays[winner]), float(self.centers[winner])
            delays.append(delay)
            dopplers.append(center)
            centers.append(center)
            # The coordinate gain below is recorded before the checked joint refit.
            coordinate_gain = correlations[winner] / (energy + sigma2)
            gains, residual, objective, _ = refit(z, time_pilot, delays, dopplers, self.c1, sigma2)
            counters['joint_solves'] += 1
            history.append(objective)
            # A new path gets its own coordinate refinement before the two
            # all-slot cyclic passes (8 + 72 visits at a full eight slots).
            visit(len(delays) - 1, center)
            for _ in range(2):
                for index, anchored_center in enumerate(centers):
                    visit(index, anchored_center)
        if not delays:
            raise NumericalFailure('F1 numerical stop produced no valid TF channel')
        channel = Channel(self.n, self.c1, self.c2, delays, dopplers, gains)
        return {'channel': channel, 'delays': channel.delays, 'dopplers': channel.dopplers,
                'gains': channel.gains, 'bank_centers': np.asarray(centers),
                'stopping_reason': stopping, 'objective_history': np.asarray(history),
                'counters': counters, 'pilot_energy': energy, 'bank_build_seconds': bank_build_seconds,
                'acquisition_seconds': time.perf_counter() - start,
                'last_coordinate_gain': complex(coordinate_gain)}
