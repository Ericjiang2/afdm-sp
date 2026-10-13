"""Observed-only complete guarded receiver integration. Never import generate/score."""
import argparse
import hashlib
import fcntl
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import sys
import time
from types import SimpleNamespace
import numpy as np

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
OPTIONS=dict(list_size=16,branching=12,max_depth=3,gain_precision=0.,nuisance_precision=.1)
POLICIES=('cascade','cascade_osd','cascade_geometry','scalar','coherent','f1')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value,indent=2,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())


def append_json(path,value):
    with Path(path).open('a') as f:
        f.write(json.dumps(value,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())



def safe_child(root, relative):
    root=Path(root).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root):raise ValueError('path escapes artifact root')
    return path


@contextmanager
def writer_lock(out):
    out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    # Keep the inode permanently: unlinking a released lock permits split locks.
    path=out.parent/('.'+out.name+'.writer.lock')
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise RuntimeError('another writer owns output') from error
        yield
    finally:
        os.close(fd)


def runtime_binding(rt):
    system={k:getattr(rt.system,k) for k in ('N_total','rho','c1','c2','l_max_cap')}
    code={}
    for k in ('H','G'):
        a=np.ascontiguousarray(rt.code[k])
        code[k]=dict(shape=list(a.shape),dtype=str(a.dtype),sha256=hashlib.sha256(a.tobytes()).hexdigest())
    return dict(system=system,code=code,environment=rt.environment,header=rt.header)


def verify_runtime_registration(rt,registration):
    verify_registration(rt.project,registration)
    if any(registration['source_files'].get(p)!=digest for p,digest in rt.required_sources.items()):raise ValueError('incomplete runtime source binding')
    if registration.get('runtime_binding')!=runtime_binding(rt):raise ValueError('actual code/system/environment differs from registration')
    rt.evidence.verify_runtime_binding();assert_frozen_modules(rt.up)


def validate_retry(out,completed,authorization):
    path=Path(out)/'attempts.jsonl'
    events=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    started={}
    for e in events:
        if e.get('event') in ('started','failed','finished'):
            key=(e['observation_id'],e['policy'])
            if key not in completed:started.setdefault(key,[]).append(e)
    if not started:return None
    if authorization is None:raise ValueError('prior attempt exists; explicit retry authorization required')
    authorization=Path(authorization);auth=json.loads(authorization.read_text())
    if auth.get('attempts_sha256')!=sha256(path) or not auth.get('reason') or not auth.get('authorized_by'):raise ValueError('retry authorization does not bind prior attempts')
    entries={(r['observation_id'],r['policy']):r for r in auth['retries']}
    if len(entries)!=len(auth['retries']) or set(entries)!=set(started):raise ValueError('retry authorization allocation differs')
    for key,prior in started.items():
        failed=[e for e in prior if e['event']=='failed']
        if len(failed)!=sum(e['event']=='started' for e in prior):raise ValueError('interrupted attempt elapsed cost unknown; audit required before retry')
        measured=sum(e['elapsed_seconds'] for e in failed)
        if entries[key].get('previous_elapsed_seconds')!=measured:raise ValueError('retry failed cost differs')
    record=dict(event='retry_authorized',authorization_sha256=sha256(authorization),authorization=auth)
    append_json(path,record)
    return record

def assert_frozen_modules(upstream):
    root=Path(upstream).resolve()
    for name,module in list(sys.modules.items()):
        if name=='afdm_sp_joint_unrolled' or name.startswith('afdm_sp_joint_unrolled.'):
            locations=list(getattr(module,'__path__',[]))
            if getattr(module,'__file__',None):locations.append(module.__file__)
            if not locations or any(not Path(p).resolve().is_relative_to(root) for p in locations):
                raise RuntimeError('non-frozen package import: '+name)


def bootstrap(project=PROJECT,source=None,baseline=None):
    project=Path(project).resolve()
    source=Path(source or project/'experiments/sp_afdm_native_joint_20260921').resolve()
    baseline=Path(baseline or project/'experiments/sp_afdm_frozen_20260920').resolve()
    up=baseline/'upstream/spafdm_receiver_handoff'
    # A live root regular package would override frozen namespace candidates.
    sys.path[:]=[p for p in sys.path if p and Path(p).resolve()!=project and not (Path(p)/'afdm_sp_joint_unrolled').is_dir()]
    assert_frozen_modules(up)
    old=project/'issues/20261001-afdm-innovation-exploration'
    sys.path[:0]=[str(source/'src'),str(baseline/'src'),str(up),str(old/'experiments'),str(old/'theory'),str(HERE.parent/'acquisition')]+[str(project/'experiments'/p) for p in ('tf_production_gap_audit_20260922','tf_cstate_validation_20260922','tf_geometry_reopen_20260922','cstate_necessity_stageA_20260928')]
    from audit_io import attach,load_bound
    evidence=attach(source,baseline)
    environment=evidence.bind_runtime_environment()
    from receiver import context
    t=time.perf_counter();system,_,code,header=context();setup=time.perf_counter()-t
    import native_twofft as native
    import geometry_validation as kernel
    from native_f1 import receive_f1
    from run_validation import _branch
    from run_frontier import reused_coherent,f1_call
    from run_development import branch_payload,finite,observed_inputs
    from tf_reaction_adapter import load_variant
    from physical import Channel
    from candidates import acquire
    variant=load_variant(source/'src/twofft.py',expected_sha256=sha256(source/'src/twofft.py'),mode='coherent')
    evidence.verify_runtime_binding();assert_frozen_modules(up)
    if code['H'].shape!=(1026,2048):raise ValueError('frozen parity dimensions differ')
    required_sources={}
    for root in (source,baseline):
        for name,digest in evidence.source_hashes(root).items():
            required_sources[str((root/name).relative_to(project))]=digest
    for folder in [old/'experiments',old/'theory',HERE,HERE.parent/'acquisition',HERE.parent/'geometry']+[project/'experiments'/p for p in ('tf_production_gap_audit_20260922','tf_cstate_validation_20260922','tf_geometry_reopen_20260922','cstate_necessity_stageA_20260928')]:
        for path in folder.glob('*.py'):required_sources[str(path.relative_to(project))]=sha256(path)
    cache=up/'afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    required_sources[str(cache.relative_to(project))]=sha256(cache)
    return SimpleNamespace(**locals())


def final_channel(payload,rt,n):
    """Acquisition only follows failed F1+CSTATE, so use its actual branch state."""
    restart=payload['restart']
    if restart is None or restart['branch'] is None:
        raise ValueError('failed cascade requires actual final F1 CSTATE branch')
    result=restart['branch']['geometry_result']
    return rt.Channel(n,rt.system.c1,rt.system.c2,
        [p['delay'] for p in result['paths']],[p['doppler'] for p in result['paths']],result['gains'])


def receive(obs,policy,rt,options=None):
    if policy not in POLICIES:raise ValueError('unknown policy')
    if set(obs)!={'y','pilot','sigma2'}:raise ValueError('observed-only input whitelist')
    if np.shape(obs['y'])!=(1024,) or np.shape(obs['pilot'])!=(1024,) or float(obs['sigma2'])<=0:raise ValueError('observation shape/variance')
    rt.finite(obs)
    options=dict(OPTIONS if options is None else options)
    if options!=OPTIONS:raise ValueError('v1 acquisition parameters differ')
    H=rt.code['H'];syndrome=lambda dec:int(np.count_nonzero(H@dec['decoded']%2))
    t=time.perf_counter()
    payload=dict(prefix=None,scalar_branch=None,coherent=None,restart=None,acquisition=None)
    if policy=='f1':
        payload['restart']=rt.f1_call(obs,rt.system,rt.code,H,rt.native,rt.kernel,rt._branch,rt.receive_f1)
        dec=payload['restart']['final_decoder']
    else:
        dec,arrays,timing=rt.native.receive(obs,rt.system,rt.code,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint')
        payload['prefix']=dict(decoder=dec,arrays=arrays,timing=timing)
        if syndrome(dec):
            third=rt._branch(obs,rt.system,rt.code,rt.native,rt.kernel,arrays,'CSTATE20')
            dec=third['decoder'];payload['scalar_branch']=rt.branch_payload(third)
            if syndrome(dec) and policy!='scalar':
                payload['coherent']=rt.reused_coherent(obs,rt.system,rt.code,rt.native,rt.variant,third)
                dec=payload['coherent']['decoder']
        if syndrome(dec) and policy in ('cascade','cascade_osd','cascade_geometry'):
            payload['restart']=rt.f1_call(obs,rt.system,rt.code,H,rt.native,rt.kernel,rt._branch,rt.receive_f1)
            dec=payload['restart']['final_decoder']
    payload['pre_acquisition_decoder']=dec
    if syndrome(dec) and policy in ('cascade_osd','cascade_geometry'):
        channel=final_channel(payload,rt,len(obs['y']))
        result=rt.acquire(H,dec['raw_app'],channel,obs['y'],obs['pilot'],float(obs['sigma2']),scale=np.sqrt(1-rt.system.rho),mode=policy.removeprefix('cascade_'),**options)
        payload['acquisition']=result
        payload['acquisition_geometry']=dict(delays=channel.delays,dopplers=channel.dopplers,gains=channel.gains)
        # No invented new APP or decoder iterations: candidate decision is separate.
        dec=dict(decoded=result['decoded'],decision_source='legal_candidate_gain_profile',decode_ok=True)
    payload['final_decoder']=dec
    payload['final_syndrome']=syndrome(dec)
    payload['receiver_ready_seconds']=time.perf_counter()-t
    rt.finite(payload)
    return payload


def verify_registration(project,registration):
    if registration['candidate_options']!=OPTIONS:raise ValueError('candidate config drift')
    if not registration['source_files']:raise ValueError('source binding absent')
    for path,digest in registration['source_files'].items():
        target=(Path(project)/path).resolve()
        if not target.is_relative_to(Path(project).resolve()) or sha256(target)!=digest:raise ValueError('source binding mismatch '+path)


def _run_population(rt,population,out,registration,*,resume=False,retry_authorization=None):
    population=Path(population).resolve();out=Path(out).resolve()
    verify_runtime_registration(rt,registration)
    policies=tuple(registration['policies'])
    if not policies or len(set(policies))!=len(policies) or any(p not in POLICIES for p in policies):raise ValueError('policy allocation invalid')
    seal=json.loads((population/'observed_seal.json').read_text())
    producer=json.loads((population/'manifest.json').read_text())
    if producer.get('registration')!=registration or producer.get('runtime_binding')!=runtime_binding(rt):raise ValueError('producer source/config/runtime binding differs')
    if seal['allocation_sha256']!=registration['allocation_sha256']:raise ValueError('allocation binding mismatch')
    for path,digest in seal['files'].items():
        if sha256(safe_child(population,path))!=digest:raise ValueError('observed seal drift')
    rows=[json.loads(l) for l in (population/'ledger.jsonl').read_text().splitlines()]
    if len(rows)!=len({r['observation_id'] for r in rows}):raise ValueError('duplicate observation')
    if any(not r['observation_id'] or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in r['observation_id']) for r in rows):raise ValueError('unsafe observation id')
    completed={}
    if out.exists():
        if not resume:raise FileExistsError('preserve existing run; explicit resume required')
        manifest=json.loads((out/'manifest.json').read_text())
        if manifest['registration']!=registration or manifest['population_seal_sha256']!=sha256(population/'observed_seal.json'):raise ValueError('resume binding differs')
        for line in (out/'ledger.jsonl').read_text().splitlines() if (out/'ledger.jsonl').exists() else []:
            r=json.loads(line);key=(r['observation_id'],r['policy'])
            if key in completed or sha256(safe_child(out,r['raw_path']))!=r['raw_sha256']:raise ValueError('resume ledger/raw invalid')
            completed[key]=r
        validate_retry(out,completed,retry_authorization)
    else:
        out.mkdir(parents=True);(out/'raw').mkdir()
        write_json(out/'manifest.json',dict(registration=registration,population_seal_sha256=sha256(population/'observed_seal.json'),setup_seconds=rt.setup,environment=rt.environment,header=rt.header,pid=os.getpid(),timing='ready includes observation load and all candidate generation/previews; complete includes raw write; setup excluded equally; ledger write excluded'))
    def expired(*_):raise TimeoutError('registered unit time limit')
    signal.signal(signal.SIGALRM,expired);signal.alarm(int(registration['seconds_limit']))
    try:
        for i,row in enumerate(rows):
            for policy in policies[i%len(policies):]+policies[:i%len(policies)]:
                key=(row['observation_id'],policy)
                if key in completed:continue
                path=out/'raw'/f'{key[0]}_{policy}.npz'
                if path.exists():raise FileExistsError('orphan raw requires explicit audit, never rerun/overwrite')
                identity=dict(observation_id=key[0],policy=policy,input_sha256=row['observation_sha256'],observation_hash=row['observation_hash'],stream_ids=row['stream_ids'])
                append_json(out/'attempts.jsonl',dict(identity,event='started',epoch=time.time()))
                start=time.perf_counter()
                try:
                    obs=rt.observed_inputs(rt.evidence,rt.load_bound,population,row)
                    payload=receive(obs,policy,rt,registration['candidate_options'])
                    ready=time.perf_counter()-start
                    digest=rt.evidence.save_artifact(path,payload,identity)
                    result=dict(identity,raw_path=str(path.relative_to(out)),raw_sha256=digest,receiver_ready_seconds=ready,complete_seconds=time.perf_counter()-start,final_syndrome=payload['final_syndrome'],acquisition_executed=payload['acquisition'] is not None)
                    append_json(out/'ledger.jsonl',result);append_json(out/'attempts.jsonl',dict(result,event='finished'));completed[key]=result
                except BaseException as error:
                    append_json(out/'attempts.jsonl',dict(identity,event='failed',exception=repr(error),elapsed_seconds=time.perf_counter()-start));raise
        verify_runtime_registration(rt,registration)
        receipt=dict(status='pass',completed_calls=len(completed),expected_calls=len(rows)*len(policies),ledger_sha256=sha256(out/'ledger.jsonl'),manifest_sha256=sha256(out/'manifest.json'))
        if not (out/'result.json').exists():write_json(out/'result.json',receipt)
        elif json.loads((out/'result.json').read_text())!=receipt:raise ValueError('terminal result differs')
    finally:signal.alarm(0)



def run_population(rt,population,out,registration,*,resume=False,retry_authorization=None):
    with writer_lock(out):
        return _run_population(rt,population,out,registration,resume=resume,retry_authorization=retry_authorization)

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=PROJECT);p.add_argument('--source',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--population',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--registration',type=Path,required=True);p.add_argument('--resume',action='store_true');p.add_argument('--retry-authorization',type=Path);a=p.parse_args()
    reg=json.loads(a.registration.read_text());verify_registration(a.project,reg)
    rt=bootstrap(a.project,a.source,a.baseline);run_population(rt,a.population,a.out,reg,resume=a.resume,retry_authorization=a.retry_authorization)

if __name__=='__main__':main()
