import sys
import os
import json
import time
import argparse
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h_r13_stageA_common import (
    build_daft_matrices, daft_col, idaft_col, td_path_matrix, daft_path_matrix,
    ula_steering, wideband_td_aperture_op, qam16_alphabet, qpsk_alphabet,
    nearest_symbol_ser, solve_qcqp_dual_1d, verify_common_redline1,
)


# =====================================================================
# B1-G1: Wideband Large-Array Hybrid Beamforming ISAC under Beam Squint
# Anchors: Elbir WCL'24 (10.1109/LWC.2024.3489632) + Luo & Gao TWC'26 (10.1109/twc.2026.3651469)
#          + Rang Liu & Schober arXiv:2607.05119
# Physically consistent LEO Ka-band / wideband UWA parameter regime:
# Nt=64, Nrf=6, K=3, Pk=3, N=64, eta_bw=B/fc=0.12 (e.g. Ka/UWA wideband), nu_max=0.65, SNR=20 dB
# =====================================================================
def build_wideband_user_channel(A, F_dft, c1, Nt, paths, eta_bw):
    """
    Exact DAFT-domain channel H_k in C^{N x (N*Nt)} (precoder index ordered m*Nt + nt)
    incorporating physical wideband aperture delay across Nt antennas AND doubly dispersive paths!
    Order of physics:
      S_AF (N x Nt) --A^H--> X_TD (N x Nt) --aperture delay per physical freq--> u_p(n) --T(ell_p, nu_p)--> y_TD --A--> z_AF.
    """
    N = A.shape[0]
    H_k = np.zeros((N, N * Nt), dtype=np.complex128)
    # Precompute aperture spatial-frequency coupling: for each path angle theta_p,
    # u_p_TD = F_dft^H @ sum_{nt} diag(a_wb[nt, :]) (F_dft @ x_td[:, nt])
    for alpha_p, ell_p, nu_p, theta_p in paths:
        E_p = daft_path_matrix(A, c1, ell_p, nu_p)  # (N, N)
        # Wideband array response in DFT domain: (Nt, N)
        A_wb = wideband_td_aperture_op(N, Nt, theta_p, eta_bw)  # conj? Wait: transmit steering a_t^*(theta)
        # At center freq (eta_bw=0), Liu 2607 Eq.(12) has S[q] @ a_t^*(theta) = sum_{nt} x_{nt} exp(+j pi nt sin theta)
        # Let's match sign: ula_steering has exp(-j pi nt sin theta), so conjugate is exp(+j pi nt sin theta).
        A_wb_conj = np.conj(A_wb)  # (Nt, N)
        # Operator from s_af[:, nt] to u_p_af: M_nt = A @ F_dft^H @ diag(A_wb_conj[nt, :]) @ F_dft @ A^H
        FAH = F_dft @ A.conj().T  # (N, N)
        AFH = A @ F_dft.conj().T  # (N, N)
        for nt in range(Nt):
            M_nt = (AFH * A_wb_conj[nt, :][None, :]) @ FAH  # (N, N)
            EM = (alpha_p * E_p) @ M_nt
            # Column mapping: vec_m(S) has index m*Nt + nt
            H_k[:, nt::Nt] += EM
    return H_k


def eval_sum_rate_and_radar_wb(H_users, Wc_bins, Ws_bins, F_rf, A, F_dft, Nt, theta_tar, eta_bw, sigma2):
    """
    Wc_bins: (N, Nrf, K), Ws_bins: (N, Nrf, Ls), F_rf: (Nt, Nrf) (or eye(Nt) for TTD/FD).
    Computes exact block sum-rate (Liu 2607 Eq. 19) and monostatic wideband target matched-bin gain!
    """
    N, Nrf, K = Wc_bins.shape
    Ls = Ws_bins.shape[2]
    # Construct block-diagonal effective precoders W_full_k in C^{(N*Nt) x N}
    W_full_c = np.zeros((K, N * Nt, N), dtype=np.complex128)
    W_full_s = np.zeros((N * Nt, N * Ls), dtype=np.complex128)
    for m in range(N):
        r0, r1 = m * Nt, (m + 1) * Nt
        W_eff_c = F_rf @ Wc_bins[m]  # (Nt, K)
        for k in range(K):
            W_full_c[k, r0:r1, m] = W_eff_c[:, k]
        if Ls > 0:
            W_full_s[r0:r1, m * Ls:(m + 1) * Ls] = F_rf @ Ws_bins[m]

    sum_rate = 0.0
    I_N = np.eye(N, dtype=np.complex128)
    HW_c = [[H_users[k] @ W_full_c[j] for j in range(K)] for k in range(K)]
    HW_s = [H_users[k] @ W_full_s for k in range(K)]
    for k in range(K):
        Sigma_k = sigma2 * I_N + HW_s[k] @ HW_s[k].conj().T
        for j in range(K):
            if j != k:
                Sigma_k = Sigma_k + HW_c[k][j] @ HW_c[k][j].conj().T
        Sig_des = HW_c[k][k] @ HW_c[k][k].conj().T
        mat = I_N + np.linalg.solve(Sigma_k, Sig_des)
        sign, logdet = np.linalg.slogdet(mat)
        sum_rate += float(np.real(logdet) / np.log(2.0)) / float(N)

    # Wideband target illumination energy reaching target at theta_tar across N bins (normalized by P_tot)
    H_tar = build_wideband_user_channel(A, F_dft, 0.0, Nt, [(1.0 + 0.0j, 0, 0.0, theta_tar)], eta_bw)
    # Wait: use exact same A and c1 for target! Pass H_tar from caller to avoid c1 mismatch!
    return sum_rate, W_full_c, W_full_s


def run_g1_trial(seed: int, eta_bw: float = 0.12, c1_zero: bool = False):
    rng = np.random.default_rng(seed)
    Nt, Nrf, K, Pk, N = 64, 6, 3, 3, 64
    ell_max = 4
    nu_max = 0.0 if c1_zero else 0.65
    c1 = 0.0 if c1_zero else (2.0 * nu_max + 1.0) / (2.0 * N)
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_max = float(N)
    snr_db = 20.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    theta_tar = 42.0
    user_centers = [-48.0, -15.0, 22.0]

    users_paths = []
    for k in range(K):
        paths = []
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-6.0, 6.0)
            nu = 0.0 if c1_zero else rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    H_users = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], eta_bw) for k in range(K)]
    H_tar = build_wideband_user_channel(A, F_dft, c1, Nt, [(1.0 + 0.0j, 2, 0.25 if not c1_zero else 0.0, theta_tar)], eta_bw)

    def metrics_from_W(W_full_c, W_full_s):
        # Enforce exact total transmit power P_max
        p_cur = sum(float(np.sum(np.abs(W_full_c[k]) ** 2)) for k in range(K)) + float(np.sum(np.abs(W_full_s) ** 2))
        scale = np.sqrt(P_max / max(p_cur, 1e-15))
        Wc = W_full_c * scale
        Ws = W_full_s * scale
        sr = 0.0
        I_N = np.eye(N, dtype=np.complex128)
        for k in range(K):
            Sig = sigma2 * I_N + (H_users[k] @ Ws) @ (H_users[k] @ Ws).conj().T
            for j in range(K):
                if j != k:
                    hw = H_users[k] @ Wc[j]
                    Sig = Sig + hw @ hw.conj().T
            hwd = H_users[k] @ Wc[k]
            _, ld = np.linalg.slogdet(I_N + np.linalg.solve(Sig, hwd @ hwd.conj().T))
            sr += float(np.real(ld) / np.log(2.0)) / float(N)
        # Monostatic two-way wideband echo energy at target (tx squint + rx squint = squared gain!)
        # Tx illumination waveform at target angle: u_tar = H_tar @ [Wc, Ws], expected energy E||u_tar||^2 / N
        e_tar = sum(float(np.sum(np.abs(H_tar @ Wc[k]) ** 2)) for k in range(K)) + float(np.sum(np.abs(H_tar @ Ws) ** 2))
        # Normalized against ideal array gain Nt * P_max: in dB
        tar_gain_db = 10.0 * np.log10(max(e_tar / (Nt * P_max), 1e-15))
        return sr, tar_gain_db

    # Oracle: Ideal True-Time-Delay (TTD, squint-free eta_bw=0 equivalent steering) + Full-Block RZF + Target Beam
    # Construct TTD analog dictionary: steering vectors with exact frequency-dependent phase = squint-free!
    # Equivalently, evaluate squint-free channel (eta_bw=0) with Nrf=6 analog beams (3 dominant user cov + 2 user sub + 1 target)
    H_users_ttd = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    H_tar_ttd = build_wideband_user_channel(A, F_dft, c1, Nt, [(1.0 + 0.0j, 2, 0.25 if not c1_zero else 0.0, theta_tar)], 0.0)

    # Analog phase-shifter matrix F_rf (Nt x Nrf, unit modulus |F_rf[i,j]| = 1/sqrt(Nt)):
    # Method (b): Elbir WCL'24 HANDBALL F_N -> A naive port:
    #   Pick 1 center-freq steering beam per user (dominant path) + 3 sub-beams / target beam,
    #   then per-DAFT-bin pseudo-inverse B[m] = H_eff_nb[m]^dagger assuming narrowband & diagonal DAFT!
    F_rf_elbir = np.zeros((Nt, Nrf), dtype=np.complex128)
    for k in range(K):
        p_dom = max(users_paths[k], key=lambda x: abs(x[0]))
        F_rf_elbir[:, k] = ula_steering(Nt, p_dom[3], unit_norm=True)
    F_rf_elbir[:, K] = ula_steering(Nt, theta_tar, unit_norm=True)
    # Remaining 2 RF chains: next strongest user scatterers
    extra_angs = sorted([p[3] for u in users_paths for p in u], key=lambda a: abs(a))[:2]
    F_rf_elbir[:, K + 1] = ula_steering(Nt, users_paths[0][1][3], unit_norm=True)
    F_rf_elbir[:, K + 2] = ula_steering(Nt, users_paths[1][1][3], unit_norm=True)

    # Naive port (b): treats DAFT bin m as physical OFDM frequency bin m!
    # Even if we equip (b) with wideband steering at bin m (thinking DAFT bin m == DFT freq bin m, i.e. F_N -> A!),
    # let's test BOTH narrowband Elbir and DFT->DAFT wideband-formula naive port, and take the STRONGER one!
    def build_b_precoder(use_fake_daft_freq: bool):
        Wc_b = np.zeros((K, N * Nt, N), dtype=np.complex128)
        Ws_b = np.zeros((N * Nt, N), dtype=np.complex128)
        eta_split = 0.75  # 75% comm, 25% target illumination (matched across arms)
        kc_arr = np.fft.ifftshift(np.arange(-N // 2, N // 2, dtype=np.float64))
        for m in range(N):
            f_scale = (1.0 + (kc_arr[m] / float(N)) * eta_bw) if use_fake_daft_freq else 1.0
            H_bin = np.zeros((K, Nrf), dtype=np.complex128)
            for k in range(K):
                for alpha_p, ell_p, nu_p, theta_p in users_paths[k]:
                    idx_n = np.arange(Nt, dtype=np.float64)
                    a_conj = np.exp(1j * np.pi * idx_n * f_scale * np.sin(np.deg2rad(theta_p)))
                    # Naive F_N -> A port treats channel in bin m as sum_p alpha_p e^{-j2pi m ell_p / N} a^H F_rf!
                    H_bin[k, :] += alpha_p * np.exp(-1j * 2.0 * np.pi * m * ell_p / float(N)) * (a_conj @ F_rf_elbir)
            B_c = H_bin.conj().T @ np.linalg.inv(H_bin @ H_bin.conj().T + sigma2 * np.eye(K))
            B_c = B_c / max(np.linalg.norm(F_rf_elbir @ B_c, 'fro'), 1e-12) * np.sqrt(eta_split)
            b_s = F_rf_elbir.conj().T @ ula_steering(Nt, theta_tar, unit_norm=True)
            b_s = b_s / max(np.linalg.norm(F_rf_elbir @ b_s), 1e-12) * np.sqrt(1.0 - eta_split)
            r0, r1 = m * Nt, (m + 1) * Nt
            Wc_m = F_rf_elbir @ B_c
            for k in range(K):
                Wc_b[k, r0:r1, m] = Wc_m[:, k]
            Ws_b[r0:r1, m] = F_rf_elbir @ b_s
        return metrics_from_W(Wc_b, Ws_b)

    sr_b1, tg_b1 = build_b_precoder(False)
    sr_b2, tg_b2 = build_b_precoder(True)
    sr_b = max(sr_b1, sr_b2)
    tg_b = tg_b1 if sr_b1 >= sr_b2 else tg_b2

    # Baseline (a): Published AFDM-ISAC (Liu & Schober 2607 narrowband model projected onto Nrf=6 PS-HBF,
    # plusDai/wideband-cov analog beam widening check? No: in Stage A (a) is strictly single published AFDM paper:
    # Liu 2607 narrowband DAFT model on hybrid array F_rf_elbir with full coupled DAFT baseband RZF/WMMSE!)
    # Let's give (a) FULL-BLOCK coupled baseband RZF on the narrowband-assumed effective channel so we don't handicap its baseband!
    F_blk = np.kron(np.eye(N), F_rf_elbir)  # (N*Nt, N*Nrf)
    H_nb_eff = np.vstack([H_users_ttd[k] @ F_blk for k in range(K)])  # (K*N, N*Nrf) - Liu 2607 narrowband CSI!
    G_bb = H_nb_eff.conj().T @ np.linalg.inv(H_nb_eff @ H_nb_eff.conj().T + K * sigma2 * np.eye(K * N))
    G_bb = G_bb / max(np.linalg.norm(F_blk @ G_bb, 'fro'), 1e-12) * np.sqrt(0.75 * P_max)
    Wc_a = np.zeros((K, N * Nt, N), dtype=np.complex128)
    for k in range(K):
        Wc_a[k] = F_blk @ G_bb[:, k * N:(k + 1) * N]
    Ws_a = np.zeros((N * Nt, N), dtype=np.complex128)
    b_s_nb = F_rf_elbir.conj().T @ ula_steering(Nt, theta_tar, unit_norm=True)
    w_s_col = F_rf_elbir @ b_s_nb
    w_s_col = w_s_col / np.linalg.norm(w_s_col) * np.sqrt(0.25)
    for m in range(N):
        Ws_a[m * Nt:(m + 1) * Nt, m] = w_s_col
    sr_a, tg_a = metrics_from_W(Wc_a, Ws_a)

    # Oracle 1: Ideal TTD (squint-free, same Nrf=6 RF chains!)
    # Evaluate Wc_a, Ws_a on squint-free TTD channel H_users_ttd, H_tar_ttd:
    sr_ttd = 0.0
    I_N = np.eye(N, dtype=np.complex128)
    for k in range(K):
        Sig = sigma2 * I_N + (H_users_ttd[k] @ Ws_a) @ (H_users_ttd[k] @ Ws_a).conj().T
        for j in range(K):
            if j != k:
                hw = H_users_ttd[k] @ Wc_a[j]
                Sig = Sig + hw @ hw.conj().T
        hwd = H_users_ttd[k] @ Wc_a[k]
        _, ld = np.linalg.slogdet(I_N + np.linalg.solve(Sig, hwd @ hwd.conj().T))
        sr_ttd += float(np.real(ld) / np.log(2.0)) / float(N)
    e_tar_ttd = sum(float(np.sum(np.abs(H_tar_ttd @ Wc_a[k]) ** 2)) for k in range(K)) + float(np.sum(np.abs(H_tar_ttd @ Ws_a) ** 2))
    tg_ttd = 10.0 * np.log10(max(e_tar_ttd / (Nt * P_max), 1e-15))

    # Oracle 2 (Same PS-HBF hardware without TTD, knowing exact wideband squint CSI + broadened/subarray PS):
    # Checks Rule 27 two-sided squeeze: is there real headroom WITHOUT adding TTD hardware?!
    # Use 2 subarrays per target/user cov eigenvectors + exact wideband H_users full-block RZF:
    R_tot_spatial = np.zeros((Nt, Nt), dtype=np.complex128)
    for k in range(K):
        # Reshape H_users[k] (N, N*Nt) -> (N*N, Nt)
        Hk_sp = H_users[k].reshape(N * N, Nt)
        R_tot_spatial += (Hk_sp.conj().T @ Hk_sp) / float(N)
    Ht_sp = H_tar.reshape(N * N, Nt)
    R_tar_spatial = (Ht_sp.conj().T @ Ht_sp) / float(N)
    _, U_comm = np.linalg.eigh(R_tot_spatial)
    _, U_tar = np.linalg.eigh(R_tar_spatial)
    F_rf_sq = np.zeros((Nt, Nrf), dtype=np.complex128)
    F_rf_sq[:, :4] = np.exp(1j * np.angle(U_comm[:, -4:])) / np.sqrt(Nt)
    F_rf_sq[:, 4:] = np.exp(1j * np.angle(U_tar[:, -2:])) / np.sqrt(Nt)
    F_blk_sq = np.kron(np.eye(N), F_rf_sq)
    H_wb_eff = np.vstack([H_users[k] @ F_blk_sq for k in range(K)])
    G_wb = H_wb_eff.conj().T @ np.linalg.inv(H_wb_eff @ H_wb_eff.conj().T + K * sigma2 * np.eye(K * N))
    G_wb = G_wb / max(np.linalg.norm(F_blk_sq @ G_wb, 'fro'), 1e-12) * np.sqrt(0.75 * P_max)
    Wc_oracle_ps = np.zeros((K, N * Nt, N), dtype=np.complex128)
    for k in range(K):
        Wc_oracle_ps[k] = F_blk_sq @ G_wb[:, k * N:(k + 1) * N]
    # Sensing stream in nullspace of H_wb_eff maximizing ||H_tar F_blk_sq b_s||^2!
    Ht_eff = H_tar @ F_blk_sq  # (N, N*Nrf)
    _, _, Vh_t = np.linalg.svd(Ht_eff, full_matrices=False)
    Ws_oracle_ps = (F_blk_sq @ Vh_t[:N, :].conj().T)
    Ws_oracle_ps = Ws_oracle_ps / np.linalg.norm(Ws_oracle_ps, 'fro') * np.sqrt(0.25 * P_max)
    sr_ops, tg_ops = metrics_from_W(Wc_oracle_ps, Ws_oracle_ps)

    return {
        "sr_a": sr_a, "tg_a": tg_a,
        "sr_b": sr_b, "tg_b": tg_b,
        "sr_oracle_ttd": sr_ttd, "tg_oracle_ttd": tg_ttd,
        "sr_oracle_same_ps": sr_ops, "tg_oracle_same_ps": tg_ops,
    }


# =====================================================================
# B1-G2: Narrowband Few-RF-Chain (Nrf = K+1 << Nt) Hybrid MIMO-AFDM ISAC
# Anchors: Elbir WCL'24 Fig. 2-3 (Nt=32, Nrf=4, K=3, T=1, Pk=3) + Liu & Schober 2607 Sec. V
# =====================================================================
def run_g2_trial(seed: int, c1_zero: bool = False):
    rng = np.random.default_rng(seed)
    Nt, Nrf, K, Pk, N = 32, 4, 3, 3, 64
    ell_max = 6
    nu_max = 0.0 if c1_zero else 0.85
    c1 = 0.0 if c1_zero else (2.0 * nu_max + 1.0) / (2.0 * N)
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_max = float(N)
    snr_db = 20.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    theta_tar = 40.0
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-18.0, 18.0)  # NLoS multipath spread
            nu = 0.0 if c1_zero else rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    H_users = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    a_tar = ula_steering(Nt, theta_tar, unit_norm=True)

    def eval_hybrid(F_rf, W_bb_c, W_bb_s):
        # F_rf: (Nt, Nrf) unit-modulus entries |F_rf|=1/sqrt(Nt)
        F_blk = np.kron(np.eye(N), F_rf)
        Wc = np.array([F_blk @ W_bb_c[k] for k in range(K)])
        Ws = F_blk @ W_bb_s
        p_tot = sum(float(np.sum(np.abs(Wc[k]) ** 2)) for k in range(K)) + float(np.sum(np.abs(Ws) ** 2))
        sc = np.sqrt(P_max / max(p_tot, 1e-15))
        Wc *= sc
        Ws *= sc
        sr = 0.0
        I_N = np.eye(N, dtype=np.complex128)
        # Also evaluate 16-QAM block LMMSE SER!
        alph = qam16_alphabet()
        d_syms = alph[rng.integers(0, 16, size=(K, N))]
        s_vec = sum(Wc[k] @ d_syms[k] for k in range(K)) + Ws @ ((rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0))
        sers = []
        for k in range(K):
            Sig = sigma2 * I_N + (H_users[k] @ Ws) @ (H_users[k] @ Ws).conj().T
            for j in range(K):
                if j != k:
                    hw = H_users[k] @ Wc[j]
                    Sig = Sig + hw @ hw.conj().T
            hwd = H_users[k] @ Wc[k]
            _, ld = np.linalg.slogdet(I_N + np.linalg.solve(Sig, hwd @ hwd.conj().T))
            sr += float(np.real(ld) / np.log(2.0)) / float(N)
            zk = H_users[k] @ s_vec + np.sqrt(sigma2 / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
            C_tot = Sig + hwd @ hwd.conj().T
            d_hat = hwd.conj().T @ np.linalg.solve(C_tot, zk)
            sers.append(nearest_symbol_ser(d_hat, d_syms[k], alph))
        # Target illumination gain
        S_mat = s_vec.reshape(N, Nt)
        # Deterministic expected illumination tr(a_tar^H R_x a_tar) / P_max
        e_tar = 0.0
        for m in range(N):
            r0, r1 = m * Nt, (m + 1) * Nt
            for k in range(K):
                e_tar += float(np.sum(np.abs(a_tar.conj() @ Wc[k, r0:r1, :]) ** 2))
            e_tar += float(np.sum(np.abs(a_tar.conj() @ Ws[r0:r1, :]) ** 2))
        return sr, float(np.mean(sers)), 10.0 * np.log10(max(e_tar / P_max, 1e-15))

    # Analog beamformer: Elbir WCL'24 Alg. 1 (1 dominant SVD/steering per user + 1 target beam)
    F_rf = np.zeros((Nt, Nrf), dtype=np.complex128)
    for k in range(K):
        Hk_sp = H_users[k].reshape(N * N, Nt)
        _, _, Vh = np.linalg.svd(Hk_sp, full_matrices=False)
        F_rf[:, k] = np.exp(1j * np.angle(Vh[0].conj())) / np.sqrt(Nt)
    F_rf[:, K] = a_tar

    # (b) Elbir WCL'24 F_N -> A naive port: per-DAFT-bin diagonal block H_eff[m] pseudo-inverse!
    W_bb_c_b = np.zeros((K, N * Nrf, N), dtype=np.complex128)
    W_bb_s_b = np.zeros((N * Nrf, N), dtype=np.complex128)
    F_blk = np.kron(np.eye(N), F_rf)
    H_eff_all = [H_users[k] @ F_blk for k in range(K)]  # each (N, N*Nrf)
    for m in range(N):
        # Naive per-bin extracts ONLY the diagonal (m, m*Nrf:(m+1)*Nrf) block!
        H_m = np.vstack([H_eff_all[k][m, m * Nrf:(m + 1) * Nrf] for k in range(K)])  # (K, Nrf)
        B_m = H_m.conj().T @ np.linalg.inv(H_m @ H_m.conj().T + sigma2 * np.eye(K))
        B_m = B_m / max(np.linalg.norm(F_rf @ B_m, 'fro'), 1e-12) * np.sqrt(0.75)
        for k in range(K):
            W_bb_c_b[k, m * Nrf:(m + 1) * Nrf, m] = B_m[:, k]
        bs = np.zeros(Nrf, dtype=np.complex128)
        bs[K] = 1.0
        bs = bs / max(np.linalg.norm(F_rf @ bs), 1e-12) * np.sqrt(0.25)
        W_bb_s_b[m * Nrf:(m + 1) * Nrf, m] = bs
    sr_b, ser_b, tg_b = eval_hybrid(F_rf, W_bb_c_b, W_bb_s_b)

    # (a) Liu & Schober 2607 per-bin precoder projected onto F_rf via AltMin / LS per bin (12 WMMSE iters):
    # Wait: in Liu 2607, precoder IS block-diagonal per DAFT bin! So on hybrid F_rf, W[m] = F_rf B[m] IS per-bin block-diagonal,
    # optimized with full coupled C_k^-1 WMMSE updates! Let's run 12 exact WMMSE iterations of Liu 2607 on H_eff_all!
    W_bb_c_a = W_bb_c_b.copy()
    W_bb_s_a = W_bb_s_b.copy()
    I_N = np.eye(N, dtype=np.complex128)
    a_eff_tar = F_rf.conj().T @ a_tar  # (Nrf,)
    for _ in range(12):
        Tw_bins = np.zeros((N, Nrf, Nrf), dtype=np.complex128)
        Bk_bins = np.zeros((K, N, Nrf), dtype=np.complex128)
        for k in range(K):
            Hk = H_eff_all[k]
            Ck = sigma2 * I_N + (Hk @ W_bb_s_a) @ (Hk @ W_bb_s_a).conj().T
            for j in range(K):
                hw = Hk @ W_bb_c_a[j]
                Ck = Ck + hw @ hw.conj().T
            Uk = np.linalg.solve(Ck, Hk @ W_bb_c_a[k])
            Ek = I_N - W_bb_c_a[k].conj().T @ Hk.conj().T @ Uk
            Ek = 0.5 * (Ek + Ek.conj().T) + 1e-9 * I_N
            Mk = np.linalg.inv(Ek)
            # Jk = Hk^H Uk Mk U_k^H Hk -> only need diagonal Nrf x Nrf blocks for per-bin W_bb[m]!
            V = Hk.conj().T @ Uk  # (N*Nrf, N)
            VM = V @ Mk           # (N*Nrf, N)
            for m in range(N):
                sl = slice(m * Nrf, (m + 1) * Nrf)
                Tw_bins[m] += VM[sl, :] @ V[sl, :].conj().T
                Bk_bins[k, m] = VM[sl, m]
        # Solve per-bin Ridge + keep target stream
        W_new_c = np.zeros_like(W_bb_c_a)
        for m in range(N):
            Tm = Tw_bins[m] + 0.05 * (F_rf.conj().T @ F_rf)
            for k in range(K):
                W_new_c[k, m * Nrf:(m + 1) * Nrf, m] = np.linalg.solve(Tm, Bk_bins[k, m])
        # Normalize comm to 0.75 P_max, sensing to 0.25 P_max
        p_c = sum(float(np.sum(np.abs(F_blk @ W_new_c[k]) ** 2)) for k in range(K))
        W_bb_c_a = W_new_c * np.sqrt(0.75 * P_max / max(p_c, 1e-15))
    sr_a, ser_a, tg_a = eval_hybrid(F_rf, W_bb_c_a, W_bb_s_a)

    # Oracle (Same Nrf=4 PS-HBF hardware! Full-block cross-bin baseband RZF + nullspace sensing):
    H_stack = np.vstack(H_eff_all)  # (K*N, N*Nrf)
    G_full = H_stack.conj().T @ np.linalg.inv(H_stack @ H_stack.conj().T + K * sigma2 * np.eye(K * N))
    W_bb_c_or = np.array([G_full[:, k * N:(k + 1) * N] for k in range(K)])
    p_c = sum(float(np.sum(np.abs(F_blk @ W_bb_c_or[k]) ** 2)) for k in range(K))
    W_bb_c_or *= np.sqrt(0.75 * P_max / max(p_c, 1e-15))
    # Sensing in approximate nullspace of H_stack along a_eff_tar
    W_bb_s_or = W_bb_s_b.copy()
    # Project sensing out of comm row space!
    _, _, Vh_h = np.linalg.svd(H_stack, full_matrices=True)
    P_null = Vh_h[K * N:, :].conj().T @ Vh_h[K * N:, :]  # (N*Nrf) - (K*N) = N*(4-3) = N dimensional exact nullspace!!
    W_bb_s_or = P_null @ W_bb_s_b
    p_s = float(np.sum(np.abs(F_blk @ W_bb_s_or) ** 2))
    W_bb_s_or *= np.sqrt(0.25 * P_max / max(p_s, 1e-15))
    sr_or, ser_or, tg_or = eval_hybrid(F_rf, W_bb_c_or, W_bb_s_or)

    return {
        "sr_a": sr_a, "ser_a": ser_a, "tg_a": tg_a,
        "sr_b": sr_b, "ser_b": ser_b, "tg_b": tg_b,
        "sr_oracle_same_nrf": sr_or, "ser_oracle_same_nrf": ser_or, "tg_oracle_same_nrf": tg_or,
    }


# =====================================================================
# B1-G3: Low-Resolution 1-2 bit DAC Downlink Multiuser MIMO-AFDM ISAC
# Anchors: Wang, Hu, Li, Masouros & Wong TWC'25 (10.1109/TWC.2025.3595731, Fig. 16-18)
#          + Sui & Zilong Liu TCOM'26 (10.1109/tcomm.2026.3701879, Fig. 5) + Liu 2607
# =====================================================================
def quantize_dac(X_td: np.ndarray, b_bits: int, P_tot: float) -> np.ndarray:
    """Uniform b-bit I/Q mid-riser quantizer scaled to exact total block power P_tot (Wang TWC'25 Eq. 1)."""
    L_lvl = 2 ** b_bits
    rms = np.sqrt(np.mean(np.abs(X_td) ** 2) / 2.0 + 1e-15)
    # Optimal Gaussian step delta_b (Max-Lloyd / uniform step): b=1 -> sign, b=2 -> delta=1.0*rms
    delta = {1: 1.0, 2: 0.9957 * rms, 3: 0.5860 * rms}.get(b_bits, rms / L_lvl)
    def q_real(u):
        if b_bits == 1:
            return np.where(u >= 0.0, 1.0, -1.0)
        idx = np.clip(np.floor(u / delta) + (L_lvl // 2), 0, L_lvl - 1)
        return (2.0 * idx + 1.0 - L_lvl)
    Xq = q_real(np.real(X_td)) + 1j * q_real(np.imag(X_td))
    Xq = Xq * np.sqrt(P_tot / max(float(np.sum(np.abs(Xq) ** 2)), 1e-15))
    return Xq


def run_g3_trial(seed: int, b_bits: int = 1, c1_zero: bool = False):
    rng = np.random.default_rng(seed)
    Nt, Nr, K, Pk, N, Q = 16, 8, 3, 3, 64, 8
    ell_max = 4
    nu_max = 0.0 if c1_zero else 0.75
    c1 = 0.0 if c1_zero else (2.0 * nu_max + 1.0) / (2.0 * N)
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_blk = float(N)
    snr_db = 20.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    theta_tar = 36.0
    user_centers = [-45.0, -12.0, 18.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-8.0, 8.0)
            nu = 0.0 if c1_zero else rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    # Single-tap equalization-free downlink user model (as in Wang TWC'25 & Tang TWC'26, QPSK)
    H_users_af = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    # Also map from time-domain vec(X_TD) (N x Nt): X_TD = A^H S_AF => S_AF = A X_TD
    A_kron = np.kron(A, np.eye(Nt))  # maps vec_m(X_TD) -> vec_m(S_AF)
    H_users_td = [H_users_af[k] @ A_kron for k in range(K)]  # (N, N*Nt) from vec_m(X_TD)!
    a_tar = ula_steering(Nt, theta_tar)  # unnormalized, norm^2 = Nt

    alph = qpsk_alphabet()
    d_cpi = alph[rng.integers(0, 4, size=(Q, K, N))]
    noise_cpi = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N)))

    # Radar scenario: strong target (+23 dB at ell=1, nu_s=0.0) + weak target (0 dB at ell=3, nu_w=0.22)
    # both at theta_tar (monostatic known-waveform matched filter / reciprocal sidelobe test)
    def eval_cpi_waveforms(X_td_cpi: np.ndarray):
        # X_td_cpi: (Q, N, Nt), each block normalized to P_blk
        sers = []
        for q in range(Q):
            x_vec = X_td_cpi[q].reshape(N * Nt)
            for k in range(K):
                # Optimal Bussgang/MMSE scalar scaling alpha_hat (zero-order textbook calibration!)
                y_clean = H_users_td[k] @ x_vec
                zk = y_clean + noise_cpi[q, k]
                # Single-tap QPSK quadrant decision is scale-invariant for positive real scalar!
                # Align global phase if needed? No, precoder already aligns phase; check positive scalar Bussgang:
                sers.append(nearest_symbol_ser(zk, d_cpi[q, k], alph))
        # Radar illumination & strong-target sidelobe floor at weak target bin
        u_tar = np.einsum("qni,i->qn", X_td_cpi, np.conj(a_tar))  # (Q, N) waveform toward theta_tar
        # Strong echo +23 dB at (ell_s=1, nu_s=0.05), weak echo 0 dB at (ell_w=3, nu_w=0.28)
        T_s = td_path_matrix(N, c1, 1, 0.05 if not c1_zero else 0.0)
        T_w = td_path_matrix(N, c1, 3, 0.28 if not c1_zero else 0.0)
        amp_s = 10.0 ** (23.0 / 20.0)
        amp_w = 1.0
        # Coherent slow-time phases across Q blocks (Tsym = 1.15 * N)
        q_idx = np.arange(Q, dtype=np.float64)
        b_s = np.exp(1j * 2.0 * np.pi * (0.05 if not c1_zero else 0.0) * 1.15 * q_idx)
        b_w = np.exp(1j * 2.0 * np.pi * (0.28 if not c1_zero else 0.0) * 1.15 * q_idx)
        # Matched filter at weak target hypothesis (ell_w=3, nu_w=0.28) vs strong target leakage + radar noise
        # Template at weak target: phi_w[q] = b_w[q] * (T_w @ u_tar[q])
        phi_w = b_w[:, None] * (u_tar @ T_w.T)
        echo_s = amp_s * b_s[:, None] * (u_tar @ T_s.T)
        sig_num = abs(np.sum(np.conj(phi_w) * (amp_w * phi_w))) ** 2
        leak_s = abs(np.sum(np.conj(phi_w) * echo_s)) ** 2
        rad_sigma2 = 0.1
        noise_den = rad_sigma2 * float(np.sum(np.abs(phi_w) ** 2))
        weak_sinr_db = 10.0 * np.log10(max(sig_num / max(leak_s + noise_den, 1e-15), 1e-15))
        illum_db = 10.0 * np.log10(max(float(np.mean(np.sum(np.abs(u_tar) ** 2, axis=1))) / (Nt * P_blk), 1e-15))
        return float(np.mean(sers)), weak_sinr_db, illum_db

    # Precompute full-block RZF + sensing nullspace matrix for infinite-bit Oracle & quantized RZF (a)
    H_all_td = np.vstack(H_users_td)  # (K*N, N*Nt)
    G_rzf = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + K * sigma2 * np.eye(K * N))
    # Target deterministic chirp waveform in nullspace of H_all_td!
    # Ideal low-sidelobe chirp in DAFT bin m=0 along a_tar, projected onto nullspace of H_all_td:
    s0_af = np.zeros((N, Nt), dtype=np.complex128)
    s0_af[0, :] = a_tar / np.sqrt(Nt)
    x0_td_vec = idaft_col(s0_af, lc1, lc2).reshape(N * Nt)
    # Project x0_td_vec orthogonal to columns of H_all_td^H:
    proj_h = H_all_td.conj().T @ np.linalg.solve(H_all_td @ H_all_td.conj().T + 1e-9 * np.eye(K * N), H_all_td @ x0_td_vec)
    x_rad_null = x0_td_vec - proj_h
    x_rad_null = x_rad_null / max(np.linalg.norm(x_rad_null), 1e-12)

    X_oracle = np.zeros((Q, N, Nt), dtype=np.complex128)
    X_a_qrzf = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        d_vec = d_cpi[q].reshape(K * N)
        x_comm = G_rzf @ d_vec
        x_comm = x_comm / np.linalg.norm(x_comm) * np.sqrt(0.65 * P_blk)
        x_tot = x_comm + np.sqrt(0.35 * P_blk) * np.exp(1j * 0.37 * q) * x_rad_null
        X_oracle[q] = (x_tot * np.sqrt(P_blk / np.sum(np.abs(x_tot) ** 2))).reshape(N, Nt)
        X_a_qrzf[q] = quantize_dac(X_oracle[q], b_bits, P_blk)

    # Mother method (b):
    # (b1) Wang TWC'25 per-DAFT-bin SQUID / CEO F_N -> A naive port (solves per DAFT bin m, then IDAFT + quantize)
    # (b2) Wang TWC'25 CEO applied directly to full 2*Nt*N time-domain block (Iter=35, M=120)
    X_b1 = np.zeros((Q, N, Nt), dtype=np.complex128)
    X_b2 = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        S_b1 = np.zeros((N, Nt), dtype=np.complex128)
        for m in range(N):
            H_m = np.vstack([H_users_af[k][m, m * Nt:(m + 1) * Nt] for k in range(K)])
            w_m = H_m.conj().T @ np.linalg.inv(H_m @ H_m.conj().T + sigma2 * np.eye(K)) @ d_cpi[q, :, m]
            w_m = w_m / max(np.linalg.norm(w_m), 1e-12) * np.sqrt(0.65)
            w_s = a_tar / np.sqrt(Nt) * np.sqrt(0.35) * (1.0 if m == 0 else 0.0)
            S_b1[m] = w_m + (np.sqrt(0.35 * N) * a_tar / np.sqrt(Nt) if m == 0 else 0.0)
        X_b1[q] = quantize_dac(idaft_col(S_b1, lc1, lc2), b_bits, P_blk)

        # (b2) Wang TWC'25 CEO direct block port (1-bit / 2-bit finite alphabet, M=100, Iter=30)
        D_dim = 2 * N * Nt
        L_lvl = 2 ** b_bits
        levels = np.array([-1.0, 1.0]) if b_bits == 1 else np.array([-3.0, -1.0, 1.0, 3.0])
        probs = np.full((D_dim, L_lvl), 1.0 / L_lvl)
        M_samp, M_elite = 100, 15
        d_target = d_cpi[q].reshape(K * N)
        best_x = None
        best_obj = -1e18
        for _ in range(25):
            # Sample (M_samp, D_dim)
            cdf = np.cumsum(probs, axis=1)
            u_r = rng.random((M_samp, D_dim, 1))
            idx_s = np.argmax(u_r <= cdf[None, :, :], axis=2)
            raw = levels[idx_s]
            Xc = raw[:, :N * Nt] + 1j * raw[:, N * Nt:]
            Xc = Xc * np.sqrt(P_blk / np.sum(np.abs(Xc) ** 2, axis=1, keepdims=True))
            # Wang TWC'25 objective: weighted min CI margin + target illumination power
            Y_u = Xc @ H_all_td.T  # (M_samp, K*N)
            rot = Y_u * np.conj(d_target)[None, :]
            ci_margin = np.min(np.minimum(np.real(rot) + np.imag(rot), np.real(rot) - np.imag(rot)), axis=1)
            # Target illumination
            X_reshaped = Xc.reshape(M_samp, N, Nt)
            p_rad = np.mean(np.abs(X_reshaped @ np.conj(a_tar)) ** 2, axis=1) / float(Nt)
            obj = 0.7 * ci_margin + 0.3 * np.sqrt(p_rad)
            order = np.argsort(obj)[::-1]
            if obj[order[0]] > best_obj:
                best_obj = float(obj[order[0]])
                best_x = Xc[order[0]].copy()
            elite = idx_s[order[:M_elite]]
            new_p = np.zeros_like(probs)
            for lv in range(L_lvl):
                new_p[:, lv] = np.mean(elite == lv, axis=0)
            probs = 0.7 * new_p + 0.3 * probs
        X_b2[q] = best_x.reshape(N, Nt)

    ser_or, wsinr_or, il_or = eval_cpi_waveforms(X_oracle)
    ser_a, wsinr_a, il_a = eval_cpi_waveforms(X_a_qrzf)
    ser_b1, wsinr_b1, il_b1 = eval_cpi_waveforms(X_b1)
    ser_b2, wsinr_b2, il_b2 = eval_cpi_waveforms(X_b2)
    # Pick stronger (lower SER) of b1, b2
    if ser_b2 < ser_b1:
        ser_b, wsinr_b, b_tag = ser_b2, wsinr_b2, "CEO_FullBlock"
    else:
        ser_b, wsinr_b, b_tag = ser_b1, wsinr_b1, "PerBin_Naive"

    return {
        "ser_a": ser_a, "wsinr_a": wsinr_a,
        "ser_b": ser_b, "wsinr_b": wsinr_b, "b_winner": b_tag,
        "ser_b_perbin": ser_b1, "ser_b_ceo": ser_b2,
        "ser_oracle_infbit": ser_or, "wsinr_oracle_infbit": wsinr_or,
    }


# =====================================================================
# B1-G4: Saturated Nonlinear PA (SEL/Rapp, IBO = 0 dB) Multiuser 16-QAM MIMO-AFDM ISAC
# Anchors: Sui & Zilong Liu TCOM'26 Fig. 7 + Gourar 2609.14030 / 2607.01064 + Liu 2607
# =====================================================================
def apply_sel_pa(X_td: np.ndarray, a_sat: float) -> np.ndarray:
    mag = np.abs(X_td)
    scale = np.where(mag > a_sat, a_sat / np.maximum(mag, 1e-15), 1.0)
    return X_td * scale


def run_g4_trial(seed: int, ibo_db: float = 0.0, c1_zero: bool = False):
    rng = np.random.default_rng(seed)
    Nt, K, Pk, N, Q = 8, 3, 3, 64, 8
    ell_max = 4
    nu_max = 0.0 if c1_zero else 0.75
    c1 = 0.0 if c1_zero else (2.0 * nu_max + 1.0) / (2.0 * N)
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_blk = float(N)  # average power per antenna sample = P_blk / (N*Nt) = 1/Nt
    p_avg_ant = P_blk / float(N * Nt)
    a_sat = np.sqrt(p_avg_ant * (10.0 ** (ibo_db / 10.0)))
    snr_db = 26.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    theta_tar = 38.0
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-8.0, 8.0)
            nu = 0.0 if c1_zero else rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    H_users_af = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    A_kron = np.kron(A, np.eye(Nt))
    H_users_td = [H_users_af[k] @ A_kron for k in range(K)]
    a_tar = ula_steering(Nt, theta_tar)
    alph = qam16_alphabet()
    d_cpi = alph[rng.integers(0, 16, size=(Q, K, N))]
    noise_cpi = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N)))

    H_all_td = np.vstack(H_users_td)
    G_rzf = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + K * sigma2 * np.eye(K * N))
    s0_af = np.zeros((N, Nt), dtype=np.complex128)
    s0_af[0, :] = a_tar / np.sqrt(Nt)
    x0_td_vec = idaft_col(s0_af, lc1, lc2).reshape(N * Nt)
    proj_h = H_all_td.conj().T @ np.linalg.solve(H_all_td @ H_all_td.conj().T + 1e-9 * np.eye(K * N), H_all_td @ x0_td_vec)
    x_rad_null = (x0_td_vec - proj_h)
    x_rad_null = x_rad_null / max(np.linalg.norm(x_rad_null), 1e-12)

    # Exact SEL Bussgang gain K_PA (Sui TCOM'26 Eq. 26) for textbook zero-order scaling!
    nu_clip = np.sqrt(10.0 ** (ibo_db / 10.0))
    from math import erfc
    k_pa = 1.0 - np.exp(-nu_clip ** 2) + 0.5 * np.sqrt(np.pi) * nu_clip * erfc(nu_clip)

    def eval_pa(X_in_cpi, apply_pa_flag: bool):
        sers = []
        X_out = np.zeros_like(X_in_cpi)
        for q in range(Q):
            Xo = apply_sel_pa(X_in_cpi[q], a_sat) if apply_pa_flag else X_in_cpi[q].copy()
            # Keep radiated total power equal OR physical PA output?
            # Wait: compare at EQUAL average PA input power AND equal Bussgang receiver gain compensation (1/k_pa)!
            X_out[q] = Xo
            x_vec = Xo.reshape(N * Nt)
            # Exact Bussgang gain on this block: g_buss = <Xo, X_in> / ||X_in||^2
            g_buss = k_pa if apply_pa_flag else 1.0
            for k in range(K):
                # Give baseline exact deterministic scale factor alpha_k so multi-ring 16-QAM scale is 100% calibrated!
                zk = (H_users_td[k] @ x_vec + noise_cpi[q, k]) / (g_buss * alpha_scale)
                sers.append(nearest_symbol_ser(zk, d_cpi[q, k], alph))
        # Bistatic / semi-bistatic radar where receiver knows unclipped intended reference X_in (PA distortion acts as鬼影/noise)
        # AND monostatic radar where receiver measures PA output (or knows SEL model): check BOTH!
        u_in = np.einsum("qni,i->qn", X_in_cpi, np.conj(a_tar))
        u_out = np.einsum("qni,i->qn", X_out, np.conj(a_tar))
        T_s = td_path_matrix(N, c1, 1, 0.05 if not c1_zero else 0.0)
        T_w = td_path_matrix(N, c1, 3, 0.28 if not c1_zero else 0.0)
        q_idx = np.arange(Q, dtype=np.float64)
        b_s = np.exp(1j * 2.0 * np.pi * (0.05 if not c1_zero else 0.0) * 1.15 * q_idx)
        b_w = np.exp(1j * 2.0 * np.pi * (0.28 if not c1_zero else 0.0) * 1.15 * q_idx)
        # Monostatic knowing exact u_out vs strong target (+25 dB):
        phi_w = b_w[:, None] * (u_out @ T_w.T)
        echo_s = (10.0 ** (25.0 / 20.0)) * b_s[:, None] * (u_out @ T_s.T)
        sig_num = abs(np.sum(np.conj(phi_w) * phi_w)) ** 2
        leak_s = abs(np.sum(np.conj(phi_w) * echo_s)) ** 2
        wsinr_mono = 10.0 * np.log10(max(sig_num / max(leak_s + 0.05 * float(np.sum(np.abs(phi_w) ** 2)), 1e-15), 1e-15))
        return float(np.mean(sers)), wsinr_mono

    # Build linear precoded waveform X_lin
    X_lin = np.zeros((Q, N, Nt), dtype=np.complex128)
    # Compute exact deterministic alpha_scale so H_all_td @ (alpha_scale * G_rzf @ d) == d at high SNR
    # Notice G_rzf = H^H (H H^H + reg I)^-1; normalize columns collectively to power 0.70 * P_blk:
    # Expected ||G_rzf d||^2 = tr(G_rzf^H G_rzf)
    e_norm = np.sqrt(float(np.real(np.trace(G_rzf.conj().T @ G_rzf))))
    alpha_scale = np.sqrt(0.70 * P_blk) / max(e_norm, 1e-12)
    for q in range(Q):
        d_vec = d_cpi[q].reshape(K * N)
        x_tot = alpha_scale * (G_rzf @ d_vec) + np.sqrt(0.30 * P_blk) * np.exp(1j * 0.37 * q) * x_rad_null
        X_lin[q] = x_tot.reshape(N, Nt)

    ser_or, wsinr_or = eval_pa(X_lin, False)
    ser_a, wsinr_a = eval_pa(X_lin, True)

    # (b) Per-DAFT-bin Bussgang RZF F_N -> A naive port:
    X_b = np.zeros((Q, N, Nt), dtype=np.complex128)
    G_b_blocks = []
    e_norm_b_sq = 0.0
    for m in range(N):
        H_m = np.vstack([H_users_af[k][m, m * Nt:(m + 1) * Nt] for k in range(K)])
        Gm = H_m.conj().T @ np.linalg.inv(H_m @ H_m.conj().T + K * (sigma2 + 0.08) * np.eye(K))
        G_b_blocks.append(Gm)
        e_norm_b_sq += float(np.real(np.trace(Gm.conj().T @ Gm)))
    alpha_b = np.sqrt(0.70 * P_blk / max(e_norm_b_sq, 1e-12))
    old_scale = alpha_scale
    alpha_scale = alpha_b
    for q in range(Q):
        S_b = np.zeros((N, Nt), dtype=np.complex128)
        for m in range(N):
            S_b[m] = alpha_b * (G_b_blocks[m] @ d_cpi[q, :, m])
            if m == 0:
                S_b[m] += np.sqrt(0.30 * P_blk) * a_tar / np.sqrt(Nt) * np.exp(1j * 0.37 * q)
        X_b[q] = idaft_col(S_b, lc1, lc2)
    ser_b, wsinr_b = eval_pa(X_b, True)
    alpha_scale = old_scale

    # Also check peak-constrained convex ceiling ||X||_inf <= a_sat (via 30-step projected gradient on ||H x - alpha d||^2 + ||X-X_rad||)
    # so we know if PA saturation at IBO=0 dB can actually be broken on the SAME peak-limited hardware!
    X_ceil = np.zeros((Q, N, Nt), dtype=np.complex128)
    # Lipschitz constant of H_all_td^H H_all_td:
    s_max = np.linalg.norm(H_all_td, 2) ** 2
    step = 0.9 / max(s_max, 1e-6)
    alpha_ceil = alpha_scale * 0.88  # feasible under |x| <= a_sat!
    for q in range(Q):
        d_vec = d_cpi[q].reshape(K * N)
        x_cur = apply_sel_pa(X_lin[q], a_sat).reshape(N * Nt)
        x_r = np.sqrt(0.30 * P_blk) * np.exp(1j * 0.37 * q) * x_rad_null
        for _ in range(35):
            res = H_all_td @ x_cur - alpha_ceil * d_vec
            grad = H_all_td.conj().T @ res
            # Keep target projection fixed along x_rad_null!
            grad = grad - x_rad_null * np.vdot(x_rad_null, grad)
            x_cur = apply_sel_pa((x_cur - step * grad).reshape(N, Nt), a_sat).reshape(N * Nt)
        X_ceil[q] = x_cur.reshape(N, Nt)
    alpha_scale = alpha_ceil
    ser_ceil, wsinr_ceil = eval_pa(X_ceil, True)

    return {
        "ser_a": ser_a, "wsinr_a": wsinr_a,
        "ser_b": ser_b, "wsinr_b": wsinr_b,
        "ser_oracle_lin": ser_or, "wsinr_oracle_lin": wsinr_or,
        "ser_oracle_same_pa_ceil": ser_ceil, "wsinr_oracle_same_pa_ceil": wsinr_ceil,
    }


def verify_redline1_g1_g4():
    common = verify_common_redline1()
    # G1 Redline 1: eta_bw = 0.0, sigma2 -> 1e-15: H_wb == H_ttd to < 1e-13!
    A, _, _, F_dft = build_daft_matrices(64, 3.0 / 128.0, 1.0 / 128.0)
    H0 = build_wideband_user_channel(A, F_dft, 3.0 / 128.0, 16, [(0.8 - 0.3j, 2, 0.35, 33.0)], 0.0)
    a_conj = np.conj(ula_steering(16, 33.0, unit_norm=False))
    E_p = daft_path_matrix(A, 3.0 / 128.0, 2, 0.35) * (0.8 - 0.3j)
    H_ref = np.kron(E_p, a_conj[None, :])
    g1_err = float(np.linalg.norm(H0 - H_ref))
    assert g1_err < 1e-12, f"G1 redline1 failed: {g1_err}"

    # G3 Redline 1: Wang TWC'25 Lemma 1 (1-bit at theta=0 achieves full array gain Nt * P_blk)
    X_ones = np.ones((64, 16), dtype=np.complex128)
    Xq = quantize_dac(X_ones, 1, 64.0)
    a0 = ula_steering(16, 0.0)
    u0 = Xq @ np.conj(a0)
    g3_err = float(abs(np.sum(np.abs(u0) ** 2) - 16.0 * 64.0))
    assert g3_err < 1e-11, f"G3 redline1 failed: {g3_err}"

    # G4 Redline 1: Sui TCOM'26 SEL PA with high IBO (40 dB) matches linear to < 1e-13
    X_test = (np.random.default_rng(1).standard_normal((64, 8)) + 1j) * 0.1
    g4_err = float(np.linalg.norm(apply_sel_pa(X_test, 100.0) - X_test))
    assert g4_err < 1e-14, f"G4 redline1 failed: {g4_err}"

    return {"common": common, "g1_nb_equiv_err": g1_err, "g3_lemma1_err": g3_err, "g4_linear_limit_err": g4_err}


def main():
    print(f"PYTHON_EXEC={sys.executable}", flush=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--redline1-only", action="store_true")
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    r1 = verify_redline1_g1_g4()
    print("REDLINE1 G1-G4 PASS:", json.dumps(r1))
    if args.redline1_only:
        return

    t0 = time.time()
    g1_af = [run_g1_trial(1000 + i, eta_bw=0.12, c1_zero=False) for i in range(args.trials)]
    g1_c0 = [run_g1_trial(1000 + i, eta_bw=0.12, c1_zero=True) for i in range(4)]

    g2_af = [run_g2_trial(2000 + i, c1_zero=False) for i in range(args.trials)]
    g2_c0 = [run_g2_trial(2000 + i, c1_zero=True) for i in range(4)]

    g3_b1 = [run_g3_trial(3000 + i, b_bits=1, c1_zero=False) for i in range(args.trials)]
    g3_b2 = [run_g3_trial(3000 + i, b_bits=2, c1_zero=False) for i in range(args.trials)]
    g3_c0 = [run_g3_trial(3000 + i, b_bits=1, c1_zero=True) for i in range(4)]

    g4_af = [run_g4_trial(4000 + i, ibo_db=0.0, c1_zero=False) for i in range(args.trials)]
    g4_c0 = [run_g4_trial(4000 + i, ibo_db=0.0, c1_zero=True) for i in range(4)]

    def avg_dict(lst):
        keys = [k for k in lst[0].keys() if isinstance(lst[0][k], (int, float))]
        return {k: float(np.mean([d[k] for d in lst])) for k in keys}

    summary = {
        "elapsed_sec": time.time() - t0,
        "trials": args.trials,
        "redline1": r1,
        "B1_G1_wideband_squint_hbf": {"afdm": avg_dict(g1_af), "c1_zero_static": avg_dict(g1_c0)},
        "B1_G2_narrowband_fewrf_hbf": {"afdm": avg_dict(g2_af), "c1_zero_static": avg_dict(g2_c0)},
        "B1_G3_lowres_dac_1bit": {"afdm": avg_dict(g3_b1), "c1_zero_static": avg_dict(g3_c0)},
        "B1_G3_lowres_dac_2bit": {"afdm": avg_dict(g3_b2)},
        "B1_G4_saturated_pa_ibo0": {"afdm": avg_dict(g4_af), "c1_zero_static": avg_dict(g4_c0)},
    }
    print(json.dumps(summary, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
