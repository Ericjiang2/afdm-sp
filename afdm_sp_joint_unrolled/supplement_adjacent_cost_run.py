"""One exclusive cost collector: 10 warmup and 512 measurement blocks per SNR."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace

for _name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_name]='1'

import numpy as np
import scipy
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.supplement_adjacent_run import rng_state,save_state,setup
from afdm_sp_joint_unrolled.supplement_data import _read_json,campaign_rng
from afdm_sp_joint_unrolled.supplement_profile import score_errors
from afdm_sp_joint_unrolled.supplement_scope import ARMS,reserve,validate_scope
from afdm_sp_joint_unrolled.supplement_timing import _bounded_json,_validate_result
from afdm_sp_joint_unrolled.supplement_timing_integrity import OutputMeter


def validate_telemetry(state, allowed_pid):
    if set(state['compute_pids'])-{allowed_pid}:
        raise ValueError('another GPU process entered exclusive COST collection')
    if state['numerical_threads']!=1 or state['interop_threads']!=1:
        raise ValueError('cost numerical threading changed')
    if state['load_average'][0]>state['cpu_count']-16:
        raise ValueError('shared CPU headroom exhausted during COST')
    if state['temperature_C']>85:
        raise ValueError('GPU exceeds declared85C operational ceiling')
    if state['disk_free_bytes']<2_000_000_000:
        raise ValueError('cost filesystem free-space floor crossed')
    if state['prior_workers_alive']:
        raise ValueError('a previous task worker is still active during COST')


def telemetry(hooks,root,prior_workers):
    state=hooks.telemetry('cuda:0')
    fields='temperature.gpu,clocks.current.sm,clocks.current.memory,power.draw,pstate'
    extra=subprocess.run(['nvidia-smi','--id='+state['gpu_uuid'],'--query-gpu='+fields,
        '--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10).stdout.strip().split(',')
    if len(extra)!=5:
        raise ValueError('incomplete GPU temperature/clock telemetry')
    state['temperature_C']=float(extra[0]);state['SM_MHz']=float(extra[1])
    state['memory_MHz']=float(extra[2]);state['power_W']=float(extra[3]);state['pstate']=extra[4].strip()
    state['host_CPU_ticks']=[int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
    state['host_meminfo']=Path('/proc/meminfo').read_text()
    state['host_diskstats']=Path('/proc/diskstats').read_text()
    state['process_io']=Path('/proc/self/io').read_text()
    state['disk_free_bytes']=shutil.disk_usage(root).free
    state['prior_workers_alive']=[]
    for worker in prior_workers:
        proc=Path('/proc')/str(worker['pid'])/'stat'
        if proc.exists() and int(proc.read_text().rsplit(')',1)[1].split()[19])==worker['start_ticks']:
            state['prior_workers_alive'].append(worker)
    return state


def record_telemetry(hooks,root,prior_workers,path,publish):
    state=telemetry(hooks,root,prior_workers)
    publish(path,state)
    # Rejected observations are evidence too; publish before enforcing the gate.
    validate_telemetry(state,os.getpid())
    return state


def validate_cost_contract(cost,manifest,device):
    if (cost['status']!='frozen' or cost['n_per_snr']!=512 or cost['physical_N']!=1024
            or cost['new_F']!=dict(warmup=90,measurement=4608,total=4698)
            or manifest['methods']!=cost['methods'] or device!='cuda:0'
            or manifest['admitted_purposes']!=['cost-warmup','cost-measurement']):
        raise ValueError('cost collector differs from frozen three-arm512 scope')


def execute(args):
    manifest=_read_json(args.manifest,args.manifest_sha256)
    validate_scope(manifest)
    cost=_read_json(Path(manifest['cost_contract']['path']),manifest['cost_contract']['sha256'])
    validate_cost_contract(cost,manifest,args.device)
    environment=dict(numpy=np.__version__,scipy=scipy.__version__,torch=torch.__version__,cuda_runtime=torch.version.cuda)
    if environment!=manifest['numerical_environment']:
        raise ValueError('COST numerical environment differs from the admitted cohort')
    started=time.time()
    deadline=min(args.deadline_unix,manifest['deadline_unix'])
    if not started<deadline<=manifest['cost_runtime']['deadline_unix']:
        raise ValueError('cost collection deadline outside pipeline budget')
    stages=['cost-warmup','cost-measurement']
    outputs={name:args.root/name for name in stages}
    meters={}
    reservations={}
    counts={name:dict(attempted_F=0,completed_F=0) for name in stages}
    active=None
    for stage in stages:
        outputs[stage].mkdir(exist_ok=False)
        reserved=cost['bytes']['warmup' if stage=='cost-warmup' else 'measurement']
        meters[stage]=OutputMeter(outputs[stage],reserved-1024*1024)
    old_alarm,old_term=signal.getsignal(signal.SIGALRM),signal.getsignal(signal.SIGTERM)

    def stop(_signal,_frame):
        raise TimeoutError('exclusive cost collection deadline or termination reached')

    def publish(stage,path,value):
        meter=meters[stage]
        _bounded_json(path,value,outputs[stage],meter.limit,meter=meter)

    try:
        signal.signal(signal.SIGALRM,stop);signal.signal(signal.SIGTERM,stop)
        signal.setitimer(signal.ITIMER_REAL,max(.001,
            min(deadline,manifest['cost_runtime']['warmup_deadline_unix'])-time.time()))
        for stage in stages:
            domain=manifest['data_scopes'][stage]
            identities=[dict(split='timing',family='F_C',block=b,snr_db=s,arm=a,repeat=0)
                for b in range(domain['block_start'],domain['block_stop']) for s in (7,8,9) for a in ARMS]
            reserved=cost['bytes']['warmup' if stage=='cost-warmup' else 'measurement']
            reservations[stage]=reserve(manifest,args.manifest,args.manifest_sha256,outputs[stage],
                stage,identities,bytes_reserved=reserved)
        setup_started=time.perf_counter()
        setup_args=SimpleNamespace(manifest=args.manifest,manifest_sha256=args.manifest_sha256,
            out=outputs['cost-warmup'],purpose='cost-warmup',device='cuda:0',snrs=[7,8,9],arms=list(ARMS))
        hooks,guard,data,code,system,receivers,build_times,p0=setup(setup_args,manifest)
        hooks.sync('cuda:0')
        setup_seconds=time.perf_counter()-setup_started
        meters['cost-warmup'].adopt_tree(outputs['cost-warmup']/'code-cache')
        target=outputs['cost-measurement']/'code-cache'
        target.mkdir()
        shutil.copy2(code['cache_path'],target/Path(code['cache_path']).name)
        meters['cost-measurement'].adopt_tree(target)
        for stage in stages:
            out,meter=outputs[stage],meters[stage]
            domain=manifest['data_scopes'][stage]
            stage_started=time.time()
            stage_deadline=min(deadline,manifest['cost_runtime']['warmup_deadline_unix']) if stage=='cost-warmup' else deadline
            if stage_deadline<=stage_started:
                raise TimeoutError('cost stage budget expired')
            signal.setitimer(signal.ITIMER_REAL,stage_deadline-stage_started)
            publish(stage,out/'run.json',dict(schema='adjacent-cost-run-v1',purpose=stage,
                manifest_sha256=args.manifest_sha256,cost_contract_sha256=manifest['cost_contract']['sha256'],
                reservation=reservations[stage],pid=os.getpid(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                started_at_unix=stage_started,deadline_unix=deadline,device='cuda:0',
                data_range=[domain['block_start'],domain['block_stop']],snrs=[7,8,9],arms=list(ARMS),
                setup_seconds=build_times,shared_setup_total_seconds=setup_seconds,
                setup_reused_from='cost-warmup' if stage=='cost-measurement' else None,
                code_hashes={k:array_hash(code[k]) for k in ('G','H')},numpy_version=np.__version__,
                numerical_environment=environment,stage_deadline_unix=stage_deadline,
                torch_version=torch.__version__,affinity=sorted(os.sched_getaffinity(0)),
                precision='unchanged: outer complex64/float32, BP complex128/float64, host input complex128',
                timing_scope=cost['timing_boundary'],warmup_and_measurement_share_receiver_instances=True))
            for block in range(domain['block_start'],domain['block_stop']):
                guard.check()
                record_telemetry(hooks,args.root,manifest['exclusive_prior_workers'],
                    out/f'telemetry-{block:06d}.json',lambda path,value:publish(stage,path,value))
                order=campaign_rng('timing',block,'order',family='F_C').permutation(list(ARMS)).tolist()
                for snr in (7,8,9):
                    active=dict(purpose=stage,block=block,snr_db=snr,stage='generation')
                    for arm in ARMS:
                        data._request('timing',block,snr,'F_C',arm,scope_purpose=stage)
                    clock=time.perf_counter()
                    frame=data.make_frame(system,'timing',block,snr,family='F_C',arm_id=ARMS[0],scope_purpose=stage)
                    generation_seconds=time.perf_counter()-clock
                    if not np.allclose(frame.observed['pilot'],p0,rtol=1e-12,atol=1e-12):
                        raise ValueError('cost frame pilot differs from frozen p0')
                    cell=out/f'b{block:06d}-s{snr}'
                    cell.mkdir()
                    save_clock=time.perf_counter()
                    saved=save_state(cell/'input.npz',dict(observed=dict(frame.observed),truth=frame._truth),meter)
                    publish(stage,cell/'input.json',dict(raw=saved,frame=frame.metadata,
                        generation_seconds=generation_seconds,raw_save_seconds=time.perf_counter()-save_clock,order=order))
                    for arm in order:
                        identity=dict(block=block,snr_db=snr,arm=arm,repeat=0)
                        active=dict(purpose=stage,stage='receiver',**identity)
                        before=rng_state('cuda:0')
                        torch.cuda.reset_peak_memory_stats()
                        allocated_before=torch.cuda.memory_allocated()
                        counts[stage]['attempted_F']+=1
                        print(json.dumps(dict(event='start_call',**active,**counts[stage])),flush=True)
                        hooks.sync('cuda:0')
                        wall,cpu=time.perf_counter(),time.process_time()
                        result=receivers[(snr,arm)].run(frame.observed,audit=False)
                        hooks.sync('cuda:0')
                        seconds,cpu_seconds=time.perf_counter()-wall,time.process_time()-cpu
                        after=rng_state('cuda:0')
                        if before!=after:
                            raise ValueError('cost receiver consumed unexpected RNG state')
                        active['stage']='validation_and_raw_save'
                        _validate_result(result,False,frame,code)
                        scores=score_errors(result,frame._truth)
                        result['info_error_vector']=np.asarray(result['info_hat'])!=frame._truth['info']
                        result['code_error_vector']=np.asarray(result['decoded'])!=frame._truth['coded']
                        save_clock=time.perf_counter()
                        saved=save_state(cell/(arm+'-r0.npz'),dict(result=result,bp_input_states=[]),meter)
                        publish(stage,cell/(arm+'-r0.json'),dict(identity=identity,raw=saved,
                            input_hashes=frame.metadata['input_hashes'],seconds=seconds,CPU_seconds=cpu_seconds,
                            raw_save_seconds=time.perf_counter()-save_clock,
                            start_monotonic_seconds=wall,scores=scores,audit=False,profile=[],
                            rng_before=before,rng_after=after,cuda_allocated_before=allocated_before,
                            peak_cuda_bytes=torch.cuda.max_memory_allocated(),
                            incremental_peak_cuda_bytes=torch.cuda.max_memory_allocated()-allocated_before,
                            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                        counts[stage]['completed_F']+=1
                        print(json.dumps(dict(event='complete_call',**active,**counts[stage],
                            seconds=seconds,elapsed_seconds=time.time()-started)),flush=True)
                publish(stage,out/f'progress-{block:06d}.json',dict(**counts[stage],bytes=meter.used,
                    elapsed_seconds=time.time()-stage_started))
            guard.verify();meter.verify()
            expected=(domain['block_stop']-domain['block_start'])*9
            if counts[stage]!=dict(attempted_F=expected,completed_F=expected):
                raise ValueError('cost stage incomplete')
            publish(stage,out/'complete.json',dict(status='complete_cost_collection',**counts[stage],
                started_at_unix=stage_started,finished_at_unix=time.time(),
                elapsed_seconds=time.time()-stage_started,bytes_before_closure=meter.used,
                reservation=reservations[stage],scientific_verdict='pending complete raw audit and frozen statistics'))
        record_telemetry(hooks,args.root,manifest['exclusive_prior_workers'],
            outputs['cost-measurement']/'telemetry-final.json',
            lambda path,value:publish('cost-measurement',path,value))
        return 0
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        failure=dict(status='incomplete',exception=type(error).__name__,message=str(error),
            traceback=traceback.format_exc(),active=active,counts=counts,reservations=reservations,
            started_at_unix=started,failed_at_unix=time.time(),policy='preserve all4698 F reservations and raw data; no restart')
        publish_json(args.root/'cost-collection-failure-v1.json',failure)
        print(json.dumps(failure),file=sys.stderr,flush=True)
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old_alarm);signal.signal(signal.SIGTERM,old_term)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--deadline-unix',type=float,required=True)
    parser.add_argument('--device',choices=['cuda:0'],required=True)
    args=parser.parse_args()
    for path in (args.root,args.manifest):
        if not path.resolve().is_relative_to(Path('/data/guoyikun')):
            parser.error('cost files must remain below /data/guoyikun')
    sys.exit(execute(args))
