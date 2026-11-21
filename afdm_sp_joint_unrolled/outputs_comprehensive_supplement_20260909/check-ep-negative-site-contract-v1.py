"""Exact one-symbol calibration counterexample; no receiver or campaign rerun."""
import os
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import numpy as np,json,hashlib
from afdm_sp_joint_unrolled.supplement_detectors import detect,CONST
# Complex sigma=.2, |H|=1 -> each real cavity precision10. At y=0 all
# QPSK symbols are equiprobable: real variance=.25, proposed precision4-10=-6.
y=np.array([0j]);H=np.array([[1.+0j]]);sigma=.2
logp=-abs(y[0]-H[0,0]*CONST)**2/sigma;prob=np.exp(logp-logp.max());prob/=prob.sum()
mean=np.dot(prob,CONST);variance=float(np.dot(prob,abs(CONST-mean)**2))
a=detect(y,H,sigma,CONST,'stable-EP-20-d0.5',device='cpu')
b=detect(y,H,sigma,CONST,'stable-EP-20-d0.5',device='cpu',doubled=True)
for r in (a,b):
 np.testing.assert_allclose(r['mu'],[mean],atol=1e-14)
 np.testing.assert_allclose(r['var'],[variance],atol=1e-14)
 np.testing.assert_allclose(r['raw_llr'],[0.,0.],atol=1e-14)
 assert r['diagnostics']['trace'][-1]['rejected_sites']==2
 assert r['diagnostics']['fixed_point_residual']==0 and r['diagnostics']['converged'] is False
for k in ('mu','var','raw_llr'):np.testing.assert_array_equal(a[k],b[k])
r=dict(status='exact_counterexample_verified',scope='one-symbol finite enumeration; no full receiver/FER trial',
 exact_mean=[mean.real,mean.imag],exact_complex_variance=variance,cavity_precision=10.,proposed_site_precision=-6.,
 fixed_point_residual=0.,rejected_sites=2,declared_converged=False,doubled_arrays_equal=True,
 interpretation='zero rejected sites is an extra qualification restriction, not a necessary condition for exact marginals or numerical stationarity; current campaign gate remains unchanged',
 source_sha256=hashlib.sha256(Path('afdm_sp_joint_unrolled/supplement_detectors.py').read_bytes()).hexdigest())
p=Path('.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/ep-negative-site-contract-v1.json')
with p.open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
