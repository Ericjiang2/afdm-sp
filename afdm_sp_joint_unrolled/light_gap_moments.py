"""Finite-QPSK and AFDM moment algebra for explicitly labelled diagnostics.

The lag compression is exact for a supplied covariance and integer operators.
It does not make factorized or restricted-codeword posteriors exact.
"""
from __future__ import annotations
import numpy as np


def qpsk_moments(llr, amp=.5):
    llr = np.asarray(llr)
    if (llr.ndim != 1 or not len(llr) or len(llr)%2 or np.iscomplexobj(llr)
            or not np.isfinite(llr).all() or not np.isfinite(amp) or amp <= 0):
        raise ValueError('finite I-then-Q LLRs and positive amplitude required')
    n = len(llr)//2
    ti,tq = np.tanh(llr[:n]/2),np.tanh(llr[n:]/2)
    mean = amp*(ti+1j*tq)
    variance = amp**2*(2-ti**2-tq**2)
    pseudo = amp**2*(tq**2-ti**2)
    return dict(mean=mean,variance=variance,pseudovariance=pseudo)


def improper_metric(residual, variance, pseudovariance):
    """Log Gaussian quadratic term; variance covers both real dimensions."""
    e,v,c = np.broadcast_arrays(residual,variance,pseudovariance)
    if (np.iscomplexobj(v) or any(not np.isfinite(a).all() for a in (e,v,c))
            or np.any(v <= 0) or np.any(np.abs(c) >= v)):
        raise ValueError('finite nonsingular complex Gaussian moments required')
    return -(v*np.abs(e)**2-np.real(np.conj(c)*e**2))/(v**2-np.abs(c)**2)


def circular_kl(variance, pseudovariance):
    v,c = np.broadcast_arrays(variance,pseudovariance)
    improper_metric(np.zeros_like(c),v,c)
    return -.5*np.log1p(-(np.abs(c)/v)**2)


def atom_layout(n, delays, dopplers, c1, c2, kmax=2):
    """Input-indexed unit-modulus phases and circular displacements."""
    dl,dk = np.asarray(delays),np.asarray(dopplers)
    if (type(n) is not int or n < 1 or dl.ndim != 1 or dk.shape != dl.shape
            or not len(dl) or dl.dtype.kind not in 'iu' or dk.dtype.kind not in 'iu'
            or np.any(dl < 0) or np.any(dl >= n) or np.any(np.abs(dk) > kmax)
            or not np.isfinite([c1,c2]).all()):
        raise ValueError('valid finite integer AFDM atom geometry required')
    offsets = (dl*(2*kmax+1)+dk)%n
    x = np.arange(n)[:,None]
    out = (x+offsets[None,:])%n
    phases = np.exp(2j*np.pi*(-c1*dl[None,:]**2+c2*(out**2-x**2)-x*dl[None,:]/n))
    return offsets,phases


def required_lags(offsets, n):
    offsets = np.asarray(offsets)
    return np.unique((offsets[:,None]-offsets[None,:])%n)


def covariance_lags(covariance, offsets):
    cov = np.asarray(covariance)
    if (cov.ndim != 2 or cov.shape[0] != cov.shape[1] or not np.isfinite(cov).all()
            or not np.allclose(cov,cov.conj().T,rtol=1e-10,atol=1e-12)):
        raise ValueError('finite Hermitian covariance required')
    n = len(cov)
    x = np.arange(n)
    return {int(d):cov[(x+d)%n,x].copy() for d in required_lags(offsets,n)}


def compressed_gram(offsets, phases, lags):
    """Gamma_ij = tr(U_i^H U_j C), using C[n+delta,n] only."""
    phases,offsets = np.asarray(phases),np.asarray(offsets)
    n,k = phases.shape
    if offsets.shape != (k,) or not np.isfinite(phases).all():
        raise ValueError('phase and offset dimensions differ')
    needed = set(map(int,required_lags(offsets,n)))
    if set(lags) != needed or any(np.shape(v)!=(n,) or not np.isfinite(v).all() for v in lags.values()):
        raise ValueError('exact finite support difference-set statistics required')
    x = np.arange(n)
    gamma = np.empty((k,k),dtype=np.complex128)
    for i in range(k):
        for j in range(k):
            d = int((offsets[i]-offsets[j])%n)
            gamma[i,j] = np.sum(phases[:,i].conj()*phases[(x+d)%n,j]*lags[d])
    if not np.allclose(gamma,gamma.conj().T,rtol=1e-9,atol=1e-10):
        raise ValueError('compressed uncertainty Gram is not Hermitian')
    return gamma


def weighted_sample_lags(samples, weights, offsets):
    samples,weights = np.asarray(samples),np.asarray(weights)
    if (samples.ndim != 2 or weights.shape != (len(samples),) or np.iscomplexobj(weights)
            or any(not np.isfinite(v).all() for v in (samples,weights)) or np.any(weights<0)
            or not np.isclose(weights.sum(),1.,rtol=1e-12,atol=1e-12)):
        raise ValueError('finite complex samples and normalized nonnegative weights required')
    mean = weights@samples
    center = samples-mean[None,:]
    n = samples.shape[1]
    x = np.arange(n)
    lags = {int(d):np.sum(weights[:,None]*center[:,(x+d)%n]*center.conj(),axis=0)
            for d in required_lags(offsets,n)}
    return mean,lags


def code_subspace_posterior(code, decoded, llr, free_bits=5):
    """Exact likelihood weights within 2**free_bits legal neighboring words.

    This is a restricted posterior, not a sampler of the full LDPC posterior.
    It can diagnose compression algebra but cannot certify neglected mass.
    """
    llr,decoded = np.asarray(llr),np.asarray(decoded)
    if (type(free_bits) is not int or not 1<=free_bits<=8 or free_bits>code['k']
            or decoded.shape!=(code['n'],) or llr.shape!=decoded.shape
            or not np.isin(decoded,(0,1)).all() or not np.isfinite(llr).all()):
        raise ValueError('matched finite codeword likelihood and bounded subspace required')
    free = np.asarray(code['free_cols'])
    ids = np.argsort(np.abs(llr[free]),kind='stable')[:free_bits]
    information = np.repeat(decoded[free][None,:],2**free_bits,axis=0).astype(np.int32)
    flips = (np.arange(2**free_bits)[:,None] >> np.arange(free_bits)[None,:])&1
    information[:,ids] ^= flips
    words = ((information@np.asarray(code['G'],dtype=np.int32).T)%2).astype(np.uint8)
    if np.any((np.asarray(code['H'],dtype=np.int32)@words.astype(np.int32).T)%2):
        raise ValueError('constructed neighbor is not a legal codeword')
    logweights = .5*((1-2*words.astype(float))@llr)
    weights = np.exp(logweights-logweights.max())
    weights /= weights.sum()
    n = code['n']//2
    samples = .5*(1-2*words[:,:n].astype(float))+.5j*(1-2*words[:,n:].astype(float))
    return dict(samples=samples,weights=weights,words=words,selected_information_ids=ids,
        effective_sample_size=float(1/np.sum(weights**2)),largest_weight=float(weights.max()),
        scope=f'exact restricted {2**free_bits}-word likelihood posterior; missing full-posterior mass unknown')


def residual_decomposition(observed, true_h, data, estimated_h, mean, variance):
    """Identity on actual arrays; covariance correction remains an approximation."""
    y,p = observed['y'],observed['pilot']
    h,x,hh,m,v = map(np.asarray,(true_h,data,estimated_h,mean,variance))
    n = len(y)
    terms = dict(noise=y-h@(p+x),channel=(h-hh)@(p+x),symbol=hh@(x-m))
    residual = y-hh@(p+m)
    error = float(np.linalg.norm(residual-sum(terms.values()))/max(1.,np.linalg.norm(residual)))
    if error > 1e-10 or v.shape!=(n,) or np.any(v<0) or not np.isfinite(v).all():
        raise ValueError('residual identity or finite variance contract failed')
    powers = {k:float(np.vdot(a,a).real/n) for k,a in terms.items()}
    keys = list(terms)
    cross = {keys[i]+'__'+keys[j]:float(2*np.vdot(terms[keys[i]],terms[keys[j]]).real/n)
             for i in range(3) for j in range(i+1,3)}
    residual_power = float(np.vdot(residual,residual).real/n)
    correction = float(np.dot((np.abs(hh)**2).sum(0),v)/n)
    return dict(residual_power=residual_power,powers=powers,cross_terms=cross,
        identity_relative_error=error,diagonal_uncertainty_power=correction,
        approximate_moment_noise=residual_power+correction,
        interpretation='same-observation finite-moment approximation; no unbiasedness/FER guarantee')


def graph_pseudovariance(h, variance, pseudovariance, noise, threshold=1e-4):
    h,v,c = map(np.asarray,(h,variance,pseudovariance))
    n = len(h)
    if (h.shape!=(n,n) or v.shape!=(n,) or c.shape!=(n,) or noise<=0
            or not np.isfinite(noise) or any(not np.isfinite(x).all() for x in (h,v,c))
            or np.any(v<0) or np.any(np.abs(c)>v+1e-12)):
        raise ValueError('valid diagonal complex moments and noise required')
    row,col = np.nonzero(np.abs(h)>=threshold)
    edge = h[row,col]
    ev,ec = np.abs(edge)**2*v[col],edge**2*c[col]
    total_v = np.full(n,float(noise));total_c=np.zeros(n,dtype=np.complex128)
    np.add.at(total_v,row,ev);np.add.at(total_c,row,ec)
    excluded_v,excluded_c = total_v[row]-ev,total_c[row]-ec
    zeta = np.abs(excluded_c)/excluded_v
    kl = circular_kl(excluded_v,excluded_c)
    quantiles = [0,.5,.9,.95,.99,1]
    return dict(row=row,col=col,excluded_variance=excluded_v,excluded_pseudovariance=excluded_c,
        zeta=zeta,kl=kl,summary=dict(edges=len(row),quantiles=quantiles,
            zeta_quantiles=np.quantile(zeta,quantiles).tolist() if len(row) else [0.]*6,
            KL_mean=float(kl.mean()) if len(kl) else 0.,
            fraction_zeta_gt_01=float(np.mean(zeta>.1)) if len(row) else 0.,
            fraction_zeta_gt_02=float(np.mean(zeta>.2)) if len(row) else 0.,
            scope='node-marginal proxy on actual thresholded graph; not historical edge cavities'))
