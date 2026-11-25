#!/usr/bin/env python3
"""Read-only L1 probe (<15s) for I-20261123-g06:
Position-asymmetric sparse activation schedule for waveguide-fed pinching-antenna
channel estimation under per-slot multiplicative upstream shadowing.

Compares under the exact coupled-mode prefix operator A(W)_{t,n} = W_{t,n} g_n prod_{i<n} beta_i^{W_{t,i}}
with matched T = N pilot slots:
  1. Serial (W = I_N, Xiao arXiv:2509.02403v2 baseline winner in lossy regime)
  2. Dense S-Matrix w/ Xiao fixed-leakage model (arXiv:2509.02403v2 Eq. 20)
  3. Dense S-Matrix w/ exact state-dependent unmixing A(W_S)^{-1}
  4. Wuttig-style best sparse cyclic constant-weight code (naive_port from linear photon-noise multiplexing, Wuttig 2005)
  5. Equal-column-weight coordinate-polished code (symmetric sparsity ablation)
  6. Position-asymmetric shadow-graded schedule (upstream-sparse, downstream-dense)

Also verifies:
  - End-to-end 4-user uplink LMMSE sum-rate (bps/Hz) at pilot/data SNR = 15 dB
  - Sol's strong-shadowing boundary (alpha >= 0.78 -> Serial becomes strictly optimal)
"""
import time
import numpy as np


def hadamard_sylvester(n):
    H = np.array([[1.0]])
    while H.shape[0] < n:
        H = np.block([[H, H], [H, -H]])
    return H


def build_A(W, g0, beta):
    log_b = np.log(np.maximum(beta, 1e-15))
    w_lb = W * log_b[None, :]
    up_log = np.zeros_like(w_lb)
    up_log[:, 1:] = np.cumsum(w_lb[:, :-1], axis=1)
    return W * g0[None, :] * np.exp(up_log)


def mse_trace(W, g0, beta):
    A = build_A(W, g0, beta)
    G = A.conj().T @ A
    try:
        val = float(np.real(np.trace(np.linalg.inv(G))))
        return val if val > 0 and np.isfinite(val) else 1e30
    except np.linalg.LinAlgError:
        return 1e30


def euler_lagrange_duty(g0, alpha):
    N = len(g0)
    w_n = 1.0 / np.maximum(np.abs(g0) ** 2, 1e-30)
    p = np.full(N, 0.20)
    pg = np.linspace(1.0 / N, 0.50, 250)[None, :]
    lhs = (1.0 - pg) / ((pg ** 2) * ((1.0 - 0.5 * pg) ** 2))
    log_loss = np.abs(np.log(np.maximum(1.0 - alpha ** 2, 1e-12)))
    for _ in range(80):
        S = np.concatenate([[0.0], np.cumsum(p[:-1] * log_loss[:-1])])
        J = w_n * np.exp(S) / (p * (1.0 - 0.5 * p))
        R = np.cumsum(J[::-1])[::-1] - J
        c_rhs = log_loss * R / (w_n * np.exp(S) + 1e-30)
        idx_p = np.argmin(np.abs(lhs - c_rhs[:, None]), axis=1)
        p_new = pg[0, idx_p]
        p_new[-1] = 0.50
        p = 0.5 * p + 0.5 * p_new
    return np.clip(np.round(p * N).astype(int), 1, N // 2)


def build_asym_schedule(g0, alpha, beta, rng, w_cyc_init=None, n_init=30, sweeps=6):
    N = len(g0)
    w_n = 1.0 / np.maximum(np.abs(g0) ** 2, 1e-30)
    k_tgt = euler_lagrange_duty(g0, alpha)
    best_cand_W = None
    best_cand_m = 1e30

    for _ in range(n_init):
        W_try = np.zeros((N, N))
        for col in range(N - 1, -1, -1):
            kt = int(k_tgt[col])
            if col == N - 1:
                chosen = rng.choice(N, kt, replace=False)
            else:
                placed = W_try[:, col + 1:]
                sh_cost = placed @ (w_n[col + 1:] / np.mean(w_n[col + 1:]))
                chosen = np.argsort(sh_cost + rng.uniform(0.0, 2.5, N))[:kt]
            W_try[chosen, col] = 1.0
        if np.linalg.matrix_rank(W_try) == N:
            m = mse_trace(W_try, g0, beta)
            if m < best_cand_m:
                best_cand_m, best_cand_W = m, W_try.copy()

    def polish_one(W_start):
        Wp = W_start.copy()
        mp = mse_trace(Wp, g0, beta)
        for _ in range(sweeps):
            imp = False
            for r in range(N):
                for c in range(N):
                    Wp[r, c] = 1.0 - Wp[r, c]
                    mt = mse_trace(Wp, g0, beta)
                    if mt < mp - 1e-9:
                        mp = mt
                        imp = True
                    else:
                        Wp[r, c] = 1.0 - Wp[r, c]
            if not imp:
                break
        return Wp, mp

    seeds_W = [np.eye(N)]
    if best_cand_W is not None:
        seeds_W.append(best_cand_W)
    if w_cyc_init is not None:
        seeds_W.append(w_cyc_init)

    best_final_W, best_final_m = np.eye(N), mse_trace(np.eye(N), g0, beta)
    for Ws in seeds_W:
        Wp, mp = polish_one(Ws)
        if mp < best_final_m:
            best_final_W, best_final_m = Wp, mp
    return best_final_W, best_final_m, k_tgt


def best_wuttig_cyclic_and_const_col(g0, beta, rng):
    N = len(g0)
    best_cyc_m = 1e30
    best_cyc_W = np.eye(N)
    best_K = 1
    for K in range(1, N // 2 + 1):
        if K == 1:
            m1 = mse_trace(np.eye(N), g0, beta)
            if m1 < best_cyc_m:
                best_cyc_m, best_cyc_W, best_K = m1, np.eye(N), 1
            continue
        for _ in range(45):
            r0 = np.zeros(N)
            r0[rng.choice(N, K, replace=False)] = 1.0
            Wc = np.array([np.roll(r0, r) for r in range(N)])
            if np.linalg.matrix_rank(Wc) == N:
                mc = mse_trace(Wc, g0, beta)
                if mc < best_cyc_m:
                    best_cyc_m, best_cyc_W, best_K = mc, Wc.copy(), K

    # Ablation: allow non-cyclic pairwise swaps within EACH column keeping uniform column weight == best_K!
    W_eq = best_cyc_W.copy()
    m_eq = best_cyc_m
    if best_K > 1:
        for _ in range(250):
            col = int(rng.integers(0, N))
            ones = np.where(W_eq[:, col] > 0.5)[0]
            zeros = np.where(W_eq[:, col] < 0.5)[0]
            if len(ones) == 0 or len(zeros) == 0:
                continue
            r1 = int(rng.choice(ones))
            r0 = int(rng.choice(zeros))
            W_eq[r1, col], W_eq[r0, col] = 0.0, 1.0
            mt = mse_trace(W_eq, g0, beta)
            if mt < m_eq - 1e-9:
                m_eq = mt
            else:
                W_eq[r1, col], W_eq[r0, col] = 1.0, 0.0
    return best_cyc_W, best_cyc_m, best_K, W_eq, m_eq


def eval_uplink_rate(N, d_n, g0, beta, schedules, snr_db=15.0, n_mc=120):
    """4-user spherical-wave PASS uplink rate (bps/Hz) when M_wg=4 parallel waveguides or N-PA virtual beamforming
    uses estimated channels h_hat from matched T=N pilot slots."""
    rng = np.random.default_rng(999)
    K_ue = 4
    lam = 0.0107  # 28 GHz
    lam_g = lam / 1.4
    sigma2 = 10.0 ** (-snr_db / 10.0) * float(np.mean(np.abs(g0) ** 2))
    g_complex = g0 * np.exp(-1j * 2 * np.pi * d_n / lam_g)

    A_mats = {k: build_A(W, g_complex, beta) for k, W in schedules.items()}
    pinv_mats = {k: np.linalg.pinv(A) for k, A in A_mats.items()}
    # Xiao mismatched estimator on W_S:
    W_S = schedules["S_Exact"]
    g_par_xiao = g_complex * np.concatenate([[1.0], np.cumprod(beta[:-1])])
    L_xiao = np.linalg.pinv(W_S * g_par_xiao[None, :])

    rates = {k: [] for k in list(schedules.keys()) + ["Oracle_CSI", "S_XiaoMM"]}
    for _ in range(n_mc):
        # 4 users in 30m x 10m region, height 3m
        ux = rng.uniform(2.0, 28.0, K_ue)
        uy = rng.uniform(-5.0, 5.0, K_ue)
        dist = np.sqrt((d_n[:, None] - ux[None, :]) ** 2 + uy[None, :] ** 2 + 3.0 ** 2)
        H_los = (np.exp(-1j * 2 * np.pi * dist / lam) / dist)
        H_nlos = 0.25 * (rng.standard_normal((N, K_ue)) + 1j * rng.standard_normal((N, K_ue))) / np.sqrt(2.0) / np.mean(dist)
        H = H_los + H_nlos
        H /= np.sqrt(np.mean(np.abs(H) ** 2))  # unit average wireless channel gain

        noise_pil = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((N, K_ue)) + 1j * rng.standard_normal((N, K_ue)))

        def mmse_sum_rate(H_true, H_hat):
            # Digital/multi-feed reference combiner on estimated wireless channel H_hat at data SNR = 15 dB
            snr_d = 10.0 ** (snr_db / 10.0) / K_ue
            W_c = H_hat @ np.linalg.inv(H_hat.conj().T @ H_hat + (1.0 / snr_d) * np.eye(K_ue))
            rt = 0.0
            for u in range(K_ue):
                w = W_c[:, u]
                sig = snr_d * np.abs(w.conj() @ H_true[:, u]) ** 2
                inf = sum(snr_d * np.abs(w.conj() @ H_true[:, j]) ** 2 for j in range(K_ue) if j != u)
                nv = np.sum(np.abs(w) ** 2)
                rt += float(np.log2(1.0 + sig / max(inf + nv, 1e-15)))
            return rt

        rates["Oracle_CSI"].append(mmse_sum_rate(H, H))
        Y_S = A_mats["S_Exact"] @ H + noise_pil
        rates["S_XiaoMM"].append(mmse_sum_rate(H, L_xiao @ Y_S))
        for k, A in A_mats.items():
            Y_k = A @ H + noise_pil
            H_hat = pinv_mats[k] @ Y_k
            rates[k].append(mmse_sum_rate(H, H_hat))
    return {k: float(np.mean(v)) for k, v in rates.items()}


def main():
    t0 = time.time()
    N = 32
    L_wg = 30.0
    d_n = np.linspace(1.0, L_wg, N)
    eps_np = 0.15 * np.log(10.0) / 20.0  # 0.15 dB/m dielectric waveguide loss
    H_N = hadamard_sylvester(N)
    W_S = 0.5 * (H_N + np.ones((N, N)))
    rng = np.random.default_rng(20261123)

    print("=== 1. Uniform coupling sweep across weak / moderate / strong / opaque regimes (N=32, T=32) ===")
    for alpha_val in [0.30, 0.45, 0.55, 0.82]:
        alpha = np.full(N, alpha_val)
        beta = np.sqrt(1.0 - alpha ** 2)
        g0 = np.sqrt(0.5) * alpha * np.exp(-eps_np * d_n)

        m_ser = mse_trace(np.eye(N), g0, beta)
        m_S = mse_trace(W_S, g0, beta)
        W_cyc, m_cyc, best_K, W_eq, m_eq = best_wuttig_cyclic_and_const_col(g0, beta, rng)
        W_asym, m_asym, k_tgt = build_asym_schedule(g0, alpha, beta, rng, w_cyc_init=W_cyc)
        cw = W_asym.sum(axis=0).astype(int)

        rates = eval_uplink_rate(N, d_n, g0, beta,
                                 {"Serial": np.eye(N), "S_Exact": W_S, "WuttigCyc": W_cyc, "EqWeightSwap": W_eq, "AsymShadow": W_asym})
        print(f"alpha={alpha_val:.2f} (beta={beta[0]:.3f}): "
              f"MSE(dB) Ser={10*np.log10(m_ser):.2f}, S_Ex={10*np.log10(m_S):.2f}, "
              f"WuttigCyc(K={best_K})={10*np.log10(m_cyc):.2f}, EqColSwap={10*np.log10(m_eq):.2f}, Asym={10*np.log10(m_asym):.2f} "
              f"[Asym gain vs Ser={10*np.log10(m_ser/m_asym):+.2f}dB, vs Cyc={10*np.log10(m_cyc/m_asym):+.2f}dB, vs EqSwap={10*np.log10(m_eq/m_asym):+.2f}dB] | "
              f"cw[0,7,15,23,31]={cw[[0,7,15,23,31]].tolist()} | "
              f"Rate(bps/Hz): Ora={rates['Oracle_CSI']:.2f}, Asym={rates['AsymShadow']:.2f}, Cyc={rates['WuttigCyc']:.2f}, Ser={rates['Serial']:.2f}, S_Ex={rates['S_Exact']:.2f}, XiaoMM={rates['S_XiaoMM']:.2f}")

    print("\n=== 2. Equal-power progressive coupling law alpha_n = 1/sqrt(N - n + 2) (Xu et al. 2025, N=32) ===")
    alpha_eqp = 1.0 / np.sqrt(np.arange(N, 0, -1) + 1.0)  # increases from 0.174 at feed to 0.707 at far end!
    beta_eqp = np.sqrt(1.0 - alpha_eqp ** 2)
    g0_eqp = np.sqrt(0.5) * alpha_eqp * np.exp(-eps_np * d_n)
    m_ser_e = mse_trace(np.eye(N), g0_eqp, beta_eqp)
    m_S_e = mse_trace(W_S, g0_eqp, beta_eqp)
    W_cyc_e, m_cyc_e, bK_e, W_eq_e, m_eq_e = best_wuttig_cyclic_and_const_col(g0_eqp, beta_eqp, rng)
    W_asym_e, m_asym_e, _ = build_asym_schedule(g0_eqp, alpha_eqp, beta_eqp, rng, w_cyc_init=W_cyc_e)
    rates_e = eval_uplink_rate(N, d_n, g0_eqp, beta_eqp,
                               {"Serial": np.eye(N), "S_Exact": W_S, "WuttigCyc": W_cyc_e, "EqWeightSwap": W_eq_e, "AsymShadow": W_asym_e})
    cw_e = W_asym_e.sum(axis=0).astype(int)
    print(f"ProgEqualPower: MSE(dB) Ser={10*np.log10(m_ser_e):.2f}, S_Ex={10*np.log10(m_S_e):.2f}, "
          f"WuttigCyc(K={bK_e})={10*np.log10(m_cyc_e):.2f}, EqColSwap={10*np.log10(m_eq_e):.2f}, Asym={10*np.log10(m_asym_e):.2f} "
          f"[Asym gain vs Ser={10*np.log10(m_ser_e/m_asym_e):+.2f}dB, vs Cyc={10*np.log10(m_cyc_e/m_asym_e):+.2f}dB, vs EqSwap={10*np.log10(m_eq_e/m_asym_e):+.2f}dB] | "
          f"cw[0,7,15,23,31]={cw_e[[0,7,15,23,31]].tolist()} | "
          f"Rate(bps/Hz): Ora={rates_e['Oracle_CSI']:.2f}, Asym={rates_e['AsymShadow']:.2f}, Cyc={rates_e['WuttigCyc']:.2f}, Ser={rates_e['Serial']:.2f}, S_Ex={rates_e['S_Exact']:.2f}, XiaoMM={rates_e['S_XiaoMM']:.2f}")
    print(f"Total probe time: {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
