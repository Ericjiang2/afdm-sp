"""Reference coherence-complete gain blocks; positive-chirp CPP, all-I/all-Q bits.
An approximate receiver, not an exact posterior or a claimed new AMP family.
Only NumPy and SciPy are needed. No production files imported.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.linalg import cho_factor, cho_solve

@dataclass
class Physics:
    n: int
    delays: np.ndarray
    dopplers: np.ndarray
    c1: float
    c2: float
    def __post_init__(self):
        self.delays=np.asarray(self.delays,dtype=int);self.dopplers=np.asarray(self.dopplers,float)
        if self.delays.shape!=self.dopplers.shape or np.any(self.delays<0) or np.any(self.delays>=self.n):
            raise ValueError('Invalid paths')
        self.p=len(self.delays);k=np.arange(self.n);self.k=k
        self.l1=np.exp(2j*np.pi*self.c1*k*k);self.l2=np.exp(2j*np.pi*self.c2*k*k)
        wrap=k[:,None]-self.delays
        self.idx=wrap%self.n
        cp=np.where(wrap<0,np.exp(2j*np.pi*self.c1*(self.n**2+2*self.n*wrap)),1.)
        self.phase=cp*np.exp(2j*np.pi*k[:,None]*self.dopplers/self.n)
        self.groups=[np.flatnonzero(self.delays==l) for l in np.unique(self.delays)]
        self.R=np.zeros((self.p,self.p),complex)
        for g in self.groups:
            self.R[np.ix_(g,g)]=self.phase[:,g].conj().T@self.phase[:,g]/self.n
    def daft(self,x,inverse=False):
        if inverse:return self.l1.conj()*np.fft.ifft(self.l2.conj()*x)*np.sqrt(self.n)
        return self.l2*np.fft.fft(self.l1*x)/np.sqrt(self.n)
    def response_t(self,xt):return self.phase*xt[self.idx]
    def adj_t(self,h,z):
        a=self.phase.conj()*z[:,None]*h.conj()
        return sum(np.roll(a[:,i],-int(l)) for i,l in enumerate(self.delays))
    def apply(self,h,x):return self.daft(self.response_t(self.daft(x,True))@h)
    def dense(self):
        eye=np.eye(self.n,dtype=complex)
        return np.stack([np.column_stack([self.apply(np.eye(self.p)[j],eye[:,k]) for k in range(self.n)]) for j in range(self.p)])


def moments(prior,pd=.5):
    n=len(prior)//2;a=np.sqrt(pd/2)
    mu=a*(np.tanh(prior[:n]/2)+1j*np.tanh(prior[n:]/2))
    return mu,np.maximum(pd-abs(mu)**2,0)

def receive(phys:Physics,y,pilot,h0,noise,prior=None,iterations=20,damping=.3,
            mode='scalar',prior_cov=None,save=False):
    """Modes: scalar frozen-TF equations; reaction restores R only;
    group block by exact delay; full dense P-dimensional Gaussian block.
    Default Cg=I/P. Different prior_cov allowed only in group/full modes.
    """
    if mode not in ('scalar','reaction','group','full','gram','sham'):raise ValueError('mode')
    n=phys.n;p=phys.p
    prior=np.zeros(2*n) if prior is None else np.asarray(prior,float)
    if noise<=0 or iterations<1 or prior.shape!=(2*n,):raise ValueError('configuration')
    Cg=np.eye(p)/p if prior_cov is None else np.asarray(prior_cov,complex)
    if mode in ('scalar','reaction','sham') and prior_cov is not None:raise ValueError('scalar supports native prior only')
    groups=phys.groups if mode in ('group','gram') else [np.arange(p)]
    isblock=mode in ('group','full','gram')
    Sinvs=[np.linalg.inv(Cg[np.ix_(g,g)]) for g in groups] if isblock else []
    S=Cg.copy();vh=1/p;h=np.asarray(h0,complex).copy()
    mu,v=moments(prior);x=pilot+mu;xb=x.copy();hb=h.copy();Bb=None;xbt=None
    Y=phys.daft(y,True);s=np.zeros(n,complex);alpha=0.;bar_old=None;vp_old=None;trace=[]
    for t in range(iterations):
        xt=phys.daft(x,True);B=phys.response_t(xt);vx=float(v.mean())
        power=float(np.vdot(h,phys.R@h).real)
        if isblock:
            # B^H B trace and uncertainty action. General full is O(N P^2).
            uncertainty=float(np.einsum('ni,ij,nj->',B,S,B.conj()).real/n)
            Cpower=float(np.trace(phys.R@S).real)
        else:
            uncertainty=p*vh*float(np.vdot(x,x).real)/n;Cpower=p*vh
        bar=vx*power+uncertainty;vp=bar+vx*Cpower
        if bar_old is not None:
            bar=damping*bar+(1-damping)*bar_old;vp=damping*vp+(1-damping)*vp_old
        bar_old=bar;vp_old=vp
        z=B@h;ph=z-s*bar
        s=damping*(Y-ph)/(noise+vp)+(1-damping)*s
        alpha=damping/(noise+vp)+(1-damping)*alpha
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=B.copy() if Bb is None else damping*B+(1-damping)*Bb
        xbt=xt.copy() if xbt is None else damping*xt+(1-damping)*xbt
        rprec=max(alpha*float(np.vdot(hb,phys.R@hb).real),1e-12)
        adj_t=phys.adj_t(hb,s)
        if mode in ('group','gram'):
            weight=np.zeros(n)
            for g in groups:
                phg=phys.phase[:,g];wg=np.sum((phg@S[np.ix_(g,g)])*phg.conj(),axis=1).real
                weight+=np.roll(wg,-int(phys.delays[g[0]]))
            rx=x+phys.daft(adj_t-alpha*weight*xbt)/rprec
        elif mode=='full':
            BS=Bb@S
            corr=sum(np.roll(phys.phase[:,j].conj()*BS[:,j],-int(l)) for j,l in enumerate(phys.delays))
            rx=x+phys.daft(adj_t-alpha*corr)/rprec
        else:
            rx=x+(phys.daft(adj_t)-alpha*p*vh*xb)/rprec
        if isblock:
            hn=np.zeros(p,complex);Sn=np.zeros((p,p),complex)
            for g,Cinv in zip(groups,Sinvs):
                Rg=phys.R[np.ix_(g,g)]
                D=alpha*((float(np.vdot(xb,xb).real)*Rg) if mode=='gram' else (Bb[:,g].conj().T@Bb[:,g]))
                info=D@h[g]+Bb[:,g].conj().T@s-alpha*n*vx*(Rg@hb[g])
                cf=cho_factor(Cinv+D,lower=True,check_finite=False)
                hn[g]=cho_solve(cf,info,check_finite=False)
                Sn[np.ix_(g,g)]=cho_solve(cf,np.eye(len(g)),check_finite=False)
        else:
            qprec=max(alpha*float(np.vdot(xb,xb).real),1e-12)
            react=phys.R@hb if mode=='reaction' else hb
            if mode=='sham':
                signs=np.ones(p)
                for group in phys.groups: signs[group]=(-1.)**np.arange(len(group))
                react=signs*(phys.R@(signs*hb))
            hn=(qprec*h+Bb.conj().T@s-alpha*n*vx*react)/(p+qprec)
            vhn=1/(p+qprec)
        a=.5
        ext=4*a*rprec*np.concatenate([(rx-pilot).real,(rx-pilot).imag])
        app=ext+prior;mu,v=moments(app);x=pilot+mu
        if save:
            trace.append(dict(h_pre=h.copy(),hbar=hb.copy(),h_post=hn.copy(),vx=vx,alpha=alpha,
                xbar_energy=float(np.vdot(xb,xb).real),mu=mu.copy(),s=s.copy(),
                rx=rx.copy(),rprec=rprec,bar=bar,vp=vp,
                predicted_mean=z.copy(),S_pre=S.copy() if isblock else np.eye(p)*vh))
        h=hn
        if isblock:S=Sn
        else:vh=vhn
        if not np.isfinite(h).all() or not np.isfinite(mu).all():raise FloatingPointError('Nonfinite receiver state')
    return dict(gains=h,mu=mu,variance=v,extrinsic=ext,app=app,
                gain_covariance=S if isblock else np.eye(p)*vh,trace=trace)


def soft_refit(phys,y,pilot,mu,var,noise):
    """Exact frozen diagonal AF moments; independent dense Gamma (toy only)."""
    B=phys.response_t(phys.daft(pilot+mu,True));Y=phys.daft(y,True)
    U=phys.dense()
    Gamma=np.einsum('imk,jmk,k->ij',U.conj(),U,var)
    return np.linalg.solve(B.conj().T@B+Gamma+noise*np.eye(phys.p),B.conj().T@Y)

class ToyCode:
    """Systematic (2K,K) sparse-check toy, not the production LDPC."""
    def __init__(self,k,seed=884):
        self.k=k;self.n=2*k;rng=np.random.default_rng(seed)
        A=np.zeros((k,k),np.int8)
        for i in range(k):A[i,rng.choice(k,min(5,k),replace=False)]=1
        self.H=np.column_stack((A,np.eye(k,dtype=np.int8)));self.G=np.row_stack((np.eye(k,dtype=np.int8),A))
        self.edges=[np.flatnonzero(row) for row in self.H];self.e=np.concatenate(self.edges)
        self.shape=(k,len(self.edges[0]));self.e2=self.e.reshape(self.shape)
    def encode(self,m):return (self.G@np.asarray(m,np.int8))%2
    def decode(self,L,cap=50):
        L=np.clip(L,-20,20);q=L[self.e2].copy();r=np.zeros_like(q);app=L.copy()
        for it in range(cap):
            t=np.tanh(np.clip(q,-30,30)/2)
            for j in range(t.shape[1]):
                product=np.prod(np.delete(t,j,axis=1),axis=1)
                r[:,j]=2*np.arctanh(np.clip(product,-1+1e-12,1-1e-12))
            app=L+np.bincount(self.e,weights=r.ravel(),minlength=self.n)
            hard=(app<0).astype(np.int8)
            if not np.any((self.H@hard)%2):break
            q=app[self.e2]-r
        return dict(hard=hard,app=app,extrinsic=app-L,sweeps=it+1)
