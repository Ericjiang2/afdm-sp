"""PB16 comparator (task 10-08-doppler-cluster, M1 item 3 / design.md Stage M2): PhysicalF1.acquire with the 8-slot cap raised to 16.

COPY of cstate_necessity_stageA_20260928/f1.py PhysicalF1.acquire (lines 157-244) with exactly two code edits: `for _ in range(8)` ->
`for _ in range(self.cap)` and stopping label 'eight_slots' -> 'cap_slots' (plus one comment re-worded).  No stopping rule is added (count-blind greedy fill:
it always takes `cap` slots unless the original numerical stops fire).  `_duplicate`, `_coordinate`, `response`, `refit`, `score`
and the bank are inherited / imported UNCHANGED from the frozen stage-A f1.py (not edited).  Comparator only (a pure cap-16 bound).
"""
from __future__ import annotations

import time

import numpy as np

from f1 import NumericalFailure, PhysicalF1, refit, response, score, score_derivatives  # noqa: F401  (stage-A dir on sys.path)
from physical import Channel, daft


class PhysicalF1Cap(PhysicalF1):
    def __init__(self, n: int, c1: float, c2: float, lmax: int, cap: int = 16):
        super().__init__(n, c1, c2, lmax)
        if not 1 <= cap <= 64:
            raise ValueError('cap out of range')
        self.cap = int(cap)

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

        stopping = 'cap_slots'
        for _ in range(self.cap):
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
            # all-slot cyclic passes (visits grow quadratically with the slot count).
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
