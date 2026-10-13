"""Bounded learned local-potential comparison on a legal finite bilinear teacher."""
from pathlib import Path
import io
import sys
import time
import unittest

import numpy as np
import torch
from torch import nn
from scipy.special import logsumexp

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.afdm_structured_inference_20261003.common import run,dump
from experiments.afdm_structured_inference_20261003.potential import finite_potential,make_bilinear_case,real_pack

V=np.array([.5,-.5,.5,-.5])
CONFIG=dict(schema='finite-local-potential-learning/1',n=2,p=2,states=256,
            seed_namespace=[20261003,104129],streams=dict(train=70,validation=71,test=72),
            clusters=dict(train=12,validation=4,test=8),observations_per_cluster=8,
            sigma2=.7,xi_sd=.35,eta_feature_scale=4.,inputs=33,outputs=16,
            source_order='eta[4]/4, xi[8], operators_real[8], operators_imag[8], pilot_real_imag[4], sigma2',
            training_geometry='center uniform[-.5,.5], stride5, delay1',
            test_geometry='4 centers uniform[-1.5,-.8] stride5;4 centers uniform[.8,1.5] stride5.3 CPP',
            transforms=['path_permutation','joint_phase_h_i_d_minus_i_pilot_minus_i'],
            network_seeds=[0,1,2],shared_width=32,independent_width=22,
            shared_parameters=1121,independent_parameters=1116,steps=200,lr=.01,
            optimizer='Adam, full training batch; fixed final checkpoint, no early stop/search',
            objective='mean_z MSE + Cov(z,f) v_eta MSE; v=(.5,-.5,.5,-.5)',
            step_baseline='one positive learned scalar on one parallel uniform-cavity mean-field physical message',
            bootstrap_replicates=1000,bootstrap_unit='geometry cluster, network seeds averaged first; stratified test families',
            source_fd_step=2e-5,support_tolerance=1e-10,torch_version=torch.__version__,
            thread_policy='one torch/BLAS thread; shared-machine timings are diagnostic',
            teacher='exact finite four-point gains and QPSK data, not Gaussian gain integral or production',
            proper_score_gate='all coordinate probabilities valid over entire model/seed/cohort; otherwise no proper score',
            test_selection='none; all cases and seeds retained; transformations not additional independent samples')


class SharedPotential(nn.Module):
    """Convex smooth scalar in the sources; does not impose finite QPSK support."""
    def __init__(self):
        super().__init__()
        self.hidden=nn.Linear(33,32,dtype=torch.float64)
        self.raw_readout=nn.Parameter(torch.full((32,),-2.,dtype=torch.float64))
        self.offset=nn.Parameter(torch.zeros((),dtype=torch.float64))
        nn.init.normal_(self.hidden.weight,std=.1)
        nn.init.zeros_(self.hidden.bias)

    def forward(self,x):
        return nn.functional.softplus(self.hidden(x))@nn.functional.softplus(self.raw_readout)+self.offset


class IndependentHeads(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers=nn.Sequential(nn.Linear(33,22,dtype=torch.float64),nn.Tanh(),nn.Linear(22,16,dtype=torch.float64))

    def forward(self,x):
        return self.layers(x)


def shared_prediction(model,features,*,training=False,covariance=False):
    x=features.detach().clone().requires_grad_(True)
    gradient=torch.autograd.grad(model(x).sum(),x,create_graph=True)[0]
    mean=gradient[:,4:12]
    v=torch.as_tensor(V,dtype=x.dtype)
    directional=(gradient[:,:4]*(v/CONFIG['eta_feature_scale'])).sum()
    response=torch.autograd.grad(directional,x,create_graph=training,retain_graph=training or covariance)[0][:,4:12]
    cov=None
    if covariance:
        cov=torch.stack([torch.autograd.grad(mean[:,j].sum(),x,retain_graph=j<7)[0][:,4:12]
                         for j in range(8)],dim=1)
    return mean,response,cov


def predict(model,features,*,training=False,covariance=False):
    if isinstance(model,SharedPotential):
        return shared_prediction(model,features,training=training,covariance=covariance)
    with torch.set_grad_enabled(training):
        output=model(features)
    return output[:,:8],output[:,8:],None


def features_for(case,eta,xi,sigma2):
    return np.concatenate([eta/CONFIG['eta_feature_scale'],xi,real_pack(case['operators'].ravel()),
                           real_pack(case['pilot']),[sigma2]])


def meanfield_statistics(case,sigma2):
    """One uniform-product cavity update: conditional expectation of log factor."""
    z,f=case['z'],case['f']; energy=np.sum(f*f,axis=1)/sigma2
    diff_f=np.stack([f[z[:,j]>0].mean(axis=0)-f[z[:,j]<0].mean(axis=0) for j in range(8)])
    diff_energy=np.array([energy[z[:,j]>0].mean()-energy[z[:,j]<0].mean() for j in range(8)])
    return diff_f,diff_energy


def meanfield_prediction(xi,physical_logits,response_projection,alpha=1.):
    logits=xi+alpha*physical_logits
    tangent=np.tanh(logits/2)
    mean=.5*tangent
    response=.25*(1-tangent*tangent)*alpha*response_projection
    return mean,response


def transform_case(case,xi,kind):
    updated={k:np.copy(v) for k,v in case.items()}
    if kind=='path_permutation':
        permutation=np.array([1,0,2,3,5,4,6,7])
        updated['z']=case['z'][:,permutation]
        updated['h']=case['h'][:,::-1]
        updated['operators']=case['operators'][::-1]
        source=xi[permutation]
    elif kind=='joint_phase':
        updated['h']=1j*case['h'];updated['d']=-1j*case['d'];updated['pilot']=-1j*case['pilot']
        updated['z']=real_pack(np.concatenate([updated['h'],updated['d']],axis=1))
        # z' = T z; orthogonal T also acts on the source.
        a=xi[:4]+1j*xi[4:];a[:2]*=1j;a[2:]*=-1j
        source=real_pack(a)
    else:
        raise ValueError('unregistered transformation')
    updated['f']=real_pack(np.einsum('kp,pij,kj->ki',updated['h'],updated['operators'],updated['pilot']+updated['d']))
    return updated,source


def generate_data(output):
    records=[];arrays=[];teacher_seconds=0.;start=time.perf_counter()
    for split,count in CONFIG['clusters'].items():
        for cluster in range(count):
            rng=np.random.default_rng([*CONFIG['seed_namespace'],CONFIG['streams'][split],cluster])
            if split=='test':
                family='center_extrapolation' if cluster<4 else 'center_cpp_extrapolation'
                center=rng.uniform(-1.5,-.8) if cluster<4 else rng.uniform(.8,1.5)
                stride=5. if cluster<4 else 5.3
            else:
                family='development_domain';center=rng.uniform(-.5,.5);stride=5.
            case=make_bilinear_case('general',center=center,stride=stride,delay=1)
            np.savez(output/f'geometry_{split}_{cluster:02d}.npz',**case)
            for observation in range(CONFIG['observations_per_cluster']):
                xi=rng.normal(size=8)*CONFIG['xi_sd']
                prior_logits=case['log_prior']+case['z']@xi
                state=int(rng.choice(len(prior_logits),p=np.exp(prior_logits-logsumexp(prior_logits))))
                y=case['f'][state]+rng.normal(size=4)*np.sqrt(CONFIG['sigma2']/2)
                eta=2*y/CONFIG['sigma2']
                variants=[('base',case,xi)]
                if split=='test':
                    variants += [(kind,*transform_case(case,xi,kind)) for kind in ['path_permutation','joint_phase']]
                for variant,current,current_xi in variants:
                    before=time.perf_counter()
                    exact=finite_potential(current['z'],current['f'],current['log_prior'],eta,current_xi,CONFIG['sigma2'])
                    teacher_seconds+=time.perf_counter()-before
                    diff_f,diff_energy=meanfield_statistics(current,CONFIG['sigma2'])
                    arrays.append(dict(features=features_for(current,eta,current_xi,CONFIG['sigma2']),
                         teacher_mean=exact['mean_z'],teacher_response=exact['cov_z_f']@V,
                         teacher_cov=exact['cov_z'],probability=exact['probabilities'],
                         states=current['z'],physical_logits=diff_f@eta-diff_energy,
                         response_projection=diff_f@V,eta=eta,xi=current_xi,y=y,
                         generated_state=current['z'][state]))
                    records.append(dict(index=len(records),split=split,cluster=cluster,observation=observation,
                         family=family,variant=variant,center=float(center),stride=stride))
    data={key:np.stack([row[key] for row in arrays]) for key in arrays[0]}
    np.savez(output/'dataset.npz',**data)
    dump(output/'dataset_records.json',records)
    return data,records,dict(total_seconds=time.perf_counter()-start,teacher_direct_seconds=teacher_seconds,
              teacher_evaluations=len(records),independent_geometry_clusters=24,
              base_observations=192,transformed_paired_observations=128)


def mask_for(records,split,variant='base'):
    return np.array([r['split']==split and r['variant']==variant for r in records])


def score_cohort(mean,response,target_mean,target_response,probability,states):
    if not np.isfinite(mean).all() or not np.isfinite(response).all():
        raise FloatingPointError('nonfinite prediction; retain invalid attempt')
    support_bad=np.any(abs(mean)>.5+CONFIG['support_tolerance'],axis=1)
    p0=.5+mean[:,[2,3,6,7]];truth_p0=.5+target_mean[:,[2,3,6,7]]
    proper=None
    # No clipping and no score computed on only the valid subset.
    if np.all((p0>0)&(p0<1)) and not support_bad.any():
        proper=dict(expected_brier=np.mean(truth_p0*(1-p0)**2+(1-truth_p0)*p0**2,axis=1),
                    expected_logscore=np.mean(-truth_p0*np.log(p0)-(1-truth_p0)*np.log1p(-p0),axis=1))
    actions=np.where(mean>=0,.5,-.5)
    selected=np.all(states==actions[:,None,:],axis=2)
    if not np.all(selected.sum(axis=1)==1):
        raise AssertionError('hard product-mode action missing from legal finite support')
    mass=np.sum(probability*selected,axis=1);best=probability.max(axis=1)
    return dict(mean_mse=np.mean((mean-target_mean)**2,axis=1),
                response_mse=np.mean((response-target_response)**2,axis=1),
                mode_mass_regret=best-mass,hard_action_map_match=(abs(best-mass)<1e-12).astype(float),
                support_invalid=support_bad.astype(float)),proper


def cluster_summary(values,records,mask):
    clusters=sorted(set(r['cluster'] for r,m in zip(records,mask) if m))
    aggregate=np.array([np.mean(values[[r['cluster']==c for r,m in zip(records,mask) if m]]) for c in clusters])
    return aggregate


def uncertainty(cluster_values):
    rng=np.random.default_rng([*CONFIG['seed_namespace'],72,999])
    if len(cluster_values)!=8:
        return dict(mean=float(np.mean(cluster_values)),clusters=len(cluster_values))
    a=cluster_values[:4][rng.integers(4,size=(CONFIG['bootstrap_replicates'],4))]
    b=cluster_values[4:][rng.integers(4,size=(CONFIG['bootstrap_replicates'],4))]
    samples=np.concatenate([a,b],axis=1).mean(axis=1)
    return dict(mean=float(np.mean(cluster_values)),ci95=np.quantile(samples,[.025,.975]).tolist(),
                clusters=8,interpretation='descriptive stratified geometry bootstrap; small development experiment')


def fit_network(kind,seed,data,train_mask,validation_mask,output):
    torch.manual_seed(1000+seed)
    model=SharedPotential() if kind=='shared' else IndependentHeads()
    expected=CONFIG['shared_parameters'] if kind=='shared' else CONFIG['independent_parameters']
    parameters=sum(p.numel() for p in model.parameters())
    if parameters!=expected:
        raise AssertionError('registered parameter count differs')
    x=torch.as_tensor(data['features'][train_mask]);tm=torch.as_tensor(data['teacher_mean'][train_mask]);tr=torch.as_tensor(data['teacher_response'][train_mask])
    optimizer=torch.optim.Adam(model.parameters(),lr=CONFIG['lr']);curve=[];started=time.perf_counter()
    for step in range(CONFIG['steps']):
        optimizer.zero_grad(set_to_none=True)
        mean,response,_=predict(model,x,training=True)
        loss=((mean-tm)**2).mean()+((response-tr)**2).mean()
        if not torch.isfinite(loss):
            raise FloatingPointError('nonfinite network training objective')
        loss.backward();optimizer.step()
        if step==0 or (step+1)%20==0:
            curve.append(dict(step=step+1,loss=float(loss.detach())))
    vm,vr,_=predict(model,torch.as_tensor(data['features'][validation_mask]))
    validation_loss=float(np.mean((vm.detach().numpy()-data['teacher_mean'][validation_mask])**2)
                          +np.mean((vr.detach().numpy()-data['teacher_response'][validation_mask])**2))
    seconds=time.perf_counter()-started
    torch.save(model.state_dict(),output/f'{kind}_seed{seed}.pt')
    return model,dict(kind=kind,seed=seed,parameters=parameters,training_seconds=seconds,
                      final_validation_loss=validation_loss,curve=curve)


def fit_step(data,train_mask,output):
    raw=nn.Parameter(torch.tensor(np.log(np.expm1(1.)),dtype=torch.float64))
    optimizer=torch.optim.Adam([raw],lr=CONFIG['lr'])
    xi=torch.as_tensor(data['xi'][train_mask]);b=torch.as_tensor(data['physical_logits'][train_mask]);d=torch.as_tensor(data['response_projection'][train_mask])
    tm=torch.as_tensor(data['teacher_mean'][train_mask]);tr=torch.as_tensor(data['teacher_response'][train_mask])
    curve=[];started=time.perf_counter()
    for step in range(CONFIG['steps']):
        optimizer.zero_grad(set_to_none=True);alpha=nn.functional.softplus(raw)
        t=torch.tanh((xi+alpha*b)/2);mean=.5*t;response=.25*(1-t*t)*alpha*d
        loss=((mean-tm)**2).mean()+((response-tr)**2).mean();loss.backward();optimizer.step()
        if step==0 or (step+1)%20==0:
            curve.append(dict(step=step+1,loss=float(loss.detach())))
    alpha=float(nn.functional.softplus(raw).detach())
    result=dict(alpha=alpha,parameters=1,training_seconds=time.perf_counter()-started,curve=curve)
    dump(output/'learned_step.json',result)
    return alpha,result


def evaluate_network(model,features):
    x=torch.as_tensor(features);before=time.perf_counter()
    mean,response,cov=predict(model,x,covariance=isinstance(model,SharedPotential))
    result=dict(mean=mean.detach().numpy(),response=response.detach().numpy())
    if cov is not None:
        result['covariance']=cov.detach().numpy()
    full_seconds=time.perf_counter()-before
    eps=CONFIG['source_fd_step'];xp=features.copy();xm=features.copy()
    xp[:,:4]+=eps*V/CONFIG['eta_feature_scale'];xm[:,:4]-=eps*V/CONFIG['eta_feature_scale']
    plus=predict(model,torch.as_tensor(xp))[0].detach().numpy()
    minus=predict(model,torch.as_tensor(xm))[0].detach().numpy()
    result['response_consistency_error']=np.max(abs((plus-minus)/(2*eps)-result['response']),axis=1)
    # Measured real derivative output path, excludes covariance audit and FD checks.
    trials=[]
    for _ in range(3):
        start=time.perf_counter();predict(model,x);trials.append(time.perf_counter()-start)
    return result,dict(full_prediction_and_covariance_seconds=full_seconds,
                       output_batch_seconds=trials,observations=len(features),
                       per_observation_output_seconds=float(np.median(trials))/len(features))


def calculate(output):
    from experiments.afdm_structured_inference_20261003.test_learn import LearningTests
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(LearningTests)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    dump(output/'tests.json',dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),output=stream.getvalue()))
    if not result.wasSuccessful():
        raise AssertionError('learning contract tests failed')
    data,records,cost=generate_data(output);train=mask_for(records,'train')
    alpha,step_training=fit_step(data,train,output)
    training=[];predictions={};timings={};all_clusters={};summaries={}
    schedule=[(kind,seed) for seed in CONFIG['network_seeds'] for kind in ['shared','independent']]
    rng=np.random.default_rng([*CONFIG['seed_namespace'],70,998]);rng.shuffle(schedule)
    for kind,seed in schedule:
        model,log=fit_network(kind,seed,data,train,mask_for(records,'validation'),output);training.append(log)
        values,timing=evaluate_network(model,data['features'])
        predictions[f'{kind}_seed{seed}']=values;timings[f'{kind}_seed{seed}']=timing
    for name,value in [('analytic_meanfield',1.),('learned_step',alpha)]:
        before=time.perf_counter()
        mean,response=meanfield_prediction(data['xi'],data['physical_logits'],data['response_projection'],value)
        predictions[name]=dict(mean=mean,response=response,covariance=np.array([np.diag(.25-m*m) for m in mean]))
        timings[name]=dict(batch_seconds=time.perf_counter()-before,observations=len(mean),
                           note='geometry/cavity statistic preprocessing is in dataset cost; not free in deployment')
    predictions['exact_teacher']=dict(mean=data['teacher_mean'],response=data['teacher_response'],covariance=data['teacher_cov'])
    for name,values in predictions.items():
        np.savez(output/f'predictions_{name}.npz',**values)
        cohort_summary={};all_clusters[name]={}
        cohorts=[('validation','base'),('test','base'),('test','path_permutation'),('test','joint_phase')]
        for split,variant in cohorts:
            mask=mask_for(records,split,variant);key=f'{split}/{variant}'
            metrics,proper=score_cohort(values['mean'][mask],values['response'][mask],data['teacher_mean'][mask],
                    data['teacher_response'][mask],data['probability'][mask],data['states'][mask])
            all_clusters[name][key]={}
            for metric,array in metrics.items():
                cluster=cluster_summary(array,records,mask);all_clusters[name][key][metric]=cluster
            details={metric:uncertainty(array) for metric,array in all_clusters[name][key].items()}
            details['proper_score_status']='valid marginal probabilities over entire cohort' if proper is not None else 'not_admitted: at least one invalid/out-of-domain probability; no subset score'
            if proper is not None:
                details['proper_scores']={k:uncertainty(cluster_summary(v,records,mask)) for k,v in proper.items()}
            if 'covariance' in values:
                covariance=values['covariance'][mask];mean=values['mean'][mask]
                details['covariance_contract']=dict(min_eigenvalue=float(np.linalg.eigvalsh(covariance).min()),
                    symmetry_max_error=float(np.max(abs(covariance-np.swapaxes(covariance,1,2)))),
                    finite_support_diagonal_max_error=float(np.max(abs(np.diagonal(covariance,axis1=1,axis2=2)-(.25-mean*mean)))))
            else:
                details['covariance_contract']='not supplied by independent heads; no covariance claim'
            if 'response_consistency_error' in values:
                details['response_consistency_max_error']=float(values['response_consistency_error'][mask].max())
            cohort_summary[key]=details
        summaries[name]=cohort_summary
    comparisons={}
    for key in ['test/base','test/path_permutation','test/joint_phase']:
        comparisons[key]={}
        for metric in ['mean_mse','response_mse','mode_mass_regret']:
            family={kind:np.mean([all_clusters[f'{kind}_seed{seed}'][key][metric] for seed in CONFIG['network_seeds']],axis=0)
                    for kind in ['shared','independent']}
            comparisons[key][metric]=dict(shared=uncertainty(family['shared']),independent=uncertainty(family['independent']),
                        paired_shared_minus_independent=uncertainty(family['shared']-family['independent']))
    dump(output/'training.json',dict(networks=training,step=step_training,schedule=schedule))
    dump(output/'metrics.json',summaries)
    return dict(status='completed bounded learned comparison',config=CONFIG,data_cost=cost,training=training,
         step_training=step_training,inference_timing=timings,comparisons=comparisons,
         total_trainable_parameters=dict(shared=1121,independent=1116,step=1),
         architectural_boundary='shared convexity gives PSD/integrability, not exact finite-support moments; no clipping',
         teacher_numeric_reference='potential_v1 finite-difference consistency <=2.2e-11; exact finite enumeration',
         production_receiver_calls=0,production_hessian_calls=0,
         scope='local finite working model; 8 heldout geometry clusters, transformations paired; no production gain claim')


if __name__=='__main__':
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    sources=[__file__,Path(__file__).with_name('test_learn.py'),Path(__file__).with_name('potential.py'),
             ROOT/'.mission/20261003_10-41-29-afdm-structured-inference-exploration/learn_config.json',
             ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
             ROOT/'experiments/afdm_inference_causal_20261002/oracle_comparison.py',
             ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
             ROOT/'experiments/sp_afdm_frozen_20260920/src/messages.py',
             ROOT/'experiments/sp_afdm_native_joint_20260921/src/twofft.py']
    run('learn_v1',CONFIG,sources,calculate)
