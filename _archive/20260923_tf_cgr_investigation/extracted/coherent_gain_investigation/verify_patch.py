import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import sys,importlib.util,tempfile,json
import numpy as np
from coherence_reference import Physics,receive
from make_production_variant import make
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'frozen_reference/baseline/src'))
from physical import Channel
checks=[];rng=np.random.default_rng(233005)
with tempfile.TemporaryDirectory() as temp:
 mods={}
 for mode in ['reaction','sham']:
  dest=Path(temp)/(mode+'.py');make(root/'frozen_reference/native/src/twofft.py',dest,mode)
  spec=importlib.util.spec_from_file_location('verified_'+mode,dest);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mods[mode]=mod
 for n in [17,64,128]:
  for delays in [[1,3,7],[3,3,7]]:
   phys=Physics(n,delays,[.2,.25,-.7],3.7/(2*n),.017)
   h=(rng.normal(size=3)+1j*rng.normal(size=3))/3
   c=Channel(n,phys.c1,phys.c2,delays,phys.dopplers,h)
   p=np.sqrt(.5)*np.exp(1j*rng.uniform(-3,3,n));y=rng.normal(size=n)+1j*rng.normal(size=n);L=rng.normal(size=2*n)
   for mode in mods:
    ref=receive(phys,y,p,h,.25,L,mode=mode)
    out=mods[mode].scalar_joint(y,p,c,.25,prior=L)
    err=max(np.max(abs(ref[q]-out[q])) for q in ['extrinsic','app','gains','mu'])
    assert err<1e-9,(n,mode,err)
    checks.append(dict(n=n,delays=delays,mode=mode,max_error=float(err)))
(root/'patch_qualification.json').write_text(json.dumps(checks,indent=2))
print(len(checks),'patch qualifications; max error',max(c['max_error'] for c in checks))
