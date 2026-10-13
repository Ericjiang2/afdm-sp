"""Independent saved-node correction, population, cost and precision recount."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from experiments.afdm_higher_order_information.protocol import ROOT,ARTIFACT,run,dump,hashes
from experiments.afdm_higher_order_information.llr_study import CONFIG as STUDY_CONFIG

CONFIG=dict(seed=[20261004,213705,61],new_observations=0,new_nodes=0,source_stage='llr_v1',
    cases=48,messages=2304,observations=12,replay_tolerance=2e-11,
    receiver_calls=0,decoder_calls=0,
    sensitivity='each stored admitted reference and full-population fixed thresholds; no threshold relaxation')


def stable_log_average(values):
    values=np.asarray(values,float)
    if values.ndim!=2 or min(values.shape)<1 or not np.isfinite(values).all():
        raise ValueError('finite nonempty likelihood array required')
    maximum=np.max(values,axis=0)
    return maximum+np.log(np.mean(np.exp(values-maximum),axis=0))


def independent_log_ratio(nodes,mean,covariance,alpha):
    """Dense inverse/slogdet path, independent of producing Cholesky routine."""
    nodes=np.asarray(nodes,complex);mean=np.asarray(mean,complex);covariance=np.asarray(covariance,complex)
    if not 0<alpha<=1 or not np.isfinite(nodes).all() or not np.isfinite(mean).all() or not np.isfinite(covariance).all():
        raise ValueError('invalid defensive proposal')
    if not np.allclose(covariance,covariance.conj().T,atol=1e-13,rtol=1e-13) or np.linalg.eigvalsh(covariance).min()<=0:
        raise ValueError('proposal covariance must be Hermitian positive definite')
    p=len(mean); residual=nodes-mean
    logpi=-p*np.log(np.pi)-np.sum(abs(nodes)**2,axis=1)
    sign,logdet=np.linalg.slogdet(covariance)
    if abs(sign-1)>1e-12: raise ValueError('invalid covariance determinant')
    logq=-p*np.log(np.pi)-logdet-np.einsum('ni,ij,nj->n',residual.conj(),np.linalg.inv(covariance),residual).real
    logrho=logpi if alpha==1 else np.logaddexp(np.log(alpha)+logpi,np.log1p(-alpha)+logq)
    return logpi-logrho


def validate_population(cases,messages):
    if len(cases)!=CONFIG['cases'] or [c['case'] for c in cases]!=list(range(CONFIG['cases'])):
        raise ValueError('missing or reordered cases')
    if len({c['observation'] for c in cases})!=CONFIG['observations']:
        raise ValueError('observation allocation mismatch')
    if any(sum(c['observation']==obs for c in cases)!=4 for obs in {c['observation'] for c in cases}):
        raise ValueError('each observation must have four object/cavity cases')
    expected=set(itertools.product(range(CONFIG['cases']),STUDY_CONFIG['arms'],STUDY_CONFIG['budgets'],range(STUDY_CONFIG['replicates'])))
    actual=[(m['case'],m['arm'],m['budget'],m['replicate']) for m in messages]
    if len(actual)!=CONFIG['messages'] or len(set(actual))!=len(actual) or set(actual)!=expected:
        raise ValueError('missing or duplicated message population')


def quality(logm,reference):
    logm,reference=np.asarray(logm),np.asarray(reference)
    errors=(logm[:,0]-logm[:,1])-(reference[:,0]-reference[:,1])
    relative=np.expm1(logm-reference)
    metrics=dict(llr_rmse=float(np.sqrt(np.mean(errors**2))),
        llr_p95_absolute=float(np.quantile(abs(errors),.95)),
        side_relative_density_rmse=float(np.sqrt(np.mean(relative**2))))
    metrics['precision_pass']=all(metrics[k]<=STUDY_CONFIG['precision'][k] for k in STUDY_CONFIG['precision'])
    return metrics


def classification(variants):
    values=[value['precision_pass'] for value in variants.values()]
    return 'stable_pass' if all(values) else 'stable_fail' if not any(values) else 'reference_sensitive'


def sources():
    source=ARTIFACT/CONFIG['source_stage']
    return [__file__,Path(__file__).with_name('test_llr_recount.py'),
        Path(__file__).with_name('llr_study.py'),Path(__file__).with_name('llr.py'),
        source/'attempt.json',source/'registration.json',source/'raw.json',source/'results.json']


def calculate(output):
    source=ARTIFACT/CONFIG['source_stage']
    attempt=json.loads((source/'attempt.json').read_text())
    if attempt['status']!='complete' or hashes(ROOT/key for key in attempt['artifact_sha256'])!=attempt['artifact_sha256']:
        raise ValueError('source artifact or terminal status mismatch')
    raw=json.loads((source/'raw.json').read_text());cases,messages=raw['cases'],raw['messages']
    validate_population(cases,messages)
    if not all(c['reference_converged'] for c in cases): raise ValueError('a source reference was not admitted')
    references={};observations={};replayed=[];max_ratio_error=0.;max_logm_error=0.;max_probability_error=0.
    for case in cases:
        with np.load(source/f"reference_{case['case']:02d}.npz") as data:
            references[case['case']]={key.removeprefix('log_m_'):data[key].copy() for key in data.files if key.startswith('log_m_')}
    for name in sorted({case['observation'] for case in cases}):
        path=source/f'observation_{name}.npz'
        with np.load(path) as data:
            y=data['y']; observations[name]=dict(artifact=str(path.relative_to(ROOT)),
                y_sha256=__import__('hashlib').sha256(np.ascontiguousarray(y).tobytes()).hexdigest(),
                dtype=str(y.dtype),shape=list(y.shape))
    for record in messages:
        file=source/record['artifact'];budget=record['budget'];arm=record['arm']
        with np.load(file) as data:
            if arm=='independent_prior_iid':
                actual=np.array([stable_log_average(data[f'logf_{j}'])[0] for j in (0,1)])
                if any(len(data[f'base_{j}'])!=budget for j in (0,1)): raise ValueError('independent node count mismatch')
            else:
                correction=np.zeros(len(data['base']))
                expected=budget
                if arm=='defensive_contrast_iid':
                    expected-=STUDY_CONFIG['candidate_pilot_nodes']
                    if len(data['pilot_base'])!=STUDY_CONFIG['candidate_pilot_nodes']:
                        raise ValueError('pilot budget mismatch')
                    correction=independent_log_ratio(data['base'],data['proposal_mean'],data['proposal_covariance'],STUDY_CONFIG['defensive_prior_fraction'])
                    max_ratio_error=max(max_ratio_error,float(np.max(abs(correction-data['log_pi_over_rho']))))
                    if np.max(correction)>-np.log(STUDY_CONFIG['defensive_prior_fraction'])+CONFIG['replay_tolerance']:
                        raise ValueError('defensive support bound violated')
                if len(data['base'])!=expected: raise ValueError('final node count mismatch')
                actual=stable_log_average(data['logf']+correction[:,None])
            max_logm_error=max(max_logm_error,float(np.max(abs(actual-data['log_m']))))
            scaled=np.exp(actual-actual.max());probability=scaled/scaled.sum()
            max_probability_error=max(max_probability_error,float(np.max(abs(probability-data['probability']))))
            if abs(float(actual[0]-actual[1])-float(data['llr']))>CONFIG['replay_tolerance']:
                raise ValueError('LLR replay mismatch')
            original=references[record['case']][cases[record['case']]['reference_primary']]
            if abs(record['llr_error']-((actual[0]-actual[1])-(original[0]-original[1])))>CONFIG['replay_tolerance']:
                raise ValueError('saved error does not match its reference')
            leaf=(4**STUDY_CONFIG['n'] if record['object']=='QPSK' else 4)*budget
            expected_nodes=(2 if arm=='independent_prior_iid' else 1)*budget
            expected_cholesky=expected_nodes if record['object']=='Gaussian-outside' else 0
            cost=record['cost']
            if (cost['word_responses']!=leaf or cost['gain_nodes']!=expected_nodes
                    or cost['conditional_cholesky']!=expected_cholesky or cost['raw_bytes']!=file.stat().st_size
                    or cost['proposal_cholesky']!=(2 if arm=='defensive_contrast_iid' else 0)
                    or not np.isfinite(record['seconds']) or record['seconds']<=0):
                raise ValueError('cost or full-work ledger mismatch')
            replayed.append(dict(**record,recount_log_m=actual.tolist()))
    if max(max_ratio_error,max_logm_error,max_probability_error)>CONFIG['replay_tolerance']:
        raise ValueError('numeric replay contract failed')
    original_summary=json.loads((source/'results.json').read_text());groups=[];primary_metric_error=0.
    for row in original_summary['summaries']:
        subset=[r for r in replayed if all(r[k]==row[k] for k in ('prior','object','arm','budget'))]
        names=set.intersection(*(set(references[r['case']]) for r in subset))
        values=np.array([r['recount_log_m'] for r in subset]);variants={}
        for name in sorted(names):
            refs=np.array([references[r['case']][name] for r in subset])
            variants[name]=quality(values,refs)
        primary_refs=np.array([references[r['case']][cases[r['case']]['reference_primary']] for r in subset])
        primary=quality(values,primary_refs)
        primary_metric_error=max(primary_metric_error,max(abs(primary[k]-row[k]) for k in STUDY_CONFIG['precision']))
        groups.append(dict(prior=row['prior'],object=row['object'],arm=row['arm'],budget=row['budget'],
            messages=len(subset),variants=variants,classification=classification(variants),
            empirical_reference_envelope={key:[min(v[key] for v in variants.values()),max(v[key] for v in variants.values())] for key in STUDY_CONFIG['precision']},
            mean_complete_message_seconds=float(np.mean([r['seconds'] for r in subset]))))
    if primary_metric_error>CONFIG['replay_tolerance']: raise ValueError('full-group quality recount mismatch')
    cost_total=sum(r['seconds'] for r in replayed)
    if abs(cost_total-original_summary['complete_message_seconds'])>CONFIG['replay_tolerance']:
        raise ValueError('complete message cost total mismatch')
    matched=[]
    for prior,object_name,arm in itertools.product(STUDY_CONFIG['priors'],STUDY_CONFIG['objects'],STUDY_CONFIG['arms']):
        eligible=[g for g in groups if g['prior']==prior and g['object']==object_name and g['arm']==arm and g['classification']=='stable_pass']
        selected=min(eligible,key=lambda g:g['mean_complete_message_seconds']) if eligible else None
        matched.append(dict(prior=prior,object=object_name,arm=arm,selected=selected))
    dump(output/'raw.json',dict(groups=groups,observations=observations,messages=replayed))
    return dict(status='complete_independent_saved_recount',cases=len(cases),messages=len(messages),observations=len(observations),
        new_nodes=0,new_observations=0,source_artifacts_verified=len(attempt['artifact_sha256']),
        max_ratio_replay_error=max_ratio_error,max_logm_replay_error=max_logm_error,max_probability_replay_error=max_probability_error,
        max_primary_group_metric_error=primary_metric_error,complete_message_seconds=cost_total,
        reference_sensitive_groups=[g for g in groups if g['classification']=='reference_sensitive'],
        matched_precision=matched,all_groups=groups,
        interpretation='same-object full-population precision and saved complete message costs; empirical reference sensitivity, no timing confidence claim')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='llr_recount_v1');args=parser.parse_args()
    run(args.stage,CONFIG,sources(),calculate)
