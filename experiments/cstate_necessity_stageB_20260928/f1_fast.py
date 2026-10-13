"""Semantics-preserving F1 implementation candidate; not a new estimator.

Only response reuse, bank duplicate masking, and redundant conjugate removal
differ from the frozen Stage-A reference. Qualification must precede any timing
or receiver comparison. This module never sees decoder or truth data.
"""
from __future__ import annotations

import time

import numpy as np

from f1 import NumericalFailure, PhysicalF1, response as reference_response, score, score_derivatives
from physical import Channel, daft


class PhysicalF1Fast(PhysicalF1):
    """Same frozen F1 path search with per-acquisition immutable response bases."""

    def _response(self, delay: int, doppler: float) -> np.ndarray:
        # The delay/CPP/pilot factor is exactly the first product in f1.response.
        # Keep the original exponent operation order to minimize roundoff drift.
        return self._delay_base[:, delay] * np.exp(
            2j * np.pi * self._sample_index * doppler / self.n)

    def _refit(self, z: np.ndarray, delays: list[int], dopplers: list[float],
               noise: float) -> tuple[np.ndarray, np.ndarray, float, float]:
        if not delays:
            return np.empty(0, complex), z.copy(), float(np.vdot(z, z).real), 1.0
        bank = np.column_stack([self._response(delay, nu)
                                for delay, nu in zip(delays, dopplers, strict=True)])
        bank_h = bank.conj().T
        matrix = bank_h @ bank + noise * np.eye(len(delays))
        rhs = bank_h @ z
        condition = float(np.asarray(np.linalg.cond(matrix)).item())
        if not np.isfinite(condition) or condition > 1e12:
            raise NumericalFailure(f'F1 ridge condition {condition}')
        try:
            gains = np.linalg.solve(matrix, rhs)
        except np.linalg.LinAlgError as exc:
            raise NumericalFailure('F1 ridge solve failed') from exc
        rhs_norm = float(np.asarray(np.linalg.norm(rhs)).item())
        relative = np.linalg.norm(matrix @ gains - rhs) / max(rhs_norm, 1e-30)
        residual = z - bank @ gains
        objective = float(np.vdot(residual, residual).real + noise * np.vdot(gains, gains).real)
        if not np.isfinite(gains).all() or not np.isfinite(objective) or relative > 1e-10:
            raise NumericalFailure(f'F1 ridge residual {relative}')
        return gains, residual, objective, condition

    def _coordinate(
        self, z: np.ndarray, time_pilot: np.ndarray, delays: list[int],
        dopplers: list[float], gains: np.ndarray, index: int, center: float,
        energy: float, noise: float, counters: dict[str, int],
    ) -> tuple[list[float], np.ndarray, float]:
        del time_pilot  # immutable pilot/CPP bases were built in acquire()
        delay = delays[index]
        old = dopplers[index]
        other = z - sum((gains[k] * self._response(delay_k, dopplers[k])
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
                evaluated[value] = score(self._response(delay, value),
                                         other, energy, noise)[0]
            return evaluated[value]

        best_nu = old
        best = evaluate(old)
        start = best
        for endpoint in (lo, hi):
            val = evaluate(endpoint)
            if val > best:
                best_nu, best = endpoint, val
        candidate = best_nu
        for _ in range(4):
            b = self._response(delay, candidate)
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
        new_gains, _, new_objective, _ = self._refit(z, delays, proposal, noise)
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
        self._sample_index = np.arange(self.n)
        self._delay_base = np.column_stack([
            # Preserve Stage-A operation order for the delay/CPP factor.
            reference_response(time_pilot, delay, 0., self.c1)
            for delay in range(self.lmax + 1)])
        modulation = np.exp(2j * np.pi * self._sample_index[:, None] *
                            np.arange(-3., 3.00001, .25) / self.n)
        bank = (self._delay_base[:, :, None] * modulation[:, None, :]).reshape(self.n, -1)
        bank_h = bank.conj().T
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
            residual = z - sum((gains[j] * self._response(delay_j, dopplers[j])
                                for j, delay_j in enumerate(delays)), np.zeros(self.n, complex))
            counters['accepted_coordinates'] += 1
            history.append(objective)

        stopping = 'eight_slots'
        for _ in range(8):
            correlations = bank_h @ residual
            scores = abs(correlations) ** 2 / (sigma2 * (energy + sigma2))
            counters['bank_scans'] += 1
            counters['bank_scores'] += len(scores)
            if not np.isfinite(scores).all():
                raise NumericalFailure('nonfinite F1 bank score')
            for delay, nu in zip(delays, dopplers, strict=True):
                scores[(self.delays == delay) & (np.abs(self.centers - nu) < 1e-6)] = -np.inf
            if not np.isfinite(scores).any():
                stopping = 'no_valid_bank_item'
                break
            winner = int(np.argmax(scores))
            reduction = float(scores[winner] * sigma2)
            if reduction <= 1e-12 * max(1., float(np.vdot(z, z).real)):
                stopping = 'numerical_no_improvement'
                break
            delay, center = int(self.delays[winner]), float(self.centers[winner])
            delays.append(delay)
            dopplers.append(center)
            centers.append(center)
            coordinate_gain = correlations[winner] / (energy + sigma2)
            gains, residual, objective, _ = self._refit(z, delays, dopplers, sigma2)
            counters['joint_solves'] += 1
            history.append(objective)
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
