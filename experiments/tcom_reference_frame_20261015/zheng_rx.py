"""Zheng et al. 2025 (GLOBECOM, "Joint Channel Estimation and Data Detection for AFDM With Superimposed Pilots") in its OWN regime.

Self-contained numpy implementation, independent of the project's frozen AFDM code.  Equation numbers are the paper's
(papers/Zheng2025_GLOBECOM_JCED_AFDM_SP.pdf; extraction in .trellis/tasks/10-15-tcom-reference-frame/zheng2025-extraction.md).

System: N = 512, uncoded Gray QPSK, c1 = (2 alpha_max + 1) / (2 N), c2 = 1 / (2 pi N^2) (the paper only says "arbitrary irrational"),
A(m, n) = exp(-j 2 pi (c1 n^2 + m n / N + c2 m^2)) / sqrt(N).  P = 3 paths with distinct integer delays {0, 1, 2} (l_max = 2) and
random integer Doppler alpha_i in {-1, 0, 1} (alpha_max = 1), h_i ~ CN(0, 1/P), M_p = (2 alpha_max + 1)(l_max + 1) = 9.
Pilots (eq. 1): sigma_p / sqrt(M) at i = t (Q + 1), t = 0..M-1, with Q = M_p (the paper's lower bound, i.e. spacing 10); sigma_p^2 is the total
pilot energy.  Data power sigma_d^2 per symbol, noise variance sigma^2 = 1 in the DAFT domain (A is unitary).

Channel convention (verified numerically, see ``audit``): with the time-domain model of eq. (3), r[n] = sum_i h_i s_ext[n - l_i] exp(j 2 pi alpha_i n / N)
and the chirp-periodic prefix of eq. (6), the DAFT-domain operator of one path maps input index m to output index
m' = <m + alpha - 2 N c1 l>_N with value exp(j 2 pi (c1 l^2 - m l / N + c2 (m^2 - m'^2))).  This is eq. (5) with n (the paper's input-side index) =
m, the output index renamed m' and the sign of alpha flipped; alpha is uniform on {-1, 0, 1}, so the Monte-Carlo law is unchanged.  The estimator
grid (eqs. 8-11) is built from the time-domain definition (eq. 9) so it is exact for the same convention.

Receiver: Algorithm 1 (eqs. 18, 20-22, 24-33) with delta = .1, gamma = .1, epsilon = .2, i_m = 20, P = 3 known, K = 4.  Modes:
  'prop'    Algorithm 1 (interference-cancelled LS estimate inside the message-passing loop)
  'noic'    "SP without IC": h_hat from eq. (20) with x_bar_d = 0 at every iteration, same top-P selection and the same MP
  'perfect' perfect-CSI MP: the true H_eff and exact pilot cancellation, same MP and the same zeta control
"""
from __future__ import annotations

import numpy as np

QPSK_BITS = ((0, 0), (0, 1), (1, 0), (1, 1))


class Zheng:
    def __init__(self, N=512, alpha_max=1, l_max=2, P=3, c2=None, delta=.1, gamma=.1, eps=.2, i_max=20, spacing=None):
        self.N, self.alpha_max, self.l_max, self.P = int(N), int(alpha_max), int(l_max), int(P)
        self.K = 2 * self.alpha_max + 1                      # 2 N c1
        self.c1 = self.K / (2. * self.N)
        self.c2 = 1. / (2. * np.pi * self.N ** 2) if c2 is None else float(c2)
        self.Mp = self.K * (self.l_max + 1)
        self.delta, self.gamma, self.eps, self.i_max = float(delta), float(gamma), float(eps), int(i_max)
        self.spacing = self.Mp + 1 if spacing is None else int(spacing)   # Q + 1 with Q = M_p
        n = np.arange(self.N)
        self.n = n
        # grid element j (0-based): l_j = floor(j / K), alpha_j = <j>_K - alpha_max   (eqs. 10-11)
        self.grid_l = np.arange(self.Mp) // self.K
        self.grid_alpha = np.arange(self.Mp) % self.K - self.alpha_max
        self.shift = self.grid_alpha - self.K * self.grid_l            # output = <input + shift>_N
        self.dest = np.stack([(n + s) % self.N for s in self.shift])   # (Mp, N)
        self.phase = np.stack([np.exp(2j * np.pi * (self.c1 * l * l - n * l / self.N + self.c2 * (n.astype(float) ** 2 - ((n + s) % self.N).astype(float) ** 2)))
                               for l, s in zip(self.grid_l, self.shift)])  # (Mp, N)
        self.A = np.exp(-2j * np.pi * (self.c1 * n[None, :] ** 2 + np.outer(n, n) / self.N + self.c2 * n[:, None] ** 2)) / np.sqrt(self.N)
        qpsk = np.array([((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.) for b0, b1 in QPSK_BITS])
        self.qpsk = qpsk
        self._pilot_cache = {}

    # ------------------------------------------------------------------ channel operators
    def grid_index(self, l, alpha):
        return int(l * self.K + (alpha + self.alpha_max))

    def xi_apply(self, x, g):
        """Xi_g x for grid element g (closed form)."""
        y = np.zeros(self.N, complex)
        y[self.dest[g]] = self.phase[g] * x
        return y

    def heff_apply(self, x, grid_idx, gains):
        out = np.zeros(self.N, complex)
        for g, h in zip(grid_idx, gains):
            out += h * self.xi_apply(x, g)
        return out

    def xi_dense(self, g):
        """Eq. (9): Xi = A Gamma_CPP Delta_f Pi^l A^H (dense, for verification only)."""
        N, l, alpha = self.N, int(self.grid_l[g]), int(self.grid_alpha[g])
        n = np.arange(N)
        gamma = np.where(n < l, np.exp(-2j * np.pi * self.c1 * (N * N - 2 * N * (l - n))), 1.0)
        delta = np.exp(2j * np.pi * (alpha / N) * n)
        pi_l = np.roll(np.eye(N), l, axis=0)               # (Pi^l s)[n] = s[<n - l>_N]
        return self.A @ np.diag(gamma * delta) @ pi_l @ self.A.conj().T

    def heff_eq5_dense(self, grid_idx, gains):
        """Eq. (5) (input-side index n, output index m'; alpha sign as in eq. (3), see the module docstring)."""
        N = self.N
        H = np.zeros((N, N), complex)
        for g, h in zip(grid_idx, gains):
            l, alpha = int(self.grid_l[g]), int(self.grid_alpha[g])
            n = np.arange(N)
            mo = (n + alpha - self.K * l) % N
            H[mo, n] += h * np.exp(2j * np.pi / N * (N * self.c1 * l * l - n * l + N * self.c2 * (n.astype(float) ** 2 - mo.astype(float) ** 2)))
        return H

    def time_domain_output(self, x, grid_idx, gains, noise=None):
        """Eqs. (2)-(4): s = A^H x, chirp-periodic prefix, r[n] = sum h_i s_ext[n - l_i] e^{j 2 pi alpha_i n / N}, y = A r."""
        N = self.N
        s = self.A.conj().T @ x
        r = np.zeros(N, complex)
        n = np.arange(N)
        for g, h in zip(grid_idx, gains):
            l, alpha = int(self.grid_l[g]), int(self.grid_alpha[g])
            ext = np.where(n - l < 0, s[(n - l) % N] * np.exp(-2j * np.pi * self.c1 * (N * N - 2 * N * (l - n))), s[(n - l) % N])
            r += h * ext * np.exp(2j * np.pi * (alpha / N) * n)
        if noise is not None:
            r = r + noise
        return self.A @ r

    def audit(self, rng):
        """Formula audit: closed form vs eq. (9) dense, eq. (5) H_eff vs the time-domain model, and the literal eq. (5) readings."""
        grid = np.arange(self.Mp)
        err_closed = max(np.abs(self.xi_dense(g) - self.heff_eq5_dense([g], [1.])).max() for g in grid)
        picks = [self.grid_index(l, a) for l, a in zip(range(self.P), rng.integers(-self.alpha_max, self.alpha_max + 1, self.P))]
        gains = (rng.standard_normal(self.P) + 1j * rng.standard_normal(self.P)) / np.sqrt(2 * self.P)
        x = rng.standard_normal(self.N) + 1j * rng.standard_normal(self.N)
        H = self.heff_eq5_dense(picks, gains)
        err_time = np.abs(self.time_domain_output(x, picks, gains) - H @ x).max() / np.abs(H @ x).max()
        err_apply = np.abs(self.heff_apply(x, picks, gains) - H @ x).max() / np.abs(H @ x).max()
        # literal eq. (5) as printed: H_i(n, m) with row n = <m + alpha + 2 N c1 l>, phase (N c1 l^2 - n l + N c2 (n^2 - m^2))
        Hlit = np.zeros((self.N, self.N), complex)
        for g, h in zip(picks, gains):
            l, alpha = int(self.grid_l[g]), int(self.grid_alpha[g])
            m = np.arange(self.N)
            nn = (m + alpha + self.K * l) % self.N
            Hlit[nn, m] += h * np.exp(2j * np.pi / self.N * (self.N * self.c1 * l * l - nn * l + self.N * self.c2 * (nn.astype(float) ** 2 - m.astype(float) ** 2)))
        err_literal_rowcol = np.abs(Hlit @ x - H @ x).max() / np.abs(H @ x).max()
        return dict(closed_form_vs_eq9=float(err_closed), eq5_vs_time_domain=float(err_time), heff_apply_vs_eq5=float(err_apply),
                    literal_eq5_as_printed_vs_time_domain=float(err_literal_rowcol))

    # ------------------------------------------------------------------ pilots
    def pilot(self, M, sigma_p2):
        xp = np.zeros(self.N, complex)
        xp[np.arange(M) * self.spacing] = np.sqrt(sigma_p2 / M)
        return xp

    def pilot_matrix(self, M, sigma_p2):
        key = (M, float(sigma_p2))
        if key not in self._pilot_cache:
            xp = self.pilot(M, sigma_p2)
            Xp = np.column_stack([self.xi_apply(xp, g) for g in range(self.Mp)])   # eq. (13) with x -> x_p
            self._pilot_cache[key] = (xp, Xp, np.linalg.inv(Xp.conj().T @ Xp))
        return self._pilot_cache[key]

    # ------------------------------------------------------------------ data
    def modulate(self, bits, sigma_d2):
        b = np.asarray(bits).astype(np.int64).reshape(self.N, 2)   # int64: uint8 would wrap (1 - 2 b)
        return np.sqrt(sigma_d2) * ((1 - 2 * b[:, 0]) + 1j * (1 - 2 * b[:, 1])) / np.sqrt(2.)

    def demap_bits(self, k_idx):
        return np.array(QPSK_BITS, dtype=np.uint8)[np.asarray(k_idx)].reshape(-1)

    # ------------------------------------------------------------------ Algorithm 1
    def run(self, y, M, sigma_p2, sigma_d2, sigma2=1., mode='prop', true_grid=None, true_gains=None):
        """Returns dict(symbols (N,) argmax indices, bits, iterations, zeta_star, h_hat (M_p,), ind (final path set), h_hat_ic_free)."""
        N, P, K, Kp = self.N, self.P, 4, self.Mp
        a = np.sqrt(sigma_d2) * self.qpsk                       # (4,)
        a2 = np.abs(a) ** 2
        xp, Xp, Ginv = self.pilot_matrix(M, sigma_p2)
        XpH = Xp.conj().T
        p_msg = np.full((N, P, K), 1. / K)
        p_j = np.full((N, K), 1. / K)
        ind_prev, zeta_star = None, 0.
        prev_paths = None            # (grid indices, gains) of H_eff^{i-1}
        h_hat = np.zeros(Kp, complex)
        h_noic = None
        iters = 0
        n_idx = np.arange(N)
        for i in range(1, self.i_max + 1):
            iters = i
            # ---- channel estimate and path set
            if mode == 'prop':
                xbar = p_j @ a                                   # eq. (18)
                ic = 0. if prev_paths is None else self.heff_apply(xbar, *prev_paths)
                h_hat = Ginv @ (XpH @ (y - ic))                  # eq. (20)
            elif mode == 'noic':
                if h_noic is None:
                    h_noic = Ginv @ (XpH @ y)                    # eq. (20) with x_bar_d = 0
                h_hat = h_noic
            else:
                h_hat = np.zeros(Kp, complex)
                h_hat[true_grid] = true_gains
            ind = tuple(sorted(np.argsort(-np.abs(h_hat), kind='stable')[:P])) if mode != 'perfect' else tuple(sorted(true_grid))   # eq. (21)
            if ind != ind_prev:
                p_msg = np.full((N, P, K), 1. / K)              # reset to the uniform distribution
            gains = h_hat[list(ind)]
            prev_paths = (list(ind), gains)                      # eq. (22): H_eff^i for the next iteration's cancellation
            yd = y - self.heff_apply(xp, list(ind), gains)        # eq. (24)
            # ---- message passing
            sh = self.shift[list(ind)]
            Hval = np.stack([gains[p] * self.phase[ind[p]] for p in range(P)], axis=1)      # (N, P): H_eff(c_p(j), j)
            m_edge = p_msg @ a                                   # (N, P) mean of each variable->observation message
            e2 = p_msg @ a2
            t = m_edge * Hval
            v = np.abs(Hval) ** 2 * np.maximum(e2 - np.abs(m_edge) ** 2, 0.)
            T = np.zeros(N, complex)
            V = np.zeros(N)
            for p in range(P):
                T += np.roll(t[:, p], sh[p])                     # observation c collects the edge of variable (c - s_p)
                V += np.roll(v[:, p], sh[p])
            mu = np.stack([np.roll(T, -sh[p]) - t[:, p] for p in range(P)], axis=1)         # eq. (25)
            var = np.stack([np.roll(V, -sh[p]) - v[:, p] for p in range(P)], axis=1) + sigma2   # eq. (26)
            yd_edge = np.stack([np.roll(yd, -sh[p]) for p in range(P)], axis=1)
            logphi = -np.abs(yd_edge[:, :, None] - mu[:, :, None] - Hval[:, :, None] * a[None, None, :]) ** 2 / var[:, :, None]   # eq. (28), (N, P, K)
            S = logphi.sum(axis=1)                               # (N, K)
            ext = S[:, None, :] - logphi                         # eq. (27): product over e != c
            ext = np.exp(ext - ext.max(axis=2, keepdims=True))
            p_tilde_jc = ext / ext.sum(axis=2, keepdims=True)
            p_msg = (1. - self.delta) * p_msg + self.delta * p_tilde_jc   # eq. (29)
            marg = np.exp(S - S.max(axis=1, keepdims=True))      # eq. (30)
            p_tilde = marg / marg.sum(axis=1, keepdims=True)
            zeta = float(np.mean(1. - p_tilde.max(axis=1) < self.eps))    # eq. (31)
            zeta_before = zeta_star
            if zeta > zeta_before:
                p_j = p_tilde                                    # eq. (32)
            zeta_star = max(zeta_star, zeta)
            ind_prev = ind
            if zeta_before - zeta > self.gamma or zeta == 1.:
                break
        k_hat = np.argmax(p_j, axis=1)                           # eq. (33)
        return dict(k_idx=k_hat, bits=self.demap_bits(k_hat), iterations=iters, zeta_star=zeta_star, h_hat=h_hat, ind=ind, p_j=p_j, p_msg=p_msg)

    def topp(self, h_hat):
        out = np.zeros_like(h_hat)
        idx = np.argsort(-np.abs(h_hat), kind='stable')[:self.P]
        out[idx] = h_hat[idx]
        return out
