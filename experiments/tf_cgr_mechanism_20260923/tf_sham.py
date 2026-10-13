"""Two-FFT realization of scalar-variance parametric bilinear AMP for SP-AFDM.
No dense channel/tensor, no independent time-domain QPSK prior, no tail deletion.
The inferential approximation is scalar P-BiG-AMP (Parker/Schniter); the exact
change is a unitary observation rotation and the path-operation contractions.
"""
import numpy as np
from scipy.optimize import minimize_scalar
from physical import Channel,daft,dkernel
from messages import alphabet,marginal,moments

class TimePathOps:
    def __init__(self,c):
        self.c=c;self.n=c.n;self.P=c.p;n=c.n;k=np.arange(n)
        if n<1 or self.P<1 or np.any(c.delays<0) or np.any(c.delays>=n):raise ValueError('invalid path dimensions/delays')
        if not np.isfinite(c.dopplers).all() or not np.isfinite(c.gains).all():raise ValueError('nonfinite paths')
        self.idx=(k[:,None]-c.delays)%n
        wrap=k[:,None]-c.delays
        cp=np.where(wrap<0,np.exp(2j*np.pi*c.c1*(n*n+2*n*wrap)),1.)
        self.phase=cp*np.exp(2j*np.pi*k[:,None]*c.dopplers/n)
        self.R=(c.delays[:,None]==c.delays[None,:])*dkernel(c.dopplers[None,:]-c.dopplers[:,None],n)
    def responses_time(self,xt):return self.phase*xt[self.idx]
    def adjoint_time(self,h,z):
        q=self.phase.conj()*z[:,None]*h.conj()
        return sum(np.roll(q[:,i],-int(l)) for i,l in enumerate(self.c.delays))
    def power(self,h):
        value=float(np.vdot(h,self.R@h).real)
        if value < -1e-10*max(float(np.vdot(h,h).real),1.):raise FloatingPointError('non-PSD physical norm')
        return max(value,0.)

def scalar_joint(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,gain_mode='joint',record_states=False,observation_domain='time'):
    """Observed-only detector. Gain prior CN(0,I/P), reused once per batch.
    c.gains is initialization, never an independent observation-derived prior.
    Fixed-gain and zero-variance gain-mean-update controls are explicitly named.
    In each iteration only one IDAFT (new x) and one DAFT (adjoint) are needed;
    B(xbar) is updated by linearity, not with an extra transform.
    """
    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex);n=c.n;P=c.p
    if y.shape!=(n,) or pilot.shape!=(n,) or noise<=0 or not np.isfinite(noise):raise ValueError('observation/noise')
    if iterations<1 or not 0<damping<=1 or gain_mode not in ('joint','point','fixed') or observation_domain not in ('time','af'):raise ValueError('configuration')
    if not np.isfinite(y).all() or not np.isfinite(pilot).all():raise ValueError('nonfinite observations')
    if prior is None:prior=np.zeros(2*n)
    prior=np.asarray(prior,float)
    if prior.shape!=(2*n,) or not np.isfinite(prior).all() or pd<=0:raise ValueError('invalid code prior/data power')
    a,_=alphabet(pd);mu,v,_=moments(prior,pd);x=pilot+mu
    o=TimePathOps(c);Y=daft(y,c.c1,c.c2,True) if observation_domain=='time' else y.copy()
    signs=np.ones(P)
    for delay in np.unique(c.delays):
        group=np.flatnonzero(c.delays==delay)
        signs[group]=(-1.)**np.arange(group.size)
    gain_R=signs[:,None]*o.R*signs[None,:]
    h=c.gains.copy();vh=1/P if gain_mode=='joint' else 0.;tau=1/P
    xb=x.copy();hb=h.copy();Bb=None;s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[];states=[]
    for it in range(iterations):
        xt=daft(x,c.c1,c.c2,True);B=o.responses_time(xt);vx=float(v.mean());ex=float(np.vdot(x,x).real)
        channel_norm=o.power(h)
        bar=vx*channel_norm+P*vh*ex/n;vp=bar+P*vh*vx
        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
        bar0=bar;vp0=vp
        z=B@h
        if observation_domain=='af':z=daft(z,c.c1,c.c2)
        ph=z-s*bar
        s=damping*(Y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
        st=s if observation_domain=='time' else daft(s,c.c1,c.c2,True)
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=B.copy() if Bb is None else damping*B+(1-damping)*Bb
        data_precision=sv*o.power(hb);gain_precision=sv*np.vdot(xb,xb).real
        vr=1/max(data_precision,1e-12);vq=1/max(gain_precision,1e-12)
        adj=daft(o.adjoint_time(hb,st),c.c1,c.c2)
        rx=x+vr*(adj-xb*(sv*P*vh))
        h_pre=h.copy(); rh=h+vq*(Bb.conj().T@st-(gain_R@hb)*sv*n*vx)
        ext,app,mu,v=marginal(-abs((rx-pilot)[:,None]-a)**2/vr,prior,pd);x=pilot+mu
        vh=tau*vq/(tau+vq) if gain_mode=='joint' else 0.
        if gain_mode!='fixed':h=tau*rh/(tau+vq)
        if not all(np.isfinite(q).all() for q in (h,mu,v,s)):raise FloatingPointError('nonfinite scalar joint update')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh),
                          channel_norm_factor=float(channel_norm),pseudo_variance_bar=float(bar),
                          pseudo_variance_total=float(vp),data_pseudo_variance=float(vr),
                          gain_pseudo_variance=float(vq),output_precision=float(sv),
                          data_precision_floor=bool(data_precision<=1e-12),
                          gain_precision_floor=bool(gain_precision<=1e-12),
                          fft_count=2 if observation_domain=='time' else 4))
        if record_states:states.append(dict(h_pre=h_pre,h=h.copy(),hbar=hb.copy(),x=x.copy(),xbar=xb.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),rx=rx.copy(),app=app.copy(),extrinsic=ext.copy(),vx=vx,vr=vr,vq=vq,vh=vh,alpha=sv,sv=sv,bar=bar,vp=vp,xbar_energy=float(np.vdot(xb,xb).real),gain_R=gain_R.copy(),physical_R=o.R.copy()))
    out=dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations,fft_count=2*iterations+1 if observation_domain=='time' else 4*iterations)
    if record_states:out['states']=states
    return out

def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
    """Same frozen-q variable-projection objective, evaluated entirely in time.
    Two fixed transforms per call. All candidate gains/Dopplers remain nonoracle.
    """
    n=len(y);ls=np.asarray(ls,int);ks=np.asarray(ks,float);gs=np.asarray(gs,complex)
    unique=np.unique(ls);energy=np.array([np.sum(abs(gs[ls==d])**2) for d in unique]);l=unique[np.argsort(-energy)[:max_paths]]
    centers=np.array([ks[np.flatnonzero(ls==d)[np.argmax(abs(gs[ls==d]))]] for d in l]);nu=centers.copy();k=np.arange(n)
    xt=daft(np.asarray(pilot)+mu,c1,c2,True);Y=daft(y,c1,c2,True);wrap=k[:,None]-l
    base=xt[wrap%n]*np.where(wrap<0,np.exp(2j*np.pi*c1*(n*n+2*n*wrap)),1.)
    if mode not in ('mean','scalar','soft'):raise ValueError('mode')
    vv=np.zeros(n) if mode=='mean' else np.full(n,np.mean(v)) if mode=='scalar' else np.asarray(v)
    dl=l[None,:]-l[:,None];gv=np.exp(2j*np.pi*c1*(l[:,None]**2-l[None,:]**2))*np.fft.fft(vv)[dl%n];calls=0
    def ev(nu):
        nonlocal calls
        calls+=1;B=base*np.exp(2j*np.pi*k[:,None]*nu/n)
        G=gv*dkernel(nu[None,:]-nu[:,None]+2*n*c1*dl,n);G=(G+G.conj().T)*.5
        Q=B.conj().T@B+G+noise*np.eye(len(l));b=B.conj().T@Y;h=np.linalg.solve(Q,b)
        return float((np.vdot(Y,Y)-np.vdot(b,h)).real),h,G
    val,h,G=ev(nu);history=[val]
    for _ in range(rounds):
        for j,z in enumerate(centers):
            lo=max(-3.,z-.75);hi=min(3.,z+.75)
            def f(z):
                t=nu.copy();t[j]=z;return ev(t)[0]
            opt=minimize_scalar(f,bounds=(lo,hi),method='bounded',options={'xatol':.002,'maxiter':16})
            if opt.fun<val:nu[j]=opt.x;val,h,G=ev(nu);history.append(val)
    val,h,G=ev(nu)
    return Channel(n,c1,c2,l,nu,h),dict(history=history,objective=val,gamma=G,evaluations=calls,fft_count=3)
