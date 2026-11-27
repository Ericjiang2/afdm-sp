import os
import sys
import time
import json
import itertools
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h_r13_stageA_common import (
    build_daft_matrices, build_wideband_user_channel, ula_steering,
    qam16_alphabet, nearest_symbol_ser,
)


def make_g2_scene(seed: int, N: int = 64, c1_zero: bool = False):
    rng = np.random.default_rng(seed)
    Nt, Nrf, K, Pk = 32, 4, 3, 3
    ell_max = 6
    nu_max = 0.0 if c1_zero else 0.85
    # 2*N*c1 = 3 (coprime to N=64: 3 * 43 = 129 == 1 mod 64)
    c1 = 0.0 if c1_zero else 3.0 / (2.0 * N)
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_max = float(N)
    sigma2 = 10.0 ** (-20.0 / 10.0)
    theta_tar = 40.0
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-18.0, 18.0)
            nu = 0.0 if c1_zero else rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    H_users = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    a_tar = ula_steering(Nt, theta_tar, unit_norm=True)  # ||a_tar||=1, so max gain is P_max (0 dB)
    return {
        "rng": rng, "Nt": Nt, "Nrf": Nrf, "K": K, "Pk": Pk, "N": N,
        "c1": c1, "c2": c2, "P_max": P_max, "sigma2": sigma2,
        "theta_tar": theta_tar, "a_tar": a_tar, "users_paths": users_paths, "H_users": H_users,
    }


def eval_g2_arm(sc, F_rf, W_bb_c, W_bb_s, gamma_tar_ratio=0.50):
    """
    Enforces exact total power P_max AND checks/enforces common target illumination floor
    a_tar^H R_x a_tar >= gamma_tar_ratio * P_max (-3.01 dB)!
    """
    N, Nt, Nrf, K = sc["N"], sc["Nt"], sc["Nrf"], sc["K"]
    P_max, sigma2 = sc["P_max"], sc["sigma2"]
    a_tar = sc["a_tar"]
    H_users = sc["H_users"]
    F_blk = np.kron(np.eye(N), F_rf)

    Wc = np.array([F_blk @ W_bb_c[k] for k in range(K)])  # (K, N*Nt, N)
    Ws = F_blk @ W_bb_s                                   # (N*Nt, N)

    # Check power and target illumination; if below gamma_tar_ratio * P_max, blend toward max-tar RF beam!
    def calc_p_and_tar(Wc_in, Ws_in):
        p_c = sum(float(np.sum(np.abs(Wc_in[k]) ** 2)) for k in range(K))
        p_s = float(np.sum(np.abs(Ws_in) ** 2))
        Wc_r = Wc_in.reshape(K, N, Nt, N)
        Ws_r = Ws_in.reshape(N, Nt, N)
        proj_c = np.einsum("i,kmin->kmn", np.conj(a_tar), Wc_r)
        proj_s = np.einsum("i,min->mn", np.conj(a_tar), Ws_r)
        e_t = float(np.sum(np.abs(proj_c) ** 2) + np.sum(np.abs(proj_s) ** 2))
        return p_c + p_s, e_t

    p_tot, e_tar = calc_p_and_tar(Wc, Ws)
    scale0 = np.sqrt(P_max / max(p_tot, 1e-15))
    Wc *= scale0
    Ws *= scale0
    _, e_tar = calc_p_and_tar(Wc, Ws)

    # Common illumination floor enforcement: if e_tar < gamma_tar_ratio * P_max, re-weight comm vs best RF radar beam!
    g_rf = F_rf.conj().T @ a_tar  # (Nrf,)
    v_rf_tar = F_rf @ g_rf
    v_rf_tar = v_rf_tar / max(np.linalg.norm(v_rf_tar), 1e-15)  # unit norm in C^Nt, gain toward a_tar is |a_tar^H v_rf_tar|^2
    max_rf_gain = float(abs(np.vdot(a_tar, v_rf_tar)) ** 2)
    req_e = gamma_tar_ratio * P_max

    if e_tar < req_e - 1e-6 and max_rf_gain * P_max > req_e:
        # Replace/boost sensing stream along v_rf_tar and scale down Wc to hit exact req_e at total power P_max
        Ws_pure = np.zeros((N * Nt, N), dtype=np.complex128)
        for m in range(N):
            Ws_pure[m * Nt:(m + 1) * Nt, m] = v_rf_tar
        # Binary search rho in [0, 1]: Wc' = sqrt(1-rho)*Wc_norm, Ws' = sqrt(rho)*Ws_pure
        p_c_only = sum(float(np.sum(np.abs(Wc[k]) ** 2)) for k in range(K))
        Wc_unit = Wc * np.sqrt(P_max / max(p_c_only, 1e-15))
        _, e_c_unit = calc_p_and_tar(Wc_unit, np.zeros_like(Ws))
        e_s_unit = max_rf_gain * P_max
        rho = np.clip((req_e - e_c_unit) / max(e_s_unit - e_c_unit, 1e-12), 0.0, 1.0)
        Wc = np.sqrt(1.0 - rho) * Wc_unit
        Ws = np.sqrt(rho) * Ws_pure
        _, e_tar = calc_p_and_tar(Wc, Ws)

    I_N = np.eye(N, dtype=np.complex128)
    sr = 0.0
    alph = qam16_alphabet()
    rng_ev = np.random.default_rng(99991)
    d_syms = alph[rng_ev.integers(0, 16, size=(K, N))]
    s_rad = (rng_ev.standard_normal(N) + 1j * rng_ev.standard_normal(N)) / np.sqrt(2.0)
    s_vec = sum(Wc[k] @ d_syms[k] for k in range(K)) + Ws @ s_rad
    sers = []
    for k in range(K):
        Sig = sigma2 * I_N + (H_users[k] @ Ws) @ (H_users[k] @ Ws).conj().T
        for j in range(K):
            if j != k:
                hw = H_users[k] @ Wc[j]
                Sig = Sig + hw @ hw.conj().T
        hwd = H_users[k] @ Wc[k]
        _, ld = np.linalg.slogdet(I_N + np.linalg.solve(Sig, hwd @ hwd.conj().T))
        sr += float(np.real(ld) / np.log(2.0)) / float(N)
        zk = H_users[k] @ s_vec + np.sqrt(sigma2 / 2.0) * (rng_ev.standard_normal(N) + 1j * rng_ev.standard_normal(N))
        d_hat = hwd.conj().T @ np.linalg.solve(Sig + hwd @ hwd.conj().T, zk)
        sers.append(nearest_symbol_ser(d_hat, d_syms[k], alph))
    return sr, float(np.mean(sers)), 10.0 * np.log10(max(e_tar / P_max, 1e-15)), max_rf_gain


def optimize_analog_manifold(sc, mode: str, rng_scr=None):
    """
    Optimizes constant-modulus F_rf (Nt x Nrf, |F_rf|=1/sqrt(Nt)):
      - 'elbir': 1 SVD beam per user + 1 target beam (Elbir WCL'24)
      - 'liao_port': top Nrf eigenvectors of weighted comm + target spatial covariance (Liao TWC'25 hybrid port)
      - 'g2_s1_2': Riemannian ascent on multipath log-det + multi-chain coherent target gain >= tau_tar
      - 'g2_s2_1_true': G2-S1-2 + true AFDM affine collision penalty omega(c1) - omega(0)
      - 'g2_s2_1_scram': Same as g2_s2_1_true with randomly scrambled path collision weights (Sol #1 control!)
    """
    Nt, Nrf, K, N = sc["Nt"], sc["Nrf"], sc["K"], sc["N"]
    a_tar = sc["a_tar"]
    H_users = sc["H_users"]

    R_users = []
    for k in range(K):
        Hk_sp = H_users[k].reshape(N * N, Nt)
        R_users.append((Hk_sp.conj().T @ Hk_sp) / float(N))
    A_tar = np.outer(a_tar, np.conj(a_tar))  # ||a_tar||=1, so tr(F^H A_tar F) in [0, Nrf]

    if mode == "elbir":
        F_rf = np.zeros((Nt, Nrf), dtype=np.complex128)
        for k in range(K):
            _, U = np.linalg.eigh(R_users[k])
            F_rf[:, k] = np.exp(1j * np.angle(U[:, -1])) / np.sqrt(Nt)
        F_rf[:, K] = a_tar
        return F_rf

    if mode == "liao_port":
        R_tot = sum(R_users) + 2.5 * A_tar
        _, U = np.linalg.eigh(R_tot)
        return np.exp(1j * np.angle(U[:, -Nrf:])) / np.sqrt(Nt)

    # Start from Liao init and run 35 Riemannian gradient steps on unit-modulus manifold
    F = optimize_analog_manifold(sc, "liao_port")
    # Build cross-user affine collision spatial penalty matrix if requested
    R_coll = np.zeros((Nt, Nt), dtype=np.complex128)
    if mode in ("g2_s2_1_true", "g2_s2_1_scram"):
        pairs = []
        weights = []
        s_step = round(2.0 * N * sc["c1"])
        for k in range(K):
            for j in range(K):
                if j == k:
                    continue
                for g1, l1, nu1, ang1 in sc["users_paths"][k]:
                    for g2, l2, nu2, ang2 in sc["users_paths"][j]:
                        d_aff = ((s_step * (l1 - l2) + (nu1 - nu2) + N / 2.0) % N) - N / 2.0
                        d_c0 = (((nu1 - nu2) + N / 2.0) % N) - N / 2.0
                        w_c1 = 1.0 / (1.0 + d_aff ** 2)
                        w_0 = 1.0 / (1.0 + d_c0 ** 2)
                        dw = max(w_c1 - 0.3 * w_0, 0.0) * abs(g1) * abs(g2)
                        a1 = ula_steering(Nt, ang1, True)
                        a2 = ula_steering(Nt, ang2, True)
                        pairs.append((a1, a2))
                        weights.append(dw)
        if mode == "g2_s2_1_scram":
            rng_scr.shuffle(weights)
        for (a1, a2), w in zip(pairs, weights):
            R_coll += w * (np.outer(a1, np.conj(a1)) + np.outer(a2, np.conj(a2)))

    tau_tar = 1.85  # coherent multi-chain target gain (>= 1.85 out of 4.0, vs 1.0 in Elbir!)
    for it in range(35):
        grad = np.zeros_like(F)
        for k in range(K):
            Gk = np.eye(Nrf) + (F.conj().T @ R_users[k] @ F) / 0.05
            grad += (2.0 / 0.05) * (R_users[k] @ F @ np.linalg.inv(Gk))
        g_t = float(np.real(np.trace(F.conj().T @ A_tar @ F)))
        if g_t < tau_tar:
            grad += 12.0 * (tau_tar - g_t) * (A_tar @ F)
        else:
            grad += 1.5 * (A_tar @ F)
        if mode in ("g2_s2_1_true", "g2_s2_1_scram"):
            grad -= 2.5 * (R_coll @ F)
        F = np.exp(1j * np.angle(F + 0.04 * grad)) / np.sqrt(Nt)
    return F


def banded_hermitian_approx(Phi: np.ndarray, Nrf: int, N: int, half_bw: int) -> np.ndarray:
    """Keeps cyclic block-band |m - m'|_N <= half_bw of (N*Nrf x N*Nrf) matrix Phi."""
    P_b = np.zeros_like(Phi)
    for m in range(N):
        r0, r1 = m * Nrf, (m + 1) * Nrf
        for d in range(-half_bw, half_bw + 1):
            mp = (m + d) % N
            c0, c1 = mp * Nrf, (mp + 1) * Nrf
            P_b[r0:r1, c0:c1] = Phi[r0:r1, c0:c1]
    return 0.5 * (P_b + P_b.conj().T) + 1e-6 * np.eye(N * Nrf)


def solve_crossbin_baseband(sc, F_rf, solver: str = "dense", pcg_iters: int = 6):
    """
    Solves hybrid baseband cross-bin RZF + nullspace radar illumination for fixed F_rf:
      Phi * W_bb = H_stack^H, where Phi = H_stack^H H_stack + alpha (I_N kron F_rf^H F_rf).
    Compares:
      - 'dense': exact dense solve
      - 'per_bin_liu': Liu 2607 12-iter per-DAFT-bin block-diagonal WMMSE
      - 'per_bin_elbir': Elbir per-bin pseudo-inverse
      - 'pcg_dop_only': single-axis Doppler-band (B_nu=2) PCG
      - 'pcg_del_only': single-axis coprime affine-stride (B_del=6) PCG
      - 'pcg_zhu_jacobi': Zhu 2506 block-Jacobi (B=0) PCG
      - 'pcg_dual_axis': G2-S1-2 coprime dual-axis additive Schwarz (Doppler + P_{c1} delay band) PCG
    """
    N, Nrf, K, sigma2, P_max = sc["N"], sc["Nrf"], sc["K"], sc["sigma2"], sc["P_max"]
    F_blk = np.kron(np.eye(N), F_rf)
    H_eff = [sc["H_users"][k] @ F_blk for k in range(K)]
    H_stack = np.vstack(H_eff)  # (K*N, N*Nrf)
    G_rf = F_rf.conj().T @ F_rf

    if solver == "per_bin_elbir":
        W_bb_c = np.zeros((K, N * Nrf, N), dtype=np.complex128)
        W_bb_s = np.zeros((N * Nrf, N), dtype=np.complex128)
        g_t = F_rf.conj().T @ sc["a_tar"]
        b_s = np.linalg.solve(G_rf + 1e-6 * np.eye(Nrf), g_t)
        b_s /= max(np.linalg.norm(F_rf @ b_s), 1e-12)
        for m in range(N):
            sl = slice(m * Nrf, (m + 1) * Nrf)
            Hm = np.vstack([H_eff[k][m, sl] for k in range(K)])
            Bm = Hm.conj().T @ np.linalg.inv(Hm @ Hm.conj().T + sigma2 * np.eye(K))
            Bm /= max(np.linalg.norm(F_rf @ Bm, "fro"), 1e-12)
            for k in range(K):
                W_bb_c[k, sl, m] = np.sqrt(0.65) * Bm[:, k]
            W_bb_s[sl, m] = np.sqrt(0.35) * b_s
        return W_bb_c, W_bb_s, 0.0

    if solver == "per_bin_liu":
        W_bb_c, W_bb_s, _ = solve_crossbin_baseband(sc, F_rf, "per_bin_elbir")
        I_N = np.eye(N, dtype=np.complex128)
        for _ in range(12):
            Tw = np.zeros((N, Nrf, Nrf), dtype=np.complex128)
            Bk = np.zeros((K, N, Nrf), dtype=np.complex128)
            for k in range(K):
                Hk = H_eff[k]
                Ck = sigma2 * I_N + (Hk @ W_bb_s) @ (Hk @ W_bb_s).conj().T
                for j in range(K):
                    hw = Hk @ W_bb_c[j]
                    Ck += hw @ hw.conj().T
                Uk = np.linalg.solve(Ck, Hk @ W_bb_c[k])
                Ek = 0.5 * ((I_N - W_bb_c[k].conj().T @ Hk.conj().T @ Uk) + (I_N - W_bb_c[k].conj().T @ Hk.conj().T @ Uk).conj().T) + 1e-9 * I_N
                Mk = np.linalg.inv(Ek)
                V = Hk.conj().T @ Uk
                VM = V @ Mk
                for m in range(N):
                    sl = slice(m * Nrf, (m + 1) * Nrf)
                    Tw[m] += VM[sl, :] @ V[sl, :].conj().T
                    Bk[k, m] = VM[sl, m]
            W_new = np.zeros_like(W_bb_c)
            for m in range(N):
                Tm = Tw[m] + 0.05 * G_rf
                for k in range(K):
                    W_new[k, m * Nrf:(m + 1) * Nrf, m] = np.linalg.solve(Tm, Bk[k, m])
            p_c = sum(float(np.sum(np.abs(F_blk @ W_new[k]) ** 2)) for k in range(K))
            W_bb_c = W_new * np.sqrt(0.65 * P_max / max(p_c, 1e-15))
        return W_bb_c, W_bb_s, 0.0

    # Cross-bin normal equation: Phi X = RHS, where RHS = [H_stack^H, S_tar_bb]
    Phi = H_stack.conj().T @ H_stack + (K * sigma2) * np.kron(np.eye(N), G_rf)
    g_t = F_rf.conj().T @ sc["a_tar"]
    b_s = np.linalg.solve(G_rf + 1e-6 * np.eye(Nrf), g_t)
    b_s /= max(np.linalg.norm(F_rf @ b_s), 1e-12)
    S_tar_bb = np.kron(np.eye(N), b_s[:, None])  # (N*Nrf, N)

    if solver == "dense":
        G_c = np.linalg.solve(Phi, H_stack.conj().T)
        # Project S_tar_bb orthogonal to H_stack in G_rf metric:
        P_h = G_c @ np.linalg.solve(H_stack @ G_c + 1e-8 * np.eye(K * N), H_stack @ S_tar_bb)
        W_s = S_tar_bb - P_h
        W_c = np.array([G_c[:, k * N:(k + 1) * N] for k in range(K)])
        p_c = sum(float(np.sum(np.abs(F_blk @ W_c[k]) ** 2)) for k in range(K))
        p_s = float(np.sum(np.abs(F_blk @ W_s) ** 2))
        W_c *= np.sqrt(0.65 * P_max / max(p_c, 1e-15))
        W_s *= np.sqrt(0.35 * P_max / max(p_s, 1e-15))
        return W_c, W_s, 0.0

    # Build preconditioner M^-1 on (N*Nrf x N*Nrf):
    # Coprime stride permutation: s=3, inv_s = pow(3, -1, N)
    inv_s = pow(3, -1, N)
    perm_bins = np.array([(inv_s * m) % N for m in range(N)], dtype=np.int64)
    perm_idx = np.concatenate([np.arange(b * Nrf, (b + 1) * Nrf) for b in perm_bins])
    inv_perm_idx = np.argsort(perm_idx)

    if solver == "pcg_zhu_jacobi":
        M_dop = banded_hermitian_approx(Phi, Nrf, N, half_bw=0)
        L_dop = np.linalg.cholesky(M_dop)
        def apply_prec(R):
            return np.linalg.solve(L_dop.conj().T, np.linalg.solve(L_dop, R))
    elif solver == "pcg_dop_only":
        M_dop = banded_hermitian_approx(Phi, Nrf, N, half_bw=2)
        L_dop = np.linalg.cholesky(M_dop)
        def apply_prec(R):
            return np.linalg.solve(L_dop.conj().T, np.linalg.solve(L_dop, R))
    elif solver == "pcg_del_only":
        Phi_p = Phi[np.ix_(perm_idx, perm_idx)]
        M_del = banded_hermitian_approx(Phi_p, Nrf, N, half_bw=6)
        L_del = np.linalg.cholesky(M_del)
        def apply_prec(R):
            Rp = R[perm_idx]
            Zp = np.linalg.solve(L_del.conj().T, np.linalg.solve(L_del, Rp))
            return Zp[inv_perm_idx]
    elif solver == "pcg_dual_axis":
        M_dop = banded_hermitian_approx(Phi, Nrf, N, half_bw=2)
        L_dop = np.linalg.cholesky(M_dop)
        Phi_p = Phi[np.ix_(perm_idx, perm_idx)]
        M_del = banded_hermitian_approx(Phi_p, Nrf, N, half_bw=6)
        L_del = np.linalg.cholesky(M_del)
        def apply_prec(R):
            Z1 = np.linalg.solve(L_dop.conj().T, np.linalg.solve(L_dop, R))
            Rp = R[perm_idx]
            Z2 = np.linalg.solve(L_del.conj().T, np.linalg.solve(L_del, Rp))[inv_perm_idx]
            return 0.5 * (Z1 + Z2)
    else:
        raise ValueError(solver)

    # Block PCG for Phi @ G_c = H_stack^H
    RHS = H_stack.conj().T
    X = np.zeros_like(RHS)
    R = RHS.copy()
    Z = apply_prec(R)
    P_dir = Z.copy()
    rz_old = np.sum(np.conj(R) * Z, axis=0)
    for _ in range(pcg_iters):
        AP = Phi @ P_dir
        denom = np.maximum(np.real(np.sum(np.conj(P_dir) * AP, axis=0)), 1e-15)
        alpha = np.real(rz_old) / denom
        X = X + P_dir * alpha[None, :]
        R = R - AP * alpha[None, :]
        Z = apply_prec(R)
        rz_new = np.sum(np.conj(R) * Z, axis=0)
        beta = np.real(rz_new) / np.maximum(np.real(rz_old), 1e-15)
        P_dir = Z + P_dir * beta[None, :]
        rz_old = rz_new
    rel_res = float(np.linalg.norm(Phi @ X - RHS) / np.linalg.norm(RHS))
    W_c = np.array([X[:, k * N:(k + 1) * N] for k in range(K)])
    P_h = X @ np.linalg.solve(H_stack @ X + 1e-4 * np.eye(K * N), H_stack @ S_tar_bb)
    W_s = S_tar_bb - P_h
    p_c = sum(float(np.sum(np.abs(F_blk @ W_c[k]) ** 2)) for k in range(K))
    p_s = float(np.sum(np.abs(F_blk @ W_s) ** 2))
    W_c *= np.sqrt(0.65 * P_max / max(p_c, 1e-15))
    W_s *= np.sqrt(0.35 * P_max / max(p_s, 1e-15))
    return W_c, W_s, rel_res


def eval_g2_s2_2_neumann(sc):
    """Probes #7 G2-S2-2: 27 path combos + row-permuted banded D_dom + 2nd-order Neumann."""
    Nt, Nrf, K, Pk, N = sc["Nt"], sc["Nrf"], sc["K"], sc["Pk"], sc["N"]
    s_step = round(2.0 * N * sc["c1"])
    best_combo = None
    best_score = -1e18
    for combo in itertools.product(range(Pk), repeat=K):
        shifts = [(s_step * sc["users_paths"][k][combo[k]][1] + round(sc["users_paths"][k][combo[k]][2])) % N for k in range(K)]
        p_keep = sum(abs(sc["users_paths"][k][combo[k]][0]) ** 2 for k in range(K))
        min_sep = min(abs(((shifts[i] - shifts[j] + N // 2) % N) - N // 2) for i in range(K) for j in range(i + 1, K))
        score = p_keep + 0.08 * min(min_sep, 6)
        if score > best_score:
            best_score = score
            best_combo = combo

    # Build analog F_rf focusing on selected dominant paths while suppressing secondary paths
    F_rf = np.zeros((Nt, Nrf), dtype=np.complex128)
    for k in range(K):
        p_star = best_combo[k]
        a_main = ula_steering(Nt, sc["users_paths"][k][p_star][3], True)
        R_sub = np.zeros((Nt, Nt), dtype=np.complex128)
        for p in range(Pk):
            if p != p_star:
                ap = ula_steering(Nt, sc["users_paths"][k][p][3], True)
                R_sub += (abs(sc["users_paths"][k][p][0]) ** 2) * np.outer(ap, np.conj(ap))
        v = np.linalg.solve(np.eye(Nt) + 15.0 * R_sub, a_main)
        F_rf[:, k] = np.exp(1j * np.angle(v)) / np.sqrt(Nt)
    F_rf[:, K] = sc["a_tar"]

    F_blk = np.kron(np.eye(N), F_rf)
    H_eff = [sc["H_users"][k] @ F_blk for k in range(K)]
    # Permute rows of each user k by +Delta_{k,p*} so dominant path sits on main band!
    H_perm_list = []
    inv_row_perms = []
    for k in range(K):
        p_star = best_combo[k]
        sh = (s_step * sc["users_paths"][k][p_star][1] + round(sc["users_paths"][k][p_star][2])) % N
        # In AFDM, delay ell shifts output index m -> (m + 2Nc1*ell - alpha) mod N or (m - ...): find empirical peak of row 0!
        col_norms = np.array([np.linalg.norm(H_eff[k][0, m * Nrf:(m + 1) * Nrf]) for m in range(N)])
        c_peak = int(np.argmax(col_norms))  # row 0 couples strongest to input bin c_peak -> row m couples to (m + c_peak) mod N
        r_idx = np.array([(m - c_peak) % N for m in range(N)], dtype=np.int64)
        H_perm_list.append(H_eff[k][r_idx, :])
        inv_row_perms.append(np.argsort(r_idx))

    # Interleave users per bin m so Gram M = H_p H_p^H + reg I has (K x K) blocks per bin m!
    H_inter = np.zeros((K * N, N * Nrf), dtype=np.complex128)
    for m in range(N):
        for k in range(K):
            H_inter[m * K + k, :] = H_perm_list[k][m, :]
    M_gram = H_inter @ H_inter.conj().T + K * sc["sigma2"] * np.eye(K * N)
    D_dom = banded_hermitian_approx(M_gram, K, N, half_bw=2)
    E_off = M_gram - D_dom
    D_inv = np.linalg.inv(D_dom)
    DE_norm = float(np.linalg.norm(D_inv @ E_off, 2))
    # 0th-order (A-only) vs 2nd-order Neumann (A+B):
    M_inv_0 = D_inv
    DE = D_inv @ E_off
    M_inv_2 = (np.eye(K * N) - DE + DE @ DE) @ D_inv

    def make_W_from_Minv(Minv):
        G_inter = H_inter.conj().T @ Minv  # (N*Nrf, K*N)
        W_c = np.zeros((K, N * Nrf, N), dtype=np.complex128)
        for m in range(N):
            for k in range(K):
                orig_m = int(np.where(inv_row_perms[k] == m)[0][0])
                # Wait: H_perm[k] = P_k H_eff[k] => y_perm = H_perm x, we want y_eff[orig] = d[orig] => d_perm[m] = d[r_idx[m]]
                W_c[k, :, m] = G_inter[:, inv_row_perms[k][m] * K + k]
        W_s = np.zeros((N * Nrf, N), dtype=np.complex128)
        bs = np.zeros(Nrf, dtype=np.complex128)
        bs[K] = 1.0
        for m in range(N):
            W_s[m * Nrf:(m + 1) * Nrf, m] = bs
        return W_c, W_s

    W_c0, W_s0 = make_W_from_Minv(M_inv_0)
    W_c2, W_s2 = make_W_from_Minv(M_inv_2)
    sr0, ser0, tg0, _ = eval_g2_arm(sc, F_rf, W_c0, W_s0)
    sr2, ser2, tg2, _ = eval_g2_arm(sc, F_rf, W_c2, W_s2)
    return {"DE_norm2": DE_norm, "sr_0th_Aonly": sr0, "ser_0th": ser0, "sr_2nd_AB": sr2, "ser_2nd": ser2, "tg": tg2}


def main():
    t0 = time.time()
    n_trials = 2
    rows = []
    rng_scr = np.random.default_rng(777)
    for idx in range(n_trials):
        sc = make_g2_scene(8100 + idx)
        F_elbir = optimize_analog_manifold(sc, "elbir")
        F_liao = optimize_analog_manifold(sc, "liao_port")
        F_s12 = optimize_analog_manifold(sc, "g2_s1_2")
        F_s21_true = optimize_analog_manifold(sc, "g2_s2_1_true")
        F_s21_scram = optimize_analog_manifold(sc, "g2_s2_1_scram", rng_scr=rng_scr)

        # Baselines (all under common TarGain >= -3.01 dB!)
        Wc_b1, Ws_b1, _ = solve_crossbin_baseband(sc, F_elbir, "per_bin_elbir")
        sr_b1, ser_b1, tg_b1, _ = eval_g2_arm(sc, F_elbir, Wc_b1, Ws_b1)

        Wc_b2, Ws_b2, _ = solve_crossbin_baseband(sc, F_liao, "per_bin_elbir")
        sr_b2, ser_b2, tg_b2, _ = eval_g2_arm(sc, F_liao, Wc_b2, Ws_b2)

        Wc_a, Ws_a, _ = solve_crossbin_baseband(sc, F_elbir, "per_bin_liu")
        sr_a, ser_a, tg_a, _ = eval_g2_arm(sc, F_elbir, Wc_a, Ws_a)

        # Also Liu 2607 on Liao analog array (strongest per-bin baseline!)
        Wc_al, Ws_al, _ = solve_crossbin_baseband(sc, F_liao, "per_bin_liu")
        sr_al, ser_al, tg_al, _ = eval_g2_arm(sc, F_liao, Wc_al, Ws_al)

        # #1 G2-S1-2: A-only (F_s12 + per_bin_liu), B-only (strongest fixed baseline F_rf + dual-axis PCG), A+B (F_s12 + dual-axis PCG)
        Wc_s12_A, Ws_s12_A, _ = solve_crossbin_baseband(sc, F_s12, "per_bin_liu")
        sr_s12_A, ser_s12_A, tg_s12_A, _ = eval_g2_arm(sc, F_s12, Wc_s12_A, Ws_s12_A)

        Wc_s12_B_elb, Ws_s12_B_elb, _ = solve_crossbin_baseband(sc, F_elbir, "pcg_dual_axis", pcg_iters=6)
        sr_s12_B_elb, ser_s12_B_elb, _, _ = eval_g2_arm(sc, F_elbir, Wc_s12_B_elb, Ws_s12_B_elb)

        Wc_s12_B_liao, Ws_s12_B_liao, _ = solve_crossbin_baseband(sc, F_liao, "pcg_dual_axis", pcg_iters=6)
        sr_s12_B_liao, ser_s12_B_liao, _, _ = eval_g2_arm(sc, F_liao, Wc_s12_B_liao, Ws_s12_B_liao)

        Wc_s12_AB, Ws_s12_AB, res_dual = solve_crossbin_baseband(sc, F_s12, "pcg_dual_axis", pcg_iters=6)
        sr_s12_AB, ser_s12_AB, tg_s12_AB, _ = eval_g2_arm(sc, F_s12, Wc_s12_AB, Ws_s12_AB)

        # Compare preconditioners at 6 PCG steps on F_s12:
        _, _, res_zhu = solve_crossbin_baseband(sc, F_s12, "pcg_zhu_jacobi", pcg_iters=6)
        _, _, res_dop = solve_crossbin_baseband(sc, F_s12, "pcg_dop_only", pcg_iters=6)
        _, _, res_del = solve_crossbin_baseband(sc, F_s12, "pcg_del_only", pcg_iters=6)
        Wc_dop, Ws_dop, _ = solve_crossbin_baseband(sc, F_s12, "pcg_dop_only", pcg_iters=6)
        sr_dop, ser_dop, _, _ = eval_g2_arm(sc, F_s12, Wc_dop, Ws_dop)

        # #5 G2-S2-1: True collision weight vs Scrambled weight vs Unweighted (F_s12) under exact dense cross-bin solver
        Wc_t, Ws_t, _ = solve_crossbin_baseband(sc, F_s21_true, "dense")
        sr_s21_true, ser_s21_true, _, _ = eval_g2_arm(sc, F_s21_true, Wc_t, Ws_t)
        Wc_sc, Ws_sc, _ = solve_crossbin_baseband(sc, F_s21_scram, "dense")
        sr_s21_scram, _, _, _ = eval_g2_arm(sc, F_s21_scram, Wc_sc, Ws_sc)
        Wc_unw, Ws_unw, _ = solve_crossbin_baseband(sc, F_s12, "dense")
        sr_s12_dense, _, _, _ = eval_g2_arm(sc, F_s12, Wc_unw, Ws_unw)

        # #7 G2-S2-2: Neumann
        s22 = eval_g2_s2_2_neumann(sc)

        rows.append({
            "sr_a_elbir_liu": sr_a, "ser_a": ser_a, "tg_a": tg_a,
            "sr_a_liao_liu": sr_al, "ser_a_liao": ser_al,
            "sr_b_elbir": sr_b1, "ser_b_elbir": ser_b1,
            "sr_b_liao": sr_b2, "ser_b_liao": ser_b2,
            "s12_A_sr": sr_s12_A, "s12_A_ser": ser_s12_A,
            "s12_B_elbir_sr": sr_s12_B_elb, "s12_B_liao_sr": sr_s12_B_liao,
            "s12_AB_sr": sr_s12_AB, "s12_AB_ser": ser_s12_AB, "s12_AB_tg": tg_s12_AB,
            "s12_dense_sr": sr_s12_dense, "s12_dop_sr": sr_dop, "s12_dop_ser": ser_dop,
            "pcg6_res_zhu": res_zhu, "pcg6_res_dop": res_dop, "pcg6_res_del": res_del, "pcg6_res_dual": res_dual,
            "s21_true_sr": sr_s21_true, "s21_scram_sr": sr_s21_scram,
            "s22_DE_norm2": s22["DE_norm2"], "s22_A_sr": s22["sr_0th_Aonly"], "s22_AB_sr": s22["sr_2nd_AB"], "s22_AB_ser": s22["ser_2nd"],
        })

    avg = {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
    avg["elapsed_sec"] = time.time() - t0
    print(json.dumps(avg, indent=2))


if __name__ == "__main__":
    main()
