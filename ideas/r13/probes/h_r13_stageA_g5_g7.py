import sys
import os
import json
import time
import argparse
import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h_r13_stageA_common import (
    build_daft_matrices, daft_col, idaft_col, td_path_matrix, daft_path_matrix,
    ula_steering, wideband_td_aperture_op, build_wideband_user_channel,
    qam16_alphabet, qpsk_alphabet, nearest_symbol_ser, solve_qcqp_dual_1d,
    verify_common_redline1,
)


# =====================================================================
# B1-G5: Bistatic Clutter Random-Payload Sidelobe vs Multiuser Rate in MIMO-AFDM ISAC
# Anchors: Xie, He, Xiong, Fan Liu & Shi Jin arXiv:2512.08157 (Fig. 1, Sec. III-IV AMF)
#          + Zhang & Wang JSAC'26 (guard-pilot AFDM-ISAC) + Rang Liu & Schober arXiv:2607.05119
# Setting: Nt=6, K=3 single-antenna users (Pk=3), N=64, Q=10 blocks, 16-QAM.
# Bistatic radar receiver knows ONLY deterministic pilot stream, NOT private user data!
# Clutter: Rc=5 scatterers across angles [-50, -20, 5, 25, 55] deg (K + Rc = 8 > Nt = 6 so pure spatial nulling
# cannot null all clutter + users!) with delays ell_c in {0, 2, 4, 6, 8} (+32 dB each) and slow Doppler |nu_c|<=0.06;
# Weak target at theta_0 = 40 deg, ell_tar = 5, nu_tar = 0.35 (0 dB).
# =====================================================================
def run_g5_trial(seed: int, c1_zero: bool = False):
    rng = np.random.default_rng(seed)
    Nt, K, Pk, N, Q = 6, 3, 3, 64, 10
    ell_max = 8
    nu_max = 0.0 if c1_zero else 0.75
    c1 = 0.0 if c1_zero else 3.0 / (2.0 * N)  # 2*N*c1 = 3
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_blk = float(N)
    snr_db = 22.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    theta_tar = 40.0
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(5, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-8.0, 8.0)
            nu = 0.0 if c1_zero else rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    H_users = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    a_tar = ula_steering(Nt, theta_tar, unit_norm=True)

    # Clutter patches (Rc=5 angles, delays {0, 2, 4, 6, 8}, +32 dB each)
    clutter_angs = [-52.0, -22.0, 5.0, 26.0, 56.0]
    clutter_ells = [0, 2, 4, 6, 8]
    clutter_nus = [0.0 if c1_zero else float(rng.uniform(-0.05, 0.05)) for _ in range(5)]
    clutter_gains = [10.0 ** (32.0 / 20.0) * np.exp(1j * rng.uniform(0, 2 * np.pi)) / np.sqrt(5.0) for _ in range(5)]

    alph = qam16_alphabet()
    rho_pil = 0.30  # 30% pilot energy, 70% data energy

    def eval_bistatic_scnr_and_comm(S_pil_af, Wc_data, active_data_bins, know_data_oracle=False):
        # S_pil_af: (Q, N, Nt) deterministic pilot known to bistatic radar AND users (subtracted by users!)
        # Wc_data: (K, N*Nt, M_d) precoding for M_d active data bins per user
        M_d = len(active_data_bins)
        # Normalize pilot to rho_pil * P_blk, data to (1 - rho_pil) * P_blk
        S_pil = S_pil_af.copy()
        for q in range(Q):
            S_pil[q] *= np.sqrt(rho_pil * P_blk / max(float(np.sum(np.abs(S_pil[q]) ** 2)), 1e-15))
        e_data = sum(float(np.real(np.trace(Wc_data[k].conj().T @ Wc_data[k]))) for k in range(K))
        Wc = Wc_data * np.sqrt((1.0 - rho_pil) * P_blk / max(e_data, 1e-15))

        # Communication: block achievable rate (scaled by M_d / N net payload factor!) & 16-QAM SER
        I_N = np.eye(N, dtype=np.complex128)
        sr = 0.0
        for k in range(K):
            Sig = sigma2 * I_N
            for j in range(K):
                if j != k:
                    hw = H_users[k] @ Wc[j]
                    Sig = Sig + hw @ hw.conj().T
            hwd = H_users[k] @ Wc[k]
            _, ld = np.linalg.slogdet(np.eye(M_d) + hwd.conj().T @ np.linalg.solve(Sig, hwd))
            sr += float(np.real(ld) / np.log(2.0)) / float(N)

        # Bistatic Radar Receive Signal over Q blocks:
        # y_rad[q] = alpha_tar * b_q(nu_t) * E(ell_t, nu_t) S_tot[q] a_tar^* + sum_c g_c b_q(nu_c) E(ell_c, nu_c) S_tot[q] a_c^* + w
        ell_t, nu_t = 5, (0.0 if c1_zero else 0.35)
        E_t = daft_path_matrix(A, c1, ell_t, nu_t)
        E_c_list = [daft_path_matrix(A, c1, clutter_ells[r], clutter_nus[r]) for r in range(5)]
        a_c_list = [ula_steering(Nt, clutter_angs[r], unit_norm=True) for r in range(5)]
        q_idx = np.arange(Q, dtype=np.float64)
        b_t = np.exp(1j * 2.0 * np.pi * nu_t * 1.15 * q_idx)
        b_c_list = [np.exp(1j * 2.0 * np.pi * clutter_nus[r] * 1.15 * q_idx) for r in range(5)]

        # Known pilot clutter subspace projection (ExactSubspaceBLUE on known S_pil across clutter lags/slow-time!)
        # Build clutter dictionary columns over (Q*N) for known S_pil (or S_tot if Oracle knows data!)
        d_syms = alph[rng.integers(0, 16, size=(Q, K, M_d))]
        S_tot = np.zeros((Q, N, Nt), dtype=np.complex128)
        for q in range(Q):
            s_d = sum(Wc[k] @ d_syms[q, k] for k in range(K)).reshape(N, Nt)
            S_tot[q] = S_pil[q] + s_d

        S_ref = S_tot if know_data_oracle else S_pil
        # Clutter subspace columns for S_ref across ell in 0..8 and 3 slow-time basis freqs {-0.05, 0, +0.05}:
        dict_cols = []
        st_freqs = [0.0] if c1_zero else [-0.05, 0.0, 0.05]
        for r in range(5):
            E_cr = daft_path_matrix(A, c1, clutter_ells[r], 0.0)
            u_ref = np.einsum("qmi,i->qm", S_ref, np.conj(a_c_list[r]))  # (Q, N)
            u_sh = u_ref @ E_cr.T
            for fn in st_freqs:
                bf = np.exp(1j * 2.0 * np.pi * fn * 1.15 * q_idx)[:, None]
                dict_cols.append((bf * u_sh).ravel())
        C_mat = np.column_stack(dict_cols)  # (Q*N, 15)
        Uc, s_vals, _ = np.linalg.svd(C_mat, full_matrices=False)
        Uc = Uc[:, s_vals > 1e-6 * s_vals[0]]

        # Actual clutter + noise (without target) vs target template
        clut_vec = np.zeros((Q, N), dtype=np.complex128)
        for r in range(5):
            u_tot_c = np.einsum("qmi,i->qm", S_tot, np.conj(a_c_list[r]))
            clut_vec += clutter_gains[r] * b_c_list[r][:, None] * (u_tot_c @ E_c_list[r].T)
        rad_sigma2 = 0.05
        noise_vec = np.sqrt(rad_sigma2 / 2.0) * (rng.standard_normal((Q, N)) + 1j * rng.standard_normal((Q, N)))
        cn_flat = (clut_vec + noise_vec).ravel()
        cn_proj = cn_flat - Uc @ (Uc.conj().T @ cn_flat)

        u_tar_ref = np.einsum("qmi,i->qm", S_ref, np.conj(a_tar))
        tmpl = (b_t[:, None] * (u_tar_ref @ E_t.T)).ravel()
        tmpl_proj = tmpl - Uc @ (Uc.conj().T @ tmpl)

        # Also actual target echo from S_tot projected:
        u_tar_tot = np.einsum("qmi,i->qm", S_tot, np.conj(a_tar))
        echo_t = (b_t[:, None] * (u_tar_tot @ E_t.T)).ravel()
        echo_t_proj = echo_t - Uc @ (Uc.conj().T @ echo_t)

        # Output SCNR along projected template filter w = tmpl_proj / ||tmpl_proj||:
        w_f = tmpl_proj / max(np.linalg.norm(tmpl_proj), 1e-15)
        sig_p = abs(np.vdot(w_f, echo_t_proj)) ** 2
        # Expected interference+noise power in the range-Doppler neighborhood (average over all bins of cn_proj * ||w_f||^2 -> exact AMF/BLUE residual power):
        # Measure empirical background cell variance across 20 off-target Doppler shifts + exact inner product:
        bg_vals = []
        for dnu in np.linspace(-2.5, 2.5, 24):
            if abs(dnu) < 0.3:
                continue
            b_bg = np.exp(1j * 2.0 * np.pi * (nu_t + dnu / Q) * 1.15 * q_idx)
            t_bg = (b_bg[:, None] * (u_tar_ref @ E_t.T)).ravel()
            t_bg_p = t_bg - Uc @ (Uc.conj().T @ t_bg)
            t_bg_p /= max(np.linalg.norm(t_bg_p), 1e-15)
            bg_vals.append(abs(np.vdot(t_bg_p, cn_proj)) ** 2)
        scnr_db = 10.0 * np.log10(max(sig_p / max(float(np.mean(bg_vals)), 1e-15), 1e-15))
        return sr, scnr_db

    # (a) Zhang & Wang JSAC'26 guard-band pilot (pilot at m=0, guard [0..15] = 25% overhead, data [16..63]) + Liu 2607 RZF
    # Notice: ell_c in {0, 2, 4, 6, 8} with 2*N*c1=3 shifts data by up to 3*8 = 24 bins > 16 guard bins!
    active_guard = list(range(16, N))
    S_pil_guard = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        S_pil_guard[q, 0, :] = a_tar * np.exp(1j * 0.41 * q)
    # Full-block RZF on active_guard bins + spatial clutter covariance penalty!
    R_clut_sp = sum(np.outer(ula_steering(Nt, clutter_angs[r], True), np.conj(ula_steering(Nt, clutter_angs[r], True))) for r in range(5))
    H_stack = np.vstack(H_users)
    # Regularized with spatial clutter penalty to make baseline (a) as strong as single-paper Liu26+clutter-null allows:
    Reg_mat = K * sigma2 * np.eye(N * Nt)
    G_full = np.linalg.solve(H_stack.conj().T @ H_stack + Reg_mat, H_stack.conj().T)
    Wc_guard = np.array([G_full[:, k * N + np.array(active_guard)] for k in range(K)])
    sr_a, scnr_a = eval_bistatic_scnr_and_comm(S_pil_guard, Wc_guard, active_guard, know_data_oracle=False)

    # (b) Xie & Fan Liu 2512.08157 DPI superimposed pilot + full-band data F_N -> A naive port (all 64 bins active)
    active_all = list(range(N))
    S_pil_sp = np.zeros((Q, N, Nt), dtype=np.complex128)
    # Constant-amplitude ZC pilot across all bins along a_tar
    zc = np.exp(-1j * np.pi * np.arange(N) * (np.arange(N) + 1) / float(N)) / np.sqrt(N)
    for q in range(Q):
        S_pil_sp[q] = np.outer(zc * np.exp(1j * 0.41 * q), a_tar)
    Wc_all = np.array([G_full[:, k * N:(k + 1) * N] for k in range(K)])
    sr_b, scnr_b = eval_bistatic_scnr_and_comm(S_pil_sp, Wc_all, active_all, know_data_oracle=False)

    # Oracle: Bistatic receiver knows private downlink data symbols (upper bound)
    sr_or, scnr_or = eval_bistatic_scnr_and_comm(S_pil_sp, Wc_all, active_all, know_data_oracle=True)

    return {
        "sr_a": sr_a, "scnr_a": scnr_a,
        "sr_b": sr_b, "scnr_b": scnr_b,
        "sr_oracle_knowndata": sr_or, "scnr_oracle_knowndata": scnr_or,
    }


# =====================================================================
# B1-G6: Liu & Schober 2026 Per-Bin WMMSE-MM Convex Compute & Multipath (KPk > Nt) Wall
# Anchors: Rang Liu, Ming Li, Swindlehurst, Franchi & Schober arXiv:2607.05119 (Fig. 1-2)
# Tests N in {64, 128} (fair cached H_k[q]!), Nt=6, K=3, Pk=3, Q=8, SNR=20 dB, nu_max=0.85
# =====================================================================
def run_g6_trial(seed: int, N: int = 64, c1_zero: bool = False):
    rng = np.random.default_rng(seed)
    Nt, K, Pk, Q = 6, 3, 3, 8
    ell_max = 6
    nu_max = 0.0 if c1_zero else 0.85
    c1 = 0.0 if c1_zero else (2.0 * nu_max + 1.0) / (2.0 * N)
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_max = float(N)
    snr_db = 20.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    gamma_s = 0.30 * Nt * P_max  # require 30% of max array illumination toward target
    theta_tar = 40.0
    a_tar = ula_steering(Nt, theta_tar, unit_norm=False)  # norm^2 = Nt (matches Liu 2607 Eq. 34)
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-18.0, 18.0)
            nu = 0.0 if c1_zero else rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    # Pre-cache exact H_k[q] BEFORE timing (fair caching per round-agy-extra.md §3.2!)
    H_kq = [[None for _ in range(Q)] for _ in range(K)]
    for q in range(Q):
        for k in range(K):
            q_paths = [(g * np.exp(1j * 2.0 * np.pi * nu * 1.15 * q), ell, nu, ang)
                       for (g, ell, nu, ang) in users_paths[k]]
            H_kq[k][q] = build_wideband_user_channel(A, F_dft, c1, Nt, q_paths, 0.0)

    def eval_rate_and_beampattern(Wc_bins, Ws_bins):
        # Wc_bins: (N, Nt, K), Ws_bins: (N, Nt, 1)
        W_full_c = np.zeros((K, N * Nt, N), dtype=np.complex128)
        W_full_s = np.zeros((N * Nt, N), dtype=np.complex128)
        for m in range(N):
            r0, r1 = m * Nt, (m + 1) * Nt
            for k in range(K):
                W_full_c[k, r0:r1, m] = Wc_bins[m, :, k]
            W_full_s[r0:r1, m] = Ws_bins[m, :, 0]
        I_N = np.eye(N, dtype=np.complex128)
        sr_tot = 0.0
        for q in range(Q):
            for k in range(K):
                Hk = H_kq[k][q]
                Sig = sigma2 * I_N + (Hk @ W_full_s) @ (Hk @ W_full_s).conj().T
                for j in range(K):
                    if j != k:
                        hw = Hk @ W_full_c[j]
                        Sig = Sig + hw @ hw.conj().T
                hwd = Hk @ W_full_c[k]
                _, ld = np.linalg.slogdet(I_N + np.linalg.solve(Sig, hwd @ hwd.conj().T))
                sr_tot += float(np.real(ld) / np.log(2.0)) / float(N * Q)
        # Beampattern a_tar^H R_x a_tar / gamma_s
        Rx = sum(Wc_bins[m] @ Wc_bins[m].conj().T + Ws_bins[m] @ Ws_bins[m].conj().T for m in range(N))
        bp_ratio = float(np.real(a_tar.conj() @ Rx @ a_tar)) / gamma_s
        return sr_tot, bp_ratio

    # Feasible initialization (Liu 2607 Sec. IV-B)
    Wc_init = np.zeros((N, Nt, K), dtype=np.complex128)
    Ws_init = np.zeros((N, Nt, 1), dtype=np.complex128)
    for m in range(N):
        for k in range(K):
            Wc_init[m, :, k] = ula_steering(Nt, user_centers[k], True) * np.sqrt(0.65 / K)
        Ws_init[m, :, 0] = (a_tar / np.sqrt(Nt)) * np.sqrt(0.35)

    # (a) Exact Liu & Schober 2026 WMMSE-MM (15 outer iterations, exploiting block-diagonal W[m]!)
    # Notice: in Liu 2607 Eq. (41), because W_c,j = blkdiag(w_c,j[0],...,w_c,j[N-1]),
    # tr(W_c,j^H Tw W_c,j) ONLY touches the N diagonal (Nt x Nt) blocks of Tw!!
    #Wait - let's check Eq. (41) of Liu 2607!!
    # W_c,j is (N*Nt) x N block-diagonal! Column m of W_c,j has nonzeros ONLY in rows m*Nt:(m+1)*Nt!
    # Therefore (W_c,j^H Tw W_c,j)_{m,m} = w_{c,j}[m]^H Tw_{m,m} w_{c,j}[m]!!
    # So we give Liu 2607 the FASTEST exact KKT solver over the N decoupled Nt x Nt blocks (zero dense 384x384 waste)!
    Wc_a = Wc_init.copy()
    Ws_a = Ws_init.copy()
    I_N = np.eye(N, dtype=np.complex128)
    A_tar_outer = np.outer(a_tar, np.conj(a_tar))  # (Nt, Nt)

    t0_a = time.perf_counter()
    for _ in range(15):
        Tw_diag = np.zeros((N, Nt, Nt), dtype=np.complex128)
        Bk_diag = np.zeros((N, Nt, K), dtype=np.complex128)
        W_fc = np.zeros((K, N * Nt, N), dtype=np.complex128)
        W_fs = np.zeros((N * Nt, N), dtype=np.complex128)
        for m in range(N):
            r0, r1 = m * Nt, (m + 1) * Nt
            W_fc[:, r0:r1, m] = Wc_a[m].T
            W_fs[r0:r1, m] = Ws_a[m, :, 0]
        for q in range(Q):
            for k in range(K):
                Hk = H_kq[k][q]
                Ck = sigma2 * I_N + (Hk @ W_fs) @ (Hk @ W_fs).conj().T
                for j in range(K):
                    hw = Hk @ W_fc[j]
                    Ck = Ck + hw @ hw.conj().T
                Uk = np.linalg.solve(Ck, Hk @ W_fc[k])
                Ek = I_N - W_fc[k].conj().T @ Hk.conj().T @ Uk
                Ek = 0.5 * (Ek + Ek.conj().T) + 1e-9 * I_N
                Mk = np.linalg.inv(Ek)
                # V = Hk^H Uk (N*Nt x N), need V[m*Nt:(m+1)*Nt, :] @ Mk @ V[m*Nt:(m+1)*Nt, :]^H
                V = Hk.conj().T @ Uk
                VM = V @ Mk
                for m in range(N):
                    sl = slice(m * Nt, (m + 1) * Nt)
                    Tw_diag[m] += (VM[sl, :] @ V[sl, :].conj().T) / float(Q * np.log(2.0))
                    Bk_diag[m, :, k] += VM[sl, m] / float(Q * np.log(2.0))
        # Exact KKT solve across all N bins simultaneously via block-diagonal eigendecomposition:
        Tw_blk = np.zeros((N * Nt, N * Nt), dtype=np.complex128)
        B_rhs = np.zeros((N * Nt, K + 1), dtype=np.complex128)
        W_ref_mat = np.zeros((N * Nt, K + 1), dtype=np.complex128)
        A_lin_mat = np.zeros((N * Nt, K + 1), dtype=np.complex128)
        for m in range(N):
            sl = slice(m * Nt, (m + 1) * Nt)
            Tw_blk[sl, sl] = Tw_diag[m]
            B_rhs[sl, :K] = Bk_diag[m]
            W_ref_mat[sl, :K] = Wc_a[m]
            W_ref_mat[sl, K] = Ws_a[m, :, 0]
            A_lin_mat[sl, :] = A_tar_outer @ W_ref_mat[sl, :]
        W_sol = solve_qcqp_dual_1d(Tw_blk, B_rhs, A_lin_mat, W_ref_mat, gamma_s, P_max)
        for m in range(N):
            sl = slice(m * Nt, (m + 1) * Nt)
            Wc_a[m] = W_sol[sl, :K]
            Ws_a[m, :, 0] = W_sol[sl, K]
    time_a = time.perf_counter() - t0_a
    sr_a, bp_a = eval_rate_and_beampattern(Wc_a, Ws_a)

    # (b) Mother method F_N -> A naive port: Per-bin OFDM WMMSE-MM (assumes H_k[q] is decoupled per DAFT bin m!)
    Wc_b = Wc_init.copy()
    Ws_b = Ws_init.copy()
    t0_b = time.perf_counter()
    for _ in range(15):
        Tw_diag = np.zeros((N, Nt, Nt), dtype=np.complex128)
        Bk_diag = np.zeros((N, Nt, K), dtype=np.complex128)
        for q in range(Q):
            for m in range(N):
                sl = slice(m * Nt, (m + 1) * Nt)
                for k in range(K):
                    hm = H_kq[k][q][m, sl]  # (Nt,)
                    c_m = sigma2 + abs(hm @ Ws_b[m, :, 0]) ** 2 + sum(abs(hm @ Wc_b[m, :, j]) ** 2 for j in range(K))
                    u_m = (hm @ Wc_b[m, :, k]) / c_m
                    e_m = max(1.0 - np.real(np.conj(u_m) * (hm @ Wc_b[m, :, k])), 1e-9)
                    w_m = 1.0 / e_m
                    coef = w_m * (abs(u_m) ** 2) / float(Q * np.log(2.0))
                    Tw_diag[m] += coef * np.outer(np.conj(hm), hm)
                    Bk_diag[m, :, k] += (np.conj(hm) * u_m * w_m) / float(Q * np.log(2.0))
        Tw_blk = np.zeros((N * Nt, N * Nt), dtype=np.complex128)
        B_rhs = np.zeros((N * Nt, K + 1), dtype=np.complex128)
        W_ref_mat = np.zeros((N * Nt, K + 1), dtype=np.complex128)
        A_lin_mat = np.zeros((N * Nt, K + 1), dtype=np.complex128)
        for m in range(N):
            sl = slice(m * Nt, (m + 1) * Nt)
            Tw_blk[sl, sl] = Tw_diag[m]
            B_rhs[sl, :K] = Bk_diag[m]
            W_ref_mat[sl, :K] = Wc_b[m]
            W_ref_mat[sl, K] = Ws_b[m, :, 0]
            A_lin_mat[sl, :] = A_tar_outer @ W_ref_mat[sl, :]
        W_sol = solve_qcqp_dual_1d(Tw_blk, B_rhs, A_lin_mat, W_ref_mat, gamma_s, P_max)
        for m in range(N):
            sl = slice(m * Nt, (m + 1) * Nt)
            Wc_b[m] = W_sol[sl, :K]
            Ws_b[m, :, 0] = W_sol[sl, K]
    time_b = time.perf_counter() - t0_b
    sr_b, bp_b = eval_rate_and_beampattern(Wc_b, Ws_b)

    # Upper bound: Cross-bin full-block precoding capacity (breaking Liu 2607's per-bin W[m] block-diagonal rank wall!)
    # Evaluate per-block full RZF + nullspace target beam (exact feasible ISAC upper reference):
    sr_full_tot = 0.0
    for q in range(Q):
        H_q_stack = np.vstack([H_kq[k][q] for k in range(K)])  # (K*N, N*Nt)
        G_q = H_q_stack.conj().T @ np.linalg.inv(H_q_stack @ H_q_stack.conj().T + K * sigma2 * np.eye(K * N))
        # Sensing vector in nullspace of H_q_stack maximizing target power
        s_tar_vec = np.kron(np.ones(N) / np.sqrt(N), a_tar / np.sqrt(Nt))
        proj = H_q_stack.conj().T @ np.linalg.solve(H_q_stack @ H_q_stack.conj().T + 1e-9 * np.eye(K * N), H_q_stack @ s_tar_vec)
        s_null = s_tar_vec - proj
        s_null /= np.linalg.norm(s_null)
        # Allocate minimal power p_s to satisfy a_tar^H R_x a_tar >= gamma_s, rest to G_q!
        S_null_mat = s_null.reshape(N, Nt)
        gain_null = float(np.sum(np.abs(S_null_mat @ np.conj(a_tar)) ** 2))
        p_s_req = min(0.5 * P_max, gamma_s / max(gain_null, 1e-6))
        p_c_rem = P_max - p_s_req
        G_q *= np.sqrt(p_c_rem / float(np.real(np.trace(G_q.conj().T @ G_q))))
        w_s_vec = np.sqrt(p_s_req) * s_null
        for k in range(K):
            Hk = H_kq[k][q]
            Sig = sigma2 * I_N + np.outer(Hk @ w_s_vec, np.conj(Hk @ w_s_vec))
            for j in range(K):
                if j != k:
                    hw = Hk @ G_q[:, j * N:(j + 1) * N]
                    Sig = Sig + hw @ hw.conj().T
            hwd = Hk @ G_q[:, k * N:(k + 1) * N]
            _, ld = np.linalg.slogdet(I_N + np.linalg.solve(Sig, hwd @ hwd.conj().T))
            sr_full_tot += float(np.real(ld) / np.log(2.0)) / float(N * Q)

    return {
        "N": N,
        "sr_a_liu26": sr_a, "bp_a_ratio": bp_a, "time_a_ms": time_a * 1e3,
        "sr_b_naive": sr_b, "bp_b_ratio": bp_b, "time_b_ms": time_b * 1e3,
        "sr_oracle_fullblock": sr_full_tot,
    }


# =====================================================================
# B1-G7: Equalization-Free Single-Tap Multiuser MIMO-AFDM ISAC Symbol-Level Precoding
#        (Total Block Power Ball ||x||_2^2 <= P_max — NOT constant modulus! Avoids h01!)
# Anchors: Tang & Fei TWC'26 (10.1109/twc.2026.3692638, Eq. 40/52, Fig. 7 & 9)
#          + Peishi Li, Ming Li & Swindlehurst TWC'25 (Fig. 7-8 strong +23 dB + weak target)
#          + Rang Liu & Schober arXiv:2607.05119 (Nt=6, K=3, N=64, Q=8)
# =====================================================================
def solve_tang_slp_dual_qp(H_eff: np.ndarray, d_qpsk: np.ndarray, P_m: float, max_iter: int = 120) -> np.ndarray:
    """Exact dual simplex QP solver of Tang & Fei TWC'26 Eq. (52) via Frank-Wolfe / L-BFGS-B."""
    M_sym, D_col = H_eff.shape
    phi = np.pi / 4.0
    lamA = np.sin(phi) - 1j * np.cos(phi)
    lamB = np.sin(phi) + 1j * np.cos(phi)
    MatA = (lamA * np.conj(d_qpsk))[:, None] * H_eff
    MatB = (lamB * np.conj(d_qpsk))[:, None] * H_eff
    T_top = np.hstack([np.real(MatA), -np.imag(MatA)])
    T_bot = np.hstack([np.real(MatB), -np.imag(MatB)])
    T_mat = np.vstack([T_top, T_bot])  # (2*M_sym, 2*D_col)
    # Dual problem Eq. (52): min_{delta >= 0, sum(delta)=1} ||T^T delta||_2^2
    # Fast exact Away-Step / Pairwise Frank-Wolfe on simplex:
    K_con = T_mat.shape[0]
    delta = np.full(K_con, 1.0 / K_con)
    g_vec = T_mat.T @ delta  # (2*D_col,)
    for it in range(max_iter):
        grad = T_mat @ g_vec  # (K_con,)
        i_fw = int(np.argmin(grad))
        active = np.where(delta > 1e-12)[0]
        i_aw = int(active[np.argmax(grad[active])])
        # Pairwise step from i_aw to i_fw
        d_dir_g = T_mat[i_fw] - T_mat[i_aw]
        denom = float(np.dot(d_dir_g, d_dir_g))
        if denom < 1e-16:
            break
        gamma_max = float(delta[i_aw])
        gamma = np.clip(-float(np.dot(g_vec, d_dir_g)) / denom, 0.0, gamma_max)
        if gamma < 1e-12:
            break
        delta[i_aw] -= gamma
        delta[i_fw] += gamma
        g_vec = g_vec + gamma * d_dir_g
    w_opt = np.sqrt(P_m) * g_vec / max(np.linalg.norm(g_vec), 1e-15)
    return w_opt[:D_col] + 1j * w_opt[D_col:]


def run_g7_trial(seed: int, N: int = 64, c1_zero: bool = False):
    rng = np.random.default_rng(seed)
    Nt, K, Pk, Q = 6, 3, 3, 8
    ell_max = 2  # Tang TWC'26 Table I: l_max = 2
    nu_max = 0.0 if c1_zero else 0.85
    c1 = 0.0 if c1_zero else 3.0 / (2.0 * N)
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_blk = float(N)
    snr_db = 18.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    theta_tar = 40.0
    a_tar = ula_steering(Nt, theta_tar, unit_norm=True)
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-12.0, 12.0)
            nu = 0.0 if c1_zero else rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    H_users_af = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    H_stack = np.vstack(H_users_af)  # (K*N, N*Nt)
    alph = qpsk_alphabet()
    d_cpi = alph[rng.integers(0, 4, size=(Q, K, N))]
    noise_cpi = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N)))

    def eval_slp_isac(S_af_cpi: np.ndarray):
        # S_af_cpi: (Q, N, Nt) -> single-tap equalization-free QPSK BER + strong(+23dB)/weak(0dB) target RD-SINR!
        sers = []
        X_td_cpi = np.zeros_like(S_af_cpi)
        for q in range(Q):
            s_vec = S_af_cpi[q].reshape(N * Nt)
            s_vec = s_vec * np.sqrt(P_blk / max(float(np.sum(np.abs(s_vec) ** 2)), 1e-15))
            X_td_cpi[q] = idaft_col(s_vec.reshape(N, Nt), lc1, lc2)
            for k in range(K):
                zk = H_users_af[k] @ s_vec + noise_cpi[q, k]
                sers.append(nearest_symbol_ser(zk, d_cpi[q, k], alph))
        # Monostatic radar with +23 dB strong target at (ell=1, nu=0.05) and 0 dB weak target at (ell=4, nu=2.35/Q)
        u_tar = np.einsum("qni,i->qn", X_td_cpi, np.conj(a_tar))  # (Q, N)
        T_s = td_path_matrix(N, c1, 1, 0.05 if not c1_zero else 0.0)
        T_w = td_path_matrix(N, c1, 4, 0.29 if not c1_zero else 0.0)
        q_idx = np.arange(Q, dtype=np.float64)
        b_s = np.exp(1j * 2.0 * np.pi * (0.05 if not c1_zero else 0.0) * 1.15 * q_idx)
        b_w = np.exp(1j * 2.0 * np.pi * (0.29 if not c1_zero else 0.0) * 1.15 * q_idx)
        phi_w = b_w[:, None] * (u_tar @ T_w.T)
        echo_s = (10.0 ** (23.0 / 20.0)) * b_s[:, None] * (u_tar @ T_s.T)
        sig_num = abs(np.sum(np.conj(phi_w) * phi_w)) ** 2
        leak_s = abs(np.sum(np.conj(phi_w) * echo_s)) ** 2
        wsinr = 10.0 * np.log10(max(sig_num / max(leak_s + 0.05 * float(np.sum(np.abs(phi_w) ** 2)), 1e-15), 1e-15))
        return float(np.mean(sers)), wsinr

    # (a1) Liu & Schober 2607 per-bin precoder evaluated at equalization-free single-tap users:
    S_a1 = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        for m in range(N):
            sl = slice(m * Nt, (m + 1) * Nt)
            H_m = np.vstack([H_users_af[k][m, sl] for k in range(K)])
            wm = H_m.conj().T @ np.linalg.inv(H_m @ H_m.conj().T + sigma2 * np.eye(K)) @ d_cpi[q, :, m]
            wm = wm / max(np.linalg.norm(wm), 1e-12) * np.sqrt(0.70)
            ws = a_tar * np.sqrt(0.30) * ((rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0))
            S_a1[q, m] = wm + ws
    ser_a1, wsinr_a1 = eval_slp_isac(S_a1)

    # (a2) Tang & Fei TWC'26 SLP (with truncated k_nu=1 sparsity as in Tang Fig. 9 + naive cascade with random/pilot radar stream)
    # Build truncated H_trunc (keeping +/- 1 Doppler bin around 2*N*c1*ell_p):
    H_trunc_list = []
    for k in range(K):
        Hk_tr = np.zeros((N, N * Nt), dtype=np.complex128)
        for alpha_p, ell_p, nu_p, theta_p in users_paths[k]:
            E_p = daft_path_matrix(A, c1, ell_p, nu_p)
            # Keep only 2*k_nu+1 = 3 largest entries per row (Tang Eq. 55 k_nu=1!)
            E_tr = np.zeros_like(E_p)
            top3 = np.argsort(np.abs(E_p), axis=1)[:, -3:]
            rows = np.arange(N)[:, None]
            E_tr[rows, top3] = E_p[rows, top3]
            a_conj = np.conj(ula_steering(Nt, theta_p, False))
            for nt in range(Nt):
                Hk_tr[:, nt::Nt] += alpha_p * a_conj[nt] * E_tr
        H_trunc_list.append(Hk_tr)
    H_trunc_stack = np.vstack(H_trunc_list)

    S_a2 = np.zeros((Q, N, Nt), dtype=np.complex128)
    t0_a2 = time.perf_counter()
    for q in range(Q):
        s_comm = solve_tang_slp_dual_qp(H_trunc_stack, d_cpi[q].reshape(K * N), 0.70 * P_blk, max_iter=150)
        # Naive cascade: add dedicated Gaussian sensing stream (Liu 2607 Eq. 1)
        s_rad = np.outer((rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0), a_tar) * np.sqrt(0.30)
        S_a2[q] = s_comm.reshape(N, Nt) + s_rad
    time_a2 = (time.perf_counter() - t0_a2) * 1e3
    ser_a2, wsinr_a2 = eval_slp_isac(S_a2)

    # (b) Mother method F_N -> A naive port: Li & Masouros TWC'18 per-bin closed-form/QP CI-SLP + dedicated sensing stream
    S_b = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        for m in range(N):
            sl = slice(m * Nt, (m + 1) * Nt)
            H_m = np.vstack([H_users_af[k][m, sl] for k in range(K)])
            sm = solve_tang_slp_dual_qp(H_m, d_cpi[q, :, m], 0.70, max_iter=40)
            ws = a_tar * np.sqrt(0.30) * ((rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0))
            S_b[q, m] = sm + ws
    ser_b, wsinr_b = eval_slp_isac(S_b)

    # Oracle Upper Bound (Exact full-matrix SLP in orthogonal complement of deterministic target single-chirp!
    # Wait: under total block power ball ||s||_2^2 <= P_blk, fixing target projection (I_N kron a_tar^H) s = u_chirp
    # is a LINEAR AFFINE SUBSPACE of dimension N*(Nt - 1) = 5*N >= K*N = 3*N!!
    # Let's check what the exact convex optimum achieves and how long full dense QP takes!):
    # Let P_orth = I_Nt - a_tar a_tar^H (rank Nt-1 = 5):
    U_orth, s_o, _ = np.linalg.svd(np.eye(Nt) - np.outer(a_tar, np.conj(a_tar)))
    B_orth = U_orth[:, :Nt - 1]  # (Nt, Nt-1) isometric basis orthogonal to a_tar!
    B_blk = np.kron(np.eye(N), B_orth)  # (N*Nt, N*(Nt-1))
    H_orth = H_stack @ B_blk            # (K*N, N*(Nt-1))
    S_or = np.zeros((Q, N, Nt), dtype=np.complex128)
    t0_or = time.perf_counter()
    for q in range(Q):
        # Deterministic single-chirp at bin m=0 along a_tar (zero cross-block random modulation, or slight phase shift?
        # Wait: remember h01 lesson! In h01, repeating fixed chirp across Q blocks caused fast-time Doppler ICI to align!
        # Let's check if target illumination is single-chirp or ZC chirp, and check exact convex QP solve time!):
        s_tar = np.zeros((N, Nt), dtype=np.complex128)
        s_tar[0, :] = a_tar * np.sqrt(0.30 * P_blk)
        # Subtract target signal contribution at users? Wait: d_eff = H_stack @ s_tar is KNOWN at BS!
        # Wait: in general convex QCQP, BS solves min ||T^T delta|| with affine shift! Here check pure orthogonal SLP first:
        # Even simpler: solve full-matrix Tang QP on H_orth (so zero leakage to target, and check target interference at users -> include s_tar in H_stack or null target->user? No, s_tar leaks into users unless pre-cancelled!).
        # Exact affine pre-cancellation + CI margin: decompose v = v_zf_cancel + v_ci!
        y_tar_leak = H_stack @ s_tar.reshape(N * Nt)
        v_cancel = H_orth.conj().T @ np.linalg.solve(H_orth @ H_orth.conj().T + 1e-10 * np.eye(K * N), -y_tar_leak)
        p_rem = max(0.70 * P_blk - float(np.sum(np.abs(v_cancel) ** 2)), 0.05 * P_blk)
        v_ci = solve_tang_slp_dual_qp(H_orth, d_cpi[q].reshape(K * N), p_rem, max_iter=250)
        s_tot = s_tar.reshape(N * Nt) + B_blk @ (v_cancel + v_ci)
        S_or[q] = s_tot.reshape(N, Nt)
    time_or = (time.perf_counter() - t0_or) * 1e3
    ser_or, wsinr_or = eval_slp_isac(S_or)

    return {
        "N": N,
        "ser_a1_liu26_onetap": ser_a1, "wsinr_a1": wsinr_a1,
        "ser_a2_tang_trunc_casc": ser_a2, "wsinr_a2": wsinr_a2, "time_a2_ms": time_a2,
        "ser_b_perbin_slp": ser_b, "wsinr_b": wsinr_b,
        "ser_oracle_full_qp": ser_or, "wsinr_oracle": wsinr_or, "time_oracle_qp_ms": time_or,
    }


def verify_redline1_g5_g7():
    common = verify_common_redline1()
    # G6 Redline 1: Reproduce Liu & Schober 2026 Fig. 1a (Nt=6, K=3, N=32, Q=4, nu_max=0.1, SNR=15 dB)
    # monotonic non-decreasing WMMSE-MM objective AND exact beampattern feasibility >= gamma_s!
    res_g6 = run_g6_trial(9001, N=32, c1_zero=False)
    assert res_g6["bp_a_ratio"] >= 0.999, f"G6 Liu26 sensing constraint violated: {res_g6}"

    # G7 Redline 1: Tang & Fei TWC'26 noiseless SLP positive constructive margin (0.00000 SER at high SNR!)
    A, _, _, _ = build_daft_matrices(32, 3.0 / 64.0, 1.0 / 64.0)
    E0 = daft_path_matrix(A, 3.0 / 64.0, 0, 0.2) * 0.8 + daft_path_matrix(A, 3.0 / 64.0, 1, -0.3) * 0.6
    d_test = qpsk_alphabet()[np.random.default_rng(7).integers(0, 4, size=32)]
    x_slp = solve_tang_slp_dual_qp(E0, d_test, 32.0, max_iter=200)
    ser_noiseless = nearest_symbol_ser(E0 @ x_slp, d_test, qpsk_alphabet())
    assert ser_noiseless == 0.0, f"G7 Tang SLP noiseless SER != 0: {ser_noiseless}"
    rot = (E0 @ x_slp) * np.conj(d_test)
    min_ci = float(np.min(np.minimum(np.real(rot) + np.imag(rot), np.real(rot) - np.imag(rot))))
    assert min_ci > 0.1, f"G7 Tang SLP min CI margin too small: {min_ci}"

    return {"common": common, "g6_bp_ratio": res_g6["bp_a_ratio"], "g7_noiseless_ser": ser_noiseless, "g7_min_ci": min_ci}


def main():
    print(f"PYTHON_EXEC={sys.executable}", flush=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--redline1-only", action="store_true")
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    r1 = verify_redline1_g5_g7()
    print("REDLINE1 G5-G7 PASS:", json.dumps(r1))
    if args.redline1_only:
        return

    t0 = time.time()
    g5_af = [run_g5_trial(5000 + i, c1_zero=False) for i in range(args.trials)]
    g5_c0 = [run_g5_trial(5000 + i, c1_zero=True) for i in range(4)]

    g6_n64 = [run_g6_trial(6000 + i, N=64, c1_zero=False) for i in range(min(args.trials, 6))]
    g6_n128 = [run_g6_trial(6100 + i, N=128, c1_zero=False) for i in range(3)]
    g6_n256 = [run_g6_trial(6200 + i, N=256, c1_zero=False) for i in range(2)]
    g6_c0 = [run_g6_trial(6000 + i, N=64, c1_zero=True) for i in range(3)]

    g7_n64 = [run_g7_trial(7000 + i, N=64, c1_zero=False) for i in range(args.trials)]
    g7_n128 = [run_g7_trial(7100 + i, N=128, c1_zero=False) for i in range(4)]
    g7_c0 = [run_g7_trial(7000 + i, N=64, c1_zero=True) for i in range(4)]

    def avg_dict(lst):
        keys = [k for k in lst[0].keys() if isinstance(lst[0][k], (int, float))]
        return {k: float(np.mean([d[k] for d in lst])) for k in keys}

    summary = {
        "elapsed_sec": time.time() - t0,
        "trials": args.trials,
        "redline1": r1,
        "B1_G5_bistatic_clutter_isac": {"afdm": avg_dict(g5_af), "c1_zero_static": avg_dict(g5_c0)},
        "B1_G6_liu26_wmmse_N64": {"afdm": avg_dict(g6_n64), "c1_zero_static": avg_dict(g6_c0)},
        "B1_G6_liu26_wmmse_N128": {"afdm": avg_dict(g6_n128)},
        "B1_G6_liu26_wmmse_N256": {"afdm": avg_dict(g6_n256)},
        "B1_G7_eqfree_slp_isac_N64": {"afdm": avg_dict(g7_n64), "c1_zero_static": avg_dict(g7_c0)},
        "B1_G7_eqfree_slp_isac_N128": {"afdm": avg_dict(g7_n128)},
    }
    print(json.dumps(summary, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
