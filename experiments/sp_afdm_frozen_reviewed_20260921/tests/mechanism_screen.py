import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import sys,time,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from receiver import *
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
system,model,code,header=context();rows=[]
def rngf(rep,index,component,*,split):return np.random.default_rng(np.random.SeedSequence([20260920,480013,index,component]))
variants={'I1':dict(method='I1'),'mean':{},'scalar':dict(ce_mode='scalar'),'soft':dict(ce_mode='soft'),'decoder_app':dict(qsource='decoder_app'),'no_weak_variance':dict(weak_variance=False),'reset_prior':dict(retain_prior=False),'magnitude_mask':dict(selection='magnitude'),'raw_truncation':dict(preserve_mean=False),'ep':dict(detector='ep',terminal_iterations=4)}
for index in range(1,5):
 for snr in (7,8):
  raw=make_frame(system,code,0,index,snr,split=2,rng_factory=rngf);raw,_=physical_observation(raw,system,prefix_length=system.l_max_cap);obs={k:raw[k] for k in ('y','pilot','sigma2')};s=front(obs,model,code)
  for name,config in variants.items():
   out=finish(obs,s,system,code,config);r=dict(index=index,snr=snr,arm=name,info_errors=int(np.sum(out['info_hat']!=raw['info'])),incremental_seconds=out['seconds'],front_seconds=s['seconds'])
   if 'diagonal_energy' in out['arrays']:
    E=out['arrays']['diagonal_energy'];K=out['arrays']['selected_shifts'];r['selection_tail']=float(E.sum()-E[K].sum())
   rows.append(r);np.savez_compressed(ROOT/'results'/f'screen_{index}_{snr}_{name}.npz',decoded=out['decoded'],coded=raw['coded'],**out['arrays'])
  print('finished',index,snr,flush=True)
  (ROOT/'results'/'mechanism_screen.json').write_text(json.dumps(dict(rows=rows,scope='4 exogenous blocks reused at 7 and 8 dB; shared front state; 80 incremental tests; exploratory, not complete-budget comparison'),indent=2))
for name in variants:
 rr=[r for r in rows if r['arm']==name];print(name,sum(r['info_errors']>0 for r in rr),float(np.median([r['incremental_seconds'] for r in rr])),flush=True)
