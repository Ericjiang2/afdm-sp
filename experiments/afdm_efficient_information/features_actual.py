"""Actual PDP-marginal teacher, fixed public-point score regression and mismatch."""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_efficient_information.features import observed_features
from experiments.afdm_efficient_information.features_study import evaluate_layer,plain
from experiments.afdm_efficient_information.score import score_information
from experiments.afdm_efficient_information.inference import load_score_model
from experiments.afdm_efficient_information.component_artifacts import save_used_components
from experiments.afdm_efficient_information.prior_likelihood import ActualPrior
from experiments.afdm_higher_order_information.prior import frozen_components

ROOT=Path(__file__).resolve().parents[2]
CONFIG_PATH=ROOT/'results/afdm_efficient_information/FEATURE_ACTUAL_CONFIG.json'


def load_regressor(path):
    model=load_score_model(path)
    with np.load(path) as saved:
        metadata={k:saved[k].copy() for k in ['efficient_beta','public_theta']}
    return model,metadata


def calculate(output):
    from experiments.afdm_efficient_information.protocol import dump,hashes
    config=json.loads(CONFIG_PATH.read_text()); theta=np.array(config['public_theta']); start=time.perf_counter()
    models={order:ActualPrior(n=4,model='g0',pdp='marginal',order=order,phases=2*order) for order in config['orders']}
    primary=models[config['primary_order']]
    before=time.perf_counter(); y=primary.sample(theta,config['new_observations'],config['seed'])
    sample_seconds=time.perf_counter()-before
    np.savez(output/'observations.npz',y=y,public_theta=theta)
    refs={}; costs=[]; component_artifacts=[]
    for order,model in models.items():
        before=time.perf_counter(); result=model.evaluate(y,theta,step=config['score_step'])
        elapsed=time.perf_counter()-before
        refs[order]=result
        component_artifacts.append(save_used_components(output/f'components_order{order}.npz',model,theta,config['score_step']))
        np.savez(output/f'teacher_order{order}.npz',logpdf=result['logpdf'],score=result['score'])
        costs.append(dict(category='teacher',order=order,phases=2*order,seconds=elapsed,
            quadrature_mass_error=result['quadrature_mass_error'],operations=dict(model.cost)))
    before=time.perf_counter(); fine_step=primary.evaluate(y,theta,step=config['refined_step'])
    costs.append(dict(category='teacher_step_refinement',seconds=time.perf_counter()-before,step=config['refined_step']))
    component_artifacts.append(save_used_components(output/'components_refined_step.npz',primary,theta,config['refined_step']))
    reference=refs[max(config['orders'])]; teacher=refs[config['primary_order']]
    density_error=abs(teacher['logpdf']-reference['logpdf'])
    score_error=np.max(abs(teacher['score']-reference['score']),axis=1)
    step_error=np.max(abs(teacher['score']-fine_step['score']),axis=1)
    qualified=(density_error<=config['logpdf_tolerance'])&(score_error<=config['score_tolerance'])&(step_error<=config['step_tolerance'])
    np.savez(output/'teacher_refinement.npz',logpdf_error=density_error,score_error=score_error,
        step_error=step_error,qualified=qualified,refined_step_scores=fine_step['score'])
    features,feature_cost=observed_features(y); scores=teacher['score']
    ntrain,nvalidation,ntest=config['split_sizes']; end=ntrain+nvalidation
    beta=score_information(scores[:ntrain])['beta']; rows=[]
    for index,level in enumerate(config['levels']):
        f=features[level]
        model,result,raw=evaluate_layer(f[:ntrain],f[ntrain:end],f[end:],scores[:ntrain],scores[ntrain:end],scores[end:],
            config['ridges'],config['bootstrap_replicates'],[*config['seed'],200,index])
        np.savez(output/f'model_0_{level}.npz',**model.state(),efficient_beta=beta,public_theta=theta)
        np.savez(output/f'evaluation_0_{level}.npz',features_test=f[end:],**raw)
        rows.append(dict(level=level,point=0,teacher='actual G0 PDP-marginal finite positive quadrature',
            score_columns=['delta','mu','log_tau','log_sigma2'],teacher_unqualified_test=int((~qualified[end:]).sum()),**plain(result)))
    source=ROOT/config['control_model']
    proxy,metadata=load_regressor(source)
    # This is a fixed coordinate-aligned proxy at the PUBLIC destination point,
    # not an exact source-score transformation across different parameter points.
    jacobian=np.array([2*theta[0],1.,np.exp(theta[2]),np.exp(theta[3])])
    predicted=proxy.predict(features['phase'][end:])*jacobian
    mismatch=dict(source_model=str(source.relative_to(ROOT)),source_model_sha256=hashes([source]),
        source_public_theta=metadata['public_theta'],source_coordinates=['q','mu','tau','sigma2'],
        destination_public_theta=theta,destination_coordinates=['delta','mu','log_tau','log_sigma2'],
        fixed_coordinate_multiplier=jacobian,mse=np.mean((predicted-scores[end:])**2,axis=0),
        scope='different prior/input chirps/base point; frozen proxy coordinate alignment is a diagnostic, not an exact transported source score')
    np.savez(output/'Gaussian_proxy_mismatch.npz',predicted_native_coordinates=predicted,actual_teacher_score=scores[end:])
    dump(output/'feature_cases.json',rows); dump(output/'costs.json',plain(dict(sample_seconds=sample_seconds,teacher=costs,feature=feature_cost,component_artifacts=component_artifacts)))
    dump(output/'mismatch.json',plain(mismatch))
    return dict(new_observations=config['new_observations'],cases=len(rows),teacher_qualified=int(qualified.sum()),
        teacher_unqualified=int((~qualified).sum()),maximum_logpdf_error=float(density_error.max()),
        maximum_score_error=float(score_error.max()),maximum_step_error=float(step_error.max()),rows=rows,
        mismatch=plain(mismatch),teacher_costs=plain(costs),seconds_before_summary=time.perf_counter()-start,
        failure_rule='all rows including unqualified teacher rows remain in MSE; nonconvergence qualifies every dependent claim',
        receiver_calls=0,decoder_calls=0)


if __name__=='__main__':
    from experiments.afdm_efficient_information.protocol import run
    from experiments.afdm_shared_channel_20261004.production_diagnostic import source_paths
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',required=True); args=parser.parse_args()
    frozen_components(); config=json.loads(CONFIG_PATH.read_text()); base=Path(__file__).parent
    sources=[__file__,base/'features.py',base/'features_study.py',base/'score.py',base/'prior_likelihood.py',
        CONFIG_PATH,ROOT/config['control_model'],*source_paths(),
        ROOT/'experiments/afdm_higher_order_information/prior.py',
        ROOT/'experiments/afdm_shared_channel_20261004/production_prior.py']
    run(args.stage,config,sources,calculate,wall_seconds=config['wall_seconds'])
