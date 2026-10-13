"""QUAD-DIAG-01: saved Fourier potentials, no receiver or new observation.

Use --print-imports / --print-config for import-only preparation. The numerical
CLI requires --artifact-root under /data/guoyikun and a frozen engineering-kind
contract. Every case executes 1024-node NumPy replay plus all three independent
SciPy rules; neither reference agreement nor replay accuracy is presumed.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.special import logsumexp, roots_legendre

from experiments.afdm_shared_channel_20261004.common import dump
from . import protocol, runtime
from .continuous import count, finite

SOURCE_ATTEMPT = Path('/data/guoyikun/afdm_sp_receiver_20261007_dev01_78c41569/'
                      'artifact/execution/RECEIVER-DEV-01')
N = 1024
SUPPORT = (-3., 3.)
ORDER = 64
REFERENCE_PANELS = (32, 64, 128)
DROP_TOLERANCE = 1e-14
REPLAY_TOLERANCE = 1e-9
REFERENCE_TOLERANCE = 1e-9
ORIGINAL_TOLERANCE = 1e-6
CASES = tuple((block, snr) for block in range(4) for snr in (6, 8))
FAILURE_MESSAGE = 'continuous integration did not agree by 1024 nodes'


def raw_name(block, snr):
    return f'calls/b{block}_snr{snr}_vb_continuous.npz'


def input_paths(source=SOURCE_ATTEMPT):
    source = Path(source).resolve()
    if source != SOURCE_ATTEMPT:
        raise ValueError('diagnostic source attempt differs from the fixed protocol')
    return [source/name for name in ('attempt.json', 'registration.json', 'receiver_seal.json')]+[
        source/raw_name(block, snr) for block, snr in CASES]


def configuration():
    return dict(seed='none', new_observations=0, independent_blocks=0, receiver_calls=0,
                decoder_calls=0, receiver_boundary_rejection_calls=0,
                receiver_payload_executions=0, backend_fixture_calls=0,
                new_geometry_probes=0, saved_coordinate_potentials=8,
                diagnostic='saved_fourier_resolution', source_attempt=str(SOURCE_ATTEMPT),
                cases=[dict(block=block, snr_db=snr, raw=raw_name(block, snr)) for block, snr in CASES],
                n=N, support=list(SUPPORT), order=ORDER,
                original=dict(rule='numpy.leggauss', panels=16, nodes=1024,
                              drop_tolerance=DROP_TOLERANCE, replay_absolute_tolerance=REPLAY_TOLERANCE),
                reference=dict(rule='scipy.roots_legendre', panels=list(REFERENCE_PANELS),
                               nodes=[2048, 4096, 8192], all_levels_required=True,
                               artificial_tail_deletion=False, agreement_tolerance=REFERENCE_TOLERANCE),
                original_accuracy_tolerance=ORIGINAL_TOLERANCE,
                density_nodes_per_case=15360, total_density_nodes=122880,
                derivative_probes_per_case=1, total_derivative_probes=8,
                derivative_location='largest sampled 8192-node log density',
                B2='(2/sigma2)*sum_{n=1}^{N-1} abs(a_n)*(2*pi*n/N)**2',
                rules_cached_across_cases=False, phase_tables_cached_across_cases=False,
                scope='resolution diagnostic only; no certified integral, BER or receiver claim')


def _bound_sha(path, guard):
    key = str(path.relative_to(protocol.ROOT)) if path.is_relative_to(protocol.ROOT) else str(path)
    expected = guard.contract['source_sha256'][key]
    actual = protocol.sha(path)
    if actual != expected:
        raise ValueError('registered diagnostic input changed: '+str(path))
    return actual


def source_manifest(source, guard):
    hashes = {str(path): _bound_sha(path, guard) for path in input_paths(source)}
    attempt = json.loads((source/'attempt.json').read_text())
    registration = json.loads((source/'registration.json').read_text())
    seal = json.loads((source/'receiver_seal.json').read_text())
    if attempt['status'] != 'complete' or attempt['exit_code'] != 0:
        raise ValueError('source attempt did not complete its accounting')
    if registration['stage'] != 'RECEIVER-DEV-01' or registration['config']['n'] != N:
        raise ValueError('source registration identity differs')
    if seal['receiver_calls'] != 24 or seal['decoder_calls'] != 0 or len(seal['records']) != 24:
        raise ValueError('source receiver seal is incomplete')
    for path in input_paths(source)[1:]:
        if attempt['artifact_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('source attempt artifact hash mismatch: '+str(path))
    selected = [row for row in seal['records'] if row['arm'] == 'vb_continuous']
    if sorted((row['block'], row['snr_db']) for row in selected) != list(CASES):
        raise ValueError('source continuous population is not the fixed eight cases')
    for row in selected:
        expected_name = raw_name(row['block'], row['snr_db'])
        if (row['status'] != 'numerical_failure' or row['raw'] != expected_name or
                row['raw_sha256'] != hashes[str(source/expected_name)]):
            raise ValueError('source failure status/path/hash mismatch')
    return hashes


def extract_factor(rt, source, block, snr, guard):
    path = source/raw_name(block, snr)
    digest = _bound_sha(path, guard)
    payload, identity = rt.evidence.load_artifact(path, dict(
        role='receiver', block=block, snr_db=snr, arm='vb_continuous'))
    if payload['status'] != 'numerical_failure':
        raise ValueError('raw call was not a numerical failure')
    error = payload['payload']
    if error['error_type'] != 'CoreFailure' or FAILURE_MESSAGE not in error['error']:
        raise ValueError('raw failure is not the registered quadrature cap failure')
    arm = error['evidence']
    core = arm['failure_detail']
    if arm['phase'] != 'vb_continuous' or core['mode'] != 'vb_continuous':
        raise ValueError('source failed outside the continuous backend')
    trace = core['trace']
    if (len(trace) != 1 or trace[0]['sweep'] != 0 or trace[0]['doppler'] or trace[0]['data'] or
            core['counts']['doppler_coordinates_started'] != 1 or
            core['counts'].get('doppler_coordinates_completed', 0) != 0):
        raise ValueError('source is not the first failed Fourier coordinate')
    integration = core['failure_detail']
    density, levels = integration['density'], integration['levels']
    if density['kind'] != 'fourier' or [level['nodes'] for level in levels] != [128, 256, 512, 1024]:
        raise ValueError('source density or quadrature resolution sequence differs')
    if any(level['status'] != 'completed' for level in levels):
        raise ValueError('source failure did not complete its four integration levels')
    if (levels[-1]['phi_difference_bound'] <= ORIGINAL_TOLERANCE and
            levels[-1]['log_normalizer_difference'] <= ORIGINAL_TOLERANCE):
        raise ValueError('saved final level passed rather than failed resolution agreement')
    coefficients = np.asarray(density['coefficients'], complex).copy()
    sigma2 = float(density['sigma2'])
    if coefficients.shape != (N,) or not np.isfinite(coefficients).all() or not np.isfinite(sigma2) or sigma2 <= 0:
        raise ValueError('invalid saved Fourier coefficients/noise')
    coefficients.setflags(write=False)
    return dict(identity=identity, raw_sha256=digest, coefficients=coefficients, sigma2=sigma2,
                original_levels=levels, extraction='payload.evidence.failure_detail.failure_detail',
                original_error=error['error'])


def integrate_level(coefficients, sigma2, panels, original, record, counts, guard):
    """Direct positive quadrature; record no phase matrix, but all its costs."""
    start, cpu_start = time.perf_counter(), time.process_time()
    counts_before = dict(counts)
    size = panels*ORDER
    record.update(status='started', panels=panels, order=ORDER, node_count=size,
                  rule='numpy.leggauss' if original else 'scipy.roots_legendre')
    guard.check()
    count(counts, 'levels_started')
    count(counts, 'numpy_leggauss_calls' if original else 'scipy_roots_legendre_calls')
    roots, weights = np.polynomial.legendre.leggauss(ORDER) if original else roots_legendre(ORDER)
    edges = np.linspace(*SUPPORT, panels+1)
    half = (SUPPORT[1]-SUPPORT[0])/(2*panels)
    nodes = (((edges[:-1]+edges[1:])/2)[:, None]+half*roots).ravel()
    base_weights = np.tile(half*weights, panels)
    if np.any(base_weights <= 0) or abs(base_weights.sum()-6.) > 1e-12:
        raise FloatingPointError('quadrature base weights invalid')
    record.update(nodes=nodes, base_weights=base_weights)
    times = 2*np.pi*np.arange(N)/N
    count(counts, 'phase_entries_started', size*N)
    phase = np.exp(1j*nodes[:, None]*times)
    finite(phase, 'diagnostic phase table')
    count(counts, 'phase_entries_completed', size*N)
    guard.check()
    count(counts, 'density_nodes_started', size)
    count(counts, 'fourier_contraction_terms', size*(N-1))
    reduced = (2/sigma2)*np.real(phase[:, 1:]@coefficients[1:])
    constant = float(2*coefficients[0].real/sigma2)
    finite(reduced, 'diagnostic centered Fourier potential')
    finite(constant, 'diagnostic Fourier constant')
    count(counts, 'density_nodes_completed', size)
    logits = np.log(base_weights/6.)+reduced
    log_z = float(logsumexp(logits))
    log_mass = logits-log_z
    finite(log_mass, 'diagnostic log masses')
    record.update(reduced_log_kernel=reduced, constant=constant,
                  centered_log_normalizer=log_z, log_normalizer=log_z+constant, log_masses=log_mass,
                  max_node_log_density=float(np.max(reduced)-log_z-np.log(6.)),
                  max_node_mass=float(np.exp(np.max(log_mass))))
    panel_index = np.repeat(np.arange(panels), ORDER)
    if original:
        keep = log_mass > np.log(DROP_TOLERANCE/size)
        if not np.any(keep):
            raise FloatingPointError('replay removed all nodes')
        dropped = int(np.count_nonzero(~keep))
        dropped_log_mass = float(logsumexp(log_mass[~keep])) if dropped else None
        with np.errstate(under='ignore'):
            dropped_mass = float(np.exp(dropped_log_mass)) if dropped else 0.
        probabilities = np.exp(log_mass[keep]-logsumexp(log_mass[keep]))
        if np.any(probabilities <= 0) or dropped_mass > DROP_TOLERANCE:
            raise FloatingPointError('invalid original tail replay')
        count(counts, 'characteristic_contraction_terms', int(keep.sum())*N)
        phi = probabilities@phase[keep]
        record.update(retained_mask=keep, retained_probabilities=probabilities,
                      retained_nodes=int(keep.sum()), dropped_nodes=dropped,
                      dropped_mass=dropped_mass, dropped_log_mass=dropped_log_mass,
                      dropped_mass_bound=dropped*DROP_TOLERANCE/size,
                      moment_tail_bound=2*dropped*DROP_TOLERANCE/size,
                      retained_panel_mass=np.bincount(panel_index[keep], weights=probabilities,
                                                      minlength=panels))
    else:
        with np.errstate(under='ignore'):
            probabilities = np.exp(log_mass)
        underflow = probabilities == 0
        underflow_count = int(np.count_nonzero(underflow))
        # This is an upper bound in log mass for the *discrete* omitted numeric
        # terms, not an interval certificate for the continuous integral.
        log_upper = (float(np.log(underflow_count)+np.max(log_mass[underflow]))
                     if underflow_count else None)
        mass = float(np.sum(probabilities))
        if abs(mass-1.) > 1e-10:
            raise FloatingPointError('reference probability sum is invalid')
        count(counts, 'characteristic_contraction_terms', size*N)
        phi = probabilities@phase
        mean = float(probabilities@nodes/mass)
        variance = float(probabilities@((nodes-mean)**2)/mass)
        record.update(probabilities=probabilities, artificial_tail_deletion=False,
                      exponentiation_underflow_nodes=underflow_count,
                      underflow_log_mass_upper_bound=log_upper, numeric_mass_sum=mass,
                      discrete_mean=mean, discrete_standard_deviation=float(np.sqrt(variance)),
                      panel_mass=np.bincount(panel_index, weights=probabilities, minlength=panels))
    finite(phi, 'diagnostic characteristic moments')
    if abs(phi[0]-1) > 1e-10 or np.max(abs(phi)) > 1+1e-10:
        raise FloatingPointError('diagnostic characteristic invariant failed')
    record.update(phi=phi, status='completed', seconds=time.perf_counter()-start,
                  cpu_seconds=time.process_time()-cpu_start)
    count(counts, 'levels_completed')
    record['work_counts'] = {key: value-counts_before.get(key, 0) for key, value in counts.items()
                             if value != counts_before.get(key, 0)}
    guard.check()


def replay_checks(replayed, saved):
    checks = []
    for key in ('retained_nodes', 'dropped_nodes', 'dropped_mass_bound', 'moment_tail_bound'):
        checks.append(dict(field=key, passed=replayed[key] == saved[key]))
    for key in ('centered_log_normalizer', 'constant', 'log_normalizer',
                'max_node_log_density', 'max_node_mass', 'retained_panel_mass'):
        difference = float(np.max(abs(np.asarray(replayed[key])-np.asarray(saved[key]))))
        checks.append(dict(field=key, absolute_difference=difference,
                           tolerance=REPLAY_TOLERANCE, passed=difference <= REPLAY_TOLERANCE))
    if replayed['dropped_log_mass'] is None or saved['dropped_log_mass'] is None:
        checks.append(dict(field='dropped_log_mass', passed=replayed['dropped_log_mass'] is saved['dropped_log_mass']))
    else:
        difference = abs(replayed['dropped_log_mass']-saved['dropped_log_mass'])
        checks.append(dict(field='dropped_log_mass', absolute_difference=difference,
                           tolerance=REPLAY_TOLERANCE, passed=difference <= REPLAY_TOLERANCE))
    return checks


def sampled_peak_probe(coefficients, sigma2, reference, counts):
    index = int(np.argmax(reference['reduced_log_kernel']))
    node = float(reference['nodes'][index])
    times = 2*np.pi*np.arange(1, N)/N
    count(counts, 'derivative_probes_started')
    count(counts, 'derivative_phase_entries', N-1)
    phase = np.exp(1j*node*times)
    first = float((2/sigma2)*np.real(np.sum(1j*times*coefficients[1:]*phase)))
    second = float((2/sigma2)*np.real(np.sum(-times**2*coefficients[1:]*phase)))
    bound = float((2/sigma2)*np.sum(abs(coefficients[1:])*times**2))
    finite([first, second, bound], 'sampled peak derivatives')
    count(counts, 'derivative_contraction_terms', 2*(N-1))
    count(counts, 'B2_bound_terms', N-1)
    count(counts, 'derivative_probes_completed')
    return dict(reference_node_count=8192, sampled_peak_index=index, sampled_peak_position=node,
                sampled_peak_log_density=float(reference['reduced_log_kernel'][index]-
                    reference['centered_log_normalizer']-np.log(6.)),
                first_derivative=first, second_derivative=second, B2=bound,
                scope='one sampled node, not an exact stationary point or certified bound')


def comparisons(levels, original_levels):
    old, ref4096, ref8192 = levels[0], levels[2], levels[3]
    ref_phi = float(np.max(abs(ref8192['phi']-ref4096['phi'])))
    ref_logz = abs(ref8192['centered_log_normalizer']-ref4096['centered_log_normalizer'])
    agreed = ref_phi <= REFERENCE_TOLERANCE and ref_logz <= REFERENCE_TOLERANCE
    old_phi = float(np.max(abs(old['phi']-ref8192['phi'])))
    old_logz = abs(old['centered_log_normalizer']-ref8192['centered_log_normalizer'])
    replay = replay_checks(old, original_levels[-1])
    replay_ok = all(row['passed'] for row in replay)
    phi_ok = old_phi <= ORIGINAL_TOLERANCE if agreed and replay_ok else None
    logz_ok = old_logz <= ORIGINAL_TOLERANCE if agreed and replay_ok else None
    if not replay_ok:
        outcome = 'unknown: original replay metadata mismatch'
    elif not agreed:
        outcome = 'unknown: reference resolutions disagree'
    elif phi_ok and logz_ok:
        outcome = 'original 1024 agrees with resolved reference at original tolerance'
    else:
        outcome = 'original 1024 exceeds original tolerance against resolved reference'
    return dict(replay_checks=replay, replay_metadata_agreement=replay_ok,
                reference_phi_difference=ref_phi, reference_logZ_difference=ref_logz,
                reference_resolution_agreement=agreed, reference_tolerance=REFERENCE_TOLERANCE,
                original_1024_reference_phi_difference=old_phi,
                original_1024_reference_logZ_difference=old_logz,
                original_phi_within_tolerance=phi_ok, original_logZ_within_tolerance=logz_ok,
                original_tolerance=ORIGINAL_TOLERANCE,
                saved_512_to_1024_phi_difference=original_levels[-1]['raw_phi_difference'],
                saved_512_to_1024_logZ_difference=original_levels[-1]['log_normalizer_difference'],
                saved_512_reference_logZ_difference=abs(original_levels[-2]['centered_log_normalizer']-
                                                        ref8192['centered_log_normalizer']),
                outcome=outcome, certified_continuous_error=False)


def case_diagnostic(rt, output, source, block, snr, guard):
    wall, cpu = time.perf_counter(), time.process_time()
    label = f'b{block}_snr{snr}'
    partial = dict(block=block, snr_db=snr, levels=[], counts={})
    dump(output/f'{label}_started.json', dict(block=block, snr_db=snr,
         source=str(source/raw_name(block, snr)), raw_sha256=_bound_sha(source/raw_name(block, snr), guard)))
    try:
        factor = extract_factor(rt, source, block, snr, guard)
        partial['input'] = factor
        with runtime.observe_operations(rt, guard.check) as operations:
            partial['primitive_operations'] = operations
            for panels, original in ((16, True), *[(value, False) for value in REFERENCE_PANELS]):
                level = {}
                partial['levels'].append(level)
                dump(output/f'{label}_q{panels*ORDER}_started.json',
                     dict(nodes=panels*ORDER, original_replay=original))
                integrate_level(factor['coefficients'], factor['sigma2'], panels, original,
                                level, partial['counts'], guard)
                save_start = time.perf_counter()
                digest = runtime.save_new(rt, output/f'{label}_q{panels*ORDER}.npz', level,
                    dict(role='quadrature_diagnostic_level', block=block, snr_db=snr, nodes=panels*ORDER))
                level['saved_sha256'] = digest
                level['save_seconds'] = time.perf_counter()-save_start
                count(partial['counts'], 'saved_levels')
                guard.check(files=True)
            partial['sampled_peak'] = sampled_peak_probe(
                factor['coefficients'], factor['sigma2'], partial['levels'][-1], partial['counts'])
            partial['comparison'] = comparisons(partial['levels'], factor['original_levels'])
        if (partial['counts']['density_nodes_completed'] != 15360 or
                partial['counts']['derivative_probes_completed'] != 1):
            raise RuntimeError('fixed per-case diagnostic work allocation changed')
        partial['status'] = 'completed'
    except Exception as error:
        if isinstance(error, OSError) and not isinstance(error, TimeoutError):
            raise
        partial.update(status='arithmetic_failure' if isinstance(error, (FloatingPointError, np.linalg.LinAlgError))
                       else 'fatal_failure', error_type=type(error).__name__, error=str(error),
                       failure_detail=getattr(error, 'evidence', {}))
        runtime.save_new(rt, output/f'{label}_failure.npz', partial,
                         dict(role='quadrature_diagnostic_failure', block=block, snr_db=snr))
        if partial['status'] == 'fatal_failure':
            raise
    digest = runtime.save_new(rt, output/f'{label}_diagnostic.npz', partial,
                             dict(role='quadrature_diagnostic_case', block=block, snr_db=snr))
    result = dict(block=block, snr_db=snr, status=partial['status'], raw_sha256=digest,
                  counts=partial['counts'], comparison=partial.get('comparison'),
                  sampled_peak=partial.get('sampled_peak'),
                  wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu)
    dump(output/f'{label}_complete.json', result)
    guard.check(files=True, threads=True)
    return result


def calculate(rt, output, guard, source):
    hashes = source_manifest(source, guard)
    dump(output/'input_identity.json', dict(source_attempt=str(source), sha256=hashes))
    reports = [case_diagnostic(rt, output, source, block, snr, guard) for block, snr in CASES]
    totals = {}
    for report in reports:
        for key, value in report['counts'].items():
            count(totals, key, value)
    if totals.get('density_nodes_started', 0) > 122880 or totals.get('derivative_probes_started', 0) > 8:
        raise RuntimeError('diagnostic work exceeded fixed reservation')
    complete = all(report['status'] == 'completed' for report in reports)
    if complete and (totals['density_nodes_completed'] != 122880 or totals['derivative_probes_completed'] != 8):
        raise RuntimeError('complete diagnostic has incomplete work accounting')
    summary = dict(cases=reports, counts=totals, diagnostic_complete=complete,
                   new_observations=0, receiver_calls=0, decoder_calls=0,
                   independent_blocks=0, backend_fixture_calls=0,
                   scope='saved-potential resolution evidence; no receiver rerun or rigorous integral certificate')
    dump(output/'quadrature_summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--source-attempt', type=Path, default=SOURCE_ATTEMPT)
    parser.add_argument('--stage', default='QUAD-DIAG-01')
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
                 artifact_root=args.artifact_root, rt=rt, extra_sources=input_paths(source))


if __name__ == '__main__':
    main()
