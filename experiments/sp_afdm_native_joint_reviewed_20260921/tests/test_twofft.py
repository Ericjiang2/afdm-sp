import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'));sys.path[:0]=[str(R/'src'),str(O/'src')]
import numpy as np
from physical import Channel,daft,refine
from twofft import scalar_joint,TimePathOps,time_refine
from fast_bilinear import scalar_pbigamp
from messages import alphabet,marginal,moments

def dense(y,p,U,h,noise,prior,iters=8,beta=.3):
 n=len(y);P=len(h);pd=.5;a,_=alphabet(pd);mu,v,_=moments(prior,pd);x=p+mu;vh=1/P;tau=1/P;xb=x.copy();hb=h.copy();s=np.zeros(n,complex);sv=0;bar0=None;vp0=None;trace=[]
 for it in range(iters):
  B=np.einsum('imk,k->mi',U,x);H=np.einsum('i,imk->mk',h,U);vx=float(v.mean())
  bar=vx*np.linalg.norm(H)**2/n+vh*np.linalg.norm(B)**2/n;vp=bar+vh*vx*np.linalg.norm(U)**2/n
  if bar0 is not None:bar=beta*bar+(1-beta)*bar0;vp=beta*vp+(1-beta)*vp0
  bar0=bar;vp0=vp;ph=B@h-s*bar;s=beta*(y-ph)/(noise+vp)+(1-beta)*s;sv=beta/(noise+vp)+(1-beta)*sv
  xb=beta*x+(1-beta)*xb;hb=beta*h+(1-beta)*hb;Bb=np.einsum('imk,k->mi',U,xb);Hb=np.einsum('i,imk->mk',hb,U)
  vr=1/max(sv*np.linalg.norm(Hb)**2/n,1e-12);vq=1/max(sv*np.linalg.norm(Bb)**2/P,1e-12)
  rx=x+vr*(Hb.conj().T@s-xb*sv*vh*np.linalg.norm(U)**2/n)
  rh=h+vq*(Bb.conj().T@s-hb*sv*vx*np.linalg.norm(U)**2/P)
  ext,app,mu,v=marginal(-abs((rx-p)[:,None]-a)**2/vr,prior,pd);x=p+mu;vh=tau*vq/(tau+vq);h=tau*rh/(tau+vq)
  trace.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))
 return dict(extrinsic=ext,states=trace)

rng=np.random.default_rng(7361590);checks=[]
for n,P,repeat in [(7,2,False),(16,3,False),(31,4,False),(32,3,True)]:
 ls=rng.choice(n,size=P,replace=False)
 if repeat:ls[1]=ls[0]
 c=Channel(n,.017,.003,ls,rng.uniform(-2,2,P),(rng.normal(size=P)+1j*rng.normal(size=P))/np.sqrt(2*P))
 # Explicit independent CPP/time construction.
 k=np.arange(n);F=np.exp(-2j*np.pi*k[:,None]*k/n)/np.sqrt(n);A=np.diag(np.exp(2j*np.pi*c.c2*k*k))@F@np.diag(np.exp(2j*np.pi*c.c1*k*k));U=[]
 for l,nu in zip(c.delays,c.dopplers):
  T=np.zeros((n,n),complex)
  for m in range(n):T[m,(m-l)%n]=np.exp(2j*np.pi*nu*m/n)*(np.exp(2j*np.pi*c.c1*(n*n+2*n*(m-l))) if m<l else 1)
  U.append(A@T@A.conj().T)
 U=np.array(U);p=np.exp(1j*rng.uniform(0,2*np.pi,n))*.7;d=(rng.choice([-1,1],n)+1j*rng.choice([-1,1],n))*.5;noise=.4;y=np.einsum('i,imk,k->m',c.gains,U,p+d)+np.sqrt(noise/2)*(rng.normal(size=n)+1j*rng.normal(size=n));pr=rng.normal(size=2*n)
 out=scalar_joint(y,p,c,noise,prior=pr,iterations=8,record_states=True);ref=dense(y,p,U,c.gains,noise,pr)
 V=np.linalg.qr(rng.normal(size=(n,n))+1j*rng.normal(size=(n,n)))[0];rot=dense(V@y,p,np.einsum('mk,ikj->imj',V,U),c.gains,noise,pr)
 for label,obj in [('dense',ref),('rotation',rot)]:
  for j,(x,z) in enumerate(zip(out['states'],obj['states'])):
   err=max(float(np.max(abs(np.asarray(x[key])-np.asarray(z[key])))) for key in ('h','mu','v','vr','vq','vh','sv','bar','vp'));assert err<2e-9,(n,label,j,err);checks.append(dict(n=n,P=P,label=label,iteration=j,error=err))
 # Explicit response norm/Gram proof also covers repeated delays.
 H=np.einsum('i,imk->mk',c.gains,U);err=abs(np.linalg.norm(H)**2/n-TimePathOps(c).power(c.gains));assert err<1e-10;checks.append(dict(n=n,P=P,label='norm',error=err))
# Full-size existing AF-domain scalar code and exact-refit comparison.
n=1024;P=8;c=Channel(n,9/(2*n),1.9751241797117955e-7,np.array([0,5,11,18,32,51,70,91]),rng.uniform(-2,2,P),(rng.normal(size=P)+1j*rng.normal(size=P))/np.sqrt(2*P));p=np.exp(1j*rng.uniform(0,2*np.pi,n))/np.sqrt(2);d=(rng.choice([-1,1],n)+1j*rng.choice([-1,1],n))*.5;y=c.apply(p+d)+.3*(rng.normal(size=n)+1j*rng.normal(size=n));pr=rng.normal(size=2*n)
a=scalar_joint(y,p,c,.18,prior=pr,iterations=20);b=scalar_pbigamp(y,p,c,.18,prior=pr,iterations=20)
for key in ['mu','variance','gains','extrinsic']:
 err=float(np.max(abs(a[key]-b[key])));assert err<2e-9,(key,err);checks.append(dict(n=n,label=key,error=err))
mu,v,_=moments(pr,.5)
for mode in ['mean','scalar','soft']:
 c0,r0=refine(y,p,mu,v,c.delays,np.rint(c.dopplers),c.gains,c.c1,c.c2,.18,mode=mode,rounds=2)
 c1,r1=time_refine(y,p,mu,v,c.delays,np.rint(c.dopplers),c.gains,c.c1,c.c2,.18,mode=mode,rounds=2)
 for key,er in [('doppler',np.max(abs(c0.dopplers-c1.dopplers))),('gains',np.max(abs(c0.gains-c1.gains))),('objective',abs(r0['objective']-r1['objective']))]:
  assert er<2e-7,(mode,key,er);checks.append(dict(n=n,label=mode+'_'+key,error=float(er)))
print('checks',len(checks),'max',max(q['error'] for q in checks));(R/'results'/'twofft_checks.json').write_text(json.dumps(checks,indent=2))
