"""M1 DPSS oracle: project each TRUE tap sequence onto D modulated DPSS around the power-weighted centroid.

Operator fact (orders.py): the delay-l tap enters the operator only through a_l[n] = sum_{rays at l} g_r e^{2j pi nu_r n/N};
||H - H_alt||_F^2 = sum_l ||a_l - a_l'||^2, ||H||_F^2 = sum_l ||a_l||^2  =>  misfit = sum_l||a_l-a~_l||^2 / sum_l||a_l||^2.

Basis for tap l: e_d[n] = exp(2j pi c_l n/N) v_d[n], d = 0..D-1, v_d = scipy.signal.windows.dpss(N, NW=W_l, Kmax, sym=True,
norm=2) (real, orthonormal, NW = W_l bins because half-bandwidth W_cyc = W_l/N cycles/sample and NW = N W_cyc).
c_l = power-weighted ray centroid, W_l = max_r |nu_r - c_l| + 0.5 bins (so every ray lies inside [c_l-W_l, c_l+W_l]).
Projection a~ = E E^H a (orthonormal E => LS, no ridge).  Nested in D (first D columns of the same basis).
"""
from __future__ import annotations

import numpy as np
from scipy.signal.windows import dpss

import orders

D_LADDER = (1, 2, 3, 4, 6)
W_MARGIN = 0.5


def tap_band(nu, g, margin=W_MARGIN):
    c = orders.centroid(nu, g)
    half = float(np.max(np.abs(np.asarray(nu, float) - c)))
    return c, half, half + margin


def dpss_basis(n, c, W, kmax):
    """(N, kmax) orthonormal complex basis exp(2j pi c n/N) * v_d[n]."""
    v = dpss(n, W, kmax, sym=True, norm=2).T  # (N, kmax) real
    return np.exp(2j * np.pi * c * np.arange(n) / n)[:, None] * v


def project_taps(delays, dopplers, gains, orders_list, n, *, margin=W_MARGIN):
    """For each D in orders_list: dict(taps (N,T), misfit).  Shared fields: delays, centroid, halfspread, W, tap_energy."""
    kmax = max(orders_list)
    ds, A, E_all, cs, hs, Ws = [], [], [], [], [], []
    for d, (nu, g) in sorted(orders.tap_groups(delays, dopplers, gains).items()):
        c, half, W = tap_band(nu, g, margin)
        ds.append(d)
        A.append(orders.tap_sequence(nu, g, n))
        E_all.append(dpss_basis(n, c, W, kmax))
        cs.append(c), hs.append(half), Ws.append(W)
    A = np.stack(A, 1)
    energy = np.sum(np.abs(A) ** 2, 0)
    out = dict(delays=np.array(ds, int), centroid=np.array(cs), halfspread=np.array(hs), W=np.array(Ws),
               tap_energy=energy, by_order={})
    coef = [E.conj().T @ A[:, i] for i, E in enumerate(E_all)]
    for D in orders_list:
        taps = np.stack([E_all[i][:, :D] @ coef[i][:D] for i in range(len(ds))], 1)
        resid = np.sum(np.abs(A - taps) ** 2, 0)
        out['by_order'][D] = dict(taps=taps, misfit=float(resid.sum() / energy.sum()),
                                  tap_misfit=(resid / energy).tolist())
    out['exact_taps'] = A
    return out


def dense_exp_fit(a, c, W, n, *, grid=0.25, count=None, ridge_rel=1e-10):
    """FALLBACK realization: dense in-band exponential set on a `grid`-bin lattice centred at c (count points if given, else
    all points in [c-W, c+W]); ridge LS gains.  Returns (nus, gains, rel_misfit_vs_a, max|gain|, cond(E^H E))."""
    if count is None:
        m = int(np.floor(W / grid + 1e-9))
        nus = c + grid * np.arange(-m, m + 1)
    else:
        nus = c + grid * (np.arange(count) - (count - 1) / 2.)
    k = np.arange(n)
    E = np.exp(2j * np.pi * np.outer(k, nus) / n)
    G = E.conj().T @ E
    gains = np.linalg.solve(G + ridge_rel * n * np.eye(len(nus)), E.conj().T @ a)
    resid = a - E @ gains
    return (nus, gains, float(np.vdot(resid, resid).real / np.vdot(a, a).real), float(np.abs(gains).max()),
            float(np.linalg.cond(G)))
