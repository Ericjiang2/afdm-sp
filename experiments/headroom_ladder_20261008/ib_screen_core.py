"""Information-budget screen, core (task 10-08-doppler-cluster; research/info-budget-screen-20261014.md, FROZEN a34777b6).  Plain numpy/scipy, no frozen module imported.

Per-frame score (section 2, bits):   l = A(h) - f(d) + J(D)
  A(h)  = sum_i J_QPSK(a |R_ii|^2 / sigma2), G_h Pi = V R (pivoted QR, ordering from h only), G_h = the DAFT-domain data channel of the frame; J_QPSK = exact 4-point AWGN MI
  f(d)  = log2 det(I + C_s(d) / sigma2),    C_s = sum_l D_l(s) R_l D_l(s)^H,  D_l(s) = diag(cp_l * S_l s),  s = pt + xt
  J(D)  = log2 det(Q + C_p) - log2 det Q,   Q = sigma2 I + C_int,  C_int = a sum_l diag(R_l[n,n]),  C_p = sum_l D_l(pt) R_l D_l(pt)^H
Every reference has the same tap covariance for all taps, R_l = F F^H (F: N x r, real).  MODEL: F = sqrt(N) V_8 / sqrt(8 L) (8 DPSS, W = 2.5, flat I/K, K = 8L).
PHYS: R_l = (1/L) J0(4 pi (n - n') / N) (the generator's second-order statistics; numerical rank r_eff, eigenvalues > 1e-13 max).
Doppler unit (verified against driver_c1.draw_c1_paths / orders.tap_sequence): nu = 2 cos(theta) in cycles per frame, a_l[n] = sum g exp(2 pi i nu n / N).
All formulas in physical units (rho, a = 1 - rho, sigma2 = 10^(-SNR/10)); xt = IDAFT(x) with x i.i.d. unit-power QPSK scaled by sqrt(a); pt = sqrt(rho) IDAFT(ZC).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import time

import numpy as np
import scipy.linalg as sla
from scipy import integrate
from scipy.interpolate import CubicSpline
from scipy.special import j0

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'ib_screen'
N = 1024
ALPHA, TAU = 0.05, 1.0
LGRID = tuple(range(4, 97, 4))
CONDS = ((6.5, .2), (6.5, .3), (8., .2), (8., .3), (8., .5))
KC_BEST = {(6.5, .2): 201.0, (6.5, .3): 213.6, (8., .2): 254.2, (8., .3): 269.3, (8., .5): 222.9}
SEED_DOMAIN = 0x49425343  # "IBSC": own domain, distinct from C1 (0x43314254), DDST (0x44445354 / 0x5052...) and every [20260920, ...] stream
STAGE_ID = {'locate': 1, 'confirm': 2, 'test': 3, 'timing': 4}
COMP = {'delays': 1, 'data': 2, 'model': 3, 'phys': 4, 'rays': 5, 'noise': 6}
D_COEF, W_DPSS = 8, 2.5
REFS_DECISION = ('MODEL', 'PHYS')
N_STAGES = 2


# ----------------------------------------------------------------------------------------------------- constants / operators
class Consts:
    """Generator constants from out/ib_screen/consts.json (written by ib_screen_consts.py in the frozen context)."""

    def __init__(self, path=OUT / 'consts.json'):
        d = json.loads(Path(path).read_text())
        assert d['N'] == N
        self.c1, self.c2 = float(d['c1']), float(d['c2'])
        self.zc = np.array(d['zc_re']) + 1j * np.array(d['zc_im'])
        k = np.arange(N)
        self.k = k
        self.cl1 = np.conj(np.exp(2j * np.pi * self.c1 * k * k))
        self.cl2 = np.conj(np.exp(2j * np.pi * self.c2 * k * k))
        self.ptil = self.idaft(self.zc)  # IDAFT of the unit-modulus ZC pilot
        self._cp = {}

    def idaft(self, x):
        return self.cl1 * np.fft.ifft(self.cl2 * x) * np.sqrt(N)

    def cp(self, delays):
        """(N, L) CPP phases: exp(2 pi i c1 (N^2 + 2 N (k - l))) for k < l else 1 (tapchannel._cp)."""
        key = tuple(int(x) for x in delays)
        if key not in self._cp:
            if len(self._cp) > 64:
                self._cp.clear()
            wrap = self.k[:, None] - np.asarray(delays, int)[None, :]
            self._cp[key] = np.where(wrap < 0, np.exp(2j * np.pi * self.c1 * (N * N + 2 * N * wrap)), 1.)
        return self._cp[key]

    def u(self, v, delays):
        """(N, L) u_l(v) = cp_l * S_l v,  (S_l v)[k] = v[(k - l) mod N]."""
        return self.cp(delays) * v[(self.k[:, None] - np.asarray(delays, int)[None, :]) % N]


# ------------------------------------------------------------------------------------------------------------- QPSK MI table
def bpsk_mi(gamma):
    """(I_BPSK(gamma) bits, QUADPACK abs error estimate); y = sqrt(gamma) x + Z, Z ~ N(0,1), x = +-1:  I = 1 - E[log2(1 + exp(-2 gamma - 2 sqrt(gamma) Z))]."""
    sg = math.sqrt(gamma)

    def f(z):
        u = 2. * gamma + 2. * sg * z
        return math.exp(-.5 * z * z) / math.sqrt(2. * math.pi) * np.logaddexp(0., -u) / math.log(2.)

    lo, hi = -sg - 14., 14.
    pts = [-sg] if lo < -sg < hi else None
    val, err = integrate.quad(f, lo, hi, points=pts, epsabs=1e-14, epsrel=1e-12, limit=400)
    return 1. - val, err


class QpskMI:
    """J_QPSK(gamma) = 2 I_BPSK(gamma) (QPSK = two independent BPSK components of equal SNR gamma = E|x|^2 |g|^2 / sigma2).  Deterministic: QUADPACK at 4001 log-spaced
    nodes on [1e-8, 200] + cubic spline in log gamma; linear below 1e-8 (I = gamma/(2 ln2) per BPSK), 1 above 200 (1 - I < 1e-40 there)."""
    G_MIN, G_MAX, NODES = 1e-8, 200., 4001

    def __init__(self):
        self.xs = np.linspace(math.log(self.G_MIN), math.log(self.G_MAX), self.NODES)
        vals, errs = np.empty(self.NODES), np.empty(self.NODES)
        for i, x in enumerate(self.xs):
            vals[i], errs[i] = bpsk_mi(math.exp(x))
        self.vals = vals
        self.node_err_max = float(errs.max())
        self.spline = CubicSpline(self.xs, vals)
        self.slope = 1. / (2. * math.log(2.))

    def bpsk(self, g):
        g = np.asarray(g, float)
        out = np.empty_like(g)
        lo, hi = g < self.G_MIN, g > self.G_MAX
        mid = ~(lo | hi)
        out[lo] = self.slope * g[lo]
        out[hi] = 1.
        out[mid] = self.spline(np.log(g[mid]))
        return out

    def __call__(self, g):
        return 2. * self.bpsk(g)


# ------------------------------------------------------------------------------------------------------------- references
class Reference:
    """Tap covariance R_l = F F^H (the same for every tap, independent across taps).  F real (N, r)."""
    name = ''

    def factor(self, L):
        raise NotImplementedError

    def cvec(self, L):
        """c[n] = sum_l R_l[n, n]  (data-interference diagonal: C_int = a diag(c))."""
        F = self.factor(L)
        return L * np.sum(F * F, axis=1)

    def beta(self, L):
        F = self.factor(L)
        return L * float(np.max(np.sum(F * F, axis=1)))


class ModelRef(Reference):
    name = 'MODEL'

    def __init__(self):
        import dpss_rx  # frozen module imported only for the identical DPSS columns (pure numpy/scipy)
        self.M, _lam = dpss_rx.tap_columns(N, 0., W_DPSS, D_COEF)
        self.M = np.ascontiguousarray(self.M.real)

    def factor(self, L):
        return self.M / math.sqrt(D_COEF * L)


class PhysRef(Reference):
    name = 'PHYS'

    def __init__(self, thresh=1e-13):
        n = np.arange(N)
        Rn = j0(4. * np.pi * (n[:, None] - n[None, :]) / N)
        lam, V = np.linalg.eigh(Rn)
        lam, V = lam[::-1], V[:, ::-1]
        keep = lam > thresh * lam[0]
        self.lam = lam[keep]
        self.r = int(keep.sum())
        self.F1 = np.ascontiguousarray(V[:, keep] * np.sqrt(self.lam))  # R_unit = F1 F1^T (taps carry 1/L)
        self.V = np.ascontiguousarray(V[:, keep])
        self.trunc_err = float(np.max(np.abs(self.F1 @ self.F1.T - Rn)))

    def factor(self, L):
        return self.F1 / math.sqrt(L)


# ------------------------------------------------------------------------------------------------------------ randomness
def rng_for(stage, L, frame, comp):
    return np.random.default_rng(np.random.SeedSequence([20261014, SEED_DOMAIN, STAGE_ID[stage], int(L), int(frame), COMP[comp]]))


def draw_common(stage, L, frame):
    """Delays (C1 law: L distinct uniform on {0..100}, sorted) and i.i.d. unit-power QPSK, shared by all references and conditions of the frame."""
    delays = np.sort(rng_for(stage, L, frame, 'delays').choice(101, size=int(L), replace=False)).astype(int)
    bits = rng_for(stage, L, frame, 'data').integers(0, 2, size=(N, 2))
    q = ((2 * bits[:, 0] - 1) + 1j * (2 * bits[:, 1] - 1)) / math.sqrt(2.)
    return delays, q


def draw_xi(stage, L, frame, ref_name, r):
    rng = rng_for(stage, L, frame, ref_name.lower())
    return (rng.standard_normal((r, int(L))) + 1j * rng.standard_normal((r, int(L)))) / math.sqrt(2.)


def draw_rays(stage, L, frame):
    """RAY reference (the generator's law, own seed domain): per tap 1 + Poisson(3) rays, nu = 2 cos(theta), gain CN(0, 1/(L R)); returns a (N, L)."""
    rng = rng_for(stage, L, frame, 'rays')
    L = int(L)
    rays = 1 + rng.poisson(3, size=L)
    k = np.arange(N)
    a = np.empty((N, L), complex)
    for t in range(L):
        r = int(rays[t])
        theta = rng.uniform(0., 2. * np.pi, r)
        z = (rng.standard_normal(r) + 1j * rng.standard_normal(r)) / math.sqrt(2.)
        a[:, t] = np.exp(2j * np.pi * np.outer(k, 2. * np.cos(theta)) / N) @ (np.sqrt(1. / (L * r)) * z)
    return a


# ------------------------------------------------------------------------------------------------------------------- terms
def cond_arrays(conds=CONDS):
    snr = np.array([c[0] for c in conds])
    rho = np.array([c[1] for c in conds])
    return 10. ** (-snr / 10.), rho, 1. - rho


def build_G(consts, coef, delays):
    """DAFT-domain data channel G_h = Ht W from coef[:, i] = cp_l * a_l (N, L): Ht[k, (k - l) mod N] = coef; W = IDAFT matrix applied by FFT (G = ifft(Ht conj(l1)) conj(l2) sqrt(N))."""
    rows = np.arange(N)
    M1 = np.zeros((N, N), complex)
    for i, l in enumerate(np.asarray(delays, int)):
        M1[rows, (rows - l) % N] = coef[:, i]
    M1 *= consts.cl1[None, :]
    return np.fft.ifft(M1, axis=1) * (consts.cl2 * math.sqrt(N))[None, :]


def a_from_coef(consts, coef, delays, tab, conds=CONDS):
    """A(h) for every condition from the tap sequences: pivoted QR of G_h, chain rule in reverse order => sum_i J_QPSK(a |R_ii|^2 / sigma2).
    Returns (A per condition, |R_ii|^2 vector)."""
    return a_from_G(build_G(consts, coef, delays), tab, conds)


def a_from_G(G, tab, conds=CONDS, overwrite=True):
    n = G.shape[0]
    R = sla.qr(G, mode='r', pivoting=True, overwrite_a=overwrite, check_finite=False)[0]
    d = np.abs(np.diagonal(R)) ** 2
    s2, rho, a = cond_arrays(conds)
    gam = (a / s2)[:, None] * d[None, :]
    return tab(gam).sum(axis=1), d


def logdet2_chol(M):
    """log2 det of a Hermitian positive definite matrix via Cholesky."""
    Lc = sla.cholesky(M, lower=True, check_finite=False)
    return 2. * float(np.sum(np.log2(np.abs(np.diagonal(Lc).real)))), Lc


def f_and_j(consts, ref, L, delays, q, conds=CONDS, side='auto', k_switch=700):
    """f(d) and J(D) for every condition (N-side Hadamard form or K-side factor form; both exact, cross-checked in gate U1)."""
    s2, rho, a = cond_arrays(conds)
    F = ref.factor(L)
    r = F.shape[1]
    cvec = ref.cvec(L)
    xtil = consts.idaft(q)
    Up, Ux = consts.u(consts.ptil, delays), consts.u(xtil, delays)
    if side == 'auto':
        side = 'K' if L * r <= k_switch else 'N'
    nc = len(conds)
    f, J = np.empty(nc), np.empty(nc)
    if side == 'N':
        R = F @ F.T
        Xpp = R * (Up @ Up.conj().T)
        Xpx = R * (Up @ Ux.conj().T)
        Xxx = R * (Ux @ Ux.conj().T)
        idx = np.arange(N)
        for c in range(nc):
            Cs = rho[c] * Xpp + math.sqrt(rho[c] * a[c]) * (Xpx + Xpx.conj().T) + a[c] * Xxx
            Cs /= s2[c]
            Cs[idx, idx] += 1.
            f[c] = logdet2_chol(Cs)[0]
            Qd = s2[c] + a[c] * cvec
            M = rho[c] * Xpp
            M[idx, idx] += Qd
            J[c] = logdet2_chol(M)[0] - float(np.sum(np.log2(Qd)))
    else:
        Bp = (Up[:, :, None] * F[:, None, :]).reshape(N, L * r)
        Bx = (Ux[:, :, None] * F[:, None, :]).reshape(N, L * r)
        Gpp, Gpx, Gxx = Bp.conj().T @ Bp, Bp.conj().T @ Bx, Bx.conj().T @ Bx
        K = L * r
        idx = np.arange(K)
        const_c = bool(np.ptp(cvec) < 1e-10 * np.max(cvec))
        for c in range(nc):
            M = rho[c] * Gpp + math.sqrt(rho[c] * a[c]) * (Gpx + Gpx.conj().T) + a[c] * Gxx
            M /= s2[c]
            M[idx, idx] += 1.
            f[c] = logdet2_chol(M)[0]
            Qd = s2[c] + a[c] * cvec
            if const_c:
                Z = rho[c] * Gpp / Qd[0]
            else:
                Bw = Bp / np.sqrt(Qd)[:, None]
                Z = rho[c] * (Bw.conj().T @ Bw)
            Z[idx, idx] += 1.
            J[c] = logdet2_chol(Z)[0]
    return f, J, side


def gmi_terms(consts, G, q, stage, L, frame, conds=CONDS):
    """REPORT-ONLY: empirical GMI (bits, summed over the N symbols) of the LMMSE-output Gaussian metric for each condition, from one simulated observation
    (no bound guarantee).  x = sqrt(a) q, y_d = G x + w; x_hat = (G^H G + (s2/a) I)^-1 G^H y_d; z_m = mu_m x_m + residual, mu_m = B_mm, B = (G^H G + cI)^-1 G^H G,
    v_m = a (sum_j |B_mj|^2 - mu_m^2) + s2 ||w_m||^2; metric q(x', z) = exp(-|z - mu_m x'|^2 / v_m); GMI_m = log2 q(x_m, z_m) / mean_x' q(x', z_m)."""
    s2, rho, a = cond_arrays(conds)
    rng = rng_for(stage, L, frame, 'noise')
    xi = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / math.sqrt(2.)
    GhG = G.conj().T @ G
    lam, V = np.linalg.eigh((GhG + GhG.conj().T) / 2.)
    lam = np.maximum(lam, 0.)
    P = np.abs(V) ** 2
    Ghxi = G.conj().T @ xi
    Vh_q, Vh_n = V.conj().T @ q, V.conj().T @ Ghxi
    pts = np.array([(sx + 1j * sy) / math.sqrt(2.) for sx in (-1, 1) for sy in (-1, 1)])
    out = np.empty(len(conds))
    for c in range(len(conds)):
        cc = s2[c] / a[c]
        g1 = lam / (lam + cc)
        mu = P @ g1
        v = a[c] * np.maximum(P @ (g1 ** 2) - mu ** 2, 0.) + s2[c] * (P @ (lam / (lam + cc) ** 2))
        # z = B x + W w,  x = sqrt(a) q,  w = sqrt(s2) xi:  B x = V diag(g1) V^H x,  W w = V diag(1/(lam + cc)) V^H G^H w
        z = V @ (g1 * (math.sqrt(a[c]) * Vh_q)) + V @ ((math.sqrt(s2[c]) / (lam + cc)) * Vh_n)
        d2 = np.abs(z[:, None] - mu[:, None] * (math.sqrt(a[c]) * pts)[None, :]) ** 2 / v[:, None]  # (N, 4)
        true = np.argmax(np.abs(q[:, None] - pts[None, :]) < 1e-9, axis=1)
        log_q_true = -d2[np.arange(N), true]
        log_mean = np.logaddexp.reduce(-d2, axis=1) - math.log(4.)
        out[c] = float(np.sum(log_q_true - log_mean)) / math.log(2.)
    return out


def frame_terms(consts, tab, ref, stage, L, frame, common=None, conds=CONDS, side='auto', want_time=False, want_gmi=False):
    """All three terms for one frame, every condition (frames are shared across conditions).  Returns dict(A, f, J[, gmi][, sec])."""
    t0 = time.perf_counter()
    delays, q = common if common is not None else draw_common(stage, L, frame)
    F = ref.factor(L)
    xi = draw_xi(stage, L, frame, ref.name, F.shape[1])
    t1 = time.perf_counter()
    a_seq = F @ xi
    G = build_G(consts, consts.cp(delays) * a_seq, delays)
    A, _d = a_from_G(G.copy() if want_gmi else G, tab, conds)
    t2 = time.perf_counter()
    f, J, used = f_and_j(consts, ref, L, delays, q, conds, side)
    t3 = time.perf_counter()
    out = dict(A=A, f=f, J=J, side=used)
    if want_gmi:
        out['gmi'] = gmi_terms(consts, G, q, stage, L, frame, conds)
    t4 = time.perf_counter()
    if want_time:
        out['sec'] = dict(draw=t1 - t0, A=t2 - t1, fJ=t3 - t2, gmi=t4 - t3, total=t3 - t0)
    return out


# ---------------------------------------------------------------------------------------- RAY reference (report-only, X10)
def u_bound(consts, phys, L, delays, conds=CONDS):
    """U (>= E_d f(d) in expectation, valid for non-Gaussian taps; built from the PHYS second-order statistics), per condition:
    U = L sum_i log2(1 + a lam_i / s2) + log2 det(I_N + (rho / s2) Rr o (U_p U_p^H)),  Rr = R (I + (a / s2) R)^-1,  R = tap covariance."""
    s2, rho, a = cond_arrays(conds)
    lam = phys.lam / L
    V = phys.V
    Up = consts.u(consts.ptil, delays)
    Gpp = Up @ Up.conj().T
    idx = np.arange(N)
    U = np.empty(len(conds))
    for c in range(len(conds)):
        Rr = (V * (lam / (1. + a[c] * lam / s2[c]))[None, :]) @ V.T
        M = rho[c] / s2[c] * (Rr * Gpp)
        M[idx, idx] += 1.
        U[c] = L * float(np.sum(np.log2(1. + a[c] * lam / s2[c]))) + logdet2_chol(M)[0]
    return U


def ray_terms(consts, tab, phys, stage, L, frame, common=None, conds=CONDS):
    """A under the generator's ray law, U and J_z (weak T3 from the exactly Gaussian z = (a_l[0])_l).  Score_RAY = A - U + J_z.  Report-only (X10)."""
    delays, q = common if common is not None else draw_common(stage, L, frame)
    s2, rho, a = cond_arrays(conds)
    a_seq = draw_rays(stage, L, frame)
    A, _ = a_from_coef(consts, consts.cp(delays) * a_seq, delays, tab, conds)
    U = u_bound(consts, phys, L, delays, conds)
    F = phys.factor(L)
    R = F @ F.T
    Up = consts.u(consts.ptil, delays)
    Xpp = R * (Up @ Up.conj().T)
    idx = np.arange(N)
    R0 = R[0, :]
    Jz = np.empty(len(conds))
    for c in range(len(conds)):
        # J_z = -log2 det(I_L - L M_z),  M_z = G R_Y^-1 G^H,  G[l, m] = R_l[0, m] conj(sqrt(rho) u_l^p[m]),  R_Y = (s2 + a) I + rho Xpp
        RY = rho[c] * Xpp
        RY[idx, idx] += s2[c] + a[c]
        Lc = sla.cholesky(RY, lower=True, check_finite=False)
        G = (math.sqrt(rho[c]) * R0[:, None] * np.conj(Up)).T  # (L, N)
        Z = sla.solve_triangular(Lc, G.conj().T, lower=True, check_finite=False)  # (N, L)
        Mz = Z.conj().T @ Z
        E = np.eye(int(L)) - L * Mz
        E = (E + E.conj().T) / 2.
        Jz[c] = -logdet2_chol(E)[0]
    return dict(A=A, U=U, Jz=Jz)


# ------------------------------------------------------------------------------------------------------- Bernstein / stages
def eb_offset(S2, n, b, delta):
    """Maurer-Pontil empirical-Bernstein one-sided half-width for a variable of range b: sqrt(2 S2 ln(2/delta)/n) + 7 b ln(2/delta)/(3 (n-1))."""
    ln = math.log(2. / delta)
    return math.sqrt(2. * S2 * ln / n) + 7. * b * ln / (3. * (n - 1))


def term_ranges(ref, L, cond):
    snr, rho = cond
    s2, a = 10. ** (-snr / 10.), 1. - rho
    beta = ref.beta(L)
    return dict(A=2. * N, f=N * math.log2(1. + beta * (math.sqrt(rho) + math.sqrt(a)) ** 2 / s2), J=N * math.log2(1. + beta * rho / s2), beta=beta)


def n_endpoints():
    """one-sided endpoints of the whole screen: grid points x conditions x decision references x stages (the 9.5 dB / RAY report-only columns use the same delta)."""
    return len(LGRID) * len(CONDS) * len(REFS_DECISION) * N_STAGES


def delta_endpoint():
    return ALPHA / n_endpoints()


def lcb(A, f, J, ranges, delta_i=None):
    """LCB of E[l] = E A - E f + E J from n i.i.d. frames: empirical Bernstein for each of the three terms; the endpoint risk delta_i is split over the three terms
    (delta_i / 3 each, union bound) so that the endpoint fails with probability <= delta_i and sum delta_i <= ALPHA."""
    delta_i = delta_endpoint() if delta_i is None else delta_i
    d = delta_i / 3.
    A, f, J = (np.asarray(x, float) for x in (A, f, J))
    n = len(A)
    eA, ef, eJ = (eb_offset(float(np.var(x, ddof=1)), n, ranges[k], d) for x, k in ((A, 'A'), (f, 'f'), (J, 'J')))
    mean = float(A.mean() - f.mean() + J.mean())
    return dict(mean=mean, lcb=mean - eA - ef - eJ, eA=eA, ef=ef, eJ=eJ, n=n, mean_over_N=mean / N, lcb_over_N=(mean - eA - ef - eJ) / N)


def locate_passes(lcb_over_N, tau=TAU):
    """number of leading grid points whose LCB/N exceeds tau (K* = largest point such that it and every smaller point pass)."""
    m = 0
    for v in lcb_over_N:
        if v > tau:
            m += 1
        else:
            break
    return m


def confirm_plan(m_locate, G=len(LGRID)):
    """grid indices to confirm: 0..K*_loc+1 grid step (index m), or the first two points if the locate stage has no passing point."""
    if m_locate == 0:
        return [0, 1]
    return list(range(0, min(m_locate, G - 1) + 1))


def decide_kstar(confirm_lcb_over_N, plan, G=len(LGRID), tau=TAU):
    """confirm_lcb_over_N: dict grid index -> LCB/N.  Returns (K* grid index or None, status): 'none' (smallest confirmed point fails: no K*), 'exact' (K* = the point before the
    first failing confirmed point), 'right_censored' (all confirmed points pass and the grid is not exhausted: K* >= last confirmed point), 'grid_end' (all pass up to the last grid point)."""
    first_fail = None
    for j in plan:
        if not confirm_lcb_over_N[j] > tau:
            first_fail = j
            break
    if first_fail is not None:
        return (None, 'none') if first_fail == 0 else (first_fail - 1, 'exact')
    last = plan[-1]
    return (last, 'grid_end') if last == G - 1 else (last, 'right_censored')


def classify(h_low):
    """section 6, per reference: INFO-HEADROOM (H_low >= 1.25 in >= 4/5), else WEAK (>= 1.10 in >= 4/5), else UNINFORMATIVE; None (no K*) never counts."""
    ok = lambda thr: sum(1 for h in h_low if h is not None and h >= thr)
    if ok(1.25) >= 4:
        return 'INFO-HEADROOM'
    if ok(1.10) >= 4:
        return 'WEAK'
    return 'UNINFORMATIVE'
