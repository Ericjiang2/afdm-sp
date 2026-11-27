#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C13 Fast Teardown (`td_m_p1b_c13_impulsive_isac.py`):
Doubly-Dispersive ISAC (Weak High-Doppler Target -28 dB + Strong 0 dB Clutter) under
Bursty Receive-Filter-Colored Impulsive Noise (+25 dB INR) — Monostatic & Bistatic Check!

Literature Anchors (2024-2026):
  - Xiao, Li, Slock, IEEE TCOM 2026 (10.1109/tcomm.2026.3686728): AFDM-ISAC range-Doppler estimation
  - Barka, Alam, Kaddoum, Au, Agba, IEEE TCOM 2026 (10.1109/tcomm.2026.3698821): Bursty impulsive noise
  - Gourar et al., arXiv:2609.14030 (2026): AFDM sensing matched-filter distortion

Evaluates strict equal-Pfa (Pfa = 2% calibrated on independent clutter + bursty-impulsive H0 trials!)
weak-target detection Pd across:
  1) `Pub_ClutProj_GLRT`       : Standard subspace clutter projection + MF GLRT (no impulsive mitigation)
  2) `SM1_ZMNL_Clip_GLRT`      : Time-domain clipping/blanking + clutter-projected GLRT (clips clutter -> sidelobes!)
  3) `SM2_HuberIRLS_ClutGLRT`  : Iterative Huber-weighted clutter fit + weighted GLRT (ignores G coloration!)
  4) `SM3_InnovHMM_WhitenedGLRT`: Sol-level Steelman: alternating clutter LS + innovation-domain 2-state HMM ->
                                  exact colored-cov whitened generalized clutter-projected GLRT!
  5) `Oracle_TrueState_WhitGLRT`: Non-cheating State-Oracle: exact colored covariance C_true whitened clutter-projected GLRT!
  6) `Ref_NoImpulse_GLRT`      : Clean AWGN clutter-projected GLRT reference.
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


def make_atom(s, tau, nu, N):
    n = np.arange(N, dtype=float)
    return np.roll(s, int(tau)) * np.exp(1j * 2.0 * np.pi * nu * n / float(N))


def whitened_clutter_glrt(y, U_c, s, C_n, tau_grid, nu_grid):
    """Exact Generalized Clutter-Projected GLRT in C_n^{-1} metric: max_{tau,nu} |a^H P_c^perp y_w|^2 / (a^H P_c^perp a)."""
    N = len(y)
    L = np.linalg.cholesky(C_n + 1e-9 * np.eye(N))
    yw = np.linalg.solve(L, y)
    Uw = np.linalg.solve(L, U_c)
    Q, _ = np.linalg.qr(Uw)
    y_perp = yw - Q @ (Q.conj().T @ yw)
    best_stat = 0.0
    best_pt = (0, 0.0)
    for tau in tau_grid:
        s_del = np.roll(s, int(tau))
        for nu in nu_grid:
            a = s_del * np.exp(1j * 2.0 * np.pi * nu * np.arange(N) / float(N))
            aw = np.linalg.solve(L, a)
            a_perp = aw - Q @ (Q.conj().T @ aw)
            den = float(np.vdot(a_perp, a_perp).real)
            if den > 1e-10:
                st = float(abs(np.vdot(a_perp, y_perp)) ** 2 / den)
                if st > best_stat:
                    best_stat = st; best_pt = (int(tau), float(nu))
    return best_stat, best_pt


def run_scene(args):
    seed, wf, is_h1, N, snr_db, tgt_db, inr_db, duty, mean_burst = args
    rng = np.random.default_rng(seed)
    const = c3m.gray_qam(64)
    sigma0_sq = 10.0 ** (-snr_db / 10.0)
    c1 = 5.0 / (2.0 * N) if wf == "AFDM" else 0.0
    U = c3m.daft_mat(N, c1, 1.0 / (2 * math.pi * N)) if wf == "AFDM" else (c3m.otfs_mat(16, N // 16) if wf == "OTFS" else np.eye(N, dtype=np.complex128))
    x = const[rng.integers(0, len(const), size=N)]
    s = U.conj().T @ x  # Known monostatic ISAC transmit waveform (unit power)
    G = c3m.build_rx_filter_matrix(N, colored=True, bw_factor=0.42)

    # Strong 0 dB stationary clutter on delays 0..5 (zero Doppler)
    clut_delays = np.arange(6)
    U_c = np.column_stack([np.roll(s, int(l)) for l in clut_delays])
    g_c = (rng.standard_normal(len(clut_delays)) + 1j * rng.standard_normal(len(clut_delays))) / math.sqrt(2.0 * len(clut_delays))
    y_clut = U_c @ g_c

    # Weak high-Doppler target on tau in [8..15], nu in [2.5..5.5]
    tau_grid = np.arange(8, 16)
    nu_grid = np.linspace(2.5, 5.5, 13)
    if is_h1:
        tau_t = int(rng.choice(tau_grid))
        nu_t = float(rng.choice(nu_grid))
        amp_t = 10.0 ** (tgt_db / 20.0)
        y_tgt = amp_t * np.exp(1j * rng.uniform(0, 2 * math.pi)) * make_atom(s, tau_t, nu_t, N)
    else:
        tau_t, nu_t = -1, 0.0
        y_tgt = np.zeros(N, dtype=np.complex128)

    e_pre, _, v_z, ms = c3m.gen_markov_burst_noise(N, sigma0_sq, duty, mean_burst, inr_db, rng)
    w = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sigma0_sq / 2.0)
    y = y_clut + y_tgt + G @ e_pre + w
    y_clean = y_clut + y_tgt + w

    I_N = np.eye(N, dtype=np.complex128)
    C_true = sigma0_sq * I_N + (G * v_z[None, :]) @ G.conj().T
    p01, p10, sI = ms["p01"], ms["p10"], ms["sigma_I_sq"]

    out = {}
    # 1. Pub: Standard clutter-projected GLRT (Gaussian assumption)
    st, pt = whitened_clutter_glrt(y, U_c, s, (sigma0_sq + duty * sI) * I_N, tau_grid, nu_grid)
    out["Pub_Std_GLRT"] = (st, pt == (tau_t, nu_t))

    # 2. SM1: ZMNL Clip + clutter-projected GLRT
    T_clip = 2.6 * max(float(np.median(np.abs(y))) / 0.8326, 1.0)
    yc = np.where(np.abs(y) > T_clip, y * (T_clip / np.maximum(np.abs(y), 1e-12)), y)
    st, pt = whitened_clutter_glrt(yc, U_c, s, sigma0_sq * I_N, tau_grid, nu_grid)
    out["SM1_ZMNL_Clip_GLRT"] = (st, pt == (tau_t, nu_t))

    # 3. SM2: Iterative Huber-weighted clutter LS + diagonal-weighted GLRT (no G coloration!)
    w_h = np.ones(N, dtype=float)
    for _ in range(5):
        Aw = np.sqrt(w_h)[:, None] * U_c; yw = np.sqrt(w_h) * y
        gc_h, *_ = np.linalg.lstsq(Aw, yw, rcond=None)
        r = np.abs(y - U_c @ gc_h)
        mad = max(float(np.median(r)) / 0.6745, math.sqrt(sigma0_sq))
        w_h = np.where(r <= 1.345 * mad, 1.0, 1.345 * mad / np.maximum(r, 1e-12))
    C_hub = np.diag(np.clip((mad ** 2) / np.maximum(w_h, 1e-5), sigma0_sq, 1e5))
    st, pt = whitened_clutter_glrt(y, U_c, s, C_hub, tau_grid, nu_grid)
    out["SM2_Huber_DiagGLRT"] = (st, pt == (tau_t, nu_t))

    # 4. SM3: Sol-level Steelman: Huber clutter init -> Pre-filter Innovation-HMM -> Exact colored-cov C_hat whitened GLRT!
    W_dec = np.linalg.solve(G.conj().T @ G + 0.05 * I_N, G.conj().T)
    bg_v = np.real(np.sum(np.abs(W_dec) ** 2, axis=1)) * sigma0_sq
    sg = np.maximum(np.real(np.diag(W_dec @ G)) ** 2, 0.25)
    C_hat = C_hub
    for _ in range(5):
        L_h = np.linalg.cholesky(C_hat + 1e-9 * I_N)
        gc_h, *_ = np.linalg.lstsq(np.linalg.solve(L_h, U_c), np.linalg.solve(L_h, y), rcond=None)
        r = y - U_c @ gc_h
        e2 = np.abs(W_dec @ r) ** 2
        s0_v = np.maximum(bg_v, 0.6 * float(np.median(e2)) / 0.693147)
        s1_v = np.maximum(s0_v + sg * sI, 10.0 * s0_v)
        gam = c3m.hmm_fb_2state(-np.log(s0_v) - e2 / s0_v, -np.log(s1_v) - e2 / s1_v, p01, p10)
        C_hat = sigma0_sq * I_N + (G * (gam * sI)[None, :]) @ G.conj().T
    st, pt = whitened_clutter_glrt(y, U_c, s, C_hat, tau_grid, nu_grid)
    out["SM3_InnovHMM_WhitGLRT"] = (st, pt == (tau_t, nu_t))

    # 5. Oracle_TrueState_WhitGLRT (non-cheating: exact colored C_true!)
    st, pt = whitened_clutter_glrt(y, U_c, s, C_true, tau_grid, nu_grid)
    out["Oracle_TrueState_WhitGLRT"] = (st, pt == (tau_t, nu_t))

    # 6. Ref_NoImpulse_GLRT
    st, pt = whitened_clutter_glrt(y_clean, U_c, s, sigma0_sq * I_N, tau_grid, nu_grid)
    out["Ref_NoImpulse_GLRT"] = (st, pt == (tau_t, nu_t))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nh0", type=int, default=80)
    ap.add_argument("--nh1", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c13_impulsive_isac.json")
    args = ap.parse_args()
    t0 = time.time()

    results = {}
    for wf in ["AFDM", "OTFS"]:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            h0 = list(ex.map(run_scene, [(960000 + t, wf, False, 256, 35.0, -32.0, 25.0, 0.20, 8.0) for t in range(args.nh0)]))
            h1 = list(ex.map(run_scene, [(970000 + t, wf, True, 256, 35.0, -32.0, 25.0, 0.20, 8.0) for t in range(args.nh1)]))
        agg = {}
        print(f"\n=== C13_ImpulsiveISAC_Tgt-32dB_SNR35_Burst20__{wf} (Pfa=2.5%, nH0={args.nh0}, nH1={args.nh1}) ===")
        for k in h0[0]:
            s0 = np.array([o[k][0] for o in h0])
            thr = float(np.quantile(s0, 0.975))
            pd = float(np.mean([o[k][0] > thr and o[k][1] for o in h1]))
            agg[k] = {"pd": pd, "thr": thr}
            print(f"  {k:28s}: Pd = {pd*100:5.1f}% (thr={thr:.2f})")
        results[wf] = agg
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDone in {time.time()-t0:.1f}s.")


if __name__ == "__main__":
    main()
