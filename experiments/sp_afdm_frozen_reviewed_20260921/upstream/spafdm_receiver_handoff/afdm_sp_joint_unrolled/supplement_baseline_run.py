"""Bounded supplement BASE batches; failures remain in their original identities."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time
import traceback

for _key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key]='1'
import numpy as np
import torch
from .supplement_baselines import BaselineReceiver,catalogue,a02_catalogue,recipe_by_id
from .supplement_data import SupplementData,CAMPAIGN_ID,campaign_rng
from .supplement_run import sha,sources,json_value,validate_record as validate_engineering_record
from .supplement_profile import reserve_profile,assert_content_unchanged,score_errors
from .budgeted_frame_store import publish_json
from .budgeted_support_eval import build_receiver
from .budgeted_support_diagnostics import array_hash
from .direction_receiver import CHECKPOINT_HASH
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a

LIMITS={'engineering':32,'design':192}
PER_TERMINAL_BYTES=24*1024**2
FAILURE_RESERVE_BYTES=256*1024
BASE_STAGE='BASE-01'
A02_STAGE='A-02'
A02_PROTOCOL_SCHEMA='supplement-A02-development-protocol-v1'
A02_BATCH_POLICY='all nine arms per selected block; no retry/reclaim/replacement'


def output_bytes(root):
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def publish_bounded(path,value,root,limit):
    size=len(json.dumps(value,sort_keys=True,allow_nan=False).encode())
    if output_bytes(root)+size>limit:
        raise OSError("output publication would exceed frozen storage budget")
    publish_json(path,value)


def validate_a02_protocol(args):
    if (not isinstance(getattr(args,'a02_protocol',None),Path) or
            not isinstance(getattr(args,'a02_protocol_sha256',None),str) or
            len(args.a02_protocol_sha256)!=64 or
            sha(args.a02_protocol)!=args.a02_protocol_sha256):
        raise ValueError('A-02 protocol hash mismatch')
    value=json.loads(args.a02_protocol.read_text())
    required={'schema','campaign_id','stage','split','block_start','block_stop','snrs','recipe_ids',
              'total_F','data_protocol_sha256','checkpoint_sha256','batch_policy'}
    if (not isinstance(value,dict) or set(value)!=required or
            value['schema']!=A02_PROTOCOL_SCHEMA or value['campaign_id']!=CAMPAIGN_ID or
            value['stage']!=A02_STAGE or value['split']!='design' or
            (value['block_start'],value['block_stop'])!=(0,192) or value['snrs']!=[8] or
            value['recipe_ids']!=[r['id'] for r in a02_catalogue()] or value['total_F']!=1728 or
            value['data_protocol_sha256']!=sha(args.protocol) or
            value['checkpoint_sha256']!=sha(args.checkpoint) or
            value['batch_policy']!=A02_BATCH_POLICY):
        raise ValueError('invalid frozen A-02 development protocol')
    return value


def validate_args(args):
    stage=getattr(args,'stage',BASE_STAGE)
    if (args.split not in LIMITS or not 0<=args.start<args.stop<=LIMITS[args.split] or args.snr!=8):
        raise ValueError('only engineering[0,32)/design[0,192) at8dB')
    if stage==A02_STAGE:
        if getattr(args,'recipes',None) is not None:raise ValueError('A-02 recipes come only from its protocol')
        protocol=validate_a02_protocol(args);ids=protocol['recipe_ids']
    else:
        if (getattr(args,'recipes',None) is None or getattr(args,'a02_protocol',None) is not None or
                getattr(args,'a02_protocol_sha256',None) is not None):
            raise ValueError('BASE requires recipes and forbids A-02 protocol inputs')
        ids=json.loads(args.recipes)
    if not isinstance(ids,list) or not ids or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('explicit unique recipe ID JSON list required')
    recipes=[recipe_by_id(i) for i in ids]
    count=(args.stop-args.start)*len(recipes)
    if stage==A02_STAGE:
        expected=a02_catalogue()
        if (args.split!='design' or len(recipes)!=9 or set(ids)!={r['id'] for r in expected} or
                type(args.max_full_calls) is not int or args.max_full_calls!=count or count>1728):
            raise ValueError('A-02 requires all nine arms per design block and exact <=1728F reservation')
    elif stage==BASE_STAGE:
        cap=128 if args.split=='engineering' else 7680
        if (any(i not in {r['id'] for r in catalogue()} for i in ids) or
                type(args.max_full_calls) is not int or not count<=args.max_full_calls<=cap):
            raise ValueError('requested BASE F count exceeds recipe/reservation/stage cap')
    else:raise ValueError('unknown baseline runner stage')
    if not math.isfinite(args.deadline_unix) or args.deadline_unix<=time.time():
        raise ValueError('future finite deadline required')
    estimated=count*PER_TERMINAL_BYTES+32*1024**2
    if type(args.max_output_bytes) is not int or args.max_output_bytes<estimated:
        raise ValueError('output budget below conservative uncompressed terminal estimate')
    return recipes,estimated


def reserve_design(out,contract):
    ledger=out.parent/'supplement-baseline-design-ledger'
    ledger.mkdir(exist_ok=True)
    with (ledger/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        requested={(block,r['id']) for block in range(contract['start'],contract['stop'])
                   for r in contract['recipes']}
        if not requested or len(requested)>contract['max_full_calls']:
            raise ValueError('invalid design identity reservation')
        used=0
        for path in ledger.glob('reservation-*.json'):
            row=json.loads(path.read_text())
            if (row['campaign_id']!=CAMPAIGN_ID or row['stage']!='BASE-01-design' or
                    type(row['max_full_calls']) is not int or row['max_full_calls']<0):
                raise ValueError('invalid shared BASE design reservation')
            if 'identities' not in row:
                raise ValueError('legacy design reservation lacks frozen identities')
            if requested & {tuple(i) for i in row['identities']}:
                raise ValueError('design block/recipe already reserved; no automatic retry')
            used+=row['max_full_calls']
        if used+contract['max_full_calls']>7680:
            raise ValueError('cumulative BASE design7680F cap exceeded')
        key=hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger/f'reservation-{key}.json',dict(campaign_id=CAMPAIGN_ID,
            stage='BASE-01-design',out=str(out.resolve()),max_full_calls=contract['max_full_calls'],
            config_sha256=contract['config_sha256'],identities=sorted(requested),
            policy='no automatic reclaim; failures remain charged'))
    return str(ledger)


def reserve_a02(out,contract):
    ledger=out.parent/'supplement-a02-development-ledger'
    ledger.mkdir(exist_ok=True)
    with (ledger/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        expected={r['id'] for r in a02_catalogue()}
        def identities(value):
            try:
                sequence=[tuple(item) for item in value]
                result=set(sequence)
            except (TypeError,ValueError) as exc:raise ValueError('invalid A-02 identity list') from exc
            if len(sequence)!=len(result):raise ValueError('duplicate A-02 ledger identity')
            if (any(len(item)!=2 or type(item[0]) is not int or not 0<=item[0]<192 or
                    item[1] not in expected for item in result)):
                raise ValueError('invalid A-02 identity domain')
            blocks={block for block,_ in result}
            if len(result)!=9*len(blocks) or any({arm for block,arm in result if block==b}!=expected
                                                  for b in blocks):
                raise ValueError('A-02 ledger requires all nine arms for every block')
            return result
        requested=identities((block,r['id']) for block in range(contract['start'],contract['stop'])
                             for r in contract['recipes'])
        blocks={block for block,_ in requested}
        if (contract.get('stage')!=A02_STAGE or contract.get('split')!='design' or
                len(requested)!=9*len(blocks) or {arm for _,arm in requested}!=expected or
                contract['max_full_calls']!=len(requested)):
            raise ValueError('invalid A-02 all-nine identity reservation')
        used=0
        for path in ledger.glob('reservation-*.json'):
            row=json.loads(path.read_text())
            if (row.get('campaign_id')!=CAMPAIGN_ID or row.get('stage')!='A-02-development' or
                    type(row.get('max_full_calls')) is not int or 'identities' not in row or
                    any(row.get(key)!=contract[key] for key in
                        ('source_sha256','checkpoint_sha256','protocol_sha256','a02_protocol_sha256'))):
                raise ValueError('invalid shared A-02 reservation')
            prior=identities(row['identities'])
            if row['max_full_calls']!=len(prior):raise ValueError('A-02 reservation count mismatch')
            if requested & prior:raise ValueError('A-02 block/arm already reserved; no retry/reclaim')
            used+=row['max_full_calls']
        if used+len(requested)>1728:raise ValueError('cumulative A-02 development 1728F cap exceeded')
        key=hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger/f'reservation-{key}.json',dict(campaign_id=CAMPAIGN_ID,
            stage='A-02-development',out=str(out.resolve()),max_full_calls=len(requested),
            calls_reserved={'F':len(requested),'T':0,'E':0},
            config_sha256=contract['config_sha256'],source_sha256=contract['source_sha256'],
            checkpoint_sha256=contract['checkpoint_sha256'],protocol_sha256=contract['protocol_sha256'],
            a02_protocol_sha256=contract['a02_protocol_sha256'],identities=sorted(requested),
            policy='all nine arms for each reserved design block; failures/unused calls remain charged; no retry/reclaim'))
    return str(ledger)


def configure_a02_allocator(device,stage):
    if stage!=A02_STAGE or device.type!='cuda':return None
    torch.cuda.set_per_process_memory_fraction(.25,device)
    return .25


def terminal_snapshot(path,frame,result,*,budget_root=None,max_bytes=None):
    arrays={k:np.asarray(result[k]) for k in
        ('H','x_soft','gains','support','sigma2','sigma2_terminal','mu','var','llr','decoded','info_hat','x_hard')}
    arrays.update({k:np.asarray(frame.observed[k]) for k in ('y','pilot','constellation')})
    arrays.update(sigma2_thermal=np.asarray(frame.observed['sigma2']),
                  info=np.asarray(frame._truth['info']),coded=np.asarray(frame._truth['coded']))
    if arrays['support'].size==0:arrays['support']=np.asarray([],dtype=np.int64)
    n=len(arrays['y'])
    shapes={'H':(n,n),'x_soft':(n,),'mu':(n,),'var':(n,),'x_hard':(n,),
            'llr':(2*n,),'decoded':(2*n,),'coded':(2*n,),'pilot':(n,),'constellation':(4,),
            'gains':arrays['support'].shape,'info_hat':arrays['info'].shape,
            'sigma2':(),'sigma2_terminal':(),'sigma2_thermal':()}
    if (arrays['support'].ndim!=1 or len(arrays['support'])>40 or
            arrays['support'].dtype.kind not in 'iu' or len(set(arrays['support'].tolist()))!=len(arrays['support']) or
            np.any(arrays['support']<0) or np.any(arrays['support']>=515) or
            any(arrays[k].shape!=shape for k,shape in shapes.items()) or
            any(a.dtype.hasobject or not np.isfinite(a).all() for a in arrays.values())):
        raise ValueError('invalid complete terminal replay state')
    if (any(np.iscomplexobj(arrays[k]) or np.any(arrays[k]<=0)
            for k in ('sigma2','sigma2_terminal','sigma2_thermal','var')) or
            arrays['info'].ndim!=1 or arrays['info'].size==0 or
            any(not np.isin(arrays[k],(0,1)).all() for k in ('info','coded','decoded','info_hat'))):
        raise ValueError('invalid replay variance or bit domain')
    raw_bytes=sum(a.nbytes for a in arrays.values())
    if raw_bytes>PER_TERMINAL_BYTES:raise ValueError('terminal exceeds frozen per-record storage estimate')
    if budget_root is not None and output_bytes(budget_root)+raw_bytes+65536>max_bytes:
        raise OSError('terminal creation would exceed frozen storage budget')
    fd,temporary=tempfile.mkstemp(prefix='.terminal-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            np.savez_compressed(stream,**arrays);stream.flush();os.fsync(stream.fileno())
        if budget_root is not None and output_bytes(budget_root)>max_bytes:
            raise OSError('terminal publication would exceed frozen storage budget')
        os.link(temporary,path)
    finally:os.unlink(temporary)
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,uncompressed_bytes=raw_bytes,
                sha256=sha(path),md5=hashlib.md5(path.read_bytes()).hexdigest(),
                fields=sorted(arrays),truth_access='info/coded for offline scoring only',
                transfer_policy='raw stays at output path; no automatic transfer')



def validate_frame_identity(frame,split,block,protocol_sha256):
    meta=frame.metadata
    if (meta.get('split')!=split or meta.get('block')!=block or
            meta.get('snr_db')!=8 or meta.get('protocol_sha256')!=protocol_sha256 or
            any(meta.get('input_hashes',{}).get(k)!=array_hash(frame.observed[k]) for k in ('y','pilot'))):
        raise ValueError('generated frame identity/input differs from batch contract')


def assert_batch_content_unchanged(args,contract):
    assert_content_unchanged(args,contract)
    if contract.get('stage')==A02_STAGE and sha(args.a02_protocol)!=contract['a02_protocol_sha256']:
        raise ValueError('A-02 protocol changed during batch')


def make_record(frame,result,recipe,contract,wall,cpu,peak):
    m=frame.metadata;hhash=array_hash(result['H'])
    schema=('supplement-engineering-frame-v1' if m['split']=='engineering' else
            'supplement-A02-development-frame-v1' if contract.get('stage')==A02_STAGE else
            'supplement-baseline-design-frame-v1')
    row=dict(schema=schema,
        campaign_id=CAMPAIGN_ID,metadata=m,recipe=recipe,config_sha256=contract['config_sha256'],
        source_sha256=contract['source_sha256'],checkpoint_sha256=contract['checkpoint_sha256'],
        code_sha256=contract['code_sha256'],input_hashes=m['input_hashes'],protocol_sha256=m['protocol_sha256'],
        split=m['split'],scenario='G0',block_id=m['block'],SNR=m['snr_db'],arm_id=recipe['id'],
        truth_access_level='none',offline_truth_access='evaluation_only',
        H_cancel_source={'stage':'final_estimate','sha256':hhash},
        H_data_source={'stage':'final_estimate','sha256':hhash},
        H_cov_source={'stage':'scalar_terminal_BP_no_explicit_C','H_sha256':hhash},
        sigma_source='receiver sigma2 * recipe terminal_scale',sigma_value=result['sigma2_terminal'],
        decoder_status={'syndrome_ok':bool(result['decode_ok']),'maxiter':50},call_type='full',
        elapsed_seconds=wall,process_cpu_seconds=cpu,peak_gpu_bytes=peak,
        receiver_seconds=result['seconds'],initial_estimator=result['initial_estimator'],
        baseline_eligible=bool(result['baseline_eligible']),baseline_stationary=result.get('baseline_stationary'),
        channel_refit=result.get('channel_refit',{}).get('diagnostics'),
        support=result['support'],capacity_trace=result['capacity_trace'],graphs=result['graphs'],
        failure=None,retry_of=None,timing_scope='development complete F; terminal BP/LDPC included, not separately charged T')
    if contract.get('stage')==A02_STAGE:
        row.update(development_stage=A02_STAGE,
                   deployment_eligible=result.get('deployment_eligible'))
    row.update(score_errors(result,frame._truth));row['offline_truth_access']='evaluation_only'
    row=json_value(row)
    if contract.get('stage')==A02_STAGE:
        role=recipe.get('a02_role');diagnostics=row['channel_refit']
        if (role!='Bstar' and (not isinstance(diagnostics,dict) or
                any(key not in diagnostics for key in ('converged','query_count','fallback')))):
            raise ValueError('A-02 terminal refit audit is incomplete')
        if (role=='reference' and (row['deployment_eligible'] is not False or
                type(row['baseline_stationary']) is not bool or
                diagnostics.get('query_limit')!=3243)):
            raise ValueError('A-02 reference deployment/stationarity/query audit is incomplete')
    if row['split']=='engineering':validate_engineering_record(row)
    elif (row['split']!='design' or not 0<=row['block_id']<192 or row['SNR']!=8 or
            row['block_id']!=m['block'] or row['sigma_value']<=0 or min(wall,cpu,peak)<0):
        raise ValueError('invalid design record identity/cost')
    json.dumps(row,allow_nan=False)
    return row


def execute(args):
    args.out.mkdir(parents=True,exist_ok=False)
    previous=signal.getsignal(signal.SIGALRM)
    attempted=completed=unqualified=0;failures=[];records=[];active=None;completed_identities=[]
    started,cpu0=time.perf_counter(),time.process_time()
    command=[sys.executable,*sys.argv]
    def publish(path,value):
        publish_bounded(path,value,args.out,args.max_output_bytes-FAILURE_RESERVE_BYTES)
    try:
        recipes,estimated=validate_args(args)
        if shutil.disk_usage(args.out).free<estimated:raise OSError('insufficient disk for frozen storage estimate')
        def timeout(_signal,_frame):raise TimeoutError('BASE batch deadline')
        signal.signal(signal.SIGALRM,timeout)
        signal.setitimer(signal.ITIMER_REAL,args.deadline_unix-time.time())
        torch.set_num_threads(1)
        device=torch.device(args.device)
        if device.type not in ('cpu','cuda') or (device.type=='cuda' and not torch.cuda.is_available()):
            raise ValueError('requested device unavailable')
        allocator_fraction=configure_a02_allocator(device,getattr(args,'stage',BASE_STAGE))
        if sha(args.checkpoint)!=CHECKPOINT_HASH:raise ValueError('checkpoint mismatch')
        (args.out/'code-cache').mkdir();code=build_code(cache_dir=args.out/'code-cache')
        data=SupplementData(args.protocol,code);system=_make_config_a(1024,2.,8,10.,4.)
        stage=getattr(args,'stage',BASE_STAGE)
        contract=dict(campaign_id=CAMPAIGN_ID,split=args.split,start=args.start,stop=args.stop,snr=8,
            recipes=recipes,device=str(device),max_full_calls=args.max_full_calls,
            calls_reserved=dict(F=args.max_full_calls,T=0,E=0),prior_sha256=None,
            source_sha256=sources(),checkpoint_sha256=sha(args.checkpoint),protocol_sha256=sha(args.protocol),
            code_sha256={k:array_hash(code[k]) for k in ('G','H')},
            deadline_unix=args.deadline_unix,max_output_bytes=args.max_output_bytes,
            estimated_output_bytes=estimated,per_terminal_estimate_bytes=PER_TERMINAL_BYTES,
            command=command,versions=dict(numpy=np.__version__,torch=torch.__version__,python=sys.version),
            threads=torch.get_num_threads(),affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
            policy='no resume/retry/seed replacement; independent arm failures retained; terminal work included in F')
        if stage==A02_STAGE:
            contract.update(a02_protocol_sha256=args.a02_protocol_sha256,
                            a02_protocol_path=str(args.a02_protocol.resolve()),
                            gpu_allocator_fraction=allocator_fraction,
                            gpu_allocator_scope='PyTorch allocator cap; external CUDA allocations not included')
        if stage==A02_STAGE:contract['stage']=A02_STAGE
        contract['config_sha256']=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
        contract['ledger']=(reserve_a02 if stage==A02_STAGE else
                            reserve_profile if args.split=='engineering' else reserve_design)(args.out,contract)
        publish(args.out/'contract.json',contract)
        model=build_receiver(args.checkpoint,system,1024,args.device,receiver_shell='direct40',active_cap=40)
        def failure(exc,identity):
            item=dict(status='failed',identity=identity,exception=type(exc).__name__,message=str(exc),
                traceback=traceback.format_exc(),config_sha256=contract['config_sha256'],FER=None,
                wall_seconds=(time.time()-identity['started_unix']) if 'started_unix' in identity else None,
                CPU_seconds=(time.process_time()-identity['started_CPU_seconds']) if 'started_CPU_seconds' in identity else None)
            path=args.out/f'failure-{len(failures):05d}.json';publish(path,item)
            failures.append(dict(path=str(path),sha256=sha(path),identity=identity))
        for block in range(args.start,args.stop):
            assert_batch_content_unchanged(args,contract)
            active=dict(stage='generation',block=block,split=args.split,scenario='G0',snr=8)
            publish(args.out/f'generation-{block:03d}-started.json',active)
            try:frame=data.make_frame(system,args.split,block,8)
            except (TimeoutError,KeyboardInterrupt):raise
            except Exception as exc:
                for recipe in recipes:failure(exc,dict(active,arm_id=recipe['id'],full_call_started=False))
                continue
            assert_batch_content_unchanged(args,contract)
            validate_frame_identity(frame,args.split,block,contract['protocol_sha256'])
            order=list(recipes);campaign_rng(args.split,block,'order').shuffle(order)
            for recipe in order:
                assert_batch_content_unchanged(args,contract)
                if attempted>=args.max_full_calls or time.time()>=args.deadline_unix:
                    raise TimeoutError('BASE budget/deadline exhausted')
                if output_bytes(args.out)+PER_TERMINAL_BYTES+65536>args.max_output_bytes-FAILURE_RESERVE_BYTES:
                    raise OSError('insufficient remaining output budget before full call')
                attempted+=1
                active=dict(stage='full_receiver',attempt=attempted,block=block,split=args.split,
                    arm_id=recipe['id'],input_hashes=frame.metadata['input_hashes'],full_call_started=True,
                    started_unix=time.time(),started_CPU_seconds=time.process_time())
                publish(args.out/f'call-{attempted:05d}-started.json',active)
                result=None
                try:
                    receiver=BaselineReceiver(model,code,recipe['id'],system=system)
                    if device.type=='cuda':torch.cuda.synchronize(device);torch.cuda.reset_peak_memory_stats(device)
                    w,c=time.perf_counter(),time.process_time()
                    result=receiver.run(frame.observed,audit=True)
                    if device.type=='cuda':torch.cuda.synchronize(device)
                    wall,cpu=time.perf_counter()-w,time.process_time()-c
                    peak=int(torch.cuda.max_memory_allocated(device)) if device.type=='cuda' else 0
                    row=make_record(frame,result,recipe,contract,wall,cpu,peak)
                    row['terminal']=terminal_snapshot(args.out/f'terminal-{block:03d}-{recipe["id"]}.npz',frame,result,
                        budget_root=args.out,max_bytes=args.max_output_bytes-FAILURE_RESERVE_BYTES)
                except (TimeoutError,KeyboardInterrupt):raise
                except Exception as exc:
                    failure(exc,active)
                    result=None
                    assert_batch_content_unchanged(args,contract)
                    continue
                assert_batch_content_unchanged(args,contract)
                path=args.out/f'frame-{block:03d}-{recipe["id"]}.json';publish(path,row)
                records.append(dict(path=str(path),sha256=sha(path)));completed+=1
                completed_identities.append((block,recipe['id']))
                unqualified+=int(not row['baseline_eligible']);active=None;result=None
                used=sum(p.stat().st_size for p in args.out.rglob('*') if p.is_file())
                if used>args.max_output_bytes:raise OSError('actual output exceeded frozen storage budget')
        assert_batch_content_unchanged(args,contract);signal.setitimer(signal.ITIMER_REAL,0)
        status='completed_with_failures' if failures else 'complete';exitcode=1 if failures else 0
        publish(args.out/'summary.json',dict(status=status,exitcode=exitcode,calls_attempted=attempted,
            calls_completed=completed,unqualified_completed_records=unqualified,
            records=records,failures=failures,command=command,
            missing_or_failed_identities=[dict(block=b,arm_id=r['id'],split=args.split)
                for b in range(args.start,args.stop) for r in recipes
                if (b,r['id']) not in set(completed_identities)],
            reservation_ledger=contract['ledger'],
            replay_policy='No resume implemented. Reconcile these identities and original contract/reservation under an explicit new budget/retry lineage before same-seed rerun.',
            config_sha256=contract['config_sha256'],wall_seconds=time.perf_counter()-started,
            CPU_seconds=time.process_time()-cpu0,
            scope=('A-02 development; no confirmation/COST-02/scientific success claim'
                   if stage==A02_STAGE else 'BASE development; no confirmation or scientific success claim')))
        return exitcode
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        publish_bounded(args.out/'batch-failure.json',dict(status='failed',exitcode=130 if isinstance(exc,KeyboardInterrupt) else 1,
            exception=type(exc).__name__,message=str(exc)[:16384],traceback=traceback.format_exc()[-32768:],
            exception_text_may_be_truncated=True,
            calls_attempted=attempted,calls_completed=completed,active_attempt=active,
            recorded_failure_count=len(failures),completed_record_count=len(records),
            identity_recovery='Read contract.json range/recipes minus frame-*.json; failure-*.json and call/generation-started files preserve original identities. No resume implemented; new budget/retry lineage required.',
            contract_path=str(args.out/'contract.json'),command=command),args.out,args.max_output_bytes)
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','checkpoint','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--split',choices=tuple(LIMITS),required=True)
    p.add_argument('--stage',choices=(BASE_STAGE,A02_STAGE),default=BASE_STAGE)
    p.add_argument('--a02-protocol',type=Path);p.add_argument('--a02-protocol-sha256')
    for name in ('start','stop','max-full-calls','max-output-bytes'):p.add_argument('--'+name,type=int,required=True)
    p.add_argument('--snr',type=float,required=True);p.add_argument('--deadline-unix',type=float,required=True)
    p.add_argument('--recipes',help='BASE-only JSON list; A-02 recipes come from --a02-protocol')
    p.add_argument('--device',required=True)
    return execute(p.parse_args())


if __name__=='__main__':sys.exit(main())
