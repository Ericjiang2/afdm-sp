import os
import sys
import time
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h_r13_stageA_common import (
    build_daft_matrices, daft_col, idaft_col, td_path_matrix,
    build_wideband_user_channel, ula_steering, qam16_alphabet, nearest_symbol_ser,
)
from h_r13_probe_c_g4 import apply_pa, eval_full_map_radar


def probe_g4_chirp_disk(seed: int, pa_model: str = "sel"):
    """
    Tests #2 G4-S1-2 with AFDM chirp reference (2*N*c1 = 3 > 2*nu_max + 1) +
    Affine Nullspace PA Disk Projection (Module A) + Directional Target Protection / Cross-Block Dirichlet Cancellation (Module B)!
    """
    rng = np.random.default_rng(seed)
    Nt, K, Pk, N, Q = 8, 3, 3, 64, 8
    c1 = 3.0 / (2.0 * N)
    c2 = 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_nom = float(N)
    a_sat = np.sqrt(P_nom / float(N * Nt))
    sigma2 = 10.0 ** (-26.0 / 10.0)
    a_tar = ula_steering(Nt, 38.0)  # ||a_tar||^2 = Nt
    a_tar_unit = a_tar / np.sqrt(Nt)
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(5, size=Pk, replace=False)
        paths = [(
            (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk),
            int(ells[p]), float(rng.uniform(-0.75, 0.75)), float(user_centers[k] + rng.uniform(-8.0, 8.0))
        ) for p in range(Pk)]
        users_paths.append(paths)

    H_users_af = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    A_kron = np.kron(A, np.eye(Nt))
    H_users_td = [H_users_af[k] @ A_kron for k in range(K)]
    H_all_td = np.vstack(H_users_td)  # (K*N, N*Nt)

    alph = qam16_alphabet()
    d_cpi = alph[rng.integers(0, 16, size=(Q, K, N))]
    noise_cpi = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N)))
    ell_s, nu_s = 1, 0.18
    ell_w, nu_w = 3, 0.43

    G_rzf = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + K * sigma2 * np.eye(K * N))
    # AFDM single-chirp radar reference in DAFT bin m=0 (whose ambiguity ridge -2Nc1*dl = -3*dl lies OUTSIDE [-0.8, 0.8]!)
    S_chirp0 = np.zeros((N, Nt), dtype=np.complex128)
    S_chirp0[0, :] = a_tar_unit * np.sqrt(N)  # unit-modulus in TD along a_tar_unit!
    X_chirp_td = idaft_col(S_chirp0, lc1, lc2)  # (N, Nt), |u_tar[n]| == const!
    u_chirp_unit = (X_chirp_td @ np.conj(a_tar_unit)) / np.sqrt(float(N))  # unit norm in C^N!

    P_h_mat = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + 1e-8 * np.eye(K * N)) @ H_all_td
    H_pinv = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + 1e-8 * np.eye(K * N))
    x_rad_null = X_chirp_td.reshape(N * Nt) - P_h_mat @ X_chirp_td.reshape(N * Nt)
    x_rad_null /= np.linalg.norm(x_rad_null)

    # Also evaluate Gourar 2609.14030 realistic digital-baseband radar MF (correlating with pre-PA digital waveform X_in)
    # AND post-PA coupler radar MF (correlating with X_out)!
    def eval_arm(X_in, scale_ref):
        X_out = apply_pa(X_in, a_sat, pa_model=pa_model)
        p_out = float(np.mean(np.sum(np.abs(X_out) ** 2, axis=(1, 2))))
        g_buss = float(np.real(np.vdot(X_in, X_out)) / max(float(np.sum(np.abs(X_in) ** 2)), 1e-15))
        sers = []
        for q in range(Q):
            xv = X_out[q].reshape(N * Nt)
            for k in range(K):
                zk = (H_users_td[k] @ xv + noise_cpi[q, k]) / max(g_buss * scale_ref, 1e-12)
                sers.append(nearest_symbol_ser(zk, d_cpi[q, k], alph))
        u_out = np.einsum("qni,i->qn", X_out, np.conj(a_tar))
        ws, hit, mg = eval_full_map_radar(u_out, c1, ell_s, nu_s, ell_w, nu_w, np.random.default_rng(seed + 500))
        return float(np.mean(sers)), ws, hit, mg, p_out

    # Baseline (a): Liu 2607 linear precoder + AFDM chirp radar stream at 0 dB IBO (strongest possible radar stream!)
    e_norm = np.sqrt(float(np.real(np.trace(G_rzf.conj().T @ G_rzf))))
    alpha0 = np.sqrt(0.65 * P_nom) / max(e_norm, 1e-12)
    X_a0 = np.zeros((Q, N, Nt), dtype=np.complex128)
    # Slow-time Golay/unimodular phase on radar chirp across Q blocks? Wait: if you phase-modulate across Q blocks randomly,
    # slow-time Doppler sidelobes of the +25 dB strong target explode across all Doppler bins!!
    # Keep slow-time phase coherent (1.0) on the AFDM chirp so slow-time Doppler stays focused at nu_s, while fast-time AFDM chirp shears range sidelobes outside [-0.8, 0.8]!
    for q in range(Q):
        dv = d_cpi[q].reshape(K * N)
        X_a0[q] = (alpha0 * (G_rzf @ dv) + np.sqrt(0.35 * P_nom) * x_rad_null).reshape(N, Nt)
    ser_a0, ws_a0, hit_a0, mg_a0, pout_a0 = eval_arm(X_a0, alpha0)

    # Joint Disk Projection (Module A: H x = gamma d inside PA disk |x| <= a_sat) +
    # Target-Subspace AFDM Chirp Pinning `(I_N kron a_tar_unit^H) x = beta u_chirp_unit` (Module B)!
    # Notice: Under linear PA ball ||X||_F^2 <= P, A and B live in orthogonal spatial subspaces (trivial!).
    # Under PER-ANTENNA NONLINEAR PA DISK |X_{n,t}| <= a_sat, u_rad * a_tar_unit^H + X_orth MUST JOINTLY satisfy |X_{n,t}| <= a_sat at every sample (n,t)!!
    # Let's test A+B, A-only (disk + H x = gamma d, no target chirp pinning), and B-only (target chirp pinning + linear comm without disk projection, clipped by PA)!
    gamma_ab = alpha0 * 0.68
    # Build joint linear constraint C_joint x = rhs_joint:
    #   Row block 1 (K*N): H_all_td x = gamma_ab * d_q
    #   Row block 2 (N):   (I_N kron a_tar_unit^H) x = sqrt(0.28 * pout_a0) * u_chirp_unit
    A_rad_op = np.kron(np.eye(N), a_tar_unit.conj()[None, :])  # (N, N*Nt)
    C_joint = np.vstack([H_all_td, A_rad_op])                  # ((K+1)*N, N*Nt) = (256, 512) -> 256-dim exact nullspace left for PA disk peak reduction!!
    C_pinv = C_joint.conj().T @ np.linalg.inv(C_joint @ C_joint.conj().T + 1e-8 * np.eye((K + 1) * N))
    P_c = C_pinv @ C_joint

    X_AB = np.zeros((Q, N, Nt), dtype=np.complex128)
    X_Aonly = np.zeros((Q, N, Nt), dtype=np.complex128)
    X_Bonly = np.zeros((Q, N, Nt), dtype=np.complex128)

    U_orth, _, _ = np.linalg.svd(np.eye(Nt) - np.outer(a_tar_unit, np.conj(a_tar_unit)))
    B_orth_blk = np.kron(np.eye(N), U_orth[:, :Nt - 1])
    H_orth = H_all_td @ B_orth_blk
    G_orth_rzf = B_orth_blk @ H_orth.conj().T @ np.linalg.inv(H_orth @ H_orth.conj().T + K * sigma2 * np.eye(K * N))
    en_orth = np.sqrt(float(np.real(np.trace(G_orth_rzf.conj().T @ G_orth_rzf))))
    alpha_bonly = np.sqrt(0.65 * P_nom) / max(en_orth, 1e-12)

    for q in range(Q):
        dv = d_cpi[q].reshape(K * N)
        u_des = np.sqrt(0.30 * pout_a0) * u_chirp_unit
        rhs_j = np.concatenate([gamma_ab * dv, u_des])
        x_j_min = C_pinv @ rhs_j

        # A+B: POCS / Douglas-Rachford between affine intersection {C_joint x = rhs_j} and PA disk {|x| <= 0.94 * a_sat}!
        z_dr = x_j_min.copy()
        for _ in range(35):
            x_aff = z_dr - P_c @ z_dr + x_j_min
            r_ref = 2.0 * x_aff - z_dr
            x_dsk = apply_pa(r_ref.reshape(N, Nt), 0.93 * a_sat, "sel").reshape(N * Nt)
            z_dr = z_dr + (x_dsk - x_aff)
        x_ab = z_dr - P_c @ z_dr + x_j_min
        x_ab = apply_pa(x_ab.reshape(N, Nt), 0.96 * a_sat, "sel")
        if float(np.sum(np.abs(x_ab) ** 2)) > pout_a0:
            x_ab *= np.sqrt(pout_a0 / float(np.sum(np.abs(x_ab) ** 2)))
        X_AB[q] = x_ab

        # A-only: POCS between {H_all_td x = gamma_ab * dv} and PA disk {|x| <= 0.94 * a_sat} (no AFDM chirp pinning!)
        x_a_min = H_pinv @ (gamma_ab * dv)
        za = x_a_min.copy()
        for _ in range(35):
            xa = za - P_h_mat @ za + x_a_min
            xd = apply_pa((2.0 * xa - za).reshape(N, Nt), 0.93 * a_sat, "sel").reshape(N * Nt)
            za = za + (xd - xa)
        xa_fin = apply_pa((za - P_h_mat @ za + x_a_min).reshape(N, Nt), 0.96 * a_sat, "sel")
        X_Aonly[q] = xa_fin

        # B-only: Linear orthogonal RZF + AFDM chirp pinning WITHOUT disk projection -> clipped by nonlinear PA!
        y_rad_leak = H_all_td @ (A_rad_op.conj().T @ u_des)
        xb = A_rad_op.conj().T @ u_des + G_orth_rzf @ (alpha_bonly * dv - y_rad_leak)
        X_Bonly[q] = xb.reshape(N, Nt)

    ser_AB, ws_AB, hit_AB, mg_AB, po_AB = eval_arm(X_AB, gamma_ab)
    ser_A, ws_A, hit_A, mg_A, po_A = eval_arm(X_Aonly, gamma_ab)
    ser_B, ws_B, hit_B, mg_B, po_B = eval_arm(X_Bonly, alpha_bonly)
    return {
        "pa": pa_model,
        "a0_ser": ser_a0, "a0_wsinr": ws_a0, "a0_hit": hit_a0, "a0_pout": pout_a0,
        "AB_ser": ser_AB, "AB_wsinr": ws_AB, "AB_hit": hit_AB, "AB_marg_db": mg_AB, "AB_pout": po_AB,
        "Aonly_ser": ser_A, "Aonly_wsinr": ws_A, "Aonly_hit": hit_A,
        "Bonly_ser": ser_B, "Bonly_wsinr": ws_B, "Bonly_hit": hit_B,
    }


if __name__ == "__main__":
    t0 = time.time()
    sel = [probe_g4_chirp_disk(8500 + i, "sel") for i in range(4)]
    rapp = [probe_g4_chirp_disk(8500 + i, "rapp") for i in range(4)]
    def avg(lst):
        return {k: float(np.mean([d[k] for d in lst])) for k in lst[0] if isinstance(lst[0][k], (int, float))}
    print(json.dumps({"elapsed_sec": time.time() - t0, "SEL": avg(sel), "Rapp_p25": avg(rapp)}, indent=2))
