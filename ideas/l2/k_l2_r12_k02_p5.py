#!/usr/bin/env python3
"""
Round-12 Step-8 Mechanism Diagnostic (Astra Kill-Argument P_3 / P_4 / P_5) for Card I-20261125-k02:
Parent k01 Curved-Ridge Privileged OFDM Front-End + Child k02 Complete Block-Pilot Back-End
Paired Full-Map Equal-Pfa_map (1%) Diagnostic at S1 (-11.0 dB).

Preserves both prior frozen k02 verdicts untouched (summary_k_r11_k02.json & summary_k_r11_k02_conf.json).
Directly imports unchanged parent `k_l2_r10_k01` and child `k_l2_r11_k02_conf` modules and verifies
actual worker output parity (SER, score, AND peak_idx) against independent parent & child references in G1.

Paired 8-Arm Design on Identical Fresh S1 (-11.0 dB) Scenes (N_cal=1500, N_val=2000, N_pos=300):
  1. ridge_afdm_st           : Main blind practical AFDM arm (verbatim k02_conf).
  2. ofdm_p5_full            : PRIMARY P_5 arm — verbatim parent k01 curved-ridge privileged front-end
                               (`base.TAU_Q_OFDM`, `base.HQ_MOV`, `base.NU_Q_OFDM`, `base.run_ofdm_joint`)
                               plugged directly into verbatim child `ofdm_blkpil_st` complete back-end
                               (1st Exact-RC QR -> `refine_symbols_joint_em` -> 2nd Exact-RC QR).
  3. ofdm_p5_pre_fb          : Single-factor P_4 ablation — exact same parent curved-ridge front-end,
                               1st Exact-RC QR ONLY (no symbol update / 2nd projection).
  4. ofdm_p5_lin_pgrid_full  : Single-factor P_3 PURE-CURVATURE ablation — IDENTICAL parent delay grid
                               (`base.TAU_Q_OFDM`), IDENTICAL fit (`fit_genie_g_parent_verbatim`), IDENTICAL
                               solver (`base.run_ofdm_joint`), IDENTICAL complete child back-end; ONLY switches
                               `base.NU_Q_OFDM` (curved) -> `MU_MOV * base.TAU_Q_OFDM[1:]` (straight)!
  5. ofdm_genie_child_full   : Child straight-ridge privileged front-end (`k02.HQ_OFDM_LIN_MOV`,
                               `k02.run_ofdm_blkpil_blind`) + complete child back-end.
  6. ofdm_genie_child_1pass  : Verbatim k02_conf `ofdm_genie_st` (child straight-ridge front-end + 1st QR only).
  7. ofdm_blkpil_st          : Verbatim k02_conf practical equal-overhead blind block-pilot OFDM.
  8. known_ofdm_bp_st        : Known-payload OFDM upper bound on the exact same block-pilot burst `syms_bp`.

Plus pos-only paired SER decomposition cleanly isolating ALL 3 sub-factors of P_3 with per-scene paired 95% CIs:
  (a) Pure curvature (same parent grid, same fit, same parent solver),
  (b) Pure delay-knot span (parent [2.02..12.27] vs child [1.80..12.60], same straight ridge, same parent solver),
  (c) Pure solver hyperparameters (parent vs child solver on identical ridge & grid).
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
from scipy.stats import beta as beta_dist, betabinom as betabinom_dist, binom as binom_dist, norm as norm_dist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_l2_r10_k01 as base  # noqa: E402
import k_l2_r11_k02_conf as k02  # noqa: E402

CAL_ARMS = [
    "ridge_afdm_st",
    "ofdm_p5_full",
    "ofdm_p5_pre_fb",
    "ofdm_p5_lin_pgrid_full",
    "ofdm_genie_child_full",
    "ofdm_genie_child_1pass",
    "ofdm_blkpil_st",
    "known_ofdm_bp_st",
]

# Pure-curvature control on the EXACT SAME parent delay grid `base.TAU_Q_OFDM`:
NU_Q_LIN_PGRID = np.concatenate([[base.DNU_LOS_MOV], base.MU_MOV * base.TAU_Q_OFDM[1:]])
HQ_LIN_PGRID = base.build_hq(base.TAU_Q_OFDM, NU_Q_LIN_PGRID)

HQ_CURV_STACK = np.ascontiguousarray(np.stack(base.HQ_MOV, axis=0))
HQ_LIN_CGRID_LIST = [k02.HQ_OFDM_LIN_MOV[q] for q in range(len(k02.HQ_OFDM_LIN_MOV))]


def fit_genie_g_parent_verbatim(Hq_list, nuq, syms_bp, Xf_bp, paths_clut_only, b_cur):
    """Verbatim parent k01 genie clutter fit (`k_l2_r10_k01_pfa.py:269-282`)."""
    Q = len(Hq_list)
    R_clut_only = base.apply_real_rrc_frame(syms_bp, paths_clut_only)
    R_cc = [
        R_clut_only[m] * np.exp(-2j * np.pi * b_cur * (m * base.STRIDE + base.N_IDX) / float(base.N))
        for m in range(base.M_SYM)
    ]
    Ga = np.zeros((Q, Q), dtype=np.complex128)
    ba = np.zeros(Q, dtype=np.complex128)
    for m in range(base.M_SYM):
        ph = np.exp(2j * np.pi * nuq * (m * base.STRIDE / float(base.N)))
        Pm = np.column_stack([(Hq_list[q] @ Xf_bp[m]) * ph[q] for q in range(Q)])
        Ga += Pm.conj().T @ Pm
        ba += Pm.conj().T @ R_cc[m]
    return la.solve(Ga + 1e-3 * np.eye(Q), ba, assume_a="pos")


def fit_genie_g_child_verbatim(Hq_stack, nuq, syms_bp, Xf_bp, paths_clut_only, b_cur):
    """Verbatim child k02_conf genie clutter fit (`k_l2_r11_k02_conf.py:690-698`)."""
    Q = len(Hq_stack)
    R_clut_bp = base.apply_real_rrc_frame(syms_bp, paths_clut_only)
    R_cc_bp = [R_clut_bp[m] * np.exp(-2j * np.pi * b_cur * k02.T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
    Ga = np.zeros((Q, Q), dtype=np.complex128)
    ba = np.zeros(Q, dtype=np.complex128)
    for m in range(base.M_SYM):
        ph = np.exp(2j * np.pi * nuq * (m * base.STRIDE / float(base.N)))
        Pm = (Hq_stack @ Xf_bp[m]).T * ph[None, :]
        Ga += Pm.conj().T @ Pm
        ba += Pm.conj().T @ R_cc_bp[m]
    return la.solve(Ga + 1e-3 * np.eye(Q), ba, assume_a="pos")


def _finite_lt(val, bound):
    return bool(np.isfinite(val) and (float(val) < float(bound)))


def _strict_ser(xh_list, ref_list, nonfinite_flags=None, tag="ser"):
    """Compute mean symbol error rate while strictly rejecting any NaN/Inf in estimates or references."""
    errs = []
    for m_idx, (xh, rf) in enumerate(zip(xh_list, ref_list)):
        xh_a = np.asarray(xh)
        rf_a = np.asarray(rf)
        if (not np.all(np.isfinite(xh_a))) or (not np.all(np.isfinite(rf_a))):
            if nonfinite_flags is not None:
                nonfinite_flags.append(f"nonfinite_symbol:{tag}[{m_idx}]")
            return float("nan")
        errs.append(float(np.mean(np.abs(xh_a - rf_a) > 1e-4)))
    return float(np.mean(errs))


def eval_p5_scene_worker(args):
    """Evaluate all 8 paired diagnostic arms on ONE fresh S1 3D physical scene."""
    scene_seed, snr_t, role, verify_exact, compute_p3_subfactors = args
    if role not in ("cal", "val", "pos"):
        raise ValueError(f"Invalid role: {role}")
    if role in ("cal", "val"):
        if snr_t is not None:
            raise ValueError("G2 violation: snr_t must be None on cal/val frames")
    else:
        if snr_t is None:
            raise ValueError("Target frame must have non-None snr_t")

    rng = np.random.default_rng(int(scene_seed))
    local_counter = {}

    vT_cur = base.V_T_MOV
    mu_true = base.MU_MOV
    b_cur = base.B_MOV
    c1_tx = base.C1_MOV
    nu_los_cur = base.NU_LOS_MOV
    dnu_los_cur = base.DNU_LOS_MOV

    xq = rng.uniform(base.X0, base.X1, base.N_CLUT)
    yq = rng.uniform(-base.WY / 2.0, base.WY / 2.0, base.N_CLUT)
    tc, ncv, _ = base.bistatic_3d(xq, yq, np.zeros(base.N_CLUT), vT_cur)
    ac = (rng.standard_normal(base.N_CLUT) + 1j * rng.standard_normal(base.N_CLUT)) / np.sqrt(2.0 * base.N_CLUT) * (10.0 ** (28.0 / 20.0))
    alos = np.exp(1j * rng.uniform(0, 2 * np.pi)) * (10.0 ** (18.0 / 20.0))
    paths = [(alos, 0.0, nu_los_cur)] + [(a, float(t), float(v)) for a, t, v in zip(ac, tc, ncv)]

    true_cell = None
    if snr_t is not None:
        tau_t = base.TAU_TARG
        nu_t = base.NU_TARG_MOV
        ni_true = int(np.argmin(np.abs(base.DNU_GRID - (nu_t - (b_cur + mu_true * tau_t)))))
        ti_true = int(np.argmin(np.abs(base.TAU_GRID - tau_t)))
        true_cell = [ni_true, ti_true]
        paths.append((np.exp(1j * rng.uniform(0, 2 * np.pi)) * (10.0 ** (snr_t / 20.0)), tau_t, nu_t))
    else:
        if len(paths) != base.N_CLUT + 1:
            raise ValueError("G2 violation: cal/val path count mismatch")

    noise_l = [(rng.standard_normal(base.N) + 1j * rng.standard_normal(base.N)) / np.sqrt(2.0) for _ in range(base.M_SYM)]
    master_qam = rng.choice(base.CONST16, size=(base.M_SYM, len(base.ACT_OFDM)))
    pil_blk_phases = [np.exp(1j * rng.uniform(0, 2 * np.pi, len(base.ACT_OFDM))) for _ in range(base.M_SYM)]

    data_169 = [master_qam[m, : len(k02.DAT_AFDM_169)] for m in range(base.M_SYM)]
    data_blk = [master_qam[m, :] for m in range(base.M_SYM)]

    out_arms = {}
    exact_max_rel_err = 0.0
    extra_diag = {}
    nonfinite_flags = []

    def record_arm(name, rdp, ser_val, ser_pre_val=None):
        nonlocal exact_max_rel_err
        if not np.all(np.isfinite(rdp)):
            nonfinite_flags.append(f"nonfinite_rdp:{name}")
        sc, (ni_h, ti_h), grid = k02.score_cut_full_map(rdp, role=role, counter=local_counter)
        if (not np.isfinite(sc)) or (float(sc) <= 0.0) or (not np.all(np.isfinite(grid))):
            nonfinite_flags.append(f"nonfinite_or_nonpos_score:{name}:{sc}")
        if verify_exact:
            for ni_c in range(rdp.shape[0]):
                for ti_c in range(rdp.shape[1]):
                    ref = k02.score_cut(rdp, (ni_c, ti_c), role="verify", counter=None)
                    re = abs(float(grid[ni_c, ti_c]) - ref) / max(abs(ref), 1e-15)
                    if not np.isfinite(re):
                        exact_max_rel_err = float("inf")
                    elif np.isfinite(exact_max_rel_err) and re > exact_max_rel_err:
                        exact_max_rel_err = re
        sc_db = float(10.0 * np.log10(sc)) if (np.isfinite(sc) and float(sc) > 0.0) else float("nan")
        rec = {
            "score": float(sc),
            "score_db": sc_db,
            "peak_idx": [int(ni_h), int(ti_h)],
            "ser": float(ser_val),
        }
        if ser_pre_val is not None:
            rec["ser_pre_fb"] = float(ser_pre_val)
        out_arms[name] = rec

    # --- 1. ridge_afdm_st (verbatim k_l2_r11_k02_conf.py:523-571) ---
    p_af = np.sqrt(base.N / float(len(base.ACT_AFDM)))
    syms_af = []
    for m in range(base.M_SYM):
        xf = np.zeros(base.N, dtype=np.complex128)
        xf[k02.PIL_AFDM_24] = p_af
        xf[k02.DAT_AFDM_169] = data_169[m] * p_af
        syms_af.append(base.make_cpp_centered(base.A_MOV.conj().T @ xf, c1_tx))
    R_raw_af = base.apply_real_rrc_frame(syms_af, paths)
    R_cfo_af = [(R_raw_af[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * k02.T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
    R_stack_af = np.concatenate(R_cfo_af)
    xp_af = np.zeros(base.N, dtype=np.complex128)
    xp_af[k02.PIL_AFDM_24] = p_af
    Xh_af1, S_af1 = [], []
    for m in range(base.M_SYM):
        xh_d, xs_b, _ = k02.run_band3_plus_los_custom(
            base.A_MOV @ R_cfo_af[m], xp_af, k02.PIL_AFDM_24, k02.DAT_AFDM_169,
            base.U_F, k02.U_F_PIL_AFDM24_PINV, base.M_LOS_AFDM_MOV, u_grp=None, n_em=3,
        )
        Xh_af1.append(xh_d)
        S_af1.append(base.A_MOV.conj().T @ xs_b)
    ser_af_pre = _strict_ser(Xh_af1, data_169, nonfinite_flags, "ridge_afdm_st.pre")
    ch0_af, _, res_af0, _ = k02.qr_project_exact_rc(R_stack_af, S_af1, c1_tx, mu_true, dnu_los_cur, is_mov=True)
    s2_af0 = max(1e-2, float(np.mean(np.abs(res_af0) ** 2)))
    Xh_af2, Xs_af2 = k02.refine_symbols_joint_em(
        R_cfo_af, ch0_af, [xp_af] * base.M_SYM, [k02.DAT_AFDM_169] * base.M_SYM,
        p_af, k02.HQ_AFDM_MOV, base.A_MOV, mu_true, dnu_los_cur, s2_af0, u_grp=None,
    )
    S_af2 = [base.A_MOV.conj().T @ Xs_af2[m] for m in range(base.M_SYM)]
    _, R_res_af, _, _ = k02.qr_project_exact_rc(R_stack_af, S_af2, c1_tx, mu_true, dnu_los_cur, is_mov=True)
    ser_af_post = _strict_ser(Xh_af2, data_169, nonfinite_flags, "ridge_afdm_st.post")
    record_arm("ridge_afdm_st", base.compute_rd_map(R_res_af, S_af2, c1_tx, mu_true), ser_af_post, ser_pre_val=ser_af_pre)

    # --- Shared OFDM Block-Pilot (1/8 = 12.50%) TX burst for ALL 7 OFDM arms ---
    p_of = np.sqrt(base.N / float(len(base.ACT_OFDM)))
    syms_bp, Xf_bp = [], []
    pil_only_bp = {}
    xp_zero = np.zeros(base.N, dtype=np.complex128)
    for m in range(base.M_SYM):
        xf = np.zeros(base.N, dtype=np.complex128)
        if m == 0:
            xf[base.ACT_OFDM] = pil_blk_phases[m] * p_of
            pil_only_bp[0] = xf.copy()
        else:
            xf[base.ACT_OFDM] = data_blk[m] * p_of
        syms_bp.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
        Xf_bp.append(xf)
    R_raw_bp = base.apply_real_rrc_frame(syms_bp, paths)
    R_cfo_bp = [(R_raw_bp[m] + noise_l[m]) * np.exp(-2j * np.pi * b_cur * k02.T_ALL[m] / float(base.N)) for m in range(base.M_SYM)]
    R_stack_bp = np.concatenate(R_cfo_bp)
    xp_list_bp = [pil_only_bp[0] if m == 0 else xp_zero for m in range(base.M_SYM)]
    di_list_bp = [base.ACT_OFDM for _ in range(base.M_SYM)]
    paths_clut_only = paths[: base.N_CLUT + 1]

    def run_child_complete_backend(S_init, arm_tag):
        ch_1, R_res_1, res_0, _ = k02.qr_project_exact_rc(R_stack_bp, S_init, 0.0, mu_true, dnu_los_cur, is_mov=True)
        s2_0 = max(1e-2, float(np.mean(np.abs(res_0) ** 2)))
        Xh_post, Xs_post = k02.refine_symbols_joint_em(
            R_cfo_bp, ch_1, xp_list_bp, di_list_bp, p_of, k02.HQ_OFDM_MOV_LIN, base.F_MAT, mu_true, dnu_los_cur, s2_0, u_grp=None, pil_syms=(0,)
        )
        S_post = [base.F_MAT.conj().T @ Xs_post[m] for m in range(base.M_SYM)]
        _, R_res_2, _, _ = k02.qr_project_exact_rc(R_stack_bp, S_post, 0.0, mu_true, dnu_los_cur, is_mov=True)
        ser_post = _strict_ser([Xh_post[m] for m in range(1, base.M_SYM)], data_blk[1:], nonfinite_flags, f"{arm_tag}.post")
        return R_res_1, R_res_2, S_post, ser_post

    # --- 2 & 3. PRIMARY P_5 (ofdm_p5_full) + P_4 ablation (ofdm_p5_pre_fb) ---
    gg_curv = fit_genie_g_parent_verbatim(base.HQ_MOV, base.NU_Q_OFDM, syms_bp, Xf_bp, paths_clut_only, b_cur)
    Xh_p5_pre, S_p5_pre, _ = base.run_ofdm_joint(
        R_cfo_bp, xp_list_bp, True, base.HQ_MOV, base.NU_Q_OFDM, base.ACT_OFDM, {0}, n_em=3, genie_g=gg_curv, reg=1e-2
    )
    ser_p5_pre = _strict_ser([Xh_p5_pre[m] for m in range(1, base.M_SYM)], data_blk[1:], nonfinite_flags, "ofdm_p5_full.pre")
    R_p5_1, R_p5_2, S_p5_post, ser_p5_post = run_child_complete_backend(S_p5_pre, "ofdm_p5_full")
    record_arm("ofdm_p5_pre_fb", base.compute_rd_map(R_p5_1, S_p5_pre, 0.0, mu_true), ser_p5_pre, ser_pre_val=ser_p5_pre)
    record_arm("ofdm_p5_full", base.compute_rd_map(R_p5_2, S_p5_post, 0.0, mu_true), ser_p5_post, ser_pre_val=ser_p5_pre)

    # --- 4. P_3 PURE-CURVATURE ablation (ofdm_p5_lin_pgrid_full) ---
    # IDENTICAL delay grid (base.TAU_Q_OFDM), IDENTICAL fit, IDENTICAL solver (base.run_ofdm_joint), IDENTICAL complete back-end;
    # ONLY ridge Doppler changes from curved `base.NU_Q_OFDM` -> straight `NU_Q_LIN_PGRID`!
    gg_lin_pg = fit_genie_g_parent_verbatim(HQ_LIN_PGRID, NU_Q_LIN_PGRID, syms_bp, Xf_bp, paths_clut_only, b_cur)
    Xh_lp_pre, S_lp_pre, _ = base.run_ofdm_joint(
        R_cfo_bp, xp_list_bp, True, HQ_LIN_PGRID, NU_Q_LIN_PGRID, base.ACT_OFDM, {0}, n_em=3, genie_g=gg_lin_pg, reg=1e-2
    )
    ser_lp_pre = _strict_ser([Xh_lp_pre[m] for m in range(1, base.M_SYM)], data_blk[1:], nonfinite_flags, "ofdm_p5_lin_pgrid_full.pre")
    _, R_lp_2, S_lp_post, ser_lp_post = run_child_complete_backend(S_lp_pre, "ofdm_p5_lin_pgrid_full")
    record_arm("ofdm_p5_lin_pgrid_full", base.compute_rd_map(R_lp_2, S_lp_post, 0.0, mu_true), ser_lp_post, ser_pre_val=ser_lp_pre)

    # --- 5 & 6. Child straight-ridge genie: 1pass (verbatim k02_conf ofdm_genie_st) & + complete back-end ---
    gg_lin_cg = fit_genie_g_child_verbatim(k02.HQ_OFDM_LIN_MOV, k02.NU_Q_LIN_MOV, syms_bp, Xf_bp, paths_clut_only, b_cur)
    Xh_cg_pre, S_cg_pre = k02.run_ofdm_blkpil_blind(
        R_cfo_bp, pil_only_bp, True, k02.HQ_OFDM_LIN_MOV, k02.NU_Q_LIN_MOV, base.ACT_OFDM, n_em=3, genie_g=gg_lin_cg, reg=1e-2
    )
    ser_cg_pre = _strict_ser([Xh_cg_pre[m] for m in range(1, base.M_SYM)], data_blk[1:], nonfinite_flags, "ofdm_genie_child.pre")
    R_cg_1, R_cg_2, S_cg_post, ser_cg_post = run_child_complete_backend(S_cg_pre, "ofdm_genie_child_full")
    record_arm("ofdm_genie_child_1pass", base.compute_rd_map(R_cg_1, S_cg_pre, 0.0, mu_true), ser_cg_pre, ser_pre_val=ser_cg_pre)
    record_arm("ofdm_genie_child_full", base.compute_rd_map(R_cg_2, S_cg_post, 0.0, mu_true), ser_cg_post, ser_pre_val=ser_cg_pre)

    # --- 7. ofdm_blkpil_st (verbatim k02_conf practical equal-overhead blind block-pilot OFDM) ---
    Xh_bp_pre, S_bp1 = k02.run_ofdm_blkpil_blind(
        R_cfo_bp, pil_only_bp, True, k02.HQ_OFDM_LIN_MOV, k02.NU_Q_LIN_MOV, base.ACT_OFDM, n_em=3, genie_g=None, reg=1e-2
    )
    ser_bp_pre = _strict_ser([Xh_bp_pre[m] for m in range(1, base.M_SYM)], data_blk[1:], nonfinite_flags, "ofdm_blkpil_st.pre")
    _, R_bp_2, S_bp2, ser_bp_post = run_child_complete_backend(S_bp1, "ofdm_blkpil_st")
    record_arm("ofdm_blkpil_st", base.compute_rd_map(R_bp_2, S_bp2, 0.0, mu_true), ser_bp_post, ser_pre_val=ser_bp_pre)

    # --- 8. known_ofdm_bp_st (oracle known payload on the EXACT SAME syms_bp burst) ---
    S_true_bp = [base.F_MAT.conj().T @ Xf_bp[m] for m in range(base.M_SYM)]
    _, R_res_ko, _, _ = k02.qr_project_exact_rc(R_stack_bp, S_true_bp, 0.0, mu_true, dnu_los_cur, is_mov=True)
    record_arm("known_ofdm_bp_st", base.compute_rd_map(R_res_ko, S_true_bp, 0.0, mu_true), 0.0, ser_pre_val=0.0)

    # --- Optional pos-only P_3 sub-factor SER isolation (curvature vs knot-span vs solver) ---
    if compute_p3_subfactors:
        Xh_curv_cs, _ = k02.run_ofdm_blkpil_blind(
            R_cfo_bp, pil_only_bp, True, HQ_CURV_STACK, base.NU_Q_OFDM, base.ACT_OFDM, n_em=3, genie_g=gg_curv, reg=1e-2
        )
        Xh_lin_cg_ps, _, _ = base.run_ofdm_joint(
            R_cfo_bp, xp_list_bp, True, HQ_LIN_CGRID_LIST, k02.NU_Q_LIN_MOV, base.ACT_OFDM, {0}, n_em=3, genie_g=gg_lin_cg, reg=1e-2
        )
        extra_diag = {
            "ser_curv_pgrid_psolver": ser_p5_pre,
            "ser_lin_pgrid_psolver": ser_lp_pre,
            "ser_lin_cgrid_psolver": _strict_ser([Xh_lin_cg_ps[m] for m in range(1, base.M_SYM)], data_blk[1:], nonfinite_flags, "p3.lin_cgrid_psolver"),
            "ser_lin_cgrid_csolver": ser_cg_pre,
            "ser_curv_pgrid_csolver": _strict_ser([Xh_curv_cs[m] for m in range(1, base.M_SYM)], data_blk[1:], nonfinite_flags, "p3.curv_pgrid_csolver"),
        }

    return {
        "scene_seed": int(scene_seed),
        "arms": out_arms,
        "true_cell": true_cell,
        "score_calls": local_counter,
        "exact_max_rel_err": exact_max_rel_err,
        "nonfinite_flags": nonfinite_flags,
        "p3_subfactors": extra_diag,
    }


def _sanitize_nonfinite(obj, reasons, path="root"):
    """Recursively replace any NaN/Inf float with None and record path in `reasons`."""
    if isinstance(obj, dict):
        return {k: _sanitize_nonfinite(v, reasons, f"{path}.{k}") for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_nonfinite(v, reasons, f"{path}[{i}]") for i, v in enumerate(obj)]
    if isinstance(obj, (float, np.floating)):
        fv = float(obj)
        if not np.isfinite(fv):
            reasons.append(f"Non-finite float at {path}: {fv}")
            return None
        return fv
    return obj


def _write_json_strict_atomic(out_abs, payload_obj):
    """Serialize strictly in memory, write+fsync to sibling temp file, then atomically hard-link to out_abs.
    Guarantees: (1) serialization errors create zero files; (2) mid-write OSError unlinks temp file and leaves
    out_abs absent/untouched; (3) existing out_abs raises FileExistsError without overwriting."""
    text = json.dumps(payload_obj, indent=2, allow_nan=False)
    out_real = os.path.abspath(out_abs)
    parent_dir = os.path.dirname(out_real)
    tmp_path = os.path.join(parent_dir, f".{os.path.basename(out_real)}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with open(tmp_path, "x", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.link(tmp_path, out_real)
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass


def run_g1_parity_gate():
    """
    Gate G1:
      1. Synthetic 1e10 dynamic-range exact CUT relative error < 1e-12.
      2. Real S1 map exact-CUT relative error < 1e-12.
      3. Direct parity of ACTUAL running `eval_p5_scene_worker` (`ofdm_p5_full` pre-fb SER, `ofdm_p5_pre_fb`
         score AND peak_idx) against an independent inline verbatim parent `k_l2_r10_k01_pfa.py:268-288`
         reference computing `gg` independently from `base.HQ_MOV, base.NU_Q_OFDM` and calling
         `base.run_ofdm_joint(R_cfo_bp, Xf_bp, ...)` directly (< 1e-12 & exact peak_idx).
      4. Direct parity of ACTUAL running `eval_p5_scene_worker` (`ridge_afdm_st`, `ofdm_blkpil_st`,
         `ofdm_genie_child_1pass`) against `k_l2_r11_k02_conf.eval_scene_worker` on `diag_seed = 2026169900`
         checking score (< 1e-12), SER (< 1e-12), AND exact `peak_idx` match!
    """
    rng = np.random.default_rng(31415928)
    failure_reasons = []
    syn_map = rng.exponential(1.0, size=(141, 29))
    syn_map[70, 14] = 1e10
    _, _, syn_grid = k02.score_cut_full_map(syn_map)
    syn_rel_err = 0.0
    for ni in range(141):
        for ti in range(29):
            ref = k02.score_cut(syn_map, (ni, ti))
            re = abs(float(syn_grid[ni, ti]) - ref) / max(abs(ref), 1e-15)
            if not np.isfinite(re):
                syn_rel_err = float("inf")
            elif np.isfinite(syn_rel_err) and re > syn_rel_err:
                syn_rel_err = re
    if not _finite_lt(syn_rel_err, 1e-12):
        failure_reasons.append(f"G1 synthetic 1e10 rel err failed: {syn_rel_err}")

    diag_seed = 2026169900
    p5_res = eval_p5_scene_worker((diag_seed, -11.0, "pos", True, True))
    real_s1_err = float(p5_res["exact_max_rel_err"])
    if not _finite_lt(real_s1_err, 1e-12):
        failure_reasons.append(f"G1 real S1 exact CUT rel err failed: {real_s1_err}")

    # Independent k02_conf worker parity (score, SER, AND peak_idx!)
    k02_ref = k02.eval_scene_worker((diag_seed, True, -11.0, ["ridge_afdm_st", "ofdm_blkpil_st", "ofdm_genie_st"], "pos", 0.0, "nominal", False, 0.0))
    parity_diffs = {}
    all_k02_peaks_match = True
    for arm_new, arm_old in (
        ("ridge_afdm_st", "ridge_afdm_st"),
        ("ofdm_blkpil_st", "ofdm_blkpil_st"),
        ("ofdm_genie_child_1pass", "ofdm_genie_st"),
    ):
        s_new = p5_res["arms"][arm_new]["score"]
        s_old = k02_ref["arms"][arm_old]["score"]
        ser_diff = abs(p5_res["arms"][arm_new]["ser"] - k02_ref["arms"][arm_old]["ser"])
        sc_rel = abs(s_new - s_old) / max(abs(s_old), 1e-15)
        pk_eq = bool(p5_res["arms"][arm_new]["peak_idx"] == k02_ref["arms"][arm_old]["peak_idx"])
        all_k02_peaks_match = all_k02_peaks_match and pk_eq
        parity_diffs[arm_new] = {
            "score_rel_diff": float(sc_rel),
            "ser_abs_diff": float(ser_diff),
            "peak_idx_exact_match": pk_eq,
        }
    max_k02_parity = 0.0
    for v in parity_diffs.values():
        for fv in (v["score_rel_diff"], v["ser_abs_diff"]):
            if not np.isfinite(fv):
                max_k02_parity = float("inf")
            elif np.isfinite(max_k02_parity) and fv > max_k02_parity:
                max_k02_parity = fv

    # Independent inline verbatim parent `k_l2_r10_k01_pfa.py:268-288` reference on exact same diag_seed scene
    # (computes gg independently WITHOUT calling fit_genie_g_parent_verbatim, passes Xf_bp verbatim into base.run_ofdm_joint,
    #  and verifies against ACTUAL `p5_res` outputs!)
    rng_p = np.random.default_rng(diag_seed)
    xq = rng_p.uniform(base.X0, base.X1, base.N_CLUT)
    yq = rng_p.uniform(-base.WY / 2.0, base.WY / 2.0, base.N_CLUT)
    tc, ncv, _ = base.bistatic_3d(xq, yq, np.zeros(base.N_CLUT), base.V_T_MOV)
    ac = (rng_p.standard_normal(base.N_CLUT) + 1j * rng_p.standard_normal(base.N_CLUT)) / np.sqrt(2.0 * base.N_CLUT) * (10.0 ** (28.0 / 20.0))
    alos = np.exp(1j * rng_p.uniform(0, 2 * np.pi)) * (10.0 ** (18.0 / 20.0))
    paths = [(alos, 0.0, base.NU_LOS_MOV)] + [(a, float(t), float(v)) for a, t, v in zip(ac, tc, ncv)]
    paths.append((np.exp(1j * rng_p.uniform(0, 2 * np.pi)) * (10.0 ** (-11.0 / 20.0)), base.TAU_TARG, base.NU_TARG_MOV))
    noise_l = [(rng_p.standard_normal(base.N) + 1j * rng_p.standard_normal(base.N)) / np.sqrt(2.0) for _ in range(base.M_SYM)]
    master_qam = rng_p.choice(base.CONST16, size=(base.M_SYM, len(base.ACT_OFDM)))
    pil_blk_phases = [np.exp(1j * rng_p.uniform(0, 2 * np.pi, len(base.ACT_OFDM))) for _ in range(base.M_SYM)]
    p_of = np.sqrt(base.N / float(len(base.ACT_OFDM)))
    syms_bp, Xf_bp = [], []
    for m in range(base.M_SYM):
        xf = np.zeros(base.N, dtype=np.complex128)
        xf[base.ACT_OFDM] = (pil_blk_phases[m] if m == 0 else master_qam[m, :]) * p_of
        syms_bp.append(base.make_cpp_centered(base.F_MAT.conj().T @ xf, 0.0))
        Xf_bp.append(xf)
    R_raw_bp = base.apply_real_rrc_frame(syms_bp, paths)
    R_cfo_bp = [
        (R_raw_bp[m] + noise_l[m]) * np.exp(-2j * np.pi * base.B_MOV * (m * base.STRIDE + base.N_IDX) / float(base.N))
        for m in range(base.M_SYM)
    ]
    Q_p = len(base.HQ_MOV)
    R_clut_ref = base.apply_real_rrc_frame(syms_bp, paths[: base.N_CLUT + 1])
    R_cc_ref = [
        R_clut_ref[m] * np.exp(-2j * np.pi * base.B_MOV * (m * base.STRIDE + base.N_IDX) / float(base.N))
        for m in range(base.M_SYM)
    ]
    Ga_ref = np.zeros((Q_p, Q_p), dtype=np.complex128)
    ba_ref = np.zeros(Q_p, dtype=np.complex128)
    for m in range(base.M_SYM):
        ph = np.exp(2j * np.pi * base.NU_Q_OFDM * (m * base.STRIDE / float(base.N)))
        Pm = np.column_stack([(base.HQ_MOV[q] @ Xf_bp[m]) * ph[q] for q in range(Q_p)])
        Ga_ref += Pm.conj().T @ Pm
        ba_ref += Pm.conj().T @ R_cc_ref[m]
    gg_ref = la.solve(Ga_ref + 1e-3 * np.eye(Q_p), ba_ref, assume_a="pos")
    Xh_ref, S_ref, _ = base.run_ofdm_joint(R_cfo_bp, Xf_bp, True, base.HQ_MOV, base.NU_Q_OFDM, base.ACT_OFDM, {0}, n_em=3, genie_g=gg_ref)
    ser_ref = _strict_ser([Xh_ref[m] for m in range(1, base.M_SYM)], [master_qam[m, :] for m in range(1, base.M_SYM)], failure_reasons, "g1_parent_ref")
    _, R_ref_1, _, _ = k02.qr_project_exact_rc(np.concatenate(R_cfo_bp), S_ref, 0.0, base.MU_MOV, base.DNU_LOS_MOV, is_mov=True)
    sc_ref_1, pk_ref_1, _ = k02.score_cut_full_map(base.compute_rd_map(R_ref_1, S_ref, 0.0, base.MU_MOV))

    parent_ser_diff = abs(p5_res["arms"]["ofdm_p5_full"]["ser_pre_fb"] - ser_ref)
    parent_sc_rel_diff = abs(p5_res["arms"]["ofdm_p5_pre_fb"]["score"] - sc_ref_1) / max(abs(sc_ref_1), 1e-15)
    parent_pk_match = bool(p5_res["arms"]["ofdm_p5_pre_fb"]["peak_idx"] == [int(pk_ref_1[0]), int(pk_ref_1[1])])
    p5_nf_empty = (len(p5_res.get("nonfinite_flags", [])) == 0)
    if not p5_nf_empty:
        failure_reasons.append(f"G1 worker reported non-finite flags: {p5_res['nonfinite_flags']}")

    if not _finite_lt(max_k02_parity, 1e-12) or not all_k02_peaks_match:
        failure_reasons.append(f"G1 k02_conf parity failed: max_diff={max_k02_parity}, peaks={all_k02_peaks_match}")
    if (not _finite_lt(parent_ser_diff, 1e-12)) or (not _finite_lt(parent_sc_rel_diff, 1e-12)) or (not parent_pk_match):
        failure_reasons.append(
            f"G1 parent reference parity failed: ser={parent_ser_diff}, sc={parent_sc_rel_diff}, pk={parent_pk_match}"
        )

    g1_ok = bool(
        _finite_lt(syn_rel_err, 1e-12)
        and _finite_lt(real_s1_err, 1e-12)
        and _finite_lt(max_k02_parity, 1e-12)
        and all_k02_peaks_match
        and _finite_lt(parent_ser_diff, 1e-12)
        and _finite_lt(parent_sc_rel_diff, 1e-12)
        and parent_pk_match
        and p5_nf_empty
    )
    g1_obj = {
        "pass": g1_ok,
        "failure_reasons": failure_reasons,
        "syn1e10_max_rel_err": syn_rel_err,
        "real_s1_g1_max_rel_err": real_s1_err,
        "parent_ref_vs_worker_ser_pre_diff": parent_ser_diff,
        "parent_ref_vs_worker_prefb_score_rel_diff": parent_sc_rel_diff,
        "parent_ref_vs_worker_prefb_peak_exact_match": parent_pk_match,
        "k02_conf_parity_diffs": parity_diffs,
        "k02_conf_max_parity_diff": max_k02_parity,
        "k02_conf_all_peaks_exact_match": all_k02_peaks_match,
        "diag_scene_p5_ser_pre": p5_res["arms"]["ofdm_p5_full"]["ser_pre_fb"],
        "diag_scene_p5_ser_post": p5_res["arms"]["ofdm_p5_full"]["ser"],
        "diag_scene_p5_score_db": p5_res["arms"]["ofdm_p5_full"]["score_db"],
    }
    nf_g1 = []
    g1_clean = _sanitize_nonfinite(g1_obj, nf_g1, "g1")
    if nf_g1:
        g1_clean["failure_reasons"] = list(g1_clean["failure_reasons"]) + nf_g1
        g1_clean["pass"] = False
    return g1_clean


def clopper_pearson_ci(k, n, alpha=0.05):
    if n <= 0:
        return 0.0, 0.0, 1.0
    p = k / float(n)
    lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return p, lo, hi


def tango_paired_score_ci(n10, n01, n, alpha_two_sided=0.05):
    """Tango (1998, Stat. Med. 17:891-908) paired binary score CI (non-degenerate even at 0 discordance)."""
    z = float(norm_dist.ppf(1.0 - alpha_two_sided / 2.0))
    def score_z(delta):
        a_q = 2.0 * float(n)
        b_q = -float(n10 + n01) + float(2 * n - n10 + n01) * delta
        c_q = -float(n01) * delta * (1.0 - delta)
        disc = max(0.0, b_q * b_q - 4.0 * a_q * c_q)
        q21 = (-b_q + np.sqrt(disc)) / (2.0 * a_q)
        var = max(1e-12, float(n) * (2.0 * q21 + delta * (1.0 - delta)))
        return (float(n10 - n01) - float(n) * delta) / np.sqrt(var)
    pt = float(n10 - n01) / float(n)
    lo_a, lo_b = -1.0 + 1e-9, pt
    if score_z(lo_a) <= z:
        lo = -1.0
    else:
        for _ in range(50):
            mid = 0.5 * (lo_a + lo_b)
            if score_z(mid) > z:
                lo_a = mid
            else:
                lo_b = mid
        lo = 0.5 * (lo_a + lo_b)
    hi_a, hi_b = pt, 1.0 - 1e-9
    if score_z(hi_b) >= -z:
        hi = 1.0
    else:
        for _ in range(50):
            mid = 0.5 * (hi_a + hi_b)
            if score_z(mid) < -z:
                hi_b = mid
            else:
                hi_a = mid
        hi = 0.5 * (hi_a + hi_b)
    return float(lo), float(hi)


def _boot_pd_draws(arr_d, idx_c, idx_p, b_bb):
    c_boot = arr_d["cal"][idx_c]
    thrs = np.partition(c_boot, b_bb - 1, axis=1)[:, b_bb - 1 : b_bb]
    exceed = arr_d["pos"][idx_p] > thrs
    hits = np.zeros_like(exceed, dtype=np.float64)
    bi, fi = np.nonzero(exceed)
    if len(bi) > 0:
        oi = idx_p[bi, fi]
        pk = arr_d["peaks"][oi]
        tc = arr_d["true_cells"][oi]
        ok = (np.abs(pk[:, 0] - tc[:, 0]) <= 2) & (np.abs(pk[:, 1] - tc[:, 1]) <= 1)
        hits[bi, fi] = ok.astype(np.float64)
    return np.mean(hits, axis=1)


def single_arm_pd_envelope(raw_a, pfa_target=0.01, n_boot=2000, seed=2026160150):
    """Conservative envelope of dual-bootstrap (cal + pos variance) and exact Clopper-Pearson 95% CI."""
    if not (raw_a.get("cal_ok", True) and raw_a.get("pos_ok", True) and np.all(np.isfinite(raw_a["det_loc"]))):
        return {
            "point": float("nan"),
            "ci95_cp": [float("nan"), float("nan")],
            "ci95_dual_boot": [float("nan"), float("nan")],
            "ci95_envelope": [float("nan"), float("nan")],
            "half_width": float("nan"),
        }
    n_cal = len(raw_a["cal"])
    n_pos = len(raw_a["pos"])
    _, b_bb = k02.exact_order_stat_params(n_cal, pfa_target)
    k_loc = int(np.sum(raw_a["det_loc"]))
    pt, cp_lo, cp_hi = clopper_pearson_ci(k_loc, n_pos, 0.05)
    rng = np.random.default_rng(seed)
    idx_c = rng.integers(0, n_cal, size=(n_boot, n_cal))
    idx_p = rng.integers(0, n_pos, size=(n_boot, n_pos))
    draws = _boot_pd_draws(raw_a, idx_c, idx_p, b_bb)
    db_lo = float(np.quantile(draws, 0.025))
    db_hi = float(np.quantile(draws, 0.975))
    env_lo = min(cp_lo, db_lo)
    env_hi = max(cp_hi, db_hi)
    return {
        "point": pt,
        "ci95_cp": [cp_lo, cp_hi],
        "ci95_dual_boot": [db_lo, db_hi],
        "ci95_envelope": [env_lo, env_hi],
        "half_width": float(0.5 * (env_hi - env_lo)),
    }


def _scan_raw_nonfinite(cal_res, val_res, pos_res, arm_list, max_entries=50):
    """Inspect EVERY scene and arm BEFORE thresholding or summary aggregation to block NaN/Inf collapse."""
    errors = []
    total_bad = 0

    def _add(msg):
        nonlocal total_bad
        total_bad += 1
        if len(errors) < max_entries:
            errors.append(msg)

    for split_name, res_list in (("cal", cal_res), ("val", val_res), ("pos", pos_res)):
        for idx, r in enumerate(res_list):
            sd = r.get("scene_seed", "unknown")
            for fl in r.get("nonfinite_flags", []):
                _add(f"{split_name}[{idx}] (seed={sd}) worker_flag={fl}")
            er = r.get("exact_max_rel_err", 0.0)
            if not np.isfinite(er):
                _add(f"{split_name}[{idx}] (seed={sd}) exact_max_rel_err={er}")
            arms_d = r.get("arms", {})
            for arm in arm_list:
                a_rec = arms_d[arm]
                sc = a_rec.get("score")
                if (sc is None) or (not np.isfinite(sc)) or (float(sc) <= 0.0):
                    _add(f"{split_name}[{idx}] (seed={sd}) arm={arm} score={sc}")
                ser_v = a_rec.get("ser")
                if (ser_v is None) or (not np.isfinite(ser_v)) or (float(ser_v) < -1e-12) or (float(ser_v) > 1.0 + 1e-12):
                    _add(f"{split_name}[{idx}] (seed={sd}) arm={arm} ser={ser_v}")
                if "ser_pre_fb" in a_rec:
                    sp_v = a_rec["ser_pre_fb"]
                    if (sp_v is None) or (not np.isfinite(sp_v)) or (float(sp_v) < -1e-12) or (float(sp_v) > 1.0 + 1e-12):
                        _add(f"{split_name}[{idx}] (seed={sd}) arm={arm} ser_pre_fb={sp_v}")
            if split_name == "pos":
                for k_iso, v_iso in r.get("p3_subfactors", {}).items():
                    if (v_iso is None) or (not np.isfinite(v_iso)) or (float(v_iso) < -1e-12) or (float(v_iso) > 1.0 + 1e-12):
                        _add(f"pos[{idx}] (seed={sd}) p3_subfactors.{k_iso}={v_iso}")
    if total_bad > max_entries:
        errors.append(f"... ({total_bad - max_entries} additional non-finite/out-of-range raw entries omitted)")
    return (total_bad == 0), errors


def evaluate_arms(cal_res, val_res, pos_res, arm_list, pfa_target=0.01, fwer_arms=8):
    all_raw_ok, all_raw_errors = _scan_raw_nonfinite(cal_res, val_res, pos_res, arm_list)
    summary = {}
    raw_arrays = {}
    true_cells = np.array([r["true_cell"] for r in pos_res], dtype=int)
    for arm in arm_list:
        cal_s = np.array([r["arms"][arm]["score"] for r in cal_res], dtype=np.float64)
        val_s = np.array([r["arms"][arm]["score"] for r in val_res], dtype=np.float64)
        pos_s = np.array([r["arms"][arm]["score"] for r in pos_res], dtype=np.float64)
        pos_peaks = np.array([r["arms"][arm]["peak_idx"] for r in pos_res], dtype=int)
        pos_ser = np.array([r["arms"][arm]["ser"] for r in pos_res], dtype=np.float64)
        pos_ser_pre = np.array([r["arms"][arm]["ser_pre_fb"] for r in pos_res], dtype=np.float64)

        arm_errors = []
        ser_all_splits_ok = True
        worker_flags_ok = True
        for split_name, arr, res_list in (("cal", cal_s, cal_res), ("val", val_s, val_res), ("pos", pos_s, pos_res)):
            bad_idx = np.where((~np.isfinite(arr)) | (arr <= 0.0))[0]
            for bi in bad_idx[:10]:
                sd = res_list[int(bi)].get("scene_seed", "unknown")
                arm_errors.append(f"{split_name}[{int(bi)}] (seed={sd}) arm={arm} score={arr[int(bi)]}")
            for si, r in enumerate(res_list):
                sd = r.get("scene_seed", "unknown")
                a_rec = r["arms"][arm]
                for fld in ("ser", "ser_pre_fb"):
                    if fld in a_rec:
                        fv = a_rec[fld]
                        if (fv is None) or (not np.isfinite(fv)) or (float(fv) < -1e-12) or (float(fv) > 1.0 + 1e-12):
                            ser_all_splits_ok = False
                            if len(arm_errors) < 20:
                                arm_errors.append(f"{split_name}[{si}] (seed={sd}) arm={arm} {fld}={fv}")
                for fl in r.get("nonfinite_flags", []):
                    if (f":{arm}." in fl) or (fl.endswith(f":{arm}")) or (f":{arm}:" in fl) or (arm == "ofdm_p5_full" and fl.startswith("nonfinite_symbol:p3.")):
                        worker_flags_ok = False
                        if len(arm_errors) < 20:
                            arm_errors.append(f"{split_name}[{si}] (seed={sd}) worker_flag={fl}")

        cal_ok = bool(np.all(np.isfinite(cal_s)) and np.all(cal_s > 0.0))
        val_ok = bool(np.all(np.isfinite(val_s)) and np.all(val_s > 0.0))
        pos_ok = bool(np.all(np.isfinite(pos_s)) and np.all(pos_s > 0.0))
        arm_inputs_finite = bool(cal_ok and val_ok and pos_ok and ser_all_splits_ok and worker_flags_ok)

        a_bb, b_bb = k02.exact_order_stat_params(len(cal_s), pfa_target)
        alpha_each = 0.05 / float(fwer_arms)
        k_lo_bb = int(betabinom_dist.ppf(alpha_each / 2.0, len(val_s), a_bb, b_bb))
        k_hi_bb = int(betabinom_dist.ppf(1.0 - alpha_each / 2.0, len(val_s), a_bb, b_bb))

        if cal_ok:
            thr = float(np.partition(cal_s, b_bb - 1)[b_bb - 1])
            thr_db = float(10.0 * np.log10(thr))
        else:
            thr = float("nan")
            thr_db = float("nan")

        if cal_ok and val_ok:
            k_val = int(np.sum(val_s > thr))
            p_val, lo_v, hi_v = clopper_pearson_ci(k_val, len(val_s))
            # Per pre-registration §3: ANY raw non-finite anomaly across splits/arms invalidates C1 too
            c1_pass = bool(all_raw_ok and arm_inputs_finite and (k_lo_bb <= k_val <= k_hi_bb))
        else:
            k_val = None
            p_val, lo_v, hi_v = float("nan"), float("nan"), float("nan")
            c1_pass = False

        # Strict alarm-first before localization check (exact k02_conf 5x3 box: |dni|<=2 and |dti|<=1)
        if cal_ok and pos_ok:
            exceed = pos_s > thr
            det_loc = np.zeros(len(pos_s), dtype=np.float64)
            det_mis = np.zeros(len(pos_s), dtype=np.float64)
            for i in range(len(pos_s)):
                if exceed[i]:
                    ni_h, ti_h = pos_peaks[i]
                    ni_t, ti_t = true_cells[i]
                    if abs(ni_h - ni_t) <= 2 and abs(ti_h - ti_t) <= 1:
                        det_loc[i] = 1.0
                    else:
                        det_mis[i] = 1.0
            det_miss = (~exceed).astype(np.float64)
            k_loc = int(np.sum(det_loc))
            pd_loc, pd_lo, pd_hi = clopper_pearson_ci(k_loc, len(det_loc))
            pd_mis = float(np.mean(det_mis))
            p_miss = float(np.mean(det_miss))
            pos_score_db_mean = float(np.mean(10.0 * np.log10(pos_s)))
        else:
            det_loc = np.full(len(pos_s), float("nan"), dtype=np.float64)
            k_loc = None
            pd_loc, pd_lo, pd_hi = float("nan"), float("nan"), float("nan")
            pd_mis, p_miss, pos_score_db_mean = float("nan"), float("nan"), float("nan")

        summary[arm] = {
            "raw_inputs_finite": arm_inputs_finite,
            "nonfinite_errors": arm_errors,
            "n_cal": int(len(cal_s)),
            "n_val": int(len(val_s)),
            "val_k_fa": k_val,
            "val_pfa_map": p_val,
            "val_ci95_cp": [lo_v, hi_v],
            "val_bb_fwer_bounds_k": [k_lo_bb, k_hi_bb],
            "val_bb_fwer_bounds_p": [k_lo_bb / float(len(val_s)), k_hi_bb / float(len(val_s))],
            "c1_pass": c1_pass,
            "n_pos": int(len(pos_s)),
            "thr_linear": thr,
            "thr_db": thr_db,
            "pos_k_loc": k_loc,
            "pos_pd_loc": pd_loc,
            "pos_pd_loc_ci95_cp": [pd_lo, pd_hi],
            "pos_pd_mis": pd_mis,
            "pos_p_miss": p_miss,
            "pos_score_db_mean": pos_score_db_mean,
            "pos_ser_pre_fb_mean": float(np.mean(pos_ser_pre)),
            "pos_ser_pre_fb_std": float(np.std(pos_ser_pre, ddof=1)) if len(pos_ser_pre) > 1 else 0.0,
            "pos_ser_post_fb_mean": float(np.mean(pos_ser)),
            "pos_ser_post_fb_std": float(np.std(pos_ser, ddof=1)) if len(pos_ser) > 1 else 0.0,
        }
        raw_arrays[arm] = {
            "cal": cal_s,
            "pos": pos_s,
            "peaks": pos_peaks,
            "true_cells": true_cells,
            "det_loc": det_loc,
            "ser_pre": pos_ser_pre,
            "ser_post": pos_ser,
            "cal_ok": cal_ok,
            "pos_ok": pos_ok,
        }
    return summary, raw_arrays


def paired_delta_pd_envelope(raw_a, raw_b, pfa_target=0.01, n_boot=2000, seed=2026160101):
    """Conservative envelope of dual-bootstrap (cal + pos variance) and Tango (1998) paired score CI."""
    if not (
        raw_a.get("cal_ok", True) and raw_a.get("pos_ok", True) and np.all(np.isfinite(raw_a["det_loc"]))
        and raw_b.get("cal_ok", True) and raw_b.get("pos_ok", True) and np.all(np.isfinite(raw_b["det_loc"]))
    ):
        return {
            "point": float("nan"),
            "discordant_n10_n01": [None, None],
            "ci95_dual_boot": [float("nan"), float("nan")],
            "ci95_tango": [float("nan"), float("nan")],
            "ci95_envelope": [float("nan"), float("nan")],
            "half_width": float("nan"),
        }
    n_cal = len(raw_a["cal"])
    n_pos = len(raw_a["pos"])
    _, b_bb = k02.exact_order_stat_params(n_cal, pfa_target)

    a_det = raw_a["det_loc"]
    b_det = raw_b["det_loc"]
    point = float(np.mean(a_det) - np.mean(b_det))
    k_10 = int(np.sum((a_det > 0.5) & (b_det < 0.5)))
    k_01 = int(np.sum((a_det < 0.5) & (b_det > 0.5)))
    tg_lo, tg_hi = tango_paired_score_ci(k_10, k_01, n_pos, alpha_two_sided=0.05)

    rng = np.random.default_rng(seed)
    idx_c = rng.integers(0, n_cal, size=(n_boot, n_cal))
    idx_p = rng.integers(0, n_pos, size=(n_boot, n_pos))

    diff_b = _boot_pd_draws(raw_a, idx_c, idx_p, b_bb) - _boot_pd_draws(raw_b, idx_c, idx_p, b_bb)
    db_lo = float(np.quantile(diff_b, 0.025))
    db_hi = float(np.quantile(diff_b, 0.975))
    env_lo = min(db_lo, tg_lo)
    env_hi = max(db_hi, tg_hi)
    return {
        "point": point,
        "discordant_n10_n01": [k_10, k_01],
        "ci95_dual_boot": [db_lo, db_hi],
        "ci95_tango": [tg_lo, tg_hi],
        "ci95_envelope": [env_lo, env_hi],
        "half_width": float(0.5 * (env_hi - env_lo)),
    }


def paired_continuous_ci(vec_a, vec_b=None, n_boot=2000, seed=2026160201):
    """Paired bootstrap + normal-t guard 95% CI for continuous metrics (SER or score-dB)."""
    x = np.asarray(vec_a, dtype=np.float64) if vec_b is None else (np.asarray(vec_a, dtype=np.float64) - np.asarray(vec_b, dtype=np.float64))
    n = len(x)
    pt = float(np.mean(x))
    sd = float(np.std(x, ddof=1)) if n > 1 else 0.0
    se = sd / np.sqrt(float(n)) if n > 1 else 0.0
    z = float(norm_dist.ppf(0.975))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = np.mean(x[idx], axis=1)
    lo = min(float(np.quantile(means, 0.025)), pt - z * se)
    hi = max(float(np.quantile(means, 0.975)), pt + z * se)
    return {"point": pt, "std": sd, "ci95": [lo, hi], "half_width": float(0.5 * (hi - lo))}


def hoeffding_kl_bounded_mean_ci(vec_01, alpha=0.05):
    """
    Exact, non-asymptotic, distribution-free (1-alpha) CI for E[X] of i.i.d. bounded X_i in [0, 1]
    (Hoeffding 1963, JASA 58:13-30, Theorem 1: P(Xbar <= x) <= exp(-n * KL(x || mu))).
    NEVER degenerates to zero width when sample variance is 0 and is strictly immune to rare
    catastrophic [0, 1] outliers! Also reports exact binomial order-statistic 95% CI on median.
    """
    x = np.asarray(vec_01, dtype=np.float64)
    n = len(x)
    if (n <= 0) or (not np.all(np.isfinite(x))) or np.any((x < -1e-12) | (x > 1.0 + 1e-12)):
        return {
            "point": float("nan"),
            "std": float("nan"),
            "ci95_hoeffding_kl": [float("nan"), float("nan")],
            "half_width": float("nan"),
            "median_descriptive": float("nan"),
            "median_ci95_exact_descriptive": [float("nan"), float("nan")],
            "median_order_stat_1indexed": [None, None],
            "n": int(n),
        }
    x = np.clip(x, 0.0, 1.0)
    mean_x = float(np.mean(x))
    rhs = float(np.log(2.0 / alpha) / float(n))

    def kl(p, q):
        t1 = 0.0 if p <= 0.0 else p * float(np.log(p / q))
        t2 = 0.0 if p >= 1.0 else (1.0 - p) * float(np.log((1.0 - p) / (1.0 - q)))
        return t1 + t2

    if mean_x <= 0.0:
        lo = 0.0
    else:
        a, b = 1e-12, mean_x
        for _ in range(60):
            mid = 0.5 * (a + b)
            if kl(mean_x, mid) > rhs:
                a = mid
            else:
                b = mid
        lo = 0.5 * (a + b)
    if mean_x >= 1.0:
        hi = 1.0
    else:
        a, b = mean_x, 1.0 - 1e-12
        for _ in range(60):
            mid = 0.5 * (a + b)
            if kl(mean_x, mid) > rhs:
                b = mid
            else:
                a = mid
        hi = 0.5 * (a + b)

    xs = np.sort(x)
    # Descriptive-only exact binomial order-statistic 95% CI on median (NOT part of boolean recovery gate):
    k_lo_0 = max(0, int(binom_dist.ppf(alpha / 2.0, n, 0.5)) - 1)
    k_hi_0 = min(n - 1, int(binom_dist.ppf(1.0 - alpha / 2.0, n, 0.5)))
    return {
        "point": mean_x,
        "std": float(np.std(x, ddof=1)) if n > 1 else 0.0,
        "ci95_hoeffding_kl": [float(lo), float(hi)],
        "half_width": float(0.5 * (hi - lo)),
        "median_descriptive": float(np.median(xs)),
        "median_ci95_exact_descriptive": [float(xs[k_lo_0]), float(xs[k_hi_0])],
        "median_order_stat_1indexed": [int(k_lo_0 + 1), int(k_hi_0 + 1)],
        "n": int(n),
    }


def run_batch(pool, tasks):
    if pool is None:
        return [eval_p5_scene_worker(t) for t in tasks]
    return pool.map(eval_p5_scene_worker, tasks)


def classify_diagnostic_outcome(
    diagnostic_valid,
    ser_p5_pre_kl,
    p5_pd_env,
    c_afdm_vs_p5_full,
    c_afdm_vs_blkpil,
):
    """
    Pre-registered 5-state CI-bound decision function (ZERO point-estimate triggers; gated on
    both validity and Red Line 5 half-width <= 25% of threshold distance):
      1. If not diagnostic_valid (G1, real-map exact-CUT, non-finite check, or C1 fails) -> INVALID_DIAGNOSTIC_DO_NOT_USE
      2. Precision gates (Red Line 5):
         - ser_pre exact non-asymptotic Hoeffding-KL [0,1] mean bound (< 0.06 vs straight-ridge ~0.19):
           hw <= 0.0150 (25% of 0.06); median is descriptive-only (NOT a gate).
         - catch-up margin (Delta_P5 <= 0.15 & Pd >= 0.85): hw <= 0.0375 (25% of 0.15)
         - exclusive / blind margin (Delta >= 0.50 & Pd < 0.50): hw <= 0.125 (25% of 0.50)
      3. Outcomes (CI-bound only):
         - INVALID_DIAGNOSTIC_DO_NOT_USE
         - OFDM_CATCHES_UP_NARROW_CLAIM
         - OFDM_LOW_SER_STILL_FAILS_RETRACT_STAGE1_EXPLANATION
         - INCONCLUSIVE_PRECISION_INSUFFICIENT
         - INTERMEDIATE_PARTIAL_GAP
         - PARENT_INIT_NOT_RECOVERED
    """
    prec = {
        "ser_pre_kl_hw_le_0p0150": bool(np.isfinite(ser_p5_pre_kl["half_width"]) and ser_p5_pre_kl["half_width"] <= 0.0150),
        "delta_p5_hw_le_0p0375_catchup": bool(np.isfinite(c_afdm_vs_p5_full["half_width"]) and c_afdm_vs_p5_full["half_width"] <= 0.0375),
        "p5_pd_hw_le_0p0375_catchup": bool(np.isfinite(p5_pd_env["half_width"]) and p5_pd_env["half_width"] <= 0.0375),
        "delta_p5_hw_le_0p125_excl": bool(np.isfinite(c_afdm_vs_p5_full["half_width"]) and c_afdm_vs_p5_full["half_width"] <= 0.125),
        "p5_pd_hw_le_0p125_excl": bool(np.isfinite(p5_pd_env["half_width"]) and p5_pd_env["half_width"] <= 0.125),
        "delta_blkpil_hw_le_0p125": bool(np.isfinite(c_afdm_vs_blkpil["half_width"]) and c_afdm_vs_blkpil["half_width"] <= 0.125),
    }
    parent_init_recovered = bool(
        prec["ser_pre_kl_hw_le_0p0150"]
        and np.isfinite(ser_p5_pre_kl["ci95_hoeffding_kl"][1])
        and (ser_p5_pre_kl["ci95_hoeffding_kl"][1] < 0.06)
    )
    if not diagnostic_valid:
        return "INVALID_DIAGNOSTIC_DO_NOT_USE", parent_init_recovered, prec

    if not prec["ser_pre_kl_hw_le_0p0150"]:
        return "INCONCLUSIVE_PRECISION_INSUFFICIENT", parent_init_recovered, prec
    if not parent_init_recovered:
        return "PARENT_INIT_NOT_RECOVERED", parent_init_recovered, prec

    catchup_prec_ok = bool(prec["delta_p5_hw_le_0p0375_catchup"] and prec["p5_pd_hw_le_0p0375_catchup"] and prec["delta_blkpil_hw_le_0p125"])
    excl_prec_ok = bool(prec["delta_p5_hw_le_0p125_excl"] and prec["p5_pd_hw_le_0p125_excl"])

    p5_catches_up = bool(
        catchup_prec_ok
        and (c_afdm_vs_p5_full["ci95_envelope"][1] <= 0.15)
        and (p5_pd_env["ci95_envelope"][0] >= 0.85)
        and (c_afdm_vs_blkpil["ci95_envelope"][0] >= 0.50)
    )
    # Pure CI-bound trigger (NEVER point estimate): either Delta_P5 95% LB >= 0.50 OR ofdm_p5_full Pd 95% UB < 0.50
    p5_still_fails = bool(
        excl_prec_ok
        and ((c_afdm_vs_p5_full["ci95_envelope"][0] >= 0.50) or (p5_pd_env["ci95_envelope"][1] < 0.50))
    )
    if p5_catches_up:
        return "OFDM_CATCHES_UP_NARROW_CLAIM", parent_init_recovered, prec
    if p5_still_fails:
        return "OFDM_LOW_SER_STILL_FAILS_RETRACT_STAGE1_EXPLANATION", parent_init_recovered, prec
    if not catchup_prec_ok:
        return "INCONCLUSIVE_PRECISION_INSUFFICIENT", parent_init_recovered, prec
    return "INTERMEDIATE_PARTIAL_GAP", parent_init_recovered, prec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026162501)
    ap.add_argument("--mode", choices=["g1_only", "smoke", "full"], default="smoke")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--n-cal", type=int, default=1500)
    ap.add_argument("--n-val", type=int, default=2000)
    ap.add_argument("--n-pos", type=int, default=300)
    ap.add_argument("--snr-target", type=float, default=-11.0)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    t0 = time.time()
    out_abs = os.path.abspath(args.out)
    canonical_local = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_k_r12_k02_p5", "summary_k_r12_k02_p5.json"))
    canonical_deinlab = os.path.abspath("/data/guoyikun/tmp/funnel_k_r12/summary_k_r12_k02_p5.json")

    if not (1 <= args.workers <= 8):
        raise ValueError(f"Round-12 deinlab hard limit requires 1 <= workers <= 8, got {args.workers}")
    if os.path.basename(out_abs) in ("summary_k_r11_k02.json", "summary_k_r11_k02_conf.json"):
        raise ValueError(f"Refusing to touch prior frozen k02 artifact: {out_abs}")
    if args.mode == "full":
        if out_abs not in (canonical_local, canonical_deinlab):
            raise ValueError(f"Formal full mode locks output path to {canonical_local} or {canonical_deinlab}, got {out_abs}")
        if args.seed != 2026162501:
            raise ValueError(f"Formal full mode locks seed=2026162501, got {args.seed}")
        if args.snr_target != -11.0:
            raise ValueError(f"Formal full mode locks snr_target=-11.0, got {args.snr_target}")
        if (args.n_cal, args.n_val, args.n_pos) != (1500, 2000, 300):
            raise ValueError(f"Formal full mode locks sizes (1500, 2000, 300), got {(args.n_cal, args.n_val, args.n_pos)}")
    else:
        if os.path.basename(out_abs) == "summary_k_r12_k02_p5.json" or out_abs in (canonical_local, canonical_deinlab):
            raise ValueError(f"Diagnostic mode {args.mode} must not write to formal path {out_abs}")
    if os.path.exists(out_abs):
        raise FileExistsError(f"Refusing to overwrite existing output file: {out_abs}")
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)

    g1_report = run_g1_parity_gate()
    print(
        f"[Gate G1] pass={g1_report['pass']} | syn1e10={g1_report['syn1e10_max_rel_err']} | "
        f"realS1={g1_report['real_s1_g1_max_rel_err']} | parentRef_ser={g1_report['parent_ref_vs_worker_ser_pre_diff']} | "
        f"parentRef_sc={g1_report['parent_ref_vs_worker_prefb_score_rel_diff']} (pk={g1_report['parent_ref_vs_worker_prefb_peak_exact_match']}) | "
        f"k02_parity={g1_report['k02_conf_max_parity_diff']} (pks={g1_report['k02_conf_all_peaks_exact_match']})",
        flush=True,
    )
    if args.mode == "g1_only":
        _write_json_strict_atomic(
            out_abs,
            {
                "g1": g1_report,
                "verdicts": {
                    "G1_PARITY_AND_EXACT_CUT": g1_report["pass"],
                    "DIAGNOSTIC_VALID": False if not g1_report["pass"] else None,
                    "DIAGNOSTIC_OUTCOME": "INVALID_DIAGNOSTIC_DO_NOT_USE" if not g1_report["pass"] else "G1_ONLY_NO_RUN",
                    "invalid_reasons": g1_report["failure_reasons"],
                },
            },
        )
        return

    if not g1_report["pass"]:
        elapsed = time.time() - t0
        invalid_summary = {
            "meta": {
                "card": "I-20261125-k02 (Step-8 P_5 paired mechanism diagnostic; prior frozen verdicts preserved)",
                "parent": "I-20261125-k01",
                "seed": args.seed,
                "mode": args.mode,
                "workers": args.workers,
                "snr_target_db": args.snr_target,
                "pfa_map_target": 0.01,
                "elapsed_sec": round(elapsed, 2),
                "aborted_before_batch_due_to_g1_failure": True,
            },
            "gates": {"G1_parity_and_exact_cut": g1_report},
            "verdicts": {
                "G1_PARITY_AND_EXACT_CUT": False,
                "C1_VALIDITY": False,
                "DIAGNOSTIC_VALID": False,
                "DIAGNOSTIC_OUTCOME": "INVALID_DIAGNOSTIC_DO_NOT_USE",
                "invalid_reasons": g1_report["failure_reasons"],
            },
        }
        _write_json_strict_atomic(out_abs, invalid_summary)
        print(f"[ABORTED ON G1 FAILURE] Wrote INVALID_DIAGNOSTIC_DO_NOT_USE -> {out_abs}: {g1_report['failure_reasons']}", flush=True)
        return

    if args.mode == "smoke":
        n_cal, n_val, n_pos = 15, 15, 10
    else:
        n_cal, n_val, n_pos = 1500, 2000, 300

    hist_seeds = set()
    hist_sources = [2026112501, 2026122501, 2026132501, 2026142501, 2026152501, 999888777, 888777666]
    if args.mode == "smoke":
        hist_sources.append(2026162501)
    for hs in hist_sources:
        hist_seeds.update(int(x) for x in np.random.default_rng(hs).integers(1, 2**31 - 1, size=15000))
    hist_seeds.add(2026169900)

    effective_seed = (args.seed + 777777) if args.mode == "smoke" else args.seed
    rng_master = np.random.default_rng(effective_seed)
    n_needed = n_cal + n_val + n_pos
    seed_set, seed_list = set(), []
    while len(seed_list) < n_needed:
        c = int(rng_master.integers(1, 2**31 - 1))
        if c not in seed_set and c not in hist_seeds:
            seed_set.add(c)
            seed_list.append(c)
    cal_seeds = seed_list[:n_cal]
    val_seeds = seed_list[n_cal : n_cal + n_val]
    pos_seeds = seed_list[n_cal + n_val :]

    pool = Pool(processes=args.workers) if args.workers > 1 else None
    total_calls = {"cal": 0, "val": 0, "pos": 0}
    max_exact_rel_err = 0.0
    nonfinite_batch_err = False

    def accum(res_l):
        nonlocal max_exact_rel_err, nonfinite_batch_err
        for r in res_l:
            for k, v in r["score_calls"].items():
                total_calls[k] = total_calls.get(k, 0) + v
            er = float(r["exact_max_rel_err"])
            if not np.isfinite(er):
                nonfinite_batch_err = True
                max_exact_rel_err = float("inf")
            elif np.isfinite(max_exact_rel_err) and er > max_exact_rel_err:
                max_exact_rel_err = er

    try:
        print(f"[k02 P5] Running cal={n_cal}, val={n_val}, pos({args.snr_target:+.1f} dB)={n_pos} across {len(CAL_ARMS)} paired arms (workers={args.workers})...", flush=True)
        cal_res = run_batch(pool, [(s, None, "cal", i == 0, False) for i, s in enumerate(cal_seeds)])
        accum(cal_res); print(f"  [cal] done in {time.time() - t0:.1f}s", flush=True)
        val_res = run_batch(pool, [(s, None, "val", i == 0, False) for i, s in enumerate(val_seeds)])
        accum(val_res); print(f"  [val] done in {time.time() - t0:.1f}s", flush=True)
        pos_res = run_batch(pool, [(s, args.snr_target, "pos", i == 0, True) for i, s in enumerate(pos_seeds)])
        accum(pos_res); print(f"  [pos] done in {time.time() - t0:.1f}s", flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    real_map_exact_ok = bool((not nonfinite_batch_err) and _finite_lt(max_exact_rel_err, 1e-12))
    raw_inputs_finite_ok, raw_nf_errors = _scan_raw_nonfinite(cal_res, val_res, pos_res, CAL_ARMS)
    invalid_reasons = list(g1_report["failure_reasons"])
    if not real_map_exact_ok:
        invalid_reasons.append(f"Real-map exact CUT rel err failed (nonfinite={nonfinite_batch_err}): {max_exact_rel_err}")
    if not raw_inputs_finite_ok:
        invalid_reasons.extend(raw_nf_errors)

    arm_sum, raw = evaluate_arms(cal_res, val_res, pos_res, CAL_ARMS, pfa_target=0.01, fwer_arms=len(CAL_ARMS))

    # C1 Validity: 8-arm Beta-Binomial FWER (3.586% UB <= 5%) + symmetric anti-inflation cap <= 1.75% (k<=35/2000)
    # on BOTH primary P_5 comparison arms (ridge_afdm_st and ofdm_p5_full; deduplicated union UB 7.264%)
    c1_per_arm = {a: arm_sum[a]["c1_pass"] for a in CAL_ARMS}
    c1_cap_afdm = bool(raw_inputs_finite_ok and np.isfinite(arm_sum["ridge_afdm_st"]["val_pfa_map"]) and (arm_sum["ridge_afdm_st"]["val_pfa_map"] <= 0.0175))
    c1_cap_p5 = bool(raw_inputs_finite_ok and np.isfinite(arm_sum["ofdm_p5_full"]["val_pfa_map"]) and (arm_sum["ofdm_p5_full"]["val_pfa_map"] <= 0.0175))
    c1_valid = bool(raw_inputs_finite_ok and all(c1_per_arm.values()) and c1_cap_afdm and c1_cap_p5)
    if not c1_valid:
        invalid_reasons.append(f"C1_VALIDITY failed: per_arm={c1_per_arm}, cap_afdm={c1_cap_afdm}, cap_p5={c1_cap_p5}")
    diagnostic_valid = bool(g1_report["pass"] and real_map_exact_ok and raw_inputs_finite_ok and c1_valid)

    # Single-arm dual-bootstrap + CP envelope for ofdm_p5_full Pd_loc
    p5_pd_env = single_arm_pd_envelope(raw["ofdm_p5_full"], 0.01, 2000, args.seed + 150)

    # Primary & single-factor paired contrasts (Envelope of Dual-Bootstrap + Tango 1998)
    c_afdm_vs_p5_full = paired_delta_pd_envelope(raw["ridge_afdm_st"], raw["ofdm_p5_full"], 0.01, 2000, args.seed + 101)
    c_afdm_vs_p5_prefb = paired_delta_pd_envelope(raw["ridge_afdm_st"], raw["ofdm_p5_pre_fb"], 0.01, 2000, args.seed + 102)
    c_afdm_vs_blkpil = paired_delta_pd_envelope(raw["ridge_afdm_st"], raw["ofdm_blkpil_st"], 0.01, 2000, args.seed + 103)
    c_p5_full_vs_prefb = paired_delta_pd_envelope(raw["ofdm_p5_full"], raw["ofdm_p5_pre_fb"], 0.01, 2000, args.seed + 104)
    c_p3_pure_curv_pd = paired_delta_pd_envelope(raw["ofdm_p5_full"], raw["ofdm_p5_lin_pgrid_full"], 0.01, 2000, args.seed + 105)
    c_p3_grid_solver_pd = paired_delta_pd_envelope(raw["ofdm_p5_lin_pgrid_full"], raw["ofdm_genie_child_full"], 0.01, 2000, args.seed + 106)
    c_p5_full_vs_child_full = paired_delta_pd_envelope(raw["ofdm_p5_full"], raw["ofdm_genie_child_full"], 0.01, 2000, args.seed + 107)
    c_child_full_vs_1pass = paired_delta_pd_envelope(raw["ofdm_genie_child_full"], raw["ofdm_genie_child_1pass"], 0.01, 2000, args.seed + 108)
    c_p5_full_vs_known = paired_delta_pd_envelope(raw["ofdm_p5_full"], raw["known_ofdm_bp_st"], 0.01, 2000, args.seed + 109)

    # Continuous paired diagnostics (exact Hoeffding-KL [0,1] bound for primary SER recovery gate + bootstrap CIs)
    ser_p5_pre_kl = hoeffding_kl_bounded_mean_ci(raw["ofdm_p5_full"]["ser_pre"], alpha=0.05)
    ser_p5_post_kl = hoeffding_kl_bounded_mean_ci(raw["ofdm_p5_full"]["ser_post"], alpha=0.05)
    ser_p5_pre_ci = paired_continuous_ci(raw["ofdm_p5_full"]["ser_pre"], None, 2000, args.seed + 201)
    ser_p5_post_ci = paired_continuous_ci(raw["ofdm_p5_full"]["ser_post"], None, 2000, args.seed + 202)
    ser_p5_delta_fb_ci = paired_continuous_ci(raw["ofdm_p5_full"]["ser_post"], raw["ofdm_p5_full"]["ser_pre"], 2000, args.seed + 203)
    score_afdm_vs_p5_db = paired_continuous_ci(
        np.where(np.isfinite(raw["ridge_afdm_st"]["pos"]) & (raw["ridge_afdm_st"]["pos"] > 0.0), 10.0 * np.log10(np.where(raw["ridge_afdm_st"]["pos"] > 0.0, raw["ridge_afdm_st"]["pos"], 1.0)), float("nan")),
        np.where(np.isfinite(raw["ofdm_p5_full"]["pos"]) & (raw["ofdm_p5_full"]["pos"] > 0.0), 10.0 * np.log10(np.where(raw["ofdm_p5_full"]["pos"] > 0.0, raw["ofdm_p5_full"]["pos"], 1.0)), float("nan")),
        2000, args.seed + 204,
    )

    # P_3 sub-factor per-scene paired SER decomposition (pure curvature vs pure knot-span vs pure solver)
    p3_vecs = {
        k_iso: np.array([r["p3_subfactors"][k_iso] for r in pos_res], dtype=np.float64)
        for k_iso in (
            "ser_curv_pgrid_psolver",
            "ser_lin_pgrid_psolver",
            "ser_lin_cgrid_psolver",
            "ser_lin_cgrid_csolver",
            "ser_curv_pgrid_csolver",
        )
    }
    p3_subfactor_summary = {
        "levels": {
            k_iso: paired_continuous_ci(v, None, 2000, args.seed + 300 + idx)
            for idx, (k_iso, v) in enumerate(p3_vecs.items())
        },
        "paired_diffs": {
            "pure_curvature_lin_minus_curv_on_parent_grid": paired_continuous_ci(
                p3_vecs["ser_lin_pgrid_psolver"], p3_vecs["ser_curv_pgrid_psolver"], 2000, args.seed + 310
            ),
            "pure_knot_span_child_minus_parent_on_lin": paired_continuous_ci(
                p3_vecs["ser_lin_cgrid_psolver"], p3_vecs["ser_lin_pgrid_psolver"], 2000, args.seed + 311
            ),
            "pure_solver_child_minus_parent_on_lin_cgrid": paired_continuous_ci(
                p3_vecs["ser_lin_cgrid_csolver"], p3_vecs["ser_lin_cgrid_psolver"], 2000, args.seed + 312
            ),
            "pure_solver_child_minus_parent_on_curv_pgrid": paired_continuous_ci(
                p3_vecs["ser_curv_pgrid_csolver"], p3_vecs["ser_curv_pgrid_psolver"], 2000, args.seed + 313
            ),
        },
    }

    diag_outcome, parent_init_recovered, prec_gates = classify_diagnostic_outcome(
        diagnostic_valid, ser_p5_pre_kl, p5_pd_env, c_afdm_vs_p5_full, c_afdm_vs_blkpil
    )

    elapsed = time.time() - t0
    core_hours = (elapsed * args.workers) / 3600.0
    ru_s = resource.getrusage(resource.RUSAGE_SELF)
    ru_c = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_hours = (ru_s.ru_utime + ru_s.ru_stime + ru_c.ru_utime + ru_c.ru_stime) / 3600.0

    summary = {
        "meta": {
            "card": "I-20261125-k02 (Step-8 P_5 paired mechanism diagnostic; prior frozen verdicts preserved)",
            "parent": "I-20261125-k01",
            "seed": args.seed,
            "mode": args.mode,
            "workers": args.workers,
            "snr_target_db": args.snr_target,
            "pfa_map_target": 0.01,
            "elapsed_sec": round(elapsed, 2),
            "reserved_core_hours": round(core_hours, 4),
            "process_cpu_hours": round(cpu_hours, 4),
            "unified_score_calls": total_calls,
            "real_map_exact_cut_max_rel_err": max_exact_rel_err,
        },
        "gates": {
            "G1_parity_and_exact_cut": g1_report,
            "G2_no_truth_in_cal_val_and_strict_alarm_first": True,
        },
        "s1_m11db_p5_arms": arm_sum,
        "p3_frontend_subfactor_ser_decomposition": p3_subfactor_summary,
        "contrasts": {
            "P5_ofdm_p5_full_pd_envelope": p5_pd_env,
            "P5_ridge_afdm_vs_ofdm_p5_full": c_afdm_vs_p5_full,
            "P5_ridge_afdm_vs_ofdm_p5_pre_fb": c_afdm_vs_p5_prefb,
            "P5_ridge_afdm_vs_ofdm_blkpil_blind": c_afdm_vs_blkpil,
            "P4_feedback_effect_curved_genie": c_p5_full_vs_prefb,
            "P3_pure_curvature_pd_on_parent_grid_full_backend": c_p3_pure_curv_pd,
            "P3_grid_and_solver_pd_on_straight_full_backend": c_p3_grid_solver_pd,
            "P3_total_curved_vs_child_straight_full_backend": c_p5_full_vs_child_full,
            "P4_feedback_effect_straight_genie": c_child_full_vs_1pass,
            "P5_ofdm_p5_full_vs_known_ofdm_bp": c_p5_full_vs_known,
            "P5_ser_pre_fb_hoeffding_kl": ser_p5_pre_kl,
            "P5_ser_post_fb_hoeffding_kl": ser_p5_post_kl,
            "P5_ser_pre_fb_boot": ser_p5_pre_ci,
            "P5_ser_post_fb_boot": ser_p5_post_ci,
            "P5_ser_post_minus_pre_fb": ser_p5_delta_fb_ci,
            "P5_score_db_afdm_minus_p5_full": score_afdm_vs_p5_db,
        },
        "verdicts": {
            "G1_PARITY_AND_EXACT_CUT": g1_report["pass"],
            "REAL_MAP_EXACT_CUT_OK": real_map_exact_ok,
            "RAW_INPUTS_FINITE_OK": raw_inputs_finite_ok,
            "C1_per_arm": c1_per_arm,
            "C1_cap_afdm_le_1p75pct": c1_cap_afdm,
            "C1_cap_p5_le_1p75pct": c1_cap_p5,
            "C1_VALIDITY": c1_valid,
            "DIAGNOSTIC_VALID": diagnostic_valid,
            "invalid_reasons": invalid_reasons,
            "REDLINE5_PRECISION_GATES": prec_gates,
            "PARENT_INIT_RECOVERED_KL_LT_6PCT": parent_init_recovered,
            "DIAGNOSTIC_OUTCOME": diag_outcome,
        },
    }

    nf_summary = []
    summary = _sanitize_nonfinite(summary, nf_summary, "summary")
    if nf_summary:
        summary["verdicts"]["invalid_reasons"] = list(summary["verdicts"]["invalid_reasons"]) + nf_summary
        summary["verdicts"]["DIAGNOSTIC_VALID"] = False
        summary["verdicts"]["DIAGNOSTIC_OUTCOME"] = "INVALID_DIAGNOSTIC_DO_NOT_USE"

    _write_json_strict_atomic(out_abs, summary)

    print("\n=== k02 STEP-8 P_5 PAIRED FULL-MAP DIAGNOSTIC @ S1 (-11 dB), Pfa_map=1e-2 ===", flush=True)
    for a in CAL_ARMS:
        s = arm_sum[a]
        print(
            f"  {a:23s} | Thr={s['thr_db']:+5.2f}dB | ValPfa={s['val_pfa_map']*100:.2f}% (C1={s['c1_pass']}) | "
            f"Pd_loc={s['pos_pd_loc']*100:5.1f}% ({s['pos_k_loc']}/{s['n_pos']}) | Mean={s['pos_score_db_mean']:+5.2f}dB | "
            f"SER={s['pos_ser_pre_fb_mean']*100:.2f}%->{s['pos_ser_post_fb_mean']*100:.2f}%",
            flush=True,
        )
    print(f"P5 Delta_Pd (AFDM - ofdm_p5_full) = {c_afdm_vs_p5_full['point']*100:+.2f} pp, 95% env CI = [{c_afdm_vs_p5_full['ci95_envelope'][0]*100:+.2f}, {c_afdm_vs_p5_full['ci95_envelope'][1]*100:+.2f}] pp (hw={c_afdm_vs_p5_full['half_width']*100:.2f} pp)", flush=True)
    print(f"VERDICTS: {summary['verdicts']}", flush=True)
    print(f"Elapsed: {elapsed:.1f}s ({core_hours:.4f} core-h) -> {out_abs}", flush=True)


if __name__ == "__main__":
    main()
