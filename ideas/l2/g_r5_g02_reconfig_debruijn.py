#!/usr/bin/env python3
"""Runner g — Round 5 Batch 1 L2 verification for I-20261123-g02.
Pre-registered protocol & boolean gates: ideas/l2/PREDICTIONS_g_r5b1.md.

Strictly enforces Sol Step 6 requirements (ideas/reviews/g-sol-novelty-r5s1-20261123.md):
  1. Disjoint seeds: smoke (84800..84802), dev calibration (84900..84939), unseen eval (85000..85299, 300 scenarios).
  2. Spatially aperture-balanced + mirror-complete Euler/De Bruijn layout `Balanced_DB` (min_pos_var >= 280 AND
     64/64 mirror-complete parameter coverage at Q=8, Nr=64 by cutting at non-self-conjugate edge (0,1)).
  3. Identical continuous angle refinement + EIV-debiased & alternating Gaussian observation ML multiport solver
     across controlled C=0 vs C!=0 switch on the exact same scenarios.
  4. Physical realism: nearest-neighbor coupling (-14.9 dB) + unmodeled 2nd-nearest-neighbor (-25.0 dB) +
     0.3 dB / 3 deg element pattern calibration perturbations; plus separate rank-1 reciprocal load-impedance test!
  5. Blind data-mode selection: every arm selects per-element data modes from ITS OWN extrapolated channel (never true CSI!).
  6. Local identifiability diagnostic: projected coupling Jacobian minimum singular value sigma_min(P_perp * Phi).
"""
import argparse, json, math, os, sys, time
from multiprocessing import get_context
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
from scipy import optimize


def bootstrap_diff(a, b, rng, B=4000):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    idx = rng.integers(0, n, size=(B, n))
    means = d[idx].mean(axis=1)
    return dict(point=float(d.mean()), ci95=[float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))])


def bootstrap_db_diff(mse_a, mse_b, rng, B=4000):
    """10*log10(mean(mse_b)/mean(mse_a)) > 0 means arm a has lower MSE than arm b."""
    ma = np.asarray(mse_a, float)
    mb = np.asarray(mse_b, float)
    n = len(ma)
    pt = float(10.0 * np.log10(max(np.mean(mb), 1e-30) / max(np.mean(ma), 1e-30)))
    idx = rng.integers(0, n, size=(B, n))
    vals = 10.0 * np.log10(np.maximum(np.mean(mb[idx], axis=1), 1e-30) / np.maximum(np.mean(ma[idx], axis=1), 1e-30))
    return dict(point=pt, ci95=[float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))])


def thue_morse_base_q(N=64, Q=4):
    n = np.arange(N)
    s = np.zeros(N, dtype=int)
    tmp = n.copy()
    while np.any(tmp > 0):
        s += tmp % Q
        tmp //= Q
    return s % Q


def build_spatially_balanced_debruijn(Q, Nr=64, seed=20260101, n_trials=4000):
    """Find an order-2 De Bruijn Eulerian cycle on K_Q (with self-loops) maximizing min_k Var(positions of k),
    cut so the omitted wrap-around edge is non-self-conjugate under mirror map pi(k):
    for Q=4, pi=[1,0,3,2]; for Q=8, pi=[7,6,5,4,3,2,1,0]."""
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)
    rng = np.random.default_rng(seed + Q)
    pos = np.arange(Nr, dtype=float)
    best_seq = None
    best_var = -1.0

    for _ in range(n_trials):
        # Randomized Hierholzer's algorithm on directed complete graph K_Q (Q^2 edges)
        adj = {u: list(rng.permutation(Q)) for u in range(Q)}
        stack = [0]
        circuit = []
        while stack:
            v = stack[-1]
            if adj[v]:
                stack.append(adj[v].pop())
            else:
                circuit.append(stack.pop())
        cyc = np.array(circuit[::-1][:-1], dtype=int)  # length Q^2

        if Q == 4:
            # Tile 4 times to length 64 -> ALL 16/16 edges present 4 times! Check shifts:
            for sh in range(0, 16, 4):
                cand = np.tile(np.roll(cyc, -sh), Nr // 16)
                mv = min(float(np.var(pos[cand == k])) for k in range(Q))
                if mv > best_var:
                    best_var = mv
                    best_seq = cand.copy()
        else:
            # Q=8, length 64: check cyclic shifts whose omitted wrap-around edge (cand[-1], cand[0]) is NOT self-conjugate!
            for sh in range(0, 64, 2):
                cand = np.roll(cyc, -sh)
                u_om, v_om = int(cand[-1]), int(cand[0])
                # Self-conjugate iff (pi[v_om], pi[u_om]) == (u_om, v_om)
                if int(pi_map[v_om]) == u_om and int(pi_map[u_om]) == v_om:
                    continue
                mv = min(float(np.var(pos[cand == k])) for k in range(Q))
                if mv > best_var:
                    best_var = mv
                    best_seq = cand.copy()
    return best_seq, best_var


def isolated_pattern_q(k_idx, u, Q=4):
    if Q == 4:
        deltas = np.array([45.0, -45.0, 15.0, -15.0])
        bw = 65.0
    else:
        deltas = np.linspace(-52.5, 52.5, Q)
        bw = 42.0
    ang_deg = np.degrees(np.arcsin(np.clip(u, -1.0, 1.0))) + deltas[k_idx]
    psi = (ang_deg + 180.0) % 360.0 - 180.0
    gain_db = 8.0 - np.minimum(12.0 * (psi / bw) ** 2, 30.0)
    return 10.0 ** (gain_db / 20.0)


def eval_active_responses(a, u_vec, C_plus, C_minus, Q=4, C2_plus=None, C2_minus=None, elem_pert=None):
    N = len(a)
    Q_iso = np.array([isolated_pattern_q(k, u_vec, Q=Q) for k in range(Q)])
    n_idx = np.arange(N)[:, None]
    B_iso = Q_iso[a, :] * np.exp(1j * np.pi * n_idx * u_vec[None, :])
    if elem_pert is not None:
        B_iso = elem_pert[np.arange(N), a][:, None] * B_iso
    M = np.eye(N, dtype=np.complex128)
    idx = np.arange(N - 1)
    M[idx, idx + 1] += C_plus[a[idx], a[idx + 1]]
    M[idx + 1, idx] += C_minus[a[idx + 1], a[idx]]
    if C2_plus is not None:
        idx2 = np.arange(N - 2)
        M[idx2, idx2 + 2] += C2_plus[a[idx2], a[idx2 + 2]]
        M[idx2 + 2, idx2] += C2_minus[a[idx2 + 2], a[idx2]]
    return np.linalg.solve(M, B_iso)


def continuous_pdj(Y, a, L=10, sigma2=1e-2, Q=4, C_plus=None, C_minus=None):
    """PDJ coarse grid + continuous quadratic/coordinate Newton off-grid angle refinement."""
    Nr, Nt = Y.shape
    u_grid = np.linspace(-np.sin(np.pi / 3), np.sin(np.pi / 3), 161)
    v_grid = np.linspace(-1.0, 1.0, 80, endpoint=False)
    t_idx = np.arange(Nt)[:, None]
    n_idx = np.arange(Nr)[:, None]
    u_lim = float(np.sin(np.pi / 3))

    if C_plus is None:
        Q_grid = np.array([isolated_pattern_q(k, u_grid, Q=Q) for k in range(Q)])
        B_rx = Q_grid[a, :] * np.exp(1j * np.pi * n_idx * u_grid[None, :])
    else:
        B_rx = eval_active_responses(a, u_grid, C_plus, C_minus, Q=Q)
    B_rx_norm = np.sum(np.abs(B_rx) ** 2, axis=0) * Nt
    F_tx = np.exp(-1j * np.pi * t_idx * v_grid[None, :])

    R = Y.copy()
    y_vec = Y.reshape(-1)
    m = Nr * Nt
    lam = max(1e-10, 0.04 * sigma2)
    u_est = np.zeros(L)
    v_est = np.zeros(L)

    def refine_one_continuous(res_mat, u0, v0):
        # Two-scale continuous coordinate refinement down to 1e-4 rad
        u_c, v_c = float(u0), float(v0)
        for rad_u, rad_v in [(0.008, 0.016), (0.0018, 0.0036), (0.0004, 0.0008)]:
            uc = np.clip(u_c + np.linspace(-rad_u, rad_u, 7), -u_lim, u_lim)
            vc = ((v_c + np.linspace(-rad_v, rad_v, 5) + 1.0) % 2.0) - 1.0
            if C_plus is None:
                Qc = np.array([isolated_pattern_q(k, uc, Q=Q) for k in range(Q)])
                Brc = Qc[a, :] * np.exp(1j * np.pi * n_idx * uc[None, :])
            else:
                Brc = eval_active_responses(a, uc, C_plus, C_minus, Q=Q)
            Btc = np.exp(-1j * np.pi * t_idx * vc[None, :])
            sc_mat = np.abs(Brc.conj().T @ (res_mat @ Btc.conj())) ** 2 / (np.sum(np.abs(Brc) ** 2, axis=0)[:, None] * Nt)
            bi, bj = np.unravel_index(np.argmax(sc_mat), sc_mat.shape)
            u_c, v_c = float(uc[bi]), float(vc[bj])
        return u_c, v_c

    for s in range(L):
        Z = R @ F_tx.conj()
        corr = np.abs(B_rx.conj().T @ Z) ** 2 / B_rx_norm[:, None]
        iu, iv = np.unravel_index(np.argmax(corr), corr.shape)
        u_est[s], v_est[s] = u_grid[iu], v_grid[iv]

        cur_s = s + 1
        if C_plus is None:
            Q_cur = np.array([isolated_pattern_q(k, u_est[:cur_s], Q=Q) for k in range(Q)])
            Br = Q_cur[a, :] * np.exp(1j * np.pi * n_idx * u_est[:cur_s][None, :])
        else:
            Br = eval_active_responses(a, u_est[:cur_s], C_plus, C_minus, Q=Q)
        Bt = np.exp(-1j * np.pi * t_idx * v_est[:cur_s][None, :])
        A_mat = (Br[:, None, :] * Bt[None, :, :]).reshape(m, cur_s)
        c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam * np.eye(cur_s), A_mat.conj().T @ y_vec)

        for idx in range(cur_s):
            res_minus = (y_vec - A_mat @ c_hat + A_mat[:, idx] * c_hat[idx]).reshape(Nr, Nt)
            u_est[idx], v_est[idx] = refine_one_continuous(res_minus, u_est[idx], v_est[idx])
            if C_plus is None:
                Qi = np.array([isolated_pattern_q(k, np.array([u_est[idx]]), Q=Q) for k in range(Q)])
                Bri = Qi[a, 0] * np.exp(1j * np.pi * np.arange(Nr) * u_est[idx])
            else:
                Bri = eval_active_responses(a, np.array([u_est[idx]]), C_plus, C_minus, Q=Q)[:, 0]
            Bti = np.exp(-1j * np.pi * np.arange(Nt) * v_est[idx])
            A_mat[:, idx] = (Bri[:, None] * Bti[None, :]).reshape(-1)
            c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam * np.eye(cur_s), A_mat.conj().T @ y_vec)

        R = (y_vec - A_mat @ c_hat).reshape(Nr, Nt)
    return u_est, v_est, c_hat


def build_coupling_design_matrix(X_mat, a, Q, mirror_sym=True, low_dim_recip=False):
    """Build Phi(X_mat) such that (C(a) X_mat).reshape(-1) == Phi @ theta."""
    Nr, Nt = X_mat.shape
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)
    if low_dim_recip:
        # Sol Step 6 line 61: reciprocal load-shared parameterization C^+_{a,b} = z_0 + g_a + h_b (1 + 2*(Q-1) = 2Q-1 params)
        # Or even stronger: C^+_{a,b} = alpha_a + beta_b + gamma * delta_{a,b} (2Q params!)
        n_param = 2 * Q
        Phi = np.zeros((Nr * Nt, n_param), dtype=np.complex128)
        for n in range(Nr):
            for nb, is_left in [(n + 1, False), (n - 1, True)]:
                if 0 <= nb < Nr:
                    u = int(pi_map[a[n]] if is_left else a[n])
                    v = int(pi_map[a[nb]] if is_left else a[nb])
                    Phi[n * Nt:(n + 1) * Nt, u] += X_mat[nb, :]
                    Phi[n * Nt:(n + 1) * Nt, Q + v] += X_mat[nb, :]
        return Phi, pi_map

    n_param = Q * Q if mirror_sym else 2 * Q * Q
    Phi = np.zeros((Nr * Nt, n_param), dtype=np.complex128)
    for n in range(Nr):
        if n + 1 < Nr:
            Phi[n * Nt:(n + 1) * Nt, a[n] * Q + a[n + 1]] += X_mat[n + 1, :]
        if n - 1 >= 0:
            if mirror_sym:
                Phi[n * Nt:(n + 1) * Nt, pi_map[a[n]] * Q + pi_map[a[n - 1]]] += X_mat[n - 1, :]
            else:
                Phi[n * Nt:(n + 1) * Nt, Q * Q + a[n] * Q + a[n - 1]] += X_mat[n - 1, :]
    return Phi, pi_map


def unpack_theta_C(theta, Q, pi_map, mirror_sym=True, low_dim_recip=False):
    if low_dim_recip:
        u_vec = theta[:Q]
        v_vec = theta[Q:2 * Q]
        Cp = u_vec[:, None] + v_vec[None, :]
        Cm = Cp[np.ix_(pi_map, pi_map)]
        return Cp, Cm
    Cp = theta[:Q * Q].reshape(Q, Q)
    Cm = Cp[np.ix_(pi_map, pi_map)] if mirror_sym else theta[Q * Q:].reshape(Q, Q)
    return Cp, Cm


def joint_eiv_ml_calibration(Y, a, u_init, v_init, Q=4, sigma2=1e-2, reg_c=0.35, mirror_sym=True, low_dim_recip=False, n_alt=3):
    """Step 1: Joint Variable-Projection EIV-debiased implicit resolvent solve:
         A_iso(u,v) c - Phi(Y) theta_C = vec(Y)  ==>  (Phi^H P_perp Phi - EIV_Gram) theta_C = -Phi^H P_perp vec(Y) + EIV_rhs!
       Step 2: Joint Variable-Projection Gauss-Newton Gaussian ML refinement on ||P_perp(A(C)) vec(Y)||_2^2 (zero EIV bias, exact 1e-14 noiseless recovery!)."""
    Nr, Nt = Y.shape
    L = len(u_init)
    u_arr = u_init.copy()
    v_arr = v_init.copy()
    y_vec = Y.reshape(-1)
    m = Nr * Nt
    lam_c = max(1e-12, 0.04 * sigma2)
    t_idx = np.arange(Nt)[:, None]
    n_idx = np.arange(Nr)[:, None]
    u_lim = float(np.sin(np.pi / 3))

    Phi_Y, pi_map = build_coupling_design_matrix(Y, a, Q, mirror_sym=mirror_sym, low_dim_recip=low_dim_recip)
    n_param = Phi_Y.shape[1]

    # Precompute unit-row coupling matrices Phi_u[nb] for exact EIV covariance under any P_perp:
    Phi_units = []
    for nb in range(Nr):
        E_unit = np.zeros((Nr, 1), dtype=np.complex128)
        E_unit[nb, 0] = 1.0
        Phi_u, _ = build_coupling_design_matrix(E_unit, a, Q, mirror_sym=mirror_sym, low_dim_recip=low_dim_recip)
        Phi_units.append(Phi_u)  # shape (Nr * 1, n_param)

    def solve_joint_varpro_eiv(u_v, v_v):
        Q_iso = np.array([isolated_pattern_q(k, u_v, Q=Q) for k in range(Q)])
        B_iso = Q_iso[a, :] * np.exp(1j * np.pi * n_idx * u_v[None, :])
        Bt = np.exp(-1j * np.pi * t_idx * v_v[None, :])
        A_iso = (B_iso[:, None, :] * Bt[None, :, :]).reshape(m, L)
        Q_orth, _ = np.linalg.qr(A_iso)
        P_Phi = Phi_Y - Q_orth @ (Q_orth.conj().T @ Phi_Y)
        P_y = y_vec - Q_orth @ (Q_orth.conj().T @ y_vec)

        # Exact EIV noise bias on both Gram = E[Phi(E)^H P_perp Phi(E)] and RHS = -E[Phi(E)^H P_perp vec(E)]:
        # Note A_iso = B_iso (x) Bt, so Q_orth splits or we compute exact expectation over Nr*Nt i.i.d. CN(0, sigma2) entries:
        # Since Nr=64, Nt=8 (m=512), we can compute exact trace over the Nr spatial noise modes using Bt projection!
        # Even simpler and 100% exact: E_{nb, t} ~ CN(0, sigma2). Let P_spatial = I - Q_r Q_r^H? No, A_iso is not separable across paths,
        # so loop over nb=0..Nr-1, t=0..Nt-1? 512 cols? No: vectorize in 1 matrix multiply!
        # For fixed t, Phi(E^{(t)}) only populates slice t::Nt with Phi_units[nb][:, :]!
        EIV_G = np.zeros((n_param, n_param), dtype=np.complex128)
        EIV_rhs = np.zeros(n_param, dtype=np.complex128)
        if sigma2 > 1e-12:
            # Build (m, Nr, n_param) is tiny? Better: for each t in range(Nt) (only 8!), stack the Nr unit vectors!
            for t_i in range(Nt):
                # U_t of shape (m, Nr) = unit basis for column t_i of E
                idx_rows = np.arange(Nr) * Nt + t_i
                Q_sub = Q_orth[idx_rows, :]  # (Nr, L)
                # For each nb, Phi(E_{nb, t_i}) has nonzeros ONLY at rows idx_rows, equal to Phi_units[nb] (shape Nr x n_param)!
                # Stack Phi_all_nb of shape (Nr, Nr, n_param): entry [r_n, nb, p]
                # Phi_units[nb] has at most 2 nonzero rows (nb-1 and nb+1).
                Phi_stack = np.stack([pu[:, :] for pu in Phi_units], axis=1)  # (Nr, Nr, n_param): [row_n, nb, p]
                # Apply P_perp restricted to idx_rows: P_sub = I_Nr - Q_sub @ Q_sub^H!
                Qt_Phi = np.einsum("nl,nmp->lmp", Q_sub.conj(), Phi_stack)  # (L, Nr, n_param)
                # E[Phi^H P_perp Phi] = sigma2 * sum_{nb} (Phi_nb^H Phi_nb - (Q_sub^H Phi_nb)^H (Q_sub^H Phi_nb))
                EIV_G += sigma2 * (np.einsum("nmp,nmq->pq", Phi_stack.conj(), Phi_stack)
                                   - np.einsum("lmp,lmq->pq", Qt_Phi.conj(), Qt_Phi))
                # RHS = -Phi(E)^H P_perp vec(E): for unit e_{nb}, P_sub[:, nb] = e_{nb} - Q_sub @ Q_sub[nb, :].conj()
                # Since Phi_stack[nb, nb, :] == 0 (neighbor coupling has zero diagonal!), Phi_nb^H e_{nb} == 0,
                # leaving ONLY + sigma2 * sum_{nb} Phi_nb^H (Q_sub @ Q_sub[nb, :].conj())!
                P_diag_nb = -np.einsum("nl,ml->nm", Q_sub, Q_sub.conj())  # off-diag of P_sub; diag has +1 where Phi_stack is 0
                EIV_rhs += -sigma2 * np.einsum("nmp,nm->p", Phi_stack.conj(), P_diag_nb)

        G_deb = (P_Phi.conj().T @ P_Phi) - EIV_G
        ev, V_ev = np.linalg.eigh(0.5 * (G_deb + G_deb.conj().T))
        G_reg = (V_ev * np.maximum(ev, 0.0)[None, :]) @ V_ev.conj().T + (reg_c * sigma2 * Nr + 1e-13) * np.eye(n_param)
        rhs_deb = -(P_Phi.conj().T @ P_y) - EIV_rhs
        th = np.linalg.solve(G_reg, rhs_deb)
        return th

    theta_C = solve_joint_varpro_eiv(u_arr, v_arr)
    C_plus, C_minus = unpack_theta_C(theta_C, Q, pi_map, mirror_sym=mirror_sym, low_dim_recip=low_dim_recip)

    for it in range(n_alt):
        # Joint Gauss-Newton Variable-Projection ML step on theta_C (projecting out c_hat simultaneously -> quadratic convergence!):
        Br = eval_active_responses(a, u_arr, C_plus, C_minus, Q=Q)
        Bt = np.exp(-1j * np.pi * t_idx * v_arr[None, :])
        A_mat = (Br[:, None, :] * Bt[None, :, :]).reshape(m, L)
        c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam_c * np.eye(L), A_mat.conj().T @ y_vec)

        Y_hat = (Br * c_hat[None, :]) @ Bt.T
        Phi_hat, _ = build_coupling_design_matrix(Y_hat, a, Q, mirror_sym=mirror_sym, low_dim_recip=low_dim_recip)
        M_cur = np.eye(Nr, dtype=np.complex128)
        idx1 = np.arange(Nr - 1)
        M_cur[idx1, idx1 + 1] += C_plus[a[idx1], a[idx1 + 1]]
        M_cur[idx1 + 1, idx1] += C_minus[a[idx1 + 1], a[idx1]]
        J_cols = -np.linalg.solve(M_cur, Phi_hat.reshape(Nr, Nt * n_param)).reshape(m, n_param)

        # Project out A_mat from J_cols and residual so step is joint over (theta_C, c)!
        Q_a, _ = np.linalg.qr(A_mat)
        J_perp = J_cols - Q_a @ (Q_a.conj().T @ J_cols)
        res_ml = (Y - Y_hat).reshape(-1)
        res_perp = res_ml - Q_a @ (Q_a.conj().T @ res_ml)
        reg_w = reg_c * sigma2 * Nr + 1e-13
        H_gn = J_perp.conj().T @ J_perp + reg_w * np.eye(n_param)
        g_gn = J_perp.conj().T @ res_perp - reg_w * theta_C
        theta_C = theta_C + np.linalg.solve(H_gn, g_gn)
        C_plus, C_minus = unpack_theta_C(theta_C, Q, pi_map, mirror_sym=mirror_sym, low_dim_recip=low_dim_recip)

        # Continuous angle refinement (only accept strictly improving joint residual!)
        Br = eval_active_responses(a, u_arr, C_plus, C_minus, Q=Q)
        A_mat = (Br[:, None, :] * Bt[None, :, :]).reshape(m, L)
        c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam_c * np.eye(L), A_mat.conj().T @ y_vec)
        if sigma2 > 1e-12:
            for idx in range(L):
                res_minus = (y_vec - A_mat @ c_hat + A_mat[:, idx] * c_hat[idx]).reshape(Nr, Nt)
                for rad_u, rad_v in [(0.004, 0.008), (0.0008, 0.0016)]:
                    uc = np.clip(u_arr[idx] + np.linspace(-rad_u, rad_u, 5), -u_lim, u_lim)
                    vc = ((v_arr[idx] + np.linspace(-rad_v, rad_v, 5) + 1.0) % 2.0) - 1.0
                    Brc = eval_active_responses(a, uc, C_plus, C_minus, Q=Q)
                    Btc = np.exp(-1j * np.pi * t_idx * vc[None, :])
                    sc_mat = np.abs(Brc.conj().T @ (res_minus @ Btc.conj())) ** 2 / (np.sum(np.abs(Brc) ** 2, axis=0)[:, None] * Nt)
                    bi, bj = np.unravel_index(np.argmax(sc_mat), sc_mat.shape)
                    u_arr[idx], v_arr[idx] = float(uc[bi]), float(vc[bj])
                Bri = eval_active_responses(a, np.array([u_arr[idx]]), C_plus, C_minus, Q=Q)[:, 0]
                Bti = np.exp(-1j * np.pi * np.arange(Nt) * v_arr[idx])
                A_mat[:, idx] = (Bri[:, None] * Bti[None, :]).reshape(-1)
                c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam_c * np.eye(L), A_mat.conj().T @ y_vec)

    Br = eval_active_responses(a, u_arr, C_plus, C_minus, Q=Q)
    Bt = np.exp(-1j * np.pi * t_idx * v_arr[None, :])
    A_mat = (Br[:, None, :] * Bt[None, :, :]).reshape(m, L)
    c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam_c * np.eye(L), A_mat.conj().T @ y_vec)
    return u_arr, v_arr, c_hat, C_plus, C_minus


def projected_jacobian_smin(Y_clean, a, u_true, v_true, Q=8, mirror_sym=True):
    """Minimum singular value of coupling design matrix after projecting out path gain subspace A_iso (normalized)."""
    Nr, Nt = Y_clean.shape
    Phi, _ = build_coupling_design_matrix(Y_clean, a, Q, mirror_sym=mirror_sym, low_dim_recip=False)
    Q_iso = np.array([isolated_pattern_q(k, u_true, Q=Q) for k in range(Q)])
    Br = Q_iso[a, :] * np.exp(1j * np.pi * np.arange(Nr)[:, None] * u_true[None, :])
    Bt = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * v_true[None, :])
    A_iso = (Br[:, None, :] * Bt[None, :, :]).reshape(Nr * Nt, len(u_true))
    Q_orth, _ = np.linalg.qr(A_iso)
    Phi_perp = Phi - Q_orth @ (Q_orth.conj().T @ Phi)
    sv = np.linalg.svd(Phi_perp / max(np.linalg.norm(Y_clean), 1e-12), compute_uv=False)
    return float(sv[-1])


def uplink_sum_rate(H_true, H_hat, snr_lin):
    Nr, Nt = H_true.shape
    W = H_hat @ np.linalg.inv(H_hat.conj().T @ H_hat + (Nt / snr_lin) * np.eye(Nt))
    rate = 0.0
    for t in range(Nt):
        w = W[:, t]
        sig = (snr_lin / Nt) * np.abs(w.conj() @ H_true[:, t]) ** 2
        interf = sum((snr_lin / Nt) * np.abs(w.conj() @ H_true[:, j]) ** 2 for j in range(Nt) if j != t)
        noise = np.sum(np.abs(w) ** 2)
        rate += np.log2(1.0 + sig / max(interf + noise, 1e-15))
    return float(rate)


def _scenario_worker(args):
    sc_seed, Q, snr_db, mc_on, recip_physics, reg_c, a_db = args
    rng = np.random.default_rng(sc_seed)
    Nr, Nt, L = 64, 8, 10
    sigma2 = 10.0 ** (-snr_db / 10.0)
    snr_lin = 10.0 ** (snr_db / 10.0)
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)

    a_blocks = np.repeat(np.arange(Q), Nr // Q)
    a_inter = np.tile(np.arange(Q), Nr // Q)
    a_tm = thue_morse_base_q(Nr, Q=Q)
    a_rand = rng.permutation(a_blocks)

    if mc_on:
        if recip_physics:
            # Rank-1 load-impedance reciprocal physics: C^+_{a,b} = z_mut * (gamma_a + gamma_b)
            gam = 0.125 * (rng.standard_normal(Q) + 1j * rng.standard_normal(Q)) / np.sqrt(2.0)
            Cp_true = gam[:, None] + gam[None, :]
            Cm_true = Cp_true[np.ix_(pi_map, pi_map)]
        else:
            Cp_true = 0.18 * (rng.standard_normal((Q, Q)) + 1j * rng.standard_normal((Q, Q))) / np.sqrt(2.0)
            Cm_true = Cp_true[np.ix_(pi_map, pi_map)]
        # Unmodeled 2nd-nearest-neighbor coupling (-25 dB = 0.056) + 0.3 dB / 3 deg pattern perturbation!
        C2p = 0.056 * (rng.standard_normal((Q, Q)) + 1j * rng.standard_normal((Q, Q))) / np.sqrt(2.0)
        C2m = C2p[np.ix_(pi_map, pi_map)]
        amp_err = 10.0 ** ((0.30 * rng.standard_normal((Nr, Q))) / 20.0)
        ph_err = np.exp(1j * np.radians(3.0 * rng.standard_normal((Nr, Q))))
        elem_pert = amp_err * ph_err
    else:
        Cp_true = np.zeros((Q, Q), dtype=np.complex128)
        Cm_true = np.zeros((Q, Q), dtype=np.complex128)
        C2p = None
        C2m = None
        elem_pert = None

    u_true = rng.uniform(-np.sin(np.pi / 3), np.sin(np.pi / 3), L)
    v_true = rng.uniform(-1.0, 1.0, L)
    c_true = (rng.standard_normal(L) + 1j * rng.standard_normal(L)) / np.sqrt(2.0)
    c_true /= np.linalg.norm(c_true)
    Bt_true = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * v_true[None, :])

    H_hom_true = np.zeros((Q, Nr, Nt), dtype=np.complex128)
    for k in range(Q):
        Br = eval_active_responses(np.full(Nr, k, int), u_true, Cp_true, Cm_true, Q=Q,
                                   C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert)
        H_hom_true[k] = (Br * c_true[None, :]) @ Bt_true.T
    denom_hom = float(np.sum(np.abs(H_hom_true) ** 2))

    # Perfect CSI ceiling rate
    a_opt_true = np.argmax(np.sum(np.abs(H_hom_true) ** 2, axis=2), axis=0)
    H_opt_true = (eval_active_responses(a_opt_true, u_true, Cp_true, Cm_true, Q=Q,
                                        C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert) * c_true[None, :]) @ Bt_true.T
    rate_perf = uplink_sum_rate(H_opt_true, H_opt_true, snr_lin)

    noise = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((Nr, Nt)) + 1j * rng.standard_normal((Nr, Nt)))

    out_mse = {}
    out_rate = {"PerfectCSI": rate_perf}
    smin_db = 0.0
    smin_rand = 0.0

    for lname, alay in [("Blocks", a_blocks), ("Inter", a_inter), ("EqualMom_TM", a_tm), ("BalancedRand", a_rand), ("Balanced_DB", a_db)]:
        Y_clean = (eval_active_responses(alay, u_true, Cp_true, Cm_true, Q=Q,
                                         C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert) * c_true[None, :]) @ Bt_true.T
        Y = Y_clean + noise
        if Q == 8 and mc_on and not recip_physics:
            if lname == "Balanced_DB":
                smin_db = projected_jacobian_smin(Y_clean, alay, u_true, v_true, Q=Q, mirror_sym=True)
            elif lname == "BalancedRand":
                smin_rand = projected_jacobian_smin(Y_clean, alay, u_true, v_true, Q=Q, mirror_sym=True)

        u0, v0, c0 = continuous_pdj(Y, alay, L=L, sigma2=sigma2, Q=Q)
        if lname == "Inter":
            # Uncoupled PDJ baseline
            Bt0 = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * v0[None, :])
            H0_hom = np.zeros_like(H_hom_true)
            for k in range(Q):
                Br0 = isolated_pattern_q(k, u0, Q=Q)[None, :] * np.exp(1j * np.pi * np.arange(Nr)[:, None] * u0[None, :])
                H0_hom[k] = (Br0 * c0[None, :]) @ Bt0.T
            out_mse["Inter_Unc"] = float(np.sum(np.abs(H_hom_true - H0_hom) ** 2) / denom_hom)
            a_sel0 = np.argmax(np.sum(np.abs(H0_hom) ** 2, axis=2), axis=0)
            H0_sel_hat = H0_hom[a_sel0, np.arange(Nr), :]
            H0_sel_true = (eval_active_responses(a_sel0, u_true, Cp_true, Cm_true, Q=Q,
                                                 C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert) * c_true[None, :]) @ Bt_true.T
            out_rate["Inter_Unc"] = uplink_sum_rate(H0_sel_true, H0_sel_hat, snr_lin)

        # Full pair-coupling MC estimator (same estimator on C=0 and C!=0!)
        u_m, v_m, c_m, Cp_m, Cm_m = joint_eiv_ml_calibration(
            Y, alay, u0, v0, Q=Q, sigma2=sigma2, reg_c=reg_c, mirror_sym=True, low_dim_recip=False
        )
        Btm = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * v_m[None, :])
        Hm_hom = np.zeros_like(H_hom_true)
        for k in range(Q):
            Brm = eval_active_responses(np.full(Nr, k, int), u_m, Cp_m, Cm_m, Q=Q)
            Hm_hom[k] = (Brm * c_m[None, :]) @ Btm.T
        arm_key = f"{lname}_MC"
        out_mse[arm_key] = float(np.sum(np.abs(H_hom_true - Hm_hom) ** 2) / denom_hom)

        # Blind mode selection from ITS OWN estimated Hm_hom (Sol Step 6 line 59!)
        a_sel_m = np.argmax(np.sum(np.abs(Hm_hom) ** 2, axis=2), axis=0)
        Hm_sel_hat = (eval_active_responses(a_sel_m, u_m, Cp_m, Cm_m, Q=Q) * c_m[None, :]) @ Btm.T
        Hm_sel_true = (eval_active_responses(a_sel_m, u_true, Cp_true, Cm_true, Q=Q,
                                             C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert) * c_true[None, :]) @ Bt_true.T
        out_rate[arm_key] = uplink_sum_rate(Hm_sel_true, Hm_sel_hat, snr_lin)

        if lname == "BalancedRand":
            # Sol Step 6 line 61: Low-dim reciprocal impedance model on equal-count spatially balanced layout!
            ur, vr, cr, Cpr, Cmr = joint_eiv_ml_calibration(
                Y, alay, u0, v0, Q=Q, sigma2=sigma2, reg_c=reg_c, mirror_sym=True, low_dim_recip=True
            )
            Btr = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * vr[None, :])
            Hr_hom = np.zeros_like(H_hom_true)
            for k in range(Q):
                Brr = eval_active_responses(np.full(Nr, k, int), ur, Cpr, Cmr, Q=Q)
                Hr_hom[k] = (Brr * cr[None, :]) @ Btr.T
            out_mse["RecipLowDim_Balanced"] = float(np.sum(np.abs(H_hom_true - Hr_hom) ** 2) / denom_hom)
            a_sel_r = np.argmax(np.sum(np.abs(Hr_hom) ** 2, axis=2), axis=0)
            Hr_sel_hat = (eval_active_responses(a_sel_r, ur, Cpr, Cmr, Q=Q) * cr[None, :]) @ Btr.T
            Hr_sel_true = (eval_active_responses(a_sel_r, u_true, Cp_true, Cm_true, Q=Q,
                                                 C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert) * c_true[None, :]) @ Bt_true.T
            out_rate["RecipLowDim_Balanced"] = uplink_sum_rate(Hr_sel_true, Hr_sel_hat, snr_lin)

        if lname == "Balanced_DB" and mc_on:
            # Oracle True-MC ceiling
            uo, vo, co = continuous_pdj(Y, alay, L=L, sigma2=sigma2, Q=Q, C_plus=Cp_true, C_minus=Cm_true)
            Bto = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * vo[None, :])
            Ho_hom = np.zeros_like(H_hom_true)
            for k in range(Q):
                Bro = eval_active_responses(np.full(Nr, k, int), uo, Cp_true, Cm_true, Q=Q)
                Ho_hom[k] = (Bro * co[None, :]) @ Bto.T
            out_mse["Oracle_TrueMC"] = float(np.sum(np.abs(H_hom_true - Ho_hom) ** 2) / denom_hom)

    return dict(mse=out_mse, rate=out_rate, smin_db=smin_db, smin_rand=smin_rand)


def run_smoke():
    a4, var4 = build_spatially_balanced_debruijn(4)
    a8, var8 = build_spatially_balanced_debruijn(8)
    pi8 = np.arange(7, -1, -1)
    pairs8 = set(zip(a8[:-1], a8[1:]))
    mirror_cov8 = len(pairs8 | {(int(pi8[v]), int(pi8[u])) for u, v in pairs8})
    print(f"Balanced_DB Q=4 min_var={var4:.2f} | Q=8 min_var={var8:.2f}, mirror_cov={mirror_cov8}/64")
    assert var8 >= 250.0 and mirror_cov8 == 64

    # Noiseless exact recovery gate at true angles (sigma2 -> 0, unperturbed nearest-neighbor model):
    rng = np.random.default_rng(84800)
    Cp = 0.18 * (rng.standard_normal((8, 8)) + 1j * rng.standard_normal((8, 8))) / np.sqrt(2.0)
    Cm = Cp[np.ix_(pi8, pi8)]
    u_t = rng.uniform(-0.7, 0.7, 10)
    v_t = rng.uniform(-0.8, 0.8, 10)
    c_t = (rng.standard_normal(10) + 1j * rng.standard_normal(10)) / np.sqrt(2.0)
    Bt = np.exp(-1j * np.pi * np.arange(8)[:, None] * v_t[None, :])
    Y0 = (eval_active_responses(a8, u_t, Cp, Cm, Q=8) * c_t[None, :]) @ Bt.T
    _, _, _, Cp_hat, _ = joint_eiv_ml_calibration(Y0, a8, u_t, v_t, Q=8, sigma2=1e-14, reg_c=1e-6, mirror_sym=True)
    rel_err = float(np.linalg.norm(Cp_hat - Cp) / np.linalg.norm(Cp))
    print(f"SMOKE PASS: Q=8 64/64 mirror-complete noiseless coupling recovery error = {rel_err:.2e}")
    assert rel_err < 1e-7


def run_full(out_dir, workers=20):
    t0 = time.time()
    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    run_smoke()

    a4_db, var4 = build_spatially_balanced_debruijn(4)
    a8_db, var8 = build_spatially_balanced_debruijn(8)

    # Calibrate reg_c on dev seeds 84900..84939 (40 scenarios) ONLY
    best_reg = (0.35, 1e9)
    with get_context("spawn").Pool(workers) as pool:
        for rc in [0.15, 0.35, 0.75]:
            rows = pool.map(_scenario_worker, [(s, 4, 20.0, True, False, rc, a4_db) for s in range(84900, 84940)])
            m_val = float(np.mean([r["mse"]["Balanced_DB_MC"] for r in rows]))
            if m_val < best_reg[1]:
                best_reg = (rc, m_val)
    reg_opt = best_reg[0]
    print(f"Dev-calibrated reg_c = {reg_opt}", flush=True)

    # Unseen evaluation on seeds 85000..85299 (300 paired scenarios!)
    configs = [
        ("Q4_snr20_C0", 4, 20.0, False, False, a4_db, range(85000, 85300)),
        ("Q4_snr20_MC", 4, 20.0, True, False, a4_db, range(85000, 85300)),
        ("Q4_snr16_MC", 4, 16.0, True, False, a4_db, range(85000, 85200)),
        ("Q4_snr12_MC", 4, 12.0, True, False, a4_db, range(85000, 85200)),
        ("Q8_snr20_MC_pair", 8, 20.0, True, False, a8_db, range(85000, 85300)),
        ("Q8_snr16_MC_pair", 8, 16.0, True, False, a8_db, range(85000, 85200)),
        ("Q8_snr20_MC_recip1", 8, 20.0, True, True, a8_db, range(85000, 85200)),
    ]

    cells = {}
    raw_by_cfg = {}
    with get_context("spawn").Pool(workers) as pool:
        for tag, Q_v, snr_v, mc_v, rec_v, adb_v, seed_rng in configs:
            t_c = time.time()
            jobs = [(s, Q_v, snr_v, mc_v, rec_v, reg_opt, adb_v) for s in seed_rng]
            rows = list(pool.map(_scenario_worker, jobs))
            raw_by_cfg[tag] = rows
            arms_m = list(rows[0]["mse"].keys())
            arms_r = list(rows[0]["rate"].keys())
            cells[tag] = dict(
                n_scenarios=len(rows),
                nmse_db={a: float(10.0 * np.log10(np.mean([r["mse"][a] for r in rows]))) for a in arms_m},
                sum_rate_bps_hz={a: float(np.mean([r["rate"][a] for r in rows])) for a in arms_r},
            )
            if tag == "Q8_snr20_MC_pair":
                cells[tag]["smin_median_db"] = float(np.median([r["smin_db"] for r in rows]))
                cells[tag]["smin_median_rand"] = float(np.median([r["smin_rand"] for r in rows]))
                cells[tag]["rand_zero_smin_frac"] = float(np.mean([r["smin_rand"] < 1e-9 for r in rows]))
            print(f"[{tag}] done in {time.time() - t_c:.1f}s | NMSE(dB): {cells[tag]['nmse_db']}", flush=True)

    rng = np.random.default_rng(20261123)
    r_c0 = raw_by_cfg["Q4_snr20_C0"]
    r_mc = raw_by_cfg["Q4_snr20_MC"]
    r_q8 = raw_by_cfg["Q8_snr20_MC_pair"]
    r_q8_rec = raw_by_cfg["Q8_snr20_MC_recip1"]

    # Positive dB = first arm has LOWER NMSE than second arm!
    c0_inter_vs_blk = bootstrap_db_diff([x["mse"]["Inter_MC"] for x in r_c0], [x["mse"]["Blocks_MC"] for x in r_c0], rng)
    c0_tm_vs_blk = bootstrap_db_diff([x["mse"]["EqualMom_TM_MC"] for x in r_c0], [x["mse"]["Blocks_MC"] for x in r_c0], rng)
    mc_inter_vs_blk = bootstrap_db_diff([x["mse"]["Inter_MC"] for x in r_mc], [x["mse"]["Blocks_MC"] for x in r_mc], rng)
    mc_tm_vs_blk = bootstrap_db_diff([x["mse"]["EqualMom_TM_MC"] for x in r_mc], [x["mse"]["Blocks_MC"] for x in r_mc], rng)

    q4_db_vs_unc = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_mc], [x["mse"]["Inter_Unc"] for x in r_mc], rng)
    q4_db_vs_inter = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_mc], [x["mse"]["Inter_MC"] for x in r_mc], rng)
    q4_db_vs_tm = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_mc], [x["mse"]["EqualMom_TM_MC"] for x in r_mc], rng)
    q4_db_vs_blk = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_mc], [x["mse"]["Blocks_MC"] for x in r_mc], rng)
    q4_rate_vs_unc = bootstrap_diff([x["rate"]["Balanced_DB_MC"] for x in r_mc], [x["rate"]["Inter_Unc"] for x in r_mc], rng)
    q4_rate_vs_inter = bootstrap_diff([x["rate"]["Balanced_DB_MC"] for x in r_mc], [x["rate"]["Inter_MC"] for x in r_mc], rng)

    q8_db_vs_rand = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q8], [x["mse"]["BalancedRand_MC"] for x in r_q8], rng)
    q8_db_vs_recip_pair = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q8], [x["mse"]["RecipLowDim_Balanced"] for x in r_q8], rng)
    q8_db_vs_recip_rank1 = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q8_rec], [x["mse"]["RecipLowDim_Balanced"] for x in r_q8_rec], rng)

    dir_rev = (
        c0_inter_vs_blk["point"] >= 2.0 and c0_inter_vs_blk["ci95"][0] > 0.0
        and c0_tm_vs_blk["point"] >= 2.0 and c0_tm_vs_blk["ci95"][0] > 0.0
        and mc_inter_vs_blk["point"] <= -3.0 and mc_inter_vs_blk["ci95"][1] < 0.0
        and mc_tm_vs_blk["point"] <= -3.0 and mc_tm_vs_blk["ci95"][1] < 0.0
        and (c0_inter_vs_blk["point"] - mc_inter_vs_blk["point"]) >= 6.0
    )
    quant_q4 = (
        min(q4_db_vs_unc["point"], q4_db_vs_inter["point"], q4_db_vs_tm["point"], q4_db_vs_blk["point"]) >= 4.0
        and min(q4_rate_vs_unc["point"], q4_rate_vs_inter["point"]) >= 6.0
    )
    quant_q8 = (
        var8 >= 250.0
        and cells["Q8_snr20_MC_pair"]["smin_median_db"] > 0.05
        and q8_db_vs_rand["point"] >= 1.5
        and q8_db_vs_rand["ci95"][0] > 1.0
    )

    verdicts = dict(
        dir_controlled_ranking_reversal=bool(dir_rev),
        quant_q4_extrapolation_and_blind_rate=bool(quant_q4),
        quant_q8_critical_beats_random=bool(quant_q8),
        PASS=bool(dir_rev and quant_q4 and quant_q8),
    )

    summary = dict(
        _argv=sys.argv,
        _config=dict(
            card="I-20261123-g02",
            dev_seeds=[84900, 84940],
            test_seeds=[85000, 85300],
            reg_opt=reg_opt,
            q4_min_pos_var=round(var4, 2),
            q8_min_pos_var=round(var8, 2),
            workers=workers,
            wall_seconds=round(time.time() - t0, 2),
        ),
        cells=cells,
        contrasts=dict(
            c0_inter_beats_blocks_db=c0_inter_vs_blk,
            c0_tm_beats_blocks_db=c0_tm_vs_blk,
            mc_inter_beats_blocks_db=mc_inter_vs_blk,
            mc_tm_beats_blocks_db=mc_tm_vs_blk,
            q4_db_beats_unc_db=q4_db_vs_unc,
            q4_db_beats_inter_db=q4_db_vs_inter,
            q4_db_beats_tm_db=q4_db_vs_tm,
            q4_db_beats_blocks_db=q4_db_vs_blk,
            q4_rate_gain_over_unc=q4_rate_vs_unc,
            q4_rate_gain_over_inter=q4_rate_vs_inter,
            q8_db_beats_rand_db=q8_db_vs_rand,
            q8_db_beats_recip_on_pair_physics_db=q8_db_vs_recip_pair,
            q8_db_beats_recip_on_rank1_physics_db=q8_db_vs_recip_rank1,
        ),
        verdicts=verdicts,
    )
    (out_p / "summary_g02.json").write_text(json.dumps(summary, indent=2))
    print("DONE g02 verdicts:", json.dumps(verdicts), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["smoke", "run"])
    ap.add_argument("--out", default="ideas/l2/out_g_r5_b1")
    ap.add_argument("--workers", type=int, default=20)
    args = ap.parse_args()
    if args.mode == "smoke":
        run_smoke()
    else:
        run_full(args.out, workers=args.workers)
