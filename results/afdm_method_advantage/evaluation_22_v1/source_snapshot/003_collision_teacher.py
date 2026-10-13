"""Observed-only collision log-tangent for the actual normalized G0 P=2 slice.

Finite QPSK enumeration and analytic global-phase elimination.  Geometry uses
exact finite Fourier derivatives on a checked frozen physical support branch.
No latent true gain/PDP or true nuisance is accepted by ``evaluate``.
"""
from itertools import combinations_with_replacement, product
from math import comb, factorial

import numpy as np
from scipy.special import i0e, i1e, logsumexp

from experiments.afdm_efficient_information.prior_likelihood import (
    daft, pdp_distribution, qpsk_time, system_for,
)
from experiments.afdm_higher_order_information.prior import geometry
from experiments.afdm_shared_channel_20261004.production_prior import normalize_gain

SCORE_COLUMNS = ('r=q log(1/q)', 'mu', 'log_tau', 'log_sigma2')
STEPS = (1e-4, 5e-5, 2.5e-5)


def signature(system, mu, delta=0.):
    geo = geometry(system, mu, delta)
    pdp = pdp_distribution(system.N_total, mu, delta)
    return (tuple((geo['weights'] != 0).ravel()),
            tuple(geo['physical_clip_mask']), tuple(pdp['limits']),
            tuple(np.round(geo['dopplers']).astype(int)))


def collision_geometry(mu, n=4):
    """Analytic derivative of the *frozen* normalized/pruned Dirichlet vector."""
    if n != 4 or not np.isfinite(mu) or not 0 < mu < 1:
        raise ValueError('declared N=4 positive unclipped collision slice required')
    system = system_for(n)
    geo = geometry(system, mu, 0.)
    sig = signature(system, mu)
    for step in STEPS:
        for sign in (-1, 1):
            if signature(system, mu+sign*step) != sig:
                raise ValueError('mu stencil crosses physical support/PDP branch')
            if signature(system, mu, step) != sig:
                raise ValueError('collision stencil crosses physical support/PDP branch')
    offsets = np.arange(-system.k_leak, system.k_leak+1)
    center = int(np.round(mu))
    frequency = 2j*np.pi*np.arange(n)/n
    fourier = np.exp((offsets[:, None]+mu-center)*frequency)
    alpha, derivative = fourier.mean(axis=1), (fourier*frequency).mean(axis=1)
    norm = np.sqrt(np.sum(abs(alpha)**2)+1e-300)
    alpha_dot = derivative/norm-alpha*np.real(np.vdot(alpha, derivative))/norm**3
    alpha /= norm
    weight_dot = np.zeros(2*system.k_max_cap+1, complex)
    reproduced = np.zeros_like(weight_dot)
    # The exact existing physical mask is authoritative; derivatives never
    # differentiate a discontinuous threshold or silently smooth it.
    for offset, value, dot in zip(offsets, alpha, alpha_dot):
        k = center+int(offset)
        if -system.k_max_cap <= k <= system.k_max_cap:
            index = k+system.k_max_cap
            if geo['weights'][index, 0] != 0:
                reproduced[index], weight_dot[index] = value, dot
    if not np.allclose(reproduced, geo['weights'][:len(reproduced), 0], atol=3e-14, rtol=3e-14):
        raise ValueError('finite Fourier derivative does not reproduce frozen weights')
    atoms = np.exp(2j*np.pi*np.outer(np.arange(n), np.arange(-system.k_max_cap, system.k_max_cap+1))/n)
    w, w_dot = geo['g0'][:, 0], atoms@weight_dot
    w2 = float(np.vdot(w, w).real)
    b = w_dot-w*np.vdot(w, w_dot)/w2
    b2 = float(np.vdot(b, b).real)
    if b2 <= 1e-20 or np.count_nonzero(reproduced) < 2:
        raise ValueError('platform/degenerate tangent is not admitted by this teacher')
    u0, u1 = w/np.sqrt(w2), b/np.sqrt(b2)
    u0_dot = (w_dot-w*np.real(np.vdot(w, w_dot))/w2)/np.sqrt(w2)
    pdp = pdp_distribution(n, mu, 0.)
    if len(set(pdp['limits'])) != 1:
        raise ValueError('symmetric collision PDP branch required')
    powers = pdp['pdp']
    factor = pdp['weights']@(4*powers[:, 0]*powers[:, 1]/powers.sum(axis=1)**2)
    fd = []
    for step in STEPS:
        wp = geometry(system, mu+step, 0.)['g0'][:, 0]
        wm = geometry(system, mu-step, 0.)['g0'][:, 0]
        fd.append(dict(step=step, w_dot_max=float(np.max(abs((wp-wm)/(2*step)-w_dot))),
                       u0_dot_max=float(np.max(abs((wp/np.linalg.norm(wp)-wm/np.linalg.norm(wm))/(2*step)-u0_dot)))))
    return dict(w=w, w_dot=w_dot, b=b, u0=u0, u1=u1, u0_dot=u0_dot,
                kappa=float(factor*b2/w2), pdp=pdp, geometry=geo,
                signature=sig, finite_difference=fd)


class CollisionTeacher:
    """A fixed PUBLIC base point; evaluate accepts observation rows only."""
    def __init__(self, mu, tau=1., sigma2=.2, n=4):
        if not np.isfinite([tau, sigma2]).all() or min(tau, sigma2) <= 0:
            raise ValueError('finite positive signal/noise scales required')
        self.mu, self.tau, self.sigma2, self.n = float(mu), float(tau), float(sigma2), n
        self.geo = collision_geometry(mu, n)
        self.states = qpsk_time(n)
        scale = np.sqrt(tau*n)
        self.m0 = scale*self.states*self.geo['u0']
        self.m1 = scale*self.states*self.geo['u1']
        self.m_mu = scale*self.states*self.geo['u0_dot']
        self.kappa = self.geo['kappa']

    def evaluate(self, y, batch=64):
        y = np.asarray(y, complex)
        if y.ndim == 1:
            y = y[None, :]
        if y.ndim != 2 or y.shape[1] != self.n or not len(y) or not np.isfinite(y).all():
            raise ValueError('nonempty finite observed rows with N=4 required')
        if not isinstance(batch, int) or batch <= 0:
            raise ValueError('positive integer batch required')
        m0, m1, s = self.m0, self.m1, self.sigma2
        a = np.sum(abs(m0)**2, axis=1)
        b = np.sum(abs(m1)**2, axis=1)
        e = np.sum(m0.conj()*m1, axis=1)
        result_pdf, result_score = [], []
        for start in range(0, len(y), batch):
            yy = y[start:start+batch]
            yp = np.sum(abs(yy)**2, axis=1)
            c, d = yy.conj()@m0.T, yy.conj()@m1.T
            radius = abs(c)
            z = 2*radius/s
            ratio = i1e(z)/i0e(z)
            unit = np.divide(c.conj(), radius, out=np.zeros_like(c), where=radius>0)
            logs = (-(yp[:, None]+a)/s+np.log(i0e(z))+z
                    -self.n*np.log(np.pi*s)-np.log(len(m0)))
            logpdf = logsumexp(logs, axis=1)
            posterior = np.exp(logs-logpdf[:, None])
            tangent = ((abs(d)**2+abs(e)**2-2*ratio*np.real(d*e.conj()*unit))/s**2
                       -b/s-(ratio*radius-a)/s)
            mu_component = (-2*np.real(np.sum(m0.conj()*self.m_mu, axis=1))
                            +2*ratio*np.real(unit*(yy.conj()@self.m_mu.T)))/s
            tau_component = (-a+ratio*radius)/s
            noise_component = -self.n+(yp[:, None]+a)/s-ratio*z
            scores = np.column_stack([np.sum(posterior*t, axis=1) for t in
                                      (self.kappa*tangent, mu_component, tau_component, noise_component)])
            result_pdf.append(logpdf)
            result_score.append(scores)
        return dict(logpdf=np.concatenate(result_pdf), score=np.concatenate(result_score))

    def logpdf(self, y):
        return self.evaluate(y)['logpdf']

    def sample(self, count, seed):
        """Exact actual rank-one pushforward, including latent PDP and gains.

        This is not sampling quadrature points. All latent arrays are returned
        for external replay only; evaluate has no parameter accepting them.
        """
        if not isinstance(count, int) or count <= 0:
            raise ValueError('positive integer observation count required')
        rng = np.random.default_rng(seed)
        pdp = self.geo['pdp']
        label = rng.choice(len(pdp['weights']), count, p=pdp['weights'])
        z = (rng.standard_normal((count, 2))+1j*rng.standard_normal((count, 2)))/np.sqrt(2)
        h = normalize_gain(z*np.sqrt(pdp['pdp'][label]), self.geo['geometry']['gram'])
        v = h@self.geo['geometry']['g0'].T
        symbols_id = rng.integers(0, 4, (count, self.n))
        symbols = np.exp(1j*(np.pi/4+np.pi/2*symbols_id))
        time_symbols = symbols@daft(self.n).conj()
        noise = (rng.standard_normal((count, self.n))+1j*rng.standard_normal((count, self.n)))/np.sqrt(2)
        y = np.sqrt(self.tau)*v*time_symbols+np.sqrt(self.sigma2)*noise
        return dict(y=y, pdp_index=label, gaussian_gain=z, normalized_gain=h,
                    time_response=v, symbols_id=symbols_id, standard_noise=noise)

    def component_state(self):
        return dict(m0=self.m0, m1=self.m1, m_mu=self.m_mu, kappa=np.array(self.kappa),
                    w=self.geo['w'], w_dot=self.geo['w_dot'], b=self.geo['b'],
                    pdp=self.geo['pdp']['pdp'], pdp_weights=self.geo['pdp']['weights'],
                    gram=self.geo['geometry']['gram'], response=self.geo['geometry']['g0'])


def power_exponents(n=4, degree=2):
    return np.asarray([np.bincount(indices, minlength=n) for order in range(1, degree+1)
                       for indices in combinations_with_replacement(range(n), order)], int)


def power_features(y, exponents):
    return np.prod((abs(np.asarray(y))**2)[:, None, :]**np.asarray(exponents)[None, :, :], axis=2)


def monomial_and_derivatives(m, direction, tangent, exponent):
    """Wirtinger polynomial arithmetic without division, including m_i=0."""
    exponent = np.asarray(exponent, int)
    base = np.prod(m**exponent*m.conj()**exponent, axis=1)
    derivative = np.zeros(len(m), complex)
    second = np.zeros(len(m), complex)
    for i in np.flatnonzero(exponent):
        left = exponent.copy(); left[i] -= 1
        derivative += exponent[i]*direction[:, i]*np.prod(m**left*m.conj()**exponent, axis=1)
        for j in np.flatnonzero(exponent):
            right = exponent.copy(); right[j] -= 1
            second += (exponent[i]*exponent[j]*tangent[:, i]*tangent[:, j].conj()
                       *np.prod(m**left*m.conj()**right, axis=1))
    return base.real, 2*derivative.real, (second-exponent.sum()*base).real


def exact_power_moment(teacher, exponent):
    """Finite QPSK/Gaussian algebra for mean and (r,mu,logtau,logsigma2) derivatives."""
    exponent = np.asarray(exponent)
    if exponent.shape != (teacher.n,) or not np.issubdtype(exponent.dtype, np.integer) or np.any(exponent < 0):
        raise ValueError('nonnegative integer power multi-index required')
    mean, derivative = 0., np.zeros(4)
    for noise_power in product(*[range(int(k)+1) for k in exponent]):
        noise_power = np.asarray(noise_power, int)
        signal_power = exponent-noise_power
        coefficient = float(np.prod([comb(int(k), int(l))**2*factorial(int(l))
                                     for k, l in zip(exponent, noise_power)]))*teacher.sigma2**noise_power.sum()
        base, mu, tangent = monomial_and_derivatives(teacher.m0, teacher.m_mu, teacher.m1, signal_power)
        value = coefficient*base.mean()
        mean += value
        derivative += [coefficient*teacher.kappa*tangent.mean(), coefficient*mu.mean(),
                       signal_power.sum()*value, noise_power.sum()*value]
    return float(mean), derivative


def exact_moment_system(teacher, exponents=None):
    exponents = power_exponents(teacher.n) if exponents is None else np.asarray(exponents, int)
    cache = {}
    def moment(k):
        key = tuple(k)
        if key not in cache:
            cache[key] = exact_power_moment(teacher, np.asarray(k))
        return cache[key]
    means, derivatives = zip(*(moment(k) for k in exponents))
    means, derivatives = np.asarray(means), np.asarray(derivatives)
    second = np.asarray([[moment(a+b)[0] for b in exponents] for a in exponents])
    covariance = second-np.outer(means, means)
    return dict(exponents=exponents, mean=means, derivatives=derivatives, covariance=covariance,
                distinct_moments=len(cache), arithmetic='finite QPSK and exact Gaussian polynomial identities; floating evaluation')
