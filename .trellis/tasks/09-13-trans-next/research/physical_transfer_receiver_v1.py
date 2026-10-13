"""Observed-only adapter for the registered two-domain transfer check."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import numpy as np
import torch

_spec = spec_from_file_location('registered_uncoded_base', Path(__file__).with_name('uncoded-g1-v1.py'))
base = module_from_spec(_spec)
_spec.loader.exec_module(base)
ARMS = ('OMP_BASE', 'OMP_HARD', 'OMP_PLUS4', 'F2P_HEAD', 'F2P_RESID')


def check(value, arm, cfg, nominal):
    if arm not in ARMS:
        raise ValueError('unregistered arm')
    k = nominal + (4 if arm == 'OMP_PLUS4' else 0)
    d = (cfg.l_max + 1) * (2 * cfg.k_max + 1)
    assert 0 < k < d and value['nomination'] == k
    assert value['H'].shape == (cfg.N, cfg.N)
    assert value['x_soft'].shape == (cfg.N,) and value['bits'].shape == (2*cfg.N,)
    np.testing.assert_array_equal(value['bits'], base.bits_of(value['x_soft']))
    pairs = list(zip(value['delays'].tolist(), value['dopplers'].tolist()))
    assert len(set(pairs)) == len(pairs) <= (2*cfg.k_leak+1)*k
    assert all(0 <= l <= cfg.l_max and abs(nu) <= cfg.k_max for l, nu in pairs)
    assert len(value['support_trace']['initial']) <= k
    assert len(value['support_trace']['final_nomination']) <= k
    counts, schedule = value['counts'], value['bp_schedule']
    assert counts['coding_calls'] == 0 and counts['initial_omp_calls'] == 1
    assert counts['repair_calls'] == int(arm.startswith('F2P_'))
    assert counts['learned_score_calls'] == (2 if arm == 'F2P_HEAD' else 0)
    assert counts['lstsq'] > 0 and schedule['outer_iterations'] == 10
    assert len(schedule['calls']) == 10 and schedule['completed_ce_solves'] == 9
    assert all(x['requested_iterations'] == 20 for x in schedule['calls'])
    for key in ('x_soft', 'H', 'sigma2_final', 'gains', 'delays', 'dopplers'):
        assert np.isfinite(value[key]).all(), key


def build(checkpoint, system):
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    counts = {'coding_calls': 0}
    with base.forbid_coding(counts):
        model = build_receiver(checkpoint, system, system.N_total, 'cpu')
    assert counts['coding_calls'] == 0
    assert model.learnable_heads == {'cand_active_rel'}
    assert model.cfg.k_leak == 2 and model.cfg.n_outer_iter == 10 and model.cfg.pic_iter == 20
    return model, {'guarded_setup_coding_calls': counts['coding_calls'],
                   'checkpoint_load': 'strict existing build_receiver', 'new_training': False}


def receive(model, obs, arm, nominal):
    from afdm_sp_joint_unrolled import classical_joint_unrolled as joint
    from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
    cfg = model.cfg
    base.validate_observed(obs, cfg.N)
    if arm not in ARMS or nominal != min(40, ((cfg.l_max+1)*(2*cfg.k_max+1))//2):
        raise ValueError('arm/public capacity does not match registered formula')
    nomination = nominal + (4 if arm == 'OMP_PLUS4' else 0)
    cfg.n_paths = nomination
    model.use_soft_decisions = arm != 'OMP_HARD'
    head = model.cand_active_rel
    head.set_refine_config(2, 96, True, 2)
    head._gateA_scorer = base.residual_score if arm == 'F2P_RESID' else None
    head._gateA_tau = -1e9
    counts = dict(lstsq=0, coding_calls=0, repair_calls=0, learned_score_calls=0, initial_omp_calls=0)
    original_refine, original_score, original_omp = head.apply_f2p_refinement, head.score, joint.omp_sparse_torch
    def refine(*args, **kwargs):
        counts['repair_calls'] += 1
        return original_refine(*args, **kwargs)
    def score(*args, **kwargs):
        counts['learned_score_calls'] += 1
        return original_score(*args, **kwargs)
    def omp(*args, **kwargs):
        counts['initial_omp_calls'] += 1
        return original_omp(*args, **kwargs)
    head.apply_f2p_refinement, head.score, joint.omp_sparse_torch = refine, score, omp
    support = {}
    def support_observer(raw, final, delays, dopplers):
        support.update(initial=list(raw), final_nomination=list(final),
                       expanded_delays=delays.detach().cpu().numpy().copy(),
                       expanded_dopplers=dopplers.detach().cpu().numpy().copy())
    try:
        with torch.no_grad(), base.cpu_lstsq(counts), base.forbid_coding(counts):
            result = model(torch.tensor(obs['y'], dtype=cfg.dtype),
                           torch.tensor(obs['pilot'], dtype=cfg.dtype),
                           torch.tensor(obs['sigma2'], dtype=cfg.rdtype),
                           torch.tensor(obs['constellation'], dtype=cfg.dtype),
                           enable_support_repair=arm.startswith('F2P_'), code_feedback=None,
                           diagnostic_support_observer=support_observer,
                           bp_schedule=UniformBPSchedule(outer_bp_iterations=20))
    finally:
        head.apply_f2p_refinement, head.score, joint.omp_sparse_torch = original_refine, original_score, original_omp
        head._gateA_scorer = None
    array = lambda key: result[key].detach().cpu().numpy().copy()
    value = dict(x_soft=array('x_soft'), H=array('H_est'), sigma2_final=array('sigma2_final'),
                 gains=array('gains'), delays=array('support_delays'), dopplers=array('support_dopplers'),
                 support_trace=support, counts=counts, bp_schedule=result['bp_schedule'],
                 nomination=nomination, cluster_extension=cfg.k_leak, soft_decisions=model.use_soft_decisions)
    value['bits'] = base.bits_of(value['x_soft'])
    check(value, arm, cfg, nominal)
    return value
