"""E-2 co-delay guard predicates (design.md section 2).  numpy only; imported by geometry_validation_guard.py.

mode 'off'      no conflict, ever (the variant is then bitwise the E-1 variant).
mode 'all'      a candidate (l, nu) conflicts with a current path p iff l == p.delay.
mode 'neardup'  ... iff l == p.delay and |D_N(nu - p.doppler)| >= NEARDUP_THRESHOLD,
                D_N(x) = sin(pi x) / (N sin(pi x / N)), D_N(0) = 1 (limit), N = len(Y).
"others" is always the set of current paths EXCLUDING the slot being replaced (or moved, in the local refinement).
"""
from __future__ import annotations

import numpy as np

NEARDUP_THRESHOLD = .5
MODES = ('off', 'all', 'neardup')


def abs_dn(x, n):
    """|D_N(x)| elementwise, with the x -> 0 limit equal to 1."""
    x = np.abs(np.asarray(x, dtype=float))
    out = np.ones_like(x)
    nz = x != 0
    out[nz] = np.abs(np.sin(np.pi * x[nz]) / (n * np.sin(np.pi * x[nz] / n)))
    return out


def _check(mode):
    if mode not in MODES:
        raise ValueError("codelay_guard must be off, all or neardup")


def conflict_matrix(cur_delays, cur_dopplers, cand_delays, cand_dopplers, n, mode):
    """(P, C) bool: current path i conflicts with candidate j (co-delay [and near-duplicate Doppler]).
    The caller combines it with the duplicate mask exactly like a duplicate: slot s may take candidate j iff no OTHER path conflicts."""
    _check(mode)
    cur_delays, cand_delays = np.asarray(cur_delays), np.asarray(cand_delays)
    hit = np.zeros((len(cur_delays), len(cand_delays)), dtype=bool)
    if mode == 'off':
        return hit
    co = cur_delays[:, None] == cand_delays[None, :]
    if mode == 'all':
        return co
    ii, jj = np.nonzero(co)
    hit[ii, jj] = abs_dn(np.asarray(cand_dopplers, float)[jj] - np.asarray(cur_dopplers, float)[ii], n) >= NEARDUP_THRESHOLD
    return hit


def hits_group(group, others, n, mode):
    """(C,) bool: candidate group[j] conflicts with at least one path of ``others`` (objects with .delay / .doppler)."""
    _check(mode)
    out = np.zeros(len(group), dtype=bool)
    if mode == 'off' or not others or not group:
        return out
    cm = conflict_matrix([p.delay for p in others], [p.doppler for p in others],
                         [g.delay for g in group], [g.doppler for g in group], n, mode)
    return cm.any(axis=0)


def path_conflicts(path, others, n, mode):
    """True iff ``path`` conflicts with some path of ``others`` (local Doppler refinement trial)."""
    return bool(hits_group([path], others, n, mode)[0])
