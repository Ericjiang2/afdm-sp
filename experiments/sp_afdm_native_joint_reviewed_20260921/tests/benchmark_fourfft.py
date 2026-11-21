import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
import sys,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OLD=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'));sys.path[:0]=[str(ROOT/'src'),str(OLD/'src')]
import numpy as np
from physical import Channel
from fast_bilinear import scalar_pbigamp
from twofft import scalar_joint
from functools import partial
scalar_pbigamp=partial(scalar_joint,observation_domain="af")
rng=np.random.default_rng(826891);rows=[]
for n in (256,1024):
 for P in (3,8):
  c=Channel(n,9/(2*n),.002/n,np.sort(rng.choice(min(n//8,103),P,False)),rng.uniform(-2,2,P),(rng.normal(size=P)+1j*rng.normal(size=P))/np.sqrt(2*P))
  p=np.sqrt(.5)*np.exp(1j*rng.uniform(0,2*np.pi,n));y=rng.normal(size=n)+1j*rng.normal(size=n);pr=rng.normal(size=2*n)
  args=(y,p,c,.2);kw=dict(prior=pr,iterations=20)
  a=scalar_pbigamp(*args,**kw);b=scalar_joint(*args,**kw)
  err=max(float(np.max(abs(a[k]-b[k]))) for k in ('mu','gains','extrinsic','variance'));assert err<1e-7
  ts={'fourfft':[],'twofft':[]}
  for rep in range(7):
   for ident,fn in ([('fourfft',scalar_pbigamp),('twofft',scalar_joint)] if rep%2==0 else [('twofft',scalar_joint),('fourfft',scalar_pbigamp)]):
    t=time.perf_counter();fn(*args,**kw);ts[ident].append(time.perf_counter()-t)
  row=dict(n=n,paths=P,iterations=20,max_output_discrepancy=err,raw_times=ts,medians={k:float(np.median(v)) for k,v in ts.items()});rows.append(row);print(row,flush=True)
(ROOT/'results'/'fourfft_benchmark.json').write_text(json.dumps(rows,indent=2))
