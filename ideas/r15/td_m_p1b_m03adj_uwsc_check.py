#!/usr/bin/env python3
"""
Round 15 Phase 1B — P-m-03-Adj Open-Caveat Settlement (`td_m_p1b_m03adj_uwsc_check.py`):
Tests the strongest equal-overhead (154/512 pilot, exact same Nd=358 64-QAM payload, L_cpp=16,
sig_r=sig_t=1.5e-3, SNR=30 dB, adjacent delays [0,1,16] & [0,15,16]) Wide-UW & Multi-Cluster
Zero-ISI UW-SC Steelman receivers against Phase 1A's conditional survivor `P-m-03-Adj`
(`Adj_R4_30dB_SFBlind` and `Adj_R5_30dB_PNTrain`).

Strictly READ-ONLY imports `ideas/r15/td_m_m03.py` & frozen `ideas/l2/l2_m_r12_m03_modtest.py`.
Does NOT modify any Phase 1A script, JSON, card, or `teardown-m.md`.

Equal-overhead (154/512) SC-FDE Steelman_S layouts tested:
  1. `SC_Orig_UW48_106PTRS`   : Phase 1A baseline (48-UW + 106 single-sample PTRS)
  2. `SC_WideUW_100_54PTRS`   : 100-sample UW [0..99] (84 clean samples) + 54 distributed PTRS
  3. `SC_DualUW_2x77`         : Two 77-sample UW blocks [0..76], [256..332] (2 x 61 = 122 zero-ISI obs,
                                full N/2 Doppler aperture + dual-PN EKF-RTS on zero-ISI obs!)
  4. `SC_QuadUW_4x38`         : Four guard-protected UW clusters [0..38],[128..166],[256..293],[384..421]
                                (4 x 22 = 88 zero-ISI obs every 128 samples, exact Doppler + dual-PN EKF-RTS!)
  5. `Oracle_SC_Dual`         : True (H, phi_r, phi_t) exact OAMP reference.
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
from scipy.stats import t as student_t

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

import td_m_m03 as td3
m3 = td3.m3


def make_sc_mask(N: int, n_guard: int, layout: str) -> np.ndarray:
    mask = np.zeros(N, dtype=bool)
    if layout == "uw48_ptrs106":
        mask[:48] = True
        ptrs = np.round(np.linspace(50, N - 2, n_guard - 48)).astype(int)
        mask[ptrs] = True
    elif layout == "wide_uw100_ptrs54":
        mask[:100] = True
        ptrs = np.round(np.linspace(104, N - 2, n_guard - 100)).astype(int)
        mask[ptrs] = True
    elif layout == "dual_uw_2x77":
        mask[0:77] = True
        mask[256:333] = True
    elif layout == "quad_uw_4x38":
        mask[0:39] = True
        mask[128:167] = True
        mask[256:294] = True
        mask[384:422] = True
    else:
        raise ValueError(layout)
    while int(mask.sum()) < n_guard:
        mask[int(np.where(~mask)[0][0])] = True
    assert int(mask.sum()) == n_guard, f"{layout}: {int(mask.sum())} != {n_guard}"
    return mask


def eval_sc_layout(y_sc, y_tr_sc, sp_tr_sc, x_sc, xp_sc, sp_sc, sc_pil_mask, sc_data_mask,
                   P_sc, N, L_cpp, mode, sig_r_prior, sig_t_prior, pts64):
    B = N + L_cpp
    I_N = np.eye(N, dtype=complex)
    n_arr = np.arange(N)

    pil_ext = np.zeros(B, dtype=bool)
    pil_ext[:L_cpp] = sc_pil_mask[N - L_cpp:]
    pil_ext[L_cpp:] = sc_pil_mask
    clean_uw_rows = np.array([all(pil_ext[L_cpp + n - l] for l in range(L_cpp + 1)) for n in range(N)], dtype=bool)
    uw_idx = np.where(clean_uw_rows)[0]

    # Step 1: Channel delay support + initial (h, nu) estimation
    if mode == "single_frame":
        # Non-coherent short-window matched correlation on zero-ISI uw_idx (robust to Wiener PN drift!)
        # Split uw_idx into contiguous blocks of length <= 24 so PN stays coherent inside each sub-block
        sub_blocks = []
        cur = [int(uw_idx[0])]
        for idx_v in uw_idx[1:]:
            if int(idx_v) == cur[-1] + 1 and len(cur) < 20:
                cur.append(int(idx_v))
            else:
                if len(cur) >= 8:
                    sub_blocks.append(np.array(cur, dtype=int))
                cur = [int(idx_v)]
        if len(cur) >= 8:
            sub_blocks.append(np.array(cur, dtype=int))

        # OMP jointly across all coherent sub-blocks (each sub-block gets its own local phase via subspace projection!)
        # Equivalent to exact delay-support estimation on zero-ISI UW observations under unknown per-block phase!
        supp_omp = []
        Phi_blocks = [np.column_stack([sp_sc[L_cpp + blk - l] for l in range(L_cpp + 1)]) for blk in sub_blocks]
        res_blocks = [y_sc[blk].copy() for blk in sub_blocks]
        for _ in range(4):
            scores = np.zeros(L_cpp + 1, dtype=float)
            for blk_i, Pb in enumerate(Phi_blocks):
                rb = res_blocks[blk_i]
                scores += np.abs(Pb.conj().T @ rb) ** 2 / np.maximum(np.sum(np.abs(Pb) ** 2, axis=0), 1e-12)
            for s_old in supp_omp:
                scores[s_old] = -1.0
            best_l = int(np.argmax(scores))
            supp_try = sorted(supp_omp + [best_l])
            e_old = sum(float(np.sum(np.abs(rb) ** 2)) for rb in res_blocks)
            new_res = []
            for blk_i, Pb in enumerate(Phi_blocks):
                P_sub = Pb[:, supp_try]
                hb, *_ = np.linalg.lstsq(P_sub, y_sc[sub_blocks[blk_i]], rcond=None)
                new_res.append(y_sc[sub_blocks[blk_i]] - P_sub @ hb)
            e_new = sum(float(np.sum(np.abs(rb) ** 2)) for rb in new_res)
            if len(supp_omp) >= 1 and (e_old - e_new) < 0.06 * e_old and e_old / len(uw_idx) < 0.03:
                break
            supp_omp = supp_try
            res_blocks = new_res
            if e_new / len(uw_idx) < 2e-3:
                break
        l_sc = np.array(sorted(supp_omp), dtype=int)

        # Joint initial (h_sc, nu_sc, pr_sc, pt_sc) via alternating EKF-RTS + refine_channel_blind on clean UW samples!
        # Start h_sc from the FIRST sub-block (where phi_r[0] ~ 0, phi_t ~ 0)
        h_sc, *_ = np.linalg.lstsq(Phi_blocks[0][:, l_sc], y_sc[sub_blocks[0]], rcond=None)
        nu_sc = np.zeros(len(l_sc), dtype=float)
        # If multiple well-separated UW blocks exist, refine (h_sc, nu_sc) with coarse Doppler grid + phase unwrap across blocks
        s2_sc = max(sum(float(np.sum(np.abs(rb) ** 2)) for rb in res_blocks) / max(len(uw_idx), 1), 1e-4)
    else:
        # prior_pn mode: use full-frame PN-corrupted preamble (same as td_m_m03.py)
        coh_pow = np.zeros(L_cpp + 1)
        for l in range(L_cpp + 1):
            prod = y_tr_sc * np.conj(sp_tr_sc[L_cpp + n_arr - l])
            for b0 in range(0, N, 32):
                coh_pow[l] += abs(np.sum(prod[b0:b0 + 32])) ** 2 / 32.0
        med_tr = float(np.median(np.sort(coh_pow)[:(L_cpp + 1) // 2]))
        thr_tr = max(3.5 * med_tr, 0.05 * float(coh_pow.max()))
        cl_sc = [l for l in range(L_cpp + 1) if coh_pow[l] > thr_tr]
        if not cl_sc:
            cl_sc = [int(np.argmax(coh_pow))]
        l_sc = np.array(sorted(cl_sc), dtype=int)
        nu_sc = np.zeros(len(l_sc), dtype=float)
        h_sc = np.array([np.mean((y_tr_sc * np.conj(sp_tr_sc[L_cpp + n_arr - int(l)]))[N // 2 - 16 : N // 2 + 16]) for l in l_sc])
        pr_tr_s = np.zeros(N); pt_tr_s = np.zeros(B)
        for _ in range(4):
            Hl_tr = m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc)
            pr_tr_s, pt_tr_s = td3.ekf_rts_lag_timedomain(y_tr_sc, Hl_tr, sp_tr_sc, pr_tr_s, pt_tr_s, 1e-3, sig_r_prior, sig_t_prior, L_cpp, l_sc, 3)
            h_sc, nu_sc = m3.refine_channel_blind(y_tr_sc, sp_tr_sc, pr_tr_s, pt_tr_s, l_sc, nu_sc, L_cpp)
        s2_sc = max(float(np.mean(np.abs(y_tr_sc - np.exp(1j * pr_tr_s) * (m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc) @ (np.exp(1j * pt_tr_s) * sp_tr_sc))) ** 2)), 1e-5)

    # Step 2: Pilot-only 18-state Lag-IEKS-RTS + (in single_frame) UW channel refinement!
    pr_sc = np.zeros(N, dtype=float)
    pt_sc = np.zeros(B, dtype=float)
    # Initialize pr_sc by unwrapping per-block UW phase when multiple clean blocks exist
    Hl_sc0 = m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc)
    u_all = Hl_sc0 @ sp_sc
    # Find contiguous clean UW segments to unwrap initial phase across the whole frame!
    segs = []
    s0 = int(uw_idx[0]); prev = s0
    for idx_v in uw_idx[1:]:
        if int(idx_v) != prev + 1:
            segs.append(np.arange(s0, prev + 1))
            s0 = int(idx_v)
        prev = int(idx_v)
    segs.append(np.arange(s0, prev + 1))
    seg_centers = np.array([float(np.mean(sg)) for sg in segs])
    seg_phases = np.unwrap(np.array([float(np.angle(np.vdot(u_all[sg], y_sc[sg]))) for sg in segs]))
    pr_sc = np.interp(np.arange(N, dtype=float), seg_centers, seg_phases)

    r_var_vec = np.empty(N, dtype=float)
    for n_i in range(N):
        un_pow = 0.0; kn_pow = 0.0
        for p_i, l in enumerate(l_sc):
            p2 = abs(h_sc[p_i]) ** 2
            if pil_ext[L_cpp + n_i - int(l)]:
                kn_pow += p2
            else:
                un_pow += p2
        r_var_vec[n_i] = 0.5 * (s2_sc + un_pow) if kn_pow > 0.05 else 1e6

    for pass_i in range(5):
        Hl_sc0 = m3.build_H_ext(N, L_cpp, h_sc, l_sc, nu_sc)
        xi_nom = np.column_stack([pr_sc] + [pt_sc[L_cpp - l : L_cpp - l + N] for l in range(L_cpp + 1)])
        D_s = L_cpp + 2
        F_s = np.zeros((D_s, D_s)); F_s[0, 0] = 1.0; F_s[1, 1] = 1.0
        for l in range(1, L_cpp + 1): F_s[1 + l, l] = 1.0
        Q_s = np.zeros((D_s, D_s)); Q_s[0, 0] = sig_r_prior; Q_s[1, 1] = sig_t_prior
        xf = np.empty((N, D_s)); Pf = np.empty((N, D_s, D_s)); xpr = np.empty((N, D_s)); Ppr = np.empty((N, D_s, D_s))
        for n_i in range(N):
            if n_i == 0:
                xp_i = xi_nom[0].copy(); Pp_i = 10.0 * np.eye(D_s); Pp_i[1, 1] = 1e-3
            else:
                xp_i = F_s @ xf[n_i - 1]; Pp_i = F_s @ Pf[n_i - 1] @ F_s.T + Q_s
            xpr[n_i] = xp_i; Ppr[n_i] = Pp_i
            if r_var_vec[n_i] > 1e4:
                xf[n_i] = xp_i; Pf[n_i] = Pp_i; continue
            xl = xi_nom[n_i]; hr = np.zeros(D_s); hi = np.zeros(D_s); yh = 0.0 + 0.0j
            for p_i, l in enumerate(l_sc):
                if not pil_ext[L_cpp + n_i - int(l)]:
                    continue
                it = 1 + int(l)
                tm = Hl_sc0[n_i, L_cpp + n_i - int(l)] * sp_sc[L_cpp + n_i - int(l)] * np.exp(1j * (xl[0] + xl[it]))
                yh += tm; dt = 1j * tm; hr[0] += dt.real; hr[it] += dt.real; hi[0] += dt.imag; hi[it] += dt.imag
            Hn = np.vstack([hr, hi])
            inn = np.array([(y_sc[n_i] - yh).real, (y_sc[n_i] - yh).imag]) + Hn @ (xl - xp_i)
            HP = Hn @ Pp_i; S_i = r_var_vec[n_i] * np.eye(2) + HP @ Hn.T; K_i = np.linalg.solve(S_i, HP).T
            xf[n_i] = xp_i + K_i @ inn; Pf[n_i] = 0.5 * ((Pp_i - K_i @ HP) + (Pp_i - K_i @ HP).T)
        xsm = np.empty_like(xf); xsm[-1] = xf[-1]
        for n_i in range(N - 2, -1, -1):
            Cn = np.linalg.solve(Ppr[n_i + 1] + 1e-9 * np.eye(D_s), F_s @ Pf[n_i]).T
            xsm[n_i] = xf[n_i] + Cn @ (xsm[n_i + 1] - xpr[n_i + 1])
        pr_sc = pr_sc + np.clip(xsm[:, 0] - pr_sc, -0.45, 0.45)
        pt_t = np.zeros(B); pt_t[L_cpp:] = xsm[:, 1]
        for l in range(1, L_cpp + 1): pt_t[L_cpp - l] = xsm[0, 1 + l]
        pt_sc = pt_sc + np.clip(pt_t - pt_sc, -0.45, 0.45)
        sg = pt_sc[L_cpp]; pt_sc -= sg; pr_sc += sg

        # In single_frame mode, refine (h_sc, nu_sc) on the zero-ISI UW observations using current (pr_sc, pt_sc)!
        if mode == "single_frame" and len(uw_idx) >= 32 and pass_i >= 1:
            y_uw_d = y_sc[uw_idx] * np.exp(-1j * pr_sc[uw_idx])
            def fit_nu_h(nus_cur):
                A_u = np.column_stack([
                    sp_sc[L_cpp + uw_idx - int(l)] * np.exp(1j * pt_sc[L_cpp + uw_idx - int(l)]) * np.exp(-1j * 2.0 * np.pi * nus_cur[pi] * uw_idx / float(N))
                    for pi, l in enumerate(l_sc)
                ])
                hh, *_ = np.linalg.lstsq(A_u, y_uw_d, rcond=None)
                return hh, float(np.sum(np.abs(y_uw_d - A_u @ hh) ** 2))
            if len(segs) >= 2:  # Only refine Doppler when multi-block aperture spans > N/4!
                for pi in range(len(l_sc)):
                    best_nu, best_e = nu_sc[pi], 1e18
                    for v in np.linspace(-0.45, 0.45, 19):
                        nt = nu_sc.copy(); nt[pi] = float(v)
                        _, ev = fit_nu_h(nt)
                        if ev < best_e:
                            best_e = ev; best_nu = float(v)
                    nu_sc[pi] = best_nu
            h_sc, _ = fit_nu_h(nu_sc)

    # Step 3: 6-outer Joint OAMP + 18-state Lag-IEKS-RTS + blind channel refinement
    best_rsc = np.inf; best_xh_sc = None
    hc_sc, nuc_sc = h_sc.copy(), nu_sc.copy()
    s2_c_sc = s2_sc
    for out_i in range(6):
        Hl_sc = m3.build_H_ext(N, L_cpp, hc_sc, l_sc, nuc_sc)
        Hc_sc = np.exp(1j * pr_sc)[:, None] * ((Hl_sc * np.exp(1j * pt_sc)[None, :]) @ P_sc)
        xs_sc, xhc_sc, vx_sc, _ = m3.oamp_exact(y_sc, Hc_sc, I_N, max(s2_c_sc, 1e-6) + 0.02 * (0.6 ** out_i), pts64, sc_data_mask, xp_sc, 8)
        s_ext_sc_hat = P_sc @ xs_sc
        pr_sc, pt_sc = td3.ekf_rts_lag_timedomain(y_sc, Hl_sc, s_ext_sc_hat, pr_sc, pt_sc, max(s2_c_sc, 1e-6) + 0.5 * vx_sc,
                                                  sig_r_prior, sig_t_prior, L_cpp, l_sc, n_sweeps=2)
        if out_i >= 1:
            hc_sc, nuc_sc = m3.refine_channel_blind(y_sc, s_ext_sc_hat, pr_sc, pt_sc, l_sc, nuc_sc, L_cpp)
        Hl_sc2 = m3.build_H_ext(N, L_cpp, hc_sc, l_sc, nuc_sc)
        rsc = float(np.sum(np.abs(y_sc - np.exp(1j * pr_sc) * (Hl_sc2 @ (np.exp(1j * pt_sc) * (P_sc @ xhc_sc)))) ** 2))
        s2_c_sc = float(np.clip(rsc / N, 1e-5, 0.05))
        if rsc < best_rsc:
            best_rsc = rsc; best_xh_sc = xhc_sc

    ser = float(np.mean(np.abs(best_xh_sc[sc_data_mask] - x_sc[sc_data_mask]) > 1e-3))
    return ser, [int(v) for v in l_sc]


def run_frame(args):
    seed, mode, mid_delay = args
    rng = np.random.default_rng(seed)
    N = 512; L_cpp = 16; B = N + L_cpp; n_guard = 154; Nd = N - n_guard
    snr_db = 30.0; sig_r = 1.5e-3; sig_t = 1.5e-3
    P_sc = m3.build_cpp_ext(N, 0.0, L_cpp)
    I_N = np.eye(N, dtype=complex)
    g8 = np.array([-7, -5, -3, -1, 1, 3, 5, 7]); pts64 = (g8[:, None] + 1j * g8[None, :]).ravel() / np.sqrt(42.0)
    qpsk = np.array([-1-1j, -1+1j, 1-1j, 1+1j]) / np.sqrt(2.0)

    ls_t = np.array([0, mid_delay, 16], dtype=int)
    pdp = np.array([0.4225, 0.3025, 0.2750])
    nus_t = rng.uniform(-0.4, 0.4, 3)
    hs_t = np.sqrt(pdp) * np.exp(1j * rng.uniform(0, 2 * np.pi, 3))
    H_lin_t = m3.build_H_ext(N, L_cpp, hs_t, ls_t, nus_t)
    sig2_true = 10.0 ** (-snr_db / 10.0)

    phi_t = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)); phi_t -= phi_t[L_cpp]
    phi_r = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N))
    w = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    xd_vals = pts64[rng.integers(0, 64, Nd)]
    pil_vals = qpsk[rng.integers(0, 4, n_guard)]

    y_tr_sc = None; sp_tr_sc = None
    if mode == "prior_pn":
        w_tr = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        x_tr_sc = qpsk[rng.integers(0, 4, N)]
        sp_tr_sc = P_sc @ x_tr_sc
        pt_tr = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)); pt_tr -= pt_tr[L_cpp]
        pr_tr = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N))
        y_tr_sc = np.exp(1j * pr_tr) * (H_lin_t @ (np.exp(1j * pt_tr) * sp_tr_sc)) + w_tr

    out = {"mid_delay": mid_delay}
    layouts = ["uw48_ptrs106", "wide_uw100_ptrs54", "dual_uw_2x77", "quad_uw_4x38"]
    for ly in layouts:
        mask = make_sc_mask(N, n_guard, ly); dmask = ~mask
        x_sc = np.zeros(N, dtype=complex); x_sc[dmask] = xd_vals; x_sc[mask] = pil_vals
        xp_sc = np.where(mask, x_sc, 0.0); sp_sc = P_sc @ xp_sc; s_ext_sc = P_sc @ x_sc
        y_sc = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ext_sc)) + w
        ser_v, l_det = eval_sc_layout(y_sc, y_tr_sc, sp_tr_sc, x_sc, xp_sc, sp_sc, mask, dmask,
                                      P_sc, N, L_cpp, mode, sig_r, sig_t, pts64)
        out[f"SM_{ly}"] = ser_v
        out[f"_exact3_{ly}"] = float(set(l_det) == {0, mid_delay, 16})
        if ly == "quad_uw_4x38":
            Ho_sc = np.exp(1j * phi_r)[:, None] * ((H_lin_t * np.exp(1j * phi_t)[None, :]) @ P_sc)
            _, xho, _, _ = m3.oamp_exact(y_sc, Ho_sc, I_N, sig2_true, pts64, dmask, xp_sc, 10)
            out["Oracle_SC_Dual"] = float(np.mean(np.abs(xho[dmask] - x_sc[dmask]) > 1e-3))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_per_k", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_m03adj_uwsc.json")
    args = ap.parse_args()
    t0 = time.time()

    slices = [
        ("Adj_R4_30dB_SFBlind", "single_frame", [1, 15]),
        ("Adj_R5_30dB_PNTrain", "prior_pn",     [1, 15]),
    ]
    res_all = {"meta": {"n_per_k": args.n_per_k, "n_total_per_slice": 2 * args.n_per_k}, "slices": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for si, (sname, mode, ks) in enumerate(slices):
            jobs = [(202611268000 + si * 10000 + ki * 1000 + f, mode, kv) for ki, kv in enumerate(ks) for f in range(args.n_per_k)]
            rows = list(ex.map(run_frame, jobs))
            keys = [k for k in rows[0] if not k.startswith("_") and k != "mid_delay"]
            n = len(rows)
            tc = float(student_t.ppf(0.975, df=max(n - 1, 1)))
            agg = {}
            for k in keys:
                arr = np.array([r[k] for r in rows], dtype=float)
                agg[k] = {
                    "mean": float(np.mean(arr)),
                    "se": float(np.std(arr, ddof=1) / math.sqrt(n)),
                    "ci95_hw": float(tc * np.std(arr, ddof=1) / math.sqrt(n)),
                    "ll_gt5pct": float(np.mean(arr > 0.05)),
                }
            for ly in ["uw48_ptrs106", "wide_uw100_ptrs54", "dual_uw_2x77", "quad_uw_4x38"]:
                agg[f"exact3_rate_{ly}"] = float(np.mean([r[f"_exact3_{ly}"] for r in rows]))
            res_all["slices"][sname] = agg
            print(f"\n=== {sname} (n={n}) ===")
            for k in keys:
                v = agg[k]
                print(f"  {k:22s}: SER = {v['mean']:.5f} +/- {v['se']:.5f} (LL>5%: {v['ll_gt5pct']*100:.1f}%)")
            print("  exact3 rates:", {ly: round(agg[f"exact3_rate_{ly}"], 3) for ly in ["uw48_ptrs106", "wide_uw100_ptrs54", "dual_uw_2x77", "quad_uw_4x38"]})
    res_all["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(res_all, f, indent=2)
    print(f"\nSaved -> {args.out} in {res_all['elapsed_sec']}s")


if __name__ == "__main__":
    main()
