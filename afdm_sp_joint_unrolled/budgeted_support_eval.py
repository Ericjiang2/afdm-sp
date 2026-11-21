"""S2 paired coded diagnostics on the existing F2-P receiver; no new detector.

All oracle arms are offline interventions. These development frames are never
independent confirmatory evidence. Parallel jobs may use distinct replicates.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
import torch

from afdm_sp_joint_unrolled import e1_ldpc_coded_eval as e1
from afdm_sp_joint_unrolled import afdm_baselines as afb
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a, _oracle_dictionary_support, _fast_bp as final_bp
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled, resolve_receiver_capacity,
    construct_sensing_matrix_torch, omp_sparse_torch,
)
from afdm_sp_joint_unrolled.decision_gateA import make_genie_lambda
from afdm_sp_joint_unrolled.decision_bound import build_fine_prior
from afdm_sp_joint_unrolled.decision_harvest import validate_complete_prior
from afdm_sp_joint_unrolled.budgeted_frame_store import FrameStore
from afdm_sp_joint_unrolled.budgeted_job_queue import write_status
from afdm_sp_joint_unrolled.e1_ldpc import build_code, encode, qpsk_map, demap_llr, decode_llr, extract_info
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import (
    array_hash, dev_rng, keep_omp_support, perfect_gain_hook, fit_physical_cluster, feedback_statistics,
)


ARMS = ('baseline', 'keep', 'unprotected', 'oracle_gains', 'oracle_data', 'wide_pool')
POSITION_ARMS = ('position_true', 'position_rounded', 'position_local')
EXTRA_ARMS = ('conservative', 'temperature_mean', 'jsoft', 'covariance', 'a0')
MECHANISM_ARMS = {
    'r00': ('legacy_stats_prior', False, None),
    'r01': ('legacy_stats_prior', True, None),
    'r10': ('projected_stats_prior', False, None),
    'r11': ('projected_stats_prior', True, None),
    'r11_protect0': ('projected_stats_prior', True, 0),
    'ols_no_prior': ('ols_no_prior', True, None),
}
FEEDBACK_ARMS = {'f_mean':'mean', 'f_uniform':'covariance_uniform',
                 'f_dynamic':'covariance', 'o_data':'mean'}


def transaction_audit(value):
    """JSON evidence retains small state tensors and hashes large BP inputs."""
    if isinstance(value, torch.Tensor):
        array = value.detach().cpu().numpy()
        record = dict(dtype=str(array.dtype), shape=list(array.shape), sha256=array_hash(array))
        if array.size <= 128:
            if np.iscomplexobj(array):
                record.update(real=array.real.tolist(), imag=array.imag.tolist())
            else:
                record['values'] = array.tolist()
        return record
    if isinstance(value, dict):
        return {k: transaction_audit(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [transaction_audit(v) for v in value]
    return value


def load_prior(path, snr, N, *, l_max, k_max, nomination_cap=None, receiver_shell='legacy'):
    cache = torch.load(path, map_location='cpu', weights_only=False)
    expected = dict(N=N, v_mean=2, p_paths=8, tau_ms=10, fs_factor=4, rho=.5,
                    sigma2=10**(-snr/10), l_max=l_max, k_max=k_max,nomination_cap=nomination_cap)
    if (cache['n'] != 400 or cache['snr'] != snr or cache['M'] != 96
            or any(cache['config'].get(k) != v for k,v in expected.items())
            or len(cache['seed']) != 400 or len(set(cache['seed'].tolist())) != 400):
        raise ValueError('calibration cache violates the frozen frame/configuration contract')
    for key in ('dl_nn','dk_nn','g_nn','y','genie_gain_sq'):
        if cache[key].shape != (400,96) or not torch.isfinite(cache[key]).all():
            raise ValueError(f'invalid calibration tensor: {key}')
    if receiver_shell == 'direct40':
        if nomination_cap != 40:
            raise ValueError('direct40 prior nomination must be40')
        validate_complete_prior(cache, 400)
    elif receiver_shell != 'legacy':
        raise ValueError('unknown receiver shell')
    values = [cache[k].numpy().reshape(-1) for k in ('dl_nn','dk_nn','g_nn','y','genie_gain_sq')]
    lookup, metadata = build_fine_prior(*values, np.quantile(values[2], [1/3,2/3]), min_count=30)
    return lookup, dict(metadata, seeds=cache['seed'].tolist(), config=cache['config'])


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_receiver(checkpoint, system, N, device, *, receiver_shell='legacy', active_cap=None):
    ckpt = torch.load(checkpoint, map_location='cpu', weights_only=False)
    head = ckpt.get('head_config') or {}
    cfg = ClassicalJointConfig(
        N=N, l_max=system.l_max_cap, k_max=system.k_max_cap, c1=system.c1, c2=system.c2,
        rho=float(system.rho), mp_mode='bp', pic_damp=.5, n_paths=8,
        n_outer_iter=10, pic_iter=20, update_sigma2=True, early_stop=False, eps_stop_rel=-1,
        dtype=torch.complex64, rdtype=torch.float32, device=device,
        cand_pair_hidden=int(head.get('pair_hidden',16)), cand_scorer_hidden=int(head.get('scorer_hidden',16)),
    )
    nomination, _ = resolve_receiver_capacity(receiver_shell,active_cap,cfg.k_leak,cfg.k_max)
    if nomination is not None:
        cfg.n_paths = nomination
    model = ClassicalJointUnrolled(cfg, learnable_heads=e1.VARIANT_HEADS['C2-rel'], use_soft_decisions=True)
    model.load_state_dict(ckpt.get('state_dict') or ckpt.get('module') or ckpt)
    return model.to(device).eval()


def make_frame(system, code, replicate, index, snr, uncoded=False, *, split=1, rng_factory=None):
    N = system.N_total
    rng_factory = dev_rng if rng_factory is None else rng_factory
    channel_seed = int(rng_factory(replicate,index,1,split=split).integers(0,2**31))
    np.random.seed(channel_seed)
    H, _, params = system.generate_channel_matrix()
    info = rng_factory(replicate,index,2,split=split).integers(0,2,size=code['n'] if uncoded else code['k']).astype(np.uint8)
    coded = info.copy() if uncoded else encode(code, info)
    data = np.sqrt(1-system.rho)*qpsk_map(coded, scale=1)
    pilot = np.sqrt(system.rho)*system._zc_seq
    rng = rng_factory(replicate,index,3,split=split)
    noise = (rng.standard_normal(N)+1j*rng.standard_normal(N))/np.sqrt(2)
    sigma2 = 10**(-snr/10)
    y = H@(pilot+data)+np.sqrt(sigma2)*noise
    return dict(y=y, H=H, params=params, info=info, coded=coded, data=data, pilot=pilot,
                noise=noise, sigma2=sigma2, channel_seed=channel_seed,uncoded=uncoded,split_id=split)


def run_frame(model, system, code, frame, lookup, arms, replicate, index, snr, observe=True,
              single_actions=None, soft_observe=False, feedback_temperature=1.,active_cap=None,
              receiver_shell='legacy', prior_reference_id=None, include_common_keep=False,
              dals_snapshot_path=None, representation_observe=False, initial_estimator=None,
              terminal_observer=None, graph_observe=False, dals_state_observer=None):
    cfg, head = model.cfg, model.cand_active_rel
    if initial_estimator is not None and list(arms) != ['a0']:
        raise ValueError('achievable initial estimator uses the unmodified downstream A0 arm')
    if dals_state_observer is not None and list(arms) != ['a0']:
        raise ValueError('B0 state observer requires the A0 arm')
    if representation_observe and (not observe or active_cap!=40 or receiver_shell!='direct40' or any(a not in ('a0','baseline') for a in arms)):
        raise ValueError('representation observer requires observed A0/A2 arms')
    y, pilot, Htrue = frame['y'], frame['pilot'], frame['H']
    sparsity = int(frame['params']['P_actual'])
    nomination, extension = resolve_receiver_capacity(receiver_shell,active_cap,cfg.k_leak,cfg.k_max)
    nomination = sparsity if nomination is None else nomination
    cfg.n_paths = nomination
    has_mechanism = any(arm in MECHANISM_ARMS for arm in arms)
    has_feedback = any(arm in FEEDBACK_ARMS for arm in arms)
    if has_feedback and (receiver_shell!='direct40' or active_cap!=40 or soft_observe or
                         any(a not in FEEDBACK_ARMS for a in arms) or single_actions is not None):
        raise ValueError('feedback package requires registered direct40 arms only')
    if has_mechanism and (receiver_shell != 'direct40' or active_cap != 40 or
                          prior_reference_id is None or single_actions is not None or
                          len(arms) > 8 or any(a not in (*MECHANISM_ARMS, 'a0', 'baseline') for a in arms)):
        raise ValueError('mechanism package requires direct40, frozen prior identity and at most eight registered arms')
    if include_common_keep and not has_mechanism:
        raise ValueError('common GLS keep requires a registered mechanism package')
    if len(set(arms)) != len(arms):
        raise ValueError('duplicate receiver arms')
    const = np.sqrt(1-cfg.rho)*e1.QPSK
    Phi = afb.construct_sensing_matrix(cfg.N,pilot,cfg.c1,cfg.c2,cfg.l_max,cfg.k_max)
    # The actual achievable factory receives Hhat0, never the simulation H.
    scorer, prep_seconds = None, 0.
    if any(arm != 'a0' for arm in arms):
        prep_started = time.perf_counter()
        _, support0 = afb.omp_sparse(y, Phi, nomination)
        support0 = np.asarray(support0, dtype=int)
        g0 = np.linalg.lstsq(Phi[:,support0],y,rcond=None)[0]
        H0 = system.gen_h_daft(g0,support0//(2*cfg.k_max+1),support0%(2*cfg.k_max+1)-cfg.k_max)
        scorer = make_genie_lambda(H0,cfg.rho,lookup,cfg.k_max,2*cfg.k_max+1)
        prep_seconds = time.perf_counter()-prep_started
    yt = torch.tensor(y,dtype=cfg.dtype,device=cfg.device)
    pt = torch.tensor(pilot,dtype=cfg.dtype,device=cfg.device)
    nt = torch.tensor(frame['sigma2'],dtype=cfg.rdtype,device=cfg.device)
    ct = torch.tensor(const,dtype=cfg.dtype,device=cfg.device)
    mechanism_reference, mechanism_prep_seconds = None, 0.
    if has_mechanism:
        from afdm_sp_joint_unrolled.mechanism_control import prepare_mechanism_reference
        prep_started = time.perf_counter()
        Phi_common = construct_sensing_matrix_torch(cfg.N, pt, cfg.c1, cfg.c2,
                                                     cfg.l_max, cfg.k_max, cdtype=cfg.dtype)
        _, common_support = omp_sparse_torch(yt, Phi_common, nomination)
        C_common = torch.as_tensor((1-cfg.rho)*(H0@H0.conj().T)+frame['sigma2']*np.eye(cfg.N),
                                   dtype=cfg.dtype, device=cfg.device)
        mechanism_reference = prepare_mechanism_reference(Phi_common, yt, common_support, nt, C_common,
            head=head, lookup=lookup, l_max=cfg.l_max, k_max=cfg.k_max,
            nomination_cap=nomination, prior_reference=prior_reference_id)
        if cfg.device == 'cuda':
            torch.cuda.synchronize()
        mechanism_prep_seconds = time.perf_counter()-prep_started
    truth_cols = _oracle_dictionary_support(frame['params'],cfg.k_max,2*cfg.k_max+1,Phi.shape[1])
    order = list(arms) + (['mechanism_keep'] if include_common_keep else [])
    order_rng = (np.random.default_rng(frame['order_seed_words']) if 'order_seed_words' in frame
                 else dev_rng(replicate,index,4,split=frame.get('split_id',1)))
    order_rng.shuffle(order)
    results = {}
    for arm in order:
        support_log, score_log = {}, []
        graph_log, proposal_log = [], []
        soft_log = []
        transaction_log = []
        dals_states, reliability_log, dals_consumers = [], [], []
        dals_observer_seconds = 0.
        first_round = {}
        position_metadata = None
        intervention_prep_seconds = 0.
        local_action = single_actions is not None and arm in single_actions
        protect = 2 if active_cap is None else min(2,nomination)
        if arm != 'a0':
            head.set_refine_config(1 if local_action else 2,192 if arm=='wide_pool' else 96,
                                   True,0 if arm=='unprotected' else protect)
        def observed_scorer(Phi_t,y_t,S,candidates,sigma2):
            logits = scorer(Phi_t,y_t,S,candidates,sigma2)
            if arm=='conservative' and not first_round:
                first_round.update(support=list(S),candidates=candidates.detach().clone(),logits=logits.detach().clone())
            if observe:
                score_log.append(dict(support=list(S),candidate_ids=candidates.tolist(),scores=logits.tolist()))
            if local_action:
                selected = single_actions[arm]
                forced = torch.full_like(logits,-1.)
                if selected is not None:
                    match = candidates == selected
                    if int(match.sum()) != 1:
                        raise ValueError('local action candidate absent from the frozen first-round pool')
                    forced[match] = 1.
                return forced
            return logits
        if arm != 'a0':
            head._gateA_scorer = observed_scorer if observe or local_action or arm=='conservative' else scorer
            head._gateA_tau = 0. if local_action else -1e9
        def observe_support(raw, final, delays, dopplers):
            support_log.update(raw=list(raw),final_nomination=list(final),
                               expanded=list(zip(delays.tolist(),dopplers.tolist())))
        kwargs = {'diagnostic_support_observer':observe_support} if observe else {}
        kwargs['enable_support_repair'] = arm != 'a0'
        if initial_estimator is not None:
            kwargs['initial_estimator'] = initial_estimator
        if dals_state_observer is not None:
            kwargs['diagnostic_dals_observer'] = dals_state_observer
        if representation_observe:
            kwargs['diagnostic_proposal_observer'] = proposal_log.append
        if representation_observe or graph_observe:
            kwargs['diagnostic_graph_observer'] = graph_log.append
        if active_cap is not None:
            kwargs['active_support_cap'] = active_cap
        if receiver_shell == 'direct40':
            kwargs['receiver_extension'] = extension
        if arm in MECHANISM_ARMS or arm == 'mechanism_keep':
            from afdm_sp_joint_unrolled.mechanism_control import make_mechanism_transaction
            mode, gate, protected = MECHANISM_ARMS.get(arm, ('projected_stats_prior', True, 0))
            kwargs['support_transaction'] = make_mechanism_transaction(mechanism_reference,
                head=head, mode=mode, gate_enabled=gate, protect_added=protected,
                diagnostic_keep=arm == 'mechanism_keep')
            if observe:
                kwargs['transaction_observer'] = lambda event: transaction_log.append(transaction_audit(event))
        if arm in ('temperature_mean','jsoft','covariance'):
            kwargs['dals_temperature'] = feedback_temperature
            kwargs['dals_mode'] = arm if arm in ('jsoft','covariance') else 'mean'
        if arm in FEEDBACK_ARMS:
            kwargs.update(dals_temperature=1.,dals_mode=FEEDBACK_ARMS[arm])
            if observe:
                from afdm_sp_joint_unrolled.feedback_diagnostics import reliability_statistics
                def record_reliability(payload):
                    values=reliability_statistics(payload['probabilities'].cpu().numpy(),
                        payload['constellation'].cpu().numpy(),frame['data'],1-cfg.rho,
                        logits=payload['logits'].cpu().numpy())
                    reliability_log.append(dict(stage=payload['stage'],outer_iter=payload['outer_iter'],**values))
                kwargs['diagnostic_soft_observer']=record_reliability
                def save_dals_state(state):
                    nonlocal dals_observer_seconds
                    before=time.perf_counter()
                    dals_consumers.append(transaction_audit(state))
                    if arm=='f_mean':
                        dals_states.append({k:v.detach().cpu().clone() if isinstance(v,torch.Tensor) else v
                                            for k,v in state.items()})
                    dals_observer_seconds+=time.perf_counter()-before
                kwargs['diagnostic_dals_observer']=save_dals_state
        if soft_observe:
            kwargs['diagnostic_soft_observer'] = lambda payload: soft_log.append(feedback_statistics(payload,frame['data']))
        if arm == 'keep':
            kwargs['diagnostic_support_override'] = keep_omp_support
        elif arm == 'conservative':
            def conservative(Phi_t,y_t,raw,repaired,h,noise):
                if raw!=first_round['support']:
                    raise ValueError('conservative replay changed the initial OMP state')
                return head.apply_sequential_add_test(
                    Phi_t,y_t,raw,first_round['logits'],first_round['candidates'],
                    residual_reduction_threshold=.01,k_add_cap=head.k_add_max,gain_margin=0.)
            kwargs['diagnostic_support_override'] = conservative
        elif arm == 'oracle_gains':
            kwargs['diagnostic_channel_override'] = perfect_gain_hook(torch.as_tensor(Htrue),cfg)
        elif arm in ('oracle_data','o_data'):
            true_data = torch.tensor(frame['data'],dtype=cfg.dtype,device=cfg.device)
            kwargs['diagnostic_data_override'] = lambda current,t: true_data
        elif arm in POSITION_ARMS:
            prep_start = time.perf_counter()
            if arm=='position_local':
                from afdm_sp_joint_unrolled.budgeted_support_diagnostics import fit_local_physical_cluster
                fixed_H,position_metadata=fit_local_physical_cluster(system,frame['params']['l_i'],
                    np.round(frame['params']['k_real']),Phi,y)
            else:
                fixed_H,position_metadata = fit_physical_cluster(
                    system,frame['params'],Phi,y,rounded=arm=='position_rounded')
                position_metadata['fit_count']=1
            fixed_H_t = torch.tensor(fixed_H,dtype=cfg.dtype,device=cfg.device)
            position_metadata['injected_H_sha256']=array_hash(fixed_H_t.cpu().numpy())
            position_metadata['override_outer_calls']=[]
            def fixed_position_channel(current,dl,dk,t):
                position_metadata['override_outer_calls'].append(t)
                return fixed_H_t
            kwargs['diagnostic_channel_override'] = fixed_position_channel
            intervention_prep_seconds = time.perf_counter()-prep_start
        if cfg.device == 'cuda':
            torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.no_grad():
            output = model(yt,pt,nt,ct,**kwargs)
        Hhat = output['H_est'].cpu().numpy()
        xhat = output['x_soft'].cpu().numpy()
        sigma_final = float(output['sigma2_final'].cpu())
        if terminal_observer is not None:
            terminal_observer(dict(arm=arm,H=Hhat.copy(),sigma2=sigma_final,
                                   y=y.copy(),pilot=pilot.copy(),constellation=const.copy()))
        _,mu,var = final_bp(y-Hhat@pilot,Hhat,sigma_final,const,
                                   n_iter=20,threshold=1e-4,damp=.5,return_soft=True,
                                   **({'graph_observer':lambda r:graph_log.append(dict(stage='final_bp',outer_iter=None,**r))}
                                      if representation_observe or graph_observe else {}))
        llr = demap_llr(mu,var,np.sqrt((1-cfg.rho)/2))
        if frame.get('uncoded',False):
            ok,e_info = None,None
        else:
            decoded,ok = decode_llr(code,llr,maxiter=50)
            e_info = int((extract_info(code,decoded)!=frame['info']).sum())
        if cfg.device == 'cuda':
            torch.cuda.synchronize()
        elapsed = time.perf_counter()-started
        if not all(np.isfinite(v).all() for v in [Hhat,xhat,mu,var,llr]):
            raise FloatingPointError(f'nonfinite receiver result in {arm}')
        raw = e1._bits_of_symbol(xhat/np.sqrt(1-cfg.rho),cfg.N)
        results[arm] = dict(
            raw_errors=int((raw!=frame['coded']).sum()),
            info_errors=e_info,
            decode_ok=bool(ok) if ok is not None else None, nmse=float(np.linalg.norm(Hhat-Htrue)**2/np.linalg.norm(Htrue)**2),
            sigma2_final=sigma_final,
            receiver_seconds=elapsed, shared_scorer_preparation_seconds=0. if arm=='a0' else prep_seconds,
            intervention_preparation_seconds=intervention_prep_seconds,
            standalone_seconds_estimate=elapsed+(0. if arm=='a0' else prep_seconds)+intervention_prep_seconds,
            cost_interpretation=('A0 bypasses repair and scorer preparation; instrumentation still included'
                                 if arm=='a0' else 'diagnostic replay including instrumentation; keep executes then discards repair'),
            support_repair_enabled=arm!='a0',
            capacity_trace=output.get('capacity_trace',[]),
            representation=(dict(graphs=graph_log,proposal_events=proposal_log,
                repair_status='disabled' if arm=='a0' else 'enabled',
                stage_loss_scope='historical overlapping associations; no causal decomposition') if representation_observe else None),
            support=support_log, rounds=score_log, oracle=arm.startswith('oracle_') or arm in POSITION_ARMS or arm=='o_data',
            position_reference=position_metadata,
            single_candidate_action=single_actions[arm] if local_action else None,
            action_family='one-round single-add, existing protected prune and refit' if local_action else None,
            conservative_config=(dict(scorer='achievable initial pool',relative_residual_reduction=.01,
                                       add_cap=head.k_add_max,gain_margin=0.,keeps_original_support=True,
                                       discarded_f2p_trace=True) if arm=='conservative' else None),
            dals_temperature=feedback_temperature if arm in ('temperature_mean','jsoft','covariance') else 1.,
            dals_mode=arm if arm in ('jsoft','covariance') else 'mean',
            soft_feedback=soft_log,
            final_bit_nll=float(np.logaddexp(0,-(1-2*frame['coded'].astype(float))*llr).mean()),
            final_bit_brier=float(np.mean((1/(1+np.exp(llr))-frame['coded'])**2)),
            output_h_sha256=array_hash(Hhat), output_x_sha256=array_hash(xhat),
            finite=True,
        )
        if graph_observe:
            results[arm]['bp_graphs']=graph_log
        if arm in MECHANISM_ARMS or arm == 'mechanism_keep':
            results[arm].update(support_transaction=transaction_audit(output['support_transaction']),
                transaction_consumer=transaction_log,
                shared_mechanism_preparation_seconds=mechanism_prep_seconds,
                final_bp_input_h_sha256=array_hash(Hhat), final_bp_mu_sha256=array_hash(mu),
                final_bp_var_sha256=array_hash(var), final_llr_sha256=array_hash(llr),
                recipe_scope='common final GLS, frozen pools/prior; R00 is not historical A2')
            results[arm]['standalone_seconds_estimate'] += mechanism_prep_seconds
        if arm in FEEDBACK_ARMS:
            results[arm].update(dals_mode=FEEDBACK_ARMS[arm],dals_temperature=1.,
                dals_consumers=dals_consumers,
                reliability=reliability_log,dals_observer_transfer_seconds=dals_observer_seconds,
                final_bp_mu_sha256=array_hash(mu),final_bp_var_sha256=array_hash(var),
                final_llr_sha256=array_hash(llr),decoded_bits_sha256=array_hash(decoded) if not frame.get('uncoded',False) else None,
                feedback_scope='current H each outer; variance policy only; oracle only DA-LS mean; LDPC terminal')
            if dals_states:
                from afdm_sp_joint_unrolled.feedback_diagnostics import compare_frozen_state
                if [s['outer_iter'] for s in dals_states]!=list(range(1,cfg.n_outer_iter)):
                    raise ValueError('missing DA-LS snapshot boundary')
                if dals_snapshot_path is not None:
                    io_started=time.perf_counter()
                    snapshot=Path(dals_snapshot_path)
                    snapshot.parent.mkdir(parents=True,exist_ok=True)
                    with snapshot.open('xb') as stream:
                        torch.save(dict(states=dals_states,frame_input_hashes={k:array_hash(frame[k]) for k in ('y','H','noise','info','coded','pilot')}),stream)
                    results[arm]['dals_snapshot']=dict(path=str(snapshot),sha256=file_hash(snapshot))
                    results[arm]['dals_snapshot_io_seconds']=time.perf_counter()-io_started
                comparisons=[compare_frozen_state(s,channel_reference=Htrue,
                    channel_config=dict(N=cfg.N,c1=cfg.c1,c2=cfg.c2,k_max=cfg.k_max)) for s in dals_states]
                results[arm]['frozen_state_comparisons']=transaction_audit(comparisons)
                results[arm]['offline_matrix_seconds']=sum(c['offline_seconds'] for c in comparisons)
        if representation_observe:
            from afdm_sp_joint_unrolled.representation_ledger import representation_error
            final_ids=(output['support_delays']*(2*cfg.k_max+1)+output['support_dopplers']+cfg.k_max).cpu().tolist()
            rep=results[arm]['representation']
            rep['error']=representation_error(system,frame['params'],Htrue,final_ids,cfg.k_max,H_actual=Hhat,dense_reference=True)
            rep['graph_observer_seconds']=sum(g['graph_observer_seconds'] for g in graph_log)
        if arm in ('a0','baseline'):
            results[arm].update(final_bp_mu_sha256=array_hash(mu),final_bp_var_sha256=array_hash(var),
                final_llr_sha256=array_hash(llr),decoded_bits_sha256=array_hash(decoded) if not frame.get('uncoded',False) else None)
    record = dict(
        split=frame.get('dataset','D_cal' if frame.get('split_id',1)==2 else 'D_dev'),replicate=replicate,frame_index=index,snr=snr,channel_seed=frame['channel_seed'],
        coding='iid_QPSK_uncoded' if frame.get('uncoded',False) else 'LDPC',
        bits_per_frame=len(frame['coded']),
        input_hashes={key:array_hash(frame[key]) for key in ['y','H','noise','info','coded','pilot']},
        physical_paths=int(frame['params']['taps']),expanded_entries=sparsity,
        channel_parameters={
            key: ({'real':np.asarray(frame['params'][key]).real.tolist(),
                   'imag':np.asarray(frame['params'][key]).imag.tolist()}
                  if np.iscomplexobj(frame['params'][key]) else np.asarray(frame['params'][key]).tolist())
            for key in ['l_i','k_real','g_i','l_exp','k_exp','chan_coef_exp','fro_scale','k_leak']
        },
        cross_snr_cluster=[replicate,index],
        truth_unique_columns=[int(v) for v in truth_cols],
        capacity_source='simulator_expanded_tap_count; diagnostic legacy anchor only' if active_cap is None else 'registered_fixed_capacity',
        nomination_cap=nomination,active_cap=active_cap,
        receiver_shell=receiver_shell,receiver_extension=extension,
        arm_order=order,arms=results,
    )
    if representation_observe:
        from afdm_sp_joint_unrolled.representation_ledger import merged_truth_ledger, stage_losses
        record['representation_truth'] = merged_truth_ledger(frame['params'],cfg.k_max)
        for name, result in results.items():
            final_entries=[e for e in result['capacity_trace'] if e['stage']=='final']
            if len(final_entries)!=1:
                raise ValueError('representation requires one actual final capacity event')
            final_ids=final_entries[0]['atom_ids']
            rep=result['representation']
            rep['stage_losses']=(stage_losses(truth_cols,rep['proposal_events'],final_ids,raw_ids=result['support']['raw'])
                                 if name!='a0' else {'reason':'repair_disabled; candidate attribution not applicable'})
    if mechanism_reference is not None:
        record['mechanism_reference'] = transaction_audit({k: v for k, v in mechanism_reference.items() if k != 'covariance'})
        record['mechanism_reference']['covariance_source'] = 'observed host OMP H0 and frozen initial sigma2'
    return record


def run_local_actions(model,system,code,frame,prior,replicate,index,snr):
    record = run_frame(model,system,code,frame,prior,['baseline'],replicate,index,snr)
    first = record['arms']['baseline']['rounds'][0]
    candidates = first['candidate_ids']
    actions = {'local_keep':None, **{f'candidate_{c}':c for c in candidates}}
    local = run_frame(model,system,code,frame,prior,list(actions),replicate,index,snr,
                      single_actions=actions)
    for name,result in local['arms'].items():
        if (len(result['rounds']) != 1
                or result['rounds'][0]['candidate_ids'] != candidates
                or result['rounds'][0]['support'] != first['support']):
            raise ValueError(f'local action {name} differs from the frozen starting state/pool')
    adds = model.cand_active_rel.select_additions(
        torch.tensor(first['scores'],dtype=torch.float32,device=model.cfg.device),
        torch.tensor(candidates,dtype=torch.long,device=model.cfg.device),tau=-1e9)
    chosen = f'candidate_{int(adds[0])}'
    best = min(actions,key=lambda a:(local['arms'][a]['info_errors'],local['arms'][a]['raw_errors'],
                                    -1 if actions[a] is None else actions[a]))
    record['local_actions'] = local['arms']
    record['local_reference'] = dict(candidate_ids=candidates,starting_support=first['support'],
                                      scorer_choice=chosen,empirical_best=best,
                                      oracle_scope='this one-round finite action family only')
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ckpt',required=True,type=Path)
    ap.add_argument('--calibration',type=Path,help='required for every arm except A0-only')
    ap.add_argument('--snr',required=True,type=int)
    ap.add_argument('--replicate',type=int,default=0)
    ap.add_argument('--frames',type=int,default=64)
    ap.add_argument('--start-frame',type=int,default=0)
    ap.add_argument('--n-total',type=int,default=1024)
    ap.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    ap.add_argument('--arms',nargs='+',choices=ARMS+POSITION_ARMS+EXTRA_ARMS+tuple(MECHANISM_ARMS)+tuple(FEEDBACK_ARMS),default=list(ARMS))
    ap.add_argument('--include-common-keep', action='store_true',
                    help='one additional common GLS keep diagnostic per mechanism frame')
    ap.add_argument('--representation-observe',action='store_true')
    ap.add_argument('--no-observe',action='store_true')
    ap.add_argument('--soft-observe',action='store_true',help='score existing outer feedback; no receiver change')
    ap.add_argument('--split',choices=['dev','cal'],default='dev')
    ap.add_argument('--feedback-calibration',type=Path,help='frozen D_cal temperature selection JSON')
    ap.add_argument('--active-cap',type=int,choices=[8,16,24,32,40],default=None)
    ap.add_argument('--receiver-shell',choices=['legacy','direct40'],default='legacy')
    ap.add_argument('--uncoded',action='store_true',help='IID QPSK bits; skip LDPC and report no coded FER')
    ap.add_argument('--local-actions',action='store_true',help='I3: baseline plus every single-candidate action')
    ap.add_argument('--resume',action='store_true')
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    if any(a in MECHANISM_ARMS for a in args.arms) and (
            args.receiver_shell != 'direct40' or args.active_cap != 40 or args.local_actions or
            len(args.arms) > 8 or any(a not in (*MECHANISM_ARMS, 'a0', 'baseline') for a in args.arms)):
        raise ValueError('invalid registered direct40 mechanism package')
    if args.include_common_keep and not any(a in MECHANISM_ARMS for a in args.arms):
        raise ValueError('common GLS keep requires a registered mechanism package')
    if len(set(args.arms)) != len(args.arms):
        raise ValueError('duplicate receiver arms')
    temperature = 1.
    if set(args.arms)&{'temperature_mean','jsoft','covariance'}:
        if args.feedback_calibration is None:
            raise ValueError('temperature arm requires a frozen calibration record')
        calibration = json.loads(args.feedback_calibration.read_text())
        if calibration['split'] != 'D_cal' or calibration['snr'] != args.snr:
            raise ValueError('feedback calibration domain mismatch')
        temperature = calibration['selected_temperature']
        if not isinstance(temperature,(float,int)) or not np.isfinite(temperature) or temperature<=0:
            raise ValueError('invalid calibrated temperature')
    if args.local_actions:
        if args.active_cap is not None:
            raise ValueError('local-action replay is not registered for fixed capacity')
        if args.uncoded:
            raise ValueError('local-action FER ordering requires the registered coded experiment')
        if args.no_observe:
            raise ValueError('local action validation requires the support observer')
        args.arms = ['baseline']
    needs_prior = any(arm != 'a0' for arm in args.arms)
    if needs_prior and args.calibration is None:
        raise ValueError('selected receiver arms require a calibration prior')
    if args.receiver_shell == 'direct40' and args.active_cap != 40:
        raise ValueError('direct40 requires --active-cap40')
    if args.device=='cuda' and not torch.cuda.is_available():
        raise RuntimeError('S2 requested CUDA but CUDA is unavailable')
    if min(args.replicate,args.start_frame)<0 or args.frames<=0 or len(set(args.arms))!=len(args.arms):
        raise ValueError('invalid frame identifiers/count or duplicate arms')
    if args.device=='cpu' and torch.cuda.is_available():
        raise RuntimeError("CPU diagnostics require CUDA_VISIBLE_DEVICES='' because the legacy BP shim auto-selects CUDA")
    if args.resume and args.local_actions:
        raise ValueError('local-action recovery requires registered individual actions')
    if args.resume and not args.out.is_dir():
        raise ValueError('receiver resume output missing')
    args.out.mkdir(parents=True,exist_ok=args.resume)
    run_lock = (args.out/'receiver.lock').open('a')
    fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.resume and (args.out/'status.json').exists():
        (args.out/f'status-before-{time.time_ns()}.json').write_bytes((args.out/'status.json').read_bytes())
    status = dict(config={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
                  pid=os.getpid(),device=args.device,torch=torch.__version__,complete=False,
                  started_at=time.time(),completed_frames=0,computed_frames=0,restored_frames=0,scope='exploratory diagnostics, not method improvement',
                  checkpoint_sha256=file_hash(args.ckpt),calibration_sha256=file_hash(args.calibration) if args.calibration else None,
                  feedback_calibration_sha256=file_hash(args.feedback_calibration) if args.feedback_calibration else None,
                  cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
                  omp_threads=os.environ.get('OMP_NUM_THREADS'),blas_threads=os.environ.get('OPENBLAS_NUM_THREADS'),
                  timing_scope='device-ready receiver plus final BP/LDPC; observer overhead included; shared preparation separate')
    status_path = args.out/'status.json'
    write_status(status_path,status)
    try:
        system = _make_config_a(args.n_total,2,8,10,4)
        model = build_receiver(args.ckpt,system,args.n_total,args.device,
                               receiver_shell=args.receiver_shell,active_cap=args.active_cap)
        code = build_code(2*args.n_total,d_v=3,d_c=6,seed=20260726)
        status['ldpc_sha256'] = file_hash(code['cache_path'])
        status['source_sha256'] = {
            str(p.relative_to(Path(__file__).parent)):file_hash(p)
            for p in sorted(Path(__file__).parent.rglob('*.py'))
        }
        nomination, _ = resolve_receiver_capacity(args.receiver_shell,args.active_cap,model.cfg.k_leak,model.cfg.k_max)
        if needs_prior:
            prior,metadata = load_prior(args.calibration,args.snr,args.n_total,
                                        l_max=system.l_max_cap,k_max=system.k_max_cap,
                                        nomination_cap=nomination,receiver_shell=args.receiver_shell)
        else:
            prior,metadata = None,dict(seeds=[],unused_for_a0=True)
        (args.out/'calibration.json').write_text(json.dumps(metadata,indent=2))
        contract = dict(config={k:v for k,v in status['config'].items() if k not in ('out','resume')},
                        source_sha256=status['source_sha256'], checkpoint_sha256=status['checkpoint_sha256'],
                        calibration_sha256=status['calibration_sha256'],
                        feedback_calibration_sha256=status['feedback_calibration_sha256'],
                        ldpc_sha256=status['ldpc_sha256'], torch=status['torch'])
        store = FrameStore(args.out, contract, resume=args.resume)
        export = args.out/'frames.jsonl'
        if args.resume and export.exists():
            export.rename(args.out/f'frames-before-{time.time_ns()}.jsonl')
        with export.open('x') as stream:
            for i in range(args.start_frame,args.start_frame+args.frames):
                frame = make_frame(system,code,args.replicate,i,args.snr,uncoded=args.uncoded,
                                   split=2 if args.split=='cal' else 1)
                if frame['channel_seed'] in metadata['seeds']:
                    raise ValueError('development/calibration channel seed collision')
                expected = dict(frame_index=i, replicate=args.replicate, snr=args.snr,
                                split='D_cal' if args.split=='cal' else 'D_dev',
                                input_hashes={key:array_hash(frame[key]) for key in ['y','H','noise','info','coded','pilot']})
                record = store.load(i, expected) if args.resume else None
                if record is None:
                    if args.local_actions:
                        record = run_local_actions(model,system,code,frame,prior,args.replicate,i,args.snr)
                    else:
                        record = run_frame(model,system,code,frame,prior,args.arms,args.replicate,i,args.snr,
                                            not args.no_observe,soft_observe=args.soft_observe,
                                            feedback_temperature=temperature,active_cap=args.active_cap,
                                            receiver_shell=args.receiver_shell,
                                            prior_reference_id=status['calibration_sha256'],
                                            include_common_keep=args.include_common_keep,
                                            dals_snapshot_path=args.out/'dals-states'/f'frame-{i}.pt',
                                            representation_observe=args.representation_observe)
                    store.save(i, record)
                    status['computed_frames'] += 1
                else:
                    status['restored_frames'] += 1
                stream.write(json.dumps(record,allow_nan=False)+'\n')
                stream.flush()
                os.fsync(stream.fileno())
                status['completed_frames'] += 1
                write_status(status_path,status)
                metric='raw_errors' if args.uncoded else 'info_errors'
                print(f"frame {i} {metric}: "+str({k:v[metric] for k,v in record['arms'].items()}),flush=True)
        status['complete'] = True
    except Exception as exc:
        status['failure'] = dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        status['elapsed_seconds'] = time.time()-status['started_at']
        write_status(status_path,status)
        run_lock.close()


if __name__=='__main__':
    main()
