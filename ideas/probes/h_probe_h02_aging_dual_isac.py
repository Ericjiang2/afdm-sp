#!/usr/bin/env python3
"""
L1 Probe for Candidate I-20261125-h02 ([高要求] [轨B-ISAC], §4 B1):
Path-Decoupled Spatial Precoding & Co-Located Beam-Matched Superposed ISAC Pilot
for Multi-Block Coherent-CPI TDD MIMO-AFDM ISAC under Channel Aging.

Paper-Figure Grounding:
  1. Rang Liu, Ming Li, A. L. Swindlehurst, N. Franchi & R. Schober, arXiv:2607.05119 (Jul. 2026), Sec. II-V:
     Monostatic multiuser MIMO-AFDM ISAC over Q = 16 blocks, N = 64, K = 3 users at {-45, -10, +20} deg,
     Pk = 3 paths/user, target at theta_t = 40 deg.
  2. Shuntian Tang, X. Wang, Shuangyang Li, T. Mao, Zilong Liu & Z. Fei, IEEE TWC 2026 (10.1109/twc.2026.3692638)
     & arXiv:2609.09644 Table I: Two-stage TDD uplink CSI acquisition -> downlink AFDM precoding,
     N = 64, P = 3, l_max = 2, alpha_max = 1.
  3. H. Lu & Y. Zeng, IEEE TWC 2024 (10.1109/TWC.2024.3349425) / Z. Xiao, Y. Zeng et al., ICC 2023:
     Delay-Doppler Alignment Modulation (DDAM) mother method ported to AFDM (nulling all other paths (j,p') != (k,p)).
"""
import os
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_k] = "1"
import time
import numpy as np

t0 = time.perf_counter()

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


# Red Line 1 Check: Exact unitary & operator reconstruction < 1e-13
_E_chk = make_E_op(A_af, c1_af, 2, 0.63)
assert np.linalg.norm(_E_chk @ _E_chk.conj().T - np.eye(N)) < 1e-13

# Equal 40/64 net payload (62.5%) + 24/64 ISAC pilot+guard across ALL AFDM & OFDM arms:
N_data = 40
m_p_af = 10
obs_af = np.arange(0, 13)
D_af = np.arange(22, 62)

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
assert len(D_of_comb) == N_data and len(D_of_hc) == N_data

P_tot = float(N)
E_pilot = (24.0 / 64.0) * P_tot
P_comm = (40.0 / 64.0) * P_tot
E_u_pil_fixed = 0.55 * E_pilot / float(K)  # Fixed deterministic per-user pilot energy known a priori to all users!
SC_DATA_K = np.sqrt(P_comm / float(K * N_data))
theta_tar = 40.0
user_nom_degs = [-45.0, -10.0, 20.0]

NU_GRID_S1 = np.linspace(-1.0, 1.0, 81)
TH_GRID_S1 = np.linspace(-65.0, 65.0, 521)
A_GRID_S1 = np.array([steering_ula(Nt, tg) for tg in TH_GRID_S1])

NU_CAND_RX = np.linspace(-0.96, 0.96, 49)
XP_U_AF = np.zeros(N, dtype=complex); XP_U_AF[m_p_af] = np.sqrt(E_u_pil_fixed)
E_RX_AF_BANK = [[make_E_op(A_af, c1_af, el, float(nc)) @ XP_U_AF for nc in NU_CAND_RX] for el in [0, 1, 2]]


def make_ofdm_rx_bank(P_tones):
    Lr = len(P_tones)
    zc = np.exp(-1j * np.pi * np.arange(Lr) * (np.arange(Lr) + 1) / float(Lr))
    xp_u = np.zeros(N, dtype=complex); xp_u[P_tones] = np.sqrt(E_u_pil_fixed / float(Lr)) * zc
    return zc, xp_u, [[make_E_op(F_of, 0.0, el, float(nc)) @ xp_u for nc in NU_CAND_RX] for el in [0, 1, 2]]


ZC_COMB, XP_U_COMB, BANK_RX_COMB = make_ofdm_rx_bank(P_of_comb)
ZC_HC, XP_U_HC, BANK_RX_HC = make_ofdm_rx_bank(P_of_hc)


def stage1_real_uplink_sounding(users, is_dyn, sig2_ul, rng):
    """Real Stage-1 uplink sounding reception & blind estimation (ZERO oracle leaks!)."""
    m_uls = [10, 31, 52]
    E_ul_k = float(N)
    Y_ul = np.sqrt(sig2_ul / 2.0) * (rng.standard_normal((N, Nt)) + 1j * rng.standard_normal((N, Nt)))
    for k in range(K):
        x_ul = np.zeros(N, dtype=complex); x_ul[m_uls[k]] = np.sqrt(E_ul_k)
        for (el, _, _, s_als, s_nus, s_ths) in users[k]:
            for m in range(M_sub):
                b_m1 = s_als[m] * np.exp(-1j * 2 * np.pi * (s_nus[m] if is_dyn else 0.0) * Tsym)
                y_ray = b_m1 * (make_E_op(A_af, c1_af, el, s_nus[m] if is_dyn else 0.0) @ x_ul)
                Y_ul += y_ray[:, None] * steering_ula(Nt, s_ths[m])[None, :]

    nu_list = NU_GRID_S1 if is_dyn else np.array([0.0])
    est_all = []
    used_bins = np.zeros(N, dtype=bool)
    for k in range(K):
        x_ul = np.zeros(N, dtype=complex); x_ul[m_uls[k]] = np.sqrt(E_ul_k)
        u_est = []
        for el in [0, 1, 2]:
            center = (m_uls[k] - 4 * el) % N
            win = np.arange(center - 2, center + 3) % N
            used_bins[win] = True
            Y_w = Y_ul[win, :]
            th_hat = float(TH_GRID_S1[int(np.argmax(np.sum(np.abs(Y_w @ A_GRID_S1.conj().T) ** 2, axis=0)))])
            y_beam = (Y_w @ steering_ula(Nt, th_hat).conj()) / float(Nt)
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
    sig2_ul_hat = max(float(np.mean(np.abs(Y_ul[~used_bins]) ** 2)), 1e-5)
    return est_all, sig2_ul_hat


def design_beam_matched_dual_isac(Nt_v, est_s1, sig2_h):
    """
    1) Path-Decoupled Spatial User Beams W_k[k]:
       Suppresses all other users' path sectors {th_{j,p}}_{j != k} (making MUI invariant to arbitrary phase aging!),
       while aligning phases across user k's Pk = 3 paths to illuminate ALL 3 paths strongly (full 3-order DAFT diversity!).
    2) Co-Located User-Nulling Radar Pilot Beam w_tar + Superposed Pilot Vector s_pil_vec:
       w_tar steers toward theta_tar while nulling ALL K*Pk = 9 user path angles so radar illumination NEVER leaks into
       user pilot windows! Solved via exact quadratic root so ||alpha_rad * w_tar + sum_k sqrt(E_u_pil_fixed)*W_k[k]||_2^2 == E_pilot,
       keeping each user's pilot amplitude EXACTLY sqrt(E_u_pil_fixed) with ZERO downlink control overhead!
    """
    dths = [-0.9, 0.0, 0.9]
    Wk = np.zeros((K, Nt_v), dtype=complex)
    for k in range(K):
        Ri = max(K * sig2_h / P_comm, 1e-4) * np.eye(Nt_v, dtype=complex)
        for j in range(K):
            if j == k:
                continue
            for (_, th_j, _, al_j) in est_s1[j]:
                Asp = sum(np.outer(steering_ula(Nt_v, th_j + dt), steering_ula(Nt_v, th_j + dt).conj()) for dt in dths) / 3.0
                Ri += 120.0 * (abs(al_j) ** 2 + 0.03) * Asp
        L = np.linalg.cholesky(np.linalg.inv(Ri))
        Ak_c = np.array([steering_ula(Nt_v, th_k).conj() for (_, th_k, _, _) in est_s1[k]])
        Beff = Ak_c @ L
        ph_k = np.zeros(Pk)
        for _ in range(30):
            wc = L @ (Beff.conj().T @ np.exp(1j * ph_k))
            wc /= max(float(np.linalg.norm(wc)), 1e-12)
            ph_k = np.angle(Ak_c @ wc)
        Wk[k] = wc

    R_all_u = 1e-3 * np.eye(Nt_v, dtype=complex)
    for j in range(K):
        for (_, th_j, _, al_j) in est_s1[j]:
            aj = steering_ula(Nt_v, th_j)
            R_all_u += 120.0 * (abs(al_j) ** 2 + 0.03) * np.outer(aj, aj.conj())
    wt = np.linalg.solve(R_all_u, steering_ula(Nt_v, theta_tar))
    wt /= max(float(np.linalg.norm(wt)), 1e-12)

    # Exact total pilot energy E_pilot with fixed deterministic user pilot amplitude sqrt(E_u_pil_fixed):
    v_u = sum(np.sqrt(E_u_pil_fixed) * Wk[k] for k in range(K))
    # Solve ||alpha * wt * exp(j*psi) + v_u||^2 == E_pilot with phase psi aligned so Re(exp(-j*psi) wt^H v_u) >= 0:
    inner = np.vdot(wt, v_u)
    wt_aligned = wt * np.exp(1j * np.angle(inner + 1e-15))
    b_re = float(np.abs(inner))
    c_val = float(np.vdot(v_u, v_u).real) - E_pilot
    # alpha^2 + 2*b_re*alpha + c_val = 0:
    disc = max(b_re ** 2 - c_val, 0.0)
    alpha_rad = max(-b_re + np.sqrt(disc), 0.0)
    s_pil_vec = alpha_rad * wt_aligned + v_u
    assert abs(float(np.vdot(s_pil_vec, s_pil_vec).real) - E_pilot) < 1e-9
    return s_pil_vec, Wk


def blind_user_block_rx_afdm(yk):
    """100% BLIND Single-Block User Receiver (AFDM): ONLY inputs 1 received block yk (N,) — ZERO side-info, ZERO control overhead!"""
    nus_h = []
    for el in [0, 1, 2]:
        cb = m_p_af - 4 * el
        wl = np.arange(max(0, cb - 1), min(13, cb + 2))
        bi = max(
            range(len(NU_CAND_RX)),
            key=lambda i: abs(np.vdot(E_RX_AF_BANK[el][i][wl], yk[wl])) ** 2 / max(float(np.vdot(E_RX_AF_BANK[el][i][wl], E_RX_AF_BANK[el][i][wl]).real), 1e-12),
        )
        nb = float(NU_CAND_RX[bi])
        best_sc = abs(np.vdot(E_RX_AF_BANK[el][bi][wl], yk[wl])) ** 2 / max(float(np.vdot(E_RX_AF_BANK[el][bi][wl], E_RX_AF_BANK[el][bi][wl]).real), 1e-12)
        for nf in np.linspace(nb - 0.04, nb + 0.04, 7):
            v = (make_E_op(A_af, c1_af, el, float(nf)) @ XP_U_AF)[wl]
            sc = abs(np.vdot(v, yk[wl])) ** 2 / max(float(np.vdot(v, v).real), 1e-12)
            if sc > best_sc:
                best_sc, nb = sc, float(nf)
        nus_h.append(nb)

    Eops = [make_E_op(A_af, c1_af, el, nus_h[el]) for el in [0, 1, 2]]
    Phi = np.column_stack([(Eops[el] @ XP_U_AF)[obs_af] for el in [0, 1, 2]])
    gh = np.linalg.solve(Phi.conj().T @ Phi + 1e-6 * np.eye(3), Phi.conj().T @ yk[obs_af])
    sig2_b = max(float(np.mean(np.abs(yk[obs_af] - Phi @ gh) ** 2)), 1e-5)
    yd = yk - sum(gh[el] * (Eops[el] @ XP_U_AF) for el in [0, 1, 2])
    Gk = SC_DATA_K * sum(gh[el] * Eops[el][:, D_af] for el in [0, 1, 2])
    GhG = Gk.conj().T @ Gk
    Minv = np.linalg.inv(GhG + sig2_b * np.eye(N_data))
    dku = (Minv @ (Gk.conj().T @ yd)) / np.maximum(np.real(np.diag(Minv @ GhG)), 1e-8)
    return pts16[np.argmin(np.abs(dku[:, None] - pts16[None, :]), axis=1)]


def blind_user_block_rx_ofdm(yk, xp_u_of, bank_rx_of, G_tones, D_tones):
    """100% Symmetric BLIND Single-Block User Receiver (OFDM): identical Doppler search + exact full-N LMMSE!"""
    r_rem = yk[G_tones].copy()
    nus_h = []
    for el in [0, 1, 2]:
        bi = max(
            range(len(NU_CAND_RX)),
            key=lambda i: abs(np.vdot(bank_rx_of[el][i][G_tones], r_rem)) ** 2 / max(float(np.vdot(bank_rx_of[el][i][G_tones], bank_rx_of[el][i][G_tones]).real), 1e-12),
        )
        bv = bank_rx_of[el][bi][G_tones]
        r_rem = r_rem - (np.vdot(bv, r_rem) / max(float(np.vdot(bv, bv).real), 1e-12)) * bv
        nus_h.append(float(NU_CAND_RX[bi]))

    Eops = [make_E_op(F_of, 0.0, el, nus_h[el]) for el in [0, 1, 2]]
    Phi = np.column_stack([(Eops[el] @ xp_u_of)[G_tones] for el in [0, 1, 2]])
    gh = np.linalg.solve(Phi.conj().T @ Phi + 1e-6 * np.eye(3), Phi.conj().T @ yk[G_tones])
    sig2_b = max(float(np.mean(np.abs(yk[G_tones] - Phi @ gh) ** 2)), 1e-5)
    yd = yk - sum(gh[el] * (Eops[el] @ xp_u_of) for el in [0, 1, 2])
    Gk = SC_DATA_K * sum(gh[el] * Eops[el][:, D_tones] for el in [0, 1, 2])
    GhG = Gk.conj().T @ Gk
    Minv = np.linalg.inv(GhG + sig2_b * np.eye(N_data))
    dku = (Minv @ (Gk.conj().T @ yd)) / np.maximum(np.real(np.diag(Minv @ GhG)), 1e-8)
    return pts16[np.argmin(np.abs(dku[:, None] - pts16[None, :]), axis=1)]


F_RAD_GRID = np.linspace(0.14, 0.38, 33)
N_RAD_RANGE = 6


def unified_monostatic_rd_score(Y_rad_cpi, S_tot_cpi, U_mat, c1_v, is_dyn, win_center, call_log, role):
    """
    SINGLE UNIFIED MONOSTATIC RADAR SCORING FUNCTION across cal, val, pos!
    Implements Rule 6 ExactSubspaceBLUE known-transmit-waveform clutter subspace orthogonal projection
    over clutter delays ell=0..5 and 5 Chebyshev/equispaced slow-time clutter modes in [-0.035, +0.035].
    """
    call_log[role] = call_log.get(role, 0) + 1
    q_len = Y_rad_cpi.shape[0]
    ar_t = steering_ula(Nr_rad, theta_tar)
    at_t = steering_ula(Nt, theta_tar)
    Y_beam = (Y_rad_cpi @ ar_t.conj()) / np.sqrt(float(Nr_rad))

    clut_cols = []
    fn_clut = np.linspace(-0.035, 0.035, 5) if is_dyn else [0.0]
    S_flat = S_tot_cpi.reshape(q_len * N, Nt)
    _, sv_s, Vh_s = np.linalg.svd(S_flat, full_matrices=False)
    n_sp = min(6, int(np.sum(sv_s > 0.02 * sv_s[0])))
    U_sp_modes = (S_flat @ Vh_s[:n_sp].conj().T).reshape(q_len, N, n_sp)
    q_idx = np.arange(q_len)[:, None]
    for il in range(N_RAD_RANGE):
        for fnc in fn_clut:
            Ec = make_E_op(U_mat, c1_v, il, float(fnc))
            ph_q = np.exp(1j * 2 * np.pi * float(fnc) * q_idx * Tsym)
            for isp in range(n_sp):
                clut_cols.append((ph_q * (U_sp_modes[:, :, isp] @ Ec.T)).ravel())
    B_clut = np.column_stack(clut_cols)
    Qb, Rb = np.linalg.qr(B_clut, mode="reduced")
    diag_r = np.abs(np.diag(Rb))
    Qb = Qb[:, diag_r > 1e-7 * max(float(np.max(diag_r)), 1e-12)]
    y_vec = Y_beam.ravel()
    y_proj = (y_vec - Qb @ (Qb.conj().T @ y_vec)).reshape(q_len, N)

    u_tx = S_tot_cpi @ at_t.conj()
    templates = np.zeros((len(F_RAD_GRID), N_RAD_RANGE, q_len, N), dtype=complex)
    for il in range(N_RAD_RANGE):
        for jf, fc in enumerate(F_RAD_GRID):
            El = make_E_op(U_mat, c1_v, il, fc if is_dyn else 0.0)
            Tc = (np.exp(1j * 2 * np.pi * fc * np.arange(q_len)[:, None] * Tsym) * (u_tx @ El.T)).ravel()
            Tp = Tc - Qb @ (Qb.conj().T @ Tc)
            nrm = np.sqrt(max(float(np.vdot(Tp, Tp).real), 1e-18))
            templates[jf, il] = (Tp / nrm).reshape(q_len, N)

    sc0 = np.abs(np.einsum("flqn,qn->fl", templates.conj(), y_proj)) ** 2
    j_dom, l_dom = np.unravel_index(int(np.argmax(sc0)), sc0.shape)
    f0 = float(F_RAD_GRID[j_dom])
    best_Tp, best_sc_f = templates[j_dom, l_dom], -1.0
    for ff in np.linspace(f0 - 0.012, f0 + 0.012, 13):
        El = make_E_op(U_mat, c1_v, int(l_dom), float(ff) if is_dyn else 0.0)
        Tc = (np.exp(1j * 2 * np.pi * float(ff) * np.arange(q_len)[:, None] * Tsym) * (u_tx @ El.T)).ravel()
        Tp = Tc - Qb @ (Qb.conj().T @ Tc)
        Tp /= np.sqrt(max(float(np.vdot(Tp, Tp).real), 1e-18))
        sc_c = abs(np.vdot(Tp, y_proj.ravel())) ** 2
        if sc_c > best_sc_f:
            best_sc_f, best_Tp = sc_c, Tp.reshape(q_len, N)
    y_clean = y_proj - np.vdot(best_Tp, y_proj) * best_Tp

    rd_map = np.abs(np.einsum("flqn,qn->fl", templates.conj(), y_clean)) ** 2
    ray_pts = max(7, int(np.ceil((1.0 / (q_len * Tsym)) / ((F_RAD_GRID[-1] - F_RAD_GRID[0]) / (len(F_RAD_GRID) - 1)))))
    mask_valid = np.ones_like(rd_map, dtype=bool)
    mask_valid[max(0, j_dom - ray_pts):min(len(F_RAD_GRID), j_dom + ray_pts + 1), l_dom] = False

    jw, lw = win_center
    win_peak = float(np.max(rd_map[max(0, jw - 1):min(len(F_RAD_GRID), jw + 2), lw]))
    mask_bg_w = mask_valid.copy()
    mask_bg_w[max(0, jw - 3):min(len(F_RAD_GRID), jw + 4), lw] = False
    bg_w = max(float(np.mean(rd_map[mask_bg_w])), 1e-20)

    rd_blind = np.where(mask_valid, rd_map, -1.0)
    j_pk, l_pk = np.unravel_index(int(np.argmax(rd_blind)), rd_map.shape)
    blind_peak = float(rd_map[j_pk, l_pk])
    mask_bg_b = mask_valid.copy()
    mask_bg_b[max(0, j_pk - 3):min(len(F_RAD_GRID), j_pk + 4), l_pk] = False
    bg_b = max(float(np.mean(rd_map[mask_bg_b])), 1e-20)
    return win_peak / bg_w, blind_peak / bg_b, (int(j_pk), int(l_pk))


def run_probe_regime(nu_max, sig_nu_sub, sig_th_sub, snr_db=28.0, n_cal=25, n_val=25, n_pos=16, seed0=10000):
    sig2_c = 10.0 ** (-snr_db / 10.0)
    sig2_r = 10.0 ** (-20.0 / 10.0)
    clut_pow = 10.0 ** (+35.0 / 10.0) * sig2_r
    strong_pow = 10.0 ** (+22.0 / 10.0) * sig2_r
    tar_pow = 10.0 ** (-3.0 / 10.0) * sig2_r
    is_dyn = (nu_max > 0 or sig_nu_sub > 0)

    arms = [
        "Prop_BeamMatchedDualISAC_AFDM",
        "Liu26_Tang26_ExtrapWMMSE_AFDM",
        "Liu26_ShortCPI_Q2_AFDM",
        "DDAM_DelayDopplerAlign_AFDM",
        "Abl_Aonly_PathNull_NoTrack_AFDM",
        "Abl_Bonly_Extrap_WithTrack_AFDM",
        "OFDM_ExtrapWMMSE",
        "OFDM_Comb_BeamMatchedDualISAC",
        "OFDM_HillClimb_BeamMatchedISAC",
    ]

    ell_s, nu_s = 0, 0.335
    ell_tar, nu_tar = 2, 0.175
    jw_true = int(np.argmin(np.abs(F_RAD_GRID - nu_tar)))
    win_center = (jw_true, ell_tar)
    call_log = {}

    def sim_split(n_tr, has_tar, role, s_off):
        w_sc = {a: [] for a in arms}
        b_sc = {a: [] for a in arms}
        b_lc = {a: [] for a in arms}
        sers = {a: [] for a in arms}

        for i in range(n_tr):
            rng = np.random.default_rng(seed0 + s_off + i)
            users = []
            for k in range(K):
                ells = np.array([0, 1, 2])
                base_offs = np.array([-5.0, 0.0, 5.0]) + rng.uniform(-1.2, 1.2, size=Pk)
                ths_c = user_nom_degs[k] + base_offs
                nus_c = rng.uniform(-nu_max, nu_max, size=Pk)
                clusters = []
                for p in range(Pk):
                    s_als = (rng.standard_normal(M_sub) + 1j * rng.standard_normal(M_sub)) / np.sqrt(2.0 * Pk * M_sub)
                    s_nus = nus_c[p] + rng.normal(0.0, sig_nu_sub, size=M_sub)
                    s_ths = ths_c[p] + rng.normal(0.0, sig_th_sub, size=M_sub)
                    clusters.append((ells[p], ths_c[p], nus_c[p], s_als, s_nus, s_ths))
                users.append(clusters)

            est_s1, sig2_ul_hat = stage1_real_uplink_sounding(users, is_dyn, sig2_c, rng)
            s_pil_vec, W_beams = design_beam_matched_dual_isac(Nt, est_s1, sig2_ul_hat)

            if role == "pos":
                E_true_af = [[[make_E_op(A_af, c1_af, el, s_nus[m] if is_dyn else 0.0) for m in range(M_sub)] for (el, _, _, _, s_nus, _) in users[k]] for k in range(K)]
                E_true_of = [[[make_E_op(F_of, 0.0, el, s_nus[m] if is_dyn else 0.0) for m in range(M_sub)] for (el, _, _, _, s_nus, _) in users[k]] for k in range(K)]
            E_est_af = [[make_E_op(A_af, c1_af, el, nu_h) for (el, _, nu_h, _) in est_s1[k]] for k in range(K)]
            E_est_of = [[make_E_op(F_of, 0.0, el, nu_h) for (el, _, nu_h, _) in est_s1[k]] for k in range(K)]

            d_16 = rng.choice(pts16, size=(Q, K, N_data))
            noise_u = np.sqrt(sig2_c / 2.0) * (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N)))
            noise_r = np.sqrt(sig2_r / 2.0) * (rng.standard_normal((Q, N, Nr_rad)) + 1j * rng.standard_normal((Q, N, Nr_rad)))

            c_ells = [0, 1, 3, 5]
            c_degs = [-30.0, 5.0, 38.0, 50.0]
            c_gains = np.sqrt(clut_pow / 4.0 / 2.0) * (rng.standard_normal(4) + 1j * rng.standard_normal(4))
            c_nus = rng.uniform(-0.03, 0.03, size=4) if is_dyn else np.zeros(4)
            g_s = np.sqrt(strong_pow) * np.exp(1j * rng.uniform(0, 2 * np.pi))
            g_t = (np.sqrt(tar_pow) * np.exp(1j * rng.uniform(0, 2 * np.pi))) if has_tar else 0.0

            for arm in arms:
                is_ofdm = arm.startswith("OFDM")
                q_cpi = 2 if arm == "Liu26_ShortCPI_Q2_AFDM" else Q
                U_m = F_of if is_ofdm else A_af
                c1_v = 0.0 if is_ofdm else c1_af
                E_es = E_est_of if is_ofdm else E_est_af
                if arm == "OFDM_HillClimb_BeamMatchedISAC":
                    Pt, Gt, Dt, zc_o, xpu_o, b_rx_o = P_of_hc, G_of_hc, D_of_hc, ZC_HC, XP_U_HC, BANK_RX_HC
                elif is_ofdm:
                    Pt, Gt, Dt, zc_o, xpu_o, b_rx_o = P_of_comb, G_of_comb, D_of_comb, ZC_COMB, XP_U_COMB, BANK_RX_COMB
                else:
                    Pt, Gt, Dt, zc_o, xpu_o, b_rx_o = np.array([m_p_af]), obs_af, D_af, None, None, None

                S_pil = np.zeros((N, Nt), dtype=complex)
                if not is_ofdm:
                    S_pil[m_p_af, :] = s_pil_vec
                else:
                    S_pil[Pt, :] = (zc_o / np.sqrt(float(len(Pt))))[:, None] * s_pil_vec[None, :]

                S_tot_cpi = np.zeros((q_cpi, N, Nt), dtype=complex)
                U_rx_save, beta_save, W_raw_save = [], [], []

                if arm == "DDAM_DelayDopplerAlign_AFDM":
                    W_ddam = [[None] * Pk for _ in range(K)]
                    for k in range(K):
                        for p, (_, th_k, _, _) in enumerate(est_s1[k]):
                            R_i = max(K * sig2_ul_hat / P_comm, 1e-4) * np.eye(Nt, dtype=complex)
                            for j in range(K):
                                for p2, (_, th2, _, al2) in enumerate(est_s1[j]):
                                    if j == k and p2 == p:
                                        continue
                                    R_i += 80.0 * (abs(al2) ** 2 + 0.03) * np.outer(steering_ula(Nt, th2), steering_ula(Nt, th2).conj())
                            v = np.linalg.solve(R_i, steering_ula(Nt, th_k))
                            W_ddam[k][p] = v / max(float(np.linalg.norm(v)), 1e-12)

                for q in range(q_cpi):
                    if arm in ("Liu26_Tang26_ExtrapWMMSE_AFDM", "Liu26_ShortCPI_Q2_AFDM", "Abl_Bonly_Extrap_WithTrack_AFDM", "OFDM_ExtrapWMMSE"):
                        H_rows, U_rx_e = [], []
                        for k in range(K):
                            Hk_f = np.zeros((N, N_data * Nt), dtype=complex)
                            Hk_su = np.zeros((N, N_data), dtype=complex)
                            for p, (el, th_h, nu_h, al_m1) in enumerate(est_s1[k]):
                                bq_h = al_m1 * np.exp(1j * 2 * np.pi * nu_h * (q + 1) * Tsym)
                                Ec = E_es[k][p][:, Dt]
                                at = steering_ula(Nt, th_h)
                                Hk_f += bq_h * np.kron(Ec, at.conj()[None, :])
                                Hk_su += bq_h * (at.conj() @ W_beams[k]) * Ec
                            Qk, _ = np.linalg.qr(Hk_su)
                            U_rx_e.append(Qk)
                            H_rows.append(Qk.conj().T @ Hk_f)
                        H_all = np.vstack(H_rows)
                        reg_i = K * N_data * sig2_ul_hat / P_comm
                        W_raw = H_all.conj().T @ np.linalg.inv(H_all @ H_all.conj().T + reg_i * np.eye(K * N_data))
                        s_raw = W_raw @ d_16[q].ravel()
                        beta = np.sqrt(P_comm / max(float(np.sum(np.abs(s_raw) ** 2)), 1e-12))
                        S_tot_cpi[q] = S_pil.copy()
                        S_tot_cpi[q, Dt, :] += (beta * s_raw).reshape(N_data, Nt)
                        U_rx_save.append(U_rx_e); beta_save.append(beta); W_raw_save.append(W_raw)
                    elif arm == "DDAM_DelayDopplerAlign_AFDM":
                        S_comm = np.zeros((N, Nt), dtype=complex)
                        for k in range(K):
                            xk_vec = np.zeros(N, dtype=complex)
                            xk_vec[Dt] = d_16[q, k]
                            xk_vec[18] = 1.0
                            for p, (el, th_h, nu_h, al_m1) in enumerate(est_s1[k]):
                                bq_h = al_m1 * np.exp(1j * 2 * np.pi * nu_h * (q + 1) * Tsym)
                                eff_g = bq_h * (steering_ula(Nt, th_h).conj() @ W_ddam[k][p])
                                ph_c = np.exp(-1j * np.angle(eff_g + 1e-12))
                                x_pre = E_es[k][p].conj().T @ xk_vec
                                S_comm += ph_c * x_pre[:, None] * W_ddam[k][p][None, :]
                        S_comm *= np.sqrt(P_comm / max(float(np.sum(np.abs(S_comm) ** 2)), 1e-12))
                        S_tot_cpi[q] = S_pil + S_comm
                    else:
                        S_tot_cpi[q] = S_pil.copy()
                        S_tot_cpi[q, Dt, :] += sum(SC_DATA_K * d_16[q, k][:, None] * W_beams[k][None, :] for k in range(K))

                if role == "pos":
                    E_tr = E_true_of if is_ofdm else E_true_af
                    ser_u = []
                    for k in range(K):
                        Y_k_cpi = noise_u[:q_cpi, k, :].copy()
                        for q in range(q_cpi):
                            for p, (_, _, _, s_als, s_nus, s_ths) in enumerate(users[k]):
                                for m in range(M_sub):
                                    bq = s_als[m] * np.exp(1j * 2 * np.pi * s_nus[m] * q * Tsym)
                                    Y_k_cpi[q] += bq * (E_tr[k][p][m] @ (S_tot_cpi[q] @ steering_ula(Nt, s_ths[m]).conj()))

                        if arm in ("Liu26_Tang26_ExtrapWMMSE_AFDM", "Liu26_ShortCPI_Q2_AFDM", "OFDM_ExtrapWMMSE"):
                            d_hat = np.zeros((q_cpi, N_data), dtype=complex)
                            for q in range(q_cpi):
                                yk_p_h = sum(
                                    (al_m1 * np.exp(1j * 2 * np.pi * nu_h * (q + 1) * Tsym)) * (E_es[k][p] @ (S_pil @ steering_ula(Nt, th_h).conj()))
                                    for p, (_, th_h, nu_h, al_m1) in enumerate(est_s1[k])
                                )
                                zk = (U_rx_save[q][k].conj().T @ (Y_k_cpi[q] - yk_p_h)) / beta_save[q]
                                d_hat[q] = pts16[np.argmin(np.abs(zk[:, None] - pts16[None, :]), axis=1)]
                        elif arm == "DDAM_DelayDopplerAlign_AFDM":
                            d_hat = np.zeros((q_cpi, N_data), dtype=complex)
                            for q in range(q_cpi):
                                # Note: s_pil_vec has zero projection onto user k except W_beams[k]!
                                Phi_d = np.column_stack([(E_es[k][p] @ XP_U_AF)[obs_af] for p in range(Pk)])
                                gp = np.linalg.solve(Phi_d.conj().T @ Phi_d + 1e-6 * np.eye(Pk), Phi_d.conj().T @ Y_k_cpi[q, obs_af])
                                yk_d = Y_k_cpi[q] - sum(gp[p] * (E_es[k][p] @ XP_U_AF) for p in range(Pk))
                                c_hat = yk_d[18]
                                zk = yk_d[Dt] / (c_hat if abs(c_hat) > 1e-4 else 1.0)
                                d_hat[q] = pts16[np.argmin(np.abs(zk[:, None] - pts16[None, :]), axis=1)]
                        elif arm == "Abl_Aonly_PathNull_NoTrack_AFDM":
                            d_hat = np.zeros((q_cpi, N_data), dtype=complex)
                            for q in range(q_cpi):
                                Gk_h = np.zeros((N, N_data), dtype=complex)
                                yk_p_h = np.zeros(N, dtype=complex)
                                for p, (_, th_h, nu_h, al_m1) in enumerate(est_s1[k]):
                                    bq_h = al_m1 * np.exp(1j * 2 * np.pi * nu_h * (q + 1) * Tsym)
                                    at_h = steering_ula(Nt, th_h)
                                    yk_p_h += bq_h * (E_es[k][p] @ (S_pil @ at_h.conj()))
                                    Gk_h += bq_h * SC_DATA_K * (at_h.conj() @ W_beams[k]) * E_es[k][p][:, Dt]
                                GhG = Gk_h.conj().T @ Gk_h
                                Minv = np.linalg.inv(GhG + sig2_ul_hat * np.eye(N_data))
                                mu_u = np.maximum(np.real(np.diag(Minv @ GhG)), 1e-8)
                                dk_u = (Minv @ (Gk_h.conj().T @ (Y_k_cpi[q] - yk_p_h))) / mu_u
                                d_hat[q] = pts16[np.argmin(np.abs(dk_u[:, None] - pts16[None, :]), axis=1)]
                        elif arm == "Abl_Bonly_Extrap_WithTrack_AFDM":
                            d_hat = np.zeros((q_cpi, N_data), dtype=complex)
                            for q in range(q_cpi):
                                Phi_p = np.column_stack([E_es[k][p][obs_af, :] @ (S_pil @ steering_ula(Nt, th_h).conj()) for p, (_, th_h, _, _) in enumerate(est_s1[k])])
                                al_q = np.linalg.solve(Phi_p.conj().T @ Phi_p + 1e-5 * np.eye(Pk), Phi_p.conj().T @ Y_k_cpi[q, obs_af])
                                Wk_m = beta_save[q] * W_raw_save[q][:, k * N_data:(k + 1) * N_data]
                                Gk_tr = np.zeros((N, N_data), dtype=complex)
                                yk_p_tr = np.zeros(N, dtype=complex)
                                for p, (_, th_h, _, _) in enumerate(est_s1[k]):
                                    at_h = steering_ula(Nt, th_h)
                                    yk_p_tr += al_q[p] * (E_es[k][p] @ (S_pil @ at_h.conj()))
                                    Gk_tr += al_q[p] * (np.kron(E_es[k][p][:, Dt], at_h.conj()[None, :]) @ Wk_m)
                                res_p = Y_k_cpi[q, obs_af] - Phi_p @ al_q
                                sig2_b = max(float(np.mean(np.abs(res_p) ** 2)), 1e-5)
                                GhG = Gk_tr.conj().T @ Gk_tr
                                Minv = np.linalg.inv(GhG + sig2_b * np.eye(N_data))
                                mu_u = np.maximum(np.real(np.diag(Minv @ GhG)), 1e-8)
                                dk_u = (Minv @ (Gk_tr.conj().T @ (Y_k_cpi[q] - yk_p_tr))) / mu_u
                                d_hat[q] = pts16[np.argmin(np.abs(dk_u[:, None] - pts16[None, :]), axis=1)]
                        elif not is_ofdm:
                            d_hat = np.array([blind_user_block_rx_afdm(Y_k_cpi[q]) for q in range(q_cpi)])
                        else:
                            d_hat = np.array([blind_user_block_rx_ofdm(Y_k_cpi[q], xpu_o, b_rx_o, Gt, Dt) for q in range(q_cpi)])
                        ser_u.append(float(np.mean(np.abs(d_hat - d_16[:q_cpi, k, :]) > 1e-3)))
                    sers[arm].append(float(np.mean(ser_u)))

                Y_rad_cpi = noise_r[:q_cpi].copy()
                for ic in range(4):
                    Ec = make_E_op(U_m, c1_v, c_ells[ic], c_nus[ic])
                    at_c = steering_ula(Nt, c_degs[ic])
                    ar_c = steering_ula(Nr_rad, c_degs[ic])
                    u_c = (S_tot_cpi @ at_c.conj()) @ Ec.T
                    bq_c = c_gains[ic] * np.exp(1j * 2 * np.pi * c_nus[ic] * np.arange(q_cpi) * Tsym)
                    Y_rad_cpi += (bq_c[:, None] * u_c)[:, :, None] * ar_c[None, None, :]

                at_t = steering_ula(Nt, theta_tar)
                ar_t = steering_ula(Nr_rad, theta_tar)
                Es = make_E_op(U_m, c1_v, ell_s, nu_s if is_dyn else 0.0)
                u_s = (S_tot_cpi @ at_t.conj()) @ Es.T
                bq_s = g_s * np.exp(1j * 2 * np.pi * nu_s * np.arange(q_cpi) * Tsym)
                Y_rad_cpi += (bq_s[:, None] * u_s)[:, :, None] * ar_t[None, None, :]

                if has_tar:
                    Et = make_E_op(U_m, c1_v, ell_tar, nu_tar if is_dyn else 0.0)
                    u_t = (S_tot_cpi @ at_t.conj()) @ Et.T
                    bq_t = g_t * np.exp(1j * 2 * np.pi * nu_tar * np.arange(q_cpi) * Tsym)
                    Y_rad_cpi += (bq_t[:, None] * u_t)[:, :, None] * ar_t[None, None, :]

                ws, bs, bl = unified_monostatic_rd_score(Y_rad_cpi, S_tot_cpi, U_m, c1_v, is_dyn, win_center, call_log, role)
                w_sc[arm].append(ws)
                b_sc[arm].append(bs)
                b_lc[arm].append(bl)
        return w_sc, b_sc, b_lc, sers

    cw, cb, _, _ = sim_split(n_cal, False, "cal", 0)
    vw, vb, _, _ = sim_split(n_val, False, "val", 10000)
    pw, pb, pl, ps = sim_split(n_pos, True, "pos", 20000)

    pfa_t = 0.08
    print(f"\n=== Regime nu_max={nu_max:.2f}, sig_nu={sig_nu_sub:.3f}, sig_th={sig_th_sub:.1f}deg | SNR={snr_db}dB | calls={call_log} ===")
    for a in arms:
        tw = float(np.quantile(cw[a], 1.0 - pfa_t, method="weibull"))
        tb = float(np.quantile(cb[a], 1.0 - pfa_t, method="weibull"))
        vpw = float(np.mean(np.array(vw[a]) > tw))
        vpb = float(np.mean(np.array(vb[a]) > tb))
        wpd = float(np.mean(np.array(pw[a]) > tw))
        bpd = float(np.mean([(pb[a][i] > tb) and (abs(pl[a][i][0] - jw_true) <= 2) and (pl[a][i][1] == ell_tar) for i in range(n_pos)]))
        ser_m = float(np.mean(ps[a]))
        ser_se = float(np.std(ps[a], ddof=1) / np.sqrt(n_pos))
        print(f"  {a:32s} | SER={ser_m:.5f}(+-{ser_se:.5f}) | WinPd={wpd*100:5.1f}%(vPfa={vpw*100:4.1f}%) | LocBlindPd={bpd*100:5.1f}%(vPfa={vpb*100:4.1f}%)")


if __name__ == "__main__":
    run_probe_regime(0.0, 0.0, 0.0, snr_db=28.0, n_cal=25, n_val=25, n_pos=12, seed0=10000)
    run_probe_regime(0.85, 0.025, 0.8, snr_db=28.0, n_cal=25, n_val=25, n_pos=16, seed0=50000)
    print(f"\nTotal L1 probe runtime: {time.perf_counter() - t0:.2f}s")
