"""Registered same-object, equal-node-budget LLR integration comparison."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.special import logsumexp

from experiments.afdm_higher_order_information import llr
from experiments.afdm_higher_order_information.protocol import ROOT,run,dump
from experiments.afdm_shared_channel_20261004 import probability as previous
from experiments.afdm_shared_channel_20261004.quadrature import gaussian_nodes,sphere_nodes,independent_nodes

CONFIG=dict(seed=[20261004,213705,60],new_observations=12,n=3,p=2,exogenous_draws=3,
    priors=['Gaussian','sphere'],noise=[.15,1.2],cavities=['uniform','nonuniform'],
    objects=['QPSK','Gaussian-outside'],cases=48,budgets=[256,1024,4096],replicates=4,
    arms=['fixed_common_qmc','common_prior_iid','independent_prior_iid','defensive_contrast_iid'],
    candidate_pilot_nodes=64,defensive_prior_fraction=.5,proposal_regularization=.1,
    reference=dict(gaussian_hermite_order=33,hermite_point_cap=1200000,
        sphere_orders=[13,21],sobol_exponents=[18,19],independent_sobol_exponent=19,
        llr_tolerance=.008,probability_tolerance=.002,log_density_tolerance=.015),
    precision=dict(llr_rmse=.05,llr_p95_absolute=.1,side_relative_density_rmse=.05),
    input_amplitude=.5,pilot_amplitude=.55,receiver_calls=0,decoder_calls=0,
    candidate_object='same integral; independent pilot adaptation followed by fresh defensive importance samples',
    cost='node generation, proposal fitting, all likelihood sides, covariance factorizations, raw persistence; external scoring/reference separately',
    pairing='12 y shared across object/cavity;3 shared gain/data/noise exogenous draws; no independent-frame count inflation')


def sources():
    return [__file__,Path(llr.__file__),*previous.SOURCES,
            Path(__file__).with_name('LLR.md'),Path(__file__).with_name('test_llr.py')]


def reference(y,ops,pilot,incoming,noise,prior,object_name,rules):
    local,bits=llr.enumerate_qpsk(1)
    extra=llr.log_bit_prior(bits[:,1:],incoming[[len(pilot)]])
    def reduce(score):
        return np.array([logsumexp((score+extra)[bits[:,0]==sign]) for sign in (0,1)])
    if prior=='Gaussian' and object_name=='QPSK':
        score,_,_=previous.exact_scores(y,ops,pilot,[0],incoming,noise,mean=np.zeros(2),covariance=np.eye(2)/2)
        exact=reduce(score)
        return dict(primary='analytic',values=dict(analytic=exact),converged=True,errors={})
    _,mean,cov=previous.outside_cavity(len(pilot),[0],incoming)
    values={}
    for name,(nodes,weights) in rules.items():
        if object_name=='QPSK':
            score,_,_=previous.exact_scores(y,ops,pilot,[0],incoming,noise,nodes=nodes,weights=weights)
        else:
            score=previous.conditional_scores(y,ops,pilot,local,mean,cov,[0],noise,nodes,weights)
        values[name]=reduce(score)
    primary='sobol_19' if prior=='Gaussian' else 'sphere_21'
    target=llr.ratio_result(values[primary]);errors={}
    for name,value in values.items():
        candidate=llr.ratio_result(value)
        errors[name]=dict(llr=abs(candidate['llr']-target['llr']),
            probability=float(np.max(abs(candidate['probability']-target['probability']))),
            log_density=float(np.max(abs(candidate['log_m']-target['log_m']))))
    tolerance=CONFIG['reference']
    passed=all(e['llr']<=tolerance['llr_tolerance'] and e['probability']<=tolerance['probability_tolerance']
               and e['log_density']<=tolerance['log_density_tolerance'] for e in errors.values())
    return dict(primary=primary,values=values,converged=bool(passed),errors=errors)


def message(y,ops,pilot,incoming,noise,prior,object_name,arm,budget,case,rep,output):
    started=time.perf_counter()
    arm_id=CONFIG['arms'].index(arm)
    rng=np.random.default_rng([*CONFIG['seed'],100,arm_id,budget,rep])
    raw={};ledgers=[];proposal_cost=0
    if arm=='independent_prior_iid':
        logm=[];variance=0.
        for sign in (0,1):
            z=llr.base_nodes(budget,2,rng);h=llr.gain_pushforward(z,prior)
            logf,ledger=llr.log_values(y,ops,pilot,incoming,noise,h,object_name,sign=sign)
            value=llr.log_integrals(logf);logm.append(value[0]);ledgers.append(ledger)
            variance+=float(np.var(np.exp(logf[:,0]-value[0]),ddof=1))
            raw[f'base_{sign}']=z;raw[f'logf_{sign}']=logf
        logm=np.array(logm)
    elif arm=='defensive_contrast_iid':
        # Separate pilot and main RNG streams; no pilot sample enters final means.
        pilot_rng=np.random.default_rng([*CONFIG['seed'],200,case,budget,rep])
        pilot_z=llr.base_nodes(CONFIG['candidate_pilot_nodes'],2,pilot_rng)
        pilot_f,ledger=llr.log_values(y,ops,pilot,incoming,noise,llr.gain_pushforward(pilot_z,prior),object_name)
        ledgers.append(ledger)
        proposal=llr.fit_contrast_proposal(pilot_z,pilot_f,CONFIG['proposal_regularization'])
        z,ratio,component=llr.defensive_sample(budget-CONFIG['candidate_pilot_nodes'],proposal,rng,CONFIG['defensive_prior_fraction'])
        logf,ledger=llr.log_values(y,ops,pilot,incoming,noise,llr.gain_pushforward(z,prior),object_name)
        ledgers.append(ledger);logm=llr.log_integrals(logf,ratio)
        variance=llr.iid_llr_variance(logf,logm,ratio);proposal_cost=2
        raw.update(base=z,logf=logf,log_pi_over_rho=ratio,proposal_component=component,
            pilot_base=pilot_z,pilot_logf=pilot_f,proposal_mean=proposal['mean'],proposal_covariance=proposal['covariance'],
            pilot_log_m=proposal['pilot_log_m'],degenerate_contrast=proposal['degenerate_contrast'])
    else:
        z=llr.base_nodes(budget,2,rng,'qmc' if arm=='fixed_common_qmc' else 'iid')
        logf,ledger=llr.log_values(y,ops,pilot,incoming,noise,llr.gain_pushforward(z,prior),object_name)
        ledgers.append(ledger);logm=llr.log_integrals(logf)
        variance=None if arm=='fixed_common_qmc' else llr.iid_llr_variance(logf,logm)
        raw.update(base=z,logf=logf)
    result=llr.ratio_result(logm)
    raw.update(log_m=result['log_m'],probability=result['probability'],llr=result['llr'])
    path=output/f'message_{case:02d}_{arm_id}_{budget}_{rep}.npz'
    np.savez(path,**raw)
    elapsed=time.perf_counter()-started
    cost={key:sum(item[key] for item in ledgers) for key in ('gain_nodes','word_responses','conditional_cholesky')}
    cost.update(proposal_cholesky=proposal_cost,proposal_fit=int(arm=='defensive_contrast_iid'),raw_bytes=path.stat().st_size)
    return result,dict(arm=arm,budget=budget,replicate=rep,seconds=elapsed,
        iid_asymptotic_variance_plugin=variance,variance_scope='conditional on pilot for adaptive arm; none for QMC',
        final_estimator_nodes=budget-CONFIG['candidate_pilot_nodes'] if arm=='defensive_contrast_iid' else budget,
        cost=cost,artifact=path.name)


def calculate(output):
    ref_start=time.perf_counter();rules={}
    for prior in CONFIG['priors']:
        current={}
        for exponent in CONFIG['reference']['sobol_exponents']:
            current[f'sobol_{exponent}']=independent_nodes(2,1.,exponent,[*CONFIG['seed'],30],normalized=prior=='sphere')
        current['independent']=independent_nodes(2,1.,CONFIG['reference']['independent_sobol_exponent'],[*CONFIG['seed'],31],normalized=prior=='sphere')
        if prior=='Gaussian':
            current['hermite_33']=gaussian_nodes(np.zeros(2),np.eye(2)/2,CONFIG['reference']['gaussian_hermite_order'],max_points=CONFIG['reference']['hermite_point_cap'])
        else:
            for order in CONFIG['reference']['sphere_orders']: current[f'sphere_{order}']=sphere_nodes(2,1.,order)
        rules[prior]=current
        for name,(nodes,w) in current.items(): np.savez(output/f'reference_nodes_{prior}_{name}.npz',nodes=nodes,weights=w)
    reference_node_setup_seconds=time.perf_counter()-ref_start
    words,_=llr.enumerate_qpsk(CONFIG['n']);cases=[];messages=[];reference_seconds=0.
    geometry_started=time.perf_counter()
    n=CONFIG['n'];pilot=CONFIG['pilot_amplitude']*np.exp(.4j*np.arange(n))
    channel=previous.PHYSICAL.Channel(n,.37/n,.13/n**2,[0,1],[.23,-.38],[1,1])
    ops=previous.dense_operators(channel)
    geometry_setup_seconds=time.perf_counter()-geometry_started
    for draw in range(CONFIG['exogenous_draws']):
        rng=np.random.default_rng([*CONFIG['seed'],draw])
        base=llr.base_nodes(1,2,rng);data=words[rng.integers(len(words))]
        noise_unit=llr.base_nodes(1,n,rng)[0]
        for prior in CONFIG['priors']:
            h=llr.gain_pushforward(base,prior)[0]
            for noise in CONFIG['noise']:
                y=np.einsum('p,pij,j->i',h,ops,pilot+data)+np.sqrt(noise)*noise_unit
                observation=f'{draw}_{prior}_{noise}'
                np.savez(output/f'observation_{observation}.npz',y=y,operators=ops,pilot=pilot,
                         truth_gain=h,truth_data=data,base=base,noise_unit=noise_unit,noise=noise)
                for cavity in CONFIG['cavities']:
                    incoming=np.zeros(2*n) if cavity=='uniform' else np.array([.7,-.8,.4,-.3,.5,-.6])
                    for object_name in CONFIG['objects']:
                        index=len(cases);started=time.perf_counter()
                        ref=reference(y,ops,pilot,incoming,noise,prior,object_name,rules[prior])
                        reference_seconds+=time.perf_counter()-started
                        target=llr.ratio_result(ref['values'][ref['primary']])
                        np.savez(output/f'reference_{index:02d}.npz',incoming=incoming,
                            **{'log_m_'+name:value for name,value in ref['values'].items()})
                        cases.append(dict(case=index,draw=draw,prior=prior,noise=noise,cavity=cavity,object=object_name,
                            observation=observation,reference_primary=ref['primary'],reference_converged=ref['converged'],
                            reference_errors=ref['errors']))
                        for budget in CONFIG['budgets']:
                            for rep in range(CONFIG['replicates']):
                                for arm in CONFIG['arms']:
                                    result,record=message(y,ops,pilot,incoming,noise,prior,object_name,arm,budget,index,rep,output)
                                    record.update(case=index,prior=prior,object=object_name,reference_converged=ref['converged'],
                                        llr_error=result['llr']-target['llr'],
                                        probability_error=float(result['probability'][0]-target['probability'][0]),
                                        side_relative_density_error=np.expm1(result['log_m']-target['log_m']).tolist(),
                                        side_log_density_error=(result['log_m']-target['log_m']).tolist())
                                    messages.append(record)
    if len(cases)!=CONFIG['cases']: raise AssertionError('case allocation mismatch')
    dump(output/'raw.json',dict(cases=cases,messages=messages))
    summaries=[]
    for object_name in CONFIG['objects']:
        for prior in CONFIG['priors']:
            for arm in CONFIG['arms']:
                for budget in CONFIG['budgets']:
                    subset=[m for m in messages if m['prior']==prior and m['object']==object_name and m['arm']==arm and m['budget']==budget]
                    errors=np.array([m['llr_error'] for m in subset]);density=np.array([m['side_relative_density_error'] for m in subset])
                    rmse=float(np.sqrt(np.mean(errors**2)));p95=float(np.quantile(abs(errors),.95));drmse=float(np.sqrt(np.mean(density**2)))
                    summaries.append(dict(prior=prior,object=object_name,arm=arm,budget=budget,messages=len(subset),
                        llr_rmse=rmse,llr_p95_absolute=p95,side_relative_density_rmse=drmse,
                        probability_rmse=float(np.sqrt(np.mean([m['probability_error']**2 for m in subset]))),
                        mean_complete_message_seconds=float(np.mean([m['seconds'] for m in subset])),
                        precision_pass=bool(rmse<=CONFIG['precision']['llr_rmse'] and p95<=CONFIG['precision']['llr_p95_absolute'] and drmse<=CONFIG['precision']['side_relative_density_rmse'])))
    matched=[]
    for object_name in CONFIG['objects']:
        for prior in CONFIG['priors']:
            for arm in CONFIG['arms']:
                admissible=[s for s in summaries if s['prior']==prior and s['object']==object_name and s['arm']==arm and s['precision_pass']]
                selected=min(admissible,key=lambda s:s['mean_complete_message_seconds']) if admissible else None
                matched.append(dict(prior=prior,object=object_name,arm=arm,
                    selection='cheapest measured full-grid precision-admitted budget; no sample subset',selected=selected,
                    reference_admitted=all(c['reference_converged'] for c in cases if c['prior']==prior and c['object']==object_name)))
    return dict(status='all_cases_and_messages_retained',cases=len(cases),new_observations=12,messages=len(messages),
        nonconverged_references=sum(not c['reference_converged'] for c in cases),summaries=summaries,
        matched_precision=matched,one_time_fixed_geometry_setup_seconds=geometry_setup_seconds,
        reference_node_setup_seconds=reference_node_setup_seconds,reference_seconds=reference_seconds,
        complete_message_seconds=sum(m['seconds'] for m in messages),
        no_positive_claim='same-object controlled numerical comparison; QMC uses empirical refinement, no IID CLT; sphere not actual production prior')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='llr_v1');args=parser.parse_args()
    run(args.stage,CONFIG,sources(),calculate,wall_seconds=600)
