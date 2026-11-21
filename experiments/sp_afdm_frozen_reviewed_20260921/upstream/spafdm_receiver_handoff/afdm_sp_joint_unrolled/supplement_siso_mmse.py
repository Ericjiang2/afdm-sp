"""Exact-solve SISO Gaussian MMSE reference for observed, cancelled symbols.

This is the Gaussian reference behind Li and Yu's DI-S-MMSE, not a port of
their GMRES/FSPAI approximations or their OTFS/convolutional-code simulation.
Derivation and the MIT author-source snapshot live in trans-next research.
"""
import numpy as np
from scipy.linalg import cho_factor, cho_solve


def siso_mmse_torch(y, H, sigma2, constellation, code_prior=None):
    """CPU inference bridge; preserve the exact solver's message conventions."""
    import torch
    values = (y, H, sigma2, constellation)
    if any(v.device.type != 'cpu' for v in values):
        raise ValueError('exact SISO reference requires explicit CPU inputs')
    if torch.is_grad_enabled() and any(v.requires_grad for v in values):
        raise ValueError('exact SISO reference is inference only')
    c = constellation.detach().numpy()
    if c.shape != (4,):
        raise ValueError('SISO requires four constellation points')
    amp = float(abs(c[0].real))
    if amp <= 0 or not np.allclose(
            c, amp*np.array([1+1j, 1-1j, -1+1j, -1-1j]), rtol=1e-7, atol=0):
        raise ValueError('SISO requires ordered square QPSK')
    if code_prior is not None and code_prior.device.type != 'cpu':
        raise ValueError('SISO prior must be on CPU')
    prior = np.zeros(2*len(y)) if code_prior is None else code_prior.detach().numpy().copy()
    result = siso_mmse(y.detach().numpy(), H.detach().numpy(),
                      float(sigma2.detach()), prior, amplitude=amp)
    payload = {k: torch.from_numpy(result[k].copy()) for k in
               ('channel_llr', 'posterior_mean', 'posterior_variance')}
    payload['prior_llr'] = torch.from_numpy(prior.copy())
    return payload, dict(result, consumed_prior=prior)


def siso_mmse(y, H, sigma2, code_prior, *, amplitude=.5):
    """Return own-symbol-excluded likelihood and discrete QPSK posterior.

    Prior is positive log(P0/P1), I-then-Q. H and y must already have the
    caller's channel estimate and pilot cancellation; no truth is accepted
    separately. Gaussian interference moments are obtained from code prior
    only, never from a posterior that already includes the same observation.
    """
    y, H, prior = np.asarray(y), np.asarray(H), np.asarray(code_prior)
    if (y.ndim != 1 or not y.size or H.shape != (len(y), len(y))
            or prior.shape != (2*len(y),) or np.iscomplexobj(prior)
            or any(not np.isfinite(v).all() for v in (y, H, prior))
            or isinstance(sigma2, (bool, np.bool_)) or not np.isscalar(sigma2)
            or np.iscomplexobj(sigma2) or not np.isfinite(sigma2) or sigma2 <= 0
            or isinstance(amplitude, (bool, np.bool_)) or not np.isscalar(amplitude)
            or np.iscomplexobj(amplitude) or not np.isfinite(amplitude) or amplitude <= 0):
        raise ValueError('finite square channel, I/Q real prior, positive variance/amplitude required')
    y, H, prior = y.astype(np.complex128), H.astype(np.complex128), prior.astype(np.float64)
    n = len(y)
    mean = amplitude*(np.tanh(prior[:n]/2)+1j*np.tanh(prior[n:]/2))
    variance = np.maximum(2*amplitude**2-np.abs(mean)**2, 0.)
    covariance = (H*variance[None, :])@H.conj().T+float(sigma2)*np.eye(n)
    residual = y-H@mean
    rhs = np.column_stack((residual, H))
    solved = cho_solve(cho_factor(covariance, lower=True, check_finite=True), rhs, check_finite=True)
    relative_residual = float(np.linalg.norm(covariance@solved-rhs)/max(np.linalg.norm(rhs), np.finfo(float).tiny))
    if not np.isfinite(solved).all() or not np.isfinite(relative_residual) or relative_residual > 1e-9:
        raise FloatingPointError('SISO MMSE linear solve fails relative residual bound')
    xi = np.sum(H.conj()*solved[:, 1:], axis=0)
    if np.any(np.abs(xi.imag) > 1e-10*np.maximum(1., np.abs(xi.real))) or np.any(xi.real < 0):
        raise FloatingPointError('SISO MMSE leverage is not nonnegative real')
    xi = xi.real
    denominator = 1-variance*xi
    if np.any(denominator <= 0) or not np.isfinite(denominator).all():
        raise FloatingPointError('SISO MMSE extrinsic denominator lost positivity')
    natural = (H.conj().T@solved[:, 0]+xi*mean)/denominator
    precision = xi/denominator
    channel = 4*amplitude*np.concatenate((natural.real, natural.imag))
    if not np.isfinite(channel).all() or not np.isfinite(precision).all():
        raise FloatingPointError('SISO MMSE likelihood is nonfinite')
    posterior_llr = channel+prior
    posterior_mean = amplitude*(np.tanh(posterior_llr[:n]/2)+1j*np.tanh(posterior_llr[n:]/2))
    posterior_variance = np.maximum(2*amplitude**2-np.abs(posterior_mean)**2, 0.)
    hard = amplitude*(np.where(posterior_llr[:n] >= 0, 1., -1.)+1j*np.where(posterior_llr[n:] >= 0, 1., -1.))
    return dict(channel_llr=channel, posterior_llr=posterior_llr,
        posterior_mean=posterior_mean, posterior_variance=posterior_variance, hard=hard,
        prior_mean=mean, prior_variance=variance, extrinsic_natural=natural,
        extrinsic_precision=precision, leverage=xi, extrinsic_denominator=denominator,
        linear_relative_residual=relative_residual,
        algorithm='exact dense SISO Gaussian MMSE; not DI-S-MMSE approximation',
        linear_solves=1, linear_rhs=n+1, factorization_dimension=n)
