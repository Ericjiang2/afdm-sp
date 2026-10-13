"""Actual G0 pushforward and its regular/singular observable branches.

Frozen physical weight construction and gain normalization are reused verbatim.
No receiver, channel draw, arbitrary jitter or singular-moment truncation.
"""
import numpy as np
from scipy.special import roots_legendre
from scipy.stats import qmc

from experiments.afdm_shared_channel_20261004.production_prior import (
    frozen_components, normalization_gram, dense_gram, normalize_gain,
    pushforward_nodes,
)


def small_system(n=16):
    env, _, _ = frozen_components()
    system = env.__new__(env)
    system.__dict__.update(N_total=n, c1=2.5/n, c2=.1/n**2,
        l_max_cap=min(3, n-1), k_max_cap=2, k_guard=0, k_leak=2,
        frac_prune_rel_thres=.01, gen_h_daft_convention='python', use_frac_doppler=True)
    return system


def geometry(system, mu, delta):
    if delta < 0 or not np.isfinite([mu, delta]).all():
        raise ValueError('finite center and nonnegative separation required')
    requested = np.array([mu-delta, mu+delta])
    # afdm_env.generate_channel_matrix clips the physical Dopplers first.
    cap = min(system.k_max_cap, system.N_total//2-system.k_guard-1)
    nu = np.clip(requested, -float(cap), float(cap))
    gram, weights = normalization_gram(system, np.zeros(2, dtype=int), nu)
    k = np.arange(-system.k_max_cap, system.k_max_cap+1)
    time = 2*np.pi*np.arange(system.N_total)/system.N_total
    # Integer gen_h_daft has exp(+j k t) in the frozen Python convention.
    g0 = np.exp(1j*np.outer(time, k)) @ weights[:len(k)]
    g1 = np.exp(1j*np.outer(time, nu))
    return dict(gram=gram, weights=weights, g0=g0, g1=g1, dopplers=nu,
                requested_dopplers=requested, physical_clip_mask=requested != nu)


def sphere_rule(order, phase_count=None):
    """Positive CP1 product rule; global phase is integrated analytically.

    t=|z1|² is uniform [0,1], relative phase is uniform [0,2π).
    Power moments are global-phase invariant. Not a likelihood node rule.
    """
    phase_count = 2*order if phase_count is None else phase_count
    if order < 2 or phase_count < 4:
        raise ValueError('positive rule requires order>=2 and phases>=4')
    t, wt = roots_legendre(order)
    t, wt = (t+1)/2, wt/2
    phases = np.exp(2j*np.pi*(np.arange(phase_count)+.5)/phase_count)
    z = np.column_stack((np.repeat(np.sqrt(t), phase_count),
                        (np.sqrt(1-t)[:, None]*phases).ravel()))
    return z, np.repeat(wt/phase_count, phase_count)


def sphere_sobol(exponent, seed):
    u = qmc.Sobol(2, scramble=True, seed=seed).random_base2(exponent)
    z = np.column_stack((np.sqrt(u[:, 0]), np.sqrt(1-u[:, 0])*np.exp(2j*np.pi*u[:, 1])))
    return z, np.full(len(z), 1/len(z))


def power_moments(gains, weights, response, noise=.2, a=3, b=7):
    """Exact QPSK/noise elimination conditional on quadrature gains.

    QPSK has unit symbol power and an equal-modulus N-point unitary DAFT.
    Returned second is E|r_n|², cross is E|r0|²|rn|² for n=a,b.
    """
    n = len(response)
    if not 0 < a < n or not 0 < b < n or a == b or noise < 0:
        raise ValueError('distinct nonzero lags and nonnegative noise required')
    y = gains @ np.asarray(response).T
    p = abs(y)**2
    second = weights@p
    cross_signal = weights@(p[:, :1]*p[:, [a, b]])
    cross = (1-1/n)*cross_signal + noise*(second[0]+second[[a, b]]) + noise**2
    return dict(second=second+noise, cross=cross, T=float(cross[0]-cross[1]),
                signal_second=second, signal_cross=cross_signal)


def mapped_moments(z, weights, pdp, gram, response, model, **kwargs):
    if model == 'actual':
        gains, _ = pushforward_nodes(z, weights, pdp, gram)
        return power_moments(gains, weights, response, **kwargs)
    if model == 'fixed_energy':
        gains = normalize_gain(z*np.sqrt(pdp), np.eye(2))
        return power_moments(gains, weights, response, **kwargs)
    if model == 'gaussian':
        # For P=2 equal PDP Gaussian CN(0,I/2), radius E R²=1,
        # E R⁴=3/2. The same angular nodes make a paired exact radial control.
        if not np.allclose(pdp, pdp[0]):
            raise ValueError('Gaussian radial control is restricted to equal PDP')
        result = power_moments(z, weights, response, **kwargs)
        noise = kwargs.get('noise', .2); n = len(response)
        a, b = kwargs.get('a', 3), kwargs.get('b', 7)
        result['signal_cross'] *= 1.5
        result['cross'] = ((1-1/n)*result['signal_cross']
            + noise*(result['signal_second'][0]+result['signal_second'][[a,b]])+noise**2)
        result['T'] = float(np.diff(result['cross'])[0]*-1)
        return result
    raise ValueError('unknown prior model')


def pushforward_jvp(z, pdp, gram, response, pdp_dot, gram_dot, response_dot):
    """Complete fixed-base derivative on positive-definite smooth branches."""
    pdp, pdp_dot = np.asarray(pdp), np.asarray(pdp_dot)
    if np.any(pdp <= 0) or np.linalg.eigvalsh(gram).min() <= 0:
        raise ValueError('JVP requires positive PDP and positive-definite Gram')
    u = np.asarray(z)*np.sqrt(pdp)
    du = np.asarray(z)*(.5*pdp_dot/np.sqrt(pdp))
    energy = np.einsum('bi,ij,bj->b', u.conj(), gram, u).real
    de = (2*np.einsum('bi,ij,bj->b', du.conj(), gram, u).real
          + np.einsum('bi,ij,bj->b', u.conj(), gram_dot, u).real)
    h = u/np.sqrt(energy)[:,None]
    dh = du/np.sqrt(energy)[:,None]-.5*h*(de/energy)[:,None]
    return h@response.T, dh@response.T+h@response_dot.T


def singular_moment_status(gram, response, tolerance=1e-12):
    """Numerical support diagnostic; exact plateau proof is separate in PRIOR.md."""
    eigenvalues, vectors = np.linalg.eigh(gram)
    if eigenvalues.min() < -tolerance:
        raise ValueError('indefinite normalization Gram')
    mask = eigenvalues > tolerance
    rank = int(mask.sum())
    if not rank:
        return dict(rank=0, null_image_norm=float(np.linalg.norm(response)),
                    second='undefined', fourth='undefined')
    leak = float(np.linalg.norm(response@vectors[:, ~mask]))
    bounded = rank == len(gram) or leak <= tolerance
    return dict(rank=rank, null_image_norm=leak,
                second='finite' if bounded or rank > 1 else 'infinite',
                fourth='finite' if bounded or rank > 2 else 'infinite',
                output_bounded=bounded)
