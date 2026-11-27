import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys, time, json
import numpy as np
from multiprocessing import Pool
from scipy.linalg import cho_factor, cho_solve, qr
from scipy.signal.windows import dpss
from scipy.stats import t as student_t

# ---------------- Core Utilities ----------------
def daft_matrix(N, c1, c2):
    n = np.arange(N)
    L1 = np.exp(-1j * 2 * np.pi * c1 * (n**2))
    L2 = np.exp(-1j * 2 * np.pi * c2 * (n**2))
    F = np.fft.fft(np.eye(N)) / np.sqrt(N)
    return (L2[:, None] * F) * L1[None, :]

def gray_qam_constellation(M):
    b_side = int(np.log2(M)) // 2
    m_side = 1 << b_side
    gray = np.array([i ^ (i >> 1) for i in range(m_side)])
    inv_gray = np.argsort(gray)
    levels = np.arange(-(m_side - 1), m_side, 2, dtype=float)
    pts = np.empty(M, dtype=complex)
    bits = np.empty((M, 2 * b_side), dtype=np.int8)
    for idx in range(M):
        b_re = (idx >> b_side) & (m_side - 1)
        b_im = idx & (m_side - 1)
        pts[idx] = levels[inv_gray[b_re]] + 1j * levels[inv_gray[b_im]]
        for j in range(2 * b_side):
            bits[idx, j] = (idx >> (2 * b_side - 1 - j)) & 1
    pts /= np.sqrt(np.mean(np.abs(pts)**2))
    return pts, bits

def qam_hard(x, const):
    idx = np.argmin(np.abs(x[:, None] - const[None, :]), axis=1)
    return const[idx], idx

def qam_soft(x, var_n, const):
    var_n = np.maximum(var_n, 1e-6)
    d2 = np.abs(x[:, None] - const[None, :])**2
    logw = -d2 / var_n[:, None] if np.ndim(var_n) > 0 else -d2 / var_n
    logw -= np.max(logw, axis=1, keepdims=True)
    w = np.exp(logw)
    w /= np.sum(w, axis=1, keepdims=True)
    mean = w @ const
    var = np.sum(w * np.abs(const[None, :] - mean[:, None])**2, axis=1)
    return mean, np.maximum(var, 1e-6)

def real_aug_vec(z):
    return np.concatenate([np.real(z), np.imag(z)])

def real_aug_mat(G1, G2):
    return np.block([[np.real(G1 + G2), -np.imag(G1 - G2)],
                     [np.imag(G1 + G2),  np.real(G1 - G2)]])

def circ_mat(taps, N):
    M = np.zeros((N, N), dtype=complex)
    idx = np.arange(N)
    for m, v in enumerate(taps):
        M[idx, (idx - m) % N] += v
    return M

def generate_iqi_filters(rng, level="strong13", Lf=3, Lg=3):
    if level == "zero":
        return np.array([1.0+0j]), np.array([0.0+0j]), np.array([1.0+0j]), np.array([0.0+0j])
    f1 = np.zeros(Lf, dtype=complex); f1[0] = 1.0
    g1 = np.zeros(Lg, dtype=complex); g1[0] = 1.0
    f1[1:] = np.array([0.035, 0.015])[:Lf-1] * np.exp(1j * rng.uniform(0, 2*np.pi, Lf-1))
    g1[1:] = np.array([0.035, 0.015])[:Lg-1] * np.exp(1j * rng.uniform(0, 2*np.pi, Lg-1))
    if level == "mod18":
        base = np.array([0.085, 0.075, 0.045])[:Lf]
    else:
        base = np.array([0.145, 0.125, 0.075])[:Lf]
    f2 = base * rng.uniform(0.85, 1.15, Lf) * np.exp(1j * rng.uniform(0, 2*np.pi, Lf))
    g2 = base * rng.uniform(0.85, 1.15, Lg) * np.exp(1j * rng.uniform(0, 2*np.pi, Lg))
    return f1, f2, g1, g2

def phys_transmit_receive(s, c1, gains, delays, dopplers, f1, f2, g1, g2, w_full, t_offset=0):
    N = len(s); l_max = max(delays) if len(delays) else 0
    Lf, Lg = len(f1), len(g1); L_cpp = l_max + Lf + Lg
    n_neg = np.arange(-L_cpp, 0)
    cpp = s[N + n_neg] * np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * n_neg))
    s_tx = np.concatenate([cpp, s])
    s_iq = np.zeros_like(s_tx)
    for m in range(Lf):
        s_iq[m:] += f1[m] * s_tx[:len(s_tx)-m] + f2[m] * np.conj(s_tx[:len(s_tx)-m])
    start_y = L_cpp - (Lg - 1); n_y = np.arange(-(Lg - 1), N)
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

def build_bem_dict(s_vec, B_bem, L_eq):
    N, Q = B_bem.shape
    Phi = np.empty((N, L_eq * Q), dtype=complex)
    idx = np.arange(N)
    for l in range(L_eq):
        Phi[:, l*Q:(l+1)*Q] = B_bem * s_vec[(idx - l) % N][:, None]
    return Phi

def bem_coeffs_to_H(c, B_bem, L_eq):
    N, Q = B_bem.shape
    taps = B_bem @ c.reshape(L_eq, Q).T
    H = np.zeros((N, N), dtype=complex)
    idx = np.arange(N)
    for l in range(L_eq):
        H[idx, (idx - l) % N] = taps[:, l]
    return H, taps

# ---------------- Rival (a): Faithful Huang arXiv:2606.17439 Alg 1-2 (100% BLIND sig2!) ----------------
def huang_blind_alg1_alg2(r_pre, x_pre, r_list, A, B_bem, L_eq, data_idx, guard_obs_idx, xp_val, const, N_iter=6, rho=0.7):
    N = len(r_pre); K = len(r_list)
    AAT = A @ A.T
    y_p = A @ r_pre
    s_p = A.conj().T @ x_pre
    Phi_p_daft = A @ build_bem_dict(s_p, B_bem, L_eq)
    Gp = Phi_p_daft.conj().T @ Phi_p_daft
    P_pinv_pre = np.linalg.solve(Gp + 1e-4 * np.trace(Gp).real / Gp.shape[0] * np.eye(Gp.shape[0]), Phi_p_daft.conj().T)

    # Blind noise variance estimate from preamble residual (zero truth leakage!)
    c0 = P_pinv_pre @ y_p
    e0 = y_p - Phi_p_daft @ c0
    sig2_est = max(float(np.real(np.vdot(e0, e0)) / max(N - L_eq * B_bem.shape[1], 1)), 1e-5)

    k_vec = np.array([1.0 + 0j, 0.0, 0.0, 0.0])
    k0_tilde = real_aug_vec(k_vec)
    y_cur = y_p.copy()
    yp_tilde = real_aug_vec(y_p)
    I_N = np.eye(N)

    for it in range(5):
        c_h = P_pinv_pre @ y_cur
        H_td, _ = bem_coeffs_to_H(c_h, B_bem, L_eq)
        H_eff = A @ H_td @ A.conj().T
        c1_col = H_eff @ x_pre
        c2_col = H_eff @ (AAT @ np.conj(x_pre))
        c3_col = AAT @ np.conj(H_eff @ x_pre)
        c4_col = AAT @ np.conj(H_eff @ (AAT @ x_pre))
        R_mat = np.column_stack([c1_col, c2_col, c3_col, c4_col])
        R_tilde = np.block([[np.real(R_mat), -np.imag(R_mat)], [np.imag(R_mat), np.real(R_mat)]])
        Pv = 2.0 * (k_vec[0] * k_vec[2] + k_vec[1] * k_vec[3]) * sig2_est * AAT
        Cv = sig2_est * I_N
        Cv_tilde = 0.5 * np.block([[np.real(Cv + Pv), -np.imag(Cv - Pv)], [np.imag(Cv + Pv), np.real(Cv - Pv)]])
        Cv_tilde = 0.5 * (Cv_tilde + Cv_tilde.T) + 1e-10 * np.eye(2 * N)
        c_Cv = cho_factor(Cv_tilde, lower=True)
        Cv_inv_R = cho_solve(c_Cv, R_tilde)
        Cv_inv_r = cho_solve(c_Cv, yp_tilde - R_tilde @ k0_tilde)
        k_tilde_hat = k0_tilde + np.linalg.solve(R_tilde.T @ Cv_inv_R + np.eye(8), R_tilde.T @ Cv_inv_r)
        k_hat = k_tilde_hat[:4] + 1j * k_tilde_hat[4:]
        k_new = k_hat / max(np.linalg.norm(k_hat), 1e-12)
        res_p = y_p - R_mat @ k_new
        sig2_est = max(float(np.real(np.vdot(res_p, res_p)) / max(N - L_eq * B_bem.shape[1] - 4, 1)), 1e-5)
        if np.linalg.norm(k_new - k_vec) < 1e-4 and it > 0:
            k_vec = k_new; break
        k_vec = k_new
        y_ic = y_p - (k_vec[1]*c2_col + k_vec[2]*c3_col + k_vec[3]*c4_col)
        y_cur = (1.0 - rho) * y_cur + rho * (y_ic / (k_vec[0] if abs(k_vec[0]) > 0.2 else 1.0))

    # Algorithm 2 on each data symbol (fixed k_vec, per-symbol CE per Huang §IV!)
    xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    sp = A.conj().T @ xp
    Phi_d = (A @ build_bem_dict(sp, B_bem, L_eq))[guard_obs_idx, :]
    Gd = Phi_d.conj().T @ Phi_d
    P_pinv_d = np.linalg.solve(Gd + 1e-4 * np.trace(Gd).real / Gd.shape[0] * np.eye(Gd.shape[0]), Phi_d.conj().T)
    mu_x_tilde = real_aug_vec(xp)
    act = np.concatenate([data_idx, N + data_idx])
    Pv = 2.0 * (k_vec[0] * k_vec[2] + k_vec[1] * k_vec[3]) * sig2_est * AAT
    Cv = sig2_est * I_N
    Cv_tilde = 0.5 * np.block([[np.real(Cv + Pv), -np.imag(Cv - Pv)], [np.imag(Cv + Pv), np.real(Cv - Pv)]])
    Cv_tilde = 0.5 * (Cv_tilde + Cv_tilde.T) + 1e-10 * np.eye(2 * N)
    c_Cv = cho_factor(Cv_tilde, lower=True)

    xd_all = []
    H_last = None
    for k in range(K):
        y0 = A @ r_list[k]
        y_cur = y0.copy()
        y0_tilde = real_aug_vec(y0)
        x_prev = None
        xd_lin = None
        for it in range(N_iter):
            c_h = P_pinv_d @ y_cur[guard_obs_idx]
            H_td, _ = bem_coeffs_to_H(c_h, B_bem, L_eq)
            H_last = H_td
            H_eff = A @ H_td @ A.conj().T
            G1 = k_vec[0] * H_eff + k_vec[3] * (AAT @ np.conj(H_eff) @ np.conj(AAT))
            G2 = k_vec[1] * (H_eff @ AAT) + k_vec[2] * (AAT @ np.conj(H_eff))
            G_tilde = real_aug_mat(G1, G2)
            G_act = G_tilde[:, act]
            rhs = y0_tilde - G_tilde @ mu_x_tilde
            Cv_inv_G = cho_solve(c_Cv, G_act)
            M_sys = G_act.T @ Cv_inv_G + 2.0 * np.eye(len(act))
            x_act = cho_solve(cho_factor(0.5*(M_sys+M_sys.T), lower=True), Cv_inv_G.T @ rhs)
            xd_lin = x_act[:len(data_idx)] + 1j * x_act[len(data_idx):]
            xd_hard, idx_h = qam_hard(xd_lin, const)
            x_full = xp.copy(); x_full[data_idx] = xd_hard
            if x_prev is not None and np.array_equal(idx_h, x_prev):
                break
            x_prev = idx_h
            y_ic = y0 - (k_vec[1]*(H_eff @ (AAT @ np.conj(x_full))) +
                         k_vec[2]*(AAT @ np.conj(H_eff @ x_full)) +
                         k_vec[3]*(AAT @ np.conj(H_eff @ (AAT @ x_full))))
            y_cur = (1.0 - rho) * y_cur + rho * (y_ic / (k_vec[0] if abs(k_vec[0]) > 0.2 else 1.0))
        xd_all.append(xd_lin)
    return xd_all, H_last

# ---------------- Rival (b): Faithful Narasimhan JSTSP'09 §IV-B + §V-A (Banded Mirror+Adjacent WL!) ----------------
def narasimhan09_banded_wl(r_pre1, x_pre1, r_pre2, x_pre2, r_list, A, B_bem, L_eq, data_idx, xp_val, B_adj=2):
    """
    Faithful Narasimhan et al., IEEE JSTSP 2009 §IV-B + §V-A (Mobile Wideband Joint Tx/Rx IQI):
    1) §V-A Frequency-selective joint training (uses 2 known preambles, or 1st preamble + conjugate-orthogonality,
       to estimate full wideband (H_dir, H_img) in transform domain -> generous 2-preamble training so estimation is
       accurate on BOTH static & mobile OFDM!).
    2) Transforms to transform domain: G_dir = A H_dir A^H, G_img = A H_img A^T.
    3) §IV-B Banded Mirror+Adjacent WL-LMMSE Equalizer:
       For each bin m, collects the local (2*B_adj+1) bins around m AND the (2*B_adj+1) bins around mirror (-m)%N:
         y_loc = [y[m-B..m+B], y^*[-m-B..-m+B]]^T  (length 2*(2B+1))
       and computes the EXACT local WL-LMMSE equalizer for x[m] from the banded local submatrix of (G_dir, G_img)
       (modeling interference from [m-2B..m+2B] and [-m-2B..-m+2B]!)!
       -> On mobile OFDM (c1=0, |nu|<=0.85, 3-tap strong FS IQI), G_dir and G_img are STRICTLY banded around
          diagonals m and -m (B_adj=2 captures >99.9% energy -> SER < 0.5%!!).
       -> Direct zero-mod port F_N -> A on AFDM (c1 != 0) keeps the EXACT same §IV-B banded mirror+adjacent
          structure, which fails because AFDM scatters multipath lags to m - 2Nc1*l and conjugate images across all N bins!
    """
    N = len(r_pre1); Q = B_bem.shape[1]
    # Jointly estimate wideband H_dir (L_eq taps) and H_img (L_eq+3 taps) from 2 known preambles (generous §V-A!)
    L_img = L_eq + 3
    s1 = A.conj().T @ x_pre1; s2 = A.conj().T @ x_pre2
    Phi1 = np.hstack([build_bem_dict(s1, B_bem, L_eq), build_bem_dict(np.conj(s1), B_bem, L_img)])
    Phi2 = np.hstack([build_bem_dict(s2, B_bem, L_eq), build_bem_dict(np.conj(s2), B_bem, L_img)])
    Phi_all = np.vstack([Phi1, Phi2]); r_all = np.concatenate([r_pre1, r_pre2])
    Gp = Phi_all.conj().T @ Phi_all
    c_all = np.linalg.solve(Gp + 1e-4 * np.trace(Gp).real / Gp.shape[0] * np.eye(Gp.shape[0]), Phi_all.conj().T @ r_all)
    res_p = r_all - Phi_all @ c_all
    sig2_est = max(float(np.real(np.vdot(res_p, res_p)) / max(2 * N - Phi_all.shape[1], 1)), 1e-5)

    H_dir, _ = bem_coeffs_to_H(c_all[:L_eq*Q], B_bem, L_eq)
    H_img, _ = bem_coeffs_to_H(c_all[L_eq*Q:], B_bem, L_img)
    # Transform to target basis A (F_N for OFDM, A_{c1,c2} for AFDM — PURE F_N -> A direct port!)
    G1 = A @ H_dir @ A.conj().T
    G2 = A @ H_img @ A.T

    # Subtract known pilot at bin 0 (if present)
    xp_vec = np.zeros(N, dtype=complex); xp_vec[0] = xp_val
    y_p_contrib = G1[:, 0] * xp_val + G2[:, 0] * np.conj(xp_val)

    # Precompute per-bin §IV-B banded mirror+adjacent WL-LMMSE filters w_m (length 2*(2B+1))
    offs = np.arange(-B_adj, B_adj + 1)
    offs_ext = np.arange(-2 * B_adj, 2 * B_adj + 1)
    L_obs = len(offs)
    w_bank = np.zeros((len(data_idx), 2 * L_obs), dtype=complex)

    for ii, m in enumerate(data_idx):
        rows_p = (m + offs) % N
        rows_m = ((-m) + offs) % N
        cols_p = (m + offs_ext) % N
        cols_m = ((-m) + offs_ext) % N
        # Local banded model (Narasimhan §IV-B Eq. 12-16):
        # [ y[rows_p]    ] = [ G1[rows_p, cols_p]   G2[rows_p, cols_m] ] [ x[cols_p]   ] + n_loc
        # [ y^*[rows_m]  ]   [ G2^*[rows_m, cols_p] G1^*[rows_m,cols_m]] [ x^*[cols_m] ]
        # Wait: note y^*[r] = G2^*[r, c] x[c] + G1^*[r, c'] x^*[c']!
        # Let's check: y[r] = sum_c G1[r,c] x[c] + sum_c G2[r,c] x^*[c]
        # -> y^*[r] = sum_c G2^*[r,c] x[c] + sum_c G1^*[r,c] x^*[c]! EXACT!
        H_loc = np.block([
            [G1[np.ix_(rows_p, cols_p)],          G2[np.ix_(rows_p, cols_m)]],
            [np.conj(G2[np.ix_(rows_m, cols_p)]), np.conj(G1[np.ix_(rows_m, cols_m)])]
        ])
        # Target symbol x[m] is at column index 2*B_adj (center of cols_p!)
        h_sig = H_loc[:, 2 * B_adj]
        R_yy = H_loc @ H_loc.conj().T + sig2_est * np.eye(2 * L_obs)
        w_m = np.linalg.solve(R_yy, h_sig)
        # Unbiased gain normalization w_m^H h_sig
        gain = np.real(np.vdot(w_m, h_sig))
        w_bank[ii] = w_m / max(gain, 1e-4)

    xd_all = []
    for r in r_list:
        y = A @ r - y_p_contrib
        xd = np.empty(len(data_idx), dtype=complex)
        for ii, m in enumerate(data_idx):
            rows_p = (m + offs) % N
            rows_m = ((-m) + offs) % N
            y_loc = np.concatenate([y[rows_p], np.conj(y[rows_m])])
            xd[ii] = np.vdot(w_bank[ii], y_loc)
        xd_all.append(xd)
    return xd_all, H_dir

# ---------------- Proposed & Clean 1-Line Ablation (Importable from v_solfixes style) ----------------
def exact_wl_data_detect(r_obs, H_td, u_tx, u_rx, A, data_idx, xp_val, const, sig2, n_iter=3):
    N = len(r_obs)
    U_tx_m = circ_mat(u_tx, N); U_rx_m = circ_mat(u_rx, N)
    H_dir = H_td + U_rx_m @ np.conj(H_td @ U_tx_m)
    H_img = H_td @ U_tx_m + U_rx_m @ np.conj(H_td)
    G1 = H_dir @ A.conj().T; G2 = H_img @ A.T
    r_d = r_obs - (G1[:, 0] * xp_val + G2[:, 0] * np.conj(xp_val))
    G_tilde = real_aug_mat(G1[:, data_idx], G2[:, data_idx])
    W_rx = real_aug_mat(np.eye(N), U_rx_m)
    Cw = 0.5 * max(sig2, 1e-6) * (W_rx @ W_rx.T)
    Cw = 0.5 * (Cw + Cw.T) + 1e-10 * np.eye(2 * N)
    c_Cw = cho_factor(Cw, lower=True)
    Cw_inv_G = cho_solve(c_Cw, G_tilde)
    M_gram = 0.5 * (G_tilde.T @ Cw_inv_G + (G_tilde.T @ Cw_inv_G).T)
    rhs0 = Cw_inv_G.T @ real_aug_vec(r_d)
    Nd = len(data_idx)

    P0 = M_gram + 2.0 * np.eye(2 * Nd)
    c_P0 = cho_factor(P0, lower=True)
    x_lmmse_r = cho_solve(c_P0, rhs0)
    P0_inv_diag = np.diag(cho_solve(c_P0, np.eye(2 * Nd)))
    alpha_r = np.clip(1.0 - 2.0 * P0_inv_diag, 0.1, 0.9999)
    x_ext_r = x_lmmse_r / alpha_r
    var_ext_r = np.maximum(P0_inv_diag / alpha_r, 1e-6)
    xd = x_ext_r[:Nd] + 1j * x_ext_r[Nd:]
    m_d, v_d = qam_soft(xd, var_ext_r[:Nd] + var_ext_r[Nd:], const)
    if n_iter <= 1:
        return xd, m_d, v_d

    m_cur = m_d.copy(); v_cur = v_d.copy()
    for _ in range(n_iter - 1):
        v_r = np.clip(0.5 * np.concatenate([v_cur, v_cur]), 1e-4, 0.5)
        inv_v = 1.0 / v_r
        P_it = M_gram + np.diag(inv_v)
        c_Pit = cho_factor(P_it, lower=True)
        m_r = real_aug_vec(m_cur)
        post_r = m_r + cho_solve(c_Pit, rhs0 - M_gram @ m_r)
        post_var_r = np.clip(np.diag(cho_solve(c_Pit, np.eye(2 * Nd))), 1e-7, 0.4999)
        cav_prec = np.maximum(1.0 / post_var_r - inv_v, 1e-4)
        cav_var = 1.0 / cav_prec
        cav_mean = cav_var * (post_r / post_var_r - m_r * inv_v)
        xd = cav_mean[:Nd] + 1j * cav_mean[Nd:]
        m_new, v_new = qam_soft(xd, cav_var[:Nd] + cav_var[Nd:], const)
        m_cur = 0.7 * m_new + 0.3 * m_cur
        v_cur = 0.7 * v_new + 0.3 * v_cur
    return xd, m_cur, v_cur

def solve_clean_paired(r_list, A, B_bem, data_idx, guard_obs_idx, xp_val, const, L_eq, Lu,
                       use_null_u0=True, use_prefine=True, use_null_sig2=True, Lu_override=None, n_outer=6):
    K = len(r_list); N, Q_bem = B_bem.shape
    Lu_eff = Lu if Lu_override is None else Lu_override
    xp = np.zeros(N, dtype=complex); xp[0] = xp_val
    sp = A.conj().T @ xp; sp_conj = np.conj(sp)
    Phi_p = build_bem_dict(sp, B_bem, L_eq)
    A_d_H = A[data_idx, :].conj().T
    Phi_p_daft = (A @ Phi_p)[guard_obs_idx, :]
    Gp = Phi_p_daft.conj().T @ Phi_p_daft
    P_pinv = np.linalg.solve(Gp + 1e-4 * np.trace(Gp).real / Gp.shape[0] * np.eye(Gp.shape[0]), Phi_p_daft.conj().T)

    y_p_avg = np.mean([(A @ r_list[k])[guard_obs_idx] for k in range(K)], axis=0)
    H0, _ = bem_coeffs_to_H(P_pinv @ y_p_avg, B_bem, L_eq)

    U_kill = np.hstack([H0 @ A_d_H, Phi_p])
    Qf, Rf = qr(U_kill, mode="full")
    dR = np.abs(np.diag(Rf))
    Q_perp = Qf[:, int(np.sum(dR > 1e-8 * dR[0])):]

    idx = np.arange(N); yp0_c = np.conj(H0 @ sp)
    Psi_tx = np.column_stack([Q_perp.conj().T @ (H0 @ sp_conj[(idx - m) % N]) for m in range(Lu_eff)])
    Psi_rx = np.column_stack([Q_perp.conj().T @ yp0_c[(idx - m) % N] for m in range(Lu_eff)])
    Psi_all = np.vstack([np.hstack([Psi_tx, Psi_rx])] * K)
    z_all = np.concatenate([Q_perp.conj().T @ r_list[k] for k in range(K)])

    Gp_u = Psi_all.conj().T @ Psi_all
    u_vec = np.linalg.solve(Gp_u + 1e-2 * np.trace(Gp_u).real / max(Gp_u.shape[0], 1) * np.eye(Gp_u.shape[0]), Psi_all.conj().T @ z_all)
    res_null = z_all - Psi_all @ u_vec
    sig2_null = float(np.real(np.vdot(res_null, res_null)) / max(len(z_all) - len(u_vec), 1))
    sig2_raw  = float(np.real(np.vdot(z_all, z_all)) / max(len(z_all), 1))

    if use_null_u0:
        u_tx = u_vec[:Lu_eff].copy(); u_rx = u_vec[Lu_eff:].copy()
        for arr in (u_tx, u_rx):
            nrm = np.sum(np.abs(arr))
            if nrm > 0.55: arr *= (0.55 / nrm)
    else:
        u_tx = np.zeros(Lu_eff, dtype=complex); u_rx = np.zeros(Lu_eff, dtype=complex)
    sig2_est = sig2_null if use_null_sig2 else sig2_raw

    H_cur = H0.copy()
    if use_prefine and (np.linalg.norm(u_tx) > 0 or np.linalg.norm(u_rx) > 0):
        sp_eff = sp + sum(u_tx[m] * sp_conj[(idx - m) % N] for m in range(Lu_eff))
        Phi_pe = (A @ build_bem_dict(sp_eff, B_bem, L_eq))[guard_obs_idx, :]
        Gpe = Phi_pe.conj().T @ Phi_pe
        Ppe = np.linalg.solve(Gpe + 1e-4 * np.trace(Gpe).real / Gpe.shape[0] * np.eye(Gpe.shape[0]), Phi_pe.conj().T)
        U_k = np.fft.fft(u_rx, N); neg = (-np.arange(N)) % N
        denom = 1.0 - U_k * np.conj(U_k[neg])
        y_inv_avg = np.mean([(A @ np.fft.ifft((np.fft.fft(r_list[k]) - U_k * np.conj(np.fft.fft(r_list[k])[neg])) / denom))[guard_obs_idx] for k in range(K)], axis=0)
        H_cur, _ = bem_coeffs_to_H(Ppe @ y_inv_avg, B_bem, L_eq)

    xd_all = [None] * K
    for outer in range(n_outer):
        inner_iters = 1 if outer == 0 else (2 if outer == 1 else 3)
        s_hat_list, v_td_list = [], []
        for k in range(K):
            xd, m_d, v_d = exact_wl_data_detect(r_list[k], H_cur, u_tx, u_rx, A, data_idx, xp_val, const, sig2=max(sig2_est, 1e-5), n_iter=inner_iters)
            xd_all[k] = xd
            x_f = np.zeros(N, dtype=complex); x_f[0] = xp_val; x_f[data_idx] = m_d
            s_hat_list.append(A.conj().T @ x_f)
            v_td_list.append(float(np.sum(v_d)) / N)
        if outer == n_outer - 1:
            break
        U_k = np.fft.fft(u_rx, N); neg = (-np.arange(N)) % N
        denom = 1.0 - U_k * np.conj(U_k[neg])
        r_inv_list = [np.fft.ifft((np.fft.fft(r_list[k]) - U_k * np.conj(np.fft.fft(r_list[k])[neg])) / denom) for k in range(K)]
        utx_n2 = float(np.sum(np.abs(u_tx)**2))
        Gf = np.zeros((L_eq*Q_bem, L_eq*Q_bem), dtype=complex); rhs = np.zeros(L_eq*Q_bem, dtype=complex); P_l = []
        for k in range(K):
            sc = np.conj(s_hat_list[k])
            s_eff = s_hat_list[k] + sum(u_tx[m] * sc[(idx - m) % N] for m in range(Lu_eff))
            Pf = build_bem_dict(s_eff, B_bem, L_eq); P_l.append(Pf)
            Gf += Pf.conj().T @ Pf + (v_td_list[k]*(1.0+utx_n2) + 1e-5) * np.eye(L_eq*Q_bem)
            rhs += Pf.conj().T @ r_inv_list[k]
        c_new = np.linalg.solve(Gf, rhs); H_cur, _ = bem_coeffs_to_H(c_new, B_bem, L_eq)
        h_pow = float(np.mean(np.sum(np.abs(H_cur)**2, axis=1)))
        rsq = sum(max(float(np.real(np.vdot(r_inv_list[k]-P_l[k]@c_new, r_inv_list[k]-P_l[k]@c_new))) - N*v_td_list[k]*h_pow, 0.1*float(np.real(np.vdot(r_inv_list[k]-P_l[k]@c_new, r_inv_list[k]-P_l[k]@c_new)))) for k in range(K))
        sig2_est = max(rsq / max(K*N - L_eq*Q_bem - 2*Lu_eff, 1), 1e-5)

        Au, bu, eiv = [], [], 0.0
        for k in range(K):
            yd = H_cur @ s_hat_list[k]; bu.append(r_list[k] - yd)
            sc = np.conj(s_hat_list[k])
            ctx = [H_cur @ sc[(idx - m) % N] for m in range(Lu_eff)]
            ytx = sum((u_tx[m]*ctx[m] for m in range(Lu_eff)), np.zeros(N, dtype=complex))
            zc = np.conj(yd + ytx)
            crx = [zc[(idx - m) % N] for m in range(Lu_eff)]
            Au.append(np.hstack([np.column_stack(ctx), np.column_stack(crx)]))
            eiv += N * v_td_list[k] * h_pow
        Au = np.vstack(Au); bu = np.concatenate(bu)
        Gu = Au.conj().T @ Au + (eiv + 1e-5*np.trace(Au.conj().T @ Au).real/Au.shape[1]) * np.eye(Au.shape[1])
        un = np.linalg.solve(Gu, Au.conj().T @ bu)
        u_tx = un[:Lu_eff]; u_rx = un[Lu_eff:]
        for arr in (u_tx, u_rx):
            nrm = np.sum(np.abs(arr))
            if nrm > 0.55: arr *= (0.55 / nrm)
    return xd_all, H_cur

# ---------------- Fieller Exact Paired Ratio & Redline-5 Sizing Helper ----------------
def fieller_linear_report(a, b, R0):
    """Exact paired linear margin D_i(R0) = a_i - R0 * b_i (zero-error safe!) + Fieller 95% CI lower bound on mean(a)/mean(b)."""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    n = len(a); tcrit = float(student_t.ppf(0.975, n - 1))
    d = a - R0 * b
    d_mean = float(np.mean(d)); d_se = float(np.std(d, ddof=1) / np.sqrt(n))
    hw = tcrit * d_se
    hw_ratio = hw / d_mean if d_mean > 0 else float("inf")
    # Exact Fieller 95% LB on R = E[a]/E[b]: largest R >= 0 s.t. mean(a - R b) - tcrit * se(a - R b) > 0
    # Solve quadratic: (ma - R mb)^2 = t^2/n * (va - 2 R cab + R^2 vb)
    ma, mb = float(np.mean(a)), float(np.mean(b))
    va = float(np.var(a, ddof=1)); vb = float(np.var(b, ddof=1))
    cab = float(np.cov(a, b, ddof=1)[0, 1])
    k2 = (tcrit**2) / n
    # Coefficient of R^2, R, 1 in f(R) = (ma - R mb)^2 - k2*(va - 2 R cab + R^2 vb)
    # We want smallest positive root R where ma - R mb > 0!
    A_q = mb**2 - k2 * vb
    B_q = -2 * (ma * mb - k2 * cab)
    C_q = ma**2 - k2 * va
    if C_q <= 0:
        r_lb = 0.0
    elif abs(A_q) < 1e-18:
        r_lb = -C_q / B_q if B_q < 0 else float("inf")
    else:
        disc = B_q**2 - 4 * A_q * C_q
        if disc < 0:
            r_lb = 0.0
        else:
            # Roots where f(R) = 0; since f(0)=C_q>0, we want smallest root > 0 with ma - R mb > 0
            roots = [(-B_q - np.sqrt(disc)) / (2 * A_q), (-B_q + np.sqrt(disc)) / (2 * A_q)]
            valid = [r for r in roots if r > 0 and (ma - r * mb) > 0]
            r_lb = min(valid) if valid else float("inf")
    n_req = int(np.ceil(((tcrit * np.std(d, ddof=1)) / (0.25 * max(d_mean, 1e-12)))**2)) if d_mean > 0 else 9999
    return {"mean_a": ma, "mean_b": mb, "ratio_pt": ma / mb if mb > 0 else float("inf"),
            "R0": R0, "d_mean": d_mean, "d_hw": hw, "hw_frac": hw_ratio, "fieller_lb": r_lb, "n_req_25pct": n_req}

def run_dev_burst(args):
    seed, lvl, snr_db = args
    rng = np.random.default_rng(seed)
    N = 256; c1 = 7.0 / (2 * N); c2 = 1.0 / (2 * np.sqrt(2) * N)
    A = daft_matrix(N, c1, c2)
    delays = [0, 1, 2]; L_eq = 7; Lu = 4
    B_bem = dpss(N, 1.0, 5).T
    Q_g = 47
    guard_obs_idx = np.array([m % N for m in range(-Q_g, 4)])
    data_idx = np.array([m for m in range(Q_g + 1, N - Q_g)])
    xp_val = np.sqrt(50.0)
    const, _ = gray_qam_constellation(64)

    f1, f2, g1, g2 = generate_iqi_filters(rng, lvl, Lf=3, Lg=3)
    sig2 = 10**(-snr_db / 10.0)
    dopplers = rng.uniform(-0.85, 0.85, 3)
    gains = (rng.standard_normal(3) + 1j * rng.standard_normal(3)) * np.sqrt(np.array([0.5, 0.3, 0.2]) / 2)
    gains /= np.linalg.norm(gains)

    x_pre1 = const[rng.integers(0, 64, N)]; s_pre1 = A.conj().T @ x_pre1
    w_p1 = np.sqrt(sig2/2)*(rng.standard_normal(N+len(g1)-1)+1j*rng.standard_normal(N+len(g1)-1))
    r_pre1 = phys_transmit_receive(s_pre1, c1, gains, delays, dopplers, f1, f2, g1, g2, w_p1)

    x_pre2 = const[rng.integers(0, 64, N)]; s_pre2 = A.conj().T @ x_pre2
    w_p2 = np.sqrt(sig2/2)*(rng.standard_normal(N+len(g1)-1)+1j*rng.standard_normal(N+len(g1)-1))
    r_pre2 = phys_transmit_receive(s_pre2, c1, gains, delays, dopplers, f1, f2, g1, g2, w_p2)

    r_list, tx_list = [], []
    for k in range(4):
        idx_tx = rng.integers(0, 64, len(data_idx))
        x = np.zeros(N, dtype=complex); x[0] = xp_val; x[data_idx] = const[idx_tx]
        s = A.conj().T @ x
        w = np.sqrt(sig2/2)*(rng.standard_normal(N+len(g1)-1)+1j*rng.standard_normal(N+len(g1)-1))
        r_list.append(phys_transmit_receive(s, c1, gains, delays, dopplers, f1, f2, g1, g2, w))
        tx_list.append(idx_tx)

    def mser(xl): return float(np.mean([np.mean(qam_hard(xl[k], const)[1] != tx_list[k]) for k in range(4)]))

    xd_h, _ = huang_blind_alg1_alg2(r_pre1, x_pre1, r_list, A, B_bem, L_eq, data_idx, guard_obs_idx, xp_val, const, N_iter=6)
    xd_n, _ = narasimhan09_banded_wl(r_pre1, x_pre1, r_pre2, x_pre2, r_list, A, B_bem, L_eq, data_idx, xp_val, B_adj=2)
    xd_f, _ = solve_clean_paired(r_list, A, B_bem, data_idx, guard_obs_idx, xp_val, const, L_eq, Lu, use_null_u0=True,  use_prefine=True,  use_null_sig2=True, n_outer=6)
    xd_z, _ = solve_clean_paired(r_list, A, B_bem, data_idx, guard_obs_idx, xp_val, const, L_eq, Lu, use_null_u0=False, use_prefine=True,  use_null_sig2=True, n_outer=6)
    return {"huang": mser(xd_h), "nar_b2": mser(xd_n), "prop_full": mser(xd_f), "zero_u0": mser(xd_z)}

if __name__ == "__main__":
    print(f"Python: {sys.executable}", flush=True)
    t0 = time.perf_counter()

    # 1. Verify Narasimhan '09 §IV-B+§V-A (B_adj=2) on MOBILE OFDM (c1=0, fractional Doppler |nu|<=0.85, 3-tap strong13 FS IQI, 16-QAM 25 dB)!
    rng0 = np.random.default_rng(777)
    N = 256; A0 = daft_matrix(N, 0.0, 0.0); B_bem = dpss(N, 1.0, 5).T; L_eq = 7
    const16, _ = gray_qam_constellation(16)
    nar_mob_ofdm = []
    for _ in range(12):
        f1, f2, g1, g2 = generate_iqi_filters(rng0, "strong13", Lf=3, Lg=3)
        gains = (rng0.standard_normal(3)+1j*rng0.standard_normal(3))*np.sqrt(np.array([0.5,0.3,0.2])/2); gains /= np.linalg.norm(gains)
        dopplers = rng0.uniform(-0.85, 0.85, 3); sig2 = 10**(-25.0/10.0)
        xp1 = const16[rng0.integers(0,16,N)]; xp2 = const16[rng0.integers(0,16,N)]
        rp1 = phys_transmit_receive(A0.conj().T@xp1, 0.0, gains, [0,1,2], dopplers, f1, f2, g1, g2, np.sqrt(sig2/2)*(rng0.standard_normal(N+2)+1j*rng0.standard_normal(N+2)))
        rp2 = phys_transmit_receive(A0.conj().T@xp2, 0.0, gains, [0,1,2], dopplers, f1, f2, g1, g2, np.sqrt(sig2/2)*(rng0.standard_normal(N+2)+1j*rng0.standard_normal(N+2)))
        id_d = rng0.integers(0,16,N)
        rd = phys_transmit_receive(A0.conj().T@const16[id_d], 0.0, gains, [0,1,2], dopplers, f1, f2, g1, g2, np.sqrt(sig2/2)*(rng0.standard_normal(N+2)+1j*rng0.standard_normal(N+2)))
        xd, _ = narasimhan09_banded_wl(rp1, xp1, rp2, xp2, [rd], A0, B_bem, L_eq, np.arange(N), 0.0, B_adj=2)
        nar_mob_ofdm.append(np.mean(qam_hard(xd[0], const16)[1] != id_d))
    print(f"[Mother Health] Narasimhan '09 §IV-B/V-A (B_adj=2) on MOBILE OFDM (c1=0, |nu|<=0.85, strong13 FS IQI, 16-QAM 25dB): SER = {np.mean(nar_mob_ofdm):.4e}", flush=True)

    # 2. Dev sizing (n_dev = 48 independent bursts on 8 cores, DEV seeds 800000+)
    for name, lvl, snr_db, R0_p1, R0_p2 in [
        ("DEV_R1_mod18_30dB",   "mod18",    30, 20.0, None),
        ("DEV_R1_mod18_35dB",   "mod18",    35, 20.0, None),
        ("DEV_R2_strong13_32dB","strong13", 32, 20.0, 3.0),
    ]:
        tasks = [(800000 + snr_db*1000 + (0 if lvl=="mod18" else 500) + i, lvl, snr_db) for i in range(48)]
        with Pool(8) as pool:
            res = pool.map(run_dev_burst, tasks)
        h = [d["huang"] for d in res]; nb = [d["nar_b2"] for d in res]
        pf = [d["prop_full"] for d in res]; zu = [d["zero_u0"] for d in res]
        # Strongest formal rival per regime (lower mean SER between Huang & Narasimhan)
        riv = h if np.mean(h) <= np.mean(nb) else nb
        riv_name = "huang" if np.mean(h) <= np.mean(nb) else "nar_b2"
        rep_p1 = fieller_linear_report(riv, pf, R0_p1)
        print(f"\n=== {name} (n=48) === mean: huang={np.mean(h):.4e}, nar_b2={np.mean(nb):.4e}, zero_u0={np.mean(zu):.4e}, prop_full={np.mean(pf):.4e}", flush=True)
        print(f"  P1 ({riv_name} vs prop, R0={R0_p1}): ratio={rep_p1['ratio_pt']:.1f}x, Fieller_LB={rep_p1['fieller_lb']:.1f}x, hw_frac={rep_p1['hw_frac']:.3f}, n_req(25%)={rep_p1['n_req_25pct']}", flush=True)
        if R0_p2 is not None:
            rep_p2 = fieller_linear_report(zu, pf, R0_p2)
            print(f"  P2 (1-line zero_u0 vs prop, R0={R0_p2}): ratio={rep_p2['ratio_pt']:.2f}x, Fieller_LB={rep_p2['fieller_lb']:.2f}x, hw_frac={rep_p2['hw_frac']:.3f}, n_req(25%)={rep_p2['n_req_25pct']}", flush=True)
            # Also check how many bursts had zero_u0 > 0.05 vs prop_full > 0.05!
            print(f"  Failure-burst count (SER>0.01): zero_u0={sum(x>0.01 for x in zu)}/48 vs prop_full={sum(x>0.01 for x in pf)}/48 | median: zu={np.median(zu):.4e}, pf={np.median(pf):.4e}", flush=True)
    print(f"\nElapsed: {time.perf_counter()-t0:.1f}s", flush=True)
