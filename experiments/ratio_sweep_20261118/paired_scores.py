"""Observe the native first-step Schur matrices without changing selection."""
import inspect
from types import FunctionType, SimpleNamespace

import numpy as np


def _observe_source(function, edits, additions):
    source = inspect.getsource(function)
    for old, new in edits:
        if source.count(old) != 1:
            raise ValueError(f"Frozen score site changed: {function.__name__}")
        source = source.replace(old, new)
    namespace = dict(function.__globals__, **additions)
    exec(compile(source, inspect.getfile(function), "exec"), namespace)
    return namespace[function.__name__]


def instrument(kernel):
    """Bind scoped observers to both native score routes, leaving modules untouched."""
    compact, direct = [], []
    compact_fn = _observe_source(kernel.exchange_scores, [(
        "    values = state.objective - addition[None, :] + deletion",
        "    values = state.objective - addition[None, :] + deletion\n"
        "    _observe(addition[None, :] + (abs(state.gains) ** 2 / np.diag(state.inverse).real)[:, None] - deletion)",
    )], {"_observe": compact.append})
    direct_edits = [
        ("    scores = np.empty((P, C), dtype=np.float64)",
         "    scores = np.empty((P, C), dtype=np.float64)\n    gross = np.empty_like(scores)"),
        ("            values = vr - abs(g) ** 2 / schur",
         "            gain = abs(g) ** 2 / schur\n"
         "            gross[slot, first:last] = gain\n"
         "            values = vr - gain"),
        ("    return scores, valid", "    _observe(gross)\n    return scores, valid"),
    ]
    if kernel.__name__ == "stage3_codelay_geometry":
        # inspect reads the original file, so retain CODELAY's reviewed in-memory binding.
        direct_edits.append(("vf = np.fft.fft(v)", "vf = (float(v.sum()), len(v))"))
    direct_fn = _observe_source(kernel._direct_scores, direct_edits, {"_observe": direct.append})
    reopen_globals = dict(kernel.reopen_geometry.__globals__, exchange_scores=compact_fn, _direct_scores=direct_fn)
    fallback = kernel._direct_global
    reopen_globals["_direct_global"] = FunctionType(fallback.__code__, reopen_globals, fallback.__name__,
                                                      fallback.__defaults__)
    reopen = kernel.reopen_geometry
    bound = FunctionType(reopen.__code__, reopen_globals, reopen.__name__, reopen.__defaults__)
    bound.__kwdefaults__ = reopen.__kwdefaults__

    def observed(*args, **opts):
        compact.clear()
        direct.clear()
        result = bound(*args, **opts)
        ran_direct = opts["strategy"] == "direct" or result.diagnostics["numerical_fallback"]
        matrix = (direct if ran_direct else compact)[0]
        return result, matrix

    return observed


def anchor_index(r1):
    return int(np.argmax(abs(r1["r1_gains"]) ** 2))


def pair(trace, matrix, anchor, slot, weak_delay):
    delays, nus = trace["candidate_delays"], trace["candidate_dopplers"]
    paths = trace["entering_paths"]
    anchor_path = paths[anchor]
    allowed = trace["valid"][slot]
    phantom = np.flatnonzero(allowed & (delays == anchor_path["delay"]))
    weak = np.flatnonzero(allowed & (delays == weak_delay))
    if not len(phantom) or not len(weak):
        raise ValueError("Frozen candidate pair is missing at the designated slot")
    offsets = abs(nus[phantom] - anchor_path["doppler"])
    p = int(phantom[np.lexsort((nus[phantom], offsets))[0]])
    w = int(weak[np.argmax(matrix[slot, weak])])
    gain_p, gain_w = (float(matrix[slot, index]) for index in (p, w))
    edit = trace["accepted"]
    kind = "no_edit"
    if edit is not None:
        edit_delay = edit["new"]["delay"]
        survives = any(i != edit["slot"] and q["delay"] == edit_delay for i, q in enumerate(paths))
        if survives and edit_delay != anchor_path["delay"]:
            kind = "another_anchor_phantom"
        elif any(edit["new"] == {"delay": int(delays[i]), "doppler": float(nus[i])} for i in (p, w)):
            kind = "designated_candidate"
        else:
            kind = "third_candidate"
    return dict(slot=slot, phantom_index=p, weak_index=w, phantom_doppler=float(nus[p]),
                weak_doppler=float(nus[w]), phantom_gain=gain_p, weak_gain=gain_w, Q=gain_p > gain_w,
                global_winner=kind)


def deletion_slot(trace, anchor):
    keep = np.flatnonzero(np.arange(len(trace["entering_paths"])) != anchor)
    return int(keep[np.argmin(abs(trace["entering_gains"][keep]) ** 2)])


def run_from_r1(study, observers, obs, r1, truth, weak, syndrome, window, *, audit=None):
    """The A2 entering fit specifies the single deletion slot used in both arms."""
    import forced_miss

    q, ctx, variant, full, closed, sources = study
    anchor = anchor_index(r1) if window is not None else None
    entries = {}
    slot = None
    weak_delay = int(truth["l_i"][weak])

    def adapter(name, kernel):
        def reopen(*args, **opts):
            nonlocal slot
            result, matrix = observers[name](*args, **opts)
            trace = result.global_trace[0]
            row = dict(numerical_fallback=result.diagnostics["numerical_fallback"], pair=None)
            if anchor is not None:
                if name == "A2":
                    slot = deletion_slot(trace, anchor)
                row["pair"] = pair(trace, matrix, anchor, slot, weak_delay)
            entries[name] = row
            if audit is not None:
                audit(name, kernel, args, opts, result, matrix, row["pair"], anchor)
            return result
        return SimpleNamespace(Path=kernel.Path, reopen_geometry=reopen)

    wrapped = (q, ctx, variant, adapter("A2", full), adapter("CODELAY", closed), sources)
    arms = forced_miss.exchange_from_r1(wrapped, obs, r1, truth, weak, syndrome)
    for name, arm in arms.items():
        arm.update(entries[name])
    return arms
