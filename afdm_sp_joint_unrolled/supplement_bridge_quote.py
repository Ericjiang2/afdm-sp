"""A-02 bounded engineering-E quote from one content-bound cached terminal state."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import time
import traceback

# Must precede NumPy/SciPy/Torch imports in this standalone CPU quote process.
THREAD_ENV=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
for _name in THREAD_ENV:
    os.environ[_name]='1'

import numpy as np
import torch

from .budgeted_support_diagnostics import array_hash
from .loop9_cache_features import _make_config_a
from .supplement_baseline_run import output_bytes, publish_bounded
from .supplement_baselines import a02_catalogue, BaselineTerminalRefit
from .supplement_data import CAMPAIGN_ID
from .supplement_profile import reserve_profile
from .supplement_run import json_value, sha, sources

FILE_KEYS=('contract.json','summary.json','frame-000-group-p2-s0.5.json',
           'terminal-000-group-p2-s0.5.npz')
ALLOWED_ARRAYS=('y','pilot','H','x_soft','support','gains','sigma2')
FAILURE_RESERVE_BYTES=2*1024**2


def source_manifest():
    return sources()


def _read_json(path):
    value=json.loads(Path(path).read_text())
    if not isinstance(value,dict):raise ValueError('bound JSON input must be an object')
    return value


def validate_manifest(path,expected_sha):
    path=Path(path)
    if not isinstance(expected_sha,str) or len(expected_sha)!=64 or sha(path)!=expected_sha:
        raise ValueError('input manifest hash mismatch')
    manifest=_read_json(path)
    if (manifest.get('schema')!='A02-cached-engineering-inputs-v1' or
            manifest.get('status')!='input_bindings_only_not_execution_admission' or
            set(manifest.get('files',{}))!=set(FILE_KEYS) or len(manifest.get('files',{}))!=len(FILE_KEYS) or
            manifest.get('proposed_calls')!={'F':0,'T':0,'E':8} or
            manifest.get('allowed_npz_reads')!=list(ALLOWED_ARRAYS)):
        raise ValueError('invalid A-02 cached-input manifest contract')
    limits=manifest.get('limits',{})
    if (limits.get('threads')!=1 or limits.get('per_E_seconds')!=300 or
            limits.get('stage_seconds')!=2700 or limits.get('max_output_bytes')!=64*1024**2 or
            limits.get('no_automatic_retry') is not True):
        raise ValueError('invalid A-02 E quote limits')
    resolved={}
    for name in FILE_KEYS:
        ref=manifest['files'][name]
        if (not isinstance(ref,dict) or set(ref)!= {'path','sha256','bytes'} or
                not isinstance(ref['path'],str) or not isinstance(ref['sha256'],str) or
                type(ref['bytes']) is not int or ref['bytes']<1):
            raise ValueError('invalid cached file reference')
        target=Path(ref['path'])
        if not target.is_file() or target.stat().st_size!=ref['bytes'] or sha(target)!=ref['sha256']:
            raise ValueError('cached file content mismatch')
        resolved[name]=target
    contract=_read_json(resolved['contract.json']);summary=_read_json(resolved['summary.json'])
    frame=_read_json(resolved['frame-000-group-p2-s0.5.json']);identity=manifest.get('cache_identity')
    if (not isinstance(identity,dict) or set(identity)!= {'split','block_id','arm_id','config_sha256'} or
            any(frame.get(k)!=v for k,v in identity.items()) or frame.get('SNR')!=8 or
            contract.get('config_sha256')!=identity['config_sha256'] or
            contract.get('split')!='engineering' or contract.get('snr')!=8 or
            summary.get('status')!='complete' or summary.get('exitcode')!=0 or
            summary.get('config_sha256')!=identity['config_sha256']):
        raise ValueError('cached engineering identity/status mismatch')
    frame_ref=manifest['files']['frame-000-group-p2-s0.5.json']
    registered=[r for r in summary.get('records',[]) if
                Path(r.get('path','')).name=='frame-000-group-p2-s0.5.json']
    if len(registered)!=1 or registered[0].get('sha256')!=frame_ref['sha256']:
        raise ValueError('cached frame is not uniquely registered by successful summary')
    terminal=frame.get('terminal',{});snapshot_ref=manifest['files']['terminal-000-group-p2-s0.5.npz']
    if (terminal.get('sha256')!=snapshot_ref['sha256'] or
            not set(ALLOWED_ARRAYS).issubset(terminal.get('fields',[]))):
        raise ValueError('cached terminal binding/fields mismatch')
    return manifest,resolved,frame


def load_cached_state(path,n):
    with np.load(path,allow_pickle=False) as stored:
        arrays={name:np.asarray(stored[name]).copy() for name in ALLOWED_ARRAYS}
    y,pilot,H,x_soft,gains=(np.asarray(arrays[k],dtype=np.complex128)
                            for k in ('y','pilot','H','x_soft','gains'))
    support=np.asarray(arrays['support']);sigma2=np.asarray(arrays['sigma2'])
    if (y.shape!=(n,) or pilot.shape!=(n,) or H.shape!=(n,n) or x_soft.shape!=(n,) or
            support.ndim!=1 or support.dtype.kind not in 'iu' or len(support)>40 or
            gains.shape!=support.shape or len(set(support.tolist()))!=len(support) or
            np.any(support<0) or np.any(support>=515) or sigma2.shape!=() or
            np.iscomplexobj(sigma2) or not np.isfinite(sigma2) or float(sigma2)<=0 or
            any(not np.isfinite(a).all() for a in (y,pilot,H,x_soft,gains))):
        raise ValueError('invalid cached observed refit state')
    return dict(y=y,pilot=pilot,H=H,x_soft=x_soft,support=support.astype(int).tolist(),
                gains=gains,sigma2=float(sigma2))


def quote_recipes():
    rows=[r for r in a02_catalogue() if r['stage']=='terminal_refit']
    if len(rows)!=8 or any(r['terminal_scale']!=1 for r in rows):
        raise ValueError('A-02 E quote requires the frozen eight scale-one refits')
    return rows


def validate_request(args,manifest):
    limits=manifest['limits']
    if (not math.isfinite(args.deadline_unix) or args.deadline_unix<=time.time() or
            args.deadline_unix-time.time()>limits['stage_seconds'] or args.device!='cpu'):
        raise ValueError('invalid bounded E quote deadline/device')
    return limits


def assert_inputs_unchanged(args,contract):
    if sha(args.input_manifest)!=contract['input_manifest_sha256'] or source_manifest()!=contract['source_sha256']:
        raise ValueError('manifest or source changed during quote')
    for ref in contract['input_files'].values():
        if sha(ref['path'])!=ref['sha256']:raise ValueError('cached input changed during quote')


def _arm_timer(deadline,cap):
    remaining=deadline-time.time()
    if not math.isfinite(remaining) or remaining<=0:
        raise TimeoutError('A-02 E quote deadline exhausted')
    signal.setitimer(signal.ITIMER_REAL,min(remaining,cap))


def configure_threads():
    if any(os.environ.get(name)!='1' for name in THREAD_ENV):
        raise ValueError('BLAS thread environment changed after import')
    torch.set_num_threads(1)
    if torch.get_num_interop_threads()!=1:
        torch.set_num_interop_threads(1)
    if torch.get_num_threads()!=1 or torch.get_num_interop_threads()!=1:
        raise ValueError('failed to freeze Torch CPU thread pools')
    return dict(intraop=torch.get_num_threads(),interop=torch.get_num_interop_threads(),
                environment={name:os.environ[name] for name in THREAD_ENV})


def execute(args):
    args.out.mkdir(parents=True,exist_ok=False)
    previous=signal.getsignal(signal.SIGALRM)
    attempted=completed=0;failures=[];records=[];active=None
    start_wall,start_cpu=time.perf_counter(),time.process_time()
    try:
        manifest,resolved,frame=validate_manifest(args.input_manifest,args.input_manifest_sha256)
        limits=validate_request(args,manifest);recipes=quote_recipes()
        def timeout(*_):raise TimeoutError('A-02 E quote deadline reached')
        signal.signal(signal.SIGALRM,timeout)
        _arm_timer(args.deadline_unix,limits['stage_seconds'])
        if shutil.disk_usage(args.out).free<limits['max_output_bytes']:
            raise OSError('insufficient disk for frozen E quote output cap')
        thread_config=configure_threads();device=torch.device(args.device)
        system=_make_config_a(1024,2.,8,10.,4.)
        state=load_cached_state(resolved['terminal-000-group-p2-s0.5.npz'],system.N_total)
        input_files={name:dict(path=str(path),sha256=manifest['files'][name]['sha256'])
                     for name,path in resolved.items()}
        contract=dict(schema='supplement-A02-E-quote-contract-v1',campaign_id=CAMPAIGN_ID,
            input_manifest_sha256=args.input_manifest_sha256,input_manifest_path=str(args.input_manifest),
            cache_identity=manifest['cache_identity'],cache_scope=manifest['source_state_scope'],
            sigma_rule=manifest['sigma_rule'],allowed_npz_reads=list(ALLOWED_ARRAYS),
            input_files=input_files,recipes=recipes,calls_reserved={'F':0,'T':0,'E':8},
            max_full_calls=0,device=str(device),threads=thread_config,
            deadline_unix=args.deadline_unix,per_E_seconds=limits['per_E_seconds'],
            max_output_bytes=limits['max_output_bytes'],source_sha256=source_manifest(),
            command=[sys.executable,*sys.argv],policy='no retry/reclaim; resource probe only; no FER selection')
        contract['config_sha256']=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
        contract['ledger']=reserve_profile(args.out,contract)
        publish_bounded(args.out/'contract.json',contract,args.out,
                        limits['max_output_bytes']-FAILURE_RESERVE_BYTES)
        for recipe in recipes:
            assert_inputs_unchanged(args,contract)
            preparation_start=time.perf_counter()
            attempted+=1;active=dict(attempt=attempted,arm_id=recipe['id'],call_type='E',
                cache_identity=manifest['cache_identity'],started_unix=time.time(),
                started_CPU_seconds=time.process_time())
            publish_bounded(args.out/f'call-{attempted:02d}-started.json',active,args.out,
                            limits['max_output_bytes']-FAILURE_RESERVE_BYTES)
            try:
                refit=BaselineTerminalRefit(system,recipe['id'])
                preparation_seconds=time.perf_counter()-preparation_start
                wall=time.perf_counter();cpu=time.process_time()
                rss_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                _arm_timer(args.deadline_unix,limits['per_E_seconds'])
                result=refit(y=state['y'],pilot=state['pilot'],H=state['H'],x_soft=state['x_soft'],
                    support=state['support'],gains=state['gains'],
                    sigma_base=state['sigma2']*recipe['terminal_scale'])
                elapsed=time.perf_counter()-wall;cpu_elapsed=time.process_time()-cpu
                if elapsed>limits['per_E_seconds']:raise TimeoutError('E call exceeded per-call limit')
                if (not isinstance(result,dict) or set(result)!= {'H','gains','diagnostics'} or
                        not isinstance(result['diagnostics'],dict)):
                    raise ValueError('invalid physical refit quote result')
                H_after=np.asarray(result['H']);gains_after=np.asarray(result['gains'])
                if (H_after.shape!=state['H'].shape or gains_after.shape!=state['gains'].shape or
                        not np.isfinite(H_after).all() or not np.isfinite(gains_after).all()):
                    raise ValueError('invalid physical refit quote output arrays')
                row=json_value(dict(schema='supplement-A02-E-quote-record-v1',status='complete',
                    call_type='E',attempt=attempted,arm_id=recipe['id'],recipe=recipe,
                    cache_identity=manifest['cache_identity'],input_manifest_sha256=args.input_manifest_sha256,
                    config_sha256=contract['config_sha256'],source_sha256=contract['source_sha256'],
                    input_hashes={k:array_hash(state[k]) for k in ('y','pilot','H','x_soft','gains')},
                    support=state['support'],sigma_source='cached sigma2 * A02 recipe terminal_scale',
                    sigma_base=state['sigma2']*recipe['terminal_scale'],diagnostics=result['diagnostics'],
                    H_after_sha256=array_hash(H_after),gains_after_sha256=array_hash(gains_after),
                    gains_after_real=gains_after.real.tolist(),gains_after_imag=gains_after.imag.tolist(),
                    preparation_seconds=preparation_seconds,elapsed_seconds=elapsed,
                    process_cpu_seconds=cpu_elapsed,peak_gpu_bytes=0,gpu_scope='not applicable; CPU-only E',
                    process_peak_rss_native_before=rss_before,
                    process_peak_rss_native_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    truth_access='none; only manifest-whitelisted cached arrays read',failure=None,
                    qualification_scope='engineering resource quote only; not development/confirmation/COST-02'))
            except (TimeoutError,KeyboardInterrupt):raise
            except Exception as exc:
                failure=dict(status='failed',call_type='E',identity=active,exception=type(exc).__name__,
                    message=str(exc),traceback=traceback.format_exc(),retry_of=None)
                path=args.out/f'failure-{attempted:02d}.json'
                publish_bounded(path,failure,args.out,limits['max_output_bytes']-FAILURE_RESERVE_BYTES)
                failures.append(dict(path=str(path),sha256=sha(path),identity=active));active=None
                _arm_timer(args.deadline_unix,limits['stage_seconds']);continue
            path=args.out/f'record-{attempted:02d}-{recipe["id"]}.json'
            publication_start=time.perf_counter()
            publish_bounded(path,row,args.out,limits['max_output_bytes']-FAILURE_RESERVE_BYTES)
            publication_seconds=time.perf_counter()-publication_start
            publication=dict(schema='supplement-A02-E-publication-cost-v1',arm_id=recipe['id'],
                record_sha256=sha(path),output_publication_seconds=publication_seconds,
                scope='record JSON atomic serialization/fsync/link only; companion publication excluded')
            publication_path=args.out/f'publication-{attempted:02d}.json'
            publish_bounded(publication_path,publication,args.out,
                            limits['max_output_bytes']-FAILURE_RESERVE_BYTES)
            records.append(dict(path=str(path),sha256=sha(path),arm_id=recipe['id'],
                publication_path=str(publication_path),publication_sha256=sha(publication_path),
                preparation_seconds=row['preparation_seconds'],refit_seconds=row['elapsed_seconds'],
                output_publication_seconds=publication_seconds))
            completed+=1;active=None
            _arm_timer(args.deadline_unix,limits['stage_seconds'])
        assert_inputs_unchanged(args,contract)
        stage_seconds=time.perf_counter()-start_wall
        attributed=sum(r['preparation_seconds']+r['refit_seconds']+r['output_publication_seconds']
                       for r in records)
        status='complete' if not failures else 'completed_with_failures';exitcode=0 if not failures else 1
        publish_bounded(args.out/'summary.json',dict(schema='supplement-A02-E-quote-summary-v1',
            status=status,exitcode=exitcode,calls_attempted=attempted,calls_completed=completed,
            calls_reserved={'F':0,'T':0,'E':8},records=records,failures=failures,
            config_sha256=contract['config_sha256'],reservation_ledger=contract['ledger'],
            wall_seconds=stage_seconds,CPU_seconds=time.process_time()-start_cpu,
            attributed_completed_call_seconds=attributed,
            unattributed_stage_seconds=max(0.,stage_seconds-attributed),
            timing_scope='refit, per-call preparation, record publication, and remaining stage overhead are separate',
            output_bytes_before_summary=output_bytes(args.out),
            scope='bounded engineering E resource quote; not COST-02 or scientific evidence'),
            args.out,limits['max_output_bytes'])
        return exitcode
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        limit=manifest['limits']['max_output_bytes'] if 'manifest' in locals() else 64*1024**2
        publish_bounded(args.out/'batch-failure.json',dict(status='failed',
            exitcode=130 if isinstance(exc,KeyboardInterrupt) else 1,exception=type(exc).__name__,
            message=str(exc)[:16384],traceback=traceback.format_exc()[-32768:],
            calls_attempted=attempted,calls_completed=completed,active_attempt=active,
            recorded_failure_count=len(failures),completed_record_count=len(records),
            retry_policy='none; reservation and attempted identity remain charged'),args.out,limit)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest',type=Path,required=True)
    parser.add_argument('--input-manifest-sha256',required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--deadline-unix',type=float,required=True)
    parser.add_argument('--device',choices=('cpu',),required=True)
    return execute(parser.parse_args())


if __name__=='__main__':sys.exit(main())
