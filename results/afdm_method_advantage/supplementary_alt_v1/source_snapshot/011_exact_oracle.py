"""Exact finite-data / proper-Gaussian-gain posterior for small fixed geometry.

All priors must be independent of the current observation. No receiver calls,
soft-message reinterpretation, covariance jitter, or approximate pruning.
"""
from dataclasses import dataclass

import numpy as np
from scipy.special import logsumexp


@dataclass(frozen=True)
class ExactPosterior:
    probabilities: np.ndarray
    log_probabilities: np.ndarray
    log_likelihood: np.ndarray
    log_evidence: float
    llr: np.ndarray | None
    h_mean: np.ndarray
    h_cov: np.ndarray
    d_mean: np.ndarray
    d_cov: np.ndarray
    h_d_cov: np.ndarray
    h_pseudo_cov: np.ndarray
    d_pseudo_cov: np.ndarray
    h_d_pseudo_cov: np.ndarray
    component_h_mean: np.ndarray
    component_h_cov: np.ndarray
    prior_support_rank: int
    prior_roundoff_correction: float
    enumeration_size: int


def _array(value, name, ndim, dtype=complex):
    raw = np.asarray(value)
    if dtype is float and np.iscomplexobj(raw) and np.any(raw.imag != 0):
        raise ValueError(f'{name} must be real')
    if dtype is float and np.iscomplexobj(raw):
        value = raw.real
    array = np.asarray(value, dtype=dtype)
    if array.ndim != ndim or not np.isfinite(array).all():
        raise ValueError(f'{name} must be finite with {ndim} dimensions')
    return array


def _binary(value, name, columns):
    array = _array(value, name, 2, dtype=float)
    if array.shape[1] != columns or not np.isin(array, [0, 1]).all():
        raise ValueError(f'{name} must be a binary matrix with {columns} columns')
    return array.astype(np.int64)


def enumerate_qpsk(n, *, parity_check=None, amplitude=.5, max_words=65536):
    """Return (words[K,N], bits[K,2N]), all-I then all-Q, bit 0 -> +a.

    Optional binary H enforces H b = 0 mod 2. The cap bounds the *unfiltered*
    enumeration; short-code constraints do not license an exponential surprise.
    """
    if (isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, np.integer))
            or n < 1 or n > 31 or not isinstance(max_words, (int, np.integer))
            or max_words < 1 or 4**n > max_words):
        raise ValueError('n and max_words must define a bounded positive enumeration')
    if not np.isscalar(amplitude) or np.iscomplexobj(amplitude) or not np.isfinite(amplitude) or amplitude <= 0:
        raise ValueError('amplitude must be finite and positive')
    labels = np.arange(4**n, dtype=np.uint64)
    shifts = np.arange(2*n-1, -1, -1, dtype=np.uint64)
    bits = ((labels[:, None] >> shifts) & 1).astype(np.int64)
    if parity_check is not None:
        check = _binary(parity_check, 'parity_check', 2*n)
        bits = bits[np.all((bits @ check.T) % 2 == 0, axis=1)]
    words = amplitude * ((1 - 2*bits[:, :n]) + 1j*(1 - 2*bits[:, n:]))
    return words, bits


def _prior_factor(covariance):
    """PSD support, keeping every positive eigenvalue (no rank cutoff/jitter)."""
    scale = float(np.linalg.norm(covariance, ord=2))
    tolerance = 64 * np.finfo(float).eps * covariance.shape[0] * scale
    if np.linalg.norm(covariance - covariance.conj().T, ord=2) > tolerance:
        raise ValueError('gain_cov must be Hermitian')
    hermitian = (covariance + covariance.conj().T) / 2
    values, vectors = np.linalg.eigh(hermitian)
    if values.min() < -tolerance:
        raise ValueError('gain_cov must be positive semidefinite')
    positive = values > 0
    factor = vectors[:, positive] * np.sqrt(values[positive])
    correction = float(np.linalg.norm(factor @ factor.conj().T - covariance))
    return factor, correction


def _chol_solve(cholesky, rhs):
    return np.linalg.solve(cholesky.conj().T, np.linalg.solve(cholesky, rhs))


def exact_posterior(y, operators, pilot, candidates, gain_mean, gain_cov,
                    noise_variance, *, bits=None, prior_probabilities=None):
    """Integrate h for each legal d and normalize the finite posterior.

    Model y=sum_p h_p U_p(pilot+d)+w, w~CN(0,noise_variance I),
    h~CN(gain_mean,gain_cov), independent d~prior_probabilities. operators
    has shape [P,M,N], allowing rectangular observations. candidates are unique
    legal words [K,N]. Caller owns code completeness and prior provenance.
    llr=log P(bit=0|y)-log P(bit=1|y); impossible bits yield exact infinities.
    h_d_cov=E[(h-Eh)(d-Ed)^H]; *_pseudo_cov uses transpose instead.
    component_h_* retain all candidates in input order, including zero-prior ones.
    """
    y = _array(y, 'y', 1)
    ops = _array(operators, 'operators', 3)
    pilot = _array(pilot, 'pilot', 1)
    words = _array(candidates, 'candidates', 2)
    mean = _array(gain_mean, 'gain_mean', 1)
    covariance = _array(gain_cov, 'gain_cov', 2)
    p, m, n = ops.shape
    k = len(words)
    if min(p, m, n, k) < 1 or y.shape != (m,) or pilot.shape != (n,) or words.shape[1] != n:
        raise ValueError('observation/operator/pilot/candidate dimensions disagree')
    if mean.shape != (p,) or covariance.shape != (p, p):
        raise ValueError('gain prior dimensions disagree')
    if np.unique(words, axis=0).shape[0] != k:
        raise ValueError('candidates must be unique legal data words')
    if (not np.isscalar(noise_variance) or np.iscomplexobj(noise_variance)
            or not np.isfinite(noise_variance) or noise_variance <= 0):
        raise ValueError('noise_variance must be finite and strictly positive')
    sigma2 = float(np.real(noise_variance))
    labels = None
    if bits is not None:
        raw = _array(bits, 'bits', 2, dtype=float)
        labels = _binary(raw, 'bits', raw.shape[1])
        if labels.shape[0] != k or labels.shape[1] == 0:
            raise ValueError('bits must have one nonempty label per candidate')
    if prior_probabilities is None:
        prior = np.full(k, 1/k)
    else:
        prior = _array(prior_probabilities, 'prior_probabilities', 1, dtype=float)
        if (prior.shape != (k,) or np.any(prior < 0)
                or not np.isclose(prior.sum(), 1., rtol=1e-13, atol=1e-15)):
            raise ValueError('prior_probabilities must be nonnegative and sum to one')
        prior = prior / prior.sum()
    factor, correction = _prior_factor(covariance)
    rank = factor.shape[1]
    component_mean = np.empty((k, p), complex)
    component_cov = np.empty((k, p, p), complex)
    log_likelihood = np.empty(k)
    for index, word in enumerate(words):
        b = np.einsum('pij,j->ip', ops, pilot + word)
        t = b @ factor
        residual = y - b @ mean
        # Positive observation noise makes S invertible even for a point prior.
        s = sigma2 * np.eye(m) + t @ t.conj().T
        chol = np.linalg.cholesky(s)
        whitened = np.linalg.solve(chol, residual)
        logdet = 2 * np.log(chol.diagonal().real).sum()
        log_likelihood[index] = -m*np.log(np.pi) - logdet - np.vdot(whitened, whitened).real
        if rank == 0:
            component_mean[index] = mean
            component_cov[index] = 0
            continue
        precision = np.eye(rank) + t.conj().T @ t / sigma2
        latent_chol = np.linalg.cholesky(precision)
        latent_mean = _chol_solve(latent_chol, t.conj().T @ residual / sigma2)
        component_mean[index] = mean + factor @ latent_mean
        # A A^H form avoids subtracting nearly equal covariance matrices.
        posterior_factor = np.linalg.solve(latent_chol, factor.conj().T).conj().T
        component_cov[index] = posterior_factor @ posterior_factor.conj().T
    if not np.isfinite(log_likelihood).all():
        raise FloatingPointError('nonfinite likelihood; numeric dynamic range exceeded')
    log_prior = np.full(k, -np.inf)
    np.log(prior, out=log_prior, where=prior > 0)
    log_joint = log_prior + log_likelihood
    evidence = float(logsumexp(log_joint))
    log_prob = log_joint - evidence
    probability = np.exp(log_prob)
    h_mean = probability @ component_mean
    d_mean = probability @ words
    hdev = component_mean - h_mean
    ddev = words - d_mean
    h_cov = np.einsum('k,kij->ij', probability, component_cov)
    h_cov += np.einsum('k,ki,kj->ij', probability, hdev, hdev.conj())
    d_cov = np.einsum('k,ki,kj->ij', probability, ddev, ddev.conj())
    h_d_cov = np.einsum('k,ki,kj->ij', probability, hdev, ddev.conj())
    h_pseudo = np.einsum('k,ki,kj->ij', probability, hdev, hdev)
    d_pseudo = np.einsum('k,ki,kj->ij', probability, ddev, ddev)
    cross_pseudo = np.einsum('k,ki,kj->ij', probability, hdev, ddev)
    llr = None
    if labels is not None:
        llr = np.array([logsumexp(log_joint[labels[:, j] == 0])
                        - logsumexp(log_joint[labels[:, j] == 1])
                        for j in range(labels.shape[1])])
    return ExactPosterior(probability, log_prob, log_likelihood, evidence, llr,
                          h_mean, h_cov, d_mean, d_cov, h_d_cov,
                          h_pseudo, d_pseudo, cross_pseudo, component_mean,
                          component_cov, rank, correction, k)
