import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import sys,time,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'));sys.path[:0]=[str(R/'src'),str(O/'src')]
import numpy as np
from receiver import context,pilot_front,decoder_messages,extract_info
from physical import refine
from block_bilinear import block_amp
from messages import moments
system,model,code,hdr=context();rows=[]
for idx in range(8):
 raw=dict(np.load(R/'results'/f'native_{idx}_input_truth.npz'));obs={k:raw[k] for k in ('y','pilot','sigma2')}
 for ce in ['soft','mean']:
  t=time.perf_counter();s=pilot_front(obs,system,code)
  for rnd in range(2):
   c,detail=refine(obs['y'],obs['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,obs['sigma2'],mode=ce,max_paths=8,rounds=2)
   o=block_amp(obs['y'],obs['pilot'],c,obs['sigma2'],prior=s['prior'],iterations=20)
   dec=decoder_messages(code,np.clip(o['extrinsic'],-20,20),maxiter=50);s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20);s['mu'],s['v'],_=moments(np.clip(dec['raw_app'],-20,20),.5);s['delays']=c.delays;s['dopplers']=c.dopplers;s['gains']=o['gains']
  row=dict(frame=idx,ce=ce,errors=int(np.sum(extract_info(code,dec['decoded'])!=raw['info'])),seconds=time.perf_counter()-t);rows.append(row);print(row,flush=True)
  np.savez_compressed(R/'results'/f'block_{idx}_{ce}.npz',decoded=dec['decoded'],truth=raw['coded'],llr=o['extrinsic'],gains=o['gains'],gain_cov=o['gain_covariance'])
  (R/'results'/'block_screen.json').write_text(json.dumps(rows,indent=2))
