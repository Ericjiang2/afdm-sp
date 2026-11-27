#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C4 Refined Steelman Teardown (`td_m_p1b_c4_lowbit_aci.py`):
CRITICAL HONEST DECOMPOSITION per gpt-6.2-sol Call 1 warning:
  Separates THREE distinct quantities on the EXACT SAME 2-bit / 1-bit ADC quantized wideband samples:
    1) `SM_EstSubspace_JointProbit`: Realistic Steelman — receiver does NOT know the uncoordinated ACI angles!
       Estimates ACI spatial subspace U_aci from quantized out-of-band sample covariance (SVD of OOB q_c),
       then runs exact convex Newton Joint-Probit + EP!
    2) `SM_KnownSubspace_JointProbit`: Stronger Steelman handed exact `B_aci` (Sol's `r = Hx + Ba + w` joint QVB/MAP!).
    3) `Oracle_SameQuant_ExactMarg` (NON-CHEATING SAME-QUANT UPPER BOUND): Same quantized bits, exact `H` & `B_aci`,
       if ACI is REAL QAM/OFDM (discrete constellation!), tests whether exploiting discrete/non-Gaussian ACI structure
       beats Gaussian-ACI `JointProbit`! AND compares against Gaussian-ACI `Oracle_SameQuant_KnownACI` (genie realization)
       and `Oracle_InfBit_UnknownACI` (infinite-bit ADC)!
  This immediately answers Sol's lethal question:
    - If Gaussian ACI: `SM_KnownSubspace_JointProbit` already solves the exact convex MAP for Gaussian `a`; any remaining
      gap to `KnownACI` is purely information-theoretic unrecoverable uncertainty of random Gaussian `a`, UNLESS either
      (i) ACI angles are unknown (`EstSubspace` gap!) OR (ii) ACI is real non-Gaussian QAM/OFDM/chirp blocker!
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.special import ndtr


def gray_qam(M: int) -> np.ndarray:
    ms = int(round(math.sqrt(M)))
    b = np.arange(ms)
    g = b ^ (b >> 1)
    lut = np.argsort(g)
    lv = 2 * lut - (ms - 1)
    pts = np.array([lv[i] + 1j * lv[q] for q in range(ms) for i in range(ms)], dtype=np.complex128)
    return pts / math.sqrt(float(np.mean(np.abs(pts) ** 2)))


def daft_mat(N: int, c1: float, c2: float) -> np.ndarray:
    n = np.arange(N, dtype=float)
    m = np.arange(N, dtype=float)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (m ** 2))
    W = np.exp(-1j * 2.0 * np.pi * np.outer(m, n) / N) / math.sqrt(N)
    return (L2[:, None] * W) * L1[None, :]


def ula_steer(Nr: int, theta: float) -> np.ndarray:
    k = np.arange(Nr, dtype=float)
    return np.exp(1j * math.pi * k * math.sin(theta)) / math.sqrt(Nr)


def build_band_basis(M_t: int, freq_bins: np.ndarray) -> np.ndarray:
    F = np.fft.fft(np.eye(M_t)) / math.sqrt(M_t)
    return F.conj().T[:, freq_bins]


def quantize_real(z: np.ndarray, n_bits: int, step: float):
    L = 1 << n_bits
    edges = (np.arange(1, L, dtype=float) - L / 2.0) * step
    midpts = (np.arange(L, dtype=float) - (L - 1) / 2.0) * step
    idx = np.digitize(z, edges)
    q = midpts[idx]
    all_edges = np.concatenate(([-1e9], edges, [1e9]))
    return idx, q, all_edges[idx], all_edges[idx + 1]


def trunc_normal_moments(mu: np.ndarray, var: np.ndarray, lo: np.ndarray, hi: np.ndarray):
    sd = np.sqrt(np.maximum(var, 1e-12))
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
    return mu + sd * np.where(flip, -mw, mw), var * vw


def c2r_vec(z): return np.concatenate([np.real(z), np.imag(z)])
def r2c_vec(zr): n = len(zr) // 2; return zr[:n] + 1j * zr[n:]
def c2r_mat(A): Ar, Ai = np.real(A), np.imag(A); return np.block([[Ar, -Ai], [Ai, Ar]])


def qam_mmse_denoise(r, v, const):
    v_safe = np.maximum(np.real(v), 1e-6)
    if np.ndim(v_safe) == 0:
        v_safe = np.full(len(r), float(v_safe))
    d2 = np.abs(r[:, None] - const[None, :]) ** 2
    lp = -d2 / v_safe[:, None]; lp -= np.max(lp, axis=1, keepdims=True)
    p = np.exp(lp); p /= np.sum(p, axis=1, keepdims=True)
    xh = p @ const
    vh = np.sum(p * (np.abs(const[None, :] - xh[:, None]) ** 2), axis=1)
    return xh, np.maximum(np.real(vh), 1e-7)


def hard_ser(xh, xt, const):
    i1 = np.argmin(np.abs(xh[:, None] - const[None, :]), axis=1)
    i2 = np.argmin(np.abs(xt[:, None] - const[None, :]), axis=1)
    return float(np.mean(i1 != i2))


def probit_newton_ep(
    lo_r, hi_r, Hr, Br, sigma_w_r_sq, var_a_r, const,
    joint_aci=True, known_ba_r=None, aci_const=None, n_newton=14, n_ep=5
):
    """Exact Convex Damped Newton Probit MAP + EP (supports optional discrete constellation on ACI `a`!)."""
    M_r, Nx2 = Hr.shape
    N = Nx2 // 2
    if known_ba_r is not None:
        lo_eff = lo_r - known_ba_r
        hi_eff = hi_r - known_ba_r
        A_r = Hr
        K_a2 = 0
        v_noise = np.full(M_r, sigma_w_r_sq, dtype=float)
    elif joint_aci and Br is not None:
        lo_eff = lo_r; hi_eff = hi_r
        A_r = np.hstack([Hr, Br])
        K_a2 = Br.shape[1]
        v_noise = np.full(M_r, sigma_w_r_sq, dtype=float)
    else:
        lo_eff = lo_r; hi_eff = hi_r
        A_r = Hr; K_a2 = 0
        aci_diag = np.sum(Br ** 2, axis=1) * var_a_r if Br is not None else 0.0
        v_noise = sigma_w_r_sq + aci_diag

    dim_u = A_r.shape[1]
    prior_inv_var = np.full(dim_u, 2.0, dtype=float)
    if joint_aci and known_ba_r is None and K_a2 > 0:
        prior_inv_var[Nx2:] = 1.0 / max(var_a_r, 1e-6)

    u = np.zeros(dim_u, dtype=float)
    I_u = np.eye(dim_u, dtype=float)
    p_mean = np.zeros(dim_u, dtype=float)
    p_prec = prior_inv_var.copy()

    def nlp(u_vec):
        mu = A_r @ u_vec
        sd = np.sqrt(v_noise)
        a = (lo_eff - mu) / sd; b = (hi_eff - mu) / sd
        flip = a > 3.5
        aw = np.where(flip, -b, a); bw = np.where(flip, -a, b)
        diff = ndtr(bw) - ndtr(aw)
        lp = np.where(diff > 1e-15, np.log(np.maximum(diff, 1e-300)),
                      -0.5 * (bw ** 2) - np.log(np.maximum(-bw, 1.0) * math.sqrt(2.0 * math.pi)))
        return float(-np.sum(lp) + 0.5 * np.sum(p_prec * ((u_vec - p_mean) ** 2)))

    for _ in range(n_newton):
        mu = A_r @ u
        ez, vz = trunc_normal_moments(mu, v_noise, lo_eff, hi_eff)
        g_mu = (mu - ez) / v_noise
        h_mu = np.clip((1.0 - vz / v_noise) / v_noise, 1e-8, 1e6)
        grad = A_r.T @ g_mu + p_prec * (u - p_mean)
        H_mat = A_r.T @ (h_mu[:, None] * A_r) + np.diag(p_prec)
        h_fac = cho_factor(H_mat + 1e-7 * I_u, lower=True)
        sd_step = -cho_solve(h_fac, grad)
        f0 = nlp(u)
        al = 1.0
        for _ in range(8):
            if nlp(u + al * sd_step) <= f0 + 1e-6:
                break
            al *= 0.5
        u = u + al * sd_step
        if np.linalg.norm(al * sd_step) < 1e-4:
            break

    x_c_hat = r2c_vec(u[:Nx2])
    for ep in range(n_ep):
        mu = A_r @ u
        ez, vz = trunc_normal_moments(mu, v_noise, lo_eff, hi_eff)
        h_mu = np.clip((1.0 - vz / v_noise) / v_noise, 1e-8, 1e6)
        H_mat = A_r.T @ (h_mu[:, None] * A_r) + np.diag(p_prec)
        h_fac = cho_factor(H_mat + 1e-7 * I_u, lower=True)
        H_inv_diag = np.maximum(np.diag(cho_solve(h_fac, I_u)), 1e-6)

        # Update discrete QAM prior on x
        v_post_x = H_inv_diag[:Nx2]
        gam_ext = np.maximum(1.0 / v_post_x - p_prec[:Nx2], 1e-4)
        h_ext = u[:Nx2] / v_post_x - p_prec[:Nx2] * p_mean[:Nx2]
        v_ext_r = 1.0 / gam_ext
        r_ext_c = r2c_vec(h_ext * v_ext_r)
        v_ext_c = v_ext_r[:N] + v_ext_r[N:Nx2]
        x_c_hat, v_hat_c = qam_mmse_denoise(r_ext_c, v_ext_c, const)
        v_hat_r = np.maximum(np.concatenate([v_hat_c, v_hat_c]) * 0.5, 1e-3)
        gam_new = 1.0 / v_hat_r - gam_ext
        h_new = c2r_vec(x_c_hat) / v_hat_r - h_ext
        val = gam_new > 1e-3
        p_prec[:Nx2] = np.where(val, 0.6 * np.clip(gam_new, 1e-3, 1e3) + 0.4 * p_prec[:Nx2], p_prec[:Nx2])
        p_mean[:Nx2] = np.where(val, (0.6 * h_new + 0.4 * p_prec[:Nx2] * p_mean[:Nx2]) / p_prec[:Nx2], p_mean[:Nx2])

        # Optional discrete QAM prior on ACI `a` (if aci_const is provided!)
        if aci_const is not None and K_a2 > 0:
            Ka = K_a2 // 2
            v_post_a = H_inv_diag[Nx2:]
            gam_ea = np.maximum(1.0 / v_post_a - p_prec[Nx2:], 1e-4)
            h_ea = u[Nx2:] / v_post_a - p_prec[Nx2:] * p_mean[Nx2:]
            v_ea_r = 1.0 / gam_ea
            r_ea_c = r2c_vec(h_ea * v_ea_r)
            v_ea_c = v_ea_r[:Ka] + v_ea_r[Ka:K_a2]
            a_c_hat, v_ha_c = qam_mmse_denoise(r_ea_c, v_ea_c, aci_const)
            v_ha_r = np.maximum(np.concatenate([v_ha_c, v_ha_c]) * 0.5, 1e-3)
            gn_a = 1.0 / v_ha_r - gam_ea
            hn_a = c2r_vec(a_c_hat) / v_ha_r - h_ea
            va = gn_a > 1e-3
            p_prec[Nx2:] = np.where(va, 0.6 * np.clip(gn_a, 1e-3, 1e3) + 0.4 * p_prec[Nx2:], p_prec[Nx2:])
            p_mean[Nx2:] = np.where(va, (0.6 * hn_a + 0.4 * p_prec[Nx2:] * p_mean[Nx2:]) / p_prec[Nx2:], p_mean[Nx2:])

        for _ in range(3):
            mu = A_r @ u
            ez, vz = trunc_normal_moments(mu, v_noise, lo_eff, hi_eff)
            g_mu = (mu - ez) / v_noise
            h_mu = np.clip((1.0 - vz / v_noise) / v_noise, 1e-8, 1e6)
            grad = A_r.T @ g_mu + p_prec * (u - p_mean)
            H_mat = A_r.T @ (h_mu[:, None] * A_r) + np.diag(p_prec)
            h_fac = cho_factor(H_mat + 1e-7 * I_u, lower=True)
            sd_step = -cho_solve(h_fac, grad)
            f0 = nlp(u)
            al = 1.0
            for _ in range(6):
                if nlp(u + al * sd_step) <= f0 + 1e-6:
                    break
                al *= 0.5
            u = u + al * sd_step
    return x_c_hat


def run_trial(args):
    seed, regime, N_sym, Q_os, N_r, n_bits, snr_db, sir_db, M_aci, aci_type = args
    rng = np.random.default_rng(seed)
    M_t = N_sym * Q_os
    const = gray_qam(4 if n_bits == 1 else 16)
    main_bins = np.concatenate([np.arange(0, N_sym // 2), np.arange(M_t - N_sym // 2, M_t)])
    aci_bins = np.arange(N_sym // 2 + 2, M_t - N_sym // 2 - 2)
    K_aci_f = len(aci_bins)
    B_main_t = build_band_basis(M_t, main_bins)
    B_aci_t = build_band_basis(M_t, aci_bins)

    k_max = 1.5; l_max = 4
    c1 = (2 * math.ceil(k_max) + 1) / (2.0 * N_sym)
    U = daft_mat(N_sym, c1, 1.0 / (2.0 * math.pi * N_sym))

    P_des = 3
    delays = np.sort(rng.choice(np.arange(0, l_max + 1), size=P_des, replace=False)); delays[0] = 0
    pdp = np.exp(-0.3 * delays); pdp /= np.sum(pdp)
    gains = (rng.standard_normal(P_des) + 1j * rng.standard_normal(P_des)) * np.sqrt(pdp / 2.0)
    dops = rng.uniform(-k_max, k_max, size=P_des)
    thetas_des = rng.uniform(-0.9, 0.9, size=P_des)

    t_idx = np.arange(M_t, dtype=float)
    S_main = math.sqrt(Q_os) * (B_main_t @ U.conj().T)
    H_des = np.zeros((N_r * M_t, N_sym), dtype=np.complex128)
    for p in range(P_des):
        a_r = ula_steer(N_r, thetas_des[p]) * math.sqrt(N_r)
        S_del = np.roll(S_main, int(delays[p] * Q_os), axis=0)
        dop_vec = np.exp(1j * 2.0 * np.pi * dops[p] * t_idx / float(M_t))
        H_p_t = gains[p] * (dop_vec[:, None] * S_del)
        for r_i in range(N_r):
            H_des[r_i * M_t : (r_i + 1) * M_t, :] += a_r[r_i] * H_p_t

    thetas_aci = np.zeros(M_aci, dtype=float)
    thetas_aci[0] = np.clip(thetas_des[0] + rng.uniform(-0.15, 0.15), -1.1, 1.1)
    for m in range(1, M_aci):
        thetas_aci[m] = rng.uniform(-1.0, 1.0)

    P_aci_tot = 10.0 ** (-sir_db / 10.0)
    var_a = P_aci_tot / float(M_aci)
    B_aci = np.zeros((N_r * M_t, M_aci * K_aci_f), dtype=np.complex128)
    scale_f = math.sqrt(float(M_t) / float(K_aci_f))
    for m in range(M_aci):
        a_r = ula_steer(N_r, thetas_aci[m]) * math.sqrt(N_r)
        for r_i in range(N_r):
            B_aci[r_i * M_t : (r_i + 1) * M_t, m * K_aci_f : (m + 1) * K_aci_f] = a_r[r_i] * scale_f * B_aci_t

    x_true = const[rng.integers(0, len(const), size=N_sym)]
    if aci_type == "qpsk_ofdm":
        aci_const = gray_qam(4) * math.sqrt(var_a)
        a_true = aci_const[rng.integers(0, len(aci_const), size=M_aci * K_aci_f)]
    else:
        aci_const = None
        a_true = (rng.standard_normal(M_aci * K_aci_f) + 1j * rng.standard_normal(M_aci * K_aci_f)) * math.sqrt(var_a / 2.0)

    sigma_w_sq = 10.0 ** (-snr_db / 10.0)
    w = (rng.standard_normal(N_r * M_t) + 1j * rng.standard_normal(N_r * M_t)) * math.sqrt(sigma_w_sq / 2.0)
    r_aci = B_aci @ a_true
    r_wide = H_des @ x_true + r_aci + w

    Hr = c2r_mat(H_des)
    Br_true = c2r_mat(B_aci)
    r_r = c2r_vec(r_wide)
    ba_r = c2r_vec(r_aci)
    sigma_w_r_sq = sigma_w_sq / 2.0
    var_a_r = var_a / 2.0

    std_tot_r = math.sqrt(0.5 * (1.0 + P_aci_tot + sigma_w_sq))
    step = (0.72 * std_tot_r) if n_bits == 2 else (1.5958 * std_tot_r)
    _, q_r, lo_r, hi_r = quantize_real(r_r, n_bits, step)
    q_c = r2c_vec(q_r)

    # Estimate UNKNOWN ACI spatial subspace U_est (N_r x M_aci) from quantized OOB projection (realistic blind ACI subspace!)
    Q_mat = q_c.reshape(N_r, M_t)
    Q_oob = Q_mat @ B_aci_t  # N_r x K_aci_f
    U_svd, _, _ = np.linalg.svd(Q_oob, full_matrices=False)
    U_est = U_svd[:, :M_aci] * math.sqrt(N_r)
    B_aci_est = np.zeros_like(B_aci)
    for m in range(M_aci):
        for r_i in range(N_r):
            B_aci_est[r_i * M_t : (r_i + 1) * M_t, m * K_aci_f : (m + 1) * K_aci_f] = U_est[r_i, m] * scale_f * B_aci_t
    Br_est = c2r_mat(B_aci_est)

    P_lpf_1 = B_main_t @ B_main_t.conj().T
    def apply_lpf(v):
        o = np.zeros_like(v)
        for r_i in range(N_r):
            sl = slice(r_i * M_t, (r_i + 1) * M_t)
            o[sl] = P_lpf_1 @ v[sl]
        return o

    res = {}
    # 1. Pub AQNM
    rho_b = 0.3634 if n_bits == 1 else 0.1175
    alpha_aq = 1.0 - rho_b
    var_aq = rho_b * (1.0 - rho_b) * (1.0 + P_aci_tot + sigma_w_sq) + (alpha_aq ** 2) * sigma_w_sq
    H_aq = alpha_aq * H_des
    x_aq = np.linalg.solve(H_aq.conj().T @ H_aq + var_aq * np.eye(N_sym), H_aq.conj().T @ apply_lpf(q_c))
    res["Pub_AQNM_DigLPF"] = hard_ser(x_aq, x_true, const)

    # 2. SM_EstSubspace_JointProbit (Realistic blind ACI spatial subspace + Gaussian-a Probit)
    x_estB = probit_newton_ep(lo_r, hi_r, Hr, Br_est, sigma_w_r_sq, var_a_r, const, joint_aci=True, aci_const=None)
    res["SM_EstSubspace_JointProbit"] = hard_ser(x_estB, x_true, const)

    # 3. SM_KnownSubspace_JointProbit (Exact B_aci handed to Steelman, Gaussian-a Probit)
    x_knownB = probit_newton_ep(lo_r, hi_r, Hr, Br_true, sigma_w_r_sq, var_a_r, const, joint_aci=True, aci_const=None)
    res["SM_KnownSubspace_JointProbit"] = hard_ser(x_knownB, x_true, const)

    # 4. If QPSK-OFDM ACI: Exploiting discrete ACI structure (NON-CHEATING SameQuant upper bound!)
    if aci_const is not None:
        x_struct = probit_newton_ep(lo_r, hi_r, Hr, Br_true, sigma_w_r_sq, var_a_r, const, joint_aci=True, aci_const=aci_const)
        res["Struct_DiscreteACI_Probit"] = hard_ser(x_struct, x_true, const)

    # 5. Genie realization Oracle_SameQuant_KnownACI
    x_genie = probit_newton_ep(lo_r, hi_r, Hr, Br_true, sigma_w_r_sq, var_a_r, const, joint_aci=False, known_ba_r=ba_r)
    res["Oracle_SameQuant_KnownACI"] = hard_ser(x_genie, x_true, const)

    # 6. Infinite-bit ADC Oracle
    x_inf = np.linalg.solve(H_des.conj().T @ H_des + sigma_w_sq * np.eye(N_sym), H_des.conj().T @ apply_lpf(r_wide))
    res["Oracle_InfBit_UnknownACI"] = hard_ser(x_inf, x_true, const)

    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c4_lowbit_aci.json")
    args = ap.parse_args()
    t0 = time.time()

    configs = [
        ("R1_2bit_Nr16_SIRm15_GaussACI", 32, 2, 16, 2, 18.0, -15.0, 2, "gaussian"),
        ("R2_2bit_Nr16_SIRm15_QPSK_OFDM_ACI", 32, 2, 16, 2, 18.0, -15.0, 2, "qpsk_ofdm"),
        ("R3_2bit_Nr16_SIRm20_QPSK_OFDM_ACI", 32, 2, 16, 2, 18.0, -20.0, 2, "qpsk_ofdm"),
        ("R4_1bit_Nr16_SIRm15_QPSK_OFDM_ACI", 32, 2, 16, 1, 15.0, -15.0, 2, "qpsk_ofdm"),
    ]
    summary = {"meta": {"trials": args.trials}, "results": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, cfg in enumerate(configs):
            key = cfg[0]
            jobs = [(210000 + i * 1000 + t,) + cfg for t in range(args.trials)]
            outs = list(ex.map(run_trial, jobs))
            agg = {k: {"mean": float(np.mean([o[k] for o in outs])), "se": float(np.std([o[k] for o in outs], ddof=1) / math.sqrt(len(outs)))} for k in outs[0]}
            summary["results"][key] = agg
            print(f"\n=== {key} (n={args.trials}) ===")
            for k, v in agg.items():
                print(f"  {k:30s}: SER = {v['mean']:.5f} +/- {v['se']:.5f}")
    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to {args.out} in {summary['elapsed_sec']}s.")


if __name__ == "__main__":
    main()
