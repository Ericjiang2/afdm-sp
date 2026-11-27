#!/usr/bin/env python3
"""
Formal L2 Experiment Script for Card I-20261126-m04 (Round 13, Runner m):
Zero-Pilot Non-Coherent Blind Bistatic AFDM-ISAC via Non-Stationary DAFT Power-Mask
and Scale-Invariant De-Chirped Banded (Lag-0 + Lag-1) Heteroscedastic Quasi-ML.

Protocol frozen in ideas/l2/PREDICTIONS_m_r13_m04.md (v2 — all Sol 11/12 Blocking items closed):
  - Exact 765-bit equal-net-payload DAFT power mask (127*16QAM@5/3 + 127*QPSK@1/3 + 1*8QAM@1.0)
  - Symmetric per-subcarrier unbiased LMMSE gain correction in G5 Comm Gray-BER gate
  - Faithful FULL G x G PSD Ranasinghe 2407.05328 Alg. 1 (LASSO + 3-iter FP-l0, H_G >= 0) in G2 & N=63 diag
  - Exact scipy.optimize.nnls in Rival_TDCov + 32-scene high-SNR static convergence gate G2b
  - Pure single-factor ablations: Abl_DiagOnly (lag-1 OFF), Abl_HomoBanded (heteroscedastic weighting OFF),
    Abl_NoMask (exact same unit-variance normalized 765-bit X_norm, ONLY removing sqrt(d) scaling!)
  - Exact order-statistic rank r=592 (0-based 591) for n_cal=600 -> marginal Pfa=9/601=1.4975%,
    exact Beta-Binomial P(X > 18 | n_ver=400, a=9, b=592) = 0.001194
  - Strict mode-separated virgin seeds (mutation: 19000001, smoke: 2124000000+, formal: 2034000000+)
  - Exact Newcombe (1998) Method 10 paired CI + Redline-5 hw <= 0.25 * margin wired into EVERY primary check
    including anyFA and paired D_0.8 bidirectional < 80% coupling contrasts!
"""

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import numpy as np
from scipy.fft import fft, ifft
from scipy.optimize import minimize, nnls
from scipy.stats import t as student_t


# =============================================================================
# 1. Core Waveform & Channel Primitives (Exact 765-bit Mask, Even Q => Phi=I)
# =============================================================================

def generate_m_sequence(order: int) -> np.ndarray:
    taps_map = {6: (5, 4), 7: (6, 5), 8: (7, 5, 4, 3), 9: (8, 4)}
    taps = taps_map[order]
    N = (1 << order) - 1
    state = [1] * order
    out = np.empty(N, dtype=np.float64)
    for i in range(N):
        out[i] = 1.0 if state[-1] == 1 else -1.0
        fb = 0
        for t in taps:
            fb ^= state[t]
        state = [fb] + state[:-1]
    return out


def build_system(order: int = 8, Q: int = 12, delta: float = 2.0 / 3.0) -> dict:
    """
    Build N = 2^order - 1 DAFT power mask with exact 3.000000 bpcu equal net payload:
      - (N-1)/2 high bins (+1): d = 1 + 2/3 = 5/3  -> Gray 16-QAM (4 bits, d_min^2 = 2/3)
      - (N-1)/2 low bins  (-1): d = 1 - 2/3 = 1/3  -> Gray QPSK   (2 bits, d_min^2 = 2/3)
      -       1 neutral bin    : d = 1.0           -> Gray 8-QAM  (3 bits, d_min^2 = 2/3)
    Exact mean(d) = 1.000000000000; exact payload = 3*N bits (765 bits for N=255).
    """
    N = (1 << order) - 1
    c1 = Q / (2.0 * N)
    c2 = 1.0 / (2.0 * np.pi * N)
    b = generate_m_sequence(order)
    pos_idx = np.where(b > 0)[0]
    mid_idx = int(pos_idx[-1])
    d = np.where(b > 0, 1.0 + delta, 1.0 - delta)
    d[mid_idx] = 1.0
    assert abs(float(np.mean(d)) - 1.0) < 1e-12 and float(np.min(d)) > 0.0
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


def afdm_daft_matrix(N: int, c1: float, c2: float) -> np.ndarray:
    n = np.arange(N, dtype=np.float64)
    lam1 = np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))
    lam2 = np.exp(-1j * 2.0 * np.pi * c2 * (n ** 2))
    F = fft(np.eye(N), axis=0) / np.sqrt(N)
    return (lam2[:, None] * F) * lam1[None, :]


def idaft_fast(x: np.ndarray, c1: float, c2: float) -> np.ndarray:
    N = x.shape[0]
    n = np.arange(N, dtype=np.float64)
    lam1_c = np.exp(1j * 2.0 * np.pi * c1 * (n ** 2))
    lam2_c = np.exp(1j * 2.0 * np.pi * c2 * (n ** 2))
    if x.ndim == 1:
        return lam1_c * (ifft(lam2_c * x) * np.sqrt(N))
    return lam1_c[:, None] * (ifft(lam2_c[:, None] * x, axis=0) * np.sqrt(N))


def daft_fast(r: np.ndarray, c1: float, c2: float) -> np.ndarray:
    N = r.shape[0]
    n = np.arange(N, dtype=np.float64)
    lam1 = np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))
    lam2 = np.exp(-1j * 2.0 * np.pi * c2 * (n ** 2))
    if r.ndim == 1:
        return lam2 * (fft(lam1 * r) / np.sqrt(N))
    return lam2[:, None] * (fft(lam1[:, None] * r, axis=0) / np.sqrt(N))


def path_time_matrix(N: int, ell: int, nu: float, c1: float) -> np.ndarray:
    n = np.arange(N, dtype=np.float64)
    phi = np.ones(N, dtype=np.complex128)
    if ell > 0:
        idx = np.arange(ell, dtype=np.float64)
        phi[:ell] = np.exp(-1j * 2.0 * np.pi * c1 * (N ** 2 - 2.0 * N * (ell - idx)))
    omega = np.exp(1j * 2.0 * np.pi * nu * n / N)
    H = np.zeros((N, N), dtype=np.complex128)
    cols = (np.arange(N) - ell) % N
    H[np.arange(N), cols] = phi * omega
    return H


def apply_path_time_fast(s: np.ndarray, ell: int, nu: float, c1: float) -> np.ndarray:
    N = s.shape[0]
    n = np.arange(N, dtype=np.float64)
    phi = np.ones(N, dtype=np.complex128)
    if ell > 0:
        idx = np.arange(ell, dtype=np.float64)
        phi[:ell] = np.exp(-1j * 2.0 * np.pi * c1 * (N ** 2 - 2.0 * N * (ell - idx)))
    omega = np.exp(1j * 2.0 * np.pi * nu * n / N)
    s_shift = np.roll(s, ell, axis=0)
    if s.ndim == 1:
        return (phi * omega) * s_shift
    return (phi * omega)[:, None] * s_shift


def complex_dirichlet(N: int, x: np.ndarray) -> np.ndarray:
    denom = 1.0 - np.exp(-1j * 2.0 * np.pi * x / N)
    near = np.abs(denom) < 1e-12
    num = 1.0 - np.exp(-1j * 2.0 * np.pi * x)
    return np.where(near, 1.0 + 0j, num / (N * np.where(near, 1.0 + 0j, denom)))


def lag_templates(D_fft: np.ndarray, N: int, u: float) -> tuple[np.ndarray, np.ndarray]:
    k = np.arange(N, dtype=np.float64)
    K0 = complex_dirichlet(N, k - u)
    K1 = complex_dirichlet(N, (k + 1.0) - u)
    t0 = np.real(ifft(fft(np.abs(K0) ** 2) * D_fft))
    t1 = ifft(fft(K0 * np.conj(K1)) * D_fft)
    return t0, t1


def lag_templates_and_grads(D_fft: np.ndarray, N: int, u: float):
    t0, t1 = lag_templates(D_fft, N, u)
    eps = 1e-6
    t0p, t1p = lag_templates(D_fft, N, u + eps)
    t0m, t1m = lag_templates(D_fft, N, u - eps)
    return t0, t1, (t0p - t0m) / (2.0 * eps), (t1p - t1m) / (2.0 * eps)


# =============================================================================
# 2. Explicit Gray-Coded Constellations (Verified Unit Energy & 1-bit Gray)
# =============================================================================

QPSK_PTS = np.array([-1 - 1j, -1 + 1j, 1 + 1j, 1 - 1j]) / np.sqrt(2.0)
QPSK_BITS = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=np.int8)

_PAM4_V = np.array([-3.0, -1.0, 1.0, 3.0])
_PAM4_B = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=np.int8)

QAM16_PTS = np.array([(_PAM4_V[i] + 1j * _PAM4_V[j]) / np.sqrt(10.0) for i in range(4) for j in range(4)])
QAM16_BITS = np.array([np.concatenate([_PAM4_B[i], _PAM4_B[j]]) for i in range(4) for j in range(4)], dtype=np.int8)

QAM8_PTS = np.array([(_PAM4_V[i] + 1j * (-1.0 if j == 0 else 1.0)) / np.sqrt(6.0) for i in range(4) for j in range(2)])
QAM8_BITS = np.array([np.concatenate([_PAM4_B[i], [j]]) for i in range(4) for j in range(2)], dtype=np.int8)

_PSK8_G = [0, 1, 3, 2, 6, 7, 5, 4]
PSK8_PTS = np.exp(1j * 2.0 * np.pi * np.arange(8) / 8.0)
PSK8_BITS = np.array([[int(ch) for ch in f"{g:03b}"] for g in _PSK8_G], dtype=np.int8)


def sample_765bit_norm(rng: np.random.Generator, cfg: dict, M: int) -> np.ndarray:
    """Unit-variance normalized constellation matrix X_norm (N x M) with exact 3*N bits/block."""
    d = cfg["d"]
    N = cfg["N"]
    hi = d > 1.01
    lo = d < 0.99
    mid = (~hi) & (~lo)
    X_norm = np.empty((N, M), dtype=np.complex128)
    X_norm[hi, :] = QAM16_PTS[rng.integers(0, 16, size=(int(np.sum(hi)), M))]
    X_norm[lo, :] = QPSK_PTS[rng.integers(0, 4, size=(int(np.sum(lo)), M))]
    X_norm[mid, :] = QAM8_PTS[rng.integers(0, 8, size=(int(np.sum(mid)), M))]
    return X_norm


def sample_uniform_8qam(rng: np.random.Generator, N: int, M: int) -> np.ndarray:
    return QAM8_PTS[rng.integers(0, 8, size=(N, M))]


def sample_uniform_16qam(rng: np.random.Generator, N: int, M: int) -> np.ndarray:
    return QAM16_PTS[rng.integers(0, 16, size=(N, M))]


# =============================================================================
# 3. Shared Receivers (Identical Across Gates & Formal Arms!)
# =============================================================================

def estimate_banded_clean(
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
    disable_rms_norm_mutation: bool = False,
):
    N, M = Y.shape
    D_fft = sys_cfg["D_fft"]
    D0_conj = sys_cfg["D0_conj"]
    k_idx = sys_cfg["k_idx"]
    kp1 = sys_cfg["kp1"]
    dechirp = sys_cfg["dechirp"]

    rms = 1.0 if disable_rms_norm_mutation else float(np.sqrt(np.mean(np.abs(Y) ** 2)))
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
            t0, t1 = lag_templates(D_fft, N, uj)
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
            t0, _ = lag_templates(D_fft, N, u)
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
                t0s[:, j], t1s[:, j], dt0s[:, j], dt1s[:, j] = lag_templates_and_grads(D_fft, N, us[j])
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
            w_res = p_hat - mu_c
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
                t0, t1 = lag_templates(D_fft, N, uc)
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
            t0, t1 = lag_templates(D_fft, N, uj)
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


def estimate_td_cov_nomp(
    R_time: np.ndarray,
    sys_cfg: dict,
    ell_max: int,
    nu_max: float,
    tau_td: float,
    P_max: int = 5,
    return_top_stat: bool = False,
):
    """Exact scipy.optimize.nnls solution for Sol's de-chirped non-wrapped TD-Cov spectral NOMP."""
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


def project_psd(M: np.ndarray) -> np.ndarray:
    Mh = 0.5 * (M + M.conj().T)
    w, V = np.linalg.eigh(Mh)
    return (V * np.maximum(w, 0.0)[None, :]) @ V.conj().T


def ranasinghe_full_psd_alg1(
    Y: np.ndarray, E_bar: np.ndarray, G: int, sigma_w2: float,
    beta: float = 1.0, eta: float = 0.1, alpha: float = 0.001, i_max: int = 3, n_admm: int = 180
) -> np.ndarray:
    """
    Faithful FULL G x G PSD Ranasinghe et al. (arXiv:2407.05328v2) Algorithm 1:
      - Full pair dictionary E_bar in C^{N x G^2} (Eq. 29-30)
      - Step 2: LASSO initialization (Eq. 31) via exact Woodbury ADMM
      - Steps 3-4: i_max=3 iterations of FP-l0 (Eq. 36-37) with full Hermitian PSD constraint H_G >= 0!
    """
    N_l, T_l = Y.shape
    M_var = G * G
    Ry = (Y @ Y.conj().T) / float(T_l) - sigma_w2 * np.eye(N_l)
    r_bar = Ry @ np.ones(N_l, dtype=np.complex128)
    Ehr = E_bar.conj().T @ r_bar

    rho = 2.0
    W_mat = np.linalg.inv(0.5 * rho * np.eye(N_l) + E_bar @ E_bar.conj().T)
    z = np.zeros(M_var, dtype=np.complex128)
    u = np.zeros(M_var, dtype=np.complex128)
    for _ in range(n_admm):
        rhs = 2.0 * Ehr + rho * (z - u)
        b = (rhs - E_bar.conj().T @ (W_mat @ (E_bar @ rhs))) / rho
        v = b + u
        mag = np.abs(v)
        z = np.where(mag > beta / rho, v * (1.0 - (beta / rho) / np.maximum(mag, 1e-15)), 0.0)
        u += b - z

    # Steps 3-4: literal Alg. 1 — compute Eq. (36) directly from LASSO vector z on iter 1, then from H on iters 2..i_max
    b_prev = z.copy()
    H = z.reshape((G, G), order="F")
    for _ in range(i_max):
        a_tilde = np.sqrt(alpha) / (np.abs(b_prev) ** 2 + alpha)
        w_pen = eta * (a_tilde ** 2)
        rho_fp = 1.0
        inv_d = 1.0 / (2.0 * w_pen + rho_fp)
        ED = E_bar * inv_d[None, :]
        W_fp = np.linalg.inv(0.5 * np.eye(N_l) + ED @ E_bar.conj().T)
        Z = project_psd(H)
        U = np.zeros((G, G), dtype=np.complex128)
        for _ in range(n_admm):
            rhs = 2.0 * Ehr + rho_fp * (Z - U).reshape(-1, order="F")
            d_rhs = inv_d * rhs
            b_vec = d_rhs - inv_d * (E_bar.conj().T @ (W_fp @ (E_bar @ d_rhs)))
            B_mat = b_vec.reshape((G, G), order="F")
            Z = project_psd(B_mat + U)
            U += B_mat - Z
        H = Z
        b_prev = H.reshape(-1, order="F")
    return H


def match_targets(dets: list[tuple[int, float, float]], truths: list[tuple[int, float]], nu_tol: float = 0.25):
    used = set()
    hits = 0
    nu_errs = []
    for (lt, vt) in truths:
        best_j, best_e = None, 1e9
        for j, (ld, vd, _) in enumerate(dets):
            if j in used or ld != lt:
                continue
            err = abs(vd - vt)
            if err <= nu_tol and err < best_e:
                best_e, best_j = err, j
        if best_j is not None:
            used.add(best_j)
            hits += 1
            nu_errs.append(best_e)
    return hits, len(dets) - hits, nu_errs


# =============================================================================
# 4. Exact Statistical Confidence Intervals (Wilson, Newcombe M10, Paired D_0.8)
# =============================================================================

Z95 = 1.959963984540054


def wilson_ci(k: int, n: int) -> dict:
    p = k / float(n)
    den = 1.0 + (Z95 ** 2) / n
    mid = (p + (Z95 ** 2) / (2.0 * n)) / den
    hw = (Z95 * math.sqrt((p * (1.0 - p) + (Z95 ** 2) / (4.0 * n)) / n)) / den
    return {"k": int(k), "n": int(n), "est": float(p), "lo": float(max(0.0, mid - hw)), "hi": float(min(1.0, mid + hw)), "hw": float(hw)}


def newcombe_method10_ci(a_hits: np.ndarray, b_hits: np.ndarray) -> dict:
    """Exact Newcombe (1998) Method 10 paired proportion CI (continuity-corrected phi)."""
    n = len(a_hits)
    e = float(np.sum((a_hits == 1) & (b_hits == 1)))
    f = float(np.sum((a_hits == 1) & (b_hits == 0)))
    g = float(np.sum((a_hits == 0) & (b_hits == 1)))
    h = float(np.sum((a_hits == 0) & (b_hits == 0)))
    p1 = (e + f) / n
    p2 = (e + g) / n
    diff = p1 - p2
    w1 = wilson_ci(int(e + f), n)
    w2 = wilson_ci(int(e + g), n)
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
    return {
        "n": int(n), "pa": float(p1), "pb": float(p2),
        "diff": float(diff), "lo": float(lo), "hi": float(hi), "hw": float(0.5 * (hi - lo)),
        "n11": int(e), "n10": int(f), "n01": int(g), "n00": int(h),
    }


def paired_ratio_contrast_ci(ours_hits: np.ndarray, abl_hits: np.ndarray, factor: float = 0.80) -> dict:
    """Asymptotic paired Student-t_{n-1} 95% CI for linear contrast D = factor * Y_ours - Y_abl > 0 <=> p_abl / p_ours < factor."""
    d_vec = factor * ours_hits.astype(np.float64) - abl_hits.astype(np.float64)
    n = len(d_vec)
    mean_d = float(np.mean(d_vec))
    se = float(np.std(d_vec, ddof=1) / math.sqrt(n))
    t_crit = float(student_t.ppf(0.975, df=n - 1))
    hw = t_crit * se
    p_o = float(np.mean(ours_hits))
    p_a = float(np.mean(abl_hits))
    return {
        "n": int(n), "factor": float(factor), "t_crit": t_crit, "ratio": float(p_a / max(p_o, 1e-12)),
        "est": mean_d, "lo": mean_d - hw, "hi": mean_d + hw, "hw": hw,
    }


# =============================================================================
# 5. Parallel Workers
# =============================================================================

_G_CFG = None


def _init_worker(order: int, Q: int, delta: float):
    global _G_CFG
    _G_CFG = build_system(order=order, Q=Q, delta=delta)


def _h0_worker(args):
    seed, M_c, ell_max, nu_max = args
    cfg = _G_CFG
    N, Q, c1, c2 = cfg["N"], cfg["Q"], cfg["c1"], cfg["c2"]
    rng = np.random.default_rng(seed)
    W_t = (rng.standard_normal((N, M_c)) + 1j * rng.standard_normal((N, M_c))) / np.sqrt(2.0)
    Y_af = daft_fast(W_t, c1, c2)
    Y_of = daft_fast(W_t, 0.0, c2)
    s_b = estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=False, return_top_stat=True)[1]
    s_d = estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, use_lag1=False, homoscedastic=False, return_top_stat=True)[1]
    s_h = estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=True, return_top_stat=True)[1]
    s_t = estimate_td_cov_nomp(W_t, cfg, ell_max, nu_max, 0.0, P_max=1, return_top_stat=True)[1]
    s_o = estimate_banded_clean(Y_of, cfg, 0, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=False, return_top_stat=True)[1]
    return (s_b, s_d, s_h, s_t, s_o)


def _h1_resid_worker(args):
    seed, M_c, pwrs, s2_r, ell_max, nu_max, taus = args
    cfg = _G_CFG
    N, Q, c1, c2, d = cfg["N"], cfg["Q"], cfg["c1"], cfg["c2"], cfg["d"]
    rng = np.random.default_rng(seed)
    tie_rng = np.random.default_rng(seed + 77777)
    ells = rng.choice(np.arange(0, ell_max + 1), size=len(pwrs), replace=False).tolist()
    nus = rng.uniform(-nu_max + 0.3, nu_max - 0.3, size=len(pwrs)).tolist()
    truths = list(zip(ells, nus))
    X_norm = sample_765bit_norm(rng, cfg, M_c)
    X_mask = np.sqrt(d[:, None]) * X_norm
    Hf = np.array([np.sqrt(g / 2.0) * (rng.standard_normal(M_c) + 1j * rng.standard_normal(M_c)) for g in pwrs])
    W_t = np.sqrt(s2_r / 2.0) * (rng.standard_normal((N, M_c)) + 1j * rng.standard_normal((N, M_c)))

    S = idaft_fast(X_mask, c1, c2)
    R = W_t.copy()
    for p in range(len(pwrs)):
        R += apply_path_time_fast(S, ells[p], nus[p], c1) * Hf[p][None, :]
    Y_af = daft_fast(R, c1, c2)

    S_of = idaft_fast(X_mask, 0.0, c2)
    R_of = W_t.copy()
    for p in range(len(pwrs)):
        R_of += apply_path_time_fast(S_of, ells[p], nus[p], 0.0) * Hf[p][None, :]
    Y_of = daft_fast(R_of, 0.0, c2)

    S_nm = idaft_fast(X_norm, c1, c2)
    R_nm = W_t.copy()
    for p in range(len(pwrs)):
        R_nm += apply_path_time_fast(S_nm, ells[p], nus[p], c1) * Hf[p][None, :]
    Y_nm = daft_fast(R_nm, c1, c2)

    out = {}
    for name, dets in [
        ("Ours_Banded", estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)[0]),
        ("Abl_DiagOnly", estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, taus["Abl_DiagOnly"], P_max=5, use_lag1=False, homoscedastic=False)[0]),
        ("Abl_HomoBanded", estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, taus["Abl_HomoBanded"], P_max=5, use_lag1=True, homoscedastic=True)[0]),
        ("Rival_TDCov", estimate_td_cov_nomp(R, cfg, ell_max, nu_max, taus["Rival_TDCov"], P_max=5)[0]),
        ("Rival_OFDM_c1_0", estimate_banded_clean(Y_of, cfg, 0, ell_max, nu_max, taus["Rival_OFDM_c1_0"], P_max=5, use_lag1=True, homoscedastic=False, tie_rng=tie_rng)[0]),
        ("Abl_NoMask", estimate_banded_clean(Y_nm, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)[0]),
    ]:
        _, fac, _ = match_targets(dets, truths, nu_tol=0.25)
        out[name] = (1 if fac > 0 else 0, fac)
    return out


def _scene_worker(args):
    seed, tie_seed, M_c, pwrs_db, swerling2, s2_t, ell_max, nu_max, taus = args
    cfg = _G_CFG
    N, Q, c1, c2, d = cfg["N"], cfg["Q"], cfg["c1"], cfg["c2"], cfg["d"]
    rng = np.random.default_rng(seed)
    tie_rng = np.random.default_rng(tie_seed)
    P_t = len(pwrs_db)
    gammas = [10.0 ** (x / 10.0) for x in pwrs_db]

    ells = rng.choice(np.arange(0, ell_max + 1), size=P_t, replace=False).tolist()
    nus = rng.uniform(-nu_max + 0.3, nu_max - 0.3, size=P_t).tolist()
    truths = list(zip(ells, nus))

    # Pure single-factor mask ablation: X_norm is IDENTICAL between Ours and Abl_NoMask!
    X_norm = sample_765bit_norm(rng, cfg, M_c)
    X_mask = np.sqrt(d[:, None]) * X_norm
    if swerling2:
        Hf = np.array([np.sqrt(g / 2.0) * (rng.standard_normal(M_c) + 1j * rng.standard_normal(M_c)) for g in gammas])
    else:
        hs = np.array([np.sqrt(g) * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi)) for g in gammas])
        lo = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, size=M_c))
        Hf = hs[:, None] * lo[None, :]
    W_t = np.sqrt(s2_t / 2.0) * (rng.standard_normal((N, M_c)) + 1j * rng.standard_normal((N, M_c)))

    S_af = idaft_fast(X_mask, c1, c2)
    R_af = W_t.copy()
    for p in range(P_t):
        R_af += apply_path_time_fast(S_af, ells[p], nus[p], c1) * Hf[p][None, :]
    Y_af = daft_fast(R_af, c1, c2)

    S_of = idaft_fast(X_mask, 0.0, c2)
    R_of = W_t.copy()
    for p in range(P_t):
        R_of += apply_path_time_fast(S_of, ells[p], nus[p], 0.0) * Hf[p][None, :]
    Y_of = daft_fast(R_of, 0.0, c2)

    S_nm = idaft_fast(X_norm, c1, c2)
    R_nm = W_t.copy()
    for p in range(P_t):
        R_nm += apply_path_time_fast(S_nm, ells[p], nus[p], c1) * Hf[p][None, :]
    Y_nm = daft_fast(R_nm, c1, c2)

    t0 = time.perf_counter()
    d_b, _ = estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)
    ms_b = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    d_d, _ = estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, taus["Abl_DiagOnly"], P_max=5, use_lag1=False, homoscedastic=False)
    ms_d = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    d_h, _ = estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, taus["Abl_HomoBanded"], P_max=5, use_lag1=True, homoscedastic=True)
    ms_h = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    d_t, _ = estimate_td_cov_nomp(R_af, cfg, ell_max, nu_max, taus["Rival_TDCov"], P_max=5)
    ms_t = (time.perf_counter() - t0) * 1e3

    d_o, _ = estimate_banded_clean(Y_of, cfg, 0, ell_max, nu_max, taus["Rival_OFDM_c1_0"], P_max=5, use_lag1=True, homoscedastic=False, tie_rng=tie_rng)
    d_n, _ = estimate_banded_clean(Y_nm, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)

    arm_dets = {
        "Ours_Banded": (d_b, ms_b),
        "Abl_DiagOnly": (d_d, ms_d),
        "Abl_HomoBanded": (d_h, ms_h),
        "Rival_TDCov": (d_t, ms_t),
        "Rival_OFDM_c1_0": (d_o, 0.0),
        "Abl_NoMask": (d_n, 0.0),
    }
    res = {}
    for a, (dets, ms) in arm_dets.items():
        hc, fac, ne = match_targets(dets, truths, nu_tol=0.25)
        wh, _, _ = match_targets(dets, [truths[-1]], nu_tol=0.25)
        res[a] = (hc, wh, 1 if fac > 0 else 0, fac, ne, ms)
    return res


# =============================================================================
# 6. Startup Gates G1–G5 & Mutation Test
# =============================================================================

def run_gate_g1(cfg: dict, ell_max: int, nu_max: float, seed_g1: int, mutate: str | None = None) -> dict:
    N, Q, c1, c2, d = cfg["N"], cfg["Q"], cfg["c1"], cfg["c2"], cfg["d"]
    D_fft, k_idx, kp1, dechirp = cfg["D_fft"], cfg["k_idx"], cfg["kp1"], cfg["dechirp"]
    lam1, C_d = cfg["lam1"], cfg["C_d"]

    A_af = afdm_daft_matrix(N, c1, c2)
    A_of = afdm_daft_matrix(N, 0.0 if mutate != "c1_nonzero_ofdm" else c1, c2)

    G_o3 = A_of @ path_time_matrix(N, 3, 1.37, 0.0) @ A_of.conj().T
    G_o7 = A_of @ path_time_matrix(N, 7, 1.37, 0.0) @ A_of.conj().T
    R_o3 = (G_o3 * d[None, :]) @ G_o3.conj().T
    R_o7 = (G_o7 * d[None, :]) @ G_o7.conj().T
    ofdm_full_rel = float(np.linalg.norm(R_o3 - R_o7, "fro") / np.linalg.norm(R_o3, "fro"))
    ofdm_lag1_max = float(np.max(np.abs(R_o3[k_idx, kp1] - R_o7[k_idx, kp1])))

    G_a = A_af @ path_time_matrix(N, 5, 1.37, c1) @ A_af.conj().T
    R_a = (G_a * d[None, :]) @ G_a.conj().T
    u_a = (-Q * 5 + 1.37) % N
    t0, t1 = lag_templates(D_fft, N, u_a)
    r1_ex = R_a[k_idx, kp1] if mutate == "corrupt_lag1_dechirp" else R_a[k_idx, kp1] * dechirp
    err_lag0 = float(np.linalg.norm(np.real(np.diag(R_a)) - t0))
    err_lag1 = float(np.linalg.norm(r1_ex - t1))

    F = fft(np.eye(N), axis=0) / np.sqrt(N)
    R_in = (F.conj().T * d[None, :]) @ F
    R_z = np.zeros((N, N), dtype=np.complex128)
    s_pred = np.zeros(N, dtype=np.complex128)
    for (lt, vt, gt) in [(3, 1.37, 1.0), (7, -2.14, 0.5), (14, 0.08, 0.1)]:
        H_t = path_time_matrix(N, lt, vt, c1)
        Z_op = (lam1[:, None] * H_t) * np.conj(lam1)[None, :]
        R_z += gt * (Z_op @ R_in @ Z_op.conj().T)
        s_pred += gt * np.exp(1j * 2.0 * np.pi * (vt - Q * lt) * np.arange(N) / N)
    R_z_lin = np.array([np.mean(np.diag(R_z, -r)) for r in range(N)], dtype=np.complex128)
    td_pop_err = float(np.linalg.norm(R_z_lin[1:] / C_d[1:] - s_pred[1:]))

    rng_sc = np.random.default_rng(seed_g1)
    W_sc = (rng_sc.standard_normal((N, 128)) + 1j * rng_sc.standard_normal((N, 128))) / np.sqrt(2.0)
    Y_sc = daft_fast(W_sc, c1, c2)
    b_stats = [
        estimate_banded_clean(s * Y_sc, cfg, Q, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=False,
                              return_top_stat=True, disable_rms_norm_mutation=(mutate == "break_scale_inv"))[1]
        for s in (0.18, 1.0, 5.0)
    ]
    t_stats = [
        estimate_td_cov_nomp(s * W_sc, cfg, ell_max, nu_max, 0.0, P_max=1, return_top_stat=True)[1]
        for s in (0.18, 1.0, 5.0)
    ]
    scale_diff_b = float(max(b_stats) - min(b_stats))
    scale_diff_t = float(max(t_stats) - min(t_stats))

    td_pow = np.real(np.diag((A_af.conj().T * d[None, :]) @ A_af))
    td_flat_err = float(np.max(np.abs(td_pow - 1.0)))
    mask_mean_err = float(abs(float(np.mean(d)) - 1.0))

    passed = (
        ofdm_full_rel < 1e-13
        and ofdm_lag1_max < 1e-13
        and err_lag0 < 1e-12
        and err_lag1 < 1e-12
        and td_pop_err < 1e-11
        and scale_diff_b < 1e-8
        and scale_diff_t < 1e-8
        and td_flat_err < 1e-12
        and mask_mean_err < 1e-12
    )
    return {
        "pass": bool(passed),
        "seed_g1": int(seed_g1),
        "ofdm_full_rel": ofdm_full_rel,
        "ofdm_lag1_max": ofdm_lag1_max,
        "err_lag0": err_lag0,
        "err_lag1": err_lag1,
        "td_pop_err": td_pop_err,
        "scale_diff_banded": scale_diff_b,
        "scale_diff_tdcov": scale_diff_t,
        "td_flat_err": td_flat_err,
        "mask_mean_err": mask_mean_err,
    }


def run_gate_g2_ranasinghe_full_psd(seed: int, n_trials: int = 64, mutate: str | None = None) -> dict:
    """
    Redline-1 Faithful FULL G x G PSD Ranasinghe 2407.05328 Alg. 1 on EXACT Fig. 2 physical target:
      f_c = 70 GHz, BW = 20 MHz, N = 64, l_max = 4, f_max = 0.1 (grid nu in {0.0, 0.05, 0.10}),
      T = 1000, SNR = 20 dB, static LoS (0, 0) + moving target at range 15 m (ell = 2) and velocity v = 37 m/s (nu = 0.05525 bin).
    Checks BOTH range RMSE < 7.5 m AND velocity RMSE < 35.0 m/s (one 0.05-bin grid step = 33.48 m/s) + recon < 1e-12!
    """
    N64 = 64
    c_light = 3.0e8
    BW = 20.0e6
    fc = 70.0e9
    dr_m = c_light / (2.0 * BW)              # 7.50 m per delay bin (15 m = ell 2)
    dv_ms = c_light * BW / (2.0 * N64 * fc)  # 669.64 m/s per Doppler bin
    v_tgt_ms = 37.0
    nu_tgt = v_tgt_ms / dv_ms                # 0.055253 bin (exact Fig. 2 velocity inside f_max = 0.1!)

    c1_64 = 3.0 / (2.0 * N64)
    c2_64 = 1.0 / (2.0 * np.pi)
    ell_g = np.array([0, 1, 2, 3, 4])
    nu_g = np.array([0.0, 0.05, 0.10])
    pts = [(int(l), float(v)) for l in ell_g for v in nu_g]
    G = len(pts)
    j_los = pts.index((0, 0.0))
    j_grid_ref = pts.index((2, 0.05))
    A64 = afdm_daft_matrix(N64, c1_64, c2_64)
    Gammas = [A64 @ path_time_matrix(N64, l, v, c1_64) @ A64.conj().T for (l, v) in pts]
    G_true_tgt = A64 @ path_time_matrix(N64, 2, nu_tgt, c1_64) @ A64.conj().T
    ones64 = np.ones(N64, dtype=np.complex128)

    # Unanchored common integer delay-shift full-covariance ambiguity check: ((0,0),(2,0.05)) vs ((1,0),(3,0.05))
    R_01 = Gammas[j_los] @ Gammas[j_grid_ref].conj().T
    R_ab = Gammas[pts.index((1, 0.0))] @ Gammas[pts.index((3, 0.05))].conj().T
    unanch_corr = float(abs(np.vdot(R_01, R_ab)) / (np.linalg.norm(R_01) * np.linalg.norm(R_ab)))

    Gh1 = [Ga.conj().T @ ones64 for Ga in Gammas]
    E_full = np.column_stack([Gammas[a] @ Gh1[b] for b in range(G) for a in range(G)])
    if mutate == "break_ranasinghe_dict":
        E_full = np.roll(E_full, 3, axis=0)

    h0_t = 0.707 * np.exp(1j * 0.4)
    h1_t = 0.707 * np.exp(-1j * 0.9)
    hv = np.zeros(G, dtype=np.complex128)
    hv[j_los] = h0_t
    hv[j_grid_ref] = h1_t
    H_t = np.outer(hv, hv.conj())
    r_true = ((h0_t * Gammas[j_los] + h1_t * Gammas[j_grid_ref]) @ (h0_t * Gammas[j_los] + h1_t * Gammas[j_grid_ref]).conj().T) @ ones64
    recon_err = float(np.linalg.norm(r_true - E_full @ H_t.reshape(-1, order="F")))

    rng = np.random.default_rng(seed)
    T_g = 1000
    s2_g = 0.01  # SNR = 20 dB
    hits_sw0_ell = 0
    hits_sw0_unanch = 0
    hits_sw2_ell = 0
    sq_r_err = []
    sq_v_err = []

    for _ in range(n_trials):
        X64 = sample_uniform_16qam(rng, N64, T_g)
        W64 = np.sqrt(s2_g / 2.0) * (rng.standard_normal((N64, T_g)) + 1j * rng.standard_normal((N64, T_g)))
        h0 = np.exp(1j * rng.uniform(0, 2 * np.pi)) / np.sqrt(2.0)
        h1 = np.exp(1j * rng.uniform(0, 2 * np.pi)) / np.sqrt(2.0)
        Y0 = (h0 * Gammas[j_los] + h1 * G_true_tgt) @ X64 + W64
        H0 = ranasinghe_full_psd_alg1(Y0, E_full, G, s2_g, beta=1.0, eta=0.1, alpha=0.001, i_max=3, n_admm=200)
        row_sc = np.abs(H0[j_los, :]).copy()
        row_sc[j_los] = -1.0
        k_hat = int(np.argmax(row_sc))
        l_hat, v_hat = pts[k_hat]
        if l_hat == 2:
            hits_sw0_ell += 1
        sq_r_err.append(((l_hat - 2) * dr_m) ** 2)
        sq_v_err.append((v_hat * dv_ms - v_tgt_ms) ** 2)
        top2 = set(np.argsort(np.real(np.diag(H0)))[-2:].tolist())
        if {j_los, j_grid_ref} == top2:
            hits_sw0_unanch += 1

        # Swerling-II diagnostic on same Fig. 2 target
        h0m = (rng.standard_normal(T_g) + 1j * rng.standard_normal(T_g)) / 2.0
        h1m = (rng.standard_normal(T_g) + 1j * rng.standard_normal(T_g)) / 2.0
        Y2 = (Gammas[j_los] @ X64) * h0m[None, :] + (G_true_tgt @ X64) * h1m[None, :] + W64
        H2 = ranasinghe_full_psd_alg1(Y2, E_full, G, s2_g, beta=1.0, eta=0.1, alpha=0.001, i_max=3, n_admm=200)
        r2 = np.abs(H2[j_los, :]).copy()
        r2[j_los] = -1.0
        if pts[int(np.argmax(r2))][0] == 2:
            hits_sw2_ell += 1

    rec_sw0 = hits_sw0_ell / float(n_trials)
    rmse_r_m = float(math.sqrt(sum(sq_r_err) / len(sq_r_err)))
    rmse_v_ms = float(math.sqrt(sum(sq_v_err) / len(sq_v_err)))
    passed = (recon_err < 1e-12) and (unanch_corr > 1.0 - 1e-12) and (rec_sw0 >= 0.90) and (rmse_r_m < dr_m) and (rmse_v_ms < 35.0)
    return {
        "pass": bool(passed),
        "fig2_target_range_m": 15.0,
        "fig2_target_vel_ms": v_tgt_ms,
        "fig2_target_nu_bin": nu_tgt,
        "recon_err": recon_err,
        "unanch_shift_corr": unanch_corr,
        "static_sw0_los_row_delay_recovery": rec_sw0,
        "static_sw0_los_row_delay_hits": int(hits_sw0_ell),
        "static_sw0_unanch_top2_recovery": hits_sw0_unanch / float(n_trials),
        "static_sw0_range_rmse_m": rmse_r_m,
        "static_sw0_vel_rmse_ms": rmse_v_ms,
        "swerling2_full_psd_los_row_delay_recovery": hits_sw2_ell / float(n_trials),
        "n_trials": int(n_trials),
    }


def run_gate_g2b_static_convergence(cfg: dict, ell_max: int, nu_max: float, taus: dict, seed: int, n_trials: int = 32) -> dict:
    """High-SNR static-gain convergence health gate (< 0.01 bin RMSE) for BOTH Ours_Banded & Rival_TDCov."""
    N, Q, c1, c2, d = cfg["N"], cfg["Q"], cfg["c1"], cfg["c2"], cfg["d"]
    rng = np.random.default_rng(seed)
    M_st = 256
    s2_st = 1e-4  # 40 dB SNR
    hb_tot = ht_tot = 0
    eb_all, et_all = [], []
    for _ in range(n_trials):
        l_t = int(rng.integers(0, ell_max + 1))
        v_t = float(rng.uniform(-nu_max + 0.5, nu_max - 0.5))
        X_m = np.sqrt(d[:, None]) * sample_765bit_norm(rng, cfg, M_st)
        W_st = np.sqrt(s2_st / 2.0) * (rng.standard_normal((N, M_st)) + 1j * rng.standard_normal((N, M_st)))
        R_st = apply_path_time_fast(idaft_fast(X_m, c1, c2), l_t, v_t, c1) + W_st
        Y_st = daft_fast(R_st, c1, c2)
        db, _ = estimate_banded_clean(Y_st, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)
        dt, _ = estimate_td_cov_nomp(R_st, cfg, ell_max, nu_max, taus["Rival_TDCov"], P_max=5)
        hb, _, eb = match_targets(db, [(l_t, v_t)], nu_tol=0.25)
        ht, _, et = match_targets(dt, [(l_t, v_t)], nu_tol=0.25)
        hb_tot += hb
        ht_tot += ht
        eb_all.extend(eb)
        et_all.extend(et)
    rmse_b = float(math.sqrt(sum(e * e for e in eb_all) / len(eb_all))) if eb_all else None
    rmse_t = float(math.sqrt(sum(e * e for e in et_all) / len(et_all))) if et_all else None
    passed = (hb_tot == n_trials) and (ht_tot == n_trials) and (rmse_b is not None and rmse_b < 0.01) and (rmse_t is not None and rmse_t < 0.01)
    return {
        "pass": bool(passed),
        "n_trials": int(n_trials),
        "ours_banded_hits": int(hb_tot),
        "ours_banded_rmse_nu": rmse_b,
        "rival_tdcov_hits": int(ht_tot),
        "rival_tdcov_rmse_nu": rmse_t,
    }


def run_gate_g5_comm_ber(cfg: dict, seed: int, n_trials: int = 200) -> dict:
    """Exact 765-bit equal-net-payload Gray-coded BER non-inferiority gate with symmetric unbiased per-subcarrier LMMSE."""
    N, c1, c2, d = cfg["N"], cfg["c1"], cfg["c2"], cfg["d"]
    A = afdm_daft_matrix(N, c1, c2)
    hi = d > 1.01
    lo = d < 0.99
    mid = (~hi) & (~lo)
    n_hi, n_lo, n_mid = int(np.sum(hi)), int(np.sum(lo)), int(np.sum(mid))
    assert 4 * n_hi + 2 * n_lo + 3 * n_mid == 3 * N
    rng = np.random.default_rng(seed)

    results = {}
    all_pass = True
    for snr_db in (16.0, 20.0):
        s2 = 10.0 ** (-snr_db / 10.0)
        b_psk = b_qam = b_d = b_i = 0
        tot = 0
        for _ in range(n_trials):
            ells = [0, 2, 5]
            nus = [0.0, 1.4, -2.1]
            hs = (rng.standard_normal(3) + 1j * rng.standard_normal(3)) / np.sqrt(6.0)
            G = A @ sum(h * path_time_matrix(N, l, v, c1) for h, l, v in zip(hs, ells, nus)) @ A.conj().T
            w = np.sqrt(s2 / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))

            # Symmetric unbiased per-subcarrier LMMSE: alpha_k = Re((W G)_{k,k})
            W_u = np.linalg.solve(G @ G.conj().T + s2 * np.eye(N), G).conj().T
            alpha_u = np.real(np.sum(W_u * G.T, axis=1))

            i_p = rng.integers(0, 8, size=N)
            xh = (W_u @ (G @ PSK8_PTS[i_p] + w)) / alpha_u
            ih = np.argmin(np.abs(xh[:, None] - PSK8_PTS[None, :]), axis=1)
            b_psk += int(np.sum(PSK8_BITS[ih] != PSK8_BITS[i_p]))

            i_q = rng.integers(0, 8, size=N)
            xh = (W_u @ (G @ QAM8_PTS[i_q] + w)) / alpha_u
            ih = np.argmin(np.abs(xh[:, None] - QAM8_PTS[None, :]), axis=1)
            b_qam += int(np.sum(QAM8_BITS[ih] != QAM8_BITS[i_q]))

            i16 = rng.integers(0, 16, size=n_hi)
            i4 = rng.integers(0, 4, size=n_lo)
            i8 = rng.integers(0, 8, size=n_mid)
            xn = np.empty(N, dtype=np.complex128)
            xn[hi] = QAM16_PTS[i16]
            xn[lo] = QPSK_PTS[i4]
            xn[mid] = QAM8_PTS[i8]
            ym = G @ (np.sqrt(d) * xn) + w

            GD = G * d[None, :]
            W_d = (d[:, None] * G.conj().T) @ np.linalg.inv(GD @ G.conj().T + s2 * np.eye(N))
            alpha_d = np.real(np.sum(W_d * G.T, axis=1))
            xh_d = ((W_d @ ym) / alpha_d) / np.sqrt(d)
            xh_i = ((W_u @ ym) / alpha_u) / np.sqrt(d)
            for xh_cur, is_d in [(xh_d, True), (xh_i, False)]:
                ih16 = np.argmin(np.abs(xh_cur[hi, None] - QAM16_PTS[None, :]), axis=1)
                ih4 = np.argmin(np.abs(xh_cur[lo, None] - QPSK_PTS[None, :]), axis=1)
                ih8 = np.argmin(np.abs(xh_cur[mid, None] - QAM8_PTS[None, :]), axis=1)
                eb = (
                    int(np.sum(QAM16_BITS[ih16] != QAM16_BITS[i16]))
                    + int(np.sum(QPSK_BITS[ih4] != QPSK_BITS[i4]))
                    + int(np.sum(QAM8_BITS[ih8] != QAM8_BITS[i8]))
                )
                if is_d:
                    b_d += eb
                else:
                    b_i += eb
            tot += 3 * N

        ber_psk = b_psk / float(tot)
        ber_qam = b_qam / float(tot)
        ber_d = b_d / float(tot)
        ber_i = b_i / float(tot)
        ok_snr = ber_d <= min(ber_psk, ber_qam)
        all_pass = all_pass and ok_snr
        results[f"snr_{int(snr_db)}dB"] = {
            "gray_8psk_ber": ber_psk,
            "gray_8qam_ber": ber_qam,
            "ours_D_lmmse_ber": ber_d,
            "ours_I_lmmse_ber": ber_i,
            "non_inferior_pass": bool(ok_snr),
        }
    return {
        "pass": bool(all_pass),
        "n_trials": int(n_trials),
        "bits_per_block_both": int(3 * N),
        "net_rate_both_bpcu": 3.0,
        "by_snr": results,
    }


def run_diag_ranasinghe_n63(seed: int, n_trials: int = 128) -> dict:
    """
    Paired N=63 (order 6, Q=6) diagnostic under Swerling-II comparing:
      - Ours_Banded (no LoS single-target & with-LoS target)
      - Faithful FULL G x G PSD Ranasinghe 2407.05328 Alg. 1 (BOTH known-LoS row AND unanchored top-2 diagonal)
      - 4th-order known-LoS self-correlation top-1 score
    """
    cfg63 = build_system(order=6, Q=6, delta=2.0 / 3.0)
    N63, Q63, c1_63, c2_63, d63 = cfg63["N"], cfg63["Q"], cfg63["c1"], cfg63["c2"], cfg63["d"]
    ell_max63, nu_max63 = 4, 1.5
    ell_g = np.array([0, 1, 2, 3, 4])
    nu_g = np.array([-1.0, 0.0, 1.0])
    pts = [(int(l), float(v)) for l in ell_g for v in nu_g]
    G = len(pts)
    j_los = pts.index((0, 0.0))
    j_tgt = pts.index((2, 1.0))
    A63 = afdm_daft_matrix(N63, c1_63, c2_63)
    Gammas = [A63 @ path_time_matrix(N63, l, v, c1_63) @ A63.conj().T for (l, v) in pts]
    ones63 = np.ones(N63, dtype=np.complex128)
    Gh1 = [Ga.conj().T @ ones63 for Ga in Gammas]
    E_full = np.column_stack([Gammas[a] @ Gh1[b] for b in range(G) for a in range(G)])
    active_k = [k for k in range(G) if k != j_los]
    B_ops = [Gammas[j_los] @ Gammas[k].conj().T for k in active_k]

    rng_cal = np.random.default_rng(seed)
    M_63 = 128
    h0_63 = []
    for _ in range(120):
        W = (rng_cal.standard_normal((N63, M_63)) + 1j * rng_cal.standard_normal((N63, M_63))) / np.sqrt(2.0)
        h0_63.append(estimate_banded_clean(daft_fast(W, c1_63, c2_63), cfg63, Q63, ell_max63, nu_max63, 0.0, P_max=1, use_lag1=True, homoscedastic=False, return_top_stat=True)[1])
    tau63 = float(np.sort(h0_63)[118])

    rng = np.random.default_rng(seed + 1)
    s2 = 10.0 ** (-1.5)
    hits_ours_nolos = hits_ours_withlos = hits_rana_row = hits_rana_unanch = hits_4th_anch = 0
    for _ in range(n_trials):
        X_n = sample_765bit_norm(rng, cfg63, M_63)
        X_m = np.sqrt(d63[:, None]) * X_n
        W_daft = daft_fast(np.sqrt(s2 / 2.0) * (rng.standard_normal((N63, M_63)) + 1j * rng.standard_normal((N63, M_63))), c1_63, c2_63)
        h0m = (rng.standard_normal(M_63) + 1j * rng.standard_normal(M_63)) / np.sqrt(2.0)
        h1m = np.sqrt(0.25 / 2.0) * (rng.standard_normal(M_63) + 1j * rng.standard_normal(M_63))

        Y_m1 = (Gammas[j_tgt] @ X_m) * h1m[None, :] + W_daft
        d1, _ = estimate_banded_clean(Y_m1, cfg63, Q63, ell_max63, nu_max63, tau63, P_max=5, use_lag1=True, homoscedastic=False)
        hits_ours_nolos += match_targets(d1, [(2, 1.0)], nu_tol=0.25)[0]

        Y_m2 = (Gammas[j_los] @ X_m) * h0m[None, :] + (Gammas[j_tgt] @ X_m) * h1m[None, :] + W_daft
        d2, _ = estimate_banded_clean(Y_m2, cfg63, Q63, ell_max63, nu_max63, tau63, P_max=5, use_lag1=True, homoscedastic=False)
        hits_ours_withlos += match_targets(d2, [(2, 1.0)], nu_tol=0.25)[0]

        Y_u2 = (Gammas[j_los] @ X_n) * h0m[None, :] + (Gammas[j_tgt] @ X_n) * h1m[None, :] + W_daft
        H_r = ranasinghe_full_psd_alg1(Y_u2, E_full, G, s2, beta=1.0, eta=0.1, alpha=0.001, i_max=3, n_admm=150)
        r_sc = np.abs(H_r[j_los, :]).copy()
        r_sc[j_los] = -1.0
        if int(np.argmax(r_sc)) == j_tgt:
            hits_rana_row += 1
        if {j_los, j_tgt} == set(np.argsort(np.real(np.diag(H_r)))[-2:].tolist()):
            hits_rana_unanch += 1

        sc4 = [float(np.mean(np.abs(np.sum(np.conj(Y_u2) * (B @ Y_u2), axis=0)) ** 2)) for B in B_ops]
        if active_k[int(np.argmax(sc4))] == j_tgt:
            hits_4th_anch += 1

    return {
        "N": N63, "M": M_63, "n_trials": int(n_trials), "target_rel_db": -6.0,
        "ours_no_los_single_target_pd": hits_ours_nolos / float(n_trials),
        "ours_with_los_target_pd": hits_ours_withlos / float(n_trials),
        "ranasinghe_full_psd_los_row_sw2_pd": hits_rana_row / float(n_trials),
        "ranasinghe_full_psd_unanch_top2_sw2_pd": hits_rana_unanch / float(n_trials),
        "fourth_order_known_los_top1_pd": hits_4th_anch / float(n_trials),
        "note": "Ranasinghe full GxG PSD Alg. 1 reported for BOTH known-LoS row and unanchored top-2; 4th-order reported for known-LoS top-1 only (0 signal on no-LoS single target; exact shift/conjugate ambiguity without known anchor).",
    }


def run_diag_papr(cfg: dict, seed: int, n_syms: int = 2000) -> dict:
    N, c1, c2, d = cfg["N"], cfg["c1"], cfg["c2"], cfg["d"]
    rng = np.random.default_rng(seed)
    s_u = idaft_fast(sample_uniform_8qam(rng, N, n_syms), c1, c2)
    s_m = idaft_fast(np.sqrt(d[:, None]) * sample_765bit_norm(rng, cfg, n_syms), c1, c2)
    papr = lambda S: 10.0 * np.log10(np.max(np.abs(S) ** 2, axis=0) / np.mean(np.abs(S) ** 2, axis=0))
    return {
        "n_syms": int(n_syms),
        "unif_afdm_papr_99p9_db": float(np.quantile(papr(s_u), 0.999)),
        "ours_daft_mask_papr_99p9_db": float(np.quantile(papr(s_m), 0.999)),
        "descriptive_only": True,
    }


def run_mutation_test() -> int:
    print("[MUTATION TEST] Verifying startup gates catch broken invariants / helpers (dev seed 19000001)...")
    cfg = build_system(order=8, Q=12, delta=2.0 / 3.0)
    g1_ok = run_gate_g1(cfg, 16, 4.5, seed_g1=19000001, mutate=None)
    assert g1_ok["pass"], f"Clean G1 failed: {g1_ok}"
    for m_name in ("c1_nonzero_ofdm", "corrupt_lag1_dechirp", "break_scale_inv"):
        g1_m = run_gate_g1(cfg, 16, 4.5, seed_g1=19000001, mutate=m_name)
        assert not g1_m["pass"], f"Mutation {m_name} was NOT caught by G1!"
        print(f"  PASS: G1 caught mutation '{m_name}'")
    g2_m = run_gate_g2_ranasinghe_full_psd(19000002, n_trials=4, mutate="break_ranasinghe_dict")
    assert not g2_m["pass"], "Mutation 'break_ranasinghe_dict' was NOT caught by G2!"
    print("  PASS: G2 caught mutation 'break_ranasinghe_dict'")
    # Verify Newcombe Method 10 (3.2445 pp) AND paired Student-t_{n-1} D_0.8 (4.13550 pp) on Sol's exact test vectors!
    a = np.array([1] * (474 + 102) + [0] * (19 + 45))
    b = np.array([1] * 474 + [0] * 102 + [1] * 19 + [0] * 45)
    ci_m10 = newcombe_method10_ci(a, b)
    assert abs(100.0 * ci_m10["hw"] - 3.2445) < 0.0005, f"Newcombe M10 mismatch: {ci_m10}"
    print(f"  PASS: Newcombe Method 10 exact check hw={100*ci_m10['hw']:.4f} pp (target 3.2445 pp)")
    a8 = np.array([1] * (216 + 328) + [0] * (87 + 169))
    b8 = np.array([1] * 216 + [0] * 328 + [1] * 87 + [0] * 169)
    ci_t = paired_ratio_contrast_ci(a8, b8, factor=0.80)
    assert abs(100.0 * ci_t["hw"] - 4.13550) < 0.0005, f"Paired t D_0.8 mismatch: {ci_t}"
    print(f"  PASS: Paired t_799 D_0.8 check hw={100*ci_t['hw']:.5f} pp (target 4.13550 pp)")
    print("[MUTATION TEST] ALL 6 CHECKS PASSED CLEANLY.")
    return 0


# =============================================================================
# 7. Regime Aggregation & Primary Verdict Evaluator (Full Redline-5 Coverage)
# =============================================================================

def run_regime(
    pool: ProcessPoolExecutor,
    base_seed: int,
    n_scenes: int,
    M_c: int,
    pwrs_db: list[float],
    swerling2: bool,
    s2_t: float,
    ell_max: int,
    nu_max: float,
    taus: dict,
) -> dict:
    tasks = [
        (base_seed + i, base_seed + 50000 + i, M_c, pwrs_db, swerling2, s2_t, ell_max, nu_max, taus)
        for i in range(n_scenes)
    ]
    rows = list(pool.map(_scene_worker, tasks))
    arms = ["Ours_Banded", "Abl_DiagOnly", "Abl_HomoBanded", "Rival_TDCov", "Rival_OFDM_c1_0", "Abl_NoMask"]
    P_t = len(pwrs_db)

    wt_vec = {a: np.array([r[a][1] for r in rows], dtype=int) for a in arms}
    fa_any_vec = {a: np.array([r[a][2] for r in rows], dtype=int) for a in arms}
    summary = {}
    for a in arms:
        all_h = sum(r[a][0] for r in rows)
        fa_sum = sum(r[a][3] for r in rows)
        ne = [e for r in rows for e in r[a][4]]
        ms_list = [r[a][5] for r in rows if r[a][5] > 0.0]
        summary[a] = {
            "all_target_hit_rate": all_h / float(n_scenes * P_t),
            "wt_pd": wilson_ci(int(np.sum(wt_vec[a])), n_scenes),
            "any_fa": wilson_ci(int(np.sum(fa_any_vec[a])), n_scenes),
            "avg_fa_per_scene": fa_sum / float(n_scenes),
            "rmse_nu_matched": float(math.sqrt(sum(e * e for e in ne) / len(ne))) if ne else None,
            "mean_ms": float(np.mean(ms_list)) if ms_list else None,
        }

    paired = {}
    for rv in ["Abl_DiagOnly", "Abl_HomoBanded", "Rival_TDCov", "Rival_OFDM_c1_0", "Abl_NoMask"]:
        paired[f"Ours_minus_{rv}"] = newcombe_method10_ci(wt_vec["Ours_Banded"], wt_vec[rv])

    bidir = {}
    for abl in ["Abl_DiagOnly", "Abl_HomoBanded", "Abl_NoMask"]:
        bidir[f"D08_{abl}"] = paired_ratio_contrast_ci(wt_vec["Ours_Banded"], wt_vec[abl], factor=0.80)

    return {
        "n_scenes": int(n_scenes),
        "pwrs_db": pwrs_db,
        "swerling2": bool(swerling2),
        "arms": summary,
        "paired_wt_pd": paired,
        "bidirectional_D08": bidir,
    }


def check_redline5_lower(est: float, lo: float, hw: float, thresh: float) -> dict:
    margin = est - thresh
    hw_ok = (margin > 0.0) and (hw <= 0.25 * margin)
    ci_ok = lo > thresh
    return {
        "est": float(est), "lo": float(lo), "hw": float(hw), "thresh": float(thresh),
        "margin": float(margin), "max_allowed_hw": float(0.25 * max(margin, 0.0)),
        "ci_ok": bool(ci_ok), "hw_ok": bool(hw_ok), "pass": bool(ci_ok and hw_ok),
    }


def check_redline5_upper(est: float, hi: float, hw: float, thresh: float) -> dict:
    margin = thresh - est
    hw_ok = (margin > 0.0) and (hw <= 0.25 * margin)
    ci_ok = hi < thresh
    return {
        "est": float(est), "hi": float(hi), "hw": float(hw), "thresh": float(thresh),
        "margin": float(margin), "max_allowed_hw": float(0.25 * max(margin, 0.0)),
        "ci_ok": bool(ci_ok), "hw_ok": bool(hw_ok), "pass": bool(ci_ok and hw_ok),
    }


def evaluate_primary_verdict(reg1: dict, reg2: dict, gates_ok: bool) -> dict:
    def eval_reg(reg: dict, th_wt: float, th_ofdm: float, th_nomask: float, th_diag: float, th_homo: float, th_td: float) -> dict:
        ours_wt = reg["arms"]["Ours_Banded"]["wt_pd"]
        ours_fa = reg["arms"]["Ours_Banded"]["any_fa"]
        p_ofdm = reg["paired_wt_pd"]["Ours_minus_Rival_OFDM_c1_0"]
        p_nm = reg["paired_wt_pd"]["Ours_minus_Abl_NoMask"]
        p_diag = reg["paired_wt_pd"]["Ours_minus_Abl_DiagOnly"]
        p_homo = reg["paired_wt_pd"]["Ours_minus_Abl_HomoBanded"]
        p_td = reg["paired_wt_pd"]["Ours_minus_Rival_TDCov"]
        d_diag = reg["bidirectional_D08"]["D08_Abl_DiagOnly"]
        d_homo = reg["bidirectional_D08"]["D08_Abl_HomoBanded"]
        d_nm = reg["bidirectional_D08"]["D08_Abl_NoMask"]

        checks = {
            "ours_wt_pd": check_redline5_lower(ours_wt["est"], ours_wt["lo"], ours_wt["hw"], th_wt),
            "ours_any_fa_lt_8pct": check_redline5_upper(ours_fa["est"], ours_fa["hi"], ours_fa["hw"], 0.08),
            "ours_minus_ofdm": check_redline5_lower(p_ofdm["diff"], p_ofdm["lo"], p_ofdm["hw"], th_ofdm),
            "ours_minus_nomask": check_redline5_lower(p_nm["diff"], p_nm["lo"], p_nm["hw"], th_nomask),
            "ours_minus_diag": check_redline5_lower(p_diag["diff"], p_diag["lo"], p_diag["hw"], th_diag),
            "ours_minus_homo": check_redline5_lower(p_homo["diff"], p_homo["lo"], p_homo["hw"], th_homo),
            "ours_minus_tdcov": check_redline5_lower(p_td["diff"], p_td["lo"], p_td["hw"], th_td),
            "bidir_D08_diag_gt_0": check_redline5_lower(d_diag["est"], d_diag["lo"], d_diag["hw"], 0.0),
            "bidir_D08_homo_gt_0": check_redline5_lower(d_homo["est"], d_homo["lo"], d_homo["hw"], 0.0),
            "bidir_D08_nomask_gt_0": check_redline5_lower(d_nm["est"], d_nm["lo"], d_nm["hw"], 0.0),
        }
        return {"pass": bool(all(c["pass"] for c in checks.values())), "checks": checks}

    p1 = eval_reg(reg1, th_wt=0.74, th_ofdm=0.60, th_nomask=0.60, th_diag=0.15, th_homo=0.20, th_td=0.12)
    p2 = eval_reg(reg2, th_wt=0.55, th_ofdm=0.45, th_nomask=0.45, th_diag=0.12, th_homo=0.12, th_td=-0.10)
    pass_primary = bool(gates_ok and p1["pass"] and p2["pass"])
    return {"PASS_PRIMARY": pass_primary, "P1_Reg1": p1, "P2_Reg2": p2}


# =============================================================================
# 8. Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Formal L2 for I-20261126-m04")
    mode_grp = parser.add_mutually_exclusive_group()
    mode_grp.add_argument("--smoke", action="store_true", help="Fast smoke run with isolated smoke seeds (2124000000+)")
    mode_grp.add_argument("--formal", action="store_true", help="Formal L2 run with virgin formal seeds (2034000000+)")
    parser.add_argument("--mutation-test", action="store_true", help="Run startup-gate mutation tests and exit")
    parser.add_argument("--workers", type=int, default=4, help="Parallel worker count (strictly <= 8)")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    print(f"[ENV] sys.executable = {sys.executable}", flush=True)
    if args.mutation_test:
        sys.exit(run_mutation_test())

    workers = max(1, min(8, int(args.workers)))
    mode = "smoke" if args.smoke else "formal"
    if args.out is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        args.out = os.path.join(base_dir, f"out_m_r13_m04_{mode}.json")

    seed_base = 2124000000 if args.smoke else 2034000000
    n_g2 = 8 if args.smoke else 64
    n_g2b = 8 if args.smoke else 32
    n_cal = 60 if args.smoke else 600
    n_ver = 60 if args.smoke else 400
    n_h1r = 20 if args.smoke else 160
    n_comm = 20 if args.smoke else 200
    n_formal = 24 if args.smoke else 800
    n_diag = 12 if args.smoke else 128

    t_start = time.perf_counter()
    cfg = build_system(order=8, Q=12, delta=2.0 / 3.0)
    ell_max, nu_max = 16, 4.5
    M_c = 128
    s2_t = 10.0 ** (-1.5)

    out_doc = {
        "card": "I-20261126-m04",
        "mode": mode,
        "python": sys.executable,
        "workers": workers,
        "seed_base": seed_base,
        "config": {"N": cfg["N"], "Q": cfg["Q"], "delta": cfg["delta"], "bits_per_block": 3 * cfg["N"],
                   "M": M_c, "ell_max": ell_max, "nu_max": nu_max, "P_max": 5, "snr_dom_db": 15.0},
        "gates": {},
        "GATES_OK": False,
        "PASS_PRIMARY": False,
    }

    print(f"[START] mode={mode}, workers={workers}, seed_base={seed_base}, out={args.out}", flush=True)

    # [1/8] Startup Gates G1 & G2
    print("[1/8] Running G1 (algebraic/scale invariants) & G2 (Redline-1 Full GxG PSD Ranasinghe N=64)...", flush=True)
    g1 = run_gate_g1(cfg, ell_max, nu_max, seed_g1=seed_base + 10000)
    g2 = run_gate_g2_ranasinghe_full_psd(seed_base + 100000, n_trials=n_g2)
    out_doc["gates"]["G1_Algebraic_And_Scale"] = g1
    out_doc["gates"]["G2_Redline1_Ranasinghe_N64"] = g2
    print(f"  G1 pass={g1['pass']} (ofdm={g1['ofdm_full_rel']:.2e}, lag1={g1['err_lag1']:.2e}, scale_b={g1['scale_diff_banded']:.2e})", flush=True)
    print(f"  G2 pass={g2['pass']} (recon={g2['recon_err']:.2e}, sw0_ell={g2['static_sw0_los_row_delay_hits']}/{g2['n_trials']}, "
          f"r_rmse={g2['static_sw0_range_rmse_m']:.2f}m, v_rmse={g2['static_sw0_vel_rmse_ms']:.2f}m/s, "
          f"sw0_unanch={g2['static_sw0_unanch_top2_recovery']:.3f}, sw2_ell={g2['swerling2_full_psd_los_row_delay_recovery']:.3f})", flush=True)

    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(8, 12, 2.0 / 3.0)) as pool:
        # [2/8] Startup Gate G3: Independent H0_cal=600 -> H0_ver=400 exact rank r=592 (0-based 591)
        print(f"[2/8] Running G3 (H0_cal={n_cal} -> H0_ver={n_ver} independent calibration across 5 arms)...", flush=True)
        cal_rows = list(pool.map(_h0_worker, [(seed_base + 200000 + i, M_c, ell_max, nu_max) for i in range(n_cal)]))
        ver_rows = list(pool.map(_h0_worker, [(seed_base + 250000 + i, M_c, ell_max, nu_max) for i in range(n_ver)]))
        arm_names_cal = ["Ours_Banded", "Abl_DiagOnly", "Abl_HomoBanded", "Rival_TDCov", "Rival_OFDM_c1_0"]
        # Exact rank r=592 (0-based 591) for n_cal=600 => marginal Pfa = (601 - 592)/601 = 9/601 = 1.4975%
        idx_os = 591 if not args.smoke else min(n_cal - 1, int(math.floor((n_cal + 1) * 0.985)) - 1)
        taus = {}
        ver_stats = {}
        max_ver_fa = 18 if not args.smoke else max(4, int(math.ceil(0.08 * n_ver)))
        g3_pass = True
        for col, a in enumerate(arm_names_cal):
            arr_c = sorted(r[col] for r in cal_rows)
            tau_a = float(arr_c[idx_os])
            taus[a] = tau_a
            k_fa = sum(1 for r in ver_rows if r[col] > tau_a)
            ok_a = k_fa <= max_ver_fa
            g3_pass = g3_pass and ok_a
            ver_stats[a] = {"tau": tau_a, "order_stat_rank_1based": idx_os + 1, "h0_ver_fa": wilson_ci(k_fa, n_ver), "pass": bool(ok_a)}
            print(f"  G3 {a:16s}: tau={tau_a:6.2f}, H0_ver={k_fa}/{n_ver} ({100*k_fa/n_ver:.2f}%), pass={ok_a}", flush=True)
        out_doc["gates"]["G3_Pure_H0_Pfa_Control"] = {
            "pass": bool(g3_pass), "n_cal": n_cal, "n_ver": n_ver, "order_stat_rank_1based": idx_os + 1,
            "marginal_pfa_target": float((n_cal + 1 - (idx_os + 1)) / float(n_cal + 1)),
            "max_ver_fa": max_ver_fa, "arms": ver_stats,
        }

        # [3/8] Startup Gate G2b: 32-Scene High-SNR Static Convergence Health Check
        print(f"[3/8] Running G2b (High-SNR static convergence check, n={n_g2b})...", flush=True)
        g2b = run_gate_g2b_static_convergence(cfg, ell_max, nu_max, taus, seed_base + 150000, n_trials=n_g2b)
        out_doc["gates"]["G2b_Static_Convergence"] = g2b
        print(f"  G2b pass={g2b['pass']} (Ours={g2b['ours_banded_hits']}/{n_g2b}, RMSE={g2b['ours_banded_rmse_nu']:.5f}; "
              f"TDCov={g2b['rival_tdcov_hits']}/{n_g2b}, RMSE={g2b['rival_tdcov_rmse_nu']:.5f})", flush=True)

        # [4/8] Startup Gate G4: Independent H1-residual extra-FA check
        print(f"[4/8] Running G4 (H1_resid_P1 & H1_resid_P2, n={n_h1r} each)...", flush=True)
        h1r_out = {}
        g4_pass = True
        max_h1r_fa = int(math.floor(0.05 * n_h1r)) if not args.smoke else max(2, int(math.ceil(0.10 * n_h1r)))
        for lbl, pwrs_r, s_off in [("H1_resid_P1", [1.0], 300000), ("H1_resid_P2", [1.0, 0.316227766], 350000)]:
            rows_r = list(pool.map(_h1_resid_worker, [(seed_base + s_off + i, M_c, pwrs_r, s2_t, ell_max, nu_max, taus) for i in range(n_h1r)]))
            res_r = {}
            for a in ["Ours_Banded", "Abl_DiagOnly", "Abl_HomoBanded", "Rival_TDCov", "Rival_OFDM_c1_0", "Abl_NoMask"]:
                k_any = sum(r[a][0] for r in rows_r)
                tot_fa = sum(r[a][1] for r in rows_r)
                res_r[a] = {"any_fa": wilson_ci(k_any, n_h1r), "avg_fa": tot_fa / float(n_h1r)}
            ok_r = res_r["Ours_Banded"]["any_fa"]["k"] <= max_h1r_fa
            g4_pass = g4_pass and ok_r
            h1r_out[lbl] = {"pass": bool(ok_r), "max_allowed_ours_k": max_h1r_fa, "arms": res_r}
            print(f"  G4 {lbl}: Ours={res_r['Ours_Banded']['any_fa']['k']}/{n_h1r} (pass={ok_r}), "
                  f"Diag={res_r['Abl_DiagOnly']['any_fa']['k']}/{n_h1r}, Homo={res_r['Abl_HomoBanded']['any_fa']['k']}/{n_h1r}, "
                  f"TDCov={res_r['Rival_TDCov']['any_fa']['k']}/{n_h1r}, OFDM={res_r['Rival_OFDM_c1_0']['any_fa']['k']}/{n_h1r}, NoMask={res_r['Abl_NoMask']['any_fa']['k']}/{n_h1r}", flush=True)
        out_doc["gates"]["G4_H1_Residual_ExtraFA"] = {"pass": bool(g4_pass), "regimes": h1r_out}

        # [5/8] Startup Gate G5: Exact 765-bit Equal-Payload Gray-BER Non-Inferiority
        print(f"[5/8] Running G5 (Exact 765-bit Unbiased-LMMSE Gray BER, n={n_comm})...", flush=True)
        g5 = run_gate_g5_comm_ber(cfg, seed_base + 400000, n_trials=n_comm)
        out_doc["gates"]["G5_Comm_GrayBER_NonInf"] = g5
        for sk, sv in g5["by_snr"].items():
            print(f"  G5 {sk}: 8PSK={sv['gray_8psk_ber']:.5f}, 8QAM={sv['gray_8qam_ber']:.5f}, "
                  f"Ours(D)={sv['ours_D_lmmse_ber']:.5f}, Ours(I)={sv['ours_I_lmmse_ber']:.5f}, pass={sv['non_inferior_pass']}", flush=True)

        gates_ok = bool(g1["pass"] and g2["pass"] and g2b["pass"] and g3_pass and g4_pass and g5["pass"])
        out_doc["GATES_OK"] = gates_ok
        if not gates_ok:
            print("[ABORT] GATES_OK == False! Stopping immediately without running formal arms.", flush=True)
            out_doc["aborted_early"] = True
            out_doc["elapsed_sec"] = float(time.perf_counter() - t_start)
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(out_doc, f, indent=2, allow_nan=False)
            sys.exit(2)

        # [6/8] Formal Primary Regime Reg1 (P=2: 0, -13.5 dB, Swerling-II, N_formal=800)
        print(f"[6/8] Running Formal Reg1 (P=2: 0, -13.5 dB, SwII, N_formal={n_formal})...", flush=True)
        reg1 = run_regime(pool, seed_base + 500000, n_formal, M_c, [0.0, -13.5], True, s2_t, ell_max, nu_max, taus)
        out_doc["Reg1_P2_SwII"] = reg1
        for a, sv in reg1["arms"].items():
            print(f"  Reg1 {a:16s}: WT-Pd={100*sv['wt_pd']['est']:5.1f}% [{100*sv['wt_pd']['lo']:4.1f},{100*sv['wt_pd']['hi']:4.1f}], anyFA={100*sv['any_fa']['est']:4.1f}%", flush=True)

        # [7/8] Formal Primary Regime Reg2 (P=3: 0, -5, -12.5 dB, Swerling-II, N_formal=800)
        print(f"[7/8] Running Formal Reg2 (P=3: 0, -5, -12.5 dB, SwII, N_formal={n_formal})...", flush=True)
        reg2 = run_regime(pool, seed_base + 600000, n_formal, M_c, [0.0, -5.0, -12.5], True, s2_t, ell_max, nu_max, taus)
        out_doc["Reg2_P3_SwII"] = reg2
        for a, sv in reg2["arms"].items():
            print(f"  Reg2 {a:16s}: WT-Pd={100*sv['wt_pd']['est']:5.1f}% [{100*sv['wt_pd']['lo']:4.1f},{100*sv['wt_pd']['hi']:4.1f}], anyFA={100*sv['any_fa']['est']:4.1f}%", flush=True)

        # [8/8] Secondary Diagnostics
        print(f"[8/8] Running Secondary Diagnostics (Sw0+RandLO n={n_diag}, N=63 Full-PSD Ranasinghe n={n_diag}, PAPR)...", flush=True)
        diag_sw0 = run_regime(pool, seed_base + 700000, n_diag, M_c, [0.0, -5.0, -12.5], False, s2_t, ell_max, nu_max, taus)
        diag_n63 = run_diag_ranasinghe_n63(seed_base + 800000, n_trials=n_diag)
        diag_papr = run_diag_papr(cfg, seed_base + 900000, n_syms=500 if args.smoke else 2000)
        out_doc["diagnostics"] = {
            "Diag_Sw0_RandLO": diag_sw0,
            "Diag_Ranasinghe_N63_Paired": diag_n63,
            "Diag_PAPR": diag_papr,
        }

    verdict = evaluate_primary_verdict(reg1, reg2, gates_ok)
    out_doc["verdict"] = verdict
    out_doc["PASS_PRIMARY"] = verdict["PASS_PRIMARY"]
    out_doc["elapsed_sec"] = float(time.perf_counter() - t_start)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, indent=2, allow_nan=False)

    print("\n" + "=" * 80, flush=True)
    print(f"[DONE] mode={mode} | GATES_OK={out_doc['GATES_OK']} | PASS_PRIMARY={out_doc['PASS_PRIMARY']} | elapsed={out_doc['elapsed_sec']:.1f}s", flush=True)
    print(f"  Output saved to: {args.out}", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
