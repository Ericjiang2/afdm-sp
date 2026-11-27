#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C7 Steelman Teardown (`td_m_p1b_c7_lna_lowbit_aci.py`):
Cascaded Nonlinear RF LNA Compression (AM/AM + AM/PM + Memory) + 2-Bit Low-Resolution ADC
under Strong UNKNOWN Adjacent-Channel / Co-Channel Blocker in Doubly-Dispersive MIMO.

Literature Anchors (2024-2026):
  - Shipra, Wang, Eriksson, IEEE IMS 2026 (Chalmers pub 553228): Nonlinear RF RX under strong interference
  - Mehrotra, Srivastava, Jagannatham, Hanzo, IEEE TCOM 2025 (10.1109/tcomm.2024.3502682): MIMO-OTFS low-res ADCs
  - Jarraya, Mezghani, Bellili, IEEE TWC 2026 (10.1109/twc.2025.3630565): Correlated low-res ADC MUD

Exact Physical Chain (per gpt-6.2-sol Call 2 C7 prescription):
  - Oversampled wideband MIMO receiver (`N_r = 8..12` antennas, `Q_os = 2`, `N_sym = 32 -> M_t = 64` wideband samples/ant).
  - Desired doubly-dispersive AFDM/OTFS/SC-FDE user `x` (16-QAM / QPSK) in main band `[-0.25, +0.25] Fs`.
  - Strong UNKNOWN Wideband Adjacent-Channel Blocker `B a` in adjacent band `[+0.27, +0.48] & [-0.48, -0.27] Fs`
    at `+15..+18 dB` stronger than desired user, sweeping blocker **absolute input power** across LNA's P1dB knee!
    Because the blocker is wideband, cross-modulation `|b(t)|^2 s(t)` + gain desensitization lands 100% IN-BAND
    and 3rd-order spectral regrowth `|b(t)|^2 b(t)` splashes directly into the main band!
  - Exact front-end order:
      r_in  = H x + B a + w
      z_lna = f_LNA_mem(r_in)   (Rapp p=1.8 AM/AM + Saleh AM/PM + 2-tap memory, calibrated knee V_sat = 1.0!)
      q     = Q_{2-bit}(z_lna)  (2-bit ADC quantized codewords ONLY observed by digital RX!)

Arms (verbatim per Sol Call 2 C7 prescription):
  1) `Pub_MRC_AQNM_DigLPF`           : Shipra MRC weak baseline + Mehrotra AQNM + digital LPF
  2) `SM_Linear_JointProbit`         : Exact convex linear Joint-Probit on `q = Q(Hx + Ba + w)` (ignoring LNA NL!)
  3) `SM_ProbitRecon_InvLNA_DigLPF`  : Sol's cascade baseline: Bussgang/Probit wideband recon -> analytic LNA^{-1} -> dig LPF!
  4) `SM_EstOOB_LocalWL_Probit`      : Sol's Steelman_S: estimate blocker `b_hat` from OOB quantized samples -> local
                                       widely-linear Jacobian `g1(b_hat) s + g2(b_hat) s^*` around `b_hat` -> Probit!
  5) `SM_Alt_MemLNA_Probit`          : Sol's DEADLIEST Steelman_A: init `(x, a)` from linear Joint-Probit -> alternate
                                       fitting blocker `a` & soft symbols `x` directly on raw 2-bit codewords using the
                                       CALIBRATED memory-LNA forward model (Gauss-Newton on exact Probit log-likelihood)!
  6) `Oracle_SameHW_KnownBlocker`    : Same LNA + same 2-bit ADC codewords, knows exact `H`, LNA map, and blocker `Ba`
                                       (verifies whether raw 2-bit codewords still carry enough threshold-crossing info!)
  7) `Oracle_SameHW_TrueInit_Joint`  : Same LNA + same 2-bit ADC, blocker `a` STILL UNKNOWN, exact calibrated LNA Joint-Probit
                                       initialized near true basin (separates non-convex basin trap from info-theoretic limit!)
  8) `Oracle_LinearLNA_InfBit`       : Linear LNA + infinite-bit ADC with unknown blocker.
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
    b = np.arange(ms); g = b ^ (b >> 1); lut = np.argsort(g); lv = 2 * lut - (ms - 1)
    pts = np.array([lv[i] + 1j * lv[q] for q in range(ms) for i in range(ms)], dtype=np.complex128)
    return pts / math.sqrt(float(np.mean(np.abs(pts) ** 2)))


def daft_mat(N: int, c1: float, c2: float) -> np.ndarray:
    n = np.arange(N, dtype=float); m = np.arange(N, dtype=float)
    W = np.exp(-1j * 2.0 * np.pi * np.outer(m, n) / N) / math.sqrt(N)
    return (np.exp(-1j * 2.0 * np.pi * c2 * (m ** 2))[:, None] * W) * np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))[None, :]


def ula_steer(Nr: int, theta: float) -> np.ndarray:
    return np.exp(1j * math.pi * np.arange(Nr, dtype=float) * math.sin(theta)) / math.sqrt(Nr)


def build_band_basis(M_t: int, bins: np.ndarray) -> np.ndarray:
    F = np.fft.fft(np.eye(M_t)) / math.sqrt(M_t)
    return F.conj().T[:, bins]


def lna_forward_and_wirtinger(r_c: np.ndarray, V_sat: float, Nr: int, M_t: int):
    """
    Calibrated per-antenna 2-tap memory Rapp (p=1.8) + Saleh AM/PM RF LNA:
      u[t] = 0.94 r[t] + (0.08 - 0.05j) r[t-1]
      z[t] = u[t] * g_am(|u[t]|) * exp(j phi_pm(|u[t]|))
    Also returns exact pointwise Wirtinger derivatives (dz/du, dz/du*) for Gauss-Newton & Local-WL!
    """
    R = r_c.reshape(Nr, M_t)
    R_m1 = np.roll(R, 1, axis=1); R_m1[:, 0] = 0.0
    U = 0.94 * R + (0.08 - 0.05j) * R_m1
    mag = np.abs(U)
    p = 1.8
    x = mag / V_sat
    xp = np.power(np.maximum(x, 1e-12), 2.0 * p)
    g_am = np.power(1.0 + xp, -1.0 / (2.0 * p))
    phi_pm = 0.45 * (x ** 2) / (1.0 + 1.0 * (x ** 2))
    G_tot = g_am * np.exp(1j * phi_pm)
    Z = U * G_tot

    # Exact Wirtinger derivatives of F(u) = u * G(|u|):
    #   dF/du   = G(|u|) + 0.5 * |u| * G'(|u|)
    #   dF/du*  = 0.5 * (u^2 / |u|) * G'(|u|)
    # where G'(r) = (g_am'(r) + j g_am(r) phi_pm'(r)) exp(j phi_pm(r))
    # g_am'(r) = - (1/V_sat) * x^(2p-1) * (1 + x^(2p))^(-1/(2p) - 1) = - (g_am / r) * xp / (1 + xp)
    # phi_pm'(r) = 0.45 * (2 x / V_sat) / (1 + x^2)^2 = 0.90 * x^2 / (r * (1 + x^2)^2)
    r_Gprime = G_tot * (-xp / (1.0 + xp) + 1j * (0.90 * (x ** 2) / ((1.0 + x ** 2) ** 2)))
    dF_du = G_tot + 0.5 * r_Gprime
    phase2 = np.where(mag > 1e-12, (U ** 2) / np.maximum(mag ** 2, 1e-12), 0.0)
    dF_du_conj = 0.5 * phase2 * r_Gprime
    return Z.ravel(), dF_du.ravel(), dF_du_conj.ravel()


def lna_memoryless_inverse(z_c: np.ndarray, V_sat: float) -> np.ndarray:
    """Exact analytic inverse of memoryless Rapp (p=1.8) + Saleh AM/PM LNA (clamped safely below saturation!)."""
    mag_z = np.abs(z_c)
    p = 1.8
    # |z| = |u| / (1 + (|u|/V_sat)^(2p))^(1/(2p))  ==>  (|z|/V_sat)^(2p) = x^(2p) / (1 + x^(2p))
    # ==> x^(2p) = y^(2p) / (1 - y^(2p))  (diverges as |z| -> V_sat!)
    y_norm = np.minimum(mag_z / V_sat, 0.94)  # safe clamp against inf blowup at compression knee
    y2p = np.power(y_norm, 2.0 * p)
    x = np.power(y2p / np.maximum(1.0 - y2p, 1e-4), 1.0 / (2.0 * p))
    mag_u = x * V_sat
    phi_pm = 0.45 * (x ** 2) / (1.0 + x ** 2)
    return np.where(mag_z > 1e-12, (z_c / np.maximum(mag_z, 1e-12)) * mag_u * np.exp(-1j * phi_pm), 0.0) / 0.94


def quantize_real(z: np.ndarray, n_bits: int, step: float):
    L = 1 << n_bits
    edges = (np.arange(1, L, dtype=float) - L / 2.0) * step
    midpts = (np.arange(L, dtype=float) - (L - 1) / 2.0) * step
    idx = np.digitize(z, edges)
    q = midpts[idx]
    all_edges = np.concatenate(([-1e9], edges, [1e9]))
    return q, all_edges[idx], all_edges[idx + 1]


def trunc_normal_moments(mu: np.ndarray, var: np.ndarray, lo: np.ndarray, hi: np.ndarray):
    sd = np.sqrt(np.maximum(var, 1e-12))
    a = (lo - mu) / sd; b = (hi - mu) / sd
    flip = a > 3.5
    aw = np.where(flip, -b, a); bw = np.where(flip, -a, b)
    Z = ndtr(bw) - ndtr(aw)
    inv_s2p = 0.3989422804014327
    pa = inv_s2p * np.exp(-0.5 * np.minimum(aw ** 2, 700.0))
    pb = inv_s2p * np.exp(-0.5 * np.minimum(bw ** 2, 700.0))
    safe = Z > 1e-11
    Zs = np.where(safe, Z, 1.0)
    ms = np.where(safe, (pa - pb) / Zs, 0.0)
    apa = np.where(np.abs(aw) > 1e4, 0.0, aw * pa); bpb = np.where(np.abs(bw) > 1e4, 0.0, bw * pb)
    vs = np.where(safe, 1.0 + (apa - bpb) / Zs - ms ** 2, 0.05)
    tm = np.where(bw < -3.0, bw - 1.0 / np.maximum(-bw, 1.0), 0.5 * (np.clip(aw, -10, 10) + np.clip(bw, -10, 10)))
    tv = np.where(bw < -3.0, 1.0 / np.maximum(bw ** 2, 1.0), 0.05)
    mw = np.where(safe, ms, tm); vw = np.clip(np.where(safe, vs, tv), 1e-6, 1.5)
    return mu + sd * np.where(flip, -mw, mw), var * vw


def c2r_vec(z): return np.concatenate([np.real(z), np.imag(z)])
def r2c_vec(zr): n = len(zr) // 2; return zr[:n] + 1j * zr[n:]
def c2r_mat(A): Ar, Ai = np.real(A), np.imag(A); return np.block([[Ar, -Ai], [Ai, Ar]])


def wirtinger_to_real_jac(J1: np.ndarray, J2: np.ndarray) -> np.ndarray:
    """Convert complex widely-linear dz = J1 du + J2 du* to real-valued Jacobian d[Re z; Im z] / d[Re u; Im u]."""
    A = J1 + J2
    B = J2 - J1
    return np.block([
        [np.real(A), np.imag(B)],
        [np.imag(A), np.real(J1 - J2)],
    ])


def build_mem_mat(Nr: int, M_t: int) -> np.ndarray:
    """Block-diagonal 2-tap LNA linear memory operator M_lna: u[t] = 0.94 r[t] + (0.08 - 0.05j) r[t-1]."""
    M1 = 0.94 * np.eye(M_t, dtype=np.complex128)
    for t in range(1, M_t):
        M1[t, t - 1] = 0.08 - 0.05j
    return np.kron(np.eye(Nr, dtype=np.complex128), M1)


def qam_mmse(r, v, const):
    v = np.maximum(np.real(v), 1e-6)
    d2 = np.abs(r[:, None] - const[None, :]) ** 2
    lp = -d2 / (v[:, None] if np.ndim(v) else v); lp -= np.max(lp, axis=1, keepdims=True)
    p = np.exp(lp); p /= np.sum(p, axis=1, keepdims=True)
    xh = p @ const
    return xh, np.maximum(np.real(np.sum(p * (np.abs(const[None, :] - xh[:, None]) ** 2), axis=1)), 1e-7)


def hard_ser(xh, xt, const):
    i1 = np.argmin(np.abs(xh[:, None] - const[None, :]), axis=1)
    i2 = np.argmin(np.abs(xt[:, None] - const[None, :]), axis=1)
    return float(np.mean(i1 != i2))


def nonlinear_lna_probit_gn(
    lo_r, hi_r, H_des, B_aci, M_lna, V_sat, Nr, M_t, sigma_w_sq, var_a, const,
    u_init=None, known_ba_c=None, linear_only=False, n_gn=12, n_ep=4
):
    """
    Exact Gauss-Newton + Discrete QAM EP directly on RAW 2-bit ADC codewords through the CALIBRATED
    memory LNA forward model:
      q = Q( f_LNA_mem( H x + B a + w ) )
    Propagates pre-LNA noise variance locally through |dF/du|^2 + |dF/du*|^2!
    """
    N_sym = H_des.shape[1]
    if known_ba_c is not None:
        K_a = 0
        MH = M_lna @ H_des
        M_mat = MH
    else:
        K_a = B_aci.shape[1]
        M_mat = M_lna @ np.hstack([H_des, B_aci])

    dim_c = N_sym + K_a
    dim_r = 2 * dim_c
    p_prec = np.full(dim_r, 2.0, dtype=float)
    if K_a > 0:
        p_prec[2 * N_sym :] = 2.0 / max(var_a, 1e-6)
    p_mean = np.zeros(dim_r, dtype=float)
    u = np.zeros(dim_r, dtype=float) if u_init is None else u_init.copy()
    I_r = np.eye(dim_r, dtype=float)
    sigma_w_r_sq = sigma_w_sq / 2.0

    # Precompute real matrix if linear_only
    A_lin_r = c2r_mat(H_des if known_ba_c is not None else np.hstack([H_des, B_aci]))

    def eval_fwd_and_jac(u_vec):
        x_c = r2c_vec(u_vec[: 2 * N_sym])
        if known_ba_c is not None:
            r_c = H_des @ x_c + known_ba_c
        else:
            a_c = r2c_vec(u_vec[2 * N_sym :])
            r_c = H_des @ x_c + B_aci @ a_c
        if linear_only:
            mu_r = c2r_vec(r_c)
            J_r = A_lin_r
            v_loc = np.full(len(mu_r), sigma_w_r_sq, dtype=float)
            return mu_r, J_r, v_loc
        z_c, d1, d2 = lna_forward_and_wirtinger(r_c, V_sat, Nr, M_t)
        mu_r = c2r_vec(z_c)
        # Chain rule: dz = diag(d1) M_mat du_c + diag(d2) conj(M_mat) du_c^*
        # Build real Jacobian block-by-block for [x; a]:
        J1_x = d1[:, None] * M_mat[:, :N_sym]
        J2_x = d2[:, None] * np.conj(M_mat[:, :N_sym])
        Jx_r = wirtinger_to_real_jac(J1_x, J2_x)
        if K_a > 0:
            J1_a = d1[:, None] * M_mat[:, N_sym:]
            J2_a = d2[:, None] * np.conj(M_mat[:, N_sym:])
            Ja_r = wirtinger_to_real_jac(J1_a, J2_a)
            J_r = np.hstack([Jx_r, Ja_r])
        else:
            J_r = Jx_r
        # Local pre-LNA thermal noise variance propagated through LNA Jacobian!
        gain_sq = np.maximum(np.abs(d1) ** 2 + np.abs(d2) ** 2, 0.04) * (0.94 ** 2 + 0.08 ** 2 + 0.05 ** 2)
        v_loc = np.concatenate([gain_sq, gain_sq]) * sigma_w_r_sq + 1e-4
        return mu_r, J_r, v_loc

    def nlp_val(mu_r, v_loc, u_vec):
        sd = np.sqrt(v_loc)
        a = (lo_r - mu_r) / sd; b = (hi_r - mu_r) / sd
        flip = a > 3.5
        aw = np.where(flip, -b, a); bw = np.where(flip, -a, b)
        diff = ndtr(bw) - ndtr(aw)
        lp = np.where(diff > 1e-15, np.log(np.maximum(diff, 1e-300)),
                      -0.5 * (bw ** 2) - np.log(np.maximum(-bw, 1.0) * math.sqrt(2.0 * math.pi)))
        return float(-np.sum(lp) + 0.5 * np.sum(p_prec * ((u_vec - p_mean) ** 2)))

    for it in range(n_gn):
        mu_r, J_r, v_loc = eval_fwd_and_jac(u)
        ez, vz = trunc_normal_moments(mu_r, v_loc, lo_r, hi_r)
        g_mu = (mu_r - ez) / v_loc
        h_mu = np.clip((1.0 - vz / v_loc) / v_loc, 1e-6, 1e5)
        grad = J_r.T @ g_mu + p_prec * (u - p_mean)
        H_gn = J_r.T @ (h_mu[:, None] * J_r) + np.diag(p_prec) + 1e-3 * I_r
        d_step = -cho_solve(cho_factor(H_gn, lower=True), grad)
        f0 = nlp_val(mu_r, v_loc, u)
        al = 1.0
        for _ in range(7):
            u_try = u + al * d_step
            mu_t, _, vl_t = eval_fwd_and_jac(u_try)
            if nlp_val(mu_t, vl_t, u_try) <= f0 + 1e-4:
                break
            al *= 0.5
        u = u + al * d_step
        if np.linalg.norm(al * d_step) < 1e-3:
            break

    # Discrete QAM EP refinement on x
    Nx2 = 2 * N_sym
    x_c_hat = r2c_vec(u[:Nx2])
    for _ in range(n_ep):
        mu_r, J_r, v_loc = eval_fwd_and_jac(u)
        ez, vz = trunc_normal_moments(mu_r, v_loc, lo_r, hi_r)
        h_mu = np.clip((1.0 - vz / v_loc) / v_loc, 1e-6, 1e5)
        H_gn = J_r.T @ (h_mu[:, None] * J_r) + np.diag(p_prec) + 1e-3 * I_r
        h_fac = cho_factor(H_gn, lower=True)
        H_inv_x = cho_solve(h_fac, I_r[:, :Nx2])[:Nx2, :]
        vp_x = np.maximum(np.diag(H_inv_x), 1e-6)
        ge = np.maximum(1.0 / vp_x - p_prec[:Nx2], 1e-4)
        he = u[:Nx2] / vp_x - p_prec[:Nx2] * p_mean[:Nx2]
        ve = 1.0 / ge
        rc = r2c_vec(he * ve); vc = ve[:N_sym] + ve[N_sym:Nx2]
        x_c_hat, vhc = qam_mmse(rc, vc, const)
        vhr = np.maximum(np.concatenate([vhc, vhc]) * 0.5, 1e-3)
        gn = 1.0 / vhr - ge; hn = c2r_vec(x_c_hat) / vhr - he
        val = gn > 1e-3
        p_prec[:Nx2] = np.where(val, 0.6 * np.clip(gn, 1e-3, 1e3) + 0.4 * p_prec[:Nx2], p_prec[:Nx2])
        p_mean[:Nx2] = np.where(val, (0.6 * hn + 0.4 * p_prec[:Nx2] * p_mean[:Nx2]) / p_prec[:Nx2], p_mean[:Nx2])
        for _ in range(2):
            mu_r, J_r, v_loc = eval_fwd_and_jac(u)
            ez, vz = trunc_normal_moments(mu_r, v_loc, lo_r, hi_r)
            g_mu = (mu_r - ez) / v_loc
            h_mu = np.clip((1.0 - vz / v_loc) / v_loc, 1e-6, 1e5)
            grad = J_r.T @ g_mu + p_prec * (u - p_mean)
            H_gn = J_r.T @ (h_mu[:, None] * J_r) + np.diag(p_prec) + 1e-3 * I_r
            d_step = -cho_solve(cho_factor(H_gn, lower=True), grad)
            u = u + 0.7 * d_step
    return r2c_vec(u[:Nx2]), u


def run_trial(args):
    seed, name, N_sym, Q_os, Nr, n_bits, snr_db, sir_db, M_aci, v_sat_ratio = args
    rng = np.random.default_rng(seed)
    M_t = N_sym * Q_os
    const = gray_qam(16)
    main_bins = np.concatenate([np.arange(0, N_sym // 2), np.arange(M_t - N_sym // 2, M_t)])
    aci_bins = np.arange(N_sym // 2 + 2, M_t - N_sym // 2 - 2)
    K_aci_f = len(aci_bins)
    B_main_t = build_band_basis(M_t, main_bins)
    B_aci_t = build_band_basis(M_t, aci_bins)

    k_max = 1.5; l_max = 4
    c1 = 5.0 / (2.0 * N_sym)
    U = daft_mat(N_sym, c1, 1.0 / (2.0 * math.pi * N_sym))

    P_des = 3
    delays = np.sort(rng.choice(np.arange(0, l_max + 1), size=P_des, replace=False)); delays[0] = 0
    pdp = np.exp(-0.3 * delays); pdp /= np.sum(pdp)
    gains = (rng.standard_normal(P_des) + 1j * rng.standard_normal(P_des)) * np.sqrt(pdp / 2.0)
    dops = rng.uniform(-k_max, k_max, size=P_des)
    thetas_des = rng.uniform(-0.9, 0.9, size=P_des)

    t_idx = np.arange(M_t, dtype=float)
    S_main = math.sqrt(Q_os) * (B_main_t @ U.conj().T)
    H_des = np.zeros((Nr * M_t, N_sym), dtype=np.complex128)
    for p in range(P_des):
        a_r = ula_steer(Nr, thetas_des[p]) * math.sqrt(Nr)
        S_del = np.roll(S_main, int(delays[p] * Q_os), axis=0)
        dop_vec = np.exp(1j * 2.0 * np.pi * dops[p] * t_idx / float(M_t))
        H_p_t = gains[p] * (dop_vec[:, None] * S_del)
        for r_i in range(Nr):
            H_des[r_i * M_t : (r_i + 1) * M_t, :] += a_r[r_i] * H_p_t

    thetas_aci = np.zeros(M_aci, dtype=float)
    thetas_aci[0] = np.clip(thetas_des[0] + rng.uniform(-0.15, 0.15), -1.1, 1.1)
    for m in range(1, M_aci):
        thetas_aci[m] = rng.uniform(-1.0, 1.0)

    P_aci_tot = 10.0 ** (-sir_db / 10.0)
    var_a = P_aci_tot / float(M_aci)
    B_aci = np.zeros((Nr * M_t, M_aci * K_aci_f), dtype=np.complex128)
    scale_f = math.sqrt(float(M_t) / float(K_aci_f))
    for m in range(M_aci):
        a_r = ula_steer(Nr, thetas_aci[m]) * math.sqrt(Nr)
        for r_i in range(Nr):
            B_aci[r_i * M_t : (r_i + 1) * M_t, m * K_aci_f : (m + 1) * K_aci_f] = a_r[r_i] * scale_f * B_aci_t

    x_true = const[rng.integers(0, len(const), size=N_sym)]
    a_true = (rng.standard_normal(M_aci * K_aci_f) + 1j * rng.standard_normal(M_aci * K_aci_f)) * math.sqrt(var_a / 2.0)
    sigma_w_sq = 10.0 ** (-snr_db / 10.0)
    w = (rng.standard_normal(Nr * M_t) + 1j * rng.standard_normal(Nr * M_t)) * math.sqrt(sigma_w_sq / 2.0)

    r_aci = B_aci @ a_true
    r_in = H_des @ x_true + r_aci + w
    # LNA saturation knee relative to RMS input amplitude (v_sat_ratio = V_sat / RMS(r_in)):
    #   v_sat_ratio ~ 1.1 - 1.5 drives LNA right across its 1 dB compression point P1dB!
    rms_in = math.sqrt(1.0 + P_aci_tot + sigma_w_sq)
    V_sat = v_sat_ratio * rms_in

    z_lna, _, _ = lna_forward_and_wirtinger(r_in, V_sat, Nr, M_t)
    std_z_r = float(np.std(c2r_vec(z_lna)))
    step = 0.78 * std_z_r  # optimal 2-bit step for compressed LNA output
    q_r, lo_r, hi_r = quantize_real(c2r_vec(z_lna), n_bits, step)
    q_c = r2c_vec(q_r)
    M_lna = build_mem_mat(Nr, M_t)

    P_lpf_1 = B_main_t @ B_main_t.conj().T
    def apply_lpf(v):
        o = np.zeros_like(v)
        for r_i in range(Nr):
            sl = slice(r_i * M_t, (r_i + 1) * M_t)
            o[sl] = P_lpf_1 @ v[sl]
        return o

    # Also build blind estimated OOB subspace B_aci_est for realistic Steelman
    Q_oob = q_c.reshape(Nr, M_t) @ B_aci_t
    U_svd, _, _ = np.linalg.svd(Q_oob, full_matrices=False)
    U_est = U_svd[:, :M_aci] * math.sqrt(Nr)
    B_aci_est = np.zeros_like(B_aci)
    for m in range(M_aci):
        for r_i in range(Nr):
            B_aci_est[r_i * M_t : (r_i + 1) * M_t, m * K_aci_f : (m + 1) * K_aci_f] = U_est[r_i, m] * scale_f * B_aci_t

    res = {}
    # 1. Pub: MRC/AQNM + Dig LPF
    rho_b = 0.1175; alpha_aq = 1.0 - rho_b
    var_aq = rho_b * (1.0 - rho_b) * (2.0 * std_z_r ** 2) + sigma_w_sq
    H_aq = alpha_aq * 0.75 * H_des
    x_pub = np.linalg.solve(H_aq.conj().T @ H_aq + var_aq * np.eye(N_sym), H_aq.conj().T @ apply_lpf(q_c))
    res["Pub_AQNM_DigLPF"] = hard_ser(x_pub, x_true, const)

    # 2. SM1: Linear Joint-Probit ignoring LNA compression (with known B_aci!)
    x_lin_p, u_lin_p = nonlinear_lna_probit_gn(lo_r, hi_r, H_des, B_aci, M_lna, V_sat, Nr, M_t, sigma_w_sq, var_a, const, linear_only=True, n_gn=10, n_ep=4)
    res["SM1_Linear_JointProbit"] = hard_ser(x_lin_p, x_true, const)

    # 3. SM2: Sol's cascade baseline: wideband Probit recon -> analytic LNA^{-1} -> Dig LPF -> LMMSE!
    r_inv = lna_memoryless_inverse(q_c, V_sat)
    x_inv = np.linalg.solve(H_des.conj().T @ H_des + max(0.05 * P_aci_tot, sigma_w_sq) * np.eye(N_sym), H_des.conj().T @ apply_lpf(r_inv))
    res["SM2_InvLNA_DigLPF"] = hard_ser(x_inv, x_true, const)

    # 4. SM3: Sol's Steelman_S: OOB estimated subspace + calibrated memory-LNA Joint Probit GN!
    _, u_lin_est = nonlinear_lna_probit_gn(lo_r, hi_r, H_des, B_aci_est, M_lna, V_sat, Nr, M_t, sigma_w_sq, var_a, const, linear_only=True, n_gn=8, n_ep=0)
    x_sm_est, _ = nonlinear_lna_probit_gn(lo_r, hi_r, H_des, B_aci_est, M_lna, V_sat, Nr, M_t, sigma_w_sq, var_a, const, u_init=u_lin_est, linear_only=False, n_gn=12, n_ep=4)
    res["SM3_EstB_CalMemLNA_Probit"] = hard_ser(x_sm_est, x_true, const)

    # 5. SM4: Sol's DEADLIEST Steelman_A: Known B_aci + linear init -> Calibrated Memory-LNA Joint Probit GN+EP!
    x_sm_cal, _ = nonlinear_lna_probit_gn(lo_r, hi_r, H_des, B_aci, M_lna, V_sat, Nr, M_t, sigma_w_sq, var_a, const, u_init=u_lin_p, linear_only=False, n_gn=12, n_ep=4)
    res["SM4_KnownB_CalMemLNA_Probit"] = hard_ser(x_sm_cal, x_true, const)

    # 6. Oracle_SameHW_KnownBlocker: Same LNA + same 2-bit ADC, exact blocker Ba known!
    x_or_kb, _ = nonlinear_lna_probit_gn(lo_r, hi_r, H_des, B_aci, M_lna, V_sat, Nr, M_t, sigma_w_sq, var_a, const, known_ba_c=r_aci, linear_only=False, n_gn=12, n_ep=5)
    res["Oracle_SameHW_KnownBlocker"] = hard_ser(x_or_kb, x_true, const)

    # 7. Oracle_SameHW_TrueInit_Joint: Same LNA + same 2-bit ADC, blocker a STILL UNKNOWN, initialized near true basin!
    u_true = np.concatenate([c2r_vec(x_true), c2r_vec(a_true)])
    x_or_ti, _ = nonlinear_lna_probit_gn(lo_r, hi_r, H_des, B_aci, M_lna, V_sat, Nr, M_t, sigma_w_sq, var_a, const, u_init=u_true, linear_only=False, n_gn=10, n_ep=4)
    res["Oracle_SameHW_TrueInitJoint"] = hard_ser(x_or_ti, x_true, const)

    # 8. Oracle_LinearLNA_InfBit
    x_inf = np.linalg.solve(H_des.conj().T @ H_des + sigma_w_sq * np.eye(N_sym), H_des.conj().T @ apply_lpf(r_in))
    res["Oracle_LinearLNA_InfBit"] = hard_ser(x_inf, x_true, const)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c7_lna_lowbit_aci.json")
    args = ap.parse_args()
    t0 = time.time()

    configs = [
        # (name, N_sym, Q_os, Nr, n_bits, snr_db, sir_db, M_aci, v_sat_ratio)
        ("R1_2bit_Nr12_SIRm15_Knee1p4", 32, 2, 12, 2, 20.0, -15.0, 2, 1.4),
        ("R2_2bit_Nr12_SIRm15_HardKnee1p0", 32, 2, 12, 2, 20.0, -15.0, 2, 1.0),
        ("R3_2bit_Nr16_SIRm18_Knee1p2", 32, 2, 16, 2, 20.0, -18.0, 2, 1.2),
    ]
    summary = {"meta": {"trials": args.trials}, "results": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, cfg in enumerate(configs):
            jobs = [(700000 + i * 1000 + t,) + cfg for t in range(args.trials)]
            outs = list(ex.map(run_trial, jobs))
            agg = {k: {"mean": float(np.mean([o[k] for o in outs])), "se": float(np.std([o[k] for o in outs], ddof=1) / math.sqrt(len(outs)))} for k in outs[0]}
            summary["results"][cfg[0]] = agg
            print(f"\n=== {cfg[0]} (n={args.trials}) ===")
            for k, v in agg.items():
                print(f"  {k:30s}: SER = {v['mean']:.5f} +/- {v['se']:.5f}")
    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to {args.out} in {summary['elapsed_sec']}s.")


if __name__ == "__main__":
    main()
