"""Original component fixtures plus one sealed replay of eight saved potentials."""
import json
from pathlib import Path
import time
import unittest

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from . import adaptive, adaptive_diagnostic, engineering, protocol, quadrature_diagnostic as saved, runtime
from . import test_adaptive_contracts

REFERENCE_ATTEMPT = Path('/data/guoyikun/afdm_sp_quadrature_20261007_adapt01_af8fed05/'
                         'artifact/execution/QUAD-ADAPT-01')
REPLAY_TOLERANCE = 1e-10


def reference_paths():
    return [REFERENCE_ATTEMPT/name for name in ('attempt.json', 'registration.json')]+[
        REFERENCE_ATTEMPT/f'b{b}_snr{s}_{suffix}' for b, s in saved.CASES
        for suffix in ('candidate.npz', 'candidate_seal.json')]


def input_paths(math_attempt):
    return engineering.input_paths(math_attempt)+saved.input_paths()+reference_paths()


def configuration(math_attempt):
    if math_attempt is None or not Path(math_attempt).is_absolute():
        raise ValueError('adaptive engineering requires an absolute saved MATH attempt')
    return dict(variant='adaptive', quadrature='adaptive',
                saved_math_source=str(Path(math_attempt)), saved_fourier_source=str(saved.SOURCE_ATTEMPT),
                saved_adaptive_reference=str(REFERENCE_ATTEMPT),
                saved_input_paths=[str(path) for path in input_paths(math_attempt)],
                replay_cases=[dict(block=b, snr_db=s) for b, s in saved.CASES],
                replay_rule_validation_calls=1, replay_factor_exports=8,
                replay_density_nodes_per_case_cap=1020, replay_density_nodes_total_cap=8160,
                replay_center_derivatives_per_case_cap=68, replay_center_derivatives_total_cap=544,
                replay_tolerance=REPLAY_TOLERANCE, replay_counts_and_splits='exact equality',
                replay_reference_read_order='only after replay output and SHA seal',
                saved_operator_checks=21, saved_data_steps=9, original_component_fixtures=13,
                integration_stub_fixtures=test_adaptive_contracts.FIXTURES,
                integration_stub_scope='mocked bookkeeping only; synthetic counters excluded from measured work',
                valid_receiver_calls=0, certified_continuous_error=False)


def compare_reference(rt, label, block, snr, replay_path, replay_sha, partial, hashes, guard):
    # Even reference metadata is parsed only after the candidate has been sealed.
    if protocol.sha(replay_path) != replay_sha:
        raise ValueError('adaptive replay changed before reference parsing')
    for path in reference_paths():
        if saved._bound_sha(path, guard) != hashes[str(path)]:
            raise ValueError('registered adaptive reference bytes changed')
    attempt = json.loads((REFERENCE_ATTEMPT/'attempt.json').read_text())
    registration = json.loads((REFERENCE_ATTEMPT/'registration.json').read_text())
    if attempt['status'] != 'complete' or attempt['exit_code'] != 0:
        raise ValueError('saved adaptive diagnostic did not complete')
    if registration['stage'] != 'QUAD-ADAPT-01' or registration['config'] != adaptive_diagnostic.configuration():
        raise ValueError('saved adaptive diagnostic configuration differs')
    for path in reference_paths()[1:]:
        if attempt['artifact_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('adaptive reference artifact hash differs')
    for path in saved.input_paths():
        if registration['source_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('adaptive reference source potential differs')
    reference_path = REFERENCE_ATTEMPT/f'{label}_candidate.npz'
    seal = json.loads((REFERENCE_ATTEMPT/f'{label}_candidate_seal.json').read_text())
    if (seal['candidate_path'] != str(reference_path) or
            seal['candidate_sha256'] != hashes[str(reference_path)] or seal['reference_arrays_read']):
        raise ValueError('original adaptive candidate seal is invalid')
    reference, _ = rt.evidence.load_artifact(reference_path,
        dict(role='adaptive_diagnostic_candidate', block=block, snr_db=snr))
    split_keys = ('selected_panel_id', 'selected_left', 'active_panel_ids', 'bisections',
                  'density_nodes', 'center_derivatives', 'estimated_complete', 'denominator_valid', 'dropped_nodes')
    current_splits = [{key: row[key] for key in split_keys if key in row} for row in partial['trace']]
    old_splits = [{key: row[key] for key in split_keys if key in row} for row in reference['trace']]
    panel_keys = ('id', 'parent', 'left', 'right')
    current_panels = [{key: panel[key] for key in panel_keys} for panel in partial['panels']]
    old_panels = [{key: panel[key] for key in panel_keys} for panel in reference['panels']]
    if np.shape(reference['output']['phi']) != (saved.N,):
        raise ValueError('saved adaptive reference has an invalid characteristic shape')
    saved.finite(reference['output']['phi'], 'saved adaptive reference phi')
    saved.finite(reference['output']['log_normalizer'], 'saved adaptive reference logZ')
    phi_error = float(np.max(abs(partial['output']['phi']-reference['output']['phi'])))
    logz_error = abs(partial['output']['log_normalizer']-reference['output']['log_normalizer'])
    checks = dict(status=partial['status'] == reference['status'] == 'candidate_completed',
                  counts=partial['counts'] == reference['counts'] == seal['counts'],
                  splits=current_splits == old_splits, panels=current_panels == old_panels,
                  phi=phi_error <= REPLAY_TOLERANCE, logZ=logz_error <= REPLAY_TOLERANCE)
    if protocol.sha(replay_path) != replay_sha:
        raise ValueError('adaptive replay changed during reference parsing')
    return dict(checks=checks, passed=all(checks.values()), phi_difference=phi_error,
                logZ_difference=logz_error, tolerance=REPLAY_TOLERANCE,
                reference_sha256=hashes[str(reference_path)])


def replay_case(rt, output, block, snr, rule, hashes, guard):
    started, cpu = time.perf_counter(), time.process_time()
    label = f'b{block}_snr{snr}'
    partial = dict(block=block, snr_db=snr, status='started', counts={}, panels=[], trace=[],
                   certified_continuous_error=False)
    dump(output/f'{label}_replay_started.json', dict(block=block, snr_db=snr, reference_arrays_read=False))
    try:
        factor = saved.extract_factor(rt, saved.SOURCE_ATTEMPT, block, snr, guard)
        partial['input'] = factor
        with runtime.observe_operations(rt, guard.check) as operations:
            partial['primitive_operations'] = operations
            with np.errstate(over='raise', invalid='raise', divide='raise', under='ignore'):
                adaptive_diagnostic.candidate(rt, output, label, factor, rule, partial, guard)
                exported = adaptive.as_factor(factor['coefficients'], factor['sigma2'], partial)
        partial['exported_factor'] = exported.record()
        partial['factor_export_work'] = dict(expected_log_kernel_terms=len(exported.weights))
        path = output/f'{label}_replay.npz'
        digest = runtime.save_new(rt, path, partial, dict(role='adaptive_core_replay', block=block, snr_db=snr))
        dump(output/f'{label}_replay_seal.json', dict(replay_path=str(path), replay_sha256=digest,
             status=partial['status'], counts=partial['counts'], reference_arrays_read=False))
        guard.check(files=True)
        comparison = compare_reference(rt, label, block, snr, path, digest, partial, hashes, guard)
        result = dict(block=block, snr_db=snr, counts=partial['counts'], comparison=comparison,
                      passed=comparison['passed'], replay_sha256=digest,
                      wall_seconds=time.perf_counter()-started, cpu_seconds=time.process_time()-cpu)
        dump(output/f'{label}_replay_complete.json', result)
        guard.check(files=True, threads=True)
        return result
    except Exception as error:
        if isinstance(error, OSError) and not isinstance(error, TimeoutError):
            raise
        runtime.save_new(rt, output/f'{label}_replay_failure.npz',
                         dict(partial=partial, error_type=type(error).__name__, error=str(error),
                              evidence=getattr(error, 'evidence', {})),
                         dict(role='failed_adaptive_core_replay', block=block, snr_db=snr))
        raise


def calculate(rt, output, guard, math_attempt):
    hashes = {str(path): saved._bound_sha(path, guard) for path in input_paths(math_attempt)}
    saved.source_manifest(saved.SOURCE_ATTEMPT, guard)
    dump(output/'adaptive_input_identity.json', dict(sha256=hashes, reference_arrays_read=False))
    components = engineering.calculate(rt, output, guard, math_attempt)
    stubs = []
    for label in test_adaptive_contracts.FIXTURES:
        cls, method = label.split('.')
        result = unittest.TestResult()
        getattr(test_adaptive_contracts, cls)(method).run(result)
        row = dict(fixture=label, passed=result.wasSuccessful(), tests_run=result.testsRun,
                   errors=[message for _, message in result.errors],
                   failures=[message for _, message in result.failures],
                   scope='mocked adapter control flow; no density or receiver; synthetic counts excluded')
        stubs.append(row)
        dump(output/f'{method}.json', row)
        guard.check(files=True)
    start = time.perf_counter()
    try:
        rule = adaptive.validated_rule()
    except Exception as error:
        dump(output/'adaptive_rule_failure.json', runtime.diagnostic_tree(dict(
            error_type=type(error).__name__, error=str(error), evidence=getattr(error, 'evidence', {}))))
        raise
    rule_seconds = time.perf_counter()-start
    runtime.save_new(rt, output/'adaptive_validated_rule.npz', rule, dict(role='adaptive_fixed_rule'))
    reports = [replay_case(rt, output, b, s, rule, hashes, guard) for b, s in saved.CASES]
    totals = {}
    for report in reports:
        for key, value in report['counts'].items():
            totals[key] = totals.get(key, 0)+value
    if totals.get('density_nodes_started', 0) > 8160 or totals.get('center_derivatives_started', 0) > 544:
        raise RuntimeError('adaptive engineering replay exceeded its fixed reservation')
    passed = components['engineering_passed'] and all(row['passed'] for row in reports+stubs)
    summary = dict(component_regression=components, adaptive_replays=reports, replay_counts=totals,
                   replay_rule_validation_calls=1, replay_rule_validation_seconds=rule_seconds,
                   replay_factor_exports=8, engineering_passed=passed, variant='adaptive',
                   integration_stub_fixtures=stubs,
                   new_observations=0, independent_blocks=0, receiver_calls=1,
                   receiver_boundary_rejection_calls=1, receiver_payload_executions=0,
                   backend_fixture_calls=0, decoder_calls=0)
    dump(output/'adaptive_engineering_summary.json', summary)
    if not passed:
        raise AssertionError('adaptive engineering regression failed; development is not admitted')
    return summary
