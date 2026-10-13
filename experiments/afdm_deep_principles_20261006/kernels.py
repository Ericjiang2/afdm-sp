"""Small deterministic kernels; no RNG, channel sampling, fitting, or receivers."""
from collections import Counter
from math import comb

import numpy as np
from scipy.stats import ncx2

from experiments.afdm_higher_order_information.prior import geometry


class EvaluationCounter:
    """Reserve logical kernel values before evaluation; FLOPs are not evaluations."""
    def __init__(self, limit):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError('nonnegative integer evaluation limit required')
        self.limit = limit
        self.counts = Counter()

    def add(self, name, count=1):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError('nonnegative integer count required')
        if sum(self.counts.values())+count > self.limit:
            raise ValueError('deterministic kernel evaluation reservation exceeded')
        self.counts[name] += count

    def report(self):
        return dict(by_kernel=dict(self.counts), total=sum(self.counts.values()), reserved=self.limit)


def inverse_sqrt_jets(s):
    """Derivatives 0..3 of S^(-1/2), with S real and strictly positive."""
    s = np.asarray(s, float)
    if s.shape != (4,) or not np.isfinite(s).all() or s[0] <= 0:
        raise ValueError('finite positive normalization and three derivatives required')
    x, d1, d2, d3 = s
    return np.array([x**(-.5), -.5*x**(-1.5)*d1,
                     .75*x**(-2.5)*d1*d1-.5*x**(-1.5)*d2,
                     -1.875*x**(-3.5)*d1**3+2.25*x**(-2.5)*d1*d2-.5*x**(-1.5)*d3])


def actual_geometry(system, mu, delta, counter):
    counter.add('actual_geometry_calls')
    return geometry(system, mu, delta)


def physical_jets(system, nu, counter):
    """Analytic finite-Fourier derivatives, retaining the actual frozen mask.

    Differentiate the original five-point window norm before cap/prune. The
    independent actual geometry response is returned for a parity check.
    """
    n = system.N_total
    actual = actual_geometry(system, nu, 0., counter)
    counter.add('dirichlet_jet_values', 20)
    offsets = np.arange(-2, 3)
    frequencies = 2*np.pi*np.arange(n)/n
    exponential = np.exp(1j*(offsets[:, None]+nu)*frequencies[None, :])
    alpha = np.array([np.mean(exponential*(1j*frequencies)**order, axis=1) for order in range(4)])
    norm_squared = np.array([sum(comb(order, j)*np.sum(alpha[j]*alpha[order-j].conj())
                                 for j in range(order+1)).real for order in range(4)])
    norm_squared[0] += 1e-300
    normalizer = inverse_sqrt_jets(norm_squared)
    weights = np.array([sum(comb(order, j)*alpha[j]*normalizer[order-j]
                            for j in range(order+1)) for order in range(4)])
    cap = system.k_max_cap
    keep = np.array([abs(m) <= cap and actual['weights'][m+cap, 0] != 0 for m in offsets])
    weights[:, ~keep] = 0
    fourier = np.exp(1j*np.outer(frequencies, offsets))
    return weights@fourier.T, actual['g0'][:, 0], keep


def complex_complement(columns, rtol):
    columns = np.asarray(columns, complex)
    if columns.ndim != 2 or not np.isfinite(columns).all():
        raise ValueError('finite complex columns required')
    left, singular, _ = np.linalg.svd(columns, full_matrices=False)
    rank = int(np.sum(singular > rtol*singular[0])) if len(singular) and singular[0] else 0
    if rank != columns.shape[1]:
        raise ValueError(f'complex nuisance rank failure: {rank}/{columns.shape[1]}')
    basis = left[:, :rank]
    return np.eye(len(columns))-basis@basis.conj().T, singular


def real_center_residual(u, v):
    u, v = np.asarray(u, complex), np.asarray(v, complex)
    if u.shape != v.shape or not np.isfinite(u).all() or not np.isfinite(v).all():
        raise ValueError('finite equal-shaped real-tangent vectors required')
    norm = float(np.vdot(v, v).real)
    if norm == 0:
        return u.copy(), 0.
    coefficient = float(np.vdot(v, u).real/norm)
    return u-coefficient*v, coefficient


def add_proper_gaussian_noise(fourth, second, noise):
    """Exact independent proper-Gaussian Wick terms; no noise realizations."""
    second, fourth = np.asarray(second, complex), np.asarray(fourth, complex)
    n = len(second)
    if (second.shape != (n, n) or fourth.shape != (n, n, n, n)
            or not np.isfinite(noise) or noise < 0):
        raise ValueError('square moments and nonnegative noise variance required')
    i, j, k, last = np.indices(fourth.shape)
    dij, dil = (i == j).astype(float), (i == last).astype(float)
    dkj, dkl = (k == j).astype(float), (k == last).astype(float)
    total = (fourth+noise*(dij*second[k, last]+dil*second[k, j]
                          +dkj*second[i, last]+dkl*second[i, j])
             +noise**2*(dij*dkl+dil*dkj))
    return total, second+noise*np.eye(n)


def efficient_derivative(columns, slopes, gains, rtol, counter):
    """Compare sequential complex-gain/real-center projection to a real Jacobian."""
    counter.add('efficient_derivative_kernels', 2)
    projector, gain_singular = complex_complement(columns, rtol)
    fdelta = slopes@np.array([-gains[0], gains[1]])
    fmu = slopes@gains
    u, v = projector@fdelta, projector@fmu
    residual, coefficient = real_center_residual(u, v)
    nuisance = np.column_stack((columns[:, 0], 1j*columns[:, 0],
                                columns[:, 1], 1j*columns[:, 1], fmu))
    real_nuisance = np.vstack((nuisance.real, nuisance.imag))
    target = np.concatenate((fdelta.real, fdelta.imag))
    left, singular, _ = np.linalg.svd(real_nuisance, full_matrices=False)
    rank = int(np.sum(singular > rtol*singular[0]))
    if rank != 5:
        raise ValueError(f'real nuisance rank failure: {rank}/5')
    direct = target-left[:, :rank]@(left[:, :rank].T@target)
    a, b = gains.sum(), gains[1]-gains[0]
    aa = projector@(slopes[:, 1]-slopes[:, 0])/2
    bb = projector@(slopes[:, 1]+slopes[:, 0])/2
    return dict(J=float(np.vdot(residual, residual).real), direct_J=float(direct@direct),
                residual=residual, direct_residual=direct, u=u, v=v, A=aa, B=bb,
                coefficient=coefficient, gain_singular=gain_singular,
                real_nuisance_singular=singular,
                identity_error=float(max(np.linalg.norm(u-a*aa-b*bb), np.linalg.norm(v-b*aa-a*bb))))


def ncx2_power_excess(noncentrality, alpha, cutoff, counter):
    """Stable bounded power excess; explicit quadratic Taylor branch near zero.

    The Poisson representation bounds the third derivative by one, giving
    absolute remainder <= lambda^3/6 on the declared small-lambda branch.
    """
    values = np.asarray(noncentrality, float)
    if not np.isfinite(values).all() or np.any(values < 0) or not 0 < alpha < 1 or cutoff <= 0:
        raise ValueError('finite nonnegative noncentralities and valid alpha/cutoff required')
    counter.add('bounded_power_values', values.size)
    c = -2*np.log(alpha)
    small = values <= cutoff
    result = np.empty_like(values)
    result[small] = alpha*c/4*values[small]+alpha*c*(c-4)/64*values[small]**2
    result[~small] = ncx2.sf(c, 2, values[~small])-alpha
    if not np.isfinite(result).all() or np.any(result < 0) or np.any(result > 1-alpha):
        raise FloatingPointError('bounded noncentral chi-square probability failed')
    return result
