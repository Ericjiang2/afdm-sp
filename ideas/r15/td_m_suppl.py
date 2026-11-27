#!/usr/bin/env python3
"""
Round-15 Phase-1 Supplemental Precision Verification Probe (`td_m_suppl.py`):
Directly tests the three subtle scientific audits flagged by `gpt-6.2-sol` Call 2/4:
  1. `26-m01` Horizontal SNR Gap (dB): Measures `Steelman_WL_Anttila_DD6` across SNR sweeps on
     `R2_Strong13_64QAM` (`32..36 dB`, `n=60`) and `R3_ContDop_16QAM` (`28..31 dB`, `n=48`) on the
     exact paired R15 bursts to quantify horizontal dB gap vs `Ours_PropFull` and `Oracle_PhysGold`.
  2. `26-m04` `17 x 15 = 255` Aperiodic-Mask `OTFS` (`c1 = 0`) + Clutter-Present `H0` Check:
     Implements exact unitary `17 x 15 = 255` rectangular `OTFS` (`c1 = 0` standard CP, identical
     `(5/3, 1/3, 1.0)` mask power histogram and `765` bits/block) + Full Wishart QML (`M = 128`),
     verifies population Gram non-singularity, checks clutter-only `H0` (`P=1` strong `0 dB` path,
     no weak target) false alarm rate, and measures `Reg1` & `Reg2` weak-target `Pd` (`n=80` scenes).
  3. `25-m03` `Bell 1994` IEKS vs Banded GN Equivalence & Subband-Init Disentanglement:
     Tests exact Wiener Markov boundary covariance `P0` + DAFT pilot-subband dual-PN init inside
     `Bell 1994` IEKS on `Sep_R3_45dB_Floor` (`n=40`) and `Sep_R4_30dB_SFBlind` (`n=40`).
"""
import os, sys, json, time, math, argparse
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
from scipy.fft import fft, ifft
from scipy.signal.windows import dpss
from scipy.optimize import minimize
from concurrent.futures import ProcessPoolExecutor

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
L2_DIR = os.path.join(REPO_ROOT, "ideas", "l2")
for p in (THIS_DIR, L2_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import l2_m_r13_m01_wideband_iqi as m1
import l2_m_r12_m03_modtest as m3
import l2_m_r13_m04_blind_cov_afdm_isac as m4
import td_m_m01 as tm1
import td_m_m04 as tm4


# ==============================================================================
# Part 1: 26-m01 Horizontal SNR Gap Sweep
# ==============================================================================
def _eval_m01_burst_snr_curve(args):
    seed, lvl, M_qam, snr_grid, cont_doppler = args
    rng = np.random.default_rng(seed)
    N = 256; c1 = 7.0 / (2 * N); c2 = 1.0 / (2 * np.sqrt(2) * N); A = m1.daft_matrix(N, c1, c2)
    delays = [0, 1, 2]; L_eq = 7; Lu = 4
    B_bem = dpss(N, 1.0, 5).T
    guard_obs_idx = np.array([m % N for m in range(-47, 4)])
    data_idx_nom = np.array([m for m in range(48, N - 47)])
    xp_val = np.sqrt(50.0); const, _ = m1.gray_qam_constellation(M_qam)
    rx_cfg = {"A": A, "B_bem": B_bem, "L_eq": L_eq, "Lu": Lu, "data_idx": data_idx_nom,
              "guard_obs_idx": guard_obs_idx, "xp_val": xp_val, "const": const}

    f1, f2, g1, g2 = m1.generate_iqi_filters(rng, lvl, Lf=3, Lg=3)
    dopplers = rng.uniform(-0.85, 0.85, 3)
    gains = (rng.standard_normal(3) + 1j * rng.standard_normal(3)) * np.sqrt(np.array([0.5, 0.3, 0.2]) / 2.0)
    gains /= np.linalg.norm(gains)
    L_cpp = max(delays) + len(f1) + len(g1)

    # Consume exact preamble RNG draws so burst data/noise match td_m_m01.py bit-for-bit!
    _ = rng.integers(0, M_qam, N)
    _ = rng.standard_normal(N + 2); _ = rng.standard_normal(N + 2)
    _ = rng.standard_normal(N + 2); _ = rng.standard_normal(N + 2)
    _ = rng.standard_normal(N + 2); _ = rng.standard_normal(N + 2)

    tx_list_nom = []
    w_unit_list = []
    for k in range(4):
        idx_nom = rng.integers(0, M_qam, len(data_idx_nom))
        w_u = (rng.standard_normal(N + 2) + 1j * rng.standard_normal(N + 2)) / math.sqrt(2.0)
        tx_list_nom.append(idx_nom)
        w_unit_list.append(w_u)

    def mser(xl):
        return float(np.mean([np.mean(m1.qam_hard(xl[k], const)[1] != tx_list_nom[k]) for k in range(4)]))

    pool_H = not cont_doppler
    snr0 = float(snr_grid[0])
    res = {}

    for idx_s, snr_db in enumerate(snr_grid):
        sig2 = 10.0 ** (-float(snr_db) / 10.0)
        r_list = []
        for k in range(4):
            x_nom = np.zeros(N, dtype=complex); x_nom[0] = xp_val; x_nom[data_idx_nom] = const[tx_list_nom[k]]
            t_off = k * (N + L_cpp) if cont_doppler else 0
            r_list.append(m1.phys_transmit_receive(A.conj().T @ x_nom, c1, gains, delays, dopplers,
                                                   f1, f2, g1, g2, math.sqrt(sig2) * w_unit_list[k], t_offset=t_off))
        ant_dd6 = tm1.rx_steelman_anttila_wl(r_list, rx_cfg, pool_H=pool_H, n_outer=6)
        key_s = f"{snr_db:.1f}dB"
        res[f"Anttila_DD6@{key_s}"] = mser(ant_dd6)
        if idx_s == 0:
            xd_pf, _, _, _ = m1.rx_proposed_blind(r_list, rx_cfg, True, True, True, None, pool_H, 6)
            res[f"Ours_PropFull@{key_s}"] = mser(xd_pf[-1])
            xd_gold = []
            for k in range(4):
                t_off = k * (N + L_cpp) if cont_doppler else 0
                H_dir_l, H_img_l, G1_r, G2_r = m1.build_exact_linear_operators(N, c1, gains, delays, dopplers, f1, f2, g1, g2, t_offset=t_off)
                xd_g, _, _ = m1.exact_wl_ep_detect(r_list[k], None, None, None, A, data_idx_nom, xp_val, const, sig2, n_iter=3,
                                                   exact_lin_ops=(H_dir_l, H_img_l, G1_r, G2_r))
                xd_gold.append(xd_g)
            res[f"Oracle_PhysGold@{key_s}"] = mser(xd_gold)
    return res


# ==============================================================================
# Part 2: 26-m04 Rectangular 17x15=255 Aperiodic-Mask OTFS (c1=0) + Clutter H0
# ==============================================================================
def build_otfs_17x15_config(sys_afdm: dict):
    N = 255; K_del = 17; L_dop = 15
    assert K_del * L_dop == N
    # Exact unitary Zak/Heisenberg OTFS modulator U_otfs (N x N):
    # X_dd[k, l] -> s[k + K_del * l_t] = (1/sqrt(L_dop)) sum_l X_dd[k, l] exp(j 2pi l_t l / L_dop)
    U_otfs = np.zeros((N, N), dtype=np.complex128)
    l_idx = np.arange(L_dop, dtype=float)
    F_dop_h = np.exp(1j * 2.0 * np.pi * np.outer(l_idx, l_idx) / float(L_dop)) / math.sqrt(float(L_dop))
    for k in range(K_del):
        rows = k + K_del * np.arange(L_dop)
        cols = k * L_dop + np.arange(L_dop)
        U_otfs[np.ix_(rows, cols)] = F_dop_h
    unit_err = float(np.max(np.abs(U_otfs.conj().T @ U_otfs - np.eye(N))))
    assert unit_err < 1e-13, f"OTFS unitarity error {unit_err}"

    d_otfs = sys_afdm["d"].copy()  # Identical 127*(5/3), 127*(1/3), 1*(1.0) m-sequence mask!
    R_s0 = (U_otfs * d_otfs[None, :]) @ U_otfs.conj().T
    n_idx = np.arange(N)
    R_shifts = []
    for ell in range(17):
        idx_sh = (n_idx - ell) % N
        R_shifts.append(R_s0[np.ix_(idx_sh, idx_sh)])
    return {
        "N": N, "K_del": K_del, "L_dop": L_dop,
        "U_otfs": U_otfs, "A_otfs": U_otfs.conj().T,
        "d": d_otfs, "sqrt_d": np.sqrt(d_otfs),
        "R_shifts": R_shifts, "unitarity_err": unit_err,
    }


def check_otfs_population_identifiability(otfs_cfg: dict):
    N = 255
    n_idx = np.arange(N, dtype=float)
    R_shifts = otfs_cfg["R_shifts"]
    def cov_td(ell: int, nu: float):
        ph = np.exp(1j * 2.0 * np.pi * nu * n_idx / float(N))
        return (ph[:, None] * R_shifts[ell]) * np.conj(ph)[None, :]

    # Check rank & min singular value across 35 random atoms + specifically [0, 7, 16] fractional Dopplers
    rng = np.random.default_rng(2026112699)
    atoms = [np.eye(N, dtype=np.complex128).ravel()]
    test_triples = [(0, 1.37), (7, -2.83), (16, 3.61), (1, -0.45), (8, 2.15), (15, -3.90)]
    for (e, v) in test_triples:
        C = cov_td(e, v)
        atoms.append(C.ravel() / np.linalg.norm(C))
    A_mat = np.column_stack(atoms)
    svals = np.linalg.svd(A_mat, compute_uv=False)
    return {
        "min_singular_value_6paths_plus_noise": float(np.min(svals)),
        "cond_number": float(np.max(svals) / max(np.min(svals), 1e-30)),
    }


def estimate_otfs_full_wishart_qml(R_time: np.ndarray, otfs_cfg: dict, ell_max: int, nu_max: float,
                                   tau_w: float, P_max: int = 5, return_top_stat: bool = False):
    N, M = R_time.shape
    R_shifts = otfs_cfg["R_shifts"]
    n_idx = np.arange(N, dtype=np.float64)

    Zc = R_time - np.mean(R_time, axis=1, keepdims=True)
    rms = float(np.sqrt(np.mean(np.abs(Zc) ** 2)))
    if rms < 1e-15:
        return [], 0.0
    Zn = Zc / rms
    R_td_hat = (Zn @ Zn.conj().T) / float(max(M - 1, 1))

    def td_atom(ell_i: int, nu_v: float) -> np.ndarray:
        ph = np.exp(1j * 2.0 * np.pi * nu_v * n_idx / float(N))
        return (ph[:, None] * R_shifts[ell_i]) * np.conj(ph)[None, :]

    s2_c = max(float(np.real(np.trace(R_td_hat)) / N), 1e-5)
    R_c = s2_c * np.eye(N, dtype=np.complex128)
    L_c = np.linalg.cholesky(R_c)
    nll2_c = float(2.0 * M * (2.0 * np.sum(np.log(np.real(np.diag(L_c)))) + np.real(np.trace(R_td_hat)) / s2_c))

    ells_c, nus_c, gs_c = [], [], []
    first_stat = 0.0
    n_fft = 512
    nu_grid_full = np.fft.fftfreq(n_fft, d=1.0 / float(N))  # [-N/2 .. N/2) -> wait: ifft(lag_vec)*n_fft gives u = m * N / n_fft!
    u_grid = np.arange(n_fft, dtype=float) * (float(N) / float(n_fft))
    nu_signed = ((u_grid + N / 2.0) % N) - N / 2.0
    valid_nu_mask = np.abs(nu_signed) <= nu_max

    for step in range(P_max):
        R_inv = np.linalg.inv(R_c)
        W_res = R_inv @ (R_td_hat - R_c) @ R_inv

        best_ell, best_nu, best_sc = None, None, -1e30
        for ell_i in range(ell_max + 1):
            A_prod = W_res.T * R_shifts[ell_i]
            lag_vec = np.zeros(n_fft, dtype=np.complex128)
            for r in range(-(N - 1), N):
                lag_vec[r % n_fft] += np.sum(np.diag(A_prod, -r))
            rao_spec = np.real(ifft(lag_vec) * n_fft)
            for idx_g in np.where(valid_nu_mask)[0]:
                nv = float(nu_signed[idx_g])
                if any((ed == ell_i and abs(nv - vd) <= 1.0) for ed, vd in zip(ells_c, nus_c)):
                    continue
                if rao_spec[idx_g] > best_sc:
                    best_sc = float(rao_spec[idx_g])
                    best_ell = ell_i
                    best_nu = nv

        if best_ell is None or best_sc <= 0:
            break

        ells_try = ells_c + [best_ell]
        nus_try = nus_c + [best_nu]
        Pp = len(ells_try)
        C_new = td_atom(best_ell, best_nu)
        RC = R_inv @ C_new
        fim_gg = max(float(np.real(np.trace(RC @ RC))), 1e-9)
        g_new0 = max(best_sc / fim_gg, 1e-4)
        g_init = gs_c + [g_new0]
        s2_init = max(s2_c - g_new0 / float(N), 1e-4)

        nu_bnds = [(max(-nu_max, nv - 0.8), min(nu_max, nv + 0.8)) for nv in nus_try]

        def obj_w(x):
            nv_vec = x[:Pp]
            gv_vec = np.exp(np.clip(x[Pp:2 * Pp], -13.0, 6.0))
            s2v = float(np.exp(np.clip(x[2 * Pp], -13.0, 6.0)))
            R_m = s2v * np.eye(N, dtype=np.complex128)
            for j_f in range(Pp):
                R_m += gv_vec[j_f] * td_atom(ells_try[j_f], float(nv_vec[j_f]))
            R_m = 0.5 * (R_m + R_m.conj().T)
            try:
                L_ch = np.linalg.cholesky(R_m)
            except np.linalg.LinAlgError:
                return 1e30
            ld = 2.0 * float(np.sum(np.log(np.real(np.diag(L_ch)))))
            Linv_R = np.linalg.solve(L_ch, R_td_hat)
            tr_val = float(np.real(np.trace(np.linalg.solve(L_ch.conj().T, Linv_R))))
            return float(2.0 * M * (ld + tr_val))

        x0 = np.concatenate([np.array(nus_try, dtype=float), np.log(np.maximum(g_init, 1e-5)), [np.log(max(s2_init, 1e-5))]])
        bnds = nu_bnds + [(-12.0, 5.0)] * (Pp + 1)
        res_opt = minimize(obj_w, x0, method="L-BFGS-B", bounds=bnds, options={"maxiter": 25, "ftol": 1e-8})
        nus_opt = res_opt.x[:Pp].tolist()
        gs_opt = np.exp(np.clip(res_opt.x[Pp:2 * Pp], -13.0, 6.0)).tolist()
        s2_opt = float(np.exp(np.clip(res_opt.x[2 * Pp], -13.0, 6.0)))
        nll2_ref = float(res_opt.fun)

        stat = max(0.0, nll2_c - nll2_ref)
        if step == 0:
            first_stat = stat
        if return_top_stat:
            return [], first_stat
        if stat <= tau_w:
            break
        ells_c = ells_try
        nus_c = nus_opt
        gs_c = gs_opt
        s2_c = s2_opt
        nll2_c = nll2_ref
        R_c = s2_c * np.eye(N, dtype=np.complex128)
        for ej, nj, gj in zip(ells_c, nus_c, gs_c):
            R_c += gj * td_atom(ej, nj)
        R_c = 0.5 * (R_c + R_c.conj().T)

    return [(int(ej), float(nj), float(gj * (rms ** 2))) for ej, nj, gj in zip(ells_c, nus_c, gs_c)], first_stat


def _m04_otfs_h0_worker(seed):
    sys_afdm = m4.build_system(order=8, Q=12, delta=2.0 / 3.0)
    otfs_cfg = build_otfs_17x15_config(sys_afdm)
    N = 255; M = 128
    c1, c2 = sys_afdm["c1"], sys_afdm["c2"]
    rng = np.random.default_rng(seed)
    W = (rng.standard_normal((N, M)) + 1j * rng.standard_normal((N, M))) / math.sqrt(2.0)
    Y_afdm = m4.daft_fast(W, c1, c2)
    _, st_afdm_b = m4.estimate_banded_clean(Y_afdm, sys_afdm, 12, 16, 4.5, 0.0, P_max=1, use_lag1=True, homoscedastic=False, return_top_stat=True)
    _, st_afdm_w = tm4.estimate_full_wishart_qml(Y_afdm, sys_afdm, 12, 16, 4.5, 0.0, P_max=1, return_top_stat=True)
    _, st_otfs_w = estimate_otfs_full_wishart_qml(W, otfs_cfg, 16, 4.5, 0.0, P_max=1, return_top_stat=True)
    return {"afdm_b": st_afdm_b, "afdm_w": st_afdm_w, "otfs_w": st_otfs_w}


def _m04_otfs_scene_worker(args):
    seed, pwrs_db, taus = args
    sys_afdm = m4.build_system(order=8, Q=12, delta=2.0 / 3.0)
    otfs_cfg = build_otfs_17x15_config(sys_afdm)
    N = 255; M = 128; Q = 12; ell_max = 16; nu_max = 4.5
    c1, c2, d = sys_afdm["c1"], sys_afdm["c2"], sys_afdm["d"]
    sigma_w2 = 10.0 ** (-1.5)  # 15 dB exact match to td_m_m04.py
    rng = np.random.default_rng(seed)
    P_true = len(pwrs_db)

    ells = rng.choice(np.arange(0, ell_max + 1), size=P_true, replace=False).tolist()
    nus = rng.uniform(-nu_max + 0.3, nu_max - 0.3, size=P_true).tolist()
    gammas = [10.0 ** (p / 10.0) for p in pwrs_db]
    truths = list(zip(ells, nus))

    X_base = np.sqrt(d[:, None]) * m4.sample_765bit_norm(rng, sys_afdm, M)
    S_afdm = m4.idaft_fast(X_base, c1, c2)
    S_otfs = otfs_cfg["U_otfs"] @ X_base

    H_draws = [(rng.standard_normal(M) + 1j * rng.standard_normal(M)) * math.sqrt(g / 2.0) for g in gammas]
    W_noise = (rng.standard_normal((N, M)) + 1j * rng.standard_normal((N, M))) * math.sqrt(sigma_w2 / 2.0)

    R_afdm = W_noise.copy()
    R_otfs = W_noise.copy()
    for p in range(P_true):
        R_afdm += m4.apply_path_time_fast(S_afdm, ells[p], nus[p], c1) * H_draws[p][None, :]
        R_otfs += m4.apply_path_time_fast(S_otfs, ells[p], nus[p], 0.0) * H_draws[p][None, :]
    Y_afdm = m4.daft_fast(R_afdm, c1, c2)

    d_afdm_b, _ = m4.estimate_banded_clean(Y_afdm, sys_afdm, Q, ell_max, nu_max, taus["afdm_b"], P_max=5, use_lag1=True, homoscedastic=False)
    d_afdm_w, _ = tm4.estimate_full_wishart_qml(Y_afdm, sys_afdm, Q, ell_max, nu_max, taus["afdm_w"], P_max=5)
    d_otfs_w, _ = estimate_otfs_full_wishart_qml(R_otfs, otfs_cfg, ell_max, nu_max, taus["otfs_w"], P_max=5)

    def eval_d(dets):
        hc, fac, _ = m4.match_targets(dets, truths, nu_tol=0.25)
        wh, _, _ = m4.match_targets(dets, [truths[-1]], nu_tol=0.25)
        return {"weak_hit": int(wh), "any_fa": int(fac > 0), "n_dets": len(dets)}

    return {
        "AFDM_Ours_Banded": eval_d(d_afdm_b),
        "AFDM_FullWishart": eval_d(d_afdm_w),
        "OTFS_17x15_FullWishart": eval_d(d_otfs_w),
    }


# ==============================================================================
# Part 3: 25-m03 Bell (1994) IEKS Exact Markov Prior & Subband-Init Check
# ==============================================================================
def ieks_exact_markov_prior(y, H_lin, s_ext_hat, pr_init, pt_init, sig2_eff, sig_r, sig_t, L_cpp, n_sweeps=3):
    """
    Exact Bell (1994) full-trajectory IEKS matching `gn_dual_banded` Markov prior:
      - pr[0] diffuse prior variance 1e6 (`1/1e-6`), pr[n]-pr[n-1] ~ N(0, sig_r)
      - pt[L_cpp] gauge anchor variance 1e-3 (`precision 1e3`), backward/forward random walk variance sig_t
        => at n = 0, cov(pt[L_cpp - l], pt[L_cpp - m]) = 1e-3 + min(l, m) * sig_t!
    """
    N, B = H_lin.shape
    D = L_cpp + 2
    n_arr = np.arange(N)
    l_list = [l for l in range(L_cpp + 1) if np.max(np.abs(H_lin[n_arr, L_cpp + n_arr - l])) > 1e-12]
    c_tap = np.array([H_lin[n_arr, L_cpp + n_arr - l] * s_ext_hat[L_cpp + n_arr - l] for l in l_list])

    F = np.zeros((D, D), dtype=float)
    F[0, 0] = 1.0; F[1, 1] = 1.0
    for l in range(1, L_cpp + 1):
        F[1 + l, l] = 1.0
    Q = np.zeros((D, D), dtype=float)
    Q[0, 0] = max(sig_r, 1e-9); Q[1, 1] = max(sig_t, 1e-9)
    r_var = 0.5 * max(sig2_eff, 1e-6)

    # Exact stationary Markov prior P0 around n=0 (pt[L_cpp] anchored with variance 1e-3)
    P0 = np.zeros((D, D), dtype=float)
    P0[0, 0] = 1e5
    for l in range(L_cpp + 1):
        for m in range(L_cpp + 1):
            P0[1 + l, 1 + m] = 1e-3 + float(min(l, m)) * max(sig_t, 1e-9)

    pr = pr_init.copy(); pt = pt_init.copy()
    for _ in range(n_sweeps):
        xi_nom = np.empty((N, D), dtype=float)
        xi_nom[:, 0] = pr
        for l in range(L_cpp + 1):
            xi_nom[:, 1 + l] = pt[L_cpp - l : L_cpp - l + N]

        # Prior mean x0 = 0 (prior acts on state values, NOT step increments!)
        x_filt = np.empty((N, D), dtype=float)
        P_filt = np.empty((N, D, D), dtype=float)
        x_pred = np.empty((N, D), dtype=float)
        P_pred = np.empty((N, D, D), dtype=float)

        for n in range(N):
            if n == 0:
                xp = np.zeros(D, dtype=float)
                Pp = P0.copy()
            else:
                xp = F @ x_filt[n - 1]
                Pp = F @ P_filt[n - 1] @ F.T + Q
            x_pred[n] = xp; P_pred[n] = Pp

            x_lin = xi_nom[n]
            h_re = np.zeros(D, dtype=float); h_im = np.zeros(D, dtype=float)
            yhat = 0.0 + 0.0j
            for p_idx, l in enumerate(l_list):
                it = 1 + l
                term = c_tap[p_idx, n] * np.exp(1j * (x_lin[0] + x_lin[it]))
                yhat += term
                dterm = 1j * term
                h_re[0] += dterm.real; h_re[it] += dterm.real
                h_im[0] += dterm.imag; h_im[it] += dterm.imag

            H_n = np.vstack([h_re, h_im])
            res_raw = np.array([(y[n] - yhat).real, (y[n] - yhat).imag], dtype=float)
            innov = res_raw + H_n @ (x_lin - xp)
            HP = H_n @ Pp
            S = r_var * np.eye(2) + HP @ H_n.T
            K = np.linalg.solve(S, HP).T
            x_filt[n] = xp + K @ innov
            P_post = Pp - K @ HP
            P_filt[n] = 0.5 * (P_post + P_post.T)

        x_sm = np.empty_like(x_filt)
        x_sm[-1] = x_filt[-1]
        for n in range(N - 2, -1, -1):
            C_n = np.linalg.solve(P_pred[n + 1] + 1e-11 * np.eye(D), F @ P_filt[n]).T
            x_sm[n] = x_filt[n] + C_n @ (x_sm[n + 1] - x_pred[n + 1])

        pr = pr + np.clip(x_sm[:, 0] - pr, -0.4, 0.4)
        pt_target = np.zeros(B, dtype=float)
        pt_target[L_cpp:] = x_sm[:, 1]
        for l in range(1, L_cpp + 1):
            pt_target[L_cpp - l] = x_sm[0, 1 + l]
        pt = pt + np.clip(pt_target - pt, -0.4, 0.4)
    return pr, pt


def _eval_m03_bell_worker(args):
    seed, snr_db, mode = args
    rng = np.random.default_rng(seed)
    N = 512; L_cpp = 16; B = N + L_cpp; two_Nc1 = 7
    c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2 * np.pi * N)
    sig_r = 1.5e-3; sig_t = 1.5e-3
    A_a = m3.daft_matrix(N, c1, c2); Ah_a = A_a.conj().T; P_a = m3.build_cpp_ext(N, c1, L_cpp)
    g8 = np.array([-7, -5, -3, -1, 1, 3, 5, 7]); pts64 = (g8[:, None] + 1j * g8[None, :]).ravel() / np.sqrt(42.0)
    qpsk = np.array([-1-1j, -1+1j, 1-1j, 1+1j]) / np.sqrt(2.0)
    k_p = N // 2; g_lo, g_hi = 128, 282; obs_lo, obs_hi = 136, 274; max_hw = 14
    guard = np.zeros(N, dtype=bool); guard[g_lo:g_hi] = True; data_mask = ~guard
    n_guard = int(guard.sum()); Nd = int(data_mask.sum())
    pilot_obs = np.zeros(N, dtype=bool); pilot_obs[obs_lo:obs_hi] = True
    x_p = np.zeros(N, dtype=complex); x_p[k_p] = np.sqrt(float(n_guard))
    sp_a = P_a @ (Ah_a @ x_p); pca = m3.build_pca_bases(N, L_cpp, K_pca=18)
    sys_cfg = dict(N=N, L_cpp=L_cpp, two_Nc1=two_Nc1, k_p=k_p, A=A_a, Ah=Ah_a,
                   s_p_ext=sp_a, n_guard=n_guard, max_hw=max_hw, pilot_obs=pilot_obs,
                   sig_r_prior=sig_r, sig_t_prior=sig_t)

    ls_t = np.array([0, 5, 16], dtype=int); pdp = np.array([0.4225, 0.3025, 0.2750])
    nus_t = rng.uniform(-0.4, 0.4, 3); hs_t = np.sqrt(pdp) * np.exp(1j * rng.uniform(0, 2 * np.pi, 3))
    H_lin_t = m3.build_H_ext(N, L_cpp, hs_t, ls_t, nus_t)
    sig2_true = 10.0 ** (-snr_db / 10.0)
    phi_t = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)); phi_t -= phi_t[L_cpp]
    phi_r = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N))
    w = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    xd_vals = pts64[rng.integers(0, 64, Nd)]
    x_a = x_p.copy(); x_a[data_mask] = xd_vals
    y_a = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * (P_a @ (Ah_a @ x_a)))) + w
    Y_a = A_a @ y_a

    refine_ch = (mode == "single_frame")
    if mode == "single_frame":
        sig2_hat, l_h, h_h, nu_h, phi_mrc = m3.blind_single_frame_init(Y_a, sys_cfg)
    else:
        w_tr = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        _ = rng.integers(0, 4, N)
        y_tr = H_lin_t @ sp_a + w_tr
        sig2_hat, l_h, h_h, nu_h = m3.blind_ce_from_training(y_tr, sys_cfg, training_has_pn=False)
        H_p0 = [m3.build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]
        k_cs = [k_p - two_Nc1 * int(l) for l in l_h]
        z_mrc = np.zeros(N, dtype=complex)
        for i in range(len(l_h)):
            k_hi = min(k_cs[i] + max_hw, (k_cs[i] + k_cs[i - 1]) // 2) if i > 0 else k_cs[i] + max_hw
            k_lo = max(k_cs[i] - max_hw, (k_cs[i] + k_cs[i + 1]) // 2 + 1) if i < len(l_h) - 1 else k_cs[i] - max_hw
            m = np.zeros(N, dtype=bool); m[k_lo : k_hi + 1] = True
            Ys = np.zeros(N, dtype=complex); Ys[m] = Y_a[m]
            z_mrc += (Ah_a @ Ys) * np.conj(H_p0[i] @ sp_a)
        pi = m3.zero_unwrap_complex(z_mrc[L_cpp : N - L_cpp])
        phi_mrc = np.empty(N); phi_mrc[L_cpp : N - L_cpp] = pi; phi_mrc[:L_cpp] = pi[0]; phi_mrc[N - L_cpp:] = pi[-1]

    H_paths_h = [m3.build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]
    if refine_ch:
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                                 phi_mrc, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r, sig_t, L_cpp, pca, 3)
        h_0, nu_0 = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, pr_ep, pt_ep, l_h, nu_h, L_cpp)
        H_p2 = [m3.build_H_ext(N, L_cpp, [h_0[i]], [l_h[i]], [nu_0[i]]) for i in range(len(l_h))]
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_p2, l_h, sp_a,
                                                 pr_ep, pt_ep, 1.0 / max(sig2_hat, 1e-3), sig_r, sig_t, L_cpp, pca, 3)
    else:
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                                 phi_mrc, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r, sig_t, L_cpp, pca, 6)
        h_0, nu_0 = h_h.copy(), nu_h.copy()

    def run_loop(use_ieks: bool, pr_start, pt_start):
        pr_c, pt_c = pr_start.copy(), pt_start.copy()
        h_c, nu_c = h_0.copy(), nu_0.copy()
        s2 = sig2_hat; best_r = np.inf; best_xh = None
        for out_idx in range(6):
            Hl = m3.build_H_ext(N, L_cpp, h_c, l_h, nu_c)
            Hc = np.exp(1j * pr_c)[:, None] * ((Hl * np.exp(1j * pt_c)[None, :]) @ P_a)
            xs, xhc, vx, _ = m3.oamp_exact(y_a, Hc, Ah_a, max(s2, 1e-6) + 0.02 * (0.6 ** out_idx), pts64, data_mask, x_p, 8)
            s_ext_s = P_a @ (Ah_a @ xs)
            if use_ieks:
                pr_c, pt_c = ieks_exact_markov_prior(y_a, Hl, s_ext_s, pr_c, pt_c, max(s2, 1e-6) + 0.5 * vx, sig_r, sig_t, L_cpp, 3)
            else:
                pr_c, pt_c = m3.gn_dual_banded(y_a, Hl, s_ext_s, pr_c, pt_c, max(s2, 1e-6) + 0.5 * vx, sig_r, sig_t, L_cpp, 3)
            if refine_ch and out_idx >= 1:
                h_c, nu_c = m3.refine_channel_blind(y_a, s_ext_s, pr_c, pt_c, l_h, nu_c, L_cpp)
            Hl2 = m3.build_H_ext(N, L_cpp, h_c, l_h, nu_c)
            rc = float(np.sum(np.abs(y_a - np.exp(1j * pr_c) * (Hl2 @ (np.exp(1j * pt_c) * (P_a @ (Ah_a @ xhc))))) ** 2))
            s2 = float(np.clip(rc / N, 1e-5 if refine_ch else max(sig2_hat * 0.4, 1e-6), 0.05))
            if rc < best_r: best_r = rc; best_xh = xhc
        return float(np.mean(np.abs(best_xh[data_mask] - x_a[data_mask]) > 1e-3))

    return {
        "Ours_BandedGN_SubbandInit": run_loop(False, pr_ep, pt_ep),
        "Bell1994_ExactMarkovIEKS_SubbandInit": run_loop(True, pr_ep, pt_ep),
        "Bell1994_ExactMarkovIEKS_NoSubbandInit": run_loop(True, phi_mrc, np.zeros(B)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", type=str, default=os.path.join(THIS_DIR, "out_m_suppl.json"))
    args = ap.parse_args()

    t0_all = time.time()
    summary = {"smoke": bool(args.smoke), "workers": args.workers}

    # --- 1. 26-m01 Horizontal SNR Gap ---
    t0 = time.time()
    n_r2 = 4 if args.smoke else 60
    n_r3 = 4 if args.smoke else 48
    snr_r2 = [32.0, 33.0, 34.0, 35.0, 36.0]
    snr_r3 = [28.0, 29.0, 30.0, 31.0]
    m01_res = {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        rows_r2 = list(ex.map(_eval_m01_burst_snr_curve, [(202611262500 + 2000 + i, "strong", 64, snr_r2, False) for i in range(n_r2)]))
        rows_r3 = list(ex.map(_eval_m01_burst_snr_curve, [(202611262500 + 3000 + i, "moderate", 16, snr_r3, True) for i in range(n_r3)]))
    for tag, rows in [("R2_Strong13_64QAM", rows_r2), ("R3_ContDop_16QAM", rows_r3)]:
        keys = list(rows[0].keys())
        m01_res[tag] = {
            "n_bursts": len(rows),
            "mean_ser": {k: float(np.mean([r[k] for r in rows])) for k in keys},
            "lockout_gt1pct": {k: float(np.mean([r[k] > 0.01 for r in rows])) for k in keys},
        }
    summary["m01_horizontal_snr"] = m01_res
    print("[1/3 m01 horizontal SNR]:", json.dumps(m01_res, indent=2), f"({time.time()-t0:.1f}s)", flush=True)

    # --- 2. 26-m04 Rectangular 17x15=255 OTFS + Clutter-Only H0 ---
    t0 = time.time()
    sys_afdm = m4.build_system(order=8, Q=12, delta=2.0 / 3.0)
    otfs_cfg = build_otfs_17x15_config(sys_afdm)
    pop_id = check_otfs_population_identifiability(otfs_cfg)
    n_cal = 20 if args.smoke else 140
    n_sc = 8 if args.smoke else 80
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        h0_rows = list(ex.map(_m04_otfs_h0_worker, [202611268000 + i for i in range(n_cal)]))
    q_pfa = 1.0 - 0.01532567
    taus = {k: float(np.quantile([r[k] for r in h0_rows], q_pfa)) for k in ("afdm_b", "afdm_w", "otfs_w")}

    m04_suppl = {"population_identifiability_otfs_17x15": pop_id, "taus_pfa_1p5pct": taus, "regimes": {}}
    for rname, pwrs, soff in [
        ("H0_ClutterOnly_P1_0dB", [0.0], 1000),
        ("Reg1_P2_0_m13p5dB", [0.0, -13.5], 2000),
        ("Reg2_P3_0_m5_m12p5dB", [0.0, -5.0, -12.5], 3000),
    ]:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            srows = list(ex.map(_m04_otfs_scene_worker, [(202611268000 + soff + i, pwrs, taus) for i in range(n_sc)]))
        arms = list(srows[0].keys())
        m04_suppl["regimes"][rname] = {
            "n_scenes": n_sc,
            "arms": {
                a: {
                    "wt_pd": float(np.mean([r[a]["weak_hit"] for r in srows])),
                    "any_fa": float(np.mean([r[a]["any_fa"] for r in srows])),
                    "mean_n_dets": float(np.mean([r[a]["n_dets"] for r in srows])),
                } for a in arms
            }
        }
    summary["m04_otfs_17x15_and_clutter_h0"] = m04_suppl
    print("[2/3 m04 OTFS 17x15 & Clutter H0]:", json.dumps(m04_suppl, indent=2), f"({time.time()-t0:.1f}s)", flush=True)

    # --- 3. 25-m03 Bell (1994) IEKS Exact Markov Prior Equivalence ---
    t0 = time.time()
    n_m3 = 4 if args.smoke else 40
    m03_suppl = {}
    for sname, snr_db, mode, soff in [
        ("Sep_R3_45dB_Floor", 45.0, "prior_clean", 1000),
        ("Sep_R4_30dB_SFBlind", 30.0, "single_frame", 2000),
    ]:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            frows = list(ex.map(_eval_m03_bell_worker, [(202611261500 + soff + i, snr_db, mode) for i in range(n_m3)]))
        keys = list(frows[0].keys())
        m03_suppl[sname] = {
            "n_frames": n_m3,
            "mean_ser": {k: float(np.mean([r[k] for r in frows])) for k in keys},
            "lock_loss_gt5pct": {k: float(np.mean([r[k] > 0.05 for r in frows])) for k in keys},
        }
    summary["m03_bell1994_ieks_equivalence"] = m03_suppl
    print("[3/3 m03 Bell 1994 IEKS equivalence]:", json.dumps(m03_suppl, indent=2), f"({time.time()-t0:.1f}s)", flush=True)

    summary["total_elapsed_s"] = round(time.time() - t0_all, 2)
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)
    print(f"Saved -> {args.out} (total {summary['total_elapsed_s']}s)", flush=True)


if __name__ == "__main__":
    main()
