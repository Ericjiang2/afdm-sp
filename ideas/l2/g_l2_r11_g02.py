import sys
print(sys.executable, flush=True)

import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import argparse
import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scipy.linalg import cholesky_banded, cho_solve_banded, solve_banded
from scipy.special import erfc
from scipy.stats import t as sp_t

FORMAL_SPEED_COUNTS = {64: 72, 128: 65, 256: 70, 512: 49}
FORMAL_N_ACC_256 = 336

SPEED_SEED_BASES = {64: 3100000, 128: 3200000, 256: 3300000, 512: 3400000}
SPEED_PROBE_OFFSET = 50000
ACC_SEED_BASE = 3500000
ACC_PROBE_SEED_BASE = 3600000

SPEED_ARMS_BY_N = {
    64: ("mao26", "mao26_spd", "cf", "cf_spd", "b_only", "prop"),
    128: ("mao26", "mao26_spd", "cf", "cf_spd", "prop"),
    256: ("mao26", "mao26_spd", "cf", "cf_spd", "a_only", "b_only", "prop"),
    512: ("mao26", "mao26_spd", "cf", "cf_spd", "a_only", "b_only", "prop"),
}


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        fv = float(obj)
        return fv if math.isfinite(fv) else None
    return obj


def cap_ratio_lhw(tau):
    return float(min(0.25 * math.log(tau), math.log(1.25)))


def dirichlet_lobe(N, beta, wi, h_i):
    ms = np.arange(-wi, wi + 1, dtype=float)
    xa = ms + beta
    den = np.exp(-1j * 2.0 * np.pi * xa / N) - 1.0
    zm = np.abs(den) < 1e-11
    sn = np.where(zm, float(N), (np.exp(-1j * 2.0 * np.pi * xa) - 1.0) / np.where(zm, 1.0, den))
    return (h_i / N) * sn


def sn_sq_vec(N, beta, m_arr):
    x = m_arr + beta
    rem = x - N * np.round(x / N)
    nz = np.abs(rem) < 1e-10
    xs = np.where(nz, 0.5, x)
    return np.where(nz, float(N * N), (np.sin(np.pi * xs) / np.sin(np.pi * xs / N)) ** 2)


def compute_full_chan_pow(N, l_arr, alpha_arr, beta_arr, h_arr):
    n_vec = np.arange(N)
    td_map = {}
    for i in range(len(l_arr)):
        li = int(l_arr[i])
        nup = alpha_arr[i] + beta_arr[i]
        vq = h_arr[i] * np.exp(-1j * 2.0 * np.pi * nup * n_vec / N)
        td_map[li] = (td_map[li] + vq) if (li in td_map) else vq
    return float(sum(np.sum(np.abs(v) ** 2) for v in td_map.values()) / N)


def compute_sigma_delta2_exact(N, k_c, c2, l_arr, alpha_arr, beta_arr, h_arr, diag_map, full_td_pow, hf_diag_cache):
    c1 = k_c / (2.0 * N)
    q = np.arange(N)
    xis = [(int(alpha_arr[i]) + k_c * int(l_arr[i])) % N for i in range(len(l_arr))]
    diff_energy = 0.0
    for dlt, h_sp_d in diag_map.items():
        d_int = int(dlt)
        key = (k_c, d_int)
        if key not in hf_diag_cache:
            p_idx = (q + d_int) % N
            c2_term = N * c2 * (q ** 2 - p_idx ** 2)
            hf_d = np.zeros(N, dtype=complex)
            for i in range(len(l_arr)):
                li = int(l_arr[i])
                df = (d_int + xis[i]) % N
                df_s = df - N if df >= (N // 2) else df
                xa = df_s + beta_arr[i]
                den = np.exp(-1j * 2.0 * np.pi * xa / N) - 1.0
                sn = float(N) if abs(den) < 1e-11 else (np.exp(-1j * 2.0 * np.pi * xa) - 1.0) / den
                phi = c1 * N * (li ** 2) - q * li + c2_term
                hf_d += (h_arr[i] / N) * sn * np.exp(1j * 2.0 * np.pi * phi / N)
            hf_diag_cache[key] = hf_d
        hf_d = hf_diag_cache[key]
        diff_energy += float(np.sum(np.abs(hf_d - h_sp_d) ** 2) - np.sum(np.abs(hf_d) ** 2))
    return max(0.0, full_td_pow + diff_energy / N)


def build_sparse_and_psi_diags(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, full_td_pow=None, hf_diag_cache=None):
    P = len(l_arr)
    c1 = k_c / (2.0 * N)
    q = np.arange(N)
    diag_map = {}
    for i in range(P):
        li, wi = int(l_arr[i]), int(w_vec[i])
        xi_i = int((alpha_arr[i] + k_c * li) % N)
        lb = dirichlet_lobe(N, beta_arr[i], wi, h_arr[i])
        for im, m_off in enumerate(range(-wi, wi + 1)):
            delta = (m_off - xi_i) % N
            p_idx = (q + delta) % N
            phi = c1 * N * (li ** 2) - q * li + N * c2 * (q ** 2 - p_idx ** 2)
            vq = lb[im] * np.exp(1j * 2.0 * np.pi * phi / N)
            diag_map[delta] = (diag_map[delta] + vq) if (delta in diag_map) else vq

    if full_td_pow is None:
        full_td_pow = compute_full_chan_pow(N, l_arr, alpha_arr, beta_arr, h_arr)
    if hf_diag_cache is None:
        hf_diag_cache = {}
    sigma_delta2 = compute_sigma_delta2_exact(N, k_c, c2, l_arr, alpha_arr, beta_arr, h_arr, diag_map, full_td_pow, hf_diag_cache)

    deltas = list(diag_map.keys())
    psi_diags = np.zeros((d_band, N), dtype=complex)
    psi_diags[0, :] = sigma2 + sigma_delta2
    for d1 in deltas:
        v1c = np.conj(diag_map[d1])
        for d2 in deltas:
            diff_d = (d1 - d2) % N
            if diff_d < d_band:
                psi_diags[diff_d, :] += v1c * diag_map[d2][(q + diff_d) % N]
    return diag_map, psi_diags, sigma_delta2


def build_H_full_fast(N, k_c, c2, l_arr, alpha_arr, beta_arr, h_arr):
    c1 = k_c / (2.0 * N)
    p = np.arange(N)[:, None]
    q = np.arange(N)[None, :]
    H_full = np.zeros((N, N), dtype=complex)
    for i in range(len(l_arr)):
        li = int(l_arr[i])
        xi_i = int((alpha_arr[i] + k_c * li) % N)
        phi = c1 * N * (li ** 2) - q * li + N * c2 * (q ** 2 - p ** 2)
        diff = (p - q + xi_i) % N
        diff_s = np.where(diff >= N // 2, diff - N, diff)
        xa = diff_s + beta_arr[i]
        den = np.exp(-1j * 2.0 * np.pi * xa / N) - 1.0
        zm = np.abs(den) < 1e-11
        sn = np.where(zm, float(N), (np.exp(-1j * 2.0 * np.pi * xa) - 1.0) / np.where(zm, 1.0, den))
        H_full += (h_arr[i] / N) * np.exp(1j * 2.0 * np.pi * phi / N) * sn
    return H_full


def factor_cyclic_diags(N, psi_diags, d_band, require_spd=False):
    bw = d_band - 1
    q = np.arange(N)
    if 2 * bw + 2 >= N:
        Psi = np.zeros((N, N), dtype=complex)
        for d in range(d_band):
            cN = (q + d) % N
            Psi[q, cN] = psi_diags[d]
            if d > 0:
                Psi[cN, q] = np.conj(psi_diags[d])
        try:
            Lc = np.linalg.cholesky(Psi)
            return ("dense_spd", Lc), True
        except np.linalg.LinAlgError:
            if require_spd:
                return None, False
            return ("dense_lu", Psi), False

    n1 = N - bw
    ab1 = np.zeros((bw + 1, n1), dtype=complex)
    ab1[bw, :] = psi_diags[0, :n1].real
    A12 = np.zeros((n1, bw), dtype=complex)
    for d in range(1, d_band):
        ab1[bw - d, d:] = psi_diags[d, : n1 - d]
        c_up = np.arange(bw - d, bw)
        A12[c_up - bw + d, c_up] = np.conj(psi_diags[d, n1 + c_up])
        c_lo = np.arange(d)
        r_lo = n1 - d + c_lo
        A12[r_lo, c_lo] = psi_diags[d, r_lo]

    M22 = np.zeros((bw, bw), dtype=complex)
    for d in range(bw):
        c_m = np.arange(bw - d)
        vals = psi_diags[d, n1 + c_m]
        M22[c_m, c_m + d] = vals
        if d > 0:
            M22[c_m + d, c_m] = np.conj(vals)

    try:
        cb1 = cholesky_banded(ab1, lower=False)
        Z12 = cho_solve_banded((cb1, False), A12)
        S22 = M22 - A12.conj().T @ Z12
        L22 = np.linalg.cholesky(S22)
        return ("banded_spd", n1, cb1, A12, Z12, L22), True
    except np.linalg.LinAlgError:
        if require_spd:
            return None, False
        ab_lu = np.zeros((2 * bw + 1, n1), dtype=complex)
        ab_lu[bw, :] = psi_diags[0, :n1]
        for d in range(1, d_band):
            ab_lu[bw - d, d:] = psi_diags[d, : n1 - d]
            ab_lu[bw + d, : n1 - d] = np.conj(psi_diags[d, : n1 - d])
        Z12 = solve_banded((bw, bw), ab_lu, A12)
        S22 = M22 - A12.conj().T @ Z12
        return ("banded_lu", n1, bw, ab_lu, A12, Z12, S22), False


def apply_cyclic_factor(fac, RHS):
    kind = fac[0]
    if kind == "dense_spd":
        Lc = fac[1]
        Y = np.linalg.solve(Lc, RHS)
        return np.linalg.solve(Lc.conj().T, Y)
    if kind == "dense_lu":
        return np.linalg.solve(fac[1], RHS)
    if kind == "banded_spd":
        _, n1, cb1, A12, Z12, L22 = fac
        Y1 = cho_solve_banded((cb1, False), RHS[:n1])
        rhs2 = RHS[n1:] - A12.conj().T @ Y1
        X2 = np.linalg.solve(L22.conj().T, np.linalg.solve(L22, rhs2))
        return np.vstack([Y1 - Z12 @ X2, X2])
    _, n1, bw, ab_lu, A12, Z12, S22 = fac
    Y1 = solve_banded((bw, bw), ab_lu, RHS[:n1])
    X2 = np.linalg.solve(S22, RHS[n1:] - A12.conj().T @ Y1)
    return np.vstack([Y1 - Z12 @ X2, X2])


def solve_cyclic_diags(N, psi_diags, d_band, RHS, require_spd=False):
    fac, spd = factor_cyclic_diags(N, psi_diags, d_band, require_spd=require_spd)
    if fac is None:
        return None, False
    return apply_cyclic_factor(fac, RHS), spd


def _pa_from_sinr(sinr_k, use_paper_eq14=False):
    # Mao26 printed Eq. (14) sets a_M = 4*(sqrt(M)-1)/sqrt(M) = 2 for M=4 -> 2*Q - 4*Q^2;
    # Project SPD-screened 2x2 factorial arms use physical Gray 4-QAM bit-error score Q - Q^2 (explicitly distinguished).
    qv = 0.5 * erfc(np.sqrt(sinr_k / 2.0))
    if use_paper_eq14:
        return float(np.mean(2.0 * qv - 4.0 * (qv ** 2)))
    return float(np.mean(qv - qv ** 2))


def eval_exact_pa_sparse(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Hf_cache, require_spd=False, full_td_pow=None, hf_diag_cache=None, use_paper_eq14=False):
    diag_map, psi_diags, _ = build_sparse_and_psi_diags(
        N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, full_td_pow=full_td_pow, hf_diag_cache=hf_diag_cache
    )
    fac, spd = factor_cyclic_diags(N, psi_diags, d_band, require_spd=require_spd)
    if fac is None:
        return 1e30, False
    if k_c not in Hf_cache:
        Hf_cache[k_c] = build_H_full_fast(N, k_c, c2, l_arr, alpha_arr, beta_arr, h_arr)
    H_full = Hf_cache[k_c]
    q = np.arange(N)
    HspH_Hf = np.zeros((N, N), dtype=complex)
    HspH = np.zeros((N, N), dtype=complex)
    for dlt, vq in diag_map.items():
        vc = np.conj(vq)
        rows = (q + dlt) % N
        HspH_Hf += vc[:, None] * H_full[rows, :]
        HspH[q, rows] = vc
    SOL = apply_cyclic_factor(fac, np.hstack([HspH_Hf, HspH]))
    W_H, W_mat = SOL[:, :N], SOL[:, N:]
    sig_pow = np.abs(np.diag(W_H)) ** 2
    tot_pow = np.sum(np.abs(W_H) ** 2, axis=1)
    n_pow = sigma2 * np.sum(np.abs(W_mat) ** 2, axis=1)
    sinr_k = sig_pow / np.maximum(tot_pow - sig_pow + n_pow, 1e-12)
    return _pa_from_sinr(sinr_k, use_paper_eq14=use_paper_eq14), spd


def eval_hutchinson_pa(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Z_rad, HZ_cache, require_spd=True, full_td_pow=None, hf_diag_cache=None, use_paper_eq14=False):
    diag_map, psi_diags, _ = build_sparse_and_psi_diags(
        N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, full_td_pow=full_td_pow, hf_diag_cache=hf_diag_cache
    )
    fac, spd = factor_cyclic_diags(N, psi_diags, d_band, require_spd=require_spd)
    if fac is None:
        return 1e30, False
    if k_c not in HZ_cache:
        c1 = k_c / (2.0 * N)
        n_vec = np.arange(N)
        L1 = np.exp(-1j * 2.0 * np.pi * c1 * (n_vec ** 2))[:, None]
        L2 = np.exp(-1j * 2.0 * np.pi * c2 * (n_vec ** 2))[:, None]
        X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * Z_rad, axis=0) * np.sqrt(N)
        Y_td = np.zeros_like(X_td)
        for i in range(len(l_arr)):
            nup = alpha_arr[i] + beta_arr[i]
            dop = (h_arr[i] * np.exp(-1j * 2.0 * np.pi * nup * n_vec / N))[:, None]
            Y_td += dop * X_td[(n_vec - int(l_arr[i])) % N, :]
        HZ_cache[k_c] = L2 * (np.fft.fft(L1 * Y_td, axis=0) / np.sqrt(N))
    HZ = HZ_cache[k_c]
    K_h = Z_rad.shape[1]
    comb_in = np.hstack([HZ, Z_rad])
    q = np.arange(N)
    R_full = np.zeros_like(comb_in)
    for dlt, vq in diag_map.items():
        R_full += np.conj(vq)[:, None] * comb_in[(q + dlt) % N, :]
    X_all = apply_cyclic_factor(fac, R_full)
    WHZ, WZ = X_all[:, :K_h], X_all[:, K_h:]
    diag_WH = np.mean(WHZ * np.conj(Z_rad), axis=1)
    tot_pow = np.mean(np.abs(WHZ) ** 2, axis=1)
    sig_pow = np.minimum(np.abs(diag_WH) ** 2, 0.999 * tot_pow)
    n_pow = sigma2 * np.mean(np.abs(WZ) ** 2, axis=1)
    sinr_k = sig_pow / np.maximum(tot_pow - sig_pow + n_pow, 1e-12)
    return _pa_from_sinr(sinr_k, use_paper_eq14=use_paper_eq14), spd


def mao26_all_eq45_inits(N, k_r, l_arr, alpha_arr, d_band, ws):
    P = len(l_arr)
    xis = [(int(alpha_arr[i]) + k_r * int(l_arr[i])) % N for i in range(P)]
    sep = (xis[-1] - xis[0]) % N
    sep_cyc = min(sep, N - sep)
    rem_t = int(np.clip(d_band - sep_cyc, 0, ws))
    cands = []
    for w1 in range(0, rem_t + 1):
        wP = rem_t - w1
        rem_mid = ws - rem_t
        w = np.zeros(P, dtype=int)
        w[0], w[-1] = int(w1), int(wP)
        if P > 2:
            for mi in range(1, P - 1):
                w[mi] = rem_mid // (P - 2)
            w[1] += rem_mid - int(np.sum(w[1:-1]))
        else:
            w[0] += rem_mid
        cands.append(w)
    return cands


def band_coupled_wf_seed(N, k_r, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws):
    P = len(beta_arr)
    m_pos = np.arange(1, ws + 2, dtype=float)
    marg = np.array([(abs(h_arr[i]) ** 2 / (N * N)) * (sn_sq_vec(N, beta_arr[i], m_pos) + sn_sq_vec(N, beta_arr[i], -m_pos)) for i in range(P)])
    w_u = np.zeros(P, dtype=int)
    for _ in range(ws):
        w_u[int(np.argmax([marg[i, w_u[i]] for i in range(P)]))] += 1
    xis = [(int(alpha_arr[i]) + k_r * int(l_arr[i])) % N for i in range(P)]
    sep = (xis[-1] - xis[0]) % N
    sep_cyc = min(sep, N - sep)
    bw = d_band - 1
    if P >= 3:
        pair_cap = max(0, bw - sep_cyc)
        w_bc = np.zeros(P, dtype=int)
        for _ in range(ws):
            feas = list(range(1, P - 1)) if (w_bc[0] + w_bc[-1] >= pair_cap) else list(range(P))
            b = feas[int(np.argmax([marg[i, w_bc[i]] for i in feas]))]
            w_bc[b] += 1
        return w_bc, w_u
    return w_u.copy(), w_u


def run_hillclimb_selector(N, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, rng_h=None, spd_two_pass=False, iter_max=15, step_k=1, tol=0.0, fixed_k_list=None, use_paper_eq14=False):
    # Literal Mao26 Algorithm 2 lines 7-15 synchronous neighbor generation from fixed w^{(t)} -> w^{(t+1)}:
    # - PaperExact_Mao26 / CoarseFine_Mao26: spd_two_pass=False, tol=0.0, use_paper_eq14=True (printed Eq. 14 2Q - 4Q^2);
    # - Project SPD-screened 2x2 arms (FairSparse_Mao26_SPD, CoarseFine_Mao26_SPD, B_only): spd_two_pass=True, tol=1e-6, use_paper_eq14=False (Q - Q^2).
    P = len(l_arr)
    c2 = 1.0 / (2.0 * N)
    full_td_pow = compute_full_chan_pow(N, l_arr, alpha_arr, beta_arr, h_arr)
    hf_diag_cache = {}
    span_l = max(int(np.max(l_arr) - np.min(l_arr)), 1)
    r_max = min(max(d_band // span_l, 1), N)
    k_list = list(fixed_k_list) if (fixed_k_list is not None) else list(range(1, r_max + 1, step_k))
    K_h = 24 if N <= 64 else 48
    qpsk_rad = np.exp(1j * (np.pi / 4.0 + (np.pi / 2.0) * rng_h.integers(0, 4, size=(N, K_h)))) if use_hutch else None
    cache = {}
    best_pa, best_k, best_w = 1e30, int(k_list[0]), np.zeros(P, dtype=int)
    non_spd, tot_eval, all_rej = 0, 0, 0
    passes = (True, False) if spd_two_pass else (False,)

    for pass_idx, req_s in enumerate(passes):
        if pass_idx == 1:
            all_rej = 1

        def _search_k(kr):
            nonlocal best_pa, best_k, best_w, non_spd, tot_eval
            memo = {}

            def _sc(wv):
                nonlocal non_spd, tot_eval
                tk = tuple(wv.tolist())
                if tk not in memo:
                    if use_hutch:
                        pa_v, spd_v = eval_hutchinson_pa(
                            N, kr, wv, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, qpsk_rad, cache, require_spd=req_s, full_td_pow=full_td_pow, hf_diag_cache=hf_diag_cache, use_paper_eq14=use_paper_eq14
                        )
                    else:
                        pa_v, spd_v = eval_exact_pa_sparse(
                            N, kr, wv, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, cache, require_spd=req_s, full_td_pow=full_td_pow, hf_diag_cache=hf_diag_cache, use_paper_eq14=use_paper_eq14
                        )
                    tot_eval += 1
                    if not spd_v:
                        non_spd += 1
                    memo[tk] = pa_v
                return memo[tk]

            kb = 1e30
            for w0 in mao26_all_eq45_inits(N, kr, l_arr, alpha_arr, d_band, ws):
                w_t = w0.copy()
                p_t = _sc(w_t)
                for _ in range(iter_max):
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
                            if pn < p_t - tol:
                                w_next = wn
                                flag = True
                    w_t = w_next
                    p_t = _sc(w_t)
                    if not flag:
                        break
                if p_t < kb:
                    kb = p_t
                if p_t < best_pa:
                    best_pa, best_k, best_w = p_t, kr, w_t.copy()
            return kb

        if (fixed_k_list is not None) or (step_k == 1):
            for kr in k_list:
                _search_k(kr)
        else:
            cs = sorted([(kr, _search_k(kr)) for kr in k_list], key=lambda x: x[1])
            tk = cs[0][0]
            for kr in range(max(1, tk - step_k), min(r_max, tk + step_k) + 1):
                if kr not in k_list:
                    _search_k(kr)

        if best_pa < 1e29:
            break

    return best_k, best_w, non_spd, tot_eval, all_rej


def run_wf_selector(N, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=True, rng_h=None, tol=1e-6):
    P = len(l_arr)
    c2 = 1.0 / (2.0 * N)
    full_td_pow = compute_full_chan_pow(N, l_arr, alpha_arr, beta_arr, h_arr)
    hf_diag_cache = {}
    span_l = max(int(np.max(l_arr) - np.min(l_arr)), 1)
    r_max = min(max(d_band // span_l, 1), N)
    K_h = 24 if N <= 64 else 48
    qpsk_rad = np.exp(1j * (np.pi / 4.0 + (np.pi / 2.0) * rng_h.integers(0, 4, size=(N, K_h)))) if use_hutch else None
    cache = {}
    best_pa, best_k, best_w = 1e30, 1, np.zeros(P, dtype=int)
    spd_rej, tot_chk, all_rej_fallback = 0, 0, 0
    p_ord = np.argsort(np.abs(h_arr))[::-1]

    def _ev(kr, wv, req_s):
        nonlocal spd_rej, tot_chk
        if use_hutch:
            pa, spd = eval_hutchinson_pa(
                N, kr, wv, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, qpsk_rad, cache, require_spd=req_s, full_td_pow=full_td_pow, hf_diag_cache=hf_diag_cache, use_paper_eq14=False
            )
        else:
            pa, spd = eval_exact_pa_sparse(
                N, kr, wv, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, cache, require_spd=req_s, full_td_pow=full_td_pow, hf_diag_cache=hf_diag_cache, use_paper_eq14=False
            )
        tot_chk += 1
        if not spd:
            spd_rej += 1
        return pa, spd

    for pass_idx, req_s in enumerate((True, False)):
        if pass_idx == 1:
            all_rej_fallback = 1
        w_u_ref = None
        for kr in range(1, r_max + 1):
            w_bc, w_u = band_coupled_wf_seed(N, kr, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws)
            w_u_ref = w_u
            pa, spd = _ev(kr, w_bc, req_s)
            if ((not req_s) or spd) and pa < best_pa:
                best_pa, best_k, best_w = pa, kr, w_bc.copy()

        if best_pa < 1e29:
            if not np.array_equal(best_w, w_u_ref):
                pa_u, spd_u = _ev(best_k, w_u_ref, req_s)
                if ((not req_s) or spd_u) and pa_u < best_pa:
                    best_pa, best_w = pa_u, w_u_ref.copy()
            wc = best_w.copy()
            for (i, j) in [(int(p_ord[0]), int(p_ord[-1])), (int(p_ord[-1]), int(p_ord[0]))]:
                if i != j and wc[j] >= 1:
                    wn = wc.copy()
                    wn[i] += 1
                    wn[j] -= 1
                    pn, spdn = _ev(best_k, wn, req_s)
                    if ((not req_s) or spdn) and (pn < best_pa - tol):
                        best_pa, best_w, wc = pn, wn.copy(), wn.copy()
            break

    return best_k, best_w, spd_rej, tot_chk, all_rej_fallback


def mc_ber_lc_bmmse(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, X_qpsk, bits_true, noise_td):
    c1 = k_c / (2.0 * N)
    n_vec = np.arange(N)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (n_vec ** 2))[:, None]
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (n_vec ** 2))[:, None]
    X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * X_qpsk, axis=0) * np.sqrt(N)
    Y_td = noise_td.copy()
    for i in range(len(l_arr)):
        nup = alpha_arr[i] + beta_arr[i]
        dop = (h_arr[i] * np.exp(-1j * 2.0 * np.pi * nup * n_vec / N))[:, None]
        Y_td += dop * X_td[(n_vec - int(l_arr[i])) % N, :]
    Y_daft = L2 * (np.fft.fft(L1 * Y_td, axis=0) / np.sqrt(N))

    q = np.arange(N)
    diag_map, psi_diags, _ = build_sparse_and_psi_diags(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2)
    MF = np.zeros_like(Y_daft)
    for dlt, vq in diag_map.items():
        MF += np.conj(vq)[:, None] * Y_daft[(q + dlt) % N, :]
    X_hat, _ = solve_cyclic_diags(N, psi_diags, d_band, MF, require_spd=False)
    b_re = (np.real(X_hat) < 0.0).astype(int)
    b_im = (np.imag(X_hat) < 0.0).astype(int)
    return int(np.sum(b_re != bits_true[0]) + np.sum(b_im != bits_true[1]))


def mc_ber_rule30_td_exact(N, k_c, c2, l_arr, alpha_arr, beta_arr, h_arr, sigma2, X_qpsk, bits_true, noise_td):
    t0 = time.perf_counter()
    c1 = k_c / (2.0 * N)
    n_vec = np.arange(N)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (n_vec ** 2))[:, None]
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (n_vec ** 2))[:, None]
    l_max = int(np.max(l_arr))
    d_td = l_max + 1
    td_map = {}
    for i in range(len(l_arr)):
        li = int(l_arr[i])
        nup = alpha_arr[i] + beta_arr[i]
        p_idx = (n_vec + li) % N
        vq = h_arr[i] * np.exp(-1j * 2.0 * np.pi * nup * p_idx / N)
        td_map[li] = (td_map[li] + vq) if (li in td_map) else vq
    psi_td = np.zeros((d_td, N), dtype=complex)
    psi_td[0, :] = sigma2
    for d1, v1 in td_map.items():
        v1c = np.conj(v1)
        for d2, v2 in td_map.items():
            dd = (d1 - d2) % N
            if dd < d_td:
                psi_td[dd, :] += v1c * v2[(n_vec + dd) % N]
    X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * X_qpsk, axis=0) * np.sqrt(N)
    Y_td = noise_td.copy()
    for li, vq in td_map.items():
        Y_td[(n_vec + li) % N, :] += vq[:, None] * X_td
    MF_td = np.zeros_like(Y_td)
    for li, vq in td_map.items():
        MF_td += np.conj(vq)[:, None] * Y_td[(n_vec + li) % N, :]
    X_td_hat, _ = solve_cyclic_diags(N, psi_td, d_td, MF_td, require_spd=False)
    X_daft_hat = L2 * (np.fft.fft(L1 * X_td_hat, axis=0) / np.sqrt(N))
    dt = time.perf_counter() - t0
    b_re = (np.real(X_daft_hat) < 0.0).astype(int)
    b_im = (np.imag(X_daft_hat) < 0.0).astype(int)
    return int(np.sum(b_re != bits_true[0]) + np.sum(b_im != bits_true[1])), dt


def calibrate_offline_best_fixed(N=256, d_band=17, ws=16):
    rng = np.random.default_rng(20261125)
    c2 = 1.0 / (2.0 * N)
    sigma2 = 10.0 ** (-(16.0 + 3.0103) / 10.0)
    cand_pairs = [
        (k_f, np.array(w_f, dtype=int))
        for k_f in [1, 2, 3, 4]
        for w_f in [[6, 5, 5], [7, 5, 4], [8, 4, 4], [8, 5, 3]]
    ]
    scores = np.zeros(len(cand_pairs))
    for _ in range(24):
        rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
        l_arr = np.array([0, int(rem_l[0]), int(rem_l[1])])
        nu_raw = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
        al = np.round(nu_raw).astype(int)
        be = nu_raw - al
        pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0)
        pows /= np.sum(pows)
        h_arr = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
        b0 = rng.integers(0, 2, size=(N, 8))
        b1 = rng.integers(0, 2, size=(N, 8))
        Xq = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
        ntd = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((N, 8)) + 1j * rng.standard_normal((N, 8)))
        for ic, (kf, wf) in enumerate(cand_pairs):
            scores[ic] += mc_ber_lc_bmmse(N, kf, wf, c2, l_arr, al, be, h_arr, d_band, sigma2, Xq, (b0, b1), ntd)
    best_idx = int(np.argmin(scores))
    return cand_pairs[best_idx][0], cand_pairs[best_idx][1]


def verify_seed_disjointness():
    formal_list = []
    for nv, cnt in FORMAL_SPEED_COUNTS.items():
        sb = SPEED_SEED_BASES[nv]
        for tr_id in range(cnt):
            formal_list.append(sb + tr_id * 19)
            formal_list.append(sb + SPEED_PROBE_OFFSET + tr_id)
    for tr_id in range(FORMAL_N_ACC_256):
        formal_list.append(ACC_SEED_BASE + tr_id * 23)
        for ig in range(4):
            formal_list.append(ACC_PROBE_SEED_BASE + tr_id * 10 + ig)

    formal_set = set(formal_list)
    unique_ok = len(formal_set) == len(formal_list)
    in_band_ok = (min(formal_set) >= 3100000) and (max(formal_set) <= 3610000)

    # Enumerate ALL non-formal seeds (warmup, RL1, diagnostics, calibration, smoke, and all bootstrap seeds up to 20262050):
    nonformal_set = {960000, 960300, 960600, 964000, 20261125}
    for nv_w in (64, 128, 256, 512):
        nonformal_set.add(11 + nv_w)
        nonformal_set.add(51 + nv_w)
    nonformal_set.update(range(965000, 965020))
    nonformal_set.update(range(20261170, 20262050))
    for nv in (64, 128, 256, 512):
        sb = SPEED_SEED_BASES[nv]
        for k in range(len(SPEED_ARMS_BY_N[nv])):
            tr_sm = -100 - k
            nonformal_set.add(sb + tr_sm * 19)
            nonformal_set.add(sb + SPEED_PROBE_OFFSET + tr_sm)
    for k in range(2):
        tr_sm = -100 - k
        nonformal_set.add(ACC_SEED_BASE + tr_sm * 23)
        for ig in range(4):
            nonformal_set.add(ACC_PROBE_SEED_BASE + tr_sm * 10 + ig)

    disjoint_nonformal_ok = len(formal_set.intersection(nonformal_set)) == 0
    disjoint_historical_dev_ok = all(s >= 3100000 and s <= 3610000 for s in formal_set)
    return bool(unique_ok and in_band_ok and disjoint_nonformal_ok and disjoint_historical_dev_ok)


def verify_redline1_mao26():
    seed_ok = verify_seed_disjointness()

    rng = np.random.default_rng(960000)
    N = 256
    c2 = 1.0 / (2.0 * N)
    l_arr = np.array([0, 2, 5])
    al = np.array([-1, 0, 1])
    be = np.zeros(3)
    h_arr = np.array([0.8 + 0.1j, -0.4 + 0.3j, 0.25 - 0.2j])
    w0 = np.array([2, 2, 2])
    k0 = 2
    d_band = 17
    b0 = rng.integers(0, 2, size=(N, 2))
    b1 = rng.integers(0, 2, size=(N, 2))
    Xq = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
    c1 = k0 / (2.0 * N)
    nv = np.arange(N)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (nv ** 2))[:, None]
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]
    X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * Xq, axis=0) * np.sqrt(N)
    Y_td = np.zeros_like(X_td)
    for i in range(3):
        Y_td += (h_arr[i] * np.exp(-1j * 2.0 * np.pi * al[i] * nv / N))[:, None] * X_td[(nv - int(l_arr[i])) % N, :]
    Y_daft = L2 * (np.fft.fft(L1 * Y_td, axis=0) / np.sqrt(N))
    dm, pd, _ = build_sparse_and_psi_diags(N, k0, w0, c2, l_arr, al, be, h_arr, d_band, 1e-15)
    MF = np.zeros_like(Y_daft)
    for dlt, vq in dm.items():
        MF += np.conj(vq)[:, None] * Y_daft[(nv + dlt) % N, :]
    Xh, _ = solve_cyclic_diags(N, pd, d_band, MF, require_spd=False)
    rel_err_nl = float(np.linalg.norm(Xh - Xq) / np.linalg.norm(Xq))

    be_f = np.array([0.23, -0.37, 0.14])
    Hf = build_H_full_fast(127, 3, 1.0 / 254.0, l_arr, al, be_f, h_arr)
    G_exact = Hf.conj().T @ Hf
    _, pd_full, sd_full = build_sparse_and_psi_diags(127, 3, np.array([63, 63, 63]), 1.0 / 254.0, l_arr, al, be_f, h_arr, 64, 0.0)
    G_diag_err = float(np.linalg.norm(np.diag(G_exact) - pd_full[0]) / np.linalg.norm(np.diag(G_exact)))

    l_ov = np.array([0, 2, 4])
    al_ov = np.zeros(3, dtype=int)
    dm_ov, _, sd_fast_ov = build_sparse_and_psi_diags(128, 0, np.array([3, 0, 1]), 1.0 / 256.0, l_ov, al_ov, be_f, h_arr, 17, 0.0)
    Hf_ov = build_H_full_fast(128, 0, 1.0 / 256.0, l_ov, al_ov, be_f, h_arr)
    Hsp_ov = np.zeros_like(Hf_ov)
    q128 = np.arange(128)
    for dlt, vq in dm_ov.items():
        Hsp_ov[(q128 + dlt) % 128, q128] = vq
    sd_true_ov = float(np.linalg.norm(Hf_ov - Hsp_ov, "fro") ** 2 / 128.0)
    sd_ov_rel_err = float(abs(sd_true_ov - sd_fast_ov) / max(sd_true_ov, 1e-15)) + float(abs(sd_full))

    inits_k1 = mao26_all_eq45_inits(256, 1, l_ov, al_ov, 17, 16)
    inits_k4 = mao26_all_eq45_inits(256, 4, l_ov, al_ov, 17, 16)
    w_bc_b, _ = band_coupled_wf_seed(256, 4, l_ov, al_ov, np.array([0.2, 0.1, -0.1]), np.array([1.0, 0.5, 0.3]), 17, 16)
    boundary_ok = bool(
        (len(inits_k1) == 14)
        and ([int(w[0]) for w in inits_k1] == list(range(0, 14)))
        and all((np.all(w >= 0) and int(np.sum(w)) == 16 and int(w[0] + w[-1]) == 13) for w in inits_k1)
        and (len(inits_k4) == 2)
        and ([int(w[0]) for w in inits_k4] == [0, 1])
        and all((np.all(w >= 0) and int(np.sum(w)) == 16 and int(w[0] + w[-1]) == 1) for w in inits_k4)
        and bool(np.all(w_bc_b >= 0) and int(np.sum(w_bc_b)) == 16 and int(w_bc_b[0] + w_bc_b[-1]) == 0)
    )

    # Pure Section V / Table II / Fig. 12 random-delay operating point (N=256, d=16, ws=16, Eb/N0=15 dB, random delays in [0, 6]):
    sigma2_15 = 10.0 ** (-(15.0 + 3.0103) / 10.0)
    pows_tab2 = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0)
    rng_tab2 = np.random.default_rng(960300)
    err_tab2_hs, err_tab2_k1_wstar, tot_b_tab2 = 0, 0, 0
    for _ in range(20):
        l_rand = np.sort(rng_tab2.choice(np.arange(0, 7), size=3, replace=False))
        nu_r = (4.17 / 15.0) * np.cos(rng_tab2.uniform(-np.pi, np.pi, size=3))
        al_r = np.round(nu_r).astype(int)
        be_r = nu_r - al_r
        h_r = np.sqrt(pows_tab2 / 2.0) * (rng_tab2.standard_normal(3) + 1j * rng_tab2.standard_normal(3))
        km_r, wm_r, _, _, _ = run_hillclimb_selector(
            256, l_rand, al_r, be_r, h_r, 16, 16, sigma2_15, use_hutch=False, spd_two_pass=False, iter_max=15, step_k=1, tol=0.0, use_paper_eq14=True
        )
        _, wk1_r, _, _, _ = run_hillclimb_selector(
            256, l_rand, al_r, be_r, h_r, 16, 16, sigma2_15, use_hutch=False, spd_two_pass=False, iter_max=15, step_k=1, tol=0.0, fixed_k_list=[1], use_paper_eq14=True
        )
        b0 = rng_tab2.integers(0, 2, size=(256, 16))
        b1 = rng_tab2.integers(0, 2, size=(256, 16))
        Xq_r = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
        nt_r = np.sqrt(sigma2_15 / 2.0) * (rng_tab2.standard_normal((256, 16)) + 1j * rng_tab2.standard_normal((256, 16)))
        err_tab2_hs += mc_ber_lc_bmmse(256, km_r, wm_r, c2, l_rand, al_r, be_r, h_r, 16, sigma2_15, Xq_r, (b0, b1), nt_r)
        err_tab2_k1_wstar += mc_ber_lc_bmmse(256, 1, wk1_r, c2, l_rand, al_r, be_r, h_r, 16, sigma2_15, Xq_r, (b0, b1), nt_r)
        tot_b_tab2 += 2 * 256 * 16

    return {
        "seed_disjointness_exact_ok": seed_ok,
        "noiseless_lc_bmmse_rel_err": rel_err_nl,
        "full_gram_diag_rel_err": G_diag_err,
        "sigma_delta2_overlap_rel_err": sd_ov_rel_err,
        "boundary_eq45_and_wbc_exact_ok": boundary_ok,
        "tab2_rand_delay_paper_exact_mc_ber": err_tab2_hs / tot_b_tab2,
        "tab2_rand_delay_k1_wstar_mc_ber": err_tab2_k1_wstar / tot_b_tab2,
    }


def run_isolated_diagnostics():
    # Purely descriptive diagnostics (Fig. 2 l=[1,2,3] + Fig. 10 legend check, and small-N=64 153-composition exhaustive check),
    # completely isolated outside PASS_REDLINE1 / PASS_PRIMARY, with independent exception persistence per sub-block.
    out = {"fig2_l123_exception": None, "small_N64_exception": None}
    try:
        sigma2_15 = 10.0 ** (-(15.0 + 3.0103) / 10.0)
        pows_tab2 = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0)
        l_fig2 = np.array([1, 2, 3])
        w_k1_leg = np.array([1, 12, 3], dtype=int)
        w_k6_leg = np.array([3, 12, 1], dtype=int)
        rng10 = np.random.default_rng(960600)
        err_hs10, err_k1_10, err_k6_10, tot_b10 = 0, 0, 0, 0
        for _ in range(12):
            nu_r = (4.17 / 15.0) * np.cos(rng10.uniform(-np.pi, np.pi, size=3))
            al10 = np.round(nu_r).astype(int)
            be10 = nu_r - al10
            h10 = np.sqrt(pows_tab2 / 2.0) * (rng10.standard_normal(3) + 1j * rng10.standard_normal(3))
            km10, wm10, _, _, _ = run_hillclimb_selector(256, l_fig2, al10, be10, h10, 16, 16, sigma2_15, use_hutch=False, spd_two_pass=False, iter_max=15, step_k=1, tol=0.0, use_paper_eq14=True)
            b0 = rng10.integers(0, 2, size=(256, 16))
            b1 = rng10.integers(0, 2, size=(256, 16))
            Xq10 = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
            nt10 = np.sqrt(sigma2_15 / 2.0) * (rng10.standard_normal((256, 16)) + 1j * rng10.standard_normal((256, 16)))
            err_hs10 += mc_ber_lc_bmmse(256, km10, wm10, 1.0 / 512.0, l_fig2, al10, be10, h10, 16, sigma2_15, Xq10, (b0, b1), nt10)
            err_k1_10 += mc_ber_lc_bmmse(256, 1, w_k1_leg, 1.0 / 512.0, l_fig2, al10, be10, h10, 16, sigma2_15, Xq10, (b0, b1), nt10)
            err_k6_10 += mc_ber_lc_bmmse(256, 6, w_k6_leg, 1.0 / 512.0, l_fig2, al10, be10, h10, 16, sigma2_15, Xq10, (b0, b1), nt10)
            tot_b10 += 2 * 256 * 16
        out["fig2_l123_paper_exact_mc_ber"] = err_hs10 / tot_b10
        out["fig2_l123_k1_w1123_mc_ber"] = err_k1_10 / tot_b10
        out["fig2_l123_k6_w3121_mc_ber"] = err_k6_10 / tot_b10
    except Exception as exc_f2:
        out["fig2_l123_exception"] = repr(exc_f2)

    try:
        rng = np.random.default_rng(964000)
        exh_gap_pa = []
        for tr_e in range(10):
            rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
            le = np.array([0, int(rem_l[0]), int(rem_l[1])])
            nu_e = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
            ale = np.round(nu_e).astype(int)
            bee = nu_e - ale
            pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0)
            pows /= np.sum(pows)
            he = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
            s2e = 10.0 ** (-(16.0 + 3.0103) / 10.0)
            fpow_e = compute_full_chan_pow(64, le, ale, bee, he)
            hfd_cache = {}
            rm_e = min(max(17 // int(le[-1] - le[0]), 1), 64)
            best_exh_spd, best_exh_any = 1e30, 1e30
            Hfe_cache = {}
            for kre in range(1, rm_e + 1):
                for w1 in range(0, 17):
                    for w2 in range(0, 17 - w1):
                        w3 = 16 - w1 - w2
                        pae, spde = eval_exact_pa_sparse(
                            64, kre, np.array([w1, w2, w3]), 1.0 / 128.0, le, ale, bee, he, 17, s2e, Hfe_cache, require_spd=False, full_td_pow=fpow_e, hf_diag_cache=hfd_cache, use_paper_eq14=False
                        )
                        if pae < best_exh_any:
                            best_exh_any = pae
                        if spde and pae < best_exh_spd:
                            best_exh_spd = pae
            best_exh = best_exh_spd if (best_exh_spd < 1e29) else best_exh_any
            kp_e, wp_e, _, _, _ = run_wf_selector(64, le, ale, bee, he, 17, 16, s2e, use_hutch=True, rng_h=np.random.default_rng(965000 + tr_e), tol=1e-6)
            pap_e, _ = eval_exact_pa_sparse(
                64, kp_e, wp_e, 1.0 / 128.0, le, ale, bee, he, 17, s2e, Hfe_cache, require_spd=False, full_td_pow=fpow_e, hf_diag_cache=hfd_cache, use_paper_eq14=False
            )
            exh_gap_pa.append(pap_e / max(best_exh, 1e-9))
        out["small_N64_prop_over_exhaustive_pa_mean"] = float(np.mean(exh_gap_pa))
    except Exception as exc_n64:
        out["small_N64_exception"] = repr(exc_n64)
    return out


_WORKER_WARMED = False


def _ensure_warmup():
    global _WORKER_WARMED
    if not _WORKER_WARMED:
        l_w = np.array([0, 3, 6])
        al_w = np.zeros(3, dtype=int)
        be_w = np.array([0.1, -0.1, 0.05])
        h_w = np.array([0.8 + 0j, 0.4 + 0j, 0.2 + 0j])
        for nv_w in (64, 128, 256, 512):
            run_hillclimb_selector(nv_w, l_w, al_w, be_w, h_w, 17, 16, 0.02, use_hutch=False, spd_two_pass=False, iter_max=1, step_k=1, tol=0.0, use_paper_eq14=True)
            run_hillclimb_selector(nv_w, l_w, al_w, be_w, h_w, 17, 16, 0.02, use_hutch=False, spd_two_pass=True, iter_max=1, step_k=2, tol=1e-6, use_paper_eq14=False)
            run_hillclimb_selector(nv_w, l_w, al_w, be_w, h_w, 17, 16, 0.02, use_hutch=True, rng_h=np.random.default_rng(11 + nv_w), spd_two_pass=True, iter_max=1, step_k=1, tol=1e-6, use_paper_eq14=False)
            run_wf_selector(nv_w, l_w, al_w, be_w, h_w, 17, 16, 0.02, use_hutch=False, rng_h=None, tol=1e-6)
            run_wf_selector(nv_w, l_w, al_w, be_w, h_w, 17, 16, 0.02, use_hutch=True, rng_h=np.random.default_rng(51 + nv_w), tol=1e-6)
            pd_lu = np.zeros((17, nv_w), dtype=complex)
            pd_lu[0, :] = -1.0
            pd_lu[1, :] = 0.2
            fac_lu, _ = factor_cyclic_diags(nv_w, pd_lu, 17, require_spd=False)
            apply_cyclic_factor(fac_lu, np.ones((nv_w, 2), dtype=complex))
        _WORKER_WARMED = True


def run_speed_trial(task_tuple):
    _, N_v, tr_id = task_tuple
    _ensure_warmup()
    seed_base = SPEED_SEED_BASES[N_v]
    rng = np.random.default_rng(seed_base + tr_id * 19)
    rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
    l_arr = np.array([0, int(rem_l[0]), int(rem_l[1])])
    nu_raw = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
    alpha_arr = np.round(nu_raw).astype(int)
    beta_arr = nu_raw - alpha_arr
    pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0)
    pows /= np.sum(pows)
    h_arr = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
    sigma2 = 10.0 ** (-(16.0 + 3.0103) / 10.0)
    d_band = 17
    ws = 16

    probe_seed = seed_base + SPEED_PROBE_OFFSET + tr_id
    rng_b = np.random.default_rng(probe_seed)
    rng_p = np.random.default_rng(probe_seed)

    arm_list = SPEED_ARMS_BY_N[N_v]
    L_arms = len(arm_list)
    ord_idx = abs(int(tr_id))
    exec_order = [arm_list[(ord_idx + pos) % L_arms] for pos in range(L_arms)]

    wall_t = {"mao26": 0.0, "mao26_spd": 0.0, "cf": 0.0, "cf_spd": 0.0, "a_only": 0.0, "b_only": 0.0, "prop": 0.0}
    cpu_t = {"mao26": 0.0, "mao26_spd": 0.0, "cf": 0.0, "cf_spd": 0.0, "a_only": 0.0, "b_only": 0.0, "prop": 0.0}
    arm_pos = {}
    nspd_m, tot_m, mspd_fb, spd_rej, tot_chk, all_rej = 0, 0, 0, 0, 0, 0

    for pos, ak in enumerate(exec_order):
        arm_pos[ak] = pos
        w0 = time.perf_counter()
        c0 = time.process_time()
        if ak == "mao26":
            _, _, nspd_m, tot_m, _ = run_hillclimb_selector(
                N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, spd_two_pass=False, iter_max=15, step_k=1, tol=0.0, use_paper_eq14=True
            )
        elif ak == "mao26_spd":
            _, _, _, _, mspd_fb = run_hillclimb_selector(
                N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, spd_two_pass=True, iter_max=15, step_k=1, tol=1e-6, use_paper_eq14=False
            )
        elif ak == "cf":
            run_hillclimb_selector(
                N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, spd_two_pass=False, iter_max=15, step_k=2, tol=0.0, use_paper_eq14=True
            )
        elif ak == "cf_spd":
            run_hillclimb_selector(
                N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, spd_two_pass=True, iter_max=15, step_k=2, tol=1e-6, use_paper_eq14=False
            )
        elif ak == "a_only":
            run_wf_selector(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, rng_h=None, tol=1e-6)
        elif ak == "b_only":
            run_hillclimb_selector(
                N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=True, rng_h=rng_b, spd_two_pass=True, iter_max=15, step_k=1, tol=1e-6, use_paper_eq14=False
            )
        elif ak == "prop":
            _, _, spd_rej, tot_chk, all_rej = run_wf_selector(
                N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=True, rng_h=rng_p, tol=1e-6
            )
        cpu_t[ak] = time.process_time() - c0
        wall_t[ak] = time.perf_counter() - w0

    return {
        "kind": "SPEED",
        "N": N_v,
        "tr_id": int(tr_id),
        "arm_pos": arm_pos,
        "t_mao": wall_t["mao26"],
        "t_mao_spd": wall_t["mao26_spd"],
        "t_cf": wall_t["cf"],
        "t_cf_spd": wall_t["cf_spd"],
        "t_a": wall_t["a_only"],
        "t_b": wall_t["b_only"],
        "t_prop": wall_t["prop"],
        "cpu_mao": cpu_t["mao26"],
        "cpu_mao_spd": cpu_t["mao26_spd"],
        "cpu_prop": cpu_t["prop"],
        "mao_nonspd": nspd_m,
        "mao_evals": tot_m,
        "mao_spd_all_rej": mspd_fb,
        "prop_spd_rej": spd_rej,
        "prop_evals": tot_chk,
        "prop_all_rej": all_rej,
    }


def run_acc_curve_trial(task_tuple):
    _, tr_id, k_fix, w_fix_tup = task_tuple
    _ensure_warmup()
    w_fix = np.array(w_fix_tup, dtype=int) if (w_fix_tup is not None) else None
    N_v = 256
    d_band = 17
    ws = 16
    c2 = 1.0 / (2.0 * N_v)
    B_blk = 96
    snrs_eb = [10.0, 13.0, 16.0, 19.0]
    rng = np.random.default_rng(ACC_SEED_BASE + tr_id * 23)

    rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
    l_arr = np.array([0, int(rem_l[0]), int(rem_l[1])])
    nu_raw = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
    alpha_arr = np.round(nu_raw).astype(int)
    beta_arr = nu_raw - alpha_arr
    pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0)
    pows /= np.sum(pows)
    h_arr = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))

    primary_arms = ["mao26", "mao26_spd", "cf", "cf_spd", "prop"]
    desc_arms = ["fixed", "c1_zero_same_c2", "rule30_td"]
    errs = {ak: [] for ak in (primary_arms + desc_arms)}
    desc_ok = {ak: True for ak in desc_arms}
    desc_exc = {ak: [] for ak in desc_arms}
    t_r30_ms = []

    for ig, eb_db in enumerate(snrs_eb):
        sigma2 = 10.0 ** (-(eb_db + 3.0103) / 10.0)
        km, wm, _, _, _ = run_hillclimb_selector(
            N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, spd_two_pass=False, iter_max=15, step_k=1, tol=0.0, use_paper_eq14=True
        )
        kms, wms, _, _, _ = run_hillclimb_selector(
            N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, spd_two_pass=True, iter_max=15, step_k=1, tol=1e-6, use_paper_eq14=False
        )
        kcf, wcf, _, _, _ = run_hillclimb_selector(
            N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, spd_two_pass=False, iter_max=15, step_k=2, tol=0.0, use_paper_eq14=True
        )
        kcfs, wcfs, _, _, _ = run_hillclimb_selector(
            N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=False, spd_two_pass=True, iter_max=15, step_k=2, tol=1e-6, use_paper_eq14=False
        )
        rng_p = np.random.default_rng(ACC_PROBE_SEED_BASE + tr_id * 10 + ig)
        kp, wp, _, _, _ = run_wf_selector(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, use_hutch=True, rng_h=rng_p, tol=1e-6)

        b0 = rng.integers(0, 2, size=(N_v, B_blk))
        b1 = rng.integers(0, 2, size=(N_v, B_blk))
        Xq = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
        ntd = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((N_v, B_blk)) + 1j * rng.standard_normal((N_v, B_blk)))

        errs["mao26"].append(mc_ber_lc_bmmse(N_v, km, wm, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        errs["mao26_spd"].append(mc_ber_lc_bmmse(N_v, kms, wms, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        errs["cf"].append(mc_ber_lc_bmmse(N_v, kcf, wcf, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        errs["cf_spd"].append(mc_ber_lc_bmmse(N_v, kcfs, wcfs, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        errs["prop"].append(mc_ber_lc_bmmse(N_v, kp, wp, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))

        # Descriptive controls isolated inside try...except with explicit exception capture (never silently swallowed!):
        if w_fix is not None:
            try:
                errs["fixed"].append(mc_ber_lc_bmmse(N_v, k_fix, w_fix, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
            except Exception as exc:
                desc_ok["fixed"] = False
                desc_exc["fixed"].append(f"tr={tr_id},ig={ig}: {exc!r}")
                errs["fixed"].append(0)
        else:
            desc_ok["fixed"] = False
            desc_exc["fixed"].append(f"tr={tr_id},ig={ig}: offline_fixed_unavailable")
            errs["fixed"].append(0)

        try:
            errs["c1_zero_same_c2"].append(mc_ber_lc_bmmse(N_v, 0, wp, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        except Exception as exc:
            desc_ok["c1_zero_same_c2"] = False
            desc_exc["c1_zero_same_c2"].append(f"tr={tr_id},ig={ig}: {exc!r}")
            errs["c1_zero_same_c2"].append(0)

        try:
            er30, dt30 = mc_ber_rule30_td_exact(N_v, kp, c2, l_arr, alpha_arr, beta_arr, h_arr, sigma2, Xq, (b0, b1), ntd)
            errs["rule30_td"].append(er30)
            t_r30_ms.append(1e3 * dt30 / B_blk)
        except Exception as exc:
            desc_ok["rule30_td"] = False
            desc_exc["rule30_td"].append(f"tr={tr_id},ig={ig}: {exc!r}")
            errs["rule30_td"].append(0)

    return {
        "kind": "ACC256",
        "bits_per_pt": 2 * N_v * B_blk,
        "errs": errs,
        "desc_ok": desc_ok,
        "desc_exc": desc_exc,
        "rule30_per_block_ms": float(np.mean(t_r30_ms)) if t_r30_ms else None,
    }


def paired_geom_ratio_t_ci95(t_num, t_den):
    tn = np.asarray(t_num, dtype=float)
    td = np.asarray(t_den, dtype=float)
    M = len(tn)
    if M < 2 or np.any(tn <= 0.0) or np.any(td <= 0.0):
        return {"geom_ratio": float("nan"), "ci95": [0.0, float("inf")], "log_halfwidth": float("inf")}
    lr = np.log(tn / td)
    ml = float(np.mean(lr))
    tc = float(sp_t.ppf(0.975, df=M - 1))
    hw = tc * float(np.std(lr, ddof=1)) / np.sqrt(M)
    return {"geom_ratio": float(np.exp(ml)), "ci95": [float(np.exp(ml - hw)), float(np.exp(ml + hw))], "log_halfwidth": hw}


def paired_log_share_boot_ci95(t_base, t_arm, t_prop, n_boot=4000, seed=20261180):
    tb = np.asarray(t_base, dtype=float)
    ta = np.asarray(t_arm, dtype=float)
    tp = np.asarray(t_prop, dtype=float)
    M = len(tb)
    if M < 2 or np.any(tb <= 0.0) or np.any(ta <= 0.0) or np.any(tp <= 0.0):
        return {"point": float("inf"), "ci95": [float("-inf"), float("inf")], "halfwidth": float("inf"), "valid": False}
    g_sub = np.log(tb / ta)
    g_full = np.log(tb / tp)
    mf = float(np.mean(g_full))
    if mf <= 0.0:
        return {"point": float("inf"), "ci95": [float("-inf"), float("inf")], "halfwidth": float("inf"), "valid": False}
    pt = float(np.mean(g_sub) / mf)
    rb = np.random.default_rng(seed)
    idx = rb.integers(0, M, size=(n_boot, M))
    ms_b = np.mean(g_sub[idx], axis=1)
    mf_b = np.mean(g_full[idx], axis=1)
    if np.any(mf_b <= 0.0):
        return {"point": pt, "ci95": [float("-inf"), float("inf")], "halfwidth": float("inf"), "valid": False}
    sh = np.sort(ms_b / mf_b)
    lo = float(sh[int(np.floor(0.025 * (n_boot - 1)))])
    hi = float(sh[int(np.ceil(0.975 * (n_boot - 1)))])
    hw = 0.5 * (hi - lo) if (np.isfinite(lo) and np.isfinite(hi)) else float("inf")
    return {"point": pt, "ci95": [lo, hi], "halfwidth": hw, "valid": bool(np.isfinite(hw))}


def paired_ber_ratio_boot_ci95(err_num_arr, err_den_arr, n_boot=4000, seed=20261125):
    en = np.asarray(err_num_arr, dtype=float)
    ed = np.asarray(err_den_arr, dtype=float)
    M = len(en)
    s_n, s_d = float(np.sum(en)), float(np.sum(ed))
    if M < 2 or s_n <= 0.0 or s_d <= 0.0:
        pt = (s_n / s_d) if s_d > 0.0 else (float("inf") if s_n > 0.0 else float("nan"))
        return {"point": pt, "ci95": [0.0, float("inf")], "log_halfwidth": float("inf"), "observed_zero_undecidable": True}
    pt = s_n / s_d
    rb = np.random.default_rng(seed)
    idx = rb.integers(0, M, size=(n_boot, M))
    sn = np.sum(en[idx], axis=1)
    sd = np.sum(ed[idx], axis=1)
    rat = np.where(sd > 0.0, np.where(sn > 0.0, sn / np.where(sd > 0.0, sd, 1.0), 0.0), np.inf)
    sr = np.sort(rat)
    lo = float(sr[int(np.floor(0.025 * (n_boot - 1)))])
    hi = float(sr[int(np.ceil(0.975 * (n_boot - 1)))])
    valid_finite = bool(np.isfinite(hi) and (lo > 0.0))
    lhw = 0.5 * float(np.log(hi / lo)) if valid_finite else float("inf")
    return {"point": pt, "ci95": [lo, hi], "log_halfwidth": lhw, "observed_zero_undecidable": False}


def snr_at_target_strict(snrs, bers, target=3.0e-3):
    crossings = []
    for idx in range(len(snrs) - 1):
        b_lo, b_hi = float(bers[idx]), float(bers[idx + 1])
        if (b_lo >= target >= b_hi) and (b_hi > 0.0):
            lb_lo, lb_hi, lt = math.log10(b_lo), math.log10(b_hi), math.log10(target)
            denom = lb_lo - lb_hi
            frac = (lb_lo - lt) / denom if denom > 0.0 else 0.0
            crossings.append(float(snrs[idx] + frac * (snrs[idx + 1] - snrs[idx])))
    if len(crossings) == 1:
        return crossings[0], True
    return float("nan"), False


def paired_delta_snr_ci95(err_prop_mat, err_mao_mat, bits_per_frame, snrs, target=3.0e-3, n_boot=4000, seed=20261125):
    M = err_prop_mat.shape[0]
    tot_b = float(M * bits_per_frame)
    if M < 2 or tot_b <= 0.0:
        return {
            "point": float("inf"),
            "ci95": [float("-inf"), float("inf")],
            "halfwidth": float("inf"),
            "observed_crossing_valid": False,
            "all_boot_crossings_valid": False,
        }
    sp_pt, ok_p = snr_at_target_strict(snrs, np.sum(err_prop_mat, axis=0) / tot_b, target)
    sm_pt, ok_m = snr_at_target_strict(snrs, np.sum(err_mao_mat, axis=0) / tot_b, target)
    obs_ok = bool(ok_p and ok_m)
    pt = (sp_pt - sm_pt) if obs_ok else float("inf")
    rb = np.random.default_rng(seed)
    diffs = np.empty(n_boot, dtype=float)
    boot_ok = True
    for b in range(n_boot):
        ix = rb.integers(0, M, size=M)
        sp_b, ok_pb = snr_at_target_strict(snrs, np.sum(err_prop_mat[ix], axis=0) / tot_b, target)
        sm_b, ok_mb = snr_at_target_strict(snrs, np.sum(err_mao_mat[ix], axis=0) / tot_b, target)
        if ok_pb and ok_mb:
            diffs[b] = sp_b - sm_b
        else:
            boot_ok = False
            diffs[b] = np.nan
    if (not obs_ok) or (not boot_ok):
        return {
            "point": pt,
            "ci95": [float("-inf"), float("inf")],
            "halfwidth": float("inf"),
            "observed_crossing_valid": obs_ok,
            "all_boot_crossings_valid": boot_ok,
        }
    sd = np.sort(diffs)
    lo = float(sd[int(np.floor(0.025 * (n_boot - 1)))])
    hi = float(sd[int(np.ceil(0.975 * (n_boot - 1)))])
    hw = 0.5 * (hi - lo) if (np.isfinite(lo) and np.isfinite(hi)) else float("inf")
    return {
        "point": pt,
        "ci95": [lo, hi],
        "halfwidth": hw,
        "observed_crossing_valid": True,
        "all_boot_crossings_valid": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="summary_g_r11_g02.json")
    args = ap.parse_args()

    t_start = time.time()
    rl1, rl1_exc = {}, None
    try:
        rl1 = verify_redline1_mao26()
        print("[Red-Line 1]", json.dumps(rl1), flush=True)
        v_redline1 = (
            bool(rl1["seed_disjointness_exact_ok"])
            and (rl1["noiseless_lc_bmmse_rel_err"] < 1e-12)
            and (rl1["full_gram_diag_rel_err"] < 1e-12)
            and (rl1["sigma_delta2_overlap_rel_err"] < 1e-12)
            and bool(rl1["boundary_eq45_and_wbc_exact_ok"])
            and (1.5e-4 <= rl1["tab2_rand_delay_paper_exact_mc_ber"] <= 2.0e-3)
            and (rl1["tab2_rand_delay_paper_exact_mc_ber"] < rl1["tab2_rand_delay_k1_wstar_mc_ber"])
        )
    except Exception as exc:
        rl1_exc = repr(exc)
        v_redline1 = False

    if not v_redline1:
        fail_s = {
            "_argv": list(sys.argv),
            "card_id": "I-20261125-g02",
            "smoke": bool(args.smoke),
            "redline1": rl1,
            "redline1_exception": rl1_exc,
            "verdicts": {
                "PASS_REDLINE1": False,
                "PASS_CI_PRECISION_25PCT": False,
                "PASS_SPEEDUP_10X": False,
                "PASS_ACCURACY_02DB": False,
                "PASS_ABLATION_AB": False,
                "PASS_PRIMARY": False,
            },
        }
        with open(args.out, "w") as f:
            json.dump(_json_safe(fail_s), f, indent=2, allow_nan=False)
        raise RuntimeError(f"Red-Line 1 failed: {rl1} | exc={rl1_exc}")

    try:
        diag_isolated = run_isolated_diagnostics()
        diag_isolated["diagnostic_exception"] = None
    except Exception as dexc:
        diag_isolated = {"diagnostic_exception": repr(dexc)}

    cal_exc = None
    try:
        k_fix_star, w_fix_star = calibrate_offline_best_fixed(256, 17, 16)
        w_fix_tup = tuple(int(x) for x in w_fix_star.tolist())
    except Exception as cexc:
        k_fix_star, w_fix_tup = None, None
        cal_exc = repr(cexc)
    diag_isolated["offline_fixed_cal_exception"] = cal_exc

    speed_counts = {nv: len(SPEED_ARMS_BY_N[nv]) for nv in (64, 128, 256, 512)} if args.smoke else FORMAL_SPEED_COUNTS
    n_acc_256 = 2 if args.smoke else FORMAL_N_ACC_256

    speed_tasks = [
        ("SPEED", nv, (-100 - k if args.smoke else k))
        for nv, cnt in speed_counts.items()
        for k in range(cnt)
    ]
    acc_tasks = [
        ("ACC256", (-100 - k if args.smoke else k), k_fix_star, w_fix_tup)
        for k in range(n_acc_256)
    ]

    w_cnt = max(1, min(args.workers, 8))
    if w_cnt <= 1:
        sp_res = [run_speed_trial(t) for t in speed_tasks]
        ac_res = [run_acc_curve_trial(t) for t in acc_tasks]
    else:
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            sp_res = list(ex.map(run_speed_trial, speed_tasks))
            ac_res = list(ex.map(run_acc_curve_trial, acc_tasks))

    sp_by_n = {nv: [] for nv in [64, 128, 256, 512]}
    for r in sp_res:
        sp_by_n[r["N"]].append(r)

    position_balance_exact_ok = True
    for nv in (64, 128, 256, 512):
        rl = sp_by_n[nv]
        arms_nv = SPEED_ARMS_BY_N[nv]
        L_nv = len(arms_nv)
        if len(rl) == 0 or (len(rl) % L_nv != 0):
            position_balance_exact_ok = False
        else:
            exp_each = len(rl) // L_nv
            for ak in arms_nv:
                pos_counts = [sum(1 for x in rl if x["arm_pos"][ak] == p) for p in range(L_nv)]
                if any(c != exp_each for c in pos_counts):
                    position_balance_exact_ok = False

    speed_metrics = {}
    ci_spd = {"mao26": {}, "mao26_spd": {}, "cf": {}, "cf_spd": {}}
    for nv in [64, 128, 256, 512]:
        rl = sp_by_n[nv]
        tm = [x["t_mao"] for x in rl]
        tms = [x["t_mao_spd"] for x in rl]
        tcf = [x["t_cf"] for x in rl]
        tcfs = [x["t_cf_spd"] for x in rl]
        tp = [x["t_prop"] for x in rl]
        ci_spd["mao26"][str(nv)] = paired_geom_ratio_t_ci95(tm, tp)
        ci_spd["mao26_spd"][str(nv)] = paired_geom_ratio_t_ci95(tms, tp)
        ci_spd["cf"][str(nv)] = paired_geom_ratio_t_ci95(tcf, tp)
        ci_spd["cf_spd"][str(nv)] = paired_geom_ratio_t_ci95(tcfs, tp)
        speed_metrics[str(nv)] = {
            "n_frames": len(rl),
            "mean_paper_exact_mao26_ms": float(1e3 * np.mean(tm)),
            "mean_mao26_spd_ms": float(1e3 * np.mean(tms)),
            "mean_cf_ms": float(1e3 * np.mean(tcf)),
            "mean_cf_spd_ms": float(1e3 * np.mean(tcfs)),
            "mean_prop_ms": float(1e3 * np.mean(tp)),
            "geom_speedup_vs_paper_exact_mao26_ci95": ci_spd["mao26"][str(nv)],
            "geom_speedup_vs_mao26_spd_ci95": ci_spd["mao26_spd"][str(nv)],
            "geom_speedup_vs_cf_ci95": ci_spd["cf"][str(nv)],
            "geom_speedup_vs_cf_spd_ci95": ci_spd["cf_spd"][str(nv)],
            "descriptive_cpu_speedup_vs_paper_exact": paired_geom_ratio_t_ci95([x["cpu_mao"] for x in rl], [x["cpu_prop"] for x in rl]),
            "descriptive_cpu_speedup_vs_mao26_spd": paired_geom_ratio_t_ci95([x["cpu_mao_spd"] for x in rl], [x["cpu_prop"] for x in rl]),
            "mao26_nonspd_rate": float(sum(x["mao_nonspd"] for x in rl) / max(sum(x["mao_evals"] for x in rl), 1)),
            "mao26_spd_all_rejected_frames": int(sum(x["mao_spd_all_rej"] for x in rl)),
            "prop_spd_reject_rate": float(sum(x["prop_spd_rej"] for x in rl) / max(sum(x["prop_evals"] for x in rl), 1)),
            "prop_all_rejected_frames": int(sum(x["prop_all_rej"] for x in rl)),
        }

    ci_a_ratio = {
        str(nv): paired_geom_ratio_t_ci95([x["t_a"] for x in sp_by_n[nv]], [x["t_prop"] for x in sp_by_n[nv]])
        for nv in (256, 512)
    }
    ci_b_ratio = {
        str(nv): paired_geom_ratio_t_ci95([x["t_b"] for x in sp_by_n[nv]], [x["t_prop"] for x in sp_by_n[nv]])
        for nv in (64, 256, 512)
    }

    log_shares_spd = {}
    log_shares_raw = {}
    desc_lin_time_saved_shares_spd = {}
    for nv in (256, 512):
        tms = [x["t_mao_spd"] for x in sp_by_n[nv]]
        tmr = [x["t_mao"] for x in sp_by_n[nv]]
        ta = [x["t_a"] for x in sp_by_n[nv]]
        tp = [x["t_prop"] for x in sp_by_n[nv]]
        log_shares_spd[f"A_only_N{nv}"] = paired_log_share_boot_ci95(tms, ta, tp, seed=20261180 + nv)
        log_shares_raw[f"A_only_N{nv}"] = paired_log_share_boot_ci95(tmr, ta, tp, seed=20261280 + nv)
        desc_lin_time_saved_shares_spd[f"A_only_N{nv}"] = float((np.mean(tms) - np.mean(ta)) / max(np.mean(tms) - np.mean(tp), 1e-12))

    for nv in (64, 256, 512):
        tms = [x["t_mao_spd"] for x in sp_by_n[nv]]
        tmr = [x["t_mao"] for x in sp_by_n[nv]]
        tb = [x["t_b"] for x in sp_by_n[nv]]
        tp = [x["t_prop"] for x in sp_by_n[nv]]
        log_shares_spd[f"B_only_N{nv}"] = paired_log_share_boot_ci95(tms, tb, tp, seed=20261380 + nv)
        log_shares_raw[f"B_only_N{nv}"] = paired_log_share_boot_ci95(tmr, tb, tp, seed=20261480 + nv)
        desc_lin_time_saved_shares_spd[f"B_only_N{nv}"] = float((np.mean(tms) - np.mean(tb)) / max(np.mean(tms) - np.mean(tp), 1e-12))

    snrs_eb = [10.0, 13.0, 16.0, 19.0]
    bpf = ac_res[0]["bits_per_pt"]
    primary_acc_rivals = ("mao26", "mao26_spd", "cf", "cf_spd")
    all_acc_arms = ("mao26", "mao26_spd", "cf", "cf_spd", "prop", "fixed", "c1_zero_same_c2", "rule30_td")
    err_mats = {ak: np.array([r["errs"][ak] for r in ac_res], dtype=float) for ak in all_acc_arms}
    tot_bits_pt = len(ac_res) * bpf
    mc_ber_curves = {ak: [float(x) for x in (np.sum(err_mats[ak], axis=0) / tot_bits_pt)] for ak in primary_acc_rivals + ("prop",)}

    ci_dsnr = {}
    ci_ber_hi = {}
    for ir, rk in enumerate(primary_acc_rivals):
        ci_dsnr[rk] = paired_delta_snr_ci95(err_mats["prop"], err_mats[rk], bpf, snrs_eb, target=3.0e-3, seed=20261170 + ir * 2)
        ci_ber_hi[rk] = paired_ber_ratio_boot_ci95(np.sum(err_mats["prop"][:, 2:], axis=1), np.sum(err_mats[rk][:, 2:], axis=1), seed=20261171 + ir * 2)

    desc_acc = {
        "offline_fixed_cal_exception": cal_exc,
        "diagnostic_failures": {
            dak: {
                "failed_frames": int(sum(1 for r in ac_res if not r["desc_ok"][dak])),
                "exceptions": [e for r in ac_res for e in r["desc_exc"][dak]],
            }
            for dak in ("fixed", "c1_zero_same_c2", "rule30_td")
        },
    }
    if all(r["desc_ok"]["fixed"] for r in ac_res):
        mc_ber_curves["fixed"] = [float(x) for x in (np.sum(err_mats["fixed"], axis=0) / tot_bits_pt)]
        desc_acc["BER19dB_FixedOffline_over_Prop"] = paired_ber_ratio_boot_ci95(err_mats["fixed"][:, 3], err_mats["prop"][:, 3], seed=20261190)
    if all(r["desc_ok"]["c1_zero_same_c2"] for r in ac_res):
        mc_ber_curves["c1_zero_same_c2"] = [float(x) for x in (np.sum(err_mats["c1_zero_same_c2"], axis=0) / tot_bits_pt)]
        desc_acc["BER19dB_c1zero_same_c2_over_Prop"] = paired_ber_ratio_boot_ci95(err_mats["c1_zero_same_c2"][:, 3], err_mats["prop"][:, 3], seed=20261191)
    if all(r["desc_ok"]["rule30_td"] and (r["rule30_per_block_ms"] is not None) for r in ac_res):
        mc_ber_curves["rule30_td"] = [float(x) for x in (np.sum(err_mats["rule30_td"], axis=0) / tot_bits_pt)]
        desc_acc["rule30_td_per_block_ms"] = float(np.mean([r["rule30_per_block_ms"] for r in ac_res]))

    all_spd_cis = [ci_spd[rk][str(nv)] for rk in ("mao26", "mao26_spd", "cf", "cf_spd") for nv in (64, 128, 256, 512)]
    min_spd_low = float(min(c["ci95"][0] for c in all_spd_cis))
    max_spd_lhw = float(max(c["log_halfwidth"] for c in all_spd_cis))

    all_ab_ratio_cis = list(ci_a_ratio.values()) + list(ci_b_ratio.values())
    max_ab_ratio_lhw = float(max(c["log_halfwidth"] for c in all_ab_ratio_cis))

    all_share_cis = list(log_shares_spd.values()) + list(log_shares_raw.values())
    max_share_hw = float(max(c["halfwidth"] for c in all_share_cis))
    all_shares_valid = all(bool(c["valid"]) for c in all_share_cis)
    max_share_ci_high = float(max(c["ci95"][1] for c in all_share_cis))

    max_dsnr_hw = float(max(ci_dsnr[rk]["halfwidth"] for rk in primary_acc_rivals))
    max_ber_hi_lhw = float(max(ci_ber_hi[rk]["log_halfwidth"] for rk in primary_acc_rivals))

    counts_exact_ok = (
        all(len(sp_by_n[nv]) == FORMAL_SPEED_COUNTS[nv] for nv in (64, 128, 256, 512))
        and (len(ac_res) == FORMAL_N_ACC_256)
    )

    cap_10x = cap_ratio_lhw(10.0)
    cap_5x = cap_ratio_lhw(5.0)
    cap_3x = cap_ratio_lhw(3.0)
    cap_115x = cap_ratio_lhw(1.15)
    cap_dsnr = 0.25 * 0.20
    cap_share = 0.25 * (1.0 - 0.80)

    v_ci_precision = bool(
        (not args.smoke)
        and counts_exact_ok
        and position_balance_exact_ok
        and all_shares_valid
        and all(ci_dsnr[rk]["observed_crossing_valid"] and ci_dsnr[rk]["all_boot_crossings_valid"] for rk in primary_acc_rivals)
        and all(not ci_ber_hi[rk]["observed_zero_undecidable"] for rk in primary_acc_rivals)
        and np.isfinite(max_spd_lhw)
        and np.isfinite(max_ab_ratio_lhw)
        and np.isfinite(max_share_hw)
        and np.isfinite(max_dsnr_hw)
        and np.isfinite(max_ber_hi_lhw)
        and (max_spd_lhw <= cap_10x)
        and (ci_a_ratio["512"]["log_halfwidth"] <= cap_5x)
        and (ci_a_ratio["256"]["log_halfwidth"] <= cap_3x)
        and all(ci_b_ratio[k]["log_halfwidth"] <= cap_5x for k in ("64", "256", "512"))
        and (max_share_hw <= cap_share)
        and (max_dsnr_hw <= cap_dsnr)
        and (max_ber_hi_lhw <= cap_115x)
    )

    v_speedup = bool(min_spd_low >= 10.0)
    v_accuracy = bool(
        all((ci_dsnr[rk]["ci95"][1] <= 0.20) and (ci_ber_hi[rk]["ci95"][1] <= 1.15) for rk in primary_acc_rivals)
    )
    v_ablation = bool(
        (ci_a_ratio["512"]["ci95"][0] >= 5.0)
        and (ci_a_ratio["256"]["ci95"][0] >= 3.0)
        and all(ci_b_ratio[k]["ci95"][0] >= 5.0 for k in ("64", "256", "512"))
        and all_shares_valid
        and (max_share_ci_high < 0.80)
    )

    pass_primary = bool((not args.smoke) and v_redline1 and v_ci_precision and v_speedup and v_accuracy and v_ablation)

    diag_fail_summary = {
        "any_diagnostic_failed": bool(
            (rl1_exc is not None)
            or (diag_isolated.get("diagnostic_exception") is not None)
            or (diag_isolated.get("fig2_l123_exception") is not None)
            or (diag_isolated.get("small_N64_exception") is not None)
            or (cal_exc is not None)
            or any(v["failed_frames"] > 0 for v in desc_acc["diagnostic_failures"].values())
        ),
        "redline1_exception": rl1_exc,
        "isolated_diagnostics_exception": diag_isolated.get("diagnostic_exception"),
        "fig2_l123_exception": diag_isolated.get("fig2_l123_exception"),
        "small_N64_exception": diag_isolated.get("small_N64_exception"),
        "offline_fixed_cal_exception": cal_exc,
        "acc_descriptive_failed_frames": {
            dak: v["failed_frames"] for dak, v in desc_acc["diagnostic_failures"].items()
        },
        "acc_descriptive_exceptions": {
            dak: v["exceptions"] for dak, v in desc_acc["diagnostic_failures"].items()
        },
    }

    summary = {
        "_argv": list(sys.argv),
        "_config": {
            "smoke": bool(args.smoke),
            "workers": w_cnt,
            "formal_speed_counts": FORMAL_SPEED_COUNTS,
            "formal_n_acc_256": FORMAL_N_ACC_256,
            "speed_seed_bases": SPEED_SEED_BASES,
            "speed_probe_offset": SPEED_PROBE_OFFSET,
            "acc_seed_base": ACC_SEED_BASE,
            "acc_probe_seed_base": ACC_PROBE_SEED_BASE,
            "position_balance_exact_ok": position_balance_exact_ok,
            "caps": {
                "ratio_10x_5x_3x_log_halfwidth": cap_10x,
                "ber_115x_log_halfwidth": cap_115x,
                "dsnr_02db_halfwidth": cap_dsnr,
                "share_80pct_halfwidth": cap_share,
            },
        },
        "card_id": "I-20261125-g02",
        "group": "[放宽TWC]",
        "track": "[轨A-纯通信]",
        "smoke": bool(args.smoke),
        "wall_time_s": float(time.time() - t_start),
        "redline1": rl1,
        "diagnostic_failure_summary": diag_fail_summary,
        "isolated_diagnostics": diag_isolated,
        "offline_calibrated_fixed": {"k_fix": k_fix_star, "w_fix": list(w_fix_tup) if (w_fix_tup is not None) else None},
        "speed_scaling_N64_to_512": speed_metrics,
        "ablation_speedups_and_shares": {
            "A_only_over_Prop_ratios": ci_a_ratio,
            "B_only_over_Prop_ratios": ci_b_ratio,
            "log_speedup_shares_vs_MaoSPD": log_shares_spd,
            "log_speedup_shares_vs_PaperExactMao26": log_shares_raw,
            "descriptive_linear_time_saved_shares_vs_MaoSPD": desc_lin_time_saved_shares_spd,
        },
        "accuracy_curve_N256": {
            "snrs_EbN0_dB": snrs_eb,
            "n_frames": len(ac_res),
            "bits_per_snr_point": tot_bits_pt,
            "MC_BER_curves": mc_ber_curves,
            "paired_ci95_checks": {
                "Delta_SNR_dB_at_3e3_Prop_minus_Rival": ci_dsnr,
                "BER_16_19dB_Prop_over_Rival": ci_ber_hi,
            },
            "descriptive_diagnostics": desc_acc,
        },
        "ci_precision_check": {
            "position_balance_exact_ok": position_balance_exact_ok,
            "max_speed_log_halfwidth": max_spd_lhw,
            "max_ab_ratio_log_halfwidth": max_ab_ratio_lhw,
            "max_share_halfwidth": max_share_hw,
            "max_dsnr_3e3_halfwidth_dB": max_dsnr_hw,
            "max_ber_16_19_log_halfwidth": max_ber_hi_lhw,
        },
        "verdicts": {
            "PASS_REDLINE1": bool(v_redline1),
            "PASS_CI_PRECISION_25PCT": v_ci_precision,
            "PASS_SPEEDUP_10X": v_speedup,
            "PASS_ACCURACY_02DB": v_accuracy,
            "PASS_ABLATION_AB": v_ablation,
            "PASS_PRIMARY": pass_primary,
        },
    }
    with open(args.out, "w") as f:
        json.dump(_json_safe(summary), f, indent=2, allow_nan=False)
    print(json.dumps(summary["verdicts"], indent=2), flush=True)
    print("Saved summary to", args.out, "in", round(summary["wall_time_s"], 2), "s", flush=True)


if __name__ == "__main__":
    main()
