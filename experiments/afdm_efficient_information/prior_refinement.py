"""Saved-observation near-collision refinement in a fixed spectral CP1 chart.

Only quadrature changes. The actual PDP law, observations, target, nuisance and
thresholds are inherited from v1. All nodes and used components are persisted.
"""
import argparse
import hashlib
from pathlib import Path
import time

import numpy as np
from scipy.special import roots_legendre
from scipy.stats import qmc

from experiments.afdm_efficient_information.prior_likelihood import ActualPrior, project_information
from experiments.afdm_efficient_information.prior_study import (
    compare, discrete_branch, information_refinement, serializable,
)
from experiments.afdm_efficient_information.protocol import run
from experiments.afdm_shared_channel_20261004.common import ROOT, dump
from experiments.afdm_shared_channel_20261004.production_prior import frozen_components
from experiments.afdm_shared_channel_20261004.production_diagnostic import source_paths

INPUT = ROOT/'results/afdm_efficient_information/prior_information_v1/near_collision_g0_actual_marginal.npz'
CONFIG = dict(seed=[20261005, 104835, 13], new_observations=0, reused_observations=256,
    receiver_calls=0, decoder_calls=0, n=4, model='g0', pdp='marginal',
    input_path=str(INPUT.relative_to(ROOT)),
    input_sha256='81557344a52b5933b452c368c9b48736bfa4dcaba18a970d65ae709a57abe4fc',
    design_theta=[.035, .35, 0., float(np.log(.8))],
    endpoint_power=4, chart='fixed eigenvectors of design-point G0 Gram; never adapted to Y',
    rules=[dict(name='coarse', order=16, phases=32, rule='product', seed=741, phase_shift=0.),
           dict(name='medium', order=32, phases=64, rule='product', seed=742, phase_shift=0.),
           dict(name='fine', order=64, phases=128, rule='product', seed=743, phase_shift=0.),
           dict(name='independent', order=64, phases=128, rule='sobol', seed=751, phase_shift=.137)],
    new_quadrature_nodes=18944, unused_base_initialization_nodes=32,
    comparisons=[['coarse', 'medium'], ['medium', 'fine'], ['fine', 'independent']],
    independent_projection_train=128, derivative_steps=[.0001, .00005, .00002],
    fd_fixture_observations=8, integration_batch=4,
    logpdf_max_tolerance=.03, score_relative_rms_tolerance=.05,
    mass_tolerance=.001, derivative_relative_tolerance=.001,
    effective_relative_tolerance=.12, nuisance_rcond=1e-10,
    positive_evidence_standard_errors=4.,
    scope='zero new observations; new positive quadrature over exactly the saved actual-prior model')


def endpoint_nodes(unitary, order, phases, power=4, rule='product', seed=741, phase_shift=0.):
    """Positive change of variables t=1-(1-s)^power; columns of U are eigenvectors."""
    unitary = np.asarray(unitary, complex)
    if unitary.shape != (2, 2) or not np.allclose(unitary.conj().T@unitary, np.eye(2), atol=1e-12):
        raise ValueError('unitary two-path chart required')
    if not isinstance(power, int) or power < 1 or order < 2 or phases < 4:
        raise ValueError('positive integer map power and valid rule sizes required')
    if rule == 'product':
        x, w = roots_legendre(order)
        s = np.repeat((x+1)/2, phases)
        phi = 2*np.pi*np.tile((np.arange(phases)+.5)/phases+phase_shift, order)
        base_weights = np.repeat(w/(2*phases), phases)
    elif rule == 'sobol':
        count = order*phases
        if count & (count-1):
            raise ValueError('Sobol endpoint rule requires power-of-two node count')
        points = qmc.Sobol(2, scramble=True, seed=seed).random_base2(count.bit_length()-1)
        s, phi = points[:, 0], 2*np.pi*(points[:, 1]+phase_shift)
        base_weights = np.full(count, 1/count)
    else:
        raise ValueError('unknown endpoint rule')
    complement = (1-s)**power
    t = 1-complement
    jacobian = power*(1-s)**(power-1)
    sphere = np.column_stack((np.sqrt(t), np.sqrt(complement)*np.exp(1j*phi)))
    nodes = sphere@unitary.T
    weights = base_weights*jacobian
    if np.any(weights <= 0) or not np.isfinite(weights).all():
        raise ValueError('endpoint rule must retain strictly positive finite weights')
    return dict(nodes=nodes, weights=weights, chart_s=s, chart_phi=phi,
                jacobian=jacobian, base_weights=base_weights, unitary=unitary.copy())


class FixedChartPrior(ActualPrior):
    """Frozen kernel with an observation-independent fixed integration chart.

    Design geometry defines U once. During every theta stencil, U, s, phi and
    the Jacobian stay fixed. All changing R/B/PDP branch logic is inherited.
    """
    def __init__(self, design_theta, order, phases, power=4, rule='product', seed=741,
                 phase_shift=0., n=4, pdp='marginal'):
        # Eight base nodes are unused initialization overhead, recorded in CONFIG.
        super().__init__(n=n, model='g0', pdp=pdp, order=2, phases=4)
        self.design_theta = self._validate(design_theta).copy()
        branch = self.branch(self.design_theta)
        eigenvalues, unitary = np.linalg.eigh(branch['geometry']['gram'])
        if eigenvalues[0] <= 1e-12:
            raise ValueError('fixed endpoint chart requires positive-definite design Gram')
        # Reproducible phase convention; a fixed right-unitary rotation preserves Haar measure.
        for column in range(2):
            pivot = int(np.argmax(abs(unitary[:, column])))
            unitary[:, column] *= np.exp(-1j*np.angle(unitary[pivot, column]))
        self.chart = endpoint_nodes(unitary, order, phases, power, rule, seed, phase_shift)
        self.nodes = self.chart['nodes']; self.weights = self.chart['weights']
        self.nodes.setflags(write=False); self.weights.setflags(write=False)
        self.design_theta.setflags(write=False)
        self.order, self.phases, self.rule = order, phases, rule
        self.design_eigenvalues = eigenvalues
        self.chart_eigendecompositions = 1

    def evaluate(self, y, theta, step=1e-4):
        return self._integrate(y, theta, step, batch=CONFIG['integration_batch'])

    def logpdf(self, y, theta):
        return self._integrate(y, theta, batch=CONFIG['integration_batch'])['logpdf']


def save_components(output, stem, model, theta, step):
    """Persist exactly the cached arrays used for integration, without reevaluating."""
    key = (tuple(np.asarray(theta, float)), step)
    if key not in model._cache:
        raise ValueError('component evidence must have already been evaluated')
    component = model._cache[key]
    arrays = dict(means=component['means'], logweights=component['logweights'],
                  theta=np.asarray(theta), derivative_step=0. if step is None else step)
    if component['derivatives'] is not None:
        arrays['derivatives'] = component['derivatives']
    np.savez_compressed(output/(stem+'_components.npz'), **arrays)
    dump(output/(stem+'_components.json'), dict(
        array_path=stem+'_components.npz',
        node_path=stem.split('__')[0]+'_nodes.npz',
        derivatives_present=component['derivatives'] is not None,
        quadrature_mass_error=component['quadrature_mass_error'],
        discrete_branch=discrete_branch(component['branch']),
        cost_snapshot=dict(model.cost)))


def calculate(output):
    if hashlib.sha256(INPUT.read_bytes()).hexdigest() != CONFIG['input_sha256']:
        raise ValueError('saved observations differ from frozen v1 input hash')
    with np.load(INPUT) as saved:
        y, theta = saved['y'].copy(), saved['theta'].copy()
        previous = dict(logpdf=saved['fine_logpdf'].copy(), score=saved['fine_score'].copy())
    if y.shape != (CONFIG['reused_observations'], CONFIG['n']) or not np.array_equal(theta, CONFIG['design_theta']):
        raise ValueError('saved shape or physical point differs from registered model')
    arrays = dict(y=y, theta=theta, previous_fine_logpdf=previous['logpdf'], previous_fine_score=previous['score'])
    np.savez_compressed(output/'observations.npz', y=y, theta=theta)
    estimates, information, costs = {}, {}, {}
    teacher = None
    for rule in CONFIG['rules']:
        started = time.monotonic()
        options = {k:v for k,v in rule.items() if k != 'name'}
        model = FixedChartPrior(theta, power=CONFIG['endpoint_power'], **options)
        name = rule['name']
        np.savez_compressed(output/(name+'_nodes.npz'), **model.chart,
                            design_theta=model.design_theta, design_eigenvalues=model.design_eigenvalues)
        result = model.evaluate(y, theta, CONFIG['derivative_steps'][0])
        estimates[name] = result
        save_components(output, name+'__base', model, theta, CONFIG['derivative_steps'][0])
        arrays[name+'_logpdf'] = result['logpdf']; arrays[name+'_score'] = result['score']
        split = CONFIG['independent_projection_train']
        train = project_information(result['score'][:split], rtol=CONFIG['nuisance_rcond'])
        validation = project_information(result['score'][split:], train=result['score'][:split], rtol=CONFIG['nuisance_rcond'])
        arrays[name+'_effective_train'] = train.pop('efficient_score')
        arrays[name+'_effective_validation'] = validation.pop('efficient_score')
        information[name] = dict(train=train, validation=validation)
        costs[name] = dict(kernel=dict(model.cost), chart_eigendecompositions=model.chart_eigendecompositions,
                           node_count=len(model.nodes), wall_seconds=time.monotonic()-started)
        if name == 'fine':
            teacher = model
        else:
            del model
    if teacher is None:
        raise ValueError('registered fine rule missing')
    derivative_rows = []; count = CONFIG['fd_fixture_observations']
    for index, step in enumerate(CONFIG['derivative_steps'][1:], start=1):
        result = teacher.evaluate(y[:count], theta, step)
        reference = {k:v[:count] for k,v in estimates['fine'].items() if isinstance(v, np.ndarray)}
        derivative_rows.append(dict(step=step, comparison=compare(reference, result)))
        arrays[f'score_step_{index}'] = result['score']
        save_components(output, f'fine__step_{index}', teacher, theta, step)
    plus_logs, minus_logs = np.zeros((count, 4)), np.zeros((count, 4))
    step = CONFIG['derivative_steps'][-1]
    for axis in range(4):
        plus, minus = theta.copy(), theta.copy()
        plus[axis] += step; minus[axis] -= step
        plus_logs[:, axis] = teacher.logpdf(y[:count], plus)
        save_components(output, f'fine__fd_{axis}_plus', teacher, plus, None)
        minus_logs[:, axis] = teacher.logpdf(y[:count], minus)
        save_components(output, f'fine__fd_{axis}_minus', teacher, minus, None)
    finite = (plus_logs-minus_logs)/(2*step)
    arrays.update(fd_plus_logpdf=plus_logs, fd_minus_logpdf=minus_logs,
                  finite_difference_score=finite, finite_difference_step=np.array(step))
    fd_relative = np.sqrt(np.mean((finite-estimates['fine']['score'][:count])**2, axis=0))/np.maximum(
        np.sqrt(np.mean(finite**2, axis=0)), .01)
    comparisons = [compare(estimates[a], estimates[b]) for a,b in CONFIG['comparisons']]
    fine = information['fine']['validation']; independent = information['independent']['validation']
    effective_error = abs(fine['effective']-independent['effective'])/max(independent['effective'], .001)
    checks = information_refinement(comparisons, derivative_rows, fd_relative, estimates, effective_error, CONFIG)
    refined = all(checks.values())
    positive = fine['effective'] > CONFIG['positive_evidence_standard_errors']*fine['effective_batch_se']
    classification = 'numerically_positive_not_certified' if refined and positive else 'unresolved_numerical_information'
    np.savez_compressed(output/'scores.npz', **arrays)
    result = dict(classification=classification, refined=refined, refinement_checks=checks,
                  comparisons=[dict(pair=pair, **c) for pair,c in zip(CONFIG['comparisons'], comparisons)],
                  derivative_steps=derivative_rows, finite_difference_relative_rms=fd_relative.tolist(),
                  effective_rule_relative_error=effective_error,
                  quadrature_mass_errors={name:r['quadrature_mass_error'] for name,r in estimates.items()},
                  previous_rule_comparison=compare(previous, estimates['fine']),
                  information=information, costs=costs, final_teacher_cost=dict(teacher.cost),
                  new_observations=0, reused_observations=len(y),
                  new_quadrature_nodes=CONFIG['new_quadrature_nodes'],
                  receiver_calls=0, decoder_calls=0,
                  input_sha256=CONFIG['input_sha256'],
                  evidence='new registered integration, same held-out observations; not independent statistical replication',
                  remaining='finite projection/sample uncertainty remains even if quadrature converges')
    dump(output/'refinement.json', serializable(result))
    return serializable(result)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    frozen_components()
    base = Path(__file__).parent
    sources = [*source_paths(), __file__, base/'test_prior_refinement.py', base/'PRIOR_REFINEMENT.md',
               base/'prior_likelihood.py', base/'prior_study.py', INPUT,
               INPUT.parent/'registration.json', INPUT.parent/'attempt.json',
               ROOT/'experiments/afdm_higher_order_information/prior.py',
               ROOT/'experiments/afdm_shared_channel_20261004/production_prior.py',
               ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py']
    run(args.stage, CONFIG, sources, calculate, wall_seconds=900)


if __name__ == '__main__':
    main()
