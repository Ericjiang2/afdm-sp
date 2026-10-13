"""Continuous densities on [-3,3]; nodes represent integration, not posteriors.

Each receiver call owns its cache and pays all construction/refinement costs.
Resolution agreement is a diagnostic, not a rigorous integration error bound.
"""
from dataclasses import dataclass
import time

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import logsumexp

SUPPORT = (-3., 3.)
ORDERS = (8, 16, 32, 64)
PANELS = 16
RESOLUTION_TOLERANCE = 1e-6
DROP_TOLERANCE = 1e-14


class CoreFailure(FloatingPointError):
    """An explicit numerical failure with partial, already-paid evidence."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = {} if evidence is None else evidence


def raise_with_evidence(error, message, evidence):
    """Preserve fatal input/program/resource errors; classify only arithmetic."""
    previous = getattr(error, 'evidence', None)
    if previous is not None:
        evidence = dict(evidence, failure_detail=previous)
    if isinstance(error, (FloatingPointError, np.linalg.LinAlgError)):
        raise CoreFailure(message+str(error), evidence) from error
    error.evidence = evidence
    raise error


def count(counts, name, amount=1):
    counts[name] = counts.get(name, 0) + amount


def finite(value, name):
    if not np.isfinite(value).all():
        raise CoreFailure(f'nonfinite {name}')


@dataclass(frozen=True)
class DopplerFactor:
    nodes: np.ndarray
    weights: np.ndarray
    phi: np.ndarray
    density: dict
    diagnostics: list

    def record(self):
        return dict(density=self.density, nodes=self.nodes, weights=self.weights,
                    phi=self.phi, levels=self.diagnostics)


class ContinuousIntegrator:
    def __init__(self, n, counts):
        if type(n) is not int or n < 2:
            raise ValueError('integer N >= 2 required')
        self.n, self.counts = n, counts
        self.time = 2*np.pi*np.arange(n)/n
        self.cache = {}

    def level(self, order):
        if order not in ORDERS:
            raise ValueError('unregistered quadrature order')
        if order in self.cache:
            count(self.counts, 'quadrature_cache_hits')
            return self.cache[order]
        start = time.perf_counter()
        count(self.counts, 'quadrature_cache_builds')
        try:
            count(self.counts, 'legendre_rule_calls')
            nodes, weights = np.polynomial.legendre.leggauss(order)
            edges = np.linspace(*SUPPORT, PANELS+1)
            half = (SUPPORT[1]-SUPPORT[0])/(2*PANELS)
            nodes = (((edges[:-1]+edges[1:])/2)[:, None]+half*nodes).ravel()
            weights = np.tile(half*weights, PANELS)
            if (np.any(weights <= 0) or
                    not np.isclose(weights.sum(), 6., rtol=0, atol=1e-12)):
                raise CoreFailure('invalid quadrature base mass')
            count(self.counts, 'quadrature_phase_entries', nodes.size*self.n)
            phase = np.exp(1j*nodes[:, None]*self.time)
            finite(phase, 'quadrature phases')
            self.cache[order] = nodes, weights, phase
            return self.cache[order]
        finally:
            count(self.counts, 'quadrature_cache_build_seconds', time.perf_counter()-start)

    def _integrate(self, evaluate, density, constant):
        levels = []
        try:
            return self._integrate_levels(evaluate, density, constant, levels)
        except Exception as error:
            raise_with_evidence(error, 'continuous integration failed: ',
                                dict(density=density, levels=levels,
                                     cause_type=type(error).__name__))

    def _integrate_levels(self, evaluate, density, constant, levels):
        previous = None
        count(self.counts, 'continuous_integrals')
        for order in ORDERS:
            start = time.perf_counter()
            entry = dict(order=order, nodes=order*PANELS, status='started')
            levels.append(entry)
            nodes, base_weights, phase = self.level(order)
            size = len(nodes)
            count(self.counts, 'quadrature_levels')
            count(self.counts, 'quadrature_density_nodes', size)
            reduced = evaluate(nodes, phase)
            finite(reduced, 'reduced continuous log kernel')
            logits = np.log(base_weights/6.)+reduced
            normalizer = float(logsumexp(logits))
            log_mass = logits-normalizer
            finite(log_mass, 'quadrature log masses')
            keep = log_mass > np.log(DROP_TOLERANCE/size)
            if not np.any(keep):
                raise CoreFailure('quadrature discarded all nodes', dict(levels=levels))
            dropped = int(np.count_nonzero(~keep))
            dropped_log_mass = float(logsumexp(log_mass[~keep])) if dropped else None
            with np.errstate(under='ignore'):
                dropped_mass = float(np.exp(dropped_log_mass)) if dropped else 0.
            # The log mass remains available even if this scalar underflows.
            dropped_bound = dropped*DROP_TOLERANCE/size
            if dropped_mass > DROP_TOLERANCE or dropped_mass > dropped_bound*(1+1e-10):
                raise CoreFailure('quadrature tail exceeds declared mass bound')
            kept_log_mass = log_mass[keep]-logsumexp(log_mass[keep])
            probabilities = np.exp(kept_log_mass)
            if np.any(probabilities <= 0):
                raise CoreFailure('retained quadrature mass underflowed')
            count(self.counts, 'quadrature_characteristic_terms', int(keep.sum())*self.n)
            phi = probabilities@phase[keep]
            if abs(phi[0]-1) > 1e-12 or np.max(abs(phi)) > 1+1e-12:
                raise CoreFailure('invalid characteristic moments')
            finite(phi, 'integrated characteristic moments')
            panels = np.repeat(np.arange(PANELS), order)
            raw_difference = (None if previous is None else
                              float(np.max(abs(phi-previous['phi']))))
            # Adding the two explicit deletion bounds makes the test conservative
            # for the full quadrature sums; no tolerance is silently relaxed.
            difference = (None if previous is None else
                          raw_difference+2*dropped_bound+previous['moment_tail_bound'])
            log_difference = (None if previous is None else
                              abs(normalizer-previous['normalizer']))
            entry.update(status='completed', retained_nodes=int(keep.sum()),
                         centered_log_normalizer=normalizer, constant=constant,
                         log_normalizer=normalizer+constant,
                         max_node_log_density=float(np.max(reduced)-normalizer-np.log(6.)),
                         max_node_mass=float(np.exp(np.max(log_mass))),
                         retained_panel_mass=np.bincount(panels[keep], weights=probabilities,
                                                         minlength=PANELS),
                         dropped_nodes=dropped, dropped_mass=dropped_mass,
                         dropped_log_mass=dropped_log_mass, dropped_mass_bound=dropped_bound,
                         moment_tail_bound=2*dropped_bound,
                         raw_phi_difference=raw_difference, phi_difference_bound=difference,
                         log_normalizer_difference=log_difference,
                         seconds=time.perf_counter()-start)
            count(self.counts, 'quadrature_dropped_nodes', dropped)
            if previous is not None and (difference <= RESOLUTION_TOLERANCE and
                                         log_difference <= RESOLUTION_TOLERANCE):
                result_density = dict(density, support=SUPPORT, base_density='uniform[-3,3]',
                                      log_normalizer=normalizer+constant,
                                      centered_log_normalizer=normalizer, constant=constant,
                                      resolution_agreement=True,
                                      expected_log_kernel=float(probabilities@reduced[keep])+constant,
                                      kl_to_uniform=float(probabilities@reduced[keep])-normalizer)
                finite(result_density['log_normalizer'], 'continuous normalizer')
                return DopplerFactor(nodes[keep].copy(), probabilities, phi,
                                     result_density, levels)
            previous = dict(phi=phi, normalizer=normalizer, moment_tail_bound=2*dropped_bound)
        raise CoreFailure('continuous integration did not agree by 1024 nodes',
                          dict(density=density, levels=levels))

    def initial(self, center):
        if not np.isfinite(center) or not SUPPORT[0] <= center <= SUPPORT[1]:
            raise ValueError('initial Doppler outside working support')
        return self._integrate(lambda nodes, phase: -.5*((nodes-center)/.125)**2,
                               dict(kind='truncated_gaussian', center=float(center), sigma=.125), 0.)

    def from_coefficients(self, coefficients, sigma2):
        coefficients = np.asarray(coefficients, complex)
        if coefficients.shape != (self.n,) or not np.isfinite(coefficients).all():
            raise ValueError('finite Fourier coefficient vector required')
        if not np.isfinite(sigma2) or sigma2 <= 0:
            raise ValueError('positive finite noise variance required')
        constant = float(2*coefficients[0].real/sigma2)
        finite(constant, 'coordinate constant')

        def evaluate(nodes, phase):
            count(self.counts, 'quadrature_fourier_terms', len(nodes)*(self.n-1))
            return (2/sigma2)*np.real(phase[:, 1:]@coefficients[1:])

        return self._integrate(evaluate, dict(kind='fourier', coefficients=coefficients.copy(),
                                              sigma2=float(sigma2)), constant)


def point_factor(value, n, counts):
    if not np.isfinite(value) or not SUPPORT[0] <= value <= SUPPORT[1]:
        raise ValueError('point Doppler outside working support')
    count(counts, 'point_characteristic_phase_entries', n)
    phi = np.exp(2j*np.pi*np.arange(n)*value/n)
    return DopplerFactor(np.array([value]), np.ones(1), phi,
                         dict(kind='point', value=float(value), support=SUPPORT), [])


class PointOptimizer:
    """Optimize the Fourier expected-log-likelihood coordinate potential.

    Other q factors are frozen; these scores are not marginal likelihoods.
    The n=0 constant is removed for comparison, then recorded separately.
    """

    def __init__(self, n, counts):
        self.n, self.counts = n, counts
        self.grid = np.linspace(*SUPPORT, 257)
        self.time = 2*np.pi*np.arange(n)/n
        start = time.perf_counter()
        count(counts, 'point_grid_phase_entries', 257*n)
        self.phase = np.exp(1j*self.grid[:, None]*self.time)
        count(counts, 'point_grid_build_seconds', time.perf_counter()-start)

    def update(self, coefficients, sigma2, previous):
        trace = dict(previous=float(previous), refinements=[])
        try:
            return self._update(coefficients, sigma2, previous, trace)
        except Exception as error:
            raise_with_evidence(error, 'point coordinate failed: ',
                                dict(trace=trace, cause_type=type(error).__name__))

    def _update(self, coefficients, sigma2, previous, trace):
        coefficients = np.asarray(coefficients, complex)
        if coefficients.shape != (self.n,) or not np.isfinite(coefficients).all():
            raise ValueError('finite Fourier coefficient vector required')
        if not np.isfinite(sigma2) or sigma2 <= 0:
            raise ValueError('positive finite noise required')
        if not np.isfinite(previous) or not SUPPORT[0] <= previous <= SUPPORT[1]:
            raise ValueError('previous point outside working support')
        count(self.counts, 'point_coordinate_updates')
        count(self.counts, 'point_grid_scores', len(self.grid))
        count(self.counts, 'point_fourier_terms', len(self.grid)*(self.n-1))
        scores = (2/sigma2)*np.real(self.phase[:, 1:]@coefficients[1:])
        finite(scores, 'point grid likelihood')

        def score(value):
            count(self.counts, 'point_local_scores')
            count(self.counts, 'point_local_phase_entries', self.n-1)
            count(self.counts, 'point_fourier_terms', self.n-1)
            result = float((2/sigma2)*np.real(np.exp(1j*value*self.time[1:])@coefficients[1:]))
            finite(result, 'point refined likelihood')
            return result

        peaks = [i for i in range(1, len(self.grid)-1)
                 if scores[i] >= scores[i-1] and scores[i] >= scores[i+1]
                 and (scores[i] > scores[i-1] or scores[i] > scores[i+1])]
        peaks = sorted(peaks, key=lambda i: (-scores[i], i))[:3]
        candidates = [(float(previous), score(previous)),
                      (SUPPORT[0], float(scores[0])), (SUPPORT[1], float(scores[-1]))]
        best_grid = int(np.argmax(scores))
        candidates.append((float(self.grid[best_grid]), float(scores[best_grid])))
        trace.update(grid_scores=scores, selected_peaks=peaks,
                     constant=float(2*coefficients[0].real/sigma2))
        for index in peaks:
            bounds = (float(self.grid[index-1]), float(self.grid[index+1]))
            detail = dict(bounds=bounds, status='started')
            trace['refinements'].append(detail)
            count(self.counts, 'point_bounded_minimizations')
            result = minimize_scalar(lambda value: -score(value), bounds=bounds, method='bounded',
                                     options=dict(xatol=1e-6, maxiter=32))
            detail.update(status='completed', success=bool(result.success), nfev=int(result.nfev),
                          x=float(result.x), fun=float(result.fun), message=str(result.message))
            if not result.success or not np.isfinite([result.x, result.fun]).all():
                raise CoreFailure('point bounded optimization failed', trace)
            candidates.append((float(self.grid[index]), float(scores[index])))
            candidates.append((float(result.x), -float(result.fun)))
        value, potential = max(candidates, key=lambda item: item[1])
        trace.update(selected=value, reduced_coordinate_potential=potential, candidates=candidates,
                     coefficients=coefficients.copy())
        return point_factor(value, self.n, self.counts), trace


def rectangular_nodes(factors, counts):
    """Split retained mass among duplicate positions; never fill with zeros."""
    width = max(len(factor.nodes) for factor in factors)
    nodes, weights = [], []
    for factor in factors:
        extra = width-len(factor.nodes)
        largest = int(np.argmax(factor.weights))
        repeats = np.ones(len(factor.nodes), dtype=int)
        repeats[largest] += extra
        nodes.append(np.repeat(factor.nodes, repeats))
        weights.append(np.repeat(factor.weights/repeats, repeats))
        count(counts, 'moment_padding_duplicate_nodes', extra)
    return np.asarray(nodes), np.asarray(weights)
