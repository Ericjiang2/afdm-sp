"""Whole archived cohort covariance diagnosis; never imports a receiver runner."""
from pathlib import Path
import json
import sys
import hashlib
import time
from types import SimpleNamespace
import numpy as np
from linear_limits import ROOT, Channel, posterior
sys.path.insert(0,str(ROOT/'.mission/20261001_23-33-35-afdm-innovation-space/controls'))
from thread_binding import blas_binding
import evidence

OLD=ROOT/'.mission/20261002_11-01-40-afdm-algebraic-decoupling/execution'
RUN=OLD/'development-run'
POP=OLD/'development-population/observed'
OUT=ROOT/'.mission/20261002_22-12-10-afdm-inference-causal-defects/execution/state_diagnostics'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def bound(base,path,digest):
    p=(base/path).resolve()
    if not p.is_relative_to(base.resolve()) or sha(p)!=digest:raise ValueError('artifact binding mismatch: '+str(p))
    return p

def terminal(payload,system):
    # Exact branch precedence from receiver_v2/adapter.actual_terminal_channel.
    if payload['restart'] is not None:
        r=payload['restart']
        if r['branch'] is None:
            arrays=r['arrays'];stage='f1_round1';decoder=r['decoder'];branch=None
        else:branch=r['branch'];stage='f1_cstate';decoder=branch['decoder']
    elif payload['coherent'] is not None:
        branch=dict(payload['coherent']);branch['geometry_result']=payload['scalar_branch']['geometry_result'];stage='coherent';decoder=branch['decoder']
    elif payload['scalar_branch'] is not None:
        branch=payload['scalar_branch'];stage='cstate';decoder=branch['decoder']
    else:arrays=payload['prefix']['arrays'];stage='prefix_round1';decoder=payload['prefix']['decoder'];branch=None
    if not np.array_equal(decoder['decoded'],payload['final_decoder']['decoded']):raise ValueError('terminal decoder mismatch')
    if branch is None:
        ls=arrays['r1_delays'];nus=arrays['r1_dopplers'];g=arrays['r1_gains']
        mu=arrays['r1_mu'];v=arrays['r1_variance'];vh=arrays['r1_gain_variance']
    else:
        geom=branch['geometry_result'];det=branch['detector']
        ls=[p['delay'] for p in geom['paths']];nus=[p['doppler'] for p in geom['paths']];g=det['gains']
        mu=det['mu'];v=det['variance'];vh=det['gain_variance']
    c=Channel(system['N_total'],system['c1'],system['c2'],ls,nus,g)
    if np.asarray(mu).shape!=(c.n,) or np.asarray(v).shape!=(c.n,) or np.asarray(vh).shape!=(c.p,):raise ValueError('state shape mismatch')
    if not all(np.isfinite(q).all() for q in [mu,v,vh]):raise ValueError('nonfinite state')
    return c,stage,np.asarray(mu),np.asarray(v),np.asarray(vh)

def metrics(c,pilot,mu,v,vh,noise):
    B=c.regressors(pilot+mu);G=B.conj().T@B
    eigen=np.linalg.eigvalsh(G);C=posterior(B,noise,1/c.p)
    avg=float(np.trace(C).real/c.p);norm=float(np.linalg.norm(C));scalar=float(vh.mean())
    directional=float(np.linalg.norm(C-avg*np.eye(c.p))/norm)
    scale=float(np.sqrt(c.p)*abs(scalar-avg)/norm)
    total=float(np.linalg.norm(C-np.diag(vh))/norm)
    if not np.allclose(vh,scalar,rtol=0,atol=1e-14):raise ValueError('stored variance not scalar')
    if abs(total**2-directional**2-scale**2)>1e-7*max(1,total**2):raise ValueError('orthogonal error decomposition mismatch')
    pairs=[abs(c.dopplers[i]-c.dopplers[j]) for i in range(c.p) for j in range(i) if c.delays[i]==c.delays[j]]
    return dict(P=c.p,same_delay_pairs=len(pairs),same_delay_min_doppler_gap=min(pairs) if pairs else None,
        gram_eigenvalues=eigen.tolist(),gram_ratio=float(eigen[0]/eigen[-1]),
        directional=directional,scale=scale,total=total,
        conditional_variance_mean=avg,stored_variance=scalar,
        weakest_variance_ratio=float(np.linalg.eigvalsh(C)[-1]/scalar) if scalar>0 else None,
        mean_data_variance=float(v.mean()),conditional_vs_prior_max=float(np.linalg.eigvalsh(C)[-1]*c.p))

def contrast(rows,key,rng):
    fail=np.array([r[key] for r in rows if r['error']],float);ok=np.array([r[key] for r in rows if not r['error']],float)
    if not len(fail) or not len(ok):return None
    samples=fail[rng.integers(len(fail),size=(4000,len(fail)))].mean(1)-ok[rng.integers(len(ok),size=(4000,len(ok)))].mean(1)
    return dict(failed_n=len(fail),success_n=len(ok),failed_mean=float(fail.mean()),success_mean=float(ok.mean()),
                difference=float(fail.mean()-ok.mean()),bootstrap_ci=np.quantile(samples,[.025,.975]).tolist())

def main():
    start=time.process_time();binding=blas_binding();reg=read(OUT/'registration.json')
    for p,d in reg['sources'].items():
        if sha(p)!=d:raise ValueError('preregistered source changed')
    receipt=read(RUN/'result.json');manifest=read(RUN/'manifest.json');seal=read(POP/'observed_seal.json')
    if receipt['status']!='pass' or receipt['completed_calls']!=768 or receipt['expected_calls']!=768:raise ValueError('incomplete run')
    if receipt['ledger_sha256']!=sha(RUN/'ledger.jsonl') or receipt['manifest_sha256']!=sha(RUN/'manifest.json'):raise ValueError('run hash mismatch')
    if manifest['population_seal_sha256']!=sha(POP/'observed_seal.json') or manifest['producer_manifest_sha256']!=sha(POP/'manifest.json'):raise ValueError('population mismatch')
    source_paths=['experiments/sp_afdm_native_joint_20260921/src/twofft.py','experiments/sp_afdm_frozen_20260920/src/physical.py','experiments/sp_afdm_frozen_20260920/src/evidence.py']
    for p in source_paths:
        if sha(ROOT/p)!=manifest['source_files'][p]:raise ValueError('frozen source changed')
    source_paths+=['.mission/20261002_11-01-40-afdm-algebraic-decoupling/execution/receiver_v2/adapter.py','experiments/afdm_inference_causal_20261002/state_diagnostics.py','experiments/afdm_inference_causal_20261002/linear_limits.py','.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py']
    ledger=lines(RUN/'ledger.jsonl');rows=[r for r in ledger if r['policy']=='baseline'];obsrows={r['observation_id']:r for r in lines(POP/'ledger.jsonl')}
    ids=sorted(r['observation_id'] for r in rows)
    if len(rows)!=256 or len(set(ids))!=256 or set(ids)!=set(obsrows):raise ValueError('cohort mismatch')
    records=[];system=manifest['registration']['runtime_binding']['system']
    for row in sorted(rows,key=lambda r:r['observation_id']):
        stem=row['observation_id'];p,meta=evidence.load_artifact(bound(RUN,row['raw_path'],row['raw_sha256']))
        o=obsrows[stem]
        if seal['files'][o['observation_path']]!=o['observation_sha256'] or row['input_sha256']!=o['observation_sha256']:raise ValueError('input identity mismatch')
        saved,om=evidence.load_artifact(bound(POP,o['observation_path'],o['observation_sha256']))
        if meta['observation_id']!=stem or meta['policy']!='baseline' or meta['input_sha256']!=row['input_sha256'] or om['observation_id']!=stem:raise ValueError('identity mismatch')
        if meta['observation_hash']!=o['observation_hash'] or meta['stream_ids']!=o['stream_ids']:raise ValueError('stream mismatch')
        observation=saved['observation']
        if set(observation)!={'y','pilot','sigma2'}:raise ValueError('observed keys mismatch')
        c,stage,mu,v,vh=terminal(p,system)
        records.append(dict(id=stem,stage=stage,raw_sha256=row['raw_sha256'],input_sha256=row['input_sha256'],snr_centi_db=o['snr_centi_db'],
            missingness=[],**metrics(c,observation['pilot'],mu,v,vh,observation['sigma2'])))
    # Load already revealed labels only after the complete feature table exists.
    scored=read(OLD/'protocol/development-scored.json')
    if scored['result_sha256']!=sha(RUN/'result.json'):raise ValueError('label binding mismatch')
    labels={r['observation_id']:r for r in scored['records'] if r['policy']=='baseline'}
    if set(labels)!=set(ids):raise ValueError('label coverage mismatch')
    for r in records:r['error']=bool(labels[r['id']]['error'])
    rng=np.random.default_rng(2026100201);keys=['directional','scale','total','gram_ratio','mean_data_variance']
    groups={}
    for r in records:
        key=f"{r['stage']}|P={r['P']}|same_delay={r['same_delay_pairs']>0}"
        groups.setdefault(key,[]).append(r)
    result=dict(scope=reg['scope'],reference=reg['reference'],n=len(records),errors=sum(r['error'] for r in records),
        missing=0,snr_values=sorted(set(r['snr_centi_db'] for r in records)),
        global_contrasts={k:contrast(records,k,rng) for k in keys},
        strata={g:dict(n=len(rr),errors=sum(r['error'] for r in rr),contrasts={k:contrast(rr,k,rng) for k in keys}) for g,rr in groups.items()},
        distributions={k:dict(mean=float(np.mean([r[k] for r in records])),quantiles=np.quantile([r[k] for r in records],[0,.5,.9,.95,1]).tolist()) for k in keys},
        bindings={p:sha(ROOT/p) for p in source_paths},registration_sha256=sha(OUT/'registration.json'),effective_blas=binding,
        argv=sys.argv,python=sys.version,numpy=np.__version__,cpu_seconds=time.process_time()-start)
    with (OUT/'states.jsonl').open('x') as f:
        for r in records:f.write(json.dumps(r,allow_nan=False)+'\n')
    result['states_sha256']=sha(OUT/'states.jsonl')
    with (OUT/'summary.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({'n':result['n'],'errors':result['errors'],'global_contrasts':result['global_contrasts'],'strata':{k:{'n':v['n'],'errors':v['errors']} for k,v in result['strata'].items()}},indent=2))

if __name__=='__main__':main()
