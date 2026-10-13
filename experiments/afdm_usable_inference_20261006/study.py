"""Frozen deterministic stages. Scientific execution belongs on SSH only."""
import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path

import numpy as np

from experiments.afdm_coherent_structure_20261006.geometry import moments, recover
from experiments.afdm_efficient_information.prior_likelihood import daft, pdp_distribution, system_for
from experiments.afdm_shared_channel_20261004.common import dump
from experiments.afdm_shared_channel_20261004.production_prior import frozen_components, normalize_gain
from . import kernels as kr, protocol, thread_binding
from . import model_symmetry
from .config import load_config


def save(output, name, arrays, record):
    record = dict(channel_scope='actual frozen truncated G0, not untruncated physical channel', **record)
    with (output/(name+'.npz')).open('xb') as handle:
        np.savez_compressed(handle, **arrays)
    dump(output/(name+'.json'), record)
    return record


def complex_gains(encoded):
    return np.asarray(encoded, float)@np.array([1., 1j])


def physical_response(n, mu, delta, raw, counter, geo=None):
    if geo is None:
        geo = kr.actual_geometry(n, mu, delta, counter)
    counter.add('gain_normalization')
    gain = normalize_gain(np.asarray(raw)[None, :], geo['gram'])[0]
    counter.add('physical_response')
    h = geo['g0']@gain
    width = 2*system_for(n).k_max_cap+1
    q = geo['weights'][:width]@gain
    gamma = geo['weights'][width//2]*gain
    return dict(geo=geo, raw=np.asarray(raw), gain=gain, H=h, q=q, gamma=gamma)


def counterexample(config, counter):
    """The frozen N5 pair, reconstructed with original physical columns."""
    n, s, p, rho = (config[key] for key in ['N', 'S', 'P', 'rho'])
    if n != 5:
        raise ValueError('this frozen counterexample requires N=5')
    counter.add('N5_counterexample_coefficients')
    h, c, level = np.pi/n, np.cos(np.pi/n), p+1
    a, last = (s+level+2j/c)/c, (s-level+2j/c)/c
    beta = np.array([[rho*a, 1j*(a-rho*last), last],
                     [a, 1j*(rho*a-last), rho*last]])
    q = beta*np.exp(-1j*h*np.array([-1, 0, 1]))
    # One shared scale preserves the equality of both power spectra.
    q /= np.linalg.norm(q[0])
    records = []
    for index in range(2):
        counter.add('three_atom_inverse')
        values = moments(n, q[index])
        nu, qualification = recover(n, values)
        if np.any(nu <= config['branch'][0]) or np.any(nu >= config['branch'][1]):
            raise ValueError('N5 counterexample left its separately frozen branch')
        geo = kr.actual_geometry(n, float(nu.mean()), float(np.diff(nu)[0]/2), counter)
        active = np.flatnonzero(np.any(geo['weights'] != 0, axis=1))
        if not np.array_equal(active, [1, 2, 3]):
            raise ValueError('N5 physical mask is not the original three atoms')
        counter.add('N5_physical_gain_solve')
        raw, _, rank, singular = np.linalg.lstsq(geo['weights'][active], q[index], rcond=None)
        if rank != 2:
            raise ValueError('N5 physical two-column reconstruction lost rank')
        response = physical_response(n, float(nu.mean()), float(np.diff(nu)[0]/2), raw, counter, geo)
        counter.add('N5_original_G0_matrix')
        original = system_for(n).gen_h_daft(q[index], np.zeros(3, int), np.array([-1, 0, 1]))
        transform = daft(n)
        original_time = transform.conj().T@original@transform
        counter.add('N5_PDP_support')
        law = pdp_distribution(n, float(nu.mean()), float(np.diff(nu)[0]/2))
        pdp = law['pdp'][0]
        direction = raw/np.sqrt(pdp)
        direct_h = np.exp(2j*np.pi*np.outer(np.arange(n), [-1, 0, 1])/n)@q[index]
        errors = dict(q=float(np.max(abs(response['q'][active]-q[index]))),
                      H=float(np.max(abs(response['H']-direct_h))),
                      original_G0=float(np.max(abs(original_time-np.diag(direct_h)))),
                      gram_power=float(abs(np.vdot(response['gain'], geo['gram']@response['gain']).real-1)))
        records.append(dict(**response, target_q=q[index], nu=nu, moments=values,
                            qualification=qualification, singular=singular, direct_H=direct_h,
                            original_G0=original, original_G0_time=original_time,
                            pdp=pdp, gaussian_direction=direction,
                            pdp_mass=float(law['weights'][0]), errors=errors))
    return records


def pair_arrays(pair):
    arrays = {}
    for index, record in enumerate(pair):
        for key in ['H', 'q', 'raw', 'gain', 'gamma', 'target_q', 'nu', 'moments',
                    'singular', 'direct_H', 'original_G0', 'original_G0_time', 'pdp', 'gaussian_direction']:
            arrays[f'case{index}_{key}'] = record[key]
        for key in ['weights', 'gram', 'g0']:
            arrays[f'case{index}_{key}'] = record['geo'][key]
    return arrays


def gain_design_diagnostic(mean_power, inverse, n, config, numerics, counter):
    """Observed power fit at inferred nodes; rank/PSD/rank-one are reported."""
    if inverse['status'] != 'ok':
        return {}, dict(status='inverse_unavailable')
    geo = kr.actual_geometry(n, inverse['mu'], inverse['delta'], counter)
    b1, b2 = geo['g0'].T
    cross = b1*b2.conj()
    design = np.column_stack((abs(b1)**2, abs(b2)**2, 2*cross.real, -2*cross.imag, np.ones(n)))
    counter.add('power_design_solve')
    coefficients, _, rank, singular = np.linalg.lstsq(design, mean_power, rcond=config['rank_rtol'])
    u, w, real, imaginary, noise = coefficients
    outer = np.array([[u, real+1j*imaginary], [real-1j*imaginary, w]])
    counter.add('gain_outer_eigendecomposition')
    eigenvalues, vectors = np.linalg.eigh(outer)
    arrays = dict(design=design, coefficients=coefficients, singular=singular,
                  gain_outer=outer, gain_outer_eigenvalues=eigenvalues, inferred_g0=geo['g0'])
    scale = float(np.linalg.norm(mean_power))
    residual = float(np.linalg.norm(design@coefficients-mean_power)/scale) if scale else None
    report = dict(status='diagnostic_only', rank=int(rank), singular_values=singular.tolist(),
                  noise_estimate=float(noise), power_relative_residual=residual,
                  minimum_outer_eigenvalue=float(eigenvalues[0]),
                  tau_estimate=float(np.trace(geo['gram']@outer).real),
                  recovered_object='scaled normalized gain outer product, not original raw gain radius')
    if rank != 5 or eigenvalues[-1] <= 0:
        report['status'] = 'rank_or_positive_power_failure'
        return arrays, report
    gain = np.sqrt(eigenvalues[-1])*vectors[:, -1]
    projected = np.outer(gain, gain.conj())
    rank_one_error = float(np.linalg.norm(outer-projected)/np.linalg.norm(outer))
    arrays.update(best_rank_one_gain=gain, best_rank_one_H=geo['g0']@gain)
    report.update(rank_one_relative_residual=rank_one_error,
                  rank_one_qualified=rank_one_error <= numerics['reconstruction_rtol'],
                  noise_nonnegative=bool(noise >= 0))
    return arrays, report


def algebra(output, study, counter):
    config, numerics = study['algebra'], study['numerics']
    pair = counterexample(config['counterexample'], counter)
    power_error = float(np.max(abs(abs(pair[0]['H'])**2-abs(pair[1]['H'])**2)))
    pair_error = max(power_error, *(max(record['errors'].values()) for record in pair))
    rows = [save(output, 'N5_counterexample', pair_arrays(pair),
                 dict(kind='counterexample', power_error=power_error,
                      cases=[dict(nu=p['nu'].tolist(), errors=p['errors'],
                                  qualification=p['qualification'], pdp_mass=p['pdp_mass']) for p in pair],
                      minimum_H=float(min(np.min(abs(p['H'])) for p in pair)),
                      different_nodes=bool(np.max(abs(pair[0]['nu']-pair[1]['nu'])) > config['node_atol']),
                      passed=bool(pair_error < config['identity_atol']
                                  and np.max(abs(pair[0]['nu']-pair[1]['nu'])) > config['node_atol'])))]
    failures = Counter()
    for n in config['Ns']:
        for delta in config['deltas']:
            geo = kr.actual_geometry(n, config['mu'], delta, counter)
            for gain_label, encoded in config['raw_gains'].items():
                response = physical_response(n, config['mu'], delta, complex_gains(encoded), counter, geo)
                truth_nu = geo['dopplers']
                formula, gamma_factor = kr.imaginary_moment_formula(n, truth_nu, response['gamma'], counter)
                gram_error = float(np.max(abs(geo['g0'].conj().T@geo['g0']/n-geo['gram'])))
                for tau in config['tau_values']:
                    h = np.sqrt(tau)*response['H']
                    for noise in config['noise_variances']:
                        mean_power = abs(h)**2+noise
                        observed = kr.power_moments(mean_power, counter)
                        inverse = kr.infer_power(mean_power, n, study['branch'], numerics, counter)
                        arrays = dict(mean_power=mean_power, H=h, I=observed['I'],
                                      spectrum=observed['spectrum'], I_formula=tau*formula,
                                      raw=response['raw'], gain=np.sqrt(tau)*response['gain'],
                                      weights=geo['weights'], gram=geo['gram'])
                        formula_error = float(np.max(abs(observed['I']-tau*formula)))
                        node_error = None
                        gain_report = dict(status='inverse_unavailable')
                        if inverse['status'] == 'ok':
                            node_error = float(np.max(abs(np.asarray(inverse['nu'])-truth_nu)))
                            gain_arrays, gain_report = gain_design_diagnostic(
                                mean_power, inverse, n, config, numerics, counter)
                            arrays.update(gain_arrays)
                        else:
                            failures[inverse['status']] += 1
                        passed = (node_error is not None and node_error < config['node_atol']
                                  and max(formula_error, gram_error) < config['identity_atol'])
                        rows.append(save(output, f'inverse_N{n}_d{delta}_{gain_label}_t{tau}_s{noise}', arrays,
                            dict(kind='five_atom_inverse', N=n, delta=delta, gain_case=gain_label,
                                 tau=tau, noise=noise, inverse=inverse, node_error=node_error,
                                 formula_error=formula_error, gram_error=gram_error,
                                 gamma_factor=float(tau*gamma_factor), gain_reconstruction=gain_report,
                                 passed=bool(passed))))
    return dict(checks=rows, inverse_failures=dict(failures),
                all_passed=all(row['passed'] for row in rows))


def sensitivity(output, study, counter):
    config, numerics = study['sensitivity'], study['numerics']
    rows, failures = [], Counter()
    perturbations, jacobian_checks, covariance_reports = [], [], []
    for n in config['Ns']:
        for delta in config['deltas']:
            geo = kr.actual_geometry(n, config['mu'], delta, counter)
            zero_row = system_for(n).k_max_cap
            for phase_index, phase in enumerate(config['effective_phases']):
                target = np.array([1., config['effective_amplitude_ratio']*np.exp(1j*phase)])
                raw = target/geo['weights'][zero_row]
                response = physical_response(n, config['mu'], delta, raw, counter, geo)
                power = abs(response['H'])**2
                observed = kr.power_moments(power, counter)
                values, scale = observed['I'], float(np.max(power))
                inverse = kr.infer_power(power, n, study['branch'], numerics, counter)
                expected = 'weak_I4' if phase == 0 else 'ok'
                base_name = f'N{n}_d{delta}_phase{phase_index}'
                arrays = dict(H=response['H'], signal_power=power, raw=raw, gain=response['gain'],
                              effective_gain=response['gamma'], I=values, weights=geo['weights'],
                              gram=geo['gram'])
                if inverse['status'] != 'ok':
                    failures[inverse['status']] += 1
                row = dict(kind='baseline', N=n, delta=delta, effective_phase=phase,
                           inverse=inverse, expected_status=expected, passed=inverse['status'] == expected)
                if inverse['status'] == 'ok':
                    jacobian = kr.inverse_jacobian(inverse, n, counter)
                    arrays['Jacobian'] = jacobian
                    for step_index, relative_step in enumerate(config['jacobian_relative_steps']):
                        derivatives, results = [], []
                        for coordinate in range(3):
                            step = relative_step*abs(values[coordinate])
                            direction = np.eye(3)[coordinate]*step
                            pair = [kr.algebraic_inverse(values+sign*direction, n, study['branch'], numerics,
                                                       scale=scale, counter=counter) for sign in (1, -1)]
                            results.append(dict(coordinate=coordinate, step=float(step), inverse=pair))
                            if step > 0 and all(item['status'] == 'ok' for item in pair):
                                derivatives.append((np.asarray(pair[0]['nu'])-pair[1]['nu'])/(2*step))
                            else:
                                derivatives.append(None)
                        error = None
                        derivative_arrays = {}
                        if all(value is not None for value in derivatives):
                            finite_difference = np.column_stack(derivatives)
                            error = float(np.linalg.norm(finite_difference-jacobian)/np.linalg.norm(jacobian))
                            derivative_arrays['finite_difference'] = finite_difference
                        report = dict(kind='jacobian', N=n, delta=delta, effective_phase=phase,
                                      relative_step=relative_step, probes=results, relative_error=error,
                                      passed=bool(error is not None and error < config['jacobian_rtol']))
                        jacobian_checks.append(save(output, base_name+f'_jac{step_index}',
                                                    dict(I=values, analytic=jacobian, **derivative_arrays), report))
                    for noise in config['noise_variances']:
                        covariance = kr.oracle_moment_covariance(power, noise, counter)
                        counter.add('delta_method_covariance')
                        node_covariance = jacobian@covariance@jacobian.T
                        eigenvalues = np.linalg.eigvalsh(covariance)
                        if np.any(np.diag(node_covariance) < 0) or not np.isfinite(node_covariance).all():
                            raise FloatingPointError('oracle-local variance is negative or nonfinite')
                        node_mse_coefficient = float(np.trace(node_covariance)/2)
                        predicted_t = node_mse_coefficient/config['target_node_rmse']**2
                        report = dict(kind='oracle_local_delta_method', N=n, delta=delta,
                                      effective_phase=phase, noise=noise,
                                      target_node_rmse=config['target_node_rmse'],
                                      node_rmse_definition='sqrt(mean of the two ordered-node squared errors)',
                                      asymptotic_mean_node_mse_times_T=node_mse_coefficient,
                                      predicted_T_for_target_rmse=predicted_t,
                                      moment_covariance_eigenvalues=eigenvalues.tolist(),
                                      finite_sample_evidence=False)
                        covariance_reports.append(save(output, base_name+f'_noise{noise}',
                            dict(signal_power=power, I=values, moment_covariance_T1=covariance,
                                 Jacobian=jacobian, node_covariance_times_T=node_covariance), report))
                rows.append(save(output, base_name, arrays, row))
                for perturbation_scale in config['moment_perturbation_scales']:
                    for direction_index, direction in enumerate(config['directions']):
                        shift = perturbation_scale*np.asarray(direction)
                        perturbed = kr.algebraic_inverse(values+shift, n, study['branch'], numerics,
                                                        scale=scale, counter=counter)
                        perturbed = kr.qualify_mask(perturbed, n, counter)
                        error = None
                        if perturbed['status'] == 'ok':
                            error = float(np.sqrt(np.mean((np.asarray(perturbed['nu'])-geo['dopplers'])**2)))
                        else:
                            failures[perturbed['status']] += 1
                        report = dict(kind='deterministic_moment_perturbation', N=n, delta=delta,
                                      effective_phase=phase, absolute_moment_shift=perturbation_scale,
                                      direction=list(direction), inverse=perturbed,
                                      ordered_node_rmse=error, random_observation=False)
                        perturbations.append(save(output, base_name+f'_shift{perturbation_scale}_{direction_index}',
                                                  dict(I=values, shift=shift, perturbed_I=values+shift), report))
    return dict(checks=rows, jacobian_checks=jacobian_checks,
                oracle_local_delta_method=covariance_reports, perturbations=perturbations,
                failures=dict(failures), perturbation_count=len(perturbations),
                all_passed=all(row['passed'] for row in rows+jacobian_checks),
                interpretation='fixed moment perturbations and oracle-local delta-method, not finite-sample performance')


def contrast(output, study, counter):
    config = study['contrast']
    n = config['N']
    pair = counterexample(config, counter)
    h = pair[0]['H']
    states = np.asarray(list(product(range(4), repeat=n)), dtype=int)
    if len(states) != config['qpsk_state_count']:
        raise ValueError('complete QPSK state count differs from frozen allocation')
    counter.add('enumerated_qpsk_states', len(states))
    symbols = np.exp(1j*(np.pi/4+np.pi/2*states))
    counter.add('qpsk_channel_responses', len(states))
    actual_x = symbols@daft(n).conj()
    fft_x = kr.phase_rows(symbols, n)
    y = actual_x*h
    transform_error = float(np.max(abs(actual_x-fft_x)))
    theta = np.angle(h)
    candidates = dict(true=theta, paired_ambiguous=np.angle(pair[1]['H']),
                      true_character_1=theta+2*np.pi*np.arange(n)/n,
                      true_plus_fixed_offset=theta+np.asarray(config['fixed_phase_offset']))
    if list(candidates) != config['candidate_phases']:
        raise ValueError('contrast candidates differ from frozen ordered set')
    rows = [save(output, 'N5_QPSK_inputs',
                 dict(states=states, symbols=symbols, actual_x=actual_x, fft_x=fft_x, Y=y, **pair_arrays(pair)),
                 dict(kind='inputs', transform_error=transform_error,
                      qpsk_states=len(states), new_random_observations=0,
                      passed=transform_error < config['identity_atol']))]

    # Independent complete-state power covariance; Gaussian increments are exact.
    counter.add('complete_state_power_covariance')
    powers = abs(y)**2
    centered = powers-powers.mean(axis=0)
    covariance0 = centered.T@centered/len(states)
    signal_power = abs(h)**2
    for noise in config['noise_variances']:
        counter.add('power_covariance_formula')
        enumerated = covariance0+np.diag(2*noise*signal_power+noise**2)
        formula = np.diag((signal_power+noise)**2)-np.outer(signal_power, signal_power)/n
        error = float(np.max(abs(enumerated-formula)))
        rows.append(save(output, f'power_covariance_noise{noise}',
                         dict(enumerated=covariance0, integrated=enumerated, formula=formula),
                         dict(kind='power_covariance', noise=noise, error=error,
                              passed=error < config['identity_atol'])))

    for amplitude_index, amplitude in enumerate(config['common_amplitudes']):
        amplitude = np.asarray(amplitude)
        cached = {}
        for label, candidate in candidates.items():
            sample = kr.quartic_samples(y, candidate, amplitude, counter=counter)
            cached[label] = sample['score']
            population_gradient = sample['gradient'].mean(axis=0)
            fixed = kr.quartic_samples(y[:1], candidate, amplitude, counter=counter)
            numerical_population, numerical_fixed = [], []
            for step in config['gradient_steps']:
                population_fd, fixed_fd = [], []
                for coordinate in range(n):
                    offset = np.eye(n)[coordinate]*step
                    score_plus = kr.population_quartic(h, candidate+offset, amplitude, 0., counter)['score']
                    score_minus = kr.population_quartic(h, candidate-offset, amplitude, 0., counter)['score']
                    population_fd.append((score_plus-score_minus)/(2*step))
                    single_plus = kr.quartic_samples(y[:1], candidate+offset, amplitude,
                                                     gradient=False, counter=counter)['score'][0]
                    single_minus = kr.quartic_samples(y[:1], candidate-offset, amplitude,
                                                      gradient=False, counter=counter)['score'][0]
                    fixed_fd.append((single_plus-single_minus)/(2*step))
                numerical_population.append(population_fd)
                numerical_fixed.append(fixed_fd)
            population_gradient_error = float(np.max(abs(np.asarray(numerical_population)-population_gradient)))
            fixed_gradient_error = float(np.max(abs(np.asarray(numerical_fixed)-fixed['gradient'][0])))
            gauge_error = float(np.max(abs(sample['gradient'].sum(axis=1))))
            for noise in config['noise_variances']:
                predicted = kr.population_quartic(h, candidate, amplitude, noise, counter)
                variance = predicted['noise_output_variance']
                integrated_scores = sample['score']+4*variance*sample['energy']+2*n*variance**2
                score_error = float(abs(integrated_scores.mean()-predicted['score']))
                tolerance = config['identity_atol']
                bounds_passed = (predicted['excess']+tolerance >= predicted['lower_bound']
                                 and predicted['excess']-tolerance <= predicted['upper_bound'])
                row = dict(kind='quartic', amplitude_index=amplitude_index, candidate=label,
                           noise=noise, population=predicted, enumerated_score=float(integrated_scores.mean()),
                           score_error=score_error, population_gradient_error=population_gradient_error,
                           fixed_sample_gradient_error=fixed_gradient_error, gauge_error=gauge_error,
                           passed=bool(score_error < tolerance and bounds_passed
                                       and max(population_gradient_error, fixed_gradient_error, gauge_error)
                                       < config['gradient_atol']))
                rows.append(save(output, f'quartic_a{amplitude_index}_{label}_noise{noise}',
                                 dict(theta=candidate, amplitude=amplitude, scores=sample['score'],
                                      gradients=sample['gradient'], integrated_scores=integrated_scores,
                                      population_gradient=population_gradient,
                                      population_gradient_fd=np.asarray(numerical_population),
                                      fixed_sample_gradient=fixed['gradient'][0],
                                      fixed_sample_gradient_fd=np.asarray(numerical_fixed)), row))
        gap = float(np.mean(cached['paired_ambiguous']-cached['true']))
        invariant_error = float(np.max(abs(cached['true_character_1']-cached['true'])))
        rows.append(save(output, f'candidate_gap_a{amplitude_index}',
                         dict(paired_difference=cached['paired_ambiguous']-cached['true'],
                              character_difference=cached['true_character_1']-cached['true']),
                         dict(kind='candidate_gap', amplitude_index=amplitude_index,
                              positive_population_gap=gap, character_invariance_error=invariant_error,
                              passed=gap > 0 and invariant_error < config['identity_atol'])))
    return dict(checks=rows, all_passed=all(row['passed'] for row in rows),
                scope='actual frozen G0, complete QPSK enumeration, Gaussian noise integrated analytically')


def preload():
    frozen_components()
    # Numerical dependencies must all be loaded before admission freezes pools.
    return thread_binding.blas_binding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['algebra', 'sensitivity', 'contrast', 'symmetry'])
    parser.add_argument('--stage')
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--wall-seconds', type=int, default=600)
    parser.add_argument('--print-config', action='store_true')
    parser.add_argument('--print-imports', action='store_true')
    args = parser.parse_args()
    if args.print_config:
        print(json.dumps(load_config() if args.config is None else load_config(args.config), indent=2))
        return
    preload()
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    if args.phase is None or not args.stage or args.artifact_root is None or args.config is None:
        parser.error('--phase, --stage, --artifact-root and --config are required')
    config = load_config(args.config)
    scope = ('frozen G0 versus full/G1 modulation symmetry; no receiver claim'
             if args.phase == 'symmetry'
             else 'actual frozen truncated G0, not untruncated physical channel')
    registered = dict(study=config, phase=args.phase, seed=config['seed'],
                      new_geometry_probes=config['reservations'][args.phase], new_observations=0,
                      receiver_calls=0, decoder_calls=0, new_confirmation_stream=False,
                      channel_scope=scope)

    def calculate(output):
        counter = kr.EvaluationCounter(registered['new_geometry_probes'])
        try:
            function = {'algebra': algebra, 'sensitivity': sensitivity, 'contrast': contrast,
                        'symmetry': model_symmetry.calculate}[args.phase]
            result = function(output, config, counter)
            result['channel_scope'] = registered['channel_scope']
            dump(output/'scientific_checks.json', result)
            if not result['all_passed']:
                raise AssertionError('deterministic checks failed; all completed records retained')
        except BaseException:
            dump(output/'kernel_counts_partial.json', counter.report())
            raise
        counts = counter.report()
        dump(output/'kernel_counts.json', counts)
        return dict(**result, kernel_counts=counts, geometry_probes=counts['total'],
                    new_observations=0, receiver_calls=0, decoder_calls=0,
                    accounting=('logical kernel outputs before evaluation: geometry/moment transform/'
                                'complete inverse/covariance/Jacobian/solve each one; QPSK scores and '
                                'gradient vectors each one per state; scalar root calls additionally '
                                'recorded as operation diagnostics; neither FLOPs nor random observations'))

    protocol.run(args.stage, registered, [args.config.resolve()], calculate,
                 artifact_root=args.artifact_root, wall_seconds=args.wall_seconds)


if __name__ == '__main__':
    main()
