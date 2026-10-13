import numpy as np
from noncircular_siso import siso
rng=np.random.default_rng(121)
for n in (2,7,16):
 A=(rng.normal(size=(n,n))+1j*rng.normal(size=(n,n)))/np.sqrt(2*n)
 y=rng.normal(size=n)+1j*rng.normal(size=n);p=rng.normal(size=n)*.1;noise=.2;pd=.5
 # Circular moments: proper and augmented messages coincide.
 L=np.r_[np.ones(n)*.7,np.ones(n)*.7]
 c=siso(y,p,A,noise,L,pd,'proper');w=siso(y,p,A,noise,L,pd,'augmented')
 np.testing.assert_allclose(c['extrinsic'],w['extrinsic'],rtol=2e-11,atol=2e-11)
 # Direct precision-form Gaussian posterior cross-check.
 L=rng.uniform(-4,4,2*n);a=np.sqrt(pd/2);m=a*np.tanh(L/2);v=a*a/np.cosh(L/2)**2
 B=np.block([[A.real,-A.imag],[A.imag,A.real]])
 cov=np.linalg.inv(np.diag(1/v)+2/noise*B.T@B)
 residual=y-A@p;post=cov@(m/v+2/noise*B.T@np.r_[residual.real,residual.imag])
 ref=siso(y,p,A,noise,L,pd,'augmented')
 np.testing.assert_allclose(ref['posterior_mean'],post,rtol=1e-10,atol=1e-10)
 np.testing.assert_allclose(ref['posterior_variance'],np.diag(cov),rtol=1e-10,atol=1e-10)
 np.testing.assert_allclose(ref['extrinsic'],2*a*(post/np.diag(cov)-m/v),rtol=1e-10,atol=1e-10)
 # Diagonal identity likelihood: prior division must recover exact channel LLR.
 for mode in ('proper','augmented'):
  out=siso(y,p,np.eye(n),noise,L,pd,mode)
  np.testing.assert_allclose(out['extrinsic'],4*a/noise*np.r_[(y-p).real,(y-p).imag],rtol=1e-10,atol=1e-10)
print('PASS 3 sizes: circular parity, precision posterior, prior division exact identity likelihood; zero full receivers')
for magnitude in (0,10,20):
 n=8;prior=np.r_[np.full(n,magnitude),np.full(n,-magnitude)]
 y=rng.normal(size=n)+1j*rng.normal(size=n);p=np.zeros(n);noise=.2;pd=.5;a=np.sqrt(pd/2)
 for mode in ('proper','augmented'):
  out=siso(y,p,np.eye(n),noise,prior,pd,mode)
  np.testing.assert_allclose(out['extrinsic'],4*a/noise*np.r_[y.real,y.imag],rtol=2e-7,atol=2e-7)
print('PASS clipped-prior extremes 0/10/20, both representations')
