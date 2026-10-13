"""Clean gain-variance suppression: same soft CE, same observed inputs."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'));sys.path[:0]=[str(R/'src'),str(O/'src')]
import numpy as np
from receiver import context,extract_info
from native_twofft import receive
system,model,code,header=context();system.P_paths=8;system.rho=.5;rows=[]
for idx in range(8):
 z=np.load(R/'results'/f'native_{idx}_input_truth.npz');obs={k:z[k] for k in ('y','pilot','sigma2')}
 for gm in ['point','fixed']:
  d,a,row=receive(obs,system,code,ce_mode='soft',gain_mode=gm);row.update(frame=idx,snr=6 if idx<4 else 7,arm=gm,errors=int(np.sum(extract_info(code,d['decoded'])!=z['info'])));rows.append(row)
  np.savez_compressed(R/'results'/f'clean_{idx}_{gm}.npz',**a);print({k:v for k,v in row.items() if k!='events'},flush=True)
(R/'results'/'clean_screen.json').write_text(json.dumps(rows,indent=2))
