import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,numpy as np,json,time
from coherence_reference import Physics,receive,moments
root=Path(__file__).resolve().parent/'frozen_reference/baseline'
sys.path[:0]=[str(root/'src'),str(root/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled')]
from physical import projected_variance
from e1_ldpc import build_code,encode,decode_soft_messages
code=build_code();n=1024;noise=10**(-6.5/10);rows=[];t0=time.perf_counter()
for regime in ['triple']:
 delays=[3,3,3,23,37,65,83,101]
 phys=Physics(n,delays,[.41,.43,.46,-.65,1.4,-1.2,.15,1.8],3.7/(2*n),.017)
 k=np.arange(n);pilot=np.sqrt(.5)*np.exp(-1j*np.pi*k*k/n)
 for frame in range(128):
  rng=np.random.default_rng(233003000+frame)
  c=encode(code,rng.integers(0,2,code['k']));bits=c.astype(float)
  data=.5*((1-2*bits[:n])+1j*(1-2*bits[n:]))
  ht=rng.normal(size=8)+1j*rng.normal(size=8);ht/=np.linalg.norm(ht)
  y=phys.apply(ht,pilot+data)+np.sqrt(noise/2)*(rng.normal(size=n)+1j*rng.normal(size=n))
  Y=phys.daft(y,True);B=phys.response_t(phys.daft(pilot,True))
  h0=np.linalg.solve(B.conj().T@B+.5*n*phys.R+noise*np.eye(8),B.conj().T@Y)
  out0=receive(phys,y,pilot,h0,noise,mode='scalar')
  dec0=decode_soft_messages(code,np.clip(out0['extrinsic'],-20,20))
  prior=np.clip(dec0['raw_check_extrinsic'],-20,20)
  mu,v=moments(np.clip(dec0['raw_app'],-20,20))
  B=phys.response_t(phys.daft(pilot+mu,True))
  G=projected_variance(v,phys.delays,phys.dopplers,phys.c1)
  hf=np.linalg.solve(B.conj().T@B+G+noise*np.eye(8),B.conj().T@Y)
  res={}
  for mode in ['scalar','reaction','group','full']:
   start=time.perf_counter();o=receive(phys,y,pilot,hf,noise,prior=prior,mode=mode)
   de=decode_soft_messages(code,np.clip(o['extrinsic'],-20,20))
   d=o['gains']-ht
   res[mode]=dict(error=int(np.any(de['decoded'][code['free_cols']]!=c[code['free_cols']])),
      bit_errors=int(np.sum(de['decoded']!=c)),valid=bool(de['decode_ok']),
      nmse=float(np.vdot(d,phys.R@d).real/np.vdot(ht,phys.R@ht).real),seconds=time.perf_counter()-start)
  rows.append(dict(regime=regime,frame=frame,initial_error=int(np.any(dec0['decoded']!=c)),
      physical_power=float(np.vdot(ht,phys.R@ht).real),results=res))
  if frame%32==31:
   sub=[r for r in rows if r['regime']==regime]
   print(regime,frame+1,{m:sum(r['results'][m]['error'] for r in sub) for m in res},flush=True)
Path(__file__).with_name('triple_ldpc2048_rows.json').write_text(json.dumps(rows,indent=2))
summary={}
for regime in ['triple']:
 sub=[r for r in rows if r['regime']==regime];o={}
 for mode in ['scalar','reaction','group','full']:
  x=[r['results'][mode] for r in sub]
  o[mode]=dict(errors=sum(z['error'] for z in x),bit_errors=sum(z['bit_errors'] for z in x),
     median_nmse=float(np.median([z['nmse'] for z in x])),
     rescues=sum(r['results']['scalar']['error'] and not r['results'][mode]['error'] for r in sub),
     harms=sum(not r['results']['scalar']['error'] and r['results'][mode]['error'] for r in sub),
     valid_wrong=sum(z['valid'] and z['error'] for z in x),median_seconds=float(np.median([z['seconds'] for z in x])))
 summary[regime]=dict(n=len(sub),methods=o)
Path(__file__).with_name('triple_ldpc2048_summary.json').write_text(json.dumps(summary,indent=2))
print(summary);print('seconds',time.perf_counter()-t0)
