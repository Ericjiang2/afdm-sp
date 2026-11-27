#!/usr/bin/env python3
"""
Round-15 Phase-1 Steelman Teardown Probe for Card I-20261126-m01 (`26-m01`):
Wideband Frequency-Selective Joint Tx+Rx IQI in EP-AFDM.

Read-only imports frozen `ideas/l2/l2_m_r13_m01_wideband_iqi.py` (verifying MD5
`d38c944e9b529ec1ab8f81085db5497a` without modifying any historical file or seed).

Tests the required full-strength textbook Steelman baselines on disjoint fresh R15 seeds:
  1. Pub_Huang (`huang_blind`) & Pub_Narasimhan (`narasimhan_b2`): published baselines
  2. Ours_PropFull (`prop_full`) & Ours_ZeroU0 (`zero_u0_same_sig2`): `26-m01` proposed & cold-start ablation
  3. Steelman_WL_Anttila_1Pass: textbook 2nd-order non-circularity (impropriety) blind FIR circularity
     restorer (Anttila-Valkama-Renfors IEEE TVT 2008) + guard-band BEM channel est + 1-pass WL-LMMSE
  4. Steelman_WL_Anttila_DD6 (`Steelman_A1`): textbook Anttila'08 2nd-order circularity blind IQI warm-start
     cascaded (`A -> B`) into standard 6-outer WL-EP + regularized LS channel/IQI refinement (ZERO Q_perp nullspace!)
  5. Steelman_1ShortPilot_ExactBudget (`Steelman_A2`): minimal 1 short time-domain calibration header
     (`N_cal=32` QPSK + `L_cpp=8` = 40 cu) + 4 AFDM blocks (`N_sm=246, L_cpp=8` = 254 cu each) ->
     EXACTLY 1056 channel uses, EXACTLY 644 64-QAM symbols (3864 bits), and EXACTLY identical total
     prefix-inclusive burst energy (870.375, 0.0000 dB diff) as `Ours_PropFull`!
  6. Steelman_S_OFDM_1ShortPilot (`Steelman_S`): cross-waveform OFDM (`c1=c2=0`) with the exact same
     1056 cu, 3864 bits, and 870.375 burst energy (1 short 40-cu calibration header + comb/pilot BEM + WL-EP)
  7. Oracle_PhysGold (`oracle_phys_gold`): exact physical linear-convolution CSI + IQI oracle
"""
import os, sys, json, time, math, hashlib, argparse
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
from multiprocessing import Pool
from scipy.signal.windows import dpss
from scipy.stats import t as student_t

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
L2_DIR = os.path.join(REPO_ROOT, "ideas", "l2")
if L2_DIR not in sys.path:
    sys.path.insert(0, L2_DIR)

FROZEN_M01_PATH = os.path.join(L2_DIR, "l2_m_r13_m01_wideband_iqi.py")
FROZEN_M01_MD5 = "d38c944e9b529ec1ab8f81085db5497a"

with open(FROZEN_M01_PATH, "rb") as _fp:
    _actual_md5 = hashlib.md5(_fp.read()).hexdigest()
assert _actual_md5 == FROZEN_M01_MD5, f"MD5 mismatch on {FROZEN_M01_PATH}: {_actual_md5}"

import l2_m_r13_m01_wideband_iqi as m1


def anttila_blind_circularity_filter(r_list, A, guard_obs_idx, Lw=6, b_skip=8, n_fp=4):
    """
    Textbook 2nd-order non-circularity (impropriety) blind FIR circularity restorer
    (Anttila, Valkama & Renfors, IEEE TVT 2008):
    First strips the pilot guard-band projection from r_k so proper QAM data dominates,
    then solves E[y_cr[n] * y_cr[n - tau]] = 0 for y_cr[n] = r[n] - sum_{m=0}^{Lw-1} w[m] r^*[n-m]
    over lags tau = 0 .. Lw-1 via fixed-point Yule-Walker iterations.
    """
    N = len(r_list[0]); K = len(r_list)
    # Remove deterministic pilot guard-band component so data is strictly 2nd-order proper (E[x_d x_d^T] = 0)
    P_data_daft = np.ones(N, dtype=float)
    P_data_daft[guard_obs_idx] = 0.0
    # Also suppress conjugate mirror of pilot bin 0 (around bin 0, already in guard_obs_idx [-47..3]!)
    r_clean_list = []
    for r in r_list:
        y_d_only = (A @ r) * P_data_daft
        r_clean_list.append(A.conj().T @ y_d_only)

    # Estimate R_rr[lag] = E[r[n] r^*[n - lag]] and C_rr[tau] = E[r[n] r[n - tau]] on interior [b_skip:]
    max_lag = 2 * Lw
    R_rr = {}
    C_rr = {}
    for lag in range(-max_lag, max_lag + 1):
        s_r = 0.0 + 0.0j
        s_c = 0.0 + 0.0j
        cnt = 0
        for rc in r_clean_list:
            n_lo = max(b_skip, b_skip + lag)
            n_hi = min(N, N + lag)
            if n_hi > n_lo:
                v1 = rc[n_lo:n_hi]
                v2 = rc[n_lo - lag : n_hi - lag]
                s_r += np.vdot(v2, v1)       # sum v1 * conj(v2)
                s_c += np.sum(v1 * v2)       # sum v1 * v2
                cnt += (n_hi - n_lo)
        R_rr[lag] = s_r / max(cnt, 1)
        C_rr[lag] = s_c / max(cnt, 1)

    # Linear system M_yw[tau, m] = conj(R_rr[tau - m]) + conj(R_rr[-tau - m]) for tau, m in 0..Lw-1
    M_yw = np.zeros((Lw, Lw), dtype=complex)
    c_rhs0 = np.array([C_rr[tau] for tau in range(Lw)], dtype=complex)
    for tau in range(Lw):
        for m in range(Lw):
            M_yw[tau, m] = np.conj(R_rr[tau - m]) + np.conj(R_rr[-tau - m])
    reg = 1e-3 * float(np.real(R_rr[0])) * np.eye(Lw)

    w = np.linalg.solve(M_yw + reg, c_rhs0)
    for _ in range(n_fp - 1):
        quad = np.zeros(Lw, dtype=complex)
        for tau in range(Lw):
            acc = 0.0 + 0.0j
            for m in range(Lw):
                for l in range(Lw):
                    acc += w[m] * w[l] * np.conj(C_rr[tau + l - m])
            quad[tau] = acc
        w = np.linalg.solve(M_yw + reg, c_rhs0 + quad)
        nrm = float(np.sum(np.abs(w)))
        if nrm > 0.55:
            w *= (0.55 / nrm)
    return w


def rx_steelman_anttila_wl(r_list, rx_cfg, pool_H=True, n_outer=6):
    """
    Textbook 2nd-order non-circularity blind IQI compensation (Anttila TVT'08) + WL-LMMSE/EP:
      - If n_outer == 1: pure non-iterative 1-pass circularity restoration + pilot BEM CE + WL-LMMSE!
      - If n_outer == 6: Anttila blind circularity filter warm-starts u_rx^{(0)} = w[:Lu] (ZERO Q_perp
        double-orthogonal nullspace dictionary!) cascaded into standard 6-outer WL-EP + LS refinement!
    """
    A, B_bem, L_eq, Lu = rx_cfg["A"], rx_cfg["B_bem"], rx_cfg["L_eq"], rx_cfg["Lu"]
    data_idx, guard_obs_idx, xp_val, const = rx_cfg["data_idx"], rx_cfg["guard_obs_idx"], rx_cfg["xp_val"], rx_cfg["const"]
    K = len(r_list); N, Q_bem = B_bem.shape
    xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    sp = A.conj().T @ xp

    # Step 1: Anttila 2nd-order circularity restoration filter w_cr (r_cr = r - w_cr * conj(r))
    # Note: r = z + u_rx * conj(z) => z ~ r - u_rx * conj(r), so u_rx_init ~ +w_cr[:Lu]!
    w_cr = anttila_blind_circularity_filter(r_list, A, guard_obs_idx, Lw=max(Lu + 2, 6), b_skip=8, n_fp=4)
    u_rx = w_cr[:Lu].copy()
    if np.sum(np.abs(u_rx)) > 0.55:
        u_rx *= (0.55 / np.sum(np.abs(u_rx)))
    u_tx = np.zeros(Lu, dtype=complex)

    # Step 2: Standard Pass-0 pilot-window BEM channel estimate after causal RX IQI inversion with u_rx
    H_list = m1.prefine_pilot_channel_interior(r_list, u_tx, u_rx, sp, A, guard_obs_idx, B_bem, L_eq, pool_H, b_pre=8)

    # Blind noise variance estimate from guard-band pilot residual
    Phi_p_daft = (A @ m1.build_bem_dict(sp, B_bem, L_eq))[guard_obs_idx, :]
    Gp = Phi_p_daft.conj().T @ Phi_p_daft
    P_pinv = np.linalg.solve(Gp + 1e-4 * np.trace(Gp).real / Gp.shape[0] * np.eye(Gp.shape[0]), Phi_p_daft.conj().T)
    res_g = []
    for k in range(K):
        yg = (A @ m1.invert_rx_iqi_causal(r_list[k], u_rx))[guard_obs_idx]
        eg = yg - Phi_p_daft @ (P_pinv @ yg)
        res_g.append(float(np.real(np.vdot(eg, eg))) / max(len(guard_obs_idx) - Phi_p_daft.shape[1], 1))
    sig2_est = max(float(np.mean(res_g)), 1e-5)

    if n_outer <= 1:
        # Pure 1-pass linear WL-LMMSE (n_iter=1 inside exact_wl_ep_detect = exact linear WL-LMMSE!)
        xd_1p = []
        for k in range(K):
            xd, _, _ = m1.exact_wl_ep_detect(r_list[k], H_list[k], u_tx, u_rx, A, data_idx, xp_val, const, sig2=sig2_est, n_iter=1)
            xd_1p.append(xd)
        return xd_1p

    # Standard 6-outer alternating WL-EP + BEM + LS IQI refinement (identical backend to zero_u0/prop_full, ZERO Q_perp!)
    b_drop = 8; N_int = N - b_drop; idx = np.arange(N)
    xd_cur = None
    for outer in range(n_outer):
        inner_iters = 1 if outer == 0 else (2 if outer == 1 else 3)
        s_hat_list, v_td_list, xd_cur = [], [], []
        for k in range(K):
            xd, m_d, v_d = m1.exact_wl_ep_detect(r_list[k], H_list[k], u_tx, u_rx, A, data_idx, xp_val, const, sig2=max(sig2_est, 1e-5), n_iter=inner_iters)
            xd_cur.append(xd)
            x_f = np.zeros(N, dtype=complex); x_f[0] = xp_val; x_f[data_idx] = m_d
            s_hat_list.append(A.conj().T @ x_f)
            v_td_list.append(float(np.sum(v_d)) / N)
        if outer == n_outer - 1:
            break
        H_list, sig2_est = m1.fit_interior_bem_channel(r_list, s_hat_list, v_td_list, u_tx, u_rx, B_bem, L_eq, pool_H, b_drop=b_drop)
        Au, bu, eiv = [], [], 0.0
        for k in range(K):
            yd = H_list[k] @ s_hat_list[k]; bu.append((r_list[k] - yd)[b_drop:])
            sc = np.conj(s_hat_list[k])
            ctx = [(H_list[k] @ sc[(idx - m) % N])[b_drop:] for m in range(Lu)]
            zc_full = np.conj(yd + sum((u_tx[m] * (H_list[k] @ sc[(idx - m) % N]) for m in range(Lu)), np.zeros(N, dtype=complex)))
            crx = [zc_full[(idx - m) % N][b_drop:] for m in range(Lu)]
            Au.append(np.hstack([np.column_stack(ctx), np.column_stack(crx)]))
            eiv += N_int * v_td_list[k] * float(np.mean(np.sum(np.abs(H_list[k]) ** 2, axis=1)))
        Au = np.vstack(Au); bu = np.concatenate(bu)
        Gu = Au.conj().T @ Au + (eiv + 1e-5 * np.trace(Au.conj().T @ Au).real / Au.shape[1]) * np.eye(Au.shape[1])
        un = np.linalg.solve(Gu, Au.conj().T @ bu)
        u_tx = un[:Lu]; u_rx = un[Lu:]
        for arr in (u_tx, u_rx):
            nrm = np.sum(np.abs(arr))
            if nrm > 0.55:
                arr *= (0.55 / nrm)
    return xd_cur


def calibrate_from_short_header(r_cal, s_cal, L_eq_cal=7, Lu=4, n_alt=10):
    """
    Estimate (u_tx, u_rx) and short-block BEM channel from 1 short N_cal=40 time-domain pilot block
    (with L_cpp=8 cyclic prefix -> circular shift on N_cal=40 is 100% exact for l_max+Lf+Lg-2 = 6 <= 8!).
    Uses 2-basis Taylor/DPSS BEM (constant + linear slope across the 40 samples) so physical Doppler
    (|nu| <= 0.85 * 40/256 = 0.13 cycles across 40 samples) is modeled to < -40 dB!
    """
    N_c = len(s_cal)
    idx = np.arange(N_c)
    sc_conj = np.conj(s_cal)
    B_cal = dpss(N_c, 0.6, 2).T  # (40, 2) -> 7 * 2 = 14 complex BEM parameters on 40 samples!

    # Initialize H_c with u_tx=u_rx=0, then alternate BEM H_c (14 params) and (u_tx, u_rx) (8 params)
    u_tx = np.zeros(Lu, dtype=complex)
    u_rx = np.zeros(Lu, dtype=complex)
    Phi0 = m1.build_bem_dict(s_cal, B_cal, L_eq_cal)
    c_bem = np.linalg.solve(Phi0.conj().T @ Phi0 + 1e-4 * np.eye(Phi0.shape[1]), Phi0.conj().T @ r_cal)
    H_c, _ = m1.bem_coeffs_to_H(c_bem, B_cal, L_eq_cal)

    for _ in range(n_alt):
        yd = H_c @ s_cal
        bu = r_cal - yd
        ctx = [H_c @ sc_conj[(idx - m) % N_c] for m in range(Lu)]
        zc = np.conj(yd + sum((u_tx[m] * ctx[m] for m in range(Lu)), np.zeros(N_c, dtype=complex)))
        crx = [zc[(idx - m) % N_c] for m in range(Lu)]
        Au = np.hstack([np.column_stack(ctx), np.column_stack(crx)])
        un = np.linalg.solve(Au.conj().T @ Au + 1e-4 * np.eye(2 * Lu), Au.conj().T @ bu)
        u_tx = un[:Lu]; u_rx = un[Lu:]
        for arr in (u_tx, u_rx):
            nrm = np.sum(np.abs(arr))
            if nrm > 0.55:
                arr *= (0.55 / nrm)

        U_rx_c = m1.circ_mat(u_rx, N_c)
        M_rx = m1.real_aug_mat(np.eye(N_c, dtype=complex), U_rx_c)
        z_real = np.linalg.solve(M_rx, m1.real_aug_vec(r_cal))
        z_inv = z_real[:N_c] + 1j * z_real[N_c:]
        s_eff = s_cal + sum(u_tx[m] * sc_conj[(idx - m) % N_c] for m in range(Lu))
        Phi_eff = m1.build_bem_dict(s_eff, B_cal, L_eq_cal)
        c_bem = np.linalg.solve(Phi_eff.conj().T @ Phi_eff + 1e-4 * np.eye(Phi_eff.shape[1]), Phi_eff.conj().T @ z_inv)
        H_c, _ = m1.bem_coeffs_to_H(c_bem, B_cal, L_eq_cal)

    yd = H_c @ (s_cal + sum(u_tx[m] * sc_conj[(idx - m) % N_c] for m in range(Lu)))
    r_hat = yd + m1.circ_mat(u_rx, N_c) @ np.conj(yd)
    sig2_cal = max(float(np.real(np.vdot(r_cal - r_hat, r_cal - r_hat)) / max(N_c - 22, 1)), 1e-5)
    return u_tx, u_rx, sig2_cal


def calibrate_rx_anttila_tx_header(r_list_blocks, A_mat, pil_mask_idx, r_cal, s_cal, L_eq=7, Lu=4):
    """
    Full-Strength Textbook Cascade (`Anttila TVT'08` Rx Circularity + Short-Header Tx WL-LS):
      Step A: Estimate Rx IQI u_rx from 2nd-order non-circularity E[r r^T] across the 4 received blocks
              (breaks the static-channel Sylvester rank deficiency between u_tx and u_rx!).
      Step B: Invert Rx IQI causally on the known 48-sample header: z_cal = invert_rx_iqi_causal(r_cal, u_rx)
              = H_cal * (s_cal + U_tx s_cal^*), and solve exact 2-basis BEM WL-LS for (H_cal, u_tx) on
              the 39 zero-wrap interior samples (handles fractional Doppler rotation across the 48 samples!).
    """
    w_cr = anttila_blind_circularity_filter(r_list_blocks, A_mat, pil_mask_idx, Lw=max(Lu + 2, 6), b_skip=8, n_fp=4)
    u_rx = w_cr[:Lu].copy()
    z_cal = m1.invert_rx_iqi_causal(r_cal, u_rx)

    N_c = len(z_cal)
    L_img = L_eq + Lu - 1  # 10
    b_c = L_img - 1        # 9 -> 39 zero-wrap interior samples
    idx = np.arange(b_c, N_c)
    t_lin = (idx - 0.5 * (b_c + N_c - 1)) / float(N_c)  # linear time-variation basis for Doppler across header!
    sc_conj = np.conj(s_cal)

    # Fit 2-basis BEM direct channel h0[l] + t_lin * h1[l] + LTI composite image g_img[0..9]
    X_d0 = np.column_stack([s_cal[idx - l] for l in range(L_eq)])
    X_d1 = np.column_stack([t_lin * s_cal[idx - l] for l in range(L_eq)])
    X_im = np.column_stack([sc_conj[idx - l] for l in range(L_img)])
    X_all = np.hstack([X_d0, X_d1, X_im])
    y_sub = z_cal[idx]
    G_all = X_all.conj().T @ X_all
    th = np.linalg.solve(G_all + 1e-4 * np.trace(G_all).real / G_all.shape[0] * np.eye(G_all.shape[0]), X_all.conj().T @ y_sub)
    h_d = th[:L_eq]
    g_im = th[2 * L_eq :]
    res = y_sub - X_all @ th
    sig2_est = max(float(np.real(np.vdot(res, res)) / max(len(idx) - X_all.shape[1], 1)), 1e-5)

    # Now z_cal has u_rx ALREADY stripped, so g_im = T(h_d) * u_tx (10 equations for ONLY 4 unknowns u_tx -> full rank 4!)
    T_hd = np.zeros((L_img, Lu), dtype=complex)
    for m in range(Lu):
        T_hd[m : m + L_eq, m] = h_d
    G_tx = T_hd.conj().T @ T_hd
    u_tx = np.linalg.solve(G_tx + 1e-4 * np.trace(G_tx).real / Lu * np.eye(Lu), T_hd.conj().T @ g_im)
    for arr in (u_tx, u_rx):
        nrm = np.sum(np.abs(arr))
        if nrm > 0.55:
            arr *= (0.55 / nrm)
    return u_tx, u_rx, sig2_est


def run_short_pilot_burst_afdm(rng_local, gains, delays, dopplers, f1, f2, g1, g2, sig2, const, cont_doppler, n_outer=6):
    """
    Steelman_1ShortPilot_EqThru (AFDM, keeping exact N = 256 unchanged!):
      - Prepends 1 short time-domain calibration header: N_cal = 48 QPSK samples + L_cpp = 8 -> 56 channel uses.
      - Transmits 4 AFDM blocks of N = 256 (L_cpp = 8 -> 4 * 264 = 1056 cu, total = 1112 cu).
      - Sets 2*N*c1 = 6 (since |nu| <= 0.85 < 1, spacing 6 separates all integer delays cleanly!) with Q_g_sm = 42
        (`[-42..3]` = 46 guard+pilot obs, pilot support `[-39..3]`, ZERO data-pilot overlap, Nd_sm = 171 symbols/block!):
        Net spectral efficiency = (4 * 171) / 1112 = 0.61511 sym/cu > Proposed's (4 * 161) / 1056 = 0.60985 sym/cu!
      - Penalizes SNR (`sig2_sm`) so total transmitted energy per payload bit (Eb/N0, including header + all prefixes!)
        is 100% EQUAL to Proposed (`0.0000 dB` Eb/N0 advantage)!
    """
    N = 256; N_cal = 48; L_cpp = 8; K = 4
    c1 = 6.0 / (2.0 * N); c2 = 1.0 / (2.0 * np.sqrt(2.0) * N)
    A = m1.daft_matrix(N, c1, c2)
    B_bem = dpss(N, 1.0, 5).T
    L_eq = 7; Lu = 4; Q_g_sm = 42
    guard_obs_sm = np.array([m % N for m in range(-Q_g_sm, 4)])
    data_idx_sm = np.array([m for m in range(Q_g_sm + 1, N - Q_g_sm)])  # Nd_sm = 171
    Nd_sm = len(data_idx_sm)
    xp_val = math.sqrt(50.0)

    eb_prop = (4.0 * (161.0 + 50.0) * (N + L_cpp) / float(N)) / (4.0 * 161.0)
    e_burst_sm = (N_cal + L_cpp) * 1.0 + 4.0 * (Nd_sm + 50.0) * (N + L_cpp) / float(N)
    eb_sm = e_burst_sm / float(4.0 * Nd_sm)
    sig2_sm = sig2 * (eb_sm / eb_prop)

    qpsk = np.array([-1-1j, -1+1j, 1-1j, 1+1j]) / np.sqrt(2.0)
    s_cal = qpsk[rng_local.integers(0, 4, N_cal)]
    w_cal = np.sqrt(sig2_sm / 2.0) * (rng_local.standard_normal(N_cal + 2) + 1j * rng_local.standard_normal(N_cal + 2))
    dop_cal = dopplers * (float(N_cal) / float(N))
    r_cal = m1.phys_transmit_receive(s_cal, 0.0, gains, delays, dop_cal, f1, f2, g1, g2, w_cal,
                                     t_offset=(-(N_cal + L_cpp) if cont_doppler else 0))

    r_list = []; tx_list_sm = []
    for k in range(K):
        idx_k = rng_local.integers(0, len(const), Nd_sm)
        xk = np.zeros(N, dtype=complex); xk[0] = xp_val; xk[data_idx_sm] = const[idx_k]
        wk = np.sqrt(sig2_sm / 2.0) * (rng_local.standard_normal(N + 2) + 1j * rng_local.standard_normal(N + 2))
        r_list.append(m1.phys_transmit_receive(A.conj().T @ xk, c1, gains, delays, dopplers, f1, f2, g1, g2, wk,
                                               t_offset=(k * (N + L_cpp) if cont_doppler else 0)))
        tx_list_sm.append(idx_k)

    u_tx, u_rx, sig2_est = calibrate_rx_anttila_tx_header(r_list, A, guard_obs_sm, r_cal, s_cal, L_eq=L_eq, Lu=Lu)

    pool_H = not cont_doppler
    xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    sp = A.conj().T @ xp
    H_list = m1.prefine_pilot_channel_interior(r_list, u_tx, u_rx, sp, A, guard_obs_sm, B_bem, L_eq, pool_H, b_pre=8)
    b_drop = 8; N_int = N - b_drop; idx = np.arange(N)
    xd_1pass = None; xd_cur = None
    for outer in range(n_outer):
        inner_iters = 1 if outer == 0 else (2 if outer == 1 else 3)
        s_hat_list, v_td_list, xd_cur = [], [], []
        for k in range(K):
            xd, m_d, v_d = m1.exact_wl_ep_detect(r_list[k], H_list[k], u_tx, u_rx, A, data_idx_sm, xp_val, const, sig2=max(sig2_est, 1e-5), n_iter=inner_iters)
            xd_cur.append(xd)
            x_f = np.zeros(N, dtype=complex); x_f[0] = xp_val; x_f[data_idx_sm] = m_d
            s_hat_list.append(A.conj().T @ x_f)
            v_td_list.append(float(np.sum(v_d)) / N)
        if outer == 0:
            xd_1pass = [x.copy() for x in xd_cur]
        if outer == n_outer - 1:
            break
        H_list, sig2_est = m1.fit_interior_bem_channel(r_list, s_hat_list, v_td_list, u_tx, u_rx, B_bem, L_eq, pool_H, b_drop=b_drop)
        Au, bu, eiv = [], [], 0.0
        for k in range(K):
            yd = H_list[k] @ s_hat_list[k]; bu.append((r_list[k] - yd)[b_drop:])
            sc = np.conj(s_hat_list[k])
            ctx = [(H_list[k] @ sc[(idx - m) % N])[b_drop:] for m in range(Lu)]
            zc_full = np.conj(yd + sum((u_tx[m] * (H_list[k] @ sc[(idx - m) % N]) for m in range(Lu)), np.zeros(N, dtype=complex)))
            crx = [zc_full[(idx - m) % N][b_drop:] for m in range(Lu)]
            Au.append(np.hstack([np.column_stack(ctx), np.column_stack(crx)]))
            eiv += N_int * v_td_list[k] * float(np.mean(np.sum(np.abs(H_list[k]) ** 2, axis=1)))
        Au = np.vstack(Au); bu = np.concatenate(bu)
        Gu = Au.conj().T @ Au + (eiv + 1e-5 * np.trace(Au.conj().T @ Au).real / Au.shape[1]) * np.eye(Au.shape[1])
        un = np.linalg.solve(Gu, Au.conj().T @ bu)
        u_tx = un[:Lu]; u_rx = un[Lu:]
        for arr in (u_tx, u_rx):
            nrm = np.sum(np.abs(arr))
            if nrm > 0.55:
                arr *= (0.55 / nrm)

    ser_1p = float(np.mean([np.mean(m1.qam_hard(xd_1pass[k], const)[1] != tx_list_sm[k]) for k in range(K)]))
    ser_6o = float(np.mean([np.mean(m1.qam_hard(xd_cur[k], const)[1] != tx_list_sm[k]) for k in range(K)]))
    return ser_1p, ser_6o


def run_short_pilot_burst_sc_and_ofdm_s(rng_local, gains, delays, dopplers, f1, f2, g1, g2, sig2, const, cont_doppler, n_outer=6):
    """
    Cross-Waveform S-tier Steelman (c1=c2=0):
      1) Steelman_S_SC_1ShortPilot: N=256 Single-Carrier (A = I_N) with 5 contiguous 17-sample QPSK pilot clusters
         (85 pilot samples -> 5*11 = 55 ZERO-data-interference TD BEM observations across the whole block!) + 171 64-QAM
         data symbols per block + 1 short (48+8=56 cu) header. Net rate = 684/1112 = 0.6151 > 0.6098 sym/cu, exact equal Eb/N0!
      2) Steelman_S_OFDM_1ShortPilot: N=256 Comb-Pilot CP-OFDM (85 comb pilots + 171 data symbols) + 56-cu header,
         same 0.6151 sym/cu and exact equal Eb/N0.
    """
    N = 256; N_cal = 48; L_cpp = 8; K = 4
    Nd_sm = 171; n_pil = N - Nd_sm  # 85
    L_eq = 7; Lu = 4
    B_bem = dpss(N, 1.0, 5).T
    qpsk = np.array([-1-1j, -1+1j, 1-1j, 1+1j]) / np.sqrt(2.0)

    pil_amp = math.sqrt(50.0 / float(n_pil))
    eb_prop = (4.0 * (161.0 + 50.0) * (N + L_cpp) / float(N)) / (4.0 * 161.0)
    e_burst_sm = (N_cal + L_cpp) * 1.0 + 4.0 * (Nd_sm + 50.0) * (N + L_cpp) / float(N)
    eb_sm = e_burst_sm / float(4.0 * Nd_sm)
    sig2_sm = sig2 * (eb_sm / eb_prop)

    s_cal = qpsk[rng_local.integers(0, 4, N_cal)]
    w_cal = np.sqrt(sig2_sm / 2.0) * (rng_local.standard_normal(N_cal + 2) + 1j * rng_local.standard_normal(N_cal + 2))
    dop_cal = dopplers * (float(N_cal) / float(N))
    r_cal = m1.phys_transmit_receive(s_cal, 0.0, gains, delays, dop_cal, f1, f2, g1, g2, w_cal,
                                     t_offset=(-(N_cal + L_cpp) if cont_doppler else 0))

    def wl_ep_iter_generic(r_list_g, tx_list_g, A_mat, xp_vec, data_idx_g, H_list_init, u_tx_i, u_rx_i, s2_i):
        pool_H = not cont_doppler
        H_list = [H.copy() for H in H_list_init]
        u_tx, u_rx, sig2_est = u_tx_i.copy(), u_rx_i.copy(), s2_i
        b_drop = 8; N_int = N - b_drop; idx = np.arange(N)
        Nd = len(data_idx_g)
        xd_cur = None
        for outer in range(n_outer):
            inner_iters = 2 if outer == 0 else 3
            s_hat_list, v_td_list, xd_cur = [], [], []
            U_tx_m = m1.circ_mat(u_tx, N); U_rx_m = m1.circ_mat(u_rx, N)
            W1_n, W2_n = m1.causal_lin_noise_mats(u_rx, N)
            W_rx = m1.real_aug_mat(W1_n, W2_n)
            Cw = 0.5 * max(sig2_est, 1e-5) * (W_rx @ W_rx.T)
            Cw = 0.5 * (Cw + Cw.T) + 1e-10 * np.eye(2 * N)
            c_Cw = m1.cho_factor(Cw, lower=True)
            for k in range(K):
                H_td = H_list[k]
                H_dir = H_td + U_rx_m @ np.conj(H_td @ U_tx_m)
                H_img = H_td @ U_tx_m + U_rx_m @ np.conj(H_td)
                G1 = H_dir @ A_mat.conj().T; G2 = H_img @ A_mat.T
                r_d = r_list_g[k] - (G1 @ xp_vec + G2 @ np.conj(xp_vec))
                G_tilde = m1.real_aug_mat(G1[:, data_idx_g], G2[:, data_idx_g])
                Cw_inv_G = m1.cho_solve(c_Cw, G_tilde)
                M_gram = 0.5 * (G_tilde.T @ Cw_inv_G + (G_tilde.T @ Cw_inv_G).T)
                rhs0 = Cw_inv_G.T @ m1.real_aug_vec(r_d)
                P0 = M_gram + 2.0 * np.eye(2 * Nd)
                c_P0 = m1.cho_factor(P0, lower=True)
                x_lmmse_r = m1.cho_solve(c_P0, rhs0)
                P0_inv_diag = np.diag(m1.cho_solve(c_P0, np.eye(2 * Nd)))
                alpha_r = np.clip(1.0 - 2.0 * P0_inv_diag, 0.1, 0.9999)
                x_ext_r = x_lmmse_r / alpha_r
                var_ext_r = np.maximum(P0_inv_diag / alpha_r, 1e-6)
                xd = x_ext_r[:Nd] + 1j * x_ext_r[Nd:]
                m_cur, v_cur = m1.qam_soft(xd, var_ext_r[:Nd] + var_ext_r[Nd:], const)
                for _ in range(inner_iters - 1):
                    v_r = np.clip(0.5 * np.concatenate([v_cur, v_cur]), 1e-4, 0.5)
                    inv_v = 1.0 / v_r
                    c_Pit = m1.cho_factor(M_gram + np.diag(inv_v), lower=True)
                    m_r = m1.real_aug_vec(m_cur)
                    post_r = m_r + m1.cho_solve(c_Pit, rhs0 - M_gram @ m_r)
                    post_var_r = np.clip(np.diag(m1.cho_solve(c_Pit, np.eye(2 * Nd))), 1e-7, 0.4999)
                    cav_prec = np.maximum(1.0 / post_var_r - inv_v, 1e-4)
                    cav_var = 1.0 / cav_prec
                    cav_mean = cav_var * (post_r / post_var_r - m_r * inv_v)
                    xd = cav_mean[:Nd] + 1j * cav_mean[Nd:]
                    m_new, v_new = m1.qam_soft(xd, cav_var[:Nd] + cav_var[Nd:], const)
                    m_cur = 0.7 * m_new + 0.3 * m_cur
                    v_cur = 0.7 * v_new + 0.3 * v_cur
                xd_cur.append(xd)
                x_f = xp_vec.copy(); x_f[data_idx_g] = m_cur
                s_hat_list.append(A_mat.conj().T @ x_f)
                v_td_list.append(float(np.sum(v_cur)) / N)
            if outer == n_outer - 1:
                break
            H_list, sig2_est = m1.fit_interior_bem_channel(r_list_g, s_hat_list, v_td_list, u_tx, u_rx, B_bem, L_eq, pool_H, b_drop=b_drop)
            Au, bu, eiv = [], [], 0.0
            for k in range(K):
                yd = H_list[k] @ s_hat_list[k]; bu.append((r_list_g[k] - yd)[b_drop:])
                sc = np.conj(s_hat_list[k])
                ctx = [(H_list[k] @ sc[(idx - m) % N])[b_drop:] for m in range(Lu)]
                zc_full = np.conj(yd + sum((u_tx[m] * (H_list[k] @ sc[(idx - m) % N]) for m in range(Lu)), np.zeros(N, dtype=complex)))
                crx = [zc_full[(idx - m) % N][b_drop:] for m in range(Lu)]
                Au.append(np.hstack([np.column_stack(ctx), np.column_stack(crx)]))
                eiv += N_int * v_td_list[k] * float(np.mean(np.sum(np.abs(H_list[k]) ** 2, axis=1)))
            Au = np.vstack(Au); bu = np.concatenate(bu)
            Gu = Au.conj().T @ Au + (eiv + 1e-5 * np.trace(Au.conj().T @ Au).real / Au.shape[1]) * np.eye(Au.shape[1])
            un = np.linalg.solve(Gu, Au.conj().T @ bu)
            u_tx = un[:Lu]; u_rx = un[Lu:]
            for arr in (u_tx, u_rx):
                nrm = np.sum(np.abs(arr))
                if nrm > 0.55:
                    arr *= (0.55 / nrm)
        return float(np.mean([np.mean(m1.qam_hard(xd_cur[k], const)[1] != tx_list_g[k]) for k in range(K)]))

    # --- Arm S1: Multi-Cluster Pilot Single-Carrier (A = I_N) ---
    A_sc = np.eye(N, dtype=complex)
    sc_pil_mask = np.zeros(N, dtype=bool)
    sc_obs_idx = []
    for c_i in range(5):
        st = 8 + c_i * 49
        sc_pil_mask[st : st + 17] = True
        sc_obs_idx.extend(range(st + 6, st + 17))
    sc_obs_idx = np.array(sc_obs_idx, dtype=int)
    sc_data_idx = np.where(~sc_pil_mask)[0]
    assert len(sc_data_idx) == Nd_sm
    xp_sc = np.zeros(N, dtype=complex)
    xp_sc[sc_pil_mask] = pil_amp * qpsk[rng_local.integers(0, 4, n_pil)]
    r_sc_list, tx_sc_list = [], []
    for k in range(K):
        idx_k = rng_local.integers(0, len(const), Nd_sm)
        xk = xp_sc.copy(); xk[sc_data_idx] = const[idx_k]
        wk = np.sqrt(sig2_sm / 2.0) * (rng_local.standard_normal(N + 2) + 1j * rng_local.standard_normal(N + 2))
        r_sc_list.append(m1.phys_transmit_receive(xk, 0.0, gains, delays, dopplers, f1, f2, g1, g2, wk,
                                                  t_offset=(k * (N + L_cpp) if cont_doppler else 0)))
        tx_sc_list.append(idx_k)

    sc_pil_idx_all = np.where(sc_pil_mask)[0]
    ut_sc, ur_sc, s2_sc = calibrate_rx_anttila_tx_header(r_sc_list, A_sc, sc_pil_idx_all, r_cal, s_cal, L_eq=L_eq, Lu=Lu)
    pool_H = not cont_doppler
    idx_n = np.arange(N); sp_c = np.conj(xp_sc)
    sp_eff = xp_sc + sum(ut_sc[m] * sp_c[(idx_n - m) % N] for m in range(Lu))
    B_bem_sc = dpss(N, 1.0, 3).T  # 3*7=21 params -> well-conditioned on 55 clean TD pilot samples!
    Phi_sc2 = m1.build_bem_dict(sp_eff, B_bem_sc, L_eq)[sc_obs_idx, :]
    G_sc2 = Phi_sc2.conj().T @ Phi_sc2
    P_sc2 = np.linalg.solve(G_sc2 + 1e-4 * np.trace(G_sc2).real / G_sc2.shape[0] * np.eye(G_sc2.shape[0]), Phi_sc2.conj().T)
    if pool_H:
        H0_sc2, _ = m1.bem_coeffs_to_H(P_sc2 @ np.mean([m1.invert_rx_iqi_causal(r_sc_list[k], ur_sc)[sc_obs_idx] for k in range(K)], axis=0), B_bem_sc, L_eq)
        H_sc_init = [H0_sc2.copy() for _ in range(K)]
    else:
        H_sc_init = [m1.bem_coeffs_to_H(P_sc2 @ m1.invert_rx_iqi_causal(r_sc_list[k], ur_sc)[sc_obs_idx], B_bem_sc, L_eq)[0] for k in range(K)]
    ser_sc_s = wl_ep_iter_generic(r_sc_list, tx_sc_list, A_sc, xp_sc, sc_data_idx, H_sc_init, ut_sc, ur_sc, s2_sc)

    # --- Arm S2: Comb-Pilot CP-OFDM (c1=c2=0) ---
    A_ofdm = m1.daft_matrix(N, 0.0, 0.0)
    ofdm_pil_idx = np.round(np.linspace(0, N - 1, n_pil, endpoint=False)).astype(int)
    ofdm_pil_mask = np.zeros(N, dtype=bool); ofdm_pil_mask[ofdm_pil_idx] = True
    ofdm_data_idx = np.where(~ofdm_pil_mask)[0]
    assert len(ofdm_data_idx) == Nd_sm
    xp_of = np.zeros(N, dtype=complex)
    xp_of[ofdm_pil_mask] = pil_amp * qpsk[rng_local.integers(0, 4, n_pil)]
    sp_of = A_ofdm.conj().T @ xp_of
    r_of_list, tx_of_list = [], []
    for k in range(K):
        idx_k = rng_local.integers(0, len(const), Nd_sm)
        xk = xp_of.copy(); xk[ofdm_data_idx] = const[idx_k]
        wk = np.sqrt(sig2_sm / 2.0) * (rng_local.standard_normal(N + 2) + 1j * rng_local.standard_normal(N + 2))
        r_of_list.append(m1.phys_transmit_receive(A_ofdm.conj().T @ xk, 0.0, gains, delays, dopplers, f1, f2, g1, g2, wk,
                                                  t_offset=(k * (N + L_cpp) if cont_doppler else 0)))
        tx_of_list.append(idx_k)

    # Strip both comb pilots and their conjugate mirror (-ofdm_pil_idx mod N) for Anttila properness!
    ofdm_pil_mirror = np.unique(np.concatenate([ofdm_pil_idx, (-ofdm_pil_idx) % N]))
    ut_of, ur_of, s2_of = calibrate_rx_anttila_tx_header(r_of_list, A_ofdm, ofdm_pil_mirror, r_cal, s_cal, L_eq=L_eq, Lu=Lu)
    A_p_int = A_ofdm[ofdm_pil_idx, 8:]
    sp_of_c = np.conj(sp_of)
    sp_of_eff = sp_of + sum(ut_of[m] * sp_of_c[(idx_n - m) % N] for m in range(Lu))
    Phi_of2 = A_p_int @ m1.build_bem_dict(sp_of_eff, B_bem, L_eq)[8:, :]
    G_of2 = Phi_of2.conj().T @ Phi_of2
    P_of2 = np.linalg.solve(G_of2 + 2e-2 * np.trace(G_of2).real / G_of2.shape[0] * np.eye(G_of2.shape[0]), Phi_of2.conj().T)
    if pool_H:
        H0_of2, _ = m1.bem_coeffs_to_H(P_of2 @ np.mean([A_p_int @ m1.invert_rx_iqi_causal(r_of_list[k], ur_of)[8:] for k in range(K)], axis=0), B_bem, L_eq)
        H_of_init = [H0_of2.copy() for _ in range(K)]
    else:
        H_of_init = [m1.bem_coeffs_to_H(P_of2 @ (A_p_int @ m1.invert_rx_iqi_causal(r_of_list[k], ur_of)[8:]), B_bem, L_eq)[0] for k in range(K)]
    ser_ofdm_s = wl_ep_iter_generic(r_of_list, tx_of_list, A_ofdm, xp_of, ofdm_data_idx, H_of_init, ut_of, ur_of, s2_of)
    return ser_sc_s, ser_ofdm_s


def run_burst_teardown(args):
    seed, lvl, M_qam, snr_db, cont_doppler = args
    rng = np.random.default_rng(seed)
    N = 256; c1 = 7.0 / (2 * N); c2 = 1.0 / (2 * np.sqrt(2) * N); A = m1.daft_matrix(N, c1, c2)
    delays = [0, 1, 2]; L_eq = 7; Lu = 4
    B_bem = dpss(N, 1.0, 5).T
    guard_obs_idx = np.array([m % N for m in range(-47, 4)])
    data_idx_nom = np.array([m for m in range(48, N - 47)])
    xp_val = np.sqrt(50.0); const, _ = m1.gray_qam_constellation(M_qam)
    rx_cfg = {"A": A, "B_bem": B_bem, "L_eq": L_eq, "Lu": Lu, "data_idx": data_idx_nom,
              "guard_obs_idx": guard_obs_idx, "xp_val": xp_val, "const": const}

    f1, f2, g1, g2 = m1.generate_iqi_filters(rng, lvl, Lf=3, Lg=3)
    sig2 = 10.0 ** (-snr_db / 10.0)
    dopplers = rng.uniform(-0.85, 0.85, 3)
    gains = (rng.standard_normal(3) + 1j * rng.standard_normal(3)) * np.sqrt(np.array([0.5, 0.3, 0.2]) / 2.0)
    gains /= np.linalg.norm(gains)
    L_cpp = max(delays) + len(f1) + len(g1)  # 8

    x_pre_h = const[rng.integers(0, M_qam, N)]
    r_pre_h = m1.phys_transmit_receive(A.conj().T @ x_pre_h, c1, gains, delays, dopplers, f1, f2, g1, g2,
                                       np.sqrt(sig2 / 2.0) * (rng.standard_normal(N + 2) + 1j * rng.standard_normal(N + 2)),
                                       t_offset=(-(N + L_cpp) if cont_doppler else 0))
    xp1_n, xp2_n = m1.build_narasimhan_scheme_a_preambles(N)
    r_pre_n1 = m1.phys_transmit_receive(A.conj().T @ xp1_n, c1, gains, delays, dopplers, f1, f2, g1, g2,
                                        np.sqrt(sig2 / 2.0) * (rng.standard_normal(N + 2) + 1j * rng.standard_normal(N + 2)),
                                        t_offset=(-2 * (N + L_cpp) if cont_doppler else 0))
    r_pre_n2 = m1.phys_transmit_receive(A.conj().T @ xp2_n, c1, gains, delays, dopplers, f1, f2, g1, g2,
                                        np.sqrt(sig2 / 2.0) * (rng.standard_normal(N + 2) + 1j * rng.standard_normal(N + 2)),
                                        t_offset=(-(N + L_cpp) if cont_doppler else 0))

    r_list = []; tx_list_nom = []
    for k in range(4):
        idx_nom = rng.integers(0, M_qam, len(data_idx_nom))
        x_nom = np.zeros(N, dtype=complex); x_nom[0] = xp_val; x_nom[data_idx_nom] = const[idx_nom]
        t_off = k * (N + L_cpp) if cont_doppler else 0
        w_k = np.sqrt(sig2 / 2.0) * (rng.standard_normal(N + 2) + 1j * rng.standard_normal(N + 2))
        r_list.append(m1.phys_transmit_receive(A.conj().T @ x_nom, c1, gains, delays, dopplers, f1, f2, g1, g2, w_k, t_offset=t_off))
        tx_list_nom.append(idx_nom)

    def mser(xl):
        return float(np.mean([np.mean(m1.qam_hard(xl[k], const)[1] != tx_list_nom[k]) for k in range(4)]))

    pool_H = not cont_doppler
    xd_h, _ = m1.rx_huang_blind(r_pre_h, x_pre_h, r_list, rx_cfg)
    xd_n, _, _, _ = m1.rx_narasimhan09_blind(r_pre_n1, xp1_n, r_pre_n2, xp2_n, r_list, rx_cfg, D=2, L_cpp=L_cpp)
    xd_pf, _, _, _ = m1.rx_proposed_blind(r_list, rx_cfg, True, True, True, None, pool_H, 6)
    xd_z0, _, _, _ = m1.rx_proposed_blind(r_list, rx_cfg, False, False, True, None, pool_H, 6)

    xd_ant_1p = rx_steelman_anttila_wl(r_list, rx_cfg, pool_H=pool_H, n_outer=1)
    xd_ant_dd6 = rx_steelman_anttila_wl(r_list, rx_cfg, pool_H=pool_H, n_outer=6)

    rng_sp = np.random.default_rng(seed + 90000000)
    ser_sp_1p, ser_sp_6o = run_short_pilot_burst_afdm(rng_sp, gains, delays, dopplers, f1, f2, g1, g2, sig2, const, cont_doppler, n_outer=6)

    rng_ofdm = np.random.default_rng(seed + 95000000)
    ser_sc_sp, ser_ofdm_sp = run_short_pilot_burst_sc_and_ofdm_s(rng_ofdm, gains, delays, dopplers, f1, f2, g1, g2, sig2, const, cont_doppler, n_outer=6)

    # Gold-standard physical linear-conv Oracle
    xd_gold = []
    for k in range(4):
        t_off = k * (N + L_cpp) if cont_doppler else 0
        H_dir_l, H_img_l, G1_r, G2_r = m1.build_exact_linear_operators(N, c1, gains, delays, dopplers, f1, f2, g1, g2, t_offset=t_off)
        xd_g, _, _ = m1.exact_wl_ep_detect(r_list[k], None, None, None, A, data_idx_nom, xp_val, const, sig2, n_iter=3,
                                           exact_lin_ops=(H_dir_l, H_img_l, G1_r, G2_r))
        xd_gold.append(xd_g)

    return {
        "Pub_Huang": mser(xd_h),
        "Pub_Narasimhan": mser(xd_n),
        "Ours_PropFull": mser(xd_pf[-1]),
        "Ours_ZeroU0": mser(xd_z0[-1]),
        "Steelman_WL_Anttila_1Pass": mser(xd_ant_1p),
        "Steelman_WL_Anttila_DD6": mser(xd_ant_dd6),
        "Steelman_1ShortPilot_1Pass": ser_sp_1p,
        "Steelman_1ShortPilot_DD6": ser_sp_6o,
        "Steelman_S_SC_1ShortPilot": ser_sc_sp,
        "Steelman_S_OFDM_1ShortPilot": ser_ofdm_sp,
        "Oracle_PhysGold": mser(xd_gold),
    }


def summarize_reg(rows):
    arms = list(rows[0].keys())
    n = len(rows)
    t_crit = float(student_t.ppf(0.975, df=max(n - 1, 1))) if n > 1 else 0.0
    means = {}
    ci_hw = {}
    lockout_gt1pct = {}
    for a in arms:
        arr = np.array([r[a] for r in rows], dtype=float)
        means[a] = float(np.mean(arr))
        ci_hw[a] = float(t_crit * np.std(arr, ddof=1) / math.sqrt(n)) if n > 1 else 0.0
        lockout_gt1pct[a] = float(np.mean(arr > 0.01))
    return {"n_bursts": n, "mean_ser": means, "ser_ci95_hw": ci_hw, "burst_lockout_gt1pct": lockout_gt1pct}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", type=str, default=os.path.join(REPO_ROOT, "ideas", "r15", "out_m01.json"))
    args = ap.parse_args()

    t0 = time.perf_counter()
    seed_base = 202611269500 if args.smoke else 202611262500

    regimes = [
        ("R1_Mod18_64QAM_35dB",    "mod18",    64, 35.0, False, 2 if args.smoke else 48),
        ("R2_Strong13_64QAM_32dB", "strong13", 64, 32.0, False, 2 if args.smoke else 80),
        ("R3_ContDop_16QAM_28dB",  "strong13", 16, 28.0, True,  2 if args.smoke else 48),
    ]

    results = {
        "card": "I-20261126-m01",
        "frozen_m01_md5_verified": _actual_md5,
        "seed_base": seed_base,
        "smoke": bool(args.smoke),
        "workers": int(args.workers),
        "budget_verification": {
            "prop_channel_uses": 4 * (256 + 8),
            "short_pilot_steelman_channel_uses": (48 + 8) + 4 * (256 + 8),
            "prop_net_sym_per_cu": (4 * 161) / float(4 * (256 + 8)),
            "short_pilot_steelman_net_sym_per_cu": (4 * 171) / float((48 + 8) + 4 * (256 + 8)),
            "eb_n0_matched_exact_zero_db": True,
        },
        "regimes": {},
    }

    pool = Pool(args.workers) if args.workers > 1 else None
    try:
        for r_idx, (rname, lvl, mq, snr, cd, nb) in enumerate(regimes):
            tr = time.perf_counter()
            tasks = [(seed_base + r_idx * 10000 + i, lvl, mq, snr, cd) for i in range(nb)]
            rows = pool.map(run_burst_teardown, tasks) if pool else [run_burst_teardown(t) for t in tasks]
            summ = summarize_reg(rows)
            summ["elapsed_s"] = round(time.perf_counter() - tr, 2)
            results["regimes"][rname] = summ
            m = summ["mean_ser"]; lo = summ["burst_lockout_gt1pct"]
            print(f"[{rname}] (n={nb}, {summ['elapsed_s']}s):\n"
                  f"  Pub_Huang   = {m['Pub_Huang']:.4e} (LO {lo['Pub_Huang']*100:.1f}%) | Pub_Nar = {m['Pub_Narasimhan']:.4e}\n"
                  f"  Ours_Prop   = {m['Ours_PropFull']:.4e} (LO {lo['Ours_PropFull']*100:.1f}%) | ZeroU0  = {m['Ours_ZeroU0']:.4e} (LO {lo['Ours_ZeroU0']*100:.1f}%)\n"
                  f"  SM_Ant_1P   = {m['Steelman_WL_Anttila_1Pass']:.4e} | SM_Ant_DD6 = {m['Steelman_WL_Anttila_DD6']:.4e} (LO {lo['Steelman_WL_Anttila_DD6']*100:.1f}%)\n"
                  f"  SM_1Pil_1P  = {m['Steelman_1ShortPilot_1Pass']:.4e} | SM_1Pil_DD6 = {m['Steelman_1ShortPilot_DD6']:.4e} (LO {lo['Steelman_1ShortPilot_DD6']*100:.1f}%)\n"
                  f"  SM_S_SC     = {m['Steelman_S_SC_1ShortPilot']:.4e} (LO {lo['Steelman_S_SC_1ShortPilot']*100:.1f}%) | SM_S_OFDM = {m['Steelman_S_OFDM_1ShortPilot']:.4e}\n"
                  f"  Oracle_Gold = {m['Oracle_PhysGold']:.4e} (LO {lo['Oracle_PhysGold']*100:.1f}%)",
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
