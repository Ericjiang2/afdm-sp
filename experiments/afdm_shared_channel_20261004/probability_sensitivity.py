"""Saved-score numerical sensitivity; no receiver, generation or integration calls."""
import argparse
import json
from pathlib import Path

import numpy as np

from experiments.afdm_shared_channel_20261004 import probability as p
from experiments.afdm_shared_channel_20261004.common import ROOT, ARTIFACT, run, dump, hashes

CONFIG=dict(seed=[20261004,110000,22],source_stages=['probability_v1','probability_refined_v1'],
    cases=96,Gaussian_rules=['sobol_17','sobol_18','independent','highest_Hermite'],
    sphere_rules=['9','13','independent'],sphere_rule_combinations='all 3 x 3 QPSK/mix combinations',
    sign_roundoff_floor=1e-10,
    interval='observed-rule envelope, not a confidence interval or rigorous error bound',
    integrations=0,receiver_calls=0)


def verify(directory):
    attempt=json.loads((directory/'attempt.json').read_text())
    if attempt['status']!='complete' or hashes(ROOT/key for key in attempt['artifact_sha256'])!=attempt['artifact_sha256']:
        raise ValueError('source attempt incomplete or artifact hash mismatch')


def envelope(values):
    lo,hi=float(min(values)),float(max(values))
    floor=CONFIG['sign_roundoff_floor']
    return dict(min=lo,max=hi,sign='positive' if lo>floor else 'negative' if hi<-floor else 'unresolved')


def paths():
    source=ARTIFACT/'execution'/'probability_v1'
    refined=ARTIFACT/'execution'/'probability_refined_v1'
    return [__file__,*p.SOURCES,source/'attempt.json',refined/'attempt.json',refined/'raw.json',
            refined/'base_cases.json',*source.glob('case_*.npz'),*refined.glob('case_*.npz')]


def calculate(output):
    source=ARTIFACT/'execution'/'probability_v1'
    refined=ARTIFACT/'execution'/'probability_refined_v1'
    verify(source); verify(refined)
    records=json.loads((refined/'raw.json').read_text())['cases']
    if len(records)!=CONFIG['cases'] or not all(r['numerical_converged'] for r in records):
        raise ValueError('sensitivity requires the complete admitted cohort')
    rows=[]
    for row in records:
        base=refined if row['prior']=='Gaussian' else source
        file=base/f"case_{row['case']:03d}.npz"
        with np.load(file) as raw:
            bits,truth=raw['local_bits'],raw['truth_bits']
            mm=p.normalized(raw['scores_mm'],bits)
            if row['prior']=='Gaussian':
                references=['exact_analytic']
                mixtures=['sobol_17','sobol_18','independent',f"hermite_{97 if row['p']==1 else 25}"]
            else:
                references=[f'qpsk_{order}' for order in CONFIG['sphere_rules']]
                mixtures=[f'mix_{order}' for order in CONFIG['sphere_rules']]
            variants=[]
            for refname in references:
                ref=p.normalized(raw['scores_'+refname],bits)
                mm_metrics=p.metrics(ref,mm,truth)
                for mixname in mixtures:
                    mix=p.normalized(raw['scores_'+mixname],bits)
                    mix_metrics=p.metrics(ref,mix,truth)
                    step1,step2=mix['llr']-ref['llr'],mm['llr']-mix['llr']
                    variants.append(dict(reference=refname,mixture=mixname,
                        delta={key:mm_metrics[key]-mix_metrics[key] for key in mm_metrics},
                        llr_cross_term=float(2*np.mean(step1*step2)),
                        mixture_metrics=mix_metrics,mm_metrics=mm_metrics))
            ranges={key:envelope([v['delta'][key] for v in variants]) for key in variants[0]['delta']}
            cross=envelope([v['llr_cross_term'] for v in variants])
            rows.append(dict(case=row['case'],prior=row['prior'],p=row['p'],noise=row['noise'],
                cavity=row['cavity'],block_size=row['block_size'],draw=row['draw'],artifact=str(file.relative_to(ROOT)),
                delta_envelope=ranges,cancellation_envelope=cross,variants=variants))
    groups=[]
    for prior in ('Gaussian','normalized'):
        subset=[row for row in rows if row['prior']==prior]
        metrics={}
        for key in subset[0]['delta_envelope']:
            lower=float(np.mean([row['delta_envelope'][key]['min'] for row in subset]))
            upper=float(np.mean([row['delta_envelope'][key]['max'] for row in subset]))
            metrics[key]=dict(mean_delta_observed_rule_envelope=[lower,upper],
                stable_mixture_better=sum(row['delta_envelope'][key]['sign']=='positive' for row in subset),
                stable_mm_better=sum(row['delta_envelope'][key]['sign']=='negative' for row in subset),
                sign_unresolved=sum(row['delta_envelope'][key]['sign']=='unresolved' for row in subset))
        worse=[row for row in subset if row['delta_envelope']['block_kl']['sign']=='negative']
        better=[row for row in subset if row['delta_envelope']['block_kl']['sign']=='positive']
        cancellation=[row for row in subset if row['cancellation_envelope']['sign']=='negative']
        examples={}
        if worse:
            example=min(worse,key=lambda row:row['delta_envelope']['block_kl']['max'])
            examples['mixture_worse']={key:example[key] for key in ('case','artifact','delta_envelope','cancellation_envelope')}
        if better:
            example=max(better,key=lambda row:row['delta_envelope']['block_kl']['min'])
            examples['mixture_better']={key:example[key] for key in ('case','artifact','delta_envelope','cancellation_envelope')}
        if cancellation:
            example=min(cancellation,key=lambda row:row['cancellation_envelope']['max'])
            examples['error_cancellation']={key:example[key] for key in ('case','artifact','delta_envelope','cancellation_envelope')}
        groups.append(dict(prior=prior,cases=len(subset),metrics=metrics,
            stable_cancellation_cases=len(cancellation),cancellation_unresolved=sum(row['cancellation_envelope']['sign']=='unresolved' for row in subset),
            robust_examples=examples))
    # Old base fields remain in immutable evidence. Export only clearly named latest fields.
    latest_bases=[]
    for row in json.loads((refined/'base_cases.json').read_text()):
        if row['prior']=='Gaussian':
            latest_bases.append(dict(case=row['case'],prior=row['prior'],block_size=row['block_size'],noise=row['noise'],
                latest_refined=row['refined'][-1],latest_refinement=row['refinement'],
                old_top_level_fields='historical only; excluded from latest values'))
        else:
            latest_bases.append(row)
    dump(output/'raw.json',dict(cases=rows,latest_bases=latest_bases))
    return dict(status='complete_saved_score_sensitivity',cases=len(rows),groups=groups,latest_bases=latest_bases,
        delta_orientation='MM minus mixture: positive means mixture better for loss/error metrics',
        uncertainty='observed numerical-rule envelope only; 3 exogenous draws, no confidence or population claim',
        actual_production_prior='sphere is a controlled prior; actual G0-operator normalization handled separately')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',default='probability_sensitivity_v1')
    args=parser.parse_args()
    run(args.stage,CONFIG,paths(),calculate)
