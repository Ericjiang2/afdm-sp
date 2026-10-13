"""Same-eight-input engineering comparison; no new statistical trials."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OLD=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'));sys.path[:0]=[str(ROOT/'src'),str(OLD/'src')]
import numpy as np
from receiver import context,extract_info
from native_twofft import receive
system,model,code,header=context();system.P_paths=8;system.rho=.5
rows=[]
# Same fixture warmup separately labeled, no measurement credit.
z=np.load(ROOT/'results'/'native_0_input_truth.npz');obs={k:z[k] for k in ('y','pilot','sigma2')};receive(obs,system,code,iterations=1,rounds=1)
for idx in range(8):
 z=np.load(ROOT/'results'/f'native_{idx}_input_truth.npz');obs={k:z[k] for k in ('y','pilot','sigma2')}
 for mode in (('soft','joint'),('mean','point')):
  dec,a,row=receive(obs,system,code,ce_mode=mode[0],gain_mode=mode[1]);name='twofft_'+mode[0]+'_'+mode[1];old=np.load(ROOT/'results'/(f'native_{idx}_AMP20_'+('soft' if mode[0]=='soft' else 'point')+'.npz'))
  row.update(frame=idx,snr=6 if idx<4 else 7,arm=name,errors=int(np.sum(extract_info(code,dec['decoded'])!=z['info'])),old_decision_disagreements=int(np.sum(old['r1_decoded']!=dec['decoded'])),old_llr_maxdiff=float(np.max(abs(old['r1_input_llr']-a['r1_input_llr']))))
  rows.append(row);np.savez_compressed(ROOT/'results'/f'{name}_{idx}.npz',**a);(ROOT/'results'/'twofft_native_screen.json').write_text(json.dumps(rows,indent=2));print({k:v for k,v in row.items() if k!='events'},flush=True)
