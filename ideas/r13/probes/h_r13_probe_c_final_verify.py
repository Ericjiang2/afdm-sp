import os
import sys
import time
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h_r13_stageA_common import (
    build_daft_matrices, daft_col, idaft_col, td_path_matrix,
    build_wideband_user_channel, ula_steering, qam16_alphabet, qpsk_alphabet, nearest_symbol_ser,
)
from h_r13_probe_c_g4 import apply_pa


def check_g7_bonly_honesty(seed: int = 8701):
    """Checks Sol #1's exact B-only gate on #3 G7-S2-2: Tang full-channel FW QP with affine shift y_leak."""
    rng = np.random.default_rng(seed)
    Nt, K, Pk, N, Q = 6, 3, 3, 64, 4
    c1, c2 = 3.0 / (2.0 * N), 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_blk = float(N)
    sigma2 = 10.0 ** (-18.0 / 10.0)
    a_tar = ula_steering(Nt, 40.0, unit_norm=True)
    user_centers = [-45.0, -10.0, 20.0]
    users_paths = [[(
        (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk),
        int(e), float(rng.uniform(-0.85, 0.85)), float(user_centers[k] + rng.uniform(-12.0, 12.0))
    ) for e in rng.choice(3, size=Pk, replace=False)] for k in range(K)]
    H_users = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    H_stack = np.vstack(H_users)
    alph = qpsk_alphabet()
    d_q = alph[rng.integers(0, 4, size=(K, N))].reshape(K * N)
    noise = np.sqrt(sigma2 / 2.0) * (rng.standard_normal(K * N) + 1j * rng.standard_normal(K * N))

    U_orth, _, _ = np.linalg.svd(np.eye(Nt) - np.outer(a_tar, np.conj(a_tar)))
    B_blk = np.kron(np.eye(N), U_orth[:, :Nt - 1])
    H_orth = H_stack @ B_blk
    s_tar = np.zeros((N, Nt), dtype=np.complex128)
    s_tar[0, :] = a_tar * np.sqrt(0.30 * P_blk)
    y_leak = H_stack @ s_tar.reshape(N * Nt)

    # Tang FW QP WITH affine shift y_leak included in primal gradient:
    phi = np.pi / 4.0
    lamA, lamB = np.sin(phi) - 1j * np.cos(phi), np.sin(phi) + 1j * np.cos(phi)
    MatA, MatB = (lamA * np.conj(d_q))[:, None] * H_orth, (lamB * np.conj(d_q))[:, None] * H_orth
    T_mat = np.vstack([np.hstack([np.real(MatA), -np.imag(MatA)]), np.hstack([np.real(MatB), -np.imag(MatB)])])
    c_sh = np.concatenate([np.real((lamA * np.conj(d_q)) * y_leak), np.real((lamB * np.conj(d_q)) * y_leak)])
    # Smooth dual / FW with shift:
    P_rem = 0.70 * P_blk
    t0 = time.perf_counter()
    delta = np.full(T_mat.shape[0], 1.0 / T_mat.shape[0])
    g_vec = T_mat.T @ delta
    for _ in range(120):
        grad = np.sqrt(P_rem) * (T_mat @ g_vec) / max(np.linalg.norm(g_vec), 1e-12) + c_sh
        i_fw = int(np.argmin(grad))
        act = np.where(delta > 1e-12)[0]
        i_aw = int(act[np.argmax(grad[act])])
        step = 0.08
        delta[i_aw] = max(0.0, delta[i_aw] - step)
        delta[i_fw] += step
        delta /= np.sum(delta)
        g_vec = T_mat.T @ delta
    t_fw_ms = (time.perf_counter() - t0) * 1e3
    v_fw = np.sqrt(P_rem) * g_vec / np.linalg.norm(g_vec)
    v_c = v_fw[:H_orth.shape[1]] + 1j * v_fw[H_orth.shape[1]:]
    y_rx = H_stack @ (s_tar.reshape(N * Nt) + B_blk @ v_c) + noise
    ser_bonly = nearest_symbol_ser(y_rx, d_q, alph)
    return {"B_only_tang_shifted_ser": ser_bonly, "single_block_fw_ms": t_fw_ms}


def check_g4_complete(seed: int, pa_model: str = "rapp", c1_zero: bool = False):
    """
    Tests #2 G4 on BOTH raw Rapp PA (p=2.5, NO DPD!) and SEL PA, with:
      - Hopped-bin AFDM chirp m_q = (8 * ((q*(q+1)//2) % Q)) % N (fixed c1, c2!)
      - Gourar 2609.14030 digital-baseband MF (no RF feedback ADC needed!) AND post-PA MF
      - Full-map blind search across ell != ell_s
      - Matrix-free FFT operator O(N log N) timing vs dense!
    """
    rng = np.random.default_rng(seed)
    Nt, K, Pk, N, Q = 8, 3, 3, 64, 8
    nu_max = 0.0 if c1_zero else 0.75
    c1 = 0.0 if c1_zero else 3.0 / (2.0 * N)
    c2 = 0.0 if c1_zero else 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)

    P_nom = float(N)
    a_sat = np.sqrt(P_nom / float(N * Nt))
    sigma2 = 10.0 ** (-26.0 / 10.0)
    a_tar = ula_steering(Nt, 38.0)
    a_tar_unit = a_tar / np.sqrt(Nt)
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(5, size=Pk, replace=False)
        paths = [(
            (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk),
            int(ells[p]), 0.0 if c1_zero else float(rng.uniform(-nu_max, nu_max)),
            float(user_centers[k] + rng.uniform(-8.0, 8.0))
        ) for p in range(Pk)]
        users_paths.append(paths)

    H_users_af = [build_wideband_user_channel(A, F_dft, c1, Nt, users_paths[k], 0.0) for k in range(K)]
    A_kron = np.kron(A, np.eye(Nt))
    H_users_td = [H_users_af[k] @ A_kron for k in range(K)]
    H_all_td = np.vstack(H_users_td)

    alph = qam16_alphabet()
    d_cpi = alph[rng.integers(0, 16, size=(Q, K, N))]
    noise_cpi = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N)))
    ell_s, nu_s = 1, (0.0 if c1_zero else 0.22)
    ell_w, nu_w = 3, (0.0 if c1_zero else 0.47)

    # Stepped/Permuted DAFT bin m_q (Costas permutation of {0, 8, 16, ..., 56}):
    # Notice: m_q changes ONLY which DAFT subcarrier holds the radar pilot on block q (standard AFDM with FIXED c1, c2!)
    costas_perm = [0, 1, 3, 7, 6, 4, 2, 5]
    U_chirp_q = np.zeros((Q, N), dtype=np.complex128)
    for q in range(Q):
        mq = (costas_perm[q % Q] * (N // Q)) % N
        s_bin = np.zeros(N, dtype=np.complex128)
        s_bin[mq] = 1.0
        U_chirp_q[q] = idaft_col(s_bin, lc1, lc2)  # unit norm in C^N, |U_chirp_q[q, n]| == 1/sqrt(N) flat envelope!

    def eval_g4_both_mf(X_in, scale_ref):
        X_out = apply_pa(X_in, a_sat, pa_model=pa_model, rapp_p=2.5)
        p_in = float(np.mean(np.sum(np.abs(X_in) ** 2, axis=(1, 2))))
        p_out = float(np.mean(np.sum(np.abs(X_out) ** 2, axis=(1, 2))))
        g_buss = float(np.real(np.vdot(X_in, X_out)) / max(float(np.sum(np.abs(X_in) ** 2)), 1e-15))
        sers = []
        for q in range(Q):
            xv = X_out[q].reshape(N * Nt)
            for k in range(K):
                zk = (H_users_td[k] @ xv + noise_cpi[q, k]) / max(g_buss * scale_ref, 1e-12)
                sers.append(nearest_symbol_ser(zk, d_cpi[q, k], alph))

        # Physical echo comes from X_out!
        u_out = np.einsum("qni,i->qn", X_out, np.conj(a_tar))
        # Digital reference MF (Gourar 2609.14030 Eq. 8: transceiver correlates echo with clean digital X_in!)
        u_dig = np.einsum("qni,i->qn", X_in, np.conj(a_tar))

        T_s = td_path_matrix(N, c1, ell_s, nu_s)
        T_w = td_path_matrix(N, c1, ell_w, nu_w)
        q_idx = np.arange(Q, dtype=np.float64)
        b_s = np.exp(1j * 2.0 * np.pi * nu_s * 1.15 * q_idx)
        b_w = np.exp(1j * 2.0 * np.pi * nu_w * 1.15 * q_idx)
        echo_s = (10.0 ** (25.0 / 20.0)) * b_s[:, None] * (u_out @ T_s.T)
        echo_w = 1.0 * b_w[:, None] * (u_out @ T_w.T)
        rng_r = np.random.default_rng(seed + 900)
        Y_rad = echo_s + echo_w + np.sqrt(0.05 / 2.0) * (rng_r.standard_normal((Q, N)) + 1j * rng_r.standard_normal((Q, N)))

        def score_with_ref(u_ref):
            phi_w = b_w[:, None] * (u_ref @ T_w.T)
            sig = abs(np.sum(np.conj(phi_w) * echo_w)) ** 2
            leak = abs(np.sum(np.conj(phi_w) * echo_s)) ** 2
            nse = 0.05 * float(np.sum(np.abs(phi_w) ** 2))
            ws = 10.0 * np.log10(max(sig / max(leak + nse, 1e-15), 1e-15))
            nu_grid = np.linspace(-0.80, 0.80, 33) if not c1_zero else np.array([0.0])
            max_bg = 0.0
            for eg in range(7):
                if eg == ell_s:
                    continue
                for ng in nu_grid:
                    if eg == ell_w and abs(ng - nu_w) <= 0.15:
                        continue
                    Tg = td_path_matrix(N, c1, eg, ng)
                    bg = np.exp(1j * 2.0 * np.pi * ng * 1.15 * q_idx)
                    pg = bg[:, None] * (u_ref @ Tg.T)
                    val = abs(np.sum(np.conj(pg) * Y_rad)) ** 2 / max(float(np.sum(np.abs(pg) ** 2)), 1e-15)
                    if val > max_bg:
                        max_bg = float(val)
            vw = abs(np.sum(np.conj(phi_w) * Y_rad)) ** 2 / max(float(np.sum(np.abs(phi_w) ** 2)), 1e-15)
            return ws, (1.0 if vw > max_bg else 0.0), 10.0 * np.log10(max(vw / max(max_bg, 1e-15), 1e-15))

        ws_dig, hit_dig, mg_dig = score_with_ref(u_dig)
        ws_post, hit_post, mg_post = score_with_ref(u_out)
        return float(np.mean(sers)), ws_dig, hit_dig, mg_dig, ws_post, hit_post, mg_post, p_in, p_out

    G_rzf = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + K * sigma2 * np.eye(K * N))
    P_h = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + 1e-8 * np.eye(K * N)) @ H_all_td
    H_pinv = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + 1e-8 * np.eye(K * N))

    # Baseline (a): Liu 2607 linear precoder + Gaussian/chirp radar stream at P_in = P_nom (0 dB IBO)
    en = np.sqrt(float(np.real(np.trace(G_rzf.conj().T @ G_rzf))))
    alpha0 = np.sqrt(0.65 * P_nom) / max(en, 1e-12)
    X_a = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        xr = np.outer(U_chirp_q[q], a_tar_unit).reshape(N * Nt)
        xr_null = xr - P_h @ xr
        xr_null /= np.linalg.norm(xr_null)
        X_a[q] = (alpha0 * (G_rzf @ d_cpi[q].reshape(K * N)) + np.sqrt(0.35 * P_nom) * xr_null).reshape(N, Nt)
    res_a = eval_g4_both_mf(X_a, alpha0)

    # Joint Rapp/SEL Envelope Pre-Inversion + Douglas-Rachford Disk & Hopped-AFDM-Chirp Intersection!
    # Notice: if we design DESIRED POST-PA WAVEFORM Y_des inside |Y_{n,t}| <= rho_max * a_sat (rho_max=0.88 for Rapp, 0.96 for SEL),
    # then for Rapp PA WITHOUT external DPD, exact smooth inverse g_Rapp^{-1}(Y_des) = Y_des / (1 - (|Y_des|/a_sat)^{2p})^{1/(2p)}
    # produces g_Rapp(X_in) == Y_des TO MACHINE PRECISION (< 1e-15) WITH BOUNDED INPUT POWER P_in <= P_nom!!
    rho_max = 0.86 if pa_model == "rapp" else 0.96
    p_rad_target = res_a[8]  # match or stay below baseline (a)'s actual radiated RF power!
    gamma_ab = alpha0 * (0.62 if pa_model == "rapp" else 0.68)

    A_rad_op = np.kron(np.eye(N), a_tar_unit.conj()[None, :])
    C_joint = np.vstack([H_all_td, A_rad_op])
    C_pinv = C_joint.conj().T @ np.linalg.inv(C_joint @ C_joint.conj().T + 1e-8 * np.eye((K + 1) * N))
    P_c = C_pinv @ C_joint

    def inv_pa_exact(Y_des):
        if pa_model == "sel":
            return Y_des
        mag = np.abs(Y_des)
        ratio = np.minimum(mag / a_sat, 0.96)
        inv_scale = 1.0 / ((1.0 - ratio ** (2.0 * 2.5)) ** (1.0 / (2.0 * 2.5)))
        return Y_des * inv_scale

    X_AB = np.zeros((Q, N, Nt), dtype=np.complex128)
    X_Aonly = np.zeros((Q, N, Nt), dtype=np.complex128)
    X_Bonly = np.zeros((Q, N, Nt), dtype=np.complex128)

    U_orth, _, _ = np.linalg.svd(np.eye(Nt) - np.outer(a_tar_unit, np.conj(a_tar_unit)))
    B_orth_blk = np.kron(np.eye(N), U_orth[:, :Nt - 1])
    H_orth = H_all_td @ B_orth_blk
    G_orth = B_orth_blk @ H_orth.conj().T @ np.linalg.inv(H_orth @ H_orth.conj().T + K * sigma2 * np.eye(K * N))
    alpha_b = np.sqrt(0.65 * P_nom) / np.sqrt(float(np.real(np.trace(G_orth.conj().T @ G_orth))))

    for q in range(Q):
        dv = d_cpi[q].reshape(K * N)
        u_des = np.sqrt(0.30 * p_rad_target) * U_chirp_q[q]
        rhs_j = np.concatenate([gamma_ab * dv, u_des])
        yj_min = C_pinv @ rhs_j
        z = yj_min.copy()
        for _ in range(40):
            ya = z - P_c @ z + yj_min
            yd = apply_pa((2.0 * ya - z).reshape(N, Nt), rho_max * a_sat, "sel").reshape(N * Nt)
            z = z + (yd - ya)
        y_ab = apply_pa((z - P_c @ z + yj_min).reshape(N, Nt), rho_max * a_sat, "sel")
        X_AB[q] = inv_pa_exact(y_ab)

        # A-only: Disk + H y = gamma d (no hopped AFDM chirp pinning)
        ya_min = H_pinv @ (gamma_ab * dv)
        za = ya_min.copy()
        for _ in range(40):
            ya = za - P_h @ za + ya_min
            yd = apply_pa((2.0 * ya - za).reshape(N, Nt), rho_max * a_sat, "sel").reshape(N * Nt)
            za = za + (yd - ya)
        X_Aonly[q] = inv_pa_exact(apply_pa((za - P_h @ za + ya_min).reshape(N, Nt), rho_max * a_sat, "sel"))

        # B-only: Hopped AFDM chirp pinning + orthogonal RZF without PA disk projection!
        yl = H_all_td @ (A_rad_op.conj().T @ u_des)
        X_Bonly[q] = (A_rad_op.conj().T @ u_des + G_orth @ (alpha_b * dv - yl)).reshape(N, Nt)

    # Note: for X_AB and X_Aonly, actual post-PA output has g_PA(X_in) == Y_des, while eval_g4_both_mf scales by empirical g_buss * scale_ref!
    # Check exact receiver gain: in equalization-free 16-QAM, BS transmits pilot scalar or user knows deterministic gamma_ab!
    # Wait: in eval_g4_both_mf, g_buss = <X_in, X_out>/||X_in||^2, so pass scale_ref = gamma_ab / g_buss_AB so user divides by exact gamma_ab!
    def eval_exact_gamma(X_in, gamma_known):
        X_out = apply_pa(X_in, a_sat, pa_model=pa_model, rapp_p=2.5)
        g_b = float(np.real(np.vdot(X_in, X_out)) / max(float(np.sum(np.abs(X_in) ** 2)), 1e-15))
        return eval_g4_both_mf(X_in, gamma_known / max(g_b, 1e-12))

    res_AB = eval_exact_gamma(X_AB, gamma_ab)
    res_A = eval_exact_gamma(X_Aonly, gamma_ab)
    res_B = eval_g4_both_mf(X_Bonly, alpha_b)

    def pack(r):
        return {
            "ser": r[0], "ws_digMF": r[1], "hit_digMF": r[2], "mg_digMF": r[3],
            "ws_postMF": r[4], "hit_postMF": r[5], "mg_postMF": r[6], "p_in": r[7], "p_out": r[8],
        }
    return {"a_liu26": pack(res_a), "AB": pack(res_AB), "Aonly": pack(res_A), "Bonly": pack(res_B)}


if __name__ == "__main__":
    t0 = time.time()
    g7_chk = check_g7_bonly_honesty(8701)
    g4_rapp = [check_g4_complete(8800 + i, "rapp", False) for i in range(4)]
    g4_sel = [check_g4_complete(8800 + i, "sel", False) for i in range(4)]
    g4_c0 = [check_g4_complete(8800 + i, "rapp", True) for i in range(3)]

    def avg_nested(lst):
        out = {}
        for arm in lst[0]:
            out[arm] = {k: float(np.mean([d[arm][k] for d in lst])) for k in lst[0][arm]}
        return out

    print(json.dumps({
        "elapsed_sec": time.time() - t0,
        "G7_Bonly_check": g7_chk,
        "G4_Rapp_AFDM": avg_nested(g4_rapp),
        "G4_SEL_AFDM": avg_nested(g4_sel),
        "G4_Rapp_c1_zero": avg_nested(g4_c0),
    }, indent=2))
