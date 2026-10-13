"""Run one registered fresh paired TF versus TF+CSTATE population campaign.

Only the observed population root is an input.  Truth paths are not accepted by
this process.  Pair audits are outside both receivers' latency clocks.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path[:0] = [str(EXPERIMENTS/'tf_cstate_validation_20260922'),
                str(EXPERIMENTS/'tf_production_gap_audit_20260922')]
from generate_population import (SCHEMA, CELLS, FRAMES, DISK_CAP,  # noqa: E402
    validate_registration, verify_population_seal)
from run_validation import _branch  # noqa: E402
from audit_io import attach, load_bound, sha256, write_json  # noqa: E402

ARMS = ('TF','TF_CSTATE')
STAGES = ('message_handling','y_transform','geometry_setup',
    'structural_field_build','structural_scoring','structural_selection_trace',
    'structural_refit_refresh','structural_fallback_direct','local_refinement',
    'geometry_finalization','geometry_wrapper_overhead','wrapper_validation',
    'channel_construction','tf','ldpc','checkpoint_write','raw_serialization_hash')
FROZEN_CONFIG = dict(native_rounds=2,native_iterations=20,native_ce_mode='soft',
    native_gain_mode='joint',trigger='final native syndrome!=0',
    continuation='CSTATE20 compact only on trigger',
    app_clip=20,check_extrinsic_clip=20,next_round_iterations=20,
    next_round_damping=.3,next_round_gain_mode='joint',
    decoder_llr_clip=20,decoder_maxiter=50,
    geometry=dict(max_delay=102,doppler_min=-3.,doppler_max=3.,
        grid_step=.25,ridge='observation_sigma2',chunk_size=64,
        local_passes=2,local_halfwidth=.75,local_max_evals=16,
        duplicate_tolerance=1e-6,top_k=20,max_edits=2,strategy='compact'))


def _size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def _save_json_fsync(path, value):
    path = Path(path)
    with path.open('x') as stream:
        stream.write(json.dumps(value,sort_keys=True,allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return sha256(path)


def arm_schedule(population_rows):
    expected=[(snr,frame) for snr in CELLS for frame in range(FRAMES)]
    if (len(population_rows)!=3072 or
            [(r['snr_centi_db'],r['frame']) for r in population_rows]!=expected):
        raise ValueError('prospective population order/allocation differs')
    return [(row,arm) for index,row in enumerate(population_rows)
            for arm in (ARMS if index%2==0 else ARMS[::-1])]


def _native_identity(first, second):
    """Audit after both complete calls, outside the declared latency clocks."""
    a,b=first['baseline_arrays'],second['baseline_arrays']
    if set(a)!=set(b):
        raise ValueError('paired native array inventory differs')
    largest=0.
    def compare(left,right,key):
        nonlocal largest
        if isinstance(left,dict):
            if not isinstance(right,dict) or set(left)!=set(right):
                raise ValueError(f'paired native value inventory differs: {key}')
            for name in left:
                compare(left[name],right[name],f'{key}/{name}')
            return
        if isinstance(left,(list,tuple)):
            if not isinstance(right,type(left)) or len(left)!=len(right):
                raise ValueError(f'paired native value sequence differs: {key}')
            for index,(x,y) in enumerate(zip(left,right)):
                compare(x,y,f'{key}/{index}')
            return
        if isinstance(left,np.ndarray):
            x,y=np.asarray(left),np.asarray(right)
            if x.shape!=y.shape or x.dtype!=y.dtype:
                raise ValueError(f'paired native shape/dtype differs: {key}')
            if key.endswith('decoded'):
                if not np.array_equal(x,y):
                    raise ValueError(f'paired native decoded bits differ: {key}')
            elif np.issubdtype(x.dtype,np.number):
                if not np.allclose(x,y,rtol=1e-12,atol=1e-12):
                    raise ValueError(f'paired native continuous state differs: {key}')
                if x.size:
                    largest=max(largest,float(np.max(np.abs(x-y))))
            elif not np.array_equal(x,y):
                raise ValueError(f'paired native value differs: {key}')
            return
        if isinstance(left,(int,float,complex,np.number)) and not isinstance(left,bool):
            if not np.isclose(left,right,rtol=1e-12,atol=1e-12):
                raise ValueError(f'paired native continuous state differs: {key}')
            largest=max(largest,float(abs(left-right)))
        elif left!=right:
            raise ValueError(f'paired native value differs: {key}')
    for key in a:
        compare(a[key],b[key],key)
    return largest


def verify_observed_seal(root):
    root=Path(root)
    seal=json.loads((root/'observed_seal.json').read_text())
    actual={str(p.relative_to(root)):sha256(p) for p in root.rglob('*')
            if p.is_file() and p.name!='observed_seal.json'}
    if seal.get('status')!='pass' or seal.get('schema')!=SCHEMA or seal.get('files')!=actual:
        raise ValueError('prospective receiver observed seal differs')
    rows=[json.loads(line) for line in (root/'ledger.jsonl').read_text().splitlines()]
    expected=[]
    for index in range(len(CELLS)*FRAMES):
        stem=f's{CELLS[index//FRAMES]}_f{index%FRAMES:04d}'
        expected.extend((stem,arm) for arm in
                        (ARMS if index%2==0 else ARMS[::-1]))
    if (len(rows)!=6144 or
            [(r['observation_id'],r['arm']) for r in rows]!=expected or
            any(r['status']!='ok' for r in rows)):
        raise ValueError('prospective paired receiver allocation differs')
    for row in rows:
        refs=[(row['raw_path'],row['raw_sha256']),
              (row['decision_record_path'],row['decision_record_sha256'])]
        refs += [(cp['path'],cp['artifact_sha256']) for cp in row['checkpoints']]
        if any(actual.get(path)!=digest for path,digest in refs):
            raise ValueError('prospective receiver artifact hash differs')
        if len(row['checkpoints']) != (3 if row['arm']=='TF_CSTATE' and row['triggered'] else 2):
            raise ValueError('prospective receiver checkpoint count differs')
    return seal


def run(args):
    population,out=args.population_observed.resolve(),args.out.resolve()
    if out.exists():
        raise FileExistsError('prospective receiver output root already exists')
    if re.fullmatch(r'[0-9a-f]{40}',args.registration_commit) is None:
        raise ValueError('registration commit must be full Git SHA')
    evidence=attach(args.source,args.baseline)
    registration=validate_registration(args.registration,args.source,args.baseline,evidence)
    if registration.get('receiver_config')!=FROZEN_CONFIG:
        raise ValueError('registered prospective receiver configuration differs')
    verify_population_seal(population)
    population_manifest=json.loads((population/'manifest.json').read_text())
    if (population_manifest.get('registration_sha256')!=sha256(args.registration)
            or population_manifest.get('registration_commit')!=args.registration_commit):
        raise ValueError('prospective population registration differs')
    rows=[json.loads(line) for line in (population/'ledger.jsonl').read_text().splitlines()]
    schedule=arm_schedule(rows)
    import native_twofft as native
    from receiver import context
    import geometry_validation as kernel

    environment=evidence.bind_runtime_environment()
    setup_start=time.perf_counter()
    system,_,code,header=context()
    context_seconds=time.perf_counter()-setup_start
    evidence.verify_runtime_binding()
    if (system.N_total!=1024 or system.l_max_cap!=102 or system.rho!=.5
            or header['code_g_sha256']!=registration['code_g_sha256']):
        raise ValueError('prospective receiver context differs')
    cache=args.baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    with np.load(cache,allow_pickle=False) as saved:
        H=np.asarray(saved['H'])
    if H.shape!=(1026,2048):
        raise ValueError('frozen actual parity-check matrix differs')
    source_hashes=registration['registration_source_hashes']
    source_hashes_sha=evidence.canonical_hash(source_hashes)
    config_sha=evidence.canonical_hash(FROZEN_CONFIG)
    out.mkdir(parents=True)
    for folder in ('checkpoints','raw','decisions'):
        (out/folder).mkdir()
    write_json(out/'manifest.json',dict(schema=SCHEMA,kind='receiver_observed',
        arms=list(ARMS),expected_calls=6144,expected_observations=3072,
        registration_sha256=sha256(args.registration),
        registration_commit=args.registration_commit,
        protocol_sha256=registration['protocol_sha256'],
        population_observed_seal_sha256=sha256(population/'observed_seal.json'),
        population_manifest_sha256=sha256(population/'manifest.json'),
        population_ledger_sha256=sha256(population/'ledger.jsonl'),
        source_hashes=source_hashes,source_hashes_sha256=source_hashes_sha,
        receiver_config=FROZEN_CONFIG,receiver_config_sha256=config_sha,
        runtime_environment=environment,
        campaign_setup_seconds=dict(context=context_seconds),
        timing_boundary=dict(entry='before observed artifact load; same for both arms',
            complete='immediately after decision record write and fsync',
            final_timing_ledger='append/fsync after complete clock; excluded and measured as campaign control plane',
            paired_native_audit='after both receiver calls; outside both latency clocks',
            nested_checkpoint_writes='included within native or branch wall time',
            cstate_branch_stages='17 exclusive registered stages; full grid/top20/local logging included'),
        seconds_limit=args.seconds,disk_cap_bytes=DISK_CAP,
        created_epoch=time.time(),argv=sys.argv[:],pid=os.getpid()))
    ledger=out/'ledger.jsonl'
    paired_ledger=out/'paired_audit.jsonl'
    ledger.touch(exist_ok=False)
    paired_ledger.touch(exist_ok=False)
    started=time.perf_counter()
    attempts=0
    ledger_seconds=0.
    paired_audit_seconds=0.
    pending_pair={}
    try:
        for input_row,arm in schedule:
            if time.perf_counter()-started>=args.seconds:
                raise TimeoutError('prospective receiver 10800s runtime cap reached')
            if _size(out)>=DISK_CAP:
                raise RuntimeError('prospective receiver 32GiB evidence cap reached')
            attempts+=1
            stem=input_row['observation_id']
            origin=time.perf_counter()
            identity=dict(schema=SCHEMA,observation_id=stem,arm=arm,
                          input_sha256=input_row['observation_sha256'])
            record=dict(status='inflight',call_index=attempts,
                observation_id=stem,snr_centi_db=input_row['snr_centi_db'],
                frame=input_row['frame'],arm=arm,
                input_sha256=input_row['observation_sha256'],
                observation_hash=input_row['observation_hash'],
                stream_ids=input_row['stream_ids'],
                source_hashes_sha256=source_hashes_sha,
                receiver_config_sha256=config_sha,
                receiver_started=False,checkpoints=[])
            native_checkpoint_write=0.
            def sink(event,decoded):
                nonlocal native_checkpoint_write
                round_index=int(event['round'])
                ready=time.perf_counter()-origin
                cp_path=out/'checkpoints'/f'{stem}_{arm}_r{round_index}.npz'
                write_start=time.perf_counter()
                digest=evidence.save_artifact(cp_path,
                    dict(event=event,decoded=np.asarray(decoded).copy()),
                    dict(identity,round=round_index))
                if round_index<2:
                    native_checkpoint_write+=time.perf_counter()-write_start
                syndrome=int(np.count_nonzero((H @ np.asarray(decoded,dtype=np.uint8))%2))
                record['checkpoints'].append(dict(round=round_index,
                    path=str(cp_path.relative_to(out)),artifact_sha256=digest,
                    decision_ready_seconds=ready,
                    artifact_ready_seconds=time.perf_counter()-origin,
                    syndrome_weight=syndrome,
                    event={key:value for key,value in event.items() if key!='snapshot'}))
            try:
                input_payload=load_bound(evidence,population/input_row['observation_path'],
                                         input_row['observation_sha256'])
                obs=input_payload['observation']
                if (set(obs)!={'y','pilot','sigma2'} or
                        input_payload['observation_id']!=stem or
                        input_payload['observation_hash']!=input_row['observation_hash'] or
                        input_payload['stream_ids']!=input_row['stream_ids']):
                    raise ValueError('fresh observed input/stream identity differs')
                input_loaded=time.perf_counter()
                record['receiver_started']=True
                native_start=time.perf_counter()
                baseline_dec,arrays,native_timing=native.receive(obs,system,code,
                    rounds=2,iterations=20,ce_mode='soft',gain_mode='joint',
                    checkpoint_sink=sink)
                native_end=time.perf_counter()
                if len(record['checkpoints'])!=2 or not np.array_equal(
                        baseline_dec['decoded'],arrays['r1_decoded']):
                    raise ValueError('fresh native two-round output incomplete')
                trigger_start=time.perf_counter()
                syndrome=record['checkpoints'][-1]['syndrome_weight']
                if syndrome!=int(np.count_nonzero((H @ np.asarray(
                        baseline_dec['decoded'],dtype=np.uint8))%2)):
                    raise ValueError('fresh native trigger recount differs')
                triggered=bool(arm=='TF_CSTATE' and syndrome!=0)
                trigger_end=time.perf_counter()
                branch=None
                branch_start=time.perf_counter()
                if triggered:
                    branch=_branch(obs,system,code,native,kernel,arrays,'CSTATE20')
                    result=branch['result']
                    decoder=branch['decoder']
                    event=dict(round=2,ready=time.perf_counter()-origin,
                        ce=result.elapsed_seconds,
                        inference=branch['exclusive_stages']['tf'],
                        decoder=branch['exclusive_stages']['ldpc'],
                        ce_evaluations=result.evaluations,
                        inference_iterations=20,
                        decoder_iterations=int(decoder['iterations']))
                    sink(dict(event,snapshot=dict(decoded=decoder['decoded'],
                        input_llr=decoder['incoming_llr'],app=decoder['raw_app'],
                        check=decoder['raw_check_extrinsic'],
                        delays=np.asarray([p.delay for p in result.paths]),
                        dopplers=np.asarray([p.doppler for p in result.paths]),
                        geometry_gains=result.gains,
                        inference_gains=branch['detector']['gains'])),decoder['decoded'])
                final_decoder=baseline_dec if branch is None else branch['decoder']
                final_decoded=np.asarray(final_decoder['decoded']).copy()
                if final_decoded.shape!=(2048,) or not np.isin(final_decoded,[0,1]).all():
                    raise ValueError('invalid final decoded vector')
                final_syndrome=int(np.count_nonzero((H @ final_decoded)%2))
                checkpoint_end=time.perf_counter()
                raw_path=out/'raw'/f'{stem}_{arm}.npz'
                raw_payload=dict(observation_id=stem,arm=arm,
                    input_sha256=input_row['observation_sha256'],
                    stream_ids=input_row['stream_ids'],
                    baseline_arrays=arrays,native_timing=native_timing,
                    native_decoder=baseline_dec,triggered=triggered,
                    baseline_syndrome_weight=syndrome,
                    geometry_result=None if branch is None else asdict(branch['result']),
                    branch_inputs=None if branch is None else dict(
                        app_input=branch['app_input'],check_prior=branch['check_prior'],
                        ce_mu=branch['ce_mu'],ce_variance=branch['ce_variance']),
                    branch_detector=None if branch is None else branch['detector'],
                    branch_decoder=None if branch is None else branch['decoder'],
                    final_decoded=final_decoded)
                raw_hash=evidence.save_artifact(raw_path,raw_payload,identity)
                raw_ready=time.perf_counter()
                stages={name:0. for name in STAGES}
                if branch is not None:
                    stages.update(branch['exclusive_stages'])
                    stages['checkpoint_write']=checkpoint_end-branch['decision_ready_at']
                    stages['raw_serialization_hash']=raw_ready-checkpoint_end
                    if not np.isclose(sum(stages.values()),
                            raw_ready-branch['branch_origin'],rtol=0,atol=1e-7):
                        raise ValueError('prospective 17-stage branch clock differs')
                decision_path=out/'decisions'/f'{stem}_{arm}.json'
                decision_record=dict(schema=SCHEMA,observation_id=stem,arm=arm,
                    input_sha256=input_row['observation_sha256'],
                    stream_ids=input_row['stream_ids'],triggered=triggered,
                    baseline_syndrome_weight=syndrome,
                    final_syndrome_weight=final_syndrome,
                    final_decoded_sha256=hashlib.sha256(final_decoded.tobytes()).hexdigest(),
                    final_decision_ready_seconds=record['checkpoints'][-1]['decision_ready_seconds'],
                    checkpoints=record['checkpoints'],raw_path=str(raw_path.relative_to(out)),
                    raw_sha256=raw_hash,branch_exclusive_stages=stages,
                    source_hashes_sha256=source_hashes_sha,
                    receiver_config_sha256=config_sha)
                decision_write_start=time.perf_counter()
                decision_hash=_save_json_fsync(decision_path,decision_record)
                complete_end=time.perf_counter()
                # The self-referential timing ledger is the only post-clock write.
                record.update(status='ok',triggered=triggered,
                    baseline_syndrome_weight=syndrome,
                    final_syndrome_weight=final_syndrome,
                    final_decoded_sha256=decision_record['final_decoded_sha256'],
                    final_decision_ready_seconds=decision_record['final_decision_ready_seconds'],
                    input_load_seconds=input_loaded-origin,
                    before_native_bookkeeping_seconds=native_start-input_loaded,
                    native_two_rounds_seconds=native_end-native_start,
                    native_checkpoint_write_seconds=native_checkpoint_write,
                    trigger_seconds=trigger_end-trigger_start,
                    before_trigger_bookkeeping_seconds=trigger_start-native_end,
                    before_branch_bookkeeping_seconds=branch_start-trigger_end,
                    post_trigger_output_seconds=raw_ready-branch_start,
                    branch_decision_seconds=0. if branch is None else
                        branch['branch_decision_seconds'],
                    branch_exclusive_stages=stages,
                    branch_complete_seconds=0. if branch is None else
                        raw_ready-branch['branch_origin'],
                    raw_serialization_hash_seconds=raw_ready-checkpoint_end,
                    decision_record_write_seconds=complete_end-decision_write_start,
                    before_decision_record_bookkeeping_seconds=decision_write_start-raw_ready,
                    complete_latency_seconds=complete_end-origin,
                    raw_path=str(raw_path.relative_to(out)),raw_sha256=raw_hash,
                    raw_artifact_ready_seconds=raw_ready-origin,
                    decision_record_path=str(decision_path.relative_to(out)),
                    decision_record_sha256=decision_hash,
                    ledger_append_included_in_latency=False)
                total=(record['input_load_seconds']+
                    record['before_native_bookkeeping_seconds']+
                    record['native_two_rounds_seconds']+
                    record['before_trigger_bookkeeping_seconds']+
                    record['trigger_seconds']+
                    record['before_branch_bookkeeping_seconds']+
                    record['post_trigger_output_seconds']+
                    record['before_decision_record_bookkeeping_seconds']+
                    record['decision_record_write_seconds'])
                if not np.isclose(total,record['complete_latency_seconds'],rtol=0,atol=1e-7):
                    raise ValueError('prospective complete receiver timing identity differs')
                ledger_start=time.perf_counter()
                with ledger.open('a') as stream:
                    stream.write(json.dumps(record,allow_nan=False)+'\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                ledger_seconds+=time.perf_counter()-ledger_start
                if stem in pending_pair:
                    audit_start=time.perf_counter()
                    previous=pending_pair.pop(stem)
                    previous_raw=load_bound(evidence,out/previous['raw_path'],
                                            previous['raw_sha256'])
                    current_raw=load_bound(evidence,raw_path,raw_hash)
                    difference=_native_identity(previous_raw,current_raw)
                    pair=dict(observation_id=stem,
                        first_arm=previous['arm'],second_arm=arm,
                        first_input_sha256=previous['input_sha256'],
                        second_input_sha256=record['input_sha256'],
                        max_native_continuous_difference=difference,
                        native_decoded_identical=True)
                    with paired_ledger.open('a') as stream:
                        stream.write(json.dumps(pair,allow_nan=False)+'\n')
                        stream.flush()
                        os.fsync(stream.fileno())
                    paired_audit_seconds+=time.perf_counter()-audit_start
                else:
                    pending_pair[stem]=record
            except BaseException as error:
                record.update(status='failed',exception=repr(error),
                    traceback=traceback.format_exc(),elapsed_seconds=time.perf_counter()-origin)
                with ledger.open('a') as stream:
                    stream.write(json.dumps(record,allow_nan=False)+'\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                raise
        if pending_pair:
            raise ValueError('prospective paired receiver allocation incomplete')
        write_json(out/'campaign_timing.json',dict(
            context_seconds=context_seconds,
            ledger_append_seconds_total=ledger_seconds,
            paired_audit_seconds_total=paired_audit_seconds,
            completed_receiver_calls=attempts,
            receiver_clock_excludes='final timing-ledger append/fsync and paired audit'))
        files={str(p.relative_to(out)):sha256(p) for p in out.rglob('*')
               if p.is_file() and p.name!='observed_seal.json'}
        write_json(out/'observed_seal.json',dict(status='pass',schema=SCHEMA,
            receiver_calls=6144,observations=3072,
            population_observed_seal_sha256=sha256(population/'observed_seal.json'),
            registration_sha256=sha256(args.registration),files=files))
        verify_observed_seal(out)
    except BaseException as error:
        write_json(out/'invalid_partial.json',dict(status='invalid_partial',
            reason=repr(error),traceback=traceback.format_exc(),
            attempted_calls=attempts,pid=os.getpid(),
            elapsed_seconds=time.perf_counter()-started))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('registration','population-observed','source','baseline','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--registration-commit',required=True)
    parser.add_argument('--seconds',type=float,default=10800)
    run(parser.parse_args())
