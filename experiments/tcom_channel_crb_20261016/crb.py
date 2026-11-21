"""Channel-estimation bounds for the production SP-AFDM model (task 10-16-tcom-channel-crb, protocol.md sections 1-2).

Model (physical.Channel): y = A T(theta) A^H x + w,  T = sum_i g_i T_i,  (T_i s)[k] = phi_{l_i}[k] e^{j2pi k nu_i/N} s[(k-l_i) mod N].
theta = (nu_1..nu_P, Re g_1..Re g_P, Im g_1..Im g_P); delays and P are given (genie); constraint sum |g_i|^2 = 1.

Everything here is pure numpy/scipy; the production regressors are passed in as a callable so that the gates can test
this module against the receiver's own code.  Conventions: sigma2 = E|w_k|^2 (complex circular), x = x_p + d with
E d = 0, E dd^H = (1 - rho) I.
"""
from __future__ import annotations

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp

COND_LIMIT = 1e10  # protocol section 2.3: a frame with cond(U^T J U) above this is flagged


# --------------------------------------------------------------------------- path-operator traces (section 2.1)
def gram_terms(delays, dopplers, coefs, dpows, n):
    """M[a, b] = conj(c_a) c_b tr((D^{p_a} T_a)^H D^{p_b} T_b) for operator terms (l_a, nu_a, c_a, p_a), p in {0, 1}.

    Different delays: the product is a non-identity cyclic shift times a diagonal -> trace exactly 0.
    Equal delays: the CPP phases cancel pointwise, leaving sum_k w_k e^{j2pi k (nu_b - nu_a)/N}.
    """
    l = np.asarray(delays, int)
    nu = np.asarray(dopplers, float)
    c = np.asarray(coefs, complex)
    p = np.asarray(dpows, int)
    k = np.arange(n)
    jw = 1j * 2. * np.pi * k / n                                  # diagonal of D
    w = np.where(p[:, None] == 1, jw[None, :], 1.)                # D^{p} diagonal per term
    phase = np.exp(2j * np.pi * k[None, :] * nu[:, None] / n)     # e^{j2pi k nu/N} per term
    a = w * phase                                                 # diagonal of D^{p} E_nu per term
    m = (a.conj() @ a.T) * (c.conj()[:, None] * c[None, :])
    return np.where(l[:, None] == l[None, :], m, 0.)


def frob2(delays, dopplers, gains, n):
    """||H||_F^2 of a path set (exact)."""
    g = np.asarray(gains, complex)
    return float(gram_terms(delays, dopplers, g, np.zeros(len(g), int), n).sum().real)


def channel_nmse(est, truth, n):
    """||H_est - H_true||_F^2 / ||H_true||_F^2 for arbitrary path sets {delays, dopplers, gains} (section 2.4)."""
    l = np.concatenate([np.asarray(est['delays'], int), np.asarray(truth['delays'], int)])
    nu = np.concatenate([np.asarray(est['dopplers'], float), np.asarray(truth['dopplers'], float)])
    c = np.concatenate([np.asarray(est['gains'], complex), -np.asarray(truth['gains'], complex)])
    err = float(gram_terms(l, nu, c, np.zeros(len(c), int), n).sum().real)
    return max(err, 0.) / frob2(truth['delays'], truth['dopplers'], truth['gains'], n)


def param_terms(delays, dopplers, gains):
    """Operator terms of d T / d theta in theta order (nu, Re g, Im g)."""
    l = np.asarray(delays, int)
    nu = np.asarray(dopplers, float)
    g = np.asarray(gains, complex)
    P = len(g)
    return (np.tile(l, 3), np.tile(nu, 3), np.concatenate([g, np.ones(P), 1j * np.ones(P)]),
            np.concatenate([np.ones(P, int), np.zeros(2 * P, int)]))


def gram_K(delays, dopplers, gains, n):
    """K_ab = tr((d_a H)^H d_b H) (complex Hermitian, 3P x 3P)."""
    return gram_terms(*param_terms(delays, dopplers, gains), n)


# --------------------------------------------------------------------------- regressors and FIMs (section 2.2)
def regressor_matrix(regress, u, gains):
    """B(u) = [R'(u) diag(g), R(u), j R(u)]; regress(u, derivative) returns the unit-gain production columns."""
    g = np.asarray(gains, complex)
    r = regress(u, False)
    rd = regress(u, True)
    return np.hstack([rd * g[None, :], r, 1j * r])


def fim_da(b_x, sigma2):
    return (2. / sigma2) * (b_x.conj().T @ b_x).real


def fim_mcrb(b_p, K, rho, sigma2, extra=None):
    """J_M = (2/sigma2) Re[B_p^H B_p + (1 - rho) K + extra]; extra = off-diagonal data-covariance term (amendment A1)."""
    j = (b_p.conj().T @ b_p).real + (1. - rho) * K.real
    if extra is not None:
        j = j + extra.real
    return (2. / sigma2) * j


def coded_offdiag(G, nsym, rho):
    """Exact off-diagonal E[d_s d_t^*] of d = sqrt(1 - rho) qpsk_map(G info), info uniform (amendment A1).

    G is k x n (columns = coded bits); qpsk_map puts bits 0..nsym-1 on I and nsym..2 nsym-1 on Q of symbol (i mod nsym).
    For a linear code two coded bits are perfectly correlated iff their columns are equal, otherwise uncorrelated.
    Returns {(s, t): R_st} for s != t (both orders).
    """
    G = np.asarray(G, np.uint8) % 2
    groups = {}
    for i in range(G.shape[1]):
        groups.setdefault(np.packbits(G[:, i]).tobytes(), []).append(i)
    out = {}
    for members in groups.values():
        for i in members:
            for j in members:
                si, sj = i % nsym, j % nsym
                if si == sj:
                    continue
                ui = 1. if i < nsym else 1j
                uj = 1. if j < nsym else 1j
                out[(si, sj)] = out.get((si, sj), 0.) + (1. - rho) / 2. * ui * np.conj(uj)
    return out


def mcrb_offdiag_term(regress, gains, offdiag, n):
    """sum_{s != t} R[t, s] B(e_s)^H B(e_t) for the few correlated symbol pairs."""
    syms = sorted({s for pair in offdiag for s in pair})
    cols = {}
    for s in syms:
        e = np.zeros(n, complex)
        e[s] = 1.
        cols[s] = regressor_matrix(regress, e, gains)
    m = len(np.asarray(gains)) * 3
    extra = np.zeros((m, m), complex)
    for (s, t), r_st in offdiag.items():
        extra += np.conj(r_st) * (cols[s].conj().T @ cols[t])  # R[t, s] = conj(R[s, t])
    return extra


def time_operator(delays, dopplers, gains, n, c1):
    """Sparse time-domain T = sum_i g_i T_i (same CPP phase as physical.Channel.apply)."""
    k = np.arange(n)
    rows, cols, vals = [], [], []
    for l, nu, g in zip(np.asarray(delays, int), np.asarray(dopplers, float), np.asarray(gains, complex)):
        cp = np.where(k < l, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (k - l))), 1.)
        rows.append(k)
        cols.append((k - l) % n)
        vals.append(g * cp * np.exp(2j * np.pi * k * nu / n))
    return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))


def param_time_operators(delays, dopplers, gains, n, c1):
    """Sparse d T / d theta_a in theta order."""
    k = np.arange(n)
    ops = []
    g = np.asarray(gains, complex)
    single = [time_operator([l], [nu], [1.], n, c1) for l, nu in zip(delays, dopplers)]
    dmat = sp.diags(1j * 2. * np.pi * k / n)
    ops += [(dmat @ s) * gi for s, gi in zip(single, g)]
    ops += single
    ops += [1j * s for s in single]
    return ops


def interference_cov(t_op, rho, sigma2):
    """Time-domain C = (1 - rho) T T^H + sigma2 I (unitarily equivalent to the DAFT-domain C)."""
    n = t_op.shape[0]
    return (1. - rho) * (t_op @ t_op.conj().T).toarray() + sigma2 * np.eye(n)


def fim_pi(b_p_time, cho):
    """2 Re[B_p^H C^{-1} B_p] with B_p in the time domain (A^H B_p) and a Cholesky factor of the time-domain C."""
    return 2. * (b_p_time.conj().T @ sla.cho_solve(cho, b_p_time)).real


def fim_gd_cov(t_op, d_ops, cho, rho):
    """Covariance (blind) term tr(C^{-1} d_a C C^{-1} d_b C), d_a C = (1 - rho)(S_a T^H + T S_a^H), via sparse products."""
    n = t_op.shape[0]
    z = sla.cho_solve(cho, np.eye(n))                                 # C^{-1} (Hermitian)
    th = t_op.conj().T.tocsc()
    zt = (t_op.T @ z.T).T                                             # Z T (dense @ sparse)
    mats = []
    for s in d_ops:
        zs = (s.T @ z.T).T                                            # Z S_a
        e1 = (th.T @ zs.T).T                                          # Z S_a T^H
        e2 = (s.conj() @ zt.T).T                                      # Z T S_a^H
        mats.append((1. - rho) * (e1 + e2))
    m = len(mats)
    out = np.empty((m, m))
    for a in range(m):
        for b in range(a, m):
            out[a, b] = out[b, a] = float(np.sum(mats[a] * mats[b].T).real)
    return out


# --------------------------------------------------------------------------- constrained CRB and H-level bound
def constraint_basis(gains):
    """Orthonormal basis of the tangent space of sum |g|^2 = 1 (columns orthogonal to [0, 2 Re g, 2 Im g])."""
    g = np.asarray(gains, complex)
    grad = np.concatenate([np.zeros(len(g)), 2 * g.real, 2 * g.imag])
    return sla.null_space(grad[None, :])


def h_bound(J, K, frob, U=None):
    """tr(CRB Re K) / ||H||_F^2 with CRB = J^{-1} (U None) or U (U^T J U)^{-1} U^T.  Returns (bound, cond)."""
    kr = K.real
    if U is None:
        cond = float(np.linalg.cond(J))
        crb = np.linalg.inv(J)
    else:
        jt = U.T @ J @ U
        cond = float(np.linalg.cond(jt))
        crb = U @ np.linalg.inv(jt) @ U.T
    return float(np.trace(crb @ kr)) / frob, cond


def bounds_pair(J, K, frob, U):
    """Constrained (primary) and unconstrained bounds plus the constrained condition number."""
    bc, cond = h_bound(J, K, frob, U)
    bu, _ = h_bound(J, K, frob, None)
    return dict(c=bc, u=bu, cond=cond, flagged=bool(cond > COND_LIMIT))
