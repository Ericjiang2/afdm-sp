"""Offline counterfactual primitives. Never pass truth to a deployment arm."""
from __future__ import annotations

import hashlib
import math

import numpy as np
import torch

from afdm_sp_joint_unrolled.classical_joint_unrolled import reconstruct_H_torch
from .physical_stride import physical_stride


def array_hash(value):
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode())
    digest.update(str(array.shape).encode())
    digest.update(array.tobytes())
    return digest.hexdigest()


def dev_rng(replicate, frame, stream, *, split=1):
    """Exploratory splits only: D_dev=1, D_cal=2; preserve legacy dev bytes."""
    if split not in (1,2):
        raise ValueError('only D_dev and D_cal are supported by the exploratory runner')
    if min(replicate, frame, stream) < 0:
        raise ValueError('RNG identifiers cannot be negative')
    return np.random.default_rng(np.random.SeedSequence([20260905, split, replicate, frame, stream]))


def project_channel_on_support(H_true, delays, dopplers, c1, c2, k_max):
    """Exact Frobenius LS for the integer Python-convention AFDM dictionary.

    Distinct integer (delay, Doppler) operators are Frobenius orthogonal and
    have squared norm N. Equal row offsets alone do not imply equal atoms:
    the delay-dependent phase also matters. No continuous-channel claim.
    """
    N = H_true.shape[0]
    if (H_true.shape != (N, N) or not H_true.is_complex() or not torch.isfinite(H_true).all()
            or delays.ndim != 1 or delays.shape != dopplers.shape
            or delays.dtype != torch.long or dopplers.dtype != torch.long
            or delays.device != H_true.device or dopplers.device != H_true.device
            or not 0 <= k_max < N/2):
        raise ValueError('invalid channel/support projection inputs')
    pairs = list(zip(delays.tolist(), dopplers.tolist()))
    if (len(set(pairs)) != len(pairs) or any(l < 0 or l >= N or abs(k) > k_max for l,k in pairs)):
        raise ValueError('projection needs unique valid integer atoms')
    stride = physical_stride(N, c1)
    n = torch.arange(N, device=H_true.device, dtype=torch.long)
    n_float = n.to(torch.float64)
    gains = []
    for delay, doppler in pairs:
        rows = (n + delay * stride + doppler) % N
        angle = 2*math.pi*(-c1*delay**2 + c2*(rows.to(torch.float64)**2-n_float**2)
                          - delay*n_float/N)
        phase = torch.exp(1j*angle).to(H_true.dtype)
        gains.append((phase.conj()*H_true[rows, n]).sum()/N)
    gains = torch.stack(gains) if gains else torch.zeros(0, dtype=H_true.dtype, device=H_true.device)
    projected = reconstruct_H_torch(N, delays, dopplers, gains, c1, c2, k_max, H_true.dtype)
    return projected, gains


def keep_omp_support(Phi, y, raw, repaired, h, sigma2):
    """Replace only the initial repair action; the original downstream loop runs."""
    gains = torch.linalg.lstsq(Phi[:, raw], y.unsqueeze(-1)).solution.squeeze(-1)
    return list(raw), gains


def perfect_gain_hook(H_true, cfg):
    cache = {}
    def replace(H, delays, dopplers, iteration):
        key = tuple(zip(delays.tolist(), dopplers.tolist()))
        if key not in cache:
            cache[key] = project_channel_on_support(
                H_true.to(dtype=H.dtype, device=H.device), delays, dopplers,
                cfg.c1, cfg.c2, cfg.k_max)[0]
        return cache[key]
    return replace


def physical_cluster_weights(system, params, rounded=False):
    """One column per physical path, matching the truncated generator exactly.

    Known quantized delays are shared; only Doppler cluster location changes.
    Duplicate/zero physical slots stay present; integer atoms sum via W @ g.
    """
    N, kmax = system.N_total, system.k_max_cap
    P = int(params['taps'])
    W = np.zeros(((system.l_max_cap+1)*(2*kmax+1),P),dtype=np.complex128)
    clip = min(kmax,N//2-system.k_guard-1)
    offsets = np.arange(-system.k_leak,system.k_leak+1)
    for i,(delay,location) in enumerate(zip(params['l_i'],params['k_real'])):
        location = float(np.round(location)) if rounded else float(location)
        center = int(np.round(location))
        alpha = np.asarray([system.dirichlet_alpha(int(m),location-center,N) for m in offsets])
        alpha /= np.sqrt(np.sum(np.abs(alpha)**2)+1e-300)
        power = np.abs(alpha)**2
        for m,w,power_m in zip(offsets,alpha,power):
            k = center+int(m)
            if abs(k)<=clip and power_m>=system.frac_prune_rel_thres*power.max():
                W[int(delay)*(2*kmax+1)+k+kmax,i] = w
    return W


def fit_physical_cluster(system, params, Phi, y, rounded=False):
    """Oracle position, observed pilot LS; truth gains/data are never used."""
    W = physical_cluster_weights(system,params,rounded)
    A = Phi@W
    if not np.isfinite(A).all() or not np.isfinite(y).all() or not np.any(A):
        raise ValueError('physical position reference has invalid or all-zero basis')
    rcond = np.finfo(np.float64).eps*max(A.shape)
    gains,_,rank,singular = np.linalg.lstsq(A,y,rcond=rcond)
    h = W@gains
    cols = np.flatnonzero(np.any(W!=0,axis=1))
    K = 2*system.k_max_cap+1
    H = system.gen_h_daft(h[cols],cols//K,cols%K-system.k_max_cap)
    metadata = dict(position='rounded' if rounded else 'true_truncated',
                    pilot_residual_squared=float(np.linalg.norm(y-A@gains)**2),
                    fitted_gains=dict(real=gains.real.tolist(),imag=gains.imag.tolist()),
                    locations=(np.round(params['k_real']) if rounded else np.asarray(params['k_real'])).tolist(),
                    physical_slots=W.shape[1],rank=int(rank),rank_deficient=bool(rank<W.shape[1]),
                    singular_values=singular.tolist(),rcond=rcond,
                    zero_basis_slots=np.flatnonzero(~np.any(W!=0,axis=0)).tolist(),
                    effective_H_basis_columns=cols.tolist(),basis_sha256=array_hash(W),
                    basis_weights=dict(real=W[cols].real.tolist(),imag=W[cols].imag.tolist()),
                    interpretation='known quantized delay; truncated Doppler basis; minimum-norm pilot LS')
    return H,metadata



def fit_local_physical_cluster(system, known_delays, initial_rounded_locations, Phi, y):
    """Partial oracle: known eight slots; optimize using observed pilot residual only."""
    delays=np.asarray(known_delays);centers=np.asarray(initial_rounded_locations,dtype=float)
    clip=min(system.k_max_cap,system.N_total//2-system.k_guard-1)
    if (delays.shape!=(8,) or centers.shape!=(8,) or not np.isfinite(delays).all()
        or not np.isfinite(centers).all() or np.any(delays!=delays.astype(int))
        or np.any(delays<0) or np.any(delays>system.l_max_cap)
        or np.any(centers!=np.round(centers)) or np.any(np.abs(centers)>clip)):
        raise ValueError('registered local reference needs eight valid known integer slots')
    lower=np.maximum(centers-.5,-clip);upper=np.minimum(centers+.5,clip)
    fits=0;trace=[]
    def fit(locations):
        nonlocal fits
        if fits>=33:raise RuntimeError('registered position fit cap exhausted')
        fits+=1
        # Only known initialization and current trial coordinates enter this adapter.
        params=dict(taps=8,l_i=delays,k_real=locations)
        try:
            H,metadata=fit_physical_cluster(system,params,Phi,y)
        except (ValueError,np.linalg.LinAlgError) as exc:
            raise ValueError(f'position fit {fits}/33 failed: {exc}') from exc
        return H,dict(metadata,position='trial_truncated')
    current=centers.copy();H,meta=fit(current)
    trace.append(dict(stage='initial',fit_index=fits,locations=current.tolist(),fit=meta))
    for sweep,step in enumerate((.25,.125)):
        for path in range(8):
            base=current.copy();best=(current,H,meta);trials=[]
            old_objective=meta['pilot_residual_squared']
            for sign in (-1,1):
                candidate=base.copy();candidate[path]+=sign*step
                event=dict(sweep=sweep,step=step,path=path,sign=sign,locations=candidate.tolist())
                if np.any(candidate<lower) or np.any(candidate>upper):
                    event.update(status='outside_registered_bound');trials.append(event);continue
                candidate_H,candidate_meta=fit(candidate)
                objective=candidate_meta['pilot_residual_squared']
                event.update(status='evaluated',fit_index=fits,fit=candidate_meta)
                trials.append(event)
                threshold=1e-12*max(1.,best[2]['pilot_residual_squared'])
                if objective<best[2]['pilot_residual_squared']-threshold:
                    best=(candidate,candidate_H,candidate_meta)
            current,H,meta=best
            trace.append(dict(stage='coordinate',sweep=sweep,path=path,trials=trials,
                accepted=bool(np.any(current!=base)),before=old_objective,after=meta['pilot_residual_squared'],
                locations=current.tolist()))
    return H,dict(meta,position='local_truncated',initial_rounded_locations=centers.tolist(),
        known_delays=delays.tolist(),fit_count=fits,trace=trace,
        lower=lower.tolist(),upper=upper.tolist(),stop_reason='registered_sweeps_exhausted',
        partial_oracle='known quantized delays and eight rounded physical slots; observed y only for decisions',
        scope='two fixed discrete coordinate sweeps, not continuous global optimum or full interval coverage')


def feedback_statistics(payload, true_data):
    """Score an observed outer-feedback distribution without changing it.

    Temperature rescoring is offline and uses float64. It does not feed its
    mean/variance back to the receiver and is not an observed FER improvement.
    """
    logits = payload['logits'].to(torch.float64)
    constellation = payload['constellation'].to(torch.complex128)
    truth = torch.as_tensor(true_data,device=logits.device,dtype=torch.complex128)
    target = (truth[:,None]-constellation).abs().argmin(-1)
    row = torch.arange(len(truth),device=logits.device)
    onehot = torch.nn.functional.one_hot(target,len(constellation)).to(torch.float64)
    temperature_grid = []
    for temperature in (.25,.5,1.,2.,4.):
        lp = torch.log_softmax(logits/temperature,dim=-1)
        p = lp.exp()
        mu = (p*constellation).sum(-1)
        v = (p*constellation.abs().square()).sum(-1)-mu.abs().square()
        temperature_grid.append(dict(temperature=temperature,nll=float(-lp[row,target].mean()),
                                     brier_sum=float((p-onehot).square().sum(-1).mean()),
                                     mean_variance=float(v.mean()),mean_squared_error=float((truth-mu).abs().square().mean())))
    p = payload['probabilities'].to(torch.float64)
    mu = payload['mean'].to(torch.complex128)
    variance = (p*constellation.abs().square()).sum(-1)-mu.abs().square()
    squared_error = (truth-mu).abs().square()
    edges = (0.,.01,.025,.05,.1,.2,.35,.500001)
    bins = []
    for lo,hi in zip(edges[:-1],edges[1:]):
        selected = (variance.clamp_min(0)>=lo)&(variance.clamp_min(0)<hi)
        n = int(selected.sum())
        bins.append(dict(lower=lo,upper=hi,count=n,
                         predicted_variance_sum=float(variance[selected].sum()),
                         squared_error_sum=float(squared_error[selected].sum())))
    return dict(stage=payload['stage'],outer_iter=payload['outer_iter'],symbols=len(truth),
                feedback_dtype=str(payload['probabilities'].dtype),rescore_dtype='float64',
                negative_variance_count=int((variance<0).sum()),variance_bins=bins,
                mean_input_gaussian_variance=float(payload['input_variance'].mean()),
                temperature_grid=temperature_grid)
