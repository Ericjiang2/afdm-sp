"""Pmatched selection from complete hash-bound pilot audit; no receiver execution."""
import argparse
import itertools
import json
import math
from pathlib import Path
import numpy as np
from . import supplement_baseline_select as base
from .supplement_baselines import recipe_by_id
from .supplement_data import CAMPAIGN_ID
from .supplement_statistics import paired_delta
from .budgeted_frame_store import publish_json

RECIPES=['B0-p2-s0.5','bounded-param-p3-s1','group-p3-s1','ridge-p3-s0.5',
         'SBL-p2-s0.5','B0-p3-s0.5','B0-p2-s1','bounded-param-p2-s1']
PILOTS=['p0','p1','p2'];BLOCKS=192
SELECTION_PROTOCOL_SHA='a476820d649d7a36ac32a7674a7c2581f6af01613b25ec8865b8c821d3b82b87'
LIMITATION='Refit diagnostics/stationarity were not retained. Eligibility is a frozen-source runtime assertion, not independently recomputed refit convergence; bounded-param has no added stationarity gate.'


def all_identities():
    return {(m,b,s,p,r) for m in ('Pfixed','Pmatched') for b in range(BLOCKS)
            for s in ([7,8,9] if m=='Pfixed' else [8]) for p in PILOTS
            for r in (RECIPES[:1] if m=='Pfixed' else RECIPES)}


def qualification(row):
    eligible=row.get('baseline_eligible');initial=row.get('initial_estimator',{})
    if type(eligible) is not bool or type(initial.get('converged')) is not bool:
        raise ValueError('explicit runtime qualification missing')
    family=row['recipe']['family'];converged=initial['converged']
    if (eligible and not converged) or (family!='group' and eligible!=converged):
        raise ValueError('runtime eligibility contradicts frozen qualification logic')
    return eligible


def validate_protocol(path):
    protocol,digest=base.read_json(path,SELECTION_PROTOCOL_SHA)
    expected=dict(schema='supplement-pilot-receiver-selection-protocol-v1',blocks=192,snr_db=8,
                  pilots=PILOTS,recipes=RECIPES,comparisons=84,alpha_development=.05)
    if any(protocol.get(k)!=v for k,v in expected.items()) or protocol['selector_source_sha256']!=base.file_hash(base.__file__):
        raise ValueError('frozen selection protocol/helper mismatch')
    return dict(path=str(path),sha256=digest,protocol=protocol)


def verify_sources(bindings,source_root,inputs,checkpoint):
    actual={str(p.relative_to(source_root)):base.file_hash(p) for p in Path(source_root).rglob('*.py')}
    names=dict(protocol='data-protocol.json',design='pilot-receiver-development-protocol-v1.json',
        pilots='frozen-pilots-v1.npz',pilot_manifest='frozen-pilots-v1.json',pilot_protocol='pilot-selection-protocol-v1.json')
    files={k:base.file_hash(Path(inputs)/v) for k,v in names.items()};files['checkpoint']=base.file_hash(checkpoint)
    if bindings!={'files':files,'source_sha256':actual}:raise ValueError('frozen source/input hashes differ')


def index_rows(rows,bindings):
    table={};common={};pilot_inputs={};allowed=all_identities()
    for row in rows:
        identity=tuple(row['identity'])
        if identity in table or identity not in allowed:raise ValueError('duplicate/unknown pilot identity')
        mode,b,s,p,r=identity;m=row['metadata']
        if (row.get('schema')!='supplement-pilot-design-frame-v1' or row['campaign_id']!=CAMPAIGN_ID or
                row['bindings']!=bindings or row['recipe']!=recipe_by_id(r) or row['failure'] is not None or
                row['call_type']!='full' or row['truth_access_level']!='none' or
                m['split']!='design' or m['scenario']!='G0' or m['block']!=b or m['snr_db']!=s or
                m['pilot_id']!=p or m['protocol_sha256']!=bindings['files']['protocol']):
            raise ValueError('pilot frame/source/metadata contract mismatch')
        if type(row['FER']) is not int or row['FER'] not in (0,1) or not math.isfinite(row['elapsed_seconds']) or row['elapsed_seconds']<=0:
            raise ValueError('invalid FER/full-call cost')
        qualification(row)
        power=m['power'];passed=power['passes_declared_simulation_power_gate']
        if (type(passed) is not bool or not all(math.isfinite(power[k]) for k in ('papr_db','peak_power')) or
                power['papr_limit_db']!=12 or power['peak_power_limit']!=16 or
                passed!=(power['papr_db']<=12 and power['peak_power']<=16)):
            raise ValueError('power gate mismatch')
        hashes=m['input_hashes'];external={k:hashes[k] for k in ('H','data','noise','info','coded')}
        if common.setdefault((b,s),external)!=external:raise ValueError('unpaired exogenous blocks')
        observed={k:hashes[k] for k in ('y','pilot')}
        if pilot_inputs.setdefault((b,s,p),(observed,power))!=(observed,power):raise ValueError('unpaired pilot observations/power')
        table[identity]=row
    if set(table)!=all_identities():raise ValueError('complete6336 identities required; no denominator shrink')
    return table


def load_audit(path,digest):
    audit,audit_sha=base.read_json(path,digest)
    if (audit.get('status')!='complete_audited' or audit.get('F_audited')!=6336 or
            audit.get('audit_F')!=0 or audit.get('audit_T')!=0 or len(audit['records'])!=6336):
        raise ValueError('complete original raw-error audit required')
    bindings=audit['source_bindings'];rows=[];batches={};paths=set();seenproof=set()
    proofs={p['config_sha256']:p for p in audit['proofs']}
    if len(proofs)!=len(audit['proofs']):raise ValueError('duplicate audit batch proof')
    for evidence in audit['records']:
        spec=evidence['record'];record_path=Path(spec['path']).resolve()
        if record_path in paths:raise ValueError('duplicate audited frame path')
        paths.add(record_path);row,_=base.read_json(record_path,spec['sha256']);root=record_path.parent
        if root not in batches:
            summary,summary_sha=base.read_json(root/'summary.json');contract,contract_sha=base.read_json(root/'contract.json')
            config=base.config_hash(contract);proof=proofs[config];seenproof.add(config)
            count=len(contract['identities'])
            if (not 0<=proof['start']<proof['stop']<=192 or proof['stop']-proof['start']>16 or
                    summary_sha!=proof['summary_sha256'] or summary.get('status')!='complete' or summary.get('exitcode')!=0 or
                    summary.get('failures') or summary.get('missing_or_failed_identities') or
                    contract['config_sha256']!=config or summary['config_sha256']!=config or
                    contract['bindings']!=bindings or contract['campaign_id']!=CAMPAIGN_ID or
                    count!=proof['full_calls'] or count!=contract['max_full_calls'] or
                    contract['calls_reserved']!={'F':count,'T':0,'E':0} or
                    summary['calls_attempted']!=count or summary['calls_completed']!=count or len(summary['records'])!=count):
                raise ValueError('audited batch configuration/count mismatch')
            committed={str(Path(v['path']).resolve()):v['sha256'] for v in summary['records']}
            if len(committed)!=count or set(committed)!={str(p.resolve()) for p in root.glob('frame-*.json')}:
                raise ValueError('extra/duplicate frame files')
            if list(root.glob('failure-*.json')) or (root/'batch-failure.json').exists():raise ValueError('failure artifact present')
            batch_ids={tuple(i) for i in contract['identities']}
            if len(batch_ids)!=count or any(i[0]!=proof['mode'] or not proof['start']<=i[1]<proof['stop'] for i in batch_ids):
                raise ValueError('batch identity/proof mismatch')
            batches[root]=dict(config_sha256=config,contract=contract,contract_file_sha256=contract_sha,
                summary_sha256=summary_sha,committed=committed,identities=batch_ids,loaded=set())
        batch=batches[root];key=tuple(row['identity'])
        if (batch['committed'].get(str(record_path))!=spec['sha256'] or row['config_sha256']!=batch['config_sha256'] or
                key not in batch['identities'] or key in batch['loaded'] or list(key)!=evidence['identity'] or
                evidence['terminal_sha256']!=row['terminal']['sha256'] or evidence['seconds']!=row['elapsed_seconds'] or
                evidence['power']!=row['metadata']['power'] or any(row[k]!=v for k,v in evidence['errors'].items())):
            raise ValueError('raw audit reference disagrees with original frame')
        batch['loaded'].add(key);rows.append(row)
    if (seenproof!=set(proofs) or any(b['loaded']!=b['identities'] for b in batches.values()) or
            sum(b['contract']['max_full_calls'] for b in batches.values())!=6336):
        raise ValueError('incomplete audit/batch budget coverage')
    table=index_rows(rows,bindings)
    clean=[{k:v for k,v in b.items() if k not in ('committed','identities','loaded')} for b in batches.values()]
    return table,clean,dict(path=str(path),sha256=audit_sha,source_bindings=bindings,
                           scope='original raw-terminal error audit bound by SHA; selector rechecks original frame files')


def analyze(table,a2):
    output={};all_intervals=[];fixed_metrics={}
    for pilot in PILOTS:
        metrics={};intervals={}
        for identifier in RECIPES:
            rows=[table['Pmatched',b,8,pilot,identifier] for b in range(BLOCKS)]
            seconds=[r['elapsed_seconds'] for r in rows];failures=sum(not qualification(r) for r in rows)
            mean=float(np.mean(seconds));errors=sum(r['FER'] for r in rows)
            metrics[identifier]=dict(family=recipe_by_id(identifier)['family'],n=BLOCKS,frame_errors=errors,
                FER=errors/BLOCKS,elapsed_seconds=seconds,mean_seconds=mean,qualification_failures=failures,
                qualified=failures==0,cost_ratio_to_A2=mean/a2['mean_seconds'],budget_screen=mean<=1.1*a2['mean_seconds'],
                power_failures=sum(not r['metadata']['power']['passes_declared_simulation_power_gate'] for r in rows),
                qualification_evidence='runtime assertion bound to frozen source; '+LIMITATION)
        for left,right in itertools.combinations(sorted(RECIPES),2):
            a=np.array([table['Pmatched',b,8,pilot,left]['FER'] for b in range(BLOCKS)])
            c=np.array([table['Pmatched',b,8,pilot,right]['FER'] for b in range(BLOCKS)])
            W=int(np.count_nonzero((a==1)&(c==0)));L=int(np.count_nonzero((a==0)&(c==1)))
            ci=paired_delta(W,L,BLOCKS,alpha_family=.05,m=84)
            interval=dict(pilot=pilot,left=left,right=right,W=W,L=L,n=BLOCKS,delta=float(ci['delta']),
                lower=float(ci['lower']),upper=float(ci['upper']),tail_alpha=float(ci['tail']),direction='FER_left - FER_right')
            intervals[left,right]=interval;all_intervals.append(interval)
        selection=base.select_references(metrics,intervals)
        primary=selection['references'][0] if selection['references'] else None
        alternatives=[]
        if primary is not None:
            for name,value in metrics.items():
                if name==primary or not value['qualified'] or not value['budget_screen']:continue
                key=tuple(sorted((name,primary)));ci=intervals[key]
                lower=ci['lower'] if key[0]==name else -ci['upper']
                if lower<=0:alternatives.append(name)
        selection['all_qualified_budget_not_demonstrably_worse_recipes']=sorted(alternatives)
        output[pilot]=dict(metrics=metrics,selection=selection,
            primary=selection['references'][0] if selection['references'] else None,
            secondary=selection['references'][1] if len(selection['references'])>1 else None)
    for pilot,snr in itertools.product(PILOTS,(7,8,9)):
        rows=[table['Pfixed',b,snr,pilot,RECIPES[0]] for b in range(BLOCKS)]
        fixed_metrics[f'{pilot}@{snr}']=dict(n=BLOCKS,frame_errors=sum(r['FER'] for r in rows),
            FER=sum(r['FER'] for r in rows)/BLOCKS,elapsed_seconds=[r['elapsed_seconds'] for r in rows],
            qualification_failures=sum(not qualification(r) for r in rows),
            power_failures=sum(not r['metadata']['power']['passes_declared_simulation_power_gate'] for r in rows))
    return dict(pilots=output,Pfixed_metrics=fixed_metrics,all84_intervals=all_intervals,a2_quote=a2,multiplicity=84,alpha_development=.05,
        confirmation_alpha_consumed=0,confirmation_contrasts={m:['p1-p0','p2-p0','p1-p2'] for m in ('Pfixed','Pmatched')},
        limitations=[LIMITATION,'Concurrent development costs are a provisional1.1 A2 screen, not COST-02.',
            'Power violations remain in every denominator and prevent deployable claims; no confirmation access.'],
        scope='development selection only; unselected is not demonstrated inferior')


def read_bound_a2(selection_path,design_path,admission_path,bindings):
    design,_=base.read_json(design_path,bindings['files']['design'])
    selection,selection_sha=base.read_json(selection_path,design['baseline_selection_sha256'])
    quote=selection['a2_quote'];samples=quote['samples'];mean=quote['mean_seconds']
    admission,admission_sha=base.read_json(admission_path)
    if (quote.get('status')!='provisional_engineering_mean_screen_only_not_COST02' or
            quote.get('boundary')!=base.COST_BOUNDARY or type(quote['n']) is not int or
            quote['n']!=len(samples) or not samples or
            any(not math.isfinite(v) or v<=0 for v in samples) or not math.isfinite(mean) or mean<=0 or
            not math.isclose(mean,float(np.mean(samples)),rel_tol=1e-12,abs_tol=0) or
            admission.get('bindings')!=bindings or admission.get('gpu_uuid')!=quote.get('gpu_uuid')):
        raise ValueError('bound original A2 quote/GPU admission mismatch')
    return dict(quote,baseline_selection_sha256=selection_sha,pilot_admission_sha256=admission_sha,
        reuse_scope='Reuse hash-bound BASE validated A2 evidence, not a newly synthesized cost scalar; pilot GPU admission matched, physical execution audit remains separate.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('audit','selection-protocol','baseline-selection','pilot-admission','source-root','inputs','checkpoint','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--audit-sha256',required=True);args=p.parse_args()
    protocol=validate_protocol(args.selection_protocol)
    table,batches,audit=load_audit(args.audit,args.audit_sha256)
    verify_sources(audit['source_bindings'],args.source_root,args.inputs,args.checkpoint)
    a2=read_bound_a2(args.baseline_selection,args.inputs/'pilot-receiver-development-protocol-v1.json',
        args.pilot_admission,audit['source_bindings']);result=analyze(table,a2)
    result.update(selection_protocol=protocol,raw_audit=audit,batches=batches,selector_sha256=base.file_hash(__file__))
    publish_json(args.out,result)
    return int(any(v['primary'] is None for v in result['pilots'].values()))


if __name__=='__main__':raise SystemExit(main())
