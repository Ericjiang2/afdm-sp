"""F2 supplement: free-frequency per-tap D-exponential oracle (variable projection, multi-start).

For tap l with rays (nu_r, g_r) and tap sequence a_l[n] = sum_r g_r exp(2j*pi*nu_r*n/N):
  min over nu in R^D of  min_c ||a_l - E(nu) c||^2   (c = LS gains; D >= R -> the true rays, misfit 0).
Starts: contiguous Doppler groups with power-weighted centroids, lattice start (spacing .7), 3 random subsets of rays.
Deterministic: the generator is seeded from the tap's own (nu_r, g_r) bytes only, so the fit is SNR-independent.
Misfit identity of orders.py applies (operator misfit = sum_l ||a_l - fit_l||^2 / sum_l ||a_l||^2).
"""
import hashlib

import numpy as np
from scipy.optimize import minimize

import orders


def _vp(nu, a, k, n):
    E = np.exp(2j * np.pi * np.outer(k, nu) / n)
    c = np.linalg.lstsq(E, a, rcond=None)[0]
    r = a - E @ c
    return float(np.vdot(r, r).real)


def free_fit(a, nu_r, g_r, D, n, rng):
    """Return (nu (D,), gains (D,), residual energy)."""
    k = np.arange(n)
    nu_r, g_r = np.asarray(nu_r, float), np.asarray(g_r, complex)
    R = len(nu_r)
    if D >= R:  # the true rays reproduce the tap exactly
        nu = np.concatenate([nu_r, nu_r.max() + 1.0 + np.arange(D - R)]) if D > R else nu_r.copy()
        c = np.linalg.lstsq(np.exp(2j * np.pi * np.outer(k, nu) / n), a, rcond=None)[0]
        return nu, c, _vp(nu, a, k, n)
    w = np.abs(g_r) ** 2
    order = np.argsort(nu_r)
    starts = [np.array([np.sum(w[c] * nu_r[c]) / np.sum(w[c]) for c in np.array_split(order, D)])]
    starts.append(orders.subpath_grid(orders.centroid(nu_r, g_r), D, 0.7))
    for _ in range(3):
        starts.append(np.sort(rng.choice(nu_r, size=D, replace=False) + 0.2 * rng.standard_normal(D)))
    best = (None, np.inf)
    for s in starts:
        res = minimize(_vp, s, args=(a, k, n), method='L-BFGS-B', options=dict(maxiter=60))
        for cand, val in ((res.x, res.fun), (s, _vp(s, a, k, n))):
            if val < best[1]:
                best = (np.asarray(cand, float), val)
    nu = best[0]
    c = np.linalg.lstsq(np.exp(2j * np.pi * np.outer(k, nu) / n), a, rcond=None)[0]
    return nu, c, best[1]


def free_paths(delays, dopplers, gains, D, n):
    """Flat (l, nu, g) path list with D free-frequency exponentials per tap + relative operator misfit."""
    ls, nus, gs = [], [], []
    num = den = 0.
    for d, (nu_r, g_r) in sorted(orders.tap_groups(delays, dopplers, gains).items()):
        a = orders.tap_sequence(nu_r, g_r, n)
        seed = int.from_bytes(hashlib.sha256(np.ascontiguousarray(np.r_[nu_r, np.abs(g_r)]).tobytes()).digest()[:8], 'little')
        nu, c, resid = free_fit(a, nu_r, g_r, D, n, np.random.default_rng(seed))
        ls += [d] * len(nu)
        nus += list(nu)
        gs += list(c)
        num += resid
        den += float(np.vdot(a, a).real)
    return np.array(ls, int), np.array(nus, float), np.array(gs, complex), num / den
