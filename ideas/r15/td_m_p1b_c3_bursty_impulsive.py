#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C3 Refined Steelman Teardown (`td_m_p1b_c3_bursty_impulsive.py`):
Bursty & Receive-Filter-Colored Heavy-Tailed Non-Gaussian Impulsive Noise
in Doubly-Dispersive Channels (AFDM / OTFS / SC-FDE, Joint CE + 16-QAM Detection).

Refinements after smoke test:
  - Fixed natural-parameter EP/OAMP damping (`Ref_Clean_OAMP < 0.003` verified).
  - Sweeps SNR (20, 24, 28 dB) & duty (12%, 20%) to inspect HIGH-SNR FLOOR behavior (where break-wall >= 15x is judged!).
  - Upgraded R2_EstH CE Steelman with fine continuous Newton/golden-section Doppler refinement + Huber-IRLS + Colored-HMM CE
    so EstH isn't crippled by a coarse Doppler grid!
  - Added SIMO Nr=2 / rate-0.80 data-load check to ensure `Oracle_TrueH_TrueState_OAMP` reaches clean `< 1e-2` floor
    (eliminating rank-deficiency floor shared by Oracle and Steelman!).
  - Added a stronger Steelman: `SM_HMM_Innov_FullCovOAMP_Tuned` sweeping deconvolution Tikhonov reg in {0.01, 0.05, 0.2}
    and ALSO `SM_JointSparseOutlier_L1_OAMP` (convex L1/ADMM pre-filter impulse + symbol recovery: y = Ax + Ge + w)!
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.linalg import cho_factor, cho_solve


def gray_qam(M: int) -> np.ndarray:
    ms = int(round(math.sqrt(M)))
    b = np.arange(ms)
    g = b ^ (b >> 1)
    lut = np.argsort(g)
    lv = 2 * lut - (ms - 1)
    pts = np.array([lv[i] + 1j * lv[q] for q in range(ms) for i in range(ms)], dtype=np.complex128)
    return pts / math.sqrt(float(np.mean(np.abs(pts) ** 2)))


def daft_mat(N: int, c1: float, c2: float) -> np.ndarray:
    n = np.arange(N, dtype=float)
    m = np.arange(N, dtype=float)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (m ** 2))
    W = np.exp(-1j * 2.0 * np.pi * np.outer(m, n) / N) / math.sqrt(N)
    return (L2[:, None] * W) * L1[None, :]


def otfs_mat(M_del: int, N_dop: int) -> np.ndarray:
    F_N = np.fft.fft(np.eye(N_dop)) / math.sqrt(N_dop)
    return np.kron(F_N, np.eye(M_del))


def scfde_mat(N: int) -> np.ndarray:
    return np.eye(N, dtype=np.complex128)


def build_td_channel(N: int, P: int, l_max: int, k_max: float, rng: np.random.Generator, cpp_c1: float = 0.0):
    delays = np.sort(rng.choice(np.arange(0, l_max + 1), size=P, replace=False))
    delays[0] = 0
    pdp = np.exp(-0.25 * delays)
    pdp /= np.sum(pdp)
    gains = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) * np.sqrt(pdp / 2.0)
    dopplers = rng.uniform(-k_max, k_max, size=P)
    H = np.zeros((N, N), dtype=np.complex128)
    n_idx = np.arange(N, dtype=float)
    for p in range(P):
        l_p = int(delays[p])
        nu_p = float(dopplers[p])
        g_p = gains[p]
        phase_dop = np.exp(1j * 2.0 * np.pi * nu_p * n_idx / float(N))
        for n in range(N):
            m = (n - l_p) % N
            cpp_ph = np.exp(-1j * 2.0 * np.pi * cpp_c1 * (N * N - 2.0 * N * (l_p - n))) if (cpp_c1 != 0.0 and n < l_p) else 1.0
            H[n, m] += g_p * phase_dop[n] * cpp_ph
    return H, {"delays": delays, "dopplers": dopplers, "gains": gains}


def build_rx_filter_matrix(N: int, colored: bool = True, bw_factor: float = 0.42) -> np.ndarray:
    if not colored:
        return np.eye(N, dtype=np.complex128)
    L_half = 6
    k_grid = np.arange(-L_half, L_half + 1, dtype=float)
    t = k_grid * bw_factor
    h_filt = np.sinc(t) * (0.54 + 0.46 * np.cos(np.pi * k_grid / (L_half + 0.5)))
    decay = np.where(k_grid >= 0, np.exp(-0.18 * np.maximum(k_grid, 0)), 0.45)
    h_filt = h_filt * decay
    h_filt /= math.sqrt(float(np.sum(h_filt ** 2)))
    G = np.zeros((N, N), dtype=np.complex128)
    for n in range(N):
        for idx_k, tap in enumerate(h_filt):
            m = n - (idx_k - L_half)
            if 0 <= m < N:
                G[n, m] = tap
    G /= np.maximum(np.linalg.norm(G, axis=1, keepdims=True), 1e-12)
    return G


def gen_markov_burst_noise(N: int, sigma0_sq: float, duty: float, mean_burst: float, inr_db: float, rng: np.random.Generator):
    p10 = 1.0 / float(mean_burst)
    p01 = p10 * duty / max(1.0 - duty, 1e-6)
    states = np.zeros(N, dtype=int)
    states[0] = 1 if rng.random() < duty else 0
    for n in range(1, N):
        if states[n - 1] == 1:
            states[n] = 0 if rng.random() < p10 else 1
        else:
            states[n] = 1 if rng.random() < p01 else 0
    sigma_I_sq = sigma0_sq * (10.0 ** (inr_db / 10.0))
    v_z = states.astype(float) * sigma_I_sq
    e_pre = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * np.sqrt(v_z / 2.0)
    return e_pre, states, v_z, {"p01": p01, "p10": p10, "sigma_I_sq": sigma_I_sq}


def gen_alpha_stable_noise(N: int, alpha: float, gamma_scale: float, rng: np.random.Generator):
    beta = alpha / 2.0
    U = rng.uniform(0.0, math.pi, size=N)
    W = rng.exponential(1.0, size=N)
    num = np.sin(beta * U)
    den = np.sin(U) ** (1.0 / beta)
    fac = (np.sin((1.0 - beta) * U) / np.maximum(W, 1e-12)) ** ((1.0 - beta) / beta)
    A = np.minimum((num / np.maximum(den, 1e-12)) * fac, 1e6)
    v_z = 2.0 * (gamma_scale ** 2) * A
    e_pre = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * np.sqrt(v_z / 2.0)
    return e_pre, v_z


def qam_mmse_denoise(r: np.ndarray, v: np.ndarray, const: np.ndarray):
    v_safe = np.maximum(np.real(v), 1e-6)
    if np.ndim(v_safe) == 0:
        v_safe = np.full(len(r), float(v_safe))
    d2 = np.abs(r[:, None] - const[None, :]) ** 2
    lp = -d2 / v_safe[:, None]
    lp -= np.max(lp, axis=1, keepdims=True)
    p = np.exp(lp)
    p /= np.sum(p, axis=1, keepdims=True)
    xh = p @ const
    var = np.sum(p * (np.abs(const[None, :] - xh[:, None]) ** 2), axis=1)
    return xh, np.maximum(np.real(var), 1e-7)


def full_cov_lmmse(y: np.ndarray, A: np.ndarray, C_n: np.ndarray, known_idx: np.ndarray = None, x_known: np.ndarray = None):
    """Exact full-covariance LMMSE supporting optional embedded known pilots (zero-variance columns)."""
    M, N = A.shape
    c_fac = cho_factor(C_n + 1e-10 * np.eye(M), lower=True)
    if known_idx is not None and len(known_idx) > 0:
        mask = np.ones(N, dtype=bool)
        mask[known_idx] = False
        A_d = A[:, mask]
        y_eff = y - A[:, known_idx] @ x_known
    else:
        mask = np.ones(N, dtype=bool)
        A_d = A
        y_eff = y
    Nd = A_d.shape[1]
    Cinv_Ad = cho_solve(c_fac, A_d)
    J = A_d.conj().T @ Cinv_Ad + np.eye(Nd, dtype=np.complex128)
    j_fac = cho_factor(J + 1e-10 * np.eye(Nd), lower=True)
    x_d = cho_solve(j_fac, A_d.conj().T @ cho_solve(c_fac, y_eff))
    x_out = np.zeros(N, dtype=np.complex128)
    x_out[mask] = x_d
    if known_idx is not None and len(known_idx) > 0:
        x_out[known_idx] = x_known
    return x_out


def full_cov_ep_oamp(
    y: np.ndarray, A: np.ndarray, C_n: np.ndarray, const: np.ndarray,
    known_idx: np.ndarray = None, x_known: np.ndarray = None,
    n_iters: int = 10, damp: float = 0.65
):
    """Numerically stable full-covariance EP in natural parameter space, supporting known pilot indices."""
    M, N = A.shape
    if known_idx is not None and len(known_idx) > 0:
        mask = np.ones(N, dtype=bool)
        mask[known_idx] = False
        A_d = A[:, mask]
        y_eff = y - A[:, known_idx] @ x_known
    else:
        mask = np.ones(N, dtype=bool)
        A_d = A
        y_eff = y
    Nd = A_d.shape[1]
    gam_p = np.ones(Nd, dtype=float)
    h_p = np.zeros(Nd, dtype=np.complex128)

    c_fac = cho_factor(C_n + 1e-10 * np.eye(M), lower=True)
    Cinv_A = cho_solve(c_fac, A_d)
    At_Cinv_A = A_d.conj().T @ Cinv_A
    At_Cinv_y = A_d.conj().T @ cho_solve(c_fac, y_eff)
    I_Nd = np.eye(Nd, dtype=np.complex128)

    x_hat = np.zeros(Nd, dtype=np.complex128)
    for it in range(n_iters):
        J = At_Cinv_A.copy()
        J[np.diag_indices(Nd)] += gam_p
        j_fac = cho_factor(J + 1e-10 * I_Nd, lower=True)
        x_post = cho_solve(j_fac, At_Cinv_y + h_p)
        J_inv = cho_solve(j_fac, I_Nd)
        v_post = np.maximum(np.real(np.diag(J_inv)), 1e-6)

        gam_ext = np.maximum(1.0 / v_post - gam_p, 1e-4)
        h_ext = x_post / v_post - h_p
        v_ext = 1.0 / gam_ext
        r_ext = h_ext * v_ext

        x_hat, v_hat = qam_mmse_denoise(r_ext, v_ext, const)
        v_hat_s = np.maximum(v_hat, 1e-5)

        gam_new = 1.0 / v_hat_s - gam_ext
        h_new = x_hat / v_hat_s - h_ext
        valid = gam_new > 1e-3
        gam_c = np.clip(gam_new, 1e-3, 1e4)
        # Preserve exact prior mean when precision is clipped (prevents high-SNR h/gam mismatch!)
        m_new = h_new / np.maximum(gam_new, 1e-12)
        gam_upd = np.where(valid, gam_c, gam_p)
        h_upd = np.where(valid, gam_c * m_new, h_p)

        if it == 0:
            gam_p, h_p = gam_upd, h_upd
        else:
            gam_p = damp * gam_upd + (1.0 - damp) * gam_p
            h_p = damp * h_upd + (1.0 - damp) * h_p

    x_out = np.zeros(N, dtype=np.complex128)
    x_out[mask] = x_hat
    if known_idx is not None and len(known_idx) > 0:
        x_out[known_idx] = x_known
    return x_out


def hard_ser_sub(xh: np.ndarray, xt: np.ndarray, const: np.ndarray, data_idx: np.ndarray) -> float:
    i1 = np.argmin(np.abs(xh[data_idx, None] - const[None, :]), axis=1)
    i2 = np.argmin(np.abs(xt[data_idx, None] - const[None, :]), axis=1)
    return float(np.mean(i1 != i2))


def hmm_fb_2state(ll0: np.ndarray, ll1: np.ndarray, p01: float, p10: float):
    N = len(ll0)
    pi1 = p01 / max(p01 + p10, 1e-9)
    pi0 = 1.0 - pi1
    logT = np.array([
        [math.log(max(1.0 - p01, 1e-9)), math.log(max(p01, 1e-9))],
        [math.log(max(p10, 1e-9)), math.log(max(1.0 - p10, 1e-9))],
    ])
    la = np.zeros((N, 2), dtype=float)
    la[0, 0] = math.log(max(pi0, 1e-9)) + ll0[0]
    la[0, 1] = math.log(max(pi1, 1e-9)) + ll1[0]
    for n in range(1, N):
        for j, llj in enumerate((ll0[n], ll1[n])):
            a0 = la[n - 1, 0] + logT[0, j]
            a1 = la[n - 1, 1] + logT[1, j]
            m = max(a0, a1)
            la[n, j] = m + math.log(math.exp(a0 - m) + math.exp(a1 - m)) + llj
    lb = np.zeros((N, 2), dtype=float)
    for n in range(N - 2, -1, -1):
        for i in range(2):
            b0 = logT[i, 0] + ll0[n + 1] + lb[n + 1, 0]
            b1 = logT[i, 1] + ll1[n + 1] + lb[n + 1, 1]
            m = max(b0, b1)
            lb[n, i] = m + math.log(math.exp(b0 - m) + math.exp(b1 - m))
    lp = la + lb
    lp -= np.max(lp, axis=1, keepdims=True)
    p = np.exp(lp); p /= np.sum(p, axis=1, keepdims=True)
    return p[:, 1]


def rx_zmnl(y, A, sigma0_sq, const, pil_idx, x_pil):
    med = float(np.median(np.abs(y)))
    sig_est = max(med / 0.8326, math.sqrt(1.0 + sigma0_sq))
    best_x, best_obj = None, 1e18
    for mult in [1.8, 2.4, 3.0]:
        T = mult * sig_est
        mag = np.abs(y)
        yc = np.where(mag > T, y * (T / np.maximum(mag, 1e-12)), y)
        xl = full_cov_lmmse(yc, A, max(sigma0_sq, 0.01) * np.eye(len(y), dtype=np.complex128), pil_idx, x_pil)
        xq = const[np.argmin(np.abs(xl[:, None] - const[None, :]), axis=1)]
        if pil_idx is not None and len(pil_idx) > 0:
            xq[pil_idx] = x_pil
        res = np.abs(y - A @ xq)
        obj = float(np.mean(np.minimum(res, 2.0 * sig_est) ** 2))
        if obj < best_obj:
            best_obj = obj; best_x = xl
    return best_x


def rx_huber_oamp(y, A, sigma0_sq, const, pil_idx, x_pil, n_outer=6):
    N = len(y)
    med = float(np.median(np.abs(y)))
    T0 = 2.4 * max(med / 0.8326, 1.0)
    w = np.where(np.abs(y) > T0, T0 / np.maximum(np.abs(y), 1e-12), 1.0)
    v_diag = sigma0_sq / np.maximum(w, 1e-4)
    xh = np.zeros(N, dtype=np.complex128)
    for _ in range(n_outer):
        xh = full_cov_ep_oamp(y, A, np.diag(v_diag), const, pil_idx, x_pil, n_iters=6, damp=0.65)
        res = np.abs(y - A @ xh)
        mad = max(float(np.median(res)) / 0.6745, math.sqrt(sigma0_sq))
        delta = 1.345 * mad
        w = np.where(res <= delta, 1.0, delta / np.maximum(res, 1e-12))
        v_diag = np.clip((mad ** 2) / np.maximum(w, 1e-5), sigma0_sq, 1e5)
    return xh


def rx_iid_bg_oamp(y, A, sigma0_sq, const, pil_idx, x_pil, p_init, sI_init, known_stats=False, n_outer=7):
    N = len(y)
    p = p_init; sI = sI_init
    xh = rx_huber_oamp(y, A, sigma0_sq, const, pil_idx, x_pil, n_outer=1)
    for _ in range(n_outer):
        r2 = np.abs(y - A @ xh) ** 2
        s0 = max(sigma0_sq, 1e-5)
        s1 = max(s0 + sI, 10.0 * s0)
        ll0 = -math.log(s0) - r2 / s0 + math.log(max(1.0 - p, 1e-6))
        ll1 = -math.log(s1) - r2 / s1 + math.log(max(p, 1e-6))
        m = np.maximum(ll0, ll1)
        q0 = np.exp(ll0 - m); q1 = np.exp(ll1 - m)
        gam = q1 / (q0 + q1)
        if not known_stats:
            p = float(np.clip(np.mean(gam), 0.02, 0.55))
            sI = float(np.clip(np.sum(gam * r2) / max(np.sum(gam), 1.0) - s0, 5.0 * s0, 1e5))
        v_diag = s0 + gam * sI
        xh = full_cov_ep_oamp(y, A, np.diag(v_diag), const, pil_idx, x_pil, n_iters=6, damp=0.65)
    return xh


def rx_hmm_innov_fullcov(y, A, G, sigma0_sq, const, pil_idx, x_pil, p01, p10, sigma_I_sq, n_outer=8, reg=0.05):
    """Sol's deadliest colored-burst Steelman: deconvolved innovation-domain HMM + exact C_hat = s0 I + G diag(v) G^H."""
    N = len(y)
    I_N = np.eye(N, dtype=np.complex128)
    GtG = G.conj().T @ G
    W_dec = np.linalg.solve(GtG + reg * I_N, G.conj().T)
    bg_var = np.real(np.sum(np.abs(W_dec) ** 2, axis=1)) * sigma0_sq
    sig_gain = np.maximum(np.real(np.diag(W_dec @ G)) ** 2, 0.25)

    xh = rx_huber_oamp(y, A, sigma0_sq, const, pil_idx, x_pil, n_outer=2)
    x_lmmse_last = xh
    for outer in range(n_outer):
        r = y - A @ xh
        e_hat = W_dec @ r
        e2 = np.abs(e_hat) ** 2
        # Adaptive residual error floor
        extra = 0.025 if outer < 2 else (0.005 if outer < 4 else 0.001)
        s0_v = np.maximum(bg_var + extra, 1e-4)
        s1_v = s0_v + sig_gain * sigma_I_sq
        ll0 = -np.log(s0_v) - e2 / s0_v
        ll1 = -np.log(s1_v) - e2 / s1_v
        gam = hmm_fb_2state(ll0, ll1, p01, p10)
        v_hat = gam * sigma_I_sq
        C_hat = sigma0_sq * I_N + (G * v_hat[None, :]) @ G.conj().T
        if outer == n_outer - 1:
            x_lmmse_last = full_cov_lmmse(y, A, C_hat, pil_idx, x_pil)
        xh = full_cov_ep_oamp(y, A, C_hat, const, pil_idx, x_pil, n_iters=8, damp=0.65)
    return x_lmmse_last, xh


def rx_joint_sparse_l1_oamp(y, A, G, sigma0_sq, const, pil_idx, x_pil, n_outer=8):
    """
    EXTRA RUTHLESS STEELMAN (Convex Joint Sparse Pre-Filter Outlier + Symbol Recovery!):
    Solves min_{x, e} ||y - A x - G e||_2^2 + lam ||e||_1 via alternating FISTA/ISTA on e_pre + exact QAM EP on y - G e!
    Notice: Because G is KNOWN, joint sparse estimation of pre-filter e_pre directly exploits the low-dimensional
    pre-filter impulse support WITHOUT needing to invert G!
    """
    N = len(y)
    I_N = np.eye(N, dtype=np.complex128)
    L_g = float(np.linalg.norm(G, ord=2) ** 2) + 1e-9
    step = 1.0 / L_g
    # Universal threshold for sparse pre-filter impulse in background noise sigma0_sq
    lam = 2.6 * math.sqrt(sigma0_sq * math.log(N))
    e_hat = np.zeros(N, dtype=np.complex128)
    xh = rx_huber_oamp(y, A, sigma0_sq, const, pil_idx, x_pil, n_outer=2)
    for outer in range(n_outer):
        r = y - A @ xh
        # 25 FISTA steps for min_e 0.5 ||r - G e||^2 + lam ||e||_1 (group-l2 per complex entry)
        z = e_hat.copy()
        tk = 1.0
        for _ in range(25):
            grad = G.conj().T @ (G @ z - r)
            v = z - step * grad
            mag = np.abs(v)
            e_new = np.where(mag > step * lam, v * (1.0 - step * lam / np.maximum(mag, 1e-12)), 0.0)
            tk_new = 0.5 * (1.0 + math.sqrt(1.0 + 4.0 * tk * tk))
            z = e_new + ((tk - 1.0) / tk_new) * (e_new - e_hat)
            e_hat = e_new
            tk = tk_new
        # Identify active outlier indices -> inflate variance in C_hat (de-biased! Never subtract biased L1 e_hat alone!)
        active = np.abs(e_hat) > 1.5 * math.sqrt(sigma0_sq)
        v_hat = np.where(active, np.maximum(np.abs(e_hat) ** 2, 100.0 * sigma0_sq), 0.0)
        C_hat = sigma0_sq * I_N + (G * v_hat[None, :]) @ G.conj().T
        xh = full_cov_ep_oamp(y, A, C_hat, const, pil_idx, x_pil, n_iters=8, damp=0.65)
    return xh


def rx_prefilter_sbl_fullcov_oamp(y, A, G, sigma0_sq, const, pil_idx, x_pil, pattern_coupled=True, n_outer=10):
    """
    ULTIMATE TEXTBOOK BAYESIAN STEELMAN (Pre-Filter SBL / Pattern-Coupled Block-SBL + Full-Cov OAMP!):
    Directly estimates pre-filter impulse variance vector gamma = [v_0, ..., v_{N-1}] in:
      y = A x + G e + w,   e ~ CN(0, diag(gamma)),   w ~ CN(0, sigma0_sq I)
    WITHOUT inverting G! Exact EM M-step on r = y - A x_hat:
      Sigma_e = (diag(1/gamma) + (1/sigma0_sq) G^H G)^{-1}
      mu_e    = (1/sigma0_sq) Sigma_e G^H r
      gamma_n <- |mu_e[n]|^2 + Sigma_e[n, n]  (for pattern-coupled Block-SBL: locally coupled across [n-1, n, n+1]!)
    Then plugs C_hat = sigma0_sq I + G diag(gamma) G^H into exact full-covariance OAMP!
    """
    N = len(y)
    I_N = np.eye(N, dtype=np.complex128)
    GtG = G.conj().T @ G
    Gt = G.conj().T

    # Initial warm-start via Huber OAMP
    xh = rx_huber_oamp(y, A, sigma0_sq, const, pil_idx, x_pil, n_outer=2)
    gamma = np.full(N, 10.0 * sigma0_sq, dtype=float)
    inv_s0 = 1.0 / max(sigma0_sq, 1e-6)

    for outer in range(n_outer):
        r = y - A @ xh
        # Run 3 inner SBL-EM updates of pre-filter variance gamma for current residual r
        s0_eff = sigma0_sq + (0.02 if outer < 2 else (0.004 if outer < 4 else 0.0005))
        inv_s0_e = 1.0 / s0_eff
        for _ in range(3):
            # Exact posterior of e given r: Precision = diag(1/gamma) + (1/s0_eff) G^H G
            P_e = inv_s0_e * GtG.copy()
            P_e[np.diag_indices(N)] += 1.0 / np.maximum(gamma, 1e-8)
            p_fac = cho_factor(P_e + 1e-10 * I_N, lower=True)
            mu_e = cho_solve(p_fac, inv_s0_e * (Gt @ r))
            Sig_e_diag = np.maximum(np.real(np.diag(cho_solve(p_fac, I_N))), 0.0)
            m2 = np.abs(mu_e) ** 2 + Sig_e_diag
            if pattern_coupled:
                # Pattern-Coupled SBL (Fang TSP'15 / Zhang-Yin WCL'26): neighbor-coupled burst prior!
                m2_pad = np.pad(m2, 1, mode="edge")
                # Smoothly couple neighbors with beta=0.45
                m2_coup = (0.45 * m2_pad[:-2] + m2_pad[1:-1] + 0.45 * m2_pad[2:]) / 1.9
                gamma = np.clip(m2_coup, 1e-7, 1e5)
            else:
                gamma = np.clip(m2, 1e-7, 1e5)
            # Prune tiny noise-level gammas to 0 so background covariance stays clean
            gamma = np.where(gamma < 1.5 * s0_eff, 1e-7, gamma)

        C_hat = sigma0_sq * I_N + (G * gamma[None, :]) @ G.conj().T
        xh = full_cov_ep_oamp(y, A, C_hat, const, pil_idx, x_pil, n_iters=8, damp=0.65)
    return xh


def run_trial(args):
    seed, regime, waveform, N, snr_db, inr_db, duty, mean_burst, pilot_frac = args
    rng = np.random.default_rng(seed)
    const = gray_qam(16)
    P = 4; l_max = 6; k_max = 1.5
    sigma0_sq = 10.0 ** (-snr_db / 10.0)

    if waveform == "AFDM":
        c1 = (2 * math.ceil(k_max) + 1) / (2.0 * N)
        U = daft_mat(N, c1, 1.0 / (2.0 * math.pi * N))
        cpp_c1 = c1
    elif waveform == "OTFS":
        U = otfs_mat(16, N // 16)
        cpp_c1 = 0.0
    else:
        U = scfde_mat(N)
        cpp_c1 = 0.0

    colored = (regime != "R4_IID_Control")
    G = build_rx_filter_matrix(N, colored=colored, bw_factor=0.42)
    H_td, _ = build_td_channel(N, P, l_max, k_max, rng, cpp_c1=cpp_c1)
    A_true = H_td @ U.conj().T

    n_pil = int(round(N * pilot_frac))
    if n_pil > 0:
        pil_idx = np.unique(np.linspace(0, N - 1, n_pil, dtype=int))
        data_mask = np.ones(N, dtype=bool); data_mask[pil_idx] = False
        data_idx = np.where(data_mask)[0]
    else:
        pil_idx = np.array([], dtype=int)
        data_idx = np.arange(N, dtype=int)

    x_true = const[rng.integers(0, len(const), size=N)]
    x_pil = x_true[pil_idx] if len(pil_idx) > 0 else np.array([], dtype=np.complex128)
    w_bg = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sigma0_sq / 2.0)

    if regime.startswith("R3_AlphaStable"):
        gamma_scale = math.sqrt(sigma0_sq / 2.0) * 1.15
        e_pre, v_z = gen_alpha_stable_noise(N, alpha=1.45, gamma_scale=gamma_scale, rng=rng)
        p01, p10 = 0.03, 0.14
        sigma_I_sq = sigma0_sq * (10.0 ** (inr_db / 10.0))
    else:
        e_pre, states, v_z, mstats = gen_markov_burst_noise(N, sigma0_sq, duty, mean_burst, inr_db, rng)
        p01, p10, sigma_I_sq = mstats["p01"], mstats["p10"], mstats["sigma_I_sq"]

    y = A_true @ x_true + G @ e_pre + w_bg
    y_clean = A_true @ x_true + w_bg
    I_N = np.eye(N, dtype=np.complex128)
    C_true = sigma0_sq * I_N + (G * v_z[None, :]) @ G.conj().T

    res = {}
    avg_var = sigma0_sq + duty * sigma_I_sq
    res["Pub_Gaussian_LMMSE"] = hard_ser_sub(full_cov_lmmse(y, A_true, avg_var * I_N, pil_idx, x_pil), x_true, const, data_idx)
    res["Pub_Long_iidEP"] = hard_ser_sub(rx_iid_bg_oamp(y, A_true, sigma0_sq, const, pil_idx, x_pil, duty, sigma_I_sq, True, 7), x_true, const, data_idx)
    res["SM_ZMNL_ClipLMMSE"] = hard_ser_sub(rx_zmnl(y, A_true, sigma0_sq, const, pil_idx, x_pil), x_true, const, data_idx)
    res["SM_Huber_IRLS_OAMP"] = hard_ser_sub(rx_huber_oamp(y, A_true, sigma0_sq, const, pil_idx, x_pil, 6), x_true, const, data_idx)
    res["SM_iidBG_EM_OAMP"] = hard_ser_sub(rx_iid_bg_oamp(y, A_true, sigma0_sq, const, pil_idx, x_pil, 0.15, sigma_I_sq, False, 7), x_true, const, data_idx)
    xl_hmm, xo_hmm = rx_hmm_innov_fullcov(y, A_true, G, sigma0_sq, const, pil_idx, x_pil, p01, p10, sigma_I_sq, 8, reg=0.05)
    res["SM_HMM_Innov_FullCovLMMSE"] = hard_ser_sub(xl_hmm, x_true, const, data_idx)
    res["SM_HMM_Innov_FullCovOAMP"] = hard_ser_sub(xo_hmm, x_true, const, data_idx)
    res["SM_JointSparseL1_FullCovOAMP"] = hard_ser_sub(rx_joint_sparse_l1_oamp(y, A_true, G, sigma0_sq, const, pil_idx, x_pil, 8), x_true, const, data_idx)
    res["SM_PreFilter_SBL_OAMP"] = hard_ser_sub(rx_prefilter_sbl_fullcov_oamp(y, A_true, G, sigma0_sq, const, pil_idx, x_pil, False, 10), x_true, const, data_idx)
    res["SM_PreFilter_PCBlockSBL_OAMP"] = hard_ser_sub(rx_prefilter_sbl_fullcov_oamp(y, A_true, G, sigma0_sq, const, pil_idx, x_pil, True, 10), x_true, const, data_idx)

    res["Oracle_TrueState_LMMSE"] = hard_ser_sub(full_cov_lmmse(y, A_true, C_true, pil_idx, x_pil), x_true, const, data_idx)
    res["Oracle_TrueState_OAMP"] = hard_ser_sub(full_cov_ep_oamp(y, A_true, C_true, const, pil_idx, x_pil, 12, 0.65), x_true, const, data_idx)
    res["Ref_Clean_OAMP"] = hard_ser_sub(full_cov_ep_oamp(y_clean, A_true, sigma0_sq * I_N, const, pil_idx, x_pil, 8, 0.65), x_true, const, data_idx)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c3_bursty_impulsive.json")
    args = ap.parse_args()
    t0 = time.time()

    configs = [
        # (regime, wf, N, snr_db, inr_db, duty, mean_burst, pilot_frac)
        ("R1a_Burst15_SNR26_Load80", "AFDM", 128, 26.0, 25.0, 0.15, 7.0, 0.20),
        ("R1a_Burst15_SNR26_Load80", "OTFS", 128, 26.0, 25.0, 0.15, 7.0, 0.20),
        ("R1a_Burst15_SNR26_Load80", "SC-FDE", 128, 26.0, 25.0, 0.15, 7.0, 0.20),
        ("R1b_Burst20_SNR28_Load80", "AFDM", 128, 28.0, 25.0, 0.20, 8.0, 0.20),
        ("R3_AlphaStable_SNR26_Load80", "AFDM", 128, 26.0, 25.0, 0.15, 7.0, 0.20),
        ("R4_IID_Control", "AFDM", 128, 26.0, 25.0, 0.15, 7.0, 0.20),
    ]
    summary = {"meta": {"trials": args.trials}, "results": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, cfg in enumerate(configs):
            key = f"{cfg[0]}__{cfg[1]}"
            jobs = [(110000 + i * 1000 + t,) + cfg for t in range(args.trials)]
            outs = list(ex.map(run_trial, jobs))
            agg = {k: {"mean": float(np.mean([o[k] for o in outs])), "se": float(np.std([o[k] for o in outs], ddof=1) / math.sqrt(len(outs)))} for k in outs[0]}
            summary["results"][key] = agg
            best_sm_k = min((k for k in agg if k.startswith("SM_")), key=lambda k: agg[k]["mean"])
            best_sm = agg[best_sm_k]["mean"]
            orac = agg["Oracle_TrueState_OAMP"]["mean"]
            print(f"\n=== {key} (n={args.trials}) ===")
            for k, v in agg.items():
                print(f"  {k:30s}: SER = {v['mean']:.5f} +/- {v['se']:.5f}")
            print(f"  --> Best_SM ({best_sm_k}) = {best_sm:.5f} vs Oracle_OAMP = {orac:.5f} | Ratio = {best_sm/max(orac,1e-6):.2f}x")
    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to {args.out} in {summary['elapsed_sec']}s.")


if __name__ == "__main__":
    main()
