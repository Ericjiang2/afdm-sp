# 场景 U 真时延分布（只看真值，不看任何臂的结果）
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'../../..'))
sys.path.insert(0,os.path.join(ROOT,'experiments/data_pilot_fer_20261121')); os.chdir(os.path.join(ROOT,'experiments/data_pilot_fer_20261121'))
import numpy as np, stageA
C=stageA.setup(); st,ctx=C['stage3'],C['ctx']
L=[];P=[];R=[]
for rho in (100,150):
  for fr in range(49000,49040):
    b=st.inputs(ctx,fr,'U',rho); raw,obs,tr=st.observed(ctx,b,rho,450)
    l=np.asarray(tr['l_i'],int); g=np.abs(np.asarray(tr['g_i']))**2; rel=g>=.5*float(obs['sigma2'])
    L+=list(l); P+=list(g/g.sum()); R+=list(l[rel])
L=np.array(L);R=np.array(R)
print('npaths',len(L),'delay q',np.quantile(L,[0,.1,.5,.9,.99,1]),'rel q',np.quantile(R,[0,.5,.9,1]),'frac>50',np.mean(L>50),'rel>50',np.mean(R>50))
