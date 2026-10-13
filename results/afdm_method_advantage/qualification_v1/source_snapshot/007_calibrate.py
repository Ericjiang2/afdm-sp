"""Observed-only OSD1 module timing calibration; never imports generator/scorer.

Consumes saved pre-acquisition states. No native receiver calls and no truth.
Run only after explicit timing clearance and calibration registration freeze.
"""
import argparse
import json
from pathlib import Path
import signal
import time
import numpy as np
import runner
from osd1 import acquire_osd1,GRID

base=runner.base


def calibrate(rt,population,reference_run,out,registration):
    with base.writer_lock(out):
        return _calibrate(rt,Path(population).resolve(),Path(reference_run).resolve(),Path(out).resolve(),registration)


def _calibrate(rt,population,reference,out,reg):
    if reg.get('mechanism_version')!='strong_osd1_calibration_v1' or reg.get('k_grid')!=list(GRID) or type(reg.get('repeats')) is not int or reg['repeats']<3:raise ValueError('calibration protocol differs')
    runner.verify_effective(rt)
    base.verify_runtime_registration(rt,reg)
    observed=runner.global_receiver.validate_producer(rt,population,reg)
    obs_lookup={r['observation_id']:r for r in observed}
    receipt=json.loads((reference/'result.json').read_text());manifest=json.loads((reference/'manifest.json').read_text())
    if base.sha256(reference/'result.json')!=reg['reference_result_sha256']:raise ValueError('reference receipt binding differs')
    if receipt['status']!='pass' or receipt['completed_calls']!=receipt['expected_calls']:raise ValueError('reference incomplete')
    if base.sha256(reference/'manifest.json')!=receipt['manifest_sha256'] or base.sha256(reference/'ledger.jsonl')!=receipt['ledger_sha256']:raise ValueError('reference manifest/ledger differs')
    base.verify_registration(rt.project,manifest['registration'])
    if manifest['producer_binding']!=reg['producer_binding']:raise ValueError('reference observation producer differs')
    ledger=[json.loads(l) for l in (reference/'ledger.jsonl').read_text().splitlines()]
    if len(ledger)!=receipt['completed_calls'] or len({(r['observation_id'],r['policy']) for r in ledger})!=len(ledger):raise ValueError('reference allocation differs')
    states=[]
    for row in ledger:
        if row['policy']!='residual_global' or not row['acquisition_executed']:continue
        if row['observation_id'] not in obs_lookup:raise ValueError('reference observation absent')
        path=base.safe_child(reference,row['raw_path'])
        if base.sha256(path)!=row['raw_sha256']:raise ValueError('reference raw differs')
        payload,identity=rt.evidence.load_artifact(path)
        original=obs_lookup[row['observation_id']]
        if identity['observation_id']!=row['observation_id'] or identity['input_sha256']!=original['observation_sha256']:raise ValueError('reference input identity differs')
        if payload['acquisition'] is None or not np.any(rt.code['H']@payload['pre_acquisition_decoder']['decoded']%2):raise ValueError('reference trigger inconsistent')
        states.append((row,payload))
    if len(states)!=reg['expected_observable_triggers']:raise ValueError('registered observable trigger count differs')
    if not states:raise ValueError('no states for calibration')
    out.mkdir(parents=True,exist_ok=False);(out/'raw').mkdir()
    base.write_json(out/'manifest.json',dict(registration=reg,target_seconds=None,target_rule='median onsite residual_global module time across all observed states and repeated timings; historic v2 latency excluded',source_states=[dict(observation_id=r['observation_id'],raw_sha256=r['raw_sha256']) for r,_ in states],environment=rt.environment,scope='saved-state module timing only; no complete receiver timing or truth scoring'))
    records=[]
    def expired(*_):raise TimeoutError('registered calibration deadline')
    signal.signal(signal.SIGALRM,expired);signal.alarm(int(reg['seconds_limit']))
    try:
        for i,(row,saved) in enumerate(states):
            obs=rt.observed_inputs(rt.evidence,rt.load_bound,population,obs_lookup[row['observation_id']])
            channel=base.final_channel(saved,rt,len(obs['y']))
            llr=saved['pre_acquisition_decoder']['raw_app']
            methods=(None,*GRID)
            for repeat in range(reg['repeats']):
                offset=(i*reg['repeats']+repeat)%len(methods)
                for k in methods[offset:]+methods[:offset]:
                    label='residual_global_reference' if k is None else f'osd1_k{k}'
                    identity=dict(observation_id=row['observation_id'],policy=label,k=k,repeat=repeat,reference_raw_sha256=row['raw_sha256'])
                    base.append_json(out/'attempts.jsonl',dict(identity,event='started',epoch=time.time()));start=time.perf_counter()
                    try:
                        runner.verify_effective(rt)
                        if k is None:
                            result=rt.acquire(rt.code['H'],llr,channel,obs['y'],obs['pilot'],obs['sigma2'],scale=np.sqrt(1-rt.system.rho),mode='osd',**base.OPTIONS)
                        else:
                            result=acquire_osd1(rt.code['H'],llr,channel,obs['y'],obs['pilot'],obs['sigma2'],scale=np.sqrt(1-rt.system.rho),k=k)
                        rt.finite(result)
                        path=out/'raw'/f'{row["observation_id"]}_{label}_r{repeat}.npz'
                        if path.exists():raise FileExistsError('calibration artifact exists')
                        digest=rt.evidence.save_artifact(path,result,identity)
                        item=dict(identity,module_seconds=result['timing']['total_seconds'],complete_artifact_seconds=time.perf_counter()-start,physical_scores=result['counts']['physical_scores'],raw_path=str(path.relative_to(out)),raw_sha256=digest)
                        records.append(item);base.append_json(out/'ledger.jsonl',item);base.append_json(out/'attempts.jsonl',dict(item,event='finished'))
                    except BaseException as error:
                        base.append_json(out/'attempts.jsonl',dict(identity,event='failed',elapsed_seconds=time.perf_counter()-start,exception=repr(error)));raise
        runner.verify_effective(rt);base.verify_runtime_registration(rt,reg);runner.global_receiver.validate_producer(rt,population,reg)
        target=float(np.median([r['module_seconds'] for r in records if r['k'] is None]))
        medians={str(k):float(np.median([r['module_seconds'] for r in records if r['k']==k])) for k in GRID}
        feasible=[k for k in GRID if medians[str(k)]<=target]
        summary=dict(status='pass',expected_calls=len(states)*(len(GRID)+1)*reg['repeats'],completed_calls=len(records),target_seconds=target,reference_timing_calls=sum(r['k'] is None for r in records),distinct_observed_states=len(states),repeats=reg['repeats'],repeats_are_independent_frames=False,median_module_seconds=medians,suggested_k=max(feasible) if feasible else None,selection_status='main must freeze final k in independent receiver registration; no automatic receiver launch',manifest_sha256=base.sha256(out/'manifest.json'),ledger_sha256=base.sha256(out/'ledger.jsonl'),attempts_sha256=base.sha256(out/'attempts.jsonl'))
        base.write_json(out/'result.json',summary)
        return summary
    finally:signal.alarm(0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=base.PROJECT);p.add_argument('--source',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--population',type=Path,required=True);p.add_argument('--reference-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--registration',type=Path,required=True);a=p.parse_args()
    rt=runner.bootstrap(a.project,a.source,a.baseline)
    print(json.dumps(calibrate(rt,a.population,a.reference_run,a.out,json.loads(a.registration.read_text())),indent=2))

if __name__=='__main__':main()
