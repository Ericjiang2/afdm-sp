"""Strict MECH-02 paired audit and preregistered exploratory contrasts."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.direction_logging import validate_record
from afdm_sp_joint_unrolled.direction_select import paired_interval,read

SOURCES=('estimated','true')
DETECTORS=('BP','EP10')
CELLS=tuple(f'cancel_{c}__data_{d}__{t}' for c,d,t in itertools.product(SOURCES,SOURCES,DETECTORS))


def cell(c,d,t):return f'cancel_{c}__data_{d}__{t}'


def difference(intervention,control):
    result=paired_interval(list(intervention),list(control),comparisons=10)
    low,high=result['interval']
    return {'FER_contrast':result['delta'],'FER_contrast_interval':[low,high],
            'benefit_delta':-result['delta'],'benefit_interval':[-high,-low],
            'paired_counts':result,'scope':'simultaneous conservative95% CP; independent blocks, paired arms'}


def interaction(hh,th,ht,tt,seed_words):
    arrays=[np.asarray(a) for a in (hh,th,ht,tt)]
    if any(a.ndim!=1 or a.shape!=arrays[0].shape or np.any((a!=0)&(a!=1)) for a in arrays):
        raise ValueError('paired binary interaction arrays must share one shape')
    values=arrays[3].astype(float)-arrays[1]-arrays[2]+arrays[0]
    if values.ndim!=1 or not len(values) or not np.isfinite(values).all():raise ValueError('invalid paired interaction')
    rng=np.random.default_rng(np.random.SeedSequence(seed_words))
    boot=np.empty(20000)
    for begin in range(0,20000,1000):
        indices=rng.integers(0,len(values),size=(1000,len(values)))
        boot[begin:begin+1000]=values[indices].mean(axis=1)
    lo,hi=np.quantile(boot,[.05/(2*10),1-.05/(2*10)])
    return {'FER_contrast':float(values.mean()),'FER_contrast_interval':[float(lo),float(hi)],
            'benefit_delta':float(-values.mean()),'benefit_interval':[float(-hi),float(-lo)],
            'blockwise_contrast':values.tolist(),'bootstrap_samples':20000,
            'seed_words':seed_words,'tail_alpha':.05/(2*10),'percentile_method':'linear',
            'zero_degenerate':bool(np.all(boot==0)), 'degenerate':bool(np.all(boot==boot[0])),
            'scope':'exploratory paired-block bootstrap; no formal coverage or equivalence guarantee'}


def validate_registry(reg,phash):
    if (reg['status']!='preregistered_before_D_mech' or reg['protocol_sha256']!=phash
            or reg['blocks']!=256 or reg['family_size']!=10 or reg['alpha_family']!=.05
            or reg['anchor_SNR']!=8 or reg['neighbor_SNR']!=[7,9]
            or reg['bootstrap_seed_words']!=[20260908,210644,731901,992,8]):
        raise ValueError('contrast registry differs from implemented frozen numerical contract')


def load_run(root,phash):
    root=Path(root)
    if (root/'failure.json').exists():raise ValueError('failed run cannot be used as complete mechanism evidence')
    complete,chash=read(root/'complete.json');contract,khash=read(root/'contract.json')
    counts=complete['calls_attempted']
    if (complete['status']!='complete' or counts!=complete['calls_completed']
            or set(counts)!={'mechanism_full','mechanism_terminal'}
            or contract['split']!='mechanism' or contract['protocol_sha256']!=phash
            or complete['protocol_sha256']!=phash):raise ValueError('invalid mechanism run completion/split/protocol')
    cfg=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    for key in ('source_sha256','B_star_sha256','detector_reference_sha256'):
        if complete[key]!=contract[key]:raise ValueError('run provenance mismatch')
    files={Path(p).name for p in complete['records']}
    if len(files)!=sum(counts.values()):raise ValueError('completed record count mismatch')
    actual={p.name for pattern in ('normal-full-*.json','cell-*.json') for p in root.glob(pattern)}
    if files!=actual:raise ValueError('missing/extra mechanism records')
    hashes={Path(p).name:h for p,h in complete['record_sha256'].items()}
    records=[];seen=set();audit_hashes={}
    for key,count in counts.items():
        for suffix in ('started','completed'):
            if len(list(root.glob(f'{suffix}-{key}-*.json')))!=count:raise ValueError('incomplete call ledger')
        for ordinal in range(1,count+1):
            start,_=read(root/f'started-{key}-{ordinal:06d}.json')
            end,_=read(root/f'completed-{key}-{ordinal:06d}.json')
            if start['ordinal']!=ordinal or start['call_key']!=key or any(end[k]!=v for k,v in start.items()):
                raise ValueError('start/completion mismatch')
            name=Path(end['record']).name
            if name in seen or name not in files:raise ValueError('duplicate/unknown record in call ledger')
            seen.add(name);row,digest=read(root/name)
            validate_record(row,deployable=key=='mechanism_full')
            if (digest!=hashes[name] or digest!=end['record_sha256'] or row['config_sha256']!=cfg
                    or row['source_sha256']!=contract['source_sha256'] or row['protocol_sha256']!=phash
                    or row['split']!='mechanism' or row['failure'] is not None
                    or row['block_id']!=start['block'] or row['SNR']!=contract['snr']):
                raise ValueError('mechanism row provenance mismatch')
            expected_arm=start['arm_id'] if key=='mechanism_full' else start['cell_id']
            if row['arm_id']!=expected_arm:raise ValueError('arm identity mismatch')
            if key=='mechanism_terminal' and (row['candidate_eligible'] is not False or row['arm_id'] not in CELLS):
                raise ValueError('factorial cells must remain diagnostic')
            records.append(row);audit_hashes[name]=digest
    return records,{'root':str(root),'complete_sha256':chash,'contract_sha256':khash,
        'record_sha256':audit_hashes,'source_sha256':contract['source_sha256'],
        'B_star_sha256':contract['B_star_sha256'],'B_star_recipe':contract['recipe'],
        'detector_reference_sha256':contract['detector_reference_sha256'],
        'calls':counts,'failure_count':0}


def paired_table(rows):
    table={}
    for row in rows:
        arm='normal' if row['call_type']=='full' else row['arm_id']
        key=(row['SNR'],row['block_id'],arm)
        if key in table:raise ValueError('duplicate mechanism identity')
        table[key]=row
    expected=set(itertools.product((7,8,9),range(256),('normal',*CELLS)))
    if set(table)!=expected:raise ValueError('requires256 blocks x3 SNR x(normal+8cells)')
    for snr,block in itertools.product((7,8,9),range(256)):
        normal=table[snr,block,'normal']
        for arm in CELLS:
            row=table[snr,block,arm]
            if row['input_hashes']!=normal['input_hashes'] or row['sigma_value']!=normal['sigma_value']:
                raise ValueError('unpaired factorial observation or non-common terminal variance')
            if row['normal_arm_reference']!=normal['arm_id']:raise ValueError('normal B-star identity changed')
            expected_h={'estimated':normal['H_data_source']['sha256'],'true':normal['H_true_hash']}
            cancel_source=row['H_cancel_source']['source'];data_source=row['H_data_source']['source']
            if (cancel_source not in SOURCES or data_source not in SOURCES
                    or row['H_cancel_source']['sha256']!=expected_h[cancel_source]
                    or row['H_data_source']['sha256']!=expected_h[data_source]
                    or row['H_cov_source']['H_sha256']!=expected_h[data_source]
                    or row['truth_access_level']!=('CSI_oracle' if 'true' in (cancel_source,data_source) else 'none')):
                raise ValueError('factorial H source/covariance/truth routing mismatch')
            if row['data_residual']['relative_vector_closure']>1e-10:
                raise ValueError('residual closure failed')
        for source in SOURCES:
            z={table[snr,block,cell(source,d,t)]['z_hash'] for d,t in itertools.product(SOURCES,DETECTORS)}
            if len(z)!=1:raise ValueError('cancelled observation changed with detector/data H')
    for block in range(256):
        reference=table[8,block,'normal']['input_hashes']
        for snr in (7,9):
            other=table[snr,block,'normal']['input_hashes']
            if any(other[k]!=reference[k] for k in ('H','info','coded','noise','pilot','data')):
                raise ValueError('cross-SNR exogenous cluster mismatch')
    return table


def describe(table,reg):
    results={}
    for snr in (7,8,9):
        arrays={a:[table[snr,b,a]['FER'] for b in range(256)] for a in CELLS}
        contrasts={}
        for detector in DETECTORS:
            hh,th,ht,tt=(arrays[cell(c,d,detector)] for c,d in
                         (('estimated','estimated'),('true','estimated'),('estimated','true'),('true','true')))
            contrasts['cancel_'+detector]=difference(th,hh)
            contrasts['data_'+detector]=difference(ht,hh)
            contrasts['interaction_'+detector]=interaction(hh,th,ht,tt,reg['bootstrap_seed_words'])
        for c,d in itertools.product(SOURCES,SOURCES):
            contrasts[f'detector_{c}_{d}']=difference(arrays[cell(c,d,'EP10')],arrays[cell(c,d,'BP')])
        summaries={}
        for arm in ('normal',*CELLS):
            rows=[table[snr,b,arm] for b in range(256)]
            costs=[r['elapsed_seconds'] for r in rows]
            summaries[arm]={'FER':sum(r['FER'] for r in rows)/256,
                'frame_errors':sum(r['FER'] for r in rows),'frames':256,
                'decoded_info_BER':sum(r['coded_bit_errors'] for r in rows)/sum(r['coded_bits_denominator'] for r in rows),
                'raw_coded_BER':sum(r['raw_bit_errors'] for r in rows)/sum(r['raw_bits_denominator'] for r in rows),
                'cost_mean':float(np.mean(costs)),'cost_p95':float(np.quantile(costs,.95)),
                'peak_gpu_bytes':max(r['peak_gpu_bytes'] for r in rows)}
            if arm!='normal':
                residuals=[r['data_residual'] for r in rows]
                summaries[arm]['residual_energy_means']={k:float(np.mean([r['energies'][k] for r in residuals])) for k in residuals[0]['energies']}
                summaries[arm]['residual_cross_means']={k:float(np.mean([r['cross_terms'][k] for r in residuals])) for k in residuals[0]['cross_terms']}
                summaries[arm]['maximum_vector_closure']=max(r['relative_vector_closure'] for r in residuals)
        base=cell('estimated','estimated','BP')
        results[str(snr)]={'contrasts':contrasts,'cells':summaries,
            'normal_vs_00BP_decoded_hash_differences':sum(table[snr,b,'normal']['hard_output_hash']!=table[snr,b,base]['hard_output_hash'] for b in range(256)),
            'normal_vs_00BP_FER_differences':sum(table[snr,b,'normal']['FER']!=table[snr,b,base]['FER'] for b in range(256)),
            'fullCSI_point_benefit':{d:summaries[cell('estimated','estimated',d)]['FER']-summaries[cell('true','true',d)]['FER'] for d in DETECTORS}}
    return results


def route_screen(results):
    c=results['8']['contrasts'];cancel=c['cancel_BP'];data=c['data_BP']
    def positive(name):return all(results[str(s)]['contrasts'][name]['benefit_delta']>=0 for s in (7,9))
    cancel_pass=cancel['benefit_delta']>=.05 and cancel['benefit_interval'][0]>0
    detectors={}
    for name in (f'detector_{a}_{b}' for a,b in itertools.product(SOURCES,SOURCES)):
        v=c[name]
        detectors[name]={'passed':v['benefit_delta']>=.05 and v['benefit_interval'][0]>0
            and v['benefit_delta']>=max(cancel['benefit_delta'],data['benefit_delta'])+.01 and positive(name),
            'uncertain':v['benefit_interval'][0]<=0<=v['benefit_interval'][1],
            'neighbor_point_directions_nonnegative':positive(name)}
    return {'cancellation_gate_passed':cancel_pass,
        'cancellation_uncertain':cancel['benefit_interval'][0]<=0<=cancel['benefit_interval'][1],
        'cancellation_neighbor_directions_nonnegative':positive('cancel_BP'),
        'detector_dominance':detectors,
        'fullCSI_exploratory_space':{d:{'benefit_8dB':results['8']['fullCSI_point_benefit'][d],
            'point_at_least_0.05':results['8']['fullCSI_point_benefit'][d]>=.05,
            'scope':'constraint for this tested reference only; not optimality or general no-space proof'} for d in DETECTORS},
        'final_route_selected':False,'scope':'Apply frozen screens only; structure experiment still required; no additive percentage attribution.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--contrast-registry',type=Path,required=True)
    p.add_argument('--run-dir',type=Path,action='append',required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();protocol,phash=read(args.protocol);registry,rhash=read(args.contrast_registry)
    validate_registry(registry,phash)
    if protocol['campaign_id']!='afdm-direction-20260908-v1':raise ValueError('wrong campaign')
    rows=[];sources=[]
    for root in args.run_dir:
        r,s=load_run(root,phash);rows.extend(r);sources.append(s)
    for s in sources[1:]:
        if any(s[k]!=sources[0][k] for k in ('source_sha256','B_star_sha256','B_star_recipe','detector_reference_sha256')):
            raise ValueError('mixed B-star/source/reference across runs')
    table=paired_table(rows);results=describe(table,registry)
    payload={'status':'complete','protocol_sha256':phash,'contrast_registry_sha256':rhash,
        'provenance':sources,'by_SNR':results,'route_screens':route_screen(results),
        'profile':{'independent_blocks':256,'SNR_records':768,'normal_calls':768,'terminal_calls':6144,
                   'records':len(rows),'failures_in_supplied_runs':0},
        'failure_scope':'Failed/incomplete supplied runs rejected; other shared-ledger campaign failures remain preserved externally.',
        'scope':'Exploratory mechanism evidence; main gate8dB; neighbors descriptive/direction screens; no M/I/T selection or BP optimality claim.'}
    args.out.parent.mkdir(parents=True,exist_ok=True);publish_json(args.out,payload)


if __name__=='__main__':main()
