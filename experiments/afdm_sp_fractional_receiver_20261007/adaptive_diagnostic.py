"""QUAD-ADAPT-01: one frozen GK15/G7 saved-potential experiment.

Candidate selection never receives reference arrays. A candidate is saved and
sealed before its fixed 4096/8192 references are loaded. Embedded differences
and floating-point envelopes are diagnostics, not continuous error certificates.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from . import adaptive, protocol, quadrature_diagnostic as saved, runtime
from .continuous import count, finite

REFERENCE_ATTEMPT = Path('/data/guoyikun/afdm_sp_quadrature_20261007_diag01_86e7cbca/'
                         'artifact/execution/QUAD-DIAG-01')
INITIAL_PANELS = adaptive.INITIAL_PANELS
MAX_BISECTIONS = adaptive.MAX_BISECTIONS
TOLERANCE = adaptive.TOLERANCE
RULE_TOLERANCE = adaptive.RULE_TOLERANCE
N = saved.N


def configuration():
    return dict(seed='none', new_observations=0, independent_blocks=0, receiver_calls=0,
                decoder_calls=0, receiver_boundary_rejection_calls=0,
                receiver_payload_executions=0, backend_fixture_calls=0,
                new_geometry_probes=0, saved_coordinate_potentials=8, n=N,
                diagnostic='saved_fourier_adaptive_GK15_G7', source_attempt=str(saved.SOURCE_ATTEMPT),
                reference_attempt=str(REFERENCE_ATTEMPT), support=list(saved.SUPPORT),
                cases=[dict(block=b, snr_db=s) for b, s in saved.CASES],
                initial_panels=INITIAL_PANELS, max_bisections=MAX_BISECTIONS,
                max_density_nodes_per_case=1020, max_total_density_nodes=8160,
                max_center_derivatives_per_case=68, max_total_center_derivatives=544,
                max_active_panels=42, max_active_nodes=630,
                rule_validation=dict(calls=1, gauss_degrees=[0, 13], kronrod_degrees=[0, 22],
                                     absolute_tolerance=RULE_TOLERANCE),
                resolution_tolerance=TOLERANCE, drop_tolerance=saved.DROP_TOLERANCE,
                reference_tolerance=saved.REFERENCE_TOLERANCE,
                error_estimates=dict(logZ='-log(1-E_A/A)', phi='(E_A+E_B)/(A-E_A)+2*tail_bound'),
                priority='max(e_Ai/A,e_Bi/A,max(U_i-A_Ki,0)/sum(L_i)); log domain; leftmost tie',
                density_evaluation='direct Fourier; no surrogate or compression',
                phase_cache='within case; reuse unchanged panels and center; no parent-child node reuse',
                reference_read_order='after per-case candidate artifact and SHA seal',
                pass_condition='8/8 candidate_completed and fixed reference phi/logZ <= 1e-6',
                certified_continuous_error=False,
                scope='saved-input diagnostic only; no receiver, BER or independent generalization claim')


def reference_paths(reference=REFERENCE_ATTEMPT):
    reference = Path(reference).resolve()
    if reference != REFERENCE_ATTEMPT:
        raise ValueError('reference attempt differs from the fixed protocol')
    return [reference/name for name in ('attempt.json', 'registration.json')]+[
        reference/f'b{b}_snr{s}_q{nodes}.npz' for b, s in saved.CASES for nodes in (4096, 8192)]


def input_paths(source=saved.SOURCE_ATTEMPT, reference=REFERENCE_ATTEMPT):
    return saved.input_paths(source)+reference_paths(reference)


def source_manifest(source, reference, guard):
    hashes = saved.source_manifest(source, guard)
    hashes.update({str(path): saved._bound_sha(path, guard) for path in reference_paths(reference)})
    attempt = json.loads((reference/'attempt.json').read_text())
    registration = json.loads((reference/'registration.json').read_text())
    if attempt['status'] != 'complete' or attempt['exit_code'] != 0:
        raise ValueError('reference attempt did not complete')
    if registration['stage'] != 'QUAD-DIAG-01' or registration['config'] != saved.configuration():
        raise ValueError('reference registration differs from the frozen diagnostic')
    for path in reference_paths(reference)[1:]:
        if attempt['artifact_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('reference attempt hash mismatch: '+str(path))
    for path in saved.input_paths(source):
        if registration['source_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('reference was generated from a different source input: '+str(path))
    return hashes


def candidate(rt, output, label, factor, rule, partial, guard):
    """Persist numerical events without supplying information to their selection."""
    for event, detail in adaptive.candidate_events(factor, rule, partial):
        guard.check()
        if event == 'panel_started':
            path = output/f'{label}_panel{detail["id"]}.npz'
            dump(path.with_suffix('.started.json'),
                 {key: detail[key] for key in ('id', 'parent', 'left', 'right')})
        elif event == 'panel_completed':
            path = output/f'{label}_panel{detail["id"]}.npz'
            save_start = time.perf_counter()
            detail['saved_sha256'] = runtime.save_new(rt, path, detail,
                dict(role='adaptive_diagnostic_panel', case=label, panel_id=detail['id']))
            detail['save_seconds'] = time.perf_counter()-save_start
            guard.check(files=True)


def reference_comparison(rt, reference, block, snr, candidate_path, sealed_sha, result, guard):
    if protocol.sha(candidate_path) != sealed_sha:
        raise ValueError('sealed candidate changed before reference read')
    levels, hashes = [], {}
    for nodes in (4096, 8192):
        path = reference/f'b{block}_snr{snr}_q{nodes}.npz'
        hashes[str(path)] = saved._bound_sha(path, guard)
        level, _ = rt.evidence.load_artifact(path, dict(role='quadrature_diagnostic_level',
                                                      block=block, snr_db=snr, nodes=nodes))
        if (level['status'] != 'completed' or level['node_count'] != nodes or
                level['rule'] != 'scipy.roots_legendre' or level['artificial_tail_deletion']):
            raise ValueError('invalid fixed reference level')
        if np.shape(level['phi']) != (N,):
            raise ValueError('reference characteristic shape differs')
        finite(level['phi'], 'reference characteristic')
        finite(level['centered_log_normalizer'], 'reference logZ')
        levels.append(level)
        guard.check()
    agreement_phi = float(np.max(abs(levels[1]['phi']-levels[0]['phi'])))
    agreement_logz = abs(levels[1]['centered_log_normalizer']-levels[0]['centered_log_normalizer'])
    agreed = agreement_phi <= saved.REFERENCE_TOLERANCE and agreement_logz <= saved.REFERENCE_TOLERANCE
    phi_difference = float(np.max(abs(result['phi']-levels[1]['phi'])))
    logz_difference = abs(result['centered_log_normalizer']-levels[1]['centered_log_normalizer'])
    if protocol.sha(candidate_path) != sealed_sha:
        raise ValueError('sealed candidate changed during reference read')
    return dict(reference_sha256=hashes, reference_resolution_agreement=bool(agreed),
                reference_phi_difference=agreement_phi, reference_logZ_difference=agreement_logz,
                candidate_reference_phi_difference=phi_difference,
                candidate_reference_logZ_difference=logz_difference,
                within_fixed_reference_tolerance=bool(agreed and phi_difference <= TOLERANCE and
                                                     logz_difference <= TOLERANCE),
                reference_is_numerical_evidence=True, certified_continuous_error=False)


def case_diagnostic(rt, output, source, reference, block, snr, rule, guard):
    wall, cpu = time.perf_counter(), time.process_time()
    label = f'b{block}_snr{snr}'
    partial = dict(block=block, snr_db=snr, status='started', counts={}, panels=[], trace=[],
                   certified_continuous_error=False)
    path = output/f'{label}_candidate.npz'
    dump(output/f'{label}_started.json', dict(block=block, snr_db=snr, reference_arrays_read=False))
    try:
        factor = saved.extract_factor(rt, source, block, snr, guard)
        partial['input'] = factor
        with runtime.observe_operations(rt, guard.check) as operations:
            partial['primitive_operations'] = operations
            with np.errstate(over='raise', invalid='raise', divide='raise', under='ignore'):
                candidate(rt, output, label, factor, rule, partial, guard)
    except Exception as error:
        if isinstance(error, OSError) and not isinstance(error, TimeoutError):
            raise
        partial.update(status='arithmetic_failure' if isinstance(error, (FloatingPointError, np.linalg.LinAlgError))
                       else 'fatal_failure', error_type=type(error).__name__, error=str(error),
                       failure_detail=getattr(error, 'evidence', {}),
                       failure_wall_seconds=time.perf_counter()-wall,
                       failure_cpu_seconds=time.process_time()-cpu)
        runtime.save_new(rt, output/f'{label}_failure.npz', partial,
                         dict(role='adaptive_diagnostic_failure', block=block, snr_db=snr))
        if partial['status'] == 'fatal_failure':
            raise
    digest = runtime.save_new(rt, path, partial, dict(role='adaptive_diagnostic_candidate', block=block, snr_db=snr))
    seal = dict(candidate_path=str(path), candidate_sha256=digest, status=partial['status'],
                reference_arrays_read=False, counts=partial['counts'])
    dump(output/f'{label}_candidate_seal.json', seal)
    guard.check(files=True)
    comparison = None
    try:
        if 'output' in partial:
            comparison = reference_comparison(rt, reference, block, snr, path, digest, partial['output'], guard)
    except Exception as error:
        if isinstance(error, OSError) and not isinstance(error, TimeoutError):
            raise
        dump(output/f'{label}_reference_failure.json', dict(error_type=type(error).__name__, error=str(error),
                                                           candidate_sha256=digest))
        raise
    passed = partial['status'] == 'candidate_completed' and bool(
        comparison and comparison['within_fixed_reference_tolerance'])
    result = dict(block=block, snr_db=snr, status=partial['status'], candidate_sha256=digest,
                  counts=partial['counts'], comparison=comparison, passed=passed,
                  final_estimates=partial['trace'][-1] if partial['trace'] else None,
                  quadrature_wall_seconds=partial.get('quadrature_wall_seconds'),
                  quadrature_cpu_seconds=partial.get('quadrature_cpu_seconds'),
                  wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu,
                  certified_continuous_error=False)
    dump(output/f'{label}_complete.json', runtime.diagnostic_tree(result))
    guard.check(files=True, threads=True)
    return result


def calculate(rt, output, guard, source, reference):
    hashes = source_manifest(source, reference, guard)
    dump(output/'input_identity.json', dict(sha256=hashes, reference_arrays_read=False))
    dump(output/'rule_validation_started.json', dict(rule='GK15/G7', calls=1))
    rule_start = time.perf_counter()
    try:
        rule = adaptive.validated_rule()
    except Exception as error:
        dump(output/'rule_validation_failure.json', runtime.diagnostic_tree(dict(
            error_type=type(error).__name__, error=str(error), evidence=getattr(error, 'evidence', {}))))
        raise
    rule_seconds = time.perf_counter()-rule_start
    runtime.save_new(rt, output/'validated_rule.npz', rule, dict(role='adaptive_fixed_rule'))
    guard.check(files=True)
    reports = [case_diagnostic(rt, output, source, reference, b, s, rule, guard) for b, s in saved.CASES]
    totals = {}
    for report in reports:
        for key, value in report['counts'].items():
            count(totals, key, value)
    if totals.get('density_nodes_started', 0) > 8160 or totals.get('center_derivatives_started', 0) > 544:
        raise RuntimeError('saved-input diagnostic exceeded its total reservation')
    passed = all(report['passed'] for report in reports)
    summary = dict(cases=reports, counts=totals, rule_validation_calls=1, rule_validation_seconds=rule_seconds,
                   fixed_candidate_passed=passed, decision='accept_on_saved_inputs' if passed else 'reject_fixed_candidate',
                   new_observations=0, receiver_calls=0, decoder_calls=0, independent_blocks=0,
                   backend_fixture_calls=0, certified_continuous_error=False,
                   scope='eight diagnostic inputs; no independent generalization or receiver success claim')
    summary = runtime.diagnostic_tree(summary)
    dump(output/'adaptive_summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--source-attempt', type=Path, default=saved.SOURCE_ATTEMPT)
    parser.add_argument('--reference-attempt', type=Path, default=REFERENCE_ATTEMPT)
    parser.add_argument('--stage', default='QUAD-ADAPT-01')
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
    source, reference = args.source_attempt.resolve(), args.reference_attempt.resolve()

    def run(output, guard):
        return calculate(rt, output, guard, source, reference)

    protocol.run(args.stage, 'engineering', configuration(), run,
                 artifact_root=args.artifact_root, rt=rt, extra_sources=input_paths(source, reference))


if __name__ == '__main__':
    main()
