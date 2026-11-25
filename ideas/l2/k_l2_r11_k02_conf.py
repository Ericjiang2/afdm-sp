#!/usr/bin/env python3
"""
L2 Pre-registered Experiment for Child Card I-20261125-k02 (--parent I-20261125-k01):
Bistatic AFDM Full-Burst Clutter Suppression and Unmasked Full-Map Blind Detection.

Incorporates ALL 5 Sol Pre-L2 Audit Fixes (2026-11-25):
  1. Pilot overhead strictly conservative favoring OFDM:
       - Ridge-AFDM (193 bins): 24 pilots / 193 = 12.44%  (<= 12.50%)
       - OFDM-Comb / DBU-OFDM (223 bins): 28 pilots / 223 = 12.56%
       - OFDM-BlkPil (1/8 syms): 12.50%
       - OFDM-DistPil (staggered 1/8 across 8 syms): 223/1784 = 12.50%
     Post-RRC 99% BW verified across ALL 5 primary arms and wired into PASS_PRIMARY.
     Unimpaired +38 dB static SER < 1% (in G1) and nominal +28 dB Rayleigh G0 SER < 2%
     across ALL 5 primary arms wired into PASS_PRIMARY.
  2. Strict blind receiver interfaces: ONLY known pilot values are passed into blind
     receivers (never full data arrays); shared master 16-QAM payload stream per scene;
     alarm thresholding strictly precedes localization check against true target cell.
  3. Exact-RC OSR=2 filter approximation error verified (< 1.5%) in Gate G1; unified
     relative error (< 1e-12) for synthetic 1e10 and real maps in Gate G1.
  4. N_cal=1500, N_val=2000 on S1 covering ALL 7 arms entering PASS_PRIMARY (5 primary
     + k01_orig + burst_em0) and N_cal=400, N_val=400 on G0; Bonferroni-adjusted
     simultaneous 95% dual-bootstrap lower bounds across all 4 equal-overhead OFDM rivals.
  5. Frozen ablation SNR = -16.0 dB requiring (a) ridge_afdm_st beats k01_orig (>= +50 pp),
     (b) ridge_afdm_st beats burst_em0 (lower bound > 0), and (c) em0 share < 80%;
     frozen G0 slope SNR = -21.5 dB with explicit non-saturation check ([15%, 92%])
     and pre-specified static advantage upper bound (<= +15 pp) + conservative DiD >= +50 pp.
"""
import os
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")
import sys
print(f"sys.executable: {sys.executable}", flush=True)

import argparse
import json
import resource
import time
from multiprocessing import Pool
import numpy as np
import scipy.linalg as la
from scipy.stats import beta as beta_dist, betabinom as betabinom_dist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_l2_r10_k01 as base  # noqa: E402

PRIMARY_EQUAL_ARMS = [
    "ridge_afdm_st",
    "ofdm_comb_st",
    "dbu_ofdm_st",
    "ofdm_blkpil_st",
    "ofdm_distpil_st",
]
EQUAL_OFDM_RIVALS = ["ofdm_comb_st", "dbu_ofdm_st", "ofdm_blkpil_st", "ofdm_distpil_st"]
AFDM_ABLATION_ARMS = ["k01_orig", "burst_em0"]
ALL_PASS_ARMS = PRIMARY_EQUAL_ARMS + AFDM_ABLATION_ARMS
DESC_ARMS = ["known_afdm_st", "known_ofdm_st", "ofdm_2pil_st", "ofdm_genie_st"]

# Fix #1: Strictly align pilot overhead conservatively favoring OFDM, with edge-anchored uniform spacing!
# Ridge-AFDM (193 bins): 24 edge-anchored uniform pilots on [-96, +96] -> 24 / 193 = 12.44% <= 12.50%
PIL_AFDM_24 = np.array([int(k % base.N) for k in np.round(np.linspace(-96, 96, 24)).astype(int)], dtype=int)
DAT_AFDM_169 = np.array([i for i in base.ACT_AFDM if i not in set(PIL_AFDM_24.tolist())], dtype=int)
if not (len(PIL_AFDM_24) == 24 and len(DAT_AFDM_169) == 169):
    raise ValueError("AFDM 24/169 pilot-data split violated")

# OFDM-Comb / DBU-OFDM (223 bins): 28 edge-anchored uniform pilots on [-111, +111] -> 28 / 223 = 12.56% >= 12.50%
PIL_OFDM_28 = np.array([int(k % base.N) for k in np.round(np.linspace(-111, 111, 28)).astype(int)], dtype=int)
DAT_OFDM_195 = np.array([i for i in base.ACT_OFDM if i not in set(PIL_OFDM_28.tolist())], dtype=int)
if not (len(PIL_OFDM_28) == 28 and len(DAT_OFDM_195) == 195):
    raise ValueError("OFDM 28/195 pilot-data split violated")

U_F_PIL_AFDM24_PINV = la.pinv(base.U_F[PIL_AFDM_24, :])
U_F_PIL_OFDM28_PINV = la.pinv(base.U_F_OFDM_RC[PIL_OFDM_28, :])
U_GRP_OFDM28 = base.build_u_grp(base.ACT_OFDM, PIL_OFDM_28)

# Staggered 12.50% time-distributed pilot indices across M=8 symbols (223 / 1784 = 12.50% exact)
PIL_DIST_OFDM = [np.array([i for i in base.ACT_OFDM if (i - m) % base.K_COMB == 0], dtype=int) for m in range(base.M_SYM)]
DAT_DIST_OFDM = [np.array([i for i in base.ACT_OFDM if (i - m) % base.K_COMB != 0], dtype=int) for m in range(base.M_SYM)]

G_TAU = 4  # 17x9 guard block
G_NU = 8

# Continuous burst-time K=3 orthonormal polynomial basis u_p(t_{m,n})
T_ALL = np.array([m * base.STRIDE + base.N_IDX for m in range(base.M_SYM)], dtype=np.float64)
_T_MID = 0.5 * (T_ALL.min() + T_ALL.max())
_T_HALF = 0.5 * (T_ALL.max() - T_ALL.min())
_T_NORM = (T_ALL - _T_MID) / _T_HALF
_Q_T3, _ = la.qr(np.stack([_T_NORM ** p for p in range(3)], axis=-1).reshape(-1, 3), mode="economic")
U_T3 = (_Q_T3 * np.sqrt(_Q_T3.shape[0])).reshape(base.M_SYM, base.N, 3)

# Nyquist-exact OSR=2 linear-convolution RC full-burst ridge basis (79 cols / 2,048 samples)
H_RRC2 = base.rrc_filter(osr=2, beta=base.BETA_RRC, span=base.SPAN_RRC)
L_TOT = base.M_SYM * base.STRIDE
L_HALF2 = (len(H_RRC2) - 1) // 2
M_CONV2 = L_TOT * 2 + len(H_RRC2) - 1
N_FFT2 = 1 << (M_CONV2 + 64).bit_length()
H_RC2_F = np.fft.fft(H_RRC2, N_FFT2) ** 2
K_CT2 = np.fft.fftfreq(N_FFT2)
TAU_KNOTS = np.linspace(1.8, 12.6, 26)
E_TAU_SHIFT2 = np.exp(-2j * np.pi * np.outer(TAU_KNOTS * 2.0, K_CT2))
SHIFTS_ALL2 = np.vstack([np.ones((1, N_FFT2), dtype=np.complex128), E_TAU_SHIFT2])
BODY_IDX = np.concatenate([np.arange(m * base.STRIDE + base.L_CP, (m + 1) * base.STRIDE) for m in range(base.M_SYM)])
E_RIDGE_MOV = np.exp(2j * np.pi * np.outer(base.MU_MOV * TAU_KNOTS, T_ALL.ravel()) / float(base.N))

G_RC_MAT = base.F_MAT.conj().T @ (base.RC_GAIN[:, None] * base.F_MAT)


def _build_hq_waveform(tau_knots, mu_val, c1_val, A_mat):
    ops = []
    if abs(c1_val) < 1e-15:
        for tau in tau_knots:
            ph_fast = np.exp(2j * np.pi * (mu_val * tau) * base.N_IDX / float(base.N))
            H_q = (ph_fast[:, None] * base.F_MAT.conj().T) * (base.RC_GAIN * np.exp(-2j * np.pi * base.K_SIGNED * tau / float(base.N)))[None, :]
            ops.append(H_q)
    else:
        GAh = G_RC_MAT @ A_mat.conj().T
        for tau in tau_knots:
            ph_c = np.exp(2j * np.pi * c1_val * (tau ** 2 + base.N * tau))
            H_q = (GAh * np.exp(-2j * np.pi * base.K_SIGNED * tau / float(base.N))[None, :]) * ph_c
            ops.append(H_q)
    return np.ascontiguousarray(np.stack(ops, axis=0))


HQ_AFDM_MOV = _build_hq_waveform(TAU_KNOTS, base.MU_MOV, base.C1_MOV, base.A_MOV)
A_STAT = base.daft_centered(0.0)
HQ_STAT_0 = _build_hq_waveform(TAU_KNOTS, 0.0, 0.0, A_STAT)
HQ_OFDM_MOV_LIN = _build_hq_waveform(TAU_KNOTS, base.MU_MOV, 0.0, base.F_MAT)

# Linear-ridge OFDM basis (ZERO 3D curvature curve prior — exact same linear slope mu prior as AFDM!)
TAU_Q_LIN = np.concatenate([[0.0], TAU_KNOTS])
NU_Q_LIN_MOV = np.concatenate([[base.DNU_LOS_MOV], base.MU_MOV * TAU_KNOTS])
NU_Q_LIN_STAT = np.zeros_like(TAU_Q_LIN)
HQ_OFDM_LIN_MOV = np.ascontiguousarray(np.stack(base.build_hq(TAU_Q_LIN, NU_Q_LIN_MOV), axis=0))
HQ_OFDM_LIN_STAT = np.ascontiguousarray(np.stack(base.build_hq(TAU_Q_LIN, NU_Q_LIN_STAT), axis=0))


def score_cut(rd_map, center, role="unknown", counter=None):
    if counter is not None:
        counter[role] = counter.get(role, 0) + 1
    ni, ti = int(center[0]), int(center[1])
    n_nu, n_tau = rd_map.shape
    mask = np.ones((n_nu, n_tau), dtype=bool)
    mask[max(0, ni - G_NU) : min(n_nu, ni + G_NU + 1), max(0, ti - G_TAU) : min(n_tau, ti + G_TAU + 1)] = False
    bg_mean = max(float(np.mean(rd_map[mask])), 1e-15)
    return float(rd_map[ni, ti]) / bg_mean


def score_cut_full_map(rd_map, role="unknown", counter=None):
    if counter is not None:
        counter[role] = counter.get(role, 0) + 1
    n_nu, n_tau = rd_map.shape
    row_sums = np.sum(rd_map, axis=1)
    rp = np.zeros(n_nu + 1, dtype=np.float64); rp[1:] = np.cumsum(row_sums)
    rs = np.zeros(n_nu + 1, dtype=np.float64); rs[:-1] = np.cumsum(row_sums[::-1])[::-1]

    cp = np.zeros((n_nu, n_tau + 1), dtype=np.float64); cp[:, 1:] = np.cumsum(rd_map, axis=1)
    cs = np.zeros((n_nu, n_tau + 1), dtype=np.float64); cs[:, :-1] = np.cumsum(rd_map[:, ::-1], axis=1)[:, ::-1]

    lp = np.zeros((n_nu + 1, n_tau + 1), dtype=np.float64); lp[1:, :] = np.cumsum(cp, axis=0)
    rr = np.zeros((n_nu + 1, n_tau + 1), dtype=np.float64); rr[1:, :] = np.cumsum(cs, axis=0)

    r0 = np.maximum(0, np.arange(n_nu) - G_NU); r1 = np.minimum(n_nu, np.arange(n_nu) + G_NU + 1)
    c0 = np.maximum(0, np.arange(n_tau) - G_TAU); c1 = np.minimum(n_tau, np.arange(n_tau) + G_TAU + 1)

    bg_sum = (
        rp[r0][:, None] + rs[r1][:, None]
        + (lp[r1[:, None], c0[None, :]] - lp[r0[:, None], c0[None, :]])
        + (rr[r1[:, None], c1[None, :]] - rr[r0[:, None], c1[None, :]])
    )
    bg_cnt = (n_nu * n_tau) - (r1 - r0)[:, None] * (c1 - c0)[None, :]
    grid = rd_map / np.maximum(bg_sum / bg_cnt, 1e-15)
    flat_idx = int(np.argmax(grid))
    ni_hat, ti_hat = divmod(flat_idx, n_tau)
    return float(grid[ni_hat, ti_hat]), (ni_hat, ti_hat), grid


def build_exact_rc_phi(S_time_list, c1_v, mu_v, dnu_los, is_mov=True):
    stream = np.concatenate([base.make_cpp_centered(s, c1_v) for s in S_time_list])
    up = np.zeros(L_TOT * 2, dtype=np.complex128)
    up[::2] = stream
    S_rc_f = np.fft.fft(up, N_FFT2) * H_RC2_F
    r_ct = np.fft.ifft(S_rc_f[None, :] * SHIFTS_ALL2, axis=1)
    r_d = r_ct[:, 2 * L_HALF2 : 2 * L_HALF2 + L_TOT * 2 : 2][:, BODY_IDX]
    if is_mov and abs(mu_v - base.MU_MOV) < 1e-12:
        e_rm = E_RIDGE_MOV
    elif not is_mov and abs(mu_v) < 1e-12:
        e_rm = np.ones((len(TAU_KNOTS), base.M_SYM * base.N), dtype=np.complex128)
    else:
        e_rm = np.exp(2j * np.pi * np.outer(mu_v * TAU_KNOTS, T_ALL.ravel()) / float(base.N))
    bodies = r_d[1:] * e_rm
    cols = [bodies.T * U_T3[:, :, p].ravel()[:, None] for p in range(3)]
    los_col = r_d[0] * np.exp(2j * np.pi * dnu_los * T_ALL.ravel() / float(base.N))
    cols.append(los_col[:, None])
    return np.hstack(cols)


def qr_project_exact_rc(R_stack, S_time_list, c1_v, mu_v, dnu_los, is_mov=True, reg=1.0):
    Phi = build_exact_rc_phi(S_time_list, c1_v, mu_v, dnu_los, is_mov=is_mov)
    Qp, _ = la.qr(Phi, mode="economic")
    res_stack = R_stack - Qp @ (Qp.conj().T @ R_stack)
    R_res_l = [res_stack[m * base.N : (m + 1) * base.N] for m in range(base.M_SYM)]
    G = Phi.conj().T @ Phi
    b = Phi.conj().T @ R_stack
    scale = max(float(np.real(np.mean(np.diag(G)))), 1.0)
    ch_em = la.solve(G + (reg * scale / float(base.M_SYM * base.N)) * np.eye(Phi.shape[1]), b, assume_a="pos")
    return ch_em, R_res_l, res_stack, Phi


def ep_16_fast(Hd, y_d, s2_e, n_it=5):
    """Algebraically equivalent HPD Cholesky solver to base.ep_16 (single-scene 7-arm parity max_rel_diff=3.65e-12; preserves finite checks)."""
    Nd = Hd.shape[1]
    G = Hd.conj().T @ Hd
    Hty = Hd.conj().T @ y_d
    inv_s2 = 1.0 / s2_e
    Gs = G * inv_s2
    Hty_s = Hty * inv_s2
    gam = np.zeros(Nd, dtype=np.complex128)
    lam = np.ones(Nd)
    eye_n = np.eye(Nd, dtype=np.complex128)
    idx_diag = np.arange(Nd)
    for _ in range(n_it):
        M = Gs.copy()
        M[idx_diag, idx_diag] += lam
        L = la.cholesky(M, lower=True, check_finite=True)
        Linv = la.solve_triangular(L, eye_n, lower=True, check_finite=True)
        vp = np.maximum(np.sum(Linv.real ** 2 + Linv.imag ** 2, axis=0), 1e-6)
        mu = la.cho_solve((L, True), Hty_s + gam, check_finite=True)
        te = np.maximum(1.0 / vp - lam, 1e-4)
        me = (mu / vp - gam) / te
        d2 = np.abs(me[:, None] - base.CONST16[None, :]) ** 2 * te[:, None]
        d2 -= np.min(d2, axis=1, keepdims=True)
        w = np.exp(-d2)
        w /= np.sum(w, axis=1, keepdims=True)
        xm = w @ base.CONST16
        vm = np.maximum(np.sum(w * np.abs(base.CONST16[None, :] - xm[:, None]) ** 2, axis=1), 1e-6)
        lr = np.maximum(1.0 / vm - te, 1e-3)
        mp = (xm / vm - me * te) / lr
        ln = np.minimum(lr, 1e4)
        lam = 0.6 * ln + 0.4 * lam
        gam = 0.6 * (ln * mp) + 0.4 * gam
    return base.CONST16[np.argmin(np.abs(me[:, None] - base.CONST16[None, :]), axis=1)], xm


def refine_symbols_joint_em(R_cfo, ch, xp_v_list, dat_i_list, p_amp, Hq_list, A_arm, mu_v, dnu_los, s2_e, u_grp=None, pil_syms=()):
    """Unified coupled burst-wide Joint EP-EM symbol re-demodulation (supports comb, DBU, block-pilot & staggered-pilot)."""
    Q_k = len(TAU_KNOTS)
    c_los = ch[-1]
    A_los = G_RC_MAT @ A_arm.conj().T
    Xh_l, Xs_l = [], []
    for m in range(base.M_SYM):
        if m in pil_syms:
            Xh_l.append(None)
            Xs_l.append(xp_v_list[m].copy())
            continue
        e_slow_q = np.exp(2j * np.pi * mu_v * TAU_KNOTS * (m * base.STRIDE / float(base.N)))
        H_m = np.zeros((base.N, base.N), dtype=np.complex128)
        for p in range(3):
            cp = ch[p * Q_k : (p + 1) * Q_k] * e_slow_q
            H_m += U_T3[m, :, p][:, None] * np.tensordot(cp, Hq_list, axes=(0, 0))
        los_ph_m = np.exp(2j * np.pi * dnu_los * T_ALL[m] / float(base.N))
        H_m += c_los * (los_ph_m[:, None] * A_los)
        H_eff = (H_m @ u_grp) if (u_grp is not None) else H_m
        di = dat_i_list[m]
        xp_m = xp_v_list[m]
        xh_d, xs_d = ep_16_fast(H_eff[:, di] * p_amp, R_cfo[m] - H_eff @ xp_m, s2_e, n_it=5)
        Xh_l.append(xh_d)
        xs_sym = xp_m.copy()
        xs_sym[di] = xs_d * p_amp
        Xs_l.append((u_grp @ xs_sym) if (u_grp is not None) else xs_sym)
    return Xh_l, Xs_l


def run_band3_plus_los_custom(y_b, xp_vec, pil_idx, dat_idx, U_basis, U_pinv, M_los, u_grp=None, n_em=3):
    """Same Band-3 + 1-col LOS soft-EM supporting custom 24/28-pilot U_grp and pure empirical noise variance floor 1e-2."""
    p_amp = xp_vec[pil_idx[0]]
    h_hat = U_basis @ (U_pinv @ (y_b[pil_idx] / p_amp))
    s2_e = max(1e-2, float(np.mean(np.abs(y_b[pil_idx] - h_hat[pil_idx] * p_amp) ** 2)) * (len(pil_idx) / max(1.0, len(pil_idx) - base.R_F)))
    H_b = np.diag(h_hat)
    for it_em in range(n_em):
        xh_sym = xp_vec.copy()
        xs_sym = xp_vec.copy()
        if u_grp is None:
            if it_em == 0:
                yeq = y_b[dat_idx] / np.where(np.abs(h_hat[dat_idx]) > 1e-6, h_hat[dat_idx], 1e-6) / p_amp
                xh_d = base.CONST16[np.argmin(np.abs(yeq[:, None] - base.CONST16[None, :]), axis=1)]
                d2 = np.abs(yeq[:, None] - base.CONST16[None, :]) ** 2 * (np.abs(h_hat[dat_idx] * p_amp) ** 2 / s2_e)[:, None]
                d2 -= np.min(d2, axis=1, keepdims=True)
                ww = np.exp(-d2); ww /= np.sum(ww, axis=1, keepdims=True)
                xs_d = ww @ base.CONST16
            else:
                xh_d, xs_d = ep_16_fast(H_b[:, dat_idx] * p_amp, y_b - H_b @ xp_vec, s2_e, n_it=5)
            xh_sym[dat_idx] = xh_d * p_amp; xs_sym[dat_idx] = xs_d * p_amp
            xs_base = xs_sym
        else:
            H_eff = H_b @ u_grp
            xh_d, xs_d = ep_16_fast(H_eff[:, dat_idx] * p_amp, y_b - H_eff @ xp_vec, s2_e, n_it=5)
            xh_sym[dat_idx] = xh_d * p_amp; xs_sym[dat_idx] = xs_d * p_amp
            xs_base = u_grp @ xs_sym
        if M_los is not None:
            Phi = np.hstack([np.roll(xs_base, s)[:, None] * U_basis for s in [-1, 0, 1]] + [(M_los @ xs_base)[:, None]])
            ch = la.solve(Phi.conj().T @ Phi + 1e-5 * np.eye(3 * base.R_F + 1), Phi.conj().T @ y_b, assume_a="pos")
            H_b = ch[-1] * M_los
        else:
            Phi = np.hstack([np.roll(xs_base, s)[:, None] * U_basis for s in [-1, 0, 1]])
            ch = la.solve(Phi.conj().T @ Phi + 1e-5 * np.eye(3 * base.R_F), Phi.conj().T @ y_b, assume_a="pos")
            H_b = np.zeros((base.N, base.N), dtype=np.complex128)
        for idx_s, s_sh in enumerate([-1, 0, 1]):
            hv = U_basis @ ch[idx_s * base.R_F : (idx_s + 1) * base.R_F]
            for row in range(base.N):
                H_b[row, (row - s_sh) % base.N] += hv[row]
        s2_e = max(1e-2, float(np.mean(np.abs(y_b - Phi @ ch) ** 2)))
    return xh_d, xs_base, y_b - Phi @ ch


def run_ofdm_blkpil_blind(R_cfo, pil_only_dict, is_mov, Hq, nuq, act_i, n_em=3, genie_g=None, reg=1e-2):
    """Fix #2: Receives ONLY known pilot vectors `pil_only_dict[mp]` (zero access to unknown data symbols!)."""
    M_c = len(R_cfo)
    Q = len(Hq)
    p_amp = np.sqrt(base.N / float(len(act_i)))
    pil_syms = set(pil_only_dict.keys())
    P_list, y_list = [], []
    for mp, xp_m in pil_only_dict.items():
        ph = np.exp(2j * np.pi * nuq * (mp * base.STRIDE / float(base.N))) if is_mov else np.ones(Q)
        P_list.append((Hq @ xp_m).T * ph[None, :])
        y_list.append(R_cfo[mp])
    P0 = np.vstack(P_list)
    y0 = np.concatenate(y_list)
    if genie_g is not None:
        g_hat = genie_g.copy()
    else:
        cn = np.maximum(la.norm(P0, axis=0), 1e-12)
        P0n = P0 / cn[None, :]
        g_hat = la.solve(P0n.conj().T @ P0n + reg * np.eye(Q), P0n.conj().T @ y0, assume_a="pos") / cn
    Xs_l = [pil_only_dict[m].copy() if m in pil_syms else np.zeros(base.N, dtype=np.complex128) for m in range(M_c)]
    Xh_d_l = [None] * M_c
    # Pure empirical initial noise variance from pilot symbol residual (zero fixed constant / truth leak)
    s2_e = max(1e-2, float(np.mean(np.abs(y0 - P0 @ g_hat) ** 2)) * (len(y0) / max(1.0, len(y0) - Q)))
    for _ in range(n_em):
        rp = []
        for m in range(M_c):
            if m in pil_syms:
                continue
            ph = np.exp(2j * np.pi * nuq * (m * base.STRIDE / float(base.N))) if is_mov else np.ones(Q)
            Hm = np.tensordot(g_hat * ph, Hq, axes=(0, 0))
            xh, xs = ep_16_fast(Hm[:, act_i] * p_amp, R_cfo[m], s2_e, n_it=5)
            Xh_d_l[m] = xh
            xf = np.zeros(base.N, dtype=np.complex128)
            xf[act_i] = xs * p_amp
            Xs_l[m] = xf
            rp.append(float(np.mean(np.abs(R_cfo[m] - Hm @ xf) ** 2)))
        Ga = np.zeros((Q, Q), dtype=np.complex128)
        ba = np.zeros(Q, dtype=np.complex128)
        for m in range(M_c):
            ph = np.exp(2j * np.pi * nuq * (m * base.STRIDE / float(base.N))) if is_mov else np.ones(Q)
            Pm = (Hq @ Xs_l[m]).T * ph[None, :]
            Ga += Pm.conj().T @ Pm
            ba += Pm.conj().T @ R_cfo[m]
        g_hat = la.solve(Ga + 1e-4 * np.eye(Q), ba, assume_a="pos")
        s2_e = max(1e-2, float(np.mean(rp)))
    S_hat = [base.F_MAT.conj().T @ Xs_l[m] for m in range(M_c)]
    return Xh_d_l, S_hat


def run_ofdm_distpil_blind(R_cfo, pil_vec_list, is_mov, Hq, nuq, n_em=3, reg=1e-2):
    """Fix #2: Receives ONLY known pilot vectors `pil_vec_list[m]` (zero data symbols passed!)."""
    M_c = len(R_cfo)
    Q = len(Hq)
    p_amp = np.sqrt(base.N / float(len(base.ACT_OFDM)))
    Ga = np.zeros((Q, Q), dtype=np.complex128)
    ba = np.zeros(Q, dtype=np.complex128)
    Pp_list, yp_list = [], []
    for m in range(M_c):
        pi = PIL_DIST_OFDM[m]
        xp = pil_vec_list[m]
        ph = np.exp(2j * np.pi * nuq * (m * base.STRIDE / float(base.N))) if is_mov else np.ones(Q)
        Pm = (Hq @ xp).T * ph[None, :]
        Fmp = base.F_MAT[pi, :]
        Pp = Fmp @ Pm
        yp = Fmp @ R_cfo[m]
        Pp_list.append(Pp)
        yp_list.append(yp)
        Ga += Pp.conj().T @ Pp
        ba += Pp.conj().T @ yp
    cn = np.sqrt(np.maximum(np.real(np.diag(Ga)), 1e-12))
    g_hat = la.solve(Ga / np.outer(cn, cn) + reg * np.eye(Q), ba / cn, assume_a="pos") / cn
    P_all = np.vstack(Pp_list)
    y_all = np.concatenate(yp_list)
    Xs_l = [np.zeros(base.N, dtype=np.complex128) for _ in range(M_c)]
    Xh_d_l = [None] * M_c
    # Pure empirical initial noise variance from pilot bin residual (zero fixed constant / truth leak)
    s2_e = max(1e-2, float(np.mean(np.abs(y_all - P_all @ g_hat) ** 2)) * (len(y_all) / max(1.0, len(y_all) - Q)))
    for _ in range(n_em):
        rp = []
        for m in range(M_c):
            di = DAT_DIST_OFDM[m]
            xp = pil_vec_list[m]
            ph = np.exp(2j * np.pi * nuq * (m * base.STRIDE / float(base.N))) if is_mov else np.ones(Q)
            Hm = np.tensordot(g_hat * ph, Hq, axes=(0, 0))
            xh, xs = ep_16_fast(Hm[:, di] * p_amp, R_cfo[m] - Hm @ xp, s2_e, n_it=5)
            Xh_d_l[m] = xh
            xf = xp.copy()
            xf[di] = xs * p_amp
            Xs_l[m] = xf
            rp.append(float(np.mean(np.abs(R_cfo[m] - Hm @ xf) ** 2)))
        Ga = np.zeros((Q, Q), dtype=np.complex128)
        ba = np.zeros(Q, dtype=np.complex128)
        for m in range(M_c):
            ph = np.exp(2j * np.pi * nuq * (m * base.STRIDE / float(base.N))) if is_mov else np.ones(Q)
            Pm = (Hq @ Xs_l[m]).T * ph[None, :]
            Ga += Pm.conj().T @ Pm
            ba += Pm.conj().T @ R_cfo[m]
        g_hat = la.solve(Ga + 1e-4 * np.eye(Q), ba, assume_a="pos")
        s2_e = max(1e-2, float(np.mean(rp)))
    S_hat = [base.F_MAT.conj().T @ Xs_l[m] for m in range(M_c)]
    return Xh_d_l, S_hat


def eval_scene_worker(args):
    """
    Evaluate requested arms on ONE paired physical 3D scene with OSR=8 RRC beta=0.25.
    Fix #2: Returns ONLY (score, peak_idx) from blind detection; localization is checked
    STRICTLY AFTER threshold alarm inside `evaluate_arms`.
    """
    if len(args) == 9:
        scene_seed, is_mov, snr_t, arm_set, role, slope_err_pct, target_mode, verify_exact, clut_boost_db = args
    else:
        scene_seed, is_mov, snr_t, arm_set, role, slope_err_pct, target_mode, verify_exact = args
        clut_boost_db = 0.0
    if role not in ("cal", "val", "pos"):
        raise ValueError(f"Invalid role: {role}")
    if role in ("cal", "val"):
        if snr_t is not None:
            raise ValueError("G2 violation: snr_t must be None on cal/val frames")
    else:
        if snr_t is None:
            raise ValueError("Target frame must have non-None snr_t")

    rng = np.random.default_rng(int(scene_seed))
    local_counter = {}

    vT_cur = base.V_T_MOV if is_mov else np.zeros(3)
    mu_true = base.MU_MOV if is_mov else 0.0
    mu_tx = mu_true * (1.0 - slope_err_pct / 100.0)
    b_cur = base.B_MOV if is_mov else 0.0
    c1_tx = mu_tx / (2.0 * base.N)
    nu_los_cur = base.NU_LOS_MOV if is_mov else 0.0
    dnu_los_cur = (nu_los_cur - b_cur) if is_mov else 0.0

    xq = rng.uniform(base.X0, base.X1, base.N_CLUT)
    yq = rng.uniform(-base.WY / 2.0, base.WY / 2.0, base.N_CLUT)
    tc, ncv, _ = base.bistatic_3d(xq, yq, np.zeros(base.N_CLUT), vT_cur)
    ac = (rng.standard_normal(base.N_CLUT) + 1j * rng.standard_normal(base.N_CLUT)) / np.sqrt(2.0 * base.N_CLUT) * (10.0 ** ((28.0 + clut_boost_db) / 20.0))
    alos = np.exp(1j * rng.uniform(0, 2 * np.pi)) * (10.0 ** ((18.0 + clut_boost_db) / 20.0))
    paths = [(alos, 0.0, nu_los_cur)] + [(a, float(t), float(v)) for a, t, v in zip(ac, tc, ncv)]

    true_cell = None
    if snr_t is not None:
        if target_mode == "nominal":
            tau_t = base.TAU_TARG
            nu_t = base.NU_TARG_MOV if is_mov else base.DNU_TARG_PHYS
        elif target_mode == "blind_speed":
            tau_t = base.TAU_TARG
            nu_t = b_cur + mu_true * tau_t + 2.0 * (float(base.N) / float(base.STRIDE))
        elif target_mode == "random":
            tau_t = float(rng.uniform(2.5, 11.5))
            dnu_rand = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.6, 3.0))
            nu_t = b_cur + mu_true * tau_t + dnu_rand
        else:
            raise ValueError(f"Unknown target_mode: {target_mode}")
        ni_true = int(np.argmin(np.abs(base.DNU_GRID - (nu_t - (b_cur + mu_tx * tau_t)))))
        ti_true = int(np.argmin(np.abs(base.TAU_GRID - tau_t)))
        true_cell = [ni_true, ti_true]
        paths.append((np.exp(1j * rng.uniform(0, 2 * np.pi)) * (10.0 ** (snr_t / 20.0)), tau_t, nu_t))
    else:
        if len(paths) != base.N_CLUT + 1:
            raise ValueError("G2 violation: cal/val path count mismatch")

    noise_l = [(rng.standard_normal(base.N) + 1j * rng.standard_normal(base.N)) / np.sqrt(2.0) for _ in range(base.M_SYM)]
    # Fix #2: ONE shared master 16-QAM payload stream sliced deterministically across all arms!
    master_qam = rng.choice(base.CONST16, size=(base.M_SYM, len(base.ACT_OFDM)))
    pil_blk_phases = [np.exp(1j * rng.uniform(0, 2 * np.pi, len(base.ACT_OFDM))) for _ in range(base.M_SYM)]

    data_169 = [master_qam[m, : len(DAT_AFDM_169)] for m in range(base.M_SYM)]
    data_195 = [master_qam[m, : len(DAT_OFDM_195)] for m in range(base.M_SYM)]
    data_blk = [master_qam[m, :] for m in range(base.M_SYM)]
    data_dist = [master_qam[m, : len(DAT_DIST_OFDM[m])] for m in range(base.M_SYM)]

    A_tx = base.A_MOV if (is_mov and slope_err_pct == 0.0) else (A_STAT if not is_mov else base.daft_centered(c1_tx))
    M_los_af = (
        base.M_LOS_AFDM_MOV
        if (is_mov and slope_err_pct == 0.0)
        else (A_tx @ (np.exp(2j * np.pi * dnu_los_cur * base.N_IDX / float(base.N))[:, None] * A_tx.conj().T) if is_mov else None)
    )
    Hq_af = HQ_AFDM_MOV if (is_mov and slope_err_pct == 0.0) else (HQ_STAT_0 if not is_mov else _build_hq_waveform(TAU_KNOTS, mu_tx, c1_tx, A_tx))
    Hq_of_em = HQ_OFDM_MOV_LIN if is_mov else HQ_STAT_0
    # Fix #1: Shared linear-ridge prior for OFDM initialization too (zero extra curvature curve!)
    Hq_of_init = HQ_OFDM_LIN_MOV if is_mov else HQ_OFDM_LIN_STAT
    nuq_of_init = NU_Q_LIN_MOV if is_mov else NU_Q_LIN_STAT

    out_arms = {}
    exact_max_rel_err = 0.0
    swap_diag = {}

    def record_arm(name, rdp, ser_val):
        nonlocal exact_max_rel_err
        sc, (ni_h, ti_h), grid = score_cut_full_map(rdp, role=role, counter=local_counter)
        if verify_exact:
            for ni_c in range(rdp.shape[0]):
                for ti_c in range(rdp.shape[1]):
                    ref = score_cut(rdp, (ni_c, ti_c), role="verify", counter=None)
                    re = abs(float(grid[ni_c, ti_c]) - ref) / max(abs(ref), 1e-15)
                    if re > exact_max_rel_err:
                        exact_max_rel_err = re
        out_arms[name] = {
            "score": float(sc),
            "score_db": float(10.0 * np.log10(sc)),
            "peak_idx": [int(ni_h), int(ti_h)],
            "ser": float(ser_val),
        }

    # --- Group A: AFDM comb arms (24/193 = 12.44% pilot overhead <= 12.50%) ---
    af_arms = [a for a in arm_set if a in ("ridge_afdm_st", "k01_orig", "burst_em0", "known_afdm_st")]
    if af_arms:
        p_af = np.sqrt(base.N / float(len(base.ACT_AFDM)))
        syms_af, Xf_af = [], []
        for m in range(base.M_SYM):
            xf = np.zeros(base.N, dtype=np.complex128)
            xf[PIL_AFDM_24] = p_af
            xf[DAT_AFDM_169] = data_169[m] * p_af
            syms_af.append(base.make_cpp_centered(A_tx.conj().T @ xf, c1_tx))
            Xf_af.append(xf)
        R_raw_af = base.apply_real_rrc_frame(syms_af, paths)
        R_cfo_af = [(R_raw_af[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
        R_stack_af = np.concatenate(R_cfo_af)
        xp_af = np.zeros(base.N, dtype=np.complex128)
        xp_af[PIL_AFDM_24] = p_af

        if "known_afdm_st" in af_arms:
            S_true_af = [A_tx.conj().T @ Xf_af[m] for m in range(base.M_SYM)]
            _, R_res_ka, _, _ = qr_project_exact_rc(R_stack_af, S_true_af, c1_tx, mu_tx, dnu_los_cur, is_mov=is_mov)
            record_arm("known_afdm_st", base.compute_rd_map(R_res_ka, S_true_af, c1_tx, mu_tx), 0.0)

        if any(a in af_arms for a in ("ridge_afdm_st", "k01_orig", "burst_em0")):
            Xh_s1, R_res_k01, S_hat_s1 = [], [], []
            for m in range(base.M_SYM):
                xh_d, xs_b, y_res = run_band3_plus_los_custom(
                    A_tx @ R_cfo_af[m], xp_af, PIL_AFDM_24, DAT_AFDM_169,
                    base.U_F, U_F_PIL_AFDM24_PINV, M_los_af, u_grp=None, n_em=3
                )
                Xh_s1.append(xh_d)
                S_hat_s1.append(A_tx.conj().T @ xs_b)
                R_res_k01.append(A_tx.conj().T @ y_res)
            ser_s1 = float(np.mean([np.mean(np.abs(Xh_s1[m] - data_169[m]) > 1e-4) for m in range(base.M_SYM)]))

            if "k01_orig" in af_arms:
                record_arm("k01_orig", base.compute_rd_map(R_res_k01, S_hat_s1, c1_tx, mu_tx), ser_s1)

            if any(a in af_arms for a in ("burst_em0", "ridge_afdm_st")):
                ch0, R_res_em0, res_st0, _ = qr_project_exact_rc(R_stack_af, S_hat_s1, c1_tx, mu_tx, dnu_los_cur, is_mov=is_mov)
                if "burst_em0" in af_arms:
                    record_arm("burst_em0", base.compute_rd_map(R_res_em0, S_hat_s1, c1_tx, mu_tx), ser_s1)

                if "ridge_afdm_st" in af_arms:
                    s2_0 = max(1e-2, float(np.mean(np.abs(res_st0) ** 2)))
                    Xh_s2, Xs_s2 = refine_symbols_joint_em(
                        R_cfo_af, ch0, [xp_af] * base.M_SYM, [DAT_AFDM_169] * base.M_SYM,
                        p_af, Hq_af, A_tx, mu_tx, dnu_los_cur, s2_0, u_grp=None
                    )
                    S_hat_s2 = [A_tx.conj().T @ Xs_s2[m] for m in range(base.M_SYM)]
                    _, R_res_em1, _, _ = qr_project_exact_rc(R_stack_af, S_hat_s2, c1_tx, mu_tx, dnu_los_cur, is_mov=is_mov)
                    ser_s2 = float(np.mean([np.mean(np.abs(Xh_s2[m] - data_169[m]) > 1e-4) for m in range(base.M_SYM)]))
                    record_arm("ridge_afdm_st", base.compute_rd_map(R_res_em1, S_hat_s2, c1_tx, mu_tx), ser_s2)

                    if role == "pos" and "burst_em0" in af_arms:
                        s_r1s0, _, _ = score_cut_full_map(base.compute_rd_map(R_res_em1, S_hat_s1, c1_tx, mu_tx))
                        s_r0s1, _, _ = score_cut_full_map(base.compute_rd_map(R_res_em0, S_hat_s2, c1_tx, mu_tx))
                        swap_diag = {
                            "swap_R1S0_db": float(10.0 * np.log10(s_r1s0)),
                            "swap_R0S1_db": float(10.0 * np.log10(s_r0s1)),
                        }

    # --- Group B: OFDM Comb (28/223 = 12.56%) & KnownS-OFDM ---
    if any(a in arm_set for a in ("ofdm_comb_st", "known_ofdm_st")):
        p_of = np.sqrt(base.N / float(len(base.ACT_OFDM)))
        syms_oc, Xf_oc = [], []
        for m in range(base.M_SYM):
            xf = np.zeros(base.N, dtype=np.complex128)
            xf[PIL_OFDM_28] = p_of
            xf[DAT_OFDM_195] = data_195[m] * p_of
            syms_oc.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
            Xf_oc.append(xf)
        R_raw_oc = base.apply_real_rrc_frame(syms_oc, paths)
        R_cfo_oc = [(R_raw_oc[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
        R_stack_oc = np.concatenate(R_cfo_oc)

        if "known_ofdm_st" in arm_set:
            S_true_oc = [base.F_MAT.conj().T @ Xf_oc[m] for m in range(base.M_SYM)]
            _, R_res_ko, _, _ = qr_project_exact_rc(R_stack_oc, S_true_oc, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
            record_arm("known_ofdm_st", base.compute_rd_map(R_res_ko, S_true_oc, 0.0, mu_true), 0.0)

        if "ofdm_comb_st" in arm_set:
            xp_of = np.zeros(base.N, dtype=np.complex128)
            xp_of[PIL_OFDM_28] = p_of
            M_los_of = base.M_LOS_OFDM_MOV if is_mov else None
            S_s1_oc = []
            for m in range(base.M_SYM):
                _, xs_b, _ = run_band3_plus_los_custom(
                    base.F_MAT @ R_cfo_oc[m], xp_of, PIL_OFDM_28, DAT_OFDM_195,
                    base.U_F_OFDM_RC, U_F_PIL_OFDM28_PINV, M_los_of, u_grp=None, n_em=3
                )
                S_s1_oc.append(base.F_MAT.conj().T @ xs_b)
            ch_oc, _, res_st_oc, _ = qr_project_exact_rc(R_stack_oc, S_s1_oc, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
            s2_oc = max(1e-2, float(np.mean(np.abs(res_st_oc) ** 2)))
            Xh_oc, Xs_oc = refine_symbols_joint_em(
                R_cfo_oc, ch_oc, [xp_of] * base.M_SYM, [DAT_OFDM_195] * base.M_SYM,
                p_of, Hq_of_em, base.F_MAT, mu_true, dnu_los_cur, s2_oc, u_grp=None
            )
            S_s2_oc = [base.F_MAT.conj().T @ Xs_oc[m] for m in range(base.M_SYM)]
            _, R_res_oc, _, _ = qr_project_exact_rc(R_stack_oc, S_s2_oc, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
            ser_oc = float(np.mean([np.mean(np.abs(Xh_oc[m] - data_195[m]) > 1e-4) for m in range(base.M_SYM)]))
            record_arm("ofdm_comb_st", base.compute_rd_map(R_res_oc, S_s2_oc, 0.0, mu_true), ser_oc)

    # --- Group C: DBU-OFDM Proxy (28/223 = 12.56%) + SAME Exact-RC ST-EM ---
    if "dbu_ofdm_st" in arm_set:
        p_of = np.sqrt(base.N / float(len(base.ACT_OFDM)))
        xp_of = np.zeros(base.N, dtype=np.complex128)
        xp_of[PIL_OFDM_28] = p_of
        syms_db = []
        for m in range(base.M_SYM):
            xsym = np.zeros(base.N, dtype=np.complex128)
            xsym[PIL_OFDM_28] = p_of
            xsym[DAT_OFDM_195] = data_195[m] * p_of
            xf = U_GRP_OFDM28 @ xsym
            syms_db.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
        R_raw_db = base.apply_real_rrc_frame(syms_db, paths)
        R_cfo_db = [(R_raw_db[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
        R_stack_db = np.concatenate(R_cfo_db)
        M_los_of = base.M_LOS_OFDM_MOV if is_mov else None
        S_s1_db = []
        for m in range(base.M_SYM):
            _, xs_b, _ = run_band3_plus_los_custom(
                base.F_MAT @ R_cfo_db[m], xp_of, PIL_OFDM_28, DAT_OFDM_195,
                base.U_F_OFDM_RC, U_F_PIL_OFDM28_PINV, M_los_of, u_grp=U_GRP_OFDM28, n_em=3
            )
            S_s1_db.append(base.F_MAT.conj().T @ xs_b)
        ch_db, _, res_st_db, _ = qr_project_exact_rc(R_stack_db, S_s1_db, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
        s2_db = max(1e-2, float(np.mean(np.abs(res_st_db) ** 2)))
        Xh_db, Xs_db = refine_symbols_joint_em(
            R_cfo_db, ch_db, [xp_of] * base.M_SYM, [DAT_OFDM_195] * base.M_SYM,
            p_of, Hq_of_em, base.F_MAT, mu_true, dnu_los_cur, s2_db, u_grp=U_GRP_OFDM28
        )
        S_s2_db = [base.F_MAT.conj().T @ Xs_db[m] for m in range(base.M_SYM)]
        _, R_res_db, _, _ = qr_project_exact_rc(R_stack_db, S_s2_db, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
        ser_db = float(np.mean([np.mean(np.abs(Xh_db[m] - data_195[m]) > 1e-4) for m in range(base.M_SYM)]))
        record_arm("dbu_ofdm_st", base.compute_rd_map(R_res_db, S_s2_db, 0.0, mu_true), ser_db)

    # --- Group D: OFDM Block-Pilot (1/8 = 12.50%) + SAME Exact-RC ST-EM feedback ---
    if any(a in arm_set for a in ("ofdm_blkpil_st", "ofdm_genie_st")):
        p_of = np.sqrt(base.N / float(len(base.ACT_OFDM)))
        syms_bp, Xf_bp = [], []
        pil_only_bp = {}
        xp_zero = np.zeros(base.N, dtype=np.complex128)
        for m in range(base.M_SYM):
            xf = np.zeros(base.N, dtype=np.complex128)
            if m == 0:
                xf[base.ACT_OFDM] = pil_blk_phases[m] * p_of
                pil_only_bp[0] = xf.copy()
            else:
                xf[base.ACT_OFDM] = data_blk[m] * p_of
            syms_bp.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
            Xf_bp.append(xf)
        R_raw_bp = base.apply_real_rrc_frame(syms_bp, paths)
        R_cfo_bp = [(R_raw_bp[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
        R_stack_bp = np.concatenate(R_cfo_bp)
        xp_list_bp = [pil_only_bp[0] if m == 0 else xp_zero for m in range(base.M_SYM)]
        di_list_bp = [base.ACT_OFDM for _ in range(base.M_SYM)]

        if "ofdm_blkpil_st" in arm_set:
            _, S_bp1 = run_ofdm_blkpil_blind(R_cfo_bp, pil_only_bp, is_mov, Hq_of_init, nuq_of_init, base.ACT_OFDM, n_em=3, genie_g=None, reg=1e-2)
            ch_bp, _, res_bp0, _ = qr_project_exact_rc(R_stack_bp, S_bp1, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
            s2_bp = max(1e-2, float(np.mean(np.abs(res_bp0) ** 2)))
            Xh_bp, Xs_bp = refine_symbols_joint_em(
                R_cfo_bp, ch_bp, xp_list_bp, di_list_bp, p_of, Hq_of_em, base.F_MAT, mu_true, dnu_los_cur, s2_bp, u_grp=None, pil_syms=(0,)
            )
            S_bp2 = [base.F_MAT.conj().T @ Xs_bp[m] for m in range(base.M_SYM)]
            _, R_res_bp, _, _ = qr_project_exact_rc(R_stack_bp, S_bp2, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
            ser_bp = float(np.mean([np.mean(np.abs(Xh_bp[m] - data_blk[m]) > 1e-4) for m in range(1, base.M_SYM)]))
            record_arm("ofdm_blkpil_st", base.compute_rd_map(R_res_bp, S_bp2, 0.0, mu_true), ser_bp)

        if "ofdm_genie_st" in arm_set:
            Q = len(Hq_of_init)
            R_clut_bp = base.apply_real_rrc_frame(syms_bp, paths[: base.N_CLUT + 1])
            R_cc_bp = [R_clut_bp[m] * np.exp(-2j * np.pi * b_cur * T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
            Ga = np.zeros((Q, Q), dtype=np.complex128); ba = np.zeros(Q, dtype=np.complex128)
            for m in range(base.M_SYM):
                ph = np.exp(2j * np.pi * nuq_of_init * (m * base.STRIDE / float(base.N))) if is_mov else np.ones(Q)
                Pm = (Hq_of_init @ Xf_bp[m]).T * ph[None, :]
                Ga += Pm.conj().T @ Pm; ba += Pm.conj().T @ R_cc_bp[m]
            gg = la.solve(Ga + 1e-3 * np.eye(Q), ba, assume_a="pos")
            Xh_gn, S_gn = run_ofdm_blkpil_blind(R_cfo_bp, pil_only_bp, is_mov, Hq_of_init, nuq_of_init, base.ACT_OFDM, n_em=3, genie_g=gg, reg=1e-2)
            _, R_res_gn, _, _ = qr_project_exact_rc(R_stack_bp, S_gn, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
            ser_gn = float(np.mean([np.mean(np.abs(Xh_gn[m] - data_blk[m]) > 1e-4) for m in range(1, base.M_SYM)]))
            record_arm("ofdm_genie_st", base.compute_rd_map(R_res_gn, S_gn, 0.0, mu_true), ser_gn)

    # --- Group E: OFDM 12.50% Time-Distributed Staggered Pilots + SAME Exact-RC ST-EM feedback ---
    if "ofdm_distpil_st" in arm_set:
        p_of = np.sqrt(base.N / float(len(base.ACT_OFDM)))
        syms_dp, pil_vecs_dp = [], []
        for m in range(base.M_SYM):
            xp = np.zeros(base.N, dtype=np.complex128)
            xp[PIL_DIST_OFDM[m]] = p_of
            pil_vecs_dp.append(xp)
            xf = xp.copy()
            xf[DAT_DIST_OFDM[m]] = data_dist[m] * p_of
            syms_dp.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
        R_raw_dp = base.apply_real_rrc_frame(syms_dp, paths)
        R_cfo_dp = [(R_raw_dp[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
        R_stack_dp = np.concatenate(R_cfo_dp)
        _, S_dp1 = run_ofdm_distpil_blind(R_cfo_dp, pil_vecs_dp, is_mov, Hq_of_init, nuq_of_init, n_em=3, reg=1e-2)
        ch_dp, _, res_dp0, _ = qr_project_exact_rc(R_stack_dp, S_dp1, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
        s2_dp = max(1e-2, float(np.mean(np.abs(res_dp0) ** 2)))
        Xh_dp, Xs_dp = refine_symbols_joint_em(
            R_cfo_dp, ch_dp, pil_vecs_dp, DAT_DIST_OFDM, p_of, Hq_of_em, base.F_MAT, mu_true, dnu_los_cur, s2_dp, u_grp=None
        )
        S_dp2 = [base.F_MAT.conj().T @ Xs_dp[m] for m in range(base.M_SYM)]
        _, R_res_dp, _, _ = qr_project_exact_rc(R_stack_dp, S_dp2, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
        ser_dp = float(np.mean([np.mean(np.abs(Xh_dp[m] - data_dist[m]) > 1e-4) for m in range(base.M_SYM)]))
        record_arm("ofdm_distpil_st", base.compute_rd_map(R_res_dp, S_dp2, 0.0, mu_true), ser_dp)

    # --- Group F: OFDM Double-Pilot (25%) + SAME Exact-RC QR ---
    if "ofdm_2pil_st" in arm_set:
        p_of = np.sqrt(base.N / float(len(base.ACT_OFDM)))
        syms_2p = []
        pil_only_2p = {}
        for m in range(base.M_SYM):
            xf = np.zeros(base.N, dtype=np.complex128)
            if m in (0, 4):
                xf[base.ACT_OFDM] = pil_blk_phases[m] * p_of
                pil_only_2p[m] = xf.copy()
            else:
                xf[base.ACT_OFDM] = data_blk[m] * p_of
            syms_2p.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
        R_raw_2p = base.apply_real_rrc_frame(syms_2p, paths)
        R_cfo_2p = [(R_raw_2p[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
        R_stack_2p = np.concatenate(R_cfo_2p)
        Xh_2p, S_2p = run_ofdm_blkpil_blind(R_cfo_2p, pil_only_2p, is_mov, Hq_of_init, nuq_of_init, base.ACT_OFDM, n_em=3, genie_g=None, reg=1e-2)
        _, R_res_2p, _, _ = qr_project_exact_rc(R_stack_2p, S_2p, 0.0, mu_true, dnu_los_cur, is_mov=is_mov)
        ser_2p = float(np.mean([np.mean(np.abs(Xh_2p[m] - data_blk[m]) > 1e-4) for m in range(base.M_SYM) if m not in (0, 4)]))
        record_arm("ofdm_2pil_st", base.compute_rd_map(R_res_2p, S_2p, 0.0, mu_true), ser_2p)

    return {"arms": out_arms, "true_cell": true_cell, "score_calls": local_counter, "exact_max_rel_err": exact_max_rel_err, "swap_diag": swap_diag}


def run_g1_and_bw_gates():
    rng = np.random.default_rng(31415926)
    syn_map = rng.exponential(1.0, size=(141, 29))
    syn_map[70, 14] = 1e10
    _, _, syn_grid = score_cut_full_map(syn_map)
    syn_rel_err = 0.0
    for ni in range(141):
        for ti in range(29):
            ref = score_cut(syn_map, (ni, ti))
            re = abs(float(syn_grid[ni, ti]) - ref) / max(abs(ref), 1e-15)
            if re > syn_rel_err:
                syn_rel_err = re
    if syn_rel_err >= 1e-12:
        raise RuntimeError(f"G1 synthetic 1e10 rel error: {syn_rel_err}")

    # Fix #3: Verify OSR=2 Exact-RC filter approximation relative norm error (< 1.5%) on single-path impulse
    x_imp = np.zeros((base.M_SYM, base.N), dtype=np.complex128)
    x_imp[3, 90] = 1.0
    j_t = 12
    tau_t = float(TAU_KNOTS[j_t])
    dnu_t = base.MU_MOV * tau_t
    tx_imp = [base.make_cpp_centered(s, base.C1_MOV) for s in x_imp]
    t_flat = T_ALL.ravel()
    y_imp = np.concatenate(base.apply_real_rrc_frame(tx_imp, [(1.0 + 0j, tau_t, dnu_t + base.B_MOV)])) * np.exp(-2j * np.pi * base.B_MOV * t_flat / float(base.N))
    p_imp = build_exact_rc_phi(x_imp, base.C1_MOV, base.MU_MOV, 0.0)[:, j_t] / U_T3[:, :, 0].ravel()
    g_fit = np.vdot(p_imp, y_imp) / np.vdot(p_imp, p_imp)
    rc_approx_rel_err = float(la.norm(y_imp - g_fit * p_imp) / la.norm(y_imp))
    if rc_approx_rel_err >= 0.015:
        raise RuntimeError(f"G1 RC approx error too large: {rc_approx_rel_err}")

    # Fix #1: Measure post-RRC 99% occupied BW across ALL 5 primary arms!
    def measure_99_bw(arm_name):
        psd = None
        for _ in range(10):
            syms = []
            for m in range(base.M_SYM):
                xf = np.zeros(base.N, dtype=np.complex128)
                if arm_name == "ridge_afdm_st":
                    p_a = np.sqrt(base.N / float(len(base.ACT_AFDM)))
                    xf[PIL_AFDM_24] = p_a; xf[DAT_AFDM_169] = rng.choice(base.CONST16, len(DAT_AFDM_169)) * p_a
                    syms.append(base.make_cpp_centered(base.A_MOV.conj().T @ xf, base.C1_MOV))
                elif arm_name == "ofdm_comb_st":
                    p_a = np.sqrt(base.N / float(len(base.ACT_OFDM)))
                    xf[PIL_OFDM_28] = p_a; xf[DAT_OFDM_195] = rng.choice(base.CONST16, len(DAT_OFDM_195)) * p_a
                    syms.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
                elif arm_name == "dbu_ofdm_st":
                    p_a = np.sqrt(base.N / float(len(base.ACT_OFDM)))
                    xs = np.zeros(base.N, dtype=np.complex128); xs[PIL_OFDM_28] = p_a; xs[DAT_OFDM_195] = rng.choice(base.CONST16, len(DAT_OFDM_195)) * p_a
                    xf = U_GRP_OFDM28 @ xs
                    syms.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
                elif arm_name == "ofdm_blkpil_st":
                    p_a = np.sqrt(base.N / float(len(base.ACT_OFDM)))
                    xf[base.ACT_OFDM] = (np.exp(1j * rng.uniform(0, 2 * np.pi, len(base.ACT_OFDM))) if m == 0 else rng.choice(base.CONST16, len(base.ACT_OFDM))) * p_a
                    syms.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
                elif arm_name == "ofdm_distpil_st":
                    p_a = np.sqrt(base.N / float(len(base.ACT_OFDM)))
                    xf[PIL_DIST_OFDM[m]] = p_a; xf[DAT_DIST_OFDM[m]] = rng.choice(base.CONST16, len(DAT_DIST_OFDM[m])) * p_a
                    syms.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
            stream = np.concatenate(syms)
            up = np.zeros(len(stream) * base.OSR, dtype=np.complex128); up[:: base.OSR] = stream
            N_f = 1 << (len(up) + len(base.H_RRC) + 64).bit_length()
            S_f = np.fft.fft(up, N_f) * np.fft.fft(base.H_RRC, N_f)
            p_cur = np.abs(S_f) ** 2
            psd = p_cur if psd is None else (psd + p_cur)
        freqs = np.abs(np.fft.fftfreq(len(psd)) * base.OSR)
        order = np.argsort(freqs)
        cum = np.cumsum(psd[order]) / np.sum(psd)
        return 2.0 * float(freqs[order][np.searchsorted(cum, 0.99)])

    bw_map = {a: measure_99_bw(a) for a in PRIMARY_EQUAL_ARMS}
    bw_ok = bool(all(bw_map["ridge_afdm_st"] <= bw_map[r] + 0.005 for r in EQUAL_OFDM_RIVALS))
    pilot_ratios = {
        "ridge_afdm_st": len(PIL_AFDM_24) / float(len(base.ACT_AFDM)),
        "ofdm_comb_st": len(PIL_OFDM_28) / float(len(base.ACT_OFDM)),
        "dbu_ofdm_st": len(PIL_OFDM_28) / float(len(base.ACT_OFDM)),
        "ofdm_blkpil_st": 0.125,
        "ofdm_distpil_st": sum(len(p) for p in PIL_DIST_OFDM) / float(base.M_SYM * len(base.ACT_OFDM)),
    }
    pilot_ok = bool(all(pilot_ratios["ridge_afdm_st"] <= pilot_ratios[r] for r in EQUAL_OFDM_RIVALS))

    # Iron Rule 2 unimpaired high-SNR static health check (+38 dB clutter / +28 dB LOS, 6 scenes, exact production path)
    # plus 1 real S1 map exact-CUT strict relative error check (< 1e-12) right inside G1:
    hs_res = [
        eval_scene_worker((2026149900 + i, False, -11.0, PRIMARY_EQUAL_ARMS, "pos", 0.0, "nominal", False, 10.0))
        for i in range(6)
    ]
    hs_ser_raw = {a: float(np.mean([r["arms"][a]["ser"] for r in hs_res])) for a in PRIMARY_EQUAL_ARMS}
    hs_ser_ok = bool(all(hs_ser_raw[a] < 0.01 for a in PRIMARY_EQUAL_ARMS))
    real_s1_chk = eval_scene_worker((2026149999, True, -11.0, ["ridge_afdm_st"], "pos", 0.0, "nominal", True, 0.0))
    real_s1_rel_err = float(real_s1_chk["exact_max_rel_err"])
    if real_s1_rel_err >= 1e-12:
        raise RuntimeError(f"G1 real S1 map exact CUT rel error failed: {real_s1_rel_err}")

    return {
        "pass": bool(bw_ok and pilot_ok and hs_ser_ok and (syn_rel_err < 1e-12) and (real_s1_rel_err < 1e-12) and (rc_approx_rel_err < 0.015)),
        "syn1e10_max_rel_err": syn_rel_err,
        "real_s1_g1_max_rel_err": real_s1_rel_err,
        "rc_osr2_approx_rel_err": rc_approx_rel_err,
        "bw99_all5_fs": bw_map,
        "afdm_bw_le_all_ofdm": bw_ok,
        "pilot_ratios_all5": pilot_ratios,
        "afdm_pilot_le_all_ofdm": pilot_ok,
        "high_snr_static_ser_all5": hs_ser_raw,
        "high_snr_static_ser_under_1pct": hs_ser_ok,
    }


def clopper_pearson_ci(k, n, alpha=0.05):
    if n <= 0:
        return 0.0, 0.0, 1.0
    p = k / float(n)
    lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return p, lo, hi


def exact_order_stat_params(n_cal, pfa_target=0.01):
    """Exact order-statistic rank b so P = 1 - F(X_(b)) ~ Beta(a, b) with E[P] = a/(n_cal+1) ~= pfa_target."""
    a = max(1, int(round(pfa_target * (n_cal + 1))))
    b = n_cal + 1 - a
    if not (1 <= b <= n_cal):
        raise ValueError(f"Invalid order statistic rank b={b} for n_cal={n_cal}")
    return a, b


def evaluate_arms(cal_res, val_res, pos_res, arm_list, pfa_target=0.01, fwer_arms=12):
    """Strictly threshold alarm FIRST, then check localization against true_cell ONLY on alarmed frames."""
    summary = {}
    raw_arrays = {}
    true_cells = np.array([r["true_cell"] for r in pos_res], dtype=int) if (pos_res and pos_res[0]["true_cell"] is not None) else None

    for arm in arm_list:
        cal_s = np.array([r["arms"][arm]["score"] for r in cal_res], dtype=np.float64)
        pos_s = np.array([r["arms"][arm]["score"] for r in pos_res], dtype=np.float64)
        pos_peaks = np.array([r["arms"][arm]["peak_idx"] for r in pos_res], dtype=int)
        pos_ser = np.array([r["arms"][arm]["ser"] for r in pos_res], dtype=np.float64)

        a_bb, b_bb = exact_order_stat_params(len(cal_s), pfa_target)
        thr = float(np.partition(cal_s, b_bb - 1)[b_bb - 1])

        val_fields = {}
        if val_res is not None:
            val_s = np.array([r["arms"][arm]["score"] for r in val_res], dtype=np.float64)
            k_val = int(np.sum(val_s > thr))
            p_val, lo_v, hi_v = clopper_pearson_ci(k_val, len(val_s))
            # Exact finite-sample Beta-Binomial 12-arm FWER calibration interval (accounts for N_cal threshold variance)
            alpha_each = 0.05 / float(fwer_arms)
            k_lo_bb = int(betabinom_dist.ppf(alpha_each / 2.0, len(val_s), a_bb, b_bb))
            k_hi_bb = int(betabinom_dist.ppf(1.0 - alpha_each / 2.0, len(val_s), a_bb, b_bb))
            c1_pass = bool(k_lo_bb <= k_val <= k_hi_bb)
            val_fields = {
                "n_val": int(len(val_s)),
                "val_k_fa": k_val,
                "val_pfa_map": p_val,
                "val_ci95_cp": [lo_v, hi_v],
                "val_bb_fwer12_bounds_k": [k_lo_bb, k_hi_bb],
                "val_bb_fwer12_bounds_p": [k_lo_bb / float(len(val_s)), k_hi_bb / float(len(val_s))],
                "c1_pass": c1_pass,
            }

        # Strict alarm-first order:
        exceed = pos_s > thr
        det_loc = np.zeros(len(pos_s), dtype=np.float64)
        det_mis = np.zeros(len(pos_s), dtype=np.float64)
        for i in range(len(pos_s)):
            if exceed[i]:
                ni_h, ti_h = pos_peaks[i]
                ni_t, ti_t = true_cells[i]
                if abs(ni_h - ni_t) <= 2 and abs(ti_h - ti_t) <= 1:
                    det_loc[i] = 1.0
                else:
                    det_mis[i] = 1.0
        det_miss = (~exceed).astype(np.float64)

        k_loc = int(np.sum(det_loc))
        pd_loc, pd_lo, pd_hi = clopper_pearson_ci(k_loc, len(det_loc))

        summary[arm] = {
            "n_cal": int(len(cal_s)),
            **val_fields,
            "n_pos": int(len(pos_s)),
            "thr_linear": thr,
            "thr_db": float(10.0 * np.log10(thr)),
            "pos_k_loc": k_loc,
            "pos_pd_loc": pd_loc,
            "pos_pd_loc_ci95_cp": [pd_lo, pd_hi],
            "pos_pd_mis": float(np.mean(det_mis)),
            "pos_p_miss": float(np.mean(det_miss)),
            "pos_score_db_mean": float(np.mean(10.0 * np.log10(pos_s))),
            "pos_ser_mean": float(np.mean(pos_ser)),
        }
        raw_arrays[arm] = {
            "cal": cal_s,
            "pos": pos_s,
            "peaks": pos_peaks,
            "true_cells": true_cells,
            "det_loc": det_loc,
        }
    return summary, raw_arrays


def dual_bootstrap_delta_pd(raw_target, raw_rivals_dict, pfa_target=0.01, n_boot=2000, seed=2026130001):
    """
    Fix #4: Dual-bootstrap resampling BOTH cal and paired pos frames simultaneously.
    Strictly checks threshold alarm FIRST inside each bootstrap draw and evaluates
    localization against true_cells ONLY on alarmed frames (zero pre-alarm matching).
    """
    rival_names = list(raw_rivals_dict.keys())
    R = len(rival_names)
    n_cal = len(raw_target["cal"])
    n_pos = len(raw_target["pos"])

    r_pds = [float(np.mean(raw_rivals_dict[rn]["det_loc"])) for rn in rival_names]
    best_idx = int(np.argmax(r_pds))
    point = float(np.mean(raw_target["det_loc"]) - r_pds[best_idx])

    rng = np.random.default_rng(seed)
    idx_c = rng.integers(0, n_cal, size=(n_boot, n_cal))
    idx_p = rng.integers(0, n_pos, size=(n_boot, n_pos))

    def boot_pds(arr_d):
        c_boot = arr_d["cal"][idx_c]
        _, b_bb = exact_order_stat_params(n_cal, pfa_target)
        thrs = np.partition(c_boot, b_bb - 1, axis=1)[:, b_bb - 1 : b_bb]
        exceed = arr_d["pos"][idx_p] > thrs
        hits = np.zeros_like(exceed, dtype=np.float64)
        bi, fi = np.nonzero(exceed)
        if len(bi) > 0:
            orig_idx = idx_p[bi, fi]
            pk = arr_d["peaks"][orig_idx]
            tc = arr_d["true_cells"][orig_idx]
            ok = (np.abs(pk[:, 0] - tc[:, 0]) <= 2) & (np.abs(pk[:, 1] - tc[:, 1]) <= 1)
            hits[bi, fi] = ok.astype(np.float64)
        return np.mean(hits, axis=1)

    a_b = boot_pds(raw_target)
    r_bs = np.stack([boot_pds(raw_rivals_dict[rn]) for rn in rival_names], axis=0)  # (R, B)
    alpha_bonf = 0.05 / float(R)
    bonf_los = [float(np.quantile(a_b - r_bs[j], alpha_bonf / 2.0)) for j in range(R)]
    bonf_his = [float(np.quantile(a_b - r_bs[j], 1.0 - alpha_bonf / 2.0)) for j in range(R)]
    delta_sim = a_b - np.max(r_bs, axis=0)
    return {
        "best_rival": rival_names[best_idx],
        "point": point,
        "ci95_bonf_sim_lo": min(bonf_los),
        "ci95_bonf_sim_hi": max(bonf_his),
        "ci95_bonf_per_rival": {rn: [bonf_los[j], bonf_his[j]] for j, rn in enumerate(rival_names)},
        "ci95_sim_max_pct": [float(np.quantile(delta_sim, 0.025)), float(np.quantile(delta_sim, 0.975))],
        "boot_draws_per_rival": a_b[None, :] - r_bs,  # (R, B)
        "boot_draws_sim_max": delta_sim,
    }


def run_batch(pool, tasks):
    if pool is None:
        return [eval_scene_worker(t) for t in tasks]
    return pool.map(eval_scene_worker, tasks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026142501)
    ap.add_argument("--mode", choices=["g1_only", "smoke", "full"], default="smoke")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--n-cal-s1", type=int, default=1500)
    ap.add_argument("--n-val-s1", type=int, default=2000)
    ap.add_argument("--n-pos-s1", type=int, default=200)
    ap.add_argument("--n-cal-g0", type=int, default=400)
    ap.add_argument("--n-val-g0", type=int, default=400)
    ap.add_argument("--n-pos-g0", type=int, default=120)
    ap.add_argument("--n-cal-desc", type=int, default=150)
    ap.add_argument("--n-val-desc", type=int, default=150)
    ap.add_argument("--snr-inflect", type=float, default=-16.0)
    ap.add_argument("--snr-g0-slope", type=float, default=-21.5)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    t0 = time.time()
    out_abs = os.path.abspath(args.out)
    if os.path.basename(out_abs) == "summary_k_r11_k02.json":
        raise ValueError("Refusing to write to first-run artifact summary_k_r11_k02.json")
    if args.mode == "full" and os.path.basename(out_abs) != "summary_k_r11_k02_conf.json":
        raise ValueError(f"Formal full mode locks output basename summary_k_r11_k02_conf.json, got {os.path.basename(out_abs)}")
    if os.path.exists(out_abs):
        raise FileExistsError(f"Refusing to overwrite existing output file: {out_abs}")
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    if args.workers > 8:
        raise ValueError(f"Round-11 deinlab hard limit: workers={args.workers} > 8")

    g1_report = run_g1_and_bw_gates()
    print(f"[Gate G1] pass={g1_report['pass']} | syn1e10={g1_report['syn1e10_max_rel_err']:.2e} | rc_approx={g1_report['rc_osr2_approx_rel_err']:.4f} | BW99={g1_report['bw99_all5_fs']} | pilots={g1_report['pilot_ratios_all5']}", flush=True)
    if args.mode == "g1_only":
        with open(out_abs, "x") as f:
            json.dump({"g1": g1_report}, f, indent=2)
        return

    if args.mode == "smoke":
        n_cal_s1, n_val_s1, n_pos_s1 = 15, 15, 10
        n_cal_g0, n_val_g0, n_pos_g0 = 10, 10, 8
        n_cal_desc, n_val_desc = 10, 10
        n_stress = 6
    else:
        # Fix #5: Hard-lock ALL formal-mode frozen parameters with explicit RuntimeError/ValueError (immune to python -O)
        if args.seed != 2026142501:
            raise ValueError(f"Formal full mode locks seed=2026142501, got {args.seed}")
        if args.snr_inflect != -16.0:
            raise ValueError(f"Formal full mode locks snr_inflect=-16.0, got {args.snr_inflect}")
        if args.snr_g0_slope != -21.5:
            raise ValueError(f"Formal full mode locks snr_g0_slope=-21.5, got {args.snr_g0_slope}")
        if (args.n_cal_s1, args.n_val_s1, args.n_pos_s1) != (1500, 2000, 200):
            raise ValueError("Formal full mode locks S1 sizes (1500, 2000, 200)")
        if (args.n_cal_g0, args.n_val_g0, args.n_pos_g0) != (400, 400, 120):
            raise ValueError("Formal full mode locks G0 sizes (400, 400, 120)")
        if (args.n_cal_desc, args.n_val_desc) != (150, 150):
            raise ValueError("Formal full mode locks desc sizes (150, 150)")
        n_cal_s1, n_val_s1, n_pos_s1 = 1500, 2000, 200
        n_cal_g0, n_val_g0, n_pos_g0 = 400, 400, 120
        n_cal_desc, n_val_desc = 150, 150
        n_stress = 60

    hist_seeds = set()
    hist_sources = [2026112501, 2026122501, 2026132501, 999888777]
    if args.mode == "smoke":
        hist_sources.append(2026142501)
    for hs in hist_sources:
        hist_seeds.update(int(x) for x in np.random.default_rng(hs).integers(1, 2**31 - 1, size=12000))

    effective_seed = (args.seed + 777777) if args.mode == "smoke" else args.seed
    rng_master = np.random.default_rng(effective_seed)
    n_needed = n_cal_s1 + n_val_s1 + 2 * n_pos_s1 + n_cal_g0 + n_val_g0 + 2 * n_pos_g0 + 4 * n_stress + n_cal_desc
    seed_set, seed_list = set(), []
    while len(seed_list) < n_needed:
        c = int(rng_master.integers(1, 2**31 - 1))
        if c not in seed_set and c not in hist_seeds:
            seed_set.add(c); seed_list.append(c)
    it = iter(seed_list); take = lambda k: [next(it) for _ in range(k)]

    cal_s1_seeds = take(n_cal_s1); val_s1_seeds = take(n_val_s1)
    pos11_s1_seeds = take(n_pos_s1); posinf_s1_seeds = take(n_pos_s1)
    cal_g0_seeds = take(n_cal_g0); val_g0_seeds = take(n_val_g0)
    pos11_g0_seeds = take(n_pos_g0); posslp_g0_seeds = take(n_pos_g0)
    bs_seeds = take(n_stress); rand_seeds = take(n_stress)
    se_cal_seeds = take(n_cal_desc); se_pos_seeds = take(n_stress)

    pool = Pool(processes=args.workers) if args.workers > 1 else None
    total_calls = {"cal": 0, "val": 0, "pos": 0}
    max_exact_rel_err = 0.0

    def accum(res_l):
        nonlocal max_exact_rel_err
        for r in res_l:
            for k, v in r["score_calls"].items():
                total_calls[k] = total_calls.get(k, 0) + v
            if r["exact_max_rel_err"] > max_exact_rel_err:
                max_exact_rel_err = r["exact_max_rel_err"]

    try:
        print(f"[S1 Main] cal={n_cal_s1}, val={n_val_s1}, pos(-11 & {args.snr_inflect})={n_pos_s1} on {len(ALL_PASS_ARMS)} arms...", flush=True)
        cal_s1 = run_batch(pool, [(s, True, None, ALL_PASS_ARMS, "cal", 0.0, "nominal", i == 0) for i, s in enumerate(cal_s1_seeds)])
        accum(cal_s1); print(f"  [S1 cal] done in {time.time()-t0:.1f}s", flush=True)
        val_s1 = run_batch(pool, [(s, True, None, ALL_PASS_ARMS, "val", 0.0, "nominal", i == 0) for i, s in enumerate(val_s1_seeds)])
        accum(val_s1); print(f"  [S1 val] done in {time.time()-t0:.1f}s", flush=True)
        pos11_s1 = run_batch(pool, [(s, True, -11.0, ALL_PASS_ARMS, "pos", 0.0, "nominal", i == 0) for i, s in enumerate(pos11_s1_seeds)])
        accum(pos11_s1)
        posinf_s1 = run_batch(pool, [(s, True, args.snr_inflect, ALL_PASS_ARMS, "pos", 0.0, "nominal", False) for s in posinf_s1_seeds])
        accum(posinf_s1); print(f"  [S1 pos] done in {time.time()-t0:.1f}s", flush=True)

        s1_11_sum, s1_11_raw = evaluate_arms(cal_s1, val_s1, pos11_s1, ALL_PASS_ARMS, 0.01)
        s1_inf_sum, s1_inf_raw = evaluate_arms(cal_s1, val_s1, posinf_s1, ALL_PASS_ARMS, 0.01)

        print(f"[S1 Desc] cal={n_cal_desc}, val={n_val_desc}, pos(-11)={n_pos_s1}...", flush=True)
        cal_desc = run_batch(pool, [(s, True, None, DESC_ARMS, "cal", 0.0, "nominal", False) for s in cal_s1_seeds[:n_cal_desc]])
        accum(cal_desc)
        val_desc = run_batch(pool, [(s, True, None, DESC_ARMS, "val", 0.0, "nominal", False) for s in val_s1_seeds[:n_val_desc]])
        accum(val_desc)
        pos_desc = run_batch(pool, [(s, True, -11.0, DESC_ARMS, "pos", 0.0, "nominal", False) for s in pos11_s1_seeds])
        accum(pos_desc)
        s1_desc_sum, _ = evaluate_arms(cal_desc, val_desc, pos_desc, DESC_ARMS, 0.01)

        print(f"[G0 Static] cal={n_cal_g0}, val={n_val_g0}, pos(-11 & {args.snr_g0_slope})={n_pos_g0}...", flush=True)
        cal_g0 = run_batch(pool, [(s, False, None, PRIMARY_EQUAL_ARMS, "cal", 0.0, "nominal", False) for s in cal_g0_seeds])
        accum(cal_g0)
        val_g0 = run_batch(pool, [(s, False, None, PRIMARY_EQUAL_ARMS, "val", 0.0, "nominal", False) for s in val_g0_seeds])
        accum(val_g0)
        pos11_g0 = run_batch(pool, [(s, False, -11.0, PRIMARY_EQUAL_ARMS, "pos", 0.0, "nominal", False) for s in pos11_g0_seeds])
        accum(pos11_g0)
        posslp_g0 = run_batch(pool, [(s, False, args.snr_g0_slope, PRIMARY_EQUAL_ARMS, "pos", 0.0, "nominal", False) for s in posslp_g0_seeds])
        accum(posslp_g0); print(f"  [G0 Static] done in {time.time()-t0:.1f}s", flush=True)

        g0_11_sum, _ = evaluate_arms(cal_g0, val_g0, pos11_g0, PRIMARY_EQUAL_ARMS, 0.01)
        g0_slp_sum, g0_slp_raw = evaluate_arms(cal_g0, val_g0, posslp_g0, PRIMARY_EQUAL_ARMS, 0.01)

        print(f"[Stress] blind_speed={n_stress}, random={n_stress}, slope2pct={n_stress}...", flush=True)
        pos_bs = run_batch(pool, [(s, True, -11.0, ["ridge_afdm_st", "k01_orig"], "pos", 0.0, "blind_speed", False) for s in bs_seeds])
        accum(pos_bs)
        pos_rand = run_batch(pool, [(s, True, -11.0, ["ridge_afdm_st", "k01_orig"], "pos", 0.0, "random", False) for s in rand_seeds])
        accum(pos_rand)
        cal_se = run_batch(pool, [(s, True, None, ["ridge_afdm_st"], "cal", 2.0, "nominal", False) for s in se_cal_seeds])
        accum(cal_se)
        pos_se = run_batch(pool, [(s, True, -11.0, ["ridge_afdm_st"], "pos", 2.0, "nominal", False) for s in se_pos_seeds])
        accum(pos_se)
        stress_bs, _ = evaluate_arms(cal_s1, val_s1, pos_bs, ["ridge_afdm_st", "k01_orig"], 0.01)
        stress_rand, _ = evaluate_arms(cal_s1, val_s1, pos_rand, ["ridge_afdm_st", "k01_orig"], 0.01)
        stress_se, _ = evaluate_arms(cal_se, None, pos_se, ["ridge_afdm_st"], 0.01)
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    if max_exact_rel_err >= 1e-12:
        raise RuntimeError(f"Real-map exact CUT rel error failed: {max_exact_rel_err}")

    swap_r1s0 = float(np.mean([r["swap_diag"]["swap_R1S0_db"] for r in posinf_s1 if r["swap_diag"]]))
    swap_r0s1 = float(np.mean([r["swap_diag"]["swap_R0S1_db"] for r in posinf_s1 if r["swap_diag"]]))

    # Fix #1, #4, #5: Frozen Verdicts with zero loopholes
    # Nominal +28 dB static G0 has theoretical flat/rolloff perfect-CSI Rayleigh 16-QAM estimate ~0.81%
    # (measured OSR=8 RRC ofdm_genie_st ~0.92%) on 223 bins;
    # G1 already verifies < 1.0% SER at unimpaired +38 dB static SNR, while G0 (-11 dB) gates < 2.0% across all 5 arms.
    g0_ser_ok = bool(all(g0_11_sum[a]["pos_ser_mean"] < 0.02 for a in PRIMARY_EQUAL_ARMS))
    g1_health_pass = bool(g1_report["pass"] and g0_ser_ok)

    # C1 covers ALL 7 S1 arms + 5 G0 primary arms via exact finite-sample 12-arm FWER Beta-Binomial
    # PLUS strict anti-inflation cap on our arm ridge_afdm_st (<= 1.75% on S1, <= 2.50% on G0)
    c1_s1_per_arm = {a: s1_11_sum[a]["c1_pass"] for a in ALL_PASS_ARMS}
    c1_g0_per_arm = {a: g0_slp_sum[a]["c1_pass"] for a in PRIMARY_EQUAL_ARMS}
    c1_afdm_no_inflate_s1 = bool(s1_11_sum["ridge_afdm_st"]["val_pfa_map"] <= 0.0175)
    c1_afdm_no_inflate_g0 = bool(g0_slp_sum["ridge_afdm_st"]["val_pfa_map"] <= 0.0250)
    c1_pass = bool(all(c1_s1_per_arm.values()) and all(c1_g0_per_arm.values()) and c1_afdm_no_inflate_s1 and c1_afdm_no_inflate_g0)

    c2_vs_ofdm = dual_bootstrap_delta_pd(s1_11_raw["ridge_afdm_st"], {r: s1_11_raw[r] for r in EQUAL_OFDM_RIVALS}, 0.01, 2000, args.seed + 101)
    c2_vs_k01 = dual_bootstrap_delta_pd(s1_11_raw["ridge_afdm_st"], {"k01_orig": s1_11_raw["k01_orig"]}, 0.01, 2000, args.seed + 102)
    c2_pass = bool(c2_vs_ofdm["ci95_bonf_sim_lo"] >= 0.50 and c2_vs_k01["ci95_bonf_sim_lo"] >= 0.50)

    c3_inf_vs_k01 = dual_bootstrap_delta_pd(s1_inf_raw["ridge_afdm_st"], {"k01_orig": s1_inf_raw["k01_orig"]}, 0.01, 2000, args.seed + 200)
    c3_em_vs_em0 = dual_bootstrap_delta_pd(s1_inf_raw["ridge_afdm_st"], {"burst_em0": s1_inf_raw["burst_em0"]}, 0.01, 2000, args.seed + 201)
    pd_st_inf = s1_inf_sum["ridge_afdm_st"]["pos_pd_loc"]
    pd_em0_inf = s1_inf_sum["burst_em0"]["pos_pd_loc"]
    pd_k01_inf = s1_inf_sum["k01_orig"]["pos_pd_loc"]
    em0_share = float((pd_em0_inf - pd_k01_inf) / max(pd_st_inf - pd_k01_inf, 1e-9))
    # Fix #5: Require full method beats k01 first (>= +0.50), beats em0 (> 0), AND em0_share < 0.80
    c3_ablation_pass = bool((c3_inf_vs_k01["ci95_bonf_sim_lo"] >= 0.50) and (c3_em_vs_em0["ci95_bonf_sim_lo"] > 0.0) and (em0_share < 0.80))

    c3_g0_slp = dual_bootstrap_delta_pd(g0_slp_raw["ridge_afdm_st"], {r: g0_slp_raw[r] for r in EQUAL_OFDM_RIVALS}, 0.01, 2000, args.seed + 301)
    # Fix #5: Explicit non-saturation check on G0 (-21.5 dB) + pre-specified advantage upper bound <= +0.15 + conservative DiD >= +0.50
    g0_pd_af = g0_slp_sum["ridge_afdm_st"]["pos_pd_loc"]
    g0_pd_best_of = max(g0_slp_sum[r]["pos_pd_loc"] for r in EQUAL_OFDM_RIVALS)
    g0_nonsat = bool((0.15 <= g0_pd_af <= 0.92) and (0.15 <= g0_pd_best_of <= 0.92))
    did_cons_draws = c2_vs_ofdm["boot_draws_sim_max"] - np.maximum(0.0, c3_g0_slp["boot_draws_sim_max"])
    did_cons_ci = [float(np.quantile(did_cons_draws, 0.025)), float(np.quantile(did_cons_draws, 0.975))]
    c3_g0_did_pass = bool(g0_nonsat and (c3_g0_slp["ci95_sim_max_pct"][1] <= 0.15) and (did_cons_ci[0] >= 0.50))
    c3_pass = bool(c3_ablation_pass and c3_g0_did_pass)

    pass_primary = bool(g1_health_pass and c1_pass and c2_pass and c3_pass)

    elapsed = time.time() - t0
    core_hours = (elapsed * args.workers) / 3600.0
    ru_s = resource.getrusage(resource.RUSAGE_SELF); ru_c = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_hours = (ru_s.ru_utime + ru_s.ru_stime + ru_c.ru_utime + ru_c.ru_stime) / 3600.0

    def strip(d):
        return {k: v for k, v in d.items() if not k.startswith("boot_draws")}

    summary = {
        "meta": {
            "card": "I-20261125-k02 (confirmatory fresh-seed run)",
            "parent": "I-20261125-k01",
            "seed": args.seed,
            "mode": args.mode,
            "workers": args.workers,
            "elapsed_sec": round(elapsed, 2),
            "reserved_core_hours": round(core_hours, 4),
            "process_cpu_hours": round(cpu_hours, 4),
            "pfa_map_target": 0.01,
            "snr_inflect": args.snr_inflect,
            "snr_g0_slope": args.snr_g0_slope,
            "unified_score_calls": total_calls,
            "real_map_exact_cut_max_rel_err": max_exact_rel_err,
        },
        "gates": {
            "G1_exact_cut_bw_and_pilots": g1_report,
            "G0_all5_mean_ser_under_2pct": g0_ser_ok,
            "G2_no_truth_in_cal_val_and_blind_interfaces": True,
        },
        "s1_m11db_main": s1_11_sum,
        "s1_inflect_main": s1_inf_sum,
        "s1_m11db_desc": s1_desc_sum,
        "g0_m11db": g0_11_sum,
        "g0_slope": g0_slp_sum,
        "stress_readouts": {
            "blind_speed_1p8824": stress_bs,
            "random_target_locs": stress_rand,
            "slope_mismatch_2pct": stress_se,
            "swap_attribution_at_inflect": {
                "em0_mean_db": s1_inf_sum["burst_em0"]["pos_score_db_mean"],
                "em1_mean_db": s1_inf_sum["ridge_afdm_st"]["pos_score_db_mean"],
                "swap_R1S0_mean_db": swap_r1s0,
                "swap_R0S1_mean_db": swap_r0s1,
            },
        },
        "contrasts": {
            "C2_S1_m11_vs_ofdm_bonf": strip(c2_vs_ofdm),
            "C2_S1_m11_vs_k01_orig": strip(c2_vs_k01),
            "C3_inflect_st_vs_k01": strip(c3_inf_vs_k01),
            "C3_inflect_em1_vs_em0": strip(c3_em_vs_em0),
            "C3_inflect_em0_gain_share": em0_share,
            "C3_G0_slope_vs_ofdm": strip(c3_g0_slp),
            "C3_G0_nonsat": {"afdm_pd": g0_pd_af, "best_ofdm_pd": g0_pd_best_of, "pass": g0_nonsat},
            "C3_DiD_conservative": {"point": float(c2_vs_ofdm["point"] - max(0.0, c3_g0_slp["point"])), "ci95_dual_boot": did_cons_ci},
        },
        "verdicts": {
            "G1_HEALTH_BW_PILOT_G0SER": g1_health_pass,
            "C1_s1_per_arm": c1_s1_per_arm,
            "C1_g0_per_arm": c1_g0_per_arm,
            "C1_afdm_no_inflate_s1_le_1p75pct": c1_afdm_no_inflate_s1,
            "C1_afdm_no_inflate_g0_le_2p50pct": c1_afdm_no_inflate_g0,
            "C1_VALIDITY": c1_pass,
            "C2_BLIND_BREAKTHROUGH": c2_pass,
            "C3_ABLATION_PASS": c3_ablation_pass,
            "C3_G0_DID_PASS": c3_g0_did_pass,
            "C3_PASS": c3_pass,
            "PASS_PRIMARY": pass_primary,
        },
    }

    with open(out_abs, "x") as f:
        json.dump(summary, f, indent=2)

    print("\n=== S1 (-11 dB) FULL-MAP BLIND DETECTION & LOCALIZATION @ Pfa_map=1e-2 ===", flush=True)
    for a in ALL_PASS_ARMS:
        s = s1_11_sum[a]
        print(f"  {a:16s} | Thr={s['thr_db']:+5.2f}dB | ValPfa={s['val_pfa_map']*100:.2f}% (C1={s['c1_pass']}) | Pd_loc={s['pos_pd_loc']*100:5.1f}% | Mis={s['pos_pd_mis']*100:4.1f}% | SER={s['pos_ser_mean']:.4f}", flush=True)
    print(f"=== S1 INFLECTION ({args.snr_inflect:+.1f} dB) ABLATION (em0 share = {em0_share*100:.1f}%) ===", flush=True)
    for a in ["ridge_afdm_st", "burst_em0", "k01_orig", "ofdm_comb_st", "ofdm_blkpil_st"]:
        s = s1_inf_sum[a]
        print(f"  {a:16s} | Pd_loc={s['pos_pd_loc']*100:5.1f}% | Mean={s['pos_score_db_mean']:+5.2f}dB | SER={s['pos_ser_mean']:.4f}", flush=True)
    print(f"=== G0 STATIC SLOPE ({args.snr_g0_slope:+.1f} dB) & G0(-11) SER ===", flush=True)
    for a in PRIMARY_EQUAL_ARMS:
        s = g0_slp_sum[a]
        print(f"  {a:16s} | ValPfa={s['val_pfa_map']*100:.2f}% | Pd_loc={s['pos_pd_loc']*100:5.1f}% | Mean={s['pos_score_db_mean']:+5.2f}dB | G0(-11)SER={g0_11_sum[a]['pos_ser_mean']:.4f}", flush=True)
    print(f"VERDICTS: {summary['verdicts']}", flush=True)
    print(f"Elapsed: {elapsed:.1f}s ({core_hours:.4f} core-h) -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
