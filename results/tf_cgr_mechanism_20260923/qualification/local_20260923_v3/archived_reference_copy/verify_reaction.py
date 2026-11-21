import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json,numpy as np
from pathlib import Path
from coherence_reference import Physics,receive
rng=np.random.default_rng(233004);checks=[]
for n in [17,32,64]:
 p=Physics(n,[1,3,3],[.7,.21,.26],3.7/(2*n),.017);U=p.dense()
 for _ in range(4):
  v=rng.uniform(0,.5,n);G=np.einsum('imk,jmk,k->ij',U.conj(),U,v)
  g=np.array([1,2]);err=np.max(abs(G[np.ix_(g,g)]-v.sum()*p.R[np.ix_(g,g)]))
  assert err<1e-10;checks.append(dict(test='nonuniform_diagonal_V_same_delay_Gamma',n=n,error=float(err)))
  y=rng.normal(size=n)+1j*rng.normal(size=n);pilot=np.sqrt(.5)*np.exp(1j*rng.uniform(-3,3,n))
  h=rng.normal(size=3)+1j*rng.normal(size=3);L=rng.normal(size=2*n)
  a=receive(p,y,pilot,h,.25,prior=L,iterations=1,save=True)
  b=receive(p,y,pilot,h,.25,prior=L,iterations=1,mode='reaction',save=True)
  t=a['trace'][0];qprec=max(t['alpha']*t['xbar_energy'],1e-12)
  dh=-t['alpha']*n*t['vx']/(p.p+qprec)*(p.R-np.eye(p.p))@t['hbar']
  err=np.max(abs(b['gains']-a['gains']-dh))
  assert err<1e-10;checks.append(dict(test='exact_common_state_gain_change',n=n,error=float(err)))
  # spectral counterhypothesis has identical eigenvalues/diagonal
  signs=np.array([1,1,-1]);Rs=signs[:,None]*p.R*signs[None,:]
  err=max(np.max(abs(np.diag(Rs)-np.diag(p.R))),np.max(abs(np.linalg.eigvalsh(Rs)-np.linalg.eigvalsh(p.R))))
  assert err<1e-10;checks.append(dict(test='sham_matches_spectrum_and_diagonal',n=n,error=float(err)))
# Null coherent direction: Euclidean discrepancy need not matter to the waveform.
p=Physics(32,[3,3],[.2,.2],3.7/64,.017);h=np.array([1,-1],complex)
dh=(p.R-np.eye(2))@h
checks.append(dict(test='null_coherent_direction_counterexample',euclidean_norm=float(np.linalg.norm(dh)),physical_squared_norm=float(np.vdot(dh,p.R@dh).real)))
Path(__file__).with_name('reaction_qualification.json').write_text(json.dumps(checks,indent=2))
print(len(checks),'checks; max error',max(c.get('error',0.) for c in checks))
