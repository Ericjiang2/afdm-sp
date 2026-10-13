"""Observed-only continuous nuisance fits and collision score/moment tests.

The null family is independent of latent PDP.  The one-sided collision tangent
is admitted separately at the final fitted point, never by clipping a fit away
from an inconvenient branch boundary.  All fitted parameter inputs are public.
"""
from functools import lru_cache
from itertools import product
from math import comb, factorial
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import i0e, i1e, logsumexp

from experiments.afdm_collision_resolution.collision_teacher import power_exponents, power_features
from experiments.afdm_efficient_information.prior_likelihood import pdp_distribution, qpsk_time, system_for
from experiments.afdm_higher_order_information.prior import geometry

DEFAULT_CONFIG = dict(
    bounds=[[.22, .42], [float(np.log(.3)), float(np.log(2.))],
            [float(np.log(.08)), float(np.log(2.))]],
    starts_mu=[.24, .31, .40], starts_signal_fraction=[.35, .65],
    optimizer=dict(maxiter=80, maxls=30, ftol=1e-10, gtol=1e-6),
    stationarity_tolerance=1e-3, boundary_tolerance=1e-7,
    rcond=1e-10, branch_tolerance=1e-9,
)


class TangentUnavailable(ValueError):
    """A valid fitted null point has no admitted local collision tangent."""


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key:plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def settings(config=None):
    config = {} if config is None else config
    unknown = set(config)-set(DEFAULT_CONFIG)
    if unknown:
        raise ValueError(f'unknown method configuration fields: {sorted(unknown)}')
    result = {**DEFAULT_CONFIG, **config}
    result['optimizer'] = {**DEFAULT_CONFIG['optimizer'], **config.get('optimizer', {})}
    if set(result['optimizer']) != set(DEFAULT_CONFIG['optimizer']):
        raise ValueError('unsupported optimizer option')
    bounds = np.asarray(result['bounds'], float)
    if bounds.shape != (3, 2) or not np.isfinite(bounds).all() or np.any(bounds[:, 0] >= bounds[:, 1]):
        raise ValueError('three ordered finite public parameter bounds required')
    if bounds[0, 0] < .22 or bounds[0, 1] > .42:
        raise ValueError('qualified physical null domain is mu in [.22,.42]')
    if np.any(bounds[1:, 0] < np.log([.3, .08])) or np.any(bounds[1:, 1] > np.log(2.)):
        raise ValueError('qualified positive scale bounds exceeded')
    starts = np.asarray(result['starts_mu'], float)
    fractions = np.asarray(result['starts_signal_fraction'], float)
    if starts.ndim != 1 or not len(starts) or not np.isfinite(starts).all() or np.any(starts < bounds[0, 0]) or np.any(starts > bounds[0, 1]):
        raise ValueError('finite public mu starts must lie within bounds')
    if fractions.ndim != 1 or not len(fractions) or not np.isfinite(fractions).all() or np.any(fractions <= 0) or np.any(fractions >= 1):
        raise ValueError('starting signal fractions must lie strictly between zero and one')
    for key in ('stationarity_tolerance', 'boundary_tolerance', 'rcond', 'branch_tolerance'):
        if not np.isfinite(result[key]) or result[key] <= 0:
            raise ValueError(f'positive finite {key} required')
    if result['rcond'] >= 1 or result['boundary_tolerance'] >= .01 or result['branch_tolerance'] >= .001:
        raise ValueError('unqualified numerical tolerance')
    for key in ('maxiter', 'maxls'):
        if not isinstance(result['optimizer'][key], int) or result['optimizer'][key] <= 0:
            raise ValueError('positive integer optimizer limits required')
    for key in ('ftol', 'gtol'):
        if not np.isfinite(result['optimizer'][key]) or result['optimizer'][key] <= 0:
            raise ValueError('positive finite optimizer stopping tolerance required')
    return result


def observations(y):
    y = np.asarray(y, complex)
    if y.ndim != 2 or y.shape[1] != 4 or len(y) < 8 or not np.isfinite(y).all():
        raise ValueError('at least eight finite observed rows of length four required')
    return y


def psd_inverse(matrix, rcond):
    matrix = np.asarray(matrix, float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or not np.isfinite(matrix).all():
        raise ValueError('finite square covariance required')
    if not np.allclose(matrix, matrix.T, atol=1e-11, rtol=1e-11):
        raise ValueError('symmetric covariance required')
    values, vectors = np.linalg.eigh(matrix)
    if values[-1] <= 0 or values[0] < -rcond*values[-1]:
        raise ValueError('nonpositive/indefinite covariance; no jitter allowed')
    keep = values > rcond*values[-1]
    return (vectors[:, keep]/values[keep])@vectors[:, keep].T, dict(
        rank=int(keep.sum()), eigenvalues=values,
        condition=float(values[-1]/values[keep][0]), cutoff=float(rcond*values[-1]))


class NullFamily:
    """Exact P0 symbol/phase likelihood and finite Gaussian power moments."""
    def __init__(self):
        started = time.perf_counter()
        self.system = system_for(4)
        self.states = qpsk_time(4)
        self.exponents = power_exponents(4)
        self.offsets = np.arange(-2, 3)
        self.frequency = 2j*np.pi*np.arange(4)/4
        self.atoms = np.exp(2j*np.pi*np.outer(np.arange(4), np.arange(-1, 2))/4)
        self._last_geometry = None
        self._pdp_cache = {}
        self._polynomials = {}
        self._symbol_moments = {}
        indices = {tuple(np.zeros(4, int)), *map(tuple, self.exponents)}
        indices.update(tuple(a+b) for a in self.exponents for b in self.exponents)
        for exponent in sorted(indices):
            terms = []
            for noise_power in product(*[range(k+1) for k in exponent]):
                signal = tuple(k-l for k, l in zip(exponent, noise_power))
                if signal not in self._symbol_moments:
                    self._symbol_moments[signal] = float(np.mean(np.prod(abs(self.states)**(2*np.asarray(signal)), axis=1)))
                coefficient = float(np.prod([comb(k, l)**2*factorial(l) for k, l in zip(exponent, noise_power)]))
                terms.append((coefficient*self._symbol_moments[signal], sum(noise_power), np.asarray(signal, int)))
            self._polynomials[exponent] = terms
        self.geometry_qualification = []
        for mu in (.22, .27, .31, .35, .42):
            ours = self.chart(mu)
            original = geometry(self.system, mu, 0.)
            error = float(np.max(abs(ours['w']-original['g0'][:, 0])))
            if error > 3e-13 or not np.array_equal(ours['retained'], original['weights'][:3, 0] != 0):
                raise ValueError('null Fourier chart does not match frozen physical geometry')
            self.geometry_qualification.append(dict(mu=mu, max_error=error))
        self.creation_seconds = time.perf_counter()-started

    def chart(self, mu):
        if not np.isfinite(mu) or not .22 <= mu <= .42:
            raise ValueError('mu outside qualified public physical chart [.22,.42]')
        if self._last_geometry is not None and self._last_geometry['mu'] == float(mu):
            return self._last_geometry
        fourier = np.exp((self.offsets[:, None]+mu)*self.frequency)
        alpha, dot = fourier.mean(axis=1), (fourier*self.frequency).mean(axis=1)
        norm = np.sqrt(np.sum(abs(alpha)**2)+1e-300)
        normalized_dot = dot/norm-alpha*np.real(np.vdot(alpha, dot))/norm**3
        alpha = alpha/norm
        power = abs(alpha)**2
        mask = power >= self.system.frac_prune_rel_thres*power.max()
        support_margin = float(np.min(abs(power-self.system.frac_prune_rel_thres*power.max()))/power.max())
        # k=-1,0,1 are the unclipped integer atoms throughout the public chart.
        retained = mask[1:4]
        if not retained.all() or support_margin <= 1e-12:
            raise ValueError('physical support outside qualified smooth null chart')
        w, w_dot = self.atoms@alpha[1:4], self.atoms@normalized_dot[1:4]
        w2 = np.vdot(w, w).real
        u0 = w/np.sqrt(w2)
        u0_dot = (w_dot-w*np.real(np.vdot(w, w_dot))/w2)/np.sqrt(w2)
        b = w_dot-w*np.vdot(w, w_dot)/w2
        b2 = np.vdot(b, b).real
        if b2 <= 1e-20:
            raise ValueError('degenerate collision geometry')
        result = dict(mu=float(mu), w=w, w_dot=w_dot, u0=u0, u0_dot=u0_dot,
                      u1=b/np.sqrt(b2), w2=float(w2), b2=float(b2), retained=retained,
                      physical_support_margin=support_margin)
        self._last_geometry = result
        return result

    def point(self, theta):
        theta = np.asarray(theta, float)
        if theta.shape != (3,) or not np.isfinite(theta).all() or np.any(abs(theta[1:]) > 30):
            raise ValueError('finite theta=(mu,log_tau,log_sigma2) required')
        chart = self.chart(theta[0])
        tau, sigma2 = np.exp(theta[1:])
        base = np.sqrt(4*tau)*chart['u0']
        tangent = np.sqrt(4*tau)*chart['u1']
        mu_derivative = np.sqrt(4*tau)*chart['u0_dot']
        return dict(theta=theta, tau=tau, sigma2=sigma2, chart=chart,
                    base=base, tangent=tangent, mu_derivative=mu_derivative,
                    m0=base*self.states, m1=tangent*self.states, m_mu=mu_derivative*self.states)

    def tangent_factor(self, point, tolerance=1e-9):
        mu = point['theta'][0]
        # Exactly the public physical constants used by frozen pdp_distribution.
        latent = pdp_distribution(4, mu, 0.)
        k = latent['max_corrected_index']
        limit = int(latent['limits'][0])
        edges = np.array([6*(limit/k-1), 6*((limit+1)/k-1)])
        margin = float(min(mu-edges[0], edges[1]-mu))
        if margin <= tolerance or len(set(latent['limits'])) != 1:
            raise TangentUnavailable('fitted null point lies on/too close to a discrete PDP branch boundary')
        key = (k, limit)
        if key not in self._pdp_cache:
            d = latent['pdp']
            self._pdp_cache[key] = float(latent['weights']@(4*d[:, 0]*d[:, 1]/d.sum(axis=1)**2))
        chart = point['chart']
        kappa = self._pdp_cache[key]*chart['b2']/chart['w2']
        return kappa, dict(pdp_limits=latent['limits'], pdp_branch_edges=edges,
                           pdp_branch_margin=margin, physical_support_margin=chart['physical_support_margin'],
                           pdp_components=len(latent['weights']), kappa=float(kappa))

    def density(self, y, theta, tangent=False, branch_tolerance=1e-9):
        y = np.asarray(y, complex)
        if y.ndim != 2 or y.shape[1] != 4 or not len(y) or not np.isfinite(y).all():
            raise ValueError('finite N4 observation rows required')
        point = self.point(theta)
        m0, s = point['m0'], point['sigma2']
        a = np.sum(abs(m0)**2, axis=1)
        c = y.conj()@m0.T
        radius = abs(c)
        z = 2*radius/s
        bessel = i0e(z)
        ratio = i1e(z)/bessel
        yp = np.sum(abs(y)**2, axis=1)
        logs = -(yp[:, None]+a)/s+np.log(bessel)+z-4*np.log(np.pi*s)-np.log(len(m0))
        logpdf = logsumexp(logs, axis=1)
        posterior = np.exp(logs-logpdf[:, None])
        unit = np.divide(c.conj(), radius, out=np.zeros_like(c), where=radius > 0)
        mu_component = (-2*np.real(np.sum(m0.conj()*point['m_mu'], axis=1))
                        +2*ratio*np.real(unit*(y.conj()@point['m_mu'].T)))/s
        tau_component = (-a+ratio*radius)/s
        noise_component = -4+(yp[:, None]+a)/s-ratio*z
        columns = [mu_component, tau_component, noise_component]
        metadata = None
        if tangent:
            kappa, metadata = self.tangent_factor(point, branch_tolerance)
            m1 = point['m1']
            d = y.conj()@m1.T
            e = np.sum(m0.conj()*m1, axis=1)
            target = kappa*((abs(d)**2+abs(e)**2-2*ratio*np.real(d*e.conj()*unit))/s**2
                             -np.sum(abs(m1)**2, axis=1)/s-(ratio*radius-a)/s)
            columns.insert(0, target)
        return dict(logpdf=logpdf, score=np.column_stack([np.sum(posterior*x, axis=1) for x in columns]),
                    tangent_metadata=metadata)

    @staticmethod
    def _radial_polynomial_tangent(exponent, powers, mean, direction):
        value = -sum(exponent)*np.prod(powers**exponent)
        for i in np.flatnonzero(exponent):
            k = exponent.copy(); k[i] -= 1
            value += exponent[i]**2*abs(direction[i])**2*np.prod(powers**k)
            for j in np.flatnonzero(exponent):
                if j <= i:
                    continue
                k = exponent.copy(); k[i] -= 1; k[j] -= 1
                value += (2*exponent[i]*exponent[j]
                          *np.real(direction[i]*direction[j].conj()*mean[i].conj()*mean[j])
                          *np.prod(powers**k))
        return float(value)

    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
        point = self.point(theta)
        powers, s = abs(point['base'])**2, point['sigma2']
        power_jac = np.column_stack((2*np.real(point['base'].conj()*point['mu_derivative']), powers))
        # Degree <=2 means/Jacobians are the optimization hot path.  Their
        # closed Gaussian formulas avoid rebuilding the degree-four covariance.
        power_jac = np.column_stack((power_jac, np.zeros(4)))
        noise_jac = np.array([0., 0., s])
        means = list(powers+s)
        jacobians = list(power_jac+noise_jac)
        for i in range(4):
            for j in range(i, 4):
                exponent = np.zeros(4, int); exponent[i] += 1; exponent[j] += 1
                constant = self._symbol_moments[tuple(exponent)]
                if i == j:
                    means.append(constant*powers[i]**2+4*s*powers[i]+2*s**2)
                    jacobians.append((2*constant*powers[i]+4*s)*power_jac[i]
                                     +(4*powers[i]+4*s)*noise_jac)
                else:
                    means.append(constant*powers[i]*powers[j]+s*(powers[i]+powers[j])+s**2)
                    jacobians.append(constant*(powers[i]*power_jac[j]+powers[j]*power_jac[i])
                                     +s*(power_jac[i]+power_jac[j])
                                     +(powers[i]+powers[j]+2*s)*noise_jac)
        mean, jacobian = np.asarray(means), np.asarray(jacobians)
        result = dict(mean=mean, jacobian=jacobian)
        if covariance:
            values = {}
            for a in self.exponents:
                for b in self.exponents:
                    key = tuple(a+b)
                    if key not in values:
                        values[key] = sum(coefficient*s**noise_degree*np.prod(powers**exponent)
                                          for coefficient, noise_degree, exponent in self._polynomials[key])
            second = np.array([[values[tuple(a+b)] for b in self.exponents] for a in self.exponents])
            result['covariance'] = second-np.outer(mean, mean)
        if tangent:
            kappa, metadata = self.tangent_factor(point, branch_tolerance)
            derivative = []
            for exponent in self.exponents:
                total = 0.
                for coefficient, noise_degree, signal in self._polynomials[tuple(exponent)]:
                    total += coefficient*s**noise_degree*self._radial_polynomial_tangent(
                        signal, powers, point['base'], point['tangent'])
                derivative.append(kappa*total)
            result['derivatives'] = np.column_stack((derivative, jacobian))
            result['tangent_metadata'] = metadata
        return result


@lru_cache(maxsize=1)
def cached_family():
    return NullFamily()


def _starts(y, config):
    total = float(np.mean(abs(y)**2))
    if total <= 0:
        raise ValueError('positive observed energy required')
    bounds = np.asarray(config['bounds'])
    starts = []
    for mu in config['starts_mu']:
        for fraction in config['starts_signal_fraction']:
            proposed = np.array([mu, np.log(fraction*total), np.log((1-fraction)*total)])
            # This is a declared feasible initialization, not post-hoc clipping
            # of a fitted nuisance estimate or a tangent's branch membership.
            feasible = np.minimum(np.maximum(proposed, bounds[:, 0]), bounds[:, 1])
            starts.append(dict(theta=feasible, proposed=proposed,
                               initialization_bound_projection=bool(np.any(feasible != proposed))))
    return starts


def _fit(objective, starts, config):
    bounds = np.asarray(config['bounds'])
    traces = []
    for start in starts:
        result = minimize(objective, start['theta'], method='L-BFGS-B', jac=True,
                          bounds=bounds, options=config['optimizer'])
        if not np.isfinite(result.fun) or not np.isfinite(result.x).all() or not np.isfinite(result.jac).all():
            raise ValueError('optimizer returned a nonfinite objective/parameter/gradient')
        lower = abs(result.x-bounds[:, 0]) <= config['boundary_tolerance']
        upper = abs(result.x-bounds[:, 1]) <= config['boundary_tolerance']
        projected = np.asarray(result.jac).copy()
        projected[lower & (projected > 0)] = 0.
        projected[upper & (projected < 0)] = 0.
        pg = float(np.max(abs(projected)))
        traces.append(dict(theta=result.x, objective=float(result.fun), gradient=result.jac,
                           projected_gradient_max=pg, optimizer_success=bool(result.success),
                           success=bool(result.success and pg <= config['stationarity_tolerance']),
                           status=int(result.status), message=str(result.message),
                           iterations=int(result.nit), evaluations=int(result.nfev),
                           lower_boundary=lower, upper_boundary=upper, start=start))
    selected = min(range(len(traces)), key=lambda index:traces[index]['objective'])
    best = traces[selected]
    return dict(theta=best['theta'], success=best['success'], selected_start=selected,
                objective=best['objective'], on_boundary=bool(np.any(best['lower_boundary'] | best['upper_boundary'])),
                projected_gradient_max=best['projected_gradient_max'], starts=traces,
                total_evaluations=sum(item['evaluations'] for item in traces),
                failed_starts=sum(not item['success'] for item in traces))


def fit_null_mle(y, config=None, family=None):
    y, config = observations(y), settings(config)
    family = cached_family() if family is None else family
    started = time.perf_counter()
    def objective(theta):
        result = family.density(y, theta)
        return -float(result['logpdf'].mean()), -result['score'].mean(axis=0)
    fit = _fit(objective, _starts(y, config), config)
    fit.update(method='continuous exact-null MLE', seconds=time.perf_counter()-started,
               objective_scale='negative mean log likelihood', observations=len(y))
    return fit


def fit_null_m14(y, config=None, family=None):
    y, config = observations(y), settings(config)
    family = cached_family() if family is None else family
    started = time.perf_counter()
    features = power_features(y, family.exponents)
    observed_mean = features.mean(axis=0)
    diagonal = features.var(axis=0)
    if np.any(diagonal <= 0) or not np.isfinite(diagonal).all():
        raise ValueError('initial GMM feature variance is zero/nonfinite; no variance floor')
    initial_weight = np.diag(1/diagonal)
    def objective(weight):
        def evaluate(theta):
            model = family.moments(theta)
            residual = observed_mean-model['mean']
            return float(residual@weight@residual), -2*model['jacobian'].T@weight@residual
        return evaluate
    first = _fit(objective(initial_weight), _starts(y, config), config)
    if not first['success']:
        return dict(method='two-step observed-only 14-moment GMM', theta=first['theta'], success=False,
                    on_boundary=first['on_boundary'], first=first, second=None,
                    failure_reason='first-step GMM optimizer failed', seconds=time.perf_counter()-started,
                    observed_mean=observed_mean, total_evaluations=first['total_evaluations'])
    reference = family.moments(first['theta'], covariance=True)
    weight, qualification = psd_inverse(reference['covariance'], config['rcond'])
    second = _fit(objective(weight), [dict(theta=first['theta'], proposed=first['theta'],
                                         initialization_bound_projection=False)], config)
    return dict(method='two-step observed-only 14-moment GMM', theta=second['theta'], success=second['success'],
                on_boundary=second['on_boundary'], first=first, second=second,
                weight_covariance=qualification, weight_matrix=weight, observed_mean=observed_mean,
                total_evaluations=first['total_evaluations']+second['total_evaluations'],
                seconds=time.perf_counter()-started)


def test_full_score(y, fit, config=None, family=None):
    y, config = observations(y), settings(config)
    if not fit['success']:
        raise ValueError('full score requires a successful null fit')
    family = cached_family() if family is None else family
    result = family.density(y, fit['theta'], tangent=True, branch_tolerance=config['branch_tolerance'])
    scores = result['score']
    gram = scores.T@scores/len(y)
    inverse, qualification = psd_inverse(gram[1:, 1:], config['rcond'])
    beta = inverse@gram[1:, 0]
    residual = scores[:, 0]-scores[:, 1:]@beta
    effective, raw = float(np.mean(residual**2)), float(gram[0, 0])
    if min(effective, raw) <= 0 or not np.isfinite([effective, raw]).all():
        raise ValueError('nonpositive full-score empirical normalizer')
    numerator = float(residual.sum())
    estimate = float(residual.mean()/effective)
    return dict(statistic=numerator/np.sqrt(len(y)*effective),
                raw_statistic=float(scores[:, 0].sum()/np.sqrt(len(y)*raw)),
                r_hat=dict(unconstrained=estimate, one_sided=max(0., estimate), local_only=True),
                raw_second_moment=raw, effective_second_moment=effective, beta=beta,
                nuisance_gram=qualification, score_mean=scores.mean(axis=0),
                numerator=numerator, raw_numerator=float(scores[:, 0].sum()), gram=gram,
                score_sum=scores.sum(axis=0), denominator=float(np.sqrt(len(y)*effective)),
                raw_denominator=float(np.sqrt(len(y)*raw)),
                tangent_metadata=result['tangent_metadata'],
                normalizer_scope='same-group OPG Schur residual, not exact Fisher')


def test_m14(y, fit, config=None, family=None):
    evaluation_started = time.perf_counter()
    y, config = observations(y), settings(config)
    if not fit['success']:
        raise ValueError('moment tests require a successful moment null fit')
    family = cached_family() if family is None else family
    model = family.moments(fit['theta'], covariance=True)
    weight, qualification = psd_inverse(model['covariance'], config['rcond'])
    residual = power_features(y, family.exponents).mean(axis=0)-model['mean']
    result = dict(j_statistic=float(len(y)*residual@weight@residual),
                  covariance=qualification, covariance_matrix=model['covariance'],
                  model_mean=model['mean'], observed_mean_residual=residual,
                  theta=fit['theta'], tangent_failure=None)
    result['j_evaluation_seconds'] = time.perf_counter()-evaluation_started
    try:
        tangent_model = family.moments(fit['theta'], tangent=True, branch_tolerance=config['branch_tolerance'])
    except TangentUnavailable as error:
        result.update(statistic=None, raw_statistic=None, r_hat=None, tangent_failure=str(error))
        return result
    derivatives = tangent_model['derivatives']
    gram = derivatives.T@weight@derivatives
    inverse, nuisance_qualification = psd_inverse(gram[1:, 1:], config['rcond'])
    beta = inverse@gram[1:, 0]
    witness = weight@(derivatives[:, 0]-derivatives[:, 1:]@beta)
    raw_witness = weight@derivatives[:, 0]
    variance = float(witness@model['covariance']@witness)
    raw_variance = float(raw_witness@model['covariance']@raw_witness)
    if min(variance, raw_variance) <= 0:
        raise ValueError('nonpositive moment score normalizer')
    value, raw_value = float(witness@residual), float(raw_witness@residual)
    target = float(witness@derivatives[:, 0])
    if target <= 0:
        raise ValueError('nonpositive moment target derivative')
    estimate = value/target
    result.update(statistic=np.sqrt(len(y))*value/np.sqrt(variance),
                  raw_statistic=np.sqrt(len(y))*raw_value/np.sqrt(raw_variance),
                  r_hat=dict(unconstrained=estimate, one_sided=max(0., estimate), local_only=True),
                  witness=witness, raw_witness=raw_witness, beta=beta, gram=gram,
                  derivative_matrix=derivatives, numerator=float(len(y)*value),
                  raw_numerator=float(len(y)*raw_value),
                  denominator=float(np.sqrt(len(y)*variance)),
                  raw_denominator=float(np.sqrt(len(y)*raw_variance)),
                  witness_target=target, witness_nuisance=witness@derivatives[:, 1:],
                  witness_variance=variance, raw_variance=raw_variance,
                  nuisance_gram=nuisance_qualification, tangent_metadata=tangent_model['tangent_metadata'])
    return result


def second_moment_test(y, rcond=1e-10):
    y = observations(y)
    powers = abs(y)**2
    contrasts = powers[:, [0, 2]]-powers[:, [1, 3]]
    mean = contrasts.mean(axis=0)
    centered = contrasts-mean
    covariance = centered.T@centered/len(y)
    inverse, qualification = psd_inverse(covariance, rcond)
    return dict(statistic=float(len(y)*mean@inverse@mean),
                fitted_variance_pairs=[float(powers[:, :2].mean()), float(powers[:, 2:].mean())],
                nuisance_identifiable=False, identifiable_variance_combinations=2,
                contrasts=['power0-power1', 'power2-power3'], mean=mean, covariance=covariance,
                covariance_qualification=qualification,
                scope='second-moment pair-symmetry omnibus, not an identifiable collision score')


def evaluate_methods(y, config=None):
    """Return JSON-compatible methods, fits, failures and complete method costs.

    Invalid observed/config/mathematical inputs raise clearly. Expected optimizer
    nonconvergence and unavailable final tangent retain explicit null statistics.
    No actual nuisance, PDP, gain or alternative separation input is accepted.
    """
    started = time.perf_counter()
    y, config = observations(y), settings(config)
    setup_started = time.perf_counter()
    cache_hit = cached_family.cache_info().currsize > 0
    family = cached_family()
    setup_seconds = time.perf_counter()-setup_started
    failures, diagnostics = [], {}
    statistics = dict(full_score=None, full_raw=None, moment_score=None, moment_raw=None, moment_j=None, second_moment=None)
    estimates = dict(full_score=None, moment_score=None)
    before = time.perf_counter()
    mle = fit_null_mle(y, config, family)
    if mle['success']:
        try:
            full = test_full_score(y, mle, config, family)
        except TangentUnavailable as error:
            failures.append(dict(method='full_score', kind='tangent_unavailable', reason=str(error)))
        else:
            diagnostics['full_score'] = full
            statistics.update(full_score=full['statistic'], full_raw=full['raw_statistic'])
            estimates['full_score'] = full['r_hat']
    else:
        failures.append(dict(method='full_score', kind='optimizer_failed', reason='selected null MLE start did not meet frozen convergence criteria'))
    full_seconds = time.perf_counter()-before
    before = time.perf_counter()
    m14 = fit_null_m14(y, config, family)
    moment_fit_seconds = time.perf_counter()-before
    moment_j_seconds = moment_fit_seconds
    if m14['success']:
        moment = test_m14(y, m14, config, family)
        diagnostics['moment'] = moment
        moment_j_seconds += moment['j_evaluation_seconds']
        statistics.update(moment_score=moment['statistic'], moment_raw=moment['raw_statistic'], moment_j=moment['j_statistic'])
        estimates['moment_score'] = moment['r_hat']
        if moment['tangent_failure']:
            failures.append(dict(method='moment_score', kind='tangent_unavailable', reason=moment['tangent_failure']))
    else:
        failures.append(dict(method='moment_score', kind='optimizer_failed', reason='selected moment fit did not meet frozen convergence criteria'))
    moment_seconds = time.perf_counter()-before
    before = time.perf_counter()
    second = second_moment_test(y, config['rcond'])
    statistics['second_moment'] = second['statistic']
    diagnostics['second_moment'] = second
    second_seconds = time.perf_counter()-before
    result = dict(statistics=statistics, r_hat=estimates, fits=dict(mle=mle, m14=m14),
                  diagnostics=diagnostics, failures=failures, observations=len(y),
                  costs=dict(setup_seconds=setup_seconds, setup_cache_hit=cache_hit,
                      setup_original_construction_seconds=family.creation_seconds,
                      full_score_complete_seconds=setup_seconds+full_seconds,
                      full_raw_complete_seconds=setup_seconds+full_seconds,
                      moment_score_complete_seconds=setup_seconds+moment_seconds,
                      moment_raw_complete_seconds=setup_seconds+moment_seconds,
                      moment_j_complete_seconds=setup_seconds+moment_j_seconds,
                      second_moment_complete_seconds=second_seconds,
                      per_method_seconds=dict(full_score=full_seconds, full_raw=full_seconds,
                          moment_score=moment_seconds, moment_raw=moment_seconds, moment_j=moment_j_seconds,
                          second_moment=second_seconds),
                      per_method_setup_included=False,
                      joint_complete_seconds=time.perf_counter()-started,
                      sharing='full/raw share one MLE; moment/raw/J share one GMM; listed standalone costs must not be summed',
                      setup_scope='first exact QPSK/polynomial construction included on cache miss; later calls explicitly cached'))
    conversion_started = time.perf_counter()
    result = plain(result)
    result['costs']['shared_result_conversion_seconds'] = time.perf_counter()-conversion_started
    result['costs']['joint_complete_seconds'] = time.perf_counter()-started
    return result
