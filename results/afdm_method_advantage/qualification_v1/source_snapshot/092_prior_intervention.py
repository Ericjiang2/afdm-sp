"""Paired CE regularizer intervention at one frozen archived-state interface."""
import sys
import json
import time
from pathlib import Path
import numpy as np
from state_diagnostics import ROOT,OLD,RUN,POP,read,lines,sha,bound,terminal,blas_binding,evidence
from linear_limits import Channel,twofft
from physical import projected_variance
from messages import moments
OUT=ROOT/'.mission/20261002_22-12-10-afdm-inference-causal-defects/execution/prior_intervention'

def fit(c,obs,mu,v,prior_precision):
    B=c.regressors(obs['pilot']+mu)
    gamma=projected_variance(v,c.delays,c.dopplers,c.c1)
    Q=B.conj().T@B+gamma+obs['sigma2']*prior_precision*np.eye(c.p)
    rhs=B.conj().T@obs['y'];h=np.linalg.solve(Q,rhs)
    residual=float(np.linalg.norm(Q@h-rhs)/max(np.linalg.norm(rhs),1e-30))
    return Channel(c.n,c.c1,c.c2,c.delays,c.dopplers,h),residual

def objective(c,obs,out):
    B=c.regressors(obs['pilot']+out['mu'])
    gamma=projected_variance(out['variance'],c.delays,c.dopplers,c.c1)
    h=out['gains'];Q=B.conj().T@B+gamma+obs['sigma2']*c.p*np.eye(c.p);rhs=B.conj().T@obs['y']
    return float(np.linalg.norm(Q@h-rhs)/max(np.linalg.norm(rhs),1e-30))

def stats(a):
    a=np.asarray(a,float)
    return dict(n=len(a),mean=float(a.mean()),median=float(np.median(a)),min=float(a.min()),max=float(a.max()))

def main():
    start=time.process_time();binding=blas_binding();reg=read(OUT/'registration.json')
    for p,h in reg['bindings'].items():
        if sha(ROOT/p)!=h:raise ValueError('registration binding mismatch')
    manifest=read(RUN/'manifest.json');system=manifest['registration']['runtime_binding']['system']
    receipt=read(RUN/'result.json')
    if receipt['status']!='pass' or receipt['ledger_sha256']!=sha(RUN/'ledger.jsonl') or receipt['manifest_sha256']!=sha(RUN/'manifest.json'):raise ValueError('archive not verified')
    obsrows={r['observation_id']:r for r in lines(POP/'ledger.jsonl')};rows=sorted([r for r in lines(RUN/'ledger.jsonl') if r['policy']=='baseline'],key=lambda x:x['observation_id'])
    if len(rows)!=256 or [r['observation_id'] for r in rows]!=reg['ids']:raise ValueError('cohort drift')
    records=[];calls=0
    with (OUT/'records.jsonl').open('x') as logfile:
        for row in rows:
            stem=row['observation_id'];o=obsrows[stem]
            p,meta=evidence.load_artifact(bound(RUN,row['raw_path'],row['raw_sha256']))
            saved,om=evidence.load_artifact(bound(POP,o['observation_path'],row['input_sha256']))
            if meta['observation_id']!=stem or om['observation_id']!=stem or meta['input_sha256']!=row['input_sha256']:raise ValueError('identity mismatch')
            obs=saved['observation'];c,stage,_,_,_=terminal(p,system)
            app=np.clip(p['final_decoder']['raw_app'],-20,20);prior=np.clip(p['final_decoder']['raw_check_extrinsic'],-20,20)
            mu,v,_=moments(app,.5);a,res1=fit(c,obs,mu,v,1);b,resP=fit(c,obs,mu,v,c.p)
            before=float(np.linalg.norm(a.gains-b.gains));entry=dict(id=stem,stage=stage,P=c.p,raw_sha256=row['raw_sha256'],input_sha256=row['input_sha256'],ce_gain_difference=before,ce_residual_tau1=res1,ce_residual_tauP=resP,comparisons={})
            for niter in [20,40]:
                outputs=[]
                for init in [a,b]:
                    if calls>=reg['call_cap'] or time.process_time()-start>=reg['cpu_cap_seconds']:raise TimeoutError('registered budget exhausted')
                    outputs.append(twofft.scalar_joint(obs['y'],obs['pilot'],init,obs['sigma2'],pd=.5,prior=prior,iterations=niter,damping=.3))
                    calls+=1
                    if time.process_time()-start>reg['cpu_cap_seconds']:raise TimeoutError('registered CPU cap exceeded; partial invalid')
                x,y=outputs;after=float(np.linalg.norm(x['gains']-y['gains']))
                entry['comparisons'][str(niter)]=dict(gain_difference=after,attenuation=after/before if before else None,
                    llr_rms=float(np.sqrt(np.mean((x['extrinsic']-y['extrinsic'])**2))),
                    moment_rms=float(np.sqrt(np.mean(abs(x['mu']-y['mu'])**2))),
                    variance_rms=float(np.sqrt(np.mean((x['variance']-y['variance'])**2))),
                    gain_variance_difference=float(abs(x['gain_variance'][0]-y['gain_variance'][0])),
                    frozen_q_residual_tau1_init=objective(c,obs,x),frozen_q_residual_tauP_init=objective(c,obs,y),
                    fft_each=x['fft_count'],iterations_each=niter)
            records.append(entry);logfile.write(json.dumps(entry,allow_nan=False)+'\n');logfile.flush()
    if calls!=1024:raise ValueError('call allocation incomplete')
    bystage={s:[r for r in records if r['stage']==s] for s in sorted(set(r['stage'] for r in records))};bystage['all']=records
    summary={stage:{str(n):{k:stats([r['comparisons'][str(n)][k] for r in rs]) for k in ['gain_difference','attenuation','llr_rms','moment_rms','gain_variance_difference','frozen_q_residual_tau1_init','frozen_q_residual_tauP_init']} for n in [20,40]} for stage,rs in bystage.items()}
    result=dict(status='pass',scope=reg['scope'],calls=calls,frames=len(records),summary=summary,effective_blas=binding,cpu_seconds=time.process_time()-start,
        argv=sys.argv,python=sys.version,numpy=np.__version__,registration_sha256=sha(OUT/'registration.json'),records_sha256=sha(OUT/'records.jsonl'))
    with (OUT/'result.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({'calls':calls,'cpu_seconds':result['cpu_seconds'],'all':summary['all']},indent=2))

if __name__=='__main__':main()
