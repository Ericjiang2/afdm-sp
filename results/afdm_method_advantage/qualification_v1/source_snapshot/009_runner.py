"""Five complete receiver policies with separate original producer identity."""
import argparse
import json
import math
import statistics
from pathlib import Path
import signal
import sys
import time
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'experiments'))
import wrapper as base
import wrapper_global as global_receiver
from osd1 import acquire_osd1,GRID
from thread_binding import blas_binding,verify_effective

POLICIES=('cascade','residual_global','geometry_global','osd1_budget','osd1_full')


def bootstrap(project=base.PROJECT,source=None,baseline=None):
    pre=blas_binding()
    rt=global_receiver.bootstrap(project,source,baseline)
    rt=SimpleNamespace(**vars(rt));rt.control_version='strong_osd1_v1'
    rt.environment=dict(rt.environment,effective_blas_pre_bootstrap=pre,effective_blas_post_bootstrap=blas_binding())
    for p in sorted(HERE.glob('*.py')):rt.required_sources[str(p.relative_to(rt.project))]=base.sha256(p)
    return rt


def verify_registration(rt,reg):
    if reg.get('mechanism_version')!='strong_osd1_v1' or tuple(reg.get('policies',()))!=POLICIES:raise ValueError('strong OSD five-policy registration required')
    if type(reg.get('osd1_budget_k')) is not int or reg['osd1_budget_k'] not in GRID:raise ValueError('frozen timing-calibrated k absent')
    verify_effective(rt)
    base.verify_runtime_registration(rt,reg)
    if not reg.get('calibration_receipt_sha256') or not reg.get('calibration_receipt_path'):raise ValueError('calibration provenance absent')
    path=base.safe_child(rt.project,reg['calibration_receipt_path'])
    if base.sha256(path)!=reg['calibration_receipt_sha256']:raise ValueError('calibration receipt differs')
    receipt=json.loads(path.read_text())
    validate_calibration(path,receipt,reg)


def positive_time(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
        raise ValueError('finite positive '+label+' required')
    return float(value)


def validate_calibration(path,receipt,reg):
    """Check actual registered calibration calls, provenance and chosen budget."""
    root=Path(path).parent
    if receipt.get('status')!='pass':raise ValueError('incomplete calibration')
    for filename,key in (('manifest.json','manifest_sha256'),('ledger.jsonl','ledger_sha256')):
        if base.sha256(root/filename)!=receipt[key]:raise ValueError('calibration evidence differs')
    manifest=json.loads((root/'manifest.json').read_text());calreg=manifest['registration']
    if calreg.get('mechanism_version')!='strong_osd1_calibration_v1' or calreg.get('k_grid')!=list(GRID):raise ValueError('calibration mechanism/grid differs')
    for field in ('source_files','runtime_binding','producer_binding','allocation_sha256','candidate_options'):
        if field not in calreg or calreg[field]!=reg.get(field):raise ValueError('calibration '+field+' differs from receiver')
    if manifest['environment']!=reg['runtime_binding']['environment']:raise ValueError('calibration actual environment differs')
    repeats=calreg.get('repeats');n_states=calreg.get('expected_observable_triggers')
    if type(repeats) is not int or repeats<3 or type(n_states) is not int or n_states<1:raise ValueError('calibration repetition/state contract invalid')
    states=manifest['source_states'];sources={r['observation_id']:r['raw_sha256'] for r in states}
    if len(states)!=n_states or len(sources)!=n_states:raise ValueError('calibration source-state allocation differs')
    expected={(stem,k,repeat) for stem in sources for k in (None,*GRID) for repeat in range(repeats)}
    expected_count=len(expected)
    if receipt.get('expected_calls')!=expected_count or receipt.get('completed_calls')!=expected_count:raise ValueError('calibration self-reported count differs from plan')
    def identity(row):
        stem=row['observation_id'];k=row['k'];repeat=row['repeat']
        key=(stem,k,repeat)
        policy='residual_global_reference' if k is None else f'osd1_k{k}'
        if key not in expected or row['policy']!=policy or row['reference_raw_sha256']!=sources[stem]:raise ValueError('calibration call identity differs')
        if type(repeat) is not int or (k is not None and type(k) is not int):raise ValueError('calibration call identity type differs')
        return key
    rows=[json.loads(l) for l in (root/'ledger.jsonl').read_text().splitlines()]
    indexed={}
    for row in rows:
        key=identity(row)
        if key in indexed:raise ValueError('duplicate calibration ledger identity')
        positive_time(row['module_seconds'],'module timing');positive_time(row['complete_artifact_seconds'],'complete timing')
        if row['complete_artifact_seconds']<row['module_seconds']:raise ValueError('calibration complete time shorter than module')
        if row['physical_scores']!=(16 if row['k'] is None else row['k']+1):raise ValueError('calibration candidate-call count differs')
        raw=base.safe_child(root,row['raw_path'])
        if base.sha256(raw)!=row['raw_sha256']:raise ValueError('calibration raw hash differs')
        indexed[key]=row
    if set(indexed)!=expected:raise ValueError('calibration ledger does not cover planned calls')
    events=[json.loads(l) for l in (root/'attempts.jsonl').read_text().splitlines()]
    starts=set();finishes=set()
    for event in events:
        key=identity(event)
        if event['event']=='started':
            if key in starts:raise ValueError('duplicate calibration start')
            starts.add(key)
        elif event['event']=='finished':
            if key not in starts or key in finishes:raise ValueError('calibration finish/start order differs')
            finishes.add(key)
            if {k:v for k,v in event.items() if k!='event'}!=indexed[key]:raise ValueError('calibration finished evidence differs from ledger')
        else:raise ValueError('failed/unknown calibration attempt cannot support completed calibration')
    if starts!=expected or finishes!=expected:raise ValueError('calibration attempts do not cover planned calls')
    if receipt.get('attempts_sha256')!=base.sha256(root/'attempts.jsonl'):raise ValueError('calibration attempts receipt differs')
    target=statistics.median(r['module_seconds'] for r in rows if r['k'] is None)
    positive_time(receipt.get('target_seconds'),'target')
    if not math.isclose(receipt['target_seconds'],target,rel_tol=1e-12,abs_tol=0.):raise ValueError('calibration target differs from actual reference calls')
    saved_medians=receipt['median_module_seconds']
    if set(saved_medians)!={str(k) for k in GRID}:raise ValueError('calibration median inventory differs')
    medians={k:statistics.median(r['module_seconds'] for r in rows if r['k']==k) for k in GRID}
    for k,value in medians.items():
        positive_time(saved_medians[str(k)],'K median')
        if not math.isclose(saved_medians[str(k)],value,rel_tol=1e-12,abs_tol=0.):raise ValueError('calibration median differs from actual calls')
    feasible=[k for k in GRID if medians[k]<=target]
    suggested=max(feasible) if feasible else None
    if receipt.get('suggested_k')!=suggested:raise ValueError('calibration suggested K differs from measured feasibility')
    selected=reg['osd1_budget_k']
    if selected not in feasible or not reg.get('budget_choice_reason'):raise ValueError('selected K itself exceeds measured budget or lacks choice reason')


def receive(obs,policy,rt,k):
    if getattr(rt,'control_version',None)!='strong_osd1_v1' or policy not in POLICIES or k not in GRID:raise ValueError('invalid controls runtime/policy/k')
    verify_effective(rt)
    if policy in global_receiver.POLICIES:
        payload=global_receiver.receive(obs,policy,rt)
    else:
        def adapter(h,llr,ch,y,pilot,sigma2,*,scale,mode,**options):
            if mode!='geometry' or options!=base.OPTIONS:raise ValueError('frozen acquisition call contract differs')
            return acquire_osd1(h,llr,ch,y,pilot,sigma2,scale=scale,k=k if policy=='osd1_budget' else None,full=policy=='osd1_full',gain_precision=0.)
        private=SimpleNamespace(**vars(rt));private.acquire=adapter
        payload=base.receive(obs,'cascade_geometry',private)
        if payload['acquisition'] is not None and payload['acquisition']['method']!=policy:raise ValueError('control implementation differs')
    payload['comparison_version']='strong_osd1_v1';payload['comparison_policy']=policy
    return payload


def run_population(rt,population,out,reg,*,resume=False,retry_authorization=None):
    with base.writer_lock(out):
        return _run(rt,Path(population).resolve(),Path(out).resolve(),reg,resume,retry_authorization)


def _run(rt,population,out,reg,resume,retry_authorization):
    verify_registration(rt,reg)
    rows=global_receiver.validate_producer(rt,population,reg)
    completed={}
    if out.exists():
        if not resume:raise FileExistsError('preserve previous control run')
        m=json.loads((out/'manifest.json').read_text())
        if m['registration']!=reg or m['producer_binding']!=global_receiver.producer_binding(population):raise ValueError('resume binding differs')
        if (out/'ledger.jsonl').exists():
            for line in (out/'ledger.jsonl').read_text().splitlines():
                r=json.loads(line);key=(r['observation_id'],r['policy'])
                if key in completed or base.sha256(base.safe_child(out,r['raw_path']))!=r['raw_sha256']:raise ValueError('invalid resume raw/ledger')
                completed[key]=r
        base.validate_retry(out,completed,retry_authorization)
    else:
        out.mkdir(parents=True);(out/'raw').mkdir()
        base.write_json(out/'manifest.json',dict(registration=reg,producer_binding=global_receiver.producer_binding(population),producer_manifest=json.loads((population/'manifest.json').read_text()),setup_seconds=rt.setup,environment=rt.environment,header=rt.header,scope='five-policy development replay; source observations reused, not fresh confirmation',timing='ready starts before observed load and includes complete cascade/GF2/all generation/all scoring; complete adds raw write; context setup and ledger write excluded equally',candidate_counts=dict(global_methods=16,osd1_budget=reg['osd1_budget_k']+1,osd1_full=1025),cost_claim='budget-calibrated fixed k; actual timings must be compared, not exact equal cost'))
    expected={(r['observation_id'],p) for r in rows for p in POLICIES}
    if not set(completed)<=expected:raise ValueError('unexpected saved control calls')
    def expired(*_):raise TimeoutError('registered control unit deadline')
    signal.signal(signal.SIGALRM,expired);signal.alarm(int(reg['seconds_limit']))
    try:
        for index,row in enumerate(rows):
            for policy in POLICIES[index%5:]+POLICIES[:index%5]:
                key=(row['observation_id'],policy)
                if key in completed:continue
                path=out/'raw'/f'{key[0]}_{policy}.npz'
                if path.exists():raise FileExistsError('orphan raw requires audit')
                identity=dict(observation_id=key[0],policy=policy,input_sha256=row['observation_sha256'],observation_hash=row['observation_hash'],stream_ids=row['stream_ids'],comparison_version='strong_osd1_v1')
                base.append_json(out/'attempts.jsonl',dict(identity,event='started',epoch=time.time()));t=time.perf_counter()
                try:
                    obs=rt.observed_inputs(rt.evidence,rt.load_bound,population,row)
                    payload=receive(obs,policy,rt,reg['osd1_budget_k']);ready=time.perf_counter()-t
                    digest=rt.evidence.save_artifact(path,payload,identity)
                    item=dict(identity,raw_path=str(path.relative_to(out)),raw_sha256=digest,receiver_ready_seconds=ready,complete_seconds=time.perf_counter()-t,final_syndrome=payload['final_syndrome'],acquisition_executed=payload['acquisition'] is not None)
                    base.append_json(out/'ledger.jsonl',item);base.append_json(out/'attempts.jsonl',dict(item,event='finished'));completed[key]=item
                except BaseException as error:
                    base.append_json(out/'attempts.jsonl',dict(identity,event='failed',exception=repr(error),elapsed_seconds=time.perf_counter()-t));raise
        verify_registration(rt,reg);global_receiver.validate_producer(rt,population,reg)
        if set(completed)!=expected:raise ValueError('incomplete five-policy run')
        receipt=dict(status='pass',completed_calls=len(completed),expected_calls=len(expected),ledger_sha256=base.sha256(out/'ledger.jsonl'),manifest_sha256=base.sha256(out/'manifest.json'),comparison_version='strong_osd1_v1')
        if not (out/'result.json').exists():base.write_json(out/'result.json',receipt)
        elif json.loads((out/'result.json').read_text())!=receipt:raise ValueError('terminal receipt differs')
    finally:signal.alarm(0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=base.PROJECT);p.add_argument('--source',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--population',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--registration',type=Path,required=True);p.add_argument('--resume',action='store_true');p.add_argument('--retry-authorization',type=Path);a=p.parse_args()
    rt=bootstrap(a.project,a.source,a.baseline)
    run_population(rt,a.population,a.out,json.loads(a.registration.read_text()),resume=a.resume,retry_authorization=a.retry_authorization)

if __name__=='__main__':main()
