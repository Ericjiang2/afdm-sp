"""Small interleaved equivalent-operation benchmark. Not receiver FER evidence."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import sys,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from physical import Channel,sparse_apply
rng=np.random.default_rng(20260920801);rows=[]
for n in (256,1024):
 for P in (3,8):
  c=Channel(n,5/(2*n),.15/n**2,np.arange(P)*2,rng.uniform(-2,2,P),(rng.normal(size=P)+1j*rng.normal(size=P))/np.sqrt(2*P));v=rng.uniform(.001,.5,n);mu=rng.normal(size=n)+1j*rng.normal(size=n);M=24;k=np.arange(n)
  def fast():
   keep,E,tail,_=c.select(v,M);D=c.diagonals(keep);row=c.row_variance(v,keep);mean=c.apply(mu)
   return keep,E,D,row,mean
  def full():
   alld=c.diagonals(np.arange(n));H=np.empty((n,n),complex)
   for s in range(n):H[(k+s)%n,k]=alld[s]
   E=(abs(alld)**2)@v;keep=np.sort(np.lexsort((k,-E))[:M]);R=H.copy()
   for s in keep:R[(k+s)%n,k]=0
   return keep,E,alld[keep],abs(R)**2@v,H@mu
  cached_diags=c.diagonals(np.arange(n));cached_H=np.empty((n,n),complex)
  for shift in range(n):cached_H[(k+shift)%n,k]=cached_diags[shift]
  cached_abs2=abs(cached_H)**2;cached_diag_abs2=abs(cached_diags)**2
  def cached():
   E=cached_diag_abs2@v;keep=np.sort(np.lexsort((k,-E))[:M]);row=cached_abs2@v
   for shift in keep:row[(k+shift)%n]-=cached_diag_abs2[shift]*v
   return keep,E,cached_diags[keep],row,cached_H@mu
  aa=fast();bb=full();cc=cached();assert max(float(np.max(abs(a-b))) for a,b in zip(aa,cc))<1e-8
  errors=[float(np.max(abs(a-b))) for a,b in zip(aa,bb)];assert max(errors)<1e-8
  times={'fast':[],'full':[],'cached_dense':[]}
  for r in range(7):
   for name,fn in ([('fast',fast),('full',full),('cached_dense',cached)] if r%2 else [('cached_dense',cached),('full',full),('fast',fast)]):
    start=time.perf_counter();fn();times[name].append(time.perf_counter()-start)
  row=dict(N=n,P=P,errors=errors,seconds=times,median={name:float(np.median(t)) for name,t in times.items()});rows.append(row);print(row['N'],row['P'],row['median'],flush=True)
(ROOT/'results'/'kernel_benchmark.json').write_text(json.dumps(rows,indent=2))
