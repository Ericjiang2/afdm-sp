"""COLLAPSED-MATH-01: fixed saved fixtures, no receiver or communication draw.

--print-imports and --print-config perform import-only preparation. All actual
mathematics belongs to a separately admitted 120-second engineering stage.
"""
import argparse
import json
from pathlib import Path
import time
import unittest

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from experiments.afdm_sp_fractional_20261007.moments import PathMoments, real_result
from . import continuous, engineering, protocol, quadrature_diagnostic as saved, runtime, test_core
from .collapsed_gain import CollapsedGain
from .gaussian_gain import solve_gain

SOURCE_ATTEMPT = Path('/data/guoyikun/afdm_sp_fractional_20261007_math01_c639a4b0/'
                      'artifact/execution/MATH-01')
SIZES = (8, 16, 1024)
OFFSETS = (-2e-4, -1e-4, 0., 1e-4, 2e-4)
SIGMA2 = .7
FIXTURES = [
    'DataAndGainContracts.test_full_gain_covariance_solves_original_precision',
    'DataAndGainContracts.test_incremental_coefficients_equal_fresh_canonical_recalculation',
    'DataAndGainContracts.test_actual_objective_and_equation8_for_each_accepted_step',
]


def input_paths(source=SOURCE_ATTEMPT):
    source = Path(source).resolve()
    if source != SOURCE_ATTEMPT:
        raise ValueError('collapsed diagnostic requires the fixed original MATH attempt')
    return engineering.input_paths(source)


def configuration():
    return dict(seed='none', new_observations=0, independent_blocks=0, receiver_calls=0,
                receiver_boundary_rejection_calls=0, receiver_payload_executions=0,
                decoder_calls=0, backend_fixture_calls=0, new_geometry_probes=0,
                diagnostic='collapsed_gain_fixed_soft_data', source_attempt=str(SOURCE_ATTEMPT),
                cases=[dict(n=n, p=p) for n in SIZES for p in (2, 1)],
                noise_variance=SIGMA2, working_gain_prior='CN(0,I/P)',
                data_moments='saved MATH Pd=.55 mean/variance; no receiver Pd=.5 substitution',
                dopplers='first saved node in each retained path', offsets=list(OFFSETS),
                schur_candidates=45, canonical_full_references=45, gauge_full_solves=45,
                analytic_derivatives=9, derivative_request='offset zero only',
                finite_difference_pairs=18, finite_difference_steps=[1e-4, 2e-4],
                source_preparations=51, path_moment_builds=51, initial_full_statistics=6,
                schur_coordinate_preparations=9, schur_nonempty_block_solves=6,
                schur_empty_blocks=3, schur_candidate_vector_solves=30,
                shared_solver_calls=96, shared_solver_identity_rhs_columns=156,
                shared_solver_matched_rhs_columns=96, shared_solver_triangular_calls=192,
                schur_candidate_triangular_calls=60,
                diagnostic_cubic_checks=dict(schur_residual_matrix_products=45, schur_residual_matmul_terms=390,
                    derivative_trace_matrix_products=9, derivative_trace_matmul_terms=51,
                    shared_solver_residual_matrix_products=96, shared_solver_residual_matmul_terms=792,
                    direct_entropy_gram_matrix_products=90, direct_entropy_gram_matmul_terms=510,
                    gauge_dense_matrix_products=270, gauge_dense_matmul_terms=1530),
                cost_scope='full candidate diagnostics include O(P^3) covariance residual and trace checks',
                physical_channel_constructions=6, physical_basis_apply_calls=2096,
                physical_mean_apply_calls=6, physical_reference='stream basis only at P2 base; P1 reuses first column',
                direct_trace_entropy_evaluations=90, covariance_slogdet_calls=90,
                gaussian_ratio_checks=3, gaussian_2x2_inverse_calls=3,
                gaussian_scope='equal-weight local Fisher/MF illustration; not SP posterior variance',
                fixtures=FIXTURES, fixture_accounting='separate from all mathematical counts above',
                tolerance=dict(n8=1e-10, n16=1e-10, n1024=1e-9, precision_residual=1e-10,
                               derivatives=1e-5, schur_prior_lower_bound='1e-10*max(1,P)'),
                normalized_error='norm(actual-reference)/max(1,norm(reference))',
                gauge='D=diag(exp(i*pi*(N-1)/N*nu)); explicit algebraic coordinate check',
                wall_cap_seconds=120, cpu_cap_seconds=120,
                whole_process_timeout_seconds=150, termination_grace_seconds=10,
                scope='mathematical identities on six old fixtures; no receiver benefit claim')


def _check(name, actual, expected, tolerance):
    actual, expected = np.asarray(actual), np.asarray(expected)
    if actual.shape != expected.shape:
        raise ValueError('comparison shape mismatch: '+name)
    continuous.finite(actual, name+' actual')
    continuous.finite(expected, name+' reference')
    error = float(np.linalg.norm(actual-expected)/max(1., np.linalg.norm(expected)))
    return dict(name=name, normalized_error=error, tolerance=tolerance, passed=error <= tolerance)


def load_inputs(source, guard):
    hashes = {str(path): saved._bound_sha(path, guard) for path in input_paths(source)}
    attempt = json.loads((source/'attempt.json').read_text())
    if attempt['status'] != 'complete' or attempt['exit_code'] != 0:
        raise ValueError('original MATH attempt did not complete')
    for path in input_paths(source)[1:]:
        if attempt['artifact_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('original MATH artifact hash mismatch')
    records = []
    for n in SIZES:
        report = json.loads((source/f'n{n}_checks.json').read_text())
        for role in ('inputs', 'arrays'):
            name = f'n{n}_{role}.npz'
            if report[role+'_file'] != name or report[role+'_sha256'] != hashes[str(source/name)]:
                raise ValueError('saved MATH report identity mismatch')
            saved._bound_sha(source/name, guard)
        inputs = engineering._read_npz(source/f'n{n}_inputs.npz')
        arrays = engineering._read_npz(source/f'n{n}_arrays.npz')
        if (arrays['delays'].shape != (2,) or arrays['doppler_nodes'].ndim != 2 or
                arrays['doppler_nodes'].shape[0] != 2 or arrays['doppler_nodes'].shape[1] < 1):
            raise ValueError('saved MATH geometry is not the fixed two-path fixture')
        if any(inputs[key].shape != (n,) for key in ('y', 'pilot', 'data_mean', 'data_variance')):
            raise ValueError('saved MATH input dimensions differ')
        bases = arrays['doppler_nodes'][:, 0]
        if any(np.any(abs(bases+offset) > 3) for offset in OFFSETS):
            raise ValueError('registered base or probe leaves [-3,3]; no clipping allowed')
        records.append(dict(n=n, inputs=inputs, arrays=arrays))
        guard.check()
    return records, hashes


def make_moments(data, p, dopplers, counts, work):
    arrays, inputs, n = data['arrays'], data['inputs'], data['n']
    continuous.count(counts, 'path_moment_builds_started')
    op = PathMoments(n, float(arrays['c1']), float(arrays['c2']), arrays['delays'][:p],
                     np.asarray(dopplers)[:, None], np.ones((p, 1)),
                     arrays['gain_mean'][:p], arrays['gain_covariance'][:p, :p])
    work.append(op.work_counts)
    continuous.count(counts, 'path_moment_builds_completed')
    continuous.count(counts, 'path_moment_phase_entries', p*n)
    continuous.count(counts, 'source_preparations')
    source = op.prepare_source(inputs['pilot'], inputs['data_mean'], inputs['data_variance'])
    return op, source


def physical_reference(rt, data, partial, guard):
    """One streamed basis vector at a time; never retain an N-by-N operator."""
    start, cpu = time.perf_counter(), time.process_time()
    n, inputs, arrays = data['n'], data['inputs'], data['arrays']
    counts = partial['counts']
    channels = []
    for i in range(2):
        continuous.count(counts, 'physical_channel_constructions')
        channels.append(rt.physical.Channel(n, float(arrays['c1']), float(arrays['c2']),
            arrays['delays'][i:i+1], arrays['doppler_nodes'][i:i+1, 0], np.ones(1, complex)))
    mean_responses = np.zeros((n, 2), complex)
    partial['mean_responses'] = mean_responses
    x = inputs['pilot']+inputs['data_mean']
    for i, channel in enumerate(channels):
        continuous.count(counts, 'physical_mean_apply_started')
        mean_responses[:, i] = channel.apply(x)
        continuous.count(counts, 'physical_mean_apply_completed')
        partial['mean_columns_completed'] = i+1
        guard.check()
    variance_gram = np.zeros((2, 2), complex)
    partial['variance_gram'] = variance_gram
    basis = np.zeros(n, complex)
    for index in range(n):
        if index:
            basis[index-1] = 0.
        basis[index] = 1.
        partial['basis_index_started'] = index
        responses = []
        for channel in channels:
            continuous.count(counts, 'physical_basis_apply_started')
            responses.append(channel.apply(basis))
            continuous.count(counts, 'physical_basis_apply_completed')
            partial['last_basis_responses'] = responses
            guard.check()
        response = np.column_stack(responses)
        variance_gram += inputs['data_variance'][index]*(response.conj().T@response)
        continuous.count(counts, 'physical_variance_inner_product_terms', 4*n)
        partial['basis_indices_completed'] = index+1
    gram = mean_responses.conj().T@mean_responses+variance_gram
    matched = mean_responses.conj().T@inputs['y']
    continuous.finite(gram, 'independent physical Gram')
    continuous.finite(matched, 'independent physical matched vector')
    partial.update(gram=gram, matched=matched, status='completed',
                   seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu,
                   dense_operator_saved=False)
    return partial


def full_reference(data, p, dopplers, original_op, counts, solver_counts, work, result):
    continuous.count(counts, 'canonical_references_started')
    op, source = make_moments(data, p, dopplers, counts, work)
    if op is original_op or source.owner is not op:
        raise RuntimeError('full reference must own an independent canonical source')
    gram, matched = op.gain_statistics(data['inputs']['y'], source)
    result.update(gram=gram, matched=matched, source_work_counts=op.work_counts)
    continuous.count(counts, 'canonical_reference_statistics')
    continuous.count(counts, 'canonical_reference_pair_terms', p*(p-1)*data['n'])
    mean, covariance, detail = solve_gain(gram, matched, SIGMA2, solver_counts, with_logdet=True)
    score = float(real_result(np.vdot(matched/SIGMA2, mean), 'full collapsed score'))-detail['logdet_precision']
    continuous.count(counts, 'canonical_references_completed')
    result.update(status='completed', mean=mean, covariance=covariance,
                  reduced_score=score, solve=detail, independent_source_owner=True)
    return result


def trace_entropy(gram, matched, mean, covariance, counts):
    continuous.count(counts, 'trace_entropy_evaluations')
    p = len(mean)
    second = covariance+np.outer(mean, mean.conj())
    continuous.count(counts, 'covariance_slogdet_calls')
    sign, logdet = np.linalg.slogdet(covariance)
    if abs(sign-1) > 1e-10 or not np.isfinite(logdet):
        raise continuous.CoreFailure('invalid covariance determinant in direct entropy')
    continuous.count(counts, 'direct_entropy_gram_matrix_products')
    continuous.count(counts, 'direct_entropy_gram_matmul_terms', p**3)
    terms = dict(linear=float(2*np.vdot(matched/SIGMA2, mean).real),
                 likelihood_quadratic=float(real_result(np.trace(gram@second)/SIGMA2, 'likelihood trace')),
                 prior_quadratic=float(real_result(p*np.trace(second), 'prior trace')),
                 entropy_logdet=float(logdet), gaussian_dimension=p)
    terms['reduced_elbo'] = (terms['linear']-terms['likelihood_quadratic']-terms['prior_quadratic']+
                             terms['entropy_logdet']+p)
    continuous.finite(list(terms.values()), 'direct trace/entropy ELBO')
    return terms


def gauge_check(n, dopplers, candidate, reference, counts, solver_counts, tolerance, result):
    continuous.count(counts, 'gauge_rotations_started')
    c = np.pi*(n-1)/n
    rotation = np.diag(np.exp(1j*c*dopplers))
    continuous.count(counts, 'gauge_dense_matrix_products', 2)
    continuous.count(counts, 'gauge_dense_matmul_terms', 2*len(dopplers)**3)
    rotated_gram = rotation@reference['gram']@rotation.conj().T
    rotated_matched = rotation@reference['matched']
    result.update(c=float(c), D=rotation, gram=rotated_gram, matched=rotated_matched)
    mean, covariance, solved = solve_gain(rotated_gram, rotated_matched, SIGMA2,
                                          solver_counts, with_logdet=True)
    score = float(real_result(np.vdot(rotated_matched/SIGMA2, mean), 'gauge score'))-solved['logdet_precision']
    continuous.count(counts, 'gauge_dense_matrix_products', 4)
    continuous.count(counts, 'gauge_dense_matmul_terms', 4*len(dopplers)**3)
    checks = [
        _check('gauge_R', rotated_gram, rotation@candidate['gram']@rotation.conj().T, tolerance),
        _check('gauge_f', rotated_matched, rotation@candidate['matched'], tolerance),
        _check('gauge_m', mean, rotation@candidate['mean'], tolerance),
        _check('gauge_C', covariance, rotation@candidate['covariance']@rotation.conj().T, tolerance),
        _check('gauge_score', score, candidate['reduced_score'], tolerance),
        _check('gauge_precision_residual', solved['solve_residual'], 0., 1e-10),
    ]
    continuous.count(counts, 'gauge_rotations_completed')
    result.update(status='completed', mean=mean, covariance=covariance, reduced_score=score, solve=solved,
                  checks=checks, physical_calls=0)
    return result


def case_checks(candidate, reference, p, coordinate, counts, tolerance):
    checks = [
        _check('R_column', candidate['column']['gram_column'], reference['gram'][:, coordinate], tolerance),
        _check('b_i', candidate['b_i'], reference['matched'][coordinate]/SIGMA2, tolerance),
        _check('full_R', candidate['gram'], reference['gram'], tolerance),
        _check('full_f', candidate['matched'], reference['matched'], tolerance),
        _check('full_m', candidate['mean'], reference['mean'], tolerance),
        _check('full_C', candidate['covariance'], reference['covariance'], tolerance),
        _check('full_score', candidate['reduced_score'], reference['reduced_score'], tolerance),
        _check('logdet_precision', candidate['logdet_precision'], reference['solve']['logdet_precision'], tolerance),
        _check('schur_precision_residual', candidate['precision_residual'], 0., 1e-10),
        _check('full_precision_residual', reference['solve']['solve_residual'], 0., 1e-10),
    ]
    checks.append(dict(name='schur_prior_lower_bound', s=candidate['s'], lower_bound=p,
                       tolerance=1e-10*max(1, p), passed=candidate['s'] >= p-1e-10*max(1, p)))
    for name, value in candidate['hermitian_errors'].items():
        checks.append(_check('Hermitian_'+name, value, 0., 1e-10))
    direct = trace_entropy(candidate['gram'], candidate['matched'], candidate['mean'], candidate['covariance'], counts)
    reference_direct = trace_entropy(reference['gram'], reference['matched'], reference['mean'], reference['covariance'], counts)
    for name in direct:
        checks.append(_check('direct_'+name, direct[name], reference_direct[name], tolerance))
    checks.append(_check('schur_vs_direct_ELBO', candidate['reduced_score'], direct['reduced_elbo'], tolerance))
    checks.append(_check('full_vs_direct_ELBO', reference['reduced_score'], reference_direct['reduced_elbo'], tolerance))
    if p == 1:
        diagonal = p+reference['gram'][0, 0].real/SIGMA2
        reduced = abs(reference['matched'][0]/SIGMA2)**2/diagonal-np.log(diagonal)
        checks.extend([_check('P1_s', candidate['s'], diagonal, tolerance),
                       _check('P1_t', candidate['t'], reference['matched'][0]/SIGMA2, tolerance),
                       _check('P1_J', candidate['J'], reduced, tolerance)])
    if candidate['derivative'] is not None:
        checks.append(_check('Schur_vs_envelope_derivative', candidate['derivative']['J'],
                             candidate['derivative']['envelope'], tolerance))
    return checks, dict(candidate=direct, reference=reference_direct)


def run_case(rt, output, data, p, physical, partial, guard):
    n = data['n']
    label = f'n{n}_p{p}'
    tolerance = 1e-9 if n == 1024 else 1e-10
    counts, work = partial['counts'], partial['path_work']
    dopplers = data['arrays']['doppler_nodes'][:p, 0].copy()
    op, source = make_moments(data, p, dopplers, counts, work)
    model = CollapsedGain(op, source, data['inputs']['y'], SIGMA2, partial['core_counts'])
    partial.update(base_gram=model.gram, base_matched=model.matched,
                   base_dopplers=dopplers, preparations=model.preparations)
    checks = partial['checks']
    checks.extend([_check('base_R_physical', model.gram, physical['gram'][:p, :p], tolerance),
                   _check('base_f_physical', model.matched, physical['matched'][:p], tolerance)])
    for coordinate in range(p):
        prepared = model.prepare(coordinate)
        coordinate_rows = []
        for index, offset in enumerate(OFFSETS):
            entry = dict(coordinate=coordinate, offset=offset, status='started')
            partial['candidates'].append(entry)
            name = f'{label}_i{coordinate}_q{index}'
            dump(output/f'{name}_started.json', dict(n=n, p=p, coordinate=coordinate, offset=offset))
            guard.check()
            candidate = prepared.evaluate(float(dopplers[coordinate]+offset), derivative=offset == 0.)
            entry['candidate'] = candidate
            trial = dopplers.copy()
            trial[coordinate] += offset
            entry['reference'] = dict(status='started')
            reference = full_reference(data, p, trial, op, counts, partial['reference_solver_counts'], work,
                                       entry['reference'])
            candidate_checks, direct = case_checks(candidate, reference, p, coordinate, counts, tolerance)
            entry['direct_trace_entropy'] = direct
            entry['gauge'] = dict(status='started')
            gauge = gauge_check(n, trial, candidate, reference, counts, partial['gauge_solver_counts'], tolerance,
                                entry['gauge'])
            entry.update(status='completed', checks=candidate_checks+gauge['checks'])
            checks.extend(entry['checks'])
            coordinate_rows.append(entry)
            save_start = time.perf_counter()
            entry['raw_sha256'] = runtime.save_new(rt, output/f'{name}.npz', entry,
                dict(role='collapsed_math_candidate', n=n, p=p, coordinate=coordinate, offset=offset))
            entry['save_seconds'] = time.perf_counter()-save_start
            guard.check(files=True, threads=True)
        analytic = coordinate_rows[2]['candidate']['derivative']['J']
        for step, lo, hi in ((1e-4, 1, 3), (2e-4, 0, 4)):
            difference = ((coordinate_rows[hi]['reference']['reduced_score']-
                           coordinate_rows[lo]['reference']['reduced_score'])/(2*step))
            row = dict(coordinate=coordinate, step=step, analytic=analytic, finite_difference=difference,
                       check=_check('derivative_finite_difference', analytic, difference, 1e-5))
            partial['finite_differences'].append(row)
            checks.append(row['check'])
            continuous.count(counts, 'finite_difference_pairs')
    partial['status'] = 'completed'
    partial['passed'] = all(row['passed'] for row in checks)


def gaussian_ratio(n, counts):
    continuous.count(counts, 'gaussian_ratio_checks')
    time_coordinate = 2*np.pi*np.arange(n)/n
    design = np.column_stack((np.ones(n), time_coordinate))
    fisher = design.T@design
    continuous.count(counts, 'gaussian_2x2_inverse_calls')
    inverse = np.linalg.inv(fisher)
    mf_variance = 1/fisher[1, 1]
    ratio = float(mf_variance/inverse[1, 1])
    expected = (n+1)/(2*(2*n-1))
    return dict(n=n, fisher=fisher, inverse_fisher=inverse, mf_variance=float(mf_variance),
                marginal_variance=float(inverse[1, 1]), ratio=ratio, expected_ratio=expected,
                check=_check('Gaussian_Fisher_MF_ratio', ratio, expected, 1e-9 if n == 1024 else 1e-10),
                scope='equal-weight local Gaussian illustration, not actual SP posterior variance')


def run_fixtures(rt, output, guard):
    reports = []
    for index, label in enumerate(FIXTURES):
        start = time.perf_counter()
        dump(output/f'fixture_{index}_started.json', dict(fixture=label))
        cls, method = label.split('.')
        result = unittest.TestResult()
        with runtime.observe_operations(rt, guard.check) as operations:
            with runtime.observe_component_evidence(rt) as components:
                getattr(test_core, cls)(method).run(result)
        digest = runtime.save_new(rt, output/f'fixture_{index}_evidence.npz',
            dict(operations=operations, components=components), dict(role='collapsed_original_fixture', fixture=label))
        report = dict(fixture=label, passed=result.wasSuccessful(), tests_run=result.testsRun,
                      errors=[value for _, value in result.errors], failures=[value for _, value in result.failures],
                      evidence_sha256=digest, seconds=time.perf_counter()-start,
                      scope='original deterministic component fixture; separate operation ledger')
        dump(output/f'fixture_{index}_complete.json', report)
        reports.append(report)
        guard.check(files=True, threads=True)
    return reports


def calculate(rt, output, guard, source):
    partial = dict(status='started', physical=[], cases=[], gaussian=[], counts={})
    try:
        data_sets, hashes = load_inputs(source, guard)
        dump(output/'input_identity.json', dict(source=str(source), sha256=hashes))
        with runtime.observe_operations(rt, guard.check) as operations:
            partial['mathematical_operations'] = operations
            for data in data_sets:
                n = data['n']
                physical = dict(n=n, status='started', counts={})
                partial['physical'].append(physical)
                dump(output/f'n{n}_physical_started.json', dict(n=n, basis_calls=2*n, mean_calls=2))
                physical_reference(rt, data, physical, guard)
                physical['raw_sha256'] = runtime.save_new(rt, output/f'n{n}_physical.npz', physical,
                                                         dict(role='collapsed_physical_reference', n=n))
                for p in (2, 1):
                    case = dict(n=n, p=p, status='started', counts={}, core_counts={}, reference_solver_counts={},
                                gauge_solver_counts={}, path_work=[], checks=[], candidates=[], finite_differences=[])
                    partial['cases'].append(case)
                    run_case(rt, output, data, p, physical, case, guard)
                    case['raw_sha256'] = runtime.save_new(rt, output/f'n{n}_p{p}_case.npz', case,
                                                         dict(role='collapsed_math_case', n=n, p=p))
                ratio = gaussian_ratio(n, partial['counts'])
                partial['gaussian'].append(ratio)
                runtime.save_new(rt, output/f'n{n}_gaussian_ratio.npz', ratio,
                                 dict(role='collapsed_gaussian_ratio', n=n))
                guard.check(files=True)
        partial['fixtures'] = run_fixtures(rt, output, guard)
        totals = dict(partial['counts'])
        for physical in partial['physical']:
            for key, value in physical['counts'].items():
                continuous.count(totals, key, value)
        for case in partial['cases']:
            for ledger in (case['counts'], case['core_counts'], case['reference_solver_counts'], case['gauge_solver_counts']):
                for key, value in ledger.items():
                    continuous.count(totals, key, value)
            for ledger in case['path_work']:
                for key, value in ledger.items():
                    continuous.count(totals, key, value)
        expected = dict(path_moment_builds_completed=51, source_preparations=51,
                        collapsed_initial_statistics_completed=6, schur_coordinate_preparations=9,
                        schur_block_factorizations=6, schur_empty_block_preparations=3,
                        schur_candidates_completed=45, canonical_references_completed=45,
                        gauge_rotations_completed=45, schur_derivatives_completed=9, finite_difference_pairs=18,
                        physical_basis_apply_completed=2096, physical_mean_apply_completed=6,
                        gain_cholesky_calls=96, gain_triangular_solve_calls=192, gain_solve_rhs_columns=252,
                        schur_candidate_triangular_solve_calls=60, schur_block_identity_rhs_columns=6,
                        gaussian_ratio_checks=3, gaussian_2x2_inverse_calls=3,
                        trace_entropy_evaluations=90, covariance_slogdet_calls=90)
        expected.update(schur_residual_matrix_products=45, schur_residual_matmul_terms=390,
                        schur_derivative_trace_matrix_products=9, schur_derivative_trace_matmul_terms=51,
                        gain_residual_matrix_products=96, gain_residual_matmul_terms=792,
                        direct_entropy_gram_matrix_products=90, direct_entropy_gram_matmul_terms=510,
                        gauge_dense_matrix_products=270, gauge_dense_matmul_terms=1530,
                        gain_candidate_columns_completed=45, gain_candidate_derivatives_completed=9)
        if any(totals.get(key, 0) != value for key, value in expected.items()):
            raise RuntimeError('collapsed mathematical work ledger differs from its fixed allocation')
        passed = (all(case['passed'] for case in partial['cases']) and
                  all(row['check']['passed'] for row in partial['gaussian']) and
                  all(row['passed'] for row in partial['fixtures']))
        partial.update(status='completed', counts=totals, passed=passed)
        digest = runtime.save_new(rt, output/'collapsed_complete.npz', partial,
                                  dict(role='collapsed_math_complete'))
        summary = dict(passed=passed, cases=[dict(n=row['n'], p=row['p'], passed=row['passed'],
                       checks=row['checks'], finite_differences=row['finite_differences'], raw_sha256=row['raw_sha256'])
                       for row in partial['cases']],
                       gaussian_checks=[row['check'] for row in partial['gaussian']], fixtures=partial['fixtures'],
                       counts=totals, mathematical_operations=partial['mathematical_operations'],
                       raw_sha256=digest, new_observations=0, independent_blocks=0, receiver_calls=0, decoder_calls=0,
                       scope='saved-fixture mathematics only; no receiver or generalization evidence')
        dump(output/'collapsed_summary.json', summary)
        if not passed:
            raise AssertionError('collapsed fixed mathematical diagnostic failed; no automatic retry or development')
        return summary
    except Exception as error:
        if isinstance(error, OSError) and not isinstance(error, TimeoutError):
            raise
        runtime.save_new(rt, output/'collapsed_failure.npz',
                         dict(partial=partial, error_type=type(error).__name__, error=str(error),
                              evidence=getattr(error, 'evidence', {})), dict(role='collapsed_math_failure'))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--source-attempt', type=Path, default=SOURCE_ATTEMPT)
    parser.add_argument('--stage', default='COLLAPSED-MATH-01')
    parser.add_argument('--print-imports', action='store_true')
    parser.add_argument('--print-config', action='store_true')
    args = parser.parse_args()
    rt = runtime.preload()
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    if args.print_config:
        print(json.dumps(configuration(), indent=2))
        return
    if args.artifact_root is None or not args.artifact_root.is_absolute():
        parser.error('absolute admitted --artifact-root required')
    source = args.source_attempt.resolve()

    def run(output, guard):
        return calculate(rt, output, guard, source)

    protocol.run(args.stage, 'engineering', configuration(), run,
                 artifact_root=args.artifact_root, rt=rt, extra_sources=input_paths(source), wall_cap_seconds=120)


if __name__ == '__main__':
    main()
