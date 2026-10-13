"""Deterministic algebra checks, no channel or receiver simulation."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
R=Path(__file__).parent
sources={}
def extract(relative,names):
 p=ROOT/relative;sources[relative]=hashlib.sha256(p.read_bytes()).hexdigest()
 tree=ast.parse(p.read_text());nodes=[x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name in names]
 assert len(nodes)==len(names)
 env={'np':np};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),env)
 return env
npimpl=extract('afdm_sp_joint_unrolled/afdm_baselines.py',{'construct_sensing_matrix'})
qing=extract('afdm_sp_joint_unrolled/qing_baseline/qing_sp_afdm.py',{'qing_pilot'})
transform=extract('afdm_sp_joint_unrolled/supplement_pilots.py',{'_vector','transform'})['transform']
N=1024;lmax=102;kmax=2;D=(lmax+1)*(2*kmax+1);energy=512.
c1=(2*kmax+1)/(2*N);c2=(np.sqrt(2)-1)/(2*N*N)
spike,Q=qing['qing_pilot'](N,kmax,lmax,0,np.sqrt(energy))
try:qing['qing_pilot'](N,kmax,lmax,1,np.sqrt(energy))
except ValueError:two_pilots_rejected=True
else:raise AssertionError('two pilots should violate current spacing')
n=np.arange(N)
p0=np.sqrt(.5)*np.exp(-1j*np.pi*7*n*n/N)
p1=np.sqrt(.5)*np.exp(2j*np.pi*np.random.default_rng([20260909,501,2]).random(N))
p2=np.sqrt(.5)*np.exp(2j*np.pi*np.random.default_rng([20260909,502,0]).random(N))
metrics={}
for label,p in [('p0',p0),('p1',p1),('p2',p2),('zheng_single',spike)]:
 phi=npimpl['construct_sensing_matrix'](N,p,c1,c2,lmax,kmax)
 g=phi.conj().T@phi/energy
 eig=np.linalg.eigvalsh(g)
 off=g.copy();np.fill_diagonal(off,0)
 timepilot=transform(p,c1,c2,inverse=True)
 metrics[label]=dict(pilot_energy=float(np.vdot(p,p).real),max_coherence=float(abs(off).max()),min_eigenvalue=float(eig[0]),max_eigenvalue=float(eig[-1]),gram_condition=float(eig[-1]/eig[0]),normalized_trace_inverse=float(np.sum(1/eig)/D),pilot_only_time_papr_db=float(10*np.log10(np.max(abs(timepilot)**2)/np.mean(abs(timepilot)**2))))
 if label=='zheng_single':np.testing.assert_allclose(g,np.eye(D),rtol=1e-12,atol=1e-12)
# Fixed diagonal prior: inverse-diagonal/Schur bound, no high-pilot approximation.
g0=np.eye(3);g=np.array([[1,.3,.1],[.3,1,.2],[.1,.2,1.]])
prior=np.diag([1.,2.,4.]);J=2*g+prior;bound=float(np.sum(1/np.diag(J)))
assert np.trace(np.linalg.inv(J))>=bound and np.isclose(np.trace(np.linalg.inv(2*g0+prior)),bound)
# E[AA^H]=2I alone does not imply E[A B A^H] is white.
U=np.diag([1.,-1.]);H=np.eye(2)+U
conditional=H@H.T;white_assumption=2*np.eye(2)
assert not np.allclose(conditional,white_assumption)
report=dict(status='PASS',scope='deterministic operator/Gram algebra only; no BER, F, decoder, channel samples, or changed production files',source_sha256=sources,N=N,D=D,Q=Q,maximum_equally_spaced_pilots=N//D,two_pilots_rejected=two_pilots_rejected,metrics=metrics,diagonal_prior_trace_inverse=dict(actual=float(np.trace(np.linalg.inv(J))),lower_bound=bound,orthogonal_attains_bound=True),conditional_covariance_counterexample=dict(H=H.tolist(),actual=conditional.tolist(),incorrect_scalar=white_assumption.tolist()))
with (R/'zheng-pilot-algebra-v1-results.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
