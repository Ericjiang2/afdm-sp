#!/usr/bin/env python3
# Provenance (CLAUDE.md D18): Directly imports frozen ideas/l2/h_l2_r12_h02_conf.py without copying channel,
# uplink sounding, precoding, UE blind reception, or base radar scoring code. Prior frozen verdicts in
# ideas/l2/out_h_r11_h02/summary_h_r11_h02.json and ideas/l2/out_h_r12_h02/summary_h_r12_h02_conf.json remain untouched.
"""
Step-8 Astra REVISE Point P_4 Decisive Paired Diagnostic for Card I-20261125-h02 ([高要求] [轨B-ISAC], Round 12):
  Keeps ExtrapBlockRZF_Short8xQ2_AFDM Stage-1 2-block re-sounding, precoding, transmitted samples S_tot_cpi,
  and monostatic radar echoes Y_rad_cpi bit-for-bit identical, changing ONLY the radar scoring window from
  sub_cpi_len = 2 to sub_cpi_len = 16 (plus a single-constant companion control lifting max_sp: 6 -> Nt = 12
  symmetrically across 16-block arms).
Pre-registration: ideas/l2/PREDICTIONS_h_r12_h02_p4.md
"""
import sys
print(sys.executable, flush=True)

import os
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_k] = "1"

import argparse
import json
import tempfile
import time
from multiprocessing import Pool
import numpy as np
from scipy.stats import beta as beta_dist
from scipy.stats import betabinom

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import h_l2_r12_h02_conf as base


# Locked formal & smoke seed geometry (strictly >= 5,100,000; zero overlap with all R11/R12/dev seeds < 5,000,000 and 20261125):
FORMAL_CAL_BASE = 5100000
FORMAL_VAL_BASE = 5200000
FORMAL_POS_BASE = 5300000
FORMAL_N_CAL = 1599  # 0.95 * (1599 + 1) == 1520 exact integer -> Weibull quantile === 1520th order statistic, E[Pfa] == 80/1600 == 0.05 exact
FORMAL_N_VAL = 1600
FORMAL_N_POS = 600
FORMAL_BOOT_SEED = 5900001

SMOKE_CAL_BASE = 7100000
SMOKE_VAL_BASE = 7200000
SMOKE_POS_BASE = 7300000
SMOKE_N_CAL = 19     # 0.95 * (19 + 1) == 19 exact integer -> E[Pfa] == 1/20 == 0.05 exact
SMOKE_N_VAL = 20
SMOKE_N_POS = 8
SMOKE_BOOT_SEED = 7950001

PARITY_SCENE_SEED = 7900000
S1_SEED_OFFSET = 1000000
N_DUAL_BOOT = 2000
PFA_TARGET = 0.05

# Explicit protocol separation (Liu & Schober 2026 Sec. V pre-cued sector surveillance vs echo target generation):
# - PRE_SPECIFIED_SEARCH_THETA_DEG: public surveillance beam direction supplied identically to RX scoring across cal, val, and pos.
# - POS_TRUE_TARGET_THETA_DEG: echo-generator truth passed ONLY into _build_echo on target-present pos scenes (None on cal/val).
PRE_SPECIFIED_SEARCH_THETA_DEG = 40.0
POS_TRUE_TARGET_THETA_DEG = 40.0
PROTECTED_FROZEN_SUMMARY_BASENAMES = frozenset({"summary_h_r11_h02.json", "summary_h_r12_h02_conf.json"})

RADAR_ARMS = (
    "Prop_Q16",
    "Prop_SameWave_Short8xQ2",
    "ExtrapShort8xQ2_ScoredQ2",
    "ExtrapShort8xQ2_ScoredQ16",
    "ExtrapShort8xQ2_ScoredQ16_Sp12",
)


def verify_seed_disjointness():
    """Mechanically verify pairwise disjointness of all 7,599 formal seeds and zero overlap with all prior/dev/smoke/parity seeds."""
    formal_primary = (
        list(range(FORMAL_CAL_BASE, FORMAL_CAL_BASE + FORMAL_N_CAL))
        + list(range(FORMAL_VAL_BASE, FORMAL_VAL_BASE + FORMAL_N_VAL))
        + list(range(FORMAL_POS_BASE, FORMAL_POS_BASE + FORMAL_N_POS))
    )
    formal_s1 = [s + S1_SEED_OFFSET for s in formal_primary]
    formal_all = formal_primary + formal_s1 + [FORMAL_BOOT_SEED]
    expected_count = 2 * (FORMAL_N_CAL + FORMAL_N_VAL + FORMAL_N_POS) + 1
    assert len(formal_all) == expected_count, f"Unexpected seed list len: {len(formal_all)}"
    formal_set = set(formal_all)
    assert len(formal_set) == expected_count, "Duplicate seed inside formal seed set!"
    assert all(5100000 <= s < 6400000 for s in formal_set), "Formal seed outside locked [5100000, 6400000) range!"

    smoke_primary = (
        list(range(SMOKE_CAL_BASE, SMOKE_CAL_BASE + SMOKE_N_CAL))
        + list(range(SMOKE_VAL_BASE, SMOKE_VAL_BASE + SMOKE_N_VAL))
        + list(range(SMOKE_POS_BASE, SMOKE_POS_BASE + SMOKE_N_POS))
    )
    aux_seeds = set(smoke_primary + [s + S1_SEED_OFFSET for s in smoke_primary] + [SMOKE_BOOT_SEED, PARITY_SCENE_SEED, PARITY_SCENE_SEED + S1_SEED_OFFSET, 20261125])
    assert formal_set.isdisjoint(aux_seeds), "Formal seeds overlap smoke/parity/import seeds!"
    assert all(s >= 5000000 for s in formal_set), "Formal seeds overlap historical/dev [0, 5000000) range!"
    return {
        "formal_total_unique_seeds": expected_count,
        "formal_min_seed": int(min(formal_set)),
        "formal_max_seed": int(max(formal_set)),
        "disjoint_from_below_5m_and_aux": True,
    }


def score_pure_blue_rd_maxsp(Y_rad_cpi, S_tot_cpi, Nt_v, is_ofdm, is_dyn, win_center, sub_cpi_len, max_sp, theta_search_deg):
    """
    Identical line-for-line to h_l2_r12_h02_conf.unified_pure_blue_rd_score except:
      1. Spatial singular-mode cap 6 on line 619 is parameterized as max_sp;
      2. Pre-specified surveillance steering angle theta_search_deg is an explicit required input
         (never reading base.theta_tar or echo target truth).
    Verified bit-exact 0.0 diff against base.unified_pure_blue_rd_score at (max_sp=6, theta_search_deg=40.0) in G1.
    """
    theta_s = float(theta_search_deg)
    ar_t = base.steering_ula(base.Nr_rad, theta_s)
    at_t = base.steering_ula(Nt_v, theta_s)
    Y_beam_all = (Y_rad_cpi @ ar_t.conj()) / np.sqrt(float(base.Nr_rad))
    n_subs = base.Q // sub_cpi_len

    rd_map_acc = np.zeros((len(base.F_RAD_GRID), base.N_RAD_RANGE))
    jw, lw = win_center
    tot_proj_e = 0.0
    tot_raw_e = 0.0
    fn_clut = base.FN_CLUT_DYN if is_dyn else base.FN_CLUT_STA
    clut_et = base.CLUT_E_CACHE[(is_ofdm, is_dyn)]
    rad_et = base.RAD_E_CACHE[(is_ofdm, is_dyn)]

    for isub in range(n_subs):
        sl = slice(isub * sub_cpi_len, (isub + 1) * sub_cpi_len)
        Y_sub = Y_beam_all[sl]
        S_sub = S_tot_cpi[sl]
        q_len = sub_cpi_len

        S_flat = S_sub.reshape(q_len * base.N, Nt_v)
        _, sv_s, Vh_s = np.linalg.svd(S_flat, full_matrices=False)
        n_sp = min(int(max_sp), int(np.sum(sv_s > 0.01 * sv_s[0])))
        U_sp_modes = (S_flat @ Vh_s[:n_sp].conj().T).reshape(q_len, base.N, n_sp)
        q_idx = np.arange(q_len)[:, None]
        clut_cols = []
        for il in range(base.N_RAD_RANGE):
            for ic, fnc in enumerate(fn_clut):
                Ec_T = clut_et[il][ic]
                ph_q = np.exp(1j * 2 * np.pi * float(fnc) * q_idx * base.Tsym)
                for isp in range(n_sp):
                    clut_cols.append((ph_q * (U_sp_modes[:, :, isp] @ Ec_T)).ravel())
        B_clut = np.column_stack(clut_cols)
        Ub_s, sv_b, _ = np.linalg.svd(B_clut, full_matrices=False)
        Qb = Ub_s[:, sv_b > 1e-6 * max(float(sv_b[0]), 1e-12)]

        y_vec = Y_sub.ravel()
        y_proj = y_vec - Qb @ (Qb.conj().T @ y_vec)
        u_tx = S_sub @ at_t.conj()
        ph_rad_all = np.exp(1j * 2 * np.pi * base.F_RAD_GRID[:, None] * (q_idx.T) * base.Tsym)

        for il in range(base.N_RAD_RANGE):
            T_mat = np.empty((len(base.F_RAD_GRID), q_len * base.N), dtype=complex)
            for jf in range(len(base.F_RAD_GRID)):
                T_mat[jf] = (ph_rad_all[jf][:, None] * (u_tx @ rad_et[il][jf])).ravel()
            raw_es = np.maximum(np.sum(np.abs(T_mat) ** 2, axis=1), 1e-18)
            T_proj = T_mat - (T_mat @ Qb.conj()) @ Qb.T
            proj_es = np.maximum(np.sum(np.abs(T_proj) ** 2, axis=1), 1e-18)
            if il == lw:
                tot_proj_e += float(proj_es[jw])
                tot_raw_e += float(raw_es[jw])
            corr = T_proj.conj() @ y_proj
            rd_map_acc[:, il] += (np.abs(corr) ** 2) / proj_es

    bg_common = max(float(np.mean(rd_map_acc)), 1e-20)
    win_peak = float(np.max(rd_map_acc[max(0, jw - 1):min(len(base.F_RAD_GRID), jw + 2), lw]))
    j_pk, l_pk = np.unravel_index(int(np.argmax(rd_map_acc)), rd_map_acc.shape)
    blind_peak = float(rd_map_acc[j_pk, l_pk])
    return win_peak / bg_common, blind_peak / bg_common, (int(j_pk), int(l_pk)), float(tot_proj_e), float(tot_raw_e)


def _build_scene_waveforms_and_echoes(seed_i, role, has_tar, theta_tar_true_deg=None):
    """
    Constructs one Z=1 dynamic scene (nu_max=0.85, sig_nu_sub=0.025, sig_th_sub=0.8, snr_db=28.0, Nt=12, K=3)
    following the exact RNG draw order and equations of h_l2_r12_h02_conf.run_single_trial, while taking echo
    target truth angle theta_tar_true_deg as an independent input (None on cal/val; float on pos).
    """
    assert (role in ("cal", "val") and (has_tar is False) and (theta_tar_true_deg is None)) or (
        role == "pos" and (has_tar is True) and (theta_tar_true_deg is not None)
    ), f"Invalid role/has_tar/theta_tar_true_deg: {role}, {has_tar}, {theta_tar_true_deg}"
    nu_max, sig_nu_sub, sig_th_sub, snr_db, Nt_v, K_v = 0.85, 0.025, 0.8, 28.0, 12, 3
    is_dyn = True
    rng = np.random.default_rng(seed_i)
    sig2_c = 10.0 ** (-snr_db / 10.0)
    sig2_r = 10.0 ** (-20.0 / 10.0)
    clut_pow = 10.0 ** (+32.0 / 10.0) * sig2_r
    tar_pow = 10.0 ** (-3.0 / 10.0) * sig2_r

    e_u_pil, sc_data_nom, xp_af, af_bank, _, _, _, _ = base.CACHE_K3
    nom_degs = [-45.0, -10.0, 20.0]
    users = []
    for k in range(K_v):
        ells = np.array([0, 1, 2])
        base_offs = np.array([-4.5, 0.0, 4.5]) + rng.uniform(-1.0, 1.0, size=base.Pk)
        ths_c = nom_degs[k] + base_offs
        nus_c = rng.uniform(-nu_max, nu_max, size=base.Pk)
        clusters = []
        for p in range(base.Pk):
            s_als = (rng.standard_normal(base.M_sub) + 1j * rng.standard_normal(base.M_sub)) / np.sqrt(2.0 * base.Pk * base.M_sub)
            s_nus = nus_c[p] + rng.normal(0.0, sig_nu_sub, size=base.M_sub)
            s_ths = ths_c[p] + rng.normal(0.0, sig_th_sub, size=base.M_sub)
            clusters.append((ells[p], ths_c[p], nus_c[p], s_als, s_nus, s_ths))
        users.append(clusters)

    rng_s1 = np.random.default_rng(seed_i + S1_SEED_OFFSET)
    est_s1, sig2_ul_hat = base.stage1_real_uplink_sounding(users, Nt_v, K_v, is_dyn, sig2_c, rng_s1, sound_block_idx=-1)
    s_pil_vec, W_beams, _ = base.design_beam_matched_dual_isac(Nt_v, K_v, e_u_pil, est_s1, sig2_ul_hat, null_inter_user=True)

    est_sub_list = [est_s1]
    for isub in range(1, 8):
        es_sub, _ = base.stage1_real_uplink_sounding(users, Nt_v, K_v, is_dyn, sig2_c, rng_s1, sound_block_idx=2 * isub - 1)
        est_sub_list.append(es_sub)

    ref_syms = np.array([np.exp(1j * 2.0 * np.pi * k / float(K_v)) for k in range(K_v)], dtype=complex)
    d_pay = rng.choice(base.pts16, size=(base.Q, K_v, base.N_payload))
    d_blk = np.zeros((base.Q, K_v, base.N_act), dtype=complex)
    d_blk[:, :, 0] = ref_syms[None, :]
    d_blk[:, :, 1:] = d_pay

    z_u_unit = (rng.standard_normal((base.Q, K_v, base.N)) + 1j * rng.standard_normal((base.Q, K_v, base.N))) / np.sqrt(2.0)
    noise_u = np.sqrt(sig2_c) * z_u_unit
    noise_r = np.sqrt(sig2_r / 2.0) * (rng.standard_normal((base.Q, base.N, base.Nr_rad)) + 1j * rng.standard_normal((base.Q, base.N, base.Nr_rad)))

    c_ells = [0, 1, 3, 5]
    c_degs = [-30.0, 5.0, 38.0, 50.0]
    c_gains = np.sqrt(clut_pow / 4.0 / 2.0) * (rng.standard_normal(4) + 1j * rng.standard_normal(4))
    c_nus = rng.uniform(-0.03, 0.03, size=4)
    g_t = (np.sqrt(tar_pow) * np.exp(1j * rng.uniform(0, 2 * np.pi))) if has_tar else 0.0

    ell_tar, nu_tar = 2, 0.145
    jw_true = int(np.argmin(np.abs(base.F_RAD_GRID - nu_tar)))
    win_center = (jw_true, ell_tar)

    S_pil = np.zeros((base.N, Nt_v), dtype=complex)
    S_pil[base.m_p_af, :] = s_pil_vec

    # 1. Prop_BeamMatchedDualISAC_AFDM transmitted CPI waveform:
    S_ref_0 = np.zeros((base.N, Nt_v), dtype=complex)
    S_ref_0[base.D_af[0], :] = sum(ref_syms[k] * W_beams[k] for k in range(K_v))
    pay_frob2 = float(base.N_payload) * sum(float(np.sum(np.abs(W_beams[k]) ** 2)) for k in range(K_v))
    beta_std = base.solve_exact_expected_beta(S_pil, S_ref_0, pay_frob2, base.P_tot)
    exp_e_prop = float(np.sum(np.abs(S_pil + beta_std * S_ref_0) ** 2)) + (beta_std ** 2) * pay_frob2
    assert abs(exp_e_prop - base.P_tot) < 1e-9, f"Prop power mismatch: {exp_e_prop}"
    S_tot_prop = np.zeros((base.Q, base.N, Nt_v), dtype=complex)
    for q in range(base.Q):
        S_tot_prop[q] = S_pil.copy()
        S_tot_prop[q, base.D_af, :] += sum(beta_std * d_blk[q, k][:, None] * W_beams[k][None, :] for k in range(K_v))

    # 2. ExtrapBlockRZF_Short8xQ2_AFDM transmitted CPI waveform (re-sounded every 2 blocks):
    S_tot_short = np.zeros((base.Q, base.N, Nt_v), dtype=complex)
    for q in range(base.Q):
        isub = q // 2
        es_cur, sig2_cur, dt_steps = est_sub_list[isub], sig2_ul_hat, (q - (2 * isub - 1))
        H_rows = []
        for k in range(K_v):
            Hk_dt = np.zeros((base.N_act, base.N_act * Nt_v), dtype=complex)
            for p, (el, th_h, nu_h, al_m1) in enumerate(es_cur[k]):
                bq_h = al_m1 * np.exp(1j * 2 * np.pi * nu_h * dt_steps * base.Tsym)
                Ec_dt = base.make_E_op(base.A_af, base.c1_af, el, nu_h)[np.ix_(base.D_af, base.D_af)]
                at = base.steering_ula(Nt_v, th_h)
                Hk_dt += bq_h * np.kron(Ec_dt, at.conj()[None, :])
            H_rows.append(Hk_dt)
        H_all = np.vstack(H_rows)
        reg_i = K_v * base.N_act * sig2_cur / base.P_comm
        W_raw = H_all.conj().T @ np.linalg.inv(H_all @ H_all.conj().T + reg_i * np.eye(K_v * base.N_act))

        ref_mask = np.zeros(K_v * base.N_act, dtype=bool)
        ref_vec = np.zeros(K_v * base.N_act, dtype=complex)
        for k in range(K_v):
            ref_mask[k * base.N_act] = True
            ref_vec[k * base.N_act] = ref_syms[k]
        S_ref_s = np.zeros((base.N, Nt_v), dtype=complex)
        S_ref_s[base.D_af, :] = (W_raw @ ref_vec).reshape(base.N_act, Nt_v)
        pay_frob2_s = float(np.sum(np.abs(W_raw[:, ~ref_mask]) ** 2))
        beta_rzf = base.solve_exact_expected_beta(S_pil, S_ref_s, pay_frob2_s, base.P_tot)
        exp_e_s = float(np.sum(np.abs(S_pil + beta_rzf * S_ref_s) ** 2)) + (beta_rzf ** 2) * pay_frob2_s
        assert abs(exp_e_s - base.P_tot) < 1e-9, f"ExtrapShort8xQ2 power mismatch at q={q}: {exp_e_s}"
        S_tot_short[q] = S_pil.copy()
        S_tot_short[q, base.D_af, :] += beta_rzf * (W_raw @ d_blk[q].ravel()).reshape(base.N_act, Nt_v)

    def _build_echo(S_tot):
        Y_rad = noise_r.copy()
        for ic in range(4):
            Ec = base.make_E_op(base.A_af, base.c1_af, c_ells[ic], c_nus[ic])
            at_c = base.steering_ula(Nt_v, c_degs[ic])
            ar_c = base.steering_ula(base.Nr_rad, c_degs[ic])
            u_c = (S_tot @ at_c.conj()) @ Ec.T
            bq_c = c_gains[ic] * np.exp(1j * 2 * np.pi * c_nus[ic] * np.arange(base.Q) * base.Tsym)
            Y_rad += (bq_c[:, None] * u_c)[:, :, None] * ar_c[None, None, :]
        if has_tar:
            theta_true = float(theta_tar_true_deg)
            at_t = base.steering_ula(Nt_v, theta_true)
            ar_t = base.steering_ula(base.Nr_rad, theta_true)
            Et = base.make_E_op(base.A_af, base.c1_af, ell_tar, nu_tar)
            u_t = (S_tot @ at_t.conj()) @ Et.T
            bq_t = g_t * np.exp(1j * 2 * np.pi * nu_tar * np.arange(base.Q) * base.Tsym)
            Y_rad += (bq_t[:, None] * u_t)[:, :, None] * ar_t[None, None, :]
        return Y_rad

    Y_rad_prop = _build_echo(S_tot_prop)
    Y_rad_short = _build_echo(S_tot_short)

    # Lock arrays read-only so it is physically impossible for any scorer call to mutate S_tot_cpi or Y_rad_cpi:
    for arr in (S_tot_prop, Y_rad_prop, S_tot_short, Y_rad_short):
        arr.flags.writeable = False

    out_ser = {}
    if role == "pos":
        E_true_af = [[[base.make_E_op(base.A_af, base.c1_af, el, s_nus[m_i]) for m_i in range(base.M_sub)] for (el, _, _, _, s_nus, _) in users[k]] for k in range(K_v)]
        for arm_name, S_tot_use, is_rzf in (
            ("Prop_BeamMatchedDualISAC_AFDM", S_tot_prop, False),
            ("ExtrapBlockRZF_Short8xQ2_AFDM", S_tot_short, True),
        ):
            ser_u = []
            for k in range(K_v):
                Y_k_cpi = noise_u[:, k, :].copy()
                for q in range(base.Q):
                    for p, (_, _, _, s_als, s_nus, s_ths) in enumerate(users[k]):
                        for m_i in range(base.M_sub):
                            bq = s_als[m_i] * np.exp(1j * 2 * np.pi * s_nus[m_i] * q * base.Tsym)
                            Y_k_cpi[q] += bq * (E_true_af[k][p][m_i] @ (S_tot_use[q] @ base.steering_ula(Nt_v, s_ths[m_i]).conj()))
                d_hats = []
                for q in range(base.Q):
                    if is_rzf:
                        d_hats.append(base.blind_user_block_rx_tx_rzf(Y_k_cpi[q], False, xp_af, af_bank, None, None, None, base.obs_af, base.D_af, ref_syms[k]))
                    else:
                        d_hats.append(base.blind_user_block_rx_afdm(Y_k_cpi[q], xp_af, af_bank, sc_data_nom))
                d_hats_arr = np.array(d_hats)
                ser_u.append(float(np.mean(np.abs(d_hats_arr - d_pay[:, k, :]) > 1e-3)))
            out_ser[arm_name] = float(np.mean(ser_u))

    return S_tot_prop, Y_rad_prop, S_tot_short, Y_rad_short, win_center, out_ser


def eval_p4_scene(task):
    """Worker for 1 independent scene (cal, val, or pos) with independent echo truth and RX search steering."""
    seed_i, role, has_tar, theta_tar_true_deg, theta_search_deg = task
    Nt_v = 12
    S_tot_prop, Y_rad_prop, S_tot_short, Y_rad_short, win_center, out_ser = _build_scene_waveforms_and_echoes(
        seed_i, role, has_tar, theta_tar_true_deg=theta_tar_true_deg
    )

    _, sv_prop, _ = np.linalg.svd(S_tot_prop.reshape(base.Q * base.N, Nt_v), full_matrices=False)
    _, sv_short, _ = np.linalg.svd(S_tot_short.reshape(base.Q * base.N, Nt_v), full_matrices=False)
    n_sp_prop_001 = int(np.sum(sv_prop > 0.01 * sv_prop[0]))
    n_sp_short_001 = int(np.sum(sv_short > 0.01 * sv_short[0]))
    # Prop spans at most K + 1 = 4 spatial beams (<= 6), so max_sp=6 and max_sp=12 are mathematically identical on Prop:
    prop_sp12_identical = bool(n_sp_prop_001 <= 6)

    out_rad = {
        "Prop_Q16": score_pure_blue_rd_maxsp(Y_rad_prop, S_tot_prop, Nt_v, False, True, win_center, 16, 6, theta_search_deg),
        "Prop_SameWave_Short8xQ2": score_pure_blue_rd_maxsp(Y_rad_prop, S_tot_prop, Nt_v, False, True, win_center, 2, 6, theta_search_deg),
        "ExtrapShort8xQ2_ScoredQ2": score_pure_blue_rd_maxsp(Y_rad_short, S_tot_short, Nt_v, False, True, win_center, 2, 6, theta_search_deg),
        "ExtrapShort8xQ2_ScoredQ16": score_pure_blue_rd_maxsp(Y_rad_short, S_tot_short, Nt_v, False, True, win_center, 16, 6, theta_search_deg),
        "ExtrapShort8xQ2_ScoredQ16_Sp12": score_pure_blue_rd_maxsp(Y_rad_short, S_tot_short, Nt_v, False, True, win_center, 16, Nt_v, theta_search_deg),
    }
    meta_scene = {
        "has_tar_used": bool(has_tar),
        "theta_tar_true_used": theta_tar_true_deg,
        "theta_search_used": float(theta_search_deg),
        "prop_sp12_identical": prop_sp12_identical,
        "n_sp_prop_001": n_sp_prop_001,
        "n_sp_short_001": n_sp_short_001,
    }
    return out_ser, out_rad, meta_scene


def verify_g1_parity_and_invariants():
    """G1 gate: Red Line 1 invariants + seed disjointness + bit-exact parity against h_l2_r12_h02_conf.py + search/truth decoupling."""
    rl1 = base.verify_red_line_1_invariants()
    seed_info = verify_seed_disjointness()

    ref_ser, ref_rad = base.run_single_trial((PARITY_SCENE_SEED, "pos", True, 0.85, 0.025, 0.8, 28.0, 12, 3, False))
    S_p, Y_p, S_s, Y_s, wc, p4_ser = _build_scene_waveforms_and_echoes(
        PARITY_SCENE_SEED, "pos", True, theta_tar_true_deg=POS_TRUE_TARGET_THETA_DEG
    )
    _, p4_rad, p4_meta = eval_p4_scene(
        (PARITY_SCENE_SEED, "pos", True, POS_TRUE_TARGET_THETA_DEG, PRE_SPECIFIED_SEARCH_THETA_DEG)
    )

    ser_diffs = {
        k: abs(float(ref_ser[k]) - float(p4_ser[k]))
        for k in ("Prop_BeamMatchedDualISAC_AFDM", "ExtrapBlockRZF_Short8xQ2_AFDM")
    }
    rad_exact = {
        "Prop_Q16": ref_rad["Prop_BeamMatchedDualISAC_AFDM"] == p4_rad["Prop_Q16"],
        "Prop_SameWave_Short8xQ2": ref_rad["Prop_SameWave_Short8xQ2_AFDM"] == p4_rad["Prop_SameWave_Short8xQ2"],
        "ExtrapShort8xQ2_ScoredQ2": ref_rad["ExtrapBlockRZF_Short8xQ2_AFDM"] == p4_rad["ExtrapShort8xQ2_ScoredQ2"],
        "maxsp6_helper_vs_base_prop_q16": base.unified_pure_blue_rd_score(Y_p, S_p, 12, False, True, wc, 16) == p4_rad["Prop_Q16"],
        "maxsp6_helper_vs_base_short_q16": base.unified_pure_blue_rd_score(Y_s, S_s, 12, False, True, wc, 16) == p4_rad["ExtrapShort8xQ2_ScoredQ16"],
        "maxsp6_helper_vs_base_short_q2": base.unified_pure_blue_rd_score(Y_s, S_s, 12, False, True, wc, 2) == p4_rad["ExtrapShort8xQ2_ScoredQ2"],
        "prop_q16_maxsp12_vs_maxsp6": score_pure_blue_rd_maxsp(Y_p, S_p, 12, False, True, wc, 16, 12, PRE_SPECIFIED_SEARCH_THETA_DEG) == p4_rad["Prop_Q16"],
    }
    cal_ser, cal_rad_40, cal_meta = eval_p4_scene(
        (PARITY_SCENE_SEED, "cal", False, None, PRE_SPECIFIED_SEARCH_THETA_DEG)
    )
    _, cal_rad_30, _ = eval_p4_scene((PARITY_SCENE_SEED, "cal", False, None, 30.0))
    S_p_25, Y_p_25, _, _, _, _ = _build_scene_waveforms_and_echoes(
        PARITY_SCENE_SEED, "pos", True, theta_tar_true_deg=25.0
    )
    search_truth_decoupled_ok = bool(
        (cal_meta["theta_tar_true_used"] is None)
        and (cal_rad_40["Prop_Q16"][1] != cal_rad_30["Prop_Q16"][1])
        and np.array_equal(S_p, S_p_25)
        and (not np.array_equal(Y_p, Y_p_25))
    )
    readonly_arrays_ok = bool(all(not arr.flags.writeable for arr in (S_p, Y_p, S_s, Y_s)))
    cal_clean = (len(cal_ser) == 0) and (cal_meta["has_tar_used"] is False) and (cal_meta["theta_tar_true_used"] is None)

    g1_pass = bool(
        all(v == 0.0 for v in ser_diffs.values())
        and all(rad_exact.values())
        and p4_meta["prop_sp12_identical"]
        and cal_clean
        and search_truth_decoupled_ok
        and readonly_arrays_ok
    )
    return g1_pass, {
        "pass": g1_pass,
        "red_line_1": rl1,
        "seed_disjointness": seed_info,
        "parity_scene_seed": PARITY_SCENE_SEED,
        "ser_abs_diffs_vs_r12_conf": ser_diffs,
        "radar_tuple_bit_exact_matches": rad_exact,
        "cal_zero_target_verified": cal_clean,
        "search_vs_truth_theta_decoupled": search_truth_decoupled_ok,
        "readonly_cpi_arrays_verified": readonly_arrays_ok,
    }


def clopper_pearson_ci95(k_hits, n_trials):
    k = int(k_hits)
    n = int(n_trials)
    lo = 0.0 if k <= 0 else float(beta_dist.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k >= n else float(beta_dist.ppf(0.975, k + 1, n - k))
    return lo, hi


def betabinom_fwer_bounds(n_cal, n_val, pfa_target, m_arms):
    """Exact finite-sample Beta-Binomial two-sided FWER<=0.05 validation acceptance interval [k_lo, k_hi]."""
    ord_1idx = int(round((1.0 - pfa_target) * (n_cal + 1)))
    assert abs((1.0 - pfa_target) * (n_cal + 1) - ord_1idx) < 1e-9, f"(1-pfa)*(n_cal+1) not exact integer for n_cal={n_cal}"
    a = (n_cal + 1) - ord_1idx
    b = ord_1idx
    al_tail = 0.05 / (2.0 * float(m_arms))
    ks = np.arange(n_val + 1)
    cdf = betabinom.cdf(ks, n_val, a, b)
    sf = betabinom.sf(ks - 1, n_val, a, b)
    k_lo = int(ks[cdf > al_tail][0])
    k_hi = int(ks[sf > al_tail][-1])
    p_rej_each = float(betabinom.cdf(k_lo - 1, n_val, a, b) + betabinom.sf(k_hi, n_val, a, b))
    return {
        "ord_idx_0based": ord_1idx - 1,
        "ord_idx_1based": ord_1idx,
        "a_upper": a,
        "b_lower": b,
        "expected_null_pfa_exact": float(a) / float(n_cal + 1),
        "m_arms": int(m_arms),
        "k_bounds": [k_lo, k_hi],
        "pfa_bounds": [float(k_lo) / float(n_val), float(k_hi) / float(n_val)],
        "union_fwer_upper_bound": float(min(1.0, m_arms * p_rej_each)),
    }


def _atomic_write_json(path, obj):
    payload = json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    abs_path = os.path.abspath(path)
    out_dir = os.path.dirname(abs_path)
    os.makedirs(out_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_p4_", suffix=".json", dir=out_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, abs_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _validate_out_path(out_arg, is_smoke):
    abs_out = os.path.abspath(out_arg)
    real_out = os.path.realpath(abs_out)
    base_out = os.path.basename(abs_out)
    protected_paths = {
        os.path.realpath(os.path.join(SCRIPT_DIR, "summary_h_r11_h02.json")),
        os.path.realpath(os.path.join(SCRIPT_DIR, "summary_h_r12_h02_conf.json")),
        os.path.realpath(os.path.join(SCRIPT_DIR, "out_h_r11_h02", "summary_h_r11_h02.json")),
        os.path.realpath(os.path.join(SCRIPT_DIR, "out_h_r12_h02", "summary_h_r12_h02_conf.json")),
    }
    if (base_out in PROTECTED_FROZEN_SUMMARY_BASENAMES) or (real_out in protected_paths):
        raise ValueError(f"Refusing to overwrite prior frozen verdict summary file via --out: {out_arg}")
    formal_default_real = os.path.realpath(os.path.join(SCRIPT_DIR, "out_h_r12_h02_p4", "diag_h_r12_h02_p4.json"))
    if is_smoke and ((base_out == "diag_h_r12_h02_p4.json") or (real_out == formal_default_real)):
        raise ValueError("Refusing to write --smoke output to formal filename diag_h_r12_h02_p4.json!")
    return abs_out


def _classify_p4_outcome(
    diagnostic_valid,
    lit_lo,
    lit_hi,
    lit_hw,
    sp12_lo,
    sp12_hi,
    sp12_hw,
    rv_sp12_lo,
    rv_sp12_hw,
    a_q2_lo,
    a_q2_hw,
    a_sw_lo,
    a_sw_hw,
    trunc_lo,
    trunc_hi,
):
    """Pure deterministic classifier separating Red-Line-5 precision, Q=2 anchor effect, P_4 catch-up, and SP truncation."""
    hw_055_gates = {
        "lit_hw_le_0p1375": bool(lit_hw <= 0.1375),
        "sp12_hw_le_0p1375": bool(sp12_hw <= 0.1375),
        "anchor_q2_hw_le_0p1375": bool(a_q2_hw <= 0.1375),
        "anchor_samewave_hw_le_0p1375": bool(a_sw_hw <= 0.1375),
    }
    hw_055_ok = bool(all(hw_055_gates.values()))
    hw_sp12_eq10_ok = bool((sp12_hw <= 0.0250) and (rv_sp12_hw <= 0.0250))

    anchor_effect_gates = {
        "anchor_q2_lo_ge_0p55": bool(a_q2_lo >= 0.55),
        "anchor_samewave_lo_ge_0p55": bool(a_sw_lo >= 0.55),
    }
    anchors_q2_ge_055_ok = bool(all(anchor_effect_gates.values()))

    sp12_raw_catches_up = bool((sp12_hi <= 0.10) and (rv_sp12_lo >= 0.90))
    sp12_catches_up_confirmed = bool(sp12_raw_catches_up and hw_sp12_eq10_ok)

    if not diagnostic_valid:
        sp_trunc_attr = "INVALID_DIAGNOSTIC"
    elif trunc_lo > 0.0:
        sp_trunc_attr = "CONFIRMED_POSITIVE_MAXSP6_TRUNCATION_LOSS"
    elif trunc_hi < 0.0:
        sp_trunc_attr = "CONFIRMED_NEGATIVE_MAXSP12_EXTRA_CLUTTER_LOSS"
    else:
        sp_trunc_attr = "NO_CONFIRMED_SP_TRUNCATION_DIFF_STRADDLES_ZERO"

    if not diagnostic_valid:
        diag_outcome = "INVALID_DIAGNOSTIC_DO_NOT_USE"
    elif (not hw_055_ok) or (sp12_raw_catches_up and (not hw_sp12_eq10_ok)):
        diag_outcome = "INCONCLUSIVE_PRECISION_INSUFFICIENT"
    elif not anchors_q2_ge_055_ok:
        diag_outcome = "SHORT_WINDOW_ANCHOR_BELOW_055_RETRACT_CONFLICT"
    elif (lit_lo >= 0.55) and (sp12_lo >= 0.55):
        diag_outcome = "PROP_STILL_BEATS_BY_055_KEEP_RADAR_ADVANTAGE"
    elif (lit_hi < 0.55) and sp12_catches_up_confirmed:
        diag_outcome = "LITERAL_REFUTES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT"
    elif (lit_lo < 0.55 <= lit_hi) and sp12_catches_up_confirmed:
        diag_outcome = "LITERAL_STRADDLES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT"
    elif (lit_lo >= 0.55) and sp12_catches_up_confirmed:
        diag_outcome = "LITERAL_GE_055_UNDER_MAXSP6_ONLY_SP12_CATCHES_UP_RETRACT_CONFLICT"
    elif lit_hi < 0.55:
        diag_outcome = "LITERAL_REFUTES_055_SP12_NOT_CAUGHT_UP_REPORT_EXACT_DIFF"
    else:
        diag_outcome = "UNPROVEN_055_SP12_NOT_CAUGHT_UP_REPORT_EXACT_DIFF"

    retract_outcomes = {
        "SHORT_WINDOW_ANCHOR_BELOW_055_RETRACT_CONFLICT",
        "LITERAL_REFUTES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT",
        "LITERAL_STRADDLES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT",
        "LITERAL_GE_055_UNDER_MAXSP6_ONLY_SP12_CATCHES_UP_RETRACT_CONFLICT",
    }
    retract_conflict_claim = bool(diag_outcome in retract_outcomes)
    decision_ready = bool(diag_outcome not in {"INVALID_DIAGNOSTIC_DO_NOT_USE", "INCONCLUSIVE_PRECISION_INSUFFICIENT"})
    return {
        "hw_055_gates": hw_055_gates,
        "hw_055_ok": hw_055_ok,
        "hw_sp12_eq10_ok": hw_sp12_eq10_ok,
        "anchor_effect_gates": anchor_effect_gates,
        "anchors_q2_ge_055_ok": anchors_q2_ge_055_ok,
        "sp12_catches_up_confirmed": sp12_catches_up_confirmed,
        "sp_truncation_attribution": sp_trunc_attr,
        "diag_outcome": diag_outcome,
        "retract_conflict_claim": retract_conflict_claim,
        "decision_ready": decision_ready,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deinlab", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="diag_h_r12_h02_p4.json")
    args = ap.parse_args()

    if args.deinlab:
        assert sys.executable == "/home/guoyikun/.conda/envs/AFDM/bin/python", f"Wrong python: {sys.executable}"
    assert 1 <= args.workers <= 8, f"Workers {args.workers} exceeds 8-core cap!"
    out_abs = _validate_out_path(args.out, args.smoke)

    t_start = time.perf_counter()
    g1_pass, g1_info = verify_g1_parity_and_invariants()
    print(f"[G1 Parity & Invariants] pass={g1_pass}", flush=True)

    if args.smoke:
        n_cal, n_val, n_pos = SMOKE_N_CAL, SMOKE_N_VAL, SMOKE_N_POS
        cal_base, val_base, pos_base = SMOKE_CAL_BASE, SMOKE_VAL_BASE, SMOKE_POS_BASE
        boot_seed = SMOKE_BOOT_SEED
        pool = None
    else:
        n_cal, n_val, n_pos = FORMAL_N_CAL, FORMAL_N_VAL, FORMAL_N_POS
        cal_base, val_base, pos_base = FORMAL_CAL_BASE, FORMAL_VAL_BASE, FORMAL_POS_BASE
        boot_seed = FORMAL_BOOT_SEED
        pool = Pool(processes=args.workers)

    cal_tasks = [(cal_base + i, "cal", False, None, PRE_SPECIFIED_SEARCH_THETA_DEG) for i in range(n_cal)]
    val_tasks = [(val_base + i, "val", False, None, PRE_SPECIFIED_SEARCH_THETA_DEG) for i in range(n_val)]
    pos_tasks = [
        (pos_base + i, "pos", True, POS_TRUE_TARGET_THETA_DEG, PRE_SPECIFIED_SEARCH_THETA_DEG) for i in range(n_pos)
    ]

    try:
        map_fn = pool.map if pool is not None else map
        cal_res = list(map_fn(eval_p4_scene, cal_tasks))
        print(f"[Cal Done: {n_cal} target-free scenes]", flush=True)
        val_res = list(map_fn(eval_p4_scene, val_tasks))
        print(f"[Val Done: {n_val} target-free scenes]", flush=True)
        pos_res = list(map_fn(eval_p4_scene, pos_tasks))
        print(f"[Pos Done: {n_pos} target-present paired scenes]", flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    # Verify G2 (zero target truth in cal/val + Prop max_sp=12 mathematical identity across every single scene):
    g2_no_truth_cal_val = bool(
        all((not r[2]["has_tar_used"]) and (r[2]["theta_tar_true_used"] is None) and (len(r[0]) == 0) for r in cal_res)
        and all((not r[2]["has_tar_used"]) and (r[2]["theta_tar_true_used"] is None) and (len(r[0]) == 0) for r in val_res)
        and all(r[2]["has_tar_used"] and (r[2]["theta_tar_true_used"] == POS_TRUE_TARGET_THETA_DEG) for r in pos_res)
    )
    prop_sp12_all_scenes_identical = bool(
        all(r[2]["prop_sp12_identical"] for r in cal_res)
        and all(r[2]["prop_sp12_identical"] for r in val_res)
        and all(r[2]["prop_sp12_identical"] for r in pos_res)
    )

    nonfinite_errors = []
    for split_name, split_res in (("cal", cal_res), ("val", val_res), ("pos", pos_res)):
        for idx, (s_d, r_d, _) in enumerate(split_res):
            for k_s, v_s in s_d.items():
                if not np.isfinite(v_s):
                    nonfinite_errors.append(f"{split_name}[{idx}].ser.{k_s}")
            for arm in RADAR_ARMS:
                ws, bs, (jp, lp), tpe, tre = r_d[arm]
                if not (np.isfinite(ws) and np.isfinite(bs) and np.isfinite(tpe) and np.isfinite(tre)):
                    nonfinite_errors.append(f"{split_name}[{idx}].rad.{arm}")
    raw_inputs_finite_ok = (len(nonfinite_errors) == 0)

    bb_spec = betabinom_fwer_bounds(n_cal, n_val, PFA_TARGET, len(RADAR_ARMS))
    ord_idx = bb_spec["ord_idx_0based"]
    k_lo, k_hi = bb_spec["k_bounds"]
    ell_tar = 2
    jw_true = int(np.argmin(np.abs(base.F_RAD_GRID - 0.145)))

    # Synchronized dual (cal + pos) bootstrap indices preserving exact scene-level pairing across all arms:
    rng_boot = np.random.default_rng(boot_seed)
    ib_cal = rng_boot.integers(0, n_cal, size=(N_DUAL_BOOT, n_cal))
    ib_pos = rng_boot.integers(0, n_pos, size=(N_DUAL_BOOT, n_pos))

    arms_out = {}
    bhits_point = {}
    bhits_boot = {}
    proj_keep_scene_db = {}

    for arm in RADAR_ARMS:
        cw = np.array([r[1][arm][0] for r in cal_res], dtype=float)
        cb = np.array([r[1][arm][1] for r in cal_res], dtype=float)
        vw = np.array([r[1][arm][0] for r in val_res], dtype=float)
        vb = np.array([r[1][arm][1] for r in val_res], dtype=float)
        pw = np.array([r[1][arm][0] for r in pos_res], dtype=float)
        pb = np.array([r[1][arm][1] for r in pos_res], dtype=float)
        pl = [r[1][arm][2] for r in pos_res]
        tpe = np.array([r[1][arm][3] for r in pos_res], dtype=float)
        tre = np.array([r[1][arm][4] for r in pos_res], dtype=float)

        tw = float(np.quantile(cw, 1.0 - PFA_TARGET, method="weibull"))
        tb = float(np.quantile(cb, 1.0 - PFA_TARGET, method="weibull"))
        tb_ord = float(np.partition(cb, ord_idx)[ord_idx])
        assert abs(tb - tb_ord) < 1e-12, f"Weibull vs order-statistic mismatch on {arm}: {tb} vs {tb_ord}"

        val_k_fa = int(np.sum(vb > tb))
        val_pfa_b = float(val_k_fa) / float(n_val)
        val_cp_lo, val_cp_hi = clopper_pearson_ci95(val_k_fa, n_val)
        # Symmetric anti-inflation hard cap <= 0.075 across all 5 radar arms in formal mode (note k_hi/1600 = 114/1600 = 0.07125 <= 0.075):
        cap_ok = (val_pfa_b <= 0.075) if (not args.smoke) else True
        c1_arm_ok = bool(raw_inputs_finite_ok and (k_lo <= val_k_fa <= k_hi) and cap_ok)

        loc_ok = np.array([(abs(pl[i][0] - jw_true) <= 2) and (pl[i][1] == ell_tar) for i in range(n_pos)], dtype=bool)
        alarm_on = pb > tb
        bh = (alarm_on & loc_ok).astype(float)
        bhits_point[arm] = bh

        tb_b = np.partition(cb[ib_cal], ord_idx, axis=1)[:, ord_idx][:, None]
        bh_b = ((pb[ib_pos] > tb_b) & loc_ok[ib_pos]).astype(float)
        bhits_boot[arm] = bh_b

        k_loc = int(np.sum(bh > 0.5))
        pd_pt = float(k_loc) / float(n_pos)
        cp_lo, cp_hi = clopper_pearson_ci95(k_loc, n_pos)
        b_pds = np.mean(bh_b, axis=1)
        db_lo, db_hi = float(np.quantile(b_pds, 0.025)), float(np.quantile(b_pds, 0.975))
        env_lo = float(min(cp_lo, db_lo))
        env_hi = float(max(cp_hi, db_hi))
        env_hw = float(max(pd_pt - env_lo, env_hi - pd_pt))

        pk_ratio_db = float(10.0 * np.log10(max(float(np.sum(tpe)) / max(float(np.sum(tre)), 1e-18), 1e-12)))
        pk_sc_db = 10.0 * np.log10(np.maximum(tpe / np.maximum(tre, 1e-18), 1e-12))
        proj_keep_scene_db[arm] = pk_sc_db

        arms_out[arm] = {
            "n_cal": n_cal,
            "n_val": n_val,
            "n_pos": n_pos,
            "thr_blind": tb,
            "thr_win": tw,
            "val_k_fa_blind": val_k_fa,
            "val_pfa_blind": val_pfa_b,
            "val_pfa_blind_ci95_cp": [val_cp_lo, val_cp_hi],
            "val_pfa_win": float(np.mean(vw > tw)),
            "c1_pass": c1_arm_ok,
            "pos_k_loc": k_loc,
            "loc_blind_pd": pd_pt,
            "loc_blind_pd_ci95_cp": [cp_lo, cp_hi],
            "loc_blind_pd_ci95_dual_boot": [db_lo, db_hi],
            "loc_blind_pd_ci95_envelope": [env_lo, env_hi],
            "loc_blind_pd_env_half_width": env_hw,
            "pos_mis_rate": float(np.mean(alarm_on & (~loc_ok))),
            "pos_miss_rate": float(np.mean(~alarm_on)),
            "win_pd": float(np.mean(pw > tw)),
            "proj_keep_db": pk_ratio_db,
            "proj_keep_db_scene_ci95": base.paired_ci95(pk_sc_db),
        }

    def _paired_pd_contrast(a1, a2):
        h1, h2 = bhits_point[a1], bhits_point[a2]
        nc = base.newcombe_paired_binary_ci95(h1, h2)
        b_diffs = np.mean(bhits_boot[a1] - bhits_boot[a2], axis=1)
        db_lo, db_hi = float(np.quantile(b_diffs, 0.025)), float(np.quantile(b_diffs, 0.975))
        pt = nc["mean"]
        env_lo = float(min(nc["ci95_low"], db_lo))
        env_hi = float(max(nc["ci95_high"], db_hi))
        env_hw = float(max(pt - env_lo, env_hi - pt))
        n10 = int(np.sum((h1 > 0.5) & (h2 < 0.5)))
        n01 = int(np.sum((h1 < 0.5) & (h2 > 0.5)))
        return {
            "arm_1": a1,
            "arm_2": a2,
            "mean": pt,
            "discordant_n10_n01": [n10, n01],
            "ci95_newcombe": [nc["ci95_low"], nc["ci95_high"]],
            "newcombe_half_width": nc["ci95_half_width"],
            "ci95_dual_boot": [db_lo, db_hi],
            "dual_boot_half_width": float(max(pt - db_lo, db_hi - pt)),
            "ci95_envelope": [env_lo, env_hi],
            "env_half_width": env_hw,
        }

    contrasts = {
        "P4_literal_PropQ16_minus_ExtrapShort8xQ2_ScoredQ16": _paired_pd_contrast("Prop_Q16", "ExtrapShort8xQ2_ScoredQ16"),
        "P4_sp12_PropQ16_minus_ExtrapShort8xQ2_ScoredQ16_Sp12": _paired_pd_contrast("Prop_Q16", "ExtrapShort8xQ2_ScoredQ16_Sp12"),
        "sp_trunc_effect_on_rival_Sp12_minus_MaxSp6": _paired_pd_contrast("ExtrapShort8xQ2_ScoredQ16_Sp12", "ExtrapShort8xQ2_ScoredQ16"),
        "rival_window_effect_ScoredQ16_minus_ScoredQ2": _paired_pd_contrast("ExtrapShort8xQ2_ScoredQ16", "ExtrapShort8xQ2_ScoredQ2"),
        "rival_window_effect_ScoredQ16_Sp12_minus_ScoredQ2": _paired_pd_contrast("ExtrapShort8xQ2_ScoredQ16_Sp12", "ExtrapShort8xQ2_ScoredQ2"),
        "anchor_PropQ16_minus_ExtrapShort8xQ2_ScoredQ2": _paired_pd_contrast("Prop_Q16", "ExtrapShort8xQ2_ScoredQ2"),
        "anchor_PropQ16_minus_PropSameWave_Short8xQ2": _paired_pd_contrast("Prop_Q16", "Prop_SameWave_Short8xQ2"),
        "proj_keep_db_diff_PropQ16_minus_ExtrapShort8xQ2_ScoredQ16": base.paired_ci95(proj_keep_scene_db["Prop_Q16"] - proj_keep_scene_db["ExtrapShort8xQ2_ScoredQ16"]),
        "proj_keep_db_diff_PropQ16_minus_ExtrapShort8xQ2_ScoredQ16_Sp12": base.paired_ci95(proj_keep_scene_db["Prop_Q16"] - proj_keep_scene_db["ExtrapShort8xQ2_ScoredQ16_Sp12"]),
    }

    ser_pos = {
        k: base.paired_ci95([r[0][k] for r in pos_res])
        for k in ("Prop_BeamMatchedDualISAC_AFDM", "ExtrapBlockRZF_Short8xQ2_AFDM")
    }
    ser_diff_short_minus_prop = base.paired_ci95(
        np.array([r[0]["ExtrapBlockRZF_Short8xQ2_AFDM"] for r in pos_res])
        - np.array([r[0]["Prop_BeamMatchedDualISAC_AFDM"] for r in pos_res])
    )

    c1_per_arm = {arm: arms_out[arm]["c1_pass"] for arm in RADAR_ARMS}
    c1_validity = bool(all(c1_per_arm.values()))
    diagnostic_valid = bool(
        g1_pass
        and g2_no_truth_cal_val
        and prop_sp12_all_scenes_identical
        and raw_inputs_finite_ok
        and c1_validity
    )

    c_lit = contrasts["P4_literal_PropQ16_minus_ExtrapShort8xQ2_ScoredQ16"]
    c_sp12 = contrasts["P4_sp12_PropQ16_minus_ExtrapShort8xQ2_ScoredQ16_Sp12"]
    c_trunc = contrasts["sp_trunc_effect_on_rival_Sp12_minus_MaxSp6"]
    c_a_q2 = contrasts["anchor_PropQ16_minus_ExtrapShort8xQ2_ScoredQ2"]
    c_a_sw = contrasts["anchor_PropQ16_minus_PropSameWave_Short8xQ2"]

    lit_lo, lit_hi = c_lit["ci95_envelope"]
    lit_hw = c_lit["env_half_width"]
    sp12_lo, sp12_hi = c_sp12["ci95_envelope"]
    sp12_hw = c_sp12["env_half_width"]
    trunc_lo, trunc_hi = c_trunc["ci95_envelope"]

    rv_sp12_lo, _ = arms_out["ExtrapShort8xQ2_ScoredQ16_Sp12"]["loc_blind_pd_ci95_envelope"]
    rv_sp12_hw = arms_out["ExtrapShort8xQ2_ScoredQ16_Sp12"]["loc_blind_pd_env_half_width"]

    cls_res = _classify_p4_outcome(
        diagnostic_valid=diagnostic_valid,
        lit_lo=lit_lo,
        lit_hi=lit_hi,
        lit_hw=lit_hw,
        sp12_lo=sp12_lo,
        sp12_hi=sp12_hi,
        sp12_hw=sp12_hw,
        rv_sp12_lo=rv_sp12_lo,
        rv_sp12_hw=rv_sp12_hw,
        a_q2_lo=c_a_q2["ci95_envelope"][0],
        a_q2_hw=c_a_q2["env_half_width"],
        a_sw_lo=c_a_sw["ci95_envelope"][0],
        a_sw_hw=c_a_sw["env_half_width"],
        trunc_lo=trunc_lo,
        trunc_hi=trunc_hi,
    )
    hw_055_gates = cls_res["hw_055_gates"]
    hw_055_ok = cls_res["hw_055_ok"]
    hw_sp12_eq10_ok = cls_res["hw_sp12_eq10_ok"]
    anchor_effect_gates = cls_res["anchor_effect_gates"]
    anchors_q2_ge_055_ok = cls_res["anchors_q2_ge_055_ok"]
    sp12_catches_up_confirmed = cls_res["sp12_catches_up_confirmed"]
    sp_trunc_attr = cls_res["sp_truncation_attribution"]
    diag_outcome = cls_res["diag_outcome"]
    retract_conflict_claim = cls_res["retract_conflict_claim"]
    decision_ready = cls_res["decision_ready"]

    def _state_055(lo, hi, hw_ok):
        if not hw_ok:
            return "LOW_PRECISION"
        if lo >= 0.55:
            return "CONFIRMED_GE_055"
        if hi < 0.55:
            return "REFUTED_LT_055"
        return "UNPROVEN_STRADDLES_055"

    elapsed = round(time.perf_counter() - t_start, 2)
    out_obj = {
        "_argv": list(sys.argv),
        "_config": {
            "deinlab": bool(args.deinlab),
            "smoke": bool(args.smoke),
            "workers": int(args.workers),
            "out": out_abs,
            "pre_specified_search_theta_deg": PRE_SPECIFIED_SEARCH_THETA_DEG,
            "pos_true_target_theta_deg": POS_TRUE_TARGET_THETA_DEG,
            "n_cal": n_cal,
            "n_val": n_val,
            "n_pos": n_pos,
            "n_dual_boot": N_DUAL_BOOT,
            "pfa_target": PFA_TARGET,
        },
        "meta": {
            "card_id": "I-20261125-h02",
            "run_type": "step8_p4_paired_mechanism_diagnostic",
            "prior_frozen_verdicts_preserved": {
                "r11": "ideas/l2/out_h_r11_h02/summary_h_r11_h02.json (PASS_PRIMARY = false)",
                "r12_conf": "ideas/l2/out_h_r12_h02/summary_h_r12_h02_conf.json (PASS_PRIMARY = true)",
            },
            "python_executable": sys.executable,
            "smoke_mode": bool(args.smoke),
            "workers": int(args.workers),
            "elapsed_sec": elapsed,
            "reserved_core_hours": round(elapsed * float(1 if args.smoke else args.workers) / 3600.0, 4),
            "seed_bases": {"cal": cal_base, "val": val_base, "pos": pos_base, "boot": boot_seed},
            "sample_sizes": {"n_cal": n_cal, "n_val": n_val, "n_pos": n_pos, "n_dual_boot": N_DUAL_BOOT},
            "pfa_target": PFA_TARGET,
            "pre_specified_search_theta_deg": PRE_SPECIFIED_SEARCH_THETA_DEG,
            "pos_true_target_theta_deg": POS_TRUE_TARGET_THETA_DEG,
        },
        "gates": {
            "G1_parity_and_invariants": g1_info,
            "G2_no_truth_in_cal_val": g2_no_truth_cal_val,
            "Prop_Q16_maxsp12_bit_identical_all_scenes": prop_sp12_all_scenes_identical,
            "RAW_INPUTS_FINITE_OK": raw_inputs_finite_ok,
            "nonfinite_errors": nonfinite_errors,
            "C1_betabinom_fwer_spec": bb_spec,
        },
        "z1_28dB_radar_arms": arms_out,
        "z1_28dB_comm_ser_paired_check": {
            "arms": ser_pos,
            "ExtrapShort8xQ2_minus_Prop": ser_diff_short_minus_prop,
        },
        "contrasts": contrasts,
        "verdicts": {
            "G1_PARITY_AND_INVARIANTS": g1_pass,
            "G2_NO_TRUTH_IN_CAL_VAL": g2_no_truth_cal_val,
            "PROP_SP12_IDENTICAL_ALL_SCENES": prop_sp12_all_scenes_identical,
            "RAW_INPUTS_FINITE_OK": raw_inputs_finite_ok,
            "C1_per_arm": c1_per_arm,
            "C1_VALIDITY": c1_validity,
            "DIAGNOSTIC_VALID": diagnostic_valid,
            "DECISION_READY": decision_ready,
            "REDLINE5_PRECISION_GATES": {
                **hw_055_gates,
                "hw_055_all_ok": hw_055_ok,
                "hw_sp12_eq10_ok": hw_sp12_eq10_ok,
            },
            "SHORT_WINDOW_ANCHOR_EFFECT_GATES": {
                **anchor_effect_gates,
                "anchors_q2_ge_055_all_ok": anchors_q2_ge_055_ok,
            },
            "THREE_STATE_055": {
                "literal_maxsp6": _state_055(lit_lo, lit_hi, hw_055_gates["lit_hw_le_0p1375"]),
                "symmetric_maxsp12": _state_055(sp12_lo, sp12_hi, hw_055_gates["sp12_hw_le_0p1375"]),
            },
            "SP12_CATCHES_UP_CONFIRMED": sp12_catches_up_confirmed,
            "SP_TRUNCATION_ATTRIBUTION": sp_trunc_attr,
            "DIAGNOSTIC_OUTCOME": diag_outcome,
            "RETRACT_ISAC_CONFLICT_CLAIM": retract_conflict_claim,
        },
    }

    _atomic_write_json(out_abs, out_obj)
    print(f"\nSaved P_4 diagnostic JSON to {out_abs} | outcome={diag_outcome} | valid={diagnostic_valid}", flush=True)


if __name__ == "__main__":
    main()
