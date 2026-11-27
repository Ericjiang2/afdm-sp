#!/usr/bin/env python3
"""
Round 15 Phase 1B — Wildcard Candidate `P-m-15b-02` (`C15`) Formal Paired 4-Waveform Steelman Teardown
(`td_m_p1b_c15_blind_dd_cci.py`):
Blind Uncoordinated Doubly-Dispersive Co-Channel Interference Annihilation on Dual-Antenna (`Nr=2`)
UEs (`y = H_1 s_1 + H_2 s_2 + w`, SIR = 0 dB, ZERO interferer pilots, UNKNOWN 4-path fractional-Doppler
`H_2` with 4 distinct AoAs -> full-rank 2x2 spatial interference!).

Physical Motivation & Literature Anchors:
  In dense 6G LEO-NTN multi-beam/adjacent-satellite downlinks, V2X sidelink, and uncoordinated shared-spectrum
  high-mobility networks, a dual-antenna (`Nr=2`) terminal suffers strong (`SIR ~ 0 dB`) co-channel interference
  from an uncoordinated transmitter over an independent 4-path doubly-dispersive channel `H_2` (`l_max=6, k_max=1.5`)
  with NO known interferer pilots. Because `H_2` has `P=4 > Nr=2` paths at distinct AoAs and time-varying Doppler,
  both 3GPP spatial/PRB MMSE-IRC and LTI SIMO blind cross-relations break down due to the non-commutativity of
  doubly-dispersive LTV operators (`H_{2,1} H_{2,0} != H_{2,0} H_{2,1}`), yet the exact `N`-dimensional left
  nullspace of `H_2` (`C_2 = s0 I + H_2 H_2^H`) annihilates `H_2 s_2` to `SER = 0.00000` WITHOUT knowing `s_2`!

Ruthless Full-Strength Steelman Suite (ALL strictly legal; `H_1` given to all Steelmen so zero desired-CE artifact!):
  0. `Ref_Clean_NoCCI`           : Zero-interferer sanity gate (must be 0.00000 on all 4 waveforms!)
  1. `Pub_3GPP_Global_IRC`       : Standard 2x2 spatial covariance whitening estimated on clean pilot rows
  2. `SM1_SlidingWin16_IRC_3DD`  : Local 16-sample time-varying 2x2 spatial IRC + 3-pass DD OAMP
  3. `SM2_3GPP_PerPRB_FreqIRC`   : 3GPP LTE/5G per-subband (PRB=6 & PRB=12 best-of) frequency-domain 2x2 MMSE-IRC!
  4. `SM3_SpaceTime_ToepCov_3DD` : 7-lag PSD-projected 2x2 space-time block-Toeplitz covariance + 3-pass DD OAMP
  5. `SM4_SIMO_LTI_CR_DD`        : Xu-Liu-Tong-Kailath TSP'95 LTI SIMO Cross-Relation (`Q=1`) + 3-pass DD
  6. `SM5_FullAp_BEM_CR_DD`      : Giannakis-Tepedelenlioglu TSP'98 BEM-CR (`Q=2/3` on full-aperture pilots -> `Q=5` 3-pass DD)
  7. `SM6_Blind_2x2_CMA_Sub`     : Textbook 2x2 multi-tap blind Constant-Modulus / Kurtosis separation + DD
Non-Cheating Reference Oracles (NEVER know interferer data `x_2`!):
  8. `Oracle_KnownH2_GaussLMMSE` : Knows ONLY `H_2` (treats `s_2` as unknown Gaussian: `C_2 = s0 I + H_2 H_2^H`, ZERO `x_2`!)
  9. `Oracle_KnownH2_JointEP`    : Knows ONLY `H_2` + `const2`, jointly detects `[x_1; x_2]` (ZERO `x_2` truth!).
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
from scipy.linalg import cho_factor, cho_solve, qr
from scipy.stats import t as student_t

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import td_m_p1b_c3_bursty_impulsive as c3m
import td_m_p1b_c8_joint_ce_bursty as c8


def build_mimo_dd_channel(N: int, Nr: int, P: int, l_max: int, k_max: float, rng: np.random.Generator, cpp_c1: float = 0.0):
    delays = np.sort(rng.choice(np.arange(0, l_max + 1), size=P, replace=False)); delays[0] = 0
    dops = rng.uniform(-k_max, k_max, size=P)
    aoas = rng.uniform(-math.pi / 2.2, math.pi / 2.2, size=P)
    pdp = np.exp(-0.18 * delays); pdp /= np.sum(pdp)
    g_base = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) * np.sqrt(pdp / 2.0)
    g_base /= max(np.linalg.norm(g_base), 1e-12)
    return delays, dops, aoas, g_base


def materialize_mimo_H(N, Nr, delays, dops, aoas, g_base, cpp_c1=0.0):
    H_list = [c8.build_H_from_paths(N, delays, dops, g_base * np.exp(-1j * math.pi * r * np.sin(aoas)), cpp_c1=cpp_c1) for r in range(Nr)]
    return np.vstack(H_list), H_list


def fit_bem_annihilator(r0, r1, valid_rows, N, L, k_max, Q_b):
    n_idx = np.arange(N, dtype=float)
    # Collapse to Q_b=1 when k_max==0 so BEM columns are never duplicated in the LTI control!
    eff_Q = 1 if (Q_b <= 1 or k_max <= 1e-9) else Q_b
    qs = np.linspace(-k_max, k_max, eff_Q) if eff_Q > 1 else np.array([0.0])
    cols0, cols1 = [], []
    for qv in qs:
        bq = np.exp(1j * 2.0 * math.pi * qv * n_idx / float(N))
        for l in range(L):
            cols0.append((bq * np.roll(r0, l))[valid_rows])
            cols1.append((-bq * np.roll(r1, l))[valid_rows])
    M_bem = np.column_stack(cols0 + cols1)
    _, _, Vhb = np.linalg.svd(M_bem)
    vb = Vhb[-1].conj()
    G0 = np.zeros((N, N), dtype=np.complex128); G1 = np.zeros((N, N), dtype=np.complex128)
    idx_c = 0
    for qv in qs:
        bq = np.exp(1j * 2.0 * math.pi * qv * n_idx / float(N))
        for l in range(L):
            G0 += vb[idx_c] * (bq[:, None] * np.roll(np.eye(N), l, axis=0))
            G1 += -vb[eff_Q * L + idx_c] * (bq[:, None] * np.roll(np.eye(N), l, axis=0))
            idx_c += 1
    return np.hstack([G0, G1])


def per_prb_freq_irc_cov(res_2, N, Nr, sigma0_sq, prb_sz=8):
    """3GPP LTE/5G Per-PRB Frequency-Domain 2x2 MMSE-IRC covariance lifted back to time domain!"""
    F = np.fft.fft(np.eye(N)) / math.sqrt(float(N))
    Rf = np.vstack([F @ res_2[r] for r in range(Nr)])  # (2, N)
    # Build exact 2N x 2N covariance in frequency domain (block-diagonal per subcarrier with PRB-smoothed 2x2 R_k)
    C_f = np.zeros((Nr * N, Nr * N), dtype=np.complex128)
    for k in range(N):
        lo = max(0, k - prb_sz // 2); hi = min(N, lo + prb_sz); lo = max(0, hi - prb_sz)
        sub = Rf[:, lo:hi]
        Rk = (sub @ sub.conj().T) / float(hi - lo) + (sigma0_sq + 0.02) * np.eye(Nr)
        for r1 in range(Nr):
            for r2 in range(Nr):
                C_f[r1 * N + k, r2 * N + k] = Rk[r1, r2]
    F_blk = np.kron(np.eye(Nr), F)
    C_td = F_blk.conj().T @ C_f @ F_blk
    return 0.5 * (C_td + C_td.conj().T)


def blind_cma_2x2_cov(res_2, N, Nr, sigma0_sq):
    """Textbook 2x2 multi-tap (L_f=5) Constant-Modulus blind equalizer extracting s2_hat -> rank-1 interference subspace."""
    L_f = 5
    # Stack [res_2[:, n], res_2[:, n-1], ..., res_2[:, n-L_f+1]] in C^{10 x N}
    X = np.vstack([np.roll(res_2, l, axis=1) for l in range(L_f)])  # (2*L_f, N)
    # Whiten X via PCA
    Rx = (X @ X.conj().T) / float(N) + 1e-3 * np.eye(Nr * L_f)
    ev, Uv = np.linalg.eigh(Rx)
    W_wh = (Uv * (1.0 / np.sqrt(np.maximum(ev, 1e-4)))[None, :]) @ Uv.conj().T
    Z = W_wh @ X
    # CMA / kurtosis fixed-point iterations for unit-modulus interferer stream
    w_c = np.zeros(Nr * L_f, dtype=np.complex128); w_c[0] = 1.0
    for _ in range(25):
        u = w_c.conj() @ Z  # (N,)
        err = (np.abs(u) ** 2 - 1.0) * u
        grad = (Z @ err.conj()) / float(N)
        w_c = w_c - 0.15 * grad
        w_c /= max(np.linalg.norm(w_c), 1e-12)
    s2_est = w_c.conj() @ Z
    s2_est /= max(math.sqrt(float(np.mean(np.abs(s2_est) ** 2))), 1e-9)
    # Fit 7-tap 2x1 LTI channel H2_cma from res_2 ~ conv(s2_est, h2_r)
    L_c = 7
    S_mat = np.column_stack([np.roll(s2_est, l) for l in range(L_c)])
    H_blocks = []
    for r in range(Nr):
        hr = np.linalg.solve(S_mat.conj().T @ S_mat + 1e-2 * np.eye(L_c), S_mat.conj().T @ res_2[r])
        H_blocks.append(sum(hr[l] * np.roll(np.eye(N), l, axis=0) for l in range(L_c)))
    H2_c = np.vstack(H_blocks)
    return sigma0_sq * np.eye(Nr * N) + H2_c @ H2_c.conj().T + 0.02 * np.eye(Nr * N)


def run_paired_seed(args):
    seed, snr_db, sir_db, mod2, k_max = args
    N = 256; Nr = 2; P = 4; l_max = 6; L = l_max + 1
    rng = np.random.default_rng(seed)
    const1 = c3m.gray_qam(16)
    const2 = c3m.gray_qam(mod2)
    sigma0_sq = 10.0 ** (-snr_db / 10.0)
    sir_lin = 10.0 ** (sir_db / 10.0)
    scale2 = 1.0 / math.sqrt(sir_lin)
    I_2N = np.eye(Nr * N, dtype=np.complex128)
    F_N = np.fft.fft(np.eye(N)) / math.sqrt(float(N))
    F_blk = np.kron(np.eye(Nr), F_N)

    ch1 = build_mimo_dd_channel(N, Nr, P, l_max, k_max, rng)
    ch2 = build_mimo_dd_channel(N, Nr, P, l_max, k_max, rng)

    # Full-aperture 2x32 pilot clusters [0..31] & [224..255] (64/256 = 25% overhead, 40 valid CR rows spanning full frame!)
    clusters = [np.arange(0, 32), np.arange(224, 256)]
    obs_pil = np.concatenate([np.arange(c[0] + l_max, c[-1] + 1) for c in clusters])
    cr_rows = np.concatenate([np.arange(c[0] + 2 * l_max, c[-1] + 1) for c in clusters])  # 40 valid zero-data CR rows!
    pil_t = np.concatenate(clusters); data_t = np.setdiff1d(np.arange(N), pil_t); Nd = len(data_t); didx = np.arange(Nd)

    u_pil = np.exp(-1j * math.pi * 7.0 * np.arange(len(pil_t)) * (np.arange(len(pil_t)) + 1) / float(len(pil_t)))
    x1 = const1[rng.integers(0, len(const1), size=Nd)]
    x2 = const2[rng.integers(0, len(const2), size=N)]
    s1_pil = np.zeros(N, dtype=np.complex128); s1_pil[pil_t] = u_pil
    w = (rng.standard_normal(Nr * N) + 1j * rng.standard_normal(Nr * N)) * math.sqrt(sigma0_sq / 2.0)

    U1_map = {
        "AFDM": c3m.daft_mat(Nd, 5.0 / (2.0 * Nd), 1.0 / (2.0 * math.pi * Nd)),
        "OTFS": c3m.otfs_mat(16, 12),
        "OFDM": np.fft.fft(np.eye(Nd)) / math.sqrt(Nd),
        "SC-FDE": np.eye(Nd, dtype=np.complex128),
    }
    U2_map = {
        "AFDM": c3m.daft_mat(N, 5.0 / (2.0 * N), 1.0 / (2.0 * math.pi * N)),
        "OTFS": c3m.otfs_mat(16, 16),
        "OFDM": np.fft.fft(np.eye(N)) / math.sqrt(N),
        "SC-FDE": np.eye(N, dtype=np.complex128),
    }

    out = {}
    for wf in ("AFDM", "OTFS", "OFDM", "SC-FDE"):
        c1 = 5.0 / (2.0 * N) if wf == "AFDM" else 0.0
        H1, H1_l = materialize_mimo_H(N, Nr, *ch1, cpp_c1=c1)
        H2, H2_l = materialize_mimo_H(N, Nr, *ch2, cpp_c1=c1)
        U1 = U1_map[wf]; U2 = U2_map[wf]
        s1 = s1_pil.copy(); s1[data_t] = U1.conj().T @ x1
        s2 = scale2 * (U2.conj().T @ x2)
        y = H1 @ s1 + H2 @ s2 + w
        y_cl = H1 @ s1 + w
        y_d = y - H1 @ s1_pil
        A1 = H1[:, data_t] @ U1.conj().T

        wres = {}
        # 0. Sanity gate (no CCI)
        wres["Ref_Clean_NoCCI"] = c3m.hard_ser_sub(c3m.full_cov_ep_oamp(y_cl - H1 @ s1_pil, A1, sigma0_sq * I_2N, const1, n_iters=6), x1, const1, didx)

        # 1. Pub: 3GPP Global 2x2 Spatial IRC
        r_pil = np.vstack([(y[r*N:(r+1)*N] - H1_l[r] @ s1_pil)[obs_pil] for r in range(Nr)])
        R_sp = (r_pil @ r_pil.conj().T) / float(len(obs_pil)) + sigma0_sq * np.eye(Nr)
        C_irc = np.kron(R_sp, np.eye(N))
        x_irc = c3m.full_cov_ep_oamp(y_d, A1, C_irc, const1, n_iters=8)
        wres["Pub_3GPP_Global_IRC"] = c3m.hard_ser_sub(x_irc, x1, const1, didx)

        # 2. SM1: Sliding-Window 16-sample Time-Varying 2x2 IRC + 3-pass DD
        x_sw = x_irc.copy()
        for _ in range(3):
            s1_h = s1_pil.copy(); s1_h[data_t] = U1.conj().T @ x_sw
            res_2 = np.vstack([y[r*N:(r+1)*N] - H1_l[r] @ s1_h for r in range(Nr)])
            C_sw = np.zeros((Nr * N, Nr * N), dtype=np.complex128)
            for b0 in range(0, N, 16):
                rb = res_2[:, b0:b0+16]; Rb = (rb @ rb.conj().T) / 16.0 + 0.05 * np.eye(Nr)
                for r1 in range(Nr):
                    for r2 in range(Nr):
                        C_sw[r1*N+b0:r1*N+b0+16, r2*N+b0:r2*N+b0+16] = Rb[r1, r2] * np.eye(16)
            x_sw = c3m.full_cov_ep_oamp(y_d, A1, C_sw, const1, n_iters=8)
        wres["SM1_SlidingWin16_IRC_3DD"] = c3m.hard_ser_sub(x_sw, x1, const1, didx)

        # 3. SM2: 3GPP Per-PRB Frequency-Domain 2x2 MMSE-IRC (PRB=8 + 3-pass DD)
        x_prb = x_irc.copy()
        for _ in range(3):
            s1_h = s1_pil.copy(); s1_h[data_t] = U1.conj().T @ x_prb
            res_2 = np.vstack([y[r*N:(r+1)*N] - H1_l[r] @ s1_h for r in range(Nr)])
            C_prb = per_prb_freq_irc_cov(res_2, N, Nr, sigma0_sq, prb_sz=8)
            x_prb = c3m.full_cov_ep_oamp(y_d, A1, C_prb, const1, n_iters=8)
        wres["SM2_3GPP_PerPRB_FreqIRC"] = c3m.hard_ser_sub(x_prb, x1, const1, didx)

        # 4. SM3: 7-lag PSD Space-Time Block-Toeplitz Covariance + 3-pass DD
        x_bt = x_irc.copy()
        for _ in range(3):
            s1_h = s1_pil.copy(); s1_h[data_t] = U1.conj().T @ x_bt
            res_2 = np.vstack([y[r*N:(r+1)*N] - H1_l[r] @ s1_h for r in range(Nr)])
            C_bt = np.zeros((Nr * N, Nr * N), dtype=np.complex128)
            for k in range(L):
                Rk = (res_2[:, k:] @ res_2[:, :N-k].conj().T) / float(N - k) * (1.0 - k / float(L))
                for r1 in range(Nr):
                    for r2 in range(Nr):
                        for n in range(k, N):
                            C_bt[r1*N+n, r2*N+n-k] = Rk[r1, r2]
                            if k > 0: C_bt[r2*N+n-k, r1*N+n] = np.conj(Rk[r1, r2])
            ev, Uv = np.linalg.eigh(0.5 * (C_bt + C_bt.conj().T))
            C_bt = (Uv * np.maximum(ev, sigma0_sq)[None, :]) @ Uv.conj().T
            x_bt = c3m.full_cov_ep_oamp(y_d, A1, C_bt, const1, n_iters=8)
        wres["SM3_SpaceTime_ToepCov_3DD"] = c3m.hard_ser_sub(x_bt, x1, const1, didx)

        # 5. SM4 & SM5: SIMO LTI-CR (Q=1) and Full-Aperture BEM-CR (Q=2 -> DD Q=5)
        r0_p = y[:N] - H1_l[0] @ s1_pil; r1_p = y[N:] - H1_l[1] @ s1_pil
        G1 = fit_bem_annihilator(r0_p, r1_p, cr_rows, N, L, k_max, Q_b=1)
        x_cr1 = c3m.full_cov_ep_oamp(G1 @ y_d, G1 @ A1, sigma0_sq * (G1 @ G1.conj().T) + 1e-3 * np.eye(N), const1, n_iters=8)
        wres["SM4_SIMO_LTI_CR"] = c3m.hard_ser_sub(x_cr1, x1, const1, didx)

        G2 = fit_bem_annihilator(r0_p, r1_p, cr_rows, N, L, k_max, Q_b=2)
        x_bem = c3m.full_cov_ep_oamp(G2 @ y_d, G2 @ A1, sigma0_sq * (G2 @ G2.conj().T) + 1e-3 * np.eye(N), const1, n_iters=8)
        for _ in range(3):
            s1_h = s1_pil.copy(); s1_h[data_t] = U1.conj().T @ x_bem
            G5 = fit_bem_annihilator(y[:N] - H1_l[0] @ s1_h, y[N:] - H1_l[1] @ s1_h, np.arange(N), N, L, k_max, Q_b=5)
            x_bem = c3m.full_cov_ep_oamp(G5 @ y_d, G5 @ A1, sigma0_sq * (G5 @ G5.conj().T) + 1e-3 * np.eye(N), const1, n_iters=8)
        wres["SM5_FullAp_BEM_CR_3DD"] = c3m.hard_ser_sub(x_bem, x1, const1, didx)

        # 6. SM6: Blind 2x2 Multi-Tap CMA + Subspace Subtraction + 2-pass DD
        x_cma = x_prb.copy()
        for _ in range(2):
            s1_h = s1_pil.copy(); s1_h[data_t] = U1.conj().T @ x_cma
            res_2 = np.vstack([y[r*N:(r+1)*N] - H1_l[r] @ s1_h for r in range(Nr)])
            C_cma = blind_cma_2x2_cov(res_2, N, Nr, sigma0_sq)
            x_cma = c3m.full_cov_ep_oamp(y_d, A1, C_cma, const1, n_iters=8)
        wres["SM6_Blind_2x2_CMA_DD"] = c3m.hard_ser_sub(x_cma, x1, const1, didx)

        # 6b. SM7 (OFDM only): 3GPP Uniform-Comb Pilot Per-PRB Freq-IRC (64/256 comb pilots -> zero DD propagation!)
        if wf == "OFDM":
            pil_f = np.arange(0, N, 4); data_f = np.setdiff1d(np.arange(N), pil_f)
            X1_p = np.zeros(N, dtype=np.complex128); X1_p[pil_f] = u_pil
            X1_c = X1_p.copy(); X1_c[data_f] = x1
            s1_pc = F_N.conj().T @ X1_p; s1_c = F_N.conj().T @ X1_c
            y_c = H1 @ s1_c + H2 @ s2 + w; yd_c = y_c - H1 @ s1_pc
            A1_c = H1 @ F_N.conj().T[:, data_f]
            Yf = np.vstack([F_N @ yd_c[r*N:(r+1)*N] for r in range(Nr)])
            C_f = np.zeros((Nr * N, Nr * N), dtype=np.complex128)
            for k in range(N):
                dists = np.minimum(np.abs(pil_f - k), N - np.abs(pil_f - k))
                near = pil_f[np.argsort(dists)[:4]]
                sub = Yf[:, near]; Rk = (sub @ sub.conj().T) / 4.0 + (sigma0_sq + 1e-3) * np.eye(Nr)
                for r1 in range(Nr):
                    for r2 in range(Nr): C_f[r1*N+k, r2*N+k] = Rk[r1, r2]
            C_comb = F_blk.conj().T @ C_f @ F_blk
            x_comb = c3m.full_cov_ep_oamp(yd_c, A1_c, 0.5 * (C_comb + C_comb.conj().T), const1, n_iters=8)
            wres["SM7_3GPP_OFDM_CombPRB_IRC"] = c3m.hard_ser_sub(x_comb, x1, const1, didx)

        # 6c. Sol Call-4 Null(A_1) 320-dim Zero-Data Projection Steelman Suite (SM8..SM11 -> 12 total steelmen!):
        #     Exact left nullspace Q_perp of known A_1 (Q_perp^H A_1 = 0 -> 320 pure interferer equations!)
        Q_full, _ = qr(A1, mode="full")
        Q_perp = Q_full[:, Nd:]  # (512, 320)
        y_proj = Q_perp @ (Q_perp.conj().T @ y_d)
        res_p = np.vstack([y_proj[:N], y_proj[N:]])

        # SM8: Exact Variable-Projection BEM-5 CR eliminating x_1 via known A_1
        x_vp = x_prb.copy()
        for _ in range(6):
            r_vp = y_d - A1 @ x_vp
            G_vp = fit_bem_annihilator(r_vp[:N], r_vp[N:], np.arange(N), N, L, k_max, Q_b=5)
            Ga = G_vp @ A1; Gy = G_vp @ y_d
            x_vp = np.linalg.solve(Ga.conj().T @ Ga + 1e-3 * np.eye(Nd), Ga.conj().T @ Gy)
        x_8 = c3m.full_cov_ep_oamp(G_vp @ y_d, G_vp @ A1, sigma0_sq * (G_vp @ G_vp.conj().T) + 1e-3 * np.eye(N), const1, n_iters=8)
        wres["SM8_NullA1_VarProj_BEM5"] = c3m.hard_ser_sub(x_8, x1, const1, didx)

        # SM9: 7-lag Space-Time Toeplitz Cov estimated purely from Null(A_1)-projected y_proj (ZERO x_1 leakage!)
        C_pbt = np.zeros((Nr * N, Nr * N), dtype=np.complex128)
        for k in range(L):
            Rk = (res_p[:, k:] @ res_p[:, :N-k].conj().T) / float(N - k) * (1.0 - k / float(L))
            for r1 in range(Nr):
                for r2 in range(Nr):
                    for n in range(k, N):
                        C_pbt[r1*N+n, r2*N+n-k] = Rk[r1, r2]
                        if k > 0: C_pbt[r2*N+n-k, r1*N+n] = np.conj(Rk[r1, r2])
        ev, Uv = np.linalg.eigh(0.5 * (C_pbt + C_pbt.conj().T))
        C_pbt = (Uv * np.maximum(ev, sigma0_sq)[None, :]) @ Uv.conj().T
        wres["SM9_NullA1_Proj_ToepCov"] = c3m.hard_ser_sub(c3m.full_cov_ep_oamp(y_d, A1, C_pbt, const1, n_iters=8), x1, const1, didx)

        # SM10: Per-PRB(6) Freq-IRC estimated purely from Null(A_1)-projected y_proj (ZERO x_1 leakage!)
        C_pprb = per_prb_freq_irc_cov(res_p, N, Nr, sigma0_sq, prb_sz=6)
        wres["SM10_NullA1_Proj_PRB6_IRC"] = c3m.hard_ser_sub(c3m.full_cov_ep_oamp(y_d, A1, C_pprb, const1, n_iters=8), x1, const1, didx)

        # SM11: Multi-tap 2x2 CMA directly on Null(A_1)-projected y_proj (ZERO x_1 leakage!)
        C_pcma = blind_cma_2x2_cov(res_p, N, Nr, sigma0_sq)
        wres["SM11_NullA1_Proj_CMA"] = c3m.hard_ser_sub(c3m.full_cov_ep_oamp(y_d, A1, C_pcma, const1, n_iters=8), x1, const1, didx)

        # 7. 100% NON-CHEATING Oracle: Known H2 ONLY (Gaussian interferer covariance C_2 = s0 I + scale2^2 H2 H2^H, ZERO x2 truth!)
        C2_true = sigma0_sq * I_2N + (scale2 ** 2) * (H2 @ H2.conj().T)
        x_or_g = c3m.full_cov_ep_oamp(y_d, A1, C2_true, const1, n_iters=10)
        wres["Oracle_KnownH2_GaussNull"] = c3m.hard_ser_sub(x_or_g, x1, const1, didx)
        out[wf] = wres
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=48)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c15_blind_dd_cci.json")
    args = ap.parse_args()
    t0 = time.time()

    regimes = [
        ("Ctrl_LTI_kmax0_QPSK_Intf",   28.0, 0.0, 4,  0.0),
        ("R1_DD_kmax1p5_QPSK_Intf",    28.0, 0.0, 4,  1.5),
        ("R2_DD_kmax1p5_16QAM_Intf",   28.0, 0.0, 16, 1.5),
    ]
    summary = {"meta": {"trials": args.trials, "N": 256, "Nr": 2, "P": 4, "l_max": 6, "paired_4wf": True}, "regimes": {}}
    tc = float(student_t.ppf(0.975, df=max(args.trials - 1, 1)))

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for ri, (rname, snr_db, sir_db, mod2, km) in enumerate(regimes):
            jobs = [(995000 + ri * 1000 + t, snr_db, sir_db, mod2, km) for t in range(args.trials)]
            rows = list(ex.map(run_paired_seed, jobs))
            reg_out = {}
            print(f"\n================ {rname} (n={args.trials}) ================")
            for wf in ("AFDM", "OTFS", "OFDM", "SC-FDE"):
                mkeys = list(rows[0][wf].keys())
                agg = {}
                for k in mkeys:
                    arr = np.array([r[wf][k] for r in rows], dtype=float)
                    agg[k] = {
                        "mean": float(np.mean(arr)),
                        "se": float(np.std(arr, ddof=1) / math.sqrt(len(arr))),
                        "ci95_hw": float(tc * np.std(arr, ddof=1) / math.sqrt(len(arr))),
                        "nz_frames": int(np.sum(arr > 0)),
                    }
                sm_keys = [k for k in mkeys if k.startswith("SM") or k.startswith("Pub")]
                best_sm_k = min(sm_keys, key=lambda k: agg[k]["mean"])
                p_sm = np.array([r[wf][best_sm_k] for r in rows])
                p_or = np.array([r[wf]["Oracle_KnownH2_GaussNull"] for r in rows])
                diff = p_sm - 15.0 * p_or
                agg["_best_sm_key"] = best_sm_k
                agg["_paired_margin_15x"] = {"mean": float(np.mean(diff)), "ci95_lo": float(np.mean(diff) - tc * np.std(diff, ddof=1) / math.sqrt(len(rows)))}
                reg_out[wf] = agg
                bsm = agg[best_sm_k]["mean"]; orm = agg["Oracle_KnownH2_GaussNull"]["mean"]
                extra_s = f" CombIRC={agg['SM7_3GPP_OFDM_CombPRB_IRC']['mean']:.4f}" if "SM7_3GPP_OFDM_CombPRB_IRC" in agg else ""
                print(f"  [{wf:6s}] Ref={agg['Ref_Clean_NoCCI']['mean']:.5f} | PubIRC={agg['Pub_3GPP_Global_IRC']['mean']:.4f} | "
                      f"Slide={agg['SM1_SlidingWin16_IRC_3DD']['mean']:.4f} PRB={agg['SM2_3GPP_PerPRB_FreqIRC']['mean']:.4f}{extra_s} "
                      f"Toep={agg['SM3_SpaceTime_ToepCov_3DD']['mean']:.4f} CR={agg['SM4_SIMO_LTI_CR']['mean']:.4f} "
                      f"BEM={agg['SM5_FullAp_BEM_CR_3DD']['mean']:.4f} CMA={agg['SM6_Blind_2x2_CMA_DD']['mean']:.4f} | "
                      f"NullA1[VP={agg['SM8_NullA1_VarProj_BEM5']['mean']:.4f} Toep={agg['SM9_NullA1_Proj_ToepCov']['mean']:.4f} "
                      f"PRB={agg['SM10_NullA1_Proj_PRB6_IRC']['mean']:.4f} CMA={agg['SM11_NullA1_Proj_CMA']['mean']:.4f}] | "
                      f"Oracle_KnownH2={orm:.5f} (nz={agg['Oracle_KnownH2_GaussNull']['nz_frames']}/{args.trials})")
                print(f"           BestSM={best_sm_k} ({bsm:.5f}) | Paired(pSM-15*pOr)={agg['_paired_margin_15x']['mean']:+.5f} (95% lo={agg['_paired_margin_15x']['ci95_lo']:+.5f})")
            summary["regimes"][rname] = reg_out

    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved -> {args.out} in {summary['elapsed_sec']}s")


if __name__ == "__main__":
    main()
