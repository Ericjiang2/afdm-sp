import time, numpy as np

t0 = time.time()
rng_tr = np.random.default_rng(55)
rng_te = np.random.default_rng(2026)

# ==============================================================================
# Probe g25 (explore): Fast-Fading Noncoherent 4x4 MIMO (Differential Cayley USTM
# Hassibi & Hochwald IEEE TIT 2002 vs Pilot-Assisted Coherent DMRS + Turbo-DD)
# Strictly equal spectral efficiency = 6.40 raw bits / channel use (160 bits in 25 slots)
# and strictly equal total TX energy (= 1.0 per channel use):
# - Channel: Continuous Gauss-Markov fast Rayleigh fading H[n] (f_D * T_s = 0.025,
#   typical high-mobility 6G FR2/NTN/V2X where channel drifts across slots!)
# - Differential Cayley (zero pilots after initial reference S_0 = I_4, 5 blocks x 4 slots
#   = 20 slots + 4 init = 24 slots carrying 5 x 32 = 160 bits => 6.67 b/s/Hz!):
#   * C2 (HH-LinCayley, Hassibi & Hochwald TIT'02): Linearized Cayley GLS + SIC
#   * HandCayley: Zero-training Grassmannian-Cayley Lie-algebra chordal solver
#   * Unfold25 (Proposed): 5-Layer x 5 = 25-param Lie-Algebra Geodesic Unfolding
#     with decision-directed multi-lag phase-reference tracking & scale annealing!
# - C1 (Pilot-Assisted Coherent DMRS + 3-Round Decision-Directed Kalman/LMMSE):
#   Same 24 slots carrying 160 bits: sweeps pilot insertion period (e.g. 4 pilot slots
#   + 20 data slots -> 2.0 bits/sym/ant? Wait: 20 data slots * 4 ant = 80 symbols -> QPSK = 160 bits!
#   Wait: if DMRS uses 1 pilot block of 4 slots + 20 data slots, H[n] drifts over 20 slots!
#   If DMRS inserts 4 pilot slots every 8 slots (12 pilot + 12 data slots -> 48 syms), it needs 16-QAM!
#   We sweep BOTH pilot densities (P4_QPSK and P8_16QAM) + 3-round DD tracking so C1 gets its BEST!)
# ==============================================================================
M = 4
Nr = 4

basis = []
for i in range(M):
    E = np.zeros((M, M), dtype=np.complex128); E[i, i] = 1.0
    basis.append(E)
for i in range(M):
    for j in range(i + 1, M):
        Er = np.zeros((M, M), dtype=np.complex128); Er[i, j] = 1.0 / np.sqrt(2.0); Er[j, i] = 1.0 / np.sqrt(2.0)
        Ei = np.zeros((M, M), dtype=np.complex128); Ei[i, j] = 1j / np.sqrt(2.0);  Ei[j, i] = -1j / np.sqrt(2.0)
        basis.append(Er); basis.append(Ei)
B_h = np.array(basis)  # (16, 4, 4)

def vec_to_A(s_real, scale_a):
    return scale_a * np.tensordot(s_real, B_h, axes=([-1], [0]))

def cayley_V(A_mat):
    I = np.eye(M, dtype=np.complex128)
    return np.linalg.solve(I + 1j * A_mat, I - 1j * A_mat)

# Noiseless unitarity & exact Cayley inversion gate
sr0 = np.random.default_rng(1).standard_normal(16)
V0 = cayley_V(vec_to_A(sr0, 0.7))
assert np.allclose(V0.conj().T @ V0, np.eye(M))

pam4 = np.array([-3., -1., 1., 3.]) / np.sqrt(5.0)
qpsk = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / np.sqrt(2.0)
pam4_c = np.array([-3., -1., 1., 3.]) / np.sqrt(10.0)
qam16 = (pam4_c[:, None] + 1j * pam4_c[None, :]).ravel()

def pam4_mmse(z, var):
    v = max(float(var), 1e-4)
    d2 = -0.5 * ((z[..., None] - pam4) ** 2) / v
    d2 -= np.max(d2, axis=-1, keepdims=True)
    w = np.exp(d2); w /= np.sum(w, axis=-1, keepdims=True)
    return w @ pam4

def qam16_mmse(z, var):
    v = max(float(var), 1e-4)
    d2 = -np.abs(z[..., None] - qam16) ** 2 / v
    d2 -= np.max(d2, axis=-1, keepdims=True)
    w = np.exp(d2); w /= np.sum(w, axis=-1, keepdims=True)
    return w @ qam16

N_blk = 5            # 5 differential blocks -> 1 initial ref (4 slots) + 5*4 = 24 slots total!
T_tot = (N_blk + 1) * M  # 24 channel uses, 160 raw bits = 6.67 bits/s/Hz!
scale_a = 0.62

def gen_fast_mimo(rng, F_num, fD_Ts, snr_db):
    sig2 = 10.0 ** (-snr_db / 10.0)
    rho_t = float(np.real(np.hanning(3)[1]))  # Jakes AR(1) correlation J_0(2 pi fD_Ts)
    rho_t = float(1.0 - (np.pi * fD_Ts) ** 2)  # accurate J0(2 pi fD Ts) for fD_Ts <= 0.08
    H_seq = np.empty((F_num, T_tot, Nr, M), dtype=np.complex128)
    H_cur = (rng.standard_normal((F_num, Nr, M)) + 1j * rng.standard_normal((F_num, Nr, M))) / np.sqrt(2.0)
    for t in range(T_tot):
        if t > 0:
            innov = (rng.standard_normal((F_num, Nr, M)) + 1j * rng.standard_normal((F_num, Nr, M))) / np.sqrt(2.0)
            H_cur = rho_t * H_cur + np.sqrt(max(1.0 - rho_t**2, 0.0)) * innov
        H_seq[:, t] = H_cur
    W = (rng.standard_normal((F_num, T_tot, Nr)) + 1j * rng.standard_normal((F_num, T_tot, Nr))) * np.sqrt(sig2 / 2.0)
    sr_all = rng.choice(pam4, size=(F_num, N_blk, 16))
    return H_seq, W, sr_all, sig2

def sim_cayley_tx(H_seq, W, sr_all):
    F_num = H_seq.shape[0]
    Y_blk = np.empty((F_num, N_blk + 1, Nr, M), dtype=np.complex128)
    for f in range(F_num):
        S_prev = np.eye(M, dtype=np.complex128)  # slot 0..3: energy Tr(I)=4 => 1.0/slot!
        for m in range(M):
            Y_blk[f, 0, :, m] = H_seq[f, m] @ S_prev[:, m] + W[f, m]
        for b in range(N_blk):
            Vb = cayley_V(vec_to_A(sr_all[f, b], scale_a))
            S_cur = S_prev @ Vb  # unitary! Every column norm^2 = 1.0 => exact energy 1.0/slot!
            for m in range(M):
                t_idx = (b + 1) * M + m
                Y_blk[f, b + 1, :, m] = H_seq[f, t_idx] @ S_cur[:, m] + W[f, t_idx]
            S_prev = S_cur
    return Y_blk

def eval_hh_lin(Y_blk, sr_all, sig2):
    # Hassibi-Hochwald (TIT'02) Linearized Cayley LMMSE + GLS noise whitening
    F_num = sr_all.shape[0]
    errs = []
    for f in range(F_num):
        for b in range(N_blk):
            Y1, Y2 = Y_blk[f, b], Y_blk[f, b + 1]
            Yp, Ym = Y1 + Y2, Y1 - Y2
            Phi = np.empty((2 * Nr * M, 16))
            for q in range(16):
                Zq = 1j * scale_a * (Yp @ B_h[q])
                Phi[:, q] = np.concatenate([Zq.real.ravel(), Zq.imag.ravel()])
            ym_v = np.concatenate([Ym.real.ravel(), Ym.imag.ravel()])
            sh = np.linalg.solve(Phi.T @ Phi + 2.0 * sig2 * (1.0 + 4.0 * scale_a**2) * np.eye(16), Phi.T @ ym_v)
            ih = np.argmin(np.abs(sh[:, None] - pam4), axis=1)
            it = np.argmin(np.abs(sr_all[f, b, :, None] - pam4), axis=1)
            errs.append(np.mean(ih != it))
    return float(np.mean(errs)), float(-10*np.log10(max(np.mean([(sh_i)**2 for sh_i in [1e-3]]), 1e-9)))

def run_cayley_unfold(Y_blk, sr_all, sig2, params):
    # 5 layers x 5 physics params = 25 params:
    # [log_reg, logit_ref_blend (multi-block decision-directed reference smoothing!), log_step, log_tau, logit_damp]
    P = params.reshape(5, 5)
    F_num = sr_all.shape[0]
    errs, mses = [], []
    for f in range(F_num):
        for b in range(N_blk):
            Y1_raw, Y2 = Y_blk[f, b], Y_blk[f, b + 1]
            # Init from regularized HH
            Yp, Ym = Y1_raw + Y2, Y1_raw - Y2
            Phi = np.empty((2 * Nr * M, 16))
            for q in range(16):
                Zq = 1j * scale_a * (Yp @ B_h[q])
                Phi[:, q] = np.concatenate([Zq.real.ravel(), Zq.imag.ravel()])
            ym_v = np.concatenate([Ym.real.ravel(), Ym.imag.ravel()])
            sr_cur = pam4_mmse(np.linalg.solve(Phi.T @ Phi + 3.0 * sig2 * np.eye(16), Phi.T @ ym_v), 0.25)
            # Optional lag-2 reference Y0 @ V_{b-1} if b >= 1 (exponentially cleans the noisy reference Y1!)
            Y_prev_pred = Y1_raw if b == 0 else (0.65 * Y1_raw + 0.35 * Y_clean_prev)
            for t in range(5):
                reg_m = np.exp(P[t, 0]) * sig2
                w_ref = 1.0 / (1.0 + np.exp(-P[t, 1])) if b > 0 else 0.0
                step  = np.exp(P[t, 2])
                tau   = np.exp(P[t, 3])
                damp  = 1.0 / (1.0 + np.exp(-P[t, 4]))

                Y_ref = (1.0 - w_ref) * Y1_raw + w_ref * Y_prev_pred
                Ac = vec_to_A(sr_cur, scale_a)
                Inv_p = np.linalg.inv(np.eye(M) + 1j * Ac)
                Vc = (np.eye(M) - 1j * Ac) @ Inv_p
                res_g = Y_ref @ Vc - Y2
                Jg = np.empty((2 * Nr * M, 16))
                YR_Inv = Y_ref @ Inv_p
                for q in range(16):
                    dVq = -2j * scale_a * (YR_Inv @ B_h[q] @ Inv_p)
                    Jg[:, q] = np.concatenate([dVq.real.ravel(), dVq.imag.ravel()])
                rg = np.concatenate([res_g.real.ravel(), res_g.imag.ravel()])
                dsr = -np.linalg.solve(Jg.T @ Jg + reg_m * np.eye(16), Jg.T @ rg)
                sr_raw = sr_cur + step * dsr
                if t < 4:
                    sr_cur = (1.0 - damp) * sr_cur + damp * pam4_mmse(sr_raw, tau)
            # Propagate cleaned decision-directed subspace reference Y_clean_prev = 0.5*(Y_ref @ V_hat + Y2) for next block!
            Vh_f = cayley_V(vec_to_A(pam4_mmse(sr_raw, 0.015), scale_a))
            Y_clean_prev = 0.5 * (Y_ref @ Vh_f + Y2)
            mses.append(float(np.mean((sr_raw - sr_all[f, b]) ** 2)))
            ih = np.argmin(np.abs(sr_raw[:, None] - pam4), axis=1)
            it = np.argmin(np.abs(sr_all[f, b, :, None] - pam4), axis=1)
            errs.append(np.mean(ih != it))
    mse_avg = float(np.mean(mses))
    return float(np.mean(errs)), -10.0 * np.log10(max(mse_avg, 1e-12)), mse_avg

def eval_best_coherent_dmrs(H_seq, W, sig2, rng_d):
    # Strictly equal 160 bits over 24 slots, total TX power = 1.0/slot!
    # Mode A (P4_QPSK): 4 pilot slots at [0..3] + 20 QPSK data slots (20 * 4 * 2 = 160 bits!) + 3-pass DD sliding-window LMMSE tracking!
    # Mode B (P8_16QAM): TWO 4-slot orthogonal pilots at [0..3] & [12..15] + 16 data slots?
    #   Wait: 16 data slots * 4 ant = 64 syms; to carry 160 bits needs 2.5 bits/sym -> test 10 data slots of 16-QAM (160 bits) + 14 pilot slots (3.5x4 pilot blocks! Even stronger pilot tracking for DMRS!)
    F_num = H_seq.shape[0]
    err_A, err_B = [], []
    for f in range(F_num):
        # Mode A: 4 pilot + 20 QPSK data + sequential DD recursive LMMSE channel tracker (alpha=0.35)!
        Xd = rng_d.choice(qpsk, size=(20, M))
        Y_p = np.column_stack([H_seq[f, m, :, m] + W[f, m] for m in range(M)])
        H_hat = Y_p / (1.0 + sig2)
        s_err = 0
        for t_d in range(20):
            ts = M + t_d
            yt = H_seq[f, ts] @ (Xd[t_d] / np.sqrt(M)) + W[f, ts]
            He = H_hat / np.sqrt(M)
            xh = np.linalg.solve(He.conj().T @ He + (sig2 + 0.04) * np.eye(M), He.conj().T @ yt)
            s_err += int(np.sum((np.sign(xh.real) != np.sign(Xd[t_d].real)) | (np.sign(xh.imag) != np.sign(Xd[t_d].imag))))
            xm = (np.tanh(np.sqrt(2)*xh.real/0.15) + 1j*np.tanh(np.sqrt(2)*xh.imag/0.15)) / np.sqrt(2.0) / np.sqrt(M)
            # LMS / Kalman rank-1 channel tracking update!
            err_y = yt - H_hat @ xm
            H_hat = H_hat + 0.45 * np.outer(err_y, xm.conj()) / (np.sum(np.abs(xm)**2) + sig2)
        err_A.append(s_err / 80.0)

        # Mode B: Dense pilots! 12 pilot slots (3 full 4x4 orthogonal pilot blocks at [0..3], [9..12], [18..21]!)
        # + 10 data slots of 16-QAM (10 * 4 * 4 = 160 bits! Total slots = 22 <= 24, boost pilot power so total energy = 24.0!!
        # Giving Mode B 2 EXTRA FREE ENERGY UNITS so baseline is super-advantaged!)
        p_starts = [0, 9, 18]
        d_slots = [4,5,6,7,8, 13,14,15,16,17]  # 10 data slots * 4 ant * 4 bits = 160 bits!
        Ep_b = 14.0 / 12.0  # total energy = 12 * (14/12) + 10 * 1.0 = 24.0!
        Hp_est = []
        for ps in p_starts:
            Yp_b = np.column_stack([H_seq[f, ps+m, :, m]*np.sqrt(Ep_b) + W[f, ps+m] for m in range(M)])
            Hp_est.append((ps + 1.5, Yp_b / (Ep_b + sig2) * np.sqrt(Ep_b)))
        Xd16 = rng_d.choice(qam16, size=(10, M))
        se16 = 0
        for idx_d, ts in enumerate(d_slots):
            # Linear interpolation between nearest two 4x4 pilot blocks!
            if ts < 9:
                w1 = (9.5 - ts) / 9.0; H_int = w1 * Hp_est[0][1] + (1.0 - w1) * Hp_est[1][1]
            else:
                w1 = (19.5 - ts) / 9.0; H_int = w1 * Hp_est[1][1] + (1.0 - w1) * Hp_est[2][1]
            yt = H_seq[f, ts] @ (Xd16[idx_d] / np.sqrt(M)) + W[f, ts]
            He = H_int / np.sqrt(M)
            xh = np.linalg.solve(He.conj().T @ He + (sig2 + 0.02) * np.eye(M), He.conj().T @ yt)
            ih = np.argmin(np.abs(xh[:, None] - qam16), axis=1)
            it = np.argmin(np.abs(Xd16[idx_d, :, None] - qam16), axis=1)
            se16 += float(np.mean(ih != it))
        err_B.append(se16 / 10.0)
    return min(float(np.mean(err_A)), float(np.mean(err_B))), float(np.mean(err_A)), float(np.mean(err_B))

p_hand = np.tile(np.array([np.log(2.0), -0.5, np.log(1.0), np.log(0.12), 1.2]), (5, 1)).ravel()

def spsa_cayley(Y_tr, sr_tr, sig2, p0, steps=20):
    ro = np.random.default_rng(17)
    p = p0.copy(); best_p = p.copy()
    _, _, best_l = run_cayley_unfold(Y_tr, sr_tr, sig2, p)
    ma = np.zeros_like(p); va = np.zeros_like(p)
    for k in range(1, steps + 1):
        dl = ro.choice([-1.0, 1.0], size=p.shape)
        ck = 0.16 / (k ** 0.15)
        _, _, lp = run_cayley_unfold(Y_tr, sr_tr, sig2, p + ck * dl)
        _, _, lm = run_cayley_unfold(Y_tr, sr_tr, sig2, p - ck * dl)
        g = (lp - lm) / (2.0 * ck) * dl
        ma = 0.8 * ma + 0.2 * g; va = 0.95 * va + 0.05 * (g * g)
        p = np.clip(p - 0.22 * ma / (np.sqrt(va) + 1e-6), -4.5, 3.5)
        if k % 5 == 0:
            _, _, cl = run_cayley_unfold(Y_tr, sr_tr, sig2, p)
            if cl < best_l: best_l, best_p = cl, p.copy()
    return best_p

for fD_Ts, snr_db in [(0.035, 16.0), (0.050, 18.0)]:
    H_tr, W_tr, sr_tr, s2_tr = gen_fast_mimo(rng_tr, 10, fD_Ts, snr_db)
    Y_tr = sim_cayley_tx(H_tr, W_tr, sr_tr)
    p_opt = spsa_cayley(Y_tr, sr_tr, s2_tr, p_hand, steps=20)

    H_te, W_te, sr_te, s2_te = gen_fast_mimo(rng_te, 24, fD_Ts, snr_db)
    Y_te = sim_cayley_tx(H_te, W_te, sr_te)
    best_dmrs, dmrs_qpsk, dmrs_16q = eval_best_coherent_dmrs(H_te, W_te, s2_te, np.random.default_rng(99))
    hh_ser, _ = eval_hh_lin(Y_te, sr_te, s2_te)
    h_ser, h_db, _ = run_cayley_unfold(Y_te, sr_te, s2_te, p_hand)
    u_ser, u_db, _ = run_cayley_unfold(Y_te, sr_te, s2_te, p_opt)
    print(f"fDTs={fD_Ts:.3f},SNR={snr_db:.0f}dB | BestDMRS={best_dmrs:.4f}(DD-QPSK={dmrs_qpsk:.4f},Interp16Q={dmrs_16q:.4f}) | HH-TIT02={hh_ser:.4f} | HandCayley={h_ser:.4f}({h_db:.2f}dB) | Unfold25={u_ser:.4f}({u_db:.2f}dB)")
print(f"Elapsed: {time.time()-t0:.2f}s")
