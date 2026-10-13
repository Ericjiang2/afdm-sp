"""Instrumented common LOCAL20/GLOBAL20/CSTATE20 geometry operation.

The direct branch preserves the executed adapter's score/slot/delay/Doppler
lexicographic selection, not the research attachment's chunk traversal.
All three arms share the same local refinement and evidence schema.  The
compact branch changes only full-grid structural score computation.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path as FilePath
import sys
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize_scalar

_OLD = FilePath(__file__).resolve().parents[1] / "tf_geometry_reopen_20260922"
if str(_OLD) not in sys.path:
    sys.path.insert(0, str(_OLD))
from geometry_reopen import ExchangeResult, Path, _gamma_cross, _responses, _system  # noqa: E402
from physical import Channel, daft  # noqa: E402
from twofft import TimePathOps  # noqa: E402
from compact_state import CPPField, exchange_scores, state_from_normal  # noqa: E402


STAGES = ("geometry_setup", "structural_field_build", "structural_scoring",
          "structural_selection_trace", "structural_refit_refresh",
          "structural_fallback_direct", "local_refinement", "geometry_finalization")


class StageClock:
    def __init__(self):
        self.seconds = {name: 0. for name in STAGES}
        self.stage = STAGES[0]
        self.at = time.perf_counter()

    def enter(self, stage):
        now = time.perf_counter()
        self.seconds[self.stage] += now - self.at
        self.stage = stage
        self.at = now

    def finish(self):
        self.enter(self.stage)
        return dict(exclusive_seconds=self.seconds.copy(),
                    total_seconds=sum(self.seconds.values()),
                    nested_step_times_included=True)


def _validate(Y, x, v, paths, c1, c2, ridge, max_delay, doppler_min,
              doppler_max, grid_step, max_edits, chunk_size, local_passes,
              local_halfwidth, local_max_evals, duplicate_tolerance, top_k):
    Y = np.asarray(Y, dtype=np.complex128)
    x = np.asarray(x, dtype=np.complex128)
    v = np.asarray(v, dtype=float)
    if Y.ndim != 1 or len(Y) < 2 or x.shape != Y.shape or v.shape != Y.shape or not paths:
        raise ValueError("invalid observation, moments or paths")
    if not all(np.isfinite(a).all() for a in (Y, x, v)) or np.any(v < 0):
        raise ValueError("nonfinite observation/moments or negative variance")
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
        if (isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer))
                or value < minimum):
            raise ValueError(f"invalid {name}")
    if max_delay >= len(Y) or max_edits > 2:
        raise ValueError("delay or edit budget outside declared scope")
    current = []
    for p in paths:
        if (not isinstance(p, Path) or isinstance(p.delay, (bool, np.bool_))
                or not isinstance(p.delay, (int, np.integer))
                or not 0 <= p.delay <= max_delay
                or not isinstance(p.doppler, (int, float, np.integer, np.floating))
                or not np.isfinite(p.doppler)
                or not doppler_min <= p.doppler <= doppler_max):
            raise ValueError("path outside declared geometry")
        current.append(Path(int(p.delay), float(p.doppler)))
    if any(_duplicate(p, current[:i] + current[i + 1:], duplicate_tolerance)
           for i, p in enumerate(current)):
        raise ValueError("essentially identical input paths")
    return Y, x, v, current


def _duplicate(path, others, tolerance):
    return any(path.delay == other.delay and abs(path.doppler - other.doppler) < tolerance
               for other in others)


def _bank(max_delay, doppler_min, doppler_max, grid_step):
    count = int(np.floor((doppler_max - doppler_min) / grid_step + 1e-9))
    nus = doppler_min + grid_step * np.arange(count + 1)
    if nus[-1] < doppler_max - 1e-12:
        nus = np.append(nus, doppler_max)
    delays = np.repeat(np.arange(max_delay + 1, dtype=np.int32), len(nus))
    dopplers = np.tile(nus, max_delay + 1)
    return delays, dopplers, nus


def _valid(current, candidates, tolerance):
    delays = np.asarray([p.delay for p in current])
    dopplers = np.asarray([p.doppler for p in current])
    cd = np.asarray([p.delay for p in candidates])
    cn = np.asarray([p.doppler for p in candidates])
    equal = (delays[:, None] == cd[None, :]) & (abs(dopplers[:, None] - cn[None, :]) < tolerance)
    return np.sum(equal, axis=0)[None, :] - equal == 0


def _select(scores, valid, delays, dopplers, current, top_k):
    P, C = scores.shape
    slots = np.repeat(np.arange(P, dtype=np.int32), C)
    flat = scores.ravel()
    ranked = np.lexsort((np.tile(dopplers, P), np.tile(delays, P), slots, flat))
    ranked = ranked[valid.ravel()[ranked]]
    entering = [asdict(p) for p in current]
    entries = []
    for index in ranked[:max(top_k, 1)]:
        slot, candidate = divmod(int(index), C)
        replacement = Path(int(delays[candidate]), float(dopplers[candidate]))
        geometry = entering.copy()
        geometry[slot] = asdict(replacement)
        entries.append(dict(rank=len(entries) + 1, slot=slot,
                            replacement=asdict(replacement), paths=geometry,
                            frozen_score=float(flat[index])))
    return (int(ranked[0]) if len(ranked) else None,
            entries[0] if entries else None, entries[:top_k])


def _direct_scores(Y, xt, v, current, B, Q, b, c1, c2, ridge,
                   delays, dopplers, chunk_size, energy, tolerance, counts):
    """Executed production Schur computation, including its chunk arithmetic."""
    P, C = len(current), len(delays)
    reduced = []
    y_energy = float(np.vdot(Y, Y).real)
    for slot in range(P):
        keep = np.arange(P) != slot
        if P == 1:
            reduced.append((keep, None, np.empty(0, complex), y_energy))
        else:
            qr = Q[np.ix_(keep, keep)]
            br = b[keep]
            factor = cho_factor(qr, lower=True, check_finite=True)
            hr = cho_solve(factor, br, check_finite=True)
            counts["reduced_gain_solves"] += 1
            reduced.append((keep, factor, hr,
                            y_energy - float(np.vdot(br, hr).real)))
    scores = np.empty((P, C), dtype=np.float64)
    valid = np.ones((P, C), dtype=bool)
    vf = np.fft.fft(v)
    for first in range(0, C, chunk_size):
        last = min(first + chunk_size, C)
        group = [Path(int(delay), float(nu)) for delay, nu in
                 zip(delays[first:last], dopplers[first:last])]
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
                raise FloatingPointError("nonpositive/nonfinite direct Schur complement")
            values = vr - abs(g) ** 2 / schur
            if not np.isfinite(values).all():
                raise FloatingPointError("nonfinite direct score")
            scores[slot, first:last] = values
            others = current[:slot] + current[slot + 1:]
            mask = np.array([not _duplicate(path, others, tolerance)
                             for path in group], dtype=bool)
            valid[slot, first:last] = mask
            counts["global_duplicate_rejections"] += int(np.count_nonzero(~mask))
            counts["global_slot_tests"] += len(group)
    return scores, valid


def _empty_counts():
    return dict(global_candidate_columns=0, global_slot_tests=0,
                global_duplicate_rejections=0, global_accepted=0,
                global_rejected_steps=0, local_trials=0,
                local_duplicate_rejections=0, local_accepted=0,
                joint_gain_solves=0, reduced_gain_solves=0,
                schur_batch_solves=0, top_k_extra_solves=0,
                compact_field_calls=0, compact_score_batches=0,
                compact_changed_row_refreshes=0, fallback_calls=0)


def _trace(step, current, h, value, delays, dopplers, scores, valid,
           selected, top, accepted, step_start, compact_stats=None):
    P, C = scores.shape
    record = dict(step=step, entering_paths=[asdict(p) for p in current],
                  entering_gains=h.copy(), entering_objective=float(value),
                  candidate_delays=delays.copy(), candidate_dopplers=dopplers.copy(),
                  scores=scores.copy(), valid=valid.copy(), top_k=top,
                  selected=selected, accepted=accepted,
                  candidate_columns=C, slot_tests=P * C,
                  valid_slot_tests=int(np.count_nonzero(valid)),
                  duplicate_rejections=int(np.count_nonzero(~valid)),
                  elapsed_seconds=time.perf_counter() - step_start)
    if compact_stats is not None:
        record["compact_stats"] = compact_stats
    return record


def _direct_global(Y, xt, v, initial, c1, c2, ridge, bank, chunk_size,
                   duplicate_tolerance, max_edits, top_k, energy, counts):
    """Complete direct replay used by fallback, from the original entry state."""
    delays, dopplers, _ = bank
    current = initial.copy()
    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge)
    counts["joint_gain_solves"] += 1
    edits, traces = [], []
    for step in range(max_edits):
        started = time.perf_counter()
        B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge)
        counts["joint_gain_solves"] += 1
        scores, valid = _direct_scores(Y, xt, v, current, B, Q, b, c1, c2, ridge,
                                       delays, dopplers, chunk_size, energy,
                                       duplicate_tolerance, counts)
        winner, selected, top = _select(scores, valid, delays, dopplers, current, top_k)
        accepted = None
        before = current.copy()
        entering_h, entering_value = h.copy(), value
        if winner is not None:
            slot, index = divmod(winner, len(delays))
            score = float(scores[slot, index])
            if _improvement(value, score):
                old = current[slot]
                proposed = current.copy()
                new_path = Path(int(delays[index]), float(dopplers[index]))
                proposed[slot] = new_path
                new_B, new_Q, new_b, new_h, new_value, new_gamma = _system(
                    Y, xt, v, proposed, c1, c2, ridge)
                counts["joint_gain_solves"] += 1
                if abs(new_value - score) > 1e-7 * (1 + abs(score)):
                    raise AssertionError("direct Schur/refit score mismatch")
                if not _improvement(value, new_value):
                    raise AssertionError("direct winner failed strict decrease")
                accepted = dict(slot=slot, old=asdict(old), new=asdict(new_path),
                                frozen_score=score, direct_score=new_value,
                                decrease=float(value - new_value))
                edits.append(dict(step=step, slot=slot, old=asdict(old),
                                  new=asdict(new_path), decrease=float(value - new_value)))
                current = proposed
                B, Q, b, h, value, gamma = new_B, new_Q, new_b, new_h, new_value, new_gamma
                counts["global_accepted"] += 1
        if accepted is None:
            counts["global_rejected_steps"] += 1
        traces.append(_trace(step, before, entering_h, entering_value, delays, dopplers,
                             scores, valid, selected, top, accepted, started))
        if accepted is None:
            break
    return current, B, Q, b, h, value, gamma, edits, traces


def _improvement(before, after):
    return before - after > 1e-10 * (1 + abs(before))


def reopen_geometry(Y, x_mean_af, v, paths, *, c1, c2, ridge, max_delay,
                    doppler_min=-3., doppler_max=3., grid_step=.25,
                    max_edits=2, chunk_size=64, local_passes=2,
                    local_halfwidth=.75, local_max_evals=16,
                    duplicate_tolerance=1e-6, top_k=20,
                    strategy="direct") -> ExchangeResult:
    """Return a fully instrumented old-schema result for the selected strategy.

    ``strategy='compact'`` replaces only the structural score engine.  On a
    numerical guard failure, it discards that attempt and replays the original
    full-grid direct search from the original entering geometry. AssertionError
    is an algebra failure and propagates. ``max_edits=0`` is LOCAL20.
    """
    clock = StageClock()
    if strategy not in ("direct", "compact"):
        raise ValueError("strategy must be direct or compact")
    Y, x, v, current = _validate(Y, x_mean_af, v, paths, c1, c2, ridge,
                                 max_delay, doppler_min, doppler_max, grid_step,
                                 max_edits, chunk_size, local_passes, local_halfwidth,
                                 local_max_evals, duplicate_tolerance, top_k)
    initial_paths = current.copy()
    xt = daft(x, c1, c2, inverse=True)
    bank = _bank(max_delay, doppler_min, doppler_max, grid_step)
    delays, dopplers, nus = bank
    P, C = len(current), len(delays)
    energy = float(np.vdot(x, x).real + np.sum(v))
    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge)
    initial_value = value
    counts = _empty_counts()
    counts["joint_gain_solves"] = 1
    edits, traces, local_trace = [], [], []
    fallback_reason = None
    discarded_trace = []
    discarded_counts = None
    discarded_compact_seconds = 0.

    if max_edits and strategy == "compact":
        try:
            clock.enter("structural_field_build")
            candidates = [Path(int(delay), float(nu))
                          for delay, nu in zip(delays, dopplers)]
            field = CPPField(xt, c1, max_delay, nus)
            beta = field.correlate(Y)
            vf = np.fft.fft(v)
            K = np.vstack([np.conj(field.correlate(B[:, i])) for i in range(P)])
            K += _gamma_cross(current, candidates, vf, c1)
            counts["compact_field_calls"] = field.calls
            diagonal = energy + ridge
            state = state_from_normal(Q, b, float(np.vdot(Y, Y).real))
            if np.linalg.cond(Q) > 1e8:
                raise FloatingPointError("compact normal condition exceeds 1e8")
            for step in range(max_edits):
                started = time.perf_counter()
                entering = current.copy()
                entering_h, entering_value = h.copy(), value
                clock.enter("structural_scoring")
                scores, compact_stats = exchange_scores(state, K, beta, diagonal)
                counts["compact_score_batches"] += 1
                counts["global_candidate_columns"] += C
                counts["global_slot_tests"] += P * C
                valid = _valid(current, candidates, duplicate_tolerance)
                counts["global_duplicate_rejections"] += int(np.count_nonzero(~valid))
                clock.enter("structural_selection_trace")
                winner, selected, top = _select(scores, valid, delays, dopplers, current, top_k)
                accepted = None
                score = float(scores.ravel()[winner]) if winner is not None else float("inf")
                if winner is not None and _improvement(value, score):
                    slot, index = divmod(winner, C)
                    old = current[slot]
                    trial = current.copy()
                    trial[slot] = candidates[index]
                    clock.enter("structural_refit_refresh")
                    new_B, new_Q, new_b, new_h, new_value, new_gamma = _system(
                        Y, xt, v, trial, c1, c2, ridge)
                    counts["joint_gain_solves"] += 1
                    if abs(new_value - score) > 1e-7 * (1 + abs(score)):
                        raise AssertionError("compact/direct objective mismatch")
                    if not _improvement(value, new_value):
                        raise AssertionError("compact winner failed direct strict decrease")
                    accepted = dict(slot=slot, old=asdict(old), new=asdict(candidates[index]),
                                    frozen_score=score, direct_score=new_value,
                                    decrease=float(value - new_value))
                    edits.append(dict(step=step, slot=slot, old=asdict(old),
                                      new=asdict(candidates[index]), decrease=float(value - new_value)))
                    current = trial
                    B, Q, b, h, value, gamma = new_B, new_Q, new_b, new_h, new_value, new_gamma
                    counts["global_accepted"] += 1
                    state = state_from_normal(Q, b, float(np.vdot(Y, Y).real))
                    if np.linalg.cond(Q) > 1e8:
                        raise FloatingPointError("compact normal condition exceeds 1e8 after edit")
                    if step + 1 < max_edits:
                        K[slot, :] = (np.conj(field.correlate(B[:, slot]))
                                      + _gamma_cross([current[slot]], candidates, vf, c1)[0])
                        counts["compact_field_calls"] = field.calls
                        counts["compact_changed_row_refreshes"] += 1
                else:
                    counts["global_rejected_steps"] += 1
                clock.enter("structural_selection_trace")
                traces.append(_trace(step, entering, entering_h, entering_value,
                                     delays, dopplers, scores, valid, selected, top,
                                     accepted, started, compact_stats))
                if accepted is None:
                    break
        except (FloatingPointError, np.linalg.LinAlgError) as exc:
            fallback_reason = str(exc)
            discarded_trace = traces
            discarded_counts = counts.copy()
            counts = _empty_counts()
            counts["fallback_calls"] = 1
            counts["discarded_compact_evaluations"] = discarded_counts
            clock.enter("structural_fallback_direct")
            discarded_compact_seconds = sum(clock.seconds[name] for name in (
                "structural_field_build", "structural_scoring",
                "structural_selection_trace", "structural_refit_refresh"))
            current, B, Q, b, h, value, gamma, edits, traces = _direct_global(
                Y, xt, v, initial_paths, c1, c2, ridge, bank, chunk_size,
                duplicate_tolerance, max_edits, top_k, energy, counts)
    elif max_edits:
        for step in range(max_edits):
            started = time.perf_counter()
            entering = current.copy()
            entering_h, entering_value = h.copy(), value
            clock.enter("structural_scoring")
            B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge)
            counts["joint_gain_solves"] += 1
            scores, valid = _direct_scores(Y, xt, v, current, B, Q, b, c1, c2,
                                           ridge, delays, dopplers, chunk_size,
                                           energy, duplicate_tolerance, counts)
            clock.enter("structural_selection_trace")
            winner, selected, top = _select(scores, valid, delays, dopplers, current, top_k)
            accepted = None
            if winner is not None:
                slot, index = divmod(winner, C)
                score = float(scores[slot, index])
                if _improvement(value, score):
                    old = current[slot]
                    trial = current.copy()
                    new_path = Path(int(delays[index]), float(dopplers[index]))
                    trial[slot] = new_path
                    clock.enter("structural_refit_refresh")
                    new_B, new_Q, new_b, new_h, new_value, new_gamma = _system(
                        Y, xt, v, trial, c1, c2, ridge)
                    counts["joint_gain_solves"] += 1
                    if abs(new_value - score) > 1e-7 * (1 + abs(score)):
                        raise AssertionError("direct Schur/refit score mismatch")
                    if not _improvement(value, new_value):
                        raise AssertionError("direct winner failed strict decrease")
                    accepted = dict(slot=slot, old=asdict(old), new=asdict(new_path),
                                    frozen_score=score, direct_score=new_value,
                                    decrease=float(value - new_value))
                    edits.append(dict(step=step, slot=slot, old=asdict(old),
                                      new=asdict(new_path), decrease=float(value - new_value)))
                    current = trial
                    B, Q, b, h, value, gamma = new_B, new_Q, new_b, new_h, new_value, new_gamma
                    counts["global_accepted"] += 1
            if accepted is None:
                counts["global_rejected_steps"] += 1
            clock.enter("structural_selection_trace")
            traces.append(_trace(step, entering, entering_h, entering_value,
                                 delays, dopplers, scores, valid, selected, top,
                                 accepted, started))
            if accepted is None:
                break

    clock.enter("local_refinement")
    centers = [p.doppler for p in current]
    local_entering = [asdict(p) for p in current]
    for pass_index in range(local_passes):
        for slot in range(P):
            coordinate_start = time.perf_counter()
            lo = max(doppler_min, centers[slot] - local_halfwidth)
            hi = min(doppler_max, centers[slot] + local_halfwidth)
            incumbent = value
            start_path = current[slot]
            best_path, best_value = start_path, value
            trials = []
            others = current[:slot] + current[slot + 1:]

            def objective(nu):
                nonlocal best_path, best_value
                test = Path(current[slot].delay, float(nu))
                counts["local_trials"] += 1
                if _duplicate(test, others, duplicate_tolerance):
                    counts["local_duplicate_rejections"] += 1
                    trials.append(dict(doppler=float(nu), valid=False, score=None))
                    return float("inf")
                trial = current.copy()
                trial[slot] = test
                *_, score, _gamma = _system(Y, xt, v, trial, c1, c2, ridge)
                counts["joint_gain_solves"] += 1
                trials.append(dict(doppler=float(nu), valid=True, score=score))
                if _improvement(best_value, score):
                    best_path, best_value = test, score
                return score

            minimize_scalar(objective, bounds=(lo, hi), method="bounded",
                            options={"xatol": .002, "maxiter": local_max_evals})
            accepted = _improvement(incumbent, best_value)
            if accepted:
                current[slot] = best_path
                value = best_value
                counts["local_accepted"] += 1
            local_trace.append(dict(pass_index=pass_index, slot=slot,
                                    local_phase_entering_paths=local_entering,
                                    center=centers[slot], bounds=(lo, hi),
                                    start=asdict(start_path), start_objective=incumbent,
                                    endpoint=asdict(current[slot]), endpoint_objective=value,
                                    accepted=accepted, trials=trials, trial_count=len(trials),
                                    rejected_duplicate_trials=sum(not t["valid"] for t in trials),
                                    elapsed_seconds=time.perf_counter() - coordinate_start))

    clock.enter("geometry_finalization")
    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge)
    counts["joint_gain_solves"] += 1
    if value > initial_value + 1e-8 * (1 + abs(initial_value)):
        raise AssertionError("frozen geometry objective increased")
    physical = Channel(len(Y), c1, c2, [p.delay for p in current],
                       [p.doppler for p in current], np.ones(P, complex))
    diagnostics = dict(gamma=gamma, response_gram=B.conj().T @ B,
                       physical_operator_gram=TimePathOps(physical).R,
                       ridge_lambda=float(ridge),
                       local_window_centers=np.asarray(centers),
                       improvement_guard="a-b > 1e-10*(1+abs(a))",
                       strategy=strategy, selection_order="score,slot,delay,doppler",
                       numerical_fallback=fallback_reason is not None,
                       fallback_reason=fallback_reason,
                       discarded_compact_trace=discarded_trace,
                       discarded_compact_evaluations=discarded_counts)
    condition = float(np.linalg.cond(Q))
    power = float(np.vdot(h, h).real)
    diagnostics["stage_timing"] = clock.finish()
    diagnostics["stage_timing"]["discarded_compact_seconds"] = discarded_compact_seconds
    elapsed = diagnostics["stage_timing"]["total_seconds"]
    return ExchangeResult(current, h, initial_value, value, edits, counts,
                          elapsed, condition, power, traces, local_trace, diagnostics)


def score_entering_state(Y, x_mean_af, v, paths, *, strategy="compact", **kwargs):
    """Qualify one frozen entering state without a receiver or truth access.

    Uses one complete structural step with no local passes and returns its full
    score grid, mask and chosen action.  A guarded compact failure is replayed
    through the direct all-grid path, exactly as in ``reopen_geometry``.
    """
    kwargs.pop("max_edits", None)
    kwargs.pop("local_passes", None)
    result = reopen_geometry(Y, x_mean_af, v, paths, strategy=strategy,
                             max_edits=1, local_passes=0, **kwargs)
    if not result.global_trace:
        raise AssertionError("qualification did not produce a structural step")
    return result.global_trace[0], result
