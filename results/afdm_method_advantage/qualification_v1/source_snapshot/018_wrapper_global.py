"""global_v2 receiver entry with separate immutable producer/receiver identities.

Reuses all v1 receiver algorithms. Does not mutate v1 modules or old population.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time
from types import SimpleNamespace
import wrapper as base

POLICIES=('cascade','residual_global','geometry_global')
TRANSLATE=dict(cascade='cascade',residual_global='cascade_osd',geometry_global='cascade_geometry')


def bootstrap(project=base.PROJECT,source=None,baseline=None):
    rt=base.bootstrap(project,source,baseline)
    from global_candidates import acquire_global
    # Private per-runtime dependency, no mutation of any imported v1 module.
    rt=SimpleNamespace(**vars(rt));rt.acquire=acquire_global;rt.mechanism_version='global_v2'
    for path in (Path(__file__),Path(__file__).parent.parent/'acquisition/global_candidates.py'):
        rt.required_sources[str(path.relative_to(rt.project))]=base.sha256(path)
    return rt


def receive(obs,policy,rt,options=None):
    if getattr(rt,'mechanism_version',None)!='global_v2' or policy not in POLICIES:raise ValueError('global_v2 runtime/policy required')
    payload=base.receive(obs,TRANSLATE[policy],rt,options)
    payload['mechanism_version']='global_v2'
    payload['global_policy']=policy
    if payload['acquisition'] is not None and payload['acquisition'].get('mechanism_version')!='global_v2':raise ValueError('wrong acquisition implementation')
    return payload


def producer_binding(population):
    population=Path(population).resolve()
    manifest=json.loads((population/'manifest.json').read_text())
    seal=json.loads((population/'observed_seal.json').read_text())
    return dict(manifest_sha256=base.sha256(population/'manifest.json'),observed_seal_sha256=base.sha256(population/'observed_seal.json'),registration_sha256=manifest['registration_sha256'],allocation_sha256=seal['allocation_sha256'])


def validate_producer(rt,population,registration):
    """Read-only replay compatibility: no rewrite or inferred regeneration."""
    population=Path(population).resolve()
    if registration.get('producer_binding')!=producer_binding(population):raise ValueError('original producer binding differs')
    manifest=json.loads((population/'manifest.json').read_text())
    seal=json.loads((population/'observed_seal.json').read_text())
    if seal['status']!='pass' or seal['allocation_sha256']!=registration['allocation_sha256']:raise ValueError('producer allocation differs')
    if seal.get('registration_sha256')!=manifest['registration_sha256']:raise ValueError('producer registration seal differs')
    base.verify_registration(rt.project,manifest['registration'])
    current=base.runtime_binding(rt)
    # Generation and reception may be on different hardware; bind both, compare
    # scientific system/code exactly, never conflate producer and receiver envs.
    for key in ('system','code'):
        if manifest['runtime_binding'][key]!=current[key]:raise ValueError('producer/receiver scientific '+key+' differs')
    for path,digest in seal['files'].items():
        if base.sha256(base.safe_child(population,path))!=digest:raise ValueError('producer seal file differs')
    rows=[json.loads(l) for l in (population/'ledger.jsonl').read_text().splitlines()]
    if len(rows)!=seal['observations'] or len(rows)!=len({r['observation_id'] for r in rows}):raise ValueError('producer rows differ')
    for row in rows:
        stem=row['observation_id']
        if not stem or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in stem):raise ValueError('unsafe observation id')
        observed_path=base.safe_child(population,row['observation_path'])
        if seal['files'].get(row['observation_path'])!=row['observation_sha256'] or base.sha256(observed_path)!=row['observation_sha256']:raise ValueError('observed row not bound by producer seal')
    return rows


def verify_registration(rt,registration):
    if registration.get('mechanism_version')!='global_v2':raise ValueError('global_v2 registration required')
    if tuple(registration.get('policies',()))!=POLICIES:raise ValueError('global_v2 policy allocation differs')
    base.verify_runtime_registration(rt,registration)


def run_population(rt,population,out,registration,*,resume=False,retry_authorization=None):
    with base.writer_lock(out):
        return _run(rt,population,out,registration,resume,retry_authorization)


def _run(rt,population,out,registration,resume,retry_authorization):
    verify_registration(rt,registration)
    population=Path(population).resolve();out=Path(out).resolve()
    rows=validate_producer(rt,population,registration)
    completed={}
    if out.exists():
        if not resume:raise FileExistsError('preserve prior global run')
        manifest=json.loads((out/'manifest.json').read_text())
        if manifest['registration']!=registration or manifest['producer_binding']!=producer_binding(population):raise ValueError('resume binding differs')
        if (out/'ledger.jsonl').exists():
            for line in (out/'ledger.jsonl').read_text().splitlines():
                r=json.loads(line);key=(r['observation_id'],r['policy'])
                if key in completed or base.sha256(base.safe_child(out,r['raw_path']))!=r['raw_sha256']:raise ValueError('resume raw/ledger invalid')
                completed[key]=r
        base.validate_retry(out,completed,retry_authorization)
    else:
        out.mkdir(parents=True);(out/'raw').mkdir()
        base.write_json(out/'manifest.json',dict(registration=registration,producer_binding=producer_binding(population),producer_manifest=json.loads((population/'manifest.json').read_text()),environment=rt.environment,header=rt.header,setup_seconds=rt.setup,pid=os.getpid(),scope='registered replay of original sealed development observations; not fresh generation or confirmation',timing='observed load through full acquisition included in ready; complete adds raw write; setup and ledger write excluded equally'))
    expected={(r['observation_id'],p) for r in rows for p in POLICIES}
    if not set(completed)<=expected:raise ValueError('unexpected saved call')
    def expired(*_):raise TimeoutError('global_v2 registered unit deadline')
    signal.signal(signal.SIGALRM,expired);signal.alarm(int(registration['seconds_limit']))
    try:
        for i,row in enumerate(rows):
            for policy in POLICIES[i%3:]+POLICIES[:i%3]:
                key=(row['observation_id'],policy)
                if key in completed:continue
                path=out/'raw'/f'{key[0]}_{policy}.npz'
                if path.exists():raise FileExistsError('orphan raw requires separate audit')
                identity=dict(observation_id=key[0],policy=policy,input_sha256=row['observation_sha256'],observation_hash=row['observation_hash'],stream_ids=row['stream_ids'],mechanism_version='global_v2')
                base.append_json(out/'attempts.jsonl',dict(identity,event='started',epoch=time.time()))
                t=time.perf_counter()
                try:
                    obs=rt.observed_inputs(rt.evidence,rt.load_bound,population,row)
                    payload=receive(obs,policy,rt,registration['candidate_options']);ready=time.perf_counter()-t
                    digest=rt.evidence.save_artifact(path,payload,identity)
                    item=dict(identity,raw_path=str(path.relative_to(out)),raw_sha256=digest,receiver_ready_seconds=ready,complete_seconds=time.perf_counter()-t,final_syndrome=payload['final_syndrome'],acquisition_executed=payload['acquisition'] is not None)
                    base.append_json(out/'ledger.jsonl',item);base.append_json(out/'attempts.jsonl',dict(item,event='finished'));completed[key]=item
                except BaseException as error:
                    base.append_json(out/'attempts.jsonl',dict(identity,event='failed',exception=repr(error),elapsed_seconds=time.perf_counter()-t));raise
        verify_registration(rt,registration);validate_producer(rt,population,registration)
        if set(completed)!=expected:raise ValueError('incomplete global allocation')
        receipt=dict(status='pass',mechanism_version='global_v2',completed_calls=len(completed),expected_calls=len(expected),ledger_sha256=base.sha256(out/'ledger.jsonl'),manifest_sha256=base.sha256(out/'manifest.json'))
        if not (out/'result.json').exists():base.write_json(out/'result.json',receipt)
        elif json.loads((out/'result.json').read_text())!=receipt:raise ValueError('terminal receipt differs')
    finally:signal.alarm(0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=base.PROJECT);p.add_argument('--source',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--population',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--registration',type=Path,required=True);p.add_argument('--resume',action='store_true');p.add_argument('--retry-authorization',type=Path);a=p.parse_args()
    rt=bootstrap(a.project,a.source,a.baseline);reg=json.loads(a.registration.read_text())
    run_population(rt,a.population,a.out,reg,resume=a.resume,retry_authorization=a.retry_authorization)

if __name__=='__main__':main()
