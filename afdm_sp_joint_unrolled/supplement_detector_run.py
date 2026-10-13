"""Bounded engineering detector replay from explicitly mapped BASE caches only."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
import traceback
import tempfile
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key]='1'
import numpy as np
import torch
from .supplement_detectors import catalogue,terminal,qualification_pair,CONST
from .supplement_profile import reserve_profile
from .supplement_detector_development import validate_development, reserve_development, offline_score, validate_loaded_development
from .supplement_run import sources,sha,json_value
from .supplement_baseline_select import config_hash,read_json
from .budgeted_support_diagnostics import array_hash
from .budgeted_frame_store import publish_json
from .e1_ldpc import build_code
from .supplement_data import CAMPAIGN_ID
from . import supplement_detector_extension as extension

QUOTE_IDS=['stable-EP-40-d0.5','QPSK-MF-40-d1']
PER_CALL_BYTES=2*1024*1024
FAILURE_RESERVE=128*1024


def mapped_path(spec,path):
    original=Path(spec['original_root']);local=Path(spec['local_root']).resolve()
    path=Path(path)
    if not original.is_absolute() or not path.is_absolute():raise ValueError('explicit absolute original paths required')
    relative=path.relative_to(original)
    result=(local/relative).resolve()
    if not result.is_relative_to(local):raise ValueError('cache mapping escapes explicit root')
    return result


def load_cache(spec, *, split='engineering', baseline=None):
    if split not in ('engineering','design') or (split=='design' and not baseline):
        raise ValueError('explicit development split and frozen baseline required')
    limit=32 if split=='engineering' else 192
    schema='supplement-engineering-frame-v1' if split=='engineering' else 'supplement-baseline-design-frame-v1'
    root=Path(spec['local_root']).resolve()
    contract,csha=read_json(root/'contract.json');summary,ssha=read_json(root/'summary.json')
    digest=config_hash(contract)
    if (contract.get('config_sha256')!=digest or summary.get('config_sha256')!=digest or
            summary.get('status')!='complete' or summary.get('exitcode')!=0 or summary.get('failures') or
            contract.get('campaign_id')!=CAMPAIGN_ID or contract.get('split')!=split or contract.get('snr')!=8):
        raise ValueError('cache needs complete bound requested BASE split')
    expected=(contract['stop']-contract['start'])*len(contract['recipes'])
    if (not 0<=contract['start']<contract['stop']<=limit or summary.get('missing_or_failed_identities') or
            summary.get('calls_attempted')!=expected or summary.get('calls_completed')!=expected or
            len(summary['records'])!=expected or len({v['path'] for v in summary['records']})!=expected or
            (root/'batch-failure.json').exists() or list(root.glob('failure-*.json'))):
        raise ValueError('cache summary does not certify complete batch identities')
    path=mapped_path(spec,spec['record'])
    matches=[v for v in summary['records'] if mapped_path(spec,v['path'])==path]
    if len(matches)!=1:raise ValueError('cache record not uniquely committed by summary')
    row,rsha=read_json(path,matches[0]['sha256'])
    if (row.get('schema')!=schema or row.get('config_sha256')!=digest or
            row.get('split')!=split or row.get('SNR')!=8 or not 0<=row['block_id']<limit or
            row.get('failure') is not None or row.get('truth_access_level')!='none' or
            row['recipe'] not in contract['recipes'] or row['arm_id']!=row['recipe']['id']):
        raise ValueError('invalid cache identity')
    if baseline is not None and row['arm_id']!=baseline:
        raise ValueError('cache differs from frozen development baseline')
    meta=row.get('metadata',{})
    if (row.get('campaign_id')!=CAMPAIGN_ID or row.get('scenario')!='G0' or
            not contract['start']<=row['block_id']<contract['stop'] or
            meta.get('split')!=split or meta.get('block')!=row['block_id'] or
            meta.get('snr_db')!=8 or meta.get('protocol_sha256')!=contract['protocol_sha256'] or
            meta.get('input_hashes')!=row['input_hashes']):
        raise ValueError('cache metadata identity mismatch')
    for key in ('source_sha256','protocol_sha256','checkpoint_sha256','code_sha256'):
        if row[key]!=contract[key]:raise ValueError('cache lineage differs from contract')
    rawpath=mapped_path(spec,row['terminal']['path'])
    if rawpath.stat().st_size!=row['terminal']['bytes'] or sha(rawpath)!=row['terminal']['sha256']:
        raise ValueError('cache terminal content mismatch')
    # Deliberately access only observed receiver arrays; never truth H/info/coded.
    with np.load(rawpath,allow_pickle=False) as raw:
        data={k:raw[k].copy() for k in ('y','H','pilot','sigma2_terminal','constellation')}
    if (data['y'].shape!=(1024,) or data['H'].shape!=(1024,1024) or data['pilot'].shape!=(1024,) or
            data['sigma2_terminal'].shape!=() or data['constellation'].shape!=(4,) or
            any(not np.isfinite(a).all() for a in data.values()) or
            any(not np.iscomplexobj(data[k]) for k in ('y','H','pilot','constellation')) or
            np.iscomplexobj(data['sigma2_terminal']) or float(data['sigma2_terminal'])<=0 or
            not np.allclose(data['constellation'],CONST,rtol=1e-12,atol=1e-12)):
        raise ValueError('invalid cached observed dimensions/variance')
    h= array_hash(data['H'])
    if (row['H_cancel_source']['sha256']!=h or row['H_data_source']['sha256']!=h or
            row['sigma_value']!=float(data['sigma2_terminal']) or
            any(array_hash(data[k])!=row['input_hashes'][k] for k in ('y','pilot'))):
        raise ValueError('cached channel/cancellation/sigma/input mismatch')
    data['y_cancelled']=data['y']-data['H']@data['pilot']
    proof=dict(spec=spec,split=split,terminal_path=str(rawpath),truth_hashes={k:row['input_hashes'][k] for k in ('info','coded') if k in row['input_hashes']},block=row['block_id'],baseline=row['arm_id'],code_sha256=row['code_sha256'],
        config_sha256=digest,files={str(root/'contract.json'):csha,str(root/'summary.json'):ssha,
            str(path):rsha,str(rawpath):row['terminal']['sha256']},
        input_hashes={k:array_hash(v) for k,v in data.items()},truth_access='none')
    return data,proof


def validate_request(args,caches,ids):
    if (not isinstance(caches,list) or not caches or len(caches)>(16 if args.stage=='development' else 4) or
            not isinstance(ids,list) or not ids or len(set(ids))!=len(ids) or
            any(i not in [r['id'] for r in catalogue()] for i in ids)):
        raise ValueError('explicit at most4 caches and registered detector IDs required')
    if not math.isfinite(args.deadline_unix) or args.deadline_unix<=time.time():raise ValueError('finite future deadline required')
    if args.device!='cuda':raise ValueError('this engineering quotation requires actual CUDA')
    if args.stage=='quote':
        if len(caches)!=1 or ids!=QUOTE_IDS:raise ValueError('first quote is one block0 B0-p3-s1 cache and exactly2 detectors')
        if args.admission is not None:raise ValueError('quote does not consume qualification admission')
        calls=2
    elif args.stage=='qualification':
        if args.admission is None:raise ValueError('separate explicit qualification admission required')
        admission,_=read_json(args.admission)
        if (admission.get('stage')!='qualification' or admission.get('campaign_id')!=CAMPAIGN_ID or
                admission.get('caches')!=caches or admission.get('detectors')!=ids):raise ValueError('admission not bound to this request')
        quote=admission['completed_quote'];value,_=read_json(quote['path'],quote['sha256'])
        qcontract,_=read_json(Path(quote['path']).parent/'contract.json')
        qhash=config_hash(qcontract)
        if (value.get('stage')!='quote' or value.get('status')!='complete' or value.get('exitcode')!=0 or
                value.get('calls_attempted')!=2 or value.get('failures') or len(value.get('records',[]))!=2 or
                qcontract.get('config_sha256')!=qhash or value.get('config_sha256')!=qhash or
                qcontract.get('stage')!='quote' or qcontract.get('campaign_id')!=CAMPAIGN_ID or
                qcontract.get('detectors')!=QUOTE_IDS or qcontract.get('calls_reserved')!={'F':0,'T':2,'E':0} or
                {r['identity']['detector'] for r in value['records']}!=set(QUOTE_IDS)):
            raise ValueError('successful bound2T quote must precede qualification')
        calls=len(caches)*len(ids)*2
    elif args.stage=='development':
        validate_development(args,caches,ids)
        calls=len(caches)*len(ids)
    else:raise ValueError('unknown detector replay stage')
    if type(args.max_terminal_calls) is not int or args.max_terminal_calls!=calls or calls>(128 if args.stage=='development' else 64):
        raise ValueError('exact finite T reservation required, at most64')
    if type(args.max_output_bytes) is not int or args.max_output_bytes<16*1024*1024+calls*PER_CALL_BYTES:raise ValueError('insufficient preregistered output budget')
    return calls



def qualification_summary(stability,ids,cache_count):
    expected={(cache,identifier) for cache in range(cache_count) for identifier in ids}
    actual={(s['cache'],s['detector']) for s in stability}
    if actual!=expected or len(stability)!=len(expected):
        raise ValueError('qualification summary lacks exact cache/detector coverage')
    qualified={identifier:all(s['result'] is not None and s['result']['stable']
        for s in stability if s['detector']==identifier) for identifier in ids}
    return qualified,any(qualified.values())


def unchanged(contract):
    if sources()!=contract['source_sha256']:raise ValueError('source changed during replay')
    if contract.get('admission_path') and sha(contract['admission_path'])!=contract['admission_sha256']:
        raise ValueError('admission changed during replay')
    for proof in contract['caches']:
        for path,digest in proof['files'].items():
            if sha(path)!=digest:raise ValueError('cache changed during replay')


def execute(args):
    if args.stage in extension.STAGES:
        caches=json.loads(args.caches);ids=json.loads(args.detectors)
        context=extension.prepare(args,caches,ids,sources())
        with extension.execution_lock(context['allocation']):
            return _execute(args,context)
    return _execute(args)


def _execute(args, additional=None):
    caches=json.loads(args.caches);ids=json.loads(args.detectors)
    calls=args.max_terminal_calls if additional else validate_request(args,caches,ids)
    allocation=additional['allocation'] if additional else None
    storage_root=Path(allocation['run_root']) if allocation else args.out
    per_call_bytes=64*1024*1024 if additional else PER_CALL_BYTES
    is_qualification=args.stage in ('qualification',extension.STAGES[0])
    args.out.mkdir(parents=True,exist_ok=False)
    active=None;records=[];failures=[];attempted=0
    previous_handler=signal.getsignal(signal.SIGALRM)
    def publish(name,value,emergency=False):
        value=json_value(value)
        used=extension.output_bytes(storage_root)
        if used+len(json.dumps(value).encode())>args.max_output_bytes-(0 if emergency else FAILURE_RESERVE):raise OSError('output storage cap exceeded')
        publish_json(args.out/name,value)
    def timeout(*_):raise TimeoutError('finite detector replay deadline reached')
    signal.signal(signal.SIGALRM,timeout)
    signal.setitimer(signal.ITIMER_REAL,max(.001,args.deadline_unix-time.time()))
    try:
        torch.set_num_threads(1)
        if torch.get_num_interop_threads()!=1:torch.set_num_interop_threads(1)
        if not torch.cuda.is_available():raise ValueError('CUDA unavailable; no CPU fallback')
        device=torch.device('cuda',torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(.25,device)
        development=(additional['development'] if additional else
                     validate_development(args,caches,ids) if args.stage=='development' else None)
        loaded=[]
        for spec in caches:
            active=dict(stage='cache_validation',spec=spec)
            loaded.append(load_cache(spec,split='design',baseline=development['baseline']) if development else load_cache(spec))
        active=None;proofs=[v[1] for v in loaded]
        keys=[(p['config_sha256'],p['block'],p['baseline']) for p in proofs]
        if len(set(keys))!=len(keys):raise ValueError('duplicate cache identity')
        if additional and is_qualification and (
                [p['block'] for p in proofs]!=list(range(4)) or
                any(p['baseline']!='B0-p3-s1' or p['split']!='engineering' for p in proofs)):
            raise ValueError('additional qualification must replay original engineering blocks0..3')
        if development:
            validate_loaded_development(proofs,development)
            proofs[0]['files'].update({v['path']:v['sha256'] for v in (development['selection'],development['qualification'])})
        if args.stage=='quote' and (proofs[0]['block']!=0 or proofs[0]['baseline']!='B0-p3-s1'):
            raise ValueError('first quote cache is engineering block0 B0-p3-s1')
        (args.out/'code-cache').mkdir();code=build_code(cache_dir=args.out/'code-cache')
        ch={k:array_hash(code[k]) for k in ('G','H')}
        if any(p['code_sha256']!=ch for p in proofs):raise ValueError('LDPC code differs from cached receiver')
        contract=dict(schema='supplement-detector-run-v1',campaign_id=CAMPAIGN_ID,stage=args.stage,
            caches=proofs,detectors=ids,device=str(device),threads=1,gpu_memory_fraction=.25,
            calls_reserved=dict(F=0,T=calls,E=0),max_full_calls=0,source_sha256=sources(),
            max_output_bytes=args.max_output_bytes,deadline_unix=args.deadline_unix,
            command=[sys.executable,*sys.argv],admission_path=str(args.admission) if args.admission else None,admission_sha256=sha(args.admission) if args.admission else None)
        if additional:
            contract.update(allocation_path=allocation['_path'],allocation_sha256=allocation['_sha256'],
                            storage_root=str(storage_root),per_call_bytes=per_call_bytes)
        contract['config_sha256']=config_hash(contract)
        source_digest=hashlib.sha256(json.dumps(contract['source_sha256'],sort_keys=True).encode()).hexdigest()
        contract['ledger']=(extension.reserve(additional['admission']['ledger_path'],args.out,allocation,
            args.stage,[p['block'] for p in proofs],source_digest) if additional else
            reserve_development(args.out,start=development['start'],stop=development['stop'],
            baseline=development['baseline'],selection_sha256=development['selection']['sha256'],
            source_sha256=source_digest)
            if development else reserve_profile(args.out,contract))
        def verify_unchanged():
            unchanged(contract)
            if additional:
                extension.unchanged(allocation,sources())
                if sha(contract['ledger']['path'])!=contract['ledger']['sha256']:
                    raise ValueError('additional reservation changed during replay')
        publish('contract.json',contract)
        pairs={}
        for index,(data,proof) in enumerate(loaded):
            for identifier in ids:
                for doubled in ([False,True] if is_qualification else [False]):
                    verify_unchanged()
                    if time.time()>=args.deadline_unix:raise TimeoutError('deadline before terminal call')
                    used=extension.output_bytes(storage_root)
                    if used+per_call_bytes+65536>args.max_output_bytes-FAILURE_RESERVE:raise OSError('storage insufficient before T')
                    attempted+=1
                    cache_id=proof['block'] if additional else index
                    active=dict(attempt=attempted,cache=cache_id,detector=identifier,doubled=doubled,
                        call_type='T',truth_access='none',config_sha256=contract['config_sha256'])
                    if additional:
                        active['block']=proof['block']
                        active['batch_index']=index
                        reserved=contract['ledger'].get('identities')
                        if reserved is None:
                            reserved,_=read_json(contract['ledger']['path'],contract['ledger']['sha256'])
                            reserved=reserved['identities']
                            contract['ledger']['identities']=reserved
                        if [args.stage,proof['block'],identifier,doubled] not in reserved:
                            raise ValueError('record identity not in additional reservation')
                    publish(f'call-{attempted:03d}-started.json',active)
                    try:
                        torch.cuda.synchronize(device);torch.cuda.reset_peak_memory_stats(device)
                        started=time.perf_counter()
                        result=terminal(data['y_cancelled'],data['H'],float(data['sigma2_terminal']),
                            data['constellation'],code,identifier,device=device,doubled=doubled)
                        torch.cuda.synchronize(device);elapsed=time.perf_counter()-started
                        verify_unchanged()
                        arrays={k:result[k] for k in ('mu','var','raw_llr','llr','x_hard','decoded','info_hat')}
                        if additional:
                            arrays.update({'bp_message_'+k:v for k,v in result['bp_message_state'].items()})
                        path=args.out/f'terminal-{attempted:03d}.npz'
                        fd,temporary=tempfile.mkstemp(prefix='.terminal-',dir=args.out)
                        try:
                            with os.fdopen(fd,'wb') as stream:
                                np.savez_compressed(stream,**arrays);stream.flush();os.fsync(stream.fileno())
                            if Path(temporary).stat().st_size>per_call_bytes:raise OSError('terminal exceeds per-call storage reservation')
                            os.link(temporary,path)
                        finally:
                            Path(temporary).unlink(missing_ok=True)
                        record=dict(identity=active,diagnostics=result['diagnostics'],seconds=elapsed,
                            CPU_seconds=result['terminal_CPU_seconds'],peak_gpu_bytes=torch.cuda.max_memory_allocated(device),
                            decode_ok=result['decode_ok'],terminal=dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path)),
                            truth_access='none',error_counts=offline_score(result,proof) if development else None,
                            engineering_qualified=development['qualified_by_detector'][identifier] if development else None)
                        publish(f'call-{attempted:03d}.json',record);records.append(record)
                        if is_qualification:pairs[index,identifier,doubled]=result
                    except (TimeoutError,KeyboardInterrupt):raise
                    except Exception as exc:
                        failure=dict(identity=active,exception=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
                        publish(f'failure-{attempted:03d}.json',failure);failures.append(failure)
                        verify_unchanged()
                    active=None
        stability=[]
        if is_qualification:
            for index in range(len(loaded)):
                for identifier in ids:
                    pair=[pairs.get((index,identifier,d)) for d in (False,True)]
                    stability.append(dict(cache=proofs[index]['block'] if additional else index,detector=identifier,result=qualification_pair(*pair) if all(v is not None for v in pair) else None))
        verify_unchanged();signal.setitimer(signal.ITIMER_REAL,0)
        qualified,passed=qualification_summary(stability,ids,len(loaded)) if is_qualification else ({},None)
        status=('completed_with_failures' if failures else
                'completed_unqualified' if passed is False else 'complete')
        exitcode=int(bool(failures) or passed is False)
        publish('summary.json',dict(stage=args.stage,status=status,
            exitcode=exitcode,calls_attempted=attempted,records=records,failures=failures,
            stability=stability,qualified_by_detector=qualified,qualification_passed=passed,
            resource_projection=extension.qualification_resources(records,allocation) if additional and is_qualification and not failures else None,
            config_sha256=contract['config_sha256'],scope='development comparison; unqualified references cannot exclude detector space' if development else 'engineering only; stability is not exact posterior correctness'))
        return exitcode
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        publish('batch-failure.json',dict(status='failed',exitcode=1,identity=active,
            calls_attempted=attempted,exception=type(exc).__name__,message=str(exc)[:8192],
            traceback=traceback.format_exc()[-32768:],exception_text_may_be_truncated=True),emergency=True)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous_handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--caches',required=True,help='JSON array: original_root,local_root,record absolute path')
    parser.add_argument('--detectors',required=True);parser.add_argument('--stage',choices=['quote','qualification','development',*extension.STAGES],required=True)
    parser.add_argument('--allocation',type=Path);parser.add_argument('--allocation-sha256')
    parser.add_argument('--admission',type=Path);parser.add_argument('--device',required=True)
    parser.add_argument('--max-terminal-calls',type=int,required=True);parser.add_argument('--deadline-unix',type=float,required=True)
    parser.add_argument('--max-output-bytes',type=int,required=True);parser.add_argument('--out',type=Path,required=True)
    return execute(parser.parse_args())


if __name__=='__main__':raise SystemExit(main())
