import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,time
from coherence_reference import Physics,receive,ToyCode,moments
rng=np.random.default_rng(233002);n=64;code=ToyCode(n);pd=.5;sigma2=10**(-6/10)
rows=[];t0=time.perf_counter()
for regime in ['distinct','coherent']:
 delays=[3,9,17,37] if regime=='distinct' else [3,3,17,37]
 p=Physics(n,delays,[.41,.46,-.7,1.4],3.7/(2*n),.017)
 U=p.dense();R=p.R
 for frame in range(240):
  c=code.encode(rng.integers(0,2,n));d=.5*((1-2*c[:n])+1j*(1-2*c[n:]))
  pilot=np.sqrt(.5)*np.exp(2j*np.pi*np.arange(n)**2*7/n)
  ht=(rng.normal(size=4)+1j*rng.normal(size=4));ht/=np.linalg.norm(ht)
  y=p.apply(ht,pilot+d)+np.sqrt(sigma2/2)*(rng.normal(size=n)+1j*rng.normal(size=n))
  Y=p.daft(y,True);B=p.response_t(p.daft(pilot,True))
  h0=np.linalg.solve(B.conj().T@B+pd*n*R+sigma2*np.eye(4),B.conj().T@Y)
  initial=receive(p,y,pilot,h0,sigma2,mode='scalar');dec0=code.decode(initial['extrinsic'])
  L=np.clip(dec0['extrinsic'],-20,20);mu,v=moments(np.clip(dec0['app'],-20,20))
  B=p.response_t(p.daft(pilot+mu,True));G=np.einsum('imk,jmk,k->ij',U.conj(),U,v)
  hf=np.linalg.solve(B.conj().T@B+G+sigma2*np.eye(4),B.conj().T@Y)
  res={}
  for mode in ['scalar','reaction','group','full']:
   start=time.perf_counter();out=receive(p,y,pilot,hf,sigma2,L,mode=mode);dec=code.decode(out['extrinsic'])
   dh=out['gains']-ht;nmse=np.vdot(dh,R@dh).real/np.vdot(ht,R@ht).real
   res[mode]=dict(word_error=int(np.any(dec['hard']!=c)),bit_errors=int(np.sum(dec['hard']!=c)),
      info_errors=int(np.sum(dec['hard'][:n]!=c[:n])),syndrome=int(np.sum((code.H@dec['hard'])%2)),
      nmse=float(nmse),seconds=time.perf_counter()-start)
  rows.append(dict(regime=regime,frame=frame,initial_error=int(np.any(dec0['hard']!=c)),
      physical_power=float(np.vdot(ht,R@ht).real),results=res))
  if frame%40==39:
   sub=[r for r in rows if r['regime']==regime]
   print(regime,frame+1,{m:sum(r['results'][m]['word_error'] for r in sub) for m in res},flush=True)
Path(__file__).with_name('toy_receiver_rows.json').write_text(json.dumps(rows,indent=2))
summary={}
for regime in ['distinct','coherent']:
 sub=[r for r in rows if r['regime']==regime];o={}
 for mode in ['scalar','reaction','group','full']:
  x=[r['results'][mode] for r in sub]
  o[mode]=dict(errors=sum(z['word_error'] for z in x),bit_errors=sum(z['bit_errors'] for z in x),
    median_nmse=float(np.median([z['nmse'] for z in x])),
    rescues_vs_scalar=sum(r['results']['scalar']['word_error'] and not r['results'][mode]['word_error'] for r in sub),
    harms_vs_scalar=sum(not r['results']['scalar']['word_error'] and r['results'][mode]['word_error'] for r in sub),
    median_seconds=float(np.median([z['seconds'] for z in x])))
 summary[regime]=dict(n=len(sub),methods=o)
Path(__file__).with_name('toy_receiver_summary.json').write_text(json.dumps(summary,indent=2))
print(summary);print('seconds',time.perf_counter()-t0)
