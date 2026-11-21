"""Executable observed-only frozen-backbone receiver and declared competitors.
The corrected tree adds one optional, observation-only upstream decoder hook.
The default upstream path remains unchanged and no duplicate terminal pass is performed.
Primary scope N=1024, Pd=.5, frozen I-then-Q LDPC mapping, CPU.
"""
from pathlib import Path
from types import SimpleNamespace
import sys,time,numpy as np
UP=Path(__file__).resolve().parents[1]/'upstream'/'spafdm_receiver_handoff'
sys.path.insert(0,str(UP))
import torch
from run_frozen_i1_smoke import build
from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback,CONST
from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
from afdm_sp_joint_unrolled.supplement_messages import decoder_messages
from afdm_sp_joint_unrolled.e1_ldpc import extract_info
from afdm_sp_joint_unrolled.direction_receiver import terminal_decode
from physical import Channel,refine,sparse_apply,project_integer_matrix
from messages import moments,sparse_bp
from structured_ep import ep_t
from offgrid import estimate
from bilinear import pbigabp


def context():return build(SimpleNamespace(checkpoint=None))

def front(observed,model,code,outer_bp=12,refresh=(),outer_limit=None):
    """Exactly the existing formal I1 preterminal loop, no final BP/LDPC call."""
    y,pilot,noise=observed['y'],observed['pilot'],float(observed['sigma2']);cfg=model.cfg
    if len(y)!=cfg.N or cfg.rho!=.5:raise ValueError('Frozen backbone scope is N=1024, rho=.5')
    est=BaselineInitializer('B0-p2-s0.5',lstsq_driver='gels');ctl=CodeFeedback(code,checkpoint=1,refresh_checkpoints=tuple(refresh),retain_messages=True)
    kwargs=dict(enable_support_repair=False,receiver_extension=0,active_support_cap=40,initial_estimator=est,code_feedback=ctl,bp_schedule=UniformBPSchedule(outer_bp_iterations=outer_bp),bp_edge_projection='qpsk_tanh')
    if outer_limit is not None:kwargs['outer_iteration_limit']=outer_limit
    start=time.perf_counter();timeline=[];ce_inputs=[]
    old_after=ctl.after_detection;old_ce=ctl.ce
    def timed_after(iteration):
        old_after(iteration)
        if ctl.records and ctl.records[-1].get('stage')=='decoder':
            app=np.asarray(ctl.records[-1]['raw_app']);timeline.append(dict(iteration=iteration,ready_absolute=time.perf_counter(),decoded=(app<0).astype(np.uint8)))
    def logged_ce(iteration):
        m,v=old_ce(iteration);ce_inputs.append(dict(iteration=iteration,mu=m.detach().cpu().numpy().copy(),variance=v.detach().cpu().numpy().copy()));return m,v
    ctl.after_detection=timed_after;ctl.ce=logged_ce
    with torch.no_grad():out=model(torch.tensor(y,dtype=cfg.dtype),torch.tensor(pilot,dtype=cfg.dtype),torch.tensor(noise,dtype=cfg.rdtype),torch.as_tensor(CONST,dtype=cfg.dtype),**kwargs)
    arr=lambda k:out[k].detach().cpu().numpy().copy()
    state=dict(H=arr('H_est'),x_soft=arr('x_soft'),delays=arr('support_delays'),dopplers=arr('support_dopplers'),gains=arr('gains'),sigma_final=float(out['sigma2_final']),prior=ctl.prior.detach().cpu().numpy().copy(),channel_llr=ctl.channel.detach().cpu().numpy().copy(),mu=ctl.moments[0].detach().cpu().numpy().copy(),v=ctl.moments[1].detach().cpu().numpy().copy(),seconds=time.perf_counter()-start,decoder_records=ctl.records,source='formal_I1_preterminal')
    state.update(decision_timeline=timeline,ce_inputs=ce_inputs)
    return state

def finish(observed,state,system,code,configuration):
    cfg=dict(configuration);y=np.asarray(observed['y']);p=np.asarray(observed['pilot']);noise=float(observed['sigma2']);n=len(y);start=time.perf_counter();events=[];arrays={}
    if cfg.get('method')=='I1':
        decoder_records=[]
        r=terminal_decode(y-state['H']@p,state['H'],state['sigma_final']*.5,CONST,code,bp_iterations=cfg.get('terminal_iterations',20),bp_edge_projection='qpsk_tanh',decoder_observer=decoder_records.append)
        if len(decoder_records)!=1:raise RuntimeError('I1 terminal decoder record was not captured exactly once')
        dec=decoder_records[0];complete=time.perf_counter()-start
        decoder_seconds=float(r['decoder_seconds']);instrumentation_seconds=float(r['decoder_observer_seconds'])
        detector_seconds=max(0.,complete-decoder_seconds-instrumentation_seconds)
        arrays.update(final_llr=r['llr'],final_input=dec['incoming_llr'],final_app=dec['raw_app'],final_check=dec['raw_check_extrinsic'],final_detector_hard=r['x_hard'],final_detector_mu=r['mu'],final_detector_variance=r['var'])
        events.append(dict(stage='final_decoder',iterations=int(dec['iterations']),decode_ok=bool(dec['decode_ok']),instrumentation_seconds=instrumentation_seconds))
        return dict(decoded=r['decoded'],info_hat=r['info_hat'],llr=r['llr'],seconds=complete,refit_seconds=0.,detector_seconds=detector_seconds,decoder_seconds=decoder_seconds,instrumentation_seconds=instrumentation_seconds,decoder_records=decoder_records,events=events,arrays=arrays,configuration=cfg)
    qsource=cfg.get('qsource','latest');prior=state['prior'].copy();mu=state['mu'].copy();v=state['v'].copy();decoder_records=[];decoder_seconds=0.
    if qsource=='decoder_app':
        dec=decoder_messages(code,np.clip(state['channel_llr'],-20,20),maxiter=50);prior=np.clip(dec['raw_check_extrinsic'],-20,20);mu,v,_=moments(np.clip(dec['raw_app'],-20,20),.5)
        fresh_record=dict(dec,evidence_stage='fresh_decoder');decoder_records.append(fresh_record);decoder_seconds+=float(dec['metadata']['seconds'])
        events.append(dict(stage='fresh_decoder',iterations=int(dec['iterations']),metadata=dec['metadata']));arrays.update(refresh_input=dec['incoming_llr'],refresh_app=dec['raw_app'],refresh_check=dec['raw_check_extrinsic'])
    elif qsource=='x_soft':mu=state['x_soft'].copy();v=np.maximum(.5-abs(mu)**2,0)
    elif qsource=='extrinsic_only':mu,v,_=moments(prior,.5) # diagnostic only
    elif qsource!='latest':raise ValueError('Unknown qsource')
    arrays.update(ce_mu=mu,ce_variance=v,ce_prior=prior,ce_channel_llr=state['channel_llr'])
    seedtime=time.perf_counter();mode=cfg.get('ce_mode','mean');method=cfg.get('method','proposed')
    if method=='integer_control':
        c,project_error=project_integer_matrix(state['H'],system.c1,system.c2,state['delays'],state['dopplers']);detail={}
        if project_error>5e-5:raise FloatingPointError('Actual integer matrix not reproduced by projected coefficients')
        events.append(dict(stage='no_physical_refit',projection_relative_error=project_error))
    elif method in ('gamp','sbl'):
        if cfg.get('dictionary','full')=='full':
            ls=np.repeat(np.arange(system.l_max_cap+1),5);ks=np.tile(np.arange(-2,3),system.l_max_cap+1);gs=np.zeros(len(ls),complex)
            ids=state['delays'].astype(int)*5+state['dopplers'].astype(int)+2;gs[ids]=state['gains']
        else:ls,ks,gs=state['delays'],state['dopplers'],state['gains']
        c,detail=estimate(y,p+mu,system.c1,system.c2,noise,ls,ks,gs,backend='gamp' if method=='gamp' else 'exact',outer=cfg.get('grid_iterations',3),inner=cfg.get('gamp_iterations',30),damping=cfg.get('gamp_damping',.3),active_cap=cfg.get('path_cap',8),learn_noise=cfg.get('learn_ce_noise',True),initial_delta=state.get('sbl_delta'))
        arrays.update(sbl_full_dopplers=detail['full_dopplers'],sbl_full_gains=detail['full_gains'],sbl_delta=detail['delta'],sbl_posterior_variance=detail['posterior_variance']);events.extend(detail['history'])
    else:
        c,detail=refine(y,p,mu,v,state['delays'],state['dopplers'],state['gains'],system.c1,system.c2,noise,mode=mode,max_paths=cfg.get('path_cap',8),rounds=cfg.get('refit_passes',2))
        arrays.update(ce_objective_history=np.array(detail['history']),ce_gamma=detail['gamma']);events.append(dict(stage='refit',mode=mode,evaluations=detail['evaluations']))
    refit_seconds=time.perf_counter()-seedtime;arrays.update(path_delays=c.delays,path_dopplers=c.dopplers,path_gains=c.gains)
    nv=noise if cfg.get('noise','physical')=='physical' else .5*state['sigma_final']
    useprior=prior if cfg.get('retain_prior',True) else np.zeros(2*n)
    detector=cfg.get('detector','sparse');dstart=time.perf_counter()
    if detector=='ep':o=ep_t(y-c.apply(p),c,nv,.5,useprior,iterations=cfg.get('terminal_iterations',8),damping=cfg.get('ep_damping',.3))
    elif detector=='bilinear':o=pbigabp(y,p,c,nv,.5,useprior,iterations=cfg.get('terminal_iterations',8),damping=cfg.get('bilinear_damping',.3))
    else:
        weight=v if cfg.get('selection','variance')=='variance' else np.ones(n)
        M=cfg.get('diagonal_cap',24);tau=cfg.get('tail_tolerance');tau=None if tau is None else tau*n*noise
        keep,E,tail,qualified=c.select(weight,M,tau);D=c.diagonals(keep)
        weak=c.row_variance(v,keep) if cfg.get('weak_variance',True) else np.zeros(n)
        z=y-c.apply(p+mu)+sparse_apply(D,keep,mu) if cfg.get('preserve_mean',True) else y-sparse_apply(D,keep,p)
        wp=c.row_pseudovariance(mu.imag**2-mu.real**2,keep) if cfg.get('noncircular',False) else None
        o=sparse_bp(z,D,keep,nv,.5,useprior,weak,iterations=cfg.get('terminal_iterations',20),weak_pseudo=wp,noncircular=cfg.get('noncircular',False))
        arrays.update(selected_shifts=keep,diagonal_energy=E,selected_coefficients=D,weak_row_variance=weak,effective_y=z)
        events.append(dict(stage='graph',diagonals=len(keep),tail=tail,tolerance_satisfied=qualified,edges=n*len(keep)))
    if detector=='bilinear':arrays['path_gains']=o['gains'];arrays['path_gain_variance']=o['gain_variance']
    det_seconds=time.perf_counter()-dstart;llr=np.clip(o['extrinsic'],-20,20);dec=decoder_messages(code,llr,maxiter=50);decoder_seconds+=float(dec['metadata']['seconds']);decoder_records.append(dict(dec,evidence_stage='terminal_decoder'))
    arrays.update(final_input=llr,final_app=dec['raw_app'],final_check=dec['raw_check_extrinsic'],final_detector_app=o['app'],final_detector_mu=o['mu'],final_detector_variance=o['variance'])
    events.extend(o['trace']);events.append(dict(stage='final_decoder',iterations=int(dec['iterations']),decode_ok=bool(dec['decode_ok']),metadata=dec['metadata']))
    return dict(decoded=dec['decoded'],info_hat=extract_info(code,dec['decoded']),llr=llr,seconds=time.perf_counter()-start,refit_seconds=refit_seconds,detector_seconds=det_seconds,decoder_seconds=decoder_seconds,instrumentation_seconds=0.,decoder_records=decoder_records,events=events,arrays=arrays,configuration=cfg)

def run(observed,model,system,code,cfg):
    start=time.perf_counter();s=front(observed,model,code,cfg.get('outer_bp',12),cfg.get('refresh',()),cfg.get('outer_limit'))
    terminal_started=time.perf_counter()
    try:
        r=finish(observed,s,system,code,cfg)
    except (np.linalg.LinAlgError,FloatingPointError) as exc:
        if not s['decision_timeline']:raise
        dec=s['decision_timeline'][-1]['decoded'].copy()
        failed_terminal_seconds=time.perf_counter()-terminal_started
        r=dict(decoded=dec,info_hat=extract_info(code,dec),llr=s['channel_llr'].copy(),arrays={},refit_seconds=None,detector_seconds=None,decoder_seconds=None,instrumentation_seconds=None,failed_round_seconds=failed_terminal_seconds,stage_timing_scope='failed terminal stage split unavailable; complete time and failed terminal time retained',decoder_records=[],events=[dict(stage='numerical_fallback',error=repr(exc),output='last completed checkpoint',failed_terminal_seconds=failed_terminal_seconds)])
    r.update(front_seconds=s['seconds'],seconds_complete=time.perf_counter()-start)
    r['decision_timeline']=[dict(elapsed=e['ready_absolute']-start,decoded=e['decoded']) for e in s['decision_timeline']]+[dict(elapsed=r['seconds_complete'],decoded=r['decoded'])]
    return r,s

def pilot_front(observed,system,code):
    """Independent pilot-only initialization for native competitors; no I1 tax."""
    n=len(observed['y']);start=time.perf_counter();ls=np.repeat(np.arange(system.l_max_cap+1),5);ks=np.tile(np.arange(-2,3),system.l_max_cap+1)
    A=Channel(n,system.c1,system.c2,ls,ks,np.ones(len(ls))).regressors(observed['pilot'])
    est=BaselineInitializer('B0-p2-s0.5',lstsq_driver='gels')
    g,ids=est(torch.tensor(observed['y'],dtype=torch.complex64),torch.tensor(A,dtype=torch.complex64),40,float(observed['sigma2']))
    ids=np.asarray(ids,int);gs=g.detach().cpu().numpy()[ids].copy()
    return dict(delays=ls[ids],dopplers=ks[ids],gains=gs,mu=np.zeros(n,complex),v=np.full(n,.5),x_soft=np.zeros(n,complex),prior=np.zeros(2*n),channel_llr=np.zeros(2*n),sigma_final=float(observed['sigma2']),decoder_records=[],seconds=time.perf_counter()-start,source='observed_pilot_only')

def run_native(observed,system,code,cfg):
    """Independent coded rounds: detector extrinsic -> LDPC; APP -> next CE.
    Grid and variance-hyperparameter states persist in SBL/GAMP between coded rounds.
    This is a declared coded adaptation, not the original uncoded paper protocol.
    """
    start=time.perf_counter();s=pilot_front(observed,system,code);front_seconds=s['seconds'];snapshots=[];events=[];arrays={};cc=dict(cfg);round_timings=[];last_result=None;decoder_records=[]
    initial_state={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in s.items()}
    rounds=cfg.get('coded_rounds',3)
    if type(rounds) is not int or rounds<1:raise ValueError('coded_rounds must be a positive integer')
    for t in range(rounds):
        round_started=time.perf_counter()
        try:
            r=finish(observed,s,system,code,cc)
        except (np.linalg.LinAlgError,FloatingPointError) as exc:
            if not snapshots:raise
            failed_seconds=time.perf_counter()-round_started
            round_timings.append(dict(round=t,status='numerical_failure',seconds=failed_seconds,
                refit_seconds=None,detector_seconds=None,decoder_seconds=None,
                instrumentation_seconds=None,
                stage_timing_scope='failed native round stage split unavailable'))
            events.append(dict(stage='numerical_fallback',round=t,error=repr(exc),output='last completed native round',failed_round_seconds=failed_seconds))
            break
        last_result=r
        decoder_records.extend(dict(round=t,record=value) for value in r.get('decoder_records',[]))
        snapshots.append(dict(round=t,elapsed=time.perf_counter()-start,decoded=r['decoded'].copy(),llr=r['llr'].copy()))
        for k,vv in r['arrays'].items():arrays[f'round{t}_{k}']=vv
        timing=dict(round=t,status='ok',seconds=r['seconds'],refit_seconds=r['refit_seconds'],detector_seconds=r['detector_seconds'],decoder_seconds=r['decoder_seconds'],instrumentation_seconds=r['instrumentation_seconds']);round_timings.append(timing)
        events.append(dict(**timing,events=r['events']))
        a=r['arrays'];s['prior']=np.clip(a['final_check'],-20,20);s['channel_llr']=a['final_input'];s['mu'],s['v'],_=moments(np.clip(a['final_app'],-20,20),.5);s['x_soft']=s['mu'].copy()
        if 'sbl_full_dopplers' in a:
            s['delays']=np.repeat(np.arange(system.l_max_cap+1),5) if cc.get('dictionary','full')=='full' else s['delays']
            s['dopplers']=a['sbl_full_dopplers'];s['gains']=a['sbl_full_gains'];s['sbl_delta']=a['sbl_delta'];cc['dictionary']='active'
        else:s['delays']=a['path_delays'];s['dopplers']=a['path_dopplers'];s['gains']=a['path_gains']
    s['native_initial_state']=initial_state
    r=last_result
    completed=[x for x in round_timings if x['status']=='ok']
    r.update(seconds_complete=time.perf_counter()-start,front_seconds=front_seconds,arrays=arrays,events=events,decision_timeline=snapshots,decoder_records=decoder_records,round_timings=round_timings,refit_seconds=sum(x['refit_seconds'] for x in completed),detector_seconds=sum(x['detector_seconds'] for x in completed),decoder_seconds=sum(x['decoder_seconds'] for x in completed),instrumentation_seconds=sum(x['instrumentation_seconds'] for x in completed),failed_round_seconds=sum(x['seconds'] for x in round_timings if x['status']!='ok'),stage_timing_scope='stage totals include completed native rounds; failed round work is charged separately and not split by stage')
    return r,s
