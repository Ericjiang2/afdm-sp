"""Declared SISO integer-delay/Doppler-grid-evolution SBL/GAMP adaptation.
Not a byte-for-byte reconstruction of D-GESBL. Differences: known thermal lower bound and declared learned scalar effective CE
variance, no fractional-delay search, exact nonlinear dictionary refresh and
checked coordinate descent of the frozen posterior grid objective. All charged.
"""
import numpy as np
from scipy.linalg import cho_factor,cho_solve
from physical import Channel

def gaussian_posterior(A,y,variance,delta):
    cf=cho_factor(A.conj().T@A/variance+np.diag(1/delta),lower=True)
    V=cho_solve(cf,np.eye(len(delta)));m=cho_solve(cf,A.conj().T@y/variance)
    return m,V

def gamp(A,y,variance,delta,iterations=60,damping=.3,initial=None):
    """Gaussian-prior complex sum-product GAMP. delta denotes VARIANCE."""
    n,q=A.shape;x=np.zeros(q,complex) if initial is None else np.asarray(initial,complex).copy();v=delta.copy();s=np.zeros(n,complex);AA=abs(A)**2;trace=[]
    for it in range(iterations):
        vp=np.maximum(AA@v,1e-14);p=A@x-vp*s
        ss=(y-p)/(variance+vp);vs=1/(variance+vp);s=(1-damping)*s+damping*ss
        vr=1/np.maximum(AA.T@vs,1e-14);r=x+vr*(A.conj().T@s)
        nx=delta*r/(delta+vr);nv=delta*vr/(delta+vr)
        change=float(np.linalg.norm(nx-x)/max(1e-12,np.linalg.norm(x)))
        x=(1-damping)*x+damping*nx;v=(1-damping)*v+damping*nv;trace.append(change)
        if not np.isfinite(x).all() or np.max(abs(x))>1e12:raise FloatingPointError('GAMP divergence')
    return x,v,trace

def frozen_loss(y,A,m,V):
    r=y-A@m
    return float(np.vdot(r,r).real+(np.dot(np.sum(abs(A)**2,axis=0),V) if V.ndim==1 else np.einsum('ij,ji->',A.conj().T@A,V).real))

def estimate(y,x,c1,c2,noise,delays,dopplers,initial=None,backend='gamp',outer=5,inner=40,damping=.3,active_cap=8,hyper_b=1e-4,learn_noise=False,initial_delta=None):
    n=len(y);l=np.asarray(delays,int).copy();nu=np.asarray(dopplers,float).copy();q=len(l)
    if backend not in ('gamp','exact'):raise ValueError('Unknown SBL backend')
    m=np.zeros(q,complex) if initial is None else np.asarray(initial,complex).copy()
    delta=np.maximum(abs(m)**2,1/q) if initial_delta is None else np.asarray(initial_delta,float).copy();records=[]
    if delta.shape!=(q,) or np.any(delta<=0) or not np.isfinite(delta).all():raise ValueError("Invalid SBL variance state")
    thermal_floor=float(noise);effective_noise=float(noise)
    if learn_noise:effective_noise+=.5*float(np.sum(abs(m)**2))
    for t in range(outer):
        c=Channel(n,c1,c2,l,nu,np.ones(q));A=c.regressors(x)
        if backend=='gamp':
            m,vd,tr=gamp(A,y,effective_noise,delta,iterations=inner,damping=damping,initial=m);V=vd.copy()
        else:m,V=gaussian_posterior(A,y,effective_noise,delta);vd=V.diagonal().real;tr=[]
        stat=abs(m)**2+vd;delta=np.maximum(2*stat/(1+np.sqrt(1+4*hyper_b*stat)),1e-12)
        J=c.regressors(x,True);before=frozen_loss(y,A,m,V);current=before;accepted=0
        active=np.argsort(-stat,kind='stable')[:active_cap]
        for j in active:
            r=y-A@m;den=max(float(stat[j]*np.vdot(J[:,j],J[:,j]).real),1e-12)
            num=float((m[j].conjugate()*np.vdot(J[:,j],r)-(V[j]*np.vdot(J[:,j],A[:,j]) if V.ndim==1 else np.vdot(J[:,j],A@V[:,j]))).real)
            step=float(np.clip(num/den,-.5,.5));old=nu[j]
            for scale in (1.,.5,.25):
                trial=float(np.clip(old+scale*step,-3.,3.));cc=Channel(n,c1,c2,[l[j]],[trial],[1.]);column=cc.regressors(x)[:,0];B=A.copy();B[:,j]=column
                value=frozen_loss(y,B,m,V)
                if value<=current+1e-10*max(1,current):
                    nu[j]=trial;A=B;current=value;accepted+=1;break
        if learn_noise:effective_noise=max(thermal_floor,current/n)
        records.append(dict(outer=t,effective_ce_variance=effective_noise,grid_loss_before=before,grid_loss_after=current,accepted=accepted,gamp_updates=len(tr),gamp_last_change=tr[-1] if tr else None))
    # Refresh gain posterior for the final evolved dictionary.
    A=Channel(n,c1,c2,l,nu,np.ones(q)).regressors(x)
    if backend=='exact':m,V=gaussian_posterior(A,y,effective_noise,delta)
    else:m,vd,_=gamp(A,y,effective_noise,delta,iterations=inner,damping=damping,initial=m);V=vd.copy()
    ids=np.argsort(-abs(m)**2,kind='stable')[:active_cap]
    return Channel(n,c1,c2,l[ids],nu[ids],m[ids]),dict(history=records,full_gains=m,full_dopplers=nu,delta=delta,posterior_variance=(V if V.ndim==1 else V.diagonal().real),backend=backend)
