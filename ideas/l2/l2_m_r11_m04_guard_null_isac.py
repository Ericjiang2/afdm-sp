"""
Round-11 [放宽TWC] [轨B-ISAC] L2 Experiment Script for I-20261125-m04 (v7, post-Sol Call 15/15 exact order-stat & Beta-Binomial harmonization):
Self-Referenced Grassmannian Guard-Nullspace AFDM-ISAC
(Solving Ma et al., arXiv:2606.25572 Sec. III/VI compressed-guard unknown-data open problem).

Zero global id()-keyed caches; strictly disjoint seeds between --smoke (2028000000+) and full L2 (2030000000+);
fail-fast startup gates (sys.exit(2) on failure); exact Y. Luo Sec. IV posterior cross-covariance term & blind
noiseless recovery; exact order-statistic threshold X_(b) (b = n_cal + 1 - a, a = round(p * (n_cal + 1))) and
exact finite-sample Beta-Binomial predictive interval validation uniformly across NOMP startup gate and EVERY arm
in R1/R2/R3a/R3b/R0; genuine rank-deficient non-zero Hd stress test (rank 52 < 104); symmetric 1-factor ablations;
exact CPP-inclusive expected TX energy (138.0/frame) & zero-coupling (4.45e-13) R3c with strict BLER crossing.
"""
import os
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_k] = "1"

import sys
print(sys.executable, flush=True)

import argparse
import json
import math
import time
from multiprocessing import Pool
import numpy as np
from scipy.linalg import qr, cho_factor, cho_solve
from scipy.stats import betabinom as betabinom_dist

NOMP_CFAR_NCAL = 80000


def exact_order_stat_params(n_cal, pfa_target):
    """Exact order-statistic rank b so P = 1 - F(X_(b)) ~ Beta(a, b) with E[P] = a/(n_cal+1) ~= pfa_target."""
    a = max(1, int(round(pfa_target * (n_cal + 1))))
    b = n_cal + 1 - a
    if not (1 <= b <= n_cal):
        raise ValueError(f"Invalid order statistic rank b={b} for n_cal={n_cal}")
    return a, b


def exact_order_stat_threshold(cal_vals, pfa_target):
    """Exact 1-indexed order-statistic threshold X_(b) with b = n_cal + 1 - a, a = round(p * (n_cal + 1))."""
    arr = np.asarray(cal_vals, dtype=np.float64)
    a, b = exact_order_stat_params(len(arr), pfa_target)
    thr = float(np.partition(arr, b - 1)[b - 1])
    return thr, a, b


def exact_betabinom_interval(n_val, a, b, alpha_each=0.05):
    """Exact finite-sample Beta-Binomial predictive interval [k_lo, k_hi] for K = sum(val > X_(b))."""
    k_lo = int(betabinom_dist.ppf(alpha_each / 2.0, n_val, a, b))
    k_hi = int(betabinom_dist.ppf(1.0 - alpha_each / 2.0, n_val, a, b))
    return k_lo, k_hi

# ==============================================================================
# Core AFDM & Grassmannian Linear Algebra Primitives (NO global id() caches!)
# ==============================================================================
_CALL_COUNTERS = {"orth_nullspace_NG": 0, "refine_orth_null_gn": 0}


def daft_matrix(N, c1, c2):
    n = np.arange(N)
    F = np.exp(-1j * 2.0 * np.pi * np.outer(n, n) / N) / np.sqrt(N)
    return (np.exp(-1j * 2.0 * np.pi * c2 * n**2)[:, None] * F) * np.exp(-1j * 2.0 * np.pi * c1 * n**2)[None, :]


def build_cpp_ext(N, c1, L_cpp):
    """Chirp-periodic prefix extension matrix P_cpp ((N+L_cpp) x N), Bemani TWC'23 Eq.(5)."""
    P = np.zeros((N + L_cpp, N), dtype=complex)
    for k in range(L_cpp):
        n_neg = k - L_cpp
        P[k, N + n_neg] = np.exp(-1j * 2.0 * np.pi * c1 * (N * N + 2 * N * n_neg))
    P[L_cpp:, :] = np.eye(N)
    return P


def build_B_path(N, A, Ah, l_val, nu_val, Ah_f=None):
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    af = np.fft.fft(Ah, axis=0) if Ah_f is None else Ah_f
    Pi_Ah = np.fft.ifft(np.exp(-1j * 2.0 * np.pi * l_val * m_freq / N)[:, None] * af, axis=0)
    return A @ (np.exp(-1j * 2.0 * np.pi * nu_val * n / N)[:, None] * Pi_Ah)


def build_H_eff(N, A, Ah, hs, ls, nus, Ah_f=None):
    """Exact time-domain path accumulation followed by single A @ M_t matmul."""
    if len(hs) == 0:
        return np.zeros((N, N), dtype=complex)
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    af = np.fft.fft(Ah, axis=0) if Ah_f is None else Ah_f
    M_t = np.zeros((N, N), dtype=complex)
    for h, l_val, nu_val in zip(hs, ls, nus):
        Pi_Ah = np.fft.ifft(np.exp(-1j * 2.0 * np.pi * l_val * m_freq / N)[:, None] * af, axis=0)
        M_t += (h * np.exp(-1j * 2.0 * np.pi * nu_val * n / N))[:, None] * Pi_Ah
    return A @ M_t


def orth_nullspace_NG(H, data_mask, G):
    """Exact orthonormal basis N_G (N x G) for col(H E_D)^perp via column-pivoted QR."""
    _CALL_COUNTERS["orth_nullspace_NG"] += 1
    Hd = H[:, data_mask]
    if float(np.linalg.norm(Hd)) < 1e-12:
        N = H.shape[0]
        guard_idx = np.where(~data_mask)[0]
        E_G = np.zeros((N, G), dtype=complex)
        E_G[guard_idx, np.arange(G)] = 1.0
        return E_G
    Q, _, _ = qr(Hd, mode="full", pivoting=True, check_finite=False)
    return Q[:, -G:]


def isotropic_mf_map(r_res, xp, A, Ah, l_grid, nu_grid):
    N = len(r_res)
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    s_pf = np.fft.fft(Ah @ xp)
    r_t = Ah @ r_res
    E_nu = np.exp(-1j * 2.0 * np.pi * np.outer(n, nu_grid) / N)
    sc = np.zeros((len(l_grid), len(nu_grid)))
    for il, lv in enumerate(l_grid):
        s_del = np.fft.ifft(np.exp(-1j * 2.0 * np.pi * lv * m_freq / N) * s_pf)
        sc[il, :] = (np.abs((r_t.conj() * s_del) @ E_nu) ** 2) / (float(np.sum(np.abs(s_del) ** 2)) + 1e-12)
    return sc


def nomp_joint_refinement(y, xp, A, Ah, hs, ls, nus, n_cyc=2, n_newt=3, step_cap=0.25, win_idx=None, tol=1e-13):
    """NOMP (Mamandipoor TSP'16 / Shah TVT'25) F_N->A direct port cyclic variable-projection Newton
    with adaptive early-exit once parameter updates converge below `tol`.
    """
    N = len(y)
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    s_pf = np.fft.fft(Ah @ xp)
    P = len(ls)
    ls_c = [float(v) for v in ls]
    nus_c = [float(v) for v in nus]
    hs_c = [complex(v) for v in hs]

    if win_idx is None:
        r_ref = Ah @ y

        def atom_d(lv, nuv):
            dl_e = np.exp(-1j * 2.0 * np.pi * lv * m_freq / N)
            s_del = np.fft.ifft(dl_e * s_pf)
            ds_del = np.fft.ifft((-1j * 2.0 * np.pi * m_freq / N) * dl_e * s_pf)
            dop = np.exp(-1j * 2.0 * np.pi * nuv * n / N)
            a = dop * s_del
            return a, dop * ds_del, (-1j * 2.0 * np.pi * n / N) * a
    else:
        r_ref = y[win_idx]
        A_w = A[win_idx, :]

        def atom_d(lv, nuv):
            dl_e = np.exp(-1j * 2.0 * np.pi * lv * m_freq / N)
            s_del = np.fft.ifft(dl_e * s_pf)
            ds_del = np.fft.ifft((-1j * 2.0 * np.pi * m_freq / N) * dl_e * s_pf)
            dop = np.exp(-1j * 2.0 * np.pi * nuv * n / N)
            at = dop * s_del
            return A_w @ at, A_w @ (dop * ds_del), A_w @ ((-1j * 2.0 * np.pi * n / N) * at)

    prev_res = float("inf")
    for cyc in range(n_cyc):
        atoms = [atom_d(ls_c[p], nus_c[p])[0] for p in range(P)]
        max_dp = 0.0
        for p in range(P):
            res_p = r_ref - sum(hs_c[q] * atoms[q] for q in range(P) if q != p)
            lv, nuv = ls_c[p], nus_c[p]
            for _ in range(n_newt):
                a, dal, dan = atom_d(lv, nuv)
                aa = float(np.real(np.vdot(a, a))) + 1e-15
                hp = np.vdot(a, res_p) / aa
                dal_p = dal - (np.vdot(a, dal) / aa) * a
                dan_p = dan - (np.vdot(a, dan) / aa) * a
                J = np.column_stack([hp * dal_p, hp * dan_p])
                g = np.real(J.conj().T @ (res_p - hp * a))
                H_j = np.real(J.conj().T @ J) + 1e-13 * np.eye(2)
                try:
                    step = np.clip(np.linalg.solve(H_j, g), -step_cap, step_cap)
                except np.linalg.LinAlgError:
                    break
                lv += float(step[0])
                nuv += float(step[1])
                dp = max(abs(float(step[0])), abs(float(step[1])))
                if dp < tol:
                    break
            max_dp = max(max_dp, abs(lv - ls_c[p]), abs(nuv - nus_c[p]))
            ls_c[p], nus_c[p] = lv, nuv
            atoms[p] = atom_d(lv, nuv)[0]
        A_mat = np.column_stack(atoms)
        hs_c = list(np.linalg.lstsq(A_mat, r_ref, rcond=None)[0])
        cur_res = float(np.linalg.norm(r_ref - A_mat @ np.array(hs_c)))
        if max_dp < tol or cur_res < 1e-14:
            break
        if cyc >= 3 and cur_res > 1e-6 and abs(prev_res - cur_res) <= 1e-5 * prev_res:
            break
        prev_res = cur_res
    return np.array(hs_c, dtype=complex), np.array(ls_c, dtype=float), np.array(nus_c, dtype=float)


def grassmann_null_cost_and_grad(par, y, xp, data_mask, G, A, Ah, Ah_f=None):
    """Exact zero-approximation Golub-Pereyra Grassmannian cost J_null & Jacobian J_G.
    Uses exact pseudoinverse xd_hat = lstsq(Hd, r_full, rcond=1e-6) — NO ridge bias!
    """
    N = len(y)
    P = len(par) // 4
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    af = np.fft.fft(Ah, axis=0) if Ah_f is None else Ah_f
    hs = [par[4 * p] + 1j * par[4 * p + 1] for p in range(P)]
    ls = [par[4 * p + 2] for p in range(P)]
    nus = [par[4 * p + 3] for p in range(P)]
    H = build_H_eff(N, A, Ah, hs, ls, nus, Ah_f=af)
    NG = orth_nullspace_NG(H, data_mask, G)
    r_full = y - H @ xp
    rG = NG.conj().T @ r_full
    cost = float(np.sum(np.abs(rG) ** 2))

    Hd = H[:, data_mask]
    if float(np.linalg.norm(Hd)) < 1e-12:
        xd_hat = np.zeros(int(data_mask.sum()), dtype=complex)
    else:
        xd_hat, _, _, _ = np.linalg.lstsq(Hd, r_full, rcond=1e-6)
    x_tot = xp.copy()
    x_tot[data_mask] = xd_hat
    P_null = NG.conj().T @ A
    s_f = np.fft.fft(Ah @ x_tot)
    J = np.zeros((G, 4 * P), dtype=complex)
    for p in range(P):
        hp = hs[p]
        lp = ls[p]
        nup = nus[p]
        dl_e = np.exp(-1j * 2.0 * np.pi * lp * m_freq / N)
        s_del = np.fft.ifft(dl_e * s_f)
        ds_del = np.fft.ifft((-1j * 2.0 * np.pi * m_freq / N) * dl_e * s_f)
        dop = np.exp(-1j * 2.0 * np.pi * nup * n / N)
        vh = -P_null @ (dop * s_del)
        J[:, 4 * p] = vh
        J[:, 4 * p + 1] = 1j * vh
        J[:, 4 * p + 2] = -hp * (P_null @ (dop * ds_del))
        J[:, 4 * p + 3] = -hp * (P_null @ ((-1j * 2.0 * np.pi * n / N) * dop * s_del))
    grad = 2.0 * np.real(J.conj().T @ rG)
    return cost, grad, J, rG, H, NG


def refine_orth_null_gn(y, xp, data_mask, G, A, Ah, h0, l0, nu0, n_it=6, Ah_f=None):
    """Exact-gradient Gauss-Newton on Grassmannian Guard-Nullspace objective J_null."""
    _CALL_COUNTERS["refine_orth_null_gn"] += 1
    N = len(y)
    P = len(h0)
    af = np.fft.fft(Ah, axis=0) if Ah_f is None else Ah_f
    par = np.zeros(4 * P, dtype=float)
    for p in range(P):
        par[4 * p] = float(np.real(h0[p]))
        par[4 * p + 1] = float(np.imag(h0[p]))
        par[4 * p + 2] = float(l0[p])
        par[4 * p + 3] = float(nu0[p])

    def eval_cost_only(pv):
        H = build_H_eff(N, A, Ah,
                        [pv[4 * p] + 1j * pv[4 * p + 1] for p in range(P)],
                        [pv[4 * p + 2] for p in range(P)],
                        [pv[4 * p + 3] for p in range(P)], Ah_f=af)
        NG = orth_nullspace_NG(H, data_mask, G)
        rG = NG.conj().T @ (y - H @ xp)
        return float(np.sum(np.abs(rG) ** 2))

    c0 = eval_cost_only(par)
    for _ in range(n_it):
        c0, grad, J, rG, _, _ = grassmann_null_cost_and_grad(par, y, xp, data_mask, G, A, Ah, Ah_f=af)
        H_gn = np.real(J.conj().T @ J) + 1e-4 * np.eye(4 * P)
        try:
            step = -np.linalg.solve(H_gn, 0.5 * grad)
        except np.linalg.LinAlgError:
            step = -np.linalg.lstsq(H_gn, 0.5 * grad, rcond=1e-6)[0]
        if not np.all(np.isfinite(step)):
            break
        for p in range(P):
            step[4 * p + 2] = np.clip(step[4 * p + 2], -0.35, 0.35)
            step[4 * p + 3] = np.clip(step[4 * p + 3], -0.35, 0.35)
            h_step = np.hypot(step[4 * p], step[4 * p + 1])
            if h_step > 1.5:
                step[4 * p] *= 1.5 / h_step
                step[4 * p + 1] *= 1.5 / h_step
        alpha = 1.0
        accepted = False
        for _ in range(6):
            pt = par + alpha * step
            c1 = eval_cost_only(pt)
            if np.isfinite(c1) and c1 < c0:
                par = pt
                c0 = c1
                accepted = True
                break
            alpha *= 0.5
        if not accepted:
            break
    hs_o = np.array([par[4 * p] + 1j * par[4 * p + 1] for p in range(P)], dtype=complex)
    ls_o = np.array([par[4 * p + 2] for p in range(P)], dtype=float)
    nus_o = np.array([par[4 * p + 3] for p in range(P)], dtype=float)
    return hs_o, ls_o, nus_o, c0


def orth_null_score_map(y, xp, data_mask, G, H_c, A, Ah, l_grid, nu_grid, use_self_ref=True):
    """Guard-Nullspace GLRT score map."""
    N = len(y)
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    NG = orth_nullspace_NG(H_c, data_mask, G)
    r_full = y - H_c @ xp
    r_null = NG.conj().T @ r_full
    if use_self_ref and float(np.linalg.norm(H_c[:, data_mask])) >= 1e-12:
        xd_hat, _, _, _ = np.linalg.lstsq(H_c[:, data_mask], r_full, rcond=1e-6)
        x_ref = xp.copy()
        x_ref[data_mask] = xd_hat
    else:
        x_ref = xp
    P_null = NG.conj().T @ A
    s_f = np.fft.fft(Ah @ x_ref)
    E_nu = np.exp(-1j * 2.0 * np.pi * np.outer(n, nu_grid) / N)
    sc = np.zeros((len(l_grid), len(nu_grid)))
    h_est = np.zeros((len(l_grid), len(nu_grid)), dtype=complex)
    for il, lv in enumerate(l_grid):
        s_del = np.fft.ifft(np.exp(-1j * 2.0 * np.pi * lv * m_freq / N) * s_f)
        A_n = (P_null * s_del[None, :]) @ E_nu
        inn = r_null.conj() @ A_n
        den = np.sum(np.abs(A_n) ** 2, axis=0) + 1e-12
        sc[il, :] = (np.abs(inn) ** 2) / den
        h_est[il, :] = np.conj(inn) / den
    return sc, h_est


# ==============================================================================
# Constellations & Rate-1/2 / Punctured Rate-2/3 (7,5)_8 Convolutional Code
# ==============================================================================
def _gray_pam(M_pam):
    levels = np.arange(-(M_pam - 1), M_pam, 2, dtype=float)
    levels /= np.sqrt(np.mean(levels ** 2))
    pts = np.zeros(M_pam, dtype=float)
    for i in range(M_pam):
        pts[i ^ (i >> 1)] = levels[i]
    return pts


def make_qam(M_qam):
    M_pam = int(round(math.sqrt(M_qam)))
    k_pam = int(round(math.log2(M_pam)))
    nb = 2 * k_pam
    pam = _gray_pam(M_pam) / np.sqrt(2.0)
    bits = np.array([[(i >> (nb - 1 - b)) & 1 for b in range(nb)] for i in range(M_qam)], dtype=int)
    idx_i = np.zeros(M_qam, dtype=int)
    idx_q = np.zeros(M_qam, dtype=int)
    for b in range(k_pam):
        idx_i = (idx_i << 1) | bits[:, b]
        idx_q = (idx_q << 1) | bits[:, k_pam + b]
    return pam[idx_i] + 1j * pam[idx_q], bits


QPSK_P, QPSK_B = make_qam(4)
QAM16_P, QAM16_B = make_qam(16)
QAM64_P, QAM64_B = make_qam(64)

_NEXT_S = np.zeros((4, 2), dtype=int)
_OUT_B = np.zeros((4, 2, 2), dtype=int)
for _s in range(4):
    _b1, _b2 = (_s >> 1) & 1, _s & 1
    for _u in range(2):
        _NEXT_S[_s, _u] = (_u << 1) | _b1
        _OUT_B[_s, _u, 0] = _u ^ _b1 ^ _b2
        _OUT_B[_s, _u, 1] = _u ^ _b2


def conv_encode(bits, rate23=False):
    full = np.concatenate([bits, np.zeros(2, dtype=int)])
    raw = np.zeros(2 * len(full), dtype=int)
    s = 0
    for i, u in enumerate(full):
        raw[2 * i] = _OUT_B[s, u, 0]
        raw[2 * i + 1] = _OUT_B[s, u, 1]
        s = _NEXT_S[s, u]
    if not rate23:
        return raw
    mask = np.ones(len(raw), dtype=bool)
    mask[3::4] = False
    return raw[mask]


def viterbi_decode_llr(llrs_rx, n_info, rate23=False):
    n_stages = n_info + 2
    if rate23:
        llrs = np.zeros(2 * n_stages, dtype=float)
        mask = np.ones(2 * n_stages, dtype=bool)
        mask[3::4] = False
        llrs[mask] = llrs_rx
    else:
        llrs = llrs_rx
    pm = np.full(4, -1e18)
    pm[0] = 0.0
    ps = np.zeros((n_stages, 4), dtype=int)
    pu = np.zeros((n_stages, 4), dtype=int)
    for t in range(n_stages):
        l0, l1 = llrs[2 * t], llrs[2 * t + 1]
        npm = np.full(4, -1e18)
        u_vals = (0,) if t >= n_info else (0, 1)
        for s in range(4):
            if pm[s] < -1e17:
                continue
            for u in u_vals:
                ns = _NEXT_S[s, u]
                cand = pm[s] + (1 - 2 * _OUT_B[s, u, 0]) * l0 + (1 - 2 * _OUT_B[s, u, 1]) * l1
                if cand > npm[ns]:
                    npm[ns] = cand
                    ps[t, ns] = s
                    pu[t, ns] = u
        pm = npm
    s = 0
    dec = np.zeros(n_stages, dtype=int)
    for t in range(n_stages - 1, -1, -1):
        dec[t] = pu[t, s]
        s = ps[t, s]
    return dec[:n_info]


def map_qam_bits(cbits, pts, nb):
    idx = np.zeros(len(cbits) // nb, dtype=int)
    for b in range(nb):
        idx = (idx << 1) | cbits[b::nb]
    return pts[idx]


def demap_llr(z, var, pts, bits):
    d2 = (np.abs(z[:, None] - pts[None, :]) ** 2) / var[:, None]
    nb = bits.shape[1]
    llrs = np.zeros(len(z) * nb, dtype=float)
    for b in range(nb):
        llrs[b::nb] = np.min(d2[:, bits[:, b] == 1], axis=1) - np.min(d2[:, bits[:, b] == 0], axis=1)
    return llrs


# ==============================================================================
# Statistical Utilities (Wilson 95% Binomial CI & Paired Diff 95% CI)
# ==============================================================================
def wilson_ci(k, n, z=1.959963984540054):
    if n <= 0:
        return [0.0, 1.0]
    p = k / n
    den = 1.0 + z * z / n
    ctr = (p + z * z / (2.0 * n)) / den
    rad = (z / den) * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return [float(max(0.0, ctr - rad)), float(min(1.0, ctr + rad))]


def paired_diff_ci(a_bool, b_bool, z=1.959963984540054):
    d = np.asarray(a_bool, dtype=float) - np.asarray(b_bool, dtype=float)
    n = len(d)
    mean_d = float(np.mean(d))
    if n <= 1:
        return mean_d, [mean_d, mean_d]
    se = float(np.std(d, ddof=1)) / math.sqrt(n)
    return mean_d, [float(mean_d - z * se), float(mean_d + z * se)]


# ==============================================================================
# Ma et al. (arXiv:2606.25572) Exact Joint CRB Eq.(11) & Case-1 MCRB Eq.(16)
# ==============================================================================
def ma_exact_crb_and_mcrb1(N, A, Ah, xp, data_mask, sig_d2, sig_n2, hs, ls, nus, Ah_f=None):
    P = len(hs)
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    af = np.fft.fft(Ah, axis=0) if Ah_f is None else Ah_f
    H = np.zeros((N, N), dtype=complex)
    dH_list = []
    for p in range(P):
        hp, lp, nup = hs[p], ls[p], nus[p]
        dl_e = np.exp(-1j * 2.0 * np.pi * lp * m_freq / N)
        Pi = np.fft.ifft(dl_e[:, None] * af, axis=0)
        dPi = np.fft.ifft(((-1j * 2.0 * np.pi * m_freq / N) * dl_e)[:, None] * af, axis=0)
        dop = np.exp(-1j * 2.0 * np.pi * nup * n / N)
        Bp = A @ (dop[:, None] * Pi)
        dBl = A @ (dop[:, None] * dPi)
        dBnu = A @ (((-1j * 2.0 * np.pi * n / N) * dop)[:, None] * Pi)
        H += hp * Bp
        dH_list.extend([Bp, 1j * Bp, hp * dBl, hp * dBnu])

    Hd = H[:, data_mask]
    C = sig_d2 * (Hd @ Hd.conj().T) + sig_n2 * np.eye(N)
    C_inv = np.linalg.inv(C)
    dmu = [dH @ xp for dH in dH_list]
    dC = []
    for dH in dH_list:
        dHd = dH[:, data_mask]
        dC.append(sig_d2 * (dHd @ Hd.conj().T + Hd @ dHd.conj().T))
    M = 4 * P
    FIM = np.zeros((M, M), dtype=float)
    Cinv_dC = [C_inv @ M_k for M_k in dC]
    for i in range(M):
        for j in range(i, M):
            t1 = 2.0 * float(np.real(dmu[i].conj() @ (C_inv @ dmu[j])))
            t2 = float(np.real(np.trace(Cinv_dC[i] @ Cinv_dC[j])))
            FIM[i, j] = FIM[j, i] = t1 + t2
    cov_crb = np.linalg.pinv(FIM)

    A_mat = np.zeros((M, M), dtype=float)
    B_mat = np.zeros((M, M), dtype=float)
    for i in range(M):
        for j in range(i, M):
            a_ij = 2.0 * float(np.real(np.vdot(dmu[i], dmu[j])))
            b_ij = 2.0 * float(np.real(dmu[i].conj() @ (C @ dmu[j])))
            A_mat[i, j] = A_mat[j, i] = a_ij
            B_mat[i, j] = B_mat[j, i] = b_ij
    A_pinv = np.linalg.pinv(A_mat)
    cov_mcrb = A_pinv @ B_mat @ A_pinv

    base = 4 * (P - 1)
    ht = hs[-1]
    gh = np.array([np.real(ht), np.imag(ht)]) / max(abs(ht), 1e-12)
    var_h_crb = float(gh @ cov_crb[base:base + 2, base:base + 2] @ gh)
    var_h_mcrb = float(gh @ cov_mcrb[base:base + 2, base:base + 2] @ gh)
    return {
        "crb_h_std": math.sqrt(max(var_h_crb, 0.0)),
        "crb_l_std": math.sqrt(max(float(cov_crb[base + 2, base + 2]), 0.0)),
        "crb_nu_std": math.sqrt(max(float(cov_crb[base + 3, base + 3]), 0.0)),
        "mcrb1_h_std": math.sqrt(max(var_h_mcrb, 0.0)),
        "mcrb1_l_std": math.sqrt(max(float(cov_mcrb[base + 2, base + 2]), 0.0)),
        "mcrb1_nu_std": math.sqrt(max(float(cov_mcrb[base + 3, base + 3]), 0.0)),
    }


# ==============================================================================
# Y. Luo TCOM'26 (arXiv:2607.18881) Faithful D-GESBL (Exact Sec. IV Cross-Cov)
# ==============================================================================
def run_luo_gesbl(Y_in, xp, data_mask, A, Ah, l_init_grid, nu_init_grid,
                  constellation=None, sig_d2_nom=1.0, n_da=3, n_em=12, n_top_evol=4,
                  b_prior=1e-4, sp_mode=False, Ah_f=None):
    """Faithful Y. Luo TCOM'26 D-GESBL with exact Sec. IV posterior cross-covariance grid evolution
    (-Nr * sum_{j!=m} Sigma_{jm} Phi_j) and optional symbol decision feedback.
    Takes ONLY Y_in and public config — ZERO true sigma2, ZERO true x_d!
    """
    Y = Y_in[:, None] if Y_in.ndim == 1 else Y_in
    N, Nr = Y.shape
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    M = len(l_init_grid)
    xd_hat = np.zeros(N, dtype=complex)
    n_outer = n_da if constellation is not None else 1
    y_pow = float(np.mean(np.abs(Y) ** 2))
    mu_out = np.zeros((M, Nr), dtype=complex)
    lk_out = l_init_grid.copy()
    nk_out = nu_init_grid.copy()
    delta_out = np.ones(M)
    beta_est = 1.0 / max(y_pow, 1e-6)

    for t_da in range(n_outer):
        x_cur = xp + xd_hat
        lk = l_init_grid.copy()
        nk = nu_init_grid.copy()
        delta = np.ones(M, dtype=float)
        beta = 1.0 / max(y_pow, 1e-6) if t_da == 0 else beta_est
        sf = np.fft.fft(Ah @ x_cur)
        dl_mat = np.exp(-1j * 2.0 * np.pi * np.outer(m_freq, lk) / N)
        s_del_mat = np.fft.ifft(dl_mat * sf[:, None], axis=0)
        dop_mat = np.exp(-1j * 2.0 * np.pi * np.outer(n, nk) / N)
        Phi = A @ (dop_mat * s_del_mat)
        for it in range(n_em):
            PhiH_Phi = Phi.conj().T @ Phi
            A_inv_mat = beta * PhiH_Phi + np.diag(1.0 / np.maximum(delta, 1e-14))
            Sigma = np.linalg.inv(A_inv_mat)
            Mu = beta * (Sigma @ (Phi.conj().T @ Y))
            pow_m = np.sum(np.abs(Mu) ** 2, axis=1) + Nr * np.real(np.diag(Sigma))
            if b_prior > 0.0:
                delta = np.maximum((-Nr + np.sqrt(Nr * Nr + 4.0 * b_prior * pow_m)) / (2.0 * b_prior), 1e-14)
            else:
                delta = np.maximum(pow_m / Nr, 1e-14)
            res = Y - Phi @ Mu
            res_f = float(np.sum(np.abs(res) ** 2)) + Nr * float(np.real(np.trace(PhiH_Phi @ Sigma)))
            beta = min((Nr * N + 1e-12) / max(res_f + 1e-14, 1e-18), 1e14)
            if it < n_em - 1 and n_top_evol > 0:
                top_idx = np.argsort(delta)[-n_top_evol:]
                for idx in top_idx:
                    dl_e = np.exp(-1j * 2.0 * np.pi * lk[idx] * m_freq / N)
                    s_del = np.fft.ifft(dl_e * sf)
                    ds_del = np.fft.ifft((-1j * 2.0 * np.pi * m_freq / N) * dl_e * sf)
                    dop = np.exp(-1j * 2.0 * np.pi * nk[idx] * n / N)
                    b_nu = A @ ((-1j * 2.0 * np.pi * n / N) * dop * s_del)
                    b_l = A @ (dop * ds_del)
                    r_ex = res + np.outer(Phi[:, idx], Mu[idx, :])
                    w_m = float(np.sum(np.abs(Mu[idx, :]) ** 2)) + Nr * float(np.real(Sigma[idx, idx]))
                    # Exact -0.5 * grad Q(l_m, nu_m) including posterior cross-covariance & coupled 2x2 Gauss-Newton:
                    # rhs_net = res @ conj(Mu[idx,:]) - Nr * (Phi @ Sigma[:, idx]) == rhs - w_m * Phi[:, idx]
                    rhs_net = res @ np.conj(Mu[idx, :]) - Nr * (Phi @ Sigma[:, idx])
                    J2 = np.column_stack([b_l, b_nu])
                    g2 = np.real(J2.conj().T @ rhs_net)
                    H2 = np.real(J2.conj().T @ J2) * w_m + 1e-10 * np.eye(2)
                    try:
                        step2 = np.clip(np.linalg.solve(H2, g2), -0.25, 0.25)
                    except np.linalg.LinAlgError:
                        step2 = np.zeros(2)
                    lk[idx] += float(step2[0])
                    nk[idx] += float(step2[1])
                    dl_new = np.exp(-1j * 2.0 * np.pi * lk[idx] * m_freq / N)
                    Phi[:, idx] = A @ (np.exp(-1j * 2.0 * np.pi * nk[idx] * n / N) * np.fft.ifft(dl_new * sf))
                    res = r_ex - np.outer(Phi[:, idx], Mu[idx, :])
        mu_out, lk_out, nk_out, delta_out, beta_est = Mu, lk, nk, delta, beta
        if constellation is not None and t_da < n_outer - 1:
            act = np.where(delta > 0.05 * float(np.max(delta)))[0]
            if len(act) == 0:
                act = np.argsort(delta)[-max(n_top_evol, 3):]
            H_hats = [build_H_eff(N, A, Ah, Mu[act, nr], lk[act], nk[act], Ah_f=Ah_f) for nr in range(Nr)]
            if sp_mode:
                H_stk = np.vstack(H_hats)
                yd_stk = np.concatenate([Y[:, nr] - H_hats[nr] @ xp for nr in range(Nr)])
                reg = max(1.0 / max(beta_est * sig_d2_nom, 1e-3), 1e-10)
                xd_lin = np.linalg.solve(H_stk.conj().T @ H_stk + reg * np.eye(N), H_stk.conj().T @ yd_stk)
                scaled_c = math.sqrt(sig_d2_nom) * constellation
                xd_hat = scaled_c[np.argmin(np.abs(xd_lin[:, None] - scaled_c[None, :]), axis=1)]
            else:
                Hd_stk = np.vstack([H_hats[nr][:, data_mask] for nr in range(Nr)])
                yd_stk = np.concatenate([Y[:, nr] - H_hats[nr] @ xp for nr in range(Nr)])
                reg = min(max(1.0 / max(beta_est * sig_d2_nom, 1e-3), 1e-3), 0.5)
                xd_lin = np.linalg.solve(Hd_stk.conj().T @ Hd_stk + reg * np.eye(int(data_mask.sum())), Hd_stk.conj().T @ yd_stk)
                scaled_c = math.sqrt(sig_d2_nom) * constellation
                xd_hat = np.zeros(N, dtype=complex)
                xd_hat[data_mask] = scaled_c[np.argmin(np.abs(xd_lin[:, None] - scaled_c[None, :]), axis=1)]
    return mu_out, lk_out, nk_out, delta_out, xd_hat, beta_est


# ==============================================================================
# Strict Blind Receiver Arms: ALL take ONLY (y, rx_cfg)
# ==============================================================================
def _apply_clut_mask_and_norm(sc, l_grid, nu_grid, ls_c, nus_c, dl_m, dnu_m):
    scm = sc.copy() / (float(np.median(sc)) + 1e-12)
    for lp0, np0 in zip(ls_c, nus_c):
        scm[(np.abs(l_grid[:, None] - lp0) < dl_m) & (np.abs(nu_grid[None, :] - np0) < dnu_m)] = 0.0
    return scm


def _blind_nomp_clutter(y, cfg, win_idx=None, n_cyc=2, n_newt=3):
    """Independent from-scratch blind clutter peeling via isotropic NOMP (formal stopping rule)."""
    N, xp, A, Ah = cfg["N"], cfg["xp"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    y_map = np.zeros(N, dtype=complex) if win_idx is not None else y
    if win_idx is not None:
        y_map[win_idx] = y[win_idx]
    sc0 = isotropic_mf_map(y_map, xp, A, Ah, l_grid, nu_grid)
    r0 = float(sc0.max() / (float(np.median(sc0)) + 1e-12))
    if r0 <= cfg["tau_p1"]:
        return np.array([], dtype=complex), np.array([], dtype=float), np.array([], dtype=float), y_map.copy()
    i1, j1 = np.unravel_index(np.argmax(sc0), sc0.shape)
    hm, lm, nm = nomp_joint_refinement(y, xp, A, Ah, [0.5 + 0j], [l_grid[i1]], [nu_grid[j1]],
                                       n_cyc=n_cyc, n_newt=n_newt, win_idx=win_idx)
    r_full = y - build_H_eff(N, A, Ah, hm, lm, nm, Ah_f=Ah_f) @ xp
    r_c = np.zeros(N, dtype=complex) if win_idx is not None else r_full
    if win_idx is not None:
        r_c[win_idx] = r_full[win_idx]
    e_cur = float(np.sum(np.abs(r_c) ** 2))
    for _ in range(cfg["max_clut"] - 1):
        sc = isotropic_mf_map(r_c, xp, A, Ah, l_grid, nu_grid)
        for lq, nq in zip(lm, nm):
            sc[(np.abs(l_grid[:, None] - lq) < 1.0) & (np.abs(nu_grid[None, :] - nq) < 0.8)] = 0.0
        ic, jc = np.unravel_index(np.argmax(sc), sc.shape)
        ht, lt, nt = nomp_joint_refinement(
            y, xp, A, Ah, list(hm) + [0.1 + 0j], list(lm) + [l_grid[ic]], list(nm) + [nu_grid[jc]],
            n_cyc=n_cyc, n_newt=n_newt, win_idx=win_idx
        )
        rt_full = y - build_H_eff(N, A, Ah, ht, lt, nt, Ah_f=Ah_f) @ xp
        r_try = np.zeros(N, dtype=complex) if win_idx is not None else rt_full
        if win_idx is not None:
            r_try[win_idx] = rt_full[win_idx]
        e_try = float(np.sum(np.abs(r_try) ** 2))
        if np.min(np.abs(ht)) > cfg["stop_ratio_h"] * np.max(np.abs(ht)) and (e_cur - e_try) > 0.03 * e_cur:
            hm, lm, nm, r_c, e_cur = ht, lt, nt, r_try, e_try
        else:
            break
    return hm, lm, nm, r_c


from functools import lru_cache


def _nomp_atom_bank(xp, Ah, l_vals, nu_vals):
    """Normalized time-domain atom rows matching `isotropic_mf_map` element-for-element for public pilot `xp`.
    For any time-domain vector `r_t = Ah @ y`, `|D @ r_t.conj()|^2 == |r_t @ D.conj().T|^2 == isotropic_mf_map(y, ...).ravel()`.
    """
    N = len(xp)
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    s_pf = np.fft.fft(Ah @ xp)
    E_nu = np.exp(-1j * 2.0 * np.pi * np.outer(n, nu_vals) / N)  # (N, n_nu), exact sign match to isotropic_mf_map
    rows = []
    for lv in l_vals:
        s_del = np.fft.ifft(np.exp(-1j * 2.0 * np.pi * lv * m_freq / N) * s_pf)
        norm = math.sqrt(float(np.sum(np.abs(s_del) ** 2)) + 1e-12)
        # isotropic_mf_map computes |(r_t.conj() * s_del) @ E_nu|^2 / norm^2 = |r_t^H (s_del * E_nu / norm)|^2
        atoms_l = (s_del[:, None] * E_nu) / norm  # (N, n_nu)
        rows.append(atoms_l.T)
    return np.vstack(rows)  # (n_l * n_nu, N)


@lru_cache(maxsize=16)
def _calibrate_nomp_cfar_mult_cached(xp_bytes, Ah_bytes, l_bytes, nu_bytes, N, pfa_cfar, n_trials, cal_seed):
    xp = np.frombuffer(xp_bytes, dtype=np.complex128).copy()
    Ah = np.frombuffer(Ah_bytes, dtype=np.complex128).reshape(N, N).copy()
    l_grid = np.frombuffer(l_bytes, dtype=np.float64).copy()
    nu_grid = np.frombuffer(nu_bytes, dtype=np.float64).copy()
    l_orth = np.arange(math.ceil(float(l_grid[0])), math.floor(float(l_grid[-1])) + 1.0, 1.0)
    nu_orth = np.arange(math.ceil(float(nu_grid[0])), math.floor(float(nu_grid[-1])) + 1.0, 1.0)
    D_dense = _nomp_atom_bank(xp, Ah, l_grid, nu_grid)
    D_orth = _nomp_atom_bank(xp, Ah, l_orth, nu_orth)
    rng = np.random.default_rng(cal_seed)
    ratios = np.empty(n_trials, dtype=float)
    batch = 500
    for start in range(0, n_trials, batch):
        bs = min(batch, n_trials - start)
        W = (rng.standard_normal((bs, N)) + 1j * rng.standard_normal((bs, N))) / math.sqrt(2.0)
        p_dense = np.abs(W @ D_dense.conj().T) ** 2
        p_orth = np.abs(W @ D_orth.conj().T) ** 2
        sig2_orth = np.median(p_orth, axis=1) / math.log(2.0)
        ratios[start:start + bs] = p_dense.max(axis=1) / np.maximum(sig2_orth, 1e-30)
    thr, _, _ = exact_order_stat_threshold(ratios, pfa_cfar)
    return thr


def calibrate_nomp_cfar_mult(xp, Ah, l_grid, nu_grid, pfa_cfar=1e-3, n_trials=NOMP_CFAR_NCAL, cal_seed=918273645):
    """Exact order-statistic OS-CFAR multiplier X_(b) (b = n_cal + 1 - a, a = round(p * (n_cal + 1)))
    calibrated on public (xp, Ah, l_grid, nu_grid) under white complex Gaussian noise w ~ CN(0, I_N),
    matching the exact dense-grid peak divided by integer-grid median noise estimate (zero simulator
    truth; value-keyed cache by immutable array bytes, zero id()-reuse hazard).
    """
    xp_c = np.ascontiguousarray(xp, dtype=np.complex128)
    Ah_c = np.ascontiguousarray(Ah, dtype=np.complex128)
    lg_c = np.ascontiguousarray(l_grid, dtype=np.float64)
    ng_c = np.ascontiguousarray(nu_grid, dtype=np.float64)
    return _calibrate_nomp_cfar_mult_cached(
        xp_c.tobytes(), Ah_c.tobytes(), lg_c.tobytes(), ng_c.tobytes(),
        len(xp_c), float(pfa_cfar), int(n_trials), int(cal_seed),
    )


def _nomp_cfar_detect(y, cfg, n_cyc=40, n_newt=8, pfa_cfar=1e-3):
    """NOMP (Mamandipoor TSP'16) blind OS-CFAR stopping rule on AFDM:
    noise variance sigma_hat^2 is estimated via median on the integer-(l, nu) grid, and the
    stopping multiplier `cfar_mult` is calibrated under CN(0, I) for the exact public pilot `xp`,
    dense search grid `(l_grid, nu_grid)`, and median noise estimator so the white-noise
    first-step false-alarm rate matches `pfa_cfar`.
    """
    N, xp, A, Ah = cfg["N"], cfg["xp"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    l_orth = np.arange(math.ceil(float(l_grid[0])), math.floor(float(l_grid[-1])) + 1.0, 1.0)
    nu_orth = np.arange(math.ceil(float(nu_grid[0])), math.floor(float(nu_grid[-1])) + 1.0, 1.0)
    cfar_mult = calibrate_nomp_cfar_mult(xp, Ah, l_grid, nu_grid, pfa_cfar=pfa_cfar)
    r_c = y.copy()
    hm, lm, nm = [], [], []
    for _ in range(cfg["max_clut"]):
        sc = isotropic_mf_map(r_c, xp, A, Ah, l_grid, nu_grid)
        sc_orth = isotropic_mf_map(r_c, xp, A, Ah, l_orth, nu_orth)
        for lq, nq in zip(lm, nm):
            sc[(np.abs(l_grid[:, None] - lq) < 1.0) & (np.abs(nu_grid[None, :] - nq) < 0.8)] = 0.0
        sig2_orth = float(np.median(sc_orth) / math.log(2.0))
        pk = float(sc.max())
        if pk <= max(cfar_mult * sig2_orth, 1e-22):
            break
        ic, jc = np.unravel_index(np.argmax(sc), sc.shape)
        hm.append(0.1 + 0j); lm.append(float(l_grid[ic])); nm.append(float(nu_grid[jc]))
        hm, lm, nm = [list(a) for a in nomp_joint_refinement(y, xp, A, Ah, hm, lm, nm, n_cyc=n_cyc, n_newt=n_newt)]
        r_c = y - build_H_eff(N, A, Ah, hm, lm, nm, Ah_f=Ah_f) @ xp
    return np.array(hm, dtype=complex), np.array(lm, dtype=float), np.array(nm, dtype=float), r_c


def rx_ma_seq_mf(y, cfg, win_idx=None, n_newt=3):
    """Published Baseline 1: Ma 2606.25572 / Bemani WCL'24 sequential isotropic MF peeling."""
    N, xp, A, Ah = cfg["N"], cfg["xp"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    y_map = np.zeros(N, dtype=complex) if win_idx is not None else y
    if win_idx is not None:
        y_map[win_idx] = y[win_idx]
    sc0 = isotropic_mf_map(y_map, xp, A, Ah, l_grid, nu_grid)
    r0 = float(sc0.max() / (float(np.median(sc0)) + 1e-12))
    r_full = y.copy()
    r_c = y_map.copy()
    hm, lm, nm = [], [], []
    if r0 > cfg["tau_p1"]:
        for p in range(cfg["max_clut"]):
            sc = sc0 if p == 0 else isotropic_mf_map(r_c, xp, A, Ah, l_grid, nu_grid)
            for lq, nq in zip(lm, nm):
                sc[(np.abs(l_grid[:, None] - lq) < 1.0) & (np.abs(nu_grid[None, :] - nq) < 0.8)] = 0.0
            ic, jc = np.unravel_index(np.argmax(sc), sc.shape)
            hp, lp, np_ = nomp_joint_refinement(r_full, xp, A, Ah, [0.5 + 0j], [l_grid[ic]], [nu_grid[jc]],
                                                n_cyc=1, n_newt=n_newt, win_idx=win_idx)
            if p > 0 and abs(hp[0]) <= cfg["stop_ratio_h"] * max(abs(v) for v in hm):
                break
            hm.append(hp[0]); lm.append(lp[0]); nm.append(np_[0])
            r_full = r_full - build_H_eff(N, A, Ah, [hp[0]], [lp[0]], [np_[0]], Ah_f=Ah_f) @ xp
            if win_idx is not None:
                r_c = np.zeros(N, dtype=complex); r_c[win_idx] = r_full[win_idx]
            else:
                r_c = r_full
    sc_fin = _apply_clut_mask_and_norm(isotropic_mf_map(r_c, xp, A, Ah, l_grid, nu_grid),
                                       l_grid, nu_grid, lm, nm, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    ht, lt, nt = nomp_joint_refinement(r_full, xp, A, Ah, [0.1 + 0j], [l_grid[ic]], [nu_grid[jc]],
                                       n_cyc=1, n_newt=n_newt, win_idx=win_idx)
    return {"stat": float(sc_fin[ic, jc]), "l_est": float(lt[0]), "nu_est": float(nt[0]),
            "h_est": complex(ht[0]), "pc_hat": len(hm), "clut": (hm, lm, nm)}


def rx_nomp_dirport(y, cfg):
    """Required Mother-Method Direct Port: NOMP (F_N -> A) using textbook CFAR stopping rule (_nomp_cfar_detect)."""
    N, xp, A, Ah = cfg["N"], cfg["xp"], cfg["A"], cfg["Ah"]
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    hm, lm, nm, r_c = _nomp_cfar_detect(y, cfg)
    sc_fin = _apply_clut_mask_and_norm(isotropic_mf_map(r_c, xp, A, Ah, l_grid, nu_grid),
                                       l_grid, nu_grid, lm, nm, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    if len(hm) > 0:
        ht, lt, nt = nomp_joint_refinement(y, xp, A, Ah, list(hm) + [0.1 + 0j], list(lm) + [l_grid[ic]], list(nm) + [nu_grid[jc]], n_cyc=40, n_newt=8)
        l_e, nu_e, h_e = float(lt[-1]), float(nt[-1]), complex(ht[-1])
    else:
        ht, lt, nt = nomp_joint_refinement(y, xp, A, Ah, [0.1 + 0j], [l_grid[ic]], [nu_grid[jc]], n_cyc=40, n_newt=8)
        l_e, nu_e, h_e = float(lt[0]), float(nt[0]), complex(ht[0])
    return {"stat": float(sc_fin[ic, jc]), "l_est": l_e, "nu_est": nu_e, "h_est": h_e,
            "pc_hat": len(hm), "clut": (hm, lm, nm)}


def rx_luo_gesbl(y, cfg):
    """Published Baseline 2: Y. Luo TCOM'26 D-GESBL (or Pilot-GESBL when constellation is None)."""
    N, xp, data_mask, A, Ah = cfg["N"], cfg["xp"], cfg["data_mask"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    l_sbl = np.repeat(np.linspace(0.5, 9.5, 10), 5)
    nu_sbl = np.tile(np.linspace(-2.0, 2.0, 5), 10)
    const = cfg.get("constellation", None)
    Mu, lk, nk, delta, xd_hat, _ = run_luo_gesbl(
        y, xp, data_mask, A, Ah, l_sbl, nu_sbl, constellation=const,
        sig_d2_nom=cfg.get("sig_d2_nom", 1.0), n_da=3 if const is not None else 1, n_em=10, n_top_evol=4, Ah_f=Ah_f
    )
    x_eff = xp + xd_hat
    amps = np.abs(Mu[:, 0])
    ord_idx = np.argsort(amps)[::-1]
    hm, lm, nm = [], [], []
    if amps[ord_idx[0]] > 0.15:
        for idx in ord_idx:
            if len(hm) >= cfg["max_clut"]:
                break
            if len(hm) > 0 and amps[idx] <= cfg["stop_ratio_h"] * amps[ord_idx[0]]:
                break
            if any(abs(lk[idx] - lq) < 1.0 and abs(nk[idx] - nq) < 0.8 for lq, nq in zip(lm, nm)):
                continue
            hm.append(Mu[idx, 0]); lm.append(float(lk[idx])); nm.append(float(nk[idx]))
    r_c = y - build_H_eff(N, A, Ah, hm, lm, nm, Ah_f=Ah_f) @ x_eff if hm else y.copy()
    sc_fin = _apply_clut_mask_and_norm(isotropic_mf_map(r_c, x_eff, A, Ah, l_grid, nu_grid),
                                       l_grid, nu_grid, lm, nm, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    ht, lt, nt = nomp_joint_refinement(r_c, x_eff, A, Ah, [0.1 + 0j], [l_grid[ic]], [nu_grid[jc]], n_cyc=1, n_newt=3)
    return {"stat": float(sc_fin[ic, jc]), "l_est": float(lt[0]), "nu_est": float(nt[0]),
            "h_est": complex(ht[0]), "pc_hat": len(hm), "clut": (hm, lm, nm)}


def rx_b_only_nonullspace(y, cfg, use_ls_diag=False):
    """Independent-Init Ablation B-only (Self-referenced analog illuminator WITHOUT N_G, 0 N_G calls):
    - use_ls_diag=False: Primary B-only (from-scratch NOMP clutter + regularized Tikhonov LMMSE x_hat_d + isotropic MF).
    - use_ls_diag=True : Supplementary non-gating diagnostic B_only_NOMP_LS_Diag (from-scratch NOMP clutter + LS subtraction + isotropic MF).
    """
    N, xp, data_mask, A, Ah = cfg["N"], cfg["xp"], cfg["data_mask"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    hm, lm, nm, _ = _blind_nomp_clutter(y, cfg)
    if len(hm) == 0:
        x_hat = xp.copy()
        r_sub = y.copy()
    else:
        H_c = build_H_eff(N, A, Ah, hm, lm, nm, Ah_f=Ah_f)
        Hd = H_c[:, data_mask]
        r_full = y - H_c @ xp
        if use_ls_diag:
            xd_hat, _, _, _ = np.linalg.lstsq(Hd, r_full, rcond=1e-6)
        else:
            rho = max(0.15, float(np.mean(np.abs(y[cfg["guard_idx"]]) ** 2)) * 0.25)
            xd_hat = np.linalg.solve(Hd.conj().T @ Hd + rho * np.eye(Hd.shape[1]), Hd.conj().T @ r_full)
        x_hat = xp.copy()
        x_hat[data_mask] = xd_hat
        r_sub = y - H_c @ x_hat
    sc_fin = _apply_clut_mask_and_norm(isotropic_mf_map(r_sub, x_hat, A, Ah, l_grid, nu_grid),
                                       l_grid, nu_grid, lm, nm, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    ht, lt, nt = nomp_joint_refinement(r_sub, x_hat, A, Ah, [0.1 + 0j], [l_grid[ic]], [nu_grid[jc]], n_cyc=1, n_newt=3)
    return {"stat": float(sc_fin[ic, jc]), "l_est": float(lt[0]), "nu_est": float(nt[0]),
            "h_est": complex(ht[0]), "pc_hat": len(hm), "clut": (hm, lm, nm)}


def _blind_grassmann_clutter(y, cfg, use_self_ref_for_peel=True, n_it=5):
    """Frozen blind Grassmannian Guard-Nullspace clutter order & parameter estimator (Pc_hat in 0..max_clut)."""
    N, G, data_mask, xp, A, Ah = cfg["N"], cfg["G"], cfg["data_mask"], cfg["xp"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    sc0 = isotropic_mf_map(y, xp, A, Ah, l_grid, nu_grid)
    r0 = float(sc0.max() / (float(np.median(sc0)) + 1e-12))
    if r0 <= cfg["tau_p1"]:
        return np.array([], dtype=complex), np.array([], dtype=float), np.array([], dtype=float), float(np.sum(np.abs(y[cfg["guard_idx"]]) ** 2))
    i1, j1 = np.unravel_index(np.argmax(sc0), sc0.shape)
    hp, lp, np_ = nomp_joint_refinement(y, xp, A, Ah, [0.5 + 0j], [l_grid[i1]], [nu_grid[j1]], n_cyc=1, n_newt=3)
    hp, lp, np_, J_cur = refine_orth_null_gn(y, xp, data_mask, G, A, Ah, hp, lp, np_, n_it=n_it, Ah_f=Ah_f)
    for _ in range(cfg["max_clut"] - 1):
        H_c = build_H_eff(N, A, Ah, hp, lp, np_, Ah_f=Ah_f)
        scm, hmm = orth_null_score_map(y, xp, data_mask, G, H_c, A, Ah, l_grid, nu_grid, use_self_ref=use_self_ref_for_peel)
        for lq, nq in zip(lp, np_):
            scm[(np.abs(l_grid[:, None] - lq) < 1.0) & (np.abs(nu_grid[None, :] - nq) < 0.8)] = 0.0
        ic, jc = np.unravel_index(np.argmax(scm), scm.shape)
        ht, lt, nt, J_try = refine_orth_null_gn(
            y, xp, data_mask, G, A, Ah,
            list(hp) + [hmm[ic, jc]], list(lp) + [l_grid[ic]], list(np_) + [nu_grid[jc]], n_it=n_it, Ah_f=Ah_f
        )
        if J_try < cfg["stop_ratio_J"] * J_cur and float(np.min(np.abs(ht))) > cfg["stop_ratio_h"] * float(np.max(np.abs(ht))):
            hp, lp, np_, J_cur = ht, lt, nt, J_try
        else:
            break
    return hp, lp, np_, J_cur


def rx_b_tikhonov_det_diag(y, cfg):
    """Supplementary non-gating diagnostic B_only_TikhonovDet_Diag: Grassmannian N_G clutter H_c +
    regularized Tikhonov LMMSE (rho=0.25) subtraction + isotropic MF + single-path Newton (no N_G target projection/GN).
    """
    N, xp, data_mask, A, Ah = cfg["N"], cfg["xp"], cfg["data_mask"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    hp, lp, np_, _ = _blind_grassmann_clutter(y, cfg, use_self_ref_for_peel=True)
    if len(hp) == 0:
        x_hat = xp.copy(); r_sub = y.copy()
    else:
        H_c = build_H_eff(N, A, Ah, hp, lp, np_, Ah_f=Ah_f)
        Hd = H_c[:, data_mask]; r_full = y - H_c @ xp
        rho = 0.25
        xd_hat = np.linalg.solve(Hd.conj().T @ Hd + rho * np.eye(Hd.shape[1]), Hd.conj().T @ r_full)
        x_hat = xp.copy(); x_hat[data_mask] = xd_hat
        r_sub = y - H_c @ x_hat
    sc_fin = _apply_clut_mask_and_norm(isotropic_mf_map(r_sub, x_hat, A, Ah, l_grid, nu_grid),
                                       l_grid, nu_grid, lp, np_, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    ht, lt, nt = nomp_joint_refinement(r_sub, x_hat, A, Ah, [0.1 + 0j], [l_grid[ic]], [nu_grid[jc]], n_cyc=1, n_newt=3)
    return {"stat": float(sc_fin[ic, jc]), "l_est": float(lt[0]), "nu_est": float(nt[0]),
            "h_est": complex(ht[0]), "pc_hat": len(hp), "clut": (hp, lp, np_)}


def rx_a_only_nullpilot(y, cfg):
    """Independent-Init Ablation A-only (Grassmannian N_G projection ONLY, pilot xp ONLY, NO x_hat_d illuminator).
    Includes symmetric post-detection joint GN refinement identical to Ours_GrassNull!
    """
    N, G, data_mask, xp, A, Ah = cfg["N"], cfg["G"], cfg["data_mask"], cfg["xp"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    hp, lp, np_, _ = _blind_grassmann_clutter(y, cfg, use_self_ref_for_peel=False)
    H_c = build_H_eff(N, A, Ah, hp, lp, np_, Ah_f=Ah_f) if len(hp) > 0 else np.zeros((N, N), dtype=complex)
    sc, hm = orth_null_score_map(y, xp, data_mask, G, H_c, A, Ah, l_grid, nu_grid, use_self_ref=False)
    sc_fin = _apply_clut_mask_and_norm(sc, l_grid, nu_grid, lp, np_, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    l_e, nu_e, h_e = float(l_grid[ic]), float(nu_grid[jc]), complex(hm[ic, jc])
    if len(hp) > 0:
        # Symmetric post-detection target refinement (identical budget to Ours)
        h3, l3, n3, _ = refine_orth_null_gn(
            y, xp, data_mask, G, A, Ah,
            list(hp) + [h_e], list(lp) + [l_e], list(np_) + [nu_e], n_it=5, Ah_f=Ah_f
        )
        h_e, l_e, nu_e = complex(h3[-1]), float(l3[-1]), float(n3[-1])
    return {"stat": float(sc_fin[ic, jc]), "l_est": l_e, "nu_est": nu_e, "h_est": h_e,
            "pc_hat": len(hp), "clut": (hp, lp, np_)}


def rx_ours_grassnull(y, cfg, do_joint_refine=True):
    """Proposed Full Method (A + B): Blind Grassmannian Guard-Nullspace peeling + self-referenced GLRT + exact-gradient GN."""
    N, G, data_mask, xp, A, Ah = cfg["N"], cfg["G"], cfg["data_mask"], cfg["xp"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    hp, lp, np_, _ = _blind_grassmann_clutter(y, cfg, use_self_ref_for_peel=True)
    H_c = build_H_eff(N, A, Ah, hp, lp, np_, Ah_f=Ah_f) if len(hp) > 0 else np.zeros((N, N), dtype=complex)
    sc, hm = orth_null_score_map(y, xp, data_mask, G, H_c, A, Ah, l_grid, nu_grid, use_self_ref=True)
    sc_fin = _apply_clut_mask_and_norm(sc, l_grid, nu_grid, lp, np_, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    l_e, nu_e, h_e = float(l_grid[ic]), float(nu_grid[jc]), complex(hm[ic, jc])
    if do_joint_refine and len(hp) > 0:
        h3, l3, n3, _ = refine_orth_null_gn(
            y, xp, data_mask, G, A, Ah,
            list(hp) + [h_e], list(lp) + [l_e], list(np_) + [nu_e], n_it=5, Ah_f=Ah_f
        )
        h_e, l_e, nu_e = complex(h3[-1]), float(l3[-1]), float(n3[-1])
    return {"stat": float(sc_fin[ic, jc]), "l_est": l_e, "nu_est": nu_e, "h_est": h_e,
            "pc_hat": len(hp), "clut": (hp, lp, np_)}


def rx_ours_multiant_nr(Y, cfg):
    """Multi-antenna (Nr > 1) blind Grassmannian Guard-Nullspace detector."""
    N, Nr = Y.shape
    G, data_mask, xp, A, Ah = cfg["G"], cfg["data_mask"], cfg["xp"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    n = np.arange(N)
    m_freq = np.fft.fftfreq(N) * N
    E_nu = np.exp(-1j * 2.0 * np.pi * np.outer(n, nu_grid) / N)

    def _fit_per_ant_H(lp_cur, np_cur):
        Bs = [build_B_path(N, A, Ah, lv, nv, Ah_f=Ah_f) for lv, nv in zip(lp_cur, np_cur)]
        B_xp = np.column_stack([B @ xp for B in Bs])
        H_list = []
        J_sum = 0.0
        h_mags = np.zeros((Nr, len(lp_cur)))
        for m in range(Nr):
            hm = np.linalg.lstsq(B_xp, Y[:, m], rcond=None)[0]
            H_m = sum(hm[p] * Bs[p] for p in range(len(lp_cur)))
            NG = orth_nullspace_NG(H_m, data_mask, G)
            r_full = Y[:, m] - H_m @ xp
            rG = NG.conj().T @ r_full
            c_m = float(np.sum(np.abs(rG) ** 2))
            for _ in range(3):
                xd_m, _, _, _ = np.linalg.lstsq(H_m[:, data_mask], r_full, rcond=1e-6)
                x_tot = xp.copy(); x_tot[data_mask] = xd_m
                Jh = np.column_stack([-(NG.conj().T @ (Bs[p] @ x_tot)) for p in range(len(lp_cur))])
                step = -np.linalg.solve(Jh.conj().T @ Jh + 1e-4 * np.eye(len(lp_cur)), Jh.conj().T @ rG)
                hm_try = hm + step
                H_try = sum(hm_try[p] * Bs[p] for p in range(len(lp_cur)))
                NG_t = orth_nullspace_NG(H_try, data_mask, G)
                r_f_t = Y[:, m] - H_try @ xp
                rG_t = NG_t.conj().T @ r_f_t
                c_t = float(np.sum(np.abs(rG_t) ** 2))
                if c_t < c_m:
                    hm, H_m, NG, r_full, rG, c_m = hm_try, H_try, NG_t, r_f_t, rG_t, c_t
                else:
                    break
            H_list.append(H_m); J_sum += c_m; h_mags[m, :] = np.abs(hm)
        return H_list, J_sum, np.mean(h_mags, axis=0)

    def _multiant_score_map(H_list):
        if len(H_list) == 0:
            H_list_u = [np.zeros((N, N), dtype=complex) for _ in range(Nr)]
            x_ref = xp.copy()
        else:
            H_list_u = H_list
            Hd_stk = np.vstack([H_list[m][:, data_mask] for m in range(Nr)])
            r_stk = np.concatenate([Y[:, m] - H_list[m] @ xp for m in range(Nr)])
            xd_hat, _, _, _ = np.linalg.lstsq(Hd_stk, r_stk, rcond=1e-6)
            x_ref = xp.copy(); x_ref[data_mask] = xd_hat
        s_f = np.fft.fft(Ah @ x_ref)
        sc_tot = np.zeros((len(l_grid), len(nu_grid)))
        for m in range(Nr):
            NG = orth_nullspace_NG(H_list_u[m], data_mask, G)
            r_null = NG.conj().T @ (Y[:, m] - H_list_u[m] @ xp)
            P_null = NG.conj().T @ A
            for il, lv in enumerate(l_grid):
                s_del = np.fft.ifft(np.exp(-1j * 2.0 * np.pi * lv * m_freq / N) * s_f)
                A_n = (P_null * s_del[None, :]) @ E_nu
                inn = r_null.conj() @ A_n
                den = np.sum(np.abs(A_n) ** 2, axis=0) + 1e-12
                sc_tot[il, :] += (np.abs(inn) ** 2) / den
        return sc_tot

    sc0_sum = sum(isotropic_mf_map(Y[:, m], xp, A, Ah, l_grid, nu_grid) for m in range(Nr))
    i1, j1 = np.unravel_index(np.argmax(sc0_sum), sc0_sum.shape)
    m_best = int(np.argmax([np.sum(np.abs(Y[:, m]) ** 2) for m in range(Nr)]))
    hp, lp, np_ = nomp_joint_refinement(Y[:, m_best], xp, A, Ah, [0.5 + 0j], [l_grid[i1]], [nu_grid[j1]], 1, 3)
    hp, lp, np_, _ = refine_orth_null_gn(Y[:, m_best], xp, data_mask, G, A, Ah, hp, lp, np_, 5, Ah_f=Ah_f)
    H_list, J_cur, _ = _fit_per_ant_H(lp, np_)

    for _ in range(cfg["max_clut"] - 1):
        sc_m = _multiant_score_map(H_list)
        for lq, nq in zip(lp, np_):
            sc_m[(np.abs(l_grid[:, None] - lq) < 1.0) & (np.abs(nu_grid[None, :] - nq) < 0.8)] = 0.0
        ic, jc = np.unravel_index(np.argmax(sc_m), sc_m.shape)
        ht, lt, nt, _ = refine_orth_null_gn(
            Y[:, m_best], xp, data_mask, G, A, Ah,
            list(hp) + [0.3 + 0j], list(lp) + [l_grid[ic]], list(np_) + [nu_grid[jc]], 5, Ah_f=Ah_f
        )
        H_try, J_try, h_avg_t = _fit_per_ant_H(lt, nt)
        if J_try < cfg["stop_ratio_J"] * J_cur and float(np.min(h_avg_t)) > cfg["stop_ratio_h"] * float(np.max(h_avg_t)):
            hp, lp, np_, H_list, J_cur = ht, lt, nt, H_try, J_try
        else:
            break

    sc_tot = _multiant_score_map(H_list)
    sc_fin = _apply_clut_mask_and_norm(sc_tot, l_grid, nu_grid, lp, np_, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    return {"stat": float(sc_fin[ic, jc]), "l_est": float(l_grid[ic]), "nu_est": float(nu_grid[jc]), "pc_hat": len(lp)}


def rx_luo_multiant_nr(Y, cfg):
    """Multi-antenna (Nr > 1) Y. Luo TCOM'26 D-GESBL (or Pilot-GESBL when constellation is None)."""
    N, Nr = Y.shape
    xp, data_mask, A, Ah = cfg["xp"], cfg["data_mask"], cfg["A"], cfg["Ah"]
    Ah_f = cfg.get("Ah_f", None)
    l_grid, nu_grid = cfg["l_grid"], cfg["nu_grid"]
    l_sbl = np.repeat(np.linspace(0.5, 9.5, 10), 5)
    nu_sbl = np.tile(np.linspace(-2.0, 2.0, 5), 10)
    const = cfg.get("constellation", None)
    Mu, lk, nk, delta, xd_hat, _ = run_luo_gesbl(
        Y, xp, data_mask, A, Ah, l_sbl, nu_sbl, constellation=const,
        sig_d2_nom=cfg.get("sig_d2_nom", 1.0), n_da=3 if const is not None else 1, n_em=10, n_top_evol=4, Ah_f=Ah_f
    )
    x_eff = xp + xd_hat
    pow_atom = np.sqrt(np.mean(np.abs(Mu) ** 2, axis=1))
    ord_idx = np.argsort(pow_atom)[::-1]
    lm, nm, sel_idx = [], [], []
    if pow_atom[ord_idx[0]] > 0.15:
        for idx in ord_idx:
            if len(lm) >= cfg["max_clut"]:
                break
            if len(lm) > 0 and pow_atom[idx] <= cfg["stop_ratio_h"] * pow_atom[ord_idx[0]]:
                break
            if any(abs(lk[idx] - lq) < 1.0 and abs(nk[idx] - nq) < 0.8 for lq, nq in zip(lm, nm)):
                continue
            lm.append(float(lk[idx])); nm.append(float(nk[idx])); sel_idx.append(idx)
    sc_tot = np.zeros((len(l_grid), len(nu_grid)))
    for m in range(Nr):
        hm_m = [Mu[i, m] for i in sel_idx]
        r_m = Y[:, m] - (build_H_eff(N, A, Ah, hm_m, lm, nm, Ah_f=Ah_f) @ x_eff if sel_idx else 0.0)
        sc_tot += isotropic_mf_map(r_m, x_eff, A, Ah, l_grid, nu_grid)
    sc_fin = _apply_clut_mask_and_norm(sc_tot, l_grid, nu_grid, lm, nm, cfg["clut_mask_dl"], cfg["clut_mask_dnu"])
    ic, jc = np.unravel_index(np.argmax(sc_fin), sc_fin.shape)
    return {"stat": float(sc_fin[ic, jc]), "l_est": float(l_grid[ic]), "nu_est": float(nu_grid[jc]), "pc_hat": len(lm)}


# ==============================================================================
# Startup Gates (ALL fail-fast before running ANY L2 regime!)
# ==============================================================================
def run_startup_gates(seed_base):
    N = 128
    G = 24
    c1 = 7.0 / (2.0 * N)
    c2 = 1.0 / (2.0 * np.pi * N)
    A = daft_matrix(N, c1, c2)
    Ah = A.conj().T
    Ah_f = np.fft.fft(Ah, axis=0)
    guard_idx = np.arange(N // 2 - G // 2, N // 2 - G // 2 + G)
    data_mask = np.ones(N, dtype=bool)
    data_mask[guard_idx] = False
    xp = np.zeros(N, dtype=complex)
    xp[N // 2] = math.sqrt(float(G))
    rng = np.random.default_rng(seed_base + 1)

    # 1. Exact Golub-Pereyra pseudoinverse FD gradient check at LARGE noise sigma = 0.14
    hs_g = [0.8 * np.exp(1j * 0.5), 0.6 * np.exp(1j * 2.1)]
    ls_g = [1.25, 3.15]
    nus_g = [0.12, -0.18]
    xd = np.zeros(N, dtype=complex)
    xd[data_mask] = (rng.standard_normal(int(data_mask.sum())) + 1j * rng.standard_normal(int(data_mask.sum()))) / math.sqrt(2.0)
    H_true = build_H_eff(N, A, Ah, hs_g, ls_g, nus_g, Ah_f=Ah_f)
    y_noisy = H_true @ (xp + xd) + (0.14 / math.sqrt(2.0)) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    par = np.array([hs_g[0].real + 0.04, hs_g[0].imag - 0.03, ls_g[0] + 0.08, nus_g[0] - 0.06,
                    hs_g[1].real - 0.05, hs_g[1].imag + 0.02, ls_g[1] - 0.07, nus_g[1] + 0.05], dtype=float)
    _, grad_an, _, _, _, _ = grassmann_null_cost_and_grad(par, y_noisy, xp, data_mask, G, A, Ah, Ah_f=Ah_f)
    grad_fd = np.zeros_like(grad_an)
    eps = 1e-6
    for k in range(len(par)):
        pp = par.copy(); pp[k] += eps
        pm = par.copy(); pm[k] -= eps
        cp, *_ = grassmann_null_cost_and_grad(pp, y_noisy, xp, data_mask, G, A, Ah, Ah_f=Ah_f)
        cm, *_ = grassmann_null_cost_and_grad(pm, y_noisy, xp, data_mask, G, A, Ah, Ah_f=Ah_f)
        grad_fd[k] = (cp - cm) / (2.0 * eps)
    fd_rel_err = float(np.linalg.norm(grad_an - grad_fd) / (np.linalg.norm(grad_fd) + 1e-12))

    # 2. Exact nullspace leakage check ||N_G^H H_d x_d||
    NG = orth_nullspace_NG(H_true, data_mask, G)
    null_leakage = float(np.linalg.norm(NG.conj().T @ (H_true[:, data_mask] @ xd[data_mask])))

    # 3. Genuine rank-deficiency stress test:
    #    (a) exact rank-0 canceling paths (rank(Hd)=0) including full refine_orth_null_gn, AND
    #    (b) non-zero period-2 comb null H_rd = 0.7 B(0,0) - 0.7 B(64,0) at c1=0 (explicitly asserting rank(Hd)==52 < 104!)
    par_zero = np.array([0.7, 0.0, 2.0, 0.0, -0.7, 0.0, 2.0, 0.0], dtype=float)
    c_z, g_z, _, _, _, NG_z = grassmann_null_cost_and_grad(par_zero, y_noisy, xp, data_mask, G, A, Ah, Ah_f=Ah_f)
    hr_z, lr_z, nr_z, cr_z = refine_orth_null_gn(y_noisy, xp, data_mask, G, A, Ah,
                                                  [0.7 + 0j, -0.7 + 0j], [2.0, 2.0], [0.0, 0.0], n_it=3, Ah_f=Ah_f)
    A0 = daft_matrix(N, 0.0, c2); Ah0 = A0.conj().T; Ah0_f = np.fft.fft(Ah0, axis=0)
    H_rd = build_H_eff(N, A0, Ah0, [0.7, -0.7], [0.0, 64.0], [0.0, 0.0], Ah_f=Ah0_f)
    rd_rank = int(np.linalg.matrix_rank(H_rd[:, data_mask]))
    rd_norm = float(np.linalg.norm(H_rd[:, data_mask]))
    par_rd = np.array([0.7, 0.0, 0.0, 0.0, -0.7, 0.0, 64.0, 0.0], dtype=float)
    c_r, g_r, _, _, _, NG_r = grassmann_null_cost_and_grad(par_rd, y_noisy, xp, data_mask, G, A0, Ah0, Ah_f=Ah0_f)
    hr_r, lr_r, nr_r, cr_r = refine_orth_null_gn(y_noisy, xp, data_mask, G, A0, Ah0,
                                                  [0.7 + 0j, -0.7 + 0j], [0.0, 64.0], [0.0, 0.0], n_it=3, Ah_f=Ah0_f)
    rank_def_ok = bool(
        rd_rank == 52 and rd_rank < int(data_mask.sum()) and rd_norm > 1.0
        and np.isfinite(c_z) and np.all(np.isfinite(g_z)) and np.all(np.isfinite(NG_z))
        and np.isfinite(cr_z) and np.all(np.isfinite(hr_z)) and np.all(np.isfinite(lr_z)) and np.all(np.isfinite(nr_z))
        and np.isfinite(c_r) and np.all(np.isfinite(g_r)) and np.all(np.isfinite(NG_r))
        and np.isfinite(cr_r) and np.all(np.isfinite(hr_r)) and np.all(np.isfinite(lr_r)) and np.all(np.isfinite(nr_r))
    )

    # 4. Ablation isolation runtime verification (B_only MUST NOT call orth_nullspace_NG or refine_orth_null_gn!)
    l_grid = np.linspace(0.2, 10.5, 43)
    nu_grid = np.linspace(-2.5, 2.5, 41)
    rx_cfg = {
        "N": N, "G": G, "guard_idx": guard_idx, "data_mask": data_mask, "xp": xp,
        "A": A, "Ah": Ah, "Ah_f": Ah_f, "l_grid": l_grid, "nu_grid": nu_grid,
        "clut_mask_dl": 1.2, "clut_mask_dnu": 0.8, "max_clut": 3,
        "tau_p1": 15.0, "stop_ratio_J": 0.25, "stop_ratio_h": 0.25, "constellation": None,
    }
    c_ng_before = _CALL_COUNTERS["orth_nullspace_NG"]
    c_gn_before = _CALL_COUNTERS["refine_orth_null_gn"]
    _ = rx_b_only_nonullspace(y_noisy, rx_cfg, use_ls_diag=False)
    b_only_isolated = (_CALL_COUNTERS["orth_nullspace_NG"] == c_ng_before
                       and _CALL_COUNTERS["refine_orth_null_gn"] == c_gn_before)

    # 5a. Red Line #1: Y. Luo TCOM'26 Fig. 8 origin (N=256, Nr=8, 4-QAM, 10 dB, c1=9/512) + BLIND noiseless (<1e-12)
    N_l, Nr_l = 256, 8
    A_l = daft_matrix(N_l, 9.0 / 512.0, 1e-5)
    Ah_l = A_l.conj().T
    Ah_l_f = np.fft.fft(Ah_l, axis=0)
    rng_l = np.random.default_rng(seed_base + 10)
    xp_l = math.sqrt(0.2) * QPSK_P[rng_l.integers(0, 4, N_l)]
    xd_l = math.sqrt(0.8) * QPSK_P[rng_l.integers(0, 4, N_l)]
    ls_l = np.array([2.25, 6.70, 10.40])
    nus_l = np.array([-1.30, 0.35, 1.45])
    th_l = np.array([-0.4, 0.2, 0.7])
    gam_l = np.exp(1j * rng_l.uniform(0, 2.0 * np.pi, 3)) / math.sqrt(3.0)
    H_l_true = [build_H_eff(N_l, A_l, Ah_l, gam_l * np.exp(-1j * np.pi * nr * np.sin(th_l)), ls_l, nus_l, Ah_f=Ah_l_f) for nr in range(Nr_l)]
    Y_l_10db = np.column_stack([H_l_true[nr] @ (xp_l + xd_l) for nr in range(Nr_l)]) + math.sqrt(0.1 / 2.0) * (rng_l.standard_normal((N_l, Nr_l)) + 1j * rng_l.standard_normal((N_l, Nr_l)))
    l_gl = np.repeat(np.arange(0.0, 13.0, 1.0), 5)
    nu_gl = np.tile(np.arange(-2.0, 3.0, 1.0), 13)
    Mu_l, lk_l, nk_l, del_l, xd_hl, _ = run_luo_gesbl(
        Y_l_10db, xp_l, np.ones(N_l, dtype=bool), A_l, Ah_l, l_gl, nu_gl,
        constellation=QPSK_P, sig_d2_nom=0.8, n_da=4, n_em=18, n_top_evol=4, b_prior=1e-4, sp_mode=True, Ah_f=Ah_l_f
    )
    act_l = np.where(del_l > 0.05 * float(np.max(del_l)))[0]
    H_l_hat = [build_H_eff(N_l, A_l, Ah_l, Mu_l[act_l, nr], lk_l[act_l], nk_l[act_l], Ah_f=Ah_l_f) for nr in range(Nr_l)]
    luo_nmse_db = 10.0 * math.log10(
        sum(float(np.sum(np.abs(H_l_hat[nr] - H_l_true[nr]) ** 2)) for nr in range(Nr_l)) /
        sum(float(np.sum(np.abs(H_l_true[nr]) ** 2)) for nr in range(Nr_l))
    )
    luo_ser = float(np.mean(np.abs(xd_hl - xd_l) > 1e-3))

    # Genuine BLIND noiseless D-GESBL test (starts from xd_hat=0, regular grid, ZERO truth passed in!)
    ls_on = np.array([2.0, 6.0, 10.0]); nus_on = np.array([-1.0, 0.0, 1.0])
    H_on = [build_H_eff(N_l, A_l, Ah_l, gam_l * np.exp(-1j * np.pi * nr * np.sin(th_l)), ls_on, nus_on, Ah_f=Ah_l_f) for nr in range(Nr_l)]
    Y_on = np.column_stack([H_on[nr] @ (xp_l + xd_l) for nr in range(Nr_l)])
    Mu_0, lk_0, nk_0, del_0, xd_h0, _ = run_luo_gesbl(
        Y_on, xp_l, np.ones(N_l, dtype=bool), A_l, Ah_l, l_gl, nu_gl,
        constellation=QPSK_P, sig_d2_nom=0.8, n_da=4, n_em=25, n_top_evol=0, b_prior=0.0, sp_mode=True, Ah_f=Ah_l_f
    )
    act_0 = np.where(del_0 > 1e-6 * float(np.max(del_0)))[0]
    H_on_hat = [build_H_eff(N_l, A_l, Ah_l, Mu_0[act_0, nr], lk_0[act_0], nk_0[act_0], Ah_f=Ah_l_f) for nr in range(Nr_l)]
    Y_on_rec = np.column_stack([H_on_hat[nr] @ (xp_l + xd_h0) for nr in range(Nr_l)])
    luo_noiseless_err = float(np.linalg.norm(Y_on - Y_on_rec) / np.linalg.norm(Y_on))
    luo_noiseless_ser = float(np.mean(np.abs(xd_h0 - xd_l) > 1e-3))

    # 5b. Red Line #1: Ma 2606.25572 / Bemani WCL'24 2-path full-guard WITH unknown data xd using ACTUAL rx_ma_seq_mf!
    G_fg = 76
    g76 = np.arange(N // 2 - G_fg // 2, N // 2 + G_fg // 2)
    dm76 = np.ones(N, dtype=bool); dm76[g76] = False
    p_win_76 = np.arange(27, 65)
    xp_fg = np.zeros(N, dtype=complex); xp_fg[N // 2] = math.sqrt(float(G_fg))
    xd_fg = np.zeros(N, dtype=complex); xd_fg[dm76] = QAM64_P[rng_l.integers(0, 64, int(dm76.sum()))]
    H_r3c_chk = build_H_eff(N, A, Ah, [0.8, 0.6j, 0.125], [1.0, 3.0, 5.0], [0.0, 0.0, 1.0], Ah_f=Ah_f)
    r3c_g76_coupling_norm = float(np.linalg.norm(H_r3c_chk[p_win_76][:, dm76]))
    # Exact analytical CPP-inclusive expected frame energy E[||P_cpp A^H (xp + xd)||_2^2] == 138.0
    # (With public bit-scrambling XORed after conv_encode, EVERY coded QAM symbol — including the tail symbol —
    # is strictly uniform over the constellation so E[|x_k|^2] == sig_d2 identically, eliminating tail-zero bias!)
    P_cpp_chk = build_cpp_ext(N, c1, 10)
    r3c_cpp_energy_err = 0.0
    for G_c, Ep_c in ((24, 24.0), (76, 24.0), (76, 76.0)):
        gi_c = np.arange(N // 2 - G_c // 2, N // 2 + G_c // 2)
        dm_c = np.ones(N, dtype=bool); dm_c[gi_c] = False
        sd2_c = (float(N) - Ep_c) / float(dm_c.sum())
        xp_c = np.zeros(N, dtype=complex); xp_c[N // 2] = math.sqrt(Ep_c)
        e_pil = float(np.sum(np.abs(P_cpp_chk @ (Ah @ xp_c)) ** 2))
        e_dat = sd2_c * float(np.sum(np.abs(P_cpp_chk @ Ah[:, dm_c]) ** 2))
        r3c_cpp_energy_err = max(r3c_cpp_energy_err, abs((e_pil + e_dat) - 138.0))

    # 1-path full-guard WITH non-zero unknown 64-QAM data: exact noiseless recovery (< 1e-12) by actual rx_ma_seq_mf!
    cfg_ma = {
        "N": N, "G": G_fg, "guard_idx": g76, "data_mask": dm76, "xp": xp_fg,
        "A": A, "Ah": Ah, "Ah_f": Ah_f, "l_grid": np.linspace(0.2, 6.2, 31), "nu_grid": np.linspace(-2.0, 2.0, 33),
        "clut_mask_dl": 0.9, "clut_mask_dnu": 0.8, "max_clut": 4,
        "tau_p1": 14.0, "stop_ratio_J": 0.25, "stop_ratio_h": 0.25, "constellation": None,
    }
    H_ma1 = build_H_eff(N, A, Ah, [0.8 * np.exp(1j * 0.5)], [2.0], [0.0], Ah_f=Ah_f)
    res_ma1_cl = rx_ma_seq_mf(H_ma1 @ (xp_fg + xd_fg), cfg_ma, win_idx=p_win_76, n_newt=8)
    hm1_c, lm1_c, nm1_c = res_ma1_cl["clut"]
    ma_noiseless_err = float(np.linalg.norm(build_H_eff(N, A, Ah, hm1_c, lm1_c, nm1_c, Ah_f=Ah_f) - H_ma1) / np.linalg.norm(H_ma1))
    ma_p_det_clean = int(res_ma1_cl["pc_hat"])
    # 2-path full-guard WITH non-zero unknown 64-QAM data at 20 dB: actual rx_ma_seq_mf achieves NMSE < -20 dB & P_det == 2!
    H_ma = build_H_eff(N, A, Ah, [0.8 * np.exp(1j * 0.5), 0.6 * np.exp(1j * 2.1)], [1.0, 3.0], [0.0, 0.0], Ah_f=Ah_f)
    y_ma_20 = H_ma @ (xp_fg + xd_fg) + math.sqrt(0.01 / 2.0) * (rng_l.standard_normal(N) + 1j * rng_l.standard_normal(N))
    res_ma_20 = rx_ma_seq_mf(y_ma_20, cfg_ma, win_idx=p_win_76, n_newt=5)
    hm_20, lm_20, nm_20 = res_ma_20["clut"]
    H_ma_20 = build_H_eff(N, A, Ah, hm_20, lm_20, nm_20, Ah_f=Ah_f)
    ma_nmse_db = 10.0 * math.log10(float(np.sum(np.abs(H_ma_20 - H_ma) ** 2) / np.sum(np.abs(H_ma) ** 2)))
    ma_p_det_20 = int(res_ma_20["pc_hat"])
    ma_bounds_chk = ma_exact_crb_and_mcrb1(
        N, A, Ah, xp, data_mask, 1.0, 10.0 ** (-2.5),
        [0.8 * np.exp(1j * 0.5), 0.6 * np.exp(1j * 2.1), 0.125 * np.exp(1j * 1.1)],
        [1.2, 3.1, 7.4], [0.1, -0.15, 1.4], Ah_f=Ah_f
    )
    ma_mcrb_to_crb_ratio = float(ma_bounds_chk["mcrb1_l_std"] / max(ma_bounds_chk["crb_l_std"], 1e-12))

    # 5c. Red Line #1: NOMP F_N->A direct port verified directly through ACTUAL main arm rx_nomp_dirport (max_clut=5)!
    xp_fp = QPSK_P[rng_l.integers(0, 4, N)]
    ls_np = [1.35, 4.70, 8.20]; nus_np = [-1.15, 0.45, 1.30]
    hs_np = [0.7 * np.exp(1j * 0.4), 0.55 * np.exp(1j * 1.9), 0.45 * np.exp(1j * 3.8)]
    H_np = build_H_eff(N, A, Ah, hs_np, ls_np, nus_np, Ah_f=Ah_f)
    y_np_clean = H_np @ xp_fp
    y_np_20 = y_np_clean + math.sqrt(0.01 / 2.0) * (rng_l.standard_normal(N) + 1j * rng_l.standard_normal(N))
    cfg_np = {
        "N": N, "G": 0, "guard_idx": np.array([], dtype=int), "data_mask": np.zeros(N, dtype=bool), "xp": xp_fp,
        "A": A, "Ah": Ah, "Ah_f": Ah_f, "l_grid": l_grid, "nu_grid": nu_grid,
        "clut_mask_dl": 1.2, "clut_mask_dnu": 0.8, "max_clut": 5,
        "tau_p1": 15.0, "stop_ratio_J": 0.25, "stop_ratio_h": 0.25, "constellation": None,
    }
    res_np_cl = rx_nomp_dirport(y_np_clean, cfg_np)
    hnp_cl, lnp_cl, nnp_cl = res_np_cl["clut"]
    H_np_cl = build_H_eff(N, A, Ah, hnp_cl, lnp_cl, nnp_cl, Ah_f=Ah_f)
    nomp_noiseless_err = float(np.linalg.norm(H_np_cl - H_np) / np.linalg.norm(H_np))
    nomp_p_det_clean = int(res_np_cl["pc_hat"])
    res_np_20 = rx_nomp_dirport(y_np_20, cfg_np)
    hnp_20, lnp_20, nnp_20 = res_np_20["clut"]
    H_np_20 = build_H_eff(N, A, Ah, hnp_20, lnp_20, nnp_20, Ah_f=Ah_f)
    nomp_nmse_db = 10.0 * math.log10(float(np.sum(np.abs(H_np_20 - H_np) ** 2) / np.sum(np.abs(H_np) ** 2)))
    nomp_p_det_20 = int(res_np_20["pc_hat"])
    # Verify exact order-statistic OS-CFAR threshold X_(b) on 16,000 independent white-noise frames via exact Beta-Binomial predictive interval
    def _eval_white_noise_fa_count(xp_chk, mult, rng_chk, n_tr=16000):
        l_o = np.arange(math.ceil(float(l_grid[0])), math.floor(float(l_grid[-1])) + 1.0, 1.0)
        nu_o = np.arange(math.ceil(float(nu_grid[0])), math.floor(float(nu_grid[-1])) + 1.0, 1.0)
        Dd = _nomp_atom_bank(xp_chk, Ah, l_grid, nu_grid)
        Do = _nomp_atom_bank(xp_chk, Ah, l_o, nu_o)
        fa = 0
        for st in range(0, n_tr, 500):
            bs = min(500, n_tr - st)
            W = (rng_chk.standard_normal((bs, N)) + 1j * rng_chk.standard_normal((bs, N))) / math.sqrt(2.0)
            pd = np.abs(W @ Dd.conj().T) ** 2
            po = np.abs(W @ Do.conj().T) ** 2
            s2 = np.median(po, axis=1) / math.log(2.0)
            fa += int(np.count_nonzero(pd.max(axis=1) > mult * s2))
        return fa

    n_val_nomp = 16000
    a_nomp, b_nomp = exact_order_stat_params(NOMP_CFAR_NCAL, 1e-3)
    k_lo_nomp, k_hi_nomp = exact_betabinom_interval(n_val_nomp, a_nomp, b_nomp, alpha_each=0.05 / 2.0)
    rng_cfar = np.random.default_rng(seed_base + 77777)
    mult_fp = calibrate_nomp_cfar_mult(xp_fp, Ah, l_grid, nu_grid, pfa_cfar=1e-3)
    mult_cg = calibrate_nomp_cfar_mult(xp, Ah, l_grid, nu_grid, pfa_cfar=1e-3)
    # Verify exact element-by-element agreement between _nomp_atom_bank and isotropic_mf_map
    probe_t = (rng_cfar.standard_normal(N) + 1j * rng_cfar.standard_normal(N)) / math.sqrt(2.0)
    atom_bank_err = max(
        float(np.max(np.abs(np.abs(_nomp_atom_bank(xp_chk, Ah, l_grid, nu_grid) @ probe_t.conj()) ** 2
                            - isotropic_mf_map(A @ probe_t, xp_chk, A, Ah, l_grid, nu_grid).ravel())))
        for xp_chk in (xp_fp, xp)
    )
    nomp_k_fp = _eval_white_noise_fa_count(xp_fp, mult_fp, rng_cfar, n_tr=n_val_nomp)
    nomp_k_cg = _eval_white_noise_fa_count(xp, mult_cg, rng_cfar, n_tr=n_val_nomp)
    nomp_pfa_fp = nomp_k_fp / float(n_val_nomp)
    nomp_pfa_cg = nomp_k_cg / float(n_val_nomp)
    # In-script gate IDENTICAL to frozen Beta-Binomial criterion (fwer=2 over full-pilot & compressed-guard pilots)
    nomp_cfar_ok = bool(
        atom_bank_err < 1e-12
        and (k_lo_nomp <= nomp_k_fp <= k_hi_nomp)
        and (k_lo_nomp <= nomp_k_cg <= k_hi_nomp)
    )

    gates_ok = bool(
        fd_rel_err < 1e-7
        and null_leakage < 1e-12
        and rank_def_ok
        and b_only_isolated
        and r3c_g76_coupling_norm < 1e-12
        and r3c_cpp_energy_err < 1e-11
        and luo_nmse_db < -14.0 and luo_ser < 0.01 and luo_noiseless_err < 1e-12 and luo_noiseless_ser == 0.0
        and ma_nmse_db < -20.0 and ma_noiseless_err < 1e-12 and ma_p_det_clean == 1 and ma_p_det_20 == 2 and ma_mcrb_to_crb_ratio > 10.0
        and nomp_nmse_db < -20.0 and nomp_noiseless_err < 1e-12 and nomp_p_det_clean == 3 and nomp_p_det_20 == 3
        and nomp_cfar_ok
    )
    return {
        "GATES_OK": gates_ok,
        "fd_grad_rel_err": fd_rel_err,
        "null_leakage_norm": null_leakage,
        "rank_deficiency_finite": rank_def_ok,
        "rank_def_hd_rank": rd_rank,
        "rank_def_hd_cols": int(data_mask.sum()),
        "ablation_b_only_isolated": b_only_isolated,
        "r3c_g76_coupling_norm": r3c_g76_coupling_norm,
        "r3c_cpp_energy_err": r3c_cpp_energy_err,
        "luo_fig8_nmse_db": luo_nmse_db,
        "luo_fig8_ser": luo_ser,
        "luo_blind_noiseless_err": luo_noiseless_err,
        "luo_blind_noiseless_ser": luo_noiseless_ser,
        "ma_2path_with_data_nmse_db": ma_nmse_db,
        "ma_2path_with_data_noiseless_err": ma_noiseless_err,
        "ma_2path_p_det_clean": ma_p_det_clean,
        "ma_2path_p_det_20db": ma_p_det_20,
        "ma_mcrb1_to_crb_ratio": ma_mcrb_to_crb_ratio,
        "nomp_cfar_stop_nmse_db": nomp_nmse_db,
        "nomp_cfar_stop_noiseless_err": nomp_noiseless_err,
        "nomp_cfar_stop_p_det_clean": nomp_p_det_clean,
        "nomp_cfar_stop_p_det_20db": nomp_p_det_20,
        "nomp_cfar_n_cal": NOMP_CFAR_NCAL,
        "nomp_cfar_bb_ab": [a_nomp, b_nomp],
        "nomp_cfar_bb_fwer2_bounds_k": [k_lo_nomp, k_hi_nomp],
        "nomp_cfar_bb_fwer2_bounds_p": [k_lo_nomp / float(n_val_nomp), k_hi_nomp / float(n_val_nomp)],
        "nomp_cfar_mult_fp": mult_fp,
        "nomp_cfar_mult_cg": mult_cg,
        "nomp_atom_bank_err": atom_bank_err,
        "nomp_white_noise_k_fp_16k": nomp_k_fp,
        "nomp_white_noise_k_cg_16k": nomp_k_cg,
        "nomp_white_noise_pfa_fp_16k": nomp_pfa_fp,
        "nomp_white_noise_pfa_cg_16k": nomp_pfa_cg,
        "nomp_cfar_ok": nomp_cfar_ok,
    }


# ==============================================================================
# Parallel Worker Functions (100% deterministic per-frame seeds!)
# ==============================================================================
def _make_rx_cfg(N=128, G=24, two_Nc1=7, constellation=None, sig_d2_nom=1.0):
    c1 = two_Nc1 / (2.0 * N)
    c2 = 1.0 / (2.0 * np.pi * N)
    A = daft_matrix(N, c1, c2)
    Ah = A.conj().T
    Ah_f = np.fft.fft(Ah, axis=0)
    guard_idx = np.arange(N // 2 - G // 2, N // 2 - G // 2 + G)
    data_mask = np.ones(N, dtype=bool)
    data_mask[guard_idx] = False
    xp = np.zeros(N, dtype=complex)
    xp[N // 2] = math.sqrt(float(G))
    return {
        "N": N, "G": G, "two_Nc1": two_Nc1, "guard_idx": guard_idx, "data_mask": data_mask,
        "xp": xp, "A": A, "Ah": Ah, "Ah_f": Ah_f,
        "l_grid": np.linspace(0.2, 10.5, 43), "nu_grid": np.linspace(-2.5, 2.5, 41),
        "clut_mask_dl": 1.2, "clut_mask_dnu": 0.8, "max_clut": 3,
        "tau_p1": 15.0, "stop_ratio_J": 0.25, "stop_ratio_h": 0.25,
        "constellation": constellation, "sig_d2_nom": sig_d2_nom,
    }


def _gen_scene_nr1(rng, cfg, pc_true, has_tgt, tgt_amp, snr_db, payload_mode="gauss"):
    N, data_mask, xp, A, Ah, Ah_f = cfg["N"], cfg["data_mask"], cfg["xp"], cfg["A"], cfg["Ah"], cfg["Ah_f"]
    sig_n2 = 10.0 ** (-snr_db / 10.0)
    xd = np.zeros(N, dtype=complex)
    Nd = int(data_mask.sum())
    if payload_mode == "gauss":
        xd[data_mask] = (rng.standard_normal(Nd) + 1j * rng.standard_normal(Nd)) / math.sqrt(2.0)
    elif payload_mode == "64qam":
        xd[data_mask] = QAM64_P[rng.integers(0, 64, Nd)]
    w = math.sqrt(sig_n2 / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    if pc_true == 0:
        hs_c, ls_c, nus_c = [], [], []
    elif pc_true == 1:
        hs_c = [1.0 * np.exp(1j * rng.uniform(0, 2.0 * np.pi))]
        ls_c = [float(rng.uniform(0.5, 2.0))]
        nus_c = [float(rng.uniform(-0.2, 0.2))]
    else:
        hs_c = [0.8 * np.exp(1j * rng.uniform(0, 2.0 * np.pi)),
                0.6 * np.exp(1j * rng.uniform(0, 2.0 * np.pi))]
        ls_c = [float(rng.uniform(0.5, 1.8)), float(rng.uniform(2.6, 3.8))]
        nus_c = [float(rng.uniform(-0.2, 0.2)), float(rng.uniform(-0.2, 0.2))]

    tgt_truth = None
    if has_tgt:
        lt = float(rng.uniform(5.2, 9.5))
        nut = float(rng.uniform(-2.0, 2.0))
        if abs(nut) < 0.6:
            nut = (1.0 if nut >= 0 else -1.0) * 1.3
        ht = tgt_amp * np.exp(1j * rng.uniform(0, 2.0 * np.pi))
        hs_all, ls_all, nus_all = hs_c + [ht], ls_c + [lt], nus_c + [nut]
        tgt_truth = {"h": ht, "l": lt, "nu": nut, "hs_all": hs_all, "ls_all": ls_all, "nus_all": nus_all}
    else:
        hs_all, ls_all, nus_all = hs_c, ls_c, nus_c

    y = (build_H_eff(N, A, Ah, hs_all, ls_all, nus_all, Ah_f=Ah_f) @ (xp + xd) + w) if hs_all else w.copy()
    return y, tgt_truth, sig_n2


def _worker_nr1_frame(task):
    seed, regime, pc_true, has_tgt, tgt_amp, snr_db, payload_mode, arms_to_run, two_Nc1, calc_crb = task
    const = QAM64_P if payload_mode == "64qam" else None
    cfg = _make_rx_cfg(N=128, G=24, two_Nc1=two_Nc1, constellation=const, sig_d2_nom=1.0)
    rng = np.random.default_rng(seed)
    y, tgt, sig_n2 = _gen_scene_nr1(rng, cfg, pc_true, has_tgt, tgt_amp, snr_db, payload_mode)
    out = {"seed": seed, "pc_true": pc_true, "has_tgt": has_tgt, "arms": {}}
    arm_fn = {
        "Ma_SeqMF": rx_ma_seq_mf,
        "Luo_GESBL": rx_luo_gesbl,
        "NOMP_DirPort": rx_nomp_dirport,
        "A_only_NullPilot": rx_a_only_nullpilot,
        "B_only_NoNullspace": lambda yy, cc: rx_b_only_nonullspace(yy, cc, use_ls_diag=False),
        "B_only_NOMP_LS_Diag": lambda yy, cc: rx_b_only_nonullspace(yy, cc, use_ls_diag=True),
        "B_only_TikhonovDet_Diag": rx_b_tikhonov_det_diag,
        "Ours_GrassNull": rx_ours_grassnull,
    }
    for arm in arms_to_run:
        res = arm_fn[arm](y, cfg)
        entry = {"stat": res["stat"], "pc_hat": res["pc_hat"]}
        if has_tgt:
            hit = bool(abs(res["l_est"] - tgt["l"]) < 0.5 and abs(res["nu_est"] - tgt["nu"]) < 0.5)
            entry["hit"] = hit
            entry["dl"] = float(res["l_est"] - tgt["l"])
            entry["dnu"] = float(res["nu_est"] - tgt["nu"])
            entry["dh_mag"] = float(abs(res["h_est"]) - abs(tgt["h"]))
        out["arms"][arm] = entry
    if has_tgt and calc_crb:
        out["crb"] = ma_exact_crb_and_mcrb1(
            cfg["N"], cfg["A"], cfg["Ah"], cfg["xp"], cfg["data_mask"], 1.0, sig_n2,
            tgt["hs_all"], tgt["ls_all"], tgt["nus_all"], Ah_f=cfg["Ah_f"]
        )
    return out


def _worker_nr8_frame(task):
    seed, has_tgt, snr_db, payload_mode = task
    Nr = 8
    const = QAM64_P if payload_mode == "64qam" else None
    cfg = _make_rx_cfg(N=128, G=24, two_Nc1=7, constellation=const, sig_d2_nom=1.0)
    N, data_mask, xp, A, Ah, Ah_f = cfg["N"], cfg["data_mask"], cfg["xp"], cfg["A"], cfg["Ah"], cfg["Ah_f"]
    rng = np.random.default_rng(seed)
    sig_n2 = 10.0 ** (-snr_db / 10.0)
    Nd = int(data_mask.sum())
    xd = np.zeros(N, dtype=complex)
    if payload_mode == "gauss":
        xd[data_mask] = (rng.standard_normal(Nd) + 1j * rng.standard_normal(Nd)) / math.sqrt(2.0)
    else:
        xd[data_mask] = QAM64_P[rng.integers(0, 64, Nd)]
    hc = [0.8 * np.exp(1j * rng.uniform(0, 2.0 * np.pi)), 0.6 * np.exp(1j * rng.uniform(0, 2.0 * np.pi))]
    lc = [float(rng.uniform(0.5, 1.8)), float(rng.uniform(2.6, 3.8))]
    nuc = [float(rng.uniform(-0.2, 0.2)), float(rng.uniform(-0.2, 0.2))]
    th_c = [float(rng.uniform(-0.8, 0.8)), float(rng.uniform(-0.8, 0.8))]
    if has_tgt:
        lt = float(rng.uniform(5.2, 9.5))
        nut = float(rng.uniform(-2.0, 2.0))
        if abs(nut) < 0.6:
            nut = (1.0 if nut >= 0 else -1.0) * 1.3
        ht = 0.125 * np.exp(1j * rng.uniform(0, 2.0 * np.pi))
        th_t = float(rng.uniform(-0.8, 0.8))
        hs_a, ls_a, nus_a, th_a = hc + [ht], lc + [lt], nuc + [nut], th_c + [th_t]
    else:
        hs_a, ls_a, nus_a, th_a = hc, lc, nuc, th_c
    Y = np.zeros((N, Nr), dtype=complex)
    for m in range(Nr):
        hm_m = [h * np.exp(-1j * np.pi * m * math.sin(th)) for h, th in zip(hs_a, th_a)]
        Y[:, m] = build_H_eff(N, A, Ah, hm_m, ls_a, nus_a, Ah_f=Ah_f) @ (xp + xd) + math.sqrt(sig_n2 / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    r_luo = rx_luo_multiant_nr(Y, cfg)
    r_ours = rx_ours_multiant_nr(Y, cfg)
    res = {"has_tgt": has_tgt, "arms": {}}
    for name, r in [("Luo_GESBL_Nr8", r_luo), ("Ours_GrassNull_Nr8", r_ours)]:
        e = {"stat": r["stat"]}
        if has_tgt:
            e["hit"] = bool(abs(r["l_est"] - lt) < 0.5 and abs(r["nu_est"] - nut) < 0.5)
        res["arms"][name] = e
    return res


def _worker_fixed_crb_trial(seed):
    cfg = _make_rx_cfg(N=128, G=24, two_Nc1=7)
    N, data_mask, xp, A, Ah, Ah_f = cfg["N"], cfg["data_mask"], cfg["xp"], cfg["A"], cfg["Ah"], cfg["Ah_f"]
    sig_n2 = 10.0 ** (-2.5)
    hs_t = [0.8 * np.exp(1j * 0.5), 0.6 * np.exp(1j * 2.1), 0.125 * np.exp(1j * 1.1)]
    ls_t = [1.2, 3.1, 7.4]
    nus_t = [0.1, -0.15, 1.4]
    rng = np.random.default_rng(seed)
    xd = np.zeros(N, dtype=complex)
    xd[data_mask] = (rng.standard_normal(int(data_mask.sum())) + 1j * rng.standard_normal(int(data_mask.sum()))) / math.sqrt(2.0)
    y = build_H_eff(N, A, Ah, hs_t, ls_t, nus_t, Ah_f=Ah_f) @ (xp + xd) + math.sqrt(sig_n2 / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    r = rx_ours_grassnull(y, cfg, do_joint_refine=True)
    hit = bool(abs(r["l_est"] - 7.4) < 0.5 and abs(r["nu_est"] - 1.4) < 0.5)
    return {
        "hit": hit,
        "dl": float(r["l_est"] - 7.4),
        "dnu": float(r["nu_est"] - 1.4),
        "dh_mag": float(abs(r["h_est"]) - 0.125),
    }


def _worker_equal_throughput_frame(task):
    """Paired blind-CE & oracle-CE coded BLER + blind sensing for EXACT 206 net info bits / 138 samples:
    - N=128, L_cpp=10 (total 138 samples), exact per-frame realized TX energy INCLUDING CPP normalized to
      ||P_cpp @ A^H @ (xp + xd)||_2^2 == 138.0 across ALL 3 systems!
    - Zero-coupling full-guard Bemani geometry (l_c=[1,3], l_t=5, nu_c=[0,0], nu_t in {-1,+1}, verified
      ||H[p_win, D_76]||_F = 4.45e-13 < 1e-12; ALL estimators remain strictly continuous & blind!).
    - Identical 1-pass symmetric DF CE polish + soft-LLR Viterbi decoder applied to BOTH Ours_G24 and Std_G76.
    """
    seed, snr_db = task
    N = 128
    L_cpp = 10
    c1 = 7.0 / (2.0 * N)
    c2 = 1.0 / (2.0 * np.pi * N)
    A = daft_matrix(N, c1, c2)
    Ah = A.conj().T
    Ah_f = np.fft.fft(Ah, axis=0)
    P_cpp = build_cpp_ext(N, c1, L_cpp)
    l_grid = np.linspace(0.2, 6.2, 31)
    nu_grid = np.linspace(-2.0, 2.0, 33)
    p_win_76 = np.arange(27, 65)
    rng = np.random.default_rng(seed)
    sig_n2 = 10.0 ** (-snr_db / 10.0)

    hc = [0.8 * np.exp(1j * rng.uniform(0, 2.0 * np.pi)), 0.6 * np.exp(1j * rng.uniform(0, 2.0 * np.pi))]
    lc = [1.0, 3.0]
    nuc = [0.0, 0.0]
    lt = 5.0
    nut = float(rng.choice([-1.0, 1.0]))
    ht = 0.125 * np.exp(1j * rng.uniform(0, 2.0 * np.pi))
    H_true = build_H_eff(N, A, Ah, hc + [ht], lc + [lt], nuc + [nut], Ah_f=Ah_f)
    info_bits = rng.integers(0, 2, 206)
    w_unit = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / math.sqrt(2.0)

    def _decode_blind_sym_df(y, H_init, s2_init, xp_s, dm, sig_d2, pts, btbl, rate23, l_i, nu_i, scr):
        Nd = int(dm.sum())
        H_use, s2_use = H_init, s2_init
        for it in range(2):
            Hd = H_use[:, dm] * math.sqrt(sig_d2)
            W = np.linalg.inv(Hd.conj().T @ Hd + s2_use * np.eye(Nd)) @ Hd.conj().T
            z = W @ (y - H_use @ xp_s)
            mu = np.real(np.sum(W * Hd.T, axis=1))
            z_u = z / np.maximum(mu, 1e-6)
            pvar = np.maximum((1.0 - mu) / np.maximum(mu, 1e-6), 1e-5)
            if it == 0 and len(l_i) > 0:
                xd_h = np.zeros(N, dtype=complex)
                xd_h[dm] = math.sqrt(sig_d2) * pts[np.argmin(np.abs(z_u[:, None] - pts[None, :]), axis=1)]
                xf = xp_s + xd_h
                hp, lp, np_ = nomp_joint_refinement(y, xf, A, Ah, [0.5 + 0j] * len(l_i), l_i, nu_i, n_cyc=2, n_newt=3)
                H_use = build_H_eff(N, A, Ah, hp, lp, np_, Ah_f=Ah_f)
                s2_use = max(float(np.median(np.abs(y - H_use @ xf) ** 2) / math.log(2.0)), 1e-4)
            else:
                # Descramble LLRs using standard public 3GPP/Wi-Fi bit-scrambling sequence
                llrs = demap_llr(z_u, pvar, pts, btbl) * (1.0 - 2.0 * scr)
                return int(not np.array_equal(viterbi_decode_llr(llrs, 206, rate23=rate23), info_bits))

    def _eval_one(G, M_qam, rate23, Ep, is_ours):
        pts, btbl = (QAM64_P, QAM64_B) if M_qam == 64 else (QAM16_P, QAM16_B)
        nb = 6 if M_qam == 64 else 4
        guard_idx = np.arange(N // 2 - G // 2, N // 2 + G // 2)
        data_mask = np.ones(N, dtype=bool)
        data_mask[guard_idx] = False
        Nd = int(data_mask.sum())
        sig_d2 = (float(N) - Ep) / Nd
        xp = np.zeros(N, dtype=complex); xp[N // 2] = math.sqrt(Ep)
        cbits = conv_encode(info_bits, rate23=rate23)
        # Standard public PHY bit-scrambler (uniformizes tail bits -> exact E[||P_cpp A^H (xp+xd)||^2] == 138.000000!)
        scr = rng.integers(0, 2, len(cbits))
        xd = np.zeros(N, dtype=complex); xd[data_mask] = math.sqrt(sig_d2) * map_qam_bits(cbits ^ scr, pts, nb)
        e_tx_realized = float(np.sum(np.abs(P_cpp @ (Ah @ (xp + xd))) ** 2))
        y = H_true @ (xp + xd) + math.sqrt(sig_n2) * w_unit

        cfg = {
            "N": N, "G": G, "guard_idx": guard_idx, "data_mask": data_mask, "xp": xp,
            "A": A, "Ah": Ah, "Ah_f": Ah_f, "l_grid": l_grid, "nu_grid": nu_grid,
            "clut_mask_dl": 0.9, "clut_mask_dnu": 0.8, "max_clut": 3,
            "tau_p1": 14.0, "stop_ratio_J": 0.25, "stop_ratio_h": 0.25, "constellation": None,
        }
        if is_ours:
            hp, lp, np_, J_c = _blind_grassmann_clutter(y, cfg, use_self_ref_for_peel=True, n_it=6)
            H_c = build_H_eff(N, A, Ah, hp, lp, np_, Ah_f=Ah_f) if len(hp) > 0 else np.zeros((N, N), dtype=complex)
            sc, hm = orth_null_score_map(y, xp, data_mask, G, H_c, A, Ah, l_grid, nu_grid, use_self_ref=True)
            sc_m = _apply_clut_mask_and_norm(sc, l_grid, nu_grid, lp, np_, 0.9, 0.8)
            ic, jc = np.unravel_index(np.argmax(sc_m), sc_m.shape)
            hit = int(abs(l_grid[ic] - lt) < 0.5 and abs(nu_grid[jc] - nut) < 0.5)
            if sc_m[ic, jc] > 10.0 and len(hp) > 0:
                h3, l3, n3, J3 = refine_orth_null_gn(y, xp, data_mask, G, A, Ah,
                                                     list(hp) + [hm[ic, jc]], list(lp) + [l_grid[ic]], list(np_) + [nu_grid[jc]], n_it=6, Ah_f=Ah_f)
                H_hat = build_H_eff(N, A, Ah, h3, l3, n3, Ah_f=Ah_f)
                sig2_hat = max(J3 / max(G - 4 * len(h3), 4), 1e-4)
                l_i, nu_i = l3, n3
            else:
                H_hat = H_c
                sig2_hat = max(J_c / max(G - 4 * len(hp), 4), 1e-4)
                l_i, nu_i = lp, np_
        else:
            hm, lm, nm, r_c = _blind_nomp_clutter(y, cfg, win_idx=p_win_76)
            sc_s = _apply_clut_mask_and_norm(isotropic_mf_map(r_c, xp, A, Ah, l_grid, nu_grid),
                                             l_grid, nu_grid, lm, nm, 0.9, 0.8)
            ic, jc = np.unravel_index(np.argmax(sc_s), sc_s.shape)
            hit = int(abs(l_grid[ic] - lt) < 0.5 and abs(nu_grid[jc] - nut) < 0.5)
            if sc_s[ic, jc] > 10.0 and len(hm) > 0:
                h3, l3, n3 = nomp_joint_refinement(y, xp, A, Ah,
                                                   list(hm) + [0.1 + 0j], list(lm) + [l_grid[ic]], list(nm) + [nu_grid[jc]],
                                                   n_cyc=2, n_newt=3, win_idx=p_win_76)
                H_hat = build_H_eff(N, A, Ah, h3, l3, n3, Ah_f=Ah_f)
                l_i, nu_i = l3, n3
            else:
                H_hat = build_H_eff(N, A, Ah, hm, lm, nm, Ah_f=Ah_f) if len(hm) > 0 else np.zeros((N, N), dtype=complex)
                l_i, nu_i = lm, nm
            r_g = (y - H_hat @ xp)[p_win_76]
            sig2_hat = max(float(np.sum(np.abs(r_g) ** 2)) / max(len(p_win_76) - 4 * len(hm), 4), 1e-4)

        err_blind = _decode_blind_sym_df(y, H_hat, sig2_hat, xp, data_mask, sig_d2, pts, btbl, rate23, l_i, nu_i, scr)
        Hd_o = H_true[:, data_mask] * math.sqrt(sig_d2)
        W_o = np.linalg.inv(Hd_o.conj().T @ Hd_o + sig_n2 * np.eye(Nd)) @ Hd_o.conj().T
        z_o = W_o @ (y - H_true @ xp)
        mu_o = np.real(np.sum(W_o * Hd_o.T, axis=1))
        llrs_o = demap_llr(z_o / np.maximum(mu_o, 1e-6), np.maximum((1.0 - mu_o) / np.maximum(mu_o, 1e-6), 1e-5), pts, btbl) * (1.0 - 2.0 * scr)
        err_oracle = int(not np.array_equal(viterbi_decode_llr(llrs_o, 206, rate23=rate23), info_bits))
        return err_blind, err_oracle, hit, e_tx_realized

    eb_o, eo_o, h_o, et_o = _eval_one(24, 16, False, 24.0, is_ours=True)
    eb_76_24, eo_76_24, h_76_24, et_24 = _eval_one(76, 64, True, 24.0, is_ours=False)
    eb_76_76, eo_76_76, h_76_76, et_76 = _eval_one(76, 64, True, 76.0, is_ours=False)
    return {
        "snr_db": snr_db,
        "ours_err_blind": eb_o, "ours_err_oracle": eo_o, "ours_hit": h_o, "ours_etx": et_o,
        "g76_ep24_err_blind": eb_76_24, "g76_ep24_err_oracle": eo_76_24, "g76_ep24_hit": h_76_24, "g76_ep24_etx": et_24,
        "g76_ep76_err_blind": eb_76_76, "g76_ep76_err_oracle": eo_76_76, "g76_ep76_hit": h_76_76, "g76_ep76_etx": et_76,
    }


def _worker_woodbury_diag(seed):
    """Non-gating SCOPE_READOUT comparing exact Woodbury marginal NLL (Ma Eq. 9 WITH ln det C(theta),
    using oracle sigma2) vs sigma2-free Grassmannian J_null on identical R2 frames.
    """
    cfg = _make_rx_cfg(N=128, G=24, two_Nc1=7)
    N, G, data_mask, xp, A, Ah, Ah_f = cfg["N"], cfg["G"], cfg["data_mask"], cfg["xp"], cfg["A"], cfg["Ah"], cfg["Ah_f"]
    rng = np.random.default_rng(seed)
    y, tgt, sig_n2 = _gen_scene_nr1(rng, cfg, pc_true=2, has_tgt=True, tgt_amp=0.125, snr_db=25.0, payload_mode="gauss")

    t0 = time.perf_counter()
    r_ours = rx_ours_grassnull(y, cfg, do_joint_refine=True)
    t_jnull = time.perf_counter() - t0
    hit_j = bool(abs(r_ours["l_est"] - tgt["l"]) < 0.5 and abs(r_ours["nu_est"] - tgt["nu"]) < 0.5)

    t1 = time.perf_counter()
    hp, lp, np_ = r_ours["clut"]
    hs0 = list(hp) + [r_ours["h_est"]]
    ls0 = list(lp) + [r_ours["l_est"]]
    nus0 = list(np_) + [r_ours["nu_est"]]
    P = len(hs0)
    par = np.zeros(4 * P)
    for p in range(P):
        par[4 * p], par[4 * p + 1], par[4 * p + 2], par[4 * p + 3] = hs0[p].real, hs0[p].imag, ls0[p], nus0[p]

    def nll_eq9(pv):
        H = build_H_eff(N, A, Ah,
                        [pv[4 * p] + 1j * pv[4 * p + 1] for p in range(P)],
                        [pv[4 * p + 2] for p in range(P)],
                        [pv[4 * p + 3] for p in range(P)], Ah_f=Ah_f)
        Hd = H[:, data_mask]
        C = Hd @ Hd.conj().T + sig_n2 * np.eye(N)
        cf = cho_factor(C, check_finite=False)
        ld = 2.0 * float(np.sum(np.log(np.diag(cf[0]).real)))
        r = y - H @ xp
        q = float(np.real(r.conj() @ cho_solve(cf, r, check_finite=False)))
        return ld + q

    c_cur = nll_eq9(par)
    base = 4 * (P - 1)
    eps_v = np.array([1e-3, 1e-3, 1e-3, 1e-3])
    for _ in range(3):
        g = np.zeros(4); h_d = np.zeros(4)
        for k in range(4):
            pp = par.copy(); pp[base + k] += eps_v[k]
            pm = par.copy(); pm[base + k] -= eps_v[k]
            cp, cm = nll_eq9(pp), nll_eq9(pm)
            g[k] = (cp - cm) / (2.0 * eps_v[k])
            h_d[k] = max((cp - 2.0 * c_cur + cm) / (eps_v[k] ** 2), 1.0)
        step = np.clip(-g / h_d, -0.15, 0.15)
        alpha = 1.0
        for _ in range(4):
            pt = par.copy(); pt[base:base + 4] += alpha * step
            c1 = nll_eq9(pt)
            if c1 < c_cur:
                par, c_cur = pt, c1
                break
            alpha *= 0.5
    t_wood = time.perf_counter() - t1
    h_w = par[base] + 1j * par[base + 1]
    l_w, nu_w = par[base + 2], par[base + 3]
    return {
        "hit": hit_j,
        "jnull_dl": float(r_ours["l_est"] - tgt["l"]),
        "jnull_dnu": float(r_ours["nu_est"] - tgt["nu"]),
        "jnull_dh": float(abs(r_ours["h_est"]) - abs(tgt["h"])),
        "wood_dl": float(l_w - tgt["l"]),
        "wood_dnu": float(nu_w - tgt["nu"]),
        "wood_dh": float(abs(h_w) - abs(tgt["h"])),
        "t_jnull": t_jnull, "t_wood": t_wood,
    }


# ==============================================================================
# Evaluation & Aggregation Helpers
# ==============================================================================
def aggregate_regime(cal_res, ver_res, h1_res, arms, pfa_nom=0.02, primary_arm="Ours_GrassNull", fwer_arms=None):
    out = {"pfa_nominal": pfa_nom, "n_cal": len(cal_res), "n_ver": len(ver_res), "n_h1": len(h1_res), "arms": {}}
    thresholds = {}
    hits_by_arm = {}
    m_fwer = len(arms) if fwer_arms is None else int(fwer_arms)
    for arm in arms:
        cal_stats = np.array([r["arms"][arm]["stat"] for r in cal_res], dtype=float)
        tau, a_bb, b_bb = exact_order_stat_threshold(cal_stats, pfa_nom)
        thresholds[arm] = tau
        ver_stats = np.array([r["arms"][arm]["stat"] for r in ver_res], dtype=float)
        n_ver = len(ver_stats)
        k_fa = int(np.sum(ver_stats > tau))
        pfa_ver = k_fa / max(n_ver, 1)
        pfa_ci = wilson_ci(k_fa, n_ver)
        k_lo_bb, k_hi_bb = exact_betabinom_interval(n_ver, a_bb, b_bb, alpha_each=0.05 / float(m_fwer))
        bb_pass = bool(k_lo_bb <= k_fa <= k_hi_bb)

        h1_det = np.array([(r["arms"][arm]["stat"] > tau) and r["arms"][arm]["hit"] for r in h1_res], dtype=bool)
        raw_hit = np.array([r["arms"][arm]["hit"] for r in h1_res], dtype=bool)
        hits_by_arm[arm] = h1_det
        n_det = int(np.sum(h1_det))
        hit_pd = n_det / max(len(h1_res), 1)
        pd_ci = wilson_ci(n_det, len(h1_res))

        has_est = (len(h1_res) > 0 and "dl" in h1_res[0]["arms"][arm])
        entry = {
            "tau_cal": tau,
            "order_stat_ab": [a_bb, b_bb],
            "k_fa_verify": k_fa,
            "pfa_verify": float(pfa_ver),
            "pfa_verify_ci95": pfa_ci,
            "pfa_bb_fwer_m": m_fwer,
            "pfa_bb_bounds_k": [k_lo_bb, k_hi_bb],
            "pfa_bb_bounds_p": [k_lo_bb / float(max(n_ver, 1)), k_hi_bb / float(max(n_ver, 1))],
            "pfa_bb_pass": bb_pass,
            "hit_pd": float(hit_pd),
            "hit_pd_ci95": pd_ci,
            "miss_rate": float(1.0 - hit_pd),
            "raw_hit_rate": float(np.mean(raw_hit)) if len(raw_hit) else 0.0,
            "n_detected": n_det,
        }
        if n_det > 0 and has_est:
            dls = np.array([r["arms"][arm]["dl"] for r, ok in zip(h1_res, h1_det) if ok], dtype=float)
            dnus = np.array([r["arms"][arm]["dnu"] for r, ok in zip(h1_res, h1_det) if ok], dtype=float)
            dhs = np.array([r["arms"][arm]["dh_mag"] for r, ok in zip(h1_res, h1_det) if ok], dtype=float)
            entry["rmse_l"] = float(np.sqrt(np.mean(dls ** 2)))
            entry["rmse_nu"] = float(np.sqrt(np.mean(dnus ** 2)))
            entry["h_mag_bias"] = float(np.mean(dhs))
            entry["h_mag_var"] = float(np.var(dhs, ddof=1)) if n_det > 1 else 0.0
            entry["h_mag_mse"] = float(np.mean(dhs ** 2))
            entry["h_mag_rmse"] = float(np.sqrt(np.mean(dhs ** 2)))
        else:
            entry["rmse_l"] = None; entry["rmse_nu"] = None
            entry["h_mag_bias"] = None; entry["h_mag_var"] = None
            entry["h_mag_mse"] = None; entry["h_mag_rmse"] = None
        out["arms"][arm] = entry

    if primary_arm in hits_by_arm:
        out["paired_diff_vs_ours"] = {}
        for arm in arms:
            if arm == primary_arm:
                continue
            md, ci = paired_diff_ci(hits_by_arm[primary_arm], hits_by_arm[arm])
            out["paired_diff_vs_ours"][arm] = {"diff_pd": md, "ci95": ci}

    if h1_res and "crb" in h1_res[0] and primary_arm in hits_by_arm:
        det_crbs = [r["crb"] for r, ok in zip(h1_res, hits_by_arm[primary_arm]) if ok]
        all_crbs = [r["crb"] for r in h1_res]
        src = det_crbs if det_crbs else all_crbs
        out["matched_geometry_bounds"] = {
            "n_frames": len(src),
            "ma_crb_h_rmse": float(np.sqrt(np.mean([c["crb_h_std"] ** 2 for c in src]))),
            "ma_crb_l_rmse": float(np.sqrt(np.mean([c["crb_l_std"] ** 2 for c in src]))),
            "ma_crb_nu_rmse": float(np.sqrt(np.mean([c["crb_nu_std"] ** 2 for c in src]))),
            "ma_mcrb1_h_rmse": float(np.sqrt(np.mean([c["mcrb1_h_std"] ** 2 for c in src]))),
            "ma_mcrb1_l_rmse": float(np.sqrt(np.mean([c["mcrb1_l_std"] ** 2 for c in src]))),
            "ma_mcrb1_nu_rmse": float(np.sqrt(np.mean([c["mcrb1_nu_std"] ** 2 for c in src]))),
        }
    return out, thresholds


def run_r4_analytical_scnr_bound(seed_base, n_mc=400):
    settings = [
        {"name": "S1_N128_G24_2path_25dB", "N": 128, "G": 24, "two_Nc1": 7, "snr_db": 25.0,
         "hc": [0.8 * np.exp(1j * 0.5), 0.6 * np.exp(1j * 2.1)], "lc": [1.2, 3.1], "nuc": [0.1, -0.15],
         "ht": 0.125 * np.exp(1j * 1.1), "lt": 7.4, "nut": 1.4},
        {"name": "S2_N128_G16_1path_25dB", "N": 128, "G": 16, "two_Nc1": 7, "snr_db": 25.0,
         "hc": [1.0 * np.exp(1j * 0.7)], "lc": [1.5], "nuc": [-0.08],
         "ht": 0.10 * np.exp(1j * 2.2), "lt": 6.8, "nut": -1.3},
        {"name": "S3_N256_G32_2path_20dB", "N": 256, "G": 32, "two_Nc1": 9, "snr_db": 20.0,
         "hc": [0.8 * np.exp(1j * 0.3), 0.6 * np.exp(1j * 1.8)], "lc": [2.1, 5.4], "nuc": [0.15, -0.12],
         "ht": 0.10 * np.exp(1j * 0.9), "lt": 11.3, "nut": 1.6},
    ]
    results = []
    max_err = 0.0
    for idx, s in enumerate(settings):
        N, G = s["N"], s["G"]
        c1 = s["two_Nc1"] / (2.0 * N)
        c2 = 1.0 / (2.0 * np.pi * N)
        A = daft_matrix(N, c1, c2)
        Ah = A.conj().T
        Ah_f = np.fft.fft(Ah, axis=0)
        guard_idx = np.arange(N // 2 - G // 2, N // 2 - G // 2 + G)
        data_mask = np.ones(N, dtype=bool); data_mask[guard_idx] = False
        xp = np.zeros(N, dtype=complex); xp[N // 2] = math.sqrt(float(G))
        sig_n2 = 10.0 ** (-s["snr_db"] / 10.0)
        H_c = build_H_eff(N, A, Ah, s["hc"], s["lc"], s["nuc"], Ah_f=Ah_f)
        B_t = build_B_path(N, A, Ah, s["lt"], s["nut"], Ah_f=Ah_f)
        NG = orth_nullspace_NG(H_c, data_mask, G)
        pil_gain = float(np.sum(np.abs(NG.conj().T @ (B_t @ xp)) ** 2))
        dat_gain = float(np.sum(np.abs((NG.conj().T @ B_t)[:, data_mask]) ** 2))
        scnr_ana = (abs(s["ht"]) ** 2 / sig_n2) * (pil_gain + dat_gain)
        rng = np.random.default_rng(seed_base + 400001 + idx * 1000)
        mc_acc = 0.0
        Nd = int(data_mask.sum())
        for _ in range(n_mc):
            xd = np.zeros(N, dtype=complex)
            xd[data_mask] = (rng.standard_normal(Nd) + 1j * rng.standard_normal(Nd)) / math.sqrt(2.0)
            s_n = s["ht"] * (NG.conj().T @ (B_t @ (xp + xd)))
            mc_acc += float(np.sum(np.abs(s_n) ** 2)) / sig_n2
        scnr_mc = mc_acc / n_mc
        ana_db = 10.0 * math.log10(scnr_ana)
        mc_db = 10.0 * math.log10(scnr_mc)
        err_db = abs(ana_db - mc_db)
        max_err = max(max_err, err_db)
        results.append({
            "name": s["name"], "N": N, "G": G,
            "pil_gain": pil_gain, "data_gain": dat_gain, "data_gain_frac": dat_gain / G,
            "ana_db": ana_db, "mc_db": mc_db, "err_db": err_db,
        })

    N = 128; G = 24; c2 = 1.0 / (2.0 * np.pi * N)
    d_contig = np.ones(N, dtype=bool); d_contig[np.arange(N // 2 - 12, N // 2 + 12)] = False
    d_comb = np.ones(N, dtype=bool); d_comb[np.linspace(0, N - 1, G, dtype=int)] = False
    hc = [0.8 * np.exp(1j * 0.5), 0.6 * np.exp(1j * 2.1)]; lc = [1.2, 3.1]; nuc = [0.1, -0.15]
    diag_2x2 = []
    for nut in [0.05, 1.40]:
        for lbl, two_c, dm in [("AFDM_contig", 7, d_contig), ("OFDM_contig", 0, d_contig),
                               ("AFDM_comb", 7, d_comb), ("OFDM_comb", 0, d_comb)]:
            At = daft_matrix(N, two_c / (2.0 * N), c2); Aht = At.conj().T; Aht_f = np.fft.fft(Aht, axis=0)
            Hc = build_H_eff(N, At, Aht, hc, lc, nuc, Ah_f=Aht_f)
            Bt = build_B_path(N, At, Aht, 7.4, nut, Ah_f=Aht_f)
            NG = orth_nullspace_NG(Hc, dm, G)
            dg = float(np.sum(np.abs((NG.conj().T @ Bt)[:, dm]) ** 2))
            diag_2x2.append({"nu_t": nut, "layout": lbl, "data_gain": dg, "frac_of_G": dg / G})
    return {"settings": results, "max_err_db": max_err, "contig_comb_2x2_diag": diag_2x2}


# ==============================================================================
# Strict Crossing Interpolation (NO extrapolation fallback!)
# ==============================================================================
def strict_interp_snr_at_bler(curve, key, target):
    """Returns interpolated SNR (dB) where BLER strictly crosses below `target` (ys[i] >= target > ys[i+1])
    and remains strictly < target for all higher SNRs (no endpoint extrapolation, no noisy early-dip credit).
    """
    xs = [c["snr_db"] for c in curve]
    ys = [c[key] for c in curve]
    for i in range(len(xs) - 1):
        if ys[i] >= target and ys[i + 1] < target and all(y < target for y in ys[i + 1:]):
            ly0 = math.log10(max(ys[i], 1e-4))
            ly1 = math.log10(max(ys[i + 1], 1e-4))
            lt = math.log10(target)
            frac = (ly0 - lt) / max(ly0 - ly1, 1e-9)
            return float(xs[i] + frac * (xs[i + 1] - xs[i]))
    return None


# ==============================================================================
# Main Orchestrator
# ==============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Fast local Mac sanity run (disjoint seeds 2028000000+)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=str, required=True)
    args = parser.parse_args()

    t_start = time.time()
    n_workers = 1 if args.smoke else min(args.workers, 8)
    # Strictly disjoint seed namespaces: smoke=2028000000+, full L2=2030000000+ (0% overlap with smoke or prior 2029 runs!)
    SEED_BASE = 2028000000 if args.smoke else 2030000000

    def run_pool(fn, tasks):
        if n_workers <= 1:
            return [fn(t) for t in tasks]
        with Pool(n_workers) as pool:
            return pool.map(fn, tasks)

    # 0. Startup Gates (FAIL-FAST!)
    gates = run_startup_gates(SEED_BASE)
    print(f"[Gates] GATES_OK={gates['GATES_OK']} | FD={gates['fd_grad_rel_err']:.2e} | "
          f"Leak={gates['null_leakage_norm']:.2e} | RankDef={gates['rank_deficiency_finite']}({gates['rank_def_hd_rank']}/{gates['rank_def_hd_cols']}) | "
          f"B_iso={gates['ablation_b_only_isolated']} | R3c_coup={gates['r3c_g76_coupling_norm']:.2e} | "
          f"Luo={gates['luo_fig8_nmse_db']:.2f}dB/nl={gates['luo_blind_noiseless_err']:.1e} | "
          f"Ma={gates['ma_2path_with_data_nmse_db']:.2f}dB/nl={gates['ma_2path_with_data_noiseless_err']:.1e}/MCRB={gates['ma_mcrb1_to_crb_ratio']:.1f}x | "
          f"NOMP={gates['nomp_cfar_stop_nmse_db']:.2f}dB/nl={gates['nomp_cfar_stop_noiseless_err']:.1e}", flush=True)
    if not gates["GATES_OK"]:
        fail_summary = {
            "card_id": "I-20261125-m04", "mode": "smoke" if args.smoke else "full_l2",
            "seed_base": SEED_BASE, "elapsed_s": round(time.time() - t_start, 2),
            "gates": gates,
            "verdicts": {"GATES_OK": False, "P1_R1": False, "P1_R2": False, "P1_R3": False, "P2_R4": False, "PASS_PRIMARY": False},
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(fail_summary, f, indent=2)
        print("FATAL: Startup gates failed; aborting immediately.", flush=True)
        sys.exit(2)

    if args.smoke:
        n_cal_r1, n_ver_r1, n_h1_r1 = 15, 15, 15
        n_cal_r2, n_ver_r2, n_h1_r2 = 15, 15, 15
        n_null_s = 10
        n_fixed_crb = 12
        n_cal_r3a, n_ver_r3a, n_h1_r3a = 15, 15, 15
        n_cal_r3b, n_ver_r3b, n_h1_r3b = 8, 8, 8
        n_bler_fr = 15
        bler_snrs = [10, 12, 14, 16, 18, 20, 22]
        n_mc_r4 = 100
        n_ofdm_cal, n_ofdm_h1 = 10, 10
        n_wood = 6
    else:
        n_cal_r1, n_ver_r1, n_h1_r1 = 150, 150, 120
        n_cal_r2, n_ver_r2, n_h1_r2 = 150, 150, 120
        n_null_s = 90
        n_fixed_crb = 60
        n_cal_r3a, n_ver_r3a, n_h1_r3a = 120, 120, 100
        n_cal_r3b, n_ver_r3b, n_h1_r3b = 60, 60, 50
        n_bler_fr = 120
        bler_snrs = [10, 12, 14, 16, 18, 20, 22]
        n_mc_r4 = 400
        n_ofdm_cal, n_ofdm_h1 = 80, 60
        n_wood = 30

    arms_main = ["Ma_SeqMF", "Luo_GESBL", "NOMP_DirPort", "A_only_NullPilot",
                 "B_only_NoNullspace", "B_only_NOMP_LS_Diag", "B_only_TikhonovDet_Diag", "Ours_GrassNull"]
    arms_r3a = ["Luo_GESBL", "NOMP_DirPort", "Ours_GrassNull"]
    fwer_primary_arms = len(arms_main) + len(arms_main) + len(arms_r3a)  # 8 + 8 + 3 = 19 arm-regime checks

    # R1
    r1_cal = run_pool(_worker_nr1_frame, [(SEED_BASE + 100001 + i, "R1", 1, False, 0.10, 25.0, "gauss", arms_main, 7, False) for i in range(n_cal_r1)])
    r1_ver = run_pool(_worker_nr1_frame, [(SEED_BASE + 110001 + i, "R1", 1, False, 0.10, 25.0, "gauss", arms_main, 7, False) for i in range(n_ver_r1)])
    r1_h1 = run_pool(_worker_nr1_frame, [(SEED_BASE + 120001 + i, "R1", 1, True, 0.10, 25.0, "gauss", arms_main, 7, False) for i in range(n_h1_r1)])
    R1, _ = aggregate_regime(r1_cal, r1_ver, r1_h1, arms_main, pfa_nom=0.02, fwer_arms=fwer_primary_arms)
    print(f"[R1] Ours={R1['arms']['Ours_GrassNull']['hit_pd']*100:.1f}% (Pfa={R1['arms']['Ours_GrassNull']['pfa_verify']*100:.1f}%) | "
          f"Ma={R1['arms']['Ma_SeqMF']['hit_pd']*100:.1f}% | Luo={R1['arms']['Luo_GESBL']['hit_pd']*100:.1f}% | "
          f"NOMP={R1['arms']['NOMP_DirPort']['hit_pd']*100:.1f}% | A={R1['arms']['A_only_NullPilot']['hit_pd']*100:.1f}% | "
          f"B={R1['arms']['B_only_NoNullspace']['hit_pd']*100:.1f}% | B_Tikh={R1['arms']['B_only_TikhonovDet_Diag']['hit_pd']*100:.1f}%", flush=True)

    # R2
    r2_cal = run_pool(_worker_nr1_frame, [(SEED_BASE + 200001 + i, "R2", 2, False, 0.125, 25.0, "gauss", arms_main, 7, False) for i in range(n_cal_r2)])
    r2_ver = run_pool(_worker_nr1_frame, [(SEED_BASE + 210001 + i, "R2", 2, False, 0.125, 25.0, "gauss", arms_main, 7, False) for i in range(n_ver_r2)])
    r2_h1 = run_pool(_worker_nr1_frame, [(SEED_BASE + 220001 + i, "R2", 2, True, 0.125, 25.0, "gauss", arms_main, 7, True) for i in range(n_h1_r2)])
    R2, thr_r2 = aggregate_regime(r2_cal, r2_ver, r2_h1, arms_main, pfa_nom=0.02, fwer_arms=fwer_primary_arms)

    fg_res = run_pool(_worker_fixed_crb_trial, [SEED_BASE + 230001 + i for i in range(n_fixed_crb)])
    cfg_fg = _make_rx_cfg(N=128, G=24, two_Nc1=7)
    fg_crb = ma_exact_crb_and_mcrb1(
        128, cfg_fg["A"], cfg_fg["Ah"], cfg_fg["xp"], cfg_fg["data_mask"], 1.0, 10.0 ** (-2.5),
        [0.8 * np.exp(1j * 0.5), 0.6 * np.exp(1j * 2.1), 0.125 * np.exp(1j * 1.1)],
        [1.2, 3.1, 7.4], [0.1, -0.15, 1.4], Ah_f=cfg_fg["Ah_f"]
    )
    fg_hits = [r for r in fg_res if r["hit"]]
    R2["fixed_geometry_crb_check"] = {
        "n_trials": n_fixed_crb, "n_detected": len(fg_hits), "miss_rate": float(1.0 - len(fg_hits) / n_fixed_crb),
        "ours_h_mag_bias": float(np.mean([r["dh_mag"] for r in fg_hits])) if fg_hits else None,
        "ours_h_mag_var": float(np.var([r["dh_mag"] for r in fg_hits], ddof=1)) if len(fg_hits) > 1 else None,
        "ours_h_mag_rmse": float(np.sqrt(np.mean([r["dh_mag"] ** 2 for r in fg_hits]))) if fg_hits else None,
        "ours_l_rmse": float(np.sqrt(np.mean([r["dl"] ** 2 for r in fg_hits]))) if fg_hits else None,
        "ours_nu_rmse": float(np.sqrt(np.mean([r["dnu"] ** 2 for r in fg_hits]))) if fg_hits else None,
        "ma_exact_crb_and_mcrb1": fg_crb,
    }
    print(f"[R2] Ours={R2['arms']['Ours_GrassNull']['hit_pd']*100:.1f}% (Pfa={R2['arms']['Ours_GrassNull']['pfa_verify']*100:.1f}%) | "
          f"Ma={R2['arms']['Ma_SeqMF']['hit_pd']*100:.1f}% | Luo={R2['arms']['Luo_GESBL']['hit_pd']*100:.1f}% | "
          f"NOMP={R2['arms']['NOMP_DirPort']['hit_pd']*100:.1f}% | A={R2['arms']['A_only_NullPilot']['hit_pd']*100:.1f}% | "
          f"B={R2['arms']['B_only_NoNullspace']['hit_pd']*100:.1f}% | B_LS={R2['arms']['B_only_NOMP_LS_Diag']['hit_pd']*100:.1f}% | "
          f"B_Tikh={R2['arms']['B_only_TikhonovDet_Diag']['hit_pd']*100:.1f}%", flush=True)

    # R0: Stratified R_null + 3x4 blind order confusion matrix
    arms_r0 = ["Ma_SeqMF", "NOMP_DirPort", "Ours_GrassNull"]
    a_r2_bb, b_r2_bb = exact_order_stat_params(n_cal_r2, 0.02)
    k_lo_r0, k_hi_r0 = exact_betabinom_interval(n_null_s, a_r2_bb, b_r2_bb, alpha_each=0.05 / float(len(arms_r0)))
    r0_strata = {}
    conf_mat = [[0, 0, 0, 0] for _ in range(3)]
    for pc_t in (0, 1, 2):
        res_s = run_pool(_worker_nr1_frame, [(SEED_BASE + 50001 + pc_t * 10000 + i, "R0", pc_t, False, 0.125, 25.0, "gauss", arms_r0, 7, False) for i in range(n_null_s)])
        st_entry = {"n_frames": n_null_s, "arms": {}}
        for arm in arms_r0:
            tau = thr_r2[arm]
            stats = np.array([r["arms"][arm]["stat"] for r in res_s], dtype=float)
            k_fa = int(np.sum(stats > tau))
            ci = wilson_ci(k_fa, n_null_s)
            st_entry["arms"][arm] = {
                "k_fa_at_r2_tau": k_fa,
                "pfa_at_r2_tau": float(k_fa / n_null_s),
                "pfa_ci95": ci,
                "pfa_bb_fwer3_bounds_k": [k_lo_r0, k_hi_r0],
                "pfa_bb_pass": bool(k_lo_r0 <= k_fa <= k_hi_r0),
            }
        for r in res_s:
            ph = min(int(r["arms"]["Ours_GrassNull"]["pc_hat"]), 3)
            conf_mat[pc_t][ph] += 1
        r0_strata[f"Pc={pc_t}"] = st_entry
    tot_ord = sum(sum(row) for row in conf_mat)
    exact_ord = sum(conf_mat[i][i] for i in range(3))
    R0 = {
        "strata_using_r2_tau": r0_strata,
        "blind_order_confusion_matrix_rows_true012_cols_est0123": conf_mat,
        "blind_order_exact_acc": float(exact_ord / max(tot_ord, 1)),
        "blind_order_per_class_acc": {f"Pc={i}": float(conf_mat[i][i] / max(sum(conf_mat[i]), 1)) for i in range(3)},
    }
    print(f"[R0] Blind order exact acc={R0['blind_order_exact_acc']*100:.1f}% | conf={conf_mat}", flush=True)

    # R3a: Cooperative 64-QAM (Nr=1, 24 dB)
    r3a_cal = run_pool(_worker_nr1_frame, [(SEED_BASE + 300001 + i, "R3a", 2, False, 0.125, 24.0, "64qam", arms_r3a, 7, False) for i in range(n_cal_r3a)])
    r3a_ver = run_pool(_worker_nr1_frame, [(SEED_BASE + 310001 + i, "R3a", 2, False, 0.125, 24.0, "64qam", arms_r3a, 7, False) for i in range(n_ver_r3a)])
    r3a_h1 = run_pool(_worker_nr1_frame, [(SEED_BASE + 320001 + i, "R3a", 2, True, 0.125, 24.0, "64qam", arms_r3a, 7, False) for i in range(n_h1_r3a)])
    R3a, _ = aggregate_regime(r3a_cal, r3a_ver, r3a_h1, arms_r3a, pfa_nom=0.02, fwer_arms=fwer_primary_arms)
    print(f"[R3a Nr=1 64QAM 24dB] Ours={R3a['arms']['Ours_GrassNull']['hit_pd']*100:.1f}% "
          f"(Pfa={R3a['arms']['Ours_GrassNull']['pfa_verify']*100:.1f}%) | "
          f"Luo={R3a['arms']['Luo_GESBL']['hit_pd']*100:.1f}% | NOMP={R3a['arms']['NOMP_DirPort']['hit_pd']*100:.1f}%", flush=True)

    # R3b: Multi-Antenna Nr=8 (G=24)
    R3b = {}
    for sub_idx, (sub_name, p_mode, snr_m) in enumerate([("Nr8_NonCoopGauss_16dB", "gauss", 16.0), ("Nr8_Coop64QAM_12dB", "64qam", 12.0)]):
        base_s = SEED_BASE + 350001 + sub_idx * 20000
        c_m = run_pool(_worker_nr8_frame, [(base_s + i, False, snr_m, p_mode) for i in range(n_cal_r3b)])
        v_m = run_pool(_worker_nr8_frame, [(base_s + 5000 + i, False, snr_m, p_mode) for i in range(n_ver_r3b)])
        h_m = run_pool(_worker_nr8_frame, [(base_s + 10000 + i, True, snr_m, p_mode) for i in range(n_h1_r3b)])
        agg_m, _ = aggregate_regime(c_m, v_m, h_m, ["Luo_GESBL_Nr8", "Ours_GrassNull_Nr8"], pfa_nom=0.02, primary_arm="Ours_GrassNull_Nr8", fwer_arms=4)
        R3b[sub_name] = agg_m
        print(f"[R3b {sub_name}] Ours_Nr8={agg_m['arms']['Ours_GrassNull_Nr8']['hit_pd']*100:.1f}% | "
              f"Luo_Nr8={agg_m['arms']['Luo_GESBL_Nr8']['hit_pd']*100:.1f}%", flush=True)

    # R3c: Equal-Net-Throughput Coded BLER & Sensing (exact 206 net info bits / 138 samples, realized E_tx==138.0 incl CPP!)
    bler_tasks = [(SEED_BASE + 500001 + si * 1000 + f, float(snr)) for si, snr in enumerate(bler_snrs) for f in range(n_bler_fr)]
    bler_raw = run_pool(_worker_equal_throughput_frame, bler_tasks)
    bler_curve = []
    for snr in bler_snrs:
        rows = [r for r in bler_raw if r["snr_db"] == float(snr)]
        bler_curve.append({
            "snr_db": float(snr), "n_frames": len(rows),
            "mean_etx_ours": float(np.mean([r["ours_etx"] for r in rows])),
            "mean_etx_g76_ep24": float(np.mean([r["g76_ep24_etx"] for r in rows])),
            "mean_etx_g76_ep76": float(np.mean([r["g76_ep76_etx"] for r in rows])),
            "ours_g24_16qam_r12_bler_blind": float(np.mean([r["ours_err_blind"] for r in rows])),
            "ours_g24_16qam_r12_bler_oracle": float(np.mean([r["ours_err_oracle"] for r in rows])),
            "ours_g24_raw_hit": float(np.mean([r["ours_hit"] for r in rows])),
            "std_g76_64qam_r23_ep24_bler_blind": float(np.mean([r["g76_ep24_err_blind"] for r in rows])),
            "std_g76_64qam_r23_ep24_bler_oracle": float(np.mean([r["g76_ep24_err_oracle"] for r in rows])),
            "std_g76_ep24_raw_hit": float(np.mean([r["g76_ep24_hit"] for r in rows])),
            "std_g76_64qam_r23_ep76_bler_blind": float(np.mean([r["g76_ep76_err_blind"] for r in rows])),
            "std_g76_64qam_r23_ep76_bler_oracle": float(np.mean([r["g76_ep76_err_oracle"] for r in rows])),
            "std_g76_ep76_raw_hit": float(np.mean([r["g76_ep76_hit"] for r in rows])),
        })

    def _summarize_bler_crossings(target):
        o_b = strict_interp_snr_at_bler(bler_curve, "ours_g24_16qam_r12_bler_blind", target)
        g24_b = strict_interp_snr_at_bler(bler_curve, "std_g76_64qam_r23_ep24_bler_blind", target)
        g76_b = strict_interp_snr_at_bler(bler_curve, "std_g76_64qam_r23_ep76_bler_blind", target)
        o_or = strict_interp_snr_at_bler(bler_curve, "ours_g24_16qam_r12_bler_oracle", target)
        g24_or = strict_interp_snr_at_bler(bler_curve, "std_g76_64qam_r23_ep24_bler_oracle", target)
        g76_or = strict_interp_snr_at_bler(bler_curve, "std_g76_64qam_r23_ep76_bler_oracle", target)
        return {
            "target_bler": target,
            "blind_ce": {
                "snr_ours_db": o_b, "snr_g76_ep24_db": g24_b, "snr_g76_ep76_db": g76_b,
                "gain_vs_g76_ep24_db": (float(g24_b - o_b) if (o_b is not None and g24_b is not None) else None),
                "gain_vs_g76_ep76_db": (float(g76_b - o_b) if (o_b is not None and g76_b is not None) else None),
            },
            "oracle_ce": {
                "snr_ours_db": o_or, "snr_g76_ep24_db": g24_or, "snr_g76_ep76_db": g76_or,
                "gain_vs_g76_ep24_db": (float(g24_or - o_or) if (o_or is not None and g24_or is not None) else None),
                "gain_vs_g76_ep76_db": (float(g76_or - o_or) if (o_or is not None and g76_or is not None) else None),
            },
        }

    cross_10 = _summarize_bler_crossings(0.10)
    cross_05 = _summarize_bler_crossings(0.05)
    R3c = {
        "protocol": {
            "N": 128, "L_cpp": 10, "total_samples": 138,
            "expected_E_tx_including_cpp": 138.0,
            "energy_note": "Exact expected E[||P_cpp A^H (xp+xd)||_2^2] == 138.0 via PHY bit-scrambling; per-SNR realized means logged in curve[*].mean_etx_*",
            "net_info_bits_per_frame": 206, "tail_bits": 2, "net_spectral_eff_bps_hz": 206.0 / 138.0,
            "fec": "(7,5)_8 K=3 terminated conv code + soft-LLR Viterbi + symmetric 1-pass DF CE polish",
            "geometry": "Zero-coupling Bemani full-guard (l_c=[1,3], l_t=5, ||H[p_win, D_76]||_F=4.45e-13)",
            "ours": "G=24 (104 data bins), Gray 16-QAM, rate-1/2 (416 coded bits), Ep=24, Ed=104",
            "std_ep24": "G=76 (52 data bins), Gray 64-QAM, punctured rate-2/3 (312 coded bits), Ep=24, Ed=104",
            "std_ep76": "G=76 (52 data bins), Gray 64-QAM, punctured rate-2/3 (312 coded bits), Ep=76, Ed=52",
        },
        "curve": bler_curve,
        "crossing_bler10": cross_10,
        "crossing_bler05": cross_05,
    }
    print(f"[R3c Equal-206b] Blind@10%: gain vs Ep24={cross_10['blind_ce']['gain_vs_g76_ep24_db']}, vs Ep76={cross_10['blind_ce']['gain_vs_g76_ep76_db']} | "
          f"Oracle@5%: gain vs Ep24={cross_05['oracle_ce']['gain_vs_g76_ep24_db']}, vs Ep76={cross_05['oracle_ce']['gain_vs_g76_ep76_db']}", flush=True)

    # R4
    R4 = run_r4_analytical_scnr_bound(SEED_BASE, n_mc=n_mc_r4)
    print(f"[R4 Analytical SCNR_null] max_err={R4['max_err_db']:.3f} dB", flush=True)

    # SCOPE_READOUTS
    of_cal = run_pool(_worker_nr1_frame, [(SEED_BASE + 600001 + i, "OFDM", 2, False, 0.125, 25.0, "gauss", ["Ours_GrassNull"], 0, False) for i in range(n_ofdm_cal)])
    of_h1 = run_pool(_worker_nr1_frame, [(SEED_BASE + 610001 + i, "OFDM", 2, True, 0.125, 25.0, "gauss", ["Ours_GrassNull"], 0, False) for i in range(n_ofdm_h1)])
    of_tau, _, _ = exact_order_stat_threshold([r["arms"]["Ours_GrassNull"]["stat"] for r in of_cal], 0.02)
    of_pd = float(np.mean([(r["arms"]["Ours_GrassNull"]["stat"] > of_tau) and r["arms"]["Ours_GrassNull"]["hit"] for r in of_h1]))

    wd_res = run_pool(_worker_woodbury_diag, [SEED_BASE + 700001 + i for i in range(n_wood)])
    wd_ok = [r for r in wd_res if r["hit"]]
    SCOPE_READOUTS = {
        "OFDM_c1_eq_0_contiguous_R2": {
            "n_cal": n_ofdm_cal, "n_h1": n_ofdm_h1, "hit_pd_at_2pct_pfa": of_pd,
            "raw_hit_rate": float(np.mean([r["arms"]["Ours_GrassNull"]["hit"] for r in of_h1])),
        },
        "Woodbury_Eq9_OracleSig2_vs_Blind_Jnull": {
            "n_frames": n_wood, "n_detected": len(wd_ok),
            "jnull_l_rmse": float(np.sqrt(np.mean([r["jnull_dl"] ** 2 for r in wd_ok]))) if wd_ok else None,
            "wood_l_rmse": float(np.sqrt(np.mean([r["wood_dl"] ** 2 for r in wd_ok]))) if wd_ok else None,
            "jnull_nu_rmse": float(np.sqrt(np.mean([r["jnull_dnu"] ** 2 for r in wd_ok]))) if wd_ok else None,
            "wood_nu_rmse": float(np.sqrt(np.mean([r["wood_dnu"] ** 2 for r in wd_ok]))) if wd_ok else None,
            "jnull_h_rmse": float(np.sqrt(np.mean([r["jnull_dh"] ** 2 for r in wd_ok]))) if wd_ok else None,
            "wood_h_rmse": float(np.sqrt(np.mean([r["wood_dh"] ** 2 for r in wd_ok]))) if wd_ok else None,
            "mean_time_jnull_s": float(np.mean([r["t_jnull"] for r in wd_res])),
            "mean_time_woodbury_s": float(np.mean([r["t_wood"] for r in wd_res])),
        },
        "contig_comb_2x2_data_gain": R4["contig_comb_2x2_diag"],
    }

    # Pre-registered Verdicts (STRICTLY matching PREDICTIONS_m_r11_m04.md!)
    r1_ours = R1["arms"]["Ours_GrassNull"]
    r2_ours = R2["arms"]["Ours_GrassNull"]
    r3a_ours = R3a["arms"]["Ours_GrassNull"]

    # Exact Beta-Binomial predictive interval P_fa gate for EVERY arm uniformly across R1 (8 arms), R2 (8 arms), R3a (3 arms) = 19 checks
    pfa_ok = bool(
        all(arm_d["pfa_bb_pass"] for reg in (R1, R2, R3a) for arm_d in reg["arms"].values())
        and R0["blind_order_exact_acc"] >= 0.85
    )
    GATES_ALL = bool(gates["GATES_OK"] and pfa_ok)

    P1_R1 = bool(
        r1_ours["hit_pd"] >= 0.85
        and R1["arms"]["A_only_NullPilot"]["hit_pd"] < 0.80
        and R1["arms"]["B_only_NoNullspace"]["hit_pd"] < 0.80
        and all(
            R1["paired_diff_vs_ours"][k]["diff_pd"] >= 0.50 and R1["paired_diff_vs_ours"][k]["ci95"][0] > 0.0
            for k in ("Ma_SeqMF", "Luo_GESBL", "NOMP_DirPort", "A_only_NullPilot", "B_only_NoNullspace")
        )
    )

    crb_r2 = R2["matched_geometry_bounds"]
    P1_R2 = bool(
        r2_ours["hit_pd"] >= 0.75
        and R2["arms"]["A_only_NullPilot"]["hit_pd"] < 0.80
        and R2["arms"]["B_only_NoNullspace"]["hit_pd"] < 0.80
        and all(
            R2["paired_diff_vs_ours"][k]["diff_pd"] >= 0.45 and R2["paired_diff_vs_ours"][k]["ci95"][0] > 0.0
            for k in ("Ma_SeqMF", "Luo_GESBL", "NOMP_DirPort", "A_only_NullPilot", "B_only_NoNullspace")
        )
        and (r2_ours["rmse_l"] is not None and r2_ours["rmse_l"] <= 2.5 * crb_r2["ma_crb_l_rmse"])
        and (r2_ours["rmse_nu"] is not None and r2_ours["rmse_nu"] <= 2.5 * crb_r2["ma_crb_nu_rmse"])
        and (r2_ours["h_mag_bias"] is not None and abs(r2_ours["h_mag_bias"]) < 0.02)
    )

    gb24 = cross_10["blind_ce"]["gain_vs_g76_ep24_db"]
    gb76 = cross_10["blind_ce"]["gain_vs_g76_ep76_db"]
    go24 = cross_05["oracle_ce"]["gain_vs_g76_ep24_db"]
    go76 = cross_05["oracle_ce"]["gain_vs_g76_ep76_db"]
    P1_R3 = bool(
        r3a_ours["hit_pd"] >= 0.60
        and R3a["paired_diff_vs_ours"]["Luo_GESBL"]["diff_pd"] >= 0.35
        and R3a["paired_diff_vs_ours"]["Luo_GESBL"]["ci95"][0] > 0.0
        and R3a["paired_diff_vs_ours"]["NOMP_DirPort"]["diff_pd"] >= 0.35
        and R3a["paired_diff_vs_ours"]["NOMP_DirPort"]["ci95"][0] > 0.0
        and (gb24 is not None and gb24 >= 1.5)
        and (gb76 is not None and gb76 >= 2.5)
        and (go24 is not None and go24 >= 3.0)
        and (go76 is not None and go76 >= 5.0)
    )

    P2_R4 = bool(R4["max_err_db"] <= 0.50)

    PASS_PRIMARY = bool(GATES_ALL and P1_R1 and P1_R2 and P1_R3 and P2_R4)

    summary = {
        "card_id": "I-20261125-m04",
        "mode": "smoke" if args.smoke else "full_l2",
        "seed_base": SEED_BASE,
        "workers": n_workers,
        "elapsed_s": round(time.time() - t_start, 2),
        "gates": gates,
        "R0_NullAndOrder": R0,
        "R1_1PathClut_Neg20dB": R1,
        "R2_2PathFading_Neg18dB": R2,
        "R3a_Coop64QAM_Nr1_24dB": R3a,
        "R3b_MultiAnt_Nr8": R3b,
        "R3c_EqualNetThroughput_BLER": R3c,
        "R4_Analytical_SCNR_Bound": R4,
        "SCOPE_READOUTS": SCOPE_READOUTS,
        "verdicts": {
            "GATES_OK": GATES_ALL,
            "P1_R1": P1_R1,
            "P1_R2": P1_R2,
            "P1_R3": P1_R3,
            "P2_R4": P2_R4,
            "PASS_PRIMARY": PASS_PRIMARY,
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n=== VERDICTS ({summary['mode']}, seed_base={SEED_BASE}, {summary['elapsed_s']:.1f}s) ===", flush=True)
    print(json.dumps(summary["verdicts"], indent=2), flush=True)


if __name__ == "__main__":
    main()
