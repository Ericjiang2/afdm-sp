"""Bounded P-02 development only; immutable identities, no retry or confirmation."""
import argparse
import fcntl
import hashlib
import json
import math
from pathlib import Path
import signal
import shutil
import sys
import time
import traceback

from .supplement_baseline_run import (BaselineReceiver, recipe_by_id, terminal_snapshot,
    publish_bounded, output_bytes, PER_TERMINAL_BYTES, FAILURE_RESERVE_BYTES,
    torch, np, build_code, build_receiver, _make_config_a, CHECKPOINT_HASH)
from .supplement_run import sha, sources, json_value
from .supplement_data import SupplementData, CAMPAIGN_ID, campaign_rng
from .supplement_profile import score_errors
from .supplement_pilot_frames import pilot_frames
from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash

RECIPES=['B0-p2-s0.5','bounded-param-p3-s1','group-p3-s1','ridge-p3-s0.5',
         'SBL-p2-s0.5','B0-p3-s0.5','B0-p2-s1','bounded-param-p2-s1']
FILES=('protocol','pilot_protocol','design','pilots','pilot_manifest','checkpoint')


def identities(mode,start,stop):
    if mode not in ('Pfixed','Pmatched') or not 0<=start<stop<=192 or stop-start>16:
        raise ValueError('design requires 1..16 blocks within [0,192) and a frozen mode')
    return [(mode,b,s,p,r) for b in range(start,stop)
            for s in ([7,8,9] if mode=='Pfixed' else [8])
            for p in ('p0','p1','p2') for r in (RECIPES[:1] if mode=='Pfixed' else RECIPES)]


def validate_args(args):
    ids=identities(args.mode,args.start,args.stop)
    if type(args.max_full_calls) is not int or args.max_full_calls!=len(ids):
        raise ValueError('reserve exactly the requested identity count')
    if not math.isfinite(args.deadline_unix) or args.deadline_unix<=time.time():
        raise ValueError('finite future deadline required')
    if type(args.max_output_bytes) is not int or args.max_output_bytes<len(ids)*PER_TERMINAL_BYTES+32*1024**2:
        raise ValueError('output budget below terminal estimate')
    return ids


def validate_reservation(row):
    raw=row['identities'];unique={tuple(i) for i in raw}
    if (type(row['max_full_calls']) is not int or not unique or
            len(raw)!=len(unique) or len(unique)!=row['max_full_calls'] or
            row['calls_reserved']!={'F':len(unique),'T':0,'E':0}):
        raise ValueError('invalid reservation accounting')
    for identity in unique:
        if (len(identity)!=5 or type(identity[1]) is not int or
                identity not in identities(identity[0],identity[1],identity[1]+1)):
            raise ValueError('invalid reservation identity')
    return unique


def validate_geometry(manifest,protocol,system):
    expected=dict(N=1024,l_max=102,k_max=2,rho=.5,prefix_length=102,
                  papr_limit_db=12.,peak_power_limit=16.)
    if any(protocol[k]!=v for k,v in expected.items()):raise ValueError('pilot power/geometry contract changed')
    geometry=manifest['geometry']
    if (any(geometry[k]!=expected[k] for k in ('N','l_max','k_max')) or
            geometry['c1']!=system.c1 or geometry['c2']!=system.c2 or
            system.rho!=protocol['rho']):raise ValueError('pilot/system geometry mismatch')
    return {k:protocol[k] for k in ('rho','prefix_length','papr_limit_db','peak_power_limit')}


def reserve(ledger,contract):
    ledger.mkdir(parents=True,exist_ok=True)
    requested=validate_reservation(contract)
    with (ledger/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        used=0;seen=set()
        for path in ledger.glob('reservation-*.json'):
            row=json.loads(path.read_text())
            previous=validate_reservation(row)
            if (row['campaign_id']!=CAMPAIGN_ID or row['bindings']!=contract['bindings'] or
                    type(row['max_full_calls']) is not int or len(previous)!=row['max_full_calls']):
                raise ValueError('shared ledger binding or accounting mismatch')
            if seen & previous:raise ValueError('historical ledger identities overlap')
            seen.update(previous)
            if requested & previous:raise ValueError('identity already reserved; no automatic retry')
            used+=row['max_full_calls']
        if used+len(requested)>6336:raise ValueError('shared P-02 6336F cap exceeded')
        publish_json(ledger/('reservation-'+contract['config_sha256']+'.json'),contract)


def assert_unchanged(args,bindings):
    if ({k:sha(getattr(args,k)) for k in FILES}!=bindings['files'] or
            sources()!=bindings['source_sha256']):
        raise ValueError('frozen input/source changed; no fallback')


def make_record(frame,result,identity,contract,wall,cpu,peak):
    mode,block,snr,pilot,recipe=identity;m=frame.metadata
    if (m['split']!='design' or m['block']!=block or m['snr_db']!=snr or
            m['pilot_id']!=pilot or m['protocol_sha256']!=contract['bindings']['files']['protocol'] or
            any(m['input_hashes'][k]!=array_hash(frame.observed[k]) for k in ('y','pilot')) or
            not math.isfinite(wall+cpu) or min(wall,cpu,peak)<0):
        raise ValueError('pilot record identity/input/cost mismatch')
    hhash=array_hash(result['H'])
    row=dict(schema='supplement-pilot-design-frame-v1',campaign_id=CAMPAIGN_ID,
        identity=identity,metadata=m,recipe=recipe_by_id(recipe),config_sha256=contract['config_sha256'],
        bindings=contract['bindings'],call_type='full',truth_access_level='none',
        offline_truth_access='evaluation_only',failure=None,retry_of=None,
        elapsed_seconds=wall,process_cpu_seconds=cpu,peak_gpu_bytes=peak,
        timing_scope='complete F including terminal BP and LDPC; T=0',
        H_cancel_source=hhash,H_data_source=hhash,H_cov_source=hhash,
        sigma_value=result['sigma2_terminal'],decoder_status={'syndrome_ok':bool(result['decode_ok']),'maxiter':50},
        baseline_eligible=bool(result['baseline_eligible']),initial_estimator=result['initial_estimator'],
        support=result['support'],capacity_trace=result['capacity_trace'],graphs=result['graphs'])
    if not np.isfinite(row['sigma_value']) or row['sigma_value']<=0:raise ValueError('invalid terminal variance')
    row.update(score_errors(result,frame._truth));row=json_value(row)
    json.dumps(row,allow_nan=False)
    return row


def execute(args):
    ids=validate_args(args)
    args.out.mkdir(parents=True,exist_ok=False)
    previous=signal.getsignal(signal.SIGALRM);attempted=0;completed=[];records=[];failures=[];active=None
    contract=None;active_started=None
    def publish(name,value,reserve_bytes=FAILURE_RESERVE_BYTES):
        publish_bounded(args.out/name,json_value(value),args.out,args.max_output_bytes-reserve_bytes)
    def failure(exc,identity):
        item=dict(identity=identity,exception=type(exc).__name__,message=str(exc)[:16384],
                  traceback=traceback.format_exc()[-32768:],FER=None,full_call_started=identity==active,
                  elapsed_seconds=time.perf_counter()-active_started[0] if identity==active else None,
                  process_cpu_seconds=time.process_time()-active_started[1] if identity==active else None)
        publish(f'failure-{len(failures):05d}.json',item);failures.append(identity)
    try:
        def timeout(*_):raise TimeoutError('P-02 finite deadline reached')
        signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,args.deadline_unix-time.time())
        bindings={'files':{k:sha(getattr(args,k)) for k in FILES},'source_sha256':sources()}
        design=json.loads(args.design.read_text());manifest=json.loads(args.pilot_manifest.read_text())
        pilot_protocol=json.loads(args.pilot_protocol.read_text())
        if (design['total_F']!=6336 or design['Pfixed']['recipe']!=RECIPES[0] or
                design['Pmatched']['recipes']!=RECIPES or
                any(design[k]['blocks']!=192 or design[k]['pilots']!=['p0','p1','p2'] for k in ('Pfixed','Pmatched')) or
                design['Pfixed']['snrs']!=[7,8,9] or design['Pmatched']['snrs']!=[8] or
                design['pilot_sha256']!=bindings['files']['pilots'] or
                manifest['pilot_npz_sha256']!=bindings['files']['pilots'] or
                manifest['protocol_sha256']!=bindings['files']['pilot_protocol'] or
                bindings['files']['checkpoint']!=CHECKPOINT_HASH):
            raise ValueError('frozen P-02 design/pilot/protocol/checkpoint mismatch')
        with np.load(args.pilots,allow_pickle=False) as loaded:
            if set(loaded.files)!={'p0','p1','p2'}:raise ValueError('invalid pilot archive')
            pilots={k:loaded[k].copy() for k in loaded.files}
        torch.set_num_threads(1);device=torch.device(args.device)
        if device.type not in ('cpu','cuda'):raise ValueError('unsupported device')
        if device.type=='cuda':
            if not torch.cuda.is_available():raise ValueError('CUDA unavailable')
            device=torch.device('cuda',device.index if device.index is not None else torch.cuda.current_device())
            torch.cuda.set_device(device);torch.cuda.set_per_process_memory_fraction(.25,device)
        if shutil.disk_usage(args.out).free<len(ids)*PER_TERMINAL_BYTES+32*1024**2:
            raise OSError('insufficient disk for reserved terminals')
        (args.out/'code-cache').mkdir()
        code=build_code(cache_dir=args.out/'code-cache');data=SupplementData(args.protocol,code)
        system=_make_config_a(1024,2.,8,10.,4.)
        power_kwargs=validate_geometry(manifest,pilot_protocol,system)
        contract=dict(campaign_id=CAMPAIGN_ID,identities=ids,bindings=bindings,
            device=str(device),threads=torch.get_num_threads(),
            versions={'python':sys.version,'torch':torch.__version__,'numpy':np.__version__},
            max_full_calls=args.max_full_calls,calls_reserved={'F':len(ids),'T':0,'E':0},
            deadline_unix=args.deadline_unix,max_output_bytes=args.max_output_bytes,
            code_sha256={k:array_hash(code[k]) for k in ('G','H')},command=[sys.executable,*sys.argv],
            policy='no overwrite, retry, reclaim, replacement, power filtering, or confirmation')
        contract['config_sha256']=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
        # One ledger anchored to the immutable design, independent of batch output locations.
        reserve(args.design.resolve().parent/'pilot-development-ledger',contract)
        publish('contract.json',contract)
        model=build_receiver(args.checkpoint,system,1024,args.device,receiver_shell='direct40',active_cap=40)
        for block in range(args.start,args.stop):
            for snr in ([7,8,9] if args.mode=='Pfixed' else [8]):
                group=[i for i in ids if i[1]==block and i[2]==snr]
                campaign_rng('design',block,'order').shuffle(group)
                assert_unchanged(args,bindings)
                try:
                    frame=data.make_frame(system,'design',block,snr)
                    frames=pilot_frames(frame,pilots,c1=system.c1,c2=system.c2,**power_kwargs)
                except (TimeoutError,KeyboardInterrupt):raise
                except Exception as exc:
                    for identity in group:failure(exc,identity)
                    continue
                for identity in group:
                    assert_unchanged(args,bindings)
                    if attempted>=len(ids) or time.time()>=args.deadline_unix:raise TimeoutError('budget/deadline')
                    if output_bytes(args.out)+PER_TERMINAL_BYTES+65536>args.max_output_bytes-FAILURE_RESERVE_BYTES:
                        raise OSError('insufficient remaining terminal budget')
                    active=identity;attempted+=1;active_started=(time.perf_counter(),time.process_time())
                    publish(f'call-{attempted:05d}-started.json',dict(identity=identity,started_unix=time.time()))
                    frame=frames[identity[3]]
                    try:
                        if device.type=='cuda':torch.cuda.synchronize(device);torch.cuda.reset_peak_memory_stats(device)
                        wall,cpu=time.perf_counter(),time.process_time()
                        receiver=BaselineReceiver(model,code,identity[4],system=system)
                        result=receiver.run(frame.observed,audit=True)
                        if device.type=='cuda':torch.cuda.synchronize(device)
                        row=make_record(frame,result,identity,contract,time.perf_counter()-wall,time.process_time()-cpu,
                            int(torch.cuda.max_memory_allocated(device)) if device.type=='cuda' else 0)
                        row['terminal']=terminal_snapshot(args.out/f'terminal-{attempted:05d}.npz',frame,result,
                            budget_root=args.out,max_bytes=args.max_output_bytes-FAILURE_RESERVE_BYTES)
                        assert_unchanged(args,bindings)
                        name=f'frame-{attempted:05d}.json';publish(name,row)
                        path=args.out/name
                        records.append(dict(path=str(path.resolve()),sha256=sha(path)))
                        completed.append(identity)
                    except (TimeoutError,KeyboardInterrupt):raise
                    except Exception as exc:failure(exc,identity)
                    finally:active=None
                    assert_unchanged(args,bindings)
        assert_unchanged(args,bindings)
        publish('summary.json',dict(status='completed_with_failures' if failures else 'complete',
            exitcode=int(bool(failures)),records=records,
            calls_attempted=attempted,calls_completed=len(completed),failures=failures,
            missing_or_failed_identities=[i for i in ids if i not in completed],
            config_sha256=contract['config_sha256'],scope='development; no scientific success claim'))
        return int(bool(failures))
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        publish('batch-failure.json',dict(exception=type(exc).__name__,message=str(exc)[:16384],
            traceback=traceback.format_exc()[-32768:],active_identity=active,calls_attempted=attempted,
            calls_completed=len(completed),missing_or_failed_identities=[i for i in ids if i not in completed],
            config_sha256=contract['config_sha256'] if contract else None),reserve_bytes=0)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in (*FILES,'out'):parser.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    parser.add_argument('--mode',choices=('Pfixed','Pmatched'),required=True)
    for name in ('start','stop','max-full-calls','max-output-bytes'):parser.add_argument('--'+name,type=int,required=True)
    parser.add_argument('--deadline-unix',type=float,required=True);parser.add_argument('--device',required=True)
    return execute(parser.parse_args())


if __name__=='__main__':sys.exit(main())
