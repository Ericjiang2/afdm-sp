"""Classical fixed-channel Gaussian SISO reference, not a new AMP update."""
import numpy as np
from scipy.linalg import cho_factor,cho_solve


def siso(y,pilot,A,noise,prior,pd,mode):
    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex)
    if y.ndim!=1 or pilot.shape!=y.shape:raise ValueError("expected one-dimensional observation and pilot")
    if np.ndim(noise)!=0 or np.ndim(pd)!=0 or not np.isfinite(noise) or not np.isfinite(pd):raise ValueError("finite scalar noise and power required")
    n=len(y);prior=np.asarray(prior,float);A=np.asarray(A,complex)
    if A.shape!=(n,n) or prior.shape!=(2*n,) or noise<=0 or pd<=0 or mode not in ('proper','augmented'):
        raise ValueError('invalid SISO inputs')
    if np.any(np.abs(prior)>20):raise ValueError('reference expects clipped check prior in [-20,20]')
    if not all(np.isfinite(x).all() for x in (y,pilot,A,prior)):raise ValueError('nonfinite inputs')
    a=np.sqrt(pd/2);mu=a*(np.tanh(prior[:n]/2)+1j*np.tanh(prior[n:]/2))
    vi=a*a/np.cosh(prior[:n]/2)**2;vq=a*a/np.cosh(prior[n:]/2)**2
    v=vi+vq;pseudo=vi-vq;r=y-A@(pilot+mu)
    if mode=='proper':
        C=(A*v)@A.conj().T+noise*np.eye(n)
        factor=cho_factor(C,lower=True,check_finite=False)
        solved=cho_solve(factor,A,check_finite=False)
        post=mu+v*(A.conj().T@cho_solve(factor,r,check_finite=False))
        pv=v-v*v*np.sum(A.conj()*solved,axis=0).real
        if np.any(pv<=0) or not np.isfinite(pv).all():raise FloatingPointError('invalid posterior variance')
        eta=post/pv-mu/v
        llr=4*a*np.r_[eta.real,eta.imag]
    else:
        B=np.block([[A.real,-A.imag],[A.imag,A.real]])
        vv=np.r_[vi,vq];m=np.r_[mu.real,mu.imag]
        C=(B*vv)@B.T+(noise/2)*np.eye(2*n)
        factor=cho_factor(C,lower=True,check_finite=False)
        solved=cho_solve(factor,B,check_finite=False)
        post=m+vv*(B.T@cho_solve(factor,np.r_[r.real,r.imag],check_finite=False))
        pv=vv-vv*vv*np.sum(B*solved,axis=0)
        if np.any(pv<=0) or not np.isfinite(pv).all():raise FloatingPointError('invalid posterior variance')
        eta=post/pv-m/vv;llr=2*a*eta
    if not np.isfinite(llr).all():raise FloatingPointError('nonfinite SISO output')
    return dict(extrinsic=llr,posterior_mean=post,posterior_variance=pv,
                prior_max_abs=float(np.max(np.abs(prior))),min_prior_real_variance=float(min(vi.min(),vq.min())),min_posterior_variance=float(pv.min()),llr_max_abs=float(np.max(np.abs(llr))),clip_saturation_count=int(np.count_nonzero(np.abs(llr)>20)),
                prior_pseudo_l2_ratio=float(np.linalg.norm(pseudo)/max(np.linalg.norm(v),1e-30)),mode=mode)


def channel_matrix(channel):
    n=channel.n;shifts=np.arange(n);k=np.arange(n);A=np.empty((n,n),complex)
    A[(shifts[:,None]+k)%n,k]=channel.diagonals(shifts)
    return A
