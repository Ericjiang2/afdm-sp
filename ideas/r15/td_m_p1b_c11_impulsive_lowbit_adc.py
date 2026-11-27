#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C11 Brand-New Probe (`td_m_p1b_c11_impulsive_lowbit_adc.py`):
Bursty Receive-Filter-Colored Impulsive Noise x 2-3 Bit Low-Resolution ADC Rail-Saturation Ambiguity
in Doubly-Dispersive Systems (AFDM / OTFS / SC-FDE, U2 Non-Gaussian + Quantization Cascade!).

Literature Anchors (2024-2026):
  - Mehrotra, Srivastava, Jagannatham, Hanzo, IEEE TCOM 2025 (10.1109/tcomm.2024.3502682): Low-Res ADC OTFS
  - Barka, Alam, Kaddoum, Au, Agba, IEEE TCOM 2026 (10.1109/tcomm.2026.3698821): Bursty Impulsive Noise
  - Sui, Liu, Guan, Yang, IEEE TCOM 2026 (10.1109/tcomm.2026.3701879): Low-Res ADC / HWI in AFDM

Physical Paradox (Rail-Saturation Ambiguity!):
  Consider a low-cost UWA / V2X / industrial doubly-dispersive receiver with a 2-bit or 3-bit ADC hit by
  bursty receive-filter-colored impulsive noise (duty 15-20%, burst len 6-8, INR +25 dB):
      q = Q_b( g_agc * (H x + G e_pre + w_bg) )
  1) Standard RMS AGC (`Pub_RMSAGC_AQNM`): RMS is inflated by +12 dB from impulsive bursts -> quantizer step
     expands by 4x -> clean samples collapse into inner quantization deadzone!
  2) Robust MAD/Percentile AGC + Gaussian Probit (`SM1_RobAGC_GaussProbit`): sets step to clean signal RMS,
     so the ADC clips impulses to the outer rails (+/- V_max). BUT Gaussian Probit mistakes every impulsive rail
     hit for a GENUINE high-PAPR clean signal peak (pulling H x wildly toward +/- V_max)!
  3) Rail-Blanking + Interior Probit (`SM2_RailBlank_Probit`): erases ALL saturated rail samples -> throws away
     BOTH impulsive rail hits AND genuine high-PAPR clean signal peaks (15-25% of clean AFDM/OTFS samples)!
  4) Robust AGC + Joint Heavy-Tailed/BG-HMM Probit (`SM3_RobAGC_BG_HMM_Probit`): uses 2-state Markov HMM on
     Probit rail/residual surprises to distinguish contiguous impulsive bursts from isolated clean peaks!
  5) Non-Cheating Same-Hardware Oracle (`Oracle_SameQuant_TrueBurstState`): knows exact binary burst state z_n
     (using exact colored covariance C_z inside Probit — NEVER subtracting noise realization e_pre!) on the
     EXACT SAME 2-bit / 3-bit quantized samples!
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
from scipy.special import ndtr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import td_m_p1b_c3_bursty_impulsive as c3m


def quantize_real(z, n_bits, step):
    L = 1 << n_bits
    edges = (np.arange(1, L, dtype=float) - L / 2.0) * step
    midpts = (np.arange(L, dtype=float) - (L - 1) / 2.0) * step
    idx = np.digitize(z, edges)
    q = midpts[idx]
    all_edges = np.concatenate(([-1e9], edges, [1e9]))
    is_rail = (idx == 0) | (idx == L - 1)
    return q, all_edges[idx], all_edges[idx + 1], is_rail


def trunc_normal_moments(mu, var, lo, hi):
    sd = np.sqrt(np.maximum(var, 1e-12))
    a = (lo - mu) / sd; b = (hi - mu) / sd
    flip = a > 3.5
    aw = np.where(flip, -b, a); bw = np.where(flip, -a, b)
    Z = ndtr(bw) - ndtr(aw)
    inv_s2p = 0.3989422804014327
    pa = inv_s2p * np.exp(-0.5 * np.minimum(aw ** 2, 700.0))
    pb = inv_s2p * np.exp(-0.5 * np.minimum(bw ** 2, 700.0))
    safe = Z > 1e-11
    Zs = np.where(safe, Z, 1.0)
    ms = np.where(safe, (pa - pb) / Zs, 0.0)
    apa = np.where(np.abs(aw) > 1e4, 0.0, aw * pa); bpb = np.where(np.abs(bw) > 1e4, 0.0, bw * pb)
    vs = np.where(safe, 1.0 + (apa - bpb) / Zs - ms ** 2, 0.05)
    tm = np.where(bw < -3.0, bw - 1.0 / np.maximum(-bw, 1.0), 0.5 * (np.clip(aw, -10, 10) + np.clip(bw, -10, 10)))
    tv = np.where(bw < -3.0, 1.0 / np.maximum(bw ** 2, 1.0), 0.05)
    mw = np.where(safe, ms, tm); vw = np.clip(np.where(safe, vs, tv), 1e-6, 1.5)
    return mu + sd * np.where(flip, -mw, mw), var * vw


def c2r_v(z): return np.concatenate([np.real(z), np.imag(z)])
def r2c_v(zr): n = len(zr) // 2; return zr[:n] + 1j * zr[n:]
def c2r_m(A): Ar, Ai = np.real(A), np.imag(A); return np.block([[Ar, -Ai], [Ai, Ar]])


def probit_weighted_ep(lo_r, hi_r, Ar, v_noise_r, const, n_newton=10, n_ep=5):
    """Exact Convex Newton Probit + Discrete QAM EP with per-sample variance vector v_noise_r!"""
    M_r, Nx2 = Ar.shape; N = Nx2 // 2
    I_u = np.eye(Nx2, dtype=float)
    p_prec = np.full(Nx2, 2.0, dtype=float)
    p_mean = np.zeros(Nx2, dtype=float)
    u = np.zeros(Nx2, dtype=float)

    def nlp(uv):
        mu = Ar @ uv; sd = np.sqrt(v_noise_r)
        a = (lo_r - mu) / sd; b = (hi_r - mu) / sd
        flip = a > 3.5; aw = np.where(flip, -b, a); bw = np.where(flip, -a, b)
        diff = ndtr(bw) - ndtr(aw)
        lp = np.where(diff > 1e-15, np.log(np.maximum(diff, 1e-300)),
                      -0.5 * (bw ** 2) - np.log(np.maximum(-bw, 1.0) * math.sqrt(2.0 * math.pi)))
        return float(-np.sum(lp) + 0.5 * np.sum(p_prec * ((uv - p_mean) ** 2)))

    for _ in range(n_newton):
        mu = Ar @ u
        ez, vz = trunc_normal_moments(mu, v_noise_r, lo_r, hi_r)
        g_mu = (mu - ez) / v_noise_r
        h_mu = np.clip((1.0 - vz / v_noise_r) / v_noise_r, 1e-9, 1e5)
        grad = Ar.T @ g_mu + p_prec * (u - p_mean)
        H_m = Ar.T @ (h_mu[:, None] * Ar) + np.diag(p_prec) + 1e-6 * I_u
        d = -cho_solve(cho_factor(H_m, lower=True), grad)
        f0 = nlp(u); al = 1.0
        for _ in range(6):
            if nlp(u + al * d) <= f0 + 1e-5:
                break
            al *= 0.5
        u = u + al * d
        if np.linalg.norm(al * d) < 1e-4:
            break

    xc = r2c_v(u)
    for _ in range(n_ep):
        mu = Ar @ u
        ez, vz = trunc_normal_moments(mu, v_noise_r, lo_r, hi_r)
        h_mu = np.clip((1.0 - vz / v_noise_r) / v_noise_r, 1e-9, 1e5)
        H_m = Ar.T @ (h_mu[:, None] * Ar) + np.diag(p_prec) + 1e-6 * I_u
        hf = cho_factor(H_m, lower=True)
        vp = np.maximum(np.diag(cho_solve(hf, I_u)), 1e-6)
        ge = np.maximum(1.0 / vp - p_prec, 1e-4)
        he = u / vp - p_prec * p_mean
        ve = 1.0 / ge
        rc = r2c_v(he * ve); vc = ve[:N] + ve[N:]
        xc, vhc = c3m.qam_mmse_denoise(rc, vc, const)
        vhr = np.maximum(np.concatenate([vhc, vhc]) * 0.5, 1e-3)
        gn = 1.0 / vhr - ge; hn = c2r_v(xc) / vhr - he
        val = gn > 1e-3
        p_prec = np.where(val, 0.6 * np.clip(gn, 1e-3, 1e3) + 0.4 * p_prec, p_prec)
        p_mean = np.where(val, (0.6 * hn + 0.4 * p_prec * p_mean) / p_prec, p_mean)
        for _ in range(2):
            mu = Ar @ u
            ez, vz = trunc_normal_moments(mu, v_noise_r, lo_r, hi_r)
            g_mu = (mu - ez) / v_noise_r
            h_mu = np.clip((1.0 - vz / v_noise_r) / v_noise_r, 1e-9, 1e5)
            grad = Ar.T @ g_mu + p_prec * (u - p_mean)
            H_m = Ar.T @ (h_mu[:, None] * Ar) + np.diag(p_prec) + 1e-6 * I_u
            d = -cho_solve(cho_factor(H_m, lower=True), grad)
            u = u + 0.7 * d
    return r2c_v(u)


def probit_colored_oracle(lo_r, hi_r, Ar, Gr, v_z_r, sigma0_r_sq, const):
    """
    NON-CHEATING Same-Hardware Colored-Noise Probit Oracle:
    Knows exact binary burst state v_z -> models y = A x + G e + w inside Probit by JOINTLY marginalizing/estimating
    only the active burst columns of G (exact pre-filter burst subspace!), NEVER subtracting the noise realization e!
    """
    active = v_z_r > 1e-6
    M_r, Nx2 = Ar.shape; N = Nx2 // 2
    if not np.any(active):
        return probit_weighted_ep(lo_r, hi_r, Ar, np.full(M_r, sigma0_r_sq), const, 10, 5)
    G_act = Gr[:, active]
    v_act = v_z_r[active]
    A_aug = np.hstack([Ar, G_act])
    Ka = G_act.shape[1]
    dim = Nx2 + Ka
    I_d = np.eye(dim, dtype=float)
    p_prec = np.full(dim, 2.0, dtype=float)
    p_prec[Nx2:] = 1.0 / np.maximum(v_act, 1e-6)
    p_mean = np.zeros(dim, dtype=float)
    u = np.zeros(dim, dtype=float)
    v_n = np.full(M_r, sigma0_r_sq, dtype=float)

    def nlp(uv):
        mu = A_aug @ uv; sd = np.sqrt(v_n)
        a = (lo_r - mu) / sd; b = (hi_r - mu) / sd
        flip = a > 3.5; aw = np.where(flip, -b, a); bw = np.where(flip, -a, b)
        diff = ndtr(bw) - ndtr(aw)
        lp = np.where(diff > 1e-15, np.log(np.maximum(diff, 1e-300)),
                      -0.5 * (bw ** 2) - np.log(np.maximum(-bw, 1.0) * math.sqrt(2.0 * math.pi)))
        return float(-np.sum(lp) + 0.5 * np.sum(p_prec * ((uv - p_mean) ** 2)))

    for _ in range(12):
        mu = A_aug @ u
        ez, vz = trunc_normal_moments(mu, v_n, lo_r, hi_r)
        g_mu = (mu - ez) / v_n
        h_mu = np.clip((1.0 - vz / v_n) / v_n, 1e-8, 1e5)
        grad = A_aug.T @ g_mu + p_prec * (u - p_mean)
        H_m = A_aug.T @ (h_mu[:, None] * A_aug) + np.diag(p_prec) + 1e-5 * I_d
        d = -cho_solve(cho_factor(H_m, lower=True), grad)
        f0 = nlp(u); al = 1.0
        for _ in range(6):
            if nlp(u + al * d) <= f0 + 1e-5:
                break
            al *= 0.5
        u = u + al * d
        if np.linalg.norm(al * d) < 1e-4:
            break

    # Discrete QAM EP on x block
    for _ in range(5):
        mu = A_aug @ u
        ez, vz = trunc_normal_moments(mu, v_n, lo_r, hi_r)
        h_mu = np.clip((1.0 - vz / v_n) / v_n, 1e-8, 1e5)
        H_m = A_aug.T @ (h_mu[:, None] * A_aug) + np.diag(p_prec) + 1e-5 * I_d
        hf = cho_factor(H_m, lower=True)
        vp = np.maximum(np.diag(cho_solve(hf, I_d[:, :Nx2])[:Nx2, :]), 1e-6)
        ge = np.maximum(1.0 / vp - p_prec[:Nx2], 1e-4)
        he = u[:Nx2] / vp - p_prec[:Nx2] * p_mean[:Nx2]
        ve = 1.0 / ge
        rc = r2c_v(he * ve); vc = ve[:N] + ve[N:]
        xc, vhc = c3m.qam_mmse_denoise(rc, vc, const)
        vhr = np.maximum(np.concatenate([vhc, vhc]) * 0.5, 1e-3)
        gn = 1.0 / vhr - ge; hn = c2r_v(xc) / vhr - he
        val = gn > 1e-3
        p_prec[:Nx2] = np.where(val, 0.6 * np.clip(gn, 1e-3, 1e3) + 0.4 * p_prec[:Nx2], p_prec[:Nx2])
        p_mean[:Nx2] = np.where(val, (0.6 * hn + 0.4 * p_prec[:Nx2] * p_mean[:Nx2]) / p_prec[:Nx2], p_mean[:Nx2])
        for _ in range(2):
            mu = A_aug @ u
            ez, vz = trunc_normal_moments(mu, v_n, lo_r, hi_r)
            g_mu = (mu - ez) / v_n
            h_mu = np.clip((1.0 - vz / v_n) / v_n, 1e-8, 1e5)
            grad = A_aug.T @ g_mu + p_prec * (u - p_mean)
            H_m = A_aug.T @ (h_mu[:, None] * A_aug) + np.diag(p_prec) + 1e-5 * I_d
            d = -cho_solve(cho_factor(H_m, lower=True), grad)
            u = u + 0.7 * d
    return r2c_v(u[:Nx2])


def run_trial(args):
    seed, wf, N, Nr, n_bits, snr_db, inr_db, duty, mean_burst = args
    rng = np.random.default_rng(seed)
    const = c3m.gray_qam(16)
    sigma0_sq = 10.0 ** (-snr_db / 10.0)
    k_max = 1.5; l_max = 5
    c1 = 5.0 / (2.0 * N) if wf == "AFDM" else 0.0
    U = c3m.daft_mat(N, c1, 1.0 / (2.0 * math.pi * N)) if wf == "AFDM" else (c3m.otfs_mat(8, N // 8) if wf == "OTFS" else np.eye(N, dtype=np.complex128))
    G1 = c3m.build_rx_filter_matrix(N, colored=True, bw_factor=0.42)

    # SIMO Nr=2 antennas receiving same external bursty impulsive environment (correlated burst epoch across antennas!)
    H_list = [c3m.build_td_channel(N, 4, l_max, k_max, rng, cpp_c1=c1)[0] for _ in range(Nr)]
    A_full = np.vstack([H @ U.conj().T for H in H_list])  # (Nr*N) x N
    G_full = np.kron(np.eye(Nr, dtype=np.complex128), G1)

    x_true = const[rng.integers(0, len(const), size=N)]
    # Shared external burst epoch (e.g. snapping shrimp / V2X ignition spike hits all RX antennas simultaneously!)
    e_pre_1, states, v_z_1, ms = c3m.gen_markov_burst_noise(N, sigma0_sq, duty, mean_burst, inr_db, rng)
    e_pre_list = [e_pre_1]
    for _ in range(1, Nr):
        e_pre_list.append((rng.standard_normal(N) + 1j * rng.standard_normal(N)) * np.sqrt(v_z_1 / 2.0))
    e_pre_all = np.concatenate(e_pre_list)
    v_z_all = np.tile(v_z_1, Nr)
    w_bg = (rng.standard_normal(Nr * N) + 1j * rng.standard_normal(Nr * N)) * math.sqrt(sigma0_sq / 2.0)

    y_analog = A_full @ x_true + G_full @ e_pre_all + w_bg
    y_r = c2r_v(y_analog)
    Ar = c2r_m(A_full)
    Gr = c2r_m(G_full)
    v_z_r = np.concatenate([v_z_all * 0.5, v_z_all * 0.5])
    sigma0_r_sq = sigma0_sq * 0.5
    M_r = len(y_r)

    # Standard RMS AGC vs Robust MAD AGC (setting 2/3-bit quantizer step to clean signal RMS!)
    step_rms = (0.9957 if n_bits == 2 else 0.586) * float(np.std(y_r))
    q_rms, _, _, _ = quantize_real(y_r, n_bits, step_rms)

    sig_mad = float(np.median(np.abs(y_r))) / 0.6745
    step_rob = (0.9957 if n_bits == 2 else 0.586) * max(sig_mad, 0.5)
    q_rob, lo_r, hi_r, is_rail = quantize_real(y_r, n_bits, step_rob)

    res = {}
    didx = np.arange(N)

    # 1. Pub: RMS AGC + AQNM LMMSE
    rho_b = 0.1175 if n_bits == 2 else 0.03454
    alpha_aq = 1.0 - rho_b
    var_aq = rho_b * (1.0 - rho_b) * float(np.mean(y_r ** 2) * 2.0) + sigma0_sq
    H_aq = alpha_aq * A_full
    x_pub = np.linalg.solve(H_aq.conj().T @ H_aq + var_aq * np.eye(N), H_aq.conj().T @ r2c_v(q_rms))
    res["Pub_RMSAGC_AQNM"] = c3m.hard_ser_sub(x_pub, x_true, const, didx)

    # 2. SM1: Robust MAD AGC + Standard Gaussian Probit-EP (poisoned by impulsive rail hits!)
    x_sm1 = probit_weighted_ep(lo_r, hi_r, Ar, np.full(M_r, sigma0_r_sq), const, 10, 5)
    res["SM1_RobAGC_GaussProbit"] = c3m.hard_ser_sub(x_sm1, x_true, const, didx)

    # 3. SM2: Robust MAD AGC + Blank ALL saturated rail samples + Interior Probit-EP (loses clean PAPR peaks!)
    v_blank = np.where(is_rail, 1e4, sigma0_r_sq)
    x_sm2 = probit_weighted_ep(lo_r, hi_r, Ar, v_blank, const, 10, 5)
    res["SM2_RobAGC_RailBlankProbit"] = c3m.hard_ser_sub(x_sm2, x_true, const, didx)

    # 4. SM3: Robust MAD AGC + 2-State Markov HMM on Quantized Rail/Surprise Residuals + Iterated Weighted Probit!
    # Uses Markov continuity of rail-hits / Probit surprise to separate isolated clean peaks from contiguous bursts!
    x_sm3 = x_sm2.copy()
    p01, p10 = ms["p01"], ms["p10"]
    # Collapse rail indicator across Re/Im & Nr antennas per time index n=0..N-1
    rail_cnt = np.zeros(N, dtype=float)
    for r_i in range(Nr):
        rail_cnt += is_rail[r_i * N : (r_i + 1) * N].astype(float) + is_rail[Nr * N + r_i * N : Nr * N + (r_i + 1) * N].astype(float)
    for outer in range(4):
        mu_r = Ar @ c2r_v(x_sm3)
        # Surprise: distance from mu_r to quantized interval [lo_r, hi_r]
        surp = np.maximum(0.0, np.maximum(lo_r - mu_r, mu_r - hi_r)) ** 2
        surp_t = np.zeros(N, dtype=float)
        for r_i in range(Nr):
            surp_t += surp[r_i * N : (r_i + 1) * N] + surp[Nr * N + r_i * N : Nr * N + (r_i + 1) * N]
        # Combine surprise + rail hit count in 2-state HMM
        s0_t = max(2.0 * Nr * sigma0_r_sq, float(np.median(surp_t)) / 0.693 + 0.02)
        s1_t = max(s0_t * 25.0, 4.0)
        ll0 = -math.log(s0_t) - surp_t / s0_t - 0.6 * np.maximum(rail_cnt - 1.0, 0.0)
        ll1 = -math.log(s1_t) - surp_t / s1_t + 0.8 * rail_cnt
        gam_t = c3m.hmm_fb_2state(ll0, ll1, p01, p10)
        v_t_est = np.tile(gam_t * ms["sigma_I_sq"] * 0.5, 2 * Nr)
        v_eff = sigma0_r_sq + v_t_est
        x_sm3 = probit_weighted_ep(lo_r, hi_r, Ar, v_eff, const, 8, 4)
    res["SM3_RobAGC_HMM_Probit"] = c3m.hard_ser_sub(x_sm3, x_true, const, didx)

    # 5. Oracle_SameQuant_TrueBurstState (NON-CHEATING: exact binary state v_z -> colored Probit on SAME quantized bits!)
    x_or = probit_colored_oracle(lo_r, hi_r, Ar, Gr, v_z_r, sigma0_r_sq, const)
    res["Oracle_SameQuant_TrueState"] = c3m.hard_ser_sub(x_or, x_true, const, didx)

    # 6. Ref: Infinite-bit colored Oracle
    C_true = sigma0_sq * np.eye(Nr * N) + (G_full * v_z_all[None, :]) @ G_full.conj().T
    x_inf = c3m.full_cov_ep_oamp(y_analog, A_full, C_true, const, None, None, n_iters=10)
    res["Ref_InfBit_TrueState"] = c3m.hard_ser_sub(x_inf, x_true, const, didx)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c11_impulsive_lowbit_adc.json")
    args = ap.parse_args()
    t0 = time.time()

    configs = [
        ("R1_2bit_Nr2_Burst18_AFDM", "AFDM", 64, 2, 2, 22.0, 25.0, 0.18, 7.0),
        ("R1_2bit_Nr2_Burst18_OTFS", "OTFS", 64, 2, 2, 22.0, 25.0, 0.18, 7.0),
        ("R1_2bit_Nr2_Burst18_SCFDE", "SC-FDE", 64, 2, 2, 22.0, 25.0, 0.18, 7.0),
        ("R2_3bit_Nr2_Burst20_AFDM", "AFDM", 64, 2, 3, 24.0, 25.0, 0.20, 8.0),
    ]
    summary = {"meta": {"trials": args.trials}, "results": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, cfg in enumerate(configs):
            key = cfg[0]
            jobs = [(910000 + i * 1000 + t,) + cfg[1:] for t in range(args.trials)]
            outs = list(ex.map(run_trial, jobs))
            agg = {k: {"mean": float(np.mean([o[k] for o in outs])), "se": float(np.std([o[k] for o in outs], ddof=1) / math.sqrt(len(outs)))} for k in outs[0]}
            summary["results"][key] = agg
            best_sm_k = min((k for k in agg if k.startswith("SM")), key=lambda k: agg[k]["mean"])
            best_sm = agg[best_sm_k]["mean"]
            orac = agg["Oracle_SameQuant_TrueState"]["mean"]
            print(f"\n=== {key} (n={args.trials}) ===")
            for k, v in agg.items():
                print(f"  {k:28s}: SER = {v['mean']:.5f} +/- {v['se']:.5f}")
            print(f"  --> Best_SM ({best_sm_k})={best_sm:.5f} vs Oracle_SameQuant={orac:.5f} | Ratio={best_sm/max(orac,1e-6):.2f}x")
    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
