"""Exploratory joint Gaussian tangent EP. Exact Gaussian solve of a declared
first-order surrogate, not an exact bilinear posterior. Exogenous gain prior is
used once in each recomputed surrogate, never a reused CE posterior as a prior.
"""
import numpy as np
from scipy import sparse
from scipy.linalg import cho_factor, cho_solve
from physical import Channel, daft
from structured_ep import CyclicSolver,time_matrix
from messages import alphabet,marginal


def joint_gaussian(H,B,z,noise,lam,eta,tau):
    n=H.shape[1];p=B.shape[1]
    Gram=H.conj().T@H/noise+sparse.diags(lam)
    coo=Gram.tocoo();delta=(coo.row-coo.col)%n;b=int(np.minimum(delta,n-delta).max(initial=0))
    sol=CyclicSolver(Gram,b)
    C=H.conj().T@B/noise
    W=sol.solve(C) if b else sol.diag[:,None]*C
    u=sol.solve(H.conj().T@z/noise+eta)
    D=np.eye(p)/tau+B.conj().T@B/noise
    S=D-C.conj().T@W;S=(S+S.conj().T)/2
    cf=cho_factor(S,lower=True);Cg=cho_solve(cf,np.eye(p))
    mg=cho_solve(cf,B.conj().T@z/noise-C.conj().T@u)
    mx=u-W@mg;Cxdiag=sol.diag+np.einsum('ij,ij->i',W@Cg,W.conj()).real
    return mx,Cxdiag,mg,Cg,W,sol


def ep_joint(y,pilot,c,noise,pd=.5,prior=None,iterations=4,damping=.3,center_damping=.5):
    n=c.n;P=c.p;tau=1/P
    if prior is None:prior=np.zeros(2*n)
    ytd=daft(y,c.c1,c.c2,True);ptd=daft(pilot,c.c1,c.c2,True)
    lam=np.full(n,1/pd);eta=np.zeros(n,complex);x0=daft(marginal(np.zeros((n,4)),prior,pd)[2],c.c1,c.c2,True);g0=c.gains.copy()
    a,_=alphabet(pd);trace=[]
    for it in range(iterations):
        cc=Channel(n,c.c1,c.c2,c.delays,c.dopplers,g0)
        H=time_matrix(cc)
        B=np.column_stack([time_matrix(Channel(n,c.c1,c.c2,[l],[nu],[1.]))@(ptd+x0) for l,nu in zip(c.delays,c.dopplers)])
        z=ytd+H@x0
        mean,var,mg,Cg,W,_=joint_gaussian(H,B,z,noise,lam,eta,tau)
        var=np.maximum(var,1e-12)
        prec=np.maximum(1/var-lam,1e-10);cv=1/prec;cm=cv*(mean/var-eta)
        am=daft(cm,c.c1,c.c2);av=max(float(cv.mean()),1e-12)
        ext,app,m,v=marginal(-abs(am[:,None]-a)**2/av,prior,pd)
        mt=daft(m,c.c1,c.c2,True);vt=max(float(v.mean()),1e-10)
        nl=1/vt-prec;ne=mt/vt-cm/cv;good=(nl>1e-10)&np.isfinite(nl)&np.isfinite(ne)
        lam[good]=(1-damping)*lam[good]+damping*nl[good];eta[good]=(1-damping)*eta[good]+damping*ne[good]
        # Frozen local linearization within this batch; no same-observation prior addition.
        trace.append(dict(iteration=it,meanvar=float(v.mean()),gainvar=float(np.trace(Cg).real),normgain=float(np.linalg.norm(g0)),cov_correction=float(np.mean(np.einsum('ij,ij->i',W@Cg,W.conj()).real))))
    return dict(extrinsic=ext,app=app,mu=m,variance=v,gains=mg,gain_covariance=Cg,trace=trace)
