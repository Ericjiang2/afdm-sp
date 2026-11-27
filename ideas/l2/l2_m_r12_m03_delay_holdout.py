"""
Round-12 Step-8 REVISE Closure (Round-14 Fix): Frozen-Receiver 3-Path Delay Holdout Test
for I-20261125-m03 (Astra kill-argument REVISE adjudication, Eric 2026-11-26).

Design invariants:
  1. ZERO modification to the frozen Round-12 receiver: imports ALL receiver functions verbatim
     from `ideas/l2/l2_m_r12_m03_modtest.py` (untouched; startup gate verifies exact MD5
     `7d174070e3b640583e8ec0e03d948cd1` BEFORE running any check, plus exact 0.0 bit-for-bit
     diff and 0 SVD fallbacks at k=7 on R4 & R5!).
  2. Cross-platform LAPACK robustness without modifying frozen `m3`: installs an idempotent
     wrapper on `m3.np.linalg.svd` that calls original `numpy.linalg.svd` unchanged on all
     normal converging matrices and ONLY on `np.linalg.LinAlgError` falls back to
     `scipy.linalg.svd(..., lapack_driver="gesvd")` while incrementing an audited counter
     reported per frame, per k, per cell, and globally.
  3. All R4/R5 frame parameters, powers [0.4225, 0.3025, 0.2750], SNR=30 dB, sig_r=sig_t=1.5e-3,
     guard/obs windows, and RNG draw sequence are IDENTICAL to Round-12; ONLY the middle true
     path delay changes from [0, 7, 16] to [0, k, 16]:
       - Separated group (`分离组`): k in {3, 5, 9, 11, 13} (holding out k=7)
       - Adjacent group  (`相邻组`): k in {1, 15}
  4. Exact stratified fixed-delay inference (closing Sol Blocking #1):
     Each group uses equal deterministic stratum sizes n_k = N / K across its K fixed delays.
     All paired SER differences, lock-loss differences, Fieller ratios, and linearized threshold
     tests D(M) = A - M*B compute unbiased within-stratum variances/covariances (ddof=1 per k,
     equal stratum weights w_k = 1/K, residual degrees of freedom df = N - K = sum_k (n_k - 1))
     using exact int64 symbol-error counts.
  5. Red Line #5 sample sizes verified under the EXACT same stratified estimator in
     `ideas/probes/m_dev_r12_m03_holdout_sizing.py` (`DEV_HOLDOUT_BASE = 11000001`).
  6. Strictly disjoint fresh seed namespace: SEED_BASE = 2027500001 (smoke: 2029500001).
  7. Scope adjudication ONLY: NEVER modifies Round-11 or Round-12 frozen PASS_PRIMARY verdicts.
"""
import os, sys, json, time, math, hashlib
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
from scipy.linalg import svd as scipy_svd
from scipy.stats import t as student_t, beta as beta_dist
from multiprocessing import Pool

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)
import l2_m_r12_m03_modtest as m3

FROZEN_MODTEST_MD5 = "7d174070e3b640583e8ec0e03d948cd1"
SEPARATED_KS = [3, 5, 9, 11, 13]
ADJACENT_KS = [1, 15]

# =============================================================================
# Audited SVD gesvd Exception-Only Fallback Wrapper (Zero Edit to Frozen m3!)
# =============================================================================
_ORIG_NP_SVD = None
_SVD_GESVD_FALLBACK_COUNT = 0


def get_svd_fallback_count() -> int:
    return int(_SVD_GESVD_FALLBACK_COUNT)


def install_svd_gesvd_fallback():
    """Idempotently replace `m3.np.linalg.svd` with an exception-only `gesvd` fallback wrapper.
    Normal converging calls return the exact bit-for-bit output of original `np.linalg.svd`."""
    global _ORIG_NP_SVD
    cur_svd = m3.np.linalg.svd
    if getattr(cur_svd, "_is_m03_gesvd_fallback_wrapper", False):
        return cur_svd
    _ORIG_NP_SVD = cur_svd

    def _svd_with_gesvd_fallback(a, full_matrices=True, compute_uv=True, hermitian=False):
        global _SVD_GESVD_FALLBACK_COUNT
        try:
            return _ORIG_NP_SVD(
                a,
                full_matrices=full_matrices,
                compute_uv=compute_uv,
                hermitian=hermitian,
            )
        except np.linalg.LinAlgError:
            _SVD_GESVD_FALLBACK_COUNT += 1
            return scipy_svd(
                a,
                full_matrices=full_matrices,
                compute_uv=compute_uv,
                lapack_driver="gesvd",
            )

    _svd_with_gesvd_fallback._is_m03_gesvd_fallback_wrapper = True
    m3.np.linalg.svd = _svd_with_gesvd_fallback
    return _svd_with_gesvd_fallback


install_svd_gesvd_fallback()


def clopper_pearson_ci(k, n, alpha=0.05):
    """Exact finite-sample Clopper-Pearson (1-alpha) binomial CI."""
    k = int(k); n = int(n)
    if n <= 0:
        return [0.0, 1.0]
    lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return [lo, hi]


def run_frozen_holdout_frame(args):
    """Exact copy of m3.run_single_frame for R4/R5 with ONLY ls_t = [0, mid_delay, 16]
    (identical powers [0.4225, 0.3025, 0.2750], identical RNG sequence, verbatim frozen m3 receiver functions)
    plus passive post-init logging of detected delay support l_h (and l_leg in single_frame)
    and per-frame SVD gesvd fallback count.
    """
    install_svd_gesvd_fallback()
    fb_start = get_svd_fallback_count()
    seed, cfg = args
    rng = np.random.default_rng(seed)
    N = cfg['N']; L_cpp = cfg['L_cpp']; B = N + L_cpp; two_Nc1 = cfg['two_Nc1']
    c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2 * np.pi * N)
    snr_db = cfg['snr_db']; sig_r = cfg['sig_r']; sig_t = cfg['sig_t']
    mode = cfg['mode']  # 'single_frame' (R4) or 'prior_pn' (R5)
    mid_delay = int(cfg['mid_delay'])

    A_a = m3.daft_matrix(N, c1, c2); Ah_a = A_a.conj().T; P_a = m3.build_cpp_ext(N, c1, L_cpp)
    g8 = np.array([-7, -5, -3, -1, 1, 3, 5, 7]); pts64 = (g8[:, None] + 1j * g8[None, :]).ravel() / np.sqrt(42.0)
    qpsk = np.array([-1-1j, -1+1j, 1-1j, 1+1j]) / np.sqrt(2.0)

    k_p = N // 2
    g_lo, g_hi = cfg['g_lo'], cfg['g_hi']
    obs_lo, obs_hi = cfg['obs_lo'], cfg['obs_hi']
    max_hw = cfg['max_hw']
    guard = np.zeros(N, dtype=bool); guard[g_lo:g_hi] = True
    data_mask = ~guard; n_guard = int(guard.sum()); Nd = int(data_mask.sum())
    pilot_obs = np.zeros(N, dtype=bool); pilot_obs[obs_lo:obs_hi] = True

    comb_mask = np.zeros(N, dtype=bool)
    comb_mask[np.round(np.linspace(0, N - 1, n_guard, endpoint=False)).astype(int)] = True
    data_comb = ~comb_mask

    x_p = np.zeros(N, dtype=complex); x_p[k_p] = np.sqrt(float(n_guard))
    sp_a = P_a @ (Ah_a @ x_p)
    pca = m3.build_pca_bases(N, L_cpp, K_pca=18 if N == 512 else 14)

    # Fixed nominal PN prior (NEVER reads simulator true sig_r / sig_t!)
    sig_r_prior = 1.5e-3; sig_t_prior = 1.5e-3
    sys_cfg = dict(N=N, L_cpp=L_cpp, two_Nc1=two_Nc1, k_p=k_p, A=A_a, Ah=Ah_a,
                   s_p_ext=sp_a, n_guard=n_guard, max_hw=max_hw, pilot_obs=pilot_obs,
                   sig_r_prior=sig_r_prior, sig_t_prior=sig_t_prior)

    # True channel generation: ONLY middle path delay varied [0, mid_delay, 16]; powers & RNG sequence IDENTICAL!
    ls_t = np.array([0, mid_delay, 16], dtype=int)
    pdp = np.array([0.4225, 0.3025, 0.2750])
    P_cnt = len(ls_t)
    nus_t = rng.uniform(-0.4, 0.4, P_cnt)
    hs_t = np.sqrt(pdp) * np.exp(1j * rng.uniform(0, 2 * np.pi, P_cnt))
    H_lin_t = m3.build_H_ext(N, L_cpp, hs_t, ls_t, nus_t)
    sig2_true = 10.0 ** (-snr_db / 10.0)

    phi_t = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)) if sig_t > 0 else np.zeros(B); phi_t -= phi_t[L_cpp]
    phi_r = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N)) if sig_r > 0 else np.zeros(N)
    w = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    xd_vals = pts64[rng.integers(0, 64, Nd)]

    x_a = x_p.copy(); x_a[data_mask] = xd_vals
    s_ext_a = P_a @ (Ah_a @ x_a)
    y_a = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ext_a)) + w
    Y_a = A_a @ y_a

    x_c = np.zeros(N, dtype=complex); x_c[data_comb] = xd_vals; x_c[comb_mask] = qpsk[rng.integers(0, 4, n_guard)]
    xp_c = np.where(comb_mask, x_c, 0.0); sp_c = P_a @ (Ah_a @ xp_c)
    s_ext_c = P_a @ (Ah_a @ x_c)
    y_c = np.exp(1j * phi_r) * (H_lin_t @ (np.exp(1j * phi_t) * s_ext_c)) + w

    energy_ratio_comb_to_ep = float(np.sum(np.abs(s_ext_c) ** 2) / np.sum(np.abs(s_ext_a) ** 2))
    base_energy_diff = float(abs(np.sum(np.abs(x_c) ** 2) - np.sum(np.abs(x_a) ** 2)))

    # === 100% BLIND CHANNEL & NOISE INITIALIZATION (VERBATIM FROZEN m3 RECEIVER!) ===
    refine_ch_in_loop = (mode in ('single_frame', 'prior_pn'))
    if mode == 'single_frame':
        sig2_hat, l_h, h_h, nu_h, phi_mrc = m3.blind_single_frame_init(Y_a, sys_cfg)
    else:
        w_tr = np.sqrt(sig2_true / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        if mode == 'prior_pn' and (sig_r > 0 or sig_t > 0):
            pt_tr = np.cumsum(np.sqrt(sig_t) * rng.standard_normal(B)); pt_tr -= pt_tr[L_cpp]
            pr_tr = np.cumsum(np.sqrt(sig_r) * rng.standard_normal(N))
            y_tr = np.exp(1j * pr_tr) * (H_lin_t @ (np.exp(1j * pt_tr) * sp_a)) + w_tr
            sig2_hat, l_h, h_h, nu_h = m3.blind_ce_from_training(y_tr, sys_cfg, training_has_pn=True)
        else:
            y_tr = H_lin_t @ sp_a + w_tr
            sig2_hat, l_h, h_h, nu_h = m3.blind_ce_from_training(y_tr, sys_cfg, training_has_pn=False)
        H_p0 = [m3.build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]
        k_cs = [k_p - two_Nc1 * int(l) for l in l_h]
        z_mrc = np.zeros(N, dtype=complex)
        for i in range(len(l_h)):
            k_hi = min(k_cs[i] + max_hw, (k_cs[i] + k_cs[i - 1]) // 2) if i > 0 else k_cs[i] + max_hw
            k_lo = max(k_cs[i] - max_hw, (k_cs[i] + k_cs[i + 1]) // 2 + 1) if i < len(l_h) - 1 else k_cs[i] - max_hw
            m = np.zeros(N, dtype=bool); m[k_lo : k_hi + 1] = True
            Ys = np.zeros(N, dtype=complex); Ys[m] = Y_a[m]
            z_mrc += (Ah_a @ Ys) * np.conj(H_p0[i] @ sp_a)
        pi = m3.zero_unwrap_complex(z_mrc[L_cpp : N - L_cpp])
        phi_mrc = np.empty(N); phi_mrc[L_cpp:N - L_cpp] = pi; phi_mrc[:L_cpp] = pi[0]; phi_mrc[N - L_cpp:] = pi[-1]

    H_lin_h = m3.build_H_ext(N, L_cpp, h_h, l_h, nu_h); H_circ_h = H_lin_h @ P_a
    H_paths_h = [m3.build_H_ext(N, L_cpp, [h_h[i]], [l_h[i]], [nu_h[i]]) for i in range(len(l_h))]

    def run_dual_outer(y_in, P_i, Ah_i, dm_i, xp_i, pr0, pt0, h0, nu0, l_use=None, s2_init_override=None):
        l_vec = l_h if l_use is None else l_use
        pr_c, pt_c = pr0.copy(), pt0.copy()
        h_c, nu_c = h0.copy(), nu0.copy()
        s2_0 = sig2_hat if s2_init_override is None else s2_init_override
        s2 = s2_0
        best_r = np.inf; best_xh = None
        for out_idx in range(6):
            Hl = m3.build_H_ext(N, L_cpp, h_c, l_vec, nu_c)
            Hc = np.exp(1j * pr_c)[:, None] * ((Hl * np.exp(1j * pt_c)[None, :]) @ P_i)
            xs, xhc, vx, _ = m3.oamp_exact(y_in, Hc, Ah_i, max(s2, 1e-6) + 0.02 * (0.6 ** out_idx), pts64, dm_i, xp_i, 8)
            s_ext_s = P_i @ (Ah_i @ xs)
            pr_c, pt_c = m3.gn_dual_banded(y_in, Hl, s_ext_s, pr_c, pt_c, max(s2, 1e-6) + 0.5 * vx, sig_r_prior, sig_t_prior, L_cpp, 3)
            if refine_ch_in_loop and out_idx >= 1:
                h_c, nu_c = m3.refine_channel_blind(y_in, s_ext_s, pr_c, pt_c, l_vec, nu_c, L_cpp)
            Hl2 = m3.build_H_ext(N, L_cpp, h_c, l_vec, nu_c)
            rc = float(np.sum(np.abs(y_in - np.exp(1j * pr_c) * (Hl2 @ (np.exp(1j * pt_c) * (P_i @ (Ah_i @ xhc))))) ** 2))
            s2_floor = 1e-5 if refine_ch_in_loop else max(s2_0 * 0.4, 1e-6)
            s2 = float(np.clip(rc / N, s2_floor, 0.05))
            if rc < best_r:
                best_r = rc; best_xh = xhc
        return best_xh

    def ser(xh, xt, dm):
        return float(np.mean(np.abs(xh[dm] - xt[dm]) > 1e-3))

    out = {
        "mid_delay": mid_delay,
        "energy_ratio_comb_to_ep": energy_ratio_comb_to_ep,
        "base_energy_diff": base_energy_diff,
        "n_data_syms": int(Nd),
        "det_delays": [int(v) for v in l_h],
    }
    ref_all = H_circ_h @ (Ah_a @ x_p)
    phi_cpe = np.full(N, np.angle(np.vdot(ref_all, y_a)))

    # 1) AFDM_Uncomp
    _, xhu, _, _ = m3.oamp_exact(y_a, H_circ_h, Ah_a, sig2_hat, pts64, data_mask, x_p, 8)
    out['AFDM_Uncomp'] = ser(xhu, x_a, data_mask)

    # 2) AFDM_Xu_LumpPCA_Sym6
    if refine_ch_in_loop:
        phi_l = m3.exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_lin_h, sp_a, phi_mrc,
                                            max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 3)
        hl_c, nul_c = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, phi_l, np.zeros(B), l_h, nu_h, L_cpp)
        phi_l = m3.exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], m3.build_H_ext(N, L_cpp, hl_c, l_h, nul_c), sp_a, phi_l,
                                            max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 3)
    else:
        phi_l = m3.exact_proj_lumped_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_lin_h, sp_a, phi_mrc,
                                            max(sig2_hat, 1e-3), sig_r_prior + sig_t_prior, L_cpp, pca, 6)
        hl_c, nul_c = h_h.copy(), nu_h.copy()
    s2l = sig2_hat
    gam_l = np.maximum(np.abs(hl_c) ** 2, 1e-3)
    best_rl = np.inf; best_xhl = None
    for out_i in range(6):
        Hcl = m3.build_H_ext(N, L_cpp, hl_c, l_h, nul_c) @ P_a
        xs_l, xhc_l, vxl, _ = m3.oamp_exact(y_a * np.exp(-1j * phi_l), Hcl, Ah_a, max(s2l, 1e-6) + 0.02 * (0.6 ** out_i), pts64, data_mask, x_p, 8)
        phi_l = m3.gn_lumped(y_a, Hcl, Ah_a @ xs_l, phi_l, max(s2l, 1e-6) + 0.5 * vxl, sig_r_prior + sig_t_prior, 3)
        if out_i >= 1:
            hl_c, nul_c, gam_l, s2l_em = m3.refine_channel_sbl_em(y_a, P_a @ (Ah_a @ xs_l), phi_l, np.zeros(B), l_h, nul_c, gam_l, max(s2l, 1e-6) + 0.5 * vxl, L_cpp)
        else:
            s2l_em = s2l
        Hcl2 = m3.build_H_ext(N, L_cpp, hl_c, l_h, nul_c) @ P_a
        rl_hard = float(np.sum(np.abs(y_a * np.exp(-1j * phi_l) - Hcl2 @ (Ah_a @ xhc_l)) ** 2))
        s2l_floor = 1e-5 if refine_ch_in_loop else max(sig2_hat * 0.4, 1e-6)
        s2l = float(np.clip(max(s2l_em, rl_hard / N), s2l_floor, 0.05))
        if rl_hard < best_rl:
            best_rl = rl_hard; best_xhl = xhc_l
    out['AFDM_Xu_LumpPCA_Sym6'] = ser(best_xhl, x_a, data_mask)

    # 3) AFDM_Gavert_Guard_1Step
    xs_g1, _, _, vx_g1_vec = m3.oamp_exact(y_a * np.exp(-1j * phi_cpe), H_circ_h, Ah_a, max(sig2_hat, 1e-4) + 0.02, pts64, data_mask, x_p, 8)
    s_est_g1 = P_a @ (Ah_a @ xs_g1)
    M_gd = (A_a[pilot_obs, :] @ H_circ_h) @ Ah_a[:, data_mask]
    Sigma_g1 = max(sig2_hat, 1e-6) * np.eye(int(pilot_obs.sum())) + (M_gd * vx_g1_vec[None, :]) @ M_gd.conj().T
    pr_g1, pt_g1 = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, s_est_g1,
                                             phi_cpe, np.zeros(B), np.linalg.inv(Sigma_g1), sig_r_prior, sig_t_prior, L_cpp, pca, 1)
    out['AFDM_Gavert_Guard_1Step'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_g1, pt_g1, h_h, nu_h), x_a, data_mask)

    # 4) AFDM_EP_CPE_GN6
    if refine_ch_in_loop:
        pr_c6, pt_c6 = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                                 phi_cpe, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        hc_c6, nuc_c6 = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, pr_c6, pt_c6, l_h, nu_h, L_cpp)
        Hp_c6 = [m3.build_H_ext(N, L_cpp, [hc_c6[i]], [l_h[i]], [nuc_c6[i]]) for i in range(len(l_h))]
        pr_c6, pt_c6 = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], Hp_c6, l_h, sp_a,
                                                 pr_c6, pt_c6, 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        out['AFDM_EP_CPE_GN6'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_c6, pt_c6, hc_c6, nuc_c6), x_a, data_mask)
    else:
        pr_c6, pt_c6 = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                                 phi_cpe, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        out['AFDM_EP_CPE_GN6'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_c6, pt_c6, h_h, nu_h), x_a, data_mask)

    # 5) AFDM_EP_Dual_Sym6 (+ same-frame NoCMSep legacy control in single_frame!)
    if refine_ch_in_loop:
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                                 phi_mrc, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        h_sf2, nu_sf2 = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, pr_ep, pt_ep, l_h, nu_h, L_cpp)
        H_p_sf2 = [m3.build_H_ext(N, L_cpp, [h_sf2[i]], [l_h[i]], [nu_sf2[i]]) for i in range(len(l_h))]
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_p_sf2, l_h, sp_a,
                                                 pr_ep, pt_ep, 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        out['AFDM_EP_Dual_Sym6'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_ep, pt_ep, h_sf2, nu_sf2), x_a, data_mask)
        if mode == 'single_frame':
            s2_leg, l_leg, h_leg, nu_leg, phi_leg = m3.blind_single_frame_init_legacy(Y_a, sys_cfg)
            out['det_delays_legacy'] = [int(v) for v in l_leg]
            Hp_leg = [m3.build_H_ext(N, L_cpp, [h_leg[i]], [l_leg[i]], [nu_leg[i]]) for i in range(len(l_leg))]
            pr_lg, pt_lg = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], Hp_leg, l_leg, sp_a,
                                                     phi_leg, np.zeros(B), 1.0 / max(s2_leg, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
            h_lg2, nu_lg2 = m3.refine_ch_on_pilot_obs(Y_a[pilot_obs], A_a[pilot_obs, :], sp_a, pr_lg, pt_lg, l_leg, nu_leg, L_cpp)
            Hp_lg2 = [m3.build_H_ext(N, L_cpp, [h_lg2[i]], [l_leg[i]], [nu_lg2[i]]) for i in range(len(l_leg))]
            pr_lg, pt_lg = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], Hp_lg2, l_leg, sp_a,
                                                     pr_lg, pt_lg, 1.0 / max(s2_leg, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 3)
            out['AFDM_EP_Dual_Sym6_NoCMSep'] = ser(
                run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_lg, pt_lg, h_lg2, nu_lg2, l_use=l_leg, s2_init_override=s2_leg),
                x_a, data_mask
            )
    else:
        pr_ep, pt_ep = m3.exact_proj_dual_gn_pca(Y_a[pilot_obs], A_a[pilot_obs, :], H_paths_h, l_h, sp_a,
                                                 phi_mrc, np.zeros(B), 1.0 / max(sig2_hat, 1e-3), sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        out['AFDM_EP_Dual_Sym6'] = ser(run_dual_outer(y_a, P_a, Ah_a, data_mask, x_p, pr_ep, pt_ep, h_h, nu_h), x_a, data_mask)

    # 6) AFDM_Gavert_Comb_CovDIC6
    if mode == 'single_frame':
        n_arr = np.arange(N)
        corr_c = np.array([abs(np.vdot(sp_c[L_cpp + n_arr - l], y_c)) ** 2 for l in range(L_cpp + 1)])
        l_comb = np.sort(np.argsort(corr_c)[-3:]).astype(int)
        Phi_c = np.column_stack([sp_c[L_cpp + n_arr - int(l)] for l in l_comb])
        h_comb, _, _, _ = np.linalg.lstsq(Phi_c, y_c, rcond=None)
        nu_comb = np.zeros(len(l_comb))
        H_lin_c = m3.build_H_ext(N, L_cpp, h_comb, l_comb, nu_comb); H_circ_c = H_lin_c @ P_a
        H_paths_c = [m3.build_H_ext(N, L_cpp, [h_comb[i]], [l_comb[i]], [nu_comb[i]]) for i in range(len(l_comb))]
        s2_c_init = max(float(np.mean(np.abs(y_c - Phi_c @ h_comb) ** 2)) * 0.05, 1e-3)
    else:
        l_comb, h_comb, nu_comb = l_h, h_h, nu_h
        H_lin_c, H_circ_c, H_paths_c = H_lin_h, H_circ_h, H_paths_h
        s2_c_init = sig2_hat

    pcc = np.full(N, np.angle(np.vdot(H_circ_c @ (Ah_a @ xp_c), y_c)))
    xs_0, _, _, vx_0_vec = m3.oamp_exact(y_c * np.exp(-1j * pcc), H_circ_c, Ah_a, max(s2_c_init, 1e-4) + 0.02, pts64, data_comb, xp_c, 8)
    s_est_ext_c = P_a @ (Ah_a @ xs_0)
    M_cd = (A_a[comb_mask, :] @ H_circ_c) @ Ah_a[:, data_comb]
    Sigma_res = max(s2_c_init, 1e-6) * np.eye(n_guard) + (M_cd * vx_0_vec[None, :]) @ M_cd.conj().T
    Sigma_inv = np.linalg.inv(Sigma_res)
    Y_comb_obs = (A_a @ y_c)[comb_mask]
    if refine_ch_in_loop:
        pr_gc, pt_gc = m3.exact_proj_dual_gn_pca(Y_comb_obs, A_a[comb_mask, :], H_paths_c, l_comb, s_est_ext_c,
                                                 pcc, np.zeros(B), Sigma_inv, sig_r_prior, sig_t_prior, L_cpp, pca, 3)
        hc_c, nuc_c = m3.refine_ch_on_pilot_obs(Y_comb_obs, A_a[comb_mask, :], s_est_ext_c, pr_gc, pt_gc, l_comb, nu_comb, L_cpp, W_inv=Sigma_inv)
        Hp_c2 = [m3.build_H_ext(N, L_cpp, [hc_c[i]], [l_comb[i]], [nuc_c[i]]) for i in range(len(l_comb))]
        pr_gc, pt_gc = m3.exact_proj_dual_gn_pca(Y_comb_obs, A_a[comb_mask, :], Hp_c2, l_comb, s_est_ext_c,
                                                 pr_gc, pt_gc, Sigma_inv, sig_r_prior, sig_t_prior, L_cpp, pca, 3)
    else:
        pr_gc, pt_gc = m3.exact_proj_dual_gn_pca(Y_comb_obs, A_a[comb_mask, :], H_paths_c, l_comb, s_est_ext_c,
                                                 pcc, np.zeros(B), Sigma_inv, sig_r_prior, sig_t_prior, L_cpp, pca, 6)
        hc_c, nuc_c = h_comb.copy(), nu_comb.copy()
    pr_c, pt_c = pr_gc.copy(), pt_gc.copy(); s2c = s2_c_init
    best_rc = np.inf; best_xhc = None
    for out_i in range(6):
        Hl_c = m3.build_H_ext(N, L_cpp, hc_c, l_comb, nuc_c)
        Hc_c = np.exp(1j * pr_c)[:, None] * ((Hl_c * np.exp(1j * pt_c)[None, :]) @ P_a)
        xs_c, xhc_c, vxc, _ = m3.oamp_exact(y_c, Hc_c, Ah_a, max(s2c, 1e-6) + 0.02 * (0.6 ** out_i), pts64, data_comb, xp_c, 8)
        s_ext_sc = P_a @ (Ah_a @ xs_c)
        pr_c, pt_c = m3.gn_dual_banded(y_c, Hl_c, s_ext_sc, pr_c, pt_c, max(s2c, 1e-6) + 0.5 * vxc, sig_r_prior, sig_t_prior, L_cpp, 3)
        if refine_ch_in_loop and out_i >= 1:
            hc_c, nuc_c = m3.refine_channel_blind(y_c, s_ext_sc, pr_c, pt_c, l_comb, nuc_c, L_cpp)
        Hl_c2 = m3.build_H_ext(N, L_cpp, hc_c, l_comb, nuc_c)
        rc = float(np.sum(np.abs(y_c - np.exp(1j * pr_c) * (Hl_c2 @ (np.exp(1j * pt_c) * (P_a @ (Ah_a @ xhc_c))))) ** 2))
        s2c = float(np.clip(rc / N, 1e-5 if refine_ch_in_loop else max(s2_c_init * 0.4, 1e-6), 0.05))
        if rc < best_rc:
            best_rc = rc; best_xhc = xhc_c
    out['AFDM_Gavert_Comb_CovDIC6'] = ser(best_xhc, x_c, data_comb)

    # 8) Oracles
    n_arr_o = np.arange(N)
    V_d_o = P_a @ Ah_a[:, data_mask]
    path_o = np.stack([H_lin_t[n_arr_o, L_cpp + n_arr_o - int(l), None] * V_d_o[L_cpp + n_arr_o - int(l), :] for l in ls_t], axis=1)
    Wn_o = np.einsum('npk,nqk->npq', path_o, np.conj(path_o))
    v_n_o = np.sum(Wn_o, axis=2)
    local_w = v_n_o.real / v_n_o.real.sum(axis=1, keepdims=True)
    D_o = -0.5 * sig_t * np.abs(ls_t[:, None] - ls_t[None, :])
    Dv_loc = local_w @ D_o
    C_loc = D_o[None, :, :] - Dv_loc[:, :, None] - Dv_loc[:, None, :] + np.sum(Dv_loc * local_w, axis=1)[:, None, None]
    sig2_irred_rx = float(np.sum(Wn_o.real * C_loc, axis=(1, 2)).mean())
    z_pt = np.stack([np.exp(1j * phi_t[L_cpp - int(l) : L_cpp - int(l) + N]) for l in ls_t], axis=1)
    phi_ind = phi_r + np.angle(np.sum(v_n_o * z_pt, axis=1))
    _, xhlo, _, _ = m3.oamp_exact(y_a * np.exp(-1j * phi_ind), H_lin_t @ P_a, Ah_a, sig2_true + sig2_irred_rx, pts64, data_mask, x_p, 10)
    out['AFDM_LumpOrac_Indep'] = ser(xhlo, x_a, data_mask)

    Ho_a = np.exp(1j * phi_r)[:, None] * ((H_lin_t * np.exp(1j * phi_t)[None, :]) @ P_a)
    _, xhdo, _, _ = m3.oamp_exact(y_a, Ho_a, Ah_a, sig2_true, pts64, data_mask, x_p, 10)
    out['AFDM_DualOrac'] = ser(xhdo, x_a, data_mask)
    out['svd_gesvd_fallbacks'] = int(get_svd_fallback_count() - fb_start)
    return out


def compute_path_detection_stats(rows, delay_key="det_delays"):
    """Exact path detection metrics including adjacent true-path simultaneous detection rate & recall."""
    n = len(rows)
    k_exact3 = 0
    k_sup3 = 0
    k_adj_both = 0
    k_adj_path_hits = 0
    n_adj_frames = 0
    k_p0 = 0; k_pk = 0; k_p16 = 0
    k_extra = 0
    for r in rows:
        md = int(r["mid_delay"])
        true_set = {0, md, 16}
        det_set = set(int(v) for v in r[delay_key])
        if det_set == true_set:
            k_exact3 += 1
        if true_set.issubset(det_set):
            k_sup3 += 1
        if 0 in det_set:
            k_p0 += 1
        if md in det_set:
            k_pk += 1
        if 16 in det_set:
            k_p16 += 1
        if len(det_set - true_set) > 0:
            k_extra += 1
        if md == 1:
            pair = {0, 1}
        elif md == 15:
            pair = {15, 16}
        else:
            pair = None
        if pair is not None:
            n_adj_frames += 1
            if pair.issubset(det_set):
                k_adj_both += 1
            k_adj_path_hits += len(pair & det_set)
    res = {
        "n_frames": n,
        "exact_all3_count": k_exact3,
        "exact_all3_rate": float(k_exact3 / max(n, 1)),
        "exact_all3_cp95": clopper_pearson_ci(k_exact3, n),
        "superset_all3_count": k_sup3,
        "superset_all3_rate": float(k_sup3 / max(n, 1)),
        "superset_all3_cp95": clopper_pearson_ci(k_sup3, n),
        "recall_l0": float(k_p0 / max(n, 1)),
        "recall_lk": float(k_pk / max(n, 1)),
        "recall_l16": float(k_p16 / max(n, 1)),
        "false_extra_path_rate": float(k_extra / max(n, 1)),
    }
    if n_adj_frames > 0:
        res["adjacent_pair_both_detected_count"] = k_adj_both
        res["adjacent_pair_both_detected_rate"] = float(k_adj_both / n_adj_frames)
        res["adjacent_pair_both_detected_cp95"] = clopper_pearson_ci(k_adj_both, n_adj_frames)
        res["adjacent_pair_per_path_recall"] = float(k_adj_path_hits / (2.0 * n_adj_frames))
    return res


# =============================================================================
# Exact Stratified Fixed-Delay Inference (Closing Sol Blocking #1)
# Equal stratum weights w_k = 1/K, within-stratum unbiased variance/covariance
# (ddof=1 per fixed delay k), residual degrees of freedom df = N - K.
# =============================================================================
def _partition_strata_indices(strata, ks):
    strata_arr = np.asarray(strata, dtype=int)
    ks_list = [int(k) for k in ks]
    K = len(ks_list)
    if K <= 0:
        raise ValueError("ks must be non-empty")
    idx_groups = []
    total_n = 0
    for kv in ks_list:
        idx = np.where(strata_arr == kv)[0]
        if len(idx) < 2:
            raise ValueError(f"Stratum k={kv} has {len(idx)} < 2 frames; stratified variance requires n_k >= 2")
        idx_groups.append(idx)
        total_n += len(idx)
    if total_n != len(strata_arr):
        raise ValueError(f"Strata labels do not match ks={ks_list} (matched {total_n}/{len(strata_arr)})")
    n_ks = [len(idx) for idx in idx_groups]
    if len(set(n_ks)) != 1:
        raise ValueError(f"Expected equal deterministic stratum sizes, got {n_ks}")
    return idx_groups, total_n, K, n_ks[0]


def exact_int_stratified_paired_diff(a, b, strata, ks, n_syms):
    """Exact integer error-count stratified paired SER difference mean(a - b) and Student-t_{N-K} 95% CI.
    Equal stratum weights w_k = 1/K:
      Var_hat(bar_D) = sum_k w_k^2 * s_{D,k}^2 / n_k,  df = N - K = sum_k (n_k - 1).
    """
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    idx_groups, N, K, n_per_k = _partition_strata_indices(strata, ks)
    ns_i = int(n_syms)
    ka = np.rint(a * ns_i).astype(np.int64)
    kb = np.rint(b * ns_i).astype(np.int64)
    assert float(np.max(np.abs(a * ns_i - ka))) < 1e-7, "Non-integer symbol count in a"
    assert float(np.max(np.abs(b * ns_i - kb))) < 1e-7, "Non-integer symbol count in b"
    d_int = ka - kb
    d = d_int.astype(np.float64) / float(ns_i)

    # With equal stratum sizes n_per_k = N/K and w_k = 1/K, exact overall mean = sum(d_int)/(N*ns_i)
    md = float(np.sum(d_int)) / float(N * ns_i)
    w = 1.0 / float(K)
    var_mean = 0.0
    for idx in idx_groups:
        di_k = d_int[idx]
        if not np.all(di_k == di_k[0]):
            s2_k = float(np.var(d[idx], ddof=1))
            var_mean += (w * w) * (s2_k / float(n_per_k))

    df = int(N - K)
    t_crit = float(student_t.ppf(0.975, df=df))
    se = math.sqrt(max(var_mean, 0.0))
    sd_within = math.sqrt(max(var_mean * float(N), 0.0))
    hw = t_crit * se
    return {
        "mean": md,
        "sd_within": sd_within,
        "se": float(se),
        "df": df,
        "t_crit": t_crit,
        "n_strata": int(K),
        "n_per_k": int(n_per_k),
        "ci95_hw": float(hw),
        "ci95_lo": float(md - hw),
        "ci95_hi": float(md + hw),
        "pass_gt_zero": bool((md - hw) > 0.0),
    }


def stratified_paired_ll_diff(a_ll, b_ll, strata, ks):
    """Stratified paired lock-loss rate difference mean(a_ll - b_ll) with df = N - K."""
    a_ll = np.asarray(a_ll, dtype=float); b_ll = np.asarray(b_ll, dtype=float)
    idx_groups, N, K, n_per_k = _partition_strata_indices(strata, ks)
    dl = a_ll - b_ll
    ml = float(np.mean(dl))
    w = 1.0 / float(K)
    var_mean = 0.0
    for idx in idx_groups:
        dk = dl[idx]
        if not np.all(dk == dk[0]):
            var_mean += (w * w) * (float(np.var(dk, ddof=1)) / float(n_per_k))
    df = int(N - K)
    t_crit = float(student_t.ppf(0.975, df=df))
    hl = t_crit * math.sqrt(max(var_mean, 0.0))
    return {"mean": ml, "df": df, "ci95_hw": float(hl), "ci95": [float(ml - hl), float(ml + hl)]}


def stratified_paired_ratio_stats(a, b, strata, ks, M_thr=None, n_syms=None):
    """Exact stratified paired Fieller 95% CI and linearized paired-difference test
    D_i(M) = A_i - M * B_i >= 0 for E[A] / E[B] >= M across K fixed delay strata with equal
    stratum sizes n_k = N / K, weights w_k = 1 / K, within-stratum ddof=1 variance/covariance,
    and residual degrees of freedom df = N - K (guaranteeing exact algebraic equivalence between
    the stratified Fieller quadratic and the stratified linearized D(M) test!).
    """
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    idx_groups, N, K, n_per_k = _partition_strata_indices(strata, ks)
    w = 1.0 / float(K)
    df = int(N - K)
    t_crit = float(student_t.ppf(0.975, df=df))

    use_int_ab = (
        n_syms is not None and int(n_syms) > 0
        and float(np.max(np.abs(a * int(n_syms) - np.rint(a * int(n_syms))))) < 1e-7
        and float(np.max(np.abs(b * int(n_syms) - np.rint(b * int(n_syms))))) < 1e-7
    )
    if use_int_ab:
        ns_i = int(n_syms)
        ka = np.rint(a * ns_i).astype(np.int64)
        kb = np.rint(b * ns_i).astype(np.int64)
        ma = float(np.sum(ka)) / float(N * ns_i)
        mb = float(np.sum(kb)) / float(N * ns_i)
    else:
        ka = kb = None
        ma = float(np.mean(a))
        mb = float(np.mean(b))

    va = 0.0
    vb = 0.0
    cab = 0.0
    u_parts = []
    v_parts = []
    scale_fac = w / math.sqrt(float(n_per_k) * float(n_per_k - 1))
    for idx in idx_groups:
        ak = a[idx]; bk = b[idx]
        a_const = bool(np.all(ka[idx] == ka[idx][0])) if use_int_ab else bool(np.all(ak == ak[0]))
        b_const = bool(np.all(kb[idx] == kb[idx][0])) if use_int_ab else bool(np.all(bk == bk[0]))
        uk = np.zeros(n_per_k, dtype=np.float64) if a_const else (ak - float(np.mean(ak))) * scale_fac
        vk = np.zeros(n_per_k, dtype=np.float64) if b_const else (bk - float(np.mean(bk))) * scale_fac
        u_parts.append(uk)
        v_parts.append(vk)
        if not a_const:
            va += (w * w) * (float(np.var(ak, ddof=1)) / float(n_per_k))
        if not b_const:
            vb += (w * w) * (float(np.var(bk, ddof=1)) / float(n_per_k))
        if (not a_const) and (not b_const):
            cab += (w * w) * (float(np.cov(ak, bk, ddof=1)[0, 1]) / float(n_per_k))

    u_all = np.concatenate(u_parts)
    v_all = np.concatenate(v_parts)
    a_lo = ma - t_crit * math.sqrt(max(va, 0.0))

    ratio_indeterminate = bool(ma == 0.0 and mb == 0.0)
    fieller_is_disjoint = False
    fieller_disjoint_set = None
    v_res = None
    c_res = None
    if ratio_indeterminate:
        ratio = None; ratio_is_inf = False
        r_lo, r_hi = None, None
        log_hw_delta = None
    elif mb == 0.0:
        ratio = None
        ratio_is_inf = True
        r_lo = float("inf") if a_lo > 0.0 else 0.0
        r_hi = float("inf")
        log_hw_delta = 0.0
    else:
        ratio = float(int(np.sum(ka)) / int(np.sum(kb))) if use_int_ab else float(ma / mb)
        ratio_is_inf = False
        # Cancellation-free shifted Fieller quadratic in delta = r - r0 (r0 = ma / mb):
        #   A_q * delta^2 + (2 * t^2 * c_res) * delta - t^2 * v_res = 0,
        # where w_res = u_all - r0 * v_all, v_res = ||w_res||^2 >= 0, c_res = v_all . w_res.
        # Half-discriminant: t^2 * (t^2 * c_res^2 + A_q * v_res), strictly >= 0 whenever A_q > 0!
        exact_prop = False
        if use_int_ab:
            s_ka = int(np.sum(ka))
            s_kb = int(np.sum(kb))
            exact_prop = all(
                s_kb * (n_per_k * int(ka[j]) - int(np.sum(ka[idx])))
                == s_ka * (n_per_k * int(kb[j]) - int(np.sum(kb[idx])))
                for idx in idx_groups
                for j in idx
            )
        if exact_prop:
            v_res = 0.0
            c_res = 0.0
        else:
            w_res = u_all - ratio * v_all
            v_res = float(np.dot(w_res, w_res))
            c_res = float(np.dot(v_all, w_res))

        t2 = t_crit * t_crit
        A_q = mb * mb - t2 * vb
        inner_disc = t2 * (c_res * c_res) + A_q * v_res
        if A_q > 0.0:
            half_sqrt = t_crit * math.sqrt(max(inner_disc, 0.0))
            d1 = (-t2 * c_res - half_sqrt) / A_q
            d2 = (-t2 * c_res + half_sqrt) / A_q
            r1 = ratio + d1
            r2 = ratio + d2
            r_lo = max(0.0, min(r1, r2))
            r_hi = max(r1, r2)
        elif A_q < 0.0 and inner_disc >= 0.0:
            half_sqrt = t_crit * math.sqrt(inner_disc)
            r_a = ratio + (-t2 * c_res - half_sqrt) / A_q
            r_b = ratio + (-t2 * c_res + half_sqrt) / A_q
            r_small, r_large = min(r_a, r_b), max(r_a, r_b)
            if r_small < 0.0 and r_large > 0.0:
                r_lo = float(r_large)
                r_hi = float("inf")
            elif r_small >= 0.0 and r_large > r_small:
                fieller_is_disjoint = True
                fieller_disjoint_set = [[0.0, float(r_small)], [float(r_large), None]]
                r_lo = 0.0
                r_hi = float("inf")
            else:
                r_lo, r_hi = 0.0, float("inf")
        elif A_q == 0.0 and (2.0 * t2 * c_res) < 0.0 and (ma * ma - t2 * va) > 0.0:
            r_lo = max(0.0, ratio + v_res / (2.0 * c_res))
            r_hi = float("inf")
        else:
            r_lo, r_hi = 0.0, float("inf")

        if ma > 0.0 and mb > 0.0:
            log_hw_delta = float(t_crit * math.sqrt(max(v_res, 0.0)) / ma)
        else:
            log_hw_delta = None

    fieller_log_hw = None
    if (r_lo is not None and r_hi is not None
            and math.isfinite(r_lo) and math.isfinite(r_hi)
            and r_lo > 0.0 and r_hi > 0.0):
        fieller_log_hw = float(0.5 * math.log(r_hi / r_lo))

    res = {
        "df": df,
        "t_crit": t_crit,
        "n_strata": int(K),
        "n_per_k": int(n_per_k),
        "var_mean_a": float(va),
        "var_mean_b": float(vb),
        "cov_mean_ab": float(cab),
        "var_res_ratio": v_res,
        "cov_b_res_ratio": c_res,
        "ratio": ratio,
        "ratio_is_inf": ratio_is_inf,
        "ratio_indeterminate": ratio_indeterminate,
        "fieller_lo": (None if (r_lo is None or not math.isfinite(r_lo)) else float(r_lo)),
        "fieller_lo_is_inf": bool(r_lo is not None and math.isinf(r_lo) and r_lo > 0.0),
        "fieller_hi": (None if (r_hi is None or not math.isfinite(r_hi)) else float(r_hi)),
        "fieller_hi_is_inf": bool(r_hi is not None and math.isinf(r_hi) and r_hi > 0.0),
        "fieller_is_disjoint": fieller_is_disjoint,
        "fieller_disjoint_set": fieller_disjoint_set,
        "fieller_log_hw": fieller_log_hw,
        "log_hw_delta": log_hw_delta,
        "rival_mean_ci95_lo": float(a_lo),
    }
    if M_thr is not None:
        use_exact_int = bool(use_int_ab and float(M_thr).is_integer())
        var_md = 0.0
        if use_exact_int:
            ns_i = int(n_syms)
            d_int = ka - int(M_thr) * kb
            d = d_int.astype(np.float64) / float(ns_i)
            md = float(np.sum(d_int)) / float(N * ns_i)
            for idx in idx_groups:
                di_k = d_int[idx]
                if not np.all(di_k == di_k[0]):
                    var_md += (w * w) * (float(np.var(d[idx], ddof=1)) / float(n_per_k))
        else:
            d = a - float(M_thr) * b
            md = float(np.mean(d))
            for idx in idx_groups:
                dk = d[idx]
                if not np.all(dk == dk[0]):
                    var_md += (w * w) * (float(np.var(dk, ddof=1)) / float(n_per_k))
        sed = math.sqrt(max(var_md, 0.0))
        d_lo = md - t_crit * sed
        res["threshold_M"] = float(M_thr)
        res["linearized_diff_mean"] = float(md)
        res["linearized_diff_se"] = float(sed)
        res["linearized_diff_ci95_lo"] = float(d_lo)
        res["pass_ci95_lower_bound"] = bool((d_lo >= 0.0) and (a_lo > 0.0))
    return res


def summarize_holdout_cell(rows, ks, ratio_thresholds, ref_key="AFDM_EP_Dual_Sym6"):
    arm_keys = [k for k in rows[0].keys() if k.startswith("AFDM_")]
    n = len(rows)
    n_syms = int(rows[0]["n_data_syms"])
    strata = np.array([int(r["mid_delay"]) for r in rows], dtype=int)
    ref_arr = np.array([r[ref_key] for r in rows], dtype=float)
    ref_ll = (ref_arr > 0.05).astype(float)

    s = {
        "n_frames": n,
        "ks": [int(k) for k in ks],
        "n_strata": int(len(ks)),
        "n_per_k": int(n // len(ks)),
        "stratified_df": int(n - len(ks)),
        "n_data_syms": n_syms,
        "svd_gesvd_fallbacks_total": int(sum(int(r.get("svd_gesvd_fallbacks", 0)) for r in rows)),
        "svd_gesvd_fallback_frames": int(sum(1 for r in rows if int(r.get("svd_gesvd_fallbacks", 0)) > 0)),
        "means": {},
        "lock_loss_gt5pct": {},
        "paired_diff_vs_ref": {},
        "paired_ll_diff_vs_ref": {},
        "paired_ratio_vs_ref": {},
        "path_detection": compute_path_detection_stats(rows, "det_delays"),
        "per_k_breakdown": {},
        "energy_ratio_mean": float(np.mean([r["energy_ratio_comb_to_ep"] for r in rows])),
        "max_base_energy_diff": float(np.max([r["base_energy_diff"] for r in rows])),
    }
    if "det_delays_legacy" in rows[0]:
        s["path_detection_legacy"] = compute_path_detection_stats(rows, "det_delays_legacy")

    for k in arm_keys:
        arr = np.array([r[k] for r in rows], dtype=float)
        ll = (arr > 0.05).astype(float)
        s["means"][k] = float(np.mean(arr))
        s["lock_loss_gt5pct"][k] = float(np.mean(ll))
        if k != ref_key:
            s["paired_diff_vs_ref"][k] = exact_int_stratified_paired_diff(arr, ref_arr, strata, ks, n_syms)
            s["paired_ll_diff_vs_ref"][k] = stratified_paired_ll_diff(ll, ref_ll, strata, ks)
            s["paired_ratio_vs_ref"][k] = stratified_paired_ratio_stats(
                arr, ref_arr, strata, ks, M_thr=ratio_thresholds.get(k, None), n_syms=n_syms
            )

    # Stratified per-k diagnostic breakdown (non-gating, full transparency across every k, incl. legacy path detection!)
    for kv in ks:
        sub = [r for r in rows if int(r["mid_delay"]) == int(kv)]
        sub_strata = np.full(len(sub), int(kv), dtype=int)
        sub_ref = np.array([r[ref_key] for r in sub], dtype=float)
        entry = {
            "n_frames": len(sub),
            "svd_gesvd_fallbacks_total": int(sum(int(r.get("svd_gesvd_fallbacks", 0)) for r in sub)),
            "svd_gesvd_fallback_frames": int(sum(1 for r in sub if int(r.get("svd_gesvd_fallbacks", 0)) > 0)),
            "means": {ak: float(np.mean([r[ak] for r in sub])) for ak in arm_keys},
            "lock_loss_gt5pct": {ak: float(np.mean([r[ak] > 0.05 for r in sub])) for ak in arm_keys},
            "path_detection": compute_path_detection_stats(sub, "det_delays"),
            "paired_ratio_vs_ref": {},
        }
        if "det_delays_legacy" in sub[0]:
            entry["path_detection_legacy"] = compute_path_detection_stats(sub, "det_delays_legacy")
        for rk, M in ratio_thresholds.items():
            sub_a = np.array([r[rk] for r in sub], dtype=float)
            entry["paired_ratio_vs_ref"][rk] = stratified_paired_ratio_stats(
                sub_a, sub_ref, sub_strata, [int(kv)], M_thr=M, n_syms=n_syms
            )
        if "AFDM_EP_Dual_Sym6_NoCMSep" in sub[0]:
            sub_leg = np.array([r["AFDM_EP_Dual_Sym6_NoCMSep"] for r in sub], dtype=float)
            entry["paired_diff_nocmsep"] = exact_int_stratified_paired_diff(
                sub_leg, sub_ref, sub_strata, [int(kv)], n_syms
            )
        s["per_k_breakdown"][f"k={kv}"] = entry
    return s


def run_startup_gates(eq_seed):
    """Fail-fast startup verification:
      1. Exact MD5 cryptographic match of untouched frozen `l2_m_r12_m03_modtest.py` (checked FIRST!)
      2. Exact 0.0 bit-for-bit SER/energy identity AND 0 SVD fallbacks at k=7 on R4 and R5 vs `m3.run_single_frame`
      3. Projected Jacobian FD check < 1e-6
    """
    install_svd_gesvd_fallback()
    mod_path = os.path.abspath(m3.__file__)
    with open(mod_path, "rb") as fp:
        actual_md5 = hashlib.md5(fp.read()).hexdigest()
    md5_ok = (actual_md5 == FROZEN_MODTEST_MD5)
    if not md5_ok:
        return {
            "frozen_modtest_path": mod_path,
            "frozen_modtest_md5_expected": FROZEN_MODTEST_MD5,
            "frozen_modtest_md5_actual": actual_md5,
            "frozen_modtest_md5_ok": False,
            "aborted_before_gates": True,
            "GATES_OK": False,
        }

    fd_err = float(m3.verify_projected_jacobian_fd())

    base_cfg = dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268,
                    max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3)
    max_diff = 0.0
    fb_before = get_svd_fallback_count()
    for idx_m, eq_mode in enumerate(("single_frame", "prior_pn")):
        r_ref = m3.run_single_frame((eq_seed + idx_m, dict(base_cfg, mode=eq_mode, channel_mode="coprime3")))
        r_new = run_frozen_holdout_frame((eq_seed + idx_m, dict(base_cfg, mode=eq_mode, mid_delay=7)))
        for ak, av in r_ref.items():
            diff = abs(float(r_new[ak]) - float(av))
            if diff > max_diff:
                max_diff = diff
    k7_fallbacks = int(get_svd_fallback_count() - fb_before)
    bit_exact_ok = (max_diff == 0.0) and (k7_fallbacks == 0)
    gates_ok = bool(md5_ok and bit_exact_ok and (fd_err < 1e-6))
    return {
        "frozen_modtest_path": mod_path,
        "frozen_modtest_md5_expected": FROZEN_MODTEST_MD5,
        "frozen_modtest_md5_actual": actual_md5,
        "frozen_modtest_md5_ok": md5_ok,
        "k7_bit_exact_max_diff": float(max_diff),
        "k7_svd_gesvd_fallbacks": k7_fallbacks,
        "k7_bit_exact_ok": bit_exact_ok,
        "fd_jacobian_rel_err": fd_err,
        "GATES_OK": gates_ok,
    }


def main():
    print(sys.executable, flush=True)
    smoke = ("--smoke" in sys.argv)
    n_workers = 1 if smoke else min(8, os.cpu_count() or 4)
    out_path = (
        sys.argv[sys.argv.index("--out") + 1]
        if "--out" in sys.argv
        else "/data/guoyikun/tmp/funnel_m_r14/summary_m_r12_m03_delay_holdout.json"
    )

    # Strictly disjoint fresh seed namespace (0% overlap with m02, m03 R11/R12, R12 dev/smoke, holdout dev 11000001+)
    SEED_BASE = 2029500001 if smoke else 2027500001
    EQ_SEED = 2029590001 if smoke else 2027590001

    t0 = time.time()
    gates = run_startup_gates(EQ_SEED)
    print(f"[STARTUP GATES] GATES_OK={gates['GATES_OK']} | md5_ok={gates['frozen_modtest_md5_ok']} | "
          f"k7_bit_exact_diff={gates.get('k7_bit_exact_max_diff')} | k7_svd_fb={gates.get('k7_svd_gesvd_fallbacks')} | "
          f"FD={gates.get('fd_jacobian_rel_err')}", flush=True)
    if not gates["GATES_OK"]:
        print("FATAL: Startup gates failed; aborting immediately.", flush=True)
        sys.exit(2)

    base_cfg = dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268,
                    max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3)

    # Pre-registered Red Line #5 stratified sample sizes (equal frames per k in each group)
    cells = [
        ("Sep_R4_SingleFrameBlind", "single_frame", SEPARATED_KS, 2 if smoke else 280, {"AFDM_Xu_LumpPCA_Sym6": 4.0, "AFDM_EP_Dual_Sym6_NoCMSep": 1.0}),
        ("Sep_R5_PNTrain",          "prior_pn",     SEPARATED_KS, 2 if smoke else 80,  {"AFDM_Xu_LumpPCA_Sym6": 5.0, "AFDM_Gavert_Comb_CovDIC6": 5.0}),
        ("Adj_R4_SingleFrameBlind", "single_frame", ADJACENT_KS,  5 if smoke else 100, {"AFDM_Xu_LumpPCA_Sym6": 4.0, "AFDM_EP_Dual_Sym6_NoCMSep": 1.0}),
        ("Adj_R5_PNTrain",          "prior_pn",     ADJACENT_KS,  5 if smoke else 60,  {"AFDM_Xu_LumpPCA_Sym6": 5.0, "AFDM_Gavert_Comb_CovDIC6": 5.0}),
    ]

    results = {
        "meta": {
            "card": "I-20261125-m03",
            "test_type": "frozen_receiver_3path_delay_holdout",
            "label_zh": "冻结接收机的三径时延留出检验（仅裁主张范围、不改方法与历史裁决）",
            "astra_trigger": "ideas/reviews/r12-astra-m03-killarg-20261126.md (STEP8: REVISE)",
            "inference_method": "stratified_fixed_delay_equal_weights_df_N_minus_K",
            "svd_fallback_policy": "exception_only_scipy_gesvd_on_LinAlgError_wrapper_on_m3_np_linalg_svd",
            "seed_base": SEED_BASE,
            "eq_seed": EQ_SEED,
            "smoke": smoke,
            "n_workers": n_workers,
            "python": sys.executable,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "startup_gates": gates,
        "cells": {},
    }

    total_svd_fb = 0
    total_svd_fb_frames = 0
    for ci, (cname, mode, ks, n_per_k, thrs) in enumerate(cells):
        tc = time.time()
        tasks = []
        idx = 0
        for kv in ks:
            for _ in range(n_per_k):
                tasks.append((SEED_BASE + ci * 10000 + idx, dict(base_cfg, mode=mode, mid_delay=int(kv))))
                idx += 1
        if n_workers > 1:
            with Pool(n_workers, initializer=install_svd_gesvd_fallback) as pool:
                rows = pool.map(run_frozen_holdout_frame, tasks)
        else:
            rows = [run_frozen_holdout_frame(t) for t in tasks]
        summ = summarize_holdout_cell(rows, ks, thrs)
        summ["elapsed_s"] = round(time.time() - tc, 1)
        total_svd_fb += summ["svd_gesvd_fallbacks_total"]
        total_svd_fb_frames += summ["svd_gesvd_fallback_frames"]
        results["cells"][cname] = summ
        m = summ["means"]; pd_info = summ["path_detection"]
        adj_str = (f" | adj_both={pd_info['adjacent_pair_both_detected_rate']*100:.1f}% "
                   f"adj_rec={pd_info['adjacent_pair_per_path_recall']*100:.1f}%") if "adjacent_pair_both_detected_rate" in pd_info else ""
        extra_str = f" | NoCMSep={m['AFDM_EP_Dual_Sym6_NoCMSep']:.3e}" if "AFDM_EP_Dual_Sym6_NoCMSep" in m else f" | GavComb={m['AFDM_Gavert_Comb_CovDIC6']:.3e}"
        print(f"[{cname}] (n={summ['n_frames']}, df={summ['stratified_df']}, svd_fb={summ['svd_gesvd_fallbacks_total']}, {summ['elapsed_s']}s) "
              f"exact3={pd_info['exact_all3_rate']*100:.1f}%{adj_str} | "
              f"EP_Dual={m['AFDM_EP_Dual_Sym6']:.3e}({summ['lock_loss_gt5pct']['AFDM_EP_Dual_Sym6']*100:.1f}%) | "
              f"Xu={m['AFDM_Xu_LumpPCA_Sym6']:.3e}{extra_str}", flush=True)

    results["svd_gesvd_fallbacks_total"] = int(total_svd_fb)
    results["svd_gesvd_fallback_frames_total"] = int(total_svd_fb_frames)

    # Pre-registered Per-Group Scope Verdicts (UNCHANGED original thresholds, ALL by exact stratified paired 95% CI lower bounds!)
    C = results["cells"]
    sep_r4 = C["Sep_R4_SingleFrameBlind"]; sep_r5 = C["Sep_R5_PNTrain"]
    adj_r4 = C["Adj_R4_SingleFrameBlind"]; adj_r5 = C["Adj_R5_PNTrain"]

    sep_r4_xu_4x = bool(sep_r4["paired_ratio_vs_ref"]["AFDM_Xu_LumpPCA_Sym6"]["pass_ci95_lower_bound"])
    sep_r4_cmsep = bool(sep_r4["paired_diff_vs_ref"]["AFDM_EP_Dual_Sym6_NoCMSep"]["pass_gt_zero"])
    sep_r5_xu_5x = bool(sep_r5["paired_ratio_vs_ref"]["AFDM_Xu_LumpPCA_Sym6"]["pass_ci95_lower_bound"])
    sep_r5_gav_5x = bool(sep_r5["paired_ratio_vs_ref"]["AFDM_Gavert_Comb_CovDIC6"]["pass_ci95_lower_bound"])
    pass_separated = bool(gates["GATES_OK"] and sep_r4_xu_4x and sep_r4_cmsep and sep_r5_xu_5x and sep_r5_gav_5x)

    adj_r4_xu_4x = bool(adj_r4["paired_ratio_vs_ref"]["AFDM_Xu_LumpPCA_Sym6"]["pass_ci95_lower_bound"])
    adj_r4_cmsep = bool(adj_r4["paired_diff_vs_ref"]["AFDM_EP_Dual_Sym6_NoCMSep"]["pass_gt_zero"])
    adj_r5_xu_5x = bool(adj_r5["paired_ratio_vs_ref"]["AFDM_Xu_LumpPCA_Sym6"]["pass_ci95_lower_bound"])
    adj_r5_gav_5x = bool(adj_r5["paired_ratio_vs_ref"]["AFDM_Gavert_Comb_CovDIC6"]["pass_ci95_lower_bound"])
    pass_adjacent = bool(gates["GATES_OK"] and adj_r4_xu_4x and adj_r4_cmsep and adj_r5_xu_5x and adj_r5_gav_5x)

    if not gates["GATES_OK"]:
        scope_decision = "GATE_FAILED"
    elif pass_separated and pass_adjacent:
        scope_decision = "BOTH_SEPARATED_AND_ADJACENT_PASS"
    elif pass_separated and not pass_adjacent:
        scope_decision = "RESTRICT_TO_SEPARATED_3PATH"
    else:
        scope_decision = "RETRACT_CROSS_GEOMETRY_MULTIPLIER_CLAIM"

    results["verdicts"] = {
        "GATES_OK": gates["GATES_OK"],
        "SEP_R4_XU_4X": sep_r4_xu_4x,
        "SEP_R4_CMSEP_MECH": sep_r4_cmsep,
        "SEP_R5_XU_5X": sep_r5_xu_5x,
        "SEP_R5_GAVCOMB_5X": sep_r5_gav_5x,
        "PASS_SEPARATED": pass_separated,
        "ADJ_R4_XU_4X": adj_r4_xu_4x,
        "ADJ_R4_CMSEP_MECH": adj_r4_cmsep,
        "ADJ_R5_XU_5X": adj_r5_xu_5x,
        "ADJ_R5_GAVCOMB_5X": adj_r5_gav_5x,
        "PASS_ADJACENT": pass_adjacent,
        "CLAIM_SCOPE_DECISION": scope_decision,
    }
    results["total_elapsed_s"] = round(time.time() - t0, 1)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2, allow_nan=False)
    print(f"\n[VERDICTS] {json.dumps(results['verdicts'])} (svd_fb={total_svd_fb}, total {results['total_elapsed_s']}s) -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
