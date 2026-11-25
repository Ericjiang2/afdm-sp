#!/usr/bin/env python3
"""
Formal L2 Verification Script for Card I-20261125-h02 ([高要求] [轨B-ISAC], Round 11):
Path-Decoupled Spatial Precoding & Co-Located Beam-Matched Superposed ISAC Pilot
for Multi-Block Coherent-CPI TDD MIMO-AFDM ISAC under Channel Aging.

Pre-registration: ideas/l2/PREDICTIONS_h_r11_h02.md
Enforces:
  - Line-1 sys.executable print & AFDM conda env lock on deinlab
  - Single-thread BLAS/OMP per worker, multiprocessing Pool(workers <= 8)
  - All Sol Step-6 REVISE + Pre-L2 Audit 5 items + Red Lines 1-5 (unseen seeds 200000+ & 300000+)
"""
import sys
print(sys.executable, flush=True)

import os
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_k] = "1"

import argparse
import json
import time
from multiprocessing import Pool
import numpy as np


N, Ncpp, Q, Nt, Nr_rad, K, Pk, M_sub = 64, 12, 16, 12, 6, 3, 3, 5
Tsym = (N + Ncpp) / float(N)  # 1.1875
c1_af, c2_af = 4.0 / (2.0 * N), 1.0 / (2.0 * N)
pts16 = np.array([x + 1j * y for x in (-3, -1, 1, 3) for y in (-3, -1, 1, 3)]) / np.sqrt(10.0)


def steering_ula(M, deg):
    return np.exp(-1j * np.pi * np.arange(M) * np.sin(np.deg2rad(deg)))


def make_daft(N_v, c1_v, c2_v):
    n = np.arange(N_v)
    F = np.fft.fft(np.eye(N_v), norm="ortho")
    return (np.exp(-1j * 2 * np.pi * c2_v * (n ** 2))[:, None] * F) * np.exp(-1j * 2 * np.pi * c1_v * (n ** 2))[None, :]


A_af = make_daft(N, c1_af, c2_af)
F_of = make_daft(N, 0.0, 0.0)


def make_E_op(U_mat, c1_v, ell, nu):
    g = np.ones(N, dtype=complex)
    if ell > 0:
        ix = np.arange(ell)
        g[ix] = np.exp(-1j * 2 * np.pi * c1_v * (N ** 2 - 2 * N * (ell - ix)))
    phase_d = np.exp(1j * 2 * np.pi * nu * np.arange(N) / float(N)) * g
    return (U_mat * phase_d[None, :]) @ np.roll(U_mat.conj().T, ell, axis=0)


def solve_exact_expected_beta(S_pil, S_ref_0, pay_frob2_sum, P_target):
    """
    Exact expected transmit power normalization:
      E_{d_pay}[ || S_pil + beta * (S_ref_0 + sum_{k,m>=1} d_{k,m} M_{k,m}) ||_F^2 ] == P_target
    Since d_{k,m} (m>=1) are i.i.d. zero-mean unit-variance 16-QAM symbols:
      E[||S_tot||_F^2] = ||S_pil||_F^2 + 2*beta*Re<S_pil, S_ref_0> + beta^2 * (||S_ref_0||_F^2 + pay_frob2_sum).
    """
    e_pil = float(np.sum(np.abs(S_pil) ** 2))
    a_coef = float(np.sum(np.abs(S_ref_0) ** 2)) + float(pay_frob2_sum)
    b_re = float(np.real(np.vdot(S_pil, S_ref_0)))
    c_coef = e_pil - float(P_target)
    if a_coef <= 1e-18:
        return 0.0
    disc = max(b_re * b_re - a_coef * c_coef, 0.0)
    return float(max((-b_re + np.sqrt(disc)) / a_coef, 0.0))


def verify_red_line_1_invariants():
    """Red Line 1a (exact time-domain CPP operator < 1e-13) + Red Line 1b (Liu & Schober 2026 Sec. IV-B/V WMMSE-MM Fig.1a point)."""
    rng_op = np.random.default_rng(932)
    x0 = rng_op.standard_normal(N) + 1j * rng_op.standard_normal(N)
    max_op_err = 0.0
    for U, c in ((F_of, 0.0), (A_af, c1_af)):
        for ell in (0, 1, 2, 5):
            for nu in (-0.85, 0.0, 0.63):
                s = U.conj().T @ x0
                pad = np.array([s[i - ell] if i >= ell else np.exp(-2j * np.pi * c * ((i - ell + N) ** 2 - (i - ell) ** 2)) * s[i - ell + N] for i in range(N)])
                y = U @ (np.exp(2j * np.pi * nu * np.arange(N) / N) * pad)
                rel = float(np.linalg.norm(y - make_E_op(U, c, ell, nu) @ x0) / np.linalg.norm(y))
                max_op_err = max(max_op_err, rel)
    assert max_op_err < 1e-13, f"CPP operator mismatch: {max_op_err}"

    # Faithful reproduction of Rang Liu, Ming Li, Swindlehurst, Franchi & Schober (arXiv:2607.05119) Sec. IV-B & V:
    Nt_l, N_l, Q_l, K_l, Pk_l = 6, 64, 8, 3, 3
    Ts_l = (N_l + 10.0) / N_l
    Pmax_l, sig2_l = float(N_l), 10.0 ** (-15.0 / 10.0)
    Gamma_s = 0.25 * Pmax_l * Nt_l
    nu_m = 0.1
    c1_l = (2.0 * nu_m + 1.0) / (2.0 * N_l)
    U_l = make_daft(N_l, c1_l, 1.0 / (2.0 * N_l))
    Hk_q = [[np.zeros((N_l, N_l * Nt_l), dtype=complex) for _ in range(Q_l)] for _ in range(K_l)]
    rng_ch = np.random.default_rng(260705)
    degs_u = [-45.0, -10.0, 20.0]
    for k in range(K_l):
        als = (rng_ch.standard_normal(Pk_l) + 1j * rng_ch.standard_normal(Pk_l)) / np.sqrt(2.0 * Pk_l)
        els = rng_ch.choice(9, size=Pk_l, replace=False)
        nus = rng_ch.uniform(-nu_m, nu_m, size=Pk_l)
        at_u = steering_ula(Nt_l, degs_u[k])
        for p in range(Pk_l):
            E_p = make_E_op(U_l, c1_l, int(els[p]), float(nus[p]))
            H_base = np.kron(E_p, at_u.conj()[None, :])
            for q in range(Q_l):
                Hk_q[k][q] += als[p] * np.exp(1j * 2 * np.pi * nus[p] * q * Ts_l) * H_base

    at_tar_l = steering_ula(Nt_l, 40.0)
    ws_bin = np.tile((at_tar_l / np.sqrt(Nt_l))[None, :], (N_l, 1)) * np.sqrt(0.25 * Pmax_l / N_l)
    p_comm_b = 0.75 * Pmax_l
    W_bin = [np.zeros((N_l, Nt_l), dtype=complex) for _ in range(K_l)]
    for k in range(K_l):
        for m in range(N_l):
            W_bin[k][m] = Hk_q[k][0][m, m * Nt_l:(m + 1) * Nt_l].conj()
    nrm_c = np.sqrt(sum(float(np.sum(np.abs(W_bin[k]) ** 2)) for k in range(K_l)))
    W_bin = [W_bin[k] * np.sqrt(p_comm_b) / max(nrm_c, 1e-12) for k in range(K_l)]

    def _expand_blk(Wb):
        M = np.zeros((N_l * Nt_l, N_l), dtype=complex)
        for m in range(N_l):
            M[m * Nt_l:(m + 1) * Nt_l, m] = Wb[m]
        return M

    W_s = _expand_blk(ws_bin)
    sr_hist = []
    for it in range(6):
        W_c = [_expand_blk(W_bin[k]) for k in range(K_l)]
        Tw_diag = np.zeros((N_l, Nt_l, Nt_l), dtype=complex)
        Bk_diag = [np.zeros((N_l, Nt_l), dtype=complex) for _ in range(K_l)]
        sr_q = 0.0
        for q in range(Q_l):
            for k in range(K_l):
                HWs_k = [Hk_q[k][q] @ W_c[j] for j in range(K_l)]
                Hs_k = Hk_q[k][q] @ W_s
                Ck = sig2_l * np.eye(N_l) + Hs_k @ Hs_k.conj().T + sum(HWs_k[j] @ HWs_k[j].conj().T for j in range(K_l))
                Uk = np.linalg.solve(Ck, HWs_k[k])
                Ek = np.eye(N_l) - HWs_k[k].conj().T @ Uk
                Ek = 0.5 * (Ek + Ek.conj().T) + 1e-9 * np.eye(N_l)
                s_e, _ = np.linalg.eigh(Ek)
                sr_q += float(np.sum(-np.log2(np.maximum(s_e, 1e-9)))) / float(N_l * Q_l)
                Mk = np.linalg.inv(Ek)
                HUMU = Uk @ Mk @ Uk.conj().T
                Tw_full_k = (1.0 / (Q_l * np.log(2.0))) * (Hk_q[k][q].conj().T @ HUMU @ Hk_q[k][q])
                Bk_full_k = (1.0 / (Q_l * np.log(2.0))) * (Hk_q[k][q].conj().T @ (Uk @ Mk))
                for m in range(N_l):
                    sl_m = slice(m * Nt_l, (m + 1) * Nt_l)
                    Tw_diag[m] += Tw_full_k[sl_m, sl_m]
                    Bk_diag[k][m] += Bk_full_k[sl_m, m]
        sr_hist.append(sr_q)
        if it == 5:
            break
        evs_all, Us_all, B_proj_all = [], [], []
        for m in range(N_l):
            Tm = 0.5 * (Tw_diag[m] + Tw_diag[m].conj().T)
            ev_m, U_m_e = np.linalg.eigh(Tm)
            evs_all.append(np.maximum(ev_m, 0.0))
            Us_all.append(U_m_e)
            Bm = np.column_stack([Bk_diag[k][m] for k in range(K_l)])
            B_proj_all.append(U_m_e.conj().T @ Bm)
        evs_cat = np.concatenate(evs_all)
        Bp_cat = np.vstack(B_proj_all)
        row_pow = np.sum(np.abs(Bp_cat) ** 2, axis=1)
        lo, hi = 1e-7, 1e4
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if float(np.sum(row_pow / ((evs_cat + mid) ** 2))) > p_comm_b:
                lo = mid
            else:
                hi = mid
        for m in range(N_l):
            W_m_all = Us_all[m] @ ((1.0 / (evs_all[m] + hi))[:, None] * B_proj_all[m])
            for k in range(K_l):
                W_bin[k][m] = W_m_all[:, k]

    W_c_fin = [_expand_blk(W_bin[k]) for k in range(K_l)]
    A_tar_blk = np.kron(np.eye(N_l), at_tar_l.conj()[None, :])
    psen_val = float(np.sum(np.abs(A_tar_blk @ W_s) ** 2)) + sum(float(np.sum(np.abs(A_tar_blk @ W_c_fin[k]) ** 2)) for k in range(K_l))
    assert psen_val >= Gamma_s - 1e-6
    assert all(sr_hist[i + 1] >= sr_hist[i] - 1e-6 for i in range(5)), f"Non-monotone WMMSE: {sr_hist}"
    assert 10.0 <= sr_hist[-1] <= 13.0, f"Unexpected Fig.1a sum-rate: {sr_hist[-1]}"
    return {"max_cpp_operator_rel_err": max_op_err, "liu26_fig1a_wmmse_sum_rate_trajectory_bps_hz": [round(x, 4) for x in sr_hist]}


# Equal 39/64 net payload (156 bits/user/block) + 1 in-band scalar gain reference symbol at Dt[0] + 24 pilot/guard bins!
N_act = 40
N_payload = 39
m_p_af = 10
obs_af = np.arange(0, 13)
D_af = np.arange(22, 62)

# DDAM guard geometry: D_ddam=[19..58] under ALL TX/RX shifts 4*(el_tx - el_rx) in [-8..+8] lands in [11..63] U [0..2],
# leaving [3..10] strictly disjoint for aligned pilot m_p_ddam=6, obs_ddam=[4..8]!
m_p_ddam = 6
obs_ddam = np.arange(4, 9)
D_ddam = np.arange(19, 59)

P_of_comb = np.arange(0, N, 8)
G_of_comb = np.unique(np.concatenate([(P_of_comb - 1) % N, P_of_comb, (P_of_comb + 1) % N]))
D_of_comb = np.setdiff1d(np.arange(N), G_of_comb)

rng_hc = np.random.default_rng(20261125)
best_p_hc = np.sort(rng_hc.choice(N, size=8, replace=False))
def _sl_hc(idx):
    v = np.zeros(N); v[idx] = 1.0
    return float(np.max(np.abs(np.fft.ifft(v))[1:6]) * N / len(idx))
best_v = _sl_hc(best_p_hc)
for _ in range(800):
    c_idx = best_p_hc.copy()
    c_idx[rng_hc.integers(0, 8)] = rng_hc.choice(np.setdiff1d(np.arange(N), c_idx))
    c_idx.sort()
    sv = _sl_hc(c_idx)
    if sv < best_v:
        best_v, best_p_hc = sv, c_idx
P_of_hc = best_p_hc
g_pool = np.setdiff1d(np.unique(np.concatenate([(P_of_hc - 1) % N, (P_of_hc + 1) % N, (P_of_hc - 2) % N, (P_of_hc + 2) % N])), P_of_hc)
if len(g_pool) < 16:
    g_pool = np.concatenate([g_pool, np.setdiff1d(np.arange(N), np.concatenate([P_of_hc, g_pool]))[:16 - len(g_pool)]])
G_of_hc = np.sort(np.concatenate([P_of_hc, g_pool[:16]]))
D_of_hc = np.setdiff1d(np.arange(N), G_of_hc)
assert len(D_af) == N_act and len(D_ddam) == N_act and len(D_of_comb) == N_act and len(D_of_hc) == N_act

P_tot = float(N)
E_pilot = (24.0 / 64.0) * P_tot
P_comm = (40.0 / 64.0) * P_tot
theta_tar = 40.0

NU_GRID_S1 = np.linspace(-1.0, 1.0, 81)
TH_GRID_S1 = np.linspace(-65.0, 65.0, 521)
NU_CAND_RX = np.linspace(-0.96, 0.96, 49)
FREQS_OF_JLS = np.linspace(-1.02, 1.02, 103)
F_RAD_GRID = np.linspace(0.11, 0.36, 36)
N_RAD_RANGE = 6
FN_CLUT_DYN = np.linspace(-0.035, 0.035, 5)
FN_CLUT_STA = np.array([0.0])

# Precompute exact radar & clutter operators once (eliminates >10^6 redundant 64x64 matrix products):
RAD_E_CACHE = {}
CLUT_E_CACHE = {}
for _is_of, (_Um, _c1) in ((False, (A_af, c1_af)), (True, (F_of, 0.0))):
    for _is_d in (False, True):
        _fn_c = FN_CLUT_DYN if _is_d else FN_CLUT_STA
        CLUT_E_CACHE[(_is_of, _is_d)] = [
            [make_E_op(_Um, _c1, _il, float(_fnc)).T.copy() for _fnc in _fn_c]
            for _il in range(N_RAD_RANGE)
        ]
        RAD_E_CACHE[(_is_of, _is_d)] = [
            [make_E_op(_Um, _c1, _il, float(_fc) if _is_d else 0.0).T.copy() for _fc in F_RAD_GRID]
            for _il in range(N_RAD_RANGE)
        ]


def build_rx_caches(K_cur):
    e_u_pil = 0.55 * E_pilot / float(K_cur)
    sc_data = np.sqrt(P_comm / float(K_cur * N_act))
    xp_af = np.zeros(N, dtype=complex); xp_af[m_p_af] = np.sqrt(e_u_pil)
    af_bank = [[make_E_op(A_af, c1_af, el, float(nc)) @ xp_af for nc in NU_CAND_RX] for el in range(Pk)]

    e_dd_pil = 0.35 * E_pilot / float(K_cur * Pk)
    xp_dd = np.zeros(N, dtype=complex); xp_dd[m_p_ddam] = np.sqrt(e_dd_pil)
    dd_bank = [make_E_op(A_af, c1_af, 0, float(nc)) @ xp_dd for nc in NU_CAND_RX]

    def _of_cache(P_tones, G_tones, edge_weight=0.6):
        Lr = len(P_tones)
        zc = np.exp(-1j * np.pi * np.arange(Lr) * (np.arange(Lr) + 1) / float(Lr))
        xp_u = np.zeros(N, dtype=complex); xp_u[P_tones] = np.sqrt(e_u_pil / float(Lr)) * zc
        ex = np.exp(2j * np.pi * FREQS_OF_JLS[:, None] * np.arange(N) / float(N))
        s_td = np.fft.ifft(xp_u, norm="ortho")
        pilots = np.array([(ex * np.roll(s_td, ell)[None, :]) @ F_of[G_tones].T for ell in range(Pk)])
        w = np.where(np.isin(G_tones, P_tones), 1.0, edge_weight)
        return zc, xp_u, pilots * w[None, None, :], w

    return e_u_pil, sc_data, xp_af, af_bank, xp_dd, dd_bank, _of_cache(P_of_comb, G_of_comb, 0.6), _of_cache(P_of_hc, G_of_hc, 0.6)


CACHE_K3 = build_rx_caches(3)
CACHE_K4 = build_rx_caches(4)


def stage1_real_uplink_sounding(users, Nt_v, K_v, is_dyn, sig2_ul, rng, sound_block_idx=-1):
    """Real Stage-1 uplink sounding reception & blind estimation (ZERO oracle parameter or sigma2 leaks!)."""
    step_ul = N // K_v
    m_uls = [(10 + k * step_ul) % N for k in range(K_v)]
    E_ul_k = float(N)
    Y_ul = np.sqrt(sig2_ul / 2.0) * (rng.standard_normal((N, Nt_v)) + 1j * rng.standard_normal((N, Nt_v)))
    for k in range(K_v):
        x_ul = np.zeros(N, dtype=complex); x_ul[m_uls[k]] = np.sqrt(E_ul_k)
        for (el, _, _, s_als, s_nus, s_ths) in users[k]:
            for m in range(M_sub):
                b_m1 = s_als[m] * np.exp(1j * 2 * np.pi * (s_nus[m] if is_dyn else 0.0) * sound_block_idx * Tsym)
                y_ray = b_m1 * (make_E_op(A_af, c1_af, el, s_nus[m] if is_dyn else 0.0) @ x_ul)
                Y_ul += y_ray[:, None] * steering_ula(Nt_v, s_ths[m])[None, :]

    A_grid = np.array([steering_ula(Nt_v, tg) for tg in TH_GRID_S1])
    nu_list = NU_GRID_S1 if is_dyn else np.array([0.0])
    est_all = []
    used_bins = np.zeros(N, dtype=bool)
    for k in range(K_v):
        x_ul = np.zeros(N, dtype=complex); x_ul[m_uls[k]] = np.sqrt(E_ul_k)
        u_est = []
        for el in [0, 1, 2]:
            center = (m_uls[k] - 4 * el) % N
            win = np.arange(center - 1, center + 2) % N if K_v == 4 else np.arange(center - 2, center + 3) % N
            used_bins[np.arange(center - 2, center + 3) % N] = True
            Y_w = Y_ul[win, :]
            th0 = float(TH_GRID_S1[int(np.argmax(np.sum(np.abs(Y_w @ A_grid.conj().T) ** 2, axis=0)))])
            f_ths = np.linspace(th0 - 0.25, th0 + 0.25, 21)
            A_fine = np.array([steering_ula(Nt_v, tg) for tg in f_ths])
            th_hat = float(f_ths[int(np.argmax(np.sum(np.abs(Y_w @ A_fine.conj().T) ** 2, axis=0)))])
            y_beam = (Y_w @ steering_ula(Nt_v, th_hat).conj()) / float(Nt_v)
            best_nu, best_sc, best_al = 0.0, -1.0, 0.0j
            for nu_c in nu_list:
                v = (make_E_op(A_af, c1_af, el, float(nu_c)) @ x_ul)[win]
                nrm2 = max(float(np.vdot(v, v).real), 1e-12)
                al_c = np.vdot(v, y_beam) / nrm2
                sc = (abs(al_c) ** 2) * nrm2
                if sc > best_sc:
                    best_sc, best_nu, best_al = sc, float(nu_c), al_c
            if is_dyn:
                for nu_f in np.linspace(best_nu - 0.025, best_nu + 0.025, 9):
                    v = (make_E_op(A_af, c1_af, el, float(nu_f)) @ x_ul)[win]
                    nrm2 = max(float(np.vdot(v, v).real), 1e-12)
                    al_c = np.vdot(v, y_beam) / nrm2
                    sc = (abs(al_c) ** 2) * nrm2
                    if sc > best_sc:
                        best_sc, best_nu, best_al = sc, float(nu_f), al_c
            u_est.append((el, th_hat, best_nu, best_al))
        est_all.append(u_est)
    empty_mask = ~used_bins
    sig2_ul_hat = max(float(np.mean(np.abs(Y_ul[empty_mask]) ** 2)) if np.any(empty_mask) else 1e-3, 1e-5)
    return est_all, sig2_ul_hat


def build_radar_null_beam(Nt_v, K_v, est_s1, null_users=True):
    a_tar = steering_ula(Nt_v, theta_tar)
    if not null_users:
        return a_tar / max(float(np.linalg.norm(a_tar)), 1e-12)
    A_u = np.column_stack([steering_ula(Nt_v, th_j) for j in range(K_v) for (_, th_j, _, _) in est_s1[j]])
    Q_u, R_u = np.linalg.qr(A_u, mode="reduced")
    Q_u = Q_u[:, np.abs(np.diag(R_u)) > 1e-8]
    wt = a_tar - Q_u @ (Q_u.conj().T @ a_tar)
    if float(np.linalg.norm(wt)) < 1e-6:
        wt = a_tar
    return wt / max(float(np.linalg.norm(wt)), 1e-12)


def align_add_radar_pilot_vec(v_u, wt, E_pil_target):
    v_u_nrm2 = float(np.vdot(v_u, v_u).real)
    if v_u_nrm2 >= E_pil_target:
        return v_u * np.sqrt(E_pil_target / v_u_nrm2)
    inner = np.vdot(wt, v_u)
    wt_aligned = wt * np.exp(1j * np.angle(inner + 1e-15))
    b_re = float(np.abs(inner))
    c_val = v_u_nrm2 - E_pil_target
    alpha_rad = max(-b_re + np.sqrt(max(b_re ** 2 - c_val, 0.0)), 0.0)
    return alpha_rad * wt_aligned + v_u


def design_beam_matched_dual_isac(Nt_v, K_v, e_u_pil, est_s1, sig2_h, null_inter_user=True):
    dths = [-0.9, 0.0, 0.9]
    Wk = np.zeros((K_v, Nt_v), dtype=complex)
    for k in range(K_v):
        if null_inter_user:
            Ri = max(K_v * sig2_h / P_comm, 1e-4) * np.eye(Nt_v, dtype=complex)
            for j in range(K_v):
                if j == k:
                    continue
                for (_, th_j, _, al_j) in est_s1[j]:
                    Asp = sum(np.outer(steering_ula(Nt_v, th_j + dt), steering_ula(Nt_v, th_j + dt).conj()) for dt in dths) / 3.0
                    Ri += 120.0 * (abs(al_j) ** 2 + 0.03) * Asp
            L = np.linalg.cholesky(np.linalg.inv(Ri))
        else:
            L = np.eye(Nt_v, dtype=complex)
        Ak_c = np.array([steering_ula(Nt_v, th_k).conj() for (_, th_k, _, _) in est_s1[k]])
        Beff = Ak_c @ L
        ph_k = np.zeros(Pk)
        for _ in range(30):
            wc = L @ (Beff.conj().T @ np.exp(1j * ph_k))
            wc /= max(float(np.linalg.norm(wc)), 1e-12)
            ph_k = np.angle(Ak_c @ wc)
        Wk[k] = wc

    wt = build_radar_null_beam(Nt_v, K_v, est_s1, null_users=null_inter_user)
    v_u = sum(np.sqrt(e_u_pil) * Wk[k] for k in range(K_v))
    s_pil_vec = align_add_radar_pilot_vec(v_u, wt, E_pilot)
    return s_pil_vec, Wk, wt


def solve_liu26_cpi_perbin_wmmse_extrap(Nt_v, K_v, est_s1, sig2_h, Dt):
    """
    Rang Liu & Schober (arXiv:2607.05119) Sec. IV-B CPI-fixed per-bin WMMSE beamformer
    designed on Stage-1 extrapolated CSI across q = 0..Q-1 (4 WMMSE iterations).
    NOTE (Explicit Pre-Registered Generosity to Baseline): Liu & Schober Eq. (33) assumes shared CSI
    so UE applies U_rx_q[q][k] (2560 complex scalars/block of unpriced downlink control signaling granted
    for free ONLY to this baseline; pilot subtraction still uses pure UE-blind obs_af estimation).
    """
    Hk_ext = [[np.zeros((N, N_act * Nt_v), dtype=complex) for _ in range(Q)] for _ in range(K_v)]
    for k in range(K_v):
        for p, (el, th_h, nu_h, al_m1) in enumerate(est_s1[k]):
            Ec = make_E_op(A_af, c1_af, el, nu_h)[:, Dt]
            H_b = np.kron(Ec, steering_ula(Nt_v, th_h).conj()[None, :])
            for q in range(Q):
                Hk_ext[k][q] += (al_m1 * np.exp(1j * 2 * np.pi * nu_h * (q + 1) * Tsym)) * H_b

    W_bin = np.zeros((K_v, N_act, Nt_v), dtype=complex)
    for k in range(K_v):
        for m in range(N_act):
            W_bin[k, m] = Hk_ext[k][0][Dt[m], m * Nt_v:(m + 1) * Nt_v].conj()
    nrm0 = np.sqrt(max(float(np.sum(np.abs(W_bin) ** 2)), 1e-12))
    W_bin *= np.sqrt(P_comm) / nrm0

    def _exp_act(Wb_k):
        M = np.zeros((N_act * Nt_v, N_act), dtype=complex)
        for m in range(N_act):
            M[m * Nt_v:(m + 1) * Nt_v, m] = Wb_k[m]
        return M

    U_rx_final = [[None] * K_v for _ in range(Q)]
    for it in range(4):
        Wc_list = [_exp_act(W_bin[k]) for k in range(K_v)]
        Tw_d = np.zeros((N_act, Nt_v, Nt_v), dtype=complex)
        Bk_d = np.zeros((K_v, N_act, Nt_v), dtype=complex)
        for q in range(Q):
            for k in range(K_v):
                HW_k = [Hk_ext[k][q] @ Wc_list[j] for j in range(K_v)]
                Ck = sig2_h * np.eye(N) + sum(HW_k[j] @ HW_k[j].conj().T for j in range(K_v))
                Uk = np.linalg.solve(Ck, HW_k[k])
                U_rx_final[q][k] = Uk
                if it == 3:
                    continue
                Ek = np.eye(N_act) - HW_k[k].conj().T @ Uk
                Ek = 0.5 * (Ek + Ek.conj().T) + 1e-7 * np.eye(N_act)
                Mk = np.linalg.inv(Ek)
                HUMU = Uk @ Mk @ Uk.conj().T
                Tw_f = (1.0 / Q) * (Hk_ext[k][q].conj().T @ HUMU @ Hk_ext[k][q])
                Bk_f = (1.0 / Q) * (Hk_ext[k][q].conj().T @ (Uk @ Mk))
                for m in range(N_act):
                    sl = slice(m * Nt_v, (m + 1) * Nt_v)
                    Tw_d[m] += Tw_f[sl, sl]
                    Bk_d[k, m] += Bk_f[sl, m]
        if it == 3:
            break
        evs_a, Us_a, Bp_a = [], [], []
        for m in range(N_act):
            ev, Ue = np.linalg.eigh(0.5 * (Tw_d[m] + Tw_d[m].conj().T))
            evs_a.append(np.maximum(ev, 0.0)); Us_a.append(Ue)
            Bp_a.append(Ue.conj().T @ Bk_d[:, m, :].T)
        ec = np.concatenate(evs_a); bc = np.vstack(Bp_a); rp = np.sum(np.abs(bc) ** 2, axis=1)
        lo, hi = 1e-7, 1e4
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            if float(np.sum(rp / ((ec + mid) ** 2))) > P_comm:
                lo = mid
            else:
                hi = mid
        for m in range(N_act):
            Wm = Us_a[m] @ ((1.0 / (evs_a[m] + hi))[:, None] * Bp_a[m])
            for k in range(K_v):
                W_bin[k, m] = Wm[:, k]
    return W_bin, U_rx_final


# ==============================================================================
# Pure UE-Local Blind Receiver Functions (ZERO BS-side variables passed!)
# ==============================================================================

def lmmse_slice_payload(yd, Gk, sig2_b, ref_sym=1.0 + 0.0j):
    GhG = Gk.conj().T @ Gk
    Minv = np.linalg.inv(GhG + sig2_b * np.eye(N_act))
    dku = (Minv @ (Gk.conj().T @ yd)) / np.maximum(np.real(np.diag(Minv @ GhG)), 1e-8)
    _ = ref_sym  # Reference bin m=0 excluded from payload error count (39/64 net payload)
    return pts16[np.argmin(np.abs(dku[1:, None] - pts16[None, :]), axis=1)]


def blind_est_afdm_channel(yk, xp_af, af_bank):
    """Pure UE-local blind 3-path (gain, Doppler, noise_var) estimator from yk[obs_af] alone."""
    nus_h = []
    for el in [0, 1, 2]:
        cb = m_p_af - 4 * el
        wl = np.arange(max(0, cb - 1), min(13, cb + 2))
        bi = max(
            range(len(NU_CAND_RX)),
            key=lambda i: abs(np.vdot(af_bank[el][i][wl], yk[wl])) ** 2 / max(float(np.vdot(af_bank[el][i][wl], af_bank[el][i][wl]).real), 1e-12),
        )
        nb = float(NU_CAND_RX[bi])
        best_sc = abs(np.vdot(af_bank[el][bi][wl], yk[wl])) ** 2 / max(float(np.vdot(af_bank[el][bi][wl], af_bank[el][bi][wl]).real), 1e-12)
        for nf in np.linspace(nb - 0.04, nb + 0.04, 7):
            v = (make_E_op(A_af, c1_af, el, float(nf)) @ xp_af)[wl]
            sc = abs(np.vdot(v, yk[wl])) ** 2 / max(float(np.vdot(v, v).real), 1e-12)
            if sc > best_sc:
                best_sc, nb = sc, float(nf)
        nus_h.append(nb)

    Eops = [make_E_op(A_af, c1_af, el, nus_h[el]) for el in [0, 1, 2]]
    Phi = np.column_stack([(Eops[el] @ xp_af)[obs_af] for el in [0, 1, 2]])
    gh = np.linalg.solve(Phi.conj().T @ Phi + 1e-6 * np.eye(3), Phi.conj().T @ yk[obs_af])
    sig2_b = max(float(np.mean(np.abs(yk[obs_af] - Phi @ gh) ** 2)), 1e-5)
    y_pil_hat = sum(gh[el] * (Eops[el] @ xp_af) for el in [0, 1, 2])
    return gh, nus_h, Eops, sig2_b, y_pil_hat


def blind_user_block_rx_afdm(yk, xp_af, af_bank, sc_data):
    gh, _, Eops, sig2_b, y_pil_hat = blind_est_afdm_channel(yk, xp_af, af_bank)
    yd = yk - y_pil_hat
    Gk = sc_data * sum(gh[el] * Eops[el][:, D_af] for el in [0, 1, 2])
    return lmmse_slice_payload(yd, Gk, sig2_b)


def blind_est_ofdm_sol_jls(yk, xp_u_of, grid_jls, w_jls, G_tones):
    """Pure UE-local Sol upgraded weighted 3-round QR joint nonlinear LS estimator from yk[G_tones] alone."""
    yw = yk[G_tones] * w_jls
    g_nrm2 = np.maximum(np.sum(np.abs(grid_jls) ** 2, axis=2), 1e-12)
    ix = [int(np.argmax((np.abs(grid_jls[j].conj() @ yw) ** 2) / g_nrm2[j])) for j in range(Pk)]
    for _ in range(3):
        for j in range(Pk):
            B = np.column_stack([grid_jls[i, ix[i]] for i in range(Pk) if i != j])
            Qo, _ = np.linalg.qr(B, mode="reduced")
            gp = grid_jls[j] - ((grid_jls[j] @ Qo.conj()) @ Qo.T)
            denom = np.maximum(np.sum(np.abs(gp) ** 2, axis=1), 1e-12)
            ix[j] = int(np.argmax((np.abs(gp.conj() @ yw) ** 2) / denom))
    A_mat = np.column_stack([grid_jls[j, ix[j]] for j in range(Pk)])
    co, _, _, _ = np.linalg.lstsq(A_mat, yw, rcond=None)
    H_full = sum(co[j] * make_E_op(F_of, 0.0, j, float(FREQS_OF_JLS[ix[j]])) for j in range(Pk))
    sig2_b = max(float(np.mean(np.abs(yk[G_tones] - (H_full @ xp_u_of)[G_tones]) ** 2)), 1e-5)
    y_pil_hat = H_full @ xp_u_of
    return H_full, sig2_b, y_pil_hat


def blind_user_block_rx_ofdm_sol_jls(yk, xp_u_of, grid_jls, w_jls, G_tones, D_tones, sc_data):
    H_full, sig2_b, y_pil_hat = blind_est_ofdm_sol_jls(yk, xp_u_of, grid_jls, w_jls, G_tones)
    yd = yk - y_pil_hat
    Gk = sc_data * H_full[:, D_tones]
    return lmmse_slice_payload(yd, Gk, sig2_b)


def blind_user_block_rx_tx_rzf(yk, is_ofdm, xp_af, af_bank, xp_u_of, grid_jls, w_jls, G_tones, D_tones, ref_sym):
    """
    Pure UE-local receiver for BS-side ExtrapBlockRZF (AFDM & OFDM):
    ZERO BS-side variables passed! Blindly subtracts pilot spillover from yk[obs_af]/yk[G_tones],
    estimates scalar gain from in-band reference symbol Dt[0]=ref_sym, and slices Dt[1:].
    """
    if not is_ofdm:
        _, _, _, _, y_pil_hat = blind_est_afdm_channel(yk, xp_af, af_bank)
    else:
        _, _, y_pil_hat = blind_est_ofdm_sol_jls(yk, xp_u_of, grid_jls, w_jls, G_tones)
    yd = yk - y_pil_hat
    zk_raw = yd[D_tones]
    g_ref = (zk_raw[0] / ref_sym) if abs(zk_raw[0]) > 1e-3 else 1.0
    zk_c = zk_raw[1:] / g_ref
    return pts16[np.argmin(np.abs(zk_c[:, None] - pts16[None, :]), axis=1)]


def blind_user_block_rx_ddam(yk, xp_dd, dd_bank, sc_dd_ratio, ref_sym):
    """
    Pure UE-local receiver for DDAM (Lu & Zeng TWC'24):
    ZERO BS-side variables passed! Both pilot (at m_p_ddam=6) and data (at D_ddam=[19..58]) traverse
    the identical BS delay-Doppler alignment operator T_k(q). UE blindly estimates the aligned composite
    tap's residual Doppler & gain on clean window obs_ddam=[4..8], calibrates per-block gain scale via
    unitary projection on reference D_ddam[0], subtracts pilot, and runs full-block LMMSE.
    """
    bi = max(
        range(len(NU_CAND_RX)),
        key=lambda i: abs(np.vdot(dd_bank[i][obs_ddam], yk[obs_ddam])) ** 2 / max(float(np.vdot(dd_bank[i][obs_ddam], dd_bank[i][obs_ddam]).real), 1e-12),
    )
    nb = float(NU_CAND_RX[bi])
    best_sc = abs(np.vdot(dd_bank[bi][obs_ddam], yk[obs_ddam])) ** 2 / max(float(np.vdot(dd_bank[bi][obs_ddam], dd_bank[bi][obs_ddam]).real), 1e-12)
    for nf in np.linspace(nb - 0.04, nb + 0.04, 7):
        v = (make_E_op(A_af, c1_af, 0, float(nf)) @ xp_dd)[obs_ddam]
        sc = abs(np.vdot(v, yk[obs_ddam])) ** 2 / max(float(np.vdot(v, v).real), 1e-12)
        if sc > best_sc:
            best_sc, nb = sc, float(nf)

    E0 = make_E_op(A_af, c1_af, 0, nb)
    v0 = (E0 @ xp_dd)[obs_ddam]
    gh0 = np.vdot(v0, yk[obs_ddam]) / max(float(np.vdot(v0, v0).real), 1e-12)
    sig2_b = max(float(np.mean(np.abs(yk[obs_ddam] - gh0 * v0) ** 2)), 1e-5)
    yd = yk - gh0 * (E0 @ xp_dd)

    gamma_nom = sc_dd_ratio * gh0
    z_ref = np.vdot(E0[:, D_ddam[0]], yd) / ref_sym
    var_prior = 0.08 * max(abs(gamma_nom) ** 2, 1e-4)
    gamma_hat = (var_prior * z_ref + sig2_b * gamma_nom) / (var_prior + sig2_b)

    Gk0 = gamma_hat * E0[:, D_ddam]
    return lmmse_slice_payload(yd, Gk0, sig2_b, ref_sym)


def unified_pure_blue_rd_score(Y_rad_cpi, S_tot_cpi, Nt_v, is_ofdm, is_dyn, win_center, sub_cpi_len):
    """
    Single unified monostatic radar scoring function across ALL arms and ALL sub_cpi_len (Q=16 and Q=2):
      1. ZERO CLEAN peak deletion, ZERO row masking.
      2. 100% identical clutter Doppler grid fn_clut and QR orthogonal subspace projection (1e-6 rank threshold)
         for BOTH sub_cpi_len=16 and sub_cpi_len=2 (ZERO q_len branching!).
      3. ZERO peak-driven background mask: identical full-map mean background denominator bg = mean(rd_map_acc)
         for both win_score and blind_score.
      4. Returns exact (tot_proj_e, tot_raw_e) summed over the full 16-block CPI so proj_keep_db is computed
         strictly as total post-projection energy / total pre-projection energy.
    """
    ar_t = steering_ula(Nr_rad, theta_tar)
    at_t = steering_ula(Nt_v, theta_tar)
    Y_beam_all = (Y_rad_cpi @ ar_t.conj()) / np.sqrt(float(Nr_rad))
    n_subs = Q // sub_cpi_len

    rd_map_acc = np.zeros((len(F_RAD_GRID), N_RAD_RANGE))
    jw, lw = win_center
    tot_proj_e = 0.0
    tot_raw_e = 0.0
    fn_clut = FN_CLUT_DYN if is_dyn else FN_CLUT_STA
    clut_et = CLUT_E_CACHE[(is_ofdm, is_dyn)]
    rad_et = RAD_E_CACHE[(is_ofdm, is_dyn)]

    for isub in range(n_subs):
        sl = slice(isub * sub_cpi_len, (isub + 1) * sub_cpi_len)
        Y_sub = Y_beam_all[sl]
        S_sub = S_tot_cpi[sl]
        q_len = sub_cpi_len

        S_flat = S_sub.reshape(q_len * N, Nt_v)
        _, sv_s, Vh_s = np.linalg.svd(S_flat, full_matrices=False)
        n_sp = min(6, int(np.sum(sv_s > 0.01 * sv_s[0])))
        U_sp_modes = (S_flat @ Vh_s[:n_sp].conj().T).reshape(q_len, N, n_sp)
        q_idx = np.arange(q_len)[:, None]
        clut_cols = []
        for il in range(N_RAD_RANGE):
            for ic, fnc in enumerate(fn_clut):
                Ec_T = clut_et[il][ic]
                ph_q = np.exp(1j * 2 * np.pi * float(fnc) * q_idx * Tsym)
                for isp in range(n_sp):
                    clut_cols.append((ph_q * (U_sp_modes[:, :, isp] @ Ec_T)).ravel())
        B_clut = np.column_stack(clut_cols)
        Qb, Rb = np.linalg.qr(B_clut, mode="reduced")
        diag_r = np.abs(np.diag(Rb))
        Qb = Qb[:, diag_r > 1e-6 * max(float(np.max(diag_r)), 1e-12)]

        y_vec = Y_sub.ravel()
        y_proj = y_vec - Qb @ (Qb.conj().T @ y_vec)
        u_tx = S_sub @ at_t.conj()
        ph_rad_all = np.exp(1j * 2 * np.pi * F_RAD_GRID[:, None] * (q_idx.T) * Tsym)  # (36, q_len)

        for il in range(N_RAD_RANGE):
            # Vectorized across all 36 Doppler bins for range bin il:
            T_mat = np.empty((len(F_RAD_GRID), q_len * N), dtype=complex)
            for jf in range(len(F_RAD_GRID)):
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
    win_peak = float(np.max(rd_map_acc[max(0, jw - 1):min(len(F_RAD_GRID), jw + 2), lw]))
    j_pk, l_pk = np.unravel_index(int(np.argmax(rd_map_acc)), rd_map_acc.shape)
    blind_peak = float(rd_map_acc[j_pk, l_pk])
    return win_peak / bg_common, blind_peak / bg_common, (int(j_pk), int(l_pk)), float(tot_proj_e), float(tot_raw_e)


def run_single_trial(task_tuple):
    """Worker function for 1 independent scene (cal, val, or pos)."""
    seed_i, role, has_tar, nu_max, sig_nu_sub, sig_th_sub, snr_db, Nt_v, K_v, include_low26 = task_tuple
    rng = np.random.default_rng(seed_i)
    is_dyn = (nu_max > 0 or sig_nu_sub > 0)
    sig2_c = 10.0 ** (-snr_db / 10.0)
    sig2_c_26 = 10.0 ** (-26.0 / 10.0)
    sig2_r = 10.0 ** (-20.0 / 10.0)
    clut_pow = 10.0 ** (+32.0 / 10.0) * sig2_r
    tar_pow = 10.0 ** (-3.0 / 10.0) * sig2_r

    e_u_pil, sc_data_nom, xp_af, af_bank, xp_dd, dd_bank, comb_pack, hc_pack = CACHE_K3 if K_v == 3 else CACHE_K4
    zc_comb, xpu_comb, grid_comb, w_comb = comb_pack
    zc_hc, xpu_hc, grid_hc, w_hc = hc_pack

    nom_degs = [-45.0, -10.0, 20.0] if K_v == 3 else [-52.0, -22.0, 4.0, 24.0]
    users = []
    for k in range(K_v):
        ells = np.array([0, 1, 2])
        base_offs = np.array([-4.5, 0.0, 4.5]) + rng.uniform(-1.0, 1.0, size=Pk)
        ths_c = nom_degs[k] + base_offs
        nus_c = rng.uniform(-nu_max, nu_max, size=Pk)
        clusters = []
        for p in range(Pk):
            s_als = (rng.standard_normal(M_sub) + 1j * rng.standard_normal(M_sub)) / np.sqrt(2.0 * Pk * M_sub)
            s_nus = nus_c[p] + rng.normal(0.0, sig_nu_sub, size=M_sub)
            s_ths = ths_c[p] + rng.normal(0.0, sig_th_sub, size=M_sub)
            clusters.append((ells[p], ths_c[p], nus_c[p], s_als, s_nus, s_ths))
        users.append(clusters)

    rng_s1 = np.random.default_rng(seed_i + 1000000)
    est_s1, sig2_ul_hat = stage1_real_uplink_sounding(users, Nt_v, K_v, is_dyn, sig2_c, rng_s1, sound_block_idx=-1)
    s_pil_vec, W_beams, wt_null = design_beam_matched_dual_isac(Nt_v, K_v, e_u_pil, est_s1, sig2_ul_hat, null_inter_user=True)

    if include_low26 and role == "pos":
        rng_s1_26 = np.random.default_rng(seed_i + 1000000)
        est_s1_26, sig2_ul_26 = stage1_real_uplink_sounding(users, Nt_v, K_v, is_dyn, sig2_c_26, rng_s1_26, sound_block_idx=-1)
        s_pil_26, W_beams_26, _ = design_beam_matched_dual_isac(Nt_v, K_v, e_u_pil, est_s1_26, sig2_ul_26, null_inter_user=True)

    if K_v == 3:
        s_pil_mrt, W_mrt, _ = design_beam_matched_dual_isac(Nt_v, K_v, e_u_pil, est_s1, sig2_ul_hat, null_inter_user=False)
        est_sub_list = [est_s1]
        if is_dyn:
            for isub in range(1, 8):
                es_sub, _ = stage1_real_uplink_sounding(users, Nt_v, K_v, is_dyn, sig2_c, rng_s1, sound_block_idx=2 * isub - 1)
                est_sub_list.append(es_sub)
        else:
            est_sub_list = [est_s1] * 8

    E_est_af = [[make_E_op(A_af, c1_af, el, nu_h) for (el, _, nu_h, _) in est_s1[k]] for k in range(K_v)]
    E_est_of = [[make_E_op(F_of, 0.0, el, nu_h) for (el, _, nu_h, _) in est_s1[k]] for k in range(K_v)]
    if role == "pos":
        E_true_af = [[[make_E_op(A_af, c1_af, el, s_nus[m] if is_dyn else 0.0) for m in range(M_sub)] for (el, _, _, _, s_nus, _) in users[k]] for k in range(K_v)]
        E_true_of = [[[make_E_op(F_of, 0.0, el, s_nus[m] if is_dyn else 0.0) for m in range(M_sub)] for (el, _, _, _, s_nus, _) in users[k]] for k in range(K_v)]

    # Deterministic user-specific reference phase at Dt[0], i.i.d. 16-QAM payload at Dt[1:]:
    ref_syms = np.array([np.exp(1j * 2.0 * np.pi * k / float(K_v)) for k in range(K_v)], dtype=complex)
    d_pay = rng.choice(pts16, size=(Q, K_v, N_payload))
    d_blk = np.zeros((Q, K_v, N_act), dtype=complex)
    d_blk[:, :, 0] = ref_syms[None, :]
    d_blk[:, :, 1:] = d_pay

    z_u_unit = (rng.standard_normal((Q, K_v, N)) + 1j * rng.standard_normal((Q, K_v, N))) / np.sqrt(2.0)
    noise_u = np.sqrt(sig2_c) * z_u_unit
    noise_u_26 = np.sqrt(sig2_c_26) * z_u_unit
    noise_r = np.sqrt(sig2_r / 2.0) * (rng.standard_normal((Q, N, Nr_rad)) + 1j * rng.standard_normal((Q, N, Nr_rad)))

    c_ells = [0, 1, 3, 5]
    c_degs = [-30.0, 5.0, 38.0, 50.0]
    c_gains = np.sqrt(clut_pow / 4.0 / 2.0) * (rng.standard_normal(4) + 1j * rng.standard_normal(4))
    c_nus = rng.uniform(-0.03, 0.03, size=4) if is_dyn else np.zeros(4)
    g_t = (np.sqrt(tar_pow) * np.exp(1j * rng.uniform(0, 2 * np.pi))) if has_tar else 0.0

    ell_tar, nu_tar = 2, 0.145
    jw_true = int(np.argmin(np.abs(F_RAD_GRID - nu_tar)))
    win_center = (jw_true, ell_tar)

    if K_v == 4:
        arms = ["Prop_BeamMatchedDualISAC_AFDM", "OFDM_Comb_JointWLS_DualISAC", "ExtrapBlockRZF_Aged_AFDM"]
        radar_arms = []
    else:
        radar_arms = [
            "Prop_BeamMatchedDualISAC_AFDM",
            "OFDM_Comb_JointWLS_DualISAC",
            "ExtrapBlockRZF_Short8xQ2_AFDM",
        ]
        arms = [
            "Prop_BeamMatchedDualISAC_AFDM",
            "Oracle_TrueEffH_AFDM",
            "Oracle_TrueEffH_OFDM_Comb",
            "OFDM_Comb_JointWLS_DualISAC",
            "OFDM_HillClimb_JointWLS_ISAC",
            "OFDM_ExtrapBlockRZF",
            "Liu26_PerBinWMMSE_Aged_AFDM",
            "ExtrapBlockRZF_Aged_AFDM",
            "ExtrapBlockRZF_UnagedQ0_AFDM",
            "ExtrapBlockRZF_Short8xQ2_AFDM",
            "DDAM_CleanFullEq_AFDM",
            "Abl_Aonly_PathNull_NoTrack_AFDM",
            "Abl_Bonly_MRT_WithTrack_AFDM",
        ]
        if include_low26:
            arms.append("Prop_BeamMatchedDualISAC_AFDM_26dB")

    active_arms = arms if role == "pos" else radar_arms
    out_ser = {}
    out_rad = {}

    for arm in active_arms:
        is_ofdm = ("OFDM" in arm)
        U_m = F_of if is_ofdm else A_af
        c1_v = 0.0 if is_ofdm else c1_af
        E_es = E_est_of if is_ofdm else E_est_af

        if arm == "OFDM_HillClimb_JointWLS_ISAC":
            Pt, Gt, Dt, zc_o, xpu_o, gr_jls, w_jls = P_of_hc, G_of_hc, D_of_hc, zc_hc, xpu_hc, grid_hc, w_hc
        elif is_ofdm:
            Pt, Gt, Dt, zc_o, xpu_o, gr_jls, w_jls = P_of_comb, G_of_comb, D_of_comb, zc_comb, xpu_comb, grid_comb, w_comb
        elif arm == "DDAM_CleanFullEq_AFDM":
            Pt, Gt, Dt, zc_o, xpu_o, gr_jls, w_jls = np.array([m_p_ddam]), obs_ddam, D_ddam, None, None, None, None
        else:
            Pt, Gt, Dt, zc_o, xpu_o, gr_jls, w_jls = np.array([m_p_af]), obs_af, D_af, None, None, None, None

        if arm == "Prop_BeamMatchedDualISAC_AFDM_26dB":
            sp_v, Wb_use, nu_use = s_pil_26, W_beams_26, noise_u_26
        elif arm == "Abl_Bonly_MRT_WithTrack_AFDM":
            sp_v, Wb_use, nu_use = s_pil_mrt, W_mrt, noise_u
        else:
            sp_v, Wb_use, nu_use = s_pil_vec, W_beams, noise_u

        S_pil = np.zeros((N, Nt_v), dtype=complex)
        if not is_ofdm and arm != "DDAM_CleanFullEq_AFDM":
            S_pil[m_p_af, :] = sp_v
        elif is_ofdm:
            S_pil[Pt, :] = (zc_o / np.sqrt(float(len(Pt))))[:, None] * sp_v[None, :]

        S_tot_cpi = np.zeros((Q, N, Nt_v), dtype=complex)
        q_eval_list = [0] if arm == "ExtrapBlockRZF_UnagedQ0_AFDM" else list(range(Q))

        if arm == "Liu26_PerBinWMMSE_Aged_AFDM":
            W_bin_liu, U_rx_liu = solve_liu26_cpi_perbin_wmmse_extrap(Nt_v, K_v, est_s1, sig2_ul_hat, Dt)
            S_ref_0 = np.zeros((N, Nt_v), dtype=complex)
            S_ref_0[Dt[0], :] = sum(ref_syms[k] * W_bin_liu[k, 0] for k in range(K_v))
            pay_frob2 = float(np.sum(np.abs(W_bin_liu[:, 1:, :]) ** 2))
            beta_liu = solve_exact_expected_beta(S_pil, S_ref_0, pay_frob2, P_tot)
            for q in q_eval_list:
                S_comm_0 = sum(d_blk[q, k][:, None] * W_bin_liu[k] for k in range(K_v))
                S_tot_cpi[q] = S_pil.copy()
                S_tot_cpi[q, Dt, :] += beta_liu * S_comm_0
        elif arm == "DDAM_CleanFullEq_AFDM":
            # Textbook per-path SLNR / MMSE beamforming (reg = ((K*Pk)^2 * sig2_ul_hat) / P_comm balances cross-path
            # leakage suppression against 4.5-deg mainlobe array-gain loss on finite Nt=12 ULA):
            W_ddam = [[None] * Pk for _ in range(K_v)]
            reg_slnr = max(((K_v * Pk) ** 2) * sig2_ul_hat / P_comm, 1e-4)
            for k in range(K_v):
                for p, (_, th_k, _, _) in enumerate(est_s1[k]):
                    R_i = reg_slnr * np.eye(Nt_v, dtype=complex)
                    for j in range(K_v):
                        for p2, (_, th2, _, al2) in enumerate(est_s1[j]):
                            if j == k and p2 == p:
                                continue
                            a2 = steering_ula(Nt_v, th2)
                            R_i += max(abs(al2) ** 2, 1e-3) * np.outer(a2, a2.conj())
                    v = np.linalg.solve(R_i, steering_ula(Nt_v, th_k))
                    W_ddam[k][p] = v / max(float(np.linalg.norm(v)), 1e-12)

            for q in q_eval_list:
                # Per-block DDAM phase pre-compensation ph_c(q, k, p) applied identically to co-located pilot & data,
                # with exact per-block expected transmit energy == P_tot = 64.0!
                ph_mat = np.zeros((K_v, Pk), dtype=complex)
                for k in range(K_v):
                    for p, (el, th_h, nu_h, al_m1) in enumerate(est_s1[k]):
                        bq_h = al_m1 * np.exp(1j * 2 * np.pi * nu_h * (q + 1) * Tsym)
                        eff_g = bq_h * (steering_ula(Nt_v, th_h).conj() @ W_ddam[k][p])
                        ph_mat[k, p] = np.exp(-1j * np.angle(eff_g + 1e-12))

                # Build DDAM pilot matrix S_pil_q using the EXACT SAME operator T_k(q) as data + user-nulled radar beam:
                S_pil_u = np.zeros((N, Nt_v), dtype=complex)
                for k in range(K_v):
                    for p in range(Pk):
                        S_pil_u += ph_mat[k, p] * ((E_es[k][p].conj().T @ xp_dd)[:, None] * W_ddam[k][p][None, :])
                u_pil_e = float(np.sum(np.abs(S_pil_u) ** 2))
                if u_pil_e >= E_pilot:
                    S_pil_q = S_pil_u * np.sqrt(E_pilot / u_pil_e)
                else:
                    S_rad_dir = np.zeros((N, Nt_v), dtype=complex)
                    S_rad_dir[m_p_ddam, :] = wt_null
                    ip = np.vdot(S_rad_dir, S_pil_u)
                    S_rad_al = S_rad_dir * np.exp(1j * np.angle(ip + 1e-15))
                    br = float(np.abs(ip))
                    ar = max(-br + np.sqrt(max(br * br - (u_pil_e - E_pilot), 0.0)), 0.0)
                    S_pil_q = S_pil_u + ar * S_rad_al

                # Exact block-q expected power accounting including ph_mat[k, p] & cross-path inner products:
                S_ref_0 = np.zeros((N, Nt_v), dtype=complex)
                pay_frob2 = 0.0
                for k in range(K_v):
                    ev0 = np.zeros(N, dtype=complex); ev0[Dt[0]] = ref_syms[k]
                    S_ref_0 += sum(ph_mat[k, p] * ((E_es[k][p].conj().T @ ev0)[:, None] * W_ddam[k][p][None, :]) for p in range(Pk))
                    # Gram sum over m in Dt[1:]: sum_{m>=1} || sum_p ph_{k,p} w_{k,p} (E_{k,p}^H[:, Dt[m]])^T ||_F^2
                    G_p = [ph_mat[k, p] * E_es[k][p].conj().T[:, Dt[1:]] for p in range(Pk)]  # each (N, N_payload)
                    for p1 in range(Pk):
                        for p2 in range(Pk):
                            w_ip = np.vdot(W_ddam[k][p1], W_ddam[k][p2])
                            e_ip = np.vdot(G_p[p1], G_p[p2])
                            pay_frob2 += float(np.real(w_ip * e_ip))
                beta_dd_q = solve_exact_expected_beta(S_pil_q, S_ref_0, pay_frob2, P_tot)

                S_comm_0 = np.zeros((N, Nt_v), dtype=complex)
                for k in range(K_v):
                    xk_vec = np.zeros(N, dtype=complex); xk_vec[Dt] = d_blk[q, k]
                    for p in range(Pk):
                        S_comm_0 += ph_mat[k, p] * ((E_es[k][p].conj().T @ xk_vec)[:, None] * W_ddam[k][p][None, :])
                S_tot_cpi[q] = S_pil_q + beta_dd_q * S_comm_0
        elif arm in ("ExtrapBlockRZF_Aged_AFDM", "ExtrapBlockRZF_UnagedQ0_AFDM", "ExtrapBlockRZF_Short8xQ2_AFDM", "OFDM_ExtrapBlockRZF"):
            for q in q_eval_list:
                isub = q // 2
                es_cur = est_sub_list[isub] if arm == "ExtrapBlockRZF_Short8xQ2_AFDM" else est_s1
                dt_steps = (q - (2 * isub - 1)) if arm == "ExtrapBlockRZF_Short8xQ2_AFDM" else (q + 1)
                H_rows = []
                for k in range(K_v):
                    Hk_dt = np.zeros((N_act, N_act * Nt_v), dtype=complex)
                    for p, (el, th_h, nu_h, al_m1) in enumerate(es_cur[k]):
                        bq_h = al_m1 * np.exp(1j * 2 * np.pi * nu_h * dt_steps * Tsym)
                        Ec_dt = make_E_op(U_m, c1_v, el, nu_h)[np.ix_(Dt, Dt)] if arm == "ExtrapBlockRZF_Short8xQ2_AFDM" else E_es[k][p][np.ix_(Dt, Dt)]
                        at = steering_ula(Nt_v, th_h)
                        Hk_dt += bq_h * np.kron(Ec_dt, at.conj()[None, :])
                    H_rows.append(Hk_dt)
                H_all = np.vstack(H_rows)  # (K_v * N_act, N_act * Nt_v) = (120, 480) -> direct TX RZF onto UE Dt bins!
                reg_i = K_v * N_act * sig2_ul_hat / P_comm
                W_raw = H_all.conj().T @ np.linalg.inv(H_all @ H_all.conj().T + reg_i * np.eye(K_v * N_act))

                ref_mask = np.zeros(K_v * N_act, dtype=bool)
                for k in range(K_v):
                    ref_mask[k * N_act] = True
                ref_vec = np.zeros(K_v * N_act, dtype=complex)
                for k in range(K_v):
                    ref_vec[k * N_act] = ref_syms[k]
                S_ref_0 = np.zeros((N, Nt_v), dtype=complex)
                S_ref_0[Dt, :] = (W_raw @ ref_vec).reshape(N_act, Nt_v)
                pay_frob2 = float(np.sum(np.abs(W_raw[:, ~ref_mask]) ** 2))
                beta_rzf = solve_exact_expected_beta(S_pil, S_ref_0, pay_frob2, P_tot)

                S_tot_cpi[q] = S_pil.copy()
                S_tot_cpi[q, Dt, :] += beta_rzf * (W_raw @ d_blk[q].ravel()).reshape(N_act, Nt_v)
        else:
            # Prop, Oracle, OFDM_Comb, OFDM_HillClimb, Abl_Aonly, Abl_Bonly:
            S_ref_0 = np.zeros((N, Nt_v), dtype=complex)
            S_ref_0[Dt[0], :] = sum(ref_syms[k] * Wb_use[k] for k in range(K_v))
            pay_frob2 = float(N_payload) * sum(float(np.sum(np.abs(Wb_use[k]) ** 2)) for k in range(K_v))
            beta_std = solve_exact_expected_beta(S_pil, S_ref_0, pay_frob2, P_tot)
            # Verify exact expected block transmit energy == P_tot = 64.0:
            exp_e = float(np.sum(np.abs(S_pil + beta_std * S_ref_0) ** 2)) + (beta_std ** 2) * pay_frob2
            assert abs(exp_e - P_tot) < 1e-9, f"Power mismatch in {arm}: {exp_e}"
            for q in q_eval_list:
                S_tot_cpi[q] = S_pil.copy()
                S_tot_cpi[q, Dt, :] += sum(beta_std * d_blk[q, k][:, None] * Wb_use[k][None, :] for k in range(K_v))

        if role == "pos":
            E_tr = E_true_of if is_ofdm else E_true_af
            ser_u = []
            for k in range(K_v):
                Y_k_cpi = nu_use[:, k, :].copy()
                for q in q_eval_list:
                    for p, (_, _, _, s_als, s_nus, s_ths) in enumerate(users[k]):
                        for m in range(M_sub):
                            bq = s_als[m] * np.exp(1j * 2 * np.pi * s_nus[m] * q * Tsym)
                            Y_k_cpi[q] += bq * (E_tr[k][p][m] @ (S_tot_cpi[q] @ steering_ula(Nt_v, s_ths[m]).conj()))

                # For Abl_Aonly: pure UE-local blind estimation at block q=0 ONLY, held fixed across q=0..15 without tracking (ZERO BS reads!):
                if arm == "Abl_Aonly_PathNull_NoTrack_AFDM":
                    gh_q0, _, Eops_q0, sig2_q0, y_pil_q0 = blind_est_afdm_channel(Y_k_cpi[0], xp_af, af_bank)
                    Gk_q0 = sc_data_nom * sum(gh_q0[el] * Eops_q0[el][:, D_af] for el in [0, 1, 2])
                sc_dd_ratio = np.sqrt(P_comm / float(K_v * Pk * N_act))

                d_hats = []
                for idx_q, q in enumerate(q_eval_list):
                    yk = Y_k_cpi[q]
                    if arm in ("Oracle_TrueEffH_AFDM", "Oracle_TrueEffH_OFDM_Comb"):
                        H_true_u = np.zeros((N, N), dtype=complex)
                        y_pil_true = np.zeros(N, dtype=complex)
                        for p, (_, _, _, s_als, s_nus, s_ths) in enumerate(users[k]):
                            for m in range(M_sub):
                                at_c = steering_ula(Nt_v, s_ths[m]).conj()
                                g_op = s_als[m] * np.exp(1j * 2 * np.pi * s_nus[m] * q * Tsym) * E_tr[k][p][m]
                                y_pil_true += g_op @ (S_pil @ at_c)
                                H_true_u += (at_c @ W_beams[k]) * g_op
                        d_hats.append(lmmse_slice_payload(yk - y_pil_true, sc_data_nom * H_true_u[:, Dt], sig2_c, ref_syms[k]))
                    elif arm == "Liu26_PerBinWMMSE_Aged_AFDM":
                        # Pure UE-blind pilot subtraction on obs_af + pre-registered signaled U_rx_liu[q][k]:
                        _, _, _, _, y_pil_hat = blind_est_afdm_channel(yk, xp_af, af_bank)
                        zk_raw = U_rx_liu[q][k].conj().T @ (yk - y_pil_hat)
                        g_ref = (zk_raw[0] / ref_syms[k]) if abs(zk_raw[0]) > 1e-3 else 1.0
                        zk_c = zk_raw[1:] / g_ref
                        d_hats.append(pts16[np.argmin(np.abs(zk_c[:, None] - pts16[None, :]), axis=1)])
                    elif arm in ("ExtrapBlockRZF_Aged_AFDM", "ExtrapBlockRZF_UnagedQ0_AFDM", "ExtrapBlockRZF_Short8xQ2_AFDM", "OFDM_ExtrapBlockRZF"):
                        d_hats.append(blind_user_block_rx_tx_rzf(yk, is_ofdm, xp_af, af_bank, xpu_o, gr_jls, w_jls, Gt, Dt, ref_syms[k]))
                    elif arm == "DDAM_CleanFullEq_AFDM":
                        d_hats.append(blind_user_block_rx_ddam(yk, xp_dd, dd_bank, sc_dd_ratio, ref_syms[k]))
                    elif arm == "Abl_Aonly_PathNull_NoTrack_AFDM":
                        d_hats.append(lmmse_slice_payload(yk - y_pil_q0, Gk_q0, sig2_q0, ref_syms[k]))
                    elif not is_ofdm:
                        d_hats.append(blind_user_block_rx_afdm(yk, xp_af, af_bank, sc_data_nom))
                    else:
                        d_hats.append(blind_user_block_rx_ofdm_sol_jls(yk, xpu_o, gr_jls, w_jls, Gt, Dt, sc_data_nom))
                d_hats_arr = np.array(d_hats)
                ser_u.append(float(np.mean(np.abs(d_hats_arr - d_pay[q_eval_list, k, :]) > 1e-3)))
            out_ser[arm] = float(np.mean(ser_u))

        if arm in radar_arms:
            Y_rad_cpi = noise_r.copy()
            for ic in range(4):
                Ec = make_E_op(U_m, c1_v, c_ells[ic], c_nus[ic])
                at_c = steering_ula(Nt_v, c_degs[ic])
                ar_c = steering_ula(Nr_rad, c_degs[ic])
                u_c = (S_tot_cpi @ at_c.conj()) @ Ec.T
                bq_c = c_gains[ic] * np.exp(1j * 2 * np.pi * c_nus[ic] * np.arange(Q) * Tsym)
                Y_rad_cpi += (bq_c[:, None] * u_c)[:, :, None] * ar_c[None, None, :]
            if has_tar:
                at_t = steering_ula(Nt_v, theta_tar)
                ar_t = steering_ula(Nr_rad, theta_tar)
                Et = make_E_op(U_m, c1_v, ell_tar, nu_tar if is_dyn else 0.0)
                u_t = (S_tot_cpi @ at_t.conj()) @ Et.T
                bq_t = g_t * np.exp(1j * 2 * np.pi * nu_tar * np.arange(Q) * Tsym)
                Y_rad_cpi += (bq_t[:, None] * u_t)[:, :, None] * ar_t[None, None, :]

            sub_len = 2 if arm == "ExtrapBlockRZF_Short8xQ2_AFDM" else Q
            ws, bs, bl, tpe, tre = unified_pure_blue_rd_score(Y_rad_cpi, S_tot_cpi, Nt_v, is_ofdm, is_dyn, win_center, sub_len)
            out_rad[arm] = (ws, bs, bl, tpe, tre)

    return out_ser, out_rad


def paired_ci95(arr):
    a = np.asarray(arr, dtype=float)
    m = float(np.mean(a))
    se = float(np.std(a, ddof=1) / np.sqrt(len(a))) if len(a) > 1 else 0.0
    hw = 1.96 * se
    return {"mean": m, "se": se, "ci95_low": m - hw, "ci95_high": m + hw, "ci95_half_width": hw}


def newcombe_paired_binary_ci95(x_hits, y_hits):
    """
    Newcombe (1998, Stat. Med. 17:2635-2650, Method 10) Wilson score 95% CI for paired binary difference p1 - p2.
    Remains well-defined with non-zero finite Wilson width even when p1=1.0 and p2=0.0!
    """
    x = np.asarray(x_hits, dtype=float) > 0.5
    y = np.asarray(y_hits, dtype=float) > 0.5
    n = float(len(x))
    z = 1.959964
    if n < 1:
        return {"mean": 0.0, "ci95_low": 0.0, "ci95_high": 0.0, "ci95_half_width": 0.0}

    a = float(np.sum(x & y))
    b = float(np.sum(x & (~y)))
    c = float(np.sum((~x) & y))
    d = float(np.sum((~x) & (~y)))
    p1 = (a + b) / n
    p2 = (a + c) / n
    diff = p1 - p2

    def _wilson(p):
        den = 1.0 + (z * z) / n
        cen = (p + (z * z) / (2.0 * n)) / den
        rad = (z * np.sqrt(max(p * (1.0 - p) / n + (z * z) / (4.0 * n * n), 0.0))) / den
        return max(0.0, cen - rad), min(1.0, cen + rad)

    l1, u1 = _wilson(p1)
    l2, u2 = _wilson(p2)
    m_prod = (a + b) * (c + d) * (a + c) * (b + d)
    if m_prod > 0.0:
        num = a * d - b * c
        corr = (num - np.sign(num) * min(0.5 * n, abs(num))) / np.sqrt(m_prod)
    else:
        corr = 0.0

    dl = np.sqrt(max((p1 - l1) ** 2 - 2.0 * corr * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2, 0.0))
    du = np.sqrt(max((u1 - p1) ** 2 - 2.0 * corr * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2, 0.0))
    ci_low = float(max(-1.0, diff - dl))
    ci_high = float(min(1.0, diff + du))
    # Use conservative max(dl, du) as half-width check so boundary asymmetry cannot understate width:
    hw_cons = float(max(diff - ci_low, ci_high - diff))
    return {"mean": float(diff), "ci95_low": ci_low, "ci95_high": ci_high, "ci95_half_width": hw_cons}


def run_regime_pool(pool, nu_max, sig_nu_sub, sig_th_sub, snr_db, Nt_v, K_v, n_cal, n_val, n_pos, seed_base, include_low26=False):
    cal_tasks = [(seed_base + i, "cal", False, nu_max, sig_nu_sub, sig_th_sub, snr_db, Nt_v, K_v, False) for i in range(n_cal)]
    val_tasks = [(seed_base + 20000 + i, "val", False, nu_max, sig_nu_sub, sig_th_sub, snr_db, Nt_v, K_v, False) for i in range(n_val)]
    pos_tasks = [(seed_base + 40000 + i, "pos", True, nu_max, sig_nu_sub, sig_th_sub, snr_db, Nt_v, K_v, include_low26) for i in range(n_pos)]

    map_fn = pool.map if pool is not None else map
    cal_res = list(map_fn(run_single_trial, cal_tasks)) if n_cal > 0 else []
    val_res = list(map_fn(run_single_trial, val_tasks)) if n_val > 0 else []
    pos_res = list(map_fn(run_single_trial, pos_tasks))

    ser_dict = {a: [r[0][a] for r in pos_res] for a in pos_res[0][0]}
    rad_summary = {}
    rad_hits_blind = {}
    pfa_t = 0.05
    ell_tar = 2
    jw_true = int(np.argmin(np.abs(F_RAD_GRID - 0.145)))

    if n_cal > 0 and len(pos_res[0][1]) > 0:
        for a in pos_res[0][1]:
            cw = [r[1][a][0] for r in cal_res]
            cb = [r[1][a][1] for r in cal_res]
            vw = [r[1][a][0] for r in val_res]
            vb = [r[1][a][1] for r in val_res]
            pw = [r[1][a][0] for r in pos_res]
            pb = [r[1][a][1] for r in pos_res]
            pl = [r[1][a][2] for r in pos_res]
            tpe_sum = float(np.sum([r[1][a][3] for r in pos_res]))
            tre_sum = float(np.sum([r[1][a][4] for r in pos_res]))

            tw = float(np.quantile(cw, 1.0 - pfa_t, method="weibull"))
            tb = float(np.quantile(cb, 1.0 - pfa_t, method="weibull"))
            vpw = float(np.mean(np.array(vw) > tw))
            vpb = float(np.mean(np.array(vb) > tb))
            wpd = float(np.mean(np.array(pw) > tw))
            bhits = [float((pb[i] > tb) and (abs(pl[i][0] - jw_true) <= 2) and (pl[i][1] == ell_tar)) for i in range(n_pos)]
            rad_hits_blind[a] = bhits
            rad_summary[a] = {
                "win_pd": wpd,
                "val_pfa_win": vpw,
                "loc_blind_pd": float(np.mean(bhits)),
                "val_pfa_blind": vpb,
                "proj_keep_db": float(10.0 * np.log10(max(tpe_sum / max(tre_sum, 1e-18), 1e-12))),
                "calls": {"cal": len(cal_res), "val": len(val_res), "pos": len(pos_res)},
            }
    return ser_dict, rad_summary, rad_hits_blind


def bootstrap_recovery_ci95(base_arr, abl_arr, prop_arr, n_boot=4000, seed_b=99999):
    rng_b = np.random.default_rng(seed_b)
    b = np.asarray(base_arr, dtype=float)
    ab = np.asarray(abl_arr, dtype=float)
    pr = np.asarray(prop_arr, dtype=float)
    pt = float((np.mean(b) - np.mean(ab)) / max(np.mean(b) - np.mean(pr), 1e-12))
    n = len(b)
    if n < 2:
        return {"mean": pt, "ci95_low": pt, "ci95_high": pt, "ci95_half_width": 0.0}
    idx = rng_b.integers(0, n, size=(n_boot, n))
    num = np.mean(b[idx] - ab[idx], axis=1)
    den = np.maximum(np.mean(b[idx] - pr[idx], axis=1), 1e-8)
    boots = num / den
    cl = float(np.quantile(boots, 0.025))
    ch = float(np.quantile(boots, 0.975))
    return {"mean": pt, "ci95_low": cl, "ci95_high": ch, "ci95_half_width": 0.5 * (ch - cl)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deinlab", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="summary_h_r11_h02.json")
    args = ap.parse_args()

    if args.deinlab:
        assert sys.executable == "/home/guoyikun/.conda/envs/AFDM/bin/python", f"Wrong python: {sys.executable}"
    assert 1 <= args.workers <= 8, f"Workers {args.workers} exceeds 8-core cap!"

    t_start = time.perf_counter()
    rl1_info = verify_red_line_1_invariants()
    print(f"[Invariant Check Passed] {rl1_info}", flush=True)

    if args.smoke:
        n_cal_0, n_val_0, n_pos_0 = 10, 10, 3
        n_cal_1, n_val_1, n_pos_1 = 10, 10, 4
        n_pos_s2 = 3
        seed_z0, seed_z1, seed_s2 = 900, 950, 980
        pool = None
    else:
        n_cal_0, n_val_0, n_pos_0 = 120, 120, 64
        n_cal_1, n_val_1, n_pos_1 = 320, 320, 144
        n_pos_s2 = 48
        seed_z0, seed_z1, seed_s2 = 200000, 300000, 400000
        pool = Pool(processes=args.workers)

    try:
        ser_z0, rad_z0, _ = run_regime_pool(pool, 0.0, 0.0, 0.0, 28.0, 12, 3, n_cal_0, n_val_0, n_pos_0, seed_z0, include_low26=False)
        print("[Z=0 Static Regime Done]", flush=True)
        ser_z1, rad_z1, bhits_z1 = run_regime_pool(pool, 0.85, 0.025, 0.8, 28.0, 12, 3, n_cal_1, n_val_1, n_pos_1, seed_z1, include_low26=True)
        print("[Z=1 Dynamic 16-Block CPI Regime Done]", flush=True)
        ser_s2, _, _ = run_regime_pool(pool, 0.85, 0.025, 0.8, 26.0, 16, 4, 0, 0, n_pos_s2, seed_s2, include_low26=False)
        print("[Scope Regime Nt=16, K=4 Done]", flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    ofdm_candidates = ["OFDM_ExtrapBlockRZF", "OFDM_Comb_JointWLS_DualISAC", "OFDM_HillClimb_JointWLS_ISAC"]
    best_ofdm_z0_name = min(ofdm_candidates, key=lambda a: float(np.mean(ser_z0[a])))
    best_ofdm_z1_name = min(ofdm_candidates, key=lambda a: float(np.mean(ser_z1[a])))

    diff_z0 = paired_ci95(np.array(ser_z0[best_ofdm_z0_name]) - np.array(ser_z0["Prop_BeamMatchedDualISAC_AFDM"]))
    diff_z1 = paired_ci95(np.array(ser_z1[best_ofdm_z1_name]) - np.array(ser_z1["Prop_BeamMatchedDualISAC_AFDM"]))

    did_mean = diff_z1["mean"] - diff_z0["mean"]
    did_se = float(np.sqrt(diff_z1["se"] ** 2 + diff_z0["se"] ** 2))
    did_ci_low = did_mean - 1.96 * did_se
    did_ci_hw = 1.96 * did_se

    log_rat_ofdm = paired_ci95(np.log(np.maximum(ser_z1[best_ofdm_z1_name], 1e-5) / np.maximum(ser_z1["Prop_BeamMatchedDualISAC_AFDM"], 1e-5)))
    geom_ratio_ofdm = {
        "geom_mean": float(np.exp(log_rat_ofdm["mean"])),
        "ci95_low": float(np.exp(log_rat_ofdm["ci95_low"])),
        "ci95_high": float(np.exp(log_rat_ofdm["ci95_high"])),
        "log_half_width": log_rat_ofdm["ci95_half_width"],
    }

    cross_snr_2db = paired_ci95(np.array(ser_z1[best_ofdm_z1_name]) - np.array(ser_z1["Prop_BeamMatchedDualISAC_AFDM_26dB"]))

    rivals_afdm = ["Liu26_PerBinWMMSE_Aged_AFDM", "ExtrapBlockRZF_Aged_AFDM", "DDAM_CleanFullEq_AFDM"]
    rival_diffs = {rv: paired_ci95(np.array(ser_z1[rv]) - np.array(ser_z1["Prop_BeamMatchedDualISAC_AFDM"])) for rv in rivals_afdm}

    blind_pd_diff_q2 = newcombe_paired_binary_ci95(bhits_z1["Prop_BeamMatchedDualISAC_AFDM"], bhits_z1["ExtrapBlockRZF_Short8xQ2_AFDM"])

    rec_aonly = bootstrap_recovery_ci95(ser_z1["ExtrapBlockRZF_Aged_AFDM"], ser_z1["Abl_Aonly_PathNull_NoTrack_AFDM"], ser_z1["Prop_BeamMatchedDualISAC_AFDM"])
    rec_bonly = bootstrap_recovery_ci95(ser_z1["ExtrapBlockRZF_Aged_AFDM"], ser_z1["Abl_Bonly_MRT_WithTrack_AFDM"], ser_z1["Prop_BeamMatchedDualISAC_AFDM"])
    aonly_gap = paired_ci95(np.array(ser_z1["Abl_Aonly_PathNull_NoTrack_AFDM"]) - np.array(ser_z1["Prop_BeamMatchedDualISAC_AFDM"]))
    bonly_gap = paired_ci95(np.array(ser_z1["Abl_Bonly_MRT_WithTrack_AFDM"]) - np.array(ser_z1["Prop_BeamMatchedDualISAC_AFDM"]))

    # Red-line hygiene checks (including Abl_Aonly_PathNull_NoTrack_AFDM in Z=0 static check!):
    clean_full_arms = [
        "Prop_BeamMatchedDualISAC_AFDM",
        "OFDM_Comb_JointWLS_DualISAC",
        "OFDM_HillClimb_JointWLS_ISAC",
        "OFDM_ExtrapBlockRZF",
        "Liu26_PerBinWMMSE_Aged_AFDM",
        "ExtrapBlockRZF_Aged_AFDM",
        "DDAM_CleanFullEq_AFDM",
        "Abl_Aonly_PathNull_NoTrack_AFDM",
    ]
    z0_max_ser = max(float(np.mean(ser_z0[a])) for a in clean_full_arms)
    z0_hygiene_ok = bool(z0_max_ser < 0.010)
    prop_val_pfa_b = rad_z1["Prop_BeamMatchedDualISAC_AFDM"]["val_pfa_blind"]
    pfa_hygiene_ok = bool(0.015 <= prop_val_pfa_b <= 0.095) if not args.smoke else True

    # Red Line 5 realized 95% CI half-width <= 25% of threshold distance checks:
    hw_p1_checks = {
        "did_hw_ok": bool(did_ci_hw <= 0.25 * 0.080),
        "geom_log_hw_ok": bool(geom_ratio_ofdm["log_half_width"] <= min(0.25 * np.log(3.20), np.log(1.25))),
        "cross_snr_2db_hw_ok": bool(cross_snr_2db["ci95_half_width"] <= 0.25 * 0.050),
    }
    hw_p2_checks = {
        "rivals_hw_ok": bool(all(rival_diffs[rv]["ci95_half_width"] <= 0.25 * 0.150 for rv in rivals_afdm)),
        "blind_pd_hw_ok": bool(blind_pd_diff_q2["ci95_half_width"] <= 0.25 * 0.55),
        "rec_aonly_hw_ok": bool(rec_aonly["ci95_half_width"] <= 0.25 * 0.20),
        "rec_bonly_hw_ok": bool(rec_bonly["ci95_half_width"] <= 0.25 * 0.20),
        "aonly_gap_hw_ok": bool(aonly_gap["ci95_half_width"] <= 0.25 * 0.080),
        "bonly_gap_hw_ok": bool(bonly_gap["ci95_half_width"] <= 0.25 * 0.080),
    }
    p1_hw_all_ok = bool(all(hw_p1_checks.values())) if not args.smoke else True
    p2_hw_all_ok = bool(all(hw_p2_checks.values())) if not args.smoke else True

    p1_pass = bool(
        z0_hygiene_ok
        and pfa_hygiene_ok
        and p1_hw_all_ok
        and (did_ci_low >= 0.080)
        and (geom_ratio_ofdm["ci95_low"] >= 3.20)
        and (cross_snr_2db["ci95_low"] >= 0.050)
    )
    p2_pass = bool(
        z0_hygiene_ok
        and pfa_hygiene_ok
        and p2_hw_all_ok
        and all(rival_diffs[rv]["ci95_low"] >= 0.150 for rv in rivals_afdm)
        and (blind_pd_diff_q2["ci95_low"] >= 0.55)
        and (rec_aonly["ci95_high"] < 0.80)
        and (rec_bonly["ci95_high"] < 0.80)
        and (aonly_gap["ci95_low"] >= 0.080)
        and (bonly_gap["ci95_low"] >= 0.080)
    )
    pass_primary = bool(p1_pass and p2_pass)

    summary = {
        "card_id": "I-20261125-h02",
        "python_executable": sys.executable,
        "workers": args.workers,
        "elapsed_sec": round(time.perf_counter() - t_start, 2),
        "smoke_mode": args.smoke,
        "red_line_1_invariants": rl1_info,
        "hygiene": {
            "z0_max_baseline_ser": z0_max_ser,
            "z0_all_below_1pct": z0_hygiene_ok,
            "prop_z1_val_pfa_blind": prop_val_pfa_b,
            "pfa_hygiene_ok": pfa_hygiene_ok,
            "p1_hw_checks": hw_p1_checks,
            "p2_hw_checks": hw_p2_checks,
        },
        "z0_static_28dB": {
            "ser": {a: paired_ci95(ser_z0[a]) for a in ser_z0},
            "radar": rad_z0,
            "best_ofdm_arm": best_ofdm_z0_name,
        },
        "z1_dynamic_28dB": {
            "ser": {a: paired_ci95(ser_z1[a]) for a in ser_z1},
            "radar": rad_z1,
            "best_ofdm_arm": best_ofdm_z1_name,
        },
        "primary_criteria": {
            "P1": {
                "pass": p1_pass,
                "did_ser_vs_best_ofdm": {"mean": did_mean, "se": did_se, "ci95_low": did_ci_low, "ci95_half_width": did_ci_hw, "max_hw_25pct": 0.020, "threshold": 0.080},
                "geom_ratio_vs_best_ofdm_28dB": {**geom_ratio_ofdm, "max_log_hw_25pct": float(min(0.25 * np.log(3.20), np.log(1.25))), "threshold": 3.20},
                "cross_snr_2db_headroom_ofdm28_minus_prop26": {**cross_snr_2db, "max_hw_25pct": 0.0125, "threshold": 0.050},
            },
            "P2": {
                "pass": p2_pass,
                "rival_afdm_ser_diffs": rival_diffs,
                "loc_blind_pd_diff_q16_minus_short8xq2": {**blind_pd_diff_q2, "max_hw_25pct": 0.1375, "threshold": 0.55},
                "ablation_recovery_aonly": {**rec_aonly, "max_hw_25pct": 0.050, "threshold_upper": 0.80},
                "ablation_recovery_bonly_mrt": {**rec_bonly, "max_hw_25pct": 0.050, "threshold_upper": 0.80},
                "aonly_minus_prop_ser": {**aonly_gap, "max_hw_25pct": 0.020, "threshold": 0.080},
                "bonly_minus_prop_ser": {**bonly_gap, "max_hw_25pct": 0.020, "threshold": 0.080},
            },
        },
        "scope_readouts": {
            "pure_aging_isolation_z1": {
                "ExtrapBlockRZF_UnagedQ0_AFDM": paired_ci95(ser_z1["ExtrapBlockRZF_UnagedQ0_AFDM"]),
                "ExtrapBlockRZF_Aged_AFDM": paired_ci95(ser_z1["ExtrapBlockRZF_Aged_AFDM"]),
                "Prop_BeamMatchedDualISAC_AFDM": paired_ci95(ser_z1["Prop_BeamMatchedDualISAC_AFDM"]),
            },
            "nt16_k4_snr26dB": {a: paired_ci95(ser_s2[a]) for a in ser_s2},
        },
        "verdicts": {
            "P1": p1_pass,
            "P2": p2_pass,
            "PASS_PRIMARY": pass_primary,
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSaved JSON summary to {args.out} | verdicts={summary['verdicts']}", flush=True)


if __name__ == "__main__":
    main()
