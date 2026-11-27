#!/usr/bin/env python3
"""
Updated Independent Dev-Set Sizing & Sol-11/12 Blocking Verification for I-20261126-m04.
Uses DEV seeds ONLY (11001..19999; NEVER reused in smoke 2124000000+ or formal 2034000000+).

Runs the EXACT frozen L2 receivers and regimes:
  - Exact 765-bit equal net payload (127*4 + 127*2 + 1*3 = 765 bits = 3.000000 bpcu!)
  - Symmetric per-subcarrier unbiased LMMSE gain correction in G5 Comm BER
  - Exact scipy.optimize.nnls in Rival_TDCov + 32-scene high-SNR static convergence check
  - Pure single-factor ablations:
      (a) Abl_DiagOnly (lag-1 OFF)
      (b) Abl_NoMask (EXACT same normalized symbols x_norm, ONLY removing sqrt(d) power scaling!)
      (c) Abl_HomoBanded (EXACT same lag-0 + lag-1 banded receiver, ONLY replacing 1/mu_k^2 weighting with homoscedastic LS!)
  - Exact Newcombe (1998) Method 10 paired CI + exact D_0.8 paired t-CI for bidirectional < 80% coupling
  - Exact frozen primary regimes: Reg1 (P=2: 0, -13.5 dB) & Reg2 (P=3: 0, -3, -11.5 dB), M=128, n_dev=80.
"""

import math
import time
import numpy as np
from scipy.fft import fft, ifft
from scipy.optimize import minimize, nnls
from scipy.stats import t as student_t
import sys

sys.path.insert(0, "/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2")
import l2_m_r13_m04_blind_cov_afdm_isac as L2


def build_exact_765bit_system(order: int = 8, Q: int = 12, delta: float = 2.0 / 3.0) -> dict:
    """
    Build N = 255 DAFT power mask with EXACT equal net payload = 765 bits/block (3.000000 bpcu)
    and EXACT uniform d_min^2 = 2/3 across all 255 subcarriers:
      - 127 high-power bins (+1): d = 1 + 2/3 = 5/3  -> Gray 16-QAM (4 bits, d_min^2 = 0.4 * 5/3 = 2/3)
      - 127 low-power bins  (-1): d = 1 - 2/3 = 1/3  -> Gray QPSK   (2 bits, d_min^2 = 2.0 * 1/3 = 2/3)
      -   1 neutral bin (last +1): d = 1.0           -> Gray 8-QAM  (3 bits, d_min^2 = 2/3)
    Exact mean(d) = (127*(5/3) + 127*(1/3) + 1*1) / 255 = 255/255 = 1.000000000000!
    """
    N = (1 << order) - 1
    c1 = Q / (2.0 * N)
    c2 = 1.0 / (2.0 * np.pi * N)
    b = L2.generate_m_sequence(order)
    pos_idx = np.where(b > 0)[0]
    mid_idx = int(pos_idx[-1])
    d = np.where(b > 0, 1.0 + delta, 1.0 - delta)
    d[mid_idx] = 1.0
    assert abs(float(np.mean(d)) - 1.0) < 1e-12
    D_fft = fft(d)
    d0 = d - np.mean(d)
    D0_conj = np.conj(fft(d0))
    k_idx = np.arange(N)
    kp1 = (k_idx + 1) % N
    dechirp = np.exp(1j * 2.0 * np.pi * c2 * (k_idx ** 2 - kp1 ** 2))
    n_idx = np.arange(N, dtype=np.float64)
    lam1 = np.exp(-1j * 2.0 * np.pi * c1 * (n_idx ** 2))
    C_d = ifft(d)
    return {
        "order": order, "N": N, "Q": Q, "c1": c1, "c2": c2, "delta": delta,
        "d": d, "mid_idx": mid_idx, "D_fft": D_fft, "D0_conj": D0_conj,
        "k_idx": k_idx, "kp1": kp1, "dechirp": dechirp, "lam1": lam1, "C_d": C_d,
    }


def sample_765bit_norm(rng: np.random.Generator, cfg: dict, M: int) -> np.ndarray:
    """Unit-variance normalized constellation matrix x_norm (N x M) with exact 765 bits/symbol."""
    d = cfg["d"]
    N = cfg["N"]
    hi = d > 1.01
    lo = d < 0.99
    mid = (~hi) & (~lo)
    X_norm = np.empty((N, M), dtype=np.complex128)
    X_norm[hi, :] = L2.QAM16_PTS[rng.integers(0, 16, size=(int(np.sum(hi)), M))]
    X_norm[lo, :] = L2.QPSK_PTS[rng.integers(0, 4, size=(int(np.sum(lo)), M))]
    X_norm[mid, :] = L2.QAM8_PTS[rng.integers(0, 8, size=(int(np.sum(mid)), M))]
    return X_norm


def estimate_banded_v2(
    Y: np.ndarray,
    sys_cfg: dict,
    Q_in: int,
    ell_max: int,
    nu_max: float,
    tau_q: float,
    P_max: int = 5,
    use_lag1: bool = True,
    homoscedastic: bool = False,
    return_top_stat: bool = False,
    tie_rng: np.random.Generator | None = None,
):
    N, M = Y.shape
    D_fft = sys_cfg["D_fft"]
    D0_conj = sys_cfg["D0_conj"]
    k_idx = sys_cfg["k_idx"]
    kp1 = sys_cfg["kp1"]
    dechirp = sys_cfg["dechirp"]

    rms = float(np.sqrt(np.mean(np.abs(Y) ** 2)))
    if rms < 1e-15:
        return [], 0.0
    Yn = Y / rms

    P_mat = np.abs(Yn) ** 2
    p_hat = np.mean(P_mat, axis=1)
    p_bar = float(np.mean(p_hat))
    v0_k = np.var(P_mat, axis=1, ddof=1)
    phi0 = max(float(np.median(v0_k / np.maximum(p_hat ** 2, 1e-12))), 0.15)
    v0_hom = max(float(np.median(v0_k)), 1e-12)

    R1_mat = (Yn[k_idx, :] * np.conj(Yn[kp1, :])) * dechirp[:, None]
    r1_hat = np.mean(R1_mat, axis=1)
    v1_k = np.mean(np.abs(R1_mat - r1_hat[:, None]) ** 2, axis=1) * (M / max(M - 1, 1))
    phi1 = max(float(np.median(v1_k / np.maximum(p_hat[k_idx] * p_hat[kp1], 1e-12))), 0.15)
    v1_hom = max(float(np.median(v1_k)), 1e-12)
    denom_r1 = np.full(N, p_bar ** 2, dtype=np.float64) if homoscedastic else np.maximum(p_hat[k_idx] * p_hat[kp1], 1e-12)

    def is_valid_u(u_val: float) -> bool:
        if Q_in > 0:
            ec = min(range(ell_max + 1), key=lambda e: abs(((u_val + Q_in * e + N / 2.0) % N) - N / 2.0))
            nc = ((u_val + Q_in * ec + N / 2.0) % N) - N / 2.0
            return abs(nc) <= nu_max
        nc = ((u_val + N / 2.0) % N) - N / 2.0
        return abs(nc) <= nu_max

    def u_bounds(u_val: float) -> tuple[float, float]:
        if Q_in > 0:
            ec = min(range(ell_max + 1), key=lambda e: abs(((u_val + Q_in * e + N / 2.0) % N) - N / 2.0))
            c_wrap = (-Q_in * ec) % N
            diff = ((u_val - c_wrap + N / 2.0) % N) - N / 2.0
            c_unw = u_val - diff
        else:
            diff = ((u_val + N / 2.0) % N) - N / 2.0
            c_unw = u_val - diff
        lo = max(u_val - 1.2, c_unw - nu_max)
        hi = min(u_val + 1.2, c_unw + nu_max)
        return (min(lo, u_val), max(hi, u_val))

    valid_int = np.array(
        [is_valid_u(float(k)) or is_valid_u(float(k) + 0.4) or is_valid_u(float(k) - 0.4) for k in range(N)],
        dtype=bool,
    )

    def eval_2nll(us, gs, s2):
        mu = np.full(N, s2, dtype=np.float64)
        c1_pred = np.zeros(N, dtype=np.complex128)
        for uj, gj in zip(us, gs):
            t0, t1 = L2.lag_templates(D_fft, N, uj)
            mu += gj * t0
            c1_pred += gj * t1
        if homoscedastic:
            val = (M / v0_hom) * float(np.sum((p_hat - mu) ** 2))
            if use_lag1:
                val += (2.0 * M / v1_hom) * float(np.sum(np.abs(r1_hat - c1_pred) ** 2))
        else:
            mu_s = np.maximum(mu, 1e-12)
            val = (2.0 * M / phi0) * float(np.sum(np.log(mu_s) + p_hat / mu_s))
            if use_lag1:
                val += (2.0 * M / phi1) * float(np.sum(np.abs(r1_hat - c1_pred) ** 2 / denom_r1))
        return val

    def fit_w(Us):
        Pp = len(Us)
        Tm = np.ones((N, Pp + 1), dtype=np.float64)
        for j, u in enumerate(Us):
            t0, _ = L2.lag_templates(D_fft, N, u)
            Tm[:, j] = np.maximum(t0, 1e-12)
        if homoscedastic:
            th, _ = nnls(Tm, p_hat)
            th = np.maximum(th, 1e-6)
            return th[:-1], float(th[-1])
        th = np.full(Pp + 1, p_bar / (Pp + 1), dtype=np.float64)
        for _ in range(30):
            mu = Tm @ th
            inv_mu = 1.0 / np.maximum(mu, 1e-12)
            th *= np.sqrt(np.maximum(Tm.T @ (p_hat * inv_mu ** 2), 1e-18) / np.maximum(Tm.T @ inv_mu, 1e-18))
        return th[:-1], float(th[-1])

    def refine_joint(U_init, g_init, s2_init):
        Pp = len(U_init)
        w1 = np.full(N, 2.0 * M / v1_hom) if homoscedastic else (2.0 * M / phi1) / denom_r1
        c0 = (M / v0_hom) if homoscedastic else (2.0 * M / phi0)

        def obj_and_grad(x):
            us = x[:Pp]
            gs = np.exp(np.clip(x[Pp:2 * Pp], -14.0, 10.0))
            s2 = float(np.exp(np.clip(x[2 * Pp], -14.0, 10.0)))
            t0s = np.empty((N, Pp), dtype=np.float64)
            dt0s = np.empty((N, Pp), dtype=np.float64)
            t1s = np.empty((N, Pp), dtype=np.complex128)
            dt1s = np.empty((N, Pp), dtype=np.complex128)
            for j in range(Pp):
                t0s[:, j], t1s[:, j], dt0s[:, j], dt1s[:, j] = L2.lag_templates_and_grads(D_fft, N, us[j])
            mu = np.maximum(s2 + t0s @ gs, 1e-12)
            if homoscedastic:
                err0 = mu - p_hat
                val = c0 * float(np.sum(err0 ** 2))
                dL0 = 2.0 * c0 * err0
            else:
                inv_mu = 1.0 / mu
                dL0 = c0 * (inv_mu - p_hat * (inv_mu ** 2))
                val = c0 * float(np.sum(np.log(mu) + p_hat * inv_mu))
            grad = np.empty_like(x)
            for j in range(Pp):
                grad[j] = float(np.dot(dL0, gs[j] * dt0s[:, j]))
                grad[Pp + j] = float(np.dot(dL0, gs[j] * t0s[:, j]))
            grad[2 * Pp] = float(s2 * np.sum(dL0))
            if use_lag1:
                err1 = t1s @ gs - r1_hat
                val += float(np.sum(w1 * (np.abs(err1) ** 2)))
                w_err = 2.0 * w1 * err1
                for j in range(Pp):
                    grad[j] += float(np.real(np.vdot(w_err, gs[j] * dt1s[:, j])))
                    grad[Pp + j] += float(np.real(np.vdot(w_err, gs[j] * t1s[:, j])))
            return val, grad

        u_last = U_init[-1]
        u_mir = 2.0 * round(u_last) - u_last
        inits = [U_init]
        if abs(u_mir - u_last) > 0.02 and is_valid_u(u_mir % N):
            inits.append(U_init[:-1] + [u_mir])
        elif abs(u_mir - u_last) <= 0.02:
            inits = [U_init[:-1] + [round(u_last) + ds] for ds in (-0.15, 0.15) if is_valid_u((round(u_last) + ds) % N)] or [U_init]

        best = None
        for ui_try in inits:
            x0 = np.concatenate([np.array(ui_try), np.log(np.maximum(g_init, 1e-6)), [np.log(max(s2_init, 1e-6))]])
            bnds = [u_bounds(u) for u in ui_try] + [(-12.0, 8.0)] * (Pp + 1)
            r = minimize(obj_and_grad, x0, jac=True, method="L-BFGS-B", bounds=bnds, options={"maxiter": 40, "ftol": 1e-9})
            if best is None or r.fun < best.fun:
                best = r
        xf = best.x
        return (xf[:Pp] % N).tolist(), np.exp(np.clip(xf[Pp:2 * Pp], -14.0, 10.0)), float(np.exp(np.clip(xf[2 * Pp], -14.0, 10.0))), float(best.fun)

    s2_c = p_bar
    nll2_c = eval_2nll([], np.array([]), s2_c)
    mu_c = np.full(N, s2_c)
    c1_c = np.zeros(N, dtype=np.complex128)
    U_c, g_c = [], np.array([])
    first_stat = 0.0

    for step in range(P_max):
        if homoscedastic:
            w_res = (p_hat - mu_c)
            inv_mu_c = np.full(N, 1.0 / max(p_bar, 1e-12))
        else:
            inv_mu_c = 1.0 / np.maximum(mu_c, 1e-12)
            w_res = (p_hat - mu_c) * (inv_mu_c ** 2)
        w_res -= np.mean(w_res)
        sc_int = np.real(ifft(fft(w_res) * D0_conj))
        cands = np.where(valid_int)[0]
        for ua in U_c:
            cands = cands[np.abs(((cands - ua + N / 2.0) % N) - N / 2.0) > 1.2]
        if len(cands) == 0:
            break
        top_k = cands[np.argsort(sc_int[cands])[-min(6, len(cands)):]]
        best_u, best_sc = None, -1e30
        err1_c = r1_hat - c1_c
        for ui in top_k:
            for du in (-0.4, -0.15, 0.15, 0.4):
                uc = (ui + du) % N
                if not is_valid_u(uc):
                    continue
                t0, t1 = L2.lag_templates(D_fft, N, uc)
                t0z = t0 - np.mean(t0)
                if homoscedastic:
                    den0 = max(float(np.linalg.norm(t0z)), 1e-12)
                    z0 = float(np.dot(w_res, t0z)) / (den0 * np.sqrt(v0_hom / M))
                else:
                    den0 = max(float(np.linalg.norm(t0z * inv_mu_c)), 1e-12)
                    z0 = float(np.dot(w_res, t0z)) / (den0 * np.sqrt(phi0 / M))
                sc = z0
                if use_lag1:
                    if homoscedastic:
                        den1 = max(float(np.linalg.norm(t1)), 1e-12)
                        z1 = float(np.real(np.vdot(t1, err1_c))) / (den1 * np.sqrt(v1_hom / (2.0 * M)))
                    else:
                        den1 = max(float(np.linalg.norm(t1 / np.sqrt(denom_r1))), 1e-12)
                        z1 = float(np.real(np.vdot(t1 / denom_r1, err1_c))) / (den1 * np.sqrt(phi1 / (2.0 * M)))
                    sc = math.hypot(max(z0, 0.0), max(z1, 0.0)) if (z0 > 0 or z1 > 0) else z0
                if sc > best_sc:
                    best_sc, best_u = sc, uc
        if best_u is None or best_sc <= 0:
            break
        U_try = U_c + [best_u]
        g_try, s2_try = fit_w(U_try)
        U_ref, g_ref, s2_ref, nll2_ref = refine_joint(U_try, g_try, s2_try)
        stat = max(0.0, nll2_c - nll2_ref)
        if step == 0:
            first_stat = stat
        if return_top_stat:
            return [], first_stat
        if stat <= tau_q:
            break
        U_c, g_c, s2_c, nll2_c = U_ref, g_ref, s2_ref, nll2_ref
        mu_c = np.full(N, s2_c)
        c1_c = np.zeros(N, dtype=np.complex128)
        for uj, gj in zip(U_c, g_c):
            t0, t1 = L2.lag_templates(D_fft, N, uj)
            mu_c += gj * t0
            c1_c += gj * t1

    dets = []
    for uj, gj in zip(U_c, g_c):
        if Q_in > 0:
            ej = min(range(ell_max + 1), key=lambda e: abs(((uj + Q_in * e + N / 2.0) % N) - N / 2.0))
            nj = float(((uj + Q_in * ej + N / 2.0) % N) - N / 2.0)
        else:
            ej = int(tie_rng.integers(0, ell_max + 1)) if tie_rng is not None else 0
            nj = float(((uj + N / 2.0) % N) - N / 2.0)
        dets.append((ej, nj, float(gj * (rms ** 2))))
    return dets, first_stat


def estimate_td_cov_exact_nnls(
    R_time: np.ndarray,
    sys_cfg: dict,
    ell_max: int,
    nu_max: float,
    tau_td: float,
    P_max: int = 5,
    return_top_stat: bool = False,
):
    """Exact scipy.optimize.nnls solution for Sol's TD-Cov spectral NOMP."""
    N, M = R_time.shape
    Q = sys_cfg["Q"]
    lam1 = sys_cfg["lam1"]
    C_d = sys_cfg["C_d"]

    rms = float(np.sqrt(np.mean(np.abs(R_time) ** 2)))
    if rms < 1e-15:
        return [], 0.0
    Z = lam1[:, None] * (R_time / rms)

    N_fft = 1 << int(np.ceil(np.log2(2 * N)))
    Zf = fft(Z, n=N_fft, axis=0)
    ac_mat = ifft(np.abs(Zf) ** 2, axis=0)[:N, :]
    r_int = np.arange(1, N, dtype=int)
    r_idx = r_int.astype(np.float64)
    cnt = N - r_idx
    y_w_frames = ac_mat[r_int, :] / np.sqrt(cnt)[:, None]
    y_w = np.mean(y_w_frames, axis=1)
    y_real = np.concatenate([y_w.real, y_w.imag])
    var_r = np.mean(np.abs(y_w_frames - y_w[:, None]) ** 2, axis=1) / max(M - 1, 1)
    sigma2_emp = max(float(np.median(var_r)), 1e-15)
    a_scale = np.sqrt(cnt) * C_d[r_int]

    oversamp = 4
    n_grid = N * oversamp
    u_grid = np.arange(n_grid, dtype=np.float64) / oversamp
    valid_g = np.zeros(n_grid, dtype=bool)
    for ell in range(ell_max + 1):
        center = (-Q * ell) % N
        diff = ((u_grid - center + N / 2.0) % N) - N / 2.0
        valid_g |= (np.abs(diff) <= nu_max)

    def clamp_valid_u(u_val: float) -> float:
        ec = min(range(ell_max + 1), key=lambda e: abs(((u_val + Q * e + N / 2.0) % N) - N / 2.0))
        nc = ((u_val + Q * ec + N / 2.0) % N) - N / 2.0
        nc = float(np.clip(nc, -nu_max, nu_max))
        return (-Q * ec + nc) % N

    def atom(u):
        return a_scale * np.exp(1j * 2.0 * np.pi * u * r_idx / N)

    def fit_nnls_exact(U_list):
        A_m = np.column_stack([atom(u) for u in U_list])
        A_real = np.vstack([A_m.real, A_m.imag])
        g, _ = nnls(A_real, y_real)
        return g, A_m

    U_c = []
    g_c = np.array([])
    res = y_w.copy()
    rss_c = float(np.sum(np.abs(res) ** 2))
    first_stat = 0.0

    for step in range(P_max):
        z_pad = np.zeros(n_grid, dtype=np.complex128)
        z_pad[r_int] = np.conj(a_scale) * res
        spec = np.real(fft(z_pad))
        mask = valid_g.copy()
        for ua in U_c:
            mask &= (np.abs(((u_grid - ua + N / 2.0) % N) - N / 2.0) > 1.2)
        if not np.any(mask):
            break
        spec_m = np.where(mask, spec, -1e30)
        idx_best = int(np.argmax(spec_m))
        if spec_m[idx_best] <= 0:
            break
        u_new = float(u_grid[idx_best])

        U_try = U_c + [u_new]
        g_try, A_try = fit_nnls_exact(U_try)
        for _ in range(3):
            for j in range(len(U_try)):
                r_j = y_w - (A_try @ g_try - A_try[:, j] * g_try[j])
                u_j = U_try[j]
                for _ in range(5):
                    ph = np.exp(1j * 2.0 * np.pi * u_j * r_idx / N)
                    a = a_scale * ph
                    c1_d = 1j * 2.0 * np.pi * r_idx / N
                    da = a * c1_d
                    dda = da * c1_d
                    grad = float(np.real(np.vdot(da, r_j)))
                    hess = float(np.real(np.vdot(dda, r_j)))
                    if hess < -1e-12:
                        u_j = clamp_valid_u((u_j + float(np.clip(-grad / hess, -0.25, 0.25))) % N)
                    else:
                        break
                U_try[j] = u_j
            g_try, A_try = fit_nnls_exact(U_try)

        res_try = y_w - A_try @ g_try
        rss_try = float(np.sum(np.abs(res_try) ** 2))
        stat = max(0.0, 2.0 * (rss_c - rss_try) / sigma2_emp)
        if step == 0:
            first_stat = stat
        if return_top_stat:
            return [], first_stat
        if stat <= tau_td:
            break
        U_c, g_c, res, rss_c = U_try, g_try, res_try, rss_try

    dets = []
    for uj, gj in zip(U_c, g_c):
        ej = min(range(ell_max + 1), key=lambda e: abs(((uj + Q * e + N / 2.0) % N) - N / 2.0))
        nj = float(((uj + Q * ej + N / 2.0) % N) - N / 2.0)
        dets.append((ej, nj, float(gj * (rms ** 2))))
    return dets, first_stat


def newcombe_method10(a_hits: np.ndarray, b_hits: np.ndarray) -> dict:
    """Exact Newcombe (1998) Method 10 paired proportion CI."""
    n = len(a_hits)
    e = float(np.sum((a_hits == 1) & (b_hits == 1)))
    f = float(np.sum((a_hits == 1) & (b_hits == 0)))
    g = float(np.sum((a_hits == 0) & (b_hits == 1)))
    h = float(np.sum((a_hits == 0) & (b_hits == 0)))
    p1 = (e + f) / n
    p2 = (e + g) / n
    diff = p1 - p2
    w1 = L2.wilson_ci(int(e + f), n)
    w2 = L2.wilson_ci(int(e + g), n)
    den_phi = math.sqrt(max((e + f) * (g + h) * (e + g) * (f + h), 0.0))
    if den_phi > 1e-12:
        num = e * h - f * g
        phi = max(num - 0.5 * n, 0.0) / den_phi if num > 0 else num / den_phi
    else:
        phi = 0.0
    d1, u1 = p1 - w1["lo"], w1["hi"] - p1
    d2, u2 = p2 - w2["lo"], w2["hi"] - p2
    lo = diff - math.sqrt(max(0.0, d1 * d1 + u2 * u2 - 2.0 * phi * d1 * u2))
    hi = diff + math.sqrt(max(0.0, u1 * u1 + d2 * d2 - 2.0 * phi * u1 * d2))
    return {"diff": diff, "lo": lo, "hi": hi, "hw": 0.5 * (hi - lo)}


def paired_ratio_contrast_ci(ours_hits: np.ndarray, abl_hits: np.ndarray, factor: float = 0.80) -> dict:
    """Asymptotic paired Student-t_{n-1} 95% CI for D = factor * Y_ours - Y_abl > 0 <=> p_abl / p_ours < factor."""
    d_vec = factor * ours_hits.astype(np.float64) - abl_hits.astype(np.float64)
    n = len(d_vec)
    mean_d = float(np.mean(d_vec))
    se = float(np.std(d_vec, ddof=1) / math.sqrt(n))
    t_crit = float(student_t.ppf(0.975, df=n - 1))
    hw = t_crit * se
    return {"est": mean_d, "lo": mean_d - hw, "hi": mean_d + hw, "hw": hw, "ratio": float(np.mean(abl_hits) / max(np.mean(ours_hits), 1e-12))}


def main():
    t0 = time.perf_counter()
    cfg = build_exact_765bit_system(order=8, Q=12, delta=2.0 / 3.0)
    N, Q, c1, c2, d = cfg["N"], cfg["Q"], cfg["c1"], cfg["c2"], cfg["d"]
    ell_max, nu_max = 16, 4.5
    M_c = 128

    # 1. Exact 765-bit Unbiased-LMMSE Comm BER check (n_dev=100)
    print("=" * 84)
    print("[DEV 1] Exact 765-Bit Equal-Payload + Unbiased Per-Subcarrier LMMSE BER (n=100)")
    print("=" * 84)
    A = L2.afdm_daft_matrix(N, c1, c2)
    hi = d > 1.01; lo = d < 0.99; mid = (~hi) & (~lo)
    n_hi, n_lo, n_mid = int(np.sum(hi)), int(np.sum(lo)), int(np.sum(mid))
    assert 4 * n_hi + 2 * n_lo + 3 * n_mid == 765
    rng_c = np.random.default_rng(11001)
    for snr_db in (16.0, 20.0):
        s2 = 10.0 ** (-snr_db / 10.0)
        b_psk = b_qam = b_d = b_i = 0
        tot = 0
        for _ in range(100):
            ells = [0, 2, 5]; nus = [0.0, 1.4, -2.1]
            hs = (rng_c.standard_normal(3) + 1j * rng_c.standard_normal(3)) / np.sqrt(6.0)
            G = A @ sum(h * L2.path_time_matrix(N, l, v, c1) for h, l, v in zip(hs, ells, nus)) @ A.conj().T
            w = np.sqrt(s2 / 2.0) * (rng_c.standard_normal(N) + 1j * rng_c.standard_normal(N))

            # Unbiased symmetric LMMSE for D=I: W_u = G^H (G G^H + s2 I)^-1, gain alpha_k = Re((W_u G)_{k,k})
            W_u = np.linalg.solve(G @ G.conj().T + s2 * np.eye(N), G).conj().T
            alpha_u = np.real(np.sum(W_u * G.T, axis=1))

            i_p = rng_c.integers(0, 8, size=N)
            xh = (W_u @ (G @ L2.PSK8_PTS[i_p] + w)) / alpha_u
            ih = np.argmin(np.abs(xh[:, None] - L2.PSK8_PTS[None, :]), axis=1)
            b_psk += int(np.sum(L2.PSK8_BITS[ih] != L2.PSK8_BITS[i_p]))

            i_q = rng_c.integers(0, 8, size=N)
            xh = (W_u @ (G @ L2.QAM8_PTS[i_q] + w)) / alpha_u
            ih = np.argmin(np.abs(xh[:, None] - L2.QAM8_PTS[None, :]), axis=1)
            b_qam += int(np.sum(L2.QAM8_BITS[ih] != L2.QAM8_BITS[i_q]))

            # Exact 765-bit matched constellation
            i16 = rng_c.integers(0, 16, size=n_hi)
            i4 = rng_c.integers(0, 4, size=n_lo)
            i8 = rng_c.integers(0, 8, size=n_mid)
            xn = np.empty(N, dtype=np.complex128)
            xn[hi] = L2.QAM16_PTS[i16]; xn[lo] = L2.QPSK_PTS[i4]; xn[mid] = L2.QAM8_PTS[i8]
            ym = G @ (np.sqrt(d) * xn) + w

            # Symmetric unbiased D-LMMSE: W_d = D G^H (G D G^H + s2 I)^-1, gain on x_c is alpha_d = Re((W_d G)_{k,k})
            GD = G * d[None, :]
            W_d = (d[:, None] * G.conj().T) @ np.linalg.inv(GD @ G.conj().T + s2 * np.eye(N))
            alpha_d = np.real(np.sum(W_d * G.T, axis=1))
            xh_d = ((W_d @ ym) / alpha_d) / np.sqrt(d)
            xh_i = ((W_u @ ym) / alpha_u) / np.sqrt(d)
            for xh_cur, is_d in [(xh_d, True), (xh_i, False)]:
                ih16 = np.argmin(np.abs(xh_cur[hi, None] - L2.QAM16_PTS[None, :]), axis=1)
                ih4 = np.argmin(np.abs(xh_cur[lo, None] - L2.QPSK_PTS[None, :]), axis=1)
                ih8 = np.argmin(np.abs(xh_cur[mid, None] - L2.QAM8_PTS[None, :]), axis=1)
                eb = (int(np.sum(L2.QAM16_BITS[ih16] != L2.QAM16_BITS[i16]))
                      + int(np.sum(L2.QPSK_BITS[ih4] != L2.QPSK_BITS[i4]))
                      + int(np.sum(L2.QAM8_BITS[ih8] != L2.QAM8_BITS[i8])))
                if is_d: b_d += eb
                else: b_i += eb
            tot += 765
        print(f"  SNR={snr_db:4.1f} dB (765 bits/blk BOTH!) | 8PSK={b_psk/tot:.5f} | 8QAM={b_qam/tot:.5f} | "
              f"Ours(D)={b_d/tot:.5f} | Ours(I)={b_i/tot:.5f}")

    # 2. Independent H0_cal=200 (dev) for ALL 5 calibrated arms (incl. HomoBanded!)
    print("\n" + "=" * 84)
    print("[DEV 2] Dev Calibration (n_cal=200) + Frozen Reg1 & Reg2 Sizing (n_dev=80, Exact NNLS + HomoBanded)")
    print("=" * 84)
    rng_cal = np.random.default_rng(12001)
    n_cal = 200
    h0 = {"Ours_Banded": [], "Abl_DiagOnly": [], "Abl_HomoBanded": [], "Rival_TDCov": [], "Rival_OFDM_c1_0": []}
    for _ in range(n_cal):
        W_t = (rng_cal.standard_normal((N, M_c)) + 1j * rng_cal.standard_normal((N, M_c))) / np.sqrt(2.0)
        Y_af = L2.daft_fast(W_t, c1, c2)
        Y_of = L2.daft_fast(W_t, 0.0, c2)
        h0["Ours_Banded"].append(estimate_banded_v2(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=False, return_top_stat=True)[1])
        h0["Abl_DiagOnly"].append(estimate_banded_v2(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, use_lag1=False, homoscedastic=False, return_top_stat=True)[1])
        h0["Abl_HomoBanded"].append(estimate_banded_v2(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=True, return_top_stat=True)[1])
        h0["Rival_TDCov"].append(estimate_td_cov_exact_nnls(W_t, cfg, ell_max, nu_max, 0.0, P_max=1, return_top_stat=True)[1])
        h0["Rival_OFDM_c1_0"].append(estimate_banded_v2(Y_of, cfg, 0, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=False, return_top_stat=True)[1])
    # Exact rank 198 (0-based 197) => (201 - 198)/201 = 3/201 = 1.49%
    taus = {k: float(np.sort(v)[197]) for k, v in h0.items()}
    print("  Dev taus (rank 198/200, 1.49%):", {k: round(v, 2) for k, v in taus.items()})

    # 2b. Static high-SNR (< 1% convergence) health check on n=32 scenes for BOTH Ours_Banded & Rival_TDCov (round-13.md line 16)
    print("\n" + "=" * 84)
    print("[DEV 2b] 32-Scene High-SNR Static Convergence Health Check (Ours_Banded & Rival_TDCov)")
    print("=" * 84)
    rng_st = np.random.default_rng(14501)
    n_st = 32; M_st = 256; s2_st = 1e-4  # 40 dB SNR
    st_err_b, st_err_t = [], []
    st_hit_b = st_hit_t = 0
    for _ in range(n_st):
        l_t = int(rng_st.integers(0, ell_max + 1))
        v_t = float(rng_st.uniform(-nu_max + 0.5, nu_max - 0.5))
        X_m = np.sqrt(d[:, None]) * sample_765bit_norm(rng_st, cfg, M_st)
        W_st = np.sqrt(s2_st / 2.0) * (rng_st.standard_normal((N, M_st)) + 1j * rng_st.standard_normal((N, M_st)))
        R_st = L2.apply_path_time_fast(L2.idaft_fast(X_m, c1, c2), l_t, v_t, c1) + W_st
        Y_st = L2.daft_fast(R_st, c1, c2)
        db, _ = estimate_banded_v2(Y_st, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)
        dt, _ = estimate_td_cov_exact_nnls(R_st, cfg, ell_max, nu_max, taus["Rival_TDCov"], P_max=5)
        hb, _, eb = L2.match_targets(db, [(l_t, v_t)], nu_tol=0.25)
        ht, _, et = L2.match_targets(dt, [(l_t, v_t)], nu_tol=0.25)
        st_hit_b += hb; st_hit_t += ht
        st_err_b.extend(eb); st_err_t.extend(et)
    print(f"  Ours_Banded: hit={st_hit_b}/{n_st} ({100*st_hit_b/n_st:.1f}%), RMSE(nu)={np.sqrt(np.mean(np.array(st_err_b)**2)):.5f} (< 0.01 bin!)")
    print(f"  Rival_TDCov: hit={st_hit_t}/{n_st} ({100*st_hit_t/n_st:.1f}%), RMSE(nu)={np.sqrt(np.mean(np.array(st_err_t)**2)):.5f} (< 0.01 bin!)")

    # 3. Frozen Reg1 (P=2: 0, -13.5 dB) & Reg2 (P=3: 0, -5, -12.5 dB) with n_dev = 80!
    rng_d = np.random.default_rng(15501)
    rng_t = np.random.default_rng(16501)
    n_dev = 80
    s2_t = 10.0 ** (-1.5)
    arms = ["Ours_Banded", "Abl_DiagOnly", "Abl_HomoBanded", "Rival_TDCov", "Rival_OFDM_c1_0", "Abl_NoMask"]

    for reg_name, pwrs_db in [("Reg1: P=2 (0, -13.5 dB)", [0.0, -13.5]), ("Reg2: P=3 (0, -5, -12.5 dB)", [0.0, -5.0, -12.5])]:
        gammas = [10.0 ** (x / 10.0) for x in pwrs_db]
        wt = {a: np.zeros(n_dev, dtype=int) for a in arms}
        fa = {a: np.zeros(n_dev, dtype=int) for a in arms}
        for i in range(n_dev):
            ells = rng_d.choice(np.arange(0, ell_max + 1), size=len(pwrs_db), replace=False).tolist()
            nus = rng_d.uniform(-nu_max + 0.3, nu_max - 0.3, size=len(pwrs_db)).tolist()
            truths = list(zip(ells, nus))
            X_norm = sample_765bit_norm(rng_d, cfg, M_c)
            X_mask = np.sqrt(d[:, None]) * X_norm  # PURE mask-only factor vs X_norm!
            Hf = np.array([np.sqrt(g / 2.0) * (rng_d.standard_normal(M_c) + 1j * rng_d.standard_normal(M_c)) for g in gammas])
            W_t = np.sqrt(s2_t / 2.0) * (rng_d.standard_normal((N, M_c)) + 1j * rng_d.standard_normal((N, M_c)))

            S_af = L2.idaft_fast(X_mask, c1, c2)
            R_af = W_t.copy()
            for p in range(len(pwrs_db)):
                R_af += L2.apply_path_time_fast(S_af, ells[p], nus[p], c1) * Hf[p][None, :]
            Y_af = L2.daft_fast(R_af, c1, c2)

            S_of = L2.idaft_fast(X_mask, 0.0, c2)
            R_of = W_t.copy()
            for p in range(len(pwrs_db)):
                R_of += L2.apply_path_time_fast(S_of, ells[p], nus[p], 0.0) * Hf[p][None, :]
            Y_of = L2.daft_fast(R_of, 0.0, c2)

            S_nm = L2.idaft_fast(X_norm, c1, c2)
            R_nm = W_t.copy()
            for p in range(len(pwrs_db)):
                R_nm += L2.apply_path_time_fast(S_nm, ells[p], nus[p], c1) * Hf[p][None, :]
            Y_nm = L2.daft_fast(R_nm, c1, c2)

            outs = {
                "Ours_Banded": estimate_banded_v2(Y_af, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)[0],
                "Abl_DiagOnly": estimate_banded_v2(Y_af, cfg, Q, ell_max, nu_max, taus["Abl_DiagOnly"], P_max=5, use_lag1=False, homoscedastic=False)[0],
                "Abl_HomoBanded": estimate_banded_v2(Y_af, cfg, Q, ell_max, nu_max, taus["Abl_HomoBanded"], P_max=5, use_lag1=True, homoscedastic=True)[0],
                "Rival_TDCov": estimate_td_cov_exact_nnls(R_af, cfg, ell_max, nu_max, taus["Rival_TDCov"], P_max=5)[0],
                "Rival_OFDM_c1_0": estimate_banded_v2(Y_of, cfg, 0, ell_max, nu_max, taus["Rival_OFDM_c1_0"], P_max=5, use_lag1=True, homoscedastic=False, tie_rng=rng_t)[0],
                "Abl_NoMask": estimate_banded_v2(Y_nm, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)[0],
            }
            for a, dets in outs.items():
                _, fac, _ = L2.match_targets(dets, truths, nu_tol=0.25)
                fa[a][i] = 1 if fac > 0 else 0
                wh, _, _ = L2.match_targets(dets, [truths[-1]], nu_tol=0.25)
                wt[a][i] = wh

        print(f"\n  [{reg_name}] (n_dev={n_dev}):")
        for a in arms:
            print(f"    {a:16s} | WT-Pd={100*np.mean(wt[a]):5.1f}% | anyFA={100*np.mean(fa[a]):4.1f}%")
        for rv in ["Abl_DiagOnly", "Abl_HomoBanded", "Rival_TDCov", "Rival_OFDM_c1_0", "Abl_NoMask"]:
            ci = newcombe_method10(wt["Ours_Banded"], wt[rv])
            hw800 = ci["hw"] * math.sqrt(n_dev / 800.0)
            print(f"      Ours - {rv:15s}: {100*ci['diff']:+5.1f} pp (hw@{n_dev}={100*ci['hw']:.1f}, est hw@800={100*hw800:.2f} pp)")
        for abl_k in ["Abl_DiagOnly", "Abl_HomoBanded", "Abl_NoMask"]:
            d08 = paired_ratio_contrast_ci(wt["Ours_Banded"], wt[abl_k], 0.80)
            print(f"      Bidirectional D_0.8 ({abl_k:14s}): est={100*d08['est']:+5.1f} pp, ratio={d08['ratio']:.3f}, est hw@800={100*d08['hw']*math.sqrt(n_dev/800.0):.2f} pp (limit 25%={100*0.25*max(d08['est'],0):.2f} pp)")

    print(f"\nUpdated dev sizing runtime: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
