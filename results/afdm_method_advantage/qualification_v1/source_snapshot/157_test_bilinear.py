from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from physical import Channel
from bilinear import operators,pbigabp
rng=np.random.default_rng(20260920773);records=[]
for n in (8,32):
 c=Channel(n,3/(2*n),.2/n**2,[0,2],[.31,-.22],[.8,.2j]);U=operators(c);x=rng.normal(size=n)+1j*rng.normal(size=n)
 err=float(np.max(abs(np.einsum('p,pnk,k->n',c.gains,U,x)-c.apply(x))));assert err<1e-10
 a=.5*np.array([1+1j,1-1j,-1+1j,-1-1j]);d=a[rng.integers(0,4,n)];pilot=.4*np.ones(n);y=c.apply(pilot+d)+.03*(rng.normal(size=n)+1j*rng.normal(size=n))
 o=pbigabp(y,pilot,c,.002,prior=np.zeros(2*n),iterations=3)
 assert np.isfinite(o['extrinsic']).all() and np.all(o['variance']>=0) and np.all(o['gain_variance']>0)
 records.append(dict(n=n,operator_error=err,finite=True,iterations=3,scope='numerical smoke, not performance evidence'))
Path(__file__).resolve().parents[1].joinpath('results/bilinear_tests.json').write_text(json.dumps(records,indent=2));print('PASS bilinear operator and finite-output smoke')
