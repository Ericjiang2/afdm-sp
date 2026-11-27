#!/usr/bin/env python3
# Source: adapted from afdm-funnel-k/ideas/r15/td_k_n2_mimo_dd_overhead.py + td_k_p1b_u1_bilinear.py::run_pbigamp
# Reason for copy: cross-worktree diagnostic probe adding 4x8 modular-Golomb pilots, contiguous DAFT guard-zone pilots,
# c1 sweep, and symmetric prior data-leakage covariance whitening without touching frozen runner-k files.
"""
P-k-N2 AFDM-Dedicated Pilot & c1 Sweep Probe (Fast 4-EM Receiver + 64-Step P-BiG-AMP Check):
Tests whether replacing OFDM's uniform step-16 comb (`ORTH_P70`, which causes 0.93 ghost peaks in AFDM at 2Nc1=7)
with AFDM-native pilot layouts (4x8 disjoint modular-Golomb rulers, contiguous 32-bin DAFT guard+pilot zones,
non-uniform 32-bin CDM, c1 sweep, and symmetric Bayes prior data-covariance whitening) flips or closes the
OFDM vs AFDM gap on distributed 4x4 doubly-dispersive MIMO under exact OSR=8 RRC energy & BW99 parity.
"""

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool
import numpy as np
import scipy.linalg as la

N = 128
L_CP = 16
N_TX = N + L_CP
OSR = 8
RRC_BETA = 0.25
RRC_SPAN = 12
HALF_SPAN = RRC_SPAN // 2
P_PATHS = 4
TAU_MAX = 4.0
NU_MAX = 1.5

QPSK = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=np.complex128) / np.sqrt(2.0)

# Baseline uniform 32/128 (step-4) pilot grid & step-16 per-TX orthogonal comb from td_k_n2_mimo_dd_overhead.py
PIL_IDX_COMB = np.arange(0, N, 4, dtype=int)  # 32 bins
DAT_IDX_COMB = np.array([i for i in range(N) if i % 4 != 0], dtype=int)  # 96 data bins
ORTH16_BY_TX = [PIL_IDX_COMB[t::4] for t in range(4)]

# Contiguous 32-bin zone [0..31] (96 data bins [32..127])
PIL_IDX_Z32 = np.arange(0, 32, dtype=int)
DAT_IDX_Z32 = np.arange(32, N, dtype=int)


def rrc_eval(t, beta=RRC_BETA):
    t = np.asarray(t, dtype=np.float64)
    out = np.zeros_like(t)
    mask_in = np.abs(t) <= HALF_SPAN + 1e-9
    if not np.any(mask_in):
        return out
    ti = t[mask_in]
    y = np.zeros_like(ti)
    m0 = np.abs(ti) < 1e-12
    m_sing = np.abs(np.abs(4.0 * beta * ti) - 1.0) < 1e-9
    m_reg = (~m0) & (~m_sing)
    y[m0] = 1.0 + beta * (4.0 / np.pi - 1.0)
    if np.any(m_sing):
        y[m_sing] = (beta / np.sqrt(2.0)) * (
            (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * beta))
            + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * beta))
        )
    if np.any(m_reg):
        tr = ti[m_reg]
        num = np.sin(np.pi * tr * (1.0 - beta)) + 4.0 * beta * tr * np.cos(np.pi * tr * (1.0 + beta))
        den = np.pi * tr * (1.0 - (4.0 * beta * tr) ** 2)
        y[m_reg] = num / den
    out[mask_in] = y
    return out


_U_OSR = np.arange(-HALF_SPAN * OSR, HALF_SPAN * OSR + 1, dtype=np.float64) / float(OSR)
_g_test = rrc_eval(_U_OSR)
RRC_NORM = np.sqrt(np.sum(_g_test ** 2) / float(OSR))
H_RRC_TAPS = _g_test / RRC_NORM
_K_VEC = np.arange(N, dtype=np.int32)
_K_FLT = np.arange(N, dtype=np.float64)


def _path_taps(tau, nu):
    w_u = (H_RRC_TAPS * np.exp(2j * np.pi * nu * _U_OSR / float(N))) / float(OSR)
    d_min = int(np.floor(tau)) - 2 * HALF_SPAN
    d_max = int(np.ceil(tau)) + 2 * HALF_SPAN
    d_vals = np.arange(d_min, d_max + 1, dtype=np.int32)
    taps = (rrc_eval(d_vals[:, None] + _U_OSR[None, :] - tau) / RRC_NORM) @ w_u
    return d_vals, taps


def build_cp_wrap(c1):
    W = np.zeros((N_TX, N), dtype=np.complex128)
    for idx, n_val in enumerate(range(-L_CP, N)):
        if n_val >= 0:
            W[idx, n_val] = 1.0
        else:
            src = n_val + N
            W[idx, src] = np.exp(-2j * np.pi * c1 * (N * N + 2 * N * n_val)) if c1 != 0.0 else 1.0
    return W


def build_daft(n_len, c1, c2):
    n = np.arange(n_len, dtype=np.float64)
    F = np.exp(-2j * np.pi * np.outer(n, n) / float(n_len)) / np.sqrt(float(n_len))
    if c1 == 0.0 and c2 == 0.0:
        return F
    L1 = np.exp(-2j * np.pi * c1 * (n ** 2))
    L2 = np.exp(-2j * np.pi * c2 * (n ** 2))
    return (L2[:, None] * F) * L1[None, :]


C2_AF = 1.0 / (2.0 * np.pi * N)
C1_VALS = {k_num: float(k_num) / (2.0 * N) for k_num in (0, 3, 4, 5, 7, 9, 11)}
W_CACHE = {c1: build_cp_wrap(c1) for c1 in C1_VALS.values()}
F_MAT = build_daft(N, 0.0, 0.0)
I_MAT = np.eye(N, dtype=np.complex128)
DAFT_CACHE = {k_num: build_daft(N, C1_VALS[k_num], C2_AF) for k_num in (3, 4, 5, 7, 9, 11)}


def build_path_td_matrix(tau, nu, c1_wrap):
    d_vals, taps = _path_taps(tau, nu)
    H_ext = np.zeros((N, N_TX), dtype=np.complex128)
    for di, d in enumerate(d_vals):
        val = taps[di]
        if abs(val) < 1e-10:
            continue
        cols = _K_VEC - d + L_CP
        m = (cols >= 0) & (cols < N_TX)
        if np.any(m):
            H_ext[_K_VEC[m], cols[m]] = val
    ph_k = np.exp(2j * np.pi * nu * _K_FLT / float(N))
    return (ph_k[:, None] * H_ext) @ W_CACHE[c1_wrap]


def eval_path_on_sig(s_ext, tau, nu):
    d_vals, taps = _path_taps(tau, nu)
    out = np.zeros(N, dtype=np.complex128)
    for di, d in enumerate(d_vals):
        val = taps[di]
        if abs(val) < 1e-10:
            continue
        cols = _K_VEC - d + L_CP
        m = (cols >= 0) & (cols < N_TX)
        if np.any(m):
            out[_K_VEC[m]] += val * s_ext[cols[m]]
    return out * np.exp(2j * np.pi * nu * _K_FLT / float(N))


def build_link_td(paths, c1_wrap):
    H = np.zeros((N, N), dtype=np.complex128)
    for h, tau, nu in paths:
        H += h * build_path_td_matrix(tau, nu, c1_wrap)
    return H


def design_disjoint_modular_golomb_4x8(seed=20261126):
    """
    Constructs 4 pairwise-disjoint 8-element subsets G_0..G_3 in Z_128 (total 32 pilot bins, 96 data bins)
    such that EVERY G_t is a modular Golomb ruler (all 56 nonzero cyclic differences mod 128 distinct,
    reducing integer-shift cyclic autocorrelation from 8/8 = 1.000 down to <= 1/8 = 0.125), while minimizing
    inter-TX cyclic shift collisions across active DAFT shifts |dm| <= 48.
    """
    rng = np.random.default_rng(seed)
    all_bins = rng.permutation(N)
    groups = [np.sort(all_bins[t * 8 : (t + 1) * 8]).copy() for t in range(4)]
    free_bins = all_bins[32:].copy()
    active_shifts = np.array([d % N for d in range(-48, 49) if d != 0], dtype=int)

    def _score(grps):
        pen_auto = 0
        vecs = np.zeros((4, N), dtype=np.int32)
        for t in range(4):
            g = grps[t]
            diffs = (g[:, None] - g[None, :]) % N
            cnts = np.bincount(diffs.ravel(), minlength=N)
            cnts[0] = 0
            ex = np.maximum(cnts - 1, 0)
            pen_auto += int(np.sum(ex * ex)) * 1000
            vecs[t, g] = 1
        F_v = np.fft.fft(vecs, axis=1)
        pen_cross = 0
        for t1 in range(4):
            for t2 in range(t1 + 1, 4):
                cc = np.rint(np.real(np.fft.ifft(F_v[t1] * np.conj(F_v[t2])))).astype(int)
                sub = cc[active_shifts]
                ex_c = np.maximum(sub - 1, 0)
                pen_cross += int(np.sum(ex_c * ex_c)) * 10 + int(np.max(sub)) * 25
        return pen_auto + pen_cross

    cur_sc = _score(groups)
    for it in range(5000):
        t = int(rng.integers(0, 4))
        idx_in = int(rng.integers(0, 8))
        if rng.random() < 0.75:
            idx_out = int(rng.integers(0, len(free_bins)))
            old_b, new_b = groups[t][idx_in], free_bins[idx_out]
            groups[t][idx_in] = new_b
            free_bins[idx_out] = old_b
            ns = _score(groups)
            if ns <= cur_sc:
                cur_sc = ns
            else:
                groups[t][idx_in] = old_b
                free_bins[idx_out] = new_b
        else:
            t2 = (t + int(rng.integers(1, 4))) % 4
            idx2 = int(rng.integers(0, 8))
            b1, b2 = groups[t][idx_in], groups[t2][idx2]
            groups[t][idx_in], groups[t2][idx2] = b2, b1
            ns = _score(groups)
            if ns <= cur_sc:
                cur_sc = ns
            else:
                groups[t][idx_in], groups[t2][idx2] = b1, b2

    groups = [np.sort(g) for g in groups]
    used = set(np.concatenate(groups).tolist())
    dat_idx = np.array(sorted(set(range(N)) - used), dtype=int)
    assert len(used) == 32 and len(dat_idx) == 96

    # Pick unit-modulus phases minimizing 2D (tau, nu) off-peak coherence at 2Nc1=7
    best_xp = None
    best_coh = 1e9
    U7 = DAFT_CACHE[7]
    W7 = W_CACHE[C1_VALS[7]]
    tau_c = np.linspace(0.0, TAU_MAX, 9)
    nu_c = np.linspace(-NU_MAX, NU_MAX, 7)
    for _ in range(24):
        xp = np.zeros((4, N), dtype=np.complex128)
        for t in range(4):
            xp[t, groups[t]] = np.sqrt(4.0) * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, 8))
        atoms = []
        meta = []
        for t in range(4):
            s_t = W7 @ (U7.conj().T @ xp[t])
            for tau in tau_c:
                for nu in nu_c:
                    v = eval_path_on_sig(s_t, float(tau), float(nu))
                    atoms.append(v / max(np.linalg.norm(v), 1e-12))
                    meta.append((t, tau, nu))
        D = np.column_stack(atoms)
        G = np.abs(D.conj().T @ D)
        m_arr = np.array(meta)
        same_tx = m_arr[:, 0:1] == m_arr[:, 0:1].T
        far = (np.abs(m_arr[:, 1:2] - m_arr[:, 1:2].T) >= 0.65) | (np.abs(m_arr[:, 2:3] - m_arr[:, 2:3].T) >= 0.60)
        coh_same = float(np.max(G[same_tx & far]))
        coh_cross = float(np.max(G[~same_tx]))
        sc_p = max(coh_same, coh_cross)
        if sc_p < best_coh:
            best_coh = sc_p
            best_xp = xp
    return groups, dat_idx, best_xp


GOL_GROUPS, DAT_IDX_GOL, X_PIL_GOL8 = design_disjoint_modular_golomb_4x8()
PIL_IDX_GOL32 = np.sort(np.concatenate(GOL_GROUPS))

# Baseline CDM-32 and ORTH-16 from td_k_n2_mimo_dd_overhead.py (exact seed 20261527 for bit-exact reproduction!)
_q32 = np.arange(32, dtype=np.float64)
_rng_cov = np.random.default_rng(20261527)
X_PIL_CDM_COMB = np.zeros((4, N), dtype=np.complex128)
for _ti, _root in enumerate((1.0, 7.0, 13.0, 19.0)):
    cov = np.exp(1j * _rng_cov.uniform(0, 2 * np.pi, 32))
    X_PIL_CDM_COMB[_ti, PIL_IDX_COMB] = np.exp(-1j * np.pi * _root * _q32 * (_q32 + 1.0) / 32.0 + 2j * np.pi * (_ti * 0.25) * _q32) * cov

X_PIL_ORTH16 = np.zeros((4, N), dtype=np.complex128)
for _ti in range(4):
    _q8 = np.arange(8, dtype=np.float64)
    X_PIL_ORTH16[_ti, ORTH16_BY_TX[_ti]] = np.sqrt(4.0) * np.exp(-1j * np.pi * 3.0 * _q8 * (_q8 + 1.0) / 8.0)

# Shared 32-bin Golomb-support CDM (low cross-correlation constant-modulus random/ZC codes on PIL_IDX_GOL32)
_rng_gcdm = np.random.default_rng(2026112602)
X_PIL_CDM_GOL32 = np.zeros((4, N), dtype=np.complex128)
for _ti, _root in enumerate((1.0, 5.0, 11.0, 17.0)):
    cov = np.exp(1j * _rng_gcdm.uniform(0, 2 * np.pi, 32))
    X_PIL_CDM_GOL32[_ti, PIL_IDX_GOL32] = np.exp(-1j * np.pi * _root * _q32 * (_q32 + 1.0) / 32.0) * cov

# Contiguous Zone-32 [0..31]: guard cushions [0..5] & [26..31], 20-bin orthogonal DFT-shifted ZC in [6..25] (energy = 32!)
X_PIL_Z32_CDM20 = np.zeros((4, N), dtype=np.complex128)
_q20 = np.arange(20, dtype=np.float64)
_base_zc20 = np.exp(-1j * np.pi * 3.0 * _q20 * (_q20 + 1.0) / 20.0)
for _ti in range(4):
    X_PIL_Z32_CDM20[_ti, 6:26] = np.sqrt(32.0 / 20.0) * _base_zc20 * np.exp(2j * np.pi * (_ti * 5.0) * _q20 / 20.0)


# Precompute exact expected post-RRC burst energy calibration & BW99 for every (wkey, layout_key, p_split)
LAYOUTS = {
    "orth16": (X_PIL_ORTH16, DAT_IDX_COMB),
    "cdm_comb": (X_PIL_CDM_COMB, DAT_IDX_COMB),
    "gol8": (X_PIL_GOL8, DAT_IDX_GOL),
    "cdm_gol32": (X_PIL_CDM_GOL32, DAT_IDX_GOL),
    "z32_cdm20": (X_PIL_Z32_CDM20, DAT_IDX_Z32),
}

WKEYS = {
    "OFDM": (F_MAT, 0.0),
    "SCFDE": (I_MAT, 0.0),
    "AFDM_c3": (DAFT_CACHE[3], C1_VALS[3]),
    "AFDM_c4": (DAFT_CACHE[4], C1_VALS[4]),
    "AFDM_c5": (DAFT_CACHE[5], C1_VALS[5]),
    "AFDM_c7": (DAFT_CACHE[7], C1_VALS[7]),
    "AFDM_c9": (DAFT_CACHE[9], C1_VALS[9]),
    "AFDM_c11": (DAFT_CACHE[11], C1_VALS[11]),
}


def calibrate_burst_scales():
    rng = np.random.default_rng(20261521)
    p70_p, p70_d = np.sqrt(0.70 * 4.0), np.sqrt(0.30 * 4.0 / 3.0)
    scales = {}
    bw99_map = {}
    raw_e_map = {}
    for wname, (U, c1) in WKEYS.items():
        Uh = U.conj().T
        W = W_CACHE[c1]
        for lname, (xp_arr, di) in LAYOUTS.items():
            e_tx_list = []
            psd = None
            for t in range(4):
                e_acc = 0.0
                for _ in range(60):
                    x = xp_arr[t] * p70_p
                    x[di] = rng.choice(QPSK, len(di)) * p70_d
                    s_ext = W @ (Uh @ x)
                    up = np.zeros(len(s_ext) * OSR, dtype=np.complex128)
                    up[::OSR] = s_ext
                    sig = np.convolve(up, H_RRC_TAPS)
                    e_acc += float(np.sum(np.abs(sig) ** 2) / float(OSR))
                    if t == 0:
                        Nf = 1 << (len(sig) + 64).bit_length()
                        p = np.abs(np.fft.fft(sig, Nf)) ** 2
                        psd = p if psd is None else psd + p
                e_tx_list.append(e_acc / 60.0)
            mean_e = float(np.mean(e_tx_list))
            scales[(wname, lname)] = np.array([np.sqrt(144.0 / e_t) for e_t in e_tx_list], dtype=np.float64)
            raw_e_map[f"{wname}__{lname}"] = mean_e
            freqs = np.abs(np.fft.fftfreq(Nf)) * OSR
            order = np.argsort(freqs)
            cdf = np.cumsum(psd[order]) / np.sum(psd)
            bw99_map[f"{wname}__{lname}"] = float(2.0 * freqs[order][np.searchsorted(cdf, 0.99)])
    return scales, raw_e_map, bw99_map


TX_SCALES, RAW_ETX_MAP, BW99_MAP = calibrate_burst_scales()

_PRIOR_COV_CACHE = {}
_DICT_CACHE = {}
_PBIG_ATOMS_CACHE = {}


def get_prior_data_cov(wname, lname):
    """
    Computes exact zero-genie prior covariance C_dat of unknown 4-TX data spillover at RX antenna:
      C_dat = E_{tau,nu}[ H(tau,nu) U^H P_dat U H(tau,nu)^H ]  (for unit d_amp=1, total 4-TX unit average channel power).
    """
    key = (wname, lname)
    if key not in _PRIOR_COV_CACHE:
        U, c1 = WKEYS[wname]
        _, di = LAYOUTS[lname]
        Uh_dat = U.conj().T[:, di]  # (N, 96)
        taus = np.linspace(0.15, TAU_MAX - 0.15, 13)
        nus = np.linspace(-NU_MAX, NU_MAX, 11)
        C_acc = np.zeros((N, N), dtype=np.complex128)
        cnt = 0
        for tau in taus:
            for nu in nus:
                H_m = build_path_td_matrix(float(tau), float(nu), c1)
                B = H_m @ Uh_dat
                C_acc += B @ B.conj().T
                cnt += 1
        _PRIOR_COV_CACHE[key] = C_acc / float(cnt)
    return _PRIOR_COV_CACHE[key]


def get_whitener(wname, lname, d_amp, s2):
    C_dat = get_prior_data_cov(wname, lname)
    R = (d_amp ** 2) * C_dat + max(float(s2), 1e-4) * np.eye(N, dtype=np.complex128)
    evals, evecs = la.eigh(R)
    inv_sqrt = 1.0 / np.sqrt(np.maximum(evals, 1e-6))
    return (evecs * inv_sqrt[None, :]) @ evecs.conj().T


def get_pilot_dict(wname, lname, calibrated=True):
    key = (wname, lname, bool(calibrated))
    if key not in _DICT_CACHE:
        U, c1 = WKEYS[wname]
        xp_arr, _ = LAYOUTS[lname]
        sc_vec = TX_SCALES[(wname, lname)] if calibrated else np.ones(4, dtype=np.float64)
        s_list = [W_CACHE[c1] @ (U.conj().T @ (xp_arr[t] * sc_vec[t])) for t in range(4)]
        tau_g = np.linspace(0.0, TAU_MAX, 13)
        nu_g = np.linspace(-NU_MAX, NU_MAX, 11)
        atoms, meta = [], []
        for ti in range(4):
            for tau in tau_g:
                for nu in nu_g:
                    atoms.append(eval_path_on_sig(s_list[ti], float(tau), float(nu)))
                    meta.append((ti, float(tau), float(nu)))
        D_raw = np.column_stack(atoms)
        norms = np.maximum(np.linalg.norm(D_raw, axis=0), 1e-12)
        _DICT_CACHE[key] = (D_raw, D_raw / norms[None, :], meta, s_list)
    return _DICT_CACHE[key]


def measure_coherence_summary():
    out = {}
    for wname, lname in (
        ("OFDM", "orth16"),
        ("OFDM", "gol8"),
        ("AFDM_c7", "orth16"),
        ("AFDM_c7", "cdm_comb"),
        ("AFDM_c3", "orth16"),
        ("AFDM_c5", "gol8"),
        ("AFDM_c7", "gol8"),
        ("AFDM_c9", "gol8"),
        ("AFDM_c11", "gol8"),
        ("AFDM_c4", "z32_cdm20"),
        ("AFDM_c5", "z32_cdm20"),
        ("SCFDE", "z32_cdm20"),
    ):
        _, D_norm, meta, _ = get_pilot_dict(wname, lname, calibrated=True)
        G = np.abs(D_norm.conj().T @ D_norm)
        m_arr = np.array(meta)
        same_tx = m_arr[:, 0:1] == m_arr[:, 0:1].T
        far = (np.abs(m_arr[:, 1:2] - m_arr[:, 1:2].T) >= 0.67) | (np.abs(m_arr[:, 2:3] - m_arr[:, 2:3].T) >= 0.60)
        out[f"{wname}__{lname}"] = {
            "mu_same_tx_offpeak": round(float(np.max(G[same_tx & far])), 4),
            "mu_inter_tx_max": round(float(np.max(G[~same_tx])), 4),
        }
    return out


def ep_qpsk_mimo(H, y, s2, n_it=6, beta_damp=0.7):
    K = H.shape[1]
    HtH = H.conj().T @ H
    Hty = H.conj().T @ y
    inv_s2 = 1.0 / max(float(s2), 1e-6)
    gamma = np.zeros(K, dtype=np.complex128)
    lam = np.ones(K, dtype=np.float64)
    mu_p = np.zeros(K, dtype=np.complex128)
    v_p = np.ones(K, dtype=np.float64)
    I_K = np.eye(K, dtype=np.complex128)
    for _ in range(n_it):
        Q_mat = inv_s2 * HtH + np.diag(lam)
        try:
            c_fac = la.cho_factor(Q_mat, lower=True, check_finite=False)
            Sigma = la.cho_solve(c_fac, I_K, check_finite=False)
            mu = Sigma @ (inv_s2 * Hty + gamma)
        except la.LinAlgError:
            Sigma = la.inv(Q_mat + 1e-5 * I_K)
            mu = Sigma @ (inv_s2 * Hty + gamma)
        v_diag = np.maximum(np.real(np.diag(Sigma)), 1e-6)
        h2 = np.maximum(1.0 / v_diag - lam, 1e-6)
        t_mean = (mu / v_diag - gamma) / h2
        v_cav = 1.0 / h2
        d2 = np.abs(t_mean[:, None] - QPSK[None, :]) ** 2
        lw = -d2 / np.maximum(v_cav[:, None], 1e-5)
        lw -= np.max(lw, axis=1, keepdims=True)
        w = np.exp(lw)
        w /= np.sum(w, axis=1, keepdims=True)
        mu_p = w @ QPSK
        v_p = np.maximum(np.sum(w * np.abs(QPSK[None, :] - mu_p[:, None]) ** 2, axis=1), 1e-5)
        lam_new = np.maximum(1.0 / v_p - h2, 1e-6)
        gam_new = mu_p / v_p - t_mean * h2
        upd = lam_new > 1e-5
        lam = np.where(upd, beta_damp * lam_new + (1.0 - beta_damp) * lam, lam)
        gamma = np.where(upd, beta_damp * gam_new + (1.0 - beta_damp) * gamma, gamma)
    xh = QPSK[np.argmin(np.abs(mu_p[:, None] - QPSK[None, :]) ** 2, axis=1)]
    return xh, mu_p, v_p


def joint_tx_omp_and_refine(y_r, s_ext_list, D_raw, D_norm, meta, nt, p_per_link, refine_steps=2, reg=0.0, W_wh=None):
    total_k = nt * p_per_link
    tx_counts = [0] * nt
    if W_wh is not None:
        y_fit = W_wh @ y_r
        D_fit = W_wh @ D_raw
        D_fit_norm = D_fit / np.maximum(np.linalg.norm(D_fit, axis=0), 1e-12)[None, :]
    else:
        y_fit = y_r
        D_fit = D_raw
        D_fit_norm = D_norm

    res = y_fit.copy()
    sel_idx = []
    tx_of_atom = np.array([m[0] for m in meta], dtype=int)
    for _ in range(total_k):
        corrs = np.abs(D_fit_norm.conj().T @ res)
        for idx in sel_idx:
            corrs[idx] = -1.0
        for ti in range(nt):
            if tx_counts[ti] >= p_per_link:
                corrs[tx_of_atom == ti] = -1.0
        best = int(np.argmax(corrs))
        sel_idx.append(best)
        tx_counts[meta[best][0]] += 1
        A_sel = D_fit[:, sel_idx]
        if reg > 0.0:
            G = A_sel.conj().T @ A_sel + reg * np.eye(len(sel_idx))
            h_ls = la.solve(G, A_sel.conj().T @ y_fit, assume_a="pos")
        else:
            h_ls, _, _, _ = la.lstsq(A_sel, y_fit)
        res = y_fit - A_sel @ h_ls

    def _eval_col(ti, tau, nu):
        v = eval_path_on_sig(s_ext_list[ti], tau, nu)
        return W_wh @ v if W_wh is not None else v

    est_params = [[meta[i][0], meta[i][1], meta[i][2]] for i in sel_idx]
    A_cur = np.column_stack([_eval_col(p[0], p[1], p[2]) for p in est_params])
    I_k = np.eye(total_k, dtype=np.complex128)
    reg_ref = reg if W_wh is not None else 0.0

    def _solve_cur(A_m):
        if reg_ref > 0.0:
            hc = la.solve(A_m.conj().T @ A_m + reg_ref * I_k, A_m.conj().T @ y_fit, assume_a="pos")
            return hc, float(np.sum(np.abs(y_fit - A_m @ hc) ** 2) + reg_ref * np.sum(np.abs(hc) ** 2))
        hc, _, _, _ = la.lstsq(A_m, y_fit)
        return hc, float(np.sum(np.abs(y_fit - A_m @ hc) ** 2))

    h_cur, best_err = _solve_cur(A_cur)
    d_tau, d_nu = TAU_MAX / 12.0, (2.0 * NU_MAX) / 10.0
    for sc in range(refine_steps):
        st_tau, st_nu = d_tau * (0.5 ** (sc + 1)), d_nu * (0.5 ** (sc + 1))
        for k in range(total_k):
            ti = est_params[k][0]
            for delta in (-st_tau, st_tau):
                ct = float(np.clip(est_params[k][1] + delta, 0.0, TAU_MAX))
                A_try = A_cur.copy()
                A_try[:, k] = _eval_col(ti, ct, est_params[k][2])
                h_try, err = _solve_cur(A_try)
                if err < best_err:
                    best_err, est_params[k][1], A_cur, h_cur = err, ct, A_try, h_try
            for delta in (-st_nu, st_nu):
                cn = float(np.clip(est_params[k][2] + delta, -NU_MAX * 1.1, NU_MAX * 1.1))
                A_try = A_cur.copy()
                A_try[:, k] = _eval_col(ti, est_params[k][1], cn)
                h_try, err = _solve_cur(A_try)
                if err < best_err:
                    best_err, est_params[k][2], A_cur, h_cur = err, cn, A_try, h_try
    links = [[] for _ in range(nt)]
    for k in range(total_k):
        links[est_params[k][0]].append((h_cur[k], est_params[k][1], est_params[k][2]))
    return links


def refine_mimo_rx_dd_bilinear(y_r, s_ext_full_list, links_r, nt, var_reg=0.0, n_rounds=2):
    flat = [[ti, float(tau), float(nu)] for ti in range(nt) for (_, tau, nu) in links_r[ti]]
    K = len(flat)
    A_cur = np.column_stack([eval_path_on_sig(s_ext_full_list[p[0]], p[1], p[2]) for p in flat])
    I_K = np.eye(K, dtype=np.complex128)

    def _solve_h(A):
        G = A.conj().T @ A + (var_reg + 1e-6) * I_K
        h = la.solve(G, A.conj().T @ y_r, assume_a="pos")
        return h, float(np.sum(np.abs(y_r - A @ h) ** 2) + var_reg * np.sum(np.abs(h) ** 2))

    h_cur, best_err = _solve_h(A_cur)
    for r in range(n_rounds):
        dt, dn = 0.08 * (0.45 ** r), 0.08 * (0.45 ** r)
        for k in range(K):
            ti = flat[k][0]
            for delta in (-dt, dt):
                ct = float(np.clip(flat[k][1] + delta, 0.0, TAU_MAX))
                A_try = A_cur.copy()
                A_try[:, k] = eval_path_on_sig(s_ext_full_list[ti], ct, flat[k][2])
                h_try, err = _solve_h(A_try)
                if err < best_err:
                    best_err, flat[k][1], A_cur, h_cur = err, ct, A_try, h_try
            for delta in (-dn, dn):
                cn = float(np.clip(flat[k][2] + delta, -NU_MAX * 1.1, NU_MAX * 1.1))
                A_try = A_cur.copy()
                A_try[:, k] = eval_path_on_sig(s_ext_full_list[ti], flat[k][1], cn)
                h_try, err = _solve_h(A_try)
                if err < best_err:
                    best_err, flat[k][2], A_cur, h_cur = err, cn, A_try, h_try
    links = [[] for _ in range(nt)]
    for k in range(K):
        links[flat[k][0]].append((h_cur[k], flat[k][1], flat[k][2]))
    return links


def build_stacked_mimo_eff(H_links_td, U, nr, nt, dat_idx, pil_vecs, sc_vec, d_amp):
    n_d = len(dat_idx)
    H_dat = np.zeros((nr * N, nt * n_d), dtype=np.complex128)
    y_pil = np.zeros(nr * N, dtype=np.complex128)
    Uh = U.conj().T
    for r in range(nr):
        for t in range(nt):
            H_eff = H_links_td[r][t] @ Uh
            H_dat[r * N : (r + 1) * N, t * n_d : (t + 1) * n_d] = H_eff[:, dat_idx] * (d_amp * sc_vec[t])
            y_pil[r * N : (r + 1) * N] += H_eff @ pil_vecs[t]
    return H_dat, y_pil


def run_fast_receiver(y_list, wname, lname, s2_true, true_data_flat, p_amp, d_amp, whiten=False, calibrated=True, n_em=4):
    U, c1 = WKEYS[wname]
    xp_arr, dat_idx = LAYOUTS[lname]
    sc_vec = TX_SCALES[(wname, lname)] if calibrated else np.ones(4, dtype=np.float64)
    D_raw, D_norm, meta, base_sp = get_pilot_dict(wname, lname, calibrated=calibrated)

    x_pil_scaled = [xp_arr[t] * (p_amp * sc_vec[t]) for t in range(4)]
    s_pil_scaled = [base_sp[t] * p_amp for t in range(4)]
    W_wh = get_whitener(wname, lname, d_amp, s2_true) if whiten else None
    reg0 = 16.0 if whiten else 0.5  # Prior precision E[|h|^2]^{-1} = nt*P = 16 under unit-variance whitened noise!

    links_hat = [
        joint_tx_omp_and_refine(y_list[r], s_pil_scaled, D_raw * p_amp, D_norm, meta, 4, P_PATHS, refine_steps=2, reg=reg0, W_wh=W_wh)
        for r in range(4)
    ]

    y_stack = np.concatenate(y_list)
    n_d = len(dat_idx)
    for em_it in range(n_em):
        H_hat_td = [[build_link_td(links_hat[r][t], c1) for t in range(4)] for r in range(4)]
        H_dat_h, y_pil_h = build_stacked_mimo_eff(H_hat_td, U, 4, 4, dat_idx, x_pil_scaled, sc_vec, d_amp)
        s2_eff = max(s2_true, 0.08) if em_it == 0 else max(s2_true, 0.02 if em_it == 1 else s2_true)
        _, mu_p, v_p = ep_qpsk_mimo(H_dat_h, y_stack - y_pil_h, s2_eff, n_it=6)
        s_ext_full = []
        for t in range(4):
            xf = x_pil_scaled[t].copy()
            xf[dat_idx] = mu_p[t * n_d : (t + 1) * n_d] * (d_amp * sc_vec[t])
            s_ext_full.append(W_CACHE[c1] @ (U.conj().T @ xf))
        var_reg = float(np.mean(v_p)) * (d_amp ** 2) * n_d
        if em_it == 0:
            tau_g, nu_g = np.linspace(0.0, TAU_MAX, 11), np.linspace(-NU_MAX, NU_MAX, 9)
            atoms_f, meta_f = [], []
            for ti in range(4):
                for tau in tau_g:
                    for nu in nu_g:
                        atoms_f.append(eval_path_on_sig(s_ext_full[ti], float(tau), float(nu)))
                        meta_f.append((ti, float(tau), float(nu)))
            Df_raw = np.column_stack(atoms_f)
            Df_norm = Df_raw / np.maximum(np.linalg.norm(Df_raw, axis=0), 1e-12)[None, :]
            W_re = get_whitener(wname, lname, d_amp * np.sqrt(max(float(np.mean(v_p)), 1e-3)), s2_true) if whiten else None
            reg_re = 16.0 if whiten else var_reg
            links_hat = [
                joint_tx_omp_and_refine(y_list[r], s_ext_full, Df_raw, Df_norm, meta_f, 4, P_PATHS, refine_steps=1, reg=reg_re, W_wh=W_re)
                for r in range(4)
            ]
        else:
            links_hat = [refine_mimo_rx_dd_bilinear(y_list[r], s_ext_full, links_hat[r], 4, var_reg=var_reg, n_rounds=2) for r in range(4)]

    H_hat_td = [[build_link_td(links_hat[r][t], c1) for t in range(4)] for r in range(4)]
    H_dat_h, y_pil_h = build_stacked_mimo_eff(H_hat_td, U, 4, 4, dat_idx, x_pil_scaled, sc_vec, d_amp)
    xh_f, _, _ = ep_qpsk_mimo(H_dat_h, y_stack - y_pil_h, s2_true, n_it=8)
    return float(np.mean(np.abs(xh_f - true_data_flat) > 1e-4))


def get_pbig_atoms(wname):
    if wname not in _PBIG_ATOMS_CACHE:
        U, c1 = WKEYS[wname]
        Uh = U.conj().T
        taus = np.linspace(0.0, TAU_MAX, 11)
        nus = np.linspace(-NU_MAX, NU_MAX, 9)
        mats = [build_path_td_matrix(float(tau), float(nu), c1) @ Uh for tau in taus for nu in nus]
        B = np.stack(mats, axis=0)
        _PBIG_ATOMS_CACHE[wname] = (B, np.abs(B) ** 2)
    return _PBIG_ATOMS_CACHE[wname]


def run_pbigamp64(y_list, wname, lname, s2, true_d_flat, p_amp, d_amp, max_iters=64, calibrated=True):
    xp_arr, dat_idx = LAYOUTS[lname]
    sc_vec = TX_SCALES[(wname, lname)] if calibrated else np.ones(4, dtype=np.float64)
    B_atoms, B_abs2 = get_pbig_atoms(wname)
    M_atoms = B_atoms.shape[0]
    n_d = len(dat_idx)
    xp_scaled = xp_arr * (p_amp * sc_vec[:, None])
    d_scale = d_amp * sc_vec[:, None]
    y_mat = np.stack(y_list, axis=0)

    h_hat = np.zeros((4, 4, M_atoms), dtype=np.complex128)
    v_h = np.full((4, 4, M_atoms), 1.0 / float(4 * M_atoms), dtype=np.float64)
    d_hat = np.zeros((4, n_d), dtype=np.complex128)
    v_d = np.ones((4, n_d), dtype=np.float64)
    s_var = np.zeros((4, N), dtype=np.complex128)
    v_p_old = np.ones((4, N), dtype=np.float64)

    damp = 0.5
    rho_sp = min(0.25, 4.0 / float(M_atoms))
    sig_h2 = 1.0 / 12.0

    for it in range(max_iters):
        x_hat = xp_scaled.copy()
        x_hat[:, dat_idx] = d_hat * d_scale
        Bx_hat = np.einsum("mij,tj->tmi", B_atoms, x_hat)
        Bx_abs2 = np.abs(Bx_hat) ** 2
        H_sub = np.einsum("rtm,mik->rtik", h_hat, B_atoms[:, :, dat_idx]) * d_scale[None, :, None, :]
        H_sub_abs2 = np.abs(H_sub) ** 2

        v_p_bar = np.einsum("rtm,tmi->ri", v_h, Bx_abs2) + np.einsum("rtik,tk->ri", H_sub_abs2, v_d)
        p_bar = np.einsum("rtm,tmi->ri", h_hat, Bx_hat)
        v_p = np.maximum(v_p_bar + np.einsum("rtm,mik,tk->ri", v_h, B_abs2[:, :, dat_idx], v_d * (d_scale ** 2)), 1e-5)
        if it > 0:
            v_p = damp * v_p + (1.0 - damp) * v_p_old
        v_p_old = v_p.copy()

        z_hat = p_bar - v_p * s_var
        s_new = (y_mat - z_hat) / (v_p + max(s2, 1e-3))
        v_s = 1.0 / (v_p + max(s2, 1e-3))
        s_var = damp * s_new + (1.0 - damp) * s_var if it > 0 else s_new

        v_r_inv = np.maximum(np.einsum("ri,tmi->rtm", v_s, Bx_abs2), 1e-6)
        v_r = 1.0 / v_r_inv
        r_hat = h_hat + v_r * np.einsum("ri,tmi->rtm", s_var, Bx_hat.conj())
        v_tot = v_r + sig_h2
        llr = np.clip(np.log(rho_sp / (1.0 - rho_sp)) + np.log(v_r / v_tot) + (np.abs(r_hat) ** 2) * (1.0 / v_r - 1.0 / v_tot), -30.0, 30.0)
        pi_post = 1.0 / (1.0 + np.exp(-llr))
        gam_m = (sig_h2 / v_tot) * r_hat
        gam_v = (sig_h2 * v_r) / v_tot
        h_hat = damp * (pi_post * gam_m) + (1.0 - damp) * h_hat
        v_h = damp * np.maximum(pi_post * (gam_v + (1.0 - pi_post) * (np.abs(gam_m) ** 2)), 1e-7) + (1.0 - damp) * v_h

        v_q_inv = np.maximum(np.einsum("ri,rtik->tk", v_s, H_sub_abs2), 1e-6)
        v_q = 1.0 / v_q_inv
        q_hat = d_hat + v_q * np.einsum("ri,rtik->tk", s_var, H_sub.conj())
        d2 = np.abs(q_hat[:, :, None] - QPSK[None, None, :]) ** 2
        lw = -d2 / np.maximum(v_q[:, :, None], 1e-4)
        lw -= np.max(lw, axis=2, keepdims=True)
        w = np.exp(lw)
        w /= np.sum(w, axis=2, keepdims=True)
        d_new = np.sum(w * QPSK[None, None, :], axis=2)
        vd_new = np.maximum(np.sum(w * (np.abs(QPSK[None, None, :] - d_new[:, :, None]) ** 2), axis=2), 1e-5)
        d_hat = damp * d_new + (1.0 - damp) * d_hat
        v_d = damp * vd_new + (1.0 - damp) * v_d

    dh = QPSK[np.argmin(np.abs(d_hat.ravel()[:, None] - QPSK[None, :]) ** 2, axis=1)]
    return float(np.mean(np.abs(dh - true_d_flat) > 1e-4))


def eval_fast_trial(job):
    seed, snr_db = job
    rng = np.random.default_rng(int(seed))
    paths_grid = [[None for _ in range(4)] for _ in range(4)]
    for r in range(4):
        for t in range(4):
            taus = np.sort(rng.uniform(0.15, TAU_MAX - 0.15, P_PATHS))
            for i in range(1, P_PATHS):
                if taus[i] - taus[i - 1] < 0.35:
                    taus[i] = min(TAU_MAX - 0.1, taus[i - 1] + 0.35)
            nus = rng.uniform(-NU_MAX, NU_MAX, P_PATHS)
            gains = (rng.standard_normal(P_PATHS) + 1j * rng.standard_normal(P_PATHS)) / np.sqrt(2.0 * P_PATHS * 4)
            paths_grid[r][t] = [(gains[p], float(taus[p]), float(nus[p])) for p in range(P_PATHS)]

    data_streams = [rng.choice(QPSK, 96) for _ in range(4)]
    data_flat = np.concatenate(data_streams)
    s2 = 10.0 ** (-snr_db / 10.0)
    noises = [(rng.standard_normal(N) + 1j * rng.standard_normal(N)) * np.sqrt(s2 / 2.0) for _ in range(4)]

    H_by_c1 = {c1: [[build_link_td(paths_grid[r][t], c1) for t in range(4)] for r in range(4)] for c1 in C1_VALS.values()}
    p70_p, p70_d = np.sqrt(0.70 * 4.0), np.sqrt(0.30 * 4.0 / 3.0)
    p50_p, p50_d = np.sqrt(2.0), np.sqrt(2.0 / 3.0)

    def _obs(wname, lname, pa, da, cal=True):
        U, c1 = WKEYS[wname]
        xp_arr, di = LAYOUTS[lname]
        sc_vec = TX_SCALES[(wname, lname)] if cal else np.ones(4, dtype=np.float64)
        H_t = H_by_c1[c1]
        s_tx = []
        for t in range(4):
            x = xp_arr[t] * (pa * sc_vec[t])
            x[di] = data_streams[t] * (da * sc_vec[t])
            s_tx.append(U.conj().T @ x)
        return [noises[r] + sum(H_t[r][t] @ s_tx[t] for t in range(4)) for r in range(4)]

    res = {}
    # 0. Exact uncalibrated reproduction controls (must match out_n2_mimo_dd_overhead.json to machine precision!)
    res["ctrl_OFDM_orth16_raw"] = run_fast_receiver(_obs("OFDM", "orth16", p70_p, p70_d, cal=False), "OFDM", "orth16", s2, data_flat, p70_p, p70_d, whiten=False, calibrated=False)
    res["ctrl_AFDM_orth16_c7_raw"] = run_fast_receiver(_obs("AFDM_c7", "orth16", p70_p, p70_d, cal=False), "AFDM_c7", "orth16", s2, data_flat, p70_p, p70_d, whiten=False, calibrated=False)
    res["ctrl_AFDM_cdm_c7_raw"] = run_fast_receiver(_obs("AFDM_c7", "cdm_comb", p70_p, p70_d, cal=False), "AFDM_c7", "cdm_comb", s2, data_flat, p70_p, p70_d, whiten=False, calibrated=False)

    # 1. Exact energy-calibrated OFDM & SC-FDE fairness controls (with & without Golomb + Prior Data Whitening)
    res["ofdm_orth16_wh"] = run_fast_receiver(_obs("OFDM", "orth16", p70_p, p70_d), "OFDM", "orth16", s2, data_flat, p70_p, p70_d, whiten=True)
    res["ofdm_gol8_raw"] = run_fast_receiver(_obs("OFDM", "gol8", p70_p, p70_d), "OFDM", "gol8", s2, data_flat, p70_p, p70_d, whiten=False)
    res["ofdm_gol8_wh"] = run_fast_receiver(_obs("OFDM", "gol8", p70_p, p70_d), "OFDM", "gol8", s2, data_flat, p70_p, p70_d, whiten=True)
    res["scfde_z32_uw20_wh"] = run_fast_receiver(_obs("SCFDE", "z32_cdm20", p70_p, p70_d), "SCFDE", "z32_cdm20", s2, data_flat, p70_p, p70_d, whiten=True)

    # 2. AFDM dedicated pilot layouts + c1 sweep (raw & exact prior data-whitened)
    res["afdm_orth16_c3_wh"] = run_fast_receiver(_obs("AFDM_c3", "orth16", p70_p, p70_d), "AFDM_c3", "orth16", s2, data_flat, p70_p, p70_d, whiten=True)
    res["afdm_gol8_c5_wh"] = run_fast_receiver(_obs("AFDM_c5", "gol8", p70_p, p70_d), "AFDM_c5", "gol8", s2, data_flat, p70_p, p70_d, whiten=True)
    res["afdm_gol8_c7_raw"] = run_fast_receiver(_obs("AFDM_c7", "gol8", p70_p, p70_d), "AFDM_c7", "gol8", s2, data_flat, p70_p, p70_d, whiten=False)
    res["afdm_gol8_c7_wh"] = run_fast_receiver(_obs("AFDM_c7", "gol8", p70_p, p70_d), "AFDM_c7", "gol8", s2, data_flat, p70_p, p70_d, whiten=True)
    res["afdm_gol8_c9_wh"] = run_fast_receiver(_obs("AFDM_c9", "gol8", p70_p, p70_d), "AFDM_c9", "gol8", s2, data_flat, p70_p, p70_d, whiten=True)
    res["afdm_gol8_c11_wh"] = run_fast_receiver(_obs("AFDM_c11", "gol8", p70_p, p70_d), "AFDM_c11", "gol8", s2, data_flat, p70_p, p70_d, whiten=True)
    res["afdm_cdm_gol32_c7_wh"] = run_fast_receiver(_obs("AFDM_c7", "cdm_gol32", p70_p, p70_d), "AFDM_c7", "cdm_gol32", s2, data_flat, p70_p, p70_d, whiten=True)
    res["afdm_cdm_gol32_c7_p50_wh"] = run_fast_receiver(_obs("AFDM_c7", "cdm_gol32", p50_p, p50_d), "AFDM_c7", "cdm_gol32", s2, data_flat, p50_p, p50_d, whiten=True)
    res["afdm_z32_cdm20_c4_wh"] = run_fast_receiver(_obs("AFDM_c4", "z32_cdm20", p70_p, p70_d), "AFDM_c4", "z32_cdm20", s2, data_flat, p70_p, p70_d, whiten=True)
    res["afdm_z32_cdm20_c5_wh"] = run_fast_receiver(_obs("AFDM_c5", "z32_cdm20", p70_p, p70_d), "AFDM_c5", "z32_cdm20", s2, data_flat, p70_p, p70_d, whiten=True)
    return res


def eval_pbigamp_trial(seed):
    rng = np.random.default_rng(int(seed))
    paths_grid = [[None for _ in range(4)] for _ in range(4)]
    for r in range(4):
        for t in range(4):
            taus = np.sort(rng.uniform(0.15, TAU_MAX - 0.15, P_PATHS))
            for i in range(1, P_PATHS):
                if taus[i] - taus[i - 1] < 0.35:
                    taus[i] = min(TAU_MAX - 0.1, taus[i - 1] + 0.35)
            nus = rng.uniform(-NU_MAX, NU_MAX, P_PATHS)
            gains = (rng.standard_normal(P_PATHS) + 1j * rng.standard_normal(P_PATHS)) / np.sqrt(2.0 * P_PATHS * 4)
            paths_grid[r][t] = [(gains[p], float(taus[p]), float(nus[p])) for p in range(P_PATHS)]

    data_streams = [rng.choice(QPSK, 96) for _ in range(4)]
    data_flat = np.concatenate(data_streams)
    s2 = 10.0 ** (-30.0 / 10.0)
    noises = [(rng.standard_normal(N) + 1j * rng.standard_normal(N)) * np.sqrt(s2 / 2.0) for _ in range(4)]
    p70_p, p70_d = np.sqrt(0.70 * 4.0), np.sqrt(0.30 * 4.0 / 3.0)

    def _obs(wname, lname):
        U, c1 = WKEYS[wname]
        xp_arr, di = LAYOUTS[lname]
        sc_vec = TX_SCALES[(wname, lname)]
        H_t = [[build_link_td(paths_grid[r][t], c1) for t in range(4)] for r in range(4)]
        s_tx = []
        for t in range(4):
            x = xp_arr[t] * (p70_p * sc_vec[t])
            x[di] = data_streams[t] * (p70_d * sc_vec[t])
            s_tx.append(U.conj().T @ x)
        return [noises[r] + sum(H_t[r][t] @ s_tx[t] for t in range(4)) for r in range(4)]

    return {
        "pbig64_ofdm_orth16": run_pbigamp64(_obs("OFDM", "orth16"), "OFDM", "orth16", s2, data_flat, p70_p, p70_d),
        "pbig64_ofdm_gol8": run_pbigamp64(_obs("OFDM", "gol8"), "OFDM", "gol8", s2, data_flat, p70_p, p70_d),
        "pbig64_afdm_orth16_c7": run_pbigamp64(_obs("AFDM_c7", "orth16"), "AFDM_c7", "orth16", s2, data_flat, p70_p, p70_d),
        "pbig64_afdm_gol8_c7": run_pbigamp64(_obs("AFDM_c7", "gol8"), "AFDM_c7", "gol8", s2, data_flat, p70_p, p70_d),
        "pbig64_afdm_gol8_c9": run_pbigamp64(_obs("AFDM_c9", "gol8"), "AFDM_c9", "gol8", s2, data_flat, p70_p, p70_d),
        "pbig64_afdm_cdm_gol32_c7": run_pbigamp64(_obs("AFDM_c7", "cdm_gol32"), "AFDM_c7", "cdm_gol32", s2, data_flat, p70_p, p70_d),
    }


def boot_ci(arr, seed=20261529):
    rng = np.random.default_rng(seed)
    n = len(arr)
    idx = rng.integers(0, n, size=(2000, n))
    b = np.mean(arr[idx], axis=1)
    return [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))]


def summarize(raw_list):
    keys = list(raw_list[0].keys())
    out = {}
    for k in keys:
        arr = np.array([r[k] for r in raw_list], dtype=np.float64)
        out[k] = {"ser_mean": float(np.mean(arr)), "ser_ci95": boot_ci(arr)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials-fast", type=int, default=40)
    ap.add_argument("--trials-pbig", type=int, default=24)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    t0 = time.time()
    coh = measure_coherence_summary()
    print("=== Off-Peak 2D Dictionary Coherence Audit ===")
    for k, v in coh.items():
        print(f"  {k:24s}: sameTX_offpeak={v['mu_same_tx_offpeak']:.4f} | interTX_max={v['mu_inter_tx_max']:.4f}", flush=True)

    fast_out = {}
    with Pool(processes=args.workers) as pool:
        for ci, (cname, snr_db) in ((2, ("mimo4x4_indep_snr24", 24.0)), (3, ("mimo4x4_indep_snr30", 30.0))):
            t1 = time.time()
            jobs = [(2026986000 + ci * 10000 + i, snr_db) for i in range(args.trials_fast)]
            raw = pool.map(eval_fast_trial, jobs)
            s = summarize(raw)
            # Paired difference: best AFDM fast arm vs best OFDM fast arm
            af_keys = [k for k in s if k.startswith("afdm_")]
            of_keys = [k for k in s if k.startswith("ofdm_") or k == "ctrl_OFDM_orth16_raw"]
            best_af = min(af_keys, key=lambda k: s[k]["ser_mean"])
            best_of = min(of_keys, key=lambda k: s[k]["ser_mean"])
            diff_arr = np.array([r[best_af] - r[best_of] for r in raw], dtype=np.float64)
            fast_out[cname] = {
                "snr_db": snr_db,
                "n_trials": args.trials_fast,
                "elapsed_s": float(time.time() - t1),
                "best_afdm_arm": best_af,
                "best_ofdm_arm": best_of,
                "paired_afdm_minus_ofdm_mean": float(np.mean(diff_arr)),
                "paired_afdm_minus_ofdm_ci95": boot_ci(diff_arr),
                "arms": s,
            }
            print(f"\n=== Fast 4-EM [{cname}] ({fast_out[cname]['elapsed_s']:.1f}s) ===", flush=True)
            for k, v in s.items():
                print(f"  {k:28s}: SER={v['ser_mean']:.4f} CI=[{v['ser_ci95'][0]:.4f}, {v['ser_ci95'][1]:.4f}]", flush=True)
            print(
                f"  >> Best AFDM ({best_af}={s[best_af]['ser_mean']:.4f}) - Best OFDM ({best_of}={s[best_of]['ser_mean']:.4f}) = "
                f"{np.mean(diff_arr):+.4f} CI={fast_out[cname]['paired_afdm_minus_ofdm_ci95']}",
                flush=True,
            )

        t2 = time.time()
        pbig_seeds = [2026991000 + 10000 + i for i in range(args.trials_pbig)]
        raw_pb = pool.map(eval_pbigamp_trial, pbig_seeds)
        s_pb = summarize(raw_pb)
        diff_pb = np.array([r["pbig64_afdm_gol8_c7"] - r["pbig64_ofdm_orth16"] for r in raw_pb], dtype=np.float64)
        pbig_out = {
            "snr_db": 30.0,
            "n_trials": args.trials_pbig,
            "elapsed_s": float(time.time() - t2),
            "paired_afdm_gol8_c7_minus_ofdm_orth16": {
                "mean": float(np.mean(diff_pb)),
                "ci95": boot_ci(diff_pb),
            },
            "arms": s_pb,
        }
        print(f"\n=== 64-Step P-BiG-AMP @ 30 dB ({pbig_out['elapsed_s']:.1f}s) ===", flush=True)
        for k, v in s_pb.items():
            print(f"  {k:28s}: SER={v['ser_mean']:.4f} CI=[{v['ser_ci95'][0]:.4f}, {v['ser_ci95'][1]:.4f}]", flush=True)

    payload = {
        "_argv": sys.argv,
        "_config": vars(args),
        "golomb_4x8_groups": [g.tolist() for g in GOL_GROUPS],
        "coherence_audit": coh,
        "bw99_fs": BW99_MAP,
        "raw_precal_etx": RAW_ETX_MAP,
        "calibrated_target_etx": 144.0,
        "fast_4em_results": fast_out,
        "pbigamp64_snr30_results": pbig_out,
        "elapsed_total_s": float(time.time() - t0),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, allow_nan=False)
    print(f"\nSaved {args.out} in {payload['elapsed_total_s']:.1f}s", flush=True)


if __name__ == "__main__":
    main()
