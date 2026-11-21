"""Recount saved information errors without importing any proposed receiver module."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS'):os.environ[k]='1'
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'upstream/spafdm_receiver_handoff'))
from afdm_sp_joint_unrolled.e1_ldpc import build_code
code=build_code(2048,d_v=3,d_c=6,seed=20260726);fc=code['free_cols'];records=[]
for name,prefix in [('mechanism_screen','screen'),('interface_control','interface')]:
 for r in json.loads((ROOT/'results'/f'{name}.json').read_text())['rows']:
  i=r.get('index');f=ROOT/'results'/f"{prefix}_{i}_{r['snr']}_{r['arm']}.npz";a=np.load(f,allow_pickle=False)
  count=int(np.sum(a['decoded'][fc]!=a['coded'][fc]));assert count==r['info_errors'],(f,count,r['info_errors'])
  for k in a.files:
   if 'llr' in k or 'final_' in k or k in ('ce_mu','ce_variance'):
    assert np.isfinite(a[k]).all(),(f,k)
  records.append(dict(file=f.name,info_errors=count))
(ROOT/'results/recount.json').write_text(json.dumps(dict(count=len(records),records=records),indent=2));print('PASS',len(records),'saved decisions')
