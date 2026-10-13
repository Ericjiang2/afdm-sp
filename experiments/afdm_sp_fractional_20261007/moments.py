"""Exact quadratic moments for independent path-Doppler factors and AF variances.

This evaluates E[log likelihood] for a declared factor model. It is neither a
QPSK marginal likelihood nor an update under the normalized production prior.
All N-dimensional operators use the frozen physical DAFT/CPP convention.
"""
from dataclasses import dataclass

import numpy as np

from experiments.sp_afdm_frozen_20260920.src.physical import daft

ROUNDOFF = 1e-10


def require(condition, message):
    if not condition:
        raise ValueError(message)


def vector(value, size, name, *, real=False):
    original = np.asarray(value)
    require(original.shape == (size,), f'{name}: expected length {size}')
    require(not real or not np.iscomplexobj(original), f'{name}: real values required')
    out = np.asarray(original, dtype=float if real else complex).copy()
    require(np.isfinite(out).all(), f'{name}: finite values required')
    return out


def real_scalar(value, name, *, positive=False):
    value = np.asarray(value)
    require(value.shape == () and not np.iscomplexobj(value) and np.isfinite(value),
            f'{name}: finite real scalar required')
    out = float(value)
    require(not positive or out > 0, f'{name}: positive value required')
    return out


def real_result(value, name, *, nonnegative=False):
    value = np.asarray(value)
    scale = max(1., float(np.linalg.norm(value)))
    if not np.isfinite(value).all() or np.linalg.norm(value.imag) > ROUNDOFF*scale:
        raise FloatingPointError(f'{name}: nonfinite or nonreal result')
    if nonnegative and np.min(value.real) < -ROUNDOFF*scale:
        raise FloatingPointError(f'{name}: negative result exceeds roundoff')
    # Do not clip accepted roundoff or repair an invalid covariance.
    return value.real


@dataclass(frozen=True)
class SourceMoments:
    owner: object
    mean: np.ndarray
    variance: np.ndarray
    responses: np.ndarray
    variance_fft: np.ndarray
    energy: float


@dataclass(frozen=True)
class GainColumnMoments:
    """One point-Doppler column; fixed source/other phases are captured once."""
    owner: object
    source: SourceMoments
    coordinate: int
    others: np.ndarray
    kernels: np.ndarray
    matched_kernel: np.ndarray
    base_dopplers: np.ndarray

    def evaluate(self, doppler, *, derivative=False):
        doppler = real_scalar(doppler, 'candidate Doppler')
        require(type(derivative) is bool, 'derivative request must be boolean')
        self.owner._source(self.source)
        work = self.owner.work_counts

        def add(key, amount=1):
            work[key] = work.get(key, 0)+amount

        add('gain_candidate_columns_started')
        add('gain_candidate_phase_entries', self.owner.n)
        phase = np.exp(1j*self.owner.time*doppler)
        column = np.empty(self.owner.p, complex)
        column[self.coordinate] = self.source.energy
        add('gain_candidate_cross_terms', len(self.others)*self.owner.n)
        column[self.others] = self.kernels@phase
        add('gain_candidate_matched_terms', self.owner.n)
        matched = complex(self.matched_kernel@phase.conj())
        if not np.isfinite(column).all() or not np.isfinite(matched):
            raise FloatingPointError('nonfinite gain candidate column')
        result = dict(doppler=doppler, coordinate=self.coordinate, gram_column=column,
                      matched=matched, derivative=None)
        if derivative:
            add('gain_candidate_derivatives_started')
            phase_derivative = 1j*self.owner.time*phase
            column_derivative = np.zeros(self.owner.p, complex)
            add('gain_candidate_derivative_cross_terms', len(self.others)*self.owner.n)
            column_derivative[self.others] = self.kernels@phase_derivative
            add('gain_candidate_derivative_matched_terms', self.owner.n)
            matched_derivative = complex(self.matched_kernel@phase_derivative.conj())
            if not np.isfinite(column_derivative).all() or not np.isfinite(matched_derivative):
                raise FloatingPointError('nonfinite gain candidate derivative')
            result['derivative'] = dict(gram_column=column_derivative, matched=matched_derivative)
            add('gain_candidate_derivatives_completed')
        add('gain_candidate_columns_completed')
        return result


class PathMoments:
    """Matrix-free moments with independent positive finite Doppler factors.

    Finite nodes are exact diagnostic laws. This class makes no claim that
    they approximate an unspecified continuous prior or posterior accurately.
    """

    def __init__(self, n, c1, c2, delays, doppler_nodes, weights, gain_mean, gain_cov):
        require(type(n) is int and n >= 2, 'N must be an integer >=2')
        self.n, self.c1, self.c2 = n, real_scalar(c1, 'c1'), real_scalar(c2, 'c2')
        self.work_counts = dict(forward_daft_vectors=0, inverse_daft_vectors=0, ordinary_fft_vectors=0)
        delays = np.asarray(delays)
        require(delays.ndim == 1 and len(delays) > 0 and np.issubdtype(delays.dtype, np.integer),
                'integer path delays required')
        require(np.all((delays >= 0) & (delays < n)), 'delay outside [0,N)')
        self.delays = delays.copy()
        self.p = len(delays)
        nodes, weights = np.asarray(doppler_nodes), np.asarray(weights)
        require(nodes.ndim == 2 and nodes.shape[0] == self.p and nodes.shape[1] > 0 and
                weights.shape == nodes.shape, 'Doppler factor dimensions')
        require(not np.iscomplexobj(nodes) and not np.iscomplexobj(weights), 'real nodes and weights required')
        nodes, weights = nodes.astype(float), weights.astype(float)
        require(np.isfinite(nodes).all() and np.isfinite(weights).all() and np.all(weights > 0),
                'finite Doppler nodes and strictly positive weights required')
        require(np.allclose(weights.sum(axis=1), 1., atol=1e-12, rtol=0), 'weights must sum to one')
        self.nodes, self.weights = nodes, weights
        self.mean = vector(gain_mean, self.p, 'gain mean')
        covariance = np.asarray(gain_cov, complex).copy()
        require(covariance.shape == (self.p, self.p) and np.isfinite(covariance).all(), 'gain covariance dimensions/finite')
        tolerance = ROUNDOFF*max(1., float(np.linalg.norm(covariance)))
        require(np.linalg.norm(covariance-covariance.conj().T) <= tolerance, 'gain covariance must be Hermitian')
        require(np.linalg.eigvalsh((covariance+covariance.conj().T)/2).min() >= -tolerance,
                'gain covariance must be PSD')
        self.covariance = covariance
        self.second = covariance+np.outer(self.mean, self.mean.conj())
        k = np.arange(n)
        self.time = 2*np.pi*k/n
        wrap = k[None, :]-delays[:, None]
        self.indices = wrap % n
        self.cpp = np.where(wrap < 0, np.exp(2j*np.pi*self.c1*(n*n+2*n*wrap)), 1.)
        self.phi = np.sum(weights[:, :, None]*np.exp(1j*nodes[:, :, None]*self.time), axis=1)
        require(np.allclose(self.phi[:, 0], 1., atol=1e-12, rtol=0) and
                np.max(abs(self.phi)) <= 1+1e-12, 'invalid characteristic moments')
        for value in (self.delays, self.nodes, self.weights, self.mean, self.covariance,
                      self.second, self.time, self.indices, self.cpp, self.phi):
            value.setflags(write=False)

    def _daft(self, value, *, inverse=False):
        key = 'inverse_daft_vectors' if inverse else 'forward_daft_vectors'
        self.work_counts[key] += 1
        return daft(value, self.c1, self.c2, inverse=inverse)

    def _fft(self, value):
        self.work_counts['ordinary_fft_vectors'] += 1
        return np.fft.fft(value)

    def prepare_source(self, pilot, data_mean, data_variance):
        pilot = vector(pilot, self.n, 'AF pilot')
        mean = vector(data_mean, self.n, 'AF data mean')
        variance = vector(data_variance, self.n, 'AF data variance', real=True)
        require(np.all(variance >= 0), 'negative AF data variance')
        mean += pilot
        time_mean = self._daft(mean, inverse=True)
        responses = self.cpp*time_mean[self.indices]
        variance_fft = self._fft(variance)/self.n
        energy = float(np.vdot(mean, mean).real+variance.sum())
        for value in (mean, variance, responses, variance_fft):
            value.setflags(write=False)
        return SourceMoments(self, mean, variance, responses, variance_fft, energy)

    def _source(self, source):
        require(isinstance(source, SourceMoments) and source.owner is self, 'source belongs to another path model')

    def _cross_source(self, source, i, j):
        difference = int(self.delays[i]-self.delays[j])
        phase = np.exp(2j*np.pi*self.c1*(2*np.arange(self.n)*difference-
                                        self.delays[i]**2+self.delays[j]**2))
        return (source.responses[i]*source.responses[j].conj()+
                source.variance_fft[difference % self.n]*phase)

    def expected_quadratic(self, y, source):
        self._source(source)
        y = vector(y, self.n, 'AF observation fixture')
        time_y = self._daft(y, inverse=True)
        mean_response = np.sum(self.mean[:, None]*self.phi*source.responses, axis=0)
        value = np.vdot(time_y, time_y)-2*np.vdot(time_y, mean_response).real
        value += np.trace(self.second)*source.energy
        for i in range(self.p):
            for j in range(i+1, self.p):
                value += 2*np.real(self.second[i, j]*np.sum(
                    self.phi[i]*self.phi[j].conj()*self._cross_source(source, i, j)))
        return float(real_result(value, 'expected quadratic', nonnegative=True))

    def coordinate_coefficients(self, y, source):
        """Coefficients of Re sum_n a_i[n] exp(2 pi i n u/N)."""
        self._source(source)
        time_y = self._daft(vector(y, self.n, 'AF observation fixture'), inverse=True)
        coefficients = self.mean[:, None]*source.responses*time_y.conj()
        for i in range(self.p):
            for j in range(self.p):
                if i != j:
                    coefficients[i] -= self.second[i, j]*self._cross_source(source, i, j)*self.phi[j].conj()
        require(np.isfinite(coefficients).all(), 'nonfinite coordinate coefficients')
        return coefficients

    def gain_statistics(self, y, source):
        """Expected path-regressor Gram and matched vector; no gain update."""
        self._source(source)
        time_y = self._daft(vector(y, self.n, 'AF observation fixture'), inverse=True)
        gamma = np.empty((self.p, self.p), complex)
        for i in range(self.p):
            for j in range(self.p):
                gamma[i, j] = source.energy if i == j else np.sum(
                    self.phi[i].conj()*self.phi[j]*self._cross_source(source, j, i))
        matched = (self.phi*source.responses).conj()@time_y
        return gamma, matched

    def prepare_gain_column(self, y, source, coordinate):
        """Reuse canonical CPP cross moments, without mutating this path model."""
        self._source(source)
        require(self.nodes.shape == (self.p, 1) and np.all(self.weights == 1),
                'candidate gain columns require deterministic Dopplers')
        require(type(coordinate) is int and 0 <= coordinate < self.p, 'invalid gain coordinate')
        work = self.work_counts
        work['gain_column_preparations'] = work.get('gain_column_preparations', 0)+1
        time_y = self._daft(vector(y, self.n, 'AF observation'), inverse=True)
        others = np.asarray([j for j in range(self.p) if j != coordinate], dtype=int)
        kernels = np.empty((len(others), self.n), complex)
        for row, j in enumerate(others):
            kernels[row] = self.phi[j].conj()*self._cross_source(source, coordinate, int(j))
            work['gain_column_source_cross_calls'] = work.get('gain_column_source_cross_calls', 0)+1
            work['gain_column_source_cross_terms'] = work.get('gain_column_source_cross_terms', 0)+self.n
        matched_kernel = source.responses[coordinate].conj()*time_y
        base_dopplers = self.nodes[:, 0].copy()
        for value in (others, kernels, matched_kernel, base_dopplers):
            value.setflags(write=False)
        return GainColumnMoments(self, source, coordinate, others, kernels, matched_kernel, base_dopplers)

    def gram_matvec(self, value):
        """E[H^H H] value, using S[j,i] and the same-offset self terms."""
        time_value = self._daft(vector(value, self.n, 'Gram input'), inverse=True)
        output = np.trace(self.second)*time_value
        for i in range(self.p):
            for j in range(self.p):
                if i != j:
                    term = (self.second[j, i]*self.cpp[i].conj()*self.cpp[j]*
                            self.phi[i].conj()*self.phi[j]*time_value[self.indices[j]])
                    output += np.roll(term, -int(self.delays[i]))
        result = self._daft(output)
        require(np.isfinite(result).all(), 'nonfinite Gram matvec')
        return result

    def gram_diagonal(self):
        coefficients = np.zeros(self.n, complex)
        coefficients[0] = np.trace(self.second)
        for i in range(self.p):
            for j in range(self.p):
                if i != j:
                    delta = int(self.delays[j]-self.delays[i])
                    phase = np.exp(2j*np.pi*self.c1*(self.delays[i]**2-self.delays[j]**2))
                    xi = phase*np.mean(self.phi[i].conj()*self.phi[j]*
                                        np.exp(2j*self.n*self.c1*delta*self.time))
                    coefficients[delta % self.n] += self.second[j, i]*xi
        return real_result(self._fft(coefficients), 'expected Gram diagonal', nonnegative=True)

    def mean_adjoint(self, y):
        time_y = self._daft(vector(y, self.n, 'AF observation fixture'), inverse=True)
        result = np.zeros(self.n, complex)
        for i in range(self.p):
            term = self.mean[i].conj()*self.cpp[i].conj()*self.phi[i].conj()*time_y
            result += np.roll(term, -int(self.delays[i]))
        return self._daft(result)


def coordinate_log_density(coefficients, nodes, noise_variance, log_prior):
    """Continuous coordinate log density up to its normalizer at supplied nodes.

    The caller supplies the original prior's log density. This routine neither
    integrates it nor invents a data-dependent prior or a normalization rule.
    """
    coefficients = np.asarray(coefficients, complex)
    require(coefficients.ndim == 1 and len(coefficients) >= 2 and np.isfinite(coefficients).all(),
            'finite Fourier coefficient vector required')
    nodes = np.asarray(nodes)
    require(nodes.ndim == 1 and len(nodes) > 0 and not np.iscomplexobj(nodes) and np.isfinite(nodes).all(),
            'finite real evaluation nodes required')
    log_prior = np.asarray(log_prior)
    require(log_prior.shape == nodes.shape and not np.iscomplexobj(log_prior) and
            not np.isnan(log_prior).any() and not np.isposinf(log_prior).any(), 'invalid log prior')
    sigma2 = real_scalar(noise_variance, 'noise variance', positive=True)
    time = 2*np.pi*np.arange(len(coefficients))/len(coefficients)
    likelihood = (2/sigma2)*np.real(np.exp(1j*nodes[:, None]*time)@coefficients)
    require(np.isfinite(likelihood).all(), 'nonfinite coordinate likelihood')
    return log_prior+likelihood
