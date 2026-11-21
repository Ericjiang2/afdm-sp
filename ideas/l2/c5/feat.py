import os,sys,json
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='1'
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'../../..'))
sys.path.insert(0,os.path.join(ROOT,'experiments/data_pilot_fer_20261121')); os.chdir(os.path.join(ROOT,'experiments/data_pilot_fer_20261121'))
import numpy as np, stageA
C=stageA.setup(); st,ctx=C['stage3'],C['ctx']
out=open(os.path.join(HERE,'feat.jsonl'),'w')
for rho in (100,150):
  for fr in range(43000,43060):
    b=st.inputs(ctx,fr,'U',rho); raw,obs,tr=st.observed(ctx,b,rho,450)
    l=np.asarray(tr['l_i'],int); nu=np.asarray(tr['k_real'],float); g=np.abs(np.asarray(tr['g_i']))**2; s2=float(obs['sigma2'])
    rel=g>=.5*s2; L=np.sort(l[rel]); n=int(rel.sum())
    gap=int(np.min(np.diff(L))) if n>1 else 99
    dd=[abs(nu[i]-nu[j]) for i in range(len(l)) for j in range(i+1,len(l)) if rel[i] and rel[j] and abs(l[i]-l[j])<=1]
    print(json.dumps(dict(rho=rho,frame=fr,gap=gap,weak=float(np.min(g[rel])/s2) if n else 0,ddop=float(min(dd)) if dd else 9.,nrel=n,npath=len(l))),file=out,flush=True)
