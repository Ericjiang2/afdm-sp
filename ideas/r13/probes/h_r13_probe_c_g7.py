import os
import sys
import time
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h_r13_stageA_common import (
    build_daft_matrices, idaft_col, td_path_matrix, daft_path_matrix,
    build_wideband_user_channel, ula_steering, qpsk_alphabet, nearest_symbol_ser,
)
from h_r13_stageA_g5_g7 import solve_tang_slp_dual_qp


def eval_g7_cpi_fullmap(S_af_cpi, H_users_af, d_cpi, noise_cpi, lc1, lc2, c1, a_tar, P_blk, seed_r):
    Q, N, Nt = S_af_cpi.shape
    K = len(H_users_af)
    alph = qpsk_alphabet()
    sers = []
    X_td = np.zeros_like(S_af_cpi)
    for q in range(Q):
        sv = S_af_cpi[q].reshape(N * Nt)
        sv = sv * np.sqrt(P_blk / max(float(np.sum(np.abs(sv) ** 2)), 1e-15))
        X_td[q] = idaft_col(sv.reshape(N, Nt), lc1, lc2)
        for k in range(K):
            zk = H_users_af[k] @ sv + noise_cpi[q, k]
            sers.append(nearest_symbol_ser(zk, d_cpi[q, k], alph))

    u_tar = np.einsum("qni,i->qn", X_td, np.conj(a_tar))  # (Q, N)
    ell_s, nu_s = 1, 0.33   # non-zero fractional Doppler on +23 dB strong target (exposes h01 fake-peak trap!)
    ell_w, nu_w = 4, 0.61
    T_s = td_path_matrix(N, c1, ell_s, nu_s)
    T_w = td_path_matrix(N, c1, ell_w, nu_w)
    q_idx = np.arange(Q, dtype=np.float64)
    b_s = np.exp(1j * 2.0 * np.pi * nu_s * 1.15 * q_idx)
    b_w = np.exp(1j * 2.0 * np.pi * nu_w * 1.15 * q_idx)
    echo_s = (10.0 ** (23.0 / 20.0)) * b_s[:, None] * (u_tar @ T_s.T)
    echo_w = 1.0 * b_w[:, None] * (u_tar @ T_w.T)
    rng_r = np.random.default_rng(seed_r)
    Y_rad = echo_s + echo_w + np.sqrt(0.05 / 2.0) * (rng_r.standard_normal((Q, N)) + 1j * rng_r.standard_normal((Q, N)))

    phi_w = b_w[:, None] * (u_tar @ T_w.T)
    sig_num = abs(np.sum(np.conj(phi_w) * echo_w)) ** 2
    leak_s = abs(np.sum(np.conj(phi_w) * echo_s)) ** 2
    wsinr = 10.0 * np.log10(max(sig_num / max(leak_s + 0.05 * float(np.sum(np.abs(phi_w) ** 2)), 1e-15), 1e-15))

    # Full-map blind search across non-strong range gates eg != ell_s (near-range clutter gate blanking eg != ell_s;
    # note that if a fixed chirp is repeated across Q blocks as in h01, strong target fast-time Doppler ICI leaks into eg != ell_s!):
    nu_grid = np.linspace(-0.85, 0.85, 35)
    max_other = 0.0
    for eg in range(8):
        if eg == ell_s:
            continue
        for ng in nu_grid:
            if eg == ell_w and abs(ng - nu_w) <= 0.15:
                continue
            Tg = td_path_matrix(N, c1, eg, ng)
            bg = np.exp(1j * 2.0 * np.pi * ng * 1.15 * q_idx)
            pg = bg[:, None] * (u_tar @ Tg.T)
            val = abs(np.sum(np.conj(pg) * Y_rad)) ** 2 / max(float(np.sum(np.abs(pg) ** 2)), 1e-15)
            if val > max_other:
                max_other = float(val)
    val_w = abs(np.sum(np.conj(phi_w) * Y_rad)) ** 2 / max(float(np.sum(np.abs(phi_w) ** 2)), 1e-15)
    blind_hit = 1.0 if val_w > max_other else 0.0
    blind_margin_db = 10.0 * np.log10(max(val_w / max(max_other, 1e-15), 1e-15))
    return float(np.mean(sers)), wsinr, blind_hit, blind_margin_db


def solve_ssn_slp(H_eff: np.ndarray, d_qpsk: np.ndarray, P_m: float, y_shift: np.ndarray = None, max_iter: int = 12):
    """
    Fast Active-Set Semismooth Newton / Dual Projected Newton solver for multiuser QPSK CI under ||w||^2 <= P_m
    with optional known interference pre-cancellation shift y_shift (H_eff w + y_shift in CI cone!).
    """
    M_sym, D_col = H_eff.shape
    phi = np.pi / 4.0
    lamA = np.sin(phi) - 1j * np.cos(phi)
    lamB = np.sin(phi) + 1j * np.cos(phi)
    MatA = (lamA * np.conj(d_qpsk))[:, None] * H_eff
    MatB = (lamB * np.conj(d_qpsk))[:, None] * H_eff
    T_mat = np.vstack([
        np.hstack([np.real(MatA), -np.imag(MatA)]),
        np.hstack([np.real(MatB), -np.imag(MatB)]),
    ])  # (2*M_sym, 2*D_col)

    # Smooth / Semismooth Newton on primal-dual margin: maximize t - (rho/2) ||max(0, t - (T w_r + c_sh))||^2 on ||w_r||^2 <= P_m
    if y_shift is None:
        c_sh = np.zeros(2 * M_sym, dtype=np.float64)
    else:
        cA = np.real((lamA * np.conj(d_qpsk)) * y_shift)
        cB = np.real((lamB * np.conj(d_qpsk)) * y_shift)
        c_sh = np.concatenate([cA, cB])

    # Initialize via fast RZF
    G_gram = T_mat @ T_mat.T + 1e-3 * np.eye(2 * M_sym)
    rhs0 = np.ones(2 * M_sym) - c_sh
    w_r = T_mat.T @ np.linalg.solve(G_gram, rhs0)
    nrm = np.linalg.norm(w_r)
    if nrm > np.sqrt(P_m):
        w_r *= np.sqrt(P_m) / nrm

    # Active-set SSN iterations (hinge loss on violated constraints below target margin tau):
    for it in range(max_iter):
        u = T_mat @ w_r + c_sh
        tau = float(np.percentile(u, 35)) + 0.08
        viol = tau - u
        act = np.where(viol > 0.0)[0]
        if len(act) == 0:
            break
        T_act = T_mat[act]  # sparse active set! (typically ~25-40% of 2*K*N)
        # Dual Woodbury on active set: (I + rho T_act T_act^T)
        H_act = T_act @ T_act.T + 0.05 * np.eye(len(act))
        step_d = np.linalg.solve(H_act, viol[act])
        w_r = w_r + 0.85 * (T_act.T @ step_d)
        nrm = np.linalg.norm(w_r)
        if nrm > np.sqrt(P_m):
            w_r *= np.sqrt(P_m) / nrm
    return w_r[:D_col] + 1j * w_r[D_col:]


def run_probe_g7(seed: int):
    rng = np.random.default_rng(seed)
    Nt, K, Pk, N, Q = 6, 3, 3, 64, 8
    ell_max = 2
    nu_max = 0.85
    c1 = 3.0 / (2.0 * N)
    c2 = 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_blk = float(N)
    sigma2 = 10.0 ** (-18.0 / 10.0)
    a_tar = ula_steering(Nt, 40.0, unit_norm=True)
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-12.0, 12.0)
            nu = rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
        users_paths.append(paths)

    H_users_af = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    H_stack = np.vstack(H_users_af)
    alph = qpsk_alphabet()
    d_cpi = alph[rng.integers(0, 4, size=(Q, K, N))]
    noise_cpi = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N)))

    # (a1) Tang TWC'26 FULL-CHANNEL Dual Simplex QP + dedicated Gaussian sensing stream (Sol #1 mandatory strong rival!)
    S_tang_full = np.zeros((Q, N, Nt), dtype=np.complex128)
    t0 = time.perf_counter()
    for q in range(Q):
        sc_q = solve_tang_slp_dual_qp(H_stack, d_cpi[q].reshape(K * N), 0.70 * P_blk, max_iter=200)
        sr_q = np.outer((rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0), a_tar) * np.sqrt(0.30)
        S_tang_full[q] = sc_q.reshape(N, Nt) + sr_q
    t_tang_full = (time.perf_counter() - t0) * 1e3
    ser_tf, ws_tf, hit_tf, mg_tf = eval_g7_cpi_fullmap(S_tang_full, H_users_af, d_cpi, noise_cpi, lc1, lc2, c1, a_tar, P_blk, seed + 10)

    # (a2) Repeated fixed single-chirp in orthogonal complement (h01 trap test: check blind_hit when nu_s=0.33!)
    U_orth, _, _ = np.linalg.svd(np.eye(Nt) - np.outer(a_tar, np.conj(a_tar)))
    B_orth = U_orth[:, :Nt - 1]
    B_blk = np.kron(np.eye(N), B_orth)
    H_orth = H_stack @ B_blk

    S_fixed_chirp = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        s_tar = np.zeros((N, Nt), dtype=np.complex128)
        s_tar[0, :] = a_tar * np.sqrt(0.30 * P_blk)  # identical single chirp across all Q blocks!
        y_leak = H_stack @ s_tar.reshape(N * Nt)
        v_ci = solve_ssn_slp(H_orth, d_cpi[q].reshape(K * N), 0.70 * P_blk, y_shift=y_leak, max_iter=10)
        S_fixed_chirp[q] = (s_tar.reshape(N * Nt) + B_blk @ v_ci).reshape(N, Nt)
    ser_fc, ws_fc, hit_fc, mg_fc = eval_g7_cpi_fullmap(S_fixed_chirp, H_users_af, d_cpi, noise_cpi, lc1, lc2, c1, a_tar, P_blk, seed + 10)

    # #3 G7-S2-2:
    # A-only: SSN-CG full-channel SLP without target orthogonalization / cross-block thumbtack CAZAC reference
    S_Aonly = np.zeros((Q, N, Nt), dtype=np.complex128)
    t0 = time.perf_counter()
    for q in range(Q):
        s_a = solve_ssn_slp(H_stack, d_cpi[q].reshape(K * N), P_blk, y_shift=None, max_iter=10)
        S_Aonly[q] = s_a.reshape(N, Nt)
    t_Aonly = (time.perf_counter() - t0) * 1e3
    ser_A, ws_A, hit_A, mg_A = eval_g7_cpi_fullmap(S_Aonly, H_users_af, d_cpi, noise_cpi, lc1, lc2, c1, a_tar, P_blk, seed + 10)

    # A+B: Orthogonal-complement SSN-CG SLP + block-diverse Zadoff-Chu / Chu root-hopping radar waveform (zero range-lag sidelobes!)
    # Wait: check BOTH A+B AND B-only (per-bin F_N->A CI-SLP or k_nu=1 truncated CI-SLP + same orthogonal root-hopped ZC)!
    roots = [1, 3, 5, 7, 9, 11, 13, 15]
    n_idx = np.arange(N, dtype=np.float64)
    S_AB = np.zeros((Q, N, Nt), dtype=np.complex128)
    t0 = time.perf_counter()
    for q in range(Q):
        r_q = roots[q % len(roots)]  # coprime ZC root hopping in time domain -> zero periodic lag sidelobes AND decorrelates Doppler ICI across blocks!
        u_td_zc = np.exp(-1j * np.pi * r_q * n_idx * (n_idx + (r_q % 2)) / float(N)) / np.sqrt(N)
        # Map u_td_zc along a_tar to DAFT domain:
        X_tar_td = np.outer(u_td_zc * np.sqrt(0.30 * P_blk), a_tar)
        # S_AF = A X_TD
        s_tar_af = (A @ X_tar_td).reshape(N * Nt)
        y_leak = H_stack @ s_tar_af
        v_ci = solve_ssn_slp(H_orth, d_cpi[q].reshape(K * N), 0.70 * P_blk, y_shift=y_leak, max_iter=10)
        S_AB[q] = (s_tar_af + B_blk @ v_ci).reshape(N, Nt)
    t_AB = (time.perf_counter() - t0) * 1e3
    ser_AB, ws_AB, hit_AB, mg_AB = eval_g7_cpi_fullmap(S_AB, H_users_af, d_cpi, noise_cpi, lc1, lc2, c1, a_tar, P_blk, seed + 10)

    # B-only (1): Per-bin F_N->A CI-SLP + same orthogonal root-hopped ZC
    S_B_perbin = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        r_q = roots[q % len(roots)]
        u_td_zc = np.exp(-1j * np.pi * r_q * n_idx * (n_idx + (r_q % 2)) / float(N)) / np.sqrt(N)
        s_tar_af = (A @ np.outer(u_td_zc * np.sqrt(0.30 * P_blk), a_tar))
        for m in range(N):
            sl = slice(m * Nt, (m + 1) * Nt)
            Hm = np.vstack([H_users_af[k][m, sl] for k in range(K)]) @ B_orth
            yl = np.array([H_users_af[k][m, sl] @ s_tar_af[m] for k in range(K)])
            vm = solve_ssn_slp(Hm, d_cpi[q, :, m], 0.70, y_shift=yl, max_iter=8)
            S_B_perbin[q, m] = s_tar_af[m] + B_orth @ vm
    ser_Bp, ws_Bp, hit_Bp, mg_Bp = eval_g7_cpi_fullmap(S_B_perbin, H_users_af, d_cpi, noise_cpi, lc1, lc2, c1, a_tar, P_blk, seed + 10)

    # CRITICAL Sol #1 check: What if we run Tang TWC'26 FULL-CHANNEL Dual QP + same orthogonal root-hopped ZC?
    S_tang_orth_zc = np.zeros((Q, N, Nt), dtype=np.complex128)
    t0 = time.perf_counter()
    for q in range(Q):
        r_q = roots[q % len(roots)]
        u_td_zc = np.exp(-1j * np.pi * r_q * n_idx * (n_idx + (r_q % 2)) / float(N)) / np.sqrt(N)
        s_tar_af = (A @ np.outer(u_td_zc * np.sqrt(0.30 * P_blk), a_tar)).reshape(N * Nt)
        y_leak = H_stack @ s_tar_af
        v_zf = H_orth.conj().T @ np.linalg.solve(H_orth @ H_orth.conj().T + 1e-9 * np.eye(K * N), -y_leak)
        p_rem = max(0.70 * P_blk - float(np.sum(np.abs(v_zf) ** 2)), 0.05 * P_blk)
        v_fw = solve_tang_slp_dual_qp(H_orth, d_cpi[q].reshape(K * N), p_rem, max_iter=200)
        S_tang_orth_zc[q] = (s_tar_af + B_blk @ (v_zf + v_fw)).reshape(N, Nt)
    t_tang_orth = (time.perf_counter() - t0) * 1e3
    ser_toz, ws_toz, hit_toz, mg_toz = eval_g7_cpi_fullmap(S_tang_orth_zc, H_users_af, d_cpi, noise_cpi, lc1, lc2, c1, a_tar, P_blk, seed + 10)

    return {
        "tang_full_casc_ser": ser_tf, "tang_full_casc_wsinr": ws_tf, "tang_full_casc_hit": hit_tf, "tang_full_time_ms": t_tang_full,
        "fixed_chirp_h01trap_ser": ser_fc, "fixed_chirp_wsinr": ws_fc, "fixed_chirp_blind_hit": hit_fc, "fixed_chirp_margin_db": mg_fc,
        "Aonly_ser": ser_A, "Aonly_wsinr": ws_A, "Aonly_hit": hit_A, "Aonly_time_ms": t_Aonly,
        "Bonly_perbin_ser": ser_Bp, "Bonly_perbin_wsinr": ws_Bp, "Bonly_perbin_hit": hit_Bp,
        "AB_ser": ser_AB, "AB_wsinr": ws_AB, "AB_hit": hit_AB, "AB_margin_db": mg_AB, "AB_time_ms": t_AB,
        "tang_orth_zc_ser": ser_toz, "tang_orth_zc_wsinr": ws_toz, "tang_orth_zc_hit": hit_toz, "tang_orth_time_ms": t_tang_orth,
    }


def main():
    t0 = time.time()
    rows = [run_probe_g7(8300 + i) for i in range(5)]
    avg = {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
    avg["elapsed_sec"] = time.time() - t0
    print(json.dumps(avg, indent=2))


if __name__ == "__main__":
    main()
