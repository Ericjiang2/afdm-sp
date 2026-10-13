"""Four classical controls and nine fixed bases through one receiver loop."""
import numpy as np
import torch
import time

import physical_transfer_receiver_v1 as registered
from afdm_sp_joint_unrolled import classical_joint_unrolled as joint
from afdm_sp_joint_unrolled.bandlimited_estimation import fit_coefficients
from afdm_sp_joint_unrolled.fixed_basis_receiver import FixedBasisRepresentation
from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule

CLASSICS=('OMP_BASE','F2P_RESID','OMP_SMALL','OMP_SMALL_RIDGE')
BASES=tuple(f'{family}_q{q}' for family in ('fourier','gce','dpss') for q in (3,5,7))
ARMS=CLASSICS+BASES


def receive(model,obs,arm):
    started=time.perf_counter()
    registered.base.validate_observed(obs,256)
    if arm not in ARMS:raise ValueError('unregistered A/B receiver arm')
    cfg=model.cfg;basis=arm in BASES
    cfg.n_paths=12 if arm.startswith('OMP_SMALL') else 40
    model.use_soft_decisions=True
    head=model.cand_active_rel
    head.set_refine_config(2,96,True,2)
    head._gateA_scorer=registered.base.residual_score if arm=='F2P_RESID' else None
    head._gateA_tau=-1e9
    counts=dict(lstsq=0,coding_calls=0,repair_calls=0,learned_score_calls=0,initial_omp_calls=0,ce_solves=0,bp_calls=0,
        dictionary_builds=0,dals_designs=0,channel_reconstructions=0)
    times=dict(initial_omp=0.,repair=0.,ce_solve=0.,dictionary=0.,dals_design=0.,channel=0.,
        bp_frontend_graph=0.,bp_after_graph=0.,bp_total=0.)
    original_refine,original_score=head.apply_f2p_refinement,head.score
    original_omp,original_ce,original_bp=joint.omp_sparse_torch,joint.soft_gain_update,joint.mp_detect_bp_torch
    operation_names=('construct_sensing_matrix_torch','build_A_for_DALS_torch','reconstruct_H_torch')
    original_operations={name:getattr(joint,name) for name in operation_names}
    moments=[];last_bp={};support={}
    def refine(*a,**kw):
        start=time.perf_counter();value=original_refine(*a,**kw)
        counts['repair_calls']+=1;times['repair']+=time.perf_counter()-start;return value
    def score(*a,**kw):counts['learned_score_calls']+=1;return original_score(*a,**kw)
    def omp(*a,**kw):
        start=time.perf_counter();value=original_omp(*a,**kw)
        counts['initial_omp_calls']+=1;times['initial_omp']+=time.perf_counter()-start;return value
    def ce(*a,**kw):
        start=time.perf_counter();value=original_ce(*a,**kw)
        counts['ce_solves']+=1;times['ce_solve']+=time.perf_counter()-start;return value
    def operation(name,count_key,time_key):
        def measured(*a,**kw):
            start=time.perf_counter();value=original_operations[name](*a,**kw)
            counts[count_key]+=1;times[time_key]+=time.perf_counter()-start;return value
        return measured
    def bp(y,h,sigma,constellation,**kwargs):
        start=time.perf_counter();graph_finished=[];observer=kwargs.get('edge_count_observer')
        def count_edges(edges):
            graph_finished.append(time.perf_counter())
            if observer is not None:observer(edges)
        kwargs['edge_count_observer']=count_edges
        value=original_bp(y,h,sigma,constellation,**kwargs);finished=time.perf_counter()
        assert len(graph_finished)==1
        times['bp_frontend_graph']+=graph_finished[0]-start
        times['bp_after_graph']+=finished-graph_finished[0];times['bp_total']+=finished-start
        counts['bp_calls']+=1
        hard,mean,variance=value
        moments.append(dict(mean=mean.detach().numpy().copy(),variance=variance.detach().numpy().copy()))
        if counts['bp_calls']==cfg.n_outer_iter:
            last_bp.update(y=y.detach().numpy().copy(),H=h.detach().numpy().copy(),sigma2=sigma.detach().numpy().copy(),
                constellation=constellation.detach().numpy().copy(),damp=kwargs['damp'].detach().numpy().copy(),
                threshold=kwargs['threshold'],iterations=kwargs['n_iter'],hard=hard.detach().numpy().copy(),
                mean=mean.detach().numpy().copy(),variance=variance.detach().numpy().copy())
        return value
    def observe(raw,final,delays,dopplers):
        support.update(initial=list(raw),final_nomination=list(final),
            expanded_delays=delays.detach().numpy().copy(),expanded_dopplers=dopplers.detach().numpy().copy())
    def initial_ridge(y,phi,nominal,sigma):
        del sigma
        h,selected=joint.omp_sparse_torch(y,phi,nominal)
        fit=fit_coefficients(phi[:,selected].detach().numpy(),y.detach().numpy(),.1)
        h.zero_();h[selected]=torch.from_numpy(fit['coefficients'])
        return h,selected
    representation=None
    if basis:
        family,q=arm.split('_q')
        representation=FixedBasisRepresentation(family=family,q=int(q),n=cfg.N,c1=cfg.c1,c2=cfg.c2,
            delay_cap=cfg.l_max,prefix_length=32,sample_rate=4000.,max_doppler=16.,coefficient_cap=60)
    head.apply_f2p_refinement,head.score=refine,score
    joint.omp_sparse_torch,joint.soft_gain_update,joint.mp_detect_bp_torch=omp,ce,bp
    for name,count_key,time_key in zip(operation_names,('dictionary_builds','dals_designs','channel_reconstructions'),
                                      ('dictionary','dals_design','channel')):
        setattr(joint,name,operation(name,count_key,time_key))
    try:
        forward_start=time.perf_counter()
        with torch.no_grad(),registered.base.cpu_lstsq(counts),registered.base.forbid_coding(counts):
            out=model(torch.tensor(obs['y'],dtype=cfg.dtype),torch.tensor(obs['pilot'],dtype=cfg.dtype),
                torch.tensor(obs['sigma2'],dtype=cfg.rdtype),torch.tensor(obs['constellation'],dtype=cfg.dtype),
                enable_support_repair=arm=='F2P_RESID',code_feedback=None,
                diagnostic_support_observer=None if basis else observe,
                initial_estimator=initial_ridge if arm=='OMP_SMALL_RIDGE' else None,
                dals_mode='zero_ridge' if arm=='OMP_SMALL_RIDGE' else 'mean',
                dals_strength=.1 if arm=='OMP_SMALL_RIDGE' else 1.,
                channel_representation=representation,bp_schedule=UniformBPSchedule(outer_bp_iterations=20))
        times['receiver_forward']=time.perf_counter()-forward_start
    finally:
        head.apply_f2p_refinement,head.score=original_refine,original_score
        joint.omp_sparse_torch,joint.soft_gain_update,joint.mp_detect_bp_torch=original_omp,original_ce,original_bp
        for name,value in original_operations.items():setattr(joint,name,value)
        head._gateA_scorer=None
    array=lambda key:out[key].detach().numpy().copy()
    value=dict(x_soft=array('x_soft'),H=array('H_est'),sigma2_final=array('sigma2_final'),gains=array('gains'),
        delays=array('support_delays'),counts=counts,bp_schedule=out['bp_schedule'],bp_moments=moments,last_bp=last_bp,
        support_trace=support,nomination=cfg.n_paths if not basis else 60//representation.geometry.q,
        soft_decisions=True,cluster_extension=None if basis else cfg.k_leak,arm=arm)
    value['bits']=registered.base.bits_of(value['x_soft'])
    if basis:value.update(basis_indices=array('support_basis_indices'),representation=out['channel_representation'])
    else:value['dopplers']=array('support_dopplers')
    check(value)
    times['total_observed_adapter']=time.perf_counter()-started
    value['times']=times
    return value


def check(value):
    arm=value['arm'];basis=arm in BASES;c=value['counts'];schedule=value['bp_schedule']
    assert value['H'].shape==(256,256) and value['bits'].shape==(512,)
    assert c['coding_calls']==0 and c['ce_solves']==9 and c['bp_calls']==10
    assert c['initial_omp_calls']==(0 if basis else 1) and c['repair_calls']==int(arm=='F2P_RESID')
    assert c['learned_score_calls']==0 and schedule['completed_ce_solves']==9 and len(schedule['calls'])==10
    assert c['dictionary_builds']==(0 if basis else 1)
    assert c['dals_designs']==(0 if basis else 9) and c['channel_reconstructions']==(0 if basis else 10)
    assert all(x['requested_iterations']==20 for x in schedule['calls'])
    assert len(value['bp_moments'])==10
    for moment in value['bp_moments']:
        assert np.isfinite(moment['mean']).all() and np.isfinite(moment['variance']).all()
        assert np.min(moment['variance'])>=0 and np.max(moment['variance'])<=.50001
    for key in ('H','x_soft','sigma2_final','gains'):
        if not np.isfinite(value[key]).all():raise FloatingPointError('nonfinite full receiver '+key)
    np.testing.assert_array_equal(value['bits'],registered.base.bits_of(value['x_soft']))
    if basis:
        r=value['representation'];p=r['public'];q=p['q']
        assert len(value['gains'])==(60//q)*q and r['selection']['geometry']['qualified']
        assert r['counts']['initial_gels']==1 and r['counts']['dals_designs']==9 and r['counts']['channel_reconstructions']==10
        np.testing.assert_array_equal(value['basis_indices'],np.tile(np.arange(q),60//q))
        np.testing.assert_allclose(r['last_channel']@r['last_symbols'],r['last_design']@r['last_coefficients'],atol=2e-5,rtol=2e-5)
    else:
        pairs=list(zip(value['delays'],value['dopplers']))
        assert len(set(pairs))==len(pairs) and len(value['support_trace']['initial'])<=value['nomination']


def replay_last_detector(value):
    p=value['last_bp']
    with torch.no_grad():
        hard,mean,variance=joint.mp_detect_bp_torch(torch.from_numpy(p['y']),torch.from_numpy(p['H']),
            torch.from_numpy(p['sigma2']),torch.from_numpy(p['constellation']),n_iter=p['iterations'],
            threshold=p['threshold'],damp=torch.from_numpy(p['damp']),return_numpy=False,return_soft=True)
    output=dict(hard=hard.numpy(),mean=mean.numpy(),variance=variance.numpy())
    for key in output:np.testing.assert_array_equal(output[key],p[key])
    return dict(outputs=output,exact_hard_symbols=True,exact_soft_moments=True,actual_bp_calls=1)
