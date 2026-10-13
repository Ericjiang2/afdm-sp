"""Representation diagnostics; physical slots are not dictionary atoms."""
from collections import Counter
import numpy as np
from scipy.optimize import linear_sum_assignment

PHYSICAL_MATCH_TOLERANCE = (.5, .5)


def match_physical_slots(truth_slots, estimated_slots=None):
    truth=np.asarray(truth_slots,dtype=float)
    if truth.ndim!=2 or truth.shape[1]!=2 or not np.isfinite(truth).all():
        raise ValueError('physical truth slots need finite delay/Doppler pairs')
    collisions={pair for pair,count in Counter(map(tuple,truth)).items() if count>1}
    excluded=[i for i,pair in enumerate(map(tuple,truth)) if pair in collisions]
    if estimated_slots is None:
        return dict(recall=None,reason='receiver_has_no_physical_slot_estimator',
                    colliding_truth_slots=excluded,
                    tolerance=list(PHYSICAL_MATCH_TOLERANCE))
    estimate=np.asarray(estimated_slots,dtype=float)
    if estimate.size==0:estimate=np.empty((0,2))
    if estimate.ndim!=2 or estimate.shape[1]!=2 or not np.isfinite(estimate).all():raise ValueError('invalid physical estimates')
    valid=[i for i in range(len(truth)) if i not in excluded]
    if not valid:
        return dict(recall=None,reason='no_identifiable_truth_slots',colliding_truth_slots=excluded,matches=[])
    n,m=len(valid),len(estimate)
    distance=np.abs(truth[valid,None,:]-estimate[None,:,:])/np.asarray(PHYSICAL_MATCH_TOLERANCE)
    admissible=(distance<=1).all(-1)
    # Dummy assignment cost exceeds every legal distance, so cardinality wins
    # over geometric error. Deterministic input order is retained for ties.
    penalty=float(4*(n+m+1));cost=np.full((n+m,n+m),penalty)
    cost[:n,:m]=np.where(admissible,distance.sum(-1),penalty*4)
    cost[n:,m:]=0
    left,right=linear_sum_assignment(cost)
    matches=[(valid[int(i)],int(j)) for i,j in zip(left,right) if i<n and j<m and admissible[i,j]]
    return dict(recall=len(matches)/n,identifiable_denominator=n,matches=matches,
        colliding_truth_slots=excluded,ambiguous_truth_slots=[valid[i] for i in range(n) if admissible[i].sum()>1],
        contested_estimate_slots=np.flatnonzero(admissible.sum(0)>1).tolist(),
        tolerance=list(PHYSICAL_MATCH_TOLERANCE),scope='one-to-one physical slots only; exact collisions excluded explicitly')


def merged_truth_ledger(params,k_max,*,threshold=0.):
    from afdm_sp_joint_unrolled.loop9_cache_features import _merged_dictionary_coefficients
    if type(k_max) not in (int,np.int64,np.int32) or k_max<0:raise ValueError('invalid receiver Doppler bound')
    if int(params['taps'])!=len(params['l_i']) or len(params['l_i'])!=len(params['k_real']):raise ValueError('unaligned physical slots')
    if not np.isfinite(threshold) or threshold<0:raise ValueError('invalid truth coefficient threshold')
    delays=np.asarray(params['l_exp']);dopplers=np.asarray(params['k_exp']);g=np.asarray(params['chan_coef_exp'])
    if delays.shape!=dopplers.shape or delays.shape!=g.shape or delays.ndim!=1:
        raise ValueError('unaligned emitted coefficients')
    if (not np.isfinite(g).all() or not np.isfinite(delays).all() or not np.isfinite(dopplers).all()
            or np.any(delays!=delays.astype(int)) or np.any(dopplers!=dopplers.astype(int))):
        raise ValueError('invalid emitted integer atoms or coefficients')
    # The receiver dictionary must not silently truncate the truth ledger.
    bound=max(k_max,int(np.max(np.abs(dopplers))) if len(dopplers) else k_max)
    columns,gains=_merged_dictionary_coefficients(params,bound,2*bound+1)
    entries=[]
    for column,gain in zip(columns,gains):
        l,k=divmod(int(column),2*bound+1);k-=bound
        entries.append(dict(delay=l,doppler=k,
            column=l*(2*k_max+1)+k+k_max if abs(k)<=k_max else None,
            in_receiver_doppler_domain=abs(k)<=k_max,real=float(gain.real),imag=float(gain.imag),
            above_threshold=bool(abs(gain)>threshold)))
    return dict(P_phys=int(params['taps']),K_emit=len(g),K_unique_merged=len(entries),
        K_true=sum(e['above_threshold'] for e in entries),threshold=threshold,
        K_true_in_receiver_doppler_domain=sum(e['above_threshold'] and e['in_receiver_doppler_domain'] for e in entries),
        threshold_unit='absolute merged complex coefficient; sum before threshold',entries=entries,
        physical_matching=match_physical_slots(np.column_stack((params['l_i'],params['k_real']))),
        coefficient_energy_scope='dictionary coefficient weight, not physical path energy')


def stage_losses(truth_ids,events,final_ids,*,raw_ids=()):
    truth={int(i) for i in truth_ids}; final={int(i) for i in final_ids};raw={int(i) for i in raw_ids}
    pool=set();selected=set();pruned=set()
    for event in events:
        if event['stage']=='pool':pool.update(event['candidate_ids'])
        if event['stage']=='union':selected.update(event['selected_ids'])
        if event['stage']=='final_prune':pruned.update(event['pruned_ids'])
    return dict(initial_true=sorted(truth&raw),truth_not_in_pool=sorted(truth-raw-pool),in_pool_not_selected=sorted((truth&pool)-selected),
        initially_true_then_pruned=sorted(truth&raw&pruned),
        selected_then_pruned=sorted(truth&selected&pruned),final_missing=sorted(truth-final),
        scope='overlapping set associations; not a causal decomposition or independent physical paths')


def actual_bp_graph(H, mask, row_idx, col_idx, threshold, *, operator='>='):
    """Summarize the detector's existing mask, after its actual dtype cast."""
    import torch
    import time
    started=time.perf_counter()
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    energy = H.abs().square()
    total = float(energy.sum())
    discarded = float(energy[~mask].sum())
    rows = torch.bincount(row_idx, minlength=H.shape[0]).cpu().tolist()
    cols = torch.bincount(col_idx, minlength=H.shape[1]).cpu().tolist()
    return dict(backend='mp_detect_bp_torch', dtype=str(H.dtype), shape=list(H.shape),
        H_hash=array_hash(H.detach().cpu().numpy()), threshold=float(threshold), operator=operator,
        edges=int(row_idx.numel()), row_degrees=rows, column_degrees=cols,
        total_squared_frobenius=total, discarded_squared_frobenius=discarded,
        threshold_loss=discarded/total if total else None,
        threshold_loss_status='defined' if total else 'zero_channel_undefined',
        graph_observer_seconds=time.perf_counter()-started)


def representation_error(system, params, H_true, columns, k_max, *, H_actual=None, dense_reference=False):
    """Offline fixed-support projection; generator basis is independent of Torch reconstruction."""
    import time
    import torch
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support, array_hash
    from afdm_sp_joint_unrolled.physical_stride import physical_stride
    started=time.perf_counter()
    H=np.asarray(H_true,dtype=np.complex128)
    ids=np.asarray(columns)
    if H.ndim!=2 or H.shape[0]!=H.shape[1] or not np.isfinite(H).all():
        raise ValueError('finite square true channel required')
    if ids.ndim!=1 or np.any(ids!=ids.astype(int)) or len(set(ids.tolist()))!=len(ids) or np.any(ids<0):
        raise ValueError('unique integer support required')
    ids=ids.astype(int); delays=ids//(2*k_max+1);dopplers=ids%(2*k_max+1)-k_max
    physical_stride(H.shape[0], system.c1)
    if H.shape[0]!=system.N_total or system.gen_h_daft_convention!='python':
        raise ValueError('generator and analytic dictionary conventions disagree')
    if np.any(delays>system.l_max_cap):raise ValueError('support outside receiver delay domain')
    ledger=merged_truth_ledger(params,k_max)
    entries=ledger['entries']
    rebuilt=system.gen_h_daft(np.array([complex(e['real'],e['imag']) for e in entries]),
                             np.array([e['delay'] for e in entries]),np.array([e['doppler'] for e in entries]))
    truth_error=float(np.linalg.norm(rebuilt-H))
    denominator=float(np.linalg.norm(H)**2)
    if truth_error>1e-10*max(1.,np.linalg.norm(H)):
        raise ValueError('merged generator truth does not reproduce actual H_true')
    projected,gains=project_channel_on_support(torch.from_numpy(H),torch.from_numpy(delays),torch.from_numpy(dopplers),
                                               system.c1,system.c2,k_max)
    projected=projected.numpy()
    residual=float(np.linalg.norm(H-projected)**2)
    result=dict(support_ids=ids.tolist(),E_repr=residual/denominator if denominator else None,
        denominator=denominator,projection_residual_squared=residual,
        merged_truth_reconstruction_error=truth_error,projection_H_hash=array_hash(projected),
        ratio_status='defined' if denominator else 'zero_truth_undefined',
        interpretation='fixed dictionary support representation; gain and threshold losses are separate associations')
    if H_actual is not None:
        actual=np.asarray(H_actual)
        if actual.shape!=H.shape or not np.isfinite(actual).all():raise ValueError('invalid actual channel')
        result['actual_channel_error_squared']=float(np.linalg.norm(actual-H)**2)
        result['distance_actual_to_projection_squared']=float(np.linalg.norm(actual-projected)**2)
    if dense_reference:
        basis=np.column_stack([system.gen_h_daft(np.array([1.+0.j]),np.array([l]),np.array([k])).reshape(-1)
                               for l,k in zip(delays,dopplers)]) if len(ids) else np.empty((H.size,0),dtype=complex)
        solution,_,rank,singular=np.linalg.lstsq(basis,H.reshape(-1),rcond=1e-12)
        dense=(basis@solution).reshape(H.shape)
        delta=float(np.linalg.norm(dense-projected))
        if delta>1e-10*max(1.,np.linalg.norm(H)):
            raise ValueError('independent generator LS disagrees with analytic projection')
        result['dense_reference']=dict(rcond=1e-12,rank=int(rank),columns=len(ids),singular_values=singular.tolist(),
            basis_hash=array_hash(basis),projection_difference_norm=delta,residual_squared=float(np.linalg.norm(H-dense)**2),
            coefficient_identifiable=int(rank)==len(ids))
    result['offline_seconds']=time.perf_counter()-started
    return result
