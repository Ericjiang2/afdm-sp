import os, sys, json, time, math
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

import numpy as np
from scipy.linalg import solveh_banded, solve_banded, eig_banded
from multiprocessing import Pool

# ==========================================================
# Core AFDM / OFDM Non-Wrapping Physical CPP & Banded Solvers
# ==========================================================
def daft_matrix(N, c1, c2):
    n = np.arange(N)
    L1 = np.exp(-1j * 2 * np.pi * c1 * (n ** 2))
    L2 = np.exp(-1j * 2 * np.pi * c2 * (n ** 2))
    F = np.exp(-1j * 2 * np.pi * n[:, None] * n[None, :] / N) / np.sqrt(N)
    return (L2[:, None] * F) * L1[None, :]

def build_cpp_ext(N, c1, L_cpp):
    B = N + L_cpp
    P = np.zeros((B, N), dtype=complex)
    for idx in range(L_cpp):
        n_neg = idx - L_cpp
        m = (N + n_neg) % N
        P[idx, m] = np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * n_neg))
    P[L_cpp:, :] = np.eye(N)
    return P

def build_physical_H_ext(N, L_cpp, hs, ls, nus):
    B = N + L_cpp
    H_lin = np.zeros((N, B), dtype=complex)
    n_idx = np.arange(N)
    for p in range(len(hs)):
        dop = np.exp(-1j * 2 * np.pi * nus[p] * n_idx / N)
        H_lin[n_idx, L_cpp + n_idx - int(ls[p])] += hs[p] * dop
    return H_lin

def zero_unwrap_complex_phase(z_vec):
    # Pure complex-phasor incremental accumulation (ZERO np.unwrap!)
    N = len(z_vec)
    dphi = np.angle(z_vec[1:] * np.conj(z_vec[:-1]))
    phi = np.empty(N)
    phi[0] = np.angle(z_vec[0])
    phi[1:] = phi[0] + np.cumsum(dphi)
    return phi

def zero_unwrap_interior_clamped(z_vec, M_e):
    # Pure complex-phasor incremental accumulation over Gibbs-free interior [M_e .. N-M_e-1]
    # with exact Wiener MMSE constant boundary extrapolation outside.
    N = len(z_vec)
    phi_int = zero_unwrap_complex_phase(z_vec[M_e : N - M_e])
    phi = np.empty(N)
    phi[M_e : N - M_e] = phi_int
    phi[:M_e] = phi_int[0]
    phi[N - M_e:] = phi_int[-1]
    return phi

def cluster_paths(ls, min_gap=4):
    order = np.argsort(ls)
    clusters = []
    for idx in order:
        if not clusters or (ls[idx] - ls[clusters[-1][-1]] >= min_gap):
            clusters.append([int(idx)])
        else:
            clusters[-1].append(int(idx))
    return clusters

def oamp_svd_exact(y, H_td, Ah_mat, sigma2, pts, data_mask, x_full, n_iter=8):
    x_p0 = np.where(~data_mask, x_full, 0.0)
    y_d = y - H_td @ (Ah_mat @ x_p0)
    Hd = (H_td @ Ah_mat)[:, data_mask]
    Nd = Hd.shape[1]
    U, sv, Vh = np.linalg.svd(Hd, full_matrices=False)
    sv2 = sv**2
    Uhy = U.conj().T @ y_d
    v_fl = min(5e-4, max(sigma2 * 0.5, 1e-6))
    r = np.zeros(Nd, dtype=complex); v = 1.0
    for _ in range(n_iter):
        lam = sigma2 / max(v, v_fl)
        gain = sv2 / (sv2 + lam)
        xhat_lin = r + Vh.conj().T @ ((sv / (sv2 + lam)) * (Uhy - sv * (Vh @ r)))
        c_bar = min(float(np.sum(gain) / Nd), 0.9999)
        v_post = max(v * (1.0 - c_bar), v_fl)
        r_ext = (xhat_lin - (1.0 - c_bar) * r) / max(c_bar, 1e-6)
        v_ext = max(v_post / max(c_bar, 1e-6), v_fl)
        d2 = np.abs(r_ext[:, None] - pts[None, :])**2 / v_ext
        d2 -= d2.min(axis=1, keepdims=True)
        w = np.exp(-d2); w /= w.sum(axis=1, keepdims=True)
        xhat = w @ pts
        vx = max(float(np.mean(np.sum(w * np.abs(pts[None, :] - xhat[:, None])**2, axis=1))), v_fl)
        eta = min(vx / v_ext, 0.995)
        r = 0.65 * ((xhat - eta * r_ext) / (1.0 - eta)) + 0.35 * r
        v = 0.65 * max(vx / (1.0 - eta), v_fl) + 0.35 * v
    x_soft = x_p0.copy(); x_soft[data_mask] = xhat
    x_hard = x_p0.copy(); x_hard[data_mask] = pts[np.argmin(np.abs(r_ext[:, None] - pts[None, :]), axis=1)]
    return x_soft, x_hard, vx

def oamp_cyclic_banded(y, H_lin, pr, pt, c1, c2, sigma2, pts, data_mask, x_full, L_cpp, n_iter=8):
    # True O(N L_cpp^2 + N log N) cyclic-banded Woodbury OAMP:
    # ZERO dense N x N matrix formations or N^3 products!
    N = len(y); Nd = int(np.sum(data_mask)); frac_d = Nd / N; bw = L_cpp
    n_arr = np.arange(N)
    L1 = np.exp(-1j * 2 * np.pi * c1 * (n_arr ** 2))
    L2 = np.exp(-1j * 2 * np.pi * c2 * (n_arr ** 2))
    L1c = np.conj(L1); L2c = np.conj(L2)
    def daft_fwd(v): return L2 * np.fft.fft(L1 * v, norm='ortho')
    def daft_inv(v): return L1c * np.fft.ifft(L2c * v, norm='ortho')

    # Extract active taps (P << N) and build exact sparse H_td tap coefficients
    er = np.exp(1j * pr); et = np.exp(1j * pt)
    active_l = [l for l in range(L_cpp + 1) if np.max(np.abs(H_lin[n_arr, L_cpp + n_arr - l])) > 1e-12]
    P = len(active_l)
    tap_c = []
    tap_col = []
    for l in active_l:
        mc = L_cpp + n_arr - l
        val = er * H_lin[n_arr, mc] * et[mc]
        wrap = (n_arr < l)
        if np.any(wrap):
            n_neg = n_arr[wrap] - l
            val[wrap] *= np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * n_neg))
        tap_c.append(val)
        tap_col.append((n_arr - l) % N)

    # Exact O(N P) pilot subtraction y_d = y - H_td (A^H x_p0)
    x_p0 = np.where(~data_mask, x_full, 0.0)
    s_p0 = daft_inv(x_p0)
    y_p = np.zeros(N, dtype=complex)
    for p in range(P):
        y_p += tap_c[p] * s_p0[tap_col[p]]
    y_d = y - y_p

    # Exact O(N P) matched filter H_td^H y_d
    Hhy = np.zeros(N, dtype=complex)
    for p in range(P):
        np.add.at(Hhy, tap_col[p], np.conj(tap_c[p]) * y_d)

    # Exact O(N P^2) cyclic-banded Gram G0 = B + E K_mid E^H (no dense N^3 matmul!)
    ab0 = np.zeros((2 * bw + 1, N), dtype=complex)
    ab_lower = np.zeros((bw + 1, N), dtype=complex)
    C_tr = np.zeros((bw, bw), dtype=complex)
    for p in range(P):
        cp = np.conj(tap_c[p]); ip = tap_col[p]
        for q in range(P):
            prod = cp * tap_c[q]; jq = tap_col[q]
            diff = jq - ip
            in_band = (np.abs(diff) <= bw)
            if np.any(in_band):
                d_vals = diff[in_band]; j_vals = jq[in_band]; v_vals = prod[in_band]
                np.add.at(ab0, (bw - d_vals, j_vals), v_vals)
                low = (d_vals <= 0)
                if np.any(low):
                    np.add.at(ab_lower, (-d_vals[low], j_vals[low]), v_vals[low])
            top_right = (diff > bw)
            if np.any(top_right):
                np.add.at(C_tr, (ip[top_right], jq[top_right] - (N - bw)), prod[top_right])

    E = np.zeros((N, 2 * bw), dtype=complex)
    E[:bw, :bw] = np.eye(bw); E[-bw:, bw:] = np.eye(bw)
    K_mid = np.block([[np.zeros((bw, bw), dtype=complex), C_tr], [C_tr.conj().T, np.zeros((bw, bw), dtype=complex)]])
    eigs_B = np.maximum(eig_banded(ab_lower, lower=True, eigvals_only=True), 0.0)

    v_fl = min(5e-4, max(sigma2 * 0.5, 1e-6))
    r_x = np.zeros(N, dtype=complex); v_x = 1.0
    for _ in range(n_iter):
        v_td = max(frac_d * v_x, v_fl)
        r_s = daft_inv(r_x)
        lam = sigma2 / v_td
        ab = ab0.copy(); ab[bw, :] += lam
        X_all = solve_banded((bw, bw), ab, np.column_stack([Hhy + lam * r_s, E]))
        b_r = X_all[:, 0]; b_E = X_all[:, 1:]
        z_w = np.linalg.solve(np.eye(2 * bw) + K_mid @ (E.conj().T @ b_E), K_mid @ (E.conj().T @ b_r))
        shat = b_r - b_E @ z_w
        c_bar = min(float(np.mean(eigs_B / (eigs_B + lam))), 0.9999)
        v_s_post = max(v_td * (1.0 - c_bar), v_fl)
        r_s_ext = (shat - (1.0 - c_bar) * r_s) / max(c_bar, 1e-6)
        v_s_ext = max(v_s_post / max(c_bar, 1e-6), v_fl)
        r_x_ext = daft_fwd(r_s_ext)
        rd = r_x_ext[data_mask]
        d2 = np.abs(rd[:, None] - pts[None, :])**2 / v_s_ext
        d2 -= d2.min(axis=1, keepdims=True)
        w = np.exp(-d2); w /= w.sum(axis=1, keepdims=True)
        xhat_d = w @ pts
        vx_d = max(float(np.mean(np.sum(w * np.abs(pts[None, :] - xhat_d[:, None])**2, axis=1))), v_fl)
        eta = min(vx_d / v_s_ext, 0.995)
        r_x[data_mask] = 0.65 * ((xhat_d - eta * rd) / (1.0 - eta)) + 0.35 * r_x[data_mask]
        r_x[~data_mask] = 0.0
        v_x = 0.65 * max(vx_d / (1.0 - eta), v_fl) + 0.35 * v_x
    x_soft = x_p0.copy(); x_soft[data_mask] = xhat_d
    x_hard = x_p0.copy(); x_hard[data_mask] = pts[np.argmin(np.abs(r_x_ext[data_mask, None] - pts[None, :]), axis=1)]
    return x_soft, x_hard, vx_d

def gn_dual_banded(y, H_lin, s_ext_hat, phi_r, phi_t_ext, sig2_eff, sig_r, sig_t, L_cpp, obs_mask=None, n_gn=3):
    N, B = H_lin.shape
    pr = phi_r.copy(); pt = phi_t_ext.copy()
    M_tot = N + B; bw = 2 * L_cpp + 2
    idx_r = L_cpp + 2 * np.arange(N)
    idx_t = np.concatenate([np.arange(L_cpp), L_cpp + 2 * np.arange(N) + 1])
    inv_sr = 1.0 / max(sig_r, 1e-9); inv_st = 1.0 / max(sig_t, 1e-9)
    ab_prior = np.zeros((bw + 1, M_tot))
    for n in range(1, N):
        i, j = idx_r[n], idx_r[n - 1]; ab_prior[0,i]+=inv_sr; ab_prior[0,j]+=inv_sr; ab_prior[i-j,j]-=inv_sr
    for m in range(1, B):
        i, j = idx_t[m], idx_t[m - 1]; ab_prior[0,i]+=inv_st; ab_prior[0,j]+=inv_st; ab_prior[i-j,j]-=inv_st
    ab_prior[0, idx_t[L_cpp]] += 1e3; ab_prior[0, :] += 1e-6

    n_arr = np.arange(N)
    active_l = [l for l in range(L_cpp + 1) if np.max(np.abs(H_lin[n_arr, L_cpp + n_arr - l])) > 1e-12]
    H_taps = np.array([H_lin[n_arr, L_cpp + n_arr - l] for l in active_l])
    P = len(active_l)
    m_cols = np.array([L_cpp + n_arr - l for l in active_l])
    it_cols = idx_t[m_cols]
    w_obs = np.ones(N) if obs_mask is None else obs_mask.astype(float)
    inv_s2 = (2.0 / sig2_eff) * w_obs

    for _ in range(n_gn):
        er = np.exp(1j * pr); et = np.exp(1j * pt)
        c_tap = H_taps * (et[m_cols] * s_ext_hat[m_cols])
        u = np.sum(c_tap, axis=0)
        yhat = er * u; res = y - yhat
        g = np.zeros(M_tot)
        g[idx_r[1:]] += inv_sr * (pr[1:] - pr[:-1]); g[idx_r[:-1]] -= inv_sr * (pr[1:] - pr[:-1])
        g[idx_t[1:]] += inv_st * (pt[1:] - pt[:-1]); g[idx_t[:-1]] -= inv_st * (pt[1:] - pt[:-1])
        g[idx_t[L_cpp]] += 1e3 * pt[L_cpp]
        jr = 1j * yhat
        g[idx_r] += inv_s2 * np.real(np.conj(jr) * (-res))
        jt = (1j * er)[None, :] * c_tap
        np.add.at(g, it_cols, inv_s2[None, :] * np.real(np.conj(jt) * (-res)[None, :]))
        ab = ab_prior.copy()
        ab[0, idx_r] += inv_s2 * (np.abs(yhat)**2)
        for p in range(P):
            h_rt = inv_s2 * np.real(np.conj(jr) * jt[p])
            iv = np.maximum(idx_r, it_cols[p]); jv = np.minimum(idx_r, it_cols[p])
            np.add.at(ab, (iv - jv, jv), h_rt)
            np.add.at(ab[0], it_cols[p], inv_s2 * (np.abs(jt[p])**2))
            for q in range(p + 1, P):
                h_pq = inv_s2 * np.real(np.conj(jt[p]) * jt[q])
                iv = np.maximum(it_cols[p], it_cols[q]); jv = np.minimum(it_cols[p], it_cols[q])
                np.add.at(ab, (iv - jv, jv), h_pq)
        step = np.clip(-solveh_banded(ab, g, lower=True), -0.4, 0.4)
        pr += step[idx_r]; pt += step[idx_t]
    return pr, pt

def gn_dual_dense_ref(y, H_lin, s_ext_hat, phi_r, phi_t_ext, sig2_eff, sig_r, sig_t, L_cpp, n_gn=3):
    N, B = H_lin.shape
    pr = phi_r.copy(); pt = phi_t_ext.copy()
    Dr = np.zeros((N-1, N)); Dt = np.zeros((B-1, B))
    for i in range(N-1): Dr[i,i]=-1; Dr[i,i+1]=1
    for i in range(B-1): Dt[i,i]=-1; Dt[i,i+1]=1
    Qr = (Dr.T @ Dr) / max(sig_r, 1e-9)
    Qt = (Dt.T @ Dt) / max(sig_t, 1e-9); Qt[L_cpp, L_cpp] += 1e3
    inv_s2 = 2.0 / sig2_eff
    for _ in range(n_gn):
        er = np.exp(1j * pr); et = np.exp(1j * pt)
        Hs = H_lin * (et * s_ext_hat)[None, :]
        yhat = er * np.sum(Hs, axis=1); res = y - yhat
        Jt = (1j * er)[:, None] * Hs
        gr = inv_s2 * np.real(np.conj(1j * yhat) * (-res)) + Qr @ pr
        gt = inv_s2 * np.real(Jt.conj().T @ (-res)) + Qt @ pt
        Hrr = np.diag(inv_s2 * np.abs(yhat)**2) + Qr
        Hrt = inv_s2 * np.real(np.conj(1j * yhat)[:, None] * Jt)
        Htt = inv_s2 * np.real(Jt.conj().T @ Jt) + Qt
        st = np.clip(-np.linalg.solve(np.block([[Hrr,Hrt],[Hrt.T,Htt]]) + 1e-6*np.eye(N+B), np.concatenate([gr,gt])), -0.4, 0.4)
        pr += st[:N]; pt += st[N:]
    return pr, pt

def gn_lumped_fast(y, H_circ, s_hat, phi_tot, sig2_eff, sig_pn_tot, obs_mask=None, n_gn=3):
    N = len(y); u = H_circ @ s_hat; phi = phi_tot.copy()
    inv_s = 1.0 / max(sig_pn_tot, 1e-9)
    w_obs = np.ones(N) if obs_mask is None else obs_mask.astype(float)
    inv_s2 = (2.0 / sig2_eff) * w_obs
    ab_p = np.zeros((2, N))
    ab_p[0, 0] = inv_s + 1e-6; ab_p[0, -1] = inv_s + 1e-6; ab_p[0, 1:-1] = 2*inv_s + 1e-6
    ab_p[1, :-1] = -inv_s
    for _ in range(n_gn):
        ep = np.exp(1j * phi)
        g = inv_s2 * np.imag(np.conj(y) * (ep * u))
        g[1:] += inv_s * (phi[1:] - phi[:-1]); g[:-1] -= inv_s * (phi[1:] - phi[:-1])
        ab = ab_p.copy(); ab[0] += inv_s2 * (np.abs(u)**2)
        phi += np.clip(-solveh_banded(ab, g, lower=True), -0.4, 0.4)
    return phi

def init_afdm_subband_matched_proj(Y_daft, H_lin_paths, s_p_ext, l_paths, clusters, k_centers, max_hw,
                                   A_afdm, Ah_afdm, L_cpp, sig_r, sig_t, sig_sub2, n_gn=6):
    # Matched projection on BOTH observation Y_sub AND predictor Pi_c(yhat_full)!
    # Zero np.unwrap! Works for arbitrary closely-spaced random clusters!
    N = len(Y_daft); B = N + L_cpp; n_cl = len(clusters)
    masks = []; y_subs = []; ref_cls = []
    for ci, cl in enumerate(clusters):
        k_hi = min(k_centers[ci] + max_hw, (k_centers[ci] + k_centers[ci-1]) // 2) if ci > 0 else k_centers[ci] + max_hw
        k_lo = max(k_centers[ci] - max_hw, (k_centers[ci] + k_centers[ci+1]) // 2 + 1) if ci < n_cl - 1 else k_centers[ci] - max_hw
        m = np.zeros(N, dtype=bool)
        for kk in range(k_lo, k_hi + 1):
            m[kk % N] = True
        masks.append(m)
        Ys = np.zeros(N, dtype=complex); Ys[m] = Y_daft[m]
        y_subs.append(Ah_afdm @ Ys)
        ref_cls.append(sum(H_lin_paths[p] @ s_p_ext for p in cl))

    # Full-diversity MRC complex-phasor phase init (ZERO np.unwrap!)
    # Circular DAFT subband filtering of a non-periodic Wiener phase + non-wrapping CPP
    # produces Dirichlet Gibbs boundary artifacts in the first/last M_e = L_cpp samples;
    # anchor incremental accumulation in the Gibbs-free interior [M_e .. N-M_e-1] and
    # apply exact Wiener MMSE constant boundary extrapolation outside.
    M_e = min(L_cpp, N // 16)
    z_lump = sum(y_subs[ci] * np.conj(ref_cls[ci]) for ci in range(n_cl))
    phi_int = zero_unwrap_complex_phase(z_lump[M_e : N - M_e])
    phi_mrc = np.empty(N)
    phi_mrc[M_e : N - M_e] = phi_int
    phi_mrc[:M_e] = phi_int[0]
    phi_mrc[N - M_e:] = phi_int[-1]
    pr = phi_mrc.copy(); pt = np.zeros(B)

    M_tot = N + B; bw = 2 * L_cpp + 2
    idx_r = L_cpp + 2 * np.arange(N)
    idx_t = np.concatenate([np.arange(L_cpp), L_cpp + 2 * np.arange(N) + 1])
    inv_sr = 1.0 / max(sig_r, 1e-9); inv_st = 1.0 / max(sig_t, 1e-9)
    ab_prior = np.zeros((bw + 1, M_tot))
    for n in range(1, N):
        i, j = idx_r[n], idx_r[n-1]; ab_prior[0,i]+=inv_sr; ab_prior[0,j]+=inv_sr; ab_prior[i-j,j]-=inv_sr
    for m in range(1, B):
        i, j = idx_t[m], idx_t[m-1]; ab_prior[0,i]+=inv_st; ab_prior[0,j]+=inv_st; ab_prior[i-j,j]-=inv_st
    ab_prior[0, idx_t[L_cpp]] += 1e3; ab_prior[0, :] += 1e-6

    n_arr = np.arange(N)
    w_int = np.zeros(N); w_int[M_e : N - M_e] = 1.0
    inv_s2 = (2.0 / sig_sub2) * w_int
    for _ in range(n_gn):
        er = np.exp(1j * pr); et = np.exp(1j * pt)
        g = np.zeros(M_tot)
        g[idx_r[1:]] += inv_sr * (pr[1:] - pr[:-1]); g[idx_r[:-1]] -= inv_sr * (pr[1:] - pr[:-1])
        g[idx_t[1:]] += inv_st * (pt[1:] - pt[:-1]); g[idx_t[:-1]] -= inv_st * (pt[1:] - pt[:-1])
        g[idx_t[L_cpp]] += 1e3 * pt[L_cpp]
        ab = ab_prior.copy()
        for ci, cl in enumerate(clusters):
            c_taps = []; it_cl = []
            for p in cl:
                lp = int(l_paths[p]); mc = L_cpp + n_arr - lp
                c_taps.append(H_lin_paths[p][n_arr, mc] * et[mc] * s_p_ext[mc])
                it_cl.append(idx_t[mc])
            c_taps = np.array(c_taps)
            u = np.sum(c_taps, axis=0)
            yhat_full = er * u
            # Exact matched subband projection on predictor!
            Yh_d = A_afdm @ yhat_full
            Yh_s = np.zeros(N, dtype=complex); Yh_s[masks[ci]] = Yh_d[masks[ci]]
            res_proj = y_subs[ci] - (Ah_afdm @ Yh_s)
            jr = 1j * yhat_full
            jt = (1j * er)[None, :] * c_taps
            g[idx_r] += inv_s2 * np.real(np.conj(jr) * (-res_proj))
            ab[0, idx_r] += inv_s2 * (np.abs(yhat_full)**2)
            for a_i in range(len(cl)):
                np.add.at(g, it_cl[a_i], inv_s2 * np.real(np.conj(jt[a_i]) * (-res_proj)))
                np.add.at(ab[0], it_cl[a_i], inv_s2 * (np.abs(jt[a_i])**2))
                h_rt = inv_s2 * np.real(np.conj(jr) * jt[a_i])
                iv = np.maximum(idx_r, it_cl[a_i]); jv = np.minimum(idx_r, it_cl[a_i])
                np.add.at(ab, (iv - jv, jv), h_rt)
                for b_i in range(a_i + 1, len(cl)):
                    h_pq = inv_s2 * np.real(np.conj(jt[a_i]) * jt[b_i])
                    iv = np.maximum(it_cl[a_i], it_cl[b_i]); jv = np.minimum(it_cl[a_i], it_cl[b_i])
                    np.add.at(ab, (iv - jv, jv), h_pq)
        step = np.clip(-solveh_banded(ab, g, lower=True), -0.4, 0.4)
        pr += step[idx_r]; pt += step[idx_t]
    return pr, pt, phi_mrc

def run_single_frame(args):
    (seed, regime_cfg) = args
    rng = np.random.default_rng(seed)
    N = regime_cfg['N']; L_cpp = 16; B = N + L_cpp
    snr_db = regime_cfg['snr_db']; sig_r = regime_cfg['sig_r']; sig_t = regime_cfg['sig_t']
    sig_pn = sig_r + sig_t
    csi_nmse = regime_cfg['csi_nmse']
    channel_mode = regime_cfg['channel_mode'] # 'coprime3' or 'rand4'
    use_banded_oamp = regime_cfg.get('use_banded_oamp', False)

    c1 = (3.0 if N == 512 else 2.0) / (2 * N)
    c2 = 1.0 / (2 * np.pi * N)
    two_Nc1 = 3 if N == 512 else 2
    max_hw = 10 if N == 512 else 6

    A_a = daft_matrix(N, c1, c2); Ah_a = A_a.conj().T
    A_o = daft_matrix(N, 0.0, 0.0); Ah_o = A_o.conj().T
    P_a = build_cpp_ext(N, c1, L_cpp); P_o = build_cpp_ext(N, 0.0, L_cpp)
    g8 = np.array([-7,-5,-3,-1,1,3,5,7]); pts64 = (g8[:,None] + 1j*g8[None,:]).ravel() / np.sqrt(42.0)
    qpsk = np.array([-1-1j,-1+1j,1-1j,1+1j])/np.sqrt(2.0)

    k_p = N // 2
    guard = np.zeros(N, dtype=bool)
    if N == 512: guard[196:318] = True # 122 bins (23.8%)
    else: guard[88:170] = True         # 82 bins (32.0%)
    data_a = ~guard; n_guard = int(np.sum(guard)); Nd = int(np.sum(data_a))

    pilot_oc = np.zeros(N, dtype=bool)
    pilot_oc[np.round(np.linspace(0, N-1, n_guard, endpoint=False)).astype(int)] = True
    data_oc = ~pilot_oc

    if channel_mode == 'coprime3':
        l_paths = np.array([0, 7, 16])
        pdp = np.array([0.4225, 0.3025, 0.2750])
    else:
        l_paths = np.array([0, int(rng.integers(1, 3)), int(rng.integers(7, 11)), int(rng.integers(14, 17))])
        pdp = np.array([0.22, 0.18, 0.30, 0.30])
    P_cnt = len(l_paths)
    nus = rng.uniform(-0.5, 0.5, P_cnt)
    hs_true = np.sqrt(pdp) * np.exp(1j * rng.uniform(0, 2*np.pi, P_cnt))
    w_path = pdp / np.sum(pdp)
    H_lin_true = build_physical_H_ext(N, L_cpp, hs_true, l_paths, nus)
    if csi_nmse > 0:
        hs_est = hs_true + np.sqrt(csi_nmse / 2.0) * (rng.standard_normal(P_cnt) + 1j * rng.standard_normal(P_cnt)) * np.sqrt(np.mean(np.abs(hs_true)**2))
    else:
        hs_est = hs_true
    H_lin = build_physical_H_ext(N, L_cpp, hs_est, l_paths, nus)
    H_circ_a = H_lin @ P_a; H_circ_o = H_lin @ P_o
    H_circ_a_true = H_lin_true @ P_a; H_circ_o_true = H_lin_true @ P_o
    H_lin_paths = [build_physical_H_ext(N, L_cpp, [hs_est[p]], [l_paths[p]], [nus[p]]) for p in range(P_cnt)]

    sig2 = 10.0 ** (-snr_db / 10.0)
    sig2_use = sig2 + csi_nmse
    # Model prior variance (fixed nominal 1.5e-3 per osc when testing Guard-b zero/rx-only PN!)
    sig_r_mod = regime_cfg.get('sig_r_mod', max(sig_r, 1.5e-3))
    sig_t_mod = regime_cfg.get('sig_t_mod', max(sig_t, 1.5e-3))
    sig_tot_mod = sig_r_mod + sig_t_mod

    phi_t = np.cumsum(np.sqrt(sig_t)*rng.standard_normal(B)) if sig_t > 0 else np.zeros(B); phi_t -= phi_t[L_cpp]
    phi_r = np.cumsum(np.sqrt(sig_r)*rng.standard_normal(N)) if sig_r > 0 else np.zeros(N)
    phi_lopt = phi_r + sum(w_path[p] * phi_t[L_cpp - l_paths[p] : L_cpp - l_paths[p] + N] for p in range(P_cnt))
    w_noise = np.sqrt(sig2/2.0)*(rng.standard_normal(N)+1j*rng.standard_normal(N))

    def detect_oamp(y_in, H_td_in, A_in, Ah_in, s2_in, dm_in, x_in, n_it):
        return oamp_svd_exact(y_in, H_td_in, Ah_in, s2_in, pts64, dm_in, x_in, n_iter=n_it)

    def run_fixed_dual(y_in, H_lin_in, P_in, A_in, Ah_in, dm_in, x_in, pr_i, pt_i):
        pr_c, pt_c = pr_i.copy(), pt_i.copy()
        best_r = np.inf; best_xh = None
        for out in range(10):
            Hc = np.exp(1j*pr_c)[:,None]*((H_lin_in*np.exp(1j*pt_c)[None,:])@P_in)
            xs, xhc, vx = detect_oamp(y_in, Hc, A_in, Ah_in, sig2_use + 0.02*(0.65**out), dm_in, x_in, 8)
            pr_c, pt_c = gn_dual_banded(y_in, H_lin_in, P_in@(Ah_in@xs), pr_c, pt_c, sig2_use + 0.5*vx, sig_r_mod, sig_t_mod, L_cpp, n_gn=3)
            rc = float(np.sum(np.abs(y_in - np.exp(1j*pr_c)*(H_lin_in@(np.exp(1j*pt_c)*(P_in@(Ah_in@xhc)))))**2))
            if rc < best_r: best_r = rc; best_xh = xhc
        return best_xh, best_r

    out_ser = {}
    # --- AFDM ---
    x_a = np.zeros(N, dtype=complex)
    x_a[data_a] = pts64[rng.integers(0, 64, Nd)]
    x_a[k_p] = np.sqrt(float(n_guard))
    y_a = np.exp(1j*phi_r)*(H_lin_true@(np.exp(1j*phi_t)*(P_a@(Ah_a@x_a)))) + w_noise
    y_a_nopn = H_circ_a_true @ (Ah_a @ x_a) + w_noise
    _, xh_a_nopn, _ = detect_oamp(y_a_nopn, H_circ_a, A_a, Ah_a, sig2_use, data_a, x_a, 12)
    out_ser['AFDM_NoPN_Ref'] = float(np.mean(np.abs(xh_a_nopn[data_a] - x_a[data_a]) > 1e-6))

    Y_daft = A_a @ y_a
    xp0 = np.zeros(N, dtype=complex); xp0[k_p] = x_a[k_p]; sp_ext = P_a @ (Ah_a @ xp0)
    ref_all = H_circ_a @ (Ah_a @ xp0)
    phi_cpe = np.full(N, np.angle(np.vdot(ref_all, y_a)))
    Yg = np.zeros(N, dtype=complex); Yg[guard] = Y_daft[guard]
    phi_nodemux = zero_unwrap_interior_clamped((Ah_a @ Yg) * np.conj(ref_all), min(L_cpp, N // 16))

    clusters = cluster_paths(l_paths, min_gap=4)
    k_centers = [k_p - two_Nc1 * int(np.round(sum(w_path[p]*l_paths[p] for p in cl)/sum(w_path[p] for p in cl))) for cl in clusters]
    pr0, pt0, phi_mrc = init_afdm_subband_matched_proj(Y_daft, H_lin_paths, sp_ext, l_paths, clusters, k_centers, max_hw,
                                                       A_a, Ah_a, L_cpp, sig_r_mod, sig_t_mod, max(sig2_use*4.0, 2e-3), n_gn=6)

    # AFDM_LumpPrac (Bittner-style soft-OAMP + lumped GN from SubMRC init)
    phi_l = phi_mrc.copy()
    for out in range(10):
        xs_l, _, vx_l = detect_oamp(y_a*np.exp(-1j*phi_l), H_circ_a, A_a, Ah_a, sig2_use + 0.02*(0.65**out), data_a, x_a, 8)
        phi_l = gn_lumped_fast(y_a, H_circ_a, Ah_a@xs_l, phi_l, sig2_use + 0.5*vx_l, sig_tot_mod, n_gn=3)
    _, xh_lp, _ = detect_oamp(y_a*np.exp(-1j*phi_l), H_circ_a, A_a, Ah_a, sig2_use, data_a, x_a, 12)
    _, xh_loc, _ = detect_oamp(y_a*np.exp(-1j*phi_lopt), H_circ_a, A_a, Ah_a, sig2_use, data_a, x_a, 12)
    Ho_a = np.exp(1j*phi_r)[:,None]*((H_lin*np.exp(1j*phi_t)[None,:])@P_a)
    _, xh_do_a, _ = detect_oamp(y_a, Ho_a, A_a, Ah_a, sig2_use, data_a, x_a, 12)

    xh_cpe, _ = run_fixed_dual(y_a, H_lin, P_a, A_a, Ah_a, data_a, x_a, phi_cpe, np.zeros(B))
    xh_ndm, _ = run_fixed_dual(y_a, H_lin, P_a, A_a, Ah_a, data_a, x_a, phi_nodemux, np.zeros(B))
    xh_mrc, r_mrc = run_fixed_dual(y_a, H_lin, P_a, A_a, Ah_a, data_a, x_a, phi_mrc, np.zeros(B))
    xh_sd, r_sd = run_fixed_dual(y_a, H_lin, P_a, A_a, Ah_a, data_a, x_a, pr0, pt0)
    xh_auto = xh_mrc if r_mrc <= r_sd else xh_sd

    out_ser['AFDM_CPE_DualGN'] = float(np.mean(np.abs(xh_cpe[data_a] - x_a[data_a]) > 1e-6))
    out_ser['AFDM_NoDemuxGuard_DualGN'] = float(np.mean(np.abs(xh_ndm[data_a] - x_a[data_a]) > 1e-6))
    out_ser['AFDM_LumpPrac'] = float(np.mean(np.abs(xh_lp[data_a] - x_a[data_a]) > 1e-6))
    out_ser['AFDM_LumpOracCent'] = float(np.mean(np.abs(xh_loc[data_a] - x_a[data_a]) > 1e-6))
    out_ser['AFDM_SubMRC_DualGN'] = float(np.mean(np.abs(xh_mrc[data_a] - x_a[data_a]) > 1e-6))
    out_ser['AFDM_SubDual_DualGN'] = float(np.mean(np.abs(xh_sd[data_a] - x_a[data_a]) > 1e-6))
    out_ser['AFDM_SubAuto_DualGN'] = float(np.mean(np.abs(xh_auto[data_a] - x_a[data_a]) > 1e-6))
    out_ser['AFDM_DualOrac'] = float(np.mean(np.abs(xh_do_a[data_a] - x_a[data_a]) > 1e-6))

    # --- OFDM Controls (exact same net rate Nd/N & total power N!) ---
    if regime_cfg.get('run_ofdm', True):
        # 1) OFDM Comb-PTRS
        x_oc = np.zeros(N, dtype=complex)
        x_oc[data_oc] = pts64[rng.integers(0, 64, Nd)]
        x_oc[pilot_oc] = qpsk[rng.integers(0, 4, n_guard)]
        y_oc = np.exp(1j*phi_r)*(H_lin_true@(np.exp(1j*phi_t)*(P_o@(Ah_o@x_oc)))) + w_noise
        y_oc_nopn = H_circ_o_true @ (Ah_o @ x_oc) + w_noise
        _, xh_o_nopn, _ = detect_oamp(y_oc_nopn, H_circ_o, A_o, Ah_o, sig2_use, data_oc, x_oc, 12)
        out_ser['OFDM_NoPN_Ref'] = float(np.mean(np.abs(xh_o_nopn[data_oc] - x_oc[data_oc]) > 1e-6))
        x_po = np.where(pilot_oc, x_oc, 0.0); s_po = Ah_o @ x_po
        phi_oc0 = np.full(N, np.angle(np.vdot(H_circ_o@s_po, y_oc)))
        phi_oc0 = gn_lumped_fast(y_oc, H_circ_o, s_po, phi_oc0, sig2_use + Nd/N, sig_tot_mod, n_gn=5)
        xh_oc, _ = run_fixed_dual(y_oc, H_lin, P_o, A_o, Ah_o, data_oc, x_oc, phi_oc0, np.zeros(B))
        Ho_o = np.exp(1j*phi_r)[:,None]*((H_lin*np.exp(1j*phi_t)[None,:])@P_o)
        _, xh_do_o, _ = detect_oamp(y_oc, Ho_o, A_o, Ah_o, sig2_use, data_oc, x_oc, 12)
        out_ser['OFDM_Comb_Dual'] = float(np.mean(np.abs(xh_oc[data_oc] - x_oc[data_oc]) > 1e-6))
        out_ser['OFDM_DualOrac'] = float(np.mean(np.abs(xh_do_o[data_oc] - x_oc[data_oc]) > 1e-6))

        # 2) OFDM Wideband ZC TD Preamble Dual-End Fit (n_guard samples preamble + Nd-pt OFDM!)
        F_d = daft_matrix(Nd, 0.0, 0.0); Fh_d = F_d.conj().T
        n_p = np.arange(n_guard); root_zc = 23 if n_guard == 82 else 29
        s_pre = np.exp(1j * np.pi * root_zc * n_p * (n_p + 1) / n_guard)
        A_pre = np.zeros((N, N), dtype=complex); A_pre[:n_guard,:n_guard]=np.eye(n_guard); A_pre[n_guard:,n_guard:]=F_d
        Ah_pre = A_pre.conj().T
        dm_pre = np.zeros(N, dtype=bool); dm_pre[n_guard:] = True
        x_pre = np.zeros(N, dtype=complex); x_pre[:n_guard] = s_pre; x_pre[n_guard:] = pts64[rng.integers(0, 64, Nd)]
        y_pre = np.exp(1j*phi_r)*(H_lin_true@(np.exp(1j*phi_t)*(P_o@(Ah_pre@x_pre)))) + w_noise
        obs_pre = np.zeros(N, dtype=bool); obs_pre[L_cpp:n_guard] = True
        s_pre_only = P_o @ np.concatenate([s_pre, np.zeros(Nd)])
        pr_pre0 = np.full(N, np.angle(np.vdot((H_lin@s_pre_only)[obs_pre], y_pre[obs_pre])))
        pr_pre0 = gn_lumped_fast(y_pre, H_circ_o, np.concatenate([s_pre, np.zeros(Nd)]), pr_pre0, sig2_use, sig_tot_mod, obs_mask=obs_pre, n_gn=5)
        pr_pre0, pt_pre0 = gn_dual_banded(y_pre, H_lin, s_pre_only, pr_pre0, np.zeros(B), sig2_use, sig_r_mod, sig_t_mod, L_cpp, obs_mask=obs_pre, n_gn=6)
        xh_pre, _ = run_fixed_dual(y_pre, H_lin, P_o, A_pre, Ah_pre, dm_pre, x_pre, pr_pre0, pt_pre0)
        out_ser['OFDM_TDPre_Dual'] = float(np.mean(np.abs(xh_pre[dm_pre] - x_pre[dm_pre]) > 1e-6))

        # 3) OFDM Fixed-Slope Chirp Pilot inside Guard Subcarriers (Li-Wang'24 style)
        x_fc = np.zeros(N, dtype=complex)
        x_fc[data_a] = pts64[rng.integers(0, 64, Nd)]
        k_g = np.arange(n_guard); x_fc[guard] = np.exp(1j * np.pi * (k_g ** 2) / n_guard)
        y_fc = np.exp(1j*phi_r)*(H_lin_true@(np.exp(1j*phi_t)*(P_o@(Ah_o@x_fc)))) + w_noise
        Y_fc_fft = A_o @ y_fc; Yg_fc = np.zeros(N, dtype=complex); Yg_fc[guard] = Y_fc_fft[guard]
        y_fc_sub = Ah_o @ Yg_fc
        s_fc_p = Ah_o @ np.where(guard, x_fc, 0.0)
        M_e_fc = min(L_cpp, N // 16)
        phi_fc0 = zero_unwrap_interior_clamped(y_fc_sub * np.conj(H_circ_o @ s_fc_p), M_e_fc)
        obs_fc = np.zeros(N, dtype=bool); obs_fc[M_e_fc : N - M_e_fc] = True
        pr_fc0, pt_fc0 = gn_dual_banded(y_fc_sub, H_lin, P_o @ s_fc_p, phi_fc0, np.zeros(B), max(sig2_use*4.0, 2e-3), sig_r_mod, sig_t_mod, L_cpp, obs_mask=obs_fc, n_gn=6)
        xh_fc, _ = run_fixed_dual(y_fc, H_lin, P_o, A_o, Ah_o, data_a, x_fc, pr_fc0, pt_fc0)
        out_ser['OFDM_FixedChirp_Dual'] = float(np.mean(np.abs(xh_fc[data_a] - x_fc[data_a]) > 1e-6))

    return out_ser

def benchmark_end_to_end_runtime(N=512, n_reps=3):
    # TRUE full end-to-end single-core timing: Stage-1 Subband MRC Init + 10 outer iters of (OAMP + Dual-End GN)!
    rng = np.random.default_rng(999)
    L_cpp = 16; B = N + L_cpp; l_paths = np.array([0, 7, 16])
    c1 = (3.0 if N == 512 else 2.0) / (2 * N); c2 = 1.0 / (2 * np.pi * N)
    two_Nc1 = 3 if N == 512 else 2; max_hw = 10 if N == 512 else 6
    A_a = daft_matrix(N, c1, c2); Ah_a = A_a.conj().T; P_a = build_cpp_ext(N, c1, L_cpp)
    g8 = np.array([-7,-5,-3,-1,1,3,5,7]); pts64 = (g8[:,None] + 1j*g8[None,:]).ravel() / np.sqrt(42.0)
    k_p = N // 2; guard = np.zeros(N, dtype=bool)
    if N == 512: guard[196:318] = True
    else: guard[88:170] = True
    data_a = ~guard; n_guard = int(np.sum(guard)); Nd = int(np.sum(data_a))
    hs = np.array([0.65, 0.55, 0.52]) * np.exp(1j * rng.uniform(0, 2*np.pi, 3))
    nus = rng.uniform(-0.5, 0.5, 3); sig2 = 1e-3
    H_lin = build_physical_H_ext(N, L_cpp, hs, l_paths, nus)
    H_lin_paths = [build_physical_H_ext(N, L_cpp, [hs[p]], [l_paths[p]], [nus[p]]) for p in range(3)]
    phi_t = np.cumsum(np.sqrt(1e-3)*rng.standard_normal(B)); phi_t -= phi_t[L_cpp]
    phi_r = np.cumsum(np.sqrt(1e-3)*rng.standard_normal(N))
    x_a = np.zeros(N, dtype=complex); x_a[data_a] = pts64[rng.integers(0, 64, Nd)]; x_a[k_p] = np.sqrt(float(n_guard))
    y_a = np.exp(1j*phi_r)*(H_lin@(np.exp(1j*phi_t)*(P_a@(Ah_a@x_a)))) + np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N))
    xp0 = np.zeros(N, dtype=complex); xp0[k_p] = x_a[k_p]; sp_ext = P_a @ (Ah_a @ xp0)
    clusters = [[0], [1], [2]]; k_centers = [k_p - two_Nc1*int(l) for l in l_paths]

    n_arr = np.arange(N)
    L1 = np.exp(-1j * 2 * np.pi * c1 * (n_arr ** 2))
    L2 = np.exp(-1j * 2 * np.pi * c2 * (n_arr ** 2))
    L1c = np.conj(L1); L2c = np.conj(L2)
    cpp_fac = np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * (np.arange(L_cpp) - L_cpp)))
    def daft_fwd(v): return L2 * np.fft.fft(L1 * v, norm='ortho')
    def daft_inv(v): return L1c * np.fft.ifft(L2c * v, norm='ortho')
    def cpp_ext(s): return np.concatenate([cpp_fac * s[-L_cpp:], s])
    def apply_Hlin(pt_v, s_e):
        et = np.exp(1j * pt_v)
        out = np.zeros(N, dtype=complex)
        for p in range(3):
            lp = int(l_paths[p]); mc = L_cpp + n_arr - lp
            out += H_lin_paths[p][n_arr, mc] * et[mc] * s_e[mc]
        return out

    t_dense_list = []; t_band_list = []; ser_d_list = []; ser_b_list = []
    for _ in range(n_reps):
        # 1) Full Dense end-to-end (Stage-1 init + 10 outer iters SVD OAMP + Dense GN)
        td0 = time.perf_counter()
        Y_daft = A_a @ y_a
        _, _, phi_mrc = init_afdm_subband_matched_proj(Y_daft, H_lin_paths, sp_ext, l_paths, clusters, k_centers, max_hw,
                                                       A_a, Ah_a, L_cpp, 1e-3, 1e-3, 4e-3, n_gn=0)
        pr_c, pt_c = phi_mrc.copy(), np.zeros(B); best_r = np.inf; xh_d = None
        for out in range(10):
            Hc = np.exp(1j*pr_c)[:,None]*((H_lin*np.exp(1j*pt_c)[None,:])@P_a)
            xs, xhc, vx = oamp_svd_exact(y_a, Hc, Ah_a, sig2 + 0.02*(0.65**out), pts64, data_a, x_a, 8)
            pr_c, pt_c = gn_dual_dense_ref(y_a, H_lin, P_a@(Ah_a@xs), pr_c, pt_c, sig2 + 0.5*vx, 1e-3, 1e-3, L_cpp, n_gn=3)
            rc = float(np.sum(np.abs(y_a - np.exp(1j*pr_c)*(H_lin@(np.exp(1j*pt_c)*(P_a@(Ah_a@xhc)))))**2))
            if rc < best_r: best_r = rc; xh_d = xhc
        t_dense_list.append((time.perf_counter() - td0) * 1000.0)
        ser_d_list.append(float(np.mean(np.abs(xh_d[data_a] - x_a[data_a]) > 1e-6)))

        # 2) Full Banded + FFT-DAFT end-to-end (ZERO dense N x N matrices formed!)
        tb0 = time.perf_counter()
        Y_daft = daft_fwd(y_a)
        M_e = min(L_cpp, N // 16)
        z_lump = np.zeros(N, dtype=complex)
        for ci, kc in enumerate(k_centers):
            k_hi = min(kc + max_hw, (kc + k_centers[ci-1]) // 2) if ci > 0 else kc + max_hw
            k_lo = max(kc - max_hw, (kc + k_centers[ci+1]) // 2 + 1) if ci < 2 else kc - max_hw
            Ys = np.zeros(N, dtype=complex); Ys[k_lo:k_hi+1] = Y_daft[k_lo:k_hi+1]
            lp = int(l_paths[ci]); mc = L_cpp + n_arr - lp
            ref_c = H_lin_paths[ci][n_arr, mc] * sp_ext[mc]
            z_lump += daft_inv(Ys) * np.conj(ref_c)
        phi_mrc_b = zero_unwrap_interior_clamped(z_lump, M_e)
        pr_c, pt_c = phi_mrc_b.copy(), np.zeros(B); best_r = np.inf; xh_b = None
        for out in range(10):
            xs, xhc, vx = oamp_cyclic_banded(y_a, H_lin, pr_c, pt_c, c1, c2, sig2 + 0.02*(0.65**out), pts64, data_a, x_a, L_cpp, 8)
            pr_c, pt_c = gn_dual_banded(y_a, H_lin, cpp_ext(daft_inv(xs)), pr_c, pt_c, sig2 + 0.5*vx, 1e-3, 1e-3, L_cpp, n_gn=3)
            rc = float(np.sum(np.abs(y_a - np.exp(1j*pr_c)*apply_Hlin(pt_c, cpp_ext(daft_inv(xhc))))**2))
            if rc < best_r: best_r = rc; xh_b = xhc
        t_band_list.append((time.perf_counter() - tb0) * 1000.0)
        ser_b_list.append(float(np.mean(np.abs(xh_b[data_a] - x_a[data_a]) > 1e-6)))

    return {
        "N": N,
        "dense_e2e_ms": float(np.median(t_dense_list)),
        "banded_e2e_ms": float(np.median(t_band_list)),
        "speedup": float(np.median(t_dense_list) / np.median(t_band_list)),
        "dense_ser": float(np.mean(ser_d_list)),
        "banded_ser": float(np.mean(ser_b_list)),
    }

def summarize_regime(rows, ref_key='AFDM_SubMRC_DualGN'):
    keys = list(rows[0].keys())
    n = len(rows)
    summary = {"n_frames": n, "means": {}, "stds": {}, "paired_diff_vs_ref": {}}
    ref_arr = np.array([r[ref_key] for r in rows])
    for k in keys:
        arr = np.array([r[k] for r in rows])
        summary["means"][k] = float(np.mean(arr))
        summary["stds"][k] = float(np.std(arr, ddof=1)) if n > 1 else 0.0
        d = arr - ref_arr
        ci = 1.96 * float(np.std(d, ddof=1)) / math.sqrt(n) if n > 1 else 0.0
        summary["paired_diff_vs_ref"][k] = {"mean": float(np.mean(d)), "ci95": ci}
    return summary

def main():
    print("PYTHON:", sys.executable, flush=True)
    smoke = ("--smoke" in sys.argv)
    n_workers = 1 if smoke else min(16, os.cpu_count() or 8)
    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "/tmp/summary_m_r10_01.json"

    regimes = [
        ("R1_N512_30dB_2e3",     dict(N=512, snr_db=30.0, sig_r=1e-3,   sig_t=1e-3,   csi_nmse=0.0,  channel_mode='coprime3', n_frames=2 if smoke else 100, run_ofdm=True)),
        ("R2_N512_30dB_3e3",     dict(N=512, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, csi_nmse=0.0,  channel_mode='coprime3', n_frames=2 if smoke else 100, run_ofdm=True)),
        ("R3_N512_45dB_3e3_FLR", dict(N=512, snr_db=45.0, sig_r=1.5e-3, sig_t=1.5e-3, csi_nmse=0.0,  channel_mode='coprime3', n_frames=2 if smoke else 100, run_ofdm=True)),
        ("R4_N512_30dB_ImpCSI",  dict(N=512, snr_db=30.0, sig_r=1e-3,   sig_t=1e-3,   csi_nmse=1e-3, channel_mode='coprime3', n_frames=2 if smoke else 100, run_ofdm=True)),
        ("R5_N256_Rand4_3e3",    dict(N=256, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, csi_nmse=0.0,  channel_mode='rand4',    n_frames=2 if smoke else 200, run_ofdm=True)),
        ("R6a_N256_GuardB_0PN",  dict(N=256, snr_db=30.0, sig_r=0.0,    sig_t=0.0,    csi_nmse=0.0,  channel_mode='coprime3', n_frames=2 if smoke else 100, run_ofdm=False, sig_r_mod=1.5e-3, sig_t_mod=1.5e-3)),
        ("R6b_N256_GuardB_RxPN", dict(N=256, snr_db=30.0, sig_r=3e-3,   sig_t=0.0,    csi_nmse=0.0,  channel_mode='coprime3', n_frames=2 if smoke else 100, run_ofdm=False, sig_r_mod=1.5e-3, sig_t_mod=1.5e-3)),
        ("R6c_N256_Extr_6e3",    dict(N=256, snr_db=30.0, sig_r=3e-3,   sig_t=3e-3,   csi_nmse=0.0,  channel_mode='coprime3', n_frames=2 if smoke else 100, run_ofdm=False)),
    ]

    t_all = time.time()
    results = {"meta": {"smoke": smoke, "n_workers": n_workers, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}, "regimes": {}}
    for idx_r, (name, cfg) in enumerate(regimes):
        t_r = time.time()
        nf = cfg['n_frames']
        tasks = [(20261125 + idx_r * 10000 + f, cfg) for f in range(nf)]
        if n_workers > 1:
            with Pool(n_workers) as pool:
                rows = pool.map(run_single_frame, tasks)
        else:
            rows = [run_single_frame(t) for t in tasks]
        ref_k = 'AFDM_SubDual_DualGN' if name == 'R6c_N256_Extr_6e3' else 'AFDM_SubMRC_DualGN'
        summ = summarize_regime(rows, ref_key=ref_k)
        summ["elapsed_s"] = round(time.time() - t_r, 1)
        results["regimes"][name] = summ
        m = summ["means"]
        print(f"[{name}] ({nf} fr, {summ['elapsed_s']}s): LumpPrac={m['AFDM_LumpPrac']:.3e} | LumpOracCent={m['AFDM_LumpOracCent']:.3e} | "
              f"CPE_Dual={m['AFDM_CPE_DualGN']:.3e} | SubMRC_Dual={m['AFDM_SubMRC_DualGN']:.3e} | SubDual={m['AFDM_SubDual_DualGN']:.3e} | DualOrac={m['AFDM_DualOrac']:.3e}", flush=True)
        if 'OFDM_Comb_Dual' in m:
            print(f"    OFDM: Comb={m['OFDM_Comb_Dual']:.3e} | TDPre={m['OFDM_TDPre_Dual']:.3e} | FixedChirp={m['OFDM_FixedChirp_Dual']:.3e} | DualOrac={m['OFDM_DualOrac']:.3e}", flush=True)

    # R7: End-to-End Runtime Benchmark (N=256 and N=512, single core!)
    rt256 = benchmark_end_to_end_runtime(256, n_reps=1 if smoke else 3)
    rt512 = benchmark_end_to_end_runtime(512, n_reps=1 if smoke else 3)
    results["runtime_e2e"] = {"N256": rt256, "N512": rt512}
    print(f"[R7_Runtime] N=256: Dense={rt256['dense_e2e_ms']:.1f}ms vs Banded={rt256['banded_e2e_ms']:.1f}ms ({rt256['speedup']:.2f}x) | "
          f"N=512: Dense={rt512['dense_e2e_ms']:.1f}ms vs Banded={rt512['banded_e2e_ms']:.1f}ms ({rt512['speedup']:.2f}x)", flush=True)

    # Evaluate Pre-Registered Verdicts!
    R = results["regimes"]
    def safe_ratio(a, b): return a / max(b, 1e-12)
    r1, r2, r3, r4, r5 = R["R1_N512_30dB_2e3"], R["R2_N512_30dB_3e3"], R["R3_N512_45dB_3e3_FLR"], R["R4_N512_30dB_ImpCSI"], R["R5_N256_Rand4_3e3"]
    r6a, r6b, r6c = R["R6a_N256_GuardB_0PN"], R["R6b_N256_GuardB_RxPN"], R["R6c_N256_Extr_6e3"]

    p1 = (safe_ratio(r1["means"]["AFDM_LumpOracCent"], r1["means"]["AFDM_SubMRC_DualGN"]) >= 4.0 and
          safe_ratio(r2["means"]["AFDM_LumpOracCent"], r2["means"]["AFDM_SubMRC_DualGN"]) >= 4.0 and
          r1["paired_diff_vs_ref"]["AFDM_LumpOracCent"]["mean"] - r1["paired_diff_vs_ref"]["AFDM_LumpOracCent"]["ci95"] > 0 and
          r2["paired_diff_vs_ref"]["AFDM_LumpOracCent"]["mean"] - r2["paired_diff_vs_ref"]["AFDM_LumpOracCent"]["ci95"] > 0)
    p2 = (r3["means"]["OFDM_DualOrac"] < 2e-3 and
          r3["means"]["AFDM_LumpOracCent"] > 1.5e-2 and
          safe_ratio(r3["means"]["AFDM_LumpOracCent"], r3["means"]["AFDM_SubMRC_DualGN"]) >= 4.0 and
          min(safe_ratio(r3["means"][ok], r3["means"]["AFDM_SubMRC_DualGN"]) for ok in ["OFDM_Comb_Dual","OFDM_TDPre_Dual","OFDM_FixedChirp_Dual"]) >= 10.0)
    p3 = (safe_ratio(r1["means"]["AFDM_CPE_DualGN"], r1["means"]["AFDM_SubMRC_DualGN"]) >= 5.0 and
          safe_ratio(r1["means"]["AFDM_NoDemuxGuard_DualGN"], r1["means"]["AFDM_SubMRC_DualGN"]) >= 5.0 and
          safe_ratio(r2["means"]["AFDM_CPE_DualGN"], r2["means"]["AFDM_SubMRC_DualGN"]) >= 5.0 and
          safe_ratio(r2["means"]["AFDM_NoDemuxGuard_DualGN"], r2["means"]["AFDM_SubMRC_DualGN"]) >= 5.0)
    p4 = (safe_ratio(r4["means"]["AFDM_LumpPrac"], r4["means"]["AFDM_SubMRC_DualGN"]) >= 2.0 and
          safe_ratio(r4["means"]["OFDM_Comb_Dual"], r4["means"]["AFDM_SubMRC_DualGN"]) >= 3.0 and
          safe_ratio(r5["means"]["AFDM_LumpOracCent"], r5["means"]["AFDM_SubMRC_DualGN"]) >= 3.0 and
          min(safe_ratio(r5["means"][ok], r5["means"]["AFDM_SubMRC_DualGN"]) for ok in ["OFDM_Comb_Dual","OFDM_TDPre_Dual","OFDM_FixedChirp_Dual"]) >= 5.0)
    p5 = (r6a["means"]["AFDM_SubMRC_DualGN"] <= r6a["means"]["AFDM_NoPN_Ref"] + 1e-3 and
          r6b["means"]["AFDM_SubMRC_DualGN"] <= r6b["means"]["AFDM_LumpPrac"] + 5e-3 and
          safe_ratio(r6c["means"]["AFDM_LumpOracCent"], r6c["means"]["AFDM_SubDual_DualGN"]) >= 3.0 and
          r6c["means"]["AFDM_SubDual_DualGN"] < r6c["means"]["AFDM_SubMRC_DualGN"])
    p6 = (rt512["speedup"] >= 4.0 and abs(rt512["banded_ser"] - rt512["dense_ser"]) <= 2e-3)

    results["verdicts"] = {
        "P1_BREAKS_LUMPED_ORACLE_30DB": bool(p1),
        "P2_HIGH_SNR_FLOOR_AND_NO_DIVERSITY_CONFOUND": bool(p2),
        "P3_CAUSAL_SUBBAND_ABLATION": bool(p3),
        "P4_RANDOM_MULTICLUSTER_AND_IMPCSI": bool(p4),
        "P5_GUARDB_AND_EXTREME_DUAL": bool(p5),
        "P6_END_TO_END_BANDED_SPEEDUP": bool(p6),
        "PASS_PRIMARY": bool(p1 and p2 and p3 and p4 and p5 and p6),
    }
    results["meta"]["total_elapsed_s"] = round(time.time() - t_all, 1)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print("\nVERDICTS:", json.dumps(results["verdicts"], indent=2), flush=True)

if __name__ == "__main__":
    main()
