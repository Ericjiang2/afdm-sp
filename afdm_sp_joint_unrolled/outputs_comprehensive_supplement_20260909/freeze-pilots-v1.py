import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import numpy as np,json,hashlib
from afdm_sp_joint_unrolled.supplement_pilots import select_pilots,waveform_metrics,transform
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
P=Path('.mission/20260909_09-01-15-afdm-comprehensive-supplement')
protocol=P/'evidence/pilot-selection-protocol-v1.json';spec=json.loads(protocol.read_text())
assert hashlib.sha256(Path('afdm_sp_joint_unrolled/supplement_pilots.py').read_bytes()).hexdigest()==spec['source_sha256']
system=_make_config_a(1024,2.,8,10.,4.)
assert (system.l_max_cap,system.k_max_cap)==(102,2)
assert np.isclose(2*1024*system.c1,5)
pilots,details=select_pilots(system._zc_seq,c1=system.c1,c2=system.c2,l_max=102,k_max=2)
# Engineering-only fixed synthetic symbol fixture, no receiver or H and no selection feedback.
rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence([20260909,503,0])))
data=.5*((1-2*rng.integers(0,2,1024))+1j*(1-2*rng.integers(0,2,1024)))
metrics={}
for name,p in pilots.items():
 s,ext,metrics[name]=waveform_metrics(p,data,rho=.5,c1=system.c1,c2=system.c2,prefix_length=102,papr_limit_db=12.,peak_power_limit=16.)
 np.testing.assert_allclose(transform(s,system.c1,system.c2),np.sqrt(.5)*p+data,rtol=1e-12,atol=1e-12)
raw=P/'evidence/frozen-pilots-v1.npz'
with raw.open('xb') as f:np.savez_compressed(f,**pilots)
result=dict(status='pilots_frozen_geometry_only',protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
 pilot_npz_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),geometry=dict(N=1024,l_max=102,k_max=2,c1=system.c1,c2=system.c2),selection=details,
 engineering_waveform_metrics=metrics,scope='one fixed synthetic QPSK vector; no channel/receiver/FER used for selection; full-block power gates still required',
 physical_model='G0 unchanged; explicit CPP fractional propagation belongs to separately labelled G1')
with (P/'evidence/frozen-pilots-v1.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(selected=details['selected_index'],coherences=[r['max_coherence'] for r in details['candidates']],power=metrics)))
