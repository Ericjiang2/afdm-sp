import os, sys, json, time
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'../../..'))
sys.path.insert(0, os.path.join(ROOT,'experiments/data_pilot_fer_20261121')); os.chdir(os.path.join(ROOT,'experiments/data_pilot_fer_20261121'))
import numpy as np, stageA
rho=int(sys.argv[1]); frames=range(int(sys.argv[2]),int(sys.argv[3])); out=os.path.join(HERE,sys.argv[4])
C=stageA.setup(); st,ctx=C['stage3'],C['ctx']; orig=C['orig_front']; G=orig.__globals__
import torch
from physical import daft
from messages import moments
def grid_front(step,K,lo=-2.,rid='B0-p2-s0.5'):
    def front(observed,system,code):
        s=orig(observed,system,code); t=time.process_time()
        n=len(observed['y']); kk=np.arange(lo,2+1e-9,step); ls=np.repeat(np.arange(system.l_max_cap+1),len(kk)); ks=np.tile(kk,system.l_max_cap+1)
        A=G['Channel'](n,system.c1,system.c2,ls,ks,np.ones(len(ls))).regressors(observed['pilot'])
        est=G['BaselineInitializer'](rid,lstsq_driver='gels',dictionary_limit=len(ls))
        g,ids=est(torch.tensor(observed['y'],dtype=torch.complex64),torch.tensor(A,dtype=torch.complex64),K,float(observed['sigma2']))
        ids=np.asarray(ids,int); front.sec=time.process_time()-t
        return dict(s,delays=ls[ids],dopplers=ks[ids].astype(float),gains=g.detach().cpu().numpy()[ids].copy())
    return front
def make_reopen(base):
  def reopen_front(observed,system,code):
    s=base(observed,system,code); t=time.process_time(); n=len(observed['y'])
    mu,v,_=moments(np.zeros(2*n),1-system.rho)
    init=[C['cd'].Path(int(d),float(k)) for d,k in zip(s['delays'],s['dopplers'])]
    Y=daft(observed['y'],system.c1,system.c2,True)
    r=C['cd'].reopen_geometry(Y,observed['pilot']+mu,v,init,c1=system.c1,c2=system.c2,ridge=float(observed['sigma2']),
        max_delay=system.l_max_cap,doppler_min=-3.,doppler_max=3.,grid_step=.25,max_edits=2,chunk_size=64,local_passes=2,local_halfwidth=.75,
        local_max_evals=16,duplicate_tolerance=1e-6,top_k=20,strategy='compact',gamma_mode='full')
    reopen_front.sec=time.process_time()-t+getattr(base,'sec',0.)
    return dict(s,delays=np.array([p.delay for p in r.paths],int),dopplers=np.array([p.doppler for p in r.paths],float),gains=np.asarray(r.gains,complex))
  return reopen_front
def int_front(rid):
    f=grid_front(1.,40,rid=rid); return f
ALL=dict(n40=int_front('B0-p3-s0.5'),g25n40=grid_front(.25,40,rid='B0-p3-s0.5'),pos25=grid_front(.25,40,lo=0.),base=None,g50=grid_front(.5,40),g25=grid_front(.25,40),r0re=make_reopen(orig),g50re=make_reopen(grid_front(.5,40)))
ARMS={k:ALL[k] for k in (sys.argv[5].split(',') if len(sys.argv)>5 else ALL)}
def run_arm(obs,tr,fr):
    ctx.native.pilot_front=fr if fr is not None else orig
    try:
        t=time.process_time(); dec,arr,syn,_=st.e1.f0_state(ctx,obs); tf=time.process_time()-t
    finally: ctx.native.pilot_front=orig
    rec=dict(syn=int(syn),f0_err=int(st.e1.gd.score(ctx,dec['decoded'],tr)),t=tf,tfront=getattr(fr,'sec',0.) if fr else 0.)
    if syn:
        br=st.e1.run_branch(ctx,C['cd'],obs,arr,'A1'); rec['a1_err']=int(st.e1.gd.score(ctx,br['decoder']['decoded'],tr))
    else: rec['a1_err']=rec['f0_err']
    return rec
with open(out,'w') as fh:
    for f in frames:
        b=st.inputs(ctx,f,'U',rho); raw,obs,tr=st.observed(ctx,b,rho,450)
        l=np.asarray(tr['l_i'],int); nu=np.asarray(tr['k_real'],float); g=np.abs(np.asarray(tr['g_i']))**2; rel=g>=.5*float(obs['sigma2'])
        m=float(np.sum(g[rel]*np.abs(nu[rel]-np.round(nu[rel])))/max(np.sum(g[rel]),1e-30))
        row=dict(frame=f,rho=rho,m=m,nrel=int(rel.sum()))
        for k,fr in ARMS.items():
            try: row[k]=run_arm(obs,tr,fr)
            except Exception as e: row[k]=dict(error=repr(e)[:200])
        print(json.dumps(row),file=fh,flush=True)
