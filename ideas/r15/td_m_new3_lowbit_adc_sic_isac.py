#!/usr/bin/env python3
"""
Round 15 Phase 1 — New Problem #3 Steelman Teardown (`td_m_new3_lowbit_adc_sic_isac.py`):
Finite-Tap Analog Self-Interference Cancellation + Low-Resolution (2-bit / 3-bit) Oversampled RX ADC
Weak-Echo Detection in Full-Duplex Continuous-Time RRC AFDM-ISAC (`gpt-6.2-sol` §3 Flagship Experiment!).

Literature Anchors:
  - Sui et al., IEEE TCOM 2026 (DOI: 10.1109/tcomm.2026.3701879): Low-resolution quantization in AFDM
  - Gourar et al., arXiv:2609.14030 (2026): AFDM sensing under hardware nonlinearity
  - Mirabella et al., IEEE JSAC 2026 (DOI: 10.1109/jsac.2026.3751260): CT-RRC AFDM
  - Textbook Steelman references (`Sol` §2-3): Mo, Schniter & Heath IEEE TSP 2017 (low-bit quantized estimation),
    Korpi et al. IEEE TWC 2014 (full-duplex pre-ADC analog cancellation & ADC dynamic range).

Exact Physical Model (`Sol` Eq. line 825):
  r = Q_b( g * [ (h_0 T_0 + h_1 T_{0.75 Ts} + h_2 T_{2.35 Ts}) x
                 - (a_0 T_0 + a_1 T_{Ts}) x
                 + alpha D_nu T_tau x + w ] )
  - Strong multi-path SI (`|h_0|=1.0, |h_1|=0.40, |h_2|=0.30` at spillover delay `2.35 Ts` beyond the 2-tap `[0, Ts]`
    hardware analog RF canceller!), quantized by a `b = 2` bit (4-level) or `b = 3` bit (8-level) RX ADC on `[-1, +1]`.
  - Weak high-velocity radar echo: `tau/Ts in [3.5, 9.5]`, `|nu|/Delta_f in [0.65, 1.25]`, `20 log10|alpha| = -25 dB`,
    under fixed communication payload (`64-QAM` data + `16` pilot DoFs, equal bandwidth & energy across all waveforms!).

4 Arms Implemented Verbatim per `gpt-6.2-sol` §3 Table:
  1) `Pub_AFDM_Bussgang_LSAnalog`: Minimum-power LS analog canceller `(a_0, a_1)` + standard Lloyd-Max RMS AGC `g`
     + Bussgang linear digital SI subtraction & matched-filter CFAR/GLRT (`Gourar + Sui`).
  2) `Steelman_A_AFDM_ProbitGLRT_OptAGC`: Optimal 1D scalar AGC `g` scan + **Exact Quantized Probit Log-Likelihood
     Rao/Score GLRT Detector** (exact Gaussian bin probabilities `Phi((t_{k+1}-mu)/sigma) - Phi((t_k-mu)/sigma)` and
     exact score weights `p'_k(mu)/p_k(mu)`, joint nuisance tangent projection of residual SI, ZERO Bussgang approx!)
     PLUS `Steelman_A_AFDM_FisherJoint_TxAnalogRx` (coordinate optimization of `(a_0, a_1, g)` + pilot DoFs maximizing
     expected post-ADC quantized Fisher Information `sum_n J(mu_n)`!).
  3) `Steelman_S_{OFDM, SC_FDE, OTFS}_FisherProbit`: Exact same 2-tap analog hardware, pilot DoFs, optimal `(a_0, a_1, g)`
     Fisher optimization, and Exact Quantized Probit Score GLRT across `CP-OFDM`, `SC-FDE` (`DFT-s-OFDM` & `TD-SC`), and `OTFS`!
  4) `Oracle_SameHW_GenieProbit` (best achievable over candidate `(a_0, a_1, g)` + pilot set on the SAME `b`-bit ADC using
     exact Probit likelihood) AND `Oracle_InfBit_GLRT` (infinite-resolution ADC upper bound quantifying irreversible front-end loss).
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.fft import fft, ifft
from scipy.special import ndtr

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def gray_qam(M: int):
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


def rrc_taps(Q_os: int, M_p: int, alpha: float) -> np.ndarray:
    grid = np.arange(-M_p * Q_os, M_p * Q_os + 1, dtype=float) / float(Q_os)
    out = np.zeros_like(grid)
    for i, t in enumerate(grid):
        at = abs(float(t))
        if at < 1e-12:
            out[i] = 1.0 + alpha * (4.0 / math.pi - 1.0)
        elif alpha > 0 and abs(at - 1.0 / (4.0 * alpha)) < 1e-9:
            out[i] = (alpha / math.sqrt(2.0)) * (
                (1.0 + 2.0 / math.pi) * math.sin(math.pi / (4.0 * alpha))
                + (1.0 - 2.0 / math.pi) * math.cos(math.pi / (4.0 * alpha))
            )
        else:
            out[i] = (
                math.sin(math.pi * t * (1.0 - alpha)) + 4.0 * alpha * t * math.cos(math.pi * t * (1.0 + alpha))
            ) / (math.pi * t * (1.0 - (4.0 * alpha * t) ** 2))
    out /= math.sqrt(float(np.sum(out ** 2)) / float(Q_os))
    return out


def upsample_rrc(s_ext: np.ndarray, p_rrc: np.ndarray, Q_os: int) -> np.ndarray:
    B = len(s_ext)
    up = np.zeros(B * Q_os, dtype=np.complex128)
    up[::Q_os] = s_ext
    pad = len(p_rrc) // 2
    return np.convolve(up, p_rrc, mode="full")[pad : pad + B * Q_os]


def shift_frac_dop_os(x_os: np.ndarray, tau_chips: float, nu_norm: float, N: int, Q_os: int) -> np.ndarray:
    L_os = len(x_os)
    kf = np.fft.fftfreq(L_os)
    x_del = ifft(fft(x_os) * np.exp(-1j * 2.0 * np.pi * kf * (tau_chips * Q_os)))
    if abs(nu_norm) < 1e-12:
        return x_del
    t_chip = np.arange(L_os, dtype=float) / float(Q_os)
    return x_del * np.exp(1j * 2.0 * np.pi * nu_norm * t_chip / float(N))


def uniform_quantize_iq(y_scaled: np.ndarray, n_bits: int, mid_tread: bool = False):
    """
    Uniform b-bit quantizer on [-1, +1] per real/imag rail!
      - mid_tread=False (mid-rise, 2^b levels): threshold at 0.0 (`[-1+d, ..., +1-d]`).
      - mid_tread=True  (mid-tread zero-code SAR ADC, 2^b + 1 levels): `0.0` sits dead-center inside
        dead-zone `[-d/2, +d/2]` (`edges = [-1+d/2, ..., -d/2, +d/2, ..., 1-d/2]`)!
    """
    if mid_tread:
        L = (1 << n_bits) + 1  # e.g. 5 levels {-0.8, -0.4, 0, +0.4, +0.8}, edges [-0.6, -0.2, +0.2, +0.6]
        delta = 2.0 / float(L)
        edges = np.linspace(-1.0 + delta, 1.0 - delta, L - 1)  # wait: for L=5, delta=0.4 -> [-0.6, -0.2, +0.2, +0.6] (0 is mid-bin!)
        midpts = np.linspace(-1.0 + 0.5 * delta, 1.0 - 0.5 * delta, L)
    else:
        L = 1 << n_bits
        delta = 2.0 / float(L)
        edges = np.linspace(-1.0 + delta, 1.0 - delta, L - 1)
        midpts = np.linspace(-1.0 + 0.5 * delta, 1.0 - 0.5 * delta, L)
    kre = np.digitize(np.real(y_scaled), edges)
    kim = np.digitize(np.imag(y_scaled), edges)
    y_mid = midpts[kre] + 1j * midpts[kim]
    return kre, kim, y_mid, edges, midpts


def probit_score_and_fisher_1d(k_bins: np.ndarray, mu: np.ndarray, sig: float, edges: np.ndarray):
    """
    Exact Quantized Probit 1st-order score `d/dmu log P(bin = k | mu, sig)` and Fisher info `J(mu)`
    with asymptotic Mill's-ratio tail formulas so float64 NEVER underflows to 0/0!
    """
    inv_s = 1.0 / max(sig, 1e-9)
    L = len(edges) + 1
    N_s = len(mu)
    a_mat = np.full((N_s, L), -np.inf, dtype=float)
    b_mat = np.full((N_s, L), +np.inf, dtype=float)
    z_int = (edges[None, :] - mu[:, None]) * inv_s
    a_mat[:, 1:] = z_int
    b_mat[:, :-1] = z_int

    cdf = ndtr(z_int)
    pdf = np.exp(-0.5 * np.clip(z_int, -38.0, 38.0) ** 2) / math.sqrt(2.0 * math.pi)

    p_all = np.empty((N_s, L), dtype=float)
    p_all[:, 0] = cdf[:, 0]
    p_all[:, 1:-1] = np.maximum(cdf[:, 1:] - cdf[:, :-1], 0.0)
    p_all[:, -1] = 1.0 - cdf[:, -1]

    dp_all = np.empty((N_s, L), dtype=float)
    dp_all[:, 0] = -pdf[:, 0] * inv_s
    dp_all[:, 1:-1] = -(pdf[:, 1:] - pdf[:, :-1]) * inv_s
    dp_all[:, -1] = pdf[:, -1] * inv_s

    r_all = np.zeros((N_s, L), dtype=float)
    b0 = b_mat[:, 0]; m_lo = b0 < -6.0
    r_all[~m_lo, 0] = dp_all[~m_lo, 0] / np.maximum(p_all[~m_lo, 0], 1e-300)
    r_all[m_lo, 0] = inv_s * (b0[m_lo] - 1.0 / b0[m_lo])

    aL = a_mat[:, -1]; m_hi = aL > 6.0
    r_all[~m_hi, -1] = dp_all[~m_hi, -1] / np.maximum(p_all[~m_hi, -1], 1e-300)
    r_all[m_hi, -1] = inv_s * (aL[m_hi] + 1.0 / aL[m_hi])

    for k in range(1, L - 1):
        ak = a_mat[:, k]; bk = b_mat[:, k]
        mid_m = p_all[:, k] > 1e-14
        r_all[mid_m, k] = dp_all[mid_m, k] / p_all[mid_m, k]
        lo_m = (~mid_m) & (bk < 0)
        hi_m = (~mid_m) & (ak > 0)
        r_all[lo_m, k] = inv_s * bk[lo_m]
        r_all[hi_m, k] = inv_s * ak[hi_m]

    idx_n = np.arange(N_s)
    score_obs = r_all[idx_n, k_bins]
    J_vec = np.sum(p_all * (r_all ** 2), axis=1) + 1e-8 * (inv_s ** 2)
    return score_obs, J_vec


def probit_loglik_1d(k_bins: np.ndarray, mu: np.ndarray, sig: float, edges: np.ndarray) -> float:
    """Exact globally concave 1D Probit log-likelihood sum_n log P(bin = k_n | mu_n, sig) without underflow!"""
    from scipy.special import log_ndtr
    inv_s = 1.0 / max(sig, 1e-9)
    L = len(edges) + 1
    z = (edges[None, :] - mu[:, None]) * inv_s
    ll = 0.0
    m0 = k_bins == 0
    if np.any(m0):
        ll += float(np.sum(log_ndtr(z[m0, 0])))
    mL = k_bins == (L - 1)
    if np.any(mL):
        ll += float(np.sum(log_ndtr(-z[mL, -1])))
    for k in range(1, L - 1):
        mk = k_bins == k
        if np.any(mk):
            ak = z[mk, k - 1]; bk = z[mk, k]
            # log(Phi(bk) - Phi(ak)): use log_ndtr for whichever tail is smaller!
            pos = ak > 0.0
            if np.any(pos):
                # Phi(bk) - Phi(ak) = Phi(-ak) - Phi(-bk)
                la = log_ndtr(-ak[pos]); lb = log_ndtr(-bk[pos])
                ll += float(np.sum(la + np.log(np.maximum(1.0 - np.exp(lb - la), 1e-300))))
            neg = ~pos
            if np.any(neg):
                lb = log_ndtr(bk[neg]); la = log_ndtr(ak[neg])
                ll += float(np.sum(lb + np.log(np.maximum(1.0 - np.exp(la - lb), 1e-300))))
    return ll


def fit_residual_si_probit_mle(
    kre: np.ndarray,
    kim: np.ndarray,
    Phi_si: np.ndarray,
    sig_w_scaled: float,
    edges: np.ndarray,
    ymid: np.ndarray,
    n_newton: int = 25,
) -> np.ndarray:
    """
    `Sol` §3 Prescription ("量化似然下的残余自干扰与目标联合拟合"):
    Globally convergent Armijo-backtracking Fisher-Scoring / Newton MLE on the strictly concave
    Probit log-likelihood! Note: first orthonormalizes `Phi_si` via QR (`Q_si`) because `[s_sp0, c0_af]`
    both sit at delay 0 (`100%` collinear!!), then solves in the minimal orthonormal subspace!
    """
    Q_si, _ = np.linalg.qr(Phi_si, mode="reduced")
    # Drop rank-deficient columns (e.g., s_sp0 == c0_af at delay 0.0 -> singular value 0!)
    U_p, s_p, _ = np.linalg.svd(Phi_si, full_matrices=False)
    keep = s_p > 1e-7 * float(s_p[0])
    Q_orth = U_p[:, keep]
    P_eff = Q_orth.shape[1]

    th = Q_orth.conj().T @ ymid
    sig_1d = max(sig_w_scaled / math.sqrt(2.0), 1e-6)
    A_re = np.vstack([
        np.hstack([np.real(Q_orth), -np.imag(Q_orth)]),
        np.hstack([np.imag(Q_orth),  np.real(Q_orth)]),
    ])
    x_r = np.concatenate([np.real(th), np.imag(th)])

    def eval_ll(xv):
        mr = A_re @ xv
        return probit_loglik_1d(kre, mr[:len(kre)], sig_1d, edges) + probit_loglik_1d(kim, mr[len(kre):], sig_1d, edges)

    ll_cur = eval_ll(x_r)
    for _ in range(n_newton):
        mu_r = A_re @ x_r
        sc_re, J_re = probit_score_and_fisher_1d(kre, mu_r[:len(kre)], sig_1d, edges)
        sc_im, J_im = probit_score_and_fisher_1d(kim, mu_r[len(kre):], sig_1d, edges)
        grad = A_re.T @ np.concatenate([sc_re, sc_im])
        if float(np.linalg.norm(grad)) < 1e-5:
            break
        W_j = np.concatenate([J_re, J_im])
        H_f = A_re.T @ (W_j[:, None] * A_re) + 1e-8 * np.eye(2 * P_eff)
        dx = np.linalg.solve(H_f, grad)
        step = 1.0
        slope = float(np.dot(grad, dx))
        while step > 1e-4:
            ll_try = eval_ll(x_r + step * dx)
            if ll_try >= ll_cur + 1e-4 * step * max(slope, 0.0):
                x_r = x_r + step * dx
                ll_cur = ll_try
                break
            step *= 0.5
        if float(np.linalg.norm(step * dx)) < 1e-6:
            break
    th_hat = x_r[:P_eff] + 1j * x_r[P_eff:]
    return Q_orth @ th_hat


def probit_rao_glrt_detector(
    kre: np.ndarray,
    kim: np.ndarray,
    mu_si_scaled: np.ndarray,
    g_agc: float,
    sig_w_scaled: float,
    edges: np.ndarray,
    x_cpi_os: list,
    si_basis_vecs: list,
    tgt_grid: list,
    N: int,
    Q_os: int,
) -> tuple:
    """
    Exact Quantized Probit Rao / Score GLRT Detector (`Sol` §2-3):
      Under H0 (weak target alpha = 0), pre-quantizer input is CN(mu_si_scaled, sig_w_scaled^2)
      (each real/imag component has std `sig_r = sig_w_scaled / sqrt(2)`).
      For any candidate target steering vector `psi(tau, nu)` (scaled by `g_agc`), the exact
      complex Rao score statistic with nuisance SI tangent projection is:
        u_score = score_re + 1j * score_im
        Fisher metric diag W_J = J_re + J_im (or exact real 2N representation!)
        Projects target tangent `[g*Re(psi); g*Im(psi)]` orthogonal to residual SI tangent subspace `S_si`
        under the exact Fisher inner product `diag(J_re, J_im)`, yielding exact chi^2_2 Rao GLRT!
    """
    sig_1d = sig_w_scaled / math.sqrt(2.0)
    sc_re, J_re = probit_score_and_fisher_1d(kre, np.real(mu_si_scaled), sig_1d, edges)
    sc_im, J_im = probit_score_and_fisher_1d(kim, np.imag(mu_si_scaled), sig_1d, edges)

    r_score = np.concatenate([sc_re, sc_im])            # (2 * L_tot,)
    W_diag = np.maximum(np.concatenate([J_re, J_im]), 1e-12)
    sqrt_W = np.sqrt(W_diag)
    # Whitened score vector z_sc = r_score / sqrt(W_diag) -> under H0, E[z_sc z_sc^T] = I!
    z_sc = r_score / sqrt_W

    # Orthonormalize nuisance SI basis (2 real columns per complex SI basis vector) in Fisher metric W_diag!
    Q_nuis = []
    for sb in si_basis_vecs:
        c1_r = g_agc * np.concatenate([np.real(sb), np.imag(sb)]) * sqrt_W
        c2_r = g_agc * np.concatenate([-np.imag(sb), np.real(sb)]) * sqrt_W
        for col in (c1_r, c2_r):
            v = col.copy()
            for qv in Q_nuis:
                v -= qv * float(np.dot(qv, v))
            nv = float(np.linalg.norm(v))
            if nv > 1e-9:
                Q_nuis.append(v / nv)

    # Project z_sc orthogonal to Q_nuis
    for qv in Q_nuis:
        z_sc = z_sc - qv * float(np.dot(qv, z_sc))

    M_f = len(x_cpi_os)
    B_chips = len(x_cpi_os[0]) // Q_os

    scores = np.empty(len(tgt_grid), dtype=float)
    for idx_g, (tt, tn) in enumerate(tgt_grid):
        psi = np.concatenate([
            np.exp(1j * 2.0 * np.pi * tn * (m * B_chips) / float(N)) * shift_frac_dop_os(x_cpi_os[m], tt, tn, N, Q_os)
            for m in range(M_f)
        ])
        # Real 2-column Fisher-whitened target subspace [u_re, u_im]
        u1 = g_agc * np.concatenate([np.real(psi), np.imag(psi)]) * sqrt_W
        u2 = g_agc * np.concatenate([-np.imag(psi), np.real(psi)]) * sqrt_W
        for qv in Q_nuis:
            u1 -= qv * float(np.dot(qv, u1))
            u2 -= qv * float(np.dot(qv, u2))
        n1 = float(np.linalg.norm(u1))
        if n1 < 1e-11:
            scores[idx_g] = 0.0
            continue
        e1 = u1 / n1
        u2 -= e1 * float(np.dot(e1, u2))
        n2 = float(np.linalg.norm(u2))
        e2 = (u2 / n2) if n2 > 1e-11 else np.zeros_like(e1)
        scores[idx_g] = float(np.dot(e1, z_sc) ** 2 + np.dot(e2, z_sc) ** 2)

    best_i = int(np.argmax(scores))
    return float(scores[best_i]), tgt_grid[best_i][0], tgt_grid[best_i][1], float(np.mean(W_diag))


def optimize_fisher_canceller_and_agc(
    y_si_raw: np.ndarray,
    c0_vec: np.ndarray,
    c1_vec: np.ndarray,
    a_ls: np.ndarray,
    sig_w: float,
    edges: np.ndarray,
    g_candidates: np.ndarray,
    allow_tap_tilt: bool = True,
):
    """
    `Sol` §3 Prescription: Optimizes scalar AGC `g` (and 2-tap analog canceller tilt `a = a_ls + delta_a`
    within hardware tap power limit `||a||^2 <= 2.0`) to MAXIMIZE expected post-ADC Quantized Fisher
    Information `sum_n [J_re(g * Re(y_res[n])) + J_im(g * Im(y_res[n]))]`!
    Why can tilting `(a_0, a_1)` away from minimum-power LS boost Fisher Info?
    Because when `sig_w << delta_q` (dead-zone regime!), zero-dither or saturated samples have `J ~ 0`,
    whereas tuning `(g, a_0, a_1)` places the known SI trajectory right across quantizer thresholds `edges`!
    """
    C_mat = np.column_stack([c0_vec, c1_vec])

    def eval_mean_fisher(a_vec: np.ndarray, g_val: float) -> float:
        if float(np.sum(np.abs(a_vec) ** 2)) > 2.2:
            return -1e30
        y_res = y_si_raw - C_mat @ a_vec
        mu_s = g_val * y_res
        sig_1d = max(g_val * sig_w / math.sqrt(2.0), 1e-9)
        inv_s = 1.0 / sig_1d
        L = len(edges) + 1
        tot_j = 0.0
        for comp in (np.real(mu_s), np.imag(mu_s)):
            z = (edges[None, :] - comp[:, None]) * inv_s
            cdf = ndtr(z)
            pdf = np.exp(-0.5 * np.clip(z, -35.0, 35.0) ** 2) / math.sqrt(2.0 * math.pi)
            pa = np.empty((len(comp), L), dtype=float)
            pa[:, 0] = cdf[:, 0]; pa[:, 1:-1] = cdf[:, 1:] - cdf[:, :-1]; pa[:, -1] = 1.0 - cdf[:, -1]
            pa = np.maximum(pa, 1e-300)
            dpa = np.empty((len(comp), L), dtype=float)
            dpa[:, 0] = -pdf[:, 0] * inv_s; dpa[:, 1:-1] = -(pdf[:, 1:] - pdf[:, :-1]) * inv_s; dpa[:, -1] = pdf[:, -1] * inv_s
            # Target sensitivity scales as g_val^2 * J(mu_s)! (Notice: Fisher info wrt unscaled target amplitude alpha is g^2 * J!)
            tot_j += float(np.mean((g_val ** 2) * np.sum((dpa ** 2) / pa, axis=1)))
        return tot_j

    best_j = -1e30
    best_a = a_ls.copy()
    best_g = float(g_candidates[0])
    for gv in g_candidates:
        jv = eval_mean_fisher(a_ls, float(gv))
        if jv > best_j:
            best_j = jv; best_g = float(gv)

    if allow_tap_tilt:
        # Coordinate ascent on (a_0, a_1, log_g) to maximize pre-ADC target Fisher information g^2 * E[J]!
        cur_a = best_a.copy(); cur_g = best_g
        for step_a, step_g in [(0.08, 1.25), (0.025, 1.08)]:
            for idx_t in (0, 1):
                for d_dir in (1.0 + 0j, -1.0 + 0j, 1j, -1j):
                    cand_a = cur_a.copy(); cand_a[idx_t] += step_a * d_dir
                    jc = eval_mean_fisher(cand_a, cur_g)
                    if jc > best_j:
                        best_j = jc; cur_a = cand_a
            for gf in (1.0 / step_g, step_g):
                if cur_g * gf <= float(np.max(g_candidates)) * 1.0001:
                    jc = eval_mean_fisher(cur_a, cur_g * gf)
                    if jc > best_j:
                        best_j = jc; cur_g = cur_g * gf
        best_a, best_g = cur_a, cur_g

    return best_a, best_g, best_j


_W_SYS = None


def build_sys_defs(N: int = 128, L_cpp: int = 10, Q_os: int = 2):
    B = N + L_cpp
    p_rrc = rrc_taps(Q_os, M_p=6, alpha=0.25)
    Nd = 96
    N_pil = N - Nd  # 32 pilot DoFs (`Sol` §3: 32 pilot resources + 96 64-QAM payload!)

    # 1) AFDM (`c1 = 3 / (2N)`)
    A_af = daft_mat(N, 3.0 / (2.0 * N), 1.0 / (2.0 * math.pi * N))
    af_pmask = np.zeros(N, dtype=bool); af_pmask[:N_pil] = True
    af_didx = np.where(~af_pmask)[0]

    # 2) CP-OFDM (`c1 = 0`)
    A_of = daft_mat(N, 0.0, 0.0)
    of_pidx = np.round(np.linspace(0, N - 1, N_pil, endpoint=False)).astype(int)
    of_pmask = np.zeros(N, dtype=bool); of_pmask[of_pidx] = True
    of_didx = np.where(~of_pmask)[0]

    # 3) Single-Carrier SC-FDE (`A_sc = I_N`, time-domain symbols directly!)
    A_sc = np.eye(N, dtype=np.complex128)
    sc_pmask = np.zeros(N, dtype=bool); sc_pmask[:N_pil] = True
    sc_didx = np.where(~sc_pmask)[0]

    # 4) OTFS (`16 x 8 = 128`)
    F_8 = daft_mat(8, 0.0, 0.0)
    A_ot = np.kron(F_8.conj().T, np.eye(16, dtype=np.complex128))
    ot_pmask = np.zeros(N, dtype=bool); ot_pmask[:N_pil] = True
    ot_didx = np.where(~ot_pmask)[0]

    def make_P_ext(c1_v: float):
        P = np.zeros((B, N), dtype=np.complex128)
        for k in range(L_cpp):
            nn = k - L_cpp
            P[k, N + nn] = np.exp(-1j * 2.0 * np.pi * c1_v * (N ** 2 + 2.0 * N * nn))
        P[L_cpp:, :] = np.eye(N, dtype=np.complex128)
        return P

    return {
        "N": N, "L_cpp": L_cpp, "B": B, "Q_os": Q_os, "Nd": Nd, "N_pil": N_pil, "p_rrc": p_rrc,
        "waveforms": {
            "AFDM": (A_af, make_P_ext(3.0 / (2.0 * N)), af_didx, af_pmask),
            "OFDM": (A_of, make_P_ext(0.0), of_didx, of_pmask),
            "SCFDE": (A_sc, make_P_ext(0.0), sc_didx, sc_pmask),
            "OTFS": (A_ot, make_P_ext(0.0), ot_didx, ot_pmask),
        },
    }


def _init_w():
    global _W_SYS
    _W_SYS = build_sys_defs(N=128, L_cpp=10, Q_os=2)


def run_adc_scene(args):
    seed, n_bits, has_target, tgt_db, snr_si_to_noise_db, h2_amp, vga_max = args
    sysd = _W_SYS
    rng = np.random.default_rng(seed)
    N, L_cpp, B, Q_os, Nd, N_pil, p_rrc = sysd["N"], sysd["L_cpp"], sysd["B"], sysd["Q_os"], sysd["Nd"], sysd["N_pil"], sysd["p_rrc"]
    const = gray_qam(64)
    qpsk = np.array([-1 - 1j, -1 + 1j, 1 - 1j, 1 + 1j]) / math.sqrt(2.0)
    M_f = 4  # 4-frame CPI (`4 * 276 = 1104` oversampled complex samples)

    # Strong 3-tap SI channel (`|h_0|=1.0` at 0, `|h_1|=0.35` at 0.75 Ts, spillover `|h_2|=h2_amp` at 2.35 Ts!)
    h_si = np.array([
        1.00 * np.exp(1j * rng.uniform(0, 2 * np.pi)),
        (0.35 if h2_amp > 0.1 else 0.04) * np.exp(1j * rng.uniform(0, 2 * np.pi)),
        h2_amp * np.exp(1j * rng.uniform(0, 2 * np.pi)),
    ])
    tau_si = [0.0, 0.75, 2.35]

    # Target grid (`tau in [4.0 .. 8.5]` step 0.75 -> 7 delays x `nu in [0.65 .. 1.20]` step 0.1375 -> 5 Dopplers = 35 cells)
    t_taus = np.linspace(4.0, 8.5, 7)
    t_nus = np.linspace(0.65, 1.20, 5)
    tgt_grid = [(float(tt), float(tn)) for tt in t_taus for tn in t_nus]
    true_tt, true_tn = tgt_grid[int(rng.integers(0, len(tgt_grid)))]
    alpha_tgt = (10.0 ** (tgt_db / 20.0)) * np.exp(1j * rng.uniform(0, 2 * np.pi)) if has_target else 0.0j

    sig_w = 10.0 ** (-snr_si_to_noise_db / 20.0)
    L_tot = M_f * B * Q_os
    w_cpi = (sig_w / math.sqrt(2.0)) * (rng.standard_normal(L_tot) + 1j * rng.standard_normal(L_tot))

    tx_d = [rng.integers(0, 64, Nd) for _ in range(M_f)]
    # 6 candidate pilot sequences (seed 0 = nominal QPSK pilot; seeds 1..5 = candidate pilot shapes for Fisher/Oracle optimization!)
    pil_bank = [[qpsk[rng.integers(0, 4, N_pil)] for _ in range(M_f)] for _ in range(5)]

    use_midtread = vga_max < 10.0
    _, _, _, edges, _ = uniform_quantize_iq(np.zeros(1, dtype=np.complex128), n_bits, mid_tread=use_midtread)
    g_rms_nom = (0.95 if n_bits == 2 else 0.72) * math.sqrt(2.0)

    def make_cpi_os(wname: str, pil_seq_list: list):
        A_m, P_m, didx, pmask = sysd["waveforms"][wname]
        x_os_list = []
        for m in range(M_f):
            x = np.zeros(N, dtype=np.complex128)
            x[pmask] = pil_seq_list[m]
            x[didx] = const[tx_d[m]]
            se = P_m @ (A_m.conj().T @ x)
            x_os_list.append(upsample_rrc(se, p_rrc, Q_os))
        c0 = np.concatenate([shift_frac_dop_os(x_os_list[m], 0.0, 0.0, N, Q_os) for m in range(M_f)])
        c1 = np.concatenate([shift_frac_dop_os(x_os_list[m], 1.0, 0.0, N, Q_os) for m in range(M_f)])
        s_sp0 = np.concatenate([shift_frac_dop_os(x_os_list[m], tau_si[0], 0.0, N, Q_os) for m in range(M_f)])
        s_sp1 = np.concatenate([shift_frac_dop_os(x_os_list[m], tau_si[1], 0.0, N, Q_os) for m in range(M_f)])
        s_sp2 = np.concatenate([shift_frac_dop_os(x_os_list[m], tau_si[2], 0.0, N, Q_os) for m in range(M_f)])
        y_si = h_si[0] * s_sp0 + h_si[1] * s_sp1 + h_si[2] * s_sp2
        B_chips = B
        y_tgt = np.concatenate([
            alpha_tgt * np.exp(1j * 2.0 * np.pi * true_tn * (m * B_chips) / float(N)) * shift_frac_dop_os(x_os_list[m], true_tt, true_tn, N, Q_os)
            for m in range(M_f)
        ])
        # LS 2-tap analog canceller minimizing total pre-ADC SI power ||y_si - C a||^2
        C_an = np.column_stack([c0, c1])
        a_ls = np.linalg.lstsq(C_an, y_si, rcond=None)[0]
        if float(np.sum(np.abs(a_ls) ** 2)) > 2.0:
            a_ls *= math.sqrt(2.0 / float(np.sum(np.abs(a_ls) ** 2)))
        return x_os_list, c0, c1, [s_sp0, s_sp1, s_sp2], y_si, y_tgt, a_ls

    out = {}

    # --- 1) Pub_AFDM_Bussgang_LSAnalog (`Gourar + Sui`: LS analog canceller + RMS AGC + Bussgang linear GLRT) ---
    xos_af0, c0_af, c1_af, sbasis_af, ysi_af, ytgt_af, als_af = make_cpi_os("AFDM", pil_bank[0])
    yres_ls_af = ysi_af - (als_af[0] * c0_af + als_af[1] * c1_af)
    rms_pre_af = max(float(np.sqrt(np.mean(np.abs(yres_ls_af) ** 2) + sig_w ** 2)), 1e-9)
    g_pub = min(g_rms_nom / rms_pre_af, vga_max)
    y_tot_af0 = yres_ls_af + ytgt_af + w_cpi
    kre_pub, kim_pub, ymid_pub, _, _ = uniform_quantize_iq(g_pub * y_tot_af0, n_bits, mid_tread=use_midtread)
    # Bussgang digital SI cancellation: project ymid_pub orthogonal to ALL SI + analog canceller delays [sbasis_af + c0 + c1]!
    Q_lin = []
    res_pub = ymid_pub.copy()
    for sb in list(sbasis_af) + [c0_af, c1_af]:
        v = sb.copy()
        for qv in Q_lin: v -= qv * np.vdot(qv, v)
        nv = float(np.linalg.norm(v))
        if nv > 1e-9:
            u = v / nv; Q_lin.append(u); res_pub -= u * np.vdot(u, res_pub)
    sc_pub_grid = np.empty(len(tgt_grid))
    for i, (tt, tn) in enumerate(tgt_grid):
        psi = np.concatenate([np.exp(1j * 2.0 * np.pi * tn * (m * B) / float(N)) * shift_frac_dop_os(xos_af0[m], tt, tn, N, Q_os) for m in range(M_f)])
        for qv in Q_lin: psi -= qv * np.vdot(qv, psi)
        nv = float(np.linalg.norm(psi))
        sc_pub_grid[i] = (abs(np.vdot(psi / nv, res_pub)) ** 2) if nv > 1e-9 else 0.0
    bi_p = int(np.argmax(sc_pub_grid))
    stat_pub = float(sc_pub_grid[bi_p] / max(float(np.median(sc_pub_grid)), 1e-15))
    out["Pub_AFDM_Bussgang_LSAnalog"] = (stat_pub, int(abs(tgt_grid[bi_p][0] - true_tt) < 0.4 and abs(tgt_grid[bi_p][1] - true_tn) < 0.08))

    # --- 2) Steelman_A_AFDM_Probit_OptAGC (LS analog canceller + 1D optimal AGC scan <= vga_max + Blind Probit-MLE SI Fit + Probit Rao GLRT!) ---
    g_scan = np.minimum(g_pub * np.geomspace(0.25, 4.5, 15), vga_max)
    _, g_opt_af, _ = optimize_fisher_canceller_and_agc(ysi_af, c0_af, c1_af, als_af, sig_w, edges, g_scan, allow_tap_tilt=False)
    g_opt_af = min(g_opt_af, vga_max)
    kre_sa1, kim_sa1, ymid_sa1, _, _ = uniform_quantize_iq(g_opt_af * y_tot_af0, n_bits, mid_tread=use_midtread)
    full_si_af = list(sbasis_af) + [c0_af, c1_af]
    Phi_si_af = np.column_stack(full_si_af)
    mu_hat_sa1 = fit_residual_si_probit_mle(kre_sa1, kim_sa1, Phi_si_af, g_opt_af * sig_w, edges, ymid_sa1)
    st_sa1, bt_sa1, bn_sa1, _ = probit_rao_glrt_detector(
        kre_sa1, kim_sa1, mu_hat_sa1, g_opt_af, g_opt_af * sig_w, edges, xos_af0, full_si_af, tgt_grid, N, Q_os
    )
    out["Steelman_A_AFDM_Probit_OptAGC"] = (st_sa1, int(abs(bt_sa1 - true_tt) < 0.4 and abs(bn_sa1 - true_tn) < 0.08))

    # --- 3) Steelman_A & Steelman_S: Joint Fisher Optimization of `(a_0, a_1, g <= vga_max)` + Blind Probit-MLE SI Fit + Probit Rao GLRT! ---
    for wname in ("AFDM", "OFDM", "SCFDE", "OTFS"):
        xos_w, c0_w, c1_w, sbasis_w, ysi_w, ytgt_w, als_w = make_cpi_os(wname, pil_bank[0])
        yres_w0 = ysi_w - (als_w[0] * c0_w + als_w[1] * c1_w)
        rms_w = max(float(np.sqrt(np.mean(np.abs(yres_w0) ** 2) + sig_w ** 2)), 1e-9)
        g_sc_w = np.minimum((g_rms_nom / rms_w) * np.geomspace(0.25, 4.5, 15), vga_max)
        a_fj, g_fj, _ = optimize_fisher_canceller_and_agc(ysi_w, c0_w, c1_w, als_w, sig_w, edges, g_sc_w, allow_tap_tilt=True)
        g_fj = min(g_fj, vga_max)
        yres_fj = ysi_w - (a_fj[0] * c0_w + a_fj[1] * c1_w)
        kre_w, kim_w, ymid_w, _, _ = uniform_quantize_iq(g_fj * (yres_fj + ytgt_w + w_cpi), n_bits, mid_tread=use_midtread)
        full_si_w = list(sbasis_w) + [c0_w, c1_w]
        mu_hat_w = fit_residual_si_probit_mle(kre_w, kim_w, np.column_stack(full_si_w), g_fj * sig_w, edges, ymid_w)
        st_w, bt_w, bn_w, _ = probit_rao_glrt_detector(
            kre_w, kim_w, mu_hat_w, g_fj, g_fj * sig_w, edges, xos_w, full_si_w, tgt_grid, N, Q_os
        )
        key = "Steelman_A_AFDM_FisherJoint" if wname == "AFDM" else f"Steelman_S_{wname}_FisherJoint"
        out[key] = (st_w, int(abs(bt_w - true_tt) < 0.4 and abs(bn_w - true_tn) < 0.08))

    # --- 4) Same-Hardware Genie Oracle (`Oracle_SameHW_AFDM_Probit`: searches over pilot_bank + `(a_0, a_1, g <= vga_max)` + GENIE true `yres_o`!) ---
    best_orac_j = -1e30
    best_orac_cfg = None
    for p_seq in pil_bank:
        xos_o, c0_o, c1_o, sbasis_o, ysi_o, ytgt_o, als_o = make_cpi_os("AFDM", p_seq)
        yres_o0 = ysi_o - (als_o[0] * c0_o + als_o[1] * c1_o)
        rms_o = max(float(np.sqrt(np.mean(np.abs(yres_o0) ** 2) + sig_w ** 2)), 1e-9)
        g_sc_o = np.minimum((g_rms_nom / rms_o) * np.geomspace(0.25, 5.0, 17), vga_max)
        a_o, g_o, j_o = optimize_fisher_canceller_and_agc(ysi_o, c0_o, c1_o, als_o, sig_w, edges, g_sc_o, allow_tap_tilt=True)
        g_o = min(g_o, vga_max)
        if j_o > best_orac_j:
            best_orac_j = j_o
            best_orac_cfg = (xos_o, c0_o, c1_o, sbasis_o, ysi_o, ytgt_o, a_o, g_o)
    xos_o, c0_o, c1_o, sbasis_o, ysi_o, ytgt_o, a_o, g_o = best_orac_cfg
    yres_o = ysi_o - (a_o[0] * c0_o + a_o[1] * c1_o)
    kre_o, kim_o, _, _, _ = uniform_quantize_iq(g_o * (yres_o + ytgt_o + w_cpi), n_bits, mid_tread=use_midtread)
    st_o, bt_o, bn_o, _ = probit_rao_glrt_detector(
        kre_o, kim_o, g_o * yres_o, g_o, g_o * sig_w, edges, xos_o, list(sbasis_o) + [c0_o, c1_o], tgt_grid, N, Q_os
    )
    out["Oracle_SameHW_AFDM_Probit"] = (st_o, int(abs(bt_o - true_tt) < 0.4 and abs(bn_o - true_tn) < 0.08))

    # --- 5) Infinite-Bit ADC Upper Bound (`Oracle_InfBit_GLRT`: exact unquantized pre-ADC subspace GLRT!) ---
    y_inf = yres_ls_af + ytgt_af + w_cpi
    res_inf = y_inf.copy()
    for qv in Q_lin:
        res_inf -= qv * np.vdot(qv, res_inf)
    sc_inf = np.empty(len(tgt_grid))
    for i, (tt, tn) in enumerate(tgt_grid):
        psi = np.concatenate([np.exp(1j * 2.0 * np.pi * tn * (m * B) / float(N)) * shift_frac_dop_os(xos_af0[m], tt, tn, N, Q_os) for m in range(M_f)])
        for qv in Q_lin: psi -= qv * np.vdot(qv, psi)
        nv = float(np.linalg.norm(psi))
        sc_inf[i] = (abs(np.vdot(psi / nv, res_inf)) ** 2) / (sig_w ** 2 / 2.0) if nv > 1e-9 else 0.0
    bi_inf = int(np.argmax(sc_inf))
    out["Oracle_InfBit_GLRT"] = (float(sc_inf[bi_inf]), int(abs(tgt_grid[bi_inf][0] - true_tt) < 0.4 and abs(tgt_grid[bi_inf][1] - true_tn) < 0.08))

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default=os.path.join(REPO_ROOT, "ideas", "r15", "out_new3_lowbit_adc_sic_isac.json"))
    args = ap.parse_args()

    t0 = time.perf_counter()
    seed_base = 202611269700 if args.smoke else 202611266500
    n_h0 = 16 if args.smoke else 140
    n_h1 = 10 if args.smoke else 100

    # Three sharp regimes probing both (a) strong spillover SI quantization floor & (b) low-noise Fisher boundary:
    # R1: 2-bit ADC, weak target -43 dB below SI, pre-ADC SNR = 35 dB (realistic thermal noise + 2-bit quantization!)
    # R2: 2-bit ADC, weak target -48 dB below SI, pre-ADC SNR = 42 dB (extreme weak-echo 2-bit Fisher limit!)
    # R3: 3-bit ADC, weak target -48 dB below SI, pre-ADC SNR = 40 dB (3-bit dynamic-range knee!)
    # Also cap g_fj inside optimize_fisher_canceller_and_agc? Already capped via g_o = min(..., vga_max); cap step_g inside loop:
    regimes = [
        ("R1_2bitADC_StrongSpill_TgtM43dB_SNR35dB", 2, -43.0, 35.0, 0.30, 100.0),
        ("R2_2bitADC_StrongSpill_TgtM48dB_SNR42dB", 2, -48.0, 42.0, 0.30, 100.0),
        ("R3_3bitADC_StrongSpill_TgtM48dB_SNR40dB", 3, -48.0, 40.0, 0.30, 100.0),
        ("R4_2bitADC_FiniteVGA_DeadZone_TgtM38dB",  2, -38.0, 44.0, 0.02, 2.5),
    ]

    res = {
        "problem": "m_new3_LowBitADC_FiniteAnalogSIC_ISAC",
        "anchors": [
            "Sui IEEE TCOM 2026 (10.1109/tcomm.2026.3701879)",
            "Gourar arXiv:2609.14030",
            "Mo-Schniter-Heath IEEE TSP 2017",
            "Korpi et al. IEEE TWC 2014",
        ],
        "seed_base": seed_base,
        "smoke": bool(args.smoke),
        "regimes": {},
    }

    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_w) as pool:
        for r_i, (rname, nb, tdb, sdb, h2a, vgam) in enumerate(regimes):
            tr = time.perf_counter()
            h0_rows = list(pool.map(run_adc_scene, [(seed_base + r_i * 100000 + i, nb, False, tdb, sdb, h2a, vgam) for i in range(n_h0)]))
            arms = list(h0_rows[0].keys())
            idx_q = min(n_h0 - 1, max(0, int(math.floor((n_h0 + 1) * 0.95)) - 1))
            taus = {a: float(sorted(r[a][0] for r in h0_rows)[idx_q]) for a in arms}

            h1_rows = list(pool.map(run_adc_scene, [(seed_base + r_i * 100000 + 50000 + i, nb, True, tdb, sdb, h2a, vgam) for i in range(n_h1)]))
            reg_s = {}
            print(f"\n[{rname}] (b={nb}, tgt={tdb}dB, SNR_pre={sdb}dB, n={n_h1}, {round(time.perf_counter()-tr,2)}s):", flush=True)
            for a in arms:
                hits = [1 if (r[a][0] > taus[a] and r[a][1] == 1) else 0 for r in h1_rows]
                pd_v = float(np.mean(hits))
                reg_s[a] = {"wt_pd": pd_v, "hits": int(sum(hits)), "n_scenes": n_h1, "tau_h0_95": round(taus[a], 3)}
                print(f"  {a:34s}: Pd = {pd_v*100:5.1f}% ({sum(hits)}/{n_h1}) | tau95={taus[a]:.2f}", flush=True)
            res["regimes"][rname] = {"n_bits": nb, "tgt_db": tdb, "snr_pre_db": sdb, "arms": reg_s, "elapsed_s": round(time.perf_counter() - tr, 2)}

    res["total_elapsed_s"] = round(time.perf_counter() - t0, 2)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(res, fp, indent=2, allow_nan=False)
    print(f"\nSaved -> {args.out} (total {res['total_elapsed_s']}s)", flush=True)


if __name__ == "__main__":
    main()
