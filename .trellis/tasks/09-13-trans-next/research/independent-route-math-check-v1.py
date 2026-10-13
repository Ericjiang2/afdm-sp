"""Deterministic matrix checks of the supplied review; no channel/receiver runs."""
from pathlib import Path
import hashlib
import json
import time
import numpy as np

started=time.perf_counter()
n=1024;a=5;c1=a/(2*n);c2=(np.sqrt(2)-1)/(2*n*n)
x=np.arange(n);pilot=np.exp(-1j*np.pi*7*x*x/n)
rows=[]
for width in (2,4):
 ids=[(l,q) for l in range(103) for q in range(-width,width+1)]
 labels={(34*l+7*q)%n for l,q in ids}
 cols=[];control=[]
 for l,q in ids:
  source=(x-a*l-q)%n
  phi=np.exp(2j*np.pi*(-c1*l*l+c2*(x*x-source*source)-l*source/n))*pilot[source]
  phi0=np.exp(2j*np.pi*(-c1*l*l-l*source/n))*pilot[source]
  analytic=pilot*np.exp(2j*np.pi*((a*7-1)*l+7*q)*x/n)
  np.testing.assert_allclose(phi0/phi0[0],analytic/analytic[0],rtol=0,atol=2e-11)
  cols.append(phi);control.append(phi0)
 matrix=np.column_stack(cols)/np.sqrt(n)
 gram=np.abs(matrix.conj().T@matrix);np.fill_diagonal(gram,0)
 i,j=np.unravel_index(np.argmax(gram),gram.shape)
 rows.append(dict(q_max=width,columns=len(ids),c2_zero_distinct_labels=len(labels),
  actual_max_coherence=float(gram[i,j]),max_pair=[ids[i],ids[j]],
  norm_min=float(np.linalg.norm(matrix,axis=0).min()),norm_max=float(np.linalg.norm(matrix,axis=0).max())))
# Pure conditional nested-regression identity, verified by exact covariance/bias.
rng=np.random.default_rng(913);X=rng.normal(size=(12,3))+1j*rng.normal(size=(12,3));v=rng.normal(size=12)+1j*rng.normal(size=12)
B=np.column_stack((X,v));cross=np.linalg.lstsq(X,v,rcond=None)[0];gamma=float(np.linalg.norm(v-X@cross)**2)
z=.2+.1j
narrow=float(np.trace(np.linalg.inv(X.conj().T@X)).real+(1+np.linalg.norm(cross)**2)*abs(z)**2)
wide=float(np.trace(np.linalg.inv(B.conj().T@B)).real)
formula=float((1+np.linalg.norm(cross)**2)*(1/gamma-abs(z)**2))
assert abs(wide-narrow-formula)<1e-12
frequency=np.arange(n);coeff=np.fft.fft(np.exp(2j*np.pi*.5*frequency/n))/n
tails={str(w):float(1-np.sum(abs(coeff[np.arange(-w,w+1)%n])**2)) for w in (1,2,4,8)}
source=Path('/Users/guoyikun/Downloads/AFDM_SP_独立研究路线复核.md')
result=dict(scope='Public deterministic dictionary and algebra only; no physical random blocks, receiver, FER or confirmation',
 source_document_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 numpy=np.__version__,configuration=dict(N=n,a=a,c1=c1,c2=c2,root=7),pilot_gram=rows,half_integer_tails=tails,
 nested_regression=dict(exact_difference=wide-narrow,formula=formula,absolute_error=abs(wide-narrow-formula)),
 missing_evidence='Review QPSK seed and referenced E7 standalone raw are absent; its exact 0.082304 is not independently reproduced.',
 wall_seconds=time.perf_counter()-started)
with Path(__file__).with_suffix('.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
