"""Independent saved-bit recount; imports no receiver, detector, or estimator."""
import os,json,hashlib
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'))
cp=O/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
code=np.load(cp);fc=code['free_cols'];H=code['H'];records=[]
# All comparisons use saved arrays, never rerun numerical inference.
for stem in ['tangent','tangent_fixed','fastamp','scalaramp','gain_factorial','six_db']:
 for row in json.loads((R/'results'/f'{stem}_screen.json').read_text()):
  p=R/'results'/f'{stem}_{row["frame"]}_{row["arm"]}{row["iterations"]}.npz';z=np.load(p)
  err=int(np.count_nonzero(z['decoded'][fc]!=z['truth'][fc]));assert err==row['errors'];assert np.isfinite(z['llr']).all()
  records.append(dict(file=p.name,errors=err))
for stem in ['native','fair_control','twofft_native','block','clean']:
 for row in json.loads((R/'results'/f'{stem}_screen.json').read_text()):
  i=row['frame'];truth=np.load(R/'results'/f'native_{i}_input_truth.npz')
  if stem=='native':p=R/'results'/f'native_{i}_{row["arm"]}.npz'
  elif stem=='fair_control':p=R/'results'/f'fair_{i}_{row["arm"]}.npz'
  elif stem=='twofft_native':p=R/'results'/f'{row["arm"]}_{i}.npz'
  elif stem=='clean':p=R/'results'/f'clean_{i}_{row["arm"]}.npz'
  else:p=R/'results'/f'block_{i}_{row["ce"]}.npz'
  z=np.load(p);d=z['decoded'] if stem=='block' else z['r1_decoded'];err=int(np.count_nonzero(d[fc]!=truth['info']));assert err==row['errors']
  assert np.array_equal(truth['coded'][fc],truth['info']);assert not np.any((H@truth['coded'])%2)
  if stem!='block':
   for r in range(2):
    assert np.isfinite(z[f'r{r}_input_llr']).all();assert np.isfinite(z[f'r{r}_mu']).all()
    assert np.max(abs(z[f'r{r}_app']-z[f'r{r}_input_llr']-z[f'r{r}_check']))<1e-10
   assert row['events'][-1]['ready']<=row['seconds'];assert len(row['events'])==2
  records.append(dict(file=p.name,errors=err,syndrome_weight=int(np.count_nonzero((H@d)%2))))
out=dict(comparisons=len(records),status='pass',generator_sha256=hashlib.sha256(code['G'].tobytes()).hexdigest(),observations='28 fresh exploratory observations; native/fair/twofft/block share 8 of them',records=records)
(R/'results'/'independent_output_audit.json').write_text(json.dumps(out,indent=2));print(out['status'],out['comparisons'],out['generator_sha256'])
