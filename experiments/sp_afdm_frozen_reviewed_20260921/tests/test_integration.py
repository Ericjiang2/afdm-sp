import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import sys,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from receiver import *
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
system,model,code,header=context();rows=[]
def rngf(rep,index,component,*,split):return np.random.default_rng(np.random.SeedSequence([20260920,480013,index,component]))
raw=make_frame(system,code,0,0,8,split=2,rng_factory=rngf);raw,_=physical_observation(raw,system,prefix_length=system.l_max_cap);obs={k:raw[k] for k in ('y','pilot','sigma2')}
s=front(obs,model,code)
# Same unchanged outer source and controls as full upstream adapter.
r=BaselineReceiver(model,code,'B0-p2-s0.5',system=system,initial_lstsq_driver='gels').run(dict(obs,constellation=CONST.copy()),audit=False,code_feedback=CodeFeedback(code,checkpoint=1),bp_schedule=UniformBPSchedule(outer_bp_iterations=12),bp_edge_projection='qpsk_tanh')
checks={k:float(np.max(abs(s[k]-r[j]))) for k,j in [('H','H'),('x_soft','x_soft'),('gains','gains')]}
print('FRONT DIFFERENCE',checks,flush=True)
assert max(checks.values())==0
for name,cfg in [('I1',dict(method='I1')),('mean',dict(method='proposed')),('soft',dict(method='proposed',ce_mode='soft')),('ep',dict(method='proposed',detector='ep',terminal_iterations=2)),('gamp_active',dict(method='gamp',dictionary='active',grid_iterations=2,gamp_iterations=12))]:
 out=finish(obs,s,system,code,cfg);assert np.isfinite(out['llr']).all()
 row=dict(arm=name,errors=int(np.sum(out['info_hat']!=raw['info'])),incremental_seconds=out['seconds'],front_seconds=s['seconds']);rows.append(row);print(row,flush=True)
 np.savez_compressed(ROOT/'results'/('integration_'+name+'.npz'),decoded=out['decoded'],coded=raw['coded'],**out['arrays'])
(ROOT/'results'/'integration.json').write_text(json.dumps(dict(checks=checks,rows=rows,scope='one frame engineering check, shared preterminal state, not equal complete-cost FER evidence'),indent=2))
