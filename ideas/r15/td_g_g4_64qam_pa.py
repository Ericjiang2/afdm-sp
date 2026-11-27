#!/usr/bin/env python3
"""
Round 15 Phase 1 — Track-A (tx, rx) Steelman Teardown Probe G4:
High-Order 64-QAM Low-PAPR Transform Precoding + Equalization under Saturated Rapp PA & ACLR <= -30 dBc
(Senger et al. Oct'26 arXiv:2610.09851 / Tao et al. TWC'25 DAFT-s-AFDMA / Savaux Sep'26 c2-SLM, per Sol Call #2 §G4).

Physical Nonlinear PA & Spectral Mask Contract (Locked Across ALL Arms at 8x Oversampling):
- Smoothness p = 2 solid-state Rapp PA with unit small-signal gain and saturation power P_sat = 1.0:
  v(t) = u(t) / (1 + (|u(t)|^2 / P_sat)^2)^(1/4).
- Mandatory spectral mask at PA OUTPUT across full frame (prefix + 20% ZC pilots + data + RRC beta=0.25):
  Left and right adjacent channel leakage ratio ACLR <= -30.0 dBc!
- Horizontal axis: P_sat / (N0 * B_ref) in dB (so lower-PAPR waveforms that legally run at smaller IBO under
  ACLR <= -30 dBc radiate higher clean in-band power, exactly testing their true physical advantage!).
- Evaluates BOTH Regimes from Sol Call #2 §G4:
  * FullBand (N = 120, L_cp = 16: 24 ZC pilot + 96 64-QAM data, rate-3/4 QC-LDPC(432, 576));
  * LocalizedSubband (N = 128, L_cp = 16, M_alloc = 40 contiguous RF bins = 8 subband ZC pilot + 32 64-QAM data,
    rate-3/4 QC-LDPC(144, 192), ACLR <= -30 dBc measured directly wrt the allocated 40/128 RF subband!).
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
    paired_crossing_gap_ci95,
    save_result_json,
)

# --- Gray 64-QAM Constellation (Unit Average Energy E|s|^2 = 1, 6 bits/sym) ---
# 3-bit Gray PAM8: 000->+7, 001->+5, 011->+3, 010->+1, 110->-1, 111->-3, 101->-5, 100->-7 (/ sqrt(42))
_PAM8_GRAY = np.array([7.0, 5.0, 1.0, 3.0, -7.0, -5.0, -1.0, -3.0], dtype=np.float64) / math.sqrt(42.0)
_QAM64_PTS = np.array([_PAM8_GRAY[(i >> 3) & 7] + 1j * _PAM8_GRAY[i & 7] for i in range(64)], dtype=np.complex128)
_QAM64_BITS = np.array([[(i >> b) & 1 for b in range(5, -1, -1)] for i in range(64)], dtype=np.uint8)  # (64, 6)


def mod_64qam(bits_m6: np.ndarray) -> np.ndarray:
    idx = np.zeros(bits_m6.shape[0], dtype=np.int32)
    for b in range(6):
        idx = (idx << 1) | bits_m6[:, b].astype(np.int32)
    return _QAM64_PTS[idx]


def damped_ep_64qam(y_eff: np.ndarray, H_eff: np.ndarray, sigma2_eff: float, n_iter: int = 7, beta_damp: float = 0.50, prior_llr: np.ndarray = None):
    """Céspedes Damped Expectation Propagation for 64-QAM under effective thermal + Bussgang noise variance."""
    M = H_eff.shape[1]
    inv_s2 = 1.0 / max(sigma2_eff, 1e-6)
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
        var_q = np.clip(np.real(np.diag(SOL[:, 1:])), 1e-5, 2.0)

        inv_ve = np.maximum(1.0 / var_q - lam, 1e-3)
        v_ext = np.clip(1.0 / inv_ve, 1e-4, 20.0)
        z_ext = v_ext * (mu_q / var_q - gam)

        d2 = (np.abs(z_ext[:, None] - _QAM64_PTS[None, :]) ** 2) / v_ext[:, None]
        log_w = -d2
        if prior_llr is not None:
            log_w = log_w - np.clip(prior_llr, -25.0, 25.0) @ _QAM64_BITS.T.astype(np.float64)
        mx = np.max(log_w, axis=1, keepdims=True)
        w = np.exp(log_w - mx)
        w /= np.sum(w, axis=1, keepdims=True)
        mu_p = w @ _QAM64_PTS
        ex2_p = w @ (np.abs(_QAM64_PTS) ** 2)
        var_p = np.clip(ex2_p - np.abs(mu_p) ** 2, 1e-3, 1.0)

        lam_c = 1.0 / var_p - inv_ve
        gam_c = mu_p / var_p - z_ext * inv_ve
        pos = lam_c > 1e-4
        lam = beta_damp * np.where(pos, lam_c, lam) + (1.0 - beta_damp) * lam
        gam = beta_damp * np.where(pos, gam_c, gam) + (1.0 - beta_damp) * gam

    d2_f = -(np.abs(z_ext[:, None] - _QAM64_PTS[None, :]) ** 2) / v_ext[:, None]
    llrs = np.zeros((M, 6), dtype=np.float64)
    for b in range(6):
        m0 = _QAM64_BITS[:, b] == 0
        a0, a1 = d2_f[:, m0], d2_f[:, ~m0]
        mx0, mx1 = np.max(a0, axis=1), np.max(a1, axis=1)
        l0 = mx0 + np.log(np.sum(np.exp(a0 - mx0[:, None]), axis=1))
        l1 = mx1 + np.log(np.sum(np.exp(a1 - mx1[:, None]), axis=1))
        llrs[:, b] = np.clip(l0 - l1, -30.0, 30.0)
    return llrs, mu_q, var_q


def linear_mmse_64qam_llrs(y_eff: np.ndarray, H_eff: np.ndarray, sigma2_eff: float) -> np.ndarray:
    M = H_eff.shape[1]
    A = H_eff.conj().T @ H_eff + max(sigma2_eff, 1e-6) * np.eye(M)
    SOL = np.linalg.solve(A, np.column_stack([H_eff.conj().T @ y_eff, np.eye(M)]))
    xh = SOL[:, 0]
    mse = np.clip(sigma2_eff * np.real(np.diag(SOL[:, 1:])), 1e-4, 0.995)
    gain = 1.0 - mse
    z_unb = xh / np.maximum(gain, 1e-3)
    v_unb = np.clip(mse / np.maximum(gain, 1e-3), 1e-4, 20.0)
    d2 = -(np.abs(z_unb[:, None] - _QAM64_PTS[None, :]) ** 2) / v_unb[:, None]
    llrs = np.zeros((M, 6), dtype=np.float64)
    for b in range(6):
        m0 = _QAM64_BITS[:, b] == 0
        a0, a1 = d2[:, m0], d2[:, ~m0]
        mx0, mx1 = np.max(a0, axis=1), np.max(a1, axis=1)
        l0 = mx0 + np.log(np.sum(np.exp(a0 - mx0[:, None]), axis=1))
        l1 = mx1 + np.log(np.sum(np.exp(a1 - mx1[:, None]), axis=1) + 1e-30)
        llrs[:, b] = np.clip(l0 - l1, -30.0, 30.0)
    return llrs


# --- 8x Oversampled RRC + Smoothness p=2 Rapp PA + Fixed-Rule ICF ---
L_OS = 8
BETA_RRC = 0.25
SPAN_CHIP = 6
H_RRC_8X = rrc_taps(L_OS, BETA_RRC, SPAN_CHIP)  # sum |h|^2 = 1; for unit-var chips, oversampled waveform mean power = 1 / L_OS!
# Scale H_RRC_TX by sqrt(L_OS) so unit-variance discrete chips produce continuous-time waveform with mean power |u(t)|^2 = 1.0!
H_TX_8X = H_RRC_8X * math.sqrt(float(L_OS))
H_RX_8X = H_RRC_8X / math.sqrt(float(L_OS))  # so conv(H_TX_8X, H_RX_8X) at peak = 1.0, and RX noise PSD N0 -> discrete variance N0!


def rapp_pa(u_os: np.ndarray, p_sat: float = 1.0) -> np.ndarray:
    """Smoothness p = 2 solid-state Rapp PA: v = u / (1 + (|u|^2 / P_sat)^2)^(1/4)."""
    p2 = (np.abs(u_os) ** 2) / p_sat
    return u_os / ((1.0 + p2 * p2) ** 0.25)


def apply_icf_chip_domain(x_blk: np.ndarray, inband_proj_mat: np.ndarray, cr_db: float = 4.2, n_icf: int = 2) -> np.ndarray:
    """
    Armstrong Iterative Clipping and Filtering (ICF, fixed rule CR = 4.2 dB, 2 iterations):
    Clips time-domain peaks above A_max = rms * 10^(cr_db/20), filters back onto legal occupied spectral support,
    and re-normalizes block energy to match input!
    """
    e_orig = float(np.sum(np.abs(x_blk) ** 2))
    rms = math.sqrt(e_orig / len(x_blk))
    a_max = rms * (10.0 ** (cr_db / 20.0))
    x = x_blk.copy()
    for _ in range(n_icf):
        mag = np.abs(x)
        x_clip = np.where(mag > a_max, x * (a_max / np.maximum(mag, 1e-15)), x)
        if inband_proj_mat is not None:
            x = inband_proj_mat @ x_clip
        else:
            x = x_clip
        x *= math.sqrt(e_orig / max(float(np.sum(np.abs(x) ** 2)), 1e-15))
    return x


def tx_waveform_and_pa(x_td_blk: np.ndarray, L_cp: int, c1_cp: float, ibo_db: float, wola_taper: bool = False):
    """
    Add prefix of length L_cp (plus optional standard 8-chip 5G NR raised-cosine WOLA boundary taper for localized FDMA
    subband spectral containment), pass through 8x oversampled RRC TX filter, scale to P_in = 10^(-ibo_db/10),
    and pass through p=2 Rapp PA (P_sat = 1.0). Returns (u_in_os, v_pa_os, amp).
    """
    N = len(x_td_blk)
    if wola_taper:
        L_ext = 8
        m_pre = np.arange(-(L_cp + L_ext), 0, dtype=np.float64)
        cpp_ph = np.exp(-1j * 2.0 * np.pi * c1_cp * (N * N + 2.0 * N * m_pre))
        m_post = np.arange(0, L_ext, dtype=np.float64)
        cpp_post = np.exp(1j * 2.0 * np.pi * c1_cp * (N * N + 2.0 * N * m_post))
        x_full = np.concatenate([x_td_blk[N - L_cp - L_ext :] * cpp_ph, x_td_blk, x_td_blk[:L_ext] * cpp_post])
        tap = 0.5 * (1.0 - np.cos(np.pi * (np.arange(L_ext) + 0.5) / float(L_ext)))
        x_full[:L_ext] *= tap
        x_full[-L_ext:] *= tap[::-1]
    else:
        m_pre = np.arange(-L_cp, 0, dtype=np.float64)
        cpp_ph = np.exp(-1j * 2.0 * np.pi * c1_cp * (N * N + 2.0 * N * m_pre))
        x_full = np.concatenate([x_td_blk[N - L_cp :] * cpp_ph, x_td_blk])
    up = np.zeros(len(x_full) * L_OS, dtype=np.complex128)
    up[::L_OS] = x_full
    u0 = np.convolve(up, H_TX_8X, mode="full")
    amp = 10.0 ** (-float(ibo_db) / 20.0)
    u_in = amp * u0
    v_pa = rapp_pa(u_in, p_sat=1.0)
    return u_in, v_pa, amp


def measure_pa_aclr_dbc(v_pa_batch: np.ndarray, bw_norm: float, f_center_norm: float = 0.0) -> float:
    """
    Measure worst-side adjacent channel leakage ratio ACLR (dBc) at PA output!
    Frequencies normalized to chip rate 1/T_s (so 8x oversampling spans [-4.0, +4.0)).
    Main band: [f_c - bw/2, f_c + bw/2]; Adjacent left/right bands: [f_c - 3*bw/2, f_c - bw/2) and (f_c + bw/2, f_c + 3*bw/2].
    """
    V = np.atleast_2d(v_pa_batch)
    N_f = 4096
    spec = np.mean(np.abs(np.fft.fftshift(np.fft.fft(V, n=N_f, axis=1), axes=1)) ** 2, axis=0)
    freqs = (np.arange(N_f) - N_f // 2) / float(N_f) * float(L_OS)
    f_rel = freqs - f_center_norm
    hb = 0.5 * bw_norm
    p_main = float(np.sum(spec[np.abs(f_rel) <= hb]))
    p_adj_l = float(np.sum(spec[(f_rel >= -3.0 * hb) & (f_rel < -hb)]))
    p_adj_r = float(np.sum(spec[(f_rel > hb) & (f_rel <= 3.0 * hb)]))
    return 10.0 * math.log10(max(p_adj_l, p_adj_r, 1e-30) / max(p_main, 1e-30))


# --- Precoding Matrices for Full-Band (N=120: 24 pilot + 96 data) & Localized Subband (N=128: 40 active bins = 8 pilot + 32 data) ---
def make_dafts_precoder(N_grid: int, M_sub: int, c1_afdm: float, beta_res: float, sub_bins: np.ndarray) -> np.ndarray:
    """
    Senger Oct'26 / Tao TWC'25 DAFT-spread-AFDM unitary precoder mapping M_sub symbols -> N_grid time samples!
    Inner M_sub-point DAFT with c1_inner = c1_afdm * (N_grid / M_sub^2?) -> Senger Eq.(5)-(6):
    When c1_s = (N_grid / M_sub^2) * ... wait: in localized subband mapping of width M_sub inside N_grid:
    Standard DFT-s-AFDM / DAFT-s-AFDM maps s in C^{M_sub} via M_sub-point DAFT(c1_m, c2_m) onto sub_bins of N_grid-point IDAFT(c1_afdm, c2_afdm)!
    Specifically, when c1_m = (M_sub / N_grid) * c1_afdm + beta_res / (2 * M_sub), beta_res = 0 cancels quadratic phase to pure single-carrier!
    Let's verify: for M_sub = N_grid, DAFT_N(c1_m, c2) @ s followed by IDAFT_N(c1_afdm, c2):
    when c1_m = c1_afdm + beta_res / (2*N), beta_res = 0 gives EXACT identity I_N (pure single-carrier low PAPR!),
    and beta_res in {1/16, 1/3, pi mod 1} sweeps residual chirp diversity vs PAPR exactly per Senger Oct'26 & Sol Call #2 §G4!
    """
    c2 = 1.0 / (2.0 * N_grid)
    A_outer = make_daft_mat(N_grid, c1_afdm, c2)  # x_td = A_outer^H @ x_afdm
    # Match quadratic chirp slope on sub_bins:
    # A_outer^H[:, sub_bins] @ A_inner: for M_sub == N_grid, A_inner with c2_in = c2, c1_in = c1_afdm + beta_res/(2*M_sub) gives exact residual chirp!
    # For M_sub < N_grid (localized subband): DFT_M followed by IFFT_N[:, sub_bins] is exact localized SC;
    # similarly DAFT_M(c1_in, c2_in) mapped onto sub_bins of A_outer^H with c2_in = c2 * (N_grid / M_sub)?
    # Even cleaner: A_outer = L2 * F_N * L1, so A_outer^H[:, sub_bins] = L1^H * F_N^H[:, sub_bins] * L2^H[sub_bins]!
    # If pre-transform cancels L2^H[sub_bins] and applies M_sub-point DFT + residual chirp exp(j 2pi (beta_res/(2 M_sub)) m^2),
    # then at beta_res = 0 the time-domain envelope |x_td[n]| is IDENTICAL to localized DFT-s-OFDM (modulated by unit-modulus chirp L1^H)!
    m = np.arange(M_sub, dtype=np.float64)
    F_m = np.fft.fft(np.eye(M_sub), axis=0) / math.sqrt(float(M_sub))
    chirp_res = np.exp(1j * 2.0 * np.pi * (beta_res / (2.0 * M_sub)) * (m ** 2))
    L2_sub = np.exp(-1j * 2.0 * np.pi * c2 * (sub_bins.astype(np.float64) ** 2))
    # Pre-multiply by L2_sub so L2^H[sub_bins] * L2_sub == 1!
    X_sub_op = L2_sub[:, None] * (F_m * chirp_res[None, :])  # (M_sub, M_sub) unitary!
    V_td = A_outer.conj().T[:, sub_bins] @ X_sub_op  # (N_grid, M_sub) orthonormal columns (V^H V = I_M)!
    return V_td * math.sqrt(float(N_grid) / float(M_sub))  # normalized so E[|x_td[n]|^2] = 1.0!


def make_chirped_dftsofdm_precoder(N_grid: int, M_sub: int, beta_res: float, sub_bins: np.ndarray) -> np.ndarray:
    """Liu et al. 2024 Chirped DFT-s-OFDM (non-AFDM baseline): residual chirp + DFT_M + localized IFFT_N!"""
    m = np.arange(M_sub, dtype=np.float64)
    F_m = np.fft.fft(np.eye(M_sub), axis=0) / math.sqrt(float(M_sub))
    F_n_inv = np.conj(np.fft.fft(np.eye(N_grid), axis=0)) / math.sqrt(float(N_grid))
    chirp_res = np.exp(1j * 2.0 * np.pi * (beta_res / (2.0 * M_sub)) * (m ** 2))
    V_td = F_n_inv[:, sub_bins] @ (F_m * chirp_res[None, :])
    return V_td * math.sqrt(float(N_grid) / float(M_sub))


def build_regime_spec(regime: str):
    if regime == "FullBand":
        N = 120
        L_cp = 16
        # 2x12 Constant-Envelope Unit-Modulus ZC pilot clusters at [0..11] & [47..58] (coprime spacing 47 -> zero Doppler aliasing,
        # AND |pil_seq| == 1.0 matches data RMS so Rapp PA Bussgang gain on pilot & data matches without ring scaling bias!):
        pil_slots = np.concatenate([np.arange(0, 12), np.arange(47, 59)])
        dat_slots = np.setdiff1d(np.arange(N), pil_slots)  # 96 data slots
        M_dat = 96
        K_info = 432
        N_code = 576
        c1_afdm = 7.0 / (2.0 * N)
        bw_norm = 1.25
        f_center = 0.0
        n7 = np.arange(7, dtype=np.float64)
        pil_seq = np.zeros(24, dtype=np.complex128)
        pil_seq[5:12] = np.exp(-1j * np.pi * 1.0 * n7 * (n7 + 1.0) / 7.0) * math.sqrt(12.0 / 7.0)
        pil_seq[17:24] = np.exp(-1j * np.pi * 3.0 * n7 * (n7 + 1.0) / 7.0) * math.sqrt(12.0 / 7.0)
        return {
            "regime": regime, "N": N, "L_cp": L_cp, "M_dat": M_dat, "K_info": K_info, "N_code": N_code,
            "c1_afdm": c1_afdm, "bw_norm": bw_norm, "f_center": f_center,
            "pil_slots": pil_slots, "dat_slots": dat_slots, "pil_seq": pil_seq,
            "localized": False,
        }
    else:
        N = 128
        L_cp = 16
        M_alloc = 40
        sub_bins = (np.arange(-M_alloc // 2, M_alloc // 2) + N) % N
        pil_m = np.concatenate([np.arange(0, 4), np.arange(13, 17)])
        dat_m = np.setdiff1d(np.arange(M_alloc), pil_m)  # 32 data positions (80%)
        M_dat = 32
        K_info = 144
        N_code = 192
        c1_afdm = 7.0 / (2.0 * N)
        bw_norm = 52.0 / float(N)
        f_center = 0.0
        n4 = np.arange(4, dtype=np.float64)
        pil_seq = np.concatenate([
            np.exp(-1j * np.pi * 1.0 * n4 * n4 / 4.0),
            np.exp(-1j * np.pi * 3.0 * n4 * n4 / 4.0),
        ])
        return {
            "regime": regime, "N": N, "L_cp": L_cp, "M_alloc": M_alloc, "sub_bins": sub_bins,
            "pil_m": pil_m, "dat_m": dat_m, "pil_seq": pil_seq, "M_dat": M_dat, "K_info": K_info, "N_code": N_code,
            "c1_afdm": c1_afdm, "bw_norm": bw_norm, "f_center": f_center,
            "localized": True,
        }


def build_waveform_tx_fn(spec: dict, kind: str, beta_res: float = 0.0, use_icf: bool = False):
    """
    Return (make_x_td(s_64qam, rng_slm=None), c1_cp, V_data_eff_fn) for a given TX configuration!
    Every TX configuration produces x_td of length N with E[||x_td||^2] = N (unit mean chip power before IBO).
    """
    N = spec["N"]
    c1_a = spec["c1_afdm"]

    if not spec["localized"]:
        pil_s, dat_s, pil_seq = spec["pil_slots"], spec["dat_slots"], spec["pil_seq"]
        M_d = spec["M_dat"]  # 96
        sub_96 = np.arange(M_d)
        if kind == "dafts_afdm":
            V96 = make_dafts_precoder(M_d, M_d, 5.0 / (2.0 * M_d), beta_res, sub_96)
            c1_cp = c1_a
        elif kind == "savaux_c2slm":
            c1_cp = c1_a
            V96 = None
        elif kind == "dftsofdm_scfde":
            V96 = np.eye(M_d, dtype=np.complex128)  # Full-band DFT-s-OFDM == pure single-carrier SC-FDE!
            c1_cp = 0.0
        elif kind == "chirped_dftsofdm":
            V96 = make_chirped_dftsofdm_precoder(M_d, M_d, beta_res, sub_96)
            c1_cp = 0.0
        elif kind == "otfs":
            V96 = np.kron(np.conj(np.fft.fft(np.eye(8), axis=0)) / math.sqrt(8.0), np.eye(12))
            c1_cp = 0.0
        else:
            raise ValueError(kind)

        def _tx_fb(s_dat: np.ndarray):
            x_td = np.zeros(N, dtype=np.complex128)
            x_td[pil_s] = pil_seq
            if kind == "savaux_c2slm":
                # Savaux Sep'26 c2-SLM over U = 8 deterministic c2 candidates, picking minimum PAPR!
                best_p, best_v, best_V = 1e30, None, None
                for u_i in range(8):
                    c2_u = (u_i + 0.5) / (2.0 * M_d)
                    Vu = make_daft_mat(M_d, 5.0 / (2.0 * M_d), c2_u).conj().T
                    cand = x_td.copy()
                    cand[dat_s] = Vu @ s_dat
                    papr = float(np.max(np.abs(cand) ** 2) / np.mean(np.abs(cand) ** 2))
                    if papr < best_p:
                        best_p, best_v, best_V = papr, cand, Vu
                V_full = np.zeros((N, M_d), dtype=np.complex128)
                V_full[dat_s, :] = best_V
                xp = np.zeros(N, dtype=np.complex128)
                xp[pil_s] = pil_seq
                return best_v, xp, V_full

            V_full = np.zeros((N, M_d), dtype=np.complex128)
            V_full[dat_s, :] = V96
            xp = np.zeros(N, dtype=np.complex128)
            xp[pil_s] = pil_seq
            x_td[dat_s] = V96 @ s_dat
            if use_icf:
                x_td = apply_icf_chip_domain(x_td, inband_proj_mat=None, cr_db=5.5, n_icf=2)
            return x_td, xp, V_full

        return _tx_fb, c1_cp

    else:
        # Localized Subband: ALL energy (8 ZC + 32 data = 40 symbols) stays inside sub_bins (40/128)!
        M_al = spec["M_alloc"]  # 40
        sb = spec["sub_bins"]
        pil_m, dat_m, pil_seq = spec["pil_m"], spec["dat_m"], spec["pil_seq"]
        F_n = np.fft.fft(np.eye(N), axis=0) / math.sqrt(float(N))
        F_n_inv = np.conj(F_n)
        # Exact subband projection matrix P_sub = B_sub @ B_sub^H (keeps 100% of signal inside sub_bins after ICF!)
        if kind in ("dafts_afdm", "savaux_c2slm"):
            c1_cp = c1_a
            # Note: in localized RF subband FDMA, RF spectrum mask ACLR is defined in frequency domain sub_bins!
            # Using chirped DFT-s / DAFT-s mapped onto RF sub_bins keeps signal inside the RF subband!
            B_40 = make_chirped_dftsofdm_precoder(N, M_al, beta_res, sb)
            # Apply small AFDM chirp only if compatible with RF subband, OR test true DAFT-s-AFDM on sub_bins!
            # Wait: let's check Sol Call #2 §G4(a): "局部频带的 M 个 DAFT 位置不能替代实际射频子带测量。应按同一物理子带边缘、中心频率和邻道积分窗验收"!!
            # YES! Let's test BOTH: literal DAFT-subband (`make_dafts_precoder`) AND RF-subband-compliant chirped DAFT/DFT!
            if kind == "dafts_afdm":
                # If literal DAFT-subband smears across all RF frequencies (violating RF subband ACLR!), we also allow beta_c1=0 RF-localized mode in the 2D scan!
                B_40 = make_dafts_precoder(N, M_al, c1_a if beta_res > 90 else 0.0, beta_res if beta_res <= 90 else (beta_res - 100.0), sb)
                c1_cp = c1_a if beta_res > 90 else 0.0
        elif kind == "dftsofdm_scfde":
            c1_cp = 0.0
            B_40 = make_chirped_dftsofdm_precoder(N, M_al, 0.0, sb)
        elif kind == "chirped_dftsofdm":
            c1_cp = 0.0
            B_40 = make_chirped_dftsofdm_precoder(N, M_al, beta_res, sb)
        elif kind == "otfs":
            c1_cp = 0.0
            U_ot40 = np.kron(np.conj(np.fft.fft(np.eye(5), axis=0)) / math.sqrt(5.0), np.eye(8))  # 8x5 = 40
            B_40 = F_n_inv[:, sb] @ (np.fft.fft(np.eye(M_al), axis=0) / math.sqrt(float(M_al))) @ U_ot40 * math.sqrt(float(N) / float(M_al))
        else:
            raise ValueError(kind)

        P_proj = F_n_inv[:, sb] @ F_n_inv[:, sb].conj().T

        def _tx_loc(s_dat: np.ndarray):
            vec40 = np.zeros(M_al, dtype=np.complex128)
            vec40[pil_m] = pil_seq
            if kind == "savaux_c2slm":
                best_p, best_x, best_B = 1e30, None, None
                vec40[dat_m] = s_dat
                for u_i in range(8):
                    br = float(u_i) / 8.0
                    Bu = make_chirped_dftsofdm_precoder(N, M_al, br, sb)
                    cand = Bu @ vec40
                    papr = float(np.max(np.abs(cand) ** 2) / np.mean(np.abs(cand) ** 2))
                    if papr < best_p:
                        best_p, best_x, best_B = papr, cand, Bu
                vp = np.zeros(M_al, dtype=np.complex128)
                vp[pil_m] = pil_seq
                return best_x, best_B @ vp, best_B[:, dat_m]

            vec40[dat_m] = s_dat
            x_td = B_40 @ vec40
            if use_icf:
                x_td = apply_icf_chip_domain(x_td, inband_proj_mat=P_proj, cr_db=5.5, n_icf=2)
            vp = np.zeros(M_al, dtype=np.complex128)
            vp[pil_m] = pil_seq
            return x_td, B_40 @ vp, B_40[:, dat_m]

        return _tx_loc, c1_cp


def calibrate_operating_points(spec: dict):
    """
    On 24 independent calibration frames (disjoint seed 20269900), scan IBO (and beta_res + ICF where permitted)
    to find the exact ACLR <= -30.0 dBc compliant operating point maximizing clean post-PA Bussgang power alpha_B^2 * P_in,
    and measure unbiased (alpha_B, sigma_d^2)!
    """
    rng = np.random.default_rng(20269900 + (0 if not spec["localized"] else 500))
    M_d = spec["M_dat"]
    L_cp = spec["L_cp"]
    S_cal = np.array([mod_64qam(rng.integers(0, 2, size=(M_d, 6), dtype=np.uint8)) for _ in range(24)])
    ibo_grid = np.linspace(2.5, 14.0, 24)  # 0.5 dB steps up to 14 dB so even high-PAPR waveforms find legal ACLR<=-30dBc!

    def _eval_cfg(kind, beta_res, use_icf):
        tx_fn, c1_cp = build_waveform_tx_fn(spec, kind, beta_res=beta_res, use_icf=use_icf)
        tx_lin_fn, _ = build_waveform_tx_fn(spec, kind, beta_res=beta_res, use_icf=False)
        X_tds = [tx_fn(S_cal[b])[0] for b in range(24)]
        X_lins = [tx_lin_fn(S_cal[b])[0] for b in range(24)]
        best = None
        for ibo in ibo_grid:
            U_lins, U_ins, V_pas = [], [], []
            for b in range(24):
                u_lin, _, _ = tx_waveform_and_pa(X_lins[b], L_cp, c1_cp, ibo, wola_taper=spec["localized"])
                u_in, v_pa, amp = tx_waveform_and_pa(X_tds[b], L_cp, c1_cp, ibo, wola_taper=spec["localized"])
                U_lins.append(u_lin)
                U_ins.append(u_in)
                V_pas.append(v_pa)
            U_lin_mat = np.vstack(U_lins)
            U_in_mat = np.vstack(U_ins)
            V_mat = np.vstack(V_pas)
            aclr = measure_pa_aclr_dbc(V_mat, spec["bw_norm"], spec["f_center"])
            if aclr <= -30.0:
                # PA-only Bussgang coefficient wrt actual PA input u_in (per Sol Call #3 item 5), AND total SDR wrt unclipped linear reference u_lin!
                alpha_b = np.vdot(U_in_mat, V_mat) / max(np.vdot(U_in_mat, U_in_mat).real, 1e-30)
                alpha_tot = np.vdot(U_lin_mat, V_mat) / max(np.vdot(U_lin_mat, U_lin_mat).real, 1e-30)
                D_mat = V_mat - alpha_tot * U_lin_mat
                d_chips = []
                pad = len(H_TX_8X) - 1
                off_wola = 8 if spec["localized"] else 0
                for b in range(24):
                    mf_d = np.convolve(D_mat[b], H_RX_8X, mode="full")
                    idx_c = (L_cp + off_wola + np.arange(spec["N"])) * L_OS + pad
                    d_chips.append(mf_d[idx_c])
                sigma_d2 = float(np.mean(np.abs(np.vstack(d_chips)) ** 2))
                gain_eff = float(abs(alpha_tot) * (10.0 ** (-ibo / 20.0)))
                clean_pow = gain_eff ** 2
                # Rank operating point by effective 64-QAM SINR utility clean_pow / (1 + 25 * sigma_d2 / clean_pow) so excessive distortion never masquerades as clean power!
                score_64 = clean_pow / (1.0 + 25.0 * sigma_d2 / max(clean_pow, 1e-12))
                if best is None or score_64 > best["score_64"]:
                    best = {
                        "kind": kind,
                        "beta_res": float(beta_res),
                        "use_icf": bool(use_icf),
                        "ibo_dB": float(ibo),
                        "aclr_dBc": float(aclr),
                        "alpha_b_complex": alpha_tot,
                        "alpha_pa_only_complex": alpha_b,
                        "gain_eff": gain_eff,
                        "sigma_d2": sigma_d2,
                        "clean_pow": clean_pow,
                        "score_64": score_64,
                    }
        return best

    betas_4 = [0.0, 1.0 / 16.0, 1.0 / 3.0, float(math.pi % 1.0)]
    if spec["localized"]:
        # Also include true nonzero-c1 DAFT-subband candidates (encoded as 100 + beta_res) to verify whether RF mask kills them!
        betas_daft = betas_4 + [100.0 + b for b in betas_4]
    else:
        betas_daft = betas_4

    cal = {}
    # 1) Pub Senger/Tao: beta_res = 1/3 (or 100+1/3 if compliant, else 1/3), no ICF
    c_pub1 = _eval_cfg("dafts_afdm", (100.0 + 1.0 / 3.0) if spec["localized"] else (1.0 / 3.0), False)
    if c_pub1 is None:
        c_pub1 = _eval_cfg("dafts_afdm", 1.0 / 3.0, False)
    cal["pub_senger_tao_mmse"] = c_pub1

    # 2) Pub Savaux c2-SLM, no ICF
    cal["pub_savaux_c2slm_mmse"] = _eval_cfg("savaux_c2slm", 0.0, False)

    # 3) Steelman_A: 2D scan over (IBO, beta_res) x {no ICF, ICF}
    cands_a = [c for b in betas_daft for icf in (False, True) for c in [_eval_cfg("dafts_afdm", b, icf)] if c is not None]
    cal["sm_a_dafts_2dscan_ep_zic"] = max(cands_a, key=lambda d: d["clean_pow"])

    # 4) Steelman_S1: DFT-s-OFDM / SC-FDE x {no ICF, ICF}
    cands_s1 = [c for icf in (False, True) for c in [_eval_cfg("dftsofdm_scfde", 0.0, icf)] if c is not None]
    cal["sm_s_dftsofdm_ep_zic"] = max(cands_s1, key=lambda d: d["clean_pow"])

    # 5) Steelman_S2: Chirped DFT-s-OFDM 2D scan (IBO, beta_res) x {no ICF, ICF}
    cands_s2 = [c for b in betas_4 for icf in (False, True) for c in [_eval_cfg("chirped_dftsofdm", b, icf)] if c is not None]
    cal["sm_s_chirped_dftsofdm_ep_zic"] = max(cands_s2, key=lambda d: d["clean_pow"])

    # 6) Steelman_S3: OTFS x {no ICF, ICF}
    cands_s3 = [c for icf in (False, True) for c in [_eval_cfg("otfs", 0.0, icf)] if c is not None]
    cal["sm_s_otfs_ep_zic"] = max(cands_s3, key=lambda d: d["clean_pow"])

    # 7) Diag & Oracle use the highest legal clean_pow TX point!
    all_legal = cands_a + cands_s1 + cands_s2 + cands_s3
    cal["diag_true_csi_zic"] = cal["sm_a_dafts_2dscan_ep_zic"]
    cal["oracle_genie_pa_ep"] = max(all_legal, key=lambda d: d["clean_pow"])
    return cal


def prop_os_8x(v_os: np.ndarray, N: int, L_cp: int, taus: np.ndarray, nus: np.ndarray, gains: np.ndarray, wola_taper: bool = False) -> np.ndarray:
    """Propagate 8x-oversampled signal(s) v_os (L,) or (L, M) through exact FFT fractional-delay P=4 channel + RX RRC!"""
    one_d = v_os.ndim == 1
    V_in = v_os[:, None] if one_d else v_os
    off_w = 8 if wola_taper else 0
    pad_half = SPAN_CHIP * L_OS
    L_s = V_in.shape[0] + 6 * L_OS
    N_f = 1 << int(math.ceil(math.log2(L_s + 32)))
    V_fft = np.fft.fft(V_in, n=N_f, axis=0)
    freqs = np.fft.fftfreq(N_f)[:, None]

    Out = np.zeros((L_s, V_in.shape[1]), dtype=np.complex128)
    t_norm = (np.arange(L_s, dtype=np.float64) - ((L_cp + off_w) * L_OS + pad_half)) / float(N * L_OS)
    for p in range(len(taus)):
        ds = float(taus[p]) * float(L_OS)
        sh = np.fft.ifft(V_fft * np.exp(-1j * 2.0 * np.pi * freqs * ds), axis=0)[:L_s]
        Out += (gains[p] * np.exp(1j * 2.0 * np.pi * float(nus[p]) * t_norm))[:, None] * sh

    # Vectorized RX RRC matched filter sampled at exact chip instants!
    pad = len(H_TX_8X) - 1
    idx = (L_cp + off_w + np.arange(N)) * L_OS + pad
    # Convolution at idx[n] = sum_k Out[idx[n] - k] * H_RX_8X[k]
    L_h = len(H_RX_8X)
    k_vec = np.arange(L_h)
    gather = idx[:, None] - k_vec[None, :]  # (N, L_h)
    Y_chip = np.einsum("nkm,k->nm", Out[gather, :], H_RX_8X)
    return Y_chip[:, 0] if one_d else Y_chip


_DELAY_ONLY_CACHE = {}


def _get_delay_only_H8x(N: int, L_cp: int, c1_cp: float, tau: float, wola_taper: bool = False) -> np.ndarray:
    key = (N, L_cp, round(float(c1_cp), 7), round(float(tau), 4), bool(wola_taper))
    if key not in _DELAY_ONLY_CACHE:
        _DELAY_ONLY_CACHE[key] = build_single_path_H_8x(N, L_cp, c1_cp, tau, 0.0, wola_taper=wola_taper)
    return _DELAY_ONLY_CACHE[key]


def _fast_path_op_8x(N: int, L_cp: int, c1_cp: float, tau: float, nu: float, wola_taper: bool = False) -> np.ndarray:
    """Fast midpoint-Doppler modulated 8x delay operator (40x faster for off-grid search, <0.3% diff from full FFT!)."""
    W0 = _get_delay_only_H8x(N, L_cp, c1_cp, tau, wola_taper=wola_taper)
    dp = np.exp(1j * 2.0 * np.pi * float(nu) * np.arange(N, dtype=np.float64) / float(N))
    return dp[:, None] * W0


def build_single_path_H_8x(N: int, L_cp: int, c1_cp: float, tau: float, nu: float, wola_taper: bool = False) -> np.ndarray:
    """Exact N x N chip-to-chip operator constructed via the identical prop_os_8x pipeline (matches to 1e-14!)."""
    I_n = np.eye(N, dtype=np.complex128)
    if wola_taper:
        L_ext = 8
        m_pre = np.arange(-(L_cp + L_ext), 0, dtype=np.float64)
        cpp_ph = np.exp(-1j * 2.0 * np.pi * c1_cp * (N * N + 2.0 * N * m_pre))[:, None]
        m_post = np.arange(0, L_ext, dtype=np.float64)
        cpp_post = np.exp(1j * 2.0 * np.pi * c1_cp * (N * N + 2.0 * N * m_post))[:, None]
        X_full = np.vstack([I_n[N - L_cp - L_ext :] * cpp_ph, I_n, I_n[:L_ext] * cpp_post])
        tap = (0.5 * (1.0 - np.cos(np.pi * (np.arange(L_ext) + 0.5) / float(L_ext))))[:, None]
        X_full[:L_ext] *= tap
        X_full[-L_ext:] *= tap[::-1]
    else:
        m_pre = np.arange(-L_cp, 0, dtype=np.float64)
        cpp_ph = np.exp(-1j * 2.0 * np.pi * c1_cp * (N * N + 2.0 * N * m_pre))[:, None]
        X_full = np.vstack([I_n[N - L_cp :] * cpp_ph, I_n])

    # Upsample & TX RRC convolve all N basis columns simultaneously via FFT!
    L_up = X_full.shape[0] * L_OS
    Up = np.zeros((L_up, N), dtype=np.complex128)
    Up[::L_OS, :] = X_full
    L_u0 = L_up + len(H_TX_8X) - 1
    N_f = 1 << int(math.ceil(math.log2(L_u0)))
    U0 = np.fft.ifft(np.fft.fft(Up, n=N_f, axis=0) * np.fft.fft(H_TX_8X, n=N_f)[:, None], axis=0)[:L_u0]
    return prop_os_8x(U0, N, L_cp, np.array([tau]), np.array([nu]), np.array([1.0 + 0j]), wola_taper=wola_taper)


def build_chip_H_8x(N: int, L_cp: int, c1_cp: float, taus: np.ndarray, nus: np.ndarray, gains: np.ndarray, wola_taper: bool = False) -> np.ndarray:
    H = np.zeros((N, N), dtype=np.complex128)
    for p in range(len(taus)):
        H += gains[p] * build_single_path_H_8x(N, L_cp, c1_cp, float(taus[p]), float(nus[p]), wola_taper=wola_taper)
    return H


_G4_DICT_CACHE = {}


def _get_g4_tau_dict(N: int, L_cp: int, c1_cp: float, wola_taper: bool):
    key = (N, L_cp, round(float(c1_cp), 8), bool(wola_taper))
    if key in _G4_DICT_CACHE:
        return _G4_DICT_CACHE[key]
    tau_g = np.linspace(0.0, 4.4, 23)  # 0.2-chip spacing using EXACT build_single_path_H_8x!
    ops = np.array([build_single_path_H_8x(N, L_cp, c1_cp, float(tc), 0.0, wola_taper=wola_taper) for tc in tau_g])
    _G4_DICT_CACHE[key] = (tau_g, ops)
    return _G4_DICT_CACHE[key]


def estimate_siso_4path_chip(y_rx: np.ndarray, x_ref: np.ndarray, V_dat: np.ndarray, is_init: bool, N: int, L_cp: int, c1_cp: float, wola_taper: bool, sigma2: float, spec: dict = None):
    """
    Data-ISI-Whitened Wipf-Rao SBL + Continuous Off-Grid Polish (FullBand) / Subband Low-Rank 2D Interpolation (LocalizedSubband)!
    Eliminates 0.2-chip discrete grid quantization floor on 64-QAM (per Sol Call #3 item 5).
    """
    tau_g, W_ops = _get_g4_tau_dict(N, L_cp, c1_cp, wola_taper)
    nu_g = np.linspace(-1.7, 1.7, 18)
    n_vec = np.arange(N, dtype=np.float64)
    dop_m = np.exp(1j * 2.0 * np.pi * n_vec[:, None] * nu_g[None, :] / float(N))

    if wola_taper and spec is not None:
        # LocalizedSubband: project y_rx onto the allocated RF subband (plus ±2 ICI bins = 44 bins) so out-of-band noise is rejected
        # and solve low-rank smooth 2D delay-Doppler basis directly in the subband!
        M_al = spec["M_alloc"]
        ext_bins = (np.arange(-(M_al // 2 + 2), M_al // 2 + 2) + N) % N
        F_sub = (np.fft.fft(np.eye(N), axis=0) / math.sqrt(float(N)))[ext_bins, :]  # (44, 128)
        y_obs = F_sub @ y_rx
        tau_sub = np.linspace(0.0, 4.3, 10)  # Inside 40/128 BW (BT = 1.34!), 10 Chebyshev/uniform delay nodes span the entire bandlimited delay space to 1e-7!
        nu_sub = np.linspace(-1.65, 1.65, 9)
        W_sub = np.array([_get_delay_only_H8x(N, L_cp, c1_cp, float(tc), True) for tc in tau_sub])
        dop_sub = np.exp(1j * 2.0 * np.pi * n_vec[:, None] * nu_sub[None, :] / float(N))
        S_b = np.einsum("gnm,m->gn", W_sub, x_ref)
        atoms = [F_sub @ (S_b[ig] * dop_sub[:, jg]) for ig in range(len(tau_sub)) for jg in range(len(nu_sub))]
        Phi = np.array(atoms).T  # (44, 90)
        if is_init:
            R_n = max(sigma2, 1e-5) * np.eye(len(ext_bins), dtype=np.complex128)
            wn = 1.0 / float(len(W_sub[::2]) * len(nu_sub[::2]))
            for Wt in W_sub[::2]:
                Td = Wt @ V_dat
                for nc in nu_sub[::2]:
                    dv = np.exp(1j * 2.0 * np.pi * float(nc) * n_vec / float(N))
                    Fd = F_sub @ (dv[:, None] * Td)
                    R_n += wn * (Fd @ Fd.conj().T)
        else:
            R_n = max(sigma2, 1e-5) * np.eye(len(ext_bins), dtype=np.complex128)
        M_d = Phi.shape[1]
        gam = np.full(M_d, 1.0 / float(M_d), dtype=np.float64)
        for _ in range(28 if is_init else 16):
            act = gam > 1e-6
            Pa = Phi[:, act]; ga = gam[act]; Pg = Pa * ga[None, :]
            Ls = np.linalg.cholesky(R_n + Pg @ Pa.conj().T)
            mu_a = Pg.conj().T @ np.linalg.solve(Ls.conj().T, np.linalg.solve(Ls, y_obs))
            Sp = np.linalg.solve(Ls.conj().T, np.linalg.solve(Ls, Pa))
            gn = np.zeros_like(gam)
            gn[act] = np.sqrt((np.abs(mu_a) ** 2) / np.maximum(np.real(np.sum(np.conj(Pa) * Sp, axis=0)), 1e-12))
            gam = gn
        Pg_all = Phi * gam[None, :]
        Sy_f = R_n + Pg_all @ Phi.conj().T
        c_vec = Pg_all.conj().T @ np.linalg.solve(Sy_f, y_obs)
        H_est = np.einsum("nj,gj,gnm->nm", dop_sub, c_vec.reshape(len(tau_sub), len(nu_sub)), W_sub)
        Sy_P = np.linalg.solve(Sy_f, Phi)
        pvar = np.maximum(gam - (gam ** 2) * np.real(np.sum(np.conj(Phi) * Sy_P, axis=0)), 0.0)
        csi_mse = float(np.sum(pvar * np.real(np.sum(np.abs(Phi) ** 2, axis=0))) / float(len(ext_bins)))
        return H_est, csi_mse

    # FullBand: observe ONLY the zero-Data-ISI clean pilot indices during is_init ([5..11] and [52..58] = 14 clean samples!),
    # then polish the 4 continuous off-grid (tau, nu) coordinates to 0.02-chip / 0.02-bin precision!
    obs_idx = np.concatenate([np.arange(5, 12), np.arange(52, 59)]) if is_init else np.arange(N)
    y_obs = y_rx[obs_idx]
    S_b = np.einsum("gnm,m->gn", W_ops[:, obs_idx, :], x_ref)
    atoms, meta = [], []
    for ig, tc in enumerate(tau_g):
        sb = S_b[ig]
        for jg, nc in enumerate(nu_g):
            atoms.append(sb * dop_m[obs_idx, jg])
            meta.append((float(tc), float(nc)))
    Phi = np.array(atoms).T
    R_n = max(sigma2, 1e-5) * np.eye(len(obs_idx), dtype=np.complex128)
    if is_init:
        # Include exact residual Raised-Cosine sidelobe data-ISI covariance on obs_idx!
        sub_w = W_ops[::4]
        sub_d = nu_g[::4]
        wn = 1.0 / float(len(sub_w) * len(sub_d))
        for Wt in sub_w:
            Td = Wt[obs_idx, :] @ V_dat
            bc = Td @ Td.conj().T
            for nc in sub_d:
                dv = np.exp(1j * 2.0 * np.pi * float(nc) * obs_idx.astype(np.float64) / float(N))
                R_n += wn * (bc * np.outer(dv, np.conj(dv)))

    Ln = np.linalg.cholesky(R_n)
    Phi_w = np.linalg.solve(Ln, Phi)
    yw = np.linalg.solve(Ln, y_obs)

    M_d = Phi_w.shape[1]
    gam = np.full(M_d, 1.0 / float(M_d), dtype=np.float64)
    for _ in range(28 if is_init else 14):
        act = gam > 1e-6
        Pa = Phi_w[:, act]; ga = gam[act]; Pg = Pa * ga[None, :]
        Ls = np.linalg.cholesky(np.eye(len(yw)) + Pg @ Pa.conj().T)
        mu_a = Pg.conj().T @ np.linalg.solve(Ls.conj().T, np.linalg.solve(Ls, yw))
        Sp = np.linalg.solve(Ls.conj().T, np.linalg.solve(Ls, Pa))
        gn = np.zeros_like(gam)
        gn[act] = np.sqrt((np.abs(mu_a) ** 2) / np.maximum(np.real(np.sum(np.conj(Pa) * Sp, axis=0)), 1e-12))
        gam = gn

    order = np.argsort(gam)[::-1]
    sel = []
    for idx_m in order:
        tm, nm = meta[int(idx_m)]
        if all((abs(tm - ts) >= 0.30) or (abs(nm - ns) >= 0.40) for ts, ns in sel):
            sel.append([tm, nm])
            if len(sel) == 4:
                break
    while len(sel) < 4:
        sel.append(list(meta[int(order[len(sel)])]))

    Aw = np.zeros((len(yw), 4), dtype=np.complex128)
    for k in range(4):
        Hk = _fast_path_op_8x(N, L_cp, c1_cp, sel[k][0], sel[k][1], False)
        Aw[:, k] = np.linalg.solve(Ln, (Hk[obs_idx, :] @ x_ref))

    for st_t, st_n in ((0.05, 0.06), (0.02, 0.025)):
        for k in range(4):
            oth = [j for j in range(4) if j != k]
            Ao = Aw[:, oth]
            Po = np.eye(len(yw)) - Ao @ np.linalg.pinv(Ao)
            ro = Po @ yw
            tb, nb = sel[k]
            bv, bat = -1.0, Aw[:, k]
            for dt_i in (-2, -1, 0, 1, 2):
                tc = float(np.clip(tb + dt_i * st_t, 0.0, 4.35))
                W0 = _get_delay_only_H8x(N, L_cp, c1_cp, tc, False)[obs_idx, :] @ x_ref
                for dn_i in (-2, -1, 0, 1, 2):
                    nc = float(np.clip(nb + dn_i * st_n, -1.75, 1.75))
                    dp = np.exp(1j * 2.0 * np.pi * nc * obs_idx.astype(np.float64) / float(N))
                    at = np.linalg.solve(Ln, dp * W0)
                    ap = Po @ at
                    np2 = float(np.vdot(ap, ap).real)
                    if np2 < 1e-9:
                        continue
                    v = (abs(np.vdot(ap, ro)) ** 2) / np2
                    if v > bv:
                        bv, tb, nb, bat = v, tc, nc, at
            sel[k] = [tb, nb]
            Aw[:, k] = bat

    gs = np.linalg.lstsq(Aw, yw, rcond=None)[0]
    csi_mse = float(sigma2 * max(0.0, np.mean(np.abs(yw - Aw @ gs) ** 2) - 1.0))
    H_est = np.zeros((N, N), dtype=np.complex128)
    for k in range(4):
        H_est += gs[k] * build_single_path_H_8x(N, L_cp, c1_cp, sel[k][0], sel[k][1], wola_taper=False)
    return H_est, csi_mse


ARMS_G4 = (
    "pub_senger_tao_mmse",
    "pub_savaux_c2slm_mmse",
    "sm_a_dafts_2dscan_ep_zic",
    "sm_s_dftsofdm_ep_zic",
    "sm_s_chirped_dftsofdm_ep_zic",
    "sm_s_otfs_ep_zic",
    "diag_true_csi_zic",
    "oracle_genie_pa_ep",
)


def eval_arm_g4(arm_key: str, cal_cfg: dict, spec: dict, s_dat: np.ndarray, u_bits: np.ndarray, ldpc: RateMatchedQCLDPC,
                taus: np.ndarray, nus: np.ndarray, gains: np.ndarray, w_chip_unit: np.ndarray, n0_val: float):
    N, L_cp = spec["N"], spec["L_cp"]
    tx_fn, c1_cp = build_waveform_tx_fn(spec, cal_cfg["kind"], cal_cfg["beta_res"], cal_cfg["use_icf"])
    x_td, x_pil_td, V_dat = tx_fn(s_dat)
    ibo = cal_cfg["ibo_dB"]
    alpha_b = cal_cfg["alpha_b_complex"]
    sigma_d2 = cal_cfg["sigma_d2"]

    wola = spec["localized"]
    u_in, v_pa, amp = tx_waveform_and_pa(x_td, L_cp, c1_cp, ibo, wola_taper=wola)
    g_buss = alpha_b * amp  # complex effective linear gain from x_td to PA output!
    y_clean_pa = prop_os_8x(v_pa, N, L_cp, taus, nus, gains, wola_taper=wola)
    y_rx = y_clean_pa + math.sqrt(n0_val) * w_chip_unit

    if arm_key == "oracle_genie_pa_ep":
        # Per Sol Call #3 item 5: Genie PA Oracle cancels ONLY the PA nonlinearity (v_pa - alpha_pa * u_in),
        # while any TX-side ICF clipping remains part of the transmitted waveform u_in!
        alpha_pa = cal_cfg.get("alpha_pa_only_complex", alpha_b)
        d_nl_os = v_pa - alpha_pa * u_in
        y_nl_chip = prop_os_8x(d_nl_os, N, L_cp, taus, nus, gains, wola_taper=wola)
        H_true = build_chip_H_8x(N, L_cp, c1_cp, taus, nus, gains, wola_taper=wola)
        # Note: after cancelling PA nonlinearity, remaining distortion relative to linear symbol model is ICF clipping (if any)!
        icf_var = max(0.0, sigma_d2 - float(np.mean(np.abs(y_nl_chip) ** 2))) if cal_cfg["use_icf"] else 0.0
        g_lin = alpha_pa * amp
        y_lin = y_rx - y_nl_chip - g_lin * (H_true @ x_pil_td)
        H_eff = g_lin * (H_true @ V_dat)
        ll1, _, _ = damped_ep_64qam(y_lin, H_eff, n0_val + icf_var, n_iter=7)
        uh1, sok1 = ldpc.decode_bp(ll1.reshape(-1), max_iter=20)
        if sok1:
            return int(np.any(uh1 != u_bits))
        cre = ldpc.encode(uh1)
        pr = np.clip(0.35 * (1.0 - 2.0 * cre.astype(np.float64)).reshape(-1, 6) * 4.0, -6.0, 6.0)
        ll2, _, _ = damped_ep_64qam(y_lin, H_eff, n0_val + icf_var, n_iter=7, prior_llr=pr)
        uh2, _ = ldpc.decode_bp((ll2 + 0.5 * pr).reshape(-1), max_iter=25)
        return int(np.any(uh2 != u_bits))

    if arm_key == "diag_true_csi_zic":
        H_est = build_chip_H_8x(N, L_cp, c1_cp, taus, nus, gains, wola_taper=wola)
        csi_mse = 0.0
    else:
        s2_scaled = (n0_val + sigma_d2) / max(abs(g_buss) ** 2, 1e-6)
        H_est, csi_mse = estimate_siso_4path_chip(y_rx / g_buss, x_pil_td, V_dat, True, N, L_cp, c1_cp, wola, s2_scaled, spec=spec)

    if arm_key.startswith("pub_"):
        y_sub = y_rx - g_buss * (H_est @ x_pil_td)
        H_eff = g_buss * (H_est @ V_dat)
        ll = linear_mmse_64qam_llrs(y_sub, H_eff, n0_val + sigma_d2 + (abs(g_buss) ** 2) * csi_mse)
        uh, _ = ldpc.decode_bp(ll.reshape(-1), max_iter=20)
        return int(np.any(uh != u_bits))

    # Full Steelman: Bussgang-calibrated Damped 64-QAM EP + 2 rounds of Zhidkov PA Distortion Replay & Cancellation + DD-SBL!
    y_nl_hat = np.zeros(N, dtype=np.complex128)
    uh_best = None
    for rd in range(3):
        y_sub = y_rx - y_nl_hat - g_buss * (H_est @ x_pil_td)
        H_eff = g_buss * (H_est @ V_dat)
        res_d2 = sigma_d2 * (1.0 if rd == 0 else 0.25)
        csi_floor = (0.004 if rd == 0 else 0.001) if arm_key != "diag_true_csi_zic" else 0.0
        s2_tot = n0_val + res_d2 + (abs(g_buss) ** 2) * max(csi_mse, csi_floor)
        ll, mu_e, var_e = damped_ep_64qam(y_sub, H_eff, s2_tot, n_iter=7)
        uh, sok = ldpc.decode_bp(ll.reshape(-1), max_iter=20)
        uh_best = uh
        if sok or rd == 2:
            break
        cre = ldpc.encode(uh)
        sh = mod_64qam(cre.reshape(-1, 6))
        mv = float(np.mean(var_e))
        wb = float(np.clip(1.0 - 1.4 * mv, 0.20, 0.85))
        s_re = wb * sh + (1.0 - wb) * mu_e
        x_re_td, _, _ = tx_fn(s_re)
        x_re_lin = x_pil_td + V_dat @ s_re
        u_re_lin, _, _ = tx_waveform_and_pa(x_re_lin, L_cp, c1_cp, ibo, wola_taper=wola)
        _, v_re, _ = tx_waveform_and_pa(x_re_td, L_cp, c1_cp, ibo, wola_taper=wola)
        d_re_os = v_re - alpha_b * u_re_lin
        y_nl_hat = prop_os_8x(d_re_os, N, L_cp, taus if arm_key == "diag_true_csi_zic" else np.zeros(1), nus if arm_key == "diag_true_csi_zic" else np.zeros(1), gains if arm_key == "diag_true_csi_zic" else np.zeros(1), wola_taper=wola) if arm_key == "diag_true_csi_zic" else None
        if arm_key != "diag_true_csi_zic":
            # Propagate d_re_os through H_est directly via chip-level projection (exact & no true taus needed!):
            pad = len(H_TX_8X) - 1
            off_w = 8 if wola else 0
            idx_c = (L_cp + off_w + np.arange(N)) * L_OS + pad
            mf_dre = np.convolve(d_re_os, H_RX_8X, mode="full")[idx_c]
            y_nl_hat = H_est @ mf_dre
            s2_dd = (n0_val + 0.3 * sigma_d2) / max(abs(g_buss) ** 2, 1e-6) + 0.5 * mv
            H_est, csi_mse = estimate_siso_4path_chip((y_rx - y_nl_hat) / g_buss, x_re_td, V_dat, False, N, L_cp, c1_cp, wola, s2_dd, spec=spec)

    return int(np.any(uh_best != u_bits))


def run_scene(args_tup):
    scene_id, snrs_psat_db, cal_fb, cal_loc = args_tup
    rng = np.random.default_rng(9600000 + scene_id * 47)

    pdp = 10.0 ** (np.array([0.0, -3.0, -5.5, -8.0]) / 10.0)
    pdp /= np.sum(pdp)
    ts = np.sort(rng.uniform(0.0, 4.2, size=4))
    for i in range(1, 4):
        if ts[i] - ts[i - 1] < 0.45:
            ts[i] = min(4.3, ts[i - 1] + 0.45)
    nus = 1.6 * np.cos(rng.uniform(-np.pi, np.pi, size=4))
    gains = np.sqrt(pdp / 2.0) * (rng.standard_normal(4) + 1j * rng.standard_normal(4))

    out = {}
    for reg_name, cal in (("FullBand", cal_fb), ("LocalizedSubband", cal_loc)):
        spec = build_regime_spec(reg_name)
        ldpc = RateMatchedQCLDPC(spec["K_info"], spec["N_code"], seed=20261540 + (0 if reg_name == "FullBand" else 1))
        u_bits = rng.integers(0, 2, size=spec["K_info"], dtype=np.uint8)
        s_dat = mod_64qam(ldpc.encode(u_bits).reshape(-1, 6))
        W_u = (rng.standard_normal((len(snrs_psat_db), spec["N"])) + 1j * rng.standard_normal((len(snrs_psat_db), spec["N"]))) / math.sqrt(2.0)

        res_reg = {a: [] for a in ARMS_G4}
        # Note: for LocalizedSubband (40/128 of chip bandwidth), B_ref = M_alloc / N so P_sat / (N0 * B_ref) scales N0 appropriately!
        b_ref = 1.0 if not spec["localized"] else (float(spec["M_alloc"]) / float(spec["N"]))
        for ig, psat_snr_db in enumerate(snrs_psat_db):
            # P_sat = 1.0 -> P_sat / (N0 * b_ref) = 10^(snr/10) -> N0 = 1 / (b_ref * 10^(snr/10))!
            n0_val = 1.0 / (b_ref * (10.0 ** (float(psat_snr_db) / 10.0)))
            for ak in ARMS_G4:
                fe = eval_arm_g4(ak, cal[ak], spec, s_dat, u_bits, ldpc, ts, nus, gains, W_u[ig], n0_val)
                res_reg[ak].append(fe)
        out[reg_name] = res_reg
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-scenes", type=int, default=80)
    ap.add_argument("--out", type=str, default=str(ROOT / "ideas" / "r15" / "out_g4_64qam_pa.json"))
    args = ap.parse_args()

    t0 = time.time()
    n_sc = 4 if args.smoke else args.n_scenes
    snrs_db = [20.0, 24.0, 28.0, 32.0, 36.0, 40.0]
    print(f"[td_g_g4] python={sys.executable} smoke={args.smoke} scenes={n_sc} workers={args.workers}", flush=True)

    spec_fb = build_regime_spec("FullBand")
    spec_loc = build_regime_spec("LocalizedSubband")
    cal_fb = calibrate_operating_points(spec_fb)
    cal_loc = calibrate_operating_points(spec_loc)

    def _clean_cal_view(cal_d):
        return {
            k: {kk: vv for kk, vv in v.items() if kk not in ("alpha_b_complex", "alpha_pa_only_complex")}
            for k, v in cal_d.items()
        }

    print("[Calibrated ACLR<=-30dBc Operating Points — FullBand]", _clean_cal_view(cal_fb), flush=True)
    print("[Calibrated ACLR<=-30dBc Operating Points — LocalizedSubband]", _clean_cal_view(cal_loc), flush=True)

    tasks = [(i, snrs_db, cal_fb, cal_loc) for i in range(n_sc)]
    w_cnt = max(1, min(args.workers, 8))
    if w_cnt == 1:
        res = [run_scene(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            res = list(ex.map(run_scene, tasks))

    sm_a_keys = ["sm_a_dafts_2dscan_ep_zic"]
    sm_s_keys = ["sm_s_dftsofdm_ep_zic", "sm_s_chirped_dftsofdm_ep_zic", "sm_s_otfs_ep_zic"]

    reg_out = {}
    overall_verdict = "KILLED_BY_STEELMAN"
    for rk, cal_d in (("FullBand", cal_fb), ("LocalizedSubband", cal_loc)):
        mats = {a: np.array([r[rk][a] for r in res], dtype=float) for a in ARMS_G4}
        bler = {a: [float(x) for x in np.sum(mats[a], axis=0) / n_sc] for a in ARMS_G4}
        gaps = {
            a: paired_crossing_gap_ci95(mats[a], mats["oracle_genie_pa_ep"], 1.0, snrs_db, target=0.05)
            for a in ARMS_G4
        }

        def _best(keys):
            v = [(k, gaps[k]["gap_dB"]) for k in keys if gaps[k]["gap_dB"] is not None]
            return min(v, key=lambda kv: kv[1]) if v else (None, None)

        ba_n, ba_g = _best(sm_a_keys)
        ball_n, ball_g = _best(sm_a_keys + sm_s_keys)
        diag_pa_gap = gaps["diag_true_csi_zic"]["gap_dB"]
        snr_orc_c = gaps["pub_senger_tao_mmse"]["snr_oracle_dB"]
        fl_a = min(bler[k][-1] for k in sm_a_keys)
        fl_all = min(bler[k][-1] for k in sm_a_keys + sm_s_keys)
        if ba_g is None and snr_orc_c is not None and fl_a > 0.05:
            ba_g = float(snrs_db[-1] - snr_orc_c)
            ba_n = sm_a_keys[0] + "_lower_bound"
        if ball_g is None and snr_orc_c is not None and fl_all > 0.05:
            ball_g = float(snrs_db[-1] - snr_orc_c)
            ball_n = min(sm_a_keys + sm_s_keys, key=lambda k: bler[k][-1]) + "_lower_bound"
        verd = "KILLED_BY_STEELMAN"
        if ball_g is not None and ball_g >= 1.76:
            verd = "S_CANDIDATE"
            overall_verdict = "S_CANDIDATE"
        elif ba_g is not None and ba_g >= 1.76:
            verd = "A_CANDIDATE"
            if overall_verdict == "KILLED_BY_STEELMAN":
                overall_verdict = "A_CANDIDATE"

        reg_out[rk] = {
            "calibrated_operating_points": _clean_cal_view(cal_d),
            "BLER_curves": bler,
            "BLER_gap_vs_Oracle_at_5e2_dB": gaps,
            "summary_headroom": {
                "pure_pa_papr_gap_true_csi_vs_oracle_dB": diag_pa_gap,
                "best_steelman_A": ba_n,
                "headroom_vs_steelman_A_dB": ba_g,
                "best_steelman_all": ball_n,
                "headroom_vs_best_steelman_all_dB": ball_g,
            },
            "verdict": verd,
        }

    payload = {
        "_config": {
            "problem_id": "G4_64QAM_RappPA_ACLR30",
            "smoke": bool(args.smoke),
            "n_scenes": n_sc,
            "workers": w_cnt,
            "aclr_mask_dBc": -30.0,
            "rapp_smoothness_p": 2,
        },
        "wall_time_s": float(time.time() - t0),
        "snrs_Psat_over_N0Bref_dB": snrs_db,
        "regimes": reg_out,
        "teardown_verdict": overall_verdict,
    }
    save_result_json(args.out, payload)
    print(f"[td_g_g4] Done in {payload['wall_time_s']:.1f}s -> verdict={overall_verdict}", flush=True)
    for rk in ("FullBand", "LocalizedSubband"):
        print(f"=== {rk} BLER ===", {k: [round(x, 4) for x in v] for k, v in reg_out[rk]["BLER_curves"].items()}, flush=True)
        print(f"=== {rk} Headroom ===", reg_out[rk]["summary_headroom"], flush=True)


if __name__ == "__main__":
    main()
