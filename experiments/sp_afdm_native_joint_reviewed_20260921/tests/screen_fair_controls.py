"""Same eight diagnostic observations, no added independent trials.
All arms receive the same time-domain refit. PBi only four low-SNR fixtures.
"""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OLD=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'));sys.path[:0]=[str(ROOT/'src'),str(OLD/'src')]
import numpy as np
from receiver import context,pilot_front,decoder_messages,extract_info
from structured_ep import ep_t
from bilinear import pbigabp
from messages import moments
from twofft import time_refine
from native_twofft import receive
system,model,code,header=context();system.P_paths=8;system.rho=.5
cfgs=[('EP2_soft_fastCE','ep',2,'soft'),('EP2_mean_fastCE','ep',2,'mean'),('EP4_mean_fastCE','ep',4,'mean'),('PBi8_soft_fastCE','pbi',8,'soft'),('twofft_soft_joint','new',20,'soft')]
(ROOT/'results'/'fair_control_registration.json').write_text(json.dumps(dict(observations='native_0..7; PBi only 0..3',configurations=cfgs,comment='post-synthesis engineering controls, not fresh radio trials'),indent=2))
def pipeline(obs,cf):
 if cf[1]=='new':return receive(obs,system,code)
 name,kind,iters,ce=cf;st=time.perf_counter();s=pilot_front(obs,system,code);tp=time.perf_counter()-st;events=[];arr={}
 for r in range(2):
  t=time.perf_counter();c,det=time_refine(obs['y'],obs['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,obs['sigma2'],mode=ce);tc=time.perf_counter()-t;t=time.perf_counter()
  if kind=='ep':o=ep_t(obs['y']-c.apply(obs['pilot']),c,obs['sigma2'],prior=s['prior'],iterations=iters)
  else:o=pbigabp(obs['y'],obs['pilot'],c,obs['sigma2'],prior=s['prior'],iterations=iters)
  ti=time.perf_counter()-t;t=time.perf_counter();dec=decoder_messages(code,np.clip(o['extrinsic'],-20,20),maxiter=50);td=time.perf_counter()-t
  s['mu'],s['v'],_=moments(np.clip(dec['raw_app'],-20,20),.5);s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20);s['delays']=c.delays;s['dopplers']=c.dopplers;s['gains']=o.get('gains',c.gains)
  events.append(dict(round=r,ce=tc,inference=ti,decoder=td,ready=time.perf_counter()-st,decoder_iterations=int(dec['iterations'])))
  arr.update({f'r{r}_{k}':v for k,v in {'decoded':dec['decoded'],'input_llr':dec['incoming_llr'],'app':dec['raw_app'],'check':dec['raw_check_extrinsic'],'delays':c.delays,'dopplers':c.dopplers,'gains':s['gains'],'mu':o['mu'],'variance':o['variance']}.items()})
 return dec,arr,dict(seconds=time.perf_counter()-st,pilot_seconds=tp,events=events)
rows=json.loads((ROOT/'results'/'fair_control_screen.json').read_text()) if (ROOT/'results'/'fair_control_screen.json').exists() else []
seen={(r['frame'],r['arm']) for r in rows};newcount=0
z=np.load(ROOT/'results'/'native_0_input_truth.npz');obs={k:z[k] for k in ('y','pilot','sigma2')}
pipeline(obs,('warmep','ep',1,'soft'));receive(obs,system,code,iterations=1,rounds=1)
for idx in range(8):
 z=np.load(ROOT/'results'/f'native_{idx}_input_truth.npz');obs={k:z[k] for k in ('y','pilot','sigma2')}
 cc=cfgs[idx%5:]+cfgs[:idx%5]
 for cf in cc:
  if cf[1]=='pbi' and idx>=4:continue
  if (idx,cf[0]) in seen:continue
  dec,a,row=pipeline(obs,cf);row.update(frame=idx,snr=6 if idx<4 else 7,arm=cf[0],errors=int(np.sum(extract_info(code,dec['decoded'])!=z['info'])));rows.append(row)
  np.savez_compressed(ROOT/'results'/f'fair_{idx}_{cf[0]}.npz',**a);(ROOT/'results'/'fair_control_screen.json').write_text(json.dumps(rows,indent=2));print({k:v for k,v in row.items() if k!='events'},flush=True)
  newcount+=1
  if newcount>=int(os.environ.get('MAX_NEW','5')):raise SystemExit(0)

