import sys
print(sys.executable, flush=True)

import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scipy.linalg import cholesky_banded, cho_solve_banded, solve_banded
from scipy.special import erfc
from scipy.stats import t as sp_t

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

def build_sparse_and_psi_diags(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2):
    # Identical sparse-diagonal assembly shared across ALL selector arms (FairSparse_Mao26, CoarseFine, A_only, B_only, Proposed, Fixed, c1_zero)
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

    deltas = list(diag_map.keys())
    psi_diags = np.zeros((d_band, N), dtype=complex)
    psi_diags[0, :] = sigma2
    for d1 in deltas:
        v1c = np.conj(diag_map[d1])
        for d2 in deltas:
            diff_d = (d1 - d2) % N
            if diff_d < d_band:
                psi_diags[diff_d, :] += v1c * diag_map[d2][(q + diff_d) % N]
    return diag_map, psi_diags

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

def solve_cyclic_diags(N, psi_diags, d_band, RHS, require_spd=False):
    # Fully vectorized cyclic-banded Cholesky + Schur complement solver (with LU fallback when require_spd=False)
    bw = d_band - 1
    q = np.arange(N)
    if 2 * bw + 2 >= N:
        Psi = np.zeros((N, N), dtype=complex)
        for d in range(d_band):
            cN = (q + d) % N
            Psi[q, cN] = psi_diags[d]
            if d > 0:
                Psi[cN, q] = np.conj(psi_diags[d])
        spd = True
        try:
            np.linalg.cholesky(Psi)
        except np.linalg.LinAlgError:
            spd = False
            if require_spd:
                return None, False
        return np.linalg.solve(Psi, RHS), spd

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

    comb = np.hstack([A12, RHS[:n1]])
    spd = True
    try:
        cb1 = cholesky_banded(ab1, lower=False)
        sol = cho_solve_banded((cb1, False), comb)
    except np.linalg.LinAlgError:
        spd = False
        if require_spd:
            return None, False
        ab_lu = np.zeros((2 * bw + 1, n1), dtype=complex)
        ab_lu[bw, :] = psi_diags[0, :n1]
        for d in range(1, d_band):
            ab_lu[bw - d, d:] = psi_diags[d, : n1 - d]
            ab_lu[bw + d, : n1 - d] = np.conj(psi_diags[d, : n1 - d])
        sol = solve_banded((bw, bw), ab_lu, comb)

    Z12, Y1 = sol[:, :bw], sol[:, bw:]
    S22 = M22 - A12.conj().T @ Z12
    if spd:
        try:
            np.linalg.cholesky(S22)
        except np.linalg.LinAlgError:
            spd = False
            if require_spd:
                return None, False
    X2 = np.linalg.solve(S22, RHS[n1:] - A12.conj().T @ Y1)
    return np.vstack([Y1 - Z12 @ X2, X2]), spd

def eval_exact_pa_sparse(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, H_full, require_spd=False):
    q = np.arange(N)
    diag_map, psi_diags = build_sparse_and_psi_diags(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2)
    HspH_Hf = np.zeros((N, N), dtype=complex)
    HspH = np.zeros((N, N), dtype=complex)
    for dlt, vq in diag_map.items():
        vc = np.conj(vq)
        rows = (q + dlt) % N
        HspH_Hf += vc[:, None] * H_full[rows, :]
        HspH[q, rows] = vc
    RHS = np.hstack([HspH_Hf, HspH])
    SOL, spd = solve_cyclic_diags(N, psi_diags, d_band, RHS, require_spd=require_spd)
    if SOL is None:
        return 1e30, False
    W_H, W_mat = SOL[:, :N], SOL[:, N:]
    sig_pow = np.abs(np.diag(W_H)) ** 2
    tot_pow = np.sum(np.abs(W_H) ** 2, axis=1)
    n_pow = sigma2 * np.sum(np.abs(W_mat) ** 2, axis=1)
    sinr_k = sig_pow / np.maximum(tot_pow - sig_pow + n_pow, 1e-12)
    qv = 0.5 * erfc(np.sqrt(sinr_k / 2.0))
    return float(np.mean(qv - qv ** 2)), spd

def eval_hutchinson_pa(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Z_rad, HZ_cache, require_spd=True):
    q = np.arange(N)
    diag_map, psi_diags = build_sparse_and_psi_diags(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2)
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
    R_full = np.zeros_like(comb_in)
    for dlt, vq in diag_map.items():
        R_full += np.conj(vq)[:, None] * comb_in[(q + dlt) % N, :]
    X_all, spd = solve_cyclic_diags(N, psi_diags, d_band, R_full, require_spd=require_spd)
    if X_all is None:
        return 1e30, False
    WHZ, WZ = X_all[:, :K_h], X_all[:, K_h:]
    diag_WH = np.mean(WHZ * np.conj(Z_rad), axis=1)
    tot_pow = np.mean(np.abs(WHZ) ** 2, axis=1)
    sig_pow = np.minimum(np.abs(diag_WH) ** 2, 0.999 * tot_pow)
    n_pow = sigma2 * np.mean(np.abs(WZ) ** 2, axis=1)
    sinr_k = sig_pow / np.maximum(tot_pow - sig_pow + n_pow, 1e-12)
    qv = 0.5 * erfc(np.sqrt(sinr_k / 2.0))
    return float(np.mean(qv - qv ** 2)), spd

def mao26_eq45_inits(N, k_r, l_arr, alpha_arr, d_band, ws):
    P = len(l_arr)
    xis = [(int(alpha_arr[i]) + k_r * int(l_arr[i])) % N for i in range(P)]
    sep = (xis[-1] - xis[0]) % N
    sep_cyc = min(sep, N - sep)
    w1p = int(np.clip(d_band - sep_cyc, 2, ws - max(P - 2, 0)))
    cands = []
    w1_list = np.unique(np.linspace(1, max(1, w1p - 1), min(3, max(1, w1p - 1)), dtype=int))
    for w1 in w1_list:
        wP = max(1, w1p - int(w1))
        rem = max(0, ws - int(w1) - wP)
        w = np.zeros(P, dtype=int)
        w[0], w[-1] = int(w1), wP
        if P > 2:
            for mi in range(1, P - 1):
                w[mi] = rem // (P - 2)
            w[1] += rem - int(np.sum(w[1:-1]))
        else:
            w[0] += rem
        if int(np.sum(w)) == ws:
            cands.append(w)
    uw = np.full(P, ws // P, dtype=int)
    uw[0] += ws - int(np.sum(uw))
    cands.append(uw)
    uniq, seen = [], set()
    for c in cands:
        t = tuple(c.tolist())
        if t not in seen:
            seen.add(t)
            uniq.append(c)
    return uniq[:3]

def band_coupled_wf_seed(N, k_r, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws):
    # Closed-form DAFT Dirichlet marginal lobe energy water-filling coupled to outer cross-Gram non-chopping w_0 + w_{P-1} <= (d_band - 1) - sep_{0, P-1}(k_r)
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
    if P >= 3 and sep_cyc < bw:
        pair_cap = max(0, bw - sep_cyc)
        w_bc = np.zeros(P, dtype=int)
        for _ in range(ws):
            feas = list(range(1, P - 1)) if (w_bc[0] + w_bc[-1] >= pair_cap) else list(range(P))
            b = feas[int(np.argmax([marg[i, w_bc[i]] for i in feas]))]
            w_bc[b] += 1
        return w_bc, w_u
    return w_u.copy(), w_u

def run_fair_mao26(N, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, iter_max=15, step_k=1):
    P = len(l_arr)
    c2 = 1.0 / (2.0 * N)
    span_l = max(int(np.max(l_arr) - np.min(l_arr)), 1)
    r_max = min(max(d_band // span_l, 1), N // (2 * span_l))
    k_list = list(range(1, r_max + 1, step_k))
    best_pa, best_k, best_w = 1e30, 1, np.zeros(P, dtype=int)
    Hf_cache = {}
    non_spd, tot_eval = 0, 0

    def _search_k(kr):
        nonlocal best_pa, best_k, best_w, non_spd, tot_eval
        if kr not in Hf_cache:
            Hf_cache[kr] = build_H_full_fast(N, kr, c2, l_arr, alpha_arr, beta_arr, h_arr)
        Hf = Hf_cache[kr]
        memo = {}
        def _sc(wv):
            nonlocal non_spd, tot_eval
            tk = tuple(wv.tolist())
            if tk not in memo:
                pa_v, spd_v = eval_exact_pa_sparse(N, kr, wv, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Hf)
                tot_eval += 1
                if not spd_v:
                    non_spd += 1
                memo[tk] = pa_v
            return memo[tk]

        kb = 1e30
        for w0 in mao26_eq45_inits(N, kr, l_arr, alpha_arr, d_band, ws):
            wc = w0.copy()
            pc = _sc(wc)
            for _ in range(iter_max):
                imp = False
                for i in range(P):
                    for j in range(P):
                        if i == j or wc[j] < 1:
                            continue
                        wn = wc.copy(); wn[i] += 1; wn[j] -= 1
                        pn = _sc(wn)
                        if pn < pc - 1e-9:
                            wc, pc, imp = wn, pn, True
                if not imp:
                    break
            if pc < kb:
                kb = pc
            if pc < best_pa:
                best_pa, best_k, best_w = pc, kr, wc.copy()
        return kb

    if step_k == 1:
        for kr in k_list:
            _search_k(kr)
    else:
        cs = sorted([(kr, _search_k(kr)) for kr in k_list], key=lambda x: x[1])
        tk = cs[0][0]
        for kr in range(max(1, tk - step_k), min(r_max, tk + step_k) + 1):
            if kr not in k_list:
                _search_k(kr)
    return best_k, best_w, non_spd, tot_eval

def run_a_only_wf_exact(N, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2):
    # Mechanism A alone: Band-coupled Dirichlet water-filling widths + exact 2N-column banded evaluator (identical SPD-first early-rejection + fallback)
    P = len(l_arr)
    c2 = 1.0 / (2.0 * N)
    span_l = max(int(np.max(l_arr) - np.min(l_arr)), 1)
    r_max = min(max(d_band // span_l, 1), N // (2 * span_l))
    best_pa, best_k, best_w = 1e30, 1, np.zeros(P, dtype=int)
    Hf_cache = {}
    w_u_ref = None
    for kr in range(1, r_max + 1):
        w_bc, w_u = band_coupled_wf_seed(N, kr, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws)
        w_u_ref = w_u
        Hf_cache[kr] = build_H_full_fast(N, kr, c2, l_arr, alpha_arr, beta_arr, h_arr)
        pa, spd = eval_exact_pa_sparse(N, kr, w_bc, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Hf_cache[kr], require_spd=True)
        if spd and pa < best_pa:
            best_pa, best_k, best_w = pa, kr, w_bc.copy()
    if best_pa < 1e29 and (not np.array_equal(best_w, w_u_ref)):
        pa_u, spd_u = eval_exact_pa_sparse(N, best_k, w_u_ref, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Hf_cache[best_k], require_spd=True)
        if spd_u and pa_u < best_pa:
            best_pa, best_w = pa_u, w_u_ref.copy()
    all_rej = 0
    if best_pa >= 1e29:
        all_rej = 1
        for kr in range(1, r_max + 1):
            w_bc, _ = band_coupled_wf_seed(N, kr, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws)
            pa, _ = eval_exact_pa_sparse(N, kr, w_bc, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Hf_cache[kr], require_spd=False)
            if pa < best_pa:
                best_pa, best_k, best_w = pa, kr, w_bc.copy()
    p_ord = np.argsort(np.abs(h_arr))[::-1]
    wc = best_w.copy()
    for (i, j) in [(int(p_ord[0]), int(p_ord[-1])), (int(p_ord[-1]), int(p_ord[0]))]:
        if i != j and wc[j] >= 1:
            wn = wc.copy(); wn[i] += 1; wn[j] -= 1
            pn, spdn = eval_exact_pa_sparse(N, best_k, wn, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Hf_cache[best_k], require_spd=(all_rej == 0))
            if ((all_rej == 1) or spdn) and (pn < best_pa - 1e-9):
                best_pa, best_w, wc = pn, wn.copy(), wn.copy()
    return best_k, best_w

def run_b_only_hutch_hillclimb(N, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, rng_h):
    # Mechanism B alone: Unit-modulus QPSK Hutchinson plugged into Mao26's multi-init hill-climbing (identical SPD-first early-rejection + fallback)
    P = len(l_arr)
    c2 = 1.0 / (2.0 * N)
    span_l = max(int(np.max(l_arr) - np.min(l_arr)), 1)
    r_max = min(max(d_band // span_l, 1), N // (2 * span_l))
    K_h = 24 if N <= 64 else 48
    qpsk_rad = np.exp(1j * (np.pi / 4.0 + (np.pi / 2.0) * rng_h.integers(0, 4, size=(N, K_h))))
    HZ_cache = {}
    best_pa, best_k, best_w = 1e30, 1, np.zeros(P, dtype=int)
    for req_s in (True, False):
        for kr in range(1, r_max + 1):
            memo = {}
            def _sc_h(wv):
                tk = tuple(wv.tolist())
                if tk not in memo:
                    memo[tk] = eval_hutchinson_pa(N, kr, wv, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, qpsk_rad, HZ_cache, require_spd=req_s)[0]
                return memo[tk]
            for w0 in mao26_eq45_inits(N, kr, l_arr, alpha_arr, d_band, ws):
                wc = w0.copy()
                pc = _sc_h(wc)
                for _ in range(15):
                    imp = False
                    for i in range(P):
                        for j in range(P):
                            if i == j or wc[j] < 1:
                                continue
                            wn = wc.copy(); wn[i] += 1; wn[j] -= 1
                            pn = _sc_h(wn)
                            if pn < pc - 1e-6:
                                wc, pc, imp = wn, pn, True
                    if not imp:
                        break
                if pc < best_pa:
                    best_pa, best_k, best_w = pc, kr, wc.copy()
        if best_pa < 1e29:
            break
    return best_k, best_w

def run_proposed_fast_jcps(N, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, rng_h):
    # Single-Stage Band-Coupled Dirichlet Water-Filling + SPD-Gated Sparse-Diagonal QPSK Hutchinson
    P = len(l_arr)
    c2 = 1.0 / (2.0 * N)
    span_l = max(int(np.max(l_arr) - np.min(l_arr)), 1)
    r_max = min(max(d_band // span_l, 1), N // (2 * span_l))
    K_h = 24 if N <= 64 else 48
    qpsk_rad = np.exp(1j * (np.pi / 4.0 + (np.pi / 2.0) * rng_h.integers(0, 4, size=(N, K_h))))
    HZ_cache = {}
    best_pa, best_k, best_w = 1e30, 1, np.zeros(P, dtype=int)
    spd_rej, tot_chk, all_rej_fallback = 0, 0, 0
    w_u_ref = None

    for kr in range(1, r_max + 1):
        w_bc, w_u = band_coupled_wf_seed(N, kr, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws)
        w_u_ref = w_u
        pa, spd = eval_hutchinson_pa(N, kr, w_bc, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, qpsk_rad, HZ_cache, require_spd=True)
        tot_chk += 1
        if not spd:
            spd_rej += 1
        if pa < best_pa:
            best_pa, best_k, best_w = pa, kr, w_bc.copy()

    if best_pa < 1e29 and (not np.array_equal(best_w, w_u_ref)):
        pa_u, spd_u = eval_hutchinson_pa(N, best_k, w_u_ref, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, qpsk_rad, HZ_cache, require_spd=True)
        tot_chk += 1
        if not spd_u:
            spd_rej += 1
        if pa_u < best_pa:
            best_pa, best_w = pa_u, w_u_ref.copy()

    if best_pa >= 1e29:
        all_rej_fallback = 1
        for kr in range(1, r_max + 1):
            w_bc, _ = band_coupled_wf_seed(N, kr, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws)
            pa, _ = eval_hutchinson_pa(N, kr, w_bc, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, qpsk_rad, HZ_cache, require_spd=False)
            if pa < best_pa:
                best_pa, best_k, best_w = pa, kr, w_bc.copy()

    # Minimal 2-pair dominant/weakest swap polish on best_k ONLY (reuses cached HZ_cache[best_k]):
    p_ord = np.argsort(np.abs(h_arr))[::-1]
    wc = best_w.copy()
    for (i, j) in [(int(p_ord[0]), int(p_ord[-1])), (int(p_ord[-1]), int(p_ord[0]))]:
        if i != j and wc[j] >= 1:
            wn = wc.copy(); wn[i] += 1; wn[j] -= 1
            pn, spd_n = eval_hutchinson_pa(N, best_k, wn, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, qpsk_rad, HZ_cache, require_spd=(all_rej_fallback == 0))
            tot_chk += 1
            if not spd_n:
                spd_rej += 1
            if pn < best_pa - 1e-6:
                best_pa, best_w, wc = pn, wn.copy(), wn.copy()

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
    diag_map, psi_diags = build_sparse_and_psi_diags(N, k_c, w_vec, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2)
    MF = np.zeros_like(Y_daft)
    for dlt, vq in diag_map.items():
        MF += np.conj(vq)[:, None] * Y_daft[(q + dlt) % N, :]
    X_hat, _ = solve_cyclic_diags(N, psi_diags, d_band, MF, require_spd=False)
    b_re = (np.real(X_hat) < 0.0).astype(int)
    b_im = (np.imag(X_hat) < 0.0).astype(int)
    return int(np.sum(b_re != bits_true[0]) + np.sum(b_im != bits_true[1]))

def mc_ber_rule30_td_exact(N, k_c, c2, l_arr, alpha_arr, beta_arr, h_arr, sigma2, X_qpsk, bits_true, noise_td):
    # LESSONS Rule 30 exact time-domain cyclic-banded MMSE reference (descriptive reference ONLY per Group 2 rule!)
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
    # Deterministic calibration of best fixed (k_fix, w_fix) on 24 disjoint dev frames (seed 20261125)
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
        al = np.round(nu_raw).astype(int); be = nu_raw - al
        pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0); pows /= np.sum(pows)
        h_arr = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
        b0 = rng.integers(0, 2, size=(N, 8)); b1 = rng.integers(0, 2, size=(N, 8))
        Xq = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
        ntd = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((N, 8)) + 1j * rng.standard_normal((N, 8)))
        for ic, (kf, wf) in enumerate(cand_pairs):
            scores[ic] += mc_ber_lc_bmmse(N, kf, wf, c2, l_arr, al, be, h_arr, d_band, sigma2, Xq, (b0, b1), ntd)
    best_idx = int(np.argmin(scores))
    return cand_pairs[best_idx][0], cand_pairs[best_idx][1]

def verify_redline1_mao26():
    # 1) Noiseless integer-Doppler band-interior LC-BMMSE reconstruction (< 1e-12)
    rng = np.random.default_rng(960000)
    N = 256; c2 = 1.0 / (2.0 * N); l_arr = np.array([0, 2, 5]); al = np.array([-1, 0, 1]); be = np.zeros(3)
    h_arr = np.array([0.8 + 0.1j, -0.4 + 0.3j, 0.25 - 0.2j]); w0 = np.array([2, 2, 2]); k0 = 2; d_band = 17
    b0 = rng.integers(0, 2, size=(N, 2)); b1 = rng.integers(0, 2, size=(N, 2))
    Xq = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
    c1 = k0 / (2.0 * N); nv = np.arange(N)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (nv ** 2))[:, None]
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (nv ** 2))[:, None]
    X_td = np.conj(L1) * np.fft.ifft(np.conj(L2) * Xq, axis=0) * np.sqrt(N)
    Y_td = np.zeros_like(X_td)
    for i in range(3):
        Y_td += (h_arr[i] * np.exp(-1j * 2.0 * np.pi * al[i] * nv / N))[:, None] * X_td[(nv - int(l_arr[i])) % N, :]
    Y_daft = L2 * (np.fft.fft(L1 * Y_td, axis=0) / np.sqrt(N))
    dm, pd = build_sparse_and_psi_diags(N, k0, w0, c2, l_arr, al, be, h_arr, d_band, 1e-15)
    MF = np.zeros_like(Y_daft)
    for dlt, vq in dm.items():
        MF += np.conj(vq)[:, None] * Y_daft[(nv + dlt) % N, :]
    Xh, _ = solve_cyclic_diags(N, pd, d_band, MF, require_spd=False)
    rel_err_nl = float(np.linalg.norm(Xh - Xq) / np.linalg.norm(Xq))

    # 2) Exact full-period sparse-Gram identity (Mao26 Eq. (28), odd N=127 so w=63 covers exact period 2*63+1=127 without Nyquist double-count):
    be_f = np.array([0.23, -0.37, 0.14])
    Hf = build_H_full_fast(127, 3, 1.0 / 254.0, l_arr, al, be_f, h_arr)
    G_exact = Hf.conj().T @ Hf
    _, pd_full = build_sparse_and_psi_diags(127, 3, np.array([63, 63, 63]), 1.0 / 254.0, l_arr, al, be_f, h_arr, 64, 0.0)
    G_diag_err = float(np.linalg.norm(np.diag(G_exact) - pd_full[0]) / np.linalg.norm(np.diag(G_exact)))

    # 3) Mao26 Fig. 8 non-monotonic steep valley around optimal c1 at N=256, d_tilde=37 (d=19), ws=16, Eb/N0=15 dB, l=[0, 2, 6] (keeping c2 = 1/(2N) fixed):
    sigma2_fig8 = 10.0 ** (-(15.0 + 3.0103) / 10.0)
    ks_fig8 = [0, 1, 2, 3, 4]
    errs_fig8 = {kv: 0 for kv in ks_fig8}
    tot_fig8 = 0
    for _ in range(30):
        nu_r = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
        al8 = np.round(nu_r).astype(int); be8 = nu_r - al8
        pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0); pows /= np.sum(pows)
        h8 = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
        _, wu8 = band_coupled_wf_seed(256, 2, np.array([0, 2, 6]), al8, be8, h8, 19, 16)
        b0 = rng.integers(0, 2, size=(256, 8)); b1 = rng.integers(0, 2, size=(256, 8))
        Xq8 = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
        nt8 = np.sqrt(sigma2_fig8 / 2.0) * (rng.standard_normal((256, 8)) + 1j * rng.standard_normal((256, 8)))
        for kv in ks_fig8:
            errs_fig8[kv] += mc_ber_lc_bmmse(256, kv, wu8, 1.0 / 512.0, np.array([0, 2, 6]), al8, be8, h8, 19, sigma2_fig8, Xq8, (b0, b1), nt8)
        tot_fig8 += 2 * 256 * 8
    fig8_curve = {f"k={kv}": errs_fig8[kv] / tot_fig8 for kv in ks_fig8}
    opt_fig8 = min(errs_fig8[1], errs_fig8[2], errs_fig8[3]) / tot_fig8

    # 4) Small-N (N=64) optimality check vs exhaustive search over ALL non-negative (k_r, w) with w_i >= 0, sum w_i == 16 & matching SPD-first/fallback rule:
    exh_gap_pa = []
    for tr_e in range(10):
        rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
        le = np.array([0, int(rem_l[0]), int(rem_l[1])])
        nu_e = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
        ale = np.round(nu_e).astype(int); bee = nu_e - ale
        pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0); pows /= np.sum(pows)
        he = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
        s2e = 10.0 ** (-(16.0 + 3.0103) / 10.0)
        rm_e = min(max(17 // int(le[-1] - le[0]), 1), 64 // (2 * int(le[-1] - le[0])))
        best_exh_spd, best_exh_any = 1e30, 1e30
        for kre in range(1, rm_e + 1):
            Hfe = build_H_full_fast(64, kre, 1.0 / 128.0, le, ale, bee, he)
            for w1 in range(0, 17):
                for w2 in range(0, 17 - w1):
                    w3 = 16 - w1 - w2
                    pae, spde = eval_exact_pa_sparse(64, kre, np.array([w1, w2, w3]), 1.0 / 128.0, le, ale, bee, he, 17, s2e, Hfe)
                    if pae < best_exh_any:
                        best_exh_any = pae
                    if spde and pae < best_exh_spd:
                        best_exh_spd = pae
        best_exh = best_exh_spd if (best_exh_spd < 1e29) else best_exh_any
        kp_e, wp_e, _, _, _ = run_proposed_fast_jcps(64, le, ale, bee, he, 17, 16, s2e, np.random.default_rng(965000 + tr_e))
        Hfp_e = build_H_full_fast(64, kp_e, 1.0 / 128.0, le, ale, bee, he)
        pap_e, _ = eval_exact_pa_sparse(64, kp_e, wp_e, 1.0 / 128.0, le, ale, bee, he, 17, s2e, Hfp_e)
        exh_gap_pa.append(pap_e / max(best_exh, 1e-9))

    return {
        "noiseless_lc_bmmse_rel_err": rel_err_nl,
        "fcda_gram_diag_rel_err": G_diag_err,
        "fig8_valley_mc_ber": fig8_curve,
        "fig8_opt_ber": opt_fig8,
        "small_N64_prop_over_exhaustive_pa_mean": float(np.mean(exh_gap_pa)),
    }

_WORKER_WARMED = False
def _ensure_warmup():
    global _WORKER_WARMED
    if not _WORKER_WARMED:
        l_w = np.array([0, 2, 5]); al_w = np.zeros(3, dtype=int); be_w = np.array([0.1, -0.1, 0.05]); h_w = np.array([0.8+0j, 0.4+0j, 0.2+0j])
        run_fair_mao26(64, l_w, al_w, be_w, h_w, 17, 16, 0.02, iter_max=2, step_k=1)
        run_proposed_fast_jcps(64, l_w, al_w, be_w, h_w, 17, 16, 0.02, np.random.default_rng(1))
        _WORKER_WARMED = True

def run_speed_trial(task_tuple):
    # Task: ("SPEED", N_v, tr_id) -> measures single-thread wall times across FairSparse_Mao26, CoarseFine, A_only, B_only, Proposed
    _, N_v, tr_id = task_tuple
    _ensure_warmup()
    seed_base = {64: 971000, 128: 973000, 256: 975000, 512: 977000}[N_v]
    rng = np.random.default_rng(seed_base + tr_id * 19)
    rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
    l_arr = np.array([0, int(rem_l[0]), int(rem_l[1])])
    nu_raw = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
    alpha_arr = np.round(nu_raw).astype(int)
    beta_arr = nu_raw - alpha_arr
    pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0); pows /= np.sum(pows)
    h_arr = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))
    sigma2 = 10.0 ** (-(16.0 + 3.0103) / 10.0)
    d_band = 17; ws = 16

    s0 = time.perf_counter()
    km, wm, nspd_m, tot_m = run_fair_mao26(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, iter_max=15, step_k=1)
    t_mao = time.perf_counter() - s0

    s0 = time.perf_counter()
    kcf, wcf, _, _ = run_fair_mao26(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, iter_max=15, step_k=2)
    t_cf = time.perf_counter() - s0

    t_a, t_b = 0.0, 0.0
    if N_v in (256, 512):
        s0 = time.perf_counter()
        run_a_only_wf_exact(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2)
        t_a = time.perf_counter() - s0
    if N_v == 64:
        rng_b = np.random.default_rng(seed_base + 50000 + tr_id)
        s0 = time.perf_counter()
        run_b_only_hutch_hillclimb(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, rng_b)
        t_b = time.perf_counter() - s0

    rng_p = np.random.default_rng(seed_base + 80000 + tr_id)
    s0 = time.perf_counter()
    kp, wp, spd_rej, tot_chk, all_rej = run_proposed_fast_jcps(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, rng_p)
    t_prop = time.perf_counter() - s0

    return {
        "kind": "SPEED",
        "N": N_v,
        "t_mao": t_mao,
        "t_cf": t_cf,
        "t_a": t_a,
        "t_b": t_b,
        "t_prop": t_prop,
        "mao_nonspd": nspd_m,
        "mao_evals": tot_m,
        "prop_spd_rej": spd_rej,
        "prop_evals": tot_chk,
        "prop_all_rej": all_rej,
    }

def run_acc_curve_trial(task_tuple):
    # Task: ("ACC256", tr_id, k_fix, w_fix_tuple) -> evaluates Fig. 10 SNR curve Eb/N0 in [10, 13, 16, 19] dB at Table II N=256
    _, tr_id, k_fix, w_fix_tup = task_tuple
    _ensure_warmup()
    w_fix = np.array(w_fix_tup, dtype=int)
    N_v = 256; d_band = 17; ws = 16; c2 = 1.0 / (2.0 * N_v); B_blk = 32
    snrs_eb = [10.0, 13.0, 16.0, 19.0]
    rng = np.random.default_rng(981000 + tr_id * 23)

    rem_l = np.sort(rng.choice(np.arange(1, 7), size=2, replace=False))
    l_arr = np.array([0, int(rem_l[0]), int(rem_l[1])])
    nu_raw = (4.17 / 15.0) * np.cos(rng.uniform(-np.pi, np.pi, size=3))
    alpha_arr = np.round(nu_raw).astype(int)
    beta_arr = nu_raw - alpha_arr
    pows = 10.0 ** (np.array([0.0, -4.675, -6.482]) / 10.0); pows /= np.sum(pows)
    h_arr = np.sqrt(pows / 2.0) * (rng.standard_normal(3) + 1j * rng.standard_normal(3))

    arms = ["mao26", "cf", "prop", "fixed", "c1_zero_same_c2", "rule30_td"]
    errs = {ak: [] for ak in arms}
    pa_19 = {}
    t_r30_ms = []

    for ig, eb_db in enumerate(snrs_eb):
        sigma2 = 10.0 ** (-(eb_db + 3.0103) / 10.0)
        km, wm, _, _ = run_fair_mao26(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, iter_max=15, step_k=1)
        kcf, wcf, _, _ = run_fair_mao26(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, iter_max=15, step_k=2)
        rng_p = np.random.default_rng(989000 + tr_id * 10 + ig)
        kp, wp, _, _, _ = run_proposed_fast_jcps(N_v, l_arr, alpha_arr, beta_arr, h_arr, d_band, ws, sigma2, rng_p)

        b0 = rng.integers(0, 2, size=(N_v, B_blk)); b1 = rng.integers(0, 2, size=(N_v, B_blk))
        Xq = ((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.0)
        ntd = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((N_v, B_blk)) + 1j * rng.standard_normal((N_v, B_blk)))

        errs["mao26"].append(mc_ber_lc_bmmse(N_v, km, wm, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        errs["cf"].append(mc_ber_lc_bmmse(N_v, kcf, wcf, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        errs["prop"].append(mc_ber_lc_bmmse(N_v, kp, wp, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        errs["fixed"].append(mc_ber_lc_bmmse(N_v, k_fix, w_fix, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        # Diagnostic c1 = 0 check keeping c2 = 1/(2N) fixed (purely descriptive per Group 2 rule, NOT an OFDM c1=c2=0 cross-waveform lock):
        errs["c1_zero_same_c2"].append(mc_ber_lc_bmmse(N_v, 0, wp, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Xq, (b0, b1), ntd))
        er30, dt30 = mc_ber_rule30_td_exact(N_v, kp, c2, l_arr, alpha_arr, beta_arr, h_arr, sigma2, Xq, (b0, b1), ntd)
        errs["rule30_td"].append(er30)
        t_r30_ms.append(1e3 * dt30 / B_blk)

        if ig == 3:
            Hfm = build_H_full_fast(N_v, km, c2, l_arr, alpha_arr, beta_arr, h_arr)
            Hfp = build_H_full_fast(N_v, kp, c2, l_arr, alpha_arr, beta_arr, h_arr)
            pa_19["mao26"] = eval_exact_pa_sparse(N_v, km, wm, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Hfm)[0]
            pa_19["prop"] = eval_exact_pa_sparse(N_v, kp, wp, c2, l_arr, alpha_arr, beta_arr, h_arr, d_band, sigma2, Hfp)[0]

    return {
        "kind": "ACC256",
        "bits_per_pt": 2 * N_v * B_blk,
        "errs": errs,
        "pa_19": pa_19,
        "rule30_per_block_ms": float(np.mean(t_r30_ms)),
    }

def paired_geom_ratio_t_ci95(t_num, t_den):
    lr = np.log(np.asarray(t_num, dtype=float) / np.asarray(t_den, dtype=float))
    M = len(lr)
    ml = float(np.mean(lr))
    if M < 2:
        return {"geom_ratio": float(np.exp(ml)), "ci95": [float(np.exp(ml)), float(np.exp(ml))], "log_halfwidth": 0.0}
    tc = float(sp_t.ppf(0.975, df=M - 1))
    hw = tc * float(np.std(lr, ddof=1)) / np.sqrt(M)
    return {"geom_ratio": float(np.exp(ml)), "ci95": [float(np.exp(ml - hw)), float(np.exp(ml + hw))], "log_halfwidth": hw}

def paired_ber_ratio_boot_ci95(err_num_arr, err_den_arr, bits_per_frame, upper_mode=False, n_boot=4000, seed=20261125):
    en = np.asarray(err_num_arr, dtype=float)
    ed = np.asarray(err_den_arr, dtype=float)
    M = len(en)
    z_guard = -np.log(0.025) * float(bits_per_frame)
    s_n, s_d = float(np.sum(en)), float(np.sum(ed))
    if upper_mode:
        pt = (s_n / s_d) if s_d > 0.0 else (float("inf") if s_n > 0.0 else 1.0)
    else:
        pt = (s_n / s_d) if s_d > 0.0 else (s_n / z_guard)
    if M < 2:
        return {"point": pt, "ci95": [pt, pt], "log_halfwidth": 0.0}
    rb = np.random.default_rng(seed)
    idx = rb.integers(0, M, size=(n_boot, M))
    sn = np.sum(en[idx], axis=1)
    sd = np.sum(ed[idx], axis=1)
    if upper_mode:
        sn_up = np.where(sn > 0.0, sn, z_guard)
        rat = np.where(sd > 0.0, sn_up / np.where(sd > 0.0, sd, 1.0), np.inf)
    else:
        sd_safe = np.where(sd > 0.0, sd, z_guard)
        rat = np.where(sn > 0.0, sn / sd_safe, 0.0)
    sr = np.sort(rat)
    lo = float(sr[int(np.floor(0.025 * (n_boot - 1)))])
    hi = float(sr[int(np.ceil(0.975 * (n_boot - 1)))])
    lhw = 0.5 * float(np.log(hi / lo)) if (np.isfinite(hi) and lo > 0.0) else float("inf")
    return {"point": pt, "ci95": [lo, hi], "log_halfwidth": lhw}

def snr_at_target_strict(snrs, bers, target=3.0e-3):
    lb = np.log10(np.maximum(bers, 1e-9))
    lt = np.log10(target)
    for idx in range(len(snrs) - 1):
        if lb[idx] >= lt >= lb[idx + 1]:
            denom = lb[idx] - lb[idx + 1]
            frac = (lb[idx] - lt) / denom if denom > 1e-12 else 0.0
            return float(snrs[idx] + frac * (snrs[idx + 1] - snrs[idx])), True
    return float("nan"), False

def paired_delta_snr_ci95(err_prop_mat, err_mao_mat, bits_per_frame, snrs, target=3.0e-3, n_boot=4000, seed=20261125):
    M = err_prop_mat.shape[0]
    tot_b = float(M * bits_per_frame)
    sp_pt, ok_p = snr_at_target_strict(snrs, np.sum(err_prop_mat, axis=0) / tot_b, target)
    sm_pt, ok_m = snr_at_target_strict(snrs, np.sum(err_mao_mat, axis=0) / tot_b, target)
    pt = (sp_pt - sm_pt) if (ok_p and ok_m) else float("inf")
    if M < 2:
        return {"point": pt, "ci95": [pt, pt], "halfwidth": 0.0}
    rb = np.random.default_rng(seed)
    diffs = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        ix = rb.integers(0, M, size=M)
        sp_b, ok_pb = snr_at_target_strict(snrs, np.sum(err_prop_mat[ix], axis=0) / tot_b, target)
        sm_b, ok_mb = snr_at_target_strict(snrs, np.sum(err_mao_mat[ix], axis=0) / tot_b, target)
        # Order-statistic quantiles preserve +inf cleanly without inf - inf -> NaN interpolation
        diffs[b] = (sp_b - sm_b) if (ok_pb and ok_mb) else np.inf
    sd = np.sort(diffs)
    lo = float(sd[int(np.floor(0.025 * (n_boot - 1)))])
    hi = float(sd[int(np.ceil(0.975 * (n_boot - 1)))])
    hw = 0.5 * (hi - lo) if (np.isfinite(lo) and np.isfinite(hi)) else float("inf")
    return {"point": pt, "ci95": [lo, hi], "halfwidth": hw}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="summary_g_r11_g02.json")
    args = ap.parse_args()

    t_start = time.time()
    rl1 = verify_redline1_mao26()
    print("[Red-Line 1]", json.dumps(rl1), flush=True)

    v_redline1 = (
        (rl1["noiseless_lc_bmmse_rel_err"] < 1e-12)
        and (rl1["fcda_gram_diag_rel_err"] < 1e-12)
        and (rl1["fig8_opt_ber"] < rl1["fig8_valley_mc_ber"]["k=0"])
        and (rl1["fig8_opt_ber"] < rl1["fig8_valley_mc_ber"]["k=4"])
    )
    if not v_redline1:
        fail_s = {"card_id": "I-20261125-g02", "smoke": args.smoke, "redline1": rl1, "verdicts": {"PASS_REDLINE1": False, "PASS_PRIMARY": False}}
        with open(args.out, "w") as f:
            json.dump(fail_s, f, indent=2)
        raise RuntimeError(f"Red-Line 1 failed: {rl1}")

    k_fix_star, w_fix_star = calibrate_offline_best_fixed(256, 17, 16)
    w_fix_tup = tuple(int(x) for x in w_fix_star.tolist())

    speed_counts = {64: 2, 128: 2, 256: 2, 512: 2} if args.smoke else {64: 100, 128: 80, 256: 80, 512: 60}
    n_acc_256 = 2 if args.smoke else 200

    speed_tasks = [("SPEED", nv, tr) for nv, cnt in speed_counts.items() for tr in range(cnt)]
    acc_tasks = [("ACC256", tr, k_fix_star, w_fix_tup) for tr in range(n_acc_256)]

    if args.smoke or args.workers <= 1:
        sp_res = [run_speed_trial(t) for t in speed_tasks]
        ac_res = [run_acc_curve_trial(t) for t in acc_tasks]
    else:
        w_cnt = min(args.workers, 8)
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            sp_res = list(ex.map(run_speed_trial, speed_tasks))
            ac_res = list(ex.map(run_acc_curve_trial, acc_tasks))

    # Aggregate speed results across N = 64, 128, 256, 512
    sp_by_n = {nv: [] for nv in [64, 128, 256, 512]}
    for r in sp_res:
        sp_by_n[r["N"]].append(r)

    speed_metrics = {}
    ci_spd_mao = {}
    ci_spd_cf = {}
    for nv in [64, 128, 256, 512]:
        rl = sp_by_n[nv]
        tm = [x["t_mao"] for x in rl]
        tcf = [x["t_cf"] for x in rl]
        tp = [x["t_prop"] for x in rl]
        ci_m = paired_geom_ratio_t_ci95(tm, tp)
        ci_c = paired_geom_ratio_t_ci95(tcf, tp)
        ci_spd_mao[str(nv)] = ci_m
        ci_spd_cf[str(nv)] = ci_c
        speed_metrics[str(nv)] = {
            "n_frames": len(rl),
            "mean_mao26_ms": float(1e3 * np.mean(tm)),
            "mean_cf_ms": float(1e3 * np.mean(tcf)),
            "mean_prop_ms": float(1e3 * np.mean(tp)),
            "arith_speedup_vs_mao26": float(np.mean(tm) / np.mean(tp)),
            "arith_speedup_vs_cf": float(np.mean(tcf) / np.mean(tp)),
            "geom_speedup_vs_mao26_ci95": ci_m,
            "geom_speedup_vs_cf_ci95": ci_c,
            "mao26_nonspd_rate": float(sum(x["mao_nonspd"] for x in rl) / max(sum(x["mao_evals"] for x in rl), 1)),
            "prop_spd_reject_rate": float(sum(x["prop_spd_rej"] for x in rl) / max(sum(x["prop_evals"] for x in rl), 1)),
            "prop_all_rejected_frames": int(sum(x["prop_all_rej"] for x in rl)),
        }

    ci_a_only_256 = paired_geom_ratio_t_ci95([x["t_a"] for x in sp_by_n[256]], [x["t_prop"] for x in sp_by_n[256]])
    ci_a_only_512 = paired_geom_ratio_t_ci95([x["t_a"] for x in sp_by_n[512]], [x["t_prop"] for x in sp_by_n[512]])
    ci_b_only_64 = paired_geom_ratio_t_ci95([x["t_b"] for x in sp_by_n[64]], [x["t_prop"] for x in sp_by_n[64]])

    # Aggregate N=256 Fig. 10 accuracy curve results
    snrs_eb = [10.0, 13.0, 16.0, 19.0]
    bpf = ac_res[0]["bits_per_pt"]
    arms = ["mao26", "cf", "prop", "fixed", "c1_zero_same_c2", "rule30_td"]
    err_mats = {ak: np.array([r["errs"][ak] for r in ac_res], dtype=float) for ak in arms}
    tot_bits_pt = len(ac_res) * bpf
    mc_ber_curves = {ak: [float(x) for x in (np.sum(err_mats[ak], axis=0) / tot_bits_pt)] for ak in arms}

    ci_dsnr_3e3 = paired_delta_snr_ci95(err_mats["prop"], err_mats["mao26"], bpf, snrs_eb, target=3.0e-3, seed=20261170)
    # High-SNR regime (Eb/N0 in {16, 19} dB, 2 * bpf bits/frame) paired BER ratio against FairSparse_Mao26:
    ci_ber_hi_prop_over_mao = paired_ber_ratio_boot_ci95(
        np.sum(err_mats["prop"][:, 2:], axis=1),
        np.sum(err_mats["mao26"][:, 2:], axis=1),
        2 * bpf,
        upper_mode=True,
        seed=20261171,
    )
    # Descriptive diagnostics ONLY (FixedOffline_Best, c1=0 with same c2, Rule 30 TD exact):
    ci_desc_fix_over_prop_19 = paired_ber_ratio_boot_ci95(err_mats["fixed"][:, 3], err_mats["prop"][:, 3], bpf, upper_mode=False, seed=20261172)
    ci_desc_c1zero_over_prop_19 = paired_ber_ratio_boot_ci95(err_mats["c1_zero_same_c2"][:, 3], err_mats["prop"][:, 3], bpf, upper_mode=False, seed=20261173)

    min_spd_mao_low = min(ci_spd_mao[str(nv)]["ci95"][0] for nv in [64, 128, 256, 512])
    min_spd_cf_low = min(ci_spd_cf[str(nv)]["ci95"][0] for nv in [64, 128, 256, 512])
    max_spd_lhw = max(
        max(ci_spd_mao[str(nv)]["log_halfwidth"] for nv in [64, 128, 256, 512]),
        max(ci_spd_cf[str(nv)]["log_halfwidth"] for nv in [64, 128, 256, 512]),
    )

    # Red Line 5: verify EVERY primary criterion's realized 95% CI half-width <= 25% of its threshold distance!
    v_ci_precision = (
        (max_spd_lhw <= 0.25 * np.log(10.0))
        and (ci_dsnr_3e3["halfwidth"] <= 0.25 * 0.20)
        and (ci_ber_hi_prop_over_mao["log_halfwidth"] <= 0.25 * np.log(1.15))
        and (ci_a_only_512["log_halfwidth"] <= 0.25 * np.log(5.0))
        and (ci_a_only_256["log_halfwidth"] <= 0.25 * np.log(3.0))
        and (ci_b_only_64["log_halfwidth"] <= 0.25 * np.log(5.0))
    )

    v_speedup = (min_spd_mao_low >= 10.0) and (min_spd_cf_low >= 10.0)
    v_accuracy = (ci_dsnr_3e3["ci95"][1] <= 0.20) and (ci_ber_hi_prop_over_mao["ci95"][1] <= 1.15)
    v_ablation = (
        (ci_a_only_512["ci95"][0] >= 5.0)
        and (ci_a_only_256["ci95"][0] >= 3.0)
        and (ci_b_only_64["ci95"][0] >= 5.0)
    )

    pass_primary = bool((not args.smoke) and v_redline1 and v_ci_precision and v_speedup and v_accuracy and v_ablation)

    summary = {
        "card_id": "I-20261125-g02",
        "group": "[放宽TWC]",
        "track": "[轨A-纯通信]",
        "smoke": args.smoke,
        "wall_time_s": float(time.time() - t_start),
        "redline1": rl1,
        "offline_calibrated_fixed": {"k_fix": k_fix_star, "w_fix": list(w_fix_tup)},
        "speed_scaling_N64_to_512": speed_metrics,
        "ablation_speedups": {
            "A_only_WF_Exact_over_Prop_N256": ci_a_only_256,
            "A_only_WF_Exact_over_Prop_N512": ci_a_only_512,
            "B_only_Hutch_HillClimb_over_Prop_N64": ci_b_only_64,
        },
        "accuracy_curve_N256": {
            "snrs_EbN0_dB": snrs_eb,
            "n_frames": len(ac_res),
            "bits_per_snr_point": tot_bits_pt,
            "MC_BER_curves": mc_ber_curves,
            "mean_PA_19dB": {
                "mao26": float(np.mean([r["pa_19"]["mao26"] for r in ac_res])),
                "prop": float(np.mean([r["pa_19"]["prop"] for r in ac_res])),
            },
            "paired_ci95_checks": {
                "Delta_SNR_dB_at_3e3_Prop_minus_Mao": ci_dsnr_3e3,
                "BER_16_19dB_Prop_over_Mao": ci_ber_hi_prop_over_mao,
            },
            "descriptive_diagnostics": {
                "rule30_td_per_block_ms": float(np.mean([r["rule30_per_block_ms"] for r in ac_res])),
                "BER19dB_FixedOffline_over_Prop": ci_desc_fix_over_prop_19,
                "BER19dB_c1zero_same_c2_over_Prop": ci_desc_c1zero_over_prop_19,
            },
        },
        "ci_precision_check": {
            "max_speed_log_halfwidth": max_spd_lhw,
            "dsnr_3e3_halfwidth_dB": ci_dsnr_3e3["halfwidth"],
            "ber_16_19_prop_mao_log_halfwidth": ci_ber_hi_prop_over_mao["log_halfwidth"],
        },
        "verdicts": {
            "PASS_REDLINE1": bool(v_redline1),
            "PASS_CI_PRECISION_25PCT": bool(v_ci_precision),
            "PASS_SPEEDUP_10X": bool(v_speedup),
            "PASS_ACCURACY_02DB": bool(v_accuracy),
            "PASS_ABLATION_AB": bool(v_ablation),
            "PASS_PRIMARY": pass_primary,
        },
    }
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary["verdicts"], indent=2), flush=True)
    print("Saved summary to", args.out, "in", round(summary["wall_time_s"], 2), "s", flush=True)

if __name__ == "__main__":
    main()
