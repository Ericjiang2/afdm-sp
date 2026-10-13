import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OLD=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'))
sys.path[:0]=[str(ROOT/'src'),str(OLD/'src')]
import numpy as np
from receiver import context,pilot_front,decoder_messages,extract_info
from physical import Channel,refine
from structured_ep import ep_t
from fast_bilinear import pbigamp
from messages import moments
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
system,model,code,header=context();rows=[]
for idx in range(4):
 snr=[6,7,7,8][idx]
 def rngf(rep,index,component,*,split):return np.random.default_rng(np.random.SeedSequence([20260921,935170,index,component]))
 raw=make_frame(system,code,0,idx,snr,split=2,rng_factory=rngf);raw,_=physical_observation(raw,system,prefix_length=system.l_max_cap)
 obs={k:raw[k] for k in ('y','pilot','sigma2')}
 init=pilot_front(obs,system,code)
 for arm,iters in [('ep',2),('base',20),('coherent',20),('base',40),('coherent',40)]:
  st=time.perf_counter();s={k:v.copy() if isinstance(v,np.ndarray) else v for k,v in init.items()}
  for r in range(2):
   c,detail=refine(obs['y'],obs['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,obs['sigma2'],mode='mean',max_paths=8,rounds=2)
   if arm=='ep':o=ep_t(obs['y']-c.apply(obs['pilot']),c,obs['sigma2'],prior=s['prior'],iterations=iters)
   else:o=pbigamp(obs['y'],obs['pilot'],c,obs['sigma2'],prior=s['prior'],iterations=iters,mode=arm)
   dec=decoder_messages(code,np.clip(o['extrinsic'],-20,20),maxiter=50)
   s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20);s['mu'],s['v'],_=moments(np.clip(dec['raw_app'],-20,20),.5)
   s['delays']=c.delays;s['dopplers']=c.dopplers;s['gains']=o.get('gains',c.gains)
  row=dict(frame=idx,snr=snr,arm=arm,iterations=iters,errors=int(np.sum(extract_info(code,dec['decoded'])!=raw['info'])),seconds=time.perf_counter()-st,trace=o['trace']);rows.append(row);print({k:v for k,v in row.items() if k!='trace'},flush=True)
  np.savez_compressed(ROOT/'results'/f'fastamp_{idx}_{arm}{iters}.npz',decoded=dec['decoded'],truth=raw['coded'],llr=o['extrinsic'])
 (ROOT/'results'/'fastamp_screen.json').write_text(json.dumps(rows,indent=2))
