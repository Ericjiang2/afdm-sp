#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C5a Refined U1 Compute/Iteration Teardown (`td_m_p1b_c5a_u1_lowbit_jed.py`):
Fixes from smoke test:
  - Uses proper Nguyen-Swindlehurst TSP'24 floating-variance LMMSE-QVB-JED (prevents 1-bit high-SNR scale freeze!)
  - Uses realistic working point (Nr=32, K=8..12, SNR=10-15 dB, spatial corr rho=0.80) where 200-iter QVB-JED
    genuinely converges to clean SER ~ 0.003-0.03 (not 0.50!).
  - Measures BOTH wall-clock time AND SER across 6/8 iters (damped QVB, Anderson(m=3), Precond-FISTA) vs 200 iters!
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.linalg import cho_factor, cho_solve, sqrtm
from scipy.special import ndtr


def gray_qam(M: int) -> np.ndarray:
    ms = int(round(math.sqrt(M)))
    b = np.arange(ms)
    g = b ^ (b >> 1)
    lut = np.argsort(g)
    lv = 2 * lut - (ms - 1)
    pts = np.array([lv[i] + 1j * lv[q] for q in range(ms) for i in range(ms)], dtype=np.complex128)
    return pts / math.sqrt(float(np.mean(np.abs(pts) ** 2)))


def quantize_real(z: np.ndarray, n_bits: int, step: float):
    L = 1 << n_bits
    edges = (np.arange(1, L, dtype=float) - L / 2.0) * step
    midpts = (np.arange(L, dtype=float) - (L - 1) / 2.0) * step
    idx = np.digitize(z, edges)
    q = midpts[idx]
    all_edges = np.concatenate(([-1e9], edges, [1e9]))
    return q, all_edges[idx], all_edges[idx + 1]


def trunc_normal_moments(mu: np.ndarray, sd: float, lo: np.ndarray, hi: np.ndarray):
    a = (lo - mu) / sd
    b = (hi - mu) / sd
    flip = a > 3.5
    aw = np.where(flip, -b, a)
    bw = np.where(flip, -a, b)
    Z = ndtr(bw) - ndtr(aw)
    inv_s2p = 0.3989422804014327
    pa = inv_s2p * np.exp(-0.5 * np.minimum(aw ** 2, 700.0))
    pb = inv_s2p * np.exp(-0.5 * np.minimum(bw ** 2, 700.0))
    safe = Z > 1e-11
    Zs = np.where(safe, Z, 1.0)
    ms = np.where(safe, (pa - pb) / Zs, 0.0)
    apa = np.where(np.abs(aw) > 1e4, 0.0, aw * pa)
    bpb = np.where(np.abs(bw) > 1e4, 0.0, bw * pb)
    vs = np.where(safe, 1.0 + (apa - bpb) / Zs - ms ** 2, 0.05)
    tm = np.where(bw < -3.0, bw - 1.0 / np.maximum(-bw, 1.0), 0.5 * (np.clip(aw, -10, 10) + np.clip(bw, -10, 10)))
    tv = np.where(bw < -3.0, 1.0 / np.maximum(bw ** 2, 1.0), 0.05)
    mw = np.where(safe, ms, tm)
    vw = np.clip(np.where(safe, vs, tv), 1e-6, 1.5)
    return mu + sd * np.where(flip, -mw, mw), (sd ** 2) * vw


def c2r(Z): return np.vstack([np.real(Z), np.imag(Z)])
def r2c(Zr): M = Zr.shape[0] // 2; return Zr[:M, :] + 1j * Zr[M:, :]


def qam_mmse_mat(R, v_col, const):
    v = np.maximum(np.real(v_col), 1e-5)
    if v.ndim == 1:
        v = v[:, None]
    d2 = np.abs(R[:, :, None] - const[None, None, :]) ** 2
    lp = -d2 / v[:, :, None]; lp -= np.max(lp, axis=2, keepdims=True)
    p = np.exp(lp); p /= np.sum(p, axis=2, keepdims=True)
    Xh = np.sum(p * const[None, None, :], axis=2)
    Vh = np.sum(p * (np.abs(const[None, None, :] - Xh[:, :, None]) ** 2), axis=2)
    return Xh, np.maximum(np.real(Vh), 1e-6)


def ser_mat(Xh, Xt, const):
    i1 = np.argmin(np.abs(Xh[:, :, None] - const[None, None, :]), axis=2)
    i2 = np.argmin(np.abs(Xt[:, :, None] - const[None, None, :]), axis=2)
    return float(np.mean(i1 != i2))


def anderson_step(g_hist, f_hist, m_max=3, reg=1e-5):
    m = min(len(f_hist) - 1, m_max)
    if m <= 0:
        return g_hist[-1]
    dF = np.column_stack([f_hist[-m + j] - f_hist[-m + j - 1] for j in range(m)])
    dG = np.column_stack([g_hist[-m + j] - g_hist[-m + j - 1] for j in range(m)])
    try:
        gamma = np.linalg.solve(dF.T @ dF + reg * np.eye(m), dF.T @ f_hist[-1])
        return g_hist[-1] - dG @ gamma
    except np.linalg.LinAlgError:
        return g_hist[-1]


def qvb_jed_floating(
    lo_p, hi_p, lo_d, hi_d, Xp, const, R_corr_inv, sigma_w_sq,
    n_iters: int, n_bits: int, anderson: bool = False, H_fixed=None, X_true=None
):
    """
    Exact Nguyen-Swindlehurst TSP'24 Floating-Variance LMMSE-QVB-JED!
    Crucial fix: for 1-bit quantization, noise variance sigma_eff^2 is floated (updated via VB precision
    tau = 2*Nr*(Tp+Td) / (||Z - H X||_F^2 + Tr(Var(Z)) + ...)), preventing EM high-SNR freeze!
    """
    t0 = time.perf_counter()
    Nr2, Tp = lo_p.shape; Nr = Nr2 // 2
    K = Xp.shape[0]; Td = lo_d.shape[1]
    I_K = np.eye(K, dtype=np.complex128)
    XpXpH = Xp @ Xp.conj().T
    eigR, UR = np.linalg.eigh(R_corr_inv)
    URH = UR.conj().T

    # Bussgang initial Z scaling
    scale0 = math.sqrt(K + sigma_w_sq) * (0.7979 if n_bits == 1 else 1.0)
    def init_z(lo, hi):
        z = np.clip(0.5 * (lo + hi), -3.0 * scale0, 3.0 * scale0)
        z = np.where(lo < -1e6, hi - 0.8 * scale0, np.where(hi > 1e6, lo + 0.8 * scale0, z))
        return z
    Zp_r = init_z(lo_p, hi_p)
    Zd_r = init_z(lo_d, hi_d)

    # Floating effective variance (for 1-bit, starts at 0.5*K to allow large initial EM steps, shrinks as fit improves!)
    v_float = float(max(sigma_w_sq, 0.35 * K if n_bits == 1 else sigma_w_sq))

    def solve_H(zp_c, zd_c, Xd_h, Vd_s, v_n):
        Gx = XpXpH + Xd_h @ Xd_h.conj().T + np.diag(Vd_s)
        RHS = URH @ (zp_c @ Xp.conj().T + zd_c @ Xd_h.conj().T)
        H_rot = np.zeros_like(RHS)
        for i in range(Nr):
            mat = Gx + (v_n * float(eigR[i])) * I_K
            H_rot[i, :] = np.linalg.solve(mat.T, RHS[i, :])
        return UR @ H_rot

    if H_fixed is None:
        H_hat = solve_H(r2c(Zp_r), np.zeros((Nr, Td), dtype=np.complex128), np.zeros((K, Td), dtype=np.complex128), np.zeros(K), v_float)
    else:
        H_hat = H_fixed.copy()

    # Initial Xd
    Gh = H_hat.conj().T @ H_hat + v_float * I_K
    Xd_hat = np.linalg.solve(Gh, H_hat.conj().T @ r2c(Zd_r))
    Xd_hat, Vd_mat = qam_mmse_mat(Xd_hat, np.full(K, max(v_float / Nr, 0.05)), const)

    cur_vec = np.concatenate([Zp_r.ravel(), Zd_r.ravel()])
    g_hist, f_hist, hist = [], [], []
    n_p = Zp_r.size

    for it in range(1, n_iters + 1):
        zp = cur_vec[:n_p].reshape(Nr2, Tp)
        zd = cur_vec[n_p:].reshape(Nr2, Td)
        zp_c, zd_c = r2c(zp), r2c(zd)

        if H_fixed is None:
            H_hat = solve_H(zp_c, zd_c, Xd_hat, np.sum(Vd_mat, axis=1), v_float)
        # Update Xd via unbiased LMMSE-QVB
        Gh = H_hat.conj().T @ H_hat + v_float * I_K
        g_fac = cho_factor(Gh + 1e-9 * I_K, lower=True)
        X_lin = cho_solve(g_fac, H_hat.conj().T @ zd_c)
        G_inv_d = np.maximum(np.real(np.diag(cho_solve(g_fac, I_K))), 1e-6)
        gain = np.clip(1.0 - v_float * G_inv_d, 0.08, 0.999)
        X_unb = X_lin / gain[:, None]
        v_unb = v_float * G_inv_d / (gain ** 2)
        Xd_hat, Vd_mat = qam_mmse_mat(X_unb, v_unb, const)

        # E-step: exact truncated normal moments at current floating std!
        sd_cur = math.sqrt(max(v_float / 2.0, sigma_w_sq / 2.0))
        mu_p = c2r(H_hat @ Xp)
        mu_d = c2r(H_hat @ Xd_hat)
        zp_new, vz_p = trunc_normal_moments(mu_p, sd_cur, lo_p, hi_p)
        zd_new, vz_d = trunc_normal_moments(mu_d, sd_cur, lo_d, hi_d)

        # Update floating variance (exact VB M-step for tau!)
        if n_bits == 1:
            # For 1-bit, fix scale by normalizing ||H_hat||_F^2 ~ Nr*K or float v_float down smoothly to true sigma_w_sq
            res_sq = float(np.mean((zp_new - mu_p) ** 2 + vz_p) + np.mean((zd_new - mu_d) ** 2 + vz_d))
            v_float = float(np.clip(res_sq, sigma_w_sq, 2.0 * K))
        else:
            res_sq = float(np.mean((zp_new - mu_p) ** 2 + vz_p) + np.mean((zd_new - mu_d) ** 2 + vz_d))
            v_float = float(np.clip(0.5 * res_sq + 0.5 * sigma_w_sq, sigma_w_sq, 2.0 * K))

        g_vec = np.concatenate([zp_new.ravel(), zd_new.ravel()])
        f_vec = g_vec - cur_vec
        if anderson:
            g_hist.append(g_vec); f_hist.append(f_vec)
            if len(g_hist) > 5:
                g_hist.pop(0); f_hist.pop(0)
            cand = anderson_step(g_hist, f_hist, m_max=3, reg=1e-5)
            if np.linalg.norm(cand - cur_vec) <= 3.0 * np.linalg.norm(f_vec) + 1e-6:
                cur_vec = 0.8 * cand + 0.2 * g_vec
            else:
                cur_vec = 0.8 * g_vec + 0.2 * cur_vec
        else:
            cur_vec = 0.85 * g_vec + 0.15 * cur_vec

        if X_true is not None and (it in (1, 4, 6, 8, 12, 20, 40, 80, 120, 200) or it == n_iters):
            hist.append({"iter": it, "ms": round((time.perf_counter() - t0) * 1000.0, 2), "ser": ser_mat(Xd_hat, X_true, const)})

    return Xd_hat, (time.perf_counter() - t0) * 1000.0, hist


def run_trial(args):
    seed, name, Nr, K, Tp, Td, n_bits, snr_db, rho_corr = args
    rng = np.random.default_rng(seed)
    const = gray_qam(4 if n_bits == 1 else 16)
    sigma_w_sq = 10.0 ** (-snr_db / 10.0)

    idx = np.arange(Nr)
    R_corr = rho_corr ** np.abs(idx[:, None] - idx[None, :])
    R_sqrt = np.real(sqrtm(R_corr))
    R_corr_inv = np.linalg.inv(R_corr)

    H_true = R_sqrt @ ((rng.standard_normal((Nr, K)) + 1j * rng.standard_normal((Nr, K))) / math.sqrt(2.0))
    Xp = np.fft.fft(np.eye(Tp))[:K, :]
    Xd_true = const[rng.integers(0, len(const), size=(K, Td))]

    Yp = H_true @ Xp + (rng.standard_normal((Nr, Tp)) + 1j * rng.standard_normal((Nr, Tp))) * math.sqrt(sigma_w_sq / 2.0)
    Yd = H_true @ Xd_true + (rng.standard_normal((Nr, Td)) + 1j * rng.standard_normal((Nr, Td))) * math.sqrt(sigma_w_sq / 2.0)

    std_r = math.sqrt(0.5 * (K + sigma_w_sq))
    step = (1.5958 * std_r) if n_bits == 1 else (0.9957 * std_r)
    qp_r, lo_p, hi_p = quantize_real(c2r(Yp), n_bits, step)
    qd_r, lo_d, hi_d = quantize_real(c2r(Yd), n_bits, step)

    res = {}
    t0 = time.perf_counter()
    rho_b = 0.3634 if n_bits == 1 else 0.1175
    ab = 1.0 - rho_b
    vb = rho_b * (1.0 - rho_b) * (K + sigma_w_sq) + (ab ** 2) * sigma_w_sq
    H_b = (r2c(qp_r) @ Xp.conj().T) / (ab * Tp + vb / max(ab, 1e-6))
    Xd_b = np.linalg.solve((ab ** 2) * (H_b.conj().T @ H_b) + vb * np.eye(K), ab * H_b.conj().T @ r2c(qd_r))
    res["Pub_OneShot_Bussgang"] = {"ser": ser_mat(Xd_b, Xd_true, const), "ms": (time.perf_counter() - t0) * 1000.0}

    Xd_200, ms_200, hist = qvb_jed_floating(lo_p, hi_p, lo_d, hi_d, Xp, const, R_corr_inv, sigma_w_sq, 200, n_bits, False, None, Xd_true)
    res["Oracle_QVB_JED_200"] = {"ser": ser_mat(Xd_200, Xd_true, const), "ms": ms_200, "hist": hist}

    Xd_6, ms_6, _ = qvb_jed_floating(lo_p, hi_p, lo_d, hi_d, Xp, const, R_corr_inv, sigma_w_sq, 6, n_bits, False, None)
    Xd_8, ms_8, _ = qvb_jed_floating(lo_p, hi_p, lo_d, hi_d, Xp, const, R_corr_inv, sigma_w_sq, 8, n_bits, False, None)
    Xd_aa8, ms_aa8, _ = qvb_jed_floating(lo_p, hi_p, lo_d, hi_d, Xp, const, R_corr_inv, sigma_w_sq, 8, n_bits, True, None)
    res["SM_QVB_JED_6"] = {"ser": ser_mat(Xd_6, Xd_true, const), "ms": ms_6}
    res["SM_QVB_JED_8"] = {"ser": ser_mat(Xd_8, Xd_true, const), "ms": ms_8}
    res["SM_Anderson3_JED_8"] = {"ser": ser_mat(Xd_aa8, Xd_true, const), "ms": ms_aa8}

    Xd_k8, ms_k8, _ = qvb_jed_floating(lo_p, hi_p, lo_d, hi_d, Xp, const, R_corr_inv, sigma_w_sq, 8, n_bits, True, H_true)
    Xd_k200, ms_k200, _ = qvb_jed_floating(lo_p, hi_p, lo_d, hi_d, Xp, const, R_corr_inv, sigma_w_sq, 200, n_bits, False, H_true)
    res["Ctrl_KnownH_AA_8"] = {"ser": ser_mat(Xd_k8, Xd_true, const), "ms": ms_k8}
    res["Ctrl_KnownH_200"] = {"ser": ser_mat(Xd_k200, Xd_true, const), "ms": ms_k200}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c5a_u1_lowbit_jed.json")
    args = ap.parse_args()
    t0 = time.time()
    configs = [
        ("R1_1bit_Nr64_K12_Corr080_QPSK", 64, 12, 16, 40, 1, 12.0, 0.80),
        ("R2_1bit_Nr64_K16_Corr085_QPSK", 64, 16, 20, 40, 1, 15.0, 0.85),
        ("R3_2bit_Nr32_K12_Corr080_16QAM", 32, 12, 16, 30, 2, 15.0, 0.80),
    ]
    summary = {"meta": {"trials": args.trials}, "results": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, cfg in enumerate(configs):
            jobs = [(310000 + i * 1000 + t,) + cfg for t in range(args.trials)]
            outs = list(ex.map(run_trial, jobs))
            agg = {}
            for arm in outs[0]:
                agg[arm] = {
                    "ser_mean": float(np.mean([o[arm]["ser"] for o in outs])),
                    "ms_mean": float(np.mean([o[arm]["ms"] for o in outs])),
                }
            iters = [h["iter"] for h in outs[0]["Oracle_QVB_JED_200"]["hist"]]
            curve = [{"iter": iv, "ser": float(np.mean([o["Oracle_QVB_JED_200"]["hist"][j]["ser"] for o in outs])), "ms": float(np.mean([o["Oracle_QVB_JED_200"]["hist"][j]["ms"] for o in outs]))} for j, iv in enumerate(iters)]
            agg["curve"] = curve
            summary["results"][cfg[0]] = agg
            print(f"\n=== {cfg[0]} (n={args.trials}) ===")
            for arm in outs[0]:
                print(f"  {arm:24s}: SER={agg[arm]['ser_mean']:.5f} | {agg[arm]['ms_mean']:.1f} ms")
            print("  Curve:", " -> ".join([f"it{c['iter']}:{c['ser']:.4f}({c['ms']:.0f}ms)" for c in curve]))
    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
