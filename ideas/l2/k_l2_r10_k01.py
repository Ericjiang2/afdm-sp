#!/usr/bin/env python3
"""
L2 Decisive Pre-registered Experiment for Card k01:
Ridge-Matched AFDM (c1 = mu/(2N)) for Bistatic Moving-Platform ISAC Under Slanted 3D Ground Clutter.

Implements ALL Sol Gate #4 First-Knife Requirements:
  1. Waveform-agnostic OSR=8 RRC (beta=0.25) continuous-time channel (ZERO dechirp shortcut, full M-symbol ISI).
  2. True 3D bistatic air-to-ground geometry (L_q = R_T + R_R, f_D = -(fc/c) dL/dt, 2D swath beamwidth, realistic 25 m/s car).
  3. Equal 99% occupied BW (Ridge-AFDM 193 active bins vs OFDM 223 active bins — strictly favoring OFDM), equal L_cp=16, equal TX energy.
  4. All strong equal-overhead (12.5%) OFDM rivals:
       - OFDM-Comb (Same Band-3 + 1-col LOS Soft-EM frontend)
       - DBU/Group-Precoded OFDM (arXiv:2604.10296, data-block unitary precoding + Same Soft-EM)
       - OFDM-BlkPil(1/8) MultiSym-JointEM (Sol's strongest steelman: clean full-symbol pilot m=0 + joint M-symbol stacked 3D-ridge EM + EP)
     Plus scope readouts: KnownS-OFDM, KnownS-RidgeAFDM, OFDM-GenieInit, OFDM-2Pil(25%), S2_WeakLOS, S3_ModClut, slope mismatch 1%/2%.
  5. Independent target-free calibration set -> empirical P_fa = 1e-3 threshold -> SEPARATE target-free validation set with binomial CI.
  6. Paired target scenes -> paired bootstrap 95% CI on delta_SCNR, 2x2 DiD, and non-saturated delta_Pd.
"""
import sys
print(f"sys.executable: {sys.executable}", flush=True)

import argparse
import json
import math
import os
import time
from multiprocessing import Pool
import numpy as np
import scipy.linalg as la

c0 = 3e8
CONST16 = (np.array([-3, -1, 1, 3])[:, None] + 1j * np.array([-3, -1, 1, 3])[None, :]).ravel() / np.sqrt(10.0)

# Fixed Physical System Parameters (3D Air-to-Ground W-band Bistatic ISAC)
N = 256
L_CP = 16
STRIDE = N + L_CP
M_SYM = 8
K_COMB = 8
OSR = 8
BETA_RRC = 0.25
SPAN_RRC = 12
FC = 77.0e9
DF = 5000.0
P_T = np.array([0.0, 0.0, 6000.0])
V_T_MOV = np.array([220.0, 0.0, 0.0])
P_R = np.array([3500.0, 0.0, 20.0])
X0, X1, WY = 3800.0, 5300.0, 100.0
P_TARG = np.array([4500.0, 0.0, 0.0])
V_TARG = np.array([-25.0, 0.0, 0.0])  # 90 km/h ground vehicle
N_CLUT = 30


def rrc_filter(osr=OSR, beta=BETA_RRC, span=SPAN_RRC):
    t = np.arange(-span * osr // 2, span * osr // 2 + 1) / float(osr)
    h = np.zeros_like(t, dtype=np.float64)
    for i, ti in enumerate(t):
        if abs(ti) < 1e-12:
            h[i] = 1.0 - beta + 4.0 * beta / np.pi
        elif beta > 0 and abs(abs(ti) - 1.0 / (4.0 * beta)) < 1e-9:
            h[i] = (beta / np.sqrt(2.0)) * (
                (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * beta))
                + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * beta))
            )
        else:
            h[i] = (
                np.sin(np.pi * ti * (1.0 - beta)) + 4.0 * beta * ti * np.cos(np.pi * ti * (1.0 + beta))
            ) / (np.pi * ti * (1.0 - (4.0 * beta * ti) ** 2))
    return h / np.sqrt(np.sum(h ** 2))


def bistatic_3d(x_q, y_q, z_q, v_T):
    dT = np.stack([x_q - P_T[0], y_q - P_T[1], z_q - P_T[2]], axis=-1)
    dR = np.stack([x_q - P_R[0], y_q - P_R[1], z_q - P_R[2]], axis=-1)
    RT = np.linalg.norm(dT, axis=-1)
    RR = np.linalg.norm(dR, axis=-1)
    L_LOS = np.linalg.norm(P_R - P_T)
    Ts = 1.0 / (N * DF)
    tau = (RT + RR - L_LOS) / (c0 * Ts)
    nu = (FC / c0) * (np.sum(dT * v_T[None, :], axis=-1) / RT) / DF
    nu_los = float((FC / c0) * (np.dot(P_R - P_T, v_T) / L_LOS) / DF)
    return tau, nu, nu_los


# Precompute geometry & constant operators (read-only globals shared cleanly across fork workers)
H_RRC = rrc_filter()
N_IDX = np.arange(N)
NC_IDX = N_IDX - N / 2.0
K_SIGNED = np.fft.fftfreq(N) * N
F_MAT = np.fft.fft(np.eye(N), axis=0, norm="ortho")

XQ_GRID = np.linspace(X0, X1, 200)
TAU_G3, NU_G3, NU_LOS_MOV = bistatic_3d(XQ_GRID, np.zeros(200), np.zeros(200), V_T_MOV)
MU_MOV, B_MOV = [float(v) for v in np.polyfit(TAU_G3, NU_G3, 1)]
C1_MOV = MU_MOV / (2.0 * N)
DNU_LOS_MOV = NU_LOS_MOV - B_MOV

TAU_TARG = float(bistatic_3d(np.array([P_TARG[0]]), np.array([0.0]), np.array([0.0]), V_T_MOV)[0][0])
NU_T_STAT = float(bistatic_3d(np.array([P_TARG[0]]), np.array([0.0]), np.array([0.0]), V_T_MOV)[1][0])
UT_T = (P_TARG - P_T) / np.linalg.norm(P_TARG - P_T)
UR_T = (P_TARG - P_R) / np.linalg.norm(P_TARG - P_R)
DNU_TARG_PHYS = float(-(FC / c0) * np.dot(UT_T + UR_T, V_TARG) / DF)
NU_TARG_MOV = NU_T_STAT + DNU_TARG_PHYS

ACT_AFDM = np.where(np.abs(K_SIGNED) <= 96)[0]
PIL_AFDM = np.array([i for i in ACT_AFDM if i % K_COMB == 0], dtype=int)
DAT_AFDM = np.array([i for i in ACT_AFDM if i % K_COMB != 0], dtype=int)

ACT_OFDM = np.where(np.abs(K_SIGNED) <= 111)[0]
PIL_OFDM = np.array([i for i in ACT_OFDM if i % K_COMB == 0], dtype=int)
DAT_OFDM = np.array([i for i in ACT_OFDM if i % K_COMB != 0], dtype=int)


def daft_centered(c1):
    return np.fft.fft(np.exp(-2j * np.pi * c1 * (NC_IDX ** 2))[:, None] * np.eye(N), axis=0, norm="ortho")


def make_cpp_centered(s_body, c1):
    n_neg = np.arange(-L_CP, 0)
    return np.concatenate([s_body[N - L_CP:] * np.exp(-2j * np.pi * c1 * (2.0 * N * n_neg)), s_body])


# DBU/Group-Precoded OFDM (arXiv:2604.10296): unitary DFT block precoder strictly on data subcarriers (pilots & nulls untouched)
def build_u_grp(act_idx, pil_idx):
    U = np.eye(N, dtype=np.complex128)
    pil_set = set(pil_idx.tolist())
    for r in range(K_COMB):
        ir = np.array([i for i in act_idx if (i % K_COMB == r) and (i not in pil_set)], dtype=int)
        if len(ir) > 1:
            U[np.ix_(ir, ir)] = np.fft.fft(np.eye(len(ir)), axis=0, norm="ortho")
    return U


U_GRP_OFDM = build_u_grp(ACT_OFDM, PIL_OFDM)

E_F = np.exp(-2j * np.pi * np.outer(K_SIGNED, np.linspace(0.0, 13.5, 160)) / float(N))
U_F_FULL, _, _ = la.svd(E_F, full_matrices=False)
R_F = 18
U_F = U_F_FULL[:, :R_F]
# Exact known RC passband weight for equal-BW 223-bin OFDM arms (eliminates any RRC-rolloff basis mismatch on |k|>96!)
_F_NORM = np.abs(K_SIGNED) / float(N)
RC_GAIN = np.ones(N)
_M_ROLL = (_F_NORM > (1.0 - BETA_RRC) / 2.0) & (_F_NORM < (1.0 + BETA_RRC) / 2.0)
RC_GAIN[_M_ROLL] = 0.5 * (1.0 + np.cos(np.pi / BETA_RRC * (_F_NORM[_M_ROLL] - (1.0 - BETA_RRC) / 2.0)))
RC_GAIN[_F_NORM >= (1.0 + BETA_RRC) / 2.0] = 0.0
U_F_OFDM_RC = RC_GAIN[:, None] * U_F
U_F_PIL_AFDM_PINV = la.pinv(U_F[PIL_AFDM, :])
U_F_PIL_OFDM_PINV = la.pinv(U_F_OFDM_RC[PIL_OFDM, :])

TAU_Q_OFDM = np.concatenate([[0.0], np.linspace(TAU_G3.min(), TAU_G3.max(), 26)])
NU_Q_OFDM = np.concatenate([[NU_LOS_MOV - B_MOV], np.interp(TAU_Q_OFDM[1:], TAU_G3, NU_G3) - B_MOV])


def build_hq(tau_q, nu_q):
    f_norm = np.abs(K_SIGNED) / float(N)
    rc = np.ones(N)
    m_r = (f_norm > (1.0 - BETA_RRC) / 2.0) & (f_norm < (1.0 + BETA_RRC) / 2.0)
    rc[m_r] = 0.5 * (1.0 + np.cos(np.pi / BETA_RRC * (f_norm[m_r] - (1.0 - BETA_RRC) / 2.0)))
    rc[f_norm >= (1.0 + BETA_RRC) / 2.0] = 0.0
    return [
        (np.exp(2j * np.pi * nu * N_IDX / float(N))[:, None] * F_MAT.conj().T)
        * (rc * np.exp(-2j * np.pi * K_SIGNED * tau / float(N)))[None, :]
        for tau, nu in zip(tau_q, nu_q)
    ]


HQ_MOV = build_hq(TAU_Q_OFDM, NU_Q_OFDM)
HQ_STAT = build_hq(TAU_Q_OFDM, np.zeros_like(NU_Q_OFDM))

TAU_GRID = np.linspace(0.0, 14.0, 29)
DNU_GRID = np.linspace(-3.5, 3.5, 141)
E_DNU_MAT = np.exp(-2j * np.pi * np.outer(DNU_GRID, N_IDX) / float(N))
TI_EVAL = int(np.argmin(np.abs(TAU_GRID - TAU_TARG)))
NI_MOV = int(np.argmin(np.abs(DNU_GRID - (NU_TARG_MOV - (B_MOV + MU_MOV * TAU_TARG)))))
NI_STAT = int(np.argmin(np.abs(DNU_GRID - DNU_TARG_PHYS)))

A_MOV = daft_centered(C1_MOV)
M_LOS_AFDM_MOV = A_MOV @ (np.exp(2j * np.pi * DNU_LOS_MOV * N_IDX / float(N))[:, None] * A_MOV.conj().T)
M_LOS_OFDM_MOV = F_MAT @ (np.exp(2j * np.pi * DNU_LOS_MOV * N_IDX / float(N))[:, None] * F_MAT.conj().T)


def apply_real_rrc_frame(syms_cp_list, paths):
    M_s = len(syms_cp_list)
    stream = np.concatenate(syms_cp_list)
    L_tot = len(stream)
    L_half = (len(H_RRC) - 1) // 2
    up = np.zeros(L_tot * OSR, dtype=np.complex128)
    up[::OSR] = stream
    M_conv = len(up) + len(H_RRC) - 1
    N_fft = 1 << (M_conv + 64).bit_length()
    H_f = np.fft.fft(H_RRC, N_fft)
    s_ct = np.fft.ifft(np.fft.fft(up, N_fft) * H_f)[:M_conv]
    S_f = np.fft.fft(s_ct, N_fft)
    k_ct = np.fft.fftfreq(N_fft)
    t_ct = (np.arange(M_conv) - (L_half + L_CP * OSR)) / float(OSR)
    r_ct = np.zeros(M_conv, dtype=np.complex128)
    for alpha, tau_s, nu_subc in paths:
        r_ct += (
            alpha
            * np.fft.ifft(S_f * np.exp(-2j * np.pi * k_ct * (tau_s * OSR)))[:M_conv]
            * np.exp(2j * np.pi * nu_subc * t_ct / float(N))
        )
    r_mf = np.fft.ifft(np.fft.fft(r_ct, N_fft) * H_f)[: M_conv + len(H_RRC) - 1]
    r_disc = r_mf[2 * L_half : 2 * L_half + L_tot * OSR : OSR]
    return [r_disc[m * STRIDE + L_CP : (m + 1) * STRIDE] for m in range(M_s)]


def ep_16(Hd, y_d, s2_e, n_it=5):
    Nd = Hd.shape[1]
    G = Hd.conj().T @ Hd
    Hty = Hd.conj().T @ y_d
    gam = np.zeros(Nd, dtype=np.complex128)
    lam = np.ones(Nd)
    for _ in range(n_it):
        Sig = la.inv(G / s2_e + np.diag(lam))
        mu = Sig @ (Hty / s2_e + gam)
        vp = np.maximum(np.real(np.diag(Sig)), 1e-6)
        te = np.maximum(1.0 / vp - lam, 1e-4)
        me = (mu / vp - gam) / te
        d2 = np.abs(me[:, None] - CONST16[None, :]) ** 2 * te[:, None]
        d2 -= np.min(d2, axis=1, keepdims=True)
        w = np.exp(-d2)
        w /= np.sum(w, axis=1, keepdims=True)
        xm = w @ CONST16
        vm = np.maximum(np.sum(w * np.abs(CONST16[None, :] - xm[:, None]) ** 2, axis=1), 1e-6)
        lr = np.maximum(1.0 / vm - te, 1e-3)
        mp = (xm / vm - me * te) / lr
        ln = np.minimum(lr, 1e4)
        lam = 0.6 * ln + 0.4 * lam
        gam = 0.6 * (ln * mp) + 0.4 * gam
    return CONST16[np.argmin(np.abs(me[:, None] - CONST16[None, :]), axis=1)], xm


def compute_rd_map(R_res_l, S_hat_l, c1_v, mu_ref):
    M_c = len(R_res_l)
    rd = np.zeros((len(DNU_GRID), len(TAU_GRID)), dtype=np.complex128)
    for m in range(M_c):
        t0_m = m * STRIDE
        e_slow = np.exp(-2j * np.pi * DNU_GRID * (t0_m / float(N)))
        Zf = np.fft.fft(S_hat_l[m] * np.exp(-2j * np.pi * c1_v * (NC_IDX ** 2)), norm="ortho")
        for ti, tau in enumerate(TAU_GRID):
            s_del = np.fft.ifft(Zf * np.exp(-2j * np.pi * K_SIGNED * tau / float(N)), norm="ortho") * np.exp(
                2j * np.pi * c1_v * ((NC_IDX - tau) ** 2)
            )
            rd[:, ti] += (E_DNU_MAT @ (R_res_l[m] * np.conj(s_del) * np.exp(-2j * np.pi * (mu_ref * tau) * (t0_m + N_IDX) / float(N)))) * e_slow
    return np.abs(rd) ** 2 / float(M_c * N)


def eval_rd_peak(rd_pow, ti, ni, g_tau=4, g_nu=8):
    sig = float(np.max(rd_pow[max(0, ni - 2) : min(rd_pow.shape[0], ni + 3), max(0, ti - 1) : min(rd_pow.shape[1], ti + 2)]))
    mask = np.ones_like(rd_pow, dtype=bool)
    mask[max(0, ni - g_nu) : min(rd_pow.shape[0], ni + g_nu + 1), max(0, ti - g_tau) : min(rd_pow.shape[1], ti + g_tau + 1)] = False
    bg = rd_pow[mask]
    bg_mean = max(float(np.mean(bg)), 1e-15)
    return 10.0 * np.log10(sig / bg_mean), sig / bg_mean


def run_band3_plus_los(y_b, xp_vec, pil_idx, dat_idx, U_basis, U_pinv, M_los, use_u_grp=False, n_em=3):
    p_amp = xp_vec[pil_idx[0]]
    h_hat = U_basis @ (U_pinv @ (y_b[pil_idx] / p_amp))
    s2_e = max(1.0, float(np.mean(np.abs(y_b[pil_idx] - h_hat[pil_idx] * p_amp) ** 2)) * (len(pil_idx) / max(1.0, len(pil_idx) - R_F)))
    H_b = np.diag(h_hat)
    for it_em in range(n_em):
        xh_sym = xp_vec.copy()
        xs_sym = xp_vec.copy()
        if not use_u_grp:
            if it_em == 0:
                yeq = y_b[dat_idx] / np.where(np.abs(h_hat[dat_idx]) > 1e-6, h_hat[dat_idx], 1e-6) / p_amp
                xh_d = CONST16[np.argmin(np.abs(yeq[:, None] - CONST16[None, :]), axis=1)]
                d2 = np.abs(yeq[:, None] - CONST16[None, :]) ** 2 * (np.abs(h_hat[dat_idx] * p_amp) ** 2 / s2_e)[:, None]
                d2 -= np.min(d2, axis=1, keepdims=True)
                ww = np.exp(-d2)
                ww /= np.sum(ww, axis=1, keepdims=True)
                xs_d = ww @ CONST16
            else:
                xh_d, xs_d = ep_16(H_b[:, dat_idx] * p_amp, y_b - H_b @ xp_vec, s2_e, n_it=5)
            xh_sym[dat_idx] = xh_d * p_amp
            xs_sym[dat_idx] = xs_d * p_amp
            xs_base = xs_sym
        else:
            H_eff = H_b @ U_GRP_OFDM
            xh_d, xs_d = ep_16(H_eff[:, dat_idx] * p_amp, y_b - H_eff @ xp_vec, s2_e, n_it=5)
            xh_sym[dat_idx] = xh_d * p_amp
            xs_sym[dat_idx] = xs_d * p_amp
            xs_base = U_GRP_OFDM @ xs_sym
        if M_los is not None:
            Phi = np.hstack([np.roll(xs_base, s)[:, None] * U_basis for s in [-1, 0, 1]] + [(M_los @ xs_base)[:, None]])
            ch = la.solve(Phi.conj().T @ Phi + 1e-5 * np.eye(3 * R_F + 1), Phi.conj().T @ y_b, assume_a="pos")
            H_b = ch[-1] * M_los
        else:
            Phi = np.hstack([np.roll(xs_base, s)[:, None] * U_basis for s in [-1, 0, 1]])
            ch = la.solve(Phi.conj().T @ Phi + 1e-5 * np.eye(3 * R_F), Phi.conj().T @ y_b, assume_a="pos")
            H_b = np.zeros((N, N), dtype=np.complex128)
        for idx_s, s_sh in enumerate([-1, 0, 1]):
            hv = U_basis @ ch[idx_s * R_F : (idx_s + 1) * R_F]
            for row in range(N):
                H_b[row, (row - s_sh) % N] += hv[row]
        s2_e = max(1.0, float(np.mean(np.abs(y_b - Phi @ ch) ** 2)))
    return xh_d, xs_base, y_b - Phi @ ch


def run_ofdm_joint(R_cfo, Xf_l, is_mov, Hq, nuq, act_i, pil_syms, n_em=3, genie_g=None, reg=1e-2):
    M_c = len(R_cfo)
    Q = len(Hq)
    p_amp = np.sqrt(N / float(len(act_i)))
    if genie_g is not None:
        g_hat = genie_g.copy()
    else:
        Ga = np.zeros((Q, Q), dtype=np.complex128)
        ba = np.zeros(Q, dtype=np.complex128)
        for mp in pil_syms:
            ph = np.exp(2j * np.pi * nuq * (mp * STRIDE / float(N))) if is_mov else np.ones(Q)
            Pm = np.column_stack([(Hq[q] @ Xf_l[mp]) * ph[q] for q in range(Q)])
            Ga += Pm.conj().T @ Pm
            ba += Pm.conj().T @ R_cfo[mp]
        g_hat = la.solve(Ga + reg * np.eye(Q), ba, assume_a="pos")
    Xs_l = [Xf_l[m].copy() if m in pil_syms else np.zeros(N, dtype=np.complex128) for m in range(M_c)]
    Xh_d_l = [None] * M_c
    s2_e = 2.0
    for _ in range(n_em):
        rp = []
        for m in range(M_c):
            if m in pil_syms:
                continue
            ph = np.exp(2j * np.pi * nuq * (m * STRIDE / float(N))) if is_mov else np.ones(Q)
            Hm = sum((g_hat[q] * ph[q]) * Hq[q] for q in range(Q))
            xh, xs = ep_16(Hm[:, act_i] * p_amp, R_cfo[m], s2_e, n_it=5)
            Xh_d_l[m] = xh
            xf = np.zeros(N, dtype=np.complex128)
            xf[act_i] = xs * p_amp
            Xs_l[m] = xf
            rp.append(float(np.mean(np.abs(R_cfo[m] - Hm @ xf) ** 2)))
        Ga = np.zeros((Q, Q), dtype=np.complex128)
        ba = np.zeros(Q, dtype=np.complex128)
        for m in range(M_c):
            ph = np.exp(2j * np.pi * nuq * (m * STRIDE / float(N))) if is_mov else np.ones(Q)
            Pm = np.column_stack([(Hq[q] @ Xs_l[m]) * ph[q] for q in range(Q)])
            Ga += Pm.conj().T @ Pm
            ba += Pm.conj().T @ R_cfo[m]
        g_hat = la.solve(Ga + reg * np.eye(Q), ba, assume_a="pos")
        s2_e = max(1.0, float(np.mean(rp)))
    R_res, S_hat = [], []
    for m in range(M_c):
        ph = np.exp(2j * np.pi * nuq * (m * STRIDE / float(N))) if is_mov else np.ones(Q)
        Hm = sum((g_hat[q] * ph[q]) * Hq[q] for q in range(Q))
        R_res.append(R_cfo[m] - Hm @ Xs_l[m])
        S_hat.append(F_MAT.conj().T @ Xs_l[m])
    return Xh_d_l, S_hat, R_res


def eval_single_scene_worker(args):
    """Worker evaluating ALL requested arms on ONE paired physical 3D scene."""
    scene_seed, is_mov, los_db, clut_db, snr_t, arm_names, return_null_cells, slope_err_pct = args
    rng = np.random.default_rng(scene_seed)

    # 1. Generate paired physical 3D scatterers + LOS + optional target + shared AWGN
    vT_cur = V_T_MOV if is_mov else np.zeros(3)
    mu_true = MU_MOV if is_mov else 0.0
    mu_tx = mu_true * (1.0 - slope_err_pct / 100.0)
    b_cur = B_MOV if is_mov else 0.0
    c1_tx = mu_tx / (2.0 * N)
    nu_los_cur = NU_LOS_MOV if is_mov else 0.0
    nu_targ_cur = NU_TARG_MOV if is_mov else DNU_TARG_PHYS
    ni_cur = int(np.argmin(np.abs(DNU_GRID - (nu_targ_cur - (b_cur + mu_tx * TAU_TARG)))))

    xq = rng.uniform(X0, X1, N_CLUT)
    yq = rng.uniform(-WY / 2.0, WY / 2.0, N_CLUT)
    tc, ncv, _ = bistatic_3d(xq, yq, np.zeros(N_CLUT), vT_cur)
    ac = (rng.standard_normal(N_CLUT) + 1j * rng.standard_normal(N_CLUT)) / np.sqrt(2.0 * N_CLUT) * (10.0 ** (clut_db / 20.0))
    alos = np.exp(1j * rng.uniform(0, 2 * np.pi)) * (10.0 ** (los_db / 20.0))
    paths = [(alos, 0.0, nu_los_cur)] + [(a, float(t), float(v)) for a, t, v in zip(ac, tc, ncv)]
    if snr_t is not None:
        paths.append((np.exp(1j * rng.uniform(0, 2 * np.pi)) * (10.0 ** (snr_t / 20.0)), TAU_TARG, nu_targ_cur))
    noise_l = [(rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0) for _ in range(M_SYM)]

    # Generate shared random 16-QAM data streams per arm geometry
    data_193 = [rng.choice(CONST16, len(DAT_AFDM)) for _ in range(M_SYM)]
    data_223 = [rng.choice(CONST16, len(DAT_OFDM)) for _ in range(M_SYM)]
    data_blk = [rng.choice(CONST16, len(ACT_OFDM)) for _ in range(M_SYM)]
    pil_blk_phases = [np.exp(1j * rng.uniform(0, 2 * np.pi, len(ACT_OFDM))) for _ in range(M_SYM)]

    A_tx = A_MOV if (is_mov and slope_err_pct == 0.0) else daft_centered(c1_tx)
    M_los_tx = (
        M_LOS_AFDM_MOV
        if (is_mov and slope_err_pct == 0.0)
        else (A_tx @ (np.exp(2j * np.pi * DNU_LOS_MOV * N_IDX / float(N))[:, None] * A_tx.conj().T) if is_mov else None)
    )
    Hq_cur = HQ_MOV if is_mov else HQ_STAT
    nuq_cur = NU_Q_OFDM if is_mov else np.zeros_like(NU_Q_OFDM)

    out = {}
    for arm in arm_names:
        is_afdm = arm in ("ridge_afdm", "known_afdm")
        use_193 = is_afdm or (arm == "ofdm_comb_193")
        c1_arm = c1_tx if is_afdm else 0.0
        A_arm = A_tx if is_afdm else F_MAT
        act_i = ACT_AFDM if use_193 else ACT_OFDM
        pil_i = PIL_AFDM if use_193 else PIL_OFDM
        dat_i = DAT_AFDM if use_193 else DAT_OFDM
        Upinv = U_F_PIL_AFDM_PINV if use_193 else U_F_PIL_OFDM_PINV
        p_amp = np.sqrt(N / float(len(act_i)))

        syms_cp, Xf_l, Xd_l = [], [], []
        pil_syms = {0} if arm in ("ofdm_blkpil", "ofdm_genie") else ({0, 4} if arm == "ofdm_2pil" else set())
        for m in range(M_SYM):
            xf = np.zeros(N, dtype=np.complex128)
            if arm in ("ofdm_blkpil", "ofdm_genie", "ofdm_2pil"):
                if m in pil_syms:
                    xf[act_i] = pil_blk_phases[m] * p_amp
                    xd = None
                else:
                    xd = data_blk[m]
                    xf[act_i] = xd * p_amp
            elif arm == "dbu_ofdm":
                xd = data_223[m]
                xsym = np.zeros(N, dtype=np.complex128)
                xsym[pil_i] = p_amp
                xsym[dat_i] = xd * p_amp
                xf = U_GRP_OFDM @ xsym
            else:
                xd = data_193[m] if use_193 else data_223[m]
                xf[pil_i] = p_amp
                xf[dat_i] = xd * p_amp
            syms_cp.append(make_cpp_centered(A_arm.conj().T @ xf, c1_arm))
            Xf_l.append(xf)
            Xd_l.append(xd)

        R_raw = apply_real_rrc_frame(syms_cp, paths)
        R_cfo = [(R_raw[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * (m * STRIDE + N_IDX) / float(N)) for m in range(M_SYM)]

        ser_l, R_res_l, S_hat_l = [], [], []
        if arm in ("ofdm_blkpil", "ofdm_genie", "ofdm_2pil"):
            gg = None
            if arm == "ofdm_genie":
                Q = len(Hq_cur)
                R_clut_only = apply_real_rrc_frame(syms_cp, paths[: N_CLUT + 1])
                R_cc = [R_clut_only[m] * np.exp(-2j * np.pi * b_cur * (m * STRIDE + N_IDX) / float(N)) for m in range(M_SYM)]
                Ga = np.zeros((Q, Q), dtype=np.complex128)
                ba = np.zeros(Q, dtype=np.complex128)
                for m in range(M_SYM):
                    ph = np.exp(2j * np.pi * nuq_cur * (m * STRIDE / float(N))) if is_mov else np.ones(Q)
                    Pm = np.column_stack([(Hq_cur[q] @ Xf_l[m]) * ph[q] for q in range(Q)])
                    Ga += Pm.conj().T @ Pm
                    ba += Pm.conj().T @ R_cc[m]
                gg = la.solve(Ga + 1e-3 * np.eye(Q), ba, assume_a="pos")
            Xh_d_l, S_hat_l, R_res_l = run_ofdm_joint(R_cfo, Xf_l, is_mov, Hq_cur, nuq_cur, act_i, pil_syms, n_em=3, genie_g=gg)
            for m in range(M_SYM):
                if m not in pil_syms:
                    ser_l.append(float(np.mean(np.abs(Xh_d_l[m] - Xd_l[m]) > 1e-4)))
        elif arm == "known_afdm":
            for m in range(M_SYM):
                yb = A_arm @ R_cfo[m]
                if M_los_tx is not None:
                    Phi = np.hstack([np.roll(Xf_l[m], s)[:, None] * U_F for s in [-1, 0, 1]] + [(M_los_tx @ Xf_l[m])[:, None]])
                    ch = la.solve(Phi.conj().T @ Phi + 1e-5 * np.eye(3 * R_F + 1), Phi.conj().T @ yb, assume_a="pos")
                else:
                    Phi = np.hstack([np.roll(Xf_l[m], s)[:, None] * U_F for s in [-1, 0, 1]])
                    ch = la.solve(Phi.conj().T @ Phi + 1e-5 * np.eye(3 * R_F), Phi.conj().T @ yb, assume_a="pos")
                S_hat_l.append(A_arm.conj().T @ Xf_l[m])
                R_res_l.append(A_arm.conj().T @ (yb - Phi @ ch))
                ser_l.append(0.0)
        elif arm == "known_ofdm":
            Q = len(Hq_cur)
            for m in range(M_SYM):
                ph = np.exp(2j * np.pi * nuq_cur * (m * STRIDE / float(N))) if is_mov else np.ones(Q)
                Pm = np.column_stack([(Hq_cur[q] @ Xf_l[m]) * ph[q] for q in range(Q)])
                ck = la.solve(Pm.conj().T @ Pm + 1e-3 * np.eye(Q), Pm.conj().T @ R_cfo[m], assume_a="pos")
                R_res_l.append(R_cfo[m] - Pm @ ck)
                S_hat_l.append(F_MAT.conj().T @ Xf_l[m])
                ser_l.append(0.0)
        else:
            xp_v = np.zeros(N, dtype=np.complex128)
            xp_v[pil_i] = p_amp
            M_los_arm = M_los_tx if is_afdm else (M_LOS_OFDM_MOV if is_mov else None)
            U_basis_arm = U_F if use_193 else U_F_OFDM_RC
            for m in range(M_SYM):
                xh_d, xs_b, y_res = run_band3_plus_los(
                    A_arm @ R_cfo[m], xp_v, pil_i, dat_i, U_basis_arm, Upinv, M_los_arm, use_u_grp=(arm == "dbu_ofdm"), n_em=3
                )
                ser_l.append(float(np.mean(np.abs(xh_d - Xd_l[m]) > 1e-4)))
                S_hat_l.append(A_arm.conj().T @ xs_b)
                R_res_l.append(A_arm.conj().T @ y_res)

        rdp = compute_rd_map(R_res_l, S_hat_l, c1_arm, mu_tx if is_afdm else mu_true)
        if return_null_cells:
            rats = (rdp / max(float(np.mean(rdp)), 1e-15)).astype(np.float32)
            out[arm] = {"cell_rats": rats.ravel(), "map_max": float(np.max(rats))}
        else:
            sc_db, rat = eval_rd_peak(rdp, TI_EVAL, ni_cur)
            out[arm] = {"ser": float(np.mean(ser_l)), "scnr_db": float(sc_db), "peak_ratio": float(rat)}
    return out


def rrc_leakage_worker(trial_seed):
    """First Knife #1 worker: real OSR=8 RRC beta=0.25 3-symbol continuous-time data->pilot leakage."""
    rng = np.random.default_rng(trial_seed)
    xq = rng.uniform(X0, X1, N_CLUT)
    yq = rng.uniform(-WY / 2.0, WY / 2.0, N_CLUT)
    tc, ncv, _ = bistatic_3d(xq, yq, np.zeros(N_CLUT), V_T_MOV)
    ac = (rng.standard_normal(N_CLUT) + 1j * rng.standard_normal(N_CLUT)) / np.sqrt(2.0 * N_CLUT)
    paths_3d = [(a, float(t), float(v)) for a, t, v in zip(ac, tc, ncv)]
    paths_lin = [(a, float(t), float(B_MOV + MU_MOV * t)) for a, t in zip(ac, tc)]

    res = {}
    for pname, paths_c in [("3d_curved", paths_3d), ("linear_ridge", paths_lin)]:
        res[pname] = {}
        for lbl, c1_v in [("matched", +C1_MOV), ("ofdm_zero", 0.0), ("opposite", -C1_MOV)]:
            A_v = daft_centered(c1_v)
            syms_d, syms_p = [], []
            for _ in range(3):
                xfd = np.zeros(N, dtype=np.complex128)
                xfd[DAT_AFDM] = rng.choice(CONST16, len(DAT_AFDM))
                syms_d.append(make_cpp_centered(A_v.conj().T @ xfd, c1_v))
                xfp = np.zeros(N, dtype=np.complex128)
                xfp[PIL_AFDM] = 1.0
                syms_p.append(make_cpp_centered(A_v.conj().T @ xfp, c1_v))
            rd = apply_real_rrc_frame(syms_d, paths_c)[1] * np.exp(-2j * np.pi * B_MOV * (STRIDE + N_IDX) / float(N))
            rp = apply_real_rrc_frame(syms_p, paths_c)[1] * np.exp(-2j * np.pi * B_MOV * (STRIDE + N_IDX) / float(N))
            yd = A_v @ rd
            yp = A_v @ rp
            res[pname][lbl] = (float(np.mean(np.abs(yd[PIL_AFDM]) ** 2)), float(np.mean(np.abs(yp[PIL_AFDM]) ** 2)))
    return res


def paired_bootstrap_ci(diffs, n_boot=10000, seed=12345):
    arr = np.asarray(diffs, dtype=np.float64)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(arr), size=(n_boot, len(arr)))
    means = np.mean(arr[idx], axis=1)
    return float(np.mean(arr)), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def independent_diff_bootstrap_ci(a, b, n_boot=10000, seed=54321):
    # Bootstrap CI for mean(a) - mean(b) when a and b are independent groups (e.g. S1 vs G0 DiD)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    rng = np.random.default_rng(seed)
    ia = rng.integers(0, len(a), size=(n_boot, len(a)))
    ib = rng.integers(0, len(b), size=(n_boot, len(b)))
    vals = np.mean(a[ia], axis=1) - np.mean(b[ib], axis=1)
    return float(np.mean(a) - np.mean(b)), float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def wilson_binomial_ci(k, n_tot, z=1.959964):
    if n_tot == 0:
        return 0.0, 0.0, 0.0
    p = k / float(n_tot)
    denom = 1.0 + z * z / n_tot
    center = (p + z * z / (2.0 * n_tot)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n_tot)) / n_tot) / denom
    return p, max(0.0, center - half), min(1.0, center + half)


def run_batch(pool, task_list):
    if pool is None:
        return [eval_single_scene_worker(t) for t in task_list]
    return pool.map(eval_single_scene_worker, task_list)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026112501)
    ap.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    t0 = time.time()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    rng_master = np.random.default_rng(args.seed)

    if args.mode == "smoke":
        n_rrc = 4
        n_cal, n_val, n_pos_main, n_pos_aux = 6, 6, 6, 4
    else:
        n_rrc = 30
        n_cal, n_val, n_pos_main, n_pos_aux = 100, 100, 60, 40

    pool = Pool(processes=args.workers) if args.workers > 1 else None
    try:
        # ----------------------------------------------------------------------
        # 1. Target Template Energy Surviving Band-3 + 1-col LOS Null-Clutter Projection
        # ----------------------------------------------------------------------
        rng_surv = np.random.default_rng(args.seed + 1)
        surv_vals = []
        for _ in range(10):
            xft = np.zeros(N, dtype=np.complex128)
            p_amp = np.sqrt(N / float(len(ACT_AFDM)))
            xft[PIL_AFDM] = p_amp
            xft[DAT_AFDM] = rng_surv.choice(CONST16, len(DAT_AFDM)) * p_amp
            sym_t = make_cpp_centered(A_MOV.conj().T @ xft, C1_MOV)
            rt = apply_real_rrc_frame([sym_t, sym_t, sym_t], [(1.0 + 0j, TAU_TARG, NU_TARG_MOV)])[1]
            yb = A_MOV @ (rt * np.exp(-2j * np.pi * B_MOV * (STRIDE + N_IDX) / float(N)))
            Phi_c = np.hstack([np.roll(xft, s)[:, None] * U_F for s in [-1, 0, 1]] + [(M_LOS_AFDM_MOV @ xft)[:, None]])
            Q_c, _ = la.qr(Phi_c, mode="economic")
            surv_vals.append(float(la.norm(yb - Q_c @ (Q_c.conj().T @ yb)) ** 2 / la.norm(yb) ** 2))
        target_survival = float(np.mean(surv_vals))
        print(f"[Target Survival] {target_survival*100:.2f}% ({10*np.log10(target_survival):+.2f} dB)", flush=True)

        # ----------------------------------------------------------------------
        # 2. First Knife #1: Real OSR=8 RRC Leakage (Matched vs OFDM vs Opposite)
        # ----------------------------------------------------------------------
        rrc_seeds = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=n_rrc)]
        rrc_raw = pool.map(rrc_leakage_worker, rrc_seeds) if pool else [rrc_leakage_worker(s) for s in rrc_seeds]
        rrc_summary = {}
        for pname in ("3d_curved", "linear_ridge"):
            rrc_summary[pname] = {}
            for lbl in ("matched", "ofdm_zero", "opposite"):
                lk = float(np.mean([r[pname][lbl][0] for r in rrc_raw]))
                sg = float(np.mean([r[pname][lbl][1] for r in rrc_raw]))
                rrc_summary[pname][lbl + "_db"] = 10.0 * np.log10(lk / max(sg, 1e-15))
            rrc_summary[pname]["gain_vs_ofdm_db"] = rrc_summary[pname]["ofdm_zero_db"] - rrc_summary[pname]["matched_db"]
            rrc_summary[pname]["gain_vs_opposite_db"] = rrc_summary[pname]["opposite_db"] - rrc_summary[pname]["matched_db"]
        print(f"[RRC OSR=8 Leakage] 3D-Curved: matched={rrc_summary['3d_curved']['matched_db']:+.2f} dB, ofdm={rrc_summary['3d_curved']['ofdm_zero_db']:+.2f} dB, opp={rrc_summary['3d_curved']['opposite_db']:+.2f} dB (gain={rrc_summary['3d_curved']['gain_vs_ofdm_db']:+.2f} dB)", flush=True)

        # ----------------------------------------------------------------------
        # 3. Main Scenario S1 (Moving, LOS+18dB, Clut+28dB):
        #    Independent Cal -> Independent Val -> Paired Pos at SNR_t=-11 dB (Primary) & -9 dB (Scope)
        # ----------------------------------------------------------------------
        main_arms = ["ridge_afdm", "ofdm_comb", "dbu_ofdm", "ofdm_blkpil", "known_afdm", "known_ofdm"]
        scope_extra_arms = ["ofdm_genie", "ofdm_2pil"]
        all_s1_arms = main_arms + scope_extra_arms

        cal_seeds_s1 = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=n_cal)]
        val_seeds_s1 = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=n_val)]
        pos11_seeds_s1 = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=n_pos_main)]
        pos9_seeds_s1 = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=n_pos_aux)]

        print(f"[S1] Running cal={n_cal}, val={n_val}, pos(-11dB)={n_pos_main}, pos(-9dB)={n_pos_aux}...", flush=True)
        cal_s1 = run_batch(pool, [(s, True, 18.0, 28.0, None, all_s1_arms, True, 0.0) for s in cal_seeds_s1])
        val_s1 = run_batch(pool, [(s, True, 18.0, 28.0, None, all_s1_arms, True, 0.0) for s in val_seeds_s1])

        thr_s1 = {}
        val_pfa_s1 = {}
        for arm in all_s1_arms:
            cal_cells = np.concatenate([r[arm]["cell_rats"] for r in cal_s1])
            thr_cell = float(np.quantile(cal_cells, 0.999))
            val_cells = np.concatenate([r[arm]["cell_rats"] for r in val_s1])
            k_fa = int(np.sum(val_cells > thr_cell))
            p_fa, lo_fa, hi_fa = wilson_binomial_ci(k_fa, len(val_cells))
            # Whole-map P_fa (at cell threshold) & whole-map 95% threshold
            map_fa = float(np.mean([1.0 if r[arm]["map_max"] > thr_cell else 0.0 for r in val_s1]))
            thr_s1[arm] = thr_cell
            val_pfa_s1[arm] = {
                "thr_cell_db": 10.0 * np.log10(thr_cell),
                "val_cells": int(len(val_cells)),
                "val_k_fa": k_fa,
                "emp_pfa_cell": p_fa,
                "ci95_cell": [lo_fa, hi_fa],
                "emp_map_exceed_rate_at_cell_thr": map_fa,
            }

        pos11_s1 = run_batch(pool, [(s, True, 18.0, 28.0, -11.0, all_s1_arms, False, 0.0) for s in pos11_seeds_s1])
        pos9_s1 = run_batch(pool, [(s, True, 18.0, 28.0, -9.0, all_s1_arms, False, 0.0) for s in pos9_seeds_s1])

        def summarize_pos(res_list, thr_dict, arm_list):
            s = {}
            for arm in arm_list:
                sers = [r[arm]["ser"] for r in res_list]
                scnrs = [r[arm]["scnr_db"] for r in res_list]
                dets = [1.0 if r[arm]["peak_ratio"] > thr_dict[arm] else 0.0 for r in res_list]
                s[arm] = {
                    "ser_mean": float(np.mean(sers)),
                    "scnr_db_mean": float(np.mean(scnrs)),
                    "pd_at_1e3": float(np.mean(dets)),
                    "scnr_list": scnrs,
                    "det_list": dets,
                }
            return s

        s1_11_sum = summarize_pos(pos11_s1, thr_s1, all_s1_arms)
        s1_9_sum = summarize_pos(pos9_s1, thr_s1, all_s1_arms)
        for arm in all_s1_arms:
            print(
                f"  S1(-11dB) {arm:14s} | SER={s1_11_sum[arm]['ser_mean']:.4f} | SCNR={s1_11_sum[arm]['scnr_db_mean']:+6.2f} dB | Thr={val_pfa_s1[arm]['thr_cell_db']:+5.2f} (valPfa={val_pfa_s1[arm]['emp_pfa_cell']:.4e}) | Pd={s1_11_sum[arm]['pd_at_1e3']*100:5.1f}%",
                flush=True,
            )

        # ----------------------------------------------------------------------
        # 4. Guard Scenario G0 (Static v_T=0, mu=0, LOS+18dB, Clut+28dB, SNR_t=-11 dB)
        #    Includes ofdm_comb_193 for exact matched-bin c1=0 recovery check!
        # ----------------------------------------------------------------------
        g0_arms = ["ridge_afdm", "ofdm_comb_193", "ofdm_comb", "dbu_ofdm", "ofdm_blkpil", "known_afdm", "known_ofdm"]
        n_cal_g0 = max(6, n_cal // 2)
        cal_seeds_g0 = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=n_cal_g0)]
        pos11_seeds_g0 = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=n_pos_aux)]
        print(f"[G0 Static Guard] Running cal={n_cal_g0}, pos(-11dB)={n_pos_aux}...", flush=True)
        cal_g0 = run_batch(pool, [(s, False, 18.0, 28.0, None, g0_arms, True, 0.0) for s in cal_seeds_g0])
        thr_g0 = {arm: float(np.quantile(np.concatenate([r[arm]["cell_rats"] for r in cal_g0]), 0.999)) for arm in g0_arms}
        pos11_g0 = run_batch(pool, [(s, False, 18.0, 28.0, -11.0, g0_arms, False, 0.0) for s in pos11_seeds_g0])
        g0_11_sum = summarize_pos(pos11_g0, thr_g0, g0_arms)
        for arm in g0_arms:
            print(
                f"  G0(-11dB) {arm:14s} | SER={g0_11_sum[arm]['ser_mean']:.4f} | SCNR={g0_11_sum[arm]['scnr_db_mean']:+6.2f} dB | Pd={g0_11_sum[arm]['pd_at_1e3']*100:5.1f}%",
                flush=True,
            )

        # ----------------------------------------------------------------------
        # 5. Scope Scenarios: S2 (Weak LOS +6dB), S3 (Mod Clut +20dB), Slope Mismatch (1%, 2%)
        # ----------------------------------------------------------------------
        scope_arms = ["ridge_afdm", "ofdm_comb", "dbu_ofdm", "ofdm_blkpil", "known_afdm", "known_ofdm"]
        scope_results = {}
        for sc_name, los_v, clut_v, snr_v, serr in [
            ("S2_WeakLOS_6dB", 6.0, 28.0, -9.0, 0.0),
            ("S3_ModClut_20dB", 18.0, 20.0, -9.0, 0.0),
            ("S1_SlopeErr_1pct", 18.0, 28.0, -9.0, 1.0),
            ("S1_SlopeErr_2pct", 18.0, 28.0, -9.0, 2.0),
        ]:
            arms_here = ["ridge_afdm"] if serr > 0 else scope_arms
            c_seeds = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=max(6, n_cal // 4))]
            p_seeds = [int(s) for s in rng_master.integers(1, 2**31 - 1, size=n_pos_aux)]
            c_res = run_batch(pool, [(s, True, los_v, clut_v, None, arms_here, True, serr) for s in c_seeds])
            t_loc = {arm: float(np.quantile(np.concatenate([r[arm]["cell_rats"] for r in c_res]), 0.999)) for arm in arms_here}
            p_res = run_batch(pool, [(s, True, los_v, clut_v, snr_v, arms_here, False, serr) for s in p_seeds])
            sm = summarize_pos(p_res, t_loc, arms_here)
            scope_results[sc_name] = {
                arm: {
                    "ser_mean": sm[arm]["ser_mean"],
                    "scnr_db_mean": sm[arm]["scnr_db_mean"],
                    "pd_at_1e3": sm[arm]["pd_at_1e3"],
                    "thr_db": 10.0 * np.log10(t_loc[arm]),
                }
                for arm in arms_here
            }
            print(f"[{sc_name}] " + " | ".join(f"{a}:SC={sm[a]['scnr_db_mean']:+.1f},Pd={sm[a]['pd_at_1e3']*100:.0f}%" for a in arms_here), flush=True)

        # ----------------------------------------------------------------------
        # 6. Pre-registered Primary Verdicts (Exact Paired Bootstrap 95% CIs!)
        # ----------------------------------------------------------------------
        equal_rivals = ["ofdm_comb", "dbu_ofdm", "ofdm_blkpil"]
        # Pick strongest equal-overhead rival on S1(-11dB) by mean SCNR (and also check separately by Pd!)
        best_rival_scnr = max(equal_rivals, key=lambda a: s1_11_sum[a]["scnr_db_mean"])
        best_rival_pd = max(equal_rivals, key=lambda a: s1_11_sum[a]["pd_at_1e3"])

        diff_scnr_s1 = np.array(s1_11_sum["ridge_afdm"]["scnr_list"]) - np.array(s1_11_sum[best_rival_scnr]["scnr_list"])
        diff_scnr_g0 = np.array(g0_11_sum["ridge_afdm"]["scnr_list"]) - np.array(g0_11_sum[best_rival_scnr]["scnr_list"])
        diff_pd_s1 = np.array(s1_11_sum["ridge_afdm"]["det_list"]) - np.array(s1_11_sum[best_rival_pd]["det_list"])

        dscnr_mean, dscnr_lo, dscnr_hi = paired_bootstrap_ci(diff_scnr_s1, seed=args.seed + 101)
        did_mean, did_lo, did_hi = independent_diff_bootstrap_ci(diff_scnr_s1, diff_scnr_g0, seed=args.seed + 102)
        dpd_mean, dpd_lo, dpd_hi = paired_bootstrap_ci(diff_pd_s1, seed=args.seed + 103)

        g0_recovery_diff = abs(g0_11_sum["ridge_afdm"]["scnr_db_mean"] - g0_11_sum["ofdm_comb_193"]["scnr_db_mean"])

        clause1_pass = bool((dscnr_lo >= 1.0) and (did_lo > 0.0) and (dpd_lo > 0.0))
        clause2_pass = bool(
            (rrc_summary["3d_curved"]["gain_vs_ofdm_db"] >= 15.0)
            and (rrc_summary["3d_curved"]["gain_vs_opposite_db"] >= 20.0)
            and (g0_recovery_diff <= 0.20)
        )
        pass_primary = bool(clause1_pass and clause2_pass)

        # Strip raw per-trial lists from compact JSON summary
        def clean_sum(d):
            return {k: {kk: vv for kk, vv in v.items() if kk not in ("scnr_list", "det_list")} for k, v in d.items()}

        summary = {
            "meta": {
                "card": "k_r10_k01",
                "seed": args.seed,
                "mode": args.mode,
                "workers": args.workers,
                "elapsed_sec": round(time.time() - t0, 2),
                "geometry": {
                    "fc_ghz": FC / 1e9,
                    "df_khz": DF / 1e3,
                    "N": N,
                    "L_cp": L_CP,
                    "M": M_SYM,
                    "OSR": OSR,
                    "beta_rrc": BETA_RRC,
                    "mu_mov": MU_MOV,
                    "b_mov": B_MOV,
                    "nu_los_mov": NU_LOS_MOV,
                    "tau_targ": TAU_TARG,
                    "dnu_targ_phys": DNU_TARG_PHYS,
                    "ridge_span_subc": float(NU_G3.max() - NU_G3.min()),
                    "active_bins_afdm": int(len(ACT_AFDM)),
                    "active_bins_ofdm": int(len(ACT_OFDM)),
                    "target_subspace_survival_ratio": target_survival,
                    "target_subspace_survival_db": 10.0 * np.log10(target_survival),
                },
                "counts": {"n_rrc": n_rrc, "n_cal": n_cal, "n_val": n_val, "n_pos_main": n_pos_main, "n_pos_aux": n_pos_aux},
            },
            "rrc_osr8_leakage": rrc_summary,
            "s1_pfa_validation": val_pfa_s1,
            "s1_primary_snr_m11db": clean_sum(s1_11_sum),
            "s1_scope_snr_m9db": clean_sum(s1_9_sum),
            "g0_static_guard_snr_m11db": clean_sum(g0_11_sum),
            "scope_readouts": scope_results,
            "primary_contrasts": {
                "strongest_equal_rival_by_scnr": best_rival_scnr,
                "strongest_equal_rival_by_pd": best_rival_pd,
                "delta_scnr_s1_db": {"mean": dscnr_mean, "ci95": [dscnr_lo, dscnr_hi]},
                "did_2x2_db": {"mean": did_mean, "ci95": [did_lo, did_hi]},
                "delta_pd_s1": {"mean": dpd_mean, "ci95": [dpd_lo, dpd_hi]},
                "g0_matched_193_recovery_abs_diff_db": g0_recovery_diff,
            },
            "verdicts": {
                "CLAUSE_1_MOVING_BREAKTHROUGH_AND_DID": clause1_pass,
                "CLAUSE_2_RRC_LEAKAGE_AND_STATIC_DUALITY": clause2_pass,
                "PASS_PRIMARY": pass_primary,
            },
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n=== VERDICTS ===\n{json.dumps(summary['verdicts'], indent=2)}", flush=True)
        print(f"Primary Contrasts: {json.dumps(summary['primary_contrasts'], indent=2)}", flush=True)
        print(f"Saved: {args.out} (elapsed={summary['meta']['elapsed_sec']}s)", flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()


if __name__ == "__main__":
    main()
