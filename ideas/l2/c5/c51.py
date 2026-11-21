import os, sys, json
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'../../..'))
sys.path.insert(0, os.path.join(ROOT,'experiments/data_pilot_fer_20261121')); os.chdir(os.path.join(ROOT,'experiments/data_pilot_fer_20261121'))
import stageA
rho=int(sys.argv[1]); out=os.path.join(HERE,sys.argv[2])
C=stageA.setup(); st,ctx=C['stage3'],C['ctx']; cd=C['cd']
class Proxy:
    def __init__(s,**ov): s.ov=ov
    def __getattr__(s,k): return getattr(cd,k)
    def reopen_geometry(s,*a,**k): k.update(s.ov); return cd.reopen_geometry(*a,**k)
V=dict(A1=cd,A1g1L=Proxy(grid_step=1.0),A1g1=Proxy(grid_step=1.0,local_passes=0))
with open(out,'w') as fh:
    for f in range(int(sys.argv[3]),int(sys.argv[4])):
        b=st.inputs(ctx,f,'U',rho); raw,obs,tr=st.observed(ctx,b,rho,450)
        dec,arr,syn,_=stageA.f0(C,obs)
        if not syn: continue
        row=dict(frame=f,rho=rho,syn=int(syn))
        for k,kv in V.items():
            try: row[k]=int(st.e1.gd.score(ctx,st.e1.run_branch(ctx,kv,obs,arr,'A1')['decoder']['decoded'],tr))
            except Exception as e: row[k]=repr(e)[:150]
        print(json.dumps(row),file=fh,flush=True)
