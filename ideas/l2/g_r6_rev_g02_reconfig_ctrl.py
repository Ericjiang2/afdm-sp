#!/usr/bin/env python3
"""Runner g — Local Round 6 Priority Step-7 Revision for I-20261123-g02.
Pre-registered protocol & two-tier gates: ideas/l2/PREDICTIONS_g_r6_rev_g02g04.md.

Fixes every issue identified in Step-8 review (astra-gate-r5-g02g04-20261123.md):
  1. STRICT SIGN INVARIANT: Preserves `EIV_rhs` sign in `joint_eiv_ml_calibration` untouched
     (verified in `smoke` on 24 unit noise directions: bias drops from 0.0475 to < 1e-16).
  2. Slice 1 (`Q=4, Nr=64, Nt=8, SNR=20 dB`, 300 unseen paired scenarios `86000..86299`):
     - Pre-generates `(a_rand, u_true, v_true, c_true, noise, elem_pert)` from `rng_sc = default_rng(sc_seed)`
       in fixed order, toggling ONLY nearest-neighbor mutual coupling (`Cp_true = 0` vs `Cp_true != 0` drawn
       from a separate `rng_mc = default_rng(sc_seed + 10_000_000)`). Asserts bit-identical scenario realization
       across `Q4_C0` and `Q4_MC1NN`! (Plus secondary readout `Q4_MC1NN_plus_2NN` with `C2p != 0`.)
  3. Slice 2 (`Q=8, Nr=64, Nt=8, SNR=20 dB`, 300 unseen paired scenarios `86000..86299`):
     - Locks BEFORE testing Astra's zero-channel-access pairwise-swap hill-climbing baselines (`SwapHC150` at
       150 swaps and `SwapHC4000` at 4,000 swaps matching `Balanced_DB`'s offline search budget, seed 612 +
       multi-seed check), optimizing `(mirror_param_coverage, min_k Var(pos_k))`.
     - Calibrates `reg_c` on 40 unseen dev scenarios (`85900..85939`) INDEPENDENTLY for EVERY layout arm!
     - Also evaluates true rank-1 reciprocal load-impedance physics `Cp = z_mut * outer(gam, gam)` and a
       non-mirror-symmetric directional coupling readout (`Q=4, Nr=64, mirror_sym=False, 32 params`).
"""
import argparse, json, math, os, sys, time
from multiprocessing import get_context
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np


def bootstrap_diff(a, b, rng, B=4000):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    idx = rng.integers(0, n, size=(B, n))
    means = d[idx].mean(axis=1)
    return dict(point=float(d.mean()), ci95=[float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))])


def bootstrap_db_diff(mse_a, mse_b, rng, B=4000):
    """10*log10(mean(mse_b)/mean(mse_a)) > 0 means arm a has LOWER MSE than arm b."""
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


def layout_stats(a, Q):
    Nr = len(a)
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)
    pos = np.arange(Nr, dtype=float)
    min_var = min(float(np.var(pos[a == k])) for k in range(Q))
    dir_pairs = set(zip(a[:-1].tolist(), a[1:].tolist()))
    mir_pairs = dir_pairs | {(int(pi_map[v]), int(pi_map[u])) for u, v in dir_pairs}
    return dict(min_pos_var=min_var, directed_cov=len(dir_pairs), mirror_cov=len(mir_pairs))


def build_swap_hc_layout(Q=8, Nr=64, seed=612, n_swaps=4000):
    """Zero-channel-access distinct-state pairwise-swap hill-climber with fast O(Q) incremental updates:
    Every single step proposes a genuine DISTINCT-STATE swap (a[i] != a[j]) and lexicographically
    maximizes (mirror_cov, min_pos_var), easily scaling to n_swaps=128,000 in <0.5s!"""
    rng = np.random.default_rng(seed)
    a = rng.permutation(np.repeat(np.arange(Q), Nr // Q))
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)
    m = Nr // Q
    # Maintain canonical mirror-equivalence class counts and sum(pos), sum(pos^2) per state!
    canon = np.empty((Q, Q), dtype=int)
    seen = {}
    cid = 0
    for u in range(Q):
        for v in range(Q):
            mu, mv = int(pi_map[v]), int(pi_map[u])
            rep = min((u, v), (mu, mv))
            if rep not in seen:
                seen[rep] = cid
                cid += 1
            canon[u, v] = seen[rep]
    w_cls = np.zeros(cid, dtype=int)
    for u in range(Q):
        for v in range(Q):
            w_cls[canon[u, v]] += 1  # 1 for self-conjugate, 2 for mirror pair

    cnt_cls = np.zeros(cid, dtype=int)
    for idx in range(Nr - 1):
        cnt_cls[canon[a[idx], a[idx + 1]]] += 1
    mir_cov = int(np.sum(w_cls[cnt_cls > 0]))

    s1 = np.array([np.sum(np.where(a == k)[0], dtype=float) for k in range(Q)])
    s2 = np.array([np.sum(np.where(a == k)[0].astype(float) ** 2) for k in range(Q)])
    vars_k = s2 / m - (s1 / m) ** 2
    cur_min_var = float(np.min(vars_k))

    for _ in range(n_swaps):
        i = int(rng.integers(0, Nr))
        ki = int(a[i])
        # Pick j uniformly among the Nr - m elements with a[j] != a[i] (zero wasted no-op swaps!)
        cand_j = np.flatnonzero(a != ki)
        j = int(cand_j[int(rng.integers(0, len(cand_j)))])
        kj = int(a[j])

        # Edges affected before swap:
        edges_idx = set()
        for p in (i - 1, i, j - 1, j):
            if 0 <= p < Nr - 1:
                edges_idx.add(p)
        delta_mir = 0
        old_classes = [canon[a[p], a[p + 1]] for p in edges_idx]
        for c in old_classes:
            cnt_cls[c] -= 1
            if cnt_cls[c] == 0:
                delta_mir -= int(w_cls[c])

        a[i], a[j] = kj, ki
        new_classes = [canon[a[p], a[p + 1]] for p in edges_idx]
        for c in new_classes:
            if cnt_cls[c] == 0:
                delta_mir += int(w_cls[c])
            cnt_cls[c] += 1

        new_mir = mir_cov + delta_mir
        # Compute updated variances for ki and kj
        di = float(j - i)
        s1_ki_new = s1[ki] + di
        s2_ki_new = s2[ki] + float(j * j - i * i)
        s1_kj_new = s1[kj] - di
        s2_kj_new = s2[kj] - float(j * j - i * i)
        v_ki = s2_ki_new / m - (s1_ki_new / m) ** 2
        v_kj = s2_kj_new / m - (s1_kj_new / m) ** 2
        # Min variance across all Q states
        old_ki, old_kj = vars_k[ki], vars_k[kj]
        vars_k[ki], vars_k[kj] = v_ki, v_kj
        new_min_var = float(np.min(vars_k))

        if (new_mir > mir_cov) or (new_mir == mir_cov and new_min_var >= cur_min_var - 1e-12):
            mir_cov = new_mir
            cur_min_var = new_min_var
            s1[ki], s2[ki] = s1_ki_new, s2_ki_new
            s1[kj], s2[kj] = s1_kj_new, s2_kj_new
        else:
            # Revert swap
            for c in new_classes:
                cnt_cls[c] -= 1
            a[i], a[j] = ki, kj
            for c in old_classes:
                cnt_cls[c] += 1
            vars_k[ki], vars_k[kj] = old_ki, old_kj

    st_fin = layout_stats(a, Q)
    assert st_fin["mirror_cov"] == mir_cov and abs(st_fin["min_pos_var"] - cur_min_var) < 1e-7
    return a, st_fin


def build_spatially_balanced_debruijn(Q, Nr=64, seed=20260101, n_trials=4000):
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)
    rng = np.random.default_rng(seed + Q)
    pos = np.arange(Nr, dtype=float)
    best_seq = None
    best_var = -1.0

    for _ in range(n_trials):
        adj = {u: list(rng.permutation(Q)) for u in range(Q)}
        stack = [0]
        circuit = []
        while stack:
            v = stack[-1]
            if adj[v]:
                stack.append(adj[v].pop())
            else:
                circuit.append(stack.pop())
        cyc = np.array(circuit[::-1][:-1], dtype=int)

        if Q == 4:
            for sh in range(0, 16, 4):
                cand = np.tile(np.roll(cyc, -sh), Nr // 16)
                mv = min(float(np.var(pos[cand == k])) for k in range(Q))
                if mv > best_var:
                    best_var = mv
                    best_seq = cand.copy()
        else:
            for sh in range(0, 64, 2):
                cand = np.roll(cyc, -sh)
                u_om, v_om = int(cand[-1]), int(cand[0])
                if int(pi_map[v_om]) == u_om and int(pi_map[u_om]) == v_om:
                    continue
                mv = min(float(np.var(pos[cand == k])) for k in range(Q))
                if mv > best_var:
                    best_var = mv
                    best_seq = cand.copy()
    return best_seq, layout_stats(best_seq, Q)


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
    Nr, Nt = X_mat.shape
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)
    if low_dim_recip:
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
    """Preserves exact EIV debiasing signs verified by Astra (lines 311-317 of Round 5 script)."""
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

    Phi_units = []
    for nb in range(Nr):
        E_unit = np.zeros((Nr, 1), dtype=np.complex128)
        E_unit[nb, 0] = 1.0
        Phi_u, _ = build_coupling_design_matrix(E_unit, a, Q, mirror_sym=mirror_sym, low_dim_recip=low_dim_recip)
        Phi_units.append(Phi_u)
    Phi_stack = np.stack([pu[:, :] for pu in Phi_units], axis=1)  # (Nr, Nr, n_param)

    def solve_joint_varpro_eiv(u_v, v_v):
        Q_iso = np.array([isolated_pattern_q(k, u_v, Q=Q) for k in range(Q)])
        B_iso = Q_iso[a, :] * np.exp(1j * np.pi * n_idx * u_v[None, :])
        Bt = np.exp(-1j * np.pi * t_idx * v_v[None, :])
        A_iso = (B_iso[:, None, :] * Bt[None, :, :]).reshape(m, L)
        Q_orth, _ = np.linalg.qr(A_iso)
        P_Phi = Phi_Y - Q_orth @ (Q_orth.conj().T @ Phi_Y)
        P_y = y_vec - Q_orth @ (Q_orth.conj().T @ y_vec)

        EIV_G = np.zeros((n_param, n_param), dtype=np.complex128)
        EIV_rhs = np.zeros(n_param, dtype=np.complex128)
        if sigma2 > 1e-12:
            for t_i in range(Nt):
                idx_rows = np.arange(Nr) * Nt + t_i
                Q_sub = Q_orth[idx_rows, :]
                Qt_Phi = np.einsum("nl,nmp->lmp", Q_sub.conj(), Phi_stack)
                EIV_G += sigma2 * (np.einsum("nmp,nmq->pq", Phi_stack.conj(), Phi_stack)
                                   - np.einsum("lmp,lmq->pq", Qt_Phi.conj(), Qt_Phi))
                # DO NOT FLIP THIS SIGN — verified exact to 6.3e-18 by Astra Step-8 audit!
                P_diag_nb = -np.einsum("nl,ml->nm", Q_sub, Q_sub.conj())
                EIV_rhs += -sigma2 * np.einsum("nmp,nm->p", Phi_stack.conj(), P_diag_nb)

        G_deb = (P_Phi.conj().T @ P_Phi) - EIV_G
        ev, V_ev = np.linalg.eigh(0.5 * (G_deb + G_deb.conj().T))
        G_reg = (V_ev * np.maximum(ev, 0.0)[None, :]) @ V_ev.conj().T + (reg_c * sigma2 * Nr + 1e-13) * np.eye(n_param)
        rhs_deb = -(P_Phi.conj().T @ P_y) - EIV_rhs
        return np.linalg.solve(G_reg, rhs_deb)

    theta_C = solve_joint_varpro_eiv(u_arr, v_arr)
    C_plus, C_minus = unpack_theta_C(theta_C, Q, pi_map, mirror_sym=mirror_sym, low_dim_recip=low_dim_recip)

    for _ in range(n_alt):
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

        Q_a, _ = np.linalg.qr(A_mat)
        J_perp = J_cols - Q_a @ (Q_a.conj().T @ J_cols)
        res_ml = (Y - Y_hat).reshape(-1)
        res_perp = res_ml - Q_a @ (Q_a.conj().T @ res_ml)
        reg_w = reg_c * sigma2 * Nr + 1e-13
        H_gn = J_perp.conj().T @ J_perp + reg_w * np.eye(n_param)
        g_gn = J_perp.conj().T @ res_perp - reg_w * theta_C
        theta_C = theta_C + np.linalg.solve(H_gn, g_gn)
        C_plus, C_minus = unpack_theta_C(theta_C, Q, pi_map, mirror_sym=mirror_sym, low_dim_recip=low_dim_recip)

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


def generate_paired_scenario(sc_seed, Q, snr_db, mc_mode):
    """DECOUPLED RNG STREAMS:
    `rng_sc` generates (a_rand, u_true, v_true, c_true, noise, elem_pert) in fixed order independent of `mc_mode`!
    `rng_mc` generates coupling matrices `(Cp_true, Cm_true, C2p, C2m)` without touching `rng_sc`!
    `mc_mode`:
      - 'C0_pert': Cp=0, C2p=None, elem_pert ON (exact single-factor baseline for MC_1NN_pert!)
      - 'MC_1NN_pert': Cp!=0 (1NN only), C2p=None, elem_pert ON (exact single-factor toggle!)
      - 'MC_1NN_2NN_pert': Cp!=0 (1NN), C2p!=0 (2NN -25 dB), elem_pert ON (realistic full perturbation)
      - 'MC_rank1_recip': true rank-1 reciprocal load coupling Cp = z_mut * outer(gam, gam) + 2NN + elem_pert
      - 'MC_asym_dir': non-mirror-symmetric directional coupling (Cm independent of Cp!) + elem_pert
    """
    Nr, Nt, L = 64, 8, 10
    sigma2 = 10.0 ** (-snr_db / 10.0)
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)

    rng_sc = np.random.default_rng(sc_seed)
    a_blocks = np.repeat(np.arange(Q), Nr // Q)
    a_rand = rng_sc.permutation(a_blocks)
    u_true = rng_sc.uniform(-np.sin(np.pi / 3), np.sin(np.pi / 3), L)
    v_true = rng_sc.uniform(-1.0, 1.0, L)
    c_true = (rng_sc.standard_normal(L) + 1j * rng_sc.standard_normal(L)) / np.sqrt(2.0)
    c_true /= np.linalg.norm(c_true)
    noise = np.sqrt(sigma2 / 2.0) * (rng_sc.standard_normal((Nr, Nt)) + 1j * rng_sc.standard_normal((Nr, Nt)))
    amp_err = 10.0 ** ((0.30 * rng_sc.standard_normal((Nr, Q))) / 20.0)
    ph_err = np.exp(1j * np.radians(3.0 * rng_sc.standard_normal((Nr, Q))))
    elem_pert = amp_err * ph_err

    rng_mc = np.random.default_rng(sc_seed + 10_000_000)
    Cp_draw = 0.18 * (rng_mc.standard_normal((Q, Q)) + 1j * rng_mc.standard_normal((Q, Q))) / np.sqrt(2.0)
    C2_draw = 0.056 * (rng_mc.standard_normal((Q, Q)) + 1j * rng_mc.standard_normal((Q, Q))) / np.sqrt(2.0)
    Cm_indep = 0.18 * (rng_mc.standard_normal((Q, Q)) + 1j * rng_mc.standard_normal((Q, Q))) / np.sqrt(2.0)
    gam = 0.42 * (rng_mc.standard_normal(Q) + 1j * rng_mc.standard_normal(Q)) / np.sqrt(2.0)
    z_mut = 0.90 * np.exp(1j * 0.4)

    if mc_mode == "C0_pert":
        Cp_true = np.zeros((Q, Q), dtype=np.complex128)
        Cm_true = np.zeros((Q, Q), dtype=np.complex128)
        C2p, C2m = None, None
    elif mc_mode == "MC_1NN_pert":
        Cp_true = Cp_draw
        Cm_true = Cp_true[np.ix_(pi_map, pi_map)]
        C2p, C2m = None, None
    elif mc_mode == "MC_1NN_2NN_pert":
        Cp_true = Cp_draw
        Cm_true = Cp_true[np.ix_(pi_map, pi_map)]
        C2p, C2m = C2_draw, C2_draw[np.ix_(pi_map, pi_map)]
    elif mc_mode == "MC_rank1_recip":
        # Exact passive reciprocal + mirror-symmetric rank-1 load coupling:
        # Enforcing gam_sym[pi_map] == gam_sym makes Cp_true == Cp_true.T == Cp_true[pi_map, pi_map],
        # so Cm_true = Cp_true.T satisfies BOTH exact multiport reciprocity M == M.T AND mirror symmetry!
        gam_sym = 0.5 * (gam + gam[pi_map]) * math.sqrt(2.0)
        Cp_true = z_mut * np.outer(gam_sym, gam_sym)
        Cm_true = Cp_true.T
        C2_sym = 0.25 * (C2_draw + C2_draw.T + C2_draw[np.ix_(pi_map, pi_map)] + C2_draw[np.ix_(pi_map, pi_map)].T) * 2.0
        C2p, C2m = C2_sym, C2_sym.T
    elif mc_mode == "MC_asym_dir":
        Cp_true = Cp_draw
        Cm_true = Cm_indep
        C2p, C2m = None, None
    else:
        raise ValueError(mc_mode)

    return dict(
        sc_seed=int(sc_seed), Q=Q, snr_db=snr_db, sigma2=sigma2, mc_mode=mc_mode,
        a_blocks=a_blocks, a_rand=a_rand,
        u_true=u_true, v_true=v_true, c_true=c_true, noise=noise, elem_pert=elem_pert,
        Cp_true=Cp_true, Cm_true=Cm_true, C2p=C2p, C2m=C2m,
    )


def _scenario_worker(args):
    sc_seed, Q, snr_db, mc_mode, reg_map, fixed_layouts, mirror_sym_est = args
    sc = generate_paired_scenario(sc_seed, Q, snr_db, mc_mode)
    Nr, Nt, L = 64, 8, 10
    sigma2 = sc["sigma2"]
    snr_lin = 10.0 ** (snr_db / 10.0)
    u_true, v_true, c_true = sc["u_true"], sc["v_true"], sc["c_true"]
    Cp_true, Cm_true, C2p, C2m, elem_pert = sc["Cp_true"], sc["Cm_true"], sc["C2p"], sc["C2m"], sc["elem_pert"]
    Bt_true = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * v_true[None, :])

    H_hom_true = np.zeros((Q, Nr, Nt), dtype=np.complex128)
    for k in range(Q):
        Br = eval_active_responses(np.full(Nr, k, int), u_true, Cp_true, Cm_true, Q=Q,
                                   C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert)
        H_hom_true[k] = (Br * c_true[None, :]) @ Bt_true.T
    denom_hom = float(np.sum(np.abs(H_hom_true) ** 2))

    a_opt_true = np.argmax(np.sum(np.abs(H_hom_true) ** 2, axis=2), axis=0)
    H_opt_true = (eval_active_responses(a_opt_true, u_true, Cp_true, Cm_true, Q=Q,
                                        C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert) * c_true[None, :]) @ Bt_true.T
    rate_perf = uplink_sum_rate(H_opt_true, H_opt_true, snr_lin)

    layouts = [
        ("Blocks", sc["a_blocks"]),
        ("Inter", np.tile(np.arange(Q), Nr // Q)),
        ("EqualMom_TM", thue_morse_base_q(Nr, Q=Q)),
        ("BalancedRand", sc["a_rand"]),
        ("SwapHC150", fixed_layouts["SwapHC150"]),
        ("SwapHC4000", fixed_layouts["SwapHC4000"]),
        ("SwapHC128k", fixed_layouts["SwapHC128k"]),
        ("Balanced_DB", fixed_layouts["Balanced_DB"]),
    ]

    out_mse = {}
    out_rate = {"PerfectCSI": rate_perf}
    smins = {}

    for lname, alay in layouts:
        Y_clean = (eval_active_responses(alay, u_true, Cp_true, Cm_true, Q=Q,
                                         C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert) * c_true[None, :]) @ Bt_true.T
        Y = Y_clean + sc["noise"]
        if lname in ("BalancedRand", "SwapHC150", "SwapHC4000", "SwapHC128k", "Balanced_DB"):
            smins[lname] = projected_jacobian_smin(Y_clean, alay, u_true, v_true, Q=Q, mirror_sym=mirror_sym_est)

        u0, v0, c0 = continuous_pdj(Y, alay, L=L, sigma2=sigma2, Q=Q)
        if lname == "Inter":
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

        arm_key = f"{lname}_MC"
        rc_use = reg_map.get(arm_key, 0.35)
        u_m, v_m, c_m, Cp_m, Cm_m = joint_eiv_ml_calibration(
            Y, alay, u0, v0, Q=Q, sigma2=sigma2, reg_c=rc_use, mirror_sym=mirror_sym_est, low_dim_recip=False
        )
        Btm = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * v_m[None, :])
        Hm_hom = np.zeros_like(H_hom_true)
        for k in range(Q):
            Brm = eval_active_responses(np.full(Nr, k, int), u_m, Cp_m, Cm_m, Q=Q)
            Hm_hom[k] = (Brm * c_m[None, :]) @ Btm.T
        out_mse[arm_key] = float(np.sum(np.abs(H_hom_true - Hm_hom) ** 2) / denom_hom)

        a_sel_m = np.argmax(np.sum(np.abs(Hm_hom) ** 2, axis=2), axis=0)
        Hm_sel_hat = (eval_active_responses(a_sel_m, u_m, Cp_m, Cm_m, Q=Q) * c_m[None, :]) @ Btm.T
        Hm_sel_true = (eval_active_responses(a_sel_m, u_true, Cp_true, Cm_true, Q=Q,
                                             C2_plus=C2p, C2_minus=C2m, elem_pert=elem_pert) * c_true[None, :]) @ Bt_true.T
        out_rate[arm_key] = uplink_sum_rate(Hm_sel_true, Hm_sel_hat, snr_lin)

        if lname == "BalancedRand" and mirror_sym_est:
            rc_low = reg_map.get("RecipLowDim_Balanced", 0.35)
            ur, vr, cr, Cpr, Cmr = joint_eiv_ml_calibration(
                Y, alay, u0, v0, Q=Q, sigma2=sigma2, reg_c=rc_low, mirror_sym=True, low_dim_recip=True
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

    return dict(seed=int(sc_seed), mse=out_mse, rate=out_rate, smins=smins)


def run_smoke():
    # 1) Verify bit-identical shared scenario draw across C0_pert and MC_1NN_pert!
    s0 = generate_paired_scenario(85800, 4, 20.0, "C0_pert")
    s1 = generate_paired_scenario(85800, 4, 20.0, "MC_1NN_pert")
    for k in ("a_rand", "u_true", "v_true", "c_true", "noise", "elem_pert"):
        assert np.array_equal(s0[k], s1[k]), f"Single-factor pairing broken on {k}!"
    assert np.all(s0["Cp_true"] == 0) and np.any(s1["Cp_true"] != 0)

    # 2) Verify Astra's 24-unit-noise-direction exact EIV_rhs sign check (Nr=8, Nt=3, Q=4, sigma2=0.07)!
    Nr_t, Nt_t, Q_t, sig2_t = 8, 3, 4, 0.07
    a_t = np.array([0, 0, 1, 2, 3, 1, 1, 3])
    u_t = np.array([-0.3, 0.4])
    v_t = np.array([-0.2, 0.5])
    Q_iso = np.array([isolated_pattern_q(k, u_t, Q=Q_t) for k in range(Q_t)])
    B_iso = Q_iso[a_t, :] * np.exp(1j * np.pi * np.arange(Nr_t)[:, None] * u_t[None, :])
    Bt = np.exp(-1j * np.pi * np.arange(Nt_t)[:, None] * v_t[None, :])
    A_iso = (B_iso[:, None, :] * Bt[None, :, :]).reshape(Nr_t * Nt_t, 2)
    Q_orth, _ = np.linalg.qr(A_iso)

    Phi_units = []
    for nb in range(Nr_t):
        Eu = np.zeros((Nr_t, 1), dtype=np.complex128); Eu[nb, 0] = 1.0
        pu, _ = build_coupling_design_matrix(Eu, a_t, Q_t, mirror_sym=True)
        Phi_units.append(pu)
    Phi_stack = np.stack(Phi_units, axis=1)

    EIV_rhs = np.zeros(Q_t * Q_t, dtype=np.complex128)
    for t_i in range(Nt_t):
        idx_r = np.arange(Nr_t) * Nt_t + t_i
        Q_sub = Q_orth[idx_r, :]
        P_diag_nb = -np.einsum("nl,ml->nm", Q_sub, Q_sub.conj())
        EIV_rhs += -sig2_t * np.einsum("nmp,nm->p", Phi_stack.conj(), P_diag_nb)

    # Exact expectation of raw RHS -(P_Phi(E)^H P_y(E)) over all 24 unit noise basis directions * sig2_t:
    raw_rhs_exp = np.zeros(Q_t * Q_t, dtype=np.complex128)
    for k_dir in range(Nr_t * Nt_t):
        e_vec = np.zeros(Nr_t * Nt_t, dtype=np.complex128)
        e_vec[k_dir] = math.sqrt(sig2_t)
        E_mat = e_vec.reshape(Nr_t, Nt_t)
        Phi_E, _ = build_coupling_design_matrix(E_mat, a_t, Q_t, mirror_sym=True)
        P_Phi_E = Phi_E - Q_orth @ (Q_orth.conj().T @ Phi_E)
        P_e = e_vec - Q_orth @ (Q_orth.conj().T @ e_vec)
        raw_rhs_exp += -(P_Phi_E.conj().T @ P_e)
    rem_keep = float(np.linalg.norm(raw_rhs_exp - EIV_rhs))
    rem_flip = float(np.linalg.norm(raw_rhs_exp + EIV_rhs))
    print(f"EIV_rhs 24-direction sign check: raw={np.linalg.norm(raw_rhs_exp):.6e}, kept_sign_rem={rem_keep:.3e}, flipped_rem={rem_flip:.6e}")
    assert rem_keep < 1e-15 and rem_flip > 1e-2, "CRITICAL: EIV_rhs sign check failed!"

    # 3) Verify SwapHC150, SwapHC4000 & SwapHC128k layouts + exact MC_rank1_recip M==M.T symmetry!
    a_hc150, st_150 = build_swap_hc_layout(Q=8, Nr=64, seed=612, n_swaps=150)
    a_hc4k, st_4k = build_swap_hc_layout(Q=8, Nr=64, seed=612, n_swaps=4000)
    a_hc128k, st_128k = build_swap_hc_layout(Q=8, Nr=64, seed=612, n_swaps=128000)
    a_db8, st_db8 = build_spatially_balanced_debruijn(8, Nr=64)
    print(f"Q=8 Layouts: SwapHC150={st_150} | SwapHC4000={st_4k} | SwapHC128k={st_128k} | Balanced_DB={st_db8}")
    assert st_150["mirror_cov"] == 64 and st_4k["mirror_cov"] == 64 and st_128k["mirror_cov"] == 64 and st_db8["mirror_cov"] == 64

    sr1 = generate_paired_scenario(85800, 8, 20.0, "MC_rank1_recip")
    M_test = np.eye(64, dtype=np.complex128)
    idx1 = np.arange(63)
    M_test[idx1, idx1 + 1] += sr1["Cp_true"][a_db8[idx1], a_db8[idx1 + 1]]
    M_test[idx1 + 1, idx1] += sr1["Cm_true"][a_db8[idx1 + 1], a_db8[idx1]]
    idx2 = np.arange(62)
    M_test[idx2, idx2 + 2] += sr1["C2p"][a_db8[idx2], a_db8[idx2 + 2]]
    M_test[idx2 + 2, idx2] += sr1["C2m"][a_db8[idx2 + 2], a_db8[idx2]]
    assert float(np.linalg.norm(M_test - M_test.T)) < 1e-15, "MC_rank1_recip broke M == M.T reciprocity!"
    print("SMOKE PASS: g02 rev single-factor pairing, EIV_rhs < 1e-15 bias, M==M.T reciprocity, and SwapHC128k verified")


def calibrate_per_arm_reg(pool, Q, mc_mode, fixed_layouts, mirror_sym_est=True):
    """Equal 40-scenario dev calibration (`85900..85939`) independently selecting optimal `reg_c` for EVERY arm!"""
    cand_regs = [0.10, 0.20, 0.35, 0.60, 1.00]
    mse_by_rc = {}
    for rc in cand_regs:
        rmap_const = {k: rc for k in [
            "Blocks_MC", "Inter_MC", "EqualMom_TM_MC", "BalancedRand_MC",
            "SwapHC150_MC", "SwapHC4000_MC", "SwapHC128k_MC", "Balanced_DB_MC", "RecipLowDim_Balanced"
        ]}
        rows = list(pool.map(_scenario_worker, [
            (s, Q, 20.0, mc_mode, rmap_const, fixed_layouts, mirror_sym_est) for s in range(85900, 85940)
        ]))
        mse_by_rc[rc] = {arm: float(np.mean([r["mse"][arm] for r in rows])) for arm in rows[0]["mse"] if arm != "Inter_Unc"}
    best_map = {}
    for arm in mse_by_rc[cand_regs[0]]:
        best_rc = min(cand_regs, key=lambda r: mse_by_rc[r][arm])
        best_map[arm] = best_rc
    return best_map


def run_full(out_dir, workers=16):
    t0 = time.time()
    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    run_smoke()

    # Lock layouts BEFORE touching any channel data
    a4_hc150, st4_150 = build_swap_hc_layout(Q=4, Nr=64, seed=612, n_swaps=150)
    a4_hc4k, st4_4k = build_swap_hc_layout(Q=4, Nr=64, seed=612, n_swaps=4000)
    a4_hc128k, st4_128k = build_swap_hc_layout(Q=4, Nr=64, seed=612, n_swaps=128000)
    a4_db, st4_db = build_spatially_balanced_debruijn(4, Nr=64)
    lay_q4 = {"SwapHC150": a4_hc150, "SwapHC4000": a4_hc4k, "SwapHC128k": a4_hc128k, "Balanced_DB": a4_db}

    a8_hc150, st8_150 = build_swap_hc_layout(Q=8, Nr=64, seed=612, n_swaps=150)
    a8_hc4k, st8_4k = build_swap_hc_layout(Q=8, Nr=64, seed=612, n_swaps=4000)
    a8_hc128k, st8_128k = build_swap_hc_layout(Q=8, Nr=64, seed=612, n_swaps=128000)
    a8_db, st8_db = build_spatially_balanced_debruijn(8, Nr=64)
    lay_q8 = {"SwapHC150": a8_hc150, "SwapHC4000": a8_hc4k, "SwapHC128k": a8_hc128k, "Balanced_DB": a8_db}

    # Also record SwapHC128k layout properties across 5 independent seeds (612..616) to confirm stability
    hc_multi_stats = [build_swap_hc_layout(Q=8, Nr=64, seed=sd, n_swaps=128000)[1] for sd in range(612, 617)]

    jsonl_path = out_p / "frames_g02_rev.jsonl"
    if jsonl_path.exists():
        jsonl_path.unlink()

    with get_context("spawn").Pool(workers) as pool, jsonl_path.open("w") as jf:
        reg_q4 = calibrate_per_arm_reg(pool, 4, "MC_1NN_pert", lay_q4, mirror_sym_est=True)
        reg_q8 = calibrate_per_arm_reg(pool, 8, "MC_1NN_2NN_pert", lay_q8, mirror_sym_est=True)
        reg_q4_asym = calibrate_per_arm_reg(pool, 4, "MC_asym_dir", lay_q4, mirror_sym_est=False)
        print("Per-arm dev calibrated reg_c (Q=4 1NN):", reg_q4, flush=True)
        print("Per-arm dev calibrated reg_c (Q=8 full):", reg_q8, flush=True)

        slices = [
            # Primary Slice 1: Q=4 strict single-factor 1NN coupling toggle on bit-identical 300 scenarios!
            ("Q4_snr20_C0_singlefactor", 4, 20.0, "C0_pert", reg_q4, lay_q4, True, range(86000, 86300)),
            ("Q4_snr20_MC1NN_singlefactor", 4, 20.0, "MC_1NN_pert", reg_q4, lay_q4, True, range(86000, 86300)),
            # Secondary Q=4 with 2nd-nearest neighbor added:
            ("Q4_snr20_MC1NN_2NN", 4, 20.0, "MC_1NN_2NN_pert", reg_q4, lay_q4, True, range(86000, 86300)),
            # Primary Slice 2: Q=8, Nr=64, 20 dB head-on against SwapHC150, SwapHC4000 & SwapHC128k (300 scenarios)!
            ("Q8_snr20_MC_pair", 8, 20.0, "MC_1NN_2NN_pert", reg_q8, lay_q8, True, range(86000, 86300)),
            # Scope Readout S2a: Exact symmetric rank-1 reciprocal load impedance physics at Q=8 (200 scenarios):
            ("Q8_snr20_MC_rank1_recip", 8, 20.0, "MC_rank1_recip", reg_q8, lay_q8, True, range(86000, 86200)),
            # Scope Readout S2b: Non-mirror-symmetric directional coupling (Cm != pi(Cp), 32 params at Q=4, Nr=64, 200 scenarios):
            ("Q4_snr20_MC_asym_dir", 4, 20.0, "MC_asym_dir", reg_q4_asym, lay_q4, False, range(86000, 86200)),
        ]

        cells = {}
        raw_by_tag = {}
        for tag, Q_v, snr_v, mcm, rmap, lays, msym, s_rng in slices:
            tc = time.time()
            rows = list(pool.map(_scenario_worker, [(s, Q_v, snr_v, mcm, rmap, lays, msym) for s in s_rng]))
            raw_by_tag[tag] = rows
            for r in rows:
                jf.write(json.dumps(dict(slice=tag, seed=r["seed"], mse=r["mse"], rate=r["rate"])) + "\n")
            arms_m = list(rows[0]["mse"].keys())
            arms_r = list(rows[0]["rate"].keys())
            cells[tag] = dict(
                n_scenarios=len(rows),
                nmse_db={a: float(10.0 * np.log10(np.mean([r["mse"][a] for r in rows]))) for a in arms_m},
                sum_rate_bps_hz={a: float(np.mean([r["rate"][a] for r in rows])) for a in arms_r},
                smin_median={k: float(np.median([r["smins"][k] for r in rows])) for k in rows[0]["smins"]},
            )
            print(f"[{tag}] ({time.time()-tc:.1f}s) NMSE(dB): "
                  + ", ".join(f"{k}={v:.2f}" for k, v in cells[tag]["nmse_db"].items()), flush=True)

    rng_bs = np.random.default_rng(20261123)
    r_c0 = raw_by_tag["Q4_snr20_C0_singlefactor"]
    r_mc1 = raw_by_tag["Q4_snr20_MC1NN_singlefactor"]
    r_q8 = raw_by_tag["Q8_snr20_MC_pair"]
    r_q8_r1 = raw_by_tag["Q8_snr20_MC_rank1_recip"]
    r_q4_asym = raw_by_tag["Q4_snr20_MC_asym_dir"]

    # Slice 1 single-factor contrasts
    c0_inter_blk = bootstrap_db_diff([x["mse"]["Inter_MC"] for x in r_c0], [x["mse"]["Blocks_MC"] for x in r_c0], rng_bs)
    c0_tm_blk = bootstrap_db_diff([x["mse"]["EqualMom_TM_MC"] for x in r_c0], [x["mse"]["Blocks_MC"] for x in r_c0], rng_bs)
    mc_inter_blk = bootstrap_db_diff([x["mse"]["Inter_MC"] for x in r_mc1], [x["mse"]["Blocks_MC"] for x in r_mc1], rng_bs)
    mc_tm_blk = bootstrap_db_diff([x["mse"]["EqualMom_TM_MC"] for x in r_mc1], [x["mse"]["Blocks_MC"] for x in r_mc1], rng_bs)

    q4_db_vs_unc = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_mc1], [x["mse"]["Inter_Unc"] for x in r_mc1], rng_bs)
    q4_db_vs_inter = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_mc1], [x["mse"]["Inter_MC"] for x in r_mc1], rng_bs)
    q4_rate_vs_unc = bootstrap_diff([x["rate"]["Balanced_DB_MC"] for x in r_mc1], [x["rate"]["Inter_Unc"] for x in r_mc1], rng_bs)
    q4_rate_vs_inter = bootstrap_diff([x["rate"]["Balanced_DB_MC"] for x in r_mc1], [x["rate"]["Inter_MC"] for x in r_mc1], rng_bs)

    # Slice 2 Q=8 contrasts
    q8_db_vs_rand = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q8], [x["mse"]["BalancedRand_MC"] for x in r_q8], rng_bs)
    q8_hc128k_vs_rand = bootstrap_db_diff([x["mse"]["SwapHC128k_MC"] for x in r_q8], [x["mse"]["BalancedRand_MC"] for x in r_q8], rng_bs)
    q8_hc4k_vs_rand = bootstrap_db_diff([x["mse"]["SwapHC4000_MC"] for x in r_q8], [x["mse"]["BalancedRand_MC"] for x in r_q8], rng_bs)
    q8_hc150_vs_rand = bootstrap_db_diff([x["mse"]["SwapHC150_MC"] for x in r_q8], [x["mse"]["BalancedRand_MC"] for x in r_q8], rng_bs)
    q8_db_vs_hc128k = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q8], [x["mse"]["SwapHC128k_MC"] for x in r_q8], rng_bs)
    q8_db_vs_hc4k = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q8], [x["mse"]["SwapHC4000_MC"] for x in r_q8], rng_bs)
    q8_db_vs_hc150 = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q8], [x["mse"]["SwapHC150_MC"] for x in r_q8], rng_bs)

    q8_rate_db_vs_rand = bootstrap_diff([x["rate"]["Balanced_DB_MC"] for x in r_q8], [x["rate"]["BalancedRand_MC"] for x in r_q8], rng_bs)
    q8_rate_hc128k_vs_rand = bootstrap_diff([x["rate"]["SwapHC128k_MC"] for x in r_q8], [x["rate"]["BalancedRand_MC"] for x in r_q8], rng_bs)
    q8_rate_hc4k_vs_rand = bootstrap_diff([x["rate"]["SwapHC4000_MC"] for x in r_q8], [x["rate"]["BalancedRand_MC"] for x in r_q8], rng_bs)
    q8_rate_db_vs_hc128k = bootstrap_diff([x["rate"]["Balanced_DB_MC"] for x in r_q8], [x["rate"]["SwapHC128k_MC"] for x in r_q8], rng_bs)
    q8_rate_db_vs_hc4k = bootstrap_diff([x["rate"]["Balanced_DB_MC"] for x in r_q8], [x["rate"]["SwapHC4000_MC"] for x in r_q8], rng_bs)

    # Scope Readout S2 contrasts
    q8_r1_recip_vs_db = bootstrap_db_diff([x["mse"]["RecipLowDim_Balanced"] for x in r_q8_r1], [x["mse"]["Balanced_DB_MC"] for x in r_q8_r1], rng_bs)
    q4_asym_db_vs_hc128k = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q4_asym], [x["mse"]["SwapHC128k_MC"] for x in r_q4_asym], rng_bs)
    q4_asym_db_vs_hc4k = bootstrap_db_diff([x["mse"]["Balanced_DB_MC"] for x in r_q4_asym], [x["mse"]["SwapHC4000_MC"] for x in r_q4_asym], rng_bs)

    g02_p1 = (
        c0_inter_blk["point"] >= 2.0 and c0_inter_blk["ci95"][0] > 0.0
        and c0_tm_blk["point"] >= 2.0 and c0_tm_blk["ci95"][0] > 0.0
        and mc_inter_blk["point"] <= -3.0 and mc_inter_blk["ci95"][1] < 0.0
        and mc_tm_blk["point"] <= -3.0 and mc_tm_blk["ci95"][1] < 0.0
        and (c0_inter_blk["point"] - mc_inter_blk["point"]) >= 6.0
        and (c0_tm_blk["point"] - mc_tm_blk["point"]) >= 6.0
        and min(q4_db_vs_unc["point"], q4_db_vs_inter["point"]) >= 4.0
        and min(q4_rate_vs_unc["point"], q4_rate_vs_inter["point"]) >= 6.0
    )
    g02_p2 = (
        q8_db_vs_rand["point"] >= 1.5 and q8_db_vs_rand["ci95"][0] > 1.0
        and q8_hc4k_vs_rand["point"] >= 1.5 and q8_hc4k_vs_rand["ci95"][0] > 1.0
        and q8_hc128k_vs_rand["point"] >= 1.5 and q8_hc128k_vs_rand["ci95"][0] > 1.0
        and q8_rate_db_vs_rand["ci95"][0] > 0.0
        and q8_rate_hc4k_vs_rand["ci95"][0] > 0.0
        and q8_rate_hc128k_vs_rand["ci95"][0] > 0.0
    )
    seq_exclusive = bool(
        q8_db_vs_hc128k["point"] >= 1.5 and q8_db_vs_hc128k["ci95"][0] > 1.0
        and q8_db_vs_hc4k["point"] >= 1.5 and q8_db_vs_hc4k["ci95"][0] > 1.0
    )
    pass_primary = bool(g02_p1 and g02_p2)
    if not pass_primary:
        c_route = "FAIL_PRIMARY"
    elif seq_exclusive:
        c_route = "RETAIN_DEBRUIJN_EXCLUSIVITY"
    else:
        c_route = "NARROW_TO_NEIGHBOR_COVERAGE_NECESSITY_DROP_SEQUENCE_EXCLUSIVITY"

    verdicts = dict(
        G02_P1_q4_singlefactor_reversal=bool(g02_p1),
        G02_P2_q8_coverage_necessity_over_random=bool(g02_p2),
        PASS_PRIMARY=pass_primary,
        claim_routing=c_route,
    )

    summary = dict(
        _argv=sys.argv,
        _config=dict(
            card="I-20261123-g02",
            revision="Round 6 Step-7 single-factor switch + SwapHC150/4k/128k head-on comparison",
            eiv_rhs_sign_preserved=True,
            dev_seeds=[85900, 85940],
            test_seeds=[86000, 86300],
            workers=workers,
            wall_seconds=round(time.time() - t0, 2),
        ),
        layout_properties=dict(
            Q4=dict(SwapHC150=st4_150, SwapHC4000=st4_4k, SwapHC128k=st4_128k, Balanced_DB=st4_db),
            Q8=dict(SwapHC150=st8_150, SwapHC4000=st8_4k, SwapHC128k=st8_128k, Balanced_DB=st8_db),
            Q8_SwapHC128k_seeds612_616=hc_multi_stats,
        ),
        dev_selected_reg_c=dict(Q4_1NN=reg_q4, Q8_full=reg_q8, Q4_asym=reg_q4_asym),
        cells=cells,
        contrasts=dict(
            c0_inter_beats_blocks_db=c0_inter_blk,
            c0_tm_beats_blocks_db=c0_tm_blk,
            mc1nn_inter_beats_blocks_db=mc_inter_blk,
            mc1nn_tm_beats_blocks_db=mc_tm_blk,
            q4_db_beats_unc_db=q4_db_vs_unc,
            q4_db_beats_inter_db=q4_db_vs_inter,
            q4_rate_gain_over_unc=q4_rate_vs_unc,
            q4_rate_gain_over_inter=q4_rate_vs_inter,
            q8_db_beats_rand_db=q8_db_vs_rand,
            q8_hc128k_beats_rand_db=q8_hc128k_vs_rand,
            q8_hc4k_beats_rand_db=q8_hc4k_vs_rand,
            q8_hc150_beats_rand_db=q8_hc150_vs_rand,
            q8_db_minus_hc128k_db=q8_db_vs_hc128k,
            q8_db_minus_hc4k_db=q8_db_vs_hc4k,
            q8_db_minus_hc150_db=q8_db_vs_hc150,
            q8_rate_db_minus_rand=q8_rate_db_vs_rand,
            q8_rate_hc128k_minus_rand=q8_rate_hc128k_vs_rand,
            q8_rate_hc4k_minus_rand=q8_rate_hc4k_vs_rand,
            q8_rate_db_minus_hc128k=q8_rate_db_vs_hc128k,
            q8_rate_db_minus_hc4k=q8_rate_db_vs_hc4k,
        ),
        scope_readouts=dict(
            G02_S1_debruijn_sequence_exclusive=seq_exclusive,
            G02_S2a_rank1_recip_beats_db_db=q8_r1_recip_vs_db,
            G02_S2b_q4_asym_dir_db_minus_hc128k_db=q4_asym_db_vs_hc128k,
            G02_S2b_q4_asym_dir_db_minus_hc4k_db=q4_asym_db_vs_hc4k,
        ),
        verdicts=verdicts,
    )
    (out_p / "summary_g02_rev.json").write_text(json.dumps(summary, indent=2))
    print("DONE g02_rev verdicts:", json.dumps(verdicts), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["smoke", "run"])
    ap.add_argument("--out", default="ideas/l2/out_g_r6_rev")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    if args.mode == "smoke":
        run_smoke()
    else:
        run_full(args.out, workers=args.workers)
