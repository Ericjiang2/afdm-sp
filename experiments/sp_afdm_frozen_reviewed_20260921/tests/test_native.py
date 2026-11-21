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
raw=make_frame(system,code,0,6,8,split=2,rng_factory=rngf);raw,_=physical_observation(raw,system,prefix_length=system.l_max_cap);obs={k:raw[k] for k in ('y','pilot','sigma2')};rows=[]
for name,cfg in [('gamp',dict(method='gamp',coded_rounds=2,grid_iterations=1,gamp_iterations=8)),('ep',dict(detector='ep',coded_rounds=2,terminal_iterations=2)),('bilinear',dict(detector='bilinear',coded_rounds=1,terminal_iterations=2))]:
 r,s=run_native(obs,system,code,cfg);assert np.isfinite(r['llr']).all();row=dict(arm=name,complete_seconds=r['seconds_complete'],finite=True);rows.append(row);print(row,flush=True)
(ROOT/'results'/'native_smoke.json').write_text(json.dumps(dict(rows=rows,scope='production-size native-start interface checks, reduced iterations, no performance conclusion'),indent=2))
