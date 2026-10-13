"""Bounded I01 paired GPU quote. Requires separately reserved immutable contract."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import argparse,json,time,hashlib,subprocess,signal,math,shutil,sys,traceback
import numpy as np
import torch
from afdm_sp_joint_unrolled.supplement_data import SupplementData
from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
from afdm_sp_joint_unrolled.direction_receiver import ObservedReceiver
from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback
from afdm_sp_joint_unrolled.supplement_feedback_diagnostic import DiagnosticCodeSymbols
from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.supplement_profile import score_errors
from afdm_sp_joint_unrolled.supplement_baseline_run import terminal_snapshot,publish_bounded,output_bytes

SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gpu_guard(uuid):
    result=subprocess.run(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10)
    other=[]
    for line in result.stdout.splitlines():
        gpu,pid=[v.strip() for v in line.split(',')]
        if gpu==uuid and int(pid)!=os.getpid():other.append(int(pid))
    if other:raise RuntimeError(f'exclusive GPU quote has other processes: {other}')


DERIVED_FIELDS={'config_sha256','ledger','reservation_path'}
FAILURE_RESERVE=256*1024

def canonical_hash(contract):
    return hashlib.sha256(json.dumps({k:v for k,v in contract.items() if k not in DERIVED_FIELDS},
        sort_keys=True,allow_nan=False).encode()).hexdigest()


def check_frozen(contract):
    if canonical_hash(contract)!=contract['config_sha256']:raise ValueError('contract canonical SHA mismatch')
    for key in ('design','checkpoint','protocol'):
        if SHA(contract[key])!=contract[key+'_sha256']:raise ValueError(key+' changed')
    root=Path(contract['source_root']).resolve()
    expected={str(p.resolve()) for p in root.rglob('*.py')}|{str(Path(__file__).resolve())}
    if set(contract['source_sha256'])!=expected:raise ValueError('incomplete frozen source manifest')
    if Path(sys.modules[SupplementData.__module__].__file__).resolve().parent!=root:
        raise ValueError('loaded receiver source differs from frozen source_root')
    for path,digest in contract['source_sha256'].items():
        if SHA(path)!=digest:raise ValueError('source changed')


def timeout_argv_valid(argv,seconds):
    return (len(argv)>=4 and Path(argv[0]).name=='timeout' and
            argv[1:4]==['--signal=TERM','--kill-after=15s',str(seconds)+'s'])


def check_external_timeout(seconds):
    pid=os.getppid()
    for _ in range(8):
        if pid<=1:break
        root=Path('/proc')/str(pid)
        argv=root.joinpath('cmdline').read_bytes().decode().rstrip('\0').split('\0')
        if timeout_argv_valid(argv,seconds):return
        stat=root.joinpath('stat').read_text();pid=int(stat[stat.rfind(')')+2:].split()[1])
    raise ValueError('required bounded external timeout ancestor missing')


def validate_limits(contract,now):
    if canonical_hash(contract)!=contract['config_sha256']:raise ValueError('contract canonical SHA mismatch')
    deadline=contract['deadline_unix'];seconds=contract['external_timeout_seconds']
    if (not math.isfinite(deadline) or deadline<=now or type(seconds) is not int or
            seconds<=15 or deadline-now>seconds-15):raise ValueError('invalid Python/external deadline contract')
    if contract['calls_reserved']!={'F':72,'T':0,'E':0}:raise ValueError('wrong finite quote reservation')
    if type(contract['max_output_bytes']) is not int or contract['max_output_bytes']<72*32*1024**2+FAILURE_RESERVE:
        raise ValueError('output cap below complete quote estimate')


def verify_device(uuid,device):
    if torch.cuda.device_count()!=1:raise ValueError('exactly one visible CUDA device required')
    properties=torch.cuda.get_device_properties(device)
    observed=getattr(properties,'uuid',None)
    if observed is not None:
        value=str(observed)
        if value!=uuid and 'GPU-'+value!=uuid:raise ValueError('actual torch GPU UUID mismatch')
    else:
        torch.empty(1,device=device);torch.cuda.synchronize(device)
        result=subprocess.run(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],
            capture_output=True,text=True,check=True,timeout=10)
        found={line.split(',')[0].strip() for line in result.stdout.splitlines() if int(line.split(',')[1])==os.getpid()}
        if found!={uuid}:raise ValueError('current CUDA PID does not bind declared UUID')


def execute(contract):
    out=Path(contract['out']);out.mkdir(parents=True,exist_ok=True)
    if (out/'started.json').exists() or (out/'failure.json').exists():raise ValueError('quote already attempted; no automatic retry')
    previous=signal.getsignal(signal.SIGALRM);previous_term=signal.getsignal(signal.SIGTERM);rows=[];attempts=0;active=None;costs=[];selected={};active_wall=None;active_cpu=None
    def put(name,value,failure=False):
        publish_bounded(out/name,value,out,contract['max_output_bytes']-(0 if failure else FAILURE_RESERVE))
    def admission():
        check_frozen(contract)
        if time.time()>=contract['deadline_unix']:raise TimeoutError('quote deadline')
        remaining=contract['max_output_bytes']-output_bytes(out)
        if remaining<32*1024**2+FAILURE_RESERVE:raise OSError('output cap')
        if shutil.disk_usage(out).free<remaining:raise OSError('insufficient remaining disk reservation')
    def timeout(*_):raise TimeoutError('hard Python quote deadline')
    try:
        validate_limits(contract,time.time());check_external_timeout(contract['external_timeout_seconds'])
        signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGTERM,timeout);signal.setitimer(signal.ITIMER_REAL,contract['deadline_unix']-time.time())
        admission()
        reservation=json.loads(Path(contract['reservation_path']).read_text())
        if reservation['contract_sha256']!=contract['config_sha256'] or reservation['calls_reserved']!=contract['calls_reserved']:
            raise ValueError('reservation mismatch')
        design=json.loads(Path(contract['design']).read_text())
        if torch.cuda.is_initialized():raise ValueError('CUDA initialized before UUID visibility binding')
        os.environ['CUDA_VISIBLE_DEVICES']=contract['gpu_uuid']
        if not torch.cuda.is_available():raise RuntimeError('CUDA required; no substitution')
        device=torch.device('cuda:0');torch.cuda.set_device(device);verify_device(contract['gpu_uuid'],device)
        gpu_guard(contract['gpu_uuid']);torch.cuda.set_per_process_memory_fraction(.25,device)
        if torch.cuda.mem_get_info(device)[0]<6144*1024**2:raise RuntimeError('GPU headroom below guard')
        put('started.json',dict(pid=os.getpid(),started=time.time(),config_sha256=contract['config_sha256']))
        wall,cpu=time.perf_counter(),time.process_time()
        code=build_code(cache_dir=contract['code_cache']);system=_make_config_a(1024,2.,8,10.,4.)
        data=SupplementData(contract['protocol'],code)
        costs.append(dict(stage='code_system_data_setup',seconds=time.perf_counter()-wall,CPU_seconds=time.process_time()-cpu))
        frames={}
        for block in design['engineering_blocks']:
            wall,cpu=time.perf_counter(),time.process_time();frames[block]=data.make_frame(system,'engineering',block,8)
            costs.append(dict(stage='generation',block=block,seconds=time.perf_counter()-wall,CPU_seconds=time.process_time()-cpu))
        wall,cpu=time.perf_counter(),time.process_time()
        model=ObservedReceiver.build(contract['checkpoint'],system,code,device='cuda').model
        torch.cuda.synchronize(device)
        costs.append(dict(stage='model_construction',seconds=time.perf_counter()-wall,CPU_seconds=time.process_time()-cpu))
        put('preparation-costs.json',costs)
        def run_one(checkpoint,block,arm,count):
            nonlocal attempts,active,active_wall,active_cpu
            if attempts>=72 or time.time()>=contract['deadline_unix']:raise TimeoutError('quote budget/deadline')
            admission()
            gpu_guard(contract['gpu_uuid']);attempts+=1
            identity=dict(attempt=attempts,checkpoint=checkpoint,block=block,arm=arm,outer_bp_iterations=count)
            active=identity;active_wall=time.perf_counter();active_cpu=time.process_time()
            put(f'call-{attempts:03d}-started.json',identity)
            construct_wall,construct_cpu=time.perf_counter(),time.process_time()
            frame=frames[block];receiver=BaselineReceiver(model,code,design['baseline_recipe'],system=system)
            schedule=UniformBPSchedule(outer_bp_iterations=count)
            controller=None
            if arm in ('I2','I2realloc'):
                controller=DiagnosticCodeSymbols(code,frame._truth['data'],tag=arm,checkpoint=checkpoint)
                invoke=lambda:receiver.run_diagnostic(frame.observed,diagnostic_code_symbols=controller,bp_schedule=schedule,audit=False)
            else:
                control={'Irealloc':'zero','Isham':'fixed_sham','I1':'legal'}.get(arm)
                feedback=CodeFeedback(code,checkpoint=checkpoint,control=control,sham_seed=18 if control=='fixed_sham' else None) if control else None
                invoke=lambda:receiver.run(frame.observed,code_feedback=feedback,bp_schedule=schedule,audit=False)
            construction=dict(seconds=time.perf_counter()-construct_wall,CPU_seconds=time.process_time()-construct_cpu)
            torch.cuda.synchronize(device);torch.cuda.reset_peak_memory_stats(device)
            wall,cpu=time.perf_counter(),time.process_time()
            value=invoke();torch.cuda.synchronize(device)
            elapsed,cpu=time.perf_counter()-wall,time.process_time()-cpu
            if not np.isfinite(elapsed) or elapsed<=0:raise ValueError('invalid time')
            row=dict(**identity,seconds=elapsed,CPU_seconds=cpu,peak_gpu_bytes=torch.cuda.max_memory_allocated(device),
                construction=construction,input_hashes=frame.metadata['input_hashes'],bp_schedule=value['bp_schedule'],
                code_feedback_records=value.get('code_feedback_records',[]),diagnostic_consumption_records=value.get('diagnostic_consumption_records',[]),
                errors=score_errors(value,frame._truth),scope='engineering complete F timing; schedule graph and message hash instrumentation included; generation, construction and snapshot outside timer')
            snap=time.perf_counter();row['terminal']=terminal_snapshot(out/f'terminal-{attempts:03d}.npz',frame,value,budget_root=out,
                max_bytes=contract['max_output_bytes']-FAILURE_RESERVE)
            row['snapshot_seconds']=time.perf_counter()-snap
            check_frozen(contract);gpu_guard(contract['gpu_uuid'])
            put(f'call-{attempts:03d}.json',row);rows.append(row);active=None
        def run_group(checkpoint,count,arms):
            for block in design['engineering_blocks']:
                order=list(arms);np.random.default_rng(20260909+checkpoint*100+block).shuffle(order)
                for arm in order:run_one(checkpoint,block,arm,count)
        def feasible(checkpoint,count):
            mean=lambda arm,n:float(np.mean([r['seconds'] for r in rows if r['checkpoint']==checkpoint and r['arm']==arm and r['outer_bp_iterations']==n]))
            reference=mean('I0',20)
            return all(mean(arm,count)<=reference for arm in ('Irealloc','Isham','I1'))
        for checkpoint in design['checkpoints']:
            run_group(checkpoint,20,design['arms'])
            selected[str(checkpoint)]=20 if feasible(checkpoint,20) else None
            for count in design['reallocation_candidates']:
                if selected[str(checkpoint)] is not None:break
                run_group(checkpoint,count,design['reallocated_arms'])
                if feasible(checkpoint,count):selected[str(checkpoint)]=count
        admission();gpu_guard(contract['gpu_uuid'])
        put('summary.json',dict(status='complete',exitcode=0,config_sha256=contract['config_sha256'],
            attempted_F=attempts,selected=selected,records=rows,preparation_costs=costs,
            allocation_passed=all(v is not None for v in selected.values()),
            scope='two engineering blocks; instrumented complete F; no FER-based selection or COST02 inference'))
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        put('failure.json',dict(status='failed',exitcode=1,exception=type(exc).__name__,message=str(exc)[:8192],
            traceback=traceback.format_exc()[-16384:],attempted_F=attempts,completed_F=len(rows),active_identity=active,
            active_wall_seconds=time.perf_counter()-active_wall if active is not None else None,
            active_CPU_seconds=time.process_time()-active_cpu if active is not None else None,
            preparation_costs=costs,config_sha256=contract.get('config_sha256'),
            policy='charged attempts retained; no automatic retry or reclaim'),failure=True)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous);signal.signal(signal.SIGTERM,previous_term)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--contract',type=Path,required=True)
    args=parser.parse_args();return execute(json.loads(args.contract.read_text()))


if __name__=='__main__':raise SystemExit(main())
