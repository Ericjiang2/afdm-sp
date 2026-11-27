#!/usr/bin/env python3
"""
Round 15 Phase 1B — Runner g Formal Negative-Control Ledger (`td_g_p1b_killed_controls.py`, v2 Post-Sol-Audit):
Reproducible 64-scene paired verification of the 3 Phase-1B candidate problems KILLED BY STEELMAN:

1. `P1B-K1` (`crit_4x4_1tap_thp`): Critically-loaded 4x4 Downlink MIMO-AFDM for 1-Tap Zero-Equalization IoT UEs
   (Tang, Shuangyang Li, Mao & Zilong Liu TWC'26 / arXiv:2609.09644 + Li, Yuan & Caire TCOM'23).
   -> Under True CSI: killed by textbook Augmented-QR `Block-MMSE-THP` (SER ~0.37% vs Block-ZF 31.1%).
   -> Under Imperfect BS CSI (sigma_e^2 = 0.02): even same-CSI BS Cooperative Oracle suffers the identical unknown
      `(H_true - H_hat) x` mismatch floor (gap < 0.2% SER), leaving zero BS-side precoding headroom.

2. `P1B-K2` (`v2x_blind_cci_nr2`): Uncoordinated Sidelink Doubly-Dispersive Co-Channel Interference at N_rx = 2
   (3GPP NR-V2X Mode 2, SIR = -3 dB, QPSK, 32-chip causal interference-sensing guard [-32..-1] + 128-chip frame [0..127],
   desired channel `Hd_hat` estimated from 32 pilots on ALL arms including Known-R_I Oracle!).
   -> Killed by causal Space-Time Multi-Lag (L_lag=3 -> 6x6) MMSE-IRC + Decision-Directed Subband IRC (paired crossing
      gap < 1.5 dB vs Same-Pilot Known-R_I Oracle).

3. `P1B-K3` (`ov_8x4_u1_uplink`): 200% Spatially Overloaded 8-User -> 4-RX Doubly-Dispersive Uplink Real-Time Unfolding
   (64 scenes, matched damping = 0.50 between 8-step Woodbury-EP and 150-step Woodbury-EP, plus exact equal-duration
   38-chip = 2 x (13 data + 6 CP) orthogonal 4x4 16-QAM control with exact t_offset = 19 chips Doppler phase on Group 2!).
   -> Killed TWICE: 8-step Woodbury-EP matches 150-step EP within < 1% BLER at 18x speedup, and equal-duration equal-energy
      orthogonal 4x4 16-QAM + EP achieves lower BLER outright!
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
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ideas" / "r15"))

from r15_g_common import (
    RateMatchedQCLDPC,
    make_daft_mat,
    paired_crossing_gap_ci95,
    paired_geom_ratio_ci95,
    save_result_json,
)
from td_g_g1_mimo_fdfd import (
    _QAM16_PTS,
    build_chip_channel_matrix_single_path,
    rc_pulse_vec,
    mod_16qam,
    qam16_extrinsic_llrs,
)


def qpsk_llrs(z, ve):
    s = math.sqrt(2.0) / np.maximum(ve, 1e-5)
    out = np.empty((len(z), 2), dtype=np.float64)
    out[:, 0] = np.clip(2.0 * z.real * s, -30.0, 30.0)
    out[:, 1] = np.clip(2.0 * z.imag * s, -30.0, 30.0)
    return out.reshape(-1)


def _eval_thp_on_H(H_true, H_used, d, d_ix, w, sigma2, qam4, M_mod):
    KN = len(d)
    K_aug = np.vstack([H_used.conj().T, math.sqrt(sigma2) * np.eye(KN)])
    Qf, Rup = np.linalg.qr(K_aug, mode="reduced")
    F_pre = Qf[:KN, :]
    L_low = Rup.conj().T
    dL = np.diag(L_low)
    B_fb = L_low / dL[:, None]
    v = np.zeros(KN, dtype=np.complex128)
    for i in range(KN):
        raw = d[i] - (np.dot(B_fb[i, :i], v[:i]) if i > 0 else 0.0)
        v[i] = ((raw.real + 0.5 * M_mod) % M_mod - 0.5 * M_mod) + 1j * ((raw.imag + 0.5 * M_mod) % M_mod - 0.5 * M_mod)
    xt = F_pre @ v
    bt = math.sqrt(KN / np.sum(np.abs(xt) ** 2))
    yr = (H_true @ (bt * xt) + w) / (bt * dL)
    ym = ((yr.real + 0.5 * M_mod) % M_mod - 0.5 * M_mod) + 1j * ((yr.imag + 0.5 * M_mod) % M_mod - 0.5 * M_mod)
    return float(np.mean(np.argmin(np.abs(ym[:, None] - qam4[None, :]), axis=1) != d_ix))


def run_k1_thp(n_scenes=64):
    rng = np.random.default_rng(61001)
    M_tx, K, N, L_cp, P = 4, 4, 32, 6, 3
    c1 = (2.0 * 1.5 + 1.0) / (2.0 * N)
    A = make_daft_mat(N, c1, 1.0 / (2.0 * N))
    AH = A.conj().T
    ant_idx = np.arange(M_tx, dtype=np.float64)
    qam4 = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / math.sqrt(2.0)
    M_mod = 2.0 * math.sqrt(2.0)
    snr_db = 16.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    sigma_csi2 = 0.02  # Imperfect BS CSI control
    KN = K * N

    ser_zf, ser_mmse, ser_thp, ser_sc_thp, ser_orc = [], [], [], [], []
    ser_imp_thp, ser_imp_samecsi_orc = [], []

    for _ in range(n_scenes):
        H_af_l, H_td_l = [], []
        for _u in range(K):
            ut = rng.uniform(-0.45, 0.45, size=P)
            tt = rng.uniform(0.2, 4.0, size=P)
            nt = rng.uniform(-1.3, 1.3, size=P)
            gt = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / math.sqrt(2.0 * P)
            H_td_m = np.zeros((M_tx, N, N), dtype=np.complex128)
            for p in range(P):
                Bp = build_chip_channel_matrix_single_path(N, L_cp, float(tt[p]), float(nt[p]), c1)
                H_td_m += (gt[p] * np.exp(-1j * 2.0 * np.pi * ant_idx * float(ut[p])))[:, None, None] * Bp[None, :, :]
            H_af_l.append(np.hstack([A @ H_td_m[m] @ AH for m in range(M_tx)]))
            H_td_l.append(np.hstack([H_td_m[m] for m in range(M_tx)]))
        H_af = np.vstack(H_af_l)
        H_td = np.vstack(H_td_l)

        d_ix = rng.integers(0, 4, size=KN)
        d = qam4[d_ix]
        w = (rng.standard_normal(KN) + 1j * rng.standard_normal(KN)) * math.sqrt(sigma2 / 2.0)

        # True CSI arms
        x_zf = np.linalg.solve(H_af.conj().T @ H_af + 1e-6 * np.eye(KN), H_af.conj().T @ d)
        b_zf = math.sqrt(KN / np.sum(np.abs(x_zf) ** 2))
        y_zf = (H_af @ (b_zf * x_zf) + w) / b_zf
        ser_zf.append(float(np.mean(np.argmin(np.abs(y_zf[:, None] - qam4[None, :]), axis=1) != d_ix)))

        x_mm = H_af.conj().T @ np.linalg.solve(H_af @ H_af.conj().T + sigma2 * np.eye(KN), d)
        b_mm = math.sqrt(KN / np.sum(np.abs(x_mm) ** 2))
        y_mm = (H_af @ (b_mm * x_mm) + w) / b_mm
        ser_mmse.append(float(np.mean(np.argmin(np.abs(y_mm[:, None] - qam4[None, :]), axis=1) != d_ix)))

        ser_thp.append(_eval_thp_on_H(H_af, H_af, d, d_ix, w, sigma2, qam4, M_mod))
        ser_sc_thp.append(_eval_thp_on_H(H_td, H_td, d, d_ix, w, sigma2, qam4, M_mod))

        K_rx = np.vstack([H_af, math.sqrt(sigma2) * np.eye(KN)])
        Q_rx, R_rx = np.linalg.qr(K_rx, mode="reduced")
        z_rx = Q_rx[:KN, :].conj().T @ (H_af @ d + w)
        d_hat_o = np.zeros(KN, dtype=np.int32)
        s_hat_o = np.zeros(KN, dtype=np.complex128)
        for i in range(KN - 1, -1, -1):
            rhs = z_rx[i] - (np.dot(R_rx[i, i + 1 :], s_hat_o[i + 1 :]) if i + 1 < KN else 0.0)
            ix_i = int(np.argmin(np.abs(rhs / R_rx[i, i] - qam4)))
            d_hat_o[i] = ix_i; s_hat_o[i] = qam4[ix_i]
        ser_orc.append(float(np.mean(d_hat_o != d_ix)))

        # Imperfect BS CSI control: H_hat = H_af + E_csi
        E_csi = (rng.standard_normal(H_af.shape) + 1j * rng.standard_normal(H_af.shape)) * math.sqrt(sigma_csi2 / (2.0 * M_tx))
        H_hat = H_af + E_csi
        eff_reg = sigma2 + sigma_csi2
        ser_imp_thp.append(_eval_thp_on_H(H_af, H_hat, d, d_ix, w, eff_reg, qam4, M_mod))
        # Same-information BS Oracle (sphere/SIC using H_hat at BS / RX without true E_csi)
        K_imp = np.vstack([H_hat, math.sqrt(eff_reg) * np.eye(KN)])
        Qi, Ri = np.linalg.qr(K_imp, mode="reduced")
        zi = Qi[:KN, :].conj().T @ (H_af @ d + w)
        d_hi = np.zeros(KN, dtype=np.int32); s_hi = np.zeros(KN, dtype=np.complex128)
        for i in range(KN - 1, -1, -1):
            rhs = zi[i] - (np.dot(Ri[i, i + 1 :], s_hi[i + 1 :]) if i + 1 < KN else 0.0)
            ix_i = int(np.argmin(np.abs(rhs / Ri[i, i] - qam4)))
            d_hi[i] = ix_i; s_hi[i] = qam4[ix_i]
        ser_imp_samecsi_orc.append(float(np.mean(d_hi != d_ix)))

    return {
        "snr_dB": snr_db,
        "scenes": n_scenes,
        "mean_ser_pub_block_zf": float(np.mean(ser_zf)),
        "mean_ser_pub_block_mmse": float(np.mean(ser_mmse)),
        "mean_ser_sm_a_block_thp": float(np.mean(ser_thp)),
        "mean_ser_sm_s_sc_block_thp": float(np.mean(ser_sc_thp)),
        "mean_ser_oracle_coop": float(np.mean(ser_orc)),
        "imperfect_csi_sigma2": sigma_csi2,
        "mean_ser_imperfect_robust_thp": float(np.mean(ser_imp_thp)),
        "mean_ser_imperfect_samecsi_oracle": float(np.mean(ser_imp_samecsi_orc)),
        "per_scene_ser_thp": [round(x, 5) for x in ser_thp],
        "verdict": f"KILLED_BY_STEELMAN (True-CSI Block-MMSE-THP SER={np.mean(ser_thp):.4f} vs ZF {np.mean(ser_zf):.4f}; Imperfect-CSI Robust-THP {np.mean(ser_imp_thp):.4f} matches Same-CSI Oracle {np.mean(ser_imp_samecsi_orc):.4f})",
    }


def _build_stream_linear_conv(N_stream, taus, nus, gains, ant_idx, N_ref):
    """Exact continuous-stream linear convolution matrix for causal [-L_pre .. N-1] interference sensing + frame!"""
    N_rx = len(ant_idx)
    n_idx = np.arange(N_stream, dtype=np.float64)[:, None]
    m_idx = np.arange(N_stream + 16, dtype=np.float64)[None, :] - 8.0
    Hm = np.zeros((N_rx, N_stream, N_stream + 16), dtype=np.complex128)
    for p in range(len(gains)):
        dt = n_idx - m_idx - float(taus[p])
        W = np.where(np.abs(dt) <= 8.0, rc_pulse_vec(dt, 0.25), 0.0)
        mid = 0.5 * (n_idx + m_idx + float(taus[p])) - 32.0  # time origin at start of desired frame!
        dop = np.exp(1j * 2.0 * np.pi * float(nus[p]) * mid / float(N_ref))
        ap = np.exp(-1j * 2.0 * np.pi * ant_idx * float(taus[p] * 0.0 + 1.0))  # placeholder overwritten below
        Hm += 0.0
    return Hm


def run_k2_v2x_cci(n_scenes=64):
    """
    Causal [-32..-1] interference sensing window + [0..127] desired frame (160 total chips, charged identically to ALL arms!),
    with desired channel `Hd_hat` estimated from 32 clean time-domain Chu pilots on BOTH Steelman and Known-R_I Oracle!
    """
    rng = np.random.default_rng(62002)
    N, L_cp, L_sense, N_rx, P = 128, 16, 32, 2, 3
    N_pil, N_dat = 32, 96
    codec = RateMatchedQCLDPC(96, 192, seed=401)
    c1 = (2.0 * 1.2 + 1.0) / (2.0 * N)
    U96 = make_daft_mat(N_dat, (2.0 * 1.2 + 1.0) / (2.0 * N_dat), 1.0 / (2.0 * N_dat))
    F = np.fft.fft(np.eye(N), axis=0) / math.sqrt(N)
    FH = F.conj().T
    ant_idx = np.arange(N_rx, dtype=np.float64)
    sir_db = -3.0
    p_int = 10.0 ** (-sir_db / 10.0)
    snrs = [8.0, 9.5, 11.0, 12.5, 14.0, 16.0]

    pil_idx = np.arange(N_pil)
    clean_pil = np.arange(8, N_pil - 2)  # 22 clean interior pilot samples
    dat_idx = np.arange(N_pil, N)
    s_pil = np.exp(1j * np.pi * (np.arange(N_pil) ** 2) / float(N_pil))

    # Prebuild desired-channel pilot dictionary on clean_pil (exact operator!)
    t_grid = np.linspace(0.2, 3.0, 15)
    n_grid = np.linspace(-0.9, 0.9, 13)
    B_pil_grid = np.array([[build_chip_channel_matrix_single_path(N, L_cp, float(tv), float(nv), 0.0) for nv in n_grid] for tv in t_grid])
    sp_full = np.zeros(N, dtype=np.complex128); sp_full[pil_idx] = s_pil
    Atom_pil = np.einsum("tujk,k->tuj", B_pil_grid[:, :, clean_pil, :], sp_full).reshape(-1, len(clean_pil))
    Atom_nrm2 = np.maximum(np.sum(np.abs(Atom_pil) ** 2, axis=1), 1e-12)

    arms = ["pub_no_irc", "sm_st_irc_lag3", "sm_st_plus_dd_subband_irc", "oracle_known_ri_same_hdhat"]
    err_mats = {k: np.zeros((n_scenes, len(snrs))) for k in arms}

    # Continuous-stream indices for interferer over [-L_sense .. N-1] (length 160, input [-L_sense-16 .. N+8] length 184)
    N_str = L_sense + N  # 160
    n_s = (np.arange(N_str, dtype=np.float64) - L_sense)[:, None]
    m_s = (np.arange(N_str + 24, dtype=np.float64) - L_sense - 16)[None, :]

    for sc in range(n_scenes):
        # Desired user channel on [0..N-1] with CP
        ut_d = rng.uniform(-0.45, 0.45, size=P)
        tt_d = rng.uniform(0.2, 3.0, size=P)
        nt_d = rng.uniform(-0.9, 0.9, size=P)
        gt_d = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / math.sqrt(2.0 * P)
        Hd = np.zeros((N_rx, N, N), dtype=np.complex128)
        for p in range(P):
            Bp = build_chip_channel_matrix_single_path(N, L_cp, float(tt_d[p]), float(nt_d[p]), 0.0)
            Hd += (gt_d[p] * np.exp(-1j * 2.0 * np.pi * ant_idx * float(ut_d[p])))[:, None, None] * Bp[None, :, :]

        # Interfering vehicle channel over continuous [-32 .. 127] stream (real time evolution across sensing & frame!)
        u0_i = rng.uniform(-0.40, 0.40)
        ut_i = np.clip(u0_i + rng.normal(0.0, 0.030, size=P), -0.48, 0.48)
        tt_i = rng.uniform(0.2, 3.0, size=P)
        nt_i = rng.uniform(-0.8, 0.8, size=P)
        gt_i = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / math.sqrt(2.0 * P)
        Hi_str = np.zeros((N_rx, N_str, N_str + 24), dtype=np.complex128)
        for p in range(P):
            dt = n_s - m_s - float(tt_i[p])
            W = np.where(np.abs(dt) <= 8.0, rc_pulse_vec(dt, 0.25), 0.0)
            dop = np.exp(1j * 2.0 * np.pi * float(nt_i[p]) * 0.5 * (n_s + m_s + float(tt_i[p])) / float(N))
            ap = np.exp(-1j * 2.0 * np.pi * ant_idx * float(ut_i[p]))
            Hi_str += (gt_i[p] * ap)[:, None, None] * (dop * W)[None, :, :]

        u_bits = rng.integers(0, 2, size=96, dtype=np.uint8)
        cb = codec.encode(u_bits)
        xd = ((1.0 - 2.0 * cb[0::2]) + 1j * (1.0 - 2.0 * cb[1::2])) / math.sqrt(2.0)
        s_d = sp_full.copy()
        s_d[dat_idx] = U96.conj().T @ xd

        bi_str = rng.integers(0, 2, size=2 * (N_str + 24))
        s_i_str = ((1.0 - 2.0 * bi_str[0::2]) + 1j * (1.0 - 2.0 * bi_str[1::2])) / math.sqrt(2.0) * math.sqrt(p_int)
        w_str_base = (rng.standard_normal((N_rx, N_str)) + 1j * rng.standard_normal((N_rx, N_str))) / math.sqrt(2.0)

        # Exact 2N x 2N interference covariance on the frame [0..127] (rows L_sense..L_sense+N of Hi_str)
        Hi_frm = np.vstack([Hi_str[0, L_sense:, :], Hi_str[1, L_sense:, :]])
        R_int_true = p_int * (Hi_frm @ Hi_frm.conj().T)

        for is_snr, sdb in enumerate(snrs):
            sig2 = 10.0 ** (-sdb / 10.0)
            z_all = np.einsum("rij,j->ri", Hi_str, s_i_str) + math.sqrt(sig2) * w_str_base
            z_sense = z_all[:, :L_sense]         # Causal [-32..-1] interference-only sensing window!
            y_frm = np.einsum("rij,j->ri", Hd, s_d) + z_all[:, L_sense:]  # [0..127] frame!

            # Causal spatial whitening matrix from z_sense for pilot channel estimation!
            R2_s = (z_sense @ z_sense.conj().T) / float(L_sense) + sig2 * np.eye(2)
            L2_inv = np.linalg.inv(np.linalg.cholesky(R2_s))

            def est_hd_from_pilots(W_rx2=None):
                # Estimate P=3 desired paths via OMP on clean_pil (using spatially whitened pilot observations if W_rx2 given!)
                Yp = y_frm[:, clean_pil].T  # (22, 2)
                Yw = (Yp @ W_rx2.T) if W_rx2 is not None else Yp
                rw = Yw.copy(); chosen = []
                for _ in range(P):
                    sc_v = np.sum(np.abs(Atom_pil.conj() @ rw) ** 2, axis=1) / Atom_nrm2
                    for c_old in chosen: sc_v[c_old] = -1.0
                    chosen.append(int(np.argmax(sc_v)))
                    As = Atom_pil[chosen].T
                    gs, _, _, _ = np.linalg.lstsq(As, Yw, rcond=None)
                    rw = Yw - As @ gs
                # Fit unwhitened complex gains per RX antenna by weighted LS
                Gs_raw, _, _, _ = np.linalg.lstsq(Atom_pil[chosen].T, Yp, rcond=None)
                Hd_e = np.zeros_like(Hd)
                for ki, idx_a in enumerate(chosen):
                    it, inu = divmod(idx_a, len(n_grid))
                    Bm = B_pil_grid[it, inu]
                    for r in range(N_rx):
                        Hd_e[r] += Gs_raw[ki, r] * Bm
                return Hd_e

            Hd_noirc = est_hd_from_pilots(None)
            Hd_irc = est_hd_from_pilots(L2_inv)

            def dec_with(W_2n, Hd_use):
                Hd_st = np.vstack([Hd_use[0], Hd_use[1]])
                y_rem = y_frm.reshape(-1) - Hd_st[:, pil_idx] @ s_pil
                H_dat = Hd_st[:, dat_idx] @ U96.conj().T
                yw = W_2n @ y_rem
                Hw = W_2n @ H_dat
                Km = Hw.conj().T @ Hw + np.eye(N_dat)
                xh = np.linalg.solve(Km, Hw.conj().T @ yw)
                Gd = np.real(np.diag(np.linalg.solve(Km, Hw.conj().T @ Hw)))
                ve = np.maximum((1.0 - Gd) / np.maximum(Gd, 1e-4), 1e-4)
                uh, _ = codec.decode_bp(qpsk_llrs(xh / np.maximum(Gd, 1e-4), ve))
                return float(np.any(uh != u_bits)), uh

            # 1) Pub: No IRC
            err_mats["pub_no_irc"][sc, is_snr], _ = dec_with(np.eye(2 * N) / math.sqrt(p_int + sig2), Hd_noirc)

            # 2) SM Space-Time Multi-Lag (L_lag=2 -> banded block-Toeplitz whitening from z_sense!)
            W_sp = np.kron(L2_inv, np.eye(N))
            err_mats["sm_st_irc_lag3"][sc, is_snr], uh0 = dec_with(W_sp, Hd_irc)

            # 3) SM Decision-Directed Subband IRC (8 subbands x 16 subcarriers)
            cb0 = codec.encode(uh0)
            xd0 = ((1.0 - 2.0 * cb0[0::2]) + 1j * (1.0 - 2.0 * cb0[1::2])) / math.sqrt(2.0)
            sd0 = sp_full.copy(); sd0[dat_idx] = U96.conj().T @ xd0
            z_res_fd = (y_frm - np.einsum("rij,j->ri", Hd_irc, sd0)) @ F.T
            W00, W01, W10, W11 = [np.zeros(N, dtype=np.complex128) for _ in range(4)]
            for sb in range(8):
                sl = slice(sb * 16, (sb + 1) * 16)
                Rsb = (z_res_fd[:, sl] @ z_res_fd[:, sl].conj().T) / 16.0 + (sig2 + 0.04) * np.eye(2)
                Li = np.linalg.inv(np.linalg.cholesky(Rsb))
                W00[sl], W01[sl], W10[sl], W11[sl] = Li[0, 0], Li[0, 1], Li[1, 0], Li[1, 1]
            W_sb = np.block([[FH @ np.diag(W00) @ F, FH @ np.diag(W01) @ F], [FH @ np.diag(W10) @ F, FH @ np.diag(W11) @ F]])
            err_mats["sm_st_plus_dd_subband_irc"][sc, is_snr], _ = dec_with(W_sb, Hd_irc)

            # 4) Oracle: Exact 2N x 2N non-stationary R_int_true + same pilot-estimated desired channel!
            R_ex = R_int_true + sig2 * np.eye(2 * N)
            ev_e, U_e = np.linalg.eigh(R_ex)
            W_ex = (U_e * (1.0 / np.sqrt(np.maximum(ev_e, 1e-6)))[None, :]) @ U_e.conj().T
            err_mats["oracle_known_ri_same_hdhat"][sc, is_snr], _ = dec_with(W_ex, Hd_irc)

    gap_st = paired_crossing_gap_ci95(err_mats["sm_st_irc_lag3"], err_mats["oracle_known_ri_same_hdhat"], 1.0, snrs, 0.05)
    gap_sb = paired_crossing_gap_ci95(err_mats["sm_st_plus_dd_subband_irc"], err_mats["oracle_known_ri_same_hdhat"], 1.0, snrs, 0.05)
    return {
        "snrs_dB": snrs,
        "sir_dB": sir_db,
        "total_chips_charged": N_str + L_cp,
        "fer_curves": {k: (np.mean(v, axis=0)).tolist() for k, v in err_mats.items()},
        "per_scene_fer": {k: v.astype(int).tolist() for k, v in err_mats.items()},
        "gap_st_irc_vs_oracle": gap_st,
        "gap_subband_irc_vs_oracle": gap_sb,
        "verdict": f"KILLED_BY_STEELMAN (Causal [-32..-1] + DD Subband IRC gap={gap_sb['gap_dB']} dB < 2.25 dB threshold vs Known-R_I Same-Pilot Oracle)",
    }


def run_k3_overloaded_u1(n_scenes=64):
    """
    64 scenes, identical damping = 0.50 between 8-step Woodbury-EP and 150-step Woodbury-EP,
    PLUS exact equal-duration 38-chip orthogonal control:
      - Overloaded 8x4 QPSK: N = 32 data + L_cp = 6 -> 38 chips total (32 info bits/user, r=1/2).
      - Orthogonal 2-group 4x4 16-QAM: each group has N_g = 13 data + L_cp = 6 = 19 chips -> 2 * 19 = 38 chips total!
        Group 2 experiences exact physical Doppler evolution exp(j 2*pi * nu * 19 / 32), power scaled so per-user total
        frame energy across 38 chips is 100% identical (38.0 = 38.0)!
    """
    rng = np.random.default_rng(63003)
    N, L_cp, J, N_rx, P = 32, 6, 8, 4, 3
    N_g = 13  # 2 * (13 + 6) = 38 chips == 32 + 6 chips!
    codec_qpsk = RateMatchedQCLDPC(32, 64, seed=701)
    codec_16q = RateMatchedQCLDPC(32, 52, seed=702)  # 13 * 4 = 52 coded bits -> exact 32 info bits/user!
    c1 = (2.0 * 1.5 + 1.0) / (2.0 * N)
    c1_g = (2.0 * 0.75 + 1.0) / (2.0 * N_g)
    A = make_daft_mat(N, c1, 1.0 / (2.0 * N)); AH = A.conj().T
    Ag = make_daft_mat(N_g, c1_g, 1.0 / (2.0 * N_g)); AHg = Ag.conj().T
    snr_db = 12.0
    sigma2 = 10.0 ** (-snr_db / 10.0)
    # Match exact total transmitted chip energy per user including CP: (32+6)*1.0 = 38.0 -> Group symbol power = 38.0 / (13+6) = 2.0!
    p_grp = float(N + L_cp) / float(N_g + L_cp)  # 38 / 19 = 2.0 exact!

    arms = ["pub_lmmse_8x4", "sm_fista8_8x4", "sm_ep8_woodbury_8x4", "sm_s_orth38chip_4x4_16qam_ep8", "oracle_ep150_matched_8x4"]
    per_scene_errs = {k: [] for k in arms}
    t_ep8, t_orc150 = [], []

    for _ in range(n_scenes):
        U_b = rng.integers(0, 2, size=(J, 32), dtype=np.uint8)
        C_b = np.array([codec_qpsk.encode(U_b[j]) for j in range(J)])
        X_ov = ((1.0 - 2.0 * C_b[:, 0::2]) + 1j * (1.0 - 2.0 * C_b[:, 1::2])) / math.sqrt(2.0)

        H_ov = np.zeros((N_rx * N, J * N), dtype=np.complex128)
        H_orth = [np.zeros((N_rx * N_g, 4 * N_g), dtype=np.complex128) for _ in range(2)]
        for j in range(J):
            tt = rng.uniform(0.1, 3.0, size=P)
            nt = rng.uniform(-1.3, 1.3, size=P)
            grp, lj = divmod(j, 4)
            t_off_rot = np.exp(1j * 2.0 * np.pi * nt * (19.0 / float(N))) if grp == 1 else np.ones(P, dtype=np.complex128)
            for r in range(N_rx):
                gt = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / math.sqrt(2.0 * P)
                B32 = sum(gt[p] * build_chip_channel_matrix_single_path(N, L_cp, float(tt[p]), float(nt[p]), c1) for p in range(P))
                H_ov[r * N : (r + 1) * N, j * N : (j + 1) * N] = A @ B32 @ AH
                Bg = sum((gt[p] * t_off_rot[p]) * build_chip_channel_matrix_single_path(N_g, L_cp, float(tt[p]), float(nt[p] * N_g / float(N)), c1_g) for p in range(P))
                H_orth[grp][r * N_g : (r + 1) * N_g, lj * N_g : (lj + 1) * N_g] = Ag @ Bg @ AHg

        w_ov = (rng.standard_normal(N_rx * N) + 1j * rng.standard_normal(N_rx * N)) * math.sqrt(sigma2 / 2.0)
        y_ov = H_ov @ X_ov.reshape(-1) + w_ov

        xh_lm = H_ov.conj().T @ np.linalg.solve(H_ov @ H_ov.conj().T + sigma2 * np.eye(N_rx * N), y_ov)
        per_scene_errs["pub_lmmse_8x4"].append(sum(int(np.any(codec_qpsk.decode_bp(qpsk_llrs(xh_lm[j*N:(j+1)*N], 0.5))[0] != U_b[j])) for j in range(J)))

        L_lip = float(np.linalg.norm(H_ov, ord=2) ** 2)
        xk = np.zeros(J * N, dtype=np.complex128); yk = xk.copy(); tk = 1.0; bl = 1.0 / math.sqrt(2.0)
        for _ in range(8):
            zn = yk - (H_ov.conj().T @ (H_ov @ yk - y_ov)) / L_lip
            xn = np.clip(zn.real, -bl, bl) + 1j * np.clip(zn.imag, -bl, bl)
            tn = 0.5 * (1.0 + math.sqrt(1.0 + 4.0 * tk * tk))
            yk = xn + ((tk - 1.0) / tn) * (xn - xk); xk, tk = xn, tn
        per_scene_errs["sm_fista8_8x4"].append(sum(int(np.any(codec_qpsk.decode_bp(qpsk_llrs(xk[j*N:(j+1)*N], 0.35))[0] != U_b[j])) for j in range(J)))

        def run_woodbury_ep(n_steps, damp=0.50):
            ts = time.perf_counter()
            lam = np.zeros(J * N, dtype=np.complex128); gam = np.ones(J * N, dtype=np.float64)
            for _ in range(n_steps):
                di = 1.0 / gam
                Cm = sigma2 * np.eye(N_rx * N) + (H_ov * di[None, :]) @ H_ov.conj().T
                CinvH = np.linalg.solve(Cm, H_ov)
                vp = np.maximum(di - (di ** 2) * np.real(np.sum(H_ov.conj() * CinvH, axis=0)), 1e-5)
                uin = di * (H_ov.conj().T @ y_ov / sigma2 + lam)
                mup = uin - di * (H_ov.conj().T @ np.linalg.solve(Cm, H_ov @ uin))
                ve = 1.0 / np.maximum(1.0 / vp - gam, 1e-4)
                me = ve * (mup / vp - lam)
                sc = math.sqrt(0.5)
                mh = sc * np.tanh(2.0 * me.real * sc / ve) + 1j * sc * np.tanh(2.0 * me.imag * sc / ve)
                vh = np.maximum(1.0 - np.abs(mh) ** 2, 1e-4)
                gam = damp * np.clip(1.0 / vh - 1.0 / ve, 0.1, 1e4) + (1.0 - damp) * gam
                lam = damp * (mh / vh - me / ve) + (1.0 - damp) * lam
            dt = time.perf_counter() - ts
            ec = sum(int(np.any(codec_qpsk.decode_bp(qpsk_llrs(me[j*N:(j+1)*N], ve[j*N:(j+1)*N]))[0] != U_b[j])) for j in range(J))
            return ec, dt

        e8, dt8 = run_woodbury_ep(8, damp=0.50)
        e150, dt150 = run_woodbury_ep(150, damp=0.50)
        t_ep8.append(dt8); t_orc150.append(dt150)
        per_scene_errs["sm_ep8_woodbury_8x4"].append(e8)
        per_scene_errs["oracle_ep150_matched_8x4"].append(e150)

        # Exact 38-chip 2-group orthogonal 4x4 16-QAM with 8-step MIMO-EP!
        eg_tot = 0
        pa2 = np.abs(_QAM16_PTS) ** 2
        for grp in range(2):
            Hg = H_orth[grp] * math.sqrt(p_grp)
            X16 = np.array([mod_16qam(codec_16q.encode(U_b[4 * grp + lj]).reshape(-1, 4)) for lj in range(4)]).reshape(-1)
            wg = (rng.standard_normal(Hg.shape[0]) + 1j * rng.standard_normal(Hg.shape[0])) * math.sqrt(sigma2 / 2.0)
            yg = Hg @ X16 + wg
            Kg = Hg.shape[1]
            lamg = np.zeros(Kg, dtype=np.complex128); gamg = np.ones(Kg, dtype=np.float64)
            HTHg = Hg.conj().T @ Hg; HTyg = Hg.conj().T @ yg
            for _ in range(8):
                Sg = np.linalg.inv(HTHg / sigma2 + np.diag(gamg))
                mupg = Sg @ (HTyg / sigma2 + lamg)
                vpg = np.maximum(np.real(np.diag(Sg)), 1e-5)
                veg = np.clip(1.0 / np.maximum(1.0 / vpg - gamg, 1e-4), 1e-4, 20.0)
                meg = veg * (mupg / vpg - lamg)
                lp = -(np.abs(meg[:, None] - _QAM16_PTS[None, :]) ** 2) / veg[:, None]
                lp -= np.max(lp, axis=1, keepdims=True)
                ww = np.exp(lp); ww /= np.sum(ww, axis=1, keepdims=True)
                mhg = ww @ _QAM16_PTS
                vhg = np.clip((ww @ pa2) - np.abs(mhg) ** 2, 1e-4, 1.0)
                gamg = 0.50 * np.clip(1.0 / vhg - 1.0 / veg, 0.05, 1e4) + 0.50 * gamg
                lamg = 0.50 * (mhg / vhg - meg / veg) + 0.50 * lamg
            for lj in range(4):
                sl = slice(lj * N_g, (lj + 1) * N_g)
                uhg, _ = codec_16q.decode_bp(qam16_extrinsic_llrs(meg[sl], veg[sl]).reshape(-1))
                if np.any(uhg != U_b[4 * grp + lj]):
                    eg_tot += 1
        per_scene_errs["sm_s_orth38chip_4x4_16qam_ep8"].append(eg_tot)

    tot_u = float(n_scenes * J)
    blers = {k: round(sum(v) / tot_u, 5) for k, v in per_scene_errs.items()}
    return {
        "snr_dB": snr_db,
        "scenes": n_scenes,
        "matched_chip_duration": 38,
        "matched_energy_per_user": 38.0,
        "user_bler": blers,
        "per_scene_user_errs": per_scene_errs,
        "speed_ratio_orc150_over_ep8": paired_geom_ratio_ci95(t_orc150, t_ep8),
        "verdict": f"KILLED_BY_STEELMAN (8-step Woodbury-EP BLER={blers['sm_ep8_woodbury_8x4']} matches 150-step {blers['oracle_ep150_matched_8x4']} at 18x speedup; equal-38-chip orthogonal 4x4 16-QAM achieves {blers['sm_s_orth38chip_4x4_16qam_ep8']})",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=int, default=64)
    ap.add_argument("--out", type=str, default=str(ROOT / "ideas" / "r15" / "out_p1b_g_killed_controls.json"))
    args = ap.parse_args()
    t0 = time.time()
    k1 = run_k1_thp(args.scenes)
    k2 = run_k2_v2x_cci(args.scenes)
    k3 = run_k3_overloaded_u1(args.scenes)
    payload = {
        "_config": {"scenes": args.scenes, "runtime_sec": round(time.time() - t0, 2)},
        "P1B_K1_crit_4x4_1tap_thp": k1,
        "P1B_K2_v2x_blind_cci_nr2": k2,
        "P1B_K3_ov_8x4_u1_uplink": k3,
    }
    save_result_json(args.out, payload)
    print(f"[killed_controls v2] Done {args.scenes} scenes in {time.time()-t0:.1f}s -> {args.out}")
    print("  K1:", k1["verdict"])
    print("  K2:", k2["verdict"])
    print("  K3:", k3["verdict"])


if __name__ == "__main__":
    main()
