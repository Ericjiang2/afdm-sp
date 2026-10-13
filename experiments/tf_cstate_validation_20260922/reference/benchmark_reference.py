"""Paired reference-kernel timings; no TF/LDPC or production latency claim."""
import json,time,platform,os
from pathlib import Path as FPath
import numpy as np
import scipy
from geometry_exchange_control import Path,idaft,responses,reopen_geometry
from structural_state import compact_exchange

rng=np.random.default_rng(8675309)
N=1024;P=8;L=102;c1=.137/N;c2=.003;noise=.22
p=np.sqrt(.5)*np.exp(2j*np.pi*rng.random(N))
d=.5*(rng.choice([-1,1],N)+1j*rng.choice([-1,1],N))
mu=.85*d;v=.5-np.abs(mu)**2;x=p+mu
truth=[Path(3,-.62),Path(3,.58),Path(14,-1.22),Path(25,.21),Path(37,.73),Path(51,1.01),Path(79,-.39),Path(95,.31)]
h=(rng.normal(size=P)+1j*rng.normal(size=P));h/=np.linalg.norm(h)
Y=responses(idaft(p+d,c1,c2),truth,c1)@h+np.sqrt(noise/2)*(rng.normal(size=N)+1j*rng.normal(size=N))
cur=[Path(3,-.41),Path(9,.21),Path(14,-1.1),Path(25,.08),Path(37,.58),Path(57,.1),Path(79,-.19),Path(95,.41)]
kw=dict(c1=c1,c2=c2,ridge=noise,max_delay=L,doppler_min=-3,doppler_max=3,grid_step=.25)

def direct():return reopen_geometry(Y,x,v,cur,**kw,max_edits=2,local_passes=0)
def compact():return compact_exchange(Y,x,v,cur,**kw,max_edits=2)
def local(ps):return reopen_geometry(Y,x,v,ps,**kw,max_edits=0,local_passes=2)

# Untimed warmup and state comparison.
a=direct();b=compact();assert a.paths==b['paths']
la=local(a.paths);lb=local(b['paths']);assert la.paths==lb.paths
assert np.max(abs(la.gains-lb.gains))<1e-10
rows=[]
for rep in range(7):
    pairs=(('direct',direct),('compact',compact)) if rep%2==0 else (('compact',compact),('direct',direct))
    for name,fn in pairs:
        tic=time.perf_counter();out=fn();elapsed=time.perf_counter()-tic
        ps=out.paths if name=='direct' else out['paths']
        tic=time.perf_counter();last=local(ps);lt=time.perf_counter()-tic
        assert ps==a.paths and last.paths==la.paths
        rows.append(dict(rep=rep,method=name,structural_seconds=elapsed,local_seconds=lt,
                         structural_plus_local_seconds=elapsed+lt))
summary={}
for name in ('direct','compact'):
    rr=[r for r in rows if r['method']==name]
    summary[name]={k:dict(mean=float(np.mean([r[k] for r in rr])),median=float(np.median([r[k] for r in rr])),
                          minimum=float(np.min([r[k] for r in rr])),maximum=float(np.max([r[k] for r in rr])))
                   for k in ('structural_seconds','local_seconds','structural_plus_local_seconds')}
out=dict(scope='Synthetic full-size reference checkpoint, not production. Warmed, one fixed observation, seven interleaved pairs. No TF, decoder or production serialization.',
         N=N,P=P,max_delay=L,grid_size=b['grid_size'],nontrivial_CPP=True,
         numpy=np.__version__,scipy=scipy.__version__,python=platform.python_version(),platform=platform.platform(),
         openblas_threads=os.environ.get('OPENBLAS_NUM_THREADS'),
         paths_equal=True,final_local_paths_equal=True,gain_max_diff=float(np.max(abs(la.gains-lb.gains))),
         exact_complex_field_entries=b['persistent_field_complex_entries'],
         field_calls=b['field_calls'],accepted_edits=len(b['edits']),summary=summary,rows=rows)
FPath(__file__).with_name('benchmark_results.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
