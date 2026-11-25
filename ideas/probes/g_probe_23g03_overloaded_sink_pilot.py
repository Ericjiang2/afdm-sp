#!/usr/bin/env python3
"""Read-only <=30s probe for I-20261123-g03:
100% blind coded LDPC-2048 evaluation (ZERO true channel gain g_true, ZERO true X)
of Welch-bound ETF vs Random vs Orthogonal-CMA vs Sink-Coupled Tiered Pilots
in equal-power overloaded MU-MIMO uplink (Tp=8 orthogonal pilot dimensions, K > 2*Tp active users).
"""
import sys, time
import numpy as np

sys.path.insert(0, '/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation')
from afdm_sp_joint_unrolled.e1_ldpc import build_code, encode, decode_llr, extract_info, qpsk_map, demap_llr

t0 = time.time()
code = build_code(2048, d_v=3, d_c=6, seed=20260726)
const4 = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2.0)

# Verify exact QPSK mapping of e1_ldpc:
tb = np.zeros(code['k'], dtype=np.uint8); tb[::3] = 1
cw = encode(code, tb)
tx4 = qpsk_map(cw)
c_hat0, ok0 = decode_llr(code, demap_llr(tx4, 0.05, 1.0), maxiter=25)
assert ok0 and np.array_equal(extract_info(code, c_hat0), tb), "Noiseless QPSK LDPC gate failed!"

def make_etf(Tp, K, seed=7):
    r = np.random.default_rng(seed)
    A = (r.standard_normal((Tp, K)) + 1j * r.standard_normal((Tp, K))) / np.sqrt(2)
    for _ in range(300):
        U, _, Vh = np.linalg.svd(A, full_matrices=False)
        A = np.sqrt(K / Tp) * (U @ Vh)
        A = A / np.linalg.norm(A, axis=0, keepdims=True)
    return A

def make_sink_peel(Tp, K, rho_p, N, sigma2, s_sink=1):
    d = Tp - s_sink
    m = (K - s_sink + d - 1) // d
    eta = 1.0 / rho_p + 0.5 * (K + sigma2) / N
    inv_eta = 1.0 / max(eta, 1e-6)
    lo, hi = 1e-4, inv_eta
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if mid * ((1.0 + mid) ** (m - 1)) < inv_eta: lo = mid
        else: hi = mid
    gamma = 0.5 * (lo + hi)
    alphas = [min(1.0, (gamma * eta) * ((1.0 + gamma) ** (m - 1 - l))) for l in range(m)]
    alphas[0] = 1.0
    Phi = np.zeros((Tp, K), dtype=complex)
    col = 0
    for l in range(m):
        cnt = min(d, (K - s_sink) - col)
        a = np.clip(alphas[l], 1e-4, 1.0)
        for i in range(cnt):
            Phi[i, col] = np.sqrt(a)
            Phi[d + (i % s_sink), col] = np.sqrt(1.0 - a)
            col += 1
    for j in range(s_sink):
        Phi[d + j, K - s_sink + j] = 1.0
    return Phi, alphas

def soft_qpsk_batch(Z, v_vec):
    v = np.maximum(v_vec, 0.02)[:, None]
    # e1_ldpc qpsk_map uses (1-2*b0 + j*(1-2*b1))/sqrt(2): real and imag independent BPSK at +-1/sqrt(2)!
    scale = 2.0 * np.sqrt(2.0) / v
    mr = np.tanh(np.clip(np.real(Z) * scale / 2.0, -15, 15)) / np.sqrt(2.0)
    mi = np.tanh(np.clip(np.imag(Z) * scale / 2.0, -15, 15)) / np.sqrt(2.0)
    mu = mr + 1j * mi
    var = 1.0 - (mr ** 2 + mi ** 2)
    return mu, var

def run_blind_qpsk_ldpc(M=64, Tp=8, K=22, N=1024, snr_list=(0.0, 3.0, 6.0), n_trials=4):
    Phi_etf = make_etf(Tp, K, seed=7)
    s3 = 10 ** (-3.0 / 10.0)
    Phi_s3, a3 = make_sink_peel(Tp, K, Tp / s3, N, s3, s_sink=1)
    def ss_nmse(Phi):
        P = np.sqrt(Tp) * Phi
        return float(np.real(np.trace(s3 * np.linalg.inv(P.conj().T @ P + s3 * np.eye(K)))) / K)
    tsc_etf = float(np.real(np.sum(np.abs(Phi_etf.conj().T @ Phi_etf) ** 2)))
    tsc_sink = float(np.real(np.sum(np.abs(Phi_s3.conj().T @ Phi_s3) ** 2)))
    print(f"=== 100%-BLIND Rate-1/2 (2048,1024) LDPC QPSK | M={M}, Tp={Tp}, K={K} ({K/Tp:.2f}x), N={N} ===")
    print(f"  @3dB Single-shot Pilot NMSE: ETF={ss_nmse(Phi_etf):.4f} (TSC={tsc_etf:.1f}) vs Sink={ss_nmse(Phi_s3):.4f} (TSC={tsc_sink:.1f}), alphas={[round(x,3) for x in a3]}")

    modes = [
        ("Oracle (Ortho Tp=K)", "oracle", True),
        ("WBE/ETF + SubspaceMVDR + SoftEM", "etf", True),
        ("Random  + SubspaceMVDR + SoftEM", "rand", True),
        ("ETF + Whitened Ortho-CMA + LDPC", "cma", True),
        ("Sink(s=1) + Hard-SIC only (no EM)", "sink1", False),
        ("Sink(s=1) + SubspaceMVDR + SoftEM", "sink1", True),
    ]
    for label, mode, use_soft in modes:
        res_str = []
        for snr_db in snr_list:
            sigma2 = 10 ** (-snr_db / 10.0)
            rho_p = Tp / sigma2
            rng = np.random.default_rng(20261123)
            u_ok = 0; f_ok = 0
            for _ in range(n_trials):
                H = (rng.standard_normal((M, K)) + 1j * rng.standard_normal((M, K))) / np.sqrt(2.0)
                infos = rng.integers(0, 2, size=(K, code['k']), dtype=np.uint8)
                cws = np.array([encode(code, infos[k]) for k in range(K)])
                X = np.array([qpsk_map(cws[k]) for k in range(K)])
                if mode == "oracle":
                    Phi = np.eye(K, dtype=complex); Tp_eff = K
                elif mode in ("etf", "cma"):
                    Phi = Phi_etf; Tp_eff = Tp
                elif mode == "rand":
                    A = (rng.standard_normal((Tp, K)) + 1j * rng.standard_normal((Tp, K))) / np.sqrt(2)
                    Phi = A / np.linalg.norm(A, axis=0, keepdims=True); Tp_eff = Tp
                elif mode == "sink1":
                    Phi, _ = make_sink_peel(Tp, K, rho_p, N, sigma2, s_sink=1); Tp_eff = Tp

                P_mat = np.sqrt(Tp) * Phi  # Equal per-user pilot energy Tp across ALL arms (incl. Oracle!)
                Wp = np.sqrt(sigma2/2)*(rng.standard_normal((M, Tp_eff)) + 1j*rng.standard_normal((M, Tp_eff)))
                Wd = np.sqrt(sigma2/2)*(rng.standard_normal((M, N)) + 1j*rng.standard_normal((M, N)))
                Yp_res = H @ P_mat.T + Wp
                Yd_res = H @ X + Wd

                if mode == "cma":
                    Ry = (Yd_res @ Yd_res.conj().T) / N
                    evals, evecs = np.linalg.eigh(Ry)
                    Us = evecs[:, -K:]
                    lams = np.maximum(evals[-K:], sigma2)
                    Yw = (1.0 / np.sqrt(lams))[:, None] * (Us.conj().T @ Yd_res)
                    W_cma = (Us.conj().T @ (Yp_res @ P_mat.conj() / Tp)).conj().T / np.sqrt(lams)[None, :]
                    Uu, _, Vvh = np.linalg.svd(W_cma, full_matrices=False)
                    W_cma = Uu @ Vvh
                    for _it in range(25):
                        Z = W_cma @ Yw
                        Z_sl, _ = soft_qpsk_batch(Z, np.full(K, 0.25))
                        W_cma = Z_sl @ Yw.conj().T / N
                        Uu, _, Vvh = np.linalg.svd(W_cma, full_matrices=False)
                        W_cma = Uu @ Vvh
                    Z_cand = W_cma @ Yw
                    ok_k = np.zeros(K, dtype=bool)
                    for r_i in range(K):
                        for rot in (1, 1j, -1, -1j):
                            zr = Z_cand[r_i] * rot
                            nv = max(float(np.mean(np.min(np.abs(zr[:,None]-const4[None,:])**2, axis=1)))*2.0, 0.08)
                            c_hat, ok_syn = decode_llr(code, demap_llr(zr, nv, 1.0), maxiter=25)
                            if ok_syn:
                                for uk in range(K):
                                    if not ok_k[uk] and np.array_equal(extract_info(code, c_hat), infos[uk]):
                                        ok_k[uk] = True; break
                                break
                    u_ok += int(np.sum(ok_k))
                    if np.all(ok_k): f_ok += 1
                    continue

                active = list(range(K))
                decoded_ok = np.zeros(K, dtype=bool)
                H_em = None; em_steps = 0; v_sum_last = 0.0
                for _it in range(10):
                    if not active: break
                    P_act = P_mat[:, active]; K_act = len(active)
                    G_p = P_act.conj().T @ P_act + sigma2 * np.eye(K_act)
                    if H_em is None:
                        H_hat = (np.linalg.solve(G_p, P_act.conj().T @ Yp_res.T)).T
                        C_err_tr = float(np.real(np.trace(sigma2 * np.linalg.inv(G_p))))
                    else:
                        H_hat = H_em
                        C_err_tr = float((sigma2 + v_sum_last) * K_act / (N + Tp_eff))

                    if K_act <= Tp_eff or em_steps >= 2:
                        R_par = H_hat @ H_hat.conj().T + (sigma2 + C_err_tr) * np.eye(M)
                        W = np.linalg.solve(R_par, H_hat); H_use = H_hat
                    else:
                        Ry = (Yd_res @ Yd_res.conj().T) / N
                        evals, evecs = np.linalg.eigh(Ry)
                        Us = evecs[:, -K_act:]
                        lams = np.maximum(evals[-K_act:], sigma2)
                        UtH = Us.conj().T @ H_hat
                        H_use = Us @ UtH
                        W = Us @ (UtH / lams[:, None])

                    Z_raw = W.conj().T @ Yd_res
                    g_est = np.sum(W.conj() * H_use, axis=0)  # 100% BLIND gain normalization!
                    Z_est = Z_raw / (g_est[:, None] + 1e-12)
                    newly = []; X_re_list = []
                    for loc_i, u in enumerate(active):
                        z_u = Z_est[loc_i]
                        d_near = np.min(np.abs(z_u[:, None] - const4[None, :]) ** 2, axis=1)
                        nv_est = max(float(np.mean(d_near)) * 2.2, float(np.abs(np.mean(np.abs(z_u)**2) - 1.0)), 0.08)
                        c_hat, ok_syn = decode_llr(code, demap_llr(z_u, nv_est, 1.0), maxiter=25)
                        if ok_syn:
                            newly.append(u)
                            X_re_list.append(qpsk_map(c_hat))
                            if np.array_equal(extract_info(code, c_hat), infos[u]):
                                decoded_ok[u] = True
                    if newly:
                        X_dec = np.array(X_re_list)
                        P_dec = P_mat[:, newly].T
                        S_dec = np.hstack([P_dec, X_dec])
                        Y_comb = np.hstack([Yp_res, Yd_res])
                        reg = (sigma2 + (K_act - len(newly))) * np.eye(len(newly))
                        H_re = Y_comb @ S_dec.conj().T @ np.linalg.inv(S_dec @ S_dec.conj().T + reg)
                        Yp_res = Yp_res - H_re @ P_dec
                        Yd_res = Yd_res - H_re @ X_dec
                        active = [u for u in active if u not in newly]
                        H_em = None; em_steps = 0
                    elif use_soft and em_steps < 4:
                        v_est = np.maximum(np.mean(np.abs(Z_est) ** 2, axis=1) - 1.0, 0.08)
                        X_soft, var_soft = soft_qpsk_batch(Z_est, v_est)
                        v_sum_last = float(np.sum(np.mean(var_soft, axis=1)))
                        S_all = np.hstack([P_act.T, X_soft])
                        Y_all = np.hstack([Yp_res, Yd_res])
                        G_em = S_all @ S_all.conj().T + (sigma2 + v_sum_last) * np.eye(K_act)
                        H_em = Y_all @ S_all.conj().T @ np.linalg.inv(G_em)
                        em_steps += 1
                    else:
                        break
                u_ok += int(np.sum(decoded_ok))
                if np.all(decoded_ok): f_ok += 1
            res_str.append(f"{snr_db:3.0f}dB:{100*u_ok/(n_trials*K):5.1f}%({f_ok}/{n_trials})")
        print(f"  {label:34s}: " + " | ".join(res_str))

if __name__ == "__main__":
    run_blind_qpsk_ldpc(M=64, Tp=8, K=26, N=1024, snr_list=(0.0, 3.0, 6.0), n_trials=3)
    print(f"Probe finished in {time.time() - t0:.2f}s")
