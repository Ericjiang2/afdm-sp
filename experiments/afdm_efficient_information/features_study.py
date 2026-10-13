"""Independent teacher/train/validation/test study of frozen score compression."""
import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_efficient_information.features import observed_features
from experiments.afdm_efficient_information.score import (
    conditional_scores,linear_information,score_information,select_regressor,
)
from experiments.afdm_higher_order_information.moments import FiniteControl

ROOT=Path(__file__).resolve().parents[2]
CONFIG_PATH=ROOT/'results/afdm_efficient_information/FEATURE_CONTROL_CONFIG.json'


def plain(value):
    if isinstance(value,np.ndarray): return value.tolist()
    if isinstance(value,np.generic): return value.item()
    if isinstance(value,dict): return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [plain(x) for x in value]
    return value


def sample_control(model,theta,count,seed):
    """Declared experiment generator; teacher parameters never enter feature APIs."""
    q,mu,tau,noise=theta; rng=np.random.default_rng(seed); n=model.n
    index=rng.integers(len(model.weights),size=count)
    gain=(rng.normal(size=(count,2))+1j*rng.normal(size=(count,2)))*np.sqrt(tau/4)
    unit_noise=(rng.normal(size=(count,n))+1j*rng.normal(size=(count,n)))/np.sqrt(2)
    response=np.exp(2j*np.pi*np.outer(mu+np.array([-np.sqrt(q),np.sqrt(q)]),np.arange(n))/n)
    y=(gain @ response)*model.time_words[index]+np.sqrt(noise)*unit_noise
    return y,dict(word_indices=index,gain_truth=gain,unit_noise=unit_noise)


def bootstrap_information(features,scores,replicates,seed):
    rng=np.random.default_rng(seed); values=[]
    for _ in range(replicates):
        ids=rng.integers(len(scores),size=len(scores))
        values.append(linear_information(features[ids],scores[ids])['effective'])
    return np.array(values)


def evaluate_layer(train,validation,test,train_scores,validation_scores,test_scores,ridges,bootstrap,seed):
    started=time.perf_counter()
    fitted,trace=select_regressor(train,train_scores,validation,validation_scores,ridges)
    train_prediction=fitted.predict(train); prediction=fitted.predict(test)
    train_info=score_information(train_scores)
    heldout_info=score_information(test_scores)
    beta=train_info['beta']
    target=test_scores[:,0]-test_scores[:,1:] @ beta
    predicted=prediction[:,0]-prediction[:,1:] @ beta
    squared=(prediction-test_scores)**2
    mse=squared.mean(axis=0)
    mse_batches=np.array_split(squared,min(16,len(squared)))
    mse_se=np.std([x.mean(axis=0) for x in mse_batches],axis=0,ddof=1)/np.sqrt(len(mse_batches))
    linear=linear_information(test,test_scores)
    compressed=linear_information(prediction,test_scores)
    training_linear=linear_information(train,train_scores)
    boot=bootstrap_information(test,test_scores,bootstrap,seed)
    effective_residual=target-predicted
    result=dict(selected_ridge=fitted.ridge,training_rank=fitted.rank,validation_candidates=trace,
        score_mse=mse,score_mse_batch_se=mse_se,training_score_mse=np.mean((train_prediction-train_scores)**2,axis=0),
        effective_target_mse=float(np.mean(effective_residual**2)),
        effective_target='sq-s_eta*beta_train; beta_train is not population efficient projection',
        frozen_beta=beta,heldout_nuisance_residual=(test_scores[:,1:].T @ target/len(test_scores)),
        teacher_raw=heldout_info['raw'],teacher_effective_plugin=heldout_info['effective'],
        feature_linear_information_plugin=linear['effective'],feature_raw_linear_plugin=linear['raw'],
        feature_rank=linear['feature_rank'],feature_dimension=test.shape[1],
        feature_linear_bootstrap_percentile_95=np.quantile(boot,[.025,.975]),
        compressed_prediction_linear_plugin=compressed['effective'],training_feature_linear_plugin=training_linear['effective'],
        heldout_reprojected_nuisance_residual=linear['nuisance_moment_residual'],
        duration_seconds=time.perf_counter()-started,
        evidence='independent heldout diagnostics; bootstrap estimates plug-in uncertainty, not certified Fisher/retention',
        inference_cost=dict(test_predictions=len(test),active_features=int(fitted.active.sum()),
            regression_multiply_adds=len(test)*int(fitted.active.sum())*test_scores.shape[1]))
    return fitted,result,dict(predictions=prediction,bootstrap_linear_information=boot,heldout_jacobian=linear['jacobian'],
                             heldout_feature_covariance=linear['covariance'])


def calculate(output):
    from experiments.afdm_efficient_information.protocol import dump
    config=json.loads(CONFIG_PATH.read_text()); started=time.perf_counter(); rows=[]; costs=[]
    x,z=np.array(list(itertools.product([-1.,1.],repeat=2))).T
    finite_scores=np.column_stack((x,x+z)); full=score_information(finite_scores)
    conditional,mass,_=conditional_scores(finite_scores,x)
    wrong,_,_=conditional_scores(full['residual'][:,None],x)
    exact=score_information(conditional,mass)
    counterexample=dict(full_effective=full['effective'],compressed_effective=exact['effective'],
        wrongly_compressed_effective_norm=float(mass @ wrong[:,0]**2),states=np.column_stack((x,z)),
        probability=np.full(4,.25),scores=finite_scores,compressed_scores=conditional)
    dump(output/'noncommutation.json',plain(counterexample))
    for point,theta in enumerate(config['public_points']):
        model=FiniteControl.uniform(config['n']); count=sum(config['split_sizes'])
        before=time.perf_counter(); y,audit=sample_control(model,theta,count,[*config['seed'],point])
        generation_seconds=time.perf_counter()-before
        before=time.perf_counter(); logp,scores=model.evaluate(y,*theta)
        teacher_seconds=time.perf_counter()-before
        f,feature_cost=observed_features(y)
        end_train=config['split_sizes'][0]; end_validation=end_train+config['split_sizes'][1]
        np.savez(output/f'observations_{point}.npz',y=y,score=scores,logpdf=logp,public_theta=theta,
            teacher_time_words=model.time_words,teacher_weights=model.weights,
            train_indices=np.arange(end_train),validation_indices=np.arange(end_train,end_validation),
            test_indices=np.arange(end_validation,count),**audit)
        costs.append(dict(point=point,public_theta=theta,new_observations=count,
            generation_seconds=generation_seconds,teacher_seconds=teacher_seconds,feature_cost=feature_cost,
            teacher_covariance_factorizations=len(model.weights),teacher_component_observation_pairs=count*len(model.weights),
            teacher='finite QPSK exact Gaussian-control mixture',score_columns=['q','mu','tau','sigma2']))
        info=score_information(scores[:end_train])
        for level in config['levels']:
            values=f[level]
            fitted,result,raw=evaluate_layer(values[:end_train],values[end_train:end_validation],values[end_validation:],
                scores[:end_train],scores[end_train:end_validation],scores[end_validation:],config['ridges'],
                config['bootstrap_replicates'],[*config['seed'],100,point,config['levels'].index(level)])
            np.savez(output/f'model_{point}_{level}.npz',**fitted.state(),efficient_beta=info['beta'],public_theta=theta,
                teacher_time_words=model.time_words,teacher_weights=model.weights)
            np.savez(output/f'evaluation_{point}_{level}.npz',features_test=values[end_validation:],**raw)
            rows.append(dict(point=point,level=level,public_theta=theta,**plain(result)))
    dump(output/'feature_cases.json',rows); dump(output/'costs.json',plain(costs))
    return dict(new_observations=config['new_observations'],cases=len(rows),levels=config['levels'],
        rows=rows,teacher_costs=plain(costs),noncommutation=plain(counterexample),
        primary_frozen_transfer_model='model_1_phase.npz',
        selected_primary_before_data=True,interpretation='no model/level chosen using test ranking; no exact Fisher retention ratio',
        seconds_before_summary=time.perf_counter()-started,receiver_calls=0,decoder_calls=0)


if __name__=='__main__':
    from experiments.afdm_efficient_information.protocol import run
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',required=True); args=parser.parse_args()
    config=json.loads(CONFIG_PATH.read_text())
    base=Path(__file__).parent
    sources=[__file__,base/'score.py',base/'features.py',base/'test_score.py',CONFIG_PATH,
        ROOT/'experiments/afdm_higher_order_information/moments.py',
        ROOT/'experiments/afdm_shared_channel_20261004/conditional_solver.py',
        ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
        ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py']
    run(args.stage,config,sources,calculate,wall_seconds=config['wall_seconds'])
