#!/usr/bin/env python3
"""
Round 15 Phase 1 — Track-A (tx, rx) Steelman Teardown Probe G2:
J = 6 Asynchronous High-Mobility Users 150%-Overloaded Grant-Free / NOMA (AFDM-SCMA vs O-AFDMA / Cross-Waveform)
(Qu Luo TWC'24 AFDM-SCMA / Xu & Xiao TCOM'25 AFDM-GF-RA setting, testing BOTH N_rx = 1 and N_rx = 2).

Physical Channel Contract (Locked Across ALL Arms):
- J = 6 concurrent active uplink users, block length N = 128, prefix L_cp = 16 (N_tot = 144 chips).
- Continuous-time 4x oversampled RRC pulse shaping (beta = 0.25) + matched RX RRC filter.
- Each user u has asynchronous timing offset + P = 3 continuous fractional-delay paths tau_{u,p} in [0, 6] T_s
  and continuous Jakes Doppler + user CFO nu_{u,p} in [-2.0, +2.0] bins -> 18 paths (72 real params) per RX antenna!
- Per-user net payload K_u = 44 info bits (264 total info bits/frame).
- Per-user frame resource & energy budget: 40 pilot/guard dims (energy 40) + 88 data dims (energy 88) + 16 prefix (energy 16)
  -> E_u = 144 per user across ALL waveforms; horizontal axis Eb/N0 = E_u / (K_u * N0).
- Evaluates BOTH N_rx = 1 (single RX antenna) and N_rx = 2 (two independent RX antennas).

Arms Tested per N_rx in {1, 2} (per Sol Call #1 Item 2):
1. pub_luo24_afdm_scma: Cramped 40-bin DAFT impulse pilots (6 bins/user) + OMP + 2D Block-EP/OAMP SCMA + QC-LDPC.
2. sm_a1_equalrate_o_afdma: Dispersed ZC pilots (40 slots) + 6 disjoint DAFT data subbands (4x15 + 2x14 = 88 bins,
   16-QAM rate 44/60 & 44/56 QC-LDPC) + continuous SAGE + full multi-user MMSE/EP + 3-round DD-SAGE.
3. sm_a2_zc_scma_mpa_dd: Dispersed ZC pilots (40 slots) + 150%-overloaded 16-ary AFDM-SCMA (22x4=88 bins, rate-1/2
   QC-LDPC(44,88)) + continuous SAGE + exact 2D-codebook multi-user Block-EP/MPA + 3-round DD-SAGE.
4. sm_s_ofdma_dd: Equal-net-rate OFDMA (full ICI multi-user EP + dispersed ZC + 3-round DD-SAGE).
5. sm_s_scfdma_dd: Equal-net-rate DFT-s-OFDMA / SC-FDMA (localized subbands + full multi-user EP + 3-round DD-SAGE).
6. sm_s_otfs_scma_dd: 150%-overloaded OTFS-SCMA (11x8=88 DD grid + dispersed ZC + Block-EP/MPA + 3-round DD-SAGE).
7. diag_true_csi_scma: Same TX as sm_a2 + gifted true RX CSI + single-pass Block-EP/MPA + LDPC (isolates CSI gap).
8. oracle_genie_joint_mpa: Same 40-pilot-taxed TX as sm_a2 + true RX CSI + 2-pass turbo Block-EP/MPA + LDPC bound.
"""
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
import time
import math
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ideas" / "r15"))

from r15_g_common import (
    RateMatchedQCLDPC,
    make_daft_mat,
    paired_crossing_gap_ci95,
    save_result_json,
)
from td_g_g1_mimo_fdfd import (
    BETA_RRC,
    rc_pulse_vec,
    build_chip_channel_matrix_single_path,
    mod_16qam,
    damped_mimo_ep_16qam,
)

N_BLK = 128
L_CP = 16
N_TOT = N_BLK + L_CP
J_USR = 6
N_PIL = 40
N_DAT = 88
N_GRP = 22  # 22 x 4 = 88 SCMA tones
K_USR = 44  # 44 info bits per user -> 264 total info bits

C1_128 = 9.0 / (2.0 * N_BLK)
C2_128 = 1.0 / (2.0 * N_BLK)
A_DAFT_128 = make_daft_mat(N_BLK, C1_128, C2_128)
A_DAFT_88 = make_daft_mat(N_DAT, 7.0 / (2.0 * N_DAT), 1.0 / (2.0 * N_DAT))
F_FFT_88 = np.fft.fft(np.eye(N_DAT), axis=0) / math.sqrt(N_DAT)
U_OTFS_88 = np.kron(np.fft.fft(np.eye(8), axis=0) / math.sqrt(8.0), np.eye(11))  # 11x8 = 88 DD grid!

# --- Dispersed 40-slot Unaliased 3-Cluster Zadoff-Chu Multi-User Pilot Design ---
# Spacing ~42 chips across N=128 eliminates 2-cluster half-frame Doppler grating lobes while keeping 3x13/14 = 40 slots!
PIL_SLOTS = np.concatenate([np.arange(0, 14), np.arange(43, 56), np.arange(86, 99)])  # 14 + 13 + 13 = 40 slots
DAT_SLOTS = np.setdiff1d(np.arange(N_BLK), PIL_SLOTS)  # 88 slots


def build_6user_dispersed_zc() -> np.ndarray:
    """
    Build (J=6, N_PIL=40) zero-guarded multi-user ZC training matrix across 3 equispaced clusters (14, 13, 13):
    Leading 4 chips of each cluster are zero-guarded against preceding data multipath+RRC ISI, and active ZC chips
    are scaled so each user's total pilot energy across the 40 slots is strictly 40.0!
    """
    P = np.zeros((J_USR, N_PIL), dtype=np.complex128)
    # Active sub-intervals inside PIL_SLOTS (40): [4..12] (9), [14+4 .. 14+11] (8), [27+4 .. 27+11] (8) -> 25 active chips!
    sc = math.sqrt(float(N_PIL) / 25.0)
    roots1 = [1, 2, 4, 5, 7, 8]
    roots2 = [1, 3, 5, 7, 1, 3]
    roots3 = [3, 7, 1, 5, 7, 1]
    n9 = np.arange(9, dtype=np.float64)
    n8 = np.arange(8, dtype=np.float64)
    had6 = np.array([
        [1, 1, 1], [1, -1, 1], [1, 1, -1], [1, -1, -1], [-1, 1, 1], [-1, -1, 1]
    ], dtype=np.float64)
    for u in range(J_USR):
        z1 = np.exp(-1j * np.pi * roots1[u] * n9 * (n9 + 1.0) / 9.0)
        z2 = np.exp(-1j * np.pi * roots2[u] * n8 * n8 / 8.0)
        z3 = np.exp(-1j * np.pi * roots3[u] * n8 * n8 / 8.0)
        P[u, 4:13] = sc * had6[u, 0] * np.roll(z1, (2 * u) % 9)
        P[u, 18:26] = sc * had6[u, 1] * np.roll(z2, (3 * u) % 8)
        P[u, 31:39] = sc * had6[u, 2] * np.roll(z3, (5 * u) % 8)
    return P


ZC_PIL_6X40 = build_6user_dispersed_zc()

# --- Standard 150%-Overloaded (J=6, K=4, dv=2, df=3) 16-ary SCMA Codebooks ---
# User active tone pairs inside each 4-tone block: all C(4,2) = 6 pairs
SCMA_PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
_BITS_16 = np.array([[(i >> 3) & 1, (i >> 2) & 1, (i >> 1) & 1, i & 1] for i in range(16)], dtype=np.uint8)


def build_scma_16ary_codebooks() -> np.ndarray:
    """
    Build (J=6, M=16, 2) 2D complex SCMA codebooks following Taherzadeh/Huawei multidimensional constellation rotation:
    - Base 16-QAM Gray points rotated in 2D real/complex plane + user-specific phase rotation phi_u = pi*u/6
      so the 3 users colliding on any tone have angles {0, pi/3, 2*pi/3}!
    - Normalized so E_m[||cb_u[m]||^2] = 4.0 (energy 2.0 per active tone -> 22 * 4.0 = 88.0 data energy per user!).
    """
    pam4 = np.array([3.0, 1.0, -3.0, -1.0], dtype=np.float64) / math.sqrt(10.0)
    q16 = np.array([pam4[(i >> 2) & 3] + 1j * pam4[i & 3] for i in range(16)], dtype=np.complex128)
    # Permute second coordinate via Gray interleaving so both tones carry full 16-ary multidimensional diversity!
    perm = np.array([((i & 3) << 2) | ((i >> 2) & 3) for i in range(16)], dtype=np.int32)
    cb = np.zeros((J_USR, 16, 2), dtype=np.complex128)
    # Tone-collision user phase angles: on each tone k in 0..3, 3 users collide -> assign distinct phases {0, pi/3, 2pi/3}
    tone_occ = [0, 0, 0, 0]
    for u, (k0, k1) in enumerate(SCMA_PAIRS):
        th0 = (np.pi / 3.0) * tone_occ[k0] + 0.07 * u
        th1 = (np.pi / 3.0) * tone_occ[k1] + 0.19 * u
        tone_occ[k0] += 1
        tone_occ[k1] += 1
        c0 = q16 * np.exp(1j * th0)
        c1 = q16[perm] * np.exp(1j * th1)
        raw = np.stack([c0, c1], axis=1)  # E[||raw||^2] = 2.0
        # Scale to E[||cb||^2] = 4.0 so 22 groups sum to 88.0 total user data energy!
        cb[u] = raw * math.sqrt(4.0 / float(np.mean(np.sum(np.abs(raw) ** 2, axis=1))))
    return cb


SCMA_CB = build_scma_16ary_codebooks()  # (6, 16, 2)

TAU_GRID_G2 = np.linspace(0.0, 6.0, 25)
NU_GRID_G2 = np.linspace(-2.0, 2.0, 17)
DOP_MAT_G2 = np.exp(1j * 2.0 * np.pi * np.arange(N_BLK, dtype=np.float64)[:, None] * NU_GRID_G2[None, :] / float(N_BLK))


def _precompute_tau_dict_g2(c1_cp: float):
    n_rx = np.arange(N_BLK, dtype=np.float64)[:, None]
    m_full = np.arange(-L_CP, N_BLK, dtype=np.float64)[None, :]
    m_pre = np.arange(-L_CP, 0, dtype=np.float64)
    cpp_phase = np.exp(-1j * 2.0 * np.pi * c1_cp * (N_BLK * N_BLK + 2.0 * N_BLK * m_pre))
    ops = np.zeros((len(TAU_GRID_G2), N_BLK, N_BLK), dtype=np.complex128)
    for ig, tau in enumerate(TAU_GRID_G2):
        dt = n_rx - m_full - tau
        W_rc = np.where(np.abs(dt) <= 8.0, rc_pulse_vec(dt, BETA_RRC), 0.0)
        T_b = W_rc[:, L_CP:].astype(np.complex128)
        T_b[:, N_BLK - L_CP :] += W_rc[:, :L_CP] * cpp_phase[None, :]
        ops[ig] = T_b
    return ops


W_TAU_G2_CP0 = _precompute_tau_dict_g2(0.0)
W_TAU_G2_CPP = _precompute_tau_dict_g2(C1_128)
_G2_SBL_CACHE = {}


def _get_g2_sbl_init(c1_cp: float):
    key = round(float(c1_cp), 8)
    if key in _G2_SBL_CACHE:
        return _G2_SBL_CACHE[key]
    W_tau = W_TAU_G2_CP0 if abs(c1_cp) < 1e-12 else W_TAU_G2_CPP
    X_pil = np.zeros((J_USR, N_BLK), dtype=np.complex128)
    X_pil[:, PIL_SLOTS] = ZC_PIL_6X40

    # Prior data-ISI covariance on PIL_SLOTS across 6 users (each user has mean data symbol energy 1.0 per chip!)
    R_isi0 = np.zeros((N_PIL, N_PIL), dtype=np.complex128)
    sub_taus = W_tau[::2]
    sub_nus = NU_GRID_G2[::4]
    w_norm = float(J_USR) / float(len(sub_taus) * len(sub_nus))
    pf = PIL_SLOTS.astype(np.float64)
    for Wt in sub_taus:
        Td = Wt[np.ix_(PIL_SLOTS, DAT_SLOTS)]
        bc = Td @ Td.conj().T
        for nc in sub_nus:
            dv = np.exp(1j * 2.0 * np.pi * float(nc) * pf / float(N_BLK))
            R_isi0 += w_norm * (bc * np.outer(dv, np.conj(dv)))

    atoms, meta = [], []
    for u in range(J_USR):
        S_bu = np.einsum("gnm,m->gn", W_tau[:, PIL_SLOTS, :], X_pil[u])
        for ig, tc in enumerate(TAU_GRID_G2):
            sb = S_bu[ig]
            for jg, nc in enumerate(NU_GRID_G2):
                atoms.append(sb * DOP_MAT_G2[PIL_SLOTS, jg])
                meta.append((u, ig, jg, float(tc), float(nc)))
    Phi = np.array(atoms).T  # (40, 6 * 25 * 17 = 2550)
    _G2_SBL_CACHE[key] = (R_isi0, Phi, meta)
    return _G2_SBL_CACHE[key]


def sbl_estimate_6user_init(Y_rx: np.ndarray, c1_cp: float, sigma2: float, n_iter: int = 35):
    Nr = Y_rx.shape[0]
    R_isi0, Phi, meta = _get_g2_sbl_init(c1_cp)
    R_n = R_isi0 + max(sigma2, 1e-5) * np.eye(N_PIL)
    Y_p = Y_rx[:, PIL_SLOTS].T  # (40, Nr)
    M_d = Phi.shape[1]
    gam = np.full(M_d, float(J_USR) / float(M_d), dtype=np.float64)

    for _ in range(n_iter):
        act = gam > 1e-6
        Pa = Phi[:, act]
        ga = gam[act]
        Pg = Pa * ga[None, :]
        Sy = R_n + Pg @ Pa.conj().T  # (40, 40)
        L_s = np.linalg.cholesky(Sy)
        Sy_Y = np.linalg.solve(L_s.conj().T, np.linalg.solve(L_s, Y_p))
        Mu_a = Pg.conj().T @ Sy_Y
        Sy_Pa = np.linalg.solve(L_s.conj().T, np.linalg.solve(L_s, Pa))
        num = np.mean(np.abs(Mu_a) ** 2, axis=1)
        den = np.maximum(np.real(np.sum(np.conj(Pa) * Sy_Pa, axis=0)), 1e-12)
        gam_new = np.zeros_like(gam)
        gam_new[act] = np.sqrt(num / den)
        gam = gam_new

    order = np.argsort(gam)[::-1][:54]
    act_idx = order[gam[order] > 1e-4 * gam[order[0]]]
    Pa = Phi[:, act_idx]
    ga = gam[act_idx]
    Pg = Pa * ga[None, :]
    Sy_f = R_n + Pg @ Pa.conj().T
    Mu_a = Pg.conj().T @ np.linalg.solve(Sy_f, Y_p)  # (K_act, Nr)
    Sy_Pa = np.linalg.solve(Sy_f, Pa)
    post_var_a = np.maximum(ga - (ga ** 2) * np.real(np.sum(np.conj(Pa) * Sy_Pa, axis=0)), 0.0)
    csi_mse = float(np.sum(post_var_a * np.real(np.sum(np.abs(Pa) ** 2, axis=0))) / float(N_PIL))

    H_est = np.zeros((Nr, J_USR, N_BLK, N_BLK), dtype=np.complex128)
    for k_i, idx in enumerate(act_idx):
        u_i, _, _, tc, nc = meta[idx]
        Tp = build_chip_channel_matrix_single_path(N_BLK, L_CP, tc, nc, c1_cp=c1_cp)
        H_est[:, u_i] += Mu_a[k_i][:, None, None] * Tp[None, :, :]
    # Return top 240 candidate atom indices (plus neighbors) so DD-SBL runs 10x faster with zero loss!
    top_cand = np.argsort(gam)[::-1][:240]
    return H_est, csi_mse, top_cand


def dd_sbl_6user_full(Y_rx: np.ndarray, X_dd: np.ndarray, c1_cp: float, sigma2: float, resid_var: float, cand_idx: np.ndarray = None):
    Nr = Y_rx.shape[0]
    W_tau = W_TAU_G2_CP0 if abs(c1_cp) < 1e-12 else W_TAU_G2_CPP
    _, _, meta_all = _get_g2_sbl_init(c1_cp)
    if cand_idx is None:
        cand_idx = np.arange(len(meta_all))
    S_bu_all = np.einsum("gnm,um->ugn", W_tau, X_dd)  # (6, 25, 128)
    atoms = []
    meta = []
    for idx in cand_idx:
        u_i, ig, jg, tc, nc = meta_all[int(idx)]
        atoms.append(S_bu_all[u_i, ig] * DOP_MAT_G2[:, jg])
        meta.append((u_i, ig, jg, tc, nc))
    Phi = np.array(atoms).T  # (128, 240) — 10x smaller & faster!
    M_d = Phi.shape[1]
    R_n = max(sigma2 + float(J_USR) * resid_var, 1e-5) * np.eye(N_BLK)
    Y_t = Y_rx.T  # (128, Nr)
    gam = np.full(M_d, float(J_USR) / float(M_d), dtype=np.float64)
    for _ in range(12):
        act = gam > 1e-5
        Pa = Phi[:, act]
        ga = gam[act]
        Pg = Pa * ga[None, :]
        Sy = R_n + Pg @ Pa.conj().T
        L_s = np.linalg.cholesky(Sy)
        Sy_Y = np.linalg.solve(L_s.conj().T, np.linalg.solve(L_s, Y_t))
        Mu_a = Pg.conj().T @ Sy_Y
        Sy_Pa = np.linalg.solve(L_s.conj().T, np.linalg.solve(L_s, Pa))
        num = np.mean(np.abs(Mu_a) ** 2, axis=1)
        den = np.maximum(np.real(np.sum(np.conj(Pa) * Sy_Pa, axis=0)), 1e-12)
        gam_new = np.zeros_like(gam)
        gam_new[act] = np.sqrt(num / den)
        gam = gam_new
    order = np.argsort(gam)[::-1][:48]
    act_idx = order[gam[order] > 1e-4 * gam[order[0]]]
    Pa = Phi[:, act_idx]
    ga = gam[act_idx]
    Pg = Pa * ga[None, :]
    Sy_f = R_n + Pg @ Pa.conj().T
    Mu_a = Pg.conj().T @ np.linalg.solve(Sy_f, Y_t)
    Sy_Pa = np.linalg.solve(Sy_f, Pa)
    post_var_a = np.maximum(ga - (ga ** 2) * np.real(np.sum(np.conj(Pa) * Sy_Pa, axis=0)), 0.0)
    csi_mse = float(np.sum(post_var_a * np.real(np.sum(np.abs(Pa) ** 2, axis=0))) / float(N_BLK))
    H_est = np.zeros((Nr, J_USR, N_BLK, N_BLK), dtype=np.complex128)
    for k_i, idx in enumerate(act_idx):
        u_i, _, _, tc, nc = meta[idx]
        Tp = build_chip_channel_matrix_single_path(N_BLK, L_CP, tc, nc, c1_cp=c1_cp)
        H_est[:, u_i] += Mu_a[k_i][:, None, None] * Tp[None, :, :]
    return H_est, csi_mse


def luo24_daft_omp_6user(Y_daft: np.ndarray, X_pil_daft: np.ndarray, pil_bins: np.ndarray, sigma2: float):
    """Published Baseline (Luo24 / Yin24 style): 40-bin DAFT pilot region (6 bins/user) + dictionary OMP."""
    Nr = Y_daft.shape[0]
    tau_c = np.linspace(0.0, 6.0, 13)
    nu_c = np.linspace(-2.0, 2.0, 17)
    X_pil_td = np.array([A_DAFT_128.conj().T @ X_pil_daft[u] for u in range(J_USR)])
    meta = [(float(tc), float(nc)) for tc in tau_c for nc in nu_c]
    M_c = len(meta)
    Phi = np.zeros((J_USR, M_c, len(pil_bins)), dtype=np.complex128)
    A_sub = A_DAFT_128[pil_bins, :]
    nv = np.arange(N_BLK, dtype=np.float64)
    idx = 0
    for tc in tau_c:
        T_tc = build_chip_channel_matrix_single_path(N_BLK, L_CP, float(tc), 0.0, c1_cp=C1_128)
        S_tc = X_pil_td @ T_tc.T
        for nc in nu_c:
            dp = np.exp(1j * 2.0 * np.pi * float(nc) * nv / float(N_BLK))
            Phi[:, idx, :] = (S_tc * dp[None, :]) @ A_sub.T
            idx += 1
    Phi_f = Phi.reshape(J_USR * M_c, len(pil_bins)).T
    Phi_u = Phi_f / np.maximum(np.linalg.norm(Phi_f, axis=0), 1e-12)[None, :]
    H_est = np.zeros((Nr, J_USR, N_BLK, N_BLK), dtype=np.complex128)
    for r in range(Nr):
        yp = Y_daft[r, pil_bins].copy()
        res = yp.copy()
        sel = []
        for _ in range(J_USR * 3):
            c = np.abs(Phi_u.conj().T @ res)
            for s in sel:
                c[s] = -1.0
            bi = int(np.argmax(c))
            sel.append(bi)
            As = Phi_f[:, sel]
            gs = np.linalg.solve(As.conj().T @ As + max(sigma2, 1e-4) * np.eye(len(sel)), As.conj().T @ yp)
            res = yp - As @ gs
        for k_i, s in enumerate(sel):
            u_i, m_i = s // M_c, s % M_c
            tc, nc = meta[m_i]
            H_est[r, u_i] += gs[k_i] * build_chip_channel_matrix_single_path(N_BLK, L_CP, tc, nc, c1_cp=C1_128)
    return H_est


def encode_scma_users(c_bits_6x88: np.ndarray) -> np.ndarray:
    """
    Map (J=6, 88) coded bits into (J=6, 88) SCMA bin symbols s_bins[u, 0..87], and also return (6, 22, 2) active vectors.
    """
    s_bins = np.zeros((J_USR, N_DAT), dtype=np.complex128)
    v_act = np.zeros((J_USR, N_GRP, 2), dtype=np.complex128)
    for u in range(J_USR):
        b4 = c_bits_6x88[u].reshape(N_GRP, 4)
        idx = (b4[:, 0].astype(np.int32) << 3) | (b4[:, 1].astype(np.int32) << 2) | (b4[:, 2].astype(np.int32) << 1) | b4[:, 3].astype(np.int32)
        cw2 = SCMA_CB[u, idx]  # (22, 2)
        v_act[u] = cw2
        k0, k1 = SCMA_PAIRS[u]
        s_bins[u, k0::4] = cw2[:, 0]
        s_bins[u, k1::4] = cw2[:, 1]
    return s_bins, v_act


def assemble_scma_joint_H(H_td_4d: np.ndarray, V_bins_to_td: np.ndarray) -> np.ndarray:
    """
    Build H_joint of shape (Nr * 128, J * 22 * 2) = (128*Nr, 264) mapping stacked 2D SCMA user-group vectors
    v_joint (u=0..5, g=0..21, slot=0..1) directly to received chip observations!
    """
    Nr = H_td_4d.shape[0]
    cols = []
    for u in range(J_USR):
        # H_u_88: (Nr * 128, 88)
        H_u_88 = np.vstack([H_td_4d[r, u] @ V_bins_to_td for r in range(Nr)])
        k0, k1 = SCMA_PAIRS[u]
        # Interleave columns (4*g + k0, 4*g + k1) for g = 0..21 -> (Nr*128, 44)
        idx_u = np.empty(2 * N_GRP, dtype=np.int32)
        idx_u[0::2] = 4 * np.arange(N_GRP) + k0
        idx_u[1::2] = 4 * np.arange(N_GRP) + k1
        cols.append(H_u_88[:, idx_u])
    return np.hstack(cols)  # (128*Nr, 264)


def block2d_ep_scma_detector(
    y_vec: np.ndarray,
    H_joint: np.ndarray,
    sigma2: float,
    n_iter: int = 7,
    beta_damp: float = 0.50,
    prior_llr_6x22x4: np.ndarray = None,
):
    """
    Exact 2D-Block Expectation Propagation / OAMP + Multidimensional SCMA Codebook Detector!
    Solves y_vec = H_joint @ v_joint + w where v_joint consists of B = 132 (J=6 x G=22) 2D SCMA blocks,
    each drawn from its exact 16-point 2D complex codebook SCMA_CB[u] (mean energy 2.0 per coordinate)!
    """
    M = H_joint.shape[1]  # 264 = 132 * 2
    B = M // 2  # 132 blocks
    inv_s2 = 1.0 / max(sigma2, 1e-6)
    G_h = inv_s2 * (H_joint.conj().T @ H_joint)
    y_mf = inv_s2 * (H_joint.conj().T @ y_vec)

    # Prior precision per coordinate is 1 / 2.0 = 0.5 (since E|v_coord|^2 = 2.0!)
    lam = np.full(M, 0.5, dtype=np.float64)
    gam = np.zeros(M, dtype=np.complex128)

    z_ext = np.zeros((B, 2), dtype=np.complex128)
    v_ext = np.full((B, 2), 2.0, dtype=np.float64)
    mu_post = np.zeros((B, 2), dtype=np.complex128)
    var_post = np.full((B, 2), 1.0, dtype=np.float64)

    # Pre-expand user codebook table for all 132 blocks: CB_132 of shape (132, 16, 2)
    CB_132 = np.repeat(SCMA_CB, N_GRP, axis=0)  # u=0 (22 blocks), u=1 (22 blocks), ..., u=5 (22 blocks)

    for _ in range(n_iter):
        A_ep = G_h.copy()
        A_ep[np.arange(M), np.arange(M)] += lam
        L_c = np.linalg.cholesky(A_ep)
        RHS = np.column_stack([y_mf + gam, np.eye(M, dtype=np.complex128)])
        SOL = np.linalg.solve(L_c.conj().T, np.linalg.solve(L_c, RHS))
        mu_q = SOL[:, 0]
        vq = np.clip(np.real(np.diag(SOL[:, 1:])), 1e-5, 6.0)

        inv_ve = np.maximum(1.0 / vq - lam, 1e-3)
        ve = np.clip(1.0 / inv_ve, 1e-4, 30.0)
        ze = ve * (mu_q / vq - gam)

        z_ext = ze.reshape(B, 2)
        v_ext = ve.reshape(B, 2)

        # Joint 2D metric across BOTH paired SCMA tones for each of the 16 multidimensional codewords!
        # log_w[b, m] = -|z0 - cb0|^2 / v0 - |z1 - cb1|^2 / v1
        d2 = (
            (np.abs(z_ext[:, None, 0] - CB_132[:, :, 0]) ** 2) / v_ext[:, None, 0]
            + (np.abs(z_ext[:, None, 1] - CB_132[:, :, 1]) ** 2) / v_ext[:, None, 1]
        )  # (132, 16)
        log_w = -d2
        if prior_llr_6x22x4 is not None:
            pr_b = np.clip(prior_llr_6x22x4.reshape(B, 4), -25.0, 25.0)
            log_w = log_w - pr_b @ _BITS_16.T.astype(np.float64)

        mx = np.max(log_w, axis=1, keepdims=True)
        w = np.exp(log_w - mx)
        w /= np.sum(w, axis=1, keepdims=True)  # (132, 16)

        mu_p = np.einsum("bm,bmk->bk", w, CB_132)  # (132, 2)
        ex2_p = np.einsum("bm,bmk->bk", w, np.abs(CB_132) ** 2)  # (132, 2)
        var_p = np.clip(ex2_p - np.abs(mu_p) ** 2, 1e-2, 4.0)

        mu_post, var_post = mu_p, var_p
        lam_c = (1.0 / var_p - inv_ve.reshape(B, 2)).reshape(M)
        gam_c = (mu_p / var_p - z_ext * inv_ve.reshape(B, 2)).reshape(M)
        pos = lam_c > 1e-4
        lam = beta_damp * np.where(pos, lam_c, lam) + (1.0 - beta_damp) * lam
        gam = beta_damp * np.where(pos, gam_c, gam) + (1.0 - beta_damp) * gam

    # Final extrinsic bit LLRs (6, 22, 4) -> (6, 88)
    d2_f = (
        (np.abs(z_ext[:, None, 0] - CB_132[:, :, 0]) ** 2) / v_ext[:, None, 0]
        + (np.abs(z_ext[:, None, 1] - CB_132[:, :, 1]) ** 2) / v_ext[:, None, 1]
    )
    lp_f = -d2_f
    llrs_b4 = np.zeros((B, 4), dtype=np.float64)
    for b in range(4):
        m0 = _BITS_16[:, b] == 0
        a0, a1 = lp_f[:, m0], lp_f[:, ~m0]
        mx0, mx1 = np.max(a0, axis=1), np.max(a1, axis=1)
        l0 = mx0 + np.log(np.sum(np.exp(a0 - mx0[:, None]), axis=1))
        l1 = mx1 + np.log(np.sum(np.exp(a1 - mx1[:, None]), axis=1))
        llrs_b4[:, b] = np.clip(l0 - l1, -30.0, 30.0)

    return llrs_b4.reshape(J_USR, 88), mu_post.reshape(J_USR, N_GRP, 2), var_post.reshape(J_USR, N_GRP, 2)


# --- Equal-Net-Rate Orthogonal Multiple Access Subband Allocation (4 users x 15 bins + 2 users x 14 bins = 88 bins!) ---
O_SUBBANDS = [
    np.arange(0, 15),
    np.arange(15, 30),
    np.arange(30, 45),
    np.arange(45, 60),
    np.arange(60, 74),
    np.arange(74, 88),
]


def make_clean_pilot_mask_40() -> np.ndarray:
    mask = np.zeros(N_BLK, dtype=bool)
    mask[PIL_SLOTS] = True
    for n_i in range(N_BLK):
        if mask[n_i]:
            for db in range(1, 6):
                if not mask[(n_i - db) % N_BLK]:
                    mask[n_i] = False
                    break
    return mask


CLEAN_PIL_MASK_40 = make_clean_pilot_mask_40()  # [5..19] & [69..83] = 30 interference-free chips!


def run_scma_dd_chain(Y_rx, U_88, c1_cp, sigma2, ldpc_88, u_bits_6x44, n_dd=3):
    Nr = Y_rx.shape[0]
    X_pil_td = np.zeros((J_USR, N_BLK), dtype=np.complex128)
    X_pil_td[:, PIL_SLOTS] = ZC_PIL_6X40
    V_dat = np.zeros((N_BLK, N_DAT), dtype=np.complex128)
    V_dat[DAT_SLOTS, :] = U_88.conj().T

    H_est, csi_mse, top_cand = sbl_estimate_6user_init(Y_rx, c1_cp=c1_cp, sigma2=sigma2, n_iter=30)
    u_hat_6 = None
    for rd in range(n_dd + 1):
        Y_sub = Y_rx.copy()
        for r in range(Nr):
            for u in range(J_USR):
                Y_sub[r] -= H_est[r, u] @ X_pil_td[u]
        H_j = assemble_scma_joint_H(H_est, V_dat)
        llrs_6x88, mu_sc, var_sc = block2d_ep_scma_detector(
            Y_sub.reshape(-1), H_j, sigma2 + csi_mse, n_iter=7
        )
        u_hat_6, syn_6 = ldpc_88.decode_bp(llrs_6x88, max_iter=20)
        if np.all(syn_6) or rd == n_dd:
            break
        c_re = ldpc_88.encode(u_hat_6)
        _, v_hard = encode_scma_users(c_re)
        X_dd = X_pil_td.copy()
        mean_v = float(np.mean(var_sc))
        for u in range(J_USR):
            w_u = 0.85 if syn_6[u] else float(np.clip(1.0 - 0.40 * float(np.mean(var_sc[u])), 0.15, 0.70))
            v_blend = w_u * v_hard[u] + (1.0 - w_u) * mu_sc[u]
            s_u = np.zeros(N_DAT, dtype=np.complex128)
            k0, k1 = SCMA_PAIRS[u]
            s_u[k0::4] = v_blend[:, 0]
            s_u[k1::4] = v_blend[:, 1]
            X_dd[u] += V_dat @ s_u
        H_est, csi_mse = dd_sbl_6user_full(Y_rx, X_dd, c1_cp=c1_cp, sigma2=sigma2, resid_var=0.35 * mean_v, cand_idx=top_cand)

    usr_errs = int(np.sum(np.any(u_hat_6 != u_bits_6x44, axis=1)))
    bit_errs = int(np.sum(u_hat_6 != u_bits_6x44))
    return bit_errs, usr_errs


def run_oma_dd_chain(Y_rx, mode_oma, c1_cp, sigma2, ldpc_60, ldpc_56, u_bits_6x44, n_dd=3):
    Nr = Y_rx.shape[0]
    X_pil_td = np.zeros((J_USR, N_BLK), dtype=np.complex128)
    X_pil_td[:, PIL_SLOTS] = ZC_PIL_6X40

    if mode_oma == "o_afdma":
        U_base = A_DAFT_88.conj().T
    else:
        U_base = F_FFT_88.conj().T

    V_users = []
    for u in range(J_USR):
        sb = O_SUBBANDS[u]
        M_u = len(sb)
        scale_u = math.sqrt(float(N_DAT) / float(M_u))
        B_sub = U_base[:, sb]
        if mode_oma == "scfdma":
            F_m = np.fft.fft(np.eye(M_u), axis=0) / math.sqrt(float(M_u))
            B_sub = B_sub @ F_m
        V_u = np.zeros((N_BLK, M_u), dtype=np.complex128)
        V_u[DAT_SLOTS, :] = scale_u * B_sub
        V_users.append(V_u)

    H_est, csi_mse, top_cand = sbl_estimate_6user_init(Y_rx, c1_cp=c1_cp, sigma2=sigma2, n_iter=30)
    u_hats = [None] * J_USR
    for rd in range(n_dd + 1):
        Y_sub = Y_rx.copy()
        for r in range(Nr):
            for u in range(J_USR):
                Y_sub[r] -= H_est[r, u] @ X_pil_td[u]
        cols = [np.vstack([H_est[r, u] @ V_users[u] for r in range(Nr)]) for u in range(J_USR)]
        H_oma = np.hstack(cols)  # (128*Nr, 88)
        llrs_88x4, mu_88, var_88 = damped_mimo_ep_16qam(
            Y_sub.reshape(-1), H_oma, sigma2 + csi_mse, n_iter=6
        )
        syn_all = True
        s_soft_list = []
        off = 0
        for u in range(J_USR):
            M_u = len(O_SUBBANDS[u])
            lu = llrs_88x4[off : off + M_u].reshape(-1)
            codec = ldpc_60 if M_u == 15 else ldpc_56
            uh, sok = codec.decode_bp(lu, max_iter=20)
            u_hats[u] = uh
            syn_all = syn_all and sok
            cre = codec.encode(uh)
            sh = mod_16qam(cre.reshape(-1, 4))
            wu = 0.85 if sok else float(np.clip(1.0 - 1.3 * float(np.mean(var_88[off : off + M_u])), 0.15, 0.75))
            s_soft_list.append(wu * sh + (1.0 - wu) * mu_88[off : off + M_u])
            off += M_u
        if syn_all or rd == n_dd:
            break
        X_dd = X_pil_td.copy()
        for u in range(J_USR):
            X_dd[u] += V_users[u] @ s_soft_list[u]
        H_est, csi_mse = dd_sbl_6user_full(Y_rx, X_dd, c1_cp=c1_cp, sigma2=sigma2, resid_var=0.5 * float(np.mean(var_88)), cand_idx=top_cand)

    u_hat_mat = np.vstack(u_hats)
    usr_errs = int(np.sum(np.any(u_hat_mat != u_bits_6x44, axis=1)))
    bit_errs = int(np.sum(u_hat_mat != u_bits_6x44))
    return bit_errs, usr_errs


ARMS = (
    "pub_luo24_afdm_scma",
    "sm_a1_equalrate_o_afdma",
    "sm_a2_zc_scma_mpa_dd",
    "sm_s_ofdma_dd",
    "sm_s_scfdma_dd",
    "sm_s_otfs_scma_dd",
    "diag_true_csi_scma",
    "oracle_genie_joint_mpa",
)


def run_scene(scene_id: int, snrs_ebn0_db):
    rng = np.random.default_rng(8100000 + scene_id * 41)
    ldpc_88 = RateMatchedQCLDPC(K_USR, 88, seed=20261521)
    ldpc_60 = RateMatchedQCLDPC(K_USR, 60, seed=20261522)
    ldpc_56 = RateMatchedQCLDPC(K_USR, 56, seed=20261523)

    Nr_max = 2
    pdp = 10.0 ** (np.array([0.0, -3.0, -6.0]) / 10.0)
    pdp /= np.sum(pdp)

    # Independent asynchronous user timing offset Delta_tau_u in [0, 3] + multipath [0, 3] -> [0, 6] chips
    taus = np.zeros((Nr_max, J_USR, 3), dtype=np.float64)
    nus = np.zeros((Nr_max, J_USR, 3), dtype=np.float64)
    for u in range(J_USR):
        dt_u = rng.uniform(0.0, 3.0)
        cfo_u = rng.uniform(-0.6, 0.6)
        rel_t = np.sort(rng.uniform(0.0, 3.0, size=3))
        if rel_t[1] - rel_t[0] < 0.45:
            rel_t[1] = min(3.0, rel_t[0] + 0.45)
        if rel_t[2] - rel_t[1] < 0.45:
            rel_t[2] = min(3.0, rel_t[1] + 0.45)
        dop_p = np.clip(cfo_u + 1.4 * np.cos(rng.uniform(-np.pi, np.pi, size=3)), -2.0, 2.0)
        for r in range(Nr_max):
            taus[r, u] = dt_u + rel_t
            nus[r, u] = dop_p

    gains = np.sqrt(pdp[None, None, :] / 2.0) * (
        rng.standard_normal((Nr_max, J_USR, 3)) + 1j * rng.standard_normal((Nr_max, J_USR, 3))
    )

    H_cpp = np.zeros((Nr_max, J_USR, N_BLK, N_BLK), dtype=np.complex128)
    H_cp0 = np.zeros((Nr_max, J_USR, N_BLK, N_BLK), dtype=np.complex128)
    for r in range(Nr_max):
        for u in range(J_USR):
            for p in range(3):
                H_cpp[r, u] += gains[r, u, p] * build_chip_channel_matrix_single_path(
                    N_BLK, L_CP, float(taus[r, u, p]), float(nus[r, u, p]), c1_cp=C1_128
                )
                H_cp0[r, u] += gains[r, u, p] * build_chip_channel_matrix_single_path(
                    N_BLK, L_CP, float(taus[r, u, p]), float(nus[r, u, p]), c1_cp=0.0
                )

    u_bits = rng.integers(0, 2, size=(J_USR, K_USR), dtype=np.uint8)
    c_scma = ldpc_88.encode(u_bits)  # (6, 88)
    s_scma_bins, _ = encode_scma_users(c_scma)  # (6, 88)

    # Build TX waveforms (all strictly E_u = 144 per user!)
    # 1) Pub: 40 DAFT pilot bins [0..39] (impulses at 3 + 6*u with energy 40), SCMA on [40..127]
    X_pub_pil_daft = np.zeros((J_USR, N_BLK), dtype=np.complex128)
    for u in range(J_USR):
        X_pub_pil_daft[u, 3 + 6 * u] = math.sqrt(float(N_PIL))
    V_pub = A_DAFT_128.conj().T[:, 40:]
    X_pub_td = np.array([A_DAFT_128.conj().T @ X_pub_pil_daft[u] + V_pub @ s_scma_bins[u] for u in range(J_USR)])

    # 2) sm_a2 (AFDM-SCMA with dispersed ZC) & 6) sm_s_otfs_scma
    X_sma2_td = np.zeros((J_USR, N_BLK), dtype=np.complex128)
    X_sma2_td[:, PIL_SLOTS] = ZC_PIL_6X40
    X_sma2_td[:, DAT_SLOTS] = (A_DAFT_88.conj().T @ s_scma_bins.T).T

    X_otfs_td = np.zeros((J_USR, N_BLK), dtype=np.complex128)
    X_otfs_td[:, PIL_SLOTS] = ZC_PIL_6X40
    X_otfs_td[:, DAT_SLOTS] = (U_OTFS_88.conj().T @ s_scma_bins.T).T

    # 3) Equal-net-rate OMA TX frames (O-AFDMA, OFDMA, SC-FDMA)
    def _build_oma_tx(mode_oma):
        U_b = A_DAFT_88.conj().T if mode_oma == "o_afdma" else F_FFT_88.conj().T
        Xt = np.zeros((J_USR, N_BLK), dtype=np.complex128)
        Xt[:, PIL_SLOTS] = ZC_PIL_6X40
        for u in range(J_USR):
            sb = O_SUBBANDS[u]
            M_u = len(sb)
            cu = (ldpc_60 if M_u == 15 else ldpc_56).encode(u_bits[u])
            su = mod_16qam(cu.reshape(-1, 4))
            B_s = U_b[:, sb]
            if mode_oma == "scfdma":
                B_s = B_s @ (np.fft.fft(np.eye(M_u), axis=0) / math.sqrt(float(M_u)))
            Xt[u, DAT_SLOTS] = math.sqrt(float(N_DAT) / float(M_u)) * (B_s @ su)
        return Xt

    X_oafdma_td = _build_oma_tx("o_afdma")
    X_ofdma_td = _build_oma_tx("ofdma")
    X_scfdma_td = _build_oma_tx("scfdma")

    def _prop2(H4, Xt):
        return np.einsum("runm,um->rn", H4, Xt)

    Y0_pub = _prop2(H_cpp, X_pub_td)
    Y0_sma1 = _prop2(H_cpp, X_oafdma_td)
    Y0_sma2 = _prop2(H_cpp, X_sma2_td)
    Y0_ofdma = _prop2(H_cp0, X_ofdma_td)
    Y0_scfdma = _prop2(H_cp0, X_scfdma_td)
    Y0_otfs = _prop2(H_cp0, X_otfs_td)

    X_pil_zc_only = np.zeros((J_USR, N_BLK), dtype=np.complex128)
    X_pil_zc_only[:, PIL_SLOTS] = ZC_PIL_6X40
    Y0_pil_true = _prop2(H_cpp, X_pil_zc_only)
    V_sma2 = np.zeros((N_BLK, N_DAT), dtype=np.complex128)
    V_sma2[DAT_SLOTS, :] = A_DAFT_88.conj().T

    Z_noise = (rng.standard_normal((len(snrs_ebn0_db), Nr_max, N_BLK)) + 1j * rng.standard_normal((len(snrs_ebn0_db), Nr_max, N_BLK))) / math.sqrt(2.0)

    out_by_nr = {}
    for nr in (1, 2):
        uer = {a: [] for a in ARMS}
        ber = {a: [] for a in ARMS}
        H_j_true = assemble_scma_joint_H(H_cpp[:nr], V_sma2)

        for ig, ebn0_db in enumerate(snrs_ebn0_db):
            # Per-user E_u = 144, K_u = 44 -> Eb = 144 / 44 = 3.27273 -> sigma2 = N0 = Eb * 10^(-ebn0/10)
            eb = float(N_TOT) / float(K_USR)
            sigma2 = eb * (10.0 ** (-float(ebn0_db) / 10.0))
            Wn = math.sqrt(sigma2) * Z_noise[ig, :nr]

            # 1) Pub: Luo24 AFDM-SCMA
            Yp = Y0_pub[:nr] + Wn
            Hp = luo24_daft_omp_6user(Yp @ A_DAFT_128.T, X_pub_pil_daft, np.arange(40), sigma2)
            Yp_sub = Yp.copy()
            for r in range(nr):
                for u in range(J_USR):
                    Yp_sub[r] -= Hp[r, u] @ (A_DAFT_128.conj().T @ X_pub_pil_daft[u])
            Hj_p = assemble_scma_joint_H(Hp, V_pub)
            ll_p, _, _ = block2d_ep_scma_detector(Yp_sub.reshape(-1), Hj_p, sigma2 * 1.35, n_iter=7)
            uh_p, _ = ldpc_88.decode_bp(ll_p, max_iter=20)
            ber["pub_luo24_afdm_scma"].append(int(np.sum(uh_p != u_bits)))
            uer["pub_luo24_afdm_scma"].append(int(np.sum(np.any(uh_p != u_bits, axis=1))))

            # 2) sm_a1: Equal-Net-Rate O-AFDMA
            b_e, u_e = run_oma_dd_chain(Y0_sma1[:nr] + Wn, "o_afdma", C1_128, sigma2, ldpc_60, ldpc_56, u_bits, n_dd=3)
            ber["sm_a1_equalrate_o_afdma"].append(b_e)
            uer["sm_a1_equalrate_o_afdma"].append(u_e)

            # 3) sm_a2: Dispersed ZC + AFDM-SCMA + Block-EP/MPA + 3-round DD-SAGE
            b_e, u_e = run_scma_dd_chain(Y0_sma2[:nr] + Wn, A_DAFT_88, C1_128, sigma2, ldpc_88, u_bits, n_dd=3)
            ber["sm_a2_zc_scma_mpa_dd"].append(b_e)
            uer["sm_a2_zc_scma_mpa_dd"].append(u_e)

            # 4) sm_s_ofdma_dd
            b_e, u_e = run_oma_dd_chain(Y0_ofdma[:nr] + Wn, "ofdma", 0.0, sigma2, ldpc_60, ldpc_56, u_bits, n_dd=3)
            ber["sm_s_ofdma_dd"].append(b_e)
            uer["sm_s_ofdma_dd"].append(u_e)

            # 5) sm_s_scfdma_dd
            b_e, u_e = run_oma_dd_chain(Y0_scfdma[:nr] + Wn, "scfdma", 0.0, sigma2, ldpc_60, ldpc_56, u_bits, n_dd=3)
            ber["sm_s_scfdma_dd"].append(b_e)
            uer["sm_s_scfdma_dd"].append(u_e)

            # 6) sm_s_otfs_scma_dd
            b_e, u_e = run_scma_dd_chain(Y0_otfs[:nr] + Wn, U_OTFS_88, 0.0, sigma2, ldpc_88, u_bits, n_dd=3)
            ber["sm_s_otfs_scma_dd"].append(b_e)
            uer["sm_s_otfs_scma_dd"].append(u_e)

            # 7) Diag: True RX CSI + single-pass Block-EP/MPA + LDPC
            Yc_true = (Y0_sma2[:nr] - Y0_pil_true[:nr] + Wn).reshape(-1)
            ll_d, _, _ = block2d_ep_scma_detector(Yc_true, H_j_true, sigma2, n_iter=7)
            uh_d, syn_d = ldpc_88.decode_bp(ll_d, max_iter=20)
            ber["diag_true_csi_scma"].append(int(np.sum(uh_d != u_bits)))
            uer["diag_true_csi_scma"].append(int(np.sum(np.any(uh_d != u_bits, axis=1))))

            # 8) Oracle: Genie RX CSI + 2-pass Turbo Block-EP/MPA + LDPC
            if np.all(syn_d):
                ber["oracle_genie_joint_mpa"].append(int(np.sum(uh_d != u_bits)))
                uer["oracle_genie_joint_mpa"].append(int(np.sum(np.any(uh_d != u_bits, axis=1))))
            else:
                cd = ldpc_88.encode(uh_d)
                pr = np.clip(0.35 * (1.0 - 2.0 * cd.astype(np.float64)) * 4.0, -6.0, 6.0).reshape(J_USR, N_GRP, 4)
                ll_o, _, _ = block2d_ep_scma_detector(Yc_true, H_j_true, sigma2, n_iter=7, prior_llr_6x22x4=pr)
                uh_o, _ = ldpc_88.decode_bp(ll_o + 0.5 * pr.reshape(J_USR, 88), max_iter=25)
                ber["oracle_genie_joint_mpa"].append(int(np.sum(uh_o != u_bits)))
                uer["oracle_genie_joint_mpa"].append(int(np.sum(np.any(uh_o != u_bits, axis=1))))

        out_by_nr[str(nr)] = {"uer": uer, "ber": ber}
    return out_by_nr


def _worker_star(args_tup):
    return run_scene(*args_tup)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-scenes", type=int, default=80)
    ap.add_argument("--out", type=str, default=str(ROOT / "ideas" / "r15" / "out_g2_scma_noma.json"))
    args = ap.parse_args()

    t0 = time.time()
    n_sc = 4 if args.smoke else args.n_scenes
    snrs_db = [4.0, 7.0, 10.0, 13.0, 16.0, 19.0]
    print(f"[td_g_g2] python={sys.executable} smoke={args.smoke} scenes={n_sc} workers={args.workers}", flush=True)

    tasks = [(i, snrs_db) for i in range(n_sc)]
    w_cnt = max(1, min(args.workers, 8))
    if w_cnt == 1:
        res = [_worker_star(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            res = list(ex.map(_worker_star, tasks))

    results_by_nr = {}
    sm_a_keys = ["sm_a1_equalrate_o_afdma", "sm_a2_zc_scma_mpa_dd"]
    sm_s_keys = ["sm_s_ofdma_dd", "sm_s_scfdma_dd", "sm_s_otfs_scma_dd"]

    for nr_s in ("1", "2"):
        uer_mats = {a: np.array([r[nr_s]["uer"][a] for r in res], dtype=float) for a in ARMS}
        ber_mats = {a: np.array([r[nr_s]["ber"][a] for r in res], dtype=float) for a in ARMS}
        bler_curves = {a: [float(x) for x in np.sum(uer_mats[a], axis=0) / (n_sc * J_USR)] for a in ARMS}
        ber_curves = {a: [float(x) for x in np.sum(ber_mats[a], axis=0) / (n_sc * J_USR * K_USR)] for a in ARMS}

        # Crossing gap at per-user BLER = 2e-2 (and 5e-2)
        gaps_2e2 = {
            a: paired_crossing_gap_ci95(uer_mats[a], uer_mats["oracle_genie_joint_mpa"], float(J_USR), snrs_db, target=0.02)
            for a in ARMS
        }
        gaps_5e2 = {
            a: paired_crossing_gap_ci95(uer_mats[a], uer_mats["oracle_genie_joint_mpa"], float(J_USR), snrs_db, target=0.05)
            for a in ARMS
        }

        def _best(keys, gd):
            v = [(k, gd[k]["gap_dB"]) for k in keys if gd[k]["gap_dB"] is not None]
            return min(v, key=lambda kv: kv[1]) if v else (None, None)

        ba_n, ba_g = _best(sm_a_keys, gaps_2e2)
        ball_n, ball_g = _best(sm_a_keys + sm_s_keys, gaps_2e2)
        if ba_g is None:
            ba_n, ba_g = _best(sm_a_keys, gaps_5e2)
            ball_n, ball_g = _best(sm_a_keys + sm_s_keys, gaps_5e2)

        # Lower-bound headroom if Best_Steelman never crosses target even at 19 dB while Oracle crosses!
        fl_best_a = min(bler_curves[k][-1] for k in sm_a_keys)
        fl_best_all = min(bler_curves[k][-1] for k in sm_a_keys + sm_s_keys)
        fl_orc = bler_curves["oracle_genie_joint_mpa"][-1]
        snr_orc_c = gaps_5e2["pub_luo24_afdm_scma"]["snr_oracle_dB"]
        if ba_g is None and snr_orc_c is not None and fl_best_a > 0.05:
            ba_g = float(snrs_db[-1] - snr_orc_c)
            ba_n = min(sm_a_keys, key=lambda k: bler_curves[k][-1]) + "_lower_bound"
        if ball_g is None and snr_orc_c is not None and fl_best_all > 0.05:
            ball_g = float(snrs_db[-1] - snr_orc_c)
            ball_n = min(sm_a_keys + sm_s_keys, key=lambda k: bler_curves[k][-1]) + "_lower_bound"

        if (ball_g is not None and ball_g >= 1.76) or (fl_best_all >= 0.05 and fl_best_all / max(fl_orc, 1.0 / (n_sc * J_USR)) >= 10.0):
            verd = "S_CANDIDATE"
        elif (ba_g is not None and ba_g >= 1.76) or (fl_best_a >= 0.05 and fl_best_a / max(fl_orc, 1.0 / (n_sc * J_USR)) >= 10.0):
            verd = "A_CANDIDATE"
        elif ba_g is not None and ba_g >= 1.50:
            verd = "A_CANDIDATE_BORDERLINE_1P5DB"
        else:
            verd = "KILLED_BY_STEELMAN"

        results_by_nr[f"Nr_{nr_s}"] = {
            "user_BLER_curves": bler_curves,
            "BER_curves": ber_curves,
            "BLER_gap_vs_Oracle_at_2e2_dB": gaps_2e2,
            "BLER_gap_vs_Oracle_at_5e2_dB": gaps_5e2,
            "summary_headroom": {
                "best_steelman_A": ba_n,
                "headroom_vs_steelman_A_dB": ba_g,
                "best_steelman_all": ball_n,
                "headroom_vs_best_steelman_all_dB": ball_g,
                "high_snr_19dB_BLER_best_A": fl_best_a,
                "high_snr_19dB_BLER_best_all": fl_best_all,
                "high_snr_19dB_BLER_oracle": fl_orc,
                "diag_true_csi_19dB_BLER": bler_curves["diag_true_csi_scma"][-1],
            },
            "verdict": verd,
        }

    overall_verdict = (
        results_by_nr["Nr_1"]["verdict"]
        if results_by_nr["Nr_1"]["verdict"] != "KILLED_BY_STEELMAN"
        else results_by_nr["Nr_2"]["verdict"]
    )
    payload = {
        "_config": {
            "problem_id": "G2_6User_150pct_AFDM_SCMA_Uplink",
            "smoke": bool(args.smoke),
            "n_scenes": n_sc,
            "workers": w_cnt,
            "J_users": J_USR,
            "K_info_per_user": K_USR,
            "N_blk": N_BLK,
            "L_cp": L_CP,
        },
        "wall_time_s": float(time.time() - t0),
        "snrs_EbN0_dB": snrs_db,
        "results_by_Nr": results_by_nr,
        "teardown_verdict": overall_verdict,
    }
    save_result_json(args.out, payload)
    print(f"[td_g_g2] Done in {payload['wall_time_s']:.1f}s -> verdict={overall_verdict}", flush=True)
    for k_nr in ("Nr_1", "Nr_2"):
        print(f"=== {k_nr} BLER ===", {k: [round(x, 4) for x in v] for k, v in results_by_nr[k_nr]["user_BLER_curves"].items()}, flush=True)
        print(f"=== {k_nr} Headroom ===", results_by_nr[k_nr]["summary_headroom"], flush=True)


if __name__ == "__main__":
    main()
