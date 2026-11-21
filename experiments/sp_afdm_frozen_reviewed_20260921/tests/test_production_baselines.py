import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from receiver import *
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
system,model,code,header=context()
def rngf(rep,index,component,*,split):return np.random.default_rng(np.random.SeedSequence([20260920,480013,index,component]))
raw=make_frame(system,code,0,5,8,split=2,rng_factory=rngf);raw,_=physical_observation(raw,system,prefix_length=system.l_max_cap);obs={k:raw[k] for k in ('y','pilot','sigma2')};s=front(obs,model,code);rows=[]
for name,cfg in [('gamp_full',dict(method='gamp',grid_iterations=2,gamp_iterations=15)),('bilinear',dict(detector='bilinear',terminal_iterations=2)),('sbl_full',dict(method='sbl',grid_iterations=2))]:
 r=finish(obs,s,system,code,cfg);assert np.isfinite(r['llr']).all();row=dict(arm=name,errors=int(np.sum(r['info_hat']!=raw['info'])),seconds_incremental=r['seconds']);rows.append(row);print(row,flush=True)
 np.savez_compressed(ROOT/'results'/f'production_{name}.npz',decoded=r['decoded'],coded=raw['coded'],**r['arrays'])
(ROOT/'results'/'production_baselines.json').write_text(json.dumps(dict(rows=rows,scope='one N=1024 observation, reduced update caps, engineering check only'),indent=2))
