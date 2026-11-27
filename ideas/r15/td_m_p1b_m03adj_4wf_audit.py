#!/usr/bin/env python3
"""
Round 15 Phase 1B — P-m-03-Adj Complete Sol-Prescribed 4-Waveform Audit (`td_m_p1b_m03adj_4wf_audit.py`):
Directly executes gpt-6.2-sol Call 3's 10-line checklist for `P-m-03-Adj` (`[0,1,16]` & `[0,15,16]`,
N=512, L_cpp=16, 64-QAM, SNR=30 dB, sig_r=sig_t=1.5e-3, strict equal budget: 154 pilots + 358 data,
exact same total frame energy = N, paired across ALL 4 waveforms):
  1. `AFDM` (DAFT guard-band embedded pilot, frozen 25-m03 + Lag-IEKS)
  2. `SC_48_106_SoftMixed`: 48-UW + 106-PTRS with pilot-boost option + soft mixed-pilot/data Lag-IEKS
  3. `SC_5x31_Boosted`: Five equal-spaced UW blocks `31+31+31+31+30 = 154` (exact 154 budget, 5x15=75 zero-ISI
     obs every ~102 samples!) with pilot power boost (beta_p=1.5 deducted strictly from data energy!)
  4. `OFDM_Comb154_DualIEKS`: Equal 154/512 distributed comb pilots in OFDM + 18-state Lag-IEKS + 6-outer OAMP
  5. `OTFS_16x32_Guard154_DualIEKS`: Equal 154/512 embedded DD guard pilot in 16x32 OTFS + 18-state Lag-IEKS + 6-outer OAMP
  6. **Sol's Frozen-True-H Diagnostic (100% NON-CHEATING Blind-PN Oracle!)**:
     - `Diag_AFDM_TrueH_BlindPN`: Knows ONLY true `H`, ZERO phase truth -> exact 25-m03 / Lag-IEKS blind PN tracking!
     - `Diag_SC_TrueH_BlindPN`: Knows ONLY true `H`, ZERO phase truth -> SC 48+106 Lag-IEKS blind PN tracking!
  7. `Ref_Clean_ZeroPN` for ALL 4 waveforms (sanity gate!) + `Oracle_DualPhase` (known-phase reference) +
     paired `pSteel - 15 * pOracle` 95% CI!

Strictly READ-ONLY imports `ideas/r15/td_m_m03.py` & frozen `ideas/l2/l2_m_r12_m03_modtest.py`.
"""
import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np
from scipy.stats import t as student_t

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

import td_m_m03 as td3
m3 = td3.m3


def otfs_16x32_matrix():
    """Unitary 16 (delay) x 32 (Doppler) OTFS transform A_otfs such that s = A_otfs^H x_dd."""
    F32 = np.fft.fft(np.eye(32)) / math.sqrt(32.0)
    # Time-domain vectorized order: s = (F_N^H kron I_M) x_dd => A_otfs = F_N kron I_M
    return np.kron(F32, np.eye(16, dtype=complex))


def dft_matrix(N: int):
    return np.fft.fft(np.eye(N)) / math.sqrt(float(N))


def sc_blind_ce_and_ieks(y_sc, y_tr_sc, sp_tr_sc, x_sc, xp_sc, sp_sc, pil_mask, dmask, P_sc,
                         N, L_cpp, mode, sig_r, sig_t, pts64, data_scale=1.0,
                         H_true_override=None, ls_true=None, hs_true=None, nus_true=None):
    """Unified SC-FDE Steelman (handles both 48+106 and 5x31, optional pilot boost via data_scale,
    multi-init pilot Lag-IEKS using mixed pilot+data soft observations, and optional Frozen-True-H diagnostic)."""
    B = N + L_cpp; I_N = np.eye(N, dtype=complex); n_arr = np.arange(N)
    pts_s = pts64 * data_scale

    pil_ext = np.zeros(B, dtype=bool)
    pil_ext[:L_cpp] = pil_mask[N - L_cpp:]; pil_ext[L_cpp:] = pil_mask
    clean_uw = np.array([all(pil_ext[L_cpp + n - l] for l in range(L_cpp + 1)) for n in range(N)], dtype=bool)
    uw_idx = np.where(clean_uw)[0]

    if H_true_override is not None:
        l_sc = ls_true.copy(); h_sc = hs_true.copy(); nu_sc = nus_true.copy(); s2_sc = 1e-3
    elif mode == "single_frame":
        # Split uw_idx into coherent contiguous sub-blocks (<= 18 samples)
        sub_blocks = []
        cur = [int(uw_idx[0])]
        for iv in uw_idx[1:]:
            if int(iv) == cur[-1] + 1 and len(cur) < 18:
                cur.append(int(iv))
            else:
                if len(cur) >= 8: sub_blocks.append(np.array(cur, dtype=int))
                cur = [int(iv)]
        if len(cur) >= 8: sub_blocks.append(np.array(cur, dtype=int))
        Phi_b = [np.column_stack([sp_sc[L_cpp + blk - l] for l in range(L_cpp + 1)]) for blk in sub_blocks]
        res_b = [y_sc[blk].copy() for blk in sub_blocks]
        supp = []
        for _ in range(3):
            sc_l = np.zeros(L_cpp + 1)
            for bi, Pb in enumerate(Phi_b):
                sc_l += np.abs(Pb.conj().T @ res_b[bi]) ** 2 / np.maximum(np.sum(np.abs(Pb) ** 2, axis=0), 1e-12)
            for s_o in supp: sc_l[s_o] = -1.0
            supp = sorted(supp + [int(np.argmax(sc_l))])
            res_b = [y_sc[sub_blocks[bi]] - Phi_b[bi][:, supp] @ np.linalg.lstsq(Phi_b[bi][:, supp], y_sc[sub_blocks[bi]], rcond=None)[0]
                     for bi in range(len(sub_blocks))]
        l_sc = np.array(supp, dtype=int)
        h_sc, *_ = np.linalg.lstsq(Phi_b[0][:, l_sc], y_sc[sub_blocks[0]], rcond=None)
        nu_sc = np.zeros(len(l_sc), dtype=float)
        s2_sc = max(sum(float(np.sum(np.abs(rb) ** 2)) for rb in res_b) / max(len(uw_idx), 1), 1e-4)
    else:
        coh_pow = np.zeros(L_cpp + 1)
        for l in range(L_cpp + 1):
            prod = y_tr_sc * np.conj(sp_tr_sc[L_cpp + n_arr - l])
            for b0 in range(0, N, 32): coh_pow[l] += abs(np.sum(prod[b0:b0 + 32])) ** 2 / 32.0
        med_tr = float(np.median(np.sort(coh_pow)[:(L_cpp + 1) // 2]))
        cl_sc = [l for l in range(L_cpp + 1) if coh_pow[l] > max(3.5 * med_tr, 0.05 * float(coh_pow.max()))]
        if not cl_sc: cl_sc = [int(np.argmax(coh_pow))]
        l_sc = np.array(sorted(cl_sc), dtype=int)
        nu_sc = np.zeros(len(l_sc), dtype=float)
        h_sc = np.array([np.mean((y_tr_sc * np.conj(sp_tr_sc[L_cpp + n_arr - int(l)]))[N // 2 - 16 : N // 2 + 16]) for l in l_sc])
        pr_tr = np.zeros(N); pt_tr = np.zeros(B)
        for _ in range(4):
            Hl_tr = m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc)
            pr_tr, pt_tr = td3.ekf_rts_lag_timedomain(y_tr_sc, Hl_tr, sp_tr_sc, pr_tr, pt_tr, 1e-3, sig_r, sig_t, L_cpp, l_sc, 3)
            h_sc, nu_sc = m3.refine_channel_blind(y_tr_sc, sp_tr_sc, pr_tr, pt_tr, l_sc, nu_sc, L_cpp)
        s2_sc = max(float(np.mean(np.abs(y_tr_sc - np.exp(1j * pr_tr) * (m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc) @ (np.exp(1j * pt_tr) * sp_tr_sc))) ** 2)), 1e-5)

    # Multi-segment UW phase unwrap init + pilot-only mixed-variance 18-state Lag-IEKS
    Hl0 = m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc)
    u0 = Hl0 @ sp_sc
    segs = []; s0 = int(uw_idx[0]); prev = s0
    for iv in uw_idx[1:]:
        if int(iv) != prev + 1: segs.append(np.arange(s0, prev + 1)); s0 = int(iv)
        prev = int(iv)
    segs.append(np.arange(s0, prev + 1))
    sc_c = np.array([float(np.mean(sg)) for sg in segs])
    sc_p = np.unwrap(np.array([float(np.angle(np.vdot(u0[sg], y_sc[sg]))) for sg in segs]))
    pr_sc = np.interp(np.arange(N, dtype=float), sc_c, sc_p)
    pt_sc = np.zeros(B, dtype=float)

    pil_pow_scale = float(np.mean(np.abs(xp_sc[pil_mask]) ** 2))
    data_pow = data_scale ** 2
    r_var = np.empty(N, dtype=float)
    for ni in range(N):
        up = 0.0; kp = 0.0
        for pi, l in enumerate(l_sc):
            p2 = abs(h_sc[pi]) ** 2
            if pil_ext[L_cpp + ni - int(l)]: kp += p2 * pil_pow_scale
            else: up += p2 * data_pow
        r_var[ni] = 0.5 * (s2_sc + up) if kp > 0.05 else 1e6

    for _ in range(5):
        Hl0 = m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc)
        xi_nom = np.column_stack([pr_sc] + [pt_sc[L_cpp - l : L_cpp - l + N] for l in range(L_cpp + 1)])
        D_s = L_cpp + 2
        F_s = np.zeros((D_s, D_s)); F_s[0, 0] = 1.0; F_s[1, 1] = 1.0
        for l in range(1, L_cpp + 1): F_s[1 + l, l] = 1.0
        Q_s = np.zeros((D_s, D_s)); Q_s[0, 0] = sig_r; Q_s[1, 1] = sig_t
        xf = np.empty((N, D_s)); Pf = np.empty((N, D_s, D_s)); xpr = np.empty((N, D_s)); Ppr = np.empty((N, D_s, D_s))
        for ni in range(N):
            if ni == 0:
                xp_i = xi_nom[0].copy(); Pp_i = 10.0 * np.eye(D_s); Pp_i[1, 1] = 1e-3
            else:
                xp_i = F_s @ xf[ni - 1]; Pp_i = F_s @ Pf[ni - 1] @ F_s.T + Q_s
            xpr[ni] = xp_i; Ppr[ni] = Pp_i
            if r_var[ni] > 1e4:
                xf[ni] = xp_i; Pf[ni] = Pp_i; continue
            xl = xi_nom[ni]; hr = np.zeros(D_s); hi = np.zeros(D_s); yh = 0.0j
            for pi, l in enumerate(l_sc):
                if not pil_ext[L_cpp + ni - int(l)]: continue
                it = 1 + int(l)
                tm = Hl0[ni, L_cpp + ni - int(l)] * sp_sc[L_cpp + ni - int(l)] * np.exp(1j * (xl[0] + xl[it]))
                yh += tm; dt = 1j * tm; hr[0] += dt.real; hr[it] += dt.real; hi[0] += dt.imag; hi[it] += dt.imag
            Hn = np.vstack([hr, hi])
            inn = np.array([(y_sc[ni] - yh).real, (y_sc[ni] - yh).imag]) + Hn @ (xl - xp_i)
            HP = Hn @ Pp_i; S_i = r_var[ni] * np.eye(2) + HP @ Hn.T; K_i = np.linalg.solve(S_i, HP).T
            xf[ni] = xp_i + K_i @ inn; Pf[ni] = 0.5 * ((Pp_i - K_i @ HP) + (Pp_i - K_i @ HP).T)
        xsm = np.empty_like(xf); xsm[-1] = xf[-1]
        for ni in range(N - 2, -1, -1):
            Cn = np.linalg.solve(Ppr[ni + 1] + 1e-9 * np.eye(D_s), F_s @ Pf[ni]).T
            xsm[ni] = xf[ni] + Cn @ (xsm[ni + 1] - xpr[ni + 1])
        pr_sc = pr_sc + np.clip(xsm[:, 0] - pr_sc, -0.45, 0.45)
        pt_t = np.zeros(B); pt_t[L_cpp:] = xsm[:, 1]
        for l in range(1, L_cpp + 1): pt_t[L_cpp - l] = xsm[0, 1 + l]
        pt_sc = pt_sc + np.clip(pt_t - pt_sc, -0.45, 0.45)
        sg = pt_sc[L_cpp]; pt_sc -= sg; pr_sc += sg

    best_r = np.inf; best_xh = None
    hc, nuc = h_sc.copy(), nu_sc.copy(); s2c = s2_sc
    for out_i in range(6):
        Hl = m3.build_H_ext(N, L_cpp, hc, l_sc, nuc)
        Hc = np.exp(1j * pr_sc)[:, None] * ((Hl * np.exp(1j * pt_sc)[None, :]) @ P_sc)
        xs, xhc, vx, _ = m3.oamp_exact(y_sc, Hc, I_N, max(s2c, 1e-6) + 0.02 * (0.6 ** out_i), pts_s, dmask, xp_sc, 8)
        s_ext_h = P_sc @ xs
        pr_sc, pt_sc = td3.ekf_rts_lag_timedomain(y_sc, Hl, s_ext_h, pr_sc, pt_sc, max(s2c, 1e-6) + 0.5 * vx, sig_r, sig_t, L_cpp, l_sc, 2)
        if H_true_override is None and out_i >= 1:
            hc, nuc = m3.refine_channel_blind(y_sc, s_ext_h, pr_sc, pt_sc, l_sc, nuc, L_cpp)
        Hl2 = m3.build_H_ext(N, L_cpp, hc, l_sc, nuc)
        rc = float(np.sum(np.abs(y_sc - np.exp(1j * pr_sc) * (Hl2 @ (np.exp(1j * pt_sc) * (P_sc @ xhc)))) ** 2))
        s2c = float(np.clip(rc / N, 1e-5, 0.05))
        if rc < best_r: best_r = rc; best_xh = xhc
    return float(np.mean(np.abs(best_xh[dmask] - x_sc[dmask]) > 1e-3 * data_scale))


def transform_wf_blind_ieks(y_w, y_tr_w, sp_tr_w, x_w, xp_w, A_w, Ah_w, P_w, dmask,
                            N, L_cpp, mode, sig_r, sig_t, pts64,
                            ls_true=None, hs_true=None, nus_true=None, H_true_override=None):
    """Equal-budget 154/512 OFDM / OTFS blind CE + 18-state Lag-IEKS + 6-outer OAMP."""
    B = N + L_cpp; n_arr = np.arange(N)
    sp_w = P_w @ (Ah_w @ xp_w)
    if H_true_override is not None:
        l_w, h_w, nu_w, s2_w = ls_true.copy(), hs_true.copy(), nus_true.copy(), 1e-3
    elif mode == "prior_pn":
        coh_pow = np.zeros(L_cpp + 1)
        for l in range(L_cpp + 1):
            prod = y_tr_w * np.conj(sp_tr_w[L_cpp + n_arr - l])
            for b0 in range(0, N, 32): coh_pow[l] += abs(np.sum(prod[b0:b0 + 32])) ** 2 / 32.0
        med_tr = float(np.median(np.sort(coh_pow)[:(L_cpp + 1) // 2]))
        cl = [l for l in range(L_cpp + 1) if coh_pow[l] > max(3.5 * med_tr, 0.05 * float(coh_pow.max()))]
        if not cl: cl = [int(np.argmax(coh_pow))]
        l_w = np.array(sorted(cl), dtype=int)
        nu_w = np.zeros(len(l_w), dtype=float)
        h_w = np.array([np.mean((y_tr_w * np.conj(sp_tr_w[L_cpp + n_arr - int(l)]))[N // 2 - 16 : N // 2 + 16]) for l in l_w])
        pr_t = np.zeros(N); pt_t = np.zeros(B)
        for _ in range(4):
            Hl_t = m3.build_H_ext(N, L_cpp, h_w, l_w, nu_w)
            pr_t, pt_t = td3.ekf_rts_lag_timedomain(y_tr_w, Hl_t, sp_tr_w, pr_t, pt_t, 1e-3, sig_r, sig_t, L_cpp, l_w, 3)
            h_w, nu_w = m3.refine_channel_blind(y_tr_w, sp_tr_w, pr_t, pt_t, l_w, nu_w, L_cpp)
        s2_w = max(float(np.mean(np.abs(y_tr_w - np.exp(1j * pr_t) * (m3.build_H_ext(N, L_cpp, h_w, l_w, nu_w) @ (np.exp(1j * pt_t) * sp_tr_w))) ** 2)), 1e-5)
    else:
        # Single-frame blind CE from the 154 pilot bins in transform domain (OFDM comb / OTFS guard!)
        pil_m = ~dmask
        # Short-block non-coherent time-domain correlation using known pilot time waveform sp_w
        coh_pow = np.zeros(L_cpp + 1)
        for l in range(L_cpp + 1):
            prod = y_w * np.conj(sp_w[L_cpp + n_arr - l])
            for b0 in range(0, N, 32): coh_pow[l] += abs(np.sum(prod[b0:b0 + 32])) ** 2 / 32.0
        top3 = np.argsort(coh_pow)[-3:]
        l_w = np.array(sorted(top3), dtype=int)
        nu_w = np.zeros(len(l_w), dtype=float)
        # Fit h_w via transform-domain pilot bins
        Y_w = A_w @ y_w
        A_p = np.column_stack([(A_w @ (m3.build_H_ext(N, L_cpp, [1.0], [int(l)], [0.0]) @ sp_w))[pil_m] for l in l_w])
        h_w, *_ = np.linalg.lstsq(A_p, Y_w[pil_m], rcond=None)
        s2_w = 5e-3

    # Initial common-mode phase from matched pilot waveform + 18-state Lag-IEKS on pilot projection
    Hl0 = m3.build_H_ext(N, L_cpp, h_w, l_w, nu_w)
    z_m = y_w * np.conj(Hl0 @ sp_w)
    # Smooth z_m over window=11 to suppress data interference before unwrapping!
    kern = np.ones(11) / 11.0
    z_sm = np.convolve(z_m, kern, mode="same")
    pr_w = m3.zero_unwrap_complex(z_sm)
    pt_w = np.zeros(B, dtype=float)
    # Pilot-only Lag-IEKS pass (treating unknown data energy ~ 358/512 as observation variance)
    pr_w, pt_w = td3.ekf_rts_lag_timedomain(y_w, Hl0, sp_w, pr_w, pt_w, 0.75, sig_r, sig_t, L_cpp, l_w, 3)

    best_r = np.inf; best_xh = None
    hc, nuc = h_w.copy(), nu_w.copy(); s2c = s2_w
    for out_i in range(6):
        Hl = m3.build_H_ext(N, L_cpp, hc, l_w, nuc)
        Hc = np.exp(1j * pr_w)[:, None] * ((Hl * np.exp(1j * pt_w)[None, :]) @ P_w)
        xs, xhc, vx, _ = m3.oamp_exact(y_w, Hc, Ah_w, max(s2c, 1e-6) + 0.02 * (0.6 ** out_i), pts64, dmask, xp_w, 8)
        s_ext_h = P_w @ (Ah_w @ xs)
        pr_w, pt_w = td3.ekf_rts_lag_timedomain(y_w, Hl, s_ext_h, pr_w, pt_w, max(s2c, 1e-6) + 0.5 * vx, sig_r, sig_t, L_cpp, l_w, 2)
        if H_true_override is None and out_i >= 1:
            hc, nuc = m3.refine_channel_blind(y_w, s_ext_h, pr_w, pt_w, l_w, nuc, L_cpp)
        Hl2 = m3.build_H_ext(N, L_cpp, hc, l_w, nuc)
        rc = float(np.sum(np.abs(y_w - np.exp(1j * pr_w) * (Hl2 @ (np.exp(1j * pt_w) * (P_w @ (Ah_w @ xhc))))) ** 2))
        s2c = float(np.clip(rc / N, 1e-5, 0.05))
        if rc < best_r: best_r = rc; best_xh = xhc
    return float(np.mean(np.abs(best_xh[dmask] - x_w[dmask]) > 1e-3))


def run_paired_frame(args):
    seed, mode, mid_delay = args
    rng = np.random.default_rng(seed)
    N = 512; L_cpp = 16; B = N + L_cpp; n_guard = 154; Nd = N - n_guard
    snr_db = 30.0; sig_r = 1.5e-3; sig_t = 1.5e-3
    two_Nc1 = 3; c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2.0 * math.pi * N)
    A_af = m3.daft_matrix(N, c1, c2); Ah_af = A_af.conj().T; P_af = m3.build_cpp_ext(N, c1, L_cpp)
    P_cp = m3.build_cpp_ext(N, 0.0, L_cpp)
    A_ofdm = dft_matrix(N); Ah_ofdm = A_ofdm.conj().T
    A_otfs = otfs_16x32_matrix(); Ah_otfs = A_otfs.conj().T
    I_N = np.eye(N, dtype=complex)

    g8 = np.array([-7, -5, -3, -1, 1, 3, 5, 7]); pts64 = (g8[:, None] + 1j * g8[None, :]).ravel() / math.sqrt(42.0)
    qpsk = np.array([-1-1j, -1+1j, 1-1j, 1+1j]) / math.sqrt(2.0)

    # Paired physical channel, dual-end PN, AWGN, and 358 64-QAM symbols across ALL 4 waveforms!
    ls_t = np.array([0, mid_delay, 16], dtype=int)
    pdp = np.array([0.4225, 0.3025, 0.2750])
    nus_t = rng.uniform(-0.4, 0.4, 3)
    hs_t = np.sqrt(pdp) * np.exp(1j * rng.uniform(0, 2.0 * math.pi, 3))
    H_lin_t = m3.build_H_ext(N, L_cpp, hs_t, ls_t, nus_t)
    sig2_true = 10.0 ** (-snr_db / 10.0)

    phi_t = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)); phi_t -= phi_t[L_cpp]
    phi_r = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N))
    w = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    xd_vals = pts64[rng.integers(0, 64, Nd)]
    pil_vals = qpsk[rng.integers(0, 4, n_guard)]

    # Training preamble for R5 (same length N, same total energy N, same dual-end PN stats)
    y_tr_cp = None; sp_tr_cp = None
    if mode == "prior_pn":
        w_tr = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        x_tr = qpsk[rng.integers(0, 4, N)]
        sp_tr_cp = P_cp @ x_tr
        pt_tr = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)); pt_tr -= pt_tr[L_cpp]
        pr_tr = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N))
        y_tr_cp = np.exp(1j * pr_tr) * (H_lin_t @ (np.exp(1j * pt_tr) * sp_tr_cp)) + w_tr

    out = {"mid_delay": mid_delay}

    # --- 1. AFDM (same 154/512 guard pilot as td_m_m03.py) ---
    guard_af = np.zeros(N, dtype=bool); guard_af[180:334] = True; dmask_af = ~guard_af
    xp_af = np.zeros(N, dtype=complex); xp_af[N // 2] = math.sqrt(float(n_guard))
    x_af = xp_af.copy(); x_af[dmask_af] = xd_vals
    s_af = P_af @ (Ah_af @ x_af)
    y_af_clean = H_lin_t @ s_af + w
    y_af = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_af)) + w
    _, x_cl_af, _, _ = m3.oamp_exact(y_af_clean, H_lin_t @ P_af, Ah_af, sig2_true, pts64, dmask_af, xp_af, 8)
    out["Ref_Clean_AFDM"] = float(np.mean(np.abs(x_cl_af[dmask_af] - x_af[dmask_af]) > 1e-3))

    # AFDM Frozen-True-H Blind-PN Diagnostic (100% NON-CHEATING: knows ONLY H, ZERO phase truth!)
    pca = m3.build_pca_bases(N, L_cpp, K_pca=18)
    pilot_obs = np.zeros(N, dtype=bool); pilot_obs[196:268] = True
    sp_af = P_af @ (Ah_af @ xp_af); Y_af = A_af @ y_af
    H_p0 = [m3.build_H_ext(N, L_cpp, [hs_t[i]], [ls_t[i]], [nus_t[i]]) for i in range(3)]
    k_cs = [N // 2 - two_Nc1 * int(l) for l in ls_t]
    z_mrc = np.zeros(N, dtype=complex)
    for i in range(3):
        k_hi = min(k_cs[i] + 8, (k_cs[i] + k_cs[i - 1]) // 2) if i > 0 else k_cs[i] + 8
        k_lo = max(k_cs[i] - 8, (k_cs[i] + k_cs[i + 1]) // 2 + 1) if i < 2 else k_cs[i] - 8
        mm = np.zeros(N, dtype=bool); mm[k_lo : k_hi + 1] = True
        Ys = np.zeros(N, dtype=complex); Ys[mm] = Y_af[mm]
        z_mrc += (Ah_af @ Ys) * np.conj(H_p0[i] @ sp_af)
    pi_m = m3.zero_unwrap_complex(z_mrc[L_cpp : N - L_cpp])
    phi_mrc = np.empty(N); phi_mrc[L_cpp : N - L_cpp] = pi_m; phi_mrc[:L_cpp] = pi_m[0]; phi_mrc[N - L_cpp:] = pi_m[-1]
    pr_dh, pt_dh = m3.exact_proj_dual_gn_pca(Y_af[pilot_obs], A_af[pilot_obs, :], H_p0, ls_t, sp_af,
                                             phi_mrc, np.zeros(B), 1.0 / max(sig2_true, 1e-3), sig_r, sig_t, L_cpp, pca, 6)
    best_r_dh = np.inf; best_xh_dh = None; s2_dh = sig2_true
    for oi in range(6):
        Hc = np.exp(1j * pr_dh)[:, None] * ((H_lin_t * np.exp(1j * pt_dh)[None, :]) @ P_af)
        xs, xhc, vx, _ = m3.oamp_exact(y_af, Hc, Ah_af, max(s2_dh, 1e-6) + 0.02 * (0.6 ** oi), pts64, dmask_af, xp_af, 8)
        pr_dh, pt_dh = m3.gn_dual_banded(y_af, H_lin_t, P_af @ (Ah_af @ xs), pr_dh, pt_dh, max(s2_dh, 1e-6) + 0.5 * vx, sig_r, sig_t, L_cpp, 3)
        rc = float(np.sum(np.abs(y_af - np.exp(1j * pr_dh) * (H_lin_t @ (np.exp(1j * pt_dh) * (P_af @ (Ah_af @ xhc))))) ** 2))
        s2_dh = float(np.clip(rc / N, 1e-5, 0.05))
        if rc < best_r_dh: best_r_dh = rc; best_xh_dh = xhc
    out["Diag_AFDM_TrueH_BlindPN"] = float(np.mean(np.abs(best_xh_dh[dmask_af] - x_af[dmask_af]) > 1e-3))

    Ho_af = np.exp(1j * phi_r)[:, None] * ((H_lin_t * np.exp(1j * phi_t)[None, :]) @ P_af)
    _, xo_af, _, _ = m3.oamp_exact(y_af, Ho_af, Ah_af, sig2_true, pts64, dmask_af, xp_af, 10)
    out["Oracle_AFDM_DualPhase"] = float(np.mean(np.abs(xo_af[dmask_af] - x_af[dmask_af]) > 1e-3))

    # --- 2. SC-FDE: (a) 48+106 + Frozen-True-H diag; (b) 5x31 (31+31+31+31+30=154) with pilot power boost (beta_p=1.5) ---
    m_48 = np.zeros(N, dtype=bool); m_48[:48] = True
    m_48[np.round(np.linspace(50, N - 2, n_guard - 48)).astype(int)] = True
    while int(m_48.sum()) < n_guard: m_48[int(np.where(~m_48)[0][0])] = True
    dm_48 = ~m_48
    x_sc48 = np.zeros(N, dtype=complex); x_sc48[dm_48] = xd_vals; x_sc48[m_48] = pil_vals
    xp_sc48 = np.where(m_48, x_sc48, 0.0); sp_sc48 = P_cp @ xp_sc48; s_sc48 = P_cp @ x_sc48
    y_sc48_cl = H_lin_t @ s_sc48 + w
    y_sc48 = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_sc48)) + w
    _, x_cl_sc, _, _ = m3.oamp_exact(y_sc48_cl, H_lin_t @ P_cp, I_N, sig2_true, pts64, dm_48, xp_sc48, 8)
    out["Ref_Clean_SC"] = float(np.mean(np.abs(x_cl_sc[dm_48] - x_sc48[dm_48]) > 1e-3))
    out["SM_SC_48_106"] = sc_blind_ce_and_ieks(y_sc48, y_tr_cp, sp_tr_cp, x_sc48, xp_sc48, sp_sc48, m_48, dm_48, P_cp, N, L_cpp, mode, sig_r, sig_t, pts64)
    out["Diag_SC_TrueH_BlindPN"] = sc_blind_ce_and_ieks(y_sc48, y_tr_cp, sp_tr_cp, x_sc48, xp_sc48, sp_sc48, m_48, dm_48, P_cp, N, L_cpp, mode, sig_r, sig_t, pts64,
                                                        H_true_override=H_lin_t, ls_true=ls_t, hs_true=hs_t, nus_true=nus_t)
    Ho_sc = np.exp(1j * phi_r)[:, None] * ((H_lin_t * np.exp(1j * phi_t)[None, :]) @ P_cp)
    _, xo_sc, _, _ = m3.oamp_exact(y_sc48, Ho_sc, I_N, sig2_true, pts64, dm_48, xp_sc48, 10)
    out["Oracle_SC_DualPhase"] = float(np.mean(np.abs(xo_sc[dm_48] - x_sc48[dm_48]) > 1e-3))

    # 5x31 equal-spaced UW blocks (31+31+31+31+30 = 154) with pilot power boost beta_p=1.5 strictly deducted from data!
    m_5x = np.zeros(N, dtype=bool)
    for st, ln in [(0, 31), (102, 31), (204, 31), (306, 31), (408, 30)]:
        m_5x[st : st + ln] = True
    assert int(m_5x.sum()) == n_guard
    dm_5x = ~m_5x
    beta_p = 1.5; p_scale = math.sqrt(beta_p)
    d_pow = (float(N) - beta_p * float(n_guard)) / float(Nd)
    d_scale = math.sqrt(d_pow)
    x_sc5 = np.zeros(N, dtype=complex); x_sc5[dm_5x] = xd_vals * d_scale; x_sc5[m_5x] = pil_vals * p_scale
    xp_sc5 = np.where(m_5x, x_sc5, 0.0); sp_sc5 = P_cp @ xp_sc5; s_sc5 = P_cp @ x_sc5
    y_sc5 = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_sc5)) + w
    out["SM_SC_5x31_Boost1p5"] = sc_blind_ce_and_ieks(y_sc5, y_tr_cp, sp_tr_cp, x_sc5, xp_sc5, sp_sc5, m_5x, dm_5x, P_cp, N, L_cpp, mode, sig_r, sig_t, pts64, data_scale=d_scale)

    # --- 3. OFDM (equal 154/512 uniformly spaced comb pilots, exact same energy N) ---
    m_ofdm = np.zeros(N, dtype=bool)
    m_ofdm[np.round(np.linspace(0, N - 1, n_guard)).astype(int)] = True
    while int(m_ofdm.sum()) < n_guard: m_ofdm[int(np.where(~m_ofdm)[0][0])] = True
    dm_ofdm = ~m_ofdm
    x_of = np.zeros(N, dtype=complex); x_of[dm_ofdm] = xd_vals; x_of[m_ofdm] = pil_vals
    xp_of = np.where(m_ofdm, x_of, 0.0); s_of = P_cp @ (Ah_ofdm @ x_of)
    y_of_cl = H_lin_t @ s_of + w
    y_of = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_of)) + w
    _, x_cl_of, _, _ = m3.oamp_exact(y_of_cl, H_lin_t @ P_cp, Ah_ofdm, sig2_true, pts64, dm_ofdm, xp_of, 8)
    out["Ref_Clean_OFDM"] = float(np.mean(np.abs(x_cl_of[dm_ofdm] - x_of[dm_ofdm]) > 1e-3))
    out["SM_OFDM_Comb154"] = transform_wf_blind_ieks(y_of, y_tr_cp, sp_tr_cp, x_of, xp_of, A_ofdm, Ah_ofdm, P_cp, dm_ofdm, N, L_cpp, mode, sig_r, sig_t, pts64)
    _, xo_of, _, _ = m3.oamp_exact(y_of, Ho_sc, Ah_ofdm, sig2_true, pts64, dm_ofdm, xp_of, 10)
    out["Oracle_OFDM_DualPhase"] = float(np.mean(np.abs(xo_of[dm_ofdm] - x_of[dm_ofdm]) > 1e-3))

    # --- 4. OTFS 16x32 (equal 154/512 embedded DD pilot + guard band, exact same energy N) ---
    # Reserve 154 DD bins around pilot (m=8, n=16): 11 delay bins x 14 Doppler bins = 154 bins!
    m_otfs_2d = np.zeros((16, 32), dtype=bool)
    m_otfs_2d[3:14, 9:23] = True  # 11 x 14 = 154 exact!
    m_otfs = m_otfs_2d.T.ravel()  # matches kron(F32, I16) column-major (Doppler outer, delay inner)
    assert int(m_otfs.sum()) == n_guard
    dm_otfs = ~m_otfs
    xp_ot = np.zeros(N, dtype=complex); xp_ot[16 * 16 + 8] = math.sqrt(float(n_guard))
    x_ot = xp_ot.copy(); x_ot[dm_otfs] = xd_vals
    s_ot = P_cp @ (Ah_otfs @ x_ot)
    y_ot_cl = H_lin_t @ s_ot + w
    y_ot = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ot)) + w
    _, x_cl_ot, _, _ = m3.oamp_exact(y_ot_cl, H_lin_t @ P_cp, Ah_otfs, sig2_true, pts64, dm_otfs, xp_ot, 8)
    out["Ref_Clean_OTFS"] = float(np.mean(np.abs(x_cl_ot[dm_otfs] - x_ot[dm_otfs]) > 1e-3))
    out["SM_OTFS_Guard154"] = transform_wf_blind_ieks(y_ot, y_tr_cp, sp_tr_cp, x_ot, xp_ot, A_otfs, Ah_otfs, P_cp, dm_otfs, N, L_cpp, mode, sig_r, sig_t, pts64)
    _, xo_ot, _, _ = m3.oamp_exact(y_ot, Ho_sc, Ah_otfs, sig2_true, pts64, dm_otfs, xp_ot, 10)
    out["Oracle_OTFS_DualPhase"] = float(np.mean(np.abs(xo_ot[dm_otfs] - x_ot[dm_otfs]) > 1e-3))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_per_k", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_m03adj_4wf_audit.json")
    args = ap.parse_args()
    t0 = time.time()

    slices = [
        ("Adj_R4_30dB_SFBlind", "single_frame", [1, 15]),
        ("Adj_R5_30dB_PNTrain", "prior_pn",     [1, 15]),
    ]
    res_all = {"meta": {"n_per_k": args.n_per_k, "n_total": 2 * args.n_per_k, "paired_4wf": True}, "slices": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for si, (sname, mode, ks) in enumerate(slices):
            jobs = [(202611269000 + si * 10000 + ki * 1000 + f, mode, kv) for ki, kv in enumerate(ks) for f in range(args.n_per_k)]
            rows = list(ex.map(run_paired_frame, jobs))
            keys = [k for k in rows[0] if k != "mid_delay"]
            n = len(rows)
            tc = float(student_t.ppf(0.975, df=max(n - 1, 1)))
            agg = {}
            for k in keys:
                arr = np.array([r[k] for r in rows], dtype=float)
                agg[k] = {
                    "mean": float(np.mean(arr)),
                    "se": float(np.std(arr, ddof=1) / math.sqrt(n)),
                    "ci95_hw": float(tc * np.std(arr, ddof=1) / math.sqrt(n)),
                    "ll_gt5pct": float(np.mean(arr > 0.05)),
                }
            # Paired margin of best blind Steelman vs 15 * Diag_AFDM_TrueH_BlindPN AND vs 15 * Oracle_AFDM_DualPhase
            sm_keys = [k for k in keys if k.startswith("SM_")]
            best_sm_k = min(sm_keys, key=lambda k: agg[k]["mean"])
            p_sm = np.array([r[best_sm_k] for r in rows])
            p_or_h = np.array([r["Diag_AFDM_TrueH_BlindPN"] for r in rows])
            p_or_ph = np.array([r["Oracle_AFDM_DualPhase"] for r in rows])
            d_h = p_sm - 15.0 * p_or_h; d_ph = p_sm - 15.0 * p_or_ph
            agg["_best_sm_key"] = best_sm_k
            agg["_paired_margin_vs_15x_TrueH_BlindPN"] = {"mean": float(np.mean(d_h)), "ci95_lo": float(np.mean(d_h) - tc * np.std(d_h, ddof=1) / math.sqrt(n))}
            agg["_paired_margin_vs_15x_DualPhaseOracle"] = {"mean": float(np.mean(d_ph)), "ci95_lo": float(np.mean(d_ph) - tc * np.std(d_ph, ddof=1) / math.sqrt(n))}
            res_all["slices"][sname] = agg
            print(f"\n=== Paired 4-WF {sname} (n={n}) ===")
            for k in keys:
                v = agg[k]
                print(f"  {k:24s}: SER = {v['mean']:.5f} +/- {v['se']:.5f} (LL>5%: {v['ll_gt5pct']*100:.1f}%)")
            print(f"  --> BestSM={best_sm_k} ({agg[best_sm_k]['mean']:.5f}) | vs 15x TrueH_BlindPN margin={agg['_paired_margin_vs_15x_TrueH_BlindPN']['mean']:+.5f} (lo={agg['_paired_margin_vs_15x_TrueH_BlindPN']['ci95_lo']:+.5f})")
    res_all["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(res_all, f, indent=2)
    print(f"\nSaved -> {args.out} in {res_all['elapsed_sec']}s")


if __name__ == "__main__":
    main()
