"""Registered transfer/cost stages. Main-session source commit and GO required."""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

from experiments.afdm_efficient_information import features
from experiments.afdm_efficient_information.prior_likelihood import ActualPrior, daft
from experiments.afdm_efficient_information.protocol import ARTIFACT, ROOT, dump, hashes, run
from experiments.afdm_efficient_information.transfer import (
    Costs, InputPrior, amortization, anchored_features, binomial_interval,
    forward_daft, input_states, inverse_daft, phase_diagnostics, rejection_threshold,
    restore_regressor, sample_observations, stage_cost_inventory,
)
from experiments.afdm_higher_order_information.moments import FiniteControl
from experiments.afdm_shared_channel_20261004.production_prior import dense_gram, frozen_components

SCENARIOS = [
    dict(name='actual_uniform', input_kind='uniform', generator='g0', gain_prior='marginal', noise_factor=1),
    dict(name='actual_pilot', input_kind='pilot', generator='g0', gain_prior='marginal', noise_factor=1),
    dict(name='actual_biased', input_kind='biased', generator='g0', gain_prior='marginal', noise_factor=1),
    dict(name='actual_repetition', input_kind='repetition', generator='g0', gain_prior='marginal', noise_factor=1),
    dict(name='conditional_equal_pdp', input_kind='uniform', generator='g0', gain_prior='equal', noise_factor=1),
    dict(name='actual_noise_mismatch', input_kind='uniform', generator='g0', gain_prior='marginal', noise_factor=2),
    dict(name='actual_g1', input_kind='uniform', generator='g1', gain_prior='marginal', noise_factor=1),
    dict(name='gaussian_control', input_kind='uniform', generator='g1', gain_prior='gaussian', noise_factor=1),
]
CONFIG = dict(seed=[20261005, 104835, 41], new_observations=7680,
              dimensions=[4, 16, 64], calibration_per_dimension=512,
              test_per_hypothesis=128, deltas=[0., .2], public_center=.4,
              public_power=1.3, nominal_noise=.7, alpha=.05, scenarios=SCENARIOS,
              reference_observations_per_hypothesis=8,
              reference_rules=[dict(order=12, phases=24, rule='product', seed=901),
                               dict(order=24, phases=48, rule='product', seed=902),
                               dict(order=32, phases=32, rule='sobol', seed=903)],
              reference_logpdf_max_error=.1, reference_logpdf_rmse=.03,
              identity_tolerance=1e-9, geometry_centers=[.04, .12, .35],
              geometry_relative_deltas=[0., .25, .5, .9],
              new_training_observations=0, per_dimension_retraining=False,
              receiver_calls=0, decoder_calls=0, new_confirmation_stream=False,
              observed_domain='DAFT y with public N/chirps; full IDAFT included in inference cost',
              teacher_domain='frozen N4 Gaussian-control phase-polynomial score regressor',
              calibration='independent nominal actual G0/PDP-marginal null; no test-scene threshold selection',
              scope='conditional common-zero-delay two-path production slice; bounded transfer, not full production')


def _theta(delta, noise_factor=1):
    return np.array([delta, CONFIG['public_center'], math.log(CONFIG['public_power']),
                     math.log(CONFIG['nominal_noise']*noise_factor)])


def infer(y_daft, model, beta):
    """Complete observation-only route. No distribution label or theta input."""
    time_y = inverse_daft(y_daft)
    observed, operation_cost = anchored_features(time_y)
    score = model.predict(observed['phase'])
    return dict(y_time=time_y, features=observed['phase'], predicted_scores=score,
                statistic=score[:, 0]-score[:, 1:]@beta, feature_operations=operation_cost)


def _sample(output, key, n, delta, count, seed, scenario, model, beta, meter, category):
    raw, branch, operations = meter.measure('observation_generation', key, sample_observations,
        n, _theta(delta, scenario['noise_factor']), count, seed,
        **{k:scenario[k] for k in ('input_kind', 'generator', 'gain_prior')})
    meter.rows[-1]['operations'] = operations
    y_daft = meter.measure('simulation_output_transform', key, forward_daft, raw['y_time'],
                           operations=dict(forward_fft_rows=count, chirp_complex_products=2*n*count))
    prediction = meter.measure(category, key, infer, y_daft, model, beta,
                               operations=dict(inverse_fft_rows=count, chirp_complex_products=2*n*count,
                                               new_training_fits=0, matrix_decompositions=0))
    meter.rows[-1]['operations'].update(prediction['feature_operations'])
    meter.rows[-1]['operations']['regression_dot_real_products'] = count*int(model.active.sum())*4
    raw.update(y_daft=y_daft, recovered_time=prediction['y_time'],
               observed_features=prediction['features'], predicted_scores=prediction['predicted_scores'],
               statistic=prediction['statistic'])
    np.savez_compressed(output/(key+'.npz'), **raw)
    metadata = dict(key=key, observations=count, independent_groups=count, seed=list(seed),
                    input_kind=scenario['input_kind'], generator=scenario['generator'],
                    gain_prior=scenario['gain_prior'], theta=raw['theta'].tolist(),
                    gram_eigenvalues=branch['eigenvalues'].tolist(),
                    moments=branch['moments'], platform=bool(branch['platform']),
                    actual_pdp_conditioning='unordered nonnegative Dopplers and two rounded zero delays')
    return prediction, metadata


def reference_diagnostics(output, scenario, y, meter):
    """Known-model density references; never used to tune transfer thresholds."""
    thetas = [_theta(delta, scenario['noise_factor']) for delta in CONFIG['deltas']]
    z, _ = features.canonical_phase(y)
    gaussian = scenario['gain_prior'] == 'gaussian'
    words, word_mass = input_states(4, scenario['input_kind'])
    time_words = words@daft(4).conj()
    centered = time_words-word_mass@time_words
    covariance = (centered.T*word_mass)@centered.conj()
    pseudo = (centered.T*word_mass)@centered
    saved, rows = dict(input_words=words, input_mass=word_mass,
                      input_time_covariance=covariance, input_time_pseudocovariance=pseudo), []
    if gaussian:
        words, mass = input_states(4, scenario['input_kind'])
        reference = meter.measure('reference_setup', scenario['name'], FiniteControl,
                                  words@daft(4).conj(), mass)
        for axis, theta in enumerate(thetas):
            def evaluate(observation):
                return reference.evaluate(observation, theta[0]**2, theta[1],
                                          np.exp(theta[2]), np.exp(theta[3]), score=False)[0]
            for name, observation in [('original', y), ('canonical', z)]:
                saved[f'logpdf_{axis}_{name}'] = meter.measure('exact_gaussian_reference',
                    scenario['name']+f'_{axis}_{name}', evaluate, observation,
                    operations=dict(covariance_matrices=len(words), cholesky_matrices=len(words),
                                    solve_matrices=len(words), component_observation_pairs=len(words)*len(y)))
        error = max(float(np.max(abs(saved[f'logpdf_{axis}_original']-saved[f'logpdf_{axis}_canonical']))) for axis in range(2))
        rows.append(dict(scenario=scenario['name'], reference='analytic Gaussian gain, all legal words',
                         canonical_logpdf_error=error, numerical_identity_pass=error<=CONFIG['identity_tolerance'],
                         quadrature_refinement_applicable=False))
    else:
        results = []
        for index, rule in enumerate(CONFIG['reference_rules']):
            reference = meter.measure('reference_setup', f"{scenario['name']}_{index}", InputPrior,
                n=4, model=scenario['generator'], pdp=scenario['gain_prior'],
                input_kind=scenario['input_kind'], **rule,
                operations=dict(cp1_nodes=rule['order']*rule['phases'], quadrature_rule_constructions=1))
            logpdf = []
            for axis, theta in enumerate(thetas):
                before = reference.cost.copy()
                value = meter.measure('actual_input_reference', f"{scenario['name']}_{index}_{axis}",
                                      reference.logpdf, y, theta)
                meter.rows[-1]['operations'] = {k:reference.cost[k]-before.get(k, 0) for k in reference.cost}
                logpdf.append(value)
                if index == 1:
                    before = reference.cost.copy()
                    canonical = meter.measure('reference_identity_check', f"{scenario['name']}_{axis}",
                                               reference.logpdf, z, theta)
                    meter.rows[-1]['operations'] = {k:reference.cost[k]-before.get(k, 0) for k in reference.cost}
                    saved[f'canonical_logpdf_{axis}'] = canonical
            results.append(np.column_stack(logpdf))
            saved[f'logpdf_rule{index}'] = results[-1]
            saved[f'nodes_rule{index}'] = reference.nodes
            saved[f'weights_rule{index}'] = reference.weights
        maximum = max(float(np.max(abs(results[index]-results[1]))) for index in (0, 2))
        rmse = max(float(np.sqrt(np.mean((results[index]-results[1])**2))) for index in (0, 2))
        identity = max(float(np.max(abs(saved[f'canonical_logpdf_{axis}']-results[1][:, axis]))) for axis in range(2))
        rows.append(dict(scenario=scenario['name'], reference='full legal words; actual PDP mixture; positive CP1 plus analytic phase',
                         max_logpdf_refinement_error=maximum, logpdf_refinement_rmse=rmse,
                         refined=maximum<=CONFIG['reference_logpdf_max_error'] and rmse<=CONFIG['reference_logpdf_rmse'],
                         canonical_logpdf_error=identity, numerical_identity_pass=identity<=CONFIG['identity_tolerance'],
                         interpretation='numerical reference; failures retained, not exact Fisher or rigorous quadrature bound'))
    eigenvalues = np.linalg.eigvalsh(covariance)
    for row in rows:
        row.update(legal_word_count=len(words), input_centered_covariance_eigenvalues=eigenvalues.tolist(),
                   input_centered_covariance_rank=int(np.count_nonzero(eigenvalues>1e-10)),
                   input_pseudocovariance_norm=float(np.linalg.norm(pseudo)))
    np.savez_compressed(output/(scenario['name']+'_references.npz'), y=y, canonical=z, **saved)
    return rows


def geometry_diagnostics(output):
    rows = []
    for n in CONFIG['dimensions']:
        prior = ActualPrior(n=n)
        for center in CONFIG['geometry_centers']:
            for fraction in CONFIG['geometry_relative_deltas']:
                delta = center*fraction
                theta = np.array([delta, center, 0., 0.])
                for generator in ('g0', 'g1'):
                    prior.model = generator
                    branch = prior.branch(theta)
                    independent = dense_gram(prior.system, branch['geometry']['weights'])
                    error = float(np.max(abs(independent-branch['geometry']['gram'])))
                    rows.append(dict(n=n, center=center, delta=delta, generator=generator,
                                     gram_eigenvalues=branch['eigenvalues'].tolist(),
                                     dense_gram_error=error, identity_pass=error<=CONFIG['identity_tolerance'],
                                     active_atoms=branch['active'].tolist(), platform=bool(branch['platform']),
                                     moments=branch['moments'], pdp_limits=branch['pdp']['limits'].tolist(),
                                     conditioning_probability=branch['pdp'].get('event_probability')))
    dump(output/'geometry.json', rows)
    return rows


def calculate(output, model_path):
    meter = Costs()
    try:
        model = meter.measure('frozen_model_load', 'phase', restore_regressor, model_path)
        with np.load(model_path, allow_pickle=False) as saved:
            beta = saved['efficient_beta'].copy()
        if beta.shape != (3,) or not np.isfinite(beta).all() or len(model.mean) != 90:
            raise ValueError('expected frozen N4 phase90 model and three nuisance coefficients')
        calibrations, thresholds, metadata = {}, {}, []
        for n in CONFIG['dimensions']:
            prediction, row = _sample(output, f'calibration_N{n}', n, 0., CONFIG['calibration_per_dimension'],
                CONFIG['seed']+[10, n], SCENARIOS[0], model, beta, meter, 'calibration_inference')
            calibrations[n] = prediction['statistic']
            thresholds[n] = meter.measure('threshold_calibration', str(n), rejection_threshold,
                                           prediction['statistic'], CONFIG['alpha'])
            metadata.append(row)
        dump(output/'thresholds.json', dict(per_dimension={str(k):v for k, v in thresholds.items()},
                                           fixed_n4_threshold=thresholds[4], alpha=CONFIG['alpha']))
        performance, references, representations = [], [], []
        for n in CONFIG['dimensions']:
            for index, scenario in enumerate(SCENARIOS):
                predictions = []
                for hypothesis, delta in enumerate(CONFIG['deltas']):
                    prediction, row = _sample(output, f'N{n}_{scenario["name"]}_H{hypothesis}', n, delta,
                        CONFIG['test_per_hypothesis'], CONFIG['seed']+[20, n, index, hypothesis],
                        scenario, model, beta, meter, 'complete_frozen_inference')
                    predictions.append(prediction)
                    metadata.append(row)
                for calibration, threshold in [('frozen_N4_threshold', thresholds[4]),
                                                ('independent_nominal_N_calibration', thresholds[n])]:
                    metrics = [binomial_interval(int(np.count_nonzero(p['statistic']>threshold)), len(p['statistic'])) for p in predictions]
                    performance.append(dict(n=n, scenario=scenario['name'], calibration=calibration,
                                            threshold=threshold, false_alarm=metrics[0], power=metrics[1],
                                            test_groups_per_hypothesis=CONFIG['test_per_hypothesis'],
                                            composite_null_uniform_control_claim=False))
                y = np.concatenate([p['y_time'] for p in predictions])
                key = f'N{n}_{scenario["name"]}'
                yd = meter.measure('benchmark_input_transform', key, forward_daft, y,
                                   operations=dict(forward_fft_rows=len(y), chirp_complex_products=2*n*len(y)))
                canonical = meter.measure('complete_canonical_representation', key,
                    lambda data: features.canonical_phase(inverse_daft(data)), yd,
                    operations=dict(inverse_fft_rows=len(y), canonical_complex_products=y.size))
                outer = meter.measure('complete_dense_outer_representation', key,
                    lambda data: features.sufficient_outer(inverse_daft(data)), yd,
                    operations=dict(inverse_fft_rows=len(y), outer_complex_products=len(y)*n*n))
                diagnostics = meter.measure('independent_representation_diagnostic', key, phase_diagnostics, y)
                diagnostics.update(n=n, scenario=scenario['name'], observations=len(y),
                                   full_canonical_bytes=canonical[0].nbytes+canonical[1].nbytes,
                                   dense_outer_bytes=outer.nbytes)
                representations.append(diagnostics)
                del outer, canonical
                if n == 4:
                    count = CONFIG['reference_observations_per_hypothesis']
                    reference_y = np.concatenate([p['y_time'][:count] for p in predictions])
                    references.extend(reference_diagnostics(output, scenario, reference_y, meter))
        geometry = meter.measure('deterministic_geometry_checks', 'all', geometry_diagnostics, output)
        dump(output/'observations.json', metadata)
        dump(output/'performance.json', performance)
        dump(output/'references.json', references)
        dump(output/'representations.json', representations)
        comparison = []
        for row in representations:
            key = f'N{row["n"]}_{row["scenario"]}'
            canonical_cost = next(r for r in meter.rows if r['category'] == 'complete_canonical_representation' and r['key'] == key)
            dense_cost = next(r for r in meter.rows if r['category'] == 'complete_dense_outer_representation' and r['key'] == key)
            same_object = row['max_dense_reconstruction_error'] <= CONFIG['identity_tolerance']
            comparison.append(dict(n=row['n'], scenario=row['scenario'], observations=row['observations'],
                canonical_seconds_per_observation=canonical_cost['wall_seconds']/row['observations'],
                dense_seconds_per_observation=dense_cost['wall_seconds']/row['observations'],
                amortization=amortization(0, dense_cost['wall_seconds']/row['observations'],
                                         canonical_cost['wall_seconds']/row['observations'], same_object),
                object='complete representation after IDAFT, not learned-score inference'))
        dump(output/'representation_costs.json', comparison)
        observed = sum(row['observations'] for row in metadata)
        if observed != CONFIG['new_observations']:
            raise RuntimeError('declared independent observation budget disagrees with saved populations')
        return dict(new_observations=observed, independent_groups=observed,
                    calibration_observations=sum(len(x) for x in calibrations.values()),
                    test_observations=observed-sum(len(x) for x in calibrations.values()),
                    scenarios=len(SCENARIOS), dimensions=CONFIG['dimensions'],
                    source_model=str(model_path.relative_to(ROOT)), efficient_beta=beta.tolist(),
                    geometry_cases=len(geometry), geometry_identity_failures=sum(not r['identity_pass'] for r in geometry),
                    density_reference_failures=[r['scenario'] for r in references if r.get('refined') is False],
                    canonical_identity_failures=[r['scenario'] for r in references if not r['numerical_identity_pass']],
                    retained_performance_groups=len(performance), retraining=False,
                    learned_inference_amortization=amortization(0, 0, 0, False),
                    conclusions=['four-anchor frozen-weight transfer is empirical and discards N-4 coordinates',
                                 'full canonical representation preserves a circular likelihood orbit; this is separate from learning',
                                 'each scenario retains its actual false-alarm/power denominators and nominal-calibration limitation',
                                 'no full-likelihood large-N accuracy certificate or production claim'])
    finally:
        dump(output/'costs.json', meter.rows)


def calculate_cost(output, input_stages):
    inventory = stage_cost_inventory(ARTIFACT)
    rows = [row for row in inventory['stages'] if row['stage'] in input_stages]
    documents, blocks = {}, []
    for stage in input_stages:
        folder = ARTIFACT/stage
        for path in sorted(folder.glob('*.json')):
            if 'cost' in path.name or path.name in ('results.json', 'feature_cases.json'):
                documents[str(path.relative_to(ROOT))] = json.loads(path.read_text())
                if path.name == 'costs.json':
                    value = documents[str(path.relative_to(ROOT))]
                    if isinstance(value, list):
                        blocks.extend(dict(stage=stage, source_file=path.name, **row) for row in value)
                    elif isinstance(value, dict):
                        blocks.extend(dict(stage=stage, source_file=path.name, category=category,
                                           source_cost_bundle=details) for category, details in value.items())
                    else:
                        raise ValueError(f'unrecognized costs document: {path}')
    dump(output/'stage_inventory.json', rows)
    dump(output/'source_cost_documents.json', documents)
    dump(output/'measured_blocks.json', blocks)
    return dict(stages=rows, total_reserved_wall_seconds=sum(r['reserved_wall_seconds'] for r in rows),
                total_reserved_observations=sum(r['reserved_observations'] for r in rows),
                actual_recorded_wall_seconds=sum(r['actual_wall_seconds'] for r in rows if r['actual_wall_seconds'] is not None),
                actual_recorded_cpu_seconds=sum(r['actual_cpu_seconds'] for r in rows if r['actual_cpu_seconds'] is not None),
                failed_stages=[r['stage'] for r in rows if r['status'] != 'complete'],
                recorded_blocks=len(blocks), block_times_are_not_added_to_whole_stage_times=True,
                learned_inference_amortization='no same-object equal-accuracy advantage established',
                evidence='raw cost documents retained; missing operation fields are not interpreted as zero',
                new_observations=0, new_nodes=0)


def preloaded_sources():
    # Import the frozen numerical graph before the recorder freezes pool state.
    frozen_components()
    # These two PyTorch namespaces advertise synthetic relative filenames.
    # Their real implementations are torch._ops and torch._classes; resolving
    # the namespace metadata against cwd invents nonexistent project sources.
    virtual = {'torch.ops': '_ops.py', 'torch.classes': '_classes.py'}
    modules = [m for name, m in tuple(sys.modules.items())
               if name not in virtual or getattr(m, '__file__', None) != virtual[name]]
    return sorted({Path(m.__file__).resolve() for m in modules
                   if getattr(m, '__file__', None) and Path(m.__file__).suffix == '.py'
                   and Path(m.__file__).resolve().is_relative_to(ROOT)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    parser.add_argument('--mode', choices=['transfer', 'cost'], default='transfer')
    parser.add_argument('--model-path', type=Path)
    args = parser.parse_args()
    sources = preloaded_sources()
    if args.mode == 'transfer':
        if args.model_path is None:
            parser.error('--model-path is required for transfer')
        model = args.model_path.resolve()
        if not model.is_relative_to(ARTIFACT):
            raise ValueError('transfer model must be a saved model in this task artifact root')
        if json.loads((model.parent/'attempt.json').read_text())['status'] != 'complete':
            raise ValueError('transfer requires a complete immutable source model attempt')
        sources.extend([model, model.parent/'registration.json', model.parent/'attempt.json'])
        with np.load(model, allow_pickle=False) as saved:
            if 'efficient_beta' not in saved:
                raise ValueError('frozen model is missing the saved efficient_beta contract')
        config = dict(CONFIG, model_path=str(model.relative_to(ROOT)), model_sha256=hashes([model]))
        def callback(output):
            return calculate(output, model)
        run(args.stage, config, sources, callback, wall_seconds=900)
    else:
        stages = sorted(p.parent.name for p in ARTIFACT.glob('*/registration.json'))
        for stage in stages:
            sources.extend(p for p in (ARTIFACT/stage).glob('*.json') if p.is_file())
        config = dict(seed=[20261005, 104835, 42], new_observations=0, new_nodes=0,
                      input_stages=stages, receiver_calls=0, decoder_calls=0)
        def callback(output):
            return calculate_cost(output, stages)
        run(args.stage, config, sources, callback, wall_seconds=60)


if __name__ == '__main__':
    main()
