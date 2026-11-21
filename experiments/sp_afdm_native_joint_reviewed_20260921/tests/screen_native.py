"""Eight fresh-frame, matched-complete-pipeline development screen.
Not Stage-2 replay, no confirmation, not pooled with any preceding screen.
"""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OLD=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'))
sys.path[:0]=[str(ROOT/'src'),str(OLD/'src')]
import numpy as np
from receiver import context,pilot_front,decoder_messages,extract_info,run_native
from physical import Channel,refine
from structured_ep import ep_t
from fast_bilinear import scalar_pbigamp
from bilinear import pbigabp
from messages import moments
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
cfgs=[('EP2_soft','ep',2,'soft','fixed'),('EP2_mean','ep',2,'mean','fixed'),('EP4_mean','ep',4,'mean','fixed'),('AMP20_soft','amp',20,'soft','joint'),('AMP20_mean','amp',20,'mean','joint'),('AMP20_point','amp',20,'mean','point'),('AMP20_fixed','amp',20,'mean','fixed')]
(ROOT/'results'/'native_registration.json').write_text(json.dumps(dict(seed_namespace=[20260921,935171],frames=list(range(8)),snrs=[6]*4+[7]*4,configurations=cfgs,rounds=2,status='development'),indent=2))
system,model,code,header=context();system.P_paths=8;system.rho=.5;rows=[]
def pipeline(obs,cfg):
 ident,kind,iters,ce,gm=cfg;st=time.perf_counter();s=pilot_front(obs,system,code);pilot_secs=time.perf_counter()-st;events=[];arrays={}
 for r in range(2):
  t0=time.perf_counter();c,detail=refine(obs['y'],obs['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,obs['sigma2'],mode=ce,max_paths=8,rounds=2);tc=time.perf_counter()-t0
  t0=time.perf_counter()
  if kind=='ep':o=ep_t(obs['y']-c.apply(obs['pilot']),c,obs['sigma2'],prior=s['prior'],iterations=iters)
  elif kind=='amp':o=scalar_pbigamp(obs['y'],obs['pilot'],c,obs['sigma2'],prior=s['prior'],iterations=iters,gain_mode=gm)
  else:o=pbigabp(obs['y'],obs['pilot'],c,obs['sigma2'],prior=s['prior'],iterations=iters)
  ti=time.perf_counter()-t0;t0=time.perf_counter();dec=decoder_messages(code,np.clip(o['extrinsic'],-20,20),maxiter=50);td=time.perf_counter()-t0
  s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20);s['mu'],s['v'],_=moments(np.clip(dec['raw_app'],-20,20),.5)
  s['delays']=c.delays;s['dopplers']=c.dopplers;s['gains']=o.get('gains',c.gains)
  events.append(dict(round=r,ce=tc,inference=ti,decoder=td,ready=time.perf_counter()-st,decoder_iterations=int(dec['iterations']),gamma_offdiag=float(np.linalg.norm(detail['gamma']-np.diag(np.diag(detail['gamma'])))/max(np.linalg.norm(detail['gamma']),1e-30))))
  arrays.update({f'r{r}_{k}':v for k,v in {'decoded':dec['decoded'],'input_llr':dec['incoming_llr'],'app':dec['raw_app'],'check':dec['raw_check_extrinsic'],'delays':c.delays,'dopplers':c.dopplers,'gains':s['gains'],'ce_gains':c.gains,'mu':o['mu'],'variance':o['variance']}.items()})
 elapsed=time.perf_counter()-st
 return dec,arrays,dict(seconds=elapsed,pilot_seconds=pilot_secs,events=events)
# one warm-up excluded, separate namespace
start_idx=int(os.environ.get('SCREEN_START','0'))
if start_idx:rows=json.loads((ROOT/'results'/'native_screen.json').read_text())
for idx in [-1]+list(range(start_idx,8)):
 snr=6 if idx<4 else 7
 def rngf(rep,index,component,*,split):return np.random.default_rng(np.random.SeedSequence([20260921,935171,index+1,component]))
 raw=make_frame(system,code,0,idx,snr,split=2,rng_factory=rngf);raw,diag=physical_observation(raw,system,prefix_length=system.l_max_cap)
 obs={k:raw[k] for k in ('y','pilot','sigma2')}
 if idx<0:
  for cf in [cfgs[0],cfgs[4]]:pipeline(obs,cf)
  continue
 np.savez_compressed(ROOT/'results'/f'native_{idx}_input_truth.npz',**obs,info=raw['info'],coded=raw['coded'],true_delays=raw['params']['l_i'],true_dopplers=raw['params']['k_real'],true_gains=raw['params']['g_i'])
 cc=cfgs[idx%len(cfgs):]+cfgs[:idx%len(cfgs)]
 for cf in cc:
  d,a,row=pipeline(obs,cf);row.update(frame=idx,snr=snr,arm=cf[0],errors=int(np.sum(extract_info(code,d['decoded'])!=raw['info'])),channel_power=diag['channel_energy_per_dimension']);rows.append(row)
  np.savez_compressed(ROOT/'results'/f'native_{idx}_{cf[0]}.npz',**a);(ROOT/'results'/'native_screen.json').write_text(json.dumps(rows,indent=2));print({k:v for k,v in row.items() if k!='events'},flush=True)
 (ROOT/'results'/'native_screen.json').write_text(json.dumps(rows,indent=2))
