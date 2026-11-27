#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C8 Final Sol-Prescribed Adversarial Audit (`td_m_p1b_c8_nassar_audit.py`):
Implements gpt-6.2-sol Call 3's EXACT strongest legal Steelman:
  **Joint `[A_d(h), G] [x_d; e_pre]` Factor Graph (`Nassar et al., IEEE TSP 2013` upgraded with exact RX filter `G`)**!

Key upgrades over `td_m_p1b_c8_joint_ce_bursty.py`:
  1. **Joint Pilot Sparse Separation Init (`SM_PilotJointSep`)**:
     On the 40 zero-ISI pilot observations `y_pil = D_pil h + G_pil e_pre + w_pil`, jointly separates
     sparse pre-filter impulse `e_pre` (via Huber/L1-IRLS over `G_pil`) and sparse DD channel `h` (OMP)
     before entering full-frame detection (and compares against Multi-Subset CE).
  2. **Joint `[x_d; e_pre]` Full-Cov EP + Exact 2-State Markov HMM Factor Graph (`SM_Nassar_JointFG`)**:
     NO lossy residual deconvolution `W_dec @ r`! Forms the exact joint linear observation
       `y - H s_pil = [A_d(h), G] [x_d; e_pre] + w`  (256 x 448 system),
     performs exact joint `(Nd + N) x (Nd + N)` Gaussian EP linear projection preserving FULL `G`
     coloration AND FULL `x_d <-> e_pre` cross-covariance, feeds cavity `(r_x, v_x)` to the exact
     16-QAM MMSE denoiser and cavity `(r_e, v_e)` to the exact 2-state Markov forward-backward HMM
     smoother (`e_pre[n] | z_n=0 ~ N(0, eps)`, `z_n=1 ~ N(0, sigma_I^2)`), then updates `H` via
     soft-symbol + `e_pre`-subtracted full-frame OMP (3 outer DD passes).
  3. **Frozen-True-H Joint Factor Graph (`SM_Nassar_TrueH`)**:
     Directly answers Sol's diagnostic: does joint `[x_d; e_pre]` factor-graph inference crush the
     3.70% -> 0.098% gap even when `H_true` is known?
  4. **Strictly Paired 4-Waveform Suite (`AFDM, OTFS, OFDM, SC-FDE`)**:
     Identical `(H_base, e_pre, w_bg, x_data)` per seed across all 4 waveforms, verifying zero data
     leakage on the 40 pilot rows, per-frame error counts, and paired `pSteel - 15 * pOracle` 95% CI!
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
from scipy.linalg import cho_factor, cho_solve
from scipy.stats import t as student_t

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import td_m_p1b_c3_bursty_impulsive as c3m
import td_m_p1b_c8_joint_ce_bursty as c8


def hmm_scalar_bg_denoise(r_e: np.ndarray, v_e: np.ndarray, sigma_I_sq: float, p01: float, p10: float, eps0: float = 1e-6):
    """Exact 2-state Markov HMM posterior mean & variance for e_n given cavity r_e[n] = e_n + N(0, v_e[n]).
    State 0: e_n ~ CN(0, eps0) (silent); State 1: e_n ~ CN(0, sigma_I_sq) (impulse active).
    """
    ve = np.maximum(np.real(v_e), 1e-6)
    s0 = ve + eps0
    s1 = ve + sigma_I_sq
    e2 = np.abs(r_e) ** 2
    ll0 = -np.log(s0) - e2 / s0
    ll1 = -np.log(s1) - e2 / s1
    gam = c3m.hmm_fb_2state(ll0, ll1, p01, p10)  # P(z_n = 1 | r_e)

    # Conditional posterior mean & variance in each state
    k0 = eps0 / s0
    k1 = sigma_I_sq / s1
    m0 = k0 * r_e; v0 = k0 * ve
    m1 = k1 * r_e; v1 = k1 * ve

    # Exact mixture mean & total variance
    e_hat = (1.0 - gam) * m0 + gam * m1
    v_hat = (1.0 - gam) * (v0 + np.abs(m0 - e_hat) ** 2) + gam * (v1 + np.abs(m1 - e_hat) ** 2)
    return e_hat, np.maximum(np.real(v_hat), 1e-6), gam


def joint_nassar_ep_fg(y_d: np.ndarray, A_d: np.ndarray, G: np.ndarray, sigma0_sq: float,
                       const: np.ndarray, sigma_I_sq: float, p01: float, p10: float,
                       n_iters: int = 14, damp: float = 0.60,
                       gam_e_init: np.ndarray = None):
    """Exact Joint [A_d, G] [x_d; e_pre] Factor-Graph EP (Nassar TSP'13 upgraded with exact G)."""
    N, Nd = A_d.shape
    M_tot = Nd + N
    M = np.hstack([A_d, G])  # (N, Nd + N)
    inv_s0 = 1.0 / max(sigma0_sq, 1e-6)
    MtM = inv_s0 * (M.conj().T @ M)
    Mty = inv_s0 * (M.conj().T @ y_d)
    I_tot = np.eye(M_tot, dtype=np.complex128)

    # Natural parameters for x_d (prior mean 0, prec 1) and e_pre (prior prec initialized from duty/sigma_I)
    duty = p01 / max(p01 + p10, 1e-9)
    gam_x = np.ones(Nd, dtype=float)
    h_x = np.zeros(Nd, dtype=np.complex128)
    gam_e = (np.full(N, 1.0 / max(duty * sigma_I_sq, 1e-4), dtype=float)
             if gam_e_init is None else gam_e_init.copy())
    h_e = np.zeros(N, dtype=np.complex128)

    x_hat = np.zeros(Nd, dtype=np.complex128)
    vx_hat = np.ones(Nd, dtype=float)
    e_hat = np.zeros(N, dtype=np.complex128)
    ve_hat = np.full(N, duty * sigma_I_sq, dtype=float)
    gam_state = np.full(N, duty, dtype=float)

    for it in range(n_iters):
        J = MtM.copy()
        J[np.arange(Nd), np.arange(Nd)] += gam_x
        J[np.arange(Nd, M_tot), np.arange(Nd, M_tot)] += gam_e
        rhs = Mty.copy()
        rhs[:Nd] += h_x
        rhs[Nd:] += h_e

        jf = cho_factor(J + 1e-9 * I_tot, lower=True)
        mu_post = cho_solve(jf, rhs)
        J_inv = cho_solve(jf, I_tot)
        v_post = np.maximum(np.real(np.diag(J_inv)), 1e-7)

        # --- Block 1: Data x_d cavity -> exact 16-QAM MMSE ---
        vp_x = v_post[:Nd]; mp_x = mu_post[:Nd]
        ge_x = np.maximum(1.0 / vp_x - gam_x, 1e-4)
        he_x = mp_x / vp_x - h_x
        ve_x = 1.0 / ge_x
        re_x = he_x * ve_x
        x_hat, vx_hat = c3m.qam_mmse_denoise(re_x, ve_x, const)
        vxs = np.maximum(vx_hat, 1e-5)
        gn_x = 1.0 / vxs - ge_x
        hn_x = x_hat / vxs - he_x
        val_x = gn_x > 1e-3
        gc_x = np.clip(gn_x, 1e-3, 1e4)
        mn_x = hn_x / np.maximum(gn_x, 1e-12)
        gu_x = np.where(val_x, gc_x, gam_x)
        hu_x = np.where(val_x, gc_x * mn_x, h_x)

        # --- Block 2: Pre-filter impulse e_pre cavity -> exact 2-State Markov HMM ---
        vp_e = v_post[Nd:]; mp_e = mu_post[Nd:]
        ge_e = np.maximum(1.0 / vp_e - gam_e, 1e-5)
        he_e = mp_e / vp_e - h_e
        ve_e = 1.0 / ge_e
        re_e = he_e * ve_e
        e_hat, ve_hat, gam_state = hmm_scalar_bg_denoise(re_e, ve_e, sigma_I_sq, p01, p10, eps0=1e-6)
        ves = np.maximum(ve_hat, 1e-5)
        gn_e = 1.0 / ves - ge_e
        hn_e = e_hat / ves - he_e
        val_e = gn_e > 1e-4
        gc_e = np.clip(gn_e, 1e-4, 1e5)
        mn_e = hn_e / np.maximum(gn_e, 1e-12)
        gu_e = np.where(val_e, gc_e, gam_e)
        hu_e = np.where(val_e, gc_e * mn_e, h_e)

        d_cur = 1.0 if it == 0 else damp
        gam_x = d_cur * gu_x + (1.0 - d_cur) * gam_x
        h_x = d_cur * hu_x + (1.0 - d_cur) * h_x
        gam_e = d_cur * gu_e + (1.0 - d_cur) * gam_e
        h_e = d_cur * hu_e + (1.0 - d_cur) * h_e

    # Final exact full-cov OAMP polish with inferred HMM state variance C_hat = s0 I + G diag(gam_state * sigma_I^2) G^H
    C_hat = sigma0_sq * np.eye(N, dtype=np.complex128) + (G * (gam_state * sigma_I_sq)[None, :]) @ G.conj().T
    x_pol = c3m.full_cov_ep_oamp(y_d, A_d, C_hat, const, None, None, n_iters=8, damp=0.65)
    # Pick whichever has lower whitened residual on hard QAM decisions (never worse than direct joint FG!)
    xq1 = const[np.argmin(np.abs(x_hat[:, None] - const[None, :]), axis=1)]
    xq2 = const[np.argmin(np.abs(x_pol[:, None] - const[None, :]), axis=1)]
    cf = cho_factor(C_hat + 1e-9 * np.eye(N), lower=True)
    r1 = y_d - A_d @ xq1; r2 = y_d - A_d @ xq2
    sc1 = float(np.real(np.vdot(r1, cho_solve(cf, r1))))
    sc2 = float(np.real(np.vdot(r2, cho_solve(cf, r2))))
    x_best = x_hat if sc1 < sc2 else x_pol
    return x_best, e_hat, ve_hat, gam_state, C_hat


def pilot_joint_sparse_ce(y, s_pil, G, obs_pil_all, obs_clusters, N, P, l_max, k_max, c1, sigma0_sq, sigma_I_sq):
    """Sol Step 2: Joint sparse channel + pre-filter impulse separation on the 40 clean pilot obs!
    Solves min_{h, e_pre} ||y_p - A_p(h) - G_p e_pre||^2 + lambda ||e_pre||_1 via alternating IRLS-SBL + OMP,
    AND compares against Multi-Subset leave-1-out CE by robust pilot residual.
    """
    G_p = G[obs_pil_all, :]  # (40, 256)
    # Active pre-filter columns that actually touch the 40 pilot obs
    act_e = np.where(np.sum(np.abs(G_p) ** 2, axis=0) > 1e-6)[0]
    G_pa = G_p[:, act_e]  # (40, ~88)
    Na = len(act_e)

    # Start from Huber IRLS OMP
    med_p = float(np.median(np.abs(y[obs_pil_all])))
    T_p = max(2.2 * med_p, 2.5)
    w_hub = np.ones(N, dtype=float)
    w_hub[obs_pil_all] = np.minimum(1.0, T_p / np.maximum(np.abs(y[obs_pil_all]), 1e-12))
    H_cur = c8.omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1, weights=w_hub)

    # Also build leave-1-out candidate set (4 subsets) and pick best initial H_cur
    best_H, best_loss = H_cur, float(np.sum(np.minimum(np.abs(y[obs_pil_all] - (H_cur @ s_pil)[obs_pil_all]), 0.5) ** 2))
    for drop_k in range(4):
        sub_obs = np.concatenate([obs_clusters[j] for j in range(4) if j != drop_k])
        H_sub = c8.omp_continuous_ce(y, s_pil, sub_obs, N, P, l_max, k_max, c1, weights=w_hub)
        loss = float(np.sum(np.minimum(np.abs(y[obs_pil_all] - (H_sub @ s_pil)[obs_pil_all]), 0.5) ** 2))
        if loss < best_loss:
            best_loss = loss; best_H = H_sub
    H_cur = best_H

    # Alternating joint pre-filter impulse separation (Block-SBL on G_pa) + whitened OMP CE on y_p!
    gam_a = np.full(Na, 0.2 * sigma_I_sq, dtype=float)
    I_p = np.eye(len(obs_pil_all), dtype=np.complex128)
    for _ in range(3):
        r_p = y[obs_pil_all] - (H_cur @ s_pil)[obs_pil_all]
        for _ in range(5):
            # Woodbury posterior for e_a given r_p = G_pa e_a + w_p
            C_p = (sigma0_sq + 0.002) * I_p + (G_pa * gam_a[None, :]) @ G_pa.conj().T
            cf = cho_factor(C_p + 1e-9 * I_p, lower=True)
            mu_a = gam_a * (G_pa.conj().T @ cho_solve(cf, r_p))
            GinvG = np.real(np.sum(np.conj(G_pa) * cho_solve(cf, G_pa), axis=0))
            v_a = np.maximum(gam_a - (gam_a ** 2) * GinvG, 0.0)
            m2 = np.abs(mu_a) ** 2 + v_a
            mp = np.pad(m2, 1, mode="edge")
            gam_a = np.clip((0.45 * mp[:-2] + mp[1:-1] + 0.45 * mp[2:]) / 1.9, 1e-7, 1e4)
            gam_a = np.where(gam_a < 2.0 * sigma0_sq, 1e-7, gam_a)
        C_pil_est = sigma0_sq * I_p + (G_pa * gam_a[None, :]) @ G_pa.conj().T
        L_cp = np.linalg.cholesky(C_pil_est + 1e-9 * I_p)
        H_try = c8.omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_cp, I_p))
        loss_try = float(np.sum(np.minimum(np.abs(y[obs_pil_all] - (H_try @ s_pil)[obs_pil_all]), 0.5) ** 2))
        if loss_try <= best_loss * 1.05:
            best_loss = min(best_loss, loss_try); H_cur = H_try
    return H_cur


def run_paired_seed(args):
    """Runs ALL 4 waveforms on the EXACT same paired channel (delays, dopplers, gains), impulse e_pre,
    background noise w_bg, and data symbols x_data!"""
    seed, snr_db, inr_db, duty, mean_burst = args
    N = 256; P = 4; l_max = 6; k_max = 1.5
    rng = np.random.default_rng(seed)
    const = c3m.gray_qam(16)
    sigma0_sq = 10.0 ** (-snr_db / 10.0)
    G = c3m.build_rx_filter_matrix(N, colored=True, bw_factor=0.42)
    I_N = np.eye(N, dtype=np.complex128)

    # Shared paired physical channel parameters + impulse + noise + data!
    delays = np.sort(rng.choice(np.arange(0, l_max + 1), size=P, replace=False))
    delays[0] = 0
    dopplers = rng.uniform(-k_max, k_max, size=P)
    pdp = np.exp(-0.22 * delays); pdp /= np.sum(pdp)
    gains = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) * np.sqrt(pdp / 2.0)
    gains = gains / np.maximum(np.linalg.norm(gains), 1e-12)

    clusters = [np.arange(0, 16), np.arange(64, 80), np.arange(128, 144), np.arange(192, 208)]
    obs_clusters = [np.arange(c[0] + l_max, c[-1] + 1) for c in clusters]
    obs_pil_all = np.concatenate(obs_clusters)  # 40 clean pilot obs
    pil_t = np.concatenate(clusters)
    data_t = np.setdiff1d(np.arange(N), pil_t)
    Nd = len(data_t)  # 192 data symbols
    didx = np.arange(Nd)

    u_pil = np.exp(-1j * math.pi * 7.0 * np.arange(len(pil_t)) * (np.arange(len(pil_t)) + 1) / float(len(pil_t)))
    x_data = const[rng.integers(0, len(const), size=Nd)]
    s_pil = np.zeros(N, dtype=np.complex128); s_pil[pil_t] = u_pil

    e_pre, states, v_z, ms = c3m.gen_markov_burst_noise(N, sigma0_sq, duty, mean_burst, inr_db, rng)
    w_bg = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sigma0_sq / 2.0)
    C_true = sigma0_sq * I_N + (G * v_z[None, :]) @ G.conj().T
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
        # Verify strictly zero data leakage onto the 40 pilot observation rows!
        assert float(np.max(np.abs(H_true[obs_pil_all, :][:, data_t]))) < 1e-12, f"Data leaked into pilot obs for {wf}!"

        s_true = s_pil.copy(); s_true[data_t] = U_d.conj().T @ x_data
        y = H_true @ s_true + G @ e_pre + w_bg
        y_clean = H_true @ s_true + w_bg
        A_true = H_true[:, data_t] @ U_d.conj().T

        wres = {}
        # 0. Sanity clean CE
        H_cl = c8.omp_continuous_ce(y_clean, s_pil, obs_pil_all, N, P, l_max, k_max, c1)
        x_cl = c3m.full_cov_ep_oamp(y_clean - H_cl @ s_pil, H_cl[:, data_t] @ U_d.conj().T, sigma0_sq * I_N, const, None, None, n_iters=8)
        wres["Ref_Clean_EstH"] = c3m.hard_ser_sub(x_cl, x_data, const, didx)

        # 1. Sol's Joint Pilot Sparse Separation CE + Nassar Joint [A_d, G] Factor-Graph EP + 3-Pass Soft-DD CE!
        H_j = pilot_joint_sparse_ce(y, s_pil, G, obs_pil_all, obs_clusters, N, P, l_max, k_max, c1, sigma0_sq, sigma_I_sq)
        x_j, e_j, ve_j, gam_j, C_j = joint_nassar_ep_fg(y - H_j @ s_pil, H_j[:, data_t] @ U_d.conj().T, G, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=14)
        for dd_pass in range(3):
            s_soft = s_pil.copy()
            # Use exact soft QAM expectation (prevents hard-decision error propagation!)
            s_soft[data_t] = U_d.conj().T @ x_j
            L_c = np.linalg.cholesky(C_j + 1e-9 * I_N)
            H_j = c8.omp_continuous_ce(y, s_soft, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
            x_j, e_j, ve_j, gam_j, C_j = joint_nassar_ep_fg(y - H_j @ s_pil, H_j[:, data_t] @ U_d.conj().T, G, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=14)
        wres["SM_Nassar_JointFG_3DD"] = c3m.hard_ser_sub(x_j, x_data, const, didx)

        # 2. Sol's Diagnostic: Frozen True H + Nassar Joint [A_d, G] Factor-Graph EP!
        x_nth, _, _, _, _ = joint_nassar_ep_fg(y - H_true @ s_pil, A_true, G, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=16)
        wres["Diag_TrueH_NassarFG"] = c3m.hard_ser_sub(x_nth, x_data, const, didx)

        # 3. Non-Cheating Oracles: (a) Unknown H with C_true[P,P] whitened pilot CE + C_true OAMP; (b) True H + True State Variance
        C_pil_t = C_true[np.ix_(obs_pil_all, obs_pil_all)]
        L_cp = np.linalg.cholesky(C_pil_t + 1e-9 * np.eye(len(obs_pil_all)))
        H_oc = c8.omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_cp, np.eye(len(obs_pil_all))))
        x_oc = c3m.full_cov_ep_oamp(y - H_oc @ s_pil, H_oc[:, data_t] @ U_d.conj().T, C_true, const, None, None, n_iters=10, damp=0.65)
        wres["Grid_OracCE_TrueState"] = c3m.hard_ser_sub(x_oc, x_data, const, didx)

        x_or = c3m.full_cov_ep_oamp(y - H_true @ s_pil, A_true, C_true, const, None, None, n_iters=10, damp=0.65)
        wres["Oracle_TrueH_TrueState"] = c3m.hard_ser_sub(x_or, x_data, const, didx)
        out[wf] = wres
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=48)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--snr", type=float, default=30.0)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c8_nassar_audit.json")
    args = ap.parse_args()
    t0 = time.time()

    jobs = [(880000 + t, args.snr, 25.0, 0.20, 8.0) for t in range(args.trials)]
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(run_paired_seed, jobs))

    summary = {"meta": {"trials": args.trials, "snr_db": args.snr, "paired_4wf": True}, "results": {}}
    tc = float(student_t.ppf(0.975, df=max(args.trials - 1, 1)))
    afdm_or = np.array([r["AFDM"]["Oracle_TrueH_TrueState"] for r in rows])

    for wf in ("AFDM", "OTFS", "OFDM", "SC-FDE"):
        mkeys = list(rows[0][wf].keys())
        agg = {}
        for k in mkeys:
            arr = np.array([r[wf][k] for r in rows], dtype=float)
            agg[k] = {
                "mean": float(np.mean(arr)),
                "se": float(np.std(arr, ddof=1) / math.sqrt(len(arr))),
                "ci95_hw": float(tc * np.std(arr, ddof=1) / math.sqrt(len(arr))),
                "nonzero_frames": int(np.sum(arr > 0)),
            }
        # Paired margin test: p_Steel - 15 * p_Oracle (both intra-waveform and vs AFDM Oracle)
        p_sm = np.array([r[wf]["SM_Nassar_JointFG_3DD"] for r in rows])
        p_or = np.array([r[wf]["Oracle_TrueH_TrueState"] for r in rows])
        diff_intra = p_sm - 15.0 * p_or
        diff_vs_afdm = p_sm - 15.0 * afdm_or
        agg["_paired_margin_intra_15x"] = {
            "mean": float(np.mean(diff_intra)),
            "ci95_lo": float(np.mean(diff_intra) - tc * np.std(diff_intra, ddof=1) / math.sqrt(len(rows))),
        }
        agg["_paired_margin_vs_AFDM_Oracle_15x"] = {
            "mean": float(np.mean(diff_vs_afdm)),
            "ci95_lo": float(np.mean(diff_vs_afdm) - tc * np.std(diff_vs_afdm, ddof=1) / math.sqrt(len(rows))),
        }
        wc = [r for r in rows if r["_pil_clean_frac"] >= 0.70]
        agg["_strat_well_cond_n"] = len(wc)
        agg["_strat_well_cond_SM"] = float(np.mean([r[wf]["SM_Nassar_JointFG_3DD"] for r in wc]))
        agg["_strat_well_cond_TrueH_FG"] = float(np.mean([r[wf]["Diag_TrueH_NassarFG"] for r in wc]))
        agg["_strat_well_cond_Oracle"] = float(np.mean([r[wf]["Oracle_TrueH_TrueState"] for r in wc]))
        summary["results"][wf] = agg

        print(f"\n=== Paired SNR={args.snr:.0f} dB | {wf} (n={args.trials}) ===")
        for k in mkeys:
            v = agg[k]
            print(f"  {k:26s}: SER = {v['mean']:.5f} +/- {v['se']:.5f} (nz={v['nonzero_frames']}/{args.trials})")
        sm_m = agg["SM_Nassar_JointFG_3DD"]["mean"]; or_m = agg["Oracle_TrueH_TrueState"]["mean"]
        print(f"  --> NassarFG/Oracle = {sm_m/max(or_m,1e-6):.2f}x | Paired (pSM - 15*pOr) = {agg['_paired_margin_intra_15x']['mean']:+.5f} (95% lo={agg['_paired_margin_intra_15x']['ci95_lo']:+.5f})")
        print(f"  --> Well-Cond (>=70% clean, n={len(wc)}): SM={agg['_strat_well_cond_SM']:.5f}, TrueH_FG={agg['_strat_well_cond_TrueH_FG']:.5f}, Oracle={agg['_strat_well_cond_Oracle']:.5f}")

    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved -> {args.out} in {summary['elapsed_sec']}s")


if __name__ == "__main__":
    main()
