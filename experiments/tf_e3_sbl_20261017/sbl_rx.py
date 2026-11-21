"""E-3: Luo-style two-stage data-aided EM-SBL on the fine delay-Doppler grid (design.md sections 2-3).  numpy/scipy only.

Conventions are those of the CSTATE reopening kernel, imported read-only from the frozen ``tf_geometry_reopen_20260922/geometry_reopen.py``:
atom response  B = _responses(xt, atoms, c1, c2)   with  xt = daft(pilot + mu_d, c1, c2, inverse=True),
observation    Y = daft(y, c1, c2, inverse=True),
data covariance of the dictionary  Gamma = _gamma_cross(atoms, atoms, vf, c1),  vf = fft(v)  (tr(U_i^H U_j diag v)).
Frozen hyper-parameters (design section 2): M = 256 screening candidates, <= 100 EM iterations, stop at ||dgamma||/||gamma|| < 1e-4,
prune gamma_k < 1e-6 max gamma, output = atoms with |mu_k|^2 >= 1e-3 sum|mu|^2 (at most 24, co-delay atoms allowed).
"""
from __future__ import annotations

import numpy as np
import scipy.linalg as sla
from scipy.linalg import lapack

import e3_lib

e3_lib.prepare_paths()
from geometry_reopen import Path, _gamma_cross, _responses  # noqa: E402  (frozen, read-only)

N_SCREEN = 256
MAX_ITER = 100
TOL = 1e-4
PRUNE = 1e-6
KEEP_FRAC = 1e-3
MAX_ATOMS = 24
GRID_STEP = .25
DOPPLER = (-3., 3.)
GAMMA0 = 1.0   # flat initial prior variance (design leaves it open; frozen here)
CHUNK = 64
HYPER = dict(n_screen=N_SCREEN, max_iter=MAX_ITER, tol=TOL, prune=PRUNE, keep_frac=KEEP_FRAC, max_atoms=MAX_ATOMS, grid_step=GRID_STEP,
             doppler=DOPPLER, gamma0=GAMMA0)


# ----------------------------------------------------------------------------- grid, columns, screening
def full_grid(l_max_cap):
    """All atoms: delays 0..l_max_cap x Doppler -3..3 step .25 (K = 103 * 25 = 2575 for l_max_cap = 102); same order as the CSTATE bank."""
    count = int(np.floor((DOPPLER[1] - DOPPLER[0]) / GRID_STEP + 1e-9))
    nus = DOPPLER[0] + GRID_STEP * np.arange(count + 1)
    if nus[-1] < DOPPLER[1] - 1e-12:
        nus = np.append(nus, DOPPLER[1])
    return np.repeat(np.arange(l_max_cap + 1, dtype=np.int32), len(nus)), np.tile(nus, l_max_cap + 1)


def columns(xt, delays, dopplers, c1, c2, chunk=CHUNK):
    """Dictionary columns B(xt) for the given atoms (frozen ``_responses``, chunked), shape (n, len(delays))."""
    xt = np.asarray(xt, dtype=np.complex128)
    out = np.empty((len(xt), len(delays)), dtype=np.complex128)
    for first in range(0, len(delays), chunk):
        last = min(first + chunk, len(delays))
        group = [Path(int(l), float(nu)) for l, nu in zip(delays[first:last], dopplers[first:last])]
        out[:, first:last] = _responses(xt, group, c1, c2)
    return out


def screen(B, Y, m=N_SCREEN):
    """Indices (ascending) of the m atoms with the largest |B^H Y| (ties broken by index)."""
    corr = np.abs(B.conj().T @ np.asarray(Y, dtype=np.complex128))
    top = np.argsort(-corr, kind='stable')[:m]
    return np.sort(top)


def candidate_union(top, kept_delays, delays_grid):
    """Stage-2 candidate set: the screened atoms plus every Doppler atom of each delay retained by stage 1 (ascending, unique)."""
    extra = np.flatnonzero(np.isin(delays_grid, np.asarray(list(kept_delays), dtype=np.int64)))
    return np.union1d(np.asarray(top, dtype=np.int64), extra)


def gamma_full(delays, dopplers, v, c1):
    """Projected data covariance of the candidate atoms: frozen ``_gamma_cross(C, C, fft(v), c1)``."""
    atoms = [Path(int(l), float(nu)) for l, nu in zip(delays, dopplers)]
    return _gamma_cross(atoms, atoms, np.fft.fft(np.asarray(v, dtype=float)), c1)


# ----------------------------------------------------------------------------- EM-SBL core
def _factor(a):
    """Lower Cholesky factor of the Hermitian positive-definite ``a`` (LAPACK zpotrf); one fixed jitter retry (counted) if it is numerically singular."""
    try:
        return sla.cholesky(a, lower=True, check_finite=False), 0
    except np.linalg.LinAlgError:
        jitter = 1e-12 * float(np.real(np.trace(a))) / len(a)
        return sla.cholesky(a + jitter * np.eye(len(a)), lower=True, check_finite=False), 1


def _estep(A, by, beta):
    """E-step quantities from A = beta (B^H B + Gamma) + diag(1/gamma):  mu = beta A^-1 by  and  diag(A^-1), via the Cholesky factor L and
    L^-1 (LAPACK ztrtri; A^-1 = L^-H L^-1, so diag(A^-1)_k = sum_j |L^-1_jk|^2).  Exact algebra -- only the full inverse is avoided."""
    L, jit = _factor(A)
    Linv, info = lapack.ztrtri(np.asfortranarray(L), lower=1)
    if info != 0:
        raise np.linalg.LinAlgError('ztrtri failed')
    mu = beta * (Linv.conj().T @ (Linv @ by))
    return mu, np.sum(np.abs(Linv) ** 2, axis=0), jit


def sbl_em(B, Y, beta0, Gamma=None, gamma0=GAMMA0, max_iter=MAX_ITER, tol=TOL, prune=PRUNE):
    """EM-SBL with the errors-in-variables expected Gram (design section 2).

    B (N, m) complex dictionary (B-bar), Y (N,), Gamma None | float s (Gamma = s I) | (m, m) Hermitian data covariance, beta0 initial noise precision.
      E-step  Sigma = (beta (B^H B + Gamma) + diag(1/gamma))^-1,   mu = beta Sigma B^H Y
      M-step  gamma_k = |mu_k|^2 + Sigma_kk,
              1/beta = (||Y - B mu||^2 + mu^H Gamma mu + tr((B^H B + Gamma) Sigma)) / N
    tr((B^H B + Gamma) Sigma) is evaluated as (a - sum_k Sigma_kk / gamma_k) / beta, an exact identity from A Sigma = I (a = active atoms).
    Atoms with gamma_k < prune * max gamma are removed after every M-step.  Returns the posterior mean of the final active set from one last
    E-step (columns ``idx`` of B)."""
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
    idx = np.arange(m)
    Ba, Gta, Gama, bya = B, Gt, Gam, by
    gam = np.full(m, float(gamma0))
    beta = float(beta0)
    sizes, jitter_events, converged = [m], 0, False
    iterations = 0
    for it in range(1, max_iter + 1):
        iterations = it
        a = Ba.shape[1]
        A = beta * Gta                      # exactly Hermitian (Gta symmetrised once), so no re-symmetrisation is needed
        A.reshape(-1)[::a + 1] += 1.0 / gam
        mu, sdiag, jit = _estep(A, bya, beta)
        jitter_events += jit
        r = Y - Ba @ mu
        resid = float(np.vdot(r, r).real)
        quad = float(np.vdot(mu, Gama @ mu).real)
        trace = float((a - np.sum(sdiag / gam)) / beta)
        beta_new = n / (resid + quad + trace)
        gam_new = np.abs(mu) ** 2 + sdiag
        rel = float(np.linalg.norm(gam_new - gam) / np.linalg.norm(gam))
        gam, beta = gam_new, beta_new
        keep = gam >= prune * gam.max()
        if not keep.all():
            sel = np.flatnonzero(keep)
            idx, gam = idx[sel], gam[sel]
            Ba, bya = Ba[:, sel], bya[sel]
            Gta, Gama = Gta[np.ix_(sel, sel)], Gama[np.ix_(sel, sel)]
        sizes.append(len(idx))
        if rel < tol:
            converged = True
            break
    a = Ba.shape[1]
    A = beta * Gta
    A.reshape(-1)[::a + 1] += 1.0 / gam
    factor, jit = _factor(A)
    jitter_events += jit
    mu = beta * sla.cho_solve((factor, True), bya, check_finite=False)
    return dict(idx=idx, mu=mu, gamma=gam, beta=float(beta), iterations=int(iterations), converged=bool(converged), n_start=int(m),
                n_final=int(a), sizes=sizes, jitter_events=int(jitter_events))


def select_output(idx, mu, keep_frac=KEEP_FRAC, max_atoms=MAX_ATOMS):
    """Output atoms: |mu_k|^2 >= keep_frac * sum |mu|^2, at most ``max_atoms`` largest, at least one (energy order, stable)."""
    e = np.abs(mu) ** 2
    order = np.argsort(-e, kind='stable')
    sel = [int(k) for k in order if e[k] > 0 and e[k] >= keep_frac * e.sum()][:max_atoms]
    if not sel:
        sel = [int(order[0])]
    return np.asarray(idx)[sel], np.asarray(mu)[sel], e[sel]


# ----------------------------------------------------------------------------- co-delay census
def abs_dn(x, n):
    """|D_N(x)| = |sin(pi x) / (N sin(pi x / N))| with the x -> 0 limit equal to 1 (same as E-2 codelay_guard.abs_dn)."""
    x = np.abs(np.asarray(x, dtype=float))
    out = np.ones_like(x)
    nz = x != 0
    out[nz] = np.abs(np.sin(np.pi * x[nz]) / (n * np.sin(np.pi * x[nz] / n)))
    return out


def codelay_pairs(delays, dopplers, n, true_delays=None):
    """Same-delay pairs among the output atoms: list of dict(delay, dnu, dn, true_delay)."""
    truth = None if true_delays is None else set(int(d) for d in true_delays)
    out = []
    for i in range(len(delays)):
        for j in range(i + 1, len(delays)):
            if int(delays[i]) == int(delays[j]):
                dnu = abs(float(dopplers[i]) - float(dopplers[j]))
                out.append(dict(delay=int(delays[i]), dnu=dnu, dn=float(abs_dn(np.array([dnu]), n)[0]),
                                true_delay=None if truth is None else bool(int(delays[i]) in truth)))
    return out


def hard_decision(mu_d, pd):
    """Mod[Demod(mu_d)]: nearest point of the QPSK alphabet sqrt(pd/2)(+-1 +-1j); zero components decide +."""
    a = np.sqrt(pd / 2.0)
    re = np.where(np.real(mu_d) >= 0, 1.0, -1.0)
    im = np.where(np.imag(mu_d) >= 0, 1.0, -1.0)
    return a * (re + 1j * im)
