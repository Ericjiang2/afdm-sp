"""
Completes Sol Call 4's exact missing controls on C8-UnkHI (`R2_UnkHI_16QAM_30dB_D20_INR25`):
  - WL-LMMSE (Widely-Linear LMMSE — checking improper/non-circular residual structure)
  - Bussgang / ZMNL Soft-Clipping + LMMSE/OAMP
  - Huber-IRLS CE + Huber-IRLS OAMP
  - SM5_ConvSpread_CovEM_3DD: Sol's exact 7-tap source-to-receiver spread-propagated blind covariance EM!
"""
import math, sys, numpy as np
from concurrent.futures import ProcessPoolExecutor
from scipy.linalg import cho_factor, cho_solve
sys.path.insert(0, "ideas/r15")
import td_m_p1b_c3_bursty_impulsive as c3m
import td_m_p1b_c8_joint_ce_bursty as c8
import td_m_p1b_c8_nassar_audit as cn
import td_m_p1b_c8_unkHI_formal as cu

def run_one(seed):
    N = 256; P = 4; l_max = 6; k_max = 1.5; L_I = 7
    snr_db, inr_db, duty, mean_burst = 30.0, 25.0, 0.20, 8.0
    rng = np.random.default_rng(seed)
    const = c3m.gray_qam(16); sigma0_sq = 10.0 ** (-snr_db / 10.0); I_N = np.eye(N, dtype=np.complex128)
    delays = np.sort(rng.choice(np.arange(0, l_max + 1), size=P, replace=False)); delays[0] = 0
    dopplers = rng.uniform(-k_max, k_max, size=P)
    pdp = np.exp(-0.22 * delays); pdp /= np.sum(pdp)
    gains = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) * np.sqrt(pdp / 2.0)
    gains /= max(np.linalg.norm(gains), 1e-12)
    H_I_true, _ = cu.build_unknown_HI(N, L_I, rng)

    clusters = [np.arange(0, 16), np.arange(64, 80), np.arange(128, 144), np.arange(192, 208)]
    obs_clusters = [np.arange(c[0] + l_max, c[-1] + 1) for c in clusters]
    obs_pil_all = np.concatenate(obs_clusters)
    pil_t = np.concatenate(clusters); data_t = np.setdiff1d(np.arange(N), pil_t); Nd = len(data_t); didx = np.arange(Nd)
    u_pil = np.exp(-1j * math.pi * 7.0 * np.arange(len(pil_t)) * (np.arange(len(pil_t)) + 1) / float(len(pil_t)))
    x_data = const[rng.integers(0, len(const), size=Nd)]
    s_pil = np.zeros(N, dtype=np.complex128); s_pil[pil_t] = u_pil
    e_pre, states, v_z, ms = c3m.gen_markov_burst_noise(N, sigma0_sq, duty, mean_burst, inr_db, rng)
    w_bg = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sigma0_sq / 2.0)
    C_true = sigma0_sq * I_N + (H_I_true * v_z[None, :]) @ H_I_true.conj().T
    p01, p10, sigma_I_sq = ms["p01"], ms["p10"], ms["sigma_I_sq"]

    c1 = 5.0 / (2.0 * N)
    H_true = c8.build_H_from_paths(N, delays, dopplers, gains, cpp_c1=c1)
    U_d = c3m.daft_mat(Nd, 5.0 / (2.0 * Nd), 1.0 / (2.0 * math.pi * Nd))
    s_true = s_pil.copy(); s_true[data_t] = U_d.conj().T @ x_data
    y = H_true @ s_true + H_I_true @ e_pre + w_bg
    A_true = H_true[:, data_t] @ U_d.conj().T

    # 1. Huber-IRLS CE + Huber-IRLS OAMP
    med_p = float(np.median(np.abs(y[obs_pil_all]))); T_p = max(2.2 * med_p, 2.5)
    w_h = np.ones(N); w_h[obs_pil_all] = np.minimum(1.0, T_p / np.maximum(np.abs(y[obs_pil_all]), 1e-12))
    H_h = c8.omp_continuous_ce(y, s_pil, obs_pil_all, N, P, l_max, k_max, c1, weights=w_h)
    x_hub = c3m.rx_huber_oamp(y - H_h @ s_pil, H_h[:, data_t] @ U_d.conj().T, sigma0_sq, const, None, None, 6)

    # 2. ZMNL / Bussgang soft-clipping + LMMSE/OAMP
    x_zmnl = c3m.rx_zmnl(y - H_h @ s_pil, H_h[:, data_t] @ U_d.conj().T, sigma0_sq, const, None, None)

    # 3. Widely-Linear (WL) LMMSE (augmented [y; y*] with empirical improper residual cov!)
    y_d = y - H_h @ s_pil; A_d = H_h[:, data_t] @ U_d.conj().T
    r_pil = y_d[obs_pil_all]
    sig_r2 = max(float(np.mean(np.abs(r_pil) ** 2)), sigma0_sq)
    p_r = float(np.abs(np.mean(r_pil ** 2)))  # pseudo-covariance magnitude
    # Augmented real-valued 2N x 2Nd LMMSE (widely linear)
    A_aug = np.block([[A_d, np.zeros_like(A_d)], [np.zeros_like(A_d), np.conj(A_d)]])
    y_aug = np.concatenate([y_d, np.conj(y_d)])
    c_p = np.mean(r_pil ** 2)
    C_aug = np.block([[sig_r2 * I_N, c_p * I_N], [np.conj(c_p) * I_N, sig_r2 * I_N]])
    x_wl = c3m.full_cov_lmmse(y_aug, A_aug, C_aug)[:Nd]

    # 4. Sol's SM5_ConvSpread_CovEM_3DD: explicitly propagates 7-tap source burst spread into covariance!
    H_1 = cn.pilot_joint_sparse_ce(y, s_pil, I_N, obs_pil_all, obs_clusters, N, P, l_max, k_max, c1, sigma0_sq, sigma_I_sq)
    x_5, _, _, g_5, _ = cn.joint_nassar_ep_fg(y - H_1 @ s_pil, H_1[:, data_t] @ U_d.conj().T, I_N, sigma0_sq, const, sigma_I_sq, p01, p10, n_iters=12)
    H_5 = H_1.copy()
    pdp_kern = np.exp(-0.18 * np.arange(L_I)); pdp_kern /= np.sum(pdp_kern)
    for _ in range(3):
        s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_5
        r_5 = y - H_5 @ s_soft
        # Deconvolve/propagate 7-tap causal burst envelope: if source bursts at n, obs spread over n..n+L_I-1!
        e2 = np.abs(r_5) ** 2; s0_e = max(sigma0_sq, 0.5 * float(np.median(e2)) / 0.6931)
        s1_e = max(s0_e + sigma_I_sq, 10.0 * s0_e)
        g_raw = c3m.hmm_fb_2state(-np.log(s0_e) - e2 / s0_e, -np.log(s1_e) - e2 / s1_e, p01, p10)
        # Estimate source activity via non-negative Toeplitz deconvolution, then propagate via pdp_kern AND causal Toeplitz R!
        g_spread = np.clip(np.convolve(g_raw, pdp_kern, mode="full")[:N], 0.0, 1.0)
        C_5 = cu.est_banded_psd_toeplitz_cov(r_5, np.maximum(g_raw, g_spread), sigma0_sq, sigma_I_sq, N, L_lag=L_I)
        x_5 = c3m.full_cov_ep_oamp(y - H_5 @ s_pil, H_5[:, data_t] @ U_d.conj().T, C_5, const, None, None, n_iters=8, damp=0.65)
        s_soft = s_pil.copy(); s_soft[data_t] = U_d.conj().T @ x_5
        L_c = np.linalg.cholesky(C_5 + 1e-9 * I_N)
        H_5 = c8.omp_continuous_ce(y, s_soft, np.arange(N), N, P, l_max, k_max, c1, C_inv_sqrt=np.linalg.solve(L_c, I_N))
    x_5 = c3m.full_cov_ep_oamp(y - H_5 @ s_pil, H_5[:, data_t] @ U_d.conj().T, C_5, const, None, None, n_iters=8, damp=0.65)

    x_or = c3m.full_cov_ep_oamp(y - H_true @ s_pil, A_true, C_true, const, None, None, n_iters=10, damp=0.65)
    return {
        "Ctrl_WL_LMMSE": c3m.hard_ser_sub(x_wl, x_data, const, didx),
        "Ctrl_ZMNL_Bussgang": c3m.hard_ser_sub(x_zmnl, x_data, const, didx),
        "Ctrl_Huber_IRLS_OAMP": c3m.hard_ser_sub(x_hub, x_data, const, didx),
        "SM5_ConvSpread_CovEM_3DD": c3m.hard_ser_sub(x_5, x_data, const, didx),
        "Oracle": c3m.hard_ser_sub(x_or, x_data, const, didx),
    }

if __name__ == "__main__":
    import json
    with ProcessPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(run_one, [951000 + t for t in range(48)]))
    for k in rows[0]:
        arr = np.array([r[k] for r in rows])
        print(f"  {k:26s}: {np.mean(arr):.5f} +/- {np.std(arr, ddof=1)/math.sqrt(len(arr)):.5f}")

    out = {k: {"mean": float(np.mean([r[k] for r in rows])), "se": float(np.std([r[k] for r in rows], ddof=1)/math.sqrt(len(rows)))} for k in rows[0]}
    json.dump(out, open("ideas/r15/out_p1b_c8_unkHI_sol_controls.json", "w"), indent=2)
