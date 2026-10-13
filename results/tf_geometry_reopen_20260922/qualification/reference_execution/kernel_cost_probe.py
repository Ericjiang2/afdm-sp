"""Synthetic implementation-feasibility timing, NOT production latency."""
import json,platform
from pathlib import Path as FilePath
from dataclasses import asdict
import numpy as np
from geometry_exchange import Path,idaft,responses,reopen_geometry
rng=np.random.default_rng(552209);N=1024;c1=.037;c2=.011
p=np.exp(2j*np.pi*rng.random(N))/np.sqrt(2)
d=.5*(rng.choice([-1,1],N)+1j*rng.choice([-1,1],N))
x=p+.7*d;v=np.full(N,.5*(1-.7**2))
true=[Path(4,.31),Path(12,-.68),Path(12,.49),Path(23,1.31),Path(51,-1.21),Path(69,.72),Path(89,-.91),Path(101,1.45)]
h=(rng.normal(size=8)+1j*rng.normal(size=8))/4
Y=responses(idaft(p+d,c1,c2),true,c1)@h+np.sqrt(.22/2)*(rng.normal(size=N)+1j*rng.normal(size=N))
start=[Path(4,.3),Path(12,-.7),Path(23,1.3),Path(51,-1.2),Path(69,.7),Path(89,-.9),Path(92,.2),Path(101,1.5)]
res=[]
for rep in range(4):
    order=[0,2] if rep%2==0 else [2,0]
    for edits in order:
        r=reopen_geometry(Y,x,v,start,c1=c1,c2=c2,ridge=.22,max_delay=102,max_edits=edits)
        if rep:res.append(dict(repeat=rep,max_edits=edits,seconds=r.elapsed_seconds,evaluations=r.evaluations,actual_edits=len(r.edits),objective=r.objective_after))
out=dict(scope='synthetic kernel only; no acquisition, TF batch, LDPC, source parity, or production hardware match',platform=platform.platform(),N=N,P=8,records=res)
FilePath(__file__).with_name('kernel_cost_probe_results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
