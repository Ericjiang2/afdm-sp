"""Coded SP bilinear Gaussian-factor BP adaptation of the PBiGaBP family.
Not a verbatim published receiver: candidate-dependent SP variance is retained,
proper gain posteriors use factor-cavity means/variances, integer-delay geometry
is supplied by a charged observed-only estimator. No true gains/geometry.
This dense reference is deliberately not advertised as production optimized.
"""
import numpy as np
from scipy.special import logsumexp
from physical import Channel
from messages import alphabet,logprior,marginal

def operators(c):
    n=c.n;k=np.arange(n);s=(k[:,None]-k[None,:])%n
    out=[]
    for l,nu in zip(c.delays,c.dopplers):
        q=Channel(n,c.c1,c.c2,[l],[nu],[1.]);d=q.diagonals(np.arange(n));out.append(d[s,k[None,:]])
    return np.asarray(out)

def pbigabp(y,pilot,c,noise,pd=.5,prior=None,iterations=8,damping=.3,gain_prior_variance=None):
    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex);n=len(y);P=c.p
    if prior is None:prior=np.zeros(2*n)
    tau=1/P if gain_prior_variance is None else gain_prior_variance
    U=operators(c);A2=abs(U)**2;lp=logprior(prior,pd);a,_=alphabet(pd)
    prob=np.broadcast_to(np.exp(lp),(n,n,4)).copy()
    hm=np.broadcast_to(c.gains,(n,P)).copy();hv=np.full((n,P),tau);trace=[]
    for it in range(iterations):
        mu=prob@a;v=np.maximum(pd-abs(mu)**2,0);mx=mu+pilot[None,:]
        Phi=np.einsum('pnk,nk->np',U,mx,optimize=True);Uvar=np.einsum('pnk,nk->np',A2,v,optimize=True)
        H=np.einsum('np,pnk->nk',hm,U,optimize=True);ym=np.sum(hm*Phi,axis=1)
        # Channel-factor likelihoods: approximate variance of uncertain regressor
        # uses its incoming second moment, matching the stated Gaussian-family scope.
        gprec=np.zeros((n,P));geta=np.zeros((n,P),complex)
        for p in range(P):
            Hother=H-hm[:,p,None]*U[p];res=y-ym+hm[:,p]*Phi[:,p]
            nv=noise+np.sum(abs(Hother)**2*v,axis=1)+np.sum(hv*(abs(Phi)**2+Uvar),axis=1)-hv[:,p]*(abs(Phi[:,p])**2+Uvar[:,p])+(abs(hm[:,p])**2+hv[:,p])*Uvar[:,p]
            nv=np.maximum(nv,1e-12);gprec[:,p]=abs(Phi[:,p])**2/nv;geta[:,p]=Phi[:,p].conj()*res/nv
        gv=1/(1/tau+gprec.sum(axis=0)[None,:]-gprec);gm=gv*(geta.sum(axis=0)[None,:]-geta)
        # Probability-mixture damping, including between-mean variance.
        hv=(1-damping)*hv+damping*gv+damping*(1-damping)*abs(hm-gm)**2;hm=(1-damping)*hm+damping*gm
        H=np.einsum('np,pnk->nk',hm,U,optimize=True);ym=np.sum(hm*Phi,axis=1)
        base=noise+np.sum(abs(H)**2*v,axis=1)+np.sum(hv*Uvar,axis=1)
        factors=np.empty((n,n,4))
        hu2=np.einsum('np,pnk->nk',hv,A2,optimize=True)
        for j,x in enumerate(a):
            shift=x-mu;ymx=ym[:,None]+H*shift
            var=base[:,None]-(abs(H)**2+hu2)*v
            # Gain uncertainty couples the known pilot, target symbol, and others.
            for p in range(P):var+=hv[:,p,None]*abs(Phi[:,p,None]+U[p]*shift)**2
            var=np.maximum(var,1e-12);factors[:,:,j]=-np.log(var)-abs(y[:,None]-ymx)**2/var
        factors-=factors.max(axis=-1,keepdims=True);lik=factors.sum(axis=0)
        cavity=lp[None,:,:]+lik[None,:,:]-factors;cavity=np.exp(cavity-logsumexp(cavity,axis=-1,keepdims=True))
        prob=(1-damping)*prob+damping*cavity
        trace.append(dict(iteration=it,gain_variance=float(hv.mean()),data_variance=float(v.mean())))
    ext,app,mu,v=marginal(lik,prior,pd)
    gainvar=1/(1/tau+gprec.sum(axis=0));gain=gainvar*geta.sum(axis=0)
    return dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=gain,gain_variance=gainvar,trace=trace,iterations=iterations)
