import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from receiver import *
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
system,model,code,header=context()
def rngf(rep,index,component,*,split):return np.random.default_rng(np.random.SeedSequence([20260920,480013,index,component]))
raw=make_frame(system,code,0,1,8,split=2,rng_factory=rngf);raw,_=physical_observation(raw,system,prefix_length=system.l_max_cap);obs={k:raw[k] for k in ('y','pilot','sigma2')};s=front(obs,model,code)
x=np.random.default_rng(992).normal(size=1024)+1j*np.random.default_rng(993).normal(size=1024);c=Channel(1024,system.c1,system.c2,s['delays'],s['dopplers'],s['gains'])
e=float(np.linalg.norm(c.apply(x)-s['H']@x)/np.linalg.norm(s['H']@x));pc,pe=project_integer_matrix(s['H'],system.c1,system.c2,s['delays'],s['dopplers']);ce=float(np.linalg.norm(pc.apply(x)-s['H']@x)/np.linalg.norm(s['H']@x));print('raw gain mismatch',e,'projected mismatch',ce);assert ce<5e-5
(ROOT/'results'/'integer_geometry.json').write_text(json.dumps(dict(last_gain_vs_actual_H=e,projected_gain_vs_actual_H=ce,scope='last gains differ from damped/masked H; corrected actual-matrix comparator verified'),indent=2))
