"""Observed-only matched B/Cfast/Cref Stage-B wrapper producer.

Every arm is a fresh complete receiver call. The historical Stage-A C record
is used only after each new call to enforce equivalence; it never enters a
receiver. There is no truth path or outcome-based scheduling in this process.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
STAGE_A = EXPERIMENTS / 'cstate_necessity_stageA_20260928'
sys.path[:0] = [str(EXPERIMENTS / 'tf_cstate_prospective_20260923'),
                str(EXPERIMENTS / 'tf_cstate_validation_20260922'),
                str(EXPERIMENTS / 'tf_production_gap_audit_20260922'),
                str(STAGE_A), str(HERE)]
from audit_io import attach, load_bound, sha256  # noqa: E402
from generate_population import verify_population_seal  # noqa: E402
from run_stage_a import (_compare_saved, _syndrome, append_json,  # noqa: E402
                         write_json_exclusive)


SCHEMA = 'cstate-necessity-stage-b-f1/1'
SOURCE_NAMES = ('f1_fast.py', 'f1_fast_native.py', 'f1_run_stage_b.py',
                'f1_launch_once.sh')
REFERENCE_FIELDS = ('delays', 'dopplers', 'gains', 'bank_centers',
                    'stopping_reason', 'objective_history', 'counters',
                    'pilot_energy', 'last_coordinate_gain')


def schedule(index: int) -> tuple[str, ...]:
    if index % 16 == 0:
        from itertools import permutations
        return tuple(permutations(('B', 'Cref', 'Cfast')))[(index // 16) % 6]
    nonreference_ordinal = index - 1 - index // 16
    return ('B', 'Cfast') if nonreference_ordinal % 2 == 0 else ('Cfast', 'B')


def _sealed_index(root: Path, expected: int) -> tuple[dict[tuple[str, str], dict], dict]:
    seal_path = root / 'observed_seal.json'
    seal = json.loads(seal_path.read_text())
    if seal.get('status') != 'pass' or seal.get('files', {}).get('ledger.jsonl') != sha256(root / 'ledger.jsonl'):
        raise ValueError(f'sealed Stage-A evidence differs: {root}')
    rows = [json.loads(line) for line in (root / 'ledger.jsonl').read_text().splitlines()]
    if len(rows) != expected or any(row['status'] != 'ok' for row in rows):
        raise ValueError('Stage-A reference ledger incomplete')
    selected = {}
    for row in rows:
        if row['arm'] not in ('B', 'C'):
            continue
        key = row['observation_id'], row['arm']
        if key in selected or seal['files'].get(row['raw_path']) != row['raw_sha256']:
            raise ValueError(f'Stage-A reference duplicate or raw hash differs: {key}')
        selected[key] = row
    if len(selected) != 2048:
        raise ValueError('Stage-A B/C reference count differs')
    return selected, seal


def preflight(args):
    if args.out.exists():
        raise FileExistsError('Stage-B output exists; no overwrite or implicit resume')
    if re.fullmatch(r'[0-9a-f]{40}', args.registration_commit) is None:
        raise ValueError('full registration Git commit required')
    registration = json.loads(args.registration.read_text())
    stage_a_registration = json.loads(args.stage_a_registration.read_text())
    if (registration.get('schema') != SCHEMA or registration.get('status') != 'locked'
            or registration.get('expected_calls') != 2112
            or registration.get('seconds_limit') != args.seconds_limit or args.seconds_limit != 2400.0):
        raise ValueError('Stage-B registration or time limit differs')
    if registration.get('source_hashes') != {
            name: sha256(HERE / name) for name in SOURCE_NAMES}:
        raise ValueError('Stage-B source bytes differ')
    if (registration.get('protocol_sha256') != sha256(args.protocol)
            or registration.get('stage_a_registration_sha256') != sha256(args.stage_a_registration)
            or registration.get('stage_a_observed_seal_sha256') != sha256(
                args.stage_a_observed / 'observed_seal.json')
            or registration.get('population_observed_seal_sha256') != sha256(
                args.population_observed / 'observed_seal.json')):
        raise ValueError('Stage-B protocol/input/reference binding differs')
    if stage_a_registration.get('status') != 'locked':
        raise ValueError('Stage-A registration is not locked')
    if stage_a_registration.get('source_hashes') != {
            name: sha256(STAGE_A / name) for name in
            ('f1.py', 'keep_slots.py', 'native_f1.py', 'run_stage_a.py')}:
        raise ValueError('frozen Stage-A F1 source bytes differ')
    dependencies = stage_a_registration.get('dependency_source_hashes')
    if not isinstance(dependencies, dict) or not dependencies:
        raise ValueError('frozen CSTATE source inventory missing')
    for relative, digest in dependencies.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or sha256(EXPERIMENTS / path) != digest:
            raise ValueError(f'frozen CSTATE source differs: {relative}')
    evidence = attach(args.source, args.baseline)
    from native_f1 import receive_f1
    from f1_fast_native import receive_f1_fast
    if (stage_a_registration.get('native_source_hashes') != evidence.source_hashes(args.source)
            or stage_a_registration.get('baseline_source_hashes') != evidence.source_hashes(args.baseline)):
        raise ValueError('frozen native/baseline source bytes differ')
    cache = (args.baseline / 'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/'
             'e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz')
    if stage_a_registration.get('ldpc_cache_sha256') != sha256(cache):
        raise ValueError('frozen code cache differs')
    verify_population_seal(args.population_observed)
    reference, reference_seal = _sealed_index(args.stage_a_observed, 4096 + 12)
    population_rows = [json.loads(line) for line in
                       (args.population_observed / 'ledger.jsonl').read_text().splitlines()]
    selected = [row for row in population_rows if row['snr_centi_db'] == 650]
    if len(selected) != 1024 or [row['frame'] for row in selected] != list(range(1024)):
        raise ValueError('Stage-B fixed full cohort differs')
    for row in selected:
        stem = row['observation_id']
        for arm in ('B', 'C'):
            old = reference[stem, arm]
            if (old['input_sha256'] != row['observation_sha256'] or
                    old['observation_hash'] != row['observation_hash'] or
                    old['stream_ids'] != row['stream_ids']):
                raise ValueError(f'Stage-B paired input identity differs: {stem}')
    from receiver import context
    import native_twofft as native
    environment = evidence.bind_runtime_environment()
    start = time.perf_counter()
    system, _, code, header = context()
    setup_seconds = time.perf_counter() - start
    evidence.verify_runtime_binding()
    if (system.N_total != 1024 or system.l_max_cap != 102 or system.rho != .5
            or header['code_g_sha256'] != stage_a_registration.get('code_g_sha256')):
        raise ValueError('Stage-B runtime system/code differs')
    with np.load(cache, allow_pickle=False) as saved:
        H = np.asarray(saved['H'], np.uint8)
    if H.shape != (1026, 2048):
        raise ValueError('Stage-B H shape differs')
    return dict(evidence=evidence, registration=registration,
                stage_a_registration=stage_a_registration, reference=reference,
                reference_seal=reference_seal, selected=selected, system=system,
                code=code, H=H, native=native, setup_seconds=setup_seconds,
                environment=environment, cache_sha256=sha256(cache),
                receive_f1=receive_f1, receive_f1_fast=receive_f1_fast)


def _compare_reference(evidence, root: Path, old_row: dict, raw: dict, arm: str) -> float:
    old = load_bound(evidence, root / old_row['raw_path'], old_row['raw_sha256'])
    if arm != 'B':
        if old['acquisition'] is None or raw['acquisition'] is None:
            raise ValueError('F1 acquisition record missing')
        if set(old['acquisition']) != set(raw['acquisition']):
            raise ValueError('F1 acquisition field inventory differs')
        largest = max((_compare_saved(old['acquisition'][key], raw['acquisition'][key], key)
                       for key in REFERENCE_FIELDS), default=0.)
        largest = max(largest,
                      _compare_saved(old['initial_geometry'], raw['initial_geometry']),
                      _compare_saved(old['entering_geometry'], raw['entering_geometry']),
                      _compare_saved(old['baseline_arrays'], raw['baseline_arrays']))
    else:
        largest = 0.
        if old['triggered'] != raw['triggered']:
            raise ValueError('current B trigger differs from sealed B')
        for key in ('r0_decoded', 'r1_decoded'):
            if not np.array_equal(old['baseline_arrays'][key], raw['baseline_arrays'][key]):
                raise ValueError(f'current B {key} differs from sealed B')
        if old['triggered'] and not np.array_equal(
                old['branch_decoder']['decoded'], raw['branch_decoder']['decoded']):
            raise ValueError('current B branch decoded bits differ from sealed B')
    if not np.array_equal(old['final_decoded'], raw['final_decoded']):
        raise ValueError(f'{arm} final bits differ from sealed Stage-A reference')
    return largest


def run(args) -> None:
    began = time.perf_counter()  # the registered 2400 s includes preflight/setup
    bound = preflight(args)
    if time.perf_counter() - began >= args.seconds_limit:
        raise TimeoutError('Stage-B cap reached during preflight')
    out = args.out
    out.mkdir(parents=True)
    for folder in ('checkpoints', 'raw', 'decisions'):
        (out / folder).mkdir()
    evidence = bound['evidence']
    registration = bound['registration']
    write_json_exclusive(out / 'manifest.json', dict(
        schema=SCHEMA, status='running', registration_sha256=sha256(args.registration),
        registration_commit=args.registration_commit,
        protocol_sha256=sha256(args.protocol),
        stage_a_registration_sha256=sha256(args.stage_a_registration),
        stage_a_observed_seal_sha256=sha256(args.stage_a_observed / 'observed_seal.json'),
        population_observed_seal_sha256=sha256(args.population_observed / 'observed_seal.json'),
        source_hashes=registration['source_hashes'],
        stage_a_source_hashes=bound['stage_a_registration']['source_hashes'],
        runtime_environment=bound['environment'], code_cache_sha256=bound['cache_sha256'],
        setup_seconds=bound['setup_seconds'], expected_calls=2112,
        reference_subset='frame_index%16==0 (64 IDs)',
        timing_boundary='before durable attempt journal and input load through durable decision write; ledger append and sealed-reference comparison excluded',
        failure_rule='first mismatch/failure stops invalid_partial; charged attempts/checkpoints retained; no subset risk or timing claim',
        args=sys.argv[:], pid=os.getpid(), created_epoch=time.time()))
    ledger = out / 'ledger.jsonl'
    attempts_path = out / 'attempts.jsonl'
    ledger.touch(exist_ok=False)
    attempts_path.touch(exist_ok=False)
    calls = 0
    try:
        for index, input_row in enumerate(bound['selected']):
            for arm in schedule(index):
                if time.perf_counter() - began >= args.seconds_limit:
                    raise TimeoutError('registered Stage-B time cap reached')
                calls += 1
                if calls > 2112:
                    raise ValueError('Stage-B call budget exceeded')
                stem = input_row['observation_id']
                origin = time.perf_counter()
                identity = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                                input_sha256=input_row['observation_sha256'])
                row = dict(status='inflight', attempt_index=calls, frame=index,
                           observation_id=stem, arm=arm,
                           input_sha256=input_row['observation_sha256'],
                           observation_hash=input_row['observation_hash'],
                           stream_ids=input_row['stream_ids'], checkpoints=[],
                           receiver_started=False)
                append_json(attempts_path, dict(attempt_index=calls,
                    observation_id=stem, arm=arm,
                    input_sha256=input_row['observation_sha256'],
                    started_epoch=time.time()))
                rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

                def sink(event, decoded, *, row=row, origin=origin,
                         stem=stem, arm=arm, identity=identity):
                    round_index = int(event['round'])
                    if round_index != len(row['checkpoints']):
                        raise ValueError('Stage-B checkpoint order differs')
                    decision_ready = time.perf_counter() - origin
                    path = out / 'checkpoints' / f'{stem}_{arm}_r{round_index}.npz'
                    digest = evidence.save_artifact(path,
                        dict(event=event, decoded=np.asarray(decoded).copy()),
                        dict(identity, round=round_index))
                    row['checkpoints'].append(dict(round=round_index,
                        path=str(path.relative_to(out)), artifact_sha256=digest,
                        decision_ready_seconds=decision_ready,
                        ready_seconds=time.perf_counter() - origin,
                        syndrome_weight=_syndrome(bound['H'], decoded)))

                try:
                    payload = load_bound(evidence,
                        args.population_observed / input_row['observation_path'],
                        input_row['observation_sha256'])
                    if (payload['observation_id'] != stem or
                            payload['observation_hash'] != input_row['observation_hash'] or
                            payload['stream_ids'] != input_row['stream_ids']):
                        raise ValueError('Stage-B observed semantic identity differs')
                    observation = payload['observation']
                    if set(observation) != {'y', 'pilot', 'sigma2'}:
                        raise ValueError('Stage-B observed input fields differ')
                    row['receiver_started'] = True
                    receiver_start = time.perf_counter()
                    if arm == 'B':
                        native_dec, arrays, timing = bound['native'].receive(
                            observation, bound['system'], bound['code'], rounds=2,
                            iterations=20, ce_mode='soft', gain_mode='joint',
                            checkpoint_sink=sink)
                    elif arm == 'Cref':
                        native_dec, arrays, timing = bound['receive_f1'](
                            observation, bound['system'], bound['code'], checkpoint_sink=sink)
                    else:
                        native_dec, arrays, timing = bound['receive_f1_fast'](
                            observation, bound['system'], bound['code'], checkpoint_sink=sink)
                    native_end = time.perf_counter()
                    if len(row['checkpoints']) != 2 or not np.array_equal(
                            native_dec['decoded'], arrays['r1_decoded']):
                        raise ValueError('Stage-B two-round native output incomplete')
                    syndrome = row['checkpoints'][-1]['syndrome_weight']
                    triggered = bool(arm == 'B' and syndrome != 0)
                    branch = None
                    branch_start = time.perf_counter()
                    if triggered:
                        from run_validation import _branch
                        import geometry_validation as kernel
                        branch = _branch(observation, bound['system'], bound['code'],
                                         bound['native'], kernel, arrays, 'CSTATE20')
                        result, decoder = branch['result'], branch['decoder']
                        sink(dict(round=2, ready=time.perf_counter() - origin,
                            ce=result.elapsed_seconds,
                            inference=branch['exclusive_stages']['tf'],
                            decoder=branch['exclusive_stages']['ldpc'],
                            ce_evaluations=result.evaluations, inference_iterations=20,
                            decoder_iterations=int(decoder['iterations']),
                            snapshot=dict(decoded=decoder['decoded'],
                                input_llr=decoder['incoming_llr'], app=decoder['raw_app'],
                                check=decoder['raw_check_extrinsic'],
                                delays=np.asarray([p.delay for p in result.paths]),
                                dopplers=np.asarray([p.doppler for p in result.paths]),
                                geometry_gains=result.gains,
                                inference_gains=branch['detector']['gains'])),
                             decoder['decoded'])
                    branch_end = time.perf_counter()
                    final_decoder = native_dec if branch is None else branch['decoder']
                    final_decoded = np.asarray(final_decoder['decoded'], np.uint8).copy()
                    final_info = None
                    from receiver import extract_info
                    final_info = np.asarray(extract_info(bound['code'], final_decoded), np.uint8)
                    if final_info.shape != (1024,):
                        raise ValueError('Stage-B final information vector differs')
                    final_syndrome = _syndrome(bound['H'], final_decoded)
                    raw_start = time.perf_counter()
                    raw_path = out / 'raw' / f'{stem}_{arm}.npz'
                    raw = dict(observation_id=stem, arm=arm,
                        input_sha256=input_row['observation_sha256'],
                        stream_ids=input_row['stream_ids'],
                        baseline_arrays=arrays, native_events=timing['events'],
                        native_timing={k: v for k, v in timing.items() if k != 'acquisition'},
                        acquisition=None if 'acquisition' not in timing else {
                            k: v for k, v in timing['acquisition'].items() if k != 'channel'},
                        native_decoder=native_dec, triggered=triggered,
                        baseline_syndrome_weight=syndrome,
                        initial_geometry=timing.get('initial_geometry'),
                        entering_geometry=timing.get('entering_geometry'),
                        geometry_result=None if branch is None else asdict(branch['result']),
                        branch_inputs=None if branch is None else dict(
                            app_input=branch['app_input'], check_prior=branch['check_prior'],
                            ce_mu=branch['ce_mu'], ce_variance=branch['ce_variance']),
                        branch_detector=None if branch is None else branch['detector'],
                        branch_decoder=None if branch is None else branch['decoder'],
                        final_decoded=final_decoded, final_info=final_info)
                    raw_hash = evidence.save_artifact(raw_path, raw, identity)
                    raw_ready = time.perf_counter() - origin
                    decision_path = out / 'decisions' / f'{stem}_{arm}.json'
                    decision = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                        input_sha256=input_row['observation_sha256'], triggered=triggered,
                        baseline_syndrome_weight=syndrome,
                        final_syndrome_weight=final_syndrome,
                        final_decoded_sha256=hashlib.sha256(final_decoded.tobytes()).hexdigest(),
                        final_decoded=final_decoded.astype(int).tolist(),
                        final_info=final_info.astype(int).tolist(),
                        checkpoints=row['checkpoints'], raw_path=str(raw_path.relative_to(out)),
                        raw_sha256=raw_hash, source_hashes=registration['source_hashes'])
                    decision_start = time.perf_counter()
                    decision_hash = write_json_exclusive(decision_path, decision)
                    complete = time.perf_counter() - origin
                    old_arm = 'B' if arm == 'B' else 'C'
                    largest = _compare_reference(evidence, args.stage_a_observed,
                        bound['reference'][stem, old_arm], raw, arm)
                    row.update(status='ok', triggered=triggered,
                        baseline_syndrome_weight=syndrome,
                        final_syndrome_weight=final_syndrome,
                        final_decoded_sha256=decision['final_decoded_sha256'],
                        complete_latency_seconds=complete,
                        native_seconds=native_end-receiver_start,
                        acquisition_seconds=timing['pilot_seconds'],
                        refit_seconds=sum(event['ce'] for event in timing['events']),
                        tf_seconds=sum(event['inference'] for event in timing['events']),
                        decoder_seconds=sum(event['decoder'] for event in timing['events']),
                        branch_seconds=0. if branch is None else branch_end-branch_start,
                        raw_serialization_seconds=raw_ready-(raw_start-origin),
                        decision_record_seconds=complete-(decision_start-origin),
                        raw_artifact_ready_seconds=raw_ready,
                        reference_max_difference=largest,
                        reference_raw_sha256=bound['reference'][stem, old_arm]['raw_sha256'],
                        raw_path=str(raw_path.relative_to(out)), raw_sha256=raw_hash,
                        decision_path=str(decision_path.relative_to(out)),
                        decision_sha256=decision_hash,
                        ledger_append_included_in_latency=False,
                        rss_peak_kib_before=rss_before,
                        rss_peak_kib_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                    append_json(ledger, row)
                except BaseException as error:
                    row.update(status='failed', error=repr(error),
                               traceback=traceback.format_exc(),
                               charged_seconds=time.perf_counter()-origin)
                    append_json(ledger, row)
                    raise
        if calls != 2112:
            raise ValueError('Stage-B final complete-call allocation differs')
        files = {str(path.relative_to(out)): sha256(path) for path in out.rglob('*')
                 if path.is_file() and path.name != 'observed_seal.json'}
        write_json_exclusive(out / 'observed_seal.json', dict(schema=SCHEMA,
            status='pass', files=files, observations=1024, calls=2112,
            reference_subset_calls=64, attempts=calls,
            registration_sha256=sha256(args.registration),
            stage_a_observed_seal_sha256=sha256(
                args.stage_a_observed / 'observed_seal.json'),
            population_observed_seal_sha256=sha256(
                args.population_observed / 'observed_seal.json')))
    except BaseException as error:
        write_json_exclusive(out / 'invalid_partial.json', dict(status='invalid_partial',
            error=repr(error), traceback=traceback.format_exc(), attempts=calls,
            elapsed_seconds=time.perf_counter()-began))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('registration', 'protocol', 'stage-a-registration',
                 'stage-a-observed', 'population-observed', 'source',
                 'baseline', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--registration-commit', required=True)
    parser.add_argument('--seconds-limit', required=True, type=float)
    run(parser.parse_args())
