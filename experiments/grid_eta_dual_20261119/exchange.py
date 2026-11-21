"""Forced-miss first-step scoring with one candidate Doppler replaced in place."""

from types import FunctionType, SimpleNamespace
import time

import numpy as np

DELTAS = (.25, .125, .0625)
ARMS = ("A2", "CODELAY")


def shifted_kernel(kernel, index, target):
    # The frozen kernel has no candidate override. Bind its bank and CPP
    # field locally so both the compact and direct routes see the same columns.
    source = kernel.reopen_geometry

    def bank(*args):
        delays, dopplers, regular = kernel._bank(*args)
        dopplers[index] = target
        return delays, dopplers, regular

    class Field:
        def __init__(self, xt, c1, max_delay, regular):
            self.original = kernel.CPPField(xt, c1, max_delay, regular)
            self.added = kernel.CPPField(xt, c1, max_delay, [target])
            self.delay = index // len(regular)

        @property
        def calls(self):
            return self.original.calls

        def correlate(self, z):
            correlations = self.original.correlate(z)
            correlations[index] = self.added.correlate(z)[self.delay]
            return correlations

    reopen = FunctionType(source.__code__, dict(source.__globals__, _bank=bank, CPPField=Field),
                          source.__name__, source.__defaults__)
    reopen.__kwdefaults__ = source.__kwdefaults__
    return SimpleNamespace(__name__=kernel.__name__, Path=kernel.Path, reopen_geometry=reopen,
                           exchange_scores=kernel.exchange_scores, _direct_scores=kernel._direct_scores,
                           _direct_global=kernel._direct_global)


def first_scores(study, options, obs, r1, truth, weak, paired, sweep):
    captures = {}

    def adapter(name, kernel):
        observe = paired.instrument(kernel)

        def capture(*args, **kwargs):
            result, matrix = observe(*args, **kwargs)
            captures[name] = (result.global_trace[0], matrix,
                              result.diagnostics["numerical_fallback"])
            return result

        return SimpleNamespace(Path=kernel.Path, reopen_geometry=capture)

    q, ctx, variant, _, _, sources = study
    wrapped = (q, ctx, variant, *(adapter(name, k) for name, k in zip(ARMS, options)), sources)
    # The legacy eligible-only path has the same first search as the triggered
    # path and never invokes a continuation detector or decoder.
    sweep.continuation(wrapped, obs, r1, truth, weak, eligible=True, triggered=False)
    return captures


def process(study, modules, frame, ratio, *, nominal_only=False):
    start = time.process_time()
    v2, sweep, paired = modules
    _, ctx, _, full, closed, _ = study
    draw = sweep.draw_frame(study, frame)
    weak = draw["weak"]
    base, truth = sweep.controlled_base(ctx, draw, .3, ratio, background_clip=v2.BACKGROUND_CLIP)
    obs = sweep.observation(ctx, base, .3, 4.5)
    weak_delay = int(truth["l_i"][weak])
    _, r1, syndrome = v2.f0_state(study, obs, weak_delay)
    anchor = paired.anchor_index(r1)
    if weak_delay in r1["r1_delays"]:
        raise AssertionError("Masked F0 selected the weak delay")
    kernels = (full, closed)
    baseline = first_scores(study, kernels, obs, r1, truth, weak, paired, sweep)
    slot = paired.deletion_slot(baseline["A2"][0], anchor)
    prior = {}
    for name, (trace, gains, fallback) in baseline.items():
        prior[name] = dict(pair=paired.pair(trace, gains, anchor, slot, weak_delay),
                           numerical_fallback=fallback)
    result = dict(frame=frame, rho=.3, snr_db=4.5, R=ratio, syndrome=int(syndrome),
                  anchor_delay=int(r1["r1_delays"][anchor]),
                  anchor_doppler=float(r1["r1_dopplers"][anchor]),
                  weak_delay=weak_delay, slot=slot, nominal=prior)
    if nominal_only:
        return dict(result, seconds=time.process_time() - start)

    a2 = prior["A2"]["pair"]
    weak_index = a2["weak_index"]
    nominal_trace = baseline["A2"][0]
    dopplers = nominal_trace["candidate_dopplers"]
    targets = {delta: result["anchor_doppler"] + delta for delta in DELTAS}
    bank_at_anchor = dopplers[nominal_trace["candidate_delays"] == result["anchor_delay"]]
    retained_at_anchor = [
        path["doppler"] for i, path in enumerate(nominal_trace["entering_paths"])
        if i != slot and path["delay"] == result["anchor_delay"]]
    radio_min, radio_max = sweep.BANK["doppler_min"], sweep.BANK["doppler_max"]
    comparisons = np.r_[bank_at_anchor, retained_at_anchor]
    excluded = {}
    for delta, target in targets.items():
        if not radio_min <= target <= radio_max:
            excluded[str(delta)] = "outside_bank"
        elif np.any(abs(comparisons - target) < sweep.DUPLICATE):
            excluded[str(delta)] = "duplicate_atom"
    if excluded:
        return dict(result, exclusions=excluded, seconds=time.process_time() - start)

    shifts = {}
    index = a2["phantom_index"]
    for delta, target in targets.items():
        expected = dopplers.copy()
        expected[index] = target
        trial = tuple(shifted_kernel(k, index, target) for k in kernels)
        scores = first_scores(study, trial, obs, r1, truth, weak, paired, sweep)
        arms = {}
        for name, (trace, gains, fallback) in scores.items():
            old_trace = baseline[name][0]
            if (trace["entering_paths"] != old_trace["entering_paths"]
                    or not np.array_equal(trace["entering_gains"], old_trace["entering_gains"])
                    or not np.array_equal(trace["candidate_delays"], old_trace["candidate_delays"])
                    or not np.array_equal(trace["candidate_dopplers"], expected)
                    or not trace["valid"][slot, [index, weak_index]].all()):
                raise AssertionError(f"{frame=}, {delta=}, {name=}: invalid paired replay")
            phantom, weak_gain = (float(gains[slot, i]) for i in (index, weak_index))
            arms[name] = dict(phantom_gain=phantom, weak_gain=weak_gain, Q=phantom > weak_gain,
                              numerical_fallback=fallback)
        shifts[str(delta)] = dict(phantom_doppler=target, weak_doppler=float(dopplers[weak_index]),
                                  candidate_count=len(dopplers), arms=arms)
    return dict(result, deltas=shifts, seconds=time.process_time() - start)
