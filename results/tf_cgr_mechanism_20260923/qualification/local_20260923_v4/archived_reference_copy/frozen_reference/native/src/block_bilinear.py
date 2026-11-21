"""Block-gain bilinear EC/AMP research variant with affine-complete corrections.
A finite Gaussian gain block replaces independent gain pseudo-observations.
This defines a local approximate inference map, not exact joint Bayesian inference.
"""
import numpy as np
from scipy.linalg import cho_factor,cho_solve
from physical import Channel,dkernel
from messages import alphabet,marginal,moments

class Basis:
    def __init__(self,c,T=None):
        self.c=c;self.n=c.n;self.p=c.p
        self.T=np.eye(c.p,dtype=complex) if T is None else np.asarray(T,complex)
        self.U=[Channel(c.n,c.c1,c.c2,[l],[nu],[1.]) for l,nu in zip(c.delays,c.dopplers)]
        r=dkernel(c.dopplers[None,:]-c.dopplers[:,None],c.n)*(c.delays[None,:]==c.delays[:,None])
        self.R=self.T.conj().T@r@self.T
        self.h=np.linalg.solve(self.T,c.gains)
        invT=np.linalg.solve(self.T,np.eye(c.p));self.Cg=invT@invT.conj().T/c.p
    def responses(self,x):return self.c.regressors(x)@self.T
    def adjoint(self,h,z):
        return sum(a.conjugate()*u.adjoint(z) for a,u in zip(self.T@h,self.U))
    def Kapply(self,S,x):
        B=self.c.regressors(x);C=self.T@S@self.T.conj().T;BC=B@C
        return sum(u.adjoint(BC[:,j]) for j,u in enumerate(self.U))

def block_amp(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,basis=None):
    n=c.n;P=c.p;o=Basis(c) if basis is None else basis
    if prior is None:prior=np.zeros(2*n)
    a,_=alphabet(pd);p=np.asarray(pilot);mu,v,_=moments(prior,pd);x=p+mu
    h=o.h.copy();S=o.Cg.copy();Cinv=np.linalg.inv(o.Cg);hb=h.copy();xb=x.copy()
    s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[]
    for it in range(iterations):
        B=o.responses(x);vx=float(v.mean())
        bar=float((vx*np.vdot(h,o.R@h)+np.trace(S@(B.conj().T@B))/n).real)
        vp=bar+vx*float(np.trace(o.R@S).real)
        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
        bar0=bar;vp0=vp
        ph=B@h-s*bar
        s=damping*(y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=o.responses(xb);D=sv*(Bb.conj().T@Bb)
        rprec=max(float((sv*np.vdot(hb,o.R@hb)).real),1e-12)
        rx=x+(o.adjoint(hb,s)-sv*o.Kapply(S,xb))/rprec
        info=D@h+Bb.conj().T@s-sv*n*vx*(o.R@hb)
        cf=cho_factor(Cinv+D,lower=True);S=cho_solve(cf,np.eye(P));h=cho_solve(cf,info)
        ext,app,mu,v=marginal(-abs((rx-p)[:,None]-a)**2*rprec,prior,pd);x=p+mu
        if not np.isfinite(h).all():raise FloatingPointError('block AMP nonfinite')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(np.trace(S).real/P),min_gain_cov=float(np.linalg.eigvalsh(S).min())))
    return dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=o.T@h,gain_covariance=o.T@S@o.T.conj().T,trace=trace,iterations=iterations)
