"""Observed-only Stage-A A/B/C/D and C-triggered E receiver producer.

No truth path or scoring label is accepted by this process. A/B are independent
complete native calls and C/D/E each independently run their own F1 prefix.
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
sys.path[:0] = [str(EXPERIMENTS / 'tf_cstate_prospective_20260923'),
                str(EXPERIMENTS / 'tf_cstate_validation_20260922'),
                str(EXPERIMENTS / 'tf_production_gap_audit_20260922'), str(HERE)]
from audit_io import attach, load_bound, sha256  # noqa: E402
from generate_population import verify_population_seal  # noqa: E402
from run_validation import _branch  # noqa: E402


SCHEMA = 'cstate-necessity-stage-a/1'
ARMS = ('A', 'B', 'C', 'D')
SOURCE_NAMES = ('f1.py', 'keep_slots.py', 'native_f1.py', 'run_stage_a.py')


def schedule(index: int) -> tuple[str, ...]:
    return ARMS[index % 4:] + ARMS[:index % 4]


def update_c_trigger(previous: bool, arm: str, syndrome: int) -> bool:
    return syndrome != 0 if arm == 'C' else previous


def write_json_exclusive(path: Path, value: dict) -> str:
    with path.open('x') as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    return sha256(path)


def append_json(path: Path, value: dict) -> None:
    with path.open('a') as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def _all_files(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): sha256(path) for path in root.rglob('*')
            if path.is_file() and path.name != 'observed_seal.json'}


def _syndrome(H: np.ndarray, decoded: np.ndarray) -> int:
    bits = np.asarray(decoded, np.uint8)
    if bits.shape != (2048,) or not np.isin(bits, (0, 1)).all():
        raise ValueError('invalid saved decoded bits')
    return int(np.count_nonzero((H @ bits) % 2))


def _compare_saved(left, right, key='') -> float:
    """Frozen A/B parity: every array, exact bits, absolute 2e-10 continuous."""
    if isinstance(left, dict):
        if not isinstance(right, dict) or set(left) != set(right):
            raise ValueError(f'historical native inventory differs: {key}')
        return max((_compare_saved(left[k], right[k], f'{key}/{k}') for k in left), default=0.)
    if isinstance(left, (tuple, list)):
        if not isinstance(right, type(left)) or len(left) != len(right):
            raise ValueError(f'historical native sequence differs: {key}')
        return max((_compare_saved(a, b, f'{key}/{i}') for i, (a, b) in
                    enumerate(zip(left, right, strict=True))), default=0.)
    if isinstance(left, np.ndarray):
        a, b = np.asarray(left), np.asarray(right)
        if a.shape != b.shape or a.dtype != b.dtype:
            raise ValueError(f'historical native shape/dtype differs: {key}')
        if key.endswith('decoded') or not np.issubdtype(a.dtype, np.number):
            if not np.array_equal(a, b):
                raise ValueError(f'historical native exact field differs: {key}')
            return 0.
        delta = float(np.max(np.abs(a-b))) if a.size else 0.
        if not np.allclose(a, b, atol=2e-10, rtol=0):
            raise ValueError(f'historical native array differs: {key}, max={delta}')
        return delta
    if isinstance(left, (int, float, complex, np.number)) and not isinstance(left, bool):
        if not np.isclose(left, right, atol=2e-10, rtol=0):
            raise ValueError(f'historical native scalar differs: {key}')
        return float(abs(left-right))
    if left != right:
        raise ValueError(f'historical native value differs: {key}')
    return 0.


def _historical_index(root: Path) -> tuple[dict[tuple[str, str], dict], dict]:
    seal = json.loads((root / 'observed_seal.json').read_text())
    if seal.get('status') != 'pass' or seal.get('receiver_calls') != 6144:
        raise ValueError('historical A/B observed seal incomplete')
    if seal.get('files', {}).get('ledger.jsonl') != sha256(root / 'ledger.jsonl'):
        raise ValueError('historical A/B sealed ledger differs')
    rows = [json.loads(x) for x in (root / 'ledger.jsonl').read_text().splitlines()]
    if len(rows) != 6144 or any(row['status'] != 'ok' for row in rows):
        raise ValueError('historical A/B ledger incomplete')
    index = {}
    for row in rows:
        if row['observation_id'].startswith('s650_'):
            key = row['observation_id'], row['arm']
            if key in index or seal['files'].get(row['raw_path']) != row['raw_sha256']:
                raise ValueError('historical A/B duplicate/raw binding differs')
            index[key] = row
    if len(index) != 2048:
        raise ValueError('historical 6.5-dB A/B pair count differs')
    return index, seal


def preflight(args):
    for root in (args.population_observed, args.historical_observed):
        if not root.is_dir():
            raise FileNotFoundError(root)
    if args.out.exists():
        raise FileExistsError('Stage-A output root exists; no implicit resume/overwrite')
    if re.fullmatch(r'[0-9a-f]{40}', args.registration_commit) is None:
        raise ValueError('full registration Git commit required')
    registration = json.loads(args.registration.read_text())
    if registration.get('schema') != SCHEMA or registration.get('status') != 'locked':
        raise ValueError('Stage-A registration is not locked')
    if (not np.isfinite(args.seconds_limit) or args.seconds_limit <= 0 or
            registration.get('seconds_limit') != args.seconds_limit):
        raise ValueError('Stage-A registered operational time cap differs')
    source_hashes = registration.get('source_hashes')
    if not isinstance(source_hashes, dict) or any(
        source_hashes.get(name) != sha256(HERE / name) for name in SOURCE_NAMES):
        raise ValueError('Stage-A producer source binding differs')
    if registration.get('preregistration_sha256') != sha256(
        args.preregistration) or registration.get('f1_spec_sha256') != sha256(args.f1_spec):
        raise ValueError('Stage-A frozen contract binding differs')
    historical_registration = json.loads(args.historical_registration.read_text())
    dependencies = historical_registration.get('registration_source_hashes')
    if (registration.get('historical_registration_sha256') != sha256(args.historical_registration)
            or registration.get('dependency_source_hashes') != dependencies
            or not isinstance(dependencies, dict) or not dependencies):
        raise ValueError('Stage-A original CSTATE dependency inventory differs')
    for relative, digest in dependencies.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError('Stage-A dependency path escapes experiments')
        resolved = (EXPERIMENTS / path).resolve()
        if not resolved.is_relative_to(EXPERIMENTS.resolve()) or sha256(resolved) != digest:
            raise ValueError(f'Stage-A dependency source differs: {relative}')
    evidence = attach(args.source, args.baseline)
    if (registration.get('native_source_hashes') != evidence.source_hashes(args.source)
            or registration.get('baseline_source_hashes') != evidence.source_hashes(args.baseline)):
        raise ValueError('Stage-A frozen receiver source bytes differ')
    cache = args.baseline / 'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    if registration.get('ldpc_cache_sha256') != sha256(cache):
        raise ValueError('Stage-A code cache differs')
    population_seal = verify_population_seal(args.population_observed)
    if (registration.get('population_observed_seal_sha256') !=
            sha256(args.population_observed / 'observed_seal.json')):
        raise ValueError('Stage-A observed population seal differs')
    historical, historical_seal = _historical_index(args.historical_observed)
    historical_manifest = json.loads((args.historical_observed / 'manifest.json').read_text())
    if (historical_manifest.get('registration_sha256') != sha256(args.historical_registration)
            or historical_manifest.get('population_observed_seal_sha256') !=
                sha256(args.population_observed / 'observed_seal.json')):
        raise ValueError('Stage-A historical A/B provenance differs')
    if registration.get('historical_observed_seal_sha256') != sha256(
        args.historical_observed / 'observed_seal.json'):
        raise ValueError('Stage-A historical A/B seal differs')
    if registration.get('historical_frame_outcomes_sha256') != sha256(
        args.historical_frame_outcomes):
        raise ValueError('Stage-A historical outcome-label table differs')
    population_rows = [json.loads(line) for line in
                       (args.population_observed / 'ledger.jsonl').read_text().splitlines()]
    selected = [row for row in population_rows if row['snr_centi_db'] == 650]
    if len(selected) != 1024 or [row['frame'] for row in selected] != list(range(1024)):
        raise ValueError('Stage-A full 6.5-dB cohort differs')
    for row in selected:
        stem = row['observation_id']
        for old_arm in ('TF', 'TF_CSTATE'):
            old = historical[stem, old_arm]
            if (old['input_sha256'] != row['observation_sha256'] or
                    old['observation_hash'] != row['observation_hash'] or
                    old['stream_ids'] != row['stream_ids']):
                raise ValueError(f'Stage-A historical input pairing differs: {stem}')
    from receiver import context
    import native_twofft as native
    import geometry_validation as kernel
    from native_f1 import receive_f1
    environment = evidence.bind_runtime_environment()
    start = time.perf_counter()
    system, _, code, header = context()
    setup_seconds = time.perf_counter() - start
    evidence.verify_runtime_binding()
    if (system.N_total != 1024 or system.l_max_cap != 102 or system.rho != .5
            or header['code_g_sha256'] != registration.get('code_g_sha256')):
        raise ValueError('Stage-A runtime system/code differs')
    with np.load(cache, allow_pickle=False) as saved:
        H = np.asarray(saved['H'], np.uint8)
    if H.shape != (1026, 2048):
        raise ValueError('Stage-A H shape differs')
    return dict(registration=registration, evidence=evidence, selected=selected,
        historical=historical, historical_seal=historical_seal,
        population_seal=population_seal, system=system, code=code, H=H,
        native=native, kernel=kernel, receive_f1=receive_f1,
        setup_seconds=setup_seconds, environment=environment,
        cache_sha256=sha256(cache))


def _acquisition_record(timing: dict | None) -> dict | None:
    if timing is None or 'acquisition' not in timing:
        return None
    return {key: value for key, value in timing['acquisition'].items() if key != 'channel'}


def run(args):
    bound = preflight(args)
    out = args.out
    out.mkdir(parents=True)
    for folder in ('checkpoints', 'raw', 'decisions'):
        (out / folder).mkdir()
    registration = bound['registration']
    evidence = bound['evidence']
    environment = bound['environment']
    write_json_exclusive(out / 'manifest.json', dict(schema=SCHEMA, status='running',
        registration_sha256=sha256(args.registration),
        registration_commit=args.registration_commit,
        preregistration_sha256=sha256(args.preregistration),
        population_observed_seal_sha256=sha256(args.population_observed / 'observed_seal.json'),
        historical_observed_seal_sha256=sha256(args.historical_observed / 'observed_seal.json'),
        source_hashes=registration['source_hashes'], runtime_environment=environment,
        setup_seconds=bound['setup_seconds'], code_cache_sha256=bound['cache_sha256'],
        expected_primary_calls=4096, maximum_local_calls=1024,
        timing_boundary='before durable attempt journal and input load through durable decision write; final ledger append excluded',
        failure_rule='any numerical or integrity failure stops with invalid_partial; retain charged attempts and ready checkpoints; no subset FER or K/S/C/E verdict',
        peak_rss_unit='Linux ru_maxrss KiB; process-cumulative, not per-arm isolated peak',
        args=sys.argv[:], pid=os.getpid(), created_epoch=time.time()))
    ledger = out / 'ledger.jsonl'
    ledger.touch(exist_ok=False)
    attempt_journal = out / 'attempts.jsonl'
    attempt_journal.touch(exist_ok=False)
    attempts = 0
    local_calls = 0
    started = time.perf_counter()
    old_to_new = {'A': 'TF', 'B': 'TF_CSTATE'}
    try:
        for index, input_row in enumerate(bound['selected']):
            if time.perf_counter() - started >= args.seconds_limit:
                raise TimeoutError('registered Stage-A operational cap reached')
            stem = input_row['observation_id']
            c_trigger = False
            c_syndrome = None
            f1_reference = None
            for arm in schedule(index) + ('E',):
                if arm == 'E' and not c_trigger:
                    continue
                if arm == 'E':
                    local_calls += 1
                    if local_calls > 1024:
                        raise ValueError('E call budget exceeded')
                attempts += 1
                origin = time.perf_counter()
                rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                identity = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                                input_sha256=input_row['observation_sha256'])
                row = dict(status='inflight', attempt_index=attempts, observation_id=stem,
                    frame=index, arm=arm, input_sha256=input_row['observation_sha256'],
                    observation_hash=input_row['observation_hash'],
                    stream_ids=input_row['stream_ids'], checkpoints=[], receiver_started=False)
                last_bits = None
                append_json(attempt_journal, dict(attempt_index=attempts,
                    observation_id=stem, arm=arm, input_sha256=input_row['observation_sha256'],
                    started_epoch=time.time()))

                def sink(event, decoded, *, row=row, origin=origin, stem=stem,
                         arm=arm, identity=identity):
                    nonlocal last_bits
                    round_index = int(event['round'])
                    if round_index != len(row['checkpoints']):
                        raise ValueError('Stage-A checkpoint order differs')
                    decision_ready = time.perf_counter() - origin
                    path = out / 'checkpoints' / f'{stem}_{arm}_r{round_index}.npz'
                    digest = evidence.save_artifact(path,
                        dict(event=event, decoded=np.asarray(decoded).copy()),
                        dict(identity, round=round_index))
                    last_bits = np.asarray(decoded, np.uint8).copy()
                    row['checkpoints'].append(dict(round=round_index,
                        path=str(path.relative_to(out)), artifact_sha256=digest,
                        decision_ready_seconds=decision_ready,
                        ready_seconds=time.perf_counter() - origin,
                        syndrome_weight=_syndrome(bound['H'], last_bits)))

                try:
                    payload = load_bound(evidence,
                        args.population_observed / input_row['observation_path'],
                        input_row['observation_sha256'])
                    if (payload['observation_id'] != stem or
                            payload['observation_hash'] != input_row['observation_hash'] or
                            payload['stream_ids'] != input_row['stream_ids']):
                        raise ValueError('Stage-A observed semantic identity differs')
                    observation = payload['observation']
                    if set(observation) != {'y', 'pilot', 'sigma2'}:
                        raise ValueError('Stage-A observed fields differ')
                    row['receiver_started'] = True
                    receiver_start = time.perf_counter()
                    if arm in ('A', 'B'):
                        native_dec, arrays, timing = bound['native'].receive(observation,
                            bound['system'], bound['code'], rounds=2, iterations=20,
                            ce_mode='soft', gain_mode='joint', checkpoint_sink=sink)
                    else:
                        native_dec, arrays, timing = bound['receive_f1'](observation,
                            bound['system'], bound['code'], checkpoint_sink=sink)
                    native_end = time.perf_counter()
                    if len(row['checkpoints']) != 2 or not np.array_equal(
                            native_dec['decoded'], arrays['r1_decoded']):
                        raise ValueError('Stage-A two-round native output incomplete')
                    syndrome = row['checkpoints'][-1]['syndrome_weight']
                    if arm in ('C', 'D', 'E'):
                        if f1_reference is None:
                            f1_reference = (arrays, timing['initial_geometry'], syndrome)
                        else:
                            _compare_saved(f1_reference[0], arrays)
                            _compare_saved(f1_reference[1], timing['initial_geometry'])
                            if syndrome != f1_reference[2]:
                                raise ValueError('independent F1 native syndrome differs')
                        if arm == 'C':
                            c_syndrome = syndrome
                        if arm == 'E' and (c_syndrome is None or c_syndrome == 0
                                           or syndrome != c_syndrome):
                            raise ValueError('E native trigger differs from C')
                    c_trigger = update_c_trigger(c_trigger, arm, syndrome)
                    triggered = bool((arm in ('B', 'D') and syndrome != 0) or arm == 'E')
                    branch = None
                    branch_start = time.perf_counter()
                    if triggered:
                        mode = 'LOCAL20' if arm == 'E' else 'CSTATE20'
                        branch = _branch(observation, bound['system'], bound['code'],
                            bound['native'], bound['kernel'], arrays, mode)
                        result = branch['result']
                        decoder = branch['decoder']
                        sink(dict(round=2, ready=time.perf_counter()-origin,
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
                                inference_gains=branch['detector']['gains'])), decoder['decoded'])
                    branch_end = time.perf_counter()
                    final_decoder = native_dec if branch is None else branch['decoder']
                    final_decoded = np.asarray(final_decoder['decoded'], np.uint8).copy()
                    final_syndrome = _syndrome(bound['H'], final_decoded)
                    from receiver import extract_info
                    final_info = np.asarray(extract_info(bound['code'], final_decoded), np.uint8)
                    if final_info.shape != (1024,):
                        raise ValueError('Stage-A final information vector differs')
                    raw_start = time.perf_counter()
                    raw_path = out / 'raw' / f'{stem}_{arm}.npz'
                    raw_payload = dict(observation_id=stem, arm=arm,
                        input_sha256=input_row['observation_sha256'],
                        stream_ids=input_row['stream_ids'],
                        baseline_arrays=arrays, native_events=timing['events'],
                        native_timing={k:v for k,v in timing.items() if k != 'acquisition'},
                        acquisition=_acquisition_record(timing), native_decoder=native_dec,
                        triggered=triggered, baseline_syndrome_weight=syndrome,
                        initial_geometry=timing.get('initial_geometry'),
                        entering_geometry=timing.get('entering_geometry'),
                        geometry_result=None if branch is None else asdict(branch['result']),
                        branch_inputs=None if branch is None else dict(
                            app_input=branch['app_input'], check_prior=branch['check_prior'],
                            ce_mu=branch['ce_mu'], ce_variance=branch['ce_variance']),
                        branch_detector=None if branch is None else branch['detector'],
                        branch_decoder=None if branch is None else branch['decoder'],
                        final_decoded=final_decoded, final_info=final_info)
                    raw_hash = evidence.save_artifact(raw_path, raw_payload, identity)
                    raw_ready = time.perf_counter() - origin
                    decision_path = out / 'decisions' / f'{stem}_{arm}.json'
                    decision_record = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                        input_sha256=input_row['observation_sha256'],
                        triggered=triggered, baseline_syndrome_weight=syndrome,
                        final_syndrome_weight=final_syndrome,
                        final_decoded_sha256=hashlib.sha256(final_decoded.tobytes()).hexdigest(),
                        final_decoded=final_decoded.astype(int).tolist(),
                        final_info=final_info.astype(int).tolist(),
                        checkpoints=row['checkpoints'], raw_path=str(raw_path.relative_to(out)),
                        raw_sha256=raw_hash, source_hashes=registration['source_hashes'])
                    decision_start = time.perf_counter()
                    decision_hash = write_json_exclusive(decision_path, decision_record)
                    complete = time.perf_counter() - origin
                    if arm in old_to_new:
                        old_row = bound['historical'][stem, old_to_new[arm]]
                        old_raw = load_bound(evidence,
                            args.historical_observed / old_row['raw_path'], old_row['raw_sha256'])
                        largest = _compare_saved(old_raw['baseline_arrays'], arrays)
                        if not np.array_equal(old_raw['final_decoded'], final_decoded):
                            raise ValueError(f'Stage-A historical {arm} final bits differ: {stem}')
                        parity = dict(observation_id=stem, arm=arm,
                            max_array_difference=largest, final_bits_equal=True,
                            old_raw_sha256=old_row['raw_sha256'], new_raw_sha256=raw_hash)
                        append_json(out / 'historical_parity.jsonl', parity)
                    row.update(status='ok', triggered=triggered,
                        baseline_syndrome_weight=syndrome,
                        final_syndrome_weight=final_syndrome,
                        final_decoded_sha256=decision_record['final_decoded_sha256'],
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
                        raw_path=str(raw_path.relative_to(out)), raw_sha256=raw_hash,
                        decision_path=str(decision_path.relative_to(out)),
                        decision_sha256=decision_hash, ledger_append_included_in_latency=False)
                    row['rss_peak_kib_before'] = rss_before
                    row['rss_peak_kib_after'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    append_json(ledger, row)
                except BaseException as error:
                    if row['status'] != 'ok':
                        row.update(status='failed', error=repr(error),
                                   traceback=traceback.format_exc(),
                                   charged_seconds=time.perf_counter()-origin)
                        append_json(ledger, row)
                    raise
        if attempts != 4096 + local_calls or local_calls > 1024:
            raise ValueError('Stage-A final call allocation differs')
        files = _all_files(out)
        write_json_exclusive(out / 'observed_seal.json', dict(schema=SCHEMA,
            status='pass', files=files, observations=1024,
            primary_calls=4096, local_calls=local_calls,
            attempts=attempts, registration_sha256=sha256(args.registration),
            population_observed_seal_sha256=sha256(args.population_observed / 'observed_seal.json')))
    except BaseException as error:
        write_json_exclusive(out / 'invalid_partial.json', dict(
            status='invalid_partial', error=repr(error), traceback=traceback.format_exc(),
            attempts=attempts, local_calls=local_calls,
            elapsed_seconds=time.perf_counter()-started))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('registration', 'population-observed', 'historical-observed',
                 'historical-registration', 'historical-frame-outcomes',
                 'source', 'baseline', 'out',
                 'preregistration', 'f1-spec'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--registration-commit', required=True)
    parser.add_argument('--seconds-limit', required=True, type=float)
    run(parser.parse_args())
