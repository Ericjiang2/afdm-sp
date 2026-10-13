"""Raw audits and prospective paired analyses for the bounded adjacent study."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import time

for _name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_name]='1'

import numpy as np

from supplement_adjacent_evidence import file_sha, load_raw, validate_errors, validate_input
from supplement_adjacent_inference import paired_fer, confirmation_decisions
from supplement_adjacent_pool import POOLS, ROLES, candidate_signature, codeword_score
from afdm_sp_joint_unrolled.afdm_env import AFDMEnvMixin
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.direction_physical_receiver import PhysicalChannelRefit
from afdm_sp_joint_unrolled.e1_ldpc import encode
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.supplement_scope import validate_history
from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles


def read(path):
    return json.loads(Path(path).read_text())


def completed_run(batch, expected_F):
    if (batch/'failure.json').exists() or Path(str(batch)+'.exit').read_text().strip()!='0':
        raise ValueError('failed or running collection cannot be audited as complete')
    run, closure = read(batch/'run.json'), read(batch/'complete.json')
    stat = Path('/proc')/str(run['pid'])/'stat'
    if stat.exists() and int(stat.read_text().rsplit(')',1)[1].split()[19])==run['start_ticks']:
        raise ValueError('collection process has not exited')
    if (closure['attempted_F']!=expected_F or closure['completed_F']!=expected_F
            or closure['finished_at_unix']>run['deadline_unix']):
        raise ValueError('collection count or deadline differs')
    return run, closure


def freeze_tree(batch, lock_path):
    """Hash every completed output before inspecting outcome values or an oracle."""
    rows=[]
    for path in sorted(batch.rglob('*')):
        if path.is_symlink():
            raise ValueError('output lock cannot follow symlinks')
        if not path.is_file():
            continue
        digest, md5 = hashlib.sha256(),hashlib.md5()
        with path.open('rb') as handle:
            for data in iter(lambda:handle.read(1024*1024),b''):
                digest.update(data);md5.update(data)
        rows.append(dict(path=str(path),bytes=path.stat().st_size,sha256=digest.hexdigest(),md5=md5.hexdigest()))
    lock=dict(schema='adjacent-completed-output-lock-v1',root=str(batch),files=rows,
        frozen_at_unix=time.time(),bytes=sum(r['bytes'] for r in rows),
        policy='content frozen before outcome analysis; source outputs never edited')
    publish_json(lock_path,lock)
    return BoundFiles({r['path']:r['sha256'] for r in rows}),lock


def load_code(batch, expected=None):
    files=list((batch/'code-cache').glob('e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'))
    if len(files)!=1:
        raise ValueError('completed receiver LDPC cache missing')
    with np.load(files[0],allow_pickle=False) as data:
        code={key:data[key].copy() for key in data.files}
    code.update(n=int(code['H'].shape[1]),k=int(code['G'].shape[1]))
    hashes={key:array_hash(code[key]) for key in ('G','H')}
    if expected is not None and hashes!=expected:
        raise ValueError('receiver LDPC arrays changed')
    return code,hashes


def finish(out, report, index, guard):
    guard.verify()
    report.update(raw_files=len(index),raw_arrays=sum(len(x['arrays']) for x in index),
        status='raw_integrity_passed',finished_at_unix=time.time())
    publish_json(out/'audit.json',report)
    with gzip.open(out/'array-index.json.gz','xt') as handle:
        json.dump(index,handle,separators=(',',':'),allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k not in ('records','comparisons','cells','columns')},indent=2),flush=True)


def audit_pool(root,out,manifest_path):
    started=time.time()
    batch=root/'development-b-gpu'
    run,closure=completed_run(batch,1280)
    if file_sha(manifest_path)!=run['manifest_sha256']:
        raise ValueError('B admission manifest changed')
    manifest=read(manifest_path)
    validate_history(manifest)
    dependencies=BoundFiles(manifest['bound_files'])
    out.mkdir(exist_ok=False)
    guard,lock=freeze_tree(batch,out/'output-lock.json')
    code,code_hashes=load_code(batch,run['code_hashes'])
    geometry=PhysicalChannelRefit(_make_config_a(1024,2.,8,10.,4.),'m-param-budget').geometry
    development_audit=read(manifest['development_audit']['path'])
    previous={(r['block'],r['snr_db']):r for r in development_audit['records']}
    expected_cells={f'b{b:06d}-s{s}' for b in range(192,320) for s in (7,8)}
    if {p.name for p in batch.glob('b*-s*')}!=expected_cells:
        raise ValueError('B cell inventory differs')
    index,records,cross_snr=[],[],{}
    query_total=0
    for block in range(192,320):
        for snr in (7,8):
            cell=batch/f'b{block:06d}-s{snr}'
            link=read(cell/'input-link.json')
            source=Path(link['source'])
            if file_sha(source)!=manifest['development_input_hashes'][f'{block}/{snr}'] or file_sha(source)!=link['sha256']:
                raise ValueError('shared B input hash changed')
            meta=read(source)
            inputs=load_raw(meta['raw'],root,index)
            exogenous=validate_input(inputs,meta['frame'])
            if block in cross_snr and cross_snr[block]!=exogenous:
                raise ValueError('B cross-SNR exogenous pairing differs')
            cross_snr[block]=exogenous
            original=source.parent/'I1-r0.json'
            if file_sha(original)!=previous[block,snr]['result_meta_sha256']:
                raise ValueError('reused I1 result metadata differs from audited snapshot')
            i1meta=read(original)
            i1=load_raw(i1meta['raw'],root,index)['result']
            result_rows={'I1':dict(**validate_errors(i1,inputs['truth'],i1meta['scores']),
                seconds=i1meta['seconds'],decode_ok=bool(i1['decode_ok']))}
            pool_meta=read(cell/'pool.json')
            pool=load_raw(pool_meta['raw'],root,index)
            trace=pool['query_trace']
            if (len(trace)>125 or any(r['status']!='complete' for r in trace)
                    or [r['query'] for r in trace]!=list(range(1,len(trace)+1))
                    or pool['observed_hashes']!={k:array_hash(np.asarray(v)) for k,v in inputs['observed'].items()}
                    or pool_meta['local_physical_LS_queries']!=len(trace)):
                raise ValueError('nomination query accounting or observed identity differs')
            counts={role:sum(r['stage']==role for r in trace) for role in ROLES}
            if counts!=pool['query_counts'] or any(n>25 for n in counts.values()):
                raise ValueError('nomination branch query count differs')
            query_total+=len(trace)
            for roles in POOLS.values():
                if sum(counts[r] for r in roles)>75:
                    raise ValueError('strategy exceeds frozen query budget')
            for role in ROLES:
                candidate=pool['candidates'][role]
                signature=candidate_signature(candidate['delays'],candidate['locations'],candidate['weights'])
                row=read(cell/(role+'.json'))
                if (row['identity']!=dict(block=block,snr_db=snr,arm=role,repeat=0)
                        or row['input_hashes']!=meta['frame']['input_hashes']
                        or row['rng_before']!=row['rng_after']
                        or row['candidate_signature']!=signature or candidate['signature']!=signature):
                    raise ValueError('candidate identity or immutable pairing changed')
                values=load_raw(row['raw'],root,index)
                result=values['result']
                errors=validate_errors(result,inputs['truth'],row['scores'])
                if result['source_sha256']!=manifest['source_manifest']:
                    raise ValueError('candidate receiver source changed')
                ids=np.asarray(result['support'],dtype=int)
                diagnostics=result['channel_refit']['diagnostics']
                weights=candidate['weights'][ids]
                if (not np.array_equal(weights,diagnostics['weights_on_active_support'])
                        or not np.array_equal(ids,diagnostics['active_support'])
                        or not np.allclose(weights@diagnostics['fitted_latent'],result['gains'],rtol=1e-11,atol=1e-12)):
                    raise ValueError('fixed geometry and committed gains are inconsistent')
                rebuilt=AFDMEnvMixin.gen_h_daft(geometry,result['gains'],ids//5,ids%5-2)
                if not np.allclose(rebuilt,result['H'],rtol=1e-11,atol=1e-12):
                    raise ValueError('terminal H differs from committed support and gains')
                scored=codeword_score(inputs['observed'],result['H'],result['info_hat'],code)
                stored=values['codeword_score']
                if (scored['nll']!=row['codeword_nll'] or scored['nll']!=stored['nll']
                        or not np.array_equal(scored['codeword'],stored['codeword'])
                        or not np.array_equal(scored['symbols'],stored['symbols'])
                        or scored['observed_residual_sha256']!=stored['observed_residual_sha256']):
                    raise ValueError('single-use legal-codeword score cannot be reproduced')
                result_rows[role]=dict(**errors,seconds=row['seconds'],scoring_seconds=row['scoring_seconds'],
                    nll=scored['nll'],decode_ok=bool(result['decode_ok']),
                    refit_rank=diagnostics['rank'],latent_slots=diagnostics['latent_slots'],zero_slots=diagnostics['zero_slots'])
            selection=read(cell/'selection.json')
            for name,roles in POOLS.items():
                chosen=min(roles,key=lambda role:result_rows[role]['nll'])
                online=pool['strategy_nomination_seconds'][name]+sum(
                    result_rows[role]['seconds']+result_rows[role]['scoring_seconds'] for role in roles)
                if selection['selections'][name]['role']!=chosen or not np.isclose(
                        selection['selections'][name]['total_online_seconds'],online,rtol=1e-14):
                    raise ValueError('deployed whole-model selection changed')
                result_rows[name]=dict(result_rows[chosen],selected_role=chosen,total_online_seconds=online)
            # This is deliberately after the immutable output lock, never a deployed selector.
            oracle=min(POOLS['proposed'],key=lambda role:result_rows[role]['bit_errors'])
            result_rows['oracle']=dict(result_rows[oracle],selected_role=oracle,deployable=False)
            records.append(dict(block=block,snr_db=snr,partition='fit' if block<256 else 'heldout',
                results=result_rows,distinct_hypotheses=pool['distinct_hypotheses'],query_counts=counts,
                nomination_seconds=pool['strategy_nomination_seconds'],pool_meta_sha256=file_sha(cell/'pool.json')))
        if (block-191)%32==0:
            print(json.dumps(dict(event='B_audit_progress',cells=len(records),seconds=time.time()-started)),flush=True)
    if query_total!=closure['local_physical_LS_queries']:
        raise ValueError('total nomination query count differs from closure')
    contrasts=[('hard','I1'),('proposed','I1'),('multistart','I1'),('oracle','I1'),('proposed','multistart'),('oracle','proposed')]
    comparisons=[]
    tables={}
    for snr in (7,8):
        selected=[r for r in records if r['snr_db']==snr and r['partition']=='heldout']
        if [r['block'] for r in selected]!=list(range(256,320)):
            raise ValueError('B heldout block denominator changed')
        tables[str(snr)]={}
        for role in ('I1','hard','proposed','multistart','oracle'):
            values=[r['results'][role] for r in selected]
            tables[str(snr)][role]=dict(n=64,frame_errors=sum(r['frame_error'] for r in values),
                FER=sum(r['frame_error'] for r in values)/64,bits=sum(r['bits'] for r in values),
                bit_errors=sum(r['bit_errors'] for r in values),decode_ok=sum(r['decode_ok'] for r in values),
                mean_receiver_seconds=float(np.mean([r['seconds'] for r in values])))
        for arm,reference in contrasts:
            comparisons.append(dict(snr_db=snr,arm=arm,reference=reference,**paired_fer(
                [r['results'][arm]['frame_error'] for r in selected],
                [r['results'][reference]['frame_error'] for r in selected],alpha=.05,comparisons=12)))
    dependencies.verify()
    report=dict(schema='adjacent-pool-audit-v1',attempted_F=1280,completed_F=1280,reused_I1_F=256,
        local_nomination_queries=query_total,code_hashes=code_hashes,output_lock_sha256=file_sha(out/'output-lock.json'),
        raw_output_bytes=lock['bytes'],records=records,tables=tables,comparisons=comparisons,
        audit_seconds=time.time()-started,oracle_scope='post-freeze within proposed3, information-bit-error ordering; not deployable',
        timing_scope='concurrent diagnostic only; I1 reuse is instrumented, all B nomination/refit/BP/LDPC/scoring counted',
        confirmation_outcomes='not opened')
    finish(out,report,index,guard)


def audit_reference(root,out,manifest_path,kind,precheck_lock):
    started=time.time()
    domains={'confirm':('confirm-gpu',0,2048,'confirm','F_I'),
        'cost-warmup':('cost-warmup',1537,1547,'timing','F_C'),
        'cost-measurement':('cost-measurement',1547,2059,'timing','F_C')}
    batch_name,first,stop,split,family=domains[kind]
    release_guard=None
    if kind=='confirm':
        if precheck_lock is None:
            raise ValueError('confirmation outcomes require a content-bound A/B release lock')
        release=read(precheck_lock)
        if (release['status']!='A_B_outputs_and_methods_frozen'
                or release['confirmation_outcomes_opened'] is not False):
            raise ValueError('invalid precheck release lock')
        release_guard=BoundFiles(release['files'])
    batch=root/batch_name
    arms=['I1','A2','B_star_1']
    columns=[dict(index=i,snr_db=s,arm=a) for i,(s,a) in enumerate((s,a) for s in (7,8,9) for a in arms)]
    n=stop-first
    run,closure=completed_run(batch,n*9)
    if file_sha(manifest_path)!=run['manifest_sha256']:
        raise ValueError('reference admission manifest changed')
    manifest=read(manifest_path)
    validate_history(manifest)
    dependencies=BoundFiles(manifest['bound_files'])
    out.mkdir(exist_ok=False)
    guard,lock=freeze_tree(batch,out/'output-lock.json')
    code,code_hashes=load_code(batch,run.get('code_hashes'))
    expected={f'b{b:06d}-s{s}' for b in range(first,stop) for s in (7,8,9)}
    if {p.name for p in batch.glob('b*-s*')}!=expected:
        raise ValueError('reference cell inventory differs')
    index,records,cross_snr=[],[],{}
    seconds=np.empty((n,9),float)
    fer=np.empty((n,9),np.uint8)
    errors=np.empty((n,9),np.int64)
    decode_ok=np.empty((n,9),np.uint8)
    code_errors=np.empty((n,9),np.int64)
    for block in range(first,stop):
        for snr in (7,8,9):
            cell=batch/f'b{block:06d}-s{snr}'
            meta=read(cell/'input.json')
            frame=meta['frame']
            if (frame['block'],frame['snr_db'],frame['split'],frame['family'])!=(block,snr,split,family):
                raise ValueError('reference exogenous identity differs')
            inputs=load_raw(meta['raw'],root,index)
            exogenous=validate_input(inputs,frame)
            if block in cross_snr:
                if cross_snr[block]!=exogenous:
                    raise ValueError('cross-SNR exogenous pairing differs')
            elif not np.array_equal(encode(code,inputs['truth']['info']),inputs['truth']['coded']):
                raise ValueError('source information does not match the frozen encoder codeword')
            cross_snr[block]=exogenous
            if set(meta['order'])!=set(arms) or len(meta['order'])!=3:
                raise ValueError('reference order drops or duplicates an arm')
            for arm in arms:
                column=3*(snr-7)+arms.index(arm)
                path=cell/(arm+'-r0.json')
                row=read(path)
                if (row['identity']!=dict(block=block,snr_db=snr,arm=arm,repeat=0)
                        or row['input_hashes']!=frame['input_hashes']
                        or row['rng_before']!=row['rng_after'] or row['audit'] is not False or row['profile']!=[]):
                    raise ValueError('reference receiver pairing, RNG or audit boundary differs')
                raw=load_raw(row['raw'],root,index)
                result=raw['result']
                score=validate_errors(result,inputs['truth'],row['scores'])
                if (result['source_sha256']!=manifest['source_manifest'] or raw['bp_input_states']!=[]
                        or not np.isfinite(row['seconds']) or row['seconds']<=0):
                    raise ValueError('reference frozen source, state capture or timing invalid')
                seconds[block-first,column]=row['seconds']
                fer[block-first,column]=score['frame_error']
                errors[block-first,column]=score['bit_errors']
                code_errors[block-first,column]=score['codeword_errors']
                decode_ok[block-first,column]=bool(result['decode_ok'])
                records.append(dict(block=block,snr_db=snr,arm=arm,**score,decode_ok=bool(result['decode_ok']),
                    seconds=row['seconds'],CPU_seconds=row['CPU_seconds'],
                    generation_seconds=meta['generation_seconds'],
                    peak_cuda_bytes=row['peak_cuda_bytes'],peak_rss_kib=row['peak_rss_kib'],
                    meta_sha256=file_sha(path),input_meta_sha256=file_sha(cell/'input.json')))
        if (block-first+1)%128==0:
            print(json.dumps(dict(event='reference_audit_progress',kind=kind,blocks=block-first+1,
                seconds=time.time()-started)),flush=True)
    compact=out/'compact.npz'
    np.savez_compressed(compact,seconds=seconds,frame_errors=fer,info_errors=errors,
        code_errors=code_errors,decode_ok=decode_ok,blocks=np.arange(first,stop,dtype=np.int64))
    tables=[]
    for column in columns:
        i=column['index']
        tables.append(dict(column,n=n,frame_errors=int(fer[:,i].sum()),FER=float(fer[:,i].mean()),
            bit_errors=int(errors[:,i].sum()),bits=n*code['k'],BER=float(errors[:,i].sum()/(n*code['k'])),
            decode_ok=int(decode_ok[:,i].sum()),mean_seconds=float(seconds[:,i].mean()),
            p95_seconds=float(np.quantile(seconds[:,i],.95))))
    comparisons=[]
    decisions=None
    if kind=='confirm':
        for snr in (7,8,9):
            for reference in ('A2','B_star_1'):
                comparisons.append(dict(snr_db=snr,arm='I1',reference=reference,**paired_fer(
                    fer[:,3*(snr-7)],fer[:,3*(snr-7)+arms.index(reference)],alpha=.025,comparisons=6)))
        decisions=confirmation_decisions(comparisons)
        release_guard.verify()
    dependencies.verify()
    report=dict(schema='adjacent-reference-audit-v1',kind=kind,attempted_F=n*9,completed_F=n*9,
        n_independent_blocks=n,snrs=[7,8,9],arms=arms,columns=columns,tables=tables,
        comparisons=comparisons,decisions=decisions,records=records,code_hashes=code_hashes,
        run_sha256=file_sha(batch/'run.json'),complete_sha256=file_sha(batch/'complete.json'),
        output_lock_sha256=file_sha(out/'output-lock.json'),raw_output_bytes=lock['bytes'],
        compact=dict(path=str(compact),sha256=file_sha(compact),md5=hashlib.md5(compact.read_bytes()).hexdigest()),
        precheck_lock_sha256=file_sha(precheck_lock) if kind=='confirm' else None,
        audit_seconds=time.time()-started,scope='fixed paired exogenous blocks; SNRs share blocks, not independent replications')
    finish(out,report,index,guard)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--kind',choices=['pool','confirm','cost-warmup','cost-measurement'],default='pool')
    parser.add_argument('--precheck-lock',type=Path)
    args=parser.parse_args()
    for path in (args.root,args.out,args.manifest):
        if not path.resolve().is_relative_to(Path('/data/guoyikun')):
            parser.error('audit paths must remain under /data/guoyikun')
    if args.kind=='pool':
        audit_pool(args.root,args.out,args.manifest)
    else:
        audit_reference(args.root,args.out,args.manifest,args.kind,args.precheck_lock)
