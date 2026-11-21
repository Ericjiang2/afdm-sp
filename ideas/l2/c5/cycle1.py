import os, sys, json, time
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'../../..'))
sys.path.insert(0, os.path.join(ROOT,'experiments/data_pilot_fer_20261121')); os.chdir(os.path.join(ROOT,'experiments/data_pilot_fer_20261121'))
import stageA
rho=int(sys.argv[1]); frames=range(int(sys.argv[2]), int(sys.argv[3])); out=sys.argv[4]
C=stageA.setup(); st,ctx=C['stage3'],C['ctx']
with open(out,'w') as fh:
    for fr in frames:
        b=st.inputs(ctx,fr,'U',rho); raw,obs,tr=st.observed(ctx,b,rho,450)
        t=time.process_time(); dec,arr,syn,_=stageA.f0(C,obs); tf0=time.process_time()-t
        rec=dict(frame=fr,rho=rho,syn=int(syn),f0_err=int(st.e1.gd.score(ctx,dec['decoded'],tr)),t_f0=tf0)
        if syn:
            t=time.process_time(); br=st.e1.run_branch(ctx,C['cd'],obs,arr,'A1'); rec['t_a1']=time.process_time()-t
            rec['a1_err']=int(st.e1.gd.score(ctx,br['decoder']['decoded'],tr))
            t=time.process_time(); b7=st.e1.run_a7(ctx,obs,arr); rec['t_a7']=time.process_time()-t
            rec['a7_err']=int(st.e1.gd.score(ctx,b7['decoder']['decoded'],tr))
        print(json.dumps(rec),file=fh,flush=True)
