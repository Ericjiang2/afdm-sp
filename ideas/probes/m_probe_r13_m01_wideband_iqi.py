import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys, time
import numpy as np
from multiprocessing import Pool
from scipy.linalg import cholesky_banded, cho_solve_banded, cho_factor, cho_solve, qr
from scipy.signal.windows import dpss

def daft_matrix(N, c1, c2):
    n = np.arange(N)
    L1 = np.exp(-1j * 2 * np.pi * c1 * (n**2))
    L2 = np.exp(-1j * 2 * np.pi * c2 * (n**2))
    F = np.fft.fft(np.eye(N)) / np.sqrt(N)
    return (L2[:, None] * F) * L1[None, :]

def qam_constellation(M):
    m_side = int(np.sqrt(M))
    levels = np.arange(-(m_side - 1), m_side, 2, dtype=float)
    grid = (levels[:, None] + 1j * levels[None, :]).ravel()
    grid /= np.sqrt(np.mean(np.abs(grid)**2))
    return grid

def qam_hard(x, const):
    idx = np.argmin(np.abs(x[:, None] - const[None, :]), axis=1)
    return const[idx], idx

def qam_soft(x, var_n, const):
    var_n = np.maximum(var_n, 1e-6)
    d2 = np.abs(x[:, None] - const[None, :])**2
    logw = -d2 / var_n
    logw -= np.max(logw, axis=1, keepdims=True)
    w = np.exp(logw)
    w /= np.sum(w, axis=1, keepdims=True)
    mean = w @ const
    var = np.sum(w * np.abs(const[None, :] - mean[:, None])**2, axis=1)
    return mean, np.maximum(var, 1e-6)

def circ_mat(taps, N):
    M = np.zeros((N, N), dtype=complex)
    for m, val in enumerate(taps):
        for n in range(N):
            M[n, (n - m) % N] += val
    return M

def generate_iqi_filters(rng, level="mod", Lf=3, Lg=3):
    if level == "zero":
        return np.array([1.0 + 0j]), np.array([0.0 + 0j]), np.array([1.0 + 0j]), np.array([0.0 + 0j])
    f1 = np.zeros(Lf, dtype=complex); f1[0] = 1.0
    g1 = np.zeros(Lg, dtype=complex); g1[0] = 1.0
    f1[1:] = np.array([0.035, 0.015])[:Lf-1] * np.exp(1j * rng.uniform(0, 2*np.pi, Lf-1))
    g1[1:] = np.array([0.035, 0.015])[:Lg-1] * np.exp(1j * rng.uniform(0, 2*np.pi, Lg-1))
    if level == "mod":  # ~17-19 dB IRR
        base = np.array([0.085, 0.075, 0.045])[:Lf]
    else:               # "strong": ~12-14 dB IRR (uncalibrated wideband direct-conv mmWave/THz)
        base = np.array([0.145, 0.125, 0.075])[:Lf]
    f2 = base * rng.uniform(0.85, 1.15, Lf) * np.exp(1j * rng.uniform(0, 2*np.pi, Lf))
    g2 = base * rng.uniform(0.85, 1.15, Lg) * np.exp(1j * rng.uniform(0, 2*np.pi, Lg))
    return f1, f2, g1, g2

def phys_transmit_receive(s, c1, gains, delays, dopplers, f1, f2, g1, g2, w_full, t_offset=0):
    N = len(s)
    l_max = max(delays) if len(delays) else 0
    Lf, Lg = len(f1), len(g1)
    L_cpp = l_max + Lf + Lg
    n_neg = np.arange(-L_cpp, 0)
    cpp = s[N + n_neg] * np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * n_neg))
    s_tx = np.concatenate([cpp, s])
    s_iq = np.zeros_like(s_tx)
    for m in range(Lf):
        s_iq[m:] += f1[m] * s_tx[:len(s_tx)-m] + f2[m] * np.conj(s_tx[:len(s_tx)-m])
    start_y = L_cpp - (Lg - 1)
    n_y = np.arange(-(Lg - 1), N)
    y = np.zeros(len(n_y), dtype=complex)
    for h_p, l_p, nu_p in zip(gains, delays, dopplers):
        src = s_iq[start_y - l_p : start_y - l_p + len(n_y)]
        y += h_p * np.exp(-1j * 2 * np.pi * nu_p * (t_offset + n_y) / N) * src
    y += w_full
    r = np.zeros(N, dtype=complex)
    for m in range(Lg):
        idx0 = (Lg - 1) - m
        r += g1[m] * y[idx0 : idx0 + N] + g2[m] * np.conj(y[idx0 : idx0 + N])
    return r

def build_interleaved_real_banded(H_dir_taps, H_img_taps):
    N, L = H_dir_taps.shape
    a = H_dir_taps; b = H_img_taps
    B00 = np.real(a + b); B01 = -np.imag(a - b)
    B10 = np.imag(a + b); B11 =  np.real(a - b)
    G00 = np.zeros((N, L)); G01 = np.zeros((N, L))
    G10 = np.zeros((N, L)); G11 = np.zeros((N, L))
    idx_n = np.arange(N)
    for d in range(L):
        for l in range(d, L):
            n_src = (idx_n + l) % N
            l2 = l - d
            G00[:, d] += B00[n_src, l]*B00[n_src, l2] + B10[n_src, l]*B10[n_src, l2]
            G01[:, d] += B00[n_src, l]*B01[n_src, l2] + B10[n_src, l]*B11[n_src, l2]
            G10[:, d] += B01[n_src, l]*B00[n_src, l2] + B11[n_src, l]*B10[n_src, l2]
            G11[:, d] += B01[n_src, l]*B01[n_src, l2] + B11[n_src, l]*B11[n_src, l2]
    return (B00, B01, B10, B11), (G00, G01, G10, G11)

def cyclic_banded_wl_factor(G_blocks, reg_diag):
    G00, G01, G10, G11 = G_blocks
    N, L = G00.shape
    p = L - 1; m = N - p; b = 2 * p + 1
    ab = np.zeros((b + 1, 2 * m), dtype=float)
    i_m = np.arange(m)
    ab[0, 2*i_m]     = G00[:m, 0] + reg_diag[:m]
    ab[0, 2*i_m + 1] = G11[:m, 0] + reg_diag[:m]
    ab[1, 2*i_m]     = G10[:m, 0]
    for d in range(1, L):
        k = np.arange(m - d)
        ab[2*d,     2*k]     = G00[k, d]
        ab[2*d + 1, 2*k]     = G01[k, d]
        ab[2*d - 1, 2*k + 1] = G10[k, d]
        ab[2*d,     2*k + 1] = G11[k, d]
    c_A = cholesky_banded(ab, lower=True)
    D = np.zeros((2 * p, 2 * p), dtype=float)
    for ii in range(p):
        k = m + ii
        D[2*ii, 2*ii] = G00[k, 0] + reg_diag[k]; D[2*ii+1, 2*ii+1] = G11[k, 0] + reg_diag[k]
        D[2*ii, 2*ii+1] = G01[k, 0]; D[2*ii+1, 2*ii] = G10[k, 0]
        for d in range(1, L):
            jj = ii + d
            if jj < p:
                blk = np.array([[G00[k, d], G01[k, d]], [G10[k, d], G11[k, d]]])
                D[2*ii:2*ii+2, 2*jj:2*jj+2] = blk; D[2*jj:2*jj+2, 2*ii:2*ii+2] = blk.T
    B = np.zeros((2 * m, 2 * p), dtype=float)
    for d in range(1, L):
        for k in range(max(0, m - d), m):
            jj = k + d - m
            if 0 <= jj < p:
                B[2*k:2*k+2, 2*jj:2*jj+2] += np.array([[G00[k, d], G01[k, d]], [G10[k, d], G11[k, d]]])
    for ii in range(p):
        k = m + ii
        for d in range(1, L):
            r = (k + d) % N
            if r < m:
                B[2*r:2*r+2, 2*ii:2*ii+2] += np.array([[G00[k, d], G10[k, d]], [G01[k, d], G11[k, d]]])
    AinvB = cho_solve_banded((c_A, True), B)
    S = D - B.T @ AinvB
    c_S = cho_factor(S, lower=True)
    return (c_A, B, AinvB, c_S, m, p)

def cyclic_banded_wl_solve(fac, rhs_c):
    c_A, B, AinvB, c_S, m, p = fac
    N = m + p
    rhs = np.empty(2 * N, dtype=float); rhs[0::2] = np.real(rhs_c); rhs[1::2] = np.imag(rhs_c)
    f1 = rhs[:2*m]; f2 = rhs[2*m:]
    y1 = cho_solve_banded((c_A, True), f1)
    x2 = cho_solve(c_S, f2 - B.T @ y1)
    x1 = y1 - AinvB @ x2
    x = np.concatenate([x1, x2])
    return x[0::2] + 1j * x[1::2]

def apply_M_adj(B_taps, r):
    B00, B01, B10, B11 = B_taps
    N, L = B00.shape
    rr = np.real(r); ri = np.imag(r)
    out_r = np.zeros(N); out_i = np.zeros(N)
    idx = np.arange(N)
    for l in range(L):
        n_src = (idx + l) % N
        out_r += B00[n_src, l]*rr[n_src] + B10[n_src, l]*ri[n_src]
        out_i += B01[n_src, l]*rr[n_src] + B11[n_src, l]*ri[n_src]
    return out_r + 1j * out_i

def apply_M_fwd(H_dir_taps, H_img_taps, s):
    N, L = H_dir_taps.shape
    out = np.zeros(N, dtype=complex); idx = np.arange(N)
    for l in range(L):
        src = (idx - l) % N
        out += H_dir_taps[:, l] * s[src] + H_img_taps[:, l] * np.conj(s[src])
    return out

def build_bem_pilot_dict(s_p, B_bem, L_eq):
    N, Q = B_bem.shape
    Phi = np.empty((N, L_eq * Q), dtype=complex); idx = np.arange(N)
    for l in range(L_eq):
        Phi[:, l*Q:(l+1)*Q] = B_bem * s_p[(idx - l) % N][:, None]
    return Phi

def bem_coeffs_to_taps(c, B_bem, L_eq):
    return B_bem @ c.reshape(L_eq, B_bem.shape[1]).T

def taps_to_dense(H_taps):
    N, L = H_taps.shape
    H = np.zeros((N, N), dtype=complex); idx = np.arange(N)
    for l in range(L):
        H[idx, (idx - l) % N] += H_taps[:, l]
    return H

def apply_taps(H_taps, x):
    N, L = H_taps.shape
    out = np.zeros(N, dtype=complex); idx = np.arange(N)
    for l in range(L):
        out += H_taps[:, l] * x[(idx - l) % N]
    return out

def convolve_taps_with_fir(H_taps, u_fir):
    N, L_eq = H_taps.shape; Lu = len(u_fir)
    out = np.zeros((N, L_eq + Lu - 1), dtype=complex)
    for l in range(L_eq):
        for m in range(Lu):
            out[:, l + m] += H_taps[:, l] * u_fir[m]
    return out

def rx_iqi_invert_fft(r, u_rx):
    N = len(r)
    R_k = np.fft.fft(r); U_k = np.fft.fft(u_rx, N)
    neg = (-np.arange(N)) % N
    denom = 1.0 - U_k * np.conj(U_k[neg])
    if np.min(np.abs(denom)) < 0.2:
        u_rx = u_rx * (0.45 / max(np.sum(np.abs(u_rx)), 0.45))
        U_k = np.fft.fft(u_rx, N); denom = 1.0 - U_k * np.conj(U_k[neg])
    return np.fft.ifft((R_k - U_k * np.conj(R_k[neg])) / denom)

def estimate_alpha_oamp(Hd_taps, Hi_taps, reg):
    Hf = np.fft.fft(Hd_taps, n=64, axis=1)
    p2 = np.abs(Hf)**2 + np.abs(np.fft.fft(Hi_taps, n=64, axis=1))**2
    return float(np.clip(np.mean(p2 / (p2 + reg)), 0.15, 0.9999))

def banded_wl_detect(r_tilde, Hd_taps, Hi_taps, A_plus, data_idx, xp_val, const, sig2, n_iter=3):
    N = len(r_tilde)
    xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    sp = A_plus.conj().T @ xp
    r_d = r_tilde - apply_M_fwd(Hd_taps, Hi_taps, sp)
    B_taps, G_blks = build_interleaved_real_banded(Hd_taps, Hi_taps)
    v_td = len(data_idx) / float(N)
    reg0 = max(sig2, 1e-5) / max(v_td, 1e-3)
    fac0 = cyclic_banded_wl_factor(G_blks, np.full(N, reg0))
    s_lin = cyclic_banded_wl_solve(fac0, apply_M_adj(B_taps, r_d))
    alpha0 = estimate_alpha_oamp(Hd_taps, Hi_taps, reg0)
    x_lin = A_plus @ s_lin
    xd = x_lin[data_idx] / alpha0
    var_post = max((1.0 - alpha0) / alpha0, sig2)
    m_d, v_d = qam_soft(xd, var_post, const)
    if n_iter <= 1:
        return xd, m_d, v_d
    x_post = np.zeros(N, dtype=complex); x_post[data_idx] = m_d
    for _ in range(n_iter - 1):
        s_pri = A_plus.conj().T @ x_post
        res = r_d - apply_M_fwd(Hd_taps, Hi_taps, s_pri)
        v_cur = float(np.clip(np.mean(v_d) * len(data_idx) / N, 2e-4, 0.5))
        reg_it = max(sig2, 1e-5) / v_cur
        fac_it = cyclic_banded_wl_factor(G_blks, np.full(N, reg_it))
        delta_s = cyclic_banded_wl_solve(fac_it, apply_M_adj(B_taps, res))
        alpha_it = estimate_alpha_oamp(Hd_taps, Hi_taps, reg_it)
        s_ext = s_pri + delta_s / alpha_it
        x_ext = A_plus @ s_ext
        var_ext = max(v_cur * (1.0 - alpha_it) / alpha_it * (N / len(data_idx)), sig2)
        m_d_new, v_d = qam_soft(x_ext[data_idx], var_ext, const)
        x_post[data_idx] = 0.7 * m_d_new + 0.3 * x_post[data_idx]
        xd = x_ext[data_idx]
    return xd, x_post[data_idx], v_d

def solve_burst(r_list, A_plus, B_bem, data_idx, guard_obs_idx, xp_val, const, L_eq, Lu, mode, n_outer, pool_H):
    K = len(r_list); N, Q_bem = B_bem.shape
    xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    sp = A_plus.conj().T @ xp; sp_conj = np.conj(sp)
    Phi_p = build_bem_pilot_dict(sp, B_bem, L_eq)
    A_d_H = A_plus[data_idx, :].conj().T
    Phi_p_daft = (A_plus @ Phi_p)[guard_obs_idx, :]
    G_p = Phi_p_daft.conj().T @ Phi_p_daft
    P_pinv = np.linalg.solve(G_p + 1e-4*np.trace(G_p).real/G_p.shape[0]*np.eye(G_p.shape[0]), Phi_p_daft.conj().T)
    if pool_H:
        y_p_avg = np.mean([(A_plus @ r_list[k])[guard_obs_idx] for k in range(K)], axis=0)
        H0 = bem_coeffs_to_taps(P_pinv @ y_p_avg, B_bem, L_eq)
        H_taps_list = [H0.copy() for _ in range(K)]
    else:
        H_taps_list = [bem_coeffs_to_taps(P_pinv @ (A_plus @ r_list[k])[guard_obs_idx], B_bem, L_eq) for k in range(K)]

    Lu_eff = 1 if mode == "flat_joint" else Lu
    Psi_rows, z_rows = [], []
    idx = np.arange(N); Q_perp_c = None
    for k in range(K):
        if pool_H and Q_perp_c is not None:
            Q_perp = Q_perp_c
        else:
            U_kill = np.hstack([taps_to_dense(H_taps_list[k]) @ A_d_H, Phi_p])
            Qf, Rf = qr(U_kill, mode="full")
            dR = np.abs(np.diag(Rf))
            Q_perp = Qf[:, int(np.sum(dR > 1e-8 * dR[0])):]
            if pool_H:
                Q_perp_c = Q_perp
        z_rows.append(Q_perp.conj().T @ r_list[k])
        yp0_c = np.conj(apply_taps(H_taps_list[k], sp))
        Psi_tx = np.column_stack([Q_perp.conj().T @ apply_taps(H_taps_list[k], sp_conj[(idx - m) % N]) for m in range(Lu_eff)])
        Psi_rx = np.column_stack([Q_perp.conj().T @ yp0_c[(idx - m) % N] for m in range(Lu_eff)])
        if mode == "rx_only": Psi_rows.append(Psi_rx)
        elif mode == "tx_only": Psi_rows.append(Psi_tx)
        else: Psi_rows.append(np.hstack([Psi_tx, Psi_rx]))
    Psi_all = np.vstack(Psi_rows); z_all = np.concatenate(z_rows)
    if mode in ("a_only", "no_null_init"):
        u_tx = np.zeros(Lu_eff, dtype=complex); u_rx = np.zeros(Lu_eff, dtype=complex)
        sig2_est = float(np.real(np.vdot(z_all, z_all)) / max(len(z_all), 1))
    else:
        Gp_u = Psi_all.conj().T @ Psi_all
        u_vec = np.linalg.solve(Gp_u + 1e-2*np.trace(Gp_u).real/max(Gp_u.shape[0],1)*np.eye(Gp_u.shape[0]), Psi_all.conj().T @ z_all)
        res_p = z_all - Psi_all @ u_vec
        sig2_est = float(np.real(np.vdot(res_p, res_p)) / max(len(z_all) - len(u_vec), 1))
        if mode == "rx_only": u_tx = np.zeros(Lu_eff, dtype=complex); u_rx = u_vec
        elif mode == "tx_only": u_tx = u_vec; u_rx = np.zeros(Lu_eff, dtype=complex)
        else: u_tx = u_vec[:Lu_eff]; u_rx = u_vec[Lu_eff:]
        for arr in (u_tx, u_rx):
            nrm = np.sum(np.abs(arr))
            if nrm > 0.55: arr *= (0.55 / nrm)

    # Zero-decision pilot refinement of H_eq after nullspace init!
    if mode not in ("a_only", "no_null_init"):
        sp_eff = sp.copy()
        if mode != "rx_only":
            for m in range(Lu_eff):
                sp_eff += u_tx[m] * sp_conj[(idx - m) % N]
        Phi_pe = (A_plus @ build_bem_pilot_dict(sp_eff, B_bem, L_eq))[guard_obs_idx, :]
        Gpe = Phi_pe.conj().T @ Phi_pe
        Ppe = np.linalg.solve(Gpe + 1e-4*np.trace(Gpe).real/Gpe.shape[0]*np.eye(Gpe.shape[0]), Phi_pe.conj().T)
        if pool_H:
            y_avg = np.mean([(A_plus @ (rx_iqi_invert_fft(r_list[k], u_rx) if mode != "tx_only" else r_list[k]))[guard_obs_idx] for k in range(K)], axis=0)
            H0r = bem_coeffs_to_taps(Ppe @ y_avg, B_bem, L_eq)
            H_taps_list = [H0r.copy() for _ in range(K)]
        else:
            for k in range(K):
                ri = rx_iqi_invert_fft(r_list[k], u_rx) if mode != "tx_only" else r_list[k]
                H_taps_list[k] = bem_coeffs_to_taps(Ppe @ (A_plus @ ri)[guard_obs_idx], B_bem, L_eq)

    xd_pass1 = None
    xd_all = [None] * K
    for outer in range(n_outer):
        inner_iters = 1 if outer == 0 else (2 if outer == 1 else 4)
        s_hat_list, v_td_list, r_inv_list = [], [], []
        for k in range(K):
            r_inv = rx_iqi_invert_fft(r_list[k], u_rx) if mode not in ("a_only", "tx_only") else r_list[k]
            r_inv_list.append(r_inv)
            if mode in ("a_only", "rx_only"):
                Hd_pad = H_taps_list[k]; Hi_taps = np.zeros_like(Hd_pad)
            else:
                Hi_taps = convolve_taps_with_fir(H_taps_list[k], u_tx)
                Hd_pad = np.zeros_like(Hi_taps); Hd_pad[:, :L_eq] = H_taps_list[k]
            xd, m_d, v_d = banded_wl_detect(r_inv, Hd_pad, Hi_taps, A_plus, data_idx, xp_val, const, sig2=max(sig2_est, 1e-4), n_iter=inner_iters)
            xd_all[k] = xd
            x_f = np.zeros(N, dtype=complex); x_f[0] = xp_val; x_f[data_idx] = m_d
            s_hat_list.append(A_plus.conj().T @ x_f)
            v_td_list.append(float(np.sum(v_d)) / N)
        if outer == 0:
            xd_pass1 = [x.copy() for x in xd_all]
        if outer == n_outer - 1:
            break
        utx_n2 = float(np.sum(np.abs(u_tx)**2)) if mode not in ("a_only", "rx_only") else 0.0
        if pool_H:
            Gf_sum = np.zeros((L_eq*Q_bem, L_eq*Q_bem), dtype=complex); rhs_sum = np.zeros(L_eq*Q_bem, dtype=complex)
            P_l = []
            for k in range(K):
                s_eff = s_hat_list[k].copy()
                if mode not in ("a_only", "rx_only"):
                    sc = np.conj(s_hat_list[k])
                    for m in range(Lu_eff): s_eff += u_tx[m] * sc[(idx - m) % N]
                Pf = build_bem_pilot_dict(s_eff, B_bem, L_eq); P_l.append(Pf)
                Gf_sum += Pf.conj().T @ Pf + (v_td_list[k]*(1.0+utx_n2) + 1e-5)*np.eye(L_eq*Q_bem)
                rhs_sum += Pf.conj().T @ r_inv_list[k]
            c_new = np.linalg.solve(Gf_sum, rhs_sum)
            H_new = bem_coeffs_to_taps(c_new, B_bem, L_eq)
            H_taps_list = [H_new.copy() for _ in range(K)]
            hp = float(np.mean(np.sum(np.abs(H_new)**2, axis=1)))
            rsq = sum(max(float(np.real(np.vdot(r_inv_list[k]-P_l[k]@c_new, r_inv_list[k]-P_l[k]@c_new))) - N*v_td_list[k]*hp, 0.1*float(np.real(np.vdot(r_inv_list[k]-P_l[k]@c_new, r_inv_list[k]-P_l[k]@c_new)))) for k in range(K))
            sig2_est = max(rsq / max(K*N - L_eq*Q_bem - (0 if mode=="a_only" else 2*Lu_eff), 1), 1e-5)
        else:
            rsq = 0.0
            for k in range(K):
                s_eff = s_hat_list[k].copy()
                if mode not in ("a_only", "rx_only"):
                    sc = np.conj(s_hat_list[k])
                    for m in range(Lu_eff): s_eff += u_tx[m] * sc[(idx - m) % N]
                Pf = build_bem_pilot_dict(s_eff, B_bem, L_eq)
                c_new = np.linalg.solve(Pf.conj().T @ Pf + (v_td_list[k]*(1.0+utx_n2)+1e-5)*np.eye(L_eq*Q_bem), Pf.conj().T @ r_inv_list[k])
                H_taps_list[k] = bem_coeffs_to_taps(c_new, B_bem, L_eq)
                ek = r_inv_list[k] - Pf @ c_new; e2 = float(np.real(np.vdot(ek, ek)))
                hp = float(np.mean(np.sum(np.abs(H_taps_list[k])**2, axis=1)))
                rsq += max(e2 - N*v_td_list[k]*hp, 0.1*e2)
            sig2_est = max(rsq / max(K*(N - L_eq*Q_bem) - (0 if mode=="a_only" else 2*Lu_eff), 1), 1e-5)
        if mode != "a_only":
            Au, bu, eiv = [], [], 0.0
            for k in range(K):
                yd = apply_taps(H_taps_list[k], s_hat_list[k]); bu.append(r_list[k] - yd)
                sc = np.conj(s_hat_list[k])
                ctx = [apply_taps(H_taps_list[k], sc[(idx - m) % N]) for m in range(Lu_eff)]
                ytx = sum((u_tx[m]*ctx[m] for m in range(Lu_eff)), np.zeros(N, dtype=complex)) if mode != "rx_only" else np.zeros(N, dtype=complex)
                zc = np.conj(yd + ytx)
                crx = [zc[(idx - m) % N] for m in range(Lu_eff)]
                if mode == "rx_only": Au.append(np.column_stack(crx))
                elif mode == "tx_only": Au.append(np.column_stack(ctx))
                else: Au.append(np.hstack([np.column_stack(ctx), np.column_stack(crx)]))
                eiv += N * v_td_list[k] * float(np.mean(np.sum(np.abs(H_taps_list[k])**2, axis=1)))
            Au = np.vstack(Au); bu = np.concatenate(bu)
            Gu = Au.conj().T @ Au + (eiv + 1e-5*np.trace(Au.conj().T @ Au).real/max(Au.shape[1],1))*np.eye(Au.shape[1])
            un = np.linalg.solve(Gu, Au.conj().T @ bu)
            if mode == "rx_only": u_rx = un
            elif mode == "tx_only": u_tx = un
            else: u_tx = un[:Lu_eff]; u_rx = un[Lu_eff:]
            for arr in (u_tx, u_rx):
                nrm = np.sum(np.abs(arr))
                if nrm > 0.55: arr *= (0.55 / nrm)
    return xd_all, xd_pass1, u_tx, u_rx

def huang_burst(r_pre, s_pre, r_list, A_plus, B_bem, data_idx, guard_obs_idx, xp_val, const, L_eq, n_outer, pool_H):
    K = len(r_list); N, Q_bem = B_bem.shape
    Phi_pre = build_bem_pilot_dict(s_pre, B_bem, L_eq); Phi_pre_c = build_bem_pilot_dict(np.conj(s_pre), B_bem, L_eq)
    G0 = Phi_pre.conj().T @ Phi_pre
    c_h = np.linalg.solve(G0 + 1e-6*np.trace(G0).real/G0.shape[0]*np.eye(G0.shape[0]), Phi_pre.conj().T @ r_pre)
    u_tx0, u_rx0 = 0.0+0j, 0.0+0j
    for _ in range(5):
        yd = Phi_pre @ c_h; yi = Phi_pre_c @ c_h
        u2 = np.linalg.lstsq(np.column_stack([yi, np.conj(yd + u_tx0*yi)]), r_pre - yd, rcond=None)[0]
        u_tx0, u_rx0 = u2[0], u2[1]
        ri = (r_pre - u_rx0*np.conj(r_pre)) / max(1.0 - abs(u_rx0)**2, 0.2)
        Pe = build_bem_pilot_dict(s_pre + u_tx0*np.conj(s_pre), B_bem, L_eq)
        Ge = Pe.conj().T @ Pe
        c_h = np.linalg.solve(Ge + 1e-6*np.trace(Ge).real/Ge.shape[0]*np.eye(Ge.shape[0]), Pe.conj().T @ ri)
    ep = ri - Pe @ c_h
    sig2_est = max(float(np.real(np.vdot(ep, ep)) / max(N - L_eq*Q_bem - 2, 1)), 1e-5)
    u_tx = np.array([u_tx0]); u_rx = np.array([u_rx0])

    if pool_H:
        H_taps_list = [bem_coeffs_to_taps(c_h, B_bem, L_eq) for _ in range(K)]
    else:
        # Fair to Huang under continuous Doppler: re-estimate each symbol's H_k from its pilot after flat Rx IQI inv!
        xp = np.zeros(N, dtype=complex); xp[0] = xp_val
        sp = A_plus.conj().T @ xp
        Phi_pe = (A_plus @ build_bem_pilot_dict(sp + u_tx0*np.conj(sp), B_bem, L_eq))[guard_obs_idx, :]
        Gpe = Phi_pe.conj().T @ Phi_pe
        Ppe = np.linalg.solve(Gpe + 1e-4*np.trace(Gpe).real/Gpe.shape[0]*np.eye(Gpe.shape[0]), Phi_pe.conj().T)
        H_taps_list = [bem_coeffs_to_taps(Ppe @ (A_plus @ rx_iqi_invert_fft(r_list[k], u_rx))[guard_obs_idx], B_bem, L_eq) for k in range(K)]

    xd_all = [None] * K
    for outer in range(n_outer):
        inner_iters = 1 if outer == 0 else (2 if outer == 1 else 4)
        s_hat_list, v_td_list, r_inv_list = [], [], []
        for k in range(K):
            r_inv = rx_iqi_invert_fft(r_list[k], u_rx); r_inv_list.append(r_inv)
            Hi_taps = convolve_taps_with_fir(H_taps_list[k], u_tx)
            xd, m_d, v_d = banded_wl_detect(r_inv, H_taps_list[k], Hi_taps, A_plus, data_idx, xp_val, const, sig2=sig2_est, n_iter=inner_iters)
            xd_all[k] = xd
            x_f = np.zeros(N, dtype=complex); x_f[0] = xp_val; x_f[data_idx] = m_d
            s_hat_list.append(A_plus.conj().T @ x_f)
            v_td_list.append(float(np.sum(v_d)) / N)
        if outer == n_outer - 1: break
        utx_n2 = float(abs(u_tx[0])**2)
        if pool_H:
            ri_p = rx_iqi_invert_fft(r_pre, u_rx)
            Ppre = build_bem_pilot_dict(s_pre + u_tx[0]*np.conj(s_pre), B_bem, L_eq)
            Gf = Ppre.conj().T @ Ppre; rhs = Ppre.conj().T @ ri_p; Pl = []
            for k in range(K):
                Pf = build_bem_pilot_dict(s_hat_list[k] + u_tx[0]*np.conj(s_hat_list[k]), B_bem, L_eq); Pl.append(Pf)
                Gf += Pf.conj().T @ Pf + (v_td_list[k]*(1+utx_n2)+1e-5)*np.eye(L_eq*Q_bem)
                rhs += Pf.conj().T @ r_inv_list[k]
            c_new = np.linalg.solve(Gf, rhs); H_new = bem_coeffs_to_taps(c_new, B_bem, L_eq)
            H_taps_list = [H_new.copy() for _ in range(K)]
        else:
            for k in range(K):
                Pf = build_bem_pilot_dict(s_hat_list[k] + u_tx[0]*np.conj(s_hat_list[k]), B_bem, L_eq)
                c_new = np.linalg.solve(Pf.conj().T @ Pf + (v_td_list[k]*(1+utx_n2)+1e-5)*np.eye(L_eq*Q_bem), Pf.conj().T @ r_inv_list[k])
                H_taps_list[k] = bem_coeffs_to_taps(c_new, B_bem, L_eq)
        Au, bu = [], []
        for k in range(K):
            yd = apply_taps(H_taps_list[k], s_hat_list[k]); yt = apply_taps(H_taps_list[k], np.conj(s_hat_list[k]))
            Au.append(np.column_stack([yt, np.conj(yd + u_tx[0]*yt)])); bu.append(r_list[k] - yd)
        u2 = np.linalg.lstsq(np.vstack(Au), np.concatenate(bu), rcond=None)[0]
        u_tx = np.array([u2[0]]); u_rx = np.array([u2[1]])
    return xd_all

def run_trial(args):
    seed, cfg_name, iqi_level, M_qam, snr_db, cont_doppler = args
    rng = np.random.default_rng(seed)
    N = 256; c1 = 7.0 / (2 * N); c2 = 1.0 / (2 * np.sqrt(2) * N)
    A_plus = daft_matrix(N, c1, c2)
    delays = [0, 1, 2]; L_eq = 7; Lu = 4
    Q_bem = 5; NW_bem = 1.0; B_bem = dpss(N, NW_bem, Q_bem).T
    Q_g = 47
    guard_obs_idx = np.array([m % N for m in range(-Q_g, 4)])
    data_idx = np.array([m for m in range(Q_g + 1, N - Q_g)])
    xp_val = np.sqrt(50.0)
    const = qam_constellation(M_qam)

    f1, f2, g1, g2 = generate_iqi_filters(rng, iqi_level, Lf=3, Lg=3)
    sig2 = 10**(-snr_db / 10.0)
    dopplers = rng.uniform(-0.85, 0.85, 3)
    gains = (rng.standard_normal(3) + 1j * rng.standard_normal(3)) * np.sqrt(np.array([0.5, 0.3, 0.2]) / 2)
    gains /= np.linalg.norm(gains)

    L_cpp = max(delays) + len(f1) + len(g1)
    s_pre = A_plus.conj().T @ const[rng.integers(0, M_qam, N)]
    w_pre = np.sqrt(sig2/2)*(rng.standard_normal(N+len(g1)-1)+1j*rng.standard_normal(N+len(g1)-1))
    r_pre = phys_transmit_receive(s_pre, c1, gains, delays, dopplers, f1, f2, g1, g2, w_pre, t_offset=0)

    r_list, tx_list = [], []
    for k in range(4):
        idx_tx = rng.integers(0, M_qam, len(data_idx))
        x = np.zeros(N, dtype=complex); x[0] = xp_val; x[data_idx] = const[idx_tx]
        s = A_plus.conj().T @ x
        w = np.sqrt(sig2/2)*(rng.standard_normal(N+len(g1)-1)+1j*rng.standard_normal(N+len(g1)-1))
        t_off = (k + 1) * (N + L_cpp) if cont_doppler else 0
        r_list.append(phys_transmit_receive(s, c1, gains, delays, dopplers, f1, f2, g1, g2, w, t_offset=t_off))
        tx_list.append(idx_tx)

    pool_H = not cont_doppler
    out = {}
    for m in ["a_only", "flat_joint", "rx_only", "tx_only", "no_null_init", "prop_null_fs"]:
        xd_all, xd_p1, _, _ = solve_burst(r_list, A_plus, B_bem, data_idx, guard_obs_idx, xp_val, const, L_eq, Lu, m, n_outer=6, pool_H=pool_H)
        out[m] = float(np.mean([np.mean(qam_hard(xd_all[k], const)[1] != tx_list[k]) for k in range(4)]))
        if m in ("no_null_init", "prop_null_fs"):
            out[m + "_p1"] = float(np.mean([np.mean(qam_hard(xd_p1[k], const)[1] != tx_list[k]) for k in range(4)]))
    xd_h = huang_burst(r_pre, s_pre, r_list, A_plus, B_bem, data_idx, guard_obs_idx, xp_val, const, L_eq, n_outer=6, pool_H=pool_H)
    out["huang_pre"] = float(np.mean([np.mean(qam_hard(xd_h[k], const)[1] != tx_list[k]) for k in range(4)]))
    return cfg_name, out

if __name__ == "__main__":
    print(f"Python: {sys.executable}", flush=True)
    # 1. Exact single-core timing benchmark at N=128, 256, 512 (Banded WL vs Dense 2N x 2N!)
    rng_t = np.random.default_rng(42)
    print("\n=== [Timing Benchmark: O(N L^2) Interleaved Cyclic-Banded WL vs Dense 2N x 2N (1-core)] ===", flush=True)
    for Nt in [128, 256, 512]:
        Lt = 10  # L_eq=7 + Lu=4 - 1
        Hd = rng_t.standard_normal((Nt, Lt)) + 1j * rng_t.standard_normal((Nt, Lt))
        Hi = 0.15 * (rng_t.standard_normal((Nt, Lt)) + 1j * rng_t.standard_normal((Nt, Lt)))
        rt = rng_t.standard_normal(Nt) + 1j * rng_t.standard_normal(Nt)
        reg = np.full(Nt, 0.05)
        # Warmup
        Bt, Gb = build_interleaved_real_banded(Hd, Hi); fac = cyclic_banded_wl_factor(Gb, reg); sf = cyclic_banded_wl_solve(fac, apply_M_adj(Bt, rt))
        t0 = time.perf_counter()
        for _ in range(10):
            Bt, Gb = build_interleaved_real_banded(Hd, Hi); fac = cyclic_banded_wl_factor(Gb, reg); sf = cyclic_banded_wl_solve(fac, apply_M_adj(Bt, rt))
        tf = (time.perf_counter() - t0) * 100.0
        t0 = time.perf_counter()
        n_rep = 5 if Nt <= 256 else 3
        for _ in range(n_rep):
            Md = np.zeros((2*Nt, 2*Nt))
            for n in range(Nt):
                for l in range(Lt):
                    c = (n - l) % Nt; a, b = Hd[n, l], Hi[n, l]
                    Md[2*n, 2*c] += np.real(a+b); Md[2*n, 2*c+1] += -np.imag(a-b)
                    Md[2*n+1, 2*c] += np.imag(a+b); Md[2*n+1, 2*c+1] += np.real(a-b)
            ri = np.empty(2*Nt); ri[0::2] = np.real(rt); ri[1::2] = np.imag(rt)
            Gd = Md.T @ Md + np.repeat(reg, 2) * np.eye(2*Nt)
            xd = np.linalg.solve(Gd, Md.T @ ri)
        td = (time.perf_counter() - t0) * 1000.0 / n_rep
        sd = xd[0::2] + 1j * xd[1::2]
        print(f"  N={Nt:3d}, L={Lt}: banded={tf:6.2f}ms vs dense={td:7.2f}ms -> speedup={td/tf:5.1f}x, rel_err={np.linalg.norm(sf-sd)/np.linalg.norm(sd):.2e}", flush=True)

    # 2. Parallel 8-core regime probe (16 bursts per regime)
    cfgs = [
        ("C1_strong13dB_block_16QAM_25dB", "strong", 16, 25, False),
        ("C2_strong13dB_block_64QAM_32dB", "strong", 64, 32, False),
        ("C3_mod18dB_contDop_16QAM_28dB",  "mod",    16, 28, True),
        ("C4_strong13dB_contDop_16QAM_28dB","strong", 16, 28, True),
    ]
    tasks = []
    for ci, (cname, lvl, Mq, snr, cdop) in enumerate(cfgs):
        for tr in range(16):
            tasks.append((50000 + ci*1000 + tr, cname, lvl, Mq, snr, cdop))
    t0 = time.perf_counter()
    with Pool(8) as pool:
        res = pool.map(run_trial, tasks)
    print(f"\n=== [8-Core Regime Probe ({len(tasks)} bursts in {time.perf_counter()-t0:.1f}s)] ===", flush=True)
    for cname, *_ in cfgs:
        sub = [r for cn, r in res if cn == cname]
        keys = ["a_only", "huang_pre", "flat_joint", "rx_only", "tx_only", "no_null_init", "prop_null_fs", "no_null_init_p1", "prop_null_fs_p1"]
        vals = {k: np.mean([d[k] for d in sub]) for k in keys}
        print(f"  {cname}:", flush=True)
        print("    Full EM : " + ", ".join(f"{k}={vals[k]:.3e}" for k in keys[:7]), flush=True)
        print(f"    Pass-1 (0-DD): no_null={vals['no_null_init_p1']:.3e} vs prop_null={vals['prop_null_fs_p1']:.3e} (ratio={vals['no_null_init_p1']/max(vals['prop_null_fs_p1'],1e-9):.2f}x)", flush=True)
