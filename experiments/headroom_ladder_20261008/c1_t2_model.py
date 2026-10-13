#!/usr/bin/env python
"""C1 T2 scalar feedback model (task 10-08-doppler-cluster; research/c1-scalar-closure.md, section "T2 model").

Inputs are NON-SP calibration only: T1 fixed-code AWGN curves (out/c1_t1/t1_transfer.json) and, for eta, the true-H (A3)
round-1 detector-output logloss per cell (out/c1_t0/t0_screen.json).  No SP outcome enters any prediction.

Physical units: a = 1 - rho, n = 10^(-SNR/10), channel energy 1, K = 8 L, N = 1024.
  q(e)      = eta a / (n + e)                                   proxy SINR at channel error e
  refit(v)  = K s / (1 + K s),  s = (n + a v) / ((rho + a (1 - v)) N)   v = normalised soft-symbol MSE in [0, 1]
  inner(e, q_pr): iterate e <- refit(M_unc(q(e) + q_pr)) to its fixed point.  Round 1: q_pr = 0 (code-free joint updates).
            Round >= 2: the detector carries the decoder check-extrinsic prior, Gaussian-approximation combining
            q_pr = M_unc^{-1}(v_ext) (amendment 2026-10-09, before any T0/T1 output: the original round>=2 rule discarded
            the decoder prior and erased the good fixed point in a synthetic unit test).
Read-out R1 (mean field): G(e_det) = inner(refit(M_app(q)), M_unc^{-1}(M_ext(q))), q = q(e_det); fixed points / stability /
  fold of G (Codex C3-C4).
Read-out R2 (two-branch): round r decodes with success prob 1 - FER_T1(q_r); success is absorbing; failure -> refit with
  v_app|wrong(q_r) and prior v_ext|wrong(q_r).  P_fail(R) = probability of no success within R rounds.
Endpoints kept separate: fold K (R1), first-pass-start bad branch K_flip (R1 from pilot-only start), FER .5 crossing of
P_fail(R=2) (R2).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
N = 1024
D_COEF = 8


class Curves:
    """Monotone interpolation of T1 curves in q_dB; clamped at the grid ends."""

    def __init__(self, q_db, **cols):
        order = np.argsort(q_db)
        self.q_db = np.asarray(q_db, float)[order]
        self.cols = {k: np.asarray(v, float)[order] for k, v in cols.items()}

    def __call__(self, name, q_lin):
        q_db = 10 * np.log10(np.maximum(q_lin, 1e-300))
        return np.interp(q_db, self.q_db, self.cols[name])

    def inverse(self, name, value):
        """q_lin with col(q) = value, for a monotone increasing column (e.g. J)."""
        y = self.cols[name]
        if np.any(np.diff(y) < -1e-9):
            y = np.maximum.accumulate(y)
        return 10 ** (np.interp(value, y, self.q_db) / 10)

    def inverse_decreasing(self, name, value):
        """q_lin with col(q) = value for a monotone decreasing column (soft-symbol MSE); 0 if value >= col at grid start."""
        y = np.minimum.accumulate(self.cols[name])
        if value >= y[0]:
            return 0.
        return 10 ** (np.interp(value, y[::-1], self.q_db[::-1]) / 10)


class ScalarMap:
    def __init__(self, curves_unc, curves_cod, rho, snr_db, K, eta, n_obs=N, use_inner=True):
        self.cu, self.cc = curves_unc, curves_cod
        self.rho, self.a, self.n = float(rho), 1. - float(rho), 10 ** (-float(snr_db) / 10)
        self.K, self.eta, self.N, self.use_inner = float(K), float(eta), int(n_obs), bool(use_inner)

    def q(self, e):
        return self.eta * self.a / (self.n + e)

    def refit(self, v):
        v = np.clip(v, 0., 1.)
        s = (self.n + self.a * v) / ((self.rho + self.a * (1. - v)) * self.N)
        return self.K * s / (1. + self.K * s)

    def q_prior(self, v_ext):
        """Equivalent AWGN SNR of a prior whose soft-symbol MSE is v_ext (inverse of decreasing M_unc)."""
        return float(self.cu.inverse_decreasing('M_unc', v_ext))

    def inner(self, e0, q_pr=0., tol=1e-13, itmax=5000):
        if not self.use_inner:
            return float(e0)
        e = float(e0)
        for _ in range(itmax):
            e_new = float(self.refit(self.cu('M_unc', self.q(e) + q_pr)))
            if abs(e_new - e) < tol:
                return e_new
            e = e_new
        return e

    def step(self, e_det, app='M_app', ext='M_ext'):
        q = self.q(e_det)
        return self.inner(self.refit(self.cc(app, q)), self.q_prior(self.cc(ext, q)))

    def G(self, e_det):
        return self.step(e_det)

    def pilot_only(self):
        e_ce1 = float(self.refit(1.))
        return e_ce1, self.inner(e_ce1)

    def fixed_points(self, n_grid=4000):
        """Roots of G(e) - e on a log grid between the perfect-feedback floor and the no-data bound."""
        lo = 0.5 * float(self.refit(0.))
        hi = float(self.refit(1.)) * 1.0001
        grid = np.geomspace(lo, hi, n_grid)
        h = np.array([self.G(e) - e for e in grid])
        out = []
        for i in np.nonzero(np.sign(h[:-1]) * np.sign(h[1:]) < 0)[0]:
            a, b = grid[i], grid[i + 1]
            for _ in range(80):  # bisection
                m = 0.5 * (a + b)
                if np.sign(self.G(m) - m) == np.sign(self.G(a) - a):
                    a = m
                else:
                    b = m
            e = 0.5 * (a + b)
            d = 1e-6 * e
            slope = (self.G(e + d) - self.G(e - d)) / (2 * d)
            out.append(dict(e=e, slope=float(slope), stable=bool(slope < 1)))
        return out

    def mean_field_run(self, rounds):
        e_ce, e_det = self.pilot_only()
        traj = [dict(r=1, e_ce=e_ce, e_det=e_det)]
        for r in range(2, rounds + 1):
            q = self.q(e_det)
            e_ce = float(self.refit(self.cc('M_app', q)))
            e_det = self.inner(e_ce, self.q_prior(self.cc('M_ext', q)))
            traj.append(dict(r=r, e_ce=e_ce, e_det=e_det))
        return traj

    def two_branch(self, rounds):
        """P(no successful decode within `rounds`), following the failure branch deterministically."""
        e_ce, e_det = self.pilot_only()
        p_fail, path = 1., []
        for r in range(1, rounds + 1):
            q = self.q(e_det)
            fer = float(np.clip(self.cc('FER', q), 0., 1.))
            p_fail *= fer
            path.append(dict(r=r, e_ce=e_ce, e_det=e_det, q_db=10 * np.log10(q), fer=fer))
            e_ce = float(self.refit(self.cc('v_app_wrong', q)))
            e_det = self.inner(e_ce, self.q_prior(self.cc('v_ext_wrong', q)))
        return p_fail, path


def load_curves(t1_path):
    """Adapter to the T1 json schema (filled in once T1 exists; see T1_TRANSFER.md)."""
    raise NotImplementedError('bind to out/c1_t1/t1_transfer.json schema')


def eta_rule(curves_unc, a3_r1_ll_in_mean, rho, snr_db):
    """Frozen rule: eta = J_unc^{-1}(1 - mean A3 r1_ll_in) / q_data, q_data = (1 - rho)/sigma2."""
    q_eq = curves_unc.inverse('J_unc', 1. - a3_r1_ll_in_mean)
    return float(q_eq / ((1. - rho) / 10 ** (-snr_db / 10)))


if __name__ == '__main__':
    sys.exit('library only until the T1 schema adapter is bound')
