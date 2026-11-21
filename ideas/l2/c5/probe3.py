import os,sys,json,inspect
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'../../..'))
sys.path.insert(0,os.path.join(ROOT,'experiments/data_pilot_fer_20261121')); os.chdir(os.path.join(ROOT,'experiments/data_pilot_fer_20261121'))
import numpy as np, stageA
C=stageA.setup(); st,ctx=C['stage3'],C['ctx']; s=ctx.system
print('l_max_cap',s.l_max_cap,'N',len(s._zc_seq),'rho attr',getattr(s,'rho',None))
r=ctx.native.receive; print('receive',r, getattr(r,'__wrapped__',None))
try: print(inspect.signature(r)); print(inspect.getsource(r)[:1500])
except Exception as e: print('src err',e)
ks=[];frac=[]
for rho in (100,150):
  for fr in range(47000,47040):
    b=st.inputs(ctx,fr,'U',rho); raw,obs,tr=st.observed(ctx,b,rho,450)
    nu=np.asarray(tr['k_real'],float); ks+=list(nu)
ks=np.array(ks); print('npaths',len(ks),'at|2.0|',np.mean(np.isclose(np.abs(ks),2.0)),'integer',np.mean(np.isclose(ks,np.round(ks))),'sign+',np.mean(ks>0),'quantiles',np.round(np.quantile(ks,[0,.1,.25,.5,.75,.9,1]),3))
