"""Research prototype: deterministic AFDM contractions and P-BiG-AMP variants.
Base ancestry: Parker/Schniter P-BiG-AMP, Table III and eqs 79--86.
No state-evolution or posterior-exactness claim for deterministic AFDM operators.
The `coherent` variant retains the weighted off-diagonal terms discarded in
81 and its gain-side analogue. This is an explicit, testable finite-operator
modification, not a claim to invent AMP or Onsager corrections.
"""
from dataclasses import dataclass
import numpy as np
from physical import Channel, dkernel
from messages import alphabet, marginal, moments

@dataclass
class Contractions:
    channel: Channel
    def __post_init__(self):
        c=self.channel;n=c.n;self.n=n;self.P=c.p;self.k=np.arange(n)
        self.units=[Channel(n,c.c1,c.c2,[l],[nu],[1.]) for l,nu in zip(c.delays,c.dopplers)]
        D=dkernel(c.dopplers[:,None]+2*n*c.c1*c.delays[:,None]-self.k[None,:],n)
        self.D=D
        # Cross pair kernels without path gains.
        self.F=np.fft.fft(D[:,None,:]*D[None,:,:].conj(),axis=-1)
        r=c.delays[:,None]-c.delays[None,:]
        self.mod=np.exp(-2j*np.pi*r[:,:,None]*self.k/n)
        self.cp=np.exp(2j*np.pi*c.c1*(c.delays[None,:]**2-c.delays[:,None]**2))
    def responses(self,x):return self.channel.regressors(x)
    def apply(self,h,x):return self.responses(x)@h
    def adjoint(self,h,z):
        return sum(g.conjugate()*u.adjoint(z) for g,u in zip(h,self.units))
    def cross_rows(self,v):
        """T[i,j,m] = diag(U_i diag(v) U_j^H)[m]."""
        return self.cp[:,:,None]*np.fft.ifft(self.F*np.fft.fft(self.mod*v,axis=-1),axis=-1)
    def squared_forward(self,h,v):
        T=self.cross_rows(v)
        out=np.einsum('i,j,ijm->m',h,h.conj(),T,optimize=True).real
        return np.maximum(out,0.)
    def squared_adjoint(self,h,w):
        # Circular correlation (no conjugation of the cross kernel).
        corr=np.fft.ifft(self.F[:,:,-self.k % self.n]*np.fft.fft(w),axis=-1)
        T=self.cp[:,:,None]*self.mod*corr
        out=np.einsum('i,j,ijk->k',h,h.conj(),T,optimize=True).real
        return np.maximum(out,0.)
    def unit_squared_adjoint(self,w):
        rev=-self.k % self.n
        return np.fft.ifft(self.F[np.arange(self.P),np.arange(self.P)][:,rev]*np.fft.fft(w),axis=-1).real
    def weighted_gamma(self,v,w):
        # gamma_ij = tr(U_i^H diag(w) U_j diag(v)).
        G=np.einsum('ijm,m->ji',self.cross_rows(v),w,optimize=True)
        return (G+G.conj().T)*.5
    def coherent_data_correction(self,vg,w,x):
        return sum(t*u.adjoint(w*u.apply(x)) for t,u in zip(vg,self.units))


def pbigamp(y,pilot,c,noise,pd=.5,prior=None,iterations=30,damping=.3,mode='base',ops=None):
    """Damped proper-complex vector-variance parametric AMP.
    Shifted constellation x=p+d implements SP without treating p as noisy data.
    Fixed exogenous gain prior CN(0,I/P); fitted c.gains is only initialization.
    For matched comparisons all variants share initialization/damping/schedule.
    No adaptive cost selection or truth input.
    """
    if mode not in ('base','coherent','scalar'):raise ValueError(mode)
    y=np.asarray(y,complex);p=np.asarray(pilot,complex);n=len(y);P=c.p
    if prior is None:prior=np.zeros(2*n)
    if noise<=0 or not 0<damping<=1:raise ValueError('noise/damping')
    o=Contractions(c) if ops is None else ops;a,_=alphabet(pd)
    mu,v,_=moments(prior,pd);x=p+mu;h=c.gains.copy();vh=np.full(P,1/P);tau=1/P
    xb=x.copy();hb=h.copy();s=np.zeros(n,complex);sv=np.zeros(n)
    oldbar=None;oldvp=None;trace=[]
    for it in range(iterations):
        B=o.responses(x);rowT=o.cross_rows(v);single=np.maximum(rowT[np.arange(P),np.arange(P)].real,0)
        qx=np.einsum('i,j,ijm->m',h,h.conj(),rowT,optimize=True).real
        bar=np.maximum(qx,0)+abs(B)**2@vh
        vp=bar+vh@single
        if mode=='scalar':bar=np.full(n,bar.mean());vp=np.full(n,vp.mean())
        # Fixed damping of output means and precisions; all variants same.
        if oldbar is not None:
            bar=damping*bar+(1-damping)*oldbar
            vp=damping*vp+(1-damping)*oldvp
        oldbar=bar.copy();oldvp=vp.copy()
        phat=B@h-s*bar
        sp=(y-phat)/(noise+vp);svp=1/(noise+vp)
        s=damping*sp+(1-damping)*s;sv=damping*svp+(1-damping)*sv
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=o.responses(xb)
        dx=o.squared_adjoint(hb,sv);dh=(abs(Bb)**2).T@sv
        if mode=='scalar':dx=np.full(n,dx.mean());dh=np.full(P,dh.mean())
        vr=1/np.maximum(dx,1e-12);vq=1/np.maximum(dh,1e-12)
        if mode=='coherent':
            cx=o.coherent_data_correction(vh,sv,xb)
            ch=o.weighted_gamma(v,sv)@hb
        else:
            adj=o.unit_squared_adjoint(sv)
            cx=xb*(vh@adj);ch=hb*(single@sv)
        rx=x+vr*(o.adjoint(hb,s)-cx)
        rh=h+vq*(Bb.conj().T@s-ch)
        like=-abs((rx-p)[:,None]-a)**2/vr[:,None]
        ext,app,mu,v=marginal(like,prior,pd);x=p+mu
        vh=tau*vq/(tau+vq);h=tau*rh/(tau+vq)
        if not all(np.isfinite(z).all() for z in (h,vh,mu,v,s,sv)):raise FloatingPointError('AMP nonfinite')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh.mean()),residual=float(np.mean(abs(y-o.apply(h,x))**2))))
    return dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=vh,trace=trace,iterations=iterations)

def scalar_pbigamp(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,explicit_pilot=False,gain_mode="joint"):
    """Fast scalar-variance P-BiG-AMP control for distinct-delay unitary paths.
    No P^2 N variance calculation. `explicit_pilot` applies Table-III diagonal
    correction to d, rather than to x=p+d: the representation-sensitivity control.
    Both models have the same actual forward likelihood; neither reads truth.
    """
    n=c.n;P=c.p;p=np.asarray(pilot,complex);y=np.asarray(y,complex)
    if len(set(c.delays.tolist()))!=P:raise ValueError('scalar reference assumes distinct delays')
    if prior is None:prior=np.zeros(2*n)
    a,_=alphabet(pd);mu,v,_=moments(prior,pd);x=p+mu
    h=c.gains.copy();vh=1/P if gain_mode=="joint" else 0.;tau=1/P;xb=x.copy();hb=h.copy();s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[]
    for it in range(iterations):
        B=c.regressors(x);vx=float(np.mean(v));eH=float(np.vdot(h,h).real);ex=float(np.vdot(x,x).real)
        bar=vx*eH+P*vh*ex/n;vp=bar+P*vh*vx
        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
        bar0=bar;vp0=vp
        ph=B@h-s*bar
        s=damping*(y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bbar=c.regressors(xb);cg=Channel(n,c.c1,c.c2,c.delays,c.dopplers,hb)
        vr=1/max(sv*np.vdot(hb,hb).real,1e-12);vq=1/max(sv*np.vdot(xb,xb).real,1e-12)
        cx=(xb-p if explicit_pilot else xb)*(sv*P*vh)
        rx=x+vr*(cg.adjoint(s)-cx)
        rh=h+vq*(Bbar.conj().T@s-hb*sv*n*vx)
        ext,app,mu,v=marginal(-abs((rx-p)[:,None]-a)**2/vr,prior,pd);x=p+mu
        vh=tau*vq/(tau+vq) if gain_mode=="joint" else 0.
        if gain_mode!="fixed":h=tau*rh/(tau+vq)
        if not np.isfinite(h).all():raise FloatingPointError('scalar AMP nonfinite')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh)))
    return dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations)
