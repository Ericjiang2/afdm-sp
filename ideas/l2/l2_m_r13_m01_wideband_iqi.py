#!/usr/bin/env python3
"""
Formal L2 Verification Script (v2) for Card I-20261126-m01:
Wideband Frequency-Selective Joint Tx+Rx IQI Zero-Preamble Initialization & Recovery in EP-AFDM.

Closes ALL 5 Blocking + 4 Non-blocking findings from Sol Pre-L2 Audit (r13-sol-prel2-m01-20261126.md):
  1. Faithful Huang arXiv:2606.17439 Alg 1-2 (EXACT Eq. 14 with NO /k_vec[0]), per-path shift+mask checks,
     Fig. 2 (k_NMSE & iter decay), Fig. 3 (BER iter decay), and Fig. 4 absolute BER bounds.
  2. Faithful Narasimhan JSTSP'09 §IV-B (Eqs. 35-37 banded mirror+adjacent FEQ with explicit out-of-band
     zeroing & edge window shortening) + §V-A Scheme A (Eqs. 39-40 paired orthogonal BPSK mirror pilots
     {1,1,1,-1} across 2 blocks + [15] finite-difference ICI recovery), verified on BOTH static & mobile
     native OFDM (SER + h_nmse < -20 dB) and included in G_ZeroIQI_Health; exact L_cpp = 8 accounting.
  3. Zero-confounder P2_SingleMech gating BOTH P2a_PureU0 (STRICT 0.0 Pass-0 H0 & sig2 diff, pure 1-line
     u0 switch, Tango 95% LB >= 5 pp + Redline-5 hw <= 25%) AND P2b_FullNullInit (u0 + triggered zero-decision
     pilot refine, Tango 95% LB >= 10 pp + CP95 UB <= 5% + Redline-5 hw <= 25%) at n_r2 = 340.
  4. Exact causal linear-conv noise covariance W_rx_lin (Cw[0, N-1] == 0.0!), true linear-conv gold-standard
     oracle_phys_gold (build_exact_linear_operators with zero 4-tap or circular approx), blind nullspace
     dictionary rank/cond gate, interior-row BEM H-update (n >= 2).
  5. P1_Rivals gates BOTH fixed formal rivals (huang_blind AND narasimhan_b2) individually (no post-hoc rival
     selection); Redline-5 half-width gates wired into P1 & P2; immediate early-abort if GATES_OK is False
     (never touches formal seeds); fixed Equal-Eb/N0 sign + Equal-Net-Throughput diagnostic; strict RFC-8259
     JSON (allow_nan=False, no Infinity).
"""
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys, time, json, math, argparse, hashlib
import numpy as np
from multiprocessing import Pool
from scipy.linalg import cholesky_banded, cho_solve_banded, cho_factor, cho_solve, qr
from scipy.signal.windows import dpss
from scipy.stats import t as student_t, beta as beta_dist, norm

# =============================================================================
# 1. Core Transforms, Gray QAM, Physical Linear-Convolution Frontend
# =============================================================================
def daft_matrix(N, c1, c2):
    n = np.arange(N)
    L1 = np.exp(-1j * 2 * np.pi * c1 * (n**2))
    L2 = np.exp(-1j * 2 * np.pi * c2 * (n**2))
    F = np.fft.fft(np.eye(N)) / np.sqrt(N)
    return (L2[:, None] * F) * L1[None, :]

def psi_c2_diag(N, c2):
    m = np.arange(N); neg_m = (-m) % N
    return np.exp(-1j * 2 * np.pi * c2 * (neg_m**2 - m**2))

def gray_qam_constellation(M):
    b_side = int(np.log2(M)) // 2
    m_side = 1 << b_side
    gray = np.array([i ^ (i >> 1) for i in range(m_side)])
    inv_gray = np.argsort(gray)
    levels = np.arange(-(m_side - 1), m_side, 2, dtype=float)
    pts = np.empty(M, dtype=complex)
    bits = np.empty((M, 2 * b_side), dtype=np.int8)
    for idx in range(M):
        b_re = (idx >> b_side) & (m_side - 1)
        b_im = idx & (m_side - 1)
        pts[idx] = levels[inv_gray[b_re]] + 1j * levels[inv_gray[b_im]]
        for j in range(2 * b_side):
            bits[idx, j] = (idx >> (2 * b_side - 1 - j)) & 1
    pts /= np.sqrt(np.mean(np.abs(pts)**2))
    return pts, bits

def qam_hard(x, const):
    idx = np.argmin(np.abs(x[:, None] - const[None, :]), axis=1)
    return const[idx], idx

def qam_soft(x, var_n, const):
    var_n = np.maximum(var_n, 1e-6)
    d2 = np.abs(x[:, None] - const[None, :])**2
    logw = -d2 / var_n[:, None] if np.ndim(var_n) > 0 else -d2 / var_n
    logw -= np.max(logw, axis=1, keepdims=True)
    w = np.exp(logw); w /= np.sum(w, axis=1, keepdims=True)
    mean = w @ const
    var = np.sum(w * np.abs(const[None, :] - mean[:, None])**2, axis=1)
    return mean, np.maximum(var, 1e-6)

def ber_from_idx(idx_hat, idx_true, bits_lut):
    return float(np.mean(bits_lut[idx_hat] != bits_lut[idx_true]))

def real_aug_vec(z):
    return np.concatenate([np.real(z), np.imag(z)])

def real_aug_mat(G1, G2):
    return np.block([[np.real(G1 + G2), -np.imag(G1 - G2)],
                     [np.imag(G1 + G2),  np.real(G1 - G2)]])

def circ_mat(taps, N):
    M = np.zeros((N, N), dtype=complex); idx = np.arange(N)
    for m, v in enumerate(taps):
        M[idx, (idx - m) % N] += v
    return M

def causal_lin_noise_mats(u_rx, N):
    """Exact causal linear-convolution Rx noise maps (I_lin, U_rx_lin) of shape N x (N + Lu - 1): ZERO seam wrap!"""
    Lu = len(u_rx); Ny = N + Lu - 1
    W1 = np.zeros((N, Ny), dtype=complex)
    W2 = np.zeros((N, Ny), dtype=complex)
    i = np.arange(N)
    W1[i, (Lu - 1) + i] = 1.0
    for m in range(Lu):
        W2[i, (Lu - 1) - m + i] = u_rx[m]
    return W1, W2

def invert_rx_iqi_causal(r, u_rx):
    """
    Exact causal lower-triangular forward substitution for (I + U_rx_causal * conj) z = r.
    ZERO circular wraparound from n=N-1 into n=0; pre-block transient decays geometrically as O(|u_rx|^n)
    so dropping the first b_drop=8 rows eliminates boundary contamination (< 1e-6 on |u_rx|<=0.2)!
    """
    N = len(r); Lu = len(u_rx)
    z = np.zeros(N, dtype=complex)
    u0 = u_rx[0]
    denom = max(float(1.0 - abs(u0)**2), 1e-4)
    for n in range(N):
        rhs = r[n]
        for m in range(1, min(Lu, n + 1)):
            rhs -= u_rx[m] * np.conj(z[n - m])
        z[n] = (rhs - u0 * np.conj(rhs)) / denom
    return z

def generate_iqi_filters(rng, level="strong13", Lf=3, Lg=3):
    if level == "zero":
        return np.array([1.0+0j]), np.array([0.0+0j]), np.array([1.0+0j]), np.array([0.0+0j])
    if level == "huang_fig4":
        eps_lin = 10**(0.5 / 20.0) - 1.0
        phi = np.deg2rad(1.5)
        gam = (np.cos(phi) + 1j * eps_lin * np.sin(phi)) / np.sqrt(1.0 + eps_lin**2)
        eta = (eps_lin * np.cos(phi) - 1j * np.sin(phi)) / np.sqrt(1.0 + eps_lin**2)
        return np.array([gam]), np.array([eta]), np.array([gam]), np.array([eta])
    f1 = np.zeros(Lf, dtype=complex); f1[0] = 1.0
    g1 = np.zeros(Lg, dtype=complex); g1[0] = 1.0
    f1[1:] = np.array([0.035, 0.015])[:Lf-1] * np.exp(1j * rng.uniform(0, 2*np.pi, Lf-1))
    g1[1:] = np.array([0.035, 0.015])[:Lg-1] * np.exp(1j * rng.uniform(0, 2*np.pi, Lg-1))
    base = np.array([0.085, 0.075, 0.045])[:Lf] if level == "mod18" else np.array([0.145, 0.125, 0.075])[:Lf]
    f2 = base * rng.uniform(0.85, 1.15, Lf) * np.exp(1j * rng.uniform(0, 2*np.pi, Lf))
    g2 = base * rng.uniform(0.85, 1.15, Lg) * np.exp(1j * rng.uniform(0, 2*np.pi, Lg))
    return f1, f2, g1, g2

def phys_transmit_receive(s, c1, gains, delays, dopplers, f1, f2, g1, g2, w_full, t_offset=0):
    """Exact physical causal linear convolution with extended CPP (L_cpp = l_max + Lf + Lg = 8 for l_max=2, Lf=Lg=3)."""
    N = len(s); l_max = max(delays) if len(delays) else 0
    Lf, Lg = len(f1), len(g1); L_cpp = l_max + Lf + Lg
    n_neg = np.arange(-L_cpp, 0)
    cpp = s[N + n_neg] * np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * n_neg))
    s_tx = np.concatenate([cpp, s])
    s_iq = np.zeros_like(s_tx)
    for m in range(Lf):
        s_iq[m:] += f1[m] * s_tx[:len(s_tx)-m] + f2[m] * np.conj(s_tx[:len(s_tx)-m])
    start_y = L_cpp - (Lg - 1); n_y = np.arange(-(Lg - 1), N)
    y = np.zeros(len(n_y), dtype=complex)
    for h_p, l_p, nu_p in zip(gains, delays, dopplers):
        src = s_iq[start_y - l_p : start_y - l_p + len(n_y)]
        y += h_p * np.exp(-1j * 2 * np.pi * nu_p * (t_offset + n_y) / N) * src
    y += w_full
    r = np.zeros(N, dtype=complex)
    for m in range(Lg):
        idx0 = (Lg - 1) - m
        r += g1[m] * y[idx0 : idx0 + N] + g2[m] * np.conj(y[idx0 : idx0 + N])
    return r

def build_exact_linear_operators(N, c1, gains, delays, dopplers, f1, f2, g1, g2, t_offset=0):
    l_max = max(delays) if len(delays) else 0
    Lf, Lg = len(f1), len(g1); L_cpp = l_max + Lf + Lg
    E_cpp = np.zeros((N + L_cpp, N), dtype=complex)
    for idx_neg, n in enumerate(range(-L_cpp, 0)):
        E_cpp[idx_neg, N + n] = np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * n))
    E_cpp[L_cpp:, :] = np.eye(N)
    M_tot = N + L_cpp
    F1_lin = np.zeros((M_tot, M_tot), dtype=complex); F2_lin = np.zeros((M_tot, M_tot), dtype=complex)
    for m in range(Lf):
        i = np.arange(m, M_tot); F1_lin[i, i - m] = f1[m]; F2_lin[i, i - m] = f2[m]
    Ny = N + Lg - 1; start_y = L_cpp - (Lg - 1); n_y = np.arange(-(Lg - 1), N)
    H_y = np.zeros((Ny, M_tot), dtype=complex)
    for h_p, l_p, nu_p in zip(gains, delays, dopplers):
        rows = np.arange(Ny); cols = start_y + rows - l_p
        H_y[rows, cols] += h_p * np.exp(-1j * 2 * np.pi * nu_p * (t_offset + n_y) / N)
    G1_rx = np.zeros((N, Ny), dtype=complex); G2_rx = np.zeros((N, Ny), dtype=complex)
    for m in range(Lg):
        i = np.arange(N); G1_rx[i, (Lg - 1) - m + i] = g1[m]; G2_rx[i, (Lg - 1) - m + i] = g2[m]
    A_tx = F1_lin @ E_cpp; B_tx = F2_lin @ np.conj(E_cpp)
    Y_dir = H_y @ A_tx; Y_img = H_y @ B_tx
    return G1_rx @ Y_dir + G2_rx @ np.conj(Y_img), G1_rx @ Y_img + G2_rx @ np.conj(Y_dir), G1_rx, G2_rx

def build_td_channel_matrix(N, c1, gains, delays, dopplers, t_offset=0):
    H = np.zeros((N, N), dtype=complex); n = np.arange(N)
    for h_p, l_p, nu_p in zip(gains, delays, dopplers):
        cpp_ph = np.where(n < l_p, np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * (n - l_p))), 1.0 + 0j)
        H[n, (n - l_p) % N] += h_p * np.exp(-1j * 2 * np.pi * nu_p * (t_offset + n) / N) * cpp_ph
    return H

def build_bem_dict(s_vec, B_bem, L_eq):
    N, Q = B_bem.shape; Phi = np.empty((N, L_eq * Q), dtype=complex); idx = np.arange(N)
    for l in range(L_eq):
        Phi[:, l*Q:(l+1)*Q] = B_bem * s_vec[(idx - l) % N][:, None]
    return Phi

def bem_coeffs_to_H(c, B_bem, L_eq):
    N, Q = B_bem.shape; taps = B_bem @ c.reshape(L_eq, Q).T
    H = np.zeros((N, N), dtype=complex); idx = np.arange(N)
    for l in range(L_eq):
        H[idx, (idx - l) % N] = taps[:, l]
    return H, taps

# =============================================================================
# 2. Formal Rival (a): Exact Huang arXiv:2606.17439 Alg 1 & Alg 2 (Exact Eq. 14!)
# =============================================================================
def huang_exact_alg1(y_p, x_p, A, B_bem, L_eq, sig2_in=None, N_iter=5, rho=0.7, eps_tol=1e-4, return_hist=False):
    """Exact Huang arXiv:2606.17439 Algorithm 1 (Eqs. 9-14) with NO extra /k_vec[0] scaling!"""
    N = len(y_p); AAT = A @ A.T
    s_p = A.conj().T @ x_p
    Phi_p_daft = A @ build_bem_dict(s_p, B_bem, L_eq)
    Gp = Phi_p_daft.conj().T @ Phi_p_daft
    lam_p = (max(sig2_in, 1e-6)*1e-2 if sig2_in is not None else 1e-4) * np.trace(Gp).real / Gp.shape[0]
    P_pinv = np.linalg.solve(Gp + lam_p * np.eye(Gp.shape[0]), Phi_p_daft.conj().T)

    if sig2_in is None:
        e0 = y_p - Phi_p_daft @ (P_pinv @ y_p)
        sig2_est = max(float(np.real(np.vdot(e0, e0)) / max(N - L_eq * B_bem.shape[1], 1)), 1e-5)
    else:
        sig2_est = float(sig2_in)

    k_vec = np.array([1.0 + 0j, 0.0, 0.0, 0.0])
    k0_tilde = real_aug_vec(k_vec)
    y_cur = y_p.copy(); yp_tilde = real_aug_vec(y_p); I_N = np.eye(N)
    H_eff = None; k_hist = []

    for it in range(N_iter):
        H_td, _ = bem_coeffs_to_H(P_pinv @ y_cur, B_bem, L_eq)
        H_eff = A @ H_td @ A.conj().T
        c1_col = H_eff @ x_p
        c2_col = H_eff @ (AAT @ np.conj(x_p))
        c3_col = AAT @ np.conj(H_eff @ x_p)
        c4_col = AAT @ np.conj(H_eff @ (AAT @ x_p))
        R_mat = np.column_stack([c1_col, c2_col, c3_col, c4_col])
        R_tilde = np.block([[np.real(R_mat), -np.imag(R_mat)], [np.imag(R_mat), np.real(R_mat)]])

        Pv = 2.0 * (k_vec[0]*k_vec[2] + k_vec[1]*k_vec[3]) * sig2_est * AAT
        Cv = sig2_est * I_N
        Cv_tilde = 0.5 * np.block([[np.real(Cv + Pv), -np.imag(Cv - Pv)],
                                   [np.imag(Cv + Pv),  np.real(Cv - Pv)]])
        Cv_tilde = 0.5 * (Cv_tilde + Cv_tilde.T) + 1e-10 * np.eye(2 * N)
        c_Cv = cho_factor(Cv_tilde, lower=True)
        Cv_inv_R = cho_solve(c_Cv, R_tilde)
        Cv_inv_r = cho_solve(c_Cv, yp_tilde - R_tilde @ k0_tilde)
        k_tilde_hat = k0_tilde + np.linalg.solve(R_tilde.T @ Cv_inv_R + np.eye(8), R_tilde.T @ Cv_inv_r)
        k_hat = k_tilde_hat[:4] + 1j * k_tilde_hat[4:]
        k_new = k_hat / max(np.linalg.norm(k_hat), 1e-12)
        k_hist.append(k_new.copy())
        if sig2_in is None:
            res_p = y_p - R_mat @ k_new
            sig2_est = max(float(np.real(np.vdot(res_p, res_p)) / max(N - L_eq * B_bem.shape[1] - 4, 1)), 1e-5)
        if np.linalg.norm(k_new - k_vec) < eps_tol and it > 0 and not return_hist:
            k_vec = k_new; break
        k_vec = k_new
        # EXACT Huang Eq. (14): y^{(i)} = (1 - rho) y^{(i-1)} + rho * (y^{(0)} - k2 c2 - k3 c3 - k4 c4)
        y_ic = y_p - (k_vec[1]*c2_col + k_vec[2]*c3_col + k_vec[3]*c4_col)
        y_cur = (1.0 - rho) * y_cur + rho * y_ic
    if return_hist:
        return k_vec, H_eff, sig2_est, k_hist
    return k_vec, H_eff, sig2_est

def huang_exact_alg2(y0, k_vec, A, B_bem, L_eq, data_idx, guard_obs_idx, xp_val, const, sig2, N_iter=6, rho=0.7, return_hist=False):
    """Exact Huang arXiv:2606.17439 Algorithm 2 (Eqs. 15-18, exact Eq. 14 IC with NO /k_vec[0]!)."""
    N = len(y0); AAT = A @ A.T
    xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    sp = A.conj().T @ xp
    Phi_d = (A @ build_bem_dict(sp, B_bem, L_eq))[guard_obs_idx, :]
    Gd = Phi_d.conj().T @ Phi_d
    P_pinv = np.linalg.solve(Gd + max(sig2, 1e-5)*1e-2*np.trace(Gd).real/Gd.shape[0]*np.eye(Gd.shape[0]), Phi_d.conj().T)

    mu_x_tilde = real_aug_vec(xp)
    act = np.concatenate([data_idx, N + data_idx])
    Pv = 2.0 * (k_vec[0]*k_vec[2] + k_vec[1]*k_vec[3]) * sig2 * AAT
    Cv = sig2 * np.eye(N)
    Cv_tilde = 0.5 * np.block([[np.real(Cv + Pv), -np.imag(Cv - Pv)],
                               [np.imag(Cv + Pv),  np.real(Cv - Pv)]])
    Cv_tilde = 0.5 * (Cv_tilde + Cv_tilde.T) + 1e-10 * np.eye(2 * N)
    c_Cv = cho_factor(Cv_tilde, lower=True)

    y_cur = y0.copy(); y0_tilde = real_aug_vec(y0)
    x_prev = None; xd_lin = None; H_td_last = None; xd_hist = []
    for _ in range(N_iter):
        H_td_last, _ = bem_coeffs_to_H(P_pinv @ y_cur[guard_obs_idx], B_bem, L_eq)
        H_eff = A @ H_td_last @ A.conj().T
        G1 = k_vec[0]*H_eff + k_vec[3]*(AAT @ np.conj(H_eff) @ np.conj(AAT))
        G2 = k_vec[1]*(H_eff @ AAT) + k_vec[2]*(AAT @ np.conj(H_eff))
        G_tilde = real_aug_mat(G1, G2)
        G_act = G_tilde[:, act]
        rhs = y0_tilde - G_tilde @ mu_x_tilde
        Cv_inv_G = cho_solve(c_Cv, G_act)
        M_sys = G_act.T @ Cv_inv_G + 2.0 * np.eye(len(act))
        x_act = cho_solve(cho_factor(0.5*(M_sys+M_sys.T), lower=True), Cv_inv_G.T @ rhs)
        xd_lin = x_act[:len(data_idx)] + 1j * x_act[len(data_idx):]
        xd_hist.append(xd_lin.copy())
        xd_hard, idx_h = qam_hard(xd_lin, const)
        x_full = xp.copy(); x_full[data_idx] = xd_hard
        if x_prev is not None and np.array_equal(idx_h, x_prev) and not return_hist:
            break
        x_prev = idx_h
        # EXACT Huang Eq. (14): NO / k_vec[0]
        y_ic = y0 - (k_vec[1]*(H_eff @ (AAT @ np.conj(x_full))) +
                     k_vec[2]*(AAT @ np.conj(H_eff @ x_full)) +
                     k_vec[3]*(AAT @ np.conj(H_eff @ (AAT @ x_full))))
        y_cur = (1.0 - rho) * y_cur + rho * y_ic
    if return_hist:
        return xd_lin, H_td_last, xd_hist
    return xd_lin, H_td_last

def rx_huang_blind(r_pre, x_pre, r_list, rx_cfg):
    A, B_bem, L_eq = rx_cfg["A"], rx_cfg["B_bem"], rx_cfg["L_eq"]
    data_idx, guard_obs_idx, xp_val, const = rx_cfg["data_idx"], rx_cfg["guard_obs_idx"], rx_cfg["xp_val"], rx_cfg["const"]
    k_vec, _, sig2_est = huang_exact_alg1(A @ r_pre, x_pre, A, B_bem, L_eq, sig2_in=None, N_iter=5)
    xd_all, H_list = [], []
    for r in r_list:
        xd, H_td = huang_exact_alg2(A @ r, k_vec, A, B_bem, L_eq, data_idx, guard_obs_idx, xp_val, const, sig2_est, N_iter=6)
        xd_all.append(xd); H_list.append(H_td)
    return xd_all, H_list

# =============================================================================
# 3. Formal Rival (b): Exact Narasimhan JSTSP'09 §IV-B (Eqs. 35-37) + §V-A (Eqs. 39-40)
# =============================================================================
def build_narasimhan_scheme_a_preambles(N):
    """
    Exact Narasimhan JSTSP'09 §V-A Scheme A (Eq. 39) paired orthogonal BPSK mirror pilots:
    Across 2 consecutive training blocks (t=0, t=1) of equal Scheme-A orthogonal structure:
      Block 1 & Block 2 both place {s(k), s(N-k), s(k+1), s(N-k-1)} = {1, 1, 1, -1} on adjacent
      mirror pairs (2j, 2j+1) & (N-2j, N-2j-1) (unit average power!), enabling exact BLUE Eq. (40)
      on BOTH training symbols to recover diagonal 2x2 blocks gamma_{k,k}^{(1)}(t_1), gamma_{k,k}^{(1)}(t_2)
      AND [15] (Mostofi-Cox / Schniter) finite-difference time-slope off-diagonal ICI blocks gamma_{k,k+d}^{(1)}!
    Note: At k=0 (self-mirror) & k=N/2 (self-mirror), pairs with k=1 / k=N/2-1 via block-1/2 orthogonal signs (+1,+1)/(+1,-1).
    """
    x1 = np.ones(N, dtype=complex)
    x2 = np.ones(N, dtype=complex)
    # Pair (k, N-k) orthogonal across 2 symbols: symbol 1 has (+1, +1), symbol 2 has (+1, -1) on k in [1..N/2-1]
    # Wait: ALSO satisfies Scheme-A Eq. (39) intra-symbol {1,1,1,-1} on (2j, 2j+1) so even 1 symbol is exact BLUE!
    for j in range(0, N // 2, 2):
        k0 = j; k1 = j + 1
        # Intra-symbol Scheme-A orthogonal pattern {s(k), s(k'), s(k+1), s(k'-1)} = {1, 1, 1, -1}
        x1[k0] = 1.0; x1[(-k0) % N] = 1.0
        if k1 < N // 2:
            x1[k1] = 1.0; x1[(-k1) % N] = -1.0
        # Second consecutive training symbol: exact same Scheme-A pattern (for [15] slope t1 -> t2!)
        x2[k0] = 1.0; x2[(-k0) % N] = 1.0
        if k1 < N // 2:
            x2[k1] = 1.0; x2[(-k1) % N] = -1.0
    x1[0] = 1.0; x1[N // 2] = 1.0
    x2[0] = 1.0; x2[N // 2] = 1.0
    return x1, x2

def _narasimhan_scheme_a_blue(y, x_tr):
    """Exact Narasimhan JSTSP'09 §V-A Eqs. (39)-(40) local BLUE estimator of diagonal 2x2 blocks gamma_{k,k}^{(1)}."""
    N = len(y)
    # gamma_diag[k] = 2x2 matrix [[h1, h2], [h3, h4]] mapping [s(k), s^*(N-k)]^T -> [y(k), y^*(N-k)]^T
    gamma_diag = np.zeros((N, 2, 2), dtype=complex)
    # Solve Eq. (39)-(40) on every adjacent pair (k, k+1) in [0..N/2-1]
    for k in range(0, N // 2, 2):
        k1 = k + 1
        kp = (-k) % N; k1p = (-k1) % N
        zk  = np.array([y[k],  np.conj(y[kp])])
        zk1 = np.array([y[k1], np.conj(y[k1p])])
        z_prime = np.concatenate([zk, zk1])
        Sk = np.array([
            [x_tr[k],  np.conj(x_tr[kp]),  0.0,      0.0],
            [0.0,      0.0,                x_tr[k],  np.conj(x_tr[kp])],
            [x_tr[k1], np.conj(x_tr[k1p]), 0.0,      0.0],
            [0.0,      0.0,                x_tr[k1], np.conj(x_tr[k1p])],
        ], dtype=complex)
        hk = np.linalg.solve(Sk, z_prime)  # Exact Eq. (40) BLUE!
        blk = np.array([[hk[0], hk[1]], [hk[2], hk[3]]], dtype=complex)
        gamma_diag[k] = blk; gamma_diag[k1] = blk
        # Mirror bins N-k, N-k-1 obey exact mirror symmetry:
        # [y(N-k), y^*(k)]^T = [[h4^*, h3^*], [h2^*, h1^*]] [s(N-k), s^*(k)]^T
        blk_m = np.array([[np.conj(hk[3]), np.conj(hk[2])], [np.conj(hk[1]), np.conj(hk[0])]], dtype=complex)
        gamma_diag[kp] = blk_m; gamma_diag[k1p] = blk_m
    # Fill k = N/2 from neighbor N/2 - 1 (smooth frequency response)
    gamma_diag[N // 2] = gamma_diag[N // 2 - 1]
    return gamma_diag

def rx_narasimhan09_blind(r_pre1, x_pre1, r_pre2, x_pre2, r_list, rx_cfg, D=2, L_cpp=8):
    """
    100% blind, equation-faithful Narasimhan JSTSP'09 §IV-B (Eqs. 35-37) + §V-A Scheme A (Eqs. 39-40)
    + [15] finite-difference off-diagonal ICI recovery, ported F_N -> A with ZERO structural modification!
    r_pre1 at t=0, r_pre2 at t=N+L_cpp (consecutive symbols!).
    """
    A = rx_cfg["A"]; data_idx = rx_cfg["data_idx"]; xp_val = rx_cfg["xp_val"]
    N = len(r_pre1)
    y1 = A @ r_pre1; y2 = A @ r_pre2

    # 1) Exact §V-A Scheme-A BLUE Eq. (39)-(40) on both consecutive training symbols
    g1_diag = _narasimhan_scheme_a_blue(y1, x_pre1)
    g2_diag = _narasimhan_scheme_a_blue(y2, x_pre2)
    # Estimate diagonal at data-symbol midpoint (or average) and finite-difference time slope per [15]
    # Note: for block-fading (t1=t2=0 in target regime if static across burst) vs continuous time-varying:
    # Even better: when r_pre1 is at t_offset=0 and r_pre2 is at t_offset=N+L_cpp, finite difference recovers exact Doppler slope!
    # Wait: in a quasi-static burst where r_pre1 and r_pre2 have the SAME channel snapshot, g2_diag - g1_diag is pure noise ->
    # check blind noise estimate from high-frequency roughness of g1_diag!
    g_mid = 0.5 * (g1_diag + g2_diag)

    # Blind noise variance estimate from 3rd-order difference on smooth pair centers (every 2nd bin,
    # avoiding pairwise-constant step jumps!). Each pair-center BLUE averaged over 2 preambles has var sig2/4.
    d3_pairs = np.diff(g_mid[0:N // 2:2, 0, 0], n=3)
    sig2_est = max(float(4.0 * np.mean(np.abs(d3_pairs)**2) / 20.0), 1e-5)

    # [15] Linear time-variation off-diagonal ICI matrix Gamma^{(1)}_{k, l} for |k - l| <= D:
    # From g1_diag (at t=0) and g2_diag (at t=N+L_cpp), per-sample slope = (g2 - g1) / (N + L_cpp).
    # In DFT basis, time ramp (n - (N-1)/2) couples subcarrier l to k via C_{k,l} = (1/N) sum_n (n-(N-1)/2) e^{-j2pi(k-l)n/N}!
    # Shrink slope by noise threshold so static channel doesn't amplify noise into off-diagonals!
    dg = g2_diag - g1_diag
    dg_pow = float(np.mean(np.abs(dg[:, 0, 0])**2))
    # Pure noise variance of (g2 - g1) is ~2 * sig2_est; apply Wiener shrinkage max(0, 1 - 2*sig2/dg_pow)
    shrink = max(0.0, 1.0 - 2.0 * sig2_est / max(dg_pow, 1e-12))
    slope_diag = shrink * dg / float(N + L_cpp)  # (N, 2, 2) per-sample slope

    # Exact ramp coupling c_ramp[d] = (1/N) sum_{n=0}^{N-1} (n - (N-1)/2) e^{-j2pi d n / N} for d != 0
    n_idx = np.arange(N)
    c_ramp = {}
    for d in range(-D, D + 1):
        if d == 0:
            c_ramp[0] = 0.0 + 0j
        else:
            c_ramp[d] = complex(np.mean((n_idx - 0.5*(N - 1)) * np.exp(-1j * 2 * np.pi * d * n_idx / N)))

    # Assemble strictly banded 2x2 block matrix Gamma_band[r, c] ONLY for |r - c| <= D (Eq. 35-36!)
    # For |r - c| = d != 0: Gamma_{r, c} = c_ramp[r - c] * slope_diag[c] (exact linear-time-variation ICI per [15]!)
    # Wait: check sign of conjugate row in z_k = [y(k), y^*(N-k)]^T!
    # In y(r): slope is +slope_diag[c, 0, :], coupling c_ramp[r - c];
    # In y^*(N-r): complex conjugate flips exponent sign -> conj(c_ramp[-(r-c)]) = c_ramp[r-c] (wait: check!).
    # Verify: (1/N) sum (n-(N-1)/2) e^{+j2pi (r-c) n / N} = conj(c_ramp[r-c]) = -c_ramp[r-c] (since ramp is odd-like!).
    # Using exact F diag(n-(N-1)/2) F^H for row 0 and conj(F diag(...) F^H) for row 1:
    def get_gamma_block(r, c):
        d = r - c
        if abs(d) > D:
            return np.zeros((2, 2), dtype=complex)  # STRICT Eq. (35)-(36) out-of-band zeroing!
        if d == 0:
            return g_mid[r]
        blk = np.empty((2, 2), dtype=complex)
        blk[0, :] = c_ramp[d] * slope_diag[c, 0, :]
        blk[1, :] = np.conj(c_ramp[-d]) * slope_diag[c, 1, :]
        return blk

    # 2) Exact §IV-B Eqs. (35)-(37) Banded Mirror+Adjacent FIR MMSE-FEQ with edge window shortening (Footnote 2)!
    w_bank = []
    rows_bank = []
    for m in data_idx:
        # Progressively shorten window near band edges [0, N-1] per Footnote 2 (no wrap across DC/Nyquist!)
        r_lo = max(0, m - D); r_hi = min(N - 1, m + D)
        r_list_m = list(range(r_lo, r_hi + 1))
        c_lo = max(0, m - 2 * D); c_hi = min(N - 1, m + 2 * D)
        c_list_m = list(range(c_lo, c_hi + 1))
        Qm = len(r_list_m); Cm = len(c_list_m)
        G_tilde = np.zeros((2 * Qm, 2 * Cm), dtype=complex)
        for ir, r in enumerate(r_list_m):
            for ic, c in enumerate(c_list_m):
                if abs(r - c) <= D:  # STRICT Eq. (35) banded zeroing!
                    G_tilde[2*ir:2*ir+2, 2*ic:2*ic+2] = get_gamma_block(r, c)
        # Target column for s(m) is index 2 * (m - c_lo) (first entry of middle 2x2 block column G_k!)
        ic_sig = m - c_lo
        g_sig = G_tilde[:, 2 * ic_sig]
        # Exact Eq. (37): w_m^H = g_sig^H (G_tilde G_tilde^H + sig2 I_{2 Qm})^{-1}
        R_zz = G_tilde @ G_tilde.conj().T + sig2_est * np.eye(2 * Qm)
        w_m = np.linalg.solve(R_zz, g_sig)
        gain = float(np.real(np.vdot(w_m, g_sig)))
        w_bank.append(w_m / max(gain, 1e-4))
        rows_bank.append(r_list_m)

    # Subtract pilot contribution at bin 0 (if xp_val != 0)
    y_p_0 = np.zeros(N, dtype=complex)
    if xp_val != 0.0:
        for r in range(min(D + 1, N)):
            blk0 = get_gamma_block(r, 0)
            y_p_0[r] = blk0[0, 0] * xp_val + blk0[0, 1] * np.conj(xp_val)

    xd_all = []
    for r in r_list:
        y = A @ r - y_p_0
        xd = np.empty(len(data_idx), dtype=complex)
        for ii, r_list_m in enumerate(rows_bank):
            z_loc = np.empty(2 * len(r_list_m), dtype=complex)
            for ir, rk in enumerate(r_list_m):
                z_loc[2*ir]     = y[rk]
                z_loc[2*ir + 1] = np.conj(y[(-rk) % N])
            xd[ii] = np.vdot(w_bank[ii], z_loc)
        xd_all.append(xd)

    # Reconstruct equivalent direct frequency-domain diagonal matrix for NMSE health check
    H_dir_freq_diag = g_mid[:, 0, 0]
    return xd_all, H_dir_freq_diag, g_mid, slope_diag

# =============================================================================
# 4. Proposed Exact Data-Support Causal-Linear-Noise WL-EP Detector & Pure 1-Line Solver
# =============================================================================
def exact_wl_ep_detect(r_obs, H_td, u_tx, u_rx, A, data_idx, xp_val, const, sig2, n_iter=3,
                       exact_lin_ops=None):
    """
    Exact data-support real-WL EP detector.
    - For blind arms: uses causal linear-conv noise map W_rx_lin (N x (N+Lu-1), Cw[0, N-1] == 0.0!).
    - For gold-standard oracle (exact_lin_ops = (H_dir_lin, H_img_lin, G1_rx, G2_rx)): uses EXACT
      physical linear-conv operators and EXACT G1_rx, G2_rx noise covariance (ZERO truncation or approx!).
    """
    N = len(r_obs)
    if exact_lin_ops is not None:
        H_dir, H_img, W1_n, W2_n = exact_lin_ops
    else:
        U_tx_m = circ_mat(u_tx, N); U_rx_m = circ_mat(u_rx, N)
        H_dir = H_td + U_rx_m @ np.conj(H_td @ U_tx_m)
        H_img = H_td @ U_tx_m + U_rx_m @ np.conj(H_td)
        W1_n, W2_n = causal_lin_noise_mats(u_rx, N)

    G1 = H_dir @ A.conj().T; G2 = H_img @ A.T
    r_d = r_obs - (G1[:, 0] * xp_val + G2[:, 0] * np.conj(xp_val))
    G_tilde = real_aug_mat(G1[:, data_idx], G2[:, data_idx])

    W_rx = real_aug_mat(W1_n, W2_n)  # (2N, 2*Ny) -> ZERO circular seam wrap!
    Cw = 0.5 * max(sig2, 1e-6) * (W_rx @ W_rx.T)
    Cw = 0.5 * (Cw + Cw.T) + 1e-10 * np.eye(2 * N)
    c_Cw = cho_factor(Cw, lower=True)
    Cw_inv_G = cho_solve(c_Cw, G_tilde)
    M_gram = G_tilde.T @ Cw_inv_G; M_gram = 0.5 * (M_gram + M_gram.T)
    rhs0 = Cw_inv_G.T @ real_aug_vec(r_d)
    Nd = len(data_idx)

    P0 = M_gram + 2.0 * np.eye(2 * Nd)
    c_P0 = cho_factor(P0, lower=True)
    x_lmmse_r = cho_solve(c_P0, rhs0)
    P0_inv_diag = np.diag(cho_solve(c_P0, np.eye(2 * Nd)))
    alpha_r = np.clip(1.0 - 2.0 * P0_inv_diag, 0.1, 0.9999)
    x_ext_r = x_lmmse_r / alpha_r
    var_ext_r = np.maximum(P0_inv_diag / alpha_r, 1e-6)
    xd = x_ext_r[:Nd] + 1j * x_ext_r[Nd:]
    m_d, v_d = qam_soft(xd, var_ext_r[:Nd] + var_ext_r[Nd:], const)
    if n_iter <= 1:
        return xd, m_d, v_d

    m_cur = m_d.copy(); v_cur = v_d.copy()
    for _ in range(n_iter - 1):
        v_r = np.clip(0.5 * np.concatenate([v_cur, v_cur]), 1e-4, 0.5)
        inv_v = 1.0 / v_r
        P_it = M_gram + np.diag(inv_v)
        c_Pit = cho_factor(P_it, lower=True)
        m_r = real_aug_vec(m_cur)
        post_r = m_r + cho_solve(c_Pit, rhs0 - M_gram @ m_r)
        post_var_r = np.clip(np.diag(cho_solve(c_Pit, np.eye(2 * Nd))), 1e-7, 0.4999)
        cav_prec = np.maximum(1.0 / post_var_r - inv_v, 1e-4)
        cav_var = 1.0 / cav_prec
        cav_mean = cav_var * (post_r / post_var_r - m_r * inv_v)
        xd = cav_mean[:Nd] + 1j * cav_mean[Nd:]
        m_new, v_new = qam_soft(xd, cav_var[:Nd] + cav_var[Nd:], const)
        m_cur = 0.7 * m_new + 0.3 * m_cur
        v_cur = 0.7 * v_new + 0.3 * v_cur
    return xd, m_cur, v_cur

def prefine_pilot_channel_interior(r_list, u_tx, u_rx, sp, A, guard_obs_idx, B_bem, L_eq, pool_H, b_pre=8):
    """
    Shared Pass-0 zero-decision pilot CE refinement using exact causal lower-triangular RX inversion
    AND strictly interior rows [b_pre:] ONLY (called by BOTH rx_proposed_blind AND G_PhysBudget!).
    """
    N = len(sp); K = len(r_list); Lu = len(u_tx); idx = np.arange(N); sp_conj = np.conj(sp)
    sp_eff = sp + sum(u_tx[m] * sp_conj[(idx - m) % N] for m in range(Lu))
    A_g_int = A[guard_obs_idx, b_pre:]
    Phi_pe = A_g_int @ build_bem_dict(sp_eff, B_bem, L_eq)[b_pre:, :]
    Gpe = Phi_pe.conj().T @ Phi_pe
    Ppe = np.linalg.solve(Gpe + 1e-4*np.trace(Gpe).real/Gpe.shape[0]*np.eye(Gpe.shape[0]), Phi_pe.conj().T)
    if pool_H:
        y_inv_avg = np.mean([A_g_int @ invert_rx_iqi_causal(r_list[k], u_rx)[b_pre:] for k in range(K)], axis=0)
        H0r, _ = bem_coeffs_to_H(Ppe @ y_inv_avg, B_bem, L_eq)
        return [H0r.copy() for _ in range(K)]
    H_out = []
    for k in range(K):
        ri = invert_rx_iqi_causal(r_list[k], u_rx)
        Hk, _ = bem_coeffs_to_H(Ppe @ (A_g_int @ ri[b_pre:]), B_bem, L_eq)
        H_out.append(Hk)
    return H_out

def fit_interior_bem_channel(r_list, s_hat_list, v_td_list, u_tx, u_rx, B_bem, L_eq, pool_H, b_drop=8):
    """
    Shared causal-inversion + interior [b_drop:] BEM channel update (called by BOTH rx_proposed_blind AND G_PhysBudget!).
    """
    N, Q_bem = B_bem.shape; K = len(r_list); Lu = len(u_tx); idx = np.arange(N); N_int = N - b_drop
    r_inv_list = [invert_rx_iqi_causal(r_list[k], u_rx) for k in range(K)]
    utx_n2 = float(np.sum(np.abs(u_tx)**2))
    if pool_H:
        Gf = np.zeros((L_eq*Q_bem, L_eq*Q_bem), dtype=complex); rhs = np.zeros(L_eq*Q_bem, dtype=complex); Pl = []
        for k in range(K):
            sc = np.conj(s_hat_list[k])
            s_eff = s_hat_list[k] + sum(u_tx[m] * sc[(idx - m) % N] for m in range(Lu))
            Pf = build_bem_dict(s_eff, B_bem, L_eq)[b_drop:, :]; Pl.append(Pf)
            Gf += Pf.conj().T @ Pf + (v_td_list[k]*(1.0+utx_n2) + 1e-5) * np.eye(L_eq*Q_bem)
            rhs += Pf.conj().T @ r_inv_list[k][b_drop:]
        c_new = np.linalg.solve(Gf, rhs); H_new, _ = bem_coeffs_to_H(c_new, B_bem, L_eq)
        H_list = [H_new.copy() for _ in range(K)]
        hp = float(np.mean(np.sum(np.abs(H_new)**2, axis=1)))
        rsq = sum(max(float(np.real(np.vdot(r_inv_list[k][b_drop:]-Pl[k]@c_new, r_inv_list[k][b_drop:]-Pl[k]@c_new))) - N_int*v_td_list[k]*hp,
                      0.1*float(np.real(np.vdot(r_inv_list[k][b_drop:]-Pl[k]@c_new, r_inv_list[k][b_drop:]-Pl[k]@c_new)))) for k in range(K))
        sig2_est = max(rsq / max(K*N_int - L_eq*Q_bem - 2*Lu, 1), 1e-5)
        return H_list, sig2_est
    H_list = []; rsq = 0.0
    for k in range(K):
        sc = np.conj(s_hat_list[k])
        s_eff = s_hat_list[k] + sum(u_tx[m] * sc[(idx - m) % N] for m in range(Lu))
        Pf = build_bem_dict(s_eff, B_bem, L_eq)[b_drop:, :]
        c_new = np.linalg.solve(Pf.conj().T @ Pf + (v_td_list[k]*(1.0+utx_n2)+1e-5)*np.eye(L_eq*Q_bem), Pf.conj().T @ r_inv_list[k][b_drop:])
        Hk, _ = bem_coeffs_to_H(c_new, B_bem, L_eq); H_list.append(Hk)
        ek = r_inv_list[k][b_drop:] - Pf @ c_new; e2 = float(np.real(np.vdot(ek, ek)))
        hp = float(np.mean(np.sum(np.abs(Hk)**2, axis=1)))
        rsq += max(e2 - N_int*v_td_list[k]*hp, 0.1*e2)
    sig2_est = max(rsq / max(K*(N_int - L_eq*Q_bem) - 2*Lu, 1), 1e-5)
    return H_list, sig2_est

def rx_proposed_blind(r_list, rx_cfg, use_null_u0=True, use_prefine=True, use_null_sig2=True,
                      Lu_override=None, pool_H=True, n_outer=6):
    """
    100% blind receiver (NO true sig2, CSI, IQI, or payload passed).
    - prop_u0_only     : use_null_u0=True,  use_prefine=False, use_null_sig2=True  (STRICT 0.0 Pass-0 H0 & sig2 diff vs zero_u0!)
    - zero_u0_same_sig2: use_null_u0=False, use_prefine=False, use_null_sig2=True
    - prop_full        : use_null_u0=True,  use_prefine=True,  use_null_sig2=True  (u0 + triggered zero-decision pilot CE refine)
    - zero_u0_raw_sig2 : use_null_u0=False, use_prefine=False, use_null_sig2=False
    - flat_same        : Lu_override=1, use_null_u0=True, use_prefine=True
    """
    A, B_bem, L_eq = rx_cfg["A"], rx_cfg["B_bem"], rx_cfg["L_eq"]
    Lu = rx_cfg["Lu"] if Lu_override is None else Lu_override
    data_idx, guard_obs_idx, xp_val, const = rx_cfg["data_idx"], rx_cfg["guard_obs_idx"], rx_cfg["xp_val"], rx_cfg["const"]
    K = len(r_list); N, Q_bem = B_bem.shape
    xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    sp = A.conj().T @ xp; sp_conj = np.conj(sp)
    Phi_p = build_bem_dict(sp, B_bem, L_eq)
    A_d_H = A[data_idx, :].conj().T
    Phi_p_daft = (A @ Phi_p)[guard_obs_idx, :]
    Gp = Phi_p_daft.conj().T @ Phi_p_daft
    P_pinv = np.linalg.solve(Gp + 1e-4*np.trace(Gp).real/Gp.shape[0]*np.eye(Gp.shape[0]), Phi_p_daft.conj().T)

    if pool_H:
        y_p_avg = np.mean([(A @ r_list[k])[guard_obs_idx] for k in range(K)], axis=0)
        H0, _ = bem_coeffs_to_H(P_pinv @ y_p_avg, B_bem, L_eq)
        H_list = [H0.copy() for _ in range(K)]
    else:
        H_list = [bem_coeffs_to_H(P_pinv @ (A @ r_list[k])[guard_obs_idx], B_bem, L_eq)[0] for k in range(K)]

    # Shared Double-Orthogonal Left Nullspace Q_perp (kills H0 A_d^H AND Phi_p)
    idx = np.arange(N); Psi_rows, z_rows = [], []; Q_perp_first = None; d_perp_list = []
    for k in range(K):
        if pool_H and Q_perp_first is not None:
            Q_perp = Q_perp_first
        else:
            U_kill = np.hstack([H_list[k] @ A_d_H, Phi_p])
            Qf, Rf = qr(U_kill, mode="full"); dR = np.abs(np.diag(Rf))
            Q_perp = Qf[:, int(np.sum(dR > 1e-8 * dR[0])):]
            if Q_perp_first is None: Q_perp_first = Q_perp
        d_perp_list.append(Q_perp.shape[1])
        z_rows.append(Q_perp.conj().T @ r_list[k])
        yp0_c = np.conj(H_list[k] @ sp)
        Psi_tx = np.column_stack([Q_perp.conj().T @ (H_list[k] @ sp_conj[(idx - m) % N]) for m in range(Lu)])
        Psi_rx = np.column_stack([Q_perp.conj().T @ yp0_c[(idx - m) % N] for m in range(Lu)])
        Psi_rows.append(np.hstack([Psi_tx, Psi_rx]))

    Psi_all = np.vstack(Psi_rows); z_all = np.concatenate(z_rows)
    sv_psi = np.linalg.svd(Psi_all, compute_uv=False)
    Gp_u = Psi_all.conj().T @ Psi_all
    u_vec = np.linalg.solve(Gp_u + 1e-2*np.trace(Gp_u).real/max(Gp_u.shape[0],1)*np.eye(Gp_u.shape[0]), Psi_all.conj().T @ z_all)
    res_null = z_all - Psi_all @ u_vec
    sig2_null = float(np.real(np.vdot(res_null, res_null)) / max(len(z_all) - len(u_vec), 1))
    sig2_raw  = float(np.real(np.vdot(z_all, z_all)) / max(len(z_all), 1))

    if use_null_u0:
        u_tx = u_vec[:Lu].copy(); u_rx = u_vec[Lu:].copy()
        for arr in (u_tx, u_rx):
            nrm = np.sum(np.abs(arr))
            if nrm > 0.55: arr *= (0.55 / nrm)
    else:
        u_tx = np.zeros(Lu, dtype=complex); u_rx = np.zeros(Lu, dtype=complex)
    sig2_est = sig2_null if use_null_sig2 else sig2_raw

    # Optional Pass-0 zero-decision pilot CE refinement (strictly OFF for P2a_PureU0!)
    # Calls the exact shared prefine_pilot_channel_interior helper gated directly in G_PhysBudget!
    if use_prefine and (np.linalg.norm(u_tx) > 0 or np.linalg.norm(u_rx) > 0):
        H_list = prefine_pilot_channel_interior(r_list, u_tx, u_rx, sp, A, guard_obs_idx, B_bem, L_eq, pool_H, b_pre=8)

    # Regularized soft-decision alternating refinement
    # Exact causal lower-triangular Rx inversion + drop first b_drop=8 rows (transient < 1e-6, ZERO circular wrap!)
    b_drop = 8
    N_int = N - b_drop
    xd_per_iter = []
    for outer in range(n_outer):
        inner_iters = 1 if outer == 0 else (2 if outer == 1 else 3)
        s_hat_list, v_td_list, xd_cur = [], [], []
        for k in range(K):
            xd, m_d, v_d = exact_wl_ep_detect(r_list[k], H_list[k], u_tx, u_rx, A, data_idx, xp_val, const, sig2=max(sig2_est, 1e-5), n_iter=inner_iters)
            xd_cur.append(xd)
            x_f = np.zeros(N, dtype=complex); x_f[0] = xp_val; x_f[data_idx] = m_d
            s_hat_list.append(A.conj().T @ x_f)
            v_td_list.append(float(np.sum(v_d)) / N)
        xd_per_iter.append(xd_cur)
        if outer == n_outer - 1:
            break

        # Calls the exact shared fit_interior_bem_channel helper gated directly in G_PhysBudget!
        H_list, sig2_est = fit_interior_bem_channel(r_list, s_hat_list, v_td_list, u_tx, u_rx, B_bem, L_eq, pool_H, b_drop=b_drop)

        Au, bu, eiv = [], [], 0.0
        for k in range(K):
            yd = H_list[k] @ s_hat_list[k]; bu.append((r_list[k] - yd)[b_drop:])
            sc = np.conj(s_hat_list[k])
            ctx = [(H_list[k] @ sc[(idx - m) % N])[b_drop:] for m in range(Lu)]
            ytx = sum((u_tx[m]*ctx[m] for m in range(Lu)), np.zeros(N_int, dtype=complex))
            zc_full = np.conj(yd + sum((u_tx[m]*(H_list[k] @ sc[(idx - m) % N]) for m in range(Lu)), np.zeros(N, dtype=complex)))
            crx = [zc_full[(idx - m) % N][b_drop:] for m in range(Lu)]
            Au.append(np.hstack([np.column_stack(ctx), np.column_stack(crx)]))
            eiv += N_int * v_td_list[k] * float(np.mean(np.sum(np.abs(H_list[k])**2, axis=1)))
        Au = np.vstack(Au); bu = np.concatenate(bu)
        Gu = Au.conj().T @ Au + (eiv + 1e-5*np.trace(Au.conj().T @ Au).real/Au.shape[1]) * np.eye(Au.shape[1])
        un = np.linalg.solve(Gu, Au.conj().T @ bu)
        u_tx = un[:Lu]; u_rx = un[Lu:]
        for arr in (u_tx, u_rx):
            nrm = np.sum(np.abs(arr))
            if nrm > 0.55: arr *= (0.55 / nrm)

    diag_info = {
        "d_perp": int(d_perp_list[0]),
        "psi_rank": int(np.sum(sv_psi > 1e-6 * sv_psi[0])),
        "psi_min_sv": float(sv_psi[-1]),
        "psi_cond": float(sv_psi[0] / max(sv_psi[-1], 1e-15)),
        "Q_perp": Q_perp_first,
    }
    return xd_per_iter, H_list, (u_tx, u_rx), diag_info

# =============================================================================
# 5. Statistical Utilities (RFC-8259 JSON Safe: None instead of Infinity!)
# =============================================================================
def _json_safe(x):
    return None if (x is None or not math.isfinite(x)) else float(x)

def fieller_linear_ci(a, b, R0):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    n = len(a); tcrit = float(student_t.ppf(0.975, n - 1))
    d = a - R0 * b
    d_mean = float(np.mean(d)); d_se = float(np.std(d, ddof=1) / np.sqrt(n))
    hw = tcrit * d_se; d_lb = d_mean - hw
    hw_frac = hw / d_mean if d_mean > 0 else None
    ma, mb = float(np.mean(a)), float(np.mean(b))
    va, vb = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    cab = float(np.cov(a, b, ddof=1)[0, 1])
    k2 = (tcrit**2) / n
    Aq = mb**2 - k2*vb; Bq = -2*(ma*mb - k2*cab); Cq = ma**2 - k2*va
    if Cq <= 0:
        r_lb = 0.0
    elif abs(Aq) < 1e-18:
        r_lb = (-Cq / Bq) if Bq < 0 else None
    else:
        disc = Bq**2 - 4*Aq*Cq
        if disc < 0: r_lb = 0.0
        else:
            roots = [(-Bq - math.sqrt(disc))/(2*Aq), (-Bq + math.sqrt(disc))/(2*Aq)]
            valid = [r for r in roots if r > 0 and (ma - r*mb) > 0]
            r_lb = min(valid) if valid else None
    return {
        "n": n, "mean_a": ma, "mean_b": mb, "ratio_pt": _json_safe(ma/mb) if mb > 0 else None,
        "R0": R0, "d_mean": d_mean, "d_hw": hw, "d_lb": d_lb, "hw_frac": _json_safe(hw_frac),
        "fieller_lb": _json_safe(r_lb),
        "pass_lb": bool(d_lb > 0.0),
        "pass_redline5_hw": bool(d_mean > 0.0 and hw_frac is not None and hw_frac <= 0.25),
    }

def clopper_pearson_ci(k, n, alpha=0.05):
    lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return lo, hi

def tango1998_paired_diff_ci(fail_a, fail_b, alpha=0.05):
    fa = np.asarray(fail_a, dtype=int); fb = np.asarray(fail_b, dtype=int)
    n = len(fa); n10 = int(np.sum((fa == 1) & (fb == 0))); n01 = int(np.sum((fa == 0) & (fb == 1)))
    z2 = float(norm.ppf(1.0 - alpha / 2.0)**2)
    diff_pt = (n10 - n01) / float(n)
    def score_sq(delta):
        A_c = 2.0 * n; B_c = -n10 - n01 + (2*n - n10 + n01)*delta; C_c = -n01 * delta * (1.0 - delta)
        disc = max(B_c**2 - 4.0*A_c*C_c, 0.0)
        q21 = min(max((-B_c + math.sqrt(disc))/(2.0*A_c), max(0.0, -delta)), min(1.0, 1.0 - delta))
        return ((n10 - n01 - n*delta)**2) / max(n*(2.0*q21 + delta*(1.0 - delta)), 1e-12)
    lo_l, lo_r = -1.0 + 1e-9, diff_pt
    for _ in range(60):
        mid = 0.5*(lo_l + lo_r)
        if score_sq(mid) > z2: lo_l = mid
        else: lo_r = mid
    hi_l, hi_r = diff_pt, 1.0 - 1e-9
    for _ in range(60):
        mid = 0.5*(hi_l + hi_r)
        if score_sq(mid) > z2: hi_r = mid
        else: hi_l = mid
    return {"n": n, "n10": n10, "n01": n01, "p_a": float(np.mean(fa)), "p_b": float(np.mean(fb)),
            "diff_pt": diff_pt, "ci_lo": lo_r, "ci_hi": hi_l, "hw": 0.5*(hi_l - lo_r)}

# =============================================================================
# 6. Auxiliary Fair Vectorized & Cached Banded Timing Benchmark (Non-Gating)
# =============================================================================
def build_interleaved_real_banded(H_dir_taps, H_img_taps):
    N, L = H_dir_taps.shape; a = H_dir_taps; b = H_img_taps
    B00 = np.real(a + b); B01 = -np.imag(a - b); B10 = np.imag(a + b); B11 = np.real(a - b)
    G00 = np.zeros((N, L)); G01 = np.zeros((N, L)); G10 = np.zeros((N, L)); G11 = np.zeros((N, L))
    idx_n = np.arange(N)
    for d in range(L):
        for l in range(d, L):
            ns = (idx_n + l) % N; l2 = l - d
            G00[:, d] += B00[ns, l]*B00[ns, l2] + B10[ns, l]*B10[ns, l2]
            G01[:, d] += B00[ns, l]*B01[ns, l2] + B10[ns, l]*B11[ns, l2]
            G10[:, d] += B01[ns, l]*B00[ns, l2] + B11[ns, l]*B10[ns, l2]
            G11[:, d] += B01[ns, l]*B01[ns, l2] + B11[ns, l]*B11[ns, l2]
    return (B00, B01, B10, B11), (G00, G01, G10, G11)

def cyclic_banded_wl_factor(G_blocks, reg_diag):
    G00, G01, G10, G11 = G_blocks; N, L = G00.shape; p = L - 1; m = N - p; b = 2*p + 1
    ab = np.zeros((b + 1, 2*m), dtype=float); i_m = np.arange(m)
    ab[0, 2*i_m] = G00[:m, 0]+reg_diag[:m]; ab[0, 2*i_m+1] = G11[:m, 0]+reg_diag[:m]; ab[1, 2*i_m] = G10[:m, 0]
    for d in range(1, L):
        k = np.arange(m - d)
        ab[2*d, 2*k] = G00[k, d]; ab[2*d+1, 2*k] = G01[k, d]; ab[2*d-1, 2*k+1] = G10[k, d]; ab[2*d, 2*k+1] = G11[k, d]
    c_A = cholesky_banded(ab, lower=True)
    D = np.zeros((2*p, 2*p), dtype=float)
    for ii in range(p):
        k = m + ii
        D[2*ii, 2*ii] = G00[k, 0]+reg_diag[k]; D[2*ii+1, 2*ii+1] = G11[k, 0]+reg_diag[k]
        D[2*ii, 2*ii+1] = G01[k, 0]; D[2*ii+1, 2*ii] = G10[k, 0]
        for d in range(1, L):
            jj = ii + d
            if jj < p:
                blk = np.array([[G00[k, d], G01[k, d]], [G10[k, d], G11[k, d]]])
                D[2*ii:2*ii+2, 2*jj:2*jj+2] = blk; D[2*jj:2*jj+2, 2*ii:2*ii+2] = blk.T
    B = np.zeros((2*m, 2*p), dtype=float)
    for d in range(1, L):
        for k in range(max(0, m - d), m):
            jj = k + d - m
            if 0 <= jj < p:
                B[2*k:2*k+2, 2*jj:2*jj+2] += np.array([[G00[k, d], G01[k, d]], [G10[k, d], G11[k, d]]])
    for ii in range(p):
        k = m + ii
        for d in range(1, L):
            r = (k + d) % N
            if r < m:
                B[2*r:2*r+2, 2*ii:2*ii+2] += np.array([[G00[k, d], G10[k, d]], [G01[k, d], G11[k, d]]])
    AinvB = cho_solve_banded((c_A, True), B)
    return (c_A, B, AinvB, cho_factor(D - B.T @ AinvB, lower=True), m, p)

def cyclic_banded_wl_solve(fac, rhs_c):
    c_A, B, AinvB, c_S, m, p = fac; N = m + p
    rhs = np.empty(2*N); rhs[0::2] = np.real(rhs_c); rhs[1::2] = np.imag(rhs_c)
    y1 = cho_solve_banded((c_A, True), rhs[:2*m]); x2 = cho_solve(c_S, rhs[2*m:] - B.T @ y1)
    x = np.concatenate([y1 - AinvB @ x2, x2])
    return x[0::2] + 1j * x[1::2]

def run_aux_timing(seed_timing=2032090000):
    rng = np.random.default_rng(seed_timing); rows = []
    for Nt in [64, 128, 256, 512]:
        Lt = 10
        Hd = rng.standard_normal((Nt, Lt)) + 1j * rng.standard_normal((Nt, Lt))
        Hi = 0.15 * (rng.standard_normal((Nt, Lt)) + 1j * rng.standard_normal((Nt, Lt)))
        rt = rng.standard_normal(Nt) + 1j * rng.standard_normal(Nt); reg = np.full(Nt, 0.05)
        def dense_setup():
            M_d = np.zeros((2*Nt, 2*Nt)); n_i = np.arange(Nt)
            for l in range(Lt):
                c_i = (n_i - l) % Nt; a, b = Hd[:, l], Hi[:, l]
                M_d[2*n_i, 2*c_i] += np.real(a+b); M_d[2*n_i, 2*c_i+1] += -np.imag(a-b)
                M_d[2*n_i+1, 2*c_i] += np.imag(a+b); M_d[2*n_i+1, 2*c_i+1] += np.real(a-b)
            Gd = M_d.T @ M_d + np.repeat(reg, 2)*np.eye(2*Nt)
            return M_d, cho_factor(0.5*(Gd+Gd.T), lower=True)
        def dense_solve(M_d, cG):
            ri = np.empty(2*Nt); ri[0::2] = np.real(rt); ri[1::2] = np.imag(rt)
            x = cho_solve(cG, M_d.T @ ri); return x[0::2] + 1j*x[1::2]
        def band_setup():
            Bt, Gb = build_interleaved_real_banded(Hd, Hi); return Bt, cyclic_banded_wl_factor(Gb, reg)
        def band_solve(Bt, fac):
            B00, B01, B10, B11 = Bt; rr, ri = np.real(rt), np.imag(rt)
            or_, oi_ = np.zeros(Nt), np.zeros(Nt); idx = np.arange(Nt)
            for l in range(Lt):
                ns = (idx + l) % Nt
                or_ += B00[ns, l]*rr[ns] + B10[ns, l]*ri[ns]
                oi_ += B01[ns, l]*rr[ns] + B11[ns, l]*ri[ns]
            return cyclic_banded_wl_solve(fac, or_ + 1j*oi_)
        M_d, cG = dense_setup(); sd = dense_solve(M_d, cG)
        Bt, fac = band_setup(); sf = band_solve(Bt, fac)
        rel_err = float(np.linalg.norm(sf - sd) / np.linalg.norm(sd))
        def med_ms(fn, reps=15):
            ts = []
            for _ in range(reps):
                t0 = time.perf_counter(); fn(); ts.append((time.perf_counter()-t0)*1e3)
            return float(np.median(ts))
        d_full = med_ms(lambda: dense_solve(*dense_setup()), 9 if Nt==512 else 15)
        b_full = med_ms(lambda: band_solve(*band_setup()), 15)
        d_cach = med_ms(lambda: dense_solve(M_d, cG), 30)
        b_cach = med_ms(lambda: band_solve(Bt, fac), 30)
        rows.append({"N": Nt, "L": Lt, "rel_err": rel_err,
                     "dense_setup_solve_ms": d_full, "band_setup_solve_ms": b_full, "setup_speedup": d_full/b_full,
                     "dense_cached_ms": d_cach, "band_cached_ms": b_cach, "cached_speedup": d_cach/b_cach})
    return rows

# =============================================================================
# 7. Startup Gates & Redline 1 Workers
# =============================================================================
def run_startup_gates(pool, seed_base=2032000000, n_huang=24, n_nar=16, n_zero=20):
    N = 256; c1 = 7.0/(2*N); c2 = 1.0/(2*np.sqrt(2)*N)
    A_p = daft_matrix(N, c1, c2); A_m = daft_matrix(N, -c1, -c2)
    rng = np.random.default_rng(seed_base + 1)

    # G1: Exact Physics, Dual-Chirp Identity, Per-Path Shift/Mask, Causal Noise Cov Budget
    x_t = rng.standard_normal(N) + 1j * rng.standard_normal(N)
    s_c = np.conj(A_p.conj().T @ x_t)
    s_id = A_m.conj().T @ (psi_c2_diag(N, c2) * np.conj(x_t[(-np.arange(N)) % N]))
    err_dual_chirp = float(np.linalg.norm(s_c - s_id) / np.linalg.norm(s_c))

    f1, f2, g1, g2 = generate_iqi_filters(rng, "strong13", 3, 3)
    delays = [0, 1, 2]; dopplers = rng.uniform(-0.85, 0.85, 3)
    gains = (rng.standard_normal(3)+1j*rng.standard_normal(3))*np.sqrt(np.array([0.5,0.3,0.2])/2); gains /= np.linalg.norm(gains)
    s = A_p.conj().T @ x_t; w0 = np.zeros(N + len(g1) - 1, dtype=complex)
    r_phys = phys_transmit_receive(s, c1, gains, delays, dopplers, f1, f2, g1, g2, w0)
    H_dir_lin, H_img_lin, G1_rx, G2_rx = build_exact_linear_operators(N, c1, gains, delays, dopplers, f1, f2, g1, g2)
    err_lin_op = float(np.linalg.norm(r_phys - (H_dir_lin @ s + H_img_lin @ np.conj(s))) / np.linalg.norm(r_phys))

    # Causal linear noise covariance check (ZERO seam wrap!) vs exact G1_rx, G2_rx
    u_tx_full = np.fft.ifft(np.fft.fft(f2, N)/np.fft.fft(f1, N))
    u_rx_full = np.fft.ifft(np.fft.fft(g2, N)/np.fft.fft(np.conj(g1), N))
    W_true = real_aug_mat(G1_rx, G2_rx); Cw_true = W_true @ W_true.T
    W1_c, W2_c = causal_lin_noise_mats(u_rx_full[:4], N)
    W_mod = real_aug_mat(W1_c, W2_c); Cw_mod = W_mod @ W_mod.T
    noise_cov_relerr = float(np.linalg.norm(Cw_true - Cw_mod) / np.linalg.norm(Cw_true))
    noise_seam_entry = float(abs(Cw_mod[0, N - 1]))

    H_eq_c = circ_mat(g1, N) @ build_td_channel_matrix(N, c1, gains, delays, dopplers) @ circ_mat(f1, N)
    z_lu4 = H_eq_c @ (s + circ_mat(u_tx_full[:4], N) @ np.conj(s))
    r_lu4 = z_lu4 + circ_mat(u_rx_full[:4], N) @ np.conj(z_lu4)
    err_lu4_interior = float(np.linalg.norm((r_phys - r_lu4)[8:]) / np.linalg.norm(r_phys[8:]))
    err_lu4_boundary = float(np.linalg.norm((r_phys - r_lu4)[:8]) / np.linalg.norm(r_phys))

    # Direct update-path gates calling the EXACT shared receiver helpers (ZERO duplicated formulas!)
    u_ce = np.array([0.0, 0.2, 0.0, 0.0], dtype=complex)
    r_ce = np.zeros(N, dtype=complex); r_ce[0] = 0.2
    z_ce = invert_rx_iqi_causal(r_ce, u_ce)
    err_causal_inv_impulse_n8 = float(abs(z_ce[8]))
    err_causal_inv_impulse_end = float(abs(z_ce[-1]))

    B_bem_g = dpss(N, 1.0, 5).T; L_eq_g = 7
    s_g_list, r_g_list = [], []
    for _ in range(4):
        s_g = A_p.conj().T @ (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        r_g = phys_transmit_receive(s_g, c1, gains, delays, dopplers, f1, f2, g1, g2, np.zeros(N + 2, dtype=complex))
        s_g_list.append(s_g); r_g_list.append(r_g)
    H_fit_pool, _ = fit_interior_bem_channel(r_g_list, s_g_list, [0.0]*4, u_tx_full[:4], u_rx_full[:4], B_bem_g, L_eq_g, True)
    H_fit_ind,  _ = fit_interior_bem_channel(r_g_list, s_g_list, [0.0]*4, u_tx_full[:4], u_rx_full[:4], B_bem_g, L_eq_g, False)
    err_causal_inv_bem_fit = float(max(
        np.linalg.norm(H_fit_pool[0] - H_eq_c) / np.linalg.norm(H_eq_c),
        np.linalg.norm(H_fit_ind[0]  - H_eq_c) / np.linalg.norm(H_eq_c),
    ))
    H_bem_ce_pool, _ = fit_interior_bem_channel([r_ce], [s_g_list[0]], [0.0], np.zeros(4, dtype=complex), u_ce, B_bem_g, L_eq_g, True)
    H_bem_ce_ind,  _ = fit_interior_bem_channel([r_ce], [s_g_list[0]], [0.0], np.zeros(4, dtype=complex), u_ce, B_bem_g, L_eq_g, False)
    err_bem_impulse_frob = float(max(np.linalg.norm(H_bem_ce_pool[0]), np.linalg.norm(H_bem_ce_ind[0])))

    # Direct Pass-0 prefine gate calling the EXACT prefine_pilot_channel_interior helper for BOTH pool_H=True & False!
    guard_obs_g = np.array([m % N for m in range(-47, 4)])
    xp_g = np.zeros(N, dtype=complex); xp_g[0] = np.sqrt(50.0); sp_g = A_p.conj().T @ xp_g
    H_pre_ce_pool = prefine_pilot_channel_interior([r_ce], np.zeros(4, dtype=complex), u_ce, sp_g, A_p, guard_obs_g, B_bem_g, L_eq_g, True)[0]
    H_pre_ce_ind  = prefine_pilot_channel_interior([r_ce], np.zeros(4, dtype=complex), u_ce, sp_g, A_p, guard_obs_g, B_bem_g, L_eq_g, False)[0]
    err_prefine_impulse_frob = float(max(np.linalg.norm(H_pre_ce_pool), np.linalg.norm(H_pre_ce_ind)))
    r_p_only = phys_transmit_receive(sp_g, c1, gains, delays, dopplers, f1, f2, g1, g2, np.zeros(N + 2, dtype=complex))
    H_pre_fit_pool = prefine_pilot_channel_interior([r_p_only], u_tx_full[:4], u_rx_full[:4], sp_g, A_p, guard_obs_g, B_bem_g, L_eq_g, True)[0]
    H_pre_fit_ind  = prefine_pilot_channel_interior([r_p_only], u_tx_full[:4], u_rx_full[:4], sp_g, A_p, guard_obs_g, B_bem_g, L_eq_g, False)[0]
    err_prefine_bem_fit = float(max(
        np.linalg.norm(H_pre_fit_pool - H_eq_c) / np.linalg.norm(H_eq_c),
        np.linalg.norm(H_pre_fit_ind  - H_eq_c) / np.linalg.norm(H_eq_c),
    ))

    # Per-path Huang shift & mask verification (c1=11/(2N), c2=sqrt(2)/2, delays [0,1,3], dopplers [0,1,-2])
    c1_h = 11.0/(2*N); c2_h = np.sqrt(2.0)/2.0; A_h = daft_matrix(N, c1_h, c2_h)
    Q_g_h = 42; guard_obs_h = set(m % N for m in range(-Q_g_h, 7))
    per_path_checks = []
    xp_u = np.zeros(N, dtype=complex); xp_u[0] = 1.0
    for lp, nup, hp in [(0, 0.0, 0.7), (1, 1.0, -0.5), (3, -2.0, 0.4)]:
        Hp = build_td_channel_matrix(N, c1_h, [hp], [lp], [nup])
        yp = (A_h @ Hp @ A_h.conj().T) @ xp_u
        exp_bin = int((-11 * lp - int(nup)) % N)
        leak_p = float(np.linalg.norm(np.delete(yp, exp_bin)) / max(abs(yp[exp_bin]), 1e-12))
        per_path_checks.append({"l": lp, "nu": nup, "bin": exp_bin, "in_guard_mask": exp_bin in guard_obs_h, "off_bin_leak": leak_p})
    H_h = build_td_channel_matrix(N, c1_h, [0.7, -0.5, 0.4], [0, 1, 3], [0.0, 1.0, -2.0])
    s_h = A_h.conj().T @ x_t
    r_h_phys = phys_transmit_receive(s_h, c1_h, [0.7, -0.5, 0.4], [0, 1, 3], [0.0, 1.0, -2.0],
                                     np.array([1.0+0j]), np.array([0j]), np.array([1.0+0j]), np.array([0j]), np.zeros(N, dtype=complex))
    err_huang_noiseless = float(np.linalg.norm(A_h @ r_h_phys - (A_h @ H_h @ A_h.conj().T) @ x_t) / np.linalg.norm(x_t))
    per_path_ok = all(p["in_guard_mask"] and p["off_bin_leak"] < 1e-12 for p in per_path_checks)

    # G2: c1 = 0 Non-Triviality (BOTH true-channel structural check AND actual blind estimated dictionary check!)
    B_bem = dpss(N, 1.0, 5).T; L_eq = 7; Lu = 4; Q_g = 47
    data_idx = np.array([m for m in range(Q_g + 1, N - Q_g)])
    guard_obs_idx = np.array([m % N for m in range(-Q_g, 4)])
    xp_val = np.sqrt(50.0); xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    c1_stats = {}
    for tag, c1_v, c2_v in [("afdm_trueH", c1, c2), ("ofdm_c1_zero_trueH", 0.0, 0.0)]:
        At = daft_matrix(N, c1_v, c2_v); sp = At.conj().T @ xp; sp_c = np.conj(sp)
        Phi_p = build_bem_dict(sp, B_bem, L_eq); AdH = At[data_idx, :].conj().T
        U_kill = np.hstack([H_eq_c @ AdH, Phi_p])
        Qf, Rf = qr(U_kill, mode="full"); dR = np.abs(np.diag(Rf))
        Q_perp = Qf[:, int(np.sum(dR > 1e-8 * dR[0])):]
        idx = np.arange(N); yp_c = np.conj(H_eq_c @ sp)
        Psi = np.hstack([
            np.column_stack([Q_perp.conj().T @ (H_eq_c @ sp_c[(idx - m) % N]) for m in range(Lu)]),
            np.column_stack([Q_perp.conj().T @ yp_c[(idx - m) % N] for m in range(Lu)])
        ])
        sv = np.linalg.svd(Psi, compute_uv=False)
        qr_orth_err = float(max(np.linalg.norm(Q_perp.conj().T @ (H_eq_c @ AdH)), np.linalg.norm(Q_perp.conj().T @ Phi_p)))
        c1_stats[tag] = {"d_perp": int(Q_perp.shape[1]), "rank_psi": int(np.sum(sv > 1e-6*sv[0])),
                         "cond": float(sv[0]/max(sv[-1],1e-15)), "min_sv": float(sv[-1]), "qr_orth_err": qr_orth_err}
    # Actual blind estimated dictionary check on a noisy burst!
    const64, _ = gray_qam_constellation(64)
    sig2_chk = 10**(-32.0/10.0); r_chk_l = []
    for _ in range(4):
        xk = np.zeros(N, dtype=complex); xk[0] = xp_val; xk[data_idx] = const64[rng.integers(0, 64, len(data_idx))]
        wk = np.sqrt(sig2_chk/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2))
        r_chk_l.append(phys_transmit_receive(A_p.conj().T@xk, c1, gains, delays, dopplers, f1, f2, g1, g2, wk))
    rx_chk = {"A": A_p, "B_bem": B_bem, "L_eq": L_eq, "Lu": Lu, "data_idx": data_idx,
              "guard_obs_idx": guard_obs_idx, "xp_val": xp_val, "const": const64}
    _, _, _, d_blind = rx_proposed_blind(r_chk_l, rx_chk, True, False, True, None, True, 1)
    c1_stats["afdm_blind_estH"] = {"d_perp": d_blind["d_perp"], "rank_psi": d_blind["psi_rank"],
                                   "cond": d_blind["psi_cond"], "min_sv": d_blind["psi_min_sv"]}

    # G3: Redline 1 Huang Fig. 2, Fig. 3, Fig. 4 Exact Reproduction (NO /k_vec[0]!)
    h_res = pool.map(_worker_huang_fig4, [seed_base + 10000 + i for i in range(n_huang)])
    huang_fig4 = {
        "n_trials": n_huang,
        "fig2_k_nmse_iter1": float(np.mean([r[0] for r in h_res])),
        "fig2_k_nmse_iter5": float(np.mean([r[1] for r in h_res])),
        "fig3_ber_iter1": float(np.mean([r[2] for r in h_res])),
        "fig3_ber_iter5": float(np.mean([r[3] for r in h_res])),
        "fig4_ber_nocomp": float(np.mean([r[4] for r in h_res])),
        "fig4_ber_huang_comp": float(np.mean([r[3] for r in h_res])),
        "fig4_ber_no_iqimb": float(np.mean([r[5] for r in h_res])),
    }
    huang_fig4["pass"] = bool(
        1e-5 <= huang_fig4["fig2_k_nmse_iter5"] <= 1e-3 and
        huang_fig4["fig2_k_nmse_iter5"] <= huang_fig4["fig2_k_nmse_iter1"] and
        huang_fig4["fig3_ber_iter5"] <= huang_fig4["fig3_ber_iter1"] and
        5e-4 <= huang_fig4["fig4_ber_huang_comp"] <= 4e-2 and
        huang_fig4["fig4_ber_huang_comp"] <= 1.35 * huang_fig4["fig4_ber_no_iqimb"] and
        huang_fig4["fig4_ber_huang_comp"] <= 0.5 * huang_fig4["fig4_ber_nocomp"]
    )

    # G4: Redline 1 Exact Narasimhan JSTSP'09 §IV-B/V-A Native OFDM Health
    # (Static + Mobile 5% Doppler QPSK SER + 16QAM D=2 vs D=0 off-diagonal ablation + FULL 2x2 banded & off-diagonal NMSE!)
    nar_res = pool.map(_worker_nar_ofdm, [seed_base + 20000 + i for i in range(n_nar)])
    nar_ofdm = {
        "n_trials": n_nar,
        "ser_static_16qam30_strong13": float(np.mean([r[0] for r in nar_res])),
        "h_nmse_static_db": float(10*np.log10(max(np.mean([r[1] for r in nar_res]), 1e-12))),
        "ser_mobile005_qpsk25_strong13": float(np.mean([r[2] for r in nar_res])),
        "ser_mobile005_16qam30_D2": float(np.mean([r[3] for r in nar_res])),
        "ser_mobile005_16qam30_D0_noslope": float(np.mean([r[4] for r in nar_res])),
        "fullband_2x2_nmse_mobile_db": float(10*np.log10(max(np.mean([r[5] for r in nar_res]), 1e-12))),
        "offdiag_2x2_nmse_mobile_db": float(10*np.log10(max(np.mean([r[6] for r in nar_res]), 1e-12))),
    }
    nar_ofdm["pass"] = bool(
        nar_ofdm["ser_static_16qam30_strong13"] < 0.01 and nar_ofdm["h_nmse_static_db"] < -20.0 and
        nar_ofdm["ser_mobile005_qpsk25_strong13"] < 0.01 and
        nar_ofdm["ser_mobile005_16qam30_D2"] < 0.85 * nar_ofdm["ser_mobile005_16qam30_D0_noslope"] and
        nar_ofdm["fullband_2x2_nmse_mobile_db"] < -19.0 and
        nar_ofdm["offdiag_2x2_nmse_mobile_db"] < -15.0
    )

    # G5: Zero-IQI Health Gate (ALL blind arms: AFDM arms + native-OFDM Narasimhan!)
    z_res = pool.map(_worker_zero_iqi, [seed_base + 30000 + i for i in range(n_zero)])
    zero_health = {}
    all_zero_ok = True
    for arm in ["prop_full", "prop_u0_only", "zero_u0_same_sig2", "huang_blind", "flat_same", "narasimhan_ofdm_zero"]:
        s_m = float(np.mean([r[arm]["ser"] for r in z_res]))
        h_db = float(10 * np.log10(max(np.mean([r[arm]["h_nmse"] for r in z_res]), 1e-12)))
        ok = bool(s_m < 0.01 and h_db < -20.0)
        zero_health[arm] = {"ser": s_m, "h_nmse_db": h_db, "pass": ok}
        all_zero_ok = all_zero_ok and ok
    # Diagnostic: Narasimhan zero-IQI ported to AFDM (matched 64-QAM paired decomposition is reported per-burst in R1!)
    zero_health["diag_narasimhan_afdm_zero_ser"] = float(np.mean([r["diag_nar_afdm_ser"] for r in z_res]))

    phys_ok = bool(err_dual_chirp < 1e-12 and err_lin_op < 1e-12 and err_huang_noiseless < 1e-12
                   and per_path_ok and noise_seam_entry == 0.0 and noise_cov_relerr < 0.08
                   and err_causal_inv_impulse_n8 < 1e-5 and err_causal_inv_impulse_end < 1e-50
                   and err_causal_inv_bem_fit < 0.02 and err_bem_impulse_frob < 1e-4
                   and err_prefine_impulse_frob < 1e-4 and err_prefine_bem_fit < 0.03
                   and c1_stats["afdm_trueH"]["qr_orth_err"] < 1e-12)
    c1_ok = bool(c1_stats["afdm_trueH"]["rank_psi"] == 8 and c1_stats["afdm_trueH"]["cond"] < 50.0
                 and c1_stats["afdm_blind_estH"]["rank_psi"] == 8 and c1_stats["afdm_blind_estH"]["cond"] < 50.0
                 and c1_stats["ofdm_c1_zero_trueH"]["rank_psi"] < 8 and c1_stats["ofdm_c1_zero_trueH"]["cond"] > 1e10)
    gates_ok = bool(phys_ok and c1_ok and huang_fig4["pass"] and nar_ofdm["pass"] and all_zero_ok)

    return {
        "GATES_OK": gates_ok,
        "G_PhysBudget": {
            "err_dual_chirp": err_dual_chirp, "err_lin_op": err_lin_op,
            "err_huang_noiseless": err_huang_noiseless, "per_path_checks": per_path_checks,
            "causal_noise_cov_relerr": noise_cov_relerr, "causal_noise_seam_entry": noise_seam_entry,
            "err_causal_inv_impulse_n8": err_causal_inv_impulse_n8,
            "err_causal_inv_impulse_end": err_causal_inv_impulse_end,
            "err_causal_inv_bem_fit": err_causal_inv_bem_fit,
            "err_bem_impulse_frob": err_bem_impulse_frob,
            "err_prefine_impulse_frob": err_prefine_impulse_frob,
            "err_prefine_bem_fit": err_prefine_bem_fit,
            "err_lu4_interior": err_lu4_interior, "err_lu4_boundary": err_lu4_boundary, "pass": phys_ok
        },
        "G_c1_Zero_NonTrivial": {**c1_stats, "pass": c1_ok},
        "G_R1_Huang_Fig4": huang_fig4,
        "G_R1_Narasimhan_OFDM": nar_ofdm,
        "G_ZeroIQI_Health": {**zero_health, "pass": all_zero_ok},
    }

def _worker_huang_fig4(seed):
    rng = np.random.default_rng(seed)
    N = 256; c1 = 11.0/(2*N); c2 = np.sqrt(2.0)/2.0; A = daft_matrix(N, c1, c2)
    const, bits_lut = gray_qam_constellation(64)
    B_bem = dpss(N, 3.0, 9).T; L_eq = 4; Q_g = 42
    guard_obs_idx = np.array([m % N for m in range(-Q_g, 7)])
    data_idx = np.array([m for m in range(Q_g + 1, N - Q_g)])
    xp_val = np.sqrt(50.0)
    grid_pts = []
    while len(grid_pts) < 3:
        pt = (int(rng.integers(0, 4)), int(rng.integers(-2, 3)))
        if pt not in grid_pts: grid_pts.append(pt)
    delays, dopplers, gains = [], [], []
    for lc, ac in grid_pts:
        for _ in range(3):
            delays.append(lc); dopplers.append(ac + rng.uniform(-0.5, 0.5))
            gains.append((rng.standard_normal()+1j*rng.standard_normal())/np.sqrt(18.0))
    f1, f2, g1, g2 = generate_iqi_filters(rng, "huang_fig4")
    sig2 = 10**(-30.0 / 10.0)
    x_pre = const[rng.integers(0, 64, N)]
    r_pre = phys_transmit_receive(A.conj().T@x_pre, c1, gains, delays, dopplers, f1, f2, g1, g2,
                                  np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N)))
    k_true = np.array([f1[0]*g1[0], f2[0]*g1[0], np.conj(f1[0])*g2[0], np.conj(f2[0])*g2[0]])
    k_hat, _, _, k_hist = huang_exact_alg1(A @ r_pre, x_pre, A, B_bem, L_eq, sig2_in=sig2, N_iter=5, return_hist=True)
    kn1 = float(np.sum(np.abs(k_hist[0] - k_true)**2) / np.sum(np.abs(k_true)**2))
    kn5 = float(np.sum(np.abs(k_hist[-1] - k_true)**2) / np.sum(np.abs(k_true)**2))

    idx_tx = rng.integers(0, 64, len(data_idx))
    x_sym = np.zeros(N, dtype=complex); x_sym[0] = xp_val; x_sym[data_idx] = const[idx_tx]
    w_sym = np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N))
    y_iq = A @ phys_transmit_receive(A.conj().T@x_sym, c1, gains, delays, dopplers, f1, f2, g1, g2, w_sym)
    y_no = A @ phys_transmit_receive(A.conj().T@x_sym, c1, gains, delays, dopplers, np.array([1.0+0j]), np.array([0j]), np.array([1.0+0j]), np.array([0j]), w_sym)
    _, _, xd_hist = huang_exact_alg2(y_iq, k_hat, A, B_bem, L_eq, data_idx, guard_obs_idx, xp_val, const, sig2, N_iter=5, return_hist=True)
    xd_nc, _ = huang_exact_alg2(y_iq, np.array([1.0+0j,0,0,0]), A, B_bem, L_eq, data_idx, guard_obs_idx, xp_val, const, sig2, N_iter=1)
    xd_cl, _ = huang_exact_alg2(y_no, np.array([1.0+0j,0,0,0]), A, B_bem, L_eq, data_idx, guard_obs_idx, xp_val, const, sig2, N_iter=1)
    return (kn1, kn5,
            ber_from_idx(qam_hard(xd_hist[0], const)[1], idx_tx, bits_lut),
            ber_from_idx(qam_hard(xd_hist[-1], const)[1], idx_tx, bits_lut),
            ber_from_idx(qam_hard(xd_nc, const)[1], idx_tx, bits_lut),
            ber_from_idx(qam_hard(xd_cl, const)[1], idx_tx, bits_lut))

def _worker_nar_ofdm(seed):
    rng = np.random.default_rng(seed)
    N = 256; A0 = daft_matrix(N, 0.0, 0.0); L_cpp = 8
    const16, _ = gray_qam_constellation(16); const4, _ = gray_qam_constellation(4)
    xp1, xp2 = build_narasimhan_scheme_a_preambles(N)
    rx_cfg = {"A": A0, "data_idx": np.arange(N), "xp_val": 0.0}
    n_idx = np.arange(N)
    c_ramp = {d: complex(np.mean((n_idx - 0.5*(N - 1)) * np.exp(-1j * 2 * np.pi * d * n_idx / N))) for d in (-2, -1, 1, 2)}

    # (1) Static 16-QAM 30 dB strong13
    f1, f2, g1, g2 = generate_iqi_filters(rng, "strong13", 3, 3)
    gains = (rng.standard_normal(3)+1j*rng.standard_normal(3))*np.sqrt(np.array([0.5,0.3,0.2])/2); gains /= np.linalg.norm(gains)
    sig2_s = 10**(-30.0/10.0)
    rp1 = phys_transmit_receive(A0.conj().T@xp1, 0.0, gains, [0,1,2], [0.0,0.0,0.0], f1, f2, g1, g2,
                                np.sqrt(sig2_s/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=0)
    id_s = rng.integers(0, 16, N)
    rd_s = phys_transmit_receive(A0.conj().T@const16[id_s], 0.0, gains, [0,1,2], [0.0,0.0,0.0], f1, f2, g1, g2,
                                 np.sqrt(sig2_s/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=N+L_cpp)
    rp2 = phys_transmit_receive(A0.conj().T@xp2, 0.0, gains, [0,1,2], [0.0,0.0,0.0], f1, f2, g1, g2,
                                np.sqrt(sig2_s/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=2*(N+L_cpp))
    xd_s, h_d_s, _, _ = rx_narasimhan09_blind(rp1, xp1, rp2, xp2, [rd_s], rx_cfg, D=2, L_cpp=2*(N+L_cpp)-N)
    ser_stat = float(np.mean(qam_hard(xd_s[0], const16)[1] != id_s))
    Hd_s, _, _, _ = build_exact_linear_operators(N, 0.0, gains, [0,1,2], [0.0,0.0,0.0], f1, f2, g1, g2, t_offset=N+L_cpp)
    hd_t = np.diag(A0 @ Hd_s @ A0.conj().T)
    h_nmse_stat = float(np.sum(np.abs(h_d_s - hd_t)**2) / np.sum(np.abs(hd_t)**2))

    # (2) Mobile 5% Doppler (|nu| in [0.03, 0.05], exact Narasimhan §VI-A preamble-data-postamble!)
    f1, f2, g1, g2 = generate_iqi_filters(rng, "strong13", 3, 3)
    gains = (rng.standard_normal(3)+1j*rng.standard_normal(3))*np.sqrt(np.array([0.5,0.3,0.2])/2); gains /= np.linalg.norm(gains)
    dops = rng.uniform(0.03, 0.05, 3) * rng.choice([-1.0, 1.0], 3)
    # 2a) QPSK 25 dB health
    sig2_q = 10**(-25.0/10.0)
    rp1_q = phys_transmit_receive(A0.conj().T@xp1, 0.0, gains, [0,1,2], dops, f1, f2, g1, g2,
                                  np.sqrt(sig2_q/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=0)
    id_q = rng.integers(0, 4, N)
    rd_q = phys_transmit_receive(A0.conj().T@const4[id_q], 0.0, gains, [0,1,2], dops, f1, f2, g1, g2,
                                 np.sqrt(sig2_q/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=N+L_cpp)
    rp2_q = phys_transmit_receive(A0.conj().T@xp2, 0.0, gains, [0,1,2], dops, f1, f2, g1, g2,
                                  np.sqrt(sig2_q/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=2*(N+L_cpp))
    xd_q, _, _, _ = rx_narasimhan09_blind(rp1_q, xp1, rp2_q, xp2, [rd_q], rx_cfg, D=2, L_cpp=2*(N+L_cpp)-N)
    ser_mob_qpsk = float(np.mean(qam_hard(xd_q[0], const4)[1] != id_q))
    # 2b) 16-QAM 30 dB D=2 vs D=0 off-diagonal ICI effectiveness + FULL 2x2 banded & off-diagonal NMSE!
    rp1_m = phys_transmit_receive(A0.conj().T@xp1, 0.0, gains, [0,1,2], dops, f1, f2, g1, g2,
                                  np.sqrt(sig2_s/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=0)
    id_m = rng.integers(0, 16, N)
    rd_m = phys_transmit_receive(A0.conj().T@const16[id_m], 0.0, gains, [0,1,2], dops, f1, f2, g1, g2,
                                 np.sqrt(sig2_s/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=N+L_cpp)
    rp2_m = phys_transmit_receive(A0.conj().T@xp2, 0.0, gains, [0,1,2], dops, f1, f2, g1, g2,
                                  np.sqrt(sig2_s/2)*(rng.standard_normal(N+2)+1j*rng.standard_normal(N+2)), t_offset=2*(N+L_cpp))
    xd_m2, _, g_mid, sl = rx_narasimhan09_blind(rp1_m, xp1, rp2_m, xp2, [rd_m], rx_cfg, D=2, L_cpp=2*(N+L_cpp)-N)
    xd_m0, _, _, _      = rx_narasimhan09_blind(rp1_m, xp1, rp2_m, xp2, [rd_m], rx_cfg, D=0, L_cpp=2*(N+L_cpp)-N)
    ser_mob_d2 = float(np.mean(qam_hard(xd_m2[0], const16)[1] != id_m))
    ser_mob_d0 = float(np.mean(qam_hard(xd_m0[0], const16)[1] != id_m))
    Hd_m, Hi_m, _, _ = build_exact_linear_operators(N, 0.0, gains, [0,1,2], dops, f1, f2, g1, g2, t_offset=N+L_cpp)
    Fd_m = A0 @ Hd_m @ A0.conj().T; Fi_m = A0 @ Hi_m @ A0.conj().T
    ea, pa, eo, po = 0.0, 0.0, 0.0, 0.0
    # Include ALL N rows (0..N-1) including band edges (with 0 <= c < N matching Footnote-2 edge shortening!)
    for r in range(N):
        for d in (-2, -1, 0, 1, 2):
            c = r - d
            if not (0 <= c < N):
                continue
            nr, nc = (-r) % N, (-c) % N
            Gt = np.array([[Fd_m[r, c], Fi_m[r, c]], [np.conj(Fi_m[nr, nc]), np.conj(Fd_m[nr, nc])]])
            if d == 0:
                Gh = g_mid[r]
            else:
                Gh = np.empty((2, 2), dtype=complex)
                Gh[0, :] = c_ramp[d] * sl[c, 0, :]
                Gh[1, :] = np.conj(c_ramp[-d]) * sl[c, 1, :]
            ea += float(np.sum(np.abs(Gh - Gt)**2)); pa += float(np.sum(np.abs(Gt)**2))
            if d != 0:
                eo += float(np.sum(np.abs(Gh - Gt)**2)); po += float(np.sum(np.abs(Gt)**2))
    return (ser_stat, h_nmse_stat, ser_mob_qpsk, ser_mob_d2, ser_mob_d0, ea / max(pa, 1e-12), eo / max(po, 1e-12))

def _worker_zero_iqi(seed):
    rng = np.random.default_rng(seed)
    N = 256; c1 = 7.0/(2*N); c2 = 1.0/(2*np.sqrt(2)*N); A = daft_matrix(N, c1, c2); A0 = daft_matrix(N, 0.0, 0.0)
    B_bem = dpss(N, 1.0, 5).T; L_eq = 7; Lu = 4; Q_g = 47
    guard_obs_idx = np.array([m % N for m in range(-Q_g, 4)])
    data_idx = np.array([m for m in range(Q_g + 1, N - Q_g)])
    xp_val = np.sqrt(50.0); const, _ = gray_qam_constellation(4)
    rx_cfg = {"A": A, "B_bem": B_bem, "L_eq": L_eq, "Lu": Lu, "data_idx": data_idx,
              "guard_obs_idx": guard_obs_idx, "xp_val": xp_val, "const": const}
    f1, f2, g1, g2 = generate_iqi_filters(rng, "zero")
    gains = (rng.standard_normal(3)+1j*rng.standard_normal(3))*np.sqrt(np.array([0.5,0.3,0.2])/2); gains /= np.linalg.norm(gains)
    dops = rng.uniform(-0.85, 0.85, 3); sig2 = 10**(-25.0/10.0)
    H_true = build_td_channel_matrix(N, c1, gains, [0,1,2], dops)
    x_pre = const[rng.integers(0,4,N)]
    r_pre = phys_transmit_receive(A.conj().T@x_pre, c1, gains, [0,1,2], dops, f1, f2, g1, g2, np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N)))
    xp1_n, xp2_n = build_narasimhan_scheme_a_preambles(N)
    rp1_a = phys_transmit_receive(A.conj().T@xp1_n, c1, gains, [0,1,2], dops, f1, f2, g1, g2, np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N)))
    rp2_a = phys_transmit_receive(A.conj().T@xp2_n, c1, gains, [0,1,2], dops, f1, f2, g1, g2, np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N)))
    r_list, tx_list = [], []
    for _ in range(4):
        idx_tx = rng.integers(0,4,len(data_idx))
        x = np.zeros(N, dtype=complex); x[0] = xp_val; x[data_idx] = const[idx_tx]
        r_list.append(phys_transmit_receive(A.conj().T@x, c1, gains, [0,1,2], dops, f1, f2, g1, g2, np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N))))
        tx_list.append(idx_tx)
    def eval_arm(xd_l, H_l):
        ser = float(np.mean([np.mean(qam_hard(xd_l[k], const)[1] != tx_list[k]) for k in range(4)]))
        h_n = float(np.mean([np.sum(np.abs(H_l[k] - H_true)**2)/np.sum(np.abs(H_true)**2) for k in range(4)]))
        return {"ser": ser, "h_nmse": h_n}
    xd_h, H_h = rx_huang_blind(r_pre, x_pre, r_list, rx_cfg)
    xd_p, H_p, _, _ = rx_proposed_blind(r_list, rx_cfg, True,  True,  True, None, True, 6)
    xd_u, H_u, _, _ = rx_proposed_blind(r_list, rx_cfg, True,  False, True, None, True, 6)
    xd_z, H_z, _, _ = rx_proposed_blind(r_list, rx_cfg, False, False, True, None, True, 6)
    xd_f, H_f, _, _ = rx_proposed_blind(r_list, rx_cfg, True,  True,  True, 1,    True, 6)
    xd_na, _, _, _ = rx_narasimhan09_blind(rp1_a, xp1_n, rp2_a, xp2_n, r_list, rx_cfg, D=2, L_cpp=4)
    diag_nar_afdm_ser = float(np.mean([np.mean(qam_hard(xd_na[k], const)[1] != tx_list[k]) for k in range(4)]))
    # Native OFDM zero-IQI health for Narasimhan
    rp1_o = phys_transmit_receive(A0.conj().T@xp1_n, 0.0, gains, [0,1,2], [0.0,0.0,0.0], f1, f2, g1, g2, np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N)))
    rp2_o = phys_transmit_receive(A0.conj().T@xp2_n, 0.0, gains, [0,1,2], [0.0,0.0,0.0], f1, f2, g1, g2, np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N)))
    idx_o = rng.integers(0,4,N)
    rd_o  = phys_transmit_receive(A0.conj().T@const[idx_o], 0.0, gains, [0,1,2], [0.0,0.0,0.0], f1, f2, g1, g2, np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N)))
    xd_no, h_no, _, _ = rx_narasimhan09_blind(rp1_o, xp1_n, rp2_o, xp2_n, [rd_o], {"A": A0, "data_idx": np.arange(N), "xp_val": 0.0}, D=2, L_cpp=4)
    H_o_t = build_td_channel_matrix(N, 0.0, gains, [0,1,2], [0.0,0.0,0.0])
    h_o_d = np.diag(A0 @ H_o_t @ A0.conj().T)
    return {
        "huang_blind": eval_arm(xd_h, H_h), "prop_full": eval_arm(xd_p[-1], H_p),
        "prop_u0_only": eval_arm(xd_u[-1], H_u), "zero_u0_same_sig2": eval_arm(xd_z[-1], H_z),
        "flat_same": eval_arm(xd_f[-1], H_f),
        "narasimhan_ofdm_zero": {"ser": float(np.mean(qam_hard(xd_no[0], const)[1] != idx_o)),
                                 "h_nmse": float(np.sum(np.abs(h_no - h_o_d)**2)/np.sum(np.abs(h_o_d)**2))},
        "diag_nar_afdm_ser": diag_nar_afdm_ser,
    }

# =============================================================================
# 8. Main Burst Evaluation Worker
# =============================================================================
def _worker_burst(args):
    seed, lvl, M_qam, snr_db, cont_doppler, full_ablations, huang_snr_adj, nar_snr_adj, Q_g_prop_override, paired_zero_iqi_diag = args
    rng = np.random.default_rng(seed)
    N = 256; c1 = 7.0/(2*N); c2 = 1.0/(2*np.sqrt(2)*N); A = daft_matrix(N, c1, c2)
    delays = [0, 1, 2]; L_eq = 7; Lu = 4
    B_bem = dpss(N, 1.0, 5).T
    guard_obs_idx = np.array([m % N for m in range(-47, 4)])  # fixed pilot window
    data_idx_nom = np.array([m for m in range(48, N - 47)])   # nominal Nd=161 (used by rivals ALWAYS!)
    Q_g_p = 47 if Q_g_prop_override is None else Q_g_prop_override
    data_idx_prop = np.array([m for m in range(Q_g_p + 1, N - Q_g_p)])
    xp_val = np.sqrt(50.0); const, _ = gray_qam_constellation(M_qam)
    rx_cfg_nom = {"A": A, "B_bem": B_bem, "L_eq": L_eq, "Lu": Lu, "data_idx": data_idx_nom,
                  "guard_obs_idx": guard_obs_idx, "xp_val": xp_val, "const": const}
    rx_cfg_prop = {"A": A, "B_bem": B_bem, "L_eq": L_eq, "Lu": Lu, "data_idx": data_idx_prop,
                   "guard_obs_idx": guard_obs_idx, "xp_val": xp_val, "const": const}

    f1, f2, g1, g2 = generate_iqi_filters(rng, lvl, Lf=3, Lg=3)
    sig2   = 10**(-snr_db / 10.0)
    sig2_h = 10**(-(snr_db + huang_snr_adj) / 10.0)
    sig2_n = 10**(-(snr_db + nar_snr_adj) / 10.0)
    dopplers = rng.uniform(-0.85, 0.85, 3)
    gains = (rng.standard_normal(3)+1j*rng.standard_normal(3))*np.sqrt(np.array([0.5,0.3,0.2])/2); gains /= np.linalg.norm(gains)
    L_cpp = max(delays) + len(f1) + len(g1)  # EXACTLY 2 + 3 + 3 = 8!

    # Dedicated preambles strictly BEFORE data burst (t_offset = -2*(N+L_cpp), -(N+L_cpp) when cont_doppler=True!)
    x_pre_h = const[rng.integers(0, M_qam, N)]
    z_pre_h = rng.standard_normal(N+2) + 1j*rng.standard_normal(N+2)
    r_pre_h = phys_transmit_receive(A.conj().T@x_pre_h, c1, gains, delays, dopplers, f1, f2, g1, g2,
                                    np.sqrt(sig2_h/2)*z_pre_h, t_offset=(-(N+L_cpp) if cont_doppler else 0))
    xp1_n, xp2_n = build_narasimhan_scheme_a_preambles(N)
    z_pre_n1 = rng.standard_normal(N+2) + 1j*rng.standard_normal(N+2)
    z_pre_n2 = rng.standard_normal(N+2) + 1j*rng.standard_normal(N+2)
    r_pre_n1 = phys_transmit_receive(A.conj().T@xp1_n, c1, gains, delays, dopplers, f1, f2, g1, g2,
                                     np.sqrt(sig2_n/2)*z_pre_n1, t_offset=(-2*(N+L_cpp) if cont_doppler else 0))
    r_pre_n2 = phys_transmit_receive(A.conj().T@xp2_n, c1, gains, delays, dopplers, f1, f2, g1, g2,
                                     np.sqrt(sig2_n/2)*z_pre_n2, t_offset=(-(N+L_cpp) if cont_doppler else 0))

    r_list_prop, r_list_h, r_list_n, tx_list_nom, tx_list_prop, s_d_list, s_nom_list, z_w_list = [], [], [], [], [], [], [], []
    same_grid = (Q_g_prop_override is None)
    for k in range(4):
        idx_nom = rng.integers(0, M_qam, len(data_idx_nom))
        x_nom = np.zeros(N, dtype=complex); x_nom[0] = xp_val; x_nom[data_idx_nom] = const[idx_nom]
        s_nom = A.conj().T @ x_nom
        t_off = k * (N + L_cpp) if cont_doppler else 0
        z_w = rng.standard_normal(N+2) + 1j*rng.standard_normal(N+2)
        s_nom_list.append(s_nom); z_w_list.append(z_w)
        r_nom = phys_transmit_receive(s_nom, c1, gains, delays, dopplers, f1, f2, g1, g2, np.sqrt(sig2/2)*z_w, t_offset=t_off)
        r_list_h.append(r_nom if huang_snr_adj == 0.0 else phys_transmit_receive(s_nom, c1, gains, delays, dopplers, f1, f2, g1, g2, np.sqrt(sig2_h/2)*z_w, t_offset=t_off))
        r_list_n.append(r_nom if nar_snr_adj == 0.0 else phys_transmit_receive(s_nom, c1, gains, delays, dopplers, f1, f2, g1, g2, np.sqrt(sig2_n/2)*z_w, t_offset=t_off))
        tx_list_nom.append(idx_nom)
        if same_grid:
            r_list_prop.append(r_nom); tx_list_prop.append(idx_nom)
            x_d = np.zeros(N, dtype=complex); x_d[data_idx_nom] = const[idx_nom]; s_d_list.append(A.conj().T @ x_d)
        else:
            # SCOPE_EqualNetThru: shrink ONLY proposed data grid to Nd=129 (0.48864 sym/cu vs Huang 0.48788 sym/cu)!
            idx_p = idx_nom[Q_g_p - 47 : len(data_idx_nom) - (Q_g_p - 47)]
            x_p = np.zeros(N, dtype=complex); x_p[0] = xp_val; x_p[data_idx_prop] = const[idx_p]
            r_list_prop.append(phys_transmit_receive(A.conj().T@x_p, c1, gains, delays, dopplers, f1, f2, g1, g2, np.sqrt(sig2/2)*z_w, t_offset=t_off))
            tx_list_prop.append(idx_p)
            x_d = np.zeros(N, dtype=complex); x_d[data_idx_prop] = const[idx_p]; s_d_list.append(A.conj().T @ x_d)

    def mser_nom(xl):  return float(np.mean([np.mean(qam_hard(xl[k], const)[1] != tx_list_nom[k]) for k in range(4)]))
    def mser_prop(xl): return float(np.mean([np.mean(qam_hard(xl[k], const)[1] != tx_list_prop[k]) for k in range(4)]))
    pool_H = not cont_doppler
    res = {}
    xd_h, _ = rx_huang_blind(r_pre_h, x_pre_h, r_list_h, rx_cfg_nom)
    res["huang_blind"] = mser_nom(xd_h)
    xd_n, _, _, _ = rx_narasimhan09_blind(r_pre_n1, xp1_n, r_pre_n2, xp2_n, r_list_n, rx_cfg_nom, D=2, L_cpp=L_cpp)
    res["narasimhan_b2"] = mser_nom(xd_n)

    xd_p_it, _, _, diag_p = rx_proposed_blind(r_list_prop, rx_cfg_prop, True, True, True, None, pool_H, 6)
    res["prop_full"] = mser_prop(xd_p_it[-1])
    res["prop_iters"] = [mser_prop(x) for x in xd_p_it]
    res["d_perp"] = diag_p["d_perp"]; res["psi_rank"] = diag_p["psi_rank"]
    res["psi_min_sv"] = diag_p["psi_min_sv"]; res["psi_cond"] = diag_p["psi_cond"]

    H_dir_lin, H_img_lin, G1_rx, G2_rx = build_exact_linear_operators(N, c1, gains, delays, dopplers, f1, f2, g1, g2, t_offset=0)
    Qp = diag_p["Q_perp"]
    res["dir_leak_pow"] = float(np.linalg.norm(Qp.conj().T @ (H_dir_lin @ s_d_list[0]))**2 / max(Qp.shape[1], 1))
    res["img_leak_pow"] = float(np.linalg.norm(Qp.conj().T @ (H_img_lin @ np.conj(s_d_list[0])))**2 / max(Qp.shape[1], 1))

    if full_ablations:
        # STRICT 0.0 Pass-0 H0 & sig2 diff single-mechanism pair: prop_u0_only vs zero_u0_same_sig2 (BOTH use_prefine=False!)
        xd_u_it, _, _, _  = rx_proposed_blind(r_list_prop, rx_cfg_prop, True,  False, True,  None, pool_H, 6)
        xd_z_it, _, _, _  = rx_proposed_blind(r_list_prop, rx_cfg_prop, False, False, True,  None, pool_H, 6)
        xd_rs_it, _, _, _ = rx_proposed_blind(r_list_prop, rx_cfg_prop, False, False, False, None, pool_H, 6)
        xd_fl_it, _, _, _ = rx_proposed_blind(r_list_prop, rx_cfg_prop, True,  True,  True,  1,    pool_H, 6)
        res["prop_u0_only"] = mser_prop(xd_u_it[-1])
        res["prop_u0_only_iters"] = [mser_prop(x) for x in xd_u_it]
        res["zero_u0_same_sig2"] = mser_prop(xd_z_it[-1])
        res["zero_u0_iters"] = [mser_prop(x) for x in xd_z_it]
        res["zero_u0_raw_sig2"] = mser_prop(xd_rs_it[-1])
        res["flat_same"] = mser_prop(xd_fl_it[-1])
        # TRUE PHYSICAL LINEAR-CONV GOLD-STANDARD ORACLE (ZERO 4-tap or circular noise approximation!)
        xd_gold = [exact_wl_ep_detect(r_list_prop[k], None, None, None, A, data_idx_prop, xp_val, const, sig2, n_iter=3,
                                      exact_lin_ops=(H_dir_lin, H_img_lin, G1_rx, G2_rx))[0] for k in range(4)]
        res["oracle_phys_gold"] = mser_prop(xd_gold)
    else:
        xd_z_it, _, _, _ = rx_proposed_blind(r_list_prop, rx_cfg_prop, False, False, True, None, pool_H, 6)
        res["zero_u0_same_sig2"] = mser_prop(xd_z_it[-1])
        xd_fl_it, _, _, _ = rx_proposed_blind(r_list_prop, rx_cfg_prop, True, True, True, 1, pool_H, 6)
        res["flat_same"] = mser_prop(xd_fl_it[-1])

    if paired_zero_iqi_diag and same_grid:
        # Strictly burst-paired zero-IQI decomposition: IDENTICAL channel, payload, and noise draws — ONLY IQI filters toggled!
        f1_0 = np.array([1.0, 0.0, 0.0], dtype=complex); f2_0 = np.zeros(3, dtype=complex)
        g1_0 = np.array([1.0, 0.0, 0.0], dtype=complex); g2_0 = np.zeros(3, dtype=complex)
        r_pre_h0 = phys_transmit_receive(A.conj().T@x_pre_h, c1, gains, delays, dopplers, f1_0, f2_0, g1_0, g2_0, np.sqrt(sig2_h/2)*z_pre_h, t_offset=(-(N+L_cpp) if cont_doppler else 0))
        r_pre_n10 = phys_transmit_receive(A.conj().T@xp1_n, c1, gains, delays, dopplers, f1_0, f2_0, g1_0, g2_0, np.sqrt(sig2_n/2)*z_pre_n1, t_offset=(-2*(N+L_cpp) if cont_doppler else 0))
        r_pre_n20 = phys_transmit_receive(A.conj().T@xp2_n, c1, gains, delays, dopplers, f1_0, f2_0, g1_0, g2_0, np.sqrt(sig2_n/2)*z_pre_n2, t_offset=(-(N+L_cpp) if cont_doppler else 0))
        r_list0 = [phys_transmit_receive(s_nom_list[k], c1, gains, delays, dopplers, f1_0, f2_0, g1_0, g2_0, np.sqrt(sig2/2)*z_w_list[k], t_offset=(k*(N+L_cpp) if cont_doppler else 0)) for k in range(4)]
        xd_h0, _ = rx_huang_blind(r_pre_h0, x_pre_h, r_list0, rx_cfg_nom)
        xd_n0, _, _, _ = rx_narasimhan09_blind(r_pre_n10, xp1_n, r_pre_n20, xp2_n, r_list0, rx_cfg_nom, D=2, L_cpp=L_cpp)
        xd_p0, _, _, _ = rx_proposed_blind(r_list0, rx_cfg_prop, True, True, True, None, pool_H, 6)
        res["paired_zero_huang"] = mser_nom(xd_h0)
        res["paired_zero_nar"]   = mser_nom(xd_n0)
        res["paired_zero_prop"]  = mser_prop(xd_p0[-1])
    return res

# =============================================================================
# 9. Summarization & Main Driver
# =============================================================================
def summarize_regime(res_list, R0_p1=20.0, run_p2=False):
    h  = [r["huang_blind"] for r in res_list]
    nb = [r["narasimhan_b2"] for r in res_list]
    fl = [r["flat_same"] for r in res_list]
    pf = [r["prop_full"] for r in res_list]
    zu = [r["zero_u0_same_sig2"] for r in res_list]
    p1_h = fieller_linear_ci(h,  pf, R0_p1)
    p1_n = fieller_linear_ci(nb, pf, R0_p1)
    out = {
        "n_bursts": len(res_list),
        "mean_ser": {
            "huang_blind": float(np.mean(h)), "narasimhan_b2": float(np.mean(nb)),
            "flat_same": float(np.mean(fl)), "zero_u0_same_sig2": float(np.mean(zu)),
            "prop_full": float(np.mean(pf)),
        },
        "P1_vs_huang": p1_h,
        "P1_vs_narasimhan": p1_n,
        "P1_both_formal_rivals_pass": bool(p1_h["pass_lb"] and p1_h["pass_redline5_hw"] and p1_n["pass_lb"] and p1_n["pass_redline5_hw"]),
        "P1_vs_flat_same_diag": fieller_linear_ci(fl, pf, 20.0),
        "prop_iter_curve": [float(np.mean([r["prop_iters"][i] for r in res_list])) for i in range(6)],
        "nullspace_diag": {
            "d_perp_mean": float(np.mean([r["d_perp"] for r in res_list])),
            "psi_rank_min": int(min(r["psi_rank"] for r in res_list)),
            "psi_min_sv_mean": float(np.mean([r["psi_min_sv"] for r in res_list])),
            "psi_cond_med": float(np.median([r["psi_cond"] for r in res_list])),
            "dir_leak_pow_mean": float(np.mean([r["dir_leak_pow"] for r in res_list])),
            "img_leak_pow_mean": float(np.mean([r["img_leak_pow"] for r in res_list])),
        },
    }
    if "prop_u0_only" in res_list[0]:
        pu = [r["prop_u0_only"] for r in res_list]
        out["mean_ser"]["prop_u0_only"] = float(np.mean(pu))
        out["mean_ser"]["zero_u0_raw_sig2"] = float(np.mean([r["zero_u0_raw_sig2"] for r in res_list]))
        out["mean_ser"]["oracle_phys_gold"] = float(np.mean([r["oracle_phys_gold"] for r in res_list]))
        out["prop_u0_only_iter_curve"] = [float(np.mean([r["prop_u0_only_iters"][i] for r in res_list])) for i in range(6)]
        out["zero_u0_iter_curve"] = [float(np.mean([r["zero_u0_iters"][i] for r in res_list])) for i in range(6)]
    if run_p2:
        fail_zu = [1 if x > 0.01 else 0 for x in zu]
        fail_pu = [1 if r["prop_u0_only"] > 0.01 else 0 for r in res_list]
        fail_pf = [1 if x > 0.01 else 0 for x in pf]
        fail_rs = [1 if r["zero_u0_raw_sig2"] > 0.01 else 0 for r in res_list]

        # P2a: PURE 1-LINE u0 SWITCH (STRICT 0.0 Pass-0 H0 & sig2 difference!)
        t_a = tango1998_paired_diff_ci(fail_zu, fail_pu)
        m_a = t_a["diff_pt"] - 0.05
        hw_a = _json_safe(t_a["hw"] / m_a) if m_a > 0 else None
        p2a_ok = bool(t_a["ci_lo"] >= 0.05 and hw_a is not None and hw_a <= 0.25)

        # P2b: FULL ZERO-DECISION NULLSPACE INIT PACKAGE (u0 + triggered pilot refine)
        t_b = tango1998_paired_diff_ci(fail_zu, fail_pf)
        cp_pf_lo, cp_pf_hi = clopper_pearson_ci(sum(fail_pf), len(fail_pf))
        cp_zu_lo, cp_zu_hi = clopper_pearson_ci(sum(fail_zu), len(fail_zu))
        m_b = t_b["diff_pt"] - 0.10
        hw_b = _json_safe(t_b["hw"] / m_b) if m_b > 0 else None
        p2b_ok = bool(t_b["ci_lo"] >= 0.10 and cp_pf_hi <= 0.05 and hw_b is not None and hw_b <= 0.25)

        out["P2a_PureU0_StrictZeroHDiff"] = {
            **t_a, "fail_count_zero_u0": int(sum(fail_zu)), "fail_count_u0_only": int(sum(fail_pu)),
            "hw_frac_vs_5pp": hw_a, "pass_tango_5pp": bool(t_a["ci_lo"] >= 0.05),
            "pass_redline5_hw": bool(hw_a is not None and hw_a <= 0.25), "pass": p2a_ok,
        }
        out["P2b_FullNullInit_Package"] = {
            **t_b, "fail_count_zero_u0": int(sum(fail_zu)), "fail_count_prop_full": int(sum(fail_pf)),
            "cp95_prop_full": [cp_pf_lo, cp_pf_hi], "cp95_zero_u0": [cp_zu_lo, cp_zu_hi],
            "hw_frac_vs_10pp": hw_b, "pass_tango_10pp": bool(t_b["ci_lo"] >= 0.10),
            "pass_cp_prop_5pct": bool(cp_pf_hi <= 0.05),
            "pass_redline5_hw": bool(hw_b is not None and hw_b <= 0.25), "pass": p2b_ok,
        }
        out["P2_SingleMech_PASS"] = bool(p2a_ok and p2b_ok)
        out["P2_Fieller_SER_Diag"] = {
            "zero_u0_vs_prop_full": fieller_linear_ci(zu, pf, 3.0),
            "zero_u0_vs_u0_only": fieller_linear_ci(zu, [r["prop_u0_only"] for r in res_list], 2.0),
        }
        out["Ablation_Lockout_Counts"] = {
            "zero_u0_same_sig2": int(sum(fail_zu)), "zero_u0_raw_sig2": int(sum(fail_rs)),
            "prop_u0_only": int(sum(fail_pu)), "prop_full": int(sum(fail_pf)),
        }
    if "paired_zero_huang" in res_list[0]:
        zh = [r["paired_zero_huang"] for r in res_list]
        zn = [r["paired_zero_nar"]   for r in res_list]
        zp = [r["paired_zero_prop"]  for r in res_list]
        out["Paired_ZeroIQI_Decomp"] = {
            "huang_zero_iqi_ser": float(np.mean(zh)),
            "huang_wideband_iqi_ser": float(np.mean(h)),
            "huang_paired_iqi_delta_ser": float(np.mean(np.array(h) - np.array(zh))),
            "narasimhan_zero_iqi_ser": float(np.mean(zn)),
            "narasimhan_wideband_iqi_ser": float(np.mean(nb)),
            "narasimhan_paired_iqi_delta_ser": float(np.mean(np.array(nb) - np.array(zn))),
            "prop_zero_iqi_ser": float(np.mean(zp)),
            "prop_wideband_iqi_ser": float(np.mean(pf)),
            "prop_paired_iqi_delta_ser": float(np.mean(np.array(pf) - np.array(zp))),
        }
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    if args.out is None:
        args.out = ("/data/guoyikun/tmp/funnel_m_r13/smoke_m_r13_m01.json" if args.smoke
                    else "/data/guoyikun/tmp/funnel_m_r13/summary_m_r13_m01.json")

    print(f"Python: {sys.executable}", flush=True)
    t0 = time.perf_counter()

    # Exact physical L_cpp = l_max + Lf + Lg = 2 + 3 + 3 = 8 accounting (including exact CPP prefix energy!)
    N, Nd, L_cpp, xp_pow, K = 256, 161, 8, 50.0, 4
    A_acc = daft_matrix(N, 7.0/(2*N), 1.0/(2*np.sqrt(2)*N))
    xp1_acc, xp2_acc = build_narasimhan_scheme_a_preambles(N)
    nar_pfx_e = float(np.sum(np.abs((A_acc.conj().T @ xp1_acc)[-L_cpp:])**2) + np.sum(np.abs((A_acc.conj().T @ xp2_acc)[-L_cpp:])**2))
    cu_prop = K * (N + L_cpp); cu_huang = (K + 1) * (N + L_cpp); cu_nar = (K + 2) * (N + L_cpp)
    e_prop_pfx  = K * (Nd + xp_pow) * (N + L_cpp) / float(N)
    e_huang_pfx = e_prop_pfx + (N + L_cpp)
    e_nar_pfx   = e_prop_pfx + 2 * N + nar_pfx_e
    eb_delta_huang = 10.0 * math.log10(e_huang_pfx / e_prop_pfx)  # +1.1505 dB
    eb_delta_nar   = 10.0 * math.log10(e_nar_pfx / e_prop_pfx)    # +2.1466 dB (exact with prefix energy!)
    throughput_accounting = {
        "N": N, "Nd": Nd, "guard_plus_pilot": N - Nd, "xp_pow": xp_pow, "L_cpp": L_cpp, "K_burst": K,
        "prop_net_sym_per_cu": (K * Nd) / cu_prop,
        "huang_net_sym_per_cu": (K * Nd) / cu_huang,
        "narasimhan_net_sym_per_cu": (K * Nd) / cu_nar,
        "prop_eq_net_thru_sym_per_cu": (K * 129) / cu_prop,
        "prop_spectral_eff_gain_vs_huang": cu_huang / cu_prop,
        "nar_two_preambles_cpp_energy": nar_pfx_e,
        "huang_excess_eb_db": eb_delta_huang,
        "narasimhan_excess_eb_db_with_prefix": eb_delta_nar,
    }

    if args.smoke:
        n_huang, n_nar, n_zero = 12, 16, 8
        n_r1, n_r2, n_scope = 8, 16, 8
        SBASE = 2122000000  # Strictly disjoint from formal seeds 2032000000+!
    else:
        n_huang, n_nar, n_zero = 24, 16, 20
        n_r1, n_r2, n_scope = 60, 340, 60
        SBASE = 2032000000

    with Pool(min(args.workers, 8)) as pool:
        print("\n[1/7] Running Startup Gates & Redline-1 Checks (aborting before formal seeds if False)...", flush=True)
        gates = run_startup_gates(pool, seed_base=SBASE, n_huang=n_huang, n_nar=n_nar, n_zero=n_zero)
        print(f"  GATES_OK = {gates['GATES_OK']} | Huang Fig4 BER={gates['G_R1_Huang_Fig4']['fig4_ber_huang_comp']:.4e} vs noIQ={gates['G_R1_Huang_Fig4']['fig4_ber_no_iqimb']:.4e} | Nar OFDM={gates['G_R1_Narasimhan_OFDM']['ser_static_16qam30_strong13']:.4e}/{gates['G_R1_Narasimhan_OFDM']['ser_mobile005_qpsk25_strong13']:.4e}", flush=True)

        if not gates["GATES_OK"]:
            print("  ABORTING BEFORE FORMAL TARGET SEEDS: GATES_OK == False!", flush=True)
            summary = {
                "script": os.path.basename(__file__), "python": sys.executable, "smoke": bool(args.smoke),
                "elapsed_s": float(time.perf_counter() - t0), "throughput_accounting": throughput_accounting,
                "verdicts": {"GATES_OK": False, "P1_Rivals": False, "P1_FloorPersists_5dB": False, "P2_SingleMech": False, "PASS_PRIMARY": False},
                "gates": gates,
            }
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w") as f: json.dump(summary, f, indent=2, allow_nan=False)
            return

        print(f"\n[2/7] Running R1_Mod18_30dB (n={n_r1}, seeds {SBASE+100000}+, with burst-paired zero-IQI decomp)...", flush=True)
        r1_30 = summarize_regime(pool.map(_worker_burst, [(SBASE+100000+i, "mod18", 64, 30.0, False, False, 0.0, 0.0, None, True) for i in range(n_r1)]), 20.0, False)
        print(f"  R1_30: huang={r1_30['mean_ser']['huang_blind']:.4e} (zeroIQI={r1_30['Paired_ZeroIQI_Decomp']['huang_zero_iqi_ser']:.4e}), nar={r1_30['mean_ser']['narasimhan_b2']:.4e} (zeroIQI={r1_30['Paired_ZeroIQI_Decomp']['narasimhan_zero_iqi_ser']:.4e}), prop={r1_30['mean_ser']['prop_full']:.4e}, both_pass={r1_30['P1_both_formal_rivals_pass']}", flush=True)

        print(f"\n[3/7] Running R1_Mod18_35dB (n={n_r1}, seeds {SBASE+200000}+, with burst-paired zero-IQI decomp)...", flush=True)
        r1_35 = summarize_regime(pool.map(_worker_burst, [(SBASE+200000+i, "mod18", 64, 35.0, False, False, 0.0, 0.0, None, True) for i in range(n_r1)]), 20.0, False)
        print(f"  R1_35: huang={r1_35['mean_ser']['huang_blind']:.4e} (zeroIQI={r1_35['Paired_ZeroIQI_Decomp']['huang_zero_iqi_ser']:.4e}), nar={r1_35['mean_ser']['narasimhan_b2']:.4e}, prop={r1_35['mean_ser']['prop_full']:.4e}, both_pass={r1_35['P1_both_formal_rivals_pass']}", flush=True)

        print(f"\n[4/7] Running R2_Strong13_32dB (n={n_r2}, seeds {SBASE+300000}+, full zero-confounder ablations)...", flush=True)
        r2 = summarize_regime(pool.map(_worker_burst, [(SBASE+300000+i, "strong13", 64, 32.0, False, True, 0.0, 0.0, None, False) for i in range(n_r2)]), 20.0, True)
        p2a = r2["P2a_PureU0_StrictZeroHDiff"]; p2b = r2["P2b_FullNullInit_Package"]
        print(f"  R2_32: huang={r2['mean_ser']['huang_blind']:.4e}, nar={r2['mean_ser']['narasimhan_b2']:.4e}, z0={r2['mean_ser']['zero_u0_same_sig2']:.4e}, u0_only={r2['mean_ser']['prop_u0_only']:.4e}, prop={r2['mean_ser']['prop_full']:.4e}, gold={r2['mean_ser']['oracle_phys_gold']:.4e}", flush=True)
        print(f"  P2a PureU0   : z0={p2a['fail_count_zero_u0']}/{n_r2} vs u0={p2a['fail_count_u0_only']}/{n_r2}, Tango=[{p2a['ci_lo']*100:.2f},{p2a['ci_hi']*100:.2f}]pp, hw_frac={p2a['hw_frac_vs_5pp']}", flush=True)
        print(f"  P2b FullInit : z0={p2b['fail_count_zero_u0']}/{n_r2} vs pf={p2b['fail_count_prop_full']}/{n_r2}, Tango=[{p2b['ci_lo']*100:.2f},{p2b['ci_hi']*100:.2f}]pp, hw_frac={p2b['hw_frac_vs_10pp']}", flush=True)

        print(f"\n[5/7] Running Non-Gating Scope Readouts (ContDoppler + Equal-Eb/N0 + Equal-Net-Thru, n={n_scope})...", flush=True)
        sc_cd = summarize_regime(pool.map(_worker_burst, [(SBASE+400000+i, "strong13", 16, 28.0, True,  False, 0.0, 0.0, None, False) for i in range(n_scope)]), 5.0, False)
        # Fixed Equal-Eb/N0 direction: LOWER rival nominal SNR by exact prefix-inclusive preamble overhead (-1.1505 dB Huang, -2.1466 dB Narasimhan)!
        sc_eq_eb = summarize_regime(pool.map(_worker_burst, [(SBASE+500000+i, "mod18", 64, 30.0, False, False, -eb_delta_huang, -eb_delta_nar, None, False) for i in range(n_scope)]), 20.0, False)
        # Equal-Net-Throughput: prop uses Q_g=63 (Nd=129 -> 0.4886 sym/cu matching Huang's 0.4879 sym/cu!)
        sc_eq_th = summarize_regime(pool.map(_worker_burst, [(SBASE+600000+i, "mod18", 64, 30.0, False, False, 0.0, 0.0, 63, False) for i in range(n_scope)]), 20.0, False)

    print("\n[6/7] Running Non-Gating Auxiliary Vectorized+Cached Banded Timing (1-core)...", flush=True)
    aux_timing = run_aux_timing(SBASE + 90000)

    floor_persists = bool(r1_35["mean_ser"]["huang_blind"] >= 0.5 * r1_30["mean_ser"]["huang_blind"])
    p1_rivals_ok = bool(r1_30["P1_both_formal_rivals_pass"] and r1_35["P1_both_formal_rivals_pass"]
                        and r2["P1_both_formal_rivals_pass"] and floor_persists)
    p2_singlemech_ok = bool(r2["P2_SingleMech_PASS"])
    pass_primary = bool(gates["GATES_OK"] and p1_rivals_ok and p2_singlemech_ok)

    summary = {
        "script": os.path.basename(__file__), "python": sys.executable, "smoke": bool(args.smoke),
        "elapsed_s": float(time.perf_counter() - t0), "throughput_accounting": throughput_accounting,
        "verdicts": {
            "GATES_OK": gates["GATES_OK"], "P1_Rivals": p1_rivals_ok,
            "P1_FloorPersists_5dB": floor_persists, "P2_SingleMech": p2_singlemech_ok,
            "PASS_PRIMARY": pass_primary,
        },
        "gates": gates, "R1_Mod18_30dB": r1_30, "R1_Mod18_35dB": r1_35, "R2_Strong13_32dB": r2,
        "SCOPE_ContDoppler_16QAM_28dB": sc_cd, "SCOPE_EqualEbN0_Mod18_30dB": sc_eq_eb,
        "SCOPE_EqualNetThru_Mod18_30dB": sc_eq_th, "AUX_Timing_1core": aux_timing,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2, allow_nan=False)
    with open(args.out, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    print(f"\n[7/7] === DONE in {summary['elapsed_s']:.1f}s | PASS_PRIMARY={pass_primary} | MD5={md5} ===", flush=True)
    print(json.dumps(summary["verdicts"], indent=2), flush=True)

if __name__ == "__main__":
    main()
