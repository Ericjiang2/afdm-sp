"""Observed-only fixed 75 x 3 validation of compact classical geometry scores."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path[:0] = [str(EXPERIMENTS/'tf_geometry_reopen_20260922'),
                str(EXPERIMENTS/'tf_production_gap_audit_20260922')]
import run_reopening as prior_runner  # noqa: E402
from audit_io import attach, load_bound, sha256, verify_sources, write_json  # noqa: E402

ARMS = ('LOCAL20', 'GLOBAL20', 'CSTATE20')
SCHEMA = 'tf-cstate-validation/1'
EVIDENCE_CAP = 2*1024**3


def arm_schedule(selection):
    if (len(selection) != 75 or sum(s['kind'] == 'trigger' for s in selection) != 43
            or sum(s['kind'] == 'control' for s in selection) != 32):
        raise ValueError('prior 43+32 selection differs')
    return [(s, arm) for index, s in enumerate(selection)
            for arm in ARMS[index % 3:] + ARMS[:index % 3]]


def _elapsed(start):
    return time.perf_counter()-start


def _branch(observation, system, code, native, kernel, arrays, arm):
    """One fresh native coded round with exactly accounted exclusive stages."""
    from messages import moments
    from physical import Channel, daft

    stamp = time.perf_counter()
    app = np.clip(arrays['r1_app'], -20, 20)
    check = np.clip(arrays['r1_check'], -20, 20)
    mu, v, _ = moments(app, 1-system.rho)
    initial = [kernel.Path(int(delay), float(nu)) for delay, nu in zip(
        arrays['r1_delays'], arrays['r1_dopplers'])]
    if len(initial) != len(arrays['r1_gains']):
        raise ValueError('native physical slot count differs')
    message_end = time.perf_counter()
    Y = daft(observation['y'], system.c1, system.c2, True)
    transform_end = time.perf_counter()
    strategy = 'compact' if arm == 'CSTATE20' else 'direct'
    max_edits = 0 if arm == 'LOCAL20' else 2
    result = kernel.reopen_geometry(
        Y, observation['pilot']+mu, v, initial,
        c1=system.c1, c2=system.c2, ridge=float(observation['sigma2']),
        max_delay=system.l_max_cap, doppler_min=-3., doppler_max=3.,
        grid_step=.25, max_edits=max_edits, chunk_size=64,
        local_passes=2, local_halfwidth=.75, local_max_evals=16,
        duplicate_tolerance=1e-6, top_k=20, strategy=strategy)
    geometry_end = time.perf_counter()
    if len(result.paths) != len(initial):
        raise ValueError('geometry changed physical slot count')
    stage = result.diagnostics['stage_timing']
    exclusive = stage['exclusive_seconds']
    expected_names = {'geometry_setup', 'structural_field_build',
        'structural_scoring', 'structural_selection_trace',
        'structural_refit_refresh', 'structural_fallback_direct',
        'local_refinement', 'geometry_finalization'}
    if set(exclusive) != expected_names or any(not np.isfinite(x) or x < 0
                                               for x in exclusive.values()):
        raise ValueError('kernel exclusive-stage classification differs')
    if not np.isclose(sum(exclusive.values()), stage['total_seconds'], rtol=0, atol=1e-6):
        raise ValueError('kernel exclusive stages do not sum to geometry total')
    geometry_overhead = geometry_end-transform_end-stage['total_seconds']
    if geometry_overhead < 0:
        raise ValueError('kernel stage total exceeds wrapper geometry wall time')
    validation_end = time.perf_counter()
    channel = Channel(len(observation['y']), system.c1, system.c2,
                      [p.delay for p in result.paths],
                      [p.doppler for p in result.paths], result.gains)
    channel_end = time.perf_counter()
    detector = native.scalar_joint(
        observation['y'], observation['pilot'], channel,
        observation['sigma2'], pd=1-system.rho, prior=check,
        iterations=20, damping=.3, gain_mode='joint')
    tf_end = time.perf_counter()
    decoder = native.decoder_messages(code,
        np.clip(detector['extrinsic'], -20, 20), maxiter=50)
    decision_end = time.perf_counter()
    stages = dict(message_handling=message_end-stamp,
                  y_transform=transform_end-message_end,
                  **exclusive,
                  geometry_wrapper_overhead=geometry_overhead,
                  wrapper_validation=validation_end-geometry_end,
                  channel_construction=channel_end-validation_end,
                  tf= tf_end-channel_end, ldpc=decision_end-tf_end)
    decision = decision_end-stamp
    if not np.isclose(sum(stages.values()), decision, rtol=0, atol=1e-7):
        raise ValueError('decision-ready exclusive stage sum differs')
    return dict(result=result, detector=detector, decoder=decoder,
        app_input=app, check_prior=check, ce_mu=mu, ce_variance=v,
        initial_paths=initial, decision_ready_at=decision_end,
        branch_origin=stamp, exclusive_stages=stages,
        branch_decision_seconds=decision)


def verify_seal(out):
    out = Path(out)
    seal = json.loads((out/'observed_seal.json').read_text())
    actual = {str(path.relative_to(out)):sha256(path) for path in out.rglob('*')
              if path.is_file() and path.name != 'observed_seal.json'}
    if (seal.get('status') != 'pass' or seal.get('schema') != SCHEMA
            or actual != seal.get('files')):
        raise ValueError('validation seal or file hashes differ')
    selection = json.loads((out/'selection.json').read_text())
    if seal.get('selection_sha256') != sha256(out/'selection.json'):
        raise ValueError('validation selection hash differs')
    expected = [(s['observation_id'], arm) for s, arm in arm_schedule(selection)]
    rows = [json.loads(line) for line in (out/'ledger.jsonl').read_text().splitlines()]
    if (len(rows) != 225 or [(r['observation_id'], r['arm']) for r in rows] != expected
            or seal.get('completed_calls') != 225):
        raise ValueError('validation call allocation differs')
    for row in rows:
        if row['status'] != 'ok' or not row['receiver_started'] or len(row['checkpoints']) != 3:
            raise ValueError('validation call is incomplete')
        refs = [(row['raw_path'], row['raw_sha256'])] + [
            (cp['path'], cp['artifact_sha256']) for cp in row['checkpoints']]
        if any(actual.get(path) != digest for path, digest in refs):
            raise ValueError('validation ledger artifact hash differs')
        if [cp['round'] for cp in row['checkpoints']] != [0, 1, 2]:
            raise ValueError('validation checkpoint allocation differs')
        if not np.isclose(row['added_complete_branch_seconds'],
                          row['raw_artifact_ready_seconds']-row['replay_ready_seconds'],
                          rtol=0, atol=1e-7):
            raise ValueError('validation complete branch time differs')
    return seal


def run_campaign(args):
    run, out, prior = args.run.resolve(), args.out.resolve(), args.prior_observed.resolve()
    if out.exists():
        raise FileExistsError('validation output root exists')
    prior_runner.verify_seal(prior)
    previous_manifest = json.loads((prior/'manifest.json').read_text())
    previous_selection = json.loads((prior/'selection.json').read_text())
    original_manifest = json.loads((run/'manifest.json').read_text())
    evidence = attach(args.source, args.baseline)
    verify_sources(original_manifest, args.source, args.baseline, evidence)
    a_receipt = json.loads(args.a_receipt.read_text())
    if (a_receipt.get('status') != 'pass' or
            a_receipt.get('manifest_sha256') != sha256(run/'manifest.json') or
            a_receipt.get('ledger_sha256') != sha256(run/'ledger.jsonl')):
        raise ValueError('original A receipt differs')
    cache = args.baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    if sha256(cache) != a_receipt['ldpc_cache_sha256']:
        raise ValueError('actual code cache differs from A receipt')
    if previous_manifest.get('original_manifest_sha256') != sha256(run/'manifest.json'):
        raise ValueError('previous observed run is not on original data')
    for relative, digest in previous_manifest['code_hashes'].items():
        if sha256(EXPERIMENTS/relative) != digest:
            raise ValueError(f'previous observed source changed: {relative}')
    old_kernel_hash = previous_manifest['code_hashes']['tf_geometry_reopen_20260922/geometry_reopen.py']
    if sha256(EXPERIMENTS/'tf_geometry_reopen_20260922'/'geometry_reopen.py') != old_kernel_hash:
        raise ValueError('registered previous direct geometry source changed')
    stage0 = json.loads(args.qualification.read_text())
    if (stage0.get('status') != 'pass' or stage0.get('receiver_calls') != 0
            or stage0.get('original_manifest_sha256') != sha256(run/'manifest.json')
            or stage0.get('a_receipt_sha256') != sha256(args.a_receipt)
            or stage0.get('prior_observed_seal_sha256') != sha256(prior/'observed_seal.json')
            or stage0.get('prior_selection_sha256') != sha256(prior/'selection.json')
            or stage0.get('prior_kernel_sha256') != old_kernel_hash
            or stage0.get('qualified_entered_states') != 145
            or stage0.get('source_hashes', {}).get('geometry_validation.py') !=
                sha256(HERE/'geometry_validation.py')
            or stage0.get('source_hashes', {}).get('compact_state.py') !=
                sha256(HERE/'compact_state.py')
            or stage0.get('source_hashes', {}).get('qualify_validation.py') !=
                sha256(HERE/'qualify_validation.py')):
        raise ValueError('stage0 full-grid qualification is absent or unbound')
    local_audit = json.loads(args.local_audit.read_text())
    if (local_audit.get('status') != 'pass'
            or local_audit.get('receiver_calls') != 0
            or local_audit.get('global_score_steps_rerun') != 0
            or local_audit.get('checked_frames') != 75
            or local_audit.get('checked_arm_states') != 150
            or local_audit.get('qualification_receipt_sha256') != sha256(args.qualification)
            or local_audit.get('prior_observed_seal_sha256') != sha256(prior/'observed_seal.json')
            or local_audit.get('original_manifest_sha256') != sha256(run/'manifest.json')
            or any(local_audit.get('source_hashes', {}).get(name) != sha256(HERE/name)
                   for name in ('audit_local_trials.py', 'geometry_validation.py',
                                'compact_state.py', 'qualify_validation.py'))
            or local_audit.get('files', {}).get('local_trial_checks.csv') !=
                sha256(args.local_audit.parent/'local_trial_checks.csv')):
        raise ValueError('zero-receiver local-trial audit is absent or unbound')
    import native_twofft as native
    from receiver import context
    import geometry_validation as kernel

    environment = evidence.bind_runtime_environment()
    context_start = time.perf_counter()
    system, _, code, header = context()
    context_seconds = _elapsed(context_start)
    evidence.verify_runtime_binding()
    header_original = json.loads((run/'context_header.json').read_text())
    if header['code_g_sha256'] != header_original['code_g_sha256'] or system.l_max_cap != 102:
        raise ValueError('runtime code or delay domain differs')
    with np.load(cache, allow_pickle=False) as saved:
        H = np.asarray(saved['H'])
    selected = prior_runner.select_observations(run, evidence, H)
    selection = [dict(observation_id=s['observation_id'], kind=s['kind'],
                      final_syndrome_weight=s['final_syndrome_weight'],
                      input_sha256=s['record']['input_sha256'],
                      original_checkpoint_sha256=[cp['artifact_sha256']
                          for cp in s['record']['checkpoints']]) for s in selected]
    if selection != previous_selection:
        raise ValueError('new selection differs from sealed prior 75 IDs')
    common_config = dict(native_rounds=2, native_iterations=20,
        native_ce_mode='soft', native_gain_mode='joint', app_clip=20,
        check_extrinsic_clip=20, next_round_iterations=20,
        next_round_damping=.3, next_round_gain_mode='joint',
        decoder_llr_clip=20, decoder_maxiter=50,
        geometry=dict(max_delay=102, doppler_min=-3., doppler_max=3.,
            grid_step=.25, ridge='observation_sigma2', chunk_size=64,
            local_passes=2, local_halfwidth=.75, local_max_evals=16,
            duplicate_tolerance=1e-6, top_k=20),
        arm_strategy={'LOCAL20':'direct','GLOBAL20':'direct','CSTATE20':'compact'},
        arm_max_edits={'LOCAL20':0,'GLOBAL20':2,'CSTATE20':2})
    source_files = [Path(__file__), Path(kernel.__file__), HERE/'compact_state.py',
                    HERE/'qualify_validation.py', HERE/'audit_local_trials.py',
                    EXPERIMENTS/'tf_geometry_reopen_20260922'/'run_reopening.py',
                    EXPERIMENTS/'tf_production_gap_audit_20260922'/'audit_io.py']
    source_hashes = {str(p.relative_to(EXPERIMENTS)):sha256(p) for p in source_files}
    source_hashes_sha256 = evidence.canonical_hash(source_hashes)
    config_sha256 = evidence.canonical_hash(common_config)
    out.mkdir(parents=True)
    (out/'raw').mkdir()
    (out/'checkpoints').mkdir()
    write_json(out/'selection.json', selection)
    write_json(out/'manifest.json', dict(schema=SCHEMA, arms=list(ARMS),
        original_manifest_sha256=sha256(run/'manifest.json'),
        original_ledger_sha256=sha256(run/'ledger.jsonl'),
        original_context_header_sha256=sha256(run/'context_header.json'),
        previous_observed_seal_sha256=sha256(prior/'observed_seal.json'),
        previous_selection_sha256=sha256(prior/'selection.json'),
        previous_kernel_sha256=old_kernel_hash,
        stage0_receipt_sha256=sha256(args.qualification),
        local_trial_audit_sha256=sha256(args.local_audit),
        a_receipt_sha256=sha256(args.a_receipt), cache_sha256=sha256(cache),
        source_hashes=source_hashes, common_config=common_config,
        source_hashes_sha256=source_hashes_sha256,
        common_config_sha256=config_sha256,
        frozen_source_hashes=original_manifest['source_hashes'],
        frozen_baseline_hashes=original_manifest['baseline_source_hashes'],
        selection_sha256=sha256(out/'selection.json'),
        runtime_environment=environment,
        campaign_setup_seconds=dict(context=context_seconds),
        timing_boundary=dict(wrapper='from per-call origin through raw artifact '
            'readiness and row preparation; final ledger append/fsync is excluded',
            native_checkpoint_serialization='included in native two-round wall time',
            branch_checkpoint_serialization='exclusive checkpoint_write',
            raw_serialization='exclusive raw_serialization_hash; includes payload assembly',
            geometry_nested_step_times='informational; already included in exclusive stages',
            geometry_wrapper_overhead='nonnegative kernel entry/return and scheduling gap',
            wrapper_validation='stage inventory and clock checks before channel construction'),
        expected_calls=225, expected_checkpoints=675, seconds_limit=args.seconds,
        evidence_cap_bytes=EVIDENCE_CAP, argv=sys.argv[:], pid=os.getpid(),
        created_epoch=time.time()))
    ledger = out/'ledger.jsonl'
    ledger.touch(exist_ok=False)
    campaign_start = time.perf_counter()
    attempts = 0
    for selected_item, arm in arm_schedule(selected):
        if attempts >= 225 or _elapsed(campaign_start) >= args.seconds:
            write_json(out/'blocked.json', dict(reason='validation time/call limit reached',
                attempted_calls=attempts, completed_calls=attempts))
            raise TimeoutError('validation allocation/time limit reached')
        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) >= EVIDENCE_CAP:
            write_json(out/'blocked.json', dict(reason='validation 2GiB evidence cap reached',
                attempted_calls=attempts, completed_calls=attempts))
            raise RuntimeError('validation 2GiB evidence cap reached')
        attempts += 1
        stem = selected_item['observation_id']
        record = selected_item['record']
        identity = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                        input_sha256=record['input_sha256'])
        origin = time.perf_counter()
        row = dict(status='inflight', receiver_started=False, call_index=attempts,
                   observation_id=stem, arm=arm, kind=selected_item['kind'],
                   input_sha256=record['input_sha256'], checkpoints=[],
                   source_hashes_sha256=source_hashes_sha256,
                   common_config_sha256=config_sha256,
                   original_checkpoints=[dict(round=cp['round'],
                       ready_seconds=cp['ready'], artifact_sha256=cp['artifact_sha256'],
                       syndrome_weight=cp['syndrome_weight']) for cp in record['checkpoints']])
        checkpoint_write_seconds = 0.

        def sink(event, decoded):
            nonlocal checkpoint_write_seconds
            round_index = int(event['round'])
            ready = _elapsed(origin)
            path = out/'checkpoints'/f'{stem}_{arm}_r{round_index}.npz'
            write_start = time.perf_counter()
            digest = evidence.save_artifact(path,
                dict(event=event, decoded=np.asarray(decoded).copy()),
                dict(identity, round=round_index))
            checkpoint_write_seconds += _elapsed(write_start)
            row['checkpoints'].append(dict(round=round_index,
                decision_ready_seconds=ready,
                artifact_ready_seconds=_elapsed(origin),
                path=str(path.relative_to(out)), artifact_sha256=digest,
                syndrome_weight=prior_runner.syndrome_weight(H, decoded),
                event={key:value for key,value in event.items() if key!='snapshot'}))

        def persist():
            with ledger.open('a') as stream:
                stream.write(json.dumps(row, allow_nan=False)+'\n')
                stream.flush()
                os.fsync(stream.fileno())

        try:
            obs = load_bound(evidence, run/'frames'/f'{stem}_input.npz',
                             record['input_sha256'])
            if set(obs) != {'y','pilot','sigma2'}:
                raise ValueError('non-observed input field')
            setup_end = time.perf_counter()
            row['receiver_started'] = True
            native_start = time.perf_counter()
            baseline_dec, arrays, native_timing = native.receive(
                obs, system, code, rounds=2, iterations=20,
                ce_mode='soft', gain_mode='joint', checkpoint_sink=sink)
            native_end = time.perf_counter()
            if len(row['checkpoints']) != 2:
                raise ValueError('native two-round replay incomplete')
            replay_difference = prior_runner.compare_replay(arrays, record, run, evidence)
            if not np.array_equal(baseline_dec['decoded'], arrays['r1_decoded']):
                raise ValueError('native replay returned wrong final decision')
            parity_end = time.perf_counter()
            native_checkpoint_write = checkpoint_write_seconds
            branch = _branch(obs, system, code, native, kernel, arrays, arm)
            result, detector, decoder = branch['result'], branch['detector'], branch['decoder']
            third_event = dict(round=2, ready=_elapsed(origin),
                ce=result.elapsed_seconds, inference=branch['exclusive_stages']['tf'],
                decoder=branch['exclusive_stages']['ldpc'],
                ce_evaluations=result.evaluations,
                inference_iterations=20, decoder_iterations=int(decoder['iterations']))
            sink(dict(third_event, snapshot=dict(decoded=decoder['decoded'],
                input_llr=decoder['incoming_llr'], app=decoder['raw_app'],
                check=decoder['raw_check_extrinsic'],
                delays=np.asarray([p.delay for p in result.paths]),
                dopplers=np.asarray([p.doppler for p in result.paths]),
                geometry_gains=result.gains,
                inference_gains=detector['gains'])), decoder['decoded'])
            checkpoint_end = time.perf_counter()
            raw_path = out/'raw'/f'{stem}_{arm}.npz'
            payload = dict(observation_id=stem, arm=arm,
                baseline_arrays=arrays, native_timing=native_timing,
                app_input=branch['app_input'], check_prior=branch['check_prior'],
                ce_mu=branch['ce_mu'], ce_variance=branch['ce_variance'],
                native_round2_detector_mu=arrays['r1_mu'],
                native_round2_detector_variance=arrays['r1_variance'],
                initial_paths=[asdict(p) for p in branch['initial_paths']],
                initial_inference_gains=arrays['r1_gains'],
                initial_ce_gains=arrays['r1_ce_gains'],
                geometry_result=asdict(result), detector=detector, decoder=decoder,
                exclusive_stages=branch['exclusive_stages'])
            raw_hash = evidence.save_artifact(raw_path, payload, identity)
            raw_end = time.perf_counter()
            if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) >= EVIDENCE_CAP:
                raise RuntimeError('validation 2GiB evidence cap reached')
            branch_stages = dict(branch['exclusive_stages'],
                checkpoint_write=checkpoint_end-branch['decision_ready_at'],
                raw_serialization_hash=raw_end-checkpoint_end)
            complete = raw_end-branch['branch_origin']
            if not np.isclose(sum(branch_stages.values()), complete, rtol=0, atol=1e-7):
                raise ValueError('complete branch exclusive stage sum differs')
            row.update(status='ok', raw_path=str(raw_path.relative_to(out)),
                raw_sha256=raw_hash, replay_max_difference=replay_difference,
                final_syndrome_weight=row['checkpoints'][-1]['syndrome_weight'],
                setup_seconds=setup_end-origin,
                native_two_rounds_seconds=native_end-native_start,
                baseline_parity_seconds=parity_end-native_end,
                baseline_bookkeeping_seconds=(native_start-setup_end)+
                    (branch['branch_origin']-parity_end),
                replay_ready_seconds=branch['branch_origin']-origin,
                branch_decision_seconds=branch['branch_decision_seconds'],
                branch_exclusive_stages=branch_stages,
                added_complete_branch_seconds=complete,
                raw_artifact_ready_seconds=raw_end-origin,
                native_checkpoint_write_seconds=native_checkpoint_write)
            finished = time.perf_counter()
            row['wrapper_bookkeeping_seconds'] = finished-raw_end
            row['wrapper_seconds'] = finished-origin
            row['ledger_append_included_in_wrapper'] = False
            if not np.isclose(row['wrapper_seconds'],
                row['setup_seconds']+row['baseline_bookkeeping_seconds']+
                row['native_two_rounds_seconds']+row['baseline_parity_seconds']+
                row['added_complete_branch_seconds']+row['wrapper_bookkeeping_seconds'],
                rtol=0, atol=1e-7):
                raise ValueError('full wrapper exclusive stage sum differs')
            persist()
        except BaseException as error:
            row.update(status='failed', exception=repr(error),
                       traceback=traceback.format_exc(), wrapper_seconds=_elapsed(origin))
            persist()
            write_json(out/'blocked.json', dict(reason=repr(error),
                attempted_calls=attempts, completed_calls=attempts-1,
                failed_identity=identity))
            raise
    files = {str(path.relative_to(out)):sha256(path) for path in out.rglob('*')
             if path.is_file() and path.name != 'observed_seal.json'}
    write_json(out/'observed_seal.json', dict(status='pass', schema=SCHEMA,
        completed_calls=225, completed_checkpoints=675,
        selection_sha256=sha256(out/'selection.json'), files=files))
    verify_seal(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('run','source','baseline','a-receipt','prior-observed',
                 'qualification','local-audit','out'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--seconds', type=float, default=3600)
    run_campaign(parser.parse_args())
