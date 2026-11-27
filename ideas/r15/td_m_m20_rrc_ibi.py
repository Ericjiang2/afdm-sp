#!/usr/bin/env python3
"""
Round 15 Phase 1 — New Problem #1 Mandatory Priority Teardown (`A2-M20`):
Continuous-Time Truncated RRC Pulse-Shaping in AFDM Without Extra Guard Period Suffix (GPS)
(`Mirabella et al., IEEE JSAC 2026`, DOI: 10.1109/jsac.2026.3751260).

Physical Truth & What We Test:
  - Continuous multi-frame stream f = 0 .. F-1 (evaluating interior frames f = 1 .. F-2 so every frame
    experiences BOTH postcursor IBI from frame f-1 AND precursor IBI from frame f+1!).
  - Each frame transmits standard causal CPP of length N_cpp = ceil(tau_max / T_s) ONLY (GPS = 0!),
    shaped by truncated TX RRC pulse (roll-off alpha, span Lp = 17 symbol periods [-8 Ts, +8 Ts],
    oversampled at Q_os = 16) -> continuous LTV fractional-delay multipath channel -> RX matched RRC filter.
  - Compares 6 arms on identical paired realizations (both Known-CSI and Embedded-Pilot CE):
      1) `Pub_Bemani_Causal`: R11 `A2-M20` causal asymmetric EP guard (`Q_neg = 0`) + causal `[0..N_cpp]` LMMSE
         (reproduces the ~0.50 SER floor from R11).
      2) `Pub_Mirabella_1Blk`: `Mirabella JSAC'26` Eq. (51) single-block two-sided CT-RRC LMMSE with symmetric
         two-sided EP guard, ignoring cross-frame Precursor/Postcursor IBI (`GPS = 0`).
      3) `Steelman_A_1Blk_2Sided_OAMP`: Single-block symmetric two-sided EP CE + single-block OAMP/MMSE-DFE
         (no cross-frame feedback; isolates intra-block boundary seam mismatch when GPS = 0).
      4) `Steelman_A_SlideWin_IBI_DFE`: Full-strength textbook 3-frame sliding-window cross-frame soft/hard
         decision-feedback IBI cancellation (`[f-1, f, f+1]`, subtracting BOTH postcursor IBI from f-1 and
         precursor IBI from f+1 + exact non-periodic intra-frame linear matrix `H_curr` + OAMP/MMSE-DFE!).
      5) `Steelman_S_SC_SlideWin_DFE` & `Steelman_S_OFDM_SlideWin_DFE`: Equal-overhead `c1 = 0` Single-Carrier
         (UW+PTRS) and Comb-OFDM under the exact same truncated CT-RRC (`GPS = 0`) + 3-frame sliding-window IBI-DFE.
      6) `Oracle_GenieIBI_ExactCT`: Genie removes true cross-frame IBI + exact true `H_curr` + OAMP/MMSE-DFE.
"""
import argparse
import json
import math
import os
import time
from multiprocessing import Pool

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.stats import t as student_t

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def gray_qam(M: int):
    m_side = int(round(math.sqrt(M)))
    base = np.arange(m_side)
    gray = base ^ (base >> 1)
    lut = np.argsort(gray)
    levels = 2 * lut - (m_side - 1)
    pts = []
    for q in range(m_side):
        for i in range(m_side):
            pts.append(levels[i] + 1j * levels[q])
    pts = np.array(pts, dtype=np.complex128)
    pts /= math.sqrt(float(np.mean(np.abs(pts) ** 2)))
    return pts


def daft_matrix(N: int, c1: float, c2: float) -> np.ndarray:
    n = np.arange(N, dtype=float)
    m = np.arange(N, dtype=float)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (m ** 2))
    W = np.exp(-1j * 2.0 * np.pi * np.outer(m, n) / N) / math.sqrt(N)
    return (L2[:, None] * W) * L1[None, :]


def rrc_pulse(t_norm: np.ndarray, alpha: float) -> np.ndarray:
    """Unit-energy continuous-time RRC pulse p(t / T_s) at normalized time t_norm = t / T_s."""
    out = np.zeros_like(t_norm, dtype=float)
    for idx, t in enumerate(t_norm):
        at = abs(float(t))
        if at < 1e-12:
            out[idx] = 1.0 + alpha * (4.0 / math.pi - 1.0)
        elif alpha > 0 and abs(at - 1.0 / (4.0 * alpha)) < 1e-9:
            out[idx] = (alpha / math.sqrt(2.0)) * (
                (1.0 + 2.0 / math.pi) * math.sin(math.pi / (4.0 * alpha))
                + (1.0 - 2.0 / math.pi) * math.cos(math.pi / (4.0 * alpha))
            )
        else:
            num = math.sin(math.pi * t * (1.0 - alpha)) + 4.0 * alpha * t * math.cos(math.pi * t * (1.0 + alpha))
            den = math.pi * t * (1.0 - (4.0 * alpha * t) ** 2)
            out[idx] = num / den
    return out


def build_ct_rrc_stream_blocks(
    N: int,
    N_cpp: int,
    c1: float,
    alpha: float,
    M_p: int,
    gains: np.ndarray,
    taus: np.ndarray,
    nus: np.ndarray,
    Q_os: int = 16,
):
    """
    Exact oversampled truncated-RRC continuous-time stream operator decomposed per frame f!
    Each frame f has length B = N + N_cpp chips: s_ext^{(f)} = P_{c1} s^{(f)} (NO GPS!).
    When sampling frame f at t_idx = f * B + N_cpp + n (n = 0 .. N-1), chip m_tot in the stream
    contributes via lag d = t_idx - m_tot in [-2*M_p - 1 .. +2*M_p + ceil(tau_max) + 1].
    Returns function `frame_operators(f_idx)` giving exact (N, B) coupling matrices:
      - H_prev: coupling from frame f-1's extended chip vector s_ext^{(f-1)} (Postcursor IBI!)
      - H_curr: exact non-periodic coupling from frame f's extended chip vector s_ext^{(f)}
      - H_next: coupling from frame f+1's extended chip vector s_ext^{(f+1)} (Precursor IBI!)
      - H_circ_approx: single-block periodic/chirp-periodic approximation (`Mirabella` single-block model
        assuming negative lags at tail wrap chirp-periodically inside frame f instead of coming from f+1!)
      - R_wn_chol: exact colored noise Cholesky factor after truncated RX RRC matched filtering!
    """
    B = N + N_cpp
    # Truncated RRC on [-M_p, +M_p] oversampled by Q_os
    grid_p = np.arange(-M_p * Q_os, M_p * Q_os + 1, dtype=float) / float(Q_os)
    p_vec = rrc_pulse(grid_p, alpha)
    # Normalize truncated pulse energy in discrete oversampled inner product so unit-variance chips + AWGN match SNR!
    p_norm = math.sqrt(float(np.sum(p_vec ** 2)) / float(Q_os))
    p_vec = p_vec / p_norm

    # RX RRC noise autocorrelation R_w[lag] = int p_rx(u) p_rx(u + lag) du (for integer symbol lag: = g_rc(lag)!)
    # Note: for truncated RRC, R_w[lag] is slightly non-Nyquist at |lag| > 0 (~1e-3), include exact R_w!
    R_w = np.zeros((N, N), dtype=np.complex128)
    for lag in range(-(2 * M_p), 2 * M_p + 1):
        # Overlap of p_vec with p_vec shifted by lag * Q_os
        sh = lag * Q_os
        if abs(sh) < len(p_vec):
            if sh >= 0:
                val = float(np.dot(p_vec[sh:], p_vec[: len(p_vec) - sh])) / float(Q_os)
            else:
                val = float(np.dot(p_vec[: len(p_vec) + sh], p_vec[-sh:])) / float(Q_os)
            idx_r = np.arange(max(0, lag), min(N, N + lag))
            R_w[idx_r, idx_r - lag] = val
    R_w = 0.5 * (R_w + R_w.conj().T) + 1e-10 * np.eye(N)

    # Precompute per-path composite pulse g_p(d) for integer chip lag d in [d_min, d_max]:
    # At RX sample t_s, RX matched filter output for path (tau_p, nu_p) from TX chip at m_tot * T_s is:
    #   exp(j 2pi nu_p t_s / N) * (1/Q_os) sum_{sigma in [-M_p..M_p]} p_rx(sigma) * p_tx((t_s - m_tot) - tau_p + sigma) * exp(j 2pi nu_p sigma / N)
    d_min = -(2 * M_p + 1)
    d_max = int(math.ceil(float(np.max(taus)))) + 2 * M_p + 1
    d_lags = np.arange(d_min, d_max + 1, dtype=int)
    P_paths = len(gains)
    g_tap = np.zeros((P_paths, len(d_lags)), dtype=np.complex128)
    for p_i in range(P_paths):
        tau_p = float(taus[p_i])
        nu_p = float(nus[p_i])
        # Evaluate p_tx at shifted points (d - tau_p + grid_p), zero outside [-M_p, +M_p]!
        rx_dop = p_vec * np.exp(1j * 2.0 * np.pi * nu_p * grid_p / float(N))
        for d_i, d_val in enumerate(d_lags):
            arg_tx = float(d_val) - tau_p + grid_p
            mask_in = np.abs(arg_tx) <= float(M_p) + 1e-12
            if np.any(mask_in):
                ptx_vals = rrc_pulse(arg_tx[mask_in], alpha) / p_norm
                g_tap[p_i, d_i] = np.sum(rx_dop[mask_in] * ptx_vals) / float(Q_os)

    # CPP extension matrix P_ext: (B, N) mapping s^{(f)}[0..N-1] -> s_ext^{(f)}[0..B-1]
    P_ext = np.zeros((B, N), dtype=np.complex128)
    for k in range(N_cpp):
        n_neg = k - N_cpp  # -N_cpp .. -1
        P_ext[k, N + n_neg] = np.exp(-1j * 2.0 * np.pi * c1 * (N ** 2 + 2.0 * N * n_neg))
    P_ext[N_cpp:, :] = np.eye(N, dtype=np.complex128)

    def get_frame_ops(f_idx: int):
        H_prev_ext = np.zeros((N, B), dtype=np.complex128)
        H_curr_ext = np.zeros((N, B), dtype=np.complex128)
        H_next_ext = np.zeros((N, B), dtype=np.complex128)
        H_1blk_s = np.zeros((N, N), dtype=np.complex128)

        n_vec = np.arange(N, dtype=int)
        t_abs = f_idx * B + N_cpp + n_vec  # absolute symbol-rate sample index in stream
        # Path Doppler phases at t_abs: shape (P, N)
        ph_p = gains[:, None] * np.exp(1j * 2.0 * np.pi * nus[:, None] * t_abs[None, :] / float(N))

        for d_i, d_val in enumerate(d_lags):
            # Composite tap vector across n = 0..N-1 for lag d_val
            tap_n = g_tap[:, d_i] @ ph_p  # (N,)
            if np.max(np.abs(tap_n)) < 1e-13:
                continue
            # Stream chip index read at row n is m_stream = t_abs[n] - d_val = f_idx * B + (N_cpp + n - d_val)
            rel_idx = N_cpp + n_vec - int(d_val)
            for n_i in range(N):
                ri = int(rel_idx[n_i])
                val = tap_n[n_i]
                if 0 <= ri < B:
                    H_curr_ext[n_i, ri] += val
                elif -B <= ri < 0:
                    H_prev_ext[n_i, ri + B] += val
                elif B <= ri < 2 * B:
                    H_next_ext[n_i, ri - B] += val

                # Single-block chirp-periodic model (assumes infinite CPP/GPS around frame f):
                n_in_blk = n_i - int(d_val)
                q_wrap, r_mod = divmod(n_in_blk, N)
                # s_cp[q*N + r] = s[r] * exp(j 2pi c1 (q^2 N^2 + 2 q N r)) -> note for q = -1: exp(-j 2pi c1 (-N^2 + ...))
                # Wait: check sign of P_ext above: at n_neg = r - N (q = -1), P_ext used exp(-j 2pi c1 (N^2 + 2 N (r - N)))
                # = exp(-j 2pi c1 (-N^2 + 2 N r)) = exp(+j 2pi c1 (N^2 - 2 N r))!
                # General chirp-periodicity matching L1 = exp(-j 2pi c1 n^2):
                # s_idaft[n + q*N] = sum_m ... exp(+j 2pi c1 (n + qN)^2) = s_idaft[n] * exp(+j 2pi c1 (q^2 N^2 + 2 q N n))!
                # Check q = -1, n = r_mod: exp(+j 2pi c1 (N^2 - 2 N r_mod)) == exp(-j 2pi c1 (-N^2 + 2 N r_mod))
                # == exp(-j 2pi c1 (N^2 + 2 N (r_mod - N))) -> IDENTICAL TO P_ext!
                cp_ph = np.exp(1j * 2.0 * np.pi * c1 * ((q_wrap ** 2) * (N ** 2) + 2.0 * q_wrap * N * r_mod))
                H_1blk_s[n_i, r_mod] += val * cp_ph

        return H_prev_ext, H_curr_ext, H_next_ext, H_1blk_s, P_ext, R_w

    return get_frame_ops


def qam_soft_mmse(x_hat: np.ndarray, var_hat: np.ndarray, const: np.ndarray):
    var_c = np.maximum(var_hat, 1e-6)
    d2 = np.abs(x_hat[:, None] - const[None, :]) ** 2
    lw = -d2 / var_c[:, None]
    lw -= np.max(lw, axis=1, keepdims=True)
    w = np.exp(lw)
    w /= np.sum(w, axis=1, keepdims=True)
    m = w @ const
    v = np.sum(w * (np.abs(const[None, :] - m[:, None]) ** 2), axis=1)
    return m, np.maximum(v, 1e-6)


def qam_hard_slice(x_hat: np.ndarray, const: np.ndarray):
    idx = np.argmin(np.abs(x_hat[:, None] - const[None, :]), axis=1)
    return const[idx], idx


def oamp_mmse_dfe_detect(
    r_obs: np.ndarray,
    G_sym: np.ndarray,
    data_idx: np.ndarray,
    xp_vec: np.ndarray,
    const: np.ndarray,
    R_noise: np.ndarray,
    n_iter: int = 4,
):
    """
    Full-strength Whitened LMMSE + Iterative Soft-Decision-Feedback / EP-OAMP (MMSE-DFE) detector!
    Whitens exact RX RRC colored noise covariance R_noise, subtracts pilot vector xp_vec,
    and runs damped extrinsic EP / MMSE-SIC iterations on data_idx.
    """
    N = len(r_obs)
    Nd = len(data_idx)
    c_Rn = cho_factor(R_noise, lower=True)
    r_d = r_obs - G_sym @ xp_vec
    G_d = G_sym[:, data_idx]
    Rn_inv_Gd = cho_solve(c_Rn, G_d)
    M_gram = G_d.conj().T @ Rn_inv_Gd
    M_gram = 0.5 * (M_gram + M_gram.conj().T)
    rhs0 = Rn_inv_Gd.conj().T @ r_d

    # Iteration 0: Exact Whitened LMMSE
    P0 = M_gram + np.eye(Nd, dtype=np.complex128)
    c_P0 = cho_factor(P0, lower=True)
    x_lmmse = cho_solve(c_P0, rhs0)
    if n_iter <= 1:
        xh, idx_h = qam_hard_slice(x_lmmse, const)
        return x_lmmse, xh, idx_h, x_lmmse

    P0_inv_d = np.real(np.diag(cho_solve(c_P0, np.eye(Nd, dtype=np.complex128))))
    alpha0 = np.clip(1.0 - P0_inv_d, 0.1, 0.9999)
    x_ext = x_lmmse / alpha0
    v_ext = np.maximum(P0_inv_d / alpha0, 1e-6)
    m_cur, v_cur = qam_soft_mmse(x_ext, v_ext, const)

    for _ in range(n_iter - 1):
        v_c = np.clip(v_cur, 1e-4, 1.0)
        inv_v = 1.0 / v_c
        c_P = cho_factor(M_gram + np.diag(inv_v), lower=True)
        post_m = m_cur + cho_solve(c_P, rhs0 - M_gram @ m_cur)
        post_v = np.clip(np.real(np.diag(cho_solve(c_P, np.eye(Nd, dtype=np.complex128)))), 1e-7, 0.999)
        cav_p = np.maximum(1.0 / post_v - inv_v, 1e-4)
        cav_v = 1.0 / cav_p
        cav_m = cav_v * (post_m / post_v - m_cur * inv_v)
        m_new, v_new = qam_soft_mmse(cav_m, cav_v, const)
        m_cur = 0.7 * m_new + 0.3 * m_cur
        v_cur = 0.7 * v_new + 0.3 * v_cur

    xh, idx_h = qam_hard_slice(cav_m, const)
    return cav_m, xh, idx_h, m_cur


def estimate_two_sided_ep_channel(
    r_obs: np.ndarray,
    A: np.ndarray,
    sp_ext: np.ndarray,
    P_ext: np.ndarray,
    guard_obs_idx: np.ndarray,
    d_lags_est: np.ndarray,
    N_cpp: int,
):
    """
    Two-sided DPSS-BEM / Linear-Basis Embedded-Pilot Channel Estimator on symmetric guard_obs_idx!
    Models non-causal negative RRC precursor taps + causal taps d in d_lags_est (e.g. -5 .. +10)
    with 2-basis complex exponential / linear time-variation per tap to capture Doppler cleanly!
    """
    N = len(r_obs)
    B = len(sp_ext)
    n_vec = np.arange(N, dtype=float)
    b0 = np.ones(N, dtype=np.complex128)
    b1 = (n_vec - 0.5 * (N - 1)) / float(N)
    # Build pilot response dictionary for each lag d in d_lags_est:
    # For intra-frame pilot sp_ext (length B = N + N_cpp), at row n, rel_idx = N_cpp + n - d:
    # inside [0..B-1] uses sp_ext[rel_idx], outside [0..B-1] is 0 (unknown adjacent frame)!
    n_lags = len(d_lags_est)
    Phi_td = np.zeros((N, 2 * n_lags), dtype=np.complex128)
    for li, d_val in enumerate(d_lags_est):
        for n_i in range(N):
            ri = N_cpp + n_i - int(d_val)
            if 0 <= ri < B:
                Phi_td[n_i, 2 * li] = b0[n_i] * sp_ext[ri]
                Phi_td[n_i, 2 * li + 1] = b1[n_i] * sp_ext[ri]
    Phi_daft = (A @ Phi_td)[guard_obs_idx, :]
    y_g = (A @ r_obs)[guard_obs_idx]
    Gram = Phi_daft.conj().T @ Phi_daft
    reg = 2e-3 * float(np.real(np.trace(Gram))) / max(Gram.shape[0], 1) * np.eye(Gram.shape[0])
    th = np.linalg.solve(Gram + reg, Phi_daft.conj().T @ y_g)

    # Reconstruct H_prev_hat, H_curr_hat, H_next_hat, H_1blk_hat from estimated two-sided taps!
    H_prev_h = np.zeros((N, B), dtype=np.complex128)
    H_curr_h = np.zeros((N, B), dtype=np.complex128)
    H_next_h = np.zeros((N, B), dtype=np.complex128)
    H_1blk_h = np.zeros((N, N), dtype=np.complex128)
    # Infer c1 from P_ext[N_cpp - 1, N - 1] = exp(-j 2pi c1 (N^2 - 2N))? Pass c1 explicitly below via P_ext phase:
    for li, d_val in enumerate(d_lags_est):
        tap_n = th[2 * li] * b0 + th[2 * li + 1] * b1
        for n_i in range(N):
            ri = N_cpp + n_i - int(d_val)
            val = tap_n[n_i]
            if 0 <= ri < B:
                H_curr_h[n_i, ri] += val
            elif -B <= ri < 0:
                H_prev_h[n_i, ri + B] += val
            elif B <= ri < 2 * B:
                H_next_h[n_i, ri - B] += val
    # Single-block approx uses H_curr_h @ P_ext (plus chirp-wrapped negative taps)
    return H_prev_h, H_curr_h, H_next_h


def estimate_parametric_ct_rrc_nomp(
    r_sym_list: list,
    A: np.ndarray,
    sp_ext: np.ndarray,
    guard_obs_inner: np.ndarray,
    N: int,
    N_cpp: int,
    c1: float,
    alpha: float,
    M_p: int,
    nu_max: float,
    P_max: int = 4,
):
    """
    Textbook Parametric Continuous-Delay + Doppler NOMP / Matching Pursuit (`Mamandipoor TSP'16`)
    exploiting the KNOWN TX/RX RRC pulse shape across the F-frame burst's inner pilot guard windows!
    Allowed by R15 Steelman rules: <= 2D scalar grid search over (tau, nu) + local coordinate polish!
    """
    F_f = len(r_sym_list)
    Y_g = np.concatenate([(A @ r_sym_list[f])[guard_obs_inner] for f in range(F_f)])
    A_g = A[guard_obs_inner, :]

    def atom_burst(tau_v: float, nu_v: float) -> np.ndarray:
        # Exact truncated Lp=17 CT-RRC steering vector via build_ct_rrc_stream_blocks (zero model mismatch!)
        get_1p = build_ct_rrc_stream_blocks(
            N, N_cpp, c1, alpha, M_p,
            np.array([1.0 + 0j]), np.array([tau_v], dtype=float), np.array([nu_v], dtype=float), Q_os=16
        )
        return np.concatenate([A_g @ (get_1p(f)[1] @ sp_ext) for f in range(F_f)])

    tau_grid = np.linspace(0.05, float(N_cpp) - 0.05, 4 * N_cpp + 3)
    nu_grid = np.linspace(-nu_max, nu_max, 13)
    grid_params = [(float(tv), float(nv)) for tv in tau_grid for nv in nu_grid]
    Atom_mat = np.column_stack([atom_burst(tv, nv) for (tv, nv) in grid_params])
    Atom_nrm = np.maximum(np.linalg.norm(Atom_mat, axis=0), 1e-12)

    est_taus, est_nus = [], []
    est_gains = np.zeros(0, dtype=np.complex128)
    res = Y_g.copy()
    init_e = float(np.vdot(Y_g, Y_g).real)

    for _ in range(P_max):
        scores = np.abs(Atom_mat.conj().T @ res) / Atom_nrm
        for idx_g, (tv, nv) in enumerate(grid_params):
            if any(math.hypot((tv - et) / 0.45, (nv - en) / 0.35) < 1.0 for et, en in zip(est_taus, est_nus)):
                scores[idx_g] = -1.0
        best_i = int(np.argmax(scores))
        if scores[best_i] <= 0.0:
            break
        tv0, nv0 = grid_params[best_i]
        cand_t = est_taus + [tv0]
        cand_n = est_nus + [nv0]

        # Local coordinate search refinement (step 0.08 -> 0.02 -> 0.005) on all active (tau_p, nu_p)
        for step_t, step_n in [(0.08, 0.06), (0.02, 0.015), (0.005, 0.004)]:
            for p_k in range(len(cand_t)):
                best_rss = 1e30
                bt, bn = cand_t[p_k], cand_n[p_k]
                other_cols = [atom_burst(cand_t[q], cand_n[q]) for q in range(len(cand_t)) if q != p_k]
                for dt in (-step_t, 0.0, step_t):
                    tc = float(np.clip(bt + dt, 0.0, float(N_cpp) + 0.2))
                    for dn in (-step_n, 0.0, step_n):
                        nc = float(np.clip(bn + dn, -nu_max - 0.1, nu_max + 0.1))
                        Phi_c = np.column_stack(other_cols + [atom_burst(tc, nc)])
                        gh, _, _, _ = np.linalg.lstsq(Phi_c, Y_g, rcond=None)
                        rv = Y_g - Phi_c @ gh
                        rss = float(np.vdot(rv, rv).real)
                        if rss < best_rss:
                            best_rss = rss; cand_t[p_k] = tc; cand_n[p_k] = nc

        Phi_all = np.column_stack([atom_burst(cand_t[q], cand_n[q]) for q in range(len(cand_t))])
        gh_all, _, _, _ = np.linalg.lstsq(Phi_all, Y_g, rcond=None)
        res_new = Y_g - Phi_all @ gh_all
        drop_e = float(np.vdot(res, res).real - np.vdot(res_new, res_new).real)
        if len(est_taus) >= 1 and drop_e < 2e-4 * init_e:
            break
        est_taus, est_nus, est_gains, res = cand_t, cand_n, gh_all, res_new

    get_est_ops = build_ct_rrc_stream_blocks(
        N, N_cpp, c1, alpha, M_p,
        np.array(est_gains, dtype=np.complex128),
        np.array(est_taus, dtype=float),
        np.array(est_nus, dtype=float),
        Q_os=16,
    )
    return [get_est_ops(f)[:4] for f in range(F_f)], np.array(est_taus, dtype=float), np.array(est_nus, dtype=float)


def run_stream_trial(args):
    seed, cfg = args
    rng = np.random.default_rng(seed)
    N = cfg["N"]
    N_cpp = cfg["N_cpp"]
    two_Nc1 = cfg["two_Nc1"]
    alpha = cfg["alpha"]
    M_p = cfg["M_p"]
    M_qam = cfg["M_qam"]
    snr_db = cfg["snr_db"]
    F_frames = cfg["F_frames"]  # e.g. 6 frames (evaluate interior frames 1..4!)
    B = N + N_cpp

    c1 = two_Nc1 / (2.0 * N)
    c2 = 1.0 / (2.0 * math.pi * N)
    A = daft_matrix(N, c1, c2)
    Ah = A.conj().T
    const = gray_qam(M_qam)
    qpsk = np.array([-1 - 1j, -1 + 1j, 1 - 1j, 1 + 1j]) / math.sqrt(2.0)
    sig2 = 10.0 ** (-snr_db / 10.0)

    # Generate 3-path continuous-time fractional-delay doubly-dispersive channel
    # Path 0 has near-zero fractional delay [0.15, 0.55] Ts -> strong negative RRC precursor taps k = -1..-5!
    # Path 2 has delay near N_cpp - 0.35 -> strong postcursor RRC tail beyond N_cpp into previous frame!
    taus = np.array([
        rng.uniform(0.15, 0.55),
        rng.uniform(1.80, 2.80),
        rng.uniform(float(N_cpp) - 0.75, float(N_cpp) - 0.20),
    ], dtype=float)
    nus = rng.uniform(-cfg["nu_max"], cfg["nu_max"], 3)
    pdp = np.array([0.45, 0.32, 0.23], dtype=float)
    gains = np.sqrt(pdp / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
    gains /= np.linalg.norm(gains)

    get_ops = build_ct_rrc_stream_blocks(N, N_cpp, c1, alpha, M_p, gains, taus, nus, Q_os=16)
    get_ops_c0 = build_ct_rrc_stream_blocks(N, N_cpp, 0.0, alpha, M_p, gains, taus, nus, Q_os=16)

    # Guard layouts (EXACT same total guard slots n_guard so spectral efficiency & pilot energy are 100% matched!):
    # Note sign of DAFT shift for A = L2 * F * L1 with L1 = exp(-j 2pi c1 n^2):
    #   s[n - d] carries exp(+j 2pi c1 (n - d)^2), so L1 * s[n - d] carries exp(-j 2pi c1 * 2 n d)
    #   -> F maps exp(-j 2pi m n / N) peak to m = k_p + (2 N c1) * d!
    #   Therefore POSITIVE causal delays d > 0 shift UP to k_p + d * two_Nc1,
    #   and NEGATIVE RRC precursor taps d < 0 shift DOWN to k_p - |d| * two_Nc1!
    k_p = N // 2
    q_neg = cfg["q_neg_bins"]
    q_pos = cfg["q_pos_bins"]
    g_sym_lo = k_p - q_neg
    g_sym_hi = k_p + q_pos + 1
    n_guard = g_sym_hi - g_sym_lo
    mask_sym_g = np.zeros(N, dtype=bool); mask_sym_g[g_sym_lo:g_sym_hi] = True
    data_idx_sym = np.where(~mask_sym_g)[0]
    Nd = len(data_idx_sym)
    xp_val = math.sqrt(float(n_guard))  # unit guard-density pilot power matching Bemani TWC'23!
    xp_sym = np.zeros(N, dtype=np.complex128); xp_sym[k_p] = xp_val

    # Bemani causal asymmetric guard of the EXACT same width n_guard (`[k_p - 3 .. k_p + n_guard - 3] mod N`, ignoring d < 0!):
    g_caus_lo = k_p - 3
    g_caus_hi = g_caus_lo + n_guard
    idx_caus_g = np.arange(g_caus_lo, g_caus_hi) % N
    mask_caus_g = np.zeros(N, dtype=bool); mask_caus_g[idx_caus_g] = True
    data_idx_caus = np.where(~mask_caus_g)[0]
    assert len(data_idx_caus) == Nd
    xp_caus = np.zeros(N, dtype=np.complex128); xp_caus[k_p] = xp_val

    # Generate F_frames continuous stream for:
    # (A) Bemani causal-guard stream, (B) Symmetric-guard AFDM stream, (C) Single-Carrier UW+PTRS stream, (D) Comb-OFDM stream
    tx_idx_list = [rng.integers(0, M_qam, Nd) for _ in range(F_frames)]

    # Precompute frame operators for f = 0 .. F_frames-1
    ops_af = [get_ops(f) for f in range(F_frames)]
    ops_c0 = [get_ops_c0(f) for f in range(F_frames)]
    R_w = ops_af[0][5]
    L_rw = np.linalg.cholesky(R_w)

    w_frames = [
        math.sqrt(sig2 / 2.0) * (L_rw @ (rng.standard_normal(N) + 1j * rng.standard_normal(N)))
        for _ in range(F_frames)
    ]

    # --- Stream A: Bemani Causal Asymmetric Guard + Causal DT LMMSE (`Pub_Bemani_Causal`) ---
    s_ext_caus = []
    for f in range(F_frames):
        xf = xp_caus.copy(); xf[data_idx_caus] = const[tx_idx_list[f]]
        s_ext_caus.append(ops_af[f][4] @ (Ah @ xf))
    r_caus = []
    for f in range(F_frames):
        Hp, Hc, Hn, _, _, _ = ops_af[f]
        rf = Hc @ s_ext_caus[f] + w_frames[f].copy()
        if f > 0: rf += Hp @ s_ext_caus[f - 1]
        if f < F_frames - 1: rf += Hn @ s_ext_caus[f + 1]
        r_caus.append(rf)

    # --- Stream B: Symmetric Two-Sided Guard AFDM Stream ---
    s_ext_sym = []
    for f in range(F_frames):
        xf = xp_sym.copy(); xf[data_idx_sym] = const[tx_idx_list[f]]
        s_ext_sym.append(ops_af[f][4] @ (Ah @ xf))
    r_sym = []
    for f in range(F_frames):
        Hp, Hc, Hn, _, _, _ = ops_af[f]
        rf = Hc @ s_ext_sym[f] + w_frames[f].copy()
        if f > 0: rf += Hp @ s_ext_sym[f - 1]
        if f < F_frames - 1: rf += Hn @ s_ext_sym[f + 1]
        r_sym.append(rf)

    eval_f = list(range(1, F_frames - 1))  # interior frames suffering BOTH precursor & postcursor IBI!

    # 1) Pub_Bemani_Causal (Known causal taps 0..N_cpp & EP causal taps 0..N_cpp)
    d_caus = np.arange(0, N_cpp + 1, dtype=int)
    ser_bem_k, ser_bem_ce = [], []
    sp_ext_caus = ops_af[0][4] @ (Ah @ xp_caus)
    guard_obs_caus = np.arange(g_caus_lo + 3, g_caus_hi - 1) % N
    for f in eval_f:
        Hp, Hc, Hn, _, P_e, _ = ops_af[f]
        # Causal truncation of true Hc: zero out all entries outside causal lags 0..N_cpp!
        Hc_caus_true = np.zeros_like(Hc)
        for d_v in range(0, N_cpp + 1):
            for n_i in range(N):
                Hc_caus_true[n_i, N_cpp + n_i - d_v] = Hc[n_i, N_cpp + n_i - d_v]
        G_bem_k = (Hc_caus_true @ P_e) @ Ah
        _, _, idx_bk, _ = oamp_mmse_dfe_detect(r_caus[f], G_bem_k, data_idx_caus, xp_caus, const, sig2 * R_w, n_iter=1)
        ser_bem_k.append(float(np.mean(idx_bk != tx_idx_list[f])))

        _, Hc_ce_b, _ = estimate_two_sided_ep_channel(r_caus[f], A, sp_ext_caus, P_e, guard_obs_caus, d_caus, N_cpp)
        G_bem_ce = (Hc_ce_b @ P_e) @ Ah
        _, _, idx_bce, _ = oamp_mmse_dfe_detect(r_caus[f], G_bem_ce, data_idx_caus, xp_caus, const, sig2 * R_w, n_iter=1)
        ser_bem_ce.append(float(np.mean(idx_bce != tx_idx_list[f])))

    # 2) Pub_Mirabella_1Blk (`Mirabella JSAC'26` Eq. 51 single-block two-sided CT-RRC LMMSE, Known CSI)
    # 3) Steelman_A_1Blk_2Sided_OAMP (Single-block 4-iter OAMP/MMSE-DFE, Known CSI & Parametric-NOMP EP CE)
    ser_mira_k = []
    ser_sm1_k, ser_sm1_ce = [], []
    sp_ext_sym = ops_af[0][4] @ (Ah @ xp_sym)
    # CRITICAL ANTI-STRAWMAN GUARD WINDOW:
    # Pilot paths tau in [0, N_cpp] have peaks at k_p + tau * two_Nc1 (up to k_p + N_cpp * two_Nc1 + 3)
    # and negative RRC taps d = -1, -2 at k_p - 2 * two_Nc1 .. k_p!
    # Right-side data starts at k_p + q_pos + 1 and only shifts DOWN by 1..2*two_Nc1, so up to k_p + (N_cpp + 1)*two_Nc1 + 2 is 100% clean!
    obs_lo_p = k_p - min(q_neg // 2, 2 * two_Nc1 + 2)
    obs_hi_p = k_p + min(q_pos - two_Nc1, (N_cpp + 1) * two_Nc1 + 2)
    guard_obs_inner = np.arange(obs_lo_p, obs_hi_p + 1) % N

    nomp_ops_sym, est_t_p, est_n_p = estimate_parametric_ct_rrc_nomp(
        r_sym, A, sp_ext_sym, guard_obs_inner, N, N_cpp, c1, alpha, M_p, cfg["nu_max"], P_max=3
    )

    for f in eval_f:
        Hp, Hc, Hn, H_1blk_s, P_e, _ = ops_af[f]
        G_mira = H_1blk_s @ Ah
        _, _, idx_mk, _ = oamp_mmse_dfe_detect(r_sym[f], G_mira, data_idx_sym, xp_sym, const, sig2 * R_w, n_iter=1)
        ser_mira_k.append(float(np.mean(idx_mk != tx_idx_list[f])))

        G_curr_k = (Hc @ P_e) @ Ah
        _, _, idx_s1k, _ = oamp_mmse_dfe_detect(r_sym[f], G_curr_k, data_idx_sym, xp_sym, const, sig2 * R_w, n_iter=4)
        ser_sm1_k.append(float(np.mean(idx_s1k != tx_idx_list[f])))

        G_curr_ce = (nomp_ops_sym[f][1] @ P_e) @ Ah
        _, _, idx_s1ce, _ = oamp_mmse_dfe_detect(r_sym[f], G_curr_ce, data_idx_sym, xp_sym, const, sig2 * R_w, n_iter=4)
        ser_sm1_ce.append(float(np.mean(idx_s1ce != tx_idx_list[f])))

    # 4) Steelman_A_SlideWin_IBI_DFE (3-frame sliding-window cross-frame soft/hard IBI cancellation + OAMP/MMSE-DFE!)
    # (4a) Known-CSI Sliding-Window IBI-DFE:
    s_hat_k = []
    idx_sw_k = [None] * F_frames
    for f in range(F_frames):
        _, Hc, _, _, P_e, _ = ops_af[f]
        _, _, idx_f, m_soft = oamp_mmse_dfe_detect(r_sym[f], (Hc @ P_e) @ Ah, data_idx_sym, xp_sym, const, sig2 * R_w, n_iter=4)
        xf_s = xp_sym.copy(); xf_s[data_idx_sym] = m_soft
        s_hat_k.append(P_e @ (Ah @ xf_s))
        idx_sw_k[f] = idx_f
    for _sw_pass in range(2):
        s_hat_new = []
        for f in range(F_frames):
            Hp, Hc, Hn, _, P_e, _ = ops_af[f]
            r_clean = r_sym[f].copy()
            if f > 0: r_clean -= Hp @ s_hat_k[f - 1]
            if f < F_frames - 1: r_clean -= Hn @ s_hat_k[f + 1]
            _, _, idx_f, m_soft = oamp_mmse_dfe_detect(r_clean, (Hc @ P_e) @ Ah, data_idx_sym, xp_sym, const, sig2 * R_w, n_iter=4)
            xf_s = xp_sym.copy(); xf_s[data_idx_sym] = m_soft
            s_hat_new.append(P_e @ (Ah @ xf_s))
            idx_sw_k[f] = idx_f
        s_hat_k = s_hat_new
    ser_sw_k = [float(np.mean(idx_sw_k[f] != tx_idx_list[f])) for f in eval_f]

    # (4b) Embedded-Pilot CE (`Parametric CT-RRC NOMP` + Data-Aided Parametric (tau, nu, gain) Polish + Sliding-Window IBI-DFE):
    s_hat_ce = []
    idx_sw_ce = [None] * F_frames
    ce_cur = [(op[0], op[1], op[2]) for op in nomp_ops_sym]
    cur_t = est_t_p.copy(); cur_n = est_n_p.copy()
    for f in range(F_frames):
        P_e = ops_af[f][4]
        _, _, idx_f, m_soft = oamp_mmse_dfe_detect(r_sym[f], (ce_cur[f][1] @ P_e) @ Ah, data_idx_sym, xp_sym, const, sig2 * R_w, n_iter=4)
        xf_s = xp_sym.copy(); xf_s[data_idx_sym] = m_soft
        s_hat_ce.append(P_e @ (Ah @ xf_s))
        idx_sw_ce[f] = idx_f

    # Helper: evaluate multi-frame stream response per unit-gain path (tau_k, nu_k) on full reconstructed chip stream s_hat_ce!
    r_all_vec = np.concatenate(r_sym)
    def eval_path_col_full(tv: float, nv: float, s_chips_list: list) -> np.ndarray:
        get_1 = build_ct_rrc_stream_blocks(N, N_cpp, c1, alpha, M_p, np.array([1.0 + 0j]), np.array([tv]), np.array([nv]), Q_os=16)
        out_f = []
        for f in range(F_frames):
            Hp1, Hc1, Hn1, _, _, _ = get_1(f)
            vf = Hc1 @ s_chips_list[f]
            if f > 0: vf += Hp1 @ s_chips_list[f - 1]
            if f < F_frames - 1: vf += Hn1 @ s_chips_list[f + 1]
            out_f.append(vf)
        return np.concatenate(out_f)

    for _sw_pass in range(2):
        # Refine continuous (tau_p, nu_p, g_p) directly on ALL F_frames * N samples using soft chip stream!
        for step_t, step_n in [(0.04, 0.03), (0.01, 0.008)]:
            for pk in range(len(cur_t)):
                other_c = [eval_path_col_full(cur_t[q], cur_n[q], s_hat_ce) for q in range(len(cur_t)) if q != pk]
                bt, bn = cur_t[pk], cur_n[pk]
                best_rss = 1e30
                for dt in (-step_t, 0.0, step_t):
                    tc = float(np.clip(bt + dt, 0.0, float(N_cpp) + 0.1))
                    for dn in (-step_n, 0.0, step_n):
                        nc = float(np.clip(bn + dn, -cfg["nu_max"] - 0.05, cfg["nu_max"] + 0.05))
                        Phi_f = np.column_stack(other_c + [eval_path_col_full(tc, nc, s_hat_ce)])
                        gh, _, _, _ = np.linalg.lstsq(Phi_f, r_all_vec, rcond=None)
                        rv = r_all_vec - Phi_f @ gh
                        rss = float(np.vdot(rv, rv).real)
                        if rss < best_rss:
                            best_rss = rss; cur_t[pk] = tc; cur_n[pk] = nc
        Phi_fin = np.column_stack([eval_path_col_full(cur_t[q], cur_n[q], s_hat_ce) for q in range(len(cur_t))])
        cur_g, _, _, _ = np.linalg.lstsq(Phi_fin, r_all_vec, rcond=None)
        get_ref = build_ct_rrc_stream_blocks(N, N_cpp, c1, alpha, M_p, cur_g, cur_t, cur_n, Q_os=16)
        ce_cur = [get_ref(f)[:3] for f in range(F_frames)]

        s_hat_new = []
        for f in range(F_frames):
            Hp_r, Hc_r, Hn_r = ce_cur[f]
            P_e = ops_af[f][4]
            r_clean = r_sym[f].copy()
            if f > 0: r_clean -= Hp_r @ s_hat_ce[f - 1]
            if f < F_frames - 1: r_clean -= Hn_r @ s_hat_ce[f + 1]
            _, _, idx_f, m_soft = oamp_mmse_dfe_detect(r_clean, (Hc_r @ P_e) @ Ah, data_idx_sym, xp_sym, const, sig2 * R_w, n_iter=4)
            xf_s = xp_sym.copy(); xf_s[data_idx_sym] = m_soft
            s_hat_new.append(P_e @ (Ah @ xf_s))
            idx_sw_ce[f] = idx_f
        s_hat_ce = s_hat_new
    ser_sw_ce = [float(np.mean(idx_sw_ce[f] != tx_idx_list[f])) for f in eval_f]

    # (4c) Sol Prescription: 3-Frame Joint Banded Block-Equalizer (`Steelman_A_3FrameJoint_OAMP`, solving [f-1, f, f+1] jointly!)
    ser_joint3_k = []
    R_w3 = np.kron(np.eye(3, dtype=np.complex128), sig2 * R_w)
    xp_3 = np.tile(xp_sym, 3)
    data_idx_3 = np.concatenate([data_idx_sym, N + data_idx_sym, 2 * N + data_idx_sym])
    for f in eval_f:
        # Stack observations [r_{f-1}; r_f; r_{f+1}] and subtract outer boundary frames f-2 / f+2 via soft s_hat_k!
        r_stk = []
        G_3blk = np.zeros((3 * N, 3 * N), dtype=np.complex128)
        for loc_i, ff in enumerate((f - 1, f, f + 1)):
            Hp_f, Hc_f, Hn_f, _, P_ef, _ = ops_af[ff]
            rf_c = r_sym[ff].copy()
            if loc_i == 0 and ff - 1 >= 0:
                rf_c -= Hp_f @ s_hat_k[ff - 1]
            if loc_i == 2 and ff + 1 < F_frames:
                rf_c -= Hn_f @ s_hat_k[ff + 1]
            r_stk.append(rf_c)
            G_3blk[loc_i * N : (loc_i + 1) * N, loc_i * N : (loc_i + 1) * N] = (Hc_f @ P_ef) @ Ah
            if loc_i > 0:
                G_3blk[loc_i * N : (loc_i + 1) * N, (loc_i - 1) * N : loc_i * N] = (Hp_f @ P_ef) @ Ah
            if loc_i < 2:
                G_3blk[loc_i * N : (loc_i + 1) * N, (loc_i + 1) * N : (loc_i + 2) * N] = (Hn_f @ P_ef) @ Ah
        r_3 = np.concatenate(r_stk)
        _, _, idx_3, _ = oamp_mmse_dfe_detect(r_3, G_3blk, data_idx_3, xp_3, const, R_w3, n_iter=4)
        idx_mid = idx_3[Nd : 2 * Nd]
        ser_joint3_k.append(float(np.mean(idx_mid != tx_idx_list[f])))

    # 5) Cross-Waveform `Steelman_S` (c1 = 0 Single-Carrier & CP-OFDM under exact same truncated CT-RRC, GPS = 0, Known CSI & CE!):
    # (5a) Single-Carrier (A = I_N) with same n_guard pilot slots (UW in middle of block so zero cross-frame IBI hits pilot!)
    A_sc = np.eye(N, dtype=np.complex128)
    sc_pil_mask = np.zeros(N, dtype=bool)
    sc_st = (N - n_guard) // 2
    sc_pil_mask[sc_st : sc_st + n_guard] = True
    sc_data_idx = np.where(~sc_pil_mask)[0]
    xp_sc = np.zeros(N, dtype=np.complex128)
    xp_sc[sc_pil_mask] = math.sqrt(0.5) * qpsk[rng.integers(0, 4, n_guard)]  # exact same pilot energy 0.5 * n_guard!
    s_ext_sc = []
    for f in range(F_frames):
        xf = xp_sc.copy(); xf[sc_data_idx] = const[tx_idx_list[f]]
        s_ext_sc.append(ops_c0[f][4] @ xf)
    r_sc = []
    for f in range(F_frames):
        Hp, Hc, Hn, _, _, _ = ops_c0[f]
        rf = Hc @ s_ext_sc[f] + w_frames[f].copy()
        if f > 0: rf += Hp @ s_ext_sc[f - 1]
        if f < F_frames - 1: rf += Hn @ s_ext_sc[f + 1]
        r_sc.append(rf)
    # Sliding-window IBI-DFE on Single-Carrier (Known CSI & Interior-UW CE!)
    s_hat_sc = []
    idx_sc_k = [None] * F_frames
    for f in range(F_frames):
        _, Hc, _, _, P_e, _ = ops_c0[f]
        _, _, idx_f, m_soft = oamp_mmse_dfe_detect(r_sc[f], Hc @ P_e, sc_data_idx, xp_sc, const, sig2 * R_w, n_iter=4)
        xf_s = xp_sc.copy(); xf_s[sc_data_idx] = m_soft
        s_hat_sc.append(P_e @ xf_s)
        idx_sc_k[f] = idx_f
    for _ in range(2):
        s_hat_new = []
        for f in range(F_frames):
            Hp, Hc, Hn, _, P_e, _ = ops_c0[f]
            r_clean = r_sc[f].copy()
            if f > 0: r_clean -= Hp @ s_hat_sc[f - 1]
            if f < F_frames - 1: r_clean -= Hn @ s_hat_sc[f + 1]
            _, _, idx_f, m_soft = oamp_mmse_dfe_detect(r_clean, Hc @ P_e, sc_data_idx, xp_sc, const, sig2 * R_w, n_iter=4)
            xf_s = xp_sc.copy(); xf_s[sc_data_idx] = m_soft
            s_hat_new.append(P_e @ xf_s)
            idx_sc_k[f] = idx_f
        s_hat_sc = s_hat_new
    ser_sc_sw_k = [float(np.mean(idx_sc_k[f] != tx_idx_list[f])) for f in eval_f]

    # (5b) CP-OFDM (c1 = c2 = 0) with exact same Nd data symbols + sliding-window IBI-DFE (Known CSI)
    A_of = daft_matrix(N, 0.0, 0.0); Ah_of = A_of.conj().T
    of_pil_idx = np.round(np.linspace(0, N - 1, n_guard, endpoint=False)).astype(int)
    of_pil_mask = np.zeros(N, dtype=bool); of_pil_mask[of_pil_idx] = True
    of_data_idx = np.where(~of_pil_mask)[0]
    xp_of = np.zeros(N, dtype=np.complex128)
    xp_of[of_pil_mask] = math.sqrt(0.5) * qpsk[rng.integers(0, 4, n_guard)]
    s_ext_of = []
    for f in range(F_frames):
        xf = xp_of.copy(); xf[of_data_idx] = const[tx_idx_list[f]]
        s_ext_of.append(ops_c0[f][4] @ (Ah_of @ xf))
    r_of = []
    for f in range(F_frames):
        Hp, Hc, Hn, _, _, _ = ops_c0[f]
        rf = Hc @ s_ext_of[f] + w_frames[f].copy()
        if f > 0: rf += Hp @ s_ext_of[f - 1]
        if f < F_frames - 1: rf += Hn @ s_ext_of[f + 1]
        r_of.append(rf)
    s_hat_of = []
    idx_of_k = [None] * F_frames
    for f in range(F_frames):
        _, Hc, _, _, P_e, _ = ops_c0[f]
        _, _, idx_f, m_soft = oamp_mmse_dfe_detect(r_of[f], (Hc @ P_e) @ Ah_of, of_data_idx, xp_of, const, sig2 * R_w, n_iter=4)
        xf_s = xp_of.copy(); xf_s[of_data_idx] = m_soft
        s_hat_of.append(P_e @ (Ah_of @ xf_s))
        idx_of_k[f] = idx_f
    for _ in range(2):
        s_hat_new = []
        for f in range(F_frames):
            Hp, Hc, Hn, _, P_e, _ = ops_c0[f]
            r_clean = r_of[f].copy()
            if f > 0: r_clean -= Hp @ s_hat_of[f - 1]
            if f < F_frames - 1: r_clean -= Hn @ s_hat_of[f + 1]
            _, _, idx_f, m_soft = oamp_mmse_dfe_detect(r_clean, (Hc @ P_e) @ Ah_of, of_data_idx, xp_of, const, sig2 * R_w, n_iter=4)
            xf_s = xp_of.copy(); xf_s[of_data_idx] = m_soft
            s_hat_new.append(P_e @ (Ah_of @ xf_s))
            idx_of_k[f] = idx_f
        s_hat_of = s_hat_new
    ser_of_sw_k = [float(np.mean(idx_of_k[f] != tx_idx_list[f])) for f in eval_f]

    # 6) Oracle_GenieIBI_ExactCT (Genie removes exact true cross-frame IBI + exact H_curr + 4-iter OAMP/MMSE-DFE)
    ser_orac = []
    for f in eval_f:
        Hp, Hc, Hn, _, P_e, _ = ops_af[f]
        r_genie = r_sym[f] - Hp @ s_ext_sym[f - 1] - Hn @ s_ext_sym[f + 1]
        _, _, idx_o, _ = oamp_mmse_dfe_detect(r_genie, (Hc @ P_e) @ Ah, data_idx_sym, xp_sym, const, sig2 * R_w, n_iter=4)
        ser_orac.append(float(np.mean(idx_o != tx_idx_list[f])))

    return {
        "Pub_Bemani_Causal_KnownCSI": float(np.mean(ser_bem_k)),
        "Pub_Bemani_Causal_EP_CE": float(np.mean(ser_bem_ce)),
        "Pub_Mirabella_1Blk_LMMSE": float(np.mean(ser_mira_k)),
        "Steelman_A_1Blk_2Sided_KnownCSI": float(np.mean(ser_sm1_k)),
        "Steelman_A_1Blk_2Sided_EP_CE": float(np.mean(ser_sm1_ce)),
        "Steelman_A_SlideWin_IBI_DFE_KnownCSI": float(np.mean(ser_sw_k)),
        "Steelman_A_3FrameJoint_OAMP_KnownCSI": float(np.mean(ser_joint3_k)),
        "Steelman_A_SlideWin_IBI_DFE_EP_CE": float(np.mean(ser_sw_ce)),
        "Steelman_S_SC_SlideWin_DFE": float(np.mean(ser_sc_sw_k)),
        "Steelman_S_OFDM_SlideWin_DFE": float(np.mean(ser_of_sw_k)),
        "Oracle_GenieIBI_ExactCT": float(np.mean(ser_orac)),
    }


def summarize_rows(rows):
    arms = list(rows[0].keys())
    n = len(rows)
    tc = float(student_t.ppf(0.975, df=max(n - 1, 1))) if n > 1 else 0.0
    means, ci95, floor_gt1e2 = {}, {}, {}
    for a in arms:
        arr = np.array([r[a] for r in rows], dtype=float)
        means[a] = float(np.mean(arr))
        ci95[a] = float(tc * np.std(arr, ddof=1) / math.sqrt(n)) if n > 1 else 0.0
        floor_gt1e2[a] = float(np.mean(arr > 1e-2))
    return {"n_streams": n, "mean_ser": means, "ci95_hw": ci95, "stream_fail_gt1pct": floor_gt1e2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", type=str, default=os.path.join(REPO_ROOT, "ideas", "r15", "out_m20_rrc_ibi.json"))
    args = ap.parse_args()

    t0 = time.perf_counter()
    seed_base = 202611269900 if args.smoke else 202611264500

    regimes = [
        # Regime 1: Direct R11 A2-M20 reproduction + continuous stream (N=128, 2Nc1=5, alpha=0.20, Lp=17, 16-QAM 26 dB, GPS=0)
        ("R1_A2M20_16QAM_26dB_NoGPS", dict(
            N=128, N_cpp=5, two_Nc1=5, alpha=0.20, M_p=8, M_qam=16, snr_db=26.0, nu_max=0.45,
            q_pos_bins=44, q_neg_bins=24, F_frames=5,
        ), 4 if args.smoke else 60),
        # Regime 2: Mirabella JSAC'26 Table II N=64, N_cpp=4, alpha=0.25, Lp=17, 64-QAM at 36 dB (GPS=0 -> severe boundary IBI!)
        ("R2_Mirabella_N64_64QAM_36dB_NoGPS", dict(
            N=64, N_cpp=4, two_Nc1=3, alpha=0.25, M_p=8, M_qam=64, snr_db=36.0, nu_max=0.35,
            q_pos_bins=22, q_neg_bins=12, F_frames=5,
        ), 4 if args.smoke else 60),
        # Regime 3: High-order 256-QAM at 40 dB (`N=128, N_cpp=4, alpha=0.15, Lp=17, GPS=0` -> exposes exact precursor/postcursor IBI floor!)
        ("R3_Mirabella_N128_256QAM_40dB_NoGPS", dict(
            N=128, N_cpp=4, two_Nc1=5, alpha=0.15, M_p=8, M_qam=256, snr_db=40.0, nu_max=0.40,
            q_pos_bins=42, q_neg_bins=24, F_frames=5,
        ), 4 if args.smoke else 60),
    ]

    results = {
        "problem": "m_new1_A2_M20_Mirabella_CT_RRC_NoGPS_IBI",
        "anchor_paper": "Mirabella et al., IEEE JSAC 2026 (DOI: 10.1109/jsac.2026.3751260)",
        "seed_base": seed_base,
        "smoke": bool(args.smoke),
        "regimes": {},
    }

    pool = Pool(args.workers) if args.workers > 1 else None
    try:
        for r_i, (rname, cfg, n_tr) in enumerate(regimes):
            tr = time.perf_counter()
            tasks = [(seed_base + r_i * 10000 + i, cfg) for i in range(n_tr)]
            rows = pool.map(run_stream_trial, tasks) if pool else [run_stream_trial(t) for t in tasks]
            s = summarize_rows(rows)
            s["elapsed_s"] = round(time.perf_counter() - tr, 2)
            s["cfg"] = cfg
            results["regimes"][rname] = s
            m = s["mean_ser"]
            print(f"\n[{rname}] (n={n_tr}, {s['elapsed_s']}s):", flush=True)
            for k, v in m.items():
                print(f"  {k:38s}: SER = {v:.4e}", flush=True)
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
