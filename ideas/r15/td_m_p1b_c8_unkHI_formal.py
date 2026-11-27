#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate `P-m-15b-01` (`C8-UnkHI`) Formal Paired 4-Waveform Steelman Teardown
(`td_m_p1b_c8_unkHI_formal.py`):
External Asynchronous Multipath-Dispersed Bursty Impulsive Interference (`y = H s + H_I e_imp + w`)
in Doubly-Dispersive Channels (`AFDM / OTFS / OFDM / SC-FDE`).

Physical Motivation & 2023-2026 Literature Anchors:
  In underwater acoustic (snapping shrimp / sonar pulses), V2X/rail (ignition/pantograph arcing), and
  industrial IIoT (motor/welding switching arcs), external bursty impulsive interference arrives through
  its OWN unknown dispersive multipath channel `H_I` (L_I = 7 non-minimum-phase taps, uncalibrable at RX),
  distinct from both the desired doubly-dispersive channel `H` and the calibrated RX LPF `G`:
  - Barka, Alam, Kaddoum, Au, Agba, IEEE TCOM 2026 (10.1109/tcomm.2026.3698821)
  - Zhang & Yin, IEEE WCL 2026 (10.1109/lwc.2026.3693448)
  - Liu, Xu, Wu, IEEE Comm. Letters 2026 (10.1109/lcomm.2025.3638736)
  - Liang, Yu, Ji, Chen, IEEE JOE 2023 (10.1109/joe.2022.3229902)
  - Nassar, Schniter, Evans, IEEE TSP 2013 (arXiv:1306.1851)

Ruthless Full-Strength Steelman Suite (ALL strictly legal, ZERO access to H_I, z_n, or e_imp):
  0. `Ref_Clean_EstH`                 : Zero-impulse CE -> OAMP sanity gate (must be ~0.00000!)
  1. `Pub_Long_iidEP`                 : Published i.i.d. Bernoulli-Gaussian EP (`Long WCL'24`)
  2. `SM1_WhiteNassarFG_3DD`          : Sol's `Nassar TSP'13` Joint `[A_d, I]` Factor-Graph EP + 3-pass soft DD
  3. `SM2_BlindAR6_NassarFG_3DD`      : Blind Yule-Walker `AR(6)` impulse-coloration whitening + `Nassar [A_d, G_hat]` FG + 3-pass DD
  4. `SM3_BandedToeplitz_CovEM_3DD`   : Non-parametric 7-lag PSD-projected empirical burst Toeplitz covariance `R_I`
                                        + 2-state HMM + Full-Cov OAMP + 3-pass DD (captures non-min-phase autocorrelation!)
  5. `SM4_Blind_HI_AltEM_NassarFG_3DD`: Alternating Blind 7-tap `h_I` least-squares identification from inferred `e_hat`
                                        + `Nassar [A_d, H_I_hat]` Joint Factor-Graph EP + 3-pass DD!
Non-Cheating Reference Oracles (NONE ever see the random impulse realization `e_imp`!):
  6. `Diag_TrueH_KnownHI_BlindStateFG`: Knows ONLY `(H, H_I)`, ZERO burst-state truth `z_n` & ZERO `e_imp` -> runs Nassar FG!
  7. `Grid_OracCE_TrueHI_TrueState`   : Unknown `H` (estimated ONLY from 40 pilot obs whitened by `C_true[P,P]`), knows `(H_I, v_z)`.
  8. `Oracle_TrueH_TrueHI_TrueState`  : Knows `(H, H_I, v_z)` variance matrix `C_true = s0 I + H_I diag(v_z) H_I^H` (ZERO `e_imp`!).
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
from scipy.linalg import cho_factor, cho_solve, toeplitz
from scipy.stats import t as student_t

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import td_m_p1b_c3_bursty_impulsive as c3m
import td_m_p1b_c8_joint_ce_bursty as c8
import td_m_p1b_c8_nassar_audit as cn


def build_unknown_HI(N: int, L_I: int, rng: np.random.Generator):
    pdp = np.exp(-0.18 * np.arange(L_I))
    pdp /= np.sum(pdp)
    h_I = (rng.standard_normal(L_I) + 1j * rng.standard_normal(L_I)) * np.sqrt(pdp / 2.0)
    h_I /= max(np.linalg.norm(h_I), 1e-12)
    H_I = np.zeros((N, N), dtype=np.complex128)
    for l in range(L_I):
        for n in range(N):
            H_I[n, (n - l) % N] = h_I[l]
    return H_I, h_I


def est_ar_filter_matrix(r_vec: np.ndarray, N: int, order: int = 6):
    thr = max(2.2 * float(np.median(np.abs(r_vec))), 0.1)
    r_b = np.where(np.abs(r_vec) > thr, r_vec, 0.0)
    if np.sum(np.abs(r_b) ** 2) < 1e-6:
        return np.eye(N, dtype=np.complex128)
    acf = np.array([np.vdot(r_b[:N - k], r_b[k:]) / max(N - k, 1) for k in range(order + 1)], dtype=np.complex128)
    R = toeplitz(acf[:order]) + (0.05 * abs(acf[0]) + 1e-6) * np.eye(order)
    a = np.linalg.solve(R, acf[1:order + 1])
    A_w = np.eye(N, dtype=np.complex128)
    for k in range(1, order + 1):
        for n in range(N):
            A_w[n, (n - k) % N] -= a[k - 1]
    G_hat = np.linalg.inv(A_w)
    G_hat /= max(np.linalg.norm(G_hat[:, 0]), 1e-12)
    return G_hat


def est_banded_psd_toeplitz_cov(r_vec: np.ndarray, gam_state: np.ndarray, sigma0_sq: float, sigma_I_sq: float, N: int, L_lag: int = 7):
    """Non-parametric PSD-projected banded Toeplitz covariance R_I estimated from burst residuals (handles non-min-phase!)."""
    w_b = np.sqrt(np.clip(gam_state, 0.0, 1.0))
    r_b = w_b * r_vec
    denom = max(float(np.sum(w_b ** 2)), 1.0)
    acf = np.zeros(N, dtype=np.complex128)
    for k in range(L_lag):
        if k == 0:
            acf[0] = max(float(np.sum(np.abs(r_b) ** 2)) / denom, sigma0_sq)
        else:
            val = np.vdot(r_b[:N - k], r_b[k:]) / max(denom * (1.0 - k / float(N)), 1.0)
            # Bartlett taper guarantees PSD tendency; explicit FFT spectral clipping guarantees exact PSD!
            taper = 1.0 - k / float(L_lag)
            acf[k] = val * taper
            acf[N - k] = np.conj(val) * taper
    psd = np.maximum(np.real(np.fft.fft(acf)), 1e-4 * float(np.real(acf[0])))
    acf_psd = np.fft.ifft(psd)
    # Normalize unit diagonal so state variance scales it cleanly
    acf_norm = acf_psd / max(float(np.real(acf_psd[0])), 1e-9)
    # Build circulant PSD correlation matrix R_corr
    idx = (np.arange(N)[:, None] - np.arange(N)[None, :]) % N
    R_corr = acf_norm[idx]
    s_diag = np.sqrt(np.maximum(gam_state * sigma_I_sq, 0.0))
    C_hat = sigma0_sq * np.eye(N, dtype=np.complex128) + (s_diag[:, None] * R_corr) * s_diag[None, :]
    return 0.5 * (C_hat + C_hat.conj().T)


def est_blind_hi_from_ehat(r_vec: np.ndarray, e_hat: np.ndarray, N: int, L_I: int = 7):
    """Direct alternating LS estimation of the L_I-tap impulse channel h_I from r_vec ~ conv(e_hat, h_I)."""
    if np.linalg.norm(e_hat) < 1e-4:
        return np.eye(N, dtype=np.complex128)
    E_mat = np.column_stack([np.roll(e_hat, l) for l in range(L_I)])
    h_hat = np.linalg.solve(E_mat.conj().T @ E_mat + 1e-2 * (float(np.mean(np.abs(e_hat) ** 2)) + 1e-4) * np.eye(L_I),
                            E_mat.conj().T @ r_vec)
    nrm = np.linalg.norm(h_hat)
    if nrm < 1e-6:
        return np.eye(N, dtype=np.complex128)
    h_hat /= nrm
    H_hat = np.zeros((N, N), dtype=np.complex128)
    for l in range(L_I):
        for n in range(N):
            H_hat[n, (n - l) % N] = h_hat[l]
    return H_hat


def run_paired_seed(args):
    seed, mod_M, snr_db, inr_db, duty, mean_burst = args
    N = 256; P = 4; l_max = 6; k_max = 1.5; L_I = 7
    rng = np.random.default_rng(seed)
    const = c3m.gray_qam(mod_M)
    sigma0_sq = 10.0 ** (-snr_db / 10.0)
    I_N = np.eye(N, dtype=np.complex128)

    # Paired desired channel + external unknown 7-tap multipath interferer H_I + bursty impulse + noise + data!
    delays = np.sort(rng.choice(np.arange(0, l_max + 1), size=P, replace=False)); delays[0] = 0
    dopplers = rng.uniform(-k_max, k_max, size=P)
    pdp = np.exp(-0.22 * delays); pdp /= np.sum(pdp)
    gains = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) * np.sqrt(pdp / 2.0)
    gains /= max(np.linalg.norm(gains), 1e-12)
    H_I_true, _ = build_unknown_HI(N, L_I, rng)

    clusters = [np.arange(0, 16), np.arange(64, 80), np.arange(128, 144), np.arange(192, 208)]
    obs_clusters = [np.arange(c[0] + l_max, c[-1] + 1) for c in clusters]
    obs_pil_all = np.concatenate(obs_clusters)
    pil_t = np.concatenate(clusters); data_t = np.setdiff1d(np.arange(N), pil_t); Nd = len(data_t); didx = np.arange(Nd)

    u_pil = np.exp(-1j * math.pi * 7.0 * np.arange(len(pil_t)) * (np.arange(len(pil_t)) + 1) / float(len(pil_t)))
    x_data = const[rng.integers(0, len(const), size=Nd)]
    s_pil = np.zeros(N, dtype=np.complex128); s_pil[pil_t] = u_pil

    e_pre, states, v_z, ms = c3m.gen_markov_burst_noise(N, sigma0_sq, duty, mean_burst, inr_db, rng)
    w_bg = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sigma0_sq / 2.0)
    C_true = sigma0_sq * I_N + (H_I_true * v_z[None, :]) @ H_I_true.conj().T
    p01, p10, sigma_I_sq = ms["p01"], ms["p10"], ms["sigma_I_sq"]
    pil_clean_frac = float(np.mean(states[obs_pil_all] == 0))

    U_map = {
        "AFDM": c3m.daft_mat(Nd, 5.0 / (2.0 * Nd), 1.0 / (2.0 * math.pi * Nd)),
        "OTFS": c3m.otfs_mat(16, 12),
        "OFDM": np.fft.fft(np.eye(Nd)) / math.sqrt(Nd),
        "SC-FDE": np.eye(Nd, dtype=np.complex128),
    }

    out = {"_pil_clean_frac": pil_clean_frac}
    for wf in ("AFDM", "OTFS", "OFDM", "SC-FDE"):
        c1 = 5.0 / (2.0 * N) if wf == "AFDM" else 0.0
        H_true = c8.build_H_from_paths(N, delays, dopplers, gains, cpp_c1=c1)
        U_d = U_map[wf]
        assert float(np.max(np.abs(H_true[obs_pil_all, :][:, data_t]))) < 1e-12
        s_true = s_pil.copy(); s_true[data_t] = U_d.conj().T @ x_data
        y = H_true @ s_true + H_I_true @ e_pre + w_bg
        y_cl = H_true @ s_true + w_bg
        A_true = H_true[:, data_t] @ U_d.conj().T

        wres = {}
        # 0. Sanity gate
        H_cl = c8.omp_continuous_ce(y_cl, s_pil, obs_pil_all, N, P, l_max, k_max, c1)
        x_cl = c3m.full_cov_ep_oamp(y_cl - H_cl @ s_pil, H_cl[:, data_t] @ U_d.conj().T, sigma0_sq * I_N, const, None, None, n_iters=8)
        wres["Ref_Clean_EstH"] = c3m.hard_ser_sub(x_cl, x_data, const, didx)

        # 1. Pub: LS CE + Long i.i.d. BG-EP
        H_ls = c8.omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1)
        x_pub = c3m.rx_iid_bg_oamp(y - H_ls @ s_pil, H_ls[:, data_t] @ U_d.conj().T, sigma0_sq, const, None, None, duty, sigma_I_sq, True, 6)
        wres["Pub_Long_iidEP"] = c3m.hard_ser_sub(x_pub, x_data, const, didx)

        # 2. SM1: Sol's Nassar TSP'13 Joint [A_d, I] FG + 3-pass Soft-DD CE
        H_1 = cn.pilot_joint_sparse_ce(y, s_pil, I_N, obs_pil_all, obs_clusters, N, P, l_max, k_max, c1, sigma0_sq, sigma_I_sq)
        x_1, e_1, _, g_1, C_1 = cn.joint_nassar_ep_fg(y - H_1 @ s_pil, H_1[:, data_t] @ U_d.conj().T, I_N, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=12)
        for _ in range(3):
            s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_1
            L_c = np.linalg.cholesky(C_1 + 1e-9 * I_N)
            H_1 = c8.omp_continuous_ce(y, s_soft, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
            x_1, e_1, _, g_1, C_1 = cn.joint_nassar_ep_fg(y - H_1 @ s_pil, H_1[:, data_t] @ U_d.conj().T, I_N, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=12)
        wres["SM1_WhiteNassarFG_3DD"] = c3m.hard_ser_sub(x_1, x_data, const, didx)

        # 3. SM2: Blind Yule-Walker AR(6) Whitening + Nassar [A_d, G_hat] Joint FG + 3-pass Soft-DD
        H_2, x_2, C_2 = H_1.copy(), x_1.copy(), C_1.copy()
        for _ in range(3):
            s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_2
            G_ar = est_ar_filter_matrix(y - H_2 @ s_soft, N, order=6)
            x_2, _, _, _, C_2 = cn.joint_nassar_ep_fg(y - H_2 @ s_pil, H_2[:, data_t] @ U_d.conj().T, G_ar, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=12)
            s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_2
            L_c = np.linalg.cholesky(C_2 + 1e-9 * I_N)
            H_2 = c8.omp_continuous_ce(y, s_soft, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
        wres["SM2_BlindAR6_NassarFG_3DD"] = c3m.hard_ser_sub(x_2, x_data, const, didx)

        # 4. SM3: Non-parametric 7-lag PSD Banded-Toeplitz Covariance EM + HMM + Full-Cov OAMP + 3-pass DD
        H_3, x_3, g_3 = H_1.copy(), x_1.copy(), g_1.copy()
        for _ in range(3):
            s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_3
            r_3 = y - H_3 @ s_soft
            C_3 = est_banded_psd_toeplitz_cov(r_3, g_3, sigma0_sq, sigma_I_sq, N, L_lag=L_I)
            x_3 = c3m.full_cov_ep_oamp(y - H_3 @ s_pil, H_3[:, data_t] @ U_d.conj().T, C_3, const, None, None, n_iters=8, damp=0.65)
            s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_3
            r_3 = y - H_3 @ s_soft
            e2 = np.abs(r_3) ** 2; s0_e = max(sigma0_sq, 0.5 * float(np.median(e2)) / 0.6931)
            s1_e = max(s0_e + sigma_I_sq, 10.0 * s0_e)
            g_3 = c3m.hmm_fb_2state(-np.log(s0_e) - e2 / s0_e, -np.log(s1_e) - e2 / s1_e, p01, p10)
            C_3 = est_banded_psd_toeplitz_cov(r_3, g_3, sigma0_sq, sigma_I_sq, N, L_lag=L_I)
            L_c = np.linalg.cholesky(C_3 + 1e-9 * I_N)
            H_3 = c8.omp_continuous_ce(y, s_soft, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
        x_3 = c3m.full_cov_ep_oamp(y - H_3 @ s_pil, H_3[:, data_t] @ U_d.conj().T, C_3, const, None, None, n_iters=8, damp=0.65)
        wres["SM3_BandedToep_CovEM_3DD"] = c3m.hard_ser_sub(x_3, x_data, const, didx)

        # 5. SM4: Direct Alternating Blind 7-tap h_I LS Identification + Nassar [A_d, H_I_hat] Joint FG + 3-pass DD
        H_4, x_4, e_4 = H_1.copy(), x_1.copy(), e_1.copy()
        for _ in range(3):
            s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_4
            H_I_hat = est_blind_hi_from_ehat(y - H_4 @ s_soft, e_4, N, L_I=L_I)
            x_4, e_4, _, _, C_4 = cn.joint_nassar_ep_fg(y - H_4 @ s_pil, H_4[:, data_t] @ U_d.conj().T, H_I_hat, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=12)
            s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_4
            L_c = np.linalg.cholesky(C_4 + 1e-9 * I_N)
            H_4 = c8.omp_continuous_ce(y, s_soft, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
        wres["SM4_BlindHI_AltEM_FG_3DD"] = c3m.hard_ser_sub(x_4, x_data, const, didx)

        # 6. Non-Cheating Oracles (ZERO impulse realization e_imp!)
        x_bs, _, _, _, _ = cn.joint_nassar_ep_fg(y - H_true @ s_pil, A_true, H_I_true, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=14)
        wres["Diag_TrueH_KnownHI_BlindFG"] = c3m.hard_ser_sub(x_bs, x_data, const, didx)

        C_pil_t = C_true[np.ix_(obs_pil_all, obs_pil_all)]
        L_cp = np.linalg.cholesky(C_pil_t + 1e-9 * np.eye(len(obs_pil_all)))
        H_oc = c8.omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_cp, np.eye(len(obs_pil_all))))
        x_oc = c3m.full_cov_ep_oamp(y - H_oc @ s_pil, H_oc[:, data_t] @ U_d.conj().T, C_true, const, None, None, n_iters=10, damp=0.65)
        wres["Grid_OracCE_TrueHI_TrueSt"] = c3m.hard_ser_sub(x_oc, x_data, const, didx)

        x_or = c3m.full_cov_ep_oamp(y - H_true @ s_pil, A_true, C_true, const, None, None, n_iters=10, damp=0.65)
        wres["Oracle_TrueH_TrueHI_TrueSt"] = c3m.hard_ser_sub(x_or, x_data, const, didx)
        out[wf] = wres
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=48)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c8_unkHI_formal.json")
    args = ap.parse_args()
    t0 = time.time()

    regimes = [
        ("R1_UnkHI_16QAM_30dB_D15_INR22", 16, 30.0, 22.0, 0.15, 6.0),
        ("R2_UnkHI_16QAM_30dB_D20_INR25", 16, 30.0, 25.0, 0.20, 8.0),
        ("R3_UnkHI_64QAM_35dB_D15_INR22", 64, 35.0, 22.0, 0.15, 6.0),
    ]
    summary = {"meta": {"trials": args.trials, "paired_4wf": True, "L_I": 7}, "regimes": {}}
    tc = float(student_t.ppf(0.975, df=max(args.trials - 1, 1)))

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for ri, (rname, mod_M, snr_db, inr_db, duty, mb) in enumerate(regimes):
            jobs = [(950000 + ri * 1000 + t, mod_M, snr_db, inr_db, duty, mb) for t in range(args.trials)]
            rows = list(ex.map(run_paired_seed, jobs))
            reg_out = {}
            afdm_or = np.array([r["AFDM"]["Oracle_TrueH_TrueHI_TrueSt"] for r in rows])
            afdm_bs = np.array([r["AFDM"]["Diag_TrueH_KnownHI_BlindFG"] for r in rows])
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
                sm_keys = [k for k in mkeys if k.startswith("SM")]
                best_sm_k = min(sm_keys, key=lambda k: agg[k]["mean"])
                p_sm = np.array([r[wf][best_sm_k] for r in rows])
                p_or = np.array([r[wf]["Oracle_TrueH_TrueHI_TrueSt"] for r in rows])
                d_intra = p_sm - 15.0 * p_or
                d_bs = p_sm - 15.0 * np.array([r[wf]["Diag_TrueH_KnownHI_BlindFG"] for r in rows])
                d_af = p_sm - 15.0 * afdm_or
                agg["_best_sm_key"] = best_sm_k
                agg["_paired_margin_15x_Oracle"] = {"mean": float(np.mean(d_intra)), "ci95_lo": float(np.mean(d_intra) - tc * np.std(d_intra, ddof=1) / math.sqrt(len(rows)))}
                agg["_paired_margin_15x_BlindFG"] = {"mean": float(np.mean(d_bs)), "ci95_lo": float(np.mean(d_bs) - tc * np.std(d_bs, ddof=1) / math.sqrt(len(rows)))}
                agg["_paired_margin_15x_AFDM_Oracle"] = {"mean": float(np.mean(d_af)), "ci95_lo": float(np.mean(d_af) - tc * np.std(d_af, ddof=1) / math.sqrt(len(rows)))}
                wc = [r for r in rows if r["_pil_clean_frac"] >= 0.70]
                agg["_wc_n"] = len(wc)
                agg["_wc_BestSM"] = float(np.mean([r[wf][best_sm_k] for r in wc]))
                agg["_wc_Oracle"] = float(np.mean([r[wf]["Oracle_TrueH_TrueHI_TrueSt"] for r in wc]))
                reg_out[wf] = agg
                bsm = agg[best_sm_k]["mean"]; orm = agg["Oracle_TrueH_TrueHI_TrueSt"]["mean"]
                print(f"  [{wf:6s}] Ref={agg['Ref_Clean_EstH']['mean']:.5f} | Pub={agg['Pub_Long_iidEP']['mean']:.4f} | "
                      f"SM1={agg['SM1_WhiteNassarFG_3DD']['mean']:.4f} SM2_AR6={agg['SM2_BlindAR6_NassarFG_3DD']['mean']:.4f} "
                      f"SM3_Toep={agg['SM3_BandedToep_CovEM_3DD']['mean']:.4f} SM4_AltHI={agg['SM4_BlindHI_AltEM_FG_3DD']['mean']:.4f} | "
                      f"BlindFG={agg['Diag_TrueH_KnownHI_BlindFG']['mean']:.5f} | OracCE={agg['Grid_OracCE_TrueHI_TrueSt']['mean']:.5f} | "
                      f"Oracle={orm:.5f} (nz={agg['Oracle_TrueH_TrueHI_TrueSt']['nz_frames']}/{args.trials})")
                print(f"           BestSM={best_sm_k} ({bsm:.5f}) | Ratio={bsm/max(orm,1e-6):.1f}x | "
                      f"Paired(pSM-15*pOr)={agg['_paired_margin_15x_Oracle']['mean']:+.5f} (95% lo={agg['_paired_margin_15x_Oracle']['ci95_lo']:+.5f}) | "
                      f"WC(n={len(wc)}): {agg['_wc_BestSM']:.5f} vs {agg['_wc_Oracle']:.5f}")
            summary["regimes"][rname] = reg_out

    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved -> {args.out} in {summary['elapsed_sec']}s")


if __name__ == "__main__":
    main()
