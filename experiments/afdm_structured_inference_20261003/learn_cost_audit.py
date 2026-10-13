"""Frozen-weight local inference cost audit; no new training or observations."""
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time

import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.afdm_structured_inference_20261003.common import ARTIFACT,dump,run
from experiments.afdm_structured_inference_20261003.learn import (
    CONFIG as TRAIN_CONFIG, V, SharedPotential, IndependentHeads, features_for,
    predict, meanfield_statistics, meanfield_prediction)
from experiments.afdm_structured_inference_20261003.potential import finite_potential,real_pack
from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen

SOURCE=ARTIFACT/'execution/learn_v1'
CONFIG=json.loads((ARTIFACT/'learn_cost_config.json').read_text())


def geometry_input(record,pilot,physical):
    """Rebuild the actual two CPP operators from supplied local geometry."""
    n=2;c1=record['stride']/(2*n);c2=(np.sqrt(2)-1)/(2*n*n)
    operators=np.stack([np.column_stack([
        physical.Channel(n,c1,c2,[delay],[nu],[1]).apply(e) for e in np.eye(n)])
        for delay,nu in [(0,record['center']),(1,record['center']+.47)]])
    return dict(operators=operators,pilot=pilot)


def prepare_geometry(record,pilot,physical,state_grid,method):
    case=geometry_input(record,pilot,physical)
    if method in ('analytic_meanfield','learned_step','exact_teacher'):
        case.update(state_grid)
        case['f']=real_pack(np.einsum('kp,pij,kj->ki',case['h'],case['operators'],case['pilot']+case['d']))
        if method!='exact_teacher':
            case['diff_f'],case['diff_energy']=meanfield_statistics(case,TRAIN_CONFIG['sigma2'])
    return case


def one_observation(method,case,y,xi,model=None,alpha=1.):
    start=time.perf_counter()
    eta=2*real_pack(y)/TRAIN_CONFIG['sigma2']
    if model is not None:
        x=torch.as_tensor(features_for(case,eta,xi,TRAIN_CONFIG['sigma2'])[None,:])
    elif method!='exact_teacher':
        logits=case['diff_f']@eta-case['diff_energy']
        projection=case['diff_f']@V
    input_seconds=time.perf_counter()-start
    start=time.perf_counter()
    if model is not None:
        m,r,_=predict(model,x)
        mean,response=m.detach().numpy()[0],r.detach().numpy()[0]
    elif method=='exact_teacher':
        result=finite_potential(case['z'],case['f'],case['log_prior'],eta,xi,TRAIN_CONFIG['sigma2'])
        mean,response=result['mean_z'],result['cov_z_f']@V
    else:
        mean,response=meanfield_prediction(xi,logits,projection,alpha)
    prediction_seconds=time.perf_counter()-start
    return mean,response,input_seconds,prediction_seconds


def execute_audit(output):
    started=time.monotonic();cpu_started=time.process_time()
    registration=json.loads((SOURCE/'registration.json').read_text())
    changed=[p for p,h in registration['source_sha256'].items()
             if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    if changed:
        raise RuntimeError(f'frozen training sources changed: {changed}')
    data=np.load(SOURCE/'dataset.npz',allow_pickle=False)
    all_records=json.loads((SOURCE/'dataset_records.json').read_text())
    records=[r for r in all_records if r['split']=='test' and r['variant']=='base']
    if len(records)!=CONFIG['test_rows'] or len(set(r['cluster'] for r in records))!=8:
        raise AssertionError('frozen main-test population mismatch')
    physical,_,_=load_frozen()
    with np.load(SOURCE/'geometry_test_00.npz',allow_pickle=False) as geometry:
        state_grid={k:geometry[k].copy() for k in ['z','h','d','log_prior']}
        pilot=geometry['pilot'].copy()
    models={};model_load=[]
    for kind,cls in [('shared',SharedPotential),('independent',IndependentHeads)]:
        for seed in TRAIN_CONFIG['network_seeds']:
            begin=time.perf_counter();name=f'{kind}_seed{seed}'
            model=cls();model.load_state_dict(torch.load(SOURCE/f'{name}.pt',map_location='cpu',weights_only=True));model.eval()
            models[name]=model
            model_load.append(dict(method=name,seconds=time.perf_counter()-begin,
                                   parameter_bytes=sum(p.numel()*p.element_size() for p in model.parameters())))
    alpha=json.loads((SOURCE/'learned_step.json').read_text())['alpha']
    methods=[*models,'analytic_meanfield','learned_step','exact_teacher']
    saved={name:np.load(SOURCE/f'predictions_{name}.npz',allow_pickle=False) for name in methods}
    cost_rows=[];predictions=[];schedules=[]
    max_mean_error=0.;max_response_error=0.
    rng=np.random.default_rng([20261003,104129,72,1001])
    startup_seconds=time.monotonic()-started
    for repeat in range(CONFIG['repeats']):
        schedule=[(method,cache_mode) for method in methods for cache_mode in ['cold_geometry','eight_observation_geometry']]
        rng.shuffle(schedule);schedules.append(schedule)
        for method,cache_mode in schedule:
            model=models.get(method);scale=alpha if method=='learned_step' else 1.
            for cluster in range(8):
                group=[r for r in records if r['cluster']==cluster]
                if len(group)!=8:
                    raise AssertionError('geometry amortization must use exactly eight observed records')
                cached=None;shared_seconds=0.
                if cache_mode=='eight_observation_geometry':
                    begin=time.perf_counter()
                    cached=prepare_geometry(group[0],pilot,physical,state_grid,method)
                    shared_seconds=time.perf_counter()-begin
                for record in group:
                    if time.monotonic()-started>CONFIG['wall_cap_seconds'] or time.process_time()-cpu_started>CONFIG['cpu_cap_seconds']:
                        raise TimeoutError('local inference audit exceeded its own tighter cap')
                    index=record['index'];yr=data['y'][index];y=yr[:2]+1j*yr[2:];xi=data['xi'][index]
                    # Cost interval excludes audit parity checks and output serialization.
                    begin=time.perf_counter()
                    if cached is None:
                        case=prepare_geometry(record,pilot,physical,state_grid,method)
                        geometry_seconds=time.perf_counter()-begin
                    else:
                        case=cached;geometry_seconds=0.
                    mean,response,input_seconds,prediction_seconds=one_observation(method,case,y,xi,model,scale)
                    observed_seconds=time.perf_counter()-begin
                    amortized=observed_seconds+shared_seconds/len(group)
                    mean_error=float(np.max(abs(mean-saved[method]['mean'][index])))
                    response_error=float(np.max(abs(response-saved[method]['response'][index])))
                    max_mean_error=max(max_mean_error,mean_error);max_response_error=max(max_response_error,response_error)
                    if max(mean_error,response_error)>2e-12:
                        raise AssertionError('single-observation full pipeline changed frozen predictions')
                    cost_rows.append(dict(method=method,cache_mode=cache_mode,repeat=repeat,cluster=cluster,
                        dataset_index=index,observation=record['observation'],geometry_seconds=geometry_seconds,
                        shared_geometry_seconds=shared_seconds,geometry_amortized_seconds=shared_seconds/len(group),
                        input_seconds=input_seconds,prediction_seconds=prediction_seconds,
                        observed_seconds=observed_seconds,total_seconds=amortized,
                        mean_parity_error=mean_error,response_parity_error=response_error))
                    predictions.append(np.concatenate([mean,response]))
    dump(output/'cost_records.json',cost_rows)
    np.savez(output/'audited_outputs.npz',mean_response=np.array(predictions))
    summary={}
    for method in methods:
        summary[method]={}
        for mode in ['cold_geometry','eight_observation_geometry']:
            subset=[r for r in cost_rows if r['method']==method and r['cache_mode']==mode]
            summary[method][mode]={key:dict(mean=float(np.mean([r[key] for r in subset])),
                       median=float(np.median([r[key] for r in subset])),
                       p95=float(np.quantile([r[key] for r in subset],.95)))
                for key in ['total_seconds','geometry_seconds','geometry_amortized_seconds','input_seconds','prediction_seconds']}
            summary[method][mode]['calls']=len(subset)
    if len(cost_rows)!=9*2*CONFIG['repeats']*CONFIG['test_rows']:
        raise AssertionError('timing grid not complete')
    dump(output/'schedule.json',schedules)
    return dict(status='completed frozen-data local inference cost audit',rows=len(cost_rows),summary=summary,
        max_mean_parity_error=max_mean_error,max_response_parity_error=max_response_error,
        startup_seconds=startup_seconds,model_load=model_load,
        state_grid_bytes=sum(v.nbytes for v in state_grid.values()),
        process_peak_rss_raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        peak_rss_units='bytes on this macOS runtime; process includes torch and all loaded arms',
        tighter_cap=dict(cpu_seconds=CONFIG['cpu_cap_seconds'],wall_seconds=CONFIG['wall_cap_seconds']),
        observations='64 saved base test observations; three timing repeats, zero new samples and zero training',
        measured_input_boundary='observed local center/stride, known pilot/noise, complex y and xi; geometry state rebuilt or amortized over exactly8 observations',
        finite_teacher_caveat='existing public moment API computes small covariance blocks as well as mean/JVP; not an intrinsic complexity lower bound',
        exclusions='interpreter/library startup, model load, file IO, LDPC, support discovery and receiver-global initialization excluded from per-call windows; startup/model load separately recorded',
        evidence_scope='single local N2 P2 factor on shared machine, no production or independent latency qualification')


def calculate(output):
    """Enforce the audit's 30 CPU / 60 wall cap inside the looser common cap."""
    previous_alarm=signal.getitimer(signal.ITIMER_REAL)
    previous_prof_handler=signal.getsignal(signal.SIGPROF)
    old_prof=signal.getitimer(signal.ITIMER_PROF)
    if old_prof[0]>0:
        raise RuntimeError('CPU timer already owned by another local activity')
    def cpu_timeout(_signum,_frame):
        raise TimeoutError('local inference audit CPU cap exceeded')
    signal.signal(signal.SIGPROF,cpu_timeout)
    signal.setitimer(signal.ITIMER_PROF,CONFIG['cpu_cap_seconds'])
    signal.setitimer(signal.ITIMER_REAL,CONFIG['wall_cap_seconds'])
    started=time.monotonic();cpu_started=time.process_time()
    try:
        result=execute_audit(output)
        if time.process_time()-cpu_started>CONFIG['cpu_cap_seconds'] or time.monotonic()-started>CONFIG['wall_cap_seconds']:
            raise TimeoutError('local inference audit tighter cap exceeded')
        return result
    finally:
        signal.setitimer(signal.ITIMER_PROF,0)
        signal.signal(signal.SIGPROF,previous_prof_handler)
        remaining=max(.001,previous_alarm[0]-(time.monotonic()-started)) if previous_alarm[0] else 0.
        signal.setitimer(signal.ITIMER_REAL,remaining,previous_alarm[1])


if __name__=='__main__':
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    old_registration=json.loads((SOURCE/'registration.json').read_text())
    bound_inputs=[SOURCE/'registration.json',SOURCE/'dataset.npz',SOURCE/'dataset_records.json',
                  SOURCE/'learned_step.json',ARTIFACT/'learn_cost_config.json',
                  *sorted(SOURCE.glob('geometry_test_*.npz')),*sorted(SOURCE.glob('*.pt')),
                  *sorted(SOURCE.glob('predictions_*.npz'))]
    source_files=[ROOT/p for p in old_registration['source_sha256']]
    run('learn_v2',CONFIG,[__file__,*source_files,*bound_inputs],calculate)
