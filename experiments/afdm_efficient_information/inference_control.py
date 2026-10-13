"""Unknown-nuisance control detection/estimation on one frozen physical grid."""
import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_efficient_information.features import observed_features,expected_features
from experiments.afdm_efficient_information.features_study import sample_control,plain
from experiments.afdm_efficient_information.inference import (
    MomentBank,aggregate_rows,calibrate,evaluate_grid,load_score_model,
)
from experiments.afdm_higher_order_information.moments import FiniteControl
from experiments.afdm_higher_order_information.theory_study import independent_log_density,independent_words,independent_transform

ROOT=Path(__file__).resolve().parents[2]
CONFIG_PATH=ROOT/'results/afdm_efficient_information/INFERENCE_CONTROL_CONFIG.json'


def calculate(output):
    from experiments.afdm_efficient_information.protocol import dump
    config=json.loads(CONFIG_PATH.read_text()); start=time.perf_counter(); model=FiniteControl.uniform(config['n'])
    candidates=np.array(list(itertools.product(config['q'],config['mu'],config['tau'],config['noise'])))
    null=np.flatnonzero(candidates[:,0]==0); repeats=config['repeats']; max_r=max(repeats)
    score_model=load_score_model(ROOT/config['score_model'])
    methods=['old_T','powers','phase','score4','exact','second_gaussian']
    means={level:[] for level in ['old_T','powers','phase','score4']}; mean_start=time.perf_counter()
    for theta in candidates:
        current=expected_features(model.covariances(*theta),model.weights)
        for level in ['old_T','powers','phase']: means[level].append(current[level])
        means['score4'].append(score_model.predict(current['phase'][None])[0])
    means={k:np.array(v) for k,v in means.items()}
    construction_seconds=time.perf_counter()-mean_start
    ytrain=[]; train_truth=[]; generation_costs=[]; observation_count=0
    for condition in null:
        before=time.perf_counter(); y,audit=sample_control(model,candidates[condition],config['training_per_null'],[*config['seed'],0,int(condition)])
        generation_costs.append(dict(split='training',condition=int(condition),seconds=time.perf_counter()-before))
        ytrain.append(y); train_truth.extend([condition]*len(y)); observation_count+=len(y)
    ytrain=np.concatenate(ytrain); train_truth=np.array(train_truth)
    train_f,train_feature_cost=observed_features(ytrain); train_f['score4']=score_model.predict(train_f['phase'])
    banks={}; setup=[]
    for level in means:
        banks[level]=MomentBank(train_f[level],means[level][train_truth],means[level])
        setup.append(dict(method=level,**banks[level].cost))
        np.savez(output/f'bank_{level}.npz',**banks[level].state(),candidate_means=means[level])
    np.savez(output/'training.npz',y=ytrain,condition_indices=train_truth,candidates=candidates)
    all_y=[]; slices={}; cursor=0
    for split,groups in [('calibration',config['calibration_groups']),('evaluation',config['evaluation_groups'])]:
        split_index=1 if split=='calibration' else 2
        for condition,theta in enumerate(candidates):
            before=time.perf_counter(); y,_=sample_control(model,theta,groups*max_r,[*config['seed'],split_index,condition])
            generation_costs.append(dict(split=split,condition=condition,seconds=time.perf_counter()-before))
            all_y.append(y); slices[split,condition]=(cursor,cursor+len(y)); cursor+=len(y); observation_count+=len(y)
    y=np.concatenate(all_y)
    np.savez(output/'inference_observations.npz',y=y,candidates=candidates,
        calibration_slices=np.array([slices['calibration',j] for j in range(len(candidates))]),
        evaluation_slices=np.array([slices['evaluation',j] for j in range(len(candidates))]))
    f,feature_cost=observed_features(y); f['score4']=score_model.predict(f['phase'])
    reference_start=time.perf_counter(); logpdf=[]
    for theta in candidates: logpdf.append(model.evaluate(y,*theta,score=False)[0])
    logpdf=np.column_stack(logpdf); reference_seconds=time.perf_counter()-reference_start
    power=abs(y)**2; second=[]
    for q,mu,tau,noise in candidates:
        variance=tau+noise
        second.append(-config['n']*np.log(np.pi*variance)-power.sum(axis=1)/variance)
    second=np.column_stack(second)
    reference_errors=[]
    for index in config['independent_reference_candidates']:
        direct=independent_log_density(y[:config['independent_reference_rows']],independent_words(4),
            independent_transform(4,.37/4,.13/16,0),*candidates[index])
        reference_errors.append(float(np.max(abs(direct-logpdf[:len(direct),index]))))
    if max(reference_errors)>config['exact_reference_tolerance']:
        raise AssertionError('independent finite likelihood reference failed')
    np.savez(output/'likelihoods.npz',exact_logpdf=logpdf,second_gaussian_logpdf=second)
    objectives={}; inference_costs=[]
    for split,groups in [('calibration',config['calibration_groups']),('evaluation',config['evaluation_groups'])]:
        for r in repeats:
            for method in methods:
                values=[]
                for condition in range(len(candidates)):
                    a,b=slices[split,condition]
                    if method in banks:
                        grouped=aggregate_rows(f[method][a:b],groups,max_r,r)
                        objective,cost=banks[method].objective(grouped,r)
                        inference_costs.append(dict(split=split,repeats=r,method=method,condition=condition,**cost))
                    else:
                        matrix=logpdf if method=='exact' else second
                        objective=-2*aggregate_rows(matrix[a:b],groups,max_r,r,mean=False)
                    values.append(objective)
                objectives[split,r,method]=values
    calibrations={}; rows=[]
    for r in repeats:
        for method in methods:
            calibration=calibrate(objectives['calibration',r,method],candidates,0.,config['alpha'])
            calibrations[f'{method}_R{r}']=calibration
            for condition,objective in enumerate(objectives['evaluation',r,method]):
                unidentifiable=(0,1) if method=='second_gaussian' else ((1,) if method in ['old_T','powers'] else ())
                random=None
                if method=='second_gaussian':
                    rng=np.random.default_rng([*config['seed'],3,r,condition])
                    random=rng.random(len(objective))<config['alpha']
                result,raw=evaluate_grid(objective,candidates,condition,0.,calibration,interest='q',
                    unidentifiable=unidentifiable,randomized_null=random)
                rows.append(dict(method=method,repeats=r,condition=condition,public_truth=candidates[condition].tolist(),
                    statistical_model='exact Gaussian-control input/gain law',**result))
                np.savez(output/f'evaluation_{method}_R{r}_c{condition:02d}.npz',objective=objective,**raw)
            np.savez(output/f'calibration_{method}_R{r}.npz',objectives=np.stack(objectives['calibration',r,method]))
    if observation_count!=config['new_observations']: raise AssertionError('actual observation count disagrees with configuration')
    costs=dict(generation=generation_costs,training_features=train_feature_cost,features=feature_cost,
        exact_candidate_mean_construction_seconds=construction_seconds,banks=setup,inference=inference_costs,
        reference=dict(seconds=reference_seconds,candidate_parameters=len(candidates),observations=len(y),
            covariance_factorizations=len(candidates)*len(model.weights),component_observation_pairs=len(candidates)*len(y)*len(model.weights)),
        shared_objectives='detection/estimation/grid sets reuse the same objective matrix, no repeated likelihood calls',
        seconds_before_summary=time.perf_counter()-start)
    dump(output/'calibration.json',plain(calibrations)); dump(output/'cases.json',plain(rows)); dump(output/'costs.json',plain(costs))
    return dict(new_observations=observation_count,candidates=len(candidates),evaluation_rows=len(rows),
        methods=methods,repeats=repeats,calibration_groups_per_condition=config['calibration_groups'],
        evaluation_groups_per_condition=config['evaluation_groups'],independent_reference_max_error=max(reference_errors),
        q_delta_equivalence='same candidate IDs under delta=sqrt(q); no separate algorithm or claimed coordinate gain',
        failures=0,coverage_scope='finite registered parameter laws, marginal over independent calibration/evaluation; no Wilks',
        seconds_before_summary=time.perf_counter()-start,receiver_calls=0,decoder_calls=0)


if __name__=='__main__':
    from experiments.afdm_efficient_information.protocol import run
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',required=True); args=parser.parse_args()
    config=json.loads(CONFIG_PATH.read_text()); base=Path(__file__).parent
    sources=[__file__,base/'inference.py',base/'features.py',base/'features_study.py',base/'score.py',
        base/'test_inference.py',CONFIG_PATH,ROOT/config['score_model'],
        ROOT/'experiments/afdm_higher_order_information/moments.py',ROOT/'experiments/afdm_higher_order_information/theory_study.py',
        ROOT/'experiments/afdm_shared_channel_20261004/conditional_solver.py',ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
        ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py']
    run(args.stage,config,sources,calculate,wall_seconds=config['wall_seconds'])
