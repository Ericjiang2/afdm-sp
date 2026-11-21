import sys,types,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from physical import fit
old=types.ModuleType('old_physical');sys.modules[old.__name__]=old
exec((ROOT/'results/physical_pre_cache.py.txt').read_text(),old.__dict__)
rng=np.random.default_rng(312057);rows=[]
for n in (32,65):
 p=.5*np.exp(1j*rng.random(n));mu=.2*(rng.normal(size=n)+1j*rng.normal(size=n));v=np.maximum(.5-abs(mu)**2,0);y=rng.normal(size=n)+1j*rng.normal(size=n)
 for soft in (False,True):
  args=(y,p,mu,v,[0,0,1,2],[0,1,-1,1],[.6,.2,.4j,.3],3/(2*n),.71/n**2,.2)
  x=fit(*args,use_variance=soft);z=old.fit(*args,use_variance=soft)
  e=max(float(np.max(abs(x[k]-z[k]))) for k in ('dopplers','gains','gamma'))
  assert e<2e-8,(n,soft,e)
  rows.append(dict(n=n,soft=soft,max_error=e,same_calls=x['evaluations']==z['evaluations']))
(ROOT/'results/cache_equivalence.json').write_text(json.dumps(rows,indent=2));print(rows)
