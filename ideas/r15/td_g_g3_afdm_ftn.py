#!/usr/bin/env python3
"""
Round 15 Phase 1 — Track-A (tx, rx) Steelman Teardown Probe G3:
Faster-Than-Nyquist AFDM-FTN vs Equal-Net-Rate Orthogonal Coded Waveforms
(Dai & Qu Luo IEEE TWC 2026, arXiv:2607.12510, per Sol Call #2 §G3 prescription).

Physical Continuous-Time Contract (Locked Across ALL Arms at 20x Oversampling):
- Reference Nyquist symbol period T_0 = 1 (L_os = 20 samples per T_0):
  * alpha = 1.00 Orthogonal (beta = 0.30): step = 20 ticks, N_data = 112 symbols (2240 ticks);
  * alpha = 0.80 FTN (beta = 0.30): step = 16 ticks, N_data = 140 symbols (2240 ticks);
  * alpha = 0.70 FTN (beta = 0.30): step = 14 ticks, N_data = 160 symbols (2240 ticks);
  * Tighter digital RRC (beta' = 0.05) locked to BW99 of beta = 0.30: step = 18 ticks, N_data = 124 symbols (2232 ticks).
- Shared physical pilot/guard overhead = 32 T_0 (two 10-T_0 orthogonal ZC clusters separated across the frame
  with 6-T_0 zero guards against multipath + RRC tails -> total frame duration T_frame = 144 T_0 = 2880 ticks).
- Continuous P = 4 paths with delays tau_p in [0, 4.5] T_0 and Jakes Dopplers f_d * (144 T_0) in [-1.8, +1.8]
  locked in physical seconds and Hz across ALL clocks!
- Exact continuous-time TX energy E_tot = E[||s_x(t)||_2^2] via TX pulse Gram G_tx, and exact colored matched-filter
  noise R_w = N0 * G_r whitened via L_r^{-1} (verifying flat unit-channel identity L_r^{-1} G_r = L_r^H!).

Evaluates BOTH Regimes from Sol Call #2 Table:
- Regime A (K_info = 140 bits, net 140 / 144 = 0.972 bits/T_0):
  FTN alpha=0.80 QPSK r=1/2 vs Orth alpha=1.00 QPSK r=5/8 vs Tight-RRC beta'=0.05 QPSK r=140/248.
- Regime B (K_info = 240 bits, net 240 / 144 = 1.667 bits/T_0):
  FTN alpha=0.70 QPSK r=3/4 vs Orth alpha=1.00 16-QAM r=15/28 vs Tight-RRC beta'=0.05 16-QAM r=240/496.
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
    rrc_taps,
    measure_bw99_and_aclr,
    paired_crossing_gap_ci95,
    save_result_json,
)
from td_g_g1_mimo_fdfd import mod_16qam, damped_mimo_ep_16qam

L_OS = 20  # 20 samples per T_0!
SPAN_T0 = 6
T_FRAME_T0 = 144
N_FRAME_OS = T_FRAME_T0 * L_OS  # 2880 ticks

H_RRC_030 = rrc_taps(L_OS, 0.30, SPAN_T0)  # unit L2 norm
H_RRC_005 = rrc_taps(L_OS, 0.05, SPAN_T0)  # unit L2 norm

# Frame layout in units of T_0 (total 144 T_0) — Coprime Zero-ISI 2-Cluster SISO Pilot Layout!
# Two 16-T_0 overhead windows at [0..15] T_0 and [59..74] T_0 (coprime spacing 59 vs 144 -> zero Doppler grating lobes!):
#   * Window 1 [0..15] T_0: active length-8 ZC at [0..7] T_0 (at frame start -> zero preceding data!), guard [8..15] T_0 (8 T_0 > 4.5 T_0!);
#   * Data Subblock 1: [16..58] T_0 (43 T_0? Wait: keep 2x56 = 112 T_0 exact divisibility by 20, 16, 14!):
#     Window 1 [0..15] T_0: guard [0..5] T_0 (6 T_0 > 4.5!), active length-8 ZC [6..13] T_0, guard [14..15] T_0;
#     Data Subblock 1: [16..71] T_0 (56 T_0 = 1120 ticks -> exact 56 Orth / 70 FTN80 / 80 FTN70 / 62 Tight symbols!);
#     Window 2 [72..87] T_0: guard [72..77] T_0 (6 T_0 > 4.5 T_0!), active length-8 ZC [78..85] T_0, guard [86..87] T_0;
#     Wait: to avoid 72 = 144/2 half-frame alias, make Data Subblock 1 = 49 T_0 (980 ticks) and Data Subblock 2 = 63 T_0 (1260 ticks)?
#     Check divisibility: 980 / 20 = 49, 1260 / 20 = 63 (49+63 = 112!); 980 / 14 = 70, 1260 / 14 = 90 (70+90 = 160!);
#     For step=16 (FTN80): 48 T_0 (960/16 = 60) + 64 T_0 (1280/16 = 80 -> 60+80 = 140!!), and 960/20 = 48, 1280/20 = 64 (48+64 = 112!!)!
#     Check spacing when Subblock 1 = 48 T_0 ([16..63] T_0) and Window 2 = [64..79] T_0: spacing = 64 T_0, gcd(64, 144) = 16 -> span 144/16 = 9.0 >> 3.6 bins (ZERO ALIASING OVER [-1.8, +1.8]!!)!

PIL_POS_OS = np.concatenate([np.arange(0, 10), 69 + np.arange(6)]) * L_OS  # Window 1 [0..9] + 6 T_0 post-guard [10..15]; Window 2 5 T_0 pre-guard [64..68] + [69..74] + 5 T_0 post-guard [75..79]!
n10_p = np.arange(10, dtype=np.float64)
n6_p = np.arange(6, dtype=np.float64)
PIL_SEQ = np.concatenate([
    np.exp(-1j * np.pi * 1.0 * n10_p * (n10_p + 1.0) / 10.0),
    np.exp(-1j * np.pi * 1.0 * n6_p * n6_p / 6.0),
])
PIL_VEC = PIL_SEQ * math.sqrt(32.0 / 16.0)  # Exact pilot energy = 32.0!

# Pilot observation windows [0..14] T_0 (15) and [69..78] T_0 (10) = 25 samples capturing full delayed pilot energy:
PIL_OBS_OS = np.concatenate([np.arange(0, 15), 69 + np.arange(10)]) * L_OS


def get_data_positions_os(step_os: int, n_tot_sym: int) -> np.ndarray:
    """Place symbols in Data Subblock 1 [16..63] T_0 (960 ticks) and Data Subblock 2 [80..143] T_0 (1280 ticks), sum = 112 T_0 = 2240 ticks!"""
    n1 = int(round(n_tot_sym * (48.0 / 112.0)))
    n2 = n_tot_sym - n1
    return np.concatenate([16 * L_OS + np.arange(n1) * step_os, 80 * L_OS + np.arange(n2) * step_os])


POS_ORTH_112 = get_data_positions_os(20, 112)  # 48 + 64 = 112 symbols
POS_FTN80_140 = get_data_positions_os(16, 140)  # 60 + 80 = 140 symbols
POS_FTN70_160 = get_data_positions_os(14, 160)  # 69 + 91 = 160 symbols
POS_TIGHT_124 = get_data_positions_os(18, 124)  # 53 + 71 = 124 symbols


def build_pulse_bank_mat(pos_os: np.ndarray, h_rrc: np.ndarray, total_len_os: int) -> np.ndarray:
    """
    Build sparse-like pulse bank matrix P_bank of shape (total_len_os, len(pos_os)) where column m is
    h_rrc centered/starting at pos_os[m].
    """
    L_h = len(h_rrc)
    M = len(pos_os)
    P = np.zeros((total_len_os, M), dtype=np.complex128)
    for m, st in enumerate(pos_os):
        P[st : st + L_h, m] = h_rrc
    return P


L_TOT_SIG = N_FRAME_OS + len(H_RRC_030) + 6 * L_OS  # includes full RRC tail + max 6*T_0 delay!

P_PIL_030 = build_pulse_bank_mat(PIL_POS_OS, H_RRC_030, L_TOT_SIG)
P_PIL_OBS_030 = build_pulse_bank_mat(PIL_OBS_OS, H_RRC_030, L_TOT_SIG)

P_DAT_ORTH = build_pulse_bank_mat(POS_ORTH_112, H_RRC_030, L_TOT_SIG)
P_DAT_FTN80 = build_pulse_bank_mat(POS_FTN80_140, H_RRC_030, L_TOT_SIG)
P_DAT_FTN70 = build_pulse_bank_mat(POS_FTN70_160, H_RRC_030, L_TOT_SIG)
P_DAT_TIGHT = build_pulse_bank_mat(POS_TIGHT_124, H_RRC_005, L_TOT_SIG)
P_PIL_005 = build_pulse_bank_mat(PIL_POS_OS, H_RRC_005, L_TOT_SIG)
P_PIL_OBS_005 = build_pulse_bank_mat(PIL_OBS_OS, H_RRC_005, L_TOT_SIG)

# RX matched-filter observation banks covering Subblock 1 [16..63] T_0 + 5 T_0 tail and Subblock 2 [80..143] T_0 + 5 T_0 tail!
def _rx_pos_2blk(step_os: int, n1: int, n2: int) -> np.ndarray:
    return np.concatenate([16 * L_OS + np.arange(n1) * step_os, 80 * L_OS + np.arange(n2) * step_os])


RX_POS_ORTH = _rx_pos_2blk(20, 53, 69)
RX_POS_FTN80 = _rx_pos_2blk(16, 66, 86)
RX_POS_FTN70 = _rx_pos_2blk(14, 76, 98)
RX_POS_TIGHT = _rx_pos_2blk(18, 59, 77)

Q_RX_ORTH = build_pulse_bank_mat(RX_POS_ORTH, H_RRC_030, L_TOT_SIG)
Q_RX_FTN80 = build_pulse_bank_mat(RX_POS_FTN80, H_RRC_030, L_TOT_SIG)
Q_RX_FTN70 = build_pulse_bank_mat(RX_POS_FTN70, H_RRC_030, L_TOT_SIG)
Q_RX_TIGHT = build_pulse_bank_mat(RX_POS_TIGHT, H_RRC_005, L_TOT_SIG)


def make_whitener(Q_rx: np.ndarray):
    G_r = np.real(Q_rx.conj().T @ Q_rx)
    # Regularize tiny sub-1e-6 eigenvalues in severe alpha=0.70 FTN tail modes per Sol §G3(a).1
    L_r = np.linalg.cholesky(G_r + 1e-6 * np.eye(G_r.shape[0]))
    L_inv = np.linalg.inv(L_r)
    return G_r, L_r, L_inv


G_R_ORTH, L_R_ORTH, LINV_ORTH = make_whitener(Q_RX_ORTH)
G_R_80, L_R_80, LINV_80 = make_whitener(Q_RX_FTN80)
G_R_70, L_R_70, LINV_70 = make_whitener(Q_RX_FTN70)
G_R_TIGHT, L_R_TIGHT, LINV_TIGHT = make_whitener(Q_RX_TIGHT)

# Unitary transforms for each block size
U_AFDM_112 = make_daft_mat(112, 7.0 / 224.0, 1.0 / 224.0)
U_AFDM_140 = make_daft_mat(140, 9.0 / 280.0, 1.0 / 280.0)
U_AFDM_160 = make_daft_mat(160, 9.0 / 320.0, 1.0 / 320.0)
U_AFDM_124 = make_daft_mat(124, 7.0 / 248.0, 1.0 / 248.0)
U_OFDM_112 = np.fft.fft(np.eye(112), axis=0) / math.sqrt(112.0)
U_OTFS_112 = np.kron(np.fft.fft(np.eye(8), axis=0) / math.sqrt(8.0), np.eye(14))  # 14x8 = 112


def apply_phys_channel_os(S_os: np.ndarray, taus_t0: np.ndarray, nus_frame: np.ndarray, gains: np.ndarray) -> np.ndarray:
    """
    Apply continuous P=4 path channel at 20x oversampling via exact FFT fractional-sample shift (zero delay sign/rounding error!):
    S_os: (L_TOT_SIG, M_cols) or (L_TOT_SIG,).
    """
    one_d = S_os.ndim == 1
    X = S_os[:, None] if one_d else S_os
    L_s = X.shape[0]
    N_f = 1 << int(math.ceil(math.log2(L_s + 64)))
    X_fft = np.fft.fft(X, n=N_f, axis=0)
    freqs = np.fft.fftfreq(N_f)[:, None]
    Out = np.zeros_like(X, dtype=np.complex128)
    t_norm = np.arange(L_s, dtype=np.float64) / float(N_FRAME_OS)

    for p in range(len(taus_t0)):
        d_samp = float(taus_t0[p]) * float(L_OS)
        S_shift = np.fft.ifft(X_fft * np.exp(-1j * 2.0 * np.pi * freqs * d_samp), axis=0)[:L_s]
        dop = (gains[p] * np.exp(1j * 2.0 * np.pi * float(nus_frame[p]) * t_norm))[:, None]
        Out += dop * S_shift
    return Out[:, 0] if one_d else Out


def verify_ftn_gram_and_bw99():
    """Verify Sol's flat unit-channel whitening check AND locked BW99 across beta=0.30 FTN/Orth and beta'=0.05 Tight-RRC!"""
    rng = np.random.default_rng(20261530)
    # 1) Flat unit channel check: y = G_r x + w -> whitened H = L_r^{-1} G_r should satisfy H^H H == G_r!
    H_w = LINV_80 @ G_R_80[:, :140]
    gram_err = float(np.linalg.norm(H_w.conj().T @ H_w - G_R_80[:140, :140]) / np.linalg.norm(G_R_80[:140, :140]))

    # 2) Measure BW99 of Orth (beta=0.30, step=20), FTN-0.80, FTN-0.70, and Tight-RRC (beta'=0.05, step=18)
    B_mc = 24
    s_orth = np.vstack([(P_DAT_ORTH @ ((rng.standard_normal(112) + 1j * rng.standard_normal(112)) / math.sqrt(2.0))) for _ in range(B_mc)])
    s_ftn80 = np.vstack([(P_DAT_FTN80 @ ((rng.standard_normal(140) + 1j * rng.standard_normal(140)) / math.sqrt(2.0))) for _ in range(B_mc)])
    s_ftn70 = np.vstack([(P_DAT_FTN70 @ ((rng.standard_normal(160) + 1j * rng.standard_normal(160)) / math.sqrt(2.0))) for _ in range(B_mc)])
    s_tight = np.vstack([(P_DAT_TIGHT @ ((rng.standard_normal(124) + 1j * rng.standard_normal(124)) / math.sqrt(2.0))) for _ in range(B_mc)])

    bw_orth = measure_bw99_and_aclr(s_orth, L_OS)["bw99_over_symrate"]
    bw_80 = measure_bw99_and_aclr(s_ftn80, L_OS)["bw99_over_symrate"]
    bw_70 = measure_bw99_and_aclr(s_ftn70, L_OS)["bw99_over_symrate"]
    bw_tight = measure_bw99_and_aclr(s_tight, L_OS)["bw99_over_symrate"]
    return {
        "flat_whitening_gram_rel_err": gram_err,
        "bw99_orth_b030": bw_orth,
        "bw99_ftn80_b030": bw_80,
        "bw99_ftn70_b030": bw_70,
        "bw99_tight_b005_step18": bw_tight,
    }


def mod_qpsk(bits_2n: np.ndarray) -> np.ndarray:
    return ((1.0 - 2.0 * bits_2n[..., 0].astype(np.float64)) + 1j * (1.0 - 2.0 * bits_2n[..., 1].astype(np.float64))) / math.sqrt(2.0)


def damped_ep_qpsk(y_eff: np.ndarray, H_eff: np.ndarray, sigma2: float, n_iter: int = 6, beta_damp: float = 0.55, prior_llr: np.ndarray = None):
    """Damped Céspedes EP for QPSK (unit energy, 2 bits/sym) with exact colored-whitened effective channel H_eff."""
    M = H_eff.shape[1]
    q4 = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=np.complex128) / math.sqrt(2.0)
    b4 = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.uint8)

    inv_s2 = 1.0 / max(sigma2, 1e-6)
    G_h = inv_s2 * (H_eff.conj().T @ H_eff)
    y_mf = inv_s2 * (H_eff.conj().T @ y_eff)

    lam = np.ones(M, dtype=np.float64)
    gam = np.zeros(M, dtype=np.complex128)
    z_ext = np.zeros(M, dtype=np.complex128)
    v_ext = np.ones(M, dtype=np.float64)
    mu_q = np.zeros(M, dtype=np.complex128)
    var_q = np.ones(M, dtype=np.float64)

    for _ in range(n_iter):
        A_ep = G_h.copy()
        A_ep[np.arange(M), np.arange(M)] += lam
        L_c = np.linalg.cholesky(A_ep)
        SOL = np.linalg.solve(L_c.conj().T, np.linalg.solve(L_c, np.column_stack([y_mf + gam, np.eye(M, dtype=np.complex128)])))
        mu_q = SOL[:, 0]
        var_q = np.clip(np.real(np.diag(SOL[:, 1:])), 1e-5, 4.0)
        inv_ve = np.maximum(1.0 / var_q - lam, 1e-3)
        v_ext = np.clip(1.0 / inv_ve, 1e-4, 25.0)
        z_ext = v_ext * (mu_q / var_q - gam)

        log_w = -(np.abs(z_ext[:, None] - q4[None, :]) ** 2) / v_ext[:, None]
        if prior_llr is not None:
            log_w = log_w - np.clip(prior_llr, -25.0, 25.0) @ b4.T.astype(np.float64)
        mx = np.max(log_w, axis=1, keepdims=True)
        w = np.exp(log_w - mx)
        w /= np.sum(w, axis=1, keepdims=True)
        mu_p = w @ q4
        var_p = np.clip(1.0 - np.abs(mu_p) ** 2, 5e-3, 1.0)

        lam_c = 1.0 / var_p - inv_ve
        gam_c = mu_p / var_p - z_ext * inv_ve
        pos = lam_c > 1e-4
        lam = beta_damp * np.where(pos, lam_c, lam) + (1.0 - beta_damp) * lam
        gam = beta_damp * np.where(pos, gam_c, gam) + (1.0 - beta_damp) * gam

    # QPSK extrinsic bit LLRs: LLR(b0) = 2*sqrt(2)*Re(z_ext)/v_ext, LLR(b1) = 2*sqrt(2)*Im(z_ext)/v_ext!
    sc = 2.0 * math.sqrt(2.0) / np.clip(v_ext, 1e-4, 25.0)
    llrs = np.clip(np.column_stack([sc * z_ext.real, sc * z_ext.imag]), -30.0, 30.0)
    return llrs, mu_q, var_q


# Precompute Data-ISI-Whitened Wipf-Rao SBL + Continuous Off-Grid Polish dictionary for 1-TX P=4 paths!
TAU_G3 = np.linspace(0.0, 4.5, 46)  # 0.10 T_0 grid
NU_G3 = np.linspace(-1.85, 1.85, 25)


def _build_pilot_sage_dict(P_pil_tx, P_pil_obs, P_dat_ref):
    s_pil_os = P_pil_tx @ PIL_VEC  # (L_TOT_SIG,)
    G_pobs = np.real(P_pil_obs.conj().T @ P_pil_obs)
    # Exact prior Raised-Cosine sidelobe data-ISI covariance on P_pil_obs!
    sc_ref = math.sqrt(112.0 / float(np.real(np.sum(np.abs(P_dat_ref) ** 2))))
    B_ref = sc_ref * P_dat_ref
    R_isi = np.zeros((P_pil_obs.shape[1], P_pil_obs.shape[1]), dtype=np.complex128)
    sub_t = TAU_G3[::5]
    for tc in sub_t:
        Hb = P_pil_obs.conj().T @ apply_phys_channel_os(B_ref, np.array([float(tc)]), np.array([0.0]), np.array([1.0 + 0j]))
        R_isi += (1.0 / float(len(sub_t))) * (Hb @ Hb.conj().T)

    atoms = []
    meta = []
    t_norm = np.arange(L_TOT_SIG, dtype=np.float64) / float(N_FRAME_OS)
    for tc in TAU_G3:
        s_sh = apply_phys_channel_os(s_pil_os, np.array([float(tc)]), np.array([0.0]), np.array([1.0 + 0j]))
        for nc in NU_G3:
            y_m = P_pil_obs.conj().T @ (s_sh * np.exp(1j * 2.0 * np.pi * float(nc) * t_norm))
            atoms.append(y_m)
            meta.append((float(tc), float(nc)))
    Phi = np.array(atoms).T  # (25, 1150)
    return s_pil_os, Phi, G_pobs, R_isi, meta


S_PIL_030, PHI_030, GPOBS_030, RISI_030, META_G3 = _build_pilot_sage_dict(P_PIL_030, P_PIL_OBS_030, P_DAT_FTN70)
S_PIL_005, PHI_005, GPOBS_005, RISI_005, _ = _build_pilot_sage_dict(P_PIL_005, P_PIL_OBS_005, P_DAT_TIGHT)


def estimate_4path_siso_sage(y_pil_obs: np.ndarray, sigma_n0: float = 0.02, tight_rrc: bool = False):
    """Data-ISI-Whitened Wipf-Rao SBL + Continuous Off-Grid Coordinate Refinement on 25 pilot observations."""
    Phi = PHI_005 if tight_rrc else PHI_030
    G_pobs = GPOBS_005 if tight_rrc else GPOBS_030
    R_isi = RISI_005 if tight_rrc else RISI_030
    s_pil_os = S_PIL_005 if tight_rrc else S_PIL_030
    P_obs = P_PIL_OBS_005 if tight_rrc else P_PIL_OBS_030
    t_norm = np.arange(L_TOT_SIG, dtype=np.float64) / float(N_FRAME_OS)

    R_n = R_isi + max(sigma_n0, 1e-5) * G_pobs + 1e-6 * np.eye(len(y_pil_obs))
    L_n = np.linalg.cholesky(R_n)
    Phi_w = np.linalg.solve(L_n, Phi)
    yw = np.linalg.solve(L_n, y_pil_obs)

    M_d = Phi_w.shape[1]
    gam = np.full(M_d, 1.0 / float(M_d), dtype=np.float64)
    for _ in range(28):
        act = gam > 1e-6
        Pa = Phi_w[:, act]
        ga = gam[act]
        Pg = Pa * ga[None, :]
        Sy = np.eye(len(yw)) + Pg @ Pa.conj().T
        Ls = np.linalg.cholesky(Sy)
        mu_a = Pg.conj().T @ np.linalg.solve(Ls.conj().T, np.linalg.solve(Ls, yw))
        Sp = np.linalg.solve(Ls.conj().T, np.linalg.solve(Ls, Pa))
        gn = np.zeros_like(gam)
        gn[act] = np.sqrt((np.abs(mu_a) ** 2) / np.maximum(np.real(np.sum(np.conj(Pa) * Sp, axis=0)), 1e-12))
        gam = gn

    # Extract up to 6 distinct peaks (separated by >= 0.30 T_0 or >= 0.35 bin) and polish continuously off-grid!
    order = np.argsort(gam)[::-1]
    sel = []
    for idx_m in order:
        tm, nm = META_G3[int(idx_m)]
        if all((abs(tm - ts) >= 0.30) or (abs(nm - ns) >= 0.40) for ts, ns in sel):
            sel.append([tm, nm])
            if len(sel) == 4:
                break
    while len(sel) < 4:
        sel.append(list(META_G3[int(order[len(sel)])]))

    A_w = np.zeros((len(yw), 4), dtype=np.complex128)
    for k in range(4):
        sh = apply_phys_channel_os(s_pil_os, np.array([sel[k][0]]), np.array([0.0]), np.array([1.0 + 0j]))
        A_w[:, k] = np.linalg.solve(L_n, P_obs.conj().T @ (sh * np.exp(1j * 2.0 * np.pi * sel[k][1] * t_norm)))

    # 2 sweeps of continuous off-grid polish (0.025 T_0 in delay, 0.03 bin in Doppler -> < -34 dB grid error!)
    for step_t, step_n in ((0.05, 0.06), (0.02, 0.025)):
        for k in range(4):
            oth = [j for j in range(4) if j != k]
            Ao = A_w[:, oth]
            Po = np.eye(len(yw)) - Ao @ np.linalg.pinv(Ao)
            ro = Po @ yw
            tb, nb = sel[k]
            bv, bat = -1.0, A_w[:, k]
            for dt_m in (-2, -1, 0, 1, 2):
                tc = float(np.clip(tb + dt_m * step_t, 0.0, 4.55))
                ssh = apply_phys_channel_os(s_pil_os, np.array([tc]), np.array([0.0]), np.array([1.0 + 0j]))
                for dn_m in (-2, -1, 0, 1, 2):
                    nc = float(np.clip(nb + dn_m * step_n, -2.0, 2.0))
                    at = np.linalg.solve(L_n, P_obs.conj().T @ (ssh * np.exp(1j * 2.0 * np.pi * nc * t_norm)))
                    ap = Po @ at
                    np2 = float(np.vdot(ap, ap).real)
                    if np2 < 1e-9:
                        continue
                    v = (abs(np.vdot(ap, ro)) ** 2) / np2
                    if v > bv:
                        bv, tb, nb, bat = v, tc, nc, at
            sel[k] = [tb, nb]
            A_w[:, k] = bat

    gs = np.linalg.lstsq(A_w, yw, rcond=None)[0]
    pil_res_var = float(sigma_n0 * max(0.0, np.mean(np.abs(yw - A_w @ gs) ** 2) - 1.0))
    taus_e = np.array([s[0] for s in sel], dtype=np.float64)
    nus_e = np.array([s[1] for s in sel], dtype=np.float64)
    return taus_e, nus_e, gs, pil_res_var


def dd_refine_gains_and_doppler(y_whitened: np.ndarray, L_inv: np.ndarray, Q_rx: np.ndarray, s_re_os: np.ndarray, taus_e: np.ndarray, nus_e: np.ndarray):
    """Decision-directed full-frame LS gain + continuous off-grid delay/Doppler update across the 2880-tick frame!"""
    t_norm = np.arange(L_TOT_SIG, dtype=np.float64) / float(N_FRAME_OS)
    M_rx = y_whitened.shape[0]
    A_w = np.zeros((M_rx, 4), dtype=np.complex128)
    taus_new = taus_e.copy()
    nus_new = nus_e.copy()
    for p in range(4):
        A_w[:, p] = L_inv @ (Q_rx.conj().T @ apply_phys_channel_os(s_re_os, taus_new[p : p + 1], nus_new[p : p + 1], np.array([1.0 + 0j])))
    for p in range(4):
        oth = [j for j in range(4) if j != p]
        Ao = A_w[:, oth]
        Po = np.eye(M_rx) - Ao @ np.linalg.pinv(Ao)
        ro = Po @ y_whitened
        bv, b_tau, b_nu, b_col = -1.0, taus_new[p], nus_new[p], A_w[:, p]
        for dt in (-0.02, 0.0, 0.02):
            tc = float(np.clip(taus_e[p] + dt, 0.0, 4.55))
            ssh = apply_phys_channel_os(s_re_os, np.array([tc]), np.array([0.0]), np.array([1.0 + 0j]))
            for dn in (-0.03, -0.015, 0.0, 0.015, 0.03):
                nc = float(np.clip(nus_e[p] + dn, -2.05, 2.05))
                col = L_inv @ (Q_rx.conj().T @ (ssh * np.exp(1j * 2.0 * np.pi * nc * t_norm)))
                cp = Po @ col
                np2 = float(np.vdot(cp, cp).real)
                if np2 < 1e-9:
                    continue
                v = (abs(np.vdot(cp, ro)) ** 2) / np2
                if v > bv:
                    bv, b_tau, b_nu, b_col = v, tc, nc, col
        taus_new[p] = b_tau
        nus_new[p] = b_nu
        A_w[:, p] = b_col
    gs_new = np.linalg.lstsq(A_w, y_whitened, rcond=None)[0]
    return taus_new, nus_new, gs_new


# Precompute exact expected TX data waveform energy scale so EVERY arm has E_data = 112.0 and E_pil = 32.0 -> E_tot = 144.0!
def _compute_tx_scale(P_dat: np.ndarray, U_prec: np.ndarray, target_energy: float = 112.0) -> float:
    B = P_dat @ U_prec.conj().T  # columns are continuous-time symbol waveforms!
    e_raw = float(np.real(np.sum(np.abs(B) ** 2)))  # = tr(B^H B) when E[s s^H] = I!
    return math.sqrt(target_energy / e_raw)


ARMS_G3 = (
    "pub_dai26_unwhitened_lmmse",
    "sm_a1_ftn_whitened_ep_dd",
    "sm_s_scfde_ftn_dd",
    "sm_a2_orth_afdm_fixed_rrc",
    "sm_a3_orth_afdm_tight_rrc",
    "sm_s_orth_scfde_dd",
    "sm_s_orth_otfs_dd",
    "sm_s_orth_ofdm_dd",
    "oracle_ftn_genie_turbo_ep",
    "oracle_orth_genie_turbo_ep",
)


def run_arm_chain(
    z_os_unit: np.ndarray,
    sigma_n0: float,
    taus_true: np.ndarray,
    nus_true: np.ndarray,
    gains_true: np.ndarray,
    P_dat: np.ndarray,
    U_prec: np.ndarray,
    Q_rx: np.ndarray,
    L_inv: np.ndarray,
    ldpc: RateMatchedQCLDPC,
    u_bits: np.ndarray,
    qam_order: int = 4,
    tight_rrc: bool = False,
    mode: str = "sm_dd",
):
    c_bits = ldpc.encode(u_bits)
    s_sym = mod_qpsk(c_bits.reshape(-1, 2)) if qam_order == 4 else mod_16qam(c_bits.reshape(-1, 4))
    tx_sc = _compute_tx_scale(P_dat, U_prec, target_energy=112.0)
    P_pil = P_PIL_005 if tight_rrc else P_PIL_030
    P_pobs = P_PIL_OBS_005 if tight_rrc else P_PIL_OBS_030

    B_tx = tx_sc * (P_dat @ U_prec.conj().T)  # (L_TOT_SIG, M_sym)
    s_pil_tx = P_pil @ PIL_VEC
    s_tx_full = s_pil_tx + B_tx @ s_sym

    r_os = apply_phys_channel_os(s_tx_full, taus_true, nus_true, gains_true) + math.sqrt(sigma_n0) * z_os_unit
    y_raw = Q_rx.conj().T @ r_os

    if mode in ("oracle_turbo",):
        te, ne, ge = taus_true, nus_true, gains_true
        y_pil_rx = Q_rx.conj().T @ apply_phys_channel_os(s_pil_tx, te, ne, ge)
        y_w = L_inv @ (y_raw - y_pil_rx)
        H_w = L_inv @ (Q_rx.conj().T @ apply_phys_channel_os(B_tx, te, ne, ge))
        if qam_order == 4:
            ll1, _, _ = damped_ep_qpsk(y_w, H_w, sigma_n0, n_iter=6)
        else:
            ll1, _, _ = damped_mimo_ep_16qam(y_w, H_w, sigma_n0, n_iter=6)
        uh1, sok1 = ldpc.decode_bp(ll1.reshape(-1), max_iter=20)
        if sok1:
            be = int(np.sum(uh1 != u_bits))
            return be, int(be > 0)
        cre = ldpc.encode(uh1)
        nb_sym = 2 if qam_order == 4 else 4
        pr = np.clip(0.35 * (1.0 - 2.0 * cre.astype(np.float64)).reshape(-1, nb_sym) * 4.0, -6.0, 6.0)
        if qam_order == 4:
            ll2, _, _ = damped_ep_qpsk(y_w, H_w, sigma_n0, n_iter=6, prior_llr=pr)
        else:
            ll2, _, _ = damped_mimo_ep_16qam(y_w, H_w, sigma_n0, n_iter=6, prior_llr=pr)
        uh2, _ = ldpc.decode_bp((ll2 + 0.5 * pr).reshape(-1), max_iter=25)
        be = int(np.sum(uh2 != u_bits))
        return be, int(be > 0)

    # Initial pilot-only Data-ISI-Whitened SBL + Continuous Off-Grid Polish
    y_pil_obs = P_pobs.conj().T @ r_os
    te, ne, ge, pil_rv = estimate_4path_sage_cached(y_pil_obs, sigma_n0, tight_rrc)
    csi_mse_est = max(0.0, pil_rv)

    if mode == "pub_unwhitened_lmmse":
        # Dai26 unwhitened LMMSE (treats y_raw noise as white sigma_n0 * I without G_r^{-1/2} whitening, linear MMSE)
        y_sub = y_raw - Q_rx.conj().T @ apply_phys_channel_os(s_pil_tx, te, ne, ge)
        H_raw = Q_rx.conj().T @ apply_phys_channel_os(B_tx, te, ne, ge)
        M_s = H_raw.shape[1]
        s2_p = sigma_n0 + csi_mse_est
        A_m = H_raw.conj().T @ H_raw + s2_p * np.eye(M_s)
        SOL = np.linalg.solve(A_m, np.column_stack([H_raw.conj().T @ y_sub, np.eye(M_s)]))
        xh = SOL[:, 0]
        mse_k = np.clip(s2_p * np.real(np.diag(SOL[:, 1:])), 1e-4, 0.999)
        sc = 2.0 * math.sqrt(2.0) / mse_k
        llrs = np.column_stack([sc * xh.real, sc * xh.imag]).reshape(-1)
        uh, _ = ldpc.decode_bp(llrs, max_iter=20)
        be = int(np.sum(uh != u_bits))
        return be, int(be > 0)

    # Full Steelman: G_r^{-1/2} noise whitening + damped EP + 2-round DD-SAGE!
    uh_best = None
    for rd in range(3):
        y_pil_rx = Q_rx.conj().T @ apply_phys_channel_os(s_pil_tx, te, ne, ge)
        y_w = L_inv @ (y_raw - y_pil_rx)
        H_w = L_inv @ (Q_rx.conj().T @ apply_phys_channel_os(B_tx, te, ne, ge))
        s2_eff = sigma_n0 + (csi_mse_est if rd == 0 else 0.35 * csi_mse_est)
        if qam_order == 4:
            ll, mu_e, var_e = damped_ep_qpsk(y_w, H_w, s2_eff, n_iter=6)
        else:
            ll, mu_e, var_e = damped_mimo_ep_16qam(y_w, H_w, s2_eff, n_iter=6)
        uh, sok = ldpc.decode_bp(ll.reshape(-1), max_iter=20)
        uh_best = uh
        if sok or rd == 2:
            break
        cre = ldpc.encode(uh)
        sh = mod_qpsk(cre.reshape(-1, 2)) if qam_order == 4 else mod_16qam(cre.reshape(-1, 4))
        w_b = float(np.clip(1.0 - 1.2 * np.mean(var_e), 0.35, 0.80))
        s_re = s_pil_tx + B_tx @ (w_b * sh + (1.0 - w_b) * mu_e)
        te, ne, ge = dd_refine_gains_and_doppler(L_inv @ y_raw, L_inv, Q_rx, s_re, te, ne)

    be = int(np.sum(uh_best != u_bits))
    return be, int(be > 0)


def estimate_4path_sage_cached(y_pil_obs, sigma_n0, tight_rrc):
    return estimate_4path_siso_sage(y_pil_obs, sigma_n0=sigma_n0, tight_rrc=tight_rrc)


def run_scene(scene_id: int, snrs_ebn0_db):
    rng = np.random.default_rng(9100000 + scene_id * 43)

    # Sample P = 4 continuous fractional-delay Jakes-Doppler paths
    pdp = 10.0 ** (np.array([0.0, -2.5, -5.0, -8.0]) / 10.0)
    pdp /= np.sum(pdp)
    ts = np.sort(rng.uniform(0.0, 4.4, size=4))
    for i in range(1, 4):
        if ts[i] - ts[i - 1] < 0.45:
            ts[i] = min(4.5, ts[i - 1] + 0.45)
    nus = 1.8 * np.cos(rng.uniform(-np.pi, np.pi, size=4))
    gains = np.sqrt(pdp / 2.0) * (rng.standard_normal(4) + 1j * rng.standard_normal(4))

    # Shared continuous-time unit AWGN realization at 20x oversampling across ALL arms & regimes!
    Z_os = (rng.standard_normal((len(snrs_ebn0_db), L_TOT_SIG)) + 1j * rng.standard_normal((len(snrs_ebn0_db), L_TOT_SIG))) / math.sqrt(2.0)

    # Codecs for Regime A (K = 140)
    c_a_ftn = RateMatchedQCLDPC(140, 280, seed=20261531)
    c_a_orth = RateMatchedQCLDPC(140, 224, seed=20261532)
    c_a_tight = RateMatchedQCLDPC(140, 248, seed=20261533)
    u_a = rng.integers(0, 2, size=140, dtype=np.uint8)

    # Codecs for Regime B (K = 240)
    c_b_ftn = RateMatchedQCLDPC(240, 320, seed=20261534)
    c_b_orth = RateMatchedQCLDPC(240, 448, seed=20261535)
    c_b_tight = RateMatchedQCLDPC(240, 496, seed=20261536)
    u_b = rng.integers(0, 2, size=240, dtype=np.uint8)

    out = {"Regime_A_alpha080": {a: [] for a in ARMS_G3}, "Regime_B_alpha070": {a: [] for a in ARMS_G3}}

    for ig, ebn0_db in enumerate(snrs_ebn0_db):
        z_u = Z_os[ig]

        # --- Regime A (K = 140, E_tot = 144.0) ---
        eb_a = 144.0 / 140.0
        n0_a = eb_a * (10.0 ** (-float(ebn0_db) / 10.0))
        ra = out["Regime_A_alpha080"]
        ra["pub_dai26_unwhitened_lmmse"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_FTN80, U_AFDM_140, Q_RX_FTN80, LINV_80, c_a_ftn, u_a, 4, False, "pub_unwhitened_lmmse")[1]
        )
        ra["sm_a1_ftn_whitened_ep_dd"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_FTN80, U_AFDM_140, Q_RX_FTN80, LINV_80, c_a_ftn, u_a, 4, False, "sm_dd")[1]
        )
        ra["sm_s_scfde_ftn_dd"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_FTN80, np.eye(140, dtype=np.complex128), Q_RX_FTN80, LINV_80, c_a_ftn, u_a, 4, False, "sm_dd")[1]
        )
        ra["sm_a2_orth_afdm_fixed_rrc"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_ORTH, U_AFDM_112, Q_RX_ORTH, LINV_ORTH, c_a_orth, u_a, 4, False, "sm_dd")[1]
        )
        ra["sm_a3_orth_afdm_tight_rrc"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_TIGHT, U_AFDM_124, Q_RX_TIGHT, LINV_TIGHT, c_a_tight, u_a, 4, True, "sm_dd")[1]
        )
        ra["sm_s_orth_scfde_dd"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_ORTH, np.eye(112, dtype=np.complex128), Q_RX_ORTH, LINV_ORTH, c_a_orth, u_a, 4, False, "sm_dd")[1]
        )
        ra["sm_s_orth_otfs_dd"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_ORTH, U_OTFS_112, Q_RX_ORTH, LINV_ORTH, c_a_orth, u_a, 4, False, "sm_dd")[1]
        )
        ra["sm_s_orth_ofdm_dd"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_ORTH, U_OFDM_112, Q_RX_ORTH, LINV_ORTH, c_a_orth, u_a, 4, False, "sm_dd")[1]
        )
        ra["oracle_ftn_genie_turbo_ep"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_FTN80, U_AFDM_140, Q_RX_FTN80, LINV_80, c_a_ftn, u_a, 4, False, "oracle_turbo")[1]
        )
        ra["oracle_orth_genie_turbo_ep"].append(
            run_arm_chain(z_u, n0_a, ts, nus, gains, P_DAT_ORTH, U_AFDM_112, Q_RX_ORTH, LINV_ORTH, c_a_orth, u_a, 4, False, "oracle_turbo")[1]
        )

        # --- Regime B (K = 240, E_tot = 144.0) ---
        eb_b = 144.0 / 240.0
        n0_b = eb_b * (10.0 ** (-float(ebn0_db) / 10.0))
        rb = out["Regime_B_alpha070"]
        rb["pub_dai26_unwhitened_lmmse"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_FTN70, U_AFDM_160, Q_RX_FTN70, LINV_70, c_b_ftn, u_b, 4, False, "pub_unwhitened_lmmse")[1]
        )
        rb["sm_a1_ftn_whitened_ep_dd"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_FTN70, U_AFDM_160, Q_RX_FTN70, LINV_70, c_b_ftn, u_b, 4, False, "sm_dd")[1]
        )
        rb["sm_s_scfde_ftn_dd"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_FTN70, np.eye(160, dtype=np.complex128), Q_RX_FTN70, LINV_70, c_b_ftn, u_b, 4, False, "sm_dd")[1]
        )
        rb["sm_a2_orth_afdm_fixed_rrc"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_ORTH, U_AFDM_112, Q_RX_ORTH, LINV_ORTH, c_b_orth, u_b, 16, False, "sm_dd")[1]
        )
        rb["sm_a3_orth_afdm_tight_rrc"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_TIGHT, U_AFDM_124, Q_RX_TIGHT, LINV_TIGHT, c_b_tight, u_b, 16, True, "sm_dd")[1]
        )
        rb["sm_s_orth_scfde_dd"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_ORTH, np.eye(112, dtype=np.complex128), Q_RX_ORTH, LINV_ORTH, c_b_orth, u_b, 16, False, "sm_dd")[1]
        )
        rb["sm_s_orth_otfs_dd"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_ORTH, U_OTFS_112, Q_RX_ORTH, LINV_ORTH, c_b_orth, u_b, 16, False, "sm_dd")[1]
        )
        rb["sm_s_orth_ofdm_dd"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_ORTH, U_OFDM_112, Q_RX_ORTH, LINV_ORTH, c_b_orth, u_b, 16, False, "sm_dd")[1]
        )
        rb["oracle_ftn_genie_turbo_ep"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_FTN70, U_AFDM_160, Q_RX_FTN70, LINV_70, c_b_ftn, u_b, 4, False, "oracle_turbo")[1]
        )
        rb["oracle_orth_genie_turbo_ep"].append(
            run_arm_chain(z_u, n0_b, ts, nus, gains, P_DAT_ORTH, U_AFDM_112, Q_RX_ORTH, LINV_ORTH, c_b_orth, u_b, 16, False, "oracle_turbo")[1]
        )

    return out


def _worker_star(args_tup):
    return run_scene(*args_tup)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-scenes", type=int, default=80)
    ap.add_argument("--out", type=str, default=str(ROOT / "ideas" / "r15" / "out_g3_afdm_ftn.json"))
    args = ap.parse_args()

    t0 = time.time()
    n_sc = 4 if args.smoke else args.n_scenes
    snrs_db = [2.0, 4.5, 7.0, 9.5, 12.0, 14.5]
    print(f"[td_g_g3] python={sys.executable} smoke={args.smoke} scenes={n_sc} workers={args.workers}", flush=True)

    chk = verify_ftn_gram_and_bw99()
    assert chk["flat_whitening_gram_rel_err"] < 1e-4, chk
    print("[Sanity FTN Gram & BW99]", chk, flush=True)

    tasks = [(i, snrs_db) for i in range(n_sc)]
    w_cnt = max(1, min(args.workers, 8))
    if w_cnt == 1:
        res = [_worker_star(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            res = list(ex.map(_worker_star, tasks))

    sm_a_fixed = ["sm_a1_ftn_whitened_ep_dd", "sm_a2_orth_afdm_fixed_rrc"]
    sm_a_flex = ["sm_a1_ftn_whitened_ep_dd", "sm_a2_orth_afdm_fixed_rrc", "sm_a3_orth_afdm_tight_rrc"]
    sm_s_keys = ["sm_s_scfde_ftn_dd", "sm_s_orth_scfde_dd", "sm_s_orth_otfs_dd", "sm_s_orth_ofdm_dd"]

    reg_summary = {}
    overall_verdict = "KILLED_BY_STEELMAN"
    for rk in ("Regime_A_alpha080", "Regime_B_alpha070"):
        mats = {a: np.array([r[rk][a] for r in res], dtype=float) for a in ARMS_G3}
        bler = {a: [float(x) for x in np.sum(mats[a], axis=0) / n_sc] for a in ARMS_G3}
        # Compare against FTN Oracle AND Joint Best(FTN Oracle, Orth Oracle)
        orc_key = (
            "oracle_ftn_genie_turbo_ep"
            if np.sum(mats["oracle_ftn_genie_turbo_ep"]) <= np.sum(mats["oracle_orth_genie_turbo_ep"])
            else "oracle_orth_genie_turbo_ep"
        )
        gaps_vs_ftn_orc = {
            a: paired_crossing_gap_ci95(mats[a], mats["oracle_ftn_genie_turbo_ep"], 1.0, snrs_db, target=0.05)
            for a in ARMS_G3
        }
        gaps_vs_best_orc = {
            a: paired_crossing_gap_ci95(mats[a], mats[orc_key], 1.0, snrs_db, target=0.05)
            for a in ARMS_G3
        }

        def _best(keys, gd):
            v = [(k, gd[k]["gap_dB"]) for k in keys if gd[k]["gap_dB"] is not None]
            return min(v, key=lambda kv: kv[1]) if v else (None, None)

        ba_fix_n, ba_fix_g = _best(sm_a_fixed, gaps_vs_best_orc)
        ba_flx_n, ba_flx_g = _best(sm_a_flex, gaps_vs_best_orc)
        ball_n, ball_g = _best(sm_a_flex + sm_s_keys, gaps_vs_best_orc)
        snr_orc_c = gaps_vs_best_orc["pub_dai26_unwhitened_lmmse"]["snr_oracle_dB"]
        if ba_fix_g is None and snr_orc_c is not None and min(bler[k][-1] for k in sm_a_fixed) > 0.05:
            ba_fix_g = float(snrs_db[-1] - snr_orc_c)
            ba_fix_n = min(sm_a_fixed, key=lambda k: bler[k][-1]) + "_lower_bound"
        if ba_flx_g is None and snr_orc_c is not None and min(bler[k][-1] for k in sm_a_flex) > 0.05:
            ba_flx_g = float(snrs_db[-1] - snr_orc_c)
            ba_flx_n = min(sm_a_flex, key=lambda k: bler[k][-1]) + "_lower_bound"
        if ball_g is None and snr_orc_c is not None and min(bler[k][-1] for k in sm_a_flex + sm_s_keys) > 0.05:
            ball_g = float(snrs_db[-1] - snr_orc_c)
            ball_n = min(sm_a_flex + sm_s_keys, key=lambda k: bler[k][-1]) + "_lower_bound"

        verd = "KILLED_BY_STEELMAN"
        if ball_g is not None and ball_g >= 1.76:
            verd = "S_CANDIDATE"
            overall_verdict = "S_CANDIDATE"
        elif ba_fix_g is not None and ba_fix_g >= 1.76:
            verd = "A_CANDIDATE_FIXED_ANALOG_RRC"
            if overall_verdict == "KILLED_BY_STEELMAN":
                overall_verdict = verd

        reg_summary[rk] = {
            "BLER_curves": bler,
            "best_oracle_arm": orc_key,
            "BLER_gap_vs_FTN_Oracle_at_5e2_dB": gaps_vs_ftn_orc,
            "BLER_gap_vs_Best_Oracle_at_5e2_dB": gaps_vs_best_orc,
            "summary_headroom": {
                "best_steelman_A_fixed_analog": ba_fix_n,
                "headroom_vs_steelman_A_fixed_dB": ba_fix_g,
                "best_steelman_A_flex_pulse": ba_flx_n,
                "headroom_vs_steelman_A_flex_dB": ba_flx_g,
                "best_steelman_all": ball_n,
                "headroom_vs_best_steelman_all_dB": ball_g,
            },
            "verdict": verd,
        }

    payload = {
        "_config": {
            "problem_id": "G3_AFDM_FTN_vs_Orthogonal",
            "smoke": bool(args.smoke),
            "n_scenes": n_sc,
            "workers": w_cnt,
            "L_os": L_OS,
            "T_frame_T0": T_FRAME_T0,
        },
        "wall_time_s": float(time.time() - t0),
        "gram_and_bw99_check": chk,
        "snrs_EbN0_dB": snrs_db,
        "regimes": reg_summary,
        "teardown_verdict": overall_verdict,
    }
    save_result_json(args.out, payload)
    print(f"[td_g_g3] Done in {payload['wall_time_s']:.1f}s -> verdict={overall_verdict}", flush=True)
    for rk in ("Regime_A_alpha080", "Regime_B_alpha070"):
        print(f"=== {rk} BLER ===", {k: [round(x, 4) for x in v] for k, v in reg_summary[rk]["BLER_curves"].items()}, flush=True)
        print(f"=== {rk} Headroom ===", reg_summary[rk]["summary_headroom"], flush=True)


if __name__ == "__main__":
    main()
