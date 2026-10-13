"""Registered engineering/development driver. --print-imports only imports.

python -m experiments.afdm_sp_fractional_receiver_20261007.study --kind
engineering|development --stage NAME --artifact-root /data/guoyikun/NEW_ROOT
Engineering additionally requires --math-attempt PATH. The main session
freezes run_contract.json and source/input hashes before invoking this driver.
"""
import argparse
import gc
import json
from pathlib import Path
import shutil
import statistics
import time

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from . import protocol, quadrature_diagnostic as saved, runtime
from .runtime import save_new

SEED_NAMESPACE = (20261007, 703)
SNR_VALUES = (6, 8)
BLOCKS = 4


def configuration(kind, *, variant='fixed', math_attempt=None, population_attempt=None):
    config = dict(seed='none' if kind == 'engineering' else list(SEED_NAMESPACE),
                  new_observations=0 if kind == 'engineering' else 8,
                  independent_blocks=0 if kind == 'engineering' else 4,
                  receiver_calls=1 if kind == 'engineering' else 24, decoder_calls=0,
                  receiver_boundary_rejection_calls=1 if kind == 'engineering' else 0,
                  receiver_payload_executions=0 if kind == 'engineering' else 24,
                  backend_fixture_calls=0)
    if kind == 'engineering':
        from .engineering import FIXTURES
        config.update(fixtures=FIXTURES, saved_math_cases=[8, 16, 1024],
                      operator_checks_per_case=7, data_steps_per_case=3,
                      saved_moment_data_power=.55, data_step_working_power=.5,
                      data_step_inputs='saved probabilities/y/pilot; recompute Pd=.5 moments',
                      scope='component regression; one invalid-input boundary call; no BER')
    elif kind == 'development':
        config.update(arms=list(runtime.ARMS), snr_db=list(SNR_VALUES), blocks=BLOCKS,
                      n=1024, rho=.5, prefix_length=102, qpsk='all-I then all-Q',
                      sigma2='10**(-snr_db/10); no G1 energy rescaling',
                      generator='G0 normalized gains -> untruncated G1 CPP',
                      uncoded=True, seed_components=dict(channel=1, message=2, noise=3),
                      arm_order='rotate by block modulo 3; same order at both SNRs',
                      dense_H_saved=False, working_prior='CN(0,I/P), uniform[-3,3], uniform QPSK',
                      sweeps=20, data_steps_per_sweep=3, quadrature=[128, 256, 512, 1024],
                      thresholds=dict(complete_calls=24, continuous_point_error_ratio=.9,
                                      continuous_scalar_latency_ratio=1.25,
                                      continuous_not_worse_than_scalar=True, point_zero='inconclusive'))
    else:
        raise ValueError('unregistered stage kind')
    if variant not in ('fixed', 'adaptive', 'collapsed'):
        raise ValueError('unregistered receiver variant')
    if variant == 'fixed':
        if population_attempt is not None:
            raise ValueError('saved population belongs only to the adaptive protocol')
        return config
    if variant == 'collapsed' and kind == 'engineering':
        if population_attempt is not None:
            raise ValueError('population belongs only to development')
        from . import collapsed_engineering
        return collapsed_engineering.configuration(math_attempt)
    if kind == 'engineering':
        if population_attempt is not None:
            raise ValueError('population belongs only to development')
        from . import adaptive_engineering
        config.update(adaptive_engineering.configuration(math_attempt))
    else:
        paths = population_input_paths(population_attempt)
        config.update(variant=variant, seed='none', new_observations=0, independent_blocks=0,
                      source_independent_blocks=4, source_observations=8,
                      population_source=str(Path(population_attempt).resolve()),
                      saved_input_paths=[str(path) for path in paths],
                      generator='none; byte-copy and load original DEV population',
                      source_seed=list(SEED_NAMESPACE),
                      source_seed_components=config.pop('seed_components'),
                      population_preparation='raw byte copies; truth payloads opened only after all receiver outputs seal')
        if variant == 'adaptive':
            config.update(quadrature=dict(continuous='adaptive_GK15_G7', initial='original fixed truncated Gaussian',
                                      initial_panels=16, max_bisections=26,
                                      cumulative_density_nodes_per_update_cap=1020,
                                      center_derivatives_per_update_cap=68,
                                      estimate_tolerance=1e-6, discrete_tail_tolerance=1e-14,
                                      rule_validations_per_continuous_receiver=1),
                      certified_continuous_error=False)
        else:
            from . import local_search
            config.update(arms=list(runtime.COLLAPSED_ARMS), receiver_calls=32, receiver_payload_executions=32,
                          arm_order='rotate by block modulo 4; same order at both SNRs',
                          sweeps=dict(f1_scalar=None, vb_point=20, vb_local_point=5, vb_collapsed_point=5),
                          scalar_detector_iterations=20, scalar_refinement_rounds=2,
                          quadrature='point_or_scalar', local_search=local_search.configuration(),
                          wall_cap_seconds=240, cpu_cap_seconds=240,
                          process_wall_cap_seconds=270, exit_grace_seconds=10,
                          thresholds=dict(complete_calls=32, collapsed_point_error_ratio=.9,
                              collapsed_scalar_latency_ratio=1.25, collapsed_not_worse_than_scalar=True,
                              matched_control='strictly fewer total errors than vb_local_point', point_zero='inconclusive'),
                          baseline_reproduction='independent sealed-raw audit against original scalar/point LLR and hard bits',
                          local_schedule='gain_before -> frozen-gain sequential Doppler -> gain_after -> 3 data steps',
                          collapsed_schedule='canonical source per coordinate -> score-only search -> full winner -> 3 data steps',
                          gain_covariance='full; no diagonalization', rejected_work='included',
                          inference_scope='five sweeps are a fixed budget; no convergence or global optimum claim')
    return config


def population_input_paths(attempt):
    if attempt is None or Path(attempt).resolve() != saved.SOURCE_ATTEMPT:
        raise ValueError('adaptive development requires the fixed original DEV population')
    root = Path(attempt).resolve()
    return [root/name for name in ('attempt.json', 'registration.json', 'population.json', 'public.json')]+[
        root/'observed'/f'block_{b}_snr_{s}.npz' for b in range(BLOCKS) for s in SNR_VALUES]+[
        root/'truth'/f'block_{b}.npz' for b in range(BLOCKS)]


def input_paths(kind, *, variant='fixed', math_attempt=None, population_attempt=None):
    if variant not in ('fixed', 'adaptive', 'collapsed'):
        raise ValueError('unregistered receiver variant')
    if kind == 'engineering':
        if variant == 'collapsed':
            from . import collapsed_engineering
            return collapsed_engineering.input_paths(math_attempt)
        from . import adaptive_engineering, engineering
        return (adaptive_engineering.input_paths(math_attempt) if variant == 'adaptive'
                else engineering.input_paths(math_attempt))
    if kind == 'development':
        return population_input_paths(population_attempt) if variant in ('adaptive', 'collapsed') else []
    raise ValueError('unregistered stage kind')


def load_saved_population(output, guard, attempt):
    """Validate/copy the fixed cohort as bytes; decode no observed or truth NPZ."""
    started, cpu = time.perf_counter(), time.process_time()
    root = Path(attempt).resolve()
    paths = population_input_paths(root)
    hashes = {str(path): saved._bound_sha(path, guard) for path in paths}
    source_attempt = json.loads((root/'attempt.json').read_text())
    registration = json.loads((root/'registration.json').read_text())
    population = json.loads((root/'population.json').read_text())
    public = json.loads((root/'public.json').read_text())
    if source_attempt['status'] != 'complete' or source_attempt['exit_code'] != 0:
        raise ValueError('saved population source did not complete')
    if registration['stage'] != 'RECEIVER-DEV-01' or registration['config'] != configuration('development'):
        raise ValueError('saved population is not the original registered DEV cohort')
    for path in paths[1:]:
        if source_attempt['artifact_sha256'][str(path)] != hashes[str(path)]:
            raise ValueError('saved population artifact differs from source attempt')
    runtime.validate_public(public)
    if population['public'] != public or population['dense_H_saved']:
        raise ValueError('saved population public metadata differs')
    manifest = population['manifest']
    if [(row['block'], row['snr_db']) for row in manifest] != list(saved.CASES):
        raise ValueError('saved population is not the fixed eight ordered observations')
    copies = {'public.json': 'public.json', 'population.json': 'source_population.json'}
    for row in manifest:
        b, s = row['block'], row['snr_db']
        if (set(row) != {'block', 'snr_db', 'observed', 'observed_sha256', 'truth', 'truth_sha256'} or
                row['observed'] != f'observed/block_{b}_snr_{s}.npz' or row['truth'] != f'truth/block_{b}.npz'):
            raise ValueError('saved population path/field whitelist violation')
        for name in ('observed', 'truth'):
            if row[name+'_sha256'] != hashes[str(root/row[name])]:
                raise ValueError('saved population manifest hash differs')
            copies[row[name]] = row[name]
    copied = []
    for relative, destination in copies.items():
        source, target = root/relative, output/destination
        if saved._bound_sha(source, guard) != hashes[str(source)]:
            raise ValueError('saved population changed before byte copy')
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as reader, target.open('xb') as writer:
            shutil.copyfileobj(reader, writer)
        if protocol.sha(target) != hashes[str(source)]:
            raise ValueError('saved population byte copy hash differs')
        copied.append(dict(source=str(source), destination=destination, sha256=hashes[str(source)],
                           bytes=target.stat().st_size))
        guard.check(files=True)
    result = dict(manifest=manifest, public=public, source_attempt=str(root),
                  source_registration_sha256=hashes[str(root/'registration.json')],
                  copied_files=copied, copied_bytes=sum(row['bytes'] for row in copied),
                  preparation_wall_seconds=time.perf_counter()-started,
                  preparation_cpu_seconds=time.process_time()-cpu,
                  source_independent_blocks=4, source_observations=8, reused_population=True,
                  new_observations=0, independent_blocks=0, generator_calls=0,
                  observed_payloads_decoded=0, truth_payloads_decoded=0, dense_H_saved=False)
    dump(output/'population.json', result)
    return result


def generate_population(rt, output, guard):
    started, cpu_start = time.perf_counter(), time.process_time()
    original_rng = np.random.get_state()
    manifest = []
    try:
        setup_start = time.perf_counter()
        with runtime.observe_operations(rt, guard.check) as setup_counts:
            system, public = runtime.build_system(rt)
        setup_seconds = time.perf_counter()-setup_start
        dump(output/'public.json', public)
        for block in range(BLOCKS):
            block_start = time.perf_counter()
            dump(output/f'generation_{block}_started.json', dict(block=block))
            rng_requests = []

            def rng_factory(replicate, index, component, *, split):
                if replicate != 0 or index != block or split != 1 or component not in (1, 2, 3):
                    raise ValueError('unexpected generator RNG request')
                rng_requests.append(component)
                return np.random.default_rng(np.random.SeedSequence([*SEED_NAMESPACE, block, component]))

            guard.add('independent_blocks')
            with runtime.observe_operations(rt, guard.check) as operations:
                raw = rt.frames.make_frame(system, {'n': 2048}, 0, block, SNR_VALUES[0],
                                            uncoded=True, split=1, rng_factory=rng_factory)
                physical, diagnostics = rt.g1.physical_observation(raw, system, prefix_length=102)
                if diagnostics['gain_normalization'] != 'reuse_g0_physical_gains_without_rescaling':
                    raise ValueError('physical gain normalization changed')
                if rng_requests != [1, 2, 3]:
                    raise ValueError('generator component stream call sequence changed')
            truth = dict(coded=physical['coded'], data=physical['data'], noise=physical['noise'],
                         noiseless=physical['noiseless'],
                         delays=physical['params']['l_i'], dopplers=physical['params']['k_real'],
                         gains=physical['params']['g_i'], diagnostics=diagnostics,
                         channel_seed=int(raw['channel_seed']),
                         component_entropy={str(k): [*SEED_NAMESPACE, block, k] for k in (1, 2, 3)},
                         dense_H_saved=False)
            truth_path = output/'truth'/f'block_{block}.npz'
            truth_sha = save_new(rt, truth_path, truth, dict(role='truth', block=block))
            for snr in SNR_VALUES:
                frame, _ = rt.g1.reuse_at_snr(physical, diagnostics, snr)
                observed = {key: np.asarray(frame[key]) for key in ('y', 'pilot', 'sigma2')}
                path = output/'observed'/f'block_{block}_snr_{snr}.npz'
                identity = dict(role='observed', block=block, snr_db=snr)
                digest = save_new(rt, path, observed, identity)
                guard.add('new_observations')
                manifest.append(dict(block=block, snr_db=snr,
                                     observed=str(path.relative_to(output)), observed_sha256=digest,
                                     truth=str(truth_path.relative_to(output)), truth_sha256=truth_sha))
            dump(output/f'generation_{block}_complete.json', dict(block=block,
                seconds=time.perf_counter()-block_start, operations=operations,
                g0_calls=1, g1_calls=1, snr_reuse_calls=2, rng_component_calls=rng_requests,
                dense_H_saved=False, observed_snr_db=list(SNR_VALUES)))
            del raw, physical, truth, frame
            guard.check(files=True)
        del system
        gc.collect()
    finally:
        np.random.set_state(original_rng)
    generation = dict(manifest=manifest, public=public, setup_seconds=setup_seconds,
                      setup_operations=setup_counts, wall_seconds=time.perf_counter()-started,
                      cpu_seconds=time.process_time()-cpu_start, dense_H_saved=False)
    dump(output/'population.json', generation)
    return generation


def _load_bound(rt, output, relative, digest, identity):
    path = output/relative
    if protocol.sha(path) != digest:
        raise ValueError('artifact hash mismatch: '+relative)
    payload, _ = rt.evidence.load_artifact(path, identity)
    return payload


def receive_population(rt, output, population, guard, *, quadrature='fixed', arms=runtime.ARMS):
    if arms not in (runtime.ARMS, runtime.COLLAPSED_ARMS):
        raise ValueError('unregistered population arm set')
    expected_calls = BLOCKS*len(SNR_VALUES)*len(arms)
    records = []
    for row in population['manifest']:
        block, snr = row['block'], row['snr_db']
        shift = block % len(arms)
        ordered_arms = arms[shift:]+arms[:shift]
        for arm in ordered_arms:
            wall_start, cpu_start = time.perf_counter(), time.process_time()
            label = f'b{block}_snr{snr}_{arm}'
            dump(output/'calls'/f'{label}_started.json', dict(block=block, snr_db=snr, arm=arm))
            observed = _load_bound(rt, output, row['observed'], row['observed_sha256'],
                                   dict(role='observed', block=block, snr_db=snr))
            if set(observed) != {'y', 'pilot', 'sigma2'}:
                raise ValueError('observed artifact contains forbidden fields')
            for value in observed.values():
                if isinstance(value, np.ndarray):
                    value.setflags(write=False)
            guard.add('receiver_calls')
            guard.add('receiver_payload_executions')
            status = 'complete'

            def save_fatal(error, operations):
                save_new(rt, output/'calls'/f'{label}_fatal.npz',
                         dict(error_type=type(error).__name__, error=str(error),
                              evidence=getattr(error, 'evidence', {}), operations=operations),
                         dict(role='fatal_receiver_evidence', block=block, snr_db=snr, arm=arm))

            with runtime.observe_operations(rt, guard.check) as operations:
                try:
                    payload = runtime.receive_arm(rt, observed, population['public'], arm, quadrature=quadrature)
                except (FloatingPointError, np.linalg.LinAlgError) as error:
                    status = 'numerical_failure'
                    payload = dict(error_type=type(error).__name__, error=str(error),
                                   evidence=getattr(error, 'evidence', {}))
                except TimeoutError as error:
                    save_fatal(error, operations)
                    raise
                except OSError:
                    # Actual filesystem failures are fatal; another write may
                    # not be possible. The immutable started marker remains.
                    raise
                except Exception as error:
                    save_fatal(error, operations)
                    raise
            ready_wall = time.perf_counter()-wall_start
            raw_path = output/'calls'/f'{label}.npz'
            save_start = time.perf_counter()
            raw_sha = save_new(rt, raw_path, dict(status=status, payload=payload, operations=operations),
                               dict(role='receiver', block=block, snr_db=snr, arm=arm))
            saving_seconds = time.perf_counter()-save_start
            record = dict(block=block, snr_db=snr, arm=arm, status=status,
                          raw=str(raw_path.relative_to(output)), raw_sha256=raw_sha,
                          receiver_ready_wall_seconds=ready_wall,
                          raw_save_seconds=saving_seconds, operations=operations)
            if quadrature == 'adaptive':
                record['quadrature'] = 'adaptive' if arm == 'vb_continuous' else 'fixed_or_point'
            dump(output/'calls'/f'{label}_outcome.json', record)
            record.update(full_wall_seconds=time.perf_counter()-wall_start,
                          full_cpu_seconds=time.process_time()-cpu_start,
                          process_peak_rss_bytes=protocol.peak_rss())
            records.append(record)
            guard.check(files=True, threads=True)
            runtime.verify_imports(rt)
    if len(records) != expected_calls:
        raise RuntimeError(f'receiver population did not produce {expected_calls} attempt records')
    # No truth payload has been opened in the receiver phase. This immutable
    # seal is written before any score function can load a truth file.
    dump(output/'receiver_seal.json', dict(records=records, receiver_calls=expected_calls,
         decoder_calls=0, truth_payloads_opened_for_scoring=0))
    return records


def score_population(rt, output, population, records, *, arms=runtime.ARMS):
    if arms not in (runtime.ARMS, runtime.COLLAPSED_ARMS):
        raise ValueError('unregistered scoring arm set')
    expected_calls = BLOCKS*len(SNR_VALUES)*len(arms)
    seal_path = output/'receiver_seal.json'
    seal = json.loads(seal_path.read_text())
    if seal['records'] != records or len(records) != expected_calls:
        raise ValueError('receiver seal mismatch')
    for row in records:
        if protocol.sha(output/row['raw']) != row['raw_sha256']:
            raise ValueError('sealed receiver output changed')
    truth_by_block = {}
    for row in population['manifest']:
        if row['block'] not in truth_by_block:
            truth_by_block[row['block']] = _load_bound(
                rt, output, row['truth'], row['truth_sha256'], dict(role='truth', block=row['block']))
    scores, hard_by_case = [], {}
    for row in records:
        errors = None
        if row['status'] == 'complete':
            payload = _load_bound(rt, output, row['raw'], row['raw_sha256'],
                                 dict(role='receiver', block=row['block'], snr_db=row['snr_db'], arm=row['arm']))
            hard = payload['payload']['hard_bits']
            truth = truth_by_block[row['block']]['coded']
            if hard.shape != (2048,) or truth.shape != (2048,):
                raise ValueError('uncoded bit denominator differs')
            errors = int(np.count_nonzero(hard != truth))
            if arms == runtime.COLLAPSED_ARMS:
                hard_by_case[(row['block'], row['snr_db'], row['arm'])] = hard
        scores.append(dict(block=row['block'], snr_db=row['snr_db'], arm=row['arm'],
                           status=row['status'], bit_errors=errors, bit_denominator=2048,
                           full_wall_seconds=row['full_wall_seconds']))
    totals, medians, strata = {}, {}, {}
    for arm in arms:
        subset = [row for row in scores if row['arm'] == arm]
        totals[arm] = (sum(row['bit_errors'] for row in subset)
                       if all(row['bit_errors'] is not None for row in subset) else None)
        medians[arm] = statistics.median(row['full_wall_seconds'] for row in subset)
        strata[arm] = {str(snr): [row for row in subset if row['snr_db'] == snr] for snr in SNR_VALUES}
    complete = all(row['status'] == 'complete' for row in records)
    target = 'vb_collapsed_point' if arms == runtime.COLLAPSED_ARMS else 'vb_continuous'
    if not complete:
        verdict = 'failed: at least one arm output incomplete'
    elif totals['vb_point'] == 0:
        verdict = 'inconclusive: point has zero errors'
    elif (totals[target] <= .9*totals['vb_point'] and
          totals[target] <= totals['f1_scalar'] and
          medians[target] <= 1.25*medians['f1_scalar']):
        verdict = 'development screening threshold passed; not coded or confirmatory evidence'
    else:
        verdict = 'development screening threshold not met'
    result = dict(scores=scores, paired_blocks=[dict(block=block,
                  rows=[row for row in scores if row['block'] == block]) for block in range(BLOCKS)],
                  snr_strata=strata, total_bit_errors=totals, median_full_receiver_wall_seconds=medians,
                  complete_outputs=sum(row['status'] == 'complete' for row in records),
                  independent_blocks=4, snr_observations=8, receiver_calls=expected_calls, decoder_calls=0,
                  verdict=verdict, receiver_seal_sha256=protocol.sha(seal_path))
    if arms == runtime.COLLAPSED_ARMS:
        comparisons = []
        for block, snr in saved.CASES:
            local = next(row for row in records if (row['block'], row['snr_db'], row['arm']) ==
                         (block, snr, 'vb_local_point'))
            collapsed = next(row for row in records if (row['block'], row['snr_db'], row['arm']) ==
                             (block, snr, 'vb_collapsed_point'))
            comparison = dict(block=block, snr_db=snr, local_status=local['status'],
                collapsed_status=collapsed['status'],
                wall_difference=collapsed['full_wall_seconds']-local['full_wall_seconds'],
                cpu_difference=collapsed['full_cpu_seconds']-local['full_cpu_seconds'])
            if local['status'] == collapsed['status'] == 'complete':
                left = hard_by_case[(block, snr, 'vb_local_point')]
                right = hard_by_case[(block, snr, 'vb_collapsed_point')]
                truth = truth_by_block[block]['coded']
                wrong_left, wrong_right = left != truth, right != truth
                comparison.update(local_errors=int(np.count_nonzero(wrong_left)),
                    collapsed_errors=int(np.count_nonzero(wrong_right)),
                    hard_changes=int(np.count_nonzero(left != right)),
                    wrong_to_correct=int(np.count_nonzero(wrong_left & ~wrong_right)),
                    correct_to_wrong=int(np.count_nonzero(~wrong_left & wrong_right)),
                    error_difference=int(np.count_nonzero(wrong_right))-int(np.count_nonzero(wrong_left)))
            comparisons.append(comparison)
        result.update(matched_control_comparisons=comparisons,
                      matched_control_improvement=(totals['vb_collapsed_point'] < totals['vb_local_point']
                          if totals['vb_collapsed_point'] is not None and totals['vb_local_point'] is not None else None),
                      matched_control_scope='same sweep/search caps; actual work and latency may differ',
                      baseline_reproduction='pending independent comparison with original frozen scalar/point raw')
    if population.get('reused_population', False):
        result.update(reused_population=True, new_independent_blocks=0, new_observations=0,
                      evidence_scope='same original four blocks/eight observations; candidate screening only')
    dump(output/'scores.json', result)
    return result


def development(rt, output, guard, *, population_attempt=None, quadrature='fixed', variant=None):
    selected_variant = quadrature if variant is None else variant
    if (selected_variant not in ('fixed', 'adaptive', 'collapsed') or
            quadrature != ('adaptive' if selected_variant == 'adaptive' else 'fixed') or
            (selected_variant != 'fixed') != (population_attempt is not None)):
        raise ValueError('adaptive development requires saved population; fixed uses the original generator')
    population = (generate_population(rt, output, guard) if population_attempt is None
                  else load_saved_population(output, guard, population_attempt))
    arms = runtime.COLLAPSED_ARMS if selected_variant == 'collapsed' else runtime.ARMS
    records = receive_population(rt, output, population, guard, quadrature=quadrature, arms=arms)
    result = score_population(rt, output, population, records, arms=arms)
    result.update(total_receiver_wall_seconds=sum(row['full_wall_seconds'] for row in records),
                  total_receiver_cpu_seconds=sum(row['full_cpu_seconds'] for row in records),
                  cost_scope='receiver includes own F1/backend/per-call saving; generation/setup separately charged')
    if population_attempt is None:
        result.update(generator_setup_seconds=population['setup_seconds'],
                      complete_generation_wall_seconds=population['wall_seconds'],
                      complete_generation_cpu_seconds=population['cpu_seconds'])
    else:
        result.update(variant=selected_variant, population_source=str(Path(population_attempt).resolve()),
                      population_preparation_wall_seconds=population['preparation_wall_seconds'],
                      population_preparation_cpu_seconds=population['preparation_cpu_seconds'],
                      population_copied_bytes=population['copied_bytes'], generator_calls=0,
                      cost_scope='receiver includes own F1/backend/per-call saving; saved population copy/load separately charged')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('engineering', 'development'), required=True)
    parser.add_argument('--stage')
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--math-attempt', type=Path)
    parser.add_argument('--variant', choices=('fixed', 'adaptive', 'collapsed'), default='fixed')
    parser.add_argument('--population-attempt', type=Path)
    parser.add_argument('--print-imports', action='store_true')
    parser.add_argument('--print-config', action='store_true')
    args = parser.parse_args()
    preload_start = time.perf_counter()
    rt = runtime.preload()
    from . import adaptive_engineering, engineering
    if args.variant == 'collapsed':
        from . import collapsed_engineering
    rt.preload_seconds = time.perf_counter()-preload_start
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    config = configuration(args.kind, variant=args.variant, math_attempt=args.math_attempt,
                           population_attempt=args.population_attempt)
    if args.print_config:
        print(json.dumps(config, indent=2))
        return
    if args.artifact_root is None or not args.artifact_root.is_absolute() or not args.stage:
        parser.error('absolute --artifact-root and registered --stage are required')
    if args.kind == 'engineering':
        if args.math_attempt is None or not args.math_attempt.is_absolute():
            parser.error('engineering requires absolute --math-attempt')
        def calculate(output, guard):
            if args.variant == 'collapsed':
                return collapsed_engineering.calculate(rt, output, guard, args.math_attempt)
            if args.variant == 'adaptive':
                return adaptive_engineering.calculate(rt, output, guard, args.math_attempt)
            return engineering.calculate(rt, output, guard, args.math_attempt)
    else:
        if args.math_attempt is not None:
            parser.error('--math-attempt belongs only to engineering')
        def calculate(output, guard):
            return development(rt, output, guard, population_attempt=args.population_attempt,
                               quadrature='adaptive' if args.variant == 'adaptive' else 'fixed', variant=args.variant)
    extra_sources = input_paths(args.kind, variant=args.variant, math_attempt=args.math_attempt,
                                population_attempt=args.population_attempt)
    protocol.run(args.stage, args.kind, config, calculate, artifact_root=args.artifact_root, rt=rt,
                 extra_sources=extra_sources, wall_cap_seconds=config.get('wall_cap_seconds'))


if __name__ == '__main__':
    main()
