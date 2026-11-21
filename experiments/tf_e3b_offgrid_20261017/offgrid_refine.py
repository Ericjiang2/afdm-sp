"""E-3b continuous Doppler refinement of the SBL output atoms (design.md section 1.3).  numpy / scipy only.

Objective (frozen E-1 variant kernel, imported read-only):
    value(paths) = geometry_reopen_variant._system(Y, xt, v_m, paths, c1, c2, ridge = sigma2, gamma_mode = g_m)[4]
with Y = daft(y, c1, c2, True) and xt = daft(pilot + x_data, c1, c2, inverse=True) -- the conventions of the E-3 dictionary and of the E-1 branch.
Procedure: P = 3 passes; each pass visits the atoms in the order given (descending SBL energy); for atom k, all others fixed, a bounded scalar search
(scipy minimize_scalar 'bounded', xatol 1e-3, at most 16 evaluations) over [center_k - .5, center_k + .5] intersected with [-3, 3]; the new Doppler is
accepted only on a STRICT decrease of value (best evaluated point, plain '<').  Delays and atom count are fixed; no duplicate guard of any kind.
The window centre is the SBL output Doppler (fixed over the three passes, as in the CSTATE local phase: "windows are fixed at the geometry entering the
local phase"); this reading of design 1.3 is declared in PROTOCOL.md.  The final gains are _system's h at the final geometry.
Nothing here catches an exception of _system: a failure propagates and the key becomes an error row (E-3 convention).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

import e3b_lib  # noqa: F401  (sys.path: frozen modules, E-1 directory)

from geometry_reopen_variant import Path, _system  # noqa: E402  (frozen E-1 variant kernel, read-only)

PASSES = 3
HALF_WIDTH = .5
XATOL = 1e-3
MAX_EVALS = 16
DOPPLER = (-3., 3.)
HYPER = dict(passes=PASSES, half_width=HALF_WIDTH, xatol=XATOL, max_evals=MAX_EVALS, doppler=DOPPLER, acceptance='strict decrease (<)',
             window='fixed at the SBL output Doppler', objective='geometry_reopen_variant._system value, ridge = sigma2')


def refine(Y, xt, v, delays, dopplers, c1, c2, ridge, gamma_mode='full', passes=PASSES, half_width=HALF_WIDTH, xatol=XATOL, max_evals=MAX_EVALS):
    """Refine ``dopplers`` of the atoms (delays fixed; atoms in descending-energy order).  v is the data variance vector (zeros for hard / genie).

    Returns dict(dopplers, gains, value_before, value_after, monotone, ...) with per-coordinate statistics (no per-evaluation trace)."""
    delays = [int(x) for x in delays]
    nus = [float(x) for x in dopplers]
    if not len(delays) == len(nus) >= 1:
        raise ValueError('atoms: matching, non-empty delay / Doppler lists required')
    v = np.asarray(v, dtype=float)

    def system(values):
        return _system(Y, xt, v, [Path(l, nu) for l, nu in zip(delays, values)], c1, c2, ridge, gamma_mode)

    value = value0 = system(nus)[4]
    centers = list(nus)
    start = list(nus)
    trace = [value0]
    accepted_by_pass = [0] * passes
    evals_total = 0
    max_evals_coord = 0
    n_accept = 0
    for p in range(passes):
        for k in range(len(nus)):
            lo = max(DOPPLER[0], centers[k] - half_width)
            hi = min(DOPPLER[1], centers[k] + half_width)
            best = [value, nus[k]]
            count = [0]

            def objective(nu):
                trial = list(nus)
                trial[k] = float(nu)
                score = system(trial)[4]
                count[0] += 1
                if score < best[0]:
                    best[0], best[1] = score, float(nu)
                return score

            minimize_scalar(objective, bounds=(lo, hi), method='bounded', options=dict(xatol=xatol, maxiter=max_evals))
            evals_total += count[0]
            max_evals_coord = max(max_evals_coord, count[0])
            if best[0] < value:                       # strict decrease only
                nus[k], value = best[1], best[0]
                accepted_by_pass[p] += 1
                n_accept += 1
            trace.append(value)
    B, Q, b, h, value_after, gamma = system(nus)
    offdiag = gamma - np.diag(np.diag(gamma))
    total_v = float(v.sum())
    shift = np.abs(np.asarray(nus) - np.asarray(start))
    return dict(dopplers=np.asarray(nus, dtype=float), gains=h, value_before=float(value0), value_after=float(value_after),
                monotone=bool(all(b_ <= a_ for a_, b_ in zip(trace[:-1], trace[1:])) and value_after <= value0),
                value_recheck_equal=bool(value_after == value), n_coord=int(passes * len(nus)), n_accept=int(n_accept),
                accepted_by_pass=[int(x) for x in accepted_by_pass], evals=int(evals_total), max_evals_coord=int(max_evals_coord),
                shift_abs_max=float(shift.max()), shift_abs_mean=float(shift.mean()), n_moved=int(np.count_nonzero(shift > 0)),
                in_bounds=bool(np.all((np.asarray(nus) >= DOPPLER[0]) & (np.asarray(nus) <= DOPPLER[1]))),
                in_window=bool(np.all(np.abs(np.asarray(nus) - np.asarray(centers)) <= half_width + 1e-12)),
                gamma_abs_max=float(np.max(np.abs(gamma))), gamma_offdiag_abs_max=float(np.max(np.abs(offdiag))) if len(nus) > 1 else 0.,
                gamma_diag_rel_err=(float(np.max(np.abs(np.diag(gamma).real - total_v)) / total_v) if total_v > 0 else None),
                cond_Q=float(np.linalg.cond(Q)))
