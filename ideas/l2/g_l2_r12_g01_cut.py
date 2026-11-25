import sys
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g_l2_r11_g01 as base_g01

import argparse
import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np

FORMAL_N_S1 = 1500
FORMAL_N_S2 = 240

_R12_SEED_BASE = {
    "S1_K3_Nbs5_NF16": 4100000,
    "S2_K4_Nbs6_NF15": 4200000,
}


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        fv = float(obj)
        return fv if math.isfinite(fv) else None
    return obj


def cap_ratio_lhw(tau):
    return float(min(0.25 * math.log(tau), math.log(1.25)))


def classify_ci_vs_bar(ci_dict, bar):
    if ci_dict.get("observed_zero_undecidable", False):
        return "UNDECIDABLE_ZERO_COUNTS"
    lo, hi = float(ci_dict["ci95"][0]), float(ci_dict["ci95"][1])
    if lo >= bar:
        return "CONFIRMED_GE_BAR"
    if hi < bar:
        return "REFUTED_LT_BAR"
    return "UNPROVEN_STRADDLES_BAR"


def paired_ber_ratio_ci95_strict(err_num_list, err_den_list, n_boot=4000, seed=20261200):
    en = np.asarray(err_num_list, dtype=float)
    ed = np.asarray(err_den_list, dtype=float)
    M = len(en)
    s_en, s_ed = float(np.sum(en)), float(np.sum(ed))
    if M < 2 or s_en <= 0.0 or s_ed <= 0.0:
        pt = (s_en / s_ed) if s_ed > 0.0 else (float("inf") if s_en > 0.0 else float("nan"))
        return {
            "point": pt,
            "ci95": [0.0, float("inf")],
            "log_halfwidth": float("inf"),
            "observed_zero_undecidable": True,
        }
    pt = s_en / s_ed
    rng_b = np.random.default_rng(seed)
    idx = rng_b.integers(0, M, size=(n_boot, M))
    sn = np.sum(en[idx], axis=1)
    sd = np.sum(ed[idx], axis=1)
    rat = np.where(sd > 0.0, np.where(sn > 0.0, sn / np.where(sd > 0.0, sd, 1.0), 0.0), np.inf)
    sr = np.sort(rat)
    lo = float(sr[int(np.floor(0.025 * (n_boot - 1)))])
    hi = float(sr[int(np.ceil(0.975 * (n_boot - 1)))])
    valid_finite = bool(np.isfinite(hi) and (lo > 0.0))
    lhw = 0.5 * float(np.log(hi / lo)) if valid_finite else float("inf")
    return {
        "point": pt,
        "ci95": [lo, hi],
        "log_halfwidth": lhw,
        "observed_zero_undecidable": False,
    }


def _inconclusive_card_routing():
    return {
        "status": "INCONCLUSIVE_NOT_FORMAL_OR_PRECISION_FAILED",
        "literal_3win_single_cov13_note": "NO_ACTION_UNTIL_VALID_FORMAL",
        "direct_gls_precision_13_claim": "NO_ACTION_UNTIL_VALID_FORMAL",
        "right_guard_2win_cov_conditioning_claim": "NO_ACTION_UNTIL_VALID_FORMAL",
        "all_interwindow_3win_cov_claim": "NO_ACTION_UNTIL_VALID_FORMAL",
        "card_wraparound_narrative_action": "NO_ACTION_UNTIL_VALID_FORMAL",
        "intra_window_single_factor_3x": "NO_ACTION_UNTIL_VALID_FORMAL",
        "same_pulse_whole_receiver_checks": "NO_ACTION_UNTIL_VALID_FORMAL",
    }


class CutScenarioEnv(base_g01.ScenarioEnv):
    def __init__(self, N, K, Nbs, P, weak_users, near_far_db, rolloff=0.25):
        super().__init__(N, K, Nbs, P, weak_users, near_far_db, rolloff=rolloff)
        dop_half = self.alpha_max + self.k_nu
        self.w_head_end = int(self.pilots[max(self.weak_users)] + dop_half + 1)
        self.w_rguard_start = int(self.pilots[self.K - 1] + dop_half + 1)
        self.idx_head = [a * self.M_O + m for m in range(0, self.w_head_end) for a in range(self.Nbs)]
        self.idx_mid = [a * self.M_O + m for m in range(self.w_head_end, self.w_rguard_start) for a in range(self.Nbs)]
        self.idx_rguard = [a * self.M_O + m for m in range(self.w_rguard_start, self.M_O) for a in range(self.Nbs)]
        self.cut_diag_stats = {"literal_calls": 0, "literal_floored": 0, "literal_head_rel_dist": []}

    def check_raw_zero13_min_eig(self, paths_dict, s2_fixed, use_pulse=True, d_bins=None):
        # Directly inspects pre-projection zero-(1,3) Hermitian matrix on a specified paths_dict (called once per frame on full arm):
        G_all = self._build_leakage_matrix(paths_dict, use_pulse=use_pulse, d_bins=d_bins)
        M_tot = self.M_O * self.Nbs
        GG = G_all @ G_all.conj().T
        Sf = 0.5 * (GG + GG.conj().T) + s2_fixed * np.eye(M_tot)
        S4 = Sf.reshape((self.M_O, self.Nbs, self.M_O, self.Nbs), order="F")
        he, rs = self.w_head_end, self.w_rguard_start
        S4[:he, :, rs:, :] = 0.0
        S4[rs:, :, :he, :] = 0.0
        ev = np.linalg.eigvalsh(S4.reshape((M_tot, M_tot), order="F"))
        return float(ev[0])

    def build_whitener(self, paths_dict, s2_fixed, use_pulse=True, cov_mode="full", d_bins=None):
        if cov_mode in ("none", "diag_power", "no_cross_daft", "full"):
            return super().build_whitener(paths_dict, s2_fixed, use_pulse=use_pulse, cov_mode=cov_mode, d_bins=d_bins)

        G_all = self._build_leakage_matrix(paths_dict, use_pulse=use_pulse, d_bins=d_bins)
        if G_all is None:
            return None, None
        M_tot = self.M_O * self.Nbs
        GG = G_all @ G_all.conj().T
        Sf = 0.5 * (GG + GG.conj().T) + s2_fixed * np.eye(M_tot)
        S4 = Sf.reshape((self.M_O, self.Nbs, self.M_O, self.Nbs), order="F")
        he, rs = self.w_head_end, self.w_rguard_start

        if cov_mode == "cut_literal_psd":
            Sc = S4.copy()
            Sc[:he, :, rs:, :] = 0.0
            Sc[rs:, :, :he, :] = 0.0
            M2 = Sc.reshape((M_tot, M_tot), order="F")
            ev, U = np.linalg.eigh(M2)
            self.cut_diag_stats["literal_calls"] += 1
            if float(ev[0]) < float(s2_fixed):
                self.cut_diag_stats["literal_floored"] += 1
            ev_c = np.maximum(ev, s2_fixed)
            M_psd = (U * ev_c[None, :]) @ U.conj().T
            S4_psd = M_psd.reshape((self.M_O, self.Nbs, self.M_O, self.Nbs), order="F")
            rel_d = float(
                np.linalg.norm(S4_psd[:he, :, :he, :] - S4[:he, :, :he, :])
                / max(np.linalg.norm(S4[:he, :, :he, :]), 1e-12)
            )
            self.cut_diag_stats["literal_head_rel_dist"].append(rel_d)
            isq = 1.0 / np.sqrt(ev_c)
            Linv = (U * isq[None, :]).conj().T
            Cinv = (U * (isq ** 2)[None, :]) @ U.conj().T
            return Linv, Cinv

        if cov_mode == "cut_chordal_prec0":
            S12 = Sf[np.ix_(self.idx_head, self.idx_mid)]
            S22 = Sf[np.ix_(self.idx_mid, self.idx_mid)]
            S23 = Sf[np.ix_(self.idx_mid, self.idx_rguard)]
            S13_ch = S12 @ np.linalg.solve(S22, S23)
            Mc = Sf.copy()
            Mc[np.ix_(self.idx_head, self.idx_rguard)] = S13_ch
            Mc[np.ix_(self.idx_rguard, self.idx_head)] = S13_ch.conj().T
            Lc = np.linalg.cholesky(Mc)
            Linv = np.linalg.solve(Lc, np.eye(M_tot))
            return Linv, Linv.conj().T @ Linv

        if cov_mode == "cut_2blk_rguard":
            Sc = np.zeros_like(S4)
            Sc[:rs, :, :rs, :] = S4[:rs, :, :rs, :]
            Sc[rs:, :, rs:, :] = S4[rs:, :, rs:, :]
            M2 = Sc.reshape((M_tot, M_tot), order="F")
            Lc = np.linalg.cholesky(M2)
            Linv = np.linalg.solve(Lc, np.eye(M_tot))
            return Linv, Linv.conj().T @ Linv

        if cov_mode == "cut_2blk_head":
            Sc = np.zeros_like(S4)
            Sc[:he, :, :he, :] = S4[:he, :, :he, :]
            Sc[he:, :, he:, :] = S4[he:, :, he:, :]
            M2 = Sc.reshape((M_tot, M_tot), order="F")
            Lc = np.linalg.cholesky(M2)
            Linv = np.linalg.solve(Lc, np.eye(M_tot))
            return Linv, Linv.conj().T @ Linv

        if cov_mode == "cut_3blk_windows":
            Sc = np.zeros_like(S4)
            Sc[:he, :, :he, :] = S4[:he, :, :he, :]
            Sc[he:rs, :, he:rs, :] = S4[he:rs, :, he:rs, :]
            Sc[rs:, :, rs:, :] = S4[rs:, :, rs:, :]
            M2 = Sc.reshape((M_tot, M_tot), order="F")
            Lc = np.linalg.cholesky(M2)
            Linv = np.linalg.solve(Lc, np.eye(M_tot))
            return Linv, Linv.conj().T @ Linv

        raise ValueError(f"Unknown cov_mode: {cov_mode}")

    def run_same_pulse_arm(self, Y_rx, cov_mode, s2_common, d_bins=None, return_paths=False):
        if d_bins is None:
            d_bins = self.data_bins
        Y_obs = Y_rx[self.obs_idx, :]
        s2_blind = float(s2_common)
        B_use = self.B_pul
        u_en = np.array([np.sum(np.abs(Y_obs[max(0, self.pilots[u] - 11) : self.pilots[u] + 2, :]) ** 2) for u in range(self.K)])
        u_ord = np.argsort(u_en)[::-1]
        paths = {u: [] for u in range(self.K)}
        R_c = Y_obs.copy()
        max_e = u_en[u_ord[0]]

        for idx_u, u in enumerate(u_ord):
            if cov_mode != "none" and idx_u > 0 and u_en[u] < 0.45 * max_e:
                Linv, Cinv = self.build_whitener(paths, s2_blind, use_pulse=True, cov_mode=cov_mode, d_bins=d_bins)
            else:
                Linv, Cinv = None, None
            for _ in range(self.P):
                it0, inu0, ith0 = self.coarse_peak(R_c, u, Cinv, B_use[u])
                est = self.refine_newton(R_c, u, self.tau_grid[it0], self.nu_grid[inu0], self.th_grid[ith0], Linv, True, n_it=5)
                paths[u].append(est)
                R_c -= est[3] * est[4]

        Linv_pre, _ = self.build_whitener(paths, s2_blind, use_pulse=True, cov_mode=cov_mode, d_bins=d_bins)
        paths, R_c = self.joint_polish(Y_obs, paths, Linv_pre, True, n_it=4)

        for u in u_ord:
            ref_paths = {ku: paths[ku] for ku in range(self.K) if ku != u} if u_en[u] >= 0.45 * max_e else paths
            Linv, Cinv = self.build_whitener(ref_paths, s2_blind, use_pulse=True, cov_mode=cov_mode, d_bins=d_bins)
            for p_i in range(self.P):
                old = paths[u][p_i]
                Rp = R_c + old[3] * old[4]
                it_w, inu_w, ith_w = self.coarse_peak(Rp, u, Cinv, B_use[u])
                c1_e = self.refine_newton(Rp, u, old[0], old[1], old[2], Linv, True, n_it=5)
                c2_e = self.refine_newton(Rp, u, self.tau_grid[it_w], self.nu_grid[inu_w], self.th_grid[ith_w], Linv, True, n_it=5)
                r1 = (Rp - c1_e[3] * c1_e[4]).reshape(-1, order="F")
                r2 = (Rp - c2_e[3] * c2_e[4]).reshape(-1, order="F")
                e1 = np.sum(np.abs(r1 if Linv is None else (Linv @ r1)) ** 2)
                e2 = np.sum(np.abs(r2 if Linv is None else (Linv @ r2)) ** 2)
                paths[u][p_i] = c1_e if e1 <= e2 else c2_e
                R_c = Rp - paths[u][p_i][3] * paths[u][p_i][4]

        Linv, _ = self.build_whitener(paths, s2_blind, use_pulse=True, cov_mode=cov_mode, d_bins=d_bins)
        paths, _ = self.joint_polish(Y_obs, paths, Linv, True, n_it=5)

        H_list = []
        for u in range(self.K):
            Hu = np.zeros((self.Nbs, self.N, self.N), dtype=complex)
            for (tp, np_, thp, bp, _) in paths[u]:
                Hm = self.full_pulse_H(tp, np_)
                Hu += bp * self.ula_vec_and_deriv(thp)[0][:, None, None] * Hm[None, :, :]
            H_list.append(Hu)
        if return_paths:
            return H_list, s2_blind, paths
        return H_list, s2_blind


def verify_g01_seed_disjointness():
    formal_s1 = [_R12_SEED_BASE["S1_K3_Nbs5_NF16"] + tr * 17 + 300 for tr in range(FORMAL_N_S1)]
    formal_s2 = [_R12_SEED_BASE["S2_K4_Nbs6_NF15"] + tr * 17 + 300 for tr in range(FORMAL_N_S2)]
    formal_all = formal_s1 + formal_s2
    formal_set = set(formal_all)
    unique_ok = len(formal_set) == len(formal_all)
    in_band_ok = (min(formal_s1) >= 4100000) and (max(formal_s1) < 4190000) and (min(formal_s2) >= 4200000) and (max(formal_s2) <= 4300000)

    nonformal_set = {91000, 1105000}
    nonformal_set.update(range(20261200, 20261300))
    for k in range(2):
        tr_sm = -100 - k
        nonformal_set.add(_R12_SEED_BASE["S1_K3_Nbs5_NF16"] + tr_sm * 17 + 300)
        nonformal_set.add(_R12_SEED_BASE["S2_K4_Nbs6_NF15"] + tr_sm * 17 + 300)
    disjoint_ok = len(formal_set.intersection(nonformal_set)) == 0
    return bool(unique_ok and in_band_ok and disjoint_ok)


def verify_cut_operator_invariants():
    # Inspects ONLY the 4 exact-SPD primary operators + pre-projection raw zero-(1,3) matrix (cut_literal_psd completely excluded!).
    seed_ok = verify_g01_seed_disjointness()
    env = CutScenarioEnv(128, 3, 5, 3, [0], 16.0, 0.25)
    env_s2 = CutScenarioEnv(128, 4, 6, 3, [0, 1], 15.0, 0.25)
    windows_exact_ok = bool(
        (env.w_head_end == 17)
        and (env.w_rguard_start == 47)
        and (env_s2.w_head_end == 32)
        and (env_s2.w_rguard_start == 62)
    )

    rng = np.random.default_rng(1105000)
    paths = {}
    for u in range(env.K):
        amp = np.sqrt(env.user_pow[u])
        paths[u] = [
            (
                float(rng.uniform(0.15, 1.90)),
                float(rng.uniform(-1.2, 1.2)),
                float(rng.uniform(-0.8, 0.8)),
                complex(amp * (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(6.0)),
                None,
            )
            for _ in range(env.P)
        ]
    s2 = 1e-3
    M_tot = env.M_O * env.Nbs
    G = env._build_leakage_matrix(paths, use_pulse=True)
    GG = G @ G.conj().T
    Sf = 0.5 * (GG + GG.conj().T) + s2 * np.eye(M_tot)
    S4 = Sf.reshape((env.M_O, env.Nbs, env.M_O, env.Nbs), order="F")
    he, rs = env.w_head_end, env.w_rguard_start

    raw_zero13_min_eig = env.check_raw_zero13_min_eig(paths, s2, use_pulse=True)
    raw_zero13_synth_nonspd = bool(raw_zero13_min_eig < 0.0)

    S12 = Sf[np.ix_(env.idx_head, env.idx_mid)]
    S22 = Sf[np.ix_(env.idx_mid, env.idx_mid)]
    S23 = Sf[np.ix_(env.idx_mid, env.idx_rguard)]
    M_exp_chordal = Sf.copy()
    S13_ch = S12 @ np.linalg.solve(S22, S23)
    M_exp_chordal[np.ix_(env.idx_head, env.idx_rguard)] = S13_ch
    M_exp_chordal[np.ix_(env.idx_rguard, env.idx_head)] = S13_ch.conj().T
    S4_exp_ch = M_exp_chordal.reshape((env.M_O, env.Nbs, env.M_O, env.Nbs), order="F")
    chordal_target_keep_exact_err = float(
        max(
            np.max(np.abs(S4_exp_ch[:he, :, :he, :] - S4[:he, :, :he, :])),
            np.max(np.abs(S4_exp_ch[he:rs, :, he:rs, :] - S4[he:rs, :, he:rs, :])),
            np.max(np.abs(S4_exp_ch[rs:, :, rs:, :] - S4[rs:, :, rs:, :])),
            np.max(np.abs(S4_exp_ch[:he, :, he:rs, :] - S4[:he, :, he:rs, :])),
            np.max(np.abs(S4_exp_ch[he:rs, :, :he, :] - S4[he:rs, :, :he, :])),
            np.max(np.abs(S4_exp_ch[he:rs, :, rs:, :] - S4[he:rs, :, rs:, :])),
            np.max(np.abs(S4_exp_ch[rs:, :, he:rs, :] - S4[rs:, :, he:rs, :])),
            np.max(np.abs(M_exp_chordal - M_exp_chordal.conj().T)),
        )
    )

    S4_2r = np.zeros_like(S4)
    S4_2r[:rs, :, :rs, :] = S4[:rs, :, :rs, :]
    S4_2r[rs:, :, rs:, :] = S4[rs:, :, rs:, :]
    M_exp_2r = S4_2r.reshape((M_tot, M_tot), order="F")

    S4_2h = np.zeros_like(S4)
    S4_2h[:he, :, :he, :] = S4[:he, :, :he, :]
    Sc_h_rest = S4[he:, :, he:, :]
    S4_2h[he:, :, he:, :] = Sc_h_rest
    M_exp_2h = S4_2h.reshape((M_tot, M_tot), order="F")

    S4_3b = np.zeros_like(S4)
    S4_3b[:he, :, :he, :] = S4[:he, :, :he, :]
    S4_3b[he:rs, :, he:rs, :] = S4[he:rs, :, he:rs, :]
    S4_3b[rs:, :, rs:, :] = S4[rs:, :, rs:, :]
    M_exp_3b = S4_3b.reshape((M_tot, M_tot), order="F")

    expected_map = {
        "cut_chordal_prec0": M_exp_chordal,
        "cut_2blk_rguard": M_exp_2r,
        "cut_2blk_head": M_exp_2h,
        "cut_3blk_windows": M_exp_3b,
    }

    inv_resids = {}
    linv_consist = {}
    min_eigs = {}
    actual_Cinvs = {}
    for m_chk, M_exp in expected_map.items():
        Li, Ci = env.build_whitener(paths, s2, use_pulse=True, cov_mode=m_chk)
        if Li is None or Ci is None:
            inv_resids[m_chk] = float("inf")
            linv_consist[m_chk] = float("inf")
            min_eigs[m_chk] = -1.0
            actual_Cinvs[m_chk] = np.eye(M_tot, dtype=complex)
            continue
        actual_Cinvs[m_chk] = Ci
        ev_ci = np.linalg.eigvalsh(0.5 * (Ci + Ci.conj().T))
        min_eigs[m_chk] = float(ev_ci[0])
        linv_consist[m_chk] = float(np.linalg.norm(Li.conj().T @ Li - Ci) / np.linalg.norm(Ci))
        inv_resids[m_chk] = float(np.linalg.norm(M_exp @ Ci - np.eye(M_tot)) / np.sqrt(M_tot))

    sl = {"1": slice(0, he), "2": slice(he, rs), "3": slice(rs, env.M_O)}
    ref_blk_norms = {
        (a, b): float(np.linalg.norm(S4[sl[a], :, sl[b], :]))
        for a in ("1", "2", "3")
        for b in ("1", "2", "3")
    }
    min_ref_blk_norm = float(min(ref_blk_norms.values()))
    kept_cov_spec = {
        "cut_chordal_prec0": [("1", "1"), ("2", "2"), ("3", "3"), ("1", "2"), ("2", "1"), ("2", "3"), ("3", "2")],
        "cut_2blk_rguard": [("1", "1"), ("2", "2"), ("3", "3"), ("1", "2"), ("2", "1")],
        "cut_2blk_head": [("1", "1"), ("2", "2"), ("3", "3"), ("2", "3"), ("3", "2")],
        "cut_3blk_windows": [("1", "1"), ("2", "2"), ("3", "3")],
    }
    zero_cov_spec = {
        "cut_2blk_rguard": [("1", "3"), ("3", "1"), ("2", "3"), ("3", "2")],
        "cut_2blk_head": [("1", "2"), ("2", "1"), ("1", "3"), ("3", "1")],
        "cut_3blk_windows": [("1", "2"), ("2", "1"), ("1", "3"), ("3", "1"), ("2", "3"), ("3", "2")],
    }
    kept_blk_own_errs = {}
    zero_blk_own_errs = {}
    for m_cov, blks in kept_cov_spec.items():
        Si4 = np.linalg.inv(actual_Cinvs[m_cov]).reshape((env.M_O, env.Nbs, env.M_O, env.Nbs), order="F")
        kept_blk_own_errs[m_cov] = (
            float(
                max(
                    float(np.linalg.norm(Si4[sl[a], :, sl[b], :] - S4[sl[a], :, sl[b], :])) / ref_blk_norms[(a, b)]
                    for (a, b) in blks
                )
            )
            if min_ref_blk_norm > 0.0
            else float("inf")
        )
        if m_cov in zero_cov_spec:
            zero_blk_own_errs[m_cov] = (
                float(
                    max(
                        float(np.linalg.norm(Si4[sl[a], :, sl[b], :])) / ref_blk_norms[(a, b)]
                        for (a, b) in zero_cov_spec[m_cov]
                    )
                )
                if min_ref_blk_norm > 0.0
                else float("inf")
            )
    max_inv_cov_kept_blk_own_rel_err = float(max(kept_blk_own_errs.values()))
    max_inv_cov_zero_blk_own_rel_err = float(max(zero_blk_own_errs.values()))

    def _combined_zero_prec_rel_err(m_k, zero_blk_pairs):
        Ci = actual_Cinvs[m_k]
        n_ci = float(np.linalg.norm(Ci))
        if n_ci <= 0.0:
            return float("inf")
        c4 = Ci.reshape((env.M_O, env.Nbs, env.M_O, env.Nbs), order="F")
        sq_sum = sum(float(np.linalg.norm(c4[sl[a], :, sl[b], :])) ** 2 for (a, b) in zero_blk_pairs)
        return float(math.sqrt(sq_sum) / n_ci)

    min_cinv_norm = float(min(np.linalg.norm(actual_Cinvs[m_k]) for m_k in expected_map))
    prec_zero_errs = {
        "chordal_13": _combined_zero_prec_rel_err("cut_chordal_prec0", [("1", "3"), ("3", "1")]),
        "rguard2_all_r": _combined_zero_prec_rel_err("cut_2blk_rguard", [("1", "3"), ("3", "1"), ("2", "3"), ("3", "2")]),
        "head2_all_h": _combined_zero_prec_rel_err("cut_2blk_head", [("1", "2"), ("2", "1"), ("1", "3"), ("3", "1")]),
        "win3_all_off": _combined_zero_prec_rel_err(
            "cut_3blk_windows", [("1", "2"), ("2", "1"), ("1", "3"), ("3", "1"), ("2", "3"), ("3", "2")]
        ),
    }

    Y_dummy = (rng.standard_normal((env.N, env.Nbs)) + 1j * rng.standard_normal((env.N, env.Nbs))) * 0.1
    s2_d = env.estimate_common_blind_s2(Y_dummy[env.obs_idx, :])
    H_base, _ = env.run_arm(Y_dummy, "full", s2_common=s2_d)
    H_sub, _ = env.run_same_pulse_arm(Y_dummy, "full", s2_common=s2_d)
    min_h_base_norm = float(min(np.linalg.norm(H_base[u]) for u in range(env.K)))
    arm_parity_err = (
        float(max(np.linalg.norm(H_base[u] - H_sub[u]) / np.linalg.norm(H_base[u]) for u in range(env.K)))
        if min_h_base_norm > 0.0
        else float("inf")
    )

    return {
        "seed_disjointness_exact_ok": seed_ok,
        "windows_exact_ok": windows_exact_ok,
        "raw_zero13_synth_nonspd": raw_zero13_synth_nonspd,
        "raw_zero13_synth_min_eig": raw_zero13_min_eig,
        "min_ref_blk_norm": min_ref_blk_norm,
        "min_cinv_norm": min_cinv_norm,
        "min_h_base_norm": min_h_base_norm,
        "max_inv_resid": float(max(inv_resids.values())),
        "chordal_target_keep_exact_err": chordal_target_keep_exact_err,
        "max_inv_cov_kept_blk_own_rel_err": max_inv_cov_kept_blk_own_rel_err,
        "max_inv_cov_zero_blk_own_rel_err": max_inv_cov_zero_blk_own_rel_err,
        "per_mode_kept_blk_own_rel_err": kept_blk_own_errs,
        "per_mode_zero_blk_own_rel_err": zero_blk_own_errs,
        "max_linv_consist_err": float(max(linv_consist.values())),
        "min_prec_eig": float(min(min_eigs.values())),
        "max_prec_zero_rel_err": float(max(prec_zero_errs.values())),
        "full_arm_parity_rel_err": arm_parity_err,
        "per_mode_inv_resids": inv_resids,
        "per_mode_prec_zero_rel_err": prec_zero_errs,
    }


_CUT_ENV_CACHE = {}

_PRIMARY_ARM_COV_MAP = {
    "full": "full",
    "cut_chordal_prec0": "cut_chordal_prec0",
    "cut_2blk_rguard": "cut_2blk_rguard",
    "cut_2blk_head": "cut_2blk_head",
    "cut_3blk_windows": "cut_3blk_windows",
    "spatial_only": "no_cross_daft",
    "a_only": "none",
}


def run_cut_trial(task_tuple):
    scen_key, snr_db, tr_id = task_tuple
    if scen_key not in _CUT_ENV_CACHE:
        if scen_key == "S1_K3_Nbs5_NF16":
            _CUT_ENV_CACHE[scen_key] = CutScenarioEnv(128, 3, 5, 3, [0], 16.0, 0.25)
        elif scen_key == "S2_K4_Nbs6_NF15":
            _CUT_ENV_CACHE[scen_key] = CutScenarioEnv(128, 4, 6, 3, [0, 1], 15.0, 0.25)
        else:
            raise ValueError(scen_key)
    env = _CUT_ENV_CACHE[scen_key]
    env.cut_diag_stats = {"literal_calls": 0, "literal_floored": 0, "literal_head_rel_dist": []}

    seed_val = _R12_SEED_BASE[scen_key] + tr_id * 17 + int(round(snr_db * 10))
    rng = np.random.default_rng(seed_val)
    sigma2_true = 10.0 ** (-snr_db / 10.0)
    nd = len(env.data_bins)

    user_paths = {u: [] for u in range(env.K)}
    H_true = []
    X_prev = np.zeros((env.K, env.N), dtype=complex)
    X_curr = np.zeros((env.K, env.N), dtype=complex)
    X_next = np.zeros((env.K, env.N), dtype=complex)
    X_bits = rng.integers(0, 16, size=(env.K, nd))
    for u in range(env.K):
        bp, bn = rng.integers(0, 16, nd), rng.integers(0, 16, nd)
        for Xb, ba in [(X_prev, bp), (X_curr, X_bits[u]), (X_next, bn)]:
            Xb[u, env.pilots[u]] = env.pilot_amp
            Xb[u, env.data_bins] = env.qam16[ba]
        amp_u = np.sqrt(env.user_pow[u])
        taus = np.sort(rng.uniform(0.12, env.l_max - 0.05, size=env.P))
        nus = rng.uniform(-1.3, 1.3, size=env.P)
        ths = rng.uniform(-0.85, 0.85, size=env.P)
        gains = amp_u * (rng.standard_normal(env.P) + 1j * rng.standard_normal(env.P)) / np.sqrt(2.0 * env.P)
        for p_i in range(env.P):
            user_paths[u].append((float(taus[p_i]), float(nus[p_i]), float(ths[p_i]), complex(gains[p_i])))
        H_true.append(env.true_curr_block_H_from_3block(user_paths[u]))

    noise_mat = np.sqrt(sigma2_true / 2.0) * (rng.standard_normal((env.N, env.Nbs)) + 1j * rng.standard_normal((env.N, env.Nbs)))
    Y_rx = env.simulate_3block_rx(X_prev, X_curr, X_next, user_paths, noise_mat)

    s2_common = env.estimate_common_blind_s2(Y_rx[env.obs_idx, :], d_bins=env.data_bins)
    s2_err_db = float(10.0 * np.log10(s2_common / sigma2_true))

    out_err, out_nmse = {}, {}
    full_final_raw_zero13_min_eig = 0.0
    for ak, cmode in _PRIMARY_ARM_COV_MAP.items():
        if ak == "full":
            H_h, s2_e, paths_full = env.run_same_pulse_arm(Y_rx, cmode, s2_common=s2_common, return_paths=True)
            full_final_raw_zero13_min_eig = env.check_raw_zero13_min_eig(paths_full, s2_common, use_pulse=True, d_bins=env.data_bins)
        else:
            H_h, s2_e = env.run_same_pulse_arm(Y_rx, cmode, s2_common=s2_common)
        xh = env.detect_unb_lmmse(Y_rx, H_h, s2_e)
        eb, nl = 0, []
        for u in env.weak_users:
            nl.append(
                float(
                    np.linalg.norm(H_h[u][:, :, env.data_bins] - H_true[u][:, :, env.data_bins]) ** 2
                    / np.linalg.norm(H_true[u][:, :, env.data_bins]) ** 2
                )
            )
            di = np.argmin(np.abs(xh[u][:, None] - env.qam16[None, :]), axis=1)
            eb += int(np.sum(env.qam_bits[di] != env.qam_bits[X_bits[u]]))
        out_err[ak] = eb
        out_nmse[ak] = float(np.mean(nl))

    # Isolated descriptive composite diagnostic (cannot abort or alter primary verdicts):
    lit_ok, lit_err, lit_nmse = True, 0, float("nan")
    try:
        H_lit, s2_lit = env.run_same_pulse_arm(Y_rx, "cut_literal_psd", s2_common=s2_common)
        xh_lit = env.detect_unb_lmmse(Y_rx, H_lit, s2_lit)
        eb_l, nl_l = 0, []
        for u in env.weak_users:
            nl_l.append(
                float(
                    np.linalg.norm(H_lit[u][:, :, env.data_bins] - H_true[u][:, :, env.data_bins]) ** 2
                    / np.linalg.norm(H_true[u][:, :, env.data_bins]) ** 2
                )
            )
            di = np.argmin(np.abs(xh_lit[u][:, None] - env.qam16[None, :]), axis=1)
            eb_l += int(np.sum(env.qam_bits[di] != env.qam_bits[X_bits[u]]))
        lit_err, lit_nmse = eb_l, float(np.mean(nl_l))
    except Exception:
        lit_ok = False

    xh_or = env.detect_unb_lmmse(Y_rx, H_true, sigma2_true)
    eb_or = 0
    for u in env.weak_users:
        di = np.argmin(np.abs(xh_or[u][:, None] - env.qam16[None, :]), axis=1)
        eb_or += int(np.sum(env.qam_bits[di] != env.qam_bits[X_bits[u]]))
    out_err["oracle"] = eb_or

    return {
        "scen": scen_key,
        "snr": snr_db,
        "err": out_err,
        "nmse": out_nmse,
        "bits": len(env.weak_users) * nd * 4,
        "s2_err_db": s2_err_db,
        "full_raw_zero13_min_eig": full_final_raw_zero13_min_eig,
        "full_raw_zero13_nonspd": int(full_final_raw_zero13_min_eig <= 0.0),
        "lit_ok": lit_ok,
        "lit_err": lit_err,
        "lit_nmse": lit_nmse,
        "lit_calls": env.cut_diag_stats["literal_calls"],
        "lit_floored": env.cut_diag_stats["literal_floored"],
        "lit_head_dist_mean": float(np.mean(env.cut_diag_stats["literal_head_rel_dist"])) if env.cut_diag_stats["literal_head_rel_dist"] else 0.0,
    }


def summarize_scenario(d, seed_offset=0):
    ef = d["err_frames"]
    nm_db = {ak: 10.0 * np.log10(np.maximum(nv, 1e-15)) for ak, nv in d["nmse"].items()}

    ratios = {}
    nmse_diffs = {}
    primary_arms = [
        "cut_chordal_prec0",
        "cut_2blk_rguard",
        "cut_2blk_head",
        "cut_3blk_windows",
        "spatial_only",
        "a_only",
    ]
    for i, ak in enumerate(primary_arms):
        ratios[f"{ak}_over_full_BER"] = paired_ber_ratio_ci95_strict(ef[ak], ef["full"], seed=20261200 + seed_offset + i)
        nmse_diffs[f"{ak}_minus_full_NMSE_dB"] = base_g01.paired_diff_t_ci95(nm_db[ak] - nm_db["full"])

    ratios["spatial_only_over_cut_3blk_BER"] = paired_ber_ratio_ci95_strict(
        ef["spatial_only"], ef["cut_3blk_windows"], seed=20261220 + seed_offset
    )
    nmse_diffs["spatial_only_minus_cut_3blk_NMSE_dB"] = base_g01.paired_diff_t_ci95(
        nm_db["spatial_only"] - nm_db["cut_3blk_windows"]
    )

    if all(d["lit_ok"]):
        lit_nm_db = 10.0 * np.log10(np.maximum(d["lit_nmse"], 1e-15))
        desc_lit = {
            "cut_literal_psd_over_full_BER": paired_ber_ratio_ci95_strict(d["lit_err"], ef["full"], seed=20261230 + seed_offset),
            "cut_literal_psd_minus_full_NMSE_dB": base_g01.paired_diff_t_ci95(lit_nm_db - nm_db["full"]),
            "floored_call_rate": float(sum(d["lit_floored"]) / max(sum(d["lit_calls"]), 1)),
            "intra_head_rel_distortion_mean": float(np.mean(d["lit_head_dist"])),
        }
    else:
        desc_lit = {"diagnostic_failed_frames": int(sum(1 for ok in d["lit_ok"] if not ok))}

    return {
        "n_frames": d["n_frames"],
        "total_weak_bits": d["bits"],
        "BER": {ak: ev / d["bits"] for ak, ev in d["err"].items()},
        "NMSE_agg_dB": {ak: float(10.0 * np.log10(np.mean(nv))) for ak, nv in d["nmse"].items()},
        "NMSE_mean_frame_dB": {ak: float(np.mean(v)) for ak, v in nm_db.items()},
        "mean_blind_s2_err_dB": float(np.mean(d["s2_db"])),
        "raw_zero13_nonspd_frame_rate": float(sum(d["full_raw_nonspd"]) / max(d["n_frames"], 1)),
        "raw_zero13_min_eig_worst": float(min(d["full_raw_min_eig"])),
        "paired_ber_ratios_ci95": ratios,
        "paired_nmse_diffs_dB_ci95": nmse_diffs,
        "descriptive_composite_literal_psd": desc_lit,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="diag_g_r12_g01_cut.json")
    args = ap.parse_args()

    t_start = time.time()
    rl1, inv, rl1_exc = {}, {}, None
    try:
        rl1 = base_g01.verify_redline1_yin24()
        inv = verify_cut_operator_invariants()
        print("[Red-Line 1 & Cut Invariants]", json.dumps({"rl1": rl1, "inv": {k: v for k, v in inv.items() if not isinstance(v, dict)}}), flush=True)
        v_redline1 = (
            bool(inv.get("seed_disjointness_exact_ok", False))
            and bool(inv.get("windows_exact_ok", False))
            and bool(inv.get("raw_zero13_synth_nonspd", False))
            and (rl1["noiseless_integer_rel_err"] < 1e-12)
            and (rl1["ct_3block_kernel_match_err"] < 1e-12)
            and (rl1["yin24_table2_2x2_ber_perfect"] > 0.0)
            and (rl1["yin24_table2_2x2_ber_epa_dr"] <= 1.60 * rl1["yin24_table2_2x2_ber_perfect"])
            and (rl1["yin24_table2_2x2_ber_epa_dr"] < 0.025)
            and (inv["max_inv_resid"] < 1e-10)
            and (inv["min_ref_blk_norm"] > 0.0)
            and (inv["min_cinv_norm"] > 0.0)
            and (inv["min_h_base_norm"] > 0.0)
            and (inv["chordal_target_keep_exact_err"] == 0.0)
            and (inv["max_inv_cov_kept_blk_own_rel_err"] < 1e-10)
            and (inv["max_inv_cov_zero_blk_own_rel_err"] < 1e-12)
            and (inv["max_linv_consist_err"] < 1e-12)
            and (inv["min_prec_eig"] > 0.0)
            and (inv["max_prec_zero_rel_err"] < 1e-12)
            and (inv["full_arm_parity_rel_err"] < 1e-12)
        )
    except Exception as exc:
        rl1_exc = repr(exc)
        v_redline1 = False

    if not v_redline1:
        fail_s = {
            "_argv": list(sys.argv),
            "card_id": "I-20261125-g01",
            "smoke": bool(args.smoke),
            "redline1": rl1,
            "cut_invariants": inv,
            "redline1_exception": rl1_exc,
            "card_claim_routing": _inconclusive_card_routing(),
            "verdicts": {
                "PASS_REDLINE1": False,
                "PASS_CI_PRECISION_25PCT": False,
                "PASS_VALID_FORMAL": False,
                "PASS_PRIMARY": False,
            },
        }
        with open(args.out, "w") as f:
            json.dump(_json_safe(fail_s), f, indent=2, allow_nan=False)
        raise RuntimeError(f"Red-Line 1 or cut invariant check failed: {rl1} | {inv} | exc={rl1_exc}")

    n_s1 = 2 if args.smoke else FORMAL_N_S1
    n_s2 = 2 if args.smoke else FORMAL_N_S2
    tr_s1 = [-100 - k for k in range(n_s1)] if args.smoke else list(range(FORMAL_N_S1))
    tr_s2 = [-100 - k for k in range(n_s2)] if args.smoke else list(range(FORMAL_N_S2))
    tasks = [("S1_K3_Nbs5_NF16", 30.0, tr) for tr in tr_s1] + [
        ("S2_K4_Nbs6_NF15", 30.0, tr) for tr in tr_s2
    ]

    w_cnt = max(1, min(args.workers, 8))
    if w_cnt <= 1:
        results = [run_cut_trial(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            results = list(ex.map(run_cut_trial, tasks))

    agg = {}
    for r in results:
        key = f"{r['scen']}_SNR{int(r['snr'])}"
        if key not in agg:
            agg[key] = {
                "bits": 0,
                "n_frames": 0,
                "err": {},
                "err_frames": {},
                "nmse": {},
                "s2_db": [],
                "full_raw_nonspd": [],
                "full_raw_min_eig": [],
                "lit_ok": [],
                "lit_err": [],
                "lit_nmse": [],
                "lit_calls": [],
                "lit_floored": [],
                "lit_head_dist": [],
            }
        d = agg[key]
        d["bits"] += r["bits"]
        d["n_frames"] += 1
        d["s2_db"].append(r["s2_err_db"])
        d["full_raw_nonspd"].append(r["full_raw_zero13_nonspd"])
        d["full_raw_min_eig"].append(r["full_raw_zero13_min_eig"])
        d["lit_ok"].append(r["lit_ok"])
        d["lit_err"].append(r["lit_err"])
        d["lit_nmse"].append(r["lit_nmse"])
        d["lit_calls"].append(r["lit_calls"])
        d["lit_floored"].append(r["lit_floored"])
        d["lit_head_dist"].append(r["lit_head_dist_mean"])
        for ak, ev in r["err"].items():
            d["err"][ak] = d["err"].get(ak, 0) + ev
            d["err_frames"].setdefault(ak, []).append(ev)
        for ak, nv in r["nmse"].items():
            d["nmse"].setdefault(ak, []).append(nv)

    s1_sum = summarize_scenario(agg["S1_K3_Nbs5_NF16_SNR30"], seed_offset=0)
    s2_sum = summarize_scenario(agg["S2_K4_Nbs6_NF15_SNR30"], seed_offset=50)
    r_s1 = s1_sum["paired_ber_ratios_ci95"]

    cap_3x = cap_ratio_lhw(3.0)
    cap_5x = cap_ratio_lhw(5.0)
    three_x_keys = [
        "cut_chordal_prec0_over_full_BER",
        "cut_2blk_rguard_over_full_BER",
        "cut_2blk_head_over_full_BER",
        "cut_3blk_windows_over_full_BER",
        "spatial_only_over_full_BER",
        "spatial_only_over_cut_3blk_BER",
    ]
    all_keys = three_x_keys + ["a_only_over_full_BER"]
    any_obs_zero_undecidable = any(r_s1[k]["observed_zero_undecidable"] for k in all_keys)
    max_3x_lhw = float(max(r_s1[k]["log_halfwidth"] for k in three_x_keys))
    a_only_lhw = float(r_s1["a_only_over_full_BER"]["log_halfwidth"])

    v_ci_prec = bool(
        (not args.smoke)
        and (s1_sum["n_frames"] == FORMAL_N_S1)
        and (s2_sum["n_frames"] == FORMAL_N_S2)
        and (not any_obs_zero_undecidable)
        and np.isfinite(max_3x_lhw)
        and np.isfinite(a_only_lhw)
        and (max_3x_lhw <= cap_3x)
        and (a_only_lhw <= cap_5x)
    )
    v_valid_formal = bool(v_redline1 and v_ci_prec)

    three_state_s1 = {k: classify_ci_vs_bar(r_s1[k], 3.0) for k in three_x_keys}
    three_state_s1["a_only_over_full_BER"] = classify_ci_vs_bar(r_s1["a_only_over_full_BER"], 5.0)

    v_chordal = bool(three_state_s1["cut_chordal_prec0_over_full_BER"] == "CONFIRMED_GE_BAR")
    v_rguard2 = bool(three_state_s1["cut_2blk_rguard_over_full_BER"] == "CONFIRMED_GE_BAR")
    v_head2 = bool(three_state_s1["cut_2blk_head_over_full_BER"] == "CONFIRMED_GE_BAR")
    v_win3 = bool(three_state_s1["cut_3blk_windows_over_full_BER"] == "CONFIRMED_GE_BAR")
    v_intra_vs_spat = bool(three_state_s1["spatial_only_over_cut_3blk_BER"] == "CONFIRMED_GE_BAR")
    v_full_vs_spat = bool(three_state_s1["spatial_only_over_full_BER"] == "CONFIRMED_GE_BAR")
    v_full_vs_a = bool(three_state_s1["a_only_over_full_BER"] == "CONFIRMED_GE_BAR")

    v_cross_bin_gain = bool(v_full_vs_a and v_full_vs_spat and v_intra_vs_spat)
    pass_primary = bool(v_valid_formal and v_cross_bin_gain)

    if not v_valid_formal:
        card_routing = _inconclusive_card_routing()
    else:
        def _map_op_claim(st, tag):
            if st == "CONFIRMED_GE_BAR":
                return f"SUSTAIN_{tag}_GE_3X"
            if st == "REFUTED_LT_BAR":
                return f"WITHDRAW_{tag}_REFUTED_LT_3X"
            return f"WITHDRAW_{tag}_UNPROVEN_STRADDLES_3X"

        ch_claim = _map_op_claim(three_state_s1["cut_chordal_prec0_over_full_BER"], "DIRECT_PREC13")
        rg_claim = _map_op_claim(three_state_s1["cut_2blk_rguard_over_full_BER"], "RGUARD_2WIN_COV")
        w3_claim = _map_op_claim(three_state_s1["cut_3blk_windows_over_full_BER"], "INTERWINDOW_3WIN")

        wraparound_action = (
            "WITHDRAW_WRAPAROUND_NARRATIVE_KEEP_VERIFIED_OPERATORS_ONLY"
            if ((not v_chordal) and (not v_rguard2))
            else "REPORT_ONLY_CONFIRMED_SPECIFIC_OPERATOR"
        )
        intra_map = {
            "CONFIRMED_GE_BAR": "CONFIRMED_GE_3X",
            "REFUTED_LT_BAR": "REFUTED_LT_3X",
            "UNPROVEN_STRADDLES_BAR": "UNPROVEN_STRADDLES_3X",
            "UNDECIDABLE_ZERO_COUNTS": "UNDECIDABLE_ZERO_COUNTS",
        }
        card_routing = {
            "status": "VALID_FORMAL_DECISION",
            "literal_3win_single_cov13_note": (
                "INFEASIBLE_NON_SPD_ON_3WIN_GLS" if (s1_sum["raw_zero13_nonspd_frame_rate"] > 0.0) else "FEASIBLE_ON_FORMAL"
            ),
            "direct_gls_precision_13_claim": ch_claim,
            "right_guard_2win_cov_conditioning_claim": rg_claim,
            "all_interwindow_3win_cov_claim": w3_claim,
            "card_wraparound_narrative_action": wraparound_action,
            "intra_window_single_factor_3x": intra_map[three_state_s1["spatial_only_over_cut_3blk_BER"]],
            "same_pulse_whole_receiver_checks": {
                "spatial_only_over_full_3x": three_state_s1["spatial_only_over_full_BER"],
                "a_only_over_full_5x": three_state_s1["a_only_over_full_BER"],
                "PASS_SAME_PULSE_CROSS_BIN_GAIN": v_cross_bin_gain,
            },
            "r11_whole_receiver_pass_primary_preserved": True,
        }

    summary = {
        "_argv": list(sys.argv),
        "_config": {
            "smoke": bool(args.smoke),
            "workers": w_cnt,
            "formal_n_s1": FORMAL_N_S1,
            "formal_n_s2": FORMAL_N_S2,
            "actual_n_s1": n_s1,
            "actual_n_s2": n_s2,
            "seed_bases": _R12_SEED_BASE,
            "s1_windows": {"W_head": [0, 16], "W_mid": [17, 46], "W_rguard": [47, 58]},
            "s2_windows": {"W_head": [0, 31], "W_mid": [32, 61], "W_rguard": [62, 73]},
            "cap_log_halfwidth_3x": cap_3x,
            "cap_log_halfwidth_5x": cap_5x,
        },
        "card_id": "I-20261125-g01",
        "run_type": "step8_revised_spd_cross_vs_intra_window_disconnection",
        "group": "[放宽TWC]",
        "track": "[轨A-纯通信]",
        "smoke": bool(args.smoke),
        "wall_time_s": float(time.time() - t_start),
        "redline1": rl1,
        "cut_operator_invariants": inv,
        "ci_precision_check_S1": {
            "any_observed_zero_undecidable": any_obs_zero_undecidable,
            "max_3x_gates_log_halfwidth": max_3x_lhw,
            "cap_3x_log_halfwidth": cap_3x,
            "a_only_5x_log_halfwidth": a_only_lhw,
            "cap_5x_log_halfwidth": cap_5x,
        },
        "three_state_ci_classifications_S1": three_state_s1,
        "S1_primary_K3_Nbs5_NF16_SNR30": s1_sum,
        "SCOPE_READOUTS": {
            "S2_K4_Nbs6_NF15_SNR30": s2_sum,
        },
        "card_claim_routing": card_routing,
        "verdicts": {
            "PASS_REDLINE1": bool(v_redline1),
            "PASS_CI_PRECISION_25PCT": v_ci_prec,
            "PASS_VALID_FORMAL": v_valid_formal,
            "VERDICT_CHORDAL_DIRECT_PREC_3X": v_chordal,
            "VERDICT_RGUARD_2BLK_COV_3X": v_rguard2,
            "VERDICT_HEAD_2BLK_COV_3X": v_head2,
            "VERDICT_ALL_INTERWINDOW_3BLK_3X": v_win3,
            "VERDICT_INTRA_WINDOW_OVER_SPATIAL_3X": v_intra_vs_spat,
            "VERDICT_FULL_OVER_SPATIAL_3X": v_full_vs_spat,
            "VERDICT_FULL_OVER_A_ONLY_5X": v_full_vs_a,
            "PASS_SAME_PULSE_CROSS_BIN_GAIN": v_cross_bin_gain,
            "PASS_PRIMARY": pass_primary,
        },
    }
    with open(args.out, "w") as f:
        json.dump(_json_safe(summary), f, indent=2, allow_nan=False)
    print(json.dumps(summary["verdicts"], indent=2), flush=True)
    print("Card claim routing:", json.dumps(summary["card_claim_routing"]), flush=True)
    print("Saved diagnostic summary to", args.out, "in", round(summary["wall_time_s"], 2), "s", flush=True)


if __name__ == "__main__":
    main()
