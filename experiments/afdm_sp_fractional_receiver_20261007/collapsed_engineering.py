"""Eighteen frozen inputs; score-only replay and bounded-search contracts only."""
import inspect
import json
from pathlib import Path
import time

from experiments.afdm_shared_channel_20261004.common import dump
from . import collapsed_diagnostic as math, continuous, local_search, protocol, runtime, study
from .collapsed_gain import CollapsedGain

REFERENCE_ATTEMPT = Path('/data/guoyikun/afdm_sp_collapsed_20261007_math01_d3b2f1d8/'
                         'artifact/execution/COLLAPSED-MATH-01')
EXPECTED_WORK = dict(path_moment_builds_completed=6, source_preparations=6,
    path_moment_phase_entries=3144, collapsed_initial_statistics_completed=6,
    collapsed_initial_pair_terms=2096, schur_coordinate_preparations=9,
    schur_block_factorizations=6, schur_empty_block_preparations=3,
    schur_block_identity_rhs_columns=6, schur_block_matched_rhs_columns=6,
    gain_cholesky_calls=6, gain_triangular_solve_calls=12, gain_solve_rhs_columns=12,
    gain_logdet_evaluations=6, gain_residual_matrix_products=6, gain_residual_matmul_terms=12,
    schur_candidates_completed=54, schur_score_only_candidates_completed=45,
    schur_candidate_triangular_solve_calls=72, schur_candidate_vector_rhs=36,
    schur_full_covariance_restorations=9, schur_covariance_entries=27,
    schur_covariance_outer_product_terms=6, schur_residual_matrix_products=9,
    schur_residual_matmul_terms=78, schur_precision_residual_checks=9,
    gain_column_preparations=9, gain_column_source_cross_calls=6,
    gain_column_source_cross_terms=2096, gain_candidate_columns_completed=54,
    gain_candidate_phase_entries=18864, gain_candidate_cross_terms=12576,
    gain_candidate_matched_terms=18864, inverse_daft_vectors=21, ordinary_fft_vectors=6,
    forward_daft_vectors=0, schur_derivatives_completed=0, gain_candidate_derivatives_completed=0)


def reference_paths():
    return [REFERENCE_ATTEMPT/name for name in ('attempt.json', 'registration.json')]+[
        REFERENCE_ATTEMPT/f'n{n}_p{p}_case.npz' for n in math.SIZES for p in (2, 1)]


def input_paths(math_attempt):
    if math_attempt is None:
        raise ValueError('collapsed engineering requires the original MATH attempt')
    return math.input_paths(math_attempt)+reference_paths()


def configuration(math_attempt):
    paths = input_paths(math_attempt)
    return dict(variant='collapsed', seed='none', new_observations=0, independent_blocks=0,
        receiver_calls=0, decoder_calls=0, receiver_boundary_rejection_calls=0,
        receiver_payload_executions=0, backend_fixture_calls=0,
        saved_math_source=str(math.SOURCE_ATTEMPT), saved_collapsed_source=str(REFERENCE_ATTEMPT),
        saved_input_paths=[str(path) for path in paths], saved_input_files=18,
        cases=[dict(n=n, p=p) for n in math.SIZES for p in (2, 1)], offsets=list(math.OFFSETS),
        noise_variance=math.SIGMA2, data_moments='saved MATH Pd=.55; no receiver substitution',
        score_only_evaluations=45, default_full_evaluations=9, full_evaluation_offset=0.,
        replay_exact_work=EXPECTED_WORK, replay_work_scope='excludes separately recorded fixtures and search contracts',
        physical_basis_calls=0, new_geometry_probes=0, analytic_derivatives=0,
        original_component_fixtures=math.FIXTURES,
        search_contracts=['constant_keeps_previous', 'increasing_keeps_upper_endpoint'],
        search_contract_scores_cap=70, search_control=local_search.configuration(),
        reference_read_order='sealed replay before reference case arrays; never feed references into scoring',
        tolerances=dict(n8_n16=1e-10, n1024=1e-9, precision=1e-10),
        normalized_error='norm(actual-reference)/max(1,norm(reference))',
        default_contract_checks='configuration and static seal/scoring entry boundaries; no receiver execution',
        wall_cap_seconds=120, cpu_cap_seconds=120, process_wall_cap_seconds=150, exit_grace_seconds=10,
        scope='saved mathematical regression and two deterministic control contracts; no BER evidence')


def validate_reference(hashes, guard):
    for path in reference_paths():
        if math.saved._bound_sha(path, guard) != hashes[str(path)]:
            raise ValueError('collapsed reference changed after binding')
    attempt = json.loads((REFERENCE_ATTEMPT/'attempt.json').read_text())
    registration = json.loads((REFERENCE_ATTEMPT/'registration.json').read_text())
    if attempt['status'] != 'complete' or attempt['exit_code'] != 0:
        raise ValueError('collapsed reference attempt did not complete')
    if registration['stage'] != 'COLLAPSED-MATH-01' or registration['config'] != math.configuration():
        raise ValueError('collapsed reference registration differs')
    for path in reference_paths()[1:]:
        if attempt['artifact_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('collapsed reference artifact hash differs')
    for path in math.input_paths():
        if registration['source_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('collapsed reference used different original MATH inputs')


def replay_case(rt, output, guard, data, p, hashes, partial):
    n = data['n']
    label = f'n{n}_p{p}'
    dopplers = data['arrays']['doppler_nodes'][:p, 0].copy()
    counts, work = partial['counts'], partial['path_work']
    op, source = math.make_moments(data, p, dopplers, counts, work)
    model = CollapsedGain(op, source, data['inputs']['y'], math.SIGMA2, counts)
    partial['preparations'] = model.preparations
    for coordinate in range(p):
        prepared = model.prepare(coordinate)
        for offset in math.OFFSETS:
            row = dict(coordinate=coordinate, offset=offset, status='started')
            partial['candidates'].append(row)
            row['score_only'] = prepared.evaluate(float(dopplers[coordinate]+offset), score_only=True)
            if offset == 0.:
                row['full'] = prepared.evaluate(float(dopplers[coordinate]))
            row['status'] = 'completed'
            guard.check()
    partial['status'] = 'replay_completed'
    path = output/f'{label}_replay.npz'
    digest = runtime.save_new(rt, path, partial, dict(role='collapsed_receiver_replay', n=n, p=p))
    dump(output/f'{label}_replay_seal.json', dict(path=str(path), sha256=digest, reference_arrays_read=False))
    reference_path = REFERENCE_ATTEMPT/f'{label}_case.npz'
    if math.saved._bound_sha(reference_path, guard) != hashes[str(reference_path)]:
        raise ValueError('collapsed case changed before loading')
    reference, _ = rt.evidence.load_artifact(reference_path, dict(role='collapsed_math_case', n=n, p=p))
    if (reference['n'] != n or reference['p'] != p or reference['status'] != 'completed' or
            not reference['passed'] or
            [(row['coordinate'], row['offset']) for row in reference['candidates']] !=
            [(i, offset) for i in range(p) for offset in math.OFFSETS]):
        raise ValueError('collapsed reference case identity or candidate grid differs')
    tolerance = 1e-9 if n == 1024 else 1e-10
    checks = []
    for row, old in zip(partial['candidates'], reference['candidates']):
        expected = old['candidate']
        checks.extend(math._check(f"i{row['coordinate']}_o{row['offset']}_{key}", row['score_only'][key],
                                  expected[key], tolerance) for key in ('s', 't', 'J', 'reduced_score'))
        if 'full' in row:
            checks.extend(math._check(f"i{row['coordinate']}_{key}", row['full'][key], expected[key], tolerance)
                          for key in ('mean', 'covariance', 'precision', 's', 't', 'J', 'reduced_score'))
            checks.append(math._check('full_precision_residual', row['full']['precision_residual'], 0., 1e-10))
    if protocol.sha(path) != digest:
        raise ValueError('replay changed during reference comparison')
    report = dict(n=n, p=p, passed=all(row['passed'] for row in checks), checks=checks,
                  replay_sha256=digest, reference_sha256=hashes[str(reference_path)])
    dump(output/f'{label}_comparison.json', report)
    guard.check(files=True, threads=True)
    return report


def search_contracts(rt, output, guard):
    reports = []
    for name, score, expected in (('constant_keeps_previous', lambda value: 1., .2),
                                  ('increasing_keeps_upper_endpoint', lambda value: value, .95)):
        counts = {}
        with runtime.observe_operations(rt, guard.check) as operations:
            selected, trace = local_search.maximize(score, .2, counts)
        passed = (selected == expected and trace['actual_scores'] <= local_search.SCORE_CAP and
                  counts['local_scores_started'] == counts['local_scores_completed'] == trace['actual_scores'])
        report = dict(name=name, selected=selected, expected=expected, passed=passed, trace=trace,
                      counts=counts, operations=operations,
                      scope='deterministic scalar control contract; no receiver or gain solve')
        runtime.save_new(rt, output/f'{name}.npz', report, dict(role='collapsed_search_contract', name=name))
        reports.append(report)
        guard.check(files=True, threads=True)
    return reports


def default_contracts():
    fixed = study.configuration('development')
    adaptive = study.configuration('development', variant='adaptive', population_attempt=study.saved.SOURCE_ATTEMPT)
    receiver_source = inspect.getsource(study.receive_population)
    score_source = inspect.getsource(study.score_population)
    loader_source = inspect.getsource(study.load_saved_population)
    checks = dict(default_arms=runtime.ARMS == ('f1_scalar', 'vb_point', 'vb_continuous'),
        fixed_arms=fixed['arms'] == list(runtime.ARMS), fixed_calls=fixed['receiver_calls'] == 24,
        fixed_sweeps=fixed['sweeps'] == 20, fixed_quadrature=fixed['quadrature'] == [128, 256, 512, 1024],
        adaptive_calls=adaptive['receiver_calls'] == 24, adaptive_arms=adaptive['arms'] == list(runtime.ARMS),
        receiver_default=inspect.signature(study.receive_population).parameters['arms'].default == runtime.ARMS,
        scoring_default=inspect.signature(study.score_population).parameters['arms'].default == runtime.ARMS,
        receive_has_seal="dump(output/'receiver_seal.json'" in receiver_source,
        receive_no_truth_lookup="['truth']" not in receiver_source,
        scoring_checks_seal_before_truth=score_source.index("raise ValueError('receiver seal mismatch')") <
            score_source.index("row['truth']"),
        population_checks_original_registration="registration['config'] != configuration('development')" in loader_source)
    return dict(checks=checks, passed=all(checks.values()),
                scope='configuration and static source checks only; no original receiver or seal execution')


def calculate(rt, output, guard, math_attempt):
    started, cpu = time.perf_counter(), time.process_time()
    partial = dict(status='started', cases=[], reports=[])
    try:
        hashes = {str(path): math.saved._bound_sha(path, guard) for path in input_paths(math_attempt)}
        validate_reference(hashes, guard)
        data_sets, source_hashes = math.load_inputs(Path(math_attempt), guard)
        if any(hashes[path] != digest for path, digest in source_hashes.items()):
            raise ValueError('original MATH input changed during loading')
        dump(output/'input_identity.json', dict(sha256=hashes, reference_case_arrays_read=False))
        with runtime.observe_operations(rt, guard.check) as operations:
            partial['replay_operations'] = operations
            for data in data_sets:
                for p in (2, 1):
                    case = dict(n=data['n'], p=p, status='started', counts={}, path_work=[], candidates=[])
                    partial['cases'].append(case)
                    partial['reports'].append(replay_case(rt, output, guard, data, p, hashes, case))
        totals = {}
        for case in partial['cases']:
            for ledger in [case['counts'], *case['path_work']]:
                for key, value in ledger.items():
                    continuous.count(totals, key, value)
        partial['replay_counts'] = totals
        if any(totals.get(key, 0) != value for key, value in EXPECTED_WORK.items()):
            raise RuntimeError('collapsed receiver replay work differs from frozen allocation')
        partial['fixtures'] = math.run_fixtures(rt, output, guard)
        partial['search_contracts'] = search_contracts(rt, output, guard)
        partial['default_contracts'] = default_contracts()
        passed = (all(row['passed'] for row in partial['reports']+partial['fixtures']+partial['search_contracts']) and
                  partial['default_contracts']['passed'])
        partial.update(status='completed', passed=passed)
        digest = runtime.save_new(rt, output/'collapsed_engineering_complete.npz', partial,
                                  dict(role='collapsed_receiver_engineering'))
        summary = dict(engineering_passed=passed, variant='collapsed', cases=partial['reports'],
            replay_counts=totals, replay_operations=partial['replay_operations'], fixtures=partial['fixtures'],
            search_contracts=[dict(name=row['name'], passed=row['passed'], counts=row['counts'])
                              for row in partial['search_contracts']], default_contracts=partial['default_contracts'],
            raw_sha256=digest, receiver_calls=0, decoder_calls=0, new_observations=0, independent_blocks=0,
            wall_seconds=time.perf_counter()-started, cpu_seconds=time.process_time()-cpu)
        dump(output/'collapsed_engineering_summary.json', summary)
        if not passed:
            raise AssertionError('collapsed receiver engineering failed; development is not admitted')
        return summary
    except Exception as error:
        if isinstance(error, OSError) and not isinstance(error, TimeoutError):
            raise
        runtime.save_new(rt, output/'collapsed_engineering_failure.npz',
            dict(partial=partial, error_type=type(error).__name__, error=str(error),
                 evidence=getattr(error, 'evidence', {})), dict(role='failed_collapsed_receiver_engineering'))
        raise
