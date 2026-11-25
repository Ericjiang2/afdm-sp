import time
import numpy as np


def de_bruijn_k_2(k):
    """Order-2 De Bruijn cycle B(k, 2) of length k^2."""
    a = [0] * (2 * k + 2)
    seq = []
    def db(t, p):
        if t > 2:
            if 2 % p == 0:
                seq.extend(a[1:p + 1])
        else:
            a[t] = a[t - p]
            db(t + 1, p)
            for j in range(a[t - p] + 1, k):
                a[t] = j
                db(t + 1, t)
    db(1, 1)
    return np.array(seq, dtype=int)


def thue_morse_base_q(N=64, Q=4):
    """Prouhet-Tarry-Escott / generalized Thue-Morse base-Q digit sum mod Q (Sun & Huang 2611.23740 Ref [9])."""
    n = np.arange(N)
    s = np.zeros(N, dtype=int)
    tmp = n.copy()
    while np.any(tmp > 0):
        s += tmp % Q
        tmp //= Q
    return s % Q


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


def eval_active_responses(a, u_vec, C_plus, C_minus, Q=4):
    N = len(a)
    Q_iso = np.array([isolated_pattern_q(k, u_vec, Q=Q) for k in range(Q)])
    n_idx = np.arange(N)[:, None]
    B_iso = Q_iso[a, :] * np.exp(1j * np.pi * n_idx * u_vec[None, :])
    M = np.eye(N, dtype=np.complex128)
    idx = np.arange(N - 1)
    M[idx, idx + 1] += C_plus[a[idx], a[idx + 1]]
    M[idx + 1, idx] += C_minus[a[idx + 1], a[idx]]
    return np.linalg.solve(M, B_iso)


def fast_pdj(Y, a, L=10, sigma2=1e-2, Q=4, C_plus=None, C_minus=None):
    Nr, Nt = Y.shape
    u_grid = np.linspace(-np.sin(np.pi / 3), np.sin(np.pi / 3), 129)
    v_grid = np.linspace(-1.0, 1.0, 64, endpoint=False)
    t_idx = np.arange(Nt)[:, None]
    if C_plus is None:
        Q_grid = np.array([isolated_pattern_q(k, u_grid, Q=Q) for k in range(Q)])
        B_rx = Q_grid[a, :] * np.exp(1j * np.pi * np.arange(Nr)[:, None] * u_grid[None, :])
    else:
        B_rx = eval_active_responses(a, u_grid, C_plus, C_minus, Q=Q)
    B_rx_norm = np.sum(np.abs(B_rx) ** 2, axis=0) * Nt
    F_tx = np.exp(-1j * np.pi * t_idx * v_grid[None, :])

    R = Y.copy()
    y_vec = Y.reshape(-1)
    m = Nr * Nt
    lam = max(1e-10, 0.05 * sigma2)
    u_est = np.zeros(L)
    v_est = np.zeros(L)
    du_cand = np.array([-0.007, -0.0025, 0.0, 0.0025, 0.007])
    dv_cand = np.array([-0.012, 0.0, 0.012])

    for s in range(L):
        Z = R @ F_tx.conj()
        corr = np.abs(B_rx.conj().T @ Z) ** 2 / B_rx_norm[:, None]
        iu, iv = np.unravel_index(np.argmax(corr), corr.shape)
        u_est[s], v_est[s] = u_grid[iu], v_grid[iv]

        cur_s = s + 1
        if C_plus is None:
            Q_cur = np.array([isolated_pattern_q(k, u_est[:cur_s], Q=Q) for k in range(Q)])
            Br = Q_cur[a, :] * np.exp(1j * np.pi * np.arange(Nr)[:, None] * u_est[:cur_s][None, :])
        else:
            Br = eval_active_responses(a, u_est[:cur_s], C_plus, C_minus, Q=Q)
        Bt = np.exp(-1j * np.pi * t_idx * v_est[:cur_s][None, :])
        A_mat = (Br[:, None, :] * Bt[None, :, :]).reshape(m, cur_s)
        c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam * np.eye(cur_s), A_mat.conj().T @ y_vec)

        for idx in range(cur_s):
            res_minus = (y_vec - A_mat @ c_hat + A_mat[:, idx] * c_hat[idx]).reshape(Nr, Nt)
            uc = np.clip(u_est[idx] + du_cand, -np.sin(np.pi / 3), np.sin(np.pi / 3))
            vc = ((v_est[idx] + dv_cand + 1.0) % 2.0) - 1.0
            if C_plus is None:
                Qc = np.array([isolated_pattern_q(k, uc, Q=Q) for k in range(Q)])
                Brc = Qc[a, :] * np.exp(1j * np.pi * np.arange(Nr)[:, None] * uc[None, :])
            else:
                Brc = eval_active_responses(a, uc, C_plus, C_minus, Q=Q)
            Btc = np.exp(-1j * np.pi * t_idx * vc[None, :])
            sc_mat = np.abs(Brc.conj().T @ (res_minus @ Btc.conj())) ** 2 / (np.sum(np.abs(Brc) ** 2, axis=0)[:, None] * Nt)
            bi, bj = np.unravel_index(np.argmax(sc_mat), sc_mat.shape)
            u_est[idx], v_est[idx] = uc[bi], vc[bj]
            A_mat[:, idx] = (Brc[:, bi][:, None] * Btc[:, bj][None, :]).reshape(-1)
            c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam * np.eye(cur_s), A_mat.conj().T @ y_vec)

        R = (y_vec - A_mat @ c_hat).reshape(Nr, Nt)
    return u_est, v_est, c_hat


def joint_resolvent_calibration(Y, a, u_init, v_init, Q=4, sigma2=1e-2, prior_var=0.04, mirror_sym=False, n_alt=3):
    """Implicit multiport resolvent linearization: (I + C(a)) Y = Y_iso(theta, c) + (I + C(a)) E."""
    Nr, Nt = Y.shape
    L = len(u_init)
    u_arr = u_init.copy()
    v_arr = v_init.copy()
    C_plus = np.zeros((Q, Q), dtype=np.complex128)
    C_minus = np.zeros((Q, Q), dtype=np.complex128)
    y_vec = Y.reshape(-1)
    m = Nr * Nt
    lam_c = max(1e-10, 0.05 * sigma2)
    t_idx = np.arange(Nt)[:, None]
    n_idx = np.arange(Nr)[:, None]

    # Mirror symmetry pi flips left/right steering offsets: for Q=4 (0<->1, 2<->3); for Q=8 (k <-> Q-1-k)
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)
    n_param = Q * Q if mirror_sym else 2 * Q * Q
    Phi = np.zeros((Nr * Nt, n_param), dtype=np.complex128)
    for n in range(Nr):
        if n + 1 < Nr:
            Phi[n * Nt:(n + 1) * Nt, a[n] * Q + a[n + 1]] += Y[n + 1, :]
        if n - 1 >= 0:
            if mirror_sym:
                # C_minus[a_n, a_{n-1}] = C_plus[pi(a_n), pi(a_{n-1})]
                Phi[n * Nt:(n + 1) * Nt, pi_map[a[n]] * Q + pi_map[a[n - 1]]] += Y[n - 1, :]
            else:
                Phi[n * Nt:(n + 1) * Nt, Q * Q + a[n] * Q + a[n - 1]] += Y[n - 1, :]
    Gram_Phi = Phi.conj().T @ Phi + (sigma2 * Nr / prior_var) * np.eye(n_param)

    du_cand = np.array([-0.004, -0.0015, 0.0, 0.0015, 0.004])
    dv_cand = np.array([-0.006, 0.0, 0.006])

    for _ in range(n_alt):
        Br = eval_active_responses(a, u_arr, C_plus, C_minus, Q=Q)
        Bt = np.exp(-1j * np.pi * t_idx * v_arr[None, :])
        A_mat = (Br[:, None, :] * Bt[None, :, :]).reshape(m, L)
        c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam_c * np.eye(L), A_mat.conj().T @ y_vec)

        Q_iso = np.array([isolated_pattern_q(k, u_arr, Q=Q) for k in range(Q)])
        B_iso = Q_iso[a, :] * np.exp(1j * np.pi * n_idx * u_arr[None, :])
        Diff = ((B_iso * c_hat[None, :]) @ Bt.T - Y).reshape(-1)
        theta_C = np.linalg.solve(Gram_Phi, Phi.conj().T @ Diff)
        C_plus = theta_C[:Q * Q].reshape(Q, Q)
        if mirror_sym:
            C_minus = C_plus[np.ix_(pi_map, pi_map)]
        else:
            C_minus = theta_C[Q * Q:].reshape(Q, Q)

        Br = eval_active_responses(a, u_arr, C_plus, C_minus, Q=Q)
        A_mat = (Br[:, None, :] * Bt[None, :, :]).reshape(m, L)
        c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam_c * np.eye(L), A_mat.conj().T @ y_vec)
        for idx in range(L):
            res_minus = (y_vec - A_mat @ c_hat + A_mat[:, idx] * c_hat[idx]).reshape(Nr, Nt)
            uc = np.clip(u_arr[idx] + du_cand, -np.sin(np.pi / 3), np.sin(np.pi / 3))
            vc = ((v_arr[idx] + dv_cand + 1.0) % 2.0) - 1.0
            Brc = eval_active_responses(a, uc, C_plus, C_minus, Q=Q)
            Btc = np.exp(-1j * np.pi * t_idx * vc[None, :])
            sc_mat = np.abs(Brc.conj().T @ (res_minus @ Btc.conj())) ** 2 / (np.sum(np.abs(Brc) ** 2, axis=0)[:, None] * Nt)
            bi, bj = np.unravel_index(np.argmax(sc_mat), sc_mat.shape)
            u_arr[idx], v_arr[idx] = uc[bi], vc[bj]
            A_mat[:, idx] = (Brc[:, bi][:, None] * Btc[:, bj][None, :]).reshape(-1)
            c_hat = np.linalg.solve(A_mat.conj().T @ A_mat + m * lam_c * np.eye(L), A_mat.conj().T @ y_vec)

    return u_arr, v_arr, c_hat, C_plus, C_minus


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


def run_benchmark(Q, n_sc=20, snr_db=20.0, mc_rms=0.18, mirror_sym=True, seed=20261123):
    rng = np.random.default_rng(seed + Q)
    Nr, Nt, L = 64, 8, 10
    sigma2 = 10.0 ** (-snr_db / 10.0)
    snr_lin = 10.0 ** (snr_db / 10.0)
    pi_map = np.array([1, 0, 3, 2]) if Q == 4 else np.arange(Q - 1, -1, -1)

    a_blocks = np.repeat(np.arange(Q), Nr // Q)
    a_inter = np.tile(np.arange(Q), Nr // Q)
    a_tm = thue_morse_base_q(Nr, Q=Q)
    db_base = de_bruijn_k_2(Q)
    a_db = np.tile(db_base, Nr // len(db_base))

    pos = np.arange(Nr, dtype=float)
    print(f"\n=== Benchmark Q={Q} modes on Nr={Nr}, Nt={Nt}, SNR={snr_db:.0f}dB, MC_rms={mc_rms:.2f} (mirror_sym={mirror_sym}) ===")
    for name, a in [("Blocks", a_blocks), ("Interleaved", a_inter), ("EqualMom_TM", a_tm), (f"DeBruijn_B({Q},2)", a_db)]:
        pairs = set(zip(a[:-1], a[1:]))
        diag_p = sum(1 for k in range(Q) if (k, k) in pairs)
        min_var = min(np.var(pos[a == k]) for k in range(Q))
        print(f"  Layout {name:16s}: pairs={len(pairs):2d}/{Q*Q} (homog={diag_p}/{Q}), min_var={min_var:6.2f}")

    res_hom = {k: [] for k in ["Blocks_Unc", "Inter_Unc", "Rand_Unc", "Blocks_MC", "Inter_MC", "TM_MC", "Rand_MC", "DB_MC", "DB_OracleMC"]}
    res_het = {k: [] for k in ["Inter_Unc", "Blocks_MC", "Inter_MC", "Rand_MC", "DB_MC"]}
    rates = {k: [] for k in ["Inter_Unc", "Blocks_MC", "Inter_MC", "Rand_MC", "DB_MC", "PerfectCSI"]}
    rand_cov = []

    for _ in range(n_sc):
        a_rand = rng.permutation(a_blocks)
        rand_cov.append(len(set(zip(a_rand[:-1], a_rand[1:]))))

        Cp_true = mc_rms * (rng.standard_normal((Q, Q)) + 1j * rng.standard_normal((Q, Q))) / np.sqrt(2)
        Cm_true = Cp_true[np.ix_(pi_map, pi_map)] if mirror_sym else mc_rms * (rng.standard_normal((Q, Q)) + 1j * rng.standard_normal((Q, Q))) / np.sqrt(2)

        u_true = rng.uniform(-np.sin(np.pi / 3), np.sin(np.pi / 3), L)
        v_true = rng.uniform(-1.0, 1.0, L)
        c_true = (rng.standard_normal(L) + 1j * rng.standard_normal(L)) / np.sqrt(2)
        c_true /= np.linalg.norm(c_true)
        Bt_true = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * v_true[None, :])

        H_hom_true = np.zeros((Q, Nr, Nt), dtype=np.complex128)
        for k in range(Q):
            Br = eval_active_responses(np.full(Nr, k, dtype=int), u_true, Cp_true, Cm_true, Q=Q)
            H_hom_true[k] = (Br * c_true[None, :]) @ Bt_true.T

        a_het = np.argmax(np.sum(np.abs(H_hom_true) ** 2, axis=2), axis=0)
        H_het_true = (eval_active_responses(a_het, u_true, Cp_true, Cm_true, Q=Q) * c_true[None, :]) @ Bt_true.T
        rates["PerfectCSI"].append(uplink_sum_rate(H_het_true, H_het_true, snr_lin))

        noise = np.sqrt(sigma2 / 2) * (rng.standard_normal((Nr, Nt)) + 1j * rng.standard_normal((Nr, Nt)))

        for lname, alay in [("Blocks", a_blocks), ("Inter", a_inter), ("TM", a_tm), ("Rand", a_rand), ("DB", a_db)]:
            Y = (eval_active_responses(alay, u_true, Cp_true, Cm_true, Q=Q) * c_true[None, :]) @ Bt_true.T + noise
            u0, v0, c0 = fast_pdj(Y, alay, L=L, sigma2=sigma2, Q=Q)
            Bt0 = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * v0[None, :])

            if f"{lname}_Unc" in res_hom:
                Hh0 = np.zeros((Q, Nr, Nt), dtype=np.complex128)
                for k in range(Q):
                    Br0 = isolated_pattern_q(k, u0, Q=Q)[None, :] * np.exp(1j * np.pi * np.arange(Nr)[:, None] * u0[None, :])
                    Hh0[k] = (Br0 * c0[None, :]) @ Bt0.T
                res_hom[f"{lname}_Unc"].append(np.linalg.norm(Hh0 - H_hom_true) ** 2 / np.linalg.norm(H_hom_true) ** 2)
                if lname == "Inter":
                    Q0_all = np.array([isolated_pattern_q(k, u0, Q=Q) for k in range(Q)])
                    Hhet0 = (Q0_all[a_het, :] * np.exp(1j * np.pi * np.arange(Nr)[:, None] * u0[None, :]) * c0[None, :]) @ Bt0.T
                    res_het["Inter_Unc"].append(np.linalg.norm(Hhet0 - H_het_true) ** 2 / np.linalg.norm(H_het_true) ** 2)
                    rates["Inter_Unc"].append(uplink_sum_rate(H_het_true, Hhet0, snr_lin))

            uj, vj, cj, Cph, Cmh = joint_resolvent_calibration(Y, alay, u0, v0, Q=Q, sigma2=sigma2, prior_var=mc_rms ** 2, mirror_sym=mirror_sym, n_alt=3)
            Btj = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * vj[None, :])
            Hhj = np.zeros((Q, Nr, Nt), dtype=np.complex128)
            for k in range(Q):
                Brj = eval_active_responses(np.full(Nr, k, dtype=int), uj, Cph, Cmh, Q=Q)
                Hhj[k] = (Brj * cj[None, :]) @ Btj.T
            res_hom[f"{lname}_MC"].append(np.linalg.norm(Hhj - H_hom_true) ** 2 / np.linalg.norm(H_hom_true) ** 2)

            if f"{lname}_MC" in res_het:
                Hhetj = (eval_active_responses(a_het, uj, Cph, Cmh, Q=Q) * cj[None, :]) @ Btj.T
                res_het[f"{lname}_MC"].append(np.linalg.norm(Hhetj - H_het_true) ** 2 / np.linalg.norm(H_het_true) ** 2)
                rates[f"{lname}_MC"].append(uplink_sum_rate(H_het_true, Hhetj, snr_lin))

            if lname == "DB":
                uo, vo, co = fast_pdj(Y, alay, L=L, sigma2=sigma2, Q=Q, C_plus=Cp_true, C_minus=Cm_true)
                Bto = np.exp(-1j * np.pi * np.arange(Nt)[:, None] * vo[None, :])
                Hho = np.zeros((Q, Nr, Nt), dtype=np.complex128)
                for k in range(Q):
                    Bro = eval_active_responses(np.full(Nr, k, dtype=int), uo, Cp_true, Cm_true, Q=Q)
                    Hho[k] = (Bro * co[None, :]) @ Bto.T
                res_hom["DB_OracleMC"].append(np.linalg.norm(Hho - H_hom_true) ** 2 / np.linalg.norm(H_hom_true) ** 2)

    print(f"  Random layout avg pair coverage: {np.mean(rand_cov):.1f}/{Q*Q}")
    for k, v in res_hom.items():
        print(f"  Homog NMSE {k:13s}: mean={10*np.log10(np.mean(v)):6.2f} dB | med={10*np.log10(np.median(v)):6.2f} dB")
    for k, v in res_het.items():
        print(f"  Heter NMSE {k:13s}: mean={10*np.log10(np.mean(v)):6.2f} dB | med={10*np.log10(np.median(v)):6.2f} dB")
    print("  Uplink 8-stream LMMSE Sum-Rate (bps/Hz):", {k: round(float(np.mean(v)), 2) for k, v in rates.items()})


if __name__ == "__main__":
    t0 = time.time()
    run_benchmark(Q=4, n_sc=20, snr_db=20.0, mc_rms=0.18, mirror_sym=False)
    run_benchmark(Q=8, n_sc=20, snr_db=20.0, mc_rms=0.18, mirror_sym=True)
    print(f"\nTotal runtime: {time.time() - t0:.2f}s")
