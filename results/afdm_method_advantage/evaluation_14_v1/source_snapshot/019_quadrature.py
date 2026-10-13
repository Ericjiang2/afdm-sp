"""Positive quadrature for a fixed gain prior and legal finite QPSK data."""
import argparse
import itertools
from pathlib import Path
import sys

import numpy as np
from scipy.special import ndtri
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk, _prior_factor
from experiments.afdm_structured_inference_20261003.potential import finite_potential, real_pack
from experiments.afdm_shared_channel_20261004.common import run, dump


def validate_nodes(nodes, weights):
    nodes, weights = np.asarray(nodes, complex), np.asarray(weights, float)
    if (nodes.ndim != 2 or min(nodes.shape) < 1 or weights.shape != (len(nodes),)
            or not np.isfinite(nodes).all() or not np.isfinite(weights).all()
            or np.any(weights <= 0) or not np.isclose(weights.sum(), 1, atol=1e-13, rtol=1e-13)):
        raise ValueError('finite gain nodes and strictly positive normalized weights required')
    return nodes, weights


def gaussian_nodes(mean, covariance, order, max_points=300000):
    mean, covariance = np.asarray(mean, complex), np.asarray(covariance, complex)
    if mean.ndim != 1 or covariance.shape != (len(mean), len(mean)):
        raise ValueError('incompatible Gaussian prior dimensions')
    if not np.isfinite(mean).all() or not np.isfinite(covariance).all():
        raise ValueError('nonfinite Gaussian prior')
    factor, _ = _prior_factor(covariance)
    rank = factor.shape[1]
    if isinstance(order, bool) or not isinstance(order, int) or order < 1 or order**(2*rank) > max_points:
        raise ValueError('invalid quadrature order or point cap exceeded')
    if rank == 0:
        return mean[None, :].copy(), np.ones(1)
    # hermgauss integrates exp(-t^2): t+iu has CN(0,1) after this normalization.
    axis, weight = np.polynomial.hermite.hermgauss(order)
    ids = np.array(list(itertools.product(range(order), repeat=2*rank)))
    z = axis[ids[:, :rank]] + 1j*axis[ids[:, rank:]]
    weights = np.prod(weight[ids]/np.sqrt(np.pi), axis=1)
    return validate_nodes(mean+z@factor.T, weights)


def sphere_nodes(p, total_energy, order, max_points=300000):
    """Uniform complex sphere; P=2 power fraction is uniform on [0,1]."""
    if p not in (1, 2) or not np.isfinite(total_energy) or total_energy <= 0:
        raise ValueError('sphere quadrature requires P=1 or 2 and positive total energy')
    count = 4*order if p == 1 else order*(4*order)**2
    if isinstance(order, bool) or not isinstance(order, int) or order < 1 or count > max_points:
        raise ValueError('invalid quadrature order or point cap exceeded')
    phase = np.exp(2j*np.pi*np.arange(4*order)/(4*order))
    if p == 1:
        return validate_nodes(np.sqrt(total_energy)*phase[:, None], np.full(len(phase), 1/len(phase)))
    t, w = np.polynomial.legendre.leggauss(order)
    t, w = (t+1)/2, w/2
    ids = np.array(list(itertools.product(range(order), range(len(phase)), range(len(phase)))))
    nodes = np.sqrt(total_energy)*np.column_stack((np.sqrt(t[ids[:, 0]])*phase[ids[:, 1]],
                                                np.sqrt(1-t[ids[:, 0]])*phase[ids[:, 2]]))
    return validate_nodes(nodes, w[ids[:, 0]]/len(phase)**2)


def independent_nodes(p, total_energy, exponent, seed, normalized=False):
    """Independent scrambled Sobol rule; seed is frozen before any observation."""
    if p < 1 or exponent < 1 or exponent > 19 or total_energy <= 0:
        raise ValueError('invalid independent reference rule')
    u = qmc.Sobol(2*p, scramble=True, seed=np.random.default_rng(seed)).random_base2(exponent)
    normal = ndtri(u)
    if not np.isfinite(normal).all():
        raise FloatingPointError('Sobol inverse normal reached a boundary')
    z = (normal[:, :p]+1j*normal[:, p:])/np.sqrt(2)
    if normalized:
        z *= np.sqrt(total_energy)/np.linalg.norm(z, axis=1)[:, None]
    else:
        z *= np.sqrt(total_energy/p)
    return validate_nodes(z, np.full(len(z), 1/len(z)))


def legal_potential(words, responses, weights, eta, xi, sigma2, amplitude=.5):
    """Require legal data states; repeated states for different h nodes are legal."""
    words = np.asarray(words, complex)
    if words.ndim != 2 or not np.isin(words.real, [-amplitude, amplitude]).all() or not np.isin(words.imag, [-amplitude, amplitude]).all():
        raise ValueError('data nodes must lie on the declared QPSK support')
    _, weights = validate_nodes(words, weights)
    return finite_potential(real_pack(words), real_pack(responses), np.log(weights), eta, xi, sigma2)


def response_checks():
    words, _ = enumerate_qpsk(2)
    gains, gain_weights = gaussian_nodes([0], [[1]], 7)
    states = np.tile(words, (len(gains), 1))
    h = np.repeat(gains, len(words), axis=0)
    weights = np.repeat(gain_weights/len(words), len(words))
    pilot = np.array([.3+.2j, -.1+.4j])
    responses = h*(states+pilot)
    eta, xi, sigma2 = np.array([.7,-.3,.2,.6]), np.array([.1,.2,-.4,.3]), .7
    value = legal_potential(states, responses, weights, eta, xi, sigma2)
    step = 1e-5
    mean_fd, covariance_fd, cross_fd = [], [], []
    for j in range(4):
        unit = np.eye(4)[j]*step
        plus = legal_potential(states,responses,weights,eta,xi+unit,sigma2)
        minus = legal_potential(states,responses,weights,eta,xi-unit,sigma2)
        mean_fd.append((plus['psi']-minus['psi'])/(2*step))
        covariance_fd.append((plus['mean_z']-minus['mean_z'])/(2*step))
        plus = legal_potential(states,responses,weights,eta+unit,xi,sigma2)
        minus = legal_potential(states,responses,weights,eta-unit,xi,sigma2)
        cross_fd.append((plus['mean_z']-minus['mean_z'])/(2*step))
    # A normalized observation-dependent base w_y(s) proportional exp(alpha*y*s).
    # Its log derivative alpha*(s-E_base s) contributes alpha Var_post(s).
    alpha, y = 1.7, .31
    def dependent(y_value):
        tilted = weights*np.exp(alpha*y_value*states.real[:,0])
        tilted /= tilted.sum()
        source = eta.copy(); source[0] = 2*y_value/sigma2
        return legal_potential(states,responses,tilted,source,xi,sigma2)
    dep = dependent(y)
    total_fd = (dependent(y+step)['mean_z'][0]-dependent(y-step)['mean_z'][0])/(2*step)
    fixed = 2*dep['cov_z_f'][0,0]/sigma2
    chain = alpha*dep['cov_z'][0,0]
    records = dict(mean_error=float(np.max(abs(np.array(mean_fd)-value['mean_z']))),
        covariance_error=float(np.max(abs(np.array(covariance_fd).T-value['cov_z']))),
        mixed_error=float(np.max(abs(np.array(cross_fd).T-value['cov_z_f']))),
        support_variance_error=float(np.max(abs(value['cov_z'].diagonal()-(.25-value['mean_z']**2)))),
        covariance_min_eigenvalue=float(np.linalg.eigvalsh(value['cov_z']).min()),
        probability_sum=float(value['probabilities'].sum()), dependent_total_fd=float(total_fd),
        dependent_fixed_base=float(fixed), dependent_missing_chain=float(chain),
        dependent_corrected_error=float(abs(total_fd-fixed-chain)))
    return records, dict(states=states,responses=responses,weights=weights,eta=eta,xi=xi,
                         probability=value['probabilities'],mean=value['mean_z'],covariance=value['cov_z'],cross=value['cov_z_f'])


CONFIG = dict(seed=[20261004,110000,50], finite_difference_step=1e-5,
              integration_orders=[5,9,13], independent_sobol_exponent=16,
              derivative_tolerance=2e-8, receiver_calls=0)
SOURCES = [__file__, ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
           ROOT/'experiments/afdm_structured_inference_20261003/potential.py',
           ROOT/'experiments/afdm_structured_inference_20261003/common.py',
           ROOT/'experiments/afdm_inference_causal_20261002/oracle_comparison.py']


def calculate(output):
    checks, raw = response_checks()
    np.savez(output/'response_raw.npz', **raw)
    # Normalized full-density evidence at N=1, h Gaussian and finite QPSK.
    from experiments.afdm_shared_channel_20261004.probability import conditional_scores
    words, _ = enumerate_qpsk(1)
    ops = np.ones((1,1,1), complex)
    y, pilot, noise = np.array([.4+.3j]), np.array([.2+.1j]), .8
    values = []
    for order in CONFIG['integration_orders']:
        nodes, weights = gaussian_nodes([0], [[1]], order)
        scores = conditional_scores(y,ops,pilot,words,np.zeros(1,complex),np.zeros((2,2)),[0],noise,nodes,weights)
        variance = noise+abs(pilot+words[:,0])**2
        analytic = -np.log(np.pi*variance)-abs(y[0])**2/variance
        values.append(dict(order=order,nodes=len(nodes),max_log_density_error=float(np.max(abs(scores-analytic)))))
        np.savez(output/f'integration_{order}.npz',scores=scores,analytic=analytic,nodes=nodes,weights=weights)
    nodes, weights = independent_nodes(1,1,CONFIG['independent_sobol_exponent'],CONFIG['seed'])
    reference = conditional_scores(y,ops,pilot,words,np.zeros(1,complex),np.zeros((2,2)),[0],noise,nodes,weights)
    independent_error = float(np.max(abs(reference-analytic)))
    np.savez(output/'independent.npz',nodes=nodes,weights=weights,scores=reference,analytic=analytic)
    dump(output/'raw.json',dict(checks=checks,integration=values,independent_error=independent_error))
    if max(checks[k] for k in ('mean_error','covariance_error','mixed_error','support_variance_error','dependent_corrected_error')) > CONFIG['derivative_tolerance']:
        raise AssertionError('finite potential derivative contract failed')
    if abs(checks['dependent_total_fd']-checks['dependent_fixed_base']) < .01:
        raise AssertionError('dependent-base counterexample did not separate responses')
    return dict(status='finite_support_and_response_contracts_verified',checks=checks,
        integration=values, independent_log_density_error=independent_error,
        interpretation='positive fixed-prior integration tool; no algorithmic novelty or deployment claim')


if __name__ == '__main__':
    from experiments.afdm_shared_channel_20261004.probability import SOURCES as PROBABILITY_SOURCES
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='message_v1')
    args = parser.parse_args()
    run(args.stage,CONFIG,SOURCES+PROBABILITY_SOURCES,calculate)
