"""Audited BASE design selection; exploratory simultaneous intervals, not confirmation."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
import re
from pathlib import Path
import traceback

import numpy as np
from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash
from .supplement_data import CAMPAIGN_ID
from .supplement_baselines import catalogue
from .supplement_statistics import paired_delta
from .supplement_profile import A2_SOURCE,PRIOR_HASH
from .direction_receiver import CHECKPOINT_HASH

BLOCKS=192
COMPARISONS=780
ALPHA=.05
COST_BOUNDARY='observed-host-y-through-terminal-BP-LLR-LDPC'


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def read_json(path,expected=None):
    raw=Path(path).read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if expected is not None and digest!=expected:raise ValueError('artifact SHA256 mismatch: '+str(path))
    value=json.loads(raw);json.dumps(value,allow_nan=False)
    return value,digest


def config_hash(contract):
    payload={k:v for k,v in contract.items() if k not in ('config_sha256','ledger')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()


def artifact_path(root,spec):
    path=Path(spec['path'])
    local=Path(root)/path.name
    return local if local.is_file() else path


def verify_terminal(root,row):
    spec=row['terminal'];path=artifact_path(root,spec)
    if path.stat().st_size!=spec['bytes'] or file_hash(path)!=spec['sha256']:
        raise ValueError('terminal bytes/hash mismatch')
    with np.load(path,allow_pickle=False) as raw:
        shapes={'H':(1024,1024),'x_soft':(1024,),'mu':(1024,),'var':(1024,),
            'llr':(2048,),'y':(1024,),'pilot':(1024,),'constellation':(4,),
            'sigma2':(),'sigma2_terminal':(),'sigma2_thermal':()}
        if any(raw[k].shape!=shape or not np.isfinite(raw[k]).all() for k,shape in shapes.items()):
            raise ValueError('invalid full terminal state dimensions/finiteness')
        support,gains=raw['support'],raw['gains']
        if (support.ndim!=1 or len(support)>40 or support.dtype.kind not in 'iu' or
                len(set(support.tolist()))!=len(support) or np.any(support<0) or np.any(support>=515) or
                gains.shape!=support.shape or not np.isfinite(gains).all() or
                any(np.iscomplexobj(raw[k]) or np.any(raw[k]<=0) for k in ('var','sigma2','sigma2_terminal','sigma2_thermal'))):
            raise ValueError('invalid terminal support/gains/variance')
        if array_hash(raw['H'])!=row['H_data_source']['sha256'] or float(raw['sigma2_terminal'])!=row['sigma_value']:
            raise ValueError('terminal H/sigma differs from record')
        info,coded,decoded,ihat,hard=[raw[k] for k in ('info','coded','decoded','info_hat','x_hard')]
        if (coded.shape!=(2048,) or decoded.shape!=coded.shape or info.ndim!=1 or not info.size or
                ihat.shape!=info.shape or hard.shape!=(1024,) or not np.isfinite(hard).all() or
                any(not np.isin(v,(0,1)).all() for v in (info,coded,decoded,ihat))):
            raise ValueError('invalid raw terminal bit/symbol dimensions')
        for key in ('info','coded','y','pilot'):
            if array_hash(raw[key])!=row['input_hashes'][key]:raise ValueError('terminal input lineage mismatch')
        errors=int(np.count_nonzero(ihat!=info))
        raw_bits=np.concatenate((hard.real<0,hard.imag<0)).astype(np.uint8)
        expected=dict(FER=int(errors>0),coded_bit_errors=errors,
            raw_bit_errors=int(np.count_nonzero(raw_bits!=coded)),
            decoded_codeword_bit_errors=int(np.count_nonzero(decoded!=coded)),
            raw_bits_denominator=2048,coded_bits_denominator=int(info.size))
        if any(type(row[k]) is not int or row[k]!=v for k,v in expected.items()):
            raise ValueError('record error counts disagree with raw terminal')
    return dict(path=str(path),sha256=spec['sha256'],bytes=spec['bytes'])


def qualification(row):
    if type(row.get('baseline_eligible')) is not bool:raise ValueError('missing explicit baseline qualification')
    family=row['recipe']['family'];initial=row['initial_estimator']
    if not isinstance(initial,dict) or type(initial.get('converged')) is not bool:
        raise ValueError('missing initializer convergence evidence')
    qualified=initial['converged']
    if family in ('group','bounded-param'):
        refit=row['channel_refit']
        if not isinstance(refit,dict) or type(refit.get('converged')) is not bool:
            raise ValueError('missing terminal refit convergence evidence')
        if family=='group':qualified=qualified and refit['converged']
        else:
            count=refit.get('query_count')
            if type(count) is not int or not 0<=count<=73:
                raise ValueError('bounded terminal query count missing/outside budget')
            # Completion of the registered one-sweep algorithm is sufficient here.
            # Grid stationarity remains a separate diagnostic, not an invented gate.
    if row['baseline_eligible']!=bool(qualified):raise ValueError('qualification flag contradicts diagnostics')
    return bool(qualified)


def load_run(root):
    root=Path(root);summary,summary_sha=read_json(root/'summary.json');contract,contract_sha=read_json(root/'contract.json')
    if (summary.get('status')!='complete' or summary.get('exitcode')!=0 or summary.get('failures') or
            summary.get('missing_or_failed_identities') or (root/'batch-failure.json').exists() or
            list(root.glob('failure-*.json'))):raise ValueError('incomplete/failed batch cannot supply complete BASE evidence')
    digest=config_hash(contract)
    if contract.get('config_sha256')!=digest or summary.get('config_sha256')!=digest:
        raise ValueError('batch configuration hash mismatch')
    recipes={r['id']:r for r in catalogue()}
    chosen=contract['recipes'];ids=[r['id'] for r in chosen]
    if (not chosen or len(ids)!=len(set(ids)) or any(recipes.get(r['id'])!=r for r in chosen) or
            contract['campaign_id']!=CAMPAIGN_ID or contract['split']!='design' or contract['snr']!=8 or
            not 0<=contract['start']<contract['stop']<=BLOCKS):raise ValueError('batch differs from frozen BASE catalogue/domain')
    expected=set(itertools.product(range(contract['start'],contract['stop']),ids))
    count=len(expected)
    if (summary['calls_attempted']!=count or summary['calls_completed']!=count or
            len(summary['records'])!=count or not count<=contract['max_full_calls']<=7680):raise ValueError('batch call accounting differs')
    listed={Path(r['path']).name for r in summary['records']}
    if len(listed)!=count or listed!={p.name for p in root.glob('frame-*.json')}:
        raise ValueError('frame files differ from committed summary')
    starts={}
    startfiles=list(root.glob('call-*-started.json'))
    if len(startfiles)!=count:raise ValueError('missing/extra started-call identity')
    for ordinal in range(1,count+1):
        start,_=read_json(root/f'call-{ordinal:05d}-started.json')
        key=(start['block'],start['arm_id'])
        if key in starts or key not in expected or start['attempt']!=ordinal or start['split']!='design':
            raise ValueError('duplicate/mismatched call identity')
        starts[key]=start
    rows=[];seen=set();unqualified=0
    for spec in summary['records']:
        path=root/Path(spec['path']).name;row,_=read_json(path,spec['sha256']);key=(row['block_id'],row['arm_id'])
        if key in seen or key not in expected:raise ValueError('duplicate/unknown frame identity')
        seen.add(key);m=row['metadata']
        if (row.get('schema')!='supplement-baseline-design-frame-v1' or row['campaign_id']!=CAMPAIGN_ID or
                row['split']!='design' or row['SNR']!=8 or row['scenario']!='G0' or
                row['recipe']!=recipes[key[1]] or row['call_type']!='full' or row['failure'] is not None or
                row['truth_access_level']!='none' or row['offline_truth_access']!='evaluation_only' or
                row['config_sha256']!=digest or m['split']!='design' or m['block']!=key[0] or m['snr_db']!=8 or
                m['protocol_sha256']!=contract['protocol_sha256'] or row['input_hashes']!=m['input_hashes'] or
                starts[key]['input_hashes']!=row['input_hashes']):raise ValueError('frame identity/truth/input contract mismatch')
        for name in ('source_sha256','protocol_sha256','checkpoint_sha256','code_sha256'):
            if row[name]!=contract[name]:raise ValueError('row differs from bound source/code/protocol')
        if 'device' in row and row['device']!=contract['device']:
            raise ValueError('frame device differs from contract')
        if not math.isfinite(row['elapsed_seconds']) or row['elapsed_seconds']<=0:
            raise ValueError('invalid complete full-call time')
        unqualified+=int(not qualification(row))
        verify_terminal(root,row);rows.append(row)
    if seen!=expected or summary['unqualified_completed_records']!=unqualified:
        raise ValueError('qualification count or batch coverage mismatch')
    return rows,dict(root=str(root),summary_sha256=summary_sha,contract_file_sha256=contract_sha,
        config_sha256=digest,contract=contract)


def index_complete(rows):
    ids=[r['id'] for r in catalogue()];table={}
    for row in rows:
        key=(row['block_id'],row['arm_id'])
        if key in table:raise ValueError('duplicate BASE identity across batches')
        table[key]=row
    if set(table)!=set(itertools.product(range(BLOCKS),ids)):
        raise ValueError('requires every192x40 identity exactly once; qualification cannot shrink denominator')
    first=rows[0]
    for row in rows:
        if any(row[k]!=first[k] for k in ('source_sha256','protocol_sha256','checkpoint_sha256','code_sha256')):
            raise ValueError('mixed frozen BASE source/code/protocol across batches')
    for block in range(BLOCKS):
        inputs=table[block,ids[0]]['input_hashes']
        if any(table[block,identifier]['input_hashes']!=inputs for identifier in ids):
            raise ValueError('unpaired exogenous block across recipes')
    return table


def paired_intervals(table):
    ids=sorted(r['id'] for r in catalogue());output={}
    for left,right in itertools.combinations(ids,2):
        a=np.array([table[b,left]['FER'] for b in range(BLOCKS)])
        c=np.array([table[b,right]['FER'] for b in range(BLOCKS)])
        # paired_delta(W,L) is FER_left - FER_right when W=left error/right success.
        W=int(np.count_nonzero((a==1)&(c==0)));L=int(np.count_nonzero((a==0)&(c==1)))
        bound=paired_delta(W,L,BLOCKS,alpha_family=ALPHA,m=COMPARISONS)
        output[(left,right)]=dict(left=left,right=right,W=W,L=L,n=BLOCKS,
            delta=float(bound['delta']),lower=float(bound['lower']),upper=float(bound['upper']),
            tail_alpha=float(bound['tail']),direction='FER_left - FER_right')
    return output


def read_a2_quote(path,batches):
    quote,digest=read_json(path);root=Path(path).parent
    if (quote.get('schema')!='supplement-A2-cost-quote-v1' or quote.get('campaign_id')!=CAMPAIGN_ID or
            quote.get('reference')!='A2' or quote.get('boundary')!=COST_BOUNDARY):
        raise ValueError('explicit original A2 full-boundary quote required')
    cspec=quote['a2_contract'];contract,_=read_json(artifact_path(root,cspec),cspec['sha256'])
    config=config_hash(contract)
    if (contract.get('config_sha256')!=config or contract.get('A2_source')!=A2_SOURCE or
            contract.get('checkpoint_sha256')!=CHECKPOINT_HASH or contract.get('prior_sha256')!=PRIOR_HASH):
        raise ValueError('A2 recipe/checkpoint/prior/config identity mismatch')
    complete_spec=quote['a2_complete']
    complete,_=read_json(artifact_path(root,complete_spec),complete_spec['sha256'])
    if complete.get('status')!='complete' or complete.get('exitcode')!=0 or complete.get('config_sha256')!=config:
        raise ValueError('A2 quote needs a completed bound profile batch')
    committed={(Path(v['path']).name,v['sha256']) for v in complete['records']}
    hs=quote['host_binding'];hosts,_=read_json(artifact_path(root,hs),hs['sha256'])
    # A self-written host label is not provenance. BASE must supply the original
    # SSH capture containing BOTH its completed config hash and GPU UUID.
    captures=hosts.get('base_ssh_captures')
    if not isinstance(captures,list):raise ValueError('BASE SSH source captures required')
    bound={}
    for capture in captures:
        key=capture['config_sha256'];uuid=capture['gpu_uuid'];spec=capture['source']
        source=artifact_path(root,spec)
        if (not isinstance(uuid,str) or not re.fullmatch(r'GPU-[0-9a-fA-F-]+',uuid)
                or not isinstance(capture.get('ssh_alias'),str) or not capture['ssh_alias'].strip()
                or file_hash(source)!=spec['sha256']):
            raise ValueError('invalid SSH capture provenance')
        text=source.read_text()
        if key not in text or uuid not in text or key in bound:
            raise ValueError('SSH source does not bind unique BASE config and GPU UUID')
        bound[key]=uuid
    required=[b['config_sha256'] for b in batches]
    if not required or any(k not in bound for k in required) or len({bound[k] for k in required})!=1:
        raise ValueError('BASE batches lack common physical GPU evidence')
    gpu_uuid=bound[required[0]]
    if any(b['contract']['device']!=contract['device'] or b['contract']['threads']!=contract['threads'] for b in batches):
        raise ValueError('A2/BASE device or thread policies differ')
    samples=[];seen=set()
    for spec in quote['samples']:
        sample_path=artifact_path(root,spec)
        if (sample_path.name,spec['sha256']) not in committed:raise ValueError('A2 sample absent from completion manifest')
        if str(sample_path.resolve()) in seen:raise ValueError('duplicate A2 cost sample')
        seen.add(str(sample_path.resolve()));row,_=read_json(sample_path,spec['sha256'])
        attempt=row.get('attempt',{})
        if (attempt.get('kind')!='F' or attempt.get('arm')!='A2' or row.get('config_sha256')!=config or
                not math.isfinite(row['seconds']) or row['seconds']<=0):raise ValueError('invalid bound A2 full-call sample')
        for phase in ('gpu_occupancy_before','gpu_occupancy_after'):
            snapshot=row.get(phase,{})
            if snapshot.get('exitcode')!=0:
                raise ValueError('A2 sample lacks successful GPU UUID snapshot')
            lines=[line.split(',') for line in snapshot.get('stdout','').splitlines()]
            device_index=contract['device'].split(':')[-1]
            matching=[parts[1].strip() for parts in lines if len(parts)>=2 and parts[0].strip()==device_index]
            if matching!=[gpu_uuid]:raise ValueError('A2 sample and BASE SSH capture GPU UUID differ')
        samples.append(row['seconds'])
    if not samples:raise ValueError('empty A2 quote')
    return dict(mean_seconds=float(np.mean(samples)),samples=samples,n=len(samples),gpu_uuid=gpu_uuid,
        host_binding_sha256=hs['sha256'],provenance_scope='content-bound SSH captures plus committed A2 GPU snapshots; no hostname inferred',
        quote_sha256=digest,a2_config_sha256=config,boundary=COST_BOUNDARY,
        status='provisional_engineering_mean_screen_only_not_COST02')


def select_references(metrics,intervals):
    rank=lambda name:(metrics[name]['FER'],metrics[name]['mean_seconds'],name)
    representatives={}
    for family in sorted({v['family'] for v in metrics.values()}):
        names=[n for n,v in metrics.items() if v['family']==family and v['qualified'] and v['budget_screen']]
        representatives[family]=min(names,key=rank) if names else None
    names=[n for n in representatives.values() if n is not None]
    if not names:return dict(status='no_qualified_budget_reference',references=[],family_representatives=representatives)
    first=min(names,key=rank)
    def worse(candidate):
        key=tuple(sorted((candidate,first)));ci=intervals[key]
        lower=ci['lower'] if key[0]==candidate else -ci['upper']
        return lower>0
    alternatives=[n for n in names if n!=first and not worse(n)]
    pareto=[a for a in names if not any(metrics[b]['FER']<=metrics[a]['FER'] and
        metrics[b]['mean_seconds']<=metrics[a]['mean_seconds'] and
        (metrics[b]['FER']<metrics[a]['FER'] or metrics[b]['mean_seconds']<metrics[a]['mean_seconds'])
        for b in names if b!=a)]
    preferred=[a for a in alternatives if a in pareto]
    pool=preferred or alternatives
    refs=[first]+([min(pool,key=rank)] if pool else [])
    return dict(status='development_references_selected',references=refs,family_representatives=representatives,
        point_estimate_pareto=pareto,not_demonstrably_worse_alternatives=alternatives,
        unselected_not_proven_defeated=[n for n in alternatives if n not in refs],
        interpretation='operational development selection; no confirmation/cost gate or global optimality claim')


def analyze(table,a2):
    intervals=paired_intervals(table);metrics={}
    for r in catalogue():
        rows=[table[b,r['id']] for b in range(BLOCKS)]
        mean=float(np.mean([v['elapsed_seconds'] for v in rows]))
        failures=sum(not qualification(v) for v in rows)
        metrics[r['id']]=dict(family=r['family'],n=BLOCKS,frame_errors=sum(v['FER'] for v in rows),
            FER=sum(v['FER'] for v in rows)/BLOCKS,mean_seconds=mean,
            qualification_failures=failures,qualification_failure_rate=failures/BLOCKS,
            qualified=failures==0,cost_ratio_to_A2=mean/a2['mean_seconds'],budget_screen=mean<=1.1*a2['mean_seconds'])
    return dict(metrics=metrics,all780_intervals=list(intervals.values()),
        selection=select_references(metrics,intervals),a2_quote=a2,alpha_development=ALPHA,
        multiplicity=COMPARISONS,confirmation_alpha_consumed=0,
        scope='all192 blocks retained for every40 recipe; simultaneous exploratory paired CP union bounds')


def validate_selection_protocol(path):
    value,digest=read_json(path)
    expected=dict(schema='supplement-baseline-selection-protocol-v1',blocks=BLOCKS,
        recipes=catalogue(),comparisons=COMPARISONS,alpha_development=ALPHA,
        exploratory_difference_gate=0,cost_ratio_screen=1.1)
    if any(value.get(k)!=v for k,v in expected.items()):
        raise ValueError('selection protocol differs from preregistered design')
    if value.get('selector_sha256')!=file_hash(__file__):
        raise ValueError('selection protocol selector source mismatch')
    if value.get('baseline_design_sha256')!=file_hash(Path(path).parent/'baseline-design.json'):
        raise ValueError('selection protocol baseline design mismatch')
    return dict(path=str(path),sha256=digest,protocol=value)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',required=True,help='explicit JSON array of batch directories')
    p.add_argument('--selection-protocol',type=Path,required=True)
    p.add_argument('--a2-quote',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    try:
        protocol=validate_selection_protocol(args.selection_protocol)
        roots=json.loads(args.runs)
        if not isinstance(roots,list) or not roots or any(not isinstance(v,str) for v in roots) or len(set(roots))!=len(roots):raise ValueError('unique run list required')
        rows=[];batches=[]
        for root in roots:
            values,proof=load_run(root);rows.extend(values);batches.append(proof)
        if sum(b['contract']['max_full_calls'] for b in batches)>7680:
            raise ValueError('cumulative BASE reservations exceed7680F')
        table=index_complete(rows);a2=read_a2_quote(args.a2_quote,batches);result=analyze(table,a2)
        result['batches']=batches
        result['selection_protocol']=protocol
        result['selector_sha256']=file_hash(__file__)
        publish_json(args.out/'selection.json',result)
        return 0 if result['selection']['references'] else 1
    except BaseException as exc:
        publish_json(args.out/'failure.json',dict(status='failed',exception=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
        raise


if __name__=='__main__':raise SystemExit(main())
