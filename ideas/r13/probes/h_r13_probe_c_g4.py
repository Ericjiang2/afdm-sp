import os
import sys
import time
import json
from math import erfc
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h_r13_stageA_common import (
    build_daft_matrices, idaft_col, td_path_matrix, build_wideband_user_channel,
    ula_steering, qam16_alphabet, nearest_symbol_ser,
)


def apply_pa(X_td: np.ndarray, a_sat: float, pa_model: str = "sel", rapp_p: float = 2.5) -> np.ndarray:
    mag = np.abs(X_td)
    if pa_model == "sel":
        scale = np.where(mag > a_sat, a_sat / np.maximum(mag, 1e-15), 1.0)
    else:
        scale = 1.0 / ((1.0 + (mag / max(a_sat, 1e-15)) ** (2.0 * rapp_p)) ** (1.0 / (2.0 * rapp_p)))
    return X_td * scale


def eval_full_map_radar(u_out: np.ndarray, c1: float, ell_s: int, nu_s: float, ell_w: int, nu_w: float, rng_r):
    """
    Evaluates BOTH WeakSINR at (ell_w, nu_w) AND full-map blind peak search over ell in 0..7 and 32 Doppler bins
    after masking the known/Stage-1 coarse strong peak neighborhood (|ell - ell_s| == 0, |nu - nu_s| <= 0.25)!
    """
    Q, N = u_out.shape
    T_s = td_path_matrix(N, c1, ell_s, nu_s)
    T_w = td_path_matrix(N, c1, ell_w, nu_w)
    q_idx = np.arange(Q, dtype=np.float64)
    b_s = np.exp(1j * 2.0 * np.pi * nu_s * 1.15 * q_idx)
    b_w = np.exp(1j * 2.0 * np.pi * nu_w * 1.15 * q_idx)
    amp_s = 10.0 ** (25.0 / 20.0)
    echo_s = amp_s * b_s[:, None] * (u_out @ T_s.T)
    echo_w = 1.0 * b_w[:, None] * (u_out @ T_w.T)
    rad_noise = np.sqrt(0.05 / 2.0) * (rng_r.standard_normal((Q, N)) + 1j * rng_r.standard_normal((Q, N)))
    Y_rad = echo_s + echo_w + rad_noise

    phi_w = b_w[:, None] * (u_out @ T_w.T)
    sig_num = abs(np.sum(np.conj(phi_w) * echo_w)) ** 2
    leak_s = abs(np.sum(np.conj(phi_w) * echo_s)) ** 2
    noise_den = 0.05 * float(np.sum(np.abs(phi_w) ** 2))
    wsinr_db = 10.0 * np.log10(max(sig_num / max(leak_s + noise_den, 1e-15), 1e-15))

    # Full-map search over ell_grid = 0..6, nu_grid = linspace(-0.8, 0.8, 33)
    # Using CLEAN strong-echo cancellation (projecting out span of strong target lag ell_s across Doppler neighborhood!)
    # Wait: test BOTH raw MF peak-2 AND standard CLEAN strong-peak subtraction!
    # Full-map search across non-clutter range gates ell_g != ell_s (standard near-range clutter gate blanking ell != ell_s!)
    nu_grid = np.linspace(-0.80, 0.80, 33)
    max_bg_raw = 0.0
    for ell_g in range(7):
        if ell_g == ell_s:
            continue
        for nu_g in nu_grid:
            if ell_g == ell_w and abs(nu_g - nu_w) <= 0.15:
                continue
            Tg = td_path_matrix(N, c1, ell_g, nu_g)
            bg = np.exp(1j * 2.0 * np.pi * nu_g * 1.15 * q_idx)
            phig = bg[:, None] * (u_out @ Tg.T)
            val = abs(np.sum(np.conj(phig) * Y_rad)) ** 2 / max(float(np.sum(np.abs(phig) ** 2)), 1e-15)
            if val > max_bg_raw:
                max_bg_raw = float(val)
    val_w = abs(np.sum(np.conj(phi_w) * Y_rad)) ** 2 / max(float(np.sum(np.abs(phi_w) ** 2)), 1e-15)
    loc_hit = 1.0 if val_w > max_bg_raw else 0.0
    margin_vs_max_sidelobe_db = 10.0 * np.log10(max(val_w / max(max_bg_raw, 1e-15), 1e-15))
    return wsinr_db, loc_hit, margin_vs_max_sidelobe_db


def run_probe_g4(seed: int, pa_model: str = "sel"):
    rng = np.random.default_rng(seed)
    Nt, K, Pk, N, Q = 8, 3, 3, 64, 8
    ell_max = 4
    nu_max = 0.75
    c1 = 3.0 / (2.0 * N)
    c2 = 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)

    # Fixed physical PA ceiling A_sat and fixed thermal noise sigma2!
    P_nom = float(N)
    a_sat = np.sqrt(P_nom / float(N * Nt))  # Nominal 0 dB IBO reference ceiling!
    sigma2 = 10.0 ** (-26.0 / 10.0)         # Thermal noise fixed relative to P_nom!
    theta_tar = 38.0
    a_tar = ula_steering(Nt, theta_tar)     # ||a_tar||^2 = Nt
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(ell_max + 1, size=Pk, replace=False)
        paths = []
        for p in range(Pk):
            ang = user_centers[k] + rng.uniform(-8.0, 8.0)
            nu = rng.uniform(-nu_max, nu_max)
            gain = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk)
            paths.append((gain, int(ells[p]), float(nu), float(ang)))
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
    # Radar ZC chirp in nullspace of H_all_td (NOT single bin m=0! Full-band Zadoff-Chu has flat time-domain envelope AND thumbtack ambiguity!)
    zc = np.exp(-1j * np.pi * np.arange(N) * (np.arange(N) + 1) / float(N))
    S_zc = np.outer(zc / np.sqrt(N), a_tar / np.sqrt(Nt))
    x_zc_vec = idaft_col(S_zc, lc1, lc2).reshape(N * Nt)
    P_h_mat = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + 1e-9 * np.eye(K * N)) @ H_all_td
    x_rad_null = x_zc_vec - P_h_mat @ x_zc_vec
    x_rad_null /= max(np.linalg.norm(x_rad_null), 1e-12)

    e_norm = np.sqrt(float(np.real(np.trace(G_rzf.conj().T @ G_rzf))))
    alpha0 = np.sqrt(0.70 * P_nom) / max(e_norm, 1e-12)
    X_lin0 = np.zeros((Q, N, Nt), dtype=np.complex128)
    for q in range(Q):
        d_vec = d_cpi[q].reshape(K * N)
        # Distinct random unimodular phase on ZC per block OR deterministic slow-time? Wait: test random block phase vs ZC!
        x_tot = alpha0 * (G_rzf @ d_vec) + np.sqrt(0.30 * P_nom) * np.exp(1j * 0.53 * q * q) * x_rad_null
        X_lin0[q] = x_tot.reshape(N, Nt)

    def eval_waveform(X_in, scale_ref):
        X_out = apply_pa(X_in, a_sat, pa_model=pa_model)
        p_rad_out = float(np.mean(np.sum(np.abs(X_out) ** 2, axis=(1, 2))))
        # Empirical Bussgang scalar gain <X_out, X_in> / ||X_in||^2 (gives baseline BEST possible linear scalar receiver scaling!)
        g_buss = float(np.real(np.vdot(X_in, X_out)) / max(float(np.sum(np.abs(X_in) ** 2)), 1e-15))
        sers = []
        for q in range(Q):
            xv = X_out[q].reshape(N * Nt)
            for k in range(K):
                zk = (H_users_td[k] @ xv + noise_cpi[q, k]) / max(g_buss * scale_ref, 1e-12)
                sers.append(nearest_symbol_ser(zk, d_cpi[q, k], alph))
        u_out = np.einsum("qni,i->qn", X_out, np.conj(a_tar))
        wsinr, hit, marg = eval_full_map_radar(u_out, c1, ell_s, nu_s, ell_w, nu_w, np.random.default_rng(seed + 500))
        return float(np.mean(sers)), wsinr, hit, marg, p_rad_out

    # (a1) Liu 2607 at 0 dB IBO
    ser_a0, wsinr_a0, hit_a0, marg_a0, p_out_a0 = eval_waveform(X_lin0, alpha0)

    # (a2) CRITICAL CHECK: Sweep scalar input backoff IBO_opt in {1, 2, 3, 4, 5, 6, 7, 8} dB on SAME physical PA!
    best_bo_ser = 1.0
    best_bo_info = None
    for bo_db in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]:
        eta = 10.0 ** (-bo_db / 20.0)
        s_bo, ws_bo, h_bo, mg_bo, po_bo = eval_waveform(eta * X_lin0, eta * alpha0)
        if s_bo < best_bo_ser:
            best_bo_ser = s_bo
            best_bo_info = (bo_db, s_bo, ws_bo, h_bo, mg_bo, po_bo)

    # #2 G4-S1-2: Affine Nullspace Disk Projection (Module A) + Causal Cross-Block Lag-Product Ambiguity Shaping (Module B)
    # Enforce |X_in| <= a_sat AND radiated output power <= p_out_a0!
    r_disk = min(a_sat, a_sat)  # inside |x| <= a_sat, SEL has 0 clipping; on Rapp, pre-compensate or stay within linear/quasi-linear disk!
    # Target communication scale gamma matched to feasible disk radius:
    gamma_t = alpha0 * 0.72
    H_pinv = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + 1e-8 * np.eye(K * N))

    def solve_g4_s1_2(enable_A: bool, enable_B: bool):
        X_sol = np.zeros((Q, N, Nt), dtype=np.complex128)
        # Causal memory of cross-block lag products at non-zero lags delta_ell in {-4..-1, 1..4} around strong target!
        # Wait: for strong target at ell_s=1, leakage into ell_w in {0..6}\{ell_s} comes from auto-ambiguity of u_tar[q] at lag delta_ell = ell_w - ell_s in {-3..+5}\{0}!
        lags = [-3, -2, -1, 1, 2, 3, 4]
        # Continuous Doppler band around strong target relative to search [-0.8, 0.8]: coherent memory across q'<q with 3 Slepian/Fourier frequencies
        mem_freqs = [-0.25, 0.0, 0.25]
        mem_acc = {(dl, mf): 0.0 + 0.0j for dl in lags for mf in mem_freqs}

        for q in range(Q):
            d_vec = d_cpi[q].reshape(K * N)
            x_min = H_pinv @ (gamma_t * d_vec)  # exact communication solution H x = gamma d
            if not enable_A:
                # B-only: start from linear RZF + radar shaping without affine-nullspace disk projection, then PA clips!
                x_cur = (alpha0 * (G_rzf @ d_vec) + np.sqrt(0.25 * P_nom) * x_rad_null).copy()
            else:
                x_cur = (x_min + np.sqrt(0.18 * P_nom) * np.exp(1j * 0.71 * q) * x_rad_null).copy()

            for it in range(28):
                X_mat = x_cur.reshape(N, Nt)
                if enable_B:
                    u_q = X_mat @ np.conj(a_tar)  # (N,)
                    grad_u = np.zeros(N, dtype=np.complex128)
                    for dl in lags:
                        u_shift = np.roll(u_q, dl)
                        c_cur = np.vdot(u_shift, u_q)
                        for mf in mem_freqs:
                            ph = np.exp(-1j * 2.0 * np.pi * mf * q)
                            res_m = mem_acc[(dl, mf)] + ph * c_cur
                            grad_u += np.conj(ph) * res_m * u_shift + ph * np.conj(res_m) * np.roll(u_q, -dl)
                    gn = float(np.linalg.norm(grad_u))
                    if gn > 1e-12:
                        step_b = 0.18 * np.sqrt(P_nom) / (gn * np.sqrt(Nt))
                        x_cur = x_cur - step_b * np.outer(grad_u, a_tar).reshape(N * Nt)
                    if not enable_A:
                        # B-only: keep communication RZF subspace fixed and shape radar only in comm nullspace!
                        x_cur = P_h_mat @ (alpha0 * (G_rzf @ d_vec)) + (x_cur - P_h_mat @ x_cur)

                if enable_A:
                    # Alternating / Douglas-Rachford projection onto H x = gamma d AND disk |x| <= 0.92 * a_sat, capped at p_out_a0!
                    x_cur = x_cur - P_h_mat @ x_cur + x_min
                    X_m = x_cur.reshape(N, Nt)
                    X_m = apply_pa(X_m, 0.95 * a_sat, pa_model="sel")
                    p_blk_cur = float(np.sum(np.abs(X_m) ** 2))
                    if p_blk_cur > p_out_a0:
                        X_m *= np.sqrt(p_out_a0 / p_blk_cur)
                    x_cur = X_m.reshape(N * Nt)

            X_sol[q] = x_cur.reshape(N, Nt)
            # Update causal cross-block memory using actual PA output!
            u_act = apply_pa(X_sol[q], a_sat, pa_model=pa_model) @ np.conj(a_tar)
            for dl in lags:
                c_act = np.vdot(np.roll(u_act, dl), u_act)
                for mf in mem_freqs:
                    mem_acc[(dl, mf)] += np.exp(-1j * 2.0 * np.pi * mf * q) * c_act

        sc_eval = gamma_t if enable_A else alpha0
        return eval_waveform(X_sol, sc_eval)

    ser_AB, ws_AB, hit_AB, mg_AB, po_AB = solve_g4_s1_2(True, True)
    ser_A, ws_A, hit_A, mg_A, po_A = solve_g4_s1_2(True, False)
    ser_B, ws_B, hit_B, mg_B, po_B = solve_g4_s1_2(False, True)

    return {
        "pa_model": pa_model,
        "a0_0dB_ser": ser_a0, "a0_0dB_wsinr": wsinr_a0, "a0_hit": hit_a0, "a0_p_out": p_out_a0,
        "a_opt_bo_db": best_bo_info[0], "a_opt_bo_ser": best_bo_info[1], "a_opt_bo_wsinr": best_bo_info[2], "a_opt_bo_hit": best_bo_info[3], "a_opt_bo_p_out": best_bo_info[5],
        "AB_ser": ser_AB, "AB_wsinr": ws_AB, "AB_hit": hit_AB, "AB_marg_db": mg_AB, "AB_p_out": po_AB,
        "Aonly_ser": ser_A, "Aonly_wsinr": ws_A, "Aonly_hit": hit_A,
        "Bonly_ser": ser_B, "Bonly_wsinr": ws_B, "Bonly_hit": hit_B,
    }


def main():
    t0 = time.time()
    sel_rows = [run_probe_g4(8200 + i, "sel") for i in range(5)]
    rapp_rows = [run_probe_g4(8200 + i, "rapp") for i in range(5)]

    def avg(lst):
        ks = [k for k in lst[0] if isinstance(lst[0][k], (int, float))]
        return {k: float(np.mean([d[k] for d in lst])) for k in ks}

    out = {"elapsed_sec": time.time() - t0, "SEL_PA": avg(sel_rows), "Rapp_PA_p25": avg(rapp_rows)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
