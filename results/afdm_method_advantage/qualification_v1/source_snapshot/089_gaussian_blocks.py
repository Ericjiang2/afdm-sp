"""Exact affine Gaussian reference; not an approximation to the bilinear model.

Support factors permit deterministic directions without artificial jitter.
Dense solves are deliberately exposed: low path rank does not remove data cost.
"""
import numpy as np


def affine_joint(B, H, y, mean_h, mean_d, factor_h, factor_d, noise):
    """Posterior of y=B h+H d+w with independent Gaussian support factors."""
    if not np.isfinite(noise) or noise <= 0:
        raise ValueError("positive finite complex noise variance required")
    B, H, y, mh, md, Fh, Fd = map(np.asarray,
        (B, H, y, mean_h, mean_d, factor_h, factor_d))
    if B.ndim != 2 or H.ndim != 2 or Fh.ndim != 2 or Fd.ndim != 2:
        raise ValueError("operators and support factors must be matrices")
    n, p = B.shape
    k = H.shape[1]
    if H.shape[0] != n or y.shape != (n,) or mh.shape != (p,) or md.shape != (k,) or Fh.shape[0] != p or Fd.shape[0] != k:
        raise ValueError("incompatible dimensions")
    if not all(np.isfinite(a).all() for a in (B,H,y,mh,md,Fh,Fd)):
        raise ValueError("nonfinite model")
    T, V = B@Fh, H@Fd
    r = y-B@mh-H@md
    A = np.eye(Fh.shape[1])+T.conj().T@T/noise
    E = T.conj().T@V/noise
    D = np.eye(Fd.shape[1])+V.conj().T@V/noise
    ai = np.linalg.solve(A, np.eye(len(A)))
    S = D-E.conj().T@ai@E
    cdd = np.linalg.solve(S, np.eye(len(S)))
    chd = -ai@E@cdd
    correction = ai@E@cdd@E.conj().T@ai
    chh = ai+correction
    eta_h, eta_d = T.conj().T@r/noise, V.conj().T@r/noise
    zd = cdd@(eta_d-E.conj().T@ai@eta_h)
    zh = ai@(eta_h-E@zd)
    return dict(h_mean=mh+Fh@zh, d_mean=md+Fd@zd,
        h_cov=Fh@chh@Fh.conj().T, d_cov=Fd@cdd@Fd.conj().T,
        hd_cov=Fh@chd@Fd.conj().T,
        h_conditional_cov=Fh@ai@Fh.conj().T,
        h_marginal_correction=Fh@correction@Fh.conj().T,
        effective_precision=(np.eye(n)-T@ai@T.conj().T/noise)/noise,
        support_h=Fh.shape[1], support_d=Fd.shape[1])


def cavity(marginal_mean, marginal_cov, site_precision, site_information):
    """Divide represented Gaussian marginal by its stored site (real or complex)."""
    precision = np.linalg.solve(marginal_cov, np.eye(len(marginal_mean)))
    lam = precision-site_precision
    eta = precision@marginal_mean-site_information
    np.linalg.cholesky(lam)
    return lam, eta


def real_covariance(cov, pseudo):
    """Covariance of grouped [Re(z), Im(z)], retaining impropriety."""
    return .5*np.block([[(cov+pseudo).real, -(cov-pseudo).imag],
                       [(cov+pseudo).imag, (cov-pseudo).real]])
