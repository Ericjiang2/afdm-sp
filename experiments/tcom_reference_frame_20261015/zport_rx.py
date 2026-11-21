"""Port of Zheng et al. 2025 Algorithm 1 to the P1 channels (protocol.md I4 + A2): N = 1024, production c1 / c2, alpha_max = 2, l_max = 102, P = 8 known.

Numpy only; independent of the frozen receivers.  The operator convention is the production one (supplement_g1.physical_channel_matrix):
one path (l, nu) maps input n to output m with
    H(m, n) = kernel_a[(m - n) mod N] * exp(-j 2 pi (c1 l^2 + l n / N)) * exp(j 2 pi c2 (m^2 - n^2)),   a = nu + 2 N c1 l,
    kernel_a = fft(exp(j 2 pi a t / N)) / N   (Dirichlet kernel; sum |kernel|^2 = 1),
so an integer nu gives one nonzero per column (the Xi_j of eq. 9 for the integer grid) and a fractional nu a dense column with sinc tails.
This is verified against the physical CPP propagation in ZP-G1.

Frame: single DAFT-domain pilot impulse at index 0 with energy rho N (the only pilot that fits when Q >= M_p = 515), data sqrt(1 - rho) QPSK on all N symbols,
superimposed; noise variance sigma2 = 10^(-SNR/10); the receiver knows sigma2.

Grids: 'int' = delays 0..102 x integer Doppler -2..2 (M_p = 515, eq. 7); 'frac' = delays 0..102 x Doppler -3..3 step 0.25 (2575 atoms).
Estimator (eq. 20 generalised): z = y - H_hat^{i-1} x_bar (exact operator); matched-filter values h_mf = X_p,unit^H z / A (A = sqrt(rho N); for the
orthogonal integer grid this is exactly eq. 20); the P largest |h_mf| form Ind (eq. 21); the gains are then re-solved by joint LS on the selected
atoms (identical to eq. 20 on the orthogonal integer grid, the consistent choice when the fractional columns overlap).
Z-OMP (select='omp', our adaptation, protocol A3): on the fractional grid, successive selection instead of the top-P rule: pick the atom with the largest
correlation with the current pilot-domain residual, re-solve the joint LS on all atoms selected so far, update the residual (z minus the selected atoms'
pilot response), repeat until P atoms are selected.  Everything else is identical to Z-adapted.  The residual correlations are evaluated through the
Gram matrix of the pilot dictionary: X_p,unit^H r = c0 - A G[:, S] g with c0 = X_p,unit^H z (exact, no approximation).
MP (eqs. 25-30, 29 with delta_new, 31-33): the graph uses H_eff with every selected atom's column truncated to +-band DAFT bins around its main lobe
(band 0 for the integer grid = exactly one edge per atom; band 4 for the fractional grid); the pilot cancellation (eq. 24) and the interference
cancellation of eq. (20) use the exact untruncated operator.  Convergence control of eqs. 31-32 with gamma = .1, epsilon = .2, i_m = 20.
Optional symbol priors (Z-turbo): the log prior is added to eqs. (27), (30) and initialises the messages.
"""
from __future__ import annotations

import numpy as np

QPSK_BITS = ((0, 0), (0, 1), (1, 0), (1, 1))


class ZPort:
    def __init__(self, c1, c2, N=1024, P=8, delta_new=.1, gamma=.1, eps=.2, i_max=20, l_max=102, alpha_max=2, band_frac=4):
        self.N, self.P = int(N), int(P)
        self.c1, self.c2 = float(c1), float(c2)
        self.K = 2 * alpha_max + 1
        if abs(2 * self.N * self.c1 - self.K) > 1e-9:
            raise ValueError('production c1 must equal (2 alpha_max + 1) / (2 N)')
        self.l_max, self.alpha_max = int(l_max), int(alpha_max)
        self.delta, self.gamma, self.eps, self.i_max = float(delta_new), float(gamma), float(eps), int(i_max)
        self.band_frac = int(band_frac)
        n = np.arange(self.N)
        self.n = n
        self.chirp = np.exp(2j * np.pi * self.c2 * n.astype(float) ** 2)
        self.cchirp = np.conj(self.chirp)
        self.phase_l = np.stack([np.exp(-2j * np.pi * (self.c1 * l * l + l * n / self.N)) for l in range(self.l_max + 1)])   # (l_max + 1, N)
        self.qpsk = np.array([((1 - 2 * b0) + 1j * (1 - 2 * b1)) / np.sqrt(2.) for b0, b1 in QPSK_BITS])
        li = np.repeat(np.arange(self.l_max + 1), self.K)
        self.grid = {'int': (li, np.tile(np.arange(-alpha_max, alpha_max + 1, dtype=float), self.l_max + 1))}
        nu_f = np.arange(-3., 3. + 1e-9, .25)
        self.grid['frac'] = (np.repeat(np.arange(self.l_max + 1), len(nu_f)), np.tile(nu_f, self.l_max + 1))
        self._xu = {}
        self._gram = {}
        self._kern = {}
        self._idx = np.arange(self.N)

    # ------------------------------------------------------------------ operator
    def kernel(self, a):
        key = round(float(a), 9)
        k = self._kern.get(key)
        if k is None:
            k = np.fft.fft(np.exp(2j * np.pi * float(a) * self._idx / self.N)) / self.N
            if len(self._kern) < 4000:
                self._kern[key] = k
        return k

    def apply_atom(self, x, l, nu):
        """Exact single-path operator (unit gain) applied to x."""
        a = nu + self.K * l
        w = self.phase_l[l] * self.cchirp * x
        if float(nu) == round(float(nu)):                         # integer Doppler: one nonzero per column
            y = np.zeros(self.N, complex)
            y[(self._idx + int(round(a))) % self.N] = w
            return self.chirp * y
        return self.chirp * np.fft.ifft(np.fft.fft(self.kernel(a)) * np.fft.fft(w))

    def apply(self, x, ls, nus, gains):
        out = np.zeros(self.N, complex)
        for l, nu, g in zip(ls, nus, gains):
            out += g * self.apply_atom(x, int(l), float(nu))
        return out

    def pilot_unit(self, grid):
        """Xi_j e_0 for every atom of the grid: (N, G).  Column j = kernel_a[m] chirp[m] exp(-j 2 pi c1 l^2)."""
        if grid not in self._xu:
            ls, nus = self.grid[grid]
            a = nus + self.K * ls
            e = np.exp(2j * np.pi * a[:, None] * self._idx[None, :] / self.N)
            ker = np.fft.fft(e, axis=1) / self.N                                       # (G, N): kernel_a[m]
            self._xu[grid] = (ker * (self.chirp[None, :] * np.exp(-2j * np.pi * self.c1 * ls.astype(float) ** 2)[:, None])).T
        return self._xu[grid]

    def pilot_gram(self, grid):
        if grid not in self._gram:
            Xu = self.pilot_unit(grid)
            self._gram[grid] = Xu.conj().T @ Xu
        return self._gram[grid]

    def omp_select(self, Xu, G, z, A, P):
        """Successive selection (Z-OMP).  Returns (sorted atom indices, joint-LS gains in that order)."""
        c0 = Xu.conj().T @ z
        corr = c0.copy()
        sel = []
        for _ in range(P):
            mag = np.abs(corr)
            mag[sel] = -1.
            sel.append(int(np.argmax(mag)))
            gs = np.linalg.lstsq(G[np.ix_(sel, sel)], c0[sel], rcond=1e-12)[0] / A
            corr = c0 - A * (G[:, sel] @ gs)
        order = np.sort(np.asarray(sel))
        gains = np.linalg.lstsq(G[np.ix_(order, order)], c0[order], rcond=1e-12)[0] / A
        return order, gains

    # ------------------------------------------------------------------ band edges for MP
    def band_edges(self, ls, nus, gains, band):
        """Truncated H_eff as edges: shifts D (U,) and values H (N, U) with H[j, u] = H_eff((j + D[u]) mod N, j); also the kept-energy fraction per atom."""
        N = self.N
        d_all, p_all, k_all = [], [], []
        kept = np.zeros(len(ls))
        for p, (l, nu) in enumerate(zip(ls, nus)):
            a = float(nu) + self.K * int(l)
            centre = int(np.floor(a + .5))
            d = np.arange(centre - band, centre + band + 1)
            ker = self.kernel(a)
            kv = ker[d % N]
            kept[p] = float(np.sum(np.abs(kv) ** 2))
            d_all.append(d)
            p_all.append(np.full(len(d), p))
            k_all.append(kv)
        d_all, p_all, k_all = np.concatenate(d_all), np.concatenate(p_all), np.concatenate(k_all)
        uniq, inv = np.unique(d_all, return_inverse=True)
        H = np.zeros((N, len(uniq)), complex)
        for t in range(len(d_all)):
            p = p_all[t]
            d = int(d_all[t])
            H[:, inv[t]] += gains[p] * k_all[t] * self.phase_l[int(ls[p])] * self.chirp[(self._idx + d) % N] * self.cchirp
        return uniq, H, kept

    def kept_fraction(self, ls, nus, band):
        """Per atom: energy fraction of its (unit-energy) column inside the +-band bins around the main lobe."""
        out = np.zeros(len(ls))
        for p, (l, nu) in enumerate(zip(ls, nus)):
            a = float(nu) + self.K * int(l)
            centre = int(np.floor(a + .5))
            out[p] = float(np.sum(np.abs(self.kernel(a)[np.arange(centre - band, centre + band + 1) % self.N]) ** 2))
        return out

    def truncated_fraction(self, ls, nus, gains, band):
        """Energy fraction of the channel outside the +-band bins (power-weighted over the paths)."""
        g2 = np.abs(np.asarray(gains)) ** 2
        return float(np.sum(g2 * (1. - self.kept_fraction(ls, nus, band))) / np.sum(g2)) if g2.sum() > 0 else 0.

    # ------------------------------------------------------------------ Algorithm 1
    def run(self, y, rho, sigma2, grid, prior=None, truth=None, select='top'):
        """Z-faithful (grid 'int') / Z-adapted (grid 'frac').  truth = (ls, nus, gains): use the true path set and gains (no estimation).

        Returns dict(p_j (N, 4), iterations, zeta_star, ls, nus (selected atoms), gains, trunc_est, ...)."""
        N, P = self.N, self.P
        a = np.sqrt(1. - rho) * self.qpsk
        a2 = np.abs(a) ** 2
        A = np.sqrt(rho * N)
        band = 0 if grid == 'int' else self.band_frac
        Xu = self.pilot_unit(grid)
        gl, gnu = self.grid[grid]
        lp = np.log(prior + 1e-300) if prior is not None else 0.
        p_j = np.full((N, 4), .25) if prior is None else prior.copy()
        p_msg = None
        ind_prev, zeta_star = None, 0.
        prev_atoms = None
        iters = 0
        edges = None
        ls_sel = nus_sel = gains = None
        trunc_est = 0.
        for i in range(1, self.i_max + 1):
            iters = i
            # ---- channel estimate (eq. 20) and path set (eq. 21)
            if truth is None:
                xbar = p_j @ a
                ic = 0. if prev_atoms is None else self.apply(xbar, *prev_atoms)
                z = y - ic
                if select == 'omp':
                    sel, gains = self.omp_select(Xu, self.pilot_gram(grid), z, A, P)
                else:
                    h_mf = (Xu.conj().T @ z) / A
                    sel = np.sort(np.argsort(-np.abs(h_mf), kind='stable')[:P])
                    cols = A * Xu[:, sel]
                    gains = np.linalg.lstsq(cols, z, rcond=None)[0] if grid == 'frac' else h_mf[sel]    # orthogonal integer grid: eq. (20) exactly
                ind = tuple(int(s) for s in sel)
                ls_sel, nus_sel = gl[sel], gnu[sel]
            else:
                ls_sel, nus_sel, gains = truth
                ind = ('truth',)
            if truth is None or edges is None:
                D, H, kept = self.band_edges(ls_sel, nus_sel, gains, band)
                edges = (D, H, kept)
                if truth is not None:
                    pil = np.zeros(N, complex)
                    for l, nu, g in zip(ls_sel, nus_sel, gains):      # eq. (24): exact pilot cancellation, x_p = A e_0
                        pil += g * A * self._atom_column0(int(l), float(nu))
                    pil_truth = pil
            else:
                D, H, kept = edges
            if ind != ind_prev or p_msg is None:
                p_msg = np.full((N, len(D), 4), .25) if prior is None else np.repeat(prior[:, None, :], len(D), axis=1)
            trunc_est = float(np.sum(np.abs(gains) ** 2 * (1. - kept)) / np.sum(np.abs(gains) ** 2))
            prev_atoms = (ls_sel, nus_sel, gains)
            if truth is None:
                pil = A * (Xu[:, sel] @ gains)                        # eq. (24): exact pilot cancellation, x_p = A e_0
            else:
                pil = pil_truth
            yd = y - pil
            # ---- message passing on the truncated graph
            U = len(D)
            idx_fwd = (self._idx[:, None] - D[None, :]) % N       # observation c <- variable (c - D[u]) on edge u
            idx_bwd = (self._idx[:, None] + D[None, :]) % N       # variable j -> observation (j + D[u])
            cols_u = np.arange(U)[None, :]
            m_edge = p_msg @ a
            e2 = p_msg @ a2
            t = m_edge * H
            v = np.abs(H) ** 2 * np.maximum(e2 - np.abs(m_edge) ** 2, 0.)
            T = t[idx_fwd, cols_u].sum(axis=1)
            V = v[idx_fwd, cols_u].sum(axis=1)
            mu = T[idx_bwd] - t                                    # eq. (25)
            var = V[idx_bwd] - v + sigma2                          # eq. (26)
            yd_edge = yd[idx_bwd]
            logphi = -np.abs(yd_edge[:, :, None] - mu[:, :, None] - H[:, :, None] * a[None, None, :]) ** 2 / var[:, :, None]   # eq. (28)
            S = logphi.sum(axis=1)
            ext = S[:, None, :] - logphi + (lp[:, None, :] if prior is not None else 0.)              # eq. (27) (with the prior for Z-turbo)
            ext = np.exp(ext - ext.max(axis=2, keepdims=True))
            p_tilde_jc = ext / ext.sum(axis=2, keepdims=True)
            p_msg = (1. - self.delta) * p_msg + self.delta * p_tilde_jc   # eq. (29)
            sm = S + lp if prior is not None else S
            marg = np.exp(sm - sm.max(axis=1, keepdims=True))    # eq. (30)
            p_tilde = marg / marg.sum(axis=1, keepdims=True)
            zeta = float(np.mean(1. - p_tilde.max(axis=1) < self.eps))   # eq. (31)
            zeta_before = zeta_star
            if zeta > zeta_before:
                p_j = p_tilde                                      # eq. (32)
            zeta_star = max(zeta_star, zeta)
            ind_prev = ind
            if truth is not None:
                ind_prev = ('truth',)
            if zeta_before - zeta > self.gamma or zeta == 1.:
                break
        return dict(p_j=p_j, iterations=iters, zeta_star=zeta_star, ls=np.asarray(ls_sel), nus=np.asarray(nus_sel), gains=np.asarray(gains),
                    trunc_est=trunc_est, edges=int(len(D)))

    def _atom_column0(self, l, nu):
        """Xi(l, nu) e_0 (exact), the response of a unit impulse at index 0."""
        a = nu + self.K * l
        return self.kernel(a) * self.chirp * np.exp(-2j * np.pi * self.c1 * l * l)

    # ------------------------------------------------------------------ bits
    @staticmethod
    def llr_from_posterior(p_j, clip=20.):
        """Bit LLRs log P(b=0)/P(b=1), order [all I bits, all Q bits] (the project's mapping), exact log-sum over QPSK, clipped to +-clip."""
        p = np.maximum(p_j, 1e-300)
        # symbol k <-> (b0 [real], b1 [imag]) = QPSK_BITS[k]
        l_i = np.log(p[:, 0] + p[:, 1]) - np.log(p[:, 2] + p[:, 3])
        l_q = np.log(p[:, 0] + p[:, 2]) - np.log(p[:, 1] + p[:, 3])
        return np.clip(np.concatenate([l_i, l_q]), -clip, clip)

    @staticmethod
    def prior_from_llr(llr, clip=20.):
        """Symbol prior (N, 4) from independent I / Q bit LLRs (log P0/P1)."""
        n = len(llr) // 2
        l = np.clip(llr, -clip, clip)
        p0 = 1. / (1. + np.exp(-l))                               # P(b = 0)
        pi, pq = p0[:n], p0[n:]
        out = np.stack([pi * pq, pi * (1 - pq), (1 - pi) * pq, (1 - pi) * (1 - pq)], axis=1)
        return out / out.sum(axis=1, keepdims=True)
