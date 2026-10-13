"""F2 oracle representation ladder O_D (pure numpy; no frozen module imported).

Operator fact used (physical.Channel.apply and the CPP closure of supplement_g1):
a path (l, nu, g) acts as  z[k] = g * cp_l[k] * exp(2j*pi*k*nu/N) * t[(k-l) % N]  (t = IDAFT of x), i.e. the
DELAY-l tap only enters through its tap sequence  a_l[k] = sum_{rays r at l} g_r exp(2j*pi*nu_r*k/N), k=0..N-1,
and the operator is linear in a_l.  Rows of the time-domain operator have one entry per delay (unit-modulus cp
times a_l[k]) and DAFT is unitary, so
    ||H_true - H_alt||_F^2 = sum_l ||a_l - a_l'||_2^2 ,   ||H_true||_F^2 = sum_l ||a_l||_2^2 .
Oracle O_D keeps the true delays and replaces each tap by D exponentials on a 1-bin grid centred at the power-weighted
Doppler centroid, with least-squares gains over n = 0..N-1.  Spacing 1.0 bin makes the exponentials exactly orthogonal
over the frame (Gram = N*I), so the LS gain is the matched-filter coefficient.
"""
from __future__ import annotations

import numpy as np


def tap_groups(delays, dopplers, gains):
    """Return {delay: (nu_array, g_array)} preserving ray order inside each tap."""
    delays = np.asarray(delays, int)
    dopplers = np.asarray(dopplers, float)
    gains = np.asarray(gains, complex)
    return {int(d): (dopplers[delays == d], gains[delays == d]) for d in np.unique(delays)}


def tap_sequence(nu, g, n):
    k = np.arange(n)
    return np.exp(2j * np.pi * np.outer(k, np.asarray(nu, float)) / n) @ np.asarray(g, complex)


def centroid(nu, g):
    w = np.abs(np.asarray(g, complex)) ** 2
    return float(np.sum(w * np.asarray(nu, float)) / np.sum(w))


def subpath_grid(nu_bar, order, spacing=1.0):
    return nu_bar + (np.arange(order) - (order - 1) / 2.) * spacing


def lstsq_gains(a, nu_sub, n):
    """Least-squares gains of a[0..n-1] on exp(2j*pi*nu_sub*k/n); returns (gains, residual energy)."""
    k = np.arange(n)
    E = np.exp(2j * np.pi * np.outer(k, np.asarray(nu_sub, float)) / n)
    c = np.linalg.lstsq(E, a, rcond=None)[0]
    r = a - E @ c
    return c, float(np.vdot(r, r).real)


def oracle_paths(delays, dopplers, gains, order, n, *, spacing=1.0):
    """Oracle O_D: flat (l, nu, g) path list (same delay repeated D times) + relative operator misfit.

    misfit = sum_l ||a_l - fit_l||^2 / sum_l ||a_l||^2 = ||H_true - H_D||_F^2 / ||H_true||_F^2 (exact identity above).
    """
    if order < 1:
        raise ValueError('order must be >= 1')
    ls, nus, gs = [], [], []
    num = den = 0.
    for d, (nu, g) in sorted(tap_groups(delays, dopplers, gains).items()):
        a = tap_sequence(nu, g, n)
        grid = subpath_grid(centroid(nu, g), order, spacing)
        c, resid = lstsq_gains(a, grid, n)
        ls += [d] * order
        nus += list(grid)
        gs += list(c)
        num += resid
        den += float(np.vdot(a, a).real)
    return np.array(ls, int), np.array(nus, float), np.array(gs, complex), num / den


def misfit_with_nus(delays, dopplers, gains, nu_by_delay, n):
    """LS fit of every tap on an arbitrary given exponential set (identity / large-D checks)."""
    ls, nus, gs = [], [], []
    num = den = 0.
    for d, (nu, g) in sorted(tap_groups(delays, dopplers, gains).items()):
        a = tap_sequence(nu, g, n)
        c, resid = lstsq_gains(a, nu_by_delay[d], n)
        ls += [d] * len(c)
        nus += list(nu_by_delay[d])
        gs += list(c)
        num += resid
        den += float(np.vdot(a, a).real)
    return np.array(ls, int), np.array(nus, float), np.array(gs, complex), num / den
