#!/usr/bin/env python3
"""
Decisive Step-8 REVISE Equal-Pfa_win Recheck for Card I-20261125-k01.

Directly imports and reuses the channel, waveforms, and receivers from
`k_l2_r10_k01.py` UNCHANGED, while fixing the Astra REVISE critique:
  - ONE unified scoring function `score(rd_map, center)` (max over 5x3 window
    at `center`, divided by mean over map minus 17x9 guard block) called on
    ALL calibration, validation, and target frames (enforced by assertion).
  - Scope "window given a priori": `center` on target-free cal/val frames is
    drawn from the exact same center list as the paired target frames, and NO
    other truth enters cal/val frames (G2 asserted).
  - Primary Pfa_win = 1e-2 calibrated per waveform on independent target-free
    calibration frames and validated on independent target-free validation
    frames with exact Clopper-Pearson 95% CIs (C1).
  - Fresh seeds = original seed (2026112501) + 10000 = 2026122501.
  - Secondary readout: blind full-map detection maximizing the exact same
    5x3 / 17x9 score over all 141x29 = 4,089 centers (verified bit-exact
    against `score()` to < 1e-12), calibrated at per-map Pfa = 1e-2.
"""
import os
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")
import sys
print(f"sys.executable: {sys.executable}", flush=True)

import argparse
import json
import resource
import time
from multiprocessing import Pool
import numpy as np
import scipy.linalg as la
from scipy.ndimage import maximum_filter
from scipy.stats import beta as beta_dist

# Ensure sibling import of unchanged k_l2_r10_k01.py works regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_l2_r10_k01 as base  # noqa: E402

PRIMARY_ARMS = ["ridge_afdm", "ofdm_comb", "dbu_ofdm", "ofdm_blkpil"]
EQUAL_RIVALS = ["ofdm_comb", "dbu_ofdm", "ofdm_blkpil"]
DESC_ARMS = ["ofdm_2pil", "known_afdm", "ofdm_genie"]

G_TAU = 4  # 2*4 + 1 = 9 delay guard cells
G_NU = 8   # 2*8 + 1 = 17 Doppler guard cells -> 17x9 = 153 guard cells


def score(rd_map, center, role="unknown", counter=None):
    """
    THE ONE unified window scoring function used identically across
    calibration ('cal'), validation ('val'), and target ('pos') frames.

    Peak: max over 5x3 window centered at `center = (ni, ti)`.
    Background: mean over entire rd_map excluding 17x9 guard block at `center`.
    Returns: linear score ratio (peak / bg_mean).
    """
    if counter is not None:
        counter[role] = counter.get(role, 0) + 1
    ni, ti = int(center[0]), int(center[1])
    n_nu, n_tau = rd_map.shape
    sig = float(
        np.max(
            rd_map[
                max(0, ni - 2) : min(n_nu, ni + 3),
                max(0, ti - 1) : min(n_tau, ti + 2),
            ]
        )
    )
    mask = np.ones((n_nu, n_tau), dtype=bool)
    mask[
        max(0, ni - G_NU) : min(n_nu, ni + G_NU + 1),
        max(0, ti - G_TAU) : min(n_tau, ti + G_TAU + 1),
    ] = False
    bg_mean = max(float(np.mean(rd_map[mask])), 1e-15)
    return sig / bg_mean


def score_blind_full_map(rd_map):
    """
    Exact full-map maximum of `score(rd_map, (ni, ti))` over all 141x29 centers.
    Computes the excluded background sum directly as the sum of the 4 disjoint
    exterior rectangles (top, bottom, left-band, right-band) — NEVER subtracting
    the guard peak from total_sum, eliminating floating-point cancellation even
    at >100 dB dynamic range.
    """
    n_nu, n_tau = rd_map.shape
    win_max = maximum_filter(rd_map, size=(5, 3), mode="constant", cval=-np.inf)

    # Row sums for top [0:r0, :] and bottom [r1:n_nu, :] strips (disjoint from guard)
    row_sums = np.sum(rd_map, axis=1)
    row_prefix = np.zeros(n_nu + 1, dtype=np.float64)
    row_prefix[1:] = np.cumsum(row_sums)
    row_suffix = np.zeros(n_nu + 1, dtype=np.float64)
    row_suffix[:-1] = np.cumsum(row_sums[::-1])[::-1]

    # Left prefix-along-cols and right suffix-along-cols, then prefix-along-rows
    # Only sums entries strictly outside [c0, c1) -> NEVER touches the guard peak!
    col_pref = np.zeros((n_nu, n_tau + 1), dtype=np.float64)
    col_pref[:, 1:] = np.cumsum(rd_map, axis=1)
    col_suff = np.zeros((n_nu, n_tau + 1), dtype=np.float64)
    col_suff[:, :-1] = np.cumsum(rd_map[:, ::-1], axis=1)[:, ::-1]

    lp_row = np.zeros((n_nu + 1, n_tau + 1), dtype=np.float64)
    lp_row[1:, :] = np.cumsum(col_pref, axis=0)
    rs_row = np.zeros((n_nu + 1, n_tau + 1), dtype=np.float64)
    rs_row[1:, :] = np.cumsum(col_suff, axis=0)

    r0 = np.maximum(0, np.arange(n_nu) - G_NU)
    r1 = np.minimum(n_nu, np.arange(n_nu) + G_NU + 1)
    c0 = np.maximum(0, np.arange(n_tau) - G_TAU)
    c1 = np.minimum(n_tau, np.arange(n_tau) + G_TAU + 1)

    top_sum = row_prefix[r0][:, None]
    bot_sum = row_suffix[r1][:, None]
    left_sum = lp_row[r1[:, None], c0[None, :]] - lp_row[r0[:, None], c0[None, :]]
    right_sum = rs_row[r1[:, None], c1[None, :]] - rs_row[r0[:, None], c1[None, :]]

    bg_sum = top_sum + bot_sum + left_sum + right_sum
    bg_cnt = (n_nu * n_tau) - (r1 - r0)[:, None] * (c1 - c0)[None, :]
    bg_mean = np.maximum(bg_sum / bg_cnt, 1e-15)
    grid = win_max / bg_mean
    return float(np.max(grid)), grid


def clopper_pearson_ci(k, n, alpha=0.05):
    """Exact two-sided (1-alpha) Clopper-Pearson binomial confidence interval."""
    if n <= 0:
        return 0.0, 0.0, 1.0
    p = k / float(n)
    lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return p, lo, hi


def paired_delta_pd_vs_max_rival_ci(det_afdm, det_rivals_dict, n_boot=2000, seed=2026122599):
    """
    Paired bootstrap 95% CI for Delta Pd = Pd(ridge_afdm) - max_{r in rivals} Pd(r).
    Computes BOTH:
      - simultaneous max inside each bootstrap draw (primary conservative CI)
      - fixed empirical best-rival paired difference CI (diagnostic)
    """
    a = np.asarray(det_afdm, dtype=np.float64)
    n = len(a)
    rival_names = list(det_rivals_dict.keys())
    r_mat = np.stack([np.asarray(det_rivals_dict[rn], dtype=np.float64) for rn in rival_names], axis=0)  # (R, n)
    r_means = np.mean(r_mat, axis=1)
    best_idx = int(np.argmax(r_means))
    best_rival = rival_names[best_idx]
    point = float(np.mean(a) - r_means[best_idx])

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    a_boot = np.mean(a[idx], axis=1)  # (B,)
    r_boot = np.stack([np.mean(r_mat[j][idx], axis=1) for j in range(len(rival_names))], axis=0)  # (R, B)
    delta_sim = a_boot - np.max(r_boot, axis=0)
    delta_fix = a_boot - r_boot[best_idx]
    return {
        "best_rival": best_rival,
        "point": point,
        "ci95_simultaneous_max": [float(np.quantile(delta_sim, 0.025)), float(np.quantile(delta_sim, 0.975))],
        "ci95_fixed_best_rival": [float(np.quantile(delta_fix, 0.025)), float(np.quantile(delta_fix, 0.975))],
        "n_boot": n_boot,
        "boot_seed": seed,
    }


def eval_scene_pfa_worker(args):
    """
    Reuses exact channel, waveforms, and receivers from `k_l2_r10_k01.py` UNCHANGED,
    then scores every arm with the ONE unified `score(rd_map, center, role=role)`
    plus exact blind full-map score.
    """
    scene_seed, is_mov, los_db, clut_db, snr_t, arm_names, center, role, verify_blind_exact = args
    assert role in ("cal", "val", "pos"), f"Invalid role: {role}"
    if role in ("cal", "val"):
        # G2 hard invariant: no target exists on cal/val frames
        assert snr_t is None, "G2 violation: snr_t must be None on cal/val frames"
    else:
        assert snr_t is not None, "Target frame must have non-None snr_t"

    rng = np.random.default_rng(scene_seed)
    local_counter = {}

    # 1. Generate paired physical 3D scene (exact copy of base.eval_single_scene_worker setup)
    vT_cur = base.V_T_MOV if is_mov else np.zeros(3)
    mu_true = base.MU_MOV if is_mov else 0.0
    b_cur = base.B_MOV if is_mov else 0.0
    c1_tx = mu_true / (2.0 * base.N)
    nu_los_cur = base.NU_LOS_MOV if is_mov else 0.0
    nu_targ_cur = base.NU_TARG_MOV if is_mov else base.DNU_TARG_PHYS

    xq = rng.uniform(base.X0, base.X1, base.N_CLUT)
    yq = rng.uniform(-base.WY / 2.0, base.WY / 2.0, base.N_CLUT)
    tc, ncv, _ = base.bistatic_3d(xq, yq, np.zeros(base.N_CLUT), vT_cur)
    ac = (
        (rng.standard_normal(base.N_CLUT) + 1j * rng.standard_normal(base.N_CLUT))
        / np.sqrt(2.0 * base.N_CLUT)
        * (10.0 ** (clut_db / 20.0))
    )
    alos = np.exp(1j * rng.uniform(0, 2 * np.pi)) * (10.0 ** (los_db / 20.0))
    paths = [(alos, 0.0, nu_los_cur)] + [(a, float(t), float(v)) for a, t, v in zip(ac, tc, ncv)]
    if snr_t is not None:
        paths.append(
            (np.exp(1j * rng.uniform(0, 2 * np.pi)) * (10.0 ** (snr_t / 20.0)), base.TAU_TARG, nu_targ_cur)
        )
    else:
        assert len(paths) == base.N_CLUT + 1, "G2 violation: unexpected path count on cal/val frame"

    noise_l = [(rng.standard_normal(base.N) + 1j * rng.standard_normal(base.N)) / np.sqrt(2.0) for _ in range(base.M_SYM)]
    data_193 = [rng.choice(base.CONST16, len(base.DAT_AFDM)) for _ in range(base.M_SYM)]
    data_223 = [rng.choice(base.CONST16, len(base.DAT_OFDM)) for _ in range(base.M_SYM)]
    data_blk = [rng.choice(base.CONST16, len(base.ACT_OFDM)) for _ in range(base.M_SYM)]
    pil_blk_phases = [np.exp(1j * rng.uniform(0, 2 * np.pi, len(base.ACT_OFDM))) for _ in range(base.M_SYM)]

    A_tx = base.A_MOV if is_mov else base.daft_centered(0.0)
    M_los_tx = base.M_LOS_AFDM_MOV if is_mov else None
    Hq_cur = base.HQ_MOV if is_mov else base.HQ_STAT
    nuq_cur = base.NU_Q_OFDM if is_mov else np.zeros_like(base.NU_Q_OFDM)

    out_arms = {}
    blind_max_err = 0.0
    for arm in arm_names:
        is_afdm = arm in ("ridge_afdm", "known_afdm")
        use_193 = is_afdm or (arm == "ofdm_comb_193")
        c1_arm = c1_tx if is_afdm else 0.0
        A_arm = A_tx if is_afdm else base.F_MAT
        act_i = base.ACT_AFDM if use_193 else base.ACT_OFDM
        pil_i = base.PIL_AFDM if use_193 else base.PIL_OFDM
        dat_i = base.DAT_AFDM if use_193 else base.DAT_OFDM
        Upinv = base.U_F_PIL_AFDM_PINV if use_193 else base.U_F_PIL_OFDM_PINV
        p_amp = np.sqrt(base.N / float(len(act_i)))

        syms_cp, Xf_l, Xd_l = [], [], []
        pil_syms = {0} if arm in ("ofdm_blkpil", "ofdm_genie") else ({0, 4} if arm == "ofdm_2pil" else set())
        for m in range(base.M_SYM):
            xf = np.zeros(base.N, dtype=np.complex128)
            if arm in ("ofdm_blkpil", "ofdm_genie", "ofdm_2pil"):
                if m in pil_syms:
                    xf[act_i] = pil_blk_phases[m] * p_amp
                    xd = None
                else:
                    xd = data_blk[m]
                    xf[act_i] = xd * p_amp
            elif arm == "dbu_ofdm":
                xd = data_223[m]
                xsym = np.zeros(base.N, dtype=np.complex128)
                xsym[pil_i] = p_amp
                xsym[dat_i] = xd * p_amp
                xf = base.U_GRP_OFDM @ xsym
            else:
                xd = data_193[m] if use_193 else data_223[m]
                xf[pil_i] = p_amp
                xf[dat_i] = xd * p_amp
            syms_cp.append(base.make_cpp_centered(A_arm.conj().T @ xf, c1_arm))
            Xf_l.append(xf)
            Xd_l.append(xd)

        R_raw = base.apply_real_rrc_frame(syms_cp, paths)
        R_cfo = [
            (R_raw[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * (m * base.STRIDE + base.N_IDX) / float(base.N))
            for m in range(base.M_SYM)
        ]

        ser_l, R_res_l, S_hat_l = [], [], []
        if arm in ("ofdm_blkpil", "ofdm_genie", "ofdm_2pil"):
            gg = None
            if arm == "ofdm_genie":
                Q = len(Hq_cur)
                R_clut_only = base.apply_real_rrc_frame(syms_cp, paths[: base.N_CLUT + 1])
                R_cc = [
                    R_clut_only[m] * np.exp(-2j * np.pi * b_cur * (m * base.STRIDE + base.N_IDX) / float(base.N))
                    for m in range(base.M_SYM)
                ]
                Ga = np.zeros((Q, Q), dtype=np.complex128)
                ba = np.zeros(Q, dtype=np.complex128)
                for m in range(base.M_SYM):
                    ph = np.exp(2j * np.pi * nuq_cur * (m * base.STRIDE / float(base.N))) if is_mov else np.ones(Q)
                    Pm = np.column_stack([(Hq_cur[q] @ Xf_l[m]) * ph[q] for q in range(Q)])
                    Ga += Pm.conj().T @ Pm
                    ba += Pm.conj().T @ R_cc[m]
                gg = la.solve(Ga + 1e-3 * np.eye(Q), ba, assume_a="pos")
            Xh_d_l, S_hat_l, R_res_l = base.run_ofdm_joint(
                R_cfo, Xf_l, is_mov, Hq_cur, nuq_cur, act_i, pil_syms, n_em=3, genie_g=gg
            )
            for m in range(base.M_SYM):
                if m not in pil_syms:
                    ser_l.append(float(np.mean(np.abs(Xh_d_l[m] - Xd_l[m]) > 1e-4)))
        elif arm == "known_afdm":
            for m in range(base.M_SYM):
                yb = A_arm @ R_cfo[m]
                if M_los_tx is not None:
                    Phi = np.hstack(
                        [np.roll(Xf_l[m], s)[:, None] * base.U_F for s in [-1, 0, 1]]
                        + [(M_los_tx @ Xf_l[m])[:, None]]
                    )
                    ch = la.solve(Phi.conj().T @ Phi + 1e-5 * np.eye(3 * base.R_F + 1), Phi.conj().T @ yb, assume_a="pos")
                else:
                    Phi = np.hstack([np.roll(Xf_l[m], s)[:, None] * base.U_F for s in [-1, 0, 1]])
                    ch = la.solve(Phi.conj().T @ Phi + 1e-5 * np.eye(3 * base.R_F), Phi.conj().T @ yb, assume_a="pos")
                S_hat_l.append(A_arm.conj().T @ Xf_l[m])
                R_res_l.append(A_arm.conj().T @ (yb - Phi @ ch))
                ser_l.append(0.0)
        else:
            xp_v = np.zeros(base.N, dtype=np.complex128)
            xp_v[pil_i] = p_amp
            M_los_arm = M_los_tx if is_afdm else (base.M_LOS_OFDM_MOV if is_mov else None)
            U_basis_arm = base.U_F if use_193 else base.U_F_OFDM_RC
            for m in range(base.M_SYM):
                xh_d, xs_b, y_res = base.run_band3_plus_los(
                    A_arm @ R_cfo[m],
                    xp_v,
                    pil_i,
                    dat_i,
                    U_basis_arm,
                    Upinv,
                    M_los_arm,
                    use_u_grp=(arm == "dbu_ofdm"),
                    n_em=3,
                )
                ser_l.append(float(np.mean(np.abs(xh_d - Xd_l[m]) > 1e-4)))
                S_hat_l.append(A_arm.conj().T @ xs_b)
                R_res_l.append(A_arm.conj().T @ y_res)

        # Compute RD map strictly BEFORE touching `center`
        rdp = base.compute_rd_map(R_res_l, S_hat_l, c1_arm, mu_true)

        # Call THE ONE unified window scoring function
        win_score = score(rdp, center, role=role, counter=local_counter)
        blind_score, blind_grid = score_blind_full_map(rdp)
        if verify_blind_exact:
            # Verify ALL 4,089 cells against `score()` to < 1e-12
            for ni_chk in range(rdp.shape[0]):
                for ti_chk in range(rdp.shape[1]):
                    ref_s = score(rdp, (ni_chk, ti_chk), role="verify_blind", counter=None)
                    err = abs(float(blind_grid[ni_chk, ti_chk]) - ref_s)
                    if err > blind_max_err:
                        blind_max_err = err

        out_arms[arm] = {
            "win_score": float(win_score),
            "win_score_db": float(10.0 * np.log10(win_score)),
            "blind_score": float(blind_score),
            "blind_score_db": float(10.0 * np.log10(blind_score)),
            "ser": float(np.mean(ser_l)),
        }

    return {"arms": out_arms, "score_calls": local_counter, "blind_max_err": blind_max_err}


def run_g1_gate():
    """
    Gate G1:
      1. Verify new unified `score(rd_map, center)` reproduces old
         `k_l2_r10_k01.eval_rd_peak` SCNR numbers on ALL 4 primary arms
         (including Ridge-AFDM & OFDM-Comb) across 5 S1 scenarios within 0.01 dB.
      2. Verify `score_blind_full_map` matches brute-force `score()` across ALL
         4,089 centers to < 1e-12 on both a real S1 map AND a synthetic 1e10
         high-dynamic-range map (zero catastrophic cancellation).
    """
    # Synthetic 1e10 dynamic-range test (all 4,089 cells)
    rng_syn = np.random.default_rng(314159)
    syn_map = rng_syn.exponential(1.0, size=(141, 29))
    syn_map[70, 14] = 1e10
    _, syn_grid = score_blind_full_map(syn_map)
    syn_max_rel_err = 0.0
    for ni_chk in range(141):
        for ti_chk in range(29):
            ref_s = score(syn_map, (ni_chk, ti_chk), role="verify_syn", counter=None)
            rel_err = abs(float(syn_grid[ni_chk, ti_chk]) - ref_s) / max(ref_s, 1.0)
            if rel_err > syn_max_rel_err:
                syn_max_rel_err = rel_err
    assert syn_max_rel_err < 1e-12, f"G1 synthetic 1e10 blind cancellation error: {syn_max_rel_err}"

    rng_old = np.random.default_rng(2026112501)
    _ = rng_old.integers(1, 2**31 - 1, size=30)   # rrc
    _ = rng_old.integers(1, 2**31 - 1, size=100)  # cal
    _ = rng_old.integers(1, 2**31 - 1, size=100)  # val
    pos5_seeds = [int(s) for s in rng_old.integers(1, 2**31 - 1, size=5)]

    center_s1 = (base.NI_MOV, base.TI_EVAL)
    max_diff_db = 0.0
    real_blind_max_err = 0.0
    rows = []
    for idx_s, sd in enumerate(pos5_seeds):
        old_res = base.eval_single_scene_worker((sd, True, 18.0, 28.0, -11.0, PRIMARY_ARMS, False, 0.0))
        new_res = eval_scene_pfa_worker((sd, True, 18.0, 28.0, -11.0, PRIMARY_ARMS, center_s1, "pos", idx_s == 0))
        real_blind_max_err = max(real_blind_max_err, new_res["blind_max_err"])
        assert new_res["blind_max_err"] < 1e-12, f"Blind score mismatch on real S1 map: {new_res['blind_max_err']}"
        for arm in PRIMARY_ARMS:
            d_db = abs(new_res["arms"][arm]["win_score_db"] - old_res[arm]["scnr_db"])
            max_diff_db = max(max_diff_db, d_db)
            if arm in ("ridge_afdm", "ofdm_comb"):
                rows.append(
                    {
                        "seed": sd,
                        "arm": arm,
                        "old_scnr_db": old_res[arm]["scnr_db"],
                        "new_win_score_db": new_res["arms"][arm]["win_score_db"],
                        "abs_diff_db": d_db,
                    }
                )
    assert max_diff_db < 0.01, f"G1 FAILED: max_diff_db = {max_diff_db}"
    return {
        "pass": True,
        "max_abs_diff_db_all4": max_diff_db,
        "blind_real_all4089_max_err": real_blind_max_err,
        "blind_syn1e10_all4089_max_rel_err": syn_max_rel_err,
        "rows": rows,
    }


def run_batch(pool, tasks):
    if pool is None:
        return [eval_scene_pfa_worker(t) for t in tasks]
    return pool.map(eval_scene_pfa_worker, tasks)


def calibrate_validate_evaluate(cal_res, val_res, pos_res, arm_list, pfa_target=0.01):
    """Per-waveform calibration on cal_res -> validation on val_res -> detection on pos_res."""
    summary = {}
    win_det_lists = {}
    blind_det_lists = {}
    for arm in arm_list:
        cal_w = np.array([r["arms"][arm]["win_score"] for r in cal_res], dtype=np.float64)
        val_w = np.array([r["arms"][arm]["win_score"] for r in val_res], dtype=np.float64)
        pos_w = np.array([r["arms"][arm]["win_score"] for r in pos_res], dtype=np.float64)

        cal_b = np.array([r["arms"][arm]["blind_score"] for r in cal_res], dtype=np.float64)
        val_b = np.array([r["arms"][arm]["blind_score"] for r in val_res], dtype=np.float64)
        pos_b = np.array([r["arms"][arm]["blind_score"] for r in pos_res], dtype=np.float64)

        thr_w = float(np.quantile(cal_w, 1.0 - pfa_target, method="weibull"))
        k_val_w = int(np.sum(val_w > thr_w))
        p_val_w, lo_w, hi_w = clopper_pearson_ci(k_val_w, len(val_w))
        det_w = (pos_w > thr_w).astype(np.float64)
        k_pos_w = int(np.sum(det_w))
        pd_w, pd_lo_w, pd_hi_w = clopper_pearson_ci(k_pos_w, len(det_w))

        thr_b = float(np.quantile(cal_b, 1.0 - pfa_target, method="weibull"))
        k_val_b = int(np.sum(val_b > thr_b))
        p_val_b, lo_b, hi_b = clopper_pearson_ci(k_val_b, len(val_b))
        det_b = (pos_b > thr_b).astype(np.float64)
        k_pos_b = int(np.sum(det_b))
        pd_b, pd_lo_b, pd_hi_b = clopper_pearson_ci(k_pos_b, len(det_b))

        c1_point_ok = bool(0.005 <= p_val_w <= 0.015)
        c1_ci_overlap = bool(hi_w >= 0.005 and lo_w <= 0.020)

        summary[arm] = {
            "n_cal": int(len(cal_w)),
            "n_val": int(len(val_w)),
            "n_pos": int(len(pos_w)),
            "win": {
                "thr_linear": thr_w,
                "thr_db": float(10.0 * np.log10(thr_w)),
                "val_k_fa": k_val_w,
                "val_pfa": p_val_w,
                "val_ci95_cp": [lo_w, hi_w],
                "c1_point_in_0p5_1p5_e2": c1_point_ok,
                "c1_ci_overlaps_0p5_2p0_e2": c1_ci_overlap,
                "c1_pass": bool(c1_point_ok and c1_ci_overlap),
                "pos_k_det": k_pos_w,
                "pos_pd": pd_w,
                "pos_pd_ci95_cp": [pd_lo_w, pd_hi_w],
                "pos_score_db_mean": float(np.mean(10.0 * np.log10(pos_w))),
                "pos_score_db_median": float(np.median(10.0 * np.log10(pos_w))),
                "pos_ser_mean": float(np.mean([r["arms"][arm]["ser"] for r in pos_res])),
            },
            "blind": {
                "thr_linear": thr_b,
                "thr_db": float(10.0 * np.log10(thr_b)),
                "val_k_fa": k_val_b,
                "val_pfa": p_val_b,
                "val_ci95_cp": [lo_b, hi_b],
                "pos_k_det": k_pos_b,
                "pos_pd": pd_b,
                "pos_pd_ci95_cp": [pd_lo_b, pd_hi_b],
                "pos_score_db_mean": float(np.mean(10.0 * np.log10(pos_b))),
            },
        }
        win_det_lists[arm] = det_w
        blind_det_lists[arm] = det_b
    return summary, win_det_lists, blind_det_lists


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026122501, help="Fresh seed = 2026112501 + 10000")
    ap.add_argument("--mode", choices=["g1_only", "smoke", "full"], default="smoke")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--n-cal-s1", type=int, default=1050)
    ap.add_argument("--n-val-s1", type=int, default=1050)
    ap.add_argument("--n-pos-s1", type=int, default=200)
    ap.add_argument("--n-cal-g0", type=int, default=180)
    ap.add_argument("--n-val-g0", type=int, default=180)
    ap.add_argument("--n-pos-g0", type=int, default=100)
    ap.add_argument("--n-cal-desc", type=int, default=150)
    ap.add_argument("--n-val-desc", type=int, default=150)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    t0 = time.time()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    # Gate G1: always verify exact score reproduction on 5 original S1 scenes (all 4 primary arms) + 4,089-cell blind exactness
    print("[Gate G1] Verifying unified score() vs k_l2_r10_k01.eval_rd_peak on 5 S1 scenes (4 primary arms) + 4,089-cell blind...", flush=True)
    g1_report = run_g1_gate()
    print(
        f"[Gate G1] PASS: max_abs_diff_db_all4={g1_report['max_abs_diff_db_all4']:.3e} dB | blind_real={g1_report['blind_real_all4089_max_err']:.3e} | blind_syn1e10={g1_report['blind_syn1e10_all4089_max_rel_err']:.3e}",
        flush=True,
    )
    if args.mode == "g1_only":
        with open(args.out, "w") as f:
            json.dump({"g1_gate": g1_report}, f, indent=2)
        return

    if args.mode == "smoke":
        n_cal_s1, n_val_s1, n_pos_s1 = 20, 20, 10
        n_cal_g0, n_val_g0, n_pos_g0 = 10, 10, 8
        n_cal_desc, n_val_desc = 10, 10
    else:
        assert args.seed == 2026122501, f"Full mode must use pre-registered fresh seed 2026122501, got {args.seed}"
        n_cal_s1, n_val_s1, n_pos_s1 = args.n_cal_s1, args.n_val_s1, args.n_pos_s1
        n_cal_g0, n_val_g0, n_pos_g0 = args.n_cal_g0, args.n_val_g0, args.n_pos_g0
        n_cal_desc, n_val_desc = args.n_cal_desc, args.n_val_desc

    assert args.workers <= 16, f"G3 violation: workers={args.workers} > 16"

    # Historical seed freshness check: ensure ZERO overlap with original k_l2_r10_k01.py (seed 2026112501)
    rng_hist = np.random.default_rng(2026112501)
    hist_seeds = set(int(s) for s in rng_hist.integers(1, 2**31 - 1, size=1000))

    rng_master = np.random.default_rng(args.seed)
    # Draw strictly disjoint fresh seeds for every independent set
    total_seeds_needed = n_cal_s1 + n_val_s1 + n_pos_s1 + n_cal_g0 + n_val_g0 + n_pos_g0
    seed_set = set()
    seed_list = []
    while len(seed_list) < total_seeds_needed:
        cand = int(rng_master.integers(1, 2**31 - 1))
        if cand not in seed_set and cand not in hist_seeds:
            seed_set.add(cand)
            seed_list.append(cand)
    assert len(seed_set) == total_seeds_needed
    assert len(seed_set.intersection(hist_seeds)) == 0, "Fresh seed collided with historical k01 seed!"

    it = iter(seed_list)
    cal_seeds_s1 = [next(it) for _ in range(n_cal_s1)]
    val_seeds_s1 = [next(it) for _ in range(n_val_s1)]
    pos_seeds_s1 = [next(it) for _ in range(n_pos_s1)]
    cal_seeds_g0 = [next(it) for _ in range(n_cal_g0)]
    val_seeds_g0 = [next(it) for _ in range(n_val_g0)]
    pos_seeds_g0 = [next(it) for _ in range(n_pos_g0)]

    # Declared window center lists (identical distribution across cal, val, pos!)
    center_s1 = (int(base.NI_MOV), int(base.TI_EVAL))
    center_g0 = (int(base.NI_STAT), int(base.TI_EVAL))
    centers_pos_s1 = [center_s1] * n_pos_s1
    centers_cal_s1 = [centers_pos_s1[i % n_pos_s1] for i in range(n_cal_s1)]
    centers_val_s1 = [centers_pos_s1[i % n_pos_s1] for i in range(n_val_s1)]
    centers_pos_g0 = [center_g0] * n_pos_g0
    centers_cal_g0 = [centers_pos_g0[i % n_pos_g0] for i in range(n_cal_g0)]
    centers_val_g0 = [centers_pos_g0[i % n_pos_g0] for i in range(n_val_g0)]

    pool = Pool(processes=args.workers) if args.workers > 1 else None
    total_calls = {"cal": 0, "val": 0, "pos": 0}
    max_blind_err = 0.0

    def accum_calls(res_list):
        nonlocal max_blind_err
        for r in res_list:
            for k, v in r["score_calls"].items():
                total_calls[k] = total_calls.get(k, 0) + v
            if r["blind_max_err"] > max_blind_err:
                max_blind_err = r["blind_max_err"]

    try:
        # ------------------------------------------------------------------
        # 1. S1 Primary Arms (4 equal-overhead arms)
        # ------------------------------------------------------------------
        print(f"[S1 Primary] Running cal={n_cal_s1}, val={n_val_s1}, pos={n_pos_s1} on {PRIMARY_ARMS}...", flush=True)
        cal_s1_p = run_batch(
            pool,
            [(s, True, 18.0, 28.0, None, PRIMARY_ARMS, c, "cal", i == 0) for i, (s, c) in enumerate(zip(cal_seeds_s1, centers_cal_s1))],
        )
        accum_calls(cal_s1_p)
        print(f"  [S1 Primary] cal done in {time.time() - t0:.1f}s", flush=True)

        val_s1_p = run_batch(
            pool,
            [(s, True, 18.0, 28.0, None, PRIMARY_ARMS, c, "val", i == 0) for i, (s, c) in enumerate(zip(val_seeds_s1, centers_val_s1))],
        )
        accum_calls(val_s1_p)
        print(f"  [S1 Primary] val done in {time.time() - t0:.1f}s", flush=True)

        pos_s1_p = run_batch(
            pool,
            [(s, True, 18.0, 28.0, -11.0, PRIMARY_ARMS, c, "pos", i == 0) for i, (s, c) in enumerate(zip(pos_seeds_s1, centers_pos_s1))],
        )
        accum_calls(pos_s1_p)
        print(f"  [S1 Primary] pos done in {time.time() - t0:.1f}s", flush=True)

        s1_primary_sum, s1_win_det, s1_blind_det = calibrate_validate_evaluate(cal_s1_p, val_s1_p, pos_s1_p, PRIMARY_ARMS, pfa_target=0.01)

        # ------------------------------------------------------------------
        # 2. S1 Descriptive Arms (ofdm_2pil, known_afdm, ofdm_genie)
        # ------------------------------------------------------------------
        print(f"[S1 Descriptive] Running cal={n_cal_desc}, val={n_val_desc}, pos={n_pos_s1} on {DESC_ARMS}...", flush=True)
        cal_s1_d = run_batch(
            pool,
            [(s, True, 18.0, 28.0, None, DESC_ARMS, c, "cal", False) for s, c in zip(cal_seeds_s1[:n_cal_desc], centers_cal_s1[:n_cal_desc])],
        )
        accum_calls(cal_s1_d)
        val_s1_d = run_batch(
            pool,
            [(s, True, 18.0, 28.0, None, DESC_ARMS, c, "val", False) for s, c in zip(val_seeds_s1[:n_val_desc], centers_val_s1[:n_val_desc])],
        )
        accum_calls(val_s1_d)
        pos_s1_d = run_batch(
            pool,
            [(s, True, 18.0, 28.0, -11.0, DESC_ARMS, c, "pos", False) for s, c in zip(pos_seeds_s1, centers_pos_s1)],
        )
        accum_calls(pos_s1_d)
        s1_desc_sum, _, _ = calibrate_validate_evaluate(cal_s1_d, val_s1_d, pos_s1_d, DESC_ARMS, pfa_target=0.01)
        print(f"  [S1 Descriptive] done in {time.time() - t0:.1f}s", flush=True)

        # ------------------------------------------------------------------
        # 3. G0 Static Control (v_T = 0, mu = 0): Primary 4 arms
        # ------------------------------------------------------------------
        g0_arms = PRIMARY_ARMS
        print(f"[G0 Static Control] Running cal={n_cal_g0}, val={n_val_g0}, pos={n_pos_g0} on {g0_arms}...", flush=True)
        cal_g0 = run_batch(
            pool,
            [(s, False, 18.0, 28.0, None, g0_arms, c, "cal", False) for s, c in zip(cal_seeds_g0, centers_cal_g0)],
        )
        accum_calls(cal_g0)
        val_g0 = run_batch(
            pool,
            [(s, False, 18.0, 28.0, None, g0_arms, c, "val", False) for s, c in zip(val_seeds_g0, centers_val_g0)],
        )
        accum_calls(val_g0)
        pos_g0 = run_batch(
            pool,
            [(s, False, 18.0, 28.0, -11.0, g0_arms, c, "pos", False) for s, c in zip(pos_seeds_g0, centers_pos_g0)],
        )
        accum_calls(pos_g0)
        g0_sum, g0_win_det, g0_blind_det = calibrate_validate_evaluate(cal_g0, val_g0, pos_g0, g0_arms, pfa_target=0.01)
        print(f"  [G0 Static Control] done in {time.time() - t0:.1f}s", flush=True)

    finally:
        if pool is not None:
            pool.close()
            pool.join()

    # Hard assertion: ALL three paths called THE ONE unified score() exact expected number of times!
    exp_cal = n_cal_s1 * len(PRIMARY_ARMS) + n_cal_desc * len(DESC_ARMS) + n_cal_g0 * len(g0_arms)
    exp_val = n_val_s1 * len(PRIMARY_ARMS) + n_val_desc * len(DESC_ARMS) + n_val_g0 * len(g0_arms)
    exp_pos = n_pos_s1 * len(PRIMARY_ARMS) + n_pos_s1 * len(DESC_ARMS) + n_pos_g0 * len(g0_arms)
    assert total_calls["cal"] == exp_cal, f"cal score() call mismatch: {total_calls['cal']} != {exp_cal}"
    assert total_calls["val"] == exp_val, f"val score() call mismatch: {total_calls['val']} != {exp_val}"
    assert total_calls["pos"] == exp_pos, f"pos score() call mismatch: {total_calls['pos']} != {exp_pos}"
    assert max_blind_err < 1e-12, f"Blind score exactness check failed: {max_blind_err}"

    # ------------------------------------------------------------------
    # 4. Frozen Verdicts: C1, C2, C3, PASS_PRIMARY + Secondary Blind Readout
    # ------------------------------------------------------------------
    c1_per_arm = {arm: s1_primary_sum[arm]["win"]["c1_pass"] for arm in PRIMARY_ARMS}
    c1_pass = bool(all(c1_per_arm.values()))

    c2_boot = paired_delta_pd_vs_max_rival_ci(
        s1_win_det["ridge_afdm"],
        {r: s1_win_det[r] for r in EQUAL_RIVALS},
        n_boot=2000,
        seed=args.seed + 201,
    )
    c2_pass = bool(c2_boot["ci95_simultaneous_max"][0] > 0.0)

    c3_boot = paired_delta_pd_vs_max_rival_ci(
        g0_win_det["ridge_afdm"],
        {r: g0_win_det[r] for r in EQUAL_RIVALS},
        n_boot=2000,
        seed=args.seed + 301,
    )
    c3_lo, c3_hi = c3_boot["ci95_simultaneous_max"]
    c3_pass = bool(c3_lo <= 0.0 <= c3_hi)

    pass_primary = bool(c1_pass and c2_pass and c3_pass)

    # Secondary blind full-map contrast (descriptive / fallback check)
    s1_blind_boot = paired_delta_pd_vs_max_rival_ci(
        s1_blind_det["ridge_afdm"],
        {r: s1_blind_det[r] for r in EQUAL_RIVALS},
        n_boot=2000,
        seed=args.seed + 401,
    )
    g0_blind_boot = paired_delta_pd_vs_max_rival_ci(
        g0_blind_det["ridge_afdm"],
        {r: g0_blind_det[r] for r in EQUAL_RIVALS},
        n_boot=2000,
        seed=args.seed + 402,
    )

    elapsed = time.time() - t0
    core_hours = (elapsed * args.workers) / 3600.0
    ru_self = resource.getrusage(resource.RUSAGE_SELF)
    ru_chld = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_hours = (ru_self.ru_utime + ru_self.ru_stime + ru_chld.ru_utime + ru_chld.ru_stime) / 3600.0

    summary = {
        "meta": {
            "card": "I-20261125-k01",
            "recheck": "step8_revise_equal_pfa_win",
            "seed": args.seed,
            "fresh_seed_offset": args.seed - 2026112501,
            "historical_seed_overlap_count": 0,
            "quantile_method": "weibull",
            "mode": args.mode,
            "workers": args.workers,
            "elapsed_sec": round(elapsed, 2),
            "reserved_core_hours": round(core_hours, 4),
            "process_cpu_hours": round(cpu_hours, 4),
            "pfa_win_target": 0.01,
            "scope": "window given a priori (5x3 peak window, 17x9 guard excluded from background mean)",
            "declared_centers": {"S1": list(center_s1), "G0": list(center_g0)},
            "counts": {
                "n_cal_s1": n_cal_s1,
                "n_val_s1": n_val_s1,
                "n_pos_s1": n_pos_s1,
                "n_cal_g0": n_cal_g0,
                "n_val_g0": n_val_g0,
                "n_pos_g0": n_pos_g0,
                "n_cal_desc": n_cal_desc,
                "n_val_desc": n_val_desc,
            },
            "unified_score_call_audit": {
                "actual": total_calls,
                "expected": {"cal": exp_cal, "val": exp_val, "pos": exp_pos},
                "all_three_paths_verified": True,
                "blind_vs_score_max_abs_err": max_blind_err,
            },
        },
        "gates": {
            "G1_reproduce_old_scnr": g1_report,
            "G2_no_truth_in_cal_val": True,
            "G3_actual_core_hours_under_2": bool(core_hours <= 2.0),
        },
        "s1_primary_arms": s1_primary_sum,
        "s1_descriptive_arms": s1_desc_sum,
        "g0_static_control": g0_sum,
        "contrasts": {
            "C2_S1_window_delta_pd": c2_boot,
            "C3_G0_window_delta_pd": c3_boot,
            "secondary_S1_blind_delta_pd": s1_blind_boot,
            "secondary_G0_blind_delta_pd": g0_blind_boot,
        },
        "verdicts": {
            "C1_validity_per_arm": c1_per_arm,
            "C1_VALIDITY": c1_pass,
            "C2_S1_DELTA_PD_GT_0": c2_pass,
            "C3_G0_STATIC_CONTAINS_0": c3_pass,
            "PASS_PRIMARY": pass_primary,
            "SECONDARY_BLIND_BEATS_RIVALS": bool(s1_blind_boot["ci95_simultaneous_max"][0] > 0.0),
        },
    }

    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== SUMMARY (S1 Primary Window @ Pfa_win = 1e-2) ===", flush=True)
    for arm in PRIMARY_ARMS:
        w = s1_primary_sum[arm]["win"]
        b = s1_primary_sum[arm]["blind"]
        print(
            f"  {arm:12s} | WinThr={w['thr_db']:+5.2f} dB | ValPfa={w['val_pfa']*100:.2f}% [{w['val_ci95_cp'][0]*100:.2f},{w['val_ci95_cp'][1]*100:.2f}]% (C1={w['c1_pass']}) | WinPd={w['pos_pd']*100:5.1f}% | BlindPd={b['pos_pd']*100:5.1f}% (BlindValPfa={b['val_pfa']*100:.2f}%)",
            flush=True,
        )
    print("=== SUMMARY (S1 Descriptive @ Pfa_win = 1e-2) ===", flush=True)
    for arm in DESC_ARMS:
        w = s1_desc_sum[arm]["win"]
        b = s1_desc_sum[arm]["blind"]
        print(
            f"  {arm:12s} | WinThr={w['thr_db']:+5.2f} dB | ValPfa={w['val_pfa']*100:.2f}% | WinPd={w['pos_pd']*100:5.1f}% | BlindPd={b['pos_pd']*100:5.1f}%",
            flush=True,
        )
    print("=== SUMMARY (G0 Static Control @ Pfa_win = 1e-2) ===", flush=True)
    for arm in g0_arms:
        w = g0_sum[arm]["win"]
        print(f"  {arm:12s} | WinThr={w['thr_db']:+5.2f} dB | ValPfa={w['val_pfa']*100:.2f}% | WinPd={w['pos_pd']*100:5.1f}%", flush=True)
    print(f"C2 S1 Delta Pd = {c2_boot['point']:+.4f} (sim 95% CI {c2_boot['ci95_simultaneous_max']})", flush=True)
    print(f"C3 G0 Delta Pd = {c3_boot['point']:+.4f} (sim 95% CI {c3_boot['ci95_simultaneous_max']})", flush=True)
    print(f"VERDICTS: {summary['verdicts']}", flush=True)
    print(f"Elapsed: {elapsed:.1f}s ({core_hours:.4f} core-hours) -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
