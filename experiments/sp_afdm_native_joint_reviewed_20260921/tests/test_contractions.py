import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'))
sys.path[:0]=[str(R/'src'),str(O/'src')]
import numpy as np
from physical import Channel
from fast_bilinear import Contractions
rng=np.random.default_rng(924785);res=[]
for n,P in [(7,2),(16,3),(64,4)]:
 c1=.017;c2=.003;ls=rng.choice(n,size=P,replace=False);nus=rng.uniform(-2,2,P);h=(rng.normal(size=P)+1j*rng.normal(size=P))/np.sqrt(2*P)
 c=Channel(n,c1,c2,ls,nus,h);o=Contractions(c)
 # independent action-based matrices, no closed-form diagonal formula
 U=np.array([np.column_stack([u.apply(e) for e in np.eye(n)]) for u in o.units]);H=np.einsum('i,imk->mk',h,U)
 v=rng.uniform(.01,.5,n);w=rng.uniform(.2,2,n);x=rng.normal(size=n)+1j*rng.normal(size=n);vg=rng.uniform(.01,.1,P)
 G=np.einsum('imk,jmk,m,k->ij',U.conj(),U,w,v)
 refs=[(o.apply(h,x),H@x),(o.adjoint(h,x),H.conj().T@x),(o.squared_forward(h,v),abs(H)**2@v),(o.squared_adjoint(h,w),(abs(H)**2).T@w),(o.unit_squared_adjoint(w),np.einsum('imk,m->ik',abs(U)**2,w)),(o.weighted_gamma(v,w),G),(o.coherent_data_correction(vg,w,x),sum(g*u.conj().T@(w*(u@x)) for g,u in zip(vg,U)))]
 for k,(a,b) in enumerate(refs):
  err=float(np.max(abs(a-b)));assert err<1e-10,(n,k,err);res.append(dict(n=n,P=P,check=k,maxerr=err))
print(len(res),max(x['maxerr'] for x in res));(R/'results'/'contraction_checks.json').write_text(json.dumps(res,indent=2))
