"""Collect the five frozen B roles on existing audited I1 development inputs."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
from types import SimpleNamespace

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import numpy as np
import torch

from supplement_adjacent_evidence import file_sha, load_raw, validate_input
from supplement_adjacent_pool import FixedGeometryRefit, POOLS, ROLES, codeword_score, nominate
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.direction_physical_receiver import PhysicalChannelRefit
from afdm_sp_joint_unrolled.supplement_adjacent_run import rng_state, save_state, setup
from afdm_sp_joint_unrolled.supplement_data import _read_json, campaign_rng
from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback
from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
from afdm_sp_joint_unrolled.supplement_profile import score_errors
from afdm_sp_joint_unrolled.supplement_scope import reserve, validate_scope
from afdm_sp_joint_unrolled.supplement_timing import _bounded_json, _validate_result
from afdm_sp_joint_unrolled.supplement_timing_integrity import OutputMeter


def load_development_cell(root, block, snr, expected):
    path = root / 'development-i1-gpu' / f'b{block:06d}-s{snr}' / 'input.json'
    if file_sha(path) != expected:
        raise ValueError('shared development input metadata differs from audited binding')
    metadata = json.loads(path.read_text())
    frame = metadata['frame']
    if (frame['block'], frame['snr_db'], frame['split'], frame['family']) != (block, snr, 'design', None):
        raise ValueError('shared development input identity differs')
    raw = load_raw(metadata['raw'], root)
    validate_input(raw, frame)
    return metadata, raw


def run_candidate(driver, observed, code, geometry, candidate):
    """Use the original I1 outer receiver; only its terminal geometry is fixed."""
    baseline = driver.receiver
    refit = FixedGeometryRefit(geometry, candidate)
    result = baseline.receiver.run(observed, family='b0', parameter=None, terminal_scale=.5,
        audit=False, code_feedback=CodeFeedback(code, checkpoint=1, control='legal'),
        bp_schedule=UniformBPSchedule(outer_bp_iterations=12), channel_refit=refit)
    # _InitializerModel consumes the baseline initializer, replacing the generic one.
    result['initial_estimator'] = copy.deepcopy(baseline.estimator.record)
    result['baseline_recipe'] = copy.deepcopy(baseline.recipe)
    result['baseline_eligible'] = bool(baseline.estimator.record['eligible'])
    return result


def execute(args):
    manifest = _read_json(args.manifest, args.manifest_sha256)
    validate_scope(manifest)
    contract = _read_json(Path(manifest['pool_contract']['path']), manifest['pool_contract']['sha256'])
    if (contract['receiver_arms'] != list(ROLES) or contract['pool_lists'] != {k:list(v) for k,v in POOLS.items()}
            or contract['full_F'] != dict(existing_I1_reused=256, new=1280, total_max=1536)
            or args.device != 'cuda:0' or manifest['development_device'] != args.device
            or args.bytes_reserved != 14_000_000_000):
        raise ValueError('B finite algorithm, device or resource binding differs')
    inputs = manifest['development_input_hashes']
    expected_cells = {f'{block}/{snr}' for block in range(192,320) for snr in (7,8)}
    if set(inputs) != expected_cells:
        raise ValueError('all 256 audited development input bindings required')
    identities = [dict(split='design', family=None, block=block, snr_db=snr, arm=role, repeat=0)
        for block in range(192,320) for snr in (7,8) for role in ROLES]
    args.out.mkdir(parents=True, exist_ok=False)
    meter = OutputMeter(args.out, args.bytes_reserved-1024*1024)
    started = time.time()
    attempted = completed = local_queries = 0
    reservation = active = current_pool = None
    old_alarm, old_term = signal.getsignal(signal.SIGALRM), signal.getsignal(signal.SIGTERM)

    def stop(_signal, _frame):
        raise TimeoutError('B deadline or explicit termination reached')

    def publish(path, value):
        _bounded_json(path, value, args.out, meter.limit, meter=meter)

    try:
        signal.signal(signal.SIGALRM, stop)
        signal.signal(signal.SIGTERM, stop)
        deadline = min(args.deadline_unix, manifest['deadline_unix'])
        if not started < deadline <= manifest['deadline_unix']:
            raise ValueError('finite B deadline required')
        signal.setitimer(signal.ITIMER_REAL, deadline-started)
        reservation = reserve(manifest, args.manifest, args.manifest_sha256, args.out,
            'development', identities, bytes_reserved=args.bytes_reserved)
        setup_args = SimpleNamespace(**vars(args), purpose='development', snrs=[7,8], arms=['I1'])
        hooks, guard, _unused_data, code, system, receivers, build_times, _pilot = setup(setup_args, manifest)
        meter.adopt_tree(args.out/'code-cache')
        geometry = PhysicalChannelRefit(system, 'm-param-budget').geometry
        publish(args.out/'run.json', dict(schema='adjacent-pool-run-v1', manifest_sha256=args.manifest_sha256,
            contract_sha256=manifest['pool_contract']['sha256'], reservation=reservation,
            command=[sys.executable,*sys.argv], pid=os.getpid(),
            start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
            started_at_unix=started, deadline_unix=deadline, device=args.device,
            data_range=[192,320], snrs=[7,8], roles=list(ROLES), F=1280,
            reused_I1_F=256, setup_seconds=build_times, code_hashes={k:array_hash(code[k]) for k in ('G','H')},
            numpy_version=np.__version__, torch_version=torch.__version__,
            affinity=sorted(os.sched_getaffinity(0)),
            precision='original I1 outer complex64/float32 and BP complex128/float64; physical refit complex128',
            timing_scope='concurrent full candidate receiver, nomination and codeword scoring listed separately; not formal COST',
            confirmation_outcomes='not opened'))
        for block in range(192,320):
            guard.check()
            order = campaign_rng('design',block,'order',family=None).permutation(list(ROLES)).tolist()
            for snr in (7,8):
                active = dict(block=block,snr_db=snr,stage='load_observed_input')
                metadata, raw = load_development_cell(args.root,block,snr,inputs[f'{block}/{snr}'])
                frame = SimpleNamespace(observed=raw['observed'],_truth=raw['truth'],metadata=metadata['frame'])
                cell = args.out/f'b{block:06d}-s{snr}'
                cell.mkdir()
                publish(cell/'input-link.json',dict(source=str(args.root/'development-i1-gpu'/cell.name/'input.json'),
                    sha256=inputs[f'{block}/{snr}'], input_hashes=frame.metadata['input_hashes'], order=order))
                active['stage'] = 'observed_nomination'
                current_pool = nominate(frame.observed,geometry)
                local_queries += len(current_pool['query_trace'])
                saved_pool = save_state(cell/'pool.npz',current_pool,meter)
                publish(cell/'pool.json',dict(raw=saved_pool,local_OMP_calls=1,
                    local_physical_LS_queries=len(current_pool['query_trace']),F=0))
                score_rows = {}
                for role in order:
                    active = dict(block=block,snr_db=snr,arm=role,repeat=0,stage='full_receiver')
                    candidate = current_pool['candidates'][role]
                    before = rng_state(args.device)
                    torch.cuda.reset_peak_memory_stats()
                    hooks.sync(args.device)
                    wall, cpu = time.perf_counter(), time.process_time()
                    attempted += 1
                    print(json.dumps(dict(event='start_call',**active,attempted_F=attempted)),flush=True)
                    result = run_candidate(receivers[(snr,'I1')],frame.observed,code,geometry,candidate)
                    hooks.sync(args.device)
                    seconds, cpu_seconds = time.perf_counter()-wall,time.process_time()-cpu
                    after = rng_state(args.device)
                    if before != after:
                        raise ValueError('candidate receiver consumed unexpected RNG state')
                    _validate_result(result,False,frame,code)
                    active['stage'] = 'codeword_scoring'
                    score_started = time.perf_counter()
                    coded_score = codeword_score(frame.observed,result['H'],result['info_hat'],code)
                    scoring_seconds = time.perf_counter()-score_started
                    scores = score_errors(result,frame._truth)
                    result['info_error_vector'] = np.asarray(result['info_hat']) != frame._truth['info']
                    result['code_error_vector'] = np.asarray(result['decoded']) != frame._truth['coded']
                    saved = save_state(cell/(role+'.npz'),dict(result=result,codeword_score=coded_score),meter)
                    publish(cell/(role+'.json'),dict(identity={k:active[k] for k in ('block','snr_db','arm','repeat')},
                        input_hashes=frame.metadata['input_hashes'], candidate_signature=candidate['signature'],
                        raw=saved,scores=scores,seconds=seconds,CPU_seconds=cpu_seconds,
                        scoring_seconds=scoring_seconds,codeword_nll=coded_score['nll'],
                        rng_before=before,rng_after=after,peak_cuda_bytes=torch.cuda.max_memory_allocated(),
                        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                    score_rows[role] = dict(nll=coded_score['nll'],receiver_seconds=seconds,
                        scoring_seconds=scoring_seconds,candidate_signature=candidate['signature'])
                    completed += 1
                    print(json.dumps(dict(event='complete_call',**active,completed_F=completed,
                        seconds=seconds,elapsed_seconds=time.time()-started)),flush=True)
                selections = {}
                for name, roles in POOLS.items():
                    chosen = min(roles,key=lambda role:score_rows[role]['nll'])
                    selections[name] = dict(role=chosen,candidate_signature=score_rows[chosen]['candidate_signature'],
                        nll=score_rows[chosen]['nll'],
                        total_online_seconds=current_pool['strategy_nomination_seconds'][name]
                            +sum(score_rows[role]['receiver_seconds']+score_rows[role]['scoring_seconds'] for role in roles))
                publish(cell/'selection.json',dict(selections=selections,scores=score_rows,
                    rule='minimum single-use legal-codeword nll; frozen pool ordinal ties',
                    oracle='not computed; all outputs must first be frozen'))
                validate_input(raw,frame.metadata)
                current_pool = None
            publish(args.out/f'progress-{block:06d}.json',dict(completed_F=completed,attempted_F=attempted,
                local_physical_LS_queries=local_queries,elapsed_seconds=time.time()-started,bytes=meter.used))
        guard.verify()
        if completed != 1280 or attempted != completed or local_queries > 256*125:
            raise ValueError('B finite execution count differs from contract')
        meter.verify()
        publish(args.out/'complete.json',dict(status='complete_pool_collection',attempted_F=attempted,
            completed_F=completed,reused_I1_F=256,local_OMP_calls=256,local_physical_LS_queries=local_queries,
            started_at_unix=started,finished_at_unix=time.time(),elapsed_seconds=time.time()-started,
            bytes_before_closure=meter.used,reservation=reservation,oracle='not computed',
            confirmation_outcomes='not opened',scientific_verdict='pending immutable raw audit'))
        return 0
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        failure = dict(status='incomplete',exception=type(error).__name__,message=str(error),
            traceback=traceback.format_exc(),active=active,attempted_F=attempted,completed_F=completed,
            completed_nomination_queries=local_queries,failed_query_trace=getattr(error,'query_trace',None),
            reservation=reservation,started_at_unix=started,failed_at_unix=time.time(),
            policy='all failed and unused reservations remain; no automatic retry')
        publish_json(args.out/'failure.json',failure)
        print(json.dumps(failure),file=sys.stderr,flush=True)
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old_alarm)
        signal.signal(signal.SIGTERM,old_term)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--device',choices=['cuda:0'],required=True)
    parser.add_argument('--bytes-reserved',type=int,required=True)
    parser.add_argument('--deadline-unix',type=float,required=True)
    args = parser.parse_args()
    for path in (args.root,args.out,args.manifest):
        if not path.resolve().is_relative_to(Path('/data/guoyikun')):
            parser.error('B inputs and outputs must remain below /data/guoyikun')
    sys.exit(execute(args))
