import os, sys, json, time, math
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
from scipy.linalg import solveh_banded
from multiprocessing import Pool

# =========================================================================
# Standalone L2 Script for I-20261125-m02 (--parent I-20261125-m01)
# Round 11 [放宽TWC] [轨A-纯通信]: Fully Blind AFDM Dual-End Wiener PN
#   - ZERO simulator truth passed into ANY blind receiver function
#   - Exact projected Jacobian A_O J verified via finite differences (<1e-6)
#   - Exact 72-bin noiseless guard leakage < -25 dB & per-frame energy check
#   - Faithful Xu PIMRC'26 (arXiv:2604.17858) single-end PCA rival
#   - Faithful Gävert TCOM'25 (doi:10.1109/TCOMM.2024.3493814) direct port:
#     (a) Comb pilots + ZeroPN-safe DIC + Eqs.(18)/(28) residual data-cov weighting
#     (b) 1-step first-order Bayesian PCA on EP-AFDM guard band
#   - Includes R4 (100% single-frame blind, NO training frame) &
#     R5 (training frame corrupted by independent dual-end Wiener PN)
#   - Single-knob c1=0 anti-trivial-port readout (identical 72-bin budget & init)
# =========================================================================

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

def build_H_ext(N, L_cpp, hs, ls, nus):
    B = N + L_cpp
    H = np.zeros((N, B), dtype=complex)
    n = np.arange(N)
    for h, l, nu in zip(hs, ls, nus):
        H[n, L_cpp + n - int(l)] += h * np.exp(-1j * 2 * np.pi * nu * n / N)
    return H

def zero_unwrap_complex(z):
    dphi = np.angle(z[1:] * np.conj(z[:-1]))
    phi = np.empty(len(z))
    phi[0] = np.angle(z[0])
    phi[1:] = phi[0] + np.cumsum(dphi)
    return phi

def build_pca_bases(N, L_cpp, K_pca):
    B = N + L_cpp
    idx_r = np.arange(N)
    Cr = np.minimum(idx_r[:, None], idx_r[None, :]).astype(float) + 1.0 + 1e3 * np.ones((N, N))
    ev_r, U_r_all = np.linalg.eigh(Cr)
    Ur = U_r_all[:, -K_pca:][:, ::-1]
    ev_r_top = ev_r[-K_pca:][::-1]

    dt = np.arange(B) - L_cpp
    same_side = (dt[:, None] * dt[None, :]) > 0
    Ct = np.where(same_side, np.minimum(np.abs(dt[:, None]), np.abs(dt[None, :])).astype(float), 0.0)
    ev_t, U_t_all = np.linalg.eigh(Ct)
    Ut = U_t_all[:, -K_pca:][:, ::-1]
    ev_t_top = np.maximum(ev_t[-K_pca:][::-1], 1e-6)
    return Ur, ev_r_top, Ut, ev_t_top

def oamp_exact(y, H_td, Ah_mat, sigma2, pts, data_mask, x_pilot_vec, n_iter=8):
    """Exact payload-masked OAMP. Strictly receives ONLY x_pilot_vec (zero on data_mask)."""
    y_d = y - H_td @ (Ah_mat @ x_pilot_vec)
    Hd = (H_td @ Ah_mat)[:, data_mask]
    Nd = Hd.shape[1]
    U, sv, Vh = np.linalg.svd(Hd, full_matrices=False)
    sv2 = sv ** 2
    Uhy = U.conj().T @ y_d
    v_fl = min(5e-4, max(sigma2 * 0.5, 1e-6))
    r = np.zeros(Nd, dtype=complex)
    v = 1.0
    for _ in range(n_iter):
        lam = sigma2 / max(v, v_fl)
        gain = sv2 / (sv2 + lam)
        xhat_lin = r + Vh.conj().T @ ((sv / (sv2 + lam)) * (Uhy - sv * (Vh @ r)))
        c_bar = min(float(np.sum(gain) / Nd), 0.9999)
        v_post = max(v * (1.0 - c_bar), v_fl)
        r_ext = (xhat_lin - (1.0 - c_bar) * r) / max(c_bar, 1e-6)
        v_ext = max(v_post / max(c_bar, 1e-6), v_fl)
        d2 = np.abs(r_ext[:, None] - pts[None, :]) ** 2 / v_ext
        d2 -= d2.min(axis=1, keepdims=True)
        w = np.exp(-d2)
        w /= w.sum(axis=1, keepdims=True)
        xhat = w @ pts
        vx_vec_raw = np.sum(w * np.abs(pts[None, :] - xhat[:, None]) ** 2, axis=1)
        vx = max(float(np.mean(vx_vec_raw)), v_fl)
        eta = min(vx / v_ext, 0.995)
        r = 0.65 * ((xhat - eta * r_ext) / (1.0 - eta)) + 0.35 * r
        v = 0.65 * max(vx / (1.0 - eta), v_fl) + 0.35 * v
    x_soft = x_pilot_vec.copy(); x_soft[data_mask] = xhat
    x_hard = x_pilot_vec.copy(); x_hard[data_mask] = pts[np.argmin(np.abs(r_ext[:, None] - pts[None, :]) ** 2, axis=1)]
    return x_soft, x_hard, vx, vx_vec_raw

def exact_proj_dual_gn_pca(Y_m, A_m, H_paths, l_paths, s_p_ext, pr_init, pt_init,
                           Sigma_inv, sig_r, sig_t, L_cpp, pca_tuple, n_gn=6):
    """
    Exact projected Gauss-Newton in PCA basis with arbitrary Hermitian precision matrix Sigma_inv
    (scalar 1/sig2 for clean guard band, or exact Gävert Eqs.(18)/(28) residual covariance inverse for comb!).
    Exact projected Jacobian: J = A_m @ [diag(j*yhat)@Ur, sum_p diag(j*er*c_p)@Ut[m_p,:]].
    """
    Ur, ev_r, Ut, ev_t = pca_tuple
    K = Ur.shape[1]; N = len(pr_init)
    ar = Ur.T @ pr_init; at = Ut.T @ pt_init
    Q_prior = np.diag(np.concatenate([1.0 / (ev_r * max(sig_r, 1e-9)), 1.0 / (ev_t * max(sig_t, 1e-9))]))
    n_arr = np.arange(N)
    is_scalar = np.isscalar(Sigma_inv)

    for _ in range(n_gn):
        pr = Ur @ ar; pt = Ut @ at
        er = np.exp(1j * pr); et = np.exp(1j * pt)
        c_taps = []; m_cols = []
        for Hp, lp in zip(H_paths, l_paths):
            mc = L_cpp + n_arr - int(lp)
            c_taps.append(Hp[n_arr, mc] * et[mc] * s_p_ext[mc])
            m_cols.append(mc)
        yhat = er * np.sum(c_taps, axis=0)
        res = Y_m - (A_m @ yhat)
        Jr = A_m @ ((1j * yhat)[:, None] * Ur)
        d_yt = np.zeros((N, K), dtype=complex)
        for c_p, mc in zip(c_taps, m_cols):
            d_yt += (1j * er * c_p)[:, None] * Ut[mc, :]
        Jt = A_m @ d_yt
        J = np.hstack([Jr, Jt])
        if is_scalar:
            w2 = 2.0 * float(Sigma_inv)
            g = Q_prior @ np.concatenate([ar, at]) + w2 * np.real(J.conj().T @ (-res))
            H_gn = Q_prior + w2 * np.real(J.conj().T @ J)
        else:
            WJ = Sigma_inv @ J
            g = Q_prior @ np.concatenate([ar, at]) + 2.0 * np.real(WJ.conj().T @ (-res))
            H_gn = Q_prior + 2.0 * np.real(J.conj().T @ WJ)
        step = -np.linalg.solve(H_gn + 1e-6 * np.eye(2 * K), g)
        max_d = max(float(np.max(np.abs(Ur @ step[:K]))), float(np.max(np.abs(Ut @ step[K:]))), 1e-9)
        if max_d > 0.45:
            step *= (0.45 / max_d)
        ar += step[:K]; at += step[K:]
    return Ur @ ar, Ut @ at

def exact_proj_lumped_gn_pca(Y_m, A_m, H_lin, s_p_ext, phi_init, sig2_obs, sig_tot, L_cpp, pca_tuple, n_gn=6):
    """Published Xu PIMRC'26 (arXiv:2604.17858) style reduced-rank PCA single-end PN estimator (symmetric n_gn)."""
    Ur, ev_r, _, _ = pca_tuple
    K = Ur.shape[1]; N = len(phi_init)
    ar = Ur.T @ phi_init
    Q_prior = np.diag(1.0 / (ev_r * max(sig_tot, 1e-9)))
    u = H_lin @ s_p_ext
    inv_s2 = 2.0 / max(sig2_obs, 1e-6)
    for _ in range(n_gn):
        pr = Ur @ ar; er = np.exp(1j * pr)
        yhat = er * u; res = Y_m - (A_m @ yhat)
        Jr = A_m @ ((1j * yhat)[:, None] * Ur)
        g = Q_prior @ ar + inv_s2 * np.real(Jr.conj().T @ (-res))
        H_gn = Q_prior + inv_s2 * np.real(Jr.conj().T @ Jr)
        step = -np.linalg.solve(H_gn + 1e-6 * np.eye(K), g)
        max_d = max(float(np.max(np.abs(Ur @ step))), 1e-9)
        if max_d > 0.45:
            step *= (0.45 / max_d)
        ar += step
    return Ur @ ar

def gn_dual_banded(y, H_lin, s_ext_hat, phi_r, phi_t_ext, sig2_eff, sig_r, sig_t, L_cpp, n_gn=3):
    N, B = H_lin.shape; pr = phi_r.copy(); pt = phi_t_ext.copy()
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
    active_l = [l for l in range(L_cpp + 1) if np.max(np.abs(H_lin[n_arr, L_cpp + n_arr - l])) > 1e-12]
    H_taps = np.array([H_lin[n_arr, L_cpp + n_arr - l] for l in active_l]); P = len(active_l)
    m_cols = np.array([L_cpp + n_arr - l for l in active_l]); it_cols = idx_t[m_cols]
    inv_s2 = 2.0 / max(sig2_eff, 1e-6)
    for _ in range(n_gn):
        er = np.exp(1j * pr); et = np.exp(1j * pt)
        c_tap = H_taps * (et[m_cols] * s_ext_hat[m_cols])
        yhat = er * np.sum(c_tap, axis=0); res = y - yhat
        g = np.zeros(M_tot)
        g[idx_r[1:]] += inv_sr*(pr[1:]-pr[:-1]); g[idx_r[:-1]] -= inv_sr*(pr[1:]-pr[:-1])
        g[idx_t[1:]] += inv_st*(pt[1:]-pt[:-1]); g[idx_t[:-1]] -= inv_st*(pt[1:]-pt[:-1])
        g[idx_t[L_cpp]] += 1e3 * pt[L_cpp]
        jr = 1j * yhat; g[idx_r] += inv_s2 * np.real(np.conj(jr) * (-res))
        jt = (1j * er)[None, :] * c_tap
        np.add.at(g, it_cols, inv_s2 * np.real(np.conj(jt) * (-res)[None, :]))
        ab = ab_prior.copy(); ab[0, idx_r] += inv_s2 * (np.abs(yhat)**2)
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

def gn_lumped(y, H_circ, s_hat, phi_tot, sig2_eff, sig_pn_tot, n_gn=3):
    N = len(y); u = H_circ @ s_hat; phi = phi_tot.copy()
    inv_s = 1.0 / max(sig_pn_tot, 1e-9); inv_s2 = 2.0 / max(sig2_eff, 1e-6)
    ab_p = np.zeros((2, N))
    ab_p[0,0]=inv_s+1e-6; ab_p[0,-1]=inv_s+1e-6; ab_p[0,1:-1]=2*inv_s+1e-6; ab_p[1,:-1]=-inv_s
    for _ in range(n_gn):
        ep = np.exp(1j * phi)
        g = inv_s2 * np.imag(np.conj(y) * (ep * u))
        g[1:] += inv_s*(phi[1:]-phi[:-1]); g[:-1] -= inv_s*(phi[1:]-phi[:-1])
        ab = ab_p.copy(); ab[0] += inv_s2 * (np.abs(u)**2)
        phi += np.clip(-solveh_banded(ab, g, lower=True), -0.4, 0.4)
    return phi

def refine_channel_sbl_em(y, s_ext_hat, pr, pt, l_hat, nu_hat, gamma_hat, sig2_eff, L_cpp, rho_sbl=0.01, c_sbl=1e-4, d_sbl=1e-4):
    """Xu PIMRC'26 (arXiv:2604.17858) SBL-EM M-step (no artificial clamps on beta/gamma; exact positive root of rho*g^2 + g - (|mu|^2+Sigma) = 0, correcting PDF Eq.13 parenthesis typo where +1 inside 4*rho*(...+1) yields negative gamma for small rho)."""
    N = len(y); n_arr = np.arange(N); P = len(l_hat)
    y_d = y * np.exp(-1j * pr); s_tx = np.exp(1j * pt) * s_ext_hat
    nu_c = nu_hat.copy(); gam = np.maximum(gamma_hat.copy(), 1e-12)
    beta = 1.0 / max(sig2_eff, 1e-12)
    for _ in range(2):
        X = np.column_stack([s_tx[L_cpp + n_arr - int(l)] * np.exp(-1j*2*np.pi*nu_c[p]*n_arr/N) for p, l in enumerate(l_hat)])
        Sigma_h = np.linalg.inv(beta * (X.conj().T @ X) + np.diag(1.0 / gam))
        mu_h = beta * (Sigma_h @ (X.conj().T @ y_d))
        sig_diag = np.maximum(np.real(np.diag(Sigma_h)), 0.0)
        C_beta = float(np.sum(np.abs(y_d - X @ mu_h) ** 2)) + (1.0 / beta) * float(np.sum(1.0 - sig_diag / gam))
        beta = (N + c_sbl - 1.0) / max(d_sbl + C_beta, 1e-12)
        gam = np.maximum((np.sqrt(1.0 + 4.0 * rho_sbl * (np.abs(mu_h) ** 2 + sig_diag)) - 1.0) / (2.0 * rho_sbl), 1e-12)
        for p in range(P):
            res_p = y_d - X @ mu_h + X[:, p] * mu_h[p]
            phi_p = X[:, p] * mu_h[p]
            dphi = (-1j * 2 * np.pi * n_arr / N) * phi_p
            dnu = np.clip(float(np.real(np.vdot(dphi, res_p - phi_p))) / (float(np.real(np.vdot(dphi, dphi))) + 1e-12), -0.08, 0.08)
            nu_c[p] = float(np.clip(nu_c[p] + dnu, -0.5, 0.5))
            X[:, p] = s_tx[L_cpp + n_arr - int(l_hat[p])] * np.exp(-1j*2*np.pi*nu_c[p]*n_arr/N)
    Sigma_h = np.linalg.inv(beta * (X.conj().T @ X) + np.diag(1.0 / gam))
    mu_h = beta * (Sigma_h @ (X.conj().T @ y_d))
    sig_diag = np.maximum(np.real(np.diag(Sigma_h)), 0.0)
    C_beta = float(np.sum(np.abs(y_d - X @ mu_h) ** 2)) + (1.0 / beta) * float(np.sum(1.0 - sig_diag / gam))
    beta = (N + c_sbl - 1.0) / max(d_sbl + C_beta, 1e-12)
    gam = np.maximum((np.sqrt(1.0 + 4.0 * rho_sbl * (np.abs(mu_h) ** 2 + sig_diag)) - 1.0) / (2.0 * rho_sbl), 1e-12)
    return mu_h, nu_c, gam, 1.0 / beta

def refine_channel_blind(y, s_ext_hat, pr, pt, l_hat, nu_hat, L_cpp):
    """100% blind channel refinement (h, nu) given soft data and current (pr, pt)."""
    N = len(y); n_arr = np.arange(N); P = len(l_hat)
    y_d = y * np.exp(-1j * pr); s_tx = np.exp(1j * pt) * s_ext_hat
    nu_c = nu_hat.copy()
    for _ in range(2):
        X = np.column_stack([s_tx[L_cpp + n_arr - int(l)] * np.exp(-1j*2*np.pi*nu_c[p]*n_arr/N) for p, l in enumerate(l_hat)])
        h_c, _, _, _ = np.linalg.lstsq(X, y_d, rcond=None)
        for p in range(P):
            res_p = y_d - X @ h_c + X[:, p] * h_c[p]
            phi_p = X[:, p] * h_c[p]
            dphi = (-1j * 2 * np.pi * n_arr / N) * phi_p
            dnu = np.clip(float(np.real(np.vdot(dphi, res_p - phi_p))) / (float(np.real(np.vdot(dphi, dphi))) + 1e-12), -0.08, 0.08)
            nu_c[p] = float(np.clip(nu_c[p] + dnu, -0.5, 0.5))
            X[:, p] = s_tx[L_cpp + n_arr - int(l_hat[p])] * np.exp(-1j*2*np.pi*nu_c[p]*n_arr/N)
    h_c, _, _, _ = np.linalg.lstsq(X, y_d, rcond=None)
    return h_c, nu_c

def blind_ce_from_training(y_tr, sys_cfg, training_has_pn=False):
    """
    100% BLIND channel + noise estimation from received pilot training frame y_tr.
    NEVER reads any simulator truth!
    When training_has_pn=True, performs blind per-path subband demod + joint dual-PN-aware VarPro!
    """
    N = sys_cfg['N']; L_cpp = sys_cfg['L_cpp']; k_p = sys_cfg['k_p']
    two_Nc1 = sys_cfg['two_Nc1']; A = sys_cfg['A']; Ah = sys_cfg['Ah']
    s_p_ext = sys_cfg['s_p_ext']; n_guard = sys_cfg['n_guard']
    max_hw = sys_cfg['max_hw']; n_arr = np.arange(N)

    Y0 = A @ y_tr
    # Far-from-pilot bins [0:80] (guaranteed far from [k_p - 2Nc1*L_cpp, k_p])
    sig2_init = max(float(np.median(np.abs(Y0[:80]) ** 2) / np.log(2.0)), 1e-7)
    hw_det = 2 if training_has_pn else 1
    en = np.array([float(np.sum(np.abs(Y0[k_p - two_Nc1*l - hw_det : k_p - two_Nc1*l + hw_det + 1]) ** 2)) for l in range(L_cpp + 1)])
    thr = max(12.0 * (2 * hw_det + 1) * sig2_init, 0.04 * float(en.max()))
    if not training_has_pn:
        # Clean training frame: 3-bin windows for adjacent delays are strictly disjoint (two_Nc1 >= 3), so do NOT suppress adjacent true paths!
        cl = [l for l in range(L_cpp + 1) if en[l] > thr]
    else:
        cl = [l for l in range(L_cpp + 1) if en[l] > thr and (l == 0 or en[l] >= en[l-1]) and (l == L_cpp or en[l] >= en[l+1])]
    if not cl: cl = [int(np.argmax(en))]
    cl = np.array(sorted(cl), dtype=int)

    k_cs = [k_p - two_Nc1 * int(l) for l in cl]
    h_c = np.zeros(len(cl), dtype=complex); nu_c = np.zeros(len(cl))
    zp_list = []
    for i, l in enumerate(cl):
        hw_i = max_hw if training_has_pn else 2
        k_hi = min(k_cs[i] + hw_i, (k_cs[i] + k_cs[i-1]) // 2) if i > 0 else k_cs[i] + hw_i
        k_lo = max(k_cs[i] - hw_i, (k_cs[i] + k_cs[i+1]) // 2 + 1) if i < len(cl) - 1 else k_cs[i] - hw_i
        m = np.zeros(N, dtype=bool); m[k_lo : k_hi + 1] = True
        Ys = np.zeros(N, dtype=complex); Ys[m] = Y0[m]
        zp = (Ah @ Ys) * np.conj(s_p_ext[L_cpp + n_arr - l])
        zp_list.append(zp)
        E_sub = max(float(np.sum(np.abs(Y0[m]) ** 2) - m.sum() * sig2_init), 1e-7)
        amp = np.sqrt(E_sub) / np.sqrt(float(n_guard))
        if training_has_pn:
            # Gauge-clean init: avoid freezing training-frame Wiener walk slope into nu_c!
            # Align initial path complex gains at frame midpoint n=N//2 with nu_c=0 before MRC phase unwrap.
            h_c[i] = amp * np.exp(1j * np.angle(np.mean(zp[N//2 - 8 : N//2 + 8])))
            nu_c[i] = 0.0
        else:
            ph = zero_unwrap_complex(zp[L_cpp : N - L_cpp]); ti = n_arr[L_cpp : N - L_cpp]
            sl = np.sum((ti - ti.mean()) * (ph - ph.mean())) / np.sum((ti - ti.mean()) ** 2)
            nu_e = float(np.clip(-sl * N / (2 * np.pi), -0.49, 0.49))
            hc = np.sum(zp[L_cpp : N - L_cpp] * np.exp(1j * 2 * np.pi * nu_e * ti / N)) / np.sum(np.abs(s_p_ext[L_cpp + ti - l]) ** 2)
            h_c[i] = hc
            nu_c[i] = nu_e

    if not training_has_pn:
        for _ in range(3):
            X = np.column_stack([s_p_ext[L_cpp + n_arr - int(l)] * np.exp(-1j * 2 * np.pi * nu_c[i] * n_arr / N) for i, l in enumerate(cl)])
            h_c, _, _, _ = np.linalg.lstsq(X, y_tr, rcond=None)
            for i in range(len(cl)):
                res_i = y_tr - X @ h_c + X[:, i] * h_c[i]
                phi_i = X[:, i] * h_c[i]
                dphi = (-1j * 2 * np.pi * n_arr / N) * phi_i
                dnu = np.clip(float(np.real(np.vdot(dphi, res_i - phi_i))) / (float(np.real(np.vdot(dphi, dphi))) + 1e-12), -0.1, 0.1)
                nu_c[i] = float(np.clip(nu_c[i] + dnu, -0.5, 0.5))
                X[:, i] = s_p_ext[L_cpp + n_arr - int(cl[i])] * np.exp(-1j * 2 * np.pi * nu_c[i] * n_arr / N)
        h_c, _, _, _ = np.linalg.lstsq(X, y_tr, rcond=None)
        res_tr = y_tr - X @ h_c
        sig2_hat = max(float(np.sum(np.abs(res_tr) ** 2) / max(N - 2 * len(cl), 1)), 1e-7)
    else:
        # Gauge-clean alternating blind dual-PN + channel VarPro on the PN-corrupted training frame (shared identically across all arms!)
        B = N + L_cpp
        z_tr = sum(zp_list[i] * np.conj(h_c[i]) for i in range(len(cl)))
        pi = zero_unwrap_complex(z_tr[L_cpp : N - L_cpp])
        pr_tr = np.empty(N); pr_tr[L_cpp:N-L_cpp] = pi; pr_tr[:L_cpp] = pi[0]; pr_tr[N-L_cpp:] = pi[-1]
        pr_tr -= pr_tr[N // 2]
        pt_tr = np.zeros(B)
        h_c, nu_c = refine_channel_blind(y_tr, s_p_ext, pr_tr, pt_tr, cl, nu_c, L_cpp)
        for _ in range(3):
            H_tr = build_H_ext(N, L_cpp, h_c, cl, nu_c)
            pr_tr, pt_tr = gn_dual_banded(y_tr, H_tr, s_p_ext, pr_tr, pt_tr, max(sig2_init, 1e-4),
                                          sys_cfg['sig_r_prior'], sys_cfg['sig_t_prior'], L_cpp, n_gn=3)
            h_c, nu_c = refine_channel_blind(y_tr, s_p_ext, pr_tr, pt_tr, cl, nu_c, L_cpp)
        H_tr = build_H_ext(N, L_cpp, h_c, cl, nu_c)
        res_tr = y_tr - np.exp(1j * pr_tr) * (H_tr @ (np.exp(1j * pt_tr) * s_p_ext))
        sig2_hat = max(float(np.mean(np.abs(res_tr) ** 2)), 1e-6)
    return sig2_hat, cl, h_c, nu_c

def refine_ch_on_pilot_obs(Y_m, A_m, s_p_ext, pr, pt, l_hat, nu_hat, L_cpp, W_inv=None):
    """100% blind channel (h, nu) refinement on observation Y_m given (pr, pt); supports optional covariance weight W_inv."""
    N = len(pr); n_arr = np.arange(N); P = len(l_hat)
    er = np.exp(1j * pr); et_sp = np.exp(1j * pt) * s_p_ext
    nu_c = nu_hat.copy()
    def w_solve(Phi_in):
        if W_inv is None:
            return np.linalg.lstsq(Phi_in, Y_m, rcond=None)[0]
        PhW = Phi_in.conj().T @ W_inv
        return np.linalg.solve(PhW @ Phi_in + 1e-9 * np.eye(P), PhW @ Y_m)
    for _ in range(2):
        cols = [A_m @ (er * et_sp[L_cpp + n_arr - int(l)] * np.exp(-1j * 2 * np.pi * nu_c[p] * n_arr / N)) for p, l in enumerate(l_hat)]
        Phi = np.column_stack(cols)
        h_c = w_solve(Phi)
        for p in range(P):
            res_p = Y_m - Phi @ h_c + Phi[:, p] * h_c[p]
            phi_p = Phi[:, p] * h_c[p]
            dphi = A_m @ (er * et_sp[L_cpp + n_arr - int(l_hat[p])] * ((-1j * 2 * np.pi * n_arr / N) * np.exp(-1j * 2 * np.pi * nu_c[p] * n_arr / N)) * h_c[p])
            Wdphi = dphi if W_inv is None else (W_inv @ dphi)
            dnu = np.clip(float(np.real(np.vdot(Wdphi, res_p - phi_p))) / (float(np.real(np.vdot(dphi, Wdphi))) + 1e-12), -0.08, 0.08)
            nu_c[p] = float(np.clip(nu_c[p] + dnu, -0.5, 0.5))
            Phi[:, p] = A_m @ (er * et_sp[L_cpp + n_arr - int(l_hat[p])] * np.exp(-1j * 2 * np.pi * nu_c[p] * n_arr / N))
    h_c = w_solve(Phi)
    return h_c, nu_c

def blind_single_frame_init(Y_a, sys_cfg):
    """100% single-frame self-contained blind init from Y_a inside guard band ONLY (NO training frame!)."""
    N = sys_cfg['N']; L_cpp = sys_cfg['L_cpp']; k_p = sys_cfg['k_p']
    two_Nc1 = sys_cfg['two_Nc1']; A = sys_cfg['A']; Ah = sys_cfg['Ah']; s_p_ext = sys_cfg['s_p_ext']
    n_guard = sys_cfg['n_guard']; max_hw = sys_cfg['max_hw']; n_arr = np.arange(N)

    en = np.array([float(np.sum(np.abs(Y_a[k_p - two_Nc1*l - 1 : k_p - two_Nc1*l + 2]) ** 2)) for l in range(L_cpp + 1)])
    sig2_init = max(float(np.median(np.sort(en)[:max(1, (L_cpp + 1) // 2)]) / (3.0 * np.log(2.0))), 1e-6)
    thr = max(12.0 * 3 * sig2_init, 0.04 * float(en.max()))
    cl = [l for l in range(L_cpp + 1) if en[l] > thr and (l == 0 or en[l] >= en[l-1]) and (l == L_cpp or en[l] >= en[l+1])]
    if not cl: cl = [int(np.argmax(en))]
    cl = np.array(sorted(cl), dtype=int)

    k_cs = [k_p - two_Nc1 * int(l) for l in cl]
    h_h = np.zeros(len(cl), dtype=complex); nu_h = np.zeros(len(cl)); z_mrc = np.zeros(N, dtype=complex)
    for i, l in enumerate(cl):
        k_hi = min(k_cs[i] + max_hw, (k_cs[i] + k_cs[i-1]) // 2) if i > 0 else k_cs[i] + max_hw
        k_lo = max(k_cs[i] - max_hw, (k_cs[i] + k_cs[i+1]) // 2 + 1) if i < len(cl) - 1 else k_cs[i] - max_hw
        m = np.zeros(N, dtype=bool); m[k_lo : k_hi + 1] = True
        Ys = np.zeros(N, dtype=complex); Ys[m] = Y_a[m]
        zp = (Ah @ Ys) * np.conj(s_p_ext[L_cpp + n_arr - l])
        E_sub = max(float(np.sum(np.abs(Y_a[m]) ** 2) - m.sum() * sig2_init), 1e-6)
        amp = np.sqrt(E_sub) / np.sqrt(float(n_guard))
        ph = zero_unwrap_complex(zp[L_cpp : N - L_cpp]); ti = n_arr[L_cpp : N - L_cpp]
        sl = np.sum((ti - ti.mean()) * (ph - ph.mean())) / np.sum((ti - ti.mean()) ** 2)
        nu_e = float(np.clip(-sl * N / (2 * np.pi), -0.49, 0.49))
        hc = np.sum(zp[L_cpp : N - L_cpp] * np.exp(1j * 2 * np.pi * nu_e * ti / N)) / np.sum(np.abs(s_p_ext[L_cpp + ti - l]) ** 2)
        h_h[i] = amp * np.exp(1j * np.angle(hc)); nu_h[i] = nu_e
        z_mrc += zp * np.conj(h_h[i]) * np.exp(1j * 2 * np.pi * nu_h[i] * n_arr / N)
    pi = zero_unwrap_complex(z_mrc[L_cpp : N - L_cpp])
    phi_mrc = np.empty(N); phi_mrc[L_cpp:N-L_cpp] = pi; phi_mrc[:L_cpp] = pi[0]; phi_mrc[N-L_cpp:] = pi[-1]
    # Jointly align inter-path complex gains & Dopplers on clean pilot_obs using phi_mrc BEFORE Stage 1!
    pilot_obs = sys_cfg['pilot_obs']
    h_h, nu_h = refine_ch_on_pilot_obs(Y_a[pilot_obs], A[pilot_obs, :], s_p_ext, phi_mrc, np.zeros(N + L_cpp), cl, nu_h, L_cpp)
    # Blind noise estimate from pilot-subtracted residual on pilot_obs (removes pilot PN sidelobes cleanly!)
    H_tmp = build_H_ext(N, L_cpp, h_h, cl, nu_h)
    res_pil = Y_a[pilot_obs] - A[pilot_obs, :] @ (np.exp(1j * phi_mrc) * (H_tmp @ s_p_ext))
    sig2_hat = max(float(np.median(np.abs(res_pil) ** 2) / np.log(2.0)), 1e-5)
    return sig2_hat, cl, h_h, nu_h, phi_mrc

def verify_projected_jacobian_fd():
    """Startup self-test: finite-difference check of exact projected Jacobian A_m @ J (<1e-6)."""
    rng = np.random.default_rng(777)
    N = 64; L_cpp = 6; B = N + L_cpp; K = 8; c1 = 2.0 / (2 * N); c2 = 1.0 / (2 * np.pi * N)
    A = daft_matrix(N, c1, c2); Ah = A.conj().T; P_ext = build_cpp_ext(N, c1, L_cpp)
    ls = np.array([0, 2, 5]); hs = np.array([0.6+0.2j, -0.4+0.3j, 0.3-0.4j]); nus = np.array([0.2, -0.3, 0.1])
    H_paths = [build_H_ext(N, L_cpp, [hs[i]], [ls[i]], [nus[i]]) for i in range(3)]
    xp = np.zeros(N, dtype=complex); xp[N // 2] = 4.0; sp = P_ext @ (Ah @ xp)
    Ur, _, Ut, _ = build_pca_bases(N, L_cpp, K)
    obs = np.zeros(N, dtype=bool); obs[18:42] = True; A_m = A[obs, :]
    ar = 0.15 * rng.standard_normal(K); at = 0.15 * rng.standard_normal(K)
    n_arr = np.arange(N)

    def fwd(a_vec):
        pr = Ur @ a_vec[:K]; pt = Ut @ a_vec[K:]
        er = np.exp(1j * pr); et = np.exp(1j * pt)
        u = sum(H_paths[i][n_arr, L_cpp + n_arr - ls[i]] * et[L_cpp + n_arr - ls[i]] * sp[L_cpp + n_arr - ls[i]] for i in range(3))
        return A_m @ (er * u)

    a0 = np.concatenate([ar, at])
    pr = Ur @ ar; pt = Ut @ at; er = np.exp(1j * pr); et = np.exp(1j * pt)
    c_taps = [H_paths[i][n_arr, L_cpp + n_arr - ls[i]] * et[L_cpp + n_arr - ls[i]] * sp[L_cpp + n_arr - ls[i]] for i in range(3)]
    yhat = er * np.sum(c_taps, axis=0)
    Jr = A_m @ ((1j * yhat)[:, None] * Ur)
    d_yt = sum((1j * er * c_taps[i])[:, None] * Ut[L_cpp + n_arr - ls[i], :] for i in range(3))
    J_ana = np.hstack([Jr, A_m @ d_yt])

    eps = 1e-6; J_fd = np.zeros_like(J_ana)
    for j in range(2 * K):
        e = np.zeros(2 * K); e[j] = eps
        J_fd[:, j] = (fwd(a0 + e) - fwd(a0 - e)) / (2.0 * eps)
    rel_err = float(np.linalg.norm(J_ana - J_fd) / np.linalg.norm(J_fd))
    return rel_err

def check_noiseless_leakage(N, L_cpp, two_Nc1, g_lo, g_hi, obs_lo, obs_hi, ls, pdp):
    c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2 * np.pi * N)
    A = daft_matrix(N, c1, c2); Ah = A.conj().T; P = build_cpp_ext(N, c1, L_cpp)
    k_p = N // 2
    guard = np.zeros(N, dtype=bool); guard[g_lo:g_hi] = True; data = ~guard
    obs = np.zeros(N, dtype=bool); obs[obs_lo:obs_hi] = True
    nus = [0.45, -0.45, 0.48][:len(ls)]
    if len(nus) < len(ls): nus = [0.45, -0.45, 0.48, -0.42][:len(ls)]
    H = build_H_ext(N, L_cpp, np.sqrt(pdp), ls, nus) @ P
    Heff = A @ H @ Ah
    E_d_obs = float(np.sum(np.abs(Heff[obs][:, data]) ** 2))
    E_p_obs = float(guard.sum() * np.sum(np.abs(Heff[obs, k_p]) ** 2))
    E_d_full = float(np.sum(np.abs(Heff[guard][:, data]) ** 2))
    E_p_full = float(guard.sum() * np.sum(np.abs(Heff[guard, k_p]) ** 2))
    return float(10 * np.log10(E_d_obs / E_p_obs)), float(10 * np.log10(E_d_full / E_p_full))

def verify_analytical_lumped_bound_suite():
    """
    Zero-fitted-parameter guard-band covariance-corrected analytical lumped floor vs MC
    across 3 realistic multipath fractional-Doppler settings (L=12, L=16, random 4-path).
    """
    cases = [
        ("L12_3path_N512", 512, 12, 4, 184, 328, np.array([0, 5, 12]),     np.array([0.4225, 0.3025, 0.2750]), 1.5e-3),
        ("L16_3path_N512", 512, 16, 3, 180, 334, np.array([0, 7, 16]),     np.array([0.4225, 0.3025, 0.2750]), 1.5e-3),
        ("L8_4path_N256",  256,  8, 3,  84, 180, np.array([0, 2, 5, 8]),   np.array([0.22, 0.18, 0.30, 0.30]),   1.5e-3),
    ]
    out = {}
    rng = np.random.default_rng(2026112599)
    for cname, N, L_cpp, two_Nc1, g_lo, g_hi, ls, pdp, sig_t in cases:
        B = N + L_cpp; n_arr = np.arange(N); w_p = pdp / np.sum(pdp)
        c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2 * np.pi * N)
        A = daft_matrix(N, c1, c2); Ah = A.conj().T; P = build_cpp_ext(N, c1, L_cpp)
        guard = np.zeros(N, dtype=bool); guard[g_lo:g_hi] = True; data = ~guard; Nd = int(data.sum())
        V_d = P @ Ah[:, data]; R_sd = V_d @ V_d.conj().T
        nus = rng.uniform(-0.45, 0.45, len(ls))
        hs = np.sqrt(pdp) * np.exp(1j * rng.uniform(0, 2 * np.pi, len(ls)))
        H_t = build_H_ext(N, L_cpp, hs, ls, nus)

        # Analytical formula 1: EXACT Hermitian quadratic minimizer under guard-band covariance W (0 fitted params!)
        # For z_p = e^{j th_p}, min_t (z - e^{j t} 1)^H W (z - e^{j t} 1) is attained at t* = angle(v^H z)
        # where v = (W @ 1) / (1^H W 1) (exact row-sum weights, strictly tighter than power-only diagonal weights!).
        P_c = len(ls)
        W = np.zeros((P_c, P_c), dtype=complex)
        for p in range(P_c):
            mp = L_cpp + n_arr - ls[p]
            for q in range(P_c):
                mq = L_cpp + n_arr - ls[q]
                W[p, q] = hs[p] * np.conj(hs[q]) * np.mean(np.exp(-1j * 2 * np.pi * (nus[p] - nus[q]) * n_arr / N) * R_sd[mp, mq])
        w_tot = float(np.real(np.sum(W)))
        v_opt = np.sum(W, axis=1) / w_tot  # complex row-sum weights for exact angle(v_opt^T e^{j th})
        # First-order Taylor expansion of angle(sum_p v_opt[p] e^{j th_p}) for real th_p is Re(v_opt)^T th!
        v_phase = np.real(v_opt)
        D = -0.5 * sig_t * np.abs(ls[:, None] - ls[None, :])
        Dv = D @ v_phase; vDv = float(v_phase @ Dv)
        C_cen = D - Dv[:, None] - Dv[None, :] + vDv
        ana_cov = float(np.real(np.sum(W * C_cen)) / w_tot)
        # Analytical formula 2: i.i.d. Jensen lower bound (diagonal approximation)
        delta = 2.0 * sum(w_p[i]*w_p[j]*(1.0 - np.exp(-0.5*sig_t*abs(ls[i]-ls[j]))) for i in range(P_c) for j in range(i+1, P_c))
        ana_jensen = 2.0 * (1.0 - np.sqrt(max(1.0 - delta, 1e-12)))

        # Monte Carlo (250 frames of data & phi_t) using the EXACT optimal data-independent phase angle(sum_p v_opt[p] e^{j th_p})!
        mc_num = 0.0; mc_den = 0.0; genie_num = 0.0
        for _ in range(250):
            pt = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)); pt -= pt[L_cpp]
            xd = np.zeros(N, dtype=complex); xd[data] = (rng.standard_normal(Nd) + 1j * rng.standard_normal(Nd)) / np.sqrt(2.0)
            sd_e = P @ (Ah @ xd)
            y_true = H_t @ (np.exp(1j * pt) * sd_e); y_0 = H_t @ sd_e
            phi_ind = np.angle(sum(v_opt[p] * np.exp(1j * pt[L_cpp - ls[p] : L_cpp - ls[p] + N]) for p in range(P_c)))
            phi_gen = np.angle(y_true * np.conj(y_0))
            mc_num += float(np.sum(np.abs(y_true - np.exp(1j * phi_ind) * y_0) ** 2))
            genie_num += float(np.sum(np.abs(y_true - np.exp(1j * phi_gen) * y_0) ** 2))
            mc_den += float(np.sum(np.abs(y_0) ** 2))
        mc_indep = mc_num / mc_den; mc_genie = genie_num / mc_den
        out[cname] = {
            "ana_cov_db": float(10 * np.log10(ana_cov)),
            "ana_jensen_db": float(10 * np.log10(ana_jensen)),
            "mc_indep_db": float(10 * np.log10(mc_indep)),
            "mc_samplewise_genie_db": float(10 * np.log10(mc_genie)),
            "err_cov_db": float(abs(10 * np.log10(ana_cov / mc_indep))),
            "err_jensen_db": float(abs(10 * np.log10(ana_jensen / mc_indep))),
            "indep_to_genie_ratio": float(mc_indep / mc_genie),
        }
    return out

def run_single_frame(args):
    (seed, cfg) = args
    rng = np.random.default_rng(seed)
    N = cfg['N']; L_cpp = cfg['L_cpp']; B = N + L_cpp; two_Nc1 = cfg['two_Nc1']
    c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2 * np.pi * N)
    snr_db = cfg['snr_db']; sig_r = cfg['sig_r']; sig_t = cfg['sig_t']
    mode = cfg['mode']  # 'prior_clean', 'single_frame', 'prior_pn'
    channel_mode = cfg['channel_mode']
    run_c1_zero = cfg.get('run_c1_zero', False)

    A_a = daft_matrix(N, c1, c2); Ah_a = A_a.conj().T; P_a = build_cpp_ext(N, c1, L_cpp)
    g8 = np.array([-7,-5,-3,-1,1,3,5,7]); pts64 = (g8[:,None] + 1j*g8[None,:]).ravel() / np.sqrt(42.0)
    qpsk = np.array([-1-1j,-1+1j,1-1j,1+1j]) / np.sqrt(2.0)

    k_p = N // 2
    g_lo, g_hi = cfg['g_lo'], cfg['g_hi']
    obs_lo, obs_hi = cfg['obs_lo'], cfg['obs_hi']
    max_hw = cfg['max_hw']
    guard = np.zeros(N, dtype=bool); guard[g_lo:g_hi] = True
    data_mask = ~guard; n_guard = int(guard.sum()); Nd = int(data_mask.sum())
    pilot_obs = np.zeros(N, dtype=bool); pilot_obs[obs_lo:obs_hi] = True

    comb_mask = np.zeros(N, dtype=bool)
    comb_mask[np.round(np.linspace(0, N-1, n_guard, endpoint=False)).astype(int)] = True
    data_comb = ~comb_mask

    x_p = np.zeros(N, dtype=complex); x_p[k_p] = np.sqrt(float(n_guard))
    sp_a = P_a @ (Ah_a @ x_p)
    pca = build_pca_bases(N, L_cpp, K_pca=18 if N == 512 else 14)

    # Fixed nominal PN prior (NEVER reads simulator true sig_r / sig_t!)
    sig_r_prior = 1.5e-3; sig_t_prior = 1.5e-3
    sys_cfg = dict(N=N, L_cpp=L_cpp, two_Nc1=two_Nc1, k_p=k_p, A=A_a, Ah=Ah_a,
                   s_p_ext=sp_a, n_guard=n_guard, max_hw=max_hw, pilot_obs=pilot_obs,
                   sig_r_prior=sig_r_prior, sig_t_prior=sig_t_prior)

    # True channel generation (NEVER passed to any blind receiver!)
    if channel_mode == 'coprime3':
        ls_t = np.array([0, 7, 16]) if L_cpp == 16 else np.array([0, 5, 12])
        pdp = np.array([0.4225, 0.3025, 0.2750])
    else:
        ls_t = np.array([0, int(rng.integers(1, 3)), int(rng.integers(4, 6)), int(rng.integers(7, L_cpp + 1))])
        pdp = np.array([0.22, 0.18, 0.30, 0.30])
    P_cnt = len(ls_t); w_p = pdp / np.sum(pdp)
    nus_t = rng.uniform(-0.4, 0.4, P_cnt)
    hs_t = np.sqrt(pdp) * np.exp(1j * rng.uniform(0, 2 * np.pi, P_cnt))
    H_lin_t = build_H_ext(N, L_cpp, hs_t, ls_t, nus_t)
    sig2_true = 10.0 ** (-snr_db / 10.0)

    # Current data frame PN, noise, and IDENTICAL data symbols across all arms
    phi_t = np.cumsum(np.sqrt(sig_t)*rng.standard_normal(B)) if sig_t > 0 else np.zeros(B); phi_t -= phi_t[L_cpp]
    phi_r = np.cumsum(np.sqrt(sig_r)*rng.standard_normal(N)) if sig_r > 0 else np.zeros(N)
    w = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    xd_vals = pts64[rng.integers(0, 64, Nd)]

    # Generate EP-AFDM transmitted and received signal
    x_a = x_p.copy(); x_a[data_mask] = xd_vals
    s_ext_a = P_a @ (Ah_a @ x_a)
    y_a = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ext_a)) + w
    Y_a = A_a @ y_a

    # Generate Comb-AFDM transmitted and received signal (exact same Nd, exact same xd_vals, exact same pilot power n_guard!)
    x_c = np.zeros(N, dtype=complex); x_c[data_comb] = xd_vals; x_c[comb_mask] = qpsk[rng.integers(0, 4, n_guard)]
    xp_c = np.where(comb_mask, x_c, 0.0); sp_c = P_a @ (Ah_a @ xp_c)
    s_ext_c = P_a @ (Ah_a @ x_c)
    y_c = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ext_c)) + w

    energy_ratio_comb_to_ep = float(np.sum(np.abs(s_ext_c) ** 2) / np.sum(np.abs(s_ext_a) ** 2))
    base_energy_diff = float(abs(np.sum(np.abs(x_c) ** 2) - np.sum(np.abs(x_a) ** 2)))

    # === 100% BLIND CHANNEL & NOISE INITIALIZATION (ZERO SIMULATOR TRUTH!) ===
    refine_ch_in_loop = (mode in ('single_frame', 'prior_pn'))
    if mode == 'single_frame':
        sig2_hat, l_h, h_h, nu_h, phi_mrc = blind_single_frame_init(Y_a, sys_cfg)
    else:
        w_tr = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        if mode == 'prior_pn' and (sig_r > 0 or sig_t > 0):
            pt_tr = np.cumsum(np.sqrt(sig_t)*rng.standard_normal(B)); pt_tr -= pt_tr[L_cpp]
            pr_tr = np.cumsum(np.sqrt(sig_r)*rng.standard_normal(N))
            y_tr = np.exp(1j * pr_tr) * (H_lin_t @ (np.exp(1j * pt_tr) * sp_a)) + w_tr
            sig2_hat, l_h, h_h, nu_h = blind_ce_from_training(y_tr, sys_cfg, training_has_pn=True)
        else:
            y_tr = H_lin_t @ sp_a + w_tr
            sig2_hat, l_h, h_h, nu_h = blind_ce_from_training(y_tr, sys_cfg, training_has_pn=False)
        # Path-demux constant-envelope MRC phase warm-start on current frame Y_a
        H_p0 = [build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]
        k_cs = [k_p - two_Nc1 * int(l) for l in l_h]
        z_mrc = np.zeros(N, dtype=complex)
        for i in range(len(l_h)):
            k_hi = min(k_cs[i] + max_hw, (k_cs[i] + k_cs[i-1]) // 2) if i > 0 else k_cs[i] + max_hw
            k_lo = max(k_cs[i] - max_hw, (k_cs[i] + k_cs[i+1]) // 2 + 1) if i < len(l_h) - 1 else k_cs[i] - max_hw
            m = np.zeros(N, dtype=bool); m[k_lo : k_hi + 1] = True
            Ys = np.zeros(N, dtype=complex); Ys[m] = Y_a[m]
            z_mrc += (Ah_a @ Ys) * np.conj(H_p0[i] @ sp_a)
        pi = zero_unwrap_complex(z_mrc[L_cpp : N - L_cpp])
        phi_mrc = np.empty(N); phi_mrc[L_cpp:N-L_cpp] = pi; phi_mrc[:L_cpp] = pi[0]; phi_mrc[N-L_cpp:] = pi[-1]

    H_lin_h = build_H_ext(N, L_cpp, h_h, l_h, nu_h); H_circ_h = H_lin_h @ P_a
    H_paths_h = [build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]

    def run_dual_outer(y_in, P_i, Ah_i, dm_i, xp_i, pr0, pt0, h0, nu0):
        pr_c, pt_c = pr0.copy(), pt0.copy()
        h_c, nu_c = h0.copy(), nu0.copy()
        s2 = sig2_hat
        best_r = np.inf; best_xh = None
        for out in range(6):
            Hl = build_H_ext(N, L_cpp, h_c, l_h, nu_c)
            Hc = np.exp(1j * pr_c)[:, None] * ((Hl * np.exp(1j * pt_c)[None, :]) @ P_i)
            xs, xhc, vx, _ = oamp_exact(y_in, Hc, Ah_i, max(s2, 1e-6) + 0.02 * (0.6 ** out), pts64, dm_i, xp_i, 8)
            s_ext_s = P_i @ (Ah_i @ xs)
            pr_c, pt_c = gn_dual_banded(y_in, Hl, s_ext_s, pr_c, pt_c, max(s2, 1e-6) + 0.5 * vx, sig_r_prior, sig_t_prior, L_cpp, 3)
            if refine_ch_in_loop and out >= 1:
                h_c, nu_c = refine_channel_blind(y_in, s_ext_s, pr_c, pt_c, l_h, nu_c, L_cpp)
            Hl2 = build_H_ext(N, L_cpp, h_c, l_h, nu_c)
            rc = float(np.sum(np.abs(y_in - np.exp(1j * pr_c) * (Hl2 @ (np.exp(1j * pt_c) * (P_i @ (Ah_i @ xhc))))) ** 2))
            s2_floor = 1e-5 if refine_ch_in_loop else max(sig2_hat * 0.4, 1e-6)
            s2 = float(np.clip(rc / N, s2_floor, 0.05))
            if rc < best_r: best_r = rc; best_xh = xhc
        return best_xh

    def ser(xh, xt, dm): return float(np.mean(np.abs(xh[dm] - xt[dm]) > 1e-3))

    out = {"energy_ratio_comb_to_ep": energy_ratio_comb_to_ep, "base_energy_diff": base_energy_diff}
    ref_all = H_circ_h @ (Ah_a @ x_p)
    phi_cpe = np.full(N, np.angle(np.vdot(ref_all, y_a)))

    # 1) AFDM_Uncomp (Sui TCOM'26 passive blind)
    _, xhu, _, _ = oamp_exact(y_a, H_circ_h, Ah_a, sig2_hat, pts64, data_mask, x_p, 8)
    out['AFDM_Uncomp'] = ser(xhu, x_a, data_mask)

    # 2) AFDM_Xu_LumpPCA_Sym6 (Xu PIMRC'26 / arXiv:2604.17858 reduced-rank PCA single-end PN + Eq.13 SBL-EM + IDENTICAL best-residual 6-outer loop!)
    if refine_ch_in_loop:
        phi_l = exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_lin_h, sp_a, phi_mrc,
                                         max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 3)
        hl_c, nul_c = refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, phi_l, np.zeros(B), l_h, nu_h, L_cpp)
        phi_l = exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], build_H_ext(N, L_cpp, hl_c, l_h, nul_c), sp_a, phi_l,
                                         max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 3)
    else:
        phi_l = exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_lin_h, sp_a, phi_mrc,
                                         max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 6)
        hl_c, nul_c = h_h.copy(), nu_h.copy()
    s2l = sig2_hat
    gam_l = np.maximum(np.abs(hl_c) ** 2, 1e-3)
    best_rl = np.inf; best_xhl = None
    for out_i in range(6):
        Hcl = build_H_ext(N, L_cpp, hl_c, l_h, nul_c) @ P_a
        xs_l, xhc_l, vxl, _ = oamp_exact(y_a * np.exp(-1j * phi_l), Hcl, Ah_a, max(s2l, 1e-6) + 0.02 * (0.6 ** out_i), pts64, data_mask, x_p, 8)
        # Xu PIMRC'26 (arXiv:2604.17858) Eq. (13): joint reduced-rank single-end PN + SBL-EM channel, gamma & beta update!
        phi_l = gn_lumped(y_a, Hcl, Ah_a @ xs_l, phi_l, max(s2l, 1e-6) + 0.5 * vxl, sig_r_prior + sig_t_prior, 3)
        if out_i >= 1:
            hl_c, nul_c, gam_l, s2l_em = refine_channel_sbl_em(y_a, P_a @ (Ah_a @ xs_l), phi_l, np.zeros(B), l_h, nul_c, gam_l, max(s2l, 1e-6) + 0.5 * vxl, L_cpp)
        else:
            s2l_em = s2l
        Hcl2 = build_H_ext(N, L_cpp, hl_c, l_h, nul_c) @ P_a
        rl_hard = float(np.sum(np.abs(y_a * np.exp(-1j * phi_l) - Hcl2 @ (Ah_a @ xhc_l)) ** 2))
        s2l_floor = 1e-5 if refine_ch_in_loop else max(sig2_hat * 0.4, 1e-6)
        s2l = float(np.clip(max(s2l_em, rl_hard / N), s2l_floor, 0.05))
        if rl_hard < best_rl:
            best_rl = rl_hard; best_xhl = xhc_l
    out['AFDM_Xu_LumpPCA_Sym6'] = ser(best_xhl, x_a, data_mask)

    # 3) AFDM_Gavert_Guard_1Step (Gävert TCOM'25 Eqs.(18)/(28) 1-step first-order Bayesian PCA around CPE on EP-AFDM guard,
    #    using FULL signal s_est_g1 AND exact unclamped per-symbol posterior variance vector vx_g1_vec in Sigma_g1!)
    xs_g1, _, _, vx_g1_vec = oamp_exact(y_a * np.exp(-1j * phi_cpe), H_circ_h, Ah_a, max(sig2_hat, 1e-4) + 0.02, pts64, data_mask, x_p, 8)
    s_est_g1 = P_a @ (Ah_a @ xs_g1)
    M_gd = (A_a[pilot_obs, :] @ H_circ_h) @ Ah_a[:, data_mask]
    Sigma_g1 = max(sig2_hat, 1e-6) * np.eye(int(pilot_obs.sum())) + (M_gd * vx_g1_vec[None, :]) @ M_gd.conj().T
    pr_g1, pt_g1 = exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, s_est_g1,
                                          phi_cpe, np.zeros(B), np.linalg.inv(Sigma_g1), sig_r_prior, sig_t_prior, L_cpp, pca, 1)
    out['AFDM_Gavert_Guard_1Step'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_g1, pt_g1, h_h, nu_h), x_a, data_mask)

    # 4) AFDM_EP_CPE_GN6 (Honest ablation: EP-AFDM guard + symmetric 6 exact projected GN starting from CPE)
    if refine_ch_in_loop:
        pr_c6, pt_c6 = exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                              phi_cpe, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        hc_c6, nuc_c6 = refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, pr_c6, pt_c6, l_h, nu_h, L_cpp)
        Hp_c6 = [build_H_ext(N, L_cpp, [hc_c6[i]], [l_h[i]], [nuc_c6[i]]) for i in range(len(l_h))]
        pr_c6, pt_c6 = exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], Hp_c6, l_h, sp_a,
                                              pr_c6, pt_c6, 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        out['AFDM_EP_CPE_GN6'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_c6, pt_c6, hc_c6, nuc_c6), x_a, data_mask)
    else:
        pr_c6, pt_c6 = exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                              phi_cpe, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        out['AFDM_EP_CPE_GN6'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_c6, pt_c6, h_h, nu_h), x_a, data_mask)

    # 5) AFDM_EP_Dual_Sym6 (OUR PROPOSED: per-path constant-envelope MRC + symmetric 6 exact projected PCA-GN!)
    if refine_ch_in_loop:
        # 3 GN -> pilot-subspace channel realignment -> 3 GN (exact symmetric 6 total GN steps, shared identically with Xu & EP_CPE!)
        pr_ep, pt_ep = exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                              phi_mrc, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        h_sf2, nu_sf2 = refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, pr_ep, pt_ep, l_h, nu_h, L_cpp)
        H_p_sf2 = [build_H_ext(N, L_cpp, [h_sf2[i]], [l_h[i]], [nu_sf2[i]]) for i in range(len(l_h))]
        pr_ep, pt_ep = exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_p_sf2, l_h, sp_a,
                                              pr_ep, pt_ep, 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        out['AFDM_EP_Dual_Sym6'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_ep, pt_ep, h_sf2, nu_sf2), x_a, data_mask)
    else:
        pr_ep, pt_ep = exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                              phi_mrc, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        out['AFDM_EP_Dual_Sym6'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_ep, pt_ep, h_h, nu_h), x_a, data_mask)

    # 6) AFDM_Gavert_Comb_CovDIC6 (Gävert TCOM'25 direct port F_N->A: comb pilots + ZeroPN-safe preliminary data est
    #    + Gävert Eqs.(18)/(28) FULL-SIGNAL Jacobian using BOTH pilot + estimated data s_est_ext AND exact residual data-cov Sigma_inv!)
    #    In single_frame mode, strictly NO cross-frame borrowing of y_a: estimate blind CSI directly from y_c via comb-pilot OMP!
    if mode == 'single_frame':
        # Blind delay & gain estimation strictly from y_c using comb pilot waveform sp_c (zero borrowing of y_a!)
        n_arr = np.arange(N)
        corr_c = np.array([abs(np.vdot(sp_c[L_cpp + n_arr - l], y_c)) ** 2 for l in range(L_cpp + 1)])
        l_comb = np.sort(np.argsort(corr_c)[-3:]).astype(int)
        Phi_c = np.column_stack([sp_c[L_cpp + n_arr - int(l)] for l in l_comb])
        h_comb, _, _, _ = np.linalg.lstsq(Phi_c, y_c, rcond=None)
        nu_comb = np.zeros(len(l_comb))
        H_lin_c = build_H_ext(N, L_cpp, h_comb, l_comb, nu_comb); H_circ_c = H_lin_c @ P_a
        H_paths_c = [build_H_ext(N, L_cpp, [h_comb[i]], [l_comb[i]], [nu_comb[i]]) for i in range(len(l_comb))]
        s2_c_init = max(float(np.mean(np.abs(y_c - Phi_c @ h_comb) ** 2)) * 0.05, 1e-3)
    else:
        l_comb, h_comb, nu_comb = l_h, h_h, nu_h
        H_lin_c, H_circ_c, H_paths_c = H_lin_h, H_circ_h, H_paths_h
        s2_c_init = sig2_hat

    pcc = np.full(N, np.angle(np.vdot(H_circ_c @ (Ah_a @ xp_c), y_c)))
    xs_0, _, _, vx_0_vec = oamp_exact(y_c * np.exp(-1j * pcc), H_circ_c, Ah_a, max(s2_c_init, 1e-4) + 0.02, pts64, data_comb, xp_c, 8)
    # Gävert Eqs.(18)/(28): full waveform s_est_ext AND exact unclamped per-symbol posterior variance diag(vx_0_vec) in Sigma_res!
    s_est_ext_c = P_a @ (Ah_a @ xs_0)
    M_cd = (A_a[comb_mask, :] @ H_circ_c) @ Ah_a[:, data_comb]
    Sigma_res = max(s2_c_init, 1e-6) * np.eye(n_guard) + (M_cd * vx_0_vec[None, :]) @ M_cd.conj().T
    Sigma_inv = np.linalg.inv(Sigma_res)
    Y_comb_obs = (A_a @ y_c)[comb_mask]
    if refine_ch_in_loop:
        # Symmetric 3 GN -> covariance-weighted comb-obs channel realignment (own comb obs ONLY!) -> 3 GN (exact 6 total!)
        pr_gc, pt_gc = exact_proj_dual_gn_pca(Y_comb_obs, A_a[comb_mask, :], H_paths_c, l_comb, s_est_ext_c,
                                              pcc, np.zeros(B), Sigma_inv, sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        hc_c, nuc_c = refine_ch_on_pilot_obs(Y_comb_obs, A_a[comb_mask, :], s_est_ext_c, pr_gc, pt_gc, l_comb, nu_comb, L_cpp, W_inv=Sigma_inv)
        Hp_c2 = [build_H_ext(N, L_cpp, [hc_c[i]], [l_comb[i]], [nuc_c[i]]) for i in range(len(l_comb))]
        pr_gc, pt_gc = exact_proj_dual_gn_pca(Y_comb_obs, A_a[comb_mask, :], Hp_c2, l_comb, s_est_ext_c,
                                              pr_gc, pt_gc, Sigma_inv, sig_r_prior, sig_t_prior, L_cpp, pca, 3)
    else:
        pr_gc, pt_gc = exact_proj_dual_gn_pca(Y_comb_obs, A_a[comb_mask, :], H_paths_c, l_comb, s_est_ext_c,
                                              pcc, np.zeros(B), Sigma_inv, sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        hc_c, nuc_c = h_comb.copy(), nu_comb.copy()
    # Run symmetric 6-outer loop using Comb arm's OWN (l_comb, hc_c, nuc_c)
    pr_c, pt_c = pr_gc.copy(), pt_gc.copy(); s2c = s2_c_init
    best_rc = np.inf; best_xhc = None
    for out_i in range(6):
        Hl_c = build_H_ext(N, L_cpp, hc_c, l_comb, nuc_c)
        Hc_c = np.exp(1j * pr_c)[:, None] * ((Hl_c * np.exp(1j * pt_c)[None, :]) @ P_a)
        xs_c, xhc_c, vxc, _ = oamp_exact(y_c, Hc_c, Ah_a, max(s2c, 1e-6) + 0.02 * (0.6 ** out_i), pts64, data_comb, xp_c, 8)
        s_ext_sc = P_a @ (Ah_a @ xs_c)
        pr_c, pt_c = gn_dual_banded(y_c, Hl_c, s_ext_sc, pr_c, pt_c, max(s2c, 1e-6) + 0.5 * vxc, sig_r_prior, sig_t_prior, L_cpp, 3)
        if refine_ch_in_loop and out_i >= 1:
            hc_c, nuc_c = refine_channel_blind(y_c, s_ext_sc, pr_c, pt_c, l_comb, nuc_c, L_cpp)
        Hl_c2 = build_H_ext(N, L_cpp, hc_c, l_comb, nuc_c)
        rc = float(np.sum(np.abs(y_c - np.exp(1j * pr_c) * (Hl_c2 @ (np.exp(1j * pt_c) * (P_a @ (Ah_a @ xhc_c))))) ** 2))
        s2c = float(np.clip(rc / N, 1e-5 if refine_ch_in_loop else max(s2_c_init * 0.4, 1e-6), 0.05))
        if rc < best_rc: best_rc = rc; best_xhc = xhc_c
    out['AFDM_Gavert_Comb_CovDIC6'] = ser(best_xhc, x_c, data_comb)

    # 7) Single-knob c1=0 anti-trivial-port readout (ONLY c1 toggled to 0; IDENTICAL CPE warm-start as AFDM_EP_CPE_GN6,
    #    SAME 6 init + 6 outer! Reports BOTH OFDM's own centered 72-bin window [220:292] AND exact same index mask [196:268]!)
    if run_c1_zero:
        A_o = daft_matrix(N, 0.0, c2); Ah_o = A_o.conj().T; P_o = build_cpp_ext(N, 0.0, L_cpp)
        sp_o = P_o @ (Ah_o @ x_p)
        x_o = x_p.copy(); x_o[data_mask] = xd_vals
        s_ext_o = P_o @ (Ah_o @ x_o)
        y_o = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ext_o)) + w
        Y_o = A_o @ y_o
        phi_o_cpe = np.full(N, np.angle(np.vdot((H_lin_h @ P_o) @ (Ah_o @ x_p), y_o)))
        # (a) OFDM-centered 72-bin obs window [220:292] (strictly favorable to c1=0), identical CPE warm-start as AFDM_EP_CPE_GN6!
        n_obs = obs_hi - obs_lo
        obs_o_cen = np.zeros(N, dtype=bool); obs_o_cen[k_p - n_obs // 2 : k_p + n_obs - n_obs // 2] = True
        pr_o, pt_o = exact_proj_dual_gn_pca(Y_o[obs_o_cen], A_o[obs_o_cen, :], H_paths_h, l_h, sp_o,
                                            phi_o_cpe, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        out['OFDM_c1=0_SingleKnob_Sym6'] = ser(run_dual_outer(y_o, P_o, Ah_o, data_mask, x_p, pr_o, pt_o, h_h, nu_h), x_o, data_mask)
        # (b) Exact identical index mask pilot_obs [196:268] with identical CPE warm-start
        pr_o2, pt_o2 = exact_proj_dual_gn_pca(Y_o[pilot_obs], A_o[pilot_obs, :], H_paths_h, l_h, sp_o,
                                              phi_o_cpe, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        out['OFDM_c1=0_SameMask_Sym6'] = ser(run_dual_outer(y_o, P_o, Ah_o, data_mask, x_p, pr_o2, pt_o2, h_h, nu_h), x_o, data_mask)
        Ho_o = np.exp(1j * phi_r)[:, None] * ((H_lin_t * np.exp(1j * phi_t)[None, :]) @ P_o)
        _, xhdo_o, _, _ = oamp_exact(y_o, Ho_o, Ah_o, sig2_true, pts64, data_mask, x_p, 10)
        out['OFDM_c1=0_DualOrac'] = ser(xhdo_o, x_o, data_mask)

    # 8) Oracles (EXACT per-sample local Hermitian optimal weights Wn_o[n] AND exact local receiver-side variance!)
    n_arr_o = np.arange(N)
    V_d_o = P_a @ Ah_a[:, data_mask]  # (B, Nd)
    path_o = np.stack([H_lin_t[n_arr_o, L_cpp + n_arr_o - int(l), None] * V_d_o[L_cpp + n_arr_o - int(l), :] for l in ls_t], axis=1)  # (N, P, Nd)
    Wn_o = np.einsum('npk,nqk->npq', path_o, np.conj(path_o))  # exact per-sample (N, P, P) Hermitian covariance!
    v_n_o = np.sum(Wn_o, axis=2)  # exact per-sample local row-sum optimal weights (N, P)
    local_w = v_n_o.real / v_n_o.real.sum(axis=1, keepdims=True)
    D_o = -0.5 * sig_t * np.abs(ls_t[:, None] - ls_t[None, :])
    Dv_loc = local_w @ D_o
    C_loc = D_o[None, :, :] - Dv_loc[:, :, None] - Dv_loc[:, None, :] + np.sum(Dv_loc * local_w, axis=1)[:, None, None]
    # Exact local receiver-side irreducible interference variance (unnormalized, matching y_a noise scale!)
    sig2_irred_rx = float(np.sum(Wn_o.real * C_loc, axis=(1, 2)).mean())
    z_pt = np.stack([np.exp(1j * phi_t[L_cpp - int(l) : L_cpp - int(l) + N]) for l in ls_t], axis=1)  # (N, P)
    phi_ind = phi_r + np.angle(np.sum(v_n_o * z_pt, axis=1))
    _, xhlo, _, _ = oamp_exact(y_a * np.exp(-1j * phi_ind), H_lin_t @ P_a, Ah_a, sig2_true + sig2_irred_rx, pts64, data_mask, x_p, 10)
    out['AFDM_LumpOrac_Indep'] = ser(xhlo, x_a, data_mask)

    Ho_a = np.exp(1j * phi_r)[:, None] * ((H_lin_t * np.exp(1j * phi_t)[None, :]) @ P_a)
    _, xhdo, _, _ = oamp_exact(y_a, Ho_a, Ah_a, sig2_true, pts64, data_mask, x_p, 10)
    out['AFDM_DualOrac'] = ser(xhdo, x_a, data_mask)

    return out

def summarize_regime(rows, ref_key='AFDM_EP_Dual_Sym6'):
    keys = [k for k in rows[0].keys() if not k.startswith('energy_') and not k.startswith('base_')]
    n = len(rows)
    s = {"n_frames": n, "means": {}, "lock_loss_gt5pct": {}, "paired_diff_vs_ref": {},
         "energy_ratio_mean": float(np.mean([r["energy_ratio_comb_to_ep"] for r in rows])),
         "energy_ratio_std": float(np.std([r["energy_ratio_comb_to_ep"] for r in rows])),
         "max_base_energy_diff": float(np.max([r["base_energy_diff"] for r in rows]))}
    ref_arr = np.array([r[ref_key] for r in rows])
    for k in keys:
        arr = np.array([r[k] for r in rows])
        s["means"][k] = float(np.mean(arr))
        s["lock_loss_gt5pct"][k] = float(np.mean(arr > 0.05))
        d = arr - ref_arr
        ci = 1.96 * float(np.std(d, ddof=1)) / math.sqrt(n) if n > 1 else 0.0
        s["paired_diff_vs_ref"][k] = {"mean": float(np.mean(d)), "ci95": ci}
    return s

def main():
    print(sys.executable, flush=True)
    smoke = ("--smoke" in sys.argv)
    n_workers = 1 if smoke else min(8, os.cpu_count() or 4)  # STRICT <= 8 cores on deinlab!
    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "/tmp/summary_m_r11_m03.json"

    t0 = time.time()
    fd_err = verify_projected_jacobian_fd()
    leak_512_obs, leak_512_full = check_noiseless_leakage(512, 16, 3, 180, 334, 196, 268, [0, 7, 16], [0.4225, 0.3025, 0.2750])
    leak_256_obs, leak_256_full = check_noiseless_leakage(256,  8, 3,  84, 180,  98, 136, [0, 2, 5, 8], [0.22, 0.18, 0.30, 0.30])
    print(f"[STARTUP GATES] FD_jac_rel_err={fd_err:.2e} | Leak_N512(72-bin obs)={leak_512_obs:.2f} dB (full guard={leak_512_full:.2f} dB) | Leak_N256(38-bin obs)={leak_256_obs:.2f} dB", flush=True)

    bound_suite = verify_analytical_lumped_bound_suite()
    for bk, bv in bound_suite.items():
        print(f"[BOUND {bk}] ana_cov={bv['ana_cov_db']:.2f} dB vs MC={bv['mc_indep_db']:.2f} dB (err={bv['err_cov_db']:.3f} dB) | genie_ratio={bv['indep_to_genie_ratio']:.2f}x", flush=True)

    regimes = [
        ("R0_ZeroPN_30dB",            dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=30.0, sig_r=0.0,    sig_t=0.0,    mode='prior_clean',  channel_mode='coprime3', n_frames=2 if smoke else 24)),
        ("R1_N512_30dB_2e3",          dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=30.0, sig_r=1.0e-3, sig_t=1.0e-3, mode='prior_clean',  channel_mode='coprime3', n_frames=2 if smoke else 60)),
        ("R2_N512_30dB_3e3",          dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='prior_clean',  channel_mode='coprime3', n_frames=2 if smoke else 80)),
        ("R3_N512_45dB_3e3_Floor",    dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=45.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='prior_clean',  channel_mode='coprime3', n_frames=2 if smoke else 80, run_c1_zero=True)),
        ("R4_SingleFrameBlind_3e3",   dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='single_frame', channel_mode='coprime3', n_frames=2 if smoke else 60)),
        ("R5_PNTrain_30dB_3e3",       dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='prior_pn',     channel_mode='coprime3', n_frames=2 if smoke else 60)),
        ("R6_Rand4_N256_30dB_3e3",    dict(N=256, L_cpp=8,  two_Nc1=3, g_lo=84,  g_hi=180, obs_lo=98,  obs_hi=136, max_hw=5, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='prior_clean',  channel_mode='rand4',    n_frames=2 if smoke else 60)),
    ]

    results = {
        "meta": {"card": "I-20261125-m03", "parent": "I-20261125-m02", "group": "[放宽TWC]", "track": "[轨A-纯通信]",
                 "smoke": smoke, "n_workers": n_workers, "python": sys.executable, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
        "startup_gates": {
            "fd_jacobian_rel_err": fd_err,
            "leak_n512_obs72_db": leak_512_obs,
            "leak_n512_full_guard_db": leak_512_full,
            "leak_n256_obs38_db": leak_256_obs,
            "leak_n256_full_guard_db": leak_256_full,
        },
        "analytical_lumped_bound": bound_suite,
        "regimes": {},
    }

    for idx_r, (rname, rcfg) in enumerate(regimes):
        tr = time.time()
        nf = rcfg['n_frames']
        # Fresh unseen seeds strictly disjoint from m02 (2026112511..2026172570) and all dev probes (1000..50000)!
        tasks = [(2027000001 + idx_r * 10000 + f, rcfg) for f in range(nf)]
        if n_workers > 1:
            with Pool(n_workers) as pool:
                rows = pool.map(run_single_frame, tasks)
        else:
            rows = [run_single_frame(t) for t in tasks]
        summ = summarize_regime(rows, ref_key='AFDM_EP_Dual_Sym6')
        summ["elapsed_s"] = round(time.time() - tr, 1)
        results["regimes"][rname] = summ
        m = summ["means"]; ll = summ["lock_loss_gt5pct"]
        print(f"[{rname}] ({nf} fr, {summ['elapsed_s']}s, E_ratio={summ['energy_ratio_mean']:.4f}): "
              f"XuLump={m['AFDM_Xu_LumpPCA_Sym6']:.3e}({ll['AFDM_Xu_LumpPCA_Sym6']*100:.0f}%) | "
              f"GavComb={m['AFDM_Gavert_Comb_CovDIC6']:.3e}({ll['AFDM_Gavert_Comb_CovDIC6']*100:.0f}%) | "
              f"Gav1St={m['AFDM_Gavert_Guard_1Step']:.3e}({ll['AFDM_Gavert_Guard_1Step']*100:.0f}%) | "
              f"EP_CPE={m['AFDM_EP_CPE_GN6']:.3e} | EP_Dual={m['AFDM_EP_Dual_Sym6']:.3e}({ll['AFDM_EP_Dual_Sym6']*100:.0f}%) | "
              f"LumpOrac={m['AFDM_LumpOrac_Indep']:.3e} | DualOrac={m['AFDM_DualOrac']:.3e}", flush=True)
        if 'OFDM_c1=0_SingleKnob_Sym6' in m:
            print(f"   [SCOPE c1=0 single-knob] OFDM_c1=0={m['OFDM_c1=0_SingleKnob_Sym6']:.3e} (DualOrac={m['OFDM_c1=0_DualOrac']:.3e})", flush=True)

    # Pre-registered verdicts (2 clauses, strictly per [放宽TWC] — NO OFDM gate in PASS_PRIMARY!)
    R = results["regimes"]
    def sr(a, b): return a / max(b, 1e-12)
    def ci_pos(reg, k): return (reg["paired_diff_vs_ref"][k]["mean"] - reg["paired_diff_vs_ref"][k]["ci95"]) > 0

    r0, r2, r3, r4, r5 = R["R0_ZeroPN_30dB"], R["R2_N512_30dB_3e3"], R["R3_N512_45dB_3e3_Floor"], R["R4_SingleFrameBlind_3e3"], R["R5_PNTrain_30dB_3e3"]
    gates_ok = (fd_err < 1e-6 and leak_512_obs < -25.0 and leak_256_obs < -25.0 and
                all(r0["means"][k] < 1e-3 for k in ['AFDM_Uncomp', 'AFDM_Xu_LumpPCA_Sym6', 'AFDM_Gavert_Comb_CovDIC6', 'AFDM_Gavert_Guard_1Step', 'AFDM_EP_Dual_Sym6']))

    p1_r2 = (sr(r2["means"]["AFDM_Xu_LumpPCA_Sym6"], r2["means"]["AFDM_EP_Dual_Sym6"]) >= 10.0 and ci_pos(r2, "AFDM_Xu_LumpPCA_Sym6") and
             sr(r2["means"]["AFDM_Gavert_Comb_CovDIC6"], r2["means"]["AFDM_EP_Dual_Sym6"]) >= 5.0 and ci_pos(r2, "AFDM_Gavert_Comb_CovDIC6") and
             sr(r2["means"]["AFDM_Gavert_Guard_1Step"], r2["means"]["AFDM_EP_Dual_Sym6"]) >= 5.0 and ci_pos(r2, "AFDM_Gavert_Guard_1Step") and
             min(r2["lock_loss_gt5pct"][k] for k in ["AFDM_Xu_LumpPCA_Sym6", "AFDM_Gavert_Comb_CovDIC6", "AFDM_Gavert_Guard_1Step"]) - r2["lock_loss_gt5pct"]["AFDM_EP_Dual_Sym6"] >= 0.20)
    p1_r3 = (sr(r3["means"]["AFDM_Xu_LumpPCA_Sym6"], r3["means"]["AFDM_EP_Dual_Sym6"]) >= 10.0 and ci_pos(r3, "AFDM_Xu_LumpPCA_Sym6") and
             sr(r3["means"]["AFDM_Gavert_Comb_CovDIC6"], r3["means"]["AFDM_EP_Dual_Sym6"]) >= 10.0 and ci_pos(r3, "AFDM_Gavert_Comb_CovDIC6") and
             sr(r3["means"]["AFDM_Gavert_Guard_1Step"], r3["means"]["AFDM_EP_Dual_Sym6"]) >= 10.0 and ci_pos(r3, "AFDM_Gavert_Guard_1Step"))
    p1_r4 = (sr(r4["means"]["AFDM_Xu_LumpPCA_Sym6"], r4["means"]["AFDM_EP_Dual_Sym6"]) >= 4.0 and ci_pos(r4, "AFDM_Xu_LumpPCA_Sym6"))
    p1_r5 = (sr(r5["means"]["AFDM_Xu_LumpPCA_Sym6"], r5["means"]["AFDM_EP_Dual_Sym6"]) >= 5.0 and ci_pos(r5, "AFDM_Xu_LumpPCA_Sym6") and
             sr(r5["means"]["AFDM_Gavert_Comb_CovDIC6"], r5["means"]["AFDM_EP_Dual_Sym6"]) >= 5.0 and ci_pos(r5, "AFDM_Gavert_Comb_CovDIC6"))
    p1 = bool(gates_ok and p1_r2 and p1_r3 and p1_r4 and p1_r5)

    p2_bounds = all(bv["err_cov_db"] <= 0.5 for bv in bound_suite.values())
    p2_orac = (sr(r2["means"]["AFDM_LumpOrac_Indep"], r2["means"]["AFDM_EP_Dual_Sym6"]) >= 4.0 and ci_pos(r2, "AFDM_LumpOrac_Indep") and
               sr(r3["means"]["AFDM_LumpOrac_Indep"], r3["means"]["AFDM_EP_Dual_Sym6"]) >= 4.0 and ci_pos(r3, "AFDM_LumpOrac_Indep"))
    p2 = bool(p2_bounds and p2_orac)

    results["verdicts"] = {
        "GATES_OK": bool(gates_ok),
        "P1_R2": bool(p1_r2), "P1_R3": bool(p1_r3), "P1_R4": bool(p1_r4), "P1_R5": bool(p1_r5),
        "P1_FLOOR_AND_LOCKLOSS_BREAK": p1,
        "P2_BOUNDS_UNDER_0P5DB": bool(p2_bounds), "P2_BEATS_LUMP_ORAC": bool(p2_orac),
        "P2_ANALYTICAL_FLOOR_BOUND": p2,
        "PASS_PRIMARY": bool(p1 and p2),
    }
    results["total_elapsed_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as fp:
        json.dump(results, fp, indent=2)
    print(f"\n[VERDICTS] {json.dumps(results['verdicts'])} (total {results['total_elapsed_s']}s) -> {out_path}", flush=True)

if __name__ == "__main__":
    main()
