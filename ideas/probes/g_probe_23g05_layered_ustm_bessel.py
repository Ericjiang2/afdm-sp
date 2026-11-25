#!/usr/bin/env python3
"""L1 <=30s probe for I-20261123-g05:
分层稀疏空时调制在带噪信道下的逐列去相位打分与小列表检测

Implements Pendás-Recondo & Santamaría (arXiv:2611.22763v1, Nov. 17, 2026):
  - System: M=4 Tx, N=4 Rx, T=2M=8 data slots + T_p=4 orthogonal pilot slots (T_c=12),
    equal power per slot rho (Eq. 3 & Sec. VI-D).
  - Layer 1 (L_G=64): Sparse semi-unitary U_g in C^{8x4} with 1 nonzero entry per row and
    upper M x M submatrix diagonal cos(theta_{g,m}), lower M x M permuted sin(theta_{g,m}) e^{j psi_{g,m}}
    (matching [22] Pendás-Recondo TWC Aug. 2026 & Sec. V-A / V-D).
  - Layer 2 (L_S in {16, 64, 256}): Exact quadratic permutation polynomial diagonal unitary codebook
    R_s = diag(e^{j phi_{s,1}}, ..., e^{j phi_{s,M}}) via Eq. (16)-(19) of arXiv:2611.22763v1.

Compares at identical pilot overhead and total energy:
  1. Sant_K1: Sequential noncoherent Stage-1 ||U_g^H Y||_F^2 + coherent Stage-2 (2611.22763 Eq. 5+7, K=1)
  2. Sant_K3: Attiah-2017 noncoherent shortlist (K=3) + coherent Stage-2
  3. SupPhase_K1 / SupPhase_K3: Continuous per-column phase GLRT (sup_{phi_m}, linear |<z_{gm}, mu_m>| envelope)
  4. Bessel_K1 / Bessel_K3: Exact U(1)^M independent column-phase marginalized log-Bessel-I0 Stage-1 + K-list
  5. Joint_MAP: Exhaustive L_G * L_S partially-coherent MAP ceiling (O(L_G L_S))
"""
import time
import numpy as np
from scipy.special import i0e


def build_layer1_sparse_ustm(M=4, L_G=64):
    """Structured sparse Grassmannian codebook (T=2M, 1 nonzero per row, upper submatrix real positive diagonal)
    following Pendás-Recondo TWC Aug. 2026 [22]: M=4 cyclic shifts x 16 geodesic angle/phase tuples = 4*M^2 = 64."""
    T = 2 * M
    shifts = [[(m + sh) % M for m in range(M)] for sh in range(M)]
    U_list = []
    for sh in shifts:
        for c1 in range(4):
            for c2 in range(4):
                U = np.zeros((T, M), dtype=np.complex128)
                th = np.pi / 4.0 if (c1 % 2 == 0) else 0.30 * np.pi
                for m in range(M):
                    ps = (2.0 * np.pi / 4.0) * ((c1 * (m + 1) + c2 * (m // 2 + 1)) % 4)
                    U[m, m] = np.cos(th)
                    U[M + sh[m], m] = np.sin(th) * np.exp(1j * ps)
                U_list.append(U)
    U_arr = np.stack(U_list[:L_G], axis=0)  # (L_G, T, M)
    max_ov = 0.0
    for i in range(L_G):
        for j in range(i + 1, L_G):
            sv = np.linalg.svd(U_arr[i].conj().T @ U_arr[j], compute_uv=False)
            max_ov = max(max_ov, float(np.mean(sv ** 2)))
    assert max_ov < 0.96, f"Subspace collision: max_ov={max_ov}"
    return U_arr, max_ov


def build_layer2_qpp_diagonal(M=4, L_S=64):
    """Exact Eq. (16)-(19) of Pendás-Recondo & Santamaría arXiv:2611.22763v1."""
    s_vec = np.arange(1, L_S + 1, dtype=np.int64)
    P_half = L_S // 2
    # Precompute candidate permutations and pairwise wrapped angle diffs on s != k
    phi_mat = np.zeros((L_S, M), dtype=np.float64)
    phi_mat[:, 0] = (2.0 * np.pi / L_S) * (s_vec % L_S)
    # Pairwise indices s < k
    ii, jj = np.triu_indices(L_S, k=1)
    cum_prod = np.abs(np.angle(np.exp(1j * (phi_mat[jj, 0] - phi_mat[ii, 0]))))

    chosen_ab = [(0, 0)]
    # For speed when L_S=256 in <=30s L1 probe, subsample candidate (a,b) grid if P_half > 16
    a_cands = np.arange(P_half) if P_half <= 16 else np.linspace(0, P_half - 1, 16, dtype=int)
    b_cands = np.arange(P_half) if P_half <= 16 else np.linspace(0, P_half - 1, 16, dtype=int)

    for m in range(1, M):
        best_val = -1.0
        best_phi = None
        best_pair = (0, 0)
        for a in a_cands:
            for b in b_cands:
                p_s = ((2 * a + 1) * s_vec + 2 * b * (s_vec ** 2)) % L_S
                phi_c = (2.0 * np.pi / L_S) * p_s
                alp_c = np.abs(np.angle(np.exp(1j * (phi_c[jj] - phi_c[ii]))))
                score = float(np.min(cum_prod * alp_c))
                if score > best_val:
                    best_val = score
                    best_phi = phi_c
                    best_pair = (int(a), int(b))
        phi_mat[:, m] = best_phi
        cum_prod = cum_prod * np.abs(np.angle(np.exp(1j * (best_phi[jj] - best_phi[ii]))))
        chosen_ab.append(best_pair)
    R_diag = np.exp(1j * phi_mat)  # (L_S, M)
    return R_diag, chosen_ab


def evaluate_setting(U_arr, R_diag, snr_db_list, n_mc=1200, corr_gamma=0.0, seed=20261123):
    rng = np.random.default_rng(seed)
    L_G, T, M = U_arr.shape
    L_S = R_diag.shape[0]
    N = M
    T_p = M

    # Kronecker spatial correlation matrices R_t^{1/2}, R_r^{1/2} (Eq. 33 Loyka exponential model)
    idx = np.arange(M)
    if corr_gamma > 0:
        C_mat = corr_gamma ** np.abs(idx[:, None] - idx[None, :])
        L_chol = np.linalg.cholesky(C_mat)
    else:
        L_chol = np.eye(M)

    U_H = np.transpose(U_arr.conj(), (0, 2, 1))  # (L_G, M, T)
    results = {}

    for snr_db in snr_db_list:
        rho = 10.0 ** (snr_db / 10.0)
        # Eq. (3): Y = X H + sqrt(M / (T * rho)) W -> per-entry noise variance on Y is sigma2_d = M / (T * rho)
        sigma2_d = M / (T * rho)
        # Orthogonal unitary pilot P_p in C^{T_p x M} with ||P_p||_F^2 = M * T_p / T?
        # Wait: equal power per symbol slot across pilot & data!
        # Data block has ||X||_F^2 = M over T slots => average total Tx power per time slot is M/T.
        # Over T_p = M orthogonal pilot slots at identical per-slot total power M/T, each antenna gets pilot energy
        # E_p = (M / T) * T_p / M = T_p / T, with same noise variance per slot sigma2_w = M / (T * rho)?
        # Wait: in Eq. (3), E[||X H||_F^2] = N * ||X||_F^2 = N * M, E[||(M/(T*rho))^{1/2} W||_F^2] = T * N * M / (T * rho) = N * M / rho,
        # so SNR per receive antenna per slot is rho!
        # With orthogonal pilot X_p = sqrt(M / T_p) I_M? Over T_p = M slots, ||X_p||_F^2 = M * (T_p / T) so per-slot energy = M/T:
        # Y_p = sqrt(T_p / T) I_M H + sqrt(M / (T * rho)) W_p => H_ls = sqrt(T / T_p) Y_p = H + sqrt(M / (T_p * rho)) W_p!
        sigma2_p = M / (T_p * rho)
        # Isotropic Rayleigh MMSE posterior given H_ls: H | H_ls ~ CN(mu_H, tau2 * I)
        alpha_mmse = 1.0 / (1.0 + sigma2_p)
        tau2 = sigma2_p / (1.0 + sigma2_p)
        v_eff = sigma2_d + tau2  # exact marginal variance along spanned column!

        err = {k: 0 for k in ["Sant_K1", "Sant_K3", "SupPhase_K1", "SupPhase_K3", "Bessel_K1", "Bessel_K3", "Joint_MAP"]}
        err_g1 = {k: 0 for k in ["Sant_K1", "SupPhase_K1", "Bessel_K1", "Joint_MAP"]}

        for _ in range(n_mc):
            g_true = int(rng.integers(0, L_G))
            s_true = int(rng.integers(0, L_S))
            H_iid = (rng.standard_normal((M, N)) + 1j * rng.standard_normal((M, N))) / np.sqrt(2.0)
            H = L_chol @ H_iid @ L_chol.T
            W_d = (rng.standard_normal((T, N)) + 1j * rng.standard_normal((T, N))) / np.sqrt(2.0)
            W_p = (rng.standard_normal((M, N)) + 1j * rng.standard_normal((M, N))) / np.sqrt(2.0)

            X_tx = U_arr[g_true] * R_diag[s_true][None, :]
            Y = X_tx @ H + np.sqrt(sigma2_d) * W_d
            H_ls = H + np.sqrt(sigma2_p) * W_p
            mu_H = alpha_mmse * H_ls  # (M, N)

            # Z_all[g] = U_g^H Y of shape (L_G, M, N)
            Z_all = np.einsum("gmt,tn->gmn", U_H, Y)
            energy_g = np.sum(np.abs(Z_all) ** 2, axis=(1, 2))  # (L_G,)
            # Per-column spatial matched-filter inner products c_{g,m} = <mu_H[m], Z_all[g,m]> = sum_n mu_H[m,n]^* Z_all[g,m,n]
            corr_gm = np.sum(mu_H.conj()[None, :, :] * Z_all, axis=2)  # (L_G, M)
            abs_corr = np.abs(corr_gm)

            # 1) Santamaria noncoherent Stage-1 score: energy_g
            idx_sant = np.argsort(-energy_g)
            # 2) Continuous phase GLRT (sup_{phi_m}): (1/sigma2_d - 1/v_eff)*energy_g + (2/v_eff)*sum_m |c_{g,m}|
            w_ener = (1.0 / sigma2_d) - (1.0 / v_eff)
            arg_bessel = (2.0 / v_eff) * abs_corr
            score_sup = w_ener * energy_g + np.sum(arg_bessel, axis=1)
            idx_sup = np.argsort(-score_sup)
            # 3) Exact U(1)^M torus log-Bessel-I0 marginal score: w_ener*energy_g + sum_m ln I_0(arg_bessel)
            # Using log(i0e(x)) + x for overflow-free exact evaluation
            ln_i0 = np.log(i0e(arg_bessel)) + arg_bessel
            score_bes = w_ener * energy_g + np.sum(ln_i0, axis=1)
            idx_bes = np.argsort(-score_bes)

            def decode_k_list(top_g_list):
                best_metric = -1e30
                best_pair = (-1, -1)
                for g_cand in top_g_list:
                    # Exact partially coherent conditional log-likelihood for (g_cand, s):
                    # Y | g, s, H_ls: Z_g = R_s mu_H + E, E_mn ~ CN(0, v_eff), orthogonal complement has var sigma2_d
                    # => log p(Y | g, s, H_ls) = const + w_ener * ||Z_g||_F^2 + (2 / v_eff) Re sum_m R_s[m]^* corr_gm[g, m]
                    # Notice ||R_s mu_H||_F^2 = ||mu_H||_F^2 is CONSTANT across ALL (g, s) because R_s is diagonal unitary!
                    re_s = np.real(corr_gm[g_cand][None, :] * R_diag.conj()) @ np.ones(M)  # (L_S,)
                    s_best = int(np.argmax(re_s))
                    val = w_ener * energy_g[g_cand] + (2.0 / v_eff) * float(re_s[s_best])
                    if val > best_metric:
                        best_metric = val
                        best_pair = (int(g_cand), s_best)
                return best_pair

            p_sant1 = decode_k_list(idx_sant[:1])
            p_sant3 = decode_k_list(idx_sant[:3])
            p_sup1 = decode_k_list(idx_sup[:1])
            p_sup3 = decode_k_list(idx_sup[:3])
            p_bes1 = decode_k_list(idx_bes[:1])
            p_bes3 = decode_k_list(idx_bes[:3])

            # Joint MAP over all L_G * L_S
            all_re = np.real(corr_gm[:, None, :] * R_diag.conj()[None, :, :]).sum(axis=2)  # (L_G, L_S)
            joint_scores = w_ener * energy_g[:, None] + (2.0 / v_eff) * all_re
            g_j, s_j = np.unravel_index(int(np.argmax(joint_scores)), joint_scores.shape)

            for name, pr in [
                ("Sant_K1", p_sant1), ("Sant_K3", p_sant3),
                ("SupPhase_K1", p_sup1), ("SupPhase_K3", p_sup3),
                ("Bessel_K1", p_bes1), ("Bessel_K3", p_bes3),
                ("Joint_MAP", (int(g_j), int(s_j))),
            ]:
                if pr != (g_true, s_true):
                    err[name] += 1
            for name, g_hat in [
                ("Sant_K1", p_sant1[0]), ("SupPhase_K1", p_sup1[0]),
                ("Bessel_K1", p_bes1[0]), ("Joint_MAP", int(g_j)),
            ]:
                if g_hat != g_true:
                    err_g1[name] += 1

        results[snr_db] = (
            {k: v / n_mc for k, v in err.items()},
            {k: v / n_mc for k, v in err_g1.items()},
        )
    return results


def main():
    t0 = time.time()
    U_arr, max_ov = build_layer1_sparse_ustm(M=4, L_G=64)
    R64, ab64 = build_layer2_qpp_diagonal(M=4, L_S=64)
    R256, ab256 = build_layer2_qpp_diagonal(M=4, L_S=256)
    print(f"Codebooks built: L_G=64 (max subspace overlap={max_ov:.4f}), QPP64={ab64}, QPP256={ab256}")

    # Noiseless sanity gate (SNR = 60 dB => 0 errors across 50 blocks)
    res_gate = evaluate_setting(U_arr, R64, [60.0], n_mc=50, corr_gamma=0.0, seed=999)
    assert res_gate[60.0][0]["Bessel_K1"] == 0.0 and res_gate[60.0][0]["Joint_MAP"] == 0.0, f"Gate failed: {res_gate}"
    print("Noiseless gate PASS (BLER=0.0 at 60 dB)")

    for label, R_cur, snrs, corr in [
        ("Setting A: L_G=64, L_S=64 (net 1.0 bps/Hz, i.i.d. Rayleigh, 4096 vs 128/256 evals)", R64, [-2.0, 1.0, 4.0, 7.0], 0.0),
        ("Setting B: L_G=64, L_S=256 (net 1.17 bps/Hz, i.i.d. Rayleigh, 16384 vs 320/832 evals)", R256, [1.0, 4.0, 7.0], 0.0),
        ("Setting C: L_G=64, L_S=64 (correlated Kronecker gamma=0.6)", R64, [1.0, 4.0, 7.0], 0.6),
    ]:
        print(f"\n=== {label} ===")
        res = evaluate_setting(U_arr, R_cur, snrs, n_mc=1000, corr_gamma=corr, seed=20261123)
        for snr in snrs:
            bler, ser1 = res[snr]
            print(
                f"  SNR={snr:4.1f}dB | BLER: Sant_K1={bler['Sant_K1']:.4f}, Sant_K3={bler['Sant_K3']:.4f}, "
                f"Sup_K1={bler['SupPhase_K1']:.4f}, Bes_K1={bler['Bessel_K1']:.4f}, "
                f"Sup_K3={bler['SupPhase_K3']:.4f}, Bes_K3={bler['Bessel_K3']:.4f}, Joint={bler['Joint_MAP']:.4f} "
                f"| SER1(K=1): Sant={ser1['Sant_K1']:.4f}, Bes={ser1['Bessel_K1']:.4f}, Joint={ser1['Joint_MAP']:.4f}"
            )
    print(f"\nTotal L1 probe runtime: {time.time() - t0:.2f} s")


if __name__ == "__main__":
    main()
