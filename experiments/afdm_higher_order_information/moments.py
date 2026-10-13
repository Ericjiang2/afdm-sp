"""Finite-input, proper-Gaussian-gain control model in physical time coordinates.

This is not the normalized production gain prior. All QPSK symbols have unit
power; the frozen enumerator's legacy default amplitude is deliberately overridden.
"""
from dataclasses import dataclass
from itertools import permutations

import numpy as np
from scipy.special import logsumexp

from experiments.sp_afdm_frozen_20260920.src.physical import Channel, daft
from experiments.afdm_shared_channel_20261004.conditional_solver import cpp_time_matrix
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk


def time_transform(n, c1, c2, delay=0):
    """Known common delay and CPP, using the frozen physical operator."""
    if (not isinstance(n, (int, np.integer)) or n < 3
            or not isinstance(delay, (int, np.integer)) or not 0 <= delay < n
            or not np.isfinite([c1, c2]).all()):
        raise ValueError('N >= 3, finite chirps and a legal common integer delay required')
    channel = Channel(n, c1, c2, [delay], [0.], [1.])
    return cpp_time_matrix(channel) @ daft(np.eye(n), c1, c2, True)


def finite_weights(bits, incoming=None, exclude=()):
    """Legal finite-support bit factors, with specified own factors excluded.

The caller supplies legal codewords if a code constraint is intended. Independent
bit factors do not replace that support. Incoming is external, not a same-y APP.
"""
    bits = np.asarray(bits)
    if bits.ndim != 2 or len(bits) == 0 or not np.isin(bits, [0, 1]).all():
        raise ValueError('nonempty legal binary support required')
    incoming = np.zeros(bits.shape[1]) if incoming is None else np.asarray(incoming, float)
    exclude = np.asarray(exclude)
    if (incoming.shape != (bits.shape[1],) or not np.isfinite(incoming).all()
            or (exclude.size and (not np.issubdtype(exclude.dtype, np.integer)
                or np.any(exclude < 0) or np.any(exclude >= bits.shape[1])
                or len(np.unique(exclude)) != len(exclude)))):
        raise ValueError('finite matching external factors and unique excluded bit indices required')
    keep = np.ones(bits.shape[1], bool)
    keep[exclude.astype(int)] = False
    logw = np.sum(-np.logaddexp(0., (2*bits[:, keep]-1)*incoming[keep]), axis=1)
    return np.exp(logw-logsumexp(logw))


def input_moments(time_words, weights):
    """Raw second moment, central pseudo covariance and cross-power fourth moment."""
    x = np.asarray(time_words, complex)
    w = np.asarray(weights, float)
    if (x.ndim != 2 or w.shape != (len(x),) or np.any(w < 0)
            or not np.isfinite(x).all() or not np.isfinite(w).all()
            or not np.isclose(w.sum(), 1., rtol=0, atol=2e-13)):
        raise ValueError('finite words and nonnegative normalized weights required')
    mean = w @ x
    centered = x-mean
    second = np.einsum('k,kn,km->nm', w, x, x.conj())
    pseudo = np.einsum('k,kn,km->nm', w, centered, centered)
    powers = abs(x)**2
    fourth = np.einsum('k,kn,km->nm', w, powers, powers)
    return dict(mean=mean, second=second, pseudo=pseudo, fourth=fourth)


def control_T_mean(n, a, b, q, power):
    """Exact only for independent uniform unit-power QPSK and equal-modulus DAFT."""
    if (n < 3 or a == b or not 0 < a < n or not 0 < b < n
            or not np.isfinite([q, power]).all() or q < 0 or power <= 0):
        raise ValueError('distinct nonzero lags, q >= 0 and positive total power required')
    ta, tb = 2*np.pi*np.array([a, b])/n
    return (1-1/n)*power**2*(np.cos(np.sqrt(q)*ta)**2-np.cos(np.sqrt(q)*tb)**2)


def cross_power_from_inputs(second, fourth, q, power, noise):
    """General-input off-diagonal E[|r_n|²|r_m|²], Gaussian gain control only."""
    second, fourth = np.asarray(second), np.asarray(fourth)
    n = len(second)
    if (second.shape != (n, n) or fourth.shape != (n, n)
            or not np.isfinite(second).all() or not np.isfinite(fourth).all()
            or not np.isfinite([q, power, noise]).all() or min(power, noise) <= 0 or q < 0):
        raise ValueError('matching finite input moments and valid control parameters required')
    omega = 2*np.pi*(np.arange(n)[:, None]-np.arange(n)[None, :])/n
    diagonal = np.diag(second).real
    result = power**2*(1+np.cos(np.sqrt(q)*omega)**2)*fourth
    result += power*noise*(diagonal[:, None]+diagonal[None, :])+noise**2
    # At n=m the two noise Wick contractions coincide and must both be included.
    np.fill_diagonal(result, 2*power**2*np.diag(fourth)+4*power*noise*diagonal+2*noise**2)
    return result


def gaussian_power_product(covariances, indices):
    """E product_j |r[indices[j]]|² via complex Wick permanent, k <= 4.

Repeated indices are intentional, e.g. [0,0,a,b] for T cross products.
"""
    covariance = np.asarray(covariances, complex)
    indices = np.asarray(indices)
    if (covariance.ndim not in (2, 3) or covariance.shape[-1] != covariance.shape[-2]
            or indices.ndim != 1 or not 1 <= len(indices) <= 4
            or not np.issubdtype(indices.dtype, np.integer)
            or np.any(indices < 0) or np.any(indices >= covariance.shape[-1])
            or not np.isfinite(covariance).all()):
        raise ValueError('finite square covariance and one to four legal integer indices required')
    answer = np.zeros(covariance.shape[:-2], complex)
    for order in permutations(range(len(indices))):
        answer += np.prod(covariance[..., indices, indices[list(order)]], axis=-1)
    if np.any(abs(answer.imag) > 2e-10*np.maximum(1., abs(answer.real))):
        raise FloatingPointError('Wick power moment must be real')
    return answer.real


def feature_values(y, lags):
    """Observed T_ab values; lags are fixed design, never selected from truth."""
    y = np.asarray(y, complex)
    lags = np.asarray(lags)
    if (y.ndim != 2 or not np.isfinite(y).all() or lags.ndim != 2 or lags.shape[1] != 2
            or not np.issubdtype(lags.dtype, np.integer) or np.any(lags <= 0)
            or np.any(lags >= y.shape[1]) or np.any(lags[:, 0] == lags[:, 1])):
        raise ValueError('finite observations and pairs of distinct nonzero integer lags required')
    p = abs(y)**2
    return p[:, :1]*(p[:, lags[:, 0]]-p[:, lags[:, 1]])


@dataclass
class FiniteControl:
    """Exact finite-input mixture after analytic proper Gaussian gain elimination."""
    time_words: np.ndarray
    weights: np.ndarray

    def __post_init__(self):
        self.time_words = np.asarray(self.time_words, complex)
        self.weights = np.asarray(self.weights, float)
        input_moments(self.time_words, self.weights)
        if self.time_words.shape[1] < 3 or np.any(self.weights <= 0):
            raise ValueError('N >= 3 and strictly positive weights on retained support required')
        self.n = self.time_words.shape[1]
        self.outer = self.time_words[:, :, None]*self.time_words[:, None, :].conj()
        self.omega = 2*np.pi*(np.arange(self.n)[:, None]-np.arange(self.n)[None, :])/self.n

    @classmethod
    def uniform(cls, n=4, c1=None, c2=None, delay=0):
        c1 = .37/n if c1 is None else c1
        c2 = .13/n**2 if c2 is None else c2
        words, _ = enumerate_qpsk(n, amplitude=1/np.sqrt(2))
        return cls(words @ time_transform(n, c1, c2, delay).T, np.full(len(words), 1/len(words)))

    def covariances(self, q, center, power, noise, derivatives=False):
        if (not np.isfinite([q, center, power, noise]).all()
                or q < 0 or power <= 0 or noise <= 0):
            raise ValueError('finite q >= 0, center, positive total power and noise required')
        phase = np.exp(1j*center*self.omega)
        base = self.outer*phase
        oscillation = np.cos(np.sqrt(q)*self.omega)
        signal = base*oscillation
        covariance = power*signal+noise*np.eye(self.n)
        if not derivatives:
            return covariance
        derivatives = np.stack((-.5*power*base*self.omega**2*np.sinc(np.sqrt(q)*self.omega/np.pi),
                                1j*power*self.omega*signal, signal,
                                np.broadcast_to(np.eye(self.n), covariance.shape)), axis=1)
        return covariance, derivatives

    def evaluate(self, y, q, center, power, noise, *, score=True, batch=128):
        y = np.asarray(y, complex)
        if (y.ndim != 2 or y.shape[1] != self.n or not np.isfinite(y).all()
                or not isinstance(batch, int) or batch <= 0):
            raise ValueError('finite matching observation rows and positive batch size required')
        cov, deriv = self.covariances(q, center, power, noise, True)
        chol = np.linalg.cholesky(cov)
        inverse = np.linalg.solve(cov, np.broadcast_to(np.eye(self.n), cov.shape))
        normal = -self.n*np.log(np.pi)-2*np.log(np.diagonal(chol, axis1=1, axis2=2).real).sum(axis=1)
        if score:
            quadratic = inverse[:, None] @ deriv @ inverse[:, None]
            traces = np.einsum('kij,kaji->ka', inverse, deriv).real
        log_density, scores = [], []
        for start in range(0, len(y), batch):
            obs = y[start:start+batch]
            conditional = normal[None, :]-np.einsum('bi,kij,bj->bk', obs.conj(), inverse, obs, optimize=True).real
            weighted = conditional+np.log(self.weights)
            logp = logsumexp(weighted, axis=1)
            log_density.append(logp)
            if score:
                component = np.einsum('bi,kaij,bj->bka', obs.conj(), quadratic, obs, optimize=True).real-traces
                scores.append(np.einsum('bk,bka->ba', np.exp(weighted-logp[:, None]), component))
        return np.concatenate(log_density), np.concatenate(scores) if score else None

    def exact_feature_moments(self, lags, q, center, power, noise):
        covariance = self.covariances(q, center, power, noise)
        means = []
        for a, b in lags:
            means.append(self.weights @ (gaussian_power_product(covariance, [0, a])-gaussian_power_product(covariance, [0, b])))
        second = np.empty((len(lags), len(lags)))
        for i, (a, b) in enumerate(lags):
            for j, (c, d) in enumerate(lags):
                raw = sum(sign*gaussian_power_product(covariance, [0, 0, x, z])
                          for x, sx in ((a, 1), (b, -1)) for z, sz in ((c, 1), (d, -1))
                          for sign in (sx*sz,))
                second[i, j] = self.weights @ raw
        mean = np.array(means)
        return mean, second-np.outer(mean, mean)


def information_projection(scores, rcond=1e-12):
    """Uncentered empirical E ss^T; L2 projection handles singular nuisance span."""
    scores = np.asarray(scores, float)
    if scores.ndim != 2 or scores.shape[1] != 4 or len(scores) < 4 or not np.isfinite(scores).all():
        raise ValueError('finite score rows ordered q, mu, tau, sigma2 required')
    nuisance = scores[:, 1:]
    coefficients, _, rank, singular = np.linalg.lstsq(nuisance, scores[:, 0], rcond=rcond)
    residual = scores[:, 0]-nuisance @ coefficients
    fisher = scores.T @ scores/len(scores)
    return dict(fisher=fisher, raw=float(fisher[0, 0]), effective=float(np.mean(residual**2)),
                coefficients=coefficients, rank=int(rank), singular_values=singular,
                orthogonality=nuisance.T @ residual/len(scores), residual=residual)
