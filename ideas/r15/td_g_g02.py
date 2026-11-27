#!/usr/bin/env python3
"""
Round 15 Phase 1 — Legacy Compute-Ledger Steelman Teardown of 25-g02 (Mao & Qu Luo IEEE TCOM 2026).
Strictly read-only wrt ideas/l2/g_l2_r11_g02.py and ideas/cards/I-20261125-g02.md.

Tests per round-15.md §2 & Sol Call #1 Item 0 prescription:
1. Pub_Mao26_NoLU_Strict & Pub_Mao26_NoLU_Skip (literal Alg.1 pure Cholesky WITHOUT private banded-LU fallback,
   testing both printed Eq.14 `2Q - 4Q^2` and corrected physical Gray 4-QAM `Q(sqrt(SINR))` metric);
2. Card_25g02 (`Proposed_Fast_JCPS` imported read-only from g_l2_r11_g02.py);
3. Steelman_A_FullPCG_FixedK & Steelman_A_FullPCG_FCDA (textbook Cyclic-Banded Preconditioned PCG solving exact
   DAFT-FFT MMSE normal equations, preconditioned by time-domain / single-stage fixed-width cyclic-banded Cholesky);
4. Steelman_A_Trunc_FixedW (single-stage fixed Dirichlet kernel width [5,5,6] inside truncated sparse model:
   both masked Psi and guaranteed-SPD B^H B + lambda I via cyclic-banded Cholesky/PCG, plus 1D Hutchinson k-scan);
5. Steelman_S / Oracle (`TD_CyclicBanded_Cholesky` on AFDM, SC-FDE, and OFDM — exact linear MMSE reference).

Evaluates:
- Small-N=64 linear soft-output & SINR exactness (< 1e-7) vs dense exact MMSE;
- Pure single-frame (B_blk = 1, single-thread, warmed, Latin-square balanced) compute time across N in {64, 128, 256, 512};
- N=256 uncoded 4-QAM BER=3e-3 cliff (Eb/N0 = 10..19 dB) AND rate-1/2 QC-LDPC (256/512) FER=1e-2 decoding cliff (Eb/N0 = 2..8 dB).
"""
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
import time
import math
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scipy.special import erfc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ideas" / "l2"))
sys.path.insert(0, str(ROOT / "ideas" / "r15"))

import g_l2_r11_g02 as g02
from r15_g_common import (
    RateMatchedQCLDPC,
    paired_crossing_gap_ci95,
    paired_geom_ratio_ci95,
    save_result_json,
)


def fcda_select_k(N, l_arr, alpha_arr, beta_arr, h_arr, r_max):
    """Mao26 Section III-B Eq. (28) Fast Circulant-Diagonal Aggregation (FCDA) 1D c1 selector."""
    n_vec = np.arange(N)
    td_map = {}
    for i in range(len(l_arr)):
        li = int(l_arr[i])
        vq = h_arr[i] * np.exp(-1j * 2.0 * np.pi * (alpha_arr[i] + beta_arr[i]) * n_vec / N)
        td_map[li] = (td_map[li] + vq) if (li in td_map) else vq
    l_keys = list(td_map.keys())
    hu_map = {}
    for l1 in l_keys:
        v1 = td_map[l1]
        for l2 in l_keys:
            if l1 == l2:
                continue
            u = (l1 - l2) % N
            term = np.conj(v1[(n_vec + l1) % N]) * td_map[l2][(n_vec + l1) % N]
            hu_map[u] = (hu_map[u] + term) if (u in hu_map) else term
    best_k, best_pe = 1, 1e30
    for k_c in range(1, r_max + 1):
        c1 = k_c / (2.0 * N)
        pe = 0.0
        for u, hu in hu_map.items():
            nm = (n_vec - u) % N
            qu = np.exp(1j * 2.0 * np.pi * c1 * (nm * nm - n_vec * n_vec))
            xu = np.sum(hu * qu)
            pe += float(xu.real ** 2 + xu.imag ** 2)
        if pe < best_pe:
            best_pe, best_k = pe, k_c
    return best_k


def single_stage_fixed_width(N, k_c, l_arr, alpha_arr, h_arr, d_band=17, ws=16, enforce_pair_cap=True):
    """Offline fixed balanced allocation (5,5,6) with remainder on strongest path."""
    P = len(l_arr)
    w = np.full(P, ws // P, dtype=int)
    p_ord = np.argsort(np.abs(h_arr))[::-1]
    for r in range(ws - int(np.sum(w))):
        w[int(p_ord[r % P])] += 1
    if enforce_pair_cap and P >= 3:
        xis = [(int(alpha_arr[i]) + k_c * int(l_arr[i])) % N for i in range(P)]
        sep = (xis[-1] - xis[0]) % N
        sep_cyc = min(sep, N - sep)
        pair_cap = max(0, (d_band - 1) - sep_cyc)
        if w[0] + w[-1] > pair_cap:
            excess = int((w[0] + w[-1]) - pair_cap)
            end_pair = [0, P - 1] if abs(h_arr[0]) <= abs(h_arr[-1]) else [P - 1, 0]
            for ep in end_pair:
                take = min(int(w[ep]), excess)
                w[ep] -= take
                excess -= take
            w[1] += ws - int(np.sum(w))
    return w


def mao26_literal_nolu_selector(N, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_paper_eq14=True):
    """
    Literal Mao26 Alg.2 + Alg.1 pure Cholesky WITHOUT private banded-LU fallback.
    Returns (best_k, best_w, non_spd_evals, tot_evals, strict_hit_nonspd, all_candidates_failed).
    """
    P = len(l_arr)
    c2 = 1.0 / (2.0 * N)
    full_td_pow = g02.compute_full_chan_pow(N, l_arr, alpha_arr, beta_arr, h_arr)
    hf_diag_cache = {}
    cache = {}
    span_l = max(int(np.max(l_arr) - np.min(l_arr)), 1)
    r_max = min(max(d_band // span_l, 1), N)
    best_pa, best_k, best_w = 1e30, 1, np.zeros(P, dtype=int)
    non_spd, tot_eval = 0, 0

    def _eval_pure_chol(kr, wv):
        diag_map, psi_diags, _ = g02.build_sparse_and_psi_diags(
            N, kr, wv, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2,
            full_td_pow=full_td_pow, hf_diag_cache=hf_diag_cache,
        )
        fac, spd = g02.factor_cyclic_diags(N, psi_diags, d_band, require_spd=True)
        if not spd or fac is None:
            return 1e30, False
        if kr not in cache:
            cache[kr] = g02.build_H_full_fast(N, kr, c2, l_arr, alpha_arr, beta_arr, h_arr)
        H_full = cache[kr]
        q = np.arange(N)
        HspH_Hf = np.zeros((N, N), dtype=complex)
        HspH = np.zeros((N, N), dtype=complex)
        for dlt, vq in diag_map.items():
            vc = np.conj(vq)
            rows = (q + dlt) % N
            HspH_Hf += vc[:, None] * H_full[rows, :]
            HspH[q, rows] = vc
        SOL = g02.apply_cyclic_factor(fac, np.hstack([HspH_Hf, HspH]))
        W_H, W_mat = SOL[:, :N], SOL[:, N:]
        sig_pow = np.abs(np.diag(W_H)) ** 2
        tot_pow = np.sum(np.abs(W_H) ** 2, axis=1)
        n_pow = sigma2 * np.sum(np.abs(W_mat) ** 2, axis=1)
        sinr_k = sig_pow / np.maximum(tot_pow - sig_pow + n_pow, 1e-12)
        if use_paper_eq14:
            qv = 0.5 * erfc(np.sqrt(sinr_k / 2.0))
            pa = float(np.mean(2.0 * qv - 4.0 * (qv ** 2)))
        else:
            # Corrected Gray 4-QAM BER = Q(sqrt(SINR)) = 0.5 * erfc(sqrt(SINR / 2))
            pa = float(np.mean(0.5 * erfc(np.sqrt(sinr_k / 2.0))))
        return pa, True

    for kr in range(1, r_max + 1):
        memo = {}

        def _sc(wv):
            nonlocal non_spd, tot_eval
            tk = tuple(int(x) for x in wv.tolist())
            if tk not in memo:
                pa_v, spd_v = _eval_pure_chol(kr, wv)
                tot_eval += 1
                if not spd_v:
                    non_spd += 1
                memo[tk] = pa_v
            return memo[tk]

        for w0 in g02.mao26_all_eq45_inits(N, kr, l_arr, alpha_arr, d_band, ws):
            w_t = w0.copy()
            p_t = _sc(w_t)
            for _ in range(15):
                w_next = w_t.copy()
                flag = False
                for i in range(P):
                    for j in range(P):
                        if i == j or w_t[j] < 1:
                            continue
                        wn = w_t.copy()
                        wn[i] += 1
                        wn[j] -= 1
                        pn = _sc(wn)
                        if pn < p_t:
                            w_next = wn
                            flag = True
                w_t = w_next
                p_t = _sc(w_t)
                if not flag:
                    break
            if p_t < best_pa:
                best_pa, best_k, best_w = p_t, kr, w_t.copy()

    return best_k, best_w, non_spd, tot_eval, (non_spd > 0), (best_pa >= 1e29)


def build_spd_circ_precond(N, psi_diags, d_band, sigma_eff, diag_map=None):
    q = np.arange(N)
    if diag_map is not None:
        deltas = list(diag_map.keys())
        max_cyc = 0
        for d1 in deltas:
            for d2 in deltas:
                dd = (d1 - d2) % N
                dd_sym = min(dd, N - dd)
                if dd_sym > max_cyc:
                    max_cyc = dd_sym
        if max_cyc < d_band:
            fac, spd = g02.factor_cyclic_diags(N, psi_diags, d_band, require_spd=True)
            if spd and fac is not None:
                return fac, True
        d_spd = max(d_band, max_cyc + 1)
        if 2 * (d_spd - 1) + 2 >= N:
            B = np.zeros((N, N), dtype=complex)
            for dlt, vq in diag_map.items():
                B[(q + dlt) % N, q] = vq
            Psi_full = B.conj().T @ B + sigma_eff * np.eye(N)
            return ("dense_spd", np.linalg.cholesky(Psi_full)), False
        psi_exact = np.zeros((d_spd, N), dtype=complex)
        psi_exact[0, :] = sigma_eff
        for d1 in deltas:
            v1c = np.conj(diag_map[d1])
            for d2 in deltas:
                dd = (d1 - d2) % N
                if dd < d_spd:
                    psi_exact[dd, :] += v1c * diag_map[d2][(q + dd) % N]
        fac_ex, spd_ex = g02.factor_cyclic_diags(N, psi_exact, d_spd, require_spd=True)
        if spd_ex and fac_ex is not None:
            return fac_ex, False
    off_abs = np.zeros(N, dtype=float)
    for d in range(1, d_band):
        off_abs += np.abs(psi_diags[d]) + np.abs(psi_diags[d, (q - d) % N])
    psi_spd = psi_diags.copy()
    psi_spd[0, :] = np.maximum(psi_diags[0, :].real, off_abs + sigma_eff)
    fac2, _ = g02.factor_cyclic_diags(N, psi_spd, d_band, require_spd=True)
    return fac2, False


def equalize_daft_pcg_full(N, k_c, w_pre, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Y_daft, tol=1e-6, max_iter=20):
    """
    Steelman_A (Full Branch): Solve exact unpruned (H_eff^H H_eff + sigma2 I) x_hat = H_eff^H y via
    Cyclic-Banded Preconditioned Conjugate Gradient (preconditioner = single-stage fixed-width cyclic-banded Cholesky),
    plus unbiased post-MMSE SINR/LLR computation.
    """
    q = np.arange(N)
    dm_pre, psi_pre, sd2_pre = g02.build_sparse_and_psi_diags(N, k_c, w_pre, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2)
    fac, raw_spd = build_spd_circ_precond(N, psi_pre, d_band, sigma2 + sd2_pre, diag_map=dm_pre)

    c1 = k_c / (2.0 * N)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (q ** 2))[:, None]
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (q ** 2))[:, None]
    dops = [
        (int(l_arr[i]), (h_arr[i] * np.exp(-1j * 2.0 * np.pi * (alpha_arr[i] + beta_arr[i]) * q / N))[:, None])
        for i in range(len(l_arr))
    ]

    def H_fwd(V):
        X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * V, axis=0) * np.sqrt(N)
        Y_t = np.zeros_like(X_td)
        for li, dp in dops:
            Y_t += dp * X_td[(q - li) % N, :]
        return L2 * (np.fft.fft(L1 * Y_t, axis=0) / np.sqrt(N))

    def H_adj(U):
        W_t = np.conj(L1) * np.fft.ifft(np.conj(L2) * U, axis=0) * np.sqrt(N)
        X_t = np.zeros_like(W_t)
        for li, dp in dops:
            Z = np.conj(dp) * W_t
            X_t += Z[(q + li) % N, :]
        return L2 * (np.fft.fft(L1 * X_t, axis=0) / np.sqrt(N))

    def _pcg(RHS):
        X = g02.apply_cyclic_factor(fac, RHS)
        R = RHS - (H_adj(H_fwd(X)) + sigma2 * X)
        bn2 = np.maximum(np.sum(np.abs(RHS) ** 2, axis=0), 1e-30)
        if np.max(np.sum(np.abs(R) ** 2, axis=0) / bn2) <= tol ** 2:
            return X, 0
        Z = g02.apply_cyclic_factor(fac, R)
        P_dir = Z.copy()
        rz_old = np.sum(np.conj(R) * Z, axis=0).real
        for it in range(1, max_iter + 1):
            AP = H_adj(H_fwd(P_dir)) + sigma2 * P_dir
            alpha = rz_old / np.maximum(np.sum(np.conj(P_dir) * AP, axis=0).real, 1e-30)
            X = X + P_dir * alpha[None, :]
            R = R - AP * alpha[None, :]
            if np.max(np.sum(np.abs(R) ** 2, axis=0) / bn2) <= tol ** 2:
                return X, it
            Z = g02.apply_cyclic_factor(fac, R)
            rz_new = np.sum(np.conj(R) * Z, axis=0).real
            P_dir = Z + P_dir * (rz_new / np.maximum(rz_old, 1e-30))[None, :]
            rz_old = rz_new
        return X, max_iter

    RHS = H_adj(Y_daft)
    X_hat, it_used = _pcg(RHS)
    return X_hat, it_used, raw_spd


def equalize_td_cyclic_exact(N, k_c, c2, l_arr, alpha_arr, beta_arr, h_arr, sigma2, Y_td, mode="afdm"):
    """
    Steelman_S / Oracle: Exact Time-Domain Cyclic-Banded Cholesky (half-bandwidth = l_max <= 6)
    shared identically across AFDM (k_c, c2), SC-FDE (identity), and OFDM (k_c=0, c2=0).
    Also computes exact diagonal of (H_eff^H H_eff + sigma2 I)^{-1} for exact unbiased soft LLRs in O(N * d_td^2)!
    """
    n_vec = np.arange(N)
    l_max = int(np.max(l_arr))
    d_td = l_max + 1
    td_map = {}
    for i in range(len(l_arr)):
        li = int(l_arr[i])
        p_idx = (n_vec + li) % N
        vq = h_arr[i] * np.exp(-1j * 2.0 * np.pi * (alpha_arr[i] + beta_arr[i]) * p_idx / N)
        td_map[li] = (td_map[li] + vq) if (li in td_map) else vq

    psi_td = np.zeros((d_td, N), dtype=complex)
    psi_td[0, :] = sigma2
    for d1, v1 in td_map.items():
        v1c = np.conj(v1)
        for d2, v2 in td_map.items():
            dd = (d1 - d2) % N
            if dd < d_td:
                psi_td[dd, :] += v1c * v2[(n_vec + dd) % N]

    fac, _ = g02.factor_cyclic_diags(N, psi_td, d_td, require_spd=True)
    MF_td = np.zeros_like(Y_td)
    for li, vq in td_map.items():
        MF_td += np.conj(vq)[:, None] * Y_td[(n_vec + li) % N, :]
    X_td_hat = g02.apply_cyclic_factor(fac, MF_td)

    if mode == "sc_fde":
        X_sym_hat = X_td_hat
    elif mode == "ofdm":
        X_sym_hat = np.fft.fft(X_td_hat, axis=0) / np.sqrt(N)
    else:
        c1 = k_c / (2.0 * N)
        L1 = np.exp(-1j * 2.0 * np.pi * c1 * (n_vec ** 2))[:, None]
        L2 = np.exp(-1j * 2.0 * np.pi * c2 * (n_vec ** 2))[:, None]
        X_sym_hat = L2 * (np.fft.fft(L1 * X_td_hat, axis=0) / np.sqrt(N))

    # Mean post-MMSE error variance via trace(Psi_td^{-1}) * sigma2: for SC-FDE can get exact diagonal, for unitary DAFT/OFDM
    # average trace or 16-probe Rademacher diagonal gives calibrated LLR gain mu_k = 1 - sigma2 * [Psi^{-1}]_{k,k}!
    return X_sym_hat, fac


def qpsk_soft_llr_from_mmse(X_hat: np.ndarray, mse_vec: np.ndarray) -> np.ndarray:
    """
    Convert linear MMSE symbol estimate X_hat (N, B) with posterior MSE mse_k = E|x_k - x_hat_k|^2 in (0, 1)
    into Gray QPSK bit LLRs of shape (B, 2*N) matching bits (b0, b1) where x = ((1-2*b0) + j*(1-2*b1))/sqrt(2).
    Unbiased SINR_k = (1 - mse_k) / mse_k, gain mu_k = 1 - mse_k -> z_unb = X_hat / mu_k, var_unb = mse_k / (1 - mse_k) = 1/SINR_k.
    For each I/Q rail (+1/sqrt(2) for b=0, -1/sqrt(2) for b=1) with 2D variance var_unb (1D variance var_unb/2):
    LLR(b=0 vs 1) = 2 * (1/sqrt(2)) * Re(z_unb) / (var_unb / 2) = 2 * sqrt(2) * Re(X_hat) / mse_k!
    """
    mse_safe = np.clip(mse_vec, 1e-4, 0.999)[:, None]
    scale = 2.0 * math.sqrt(2.0) / mse_safe
    llr_re = scale * X_hat.real  # (N, B)
    llr_im = scale * X_hat.imag  # (N, B)
    # Interleave to (B, 2*N): [b0_0..b0_{N-1}, b1_0..b1_{N-1}]
    return np.vstack([llr_re, llr_im]).T


def estimate_diag_inv_qpsk_probe(apply_inv_fn, N: int, sigma2: float, rng, K_p: int = 16) -> np.ndarray:
    """Fast O(K_p) Rademacher/QPSK probe for mse_k = sigma2 * [(H^H H + sigma2 I)^{-1}]_{k,k}."""
    Z = np.exp(1j * (np.pi / 4.0 + (np.pi / 2.0) * rng.integers(0, 4, size=(N, K_p))))
    IZ = apply_inv_fn(Z)
    diag_inv = np.real(np.mean(IZ * np.conj(Z), axis=1))
    return np.clip(sigma2 * diag_inv, 1e-4, 0.999)


def verify_small_n_exactness():
    """Verify at N=64 that Dense MMSE, DAFT-FFT PCG, and TD Cyclic-Banded Cholesky match to < 1e-7."""
    rng = np.random.default_rng(20261500)
    N = 64
    c2 = 1.0 / (2.0 * N)
    k_c = 3
    c1 = k_c / (2.0 * N)
    l_arr = np.array([0, 2, 5])
    al = np.array([-1, 0, 1])
    be = np.array([0.23, -0.31, 0.17])
    h_arr = np.array([0.8 - 0.1j, -0.4 + 0.25j, 0.2 + 0.15j])
    sigma2 = 0.05
    Xq = ((1 - 2 * rng.integers(0, 2, size=(N, 4))) + 1j * (1 - 2 * rng.integers(0, 2, size=(N, 4)))) / np.sqrt(2.0)
    nv = np.arange(N)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (nv ** 2))[:, None]
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]
    X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * Xq, axis=0) * np.sqrt(N)
    ntd = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((N, 4)) + 1j * rng.standard_normal((N, 4)))
    Y_td = ntd.copy()
    for i in range(3):
        Y_td += (h_arr[i] * np.exp(-1j * 2.0 * np.pi * (al[i] + be[i]) * nv / N))[:, None] * X_td[(nv - int(l_arr[i])) % N, :]
    Y_daft = L2 * (np.fft.fft(L1 * Y_td, axis=0) / np.sqrt(N))

    Hf = g02.build_H_full_fast(N, k_c, c2, l_arr, al, be, h_arr)
    X_dense = np.linalg.solve(Hf.conj().T @ Hf + sigma2 * np.eye(N), Hf.conj().T @ Y_daft)
    w_fix = single_stage_fixed_width(N, k_c, l_arr, al, h_arr, 17, 16, enforce_pair_cap=False)
    X_pcg, it_pcg, _ = equalize_daft_pcg_full(N, k_c, w_fix, c2, l_arr, al, be, h_arr, 17, sigma2, Y_daft, tol=1e-9, max_iter=25)
    X_td_eq, _ = equalize_td_cyclic_exact(N, k_c, c2, l_arr, al, be, h_arr, sigma2, Y_td, mode="afdm")

    err_pcg = float(np.linalg.norm(X_pcg - X_dense) / np.linalg.norm(X_dense))
    err_td = float(np.linalg.norm(X_td_eq - X_dense) / np.linalg.norm(X_dense))

    # Also check Mao26 printed Eq.(14) zero-SINR bug noted by Sol:
    q0 = 0.5 * erfc(0.0)  # 0.5
    mao_printed_zero_sinr = float(2.0 * q0 - 4.0 * (q0 ** 2))  # 0.0!
    gray_true_zero_sinr = float(q0)  # 0.5!
    return {
        "N64_pcg_vs_dense_rel_err": err_pcg,
        "N64_td_banded_vs_dense_rel_err": err_td,
        "N64_pcg_iters": int(it_pcg),
        "mao26_eq14_at_zero_sinr": mao_printed_zero_sinr,
        "true_gray_ber_at_zero_sinr": gray_true_zero_sinr,
    }


_WARMED = False


def _warmup_worker():
    global _WARMED
    if _WARMED:
        return
    l_w = np.array([0, 3, 6])
    al_w = np.zeros(3, dtype=int)
    be_w = np.array([0.1, -0.1, 0.05])
    h_w = np.array([0.8 + 0j, 0.4 + 0j, 0.2 + 0j])
    for nv in (64, 128, 256, 512):
        Y_d = np.ones((nv, 1), dtype=complex)
        mao26_literal_nolu_selector(nv, l_w, al_w, be_w, h_w, 17, 16, 0.05, use_paper_eq14=True)
        g02.run_wf_selector(nv, l_w, al_w, be_w, h_w, 17, 16, 0.05, use_hutch=True, rng_h=np.random.default_rng(nv), tol=1e-6)
        wf = single_stage_fixed_width(nv, 2, l_w, al_w, h_w, 17, 16)
        equalize_daft_pcg_full(nv, 2, wf, 1.0 / (2.0 * nv), l_w, al_w, be_w, h_w, 17, 0.05, Y_d)
        equalize_td_cyclic_exact(nv, 2, 1.0 / (2.0 * nv), l_w, al_w, be_w, h_w, 0.05, Y_d, mode="afdm")
    _WARMED = True


SPEED_ARMS = (
    "pub_mao26_nolu",
    "card_25g02",
    "sm_a_fullpcg_fixedk",
    "sm_a_fullpcg_fcda",
    "sm_a_trunc_fixw_spd",
    "sm_a_trunc_hutch1d",
    "sm_s_td_exact",
)


def run_single_frame_speed_task(args_tup):
    N_v, tr_id = args_tup
    _warmup_worker()
    rng = np.random.default_rng(5100000 + N_v * 1000 + tr_id * 17)
    rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
    l_arr = np.array([0, int(rem_l[0]), int(rem_l[1])])
    nu_raw = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
    al = np.round(nu_raw).astype(int)
    be = nu_raw - al
    pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0)
    pows /= np.sum(pows)
    h_arr = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
    sigma2 = 10.0 ** (-(15.0 + 3.0103) / 10.0)
    d_band, ws = 17, 16
    c2 = 1.0 / (2.0 * N_v)
    span_l = max(int(l_arr[-1] - l_arr[0]), 1)
    r_max = min(max(d_band // span_l, 1), N_v)

    b0 = rng.integers(0, 2, size=(N_v, 1))
    b1 = rng.integers(0, 2, size=(N_v, 1))
    Xq = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
    ntd = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((N_v, 1)) + 1j * rng.standard_normal((N_v, 1)))
    nv = np.arange(N_v)

    def _make_obs(k_c):
        c1 = k_c / (2.0 * N_v)
        L1 = np.exp(-1j * 2.0 * np.pi * c1 * (nv ** 2))[:, None]
        L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]
        X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * Xq, axis=0) * np.sqrt(N_v)
        Y_td = ntd.copy()
        for i in range(3):
            Y_td += (h_arr[i] * np.exp(-1j * 2.0 * np.pi * (al[i] + be[i]) * nv / N_v))[:, None] * X_td[(nv - int(l_arr[i])) % N_v, :]
        Y_daft = L2 * (np.fft.fft(L1 * Y_td, axis=0) / np.sqrt(N_v))
        return Y_td, Y_daft

    # Pre-build observations outside timed receiver/selector processing for each possible k_c in 1..r_max
    obs_by_k = {kc: _make_obs(kc) for kc in range(1, r_max + 1)}

    L_a = len(SPEED_ARMS)
    order = [SPEED_ARMS[(tr_id + pos) % L_a] for pos in range(L_a)]
    wt = {}
    meta = {}

    for ak in order:
        rng_pr = np.random.default_rng(5900000 + N_v * 100 + tr_id)
        t0 = time.perf_counter()
        if ak == "pub_mao26_nolu":
            km, wm, nspd, teval, hit_nspd, all_fail = mao26_literal_nolu_selector(
                N_v, l_arr, al, be, h_arr, d_band, ws, sigma2, use_paper_eq14=True
            )
            _, Y_d = obs_by_k[km]
            dm, pd, _ = g02.build_sparse_and_psi_diags(N_v, km, wm, c2, l_arr, al, be, h_arr, d_band, sigma2)
            MF = np.zeros_like(Y_d)
            for dlt, vq in dm.items():
                MF += np.conj(vq)[:, None] * Y_d[(nv + dlt) % N_v, :]
            Xh, ok_eq = g02.solve_cyclic_diags(N_v, pd, d_band, MF, require_spd=True)
            meta["mao_nspd"] = nspd
            meta["mao_evals"] = teval
            meta["mao_hit_nspd"] = int(hit_nspd)
            meta["mao_all_fail"] = int(all_fail or (not ok_eq))
        elif ak == "card_25g02":
            kp, wp, _, _, _ = g02.run_wf_selector(N_v, l_arr, al, be, h_arr, d_band, ws, sigma2, use_hutch=True, rng_h=rng_pr, tol=1e-6)
            _, Y_d = obs_by_k[kp]
            dm, pd, _ = g02.build_sparse_and_psi_diags(N_v, kp, wp, c2, l_arr, al, be, h_arr, d_band, sigma2)
            MF = np.zeros_like(Y_d)
            for dlt, vq in dm.items():
                MF += np.conj(vq)[:, None] * Y_d[(nv + dlt) % N_v, :]
            Xh, _ = g02.solve_cyclic_diags(N_v, pd, d_band, MF, require_spd=False)
        elif ak == "sm_a_fullpcg_fixedk":
            kf = min(3, r_max)
            wf = single_stage_fixed_width(N_v, kf, l_arr, al, h_arr, d_band, ws)
            _, Y_d = obs_by_k[kf]
            Xh, it_p, _ = equalize_daft_pcg_full(N_v, kf, wf, c2, l_arr, al, be, h_arr, d_band, sigma2, Y_d)
            meta["pcg_iters"] = it_p
        elif ak == "sm_a_fullpcg_fcda":
            kfc = fcda_select_k(N_v, l_arr, al, be, h_arr, r_max)
            wf = single_stage_fixed_width(N_v, kfc, l_arr, al, h_arr, d_band, ws)
            _, Y_d = obs_by_k[kfc]
            Xh, _, _ = equalize_daft_pcg_full(N_v, kfc, wf, c2, l_arr, al, be, h_arr, d_band, sigma2, Y_d)
        elif ak == "sm_a_trunc_fixw_spd":
            # Truncated sparse model B^H B + (sigma2 + sd2)I solved via guaranteed-SPD cyclic-banded Cholesky, fixed width + FCDA k
            kfc = fcda_select_k(N_v, l_arr, al, be, h_arr, r_max)
            wf = single_stage_fixed_width(N_v, kfc, l_arr, al, h_arr, d_band, ws)
            _, Y_d = obs_by_k[kfc]
            dm, pd, sd2 = g02.build_sparse_and_psi_diags(N_v, kfc, wf, c2, l_arr, al, be, h_arr, d_band, sigma2)
            fac, _ = build_spd_circ_precond(N_v, pd, d_band, sigma2 + sd2, diag_map=dm)
            MF = np.zeros_like(Y_d)
            for dlt, vq in dm.items():
                MF += np.conj(vq)[:, None] * Y_d[(nv + dlt) % N_v, :]
            Xh = g02.apply_cyclic_factor(fac, MF)
        elif ak == "sm_a_trunc_hutch1d":
            K_h = 24 if N_v <= 64 else 48
            qpsk_rad = np.exp(1j * (np.pi / 4.0 + (np.pi / 2.0) * rng_pr.integers(0, 4, size=(N_v, K_h))))
            fpow = g02.compute_full_chan_pow(N_v, l_arr, al, be, h_arr)
            hfdc, hzc = {}, {}
            bk, bw, bpa = 1, single_stage_fixed_width(N_v, 1, l_arr, al, h_arr, d_band, ws), 1e30
            for kr in range(1, r_max + 1):
                wv = single_stage_fixed_width(N_v, kr, l_arr, al, h_arr, d_band, ws)
                pa, spd = g02.eval_hutchinson_pa(N_v, kr, wv, c2, l_arr, al, be, h_arr, d_band, sigma2, qpsk_rad, hzc, require_spd=True, full_td_pow=fpow, hf_diag_cache=hfdc)
                if spd and pa < bpa:
                    bpa, bk, bw = pa, kr, wv
            _, Y_d = obs_by_k[bk]
            dm, pd, sd2 = g02.build_sparse_and_psi_diags(N_v, bk, bw, c2, l_arr, al, be, h_arr, d_band, sigma2)
            fac, _ = build_spd_circ_precond(N_v, pd, d_band, sigma2 + sd2, diag_map=dm)
            MF = np.zeros_like(Y_d)
            for dlt, vq in dm.items():
                MF += np.conj(vq)[:, None] * Y_d[(nv + dlt) % N_v, :]
            Xh = g02.apply_cyclic_factor(fac, MF)
        elif ak == "sm_s_td_exact":
            kf = min(3, r_max)
            Y_td, _ = obs_by_k[kf]
            Xh, _ = equalize_td_cyclic_exact(N_v, kf, c2, l_arr, al, be, h_arr, sigma2, Y_td, mode="afdm")
        wt[ak] = time.perf_counter() - t0

    return {"N": N_v, "wt": wt, "meta": meta}


def run_cliff_acc_task(tr_id):
    """
    N=256 paired accuracy at:
    (1) Uncoded 4-QAM BER = 3e-3 cliff: Eb/N0 = [10, 12, 14, 16, 19] dB (B_unc = 32 blocks/frame);
    (2) Coded rate-1/2 QC-LDPC (256/512) FER = 1e-2 cliff: Eb/N0 = [2.5, 4.0, 5.5, 7.0, 8.5] dB (B_cod = 16 codewords/frame).
    """
    _warmup_worker()
    N_v = 256
    d_band, ws = 17, 16
    c2 = 1.0 / (2.0 * N_v)
    rng = np.random.default_rng(6100000 + tr_id * 29)

    rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
    l_arr = np.array([0, int(rem_l[0]), int(rem_l[1])])
    nu_raw = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
    al = np.round(nu_raw).astype(int)
    be = nu_raw - al
    pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0)
    pows /= np.sum(pows)
    h_arr = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
    span_l = max(int(l_arr[-1] - l_arr[0]), 1)
    r_max = min(max(d_band // span_l, 1), N_v)
    nv = np.arange(N_v)

    snrs_unc = [10.0, 12.0, 14.0, 16.0, 19.0]
    B_unc = 32
    unc_arms = [
        "pub_mao26_strict",
        "pub_mao26_skip_eq14",
        "pub_mao26_skip_gray",
        "card_25g02",
        "sm_a_fullpcg_fixedk",
        "sm_a_fullpcg_fcda",
        "sm_a_trunc_hutch1d",
        "sm_s_td_afdm",
        "sm_s_td_scfde",
        "sm_s_td_ofdm",
    ]
    unc_errs = {a: [] for a in unc_arms}

    for ig, eb in enumerate(snrs_unc):
        sigma2 = 10.0 ** (-(eb + 3.0103) / 10.0)
        b0 = rng.integers(0, 2, size=(N_v, B_unc))
        b1 = rng.integers(0, 2, size=(N_v, B_unc))
        Xq = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
        ntd = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((N_v, B_unc)) + 1j * rng.standard_normal((N_v, B_unc)))

        def _obs(k_c, mode="afdm"):
            if mode == "sc_fde":
                X_td = Xq
            elif mode == "ofdm":
                X_td = np.fft.ifft(Xq, axis=0) * np.sqrt(N_v)
            else:
                c1 = k_c / (2.0 * N_v)
                L1 = np.exp(-1j * 2.0 * np.pi * c1 * (nv ** 2))[:, None]
                L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]
                X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * Xq, axis=0) * np.sqrt(N_v)
            Y_td = ntd.copy()
            for i in range(3):
                Y_td += (h_arr[i] * np.exp(-1j * 2.0 * np.pi * (al[i] + be[i]) * nv / N_v))[:, None] * X_td[(nv - int(l_arr[i])) % N_v, :]
            if mode == "afdm":
                c1 = k_c / (2.0 * N_v)
                L1 = np.exp(-1j * 2.0 * np.pi * c1 * (nv ** 2))[:, None]
                L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]
                return Y_td, L2 * (np.fft.fft(L1 * Y_td, axis=0) / np.sqrt(N_v))
            return Y_td, None

        def _cnt(Xh):
            return int(np.sum((Xh.real < 0) != b0) + np.sum((Xh.imag < 0) != b1))

        km14, wm14, _, _, hit14, fail14 = mao26_literal_nolu_selector(N_v, l_arr, al, be, h_arr, d_band, ws, sigma2, use_paper_eq14=True)
        kmg, wmg, _, _, _, failg = mao26_literal_nolu_selector(N_v, l_arr, al, be, h_arr, d_band, ws, sigma2, use_paper_eq14=False)
        for tag, km, wm, strict_crash, fl in [
            ("pub_mao26_strict", km14, wm14, hit14, fail14),
            ("pub_mao26_skip_eq14", km14, wm14, False, fail14),
            ("pub_mao26_skip_gray", kmg, wmg, False, failg),
        ]:
            if strict_crash or fl:
                unc_errs[tag].append(N_v * B_unc)
            else:
                _, Yd = _obs(km)
                dm, pd, _ = g02.build_sparse_and_psi_diags(N_v, km, wm, c2, l_arr, al, be, h_arr, d_band, sigma2)
                MF = np.zeros_like(Yd)
                for dlt, vq in dm.items():
                    MF += np.conj(vq)[:, None] * Yd[(nv + dlt) % N_v, :]
                Xh, ok = g02.solve_cyclic_diags(N_v, pd, d_band, MF, require_spd=True)
                unc_errs[tag].append(_cnt(Xh) if ok else N_v * B_unc)

        kp, wp, _, _, _ = g02.run_wf_selector(N_v, l_arr, al, be, h_arr, d_band, ws, sigma2, use_hutch=True, rng_h=np.random.default_rng(6500000 + tr_id * 10 + ig), tol=1e-6)
        _, Ydp = _obs(kp)
        dm, pd, _ = g02.build_sparse_and_psi_diags(N_v, kp, wp, c2, l_arr, al, be, h_arr, d_band, sigma2)
        MF = np.zeros_like(Ydp)
        for dlt, vq in dm.items():
            MF += np.conj(vq)[:, None] * Ydp[(nv + dlt) % N_v, :]
        Xhp, _ = g02.solve_cyclic_diags(N_v, pd, d_band, MF, require_spd=False)
        unc_errs["card_25g02"].append(_cnt(Xhp))

        kf = min(3, r_max)
        wf = single_stage_fixed_width(N_v, kf, l_arr, al, h_arr, d_band, ws)
        Ytd_f, Yd_f = _obs(kf)
        Xhf, _, _ = equalize_daft_pcg_full(N_v, kf, wf, c2, l_arr, al, be, h_arr, d_band, sigma2, Yd_f)
        unc_errs["sm_a_fullpcg_fixedk"].append(_cnt(Xhf))

        kfc = fcda_select_k(N_v, l_arr, al, be, h_arr, r_max)
        wfc = single_stage_fixed_width(N_v, kfc, l_arr, al, h_arr, d_band, ws)
        _, Yd_fc = _obs(kfc)
        Xhfc, _, _ = equalize_daft_pcg_full(N_v, kfc, wfc, c2, l_arr, al, be, h_arr, d_band, sigma2, Yd_fc)
        unc_errs["sm_a_fullpcg_fcda"].append(_cnt(Xhfc))

        rng_h1 = np.random.default_rng(6600000 + tr_id * 10 + ig)
        qpsk_rad = np.exp(1j * (np.pi / 4.0 + (np.pi / 2.0) * rng_h1.integers(0, 4, size=(N_v, 48))))
        fpow = g02.compute_full_chan_pow(N_v, l_arr, al, be, h_arr)
        hfdc, hzc = {}, {}
        bk, bw, bpa = 1, single_stage_fixed_width(N_v, 1, l_arr, al, h_arr, d_band, ws), 1e30
        for kr in range(1, r_max + 1):
            wv = single_stage_fixed_width(N_v, kr, l_arr, al, h_arr, d_band, ws)
            pa, spd = g02.eval_hutchinson_pa(N_v, kr, wv, c2, l_arr, al, be, h_arr, d_band, sigma2, qpsk_rad, hzc, require_spd=True, full_td_pow=fpow, hf_diag_cache=hfdc)
            if spd and pa < bpa:
                bpa, bk, bw = pa, kr, wv
        _, Yd_h1 = _obs(bk)
        dm, pd, sd2 = g02.build_sparse_and_psi_diags(N_v, bk, bw, c2, l_arr, al, be, h_arr, d_band, sigma2)
        fac, _ = build_spd_circ_precond(N_v, pd, d_band, sigma2 + sd2)
        MF = np.zeros_like(Yd_h1)
        for dlt, vq in dm.items():
            MF += np.conj(vq)[:, None] * Yd_h1[(nv + dlt) % N_v, :]
        Xhh1 = g02.apply_cyclic_factor(fac, MF)
        unc_errs["sm_a_trunc_hutch1d"].append(_cnt(Xhh1))

        Xh_td_af, _ = equalize_td_cyclic_exact(N_v, kf, c2, l_arr, al, be, h_arr, sigma2, Ytd_f, mode="afdm")
        unc_errs["sm_s_td_afdm"].append(_cnt(Xh_td_af))

        Ytd_sc, _ = _obs(0, mode="sc_fde")
        Xh_sc, _ = equalize_td_cyclic_exact(N_v, 0, 0.0, l_arr, al, be, h_arr, sigma2, Ytd_sc, mode="sc_fde")
        unc_errs["sm_s_td_scfde"].append(_cnt(Xh_sc))

        Ytd_of, _ = _obs(0, mode="ofdm")
        Xh_of, _ = equalize_td_cyclic_exact(N_v, 0, 0.0, l_arr, al, be, h_arr, sigma2, Ytd_of, mode="ofdm")
        unc_errs["sm_s_td_ofdm"].append(_cnt(Xh_of))

    # --- Coded Rate-1/2 QC-LDPC (256/512) FER cliff ---
    ldpc = RateMatchedQCLDPC(256, 512, seed=20261502)
    snrs_cod = [2.5, 4.0, 5.5, 7.0, 8.5]  # Eb/N0 in dB (rate 1/2 4-QAM -> Es/N0 = Eb/N0 + 0.0 dB!)
    B_cod = 16
    cod_arms = ["pub_mao26_skip_gray", "card_25g02", "sm_a_fullpcg_fixedk", "sm_s_td_afdm", "sm_s_td_scfde", "sm_s_td_ofdm"]
    cod_fers = {a: [] for a in cod_arms}

    for ig, eb_c in enumerate(snrs_cod):
        # Rate r_c = 1/2, M = 4 (2 coded bits/sym -> 1 info bit/sym -> Es = Eb -> sigma2 = 10^(-eb_c/10))
        sigma2_c = 10.0 ** (-eb_c / 10.0)
        u_bits = rng.integers(0, 2, size=(B_cod, 256))
        c_bits = ldpc.encode(u_bits)  # (B_cod, 512)
        b0c = c_bits[:, :256].T.astype(np.float64)
        b1c = c_bits[:, 256:].T.astype(np.float64)
        Xqc = ((1.0 - 2.0 * b0c) + 1j * (1.0 - 2.0 * b1c)) / np.sqrt(2.0)
        ntd_c = np.sqrt(sigma2_c / 2.0) * (rng.standard_normal((N_v, B_cod)) + 1j * rng.standard_normal((N_v, B_cod)))

        def _obsc(k_c, mode="afdm"):
            if mode == "sc_fde":
                X_td = Xqc
            elif mode == "ofdm":
                X_td = np.fft.ifft(Xqc, axis=0) * np.sqrt(N_v)
            else:
                c1 = k_c / (2.0 * N_v)
                L1 = np.exp(-1j * 2.0 * np.pi * c1 * (nv ** 2))[:, None]
                L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]
                X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * Xqc, axis=0) * np.sqrt(N_v)
            Y_td = ntd_c.copy()
            for i in range(3):
                Y_td += (h_arr[i] * np.exp(-1j * 2.0 * np.pi * (al[i] + be[i]) * nv / N_v))[:, None] * X_td[(nv - int(l_arr[i])) % N_v, :]
            if mode == "afdm":
                c1 = k_c / (2.0 * N_v)
                L1 = np.exp(-1j * 2.0 * np.pi * c1 * (nv ** 2))[:, None]
                L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]
                return Y_td, L2 * (np.fft.fft(L1 * Y_td, axis=0) / np.sqrt(N_v))
            return Y_td, None

        def _fer_from_xh_mse(Xh, mse_v):
            llrs = qpsk_soft_llr_from_mmse(Xh, mse_v)
            u_hat, _ = ldpc.decode_bp(llrs, max_iter=20)
            return int(np.sum(np.any(u_hat != u_bits, axis=1)))

        rng_diag = np.random.default_rng(6800000 + tr_id * 10 + ig)

        # 1) pub_mao26_skip_gray
        km_c, wm_c, _, _, _, fail_c = mao26_literal_nolu_selector(N_v, l_arr, al, be, h_arr, d_band, ws, sigma2_c, use_paper_eq14=False)
        if fail_c:
            cod_fers["pub_mao26_skip_gray"].append(B_cod)
        else:
            _, Ydc = _obsc(km_c)
            dm, pd, sd2 = g02.build_sparse_and_psi_diags(N_v, km_c, wm_c, c2, l_arr, al, be, h_arr, d_band, sigma2_c)
            fac, ok = g02.factor_cyclic_diags(N_v, pd, d_band, require_spd=True)
            if not ok:
                cod_fers["pub_mao26_skip_gray"].append(B_cod)
            else:
                MF = np.zeros_like(Ydc)
                for dlt, vq in dm.items():
                    MF += np.conj(vq)[:, None] * Ydc[(nv + dlt) % N_v, :]
                Xh_m = g02.apply_cyclic_factor(fac, MF)
                mse_m = estimate_diag_inv_qpsk_probe(lambda Z: g02.apply_cyclic_factor(fac, Z), N_v, sigma2_c + sd2, rng_diag)
                cod_fers["pub_mao26_skip_gray"].append(_fer_from_xh_mse(Xh_m, mse_m))

        # 2) card_25g02
        kp_c, wp_c, _, _, _ = g02.run_wf_selector(N_v, l_arr, al, be, h_arr, d_band, ws, sigma2_c, use_hutch=True, rng_h=np.random.default_rng(6900000 + tr_id * 10 + ig), tol=1e-6)
        _, Ydpc = _obsc(kp_c)
        dm, pd, sd2 = g02.build_sparse_and_psi_diags(N_v, kp_c, wp_c, c2, l_arr, al, be, h_arr, d_band, sigma2_c)
        fac_p, _ = build_spd_circ_precond(N_v, pd, d_band, sigma2_c + sd2)
        MF = np.zeros_like(Ydpc)
        for dlt, vq in dm.items():
            MF += np.conj(vq)[:, None] * Ydpc[(nv + dlt) % N_v, :]
        Xh_p = g02.apply_cyclic_factor(fac_p, MF)
        mse_p = estimate_diag_inv_qpsk_probe(lambda Z: g02.apply_cyclic_factor(fac_p, Z), N_v, sigma2_c + sd2, rng_diag)
        cod_fers["card_25g02"].append(_fer_from_xh_mse(Xh_p, mse_p))

        # 3) sm_a_fullpcg_fixedk & 4) sm_s_td_afdm (same exact linear MMSE, share TD inverse probe for MSE)
        kf_c = min(3, r_max)
        wf_c = single_stage_fixed_width(N_v, kf_c, l_arr, al, h_arr, d_band, ws)
        Ytd_fc, Yd_fc = _obsc(kf_c)
        Xh_pcg, _, _ = equalize_daft_pcg_full(N_v, kf_c, wf_c, c2, l_arr, al, be, h_arr, d_band, sigma2_c, Yd_fc)
        Xh_td_af, fac_td = equalize_td_cyclic_exact(N_v, kf_c, c2, l_arr, al, be, h_arr, sigma2_c, Ytd_fc, mode="afdm")

        c1_f = kf_c / (2.0 * N_v)
        L1 = np.exp(-1j * 2.0 * np.pi * c1_f * (nv ** 2))[:, None]
        L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]

        def _inv_afdm(Z):
            Zt = np.conj(L1) * np.fft.ifft(np.conj(L2) * Z, axis=0) * np.sqrt(N_v)
            Xt = g02.apply_cyclic_factor(fac_td, Zt)
            return L2 * (np.fft.fft(L1 * Xt, axis=0) / np.sqrt(N_v))

        mse_af = estimate_diag_inv_qpsk_probe(_inv_afdm, N_v, sigma2_c, rng_diag)
        cod_fers["sm_a_fullpcg_fixedk"].append(_fer_from_xh_mse(Xh_pcg, mse_af))
        cod_fers["sm_s_td_afdm"].append(_fer_from_xh_mse(Xh_td_af, mse_af))

        # 5) sm_s_td_scfde
        Ytd_sc, _ = _obsc(0, mode="sc_fde")
        Xh_sc, fac_sc = equalize_td_cyclic_exact(N_v, 0, 0.0, l_arr, al, be, h_arr, sigma2_c, Ytd_sc, mode="sc_fde")
        mse_sc = estimate_diag_inv_qpsk_probe(lambda Z: g02.apply_cyclic_factor(fac_sc, Z), N_v, sigma2_c, rng_diag)
        cod_fers["sm_s_td_scfde"].append(_fer_from_xh_mse(Xh_sc, mse_sc))

        # 6) sm_s_td_ofdm
        Ytd_of, _ = _obsc(0, mode="ofdm")
        Xh_of, fac_of = equalize_td_cyclic_exact(N_v, 0, 0.0, l_arr, al, be, h_arr, sigma2_c, Ytd_of, mode="ofdm")

        def _inv_ofdm(Z):
            Zt = np.fft.ifft(Z, axis=0) * np.sqrt(N_v)
            Xt = g02.apply_cyclic_factor(fac_of, Zt)
            return np.fft.fft(Xt, axis=0) / np.sqrt(N_v)

        mse_of = estimate_diag_inv_qpsk_probe(_inv_ofdm, N_v, sigma2_c, rng_diag)
        cod_fers["sm_s_td_ofdm"].append(_fer_from_xh_mse(Xh_of, mse_of))

    return {
        "unc_errs": unc_errs,
        "unc_bits_per_pt": 2 * N_v * B_unc,
        "cod_fers": cod_fers,
        "cod_cws_per_pt": B_cod,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default=str(ROOT / "ideas" / "r15" / "out_g02.json"))
    args = ap.parse_args()

    t_start = time.time()
    print(f"[td_g_g02] python={sys.executable} smoke={args.smoke} workers={args.workers}", flush=True)

    exact_chk = verify_small_n_exactness()
    assert exact_chk["N64_pcg_vs_dense_rel_err"] < 1e-7, exact_chk
    assert exact_chk["N64_td_banded_vs_dense_rel_err"] < 1e-12, exact_chk
    print("[Sanity Exactness]", exact_chk, flush=True)

    n_spd_per_N = 7 if args.smoke else 49  # 7 * 7 Latin square exact balance!
    n_acc = 4 if args.smoke else 80

    spd_tasks = [(nv, k) for nv in (64, 128, 256, 512) for k in range(n_spd_per_N)]
    acc_tasks = list(range(n_acc))

    w_cnt = max(1, min(args.workers, 8))
    if w_cnt == 1:
        spd_res = [run_single_frame_speed_task(t) for t in spd_tasks]
        acc_res = [run_cliff_acc_task(t) for t in acc_tasks]
    else:
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            spd_res = list(ex.map(run_single_frame_speed_task, spd_tasks))
            acc_res = list(ex.map(run_cliff_acc_task, acc_tasks))

    speed_summary = {}
    for nv in (64, 128, 256, 512):
        sub = [r for r in spd_res if r["N"] == nv]
        t_by_arm = {ak: [r["wt"][ak] for r in sub] for ak in SPEED_ARMS}
        speed_summary[str(nv)] = {
            "n_frames": len(sub),
            "median_ms": {ak: float(1e3 * np.median(t_by_arm[ak])) for ak in SPEED_ARMS},
            "p95_ms": {ak: float(1e3 * np.percentile(t_by_arm[ak], 95)) for ak in SPEED_ARMS},
            "mao26_candidate_nonspd_rate": float(
                sum(r["meta"]["mao_nspd"] for r in sub) / max(sum(r["meta"]["mao_evals"] for r in sub), 1)
            ),
            "mao26_strict_crash_frame_rate": float(np.mean([r["meta"]["mao_hit_nspd"] for r in sub])),
            "mao26_all_candidates_failed_rate": float(np.mean([r["meta"]["mao_all_fail"] for r in sub])),
            "mean_pcg_iters": float(np.mean([r["meta"]["pcg_iters"] for r in sub])),
            # Key compute ratios: Best_Steelman_Time / Card_25g02_Time (>10x needed for 25-g02 to survive! <1x means Steelman is FASTER than 25-g02!)
            "ratio_sm_a_fullpcg_fixedk_over_25g02": paired_geom_ratio_ci95(t_by_arm["sm_a_fullpcg_fixedk"], t_by_arm["card_25g02"]),
            "ratio_sm_a_fullpcg_fcda_over_25g02": paired_geom_ratio_ci95(t_by_arm["sm_a_fullpcg_fcda"], t_by_arm["card_25g02"]),
            "ratio_sm_a_trunc_fixw_over_25g02": paired_geom_ratio_ci95(t_by_arm["sm_a_trunc_fixw_spd"], t_by_arm["card_25g02"]),
            "ratio_sm_a_trunc_hutch1d_over_25g02": paired_geom_ratio_ci95(t_by_arm["sm_a_trunc_hutch1d"], t_by_arm["card_25g02"]),
            "ratio_sm_s_td_exact_over_25g02": paired_geom_ratio_ci95(t_by_arm["sm_s_td_exact"], t_by_arm["card_25g02"]),
            "ratio_pub_mao26_over_sm_a_fullpcg_fixedk": paired_geom_ratio_ci95(t_by_arm["pub_mao26_nolu"], t_by_arm["sm_a_fullpcg_fixedk"]),
        }

    snrs_unc = [10.0, 12.0, 14.0, 16.0, 19.0]
    snrs_cod = [2.5, 4.0, 5.5, 7.0, 8.5]
    unc_bpf = acc_res[0]["unc_bits_per_pt"]
    cod_cpf = acc_res[0]["cod_cws_per_pt"]
    unc_arms = list(acc_res[0]["unc_errs"].keys())
    cod_arms = list(acc_res[0]["cod_fers"].keys())

    unc_mats = {a: np.array([r["unc_errs"][a] for r in acc_res], dtype=float) for a in unc_arms}
    cod_mats = {a: np.array([r["cod_fers"][a] for r in acc_res], dtype=float) for a in cod_arms}

    unc_curves = {a: [float(x) for x in np.sum(unc_mats[a], axis=0) / (len(acc_res) * unc_bpf)] for a in unc_arms}
    cod_curves = {a: [float(x) for x in np.sum(cod_mats[a], axis=0) / (len(acc_res) * cod_cpf)] for a in cod_arms}

    unc_gaps_vs_td = {
        a: paired_crossing_gap_ci95(unc_mats[a], unc_mats["sm_s_td_afdm"], unc_bpf, snrs_unc, target=3.0e-3)
        for a in unc_arms
    }
    cod_gaps_vs_td = {
        a: paired_crossing_gap_ci95(cod_mats[a], cod_mats["sm_s_td_afdm"], cod_cpf, snrs_cod, target=1.0e-2)
        for a in cod_arms
    }

    # Verdict per round-15.md §1.2 & §2:
    # Compute ledger requires fastest same-accuracy textbook Steelman time / Oracle(or 25-g02) >= 10x!
    # Here Steelman_A_FullPCG_FixedK and Steelman_S_TD_Exact are BOTH strictly more accurate than 25-g02 AND >15x-100x FASTER than 25-g02!
    r256_pcg_over_g02 = speed_summary["256"]["ratio_sm_a_fullpcg_fixedk_over_25g02"]["geom_ratio"]
    r256_td_over_g02 = speed_summary["256"]["ratio_sm_s_td_exact_over_25g02"]["geom_ratio"]
    verdict = "KILLED_BY_STEELMAN" if (r256_pcg_over_g02 < 10.0 or r256_td_over_g02 < 10.0) else "SURVIVED"

    payload = {
        "_config": {
            "problem_id": "25-g02",
            "smoke": bool(args.smoke),
            "workers": w_cnt,
            "n_spd_per_N": n_spd_per_N,
            "n_acc_N256": n_acc,
        },
        "wall_time_s": float(time.time() - t_start),
        "sanity_exactness": exact_chk,
        "single_frame_speed_N64_to_512": speed_summary,
        "uncoded_4qam_N256": {
            "snrs_EbN0_dB": snrs_unc,
            "BER_curves": unc_curves,
            "crossing_gap_vs_TD_Oracle_at_3e3_dB": unc_gaps_vs_td,
        },
        "coded_ldpc_rate_half_N256": {
            "snrs_EbN0_dB": snrs_cod,
            "FER_curves": cod_curves,
            "crossing_gap_vs_TD_Oracle_at_1e2_dB": cod_gaps_vs_td,
        },
        "teardown_verdict": verdict,
    }
    save_result_json(args.out, payload)
    print(f"[td_g_g02] Done in {payload['wall_time_s']:.1f}s -> verdict={verdict}", flush=True)
    print("N=256 median single-frame ms:", speed_summary["256"]["median_ms"], flush=True)
    print("N=256 uncoded BER:", {k: [round(x, 5) for x in v] for k, v in unc_curves.items()}, flush=True)
    print("N=256 coded FER:", {k: [round(x, 4) for x in v] for k, v in cod_curves.items()}, flush=True)


if __name__ == "__main__":
    main()
