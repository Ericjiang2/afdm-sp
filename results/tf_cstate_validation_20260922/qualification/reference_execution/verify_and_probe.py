"""Independent algebra and negative-control probes; not production receiver evidence."""
import json, time
from pathlib import Path as FSPath
import numpy as np
from scipy.linalg import cho_factor,cho_solve
from geometry_exchange_control import Path,idaft,responses,gamma_cross,system,reopen_geometry
from structural_state import CPPField,state_from_gram,exchange_scores,valid_replacements,compact_exchange


def serial(z):
    if isinstance(z,np.ndarray):return z.tolist()
    if isinstance(z,np.bool_):return bool(z)
    if isinstance(z,(np.integer,np.floating)):return z.item()
    if isinstance(z,np.complexfloating):return [float(z.real),float(z.imag)]
    raise TypeError(type(z))


def direct_scores(Y,xt,v,paths,cand,c1,ridge):
    out=np.empty((len(paths),len(cand)))
    for i in range(len(paths)):
        for j,p in enumerate(cand):
            ps=list(paths);ps[i]=p
            *_,out[i,j]=system(Y,xt,v,ps,c1,ridge)
    return out


def verify():
    rng=np.random.default_rng(2026092213)
    errors={};ncomparisons=0
    field_err=gamma_err=score_err=gain_err=0.
    winners=[]
    for N in (16,31,64):
      for c1 in (5/(2*N),.137/N):
        P=3;L=7
        x=(rng.normal(size=N)+1j*rng.normal(size=N))/np.sqrt(2)
        v=rng.uniform(.01,.5,N);Y=rng.normal(size=N)+1j*rng.normal(size=N)
        xt=idaft(x,c1,.011)
        paths=[Path(1,-.371),Path(1,.684),Path(5,-.119)]
        fld=CPPField(xt,c1,L,np.arange(-1.,1.01,.5))
        U=responses(xt,fld.paths,c1)
        field_err=max(field_err,float(np.max(abs(fld.correlate(Y)-U.conj().T@Y))))
        B,A,b,h,val=system(Y,xt,v,paths,c1,.17)
        st=state_from_gram(A,b,float(np.vdot(Y,Y).real))
        K=B.conj().T@U+gamma_cross(paths,fld.paths,v,c1)
        beta=U.conj().T@Y
        vals,add,stats=exchange_scores(st,K,beta,float(np.vdot(x,x).real+v.sum()+.17))
        ref=direct_scores(Y,xt,v,paths,fld.paths,c1,.17)
        score_err=max(score_err,float(np.max(abs(vals-ref))));ncomparisons+=vals.size
        # Independent dense AF path operators, not the Fourier Gamma identity.
        n=np.arange(N);F=np.exp(-2j*np.pi*n[:,None]*n[None,:]/N)/np.sqrt(N)
        Aaf=np.exp(2j*np.pi*.011*n*n)[:,None]*F*np.exp(2j*np.pi*c1*n*n)[None,:]
        ops=[]
        for p in paths:
            M=np.zeros((N,N),complex)
            ph=np.exp(2j*np.pi*p.doppler*n/N)
            prefix=np.ones(N,complex)
            prefix[n<p.delay]=np.exp(2j*np.pi*c1*(N*N+2*N*(n[n<p.delay]-p.delay)))
            M[n,(n-p.delay)%N]=ph*prefix
            ops.append(Aaf@M@Aaf.conj().T)
        gd=np.array([[np.sum((a.conj()*b)*v[None,:]) for b in ops] for a in ops])
        gamma_err=max(gamma_err,float(np.max(abs(gd-gamma_cross(paths,paths,v,c1)))))
        # Two sequential swaps; exact control ordering, same duplicate rule.
        fast=compact_exchange(Y,x,v,paths,c1=c1,c2=.011,ridge=.17,max_delay=L,
                              doppler_min=-1,doppler_max=1,grid_step=.5,max_edits=2)
        slow=reopen_geometry(Y,x,v,paths,c1=c1,c2=.011,ridge=.17,max_delay=L,
                             doppler_min=-1,doppler_max=1,grid_step=.5,max_edits=2,local_passes=0)
        if fast['paths']!=slow.paths:raise AssertionError('Sequential structural decisions differ')
        winners.append([[p.delay,p.doppler] for p in slow.paths])
        gain_err=max(gain_err,float(np.max(abs(fast['gains']-slow.gains))))
    assert field_err<1e-10 and score_err<1e-10 and gamma_err<1e-10 and gain_err<1e-9
    errors.update(field_max_abs=field_err,gamma_max_abs=gamma_err,
                  all_swap_objective_max_abs=score_err,final_gain_max_abs=gain_err,
                  candidate_score_comparisons=ncomparisons,
                  sequential_fixture_count=len(winners),all_sequential_winners_equal=True)
    return errors


def bridge_counterexample():
    # Incumbent orthogonal columns; tiny positive ridge, no singular system.
    eye=np.eye(4);B=eye[:,:2].astype(complex);Y=np.array([1.,2.,1.1,1.]).astype(complex)
    cand=np.column_stack([eye[:,2],(eye[:,0]+eye[:,3])/np.sqrt(2)]).astype(complex)
    lam=.01;A=B.conj().T@B+lam*np.eye(2);b=B.conj().T@Y
    st=state_from_gram(A,b,float(np.vdot(Y,Y).real))
    vals,add,stats=exchange_scores(st,B.conj().T@cand,cand.conj().T@Y,1+lam)
    chosen_add=int(np.argmax(add));chosen_swap=np.unravel_index(np.argmin(vals),vals.shape)
    direct=[]
    for j in range(2):
      aa=B.copy();aa[:,0]=cand[:,j]
      hh=np.linalg.solve(aa.conj().T@aa+lam*np.eye(2),aa.conj().T@Y)
      direct.append(float(np.linalg.norm(Y-aa@hh)**2+lam*np.linalg.norm(hh)**2))
    assert chosen_add==0 and chosen_swap==(0,1)
    return dict(incumbent_objective=st.objective,add_improvement=add.tolist(),
                best_swap_improvement_by_candidate=(st.objective-vals.min(axis=0)).tolist(),
                candidate_first_choice=chosen_add,joint_swap_choice=list(chosen_swap),
                independent_objectives=direct,
                active_gram_condition=float(np.linalg.cond(A)))


def same_local_state_witness():
    # Actual single-sample waveform, exact CPP path columns, no Doppler claim.
    N=16;xt=np.zeros(N,complex);xt[0]=np.sqrt(N);c1=.137/N
    cur=[Path(1,.37),Path(3,-.61)]
    cs=[Path(7,.43),Path(9,-.21)]
    B=responses(xt,cur,c1);D=responses(xt,cs,c1)
    h=np.array([1.+.2j,.7-.1j]);y0=B@h
    y1=y0+.4*D[:,0];y2=y0+.4*D[:,1]
    active_diff=float(np.max(abs(B.conj().T@y1-B.conj().T@y2)))
    norm_diff=float(abs(np.linalg.norm(y1-y0)-np.linalg.norm(y2-y0)))
    outside=np.abs(D.conj().T@np.column_stack([y1,y2]))
    assert active_diff<1e-12 and norm_diff<1e-12
    assert np.argmax(outside[:,0])!=np.argmax(outside[:,1])
    return dict(active_projection_max_difference=active_diff,residual_norm_difference=norm_diff,
                outside_correlation_magnitudes=outside.tolist())


def afdm_negative_probe():
    rng=np.random.default_rng(314159)
    results=[]
    # One fixed configuration, 80 paired reference snapshots, no parameter sweep.
    N=96;P=4;L=15;c1=.137/N;c2=.009;lam=.15
    nus=np.arange(-1.5,1.501,.25)
    for trial in range(80):
        d=.5*(rng.choice([-1,1],N)+1j*rng.choice([-1,1],N))
        p=np.sqrt(.5)*np.exp(2j*np.pi*rng.random(N))
        # Independent synthetic working means, NOT exact LDPC posteriors.
        ri=rng.uniform(.65,.99,N);rq=rng.uniform(.65,.99,N)
        mu=d.real*ri+1j*d.imag*rq
        v=.5-abs(mu)**2;x=p+mu;xt=idaft(x,c1,c2)
        true=[Path(2,-.45),Path(2,.5),Path(7,-.75),Path(11,.9)]
        h=(rng.normal(size=P)+1j*rng.normal(size=P));h/=np.linalg.norm(h)
        Y=responses(idaft(p+d,c1,c2),true,c1)@h+np.sqrt(lam/2)*(rng.normal(size=N)+1j*rng.normal(size=N))
        # True same-delay component excluded; a false slot occupies the budget.
        cur=[Path(2,-.28),Path(5,.25),Path(7,-.61),Path(11,.71)]
        fld=CPPField(xt,c1,L,nus)
        B,A,b,hh,val=system(Y,xt,v,cur,c1,lam)
        st=state_from_gram(A,b,float(np.vdot(Y,Y).real))
        beta=fld.correlate(Y)
        K=np.vstack([np.conj(fld.correlate(B[:,i])) for i in range(P)])+gamma_cross(cur,fld.paths,v,c1)
        scores,add,stats=exchange_scores(st,K,beta,float(np.vdot(x,x).real+v.sum()+lam))
        valid=valid_replacements(cur,fld.paths)
        good=np.where(valid,scores,np.inf)
        best_i,best_j=np.unravel_index(np.argmin(good),good.shape)
        feasible=valid.any(axis=0)
        j_add=int(np.argmax(np.where(feasible,add,-np.inf)))
        i_add=int(np.argmin(good[:,j_add]))
        q_best=min(val,float(good[best_i,best_j]));q_add=min(val,float(good[i_add,j_add]))
        u=float(val-q_best);a=float(val-q_add)
        # No FER in this experiment; compare ONLY the same frozen objective.
        results.append(dict(trial=trial,full_improvement=u,add_first_improvement=a,
                            regret=q_add-q_best,same_candidate=(best_j==j_add),
                            full_path=[fld.paths[best_j].delay,fld.paths[best_j].doppler],
                            add_first_path=[fld.paths[j_add].delay,fld.paths[j_add].doppler]))
    regrets=np.array([r['regret'] for r in results]);imp=np.array([r['full_improvement'] for r in results])
    aimp=np.array([r['add_first_improvement'] for r in results])
    return dict(configuration='N96 P4; fixed two same-delay paths; 80 synthetic moment snapshots',
                n=len(results),candidate_agreements=sum(r['same_candidate'] for r in results),
                strictly_worse_objective_count=int(np.sum(regrets>1e-8)),
                full_improves_add_first_stalls=int(np.sum((imp>1e-8)&(aimp<=1e-8))),
                max_regret=float(regrets.max()),mean_regret=float(regrets.mean()),
                median_improvement_retention=float(np.median(aimp/np.maximum(imp,1e-30))),
                rows=results)


if __name__=='__main__':
    out=dict(verification=verify(),bridge_counterexample=bridge_counterexample(),
             local_state_counterexample=same_local_state_witness(),
             afdm_add_first_negative_probe=afdm_negative_probe())
    dest=FSPath(__file__).with_name('verification_and_probe_results.json')
    dest.write_text(json.dumps(out,indent=2,default=serial))
    print(json.dumps({k:({kk:vv for kk,vv in v.items() if kk!='rows'} if isinstance(v,dict) else v) for k,v in out.items()},indent=2,default=serial))
