import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys,json
from pathlib import Path
import numpy as np
from coherence_reference import Physics,receive,moments
root=Path(__file__).resolve().parent/'frozen_reference'
sys.path[:0]=[str(root/'baseline/src'),str(root/'native/src')]
from physical import Channel
from twofft import scalar_joint
from block_bilinear import block_amp
rng=np.random.default_rng(233001);checks=[]
for n in [17,32,64]:
 for ls in ([1,3,7],[3,3,3],[1,3,3]):
  nus=np.array([.2,.23,1.1]);phys=Physics(n,np.array(ls),nus,3.7/(2*n),.017)
  h=(rng.normal(size=3)+1j*rng.normal(size=3))/3
  y=rng.normal(size=n)+1j*rng.normal(size=n);p=np.sqrt(.5)*np.exp(1j*rng.uniform(0,6.28,n));L=rng.normal(size=2*n)
  c=Channel(n,phys.c1,phys.c2,ls,nus,h)
  ref=scalar_joint(y,p,c,.25,prior=L,record_states=True)
  own=receive(phys,y,p,h,.25,prior=L,save=True)
  err=max(np.max(abs(ref[q]-own[q])) for q in ['extrinsic','app','gains','mu'])
  assert err<1e-9,(n,ls,err)
  checks.append(dict(check='archived_scalar',n=n,delays=ls,error=float(err)))
  full=receive(phys,y,p,h,.25,prior=L,mode='full',save=True)
  refb=block_amp(y,p,c,.25,prior=L)
  err=max(np.max(abs(refb[q]-full[q])) for q in ['extrinsic','app','gains','mu'])
  assert err<1e-8,(n,ls,err)
  checks.append(dict(check='archived_full_block',n=n,delays=ls,error=float(err)))
  if len(set(ls))==len(ls):
   group=receive(phys,y,p,h,.25,prior=L,mode='group',save=True)
   err=max(np.max(abs(group[q]-own[q])) for q in ['extrinsic','app','gains','mu'])
   assert err<1e-8,err
   checks.append(dict(check='distinct_delay_reduction',n=n,error=float(err)))
  if len(set(ls))==1:
   group=receive(phys,y,p,h,.25,prior=L,mode='group',save=True)
   err=max(np.max(abs(group[q]-full[q])) for q in ['extrinsic','app','gains','mu'])
   assert err<1e-8,err
   checks.append(dict(check='single_delay_full_block',n=n,error=float(err)))
  dense=phys.dense()
  R=np.einsum('imk,jmk->ij',dense.conj(),dense)/n
  err=np.max(abs(R-phys.R));assert err<1e-10
  checks.append(dict(check='physical_Gram',n=n,error=float(err)))
# Duplicate/merge: same prior over the observable channel, not resetting 1/P.
for n in [32,64,128]:
 a=Physics(n,[3,3,11],[.3,.3,-.8],3.7/(2*n),.017)
 b=Physics(n,[3,11],[.3,-.8],a.c1,a.c2)
 h=(rng.normal(size=3)+1j*rng.normal(size=3))/3
 hm=np.array([h[0]+h[1],h[2]])
 Cg=np.diag([.2,.4,.35]);Cm=np.diag([.6,.35])
 p=np.sqrt(.5)*np.exp(1j*rng.uniform(0,6.28,n));y=rng.normal(size=n)+1j*rng.normal(size=n);L=rng.normal(size=2*n)
 x=receive(a,y,p,h,.25,L,mode='group',prior_cov=Cg,save=True)
 z=receive(b,y,p,hm,.25,L,mode='group',prior_cov=Cm,save=True)
 err=max(np.max(abs(x[q]-z[q])) for q in ['extrinsic','app','mu'])
 hmend=np.array([x['gains'][0]+x['gains'][1],x['gains'][2]])
 err=max(err,np.max(abs(hmend-z['gains'])))
 assert err<1e-8,err
 checks.append(dict(check='duplicate_merge_physical_invariance',n=n,error=float(err)))
# reaction identity difference and analytic known-waveform Gaussian doublet
pairs=[]
for delta in [0,.01,.05,.125,.5,1.]:
 n=1024;k=np.arange(n);corr=np.mean(np.exp(2j*np.pi*k*delta/n));R=np.array([[1,corr],[corr.conjugate(),1]])
 h=np.array([1,corr.conjugate()])/np.sqrt(2)
 ratio=np.linalg.norm((R-np.eye(2))@h)/np.linalg.norm(h)
 pairs.append(dict(delta=delta,abs_R12=abs(corr),reaction_relative_defect=float(ratio)))
Path(__file__).with_name('qualification.json').write_text(json.dumps(dict(checks=checks,pairs=pairs),indent=2))
print(len(checks),'passed; max',max(x['error'] for x in checks))
print(pairs)
