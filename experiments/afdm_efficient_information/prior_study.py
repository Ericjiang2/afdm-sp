"""Frozen geometry and complete actual-prior information study configurations."""
import argparse
import time
from pathlib import Path

import numpy as np

from experiments.afdm_efficient_information.prior_likelihood import (
    ActualPrior, actual_signal_covariance, angular_density, cp1_nodes,
    pdp_distribution, project_information, system_for, collision_qlogq_coefficient,
)
from experiments.afdm_efficient_information.protocol import run
from experiments.afdm_higher_order_information.prior import geometry
from experiments.afdm_shared_channel_20261004.production_prior import (
    dense_gram, frozen_components,
)
from experiments.afdm_shared_channel_20261004.production_diagnostic import source_paths
from experiments.afdm_shared_channel_20261004.common import ROOT, dump

GEOMETRY_CONFIG = dict(seed=[20261005, 104835, 11], new_observations=0,
    receiver_calls=0, decoder_calls=0, sizes=[4, 8, 16],
    centers=[0., .04, .35, 1., 1.95, 2.], separations=[0., .015, .08, .12, .2, .49],
    collision_centers=[.27, .35], collision_deltas=[.01, .003, .001, .0003, .0001, .00003],
    pdp_modes=['equal', [1., .3], 'marginal'], dense_tolerance=1e-11,
    qlogq_signal_tolerance=.03, coefficient_fit_last=3, covariance_quadrature_order=48,
    covariance_quadrature_phases=96, threshold_relative_sides=[.999999, 1.000001],
    scope='actual two-path common-zero-delay slices; geometry integrals only')
CASES = [
    dict(name='regular_g0_equal', model='g0', pdp='equal', delta=.2, mu=.35),
    dict(name='regular_g0_conditional_unequal', model='g0', pdp=[1., .3], delta=.2, mu=.35),
    dict(name='regular_g0_actual_marginal', model='g0', pdp='marginal', delta=.2, mu=.35),
    dict(name='regular_g1_actual_marginal', model='g1', pdp='marginal', delta=.2, mu=.35),
    dict(name='near_collision_g0_actual_marginal', model='g0', pdp='marginal', delta=.035, mu=.35),
    dict(name='platform_g0_actual_marginal', model='g0', pdp='marginal', delta=.015, mu=.04),
]
INFORMATION_CONFIG = dict(seed=[20261005, 104835, 12], new_observations=1536,
    receiver_calls=0, decoder_calls=0, n=4, cases=CASES, observations_per_case=256,
    independent_projection_train=128, log_tau=0., sigma2=.8,
    rules=[dict(name='coarse', order=12, phases=24, rule='product', seed=731),
           dict(name='fine', order=24, phases=48, rule='product', seed=732),
           dict(name='independent', order=64, phases=128, rule='sobol', seed=739)],
    derivative_steps=[.0001, .00005, .00002], fd_fixture_observations=8,
    logpdf_max_tolerance=.03, score_relative_rms_tolerance=.05,
    mass_tolerance=.001, derivative_relative_tolerance=.001,
    effective_relative_tolerance=.12, nuisance_rcond=1e-10,
    positive_evidence_standard_errors=4.,
    scope='numerically refined actual-prior score information; not exact Fisher certification')


def serializable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k:serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


def discrete_branch(branch):
    """Discrete smoothness data only; collision rank is intentionally excluded."""
    geo = branch['geometry']
    return dict(active_support=(geo['weights'] != 0).tolist(),
                physical_clip_mask=geo['physical_clip_mask'].tolist(),
                rounded_dopplers=np.round(geo['dopplers']).astype(int).tolist(),
                pdp_limits=branch['pdp']['limits'].tolist())


def fit_collision_tail(points, coefficient, count, tolerance):
    """Use exactly the registered tail; a branch change makes this fit invalid."""
    tail = points[-count:]
    qualified = len(tail) == count and all(p['same_as_collision'] for p in tail)
    result = dict(fit_deltas=[p['delta'] for p in tail], branch_qualified=qualified,
                  fit_status='same_discrete_branch' if qualified else 'unqualified_discrete_branch',
                  log_slope_coefficient=None, log_slope_relative_error=None,
                  log_slope_refined=False)
    if not qualified:
        return result
    xfit = np.array([np.log(1/p['delta']**2) for p in tail])
    yfit = np.array([np.array(p['even_change'])/p['delta']**2 for p in tail])
    fitted = np.linalg.lstsq(np.column_stack((xfit, np.ones(len(xfit)))), yfit, rcond=None)[0][0]
    error = float(np.linalg.norm(fitted-coefficient)/max(np.linalg.norm(coefficient), 1e-12))
    result.update(log_slope_coefficient=fitted.tolist(), log_slope_relative_error=error,
                  log_slope_refined=error < tolerance)
    return result


def information_refinement(comparisons, derivative_rows, fd_relative, estimates,
                           effective_error, config=INFORMATION_CONFIG):
    """Every predeclared convergence requirement enters the saved decision."""
    derivative_steps = [row['step'] for row in derivative_rows]
    return dict(
        node_rules=all(c['logpdf_max'] <= config['logpdf_max_tolerance'] and
                       max(c['score_relative_rms']) <= config['score_relative_rms_tolerance']
                       for c in comparisons),
        derivative_steps=(derivative_steps == config['derivative_steps'][1:] and
            all(row['comparison']['logpdf_max'] <= config['logpdf_max_tolerance'] and
                max(row['comparison']['score_relative_rms']) <= config['derivative_relative_tolerance']
                for row in derivative_rows)),
        direct_finite_difference=bool(max(fd_relative) <= config['derivative_relative_tolerance']),
        quadrature_mass=max(e['quadrature_mass_error'] for e in estimates.values()) <= config['mass_tolerance'],
        effective_information=effective_error <= config['effective_relative_tolerance'])


def calculate_geometry(output):
    rows, thresholds, collisions = [], [], []
    for n in GEOMETRY_CONFIG['sizes']:
        system = system_for(n)
        threshold = n/np.pi*np.arctan(.1*np.sin(np.pi/n)/(1+.1*np.cos(np.pi/n)))
        sides = []
        for factor in GEOMETRY_CONFIG['threshold_relative_sides']:
            geo = geometry(system, 0., threshold*factor)
            sides.append(dict(factor=factor, active_atoms=int(np.any(geo['weights'] != 0, axis=1).sum())))
        thresholds.append(dict(n=n, delta_star=float(threshold), sides=sides))
        for mu in GEOMETRY_CONFIG['centers']:
            for delta in GEOMETRY_CONFIG['separations']:
                model = ActualPrior(n=n, pdp='equal')
                theta = [delta, mu, 0., 0.]
                branch = model.branch(theta); geo = branch['geometry']
                error = float(np.max(abs(geo['gram']-dense_gram(system, geo['weights']))))
                rows.append(dict(n=n, mu=mu, delta=delta, dense_gram_error=error,
                    eigenvalues=branch['eigenvalues'].tolist(), active_atoms=branch['active'].tolist(),
                    platform=branch['platform'], physical_clipped=geo['physical_clip_mask'].tolist(),
                    requested=geo['requested_dopplers'].tolist(), actual=geo['dopplers'].tolist(),
                    g0_moments=branch['moments'],
                    g1_moments=ActualPrior(n=n, model='g1', pdp='equal').branch(theta)['moments']))
    # Exact normalized-covariance evaluation exposes collision q log q without
    # trying to resolve a vanishing sphere region with finite angular nodes.
    for mu in GEOMETRY_CONFIG['collision_centers']:
        for pdp in GEOMETRY_CONFIG['pdp_modes']:
            model = ActualPrior(n=4, pdp=pdp)
            theta0 = np.array([0., mu, 0., 0.])
            collision_branch = discrete_branch(model.branch(theta0))
            zero = actual_signal_covariance(model, theta0).diagonal().real
            values = []
            for delta in GEOMETRY_CONFIG['collision_deltas']:
                theta = theta0.copy(); theta[0] = delta
                point_branch = discrete_branch(model.branch(theta))
                positive = actual_signal_covariance(model, theta).diagonal().real
                if isinstance(pdp, list):
                    swapped = ActualPrior(n=4, pdp=pdp[::-1])
                    negative = actual_signal_covariance(swapped, theta).diagonal().real
                else:
                    negative = positive
                even = (positive+negative)/2-zero
                odd = (positive-negative)/2
                q = delta**2
                values.append(dict(delta=delta, discrete_branch=point_branch,
                    same_as_collision=point_branch == collision_branch, signal_second=positive.tolist(),
                    even_change=even.tolist(), even_over_qlogq=(even/(q*np.log(1/q))).tolist(),
                    odd_over_delta=(odd/delta).tolist()))
            coefficient = collision_qlogq_coefficient(model, mu)
            last = np.array(values[-1]['even_over_qlogq'])
            relative_error = float(np.linalg.norm(last-coefficient)/max(np.linalg.norm(coefficient), 1e-12))
            fit = fit_collision_tail(values, coefficient, GEOMETRY_CONFIG['coefficient_fit_last'],
                                     GEOMETRY_CONFIG['qlogq_signal_tolerance'])
            collisions.append(dict(mu=mu, pdp=pdp, collision_discrete_branch=collision_branch,
                points=values, predicted_qlogq_coefficient=coefficient.tolist(),
                last_coefficient_relative_error=relative_error,
                finite_delta_convergence=(values[-1]['same_as_collision'] and
                    relative_error < GEOMETRY_CONFIG['qlogq_signal_tolerance']),
                **fit,
                interpretation='analytic population moments; nonzero coefficient rules out finite q-DQM'))
    dump(output/'geometry.json', serializable(rows))
    dump(output/'thresholds.json', thresholds)
    dump(output/'collision_covariance.json', collisions)
    worst = max(r['dense_gram_error'] for r in rows)
    if worst > GEOMETRY_CONFIG['dense_tolerance']:
        raise AssertionError('independent dense Gram contract failed')
    return dict(geometry_cases=len(rows), max_dense_gram_error=worst,
                thresholds=thresholds, collision_cases=collisions,
                new_observations=0, receiver_calls=0, decoder_calls=0,
                classifications=['exact G0 plateau zero', 'G1 nullspace divergent moments',
                                 'smooth positive-definite interior', 'clip/prune/round/PDP boundaries',
                                 'non-platform collision q regularity requires separate analysis'])


def compare(first, second):
    a, b = first['score'], second['score']
    relative = np.sqrt(np.mean((a-b)**2, axis=0))/np.maximum(np.sqrt(np.mean(b*b, axis=0)), .01)
    return dict(logpdf_max=float(np.max(abs(first['logpdf']-second['logpdf']))),
                score_relative_rms=relative.tolist())


def calculate_information(output):
    config = INFORMATION_CONFIG; rows = []
    for case_index, case in enumerate(config['cases']):
        started = time.monotonic()
        theta = np.array([case['delta'], case['mu'], config['log_tau'], np.log(config['sigma2'])])
        sampler = ActualPrior(n=config['n'], model=case['model'], pdp=case['pdp'])
        seed = [*config['seed'], case_index]
        y = sampler.sample(theta, config['observations_per_case'], seed)
        arrays = dict(y=y, theta=theta, seed=np.array(seed)); estimates, costs = {}, {}
        for rule in config['rules']:
            settings = {k:v for k,v in rule.items() if k != 'name'}
            model = ActualPrior(n=config['n'], model=case['model'], pdp=case['pdp'], **settings)
            result = model.evaluate(y, theta, config['derivative_steps'][0])
            estimates[rule['name']] = result
            arrays[rule['name']+'_logpdf'] = result['logpdf']
            arrays[rule['name']+'_score'] = result['score']
            costs[rule['name']] = dict(model.cost)
            if rule['name'] == 'fine':
                teacher = model
        comparisons = [compare(estimates['coarse'], estimates['fine']),
                       compare(estimates['fine'], estimates['independent'])]
        derivative_rows = []
        count = config['fd_fixture_observations']
        for step in config['derivative_steps'][1:]:
            result = teacher.evaluate(y[:count], theta, step)
            derivative_rows.append(dict(step=step, comparison=compare(
                {k:v[:count] for k,v in estimates['fine'].items() if isinstance(v, np.ndarray)}, result)))
            arrays[f'score_step_{step}'] = result['score']
        finite = np.zeros((count, 4))
        for axis in range(4):
            plus, minus = theta.copy(), theta.copy(); step = config['derivative_steps'][-1]
            plus[axis] += step; minus[axis] -= step
            finite[:, axis] = (teacher.logpdf(y[:count], plus)-teacher.logpdf(y[:count], minus))/(2*step)
        arrays['finite_difference_score'] = finite
        fd_relative = np.sqrt(np.mean((finite-estimates['fine']['score'][:count])**2, axis=0))/np.maximum(
            np.sqrt(np.mean(finite**2, axis=0)), .01)
        split = config['independent_projection_train']
        information = {}
        for name, result in estimates.items():
            score = result['score']
            fitted = project_information(score[:split], rtol=config['nuisance_rcond'])
            validated = project_information(score[split:], train=score[:split], rtol=config['nuisance_rcond'])
            arrays[name+'_effective_validation'] = validated.pop('efficient_score')
            fitted.pop('efficient_score')
            information[name] = dict(train=fitted, validation=validated,
                                     q_information_factor=1/(4*theta[0]**2))
        fine_info = information['fine']['validation']; alt_info = information['independent']['validation']
        effective_error = abs(fine_info['effective']-alt_info['effective'])/max(alt_info['effective'], .001)
        refinement_checks = information_refinement(comparisons, derivative_rows, fd_relative,
                                                  estimates, effective_error, config)
        refined = all(refinement_checks.values())
        if sampler.branch(theta)['platform'] and case['model'] == 'g0':
            classification = 'exact_zero'
            if np.any(estimates['fine']['score'][:, 0] != 0):
                raise AssertionError('exact platform score must be bitwise zero')
        elif refined and fine_info['effective'] > config['positive_evidence_standard_errors']*fine_info['effective_batch_se']:
            classification = 'numerically_positive_not_certified'
        else:
            classification = 'unresolved_numerical_information'
        row = dict(case=case, classification=classification, refined=bool(refined),
                   refinement_checks=refinement_checks,
                   comparisons=comparisons, derivative_steps=derivative_rows,
                   finite_difference_relative_rms=fd_relative.tolist(), effective_rule_relative_error=effective_error,
                   quadrature_mass_errors={k:v['quadrature_mass_error'] for k,v in estimates.items()},
                   information=information, costs=costs, final_teacher_cost=dict(teacher.cost),
                   sampler_cost=dict(sampler.cost), case_wall_seconds=time.monotonic()-started,
                   independent_train=split, independent_validation=len(y)-split,
                   target='observed actual-prior delta information projected against mu,log_tau,log_sigma2')
        rows.append(serializable(row))
        np.savez_compressed(output/(case['name']+'.npz'), **arrays)
        dump(output/(case['name']+'.json'), serializable(row))
    dump(output/'information.json', rows)
    return dict(cases=rows, new_observations=config['new_observations'],
                receiver_calls=0, decoder_calls=0,
                q_claim='interior chain rule only; q collision regularity not assumed',
                conditional_oracle='equal and fixed unequal PDP are separately labeled; marginal integrates exact PDP law',
                all_cases_retained=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['geometry', 'information'], required=True)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    frozen_components()
    base = Path(__file__).parent
    sources = [*source_paths(), __file__, base/'prior_likelihood.py', base/'test_prior_likelihood.py', base/'test_prior_study.py',
               ROOT/'experiments/afdm_higher_order_information/prior.py',
               ROOT/'experiments/afdm_shared_channel_20261004/production_prior.py',
               ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
               base/'PRIOR_THEORY.md', base/'PRIOR_QUALIFICATION.md']
    if args.mode == 'geometry':
        run(args.stage, GEOMETRY_CONFIG, sources, calculate_geometry, wall_seconds=120)
    else:
        run(args.stage, INFORMATION_CONFIG, sources, calculate_information, wall_seconds=900)


if __name__ == '__main__':
    main()
