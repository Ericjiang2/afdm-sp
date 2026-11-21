"""Gate U4 (section 2.2): toy exact falsification of E[l] <= I(d; y) by deterministic quadrature (N in {1, 2}) and Monte Carlo (N = 4, report-only).

Toy instance of the proposition: one tap (L = 1, delay 0, cp = 1), tap-gain sequence a ~ CN(0, R) with R = I_N ('flat') or R = 1 1^T ('rank1', constant tap),
unitary IDAFT W (N = 1: [1]; N = 2: DFT_2; N = 4: DFT_4), pilot pt = W sqrt(rho) z (z_k = exp(j pi k^2 / 2 ...), unit modulus), data x = sqrt(a) q, q i.i.d. unit-power QPSK,
y = diag(pt + W x) a + w, w ~ CN(0, sigma2 I), a_d = 1 - rho.   Same three terms as the screen:
  LB = E_h A(h) - E_d f(d) + J,  A = sum_i J_QPSK(a |R_ii|^2 / sigma2) (pivoted QR of G_h = diag(h) W), f = log2 det(I + C_s / sigma2), C_s = diag(s) R diag(s)^H,
  J = log2 det(Q + C_p) - log2 det Q, Q = sigma2 I + a diag(R_nn), C_p = diag(pt) R diag(pt)^H.
  MI = h(y) - h(y | d), y | d ~ CN(0, diag(s_d) R diag(s_d)^H + sigma2 I), h(y) = entropy of the 4^N-component equal-weight Gaussian mixture.
Quadrature (N <= 2): E_h A by QUADPACK (value + abs error estimate); h(y) by composite Gauss-Legendre in t_k = |y_k|^2 on geometric panels (+ periodic trapezoid in the relative phase
for the rank-1 case), error = |fine - coarse| of two grid refinements (+ tail bound).  The reported error bound of a case is err_LB + err_MI.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import scipy.linalg as sla
from scipy import integrate

import ib_screen_core as C


def dft_unitary(n):
    k = np.arange(n)
    return np.exp(-2j * np.pi * np.outer(k, k) / n) / math.sqrt(n)


def toy_setup(n, cov, rho, s2):
    a = 1. - rho
    W = np.array([[1. + 0j]]) if n == 1 else dft_unitary(n)
    z = np.exp(1j * np.pi * (np.arange(n) ** 2) / 2.)  # unit-modulus pilot (1, j, 1, j, ..)
    pt = W @ (math.sqrt(rho) * z)
    R = np.eye(n) if cov == 'flat' else np.ones((n, n))
    qp = np.array([(sx + 1j * sy) / math.sqrt(2.) for sx in (-1, 1) for sy in (-1, 1)])
    Q4 = np.array(list(itertools.product(range(4), repeat=n)))
    S = np.empty((4 ** n, n), complex)
    for i, idx in enumerate(Q4):
        S[i] = pt + W @ (math.sqrt(a) * qp[idx])
    return dict(n=n, a=a, rho=rho, s2=s2, W=W, pt=pt, R=R, S=S, qp=qp)


def logdet2(M):
    return float(np.linalg.slogdet(M)[1] / math.log(2.))


def toy_f_J(t):
    n, a, rho, s2, pt, R, S = (t[k] for k in ('n', 'a', 'rho', 's2', 'pt', 'R', 'S'))
    f = np.mean([logdet2(np.eye(n) + (s[:, None] * R * s.conj()[None, :]) / s2) for s in S])
    Q = s2 * np.eye(n) + a * np.diag(np.diag(R))
    Cp = pt[:, None] * R * pt.conj()[None, :]
    J = logdet2(Q + Cp) - logdet2(Q)
    return float(f), float(J)


def A_qr(h, t, tab):
    """A(h) by the same pivoted-QR routine as the screen (G_h = diag(h) W)."""
    G = h[:, None] * t['W']
    R = sla.qr(G, mode='r', pivoting=True, check_finite=False)[0]
    d = np.abs(np.diagonal(R)) ** 2
    return float(tab(t['a'] / t['s2'] * d).sum())


def A_closed(h, t, tab):
    """Closed forms (N = 1, N = 2 with W = DFT_2): equal to A_qr up to rounding (deterministic cross-check of the QR routine)."""
    a, s2 = t['a'], t['s2']
    if t['n'] == 1:
        return float(tab(np.array([a * abs(h[0]) ** 2 / s2]))[0])
    t1, t2 = abs(h[0]) ** 2, abs(h[1]) ** 2
    g = np.array([a * (t1 + t2) / (2. * s2), a * (2. * t1 * t2 / (t1 + t2)) / s2])
    return float(tab(g).sum())


def toy_EA(t, tab):
    """E_h A(h) by QUADPACK with error estimate (N = 1: t ~ Exp(1); N = 2 flat: (t1, t2) iid Exp(1); N = 2 rank-1: both taps equal)."""
    a, s2, n = t['a'], t['s2'], t['n']
    cov = 'flat' if np.allclose(t['R'], np.eye(n)) else 'rank1'
    sc = a / s2
    if n == 1:
        v, e = integrate.quad(lambda x: math.exp(-x) * tab(np.array([sc * x]))[0], 0., 80., epsabs=1e-13, epsrel=1e-12, limit=400)
        return v, e + math.exp(-80.) * 2.
    if cov == 'rank1':
        v, e = integrate.quad(lambda x: math.exp(-x) * 2. * tab(np.array([sc * x]))[0], 0., 80., epsabs=1e-13, epsrel=1e-12, limit=400)
        return v, e + math.exp(-80.) * 4.

    def inner(t2, t1):
        s = t1 + t2
        g = np.array([sc * s / 2., sc * 2. * t1 * t2 / s]) if s > 0 else np.zeros(2)
        return math.exp(-t1 - t2) * float(tab(g).sum())

    v, e = integrate.dblquad(inner, 0., 60., 0., 60., epsabs=1e-9, epsrel=1e-9)
    return v, e + 2. * math.exp(-60.) * 4.


def gl_panels(tmax, tmin, ratio, nodes):
    """composite Gauss-Legendre nodes/weights on [0, tmax]: first panel [0, tmin], then geometric panels (ratio)."""
    x0, w0 = np.polynomial.legendre.leggauss(nodes)
    edges = [0., tmin]
    while edges[-1] < tmax:
        edges.append(edges[-1] * ratio)
    xs, ws = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        xs.append(.5 * (hi - lo) * x0 + .5 * (hi + lo))
        ws.append(.5 * (hi - lo) * w0)
    return np.concatenate(xs), np.concatenate(ws), edges[-1]


def mixture_entropy_bits(t, panels, ntheta):
    """h(y) in bits by quadrature (see module docstring).  panels = (tmin_ratio, ratio, nodes)."""
    n, s2, S, R = t['n'], t['s2'], t['S'], t['R']
    M = S.shape[0]
    cov = 'flat' if np.allclose(R, np.eye(n)) else 'rank1'
    if n == 1:
        v = np.abs(S[:, 0]) ** 2 + s2
        tmax = 90. * v.max()
        ts, ws, tm = gl_panels(tmax, s2 / 4., panels[1], panels[2])
        p = np.sum(np.exp(-ts[:, None] / v[None, :]) / (math.pi * v[None, :]), axis=1) / M
        return float(-math.pi * np.sum(ws * p * np.log2(p))), tm
    if cov == 'flat':
        v = np.abs(S) ** 2 + s2  # (M, 2)
        tmax = 90. * v.max()
        ts, ws, tm = gl_panels(tmax, s2 / 4., panels[1], panels[2])
        e0 = np.exp(-ts[:, None] / v[None, :, 0]) / (math.pi * v[None, :, 0])  # (T, M)
        e1 = np.exp(-ts[:, None] / v[None, :, 1]) / (math.pi * v[None, :, 1])
        p = (e0 @ e1.T) / M  # sum_m e0[t1, m] e1[t2, m]
        return float(-math.pi ** 2 * np.einsum('i,j,ij->', ws, ws, p * np.log2(p))), tm
    # rank-1: y | d ~ CN(0, s s^H + s2 I);  p = exp(-(|y|^2 - |s^H y|^2 / (s2 + |s|^2)) / s2) / (pi^2 s2 (s2 + |s|^2))
    ns2 = np.sum(np.abs(S) ** 2, axis=1)  # (M,)
    tmax = 90. * (s2 + ns2.max())
    ts, ws, tm = gl_panels(tmax, s2 / 4., panels[1], panels[2])
    th = 2. * np.pi * (np.arange(ntheta) + .5) / ntheta
    absS = np.abs(S)
    psi = np.angle(S)
    total = 0.
    for i1, t1 in enumerate(ts):
        r1 = math.sqrt(t1)
        r2 = np.sqrt(ts)  # (T,)
        # |s^H y|^2 = |s1|^2 r1^2 + |s2|^2 r2^2 + 2 |s1||s2| r1 r2 cos(theta - psi1 + psi2)   (theta = phi1 - phi2)
        cross = 2. * (absS[:, 0] * absS[:, 1])[None, None, :] * (r1 * r2)[:, None, None] * np.cos(th[None, :, None] - (psi[:, 0] - psi[:, 1])[None, None, :])
        sy2 = (absS[:, 0] ** 2)[None, None, :] * t1 + (absS[:, 1] ** 2)[None, None, :] * ts[:, None, None] + cross  # (T, th, M)
        yy = (t1 + ts)[:, None, None]
        lq = -(yy - sy2 / (s2 + ns2)[None, None, :]) / s2 - np.log(math.pi ** 2 * s2 * (s2 + ns2))[None, None, :]
        lp = np.logaddexp.reduce(lq, axis=2) - math.log(M)  # (T, th), natural log of the mixture density
        total += ws[i1] * float(np.sum(ws[:, None] * np.exp(lp) * lp / math.log(2.)) * (2. * np.pi / ntheta))
    return float(-(math.pi / 2.) * total), tm


def theta_levels(s2):
    """periodic trapezoid nodes in the relative phase (rank-1 case): coarse / fine; the density concentrates in theta as sigma2 -> 0."""
    return [48, 96] if s2 >= 0.1 else [96, 192]


def toy_mi(t, fine=False):
    """(MI bits, error bound) with error = |fine - coarse| of h(y) (the h(y | d) term is a finite closed form)."""
    n, s2, S, R = t['n'], t['s2'], t['S'], t['R']
    h_cond = float(np.mean([logdet2(math.pi * math.e * (s[:, None] * R * s.conj()[None, :] + s2 * np.eye(n))) for s in S]))
    lvl = [(1.0, 1.6, 12), (1.0, 1.35, 16)] if n == 1 else [(1.0, 1.9, 10), (1.0, 1.5, 14)]
    ntheta = theta_levels(s2)
    hy = []
    for (a0, ratio, nodes), nth in zip(lvl, ntheta):
        hy.append(mixture_entropy_bits(t, (a0, ratio, nodes), nth)[0])
    return hy[1] - h_cond, abs(hy[1] - hy[0])


def toy_case(n, cov, rho, snr_db=None, s2=None, tab=None):
    s2 = 10. ** (-snr_db / 10.) if s2 is None else s2
    t = toy_setup(n, cov, rho, s2)
    f, J = toy_f_J(t)
    EA, eA = toy_EA(t, tab)
    LB = EA - f + J
    MI, eM = toy_mi(t)
    return dict(n=n, cov=cov, rho=rho, sigma2=s2, snr_db=snr_db, EA=EA, f=f, J=J, LB=LB, MI=MI, err_LB=eA, err_MI=eM, err=eA + eM, margin=MI - LB - (eA + eM),
                ok=bool(LB <= MI - (eA + eM)))


# ------------------------------------------------------------------------------------------------ N = 4 Monte Carlo (report only)
def toy_mc_n4(cov, rho, snr_db, tab, n_y=4000, n_h=4000, seed=11):
    t = toy_setup(4, cov, rho, 10. ** (-snr_db / 10.))
    rng = np.random.default_rng(seed)
    n, s2, S, R = 4, t['s2'], t['S'], t['R']
    M = S.shape[0]
    Sig = np.array([s[:, None] * R * s.conj()[None, :] + s2 * np.eye(n) for s in S])
    Lc = np.linalg.cholesky(Sig)
    logdet = 2. * np.sum(np.log(np.abs(np.diagonal(Lc, axis1=1, axis2=2))), axis=1)  # ln det Sigma_d
    idx = rng.integers(0, M, size=n_y)
    z = (rng.standard_normal((n_y, n)) + 1j * rng.standard_normal((n_y, n))) / math.sqrt(2.)
    y = np.einsum('kij,kj->ki', Lc[idx], z)
    sol = np.linalg.solve(Lc[None, :, :, :], y[:, None, :, None])[..., 0]  # (n_y, M, n)
    logp = -np.sum(np.abs(sol) ** 2, axis=2) - logdet[None, :] - n * math.log(math.pi)
    lpy = np.logaddexp.reduce(logp, axis=1) - math.log(M)
    info = (logp[np.arange(n_y), idx] - lpy) / math.log(2.)
    mi, mi_se = float(info.mean()), float(info.std(ddof=1) / math.sqrt(n_y))
    f, J = toy_f_J(t)
    rngh = np.random.default_rng(seed + 1)
    As = []
    for _ in range(n_h):
        h = (rngh.standard_normal(n) + 1j * rngh.standard_normal(n)) / math.sqrt(2.)
        if cov == 'rank1':
            h = np.full(n, h[0])
        As.append(A_qr(h, t, tab))
    As = np.array(As)
    EA, EA_se = float(As.mean()), float(As.std(ddof=1) / math.sqrt(n_h))
    LB = EA - f + J
    se = math.sqrt(mi_se ** 2 + EA_se ** 2)
    return dict(n=4, cov=cov, rho=rho, snr_db=snr_db, EA=EA, f=f, J=J, LB=LB, MI=mi, MI_se=mi_se, EA_se=EA_se, margin=mi - LB, margin_in_se=(mi - LB) / se)


def mixture_mass(t, ratio=1.5, nodes=14, ntheta=None):
    """normalisation check of the quadrature: integral of the mixture density (must be 1)."""
    n, s2, S, R = t['n'], t['s2'], t['S'], t['R']
    M = S.shape[0]
    ntheta = theta_levels(s2)[1] if ntheta is None else ntheta
    cov = 'flat' if np.allclose(R, np.eye(n)) else 'rank1'
    if n == 1:
        v = np.abs(S[:, 0]) ** 2 + s2
        ts, ws, _ = gl_panels(90. * v.max(), s2 / 4., ratio, nodes)
        p = np.sum(np.exp(-ts[:, None] / v[None, :]) / (math.pi * v[None, :]), axis=1) / M
        return float(math.pi * np.sum(ws * p))
    if cov == 'flat':
        v = np.abs(S) ** 2 + s2
        ts, ws, _ = gl_panels(90. * v.max(), s2 / 4., ratio, nodes)
        e0 = np.exp(-ts[:, None] / v[None, :, 0]) / (math.pi * v[None, :, 0])
        e1 = np.exp(-ts[:, None] / v[None, :, 1]) / (math.pi * v[None, :, 1])
        return float(math.pi ** 2 * np.einsum('i,j,ij->', ws, ws, (e0 @ e1.T) / M))
    ns2 = np.sum(np.abs(S) ** 2, axis=1)
    ts, ws, _ = gl_panels(90. * (s2 + ns2.max()), s2 / 4., ratio, nodes)
    th = 2. * np.pi * (np.arange(ntheta) + .5) / ntheta
    absS, psi = np.abs(S), np.angle(S)
    total = 0.
    for i1, t1 in enumerate(ts):
        cross = 2. * (absS[:, 0] * absS[:, 1])[None, None, :] * (math.sqrt(t1) * np.sqrt(ts))[:, None, None] * np.cos(th[None, :, None] - (psi[:, 0] - psi[:, 1])[None, None, :])
        sy2 = (absS[:, 0] ** 2)[None, None, :] * t1 + (absS[:, 1] ** 2)[None, None, :] * ts[:, None, None] + cross
        lq = -((t1 + ts)[:, None, None] - sy2 / (s2 + ns2)[None, None, :]) / s2 - np.log(math.pi ** 2 * s2 * (s2 + ns2))[None, None, :]
        total += ws[i1] * float(np.sum(ws[:, None] * np.exp(np.logaddexp.reduce(lq, axis=2) - math.log(M))) * (2. * np.pi / ntheta))
    return float((math.pi / 2.) * total)


def n1_mi_kl(t):
    """N = 1 independent check of the MI: I = (1/M) sum_k int pi p_k(t) log2(p_k(t) / p(t)) dt  (KL form, no entropy subtraction), QUADPACK."""
    s2, S = t['s2'], t['S']
    v = np.abs(S[:, 0]) ** 2 + s2
    M = len(v)

    def pk(x, k):
        return math.exp(-x / v[k]) / (math.pi * v[k])

    def integrand(x):
        p = sum(pk(x, k) for k in range(M)) / M
        return sum(math.pi * pk(x, k) * (math.log(pk(x, k)) - math.log(p)) for k in range(M)) / (M * math.log(2.))

    tmax = 90. * v.max()
    val, _ = integrate.quad(integrand, 0., tmax, points=sorted(set(float(x) for x in v)), epsabs=1e-14, epsrel=1e-12, limit=400)
    return float(val)
