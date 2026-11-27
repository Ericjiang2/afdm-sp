#!/usr/bin/env python3
"""
Round-15 Phase-1 Steelman Teardown Probe for Card I-20261125-m03 (`25-m03`):
Dual-End Wiener Phase Noise in Doubly-Dispersive AFDM — Separated & Adjacent 3-Path Holdout.

Read-only imports frozen `ideas/l2/l2_m_r12_m03_modtest.py` (verifying MD5 `7d174070e3b640583e8ec0e03d948cd1`
without touching any historical script/card/seed).

Tests the required full-strength textbook Steelman baselines on disjoint fresh R15 seeds:
  1. Pub (`AFDM_Xu_LumpPCA_Sym6` / `AFDM_Gavert_Guard_1Step`): published single-end PCA & 1-step dual PCA
  2. Ours_Frozen (`AFDM_EP_Dual_Sym6`): frozen Round-12 `25-m03` receiver
  3. Steelman_CM_PLL2: textbook common-mode 2nd-order decision-directed PLL (forward-backward) + 6-outer OAMP
  4. Steelman_PerPath_PLL2: textbook per-path subband 2nd-order PLL warm-start + multi-branch DD-PLL2 + 6-outer OAMP
  5. Steelman_LagEKF_RTS (`Steelman_A`): textbook 18-state exact Markov lag-line Extended Kalman Filter +
     Rauch-Tung-Striebel smoother ([phi_r[n], phi_t[n], ..., phi_t[n-L_cpp]]) warm-started on per-path
     subband observations and iterated with 6-outer OAMP + blind channel refinement
  6. Steelman_SC_PilEKF (`Steelman_S`): cross-waveform equal-overhead (154/512 distributed time-domain pilots,
     exact same Nd=358 64-QAM payload, L_cpp=16, total energy) Single-Carrier + 18-state EKF-RTS + 6-outer OAMP
  7. Oracles: `AFDM_LumpOrac_Indep` (single-end analytical floor) and `AFDM_DualOrac` / `SC_DualOrac` (full truth)
"""
import os, sys, json, time, math, hashlib, argparse
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
from scipy.linalg import svd as scipy_svd
from scipy.stats import t as student_t
from multiprocessing import Pool

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
L2_DIR = os.path.join(REPO_ROOT, "ideas", "l2")
if L2_DIR not in sys.path:
    sys.path.insert(0, L2_DIR)

FROZEN_M03_PATH = os.path.join(L2_DIR, "l2_m_r12_m03_modtest.py")
FROZEN_M03_MD5 = "7d174070e3b640583e8ec0e03d948cd1"

with open(FROZEN_M03_PATH, "rb") as _fp:
    _actual_md5 = hashlib.md5(_fp.read()).hexdigest()
assert _actual_md5 == FROZEN_M03_MD5, f"MD5 mismatch on {FROZEN_M03_PATH}: {_actual_md5}"

import l2_m_r12_m03_modtest as m3

# Install idempotent exception-only gesvd fallback in memory (zero file modification)
_ORIG_SVD = m3.np.linalg.svd
def _safe_svd(a, full_matrices=True, compute_uv=True, hermitian=False):
    try:
        return _ORIG_SVD(a, full_matrices=full_matrices, compute_uv=compute_uv, hermitian=hermitian)
    except np.linalg.LinAlgError:
        return scipy_svd(a, full_matrices=full_matrices, compute_uv=compute_uv, lapack_driver="gesvd")
m3.np.linalg.svd = _safe_svd


def extract_subband_traces(Y_a, l_vec, sys_cfg):
    """Extract per-path de-chirped pilot subband time-domain traces z_p[n] (100% blind, guard subbands only)."""
    N = sys_cfg["N"]; L_cpp = sys_cfg["L_cpp"]; k_p = sys_cfg["k_p"]
    two_Nc1 = sys_cfg["two_Nc1"]; Ah = sys_cfg["Ah"]; s_p_ext = sys_cfg["s_p_ext"]
    max_hw = sys_cfg["max_hw"]; n_arr = np.arange(N)
    k_cs = [k_p - two_Nc1 * int(l) for l in l_vec]
    z_list = []
    m_bins = []
    for i, l in enumerate(l_vec):
        k_hi = min(k_cs[i] + max_hw, (k_cs[i] + k_cs[i - 1]) // 2) if i > 0 else k_cs[i] + max_hw
        k_lo = max(k_cs[i] - max_hw, (k_cs[i] + k_cs[i + 1]) // 2 + 1) if i < len(l_vec) - 1 else k_cs[i] - max_hw
        m = np.zeros(N, dtype=bool); m[k_lo : k_hi + 1] = True
        Ys = np.zeros(N, dtype=complex); Ys[m] = Y_a[m]
        zp = (Ah @ Ys) * np.conj(s_p_ext[L_cpp + n_arr - int(l)])
        z_list.append(zp)
        m_bins.append(int(m.sum()))
    return np.asarray(z_list), np.asarray(m_bins)


def pll2_forward_backward_1d(z_obs, u_ref, sig2_obs, sig_w=3.0e-3):
    """Textbook 2nd-order Type-II PLL (forward + backward zero-lag average) on y[n] ~ exp(j*phi[n])*u_ref[n]."""
    N = len(z_obs)
    # Optimal steady-state Kalman/PLL gain for random-walk + small frequency drift:
    # K1 ~ sqrt(sig_w / R_n), K2 = 0.25 * K1^2 (critically damped zeta = 1/sqrt(2))
    def _pass(z_seq, u_seq, p0):
        phi = np.empty(N, dtype=float)
        th = float(p0)
        om = 0.0
        for n in range(N):
            pred = th + om
            un = u_seq[n]
            p_u = float(np.abs(un) ** 2)
            rn = max(sig2_obs, 1e-6) / max(2.0 * p_u, 1e-9)
            k1 = min(math.sqrt(sig_w / (sig_w + rn)), 0.65)
            k2 = 0.20 * k1 * k1
            err = float(np.angle(z_seq[n] * np.conj(un) * np.exp(-1j * pred))) if p_u > 1e-10 else 0.0
            th = pred + k1 * err
            om = om + k2 * err
            phi[n] = th
        return phi

    # Initial phase anchor at midpoint / edges
    mid = N // 2
    p_init_f = float(np.angle(np.vdot(u_ref[:16], z_obs[:16])))
    p_init_b = float(np.angle(np.vdot(u_ref[-16:], z_obs[-16:])))
    pf = _pass(z_obs, u_ref, p_init_f)
    pb = _pass(z_obs[::-1], u_ref[::-1], p_init_b)[::-1]
    # Unwrap pb to align with pf at midpoint before averaging
    pb += np.round((pf[mid] - pb[mid]) / (2.0 * np.pi)) * (2.0 * np.pi)
    # Unwrap sample-by-sample difference
    diff = np.angle(np.exp(1j * (pb - pf)))
    return pf + 0.5 * diff


def pll2_multibranch_dd(y, H_lin, s_ext_hat, theta_init, sig2_eff, L_cpp, l_vec, sig_w=3.0e-3, n_sweeps=2):
    """Textbook multi-branch per-path 2nd-order DD-PLL (tracks theta_p[n] = phi_r[n] + phi_t[n - l_p])."""
    N = len(y); P = len(l_vec); n_arr = np.arange(N)
    c_mat = np.array([H_lin[n_arr, L_cpp + n_arr - int(l)] * s_ext_hat[L_cpp + n_arr - int(l)] for l in l_vec])  # (P, N)
    th_cur = theta_init.copy()  # (P, N)

    for _ in range(n_sweeps):
        # Forward pass
        th_f = np.empty_like(th_cur)
        th = th_cur[:, 0].copy()
        om = np.zeros(P, dtype=float)
        for n in range(N):
            pred = th + om
            cn = c_mat[:, n]
            yhat = np.sum(np.exp(1j * pred) * cn)
            res = y[n] - yhat
            denom = float(np.sum(np.abs(cn) ** 2)) + max(sig2_eff, 1e-5)
            for p in range(P):
                # Phase discriminator for path p
                e_p = float(np.imag(np.conj(np.exp(1j * pred[p]) * cn[p]) * res)) / denom
                k1 = min(math.sqrt(sig_w / (sig_w + max(sig2_eff, 1e-5) / max(2.0 * abs(cn[p])**2, 1e-6))), 0.55)
                k2 = 0.15 * k1 * k1
                th[p] = pred[p] + k1 * np.clip(e_p, -0.5, 0.5)
                om[p] = om[p] + k2 * np.clip(e_p, -0.5, 0.5)
            th_f[:, n] = th

        # Backward pass
        th_b = np.empty_like(th_cur)
        th = th_f[:, -1].copy()
        om = np.zeros(P, dtype=float)
        for n in range(N - 1, -1, -1):
            pred = th + om
            cn = c_mat[:, n]
            yhat = np.sum(np.exp(1j * pred) * cn)
            res = y[n] - yhat
            denom = float(np.sum(np.abs(cn) ** 2)) + max(sig2_eff, 1e-5)
            for p in range(P):
                e_p = float(np.imag(np.conj(np.exp(1j * pred[p]) * cn[p]) * res)) / denom
                k1 = min(math.sqrt(sig_w / (sig_w + max(sig2_eff, 1e-5) / max(2.0 * abs(cn[p])**2, 1e-6))), 0.55)
                k2 = 0.15 * k1 * k1
                th[p] = pred[p] + k1 * np.clip(e_p, -0.5, 0.5)
                om[p] = om[p] + k2 * np.clip(e_p, -0.5, 0.5)
            th_b[:, n] = th

        mid = N // 2
        for p in range(P):
            th_b[p] += np.round((th_f[p, mid] - th_b[p, mid]) / (2.0 * np.pi)) * (2.0 * np.pi)
            th_cur[p] = th_f[p] + 0.5 * np.angle(np.exp(1j * (th_b[p] - th_f[p])))
    return th_cur


def ekf_rts_lag_subband_init(z_sub, m_bins, h_init, nu_init, l_vec, sig2_init, L_cpp, sig_r, sig_t, n_passes=4):
    """
    Textbook Iterated Extended Kalman Smoother (IEKS, Bell & Cathey IEEE TAC 1993) on the EXACT Markov lag state:
      xi[n] = [phi_r[n], phi_t[n], phi_t[n-1], ..., phi_t[n - L_cpp]]^T in R^{L_cpp + 2},
    applied to the P-dimensional subband pilot traces z_p[n] (guard subbands ONLY).
    Linearizes at each pass around the current smoothed trajectory xi_nom[n] (eliminating causal cycle slips!).
    """
    P_cnt, N = z_sub.shape
    D = L_cpp + 2
    B = N + L_cpp
    n_arr = np.arange(N)

    F = np.zeros((D, D), dtype=float)
    F[0, 0] = 1.0
    F[1, 1] = 1.0
    for l in range(1, L_cpp + 1):
        F[1 + l, l] = 1.0
    Q = np.zeros((D, D), dtype=float)
    Q[0, 0] = max(sig_r, 1e-9)
    Q[1, 1] = max(sig_t, 1e-9)

    r_var_p = np.maximum(sig2_init * (m_bins / float(N)) * 1.5, 1e-4)
    R_inv_diag = 2.0 / r_var_p

    z_mrc = np.zeros(N, dtype=complex)
    for i in range(P_cnt):
        z_mrc += z_sub[i] * np.conj(h_init[i]) * np.exp(1j * 2.0 * np.pi * nu_init[i] * n_arr / N)
    pi = m3.zero_unwrap_complex(z_mrc[L_cpp : N - L_cpp])
    pr_cur = np.empty(N, dtype=float)
    pr_cur[L_cpp : N - L_cpp] = pi; pr_cur[:L_cpp] = pi[0]; pr_cur[N - L_cpp:] = pi[-1]
    pt_cur = np.zeros(B, dtype=float)

    n_guard_est = max(float(np.sum(np.abs(z_sub[:, L_cpp:N-L_cpp])**2) / (N - 2*L_cpp)) / max(float(np.sum(np.abs(h_init)**2)), 1e-6), 1e-4)
    c_base = np.array([h_init[i] * math.sqrt(n_guard_est) * np.exp(-1j * 2.0 * np.pi * nu_init[i] * n_arr / N) for i in range(P_cnt)])
    # Match exact scale of zp[n]: in m3, |s_p_ext|^2 = n_guard / N, so E[zp[n]] = h_p * (n_guard / N) * exp(-j2pi nu_p n / N)!
    # Estimate exact scalar gain g_scale from inner product with z_sub!
    num_sc = sum(np.vdot(np.exp(1j * pr_cur) * np.exp(-1j * 2.0 * np.pi * nu_init[i] * n_arr / N) * h_init[i], z_sub[i]) for i in range(P_cnt))
    den_sc = sum(np.vdot(h_init[i] * np.ones(N), h_init[i] * np.ones(N)) for i in range(P_cnt))
    g_sc = max(float(np.abs(num_sc) / max(float(np.real(den_sc)), 1e-9)), 1e-4)
    c_base = np.array([h_init[i] * g_sc * np.exp(-1j * 2.0 * np.pi * nu_init[i] * n_arr / N) for i in range(P_cnt)])

    for _ in range(n_passes):
        xi_nom = np.empty((N, D), dtype=float)
        xi_nom[:, 0] = pr_cur
        for l in range(L_cpp + 1):
            xi_nom[:, 1 + l] = pt_cur[L_cpp - l : L_cpp - l + N]

        x_filt = np.zeros((N, D), dtype=float)
        P_filt = np.zeros((N, D, D), dtype=float)
        x_pred_arr = np.zeros((N, D), dtype=float)
        P_pred_arr = np.zeros((N, D, D), dtype=float)

        for n in range(N):
            if n == 0:
                xp = xi_nom[0].copy()
                Pp = 10.0 * np.eye(D)
                Pp[1, 1] = 1e-3  # gauge anchor on pt[L_cpp]
            else:
                xp = F @ x_filt[n - 1]
                Pp = F @ P_filt[n - 1] @ F.T + Q
            x_pred_arr[n] = xp
            P_pred_arr[n] = Pp

            # IEKS: linearize around xi_nom[n]: y_eff = y - h(xi_nom) + H_n (xi_nom - xp)
            x_lin = xi_nom[n]
            H_re = np.zeros((P_cnt, D), dtype=float)
            H_im = np.zeros((P_cnt, D), dtype=float)
            innov_re = np.zeros(P_cnt, dtype=float)
            innov_im = np.zeros(P_cnt, dtype=float)
            d_nom_xp = x_lin - xp
            for i, l in enumerate(l_vec):
                idx_t = 1 + int(l)
                th_i = x_lin[0] + x_lin[idx_t]
                pred_i = c_base[i, n] * np.exp(1j * th_i)
                ri = z_sub[i, n] - pred_i
                deriv = 1j * pred_i
                H_re[i, 0] = deriv.real; H_re[i, idx_t] = deriv.real
                H_im[i, 0] = deriv.imag; H_im[i, idx_t] = deriv.imag
                sh_p = d_nom_xp[0] + d_nom_xp[idx_t]
                innov_re[i] = ri.real + deriv.real * sh_p
                innov_im[i] = ri.imag + deriv.imag * sh_p

            HtRH = (H_re.T * R_inv_diag[None, :]) @ H_re + (H_im.T * R_inv_diag[None, :]) @ H_im
            HtRr = H_re.T @ (R_inv_diag * innov_re) + H_im.T @ (R_inv_diag * innov_im)
            if n == 0:
                HtRH[1, 1] += 1e3
                HtRr[1] += 1e3 * (0.0 - xp[1])
            P_post = np.linalg.solve(np.eye(D) + Pp @ HtRH, Pp)
            P_post = 0.5 * (P_post + P_post.T)
            x_filt[n] = xp + P_post @ HtRr
            P_filt[n] = P_post

        x_sm = np.empty_like(x_filt)
        x_sm[-1] = x_filt[-1]
        for n in range(N - 2, -1, -1):
            C_n = np.linalg.solve(P_pred_arr[n + 1] + 1e-9 * np.eye(D), F @ P_filt[n]).T
            x_sm[n] = x_filt[n] + C_n @ (x_sm[n + 1] - x_pred_arr[n + 1])

        step_pr = np.clip(x_sm[:, 0] - pr_cur, -0.45, 0.45)
        pr_cur = pr_cur + step_pr
        pt_target = np.zeros(B, dtype=float)
        pt_target[L_cpp:] = x_sm[:, 1]
        for l in range(1, L_cpp + 1):
            pt_target[L_cpp - l] = x_sm[0, 1 + l]
        pt_cur = pt_cur + np.clip(pt_target - pt_cur, -0.45, 0.45)
        sg = pt_cur[L_cpp]
        pt_cur -= sg
        pr_cur += sg
    return pr_cur, pt_cur


def ekf_rts_lag_timedomain(y, H_lin, s_ext_hat, pr_init, pt_init, sig2_eff, sig_r, sig_t, L_cpp, l_vec, n_sweeps=3, obs_mask=None):
    """
    Textbook Iterated Extended Kalman Filter + RTS Smoother (IEKS, Bell & Cathey IEEE TAC 1993)
    on time-domain scalar observations y[n] = sum_p exp(j*(xi_0[n] + xi_{1+l_p}[n])) * c_p[n] + v[n]
    with exact 18-state Markov lag vector xi[n] = [phi_r[n], phi_t[n], ..., phi_t[n-L_cpp]]^T.
    Linearizes around the current smoothed trajectory xi_nom[n] at each sweep -> exact Gauss-Newton / MAP
    equivalence in O(N * D^2) sequential Kalman smoothing!
    """
    N, B = H_lin.shape
    D = L_cpp + 2
    n_arr = np.arange(N)
    l_list = [int(l) for l in l_vec]
    c_tap = np.array([H_lin[n_arr, L_cpp + n_arr - l] * s_ext_hat[L_cpp + n_arr - l] for l in l_list])

    F = np.zeros((D, D), dtype=float)
    F[0, 0] = 1.0
    F[1, 1] = 1.0
    for l in range(1, L_cpp + 1):
        F[1 + l, l] = 1.0
    Q = np.zeros((D, D), dtype=float)
    Q[0, 0] = max(sig_r, 1e-9)
    Q[1, 1] = max(sig_t, 1e-9)
    r_var = 0.5 * max(sig2_eff, 1e-6)

    pr = pr_init.copy()
    pt = pt_init.copy()

    for _ in range(n_sweeps):
        xi_nom = np.empty((N, D), dtype=float)
        xi_nom[:, 0] = pr
        for l in range(L_cpp + 1):
            xi_nom[:, 1 + l] = pt[L_cpp - l : L_cpp - l + N]

        x_filt = np.empty((N, D), dtype=float)
        P_filt = np.empty((N, D, D), dtype=float)
        x_pred = np.empty((N, D), dtype=float)
        P_pred = np.empty((N, D, D), dtype=float)

        for n in range(N):
            if n == 0:
                xp = xi_nom[0].copy()
                Pp = 10.0 * np.eye(D)
                Pp[1, 1] = 1e-3  # gauge anchor on pt[L_cpp]
            else:
                xp = F @ x_filt[n - 1]
                Pp = F @ P_filt[n - 1] @ F.T + Q
            x_pred[n] = xp
            P_pred[n] = Pp
            if obs_mask is not None and not obs_mask[n]:
                x_filt[n] = xp
                P_filt[n] = Pp
                continue

            x_lin = xi_nom[n]
            h_re = np.zeros(D, dtype=float)
            h_im = np.zeros(D, dtype=float)
            yhat = 0.0 + 0.0j
            for p_idx, l in enumerate(l_list):
                it = 1 + l
                term = c_tap[p_idx, n] * np.exp(1j * (x_lin[0] + x_lin[it]))
                yhat += term
                dterm = 1j * term
                h_re[0] += dterm.real; h_re[it] += dterm.real
                h_im[0] += dterm.imag; h_im[it] += dterm.imag

            H_n = np.vstack([h_re, h_im])
            res_raw = np.array([(y[n] - yhat).real, (y[n] - yhat).imag], dtype=float)
            innov = res_raw + H_n @ (x_lin - xp)

            HP = H_n @ Pp
            S = r_var * np.eye(2) + HP @ H_n.T
            K = np.linalg.solve(S, HP).T
            x_filt[n] = xp + K @ innov
            P_post = Pp - K @ HP
            P_filt[n] = 0.5 * (P_post + P_post.T)

        x_sm = np.empty_like(x_filt)
        x_sm[-1] = x_filt[-1]
        for n in range(N - 2, -1, -1):
            C_n = np.linalg.solve(P_pred[n + 1] + 1e-9 * np.eye(D), F @ P_filt[n]).T
            x_sm[n] = x_filt[n] + C_n @ (x_sm[n + 1] - x_pred[n + 1])

        pr = pr + np.clip(x_sm[:, 0] - pr, -0.4, 0.4)
        pt_target = np.zeros(B, dtype=float)
        pt_target[L_cpp:] = x_sm[:, 1]
        for l in range(1, L_cpp + 1):
            pt_target[L_cpp - l] = x_sm[0, 1 + l]
        pt = pt + np.clip(pt_target - pt, -0.4, 0.4)
        sg = pt[L_cpp]
        pt -= sg
        pr += sg
    return pr, pt


def run_teardown_frame(args):
    seed, cfg = args
    rng = np.random.default_rng(seed)
    N = cfg["N"]; L_cpp = cfg["L_cpp"]; B = N + L_cpp; two_Nc1 = cfg["two_Nc1"]
    c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2 * np.pi * N)
    snr_db = cfg["snr_db"]; sig_r = cfg["sig_r"]; sig_t = cfg["sig_t"]
    mode = cfg["mode"]  # 'prior_clean', 'single_frame', 'prior_pn'
    mid_delay = int(cfg["mid_delay"])

    A_a = m3.daft_matrix(N, c1, c2); Ah_a = A_a.conj().T; P_a = m3.build_cpp_ext(N, c1, L_cpp)
    I_N = np.eye(N, dtype=complex)
    P_sc = m3.build_cpp_ext(N, 0.0, L_cpp)  # standard CP for Single-Carrier
    g8 = np.array([-7, -5, -3, -1, 1, 3, 5, 7]); pts64 = (g8[:, None] + 1j * g8[None, :]).ravel() / np.sqrt(42.0)
    qpsk = np.array([-1-1j, -1+1j, 1-1j, 1+1j]) / np.sqrt(2.0)

    k_p = N // 2
    g_lo, g_hi = cfg["g_lo"], cfg["g_hi"]
    obs_lo, obs_hi = cfg["obs_lo"], cfg["obs_hi"]
    max_hw = cfg["max_hw"]
    guard = np.zeros(N, dtype=bool); guard[g_lo:g_hi] = True
    data_mask = ~guard; n_guard = int(guard.sum()); Nd = int(data_mask.sum())
    pilot_obs = np.zeros(N, dtype=bool); pilot_obs[obs_lo:obs_hi] = True

    # 3GPP TS 38.211 Hybrid UW + Distributed TD-PTRS Single-Carrier layout (exact same 154 pilot slots & Nd=358!):
    # - 1 compact 48-sample Unique Word [0..47] (gives 32 ZERO-data-interference samples [16..47] to resolve ANY integer
    #   delays including adjacent [0, 1, 16]!)
    # - 106 distributed TD-PTRS pilot samples uniformly spaced every ~4.3 samples across [48..511] (max gap = 4 samples ->
    #   Wiener Brownian-bridge interpolation error < 2.5 deg across the entire block!)
    sc_pil_mask = np.zeros(N, dtype=bool)
    sc_pil_mask[:48] = True
    ptrs_idx = np.round(np.linspace(50, N - 2, n_guard - 48)).astype(int)
    sc_pil_mask[ptrs_idx] = True
    while int(sc_pil_mask.sum()) < n_guard:
        cand = int(np.where(~sc_pil_mask)[0][0])
        sc_pil_mask[cand] = True
    assert int(sc_pil_mask.sum()) == n_guard
    sc_data_mask = ~sc_pil_mask

    x_p = np.zeros(N, dtype=complex); x_p[k_p] = np.sqrt(float(n_guard))
    sp_a = P_a @ (Ah_a @ x_p)
    pca = m3.build_pca_bases(N, L_cpp, K_pca=18 if N == 512 else 14)

    sig_r_prior = 1.5e-3; sig_t_prior = 1.5e-3
    sys_cfg = dict(N=N, L_cpp=L_cpp, two_Nc1=two_Nc1, k_p=k_p, A=A_a, Ah=Ah_a,
                   s_p_ext=sp_a, n_guard=n_guard, max_hw=max_hw, pilot_obs=pilot_obs,
                   sig_r_prior=sig_r_prior, sig_t_prior=sig_t_prior)

    ls_t = np.array([0, mid_delay, 16], dtype=int)
    pdp = np.array([0.4225, 0.3025, 0.2750])
    P_cnt = len(ls_t)
    nus_t = rng.uniform(-0.4, 0.4, P_cnt)
    hs_t = np.sqrt(pdp) * np.exp(1j * rng.uniform(0, 2 * np.pi, P_cnt))
    H_lin_t = m3.build_H_ext(N, L_cpp, hs_t, ls_t, nus_t)
    sig2_true = 10.0 ** (-snr_db / 10.0)

    phi_t = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)) if sig_t > 0 else np.zeros(B); phi_t -= phi_t[L_cpp]
    phi_r = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N)) if sig_r > 0 else np.zeros(N)
    w = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    xd_vals = pts64[rng.integers(0, 64, Nd)]

    # AFDM frame
    x_a = x_p.copy(); x_a[data_mask] = xd_vals
    s_ext_a = P_a @ (Ah_a @ x_a)
    y_a = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ext_a)) + w
    Y_a = A_a @ y_a

    # Single-Carrier frame (exact same Nd=358 xd_vals, unit-power distributed pilots -> exact total energy N!)
    pil_sc_vals = qpsk[rng.integers(0, 4, n_guard)]
    x_sc = np.zeros(N, dtype=complex); x_sc[sc_data_mask] = xd_vals; x_sc[sc_pil_mask] = pil_sc_vals
    xp_sc = np.where(sc_pil_mask, x_sc, 0.0)
    sp_sc = P_sc @ xp_sc
    s_ext_sc = P_sc @ x_sc
    y_sc = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ext_sc)) + w

    # Blind channel & noise initialization (identical to frozen m3)
    refine_ch_in_loop = (mode in ("single_frame", "prior_pn"))
    y_tr_sc = None
    sp_tr_sc = None
    if mode == "single_frame":
        sig2_hat, l_h, h_h, nu_h, phi_mrc = m3.blind_single_frame_init(Y_a, sys_cfg)
    else:
        w_tr = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        x_tr_sc = qpsk[rng.integers(0, 4, N)]
        sp_tr_sc = P_sc @ x_tr_sc
        if mode == "prior_pn" and (sig_r > 0 or sig_t > 0):
            pt_tr = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)); pt_tr -= pt_tr[L_cpp]
            pr_tr = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N))
            y_tr = np.exp(1j * pr_tr) * (H_lin_t @ (np.exp(1j * pt_tr) * sp_a)) + w_tr
            y_tr_sc = np.exp(1j * pr_tr) * (H_lin_t @ (np.exp(1j * pt_tr) * sp_tr_sc)) + w_tr
            sig2_hat, l_h, h_h, nu_h = m3.blind_ce_from_training(y_tr, sys_cfg, training_has_pn=True)
        else:
            y_tr = H_lin_t @ sp_a + w_tr
            y_tr_sc = H_lin_t @ sp_tr_sc + w_tr
            sig2_hat, l_h, h_h, nu_h = m3.blind_ce_from_training(y_tr, sys_cfg, training_has_pn=False)
        H_p0 = [m3.build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]
        k_cs = [k_p - two_Nc1 * int(l) for l in l_h]
        z_mrc = np.zeros(N, dtype=complex)
        for i in range(len(l_h)):
            k_hi = min(k_cs[i] + max_hw, (k_cs[i] + k_cs[i - 1]) // 2) if i > 0 else k_cs[i] + max_hw
            k_lo = max(k_cs[i] - max_hw, (k_cs[i] + k_cs[i + 1]) // 2 + 1) if i < len(l_h) - 1 else k_cs[i] - max_hw
            m = np.zeros(N, dtype=bool); m[k_lo : k_hi + 1] = True
            Ys = np.zeros(N, dtype=complex); Ys[m] = Y_a[m]
            z_mrc += (Ah_a @ Ys) * np.conj(H_p0[i] @ sp_a)
        pi = m3.zero_unwrap_complex(z_mrc[L_cpp : N - L_cpp])
        phi_mrc = np.empty(N); phi_mrc[L_cpp : N - L_cpp] = pi; phi_mrc[:L_cpp] = pi[0]; phi_mrc[N - L_cpp:] = pi[-1]

    H_lin_h = m3.build_H_ext(N, L_cpp, h_h, l_h, nu_h)
    H_circ_h = H_lin_h @ P_a
    H_paths_h = [m3.build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]

    def ser(xh, xt, dm):
        return float(np.mean(np.abs(xh[dm] - xt[dm]) > 1e-3))

    out = {"mid_delay": mid_delay, "det_delays": [int(v) for v in l_h], "n_data_syms": Nd}

    # --- Arm 1: Pub (`AFDM_Xu_LumpPCA_Sym6`) ---
    if refine_ch_in_loop:
        phi_l = m3.exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_lin_h, sp_a, phi_mrc,
                                            max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 3)
        hl_c, nul_c = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, phi_l, np.zeros(B), l_h, nu_h, L_cpp)
        phi_l = m3.exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], m3.build_H_ext(N, L_cpp, hl_c, l_h, nul_c), sp_a, phi_l,
                                            max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 3)
    else:
        phi_l = m3.exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_lin_h, sp_a, phi_mrc,
                                            max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 6)
        hl_c, nul_c = h_h.copy(), nu_h.copy()
    s2l = sig2_hat; gam_l = np.maximum(np.abs(hl_c) ** 2, 1e-3)
    best_rl = np.inf; best_xhl = None
    for out_i in range(6):
        Hcl = m3.build_H_ext(N, L_cpp, hl_c, l_h, nul_c) @ P_a
        xs_l, xhc_l, vxl, _ = m3.oamp_exact(y_a * np.exp(-1j * phi_l), Hcl, Ah_a, max(s2l, 1e-6) + 0.02 * (0.6 ** out_i), pts64, data_mask, x_p, 8)
        phi_l = m3.gn_lumped(y_a, Hcl, Ah_a @ xs_l, phi_l, max(s2l, 1e-6) + 0.5 * vxl, sig_r_prior + sig_t_prior, 3)
        if out_i >= 1:
            hl_c, nul_c, gam_l, s2l_em = m3.refine_channel_sbl_em(y_a, P_a @ (Ah_a @ xs_l), phi_l, np.zeros(B), l_h, nul_c, gam_l, max(s2l, 1e-6) + 0.5 * vxl, L_cpp)
        else:
            s2l_em = s2l
        Hcl2 = m3.build_H_ext(N, L_cpp, hl_c, l_h, nul_c) @ P_a
        rl_hard = float(np.sum(np.abs(y_a * np.exp(-1j * phi_l) - Hcl2 @ (Ah_a @ xhc_l)) ** 2))
        s2l = float(np.clip(max(s2l_em, rl_hard / N), 1e-5 if refine_ch_in_loop else max(sig2_hat * 0.4, 1e-6), 0.05))
        if rl_hard < best_rl: best_rl = rl_hard; best_xhl = xhc_l
    out["Pub_Xu_LumpPCA"] = ser(best_xhl, x_a, data_mask)

    # --- Arm 2: Frozen `25-m03` (`AFDM_EP_Dual_Sym6`) ---
    def run_dual_outer_m3(pr0, pt0, h0, nu0):
        pr_c, pt_c = pr0.copy(), pt0.copy()
        h_c, nu_c = h0.copy(), nu0.copy()
        s2 = sig2_hat; best_r = np.inf; best_xh = None
        for out_idx in range(6):
            Hl = m3.build_H_ext(N, L_cpp, h_c, l_h, nu_c)
            Hc = np.exp(1j * pr_c)[:, None] * ((Hl * np.exp(1j * pt_c)[None, :]) @ P_a)
            xs, xhc, vx, _ = m3.oamp_exact(y_a, Hc, Ah_a, max(s2, 1e-6) + 0.02 * (0.6 ** out_idx), pts64, data_mask, x_p, 8)
            s_ext_s = P_a @ (Ah_a @ xs)
            pr_c, pt_c = m3.gn_dual_banded(y_a, Hl, s_ext_s, pr_c, pt_c, max(s2, 1e-6) + 0.5 * vx, sig_r_prior, sig_t_prior, L_cpp, 3)
            if refine_ch_in_loop and out_idx >= 1:
                h_c, nu_c = m3.refine_channel_blind(y_a, s_ext_s, pr_c, pt_c, l_h, nu_c, L_cpp)
            Hl2 = m3.build_H_ext(N, L_cpp, h_c, l_h, nu_c)
            rc = float(np.sum(np.abs(y_a - np.exp(1j * pr_c) * (Hl2 @ (np.exp(1j * pt_c) * (P_a @ (Ah_a @ xhc))))) ** 2))
            s2 = float(np.clip(rc / N, 1e-5 if refine_ch_in_loop else max(sig2_hat * 0.4, 1e-6), 0.05))
            if rc < best_r: best_r = rc; best_xh = xhc
        return best_xh

    if refine_ch_in_loop:
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                                 phi_mrc, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        h_sf2, nu_sf2 = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, pr_ep, pt_ep, l_h, nu_h, L_cpp)
        H_p_sf2 = [m3.build_H_ext(N, L_cpp, [h_sf2[i]], [l_h[i]], [nu_sf2[i]]) for i in range(len(l_h))]
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_p_sf2, l_h, sp_a,
                                                 pr_ep, pt_ep, 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        out["Ours_EP_Dual_Sym6"] = ser(run_dual_outer_m3(pr_ep, pt_ep, h_sf2, nu_sf2), x_a, data_mask)
    else:
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                                 phi_mrc, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        out["Ours_EP_Dual_Sym6"] = ser(run_dual_outer_m3(pr_ep, pt_ep, h_h, nu_h), x_a, data_mask)

    # --- Arm 3: Steelman_CM_PLL2 (Common-mode 2nd-order FB-PLL + 6-outer OAMP) ---
    phi_cm = phi_mrc.copy()
    hc_cm, nuc_cm = h_h.copy(), nu_h.copy()
    if refine_ch_in_loop:
        hc_cm, nuc_cm = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, phi_cm, np.zeros(B), l_h, nu_h, L_cpp)
    s2_cm = sig2_hat; best_rcm = np.inf; best_xh_cm = None
    for out_i in range(6):
        H_cm = m3.build_H_ext(N, L_cpp, hc_cm, l_h, nuc_cm) @ P_a
        xs_cm, xhc_cm, vx_cm, _ = m3.oamp_exact(y_a * np.exp(-1j * phi_cm), H_cm, Ah_a, max(s2_cm, 1e-6) + 0.02 * (0.6 ** out_i), pts64, data_mask, x_p, 8)
        u_cm = H_cm @ (Ah_a @ xs_cm)
        phi_cm = pll2_forward_backward_1d(y_a, u_cm, max(s2_cm, 1e-6) + 0.5 * vx_cm, sig_r_prior + sig_t_prior)
        if refine_ch_in_loop and out_i >= 1:
            hc_cm, nuc_cm = m3.refine_channel_blind(y_a, P_a @ (Ah_a @ xs_cm), phi_cm, np.zeros(B), l_h, nuc_cm, L_cpp)
        H_cm2 = m3.build_H_ext(N, L_cpp, hc_cm, l_h, nuc_cm) @ P_a
        rcm = float(np.sum(np.abs(y_a * np.exp(-1j * phi_cm) - H_cm2 @ (Ah_a @ xhc_cm)) ** 2))
        s2_cm = float(np.clip(rcm / N, 1e-5 if refine_ch_in_loop else max(sig2_hat * 0.4, 1e-6), 0.05))
        if rcm < best_rcm: best_rcm = rcm; best_xh_cm = xhc_cm
    out["Steelman_CM_PLL2"] = ser(best_xh_cm, x_a, data_mask)

    # --- Arm 4: Steelman_PerPath_PLL2 (Per-path subband 2nd-order FB-PLL + multi-branch DD-PLL2 + 6-outer OAMP) ---
    z_sub, m_bins = extract_subband_traces(Y_a, l_h, sys_cfg)
    n_arr = np.arange(N)
    n_g_scale = float(n_guard) / float(N)
    th_pp = np.zeros((len(l_h), N), dtype=float)
    for i in range(len(l_h)):
        u_sub_i = h_h[i] * n_g_scale * np.exp(-1j * 2.0 * np.pi * nu_h[i] * n_arr / N)
        th_pp[i] = pll2_forward_backward_1d(z_sub[i], u_sub_i, max(sig2_hat * m_bins[i] / N, 1e-5), sig_r_prior + sig_t_prior)
    hc_pp, nuc_pp = h_h.copy(), nu_h.copy()
    s2_pp = sig2_hat; best_rpp = np.inf; best_xh_pp = None
    for out_i in range(6):
        Hl_pp = m3.build_H_ext(N, L_cpp, hc_pp, l_h, nuc_pp)
        H_eff_td = np.zeros((N, B), dtype=complex)
        for i, l in enumerate(l_h):
            H_eff_td[n_arr, L_cpp + n_arr - int(l)] += Hl_pp[n_arr, L_cpp + n_arr - int(l)] * np.exp(1j * th_pp[i])
        Hc_pp = H_eff_td @ P_a
        xs_pp, xhc_pp, vx_pp, _ = m3.oamp_exact(y_a, Hc_pp, Ah_a, max(s2_pp, 1e-6) + 0.02 * (0.6 ** out_i), pts64, data_mask, x_p, 8)
        s_ext_pp = P_a @ (Ah_a @ xs_pp)
        th_pp = pll2_multibranch_dd(y_a, Hl_pp, s_ext_pp, th_pp, max(s2_pp, 1e-6) + 0.5 * vx_pp, L_cpp, l_h, sig_r_prior + sig_t_prior, 2)
        H_eff_td2 = np.zeros((N, B), dtype=complex)
        for i, l in enumerate(l_h):
            H_eff_td2[n_arr, L_cpp + n_arr - int(l)] += Hl_pp[n_arr, L_cpp + n_arr - int(l)] * np.exp(1j * th_pp[i])
        rpp = float(np.sum(np.abs(y_a - (H_eff_td2 @ P_a) @ (Ah_a @ xhc_pp)) ** 2))
        s2_pp = float(np.clip(rpp / N, 1e-5 if refine_ch_in_loop else max(sig2_hat * 0.4, 1e-6), 0.05))
        if rpp < best_rpp: best_rpp = rpp; best_xh_pp = xhc_pp
    out["Steelman_PerPath_PLL2"] = ser(best_xh_pp, x_a, data_mask)

    # --- Arm 5: Steelman_LagEKF_RTS (`Steelman_A`: 18-state exact Markov lag-line EKF + RTS smoother + 6-outer OAMP) ---
    pr_ekf, pt_ekf = ekf_rts_lag_subband_init(z_sub, m_bins, h_h, nu_h, l_h, max(sig2_hat, 1e-4), L_cpp, sig_r_prior, sig_t_prior, n_passes=2)
    hc_ek, nuc_ek = h_h.copy(), nu_h.copy()
    if refine_ch_in_loop:
        hc_ek, nuc_ek = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, pr_ekf, pt_ekf, l_h, nu_h, L_cpp)
        z_sub2, _ = extract_subband_traces(Y_a, l_h, sys_cfg)
        pr_ekf, pt_ekf = ekf_rts_lag_subband_init(z_sub2, m_bins, hc_ek, nuc_ek, l_h, max(sig2_hat, 1e-4), L_cpp, sig_r_prior, sig_t_prior, n_passes=2)
    s2_ek = sig2_hat; best_rek = np.inf; best_xh_ek = None
    for out_i in range(6):
        Hl_ek = m3.build_H_ext(N, L_cpp, hc_ek, l_h, nuc_ek)
        Hc_ek = np.exp(1j * pr_ekf)[:, None] * ((Hl_ek * np.exp(1j * pt_ekf)[None, :]) @ P_a)
        xs_ek, xhc_ek, vx_ek, _ = m3.oamp_exact(y_a, Hc_ek, Ah_a, max(s2_ek, 1e-6) + 0.02 * (0.6 ** out_i), pts64, data_mask, x_p, 8)
        s_ext_ek = P_a @ (Ah_a @ xs_ek)
        pr_ekf, pt_ekf = ekf_rts_lag_timedomain(y_a, Hl_ek, s_ext_ek, pr_ekf, pt_ekf, max(s2_ek, 1e-6) + 0.5 * vx_ek,
                                                sig_r_prior, sig_t_prior, L_cpp, l_h, n_sweeps=2)
        if refine_ch_in_loop and out_i >= 1:
            hc_ek, nuc_ek = m3.refine_channel_blind(y_a, s_ext_ek, pr_ekf, pt_ekf, l_h, nuc_ek, L_cpp)
        Hl_ek2 = m3.build_H_ext(N, L_cpp, hc_ek, l_h, nuc_ek)
        rek = float(np.sum(np.abs(y_a - np.exp(1j * pr_ekf) * (Hl_ek2 @ (np.exp(1j * pt_ekf) * (P_a @ (Ah_a @ xhc_ek))))) ** 2))
        s2_ek = float(np.clip(rek / N, 1e-5 if refine_ch_in_loop else max(sig2_hat * 0.4, 1e-6), 0.05))
        if rek < best_rek: best_rek = rek; best_xh_ek = xhc_ek
    out["Steelman_LagEKF_RTS"] = ser(best_xh_ek, x_a, data_mask)

    # --- Arm 6: Steelman_SC_PilEKF (`Steelman_S`: Equal-overhead 154/512 Hybrid UW + Distributed TD-PTRS SC + IEKS + OAMP) ---
    pil_ext = np.zeros(B, dtype=bool)
    pil_ext[:L_cpp] = sc_pil_mask[N - L_cpp:]
    pil_ext[L_cpp:] = sc_pil_mask
    clean_uw_rows = np.array([all(pil_ext[L_cpp + n - l] for l in range(L_cpp + 1)) for n in range(N)], dtype=bool)
    uw_idx = np.where(clean_uw_rows)[0]  # [16..47] = 32 ZERO-DATA-INTERFERENCE UW samples!

    if mode == "single_frame":
        Phi_all_uw = np.column_stack([sp_sc[L_cpp + uw_idx - l] for l in range(L_cpp + 1)])
        res_omp = y_sc[uw_idx].copy()
        supp_omp = []
        for _ in range(5):
            corrs = np.abs(Phi_all_uw.conj().T @ res_omp)
            for s_old in supp_omp:
                corrs[s_old] = -1.0
            best_l = int(np.argmax(corrs))
            supp_try = sorted(supp_omp + [best_l])
            h_try, _, _, _ = np.linalg.lstsq(Phi_all_uw[:, supp_try], y_sc[uw_idx], rcond=None)
            res_new = y_sc[uw_idx] - Phi_all_uw[:, supp_try] @ h_try
            if len(supp_omp) >= 1 and float(np.sum(np.abs(res_omp) ** 2) - np.sum(np.abs(res_new) ** 2)) < 0.08 * float(np.sum(np.abs(res_omp) ** 2)) and float(np.mean(np.abs(res_omp) ** 2)) < 0.05:
                break
            supp_omp = supp_try
            res_omp = res_new
            if float(np.mean(np.abs(res_omp) ** 2)) < 2e-3:
                break
        l_sc = np.array(sorted(supp_omp), dtype=int)
        Phi_uw = Phi_all_uw[:, l_sc]
        h_sc, _, _, _ = np.linalg.lstsq(Phi_uw, y_sc[uw_idx], rcond=None)
        nu_sc = np.zeros(len(l_sc), dtype=float)
        s2_sc = max(float(np.mean(np.abs(y_sc[uw_idx] - Phi_uw @ h_sc) ** 2)), 1e-4)
    else:
        coh_pow = np.zeros(L_cpp + 1)
        for l in range(L_cpp + 1):
            prod = y_tr_sc * np.conj(sp_tr_sc[L_cpp + n_arr - l])
            for b0 in range(0, N, 32):
                coh_pow[l] += abs(np.sum(prod[b0:b0 + 32])) ** 2 / 32.0
        med_tr = float(np.median(np.sort(coh_pow)[:(L_cpp + 1) // 2]))
        thr_tr = max(3.5 * med_tr, 0.05 * float(coh_pow.max()))
        cl_sc = [l for l in range(L_cpp + 1) if coh_pow[l] > thr_tr]
        if not cl_sc: cl_sc = [int(np.argmax(coh_pow))]
        l_sc = np.array(sorted(cl_sc), dtype=int)
        nu_sc = np.zeros(len(l_sc), dtype=float)
        if mode == "prior_clean":
            for idx_p, l in enumerate(l_sc):
                prod = y_tr_sc * np.conj(sp_tr_sc[L_cpp + n_arr - int(l)])
                grid_nu = np.linspace(-0.48, 0.48, 49)
                vals = [abs(np.sum(prod * np.exp(1j * 2 * np.pi * v * n_arr / N))) for v in grid_nu]
                nu_sc[idx_p] = float(grid_nu[int(np.argmax(vals))])
            h_sc, nu_sc = m3.refine_channel_blind(y_tr_sc, sp_tr_sc, np.zeros(N), np.zeros(B), l_sc, nu_sc, L_cpp)
            h_sc, nu_sc = m3.refine_channel_blind(y_tr_sc, sp_tr_sc, np.zeros(N), np.zeros(B), l_sc, nu_sc, L_cpp)
            s2_sc = max(float(np.mean(np.abs(y_tr_sc - m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc) @ sp_tr_sc) ** 2)), 1e-6)
        else:
            h_sc = np.array([np.mean((y_tr_sc * np.conj(sp_tr_sc[L_cpp + n_arr - int(l)]))[N // 2 - 16 : N // 2 + 16]) for l in l_sc])
            pr_tr_s = np.zeros(N); pt_tr_s = np.zeros(B)
            for _ in range(4):
                Hl_tr = m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc)
                pr_tr_s, pt_tr_s = ekf_rts_lag_timedomain(y_tr_sc, Hl_tr, sp_tr_sc, pr_tr_s, pt_tr_s, 1e-3, sig_r_prior, sig_t_prior, L_cpp, l_sc, 3)
                h_sc, nu_sc = m3.refine_channel_blind(y_tr_sc, sp_tr_sc, pr_tr_s, pt_tr_s, l_sc, nu_sc, L_cpp)
            s2_sc = max(float(np.mean(np.abs(y_tr_sc - np.exp(1j * pr_tr_s) * (m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc) @ (np.exp(1j * pt_tr_s) * sp_tr_sc))) ** 2)), 1e-5)

    Hl_sc0 = m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc)
    u_uw = (Hl_sc0 @ sp_sc)[uw_idx]
    ph_uw0 = float(np.angle(np.vdot(u_uw, y_sc[uw_idx]))) if mode != "single_frame" else 0.0
    pr_sc = np.full(N, ph_uw0, dtype=float)
    pt_sc = np.zeros(B, dtype=float)
    r_var_vec = np.empty(N, dtype=float)
    for n_i in range(N):
        un_pow = 0.0; kn_pow = 0.0
        for p_i, l in enumerate(l_sc):
            p2 = abs(h_sc[p_i]) ** 2
            if pil_ext[L_cpp + n_i - int(l)]:
                kn_pow += p2
            else:
                un_pow += p2
        r_var_vec[n_i] = 0.5 * (s2_sc + un_pow) if kn_pow > 0.05 else 1e6
    for _ in range(4):
        xi_nom = np.column_stack([pr_sc] + [pt_sc[L_cpp - l : L_cpp - l + N] for l in range(L_cpp + 1)])
        D_s = L_cpp + 2
        F_s = np.zeros((D_s, D_s)); F_s[0, 0] = 1.0; F_s[1, 1] = 1.0
        for l in range(1, L_cpp + 1): F_s[1 + l, l] = 1.0
        Q_s = np.zeros((D_s, D_s)); Q_s[0, 0] = sig_r_prior; Q_s[1, 1] = sig_t_prior
        xf = np.empty((N, D_s)); Pf = np.empty((N, D_s, D_s)); xpr = np.empty((N, D_s)); Ppr = np.empty((N, D_s, D_s))
        for n_i in range(N):
            if n_i == 0:
                xp_i = xi_nom[0].copy(); Pp_i = 10.0 * np.eye(D_s); Pp_i[1, 1] = 1e-3
            else:
                xp_i = F_s @ xf[n_i - 1]; Pp_i = F_s @ Pf[n_i - 1] @ F_s.T + Q_s
            xpr[n_i] = xp_i; Ppr[n_i] = Pp_i
            if r_var_vec[n_i] > 1e4:
                xf[n_i] = xp_i; Pf[n_i] = Pp_i; continue
            xl = xi_nom[n_i]; hr = np.zeros(D_s); hi = np.zeros(D_s); yh = 0.0 + 0.0j
            for p_i, l in enumerate(l_sc):
                if not pil_ext[L_cpp + n_i - int(l)]:
                    continue
                it = 1 + int(l)
                tm = Hl_sc0[n_i, L_cpp + n_i - int(l)] * sp_sc[L_cpp + n_i - int(l)] * np.exp(1j * (xl[0] + xl[it]))
                yh += tm; dt = 1j * tm; hr[0] += dt.real; hr[it] += dt.real; hi[0] += dt.imag; hi[it] += dt.imag
            Hn = np.vstack([hr, hi])
            inn = np.array([(y_sc[n_i] - yh).real, (y_sc[n_i] - yh).imag]) + Hn @ (xl - xp_i)
            HP = Hn @ Pp_i; S_i = r_var_vec[n_i] * np.eye(2) + HP @ Hn.T; K_i = np.linalg.solve(S_i, HP).T
            xf[n_i] = xp_i + K_i @ inn; Pf[n_i] = 0.5 * ((Pp_i - K_i @ HP) + (Pp_i - K_i @ HP).T)
        xsm = np.empty_like(xf); xsm[-1] = xf[-1]
        for n_i in range(N - 2, -1, -1):
            Cn = np.linalg.solve(Ppr[n_i + 1] + 1e-9 * np.eye(D_s), F_s @ Pf[n_i]).T
            xsm[n_i] = xf[n_i] + Cn @ (xsm[n_i + 1] - xpr[n_i + 1])
        pr_sc = pr_sc + np.clip(xsm[:, 0] - pr_sc, -0.45, 0.45)
        pt_t = np.zeros(B); pt_t[L_cpp:] = xsm[:, 1]
        for l in range(1, L_cpp + 1): pt_t[L_cpp - l] = xsm[0, 1 + l]
        pt_sc = pt_sc + np.clip(pt_t - pt_sc, -0.45, 0.45)
        sg = pt_sc[L_cpp]; pt_sc -= sg; pr_sc += sg

    best_rsc = np.inf; best_xh_sc = None
    hc_sc, nuc_sc = h_sc.copy(), nu_sc.copy()
    s2_c_sc = s2_sc
    for out_i in range(6):
        Hl_sc = m3.build_H_ext(N, L_cpp, hc_sc, l_sc, nuc_sc)
        Hc_sc = np.exp(1j * pr_sc)[:, None] * ((Hl_sc * np.exp(1j * pt_sc)[None, :]) @ P_sc)
        xs_sc, xhc_sc, vx_sc, _ = m3.oamp_exact(y_sc, Hc_sc, I_N, max(s2_c_sc, 1e-6) + 0.02 * (0.6 ** out_i), pts64, sc_data_mask, xp_sc, 8)
        s_ext_sc_hat = P_sc @ xs_sc
        pr_sc, pt_sc = ekf_rts_lag_timedomain(y_sc, Hl_sc, s_ext_sc_hat, pr_sc, pt_sc, max(s2_c_sc, 1e-6) + 0.5 * vx_sc,
                                              sig_r_prior, sig_t_prior, L_cpp, l_sc, n_sweeps=2)
        if refine_ch_in_loop and out_i >= 1:
            hc_sc, nuc_sc = m3.refine_channel_blind(y_sc, s_ext_sc_hat, pr_sc, pt_sc, l_sc, nuc_sc, L_cpp)
        Hl_sc2 = m3.build_H_ext(N, L_cpp, hc_sc, l_sc, nuc_sc)
        rsc = float(np.sum(np.abs(y_sc - np.exp(1j * pr_sc) * (Hl_sc2 @ (np.exp(1j * pt_sc) * (P_sc @ xhc_sc)))) ** 2))
        s2_c_sc = float(np.clip(rsc / N, 1e-5 if refine_ch_in_loop else max(s2_sc * 0.4, 1e-6), 0.05))
        if rsc < best_rsc: best_rsc = rsc; best_xh_sc = xhc_sc
    out["Steelman_SC_PilEKF"] = ser(best_xh_sc, x_sc, sc_data_mask)

    # --- Arm 7: Oracles ---
    V_d_o = P_a @ Ah_a[:, data_mask]
    path_o = np.stack([H_lin_t[n_arr, L_cpp + n_arr - int(l), None] * V_d_o[L_cpp + n_arr - int(l), :] for l in ls_t], axis=1)
    Wn_o = np.einsum("npk,nqk->npq", path_o, np.conj(path_o))
    v_n_o = np.sum(Wn_o, axis=2)
    local_w = v_n_o.real / v_n_o.real.sum(axis=1, keepdims=True)
    D_o = -0.5 * sig_t * np.abs(ls_t[:, None] - ls_t[None, :])
    Dv_loc = local_w @ D_o
    C_loc = D_o[None, :, :] - Dv_loc[:, :, None] - Dv_loc[:, None, :] + np.sum(Dv_loc * local_w, axis=1)[:, None, None]
    sig2_irred_rx = float(np.sum(Wn_o.real * C_loc, axis=(1, 2)).mean())
    z_pt = np.stack([np.exp(1j * phi_t[L_cpp - int(l) : L_cpp - int(l) + N]) for l in ls_t], axis=1)
    phi_ind = phi_r + np.angle(np.sum(v_n_o * z_pt, axis=1))
    _, xhlo, _, _ = m3.oamp_exact(y_a * np.exp(-1j * phi_ind), H_lin_t @ P_a, Ah_a, sig2_true + sig2_irred_rx, pts64, data_mask, x_p, 10)
    out["Oracle_SingleEnd_Lump"] = ser(xhlo, x_a, data_mask)

    Ho_a = np.exp(1j * phi_r)[:, None] * ((H_lin_t * np.exp(1j * phi_t)[None, :]) @ P_a)
    _, xhdo, _, _ = m3.oamp_exact(y_a, Ho_a, Ah_a, sig2_true, pts64, data_mask, x_p, 10)
    out["Oracle_AFDM_Dual"] = ser(xhdo, x_a, data_mask)

    Ho_sc = np.exp(1j * phi_r)[:, None] * ((H_lin_t * np.exp(1j * phi_t)[None, :]) @ P_sc)
    _, xhdo_sc, _, _ = m3.oamp_exact(y_sc, Ho_sc, I_N, sig2_true, pts64, sc_data_mask, xp_sc, 10)
    out["Oracle_SC_Dual"] = ser(xhdo_sc, x_sc, sc_data_mask)
    return out


def summarize_slice(rows):
    arms = ["Pub_Xu_LumpPCA", "Ours_EP_Dual_Sym6", "Steelman_CM_PLL2", "Steelman_PerPath_PLL2",
            "Steelman_LagEKF_RTS", "Steelman_SC_PilEKF", "Oracle_SingleEnd_Lump", "Oracle_AFDM_Dual", "Oracle_SC_Dual"]
    n = len(rows)
    t_crit = float(student_t.ppf(0.975, df=max(n - 1, 1))) if n > 1 else 0.0
    means = {}
    ll = {}
    ci_hw = {}
    for a in arms:
        arr = np.array([r[a] for r in rows], dtype=float)
        means[a] = float(np.mean(arr))
        ll[a] = float(np.mean(arr > 0.05))
        ci_hw[a] = float(t_crit * np.std(arr, ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    exact3 = sum(1 for r in rows if set(r["det_delays"]) == {0, int(r["mid_delay"]), 16}) / float(max(n, 1))
    return {"n_frames": n, "exact_all3_rate": exact3, "mean_ser": means, "ser_ci95_hw": ci_hw, "lock_loss_gt5pct": ll}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", type=str, default=os.path.join(REPO_ROOT, "ideas", "r15", "out_m03.json"))
    args = ap.parse_args()

    t0 = time.perf_counter()
    seed_base = 202611269000 if args.smoke else 202611261500
    n_per_k = 1 if args.smoke else 16  # Sep: 5*16=80 frames; Adj: 2*20=40 frames

    base_cfg = dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, sig_r=1.5e-3, sig_t=1.5e-3)
    sep_ks = [3, 5, 9, 11, 13]
    adj_ks = [1, 15]

    slices = [
        ("Sep_R3_45dB_Floor",   sep_ks, dict(**base_cfg, snr_db=45.0, mode="prior_clean"),  1 if args.smoke else 12),
        ("Sep_R4_30dB_SFBlind", sep_ks, dict(**base_cfg, snr_db=30.0, mode="single_frame"), n_per_k),
        ("Sep_R5_30dB_PNTrain", sep_ks, dict(**base_cfg, snr_db=30.0, mode="prior_pn"),     n_per_k),
        ("Adj_R2_30dB_CleanTr", adj_ks, dict(**base_cfg, snr_db=30.0, mode="prior_clean"),  1 if args.smoke else 15),
        ("Adj_R4_30dB_SFBlind", adj_ks, dict(**base_cfg, snr_db=30.0, mode="single_frame"), 1 if args.smoke else 20),
        ("Adj_R5_30dB_PNTrain", adj_ks, dict(**base_cfg, snr_db=30.0, mode="prior_pn"),     1 if args.smoke else 20),
    ]

    results = {
        "card": "I-20261125-m03",
        "frozen_m03_md5_verified": _actual_md5,
        "seed_base": seed_base,
        "smoke": bool(args.smoke),
        "workers": int(args.workers),
        "slices": {},
    }

    pool = Pool(args.workers) if args.workers > 1 else None
    try:
        for s_idx, (sname, ks, scfg, nk) in enumerate(slices):
            ts = time.perf_counter()
            tasks = []
            for ki, kv in enumerate(ks):
                c_k = dict(scfg, mid_delay=kv)
                for f in range(nk):
                    tasks.append((seed_base + s_idx * 10000 + ki * 1000 + f, c_k))
            rows = pool.map(run_teardown_frame, tasks) if pool else [run_teardown_frame(t) for t in tasks]
            summ = summarize_slice(rows)
            summ["elapsed_s"] = round(time.perf_counter() - ts, 2)
            results["slices"][sname] = summ
            m = summ["mean_ser"]; ll = summ["lock_loss_gt5pct"]
            print(f"[{sname}] (n={summ['n_frames']}, exact3={summ['exact_all3_rate']*100:.0f}%, {summ['elapsed_s']}s):\n"
                  f"  Pub_Xu     = {m['Pub_Xu_LumpPCA']:.4e} (LL {ll['Pub_Xu_LumpPCA']*100:.0f}%)\n"
                  f"  Ours_m03   = {m['Ours_EP_Dual_Sym6']:.4e} (LL {ll['Ours_EP_Dual_Sym6']*100:.0f}%)\n"
                  f"  SM_CM_PLL2 = {m['Steelman_CM_PLL2']:.4e} (LL {ll['Steelman_CM_PLL2']*100:.0f}%)\n"
                  f"  SM_PP_PLL2 = {m['Steelman_PerPath_PLL2']:.4e} (LL {ll['Steelman_PerPath_PLL2']*100:.0f}%)\n"
                  f"  SM_LagEKF  = {m['Steelman_LagEKF_RTS']:.4e} (LL {ll['Steelman_LagEKF_RTS']*100:.0f}%)\n"
                  f"  SM_SC_EKF  = {m['Steelman_SC_PilEKF']:.4e} (LL {ll['Steelman_SC_PilEKF']*100:.0f}%)\n"
                  f"  Orac_1End  = {m['Oracle_SingleEnd_Lump']:.4e} | Orac_AFDM = {m['Oracle_AFDM_Dual']:.4e} | Orac_SC = {m['Oracle_SC_Dual']:.4e}",
                  flush=True)
    finally:
        if pool:
            pool.close(); pool.join()

    results["total_elapsed_s"] = round(time.perf_counter() - t0, 2)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2, allow_nan=False)
    print(f"\nSaved -> {args.out} (total {results['total_elapsed_s']}s)", flush=True)


if __name__ == "__main__":
    main()
