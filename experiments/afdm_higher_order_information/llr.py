"""Legal common-node likelihood ratios and defensive contrast-guided proposals."""
import numpy as np
from scipy.special import logsumexp
from scipy.stats import qmc
from scipy.special import ndtri

from experiments.afdm_shared_channel_20261004.probability import (
    outside_cavity,log_bit_prior,real_matrix,packed)
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk


def base_nodes(count,p,rng,method='iid'):
    if count<1 or p<1: raise ValueError('positive node count and dimension required')
    if method=='iid': return (rng.normal(size=(count,p))+1j*rng.normal(size=(count,p)))/np.sqrt(2)
    if method!='qmc' or count & (count-1): raise ValueError('QMC requires a power of two')
    normal=ndtri(qmc.Sobol(2*p,scramble=True,seed=rng).random_base2(int(np.log2(count))))
    if not np.isfinite(normal).all(): raise FloatingPointError('nonfinite inverse-normal node')
    return (normal[:,:p]+1j*normal[:,p:])/np.sqrt(2)


def gain_pushforward(base,prior):
    if prior=='Gaussian': return base/np.sqrt(base.shape[1])
    if prior!='sphere': raise ValueError('unknown declared gain prior')
    norm=np.linalg.norm(base,axis=1)
    if np.any(norm==0): raise ValueError('sphere map undefined at zero')
    return base/norm[:,None]


def log_values(y,operators,pilot,incoming,noise,nodes,object_name,sign=None,batch=1024):
    """f_0(h), f_1(h) for target I bit at data index 0, own factor excluded.

    Each side includes all other incoming factors. QPSK is a full finite outside
    marginal; Gaussian-outside has one symbol block and real cavity covariance.
    The optional sign evaluates only that side for a fair independent-node arm.
    """
    y,pilot,nodes=np.asarray(y,complex),np.asarray(pilot,complex),np.asarray(nodes,complex)
    n=len(pilot); incoming=np.asarray(incoming,float)
    if (nodes.ndim!=2 or not np.isfinite(nodes).all() or incoming.shape!=(2*n,)
            or not np.isfinite(incoming).all() or not np.isfinite(noise) or noise<=0
            or sign not in (None,0,1)):
        raise ValueError('invalid finite message inputs')
    if object_name=='QPSK':
        words,bits=enumerate_qpsk(n); target=bits[:,0]
        other=np.arange(2*n)!=0
        log_prior=log_bit_prior(bits[:,other],incoming[other])
        x=pilot+words; cavity=None
    elif object_name=='Gaussian-outside':
        words,bits=enumerate_qpsk(1); target=bits[:,0]
        _,mean,cavity=outside_cavity(n,[0],incoming)
        x=np.broadcast_to(pilot+mean,(4,n)).copy();x[:,0]+=words[:,0]
        log_prior=log_bit_prior(bits[:,1:],incoming[[n]])
    else: raise ValueError('unknown probability object')
    signs=[0,1] if sign is None else [sign]
    mask=np.ones(len(x),bool) if sign is None else target==sign
    x,log_prior,target=x[mask],log_prior[mask],target[mask]
    output=np.empty((len(nodes),len(signs)))
    for start in range(0,len(nodes),batch):
        h=np.einsum('tp,pij->tij',nodes[start:start+batch],operators)
        residual=y[None,None,:]-np.einsum('tij,kj->tki',h,x)
        if cavity is None:
            density=-n*np.log(np.pi*noise)-np.sum(abs(residual)**2,axis=2)/noise
        else:
            rh=real_matrix(h)
            covariance=noise/2*np.eye(2*n)+rh@cavity@rh.transpose(0,2,1)
            chol=np.linalg.cholesky(covariance)
            white=np.linalg.solve(chol,packed(residual).transpose(0,2,1))
            density=(-n*np.log(2*np.pi)-np.log(np.diagonal(chol,axis1=1,axis2=2)).sum(axis=1)[:,None]
                     -.5*np.sum(white**2,axis=1))
        for j,label in enumerate(signs):
            output[start:start+batch,j]=logsumexp(density[:,target==label]+log_prior[target==label],axis=1)
    if not np.isfinite(output).all(): raise FloatingPointError('nonfinite conditional likelihood')
    ledger=dict(gain_nodes=len(nodes),word_responses=len(nodes)*len(x),
                conditional_cholesky=len(nodes) if cavity is not None else 0,
                probability_object=object_name)
    return output,ledger


def log_integrals(logf,log_ratio=None):
    logf=np.asarray(logf,float)
    if logf.ndim!=2 or not np.isfinite(logf).all(): raise ValueError('finite log likelihood matrix required')
    ratio=np.zeros(len(logf)) if log_ratio is None else np.asarray(log_ratio,float)
    if ratio.shape!=(len(logf),) or not np.isfinite(ratio).all(): raise ValueError('invalid prior/proposal log ratio')
    return logsumexp(logf+ratio[:,None],axis=0)-np.log(len(logf))


def ratio_result(logm):
    logm=np.asarray(logm,float)
    if logm.shape!=(2,) or not np.isfinite(logm).all(): raise ValueError('positive finite two-side integrals required')
    logp=logm-logsumexp(logm)
    return dict(log_m=logm,probability=np.exp(logp),llr=float(logm[0]-logm[1]))


def fit_contrast_proposal(base,logf,regularization=.1):
    """Fit one proper Gaussian to estimated |f0/m0-f1/m1| using pilot nodes.

    This changes only a proposal. All later samples use exact base pi/rho, and
    pilot samples are not reused in the final estimator.
    """
    estimates=log_integrals(logf)
    normalized=np.exp(logf-estimates)
    contrast=np.abs(normalized[:,0]-normalized[:,1])
    dimension=base.shape[1]
    if contrast.sum()==0:
        return dict(mean=np.zeros(dimension,complex),covariance=np.eye(dimension),
                    pilot_log_m=estimates,degenerate_contrast=True,regularization=regularization)
    weights=contrast/contrast.sum(); mean=weights@base; centered=base-mean
    covariance=np.einsum('t,ti,tj->ij',weights,centered,centered.conj())
    covariance=(1-regularization)*covariance+regularization*np.eye(dimension)
    return dict(mean=mean,covariance=covariance,pilot_log_m=estimates,
                degenerate_contrast=False,regularization=regularization)


def gaussian_log_density(nodes,mean,covariance):
    chol=np.linalg.cholesky(covariance)
    whitened=np.linalg.solve(chol,(nodes-mean).T)
    return (-len(mean)*np.log(np.pi)-2*np.log(chol.diagonal().real).sum()
            -np.sum(abs(whitened)**2,axis=0))


def defensive_sample(count,proposal,rng,prior_fraction=.5):
    if not 0<prior_fraction<=1: raise ValueError('positive defensive prior fraction required')
    p=len(proposal['mean']); z=base_nodes(count,p,rng)
    component=rng.random(count)>=prior_fraction
    chol=np.linalg.cholesky(proposal['covariance'])
    z[component]=proposal['mean']+z[component]@chol.T
    logpi=-p*np.log(np.pi)-np.sum(abs(z)**2,axis=1)
    logq=gaussian_log_density(z,proposal['mean'],proposal['covariance'])
    logrho=np.logaddexp(np.log(prior_fraction)+logpi,np.log1p(-prior_fraction)+logq) if prior_fraction<1 else logpi
    logratio=logpi-logrho
    if np.max(logratio)>-np.log(prior_fraction)+1e-12: raise AssertionError('defensive bound violated')
    return z,logratio,component


def iid_llr_variance(logf,logm,log_ratio=None):
    """IID plug-in variance of the normalized weight difference, not a QMC CI."""
    ratio=np.zeros(len(logf)) if log_ratio is None else np.asarray(log_ratio)
    contrast=np.exp(logf[:,0]+ratio-logm[0])-np.exp(logf[:,1]+ratio-logm[1])
    return float(np.var(contrast,ddof=1))


def epsilon_error_bound(e0,e1,epsilon):
    if not 0<=epsilon<1 or max(abs(e0),abs(e1))>epsilon:
        raise ValueError('relative errors must lie within epsilon<1')
    return abs(e0-e1)/(1-epsilon)
