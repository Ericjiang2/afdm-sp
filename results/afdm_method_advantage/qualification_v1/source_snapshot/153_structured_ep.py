"""Proper-complex dual-domain EP adaptation, not verbatim real-valued EP-T.
Exact cyclic-band Gaussian mean and inverse diagonal. Domain crossing projects
covariances to their marginals; constellation/LDPC factors remain in AF domain.
"""
import numpy as np
from scipy import sparse
from scipy.linalg import cholesky_banded,cho_solve_banded,cho_factor,cho_solve
from physical import daft
from messages import alphabet,marginal

def band_inverse_diagonal(R,b):
    n=R.shape[1];Z=np.zeros((n,b+1),complex)
    for i in range(n-1,-1,-1):
        js=np.arange(i+1,min(n,i+b+1));ri=R[b,i]
        if len(js):
            p,q=np.meshgrid(js,js,indexing='ij');lo=np.minimum(p,q);hi=np.maximum(p,q)
            B=Z[lo,hi-lo];B=np.where(p<=q,B,B.conj());r=R[b+i-js,js]/ri
            z=-r@B;Z[i,js-i]=z;Z[i,0]=1/abs(ri)**2-np.dot(r,z.conj())
        else:Z[i,0]=1/abs(ri)**2
    return Z[:,0].real

class CyclicSolver:
    """Q cyclic half-band b; first b variables form an exact Schur border."""
    def __init__(self,Q,b):
        Q=sparse.csc_matrix(Q);self.n=Q.shape[0];self.b=int(b);self.dense=b>=self.n/2
        if self.dense:
            self.cf=cho_factor(Q.toarray(),lower=True);self.diag=np.diag(cho_solve(self.cf,np.eye(self.n))).real;return
        if b==0:self.diag=1/Q.diagonal().real;return
        A=Q[:b,:b].toarray();self.B=Q[:b,b:].toarray();D=Q[b:,b:].tocoo();nn=self.n-b
        if np.any(abs(D.row-D.col)>b):raise ValueError('Matrix exceeds declared cyclic bandwidth')
        ab=np.zeros((b+1,nn),complex);sel=D.row<=D.col;ab[b+D.row[sel]-D.col[sel],D.col[sel]]=D.data[sel]
        self.R=cholesky_banded(ab,lower=False,check_finite=False)
        self.W=cho_solve_banded((self.R,False),self.B.conj().T,check_finite=False)
        self.S=cho_factor(A-self.B@self.W,lower=True,check_finite=False);si=cho_solve(self.S,np.eye(b),check_finite=False)
        self.diag=np.r_[np.diag(si).real,band_inverse_diagonal(self.R,b)+np.einsum('ij,ij->i',self.W@si,self.W.conj()).real]
    def solve(self,r):
        if self.dense:return cho_solve(self.cf,r)
        if self.b==0:return self.diag*r
        b=self.b;dr=cho_solve_banded((self.R,False),r[b:],check_finite=False)
        ra=cho_solve(self.S,r[:b]-self.B@dr,check_finite=False)
        return np.r_[ra,dr-self.W@ra]

def time_matrix(c):
    n=c.n;k=np.arange(n);rr=[];cc=[];vv=[]
    for l,nu,h in zip(c.delays,c.dopplers,c.gains):
        cp=np.where(k<l,np.exp(2j*np.pi*c.c1*(n*n+2*n*(k-l))),1)
        rr.extend(k);cc.extend((k-l)%n);vv.extend(h*cp*np.exp(2j*np.pi*nu*k/n))
    return sparse.coo_matrix((vv,(rr,cc)),shape=(n,n)).tocsc()

def ep_t(ydata,c,noise,pd=.5,prior=None,iterations=8,damping=.3):
    n=c.n
    if prior is None:prior=np.zeros(2*n)
    H=time_matrix(c);Y=daft(ydata,c.c1,c.c2,True);Gram=H.conj().T@H/noise;rhs=H.conj().T@Y/noise
    lam=np.full(n,1/pd);eta=np.zeros(n,complex);events=[];b=int(c.delays.max()-c.delays.min());a,_=alphabet(pd)
    for it in range(iterations):
        solver=CyclicSolver(Gram+sparse.diags(lam),b);mean=solver.solve(rhs+eta);var=np.maximum(solver.diag,1e-12)
        prec=np.maximum(1/var-lam,1e-10);cv=1/prec;cm=cv*(mean/var-eta)
        am=daft(cm,c.c1,c.c2);av=max(float(cv.mean()),1e-12)
        ext,app,m,v=marginal(-abs(am[:,None]-a)**2/av,prior,pd)
        mt=daft(m,c.c1,c.c2,True);vt=max(float(v.mean()),1e-10)
        nl=1/vt-prec;ne=mt/vt-cm/cv;good=(nl>1e-10)&np.isfinite(nl)&np.isfinite(ne)
        lam[good]=(1-damping)*lam[good]+damping*nl[good];eta[good]=(1-damping)*eta[good]+damping*ne[good]
        events.append(dict(iteration=it,accepted_sites=int(good.sum()),bandwidth=b,dense_fallback=solver.dense))
    return dict(extrinsic=ext,app=app,mu=m,variance=v,trace=events,iterations=iterations)
