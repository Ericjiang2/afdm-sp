"""Actual normalized G0/PDP-marginal unknown-nuisance finite-grid study."""
import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_efficient_information.features import observed_features
from experiments.afdm_efficient_information.features_study import plain
from experiments.afdm_efficient_information.inference import (
    MomentBank,aggregate_rows,calibrate,evaluate_grid,load_score_model,
)
from experiments.afdm_efficient_information.component_artifacts import save_used_components
from experiments.afdm_efficient_information.prior_likelihood import ActualPrior,actual_signal_covariance
from experiments.afdm_higher_order_information.prior import frozen_components

ROOT=Path(__file__).resolve().parents[2]
CONFIG_PATH=ROOT/'results/afdm_efficient_information/INFERENCE_ACTUAL_CONFIG.json'


def public_candidates(config):
    return np.array([(d,m,np.log(t),np.log(s)) for d,m,t,s in itertools.product(
        config['delta'],config['mu'],config['tau'],config['noise'])])


def second_gaussian_logpdf(y,model,theta):
    """Independent uniform unit-power inputs give E[ssH]=I in time coordinates."""
    channel_covariance=actual_signal_covariance(model,theta)
    variance=np.diag(channel_covariance).real+np.exp(theta[3])
    if not np.isfinite(variance).all() or np.any(variance<=0):
        raise ValueError('actual second-moment working Gaussian must be positive')
    return -np.sum(np.log(np.pi*variance))-(abs(y)**2)@(1/variance),variance


def mean_validation(training,validation):
    """Independent raw and SE-scaled candidate mean discrepancies, no tuning."""
    difference=validation.mean(axis=0)-training.mean(axis=0)
    se=np.sqrt(training.var(axis=0,ddof=1)/len(training)+validation.var(axis=0,ddof=1)/len(validation))
    normalized=np.divide(abs(difference),se,out=np.zeros_like(se),where=se>0)
    if np.any((se==0)&(difference!=0)):
        raise ValueError('different deterministic feature means cannot have zero SE')
    return dict(difference=difference,standard_error=se,absolute_se_ratio=normalized,
                maximum_absolute_se_ratio=float(normalized.max()),
                scope='independent mean discrepancy; componentwise SE diagnostics, no simultaneous or exact-mean certificate')


def calculate(output):
    from experiments.afdm_efficient_information.protocol import dump,hashes
    config=json.loads(CONFIG_PATH.read_text()); start=time.perf_counter(); candidates=public_candidates(config)
    max_r=max(config['repeats']); null_value=config['delta'][0]
    models={order:ActualPrior(n=config['n'],model='g0',pdp='marginal',order=order,phases=2*order)
            for order in [config['primary_order'],config['refined_order'],config['audit_order']]}
    generator=models[config['primary_order']]
    actual_model=load_score_model(ROOT/config['actual_score_model'])
    control_model=load_score_model(ROOT/config['control_score_model'])
    feature_levels=['old_T','powers','phase','actual_score4','Gaussian_transfer_score4']
    methods=feature_levels+['actual_reference','actual_reference_refined','second_gaussian']
    teacher_results=json.loads((ROOT/config['actual_feature_results']).read_text())
    # Retain the complete branch declarations; no true realized PDP enters features.
    branches=[]
    for condition,theta in enumerate(candidates):
        branch=generator.branch(theta)
        branches.append(dict(condition=condition,public_theta=theta,signature=branch['signature'],
            eigenvalues=branch['eigenvalues'],platform=branch['platform'],pdp=branch['pdp']))
    dump(output/'branches.json',plain(branches))
    generation=[]; all_y=[]; slices={}; cursor=0
    counts=[('training',config['training_per_candidate']),('mean_validation',config['mean_validation_per_candidate']),
        ('calibration',config['calibration_groups']*max_r),('evaluation',config['evaluation_groups']*max_r)]
    for split_index,(split,count) in enumerate(counts):
        for condition,theta in enumerate(candidates):
            before=time.perf_counter(); y=generator.sample(theta,count,[*config['seed'],split_index,condition])
            generation.append(dict(split=split,condition=condition,seconds=time.perf_counter()-before))
            slices[split,condition]=(cursor,cursor+len(y)); cursor+=len(y); all_y.append(y)
    if cursor!=config['new_observations']: raise AssertionError('actual new observation count differs from reservation')
    y=np.concatenate(all_y)
    np.savez(output/'observations.npz',y=y,candidates=candidates,
        **{split+'_slices':np.array([slices[split,j] for j in range(len(candidates))]) for split,_ in counts})
    feature,feature_cost=observed_features(y)
    score_start=time.perf_counter()
    feature['actual_score4']=actual_model.predict(feature['phase'])
    feature['Gaussian_transfer_score4']=control_model.predict(feature['phase'])
    score_seconds=time.perf_counter()-score_start
    means={}; banks={}; diagnostics=[]; setup=[]
    for level in feature_levels:
        training=[]; candidate_means=[]; ids=[]
        for condition in range(len(candidates)):
            a,b=slices['training',condition]; c,d=slices['mean_validation',condition]
            observed=feature[level][a:b]; validation=feature[level][c:d]
            candidate_means.append(observed.mean(axis=0)); training.append(observed); ids.extend([condition]*len(observed))
            diagnostics.append(dict(method=level,condition=condition,**mean_validation(observed,validation)))
        means[level]=np.array(candidate_means); training=np.concatenate(training)
        banks[level]=MomentBank(training,means[level][ids],means[level])
        setup.append(dict(method=level,**banks[level].cost))
        np.savez(output/f'bank_{level}.npz',**banks[level].state(),candidate_means=means[level])
    dump(output/'mean_validation.json',plain(diagnostics))
    inference_start=slices['calibration',0][0]; observed=y[inference_start:]
    references={}; reference_costs=[]; component_artifacts=[]
    for order in [config['primary_order'],config['refined_order']]:
        before=time.perf_counter()
        references[order]=np.column_stack([models[order].logpdf(observed,theta) for theta in candidates])
        reference_costs.append(dict(order=order,seconds=time.perf_counter()-before,operations=dict(models[order].cost)))
        for condition,theta in enumerate(candidates):
            component_artifacts.append(save_used_components(output/f'components_order{order}_c{condition:02d}.npz',models[order],theta))
    primary=references[config['primary_order']]; refined=references[config['refined_order']]
    error=abs(primary-refined); qualified=error<=config['logpdf_tolerance']
    audit_ids=np.concatenate([np.arange(slices[split,j][0],slices[split,j][0]+config['audit_rows_per_condition_split'])
        for split in ['calibration','evaluation'] for j in range(len(candidates))])-inference_start
    audit_start=time.perf_counter()
    audited=np.column_stack([models[config['audit_order']].logpdf(observed[audit_ids],candidates[j]) for j in config['audit_candidates']])
    audit_error=abs(audited-refined[np.ix_(audit_ids,config['audit_candidates'])])
    reference_costs.append(dict(order=config['audit_order'],seconds=time.perf_counter()-audit_start,
        operations=dict(models[config['audit_order']].cost),scope='predetermined candidate/row subset only'))
    for condition in config['audit_candidates']:
        component_artifacts.append(save_used_components(output/f'components_order{config["audit_order"]}_c{condition:02d}.npz',
            models[config['audit_order']],candidates[condition]))
    second_start=time.perf_counter(); second=[]; variances=[]
    for theta in candidates:
        logpdf,variance=second_gaussian_logpdf(observed,generator,theta)
        second.append(logpdf); variances.append(variance)
    second=np.column_stack(second); second_seconds=time.perf_counter()-second_start
    np.savez(output/'likelihoods.npz',primary=primary,refined=refined,second_gaussian=second,variance=variances,
        absolute_error=error,qualified=qualified,audit_logpdf=audited,audit_error=audit_error,
        audit_row_indices=audit_ids,audit_candidate_indices=config['audit_candidates'])
    objectives={}; inference_costs=[]
    for split,groups in [('calibration',config['calibration_groups']),('evaluation',config['evaluation_groups'])]:
        for r in config['repeats']:
            for method in methods:
                values=[]
                for condition in range(len(candidates)):
                    a,b=slices[split,condition]
                    if method in banks:
                        grouped=aggregate_rows(feature[method][a:b],groups,max_r,r)
                        objective,cost=banks[method].objective(grouped,r)
                        inference_costs.append(dict(split=split,repeats=r,method=method,condition=condition,**cost))
                    else:
                        matrix={'actual_reference':primary,'actual_reference_refined':refined,'second_gaussian':second}[method]
                        objective=-2*aggregate_rows(matrix[a-inference_start:b-inference_start],groups,max_r,r,mean=False)
                    values.append(objective)
                objectives[split,r,method]=values
    calibrations={}; rows=[]; reference_sensitivity=[]
    for r in config['repeats']:
        for method in methods:
            calibration=calibrate(objectives['calibration',r,method],candidates,null_value,config['alpha'])
            calibrations[f'{method}_R{r}']=calibration
            for condition,objective in enumerate(objectives['evaluation',r,method]):
                result,raw=evaluate_grid(objective,candidates,condition,null_value,calibration,interest='delta')
                a,b=slices['evaluation',condition]; group_qualified=aggregate_rows(
                    np.all(qualified[a-inference_start:b-inference_start],axis=1),config['evaluation_groups'],max_r,r,mean=False)==r
                rows.append(dict(method=method,repeats=r,condition=condition,public_truth=candidates[condition].tolist(),
                    statistical_model='actual G0 common-zero-delay conditional PDP-marginal law',
                    numerical_reference_unqualified_groups=int((~group_qualified).sum()),**result))
                np.savez(output/f'evaluation_{method}_R{r}_c{condition:02d}.npz',objective=objective,
                         numerical_reference_qualified=group_qualified,**raw)
            np.savez(output/f'calibration_{method}_R{r}.npz',objectives=np.stack(objectives['calibration',r,method]))
        for condition in range(len(candidates)):
            a=objectives['evaluation',r,'actual_reference'][condition]
            b=objectives['evaluation',r,'actual_reference_refined'][condition]
            reference_sensitivity.append(dict(condition=condition,repeats=r,
                maximum_candidate_objective_difference=float(np.max(abs(a-b))),
                selected_candidate_disagreements=int(np.sum(a.argmin(axis=1)!=b.argmin(axis=1)))))
    reference_qualification=dict(primary_order=config['primary_order'],refined_order=config['refined_order'],
        tolerance=config['logpdf_tolerance'],candidate_observation_pairs=int(error.size),
        unqualified_pairs=int((~qualified).sum()),maximum_logpdf_error=float(error.max()),
        audit_order=config['audit_order'],audit_pairs=int(audit_error.size),
        audit_unqualified_pairs=int((audit_error>config['logpdf_tolerance']).sum()),maximum_audit_logpdf_error=float(audit_error.max()),
        full_reference_qualified=bool(qualified.all() and (audit_error<=config['logpdf_tolerance']).all()),
        scope='refinement qualification, not mathematical exactness; order48 checks only registered subset')
    costs=dict(generation=generation,features=feature_cost,score_prediction_seconds=score_seconds,
        banks=setup,reference=reference_costs,component_artifacts=component_artifacts,second_gaussian_seconds=second_seconds,inference=inference_costs,
        seconds_before_summary=time.perf_counter()-start,
        no_double_count='nested feature, teacher and candidate costs are categories within attempt wall, not additive repeat stages')
    source_binding=hashes([ROOT/config[k] for k in ['actual_score_model','control_score_model','actual_feature_results']])
    dump(output/'calibration.json',plain(calibrations)); dump(output/'cases.json',plain(rows))
    dump(output/'costs.json',plain(costs)); dump(output/'reference_qualification.json',reference_qualification)
    dump(output/'reference_sensitivity.json',reference_sensitivity)
    return dict(new_observations=cursor,candidates=len(candidates),evaluation_rows=len(rows),methods=methods,
        repeats=config['repeats'],reference_qualification=reference_qualification,
        upstream_actual_teacher_unqualified=teacher_results['teacher_unqualified'],source_artifact_sha256=source_binding,
        reference_sensitivity=reference_sensitivity,failures=0,receiver_calls=0,decoder_calls=0,
        seconds_before_summary=time.perf_counter()-start,
        scope='actual regular local finite-grid detection and estimation; no Gaussian collision q-DQM transfer')


if __name__=='__main__':
    from experiments.afdm_efficient_information.protocol import run
    from experiments.afdm_shared_channel_20261004.production_diagnostic import source_paths
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',required=True); args=parser.parse_args()
    frozen_components(); config=json.loads(CONFIG_PATH.read_text()); base=Path(__file__).parent
    sources=[__file__,base/'inference.py',base/'features.py',base/'features_study.py',base/'score.py',
        base/'prior_likelihood.py',base/'test_inference_actual.py',CONFIG_PATH,
        *[ROOT/config[k] for k in ['actual_score_model','control_score_model','actual_feature_results']],
        *source_paths(),ROOT/'experiments/afdm_higher_order_information/prior.py',
        ROOT/'experiments/afdm_shared_channel_20261004/production_prior.py']
    run(args.stage,config,sources,calculate,wall_seconds=config['wall_seconds'])
