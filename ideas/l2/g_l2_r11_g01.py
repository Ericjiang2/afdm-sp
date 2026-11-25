import sys
print(sys.executable, flush=True)

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scipy.stats import beta as sp_beta, t as sp_t

def rrc_cont(t_arr, alpha, half_span=4.0):
    t = np.asarray(t_arr, dtype=float)
    out = np.zeros_like(t, dtype=float)
    mask = np.abs(t) <= half_span + 1e-12
    tm = t[mask]
    hm = np.zeros_like(tm)
    z0 = np.abs(tm) < 1e-12
    hm[z0] = 1.0 - alpha + 4.0 * alpha / np.pi
    if alpha > 0:
        zs = (~z0) & (np.abs(np.abs(tm) - 1.0 / (4.0 * alpha)) < 1e-9)
        hm[zs] = (alpha / np.sqrt(2.0)) * (
            (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * alpha))
            + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * alpha))
        )
    else:
        zs = np.zeros_like(z0)
    reg = (~z0) & (~zs)
    tr = tm[reg]
    hm[reg] = (
        np.sin(np.pi * tr * (1.0 - alpha))
        + 4.0 * alpha * tr * np.cos(np.pi * tr * (1.0 + alpha))
    ) / (np.pi * tr * (1.0 - (4.0 * alpha * tr) ** 2))
    out[mask] = hm
    return out

def build_afdm(N, two_Nc1, c2=0.0):
    c1 = two_Nc1 / (2.0 * N)
    n = np.arange(N)
    L1 = np.exp(-1j * 2 * np.pi * c1 * (n ** 2))
    L2 = np.exp(-1j * 2 * np.pi * c2 * (n ** 2))
    F = np.fft.fft(np.eye(N), axis=0) / np.sqrt(N)
    A = (L2[:, None] * F) * L1[None, :]
    return c1, L1, F, A

def yin24_epa_dr(Y_rx, N, Nbs, K, pilots, l_max, alpha_max, k_nu, two_Nc1, pilot_amp, thresh=0.0):
    H_list = []
    m_prime = np.arange(N)
    for u in range(K):
        pu = pilots[u]
        H_u = np.zeros((Nbs, N, N), dtype=complex)
        for ant in range(Nbs):
            for l_int in range(l_max + 1):
                center = pu - two_Nc1 * l_int
                ph_col = np.exp(-1j * 2 * np.pi * l_int * (m_prime - pu) / N)
                for d_al in range(-(alpha_max + k_nu), alpha_max + k_nu + 1):
                    r_p = (center + d_al) % N
                    h_val = Y_rx[r_p, ant] / pilot_amp
                    if abs(h_val) >= thresh:
                        r_target = (m_prime - two_Nc1 * l_int + d_al) % N
                        H_u[ant, r_target, m_prime] += h_val * ph_col
        H_list.append(H_u)
    return H_list

def verify_redline1_yin24():
    # 1) Noiseless integer-delay integer-Doppler + full data on [M_O .. N-1] exactness (< 1e-12)
    rng = np.random.default_rng(91000)
    N, K, Nbs = 128, 3, 5
    l_max, alpha_max, k_nu = 2, 1, 1
    two_Nc1 = 2 * (alpha_max + k_nu) + 1  # 5
    Q_yin = (l_max + 1) * two_Nc1 - 1     # 14
    pilots = np.array([(u + 1) * Q_yin + u for u in range(K)])
    M_O = K * (Q_yin + 1) + Q_yin         # 59
    data_bins = np.arange(M_O, N)         # [59..127]
    pilot_amp = np.sqrt(float(Q_yin + 1))
    c1, _, _, A = build_afdm(N, two_Nc1)

    H_true = []
    Y_rx = np.zeros((N, Nbs), dtype=complex)
    for u in range(K):
        xu = np.zeros(N, dtype=complex)
        xu[pilots[u]] = pilot_amp
        xu[data_bins] = (rng.standard_normal(len(data_bins)) + 1j * rng.standard_normal(len(data_bins))) / np.sqrt(2.0)
        Hu = np.zeros((Nbs, N, N), dtype=complex)
        for lp, nup in [(0, 1), (1, 0), (2, -1)]:
            M_td = np.zeros((N, N), dtype=complex)
            for ni in range(N):
                ms = ni - lp
                ph = np.exp(-1j * 2 * np.pi * c1 * (N ** 2 + 2 * N * ms)) if ms < 0 else 1.0
                M_td[ni, ms % N] = ph * np.exp(1j * 2 * np.pi * nup * ni / N)
            Hp = A @ M_td @ A.conj().T
            g_ant = (rng.standard_normal(Nbs) + 1j * rng.standard_normal(Nbs)) / np.sqrt(2.0)
            Hu += g_ant[:, None, None] * Hp[None, :, :]
        H_true.append(Hu)
        for ant in range(Nbs):
            Y_rx[:, ant] += Hu[ant] @ xu

    H_yin = yin24_epa_dr(Y_rx, N, Nbs, K, pilots, l_max, alpha_max, k_nu, two_Nc1, pilot_amp, thresh=0.0)
    rel_err_noiseless = float(max(np.linalg.norm(H_yin[u] - H_true[u]) / np.linalg.norm(H_true[u]) for u in range(K)))

    # 2) Yin TWC'24 Table II / Fig. 12 normal point: 2x2 MIMO-AFDM, P=4, l_max=2, alpha_max=2, k_nu=1 -> O_MIMO=62, SNRp=35 dB, SNRd=14 dB, 4-QAM, integer Doppler
    N2, Nt2, Nr2, P2 = 256, 2, 2, 4
    l_m2, al_m2, kn2 = 2, 2, 1
    two_Nc1_2 = 2 * (al_m2 + kn2) + 1  # 7
    Q2 = (l_m2 + 1) * two_Nc1_2 - 1     # 20
    pilots2 = np.array([(u + 1) * Q2 + u for u in range(Nt2)])  # [20, 41]
    M_O2 = (Nt2 + 1) * (Q2 + 1) - 1     # 62 (exact Yin24 Table II O_MIMO = 62)
    d_bins2 = np.arange(M_O2, N2)
    # Exact zero-pilot, zero-data guard bins under l in {0,1,2} and integer Doppler in {-2..2}:
    # Pilot 0 [4..22], Pilot 1 [25..43], Data [46..255] U [0,1] -> [2, 3, 23, 24, 44, 45] have exact zero signal!
    pure_guard_2 = np.array([2, 3, 23, 24, 44, 45])
    c1_2, _, _, A2 = build_afdm(N2, two_Nc1_2)
    qpsk = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / np.sqrt(2.0)
    q_bits = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    snrp_lin = 10.0 ** (35.0 / 10.0)
    snrd_lin = 10.0 ** (14.0 / 10.0)
    sigma2_2 = 1.0 / snrd_lin
    p_amp2 = np.sqrt(snrp_lin * sigma2_2)
    err_yin2, err_perf2, tot_b2 = 0, 0, 0

    for _ in range(80):
        H_t2 = []
        Y2 = np.sqrt(sigma2_2 / 2.0) * (rng.standard_normal((N2, Nr2)) + 1j * rng.standard_normal((N2, Nr2)))
        xb_2 = rng.integers(0, 4, size=(Nt2, len(d_bins2)))
        for u in range(Nt2):
            xu = np.zeros(N2, dtype=complex)
            xu[pilots2[u]] = p_amp2
            xu[d_bins2] = qpsk[xb_2[u]]
            Hu = np.zeros((Nr2, N2, N2), dtype=complex)
            for lp in [0, 1, 1, 2]:
                nup = float(rng.choice([-2, -1, 0, 1, 2]))
                M_td = np.zeros((N2, N2), dtype=complex)
                for ni in range(N2):
                    ms = ni - lp
                    ph = np.exp(-1j * 2 * np.pi * c1_2 * (N2 ** 2 + 2 * N2 * ms)) if ms < 0 else 1.0
                    M_td[ni, ms % N2] = ph * np.exp(1j * 2 * np.pi * nup * ni / N2)
                Hp = A2 @ M_td @ A2.conj().T
                ga = (rng.standard_normal(Nr2) + 1j * rng.standard_normal(Nr2)) / np.sqrt(2.0 * P2)
                Hu += ga[:, None, None] * Hp[None, :, :]
            H_t2.append(Hu)
            for ant in range(Nr2):
                Y2[:, ant] += Hu[ant] @ xu
        s2_hat2 = max(float(np.mean(np.abs(Y2[pure_guard_2, :]) ** 2)), 1e-9)
        thresh_amp = np.sqrt(3.0 * s2_hat2) / p_amp2
        H_e2 = yin24_epa_dr(Y2, N2, Nr2, Nt2, pilots2, l_m2, al_m2, kn2, two_Nc1_2, p_amp2, thresh=thresh_amp)
        for H_use, s2_use, acc_flag in [(H_e2, s2_hat2, True), (H_t2, sigma2_2, False)]:
            Yc = Y2.copy()
            for u in range(Nt2):
                Yc -= (H_use[u][:, :, pilots2[u]] * p_amp2).T
            nd = len(d_bins2)
            Gd = np.hstack([H_use[u][:, :, d_bins2].reshape(Nr2 * N2, nd) for u in range(Nt2)])
            sh = np.linalg.solve(Gd.conj().T @ Gd + s2_use * np.eye(Nt2 * nd), Gd.conj().T @ Yc.T.reshape(-1)).reshape(Nt2, nd)
            for u in range(Nt2):
                di = np.argmin(np.abs(sh[u][:, None] - qpsk[None, :]), axis=1)
                eb = int(np.sum(q_bits[di] != q_bits[xb_2[u]]))
                if acc_flag:
                    err_yin2 += eb
                else:
                    err_perf2 += eb
        tot_b2 += Nt2 * len(d_bins2) * 2

    # 3) Verify acyclic continuous-time 3-block simulation vs analytical pulse lag kernel (< 1e-13):
    env_chk = ScenarioEnv(128, 3, 5, 3, [0], 0.0, 0.25)
    X0 = np.zeros((3, 128), dtype=complex)
    X1 = np.zeros((3, 128), dtype=complex)
    X1[0, env_chk.data_bins[0]] = 1.0
    upaths = {0: [(1.37, -0.73, 0.31, 0.8 - 0.4j)], 1: [], 2: []}
    Y_sim = env_chk.simulate_3block_rx(X0, X1, X0, upaths, np.zeros((128, 5), dtype=complex))
    H_col_sim = env_chk.true_curr_block_H_from_3block(upaths[0])[:, :, env_chk.data_bins[0]]
    H_col_ana = ((0.8 - 0.4j) * env_chk.ula_vec_and_deriv(0.31)[0][:, None, None] * env_chk.full_pulse_H(1.37, -0.73)[None, :, :])[:, :, env_chk.data_bins[0]]
    ct_match_err = float(max(
        np.linalg.norm(Y_sim.T - H_col_sim) / np.linalg.norm(H_col_sim),
        np.linalg.norm(H_col_ana - H_col_sim) / np.linalg.norm(H_col_sim),
    ))

    return {
        "noiseless_integer_rel_err": rel_err_noiseless,
        "yin24_table2_2x2_ber_epa_dr": err_yin2 / tot_b2,
        "yin24_table2_2x2_ber_perfect": err_perf2 / tot_b2,
        "ct_3block_kernel_match_err": ct_match_err,
    }

class ScenarioEnv:
    def __init__(self, N, K, Nbs, P, weak_users, near_far_db, rolloff=0.25):
        self.N = N
        self.K = K
        self.Nbs = Nbs
        self.P = P
        self.rolloff = rolloff
        self.weak_users = list(weak_users)
        self.user_pow = np.array([1.0 if u in self.weak_users else (10.0 ** (near_far_db / 10.0)) for u in range(K)])
        self.l_max = 2
        self.alpha_max = 1
        self.k_nu = 1
        self.two_Nc1 = 2 * (self.alpha_max + self.k_nu) + 1  # 5
        self.Q_yin = (self.l_max + 1) * self.two_Nc1 - 1     # 14
        self.pilots = np.array([(u + 1) * self.Q_yin + u for u in range(K)])
        self.M_O = K * (self.Q_yin + 1) + self.Q_yin
        self.obs_idx = np.arange(0, self.M_O)
        self.data_bins = np.arange(self.M_O, N)
        self.d_bins_shift = np.arange(self.M_O - 7, N - 7)
        self.pilot_amp = np.sqrt(float(self.Q_yin + 1))

        self.c1, self.L1, self.F, self.A = build_afdm(N, self.two_Nc1)
        self.n_idx = np.arange(N)
        self.L_os = 4
        self.half_span = 4
        self.span_rrc = 2 * self.half_span  # 8 symbols
        self.s_rx = np.arange(-self.half_span * self.L_os, self.half_span * self.L_os + 1, dtype=float)
        h_raw = rrc_cont(self.s_rx / self.L_os, rolloff, self.half_span)
        self.rrc_scale = float(np.sqrt(np.sum(h_raw ** 2)))
        self.h_rrc = h_raw / self.rrc_scale
        # Acyclic TX filter grid [-4.0 .. +7.0] symbols (45 oversampled taps) covers full shifted support for tau in [0, 2]:
        self.s_tx = np.arange(-self.half_span * self.L_os, (self.half_span + self.l_max + 1) * self.L_os + 1, dtype=float)
        self.tx_zero_idx = self.half_span * self.L_os  # 16
        self.rx_zero_idx = self.half_span * self.L_os  # 16

        self.N_cp = 6
        self.N_blk = N + self.N_cp
        self.d_list = np.arange(-self.span_rrc, self.l_max + self.span_rrc + 1)  # [-8..10]
        # Complete 12 reachable inter-block boundary time-domain indices ms = ni - d outside [-N_cp .. N-1]:
        # ms in [-10, -9, -8, -7] (prev block tail) and ms in [N .. N+7] (next block CPP + first 2 body samples)
        self.ibi_ms_list = list(range(-self.span_rrc - self.l_max, -self.N_cp)) + list(range(N, N + self.span_rrc))

        M_lag = []
        for d in self.d_list:
            M = np.zeros((N, N), dtype=complex)
            for ni in range(N):
                ms = ni - d
                if -self.N_cp <= ms < 0:
                    M[ni, ms + N] = np.exp(-1j * 2 * np.pi * self.c1 * (N ** 2 + 2 * N * ms))
                elif 0 <= ms < N:
                    M[ni, ms] = 1.0
            M_lag.append(M)
        self.M_lag = np.array(M_lag)
        self.V_pilots = {u: self.M_lag @ (self.pilot_amp * self.A[self.pilots[u], :].conj()) for u in range(K)}
        self.f_bins = np.fft.fftfreq(N) * N

        pam4 = np.array([-3.0, -1.0, 3.0, 1.0]) / np.sqrt(10.0)
        self.qam16 = np.array([x + 1j * y for x in pam4 for y in pam4])
        self.qam_bits = np.array([[(i >> 3) & 1, (i >> 2) & 1, (i >> 1) & 1, i & 1] for i in range(16)])

        self.tau_grid = np.linspace(0.0, self.l_max, 13)
        self.nu_grid = np.linspace(-1.4, 1.4, 13)
        self.th_grid = np.linspace(-0.85, 0.85, 19)
        self.A_th_grid = np.stack([self.ula_vec_and_deriv(th)[0] for th in self.th_grid], axis=1)
        self.B_dir = np.zeros((K, len(self.tau_grid), len(self.nu_grid), self.M_O), dtype=complex)
        self.B_pul = np.zeros((K, len(self.tau_grid), len(self.nu_grid), self.M_O), dtype=complex)
        for it, tg in enumerate(self.tau_grid):
            for inu, ng in enumerate(self.nu_grid):
                for u in range(K):
                    self.B_dir[u, it, inu] = self.dirichlet_atom_jac(u, tg, ng)[0]
                    self.B_pul[u, it, inu] = self.pulse_atom_jac(u, tg, ng)[0]

    def ula_vec_and_deriv(self, theta_sin):
        m = np.arange(self.Nbs, dtype=float)
        a = np.exp(1j * np.pi * m * theta_sin) / np.sqrt(self.Nbs)
        return a, (1j * np.pi * m) * a

    def _pulse_w_exact(self, tau, nu):
        # Exact discrete lag kernel of the acyclic continuous-time 4x RRC TX -> Doppler -> RX matched filter chain:
        t_mat = self.d_list[:, None] + (self.s_rx[None, :] / self.L_os) - tau
        h_tx_mat = rrc_cont(t_mat, self.rolloff, self.half_span) / self.rrc_scale
        rx_mod = self.h_rrc * np.exp(1j * 2 * np.pi * nu * self.s_rx / (self.N * self.L_os))
        return h_tx_mat @ rx_mod, h_tx_mat, rx_mod

    def pulse_weights_and_deriv(self, tau, nu):
        w, h_tx_mat, rx_mod = self._pulse_w_exact(tau, nu)
        eps = 1e-5
        t_p = self.d_list[:, None] + (self.s_rx[None, :] / self.L_os) - (tau + eps)
        t_m = self.d_list[:, None] + (self.s_rx[None, :] / self.L_os) - (tau - eps)
        dh_dtau = (rrc_cont(t_p, self.rolloff, self.half_span) - rrc_cont(t_m, self.rolloff, self.half_span)) / (2.0 * eps * self.rrc_scale)
        dw_dtau = dh_dtau @ rx_mod
        dw_dnu = h_tx_mat @ (rx_mod * (1j * 2 * np.pi * self.s_rx / (self.N * self.L_os)))
        return w, dw_dtau, dw_dnu

    def pulse_atom_jac(self, u, tau, nu):
        w, dw_dtau, dw_dnu = self.pulse_weights_and_deriv(tau, nu)
        Vt = self.V_pilots[u]
        u_td, du_dtau, du_dnu = w @ Vt, dw_dtau @ Vt, dw_dnu @ Vt
        dop = np.exp(1j * 2 * np.pi * nu * self.n_idx / self.N)
        sN = np.sqrt(self.N)
        b = np.fft.fft(self.L1 * (dop * u_td)) / sN
        dbt = np.fft.fft(self.L1 * (dop * du_dtau)) / sN
        dbn = np.fft.fft(self.L1 * (dop * (du_dnu + 1j * 2 * np.pi * (self.n_idx / self.N) * u_td))) / sN
        return b[self.obs_idx], dbt[self.obs_idx], dbn[self.obs_idx]

    def full_pulse_H(self, tau, nu):
        w, _, _ = self._pulse_w_exact(tau, nu)
        M0 = np.tensordot(w, self.M_lag, axes=(0, 0))
        dop = np.exp(1j * 2 * np.pi * nu * self.n_idx / self.N)[:, None]
        return self.A @ (dop * M0) @ self.A.conj().T

    def dirichlet_H(self, tau, nu):
        ph_del = np.exp(-1j * 2 * np.pi * tau * self.f_bins / self.N)
        X_del = np.fft.ifft(np.fft.fft(self.A.conj().T, axis=0) * ph_del[:, None], axis=0)
        dop = np.exp(1j * 2 * np.pi * nu * self.n_idx / self.N)[:, None]
        return self.A @ (dop * X_del)

    def dirichlet_atom_jac(self, u, tau, nu):
        pu = self.pilots[u]
        fa_p = np.fft.fft(self.pilot_amp * self.A[pu, :].conj())
        ph_del = np.exp(-1j * 2 * np.pi * tau * self.f_bins / self.N)
        x_del = np.fft.ifft(fa_p * ph_del)
        dx_tau = np.fft.ifft(fa_p * (-1j * 2 * np.pi * self.f_bins / self.N) * ph_del)
        dop = np.exp(1j * 2 * np.pi * nu * self.n_idx / self.N)
        sN = np.sqrt(self.N)
        return (
            (np.fft.fft(self.L1 * (dop * x_del)) / sN)[self.obs_idx],
            (np.fft.fft(self.L1 * (dop * dx_tau)) / sN)[self.obs_idx],
            (np.fft.fft(self.L1 * (dop * (1j * 2 * np.pi * (self.n_idx / self.N) * x_del))) / sN)[self.obs_idx],
        )

    def _single_user_3block_acyclic(self, s3, u_paths):
        # Strictly acyclic linear convolution in 4x oversampled continuous time (zero periodic FFT wrap!)
        up = np.zeros(len(s3) * self.L_os, dtype=complex)
        up[::self.L_os] = s3
        sym0 = self.N_blk + self.N_cp
        k0 = sym0 * self.L_os
        idx0 = k0 + self.tx_zero_idx
        idx_rx0 = idx0 + self.rx_zero_idx
        sample_idx = idx_rx0 + np.arange(self.N) * self.L_os
        Y_u = np.zeros((self.N, self.Nbs), dtype=complex)
        for (tau_p, nu_p, th_p, gain_p) in u_paths:
            h_tx_tau = rrc_cont(self.s_tx / self.L_os - tau_p, self.rolloff, self.half_span) / self.rrc_scale
            s_del = np.convolve(up, h_tx_tau, mode="full")
            dop = np.exp(1j * 2 * np.pi * nu_p * (np.arange(len(s_del)) - idx0) / (self.N * self.L_os))
            y_mf = np.convolve(s_del * dop, self.h_rrc, mode="full")
            y_daft = self.A @ y_mf[sample_idx]
            a_s = np.exp(1j * np.pi * np.arange(self.Nbs) * th_p) / np.sqrt(self.Nbs)
            Y_u += gain_p * np.outer(y_daft, a_s)
        return Y_u

    def simulate_3block_rx(self, x_prev, x_curr, x_next, user_paths, noise_mat):
        Y_rx = noise_mat.copy()
        n_cp = np.arange(-self.N_cp, 0)
        cpp_ph = np.exp(-1j * 2 * np.pi * self.c1 * (self.N ** 2 + 2 * self.N * n_cp))
        def _to_cpp(xd):
            xt = self.A.conj().T @ xd
            return np.concatenate([cpp_ph * xt[self.N - self.N_cp :], xt])
        for u in range(self.K):
            s3 = np.concatenate([_to_cpp(x_prev[u]), _to_cpp(x_curr[u]), _to_cpp(x_next[u])])
            Y_rx += self._single_user_3block_acyclic(s3, user_paths[u])
        return Y_rx

    def true_curr_block_H_from_3block(self, u_paths):
        # Extract ground-truth current-block effective channel matrix directly from the 3-block acyclic physical operator
        n_cp = np.arange(-self.N_cp, 0)
        cpp_ph = np.exp(-1j * 2 * np.pi * self.c1 * (self.N ** 2 + 2 * self.N * n_cp))
        # Impulse responses of all N+N_cp samples of middle block at 4x acyclic linear convolution:
        Hu = np.zeros((self.Nbs, self.N, self.N), dtype=complex)
        sym0 = self.N_blk + self.N_cp
        k0 = sym0 * self.L_os
        idx0 = k0 + self.tx_zero_idx
        idx_rx0 = idx0 + self.rx_zero_idx
        sample_idx = idx_rx0 + np.arange(self.N) * self.L_os
        len_up = 3 * self.N_blk * self.L_os
        len_sdel = len_up + len(self.s_tx) - 1
        # Build N x N_blk middle-block TD transfer matrix per path directly from acyclic impulse positions:
        m_blk = np.arange(self.N_blk)  # 0..133 inside middle block; m_rel_curr0 = m_blk - N_cp in [-6..127]
        pos_up = (self.N_blk + m_blk) * self.L_os  # position in `up`
        for (tau_p, nu_p, th_p, gain_p) in u_paths:
            h_tx_tau = rrc_cont(self.s_tx / self.L_os - tau_p, self.rolloff, self.half_span) / self.rrc_scale
            dop = np.exp(1j * 2 * np.pi * nu_p * (np.arange(len_sdel) - idx0) / (self.N * self.L_os))
            M_blk = np.zeros((self.N, self.N_blk), dtype=complex)
            for im, pu_k in enumerate(pos_up):
                # Nonzero segment in s_del is [pu_k .. pu_k + len(h_tx_tau) - 1]
                seg = h_tx_tau * dop[pu_k : pu_k + len(h_tx_tau)]
                ym_seg = np.convolve(seg, self.h_rrc, mode="full")  # starts at pu_k in y_mf
                rel = sample_idx - pu_k
                valid = (rel >= 0) & (rel < len(ym_seg))
                M_blk[valid, im] = ym_seg[rel[valid]]
            # Map x_curr (N) -> middle block (N_cp + N) -> M_blk (N) -> DAFT:
            X_td = self.A.conj().T
            S_mid = np.vstack([cpp_ph[:, None] * X_td[self.N - self.N_cp :, :], X_td])
            H_p = self.A @ (M_blk @ S_mid)
            a_s = np.exp(1j * np.pi * np.arange(self.Nbs) * th_p) / np.sqrt(self.Nbs)
            Hu += gain_p * a_s[:, None, None] * H_p[None, :, :]
        return Hu

    def _build_leakage_matrix(self, paths_dict, use_pulse=True, d_bins=None):
        if d_bins is None:
            d_bins = self.data_bins
        M_tot = self.M_O * self.Nbs
        G_cols = []
        n_ibi = len(self.ibi_ms_list)
        for u, plist in paths_dict.items():
            if len(plist) == 0:
                continue
            Gu_d = np.zeros((M_tot, len(d_bins)), dtype=complex)
            Gu_ibi = np.zeros((M_tot, n_ibi), dtype=complex)
            for (tp, np_, thp, bp, _) in plist:
                if abs(bp) < 1e-8:
                    continue
                Hf = self.full_pulse_H(tp, np_) if use_pulse else self.dirichlet_H(tp, np_)
                a_s, _ = self.ula_vec_and_deriv(thp)
                Gu_d += bp * np.kron(a_s[:, None], Hf[np.ix_(self.obs_idx, d_bins)])
                if use_pulse:
                    w_p, _, _ = self._pulse_w_exact(tp, np_)
                    dop_p = np.exp(1j * 2 * np.pi * np_ * self.n_idx / self.N)
                    T_ibi = np.zeros((self.N, n_ibi), dtype=complex)
                    d0 = int(self.d_list[0])
                    n_d = len(self.d_list)
                    for ic, ms_ext in enumerate(self.ibi_ms_list):
                        for ni in range(self.N):
                            id_d = (ni - ms_ext) - d0
                            if 0 <= id_d < n_d:
                                T_ibi[ni, ic] = dop_p[ni] * w_p[id_d]
                    Gu_ibi += bp * np.kron(a_s[:, None], (self.A @ T_ibi)[self.obs_idx, :])
            G_cols.append(Gu_d)
            if use_pulse:
                G_cols.append(Gu_ibi)
        if len(G_cols) == 0:
            return None
        return np.hstack(G_cols)

    def estimate_common_blind_s2(self, Y_obs, d_bins=None):
        # Purely blind 2-step noise estimator from Y_obs alone (zero truth access!), shared identically across ALL arms for strict parity!
        if d_bins is None:
            d_bins = self.data_bins
        u_en = np.array([np.sum(np.abs(Y_obs[max(0, self.pilots[u] - 11) : self.pilots[u] + 2, :]) ** 2) for u in range(self.K)])
        u_ord = np.argsort(u_en)[::-1]
        paths0 = {u: [] for u in range(self.K)}
        R0 = Y_obs.copy()
        for u in u_ord:
            for _ in range(self.P):
                it0, inu0, ith0 = self.coarse_peak(R0, u, None, self.B_pul[u])
                est = self.refine_newton(R0, u, self.tau_grid[it0], self.nu_grid[inu0], self.th_grid[ith0], None, True, n_it=5)
                paths0[u].append(est)
                R0 -= est[3] * est[4]
        paths0, R0 = self.joint_polish(Y_obs, paths0, None, True, n_it=5)
        M_tot = self.M_O * self.Nbs

        def _proj_s2(p_dict, R_mat):
            Gm = self._build_leakage_matrix(p_dict, use_pulse=True, d_bins=d_bins)
            rv = R_mat.reshape(-1, order="F")
            Uf, _, _ = np.linalg.svd(Gm, full_matrices=True)
            r_eff = min(Gm.shape[1], M_tot - 24)
            Un = Uf[:, r_eff:]
            return max(float(np.median(np.abs(Un.conj().T @ rv) ** 2) / np.log(2.0)), 1e-7)

        s2_0 = _proj_s2(paths0, R0)
        # One whitened bootstrap pass (whitening strong users against other users only to prevent self-steering nulling):
        R1 = R0.copy()
        max_e0 = u_en[u_ord[0]]
        for u in u_ord:
            ref_p0 = {ku: paths0[ku] for ku in range(self.K) if ku != u} if u_en[u] >= 0.45 * max_e0 else paths0
            Linv0, Cinv0 = self.build_whitener(ref_p0, s2_0, use_pulse=True, cov_mode="full", d_bins=d_bins)
            for p_i in range(self.P):
                old = paths0[u][p_i]
                Rp = R1 + old[3] * old[4]
                it_w, inu_w, ith_w = self.coarse_peak(Rp, u, Cinv0, self.B_pul[u])
                c1_e = self.refine_newton(Rp, u, old[0], old[1], old[2], Linv0, True, n_it=5)
                c2_e = self.refine_newton(Rp, u, self.tau_grid[it_w], self.nu_grid[inu_w], self.th_grid[ith_w], Linv0, True, n_it=5)
                r1 = (Rp - c1_e[3] * c1_e[4]).reshape(-1, order="F")
                r2 = (Rp - c2_e[3] * c2_e[4]).reshape(-1, order="F")
                e1 = np.sum(np.abs(r1 if Linv0 is None else (Linv0 @ r1)) ** 2)
                e2 = np.sum(np.abs(r2 if Linv0 is None else (Linv0 @ r2)) ** 2)
                paths0[u][p_i] = c1_e if e1 <= e2 else c2_e
                R1 = Rp - paths0[u][p_i][3] * paths0[u][p_i][4]
        Linv1, _ = self.build_whitener(paths0, s2_0, use_pulse=True, cov_mode="full", d_bins=d_bins)
        paths0, R1 = self.joint_polish(Y_obs, paths0, Linv1, True, n_it=5)
        return _proj_s2(paths0, R1)

    def build_whitener(self, paths_dict, s2_fixed, use_pulse=True, cov_mode="full", d_bins=None):
        if cov_mode == "none":
            return None, None
        G_all = self._build_leakage_matrix(paths_dict, use_pulse=use_pulse, d_bins=d_bins)
        if G_all is None:
            return None, None
        M_tot = self.M_O * self.Nbs
        if cov_mode == "diag_power":
            dp = np.sum(np.abs(G_all) ** 2, axis=1) + s2_fixed
            isq = 1.0 / np.sqrt(dp)
            return np.diag(isq), np.diag(isq ** 2)
        if cov_mode == "no_cross_daft":
            Sf = G_all @ G_all.conj().T + s2_fixed * np.eye(M_tot)
            S4 = Sf.reshape((self.M_O, self.Nbs, self.M_O, self.Nbs), order="F")
            Sb = np.zeros_like(S4)
            for mi in range(self.M_O):
                Sb[mi, :, mi, :] = S4[mi, :, mi, :]
            Lc = np.linalg.cholesky(Sb.reshape((M_tot, M_tot), order="F"))
            Linv = np.linalg.solve(Lc, np.eye(M_tot))
            return Linv, Linv.conj().T @ Linv
        U_f, sv, _ = np.linalg.svd(G_all, full_matrices=True)
        eig_all = np.zeros(M_tot)
        eig_all[: len(sv)] = sv ** 2
        isq = 1.0 / np.sqrt(eig_all + s2_fixed)
        Linv = (U_f * isq[None, :]).conj().T
        Cinv = (U_f * (isq ** 2)[None, :]) @ U_f.conj().T
        return Linv, Cinv

    def coarse_peak(self, R_plus, u, C_inv, B_u):
        if C_inv is None:
            RB = np.tensordot(B_u.conj(), R_plus, axes=([2], [0]))
            num = np.abs(RB @ self.A_th_grid.conj()) ** 2
            den = (np.sum(np.abs(B_u) ** 2, axis=2)[:, :, None]) + 1e-12
            return np.unravel_index(np.argmax(num / den), num.shape)
        rv = R_plus.reshape(-1, order="F")
        Cr = (C_inv @ rv).reshape((self.M_O, self.Nbs), order="F")
        num = np.abs(np.tensordot(B_u.conj(), Cr, axes=([2], [0])) @ self.A_th_grid.conj()) ** 2
        C4 = C_inv.reshape((self.M_O, self.Nbs, self.M_O, self.Nbs), order="F")
        CA = np.einsum("maMb,bi->maMi", C4, self.A_th_grid, optimize=True)
        K_th = np.einsum("ai,maMi->mMi", self.A_th_grid.conj(), CA, optimize=True)
        BK = np.einsum("tnm,mMi->tnMi", B_u.conj(), K_th, optimize=True)
        den = np.real(np.einsum("tnMi,tnM->tni", BK, B_u, optimize=True)) + 1e-12
        return np.unravel_index(np.argmax(num / den), num.shape)

    def refine_newton(self, R_obs, u, tau0, nu0, th0, L_inv, use_pulse, n_it=5):
        tau, nu, th = float(tau0), float(nu0), float(th0)
        rv = R_obs.reshape(-1, order="F")
        wr = rv if L_inv is None else (L_inv @ rv)
        fn = self.pulse_atom_jac if use_pulse else self.dirichlet_atom_jac
        for _ in range(n_it):
            b, dbt, dbn = fn(u, tau, nu)
            a_s, da_s = self.ula_vec_and_deriv(th)
            phi = np.kron(a_s, b)
            wphi = phi if L_inv is None else (L_inv @ phi)
            den = np.real(np.vdot(wphi, wphi)) + 1e-12
            beta = np.vdot(wphi, wr) / den
            wres = wr - beta * wphi
            J3 = beta * np.column_stack([np.kron(a_s, dbt), np.kron(a_s, dbn), np.kron(da_s, b)])
            WJ3 = J3 if L_inv is None else (L_inv @ J3)
            WJ_vp = WJ3 - np.outer(wphi, (wphi.conj() @ WJ3) / den)
            step = np.linalg.solve(np.real(WJ_vp.conj().T @ WJ_vp) + 1e-6 * np.eye(3), np.real(WJ_vp.conj().T @ wres))
            tau = float(np.clip(tau + 0.8 * step[0], -0.02, self.l_max + 0.02))
            nu = float(np.clip(nu + 0.8 * step[1], -1.55, 1.55))
            th = float(np.clip(th + 0.8 * step[2], -0.95, 0.95))
        b = fn(u, tau, nu)[0]
        a_s, _ = self.ula_vec_and_deriv(th)
        phi = np.kron(a_s, b)
        wphi = phi if L_inv is None else (L_inv @ phi)
        beta = np.vdot(wphi, wr) / (np.real(np.vdot(wphi, wphi)) + 1e-12)
        return [tau, nu, th, beta, np.outer(b, a_s)]

    def refine_fleury_coord(self, R_obs, u, tau0, nu0, th0, n_cyc=3):
        tau, nu, th = float(tau0), float(nu0), float(th0)
        for _ in range(n_cyc):
            a_s, _ = self.ula_vec_and_deriv(th)
            rb = R_obs @ a_s.conj()
            tc_arr = np.clip(tau + np.linspace(-0.25, 0.25, 15), 0.0, self.l_max)
            tau = float(max(tc_arr, key=lambda tc: (abs(np.vdot(self.dirichlet_atom_jac(u, tc, nu)[0], rb)) ** 2) / (np.sum(np.abs(self.dirichlet_atom_jac(u, tc, nu)[0]) ** 2) + 1e-12)))
            nc_arr = np.clip(nu + np.linspace(-0.35, 0.35, 15), -1.55, 1.55)
            nu = float(max(nc_arr, key=lambda nc: (abs(np.vdot(self.dirichlet_atom_jac(u, tau, nc)[0], rb)) ** 2) / (np.sum(np.abs(self.dirichlet_atom_jac(u, tau, nc)[0]) ** 2) + 1e-12)))
            b = self.dirichlet_atom_jac(u, tau, nu)[0]
            bp = b.conj() @ R_obs
            th_arr = np.clip(th + np.linspace(-0.20, 0.20, 17), -0.95, 0.95)
            Ac = np.stack([self.ula_vec_and_deriv(tc)[0] for tc in th_arr], axis=1)
            th = float(th_arr[int(np.argmax(np.abs(bp @ Ac.conj()) ** 2))])
        b = self.dirichlet_atom_jac(u, tau, nu)[0]
        a_s, _ = self.ula_vec_and_deriv(th)
        phi = np.kron(a_s, b)
        beta = np.vdot(phi, R_obs.reshape(-1, order="F")) / (np.real(np.vdot(phi, phi)) + 1e-12)
        return [tau, nu, th, beta, np.outer(b, a_s)]

    def joint_polish(self, Y_obs, paths, L_inv, use_pulse, n_it=3):
        yv = Y_obs.reshape(-1, order="F")
        wy = yv if L_inv is None else (L_inv @ yv)
        keys = [(u, p_i) for u in range(self.K) for p_i in range(self.P)]
        fn = self.pulse_atom_jac if use_pulse else self.dirichlet_atom_jac
        for _ in range(n_it):
            WPhi, J_nl = [], []
            for (u, p_i) in keys:
                tau, nu, th, _, _ = paths[u][p_i]
                b, dbt, dbn = fn(u, tau, nu)
                a_s, da_s = self.ula_vec_and_deriv(th)
                phi = np.kron(a_s, b)
                d1, d2, d3 = np.kron(a_s, dbt), np.kron(a_s, dbn), np.kron(da_s, b)
                WPhi.append(phi if L_inv is None else (L_inv @ phi))
                J_nl.append((d1, d2, d3) if L_inv is None else (L_inv @ d1, L_inv @ d2, L_inv @ d3))
            WPhi = np.column_stack(WPhi)
            betas = np.linalg.lstsq(WPhi, wy, rcond=None)[0]
            wres = wy - WPhi @ betas
            WJ = np.column_stack([bk * dc for bk, dt in zip(betas, J_nl) for dc in dt])
            Qp, _ = np.linalg.qr(WPhi, mode="reduced")
            WJv = WJ - Qp @ (Qp.conj().T @ WJ)
            step = np.linalg.solve(np.real(WJv.conj().T @ WJv) + 1e-5 * np.eye(3 * len(keys)), np.real(WJv.conj().T @ wres))
            for ik, (u, p_i) in enumerate(keys):
                paths[u][p_i][0] = float(np.clip(paths[u][p_i][0] + 0.7 * step[3 * ik], -0.02, self.l_max + 0.02))
                paths[u][p_i][1] = float(np.clip(paths[u][p_i][1] + 0.7 * step[3 * ik + 1], -1.55, 1.55))
                paths[u][p_i][2] = float(np.clip(paths[u][p_i][2] + 0.7 * step[3 * ik + 2], -0.95, 0.95))
        WPhi, atoms = [], []
        for (u, p_i) in keys:
            tau, nu, th, _, _ = paths[u][p_i]
            b = fn(u, tau, nu)[0]
            a_s, _ = self.ula_vec_and_deriv(th)
            phi = np.kron(a_s, b)
            WPhi.append(phi if L_inv is None else (L_inv @ phi))
            atoms.append(np.outer(b, a_s))
        betas = np.linalg.lstsq(np.column_stack(WPhi), wy, rcond=None)[0]
        R_out = Y_obs.copy()
        for ik, (u, p_i) in enumerate(keys):
            paths[u][p_i][3] = betas[ik]
            paths[u][p_i][4] = atoms[ik]
            R_out -= betas[ik] * atoms[ik]
        return paths, R_out

    def run_arm(self, Y_rx, arm_kind="full", d_bins=None, s2_common=None):
        # Zero side-info leaks: receives ONLY Y_rx (and optional pre-computed purely blind s2_common from Y_rx[obs_idx])!
        if d_bins is None:
            d_bins = self.data_bins
        Y_obs = Y_rx[self.obs_idx, :]
        s2_blind = self.estimate_common_blind_s2(Y_obs, d_bins=d_bins) if s2_common is None else float(s2_common)

        if arm_kind == "yin24_a":
            th_y = np.sqrt(3.0 * s2_blind) / self.pilot_amp
            H_y = yin24_epa_dr(Y_rx, self.N, self.Nbs, self.K, self.pilots, self.l_max, self.alpha_max, self.k_nu, self.two_Nc1, self.pilot_amp, thresh=th_y)
            return H_y, s2_blind

        if arm_kind == "fleury_sage_b":
            # Matched 3-stage SAGE search budget (init + dual-start re-search + refine pass + joint LS amplitudes)
            u_en = np.array([np.sum(np.abs(Y_obs[max(0, self.pilots[u] - 11) : self.pilots[u] + 2, :]) ** 2) for u in range(self.K)])
            u_ord = np.argsort(u_en)[::-1]
            paths = {u: [] for u in range(self.K)}
            R_c = Y_obs.copy()
            for u in u_ord:
                for _ in range(self.P):
                    it0, inu0, ith0 = self.coarse_peak(R_c, u, None, self.B_dir[u])
                    est = self.refine_fleury_coord(R_c, u, self.tau_grid[it0], self.nu_grid[inu0], self.th_grid[ith0], n_cyc=3)
                    paths[u].append(est)
                    R_c -= est[3] * est[4]
            for _ in range(2):
                for u in u_ord:
                    for p_i in range(self.P):
                        old = paths[u][p_i]
                        Rp = R_c + old[3] * old[4]
                        it_w, inu_w, ith_w = self.coarse_peak(Rp, u, None, self.B_dir[u])
                        c1_e = self.refine_fleury_coord(Rp, u, old[0], old[1], old[2], n_cyc=3)
                        c2_e = self.refine_fleury_coord(Rp, u, self.tau_grid[it_w], self.nu_grid[inu_w], self.th_grid[ith_w], n_cyc=3)
                        e1 = np.sum(np.abs(Rp - c1_e[3] * c1_e[4]) ** 2)
                        e2 = np.sum(np.abs(Rp - c2_e[3] * c2_e[4]) ** 2)
                        paths[u][p_i] = c1_e if e1 <= e2 else c2_e
                        R_c = Rp - paths[u][p_i][3] * paths[u][p_i][4]
            # Joint LS amplitude refit across all K*P paths:
            keys = [(u, p_i) for u in range(self.K) for p_i in range(self.P)]
            Phi = np.column_stack([paths[u][p_i][4].reshape(-1, order="F") for (u, p_i) in keys])
            betas = np.linalg.lstsq(Phi, Y_obs.reshape(-1, order="F"), rcond=None)[0]
            for ik, (u, p_i) in enumerate(keys):
                paths[u][p_i][3] = betas[ik]
            H_list = []
            for u in range(self.K):
                Hu = np.zeros((self.Nbs, self.N, self.N), dtype=complex)
                for (tp, np_, thp, bp, _) in paths[u]:
                    Hu += bp * self.ula_vec_and_deriv(thp)[0][:, None, None] * self.dirichlet_H(tp, np_)[None, :, :]
                H_list.append(Hu)
            return H_list, s2_blind

        cfg = {
            "matched_dir_b": (False, "none"),
            "a_only": (True, "none"),
            "b_only": (False, "full"),
            "diag_weight": (True, "diag_power"),
            "spatial_only": (True, "no_cross_daft"),
            "full": (True, "full"),
        }[arm_kind]
        use_pulse, cov_mode = cfg
        B_use = self.B_pul if use_pulse else self.B_dir
        u_en = np.array([np.sum(np.abs(Y_obs[max(0, self.pilots[u] - 11) : self.pilots[u] + 2, :]) ** 2) for u in range(self.K)])
        u_ord = np.argsort(u_en)[::-1]
        paths = {u: [] for u in range(self.K)}
        R_c = Y_obs.copy()
        max_e = u_en[u_ord[0]]

        for idx_u, u in enumerate(u_ord):
            if cov_mode != "none" and idx_u > 0 and u_en[u] < 0.45 * max_e:
                Linv, Cinv = self.build_whitener(paths, s2_blind, use_pulse=use_pulse, cov_mode=cov_mode, d_bins=d_bins)
            else:
                Linv, Cinv = None, None
            for _ in range(self.P):
                it0, inu0, ith0 = self.coarse_peak(R_c, u, Cinv, B_use[u])
                est = self.refine_newton(R_c, u, self.tau_grid[it0], self.nu_grid[inu0], self.th_grid[ith0], Linv, use_pulse, n_it=5)
                paths[u].append(est)
                R_c -= est[3] * est[4]

        Linv_pre, _ = self.build_whitener(paths, s2_blind, use_pulse=use_pulse, cov_mode=cov_mode, d_bins=d_bins)
        paths, R_c = self.joint_polish(Y_obs, paths, Linv_pre, use_pulse, n_it=4)

        for u in u_ord:
            ref_paths = {ku: paths[ku] for ku in range(self.K) if ku != u} if u_en[u] >= 0.45 * max_e else paths
            Linv, Cinv = self.build_whitener(ref_paths, s2_blind, use_pulse=use_pulse, cov_mode=cov_mode, d_bins=d_bins)
            for p_i in range(self.P):
                old = paths[u][p_i]
                Rp = R_c + old[3] * old[4]
                it_w, inu_w, ith_w = self.coarse_peak(Rp, u, Cinv, B_use[u])
                c1_e = self.refine_newton(Rp, u, old[0], old[1], old[2], Linv, use_pulse, n_it=5)
                c2_e = self.refine_newton(Rp, u, self.tau_grid[it_w], self.nu_grid[inu_w], self.th_grid[ith_w], Linv, use_pulse, n_it=5)
                r1 = (Rp - c1_e[3] * c1_e[4]).reshape(-1, order="F")
                r2 = (Rp - c2_e[3] * c2_e[4]).reshape(-1, order="F")
                e1 = np.sum(np.abs(r1 if Linv is None else (Linv @ r1)) ** 2)
                e2 = np.sum(np.abs(r2 if Linv is None else (Linv @ r2)) ** 2)
                paths[u][p_i] = c1_e if e1 <= e2 else c2_e
                R_c = Rp - paths[u][p_i][3] * paths[u][p_i][4]

        Linv, _ = self.build_whitener(paths, s2_blind, use_pulse=use_pulse, cov_mode=cov_mode, d_bins=d_bins)
        paths, _ = self.joint_polish(Y_obs, paths, Linv, use_pulse, n_it=5)

        H_list = []
        for u in range(self.K):
            Hu = np.zeros((self.Nbs, self.N, self.N), dtype=complex)
            for (tp, np_, thp, bp, _) in paths[u]:
                Hm = self.full_pulse_H(tp, np_) if use_pulse else self.dirichlet_H(tp, np_)
                Hu += bp * self.ula_vec_and_deriv(thp)[0][:, None, None] * Hm[None, :, :]
            H_list.append(Hu)
        return H_list, s2_blind

    def detect_unb_lmmse(self, Y_full, H_est_list, sigma2_est, d_bins=None):
        if d_bins is None:
            d_bins = self.data_bins
        Yc = Y_full.copy()
        for u in range(self.K):
            Yc -= (H_est_list[u][:, :, self.pilots[u]] * self.pilot_amp).T
        nd = len(d_bins)
        Gd = np.hstack([H_est_list[u][:, :, d_bins].reshape(self.Nbs * self.N, nd) for u in range(self.K)])
        Gram = Gd.conj().T @ Gd
        Inv = np.linalg.inv(Gram + sigma2_est * np.eye(self.K * nd))
        xb = Inv @ (Gd.conj().T @ Yc.T.reshape(-1))
        # Exact unbiased gain g_k = [Gram @ Inv]_{kk} (>0 iff column k of Gd is nonzero; 0 only if hard threshold zeroed entire column)
        g_diag = np.real(np.sum(np.conj(Gd) * (Gd @ Inv), axis=0))
        x_unb = np.where(g_diag > 1e-12, xb / np.where(g_diag > 1e-12, g_diag, 1.0), 0.0)
        return x_unb.reshape(self.K, nd)

_ENV_CACHE = {}
_SCEN_SEED_BASE = {
    "S1_K3_Nbs5_NF16": 910000,
    "S2_K4_Nbs6_NF15": 930000,
    "CLEAN_K3_Nbs5_NF0": 950000,
}

def run_single_trial(task_tuple):
    scen_key, snr_db, tr_id = task_tuple
    if scen_key not in _ENV_CACHE:
        if scen_key == "S1_K3_Nbs5_NF16":
            _ENV_CACHE[scen_key] = ScenarioEnv(128, 3, 5, 3, [0], 16.0, 0.25)
        elif scen_key == "S2_K4_Nbs6_NF15":
            _ENV_CACHE[scen_key] = ScenarioEnv(128, 4, 6, 3, [0, 1], 15.0, 0.25)
        elif scen_key == "CLEAN_K3_Nbs5_NF0":
            _ENV_CACHE[scen_key] = ScenarioEnv(128, 3, 5, 3, [0, 1, 2], 0.0, 0.25)
    env = _ENV_CACHE[scen_key]
    seed_val = _SCEN_SEED_BASE[scen_key] + tr_id * 17 + int(round(snr_db * 10))
    rng = np.random.default_rng(seed_val)
    sigma2_true = 10.0 ** (-snr_db / 10.0)
    nd = len(env.data_bins)

    user_paths = {u: [] for u in range(env.K)}
    H_true = []
    X_prev = np.zeros((env.K, env.N), dtype=complex)
    X_curr = np.zeros((env.K, env.N), dtype=complex)
    X_next = np.zeros((env.K, env.N), dtype=complex)
    X_prev_sh = np.zeros((env.K, env.N), dtype=complex)
    X_curr_sh = np.zeros((env.K, env.N), dtype=complex)
    X_next_sh = np.zeros((env.K, env.N), dtype=complex)
    X_bits = rng.integers(0, 16, size=(env.K, nd))
    for u in range(env.K):
        bp, bn = rng.integers(0, 16, nd), rng.integers(0, 16, nd)
        for Xb, ba in [(X_prev, bp), (X_curr, X_bits[u]), (X_next, bn)]:
            Xb[u, env.pilots[u]] = env.pilot_amp
            Xb[u, env.data_bins] = env.qam16[ba]
        # Consistent 3-block shifted-guard layout across prev, curr, AND next blocks:
        for Xb_s, ba in [(X_prev_sh, bp), (X_curr_sh, X_bits[u]), (X_next_sh, bn)]:
            Xb_s[u, env.pilots[u]] = env.pilot_amp
            Xb_s[u, env.d_bins_shift] = env.qam16[ba]

        amp_u = np.sqrt(env.user_pow[u])
        taus = np.sort(rng.uniform(0.12, env.l_max - 0.05, size=env.P))
        nus = rng.uniform(-1.3, 1.3, size=env.P)
        ths = rng.uniform(-0.85, 0.85, size=env.P)
        gains = amp_u * (rng.standard_normal(env.P) + 1j * rng.standard_normal(env.P)) / np.sqrt(2.0 * env.P)
        for p_i in range(env.P):
            user_paths[u].append((float(taus[p_i]), float(nus[p_i]), float(ths[p_i]), complex(gains[p_i])))
        # Ground-truth channel matrix extracted directly from the 3-block acyclic physical operator:
        H_true.append(env.true_curr_block_H_from_3block(user_paths[u]))

    noise_mat = np.sqrt(sigma2_true / 2.0) * (rng.standard_normal((env.N, env.Nbs)) + 1j * rng.standard_normal((env.N, env.Nbs)))
    Y_rx = env.simulate_3block_rx(X_prev, X_curr, X_next, user_paths, noise_mat)

    if scen_key == "CLEAN_K3_Nbs5_NF0":
        H_f, s2_f = env.run_arm(Y_rx, "full")
        xh = env.detect_unb_lmmse(Y_rx, H_f, s2_f)
        ser_err, nmse_l = 0, []
        for u in env.weak_users:
            nmse_l.append(float(np.linalg.norm(H_f[u][:, :, env.data_bins] - H_true[u][:, :, env.data_bins]) ** 2 / np.linalg.norm(H_true[u][:, :, env.data_bins]) ** 2))
            di = np.argmin(np.abs(xh[u][:, None] - env.qam16[None, :]), axis=1)
            ser_err += int(np.sum(di != X_bits[u]))
        return {"scen": scen_key, "snr": snr_db, "ser_err": ser_err, "tot_sym": len(env.weak_users) * nd, "nmse": float(np.mean(nmse_l))}

    Y_sh = env.simulate_3block_rx(X_prev_sh, X_curr_sh, X_next_sh, user_paths, noise_mat)
    arm_list = ["yin24_a", "fleury_sage_b", "matched_dir_b", "a_only", "b_only", "diag_weight", "spatial_only", "full"]
    out_err = {}
    out_nmse = {}

    # Measure full standalone blind runtime (including blind noise estimation), then share common blind s2 across all arms for strict parity:
    t0_s2 = time.perf_counter()
    s2_common = env.estimate_common_blind_s2(Y_rx[env.obs_idx, :], d_bins=env.data_bins)
    t_s2 = time.perf_counter() - t0_s2
    s2_err_db = float(10.0 * np.log10(s2_common / sigma2_true))
    t_full = 0.0

    for ak in arm_list:
        ts = time.perf_counter()
        H_h, s2_e = env.run_arm(Y_rx, ak, s2_common=s2_common)
        if ak == "full":
            t_full = (time.perf_counter() - ts) + t_s2
        xh = env.detect_unb_lmmse(Y_rx, H_h, s2_e)
        eb, nl = 0, []
        for u in env.weak_users:
            nl.append(float(np.linalg.norm(H_h[u][:, :, env.data_bins] - H_true[u][:, :, env.data_bins]) ** 2 / np.linalg.norm(H_true[u][:, :, env.data_bins]) ** 2))
            di = np.argmin(np.abs(xh[u][:, None] - env.qam16[None, :]), axis=1)
            eb += int(np.sum(env.qam_bits[di] != env.qam_bits[X_bits[u]]))
        out_err[ak] = eb
        out_nmse[ak] = float(np.mean(nl))

    # Equal-net-throughput 3-block shifted guard baseline:
    H_sh, s2_sh = env.run_arm(Y_sh, "a_only", d_bins=env.d_bins_shift)
    xh_sh = env.detect_unb_lmmse(Y_sh, H_sh, s2_sh, d_bins=env.d_bins_shift)
    eb_sh, nl_sh = 0, []
    for u in env.weak_users:
        nl_sh.append(float(np.linalg.norm(H_sh[u][:, :, env.d_bins_shift] - H_true[u][:, :, env.d_bins_shift]) ** 2 / np.linalg.norm(H_true[u][:, :, env.d_bins_shift]) ** 2))
        di = np.argmin(np.abs(xh_sh[u][:, None] - env.qam16[None, :]), axis=1)
        eb_sh += int(np.sum(env.qam_bits[di] != env.qam_bits[X_bits[u]]))
    out_err["shift_guard"] = eb_sh
    out_nmse["shift_guard"] = float(np.mean(nl_sh))

    # Oracle Perfect CSI diagnostic (never enters PASS_PRIMARY):
    xh_or = env.detect_unb_lmmse(Y_rx, H_true, sigma2_true)
    eb_or = 0
    for u in env.weak_users:
        di = np.argmin(np.abs(xh_or[u][:, None] - env.qam16[None, :]), axis=1)
        eb_or += int(np.sum(env.qam_bits[di] != env.qam_bits[X_bits[u]]))
    out_err["oracle"] = eb_or

    return {
        "scen": scen_key,
        "snr": snr_db,
        "err": out_err,
        "nmse": out_nmse,
        "bits": len(env.weak_users) * nd * 4,
        "t_full_ms": 1e3 * t_full,
        "s2_err_db": s2_err_db,
    }

def paired_ber_ratio_ci95(err_num_list, err_den_list, bits_per_frame, n_boot=4000, seed=20261125):
    en = np.asarray(err_num_list, dtype=float)
    ed = np.asarray(err_den_list, dtype=float)
    M = len(en)
    # Conservative cluster-level worst-case bound (-ln(0.025) * bits_per_frame) ONLY when denominator sum == 0; exact unmodified ratio when > 0:
    zero_den_guard = -np.log(0.025) * float(bits_per_frame)
    s_en, s_ed = float(np.sum(en)), float(np.sum(ed))
    pt = (s_en / s_ed) if s_ed > 0.0 else (s_en / zero_den_guard)
    if M < 2:
        return {"point": pt, "ci95": [pt, pt], "log_halfwidth": 0.0}
    rng_b = np.random.default_rng(seed)
    idx = rng_b.integers(0, M, size=(n_boot, M))
    sn = np.sum(en[idx], axis=1)
    sd = np.sum(ed[idx], axis=1)
    sd_safe = np.where(sd > 0.0, sd, zero_den_guard)
    sn_safe = np.maximum(sn, 1e-12)
    lr = np.log(sn_safe / sd_safe)
    lo_l, hi_l = float(np.quantile(lr, 0.025)), float(np.quantile(lr, 0.975))
    return {
        "point": pt,
        "ci95": [float(np.exp(lo_l)), float(np.exp(hi_l))],
        "log_halfwidth": 0.5 * (hi_l - lo_l),
    }

def hoeffding_kl_ci95(frame_rates, alpha_side=0.025):
    # Exact two-sided non-asymptotic finite-sample 95% CI for mean of M independent [0, 1]-bounded frame variables (Hoeffding 1963 Thm 1)
    x = np.asarray(frame_rates, dtype=float)
    M = len(x)
    xb = float(np.clip(np.mean(x), 0.0, 1.0))
    if M < 1:
        return {"point": xb, "ci95": [0.0, 1.0], "halfwidth": 0.5}
    target = -np.log(alpha_side) / float(M)

    def _kl(p, q):
        t1 = (p * np.log(p / q)) if p > 0.0 else 0.0
        t2 = ((1.0 - p) * np.log((1.0 - p) / (1.0 - q))) if p < 1.0 else 0.0
        return t1 + t2

    if xb >= 1.0 - 1e-12:
        hi_b = 1.0
    else:
        lo, hi = xb, 1.0 - 1e-12
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if _kl(xb, mid) <= target:
                lo = mid
            else:
                hi = mid
        hi_b = float(hi)

    if xb <= 1e-12:
        lo_b = 0.0
    else:
        lo, hi = 1e-12, xb
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if _kl(xb, mid) <= target:
                hi = mid
            else:
                lo = mid
        lo_b = float(lo)

    return {"point": xb, "ci95": [lo_b, hi_b], "halfwidth": 0.5 * (hi_b - lo_b)}

def paired_diff_t_ci95(diff_arr):
    x = np.asarray(diff_arr, dtype=float)
    M = len(x)
    m = float(np.mean(x))
    if M < 2:
        return {"point": m, "ci95": [m, m], "halfwidth": 0.0}
    t_crit = float(sp_t.ppf(0.975, df=M - 1))
    hw = t_crit * float(np.std(x, ddof=1)) / np.sqrt(M)
    return {"point": m, "ci95": [m - hw, m + hw], "halfwidth": hw}

def paired_share_ci95(g_sub_arr, g_full_arr, n_boot=4000, seed=20261125):
    gs = np.asarray(g_sub_arr, dtype=float)
    gf = np.asarray(g_full_arr, dtype=float)
    M = len(gs)
    mf = float(np.mean(gf))
    pt = float(np.mean(gs) / mf) if mf > 0.0 else float("inf")
    if M < 2:
        return {"point": pt, "ci95": [pt, pt], "halfwidth": 0.0}
    rng_b = np.random.default_rng(seed)
    idx = rng_b.integers(0, M, size=(n_boot, M))
    ms = np.mean(gs[idx], axis=1)
    mf_b = np.mean(gf[idx], axis=1)
    # Never clamp non-positive denominator to positive: if full gain <= 0 in any replicate, share = +inf (strictly fails < 0.80)
    sh = np.where(mf_b > 0.0, ms / np.where(mf_b > 0.0, mf_b, 1.0), np.inf)
    lo, hi = float(np.quantile(sh, 0.025)), float(np.quantile(sh, 0.975))
    return {"point": pt, "ci95": [lo, hi], "halfwidth": 0.5 * (hi - lo)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default="summary_g_r11_g01.json")
    args = ap.parse_args()

    t_start = time.time()
    rl1 = verify_redline1_yin24()
    print("[Red-Line 1]", json.dumps(rl1), flush=True)

    v_redline1 = (
        (rl1["noiseless_integer_rel_err"] < 1e-12)
        and (rl1["ct_3block_kernel_match_err"] < 1e-12)
        and (rl1["yin24_table2_2x2_ber_perfect"] > 0.0)
        and (rl1["yin24_table2_2x2_ber_epa_dr"] <= 1.60 * rl1["yin24_table2_2x2_ber_perfect"])
        and (rl1["yin24_table2_2x2_ber_epa_dr"] < 0.025)
    )
    if not v_redline1:
        fail_summary = {
            "card_id": "I-20261125-g01",
            "smoke": args.smoke,
            "redline1": rl1,
            "verdicts": {"PASS_REDLINE1": False, "PASS_PRIMARY": False},
        }
        with open(args.out, "w") as f:
            json.dump(fail_summary, f, indent=2)
        raise RuntimeError(f"Red-Line 1 anchor check failed: {rl1}")

    n_trials_s1_30 = 2 if args.smoke else 680
    n_trials_s1_curve = 0 if args.smoke else 60
    n_trials_s2 = 2 if args.smoke else 720
    n_trials_clean = 2 if args.smoke else 2000

    tasks = []
    for snr in [20.0, 25.0]:
        for tr in range(n_trials_s1_curve):
            tasks.append(("S1_K3_Nbs5_NF16", snr, tr))
    for tr in range(n_trials_s1_30):
        tasks.append(("S1_K3_Nbs5_NF16", 30.0, tr))
    for tr in range(n_trials_s2):
        tasks.append(("S2_K4_Nbs6_NF15", 30.0, tr))
    for tr in range(n_trials_clean):
        tasks.append(("CLEAN_K3_Nbs5_NF0", 30.0, tr))

    if args.smoke or args.workers <= 1:
        results = [run_single_trial(t) for t in tasks]
    else:
        w_cnt = min(args.workers, 8)
        with ProcessPoolExecutor(max_workers=w_cnt) as ex:
            results = list(ex.map(run_single_trial, tasks))

    agg = {}
    clean_ser_frame, clean_nmse_db_frame, clean_nmse_lin = [], [], []
    clean_ser_err, clean_sym = 0, 0
    for r in results:
        if r["scen"] == "CLEAN_K3_Nbs5_NF0":
            clean_ser_err += r["ser_err"]
            clean_sym += r["tot_sym"]
            clean_ser_frame.append(r["ser_err"] / max(r["tot_sym"], 1))
            clean_nmse_lin.append(r["nmse"])
            clean_nmse_db_frame.append(10.0 * np.log10(max(r["nmse"], 1e-15)))
            continue
        key = f"{r['scen']}_SNR{int(r['snr'])}"
        if key not in agg:
            agg[key] = {"bits": 0, "n_frames": 0, "err": {}, "err_frames": {}, "nmse": {}, "t_ms": [], "s2_db": [], "frame_ber_full": []}
        agg[key]["bits"] += r["bits"]
        agg[key]["n_frames"] += 1
        agg[key]["t_ms"].append(r["t_full_ms"])
        agg[key]["s2_db"].append(r["s2_err_db"])
        agg[key]["frame_ber_full"].append(r["err"]["full"] / r["bits"])
        for ak, ev in r["err"].items():
            agg[key]["err"][ak] = agg[key]["err"].get(ak, 0) + ev
            agg[key]["err_frames"].setdefault(ak, []).append(ev)
        for ak, nv in r["nmse"].items():
            agg[key]["nmse"].setdefault(ak, []).append(nv)

    metrics = {}
    for key, d in agg.items():
        tot_b = d["bits"]
        ber_d = {ak: ev / tot_b for ak, ev in d["err"].items()}
        nmse_agg_db_d = {ak: float(10.0 * np.log10(np.mean(nv))) for ak, nv in d["nmse"].items()}
        nmse_mean_db_d = {ak: float(np.mean(10.0 * np.log10(np.maximum(nv, 1e-15)))) for ak, nv in d["nmse"].items()}
        f_arr = np.array(d["frame_ber_full"])
        metrics[key] = {
            "n_frames": d["n_frames"],
            "total_weak_bits": tot_b,
            "BER": ber_d,
            "NMSE_agg_dB": nmse_agg_db_d,
            "NMSE_mean_frame_dB": nmse_mean_db_d,
            "full_ber_iqr": [float(np.quantile(f_arr, 0.25)), float(np.median(f_arr)), float(np.quantile(f_arr, 0.75))],
            "avg_full_runtime_ms": float(np.mean(d["t_ms"])),
            "mean_blind_s2_err_dB": float(np.mean(d["s2_db"])),
        }

    clean_t_ser = paired_diff_t_ci95(clean_ser_frame)
    # Exact two-sided Hoeffding (1963 Thm 1) KL-Chernoff 95% CI valid for ANY independent [0, 1]-bounded frame SER distribution:
    clean_kl_ser = hoeffding_kl_ci95(clean_ser_frame, alpha_side=0.025)
    clean_ser_upper = max(clean_t_ser["ci95"][1], clean_kl_ser["ci95"][1])
    clean_nmse_db_ci = paired_diff_t_ci95(clean_nmse_db_frame)
    clean_agg_nmse_db = float(10.0 * np.log10(np.mean(clean_nmse_lin)))

    d_s1 = agg["S1_K3_Nbs5_NF16_SNR30"]
    d_s2 = agg["S2_K4_Nbs6_NF15_SNR30"]
    bpf_s1 = int(d_s1["bits"] // max(d_s1["n_frames"], 1))
    bpf_s2 = int(d_s2["bits"] // max(d_s2["n_frames"], 1))

    # Compute paired 95% CIs separately against EVERY legal rival & EVERY ablation arm (zero post-selection!):
    legal_rivals = ["yin24_a", "fleury_sage_b", "matched_dir_b"]
    ci_rivals_s1 = {
        rk: paired_ber_ratio_ci95(d_s1["err_frames"][rk], d_s1["err_frames"]["full"], bpf_s1, seed=20261125 + i)
        for i, rk in enumerate(legal_rivals)
    }
    ci_rivals_s2 = {
        rk: paired_ber_ratio_ci95(d_s2["err_frames"][rk], d_s2["err_frames"]["full"], bpf_s2, seed=20261140 + i)
        for i, rk in enumerate(legal_rivals)
    }
    ci_ab_ber_a = paired_ber_ratio_ci95(d_s1["err_frames"]["a_only"], d_s1["err_frames"]["full"], bpf_s1, seed=20261150)
    ci_ab_ber_b = paired_ber_ratio_ci95(d_s1["err_frames"]["b_only"], d_s1["err_frames"]["full"], bpf_s1, seed=20261151)
    ci_diag_ber = paired_ber_ratio_ci95(d_s1["err_frames"]["diag_weight"], d_s1["err_frames"]["full"], bpf_s1, seed=20261152)
    ci_spat_ber = paired_ber_ratio_ci95(d_s1["err_frames"]["spatial_only"], d_s1["err_frames"]["full"], bpf_s1, seed=20261153)
    ci_shift_ber = paired_ber_ratio_ci95(d_s1["err_frames"]["shift_guard"], d_s1["err_frames"]["full"], bpf_s1, seed=20261154)

    nm_dir_db = 10.0 * np.log10(np.maximum(d_s1["nmse"]["matched_dir_b"], 1e-15))
    nm_a_db = 10.0 * np.log10(np.maximum(d_s1["nmse"]["a_only"], 1e-15))
    nm_b_db = 10.0 * np.log10(np.maximum(d_s1["nmse"]["b_only"], 1e-15))
    nm_sp_db = 10.0 * np.log10(np.maximum(d_s1["nmse"]["spatial_only"], 1e-15))
    nm_fl_db = 10.0 * np.log10(np.maximum(d_s1["nmse"]["full"], 1e-15))

    ci_share_a = paired_share_ci95(nm_dir_db - nm_a_db, nm_dir_db - nm_fl_db, seed=20261161)
    ci_share_b = paired_share_ci95(nm_dir_db - nm_b_db, nm_dir_db - nm_fl_db, seed=20261162)
    ci_cross_nmse = paired_diff_t_ci95(nm_sp_db - nm_fl_db)

    min_rival_ci_low_s1 = min(ci_rivals_s1[rk]["ci95"][0] for rk in legal_rivals)
    min_rival_ci_low_s2 = min(ci_rivals_s2[rk]["ci95"][0] for rk in legal_rivals)
    min_ab_ber_ci_low = min(ci_ab_ber_a["ci95"][0], ci_ab_ber_b["ci95"][0])

    v_beat_rivals = (min_rival_ci_low_s1 >= 10.0) and (min_rival_ci_low_s2 >= 10.0)
    v_ablation = (
        (ci_share_a["ci95"][1] < 0.80)
        and (ci_share_b["ci95"][1] < 0.80)
        and (min_ab_ber_ci_low >= 5.0)
    )
    v_cross_win = (
        (ci_diag_ber["ci95"][0] >= 4.0)
        and (ci_spat_ber["ci95"][0] >= 3.0)
        and (ci_cross_nmse["ci95"][0] >= 8.0)
    )
    v_shift_guard = ci_shift_ber["ci95"][0] >= 5.0
    v_clean = (clean_nmse_db_ci["ci95"][1] < -20.0) and (clean_ser_upper < 0.01)

    # Smoke runs NEVER produce formal PASS_PRIMARY == True!
    pass_primary = bool((not args.smoke) and v_redline1 and v_beat_rivals and v_ablation and v_cross_win and v_shift_guard and v_clean)

    summary = {
        "card_id": "I-20261125-g01",
        "group": "[放宽TWC]",
        "track": "[轨A-纯通信]",
        "smoke": args.smoke,
        "wall_time_s": float(time.time() - t_start),
        "redline1": rl1,
        "clean_sanity": {
            "n_frames": len(clean_ser_frame),
            "tot_sym": clean_sym,
            "ser_err": clean_ser_err,
            "SER_t_ci95": clean_t_ser,
            "SER_hoeffding_kl_ci95": clean_kl_ser,
            "SER_strict_upper975": clean_ser_upper,
            "NMSE_frame_dB_ci95": clean_nmse_db_ci,
            "NMSE_agg_dB": clean_agg_nmse_db,
        },
        "paired_ci95_checks": {
            "S1_rivals_over_full_BER": ci_rivals_s1,
            "S1_min_rival_ci95_low": min_rival_ci_low_s1,
            "S2_rivals_over_full_BER": ci_rivals_s2,
            "S2_min_rival_ci95_low": min_rival_ci_low_s2,
            "ablation_share_A_only": ci_share_a,
            "ablation_share_B_only": ci_share_b,
            "ablation_A_only_over_full_BER": ci_ab_ber_a,
            "ablation_B_only_over_full_BER": ci_ab_ber_b,
            "diag_over_full_BER": ci_diag_ber,
            "spatial_only_over_full_BER": ci_spat_ber,
            "spatial_only_minus_full_NMSE_dB": ci_cross_nmse,
            "shift_guard_over_full_BER": ci_shift_ber,
        },
        "scenarios": metrics,
        "verdicts": {
            "PASS_REDLINE1": bool(v_redline1),
            "PASS_RIVAL_10X": bool(v_beat_rivals),
            "PASS_ABLATION_80PCT": bool(v_ablation),
            "PASS_CROSS_WINDOW": bool(v_cross_win),
            "PASS_SHIFT_GUARD": bool(v_shift_guard),
            "PASS_CLEAN_SANITY": bool(v_clean),
            "PASS_PRIMARY": pass_primary,
        },
    }
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary["verdicts"], indent=2), flush=True)
    print("Saved summary to", args.out, "in", round(summary["wall_time_s"], 2), "s", flush=True)

if __name__ == "__main__":
    main()
