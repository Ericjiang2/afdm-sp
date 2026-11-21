from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from scipy import sparse
from structured_ep import CyclicSolver,time_matrix,ep_t
from physical import Channel,daft
from offgrid import gaussian_posterior,gamp,estimate
from messages import marginal,alphabet
rng=np.random.default_rng(20260920999);records=[]
def ck(name,a,b,tol):
 e=float(np.max(abs(a-b)));assert e<tol,(name,e);records.append(dict(name=name,error=e,tol=tol))
for n in (16,35,64):
 for b in (1,3,5):
  H=np.zeros((n,n),complex)
  for l in range(b+1):H[np.arange(n),(np.arange(n)-l)%n]=rng.normal(size=n)+1j*rng.normal(size=n)
  Q=H.conj().T@H+.3*np.eye(n);r=rng.normal(size=n)+1j*rng.normal(size=n);s=CyclicSolver(sparse.csc_matrix(Q),b)
  ck('cyclic_inverse_diag',s.diag,np.linalg.inv(Q).diagonal().real,1e-10);ck('cyclic_solve',s.solve(r),np.linalg.solve(Q,r),1e-10)
c=Channel(32,3/64,.1/1024,[0,3],[.4,-.2],[.8,.2j]);x=rng.normal(size=32)+1j*rng.normal(size=32)
ck('TD_AF_operator',c.apply(x),daft(time_matrix(c)@daft(x,c.c1,c.c2,True),c.c1,c.c2),1e-10)
# Gaussian GAMP mean fixed point test; its variance is not exact for arbitrary A.
A=np.diag(np.linspace(.3,1.5,12)).astype(complex);y=rng.normal(size=12)+1j*rng.normal(size=12);delta=np.linspace(.2,2,12)
m,V=gaussian_posterior(A,y,.2,delta);mg,vg,tr=gamp(A,y,.2,delta,iterations=500,damping=.5)
ck('Gaussian_GAMP_mean',mg,m,1e-8)
variance_gap=float(np.max(abs(vg-V.diagonal().real)))
assert np.all(vg>0) and variance_gap>.01
# Exact scalar prior-times-pseudo-observation denoiser (distinct from GAMP fixed-point variance).
ck('Gaussian_scalar_denoiser',delta*y/(delta+.2),np.linalg.solve(np.diag(1/delta)+np.eye(12)/.2,y/.2),1e-12)
# No sparse/off-grid inference oracle: noiseless matched identity EP scalar.
c=Channel(16,3/32,.1/256,[0],[0],[1.]);y=rng.normal(size=16)+1j*rng.normal(size=16);prior=rng.normal(size=32)
out=ep_t(y,c,.4,1,prior=prior,iterations=1);a,_=alphabet(1);ext,*_=marginal(-abs(y[:,None]-a)**2/.4,prior,1)
ck('EP_scalar_LLR',out['extrinsic'],ext,1e-9)
# Grid-update acceptance under a frozen posterior, not FER claim.
y=c.apply(x[:16]);ec,detail=estimate(y,x[:16],c.c1,c.c2,.1,[0,1],[.2,-.3],backend='exact',outer=2,active_cap=2)
assert all(r['grid_loss_after']<=r['grid_loss_before']+1e-8 for r in detail['history'])
Path(__file__).resolve().parents[1].joinpath('results/baseline_tests.json').write_text(json.dumps(dict(checks=records,grid_history=detail['history'],gamp_variance_counterexample=variance_gap),indent=2));print('PASS',len(records),'baseline checks')
