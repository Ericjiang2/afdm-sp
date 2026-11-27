#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C6 Complete Steelman Teardown (`td_m_p1b_c6_tx_bursty_pn.py`):
Transmitter-Side Bursty / Heavy-Tailed Phase Jumps (PLL Loss-of-Lock / VCO Phase Hits)
Interleaved with Doubly-Dispersive Multipath (`y = D_R H D_T s + w`) in AFDM / OTFS / SC-FDE.

Literature Anchors (2024-2026):
  - Cui, Kschischang, Karlsson, Agrell, IEEE TCOM 2026 (10.1109/tcomm.2026.3735724):
    "Channel Estimation and LDPC Decoding for Bursty Phase Noise"
  - Sui, Liu, Musavian, Guan, Yang, IEEE TCOM 2026 (10.1109/tcomm.2026.3701879): TX/RX PN in MIMO-AFDM
  - Colavolpe, Barbieri, Caire, IEEE JSAC 2005: Discrete-Phase-Grid Forward-Backward BCJR
  - Bell (SIAM J. Sci. Comput. 1994): Exact Gauss-Newton <-> IEKS equivalence

Complete Ruthless Steelman Suite (per gpt-6.2-sol Call 2 C6 prescription):
  1) `Ref_Clean_ZeroPN`          : Zero-PN sanity gate (must be 0.00000!)
  2) `Pub_PTRSInterp_Only`       : Standard PTRS interpolation + EP (no jump tracking)
  3) `SM1_Gauss_Bell94_IEKS`     : Stationary Gaussian Lag-IEKS on `H D_T`
  4) `SM2_StepScan_StudentT_IEKS`: 1D per-interval jump-time sweep + Student-t heavy-tailed Lag-IEKS!
  5) `SM3_StepScan_2StateHMM`    : 1D per-interval jump-time sweep + 2-state Markov HMM Lag-IEKS!
  6) `SM4_StepScan_1D_BCJR_Cui26`: 1D per-interval jump-time sweep + Exact Colavolpe/Cui 2-state
                                   Discrete-Phase-Grid Forward-Backward BCJR (Q=32 states)!
  7) `SM_S_EqRate_8DPSK_SC`      : Equal-net-rate differential 8-DPSK on SC-FDE (zero PTRS needed ->
                                   3.0 bpcu vs 3.125 bpcu for 16-QAM w/ 21.9% PTRS; constant modulus!)
  8) `Oracle_BasinMAP_TrueState` : NON-CHEATING same-observation MAP Oracle (knows burst state v_t and
                                   starts in global unwrapped basin phi_true + N(0, 0.20^2), NEVER knows
                                   exact phi_true or data x!)
  9) `Oracle_TruePhi_EP`         : Exact-trajectory upper reference.
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.linalg import cho_factor, cho_solve


def gray_qam(M: int) -> np.ndarray:
    ms = int(round(math.sqrt(M)))
    b = np.arange(ms); g = b ^ (b >> 1); lut = np.argsort(g); lv = 2 * lut - (ms - 1)
    pts = np.array([lv[i] + 1j * lv[q] for q in range(ms) for i in range(ms)], dtype=np.complex128)
    return pts / math.sqrt(float(np.mean(np.abs(pts) ** 2)))


def daft_mat(N: int, c1: float, c2: float) -> np.ndarray:
    n = np.arange(N, dtype=float); m = np.arange(N, dtype=float)
    W = np.exp(-1j * 2.0 * np.pi * np.outer(m, n) / N) / math.sqrt(N)
    return (np.exp(-1j * 2.0 * np.pi * c2 * (m ** 2))[:, None] * W) * np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))[None, :]


def otfs_mat(M_del: int, N_dop: int) -> np.ndarray:
    F_N = np.fft.fft(np.eye(N_dop)) / math.sqrt(N_dop)
    return np.kron(F_N, np.eye(M_del))


def build_multipath_H(N: int, P: int, l_max: int, k_max: float, rng: np.random.Generator, cpp_c1: float = 0.0):
    if P == 4 and l_max == 8:
        delays = np.array([0, 2, 5, 8], dtype=int)
    elif P == 4 and l_max == 12:
        delays = np.array([0, 3, 7, 12], dtype=int)
    else:
        delays = np.sort(rng.choice(np.arange(0, l_max + 1), P, replace=False))
    delays[0] = 0
    pdp = np.array([0.34, 0.28, 0.22, 0.16]) if P == 4 else np.ones(P) / P
    gains = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) * np.sqrt(pdp / 2.0)
    gains = gains / np.maximum(np.linalg.norm(gains), 1e-12)
    dops = rng.uniform(-k_max, k_max, size=P)
    H = np.zeros((N, N), dtype=np.complex128)
    n_idx = np.arange(N, dtype=float)
    for p in range(P):
        lp = int(delays[p]); gp = gains[p]
        ph = np.exp(1j * 2.0 * np.pi * float(dops[p]) * n_idx / float(N))
        for n in range(N):
            m = (n - lp) % N
            cph = np.exp(-1j * 2.0 * np.pi * cpp_c1 * (N * N - 2.0 * N * (lp - n))) if (cpp_c1 != 0.0 and n < lp) else 1.0
            H[n, m] += gp * ph[n] * cph
    return H


def gen_bursty_pn(N: int, sig0_sq: float, sig1_sq: float, duty: float, mean_burst: float, rng: np.random.Generator):
    p10 = 1.0 / float(mean_burst)
    p01 = p10 * duty / max(1.0 - duty, 1e-6)
    z = np.zeros(N, dtype=int)
    dphi = np.zeros(N, dtype=float)
    slew_sign = 1.0
    for n in range(1, N):
        if z[n - 1] == 1:
            z[n] = 0 if rng.random() < p10 else 1
        else:
            z[n] = 1 if rng.random() < p01 else 0
            if z[n] == 1:
                slew_sign = 1.0 if rng.random() < 0.5 else -1.0
        if z[n] == 1:
            dphi[n] = slew_sign * 0.30 + rng.normal(0.0, math.sqrt(sig1_sq))
        else:
            dphi[n] = rng.normal(0.0, math.sqrt(sig0_sq))
    phi = np.cumsum(dphi)
    v_innov = np.where(z == 1, sig1_sq + 0.30 ** 2, sig0_sq)
    return phi, z, v_innov, {"p01": p01, "p10": p10}


def qam_mmse(r, v, const):
    v = np.maximum(np.real(v), 1e-6)
    d2 = np.abs(r[:, None] - const[None, :]) ** 2
    lp = -d2 / (v[:, None] if np.ndim(v) else v); lp -= np.max(lp, axis=1, keepdims=True)
    p = np.exp(lp); p /= np.sum(p, axis=1, keepdims=True)
    xh = p @ const
    vh = np.sum(p * (np.abs(const[None, :] - xh[:, None]) ** 2), axis=1)
    return xh, np.maximum(np.real(vh), 1e-7)


def hard_ser(xh, xt, const):
    i1 = np.argmin(np.abs(xh[:, None] - const[None, :]), axis=1)
    i2 = np.argmin(np.abs(xt[:, None] - const[None, :]), axis=1)
    return float(np.mean(i1 != i2))


def linear_ep_sub(y, A, sigma_w_sq, const, n_iters=6):
    Nd = A.shape[1]
    inv_sw = 1.0 / max(sigma_w_sq, 1e-6)
    AtA = inv_sw * (A.conj().T @ A)
    Aty = inv_sw * (A.conj().T @ y)
    I_Nd = np.eye(Nd, dtype=np.complex128)
    gam_p = np.ones(Nd, dtype=float)
    h_p = np.zeros(Nd, dtype=np.complex128)
    xh = np.zeros(Nd, dtype=np.complex128)
    for it in range(n_iters):
        J = AtA.copy(); J[np.diag_indices(Nd)] += gam_p
        jf = cho_factor(J + 1e-9 * I_Nd, lower=True)
        xp = cho_solve(jf, Aty + h_p)
        vp = np.maximum(np.real(np.diag(cho_solve(jf, I_Nd))), 1e-6)
        ge = np.maximum(1.0 / vp - gam_p, 1e-4)
        he = xp / vp - h_p
        ve = 1.0 / ge
        xh, vh = qam_mmse(he * ve, ve, const)
        vhs = np.maximum(vh, 1e-5)
        gn = 1.0 / vhs - ge; hn = xh / vhs - he
        val = gn > 1e-3
        gc = np.clip(gn, 1e-3, 1e4)
        mn = hn / np.maximum(gn, 1e-12)
        gu = np.where(val, gc, gam_p)
        hu = np.where(val, gc * mn, h_p)
        gam_p = gu if it == 0 else (0.65 * gu + 0.35 * gam_p)
        h_p = hu if it == 0 else (0.65 * hu + 0.35 * h_p)
    return xh


def build_rw_prec(v_innov, anchor_prec=1e4):
    N = len(v_innov)
    P = np.zeros((N, N), dtype=float)
    P[0, 0] += anchor_prec
    inv_v = 1.0 / np.maximum(v_innov[1:], 1e-6)
    for n in range(1, N):
        w = inv_v[n - 1]
        P[n - 1, n - 1] += w; P[n, n] += w; P[n - 1, n] -= w; P[n, n - 1] -= w
    return P


def gn_ieks_phase(y, H, s_hat, phi_t, phi_r, v_t, v_r, sigma_w_sq, pn_mode="tx", n_gn=5):
    N = len(y); inv_sw = 2.0 / max(sigma_w_sq, 1e-5)
    if pn_mode == "dual":
        pt = phi_t.copy(); pr = phi_r.copy()
        Pt = build_rw_prec(v_t, anchor_prec=1e4)  # gauge anchor pt[0] = 0
        Pr = build_rw_prec(v_r, anchor_prec=1e4)
        P_blk = np.zeros((2 * N, 2 * N), dtype=float)
        P_blk[:N, :N] = Pt; P_blk[N:, N:] = Pr
        I2 = 1e-4 * np.eye(2 * N)
        for _ in range(n_gn):
            u = s_hat * np.exp(1j * pt)
            Hu = H @ u
            f = Hu * np.exp(1j * pr)
            r = y - f
            Jt = 1j * (np.exp(1j * pr)[:, None] * (H * u[None, :]))
            Jr = np.diag(1j * f)
            J = np.hstack([Jt, Jr])
            Hess = inv_sw * np.real(J.conj().T @ J) + P_blk + I2
            th = np.concatenate([pt, pr])
            grad = -inv_sw * np.real(J.conj().T @ r) + P_blk @ th
            d = -np.linalg.solve(Hess, grad)
            c0 = 0.5 * inv_sw * float(np.sum(np.abs(r) ** 2)) + 0.5 * float(th @ (P_blk @ th))
            al = 1.0
            for _ in range(6):
                thn = th + al * d
                rn = y - (H @ (s_hat * np.exp(1j * thn[:N]))) * np.exp(1j * thn[N:])
                if 0.5 * inv_sw * float(np.sum(np.abs(rn) ** 2)) + 0.5 * float(thn @ (P_blk @ thn)) <= c0 + 1e-6:
                    break
                al *= 0.5
            pt = pt + al * d[:N]; pr = pr + al * d[N:]
        return pt, pr
    if pn_mode == "tx":
        phi = phi_t.copy(); P = build_rw_prec(v_t)
        for _ in range(n_gn):
            u = s_hat * np.exp(1j * phi); r = y - H @ u
            Jc = 1j * (H * u[None, :])
            Hess = inv_sw * np.real(Jc.conj().T @ Jc) + P + 1e-4 * np.eye(N)
            grad = -inv_sw * np.real(Jc.conj().T @ r) + P @ phi
            d = -np.linalg.solve(Hess, grad)
            c0 = 0.5 * inv_sw * float(np.sum(np.abs(r) ** 2)) + 0.5 * float(phi @ (P @ phi))
            al = 1.0
            for _ in range(6):
                pn = phi + al * d; rn = y - H @ (s_hat * np.exp(1j * pn))
                if 0.5 * inv_sw * float(np.sum(np.abs(rn) ** 2)) + 0.5 * float(pn @ (P @ pn)) <= c0 + 1e-6:
                    break
                al *= 0.5
            phi = phi + al * d
        return phi, phi_r
    else:
        phi = phi_r.copy(); P = build_rw_prec(v_r)
        Hs = H @ s_hat
        for _ in range(n_gn):
            f = Hs * np.exp(1j * phi); r = y - f
            Hess = P.copy(); Hess[np.diag_indices(N)] += inv_sw * (np.abs(f) ** 2) + 1e-4
            grad = -inv_sw * np.real(np.conj(1j * f) * r) + P @ phi
            d = -np.linalg.solve(Hess, grad)
            c0 = 0.5 * inv_sw * float(np.sum(np.abs(r) ** 2)) + 0.5 * float(phi @ (P @ phi))
            al = 1.0
            for _ in range(6):
                pn = phi + al * d; rn = y - Hs * np.exp(1j * pn)
                if 0.5 * inv_sw * float(np.sum(np.abs(rn) ** 2)) + 0.5 * float(pn @ (P @ pn)) <= c0 + 1e-6:
                    break
                al *= 0.5
            phi = phi + al * d
        return phi_t, phi


def hmm_fb_2state(ll0, ll1, p01, p10):
    N = len(ll0); pi1 = p01 / max(p01 + p10, 1e-9); pi0 = 1.0 - pi1
    logT = np.array([[math.log(max(1 - p01, 1e-9)), math.log(max(p01, 1e-9))],
                     [math.log(max(p10, 1e-9)), math.log(max(1 - p10, 1e-9))]])
    la = np.zeros((N, 2)); la[0, 0] = math.log(max(pi0, 1e-9)) + ll0[0]; la[0, 1] = math.log(max(pi1, 1e-9)) + ll1[0]
    for n in range(1, N):
        for j, llj in enumerate((ll0[n], ll1[n])):
            a0 = la[n - 1, 0] + logT[0, j]; a1 = la[n - 1, 1] + logT[1, j]; m = max(a0, a1)
            la[n, j] = m + math.log(math.exp(a0 - m) + math.exp(a1 - m)) + llj
    lb = np.zeros((N, 2))
    for n in range(N - 2, -1, -1):
        for i in range(2):
            b0 = logT[i, 0] + ll0[n + 1] + lb[n + 1, 0]; b1 = logT[i, 1] + ll1[n + 1] + lb[n + 1, 1]; m = max(b0, b1)
            lb[n, i] = m + math.log(math.exp(b0 - m) + math.exp(b1 - m))
    lp = la + lb; lp -= np.max(lp, axis=1, keepdims=True)
    p = np.exp(lp); p /= np.sum(p, axis=1, keepdims=True)
    return p[:, 1]


def discrete_phase_bcjr_1d(y, Hs_hat, pil_obs_mask, sigma_w_sq, sig0_sq, sig1_sq, p01, p10, Q=128):
    """Exact Colavolpe JSAC'05 / Cui TCOM'26 2-State Bursty Discrete-Phase-Grid BCJR (2*Q states)."""
    N = len(y)
    grid = np.linspace(-math.pi, math.pi, Q, endpoint=False)
    dq = 2.0 * math.pi / Q
    ejg = np.exp(1j * grid)
    diff = np.angle(np.exp(1j * (grid[:, None] - grid[None, :])))
    v0_eff = max(sig0_sq, (dq ** 2) / 3.0)
    K0 = np.exp(-0.5 * (diff ** 2) / v0_eff); K0 /= np.sum(K0, axis=1, keepdims=True)
    K1 = 0.5 * np.exp(-0.5 * ((diff - 0.30) ** 2) / max(sig1_sq, 1e-2)) + 0.5 * np.exp(-0.5 * ((diff + 0.30) ** 2) / max(sig1_sq, 1e-2))
    K1 /= np.sum(K1, axis=1, keepdims=True)
    T = np.maximum(np.block([[(1.0 - p01) * K0, p01 * K1], [p10 * K0, (1.0 - p10) * K1]]), 1e-30)

    sw_vec = np.where(pil_obs_mask, max(sigma_w_sq, 1e-5), max(sigma_w_sq, 0.008))
    err2 = np.abs(y[:, None] - Hs_hat[:, None] * ejg[None, :]) ** 2
    ll = -err2 / sw_vec[:, None]; ll -= np.max(ll, axis=1, keepdims=True)
    em_q = np.exp(ll); em = np.hstack([em_q, em_q])

    alpha = np.zeros((N, 2 * Q), dtype=float)
    pi_q = np.exp(-0.5 * (grid ** 2) / 0.04); pi_q /= np.sum(pi_q)
    alpha[0] = np.concatenate([0.96 * pi_q, 0.04 * pi_q]) * em[0]
    alpha[0] /= max(np.sum(alpha[0]), 1e-300)
    for n in range(1, N):
        alpha[n] = (alpha[n - 1] @ T) * em[n]
        s = np.sum(alpha[n]); alpha[n] = alpha[n] / s if s > 1e-300 else np.ones(2 * Q) / (2 * Q)

    beta = np.ones((N, 2 * Q), dtype=float)
    for n in range(N - 2, -1, -1):
        beta[n] = T @ (em[n + 1] * beta[n + 1])
        s = np.sum(beta[n]); beta[n] = beta[n] / s if s > 1e-300 else np.ones(2 * Q) / (2 * Q)

    post = alpha * beta
    post /= np.maximum(np.sum(post, axis=1, keepdims=True), 1e-300)
    post_q = post[:, :Q] + post[:, Q:]
    return np.angle(post_q @ ejg)


def marginalized_qam_bcjr_1d(z, pil_mask, s_pil, const, v_eff, sig0_sq, sig1_sq, p01, p10, Q=128):
    """Exact Colavolpe JSAC'05 / Cui TCOM'26 Blind QAM-Marginalized 2-state Discrete-Phase BCJR on SC-FDE z=H^{-1}y."""
    N = len(z)
    grid = np.linspace(-math.pi, math.pi, Q, endpoint=False)
    dq = 2.0 * math.pi / Q
    ejg = np.exp(1j * grid)
    diff = np.angle(np.exp(1j * (grid[:, None] - grid[None, :])))
    v0_eff = max(sig0_sq, (dq ** 2) / 3.0)
    K0 = np.exp(-0.5 * (diff ** 2) / v0_eff); K0 /= np.sum(K0, axis=1, keepdims=True)
    K1 = 0.5 * np.exp(-0.5 * ((diff - 0.30) ** 2) / max(sig1_sq, 1e-2)) + 0.5 * np.exp(-0.5 * ((diff + 0.30) ** 2) / max(sig1_sq, 1e-2))
    K1 /= np.sum(K1, axis=1, keepdims=True)
    T = np.maximum(np.block([[(1.0 - p01) * K0, p01 * K1], [p10 * K0, (1.0 - p10) * K1]]), 1e-30)

    em_q = np.zeros((N, Q), dtype=float)
    for n in range(N):
        vn = max(float(v_eff[n]), 1e-4)
        if pil_mask[n]:
            ll = -(np.abs(z[n] - s_pil[n] * ejg) ** 2) / vn
        else:
            zr = z[n] * np.conj(ejg)
            d2 = np.abs(zr[:, None] - const[None, :]) ** 2
            lse = -d2 / vn
            mx = np.max(lse, axis=1, keepdims=True)
            ll = mx[:, 0] + np.log(np.mean(np.exp(lse - mx), axis=1))
        ll -= np.max(ll)
        em_q[n] = np.exp(ll)
    em = np.hstack([em_q, em_q])

    alpha = np.zeros((N, 2 * Q), dtype=float)
    pi_q = np.exp(-0.5 * (grid ** 2) / 0.04); pi_q /= np.sum(pi_q)
    alpha[0] = np.concatenate([0.96 * pi_q, 0.04 * pi_q]) * em[0]
    alpha[0] /= max(np.sum(alpha[0]), 1e-300)
    for n in range(1, N):
        alpha[n] = (alpha[n - 1] @ T) * em[n]
        s = np.sum(alpha[n]); alpha[n] = alpha[n] / s if s > 1e-300 else np.ones(2 * Q) / (2 * Q)
    beta = np.ones((N, 2 * Q), dtype=float)
    for n in range(N - 2, -1, -1):
        beta[n] = T @ (em[n + 1] * beta[n + 1])
        s = np.sum(beta[n]); beta[n] = beta[n] / s if s > 1e-300 else np.ones(2 * Q) / (2 * Q)
    post = alpha * beta
    post /= np.maximum(np.sum(post, axis=1, keepdims=True), 1e-300)
    post_q = post[:, :Q] + post[:, Q:]
    return np.angle(post_q @ ejg)


def init_phase_ptrs(y, H, s_pil, pil_obs_cl, N):
    y_pil_ref = H @ s_pil
    centers = np.array([float(np.mean(cl)) for cl in pil_obs_cl])
    phases = np.unwrap(np.array([float(np.angle(np.vdot(y_pil_ref[cl], y[cl]))) for cl in pil_obs_cl]))
    return np.interp(np.arange(N, dtype=float), centers, phases), centers, phases


def step_scan_init_phase(y, H, U_d, s_pil, data_t, pil_obs_cl, const, sigma_w_sq, pn_mode):
    """Ruthless 1D per-interval jump-location + +-2pi unwrap scan (eliminates linear-interp & wrap smearing!)."""
    N = len(y)
    phi_best, centers, phases = init_phase_ptrs(y, H, s_pil, pil_obs_cl, N)
    Nd = len(data_t)

    def eval_phi(phi_cand):
        if pn_mode == "rx":
            H_e = np.exp(1j * phi_cand)[:, None] * H
        elif pn_mode == "tx":
            H_e = H * np.exp(1j * phi_cand)[None, :]
        else:
            H_e = (np.exp(1j * (0.5 * phi_cand))[:, None] * H) * np.exp(1j * (0.5 * phi_cand))[None, :]
        y_d = y - H_e @ s_pil
        A_d = H_e[:, data_t] @ U_d.conj().T
        xh = np.linalg.solve(A_d.conj().T @ A_d + max(sigma_w_sq + 0.015, 0.015) * np.eye(Nd), A_d.conj().T @ y_d)
        xq = const[np.argmin(np.abs(xh[:, None] - const[None, :]), axis=1)]
        return float(np.sum(np.abs(y_d - A_d @ xq) ** 2))

    best_sc = eval_phi(phi_best)
    for k in range(len(centers) - 1):
        c0, c1 = int(round(centers[k])), int(round(centers[k + 1]))
        base = phi_best.copy()
        for shift in (0.0, 2.0 * math.pi, -2.0 * math.pi):
            p_right = base[c1] + shift
            if abs(p_right - base[c0]) < 0.12 and shift == 0.0:
                continue
            for n_star in range(c0 + 4, c1 - 2, 4):
                cand = base.copy()
                cand[c0:n_star] = base[c0]
                cand[n_star:] = base[n_star:] + shift
                cand[n_star:c1 + 1] = p_right
                sc = eval_phi(cand)
                if sc < best_sc:
                    best_sc = sc; phi_best = cand
    return phi_best


def run_ieks_arm(y, H, U_d, s_pil, data_t, phi_init, sigma_w_sq, const, pn_mode, prior_type, sig0_sq, sig1_sq, p01, p10, true_vt=None, true_vr=None, phi_init_r=None, n_outer=8):
    N = len(y)
    duty = p01 / max(p01 + p10, 1e-9)
    sig_avg = (1.0 - duty) * sig0_sq + duty * (sig1_sq + 0.30 ** 2)
    if pn_mode == "dual":
        pt = (phi_init.copy() if phi_init_r is not None else 0.5 * phi_init.copy())
        pr = (phi_init_r.copy() if phi_init_r is not None else 0.5 * phi_init.copy())
    elif pn_mode == "tx":
        pt = phi_init.copy(); pr = np.zeros(N)
    else:
        pt = np.zeros(N); pr = phi_init.copy()
    vtc = np.full(N, sig_avg) if true_vt is None else true_vt.copy()
    vrc = np.full(N, sig_avg) if true_vr is None else true_vr.copy()

    for outer in range(n_outer):
        H_eff = (np.exp(1j * pr)[:, None] * H) * np.exp(1j * pt)[None, :]
        y_d = y - H_eff @ s_pil; A_d = H_eff[:, data_t] @ U_d.conj().T
        sw_e = sigma_w_sq + (0.02 if outer == 0 else (0.004 if outer == 1 else 0.0005))
        xh = linear_ep_sub(y_d, A_d, sw_e, const, n_iters=6)
        s_hat = s_pil.copy(); s_hat[data_t] = U_d.conj().T @ xh

        if prior_type == "oracle_state":
            vtc, vrc = true_vt, true_vr
        elif prior_type == "gauss_avg":
            vtc[:] = sig_avg; vrc[:] = sig_avg
        elif prior_type == "student_t":
            if pn_mode in ("tx", "dual"):
                dpt = np.diff(pt, prepend=0.0)
                vtc = np.clip((sig0_sq * 2.5 + dpt ** 2) / 3.5, sig0_sq, 2.0)
            if pn_mode in ("rx", "dual"):
                dpr = np.diff(pr, prepend=0.0)
                vrc = np.clip((sig0_sq * 2.5 + dpr ** 2) / 3.5, sig0_sq, 2.0)
        elif prior_type == "hmm_2state":
            s1_t = sig1_sq + 0.30 ** 2
            s0_e = sig0_sq * (3.0 if outer < 2 else 1.3)
            if pn_mode in ("tx", "dual"):
                dpt = np.diff(pt, prepend=0.0)
                gt = hmm_fb_2state(-0.5 * math.log(s0_e) - 0.5 * dpt ** 2 / s0_e,
                                   -0.5 * math.log(s1_t) - 0.5 * dpt ** 2 / s1_t, p01, p10)
                vtc = (1.0 - gt) * sig0_sq + gt * s1_t
            if pn_mode in ("rx", "dual"):
                dpr = np.diff(pr, prepend=0.0)
                gr = hmm_fb_2state(-0.5 * math.log(s0_e) - 0.5 * dpr ** 2 / s0_e,
                                   -0.5 * math.log(s1_t) - 0.5 * dpr ** 2 / s1_t, p01, p10)
                vrc = (1.0 - gr) * sig0_sq + gr * s1_t
        pt, pr = gn_ieks_phase(y, H, s_hat, pt, pr, vtc, vrc, sw_e, pn_mode=pn_mode, n_gn=5)

    H_eff = (np.exp(1j * pr)[:, None] * H) * np.exp(1j * pt)[None, :]
    return linear_ep_sub(y - H_eff @ s_pil, H_eff[:, data_t] @ U_d.conj().T, sigma_w_sq, const, n_iters=8)


def run_trial(args):
    seed, regime, wf, mod_M, N, snr_db, sig0_sq, sig1_sq, duty, mean_burst = args
    rng = np.random.default_rng(seed)
    const = gray_qam(mod_M)
    sigma_w_sq = 10.0 ** (-snr_db / 10.0)
    k_max = 1.5; l_max = 8
    c1 = 5.0 / (2.0 * N) if wf == "AFDM" else 0.0
    H = build_multipath_H(N, 4, l_max, k_max, rng, cpp_c1=c1)

    # Symmetric 4-cluster PTRS bracketing ENTIRE frame [0..13],[80..93],[160..173],[242..255]
    # 56/256 = 21.9% overhead -> 4 x 6 = 24 zero-ISI pilot observations (zero unanchored tail!)
    clusters = [np.arange(0, 14), np.arange(80, 94), np.arange(160, 174), np.arange(242, 256)]
    pil_obs_cl = [np.arange(c[0] + l_max, c[-1] + 1) for c in clusters]
    pil_obs_mask = np.zeros(N, dtype=bool)
    for c in pil_obs_cl:
        pil_obs_mask[c] = True
    pil_t = np.concatenate(clusters)
    data_t = np.setdiff1d(np.arange(N), pil_t)
    Nd = len(data_t)

    if wf == "AFDM":
        U_d = daft_mat(Nd, 5.0 / (2.0 * Nd), 1.0 / (2.0 * math.pi * Nd))
    elif wf == "OTFS":
        U_d = otfs_mat(20, 10)
    else:
        U_d = np.eye(Nd, dtype=np.complex128)

    pil_const = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / math.sqrt(2.0)
    u_pil = pil_const[rng.integers(0, 4, size=len(pil_t))]
    x_data = const[rng.integers(0, len(const), size=Nd)]
    s_pil = np.zeros(N, dtype=np.complex128); s_pil[pil_t] = u_pil
    s_true = s_pil.copy(); s_true[data_t] = U_d.conj().T @ x_data

    pn_mode = "dual" if regime == "DUAL" else ("tx" if regime == "TX" else "rx")
    if pn_mode == "tx":
        phi_t, z_b, v_t, ms = gen_bursty_pn(N, sig0_sq, sig1_sq, duty, mean_burst, rng)
        phi_r = np.zeros(N); v_r = np.full(N, sig0_sq)
    elif pn_mode == "rx":
        phi_t = np.zeros(N); v_t = np.full(N, sig0_sq)
        phi_r, z_b, v_r, ms = gen_bursty_pn(N, sig0_sq, sig1_sq, duty, mean_burst, rng)
    else:
        phi_t, z_t, v_t, ms = gen_bursty_pn(N, sig0_sq, sig1_sq, duty * 0.5, mean_burst, rng)
        phi_r, z_r, v_r, _  = gen_bursty_pn(N, sig0_sq, sig1_sq, duty * 0.5, mean_burst, rng)
        z_b = np.maximum(z_t, z_r)
    w = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sigma_w_sq / 2.0)
    y = (H @ (s_true * np.exp(1j * phi_t))) * np.exp(1j * phi_r) + w
    p01, p10 = ms["p01"], ms["p10"]

    res = {"_pil_clean": float(all(np.sum(z_b[c]) == 0 for c in clusters))}
    # 0. Sanity zero-PN
    y_cl = H @ s_true + w
    res["Ref_Clean_ZeroPN"] = hard_ser(linear_ep_sub(y_cl - H @ s_pil, H[:, data_t] @ U_d.conj().T, sigma_w_sq, const, 6), x_data, const)

    # 1. Pub PTRS linear interp
    phi_lin, _, _ = init_phase_ptrs(y, H, s_pil, pil_obs_cl, N)
    if pn_mode == "rx":
        H_p0 = np.exp(1j * phi_lin)[:, None] * H
    elif pn_mode == "tx":
        H_p0 = H * np.exp(1j * phi_lin)[None, :]
    else:
        H_p0 = (np.exp(1j * (0.5 * phi_lin))[:, None] * H) * np.exp(1j * (0.5 * phi_lin))[None, :]
    res["Pub_PTRS_Interp"] = hard_ser(linear_ep_sub(y - H_p0 @ s_pil, H_p0[:, data_t] @ U_d.conj().T, sigma_w_sq + 0.02, const, 6), x_data, const)

    # 2. SM1: Gauss Bell-1994 IEKS (from linear PTRS)
    res["SM1_Gauss_Bell94_IEKS"] = hard_ser(run_ieks_arm(y, H, U_d, s_pil, data_t, phi_lin, sigma_w_sq, const, pn_mode, "gauss_avg", sig0_sq, sig1_sq, p01, p10), x_data, const)

    # 3. 1D Step-Scan + +-2pi Unwrap initialization (Sol-level Steelman!)
    phi_step = step_scan_init_phase(y, H, U_d, s_pil, data_t, pil_obs_cl, const, sigma_w_sq, pn_mode)
    res["SM2_StepScan_StudentT"] = hard_ser(run_ieks_arm(y, H, U_d, s_pil, data_t, phi_step, sigma_w_sq, const, pn_mode, "student_t", sig0_sq, sig1_sq, p01, p10), x_data, const)
    res["SM3_StepScan_2StateHMM"] = hard_ser(run_ieks_arm(y, H, U_d, s_pil, data_t, phi_step, sigma_w_sq, const, pn_mode, "hmm_2state", sig0_sq, sig1_sq, p01, p10), x_data, const)

    # 4. SM4: Step-Scan + Exact 2-State Discrete-Phase-Grid BCJR (Q=128, Colavolpe JSAC'05 / Cui TCOM'26)
    phi_b = phi_step.copy()
    for it in range(8):
        H_e = (np.exp(1j * phi_b)[:, None] * H) if pn_mode == "rx" else (H * np.exp(1j * phi_b)[None, :])
        xb = linear_ep_sub(y - H_e @ s_pil, H_e[:, data_t] @ U_d.conj().T, sigma_w_sq + (0.02 if it < 2 else 0.002), const, 6)
        sb = s_pil.copy(); sb[data_t] = U_d.conj().T @ xb
        phi_b = discrete_phase_bcjr_1d(y, H @ sb, pil_obs_mask, sigma_w_sq + (0.01 if it < 2 else 0.0), sig0_sq, sig1_sq, p01, p10, Q=128)
    H_e = (np.exp(1j * phi_b)[:, None] * H) if pn_mode == "rx" else (H * np.exp(1j * phi_b)[None, :])
    res["SM4_StepScan_Q128_BCJR_Cui26"] = hard_ser(linear_ep_sub(y - H_e @ s_pil, H_e[:, data_t] @ U_d.conj().T, sigma_w_sq, const, 8), x_data, const)

    # 4b. SM5 (SC-FDE cross-waveform killer): LMMSE H^{-1} y + Exact Blind QAM-Marginalized Q=128 2-State BCJR + EP!
    s_sc_true = s_pil.copy(); s_sc_true[data_t] = x_data
    y_sc = (H @ (s_sc_true * np.exp(1j * phi_t))) * np.exp(1j * phi_r) + w
    W_sc = np.linalg.solve(H.conj().T @ H + sigma_w_sq * np.eye(N), H.conj().T)
    z_sc = W_sc @ y_sc
    v_sc = np.maximum(np.real(np.sum(np.abs(W_sc) ** 2, axis=1)) * sigma_w_sq, sigma_w_sq)
    pil_m_full = np.zeros(N, dtype=bool); pil_m_full[pil_t] = True
    phi_mb = marginalized_qam_bcjr_1d(z_sc, pil_m_full, s_pil, const, v_sc * 2.0, sig0_sq, sig1_sq, p01, p10, Q=128)
    H_mb = (H * np.exp(1j * phi_mb)[None, :]) if pn_mode != "rx" else (np.exp(1j * phi_mb)[:, None] * H)
    res["SM5_SC_Hinv_MargQAM_BCJR"] = hard_ser(linear_ep_sub(y_sc - H_mb @ s_pil, H_mb[:, data_t], sigma_w_sq, const, 8), x_data, const)

    # 5. SM_S: Equal-net-rate Differential modulation on SC-FDE (zero PTRS needed -> matches/exceeds net bpcu!)
    #    - For 16-QAM w/ 21.9% PTRS (3.125 bpcu): 8-DPSK (3.0 bpcu, constant modulus, best-case!)
    #    - For 64-QAM w/ 21.9% PTRS (4.69 bpcu):  32-DAPSK (2 rings [r1=0.62, r2=1.27] x 16-DPSK = 5.0 bpcu!)
    if mod_M == 16:
        b_idx = rng.integers(0, 8, size=N)
        s_d = np.exp(1j * np.cumsum(b_idx * (2.0 * math.pi / 8.0)))
        y_d8 = (H @ (s_d * np.exp(1j * phi_t))) * np.exp(1j * phi_r) + w
        s_h8 = np.linalg.solve(H.conj().T @ H + sigma_w_sq * np.eye(N), H.conj().T @ y_d8)
        dec8 = np.round(np.angle(s_h8[1:] * np.conj(s_h8[:-1])) / (2.0 * math.pi / 8.0)).astype(int) % 8
        res["SM_S_EqRate_Diff_SC"] = float(np.mean(dec8 != b_idx[1:]))
    else:
        # 32-DAPSK: 1 bit amplitude ring (r_lo=0.60, r_hi=1.28, unit avg power) + 4 bits 16-DPSK phase
        rings = np.array([0.60, 1.2806248])
        r_idx = rng.integers(0, 2, size=N)
        p_idx = rng.integers(0, 16, size=N)
        s_d = rings[r_idx] * np.exp(1j * np.cumsum(p_idx * (2.0 * math.pi / 16.0)))
        y_d32 = (H @ (s_d * np.exp(1j * phi_t))) * np.exp(1j * phi_r) + w
        s_h32 = np.linalg.solve(H.conj().T @ H + sigma_w_sq * np.eye(N), H.conj().T @ y_d32)
        dec_r = (np.abs(s_h32[1:]) > 0.94).astype(int)
        dec_p = np.round(np.angle(s_h32[1:] * np.conj(s_h32[:-1])) / (2.0 * math.pi / 16.0)).astype(int) % 16
        res["SM_S_EqRate_Diff_SC"] = float(np.mean((dec_r != r_idx[1:]) | (dec_p != p_idx[1:])))

    # 6. Non-Cheating Same-Obs Basin MAP Oracle & Exact-Phi Oracle
    if pn_mode == "dual":
        xo = run_ieks_arm(y, H, U_d, s_pil, data_t, phi_t + rng.normal(0.0, 0.20, N), sigma_w_sq, const, pn_mode, "oracle_state", sig0_sq, sig1_sq, p01, p10, true_vt=v_t, true_vr=v_r, phi_init_r=phi_r + rng.normal(0.0, 0.20, N), n_outer=8)
    else:
        phi_tr = phi_t if pn_mode == "tx" else phi_r
        xo = run_ieks_arm(y, H, U_d, s_pil, data_t, phi_tr + rng.normal(0.0, 0.20, N), sigma_w_sq, const, pn_mode, "oracle_state", sig0_sq, sig1_sq, p01, p10, true_vt=v_t, true_vr=v_r, n_outer=8)
    res["Oracle_BasinMAP_TrueState"] = hard_ser(xo, x_data, const)

    H_tr = (np.exp(1j * phi_r)[:, None] * H) * np.exp(1j * phi_t)[None, :]
    res["Oracle_TruePhi_EP"] = hard_ser(linear_ep_sub(y - H_tr @ s_pil, H_tr[:, data_t] @ U_d.conj().T, sigma_w_sq, const, 8), x_data, const)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=32)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c6_tx_bursty_pn.json")
    args = ap.parse_args()
    t0 = time.time()

    configs = [
        ("DUAL", "AFDM", 16, 256, 22.0, 2e-4, 0.16, 0.04, 3.0),
        ("DUAL", "OTFS", 16, 256, 22.0, 2e-4, 0.16, 0.04, 3.0),
        ("DUAL", "SC-FDE", 16, 256, 22.0, 2e-4, 0.16, 0.04, 3.0),
        ("DUAL", "AFDM", 64, 256, 28.0, 2e-4, 0.16, 0.04, 3.0),
        ("DUAL", "OTFS", 64, 256, 28.0, 2e-4, 0.16, 0.04, 3.0),
        ("DUAL", "SC-FDE", 64, 256, 28.0, 2e-4, 0.16, 0.04, 3.0),
        ("TX",   "AFDM", 64, 256, 28.0, 2e-4, 0.16, 0.04, 3.0),
        ("TX",   "SC-FDE", 64, 256, 28.0, 2e-4, 0.16, 0.04, 3.0),
        ("RX",   "AFDM", 64, 256, 28.0, 2e-4, 0.16, 0.04, 3.0),
    ]
    summary = {"meta": {"trials": args.trials}, "results": {}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, cfg in enumerate(configs):
            key = f"{cfg[0]}_{cfg[1]}_{cfg[2]}QAM_SNR{int(cfg[4])}"
            jobs = [(630000 + i * 1000 + t,) + cfg for t in range(args.trials)]
            outs = list(ex.map(run_trial, jobs))
            mkeys = [k for k in outs[0] if not k.startswith("_")]
            agg = {k: {"mean": float(np.mean([o[k] for o in outs])), "se": float(np.std([o[k] for o in outs], ddof=1) / math.sqrt(len(outs)))} for k in mkeys}
            clean_pil = [o for o in outs if o["_pil_clean"] > 0.5]
            if len(clean_pil) >= 2:
                agg["_strat_clean_pil_n"] = len(clean_pil)
                agg["_strat_clean_pil_BestSM"] = float(min(np.mean([o[k] for o in clean_pil]) for k in mkeys if k.startswith("SM")))
                agg["_strat_clean_pil_Oracle"] = float(np.mean([o["Oracle_BasinMAP_TrueState"] for o in clean_pil]))
            summary["results"][key] = agg
            best_sm_k = min((k for k in mkeys if k.startswith("SM")), key=lambda k: agg[k]["mean"])
            best_sm = agg[best_sm_k]["mean"]
            or_m = agg["Oracle_BasinMAP_TrueState"]["mean"]
            print(f"\n=== {key} (n={args.trials}) ===")
            for k in mkeys:
                v = agg[k]
                print(f"  {k:28s}: SER = {v['mean']:.5f} +/- {v['se']:.5f}")
            print(f"  --> Best_SM ({best_sm_k})={best_sm:.5f} vs Oracle_BasinMAP={or_m:.5f} | Ratio={best_sm/max(or_m,1e-6):.2f}x")
            if "_strat_clean_pil_n" in agg:
                print(f"  --> Clean-Pilot Strat (n={agg['_strat_clean_pil_n']}): BestSM={agg['_strat_clean_pil_BestSM']:.5f} vs Oracle={agg['_strat_clean_pil_Oracle']:.5f}")
    summary["elapsed_sec"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to {args.out} in {summary['elapsed_sec']}s.")


if __name__ == "__main__":
    main()
