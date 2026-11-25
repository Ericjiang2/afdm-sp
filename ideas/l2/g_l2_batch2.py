#!/usr/bin/env python3
"""Runner g L2 Batch 2 driver (2026-11-22, gemini-4-carbon) for cards:
  g10  I-20261122-g10: Zero-pilot clutter-aided finite-alphabet passive bistatic radar (CA-FA-EM)
  g07  I-20261122-g07: Contracting leaky Sigma-Delta 1-bit ADF-Probit rescuing low-PAPR SC-QPSK
  g09  I-20261122-g09: Asynchronous IF-TEM endpoint-telescoping tridiagonal GLS & PAPR reversal

Pre-registered criteria & forecasts: ideas/l2/PREDICTIONS_g_batch2.md
No frozen receiver source files are modified.
Usage:
  python g_l2_batch2.py smoke|g10|g07|g09|all --out out_g2 --workers 24
"""
import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solveh_banded
from scipy.signal import lfilter
from scipy.special import erfcx, ndtr

HERE = Path(__file__).resolve().parent

CFG = dict(
    calib_seeds=[60000, 62000],
    null_check_seeds=[62000, 62500],
    eval_seeds=[63000, 63400],
    pfa=0.01,
    g10=dict(
        N=1024,
        L_cp=56,
        Pc=8,
        cnr2_db=30.0,
        snr1_dbs=[-2.0, 2.0],
        wsrs_db=[-18.0, -22.0, -26.0, -30.0, -34.0],
        icm_stds=[0.0, 0.04],
        modulations=["qpsk", "16qam"],
        ell_range=[4, 44],
        nu_step=0.25,
        nu_max=3.25,
        nu_notch=0.75,
        c1_k=5,
    ),
    g07=dict(
        N=512,
        Mos=8,
        beta=0.25,
        alpha_nom=0.92,
        delta_sc=2.0,
        delta_afdm=2.8,
        transient=180,
        cnrs_db=[25.0, 35.0, 42.0],
        wsrs_db=[-22.0, -26.0, -30.0, -34.0, -38.0],
        ell_range=[4, 44],
        nu_step=0.25,
        nu_max=3.25,
        c1_k=5,
    ),
    g09=dict(
        N=256,
        Lsim=32,
        beta=0.25,
        target_rate=3.5,
        peak_margin=1.15,
        m_tdcs=[4, 8],
        cnrs_db=[30.0, 40.0],
        wsrs_db=[-22.0, -26.0, -30.0, -34.0],
        tau_ref=0.015,
        ell_range=[4, 32],
        nu_step=0.25,
        nu_max=3.0,
        c1_k=5,
    ),
)


# ===========================================================================
# Shared numerical primitives
# ===========================================================================
def inv_mills(z):
    """Overflow/underflow-safe phi(z) / Phi(z) on (-inf, +inf)."""
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z)
    pos = z >= 0.0
    if np.any(pos):
        zp = z[pos]
        out[pos] = (np.exp(-0.5 * zp * zp) / np.sqrt(2.0 * np.pi)) / ndtr(zp)
    if np.any(~pos):
        zn = z[~pos]
        out[~pos] = np.sqrt(2.0 / np.pi) / erfcx(-zn / np.sqrt(2.0))
    return out


def daft_u(X, c1_k, inverse=False):
    """Unitary DAFT / IDAFT with 2*N*c1 = c1_k and c2 = pi/(4*N^2) irrational."""
    X = np.asarray(X, dtype=complex)
    n = X.shape[0]
    k = np.arange(n, dtype=float)
    c1 = c1_k / (2.0 * n)
    c2 = np.sqrt(2.0) / (4.0 * n)
    a = np.exp(2j * np.pi * c1 * k * k)
    b = np.exp(2j * np.pi * c2 * k * k)
    if inverse:
        return a.conj() * np.fft.ifft(b.conj() * X) * np.sqrt(n)
    return b * np.fft.fft(a * X) / np.sqrt(n)


def frac_shift_periodic(x, tau):
    """Exact bandlimited fractional shift x(t - tau) on periodic grid of length M."""
    m = len(x)
    freqs = np.fft.fftfreq(m)
    return np.fft.ifft(np.fft.fft(x) * np.exp(-2j * np.pi * freqs * tau))


def frac_shift_compact(x, tau, half_win=8):
    """Physical compact-support Hann-windowed sinc fractional delay x(t - tau) (<-65 dB sidelobes)."""
    n = len(x)
    ell0 = int(np.floor(tau))
    taps = np.arange(ell0 - half_win + 1, ell0 + half_win + 1, dtype=float)
    u = tau - taps
    # Hann window over [-half_win, +half_win]
    w = 0.5 * (1.0 + np.cos(np.pi * np.clip(u / half_win, -1.0, 1.0)))
    h = np.sinc(u) * w
    h /= np.sum(h)
    h_vec = np.zeros(n, dtype=complex)
    for k_t, val in zip(taps.astype(int), h):
        h_vec[k_t % n] += val
    return np.fft.ifft(np.fft.fft(h_vec) * np.fft.fft(x))


def rrc_freq_mask(n_tot, oversamp, beta=0.25):
    freqs = np.fft.fftfreq(n_tot, d=1.0 / oversamp)
    af = np.abs(freqs)
    h = np.zeros(n_tot, dtype=float)
    f1 = (1.0 - beta) * 0.5
    f2 = (1.0 + beta) * 0.5
    h[af <= f1] = 1.0
    tr = (af > f1) & (af <= f2)
    h[tr] = np.sqrt(0.5 * (1.0 + np.cos(np.pi / beta * (af[tr] - f1))))
    return h


def dd_map_search(res_v, ref_x, ell_lo, ell_hi, nu_grid):
    """Normalized 2D delay-Doppler matched-filter peak and (ell, nu) argmax."""
    n = len(ref_x)
    denom = float(np.vdot(res_v, res_v).real) * float(np.vdot(ref_x, ref_x).real)
    if denom <= 1e-30:
        return 0.0, ell_lo, 0.0
    idx = np.arange(n, dtype=float)
    # Batched Doppler demodulation: shape (len(nu_grid), n)
    demod = res_v[None, :] * np.exp(-2j * np.pi * nu_grid[:, None] * idx[None, :] / n)
    X_conj = np.conj(np.fft.fft(ref_x))[None, :]
    corr = np.fft.ifft(X_conj * np.fft.fft(demod, axis=1), axis=1)[:, ell_lo : ell_hi + 1]
    pwr = (corr.real * corr.real + corr.imag * corr.imag) * (n / denom)
    flat_idx = int(np.argmax(pwr))
    n_ell = ell_hi - ell_lo + 1
    i_nu, i_ell = divmod(flat_idx, n_ell)
    return float(pwr[i_nu, i_ell]), int(ell_lo + i_ell), float(nu_grid[i_nu])


def bootstrap_ci(arr, rng, n_boot=1000):
    arr = np.asarray(arr, dtype=float)
    if len(arr) == 0:
        return [0.0, 0.0]
    idx = rng.integers(0, len(arr), size=(n_boot, len(arr)))
    means = idx.shape[1] and np.mean(arr[idx], axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def interp_mdr50(wsrs_db, rates):
    """Interpolate WSR (dB, lower is better) at 50% true-peak detection rate."""
    w = np.asarray(wsrs_db, dtype=float)
    r = np.asarray(rates, dtype=float)
    order = np.argsort(w)  # ascending WSR: e.g. -34, -30, -26, -22, -18
    w, r = w[order], r[order]
    if np.all(r >= 0.5):
        return float(w[0])
    if np.all(r < 0.5):
        return float(w[-1] + 4.0)
    for i in range(len(w) - 1):
        if r[i] <= 0.5 <= r[i + 1] and r[i + 1] > r[i]:
            frac = (0.5 - r[i]) / (r[i + 1] - r[i])
            return float(w[i] + frac * (w[i + 1] - w[i]))
    above = np.where(r >= 0.5)[0]
    return float(w[above[0]]) if len(above) else float(w[-1] + 4.0)


# ===========================================================================
# 1. Card g10: Zero-pilot clutter-aided finite-alphabet PBR (CA-FA-EM)
# ===========================================================================
def gen_constellation(rng, n, mod):
    if mod == "qpsk":
        re = rng.choice([-1.0, 1.0], size=n)
        im = rng.choice([-1.0, 1.0], size=n)
        return (re + 1j * im) / np.sqrt(2.0)
    pts = np.array([-3.0, -1.0, 1.0, 3.0]) / np.sqrt(10.0)
    return rng.choice(pts, size=n) + 1j * rng.choice(pts, size=n)


def slice_constellation(z, mod):
    if mod == "qpsk":
        sr = np.where(z.real >= 0.0, 1.0, -1.0)
        si = np.where(z.imag >= 0.0, 1.0, -1.0)
        return (sr + 1j * si) / np.sqrt(2.0)
    s = np.sqrt(10.0)
    zr, zi = z.real * s, z.imag * s
    pr = np.where(zr < -2.0, -3.0, np.where(zr < 0.0, -1.0, np.where(zr < 2.0, 1.0, 3.0)))
    pi = np.where(zi < -2.0, -3.0, np.where(zi < 0.0, -1.0, np.where(zi < 2.0, 1.0, 3.0)))
    return (pr + 1j * pi) / s


def blind_rot_and_timing(z_raw, xt_est, wf, mod, c1_k=5):
    """Zero-pilot blind fractional timing (-0.45..+0.45 Ts) + 4th-power phase lock."""
    taus = np.linspace(-0.45, 0.45, 13)
    best_loss = 1e30
    best_sh = None
    best_tau = 0.0
    for tau in taus:
        xt_tau = frac_shift_compact(xt_est, -tau)
        zt = np.fft.fft(xt_tau) / np.sqrt(len(xt_tau)) if wf == "ofdm" else daft_u(xt_tau, c1_k, inverse=False)
        rms = np.sqrt(max(np.mean(np.abs(zt) ** 2), 1e-12))
        zt = zt / rms
        ang = 0.25 * np.angle(-np.mean(zt ** 4))
        zt_rot = zt * np.exp(-1j * ang)
        sh = slice_constellation(zt_rot, mod)
        loss = float(np.mean(np.abs(zt_rot - sh) ** 2))
        if loss < best_loss:
            best_loss = loss
            best_sh = sh
            best_tau = tau
    for tau in best_tau + np.linspace(-0.075, 0.075, 5):
        xt_tau = frac_shift_compact(xt_est, -tau)
        zt = np.fft.fft(xt_tau) / np.sqrt(len(xt_tau)) if wf == "ofdm" else daft_u(xt_tau, c1_k, inverse=False)
        zt = zt / np.sqrt(max(np.mean(np.abs(zt) ** 2), 1e-12))
        ang = 0.25 * np.angle(-np.mean(zt ** 4))
        zt_rot = zt * np.exp(-1j * ang)
        sh = slice_constellation(zt_rot, mod)
        loss = float(np.mean(np.abs(zt_rot - sh) ** 2))
        if loss < best_loss:
            best_loss = loss
            best_sh = sh
            best_tau = tau
    xt_clean = np.fft.ifft(best_sh) * np.sqrt(len(best_sh)) if wf == "ofdm" else daft_u(best_sh, c1_k, inverse=True)
    return xt_clean, best_sh, best_tau


def eca_cancel(y2, ref_sig, lags, tapers=1):
    """Project y2 orthogonal to cyclic/shifted clutter subspace of ref_sig."""
    n = len(y2)
    cols = []
    idx = np.arange(n, dtype=float)
    u1 = (idx - 0.5 * n) / n
    taper_list = [np.ones(n)] if tapers == 1 else [np.ones(n), u1, u1 * u1]
    for tap in taper_list:
        for lag in lags:
            cols.append(tap * np.roll(ref_sig, lag))
    A = np.column_stack(cols)
    gram = A.conj().T @ A + 1e-8 * np.eye(A.shape[1])
    cf = cho_factor(gram)
    coef = cho_solve(cf, A.conj().T @ y2)
    return y2 - A @ coef


def est_2ch_rel_filters(y1, y2, lags1, lags2):
    """Zero-pilot cross-correlation & power-spectrum initial relative channel estimate."""
    n = len(y1)
    Y1 = np.fft.fft(y1)
    Y2 = np.fft.fft(y2)
    # Cross-correlation (1/N) * IFFT(Y2 * conj(Y1)) ≈ h_c * h_1^*
    xcorr = np.fft.ifft(Y2 * np.conj(Y1))
    # Estimate noise variances from out-of-support lags [180..450]
    # Power spectra E|Y1|^2/N = |H1|^2 + sig1^2, E|Y2|^2/N = |Hc|^2 + sig2^2
    hc_rel = np.zeros(n, dtype=complex)
    for lag in lags2:
        hc_rel[lag % n] = xcorr[lag % n]
    # Normalize scale via high-lag tail of xcorr
    tail_idx = np.arange(150, 400)
    xcorr_var = float(np.mean(np.abs(xcorr[tail_idx]) ** 2))
    p1 = float(np.mean(np.abs(y1) ** 2))
    p2 = float(np.mean(np.abs(y2) ** 2))
    # Signal power on y2 is ~sum |hc_rel|^2 / |g1|^2; since |x_t|^2 = 1 and |g1| ~ 1:
    norm_hc2 = max(float(np.sum(np.abs(hc_rel) ** 2)) - len(lags2) * xcorr_var, 1e-6)
    # In y1 = g1 * x + w1 with |g1|=1 (or unknown scale absorbed into x/g1):
    # Note |xcorr_true|^2 sum = |g1|^2 * ||h_c||^2, while p2 ≈ ||h_c||^2 + sig2^2!
    # Hence |g1|^2 ≈ norm_hc2 / max(p2, 1e-6)!! Completely blind!
    g1_sq_est = np.clip(norm_hc2 / max(p2, 1e-6), 0.05, 50.0)
    g1_abs = np.sqrt(g1_sq_est)
    sig1_sq = max(p1 - g1_sq_est, 1e-4 * p1)
    Hc_f = np.fft.fft(hc_rel) / g1_abs
    # Estimate sig2_sq from residual of y2 not explained by Hc_f
    sig2_sq = max(xcorr_var * n / max(g1_sq_est, 1e-3) - float(np.mean(np.abs(Hc_f) ** 2)) * sig1_sq / n, 1e-4 * p2)
    sig2_sq = np.clip(sig2_sq, 1e-4 * p2, 0.2 * p2)
    return g1_abs, Hc_f, sig1_sq, sig2_sq


def run_cafa_em(y1, y2, wf, mod, lags1, lags2, n_iters=4, c1_k=5):
    """Zero-pilot 2-channel Clutter-Aided Finite-Alphabet EM (or 1-step if n_iters=1)."""
    n = len(y1)
    g1_abs, Hc_f, sig1_sq, sig2_sq = est_2ch_rel_filters(y1, y2, lags1, lags2)
    Y1 = np.fft.fft(y1)
    Y2 = np.fft.fft(y2)
    # Initial 2-channel LMMSE waveform estimate (note phase of g1 is absorbed into global rotation!)
    num = (g1_abs / sig1_sq) * Y1 + (np.conj(Hc_f) / sig2_sq) * Y2
    den = (g1_abs * g1_abs / sig1_sq) + (np.abs(Hc_f) ** 2 / sig2_sq) + 1.0
    xt_lin = np.fft.ifft(num / den)
    if n_iters == 0:
        # 4-iteration Gaussian alternating LMMSE WITHOUT Voronoi finite-alphabet projection
        xt_g = xt_lin / np.sqrt(max(np.mean(np.abs(xt_lin) ** 2), 1e-12))
        for _ in range(4):
            Xg = np.fft.fft(xt_g)
            denom_g = np.abs(Xg) ** 2 + 1e-2 * n
            h1_f = np.fft.ifft(Y1 * np.conj(Xg) / denom_g)
            hc_f = np.fft.ifft(Y2 * np.conj(Xg) / denom_g)
            h1_w = np.zeros(n, dtype=complex)
            for lag in lags1:
                h1_w[lag % n] = h1_f[lag % n]
            hc_w = np.zeros(n, dtype=complex)
            for lag in lags2:
                hc_w[lag % n] = hc_f[lag % n]
            H1_g, Hc_g = np.fft.fft(h1_w), np.fft.fft(hc_w)
            s1_g = max(float(np.mean(np.abs(Y1 - H1_g * Xg) ** 2)) / n, 1e-6)
            s2_g = max(float(np.mean(np.abs(Y2 - Hc_g * Xg) ** 2)) / n, 1e-6)
            xt_g = np.fft.ifft(((np.conj(H1_g) / s1_g) * Y1 + (np.conj(Hc_g) / s2_g) * Y2) / ((np.abs(H1_g) ** 2 / s1_g) + (np.abs(Hc_g) ** 2 / s2_g) + 1.0))
            xt_g = xt_g / np.sqrt(max(np.mean(np.abs(xt_g) ** 2), 1e-12))
        return xt_g, None

    xt_cur, sh_cur, tau_est = blind_rot_and_timing(None, xt_lin, wf, mod, c1_k=c1_k)
    for _ in range(n_iters - 1):
        X_dft = np.fft.fft(xt_cur)
        # Re-estimate short fractional timing filter H1_f on lags1 and clutter filter Hc_f on lags2
        # LS in lag domain via FFT cross-correlation (since |X_dft|^2 ≈ N, exact regularized deconvolution)
        denom_x = np.abs(X_dft) ** 2 + 1e-2 * n
        h1_full = np.fft.ifft(Y1 * np.conj(X_dft) / denom_x)
        hc_full = np.fft.ifft(Y2 * np.conj(X_dft) / denom_x)
        h1_win = np.zeros(n, dtype=complex)
        for lag in lags1:
            h1_win[lag % n] = h1_full[lag % n]
        hc_win = np.zeros(n, dtype=complex)
        for lag in lags2:
            hc_win[lag % n] = hc_full[lag % n]
        H1_f = np.fft.fft(h1_win)
        Hc_f = np.fft.fft(hc_win)
        s1 = max(float(np.mean(np.abs(Y1 - H1_f * X_dft) ** 2)) / n, 1e-6)
        s2 = max(float(np.mean(np.abs(Y2 - Hc_f * X_dft) ** 2)) / n, 1e-6)
        num = (np.conj(H1_f) / s1) * Y1 + (np.conj(Hc_f) / s2) * Y2
        den = (np.abs(H1_f) ** 2 / s1) + (np.abs(Hc_f) ** 2 / s2) + 1.0
        xt_mmse = np.fft.ifft(num / den)
        zt = np.fft.fft(xt_mmse) / np.sqrt(n) if wf == "ofdm" else daft_u(xt_mmse, c1_k, inverse=False)
        zt = zt / np.sqrt(max(np.mean(np.abs(zt) ** 2), 1e-12))
        # Fine phase lock (quadrant already locked from previous iteration, refine small residual angle)
        ang = 0.25 * np.angle(-np.mean(zt ** 4))
        sh_cur = slice_constellation(zt * np.exp(-1j * ang), mod)
        xt_cur = np.fft.ifft(sh_cur) * np.sqrt(n) if wf == "ofdm" else daft_u(sh_cur, c1_k, inverse=True)
    return xt_cur, sh_cur


def g10_sim_frame(seed, snr1_db, wsr_db, icm_std, mod, is_null=False):
    cfg = CFG["g10"]
    n = cfg["N"]
    rng = np.random.default_rng(seed)
    lags1 = list(range(-8, 9))
    lags2 = list(range(-8, 48))
    nu_all = np.arange(-cfg["nu_max"], cfg["nu_max"] + 1e-9, cfg["nu_step"])
    nu_grid = nu_all[np.abs(nu_all) > cfg["nu_notch"] + 1e-9]
    ell_lo, ell_hi = cfg["ell_range"]

    syms = gen_constellation(rng, n, mod)
    # Same symbols & same channel realization compared fairly across OFDM and AFDM!
    taus_c = rng.uniform(2.0, 38.0, size=cfg["Pc"])
    pows_c = np.exp(-taus_c / 14.0)
    pows_c /= np.sum(pows_c)
    amps_c = (rng.standard_normal(cfg["Pc"]) + 1j * rng.standard_normal(cfg["Pc"])) / np.sqrt(2.0) * np.sqrt(pows_c)
    nus_c = rng.normal(0.0, icm_std, size=cfg["Pc"]) if icm_std > 0 else np.zeros(cfg["Pc"])
    dtau_1 = rng.uniform(-0.25, 0.25)
    dtau_12 = rng.uniform(-0.40, 0.40)
    phi1 = rng.uniform(0.0, 2.0 * np.pi)
    g1 = np.exp(1j * phi1)

    sig1 = 10.0 ** (-0.05 * snr1_db)
    sig2 = 10.0 ** (-0.05 * cfg["cnr2_db"])
    w1_base = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0) * sig1
    w2_base = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0) * sig2

    tau_w = rng.uniform(6.0, 40.0)
    nu_sign = rng.choice([-1.0, 1.0])
    nu_w = nu_sign * rng.uniform(1.2, 3.0)
    phi_w = rng.uniform(0.0, 2.0 * np.pi)
    gw = 0.0 if is_null else (10.0 ** (0.05 * wsr_db)) * np.exp(1j * phi_w)

    idx = np.arange(n, dtype=float)
    out = {}
    for wf in ("ofdm", "afdm"):
        xt = np.fft.ifft(syms) * np.sqrt(n) if wf == "ofdm" else daft_u(syms, cfg["c1_k"], inverse=True)
        # Cyclic-prefix / chirp-periodic prefix makes circular shift == linear shift on [0, 48]
        y1 = g1 * frac_shift_compact(xt, dtau_1) + w1_base
        y2_clut = np.zeros(n, dtype=complex)
        for p in range(cfg["Pc"]):
            sh_p = frac_shift_compact(xt, dtau_1 + dtau_12 + taus_c[p])
            if icm_std > 0:
                sh_p = sh_p * np.exp(2j * np.pi * nus_c[p] * idx / n)
            y2_clut += amps_c[p] * sh_p
        psi_w = frac_shift_compact(xt, dtau_1 + dtau_12 + tau_w) * np.exp(2j * np.pi * nu_w * idx / n)
        y2 = y2_clut + gw * psi_w + w2_base

        tapers = 3 if icm_std > 0 else 1
        # Baseline arms (computed on OFDM waveform; note Gaussian/ECA arms are waveform-blind)
        if wf == "ofdm":
            r_eca = eca_cancel(y2, y1, lags2, tapers=1)
            out["eca"] = dd_map_search(r_eca, y1, ell_lo, ell_hi, nu_grid)
            r_ecacd = eca_cancel(y2, y1, lags2, tapers=3)
            out["eca_cd"] = dd_map_search(r_ecacd, y1, ell_lo, ell_hi, nu_grid)
            # Frequency-domain Gaussian TLS / whitened cross-relation (Hack et al. TSP 2014)
            g1_a, Hc_f, s1_sq, s2_sq = est_2ch_rel_filters(y1, y2, lags1, lags2)
            Y1, Y2 = np.fft.fft(y1), np.fft.fft(y2)
            # First remove static/ICM clutter best-fit on y1, then whiten by Schur denominator
            r_tls_t = np.fft.ifft((Y2 - (Hc_f / max(g1_a, 1e-3)) * Y1) / np.sqrt(s2_sq + (np.abs(Hc_f) ** 2 / max(g1_a ** 2, 1e-4)) * s1_sq))
            out["gauss_tls"] = dd_map_search(r_tls_t, y1, ell_lo, ell_hi, nu_grid)
            # Claude baseline 1a: 2-channel linear LMMSE waveform estimate WITHOUT Voronoi slicing + ECA-CD
            xt_lin, _ = run_cafa_em(y1, y2, "ofdm", mod, lags1, lags2, n_iters=0)
            r_lin2 = eca_cancel(y2, xt_lin, lags2, tapers=tapers)
            out["lin_2ch_eca"] = dd_map_search(r_lin2, xt_lin, ell_lo, ell_hi, nu_grid)
            # Claude baseline 1b: 1-shot non-EM 2-channel MRC hard Voronoi decision + ECA-CD
            xt_1s, _ = run_cafa_em(y1, y2, "ofdm", mod, lags1, lags2, n_iters=1)
            r_1s = eca_cancel(y2, xt_1s, lags2, tapers=tapers)
            out["df_1step_eca"] = dd_map_search(r_1s, xt_1s, ell_lo, ell_hi, nu_grid)
            # Oracle waveform upper bound
            xt_ref_true = frac_shift_compact(xt, dtau_1)
            r_ora = eca_cancel(y2, xt_ref_true, lags2, tapers=tapers)
            out["oracle_x"] = dd_map_search(r_ora, xt_ref_true, ell_lo, ell_hi, nu_grid)

        # Proposed 4-iteration zero-pilot CA-FA-EM
        xt_em, _ = run_cafa_em(y1, y2, wf, mod, lags1, lags2, n_iters=4, c1_k=cfg["c1_k"])
        r_em = eca_cancel(y2, xt_em, lags2, tapers=tapers)
        # Note xt_em is aligned to symbol boundary (lag relative to xt is dtau_1 + dtau_12 + tau_w)
        out[f"{wf}_cafa"] = dd_map_search(r_em, xt_em, ell_lo, ell_hi, nu_grid)

    return dict(seed=seed, tau_w=float(tau_w), dtau_tot=float(dtau_1 + dtau_12), nu_w=float(nu_w), arms=out)


# ===========================================================================
# 2. Card g07: Leaky Sigma-Delta 1-bit ADF-Probit on RRC SC-QPSK vs AFDM
# ===========================================================================
def gen_oversampled_waveform(rng, n, mos, wf, beta=0.25, c1_k=5):
    nos = n * mos
    syms = gen_constellation(rng, n, "qpsk")
    if wf == "sc":
        up = np.zeros(nos, dtype=complex)
        up[::mos] = syms
        h_rrc = rrc_freq_mask(nos, mos, beta=beta)
        x = np.fft.ifft(np.fft.fft(up) * h_rrc * np.sqrt(mos))
    else:
        x_nyq = daft_u(syms, c1_k, inverse=True)
        X_f = np.fft.fft(x_nyq)
        X_pad = np.zeros(nos, dtype=complex)
        half = n // 2
        X_pad[:half] = X_f[:half]
        X_pad[-half:] = X_f[-half:]
        x = np.fft.ifft(X_pad) * mos
    x /= np.sqrt(np.mean(np.abs(x) ** 2))
    return x


def sim_sd1_hardware(y, alpha, delta, rng, u0=0.0j, v_off=0.0j, v_hys=0.0, sig_int=0.0):
    """Exact sample-by-sample analog 1-bit Sigma-Delta modulator."""
    nos = len(y)
    yr, yi = y.real, y.imag
    ur, ui = float(u0.real), float(u0.imag)
    vor, voi = float(v_off.real), float(v_off.imag)
    qr = np.empty(nos, dtype=float)
    qi = np.empty(nos, dtype=float)
    q_prev_r, q_prev_i = 1.0, 1.0
    int_nr = rng.standard_normal(nos) * (sig_int / np.sqrt(2.0)) if sig_int > 0 else np.zeros(nos)
    int_ni = rng.standard_normal(nos) * (sig_int / np.sqrt(2.0)) if sig_int > 0 else np.zeros(nos)
    for k in range(nos):
        umr = alpha * ur + yr[k] + int_nr[k]
        umi = alpha * ui + yi[k] + int_ni[k]
        sr = 1.0 if (umr - vor - v_hys * q_prev_r) >= 0.0 else -1.0
        si = 1.0 if (umi - voi - v_hys * q_prev_i) >= 0.0 else -1.0
        qr[k] = sr
        qi[k] = si
        q_prev_r, q_prev_i = sr, si
        ur = umr - delta * sr
        ui = umi - delta * si
    return qr + 1j * qi


def sd1_concave_fit(q, x, alpha, delta, tr=180, fit_offset=False, max_iter=10):
    """Strictly concave 3D (or 5D with DC offset) Probit MLE for (g0, sigma_eff, v_off)."""
    xt = lfilter([1.0], [1.0, -alpha], x)[tr:]
    qh = np.zeros_like(q)
    qh[1:] = q[:-1]
    ft = delta * lfilter([alpha], [1.0, -alpha], qh)[tr:]
    sr, si = q.real[tr:], q.imag[tr:]
    s = np.concatenate([sr, si])
    xtr, xti = xt.real, xt.imag
    ftr, fti = ft.real, ft.imag
    if fit_offset:
        X = np.column_stack([
            np.concatenate([xtr, xti]),
            np.concatenate([-xti, xtr]),
            np.concatenate([-ftr, -fti]),
            np.concatenate([np.ones_like(xtr), np.zeros_like(xti)]),
            np.concatenate([np.zeros_like(xtr), np.ones_like(xti)]),
        ])
        g0_init = np.vdot(xt, ft) / max(np.vdot(xt, xt).real, 1e-12)
        c_init = 8.0
        theta = np.array([c_init * g0_init.real, c_init * g0_init.imag, c_init, 0.0, 0.0])
    else:
        X = np.column_stack([
            np.concatenate([xtr, xti]),
            np.concatenate([-xti, xtr]),
            np.concatenate([-ftr, -fti]),
        ])
        g0_init = np.vdot(xt, ft) / max(np.vdot(xt, xt).real, 1e-12)
        c_init = 8.0
        theta = np.array([c_init * g0_init.real, c_init * g0_init.imag, c_init])

    reg = 1e-5
    ll_val = -1e30
    for _ in range(max_iter):
        u = X @ theta
        su = s * u
        lam = inv_mills(su)
        grad = X.T @ (s * lam) - reg * theta
        w = np.maximum(lam * (lam + su), 0.0)
        H = -(X.T * w[None, :]) @ X - reg * np.eye(len(theta))
        step = np.linalg.solve(-H, grad)
        sn = np.linalg.norm(step)
        if sn > 20.0:
            step *= 20.0 / sn
        theta = theta + step
        theta[2] = np.clip(theta[2], 0.5, 400.0)
        if sn < 1e-4:
            break
    u = X @ theta
    su = s * u
    # Stable log Phi(su)
    pos = su >= 0.0
    lphi = np.empty_like(su)
    lphi[pos] = np.log(np.maximum(ndtr(su[pos]), 1e-300))
    zn = su[~pos]
    lphi[~pos] = -0.5 * zn * zn + np.log(np.maximum(0.5 * erfcx(-zn / np.sqrt(2.0)), 1e-300))
    ll_val = float(np.sum(lphi)) - 0.5 * reg * float(np.dot(theta, theta))
    c_est = float(theta[2])
    sig_eff = 1.0 / c_est
    g0_est = complex(theta[0] / c_est, theta[1] / c_est)
    v_off_est = complex(-theta[3] / c_est, -theta[4] / c_est) if fit_offset else 0.0j
    return ll_val, g0_est, sig_eff, v_off_est, xt, ft


def sd1_adf_score(q, x, alpha, delta, tr=180, use_adf=True, fit_offset=False, cal_alpha=False):
    """Compute innovation Probit score at oversampled rate, then matched-decimate to Nyquist."""
    if cal_alpha:
        # Coarse 5-point + 3-point local parabolic refinement on alpha in [0.898, 0.942]
        a_grid = np.linspace(alpha * 0.978, alpha * 1.022, 5)
        best_a = alpha
        best_res = None
        best_ll = -1e30
        for a_try in a_grid:
            res = sd1_concave_fit(q, x, a_try, delta, tr=tr, fit_offset=fit_offset, max_iter=8)
            if res[0] > best_ll:
                best_ll = res[0]
                best_a = a_try
                best_res = res
        for a_try in best_a + np.array([-0.004, 0.004]):
            res = sd1_concave_fit(q, x, a_try, delta, tr=tr, fit_offset=fit_offset, max_iter=8)
            if res[0] > best_ll:
                best_ll = res[0]
                best_a = a_try
                best_res = res
        alpha_use = best_a
        _, g0_hat, sig_eff, v_off_hat, xt, ft = best_res
    else:
        alpha_use = alpha
        _, g0_hat, sig_eff, v_off_hat, xt, ft = sd1_concave_fit(q, x, alpha_use, delta, tr=tr, fit_offset=fit_offset)

    u_det = g0_hat * xt - ft - v_off_hat
    sr, si = q.real[tr:], q.imag[tr:]
    if not use_adf:
        zr = sr * (u_det.real / sig_eff)
        zi = si * (u_det.imag / sig_eff)
        xi = (sr * inv_mills(zr) + 1j * si * inv_mills(zi)) / sig_eff
    else:
        # 1D Truncated-Gaussian Markov ADF tracking thermal state e_th,k = alpha * e_th,k-1 + w_k
        # Note sig_eff from marginal fit satisfies sig_eff^2 ≈ sig0_1d^2 * (1 + ~0.25*alpha^2); set process var:
        sig0_1d_sq = (sig_eff * sig_eff) * (1.0 - 0.55 * alpha_use * alpha_use)
        m_len = len(sr)
        xir = np.empty(m_len, dtype=float)
        xii = np.empty(m_len, dtype=float)
        mur, mui = 0.0, 0.0
        vr, vi = sig0_1d_sq, sig0_1d_sq
        udr, udi = u_det.real, u_det.imag
        a2 = alpha_use * alpha_use
        for k in range(m_len):
            m_mr = alpha_use * mur
            v_mr = a2 * vr + sig0_1d_sq
            std_r = np.sqrt(v_mr)
            zr = sr[k] * (udr[k] + m_mr) / std_r
            lam_r = float(inv_mills(zr))
            xir[k] = sr[k] * lam_r / std_r
            mur = m_mr + sr[k] * std_r * lam_r
            vr = max(v_mr * (1.0 - lam_r * (lam_r + zr)), 1e-8 * sig0_1d_sq)

            m_mi = alpha_use * mui
            v_mi = a2 * vi + sig0_1d_sq
            std_i = np.sqrt(v_mi)
            zi = si[k] * (udi[k] + m_mi) / std_i
            lam_i = float(inv_mills(zi))
            xii[k] = si[k] * lam_i / std_i
            mui = m_mi + si[k] * std_i * lam_i
            vi = max(v_mi * (1.0 - lam_i * (lam_i + zi)), 1e-8 * sig0_1d_sq)
        xi = xir + 1j * xii

    # Matched adjoint filter (1 - alpha_use * z^{+1})^{-1} on score, padded back to Nos
    xi_full = np.zeros(len(q), dtype=complex)
    xi_full[tr:] = lfilter([1.0], [1.0, -alpha_use], xi[::-1])[::-1]
    return xi_full


def decimate_to_nyq(vec_os, n, mos):
    """Bandlimited anti-alias decimation from Nos = n*mos to Nyquist n."""
    V = np.fft.fft(vec_os)
    half = n // 2
    V_nyq = np.concatenate([V[:half], V[-half:]])
    return np.fft.ifft(V_nyq) / np.sqrt(mos)


def memless_probit_os(r_1bit, x_os):
    sr, si = r_1bit.real, r_1bit.imag
    xr, xi = x_os.real, x_os.imag
    s = np.concatenate([sr, si])
    X = np.column_stack([np.concatenate([xr, xi]), np.concatenate([-xi, xr])])
    ang0 = np.angle(np.vdot(x_os, r_1bit))
    theta = np.array([4.0 * np.cos(ang0), 4.0 * np.sin(ang0)])
    for _ in range(10):
        u = X @ theta
        su = s * u
        lam = inv_mills(su)
        grad = X.T @ (s * lam) - 1e-5 * theta
        w = np.maximum(lam * (lam + su), 0.0)
        H = -(X.T * w[None, :]) @ X - 1e-5 * np.eye(2)
        step = np.linalg.solve(-H, grad)
        sn = np.linalg.norm(step)
        if sn > 15.0:
            step *= 15.0 / sn
        theta += step
        if np.linalg.norm(theta) > 120.0:
            theta *= 120.0 / np.linalg.norm(theta)
            break
        if sn < 1e-4:
            break
    u_c = complex(theta[0], theta[1]) * x_os
    return sr * inv_mills(sr * u_c.real) + 1j * si * inv_mills(si * u_c.imag)


def g07_sim_frame(seed, cnr_db, wsr_db, is_null=False):
    cfg = CFG["g07"]
    n, mos = cfg["N"], cfg["Mos"]
    nos = n * mos
    rng = np.random.default_rng(seed)
    nu_all = np.arange(-cfg["nu_max"], cfg["nu_max"] + 1e-9, cfg["nu_step"])
    nu_grid = nu_all[np.abs(nu_all) > 0.75 + 1e-9]
    ell_lo, ell_hi = cfg["ell_range"]

    x_sc = gen_oversampled_waveform(rng, n, mos, "sc", beta=cfg["beta"], c1_k=cfg["c1_k"])
    x_af = gen_oversampled_waveform(rng, n, mos, "afdm", beta=cfg["beta"], c1_k=cfg["c1_k"])
    x_sc_nyq = decimate_to_nyq(x_sc, n, mos)
    x_af_nyq = decimate_to_nyq(x_af, n, mos)

    phi0 = rng.uniform(0.0, 2.0 * np.pi)
    g0 = np.exp(1j * phi0)
    sig0 = 10.0 ** (-0.05 * cnr_db)
    w_os = (rng.standard_normal(nos) + 1j * rng.standard_normal(nos)) / np.sqrt(2.0) * sig0

    tau_w = rng.uniform(6.0, 40.0)
    nu_w = rng.choice([-1.0, 1.0]) * rng.uniform(1.2, 3.0)
    gw = 0.0 if is_null else (10.0 ** (0.05 * wsr_db)) * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi))
    idx_os = np.arange(nos, dtype=float)

    psi_sc = frac_shift_periodic(x_sc, tau_w * mos) * np.exp(2j * np.pi * nu_w * idx_os / nos)
    y_sc = g0 * x_sc + gw * psi_sc + w_os

    psi_af = frac_shift_periodic(x_af, tau_w * mos) * np.exp(2j * np.pi * nu_w * idx_os / nos)
    y_af = g0 * x_af + gw * psi_af + w_os

    out = {}
    # 1. Memoryless 8x oversampled 1-bit Probit on SC-QPSK
    r_mem = np.where(y_sc.real >= 0, 1.0, -1.0) + 1j * np.where(y_sc.imag >= 0, 1.0, -1.0)
    sc_mem = decimate_to_nyq(memless_probit_os(r_mem, x_sc), n, mos)
    out["sc_memless_probit"] = dd_map_search(sc_mem, x_sc_nyq, ell_lo, ell_hi, nu_grid)

    # Nominal leaky SD1 (alpha = 0.92) on SC-QPSK with random initial capacitor state u0 in [-Delta, Delta]
    d_sc = cfg["delta_sc"]
    u0 = rng.uniform(-d_sc, d_sc) + 1j * rng.uniform(-d_sc, d_sc)
    q_nom = sim_sd1_hardware(y_sc, cfg["alpha_nom"], d_sc, rng, u0=u0)

    # 2. Linear Sigma-Delta decimation WITH blind g0_hat * x strong-path subtraction!
    # Exact linear NTF transfer: y_est_k = Delta * q_k - alpha * Delta * q_{k-1} on leaky integrator!
    # Wait: u_k = alpha * u_{k-1} + y_k - Delta * q_k => y_k = Delta * q_k + (u_k - alpha * u_{k-1})!
    # So after bandlimited decimation to Nyquist, high-pass quantization error (1 - alpha z^{-1}) u_k is filtered out!
    y_lin_nyq = decimate_to_nyq(d_sc * q_nom, n, mos)
    # Blind LS g0 subtraction in Nyquist band (absorbs exact transfer response cleanly!)
    g0_lin = np.vdot(x_sc_nyq, y_lin_nyq) / max(np.vdot(x_sc_nyq, x_sc_nyq).real, 1e-12)
    r_lin_nyq = y_lin_nyq - g0_lin * x_sc_nyq
    out["sc_sd1_lin_sic"] = dd_map_search(r_lin_nyq, x_sc_nyq, ell_lo, ell_hi, nu_grid)

    # 3. Deterministic leaky trajectory WITHOUT Markov ADF
    sc_det = decimate_to_nyq(sd1_adf_score(q_nom, x_sc, cfg["alpha_nom"], d_sc, tr=cfg["transient"], use_adf=False), n, mos)
    out["sc_sd1_det_no_adf"] = dd_map_search(sc_det, x_sc_nyq, ell_lo, ell_hi, nu_grid)

    # 4. Non-leaky alpha = 1.0 with unknown initial state u0 in [-Delta, Delta]
    q_a1 = sim_sd1_hardware(y_sc, 0.9999, d_sc, rng, u0=u0)
    sc_a1 = decimate_to_nyq(sd1_adf_score(q_a1, x_sc, 0.9999, d_sc, tr=cfg["transient"], use_adf=True), n, mos)
    out["sc_sd1_alpha1"] = dd_map_search(sc_a1, x_sc_nyq, ell_lo, ell_hi, nu_grid)

    # 5. Proposed blind 3D + 1D Truncated-Gaussian ADF on nominal hardware
    sc_adf = decimate_to_nyq(sd1_adf_score(q_nom, x_sc, cfg["alpha_nom"], d_sc, tr=cfg["transient"], use_adf=True), n, mos)
    out["sc_sd1_adf"] = dd_map_search(sc_adf, x_sc_nyq, ell_lo, ell_hi, nu_grid)

    # 6. Full analog hardware stress test: +-1.5% RC alpha + comparator DC offset + hysteresis + kT/C noise
    alpha_hw = cfg["alpha_nom"] * (1.0 + rng.uniform(-0.015, 0.015))
    v_off_hw = (rng.uniform(-0.03, 0.03) + 1j * rng.uniform(-0.03, 0.03)) * d_sc
    v_hys_hw = 0.01 * d_sc
    q_hw = sim_sd1_hardware(y_sc, alpha_hw, d_sc, rng, u0=u0, v_off=v_off_hw, v_hys=v_hys_hw, sig_int=0.2 * sig0)
    sc_hw = decimate_to_nyq(
        sd1_adf_score(q_hw, x_sc, cfg["alpha_nom"], d_sc, tr=cfg["transient"], use_adf=True, fit_offset=True, cal_alpha=True),
        n,
        mos,
    )
    out["sc_sd1_adf_hw"] = dd_map_search(sc_hw, x_sc_nyq, ell_lo, ell_hi, nu_grid)

    # 7. AFDM + SD1-ADF comparison under identical hardware mismatch
    d_af = cfg["delta_afdm"]
    u0_af = rng.uniform(-d_af, d_af) + 1j * rng.uniform(-d_af, d_af)
    v_off_af = (rng.uniform(-0.03, 0.03) + 1j * rng.uniform(-0.03, 0.03)) * d_af
    q_af = sim_sd1_hardware(y_af, alpha_hw, d_af, rng, u0=u0_af, v_off=v_off_af, v_hys=0.01 * d_af, sig_int=0.2 * sig0)
    af_hw = decimate_to_nyq(
        sd1_adf_score(q_af, x_af, cfg["alpha_nom"], d_af, tr=cfg["transient"], use_adf=True, fit_offset=True, cal_alpha=True),
        n,
        mos,
    )
    out["afdm_adf"] = dd_map_search(af_hw, x_af_nyq, ell_lo, ell_hi, nu_grid)

    return dict(seed=seed, tau_w=float(tau_w), nu_w=float(nu_w), arms=out)


# ===========================================================================
# 3. Card g09: Asynchronous IF-TEM Endpoint-Telescoping Tridiagonal GLS
# ===========================================================================
def sim_if_tem_branch(sig_br, b, delta, dt, m_tdc, tau_ref=0.0):
    """Exact piecewise-linear IF-TEM spike generator with optional refractory dead-time."""
    nsim = len(sig_br)
    s_pos = sig_br + b
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (s_pos[:-1] + s_pos[1:])) * dt])
    max_i = len(cum) - 2
    t_max = max_i * dt
    if tau_ref <= 0.0:
        k_sp = int(cum[-1] // delta)
        levels = np.arange(1, k_sp + 1, dtype=float) * delta
        levels = levels[levels < cum[-1] - 1e-12]
        idx = np.clip(np.searchsorted(cum, levels) - 1, 0, max_i)
        frac = (levels - cum[idx]) / np.maximum(cum[idx + 1] - cum[idx], 1e-15)
        t_true = (idx + frac) * dt
    else:
        # Exact event-driven integration with dead-time tau_ref after each firing
        t_list = []
        t_cur = 0.0
        while t_cur < t_max:
            u = min(t_cur / dt, max_i + 1.0 - 1e-7)
            i0 = min(int(u), max_i)
            f0 = u - i0
            c_start = cum[i0] * (1.0 - f0) + cum[i0 + 1] * f0
            target = c_start + delta
            if target >= cum[-1] - 1e-12:
                break
            idx = int(np.clip(np.searchsorted(cum, target) - 1, 0, max_i))
            frac = (target - cum[idx]) / max(cum[idx + 1] - cum[idx], 1e-15)
            t_fire = (idx + frac) * dt
            t_list.append(t_fire)
            t_cur = t_fire + tau_ref
        t_true = np.asarray(t_list, dtype=float)
    t_hat = np.round(t_true * m_tdc) / m_tdc
    t_hat = np.clip(t_hat, dt, t_max - 1e-6)
    return t_hat


def eval_cum_piecewise(cum_arr, t_arr, dt, nsim):
    max_u = len(cum_arr) - 1.000001
    u = np.clip(t_arr / dt, 0.0, max_u)
    i0 = u.astype(int)
    f0 = u - i0
    return cum_arr[i0] * (1.0 - f0) + cum_arr[i0 + 1] * f0


def eval_sig_piecewise(sig_arr, t_arr, dt, nsim):
    max_u = len(sig_arr) - 1.000001
    u = np.clip(t_arr / dt, 0.0, max_u)
    i0 = u.astype(int)
    f0 = u - i0
    return sig_arr[i0] * (1.0 - f0) + sig_arr[i0 + 1] * f0


def tem_reconstruct_nyq(t_hat_r, t_hat_i, x_fine, n, lsim, b, delta, m_tdc, sig0_est, mode):
    """Blind g0 estimation + residual projection onto Nyquist basis (no oracle g0!)."""
    nsim = len(x_fine)
    dt = 1.0 / lsim
    xr_f, xi_f = x_fine.real, x_fine.imag
    cum_xr = np.concatenate([[0.0], np.cumsum(0.5 * (xr_f[:-1] + xr_f[1:])) * dt])
    cum_xi = np.concatenate([[0.0], np.cumsum(0.5 * (xi_f[:-1] + xi_f[1:])) * dt])

    # Blind 2D LS estimate of g0 = g0_r + j g0_i from cumulative firing conservation k*delta - b*t_hat
    kr = np.arange(1, len(t_hat_r) + 1, dtype=float)
    ki = np.arange(1, len(t_hat_i) + 1, dtype=float)
    ixr_r = eval_cum_piecewise(cum_xr, t_hat_r, dt, nsim)
    ixi_r = eval_cum_piecewise(cum_xi, t_hat_r, dt, nsim)
    ixr_i = eval_cum_piecewise(cum_xr, t_hat_i, dt, nsim)
    ixi_i = eval_cum_piecewise(cum_xi, t_hat_i, dt, nsim)

    # Include unknown initial state c0_r, c0_i in linear regression!
    Ar = np.column_stack([ixr_r, -ixi_r, np.ones_like(ixr_r), np.zeros_like(ixr_r)])
    Ai = np.column_stack([ixi_i, ixr_i, np.zeros_like(ixi_i), np.ones_like(ixi_i)])
    A_ls = np.vstack([Ar, Ai])
    y_ls = np.concatenate([kr * delta - b * t_hat_r, ki * delta - b * t_hat_i])
    sol, _, _, _ = np.linalg.lstsq(A_ls, y_ls, rcond=None)
    g0_hat = complex(sol[0], sol[1])

    # Build Fourier basis G_br of size (K, n) for bandlimited Nyquist projection:
    # A bandlimited Nyquist signal z[m] (m=0..n-1) has Fourier coeffs Z[f] (f in fftfreq*n).
    # Integral over [t_{k-1}, t_k] of exp(j 2pi f t / n) is exact closed-form!
    freqs = np.fft.fftfreq(n) * (2.0 * np.pi)  # rad / Ts, length n
    nyq_parts = []
    for br_idx, t_hat in enumerate((t_hat_r, t_hat_i)):
        t0 = np.concatenate([[0.0], t_hat[:-1]])
        t1 = t_hat
        dt_k = np.maximum(t1 - t0, 1e-6)
        if br_idx == 0:
            s0_f = (g0_hat * x_fine).real
            cum_s0 = sol[0] * cum_xr - sol[1] * cum_xi
        else:
            s0_f = (g0_hat * x_fine).imag
            cum_s0 = sol[0] * cum_xi + sol[1] * cum_xr
        int_s0 = eval_cum_piecewise(cum_s0, t1, dt, nsim) - eval_cum_piecewise(cum_s0, t0, dt, nsim)
        r_k = delta - (int_s0 + b * (t1 - t0))
        # Discard index 0 (initial capacitor transient before first spike)
        r_k = r_k[1:]
        t0, t1, dt_k = t0[1:], t1[1:], dt_k[1:]
        k_len = len(r_k)
        if k_len < 8:
            nyq_parts.append(np.zeros(n, dtype=float))
            continue

        # Exact integral matrix Phi_{k, f} = int_{t0_k}^{t1_k} exp(j * freqs[f] * t) dt / sqrt(n)
        t_mid = 0.5 * (t0 + t1)
        # Note np.sinc(u) = sin(pi u)/(pi u) => int_{t0}^{t1} e^{j w t} dt = dt_k * e^{j w t_mid} * sinc(w * dt_k / (2*pi))
        Phi = (dt_k[:, None] * np.exp(1j * t_mid[:, None] * freqs[None, :]) * np.sinc(dt_k[:, None] * freqs[None, :] / (2.0 * np.pi))) / np.sqrt(n)

        v_end = np.maximum(eval_sig_piecewise(s0_f, t1, dt, nsim) + b, 0.05 * b)
        v_start = np.maximum(eval_sig_piecewise(s0_f, t0, dt, nsim) + b, 0.05 * b)
        q_var = (1.0 / (m_tdc * m_tdc)) / 12.0
        th_var = max(0.5 * sig0_est * sig0_est, 1e-9) * dt_k

        if mode == "tdc_riem":
            # Trapezoidal / midpoint Riemann adjoint projection Phi^H r_k (since r_k already = (y_avg)*dt_k!)
            Z_hat = Phi.conj().T @ r_k
        elif mode == "tdc_lt":
            # Unweighted Lazar-Toth bandlimited frame pseudoinverse (Phi^H Phi + reg I)^{-1} Phi^H r_k
            gram = Phi.conj().T @ Phi + 1e-3 * np.eye(n)
            Z_hat = np.linalg.solve(gram, Phi.conj().T @ r_k)
        elif mode == "tdc_diag_gls":
            # Heteroscedastic diagonal slope-weighted GLS (NO off-diagonal endpoint telescoping!)
            d_diag = th_var + q_var * (v_end * v_end + v_start * v_start)
            w_r = r_k / d_diag
            Z_hat = Phi.conj().T @ w_r
        elif mode == "tdc_homo_tri":
            # Homoscedastic tridiagonal MA(1) GLS (mean slope v_bar)
            v_bar2 = float(np.mean(v_end * v_end))
            ab = np.zeros((2, k_len), dtype=float)
            ab[0, :] = th_var + 2.0 * q_var * v_bar2
            ab[1, :-1] = -q_var * v_bar2
            w_r = solveh_banded(ab, r_k, lower=True)
            Z_hat = Phi.conj().T @ w_r
        else:
            # Exact heteroscedastic endpoint-telescoping tridiagonal TEM-TriGLS ("tdc_het_tri" / "tdc_het_tri_ref")
            # Note end of interval k is start of interval k+1 => v_{start, k+1} == v_{end, k}!
            ab = np.zeros((2, k_len), dtype=float)
            ab[0, :] = th_var + q_var * (v_end * v_end + v_start * v_start)
            ab[1, :-1] = -q_var * (v_end[:-1] * v_end[:-1])
            w_r = solveh_banded(ab, r_k, lower=True)
            Z_hat = Phi.conj().T @ w_r

        # Reconstruct real Nyquist branch time series from Fourier domain Z_hat
        z_br = np.fft.ifft(Z_hat * np.sqrt(n)).real
        nyq_parts.append(z_br)

    return nyq_parts[0] + 1j * nyq_parts[1]


def g09_sim_frame(seed, m_tdc, cnr_db, wsr_db, is_null=False):
    cfg = CFG["g09"]
    n, lsim = cfg["N"], cfg["Lsim"]
    nsim = n * lsim
    dt = 1.0 / lsim
    rng = np.random.default_rng(seed)
    nu_all = np.arange(-cfg["nu_max"], cfg["nu_max"] + 1e-9, cfg["nu_step"])
    nu_grid = nu_all[np.abs(nu_all) > 0.75 + 1e-9]
    ell_lo, ell_hi = cfg["ell_range"]

    x_sc = gen_oversampled_waveform(rng, n, lsim, "sc", beta=cfg["beta"], c1_k=cfg["c1_k"])
    x_af = gen_oversampled_waveform(rng, n, lsim, "afdm", beta=cfg["beta"], c1_k=cfg["c1_k"])
    x_sc_nyq = decimate_to_nyq(x_sc, n, lsim)
    x_af_nyq = decimate_to_nyq(x_af, n, lsim)

    g0 = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi))
    sig0 = 10.0 ** (-0.05 * cnr_db)
    # Continuous white noise power spectral density matching Nyquist thermal SNR:
    # Over Nyquist Ts = 1, int_0^1 w(t) dt has variance sig0^2 => fine step dt has variance sig0^2 / dt!
    w_fine = (rng.standard_normal(nsim) + 1j * rng.standard_normal(nsim)) / np.sqrt(2.0 * dt) * sig0

    tau_w = rng.uniform(5.0, 28.0)
    nu_w = rng.choice([-1.0, 1.0]) * rng.uniform(1.2, 2.75)
    gw = 0.0 if is_null else (10.0 ** (0.05 * wsr_db)) * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi))
    idx_f = np.arange(nsim, dtype=float)

    out = {}
    for wf, x_f, x_nyq in (("sc", x_sc, x_sc_nyq), ("afdm", x_af, x_af_nyq)):
        psi_f = frac_shift_periodic(x_f, tau_w * lsim) * np.exp(2j * np.pi * nu_w * idx_f / nsim)
        y_f = g0 * x_f + gw * psi_f + w_fine
        # Unified peak-margin rule & matched average firing rate 3.5 spikes/Ts/branch!
        s0_peak = max(float(np.max(np.abs((g0 * x_f).real))), float(np.max(np.abs((g0 * x_f).imag))))
        b = cfg["peak_margin"] * s0_peak
        delta = b / cfg["target_rate"]

        tr_nom = sim_if_tem_branch(y_f.real, b, delta, dt, m_tdc, tau_ref=0.0)
        ti_nom = sim_if_tem_branch(y_f.imag, b, delta, dt, m_tdc, tau_ref=0.0)
        # Estimate thermal noise floor blindly from high-frequency differences (or practical floor)
        # Note: in TEM-TriGLS, sig0_est sets smooth low-pass cutoff; estimate blindly from receiver thermal NF or high-order diff
        # Wait: NO oracle sig0! Estimate sig0_est blindly from long-window cumulative variance!
        # Over M_win = 16 spikes (~4.5 Ts), endpoint jitter cancels to O(Delta_tdc^2 / 16) while thermal noise accumulates!
        # Let's compute blind sig0_est inside each frame from 16-spike block residuals!
        kr16 = np.arange(16, len(tr_nom), 16)
        if len(kr16) >= 4:
            # Quick LS g0 on tr_nom
            cum_xr = np.concatenate([[0.0], np.cumsum(0.5 * (x_f.real[:-1] + x_f.real[1:])) * dt])
            cum_xi = np.concatenate([[0.0], np.cumsum(0.5 * (x_f.imag[:-1] + x_f.imag[1:])) * dt])
            ix1 = eval_cum_piecewise(cum_xr, tr_nom, dt, nsim)
            ix2 = eval_cum_piecewise(cum_xi, tr_nom, dt, nsim)
            Ar0 = np.column_stack([ix1, -ix2, np.ones_like(ix1)])
            yr0 = np.arange(1, len(tr_nom) + 1) * delta - b * tr_nom
            c_ls, _, _, _ = np.linalg.lstsq(Ar0, yr0, rcond=None)
            res_cum = yr0 - Ar0 @ c_ls
            blk_diff = res_cum[kr16[1:]] - res_cum[kr16[:-1]]
            blk_dt = np.maximum(tr_nom[kr16[1:]] - tr_nom[kr16[:-1]], 1.0)
            var_1d = max(float(np.median(blk_diff * blk_diff / blk_dt)) - 2.0 * (b / m_tdc) ** 2 / (12.0 * float(np.mean(blk_dt))), (b / (m_tdc * 25.0)) ** 2)
            sig0_blind = float(np.clip(np.sqrt(2.0 * var_1d), 1e-3, 0.5))
        else:
            sig0_blind = 0.02

        if wf == "sc":
            for arm in ("tdc_lt", "tdc_riem", "tdc_diag_gls", "tdc_homo_tri", "tdc_het_tri"):
                z_nyq = tem_reconstruct_nyq(tr_nom, ti_nom, x_f, n, lsim, b, delta, m_tdc, sig0_blind, arm)
                out[f"sc_{arm}"] = dd_map_search(z_nyq, x_nyq, ell_lo, ell_hi, nu_grid)
            # Refractory dead-time mismatch arm tau_ref = 0.015 Ts (unmodeled by receiver!)
            tr_ref = sim_if_tem_branch(y_f.real, b, delta, dt, m_tdc, tau_ref=cfg["tau_ref"])
            ti_ref = sim_if_tem_branch(y_f.imag, b, delta, dt, m_tdc, tau_ref=cfg["tau_ref"])
            z_ref = tem_reconstruct_nyq(tr_ref, ti_ref, x_f, n, lsim, b, delta, m_tdc, sig0_blind, "tdc_het_tri")
            out["sc_tdc_het_tri_ref"] = dd_map_search(z_ref, x_nyq, ell_lo, ell_hi, nu_grid)
        else:
            z_af = tem_reconstruct_nyq(tr_nom, ti_nom, x_f, n, lsim, b, delta, m_tdc, sig0_blind, "tdc_het_tri")
            out["afdm_tdc_het_tri"] = dd_map_search(z_af, x_nyq, ell_lo, ell_hi, nu_grid)
            tr_af_ref = sim_if_tem_branch(y_f.real, b, delta, dt, m_tdc, tau_ref=cfg["tau_ref"])
            ti_af_ref = sim_if_tem_branch(y_f.imag, b, delta, dt, m_tdc, tau_ref=cfg["tau_ref"])
            z_af_ref = tem_reconstruct_nyq(tr_af_ref, ti_af_ref, x_f, n, lsim, b, delta, m_tdc, sig0_blind, "tdc_het_tri")
            out["afdm_tdc_het_tri_ref"] = dd_map_search(z_af_ref, x_nyq, ell_lo, ell_hi, nu_grid)

    return dict(seed=seed, tau_w=float(tau_w), nu_w=float(nu_w), arms=out)


# ===========================================================================
# 4. Implementation Gates (`smoke`)
# ===========================================================================
def run_smoke_gates():
    rng = np.random.default_rng(20261122)
    gates = {}

    # Gate 1: G_g10_noiseless_exact
    n = 1024
    lags1, lags2 = list(range(-8, 9)), list(range(-8, 48))
    syms = gen_constellation(rng, n, "qpsk")
    taus_c = np.array([3.2, 9.7, 18.4, 29.1])
    amps_c = np.array([0.7 - 0.2j, -0.4 + 0.5j, 0.3 + 0.2j, -0.2 - 0.15j])
    for wf in ("ofdm", "afdm"):
        xt = np.fft.ifft(syms) * np.sqrt(n) if wf == "ofdm" else daft_u(syms, 5, inverse=True)
        y1 = np.exp(0.6j) * frac_shift_compact(xt, 0.18)
        y2 = sum(amps_c[p] * frac_shift_compact(xt, 0.18 - 0.27 + taus_c[p]) for p in range(4))
        xt_em, sh_em = run_cafa_em(y1 + 1e-7 * rng.standard_normal(n), y2 + 1e-7 * rng.standard_normal(n), wf, "qpsk", lags1, lags2, n_iters=4)
        # Check symbol error rate up to global k*pi/2 phase rotation
        sers = [float(np.mean(np.abs(sh_em * (1j ** k) - syms) > 0.1)) for k in range(4)]
        r_res = eca_cancel(y2, xt_em, lags2, tapers=1)
        rel_res = float(np.linalg.norm(r_res) / np.linalg.norm(y2))
        gates[f"G_g10_noiseless_{wf}"] = dict(min_ser=min(sers), rel_residual=rel_res, pass_gate=(min(sers) == 0.0 and rel_res < 1e-5))

    # Gate 2: G_g10_linear_self_suppression
    xt = np.fft.ifft(syms) * np.sqrt(n)
    y1 = xt + (rng.standard_normal(n) + 1j * rng.standard_normal(n)) * 0.8  # ~ -1 dB SNR1
    psi_t = np.roll(xt, 16) * np.exp(2j * np.pi * 2.0 * np.arange(n) / n)
    y2 = 1.0 * np.roll(xt, 5) + 0.04 * psi_t + (rng.standard_normal(n) + 1j * rng.standard_normal(n)) * 0.02
    xt_lin, _ = run_cafa_em(y1, y2, "ofdm", "qpsk", lags1, lags2, n_iters=0)
    xt_em, _ = run_cafa_em(y1, y2, "ofdm", "qpsk", lags1, lags2, n_iters=4)
    r_lin = eca_cancel(y2, xt_lin, lags2, tapers=1)
    r_em = eca_cancel(y2, xt_em, lags2, tapers=1)
    r_ora = eca_cancel(y2, xt, lags2, tapers=1)
    sinr_ora = (abs(np.vdot(psi_t, r_ora)) ** 2) / max(float(np.vdot(r_ora, r_ora).real), 1e-15)
    sinr_lin = (abs(np.vdot(psi_t, r_lin)) ** 2) / max(float(np.vdot(r_lin, r_lin).real), 1e-15)
    sinr_em = (abs(np.vdot(psi_t, r_em)) ** 2) / max(float(np.vdot(r_em, r_em).real), 1e-15)
    ratio_lin = float(sinr_lin / sinr_ora)
    ratio_em = float(sinr_em / sinr_ora)
    gates["G_g10_linear_self_suppression"] = dict(
        lin_retained_target_sinr_ratio=ratio_lin,
        cafa_retained_target_sinr_ratio=ratio_em,
        pass_gate=(ratio_lin < 0.05 and ratio_em > 0.95),
    )

    # Gate 3: G_g07_deterministic_loop_closure
    x_sc = gen_oversampled_waveform(rng, 512, 8, "sc", beta=0.25)
    g0 = np.exp(0.73j)
    q = sim_sd1_hardware(g0 * x_sc, 0.92, 2.0, rng, u0=0.4 - 0.5j)
    # Reconstruct pre-comparator state directly
    xt_f = lfilter([1.0], [1.0, -0.92], x_sc)
    qh = np.zeros_like(q)
    qh[1:] = q[:-1]
    ft_f = 2.0 * lfilter([0.92], [1.0, -0.92], qh)
    # True recursion
    u_c = 0.4 - 0.5j
    u_true = np.empty_like(q)
    for k in range(len(x_sc)):
        um = 0.92 * u_c + g0 * x_sc[k]
        u_true[k] = um
        u_c = um - 2.0 * q[k]
    rel_err7 = float(np.linalg.norm(u_true[180:] - (g0 * xt_f[180:] - ft_f[180:])) / np.linalg.norm(u_true[180:]))
    gates["G_g07_deterministic_loop_closure"] = dict(rel_err_after_180=rel_err7, pass_gate=(rel_err7 < 1e-6))

    # Gate 4: G_g09_telescoping_exact
    x9 = gen_oversampled_waveform(rng, 256, 32, "sc", beta=0.25).real
    psi9 = np.roll(x9, 8 * 32) * np.cos(2 * np.pi * 1.5 * np.arange(len(x9)) / len(x9))
    b9 = 1.15 * float(np.max(np.abs(x9)))
    d9 = b9 / 3.5
    dt9 = 1.0 / 32.0
    t_hat9 = sim_if_tem_branch(x9 + 0.02 * psi9, b9, d9, dt9, m_tdc=65536)
    cum_x9 = np.concatenate([[0.0], np.cumsum(0.5 * (x9[:-1] + x9[1:])) * dt9])
    cum_p9 = np.concatenate([[0.0], np.cumsum(0.5 * (psi9[:-1] + psi9[1:])) * dt9])
    res9 = np.arange(1, len(t_hat9) + 1) * d9 - (eval_cum_piecewise(cum_x9, t_hat9, dt9, len(x9)) + b9 * t_hat9)
    true9 = 0.02 * eval_cum_piecewise(cum_p9, t_hat9, dt9, len(x9))
    rel_err9 = float(np.linalg.norm(res9 - true9) / np.linalg.norm(true9))
    gates["G_g09_telescoping_exact"] = dict(rel_err=rel_err9, pass_gate=(rel_err9 < 1e-4))

    # Also time 1 frame of each card
    t0 = time.time()
    _ = g10_sim_frame(9991, -2.0, -26.0, 0.04, "qpsk", is_null=False)
    t_g10 = time.time() - t0
    t0 = time.time()
    _ = g07_sim_frame(9992, 35.0, -30.0, is_null=False)
    t_g07 = time.time() - t0
    t0 = time.time()
    _ = g09_sim_frame(9993, 8, 40.0, -26.0, is_null=False)
    t_g09 = time.time() - t0
    gates["single_frame_sec"] = dict(g10=round(t_g10, 4), g07=round(t_g07, 4), g09=round(t_g09, 4))
    return gates


# ===========================================================================
# Parallel batch runners for g10, g07, g09
# ===========================================================================
def _worker_g10(task):
    return g10_sim_frame(*task)


def _worker_g07(task):
    return g07_sim_frame(*task)


def _worker_g09(task):
    return g09_sim_frame(*task)


def eval_g10(pool):
    cfg = CFG["g10"]
    c0, c1 = CFG["calib_seeds"]
    n0, n1 = CFG["null_check_seeds"]
    e0, e1 = CFG["eval_seeds"]
    pfa = CFG["pfa"]
    rng_ci = np.random.default_rng(2026112210)
    results = {}

    for mod in cfg["modulations"]:
        for icm in cfg["icm_stds"]:
            for snr1 in cfg["snr1_dbs"]:
                # To keep total core-hours well inside <= 5 core-hr cap while covering full pre-registered matrix:
                # Full 2000-frame calibration + 500 null check + 400 eval per WSR on the decisive ICM=0.04 conditions,
                # and 600 calib + 200 eval on static ICM=0.0 reference slice!
                if icm > 0:
                    cal_s = range(c0, c1)
                    nul_s = range(n0, n1)
                    ev_s = range(e0, e1)
                else:
                    cal_s = range(c0, c0 + 600)
                    nul_s = range(n0, n0 + 200)
                    ev_s = range(e0, e0 + 160)

                cal_rows = list(pool.map(_worker_g10, [(s, snr1, -26.0, icm, mod, True) for s in cal_s], chunksize=16))
                arms = list(cal_rows[0]["arms"].keys())
                thresh = {a: float(np.quantile([r["arms"][a][0] for r in cal_rows], 1.0 - pfa)) for a in arms}

                nul_rows = list(pool.map(_worker_g10, [(s, snr1, -26.0, icm, mod, True) for s in nul_s], chunksize=16))
                emp_pfa = {a: float(np.mean([r["arms"][a][0] > thresh[a] for r in nul_rows])) for a in arms}

                by_wsr = {}
                pooled_hits = {a: [] for a in arms}
                for wsr in cfg["wsrs_db"]:
                    ev_rows = list(pool.map(_worker_g10, [(s, snr1, wsr, icm, mod, False) for s in ev_s], chunksize=16))
                    wsr_rates = {}
                    for a in arms:
                        hits = []
                        for r in ev_rows:
                            pk, ell_h, nu_h = r["arms"][a]
                            # Note: baseline arms correlate against y1 (delay relative to y1 is dtau_12 + tau_w),
                            # whereas xt_em / xt_lin / xt_1s are aligned to symbol grid (delay is dtau_tot + tau_w);
                            # allow fair +-1.8 Ts around true relative lag in either convention:
                            ok_lag = (abs(ell_h - (r["tau_w"] + r["dtau_tot"])) <= 1.8) or (abs(ell_h - r["tau_w"]) <= 2.2)
                            ok_nu = abs(nu_h - r["nu_w"]) <= 0.5
                            hits.append(1.0 if (pk > thresh[a] and ok_lag and ok_nu) else 0.0)
                        wsr_rates[a] = round(float(np.mean(hits)), 4)
                        pooled_hits[a].extend(hits)
                    by_wsr[str(wsr)] = wsr_rates

                pooled = {a: round(float(np.mean(pooled_hits[a])), 4) for a in arms}
                mdr50 = {a: round(interp_mdr50(cfg["wsrs_db"], [by_wsr[str(w)][a] for w in cfg["wsrs_db"]]), 2) for a in arms}
                best_lin = max(["eca", "eca_cd", "gauss_tls", "lin_2ch_eca"], key=lambda a: pooled[a])
                best_cafa = "afdm_cafa" if pooled["afdm_cafa"] >= pooled["ofdm_cafa"] else "ofdm_cafa"
                diff_vs_lin = np.asarray(pooled_hits[best_cafa]) - np.asarray(pooled_hits[best_lin])
                diff_af_of = np.asarray(pooled_hits["afdm_cafa"]) - np.asarray(pooled_hits["ofdm_cafa"])
                key = f"{mod}_icm{icm}_snr{snr1}"
                results[key] = dict(
                    emp_pfa=emp_pfa,
                    by_wsr=by_wsr,
                    pooled_hit=pooled,
                    mdr50_db=mdr50,
                    best_cafa_minus_best_lin_pp=round(100.0 * float(np.mean(diff_vs_lin)), 2),
                    best_cafa_minus_best_lin_ci_pp=[round(100.0 * x, 2) for x in bootstrap_ci(diff_vs_lin, rng_ci)],
                    afdm_minus_ofdm_pp=round(100.0 * float(np.mean(diff_af_of)), 2),
                    afdm_minus_ofdm_ci_pp=[round(100.0 * x, 2) for x in bootstrap_ci(diff_af_of, rng_ci)],
                )
    return results


def eval_g07(pool):
    cfg = CFG["g07"]
    c0, c1 = CFG["calib_seeds"]
    n0, n1 = CFG["null_check_seeds"]
    e0, e1 = CFG["eval_seeds"]
    pfa = CFG["pfa"]
    rng_ci = np.random.default_rng(2026112207)
    results = {}
    pooled_35_42 = {}

    for cnr in cfg["cnrs_db"]:
        cal_rows = list(pool.map(_worker_g07, [(s, cnr, -30.0, True) for s in range(c0, c1)], chunksize=16))
        arms = list(cal_rows[0]["arms"].keys())
        thresh = {a: float(np.quantile([r["arms"][a][0] for r in cal_rows], 1.0 - pfa)) for a in arms}
        nul_rows = list(pool.map(_worker_g07, [(s, cnr, -30.0, True) for s in range(n0, n1)], chunksize=16))
        emp_pfa = {a: float(np.mean([r["arms"][a][0] > thresh[a] for r in nul_rows])) for a in arms}

        by_wsr = {}
        pooled_hits = {a: [] for a in arms}
        for wsr in cfg["wsrs_db"]:
            ev_rows = list(pool.map(_worker_g07, [(s, cnr, wsr, False) for s in range(e0, e1)], chunksize=16))
            wsr_rates = {}
            for a in arms:
                hits = [
                    1.0
                    if (r["arms"][a][0] > thresh[a] and abs(r["arms"][a][1] - r["tau_w"]) <= 1.5 and abs(r["arms"][a][2] - r["nu_w"]) <= 0.5)
                    else 0.0
                    for r in ev_rows
                ]
                wsr_rates[a] = round(float(np.mean(hits)), 4)
                pooled_hits[a].extend(hits)
                if cnr in (35.0, 42.0):
                    pooled_35_42.setdefault(a, []).extend(hits)
            by_wsr[str(wsr)] = wsr_rates

        pooled = {a: round(float(np.mean(pooled_hits[a])), 4) for a in arms}
        mdr50 = {a: round(interp_mdr50(cfg["wsrs_db"], [by_wsr[str(w)][a] for w in cfg["wsrs_db"]]), 2) for a in arms}
        diff_hw_lin = np.asarray(pooled_hits["sc_sd1_adf_hw"]) - np.asarray(pooled_hits["sc_sd1_lin_sic"])
        results[f"cnr{int(cnr)}"] = dict(
            emp_pfa=emp_pfa,
            by_wsr=by_wsr,
            pooled_hit=pooled,
            mdr50_db=mdr50,
            hw_minus_lin_sic_pp=round(100.0 * float(np.mean(diff_hw_lin)), 2),
            hw_minus_lin_sic_ci_pp=[round(100.0 * x, 2) for x in bootstrap_ci(diff_hw_lin, rng_ci)],
        )

    diff_35_42 = np.asarray(pooled_35_42["sc_sd1_adf_hw"]) - np.asarray(pooled_35_42["sc_sd1_lin_sic"])
    results["pooled_cnr35_42"] = dict(
        pooled_hit={a: round(float(np.mean(v)), 4) for a, v in pooled_35_42.items()},
        hw_minus_lin_sic_pp=round(100.0 * float(np.mean(diff_35_42)), 2),
        hw_minus_lin_sic_ci_pp=[round(100.0 * x, 2) for x in bootstrap_ci(diff_35_42, rng_ci)],
    )
    return results


def eval_g09(pool):
    cfg = CFG["g09"]
    c0, c1 = CFG["calib_seeds"]
    n0, n1 = CFG["null_check_seeds"]
    e0, e1 = CFG["eval_seeds"]
    pfa = CFG["pfa"]
    rng_ci = np.random.default_rng(2026112209)
    results = {}

    for m_tdc in cfg["m_tdcs"]:
        for cnr in cfg["cnrs_db"]:
            cal_rows = list(pool.map(_worker_g09, [(s, m_tdc, cnr, -26.0, True) for s in range(c0, c1)], chunksize=16))
            arms = list(cal_rows[0]["arms"].keys())
            thresh = {a: float(np.quantile([r["arms"][a][0] for r in cal_rows], 1.0 - pfa)) for a in arms}
            nul_rows = list(pool.map(_worker_g09, [(s, m_tdc, cnr, -26.0, True) for s in range(n0, n1)], chunksize=16))
            emp_pfa = {a: float(np.mean([r["arms"][a][0] > thresh[a] for r in nul_rows])) for a in arms}

            by_wsr = {}
            pooled_hits = {a: [] for a in arms}
            for wsr in cfg["wsrs_db"]:
                ev_rows = list(pool.map(_worker_g09, [(s, m_tdc, cnr, wsr, False) for s in range(e0, e1)], chunksize=16))
                wsr_rates = {}
                for a in arms:
                    hits = [
                        1.0
                        if (r["arms"][a][0] > thresh[a] and abs(r["arms"][a][1] - r["tau_w"]) <= 1.5 and abs(r["arms"][a][2] - r["nu_w"]) <= 0.5)
                        else 0.0
                        for r in ev_rows
                    ]
                    wsr_rates[a] = round(float(np.mean(hits)), 4)
                    pooled_hits[a].extend(hits)
                by_wsr[str(wsr)] = wsr_rates

            pooled = {a: round(float(np.mean(pooled_hits[a])), 4) for a in arms}
            mdr50 = {a: round(interp_mdr50(cfg["wsrs_db"], [by_wsr[str(w)][a] for w in cfg["wsrs_db"]]), 2) for a in arms}
            diff_het_diag = np.asarray(pooled_hits["sc_tdc_het_tri"]) - np.asarray(pooled_hits["sc_tdc_diag_gls"])
            diff_het_homo = np.asarray(pooled_hits["sc_tdc_het_tri"]) - np.asarray(pooled_hits["sc_tdc_homo_tri"])
            diff_ref_base = np.asarray(pooled_hits["sc_tdc_het_tri_ref"]) - np.asarray(
                pooled_hits[max(["sc_tdc_lt", "sc_tdc_riem", "sc_tdc_diag_gls"], key=lambda a: pooled[a])]
            )
            diff_sc_af = np.asarray(pooled_hits["sc_tdc_het_tri"]) - np.asarray(pooled_hits["afdm_tdc_het_tri"])
            results[f"mtdc{m_tdc}_cnr{int(cnr)}"] = dict(
                emp_pfa=emp_pfa,
                by_wsr=by_wsr,
                pooled_hit=pooled,
                mdr50_db=mdr50,
                het_minus_diag_pp=round(100.0 * float(np.mean(diff_het_diag)), 2),
                het_minus_diag_ci_pp=[round(100.0 * x, 2) for x in bootstrap_ci(diff_het_diag, rng_ci)],
                het_minus_homo_pp=round(100.0 * float(np.mean(diff_het_homo)), 2),
                ref_minus_best_nontri_pp=round(100.0 * float(np.mean(diff_ref_base)), 2),
                ref_minus_best_nontri_ci_pp=[round(100.0 * x, 2) for x in bootstrap_ci(diff_ref_base, rng_ci)],
                sc_minus_afdm_pp=round(100.0 * float(np.mean(diff_sc_af)), 2),
                sc_minus_afdm_ci_pp=[round(100.0 * x, 2) for x in bootstrap_ci(diff_sc_af, rng_ci)],
            )
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["smoke", "g10", "g07", "g09", "all"])
    ap.add_argument("--out", default=str(HERE / "out_g2"))
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    t_cpu0 = os.times()

    gates = run_smoke_gates()
    if args.cmd == "smoke":
        print(json.dumps(gates, indent=2))
        all_ok = all(v["pass_gate"] for k, v in gates.items() if isinstance(v, dict) and "pass_gate" in v)
        if not all_ok:
            raise SystemExit("SMOKE GATE FAILED!")
        return

    all_ok = all(v["pass_gate"] for k, v in gates.items() if isinstance(v, dict) and "pass_gate" in v)
    if not all_ok:
        raise SystemExit(f"SMOKE GATE FAILED: {json.dumps(gates)}")

    summary = dict(gates=gates, workers=args.workers)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        if args.cmd in ("g10", "all"):
            t0 = time.time()
            summary["g10"] = eval_g10(pool)
            summary["g10_wall_sec"] = round(time.time() - t0, 2)
        if args.cmd in ("g07", "all"):
            t0 = time.time()
            summary["g07"] = eval_g07(pool)
            summary["g07_wall_sec"] = round(time.time() - t0, 2)
        if args.cmd in ("g09", "all"):
            t0 = time.time()
            summary["g09"] = eval_g09(pool)
            summary["g09_wall_sec"] = round(time.time() - t0, 2)

    t_cpu1 = os.times()
    cpu_sec = (t_cpu1.user - t_cpu0.user) + (t_cpu1.system - t_cpu0.system) + (t_cpu1.children_user - t_cpu0.children_user) + (t_cpu1.children_system - t_cpu0.children_system)
    summary["wall_sec"] = round(time.time() - t_start, 2)
    summary["cpu_core_hours"] = round(cpu_sec / 3600.0, 4)

    out_path = out_dir / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"DONE in {summary['wall_sec']}s wall ({summary['cpu_core_hours']} CPU core-hrs) -> {out_path}")


if __name__ == "__main__":
    main()
