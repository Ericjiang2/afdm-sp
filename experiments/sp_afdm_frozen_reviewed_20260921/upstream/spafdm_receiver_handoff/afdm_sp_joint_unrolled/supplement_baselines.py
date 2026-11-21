"""New supplement initial-estimator catalogue; old eight recipes remain frozen.

B0/ridge/SBL change initial CE. Group/parameterized families retain the old
Bstar outer receiver and refit its terminal channel before the shared BP/LDPC.
No data generation, selection, or experiment execution occurs in this module.
"""
from __future__ import annotations

import copy
import math
import time
import numpy as np
import torch

from .classical_joint_unrolled import omp_sparse_torch
from .direction_receiver import ObservedReceiver
from .direction_data import ReceiverDomain
from .direction_physical_receiver import PhysicalChannelRefit
from .direction_physical import _centers, _search
from .afdm_baselines import construct_sensing_matrix
from .afdm_env import AFDMEnvMixin
from .budgeted_support_diagnostics import array_hash

PARAMETERS = {
    'B0': (8,16,24,40),
    'ridge': (1e-4,1e-3,1e-2,1e-1),
    'SBL': (1e-4,1e-3,1e-2,1e-1),
    'group': (.25,.5,1.,2.),
    'bounded-param': (2,4,6,8),
}


def catalogue():
    return [dict(id=f'{family}-p{index}-s{scale:g}',family=family,parameter=parameter,
                 terminal_scale=scale,parameter_index=index,
                 stage='terminal_refit' if family in ('group','bounded-param') else 'initial_CE')
            for family,parameters in PARAMETERS.items() for index,parameter in enumerate(parameters)
            for scale in (.5,1.)]


def a02_catalogue():
    """Frozen nine-arm A-02 interface; separate from the 40 baseline recipes."""
    old={row['id']:row for row in catalogue()}
    rows=[]
    for identifier,role in (('B0-p2-s0.5','Bstar'),('group-p3-s1','group'),
                            ('bounded-param-p3-s1','hard')):
        row=copy.deepcopy(old[identifier])
        row.update(id=f'A02-{role}',a02_role=role,source_recipe_id=identifier)
        rows.append(row)
    for index,value in enumerate((0.,.001,.01,.1,1.)):
        rows.append(dict(id=f'A02-soft-lambda{value:g}',family='soft',parameter=value,
            normalized_lambda=value,terminal_scale=1.,parameter_index=index,
            stage='terminal_refit',a02_role='soft',outer_receiver_kind='ObservedReceiver',
            outer_receiver_family='sbl',outer_receiver_parameter=.001,
            matched_hard_recipe_id='bounded-param-p3-s1'))
    rows.append(dict(id='A02-reference',family='reference',parameter=None,
        terminal_scale=1.,parameter_index=0,stage='terminal_refit',
        a02_role='reference',outer_receiver_kind='ObservedReceiver',
        outer_receiver_family='sbl',outer_receiver_parameter=.001,
        matched_hard_recipe_id='bounded-param-p3-s1',deployment_eligible=False))
    return rows


def recipe_by_id(identifier):
    matches=[r for r in catalogue()+a02_catalogue() if r['id']==identifier]
    if len(matches)!=1:raise ValueError('unknown supplement baseline recipe')
    return matches[0]


def sbl_em(A,y,sigma,initial,*,max_iter=2000,tolerance=1e-6):
    """Complex Gaussian type-II ML EM, fixed observed variance, no hidden jitter.

    Objective is logdet(sigma I+A diag(gamma) A^H)+y^H C^-1 y.
    K-dimensional posterior identities avoid materializing the N-square C.
    """
    A,y,initial=[np.asarray(v,dtype=np.complex128) for v in (A,y,initial)]
    if (A.ndim!=2 or y.shape!=(A.shape[0],) or initial.shape!=(A.shape[1],) or
            A.shape[1]==0 or not math.isfinite(float(sigma)) or sigma<=0 or
            any(not np.isfinite(v).all() for v in (A,y,initial)) or
            type(max_iter) is not int or max_iter<1 or not 0<tolerance<=1e-3):
        raise ValueError('invalid SBL inputs/bounds')
    gram=A.conj().T@A;rhs=A.conj().T@y/sigma
    scale=float(np.trace(gram).real/A.shape[1])
    if scale<=0:raise ValueError('SBL requires positive dictionary energy')
    floor=max(np.finfo(float).tiny,np.finfo(float).eps*float(np.vdot(y,y).real/len(y))/scale)
    gamma=np.maximum(np.abs(initial)**2,floor)
    def posterior(g):
        precision=gram/sigma+np.diag(1/g)
        factor=np.linalg.cholesky(precision)
        from scipy.linalg import cho_solve
        covariance=cho_solve((factor,True),np.eye(len(g)),check_finite=True)
        mu=cho_solve((factor,True),rhs,check_finite=True)
        objective=float(len(y)*np.log(sigma)+np.log(g).sum()+
            2*np.log(factor.diagonal().real).sum()+np.vdot(y,y).real/sigma-np.vdot(rhs,mu).real)
        if not np.isfinite(objective) or not np.isfinite(mu).all() or not np.isfinite(covariance).all():
            raise FloatingPointError('nonfinite SBL posterior')
        return mu,covariance,objective
    mu,cov,objective=posterior(gamma)
    history=[objective];converged=False
    for iteration in range(1,max_iter+1):
        updated=np.abs(mu)**2+cov.diagonal().real
        if not np.isfinite(updated).all() or np.any(updated<=0):
            raise FloatingPointError('invalid SBL variance update')
        relative=float(np.linalg.norm(updated-gamma)/np.linalg.norm(gamma))
        next_mu,next_cov,next_objective=posterior(updated)
        if next_objective>objective+1e-8*max(1.,abs(objective)):
            raise FloatingPointError('SBL evidence objective increased beyond numerical tolerance')
        objective_change=abs(next_objective-objective)/max(1.,abs(objective))
        gamma,mu,cov,objective=updated,next_mu,next_cov,next_objective
        history.append(objective)
        if relative<=tolerance and objective_change<=tolerance:
            converged=True;break
    diagnostics=dict(iterations=iteration,max_iterations=max_iter,converged=converged,
        eligible=converged,relative_gamma_update=relative,relative_objective_change=objective_change,
        objective_history=history,initialization_floor=floor,tolerance=tolerance,
        posterior_solves=iteration+1,convergence_scope='EM fixed-point/evidence tolerance; not global ML optimum')
    if not converged:
        raise RuntimeError(f'SBL did not converge within declared cap: {diagnostics}')
    return mu,gamma,diagnostics


class BaselineInitializer:
    def __init__(self,identifier,*,geometry=None,lstsq_driver=None,dictionary_limit=515):
        self.recipe=recipe_by_id(identifier)
        if self.recipe['stage']!='initial_CE':
            raise ValueError('group/parameterized families require terminal refit, not initial CE')
        self.geometry=geometry
        if lstsq_driver not in (None,'gels','gelsy','gelsd','gelss'):
            raise ValueError('unknown initializer least-squares driver')
        self.lstsq_driver=lstsq_driver
        if type(dictionary_limit) is not int or dictionary_limit < 40:
            raise ValueError('initial CE dictionary limit must cover the fixed capacity')
        self.dictionary_limit=dictionary_limit
        self.record=None
        self.coefficients=None

    def __call__(self,y,Phi,capacity,sigma2):
        if (capacity!=40 or y.ndim!=1 or Phi.ndim!=2 or Phi.shape[0]!=len(y) or
                Phi.shape[1]<40 or Phi.shape[1]>self.dictionary_limit or not torch.isfinite(y).all() or
                not torch.isfinite(Phi).all() or not math.isfinite(float(sigma2)) or float(sigma2)<=0):
            raise ValueError('invalid observed initial CE boundary')
        started=time.perf_counter();r=self.recipe;family=r['family'];parameter=r['parameter']
        nomination=parameter if family=='B0' else 40
        h,support=omp_sparse_torch(y,Phi,nomination,lstsq_driver=self.lstsq_driver)
        self.record=dict(recipe=copy.deepcopy(r),truth_access='none',omp_budget=nomination,
            omp_selected=len(support),query_limit=73,physical_queries=0,converged=True,eligible=True,
            stopping='fixed OMP nomination budget; not global sparse recovery optimum')
        if self.lstsq_driver is not None:
            self.record['lstsq_driver']=self.lstsq_driver
        if support and family!='B0':
            ids=np.asarray(support,dtype=int)
            A=Phi[:,support].detach().cpu().numpy().astype(np.complex128)
            observed=y.detach().cpu().numpy().astype(np.complex128)
            gains=h[support].detach().cpu().numpy().astype(np.complex128)
            if family=='ridge':
                lam=float(parameter*np.linalg.norm(A,'fro')**2/len(ids))
                augmented=np.vstack((A,np.sqrt(lam)*np.eye(len(ids))))
                target=np.concatenate((observed,np.zeros(len(ids))))
                gains=np.linalg.lstsq(augmented,target,rcond=None)[0]
                residual=A.conj().T@(A@gains-observed)+lam*gains
                stationarity=float(np.linalg.norm(residual)/max(1.,np.linalg.norm(A.conj().T@observed)))
                if stationarity>1e-8:raise FloatingPointError('ridge normal-equation residual too large')
                self.record.update(lambda_actual=lam,relative_stationarity=stationarity,linear_solves=1)
            elif family=='SBL':
                gains,gamma,detail=sbl_em(A,observed,float(sigma2),gains)
                selected=gamma>=parameter*gamma.max()
                ids=ids[selected];gains=gains[selected];support=ids.tolist()
                self.record.update(detail,pruning='final gamma threshold; final posterior mean; no LS debias')
            h=torch.zeros(Phi.shape[1],dtype=y.dtype,device=y.device)
            h[support]=torch.as_tensor(gains,dtype=y.dtype,device=y.device)
        if not torch.isfinite(h).all():raise FloatingPointError('nonfinite final initial CE')
        self.record.update(support=list(support),seconds=time.perf_counter()-started)
        self.coefficients=h.detach().cpu().numpy().copy()
        return h,support


class _InitializerModel:
    def __init__(self,model,estimator):
        self.model,self.estimator=model,estimator
        self.cfg,self.use_soft_decisions=model.cfg,model.use_soft_decisions

    def __call__(self,*args,**kwargs):
        kwargs['initial_estimator']=self.estimator
        return self.model(*args,**kwargs)


class BaselineTerminalRefit:
    """Keep the existing strong terminal path; default settings call it directly."""
    def __init__(self,system,identifier):
        self.recipe=recipe_by_id(identifier)
        if self.recipe['stage']!='terminal_refit':raise ValueError('not a terminal refit recipe')
        family=self.recipe['family']
        arm={'group':'m-group','bounded-param':'m-param-budget','soft':'m-soft',
             'reference':'m-param-reference'}[family]
        kwargs=({'soft_lambda_normalized':self.recipe['normalized_lambda']}
                if family=='soft' else {})
        self.original=PhysicalChannelRefit(system,arm,**kwargs)

    def __call__(self,*,y,pilot,H,x_soft,support,gains,sigma_base):
        parameter=self.recipe['parameter']
        if self.recipe['family']=='group':
            result=self.original(y=y,pilot=pilot,H=H,x_soft=x_soft,support=support,
                gains=gains,sigma_base=sigma_base*parameter**2)
            result['diagnostics']['lambda_multiplier']=parameter
            result['diagnostics']['noise_variance_unchanged']=float(sigma_base)
            return result
        if self.recipe['family'] in ('soft','reference'):
            result=self.original(y=y,pilot=pilot,H=H,x_soft=x_soft,support=support,
                gains=gains,sigma_base=sigma_base)
            if self.recipe['family']=='soft':
                result['diagnostics']['admission_scope']=(
                    'completed fixed one-sweep finite algorithm; stationarity is diagnostic only')
            else:
                result['diagnostics']['admission_scope']=(
                    'bounded high-compute reference; stationarity reported; not deployment eligible')
                result['diagnostics']['deployment_eligible']=False
            return result
        if parameter==8:
            return self.original(y=y,pilot=pilot,H=H,x_soft=x_soft,support=support,
                                 gains=gains,sigma_base=sigma_base)
        g=self.original.geometry;ids=np.asarray(support)
        arrays=[np.asarray(v,dtype=np.complex128) for v in (y,pilot,H,x_soft,gains)]
        y,pilot,H,x_soft,gains=arrays
        if (ids.ndim!=1 or (ids.size and ids.dtype.kind not in 'iu') or len(ids)>40 or
                len(set(ids.tolist()))!=len(ids) or np.any(ids<0) or np.any(ids>=515) or
                y.shape!=(g.N_total,) or pilot.shape!=y.shape or x_soft.shape!=y.shape or
                H.shape!=(g.N_total,g.N_total) or gains.shape!=(len(ids),) or
                any(not np.isfinite(v).all() for v in arrays) or
                not math.isfinite(float(sigma_base)) or sigma_base<=0):
            raise ValueError('invalid observed terminal refit boundary')
        ids=ids.astype(int)
        if len(ids)==0:
            return self.original(y=y,pilot=pilot,H=H,x_soft=x_soft,support=[],gains=gains,sigma_base=sigma_base)
        A=construct_sensing_matrix(g.N_total,pilot+x_soft,g.c1,g.c2,g.l_max_cap,g.k_max_cap)[:,ids]
        centers=_centers(ids,gains,5,2)[:parameter]
        selected,diagnostics=_search(g,y,A,ids,centers,False)
        coefficients=selected['coefficients']
        fitted=AFDMEnvMixin.gen_h_daft(g,coefficients,ids//5,ids%5-2)
        diagnostics.update(truth_access='none',center_limit=parameter,coefficient_dimension=len(ids),
            A_sha256=array_hash(A),H_before_sha256=array_hash(H),H_after_sha256=array_hash(fitted),
            sensing_input='pilot+x_soft; already power-scaled',sigma_policy='unchanged terminal sigma',
            fallback=None,rank=selected['details']['rank'])
        return dict(H=fitted,gains=coefficients,diagnostics=diagnostics)


class BaselineReceiver:
    """New catalogue adapter; the original ObservedReceiver whitelist is untouched."""
    def __init__(self,model,code,identifier,*,system=None,initial_lstsq_driver=None,receiver_domain=None):
        self.recipe=recipe_by_id(identifier)
        if receiver_domain is not None and (type(receiver_domain) is not ReceiverDomain
                or self.recipe['stage'] != 'initial_CE'):
            raise ValueError('explicit receiver domain requires an initial-CE recipe')
        domain_args={} if receiver_domain is None else dict(domain=receiver_domain)
        initializer_args={} if receiver_domain is None else dict(dictionary_limit=receiver_domain.dictionary_columns)
        self.refit=None;self.estimator=None
        if self.recipe['stage']=='terminal_refit':
            if initial_lstsq_driver is not None:
                raise ValueError('explicit initializer driver requires an initial-CE recipe')
            if system is None:raise ValueError('public geometry required')
            self.refit=BaselineTerminalRefit(system,identifier)
            self.receiver=ObservedReceiver(model,code,**domain_args)
        else:
            self.estimator=BaselineInitializer(identifier,lstsq_driver=initial_lstsq_driver,**initializer_args)
            self.receiver=ObservedReceiver(_InitializerModel(model,self.estimator),code,**domain_args)

    def run(self,observed,*,audit=True,code_feedback=None,bp_schedule=None,terminal_transform=None,
            dals_mode='mean',dals_strength=1.,outer_iteration_limit=None,ce_update_iterations=None,dals_start_iteration=1,ce_support_exchange=None,detector=None,bp_edge_projection=None,terminal_check_prior=None,outer_bp_graph=None,
                 terminal_bp_temperature=None,terminal_variance_source=None,dals_prior=None,one_shot_true_data_ce=None):
        return self._execute(observed,audit=audit,code_feedback=code_feedback,bp_schedule=bp_schedule,
                             terminal_transform=terminal_transform,dals_mode=dals_mode,dals_strength=dals_strength,
                             outer_iteration_limit=outer_iteration_limit,ce_update_iterations=ce_update_iterations,
                             dals_start_iteration=dals_start_iteration,ce_support_exchange=ce_support_exchange,detector=detector,bp_edge_projection=bp_edge_projection,terminal_check_prior=terminal_check_prior,outer_bp_graph=outer_bp_graph,
                             terminal_bp_temperature=terminal_bp_temperature,terminal_variance_source=terminal_variance_source,dals_prior=dals_prior,
                             one_shot_true_data_ce=one_shot_true_data_ce)

    def run_diagnostic(self,observed,*,diagnostic_code_symbols,audit=True,bp_schedule=None):
        from .supplement_feedback_diagnostic import DiagnosticCodeSymbols
        if type(diagnostic_code_symbols) is not DiagnosticCodeSymbols:
            raise ValueError('explicit diagnostic controller required')
        return self._execute(observed,audit=audit,diagnostic_code_symbols=diagnostic_code_symbols,bp_schedule=bp_schedule)

    def _execute(self,observed,*,audit=True,code_feedback=None,diagnostic_code_symbols=None,bp_schedule=None,
                 terminal_transform=None,dals_mode='mean',dals_strength=1.,outer_iteration_limit=None,ce_update_iterations=None,dals_start_iteration=1,ce_support_exchange=None,detector=None,bp_edge_projection=None,terminal_check_prior=None,outer_bp_graph=None,
                 terminal_bp_temperature=None,terminal_variance_source=None,dals_prior=None,one_shot_true_data_ce=None):
        if one_shot_true_data_ce is not None and diagnostic_code_symbols is not None:
            raise ValueError('one-shot true data CE cannot combine with symbol diagnostic')
        run=self.receiver.run if diagnostic_code_symbols is None else self.receiver.run_diagnostic
        feedback_args=({'code_feedback':code_feedback} if diagnostic_code_symbols is None else
                       {'diagnostic_code_symbols':diagnostic_code_symbols})
        if dals_prior is not None:feedback_args['dals_prior']=dals_prior
        if one_shot_true_data_ce is not None:feedback_args['one_shot_true_data_ce']=one_shot_true_data_ce
        if terminal_check_prior is not None:feedback_args['terminal_check_prior']=terminal_check_prior
        if terminal_bp_temperature is not None:feedback_args['terminal_bp_temperature']=terminal_bp_temperature
        if terminal_variance_source is not None:feedback_args['terminal_variance_source']=terminal_variance_source
        if outer_bp_graph is not None:feedback_args['outer_bp_graph']=outer_bp_graph
        if detector is not None:feedback_args['detector']=detector
        if bp_edge_projection is not None:feedback_args['bp_edge_projection']=bp_edge_projection
        if bp_schedule is not None:feedback_args['bp_schedule']=bp_schedule
        if isinstance(dals_strength,bool) or dals_mode != 'mean' or dals_strength != 1.:
            feedback_args.update(dals_mode=dals_mode,dals_strength=dals_strength)
        if outer_iteration_limit is not None:feedback_args['outer_iteration_limit']=outer_iteration_limit
        if ce_update_iterations is not None:feedback_args['ce_update_iterations']=ce_update_iterations
        if type(dals_start_iteration) is not int or dals_start_iteration != 1:
            feedback_args['dals_start_iteration']=dals_start_iteration
        if ce_support_exchange is not None:feedback_args['ce_support_exchange']=ce_support_exchange
        if self.refit is not None:
            if terminal_transform is not None:
                raise ValueError('cancellation transform cannot combine with terminal refit')
            result=run(observed,family='sbl',parameter=.001,
                terminal_scale=self.recipe['terminal_scale'],audit=audit,channel_refit=self.refit,
                **feedback_args)
            initial=result['initial_estimator']
            refit=result['channel_refit']['diagnostics']
            # A completed fixed one-sweep algorithm is a valid budget candidate.
            # Stationarity is evidence about optimization, not an extra runtime gate.
            if 'converged' not in initial:
                raise ValueError('old Bstar initializer did not report convergence qualification')
            family=self.recipe['family']
            refit_eligible=(family in ('bounded-param','soft','reference') or
                            bool(refit['converged']))
            eligible=bool(initial['converged'] and refit_eligible)
            result['baseline_stationary']=bool(refit['converged'])
            if family=='reference':
                result['deployment_eligible']=False
                result['baseline_eligibility_scope']=(
                    'high-compute reference evidence only; not deployment eligible')
        else:
            if terminal_transform is not None:
                feedback_args['terminal_transform']=terminal_transform
            result=run(observed,family='b0',parameter=None,
                terminal_scale=self.recipe['terminal_scale'],audit=audit,**feedback_args)
            result['initial_estimator']=copy.deepcopy(self.estimator.record)
            eligible=bool(self.estimator.record['eligible'])
        result['baseline_recipe']=copy.deepcopy(self.recipe)
        result['baseline_eligible']=eligible and not (
            code_feedback is not None and code_feedback.diagnostic_perturbation is not None)
        return result
