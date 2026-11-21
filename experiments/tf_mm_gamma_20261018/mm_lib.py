"""Model-matched check of the full Gamma (task 10-18-model-matched-gamma): library part.  numpy/scipy only.

  sample_qpsk / sampler_moments   per-symbol QPSK posterior sampler consistent with ``messages.moments(L, pd)``
  eiv_bound / standard_sbl_ll     the EIV EM lower bound L(beta, gamma) (textbook evaluation) and the standard SBL marginal -log det C - Y^H C^-1 Y
  sbl_em_traced                   the frozen ``sbl_rx.sbl_em`` arithmetic, verbatim, plus the bound after every E-step (outputs bit-identical)
  eiv_summary                     monotonicity readout of a bound trace
The frozen E-3 code (``tf_e3_sbl_20261017``) is imported read-only (sbl_rx); nothing there is edited.
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import scipy.linalg as sla
from scipy.linalg import lapack
from scipy.special import expit

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
E3_DIR = EXPERIMENTS / 'tf_e3_sbl_20261017'
if str(E3_DIR) not in sys.path:
    sys.path.insert(0, str(E3_DIR))
import e3_lib  # noqa: E402  (frozen E-3 helper)

e3_lib.prepare_paths()
import sbl_rx as sbl  # noqa: E402  (frozen E-3 SBL core: sbl_em, screen, select_output, codelay_pairs, hard_decision, columns, gamma_full)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

VIOLATION_TOL = 1e-9     # a transition L_{t+1} < L_t - tol * max(1, |L_t|) counts as a monotonicity violation (frozen)


# ----------------------------------------------------------------------------- posterior sampler
def sample_qpsk(L, pd, rng):
    """One draw of x~ from the per-symbol QPSK posterior implied by the grouped LLR vector L (all-I-then-all-Q; L > 0 means bit zero; the same
    convention as ``messages.logprior``): Re x~ = +a with probability sigma(L_I) else -a, Im x~ = +a with probability sigma(L_Q) else -a,
    a = sqrt(pd / 2).  This is the distribution ``messages.moments`` integrates (the four-point posterior factorises over the two bits)."""
    L = np.asarray(L, dtype=float)
    n = len(L) // 2
    a = np.sqrt(pd / 2.0)
    re = np.where(rng.random(n) < expit(L[:n]), 1.0, -1.0)
    im = np.where(rng.random(n) < expit(L[n:]), 1.0, -1.0)
    return a * (re + 1j * im)


def sampler_moments(L, pd):
    """Exact mean and total variance E|x~ - E x~|^2 of ``sample_qpsk`` (closed form, independent of ``messages.moments``)."""
    L = np.asarray(L, dtype=float)
    n = len(L) // 2
    a = np.sqrt(pd / 2.0)
    ti, tq = np.tanh(L[:n] / 2.0), np.tanh(L[n:] / 2.0)
    return a * (ti + 1j * tq), a * a * ((1.0 - ti * ti) + (1.0 - tq * tq))


# ----------------------------------------------------------------------------- the EIV EM lower bound
def eiv_bound(B, Y, beta, gamma, Gamma=None):
    """L(beta, gamma) = N log beta - log det(Lambda) - log det(A) - beta ||Y||^2 + beta^2 b^H A^-1 b,   A = beta (B^H B + Gamma) + Lambda^-1,
    b = B^H Y, Lambda = diag(gamma).  Textbook evaluation (explicit slogdet / solve).  It is  max_q F(q; beta, gamma) - (-N log pi)  where F is the
    EM objective of the errors-in-variables model (PROTOCOL.md section 3); for Gamma = 0 it equals -log det C - Y^H C^-1 Y, C = I/beta + B Lambda B^H."""
    B = np.asarray(B, dtype=np.complex128)
    Y = np.asarray(Y, dtype=np.complex128)
    gamma = np.asarray(gamma, dtype=float)
    n, m = B.shape
    G = B.conj().T @ B
    if Gamma is not None:
        G = G + np.asarray(Gamma, dtype=np.complex128)
    G = (G + G.conj().T) / 2
    A = beta * G + np.diag(1.0 / gamma)
    b = B.conj().T @ Y
    sign, logdet_a = np.linalg.slogdet(A)
    assert abs(sign - 1) < 1e-9, 'A is not positive definite'
    quad = float(np.real(np.vdot(b, np.linalg.solve(A, b))))
    return float(n * np.log(beta) - np.sum(np.log(gamma)) - logdet_a - beta * float(np.vdot(Y, Y).real) + beta * beta * quad)


def standard_sbl_ll(B, Y, beta, gamma):
    """Standard SBL marginal log-likelihood without the constant:  -log det C - Y^H C^-1 Y,   C = I/beta + B diag(gamma) B^H  (N x N, direct)."""
    B = np.asarray(B, dtype=np.complex128)
    Y = np.asarray(Y, dtype=np.complex128)
    n = len(Y)
    C = np.eye(n) / beta + (B * np.asarray(gamma, dtype=float)[None, :]) @ B.conj().T
    C = (C + C.conj().T) / 2
    sign, logdet_c = np.linalg.slogdet(C)
    assert abs(sign - 1) < 1e-9
    return float(-logdet_c - np.real(np.vdot(Y, np.linalg.solve(C, Y))))


# ----------------------------------------------------------------------------- traced EM-SBL (arithmetic of sbl_rx.sbl_em, verbatim)
def _estep_ld(A, by, beta):
    """``sbl_rx._estep`` plus log det A = 2 sum log diag(L) from the Cholesky factor already computed (same operations, same order)."""
    L, jit = sbl._factor(A)
    Linv, info = lapack.ztrtri(np.asfortranarray(L), lower=1)
    if info != 0:
        raise np.linalg.LinAlgError('ztrtri failed')
    mu = beta * (Linv.conj().T @ (Linv @ by))
    return mu, np.sum(np.abs(Linv) ** 2, axis=0), jit, 2.0 * float(np.sum(np.log(np.real(np.diagonal(L)))))


def sbl_em_traced(B, Y, beta0, Gamma=None, gamma0=sbl.GAMMA0, max_iter=sbl.MAX_ITER, tol=sbl.TOL, prune=sbl.PRUNE):
    """Identical to ``sbl_rx.sbl_em`` in every arithmetic operation (outputs bit-identical, tested), and in addition evaluates the EIV bound L(beta, gamma)
    at the parameters used by every E-step plus once more at the final parameters: ``trace`` has iterations + 1 points; ``skip`` lists the transition
    indices (trace[i] -> trace[i+1]) in which atoms were pruned (the model changes there; excluded from the violation count)."""
    B = np.asarray(B, dtype=np.complex128)
    Y = np.asarray(Y, dtype=np.complex128)
    n, m = B.shape
    if Gamma is None:
        Gam = np.zeros((m, m), dtype=np.complex128)
    elif np.isscalar(Gamma):
        Gam = float(Gamma) * np.eye(m, dtype=np.complex128)
    else:
        Gam = np.asarray(Gamma, dtype=np.complex128)
        Gam = (Gam + Gam.conj().T) / 2
    G = B.conj().T @ B
    G = (G + G.conj().T) / 2
    Gt = G + Gam                       # expected Gram B^H B + Gamma
    by = B.conj().T @ Y
    ynorm2 = float(np.vdot(Y, Y).real)
    idx = np.arange(m)
    Ba, Gta, Gama, bya = B, Gt, Gam, by
    gam = np.full(m, float(gamma0))
    beta = float(beta0)
    sizes, jitter_events, converged = [m], 0, False
    iterations = 0
    trace, skip = [], []
    for it in range(1, max_iter + 1):
        iterations = it
        a = Ba.shape[1]
        A = beta * Gta
        A.reshape(-1)[::a + 1] += 1.0 / gam
        mu, sdiag, jit, logdet_a = _estep_ld(A, bya, beta)
        jitter_events += jit
        trace.append(n * np.log(beta) - float(np.sum(np.log(gam))) - logdet_a - beta * ynorm2 + beta * float(np.real(np.vdot(bya, mu))))
        r = Y - Ba @ mu
        resid = float(np.vdot(r, r).real)
        quad = float(np.vdot(mu, Gama @ mu).real)
        trace_term = float((a - np.sum(sdiag / gam)) / beta)
        beta_new = n / (resid + quad + trace_term)
        gam_new = np.abs(mu) ** 2 + sdiag
        rel = float(np.linalg.norm(gam_new - gam) / np.linalg.norm(gam))
        gam, beta = gam_new, beta_new
        keep = gam >= prune * gam.max()
        if not keep.all():
            sel = np.flatnonzero(keep)
            idx, gam = idx[sel], gam[sel]
            Ba, bya = Ba[:, sel], bya[sel]
            Gta, Gama = Gta[np.ix_(sel, sel)], Gama[np.ix_(sel, sel)]
            skip.append(it - 1)
        sizes.append(len(idx))
        if rel < tol:
            converged = True
            break
    a = Ba.shape[1]
    A = beta * Gta
    A.reshape(-1)[::a + 1] += 1.0 / gam
    factor, jit = sbl._factor(A)
    jitter_events += jit
    mu = beta * sla.cho_solve((factor, True), bya, check_finite=False)
    logdet_a = 2.0 * float(np.sum(np.log(np.real(np.diagonal(factor)))))
    trace.append(n * np.log(beta) - float(np.sum(np.log(gam))) - logdet_a - beta * ynorm2 + beta * float(np.real(np.vdot(bya, mu))))
    return dict(idx=idx, mu=mu, gamma=gam, beta=float(beta), iterations=int(iterations), converged=bool(converged), n_start=int(m),
                n_final=int(a), sizes=sizes, jitter_events=int(jitter_events), trace=[float(x) for x in trace], skip=skip)


def eiv_summary(trace, skip=(), tol=VIOLATION_TOL):
    """Monotonicity readout: a transition violates when L_{t+1} < L_t - tol * max(1, |L_t|); transitions across an atom-pruning event are excluded
    (and counted in ``n_prune_events``).  ``max_rel_drop`` = largest decrease / max(1, |L_t|) over the counted transitions (0 when none decreases)."""
    L = np.asarray(trace, dtype=float)
    d = np.diff(L)
    scale = np.maximum(1.0, np.abs(L[:-1]))
    counted = np.ones(len(d), dtype=bool)
    for i in skip:
        if 0 <= i < len(d):
            counted[i] = False
    rel = -d / scale
    viol = (rel > tol) & counted
    return dict(n_points=int(len(L)), n_viol=int(viol.sum()), max_rel_drop=float(max(0.0, rel[counted].max())) if counted.any() else 0.0,
                L_first=float(L[0]), L_last=float(L[-1]), n_prune_events=int(len(skip)), monotone=bool(not viol.any()))
