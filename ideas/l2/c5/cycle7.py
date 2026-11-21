import os, sys, json, time
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'../../..'))
sys.path.insert(0, os.path.join(ROOT,'experiments/data_pilot_fer_20261121')); os.chdir(os.path.join(ROOT,'experiments/data_pilot_fer_20261121'))
import numpy as np, stageA
SNR=int(sys.argv[6]) if len(sys.argv)>6 else 450
SC=sys.argv[7] if len(sys.argv)>7 else 'U'
rho=int(sys.argv[1]); frames=range(int(sys.argv[2]),int(sys.argv[3])); out=os.path.join(HERE,sys.argv[4])
C=stageA.setup(); st,ctx=C['stage3'],C['ctx']; orig=C['orig_front']; G=orig.__globals__
import torch
from physical import daft
from messages import moments
def omp(observed,system,ls,ks,K,rid):
    A=G['Channel'](len(observed['y']),system.c1,system.c2,ls,ks,np.ones(len(ls))).regressors(observed['pilot'])
    est=G['BaselineInitializer'](rid,lstsq_driver='gels',dictionary_limit=len(ls))
    g,ids=est(torch.tensor(observed['y'],dtype=torch.complex64),torch.tensor(A,dtype=torch.complex64),K,float(observed['sigma2']))
    ids=np.asarray(ids,int); return ls[ids],ks[ids].astype(float),g.detach().cpu().numpy()[ids].copy()
def kk_front(kkf,rid='B0-p2-s0.5'):
    # kkf(s) -> 每个时延的多普勒候选；s 为生产前端输出（时间计入）
    def front(observed,system,code):
        t=time.process_time(); s=orig(observed,system,code); kk=np.asarray(kkf(s),float)
        ls=np.repeat(np.arange(system.l_max_cap+1),len(kk)); ks=np.tile(kk,system.l_max_cap+1)
        d,k,g=omp(observed,system,ls,ks,40,rid); front.sec=time.process_time()-t; front.last=kk
        return dict(s,delays=d,dopplers=k,gains=g)
    return front
def chat(s):
    w=np.abs(np.asarray(s['gains']))**2; return np.round(4*np.sum(w*np.asarray(s['dopplers'],float))/max(w.sum(),1e-30))/4
def loc_front(observed,system,code):
    t=time.process_time(); s=orig(observed,system,code)
    for off in ((-.5,-.25,0.,.25,.5),(-1.,-.75,-.5,-.25,0.,.25,.5,.75,1.)):
        P=sorted({(int(d),float(k)+o) for d,k in zip(s['delays'],s['dopplers']) for o in off})
        if len(P)>=40: break
    ls=np.array([p[0] for p in P],int); ks=np.array([p[1] for p in P],float)
    d,k,g=omp(observed,system,ls,ks,40,'B0-p2-s0.5'); loc_front.sec=time.process_time()-t
    return dict(s,delays=d,dopplers=k,gains=g)
def corrmap(observed,system):
    L=system.l_max_cap+1; ls=np.repeat(np.arange(L),5); ks=np.tile(np.arange(-2,3),L).astype(float)
    A=G['Channel'](len(observed['y']),system.c1,system.c2,ls,ks,np.ones(len(ls))).regressors(observed['pilot'])
    A=A/np.linalg.norm(A,axis=0,keepdims=True); return (np.abs(A.conj().T@observed['y'])**2).reshape(L,5)
FINE=np.arange(-2,2+1e-9,.25)
def emap_front(observed,system,code):
    t=time.process_time(); s=orig(observed,system,code); E=corrmap(observed,system).sum(0)
    top=set((np.argsort(E)[-3:]-2).tolist()); kk=np.array([k for k in FINE if int(np.floor(k+.5)) in top])
    ls=np.repeat(np.arange(system.l_max_cap+1),len(kk)); ks=np.tile(kk,system.l_max_cap+1)
    d,k,g=omp(observed,system,ls,ks,40,'B0-p2-s0.5'); emap_front.sec=time.process_time()-t
    return dict(s,delays=d,dopplers=k,gains=g)
def dmap_front(observed,system,code):
    t=time.process_time(); s=orig(observed,system,code); D=corrmap(observed,system).max(1)
    keep=np.sort(np.argsort(D)[-52:]); ls=np.repeat(keep,len(FINE)); ks=np.tile(FINE,len(keep))
    d,k,g=omp(observed,system,ls,ks,40,'B0-p2-s0.5'); dmap_front.sec=time.process_time()-t
    return dict(s,delays=d,dopplers=k,gains=g)
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
def omp_guard(y,Phi,K,mu):
    Pn=Phi/torch.linalg.vector_norm(Phi,dim=0,keepdim=True); PH=Phi.conj().T; r=y.clone(); sup=[]; ban=torch.zeros(Phi.shape[1],dtype=torch.bool)
    for _ in range(K):
        c=(PH@r).abs(); c[sup]=0.; c[ban]=0.; j=int(torch.argmax(c).item()); sup.append(j)
        if mu<1: ban|=(Pn.conj().T@Pn[:,j]).abs()>mu
        sol=torch.linalg.lstsq(Phi[:,sup],y.unsqueeze(-1),driver='gels').solution.squeeze(-1); r=y-Phi[:,sup]@sol
    return np.asarray(sup,int),sol.detach().cpu().numpy()
def guard_front(mu,step=.25):
    def front(observed,system,code):
        s=orig(observed,system,code); t=time.process_time(); n=len(observed['y'])
        kk=np.arange(-2,2+1e-9,step); ls=np.repeat(np.arange(system.l_max_cap+1),len(kk)); ks=np.tile(kk,system.l_max_cap+1)
        A=G['Channel'](n,system.c1,system.c2,ls,ks,np.ones(len(ls))).regressors(observed['pilot'])
        ids,g=omp_guard(torch.tensor(observed['y'],dtype=torch.complex64),torch.tensor(A,dtype=torch.complex64),24,mu)
        front.sec=time.process_time()-t; return dict(s,delays=ls[ids],dopplers=ks[ids].astype(float),gains=g)
    return front
def di52_front(observed,system,code):
    t=time.process_time(); s=orig(observed,system,code); D=corrmap(observed,system).max(1)
    keep=np.sort(np.argsort(D)[-52:]); kk=np.arange(-2.,3.); ls=np.repeat(keep,5); ks=np.tile(kk,len(keep))
    d,k,g=omp(observed,system,ls,ks,40,'B0-p2-s0.5'); di52_front.sec=time.process_time()-t
    return dict(s,delays=d,dopplers=k,gains=g)
def off_front(observed,system,code):
    t=time.process_time(); s=orig(observed,system,code); kk=np.arange(-1.875,1.875+1e-9,.25)
    ls=np.repeat(np.arange(system.l_max_cap+1),len(kk)); ks=np.tile(kk,system.l_max_cap+1)
    d,k,g=omp(observed,system,ls,ks,40,'B0-p2-s0.5'); off_front.sec=time.process_time()-t
    return dict(s,delays=d,dopplers=k,gains=g)
ALL=dict(rdg=grid_front(.25,40,rid='ridge-p2-s0.5'),sbl=grid_front(.25,40,rid='SBL-p2-s0.5'),g125=grid_front(.125,40),di52=di52_front,g25off=off_front,cg90=guard_front(.9),g25my=guard_front(1.01),w13=kk_front(lambda s:np.arange(-1,2+1e-9,.25)),i4=kk_front(lambda s:[-1.,0.,1.,2.]),emap=emap_front,dmap=dmap_front,a1w='A1W',adapt=kk_front(lambda s:np.arange(chat(s)-1,chat(s)+1+1e-9,.25)),n16=int_front('B0-p1-s0.5'),g25n16=grid_front(.25,40,rid='B0-p1-s0.5'),
  pos1=kk_front(lambda s:[0.,1.,2.]),loc=loc_front,int24=int_front('B0-p2-s0.5'),n40=int_front('B0-p3-s0.5'),g25n40=grid_front(.25,40,rid='B0-p3-s0.5'),pos25=grid_front(.25,40,lo=0.),base=None,g50=grid_front(.5,40),g25=grid_front(.25,40),r0re=make_reopen(orig),g50re=make_reopen(grid_front(.5,40)))
ARMS={k:ALL[k] for k in (sys.argv[5].split(',') if len(sys.argv)>5 else ALL)}
def run_arm(obs,tr,fr):
    a1w=isinstance(fr,str); fr=None if a1w else fr
    ctx.native.pilot_front=fr if fr is not None else orig
    try:
        t=time.process_time(); dec,arr,syn,_=st.e1.f0_state(ctx,obs); tf=time.process_time()-t
    finally: ctx.native.pilot_front=orig
    rec=dict(syn=int(syn),f0_err=int(st.e1.gd.score(ctx,dec['decoded'],tr)),t=tf,tfront=getattr(fr,'sec',0.) if fr else 0.)
    if syn:
        if a1w:
            kd=np.asarray(arr['r1_dopplers'],float); lo,hi=min(-2.,kd.min()),max(2.,kd.max()); o=C['cd'].reopen_geometry
            def w(*a,**k): k['doppler_min']=lo; k['doppler_max']=hi; return o(*a,**k)
            C['cd'].reopen_geometry=w
            try: br=st.e1.run_branch(ctx,C['cd'],obs,arr,'A1')
            finally: C['cd'].reopen_geometry=o
            rec['a1w_win']=[lo,hi]
        else: br=st.e1.run_branch(ctx,C['cd'],obs,arr,'A1')
        rec['a1_err']=int(st.e1.gd.score(ctx,br['decoder']['decoded'],tr)); rec['a1_syn']=int(ctx.hd.syndrome_weight(ctx,br['decoder']['decoded']))
    else: rec['a1_err']=rec['f0_err']; rec['a1_syn']=0
    return rec
with open(out,'w') as fh:
    for f in frames:
        b=st.inputs(ctx,f,SC,rho); raw,obs,tr=st.observed(ctx,b,rho,SNR)
        l=np.asarray(tr['l_i'],int); nu=np.asarray(tr['k_real'],float); g=np.abs(np.asarray(tr['g_i']))**2; rel=g>=.5*float(obs['sigma2'])
        m=float(np.sum(g[rel]*np.abs(nu[rel]-np.round(nu[rel])))/max(np.sum(g[rel]),1e-30))
        row=dict(frame=f,rho=rho,snr=SNR,sc=SC,m=m,nrel=int(rel.sum()))
        if 'adapt' in ARMS: row['chat']=float(chat(orig(obs,ctx.system,ctx.code)))
        for k,fr in ARMS.items():
            try: row[k]=run_arm(obs,tr,fr)
            except Exception as e: row[k]=dict(error=repr(e)[:200])
        print(json.dumps(row),file=fh,flush=True)
