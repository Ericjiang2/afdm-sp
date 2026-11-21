"""All bit vectors use the upstream ALL-I THEN ALL-Q order. L>0 means bit zero.
Output APP and extrinsic are distinct; decoder priors are replacements.
"""
import numpy as np
from scipy.special import logsumexp

def alphabet(pd):
    a=np.sqrt(pd/2);return a*np.array([1+1j,1-1j,-1+1j,-1-1j]),np.array([[0,0],[0,1],[1,0],[1,1]])
def logprior(L,pd):
    L=np.asarray(L,float);n=len(L)//2
    if L.ndim!=1 or len(L)%2 or not np.isfinite(L).all():raise ValueError('Invalid grouped LLR vector')
    _,bits=alphabet(pd);li=np.column_stack((L[:n],L[n:]));a=.5*li@(1-2*bits).T
    return a-logsumexp(a,axis=1,keepdims=True)
def moments(L,pd):
    p=np.exp(logprior(L,pd));a,_=alphabet(pd);mu=p@a
    return mu,np.maximum(pd-abs(mu)**2,0),p@(a*a)-mu*mu

def marginal(likelihood,prior,pd):
    post=np.asarray(likelihood,float)+logprior(prior,pd);a,b=alphabet(pd)
    app=np.concatenate([logsumexp(post[:,b[:,j]==0],axis=1)-logsumexp(post[:,b[:,j]==1],axis=1) for j in (0,1)])
    p=np.exp(post-logsumexp(post,axis=1,keepdims=True));mu=p@a
    return app-prior,app,mu,np.maximum(pd-abs(mu)**2,0)

def sparse_bp(y,diags,shifts,noise,pd=.5,prior=None,weak_variance=None,iterations=20,damping=.5,weak_pseudo=None,noncircular=False):
    """Gaussian observation-factor BP, exact QPSK variable factors.
    Weak mean is already subtracted. Weak row variance is frozen for this batch.
    No silent edge threshold. Fresh factor messages for each new channel/mask.
    """
    y=np.asarray(y,complex);D=np.asarray(diags,complex);s=np.asarray(shifts,int);n=len(y);M=len(s)
    if D.shape!=(M,n) or M==0 or iterations<1:raise ValueError('Invalid graph')
    if prior is None:prior=np.zeros(2*n)
    prior=np.asarray(prior,float);lp=logprior(prior,pd);a,_=alphabet(pd)
    nv=np.broadcast_to(np.asarray(noise,float),(n,)).copy()
    if weak_variance is not None:nv+=np.asarray(weak_variance,float)
    if np.any(nv<=0):raise ValueError('Nonpositive variance')
    rows=(np.arange(n)[None,:]+s[:,None])%n
    prob=np.broadcast_to(np.exp(lp),(M,n,4)).copy();trace=[]
    for it in range(iterations):
        em=prob@a;ev=np.maximum(pd-abs(em)**2,0);tm=np.zeros(n,complex);tv=nv.copy();tc=np.zeros(n,complex) if weak_pseudo is None else np.asarray(weak_pseudo,complex).copy();ec=prob@(a*a)-em*em
        for j in range(M):
            tm[rows[j]]+=D[j]*em[j];tv[rows[j]]+=abs(D[j])**2*ev[j];tc[rows[j]]+=D[j]**2*ec[j]
        r=y[rows]-tm[rows]+D*em;vv=np.maximum(tv[rows]-abs(D)**2*ev,1e-12)
        err=r[:,:,None]-D[:,:,None]*a
        if noncircular:
            pc=tc[rows]-D**2*ec;den=np.maximum(vv*vv-abs(pc)**2,1e-18)
            msg=-(vv[:,:,None]*abs(err)**2-(pc.conj()[:,:,None]*err**2).real)/den[:,:,None]
        else:msg=-abs(err)**2/vv[:,:,None]
        msg-=msg.max(axis=-1,keepdims=True)
        lik=msg.sum(axis=0);new=lp[None,:,:]+lik[None,:,:]-msg
        new=np.exp(new-logsumexp(new,axis=-1,keepdims=True));prob=(1-damping)*prob+damping*new
        trace.append(float(np.mean(ev)))
    ext,app,mu,v=marginal(lik,prior,pd)
    return dict(extrinsic=ext,app=app,mu=mu,variance=v,trace=trace,iterations=iterations,edges=M*n)

def sp_candidate_moments(U,hm,hv,mu,v,pilot,k,a,noise):
    """Exact conditional mean/variance under independent q(h_p), q(d_j).
    Gaussianization of that distribution is a separate approximation.
    """
    mx=np.asarray(pilot)+np.asarray(mu);mx=mx.copy();mx[k]=pilot[k]+a
    vv=np.asarray(v).copy();vv[k]=0;z=U@mx;H=hm@U
    mean=hm@z;var=noise+np.sum(abs(H)**2*vv)+np.sum(hv*(abs(z)**2+abs(U)**2@vv))
    return mean,float(var)
