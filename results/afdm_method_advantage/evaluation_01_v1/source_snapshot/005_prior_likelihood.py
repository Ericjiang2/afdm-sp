"""Finite-QPSK likelihood under the actual, G0-normalized two-path prior.

The marginal PDP is the frozen delay-increment law conditional on two rounded
zero delays and an unordered positive Doppler pair. Global phase is integrated
analytically; positive CP1 quadrature is a numerical likelihood reference.
"""
from itertools import product
from functools import lru_cache

import numpy as np
from scipy.special import i0e, i1e, logsumexp, roots_legendre
from scipy.stats import qmc
from experiments.sp_afdm_frozen_20260920.src.physical import daft as frozen_daft

from experiments.afdm_higher_order_information.prior import (
    geometry, small_system, pushforward_jvp, singular_moment_status,
)
from experiments.afdm_shared_channel_20261004.production_prior import normalize_gain

PARAMETERS = ('delta', 'mu', 'log_tau', 'log_sigma2')


def system_for(n):
    if not isinstance(n, int) or n < 4:
        raise ValueError('integer N>=4 required')
    system = small_system(n)
    system.k_max_cap = min(2, (n-1)//2)
    return system


def daft(n):
    return frozen_daft(np.eye(n), 2.5/n, .1/n**2)


@lru_cache(maxsize=16)
def qpsk_time(n):
    if n > 6:
        raise ValueError('full QPSK orbit enumeration restricted to N<=6')
    # One representative per global QPSK phase orbit; the gain phase is uniform.
    states = np.column_stack((np.zeros(4**(n-1), int),
                             np.array(list(product(range(4), repeat=n-1)))))
    symbols = np.exp(1j*(np.pi/4+np.pi/2*states))
    return symbols @ daft(n).conj()


def pdp_distribution(n, mu, delta, *, fs=8000., fc=12000., delta_f=15.,
                     tau_mean=.0008, tau_spread=.01, attenuation_db=20.):
    """Exact finite PDP mixture in the declared actual common-zero-delay slice.

    J_i=ceil(Exp(tau_mean)/Ts) are geometric, indexed from 1. On label
    assignment a, J1<=L1 and J1+J2<=L2; sum J1 analytically. Includes both
    assignments BEFORE conditioning. Returned PDP is in ascending Doppler order.
    """
    nu = np.array([mu-delta, mu+delta])
    if n < 4 or np.any(nu < 0) or not np.isfinite(nu).all():
        raise ValueError('actual unordered-Doppler marginal requires nonnegative pair')
    ts, resolution = 1/fs, 1/(n*delta_f)
    # Same rounding as frozen np.round((delay_idx_bar-1)*Ts/resolution).
    k = np.arange(1, int(np.ceil(resolution/ts))+3)
    zero = k[np.round((k-1)*ts/resolution).astype(int) == 0]
    max_index = int(zero[-1])
    limits = np.floor(max_index*(1+nu*fs/(fc*n))).astype(int)
    survival = np.exp(-ts/tau_mean)
    beta = np.log(10)*attenuation_db/10/tau_spread*ts
    powers, masses, increments, assignments = [], [], [], []
    for assignment in (0, 1):
        l1, l2 = limits if assignment == 0 else limits[::-1]
        for j2 in range(1, int(l2)):
            maximum_j1 = min(int(l1), int(l2)-j2)
            if maximum_j1 < 1:
                continue
            mass = .5*(1-survival)*survival**(j2-1)*(1-survival**maximum_j1)
            pair = [1., np.exp(-beta*j2)]
            powers.append(pair if assignment == 0 else pair[::-1])
            masses.append(mass)
            increments.append(j2)
            assignments.append(assignment)
    mass = np.asarray(masses)
    if not len(mass) or mass.sum() <= 0:
        raise ValueError('common-zero-delay conditioning event has zero probability')
    return dict(pdp=np.asarray(powers), weights=mass/mass.sum(),
                event_probability=float(mass.sum()), limits=limits,
                max_corrected_index=max_index, increments=np.asarray(increments),
                assignments=np.asarray(assignments), raw_masses=mass)


def cp1_nodes(order=12, phases=24, *, rule='product', seed=731):
    if order < 2 or phases < 4:
        raise ValueError('positive rule requires order>=2 and phases>=4')
    if rule == 'product':
        t, w = roots_legendre(order)
        t, w = (t+1)/2, w/2
        u = np.repeat(t, phases)
        phi = np.tile(2*np.pi*(np.arange(phases)+.5)/phases, order)
        weights = np.repeat(w/phases, phases)
    elif rule == 'sobol':
        count = order*phases
        if count & (count-1):
            raise ValueError('Sobol node count must be a power of two')
        points = qmc.Sobol(2, scramble=True, seed=seed).random_base2(count.bit_length()-1)
        u, phi = points[:, 0], 2*np.pi*points[:, 1]
        weights = np.full(count, 1/count)
    else:
        raise ValueError('unknown positive node rule')
    return np.column_stack((np.sqrt(u), np.sqrt(1-u)*np.exp(1j*phi))), weights


def angular_density(nodes, pdp, probabilities):
    """ACG density on CP1; exact positive sum over the latent PDP mixture."""
    t = abs(nodes[:, 0])**2
    d1, d2 = np.asarray(pdp).T
    return ((d1*d2)[None, :]
            / (t[:, None]*d2+(1-t[:, None])*d1)**2) @ probabilities


def project_information(scores, train=None, rtol=1e-10):
    """Same-sample information and an optional independent nuisance projection."""
    scores = np.asarray(scores, float)
    fit = scores if train is None else np.asarray(train, float)
    if scores.ndim != 2 or scores.shape[1] != 4 or not np.isfinite(scores).all():
        raise ValueError('four finite score columns required')
    a = fit[:, 1:]
    coefficient, _, rank, singular = np.linalg.lstsq(a, fit[:, 0], rcond=rtol)
    efficient = scores[:, 0]-scores[:, 1:]@coefficient
    batches = np.array_split(efficient**2, min(8, len(scores)))
    se = np.std([x.mean() for x in batches], ddof=1)/np.sqrt(len(batches)) if len(batches)>1 else 0.
    return dict(raw=float(np.mean(scores[:, 0]**2)), effective=float(np.mean(efficient**2)),
                effective_batch_se=float(se), coefficient=coefficient,
                nuisance_rank=int(rank), nuisance_singular_values=singular,
                score_mean=scores.mean(axis=0), efficient_score=efficient)


class ActualPrior:
    """Actual conditional/PDP-marginal G0 or G1 reference; theta uses log scales.

    sample uses the exact latent mixture and continuous sphere, independently of
    quadrature. logpdf/evaluate enumerate all legal QPSK orbits at N<=6. No true
    nuisance or PDP is an input to data features; theta is a public model point.
    """
    def __init__(self, n=4, model='g0', pdp='marginal', order=12, phases=24,
                 rule='product', seed=731):
        if model not in ('g0', 'g1'):
            raise ValueError('model must be g0 or g1')
        self.n, self.model, self.pdp = n, model, pdp
        self.system = system_for(n)
        self.nodes, self.weights = cp1_nodes(order, phases, rule=rule, seed=seed)
        self.order, self.phases, self.rule = order, phases, rule
        self._cache = {}
        self.cost = dict(response_evaluations=0, logpdf_observations=0,
                         component_observation_pairs=0, tracked_branch_eigvalsh=0)

    def _validate(self, theta):
        theta = np.asarray(theta, float)
        if theta.shape != (4,) or not np.isfinite(theta).all() or theta[0] < 0:
            raise ValueError('theta=(nonnegative delta,mu,log_tau,log_sigma2) required')
        if abs(theta[2]) > 30 or abs(theta[3]) > 30:
            raise ValueError('unsupported scale')
        return theta

    def _pdp(self, theta):
        if isinstance(self.pdp, str):
            if self.pdp == 'marginal':
                return pdp_distribution(self.n, theta[1], theta[0])
            if self.pdp == 'equal':
                return dict(pdp=np.ones((1, 2)), weights=np.ones(1), limits=np.array([]))
            raise ValueError('unknown PDP law')
        pdp = np.asarray(self.pdp, float)
        if pdp.shape != (2,) or np.any(pdp <= 0) or not np.isfinite(pdp).all():
            raise ValueError('two positive conditional PDP powers required')
        return dict(pdp=pdp[None, :], weights=np.ones(1), limits=np.array([]))

    def branch(self, theta):
        theta = self._validate(theta)
        geo = geometry(self.system, theta[1], theta[0])
        active = np.flatnonzero(np.any(geo['weights'] != 0, axis=1))
        if isinstance(self.pdp, str) and self.pdp == 'marginal' and np.any(geo['physical_clip_mask']):
            raise ValueError('actual marginal conditions on unclipped Doppler; cap atoms require another law')
        pdp = self._pdp(theta)
        eigenvalues = np.linalg.eigvalsh(geo['gram'])
        self.cost['tracked_branch_eigvalsh'] += 1
        platform = len(active) == 1 and np.all(geo['weights'][active[0]] != 0)
        return dict(geometry=geo, active=active, pdp=pdp, eigenvalues=eigenvalues,
                    platform=platform, signature=(tuple((geo['weights'] != 0).ravel()),
                    tuple(geo['physical_clip_mask']), tuple(pdp['limits']),
                    tuple(np.round(geo['dopplers']).astype(int))),
                    moments=singular_moment_status(geo['gram'], geo[self.model]))

    def _components(self, theta, step=None):
        theta = self._validate(theta)
        key = (tuple(theta), step)
        if key in self._cache:
            return self._cache[key]
        branch = self.branch(theta)
        geo, latent = branch['geometry'], branch['pdp']
        is_platform = self.model == 'g0' and branch['platform']
        states = qpsk_time(self.n)
        tau = np.exp(theta[2])
        if is_platform:
            # Exact pushforward, not an artificial replacement of singular gains.
            atom = int(branch['active'][0]) % (2*self.system.k_max_cap+1)-self.system.k_max_cap
            v = np.exp(2j*np.pi*atom*np.arange(self.n)/self.n)[None, :]
            weights = np.ones(1)
            normalization_error = 0.
        else:
            gains = normalize_gain(self.nodes, geo['gram'])
            v = gains@geo[self.model].T
            weights = self.weights*angular_density(self.nodes, latent['pdp'], latent['weights'])
            normalization_error = abs(float(weights.sum())-1)
            weights = weights/weights.sum()
        means = (np.sqrt(tau)*v[:, None, :]*states[None, :, :]).reshape(-1, self.n)
        logweights = np.log(np.repeat(weights/len(states), len(states)))
        derivatives = None
        if step is not None:
            if step <= 0:
                raise ValueError('positive derivative step required')
            derivatives = np.zeros((3, len(means), self.n), complex)
            if not is_platform:
                if branch['eigenvalues'][0] <= 1e-12:
                    raise ValueError('regular score not certified on singular non-platform branch')
                for axis in (0, 1):
                    if axis == 0 and theta[0] <= step:
                        raise ValueError('collision q/delta regularity requires separate analysis')
                    plus, minus = theta.copy(), theta.copy()
                    plus[axis] += step; minus[axis] -= step
                    bp, bm = self.branch(plus), self.branch(minus)
                    if bp['signature'] != branch['signature'] or bm['signature'] != branch['signature']:
                        raise ValueError('derivative stencil crosses frozen support/PDP branch')
                    dg = (bp['geometry']['gram']-bm['geometry']['gram'])/(2*step)
                    db = (bp['geometry'][self.model]-bm['geometry'][self.model])/(2*step)
                    _, dv = pushforward_jvp(self.nodes, np.ones(2), geo['gram'],
                                           geo[self.model], np.zeros(2), dg, db)
                    derivatives[axis] = (np.sqrt(tau)*dv[:, None, :]*states).reshape(-1, self.n)
            else:
                for axis in (0, 1):
                    for sign in (-1, 1):
                        test = theta.copy(); test[axis] += sign*step
                        if test[0] < 0:
                            continue
                        other = self.branch(test)
                        if other['signature'] != branch['signature']:
                            raise ValueError('platform stencil crosses a support/PDP boundary')
            derivatives[2] = means/2
        self.cost['response_evaluations'] += len(means)
        result = dict(means=means, logweights=logweights, derivatives=derivatives,
                      quadrature_mass_error=normalization_error, branch=branch)
        self._cache[key] = result
        return result

    def _integrate(self, y, theta, step=None, batch=16):
        theta = self._validate(theta)
        y = np.asarray(y, complex)
        if y.ndim == 1:
            y = y[None, :]
        if y.ndim != 2 or y.shape[1] != self.n or not np.isfinite(y).all():
            raise ValueError('finite observation rows of length N required')
        components = self._components(theta, step)
        m, lw, dm = (components[k] for k in ('means', 'logweights', 'derivatives'))
        sigma = np.exp(theta[3]); power = np.sum(abs(m)**2, axis=1)
        logpdf, scores = [], []
        for start in range(0, len(y), batch):
            yy = y[start:start+batch]
            yp = np.sum(abs(yy)**2, axis=1)
            c = yy.conj()@m.T
            radius = abs(c); kappa = 2*radius/sigma
            bessel = i0e(kappa)
            logs = (lw[None, :]-(yp[:, None]+power)/sigma
                    + np.log(bessel)+kappa-self.n*np.log(np.pi*sigma))
            normalizer = logsumexp(logs, axis=1)
            logpdf.append(normalizer)
            if dm is not None:
                posterior = np.exp(logs-normalizer[:, None])
                ratio = i1e(kappa)/bessel
                unit = np.divide(c.conj(), radius, out=np.zeros_like(c), where=radius>0)
                columns = []
                for d in dm:
                    dc = yy.conj()@d.T
                    radial_dot = np.real(unit*dc)
                    conditional = (-2*np.real(np.sum(m.conj()*d, axis=1))[None, :]
                                   + 2*ratio*radial_dot)/sigma
                    columns.append(np.sum(posterior*conditional, axis=1))
                noise_score = -self.n+(yp[:, None]+power)/sigma-ratio*kappa
                columns.append(np.sum(posterior*noise_score, axis=1))
                scores.append(np.column_stack(columns))
        self.cost['logpdf_observations'] += len(y)
        self.cost['component_observation_pairs'] += len(y)*len(m)
        result = dict(logpdf=np.concatenate(logpdf),
                      quadrature_mass_error=components['quadrature_mass_error'])
        if scores:
            result['score'] = np.concatenate(scores)
        return result

    def logpdf(self, y, theta):
        return self._integrate(y, theta)['logpdf']

    def evaluate(self, y, theta, step=1e-4):
        return self._integrate(y, theta, step)

    def sample(self, theta, count, seed):
        """Exact continuous latent sampling; never samples the likelihood nodes."""
        theta = self._validate(theta)
        if not isinstance(count, int) or count <= 0:
            raise ValueError('positive integer observation count required')
        branch = self.branch(theta)
        rng = np.random.default_rng(seed)
        latent = branch['pdp']
        idx = rng.choice(len(latent['weights']), count, p=latent['weights'])
        z = (rng.standard_normal((count, 2))+1j*rng.standard_normal((count, 2)))/np.sqrt(2)
        h = normalize_gain(z*np.sqrt(latent['pdp'][idx]), branch['geometry']['gram'])
        v = h@branch['geometry'][self.model].T
        symbols = np.exp(1j*(np.pi/4+np.pi/2*rng.integers(0, 4, (count, self.n))))
        s = symbols@daft(self.n).conj()
        noise = (rng.standard_normal((count, self.n))+1j*rng.standard_normal((count, self.n)))/np.sqrt(2)
        return np.exp(theta[2]/2)*v*s+np.exp(theta[3]/2)*noise


def normalized_signal_covariance(response, gram, pdp):
    """Analytic P=2 Gaussian radial cancellation, including rank-one support.

    This is the actual normalized prior covariance, not a Gaussian likelihood.
    Independent Exp(1) squared eigen-coordinates permit exact 1-D elimination.
    """
    pdp = np.asarray(pdp, float)
    root = np.sqrt(pdp)
    covariance = root[:, None]*gram*root[None, :]
    values, vectors = np.linalg.eigh(covariance)
    if values[-1] <= 0 or values[0] < -1e-12*values[-1]:
        raise ValueError('invalid normalization covariance')
    if values[0] <= 1e-14*values[-1]:
        # Declared numerical rank decision; no eigenvalue is moved or jittered.
        v = response@(root*vectors[:, -1])/np.sqrt(values[-1])
        return np.outer(v, v.conj())
    ratio = values[0]/values[1]
    if abs(1-ratio) < 1e-4:
        e = ratio-1
        small = .5+e/6-e*e/12+e**3/20
    else:
        small = ratio*(ratio-1-np.log(ratio))/(1-ratio)**2
    basis = (response*root[None, :])@vectors/np.sqrt(values)[None, :]
    return (basis*np.array([small, 1-small]))@basis.conj().T


def actual_signal_covariance(model, theta):
    branch = model.branch(theta)
    result = np.zeros((model.n, model.n), complex)
    for pdp, weight in zip(branch['pdp']['pdp'], branch['pdp']['weights']):
        result += weight*normalized_signal_covariance(branch['geometry'][model.model],
                                                     branch['geometry']['gram'], pdp)
    return np.exp(theta[2])*result


def collision_qlogq_coefficient(model, mu, step=1e-5):
    """Leading G0 signal-power coefficient on a fixed collision support branch.

    For symmetric label law, M(delta)-M(0)=K delta² log(1/delta²)+O(delta²).
    For unequal conditional PDP this describes the even part; odd terms remain.
    """
    if model.model != 'g0':
        raise ValueError('bounded G0 collision coefficient only')
    theta = np.array([0., mu, 0., 0.])
    branch = model.branch(theta)
    plus = model.branch([0., mu+step, 0., 0.])
    minus = model.branch([0., mu-step, 0., 0.])
    if plus['signature'] != branch['signature'] or minus['signature'] != branch['signature']:
        raise ValueError('collision coefficient crosses an active-support/PDP boundary')
    w = branch['geometry']['g0'][:, 0]
    derivative = (plus['geometry']['g0'][:, 0]-minus['geometry']['g0'][:, 0])/(2*step)
    b = derivative-w*np.vdot(w, derivative)/np.vdot(w, w)
    a2, b2 = np.vdot(w, w).real/model.n, np.vdot(b, b).real/model.n
    if b2 <= 1e-24:
        return np.zeros(model.n)
    pdp = branch['pdp']['pdp']
    factor = branch['pdp']['weights']@(4*pdp[:, 0]*pdp[:, 1]/pdp.sum(axis=1)**2)
    return factor*b2/a2*(abs(b)**2/b2-abs(w)**2/a2)
