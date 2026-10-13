"""Observed-only, fixed-cardinality geometry exchange for the TF continuation.

``Y`` is the time-domain observation after the production inverse DAFT;
``x_mean_af`` and ``v`` are frozen AF-domain APP moments.  The caller owns
receiver state, timing, and truth isolation.  This module never reads truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize_scalar

from physical import Channel, daft, dkernel, projected_variance
from twofft import TimePathOps


@dataclass(frozen=True)
class Path:
    delay: int
    doppler: float


@dataclass
class ExchangeResult:
    paths: list[Path]
    gains: np.ndarray
    objective_before: float
    objective_after: float
    edits: list[dict]
    evaluations: dict
    elapsed_seconds: float
    condition_number: float
    coefficient_power: float
    global_trace: list[dict]
    local_trace: list[dict]
    diagnostics: dict


def _responses(xt: np.ndarray, paths: list[Path], c1: float, c2: float) -> np.ndarray:
    channel = Channel(len(xt), c1, c2,
                      np.array([p.delay for p in paths], dtype=int),
                      np.array([p.doppler for p in paths], dtype=float),
                      np.ones(len(paths), dtype=complex))
    return TimePathOps(channel).responses_time(xt)


def _gamma_cross(a: list[Path], b: list[Path], vf: np.ndarray, c1: float) -> np.ndarray:
    """Production projected-variance identity extended to rectangular blocks."""
    n = len(vf)
    la = np.array([p.delay for p in a], dtype=int)[:, None]
    lb = np.array([p.delay for p in b], dtype=int)[None, :]
    na = np.array([p.doppler for p in a], dtype=float)[:, None]
    nb = np.array([p.doppler for p in b], dtype=float)[None, :]
    dl = lb - la
    return (np.exp(2j * np.pi * c1 * (la * la - lb * lb))
            * dkernel(nb - na + 2 * n * c1 * dl, n) * vf[dl % n])


def _system(Y: np.ndarray, xt: np.ndarray, v: np.ndarray, paths: list[Path],
            c1: float, c2: float, ridge: float):
    B = _responses(xt, paths, c1, c2)
    gamma = projected_variance(v, [p.delay for p in paths],
                               [p.doppler for p in paths], c1)
    Q = B.conj().T @ B + gamma + ridge * np.eye(len(paths))
    Q = (Q + Q.conj().T) / 2
    b = B.conj().T @ Y
    factor = cho_factor(Q, lower=True, check_finite=True)
    h = cho_solve(factor, b, check_finite=True)
    value = float(np.vdot(Y, Y).real) - float(np.vdot(b, h).real)
    if not np.isfinite(value) or not np.isfinite(h).all():
        raise FloatingPointError("nonfinite geometry objective or gains")
    return B, Q, b, h, value, gamma


def reopen_geometry(Y: np.ndarray, x_mean_af: np.ndarray, v: np.ndarray,
                    paths: list[Path], *, c1: float, c2: float,
                    ridge: float, max_delay: int,
                    doppler_min: float = -3., doppler_max: float = 3.,
                    grid_step: float = .25, max_edits: int = 2,
                    chunk_size: int = 64, local_passes: int = 2,
                    local_halfwidth: float = .75,
                    local_max_evals: int = 16,
                    duplicate_tolerance: float = 1e-6,
                    top_k: int = 20) -> ExchangeResult:
    """Score every slot/candidate once per global step, then refine local Dopplers.

    The reference's 1e-10 relative decrease guard is retained. ``scores`` and
    ``valid`` in each global trace are aligned with the candidate arrays and
    preserve float64 precision for later exact ranking. Invalid duplicate
    trials retain their computed score but have ``valid=False``.
    """
    start_time = time.perf_counter()
    Y = np.asarray(Y, dtype=np.complex128)
    x = np.asarray(x_mean_af, dtype=np.complex128)
    v = np.asarray(v, dtype=float)
    if Y.ndim != 1 or len(Y) < 2 or x.shape != Y.shape or v.shape != Y.shape or not paths:
        raise ValueError("Y, x_mean_af, v must be matching vectors; paths nonempty")
    if not all(np.isfinite(z).all() for z in (Y, x, v)) or np.any(v < 0):
        raise ValueError("nonfinite inputs or negative variances")
    scalars = (c1, c2, ridge, doppler_min, doppler_max, grid_step,
               local_halfwidth, duplicate_tolerance)
    if not all(isinstance(z, (int, float, np.integer, np.floating))
               and np.isfinite(z) for z in scalars):
        raise ValueError("nonfinite geometry configuration")
    if ridge <= 0 or grid_step <= 0 or doppler_min >= doppler_max:
        raise ValueError("invalid ridge or Doppler grid")
    if local_halfwidth <= 0 or duplicate_tolerance <= 0:
        raise ValueError("invalid local width or duplicate tolerance")
    for name, value, minimum in (("max_delay", max_delay, 0), ("max_edits", max_edits, 0),
                                 ("chunk_size", chunk_size, 1), ("local_passes", local_passes, 0),
                                 ("local_max_evals", local_max_evals, 1), ("top_k", top_k, 0)):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < minimum:
            raise ValueError(f"invalid {name}")
    if max_delay >= len(Y):
        raise ValueError("max_delay exceeds vector length")
    if max_edits > 2:
        raise ValueError("at most two accepted replacements are declared")
    current = []
    for p in paths:
        if (not isinstance(p, Path) or isinstance(p.delay, (bool, np.bool_))
                or not isinstance(p.delay, (int, np.integer))
                or not 0 <= p.delay <= max_delay
                or not isinstance(p.doppler, (int, float, np.integer, np.floating))
                or not np.isfinite(p.doppler)
                or not doppler_min <= p.doppler <= doppler_max):
            raise ValueError("input path outside declared model")
        current.append(Path(int(p.delay), float(p.doppler)))
    def duplicate(p: Path, others: list[Path]) -> bool:
        return any(p.delay == q.delay and abs(p.doppler - q.doppler) < duplicate_tolerance
                   for q in others)
    if any(duplicate(p, current[:i] + current[i + 1:]) for i, p in enumerate(current)):
        raise ValueError("essentially identical input paths")

    xt = daft(x, c1, c2, inverse=True)
    n = len(Y)
    P = len(current)
    energy = float(np.vdot(x, x).real + np.sum(v))
    steps = int(np.floor((doppler_max - doppler_min) / grid_step + 1e-9))
    nus = doppler_min + grid_step * np.arange(steps + 1)
    if nus[-1] < doppler_max - 1e-12:
        nus = np.append(nus, doppler_max)
    candidate_delays = np.repeat(np.arange(max_delay + 1, dtype=np.int32), len(nus))
    candidate_dopplers = np.tile(nus, max_delay + 1)
    C = len(candidate_delays)
    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge)
    initial = value
    edits: list[dict] = []
    global_trace: list[dict] = []
    local_trace: list[dict] = []
    counts = dict(global_candidate_columns=0, global_slot_tests=0,
                  global_duplicate_rejections=0, global_accepted=0,
                  global_rejected_steps=0, local_trials=0,
                  local_duplicate_rejections=0, local_accepted=0,
                  joint_gain_solves=1, reduced_gain_solves=0,
                  schur_batch_solves=0, top_k_extra_solves=0)

    def improvement(a: float, z: float) -> bool:
        return a - z > 1e-10 * (1 + abs(a))

    for step in range(max_edits):
        step_start = time.perf_counter()
        entering = [asdict(p) for p in current]
        entering_gains = h.copy()
        entering_value = value
        # Refit at the start of each step, as in the supplied kernel.
        B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge)
        counts["joint_gain_solves"] += 1
        reduced = []
        for slot in range(P):
            keep = np.arange(P) != slot
            if P == 1:
                reduced.append((keep, None, np.empty(0, complex), float(np.vdot(Y, Y).real)))
            else:
                qr = Q[np.ix_(keep, keep)]
                br = b[keep]
                factor = cho_factor(qr, lower=True, check_finite=True)
                hr = cho_solve(factor, br, check_finite=True)
                counts["reduced_gain_solves"] += 1
                reduced.append((keep, factor, hr,
                                float(np.vdot(Y, Y).real) - float(np.vdot(br, hr).real)))
        scores = np.empty((P, C), dtype=np.float64)
        valid = np.ones((P, C), dtype=bool)
        vf = np.fft.fft(v)
        for first in range(0, C, chunk_size):
            last = min(first + chunk_size, C)
            group = [Path(int(l), float(nu)) for l, nu in
                     zip(candidate_delays[first:last], candidate_dopplers[first:last])]
            Ux = _responses(xt, group, c1, c2)
            cross = B.conj().T @ Ux + _gamma_cross(current, group, vf, c1)
            bu = Ux.conj().T @ Y
            counts["global_candidate_columns"] += len(group)
            for slot, (keep, factor, hr, vr) in enumerate(reduced):
                kk = cross[keep]
                g = bu - kk.conj().T @ hr
                schur = np.full(len(group), energy + ridge)
                if P > 1:
                    schur -= np.sum(kk.conj() * cho_solve(factor, kk, check_finite=True), axis=0).real
                    counts["schur_batch_solves"] += 1
                if not np.isfinite(schur).all() or np.min(schur) <= 0:
                    raise FloatingPointError("nonpositive/nonfinite Schur complement")
                values = vr - abs(g) ** 2 / schur
                if not np.isfinite(values).all():
                    raise FloatingPointError("nonfinite candidate score")
                scores[slot, first:last] = values
                others = current[:slot] + current[slot + 1:]
                mask = np.array([not duplicate(p, others) for p in group], dtype=bool)
                valid[slot, first:last] = mask
                counts["global_duplicate_rejections"] += int(np.count_nonzero(~mask))
                counts["global_slot_tests"] += len(group)
        # np.lexsort uses its last key first; row-major slot order is explicit.
        slot_ids = np.repeat(np.arange(P, dtype=np.int32), C)
        scores_flat = scores.ravel()
        valid_flat = valid.ravel()
        ranked = np.lexsort((np.tile(candidate_dopplers, P),
                             np.tile(candidate_delays, P), slot_ids, scores_flat))
        ranked = ranked[valid_flat[ranked]]
        entries: list[dict] = []
        for index in ranked[:max(top_k, 1)]:
            slot, candidate = divmod(int(index), C)
            geometry = entering.copy()
            replacement = Path(int(candidate_delays[candidate]),
                               float(candidate_dopplers[candidate]))
            geometry[slot] = asdict(replacement)
            entries.append(dict(rank=len(entries) + 1, slot=slot,
                                replacement=asdict(replacement), paths=geometry,
                                frozen_score=float(scores_flat[index])))
        top = entries[:top_k]
        accepted = None
        if len(ranked):
            winner_index = int(ranked[0])
            winner_score = float(scores_flat[winner_index])
            if improvement(value, winner_score):
                slot, candidate = divmod(winner_index, C)
                new_path = Path(int(candidate_delays[candidate]),
                                float(candidate_dopplers[candidate]))
                old_path = current[slot]
                trial = current.copy()
                trial[slot] = new_path
                new_B, new_Q, new_b, new_h, new_value, new_gamma = _system(
                    Y, xt, v, trial, c1, c2, ridge)
                counts["joint_gain_solves"] += 1
                if abs(new_value - winner_score) > 1e-7 * (1 + abs(winner_score)):
                    raise AssertionError("Schur/direct objective mismatch")
                if not improvement(value, new_value):
                    raise AssertionError("winner failed direct strict-decrease guard")
                accepted = dict(slot=slot, old=asdict(old_path), new=asdict(new_path),
                                frozen_score=winner_score, direct_score=new_value,
                                decrease=float(value - new_value))
                edits.append(dict(step=step, slot=slot, old=asdict(old_path),
                                  new=asdict(new_path), decrease=float(value - new_value)))
                current = trial
                B, Q, b, h, value, gamma = new_B, new_Q, new_b, new_h, new_value, new_gamma
                counts["global_accepted"] += 1
        if accepted is None:
            counts["global_rejected_steps"] += 1
        global_trace.append(dict(step=step, entering_paths=entering,
                                 entering_gains=entering_gains,
                                 entering_objective=float(entering_value),
                                 candidate_delays=candidate_delays.copy(),
                                 candidate_dopplers=candidate_dopplers.copy(),
                                 scores=scores, valid=valid, top_k=top,
                                 selected=entries[0] if entries else None,
                                 accepted=accepted,
                                 candidate_columns=C, slot_tests=P * C,
                                 valid_slot_tests=int(np.count_nonzero(valid)),
                                 duplicate_rejections=int(np.count_nonzero(~valid)),
                                 elapsed_seconds=time.perf_counter() - step_start))
        if accepted is None:
            break

    # Windows are fixed at the geometry entering the local phase.
    centers = [p.doppler for p in current]
    local_entering = [asdict(p) for p in current]
    for pass_index in range(local_passes):
        for slot in range(P):
            coordinate_start = time.perf_counter()
            lo = max(doppler_min, centers[slot] - local_halfwidth)
            hi = min(doppler_max, centers[slot] + local_halfwidth)
            incumbent = value
            start_path = current[slot]
            best_path = start_path
            best_value = value
            trials = []
            others = current[:slot] + current[slot + 1:]

            def objective(nu: float) -> float:
                nonlocal best_path, best_value
                test = Path(current[slot].delay, float(nu))
                counts["local_trials"] += 1
                if duplicate(test, others):
                    counts["local_duplicate_rejections"] += 1
                    trials.append(dict(doppler=float(nu), valid=False, score=None))
                    return float("inf")
                proposed = current.copy()
                proposed[slot] = test
                *_, score, _gamma = _system(Y, xt, v, proposed, c1, c2, ridge)
                counts["joint_gain_solves"] += 1
                trials.append(dict(doppler=float(nu), valid=True, score=score))
                if improvement(best_value, score):
                    best_value = score
                    best_path = test
                return score

            minimize_scalar(objective, bounds=(lo, hi), method="bounded",
                            options={"xatol": .002, "maxiter": local_max_evals})
            local_accepted = improvement(incumbent, best_value)
            if local_accepted:
                current[slot] = best_path
                value = best_value
                counts["local_accepted"] += 1
            local_trace.append(dict(pass_index=pass_index, slot=slot,
                                    local_phase_entering_paths=local_entering,
                                    center=centers[slot], bounds=(lo, hi),
                                    start=asdict(start_path), start_objective=incumbent,
                                    endpoint=asdict(current[slot]), endpoint_objective=value,
                                    accepted=local_accepted, trials=trials,
                                    trial_count=len(trials),
                                    rejected_duplicate_trials=sum(not t["valid"] for t in trials),
                                    elapsed_seconds=time.perf_counter() - coordinate_start))
    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge)
    counts["joint_gain_solves"] += 1
    if value > initial + 1e-8 * (1 + abs(initial)):
        raise AssertionError("frozen objective increased")
    gram = B.conj().T @ B
    physical = Channel(n, c1, c2,
                       [p.delay for p in current], [p.doppler for p in current],
                       np.ones(P, dtype=complex))
    diagnostics = dict(gamma=gamma, response_gram=gram,
                       physical_operator_gram=TimePathOps(physical).R,
                       ridge_lambda=float(ridge),
                       local_window_centers=np.asarray(centers),
                       improvement_guard="a-b > 1e-10*(1+abs(a))")
    return ExchangeResult(current, h, initial, value, edits, counts,
                          time.perf_counter() - start_time,
                          float(np.linalg.cond(Q)), float(np.vdot(h, h).real),
                          global_trace, local_trace, diagnostics)
