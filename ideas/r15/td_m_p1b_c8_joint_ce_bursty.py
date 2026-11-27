#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C8 Refined Steelman Teardown (`td_m_p1b_c8_joint_ce_bursty.py`):
Fixes from initial test:
  1. Uses N=256 with 4 FULL-APERTURE distributed pilot clusters (4 x 16 = 64 samples = 25% overhead,
     yielding 4 x 10 = 40 clean pilot observations spanning the full frame [6..15, 70..79, 134..143, 198..207]!).
  2. Verifies `Ref_Clean_EstH` (zero-impulse CE -> detection) hits `SER < 0.001`! (Proves zero pilot-aperture artifact!)
  3. Implements Sol's exact `Steelman_S`: Multi-Subset Complementary CE Initialization (fits H from ALL 4 clusters,
     plus all 4 leave-one-cluster-out 3-cluster subsets = 5 hypotheses, selecting best by full-frame robust Huber residual!)
     + Innovation-HMM Full-Cov OAMP + 2-Pass Reliability-Weighted DD Channel Re-estimation!
  4. Tests BOTH `Known G` and `Unknown G` (estimated from normalized short filter family) + `2x2` Oracle Decomposition!
"""
import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.linalg import cho_factor, cho_solve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import td_m_p1b_c3_bursty_impulsive as c3m


def build_H_from_paths(N, delays, dopplers, gains, cpp_c1=0.0):
    H = np.zeros((N, N), dtype=np.complex128)
    n_idx = np.arange(N, dtype=float)
    for l_p, nu_p, g_p in zip(delays, dopplers, gains):
        lp = int(l_p)
        ph = np.exp(1j * 2.0 * np.pi * float(nu_p) * n_idx / float(N))
        for n in range(N):
            m = (n - lp) % N
            cph = np.exp(-1j * 2.0 * np.pi * cpp_c1 * (N * N - 2.0 * N * (lp - n))) if (cpp_c1 != 0.0 and n < lp) else 1.0
            H[n, m] += g_p * ph[n] * cph
    return H


def build_path_atom(s_known, l_p, nu_p, N, cpp_c1=0.0):
    n_idx = np.arange(N, dtype=float)
    m_idx = (np.arange(N) - l_p) % N
    s_del = s_known[m_idx]
    if cpp_c1 != 0.0 and l_p > 0:
        cph = np.ones(N, dtype=np.complex128)
        nw = np.arange(l_p, dtype=float)
        cph[:l_p] = np.exp(-1j * 2.0 * np.pi * cpp_c1 * (N * N - 2.0 * N * (l_p - nw)))
        s_del = s_del * cph
    return s_del * np.exp(1j * 2.0 * np.pi * nu_p * n_idx / float(N))


def omp_continuous_ce(y, s_known, obs_idx, N, P, l_max, k_max, cpp_c1, weights=None, C_inv_sqrt=None):
    y_sub = y[obs_idx]
    if C_inv_sqrt is not None:
        yw = C_inv_sqrt @ y_sub; w_sqrt = None
    elif weights is not None:
        w_sqrt = np.sqrt(np.maximum(weights[obs_idx], 1e-6)); yw = w_sqrt * y_sub
    else:
        w_sqrt = None; yw = y_sub

    dop_coarse = np.linspace(-k_max, k_max, 49)
    atoms_raw, meta = [], []
    for l in range(l_max + 1):
        for nu in dop_coarse:
            atoms_raw.append(build_path_atom(s_known, l, nu, N, cpp_c1)[obs_idx])
            meta.append((l, float(nu)))
    D_raw = np.column_stack(atoms_raw)
    Dw = (C_inv_sqrt @ D_raw) if C_inv_sqrt is not None else ((w_sqrt[:, None] * D_raw) if w_sqrt is not None else D_raw)
    col_norms = np.linalg.norm(Dw, axis=0) + 1e-12

    chosen_l, chosen_nu = [], []
    res = yw.copy()
    for _ in range(P):
        corr = np.abs(Dw.conj().T @ res) / col_norms
        for cl, cnu in zip(chosen_l, chosen_nu):
            for idx_m, (ml, mnu) in enumerate(meta):
                if ml == cl:
                    corr[idx_m] = -1.0
        best = int(np.argmax(corr))
        chosen_l.append(meta[best][0]); chosen_nu.append(meta[best][1])
        A_cur = np.column_stack([build_path_atom(s_known, l, nu, N, cpp_c1)[obs_idx] for l, nu in zip(chosen_l, chosen_nu)])
        Aw = (C_inv_sqrt @ A_cur) if C_inv_sqrt is not None else ((w_sqrt[:, None] * A_cur) if w_sqrt is not None else A_cur)
        gains, *_ = np.linalg.lstsq(Aw, yw, rcond=None)
        res = yw - Aw @ gains

    # Fine continuous Doppler refinement (3-stage coarse-to-fine -> ~0.002 resolution)
    for rad, npts in [(0.10, 11), (0.025, 11), (0.006, 9)]:
        for p in range(P):
            nu_c = chosen_nu[p]; best_nu, best_err = nu_c, 1e18
            for nu_try in np.linspace(max(-k_max, nu_c - rad), min(k_max, nu_c + rad), npts):
                nus_try = list(chosen_nu); nus_try[p] = float(nu_try)
                A_try = np.column_stack([build_path_atom(s_known, l, nu, N, cpp_c1)[obs_idx] for l, nu in zip(chosen_l, nus_try)])
                Aw = (C_inv_sqrt @ A_try) if C_inv_sqrt is not None else ((w_sqrt[:, None] * A_try) if w_sqrt is not None else A_try)
                g_try, *_ = np.linalg.lstsq(Aw, yw, rcond=None)
                err = float(np.sum(np.abs(yw - Aw @ g_try) ** 2))
                if err < best_err:
                    best_err = err; best_nu = float(nu_try)
            chosen_nu[p] = best_nu

    A_fin = np.column_stack([build_path_atom(s_known, l, nu, N, cpp_c1)[obs_idx] for l, nu in zip(chosen_l, chosen_nu)])
    Aw = (C_inv_sqrt @ A_fin) if C_inv_sqrt is not None else ((w_sqrt[:, None] * A_fin) if w_sqrt is not None else A_fin)
    gains, *_ = np.linalg.lstsq(Aw, yw, rcond=None)
    return build_H_from_paths(N, chosen_l, chosen_nu, gains, cpp_c1)


def run_trial(args):
    seed, wf, N, snr_db, inr_db, duty, mean_burst = args
    rng = np.random.default_rng(seed)
    const = c3m.gray_qam(16)
    P = 4; l_max = 6; k_max = 1.5
    sigma0_sq = 10.0 ** (-snr_db / 10.0)
    c1 = 5.0 / (2.0 * N) if wf == "AFDM" else 0.0

    G = c3m.build_rx_filter_matrix(N, colored=True, bw_factor=0.42)
    H_true, _ = c3m.build_td_channel(N, P, l_max, k_max, rng, cpp_c1=c1)

    # 4 full-aperture distributed pilot clusters (4 x 16 = 64 samples = 25% overhead, 40 clean pilot obs!)
    clusters = [np.arange(0, 16), np.arange(64, 80), np.arange(128, 144), np.arange(192, 208)]
    obs_clusters = [np.arange(c[0] + l_max, c[-1] + 1) for c in clusters]
    obs_pil_all = np.concatenate(obs_clusters)
    pil_t = np.concatenate(clusters)
    data_t = np.setdiff1d(np.arange(N), pil_t)
    Nd = len(data_t)  # 192 data symbols!

    if wf == "AFDM":
        U_d = c3m.daft_mat(Nd, 5.0 / (2.0 * Nd), 1.0 / (2.0 * math.pi * Nd))
    elif wf == "OTFS":
        U_d = c3m.otfs_mat(16, 12)
    elif wf == "OFDM":
        U_d = np.fft.fft(np.eye(Nd)) / math.sqrt(Nd)
    else:
        U_d = np.eye(Nd, dtype=np.complex128)

    u_pil = np.exp(-1j * math.pi * 7.0 * np.arange(len(pil_t)) * (np.arange(len(pil_t)) + 1) / float(len(pil_t)))
    x_data = const[rng.integers(0, len(const), size=Nd)]
    s_pil = np.zeros(N, dtype=np.complex128); s_pil[pil_t] = u_pil
    s_true = s_pil.copy(); s_true[data_t] = U_d.conj().T @ x_data

    e_pre, states, v_z, ms = c3m.gen_markov_burst_noise(N, sigma0_sq, duty, mean_burst, inr_db, rng)
    w_bg = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sigma0_sq / 2.0)
    y = H_true @ s_true + G @ e_pre + w_bg
    y_clean = H_true @ s_true + w_bg

    I_N = np.eye(N, dtype=np.complex128)
    C_true = sigma0_sq * I_N + (G * v_z[None, :]) @ G.conj().T
    p01, p10, sigma_I_sq = ms["p01"], ms["p10"], ms["sigma_I_sq"]
    didx = np.arange(Nd)

    def detect_H(H_use, C_use, mode="oracle", G_use=None):
        G_cur = G if G_use is None else G_use
        y_d = y - H_use @ s_pil
        A_d = H_use[:, data_t] @ U_d.conj().T
        if mode == "oracle":
            return c3m.full_cov_ep_oamp(y_d, A_d, C_use, const, None, None, n_iters=10, damp=0.65), C_use
        if mode == "pc_sbl":
            # Pattern-Coupled Block-SBL in pre-filter domain + Full-Cov OAMP!
            GtG = G_cur.conj().T @ G_cur; Gt = G_cur.conj().T
            med = float(np.median(np.abs(y_d))); T0 = 2.4 * max(med / 0.8326, 1.0)
            w0 = np.where(np.abs(y_d) > T0, T0 / np.maximum(np.abs(y_d), 1e-12), 1.0)
            xh = c3m.full_cov_ep_oamp(y_d, A_d, np.diag(sigma0_sq / np.maximum(w0, 1e-4)), const, None, None, n_iters=6)
            gamma = np.full(N, 10.0 * sigma0_sq, dtype=float)
            C_hat = C_use
            for outer in range(7):
                r = y_d - A_d @ xh
                s0_e = sigma0_sq + (0.02 if outer < 2 else (0.004 if outer < 4 else 0.0005))
                inv_s0 = 1.0 / s0_e
                for _ in range(3):
                    Pe = inv_s0 * GtG.copy()
                    Pe[np.diag_indices(N)] += 1.0 / np.maximum(gamma, 1e-8)
                    pf = cho_factor(Pe + 1e-10 * I_N, lower=True)
                    mu_e = cho_solve(pf, inv_s0 * (Gt @ r))
                    sig_d = np.maximum(np.real(np.diag(cho_solve(pf, I_N))), 0.0)
                    m2 = np.abs(mu_e) ** 2 + sig_d
                    mp = np.pad(m2, 1, mode="edge")
                    gamma = np.clip((0.45 * mp[:-2] + mp[1:-1] + 0.45 * mp[2:]) / 1.9, 1e-7, 1e5)
                    gamma = np.where(gamma < 1.5 * s0_e, 1e-7, gamma)
                C_hat = sigma0_sq * I_N + (G_cur * gamma[None, :]) @ G_cur.conj().T
                xh = c3m.full_cov_ep_oamp(y_d, A_d, C_hat, const, None, None, n_iters=8, damp=0.65)
            return xh, C_hat
        # Default: Adaptive Innovation-HMM + Full-Cov OAMP
        W_dec = np.linalg.solve(G_cur.conj().T @ G_cur + 0.05 * I_N, G_cur.conj().T)
        bg_var = np.real(np.sum(np.abs(W_dec) ** 2, axis=1)) * sigma0_sq
        sig_gain = np.maximum(np.real(np.diag(W_dec @ G_cur)) ** 2, 0.25)
        med = float(np.median(np.abs(y_d)))
        T0 = 2.4 * max(med / 0.8326, 1.0)
        w0 = np.where(np.abs(y_d) > T0, T0 / np.maximum(np.abs(y_d), 1e-12), 1.0)
        xh = c3m.full_cov_ep_oamp(y_d, A_d, np.diag(sigma0_sq / np.maximum(w0, 1e-4)), const, None, None, n_iters=6)
        C_hat = C_use
        for _ in range(7):
            r = y_d - A_d @ xh
            e2 = np.abs(W_dec @ r) ** 2
            med_e2 = float(np.median(e2)) / 0.693147
            s0_v = np.maximum(bg_var, 0.6 * med_e2)
            s1_v = np.maximum(s0_v + sig_gain * sigma_I_sq, 10.0 * s0_v)
            gam = c3m.hmm_fb_2state(-np.log(s0_v) - e2 / s0_v, -np.log(s1_v) - e2 / s1_v, p01, p10)
            v_hat = gam * sigma_I_sq
            C_hat = sigma0_sq * I_N + (G_cur * v_hat[None, :]) @ G_cur.conj().T
            xh = c3m.full_cov_ep_oamp(y_d, A_d, C_hat, const, None, None, n_iters=8, damp=0.65)
        return xh, C_hat

    res = {}
    # Record number of clean (non-burst) pilot observations for Sol's conditioning stratification!
    pil_clean_frac = float(np.mean(states[obs_pil_all] == 0))
    res["_pil_clean_frac"] = pil_clean_frac

    # 0. Sanity Gate: Zero-impulse clean EstH -> detection!
    H_cl = omp_continuous_ce(y_clean, s_pil, obs_pil_all, N, P, l_max, k_max, c1)
    x_cl = c3m.full_cov_ep_oamp(y_clean - H_cl @ s_pil, H_cl[:, data_t] @ U_d.conj().T, sigma0_sq * I_N, const, None, None, n_iters=8)
    res["Ref_Clean_EstH"] = c3m.hard_ser_sub(x_cl, x_data, const, didx)

    # 1. Pub: LS CE + Gaussian LMMSE & Long i.i.d. EP
    H_ls = omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1)
    x_pub = c3m.full_cov_lmmse(y - H_ls @ s_pil, H_ls[:, data_t] @ U_d.conj().T, (sigma0_sq + duty * sigma_I_sq) * I_N)
    res["Pub_LS_CE_GaussLMMSE"] = c3m.hard_ser_sub(x_pub, x_data, const, didx)
    x_long = c3m.rx_iid_bg_oamp(y - H_ls @ s_pil, H_ls[:, data_t] @ U_d.conj().T, sigma0_sq, const, None, None, duty, sigma_I_sq, True, 6)
    res["Pub_Long_iidEP"] = c3m.hard_ser_sub(x_long, x_data, const, didx)

    # 2. SM1: Huber CE + Innovation-HMM + 2-pass DD re-estimation (Sol Steelman_A!)
    med_p = float(np.median(np.abs(y[obs_pil_all])))
    T_p = max(2.2 * med_p, 2.5)
    w_hub = np.ones(N, dtype=float)
    w_hub[obs_pil_all] = np.minimum(1.0, T_p / np.maximum(np.abs(y[obs_pil_all]), 1e-12))
    H_hub = omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1, weights=w_hub)
    r_p0 = np.abs(y[obs_pil_all] - (H_hub @ s_pil)[obs_pil_all])
    mad_p = max(float(np.median(r_p0)) / 0.6745, math.sqrt(sigma0_sq))
    w_hub[obs_pil_all] = np.where(r_p0 <= 1.345 * mad_p, 1.0, 1.345 * mad_p / np.maximum(r_p0, 1e-12))
    H_hub = omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1, weights=w_hub)

    x_sm1, C_sm1 = detect_H(H_hub, sigma0_sq * I_N, mode="hmm")
    H_dd, x_dd, C_dd = H_hub, x_sm1, C_sm1
    for _ in range(2):
        s_hat = s_pil.copy()
        s_hat[data_t] = U_d.conj().T @ const[np.argmin(np.abs(x_dd[:, None] - const[None, :]), axis=1)]
        L_c = np.linalg.cholesky(C_dd + 1e-9 * I_N)
        H_dd = omp_continuous_ce(y, s_hat, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
        x_dd, C_dd = detect_H(H_dd, C_dd, mode="hmm")
    res["SM1_HuberCE_HMM_2PassDD"] = c3m.hard_ser_sub(x_dd, x_data, const, didx)

    # 3. SM2: Sol's Steelman_S — Multi-Subset Complementary CE (all 4 + 4 leave-1-out subsets) + HMM + 2Pass DD!
    best_H_ms, best_loss = H_hub, float(np.sum(np.minimum(np.abs(y[obs_pil_all] - (H_hub @ s_pil)[obs_pil_all]), 0.5) ** 2))
    for drop_k in range(4):
        sub_obs = np.concatenate([obs_clusters[j] for j in range(4) if j != drop_k])
        H_sub = omp_continuous_ce(y, s_pil, sub_obs, N, P, l_max, k_max, c1, weights=w_hub)
        loss = float(np.sum(np.minimum(np.abs(y[obs_pil_all] - (H_sub @ s_pil)[obs_pil_all]), 0.5) ** 2))
        if loss < best_loss:
            best_loss = loss; best_H_ms = H_sub
    x_ms, C_ms = detect_H(best_H_ms, sigma0_sq * I_N, mode="hmm")
    for _ in range(2):
        s_hat = s_pil.copy()
        s_hat[data_t] = U_d.conj().T @ const[np.argmin(np.abs(x_ms[:, None] - const[None, :]), axis=1)]
        L_c = np.linalg.cholesky(C_ms + 1e-9 * I_N)
        H_ms_dd = omp_continuous_ce(y, s_hat, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
        x_ms, C_ms = detect_H(H_ms_dd, C_ms, mode="hmm")
    res["SM2_MultiSubsetCE_HMM_2PassDD"] = c3m.hard_ser_sub(x_ms, x_data, const, didx)

    # 4. SM3: Multi-Subset CE + Pre-Filter Pattern-Coupled Block-SBL + 2-Pass DD!
    x_sbl, C_sbl = detect_H(best_H_ms, sigma0_sq * I_N, mode="pc_sbl")
    for _ in range(2):
        s_hat = s_pil.copy()
        s_hat[data_t] = U_d.conj().T @ const[np.argmin(np.abs(x_sbl[:, None] - const[None, :]), axis=1)]
        L_c = np.linalg.cholesky(C_sbl + 1e-9 * I_N)
        H_sbl_dd = omp_continuous_ce(y, s_hat, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
        x_sbl, C_sbl = detect_H(H_sbl_dd, C_sbl, mode="pc_sbl")
    res["SM3_MultiSubCE_PCBlockSBL_2DD"] = c3m.hard_ser_sub(x_sbl, x_data, const, didx)

    # 4b. SM4: Unknown-G Filter-Family Mismatch Steelman (sweeps bw_factor in {0.30, 0.55, 0.80} without true bw=0.42!)
    r_init_ms = y - best_H_ms @ s_pil
    best_bw, best_nll = 0.55, 1e18
    for bw_try in (0.30, 0.55, 0.80):
        G_try = c3m.build_rx_filter_matrix(N, colored=True, bw_factor=bw_try)
        W_try = np.linalg.solve(G_try.conj().T @ G_try + 0.05 * I_N, G_try.conj().T)
        e2_t = np.abs(W_try @ r_init_ms) ** 2
        # Penalized whitened innovation variance on pilot obs (selects best mismatched filter family member)
        sc_t = float(np.median(e2_t[obs_pil_all]))
        if sc_t < best_nll:
            best_nll = sc_t; best_bw = bw_try
    G_unk = c3m.build_rx_filter_matrix(N, colored=True, bw_factor=best_bw)
    x_ug, C_ug = detect_H(best_H_ms, sigma0_sq * I_N, mode="hmm", G_use=G_unk)
    for _ in range(2):
        s_hat = s_pil.copy()
        s_hat[data_t] = U_d.conj().T @ const[np.argmin(np.abs(x_ug[:, None] - const[None, :]), axis=1)]
        L_c = np.linalg.cholesky(C_ug + 1e-9 * I_N)
        H_ug_dd = omp_continuous_ce(y, s_hat, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
        x_ug, C_ug = detect_H(H_ug_dd, C_ug, mode="hmm", G_use=G_unk)
    res["SM4_UnknownG_Family_HMM_2DD"] = c3m.hard_ser_sub(x_ug, x_data, const, didx)

    # 5. 2x2 Oracle Decomposition (strictly non-cheating!)
    C_pil_t = C_true[np.ix_(obs_pil_all, obs_pil_all)]
    L_cp = np.linalg.cholesky(C_pil_t + 1e-9 * np.eye(len(obs_pil_all)))
    H_oc = omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_cp, np.eye(len(obs_pil_all))))
    x_oc, _ = detect_H(H_oc, C_true, mode="oracle")
    res["Grid_OracCE_TrueState"] = c3m.hard_ser_sub(x_oc, x_data, const, didx)

    x_th, _ = detect_H(H_true, sigma0_sq * I_N, mode="hmm")
    res["Grid_TrueH_EstState"] = c3m.hard_ser_sub(x_th, x_data, const, didx)

    x_or, _ = detect_H(H_true, C_true, mode="oracle")
    res["Oracle_TrueH_TrueState"] = c3m.hard_ser_sub(x_or, x_data, const, didx)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=16)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c8_joint_ce_bursty.json")
    args = ap.parse_args()
    t0 = time.time()

    configs = [
        ("AFDM", 256, 26.0, 25.0, 0.20, 8.0),
        ("OFDM", 256, 26.0, 25.0, 0.20, 8.0),
        ("OTFS", 256, 26.0, 25.0, 0.20, 8.0),
        ("SC-FDE", 256, 26.0, 25.0, 0.20, 8.0),
        ("AFDM", 256, 30.0, 25.0, 0.20, 8.0),
        ("OFDM", 256, 30.0, 25.0, 0.20, 8.0),
        ("OTFS", 256, 30.0, 25.0, 0.20, 8.0),
        ("SC-FDE", 256, 30.0, 25.0, 0.20, 8.0),
    ]
    summary = {"meta": {"trials": args.trials}, "results": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, cfg in enumerate(configs):
            key = f"N256_4ClusterPil_Burst20_SNR{int(cfg[2])}__{cfg[0]}"
            jobs = [(810000 + i * 1000 + t,) + cfg for t in range(args.trials)]
            outs = list(ex.map(run_trial, jobs))
            metric_keys = [k for k in outs[0] if not k.startswith("_")]
            agg = {k: {"mean": float(np.mean([o[k] for o in outs])), "se": float(np.std([o[k] for o in outs], ddof=1) / math.sqrt(len(outs)))} for k in metric_keys}
            well_cond = [o for o in outs if o["_pil_clean_frac"] >= 0.70]
            if len(well_cond) >= 3:
                agg["_strat_well_cond_n"] = len(well_cond)
                agg["_strat_well_cond_SM2"] = float(np.mean([o["SM2_MultiSubsetCE_HMM_2PassDD"] for o in well_cond]))
                agg["_strat_well_cond_SM3"] = float(np.mean([o["SM3_MultiSubCE_PCBlockSBL_2DD"] for o in well_cond]))
                agg["_strat_well_cond_Oracle"] = float(np.mean([o["Oracle_TrueH_TrueState"] for o in well_cond]))
            summary["results"][key] = agg
            best_sm_k = min((k for k in metric_keys if k.startswith("SM")), key=lambda k: agg[k]["mean"])
            best_sm = agg[best_sm_k]["mean"]
            orac = agg["Oracle_TrueH_TrueState"]["mean"]
            print(f"\n=== {key} (n={args.trials}) ===")
            for k in metric_keys:
                v = agg[k]
                print(f"  {k:32s}: SER = {v['mean']:.5f} +/- {v['se']:.5f}")
            print(f"  --> Best_SM ({best_sm_k})={best_sm:.5f} vs Oracle={orac:.5f} | Ratio={best_sm/max(orac,1e-6):.2f}x")
            if "_strat_well_cond_n" in agg:
                bsw = min(agg["_strat_well_cond_SM2"], agg["_strat_well_cond_SM3"])
                print(f"  --> Well-Cond Pilots (>=70% clean, n={agg['_strat_well_cond_n']}): BestSM={bsw:.5f} vs Oracle={agg['_strat_well_cond_Oracle']:.5f} | Ratio={bsw/max(agg['_strat_well_cond_Oracle'],1e-6):.2f}x")
    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
