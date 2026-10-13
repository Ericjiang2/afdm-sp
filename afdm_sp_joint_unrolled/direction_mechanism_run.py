"""Budgeted B-star full receiver then disk-backed eight-cell diagnostic factorial."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
import traceback

START_WALL=time.monotonic();START_CPU=time.process_time()
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[_key]='1'
import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.direction_budget import reserve_many,settle_many
from afdm_sp_joint_unrolled.direction_data import CampaignData,source_manifest
from afdm_sp_joint_unrolled.direction_receiver import ObservedReceiver
from afdm_sp_joint_unrolled.direction_factorial import run_factorial
from afdm_sp_joint_unrolled.direction_logging import validate_record,publish_snapshot,confidence_groups
from afdm_sp_joint_unrolled.direction_run import frame_record,json_value,summarize
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a


def select_recipe(path,expected_hash,protocol,protocol_hash):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_hash:raise ValueError('B-star selection file hash mismatch')
    result=json.loads(raw)
    if result['status']!='complete' or result['protocol_sha256']!=protocol_hash:
        raise ValueError('B-star selection is incomplete or belongs to another protocol')
    name=result['selection']['B_star_operational']
    recipes={r['id']:r for r in protocol['design']['recipes']}
    if len(recipes)!=8 or name not in recipes:raise ValueError('B-star not in frozen eight recipes')
    return recipes[name]


def cell_record(normal,cell,snapshot,out):
    row=copy.deepcopy(normal)
    small=publish_snapshot(out/f"cell-{normal['block_id']:06d}-{cell['cell_id']}.npz",
        {k:cell[k] for k in ('mu','var','llr','decoded','info_hat','hard')})
    Hdata=snapshot['Hhat'] if cell['data_source']=='estimated' else snapshot['Htrue']
    Hcancel=snapshot['Hhat'] if cell['cancel_source']=='estimated' else snapshot['Htrue']
    denominator=float(np.linalg.norm(snapshot['Htrue'])**2)
    if denominator<=0:raise ValueError('nonzero true channel required for NMSE')
    raw_bits=np.r_[cell['hard'].real<0,cell['hard'].imag<0]
    llr=cell['llr'];coded=snapshot['coded']
    confidence={'bit_NLL':float(np.logaddexp(0,-(1-2*coded.astype(float))*llr).mean()),
        'bit_Brier':float(np.mean((1/(1+np.exp(llr))-coded)**2)),
        'groups':confidence_groups(llr,coded),'evaluation_only':True}
    row.update(arm_id=cell['cell_id'],call_type='terminal',candidate_eligible=False,
        truth_access_level=cell['truth_access_level'],detector=cell['detector'],
        H_cancel_source=cell['H_cancel_source'],H_data_source=cell['H_data_source'],H_cov_source=cell['H_cov_source'],
        sigma_source=cell['sigma_source'],sigma_value=cell['sigma2_terminal'],
        pilot_cancellation_identity_check={'relative_error':cell['residual']['relative_vector_closure'],
            'tolerance':1e-10,'identity':'z-Hdata*true_data=cancel_error+data_channel_error+thermal_noise'},
        S_submitted_semantics='normal estimator support retained as provenance only; not oracle H support',
        K_effective_semantics='normal estimator coefficient count only; detector actual graph/dense matrix recorded separately',
        graph_edges_each_stage=cell['diagnostics']['graphs'] if cell['detector']=='BP' else [],
        detector_diagnostics=cell['diagnostics'],
        raw_bit_errors=int(np.count_nonzero(raw_bits!=coded)),coded_bit_errors=cell['info_errors'],
        decoded_codeword_bit_errors=int(np.count_nonzero(cell['decoded']!=coded)),FER=cell['FER'],
        hard_output_hash=cell['decoded_sha256'],decoder_status={'syndrome_ok':cell['decode_ok'],'maxiter':50},
        channel_error={'Hdata_actual_nmse':float(np.linalg.norm(snapshot['Htrue']-Hdata)**2/denominator),
            'Hcancel_actual_nmse':float(np.linalg.norm(snapshot['Htrue']-Hcancel)**2/denominator),
            'normal_channel_error_reference':normal['channel_error'],
            'scope':'separate cancellation/detection channel diagnostics, no support estimation performed'},
        posterior_audit={'mu':summarize(cell['mu']),'var':summarize(cell['var']),'llr':summarize(llr),
            'semantics':'EP cavity tilted QPSK moments' if cell['detector']=='EP10' else 'BP Gaussian aggregate'},
        pilot_residual={'cancel_error_energy':cell['residual']['energies']['pilot_channel_error']},
        data_residual=cell['residual'],message_confidence=confidence,
        elapsed_seconds=cell['seconds'],process_cpu_seconds=cell['CPU_seconds'],
        transfer_seconds=None,inclusive_seconds=cell['seconds'],peak_gpu_bytes=cell['peak_gpu_bytes'],
        snapshot=small,normal_snapshot_reference=normal['snapshot'],
        normal_arm_reference=normal['arm_id'],z_hash=cell['z_hash'],
        timing_scope='instrumented terminal diagnostic; not full receiver or deployable comparison',
        support_trace=[],capacity_trace=[],initial_estimator=None,
        offline_truth_access='factorial CSI intervention and evaluator; not deployable',
        failure=None,retry_of=None)
    # Old normal audit timings cannot describe this new terminal execution.
    row.pop('offline_audit_seconds',None);row.pop('offline_audit_cpu_seconds',None)
    return validate_record(json_value(row),expected_inputs=normal['input_hashes'],deployable=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','checkpoint','b-star','out','ledger'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--b-star-sha256',required=True)
    p.add_argument('--split',choices=('engineering','mechanism'),required=True)
    p.add_argument('--start',type=int,required=True);p.add_argument('--stop',type=int,required=True)
    p.add_argument('--snr',type=int,choices=(7,8,9),required=True)
    p.add_argument('--deadline-unix',type=float,required=True);p.add_argument('--device',default='cuda')
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    full_key=args.split+'_full';terminal_key=args.split+'_terminal'
    calls={full_key:0,terminal_key:0};done={full_key:0,terminal_key:0}
    active=None;outputs=[];reserved=False;peak=0
    def resources():
        elapsed=time.monotonic()-START_WALL
        return {'host_seconds':elapsed,'gpu_seconds':elapsed if args.device.startswith('cuda') else 0.,
                'cpu_core_seconds':time.process_time()-START_CPU}
    def attempt(key,metadata):
        nonlocal active
        if time.time()>=args.deadline_unix:raise TimeoutError('deadline before receiver/terminal attempt')
        if calls[key]>=limits[key]:raise RuntimeError('reserved call budget exhausted')
        calls[key]+=1;active=dict(metadata,call_key=key,ordinal=calls[key],started_unix=time.time())
        publish_json(args.out/f'started-{key}-{calls[key]:06d}.json',active)
    def committed(key,path):
        nonlocal active
        publish_json(args.out/f'completed-{key}-{calls[key]:06d}.json',dict(active,
            record=str(path),record_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        done[key]+=1;outputs.append(str(path));active=None
    try:
        duration=args.deadline_unix-time.time()
        if not math.isfinite(duration) or duration<=0 or args.start<0 or args.stop<=args.start:
            raise ValueError('invalid deadline or block range')
        cores=sorted(os.sched_getaffinity(0))
        if len(cores)!=4:raise ValueError('exactly four CPU affinity cores required')
        if args.ledger.resolve()!=(args.out.parent/'resource-ledger.json').resolve():
            raise ValueError('shared campaign ledger required')
        protocol=json.loads(args.protocol.read_text());phash=hashlib.sha256(args.protocol.read_bytes()).hexdigest()
        recipe=select_recipe(args.b_star,args.b_star_sha256,protocol,phash)
        reference=args.protocol.parent/'detector-reference-preregister.json'
        ref=json.loads(reference.read_text())
        if ref['campaign_protocol_sha256']!=phash or ref['detector_id']!='real-EP10-damp0.5-f64':
            raise ValueError('reference detector preregistration/protocol mismatch')
        limits={full_key:args.stop-args.start,terminal_key:8*(args.stop-args.start)}
        reserve_many(args.ledger,args.out.name,campaign_id=protocol['campaign_id'],protocol_sha256=phash,
            calls=limits,resources={'host_seconds':duration,'gpu_seconds':duration if args.device.startswith('cuda') else 0,
                                   'cpu_core_seconds':duration*4})
        reserved=True
        def timeout(signum,frame):raise TimeoutError('registered mechanism wall deadline reached')
        signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,max(.001,args.deadline_unix-time.time()))
        contract={'protocol_sha256':phash,'source_sha256':source_manifest(),'recipe':recipe,
            'B_star_sha256':args.b_star_sha256,'detector_reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
            'affinity':cores,'calls_reserved':limits,'split':args.split,'blocks':list(range(args.start,args.stop)),
            'snr':args.snr,'command':[sys.executable]+sys.argv,'no_inplace_resume':True}
        config_hash=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
        publish_json(args.out/'contract.json',contract)
        dev=torch.device(args.device)
        if dev.type=='cuda' and not torch.cuda.is_available():raise ValueError('requested CUDA unavailable')
        torch.set_num_threads(1)
        system=_make_config_a(1024,2.,8,10.,4.);code=build_code();data=CampaignData(args.protocol,code)
        for block in range(args.start,args.stop):data._validate_request(args.split,block,args.snr)
        receiver=ObservedReceiver.build(args.checkpoint,system,code,device=args.device)
        for block in range(args.start,args.stop):
            if time.time()>=args.deadline_unix:raise TimeoutError('deadline before generator')
            frame=data.make_frame(system,args.split,block,args.snr)
            attempt(full_key,{'block':block,'arm_id':recipe['id'],'call_type':'full'})
            if dev.type=='cuda':torch.cuda.reset_peak_memory_stats(dev)
            c0=time.process_time()
            normal_result=receiver.run(frame.observed,family=recipe['family'],parameter=recipe['parameter'],
                                        terminal_scale=recipe['terminal_scale'],audit=True)
            current=int(torch.cuda.max_memory_allocated(dev)) if dev.type=='cuda' else 0;peak=max(peak,current)
            normal=frame_record(args.out.name,frame,normal_result,recipe,system,args.out,dev,
                                time.process_time()-c0,current,config_hash)
            normal_path=args.out/f'normal-full-{block:06d}.json'
            publish_json(normal_path,normal);committed(full_key,normal_path)
            del normal_result
            # Re-open immutable disk evidence, never reuse in-memory receiver arrays.
            spath=Path(normal['snapshot']['path'])
            if hashlib.sha256(spath.read_bytes()).hexdigest()!=normal['snapshot']['sha256']:
                raise ValueError('normal terminal snapshot hash mismatch')
            with np.load(spath,allow_pickle=False) as loaded:snapshot={k:loaded[k].copy() for k in loaded.files}
            def before_cell(meta):attempt(terminal_key,dict(meta,block=block))
            def on_cell(cell):
                nonlocal peak
                if cell['cell_id']!=active['cell_id']:raise AssertionError('terminal result does not match attempt')
                peak=max(peak,cell['peak_gpu_bytes'])
                row=cell_record(normal,cell,snapshot,args.out)
                row['budget']={'attempt':calls[terminal_key],'reserved':limits[terminal_key]}
                destination=args.out/f'cell-{block:06d}-{cell["cell_id"]}.json'
                publish_json(destination,row);committed(terminal_key,destination)
            factorial=run_factorial(snapshot,code,device=dev,before_call=before_cell,on_cell=on_cell)
            comparison=json_value(factorial['normal_output'])
            publish_json(args.out/f'normal-replay-comparison-{block:06d}.json',comparison)
        result={'status':'complete','calls_attempted':calls,'calls_completed':done,'resources':resources(),
            'peak_gpu_bytes':peak,'records':outputs,
            'record_sha256':{v:hashlib.sha256(Path(v).read_bytes()).hexdigest() for v in outputs},
            'source_sha256':contract['source_sha256'],'protocol_sha256':phash,
            'B_star_sha256':args.b_star_sha256,'detector_reference_sha256':contract['detector_reference_sha256']}
        publish_json(args.out/'complete.json',result)
        settle_many(args.ledger,args.out.name,calls=calls,resources=resources(),evidence=str(args.out/'complete.json'),status='complete')
        reserved=False
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        publish_json(args.out/'failure.json',{'status':'failed','exception':type(exc).__name__,
            'message':str(exc),'traceback':traceback.format_exc(),'calls_attempted':calls,
            'calls_completed':done,'active_attempt':active,'completed_records':outputs,
            'resources':resources(),'peak_gpu_bytes':peak,'B_star_sha256':args.b_star_sha256})
        if reserved:settle_many(args.ledger,args.out.name,calls=calls,resources=resources(),
            evidence=str(args.out/'failure.json'),status='failed')
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':main()
