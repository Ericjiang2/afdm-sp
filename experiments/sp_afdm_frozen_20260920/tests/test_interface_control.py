import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from receiver import *
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
system,model,code,header=context();rows=[]
def rngf(rep,index,component,*,split):return np.random.default_rng(np.random.SeedSequence([20260920,480013,index,component]))
for idx in range(1,5):
 for snr in (7,8):
  raw=make_frame(system,code,0,idx,snr,split=2,rng_factory=rngf);raw,_=physical_observation(raw,system,prefix_length=system.l_max_cap);obs={k:raw[k] for k in ('y','pilot','sigma2')};s=front(obs,model,code)
  for name,cfg in [('integer_BP',dict(method='integer_control',diagonal_cap=40)),('integer_EP',dict(method='integer_control',detector='ep',terminal_iterations=4)),('soft_noncircular',dict(ce_mode='soft',noncircular=True))]:
   out=finish(obs,s,system,code,cfg);row=dict(index=idx,snr=snr,arm=name,info_errors=int(np.sum(out['info_hat']!=raw['info'])),seconds_incremental=out['seconds']);rows.append(row)
   np.savez_compressed(ROOT/'results'/f'interface_{idx}_{snr}_{name}.npz',decoded=out['decoded'],coded=raw['coded'],**out['arrays'])
for name in ('integer_BP','integer_EP','soft_noncircular'):
 rr=[r for r in rows if r['arm']==name];print(name,sum(r['info_errors']>0 for r in rr),float(np.median([r['seconds_incremental'] for r in rr])))
(ROOT/'results'/'interface_control.json').write_text(json.dumps(dict(rows=rows,scope='8 reused observations, isolating terminal-interface/geometry, not statistical confirmation'),indent=2))
