"""Saved MATH regression plus distinct deterministic component unit fixtures.

The sole receive() call carries forbidden truth and must reject at its boundary.
There are zero valid receiver payloads, backend runs or new communication draws.
"""
import json
from pathlib import Path
import time
import unittest

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from experiments.afdm_sp_fractional_20261007.moments import PathMoments
from . import protocol, runtime, test_core
from .data_step import DataStepper

CASES = (8, 16, 1024)
FIXTURES = [
    'QuadratureContracts.test_uniform_analytic_characteristic_and_cache_accounting',
    'QuadratureContracts.test_truncated_gaussian_boundary_normalization',
    'QuadratureContracts.test_tail_removal_and_duplicate_padding_preserve_moments',
    'QuadratureContracts.test_no_success_when_all_resolutions_disagree',
    'QuadratureContracts.test_point_keeps_old_candidate_and_ignores_constant_for_selection',
    'DataAndGainContracts.test_actual_objective_and_equation8_for_each_accepted_step',
    'DataAndGainContracts.test_finite_log_state_recovers_numerically_underflowed_mass',
    'DataAndGainContracts.test_identity_failure_aborts_without_backtracking',
    'DataAndGainContracts.test_full_gain_covariance_solves_original_precision',
    'DataAndGainContracts.test_incremental_coefficients_equal_fresh_canonical_recalculation',
    'DataAndGainContracts.test_truth_input_is_rejected_before_any_operator_or_decoder',
    'DataAndGainContracts.test_fatal_errors_keep_type_and_partial_evidence',
    'DataAndGainContracts.test_numerical_failure_keeps_paid_level_evidence',
]


def input_paths(attempt):
    attempt = Path(attempt)
    return [attempt/'attempt.json', *[attempt/f'n{n}_{suffix}' for n in CASES
                                    for suffix in ('inputs.npz', 'arrays.npz', 'checks.json')]]


def _read_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        result = {key: archive[key].copy() for key in archive.files}
    if any(value.dtype.hasobject or not np.isfinite(value).all() for value in result.values()):
        raise ValueError('invalid saved MATH arrays')
    return result


def saved_case(rt, output, guard, attempt, n):
    begin = time.perf_counter()
    partial = dict(n=n, computed={}, checks=[], data_steps=[], counts={})
    dump(output/f'saved_n{n}_started.json', dict(n=n, new_observations=0))
    try:
        report = json.loads((attempt/f'n{n}_checks.json').read_text())
        for role in ('inputs', 'arrays'):
            if protocol.sha(attempt/report[f'{role}_file']) != report[f'{role}_sha256']:
                raise ValueError('saved MATH payload hash mismatch')
        inputs = _read_npz(attempt/f'n{n}_inputs.npz')
        arrays = _read_npz(attempt/f'n{n}_arrays.npz')
        counts = partial['counts']
        with runtime.observe_operations(rt, guard.check) as operations:
            partial['operations'] = operations
            op = PathMoments(n, float(arrays['c1']), float(arrays['c2']), arrays['delays'],
                             arrays['doppler_nodes'], arrays['doppler_weights'],
                             arrays['gain_mean'], arrays['gain_covariance'])
            partial['transforms'] = op.work_counts
            source = op.prepare_source(inputs['pilot'], inputs['data_mean'], inputs['data_variance'])
            gram, matched = op.gain_statistics(inputs['y'], source)
            computed = partial['computed']
            computed.update(gain_gram=gram, gain_matched=matched)
            computed['quadratic'] = op.expected_quadratic(inputs['y'], source)
            computed['gram_diagonal'] = op.gram_diagonal()
            computed['gram_matvec'] = op.gram_matvec(inputs['probe'])
            computed['mean_adjoint'] = op.mean_adjoint(inputs['y'])
            computed['coordinate_coefficients'] = op.coordinate_coefficients(inputs['y'], source)
            checks = partial['checks']
            for key, actual in computed.items():
                expected = arrays[key if key == 'coordinate_coefficients' else 'structured_'+key]
                error = float(np.linalg.norm(np.asarray(actual)-expected)/max(1., np.linalg.norm(expected)))
                tolerance = 1e-9 if n == 1024 else 1e-10
                checks.append(dict(name=key, normalized_error=error, tolerance=tolerance,
                                   passed=error <= tolerance))
            # The saved y/pilot are reused, with the receiver's declared Pd=.5
            # for these new data updates; the original MATH source moments above
            # retain their original Pd=.55 and are not relabeled.
            stepper = DataStepper(op, inputs['y'], inputs['pilot'], .7,
                                  np.log(inputs['probabilities']), counts)
            for _ in range(3):
                log_q, detail = stepper.step()
                partial['data_steps'].append(detail)
                partial['log_q'] = log_q
        digest = runtime.save_new(rt, output/f'saved_n{n}_regression.npz', partial,
                                  dict(role='saved_math_regression', n=n))
        result = dict(n=n, checks=checks, data_steps=3, raw_sha256=digest,
                      seconds=time.perf_counter()-begin)
        dump(output/f'saved_n{n}_complete.json', result)
        guard.check(files=True, threads=True)
        if not all(check['passed'] for check in checks):
            raise AssertionError('saved MATH regression failed')
        return result
    except Exception as error:
        if isinstance(error, OSError) and not isinstance(error, TimeoutError):
            raise
        runtime.save_new(rt, output/f'saved_n{n}_failure.npz',
                         dict(partial=partial, error_type=type(error).__name__, error=str(error),
                              evidence=getattr(error, 'evidence', {}),
                              seconds=time.perf_counter()-begin),
                         dict(role='failed_saved_math_regression', n=n))
        raise


def calculate(rt, output, guard, attempt):
    attempt = Path(attempt)
    source_attempt = json.loads((attempt/'attempt.json').read_text())
    if source_attempt['status'] != 'complete':
        raise ValueError('saved MATH attempt did not complete')
    reports = [saved_case(rt, output, guard, attempt, n) for n in CASES]
    fixtures = []
    for index, label in enumerate(FIXTURES):
        started = time.perf_counter()
        dump(output/f'unit_{index:02d}_started.json', dict(fixture=label))
        cls, method = label.split('.')
        if method == 'test_truth_input_is_rejected_before_any_operator_or_decoder':
            guard.add('receiver_calls')
            guard.add('receiver_boundary_rejection_calls')
        test = getattr(test_core, cls)(method)
        result = unittest.TestResult()
        with runtime.observe_operations(rt, guard.check) as operations:
            with runtime.observe_component_evidence(rt) as components:
                test.run(result)
        raw_digest = runtime.save_new(rt, output/f'unit_{index:02d}_evidence.npz',
                                      dict(operations=operations, components=components),
                                      dict(role='unit_fixture_evidence', fixture=label))
        row = dict(fixture=label, passed=result.wasSuccessful(), tests_run=result.testsRun,
                   errors=[message for _, message in result.errors],
                   failures=[message for _, message in result.failures], operations=operations,
                   raw_evidence_sha256=raw_digest,
                   seconds=time.perf_counter()-started,
                   scope='independent deterministic unit fixture; not saved-array replay or BER')
        dump(output/f'unit_{index:02d}_complete.json', row)
        fixtures.append(row)
        guard.check(files=True, threads=True)
    summary = dict(saved_math_regressions=reports, unit_fixtures=fixtures,
                   engineering_passed=all(row['passed'] for row in fixtures),
                   saved_operator_checks=21, saved_data_steps=9,
                   receiver_calls=1, receiver_boundary_rejection_calls=1,
                   receiver_payload_executions=0, backend_fixture_calls=0,
                   new_observations=0, decoder_calls=0, source_attempt=str(attempt))
    dump(output/'engineering_summary.json', summary)
    if not summary['engineering_passed']:
        raise AssertionError('engineering unit fixture failed; no retry or success substitution')
    return summary
