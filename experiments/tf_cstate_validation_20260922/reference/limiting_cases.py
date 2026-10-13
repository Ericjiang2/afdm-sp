"""Boundary/failure cases for the compact fixed-q calculation."""
import json
from pathlib import Path as FPath
import numpy as np
from geometry_exchange_control import Path,idaft,responses,system,gamma_cross,reopen_geometry
from structural_state import CPPField,state_from_gram,exchange_scores,compact_exchange
rng=np.random.default_rng(123456)
rows=[]
for name,N,ps,var,ridge in [
    ('known_waveform_same_delay',64,[Path(1,.2),Path(1,.20001),Path(6,-.4)],0.,.2),
    ('uninformative_zero_mean',31,[Path(1,.2),Path(1,.5),Path(6,-.4)],.5,.2),
    ('tiny_ridge_nearly_duplicate',64,[Path(1,.2),Path(1,.2000001),Path(6,-.4)],0.,1e-12),
]:
    c1=.137/N;c2=.01
    x=(rng.normal(size=N)+1j*rng.normal(size=N)) if var==0 else np.zeros(N,complex)
    Y=rng.normal(size=N)+1j*rng.normal(size=N);v=np.full(N,var)
    xt=idaft(x,c1,c2);B,A,b,h,val=system(Y,xt,v,ps,c1,ridge)
    fld=CPPField(xt,c1,8,np.arange(-1.,1.001,.25))
    st=state_from_gram(A,b,float(np.vdot(Y,Y).real))
    K=np.vstack([np.conj(fld.correlate(B[:,i])) for i in range(3)])+gamma_cross(ps,fld.paths,v,c1)
    row=dict(name=name,condition=float(np.linalg.cond(A)),ridge=ridge)
    try:
        q,_,stats=exchange_scores(st,K,fld.correlate(Y),float(np.vdot(x,x).real+v.sum()+ridge))
        maxdiff=0
        for i in range(3):
            for j,p in enumerate(fld.paths):
                trial=list(ps);trial[i]=p
                *_,ref=system(Y,xt,v,trial,c1,ridge)
                maxdiff=max(maxdiff,abs(ref-q[i,j]))
        row.update(status='computed',max_objective_discrepancy=float(maxdiff),minimum_slack=float(stats['slack'].min()))
        if name!='tiny_ridge_nearly_duplicate':assert maxdiff<1e-8
        if name=='uninformative_zero_mean':
            row['objective_range']=float(q.max()-q.min());assert np.max(abs(h))==0 and row['objective_range']==0
    except (FloatingPointError,np.linalg.LinAlgError) as exc:
        if name!='tiny_ridge_nearly_duplicate':raise
        row.update(status='explicit_numerical_failure',exception=str(exc))
    if name=='tiny_ridge_nearly_duplicate':
        try:
            guarded=compact_exchange(Y,x,v,ps,c1=c1,c2=c2,ridge=ridge,max_delay=8,
                                     doppler_min=-1,doppler_max=1,grid_step=.25,max_edits=2)
            direct=reopen_geometry(Y,x,v,ps,c1=c1,c2=c2,ridge=ridge,max_delay=8,
                                   doppler_min=-1,doppler_max=1,grid_step=.25,max_edits=2,local_passes=0)
            row['guarded_fallback']=bool(guarded['numerical_fallback'])
            row['guarded_paths_equal_control']=guarded['paths']==direct.paths
            row['guarded_gain_maxdiff']=float(np.max(abs(guarded['gains']-direct.gains)))
            assert guarded['numerical_fallback'] and guarded['paths']==direct.paths
        except (FloatingPointError,np.linalg.LinAlgError) as exc:
            row['guarded_control_numerical_failure']=str(exc)
    rows.append(row)
FPath(__file__).with_name('limiting_case_results.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
