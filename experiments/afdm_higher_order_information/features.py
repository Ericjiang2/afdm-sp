"""Observed power features and covariance-aware Gaussian-control GMM.

No function accepts a realized channel, data word, true gap or latent PDP.
"""
import time

import numpy as np

from experiments.sp_afdm_frozen_20260920.src.physical import daft


def validate_lags(n, lags):
    lags = np.asarray(lags)
    if (lags.ndim != 2 or lags.shape[1] != 2 or not len(lags)
            or not np.issubdtype(lags.dtype, np.integer) or np.any(lags <= 0)
            or np.any(lags >= n) or np.any(lags[:, 0] == lags[:, 1])):
        raise ValueError('distinct nonzero in-range integer lag pairs required')
    return lags


def observed_features(y_daft, c1, c2, lags):
    """One inverse DAFT per observation, then O(N+J) power arithmetic."""
    y = np.asarray(y_daft, complex)
    if y.ndim != 2 or not np.isfinite(y).all() or not np.isfinite([c1, c2]).all():
        raise ValueError('finite observed rows and chirps required')
    lags = validate_lags(y.shape[1], lags)
    started = time.perf_counter()
    r = daft(y.T, c1, c2, True).T
    powers = abs(r)**2
    t = powers[:, :1]*(powers[:, lags[:, 0]]-powers[:, lags[:, 1]])
    result = np.column_stack((powers.mean(axis=1), (powers**2).mean(axis=1), t))
    return result, dict(seconds=time.perf_counter()-started, observations=len(y),
        inverse_daft_vectors=len(y), input_elements=int(y.size), feature_values=int(result.size),
        order='O(M N log N + M J) including inverse DAFT', truth_inputs=0)


def control_mean(n, lags, parameters):
    """E F for Gaussian h, iid unit QPSK, q/tau/sigma2 columns, no center claim."""
    lags = validate_lags(n, lags)
    p = np.asarray(parameters, float)
    if (p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all()
            or np.any(p[:, 0] < 0) or np.any(p[:, 1:] <= 0)):
        raise ValueError('finite candidate rows q>=0, tau>0, sigma2>0 required')
    q, tau, noise = p.T
    time_lag = 2*np.pi*lags/n
    total = tau+noise
    t = (1-1/n)*tau[:, None]**2*(np.cos(np.sqrt(q)[:, None]*time_lag[:, 0])**2
                                  -np.cos(np.sqrt(q)[:, None]*time_lag[:, 1])**2)
    return np.column_stack((total, 2*total**2+2*(1-1/n)*tau**2, t))


def collision_jacobian(n, lags, tau, noise):
    """Analytic moment Jacobian at q=0; columns q, mu, tau, sigma2."""
    lags = validate_lags(n, lags)
    if not np.isfinite([tau, noise]).all() or min(tau, noise) <= 0:
        raise ValueError('positive declared working power and noise required')
    j = np.zeros((2+len(lags), 4))
    j[0, 2:] = 1
    j[1, 2] = 4*(tau+noise)+4*(1-1/n)*tau
    j[1, 3] = 4*(tau+noise)
    j[2:, 0] = (1-1/n)*tau**2*(2*np.pi/n)**2*(lags[:, 1]**2-lags[:, 0]**2)
    return j


def covariance_metric(covariance, rcond=1e-12):
    """Declared PSD support inverse; no jitter and every discarded direction reported."""
    covariance = np.asarray(covariance, float)
    if (covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]
            or not np.isfinite(covariance).all() or not 0 < rcond < 1
            or not np.allclose(covariance, covariance.T, atol=1e-12, rtol=1e-12)):
        raise ValueError('finite symmetric covariance and declared rank tolerance required')
    values, vectors = np.linalg.eigh(covariance)
    scale = max(float(values[-1]), 1.)
    if values[0] < -rcond*scale:
        raise ValueError('indefinite feature covariance')
    keep = values > rcond*scale
    if not np.any(keep):
        raise ValueError('zero feature covariance has no usable metric support')
    inverse = (vectors[:, keep]/values[keep]) @ vectors[:, keep].T
    return inverse, dict(rank=int(keep.sum()), eigenvalues=values.tolist(),
                         rcond=rcond, discarded_directions=int((~keep).sum()))


def nuisance_projection(covariance, jacobian, rcond=1e-12):
    """GMM feature direction orthogonal to all declared nuisance derivatives."""
    inverse, support = covariance_metric(covariance, rcond)
    jacobian = np.asarray(jacobian, float)
    if jacobian.shape != (len(inverse), 4) or not np.isfinite(jacobian).all():
        raise ValueError('finite matching q/mu/tau/noise Jacobian required')
    jq, nuisance = jacobian[:, 0], jacobian[:, 1:]
    nuisance_gram = nuisance.T @ inverse @ nuisance
    beta = np.linalg.pinv(nuisance_gram, rcond=rcond, hermitian=True) @ nuisance.T @ inverse @ jq
    weight = inverse @ (jq-nuisance @ beta)
    slope = float(weight @ jq)
    variance = float(weight @ covariance @ weight)
    identifiable = variance > rcond and abs(slope) > rcond
    return weight, dict(support=support, nuisance_rank=int(np.linalg.matrix_rank(nuisance_gram, tol=rcond)),
        nuisance_coefficients=beta.tolist(), nuisance_residual=(weight @ nuisance).tolist(),
        slope=slope, variance=variance, feature_information=slope*slope/variance if identifiable else 0.,
        identifiable=bool(identifiable), reason='finite training covariance and declared control Jacobian' if identifiable else 'no usable q direction',
        interpretation='estimated working-model information certificate, not exact population Fisher')


class CandidateBank:
    """Same physical grid in q or original half-gap coordinates; no adaptive starts."""
    def __init__(self, n, lags, q_grid, tau_grid, noise_grid, covariance, coordinates='q'):
        if coordinates not in ('q', 'delta'):
            raise ValueError('coordinates must be q or delta')
        started = time.perf_counter()
        axes = [np.asarray(x, float) for x in (q_grid, tau_grid, noise_grid)]
        if any(x.ndim != 1 or not len(x) or not np.isfinite(x).all() or np.any(np.diff(x) <= 0) for x in axes):
            raise ValueError('nonempty strictly increasing finite physical grids required')
        q, tau, noise = np.meshgrid(*axes, indexing='ij')
        self.parameters = np.column_stack((q.ravel(), tau.ravel(), noise.ravel()))
        self.coordinates = coordinates
        evaluated = self.parameters.copy()
        if coordinates == 'delta':
            evaluated[:, 0] = np.sqrt(evaluated[:, 0])**2
        self.means = control_mean(n, lags, evaluated)
        self.inverse, self.support = covariance_metric(covariance)
        self.weighted_means = self.means @ self.inverse
        self.constant = np.sum(self.weighted_means*self.means, axis=1)
        self.axes = axes
        self.setup = dict(seconds=time.perf_counter()-started, candidates=len(self.parameters),
                          moment_response_values=int(self.means.size), metric_factorizations=1)

    def estimate(self, observed, batch=128):
        observed = np.asarray(observed, float)
        if observed.ndim != 2 or observed.shape[1] != self.means.shape[1] or not np.isfinite(observed).all():
            raise ValueError('finite observed feature means required')
        started = time.perf_counter(); indices=[]; objectives=[]
        for start in range(0, len(observed), batch):
            f = observed[start:start+batch]
            objective = self.constant[None, :]-2*f @ self.weighted_means.T+np.sum((f @ self.inverse)*f, axis=1)[:, None]
            index = np.argmin(objective, axis=1)
            indices.append(index); objectives.append(objective[np.arange(len(index)), index])
        index=np.concatenate(indices); estimate=self.parameters[index]
        boundary=np.column_stack([(estimate[:, j]==axis[0])|(estimate[:, j]==axis[-1]) if len(axis)>1 else np.zeros(len(estimate), bool)
                                  for j, axis in enumerate(self.axes)])
        return dict(parameters=estimate, half_gap=np.sqrt(estimate[:, 0]), indices=index,
            objectives=np.concatenate(objectives), boundary=boundary,
            cost=dict(seconds=time.perf_counter()-started, feature_groups=len(observed),
                candidate_objectives=len(observed)*len(self.parameters), new_moment_response_values=0,
                cached_response_values=self.setup['moment_response_values'],
                failed_groups=0, center_identifiable=False, coordinates=self.coordinates))
