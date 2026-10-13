"""Offline same-state comparisons and preregistered finite-symbol reliability."""
import time
import numpy as np
import torch
from afdm_sp_joint_unrolled.classical_joint_unrolled import residual_data_covariance, soft_gain_update

VARIANCE_EDGES = (0., .02, .05, .1, .2, .4, .7, 1.)


def reliability_statistics(probabilities, constellation, truth, data_power, logits=None):
    p=np.asarray(probabilities); s=np.asarray(constellation); truth=np.asarray(truth)
    if (p.ndim!=2 or s.ndim!=1 or p.shape[1]!=len(s) or truth.shape!=(len(p),)
            or len(p)==0 or not np.isfinite(data_power) or data_power<=0
            or not np.isfinite(s).all() or not np.isfinite(truth).all()
            or not np.isfinite(p).all() or np.any(p<0) or np.any(p>1)
            or not np.allclose(p.sum(1),1,atol=2e-6,rtol=0)):
        raise ValueError('invalid finite-symbol probability contract')
    distances=np.abs(truth[:,None]-s[None,:])
    target=distances.argmin(1)
    if np.any(distances[np.arange(len(p)),target]>1e-6):
        raise ValueError('truth does not belong to scaled constellation')
    mean=(p*s[None,:]).sum(1)
    deviation=s[None,:]-mean[:,None]
    variance=(p*(deviation.real**2+deviation.imag**2)).sum(1)
    normalized=variance/data_power
    error=np.abs(truth-mean)**2
    predicted=p.argmax(1); wrong=predicted!=target; confident=p.max(1)>=.9
    correct_probability=p[np.arange(len(p)),target]
    zero=correct_probability==0
    nll=None if zero.any() else float(-np.log(correct_probability).mean())
    if logits is not None:
        logits=np.asarray(logits,dtype=np.float64)
        if logits.shape!=p.shape or not np.isfinite(logits).all():
            raise ValueError('invalid probability logits')
        shifted=logits-logits.max(1,keepdims=True)
        log_probability=shifted-np.log(np.exp(shifted).sum(1,keepdims=True))
        nll=float(-log_probability[np.arange(len(p)),target].mean())
    onehot=np.eye(len(s))[target]
    bins=[]
    for i,(lo,hi) in enumerate(zip(VARIANCE_EDGES[:-1],VARIANCE_EDGES[1:])):
        mask=(normalized>=lo)&((normalized<=hi) if i==len(VARIANCE_EDGES)-2 else (normalized<hi))
        bins.append(dict(lo=lo,hi=hi,count=int(mask.sum()),sum_variance=float(variance[mask].sum()),
            sum_actual_squared_error=float(error[mask].sum()),wrong=int(wrong[mask].sum())))
    high_count=int(confident.sum()); high_errors=int((confident&wrong).sum())
    return dict(count=len(p),bins=bins,out_of_range_count=int(((normalized<0)|(normalized>1)).sum()),
        nll=nll,zero_true_probability_count=int(zero.sum()),nll_status='infinite' if nll is None else 'finite',
        brier=float(((p-onehot)**2).sum(1).mean()),high_confidence_count=high_count,
        high_confidence_errors=high_errors,high_confidence_error_rate=high_errors/high_count if high_count else None,
        high_confidence_error_frequency=high_errors/len(p),
        first_high_confidence_error_symbols=np.flatnonzero(confident&wrong)[:3].tolist(),
        variance_unit='already-scaled symbols; bins use v/data_power')


@torch.no_grad()
def compare_frozen_state(state, *, channel_reference=None, channel_config=None):
    """Three objectives share actual A/y/g/H/sigma; no downstream receiver call."""
    started=time.perf_counter()
    A,y,previous,H=(state[k] for k in ('A','y','g_previous','H'))
    sigma,regularization=state['sigma2'],state['regularization']
    uniform=(state['constellation']-state['constellation'].mean()).abs().square().mean()
    matrices={
        'unweighted': None,
        'uniform': residual_data_covariance(H,torch.full_like(state['finite_variance'],uniform),sigma),
        'dynamic': residual_data_covariance(H,state['finite_variance'],sigma),
    }
    solutions={name:soft_gain_update(A,y,previous,regularization,**(
        {} if C is None else dict(C=C,sigma2=sigma))) for name,C in matrices.items()}
    result={}
    for name,C in matrices.items():
        def objective(g):
            residual=y-A@g
            fit=residual.abs().square().sum() if C is None else sigma*(residual.conj()@torch.linalg.solve(C,residual)).real
            return float(fit+regularization*(g-previous).abs().square().sum())
        result[name]=dict(gains=solutions[name],own_objective_before=objective(previous),
            own_objective_after=objective(solutions[name]),
            same_objective_at_all_solutions={other:objective(g) for other,g in solutions.items()},
            residual_squared_norm=float((y-A@solutions[name]).abs().square().sum()))
    if channel_reference is not None:
        from afdm_sp_joint_unrolled.classical_joint_unrolled import reconstruct_H_torch
        if channel_config is None:
            raise ValueError('channel reference requires reconstruction configuration')
        reference=torch.as_tensor(channel_reference,dtype=A.dtype,device=A.device)
        energy=float(reference.abs().square().sum())
        errors={}
        for name,g in dict(previous=previous,**solutions).items():
            estimate=reconstruct_H_torch(channel_config['N'],state['support_delays'],
                state['support_dopplers'],g,channel_config['c1'],channel_config['c2'],
                channel_config['k_max'],cdtype=A.dtype)
            errors[name]=float((reference-estimate).abs().square().sum())/energy if energy else None
        result['same_support_channel_nmse']=errors
        result['channel_reference_scope']='offline simulation truth only; no receiver or decoder feedback'
    if A.is_cuda:torch.cuda.synchronize()
    result['offline_seconds']=time.perf_counter()-started
    result['scope']='frozen-state objective comparisons; no closed-loop FER'
    return result
