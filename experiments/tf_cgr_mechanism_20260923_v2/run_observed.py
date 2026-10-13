"""Exactly 25 observed witnesses times four frozen final-batch mechanisms.

Truth payloads are not accepted by this process. A numerical final-branch failure
returns the already ready native decision and retains the failed branch cost.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path[:0] = [str(HERE),str(EXP/'tf_cstate_validation_20260922'),
                str(EXP/'tf_production_gap_audit_20260922')]
from audit_io import attach, load_bound, sha256, write_json  # noqa: E402
import generate_variants  # noqa: E402

SCHEMA = 'tf-cgr-observed/1'
WITNESS_MANIFEST_SHA256 = 'e71475bed16578db1e3811efe56e32fb3ef27d1961e5cb691fd126936af30cf2'
PROTOCOL_SHA256 = '4097203fd4691985878e87939ff1e6a82ff40e77a6973b4687f35455645a4968'
ARMS = ('BASE','CGR','SHAM','BLOCK')
SECONDS_CAP = 1800
BYTES_CAP = 2*1024**3
TARGET_IDS = frozenset(('s650_f0390','s650_f0415','s650_f0718','s650_f0720',
    's650_f0770','s650_f0996','s600_f0600','s700_f0732'))
STAGES = ('message_handling','y_transform','geometry_setup','structural_field_build',
    'structural_scoring','structural_selection_trace','structural_refit_refresh',
    'structural_fallback_direct','local_refinement','geometry_finalization',
    'geometry_wrapper_overhead','wrapper_validation','channel_construction',
    'tf','ldpc')


def schedule(entries):
    if (len(entries)!=25 or len({e['observation_id'] for e in entries})!=25 or
            sum(e['role']=='target_remaining_failure' for e in entries)!=8 or
            sum(e['role']=='matched_rescued_control' for e in entries)!=7 or
            sum(e['role']=='matched_easy_control' for e in entries)!=7 or
            sum(e['role']=='distinct_delay_failure_specificity' for e in entries)!=3):
        raise ValueError('witness allocation differs from fixed 8+7+7+3')
    if {e['observation_id'] for e in entries if e['role']=='target_remaining_failure'} != TARGET_IDS:
        raise ValueError('target identities differ')
    return [(entry,arm) for index,entry in enumerate(entries)
            for arm in ARMS[index%4:]+ARMS[:index%4]]


def _safe_file(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('unsafe witness artifact path')
    resolved = (root/path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError('witness artifact escapes root')
    return resolved


def _observed_file(entry, root):
    matches = [f for f in entry['files'] if f['kind']=='observation']
    if len(matches)!=1:
        raise ValueError('one bound observation required')
    file = _safe_file(root,matches[0]['relative_path'])
    if sha256(file)!=matches[0]['sha256']:
        raise ValueError('cold observation SHA differs')
    return file,matches[0]['sha256']


def _hash_value(value):
    digest=hashlib.sha256()
    def visit(v):
        if isinstance(v,dict):
            for key in sorted(v):
                digest.update(key.encode());visit(v[key])
        elif isinstance(v,(list,tuple)):
            digest.update(str(len(v)).encode())
            for item in v:visit(item)
        elif isinstance(v,np.ndarray):
            a=np.ascontiguousarray(v)
            digest.update(str(a.dtype).encode())
            digest.update(json.dumps(a.shape).encode())
            digest.update(a.tobytes())
        else:
            digest.update(json.dumps(v,sort_keys=True,allow_nan=False).encode())
    visit(value)
    return digest.hexdigest()


def _input_observation(payload, observation_id):
    """Strict producer schema and original per-array dtype/shape/byte identity."""
    if set(payload)!= {'observation_id','observation','observation_hash','stream_ids'}:
        raise ValueError(f'cold observation payload keys differ: {sorted(payload)}')
    if payload['observation_id']!=observation_id:
        raise ValueError('cold observation ID differs')
    obs=payload['observation']
    if set(obs)!={'y','pilot','sigma2'}:
        raise ValueError(f'cold observed fields differ: {sorted(obs)}')
    if np.asarray(obs['y']).shape!=(1024,) or np.asarray(obs['pilot']).shape!=(1024,):
        raise ValueError('cold N differs')
    parts=[]
    for name in ('y','pilot','sigma2'):
        a=np.asarray(obs[name])
        digest=hashlib.sha256()
        digest.update(str(a.dtype).encode())
        digest.update(json.dumps(a.shape).encode())
        digest.update(np.ascontiguousarray(a).tobytes())
        parts.append(digest.hexdigest())
    reconstructed=hashlib.sha256('|'.join(parts).encode()).hexdigest()
    if reconstructed!=payload['observation_hash']:
        raise ValueError('cold producer observation hash differs')
    if set(payload['stream_ids'])!={'channel','message','noise'}:
        raise ValueError('cold stream IDs differ')
    return obs


def _source_files(args):
    files=dict(geometry_validation=args.geometry/'geometry_validation.py',
        compact_state=args.geometry/'compact_state.py',
        geometry_reopen=EXP/'tf_geometry_reopen_20260922/geometry_reopen.py',
        audit_io=EXP/'tf_production_gap_audit_20260922/audit_io.py',
        code_cache=args.baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz')
    for label,root in (('native',args.source),('baseline',args.baseline)):
        for folder in ('src','upstream'):
            for path in (root/folder).rglob('*.py'):
                if '__pycache__' not in path.parts:
                    files[f'{label}/{path.relative_to(root)}']=path
    for name in ('run_observed.py','generate_variants.py','tf_base.py',
                 'tf_cgr.py','tf_sham.py','tf_block.py'):
        files[f'cgr/{name}']=HERE/name
    return files


def preflight(args):
    if args.seconds>SECONDS_CAP or args.bytes_cap>BYTES_CAP or args.seconds<=0 or args.bytes_cap<=0:
        raise ValueError('CGR bounds exceed frozen 30min/2GiB contract')
    if args.out.exists():
        raise FileExistsError(args.out)
    manifest=json.loads(args.witness_manifest.read_text())
    if (sha256(args.witness_manifest)!=WITNESS_MANIFEST_SHA256 or
            manifest.get('schema')!='coherent-gain-witness-request/1' or
            manifest.get('n_frames')!=25):
        raise ValueError('witness manifest schema/count differs')
    receipt=json.loads(args.witness_receipt.read_text())
    if (receipt.get('schema')!='tf-cgr-witness-retrieval/1' or
            receipt.get('status')!='pass' or
            receipt.get('integrity',{}).get('npz_declared_sha256_verified')!=93):
        raise ValueError('witness retrieval receipt differs')
    registration=json.loads(args.registration.read_text())
    qualification=json.loads(args.qualification.read_text())
    if (registration.get('schema')!='tf-cgr-registration/1' or
            registration.get('status')!='locked' or
            registration.get('protocol_sha256')!=PROTOCOL_SHA256 or
            registration.get('witness_manifest_sha256')!=WITNESS_MANIFEST_SHA256 or
            registration.get('witness_receipt_sha256')!=sha256(args.witness_receipt) or
            registration.get('source_bindings_sha256')!=sha256(args.source_bindings) or
            registration.get('qualification_sha256')!=sha256(args.qualification) or
            qualification.get('status')!='synthetic_pass' or
            qualification.get('source_sha256')!=generate_variants.EXPECTED or
            qualification.get('qualifier_sha256')!=sha256(HERE/'qualify.py') or
            len(qualification.get('checks',[]))<95):
        raise ValueError('CGR locked registration/qualification differs')
    calls=schedule(manifest['entries'])
    paths=_source_files(args)
    actual={name:sha256(path) for name,path in paths.items()}
    expected=json.loads(args.source_bindings.read_text())
    if actual!=expected:
        raise ValueError('production source binding differs')
    generate_variants.verify(args.source/'src/twofft.py')
    sys.path[:0]=[str(args.source/'src'),str(args.baseline/'src')]
    import tf_block
    tf_block.bind_source(args.source/'src/block_bilinear.py')
    # Hash every supplied observation before receiver context or output creation.
    for entry in manifest['entries']:
        _observed_file(entry,args.witness_root)
    return manifest,calls,actual


def _branch(obs,system,code,native,kernel,arrays,detector):
    from messages import moments
    from physical import Channel,daft

    stamp=time.perf_counter()
    app=np.clip(arrays['r1_app'],-20,20)
    check=np.clip(arrays['r1_check'],-20,20)
    mu,v,_=moments(app,1-system.rho)
    initial=[kernel.Path(int(delay),float(nu)) for delay,nu in zip(
        arrays['r1_delays'],arrays['r1_dopplers'])]
    if len(initial)!=len(arrays['r1_gains']):
        raise ValueError('native path slots differ')
    message_end=time.perf_counter()
    Y=daft(obs['y'],system.c1,system.c2,True)
    transform_end=time.perf_counter()
    result=kernel.reopen_geometry(Y,obs['pilot']+mu,v,initial,
        c1=system.c1,c2=system.c2,ridge=float(obs['sigma2']),
        max_delay=system.l_max_cap,doppler_min=-3.,doppler_max=3.,
        grid_step=.25,max_edits=2,chunk_size=64,local_passes=2,
        local_halfwidth=.75,local_max_evals=16,duplicate_tolerance=1e-6,
        top_k=20,strategy='compact')
    geometry_end=time.perf_counter()
    if len(result.paths)!=len(initial):
        raise ValueError('CSTATE changed slot count')
    stage=result.diagnostics['stage_timing']
    exclusive=stage['exclusive_seconds']
    expected=set(STAGES[2:10])
    if set(exclusive)!=expected or any(not np.isfinite(x) or x<0 for x in exclusive.values()):
        raise ValueError('CSTATE exclusive stage inventory differs')
    if not np.isclose(sum(exclusive.values()),stage['total_seconds'],rtol=0,atol=1e-6):
        raise ValueError('CSTATE stage timing differs')
    overhead=geometry_end-transform_end-stage['total_seconds']
    if overhead<0:
        raise ValueError('CSTATE clock exceeds wrapper')
    validation_end=time.perf_counter()
    channel=Channel(len(obs['y']),system.c1,system.c2,
        [p.delay for p in result.paths],[p.doppler for p in result.paths],result.gains)
    channel_end=time.perf_counter()
    entering=dict(app=app,check=check,ce_mu=mu,ce_variance=v,
        initial_delays=np.asarray([p.delay for p in initial]),
        initial_dopplers=np.asarray([p.doppler for p in initial]),
        delays=channel.delays,dopplers=channel.dopplers,gains=channel.gains)
    entering_hash=_hash_value(entering)
    from twofft import TimePathOps
    R=TimePathOps(channel).R
    eig=np.linalg.eigvalsh(R)
    tol=1e-10
    if (np.max(abs(R-R.conj().T))>tol or np.max(abs(np.diag(R)-1))>tol or
            eig.min() < -tol):
        raise ValueError('physical R Hermitian/unit/PSD qualification failed')
    groups={str(int(delay)):int(np.count_nonzero(channel.delays==delay))
            for delay in np.unique(channel.delays)}
    coherence=float(np.max(abs(R-np.eye(channel.p))))
    Gamma=channel.gamma(v)
    B=channel.regressors(obs['pilot']+mu)
    response_gram=B.conj().T@B
    same=channel.delays[:,None]==channel.delays[None,:]
    moment_error=float(np.max(abs((Gamma-len(obs['y'])*float(v.mean())*R)[same])))
    if moment_error>1e-8:
        raise ValueError('same-delay frozen working moment identity differs')
    gram=dict(R=R,eigenvalues=eig,group_multiplicities=groups,
              max_within_group_coherence=coherence,Gamma=Gamma,
              response_gram=response_gram,same_delay_moment_error=moment_error)
    detector_result=detector.scalar_joint(obs['y'],obs['pilot'],channel,obs['sigma2'],
        pd=1-system.rho,prior=check,iterations=20,damping=.3,gain_mode='joint',
        record_states=True)
    tf_end=time.perf_counter()
    decoder=native.decoder_messages(code,np.clip(detector_result['extrinsic'],-20,20),maxiter=50)
    decision_end=time.perf_counter()
    stages=dict(message_handling=message_end-stamp,y_transform=transform_end-message_end,
        **exclusive,geometry_wrapper_overhead=overhead,
        wrapper_validation=validation_end-geometry_end,
        channel_construction=channel_end-validation_end,
        tf=tf_end-channel_end,ldpc=decision_end-tf_end)
    if not np.isclose(sum(stages.values()),decision_end-stamp,rtol=0,atol=1e-7):
        raise ValueError('branch exclusive clocks differ')
    return dict(result=result,detector=detector_result,decoder=decoder,
        entering=entering,entering_sha256=entering_hash,gram=gram,
        decision_ready_at=decision_end,branch_origin=stamp,
        exclusive_stages=stages,branch_decision_seconds=decision_end-stamp)


def _scalar_states(states):
    keys=('h_pre','h','hbar','vx','alpha','vq','xbar_energy','vr','vh',
          'bar','vp','physical_R','gain_R')
    return [{name:state[name] for name in keys} for state in states]


def _base_common_state(states,n):
    rows=[]
    for index,state in enumerate(states):
        R=state['physical_R'];P=len(state['hbar'])
        dh=(-state['alpha']*n*state['vx']/(P+1/state['vq'])*
            (R-np.eye(P))@state['hbar'])
        physical=float(np.vdot(dh,R@dh).real)
        if physical < -1e-10:
            raise ValueError('negative common-state physical correction norm')
        rows.append(dict(iteration=index,dh=dh,
            physical_norm_squared=max(0.,physical),
            reciprocal_precision=1/state['vq']))
    return rows


def _persist_jsonl(path,row):
    with path.open('a') as stream:
        stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def run(args):
    manifest,calls,source_hashes=preflight(args)
    evidence=attach(args.source,args.baseline)
    import native_twofft as native
    import geometry_validation as kernel
    import tf_base
    import tf_cgr
    import tf_sham
    import tf_block
    from receiver import context

    environment=evidence.bind_runtime_environment()
    setup_start=time.perf_counter()
    system,_,code,header=context()
    setup_seconds=time.perf_counter()-setup_start
    evidence.verify_runtime_binding()
    if system.N_total!=1024 or system.l_max_cap!=102 or system.rho!=.5:
        raise ValueError('frozen receiver context differs')
    with np.load(_source_files(args)['code_cache'],allow_pickle=False) as saved:
        H=np.asarray(saved['H']);G=np.asarray(saved['G']);free=np.asarray(saved['free_cols'])
    if (H.shape!=(1026,2048) or G.shape!=(2048,1024) or free.shape!=(1024,) or
            hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest()!=header['code_g_sha256']):
        raise ValueError('actual H/G/free code identity differs')
    args.out.mkdir(parents=True)
    for name in ('checkpoints','raw','decisions'):
        (args.out/name).mkdir()
    write_json(args.out/'manifest.json',dict(schema=SCHEMA,expected_calls=100,
        registration_sha256=sha256(args.registration),
        qualification_sha256=sha256(args.qualification),
        witness_manifest_sha256=sha256(args.witness_manifest),
        witness_receipt_sha256=sha256(args.witness_receipt),
        source_bindings_sha256=sha256(args.source_bindings),source_hashes=source_hashes,
        code_g_sha256=header['code_g_sha256'],arms=list(ARMS),
        runtime_environment=environment,setup_seconds=setup_seconds,
        seconds_cap=args.seconds,bytes_cap=args.bytes_cap,
        clock='input load through decision record write; ledger append outside',
        trace_state_semantics=dict(h_pre='gain before current update',
            h='gain after current update',hbar='damped gain entering current update',
            x='data mean after current QPSK marginal',
            xbar='damped data mean entering current update',
            mu='QPSK data mean after current marginal',
            v='QPSK data variance after current marginal',
            s='output residual after current output update',
            alpha='output precision after current output update',
            bar='output variance at current output update',
            vp='total output variance at current output update'),
        argv=sys.argv[:],pid=os.getpid()))
    ledger=args.out/'ledger.jsonl';ledger.touch(exist_ok=False)
    start=time.perf_counter();detectors=dict(BASE=tf_base,CGR=tf_cgr,SHAM=tf_sham,BLOCK=tf_block)
    for number,(entry,arm) in enumerate(calls,1):
        if time.perf_counter()-start>=args.seconds:
            raise TimeoutError('CGR fixed campaign 30min cap reached')
        if sum(p.stat().st_size for p in args.out.rglob('*') if p.is_file())>=args.bytes_cap:
            raise RuntimeError('CGR fixed campaign 2GiB cap reached')
        obs_id=entry['observation_id'];origin=time.perf_counter()
        identity=dict(schema=SCHEMA,observation_id=obs_id,arm=arm)
        row=dict(status='inflight',call_index=number,observation_id=obs_id,
            role=entry['role'],arm=arm,receiver_started=False,checkpoints=[])
        def sink(event,decoded):
            round_index=int(event['round']);ready=time.perf_counter()-origin
            path=args.out/'checkpoints'/f'{obs_id}_{arm}_r{round_index}.npz'
            digest=evidence.save_artifact(path,
                dict(event=event,decoded=np.asarray(decoded).copy()),
                dict(identity,round=round_index))
            syndrome=int(np.count_nonzero((H@np.asarray(decoded,dtype=np.int32))%2))
            row['checkpoints'].append(dict(round=round_index,
                path=str(path.relative_to(args.out)),artifact_sha256=digest,
                decision_ready_seconds=ready,
                artifact_ready_seconds=time.perf_counter()-origin,
                syndrome_weight=syndrome,
                event={key:value for key,value in event.items() if key!='snapshot'}))
        try:
            file,digest=_observed_file(entry,args.witness_root)
            payload=load_bound(evidence,file,digest)
            obs=_input_observation(payload,obs_id)
            row['input_sha256']=digest
            input_end=time.perf_counter()
            row['receiver_started']=True
            native_dec,arrays,native_timing=native.receive(obs,system,code,
                rounds=2,iterations=20,ce_mode='soft',gain_mode='joint',checkpoint_sink=sink)
            native_end=time.perf_counter()
            if len(row['checkpoints'])!=2 or not np.array_equal(native_dec['decoded'],arrays['r1_decoded']):
                raise ValueError('native two-round checkpoint differs')
            syndrome=row['checkpoints'][-1]['syndrome_weight']
            triggered=syndrome!=0
            branch=None;numeric_error=None;branch_start=time.perf_counter()
            if triggered:
                try:
                    branch=_branch(obs,system,code,native,kernel,arrays,detectors[arm])
                except (FloatingPointError,np.linalg.LinAlgError) as error:
                    numeric_error=repr(error)
            branch_end=time.perf_counter()
            if branch is not None:
                dec=branch['decoder']
                event=dict(round=2,ready=branch_end-origin,
                    ce=branch['result'].elapsed_seconds,
                    inference=branch['exclusive_stages']['tf'],
                    decoder=branch['exclusive_stages']['ldpc'],
                    ce_evaluations=branch['result'].evaluations,
                    inference_iterations=20,decoder_iterations=int(dec['iterations']))
                sink(dict(event,snapshot=dict(decoded=dec['decoded'],
                    input_llr=dec['incoming_llr'],app=dec['raw_app'],
                    check=dec['raw_check_extrinsic'],
                    delays=branch['entering']['delays'],
                    dopplers=branch['entering']['dopplers'],
                    geometry_gains=branch['entering']['gains'],
                    inference_gains=branch['detector']['gains'])),dec['decoded'])
            final=native_dec if branch is None else branch['decoder']
            bits=np.asarray(final['decoded'])
            if bits.shape!=(2048,) or not np.isin(bits,[0,1]).all():
                raise ValueError('invalid final decoded bits')
            final_syndrome=int(np.count_nonzero((H@bits.astype(np.int32))%2))
            raw=args.out/'raw'/f'{obs_id}_{arm}.npz'
            branch_detector=None
            common_state=None
            if branch is not None:
                branch_detector=dict(branch['detector'])
                if arm=='BASE':
                    common_state=_base_common_state(branch_detector['states'],len(obs['y']))
                if obs_id not in TARGET_IDS:
                    branch_detector['states']=_scalar_states(branch_detector['states'])
            raw_payload=dict(observation_id=obs_id,arm=arm,input_sha256=digest,
                native_arrays=arrays,native_timing=native_timing,native_decoder=native_dec,
                triggered=triggered,numerical_failure=numeric_error,
                entering=None if branch is None else branch['entering'],
                gram=None if branch is None else branch['gram'],
                geometry_result=None if branch is None else asdict(branch['result']),
                branch_detector=branch_detector,
                base_common_state=common_state,
                trace_origin='newly instrumented replay of frozen observed witness',
                branch_decoder=None if branch is None else branch['decoder'],
                final_decoded=bits)
            raw_sha=evidence.save_artifact(raw,raw_payload,identity)
            raw_ready=time.perf_counter()
            decision_path=args.out/'decisions'/f'{obs_id}_{arm}.json'
            decision=dict(schema=SCHEMA,observation_id=obs_id,arm=arm,
                input_sha256=digest,triggered=triggered,numerical_failure=numeric_error,
                baseline_syndrome_weight=syndrome,final_syndrome_weight=final_syndrome,
                final_decoded_sha256=hashlib.sha256(bits.tobytes()).hexdigest(),
                final_decision_ready_seconds=row['checkpoints'][-1]['decision_ready_seconds'],
                checkpoints=row['checkpoints'],raw_path=str(raw.relative_to(args.out)),
                raw_sha256=raw_sha,entering_sha256=None if branch is None else branch['entering_sha256'])
            write_json(decision_path,decision)
            complete_end=time.perf_counter()
            row.update(status='ok',triggered=triggered,numerical_failure=numeric_error,
                baseline_syndrome_weight=syndrome,final_syndrome_weight=final_syndrome,
                final_decoded_sha256=decision['final_decoded_sha256'],
                final_decision_ready_seconds=decision['final_decision_ready_seconds'],
                input_load_seconds=input_end-origin,native_two_rounds_seconds=native_end-input_end,
                branch_elapsed_seconds=branch_end-branch_start,
                branch_decision_seconds=None if branch is None else branch['branch_decision_seconds'],
                branch_complete_seconds=complete_end-branch_start if triggered else 0.,
                branch_exclusive_stages=None if branch is None else branch['exclusive_stages'],
                entering_sha256=decision['entering_sha256'],
                raw_artifact_ready_seconds=raw_ready-origin,
                complete_latency_seconds=complete_end-origin,
                raw_path=decision['raw_path'],raw_sha256=raw_sha,
                decision_path=str(decision_path.relative_to(args.out)),
                decision_sha256=sha256(decision_path))
            _persist_jsonl(ledger,row)
        except BaseException as error:
            row.update(status='failed',exception=repr(error),traceback=traceback.format_exc(),
                       elapsed_seconds=time.perf_counter()-origin)
            _persist_jsonl(ledger,row)
            write_json(args.out/'blocked.json',dict(reason=repr(error),failed_call=number,
                observation_id=obs_id,arm=arm))
            raise
        if sum(p.stat().st_size for p in args.out.rglob('*') if p.is_file())>=args.bytes_cap:
            write_json(args.out/'blocked.json',dict(reason='CGR fixed campaign 2GiB cap reached',
                after_call=number,completed_rows=number))
            raise RuntimeError('CGR fixed campaign 2GiB cap reached after completed call')
    inventory={str(p.relative_to(args.out)):sha256(p) for p in args.out.rglob('*')
               if p.is_file() and p.name!='observed_seal.json'}
    write_json(args.out/'observed_seal.json',dict(schema=SCHEMA,status='pass',
        completed_calls=100,witness_manifest_sha256=sha256(args.witness_manifest),
        source_bindings_sha256=sha256(args.source_bindings),files=inventory))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ('source','baseline','geometry','witness-root','witness-manifest',
                'witness-receipt','registration','qualification',
                'source-bindings','out'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=SECONDS_CAP)
    parser.add_argument('--bytes-cap',type=int,default=BYTES_CAP)
    parser.add_argument('--preflight-only',action='store_true')
    args=parser.parse_args()
    if args.preflight_only:
        manifest,calls,hashes=preflight(args)
        print(json.dumps(dict(status='preflight_pass',calls=len(calls),
                              source_files=len(hashes),witnesses=manifest['n_frames'])))
    else:
        run(args)
