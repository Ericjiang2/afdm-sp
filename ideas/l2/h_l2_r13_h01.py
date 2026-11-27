import os
import sys
import time
import json
import hashlib
import argparse
from math import erfc
from multiprocessing import Pool
import numpy as np
from scipy.integrate import quad
from scipy.linalg import qr, solve_triangular
from scipy.stats import t as student_t, betabinom

# First-line environment printout (round-13.md & round-agy-extra.md §2.2)
print(f"PYTHON_EXEC={sys.executable}", flush=True)


# =====================================================================
# 1. Exact AFDM Operators & Matrix-Free Fast FFT-CPP Multipath Operator
# =====================================================================
def build_daft_matrices(N: int, c1: float, c2: float):
    n = np.arange(N, dtype=np.float64)
    m = np.arange(N, dtype=np.float64)
    lc1 = np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))
    lc2 = np.exp(-1j * 2.0 * np.pi * c2 * (m ** 2))
    F = np.fft.fft(np.eye(N, dtype=np.complex128), axis=0) / np.sqrt(float(N))
    A = (lc2[:, None] * F) * lc1[None, :]
    return A, lc1, lc2, F


def daft_col(X: np.ndarray, lc1: np.ndarray, lc2: np.ndarray) -> np.ndarray:
    N = lc1.shape[0]
    tmp = lc1[:, None] * X if X.ndim == 2 else lc1 * X
    f = np.fft.fft(tmp, axis=0) / np.sqrt(float(N))
    return (lc2[:, None] * f) if X.ndim == 2 else (lc2 * f)


def idaft_col(S: np.ndarray, lc1: np.ndarray, lc2: np.ndarray) -> np.ndarray:
    N = lc1.shape[0]
    tmp = np.conj(lc2)[:, None] * S if S.ndim == 2 else np.conj(lc2) * S
    f = np.fft.ifft(tmp, axis=0) * np.sqrt(float(N))
    return (np.conj(lc1)[:, None] * f) if S.ndim == 2 else (np.conj(lc1) * f)


def ula_steering(Nt: int, theta_deg: float, unit_norm: bool = False) -> np.ndarray:
    idx = np.arange(Nt, dtype=np.float64)
    v = np.exp(-1j * np.pi * idx * np.sin(np.deg2rad(theta_deg)))
    if unit_norm:
        v = v / np.sqrt(float(Nt))
    return v


def td_path_matrix(N: int, c1: float, ell: int, nu: float) -> np.ndarray:
    n = np.arange(N, dtype=np.int64)
    col = (n - ell) % N
    cpp = np.where(n < ell, np.exp(-1j * 2.0 * np.pi * c1 * (N * N - 2.0 * N * (ell - n))), 1.0 + 0.0j)
    dop = np.exp(1j * 2.0 * np.pi * nu * n / float(N))
    T = np.zeros((N, N), dtype=np.complex128)
    T[n, col] = dop * cpp
    return T


def build_user_afdm_channel_dense(A: np.ndarray, c1: float, Nt: int, paths: list) -> np.ndarray:
    """Reference dense DAFT-domain channel H_af in C^{N x (N*Nt)} (used for Redline 1 parity check)."""
    N = A.shape[0]
    H_k = np.zeros((N, N * Nt), dtype=np.complex128)
    for alpha_p, ell_p, nu_p, theta_p in paths:
        T_p = td_path_matrix(N, c1, ell_p, nu_p)
        E_p = A @ T_p @ A.conj().T
        a_conj = np.conj(ula_steering(Nt, theta_p, unit_norm=False))
        H_k += np.kron(alpha_p * E_p, a_conj[None, :])
    return H_k


def fast_forward_H_td(X_td: np.ndarray, users_q_paths: list, Nt: int, c1: float, lc1: np.ndarray, lc2: np.ndarray) -> np.ndarray:
    """Matrix-free O(Nt K Pk N + K N log N) exact forward operator mapping X_td (N, Nt) -> Z_af (K, N)."""
    N = X_td.shape[0]
    K = len(users_q_paths)
    n_idx = np.arange(N, dtype=np.int64)
    Y_td = np.zeros((N, K), dtype=np.complex128)
    for k in range(K):
        acc = np.zeros(N, dtype=np.complex128)
        for alpha_p, ell_p, nu_p, theta_p in users_q_paths[k]:
            a_conj = np.conj(ula_steering(Nt, theta_p, unit_norm=False))
            u_p = X_td @ a_conj
            col = (n_idx - ell_p) % N
            cpp = np.where(n_idx < ell_p, np.exp(-1j * 2.0 * np.pi * c1 * (N * N - 2.0 * N * (ell_p - n_idx))), 1.0 + 0.0j)
            dop = np.exp(1j * 2.0 * np.pi * nu_p * n_idx / float(N))
            acc += alpha_p * dop * cpp * u_p[col]
        Y_td[:, k] = acc
    return daft_col(Y_td, lc1, lc2).T


def fast_adjoint_H_td(R_af: np.ndarray, users_q_paths: list, Nt: int, c1: float, lc1: np.ndarray, lc2: np.ndarray) -> np.ndarray:
    """Matrix-free O(Nt K Pk N + K N log N) exact adjoint operator mapping R_af (K, N) -> G_td (N, Nt)."""
    K, N = R_af.shape
    n_idx = np.arange(N, dtype=np.int64)
    R_td = idaft_col(R_af.T, lc1, lc2)
    G_td = np.zeros((N, Nt), dtype=np.complex128)
    for k in range(K):
        rk = R_td[:, k]
        for alpha_p, ell_p, nu_p, theta_p in users_q_paths[k]:
            a_vec = ula_steering(Nt, theta_p, unit_norm=False)
            cpp = np.where(n_idx < ell_p, np.exp(-1j * 2.0 * np.pi * c1 * (N * N - 2.0 * N * (ell_p - n_idx))), 1.0 + 0.0j)
            dop = np.exp(1j * 2.0 * np.pi * nu_p * n_idx / float(N))
            idx_fwd = (n_idx + ell_p) % N
            w_adj = np.conj(alpha_p * dop[idx_fwd] * cpp[idx_fwd]) * rk[idx_fwd]
            G_td += np.outer(w_adj, a_vec)
    return G_td


def qam16_alphabet() -> np.ndarray:
    pts = np.array([-3.0, -1.0, 1.0, 3.0], dtype=np.float64)
    return (pts[:, None] + 1j * pts[None, :]).ravel() / np.sqrt(10.0)


# =====================================================================
# 2. PA Hardware, Exact Projectors, Proximal Operators, Blind Rx & RD
# =====================================================================
def apply_pa_elem(X_td: np.ndarray, a_sat: float, pa_model: str = "rapp", rapp_p: float = 2.5) -> np.ndarray:
    if a_sat > 1e6:
        return X_td.copy()
    mag = np.abs(X_td)
    if pa_model == "sel":
        return X_td * np.where(mag > a_sat, a_sat / np.maximum(mag, 1e-15), 1.0)
    elif pa_model == "rapp":
        return X_td / ((1.0 + (mag / max(a_sat, 1e-15)) ** (2.0 * rapp_p)) ** (1.0 / (2.0 * rapp_p)))
    raise ValueError(f"Unknown pa_model={pa_model}")


def bounded_pa_preinv(Y_des: np.ndarray, a_sat: float, pa_model: str = "rapp", rapp_p: float = 2.5, rho_cap: float = 0.89) -> np.ndarray:
    """Exact monotone smooth PA pre-inversion g_PA^{-1} on interior disk |Y| <= rho_cap * a_sat."""
    if a_sat > 1e6:
        return Y_des.copy()
    Y_clip = apply_pa_elem(Y_des, rho_cap * a_sat, pa_model="sel")
    if pa_model == "sel":
        return Y_clip
    ratio = np.minimum(np.abs(Y_clip) / max(a_sat, 1e-15), 0.96)
    return Y_clip / ((1.0 - ratio ** (2.0 * rapp_p)) ** (1.0 / (2.0 * rapp_p)))


def sui_bussgang_params(sigma_x2: float, a_sat: float, pa_model: str = "rapp", rapp_p: float = 2.5):
    """
    Exact analytical Bussgang gain K_PA = E[x* g_PA(x)] / E[|x|^2] and distortion variance sigma_d2
    for circular Gaussian x ~ CN(0, sigma_x2) per Sui et al., IEEE TCOM 2026 Eq. (25)-(27).
    """
    if a_sat > 1e6 or sigma_x2 <= 1e-18:
        return 1.0, 0.0
    xi = a_sat / np.sqrt(sigma_x2)
    if pa_model == "sel":
        k_pa = 1.0 - np.exp(-(xi ** 2)) + 0.5 * np.sqrt(np.pi) * xi * erfc(xi)
        p_out = sigma_x2 * (1.0 - np.exp(-(xi ** 2)))
        return float(k_pa), max(0.0, float(p_out - (k_pa ** 2) * sigma_x2))
    elif pa_model == "rapp":
        def f_k(u):
            if u <= 0.0:
                return 0.0
            log_r = 0.5 * np.log(u) - np.log(xi)
            return u * np.exp(-u - np.logaddexp(0.0, 2.0 * rapp_p * log_r) / (2.0 * rapp_p))

        def f_p(u):
            if u <= 0.0:
                return 0.0
            log_r = 0.5 * np.log(u) - np.log(xi)
            return u * np.exp(-u - np.logaddexp(0.0, 2.0 * rapp_p * log_r) / rapp_p)

        k_pa = quad(f_k, 0.0, xi ** 2, epsabs=1e-12, epsrel=1e-12)[0] + quad(f_k, xi ** 2, np.inf, epsabs=1e-12, epsrel=1e-12)[0]
        p_norm = quad(f_p, 0.0, xi ** 2, epsabs=1e-12, epsrel=1e-12)[0] + quad(f_p, xi ** 2, np.inf, epsabs=1e-12, epsrel=1e-12)[0]
        return float(k_pa), max(0.0, float(sigma_x2 * p_norm - (k_pa ** 2) * sigma_x2))
    raise ValueError(f"Unknown pa_model={pa_model}")


def exact_proj_disk_l2_ball_batched(V: np.ndarray, r_max: float, p_cap: float) -> np.ndarray:
    """
    Exact Euclidean projection onto the closed convex intersection
        D(r_max, p_cap) = { y in C^D : |y_i| <= r_max for all i,  ||y||_2^2 <= p_cap }.
    Solves the monotone 1D KKT root sum_i min(|v_i|/(1 + lam), r_max)^2 = p_cap via 54-step bisection (< 1e-14).
    """
    was_1d = (V.ndim == 1)
    Vb = V[None, :] if was_1d else V
    mag = np.abs(Vb)
    clipped = np.minimum(mag, r_max)
    p_clip = np.einsum("qd,qd->q", clipped, clipped)
    need_ball = p_clip > p_cap
    out = Vb * np.where(mag > r_max, r_max / np.maximum(mag, 1e-15), 1.0)
    if not np.any(need_ball):
        return out[0] if was_1d else out
    if p_cap <= 0.0:
        out[need_ball] = 0.0
        return out[0] if was_1d else out

    mag_sub = mag[need_ball]
    norms = np.sqrt(np.einsum("qd,qd->q", mag_sub, mag_sub))
    lam_lo = np.zeros(mag_sub.shape[0], dtype=np.float64)
    lam_hi = np.maximum(norms / np.sqrt(p_cap) - 1.0, 1e-12)
    while np.any(np.einsum("qd,qd->q", np.minimum(mag_sub / (1.0 + lam_hi[:, None]), r_max), np.minimum(mag_sub / (1.0 + lam_hi[:, None]), r_max)) > p_cap):
        lam_hi *= 2.0
    for _ in range(54):
        lam_mid = 0.5 * (lam_lo + lam_hi)
        m_mid = np.minimum(mag_sub / (1.0 + lam_mid[:, None]), r_max)
        s_mid = np.einsum("qd,qd->q", m_mid, m_mid)
        gt = s_mid > p_cap
        lam_lo = np.where(gt, lam_mid, lam_lo)
        lam_hi = np.where(gt, lam_hi, lam_mid)
    m_opt = np.minimum(mag_sub / (1.0 + lam_hi[:, None]), r_max)
    sc_sub = np.where(mag_sub > 1e-15, m_opt / np.maximum(mag_sub, 1e-15), 0.0)
    out[need_ball] = Vb[need_ball] * sc_sub
    return out[0] if was_1d else out


def prox_linf_moreau_batched(V: np.ndarray, tau) -> np.ndarray:
    """
    Exact complex l_infinity proximal operator (Studer, Yin & Baraniuk, IEEE J-STSP 2013 Lemma 1):
        prox_{tau ||.||_inf}(v) = argmin_z  0.5 ||z - v||_2^2 + tau ||z||_inf
                                = v - Proj_{||.||_1 <= tau}(v).
    Supports scalar tau or per-row vector tau of shape (Q,). Computed in O(D log D) per row (< 1e-15 accuracy).
    """
    was_1d = (V.ndim == 1)
    Vb = V[None, :] if was_1d else V
    Q_b, D = Vb.shape
    tau_vec = np.broadcast_to(np.asarray(tau, dtype=np.float64), (Q_b,))
    if np.all(tau_vec <= 0.0):
        return V.copy()
    mag = np.abs(Vb)
    l1_sum = np.sum(mag, axis=1)
    out = Vb.copy()
    zero_mask = l1_sum <= tau_vec
    out[zero_mask] = 0.0
    act = (~zero_mask) & (tau_vec > 0.0)
    if not np.any(act):
        return out[0] if was_1d else out

    mag_a = mag[act]
    tau_a = tau_vec[act][:, None]
    s_desc = np.sort(mag_a, axis=1)[:, ::-1]
    csum = np.cumsum(s_desc, axis=1)
    k_idx = np.arange(1, D + 1, dtype=np.float64)[None, :]
    cand_theta = (csum - tau_a) / k_idx
    cond = s_desc > cand_theta
    k_star = np.sum(cond, axis=1) - 1
    theta = cand_theta[np.arange(mag_a.shape[0]), k_star][:, None]
    m_clipped = np.minimum(mag_a, np.maximum(theta, 0.0))
    scale = np.where(mag_a > 1e-15, m_clipped / np.maximum(mag_a, 1e-15), 0.0)
    out[act] = Vb[act] * scale
    return out[0] if was_1d else out


def _run_admm_min_linf_core(X_min: np.ndarray, proj_affine_fn, min_admm: int = 100, max_admm: int = 240):
    """
    Shared over-relaxed & relative-residual-balanced exact ADMM solver for:
        p_q^* = min_x ||x||_inf   s.t.   x in A_q = x_min,q + N_q   (q = 0..Q-1).
    Uses Boyd et al. (Found. Trends Mach. Learn. 2011, Sec. 3.3.1, 3.4.1 & 3.4.3):
      - Scale-matched initial penalty rho_0 = 2 / ||x_min,q||_2 with relative primal-vs-dual residual
        balancing in the first 60 iterations and fixed rho thereafter for guaranteed global convergence;
      - Over-relaxation alpha_or = 1.6 in the first 75 iterations and exact unrelaxed alpha_or = 1.0
        for it >= 75 so final iterates satisfy X_K == Z_K and dual feasibility without relaxation bias;
      - Runs at least min_admm = 100 steps and continues in 20-step blocks up to max_admm = 240 until
        iter_primal_rel <= 0.003, dual_rel <= 0.003, peak_step_rel <= 0.003, AND exact Holder (l_1, l_inf)
        certified global relative duality gap <= 0.015 on ALL Q blocks!
    """
    Q_b, D = X_min.shape
    Z = X_min.copy()
    U = np.zeros_like(X_min)
    rho = 2.0 / np.maximum(np.linalg.norm(X_min, axis=1), 1e-6)
    alpha_or = 1.6
    X = X_min.copy()
    X_prev = X_min.copy()
    Z_prev = Z.copy()
    pk_min_l2 = np.max(np.abs(X_min), axis=1)
    is_zero_rhs = pk_min_l2 <= 1e-12

    def compute_cert(X_c, X_p, Z_c, Z_p, U_c):
        it_p = float(np.max(np.linalg.norm(X_c - Z_c, axis=1) / np.maximum(np.linalg.norm(X_c, axis=1), 1e-12)))
        # Standard unprojected Boyd et al. (2011, Sec. 3.1.1 Eq. 3.8 & Sec. 3.3.1) relative dual residual:
        # s^k = -rho (z^k - z^{k-1}), normalized by ||rho u^k||_2 => ||Z_c - Z_p||_2 / ||U_c||_2
        du_r = float(np.max(np.linalg.norm(Z_c - Z_p, axis=1) / np.maximum(np.linalg.norm(U_c, axis=1), 1e-12)))
        pk_c = np.max(np.abs(X_c), axis=1)
        pk_pr = np.max(np.abs(X_p), axis=1)
        pk_st = float(np.max(np.abs(pk_c - pk_pr) / np.maximum(pk_c, 1e-12)))
        X_f = proj_affine_fn(Z_c)
        pk_f = np.max(np.abs(X_f), axis=1)
        lam = rho[:, None] * U_c
        nu_raw = lam - (proj_affine_fn(lam) - X_min)
        nu_l1 = np.maximum(np.sum(np.abs(nu_raw), axis=1), 1.0)
        nu_feas = nu_raw / nu_l1[:, None]
        dual_lb = np.maximum(0.0, np.real(np.einsum("qd,qd->q", np.conj(nu_feas), X_min)))
        rel_dg = float(np.max(np.where(is_zero_rhs, 0.0, np.maximum(0.0, pk_f - dual_lb) / np.maximum(pk_f, 1e-12))))
        pk_rat = float(np.max(np.where(is_zero_rhs, 1.0, pk_f / np.maximum(pk_min_l2, 1e-12))))
        return X_f, it_p, du_r, pk_st, rel_dg, pk_rat

    X_fin = X_min.copy()
    iter_primal_rel_max, dual_rel_max, peak_step_rel_max, rel_duality_gap_max, peak_ratio_max = 1.0, 1.0, 1.0, 1.0, 1.0
    iters_used = 0
    for it in range(max_admm):
        X_prev = X
        X = proj_affine_fn(Z - U)
        a_cur = alpha_or if it < 75 else 1.0
        X_hat = a_cur * X + (1.0 - a_cur) * Z
        Z_prev = Z
        Z = prox_linf_moreau_batched(X_hat + U, 1.0 / rho)
        U = U + (X_hat - Z)
        if it < 60 and (it % 5 == 4):
            r_rel = np.linalg.norm(X - Z, axis=1) / np.maximum(np.linalg.norm(X, axis=1), 1e-12)
            s_rel = np.linalg.norm(Z - Z_prev, axis=1) / np.maximum(np.linalg.norm(U, axis=1), 1e-12)
            grow = r_rel > 3.0 * np.maximum(s_rel, 1e-15)
            shrink = s_rel > 3.0 * np.maximum(r_rel, 1e-15)
            rho = np.where(grow, 2.0 * rho, np.where(shrink, 0.5 * rho, rho))
            U = np.where(grow[:, None], 0.5 * U, np.where(shrink[:, None], 2.0 * U, U))
        iters_used = it + 1
        if iters_used >= min_admm and ((iters_used - min_admm) % 20 == 0 or iters_used == max_admm):
            X_fin, iter_primal_rel_max, dual_rel_max, peak_step_rel_max, rel_duality_gap_max, peak_ratio_max = compute_cert(
                X, X_prev, Z, Z_prev, U
            )
            if (iter_primal_rel_max <= 0.003 and dual_rel_max <= 0.003
                    and peak_step_rel_max <= 0.003 and rel_duality_gap_max <= 0.015):
                break

    return X_fin, {
        "iters_used": iters_used,
        "iter_primal_rel_max": iter_primal_rel_max,
        "dual_rel_max": dual_rel_max,
        "peak_step_rel_max": peak_step_rel_max,
        "rel_duality_gap_max": rel_duality_gap_max,
        "peak_vs_l2min_max_ratio": peak_ratio_max,
    }


def solve_studer_min_linf_pair_cpi(H_diag_af_q: np.ndarray, H_td_stack_q: list, Qc_rc_af_list: list,
                                   a_tar_unit: np.ndarray, u_chirp: np.ndarray, A_rad_op: np.ndarray,
                                   d_cpi: np.ndarray, lc1: np.ndarray, lc2: np.ndarray,
                                   m_rad: int, P_nom: float, n_admm: int = 100):
    """
    Matched pure single-factor Studer, Yin & Baraniuk (IEEE J-STSP 2013, Eq. 4 / Alg. 1) minimum-l_inf ADMM pair:
      1. Rival_b1_PerBinStuderMinLinf (F_N -> A per-DAFT-bin mother-method port):
         - Treats each DAFT bin m = 0..N-1 as a decoupled spatial problem C_m s_m = r_m with C_m = [H_diag[q,m]; a_tar^H]
           and r_m = [d_cpi[q,:,m]; u_rad_bin * 1_{m==m_rad}];
         - Uses rank-safe truncated-SVD minimum-norm least-squares affine projection A_{LS,m} = argmin ||C_m s_m - r_m||_2^2
           so zero-delay-missing users in Z0_mp (where row k of H_diag is identically zero) never cause singular division;
      2. Rival_b2_FullBlockStuderMinLinf (paired full-channel control isolating per-bin approximation):
         - Uses the EXACT SAME 100-step Moreau l_inf ADMM solver, u_rad_bin ratio, raw PA frontend, and CPI waveform
           power normalization, ONLY replacing per-bin diagonal H_diag with full coupled AFDM channel [H_td_q; A_rad_op]
           (identical to Rival_b1 to < 1e-12 on flat channels Z0_flat!).
      - Both arms have ZERO borrowing of Prop's rho_c interior disk, p_eff_cap ball, RZF target, or M3 PA pre-inversion,
        and scale their generated symbol-level CPI waveforms uniformly across Q blocks to exact CPI-mean input power P_nom.
    """
    Q, N, K, Nt = H_diag_af_q.shape
    u_rad_bin = np.sqrt(0.36 / 0.64 * float(K * N))
    sqrtN = np.sqrt(float(N))

    # --- Arm b1: Rank-safe per-bin SVD affine projector stack P_null (Q, N, Nt, Nt) & S_min (Q, N, Nt) ---
    P_null = np.zeros((Q, N, Nt, Nt), dtype=np.complex128)
    S_min = np.zeros((Q, N, Nt), dtype=np.complex128)
    I_nt = np.eye(Nt, dtype=np.complex128)
    for q in range(Q):
        for m_idx in range(N):
            Hm = H_diag_af_q[q, m_idx]
            Cm = np.vstack([Hm, a_tar_unit.conj()[None, :]])
            rm = np.concatenate([d_cpi[q, :, m_idx], np.array([(u_rad_bin if m_idx == m_rad else 0.0) + 0.0j])])
            U_c, s_c, Vh_c = np.linalg.svd(Cm, full_matrices=False)
            if s_c[0] > 1e-12:
                keep = s_c > 1e-10 * s_c[0]
                V_r = Vh_c[keep, :].conj().T
                U_r = U_c[:, keep]
                S_min[q, m_idx] = V_r @ ((U_r.conj().T @ rm) / s_c[keep])
                P_null[q, m_idx] = I_nt - (V_r @ V_r.conj().T)
            else:
                P_null[q, m_idx] = I_nt

    X_min_b1 = (
        np.conj(lc1)[None, :, None]
        * np.fft.ifft(np.conj(lc2)[None, :, None] * S_min, axis=1)
        * sqrtN
    ).reshape(Q, N * Nt)

    def proj_b1(V_td: np.ndarray) -> np.ndarray:
        V3 = V_td.reshape(Q, N, Nt)
        S_v = lc2[None, :, None] * (np.fft.fft(lc1[None, :, None] * V3, axis=1) / sqrtN)
        S_p = np.einsum("qmij,qmj->qmi", P_null, S_v) + S_min
        X_p = np.conj(lc1)[None, :, None] * (np.fft.ifft(np.conj(lc2)[None, :, None] * S_p, axis=1) * sqrtN)
        return X_p.reshape(Q, N * Nt)

    X_b1, st_b1 = _run_admm_min_linf_core(X_min_b1, proj_b1, min_admm=n_admm, max_admm=240)
    X_b1 = X_b1.reshape(Q, N, Nt)
    mp_b1 = float(np.mean(np.sum(np.abs(X_b1) ** 2, axis=(1, 2))))
    if mp_b1 > 1e-12:
        X_b1 *= np.sqrt(P_nom / mp_b1)

    # --- Arm b2: Exact full-block coupled twin [H_td_q; A_rad_op] x_q = [d_q; u_rad_bin * u_chirp] ---
    X_min_b2 = np.zeros((Q, N * Nt), dtype=np.complex128)
    Vf_list = []
    rhs_rad_td = u_rad_bin * u_chirp
    all_same_rank = True
    for q in range(Q):
        r_full = np.concatenate([d_cpi[q].reshape(K * N), rhs_rad_td])
        Qc_q, Rc_q = Qc_rc_af_list[q]
        diag_rc = np.abs(np.diag(Rc_q))
        if np.min(diag_rc) > 1e-10 * max(float(np.max(diag_rc)), 1e-15):
            X_min_b2[q] = Qc_q @ solve_triangular(Rc_q.conj().T, r_full, lower=True)
            Vf_list.append(Qc_q)
        else:
            all_same_rank = False
            C_full = np.vstack([H_td_stack_q[q], A_rad_op])
            U_f, s_f, Vh_f = np.linalg.svd(C_full, full_matrices=False)
            keep_f = s_f > 1e-10 * max(float(s_f[0]), 1e-15)
            V_f = Vh_f[keep_f, :].conj().T
            X_min_b2[q] = V_f @ ((U_f[:, keep_f].conj().T @ r_full) / s_f[keep_f])
            Vf_list.append(V_f)

    if all_same_rank:
        Vf_stack = np.stack(Vf_list, axis=0)
        Vf_H = np.conj(np.transpose(Vf_stack, (0, 2, 1)))

        def proj_b2(V_td: np.ndarray) -> np.ndarray:
            return V_td - np.einsum("qdm,qm->qd", Vf_stack, np.einsum("qmd,qd->qm", Vf_H, V_td)) + X_min_b2
    else:
        def proj_b2(V_td: np.ndarray) -> np.ndarray:
            Out = V_td.copy()
            for q in range(Q):
                Vf = Vf_list[q]
                Out[q] = V_td[q] - Vf @ (Vf.conj().T @ V_td[q]) + X_min_b2[q]
            return Out

    X_b2, st_b2 = _run_admm_min_linf_core(X_min_b2, proj_b2, min_admm=n_admm, max_admm=240)
    X_b2 = X_b2.reshape(Q, N, Nt)
    mp_b2 = float(np.mean(np.sum(np.abs(X_b2) ** 2, axis=(1, 2))))
    if mp_b2 > 1e-12:
        X_b2 *= np.sqrt(P_nom / mp_b2)

    return X_b1, st_b1, X_b2, st_b2


def blind_rx_16qam_cpi(Z_rx_cpi: np.ndarray, d_pil_col0: np.ndarray, alph: np.ndarray):
    """
    STRICTLY BLIND single-tap equalization-free 16-QAM user receiver (Redline 2):
    Receives ONLY (Z_rx_cpi, d_pil_col0, alph) — ZERO access to payload truth d_cpi, H, sigma2, X_in, X_out, gamma, or K_PA!
    """
    Q, K, N = Z_rx_cpi.shape
    idx_hat = np.zeros((Q, K, N - 1), dtype=np.int64)
    g_hats = np.zeros(K, dtype=np.complex128)
    for k in range(K):
        denom = max(float(np.real(np.vdot(d_pil_col0[:, k], d_pil_col0[:, k]))), 1e-15)
        g_hat = np.vdot(d_pil_col0[:, k], Z_rx_cpi[:, k, 0]) / denom
        if abs(g_hat) < 1e-12:
            g_hat = 1e-12 + 0.0j
        g_hats[k] = g_hat
        z_eq = (Z_rx_cpi[:, k, 1:] / g_hat).ravel()
        idx_hat[:, k, :] = np.argmin(np.abs(z_eq[:, None] - alph[None, :]), axis=1).reshape(Q, N - 1)
    return idx_hat, g_hats


def sui_analytical_bussgang_gain_from_precoder(g_lin_users: np.ndarray, sigma_x2_det: float,
                                               a_sat: float, pa_model: str = "rapp", rapp_p: float = 2.5) -> np.ndarray:
    """
    Exact Sui et al. (IEEE TCOM 2026 Eq. 25-27) end-to-end effective linear gain:
        g_sui[k] = K_PA(sigma_x2_det, a_sat) * g_lin_users[k],
    computed strictly from deterministic precoder variance sigma_x2_det = P_nom / (N * Nt) and true linear channel gain
    g_lin_users[k] = (1 / QN) sum_{q,m} (H_{q,k} W_{c,q,k})_{m,m} (ZERO dependence on noise sigma2 or realized payload d_cpi!).
    """
    k_pa, _ = sui_bussgang_params(sigma_x2_det, a_sat, pa_model, rapp_p)
    return k_pa * g_lin_users


NU_GRID = np.linspace(-0.75, 0.75, 31)
DNU_SUB = np.array([-0.12, -0.06, -0.02, 0.0, 0.02, 0.06, 0.12], dtype=np.float64)


def blind_two_stage_rd_scorer(Y_rad_cpi: np.ndarray, U_ref_cpi: np.ndarray, c1: float, ell_max_rad: int = 6):
    """
    UNIFIED ZERO-LEAKAGE BLIND TWO-STAGE RANGE-DOPPLER SCORER (Redline 3):
    Applies identical Hermitian projector (I - Uc Uc^H) to echo column y_flat and row-stored templates Phi_rem:
        ((I - Uc Uc^H) phi)^T = phi^T - (phi^T Uc*) Uc^T.
    """
    Q, N = Y_rad_cpi.shape
    q_idx = np.arange(Q, dtype=np.float64)
    n_idx = np.arange(N, dtype=np.int64)
    M_nu = len(NU_GRID)

    df_all = np.exp(1j * 2.0 * np.pi * NU_GRID[:, None] * n_idx[None, :] / float(N))
    ds_all = np.exp(1j * 2.0 * np.pi * NU_GRID[:, None] * 1.125 * q_idx[None, :])

    L_rad = ell_max_rad + 1
    Phi = np.zeros((L_rad, M_nu, Q * N), dtype=np.complex128)
    for eg in range(L_rad):
        col = (n_idx - eg) % N
        cpp = np.where(n_idx < eg, np.exp(-1j * 2.0 * np.pi * c1 * (N * N - 2.0 * N * (eg - n_idx))), 1.0 + 0.0j)
        U_sh = U_ref_cpi[:, col] * cpp[None, :]
        Phi[eg] = (ds_all[:, :, None] * U_sh[None, :, :] * df_all[:, None, :]).reshape(M_nu, Q * N)

    norms_sq = np.maximum(np.real(np.einsum("lmk,lmk->lm", np.conj(Phi), Phi)), 1e-15)
    y_flat = Y_rad_cpi.ravel()
    s1_scores = (np.abs(Phi.conj() @ y_flat) ** 2) / norms_sq
    flat_idx1 = int(np.argmax(s1_scores))
    ell_1_hat, ni_1_hat = divmod(flat_idx1, M_nu)
    nu_1_hat = float(NU_GRID[ni_1_hat])

    col1 = (n_idx - ell_1_hat) % N
    cpp1 = np.where(n_idx < ell_1_hat, np.exp(-1j * 2.0 * np.pi * c1 * (N * N - 2.0 * N * (ell_1_hat - n_idx))), 1.0 + 0.0j)
    U_sh1 = U_ref_cpi[:, col1] * cpp1[None, :]
    nus_loc = nu_1_hat + DNU_SUB
    df_loc = np.exp(1j * 2.0 * np.pi * nus_loc[:, None] * n_idx[None, :] / float(N))
    ds_loc = np.exp(1j * 2.0 * np.pi * nus_loc[:, None] * 1.125 * q_idx[None, :])
    C_mat = (ds_loc[:, :, None] * U_sh1[None, :, :] * df_loc[:, None, :]).reshape(len(DNU_SUB), Q * N).T
    Uc, s_vals, _ = np.linalg.svd(C_mat, full_matrices=False)
    Uc = Uc[:, s_vals > 1e-6 * s_vals[0]]
    y_res = y_flat - Uc @ (Uc.conj().T @ y_flat)

    keep_ells = [e for e in range(L_rad) if e != ell_1_hat]
    Phi_rem = Phi[keep_ells].reshape(-1, Q * N)
    Phi_proj = Phi_rem - (Phi_rem @ Uc.conj()) @ Uc.T
    np_sq = np.real(np.einsum("mk,mk->m", np.conj(Phi_proj), Phi_proj))
    num = np.abs(Phi_proj.conj() @ y_res) ** 2
    arr = np.where(np_sq > 1e-12, num / np.maximum(np_sq, 1e-15), 0.0)

    sorted_arr = np.sort(arr)
    n_trim = max(int(0.75 * len(sorted_arr)), 1)
    bg_scale = max(float(np.mean(sorted_arr[:n_trim])), 1e-15)
    idx_max = int(np.argmax(arr))
    t_max = float(arr[idx_max] / bg_scale)
    e_idx, ni_2 = divmod(idx_max, M_nu)
    return t_max, keep_ells[e_idx], float(NU_GRID[ni_2])


# =====================================================================
# 3. Faithful Monotone WMMSE-MM (Liu & Schober 2026 Sec. IV-B, Per-Block Exact Power)
# =====================================================================
def solve_kkt_mm_subproblem(Hs_w: np.ndarray, B_rhs: np.ndarray, a_ch: np.ndarray, a_perp_comm: np.ndarray,
                            proj_ch: np.ndarray, rhs_sens: float, P_nom: float) -> np.ndarray:
    """
    Cancellation-free exact KKT solver via direct SVD of Hs_w^H for the per-block MM subproblem:
        min_W  ||Hs_w W||_F^2 - 2 Re tr(B_rhs^H W)
        s.t.   Re tr((a_ch proj_ch)^H W) >= rhs_sens,   ||W||_F^2 == P_nom.
    Here a_perp_comm is pre-orthogonalized against the UNWEIGHTED block channel Hs_q (||Hs_q a_perp_comm||_2 < 1e-12,
    explicitly measured and gated in Redline 1 and G_HYGIENE across every block and scene).
    Consequently, both the unconstrained-communication branch and the active-boundary bisection branch output
    ||W_q||_F^2 == P_nom directly (< 1e-11) with ZERO post-loop rescaling ever applied to W_sub_list!
    """
    U1, s_svd, _ = np.linalg.svd(Hs_w.conj().T, full_matrices=False)
    keep = s_svd > 1e-12 * max(float(s_svd[0]), 1e-15)
    U1 = U1[:, keep]
    d_pos = (s_svd[keep]) ** 2
    A_lin = np.outer(a_ch, proj_ch)
    UB1 = U1.conj().T @ B_rhs
    UA1 = U1.conj().T @ A_lin
    # Double orthogonalize against U1 as well (already orthogonal to unweighted Hs_q so U1^H a_perp_comm == 0)
    a_perp = a_perp_comm - U1 @ (U1.conj().T @ a_perp_comm)
    ap_norm2 = float(np.real(np.vdot(a_perp, a_perp)))
    pch_norm2 = float(np.real(np.vdot(proj_ch, proj_ch)))
    aa0 = ap_norm2 * pch_norm2

    UW0 = UB1 / d_pos[:, None]
    pow0 = float(np.real(np.einsum("rl,rl->", np.conj(UW0), UW0)))
    sens0 = float(np.real(np.einsum("rl,rl->", np.conj(UA1), UW0)))
    if pow0 <= P_nom and aa0 > 1e-14:
        beta_full = np.sqrt(max(P_nom - pow0, 0.0) / aa0)
        if rhs_sens <= 1e-12 or (sens0 + beta_full * aa0 >= rhs_sens):
            return (U1 @ UW0) + beta_full * np.outer(a_perp, proj_ch)

    bb1 = np.real(np.einsum("rl,rl->r", np.conj(UB1), UB1))
    aa1 = np.real(np.einsum("rl,rl->r", np.conj(UA1), UA1))
    ba1 = np.real(np.einsum("rl,rl->r", np.conj(UA1), UB1))
    ones_r = np.ones_like(d_pos)

    def solve_lam_active(mu_v: float) -> float:
        nsq1 = bb1 + (2.0 * mu_v) * ba1 + (mu_v * mu_v) * aa1
        nsq0 = (mu_v * mu_v) * aa0
        lo = 1e-15
        hi = max(np.sqrt((float(np.dot(nsq1, ones_r)) + nsq0) / P_nom), 1e-6)
        while float(np.dot(nsq1, 1.0 / ((d_pos + hi) ** 2))) + (nsq0 / (hi * hi)) > P_nom:
            hi *= 2.0
        for _ in range(62):
            mid = 0.5 * (lo + hi)
            if float(np.dot(nsq1, 1.0 / ((d_pos + mid) ** 2))) + (nsq0 / (mid * mid)) > P_nom:
                lo = mid
            else:
                hi = mid
        return hi

    def sens_at_mu(mu_v: float):
        lam_v = solve_lam_active(mu_v)
        lhs = float(np.dot(ba1 + mu_v * aa1, 1.0 / (d_pos + lam_v))) + (mu_v * aa0) / lam_v
        return lhs, lam_v

    s0, l0 = sens_at_mu(0.0)
    if rhs_sens <= 1e-12 or s0 >= rhs_sens:
        mu_opt, lam_opt = 0.0, l0
    else:
        m_lo, m_hi = 0.0, 1.0
        for _ in range(30):
            if sens_at_mu(m_hi)[0] >= rhs_sens:
                break
            m_hi *= 3.0
        for _ in range(56):
            m_mid = 0.5 * (m_lo + m_hi)
            if sens_at_mu(m_mid)[0] < rhs_sens:
                m_lo = m_mid
            else:
                m_hi = m_mid
        mu_opt = m_hi
        _, lam_opt = sens_at_mu(mu_opt)

    UW = (UB1 + mu_opt * UA1) / (d_pos + lam_opt)[:, None]
    W_out = (U1 @ UW) + (mu_opt / lam_opt) * np.outer(a_perp, proj_ch)
    p_cur = float(np.real(np.einsum("ml,ml->", np.conj(W_out), W_out)))
    if p_cur < P_nom - 1e-12 and ap_norm2 > 1e-14:
        # Pure nullspace fill on dedicated radar column (Hs_q @ a_perp == 0, Re tr >= rhs_sens preserved)
        w_last = W_out[:, -1]
        c_proj = np.vdot(a_perp, w_last) / ap_norm2
        w_orth = w_last - c_proj * a_perp
        rem = max(P_nom - (p_cur - float(abs(c_proj) ** 2) * ap_norm2), 0.0)
        phase = (c_proj / abs(c_proj)) if abs(c_proj) > 1e-15 else (np.conj(proj_ch[-1]) / max(abs(proj_ch[-1]), 1e-15) if abs(proj_ch[-1]) > 1e-15 else (1.0 + 0.0j))
        W_out[:, -1] = w_orth + phase * np.sqrt(rem / ap_norm2) * a_perp
    return W_out


def extract_wmmse_linear_user_gains(Hsub_list: list, W_sub_list: list, K: int, N: int) -> np.ndarray:
    """
    Production linear effective scalar channel-gain extractor shared by build_liu26_wmmse_mm_cpi and Redline 1:
        g_lin_users[k] = (1 / QN) sum_{q=0}^{Q-1} sum_{m=0}^{N-1} (H_{q,k} W_{c,q,k})_{m,m}.
    """
    Q = len(Hsub_list)
    idx_diag = np.arange(N)
    g_lin_users = np.zeros(K, dtype=np.complex128)
    for k in range(K):
        acc_g = 0.0 + 0.0j
        for q in range(Q):
            HW_c = Hsub_list[q][k * N:(k + 1) * N, :] @ W_sub_list[q][:, k * N:(k + 1) * N]
            acc_g += np.sum(HW_c[idx_diag, idx_diag])
        g_lin_users[k] = acc_g / float(Q * N)
    return g_lin_users


def build_liu26_wmmse_mm_cpi(H_td_stack_q: list, Qc_list: list, A_rad_op: np.ndarray, u_chirp: np.ndarray,
                             d_cpi: np.ndarray, K: int, N: int, Nt: int, sig2: float, P_nom: float,
                             gamma_s_frac: float = 0.38, min_iter: int = 16, max_iter: int = 60, rel_tol: float = 1e-3):
    """
    Faithful monotone WMMSE-MM (Liu & Schober 2026 Sec. IV-B, Alg. 1):
      - Runs at least min_iter = 16 iterations and continues up to max_iter = 60 until relative sum-rate
        increment (R^{(t)} - R^{(t-1)}) / |R^{(t)}| <= rel_tol = 1e-3 (strictly payload-independent);
      - Enforces exact PER-BLOCK deterministic expected power ||W_c,q||_F^2 + ||w_s,q||_2^2 == P_nom
        directly inside every KKT step with ZERO post-loop rescaling of W_sub_list, so the actual
        transmitted precoder matrices W_sub_list are 100% bit-for-bit identical to the iterates in obj_hist!
    """
    Q = len(H_td_stack_q)
    gamma_s = gamma_s_frac * P_nom
    Hsub_list, W_sub_list, achirp_sub_list, aperp_comm_list = [], [], [], []

    for q in range(Q):
        Qc = Qc_list[q]
        Hs = H_td_stack_q[q] @ Qc
        Ar = A_rad_op @ Qc
        U_hs, _ = qr(Hs.conj().T, mode="economic")
        a_ch = Ar.conj().T @ u_chirp
        # Exact double Gram-Schmidt orthogonalization against unweighted communication row-space U_hs
        a_perp_c = a_ch - U_hs @ (U_hs.conj().T @ a_ch)
        a_perp_c = a_perp_c - U_hs @ (U_hs.conj().T @ a_perp_c)
        G0 = Hs.conj().T @ np.linalg.inv(Hs @ Hs.conj().T + K * sig2 * np.eye(K * N))
        G0 *= np.sqrt((1.0 - gamma_s_frac) * P_nom / max(float(np.sum(np.abs(G0) ** 2)), 1e-12))
        ws0 = np.sqrt(gamma_s) * a_ch
        W_init = np.hstack([G0, ws0[:, None]])
        Hsub_list.append(Hs)
        achirp_sub_list.append(a_ch)
        aperp_comm_list.append(a_perp_c)
        W_sub_list.append(W_init)

    idx_diag = np.arange(N)

    def eval_rate_and_aux():
        u_vec = np.zeros(K, dtype=np.complex128)
        om_vec = np.zeros(K, dtype=np.float64)
        r_sum = 0.0
        for k in range(K):
            num_u, den_u = 0.0 + 0.0j, 0.0
            for q in range(Q):
                Hs_k = Hsub_list[q][k * N:(k + 1) * N, :]
                HW = Hs_k @ W_sub_list[q]
                des_m = HW[idx_diag, k * N + idx_diag]
                tot_q = float(np.real(np.einsum("nm,nm->", np.conj(HW), HW))) + N * sig2
                num_u += np.sum(np.conj(des_m))
                den_u += tot_q
            uk_val = num_u / max(den_u, 1e-15)
            u_vec[k] = uk_val
            e_bar_k = max(1.0 - (abs(num_u) ** 2) / max(float(Q * N) * den_u, 1e-15), 1e-8)
            om_vec[k] = 1.0 / e_bar_k
            r_sum += float(np.log2(1.0 / e_bar_k))
        return r_sum, u_vec, om_vec

    r0, u_k, omega_k = eval_rate_and_aux()
    obj_hist = [r0]
    for it in range(max_iter):
        w_user = (np.abs(u_k) ** 2) * omega_k
        w_alpha = np.repeat(w_user, N)
        b_scale = np.repeat(np.conj(u_k) * omega_k, N)
        for q in range(Q):
            Hs = Hsub_list[q]
            a_ch = achirp_sub_list[q]
            a_perp_c = aperp_comm_list[q]
            W_ref = W_sub_list[q]
            Hs_w = Hs * np.sqrt(w_alpha)[:, None]
            B_rhs = np.hstack([Hs.conj().T * b_scale[None, :], np.zeros((Hs.shape[1], 1), dtype=np.complex128)])
            proj_ch = a_ch.conj() @ W_ref
            c_ref = float(np.sum(np.abs(proj_ch) ** 2))
            rhs_sens = 0.5 * (gamma_s + c_ref)
            W_sub_list[q] = solve_kkt_mm_subproblem(Hs_w, B_rhs, a_ch, a_perp_c, proj_ch, rhs_sens, P_nom)

        r_next, u_k, omega_k = eval_rate_and_aux()
        obj_hist.append(r_next)
        if (it + 1) >= min_iter:
            rel_step = (obj_hist[-1] - obj_hist[-2]) / max(abs(obj_hist[-1]), 1e-12)
            if rel_step <= rel_tol:
                break

    # ZERO post-loop rescaling: W_sub_list transmitted below is 100% identical to W_sub_list in obj_hist[-1]!
    blk_pows = [float(np.real(np.einsum("ml,ml->", np.conj(W_sub_list[q]), W_sub_list[q]))) for q in range(Q)]
    max_blk_err = max(abs(p - P_nom) for p in blk_pows)
    max_aperp_null_err = max(float(np.linalg.norm(Hsub_list[q] @ aperp_comm_list[q])) for q in range(Q))
    g_lin_users = extract_wmmse_linear_user_gains(Hsub_list, W_sub_list, K, N)

    X_out_in = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        dv = d_cpi[q].reshape(K * N)
        w_sub = W_sub_list[q][:, :K * N] @ dv + W_sub_list[q][:, K * N]
        X_out_in[q] = (Qc_list[q] @ w_sub).reshape(N, Nt)

    wmmse_diag = {
        "monotone": bool(all(obj_hist[i + 1] >= obj_hist[i] - 1e-9 for i in range(len(obj_hist) - 1))),
        "rel_last_step": float((obj_hist[-1] - obj_hist[-2]) / max(abs(obj_hist[-1]), 1e-12)),
        "iters_used": len(obj_hist) - 1,
        "max_blk_pow_err": float(max_blk_err),
        "max_aperp_null_err": float(max_aperp_null_err),
    }
    return X_out_in, g_lin_users, obj_hist, wmmse_diag


# =====================================================================
# 4. Redline 1 Operator & Algebraic Invariant Verification (< 1e-12)
# =====================================================================
def verify_redline1_and_invariants() -> dict:
    N, Nt, K = 64, 8, 3
    c1 = 2.37 / (2.0 * N)
    c2 = 1.0 / (2.0 * N)
    A, lc1, lc2, _ = build_daft_matrices(N, c1, c2)
    unitary_err = float(np.linalg.norm(A @ A.conj().T - np.eye(N)))

    rng = np.random.default_rng(20261126)

    # 1. True TWO-BLOCK continuous multi-tap CPP + global-sample Doppler convolution check (s_af0 != s_af1)
    Ncpp = 8
    s_af0 = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    s_af1 = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    assert np.linalg.norm(s_af0 - s_af1) > 1.0
    x0 = idaft_col(s_af0, lc1, lc2)
    x1 = idaft_col(s_af1, lc1, lc2)
    k_cpp = np.arange(-Ncpp, 0, dtype=np.int64)
    cpp_phase = np.exp(-1j * 2.0 * np.pi * c1 * (N * N + 2.0 * N * k_cpp))
    tx_stream = np.concatenate([x0[N + k_cpp] * cpp_phase, x0, x1[N + k_cpp] * cpp_phase, x1])
    test_paths = [(0.7 - 0.4j, 0, 0.31), (-0.5 + 0.6j, 3, -0.58), (0.3 + 0.2j, 7, 0.71)]
    L_tot = len(tx_stream)
    rx_stream = np.zeros(L_tot, dtype=np.complex128)
    t_global = np.arange(L_tot, dtype=np.int64)
    for gain_p, ell_p, nu_p in test_paths:
        valid = t_global >= ell_p
        dop_global = np.exp(1j * 2.0 * np.pi * nu_p * (t_global[valid] - Ncpp) / float(N))
        rx_stream[valid] += gain_p * dop_global * tx_stream[t_global[valid] - ell_p]
    rx_blk0 = daft_col(rx_stream[Ncpp:Ncpp + N], lc1, lc2)
    rx_blk1 = daft_col(rx_stream[N + 2 * Ncpp:2 * N + 2 * Ncpp], lc1, lc2)
    op_blk0 = sum(g * (A @ td_path_matrix(N, c1, el, nu) @ A.conj().T) @ s_af0 for g, el, nu in test_paths)
    op_blk1 = sum(g * np.exp(1j * 2.0 * np.pi * nu * 1.125) * (A @ td_path_matrix(N, c1, el, nu) @ A.conj().T) @ s_af1 for g, el, nu in test_paths)
    cpp_2blk_err = max(float(np.linalg.norm(rx_blk0 - op_blk0)), float(np.linalg.norm(rx_blk1 - op_blk1)))

    # 2. Matrix-free fast forward & adjoint operator parity vs dense reference
    q_paths = [[
        ((rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(6.0), int(p), float(rng.uniform(-0.7, 0.7)), float(-30.0 + 25.0 * k + p))
        for p in range(3)
    ] for k in range(K)]
    A_kron = np.kron(A, np.eye(Nt))
    H_dense = np.vstack([build_user_afdm_channel_dense(A, c1, Nt, q_paths[k]) @ A_kron for k in range(K)])
    X_test = (rng.standard_normal((N, Nt)) + 1j * rng.standard_normal((N, Nt))) / np.sqrt(2.0)
    y_fast = fast_forward_H_td(X_test, q_paths, Nt, c1, lc1, lc2).reshape(K * N)
    y_dense = H_dense @ X_test.reshape(N * Nt)
    fwd_err = float(np.linalg.norm(y_fast - y_dense) / np.linalg.norm(y_dense))

    R_test = (rng.standard_normal((K, N)) + 1j * rng.standard_normal((K, N))) / np.sqrt(2.0)
    g_fast = fast_adjoint_H_td(R_test, q_paths, Nt, c1, lc1, lc2).reshape(N * Nt)
    g_dense = H_dense.conj().T @ R_test.reshape(K * N)
    adj_err = float(np.linalg.norm(g_fast - g_dense) / np.linalg.norm(g_dense))

    # 3. Complex row-template subspace nulling check (explicit assert < 1e-15 + random inner-product parity)
    Uc_t = np.array([[1.0], [1j]], dtype=np.complex128) / np.sqrt(2.0)
    phi_row = Uc_t[:, 0][None, :]
    uc_null_err = float(np.linalg.norm(phi_row - (phi_row @ Uc_t.conj()) @ Uc_t.T))
    assert uc_null_err < 1e-15, f"Uc subspace nulling failed < 1e-15: {uc_null_err}"
    Uc_r, _ = qr((rng.standard_normal((16, 3)) + 1j * rng.standard_normal((16, 3))), mode="economic")
    Phi_r = rng.standard_normal((5, 16)) + 1j * rng.standard_normal((5, 16))
    y_r = rng.standard_normal(16) + 1j * rng.standard_normal(16)
    Phi_p_row = Phi_r - (Phi_r @ Uc_r.conj()) @ Uc_r.T
    y_p_col = y_r - Uc_r @ (Uc_r.conj().T @ y_r)
    Phi_p_col = (np.eye(16) - Uc_r @ Uc_r.conj().T) @ Phi_r.T
    uc_ip_err = float(np.linalg.norm((Phi_p_row.conj() @ y_p_col) - (Phi_p_col.conj().T @ y_p_col)))

    # 4. Exact thin QR affine projection, batched 1D KKT disk-ball projection, AND Studer Moreau l_inf prox optimality
    C_rand = (rng.standard_normal((24, 64)) + 1j * rng.standard_normal((24, 64))) / np.sqrt(2.0)
    rhs_r = rng.standard_normal(24) + 1j * rng.standard_normal(24)
    Qc_r, Rc_r = qr(C_rand.conj().T, mode="economic")
    y_min_r = Qc_r @ solve_triangular(Rc_r.conj().T, rhs_r, lower=True)
    z_r = rng.standard_normal(64) + 1j * rng.standard_normal(64)
    ya_r = z_r - Qc_r @ (Qc_r.conj().T @ z_r) + y_min_r
    qr_aff_err = float(np.linalg.norm(C_rand @ ya_r - rhs_r))

    V_b = rng.standard_normal((4, 64)) + 1j * rng.standard_normal((4, 64))
    Y_b = exact_proj_disk_l2_ball_batched(V_b, 0.75, 18.0)
    kkt_vi_err = 0.0
    for q in range(4):
        for _ in range(60):
            w = apply_pa_elem(rng.standard_normal(64) + 1j * rng.standard_normal(64), 0.75, "sel")
            if np.sum(np.abs(w) ** 2) > 18.0:
                w *= np.sqrt(18.0 / np.sum(np.abs(w) ** 2))
            kkt_vi_err = max(kkt_vi_err, float(np.real(np.vdot(V_b[q] - Y_b[q], w - Y_b[q]))))
    kkt_feas_err = max(0.0, float(np.max(np.abs(Y_b)) - 0.75), float(np.max(np.sum(np.abs(Y_b) ** 2, axis=1)) - 18.0))

    # Studer l_inf proximal variational inequality: Re <v - z*, w - z*> <= tau * (||w||_inf - ||z*||_inf)
    tau_t = 3.5
    Z_prox = prox_linf_moreau_batched(V_b, tau_t)
    prox_vi_err = 0.0
    for q in range(4):
        z_opt = Z_prox[q]
        z_inf = float(np.max(np.abs(z_opt)))
        for _ in range(60):
            w = rng.standard_normal(64) + 1j * rng.standard_normal(64)
            lhs_vi = float(np.real(np.vdot(V_b[q] - z_opt, w - z_opt)))
            rhs_vi = tau_t * (float(np.max(np.abs(w))) - z_inf)
            prox_vi_err = max(prox_vi_err, lhs_vi - rhs_vi)

    # 5. End-to-end Sui TCOM'26 extraction-path check (calling production helpers directly!), WMMSE per-block exact power, & Studer parity
    # (a) Unit orthogonal single-tap channel (H_k H_j^H = delta_{kj} I_N) + build_liu26_wmmse_mm_cpi(gamma_s_frac=0.0, P_nom=K*N) at sigma2 = 0.25, a_sat = 1e9:
    #     by symmetry, each user stream gets exact unit power ||w_{c,k,m}||_2^2 = 1 along H_{q,k}^H, so (H_{q,k} W_{c,q,k})_{m,m} == 1.0
    #     and production build_liu26_wmmse_mm_cpi -> sui_analytical_bussgang_gain_from_precoder MUST return g_sui == 1.0 (NOT 1.25!)
    Q_t = 2
    a_tar_t = np.eye(Nt, dtype=np.complex128)[K]  # antenna K orthogonal to user antennas 0..K-1
    A_rad_t = np.kron(np.eye(N), a_tar_t.conj()[None, :])
    s_cm_t = np.zeros(N, dtype=np.complex128)
    s_cm_t[N // 2] = 1.0
    u_ch_t = idaft_col(s_cm_t, lc1, lc2)
    a_orth = np.eye(Nt, dtype=np.complex128)[:K]
    H_unit_q = [np.vstack([np.kron(A, a_orth[k][None, :]) for k in range(K)]) for _ in range(Q_t)]
    Qc_unit_t = [qr(np.vstack([H_unit_q[q], A_rad_t]).conj().T, mode="economic")[0] for q in range(Q_t)]
    alph_t = qam16_alphabet()
    d_A = alph_t[rng.integers(0, 16, size=(Q_t, K, N))]
    d_B = alph_t[rng.integers(0, 16, size=(Q_t, K, N))]
    _, g_lin_unit, _, wdiag_unit = build_liu26_wmmse_mm_cpi(
        H_unit_q, Qc_unit_t, A_rad_t, u_ch_t, d_A, K, N, Nt, 0.25, float(K * N), 0.0, 16, 60, 1e-3
    )
    g_sui_ext = sui_analytical_bussgang_gain_from_precoder(g_lin_unit, float(K * N) / float(N * Nt), 1e9, "rapp", 2.5)
    sui_unit_gain_err = float(np.linalg.norm(g_sui_ext - np.ones(K, dtype=np.complex128)))

    # (b) Full build_liu26_wmmse_mm_cpi extraction test on multipath channel at sigma2 = 0.25: payload invariance & zero-rescaling per-block power == P_nom
    a_tar_mp = ula_steering(Nt, 38.0, unit_norm=True)
    A_rad_mp = np.kron(np.eye(N), a_tar_mp.conj()[None, :])
    H_mp_t = [H_dense.copy() for _ in range(Q_t)]
    Qc_rc_t = [qr(np.vstack([H_mp_t[q], A_rad_mp]).conj().T, mode="economic") for q in range(Q_t)]
    Qc_t = [pair[0] for pair in Qc_rc_t]
    _, g_lin_A, _, wdiag_A = build_liu26_wmmse_mm_cpi(H_mp_t, Qc_t, A_rad_mp, u_ch_t, d_A, K, N, Nt, 0.25, float(N), 0.38, 16, 60, 1e-3)
    _, g_lin_B, _, _ = build_liu26_wmmse_mm_cpi(H_mp_t, Qc_t, A_rad_mp, u_ch_t, d_B, K, N, Nt, 0.25, float(N), 0.38, 16, 60, 1e-3)
    g_sui_A = sui_analytical_bussgang_gain_from_precoder(g_lin_A, 1.0 / float(Nt), 1e9, "rapp", 2.5)
    g_sui_B = sui_analytical_bussgang_gain_from_precoder(g_lin_B, 1.0 / float(Nt), 1e9, "rapp", 2.5)
    sui_payload_inv_err = float(np.linalg.norm(g_sui_A - g_sui_B))
    wmmse_blk_pow_err = max(wdiag_unit["max_blk_pow_err"], wdiag_A["max_blk_pow_err"])
    wmmse_aperp_null_err = max(wdiag_unit["max_aperp_null_err"], wdiag_A["max_aperp_null_err"])
    assert wdiag_A["monotone"] and wdiag_A["rel_last_step"] <= 1e-3, f"WMMSE invariant check failed: {wdiag_A}"
    assert wmmse_blk_pow_err < 1e-9, f"WMMSE per-block power error too large: {wmmse_blk_pow_err}"
    assert wmmse_aperp_null_err < 1e-12, f"WMMSE a_perp unweighted nulling error too large: {wmmse_aperp_null_err}"

    # (c) Studer flat-channel parity (Rival_b1 == Rival_b2 to < 1e-12 when ell=0, nu=0) & global duality-gap certificate
    H_flat_td_t = []
    H_flat_diag_t = np.zeros((Q_t, N, K, Nt), dtype=np.complex128)
    for q in range(Q_t):
        rows_f = []
        for k in range(K):
            ak_c = np.conj(ula_steering(Nt, -35.0 + 25.0 * k, unit_norm=False))
            rows_f.append(np.kron(A, ak_c[None, :]))
            H_flat_diag_t[q, :, k, :] = ak_c[None, :]
        H_flat_td_t.append(np.vstack(rows_f))
    Qc_rc_flat_t = [qr(np.vstack([H_flat_td_t[q], A_rad_mp]).conj().T, mode="economic") for q in range(Q_t)]
    Xb1_f, stb1_f, Xb2_f, stb2_f = solve_studer_min_linf_pair_cpi(
        H_flat_diag_t, H_flat_td_t, Qc_rc_flat_t, a_tar_mp, u_ch_t, A_rad_mp, d_A, lc1, lc2, N // 2, float(N), n_admm=100
    )
    studer_flat_parity_err = float(np.linalg.norm(Xb1_f - Xb2_f) / max(float(np.linalg.norm(Xb2_f)), 1e-15))
    studer_admm_test_res = max(
        stb1_f["iter_primal_rel_max"], stb2_f["iter_primal_rel_max"],
        stb1_f["dual_rel_max"], stb2_f["dual_rel_max"],
        stb1_f["rel_duality_gap_max"], stb2_f["rel_duality_gap_max"],
    )
    assert studer_admm_test_res < 0.005, f"Studer ADMM test convergence failed: {studer_admm_test_res}"

    Y_sub = 0.05 * X_test
    rapp_lin_err = float(np.linalg.norm(apply_pa_elem(Y_sub, 1e4, "rapp", 2.5) - Y_sub))
    Y_disk = apply_pa_elem(X_test, 0.89 * 0.4, "sel")
    X_inv = bounded_pa_preinv(Y_disk, 0.4, "rapp", 2.5, 0.89)
    preinv_err = float(np.linalg.norm(apply_pa_elem(X_inv, 0.4, "rapp", 2.5) - Y_disk))
    k_sel, sd_sel = sui_bussgang_params(1.0, 0.9, "sel")
    k_rap_inf, sd_rap_inf = sui_bussgang_params(1.0, 0.9, "rapp", rapp_p=2000.0)
    sui_limit_diff = float(abs(k_sel - k_rap_inf) + abs(sd_sel - sd_rap_inf))

    max_err = max(
        unitary_err, cpp_2blk_err, fwd_err, adj_err, uc_null_err, uc_ip_err,
        qr_aff_err, kkt_vi_err, kkt_feas_err, prox_vi_err,
        sui_unit_gain_err, sui_payload_inv_err, wmmse_aperp_null_err, studer_flat_parity_err, rapp_lin_err, preinv_err,
    )
    assert max_err < 1e-12, f"Redline 1 failed: max_err={max_err}"
    assert sui_limit_diff < 1e-3, f"Sui Bussgang limit failed: {sui_limit_diff}"
    return {
        "unitary_err": unitary_err,
        "cpp_2blk_err": cpp_2blk_err,
        "fast_fwd_rel_err": fwd_err,
        "fast_adj_rel_err": adj_err,
        "uc_subspace_null_err": uc_null_err,
        "uc_row_col_ip_err": uc_ip_err,
        "qr_affine_proj_err": qr_aff_err,
        "kkt_disk_ball_err": max(kkt_vi_err, kkt_feas_err),
        "studer_prox_linf_vi_err": prox_vi_err,
        "studer_flat_b1_vs_b2_parity_err": studer_flat_parity_err,
        "studer_admm_test_primal_rel": studer_admm_test_res,
        "sui_unit_gain_extraction_err": sui_unit_gain_err,
        "sui_payload_invariance_err": sui_payload_inv_err,
        "wmmse_per_block_pow_err": wmmse_blk_pow_err,
        "wmmse_aperp_unweighted_null_err": wmmse_aperp_null_err,
        "rapp_high_ibo_err": rapp_lin_err,
        "bounded_preinv_identity_err": preinv_err,
        "sui_rapp2000_vs_sel_diff": sui_limit_diff,
        "redline1_max_err": max_err,
    }


# =====================================================================
# 5. Statistical Confidence Interval Helpers (RFC-8259 Strict JSON Safe)
# =====================================================================
def paired_t_ci(diff: np.ndarray, alpha: float = 0.05, bonf_m: int = 1) -> dict:
    n = len(diff)
    mean = float(np.mean(diff))
    sd = float(np.std(diff, ddof=1))
    se = sd / np.sqrt(float(n))
    t_crit = float(student_t.ppf(1.0 - alpha / (2.0 * bonf_m), df=n - 1))
    hw = t_crit * se
    return {
        "n": n, "mean": mean, "sd": sd, "se": se, "t_crit": t_crit,
        "ci_low": mean - hw, "ci_high": mean + hw, "ci_hw": hw,
    }


def wilson_ci_single(k: int, n: int, z: float = 1.959963984540054):
    p = k / float(n)
    z2 = z * z
    denom = 1.0 + z2 / float(n)
    center = (p + z2 / (2.0 * n)) / denom
    rad = (z / denom) * np.sqrt(max(p * (1.0 - p) / float(n) + z2 / (4.0 * n * n), 0.0))
    return max(0.0, float(center - rad)), min(1.0, float(center + rad))


def newcombe_paired_ci(hits_x: np.ndarray, hits_y: np.ndarray, z: float = 1.959963984540054) -> dict:
    """Nominal 95% Newcombe Method 10 score CI (Stat. Med. 1998; 17:2635-2650) for paired binary difference P(X=1) - P(Y=1)."""
    x = (hits_x > 0.5).astype(np.int64)
    y = (hits_y > 0.5).astype(np.int64)
    n = len(x)
    a = int(np.sum((x == 1) & (y == 1)))
    b = int(np.sum((x == 1) & (y == 0)))
    c = int(np.sum((x == 0) & (y == 1)))
    d = int(np.sum((x == 0) & (y == 0)))

    kx = a + b
    ky = a + c
    lx, ux = wilson_ci_single(kx, n, z)
    ly, uy = wilson_ci_single(ky, n, z)

    m1 = a + b
    m0 = c + d
    n1 = a + c
    n0 = b + d
    denom_prod = float(m1) * float(m0) * float(n1) * float(n0)
    if denom_prod <= 0.0:
        phi = 0.0
    else:
        det = float(a * d - b * c)
        num_corr = max(0.0, det - 0.5 * float(n)) if det > 0.0 else det
        phi = float(np.clip(num_corr / np.sqrt(denom_prod), -1.0, 1.0))

    diff = (kx - ky) / float(n)
    dl = np.sqrt(max((kx / float(n) - lx) ** 2 + (uy - ky / float(n)) ** 2 - 2.0 * phi * (kx / float(n) - lx) * (uy - ky / float(n)), 0.0))
    du = np.sqrt(max((ux - kx / float(n)) ** 2 + (ky / float(n) - ly) ** 2 - 2.0 * phi * (ux - kx / float(n)) * (ky / float(n) - ly), 0.0))
    ci_low = float(max(-1.0, diff - dl))
    ci_high = float(min(1.0, diff + du))
    return {
        "n": n, "n11": a, "n10": b, "n01": c, "n00": d,
        "p_x": kx / float(n), "p_y": ky / float(n), "diff": diff, "phi": phi,
        "ci_low": ci_low, "ci_high": ci_high, "ci_hw": 0.5 * (ci_high - ci_low),
    }


def paired_recovery_bootstrap(j_prop: np.ndarray, j_base: np.ndarray, j_abl: np.ndarray,
                              n_boot: int = 4000, seed: int = 20261126) -> dict:
    """
    Paired percentile bootstrap 95% CI for ablation recovery ratio (J_abl - J_base) / (J_prop - J_base).
    Enforces strict positive-denominator validity: point gain >= 0.10 AND all B=4000 resamples mp - mb > 0.05
    (zero clamping; emits strict JSON null fields when denom_valid is False so allow_nan=False always succeeds).
    """
    n = len(j_prop)
    denom_pt = float(np.mean(j_prop) - np.mean(j_base))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    mp = np.mean(j_prop[idx], axis=1)
    mb = np.mean(j_base[idx], axis=1)
    ma = np.mean(j_abl[idx], axis=1)
    denom_boot = mp - mb
    denom_min = float(np.min(denom_boot))
    denom_valid = bool((denom_pt >= 0.10) and (denom_min > 0.05))
    if not denom_valid:
        return {
            "denom_valid": False, "denom_point": denom_pt, "denom_boot_min": denom_min,
            "point": None, "ci_low": None, "ci_high": None, "ci_hw": None,
        }
    pt = float((np.mean(j_abl) - np.mean(j_base)) / denom_pt)
    vals = (ma - mb) / denom_boot
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {
        "denom_valid": True, "denom_point": denom_pt, "denom_boot_min": denom_min,
        "point": pt, "ci_low": float(lo), "ci_high": float(hi), "ci_hw": 0.5 * float(hi - lo),
    }


# =====================================================================
# 6. Single-Scene Simulation Worker (All 10 Arms + Sui Bussgang + Cross-SNR)
# =====================================================================
def run_scene_worker(args_tuple):
    seed, mode, snr_db, Nt, K, pa_model, z0_kind, do_xsnr = args_tuple
    rng = np.random.default_rng(seed)
    Pk = 1 if z0_kind == "flat" else 3
    N, Q = 64, 8
    m_rad = N // 2  # bin 32: strictly disjoint from user scalar pilot bin m = 0
    ell_max = 0 if z0_kind == "flat" else 4
    nu_max = 0.0 if z0_kind else 0.75
    c1 = 9.0 / (2.0 * N)
    c2 = 1.0 / (2.0 * N)
    A, lc1, lc2, _ = build_daft_matrices(N, c1, c2)
    # Single-factor c1 = 0 diagnostic: keep c2 = 1/(2N) UNCHANGED, set ONLY c1 = 0.0
    A_c1z, lc1_0, lc2_keep, _ = build_daft_matrices(N, 0.0, c2)

    P_nom = float(N)
    sigma_x2_det = P_nom / float(N * Nt)  # deterministic nominal per-sample variance (payload-independent!)
    a_sat = 1e9 if z0_kind else np.sqrt(sigma_x2_det)
    sigma2 = 10.0 ** (-snr_db / 10.0)
    a_tar = ula_steering(Nt, 38.0)
    a_tar_unit = a_tar / np.sqrt(float(Nt))
    user_centers = np.linspace(-45.0, 20.0, K)

    users_paths = []
    for k in range(K):
        ells = [0] if z0_kind == "flat" else list(rng.choice(ell_max + 1, size=Pk, replace=False))
        ang_spread = 5.0 if z0_kind == "flat" else 9.0
        paths = [(
            (1.0 + 0.0j) if z0_kind == "flat" else (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk),
            int(ells[p]),
            0.0 if z0_kind else float(rng.uniform(-nu_max, nu_max)),
            float(user_centers[k] + rng.uniform(-ang_spread, ang_spread)),
        ) for p in range(Pk)]
        users_paths.append(paths)

    alph = qam16_alphabet()
    d_cpi = alph[rng.integers(0, 16, size=(Q, K, N))]
    d_pil = np.exp(1j * (np.pi / 4.0 + (np.pi / 2.0) * rng.integers(0, 4, size=(Q, K))))
    d_cpi[:, :, 0] = d_pil
    idx_true_pay = np.argmin(np.abs(d_cpi[:, :, 1:].ravel()[:, None] - alph[None, :]), axis=1).reshape(Q, K, N - 1)

    unit_noise_comm = (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N))) / np.sqrt(2.0)
    noise_comm = np.sqrt(sigma2) * unit_noise_comm

    ell_s = int(rng.choice([1, 2]))
    nu_s = 0.0 if z0_kind else float(rng.uniform(-0.22, 0.22))
    ell_w = int(rng.choice([3, 4, 5, 6]))
    nu_w = 0.0 if z0_kind else float(rng.uniform(-0.68, 0.68))
    amp_s = (10.0 ** (33.0 / 20.0)) * np.exp(1j * rng.uniform(0, 2.0 * np.pi))
    amp_w = (1.0 * np.exp(1j * rng.uniform(0, 2.0 * np.pi))) if mode == "H1" else 0.0
    rad_sigma2 = 4.2
    noise_rad = np.sqrt(rad_sigma2 / 2.0) * (rng.standard_normal((Q, N)) + 1j * rng.standard_normal((Q, N)))

    def build_channels(A_mat, c1_val, need_diag_af: bool = True):
        n_idx = np.arange(N, dtype=np.int64)
        H_td, q_paths_all = [], []
        H_diag_af = np.zeros((Q, N, K, Nt), dtype=np.complex128) if need_diag_af else None
        for q in range(Q):
            td_l, qp_k = [], []
            for k in range(K):
                qp = [(g * np.exp(1j * 2.0 * np.pi * nu * 1.125 * q), el, nu, an) for (g, el, nu, an) in users_paths[k]]
                qp_k.append(qp)
                Hk_td = np.zeros((N, N * Nt), dtype=np.complex128)
                for alpha_p, ell_p, nu_p, theta_p in qp:
                    idx_fwd = (n_idx + ell_p) % N
                    cpp = np.where(idx_fwd < ell_p, np.exp(-1j * 2.0 * np.pi * c1_val * (N * N - 2.0 * N * (ell_p - idx_fwd))), 1.0 + 0.0j)
                    dop = np.exp(1j * 2.0 * np.pi * nu_p * idx_fwd / float(N))
                    AT_p = A_mat[:, idx_fwd] * (alpha_p * dop * cpp)[None, :]
                    a_conj = np.conj(ula_steering(Nt, theta_p, unit_norm=False))
                    Hk_td += np.kron(AT_p, a_conj[None, :])
                    if need_diag_af:
                        diag_ep = np.sum(AT_p * np.conj(A_mat), axis=1)
                        H_diag_af[q, :, k, :] += diag_ep[:, None] * a_conj[None, :]
                td_l.append(Hk_td)
            H_td.append(np.vstack(td_l))
            q_paths_all.append(qp_k)
        return H_td, H_diag_af, q_paths_all

    H_td_stack_q, H_diag_af_q, q_paths_af = build_channels(A, c1, True)
    H_td_c1z_q, _, q_paths_c1z = build_channels(A_c1z, 0.0, False)

    s_cm = np.zeros(N, dtype=np.complex128)
    s_cm[m_rad] = 1.0
    u_chirp = idaft_col(s_cm, lc1, lc2)
    u_chirp_c1z = idaft_col(s_cm, lc1_0, lc2_keep)
    A_rad_op = np.kron(np.eye(N), a_tar_unit.conj()[None, :])
    U_orth, _, _ = np.linalg.svd(np.eye(Nt) - np.outer(a_tar_unit, np.conj(a_tar_unit)))
    B_orth_blk = np.kron(np.eye(N), U_orth[:, :Nt - 1])

    Qc_rc_af_list = [qr(np.vstack([H_td_stack_q[q], A_rad_op]).conj().T, mode="economic") for q in range(Q)]
    Qc_af_list = [pair[0] for pair in Qc_rc_af_list]
    Qh_af_rm_list = [qr(H_td_stack_q[q].conj().T, mode="economic") for q in range(Q)]

    rho_c = 0.89 if pa_model == "rapp" else 0.95
    preinv_max_pow_gain = (1.0 / ((1.0 - (rho_c ** 5.0)) ** 0.4)) if (pa_model == "rapp" and not z0_kind) else 1.0

    X_a1_raw, g_lin_a1, wmmse_obj, wmmse_diag = build_liu26_wmmse_mm_cpi(
        H_td_stack_q, Qc_af_list, A_rad_op, u_chirp, d_cpi, K, N, Nt, sigma2, P_nom,
        gamma_s_frac=0.38, min_iter=16, max_iter=60, rel_tol=1e-3,
    )
    X_a2_preinv = bounded_pa_preinv(X_a1_raw, a_sat, pa_model, 2.5, rho_c)
    mean_pa2 = float(np.mean(np.sum(np.abs(X_a2_preinv) ** 2, axis=(1, 2))))
    if mean_pa2 > P_nom:
        X_a2_preinv *= np.sqrt(P_nom / mean_pa2)

    Y_a1_out = apply_pa_elem(X_a1_raw, a_sat, pa_model, 2.5)
    p_rad_cap = float(np.mean(np.sum(np.abs(Y_a1_out) ** 2, axis=(1, 2)))) if not z0_kind else P_nom
    p_eff_cap = min(p_rad_cap, P_nom / preinv_max_pow_gain)
    X_a3_bo = (1.0 if z0_kind else (10.0 ** (-7.5 / 20.0))) * X_a1_raw

    # Matched Studer (IEEE J-STSP 2013) 100-step minimum-l_inf ADMM pair:
    #   Rival_b1_PerBinStuderMinLinf (per-DAFT-bin diagonal) vs Rival_b2_FullBlockStuderMinLinf (full coupled H_q)
    X_b1_studer, st_b1, X_b2_studer, st_b2 = solve_studer_min_linf_pair_cpi(
        H_diag_af_q, H_td_stack_q, Qc_rc_af_list, a_tar_unit, u_chirp, A_rad_op,
        d_cpi, lc1, lc2, m_rad, P_nom, n_admm=100,
    )

    def run_dr_batched(Qc_stack, Y_min, Z_init, r_max, p_cap_val: float):
        Qc_H = np.conj(np.transpose(Qc_stack, (0, 2, 1)))
        Z = Z_init.copy()
        for _ in range(40):
            proj_coeff = np.einsum("qmd,qd->qm", Qc_H, Z)
            Ya = Z - np.einsum("qdm,qm->qd", Qc_stack, proj_coeff) + Y_min
            Yd = exact_proj_disk_l2_ball_batched(2.0 * Ya - Z, r_max, p_cap_val)
            Z = Z + (Yd - Ya)
        proj_coeff = np.einsum("qmd,qd->qm", Qc_H, Z)
        Ya = Z - np.einsum("qdm,qm->qd", Qc_stack, proj_coeff) + Y_min
        return exact_proj_disk_l2_ball_batched(Ya, r_max, p_cap_val).reshape(Q, N, Nt)

    def run_dr_family_from_qr(Qc_l, Qh_rm_l, H_td_l, u_ch_vec, sig2_val: float, p_cap_val: float, compute_ablations: bool):
        """
        Strict single-factor design across Prop, Abl_Aonly, Abl_Bonly, Abl_NoPreInv, and Diag_c1Zero:
          - Prop: 40-step exact DR from minimum-norm point Y_min of { H_q y = b_comm_q, A_rad y = u_des } cap D(r_max, p_cap_val) + M3;
          - Abl_NoPreInv: exact same Y_fin without M3;
          - Abl_Bonly: exact same Y_min (n_dr = 0) + p_cap_val ball + M3;
          - Abl_Aonly: exact same b_comm_q RHS, starting from minimum-norm point Y_min_h of { H_q y = b_comm_q } ONLY
            (deleting ONLY A_rad y = u_des, ZERO recomputed RHS and ZERO random nullspace injection!) + 40-step DR + M3.
        """
        u_des = np.sqrt(0.36 * p_cap_val) * u_ch_vec
        y_rad_base = A_rad_op.conj().T @ u_des
        cap_comm = (0.78 - 0.36) * p_cap_val

        Yc1 = np.zeros((Q, N * Nt), dtype=np.complex128)
        Yr_leak_comp = np.zeros((Q, N * Nt), dtype=np.complex128)
        gams = []
        for q in range(Q):
            Hq = H_td_l[q]
            H_or = Hq @ B_orth_blk
            Minv = np.linalg.inv(H_or @ H_or.conj().T + K * sig2_val * np.eye(K * N))
            yc_unit = B_orth_blk @ (H_or.conj().T @ (Minv @ d_cpi[q].reshape(K * N)))
            yr_cancel = B_orth_blk @ (H_or.conj().T @ (Minv @ (-(Hq @ y_rad_base))))
            Yc1[q] = yc_unit
            Yr_leak_comp[q] = yr_cancel
            a_q = max(float(np.real(np.vdot(yc_unit, yc_unit))), 1e-15)
            b_q = float(np.real(np.vdot(yc_unit, yr_cancel)))
            c_q = float(np.real(np.vdot(yr_cancel, yr_cancel))) - cap_comm
            if c_q >= 0.0:
                g_q = np.sqrt(0.10 * p_cap_val / a_q)
            else:
                disc = max(b_q * b_q - a_q * c_q, 0.0)
                g_q = max((-b_q + np.sqrt(disc)) / a_q, 1e-6)
            gams.append(g_q)

        gam_cpi = float(min(gams))
        Qc_stack = np.stack(Qc_l, axis=0)
        Y_ref = y_rad_base[None, :] + gam_cpi * Yc1 + Yr_leak_comp
        Qc_H = np.conj(np.transpose(Qc_stack, (0, 2, 1)))
        Y_min = np.einsum("qdm,qm->qd", Qc_stack, np.einsum("qmd,qd->qm", Qc_H, Y_ref))
        b_comm_cpi = np.array([H_td_l[q] @ Y_min[q] for q in range(Q)]).reshape(Q, K, N)

        r_max = rho_c * a_sat
        Y_fin = run_dr_batched(Qc_stack, Y_min, Y_min, r_max, p_cap_val)
        X_m123 = bounded_pa_preinv(Y_fin, a_sat, pa_model, 2.5, rho_c) if not z0_kind else Y_fin.copy()
        if not compute_ablations:
            return X_m123, gam_cpi, b_comm_cpi, u_des

        # 1. Abl_NoPreInv_RawRapp: removes ONLY M3 on exact same Y_fin
        X_no_m3 = Y_fin.copy()

        # 2. Abl_Bonly_NoDiskProj: removes ONLY M1 (n_dr = 0 on exact same Y_min, p_cap_val, and M3)
        Y_bonly = exact_proj_disk_l2_ball_batched(Y_min, 1e9, p_cap_val).reshape(Q, N, Nt)
        X_bonly = bounded_pa_preinv(Y_bonly, a_sat, pa_model, 2.5, rho_c) if not z0_kind else Y_bonly.copy()

        # 3. Abl_Aonly_NoChirpPin: removes ONLY M2 (the A_rad y = u_des block), keeping exact same b_comm_cpi[q] RHS,
        #    exact minimum-norm start Z_init = Y_min_h, exact 40-step DR on D(r_max, p_cap_val), and exact M3!
        Qh_stack = np.stack([qr_pair[0] for qr_pair in Qh_rm_l], axis=0)
        Y_min_h = np.zeros((Q, N * Nt), dtype=np.complex128)
        for q in range(Q):
            Qh, Rh = Qh_rm_l[q]
            Y_min_h[q] = Qh @ solve_triangular(Rh.conj().T, b_comm_cpi[q].reshape(K * N), lower=True)
        Y_fin_a = run_dr_batched(Qh_stack, Y_min_h, Y_min_h, r_max, p_cap_val)
        X_aonly = bounded_pa_preinv(Y_fin_a, a_sat, pa_model, 2.5, rho_c) if not z0_kind else Y_fin_a.copy()

        return X_m123, X_aonly, X_bonly, X_no_m3, gam_cpi, b_comm_cpi, u_des

    X_prop, X_Aonly, X_Bonly, X_noM3, gam_prop, b_comm_prop, u_des_prop = run_dr_family_from_qr(
        Qc_af_list, Qh_af_rm_list, H_td_stack_q, u_chirp, sigma2, p_eff_cap, True
    )

    Qc_c1z_list = [qr(np.vstack([H_td_c1z_q[q], A_rad_op]).conj().T, mode="economic")[0] for q in range(Q)]
    X_c1zero, _, _, _ = run_dr_family_from_qr(Qc_c1z_list, None, H_td_c1z_q, u_chirp_c1z, sigma2, p_eff_cap, False)

    # Payload-independent deterministic Sui TCOM'26 Eq. (25)-(27) analytical Bussgang gain vector
    g_sui_a1 = sui_analytical_bussgang_gain_from_precoder(g_lin_a1, sigma_x2_det, a_sat, pa_model, 2.5)

    def eval_arm(X_in, q_paths_list, lc1_v, lc2_v, c1_val, noise_c, use_post_pa_ref: bool = False,
                 skip_radar: bool = False, check_res_params=None, g_sui_vec=None):
        X_out = apply_pa_elem(X_in, a_sat, pa_model, 2.5)
        blk_pin = np.sum(np.abs(X_in) ** 2, axis=(1, 2))
        blk_pout = np.sum(np.abs(X_out) ** 2, axis=(1, 2))
        Z_rx = np.zeros((Q, K, N), dtype=np.complex128)
        Z_clean = np.zeros((Q, K, N), dtype=np.complex128)
        for q in range(Q):
            Z_clean[q] = fast_forward_H_td(X_out[q], q_paths_list[q], Nt, c1_val, lc1_v, lc2_v)
            Z_rx[q] = Z_clean[q] + noise_c[q]
        idx_hat, g_hats = blind_rx_16qam_cpi(Z_rx, d_pil, alph)
        ser = float(np.mean(idx_hat != idx_true_pay))

        extra = {}
        if check_res_params is not None:
            b_comm_t, gam_t, u_des_t = check_res_params
            comm_aff_res = np.linalg.norm(Z_clean - b_comm_t) / max(np.linalg.norm(b_comm_t), 1e-15)
            comm_ideal_res = np.linalg.norm(Z_clean - gam_t * d_cpi) / max(np.linalg.norm(gam_t * d_cpi), 1e-15)
            u_out_all = np.einsum("qni,i->qn", X_out, np.conj(a_tar_unit))
            chirp_res = np.linalg.norm(u_out_all - u_des_t[None, :]) / max(np.sqrt(Q) * np.linalg.norm(u_des_t), 1e-15)
            extra["post_pa_comm_rel_res"] = float(comm_aff_res)
            extra["post_pa_ideal_constell_rel_res"] = float(comm_ideal_res)
            extra["post_pa_chirp_rel_res"] = float(chirp_res)

        if g_sui_vec is not None:
            idx_sui = np.zeros((Q, K, N - 1), dtype=np.int64)
            for k in range(K):
                gk = g_sui_vec[k] if abs(g_sui_vec[k]) > 1e-15 else (1.0 + 0.0j)
                z_s = (Z_rx[:, k, 1:] / gk).ravel()
                idx_sui[:, k, :] = np.argmin(np.abs(z_s[:, None] - alph[None, :]), axis=1).reshape(Q, N - 1)
            extra["ser_sui_analytical_bussgang"] = float(np.mean(idx_sui != idx_true_pay))
            extra["pilot_vs_sui_gain_rel_diff"] = float(np.linalg.norm(g_hats - g_sui_vec) / max(np.linalg.norm(g_sui_vec), 1e-15))

        if z0_kind or skip_radar:
            return {
                "ser": ser, "t_max": 0.0, "loc_ok": 0.0,
                "p_in_mean": float(np.mean(blk_pin)), "p_in_max": float(np.max(blk_pin)), "p_out_mean": float(np.mean(blk_pout)),
                **extra,
            }

        u_out = np.einsum("qni,i->qn", X_out, np.conj(a_tar_unit))
        u_dig = np.einsum("qni,i->qn", X_in, np.conj(a_tar_unit))
        n_idx = np.arange(N, dtype=np.int64)
        q_idx = np.arange(Q, dtype=np.float64)

        def mk_echo(ell, nu, amp):
            if abs(amp) < 1e-15:
                return np.zeros((Q, N), dtype=np.complex128)
            col = (n_idx - ell) % N
            cpp = np.where(n_idx < ell, np.exp(-1j * 2.0 * np.pi * c1_val * (N * N - 2.0 * N * (ell - n_idx))), 1.0 + 0.0j)
            df = np.exp(1j * 2.0 * np.pi * nu * n_idx / float(N))[None, :]
            ds = np.exp(1j * 2.0 * np.pi * nu * 1.125 * q_idx)[:, None]
            return amp * ds * ((u_out[:, col] * cpp[None, :]) * df)

        Y_rad = mk_echo(ell_s, nu_s, amp_s) + mk_echo(ell_w, nu_w, amp_w) + noise_rad
        U_ref = u_out if use_post_pa_ref else u_dig
        t_max, ell_hat, nu_hat = blind_two_stage_rd_scorer(Y_rad, U_ref, c1_val, ell_max_rad=6)
        loc_ok = 1.0 if (ell_hat == ell_w and abs(nu_hat - nu_w) <= 0.12) else 0.0
        return {
            "ser": ser, "t_max": t_max, "loc_ok": loc_ok,
            "p_in_mean": float(np.mean(blk_pin)), "p_in_max": float(np.max(blk_pin)), "p_out_mean": float(np.mean(blk_pout)),
            **extra,
        }

    res = {
        "Prop_Full_AFDM": eval_arm(X_prop, q_paths_af, lc1, lc2, c1, noise_comm, False, False, (b_comm_prop, gam_prop, u_des_prop)),
        "Rival_a1_Liu26_WMMSE_RawRapp": eval_arm(X_a1_raw, q_paths_af, lc1, lc2, c1, noise_comm, False, False, None, g_sui_a1),
        "Rival_a2_Liu26_WMMSE_PreInvRapp": eval_arm(X_a2_preinv, q_paths_af, lc1, lc2, c1, noise_comm, False),
        "Rival_a3_OptBackoff": eval_arm(X_a3_bo, q_paths_af, lc1, lc2, c1, noise_comm, False),
        "Rival_a4_Liu26_WMMSE_PostPACoupler": eval_arm(X_a1_raw, q_paths_af, lc1, lc2, c1, noise_comm, True),
        "Rival_b1_PerBinStuderMinLinf": eval_arm(X_b1_studer, q_paths_af, lc1, lc2, c1, noise_comm, False),
        "Rival_b2_FullBlockStuderMinLinf": eval_arm(X_b2_studer, q_paths_af, lc1, lc2, c1, noise_comm, False),
        "Abl_Aonly_NoChirpPin": eval_arm(X_Aonly, q_paths_af, lc1, lc2, c1, noise_comm, False),
        "Abl_Bonly_NoDiskProj": eval_arm(X_Bonly, q_paths_af, lc1, lc2, c1, noise_comm, False),
        "Abl_NoPreInv_RawRapp": eval_arm(X_noM3, q_paths_af, lc1, lc2, c1, noise_comm, False),
        "Diag_c1Zero_SameAlg": eval_arm(X_c1zero, q_paths_c1z, lc1_0, lc2_keep, 0.0, noise_comm, False),
        "_wmmse_diag": wmmse_diag,
        "_studer_b1_diag": st_b1,
        "_studer_b2_diag": st_b2,
    }

    if do_xsnr:
        # Strictly SNR-independent execution: Prop_24dB computes its own 24 dB p_eff_cap_24; rivals run at 28 dB!
        sig2_24 = 10.0 ** (-24.0 / 10.0)
        sig2_28 = 10.0 ** (-28.0 / 10.0)
        Xa1_24, _, _, wdiag_24 = build_liu26_wmmse_mm_cpi(
            H_td_stack_q, Qc_af_list, A_rad_op, u_chirp, d_cpi, K, N, Nt, sig2_24, P_nom, 0.38, 16, 60, 1e-3
        )
        Y_a1_out_24 = apply_pa_elem(Xa1_24, a_sat, pa_model, 2.5)
        p_eff_cap_24 = min(float(np.mean(np.sum(np.abs(Y_a1_out_24) ** 2, axis=(1, 2)))), P_nom / preinv_max_pow_gain)
        X_prop_24, _, _, _ = run_dr_family_from_qr(Qc_af_list, None, H_td_stack_q, u_chirp, sig2_24, p_eff_cap_24, False)

        Xa1_28, _, _, wdiag_28 = build_liu26_wmmse_mm_cpi(
            H_td_stack_q, Qc_af_list, A_rad_op, u_chirp, d_cpi, K, N, Nt, sig2_28, P_nom, 0.38, 16, 60, 1e-3
        )
        Xa2_28 = bounded_pa_preinv(Xa1_28, a_sat, pa_model, 2.5, rho_c)
        mp28 = float(np.mean(np.sum(np.abs(Xa2_28) ** 2, axis=(1, 2))))
        if mp28 > P_nom:
            Xa2_28 *= np.sqrt(P_nom / mp28)
        # Studer minimum-l_inf precoders solve SNR-independent equality systems
        res["_xsnr"] = {
            "Prop_24dB_ser": eval_arm(X_prop_24, q_paths_af, lc1, lc2, c1, np.sqrt(sig2_24) * unit_noise_comm, False, True)["ser"],
            "Rival_a1_28dB_ser": eval_arm(Xa1_28, q_paths_af, lc1, lc2, c1, np.sqrt(sig2_28) * unit_noise_comm, False, True)["ser"],
            "Rival_a2_28dB_ser": eval_arm(Xa2_28, q_paths_af, lc1, lc2, c1, np.sqrt(sig2_28) * unit_noise_comm, False, True)["ser"],
            "Rival_b1_28dB_ser": eval_arm(X_b1_studer, q_paths_af, lc1, lc2, c1, np.sqrt(sig2_28) * unit_noise_comm, False, True)["ser"],
            "Rival_b2_28dB_ser": eval_arm(X_b2_studer, q_paths_af, lc1, lc2, c1, np.sqrt(sig2_28) * unit_noise_comm, False, True)["ser"],
            "wmmse_diag_24dB": wdiag_24,
            "wmmse_diag_28dB": wdiag_28,
        }
    return res


def summarize_block(cal_list: list, val_list: list, pos_list: list, alpha_pfa: float = 0.05):
    arms = [k for k in pos_list[0].keys() if not k.startswith("_")]
    n_cal = len(cal_list)
    k_ord = int(np.ceil((1.0 - alpha_pfa) * (n_cal + 1)))
    out_arms, hits_dict, sers_dict = {}, {}, {}

    for a in arms:
        cal_scores = np.sort([r[a]["t_max"] for r in cal_list])
        assert len(np.unique(cal_scores)) == len(cal_scores), f"Tie detected in H0_cal for {a}"
        tau = float(cal_scores[k_ord - 1])

        sers = np.array([r[a]["ser"] for r in pos_list], dtype=np.float64)
        hits = np.array([1.0 if (r[a]["t_max"] > tau and r[a]["loc_ok"] > 0.5) else 0.0 for r in pos_list], dtype=np.float64)
        sers_dict[a] = sers
        hits_dict[a] = hits

        val_fa_cnt = int(np.sum([1 for r in val_list if r[a]["t_max"] > tau])) if val_list else 0
        n_val = len(val_list)
        out_arms[a] = {
            "tau_pfa05": tau,
            "k_ord_1based": k_ord,
            "n_cal": n_cal,
            "n_val": n_val,
            "val_fa_count": val_fa_cnt,
            "val_pfa": (val_fa_cnt / float(n_val)) if n_val > 0 else None,
            "ser_mean": float(np.mean(sers)),
            "ser_sd": float(np.std(sers, ddof=1)),
            "loc_pd_mean": float(np.mean(hits)),
            "joint_J8_mean": float(np.mean(((1.0 - sers) ** 8) * hits)),
            "p_in_mean": float(np.mean([r[a]["p_in_mean"] for r in pos_list])),
            "p_in_max": float(np.max([r[a]["p_in_max"] for r in pos_list])),
            "p_out_mean": float(np.mean([r[a]["p_out_mean"] for r in pos_list])),
        }
    return out_arms, sers_dict, hits_dict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true", help="Fast smoke run on disjoint seeds 410000..475999")
    ap.add_argument("--require-afdm-env", action="store_true")
    ap.add_argument("--out", type=str, default="summary_h_r13_h01.json")
    args = ap.parse_args()

    assert 1 <= args.workers <= 8, f"Workers must be <= 8 (got {args.workers})"
    if args.require_afdm_env:
        assert sys.executable == "/home/guoyikun/.conda/envs/AFDM/bin/python", f"Wrong python: {sys.executable}"

    t_start = time.time()
    r1_info = verify_redline1_and_invariants()
    print("REDLINE1_AND_INVARIANTS_PASS:", json.dumps(r1_info, allow_nan=False), flush=True)

    if args.smoke:
        n_z0_flat, n_z0_mp, n_cal, n_val, n_pos, n_xsnr, n_cal_s2, n_pos_s2 = 4, 4, 19, 20, 12, 6, 19, 6
        seed_shift = -500000  # disjoint smoke seeds 410000..475005
    else:
        n_z0_flat, n_z0_mp, n_cal, n_val, n_pos, n_xsnr, n_cal_s2, n_pos_s2 = 64, 64, 399, 400, 1040, 256, 199, 96
        seed_shift = 0

    # Frozen disjoint seed ranges (zero overlap with Stage A 1000..7999, Stage C 8000..8999, Dev 110000..599999, Smoke 210000..475999)
    seeds_z0_flat = [910000 + seed_shift + i for i in range(n_z0_flat)]
    seeds_z0_mp = [920000 + seed_shift + i for i in range(n_z0_mp)]
    seeds_cal = [930000 + seed_shift + i for i in range(n_cal)]
    seeds_val = [940000 + seed_shift + i for i in range(n_val)]
    seeds_pos = [950000 + seed_shift + i for i in range(n_pos)]
    seeds_cal_s2 = [960000 + seed_shift + i for i in range(n_cal_s2)]
    seeds_pos_s2 = [965000 + seed_shift + i for i in range(n_pos_s2)]
    seeds_cal_s3 = [970000 + seed_shift + i for i in range(n_cal_s2)]
    seeds_pos_s3 = [975000 + seed_shift + i for i in range(n_pos_s2)]

    all_used = set(seeds_z0_flat + seeds_z0_mp + seeds_cal + seeds_val + seeds_pos + seeds_cal_s2 + seeds_pos_s2 + seeds_cal_s3 + seeds_pos_s3)
    assert len(all_used) == (n_z0_flat + n_z0_mp + n_cal + n_val + n_pos + 2 * n_cal_s2 + 2 * n_pos_s2), "Seed collision!"
    if not args.smoke:
        assert min(all_used) >= 910000, "Seed range violation!"

    with Pool(processes=args.workers) as pool:
        z0_flat_res = pool.map(run_scene_worker, [(s, "H0", 30.0, 8, 3, "rapp", "flat", False) for s in seeds_z0_flat])
        z0_mp_res = pool.map(run_scene_worker, [(s, "H0", 30.0, 8, 3, "rapp", "mp", False) for s in seeds_z0_mp])
        cal_res = pool.map(run_scene_worker, [(s, "H0", 26.0, 8, 3, "rapp", "", False) for s in seeds_cal])
        val_res = pool.map(run_scene_worker, [(s, "H0", 26.0, 8, 3, "rapp", "", False) for s in seeds_val])
        pos_res = pool.map(run_scene_worker, [(s, "H1", 26.0, 8, 3, "rapp", "", idx < n_xsnr) for idx, s in enumerate(seeds_pos)])
        cal_s2_res = pool.map(run_scene_worker, [(s, "H0", 26.0, 12, 4, "rapp", "", False) for s in seeds_cal_s2])
        pos_s2_res = pool.map(run_scene_worker, [(s, "H1", 26.0, 12, 4, "rapp", "", False) for s in seeds_pos_s2])
        cal_s3_res = pool.map(run_scene_worker, [(s, "H0", 26.0, 8, 3, "sel", "", False) for s in seeds_cal_s3])
        pos_s3_res = pool.map(run_scene_worker, [(s, "H1", 26.0, 8, 3, "sel", "", False) for s in seeds_pos_s3])

    arms_all = [k for k in pos_res[0].keys() if not k.startswith("_")]
    mp_arms = [a for a in arms_all if a != "Rival_b1_PerBinStuderMinLinf"]

    z0_flat_sers = {a: float(np.mean([r[a]["ser"] for r in z0_flat_res])) for a in arms_all}
    z0_flat_sers["Rival_a1_SuiAnalyticalBussgang"] = float(np.mean([r["Rival_a1_Liu26_WMMSE_RawRapp"]["ser_sui_analytical_bussgang"] for r in z0_flat_res]))
    z0_mp_sers = {a: float(np.mean([r[a]["ser"] for r in z0_mp_res])) for a in arms_all}
    z0_mp_sers["Rival_a1_SuiAnalyticalBussgang"] = float(np.mean([r["Rival_a1_Liu26_WMMSE_RawRapp"]["ser_sui_analytical_bussgang"] for r in z0_mp_res]))

    z0_flat_max = max(z0_flat_sers.values())
    z0_mp_max_capable = max(z0_mp_sers[a] for a in (mp_arms + ["Rival_a1_SuiAnalyticalBussgang"]))
    z0_max_post_pa_res = max(
        max(r["Prop_Full_AFDM"]["post_pa_comm_rel_res"] for r in z0_flat_res),
        max(r["Prop_Full_AFDM"]["post_pa_chirp_rel_res"] for r in z0_flat_res),
        max(r["Prop_Full_AFDM"]["post_pa_comm_rel_res"] for r in z0_mp_res),
        max(r["Prop_Full_AFDM"]["post_pa_chirp_rel_res"] for r in z0_mp_res),
    )

    primary_arms, sers, hits = summarize_block(cal_res, val_res, pos_res, alpha_pfa=0.05)
    s2_arms, _, _ = summarize_block(cal_s2_res, [], pos_s2_res, alpha_pfa=0.05)
    s3_arms, _, _ = summarize_block(cal_s3_res, [], pos_s3_res, alpha_pfa=0.05)

    sers["Rival_a1_SuiAnalyticalBussgang"] = np.array(
        [r["Rival_a1_Liu26_WMMSE_RawRapp"]["ser_sui_analytical_bussgang"] for r in pos_res], dtype=np.float64
    )
    pilot_vs_sui_gain_diff = float(np.mean([r["Rival_a1_Liu26_WMMSE_RawRapp"]["pilot_vs_sui_gain_rel_diff"] for r in pos_res]))
    mean_post_pa_comm_res = float(np.mean([r["Prop_Full_AFDM"]["post_pa_comm_rel_res"] for r in pos_res]))
    mean_post_pa_ideal_res = float(np.mean([r["Prop_Full_AFDM"]["post_pa_ideal_constell_rel_res"] for r in pos_res]))
    mean_post_pa_chirp_res = float(np.mean([r["Prop_Full_AFDM"]["post_pa_chirp_rel_res"] for r in pos_res]))

    # Comprehensive per-scene WMMSE-MM monotonicity, per-scene max < 1% convergence, & per-block exact power audit
    # across ALL branches (Z0_flat, Z0_mp, H0_cal, H0_val, H1 26dB, P1b 24dB, P1b 28dB, S2_Nt12K4, S3_SEL)!
    wmmse_branches = {
        "z0_flat": [r["_wmmse_diag"] for r in z0_flat_res],
        "z0_mp": [r["_wmmse_diag"] for r in z0_mp_res],
        "h0_cal": [r["_wmmse_diag"] for r in cal_res],
        "h0_val": [r["_wmmse_diag"] for r in val_res],
        "h1_26dB": [r["_wmmse_diag"] for r in pos_res],
        "p1b_24dB": [pos_res[i]["_xsnr"]["wmmse_diag_24dB"] for i in range(n_xsnr)],
        "p1b_28dB": [pos_res[i]["_xsnr"]["wmmse_diag_28dB"] for i in range(n_xsnr)],
        "s2_Nt12K4": [r["_wmmse_diag"] for r in (cal_s2_res + pos_s2_res)],
        "s3_SEL": [r["_wmmse_diag"] for r in (cal_s3_res + pos_s3_res)],
    }
    wmmse_mono_all = bool(all(d["monotone"] for diag_list in wmmse_branches.values() for d in diag_list))
    wmmse_rel_last_max_by_branch = {
        k_br: float(max(d["rel_last_step"] for d in diag_list)) for k_br, diag_list in wmmse_branches.items()
    }
    wmmse_rel_last_mean_by_branch = {
        k_br: float(np.mean([d["rel_last_step"] for d in diag_list])) for k_br, diag_list in wmmse_branches.items()
    }
    wmmse_max_blk_pow_err = float(
        max(d["max_blk_pow_err"] for diag_list in wmmse_branches.values() for d in diag_list)
    )
    wmmse_max_aperp_null_err = float(
        max(d["max_aperp_null_err"] for diag_list in wmmse_branches.values() for d in diag_list)
    )
    wmmse_conv_ok = bool(
        wmmse_mono_all
        and all(v < 0.010 for v in wmmse_rel_last_max_by_branch.values())
        and (wmmse_max_blk_pow_err < 1e-9)
        and (wmmse_max_aperp_null_err < 1e-12)
    )

    # Studer 100-step ADMM solver end-to-end iterate consistency, Boyd dual residual, peak stabilization,
    # AND exact Holder (l_1, l_inf) global relative duality-gap certificate across ALL scenes (incl. Z0_mp & H1)!
    all_scene_lists = [z0_flat_res, z0_mp_res, cal_res, val_res, pos_res, cal_s2_res, pos_s2_res, cal_s3_res, pos_s3_res]
    studer_b1_iter_primal_max_all = float(max(r["_studer_b1_diag"]["iter_primal_rel_max"] for lst in all_scene_lists for r in lst))
    studer_b2_iter_primal_max_all = float(max(r["_studer_b2_diag"]["iter_primal_rel_max"] for lst in all_scene_lists for r in lst))
    studer_b1_dual_rel_max_all = float(max(r["_studer_b1_diag"]["dual_rel_max"] for lst in all_scene_lists for r in lst))
    studer_b2_dual_rel_max_all = float(max(r["_studer_b2_diag"]["dual_rel_max"] for lst in all_scene_lists for r in lst))
    studer_b1_peak_step_max_all = float(max(r["_studer_b1_diag"]["peak_step_rel_max"] for lst in all_scene_lists for r in lst))
    studer_b2_peak_step_max_all = float(max(r["_studer_b2_diag"]["peak_step_rel_max"] for lst in all_scene_lists for r in lst))
    studer_b1_dgap_max_z0_mp = float(max(r["_studer_b1_diag"]["rel_duality_gap_max"] for r in z0_mp_res))
    studer_b2_dgap_max_z0_mp = float(max(r["_studer_b2_diag"]["rel_duality_gap_max"] for r in z0_mp_res))
    studer_b1_dgap_max_all = float(max(r["_studer_b1_diag"]["rel_duality_gap_max"] for lst in all_scene_lists for r in lst))
    studer_b2_dgap_max_all = float(max(r["_studer_b2_diag"]["rel_duality_gap_max"] for lst in all_scene_lists for r in lst))
    studer_peak_ratio_max_all = float(
        max(max(r["_studer_b1_diag"]["peak_vs_l2min_max_ratio"], r["_studer_b2_diag"]["peak_vs_l2min_max_ratio"]) for lst in all_scene_lists for r in lst)
    )
    studer_admm_conv_ok = bool(
        (studer_b1_iter_primal_max_all <= 0.010)
        and (studer_b2_iter_primal_max_all <= 0.010)
        and (studer_b1_dual_rel_max_all <= 0.010)
        and (studer_b2_dual_rel_max_all <= 0.010)
        and (studer_b1_peak_step_max_all <= 0.010)
        and (studer_b2_peak_step_max_all <= 0.010)
        and (studer_b1_dgap_max_all <= 0.025)
        and (studer_b2_dgap_max_all <= 0.025)
        and (studer_peak_ratio_max_all <= 1.0 + 1e-9)
    )

    n_arms_fwer = len(arms_all)
    k_ord = primary_arms["Prop_Full_AFDM"]["k_ord_1based"]
    a_bb = n_cal + 1 - k_ord
    b_bb = k_ord
    bb_lo = int(betabinom.ppf(0.005 / float(n_arms_fwer), n_val, a_bb, b_bb))
    bb_hi = int(betabinom.ppf(1.0 - 0.005 / float(n_arms_fwer), n_val, a_bb, b_bb))
    if not args.smoke:
        assert (bb_lo, bb_hi) == (4, 45), f"Expected exact BetaBinomial(400,20,380) 11-arm interval [4, 45], got [{bb_lo}, {bb_hi}]"
    pfa_all_ok = all(bb_lo <= primary_arms[a]["val_fa_count"] <= bb_hi for a in arms_all)

    P_nom = 64.0
    pow_ok = (
        primary_arms["Prop_Full_AFDM"]["p_in_max"] <= P_nom + 1e-9
        and primary_arms["Prop_Full_AFDM"]["p_out_mean"] <= primary_arms["Rival_a1_Liu26_WMMSE_RawRapp"]["p_out_mean"] + 1e-9
        and (wmmse_max_blk_pow_err < 1e-9)
    )
    res_ok = (
        z0_max_post_pa_res < 1e-12
        and mean_post_pa_comm_res <= 0.050
        and mean_post_pa_chirp_res <= 0.050
    )

    G_HYGIENE = bool(
        (r1_info["redline1_max_err"] < 1e-12)
        and (r1_info["uc_subspace_null_err"] < 1e-15)
        and (z0_flat_max < 0.010)
        and (z0_mp_max_capable < 0.010)
        and wmmse_conv_ok
        and studer_admm_conv_ok
        and pfa_all_ok
        and pow_ok
        and res_ok
    )

    # P1: Communication Saturation Floor Wall-Breaking (M=5 Bonferroni across 5 published/port 0dB-IBO rivals + M=3 Cross-SNR
    #     + P1c Studer per-bin vs full-channel coupling attribution + P1d Prop vs full-channel+chirp Studer control)
    sat_rivals = [
        "Rival_a1_Liu26_WMMSE_RawRapp",
        "Rival_a1_SuiAnalyticalBussgang",
        "Rival_a2_Liu26_WMMSE_PreInvRapp",
        "Rival_a4_Liu26_WMMSE_PostPACoupler",
        "Rival_b1_PerBinStuderMinLinf",
    ]
    p1a_stats = {r: paired_t_ci(sers[r] - sers["Prop_Full_AFDM"], alpha=0.05, bonf_m=5) for r in sat_rivals}
    P1a_ok = all(st["ci_low"] >= 0.080 and st["ci_hw"] <= 0.0200 for st in p1a_stats.values())

    prop_24 = np.array([pos_res[i]["_xsnr"]["Prop_24dB_ser"] for i in range(n_xsnr)], dtype=np.float64)
    xsnr_rivals = ["Rival_a1_28dB_ser", "Rival_a2_28dB_ser", "Rival_b1_28dB_ser"]
    p1b_stats = {
        rk: paired_t_ci(np.array([pos_res[i]["_xsnr"][rk] for i in range(n_xsnr)], dtype=np.float64) - prop_24, alpha=0.05, bonf_m=3)
        for rk in xsnr_rivals
    }
    p1b_b2_diag = paired_t_ci(np.array([pos_res[i]["_xsnr"]["Rival_b2_28dB_ser"] for i in range(n_xsnr)], dtype=np.float64) - prop_24, alpha=0.05, bonf_m=1)
    # P1c: Paired pure single-factor attribution of Rival_b1's collapse to per-bin diagonal approximation (b1 vs b2 on Z0_mp & H1)
    z0_mp_b1_minus_b2 = paired_t_ci(
        np.array([r["Rival_b1_PerBinStuderMinLinf"]["ser"] - r["Rival_b2_FullBlockStuderMinLinf"]["ser"] for r in z0_mp_res], dtype=np.float64),
        alpha=0.05, bonf_m=1,
    )
    h1_b1_minus_b2 = paired_t_ci(sers["Rival_b1_PerBinStuderMinLinf"] - sers["Rival_b2_FullBlockStuderMinLinf"], alpha=0.05, bonf_m=1)
    P1c_studer_attr_ok = bool(
        (z0_mp_b1_minus_b2["ci_low"] >= 0.500 and z0_mp_b1_minus_b2["ci_hw"] <= 0.1250)
        and (h1_b1_minus_b2["ci_low"] >= 0.500 and h1_b1_minus_b2["ci_hw"] <= 0.1250)
    )
    # P1d: Paired superiority of Prop (RZF + interior disk-ball D(rho_c A_sat, p_eff_cap) + M3 pre-inversion) over
    #      synthetic full-coupled + chirp-pinned Studer min-l_inf control Rival_b2_FullBlockStuderMinLinf at 0 dB IBO:
    j8_prop_early = ((1.0 - sers["Prop_Full_AFDM"]) ** 8) * hits["Prop_Full_AFDM"]
    j8_b2 = ((1.0 - sers["Rival_b2_FullBlockStuderMinLinf"]) ** 8) * hits["Rival_b2_FullBlockStuderMinLinf"]
    p1d_b2_ser = paired_t_ci(sers["Rival_b2_FullBlockStuderMinLinf"] - sers["Prop_Full_AFDM"], alpha=0.05, bonf_m=1)
    p1d_b2_j8 = paired_t_ci(j8_prop_early - j8_b2, alpha=0.05, bonf_m=1)
    P1d_b2_superior_ok = bool(
        (p1d_b2_ser["ci_low"] >= 0.0080 and p1d_b2_ser["ci_hw"] <= 0.00200)
        and (p1d_b2_j8["ci_low"] >= 0.060 and p1d_b2_j8["ci_hw"] <= 0.0150)
    )
    P1b_ok = all(st["ci_low"] >= 0.080 and st["ci_hw"] <= 0.0200 for st in p1b_stats.values())
    P1 = bool(P1a_ok and P1b_ok and P1c_studer_attr_ok and P1d_b2_superior_ok)

    # P2: ISAC Backoff Pareto Dominance & Single-Factor c1=0 Non-Degeneracy
    j8_prop = ((1.0 - sers["Prop_Full_AFDM"]) ** 8) * hits["Prop_Full_AFDM"]
    j8_bo = ((1.0 - sers["Rival_a3_OptBackoff"]) ** 8) * hits["Rival_a3_OptBackoff"]
    p2a_pd_bo = newcombe_paired_ci(hits["Prop_Full_AFDM"], hits["Rival_a3_OptBackoff"])
    p2a_joint_bo = paired_t_ci(j8_prop - j8_bo, alpha=0.05, bonf_m=1)
    p2a_ser_bo = paired_t_ci(sers["Rival_a3_OptBackoff"] - sers["Prop_Full_AFDM"], alpha=0.05, bonf_m=1)
    p2a_pd_a1 = newcombe_paired_ci(hits["Prop_Full_AFDM"], hits["Rival_a1_Liu26_WMMSE_RawRapp"])
    p2b_c1z = newcombe_paired_ci(hits["Prop_Full_AFDM"], hits["Diag_c1Zero_SameAlg"])

    P2 = bool(
        (p2a_pd_bo["ci_low"] >= 0.280 and p2a_pd_bo["ci_hw"] <= 0.0700)
        and (p2a_joint_bo["ci_low"] >= 0.280 and p2a_joint_bo["ci_hw"] <= 0.0700)
        and (p2a_ser_bo["ci_low"] >= -0.0100 and p2a_ser_bo["ci_hw"] <= 0.00250)
        and (p2a_pd_a1["ci_low"] >= 0.160 and p2a_pd_a1["ci_hw"] <= 0.0400)
        and (p2b_c1z["ci_low"] >= 0.600 and p2b_c1z["ci_hw"] <= 0.1500)
    )

    # P3: Strict Single-Factor < 80% Bidirectional Ablations & Sub-Mechanism Attribution
    j8_base = ((1.0 - sers["Rival_a1_Liu26_WMMSE_RawRapp"]) ** 8) * hits["Rival_a1_Liu26_WMMSE_RawRapp"]
    j8_aonly = ((1.0 - sers["Abl_Aonly_NoChirpPin"]) ** 8) * hits["Abl_Aonly_NoChirpPin"]
    j8_bonly = ((1.0 - sers["Abl_Bonly_NoDiskProj"]) ** 8) * hits["Abl_Bonly_NoDiskProj"]

    eta_A = paired_recovery_bootstrap(j8_prop, j8_base, j8_aonly, n_boot=4000, seed=20261126)
    eta_B = paired_recovery_bootstrap(j8_prop, j8_base, j8_bonly, n_boot=4000, seed=20261127)
    p3b_m2 = newcombe_paired_ci(hits["Prop_Full_AFDM"], hits["Abl_Aonly_NoChirpPin"])
    p3b_m1 = paired_t_ci(sers["Abl_Bonly_NoDiskProj"] - sers["Prop_Full_AFDM"], alpha=0.05, bonf_m=1)
    p3b_m3 = paired_t_ci(sers["Abl_NoPreInv_RawRapp"] - sers["Prop_Full_AFDM"], alpha=0.05, bonf_m=1)

    P3a_ok = bool(
        eta_A["denom_valid"] and (eta_A["ci_high"] < 0.80 and eta_A["ci_hw"] <= 0.200)
        and eta_B["denom_valid"] and (eta_B["ci_high"] < 0.80 and eta_B["ci_hw"] <= 0.200)
    )
    P3b_ok = bool(
        (p3b_m2["ci_low"] >= 0.550 and p3b_m2["ci_hw"] <= 0.1375)
        and (p3b_m1["ci_low"] >= 0.040 and p3b_m1["ci_hw"] <= 0.0100)
        and (p3b_m3["ci_low"] >= 0.0036 and p3b_m3["ci_hw"] <= 0.00090)
    )
    P3 = bool(P3a_ok and P3b_ok)
    PASS_PRIMARY = bool(G_HYGIENE and P1 and P2 and P3)

    script_md5 = hashlib.md5(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    summary = {
        "card_id": "I-20261126-h01",
        "_argv": sys.argv,
        "_config": {
            "python_executable": sys.executable,
            "script_md5": script_md5,
            "workers": args.workers,
            "smoke": args.smoke,
            "sample_sizes": {
                "n_z0_flat": n_z0_flat, "n_z0_mp": n_z0_mp, "n_cal": n_cal, "n_val": n_val,
                "n_pos": n_pos, "n_xsnr": n_xsnr, "n_cal_s2": n_cal_s2, "n_pos_s2": n_pos_s2,
            },
            "seed_ranges": {
                "z0_flat": [seeds_z0_flat[0], seeds_z0_flat[-1]],
                "z0_mp": [seeds_z0_mp[0], seeds_z0_mp[-1]],
                "cal": [seeds_cal[0], seeds_cal[-1]],
                "val": [seeds_val[0], seeds_val[-1]],
                "pos": [seeds_pos[0], seeds_pos[-1]],
                "s2_Nt12K4": [seeds_cal_s2[0], seeds_pos_s2[-1]],
                "s3_SEL": [seeds_cal_s3[0], seeds_pos_s3[-1]],
            },
        },
        "elapsed_sec": time.time() - t_start,
        "redline1": r1_info,
        "hygiene": {
            "z0_flat_sers": z0_flat_sers,
            "z0_flat_max": z0_flat_max,
            "z0_mp_sers": z0_mp_sers,
            "z0_mp_max_capable": z0_mp_max_capable,
            "z0_max_post_pa_rel_res": z0_max_post_pa_res,
            "h1_mean_post_pa_comm_rel_res": mean_post_pa_comm_res,
            "h1_mean_post_pa_ideal_constell_rel_res": mean_post_pa_ideal_res,
            "h1_mean_post_pa_chirp_rel_res": mean_post_pa_chirp_res,
            "sui_analytical_bussgang_ser_mean": float(np.mean(sers["Rival_a1_SuiAnalyticalBussgang"])),
            "pilot_vs_sui_gain_rel_diff_mean": pilot_vs_sui_gain_diff,
            "wmmse_monotone_all_runs": wmmse_mono_all,
            "wmmse_rel_last_step_max_by_branch": wmmse_rel_last_max_by_branch,
            "wmmse_rel_last_step_mean_by_branch": wmmse_rel_last_mean_by_branch,
            "wmmse_max_blk_pow_err": wmmse_max_blk_pow_err,
            "wmmse_max_aperp_null_err": wmmse_max_aperp_null_err,
            "wmmse_convergence_ok": wmmse_conv_ok,
            "studer_b1_iter_primal_rel_max_all": studer_b1_iter_primal_max_all,
            "studer_b2_iter_primal_rel_max_all": studer_b2_iter_primal_max_all,
            "studer_b1_dual_rel_max_all": studer_b1_dual_rel_max_all,
            "studer_b2_dual_rel_max_all": studer_b2_dual_rel_max_all,
            "studer_b1_peak_step_rel_max_all": studer_b1_peak_step_max_all,
            "studer_b2_peak_step_rel_max_all": studer_b2_peak_step_max_all,
            "studer_b1_rel_duality_gap_max_z0_mp": studer_b1_dgap_max_z0_mp,
            "studer_b2_rel_duality_gap_max_z0_mp": studer_b2_dgap_max_z0_mp,
            "studer_b1_rel_duality_gap_max_all": studer_b1_dgap_max_all,
            "studer_b2_rel_duality_gap_max_all": studer_b2_dgap_max_all,
            "studer_peak_vs_l2min_ratio_max_all": studer_peak_ratio_max_all,
            "studer_admm_convergence_ok": studer_admm_conv_ok,
            "betabinom_fwer99_bonf11_interval": [bb_lo, bb_hi],
            "pfa_all_ok": pfa_all_ok,
            "power_budget_ok": pow_ok,
            "post_pa_residual_ok": res_ok,
        },
        "primary_26dB_Rapp_Nt8K3": primary_arms,
        "tests": {
            "P1a_vs_sat_rivals_bonf5": p1a_stats,
            "P1b_cross_snr_28vs24_bonf3": p1b_stats,
            "P1b_b2_28vs24_diag": p1b_b2_diag,
            "P1c_studer_perbin_vs_full_z0_mp": z0_mp_b1_minus_b2,
            "P1c_studer_perbin_vs_full_h1_26dB": h1_b1_minus_b2,
            "P1d_full_studer_ctrl_ser_gap": p1d_b2_ser,
            "P1d_full_studer_ctrl_J8_gap": p1d_b2_j8,
            "P2a_pd_vs_backoff75dB": p2a_pd_bo,
            "P2a_joint_J8_vs_backoff75dB": p2a_joint_bo,
            "P2a_ser_noninf_vs_backoff75dB": p2a_ser_bo,
            "P2a_pd_vs_raw_liu26_wmmse": p2a_pd_a1,
            "P2b_pd_vs_c1_zero_keep_c2": p2b_c1z,
            "P3a_eta_A_bootstrap": eta_A,
            "P3a_eta_B_bootstrap": eta_B,
            "P3b_M2_pd_drop": p3b_m2,
            "P3b_M1_ser_rise": p3b_m1,
            "P3b_M3_ser_rise": p3b_m3,
        },
        "secondary_Nt12K4_Rapp": s2_arms,
        "secondary_Nt8K3_SEL": s3_arms,
        "verdicts": {
            "G_HYGIENE": G_HYGIENE,
            "P1a": P1a_ok,
            "P1b": P1b_ok,
            "P1c": P1c_studer_attr_ok,
            "P1d": P1d_b2_superior_ok,
            "P1": P1,
            "P2": P2,
            "P3a": P3a_ok,
            "P3b": P3b_ok,
            "P3": P3,
            "PASS_PRIMARY": PASS_PRIMARY,
        },
    }

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2, allow_nan=False)
    print(f"WROTE_SUMMARY={args.out} PASS_PRIMARY={PASS_PRIMARY} elapsed={summary['elapsed_sec']:.2f}s", flush=True)


if __name__ == "__main__":
    main()
