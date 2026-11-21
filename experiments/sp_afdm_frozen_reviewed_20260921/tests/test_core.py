import sys,json,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from physical import Channel,daft,sparse_apply
from messages import *
rng=np.random.default_rng(20260920123);checks=[]
def check(name,x,y,tol=2e-9):
 e=float(np.max(abs(np.asarray(x)-np.asarray(y))));assert e<tol,(name,e);checks.append(dict(name=name,error=e,tol=tol))
def dense(n,c1,c2,l,nu):
 k=np.arange(n);F=np.exp(-2j*np.pi*k[:,None]*k/n)/np.sqrt(n);A=np.exp(2j*np.pi*c2*k*k)[:,None]*F*np.exp(2j*np.pi*c1*k*k)[None,:];T=np.zeros((n,n),complex)
 for t in range(n):T[t,(t-l)%n]=np.exp(2j*np.pi*nu*t/n)*(np.exp(2j*np.pi*c1*(n*n+2*n*(t-l))) if t<l else 1)
 return A@T@A.conj().T
for n in (7,12,32,65):
 for rep in range(3):
  l=rng.integers(0,min(5,n),3);nu=rng.uniform(-1.4,1.4,3);h=(rng.normal(size=3)+1j*rng.normal(size=3))/np.sqrt(6);c1=(3 if rep<2 else 2.31)/(2*n);c2=.73/n**2
  c=Channel(n,c1,c2,l,nu,h);U=np.array([dense(n,c1,c2,li,ni) for li,ni in zip(l,nu)]);H=np.einsum('p,pnk->nk',h,U);v=rng.random(n);x=rng.normal(size=n)+1j*rng.normal(size=n)
  sh=np.array([0,2,5]);D=c.diagonals(sh);G=np.zeros_like(H)
  for s,d in zip(sh,D):G[(np.arange(n)+s)%n,np.arange(n)]=d
  check('apply',c.apply(x),H@x);check('adjoint',c.adjoint(x),H.conj().T@x)
  ga=np.einsum('pnk,qnk,k->pq',U.conj(),U,v);check('Gamma',c.gamma(v),ga)
  check('sparse',sparse_apply(D,sh,x),G@x)
  check('energies',c.energies(v),[np.sum(abs(H[(np.arange(n)+s)%n,np.arange(n)])**2*v) for s in range(n)])
  check('weak_row_variance',c.row_variance(v,sh),abs(H-G)**2@v);
  pseudo=.4*v*np.exp(1j*np.arange(n));check('weak_pseudovariance',c.row_pseudovariance(pseudo,sh),(H-G)**2@pseudo); check('trace_link',c.energies(v).sum(),np.vdot(h,ga@h).real)
  ep=1e-6;cp=Channel(n,c1,c2,l,nu+ep,h);cm=Channel(n,c1,c2,l,nu-ep,h)
  check('regressor_derivative',c.regressors(x,True),(cp.regressors(x)-cm.regressors(x))/(2*ep),2e-7)
  mu=.3*(rng.normal(size=n)+1j*rng.normal(size=n));p=.1*np.ones(n)
  check('SIC_equivalence',H@(p+x)-(H@(p+mu)+G@(x-mu)),(H-G)@(x-mu))
# Conditioned symbol uncertainty with random proper gains, integrated exactly.
U=rng.normal(size=(2,3))+1j*rng.normal(size=(2,3));hm=np.array([.7+.2j,-.2+.4j]);hv=np.array([.3,.1]);p=np.array([.3+.1j,.2-.4j,.1]);a,_=alphabet(.7)
L=np.array([.3,-.4,1.2,-.3,.6,1.1]);mu,v,_=moments(L,.7);pr=np.exp(logprior(L,.7));vars=[]
for cand in a:
 av=[];weights=[];second=[]
 for i,j in itertools.product(range(4),repeat=2):
  d=np.array([a[i],cand,a[j]]);z=U@(p+d);m=hm@z;av.append(m);weights.append(pr[0,i]*pr[2,j]);second.append(abs(m)**2+np.sum(hv*abs(z)**2))
 m=np.dot(weights,av);v0=np.dot(weights,second)-abs(m)**2+.12;m1,v1=sp_candidate_moments(U,hm,hv,mu,v,p,1,cand,.12)
 check('SP_conditional_mean',m1,m);check('SP_conditional_var',v1,v0);vars.append(v1)
assert np.ptp(vars)>.1
# Own-bit prior removal is invariant; the other bit remains in coupled marginalization.
lik=np.array([[0.,-.5,-2.,-.1]]);pr=np.array([.4,1.1]);e,*_=marginal(lik,pr,1);p2=pr.copy();p2[0]+=2;e2,*_=marginal(lik,p2,1);check('extrinsic_own_bit',e[0],e2[0])
p2=pr.copy();p2[1]+=2;e2,*_=marginal(lik,p2,1);assert abs(e[0]-e2[0])>.01
# Flat diagonal channel scalar test, exact QPSK likelihood.
n=8;D=(.8+.1j)*np.ones((1,n));y=rng.normal(size=n)+1j*rng.normal(size=n);prior=rng.normal(size=2*n);a,_=alphabet(1)
out=sparse_bp(y,D,[0],.4,1,prior,iterations=2);e,*_=marginal(-abs(y[:,None]-D[0,:,None]*a)**2/.4,prior,1);check('BP_scalar',out['extrinsic'],e)
# Equal-cost mask optimum; degeneracies.
c=Channel(12,3/24,.73/144,[0,1],[.4,-.3],[.7,.3j]);v=np.linspace(.01,.8,12);keep,E,tail,_=c.select(v,3)
assert all(tail<=E.sum()-E[list(s)].sum()+1e-10 for s in itertools.combinations(range(12),3));check('zero_var',c.energies(np.zeros(12)),np.zeros(12))
one=Channel(12,3/24,.73/144,[1],[.4],[.7j]);check('onepath_rank',one.energies(v)/v.sum(),one.energies(np.ones(12))/12)
# Covariance cross-term and real/imag variance transformation counterexamples.
H=np.array([[1.,1.],[1.,-1.]]);G=np.diag(np.diag(H));assert np.linalg.norm(G@(H-G).T)>0
A=1j*np.eye(2);vr=np.array([.1,.2]);vi=np.array([.8,.9]);check('real_variance_rotate',(A.real**2)@vr+(A.imag**2)@vi,vi)
check('variance_not_precision',4*2/(4+.5),1.7777777777777777)
path=Path(__file__).resolve().parents[1]/'results'/'core_tests.json';path.write_text(json.dumps(dict(checks=checks,count=len(checks),sp_candidate_variances=vars),indent=2));print('PASS',len(checks),'checks; max error',max(z['error'] for z in checks),'SP variances',vars)
