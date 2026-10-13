"""Observed-only, fixed-allocation LOCAL20/GLOBAL20 production diagnostic.

The original observation and two saved decisions are inputs. Truth artifacts and
earlier intervention outcomes are deliberately outside this runner's interface.
Every attempt consumes one of the 150 allocated full native receiver calls.
"""
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

AUDIT = Path(__file__).resolve().parents[1] / 'tf_production_gap_audit_20260922'
sys.path.insert(0, str(AUDIT))
from audit_io import attach, load_bound, sha256, unpack, verify_sources, write_json  # noqa: E402

ARMS = ('LOCAL20', 'GLOBAL20')
EXPECTED = {'trigger': 43, 'control': 32}
SCHEMA = 'tf-geometry-reopen/1'


def arm_schedule(selected):
    if len(selected) != 75 or sum(s['kind'] == 'trigger' for s in selected) != 43:
        raise ValueError('fixed 43+32 observation allocation differs')
    return [(item, arm) for index, item in enumerate(selected)
            for arm in (ARMS if index % 2 == 0 else ARMS[::-1])]


def _bits(value, count):
    bits = unpack(value) if isinstance(value, dict) else np.asarray(value)
    if bits.shape != (count,) or not np.isin(bits, [0, 1]).all():
        raise ValueError('invalid saved decoder vector')
    return bits.astype(np.uint8, copy=True)


def syndrome_weight(H, decoded):
    if H.shape != (1026, 2048):
        raise ValueError(f'actual parity-check matrix shape differs: {H.shape}')
    return int(np.count_nonzero((H @ _bits(decoded, H.shape[1])) % 2))


def select_observations(run, evidence, H):
    """Membership uses saved final decoded vectors and the actual code H only."""
    rows = [json.loads(line) for line in (run / 'ledger.jsonl').read_text().splitlines()]
    cell = sorted((r for r in rows if r['snr_centi_db'] == 650 and
                   r['arm'] == 'TF_J20_R2'), key=lambda r: r['frame'])
    if len(cell) != 1024 or [r['frame'] for r in cell] != list(range(1024)):
        raise ValueError('frozen 6.5 dB TF cell incomplete')
    triggered, controls = [], []
    for record in cell:
        if record['status'] != 'ok' or len(record['checkpoints']) != 2:
            raise ValueError('original TF output/checkpoints incomplete')
        cp = record['checkpoints'][-1]
        saved = load_bound(evidence, run / cp['path'], cp['artifact_sha256'])
        weight = syndrome_weight(H, saved['decoded'])
        if weight != cp['syndrome_weight']:
            raise ValueError('original saved syndrome differs from actual H')
        target = triggered if weight else controls
        if weight or len(controls) < EXPECTED['control']:
            target.append(dict(observation_id=f"s650_f{record['frame']:04d}",
                               kind='trigger' if weight else 'control',
                               final_syndrome_weight=weight, record=record))
    if len(triggered) != EXPECTED['trigger'] or len(controls) != EXPECTED['control']:
        raise ValueError(f'observed selection count differs: {len(triggered)}/{len(controls)}')
    return sorted(triggered + controls, key=lambda item: item['record']['frame'])


def compare_replay(arrays, record, run, evidence):
    largest = 0.
    for cp in record['checkpoints']:
        saved = load_bound(evidence, run / cp['path'], cp['artifact_sha256'])
        r = cp['round']
        if not np.array_equal(_bits(arrays[f'r{r}_decoded'], 2048),
                              _bits(saved['decoded'], 2048)):
            raise ValueError(f'baseline replay decoded differs at round {r}')
        for key in ('input_llr', 'app', 'check', 'delays', 'dopplers',
                    'gains', 'mu', 'variance'):
            actual = np.asarray(arrays[f'r{r}_{key}'])
            original = np.asarray(saved['snapshot'][key])
            if actual.shape != original.shape or not np.allclose(
                    actual, original, rtol=1e-12, atol=1e-12):
                raise ValueError(f'baseline replay differs at round {r}/{key}')
            largest = max(largest, float(np.max(np.abs(actual-original))))
    return largest


def _geometry_round(observation, system, code, native, geometry, baseline_arrays,
                    max_delay, arm):
    from physical import Channel, daft
    from messages import moments

    before = time.perf_counter()
    n = len(observation['y'])
    app = np.clip(baseline_arrays['r1_app'], -20, 20)
    prior = np.clip(baseline_arrays['r1_check'], -20, 20)
    mu, v, _ = moments(app, 1-system.rho)
    saved_mu, saved_v = baseline_arrays['r1_mu'], baseline_arrays['r1_variance']
    # Native receive stores detector moments, while this branch needs decoder APP
    # moments. Never substitute detector mu/v or add APP to the detector prior.
    initial = [geometry.Path(int(delay), float(doppler)) for delay, doppler in zip(
        baseline_arrays['r1_delays'], baseline_arrays['r1_dopplers'])]
    if len(initial) != len(baseline_arrays['r1_gains']):
        raise ValueError('round-two physical slot/gain count differs')
    message_at = time.perf_counter()
    Y = daft(observation['y'], system.c1, system.c2, True)
    transformed_at = time.perf_counter()
    result = geometry.reopen_geometry(
        Y, observation['pilot']+mu, v, initial, c1=system.c1,
        c2=system.c2, ridge=float(observation['sigma2']),
        max_delay=max_delay, doppler_min=-3., doppler_max=3.,
        grid_step=.25, max_edits=0 if arm == 'LOCAL20' else 2,
        chunk_size=64, local_passes=2, local_halfwidth=.75,
        local_max_evals=16, duplicate_tolerance=1e-6, top_k=20)
    geometry_at = time.perf_counter()
    if len(result.paths) != len(initial):
        raise ValueError('geometry operation changed physical slot count')
    channel = Channel(n, system.c1, system.c2,
                      [p.delay for p in result.paths],
                      [p.doppler for p in result.paths], result.gains)
    # A fresh native batch resets all internal residual/cavity state. The only
    # continuing coded-round state is the clipped check-extrinsic prior.
    detector = native.scalar_joint(
        observation['y'], observation['pilot'], channel,
        observation['sigma2'], pd=1-system.rho, prior=prior,
        iterations=20, damping=.3, gain_mode='joint')
    detector_at = time.perf_counter()
    decoder = native.decoder_messages(code, np.clip(detector['extrinsic'], -20, 20),
                                      maxiter=50)
    decision_at = time.perf_counter()
    return dict(result=result, detector=detector, decoder=decoder,
                app_input=app, check_prior=prior, mu=mu, v=v,
                native_round2_detector_mu=saved_mu,
                native_round2_detector_variance=saved_v,
                initial_paths=initial,
                initial_inference_gains=np.asarray(baseline_arrays['r1_gains']).copy(),
                initial_ce_gains=np.asarray(baseline_arrays['r1_ce_gains']).copy(),
                geometry_gains=np.asarray(result.gains).copy(),
                timing=dict(message_seconds=message_at-before,
                            transform_seconds=transformed_at-message_at,
                            geometry_seconds=geometry_at-transformed_at,
                            tf_seconds=detector_at-geometry_at,
                            ldpc_seconds=decision_at-detector_at,
                            branch_seconds=decision_at-before))


def verify_seal(out):
    out = Path(out)
    seal = json.loads((out/'observed_seal.json').read_text())
    actual = {str(p.relative_to(out)): sha256(p) for p in out.rglob('*')
              if p.is_file() and p.name != 'observed_seal.json'}
    if seal['status'] != 'pass' or actual != seal['files']:
        raise ValueError('observed evidence seal/hash inventory differs')
    rows = [json.loads(line) for line in (out/'ledger.jsonl').read_text().splitlines()]
    chosen = json.loads((out/'selection.json').read_text())
    expected = [(s['observation_id'], a) for s, a in arm_schedule(chosen)]
    if (len(rows) != 150 or
            [(r['observation_id'], r['arm']) for r in rows] != expected):
        raise ValueError('observed evidence attempt allocation differs')
    if any(r['status'] != 'ok' or len(r['checkpoints']) != 3 for r in rows):
        raise ValueError('observed evidence contains incomplete call/checkpoints')
    if any(not r.get('receiver_started') for r in rows):
        raise ValueError('observed evidence contains a call without native receiver')
    if seal['selection_sha256'] != sha256(out/'selection.json'):
        raise ValueError('observed selection hash differs')
    for row in rows:
        if row['raw_path'] not in actual or actual[row['raw_path']] != row['raw_sha256']:
            raise ValueError('observed raw artifact reference/hash differs')
        for round_index, checkpoint in enumerate(row['checkpoints']):
            if (checkpoint['round'] != round_index or checkpoint['path'] not in actual
                    or actual[checkpoint['path']] != checkpoint['artifact_sha256']):
                raise ValueError('observed checkpoint reference/hash differs')
            if not (0 <= checkpoint['decision_ready_seconds'] <=
                    checkpoint['artifact_ready_seconds'] <= row['wrapper_seconds']):
                raise ValueError('observed checkpoint ready time order differs')
    return seal


def run_campaign(args):
    run, out = args.run.resolve(), args.out.resolve()
    if out.exists():
        raise FileExistsError('output root exists; no implicit retry or overwrite')
    evidence = attach(args.source, args.baseline)
    manifest = json.loads((run/'manifest.json').read_text())
    verify_sources(manifest, args.source, args.baseline, evidence)
    receipt = json.loads(args.a_receipt.read_text())
    if (receipt.get('status') != 'pass' or
            receipt.get('manifest_sha256') != sha256(run/'manifest.json') or
            receipt.get('ledger_sha256') != sha256(run/'ledger.jsonl')):
        raise ValueError('A receipt does not bind original manifest/ledger')
    cache = args.baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    if sha256(cache) != receipt['ldpc_cache_sha256']:
        raise ValueError('frozen code cache differs from A receipt')
    qualification = json.loads(args.qualification.read_text())
    if (qualification.get('status') != 'pass' or
            qualification.get('original_manifest_sha256') != sha256(run/'manifest.json') or
            qualification.get('a_receipt_sha256') != sha256(args.a_receipt) or
            qualification.get('receiver_calls') != 0 or
            qualification.get('source_hashes', {}).get('geometry_reopen.py') !=
            sha256(Path(__file__).parent/'geometry_reopen.py')):
        raise ValueError('production/reference qualification is absent or unbound')
    with np.load(cache, allow_pickle=False) as archive:
        H = np.asarray(archive['H'])
    selected = select_observations(run, evidence, H)
    import native_twofft as native
    from receiver import context
    import geometry_reopen as geometry
    # Only the frozen numerical source list is bound here. Other analysis code
    # may be written in parallel without changing an already launched run.
    source_files = [Path(__file__), Path(geometry.__file__), AUDIT/'audit_io.py']
    code_hashes = {str(p.relative_to(Path(__file__).resolve().parents[1])): sha256(p)
                   for p in source_files}
    environment = evidence.bind_runtime_environment()
    system, _, code, header = context()
    evidence.verify_runtime_binding()
    original_header = json.loads((run/'context_header.json').read_text())
    if header['code_g_sha256'] != original_header['code_g_sha256']:
        raise ValueError('runtime code generator differs from original run')
    if system.l_max_cap != 102:
        raise ValueError(f'declared production delay cap differs: {system.l_max_cap}')
    if len(selected) != 75:
        raise ValueError('observed selection count differs')
    common_config = dict(native_rounds=2, native_iterations=20,
        native_ce_mode='soft', native_gain_mode='joint',
        app_clip=20, check_extrinsic_clip=20,
        next_round_iterations=20, next_round_gain_mode='joint',
        next_round_damping=.3, decoder_llr_clip=20, decoder_maxiter=50,
        geometry=dict(max_delay=system.l_max_cap, doppler_min=-3.,
            doppler_max=3., grid_step=.25, ridge='observation_sigma2',
            chunk_size=64, local_passes=2, local_halfwidth=.75,
            local_max_evals=16, duplicate_tolerance=1e-6, top_k=20),
        arm_max_edits={'LOCAL20':0, 'GLOBAL20':2})
    out.mkdir(parents=True)
    (out/'raw').mkdir()
    (out/'checkpoints').mkdir()
    selection = [dict(observation_id=s['observation_id'], kind=s['kind'],
                      final_syndrome_weight=s['final_syndrome_weight'],
                      input_sha256=s['record']['input_sha256'],
                      original_checkpoint_sha256=[c['artifact_sha256']
                          for c in s['record']['checkpoints']]) for s in selected]
    write_json(out/'selection.json', selection)
    write_json(out/'manifest.json', dict(schema=SCHEMA,
        original_manifest_sha256=sha256(run/'manifest.json'),
        original_ledger_sha256=sha256(run/'ledger.jsonl'),
        original_context_header_sha256=sha256(run/'context_header.json'),
        a_receipt_sha256=sha256(args.a_receipt),
        qualification_sha256=sha256(args.qualification),
        cache_sha256=sha256(cache), code_hashes=code_hashes,
        frozen_source_hashes=manifest['source_hashes'],
        frozen_baseline_hashes=manifest['baseline_source_hashes'],
        runtime_environment=environment, max_delay=system.l_max_cap,
        common_config=common_config,
        common_config_sha256=evidence.canonical_hash(common_config),
        argv=sys.argv[:], evidence_cap_bytes=2*1024**3,
        arms=list(ARMS), expected_calls=150, selection_sha256=sha256(out/'selection.json'),
        seconds_limit=args.seconds, pid=os.getpid(), created_epoch=time.time()))
    source_config_manifest_sha256 = sha256(out/'manifest.json')
    campaign_started = time.perf_counter()
    ledger = out/'ledger.jsonl'
    with ledger.open('x'):
        pass
    attempts = 0
    for item, arm in arm_schedule(selected):
            if attempts >= 150 or time.perf_counter()-campaign_started >= args.seconds:
                raise TimeoutError('fixed campaign call/time allocation exhausted')
            if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) >= 2*1024**3:
                raise RuntimeError('2 GiB observed evidence cap reached')
            attempts += 1  # Charge even an attempted call that later fails.
            stem = item['observation_id']
            record = item['record']
            identity = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                            input_sha256=record['input_sha256'])
            origin = time.perf_counter()
            checkpoints = []
            row = dict(observation_id=stem, arm=arm, kind=item['kind'],
                       status='inflight', call_index=attempts, receiver_started=False,
                       input_sha256=record['input_sha256'],
                       source_config_manifest_sha256=source_config_manifest_sha256,
                       original_checkpoints=[dict(round=cp['round'],
                           artifact_sha256=cp['artifact_sha256'],
                           ready_seconds=cp['ready'],
                           syndrome_weight=cp['syndrome_weight'])
                           for cp in record['checkpoints']], checkpoints=checkpoints)

            def persist_row():
                with ledger.open('a') as stream:
                    stream.write(json.dumps(row, allow_nan=False)+'\n')
                    stream.flush()
                    os.fsync(stream.fileno())

            def save_checkpoint(event, decoded):
                r = int(event['round'])
                decision_ready = time.perf_counter()-origin
                path = out/'checkpoints'/f'{stem}_{arm}_r{r}.npz'
                digest = evidence.save_artifact(path,
                    dict(event=event, decoded=np.asarray(decoded).copy()),
                    dict(identity, round=r))
                artifact_ready = time.perf_counter()-origin
                checkpoints.append(dict(round=r, path=str(path.relative_to(out)),
                    artifact_sha256=digest, decision_ready_seconds=decision_ready,
                    artifact_ready_seconds=artifact_ready,
                    syndrome_weight=syndrome_weight(H, decoded), event={
                        k:v for k,v in event.items() if k!='snapshot'}))

            try:
                obs = load_bound(evidence, run/'frames'/f'{stem}_input.npz',
                                 record['input_sha256'])
                if set(obs) != {'y', 'pilot', 'sigma2'}:
                    raise ValueError('observation contains non-observed fields')
                setup_seconds = time.perf_counter()-origin
                row['receiver_started'] = True
                dec0, arrays, native_timing = native.receive(
                    obs, system, code, rounds=2, iterations=20,
                    ce_mode='soft', gain_mode='joint',
                    checkpoint_sink=save_checkpoint)
                if len(checkpoints) != 2:
                    raise ValueError('native replay did not produce two checkpoints')
                replay_difference = compare_replay(arrays, record, run, evidence)
                if not np.array_equal(dec0['decoded'], arrays['r1_decoded']):
                    raise ValueError('native returned decision differs from round two')
                replay_ready = time.perf_counter()-origin
                branch = _geometry_round(obs, system, code, native, geometry,
                                         arrays, system.l_max_cap, arm)
                detector, decoder = branch['detector'], branch['decoder']
                third_event = dict(round=2, ce=branch['timing']['geometry_seconds'],
                    inference=branch['timing']['tf_seconds'],
                    decoder=branch['timing']['ldpc_seconds'],
                    decoder_iterations=int(decoder['iterations']),
                    inference_iterations=20, ce_evaluations=branch['result'].evaluations,
                    ready=time.perf_counter()-origin)
                save_checkpoint(dict(third_event, snapshot=dict(
                    decoded=decoder['decoded'], input_llr=decoder['incoming_llr'],
                    app=decoder['raw_app'], check=decoder['raw_check_extrinsic'],
                    delays=np.asarray([p.delay for p in branch['result'].paths]),
                    dopplers=np.asarray([p.doppler for p in branch['result'].paths]),
                    geometry_gains=branch['geometry_gains'],
                    inference_gains=detector['gains'])), decoder['decoded'])
                raw_path = out/'raw'/f'{stem}_{arm}.npz'
                payload = dict(observation_id=stem, arm=arm,
                    baseline_arrays={k:v for k,v in arrays.items() if k.startswith(('r0_', 'r1_'))},
                    native_timing=native_timing,
                    app_input=branch['app_input'], check_prior=branch['check_prior'],
                    ce_mu=branch['mu'], ce_variance=branch['v'],
                    native_round2_detector_mu=branch['native_round2_detector_mu'],
                    native_round2_detector_variance=branch['native_round2_detector_variance'],
                    initial_paths=[asdict(p) for p in branch['initial_paths']],
                    initial_inference_gains=branch['initial_inference_gains'],
                    initial_ce_gains=branch['initial_ce_gains'],
                    geometry_result=asdict(branch['result']), detector=detector,
                    decoder=decoder, branch_timing=branch['timing'])
                raw_hash = evidence.save_artifact(raw_path, payload, identity)
                raw_ready = time.perf_counter()
                if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) >= 2*1024**3:
                    raise RuntimeError('2 GiB observed evidence cap reached')
                row.update(status='ok', replay_max_difference=replay_difference,
                    replay_ready_seconds=replay_ready,
                    final_syndrome_weight=checkpoints[-1]['syndrome_weight'],
                    branch_seconds=branch['timing']['branch_seconds'],
                    added_complete_branch_seconds=raw_ready-origin-replay_ready,
                    setup_seconds=setup_seconds,
                    raw_artifact_ready_seconds=raw_ready-origin,
                    wrapper_seconds=time.perf_counter()-origin,
                    raw_path=str(raw_path.relative_to(out)), raw_sha256=raw_hash)
                persist_row()
            except BaseException as error:
                row.update(status='failed', exception=repr(error),
                           traceback=traceback.format_exc(),
                           wrapper_seconds=time.perf_counter()-origin)
                persist_row()
                write_json(out/'blocked.json', dict(reason=repr(error),
                    attempted_calls=attempts, completed_calls=attempts-1,
                    failed_identity=identity))
                raise
    if attempts != 150:
        raise AssertionError('fixed call allocation incomplete')
    files = {str(p.relative_to(out)): sha256(p) for p in out.rglob('*')
             if p.is_file() and p.name != 'observed_seal.json'}
    write_json(out/'observed_seal.json', dict(status='pass', schema=SCHEMA,
        expected_calls=150, completed_calls=attempts,
        selection_sha256=sha256(out/'selection.json'), files=files))
    verify_seal(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('run', 'source', 'baseline', 'out', 'a-receipt', 'qualification'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--seconds', type=float, default=3600)
    run_campaign(parser.parse_args())
