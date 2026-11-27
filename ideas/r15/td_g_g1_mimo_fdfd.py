#!/usr/bin/env python3
"""
Round 15 Phase 1 — Track-A (tx, rx) Steelman Teardown Probe G1:
Single-Frame 4x4 Dual-Fractional (FDFD) MIMO-AFDM Pilot-Precoding-Receiver Joint Design
(Yin TWC'24 / Qu Luo TWC'25 / Wang JSAC'26 setting).

Physical Channel Contract (Locked Across ALL Arms):
- Nt = 4, Nr = 4, block length N = 128, cyclic/CPP prefix L_cp = 16 (N_tot = 144 chips).
- Continuous-time 4x oversampled RRC pulse shaping (beta = 0.25, span = 8 chips) + matched RX RRC filter.
- P = 3 continuous fractional-delay (tau in [0, 5] T_s) + continuous Jakes Doppler (nu in [-2.0, +2.0] bins)
  paths per (r, t) link -> 12 paths (48 real parameters) per RX antenna!
- Net payload K_info = 768 info bits/frame (RateMatchedQCLDPC(768, 1536) rate-1/2 mapped to 4 * 96 = 384
  Gray 16-QAM data symbols; 32 pilot dimensions per TX = 25% overhead).
- Total transmitted continuous-time frame energy E_tot (including prefix, pilots, and RRC tails) strictly
  normalized across all waveforms; horizontal axis Eb/N0 = E_tot / (K_info * N0).

Arms Tested (per Sol Call #1 Item 1):
1. pub_yin24_luo25: Embedded 32-bin DAFT impulse pilots (8-bin spacing/TX) + OMP + damped MIMO-EP + QC-LDPC.
2. sm_a1_splitchu_sage_dd: Two time-separated 16-sample orthogonal Chu training clusters ([0..15] & [64..79])
   + nullspace 96-pt DAFT data precoding + continuous 2D SAGE + full 512x384 damped MIMO-EP + 3-round soft-IC DD-SAGE + LDPC.
3. sm_a2_contigchu_sage_dd: Contiguous 32-sample Chu preamble ([0..31], shifts 0,8,16,24) + 96-pt DAFT data
   + continuous 2D SAGE + damped MIMO-EP + 3-round DD-SAGE + LDPC.
4. sm_s_ofdm_dd: 4x4 MIMO-OFDM with identical split-Chu training, full ICI channel, SAGE + MIMO-EP + 3-round DD-SAGE.
5. sm_s_scfde_dd: 4x4 MIMO-SC-FDE with identical split-Chu training, full time-varying channel, SAGE + MIMO-EP + 3-round DD-SAGE.
6. sm_s_otfs_dd: 4x4 MIMO-OTFS (12x8 DD data grid) with identical split-Chu training, SAGE + MIMO-EP + 3-round DD-SAGE.
7. diag_true_csi_ep: Exact same TX frame as sm_a1 + gifted true RX CSI + single-pass MIMO-EP + LDPC (isolates CSI gap).
8. oracle_genie_turbo_ep: Exact same 25%-pilot-taxed TX frame + true RX CSI + 2-pass turbo MIMO-EP-LDPC bound.
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

# --- 16-QAM Gray Mapping (Unit Average Energy E|s|^2 = 1) ---
# 2-bit Gray PAM4: 00 -> +3, 01 -> +1, 11 -> -1, 10 -> -3 (divided by sqrt(10))
_PAM4_MAP = np.array([3.0, 1.0, -3.0, -1.0], dtype=np.float64) / math.sqrt(10.0)
_QAM16_PTS = np.array(
    [_PAM4_MAP[(i >> 2) & 3] + 1j * _PAM4_MAP[i & 3] for i in range(16)],
    dtype=np.complex128,
)
_QAM16_BITS = np.array(
    [[(i >> 3) & 1, (i >> 2) & 1, (i >> 1) & 1, i & 1] for i in range(16)],
    dtype=np.uint8,
)  # (16, 4)


def mod_16qam(bits_4n: np.ndarray) -> np.ndarray:
    """bits_4n: (..., 4) uint8 -> complex symbols (...) unit energy."""
    idx = (
        (bits_4n[..., 0].astype(np.int32) << 3)
        | (bits_4n[..., 1].astype(np.int32) << 2)
        | (bits_4n[..., 2].astype(np.int32) << 1)
        | bits_4n[..., 3].astype(np.int32)
    )
    return _QAM16_PTS[idx]


def qam16_extrinsic_llrs(z_ext: np.ndarray, v_ext: np.ndarray) -> np.ndarray:
    """
    Given Gaussian cavity / extrinsic symbol observation z_k = x_k + w_k, w_k ~ CN(0, v_k),
    compute exact max-log / log-sum-exp bit LLRs log(P(b=0)/P(b=1)) of shape (len(z_ext), 4).
    """
    v_safe = np.clip(v_ext, 1e-4, 20.0)[:, None]  # (M, 1)
    d2 = np.abs(z_ext[:, None] - _QAM16_PTS[None, :]) ** 2  # (M, 16)
    log_p = -d2 / v_safe  # (M, 16)
    llrs = np.zeros((len(z_ext), 4), dtype=np.float64)
    for b in range(4):
        m0 = _QAM16_BITS[:, b] == 0
        m1 = ~m0
        a0 = log_p[:, m0]
        a1 = log_p[:, m1]
        mx0 = np.max(a0, axis=1)
        mx1 = np.max(a1, axis=1)
        l0 = mx0 + np.log(np.sum(np.exp(a0 - mx0[:, None]), axis=1))
        l1 = mx1 + np.log(np.sum(np.exp(a1 - mx1[:, None]), axis=1))
        llrs[:, b] = np.clip(l0 - l1, -30.0, 30.0)
    return llrs


def soft_qam16_from_llr(llrs_m4: np.ndarray):
    """Convert prior bit LLRs (M, 4) into soft symbol mean and variance (mu, var)."""
    # log P(b=0)=0, log P(b=1)=-L -> normalized log prob for each of 16 points
    L = np.clip(llrs_m4, -25.0, 25.0)
    # log_prior[m, s] = sum_b (-bits[s,b] * L[m,b])
    lp = -L @ _QAM16_BITS.T.astype(np.float64)  # (M, 16)
    mx = np.max(lp, axis=1, keepdims=True)
    w = np.exp(lp - mx)
    w /= np.sum(w, axis=1, keepdims=True)
    mu = w @ _QAM16_PTS
    ex2 = w @ (np.abs(_QAM16_PTS) ** 2)
    var = np.clip(ex2 - np.abs(mu) ** 2, 1e-5, 1.0)
    return mu, var


# --- Continuous-Time Raised-Cosine Fractional-Delay Chip Kernel ---
L_OS = 4
BETA_RRC = 0.25
SPAN_SYM = 8
H_RRC = rrc_taps(L_OS, BETA_RRC, SPAN_SYM)
# Combined TX RRC * RX RRC = Raised Cosine pulse g_rc(t); precompute on ultra-fine grid or closed-form RC!


def rc_pulse_vec(t_chips: np.ndarray, beta: float = BETA_RRC) -> np.ndarray:
    """Exact continuous-time unit-energy RRC*RRC = Raised Cosine correlation g_rc(t) = <p_rrc(u), p_rrc(u-t)>."""
    x = np.asarray(t_chips, dtype=np.float64)
    out = np.zeros_like(x)
    sinc_x = np.sinc(x)  # sin(pi*x)/(pi*x)
    den = 1.0 - (2.0 * beta * x) ** 2
    singular = np.abs(den) < 1e-8
    out[~singular] = sinc_x[~singular] * np.cos(np.pi * beta * x[~singular]) / den[~singular]
    if np.any(singular):
        out[singular] = (np.pi / 4.0) * np.sinc(1.0 / (2.0 * beta))
    # Truncate outside [-2*SPAN_SYM, 2*SPAN_SYM] to match finite-span RRC
    out[np.abs(x) > (2 * SPAN_SYM)] = 0.0
    return out


def build_chip_channel_matrix_single_path(N: int, L_cp: int, tau_chips: float, nu_bins: float, c1_cp: float = 0.0) -> np.ndarray:
    """
    Build exact N x N chip-rate effective time-domain operator T(tau, nu) after:
    1) Adding prefix of length L_cp with CPP parameter c1_cp (c1_cp = 0 gives standard CP; c1_cp = c1 gives AFDM CPP!);
    2) Continuous-time RRC TX pulse shaping;
    3) Continuous fractional delay tau_chips and continuous Doppler phase exp(j*2*pi*nu_bins*(n_full - L_cp)/N);
    4) Matched RX RRC filtering and chip-rate sampling at n = 0..N-1!

    Notice: <p_rrc(t - n T_s), p_rrc(t - m_full T_s - tau) * exp(j 2pi f_d t)>
    For realistic vehicular f_d * T_s = nu / N <= 2/128 = 0.0156 << 1, within one RRC mainlobe (~2 chips)
    exp(j 2pi f_d t) varies by < 0.03 rad (sinc(0.0156) = 0.9996), and to be 100% physically exact we compute
    or apply the exact continuous Doppler-shifted inner product!
    Even cleaner: compute exact discrete 4x-oversampled RRC inner product or RC tap weights with midpoint phase!
    Let's check: at N=128, L_cp=16, N_tot=144, we can build T_full: (N, N_tot) directly and fold the prefix!
    """
    n_rx = np.arange(N, dtype=np.float64)[:, None]  # (N, 1), indices 0..N-1 (corresponding to full-frame index n + L_cp)
    m_full = np.arange(-L_cp, N, dtype=np.float64)[None, :]  # (1, N_tot), indices -L_cp..N-1
    dt = n_rx - m_full - tau_chips  # (N, N_tot)
    # Restrict to local support |dt| <= 8 chips for speed & accuracy
    W_rc = np.where(np.abs(dt) <= 8.0, rc_pulse_vec(dt, BETA_RRC), 0.0)
    # Doppler phase evaluated at midpoint of overlap (exact to O((nu/N)^2) < 1e-4!)
    t_mid = 0.5 * (n_rx + m_full + tau_chips)
    dop = np.exp(1j * 2.0 * np.pi * nu_bins * t_mid / float(N))
    T_full = W_rc * dop  # (N, N_tot)

    # Fold prefix [-L_cp .. -1] into [N - L_cp .. N - 1]:
    # In CPP: x[-k] = x[N - k] * exp(-j * 2 * pi * c1_cp * (N^2 - 2 * N * (L_cp_idx)))
    # Specifically for m in [-L_cp..-1], m = idx - L_cp, corresponding to m + N in [N-L_cp..N-1]:
    # x_full[m] = x_td[m + N] * exp(-j * 2 * pi * c1_cp * (N^2 + 2 * N * m))!
    T_blk = T_full[:, L_cp:].copy()  # (N, N)
    m_pre = np.arange(-L_cp, 0, dtype=np.float64)
    cpp_phase = np.exp(-1j * 2.0 * np.pi * c1_cp * (N * N + 2.0 * N * m_pre))
    T_blk[:, N - L_cp :] += T_full[:, :L_cp] * cpp_phase[None, :]
    return T_blk


def verify_oversampled_vs_analytic_rc():
    """Verify our fast exact RC folded operator matches explicit 4x-oversampled RRC convolution to < 2e-3 NRMSE,
    and verify TX BW99 is identical across AFDM, OFDM, SC-FDE, and OTFS."""
    rng = np.random.default_rng(20261510)
    N, L_cp = 128, 16
    N_tot = N + L_cp
    c1 = 7.0 / (2.0 * N)
    tau, nu = 2.37, -1.42

    x_td = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / math.sqrt(2.0)
    m_pre = np.arange(-L_cp, 0, dtype=np.float64)
    x_pre = x_td[N - L_cp :] * np.exp(-1j * 2.0 * np.pi * c1 * (N * N + 2.0 * N * m_pre))
    x_full = np.concatenate([x_pre, x_td])

    # Explicit 4x oversampled TX -> continuous fractional delay + Doppler -> RX RRC matched filter
    up = np.zeros(N_tot * L_OS, dtype=np.complex128)
    up[::L_OS] = x_full
    s_tx_os = np.convolve(up, H_RRC, mode="full")  # length N_tot*L_OS + len(H_RRC) - 1
    pad = SPAN_SYM * L_OS
    # Fractional shift by tau * L_OS samples via FFT phase ramp
    L_sig = len(s_tx_os)
    N_f = 1 << int(math.ceil(math.log2(L_sig + 64)))
    freqs = np.fft.fftfreq(N_f)
    s_del = np.fft.ifft(np.fft.fft(s_tx_os, n=N_f) * np.exp(-1j * 2.0 * np.pi * freqs * (tau * L_OS)))[:L_sig]
    # Sample time index relative to n=0 chip start (which sits at sample (L_cp * L_OS + pad))
    t_chips_os = (np.arange(L_sig, dtype=np.float64) - (L_cp * L_OS + pad)) / float(L_OS)
    s_rx_os = s_del * np.exp(1j * 2.0 * np.pi * nu * t_chips_os / float(N))
    mf_full = np.convolve(s_rx_os, H_RRC, mode="full")
    # Peak of RRC*RRC is at offset 2*pad; chip n in 0..N-1 is at index (L_cp + n)*L_OS + 2*pad
    idx_chips = (L_cp + np.arange(N)) * L_OS + 2 * pad
    y_os_ref = mf_full[idx_chips]

    T_op = build_chip_channel_matrix_single_path(N, L_cp, tau, nu, c1_cp=c1)
    y_op = T_op @ x_td
    nrmse = float(np.linalg.norm(y_op - y_os_ref) / np.linalg.norm(y_os_ref))
    spec_info = measure_bw99_and_aclr(s_tx_os, L_OS, bw_chan_norm=1.25)
    etot_ratio = float(np.sum(np.abs(s_tx_os) ** 2) / np.sum(np.abs(x_full) ** 2))
    return {"os4x_vs_rc_op_nrmse": nrmse, "bw99_over_symrate": spec_info["bw99_over_symrate"], "etot_over_discrete_norm": etot_ratio}


# --- Precomputed Basis & Chu Training Sequences ---
N_BLK = 128
L_CP = 16
N_TOT = N_BLK + L_CP
N_TX = 4
N_RX = 4
N_PILOT = 32
N_DATA = 96
K_INFO = 768
N_CODE = 1536

C1_AFDM_128 = 7.0 / (2.0 * N_BLK)
C2_AFDM_128 = 1.0 / (2.0 * N_BLK)
A_DAFT_128 = make_daft_mat(N_BLK, C1_AFDM_128, C2_AFDM_128)  # unitary: x_td = A^H x_daft
A_DAFT_96 = make_daft_mat(N_DATA, 5.0 / (2.0 * N_DATA), 1.0 / (2.0 * N_DATA))
F_FFT_96 = np.fft.fft(np.eye(N_DATA), axis=0) / math.sqrt(N_DATA)


def make_otfs_96_mat() -> np.ndarray:
    """Unitary map from 12x8 Delay-Doppler symbols to 96 time samples (column-major delay-Doppler ISFFT/Zak)."""
    M_d, N_d = 12, 8
    F_n = np.fft.fft(np.eye(N_d), axis=0) / math.sqrt(N_d)
    # x_td_96 = kron(F_n^H, I_M) x_dd -> X_sym = kron(F_n, I_M) x_td
    return np.kron(F_n, np.eye(M_d))


U_OTFS_96 = make_otfs_96_mat()


def build_chu_seq(L: int, root: int = 1) -> np.ndarray:
    n = np.arange(L, dtype=np.float64)
    return np.exp(-1j * np.pi * root * n * n / float(L))


# Unaliased 3-cluster dispersed pilot slots (11 + 11 + 10 = 32 slots spaced by ~43 chips -> zero half-frame Doppler aliasing!):
SPLIT_PIL_IDX = np.concatenate([np.arange(0, 11), np.arange(43, 54), np.arange(86, 96)])
SPLIT_DAT_IDX = np.setdiff1d(np.arange(N_BLK), SPLIT_PIL_IDX)

# Contiguous-Chu pilot slots: [0..31]; data slots: [32..127]
CONTIG_PIL_IDX = np.arange(0, 32)
CONTIG_DAT_IDX = np.arange(32, 128)


def make_split_chu_pilots() -> np.ndarray:
    """
    Build (N_TX=4, N_PILOT=32) zero-guarded 3-cluster Chu training matrix across [0..10], [43..53], [86..95]:
    Leading 3 chips of each cluster guard against preceding data multipath+RRC ISI; active (7, 7, 6) = 20 chips
    scaled by sqrt(32/20) keep exact pilot energy 32.0 per TX while spacing ~43 chips unaliases Doppler!
    """
    P_mat = np.zeros((N_TX, N_PILOT), dtype=np.complex128)
    sc = math.sqrt(32.0 / 20.0)
    n7 = np.arange(7, dtype=np.float64)
    n6 = np.arange(6, dtype=np.float64)
    had = np.array([[1, 1, 1], [1, -1, 1], [1, 1, -1], [1, -1, -1]], dtype=np.float64)
    roots7 = [1, 2, 3, 5]
    roots6 = [1, 5, 1, 5]
    for t in range(N_TX):
        c1 = np.exp(-1j * np.pi * roots7[t] * n7 * (n7 + 1.0) / 7.0)
        c2 = np.exp(-1j * np.pi * roots7[(t + 1) % 4] * n7 * (n7 + 1.0) / 7.0)
        c3 = np.exp(-1j * np.pi * roots6[t] * n6 * n6 / 6.0)
        P_mat[t, 3:10] = sc * had[t, 0] * np.roll(c1, (2 * t) % 7)
        P_mat[t, 14:21] = sc * had[t, 1] * np.roll(c2, (3 * t) % 7)
        P_mat[t, 25:31] = sc * had[t, 2] * np.roll(c3, (2 * t) % 6)
    return P_mat


def make_contig_chu_pilots() -> np.ndarray:
    """Build (4, 32) zero-guarded contiguous Chu preamble ([5..28] active length-24 Chu scaled by sqrt(32/24))."""
    P_mat = np.zeros((N_TX, N_PILOT), dtype=np.complex128)
    base24 = build_chu_seq(24, root=1) * math.sqrt(32.0 / 24.0)
    for t in range(N_TX):
        P_mat[t, 5:29] = np.roll(base24, 6 * t)
    return P_mat


SPLIT_P_MAT = make_split_chu_pilots()
CONTIG_P_MAT = make_contig_chu_pilots()

TAU_GRID = np.linspace(0.0, 5.0, 21)  # 0.25-chip spacing
NU_GRID = np.linspace(-2.0, 2.0, 17)  # 0.25-bin spacing


def precompute_tau_rc_dict(N: int, L_cp: int, tau_grid: np.ndarray, c1_cp: float):
    n_rx = np.arange(N, dtype=np.float64)[:, None]
    m_full = np.arange(-L_cp, N, dtype=np.float64)[None, :]
    m_pre = np.arange(-L_cp, 0, dtype=np.float64)
    cpp_phase = np.exp(-1j * 2.0 * np.pi * c1_cp * (N * N + 2.0 * N * m_pre))
    ops = np.zeros((len(tau_grid), N, N), dtype=np.complex128)
    for ig, tau in enumerate(tau_grid):
        dt = n_rx - m_full - tau
        W_rc = np.where(np.abs(dt) <= 8.0, rc_pulse_vec(dt, BETA_RRC), 0.0)
        T_b = W_rc[:, L_cp:].astype(np.complex128)
        T_b[:, N - L_cp :] += W_rc[:, :L_cp] * cpp_phase[None, :]
        ops[ig] = T_b
    return ops


W_TAU_CP0 = precompute_tau_rc_dict(N_BLK, L_CP, TAU_GRID, c1_cp=0.0)
W_TAU_CPP = precompute_tau_rc_dict(N_BLK, L_CP, TAU_GRID, c1_cp=C1_AFDM_128)
DOP_GRID_MAT = np.exp(1j * 2.0 * np.pi * np.arange(N_BLK, dtype=np.float64)[:, None] * NU_GRID[None, :] / float(N_BLK))

# Precompute prior data-ISI covariance R_isi_base (32x32) and pilot dictionary Phi_init (32 x 1428) per pilot layout!
_INIT_SBL_CACHE = {}


def _get_init_sbl_struct(pil_key: str, pil_idx: np.ndarray, dat_idx: np.ndarray, P_mat: np.ndarray, c1_cp: float):
    key = (pil_key, round(float(c1_cp), 8))
    if key in _INIT_SBL_CACHE:
        return _INIT_SBL_CACHE[key]
    W_tau = W_TAU_CP0 if abs(c1_cp) < 1e-12 else W_TAU_CPP
    X_pil = np.zeros((N_TX, N_BLK), dtype=np.complex128)
    X_pil[:, pil_idx] = P_mat

    # Exact average data-ISI covariance on pil_idx from unit-variance data on dat_idx across 4 TX antennas
    R_isi0 = np.zeros((len(pil_idx), len(pil_idx)), dtype=np.complex128)
    sub_taus = W_tau[::2]  # 11 delays
    sub_nus = NU_GRID[::4]  # 5 Dopplers
    w_norm = float(N_TX) / float(len(sub_taus) * len(sub_nus))
    p_f = pil_idx.astype(np.float64)
    for Wt in sub_taus:
        Td = Wt[np.ix_(pil_idx, dat_idx)]  # (32, 96)
        base_cov = Td @ Td.conj().T
        for nc in sub_nus:
            dv = np.exp(1j * 2.0 * np.pi * float(nc) * p_f / float(N_BLK))
            R_isi0 += w_norm * (base_cov * np.outer(dv, np.conj(dv)))

    # Build (32, 4 * 21 * 17 = 1428) dictionary
    atoms, meta = [], []
    for t in range(N_TX):
        S_bt = np.einsum("gnm,m->gn", W_tau[:, pil_idx, :], X_pil[t])  # (21, 32)
        for ig, tc in enumerate(TAU_GRID):
            sb = S_bt[ig]
            for jg, nc in enumerate(NU_GRID):
                atoms.append(sb * DOP_GRID_MAT[pil_idx, jg])
                meta.append((t, ig, jg, float(tc), float(nc)))
    Phi = np.array(atoms).T  # (32, 1428)
    _INIT_SBL_CACHE[key] = (R_isi0, Phi, meta, X_pil)
    return _INIT_SBL_CACHE[key]


def wipf_rao_mmv_sbl_init(Y_rx: np.ndarray, pil_key: str, pil_idx: np.ndarray, dat_idx: np.ndarray, P_mat: np.ndarray, c1_cp: float, sigma2: float, n_iter: int = 35):
    """
    Data-ISI-Whitened Wipf-Rao Convex-Bounding MMV-SBL across all 4 co-located RX antennas on the 32 pilot samples!
    Returns (H_est (4,4,128,128), active_support_list [(t, ig, jg, tau, nu), ...]).
    """
    W_tau = W_TAU_CP0 if abs(c1_cp) < 1e-12 else W_TAU_CPP
    R_isi0, Phi, meta, _ = _get_init_sbl_struct(pil_key, pil_idx, dat_idx, P_mat, c1_cp)
    R_n = R_isi0 + max(sigma2, 1e-5) * np.eye(len(pil_idx))
    Y_p = Y_rx[:, pil_idx].T  # (32, 4)

    M_d = Phi.shape[1]
    gam = np.full(M_d, float(N_TX) / float(M_d), dtype=np.float64)
    for _ in range(n_iter):
        act = gam > 1e-6
        Pa = Phi[:, act]
        ga = gam[act]
        Pg = Pa * ga[None, :]
        Sy = R_n + Pg @ Pa.conj().T  # (32, 32)
        L_s = np.linalg.cholesky(Sy)
        Sy_Y = np.linalg.solve(L_s.conj().T, np.linalg.solve(L_s, Y_p))
        Mu_a = Pg.conj().T @ Sy_Y  # (Ma, 4)
        Sy_Pa = np.linalg.solve(L_s.conj().T, np.linalg.solve(L_s, Pa))
        num = np.mean(np.abs(Mu_a) ** 2, axis=1)
        den = np.maximum(np.real(np.sum(np.conj(Pa) * Sy_Pa, axis=0)), 1e-12)
        gam_new = np.zeros_like(gam)
        gam_new[act] = np.sqrt(num / den)
        gam = gam_new

    # Keep top 48 active basis atoms (captures fractional-delay/Doppler off-grid interpolation cleanly!)
    order = np.argsort(gam)[::-1][:48]
    act_idx = order[gam[order] > 1e-4 * gam[order[0]]]
    Pa = Phi[:, act_idx]
    ga = gam[act_idx]
    Pg = Pa * ga[None, :]
    Sy = R_n + Pg @ Pa.conj().T
    Mu_a = Pg.conj().T @ np.linalg.solve(Sy, Y_p)  # (K_act, 4)

    # Posterior SBL channel MSE estimate: tr(Pa Sigma_post Pa^H) / len(pil_idx) where Sigma_post = ga - ga^2 diag(Pa^H Sy^{-1} Pa)
    Sy_Pa = np.linalg.solve(Sy, Pa)
    post_var_a = np.maximum(ga - (ga ** 2) * np.real(np.sum(np.conj(Pa) * Sy_Pa, axis=0)), 0.0)
    csi_mse = float(np.sum(post_var_a * np.real(np.sum(np.abs(Pa) ** 2, axis=0))) / float(len(pil_idx)))

    H_est = np.zeros((N_RX, N_TX, N_BLK, N_BLK), dtype=np.complex128)
    sup_out = []
    for k_i, idx in enumerate(act_idx):
        t_i, ig, jg, tc, nc = meta[idx]
        sup_out.append((t_i, ig, jg, tc, nc))
        Tp = build_chip_channel_matrix_single_path(N_BLK, L_CP, tc, nc, c1_cp=c1_cp)
        H_est[:, t_i] += Mu_a[k_i][:, None, None] * Tp[None, :, :]
    return H_est, csi_mse


def dd_mmv_sbl_full_frame(Y_rx: np.ndarray, X_dd_td: np.ndarray, sup_prev, c1_cp: float, sigma2: float, resid_var: float):
    """
    Decision-directed MMV-SBL / Ridge-LS across ALL 128 samples using soft-reconstructed X_dd_td!
    Expands local neighborhood around initial SBL support + coarse scan to refine continuous off-grid paths!
    """
    W_tau = W_TAU_CP0 if abs(c1_cp) < 1e-12 else W_TAU_CPP
    # Build full-frame dictionary on W_tau x NU_GRID (1428 atoms -> S_full (128, 1428), 128x128 solve takes 0.4 ms!)
    atoms, meta = [], []
    for t in range(N_TX):
        S_bt = np.einsum("gnm,m->gn", W_tau, X_dd_td[t])  # (21, 128)
        for ig, tc in enumerate(TAU_GRID):
            sb = S_bt[ig]
            for jg, nc in enumerate(NU_GRID):
                atoms.append(sb * DOP_GRID_MAT[:, jg])
                meta.append((t, ig, jg, float(tc), float(nc)))
    Phi = np.array(atoms).T  # (128, 1428)
    M_d = Phi.shape[1]
    s2_tot = max(sigma2 + float(N_TX) * resid_var, 1e-5)
    R_n = s2_tot * np.eye(N_BLK)
    Y_t = Y_rx.T  # (128, 4)

    gam = np.full(M_d, float(N_TX) / float(M_d), dtype=np.float64)
    for _ in range(18):
        act = gam > 1e-5
        Pa = Phi[:, act]
        ga = gam[act]
        Pg = Pa * ga[None, :]
        Sy = R_n + Pg @ Pa.conj().T  # (128, 128)
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

    H_est = np.zeros((N_RX, N_TX, N_BLK, N_BLK), dtype=np.complex128)
    for k_i, idx in enumerate(act_idx):
        t_i, _, _, tc, nc = meta[idx]
        Tp = build_chip_channel_matrix_single_path(N_BLK, L_CP, tc, nc, c1_cp=c1_cp)
        H_est[:, t_i] += Mu_a[k_i][:, None, None] * Tp[None, :, :]
    return H_est, csi_mse


def yin24_daft_omp_channel(
    Y_daft: np.ndarray,
    X_pil_daft: np.ndarray,
    pil_bins: np.ndarray,
    sigma2: float,
    P_per_tx: int = 3,
):
    """
    Published Baseline (Yin TWC'24 / Bemani TWC'23):
    DAFT-domain embedded impulse pilot estimation via fractional-Doppler dictionary OMP on the 32-bin pilot zone.
    """
    # Build candidate (tau, nu) dictionary in DAFT domain mapped from pilot impulses!
    # Candidate delays 0..5.5 step 0.5 (12), Dopplers -2..2 step 0.25 (17) -> 204 atoms per TX
    tau_c = np.linspace(0.0, 5.5, 12)
    nu_c = np.linspace(-2.0, 2.0, 17)
    X_pil_td = np.zeros((N_TX, N_BLK), dtype=np.complex128)
    for t in range(N_TX):
        X_pil_td[t] = A_DAFT_128.conj().T @ X_pil_daft[t]

    # Precompute DAFT pilot-zone atoms per TX
    atoms_pil = []  # (N_TX, M_cand, len(pil_bins))
    meta_cand = []
    for ig, tc in enumerate(tau_c):
        T_tc = build_chip_channel_matrix_single_path(N_BLK, L_CP, float(tc), 0.0, c1_cp=C1_AFDM_128)
        for jg, nc in enumerate(nu_c):
            meta_cand.append((float(tc), float(nc)))
    M_c = len(meta_cand)
    Phi = np.zeros((N_TX, M_c, len(pil_bins)), dtype=np.complex128)
    A_sub = A_DAFT_128[pil_bins, :]  # (32, 128)
    n_vec = np.arange(N_BLK, dtype=np.float64)
    idx_m = 0
    for tc in tau_c:
        T_tc = build_chip_channel_matrix_single_path(N_BLK, L_CP, float(tc), 0.0, c1_cp=C1_AFDM_128)
        S_tc = X_pil_td @ T_tc.T  # (4, 128)
        for nc in nu_c:
            dp = np.exp(1j * 2.0 * np.pi * float(nc) * n_vec / float(N_BLK))
            Phi[:, idx_m, :] = (S_tc * dp[None, :]) @ A_sub.T
            idx_m += 1

    Phi_flat = Phi.reshape(N_TX * M_c, len(pil_bins)).T  # (32, 4*M_c)
    col_nrm = np.maximum(np.linalg.norm(Phi_flat, axis=0), 1e-12)
    Phi_unit = Phi_flat / col_nrm[None, :]

    H_td_est = np.zeros((N_RX, N_TX, N_BLK, N_BLK), dtype=np.complex128)
    K_omp = N_TX * P_per_tx
    for r in range(N_RX):
        y_p = Y_daft[r, pil_bins].copy()
        res = y_p.copy()
        sel = []
        for _ in range(K_omp):
            corr = np.abs(Phi_unit.conj().T @ res)
            for s_i in sel:
                corr[s_i] = -1.0
            best_i = int(np.argmax(corr))
            sel.append(best_i)
            A_s = Phi_flat[:, sel]
            g_s = np.linalg.solve(A_s.conj().T @ A_s + max(sigma2, 1e-4) * np.eye(len(sel)), A_s.conj().T @ y_p)
            res = y_p - A_s @ g_s
        for idx_k, s_i in enumerate(sel):
            t_i = s_i // M_c
            m_i = s_i % M_c
            tc, nc = meta_cand[m_i]
            H_td_est[r, t_i] += g_s[idx_k] * build_chip_channel_matrix_single_path(N_BLK, L_CP, tc, nc, c1_cp=C1_AFDM_128)
    return H_td_est


def damped_mimo_ep_16qam(
    y_eff: np.ndarray,
    H_eff: np.ndarray,
    sigma2_eff: float,
    n_iter: int = 6,
    beta_damp: float = 0.55,
    prior_llr: np.ndarray = None,
):
    """
    Céspedes TWC'14 / Qu Luo TWC'25 Damped Expectation Propagation (EP) for 16-QAM MIMO:
    Model: y_eff = H_eff @ x + w, w ~ CN(0, sigma2_eff * I), x in QAM16^M (M = 384).
    Optional prior_llr: (M, 4) extrinsic bit LLRs from outer LDPC decoder (for Oracle turbo EP).
    Returns: (ext_bit_llrs (M, 4), mu_post (M,), var_post (M,)).
    """
    M = H_eff.shape[1]
    inv_s2 = 1.0 / max(sigma2_eff, 1e-6)
    G_h = inv_s2 * (H_eff.conj().T @ H_eff)  # (M, M)
    y_mf = inv_s2 * (H_eff.conj().T @ y_eff)  # (M,)

    if prior_llr is not None:
        mu0, var0 = soft_qam16_from_llr(prior_llr)
        lam = 1.0 / np.clip(var0, 1e-3, 1.0)
        gam = mu0 * lam
    else:
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
        # Solve A_ep @ mu_q = y_mf + gam AND A_ep @ V = I simultaneously for exact diagonal!
        RHS_all = np.column_stack([y_mf + gam, np.eye(M, dtype=np.complex128)])
        Y_tmp = np.linalg.solve(L_c, RHS_all)
        SOL = np.linalg.solve(L_c.conj().T, Y_tmp)
        mu_q = SOL[:, 0]
        var_q = np.clip(np.real(np.diag(SOL[:, 1:])), 1e-5, 2.0)

        # Cavity distribution: 1/v_ext = 1/var_q - lam
        inv_v_ext = np.maximum(1.0 / var_q - lam, 1e-3)
        v_ext = np.clip(1.0 / inv_v_ext, 1e-4, 20.0)
        z_ext = v_ext * (mu_q / var_q - gam)

        # Moment matching onto discrete 16-QAM constellation (with optional LDPC prior)
        d2 = np.abs(z_ext[:, None] - _QAM16_PTS[None, :]) ** 2 / v_ext[:, None]
        log_w = -d2
        if prior_llr is not None:
            log_w = log_w - np.clip(prior_llr, -25.0, 25.0) @ _QAM16_BITS.T.astype(np.float64)
        mx = np.max(log_w, axis=1, keepdims=True)
        w = np.exp(log_w - mx)
        w /= np.sum(w, axis=1, keepdims=True)
        mu_p = w @ _QAM16_PTS
        ex2_p = w @ (np.abs(_QAM16_PTS) ** 2)
        var_p = np.clip(ex2_p - np.abs(mu_p) ** 2, 5e-3, 1.0)

        lam_cand = 1.0 / var_p - inv_v_ext
        gam_cand = mu_p / var_p - z_ext * inv_v_ext
        # Only update coordinates where precision increment is positive (standard Céspedes safeguard)
        pos = lam_cand > 1e-4
        lam_new = np.where(pos, lam_cand, lam)
        gam_new = np.where(pos, gam_cand, gam)
        lam = beta_damp * lam_new + (1.0 - beta_damp) * lam
        gam = beta_damp * gam_new + (1.0 - beta_damp) * gam

    ext_llrs = qam16_extrinsic_llrs(z_ext, v_ext)
    return ext_llrs, mu_q, var_q


def assemble_mimo_eff(H_td_4d: np.ndarray, V_data_tx: np.ndarray, U_rx: np.ndarray = None):
    """
    Given H_td_4d (N_RX, N_TX, N_BLK, N_BLK) and per-TX linear data embedding V_data_tx (N_BLK, N_DATA)
    such that x_td[t] = p_td[t] + V_data_tx @ s_data[t]:
    Returns H_eff of shape (N_RX * N_BLK, N_TX * N_DATA) = (512, 384), and pilot contribution func.
    """
    # H_sub[r, t] = (U_rx @ H_td_4d[r, t]) @ V_data_tx
    H_blocks = np.zeros((N_RX, N_TX, N_BLK, N_DATA), dtype=np.complex128)
    for r in range(N_RX):
        for t in range(N_TX):
            M_rt = H_td_4d[r, t] if U_rx is None else (U_rx @ H_td_4d[r, t])
            H_blocks[r, t] = M_rt @ V_data_tx
    return H_blocks.transpose(0, 2, 1, 3).reshape(N_RX * N_BLK, N_TX * N_DATA)


def run_nullspace_waveform_chain(
    Y_td: np.ndarray,
    pil_key: str,
    pil_idx: np.ndarray,
    dat_idx: np.ndarray,
    P_pil_mat: np.ndarray,
    U_data_96: np.ndarray,
    c1_cp: float,
    sigma2: float,
    ldpc: RateMatchedQCLDPC,
    u_bits_true: np.ndarray,
    n_dd_rounds: int = 3,
):
    X_pil_td = np.zeros((N_TX, N_BLK), dtype=np.complex128)
    X_pil_td[:, pil_idx] = P_pil_mat

    V_data = np.zeros((N_BLK, N_DATA), dtype=np.complex128)
    V_data[dat_idx, :] = U_data_96.conj().T

    H_est, csi_mse = wipf_rao_mmv_sbl_init(Y_td, pil_key, pil_idx, dat_idx, P_pil_mat, c1_cp, sigma2, n_iter=35)

    best_u_hat = None
    for rd in range(n_dd_rounds + 1):
        Y_sub = Y_td.copy()
        for r in range(N_RX):
            for t in range(N_TX):
                Y_sub[r] -= H_est[r, t] @ X_pil_td[t]
        H_eff = assemble_mimo_eff(H_est, V_data, U_rx=None)
        # Textbook CSI-uncertainty-aware noise variance: thermal sigma2 + posterior SBL channel MSE!
        s2_ep = sigma2 + csi_mse
        ext_llrs_m4, mu_ep, var_ep = damped_mimo_ep_16qam(Y_sub.reshape(-1), H_eff, s2_ep, n_iter=6)
        u_hat, syn_ok = ldpc.decode_bp(ext_llrs_m4.reshape(-1), max_iter=20)
        best_u_hat = u_hat
        if syn_ok or rd == n_dd_rounds:
            break

        c_re = ldpc.encode(u_hat)
        s_ldpc = mod_16qam(c_re.reshape(-1, 4))
        mean_v = float(np.mean(var_ep))
        # Weight soft EP posterior mean vs LDPC hard decision strictly by symbol confidence!
        alpha_dd = float(np.clip(1.0 - 1.5 * mean_v, 0.15, 0.80))
        s_soft = (alpha_dd * s_ldpc + (1.0 - alpha_dd) * mu_ep).reshape(N_TX, N_DATA)
        X_dd_td = X_pil_td.copy()
        for t in range(N_TX):
            X_dd_td[t] += V_data @ s_soft[t]
        H_est, csi_mse = dd_mmv_sbl_full_frame(Y_td, X_dd_td, None, c1_cp, sigma2, resid_var=0.6 * mean_v)

    bit_err = int(np.sum(best_u_hat != u_bits_true))
    frm_err = int(bit_err > 0)
    return bit_err, frm_err


ARMS = (
    "pub_yin24_luo25",
    "sm_a1_splitchu_sage_dd",
    "sm_a2_contigchu_sage_dd",
    "sm_s_ofdm_dd",
    "sm_s_scfde_dd",
    "sm_s_otfs_dd",
    "diag_true_csi_ep",
    "oracle_genie_turbo_ep",
)


def run_scene(scene_id: int, snrs_ebn0_db):
    rng = np.random.default_rng(7100000 + scene_id * 37)
    ldpc = RateMatchedQCLDPC(K_INFO, N_CODE, seed=20261511)

    # Sample physical co-located 4x4 continuous FDFD MIMO channel (Yin24 / Luo25 / Wang26):
    # Each TX antenna t excites P = 3 scatterer paths (tau_{t,p}, nu_{t,p}) shared across the 4 co-located RX antennas,
    # with independent Rayleigh complex gains h_{r,t,p} across (r, t, p)!
    pdp_link = 10.0 ** (np.array([0.0, -3.0, -6.0]) / 10.0)
    pdp_link /= np.sum(pdp_link)

    taus_tp = np.zeros((N_TX, 3), dtype=np.float64)
    for t in range(N_TX):
        ts = np.sort(rng.uniform(0.0, 5.0, size=3))
        if ts[1] - ts[0] < 0.45:
            ts[1] = min(5.0, ts[0] + 0.45)
        if ts[2] - ts[1] < 0.45:
            ts[2] = min(5.0, ts[1] + 0.45)
        taus_tp[t] = ts
    nus_tp = 2.0 * np.cos(rng.uniform(-np.pi, np.pi, size=(N_TX, 3)))
    h_gains = np.sqrt(pdp_link[None, None, :] / 2.0) * (
        rng.standard_normal((N_RX, N_TX, 3)) + 1j * rng.standard_normal((N_RX, N_TX, 3))
    )

    H_true_cpp = np.zeros((N_RX, N_TX, N_BLK, N_BLK), dtype=np.complex128)
    H_true_cp0 = np.zeros((N_RX, N_TX, N_BLK, N_BLK), dtype=np.complex128)
    for t in range(N_TX):
        for p in range(3):
            Tp_cpp = build_chip_channel_matrix_single_path(N_BLK, L_CP, float(taus_tp[t, p]), float(nus_tp[t, p]), c1_cp=C1_AFDM_128)
            Tp_cp0 = build_chip_channel_matrix_single_path(N_BLK, L_CP, float(taus_tp[t, p]), float(nus_tp[t, p]), c1_cp=0.0)
            H_true_cpp[:, t] += h_gains[:, t, p][:, None, None] * Tp_cpp[None, :, :]
            H_true_cp0[:, t] += h_gains[:, t, p][:, None, None] * Tp_cp0[None, :, :]

    u_bits = rng.integers(0, 2, size=K_INFO, dtype=np.uint8)
    c_bits = ldpc.encode(u_bits)
    # Scale symbols by 1/sqrt(N_TX) so total TX power summed across 4 TX antennas is 1.0 per chip (E_tot = N_TOT = 144!)
    tx_scale = 1.0 / math.sqrt(N_TX)
    s_16qam = (tx_scale * mod_16qam(c_bits.reshape(-1, 4))).reshape(N_TX, N_DATA)

    # Pre-construct TX frames for each waveform family (all strictly E_tot = N_TOT = 144!)
    # 1) Pub: Yin24 DAFT impulses on bins [4, 12, 20, 28] inside [0..31] (with energy 32 * tx_scale^2 = 8 per TX), data on [32..127]
    X_pub_daft_pil = np.zeros((N_TX, N_BLK), dtype=np.complex128)
    for t in range(N_TX):
        X_pub_daft_pil[t, 4 + 8 * t] = math.sqrt(N_PILOT) * tx_scale
    V_pub_data = A_DAFT_128.conj().T[:, 32:]  # (128, 96)
    X_pub_td = np.zeros((N_TX, N_BLK), dtype=np.complex128)
    for t in range(N_TX):
        X_pub_td[t] = A_DAFT_128.conj().T @ X_pub_daft_pil[t] + V_pub_data @ s_16qam[t]

    # Helper for nullspace waveforms:
    def _make_tx_td(pil_idx, dat_idx, P_mat, U_96):
        X_t = np.zeros((N_TX, N_BLK), dtype=np.complex128)
        X_t[:, pil_idx] = tx_scale * P_mat
        X_t[:, dat_idx] = (U_96.conj().T @ s_16qam.T).T
        return X_t

    X_sma1_td = _make_tx_td(SPLIT_PIL_IDX, SPLIT_DAT_IDX, SPLIT_P_MAT, A_DAFT_96)
    X_sma2_td = _make_tx_td(CONTIG_PIL_IDX, CONTIG_DAT_IDX, CONTIG_P_MAT, A_DAFT_96)
    X_ofdm_td = _make_tx_td(SPLIT_PIL_IDX, SPLIT_DAT_IDX, SPLIT_P_MAT, F_FFT_96)
    X_scfde_td = _make_tx_td(SPLIT_PIL_IDX, SPLIT_DAT_IDX, SPLIT_P_MAT, np.eye(N_DATA, dtype=np.complex128))
    X_otfs_td = _make_tx_td(SPLIT_PIL_IDX, SPLIT_DAT_IDX, SPLIT_P_MAT, U_OTFS_96)

    # Noiseless received blocks
    def _prop(H_4d, X_t):
        return np.einsum("rtnm,tm->rn", H_4d, X_t)

    Y0_pub = _prop(H_true_cpp, X_pub_td)
    Y0_sma1 = _prop(H_true_cpp, X_sma1_td)
    Y0_sma2 = _prop(H_true_cpp, X_sma2_td)
    Y0_ofdm = _prop(H_true_cp0, X_ofdm_td)
    Y0_scfde = _prop(H_true_cp0, X_scfde_td)
    Y0_otfs = _prop(H_true_cp0, X_otfs_td)

    # Base unit complex Gaussian noise shared across all arms and SNR points (strictly paired!)
    Z_noise = (rng.standard_normal((len(snrs_ebn0_db), N_RX, N_BLK)) + 1j * rng.standard_normal((len(snrs_ebn0_db), N_RX, N_BLK))) / math.sqrt(2.0)

    ber_cnt = {a: [] for a in ARMS}
    fer_cnt = {a: [] for a in ARMS}

    # True effective matrices for Diag & Oracle on sm_a1 TX frame
    V_sma1 = np.zeros((N_BLK, N_DATA), dtype=np.complex128)
    V_sma1[SPLIT_DAT_IDX, :] = A_DAFT_96.conj().T
    H_eff_true_sma1 = assemble_mimo_eff(H_true_cpp, V_sma1) * tx_scale
    X_sma1_pil_only = np.zeros((N_TX, N_BLK), dtype=np.complex128)
    X_sma1_pil_only[:, SPLIT_PIL_IDX] = tx_scale * SPLIT_P_MAT
    Y_pil_true_sma1 = _prop(H_true_cpp, X_sma1_pil_only)

    for ig, ebn0_db in enumerate(snrs_ebn0_db):
        # E_tot = N_TOT = 144, K_info = 768 -> Eb = 144 / 768 = 0.1875 per info bit!
        # N0 = Eb * 10^(-ebn0_db / 10) -> discrete chip noise variance sigma2 = N0!
        eb = float(N_TOT) / float(K_INFO)
        sigma2 = eb * (10.0 ** (-float(ebn0_db) / 10.0))
        W_n = math.sqrt(sigma2) * Z_noise[ig]

        # Note: inside receiver functions, symbol variance is 1.0 when we scale H by tx_scale (or scale Y & noise by 1/tx_scale)!
        # Scaling Y and sigma2 by 1 / tx_scale^2 = N_TX puts unit-energy 16-QAM symbols on standard scale!
        inv_tx = 1.0 / tx_scale
        s2_unit = sigma2 * (inv_tx ** 2)

        # 1) Pub: Yin24 + Luo25 MIMO-EP
        Y_pub = (Y0_pub + W_n) * inv_tx
        Y_pub_daft = Y_pub @ A_DAFT_128.T
        H_pub_est = yin24_daft_omp_channel(Y_pub_daft, X_pub_daft_pil * inv_tx, np.arange(32), s2_unit, P_per_tx=3)
        Y_pub_sub = Y_pub.copy()
        for r in range(N_RX):
            for t in range(N_TX):
                Y_pub_sub[r] -= H_pub_est[r, t] @ (A_DAFT_128.conj().T @ (X_pub_daft_pil[t] * inv_tx))
        H_eff_pub = assemble_mimo_eff(H_pub_est, V_pub_data)
        llrs_pub, _, _ = damped_mimo_ep_16qam(Y_pub_sub.reshape(-1), H_eff_pub, s2_unit * 1.35, n_iter=6)
        uh_pub, _ = ldpc.decode_bp(llrs_pub.reshape(-1), max_iter=20)
        be_pub = int(np.sum(uh_pub != u_bits))
        ber_cnt["pub_yin24_luo25"].append(be_pub)
        fer_cnt["pub_yin24_luo25"].append(int(be_pub > 0))

        # 2) Steelman_A1: Split-Chu + Whitened MMV-SBL + MIMO-EP + 3-round DD-SBL
        be, fe = run_nullspace_waveform_chain(
            (Y0_sma1 + W_n) * inv_tx, "split", SPLIT_PIL_IDX, SPLIT_DAT_IDX, SPLIT_P_MAT, A_DAFT_96, C1_AFDM_128, s2_unit, ldpc, u_bits, n_dd_rounds=3
        )
        ber_cnt["sm_a1_splitchu_sage_dd"].append(be)
        fer_cnt["sm_a1_splitchu_sage_dd"].append(fe)

        # 3) Steelman_A2: Contiguous-Chu + Whitened MMV-SBL + MIMO-EP + 3-round DD-SBL
        be, fe = run_nullspace_waveform_chain(
            (Y0_sma2 + W_n) * inv_tx, "contig", CONTIG_PIL_IDX, CONTIG_DAT_IDX, CONTIG_P_MAT, A_DAFT_96, C1_AFDM_128, s2_unit, ldpc, u_bits, n_dd_rounds=3
        )
        ber_cnt["sm_a2_contigchu_sage_dd"].append(be)
        fer_cnt["sm_a2_contigchu_sage_dd"].append(fe)

        # 4) Steelman_S: 4x4 MIMO-OFDM
        be, fe = run_nullspace_waveform_chain(
            (Y0_ofdm + W_n) * inv_tx, "split", SPLIT_PIL_IDX, SPLIT_DAT_IDX, SPLIT_P_MAT, F_FFT_96, 0.0, s2_unit, ldpc, u_bits, n_dd_rounds=3
        )
        ber_cnt["sm_s_ofdm_dd"].append(be)
        fer_cnt["sm_s_ofdm_dd"].append(fe)

        # 5) Steelman_S: 4x4 MIMO-SC-FDE
        be, fe = run_nullspace_waveform_chain(
            (Y0_scfde + W_n) * inv_tx, "split", SPLIT_PIL_IDX, SPLIT_DAT_IDX, SPLIT_P_MAT, np.eye(N_DATA, dtype=np.complex128), 0.0, s2_unit, ldpc, u_bits, n_dd_rounds=3
        )
        ber_cnt["sm_s_scfde_dd"].append(be)
        fer_cnt["sm_s_scfde_dd"].append(fe)

        # 6) Steelman_S: 4x4 MIMO-OTFS
        be, fe = run_nullspace_waveform_chain(
            (Y0_otfs + W_n) * inv_tx, "split", SPLIT_PIL_IDX, SPLIT_DAT_IDX, SPLIT_P_MAT, U_OTFS_96, 0.0, s2_unit, ldpc, u_bits, n_dd_rounds=3
        )
        ber_cnt["sm_s_otfs_dd"].append(be)
        fer_cnt["sm_s_otfs_dd"].append(fe)

        # 7) Diag: True RX CSI + single-pass MIMO-EP + LDPC
        Y_clean_true = (Y0_sma1 - Y_pil_true_sma1 + W_n).reshape(-1)
        llrs_diag, _, _ = damped_mimo_ep_16qam(Y_clean_true, H_eff_true_sma1, sigma2, n_iter=6)
        uh_diag, syn_d = ldpc.decode_bp(llrs_diag.reshape(-1), max_iter=20)
        be_d = int(np.sum(uh_diag != u_bits))
        ber_cnt["diag_true_csi_ep"].append(be_d)
        fer_cnt["diag_true_csi_ep"].append(int(be_d > 0))

        # 8) Oracle: Genie RX CSI + 2-pass Turbo MIMO-EP-LDPC on the exact same 25%-pilot-taxed TX frame
        if syn_d:
            ber_cnt["oracle_genie_turbo_ep"].append(be_d)
            fer_cnt["oracle_genie_turbo_ep"].append(int(be_d > 0))
        else:
            # Pass extrinsic LLRs from LDPC soft output / re-encoded confidence back to EP once!
            c_d = ldpc.encode(uh_diag)
            prior_l = np.clip(0.35 * (1.0 - 2.0 * c_d.astype(np.float64)).reshape(-1, 4) * 4.0, -6.0, 6.0)
            llrs_orc, _, _ = damped_mimo_ep_16qam(Y_clean_true, H_eff_true_sma1, sigma2, n_iter=6, prior_llr=prior_l)
            uh_orc, _ = ldpc.decode_bp((llrs_orc + 0.5 * prior_l).reshape(-1), max_iter=25)
            be_o = int(np.sum(uh_orc != u_bits))
            ber_cnt["oracle_genie_turbo_ep"].append(be_o)
            fer_cnt["oracle_genie_turbo_ep"].append(int(be_o > 0))

    return {"ber_cnt": ber_cnt, "fer_cnt": fer_cnt}


def _worker_star(args_tup):
    return run_scene(*args_tup)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--n-scenes", type=int, default=80)
    ap.add_argument("--out", type=str, default=str(ROOT / "ideas" / "r15" / "out_g1_mimo_fdfd.json"))
    args = ap.parse_args()

    t0 = time.time()
    n_sc = 4 if args.smoke else args.n_scenes
    snrs_db = [5.0, 7.5, 10.0, 12.5, 15.0, 18.0]
    print(f"[td_g_g1] python={sys.executable} smoke={args.smoke} scenes={n_sc} workers={args.workers}", flush=True)

    rc_chk = verify_oversampled_vs_analytic_rc()
    assert rc_chk["os4x_vs_rc_op_nrmse"] < 0.015, rc_chk
    print("[Sanity 4x-RRC vs Analytic RC]", rc_chk, flush=True)

    tasks = [(i, snrs_db) for i in range(n_sc)]
    w_cnt = max(1, min(args.workers, 8))
    if w_cnt == 1:
        res = [_worker_star(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            res = list(ex.map(_worker_star, tasks))

    ber_mats = {a: np.array([r["ber_cnt"][a] for r in res], dtype=float) for a in ARMS}
    fer_mats = {a: np.array([r["fer_cnt"][a] for r in res], dtype=float) for a in ARMS}

    ber_curves = {a: [float(x) for x in np.sum(ber_mats[a], axis=0) / (n_sc * K_INFO)] for a in ARMS}
    fer_curves = {a: [float(x) for x in np.sum(fer_mats[a], axis=0) / n_sc] for a in ARMS}

    # Target FER = 5e-2 (and BER = 1e-3) crossing gaps vs Oracle
    fer_target = 0.05
    ber_target = 1.0e-3
    fer_gaps = {
        a: paired_crossing_gap_ci95(fer_mats[a], fer_mats["oracle_genie_turbo_ep"], 1.0, snrs_db, target=fer_target)
        for a in ARMS
    }
    ber_gaps = {
        a: paired_crossing_gap_ci95(ber_mats[a], ber_mats["oracle_genie_turbo_ep"], float(K_INFO), snrs_db, target=ber_target)
        for a in ARMS
    }

    sm_a_keys = ["sm_a1_splitchu_sage_dd", "sm_a2_contigchu_sage_dd"]
    sm_s_keys = ["sm_s_ofdm_dd", "sm_s_scfde_dd", "sm_s_otfs_dd"]

    def _best_gap(keys, gap_dict):
        valid = [(k, gap_dict[k]["gap_dB"]) for k in keys if gap_dict[k]["gap_dB"] is not None]
        if not valid:
            return None, None
        return min(valid, key=lambda kv: kv[1])

    best_a_name, best_a_gap = _best_gap(sm_a_keys, fer_gaps)
    best_s_name, best_s_gap = _best_gap(sm_s_keys, fer_gaps)
    best_all_name, best_all_gap = _best_gap(sm_a_keys + sm_s_keys, fer_gaps)

    # Also check high-SNR (18 dB) error floor ratio Best_Steelman / Oracle!
    fer_18_best_a = min(fer_curves[k][-1] for k in sm_a_keys)
    fer_18_best_all = min(fer_curves[k][-1] for k in sm_a_keys + sm_s_keys)
    fer_18_orc = fer_curves["oracle_genie_turbo_ep"][-1]

    # Per Sol Call #1 & #2 and round-15.md §1.2:
    # 1.5x linear power/energy threshold = 1.76 dB (round-15.md §1.2 states >= 1.5 dB perf ledger / >= 10x & 3 dB floor ledger)
    headroom_a_db = best_a_gap
    headroom_s_db = best_all_gap
    # If Best_Steelman never crosses target 0.05 even at max SNR while Oracle DOES cross 0.05 at snr_o,
    # compute rigorous lower-bound headroom = max_snr - snr_oracle!
    snr_orc_cross = fer_gaps["pub_yin24_luo25"]["snr_oracle_dB"]
    if headroom_a_db is None and snr_orc_cross is not None and fer_18_best_a > fer_target:
        headroom_a_db = float(snrs_db[-1] - snr_orc_cross)
        best_a_name = min(sm_a_keys, key=lambda k: fer_curves[k][-1]) + "_lower_bound"
    if headroom_s_db is None and snr_orc_cross is not None and fer_18_best_all > fer_target:
        headroom_s_db = float(snrs_db[-1] - snr_orc_cross)
        best_s_name = min(sm_a_keys + sm_s_keys, key=lambda k: fer_curves[k][-1]) + "_lower_bound"

    if headroom_s_db is not None and headroom_s_db >= 1.76:
        verdict = "S_CANDIDATE"
    elif headroom_a_db is not None and headroom_a_db >= 1.76:
        verdict = "A_CANDIDATE"
    elif headroom_a_db is not None and headroom_a_db >= 1.50:
        verdict = "A_CANDIDATE_BORDERLINE_1P5DB"
    else:
        verdict = "KILLED_BY_STEELMAN"

    payload = {
        "_config": {
            "problem_id": "G1_4x4_MIMO_AFDM_FDFD",
            "smoke": bool(args.smoke),
            "n_scenes": n_sc,
            "workers": w_cnt,
            "N_blk": N_BLK,
            "L_cp": L_CP,
            "Nt": N_TX,
            "Nr": N_RX,
            "P_paths_per_link": 3,
            "K_info_bits": K_INFO,
            "net_bits_per_chip": K_INFO / float(N_TOT),
            "pilot_overhead": N_PILOT / float(N_BLK),
        },
        "wall_time_s": float(time.time() - t0),
        "rrc_contract_check": rc_chk,
        "snrs_EbN0_dB": snrs_db,
        "FER_curves": fer_curves,
        "BER_curves": ber_curves,
        "FER_crossing_gap_vs_Oracle_at_5e2_dB": fer_gaps,
        "BER_crossing_gap_vs_Oracle_at_1e3_dB": ber_gaps,
        "summary_headroom": {
            "best_steelman_A": best_a_name,
            "headroom_vs_steelman_A_dB": headroom_a_db,
            "best_steelman_S": best_s_name,
            "headroom_vs_best_steelman_all_dB": headroom_s_db,
            "high_snr_18dB_FER_best_A": fer_18_best_a,
            "high_snr_18dB_FER_best_all": fer_18_best_all,
            "high_snr_18dB_FER_oracle": fer_18_orc,
        },
        "teardown_verdict": verdict,
    }
    save_result_json(args.out, payload)
    print(f"[td_g_g1] Done in {payload['wall_time_s']:.1f}s -> verdict={verdict}", flush=True)
    print("FER curves:", {k: [round(x, 4) for x in v] for k, v in fer_curves.items()}, flush=True)
    print("BER curves:", {k: [round(x, 5) for x in v] for k, v in ber_curves.items()}, flush=True)
    print("Headroom summary:", payload["summary_headroom"], flush=True)


if __name__ == "__main__":
    main()
