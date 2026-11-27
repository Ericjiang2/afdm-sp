import os
import sys
import time
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h_r13_stageA_common import (
    build_daft_matrices, idaft_col, td_path_matrix, build_wideband_user_channel,
    ula_steering, qpsk_alphabet, nearest_symbol_ser,
)
from h_r13_stageA_g1_g4 import quantize_dac


# =====================================================================
# Part 1: #4 G3-S2-3 (1-bit DAC Quadratic-Residue Coset Group-Flip vs Single-Bit Flip HC!)
# =====================================================================
def probe_g3_s2_3(seed: int):
    rng = np.random.default_rng(seed)
    Nt, K, Pk, N, Q = 16, 3, 3, 64, 4  # Q=4 blocks for fast <5s probe
    c1 = 3.0 / (2.0 * N)               # 2*N*c1 = 3; with L=16, 2N=128 divides L^2=256! B = N/L = 4
    c2 = 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_blk = float(N)
    sigma2 = 10.0 ** (-20.0 / 10.0)
    a_tar = ula_steering(Nt, 36.0)
    user_centers = [-45.0, -12.0, 18.0]

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
    H_all_td = np.vstack([H_users_af[k] @ A_kron for k in range(K)])  # (K*N, N*Nt)
    alph = qpsk_alphabet()
    d_cpi = alph[rng.integers(0, 4, size=(Q, K, N))]
    noise_cpi = np.sqrt(sigma2 / 2.0) * (rng.standard_normal((Q, K, N)) + 1j * rng.standard_normal((Q, K, N)))

    G_rzf = H_all_td.conj().T @ np.linalg.inv(H_all_td @ H_all_td.conj().T + K * sigma2 * np.eye(K * N))
    s0 = np.zeros((N, Nt), dtype=np.complex128)
    s0[0, :] = a_tar / np.sqrt(Nt)
    x0_rad = idaft_col(s0, lc1, lc2).reshape(N * Nt)
    x_rad_null = x0_rad - H_all_td.conj().T @ np.linalg.solve(H_all_td @ H_all_td.conj().T + 1e-9 * np.eye(K * N), H_all_td @ x0_rad)
    x_rad_null /= np.linalg.norm(x_rad_null)

    # Exact joint objective per block q (soft CI hinge + causal cross-block lag sidelobe):
    scale_1bit = np.sqrt(P_blk / float(2 * N * Nt))
    lags = [-3, -2, -1, 1, 2, 3]

    def block_loss(b_real, b_imag, d_vec, mem_lags):
        xv = scale_1bit * (b_real + 1j * b_imag)
        y = H_all_td @ xv
        rot = y * np.conj(d_vec)
        tau = 0.45
        v1 = np.maximum(0.0, tau - (np.real(rot) + np.imag(rot)))
        v2 = np.maximum(0.0, tau - (np.real(rot) - np.imag(rot)))
        loss_c = float(np.sum(v1 ** 2 + v2 ** 2))
        X_m = xv.reshape(N, Nt)
        u_q = X_m @ np.conj(a_tar)
        loss_r = 0.0
        for dl in lags:
            c_dl = np.vdot(np.roll(u_q, dl), u_q)
            loss_r += 0.008 * float(abs(mem_lags[dl] + c_dl) ** 2)
        return loss_c + loss_r

    X_buss = np.zeros((Q, N, Nt), dtype=np.complex128)
    X_hc1 = np.zeros((Q, N, Nt), dtype=np.complex128)
    X_coset = np.zeros((Q, N, Nt), dtype=np.complex128)
    mem_hc = {dl: 0.0 + 0.0j for dl in lags}
    mem_co = {dl: 0.0 + 0.0j for dl in lags}
    escaped_count = 0

    L = 16
    B = N // L  # B = 4 samples per quadratic-residue coset!
    # All 15 non-empty flip masks on B=4 samples in a coset:
    masks = [np.array([(m >> j) & 1 for j in range(B)], dtype=bool) for m in range(1, 1 << B)]

    for q in range(Q):
        dv = d_cpi[q].reshape(K * N)
        x_init = G_rzf @ dv
        x_init = x_init / np.linalg.norm(x_init) * np.sqrt(0.65 * P_blk) + np.sqrt(0.35 * P_blk) * np.exp(1j * 0.43 * q) * x_rad_null
        Xq0 = quantize_dac(x_init.reshape(N, Nt), 1, P_blk)
        X_buss[q] = Xq0

        # 1) Fast vectorized Single-Bit Flip Hill-Climbing (rank-1 column update on y = H_all_td @ xv and u_q = X_m @ a_tar^*!)
        br = np.sign(np.real(Xq0.reshape(N * Nt)))
        bi = np.sign(np.imag(Xq0.reshape(N * Nt)))
        xv = scale_1bit * (br + 1j * bi)
        y_cur = H_all_td @ xv
        u_cur = xv.reshape(N, Nt) @ np.conj(a_tar)

        def fast_eval(y_v, u_v, mem_d):
            rot = y_v * np.conj(dv)
            v1 = np.maximum(0.0, 0.45 - (np.real(rot) + np.imag(rot)))
            v2 = np.maximum(0.0, 0.45 - (np.real(rot) - np.imag(rot)))
            lc = float(np.sum(v1 * v1 + v2 * v2))
            lr = 0.0
            for dl in lags:
                lr += 0.008 * float(abs(mem_d[dl] + np.vdot(np.roll(u_v, dl), u_v)) ** 2)
            return lc + lr

        # Run 2 full sweeps of single-bit HC to reach true 1-bit local minimum!
        a_conj = np.conj(a_tar)
        cur_loss = fast_eval(y_cur, u_cur, mem_hc)
        for _sweep in range(2):
            improved = False
            for idx in range(N * Nt):
                n_row, nt_col = divmod(idx, Nt)
                # Try real flip: delta = -2 * scale_1bit * br[idx]
                dx = -2.0 * scale_1bit * br[idx]
                y_try = y_cur + dx * H_all_td[:, idx]
                u_try = u_cur.copy()
                u_try[n_row] += dx * a_conj[nt_col]
                nl = fast_eval(y_try, u_try, mem_hc)
                if nl < cur_loss - 1e-9:
                    br[idx] = -br[idx]
                    y_cur, u_cur, cur_loss = y_try, u_try, nl
                    improved = True
                # Try imag flip: delta = -2j * scale_1bit * bi[idx]
                dxj = -2.0j * scale_1bit * bi[idx]
                y_try = y_cur + dxj * H_all_td[:, idx]
                u_try = u_cur.copy()
                u_try[n_row] += dxj * a_conj[nt_col]
                nl = fast_eval(y_try, u_try, mem_hc)
                if nl < cur_loss - 1e-9:
                    bi[idx] = -bi[idx]
                    y_cur, u_cur, cur_loss = y_try, u_try, nl
                    improved = True
            if not improved:
                break
        X_hc1[q] = (scale_1bit * (br + 1j * bi)).reshape(N, Nt)
        for dl in lags:
            mem_hc[dl] += np.vdot(np.roll(u_cur, dl), u_cur)

        # 2) Sol #1's EXACT DECISIVE TEST: From a true 1-bit HC local minimum (with mem_co == mem_hc on q=0, or run 1-bit HC on mem_co first!),
        # check if B=4 QR-coset multi-bit flips strictly escape the 1-bit HC local minimum!
        br_c = np.sign(np.real(Xq0.reshape(N * Nt)))
        bi_c = np.sign(np.imag(Xq0.reshape(N * Nt)))
        xv_c = scale_1bit * (br_c + 1j * bi_c)
        yc = H_all_td @ xv_c
        uc = xv_c.reshape(N, Nt) @ a_conj
        closs = fast_eval(yc, uc, mem_co)
        for _sweep in range(2):
            imp = False
            for idx in range(N * Nt):
                nr, nc = divmod(idx, Nt)
                dx = -2.0 * scale_1bit * br_c[idx]
                yt = yc + dx * H_all_td[:, idx]
                ut = uc.copy(); ut[nr] += dx * a_conj[nc]
                nl = fast_eval(yt, ut, mem_co)
                if nl < closs - 1e-9:
                    br_c[idx] = -br_c[idx]; yc, uc, closs = yt, ut, nl; imp = True
                dxj = -2.0j * scale_1bit * bi_c[idx]
                yt = yc + dxj * H_all_td[:, idx]
                ut = uc.copy(); ut[nr] += dxj * a_conj[nc]
                nl = fast_eval(yt, ut, mem_co)
                if nl < closs - 1e-9:
                    bi_c[idx] = -bi_c[idx]; yc, uc, closs = yt, ut, nl; imp = True
            if not imp:
                break
        loss_at_1bit_opt = closs
        br_m = br_c.reshape(N, Nt)
        bi_m = bi_c.reshape(N, Nt)
        for r in range(L):
            coset_rows = r + np.arange(B) * L
            for nt in range(Nt):
                cols_idx = coset_rows * Nt + nt
                H_sub = H_all_td[:, cols_idx]  # (K*N, B)
                for msk in masks:
                    if int(np.sum(msk)) < 2:
                        continue
                    rf = coset_rows[msk]
                    dx_vec = -2.0 * scale_1bit * br_m[rf, nt]
                    yt = yc + H_sub[:, msk] @ dx_vec
                    ut = uc.copy(); ut[rf] += dx_vec * a_conj[nt]
                    nl = fast_eval(yt, ut, mem_co)
                    if nl < closs - 1e-7:
                        br_m[rf, nt] *= -1.0
                        yc, uc, closs = yt, ut, nl
        if closs < loss_at_1bit_opt - 1e-5:
            escaped_count += 1
        X_coset[q] = (scale_1bit * (br_m.ravel() + 1j * bi_m.ravel())).reshape(N, Nt)
        for dl in lags:
            mem_co[dl] += np.vdot(np.roll(uc, dl), uc)

    def eval_g3(X_cpi):
        sers = []
        for q in range(Q):
            xv = X_cpi[q].reshape(N * Nt)
            for k in range(K):
                zk = H_all_td[k * N:(k + 1) * N] @ xv + noise_cpi[q, k]
                sers.append(nearest_symbol_ser(zk, d_cpi[q, k], alph))
        u_t = np.einsum("qni,i->qn", X_cpi, np.conj(a_tar))
        T_s = td_path_matrix(N, c1, 1, 0.05)
        T_w = td_path_matrix(N, c1, 3, 0.28)
        q_idx = np.arange(Q, dtype=np.float64)
        phi_w = np.exp(1j * 2.0 * np.pi * 0.28 * 1.15 * q_idx)[:, None] * (u_t @ T_w.T)
        echo_s = (10.0 ** (23.0 / 20.0)) * np.exp(1j * 2.0 * np.pi * 0.05 * 1.15 * q_idx)[:, None] * (u_t @ T_s.T)
        sig = abs(np.sum(np.conj(phi_w) * phi_w)) ** 2
        leak = abs(np.sum(np.conj(phi_w) * echo_s)) ** 2
        ws = 10.0 * np.log10(max(sig / max(leak + 0.1 * float(np.sum(np.abs(phi_w) ** 2)), 1e-15), 1e-15))
        return float(np.mean(sers)), ws

    sb, wb = eval_g3(X_buss)
    sh, wh = eval_g3(X_hc1)
    sc, wc = eval_g3(X_coset)
    return {
        "bussgang_ser": sb, "bussgang_wsinr": wb,
        "hc1bit_ser": sh, "hc1bit_wsinr": wh,
        "coset_after_hc_ser": sc, "coset_after_hc_wsinr": wc,
        "coset_escaped_frac": escaped_count / float(Q),
    }


# =====================================================================
# Part 2: #6 G6-S1-1 (Fair Vectorized Batched Liu 2607 WMMSE-MM Timing vs Polyphase PCG!)
# =====================================================================
def solve_batched_perbin_qcqp(Tw_diag, Bk_diag, W_ref, a_tar, gamma_s, p_max):
    """
    FAST vectorized KKT solver exploiting Liu 2607's exact per-bin block-diagonal structure:
    Tw_diag is (N, Nt, Nt) -> batched np.linalg.eigh on (N, 6, 6) instead of (384, 384)!
    """
    N, Nt, _ = Tw_diag.shape
    M_str = W_ref.shape[2]
    H_sym = 0.5 * (Tw_diag + np.swapaxes(Tw_diag.conj(), -1, -2)) + 1e-10 * np.eye(Nt)[None, :, :]
    eigvals, U = np.linalg.eigh(H_sym)  # (N, Nt), (N, Nt, Nt) - takes < 0.1 ms!
    eigvals = np.maximum(eigvals, 1e-10)

    A_outer = np.outer(a_tar, np.conj(a_tar))  # (Nt, Nt)
    A_vec = np.einsum("ij,njm->nim", A_outer, W_ref)  # (N, Nt, K+1)
    B_rhs = np.zeros_like(W_ref)
    B_rhs[:, :, :-1] = Bk_diag

    c_ref = float(np.real(np.sum(np.conj(W_ref) * A_vec)))
    rhs_req = 0.5 * (gamma_s + c_ref)

    UB = np.einsum("nij,nim->njm", U.conj(), B_rhs)
    UA = np.einsum("nij,nim->njm", U.conj(), A_vec)

    def solve_lam(mu):
        num = UB + mu * UA
        num_sq = np.abs(num) ** 2  # (N, Nt, M_str)
        if float(np.sum(num_sq / ((eigvals + 1e-11)[:, :, None] ** 2))) <= p_max:
            return num / (eigvals + 1e-11)[:, :, None]
        lo, hi = 1e-11, 1.0
        while float(np.sum(num_sq / ((eigvals + hi)[:, :, None] ** 2))) > p_max:
            hi *= 4.0
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            if float(np.sum(num_sq / ((eigvals + mid)[:, :, None] ** 2))) > p_max:
                lo = mid
            else:
                hi = mid
        return num / (eigvals + hi)[:, :, None]

    UW0 = solve_lam(0.0)
    if float(np.real(np.sum(np.conj(UA) * UW0))) >= rhs_req:
        return np.einsum("nij,njm->nim", U, UW0)

    mu_lo, mu_hi = 0.0, 1.0
    for _ in range(25):
        if float(np.real(np.sum(np.conj(UA) * solve_lam(mu_hi)))) >= rhs_req:
            break
        mu_hi *= 3.0
    for _ in range(36):
        mu_mid = 0.5 * (mu_lo + mu_hi)
        if float(np.real(np.sum(np.conj(UA) * solve_lam(mu_mid)))) < rhs_req:
            mu_lo = mu_mid
        else:
            mu_hi = mu_mid
    UW = solve_lam(mu_hi)
    return np.einsum("nij,njm->nim", U, UW)


def probe_g6_s1_1(N: int = 64, seed: int = 8600):
    rng = np.random.default_rng(seed)
    Nt, K, Pk, Q = 6, 3, 3, 8
    c1 = 3.0 / (2.0 * N)
    c2 = 1.0 / (2.0 * N)
    A, lc1, lc2, F_dft = build_daft_matrices(N, c1, c2)
    P_max = float(N)
    sigma2 = 0.01
    gamma_s = 0.30 * Nt * P_max
    a_tar = ula_steering(Nt, 40.0, unit_norm=False)
    user_centers = [-45.0, -10.0, 20.0]

    users_paths = []
    for k in range(K):
        ells = rng.choice(7, size=Pk, replace=False)
        paths = [(
            (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0 * Pk),
            int(ells[p]), float(rng.uniform(-0.85, 0.85)), float(user_centers[k] + rng.uniform(-18.0, 18.0))
        ) for p in range(Pk)]
        users_paths.append(paths)

    # Fair pre-cached H_kq as (K, Q, N, N, Nt) tensor!
    H_tens = np.zeros((K, Q, N, N, Nt), dtype=np.complex128)
    for q in range(Q):
        for k in range(K):
            q_paths = [(g * np.exp(1j * 2.0 * np.pi * nu * 1.15 * q), ell, nu, ang) for (g, ell, nu, ang) in users_paths[k]]
            Hkq = build_wideband_user_channel(A, F_dft, c1, Nt, q_paths, 0.0)
            H_tens[k, q] = Hkq.reshape(N, N, Nt)

    W_init = np.zeros((N, Nt, K + 1), dtype=np.complex128)
    for m in range(N):
        for k in range(K):
            W_init[m, :, k] = ula_steering(Nt, user_centers[k], True) * np.sqrt(0.65 / K)
        W_init[m, :, K] = (a_tar / np.sqrt(Nt)) * np.sqrt(0.35)

    # RunSol #1's FAIR VECTORIZED Liu 2607 exact baseline (batched solve + diagonal-block einsum + batched 6x6 KKT!)
    W = W_init.copy()
    I_N = np.eye(N, dtype=np.complex128)[None, None, :, :]
    t0 = time.perf_counter()
    for _ in range(15):
        # HW[k, q, r, m, s] = sum_i H_tens[k, q, r, m, i] * W[m, i, s] -> (K, Q, N, N, K+1)
        HW = np.einsum("kqrmi,mis->kqrms", H_tens, W)
        # C_kq = sigma2 I + sum_{s} HW[..., s] @ HW[..., s]^H -> (K, Q, N, N)
        Ck = sigma2 * I_N + np.einsum("kqrms,kqpms->kqrp", HW, HW.conj())
        # Desired HW_des[k, q, r, m] = HW[k, q, r, m, k]
        HW_des = np.stack([HW[k, :, :, :, k] for k in range(K)], axis=0)  # (K, Q, N, N)
        Uk = np.linalg.solve(Ck, HW_des)  # batched solve of 24 (N x N) systems in LAPACK C!
        # Sigma_int = Ck - HW_des @ HW_des^H; note U_k M_k U_k^H = Sigma_int^{-1} - C_k^{-1} (Woodbury identity cited by Sol #1!)
        Sig_int = Ck - np.einsum("kqrm,kqpm->kqrp", HW_des, HW_des.conj())
        J_mat = np.linalg.inv(Sig_int) - np.linalg.inv(Ck)  # (K, Q, N, N)
        # Per-bin diagonal block: Tw_diag[m, i, j] = sum_{k,q,r,p} H^*[k,q,r,m,i] J_mat[k,q,r,p] H[k,q,p,m,j]
        HJ = np.einsum("kqrmi,kqrp->kqpmi", H_tens.conj(), J_mat)
        Tw_diag = np.einsum("kqpmi,kqpmj->mij", HJ, H_tens) / float(Q * np.log(2.0))
        # Bk_diag[m, i, k]: Uk @ Mk where Mk = (I - HW_des^H Uk)^{-1}
        Ek = I_N - np.einsum("kqrm,kqrm->kqm", HW_des.conj(), Uk)[:, :, :, None] * 0.0  # compute exact Ek:
        Ek_full = I_N - np.einsum("kqrm,kqrn->kqmn", HW_des.conj(), Uk)
        Ek_full = 0.5 * (Ek_full + np.swapaxes(Ek_full.conj(), -1, -2)) + 1e-9 * I_N
        UM = np.linalg.solve(np.swapaxes(Ek_full, -1, -2), np.swapaxes(Uk, -1, -2))  # (K, Q, N_col, N_row) -> UM^T = Uk @ Ek^{-1}
        UM = np.swapaxes(UM, -1, -2)  # (K, Q, N, N) = Uk @ Mk
        Bk_diag = np.einsum("kqrmi,kqrm->mik", H_tens.conj(), UM) / float(Q * np.log(2.0))
        W = solve_batched_perbin_qcqp(Tw_diag, Bk_diag, W, a_tar, gamma_s, P_max)
    t_vec_liu_ms = (time.perf_counter() - t0) * 1e3

    # Compute final rate
    HW = np.einsum("kqrmi,mis->kqrms", H_tens, W)
    sr = 0.0
    for k in range(K):
        for q in range(Q):
            Ck = sigma2 * np.eye(N) + sum(HW[k, q, :, :, s] @ HW[k, q, :, :, s].conj().T for s in range(K + 1) if s != k)
            hd = HW[k, q, :, :, k]
            _, ld = np.linalg.slogdet(np.eye(N) + np.linalg.solve(Ck, hd @ hd.conj().T))
            sr += float(np.real(ld) / np.log(2.0)) / float(N * Q)
    Rx = np.einsum("mis,mjs->ij", W, W.conj())
    bp_ratio = float(np.real(a_tar.conj() @ Rx @ a_tar)) / gamma_s
    return {"N": N, "fair_vec_liu26_time_ms": t_vec_liu_ms, "fair_vec_liu26_sr": sr, "bp_ratio": bp_ratio}


def main():
    t0 = time.time()
    g3_rows = [probe_g3_s2_3(8400 + i) for i in range(2)]
    g3_avg = {k: float(np.mean([r[k] for r in g3_rows])) for k in g3_rows[0]}
    g6_64 = probe_g6_s1_1(64, 8601)
    g6_128 = probe_g6_s1_1(128, 8602)
    print(json.dumps({
        "elapsed_sec": time.time() - t0,
        "G3_S2_3": g3_avg,
        "G6_fair_vec_liu26_baseline": {"N64": g6_64, "N128": g6_128},
    }, indent=2))


if __name__ == "__main__":
    main()
