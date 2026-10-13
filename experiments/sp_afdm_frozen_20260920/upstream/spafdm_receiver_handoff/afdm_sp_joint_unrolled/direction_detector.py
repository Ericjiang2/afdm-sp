"""Frozen real-EP10 diagnostic reference. Not ML, a bound, or a learned detector."""
from __future__ import annotations

import time

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.e1_ldpc import decode_llr, extract_info

DETECTOR_ID = 'real-EP10-damp0.5-f64'


def detect(y_cancelled, H, sigma_complex, constellation, *, device='cpu'):
    """Observed-only fixed ten-round EP; extra keyword inputs are rejected.

    Output mu/var are discrete tilted moments under the EP cavity approximation,
    not exact joint-posterior marginals. LLR is computed from
    the cavity natural parameter, never by Gaussian-demapping these moments.
    The caller labels whether its supplied H is estimated or diagnostic oracle.
    """
    y=np.asarray(y_cancelled)
    h=np.asarray(H)
    const=np.asarray(constellation)
    if (y.ndim!=1 or not len(y) or h.shape!=(len(y),len(y)) or const.shape!=(4,)
            or any(not np.iscomplexobj(v) or not np.isfinite(v).all() for v in (y,h,const))):
        raise ValueError('finite complex y(N), H(N,N), QPSK(4) required')
    sigma=np.asarray(sigma_complex)
    if sigma.ndim!=0 or np.iscomplexobj(sigma) or not np.isfinite(sigma) or sigma<=0:
        raise ValueError('sigma_complex must be positive finite total complex variance')
    expected=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
    if not np.allclose(const,expected,rtol=1e-12,atol=1e-12):
        raise ValueError('frozen detector requires QPSK +/-0.5 +/-j0.5 in registered order')
    dev=torch.device(device)
    if dev.type=='cuda' and not torch.cuda.is_available():
        raise ValueError('requested CUDA unavailable; no alternate detector/device')
    started=time.perf_counter()
    n=len(y);a=.5;real_noise=float(sigma)/2
    hc=torch.tensor(h,dtype=torch.complex128,device=dev)
    yc=torch.tensor(y,dtype=torch.complex128,device=dev)
    Hreal=torch.cat((torch.cat((hc.real,-hc.imag),dim=1),
                     torch.cat((hc.imag,hc.real),dim=1)),dim=0)
    yr=torch.cat((yc.real,yc.imag))
    gram=Hreal.T@Hreal/real_noise
    natural=Hreal.T@yr/real_noise
    # All state is fresh per call; no external site/cache state is accepted.
    lam=torch.full((2*n,),1/a**2,dtype=torch.float64,device=dev)
    gamma=torch.zeros_like(lam)
    trace=[]
    for iteration in range(10):
        precision=gram+torch.diag(lam)
        rhs=natural+gamma
        factor=torch.linalg.cholesky(precision)
        gaussian_mean=torch.cholesky_solve(rhs[:,None],factor).squeeze(1)
        covariance_diagonal=torch.cholesky_inverse(factor).diagonal()
        if (not torch.isfinite(gaussian_mean).all() or not torch.isfinite(covariance_diagonal).all()
                or bool((covariance_diagonal<=0).any())):
            raise FloatingPointError('invalid EP Gaussian mean/covariance diagonal')
        cavity_precision=1/covariance_diagonal-lam
        cavity_eta=gaussian_mean/covariance_diagonal-gamma
        raw_llr=2*a*cavity_eta
        posterior_mean=a*torch.tanh(raw_llr/2)
        raw_variance=a*a-posterior_mean.square()
        posterior_variance=raw_variance.clamp_min(1e-12)
        proposed_lam=1/posterior_variance-cavity_precision
        proposed_gamma=posterior_mean/posterior_variance-cavity_eta
        if not all(bool(torch.isfinite(v).all()) for v in
                   (cavity_precision,cavity_eta,raw_llr,proposed_lam,proposed_gamma)):
            raise FloatingPointError('nonfinite EP cavity or site proposal')
        accepted=proposed_lam>0
        # Registered algorithm guard: nonpositive precision proposals retain both
        # previous site parameters. Cholesky/nonfinite failures are never hidden.
        next_lam=torch.where(accepted,.5*lam+.5*proposed_lam,lam)
        next_gamma=torch.where(accepted,.5*gamma+.5*proposed_gamma,gamma)
        residual=torch.linalg.vector_norm(precision@gaussian_mean-rhs)/torch.clamp_min(torch.linalg.vector_norm(rhs),1.)
        trace.append({'iteration':iteration+1,'rejected_sites':int((~accepted).sum()),
            'variance_floor_sites':int((raw_variance<1e-12).sum()),
            'cavity_precision_min':float(cavity_precision.min()),
            'site_precision_min':float(next_lam.min()),'site_precision_max':float(next_lam.max()),
            'linear_relative_residual':float(residual)})
        lam,gamma=next_lam,next_gamma
    if dev.type=='cuda':torch.cuda.synchronize(dev)
    mean=posterior_mean.detach().cpu().numpy()
    # Return the actual finite-alphabet variance. The floor only regularizes site
    # moment matching; it does not become a fictitious uncertainty in the output.
    variance=raw_variance.detach().cpu().numpy()
    raw=raw_llr.detach().cpu().numpy()
    llr=np.clip(raw,-20.,20.)
    mu=mean[:n]+1j*mean[n:]
    var=variance[:n]+variance[n:]
    hard=a*np.where(raw[:n]>=0,1.,-1.)+1j*a*np.where(raw[n:]>=0,1.,-1.)
    diagnostics={'detector_id':DETECTOR_ID,'iterations':10,'damping':.5,'dtype':'float64',
        'matrix_shape':list(Hreal.shape),'sigma_complex':float(sigma),'sigma_real':real_noise,
        'input_hashes':{'y_cancelled':array_hash(y),'H':array_hash(h),'constellation':array_hash(const)},
        'fresh_sites':True,'trace':trace,'rejected_site_proposals':sum(t['rejected_sites'] for t in trace),
        'variance_floor_uses':sum(t['variance_floor_sites'] for t in trace),
        'raw_llr_sha256':array_hash(raw),'seconds':time.perf_counter()-started,
        'moment_semantics':'finite-QPSK tilted moments under EP cavity approximation, not exact joint marginals; unclipped cavity LLR used for tanh; variance floor applies only to site updates',
        'LLR_semantics':'log P(bit0)/P(bit1); all real bits then imaginary bits; clip20 after moment calculation',
        'scope':'diagnostic approximate reference, no truth or code constraint input; not optimality evidence'}
    return {'mu':mu,'var':var,'llr':llr,'raw_llr':raw,'hard':hard,'diagnostics':diagnostics}


def terminal(y_cancelled,H,sigma_complex,constellation,code,*,device='cpu'):
    """Decode the EP cavity LLR directly using the existing fixed-budget LDPC."""
    if code['n']!=2*len(y_cancelled):
        raise ValueError('code length and detector observation disagree')
    result=detect(y_cancelled,H,sigma_complex,constellation,device=device)
    decoded,ok=decode_llr(code,result['llr'],maxiter=50)
    return dict(result,decoded=decoded,info_hat=extract_info(code,decoded),decode_ok=bool(ok))
