"""Fixed-prior refinement of the complete saved cohort; original attempt retained."""
import argparse
import copy
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_shared_channel_20261004 import probability as p
from experiments.afdm_shared_channel_20261004.common import ARTIFACT, ROOT, run, dump, hashes
from experiments.afdm_shared_channel_20261004.quadrature import independent_nodes, gaussian_nodes

CONFIG = dict(seed=[20261004,110000,21], source_stage='probability_v1', expected_cases=96,
    recompute='all 48 Gaussian-prior rows, both noise levels; retain admitted 48 sphere rows',
    primary_sobol_exponents=[16,17,18], independent_sobol_exponent=18,
    hermite_orders={1:[65,97],2:[25]}, hermite_point_cap=500000,
    tolerance=copy.deepcopy({k:v for k,v in p.CONFIG.items() if 'tolerance' in k}),
    base_orders=[65,97], receiver_calls=0,
    gate='last Sobol refinement AND independent scramble AND highest Hermite rule; all original rows retained')


def source_paths():
    directory=ARTIFACT/'execution'/CONFIG['source_stage']
    return [__file__,*p.SOURCES,directory/'registration.json',directory/'attempt.json',
            directory/'results.json',directory/'raw.json',directory/'base_cases.json',
            *sorted(directory.glob('case_*.npz')),*sorted(directory.glob('base_*.npz'))]


def admitted_input(directory):
    attempt=json.loads((directory/'attempt.json').read_text())
    if attempt['status']!='complete':
        raise ValueError('source stage must have a complete preserved attempt')
    actual=hashes(ROOT/key for key in attempt['artifact_sha256'])
    if actual!=attempt['artifact_sha256']:
        raise ValueError('source artifact hash mismatch')
    rows=json.loads((directory/'raw.json').read_text())['cases']
    if len(rows)!=CONFIG['expected_cases'] or [r['case'] for r in rows]!=list(range(CONFIG['expected_cases'])):
        raise ValueError('source cohort is incomplete or reordered')
    return rows


def differences(fine,other):
    return dict(probability=float(np.max(abs(fine['probability']-other['probability']))),
                llr=float(np.max(abs(fine['llr']-other['llr']))))


def converged(errors):
    tolerance=CONFIG['tolerance']
    return (errors['refinement']['probability']<=tolerance['refinement_probability_tolerance']
        and errors['refinement']['llr']<=tolerance['refinement_llr_tolerance']
        and all(errors[key]['probability']<=tolerance['independent_probability_tolerance']
            and errors[key]['llr']<=tolerance['independent_llr_tolerance'] for key in ('independent','Hermite')))


def refined_bases(source,output):
    original=json.loads((source/'base_cases.json').read_text())
    rows=[]
    for row in original:
        if row['prior']!='Gaussian':
            rows.append(dict(**row,disposition='reuse_preserved_base'))
            continue
        with np.load(source/f"base_{row['case']:02d}.npz") as data:
            y,ops,pilot,incoming,block,noise=(data[k] for k in ('y','operators','pilot','incoming','block','noise'))
            local,bits=p.enumerate_qpsk(len(block)); _,m,v=p.outside_cavity(len(pilot),block,incoming)
            reference=data['score_qpsk_fine'].copy(); exact=p.normalized(reference,bits)
            scores={}; result=[]
            for order in CONFIG['base_orders']:
                nodes,w=gaussian_nodes([0],[[1]],order)
                score=p.conditional_scores(y,ops,pilot,local,m,v,block,noise,nodes,w)
                scores[f'mix_{order}']=score
                result.append(dict(order=order,max_qpsk_probability_difference=float(np.max(abs(p.normalized(score,bits)['probability']-exact['probability']))),
                    max_qpsk_logscore_difference=float(np.max(abs(score-reference)))))
            fine=p.normalized(scores[f"mix_{CONFIG['base_orders'][-1]}"],bits)
            coarse=p.normalized(scores[f"mix_{CONFIG['base_orders'][-2]}"],bits)
            row=dict(**row,disposition='refined_Gaussian_base',refined=result,refinement=differences(fine,coarse))
            np.savez(output/f"base_{row['case']:02d}.npz",y=y,operators=ops,pilot=pilot,incoming=incoming,
                     block=block,noise=noise,reference=reference,**scores)
            rows.append(row)
    dump(output/'base_cases.json',rows)
    return rows


def calculate(output):
    source=ARTIFACT/'execution'/CONFIG['source_stage']
    original=admitted_input(source)
    # Rules fixed and saved before reading any observation payload.
    rules={}
    for paths in (1,2):
        for exponent in CONFIG['primary_sobol_exponents']:
            rules[paths,f'sobol_{exponent}']=independent_nodes(paths,1.,exponent,[*CONFIG['seed'],paths,0])
        rules[paths,'independent']=independent_nodes(paths,1.,CONFIG['independent_sobol_exponent'],[*CONFIG['seed'],paths,1])
        for order in CONFIG['hermite_orders'][paths]:
            rules[paths,f'hermite_{order}']=gaussian_nodes(np.zeros(paths),np.eye(paths)/paths,order,max_points=CONFIG['hermite_point_cap'])
        for (rule_p,name),(nodes,w) in list(rules.items()):
            if rule_p==paths: np.savez(output/f'nodes_{paths}_{name}.npz',nodes=nodes,weights=w)
    rows=[]
    for old in original:
        row=copy.deepcopy(old)
        filename=f"case_{old['case']:03d}.npz"
        row['source_artifact']=str((source/filename).relative_to(ROOT))
        if old['prior']=='normalized':
            if not old['numerical_converged']:
                raise ValueError('an unqualified sphere row cannot be reused as converged')
            row['disposition']='reuse_preserved_converged_sphere_row'
            rows.append(row)
            continue
        started=time.perf_counter()
        with np.load(source/filename) as data:
            y,ops,pilot,incoming,block,local,bits,truth=(data[key] for key in (
                'y','operators','pilot','incoming','block','local_words','local_bits','truth_bits'))
            _,m,v=p.outside_cavity(len(pilot),block,incoming)
            all_scores={name:p.conditional_scores(y,ops,pilot,local,m,v,block,old['noise'],nodes,w)
                        for (paths,name),(nodes,w) in rules.items() if paths==old['p']}
            all_scores['exact_analytic']=data['scores_exact_analytic'].copy()
            all_scores['mm']=data['scores_mm'].copy()
            values={name:p.normalized(score,bits) for name,score in all_scores.items()}
            high=f"sobol_{CONFIG['primary_sobol_exponents'][-1]}"
            low=f"sobol_{CONFIG['primary_sobol_exponents'][-2]}"
            hermite=f"hermite_{CONFIG['hermite_orders'][old['p']][-1]}"
            ref,mix,mm=(values[name] for name in ('exact_analytic',high,'mm'))
            met={name:p.metrics(ref,value,truth) for name,value in values.items()}
            errors=dict(refinement=differences(mix,values[low]),independent=differences(mix,values['independent']),
                        Hermite=differences(mix,values[hermite]))
            step1,step2=mix['llr']-ref['llr'],mm['llr']-mix['llr']
            raw={key:data[key] for key in data.files if not any(key.startswith(prefix) for prefix in
                 ('scores_','probability_','logp_','llr_','bit0_'))}
            raw.update(step1_llr=step1,step2_llr=step2)
            local_incoming=incoming[np.r_[block,block+len(pilot)]]
            raw['extrinsic']=p.block_extrinsic(all_scores[high],bits,local_incoming)
            for name in all_scores:
                raw['scores_'+name]=all_scores[name]
                raw.update({key+'_'+name:value for key,value in values[name].items()})
            np.savez(output/filename,**raw)
            row.update(disposition='refined_all_Gaussian_rows',reference='exact_analytic',primary_mixture=high,
                metrics=met,numerical_converged=bool(converged(errors)),integration_errors=errors,
                paired_mm_minus_mix={key:met['mm'][key]-met[high][key] for key in met['mm']},
                approximation_steps=dict(outside_gaussian_llr_rmse=float(np.sqrt(np.mean(step1**2))),
                    shared_gain_projection_llr_rmse=float(np.sqrt(np.mean(step2**2))),
                    llr_error_cross_term=float(2*np.mean(step1*step2)),
                    opposing_error_coordinates=int(np.count_nonzero(step1*step2<0)),
                    projection_sign_changes=int(np.count_nonzero((mm['llr']>=0)!=(mix['llr']>=0)))),
                seconds=time.perf_counter()-started,original_integration_errors=old['integration_errors'])
            rows.append(row)
    bases=refined_bases(source,output)
    dump(output/'raw.json',dict(cases=rows))
    groups=[]
    for prior in ('Gaussian','normalized'):
        subset=[row for row in rows if row['prior']==prior]
        groups.append(dict(prior=prior,cases=len(subset),nonconverged=sum(not row['numerical_converged'] for row in subset),
            mm_better_block_kl=sum(row['paired_mm_minus_mix']['block_kl']<0 for row in subset),
            mix_better_block_kl=sum(row['paired_mm_minus_mix']['block_kl']>0 for row in subset),
            cancellation_cases=sum(row['approximation_steps']['llr_error_cross_term']<0 for row in subset),
            mean_paired_mm_minus_mix={key:float(np.mean([row['paired_mm_minus_mix'][key] for row in subset])) for key in subset[0]['paired_mm_minus_mix']}))
    return dict(status='all_original_rows_accounted',cases=len(rows),recomputed_Gaussian=48,reused_sphere=48,
        source_stage=CONFIG['source_stage'],nonconverged=sum(not row['numerical_converged'] for row in rows),
        groups=groups,base_cases=bases,interpretation='bounded paired approximation diagnostic; original failed refinements retained; no production inference')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',default='probability_refined_v1')
    args=parser.parse_args()
    run(args.stage,CONFIG,source_paths(),calculate)
