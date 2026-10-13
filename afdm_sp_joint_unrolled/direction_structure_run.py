"""Immutable budgeted restricted-structure CE and terminal replay driver."""
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
for _k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[_k]='1'
import numpy as np
import torch
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.direction_budget import reserve_many,settle_many
from afdm_sp_joint_unrolled.direction_data import CampaignData,source_manifest,campaign_rng
from afdm_sp_joint_unrolled.direction_logging import validate_record,publish_snapshot,confidence_groups
from afdm_sp_joint_unrolled.direction_run import json_value,summarize
from afdm_sp_joint_unrolled.direction_structure_replay import prepare,run_arm,ARMS
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a


def admission(algorithm,allocation,phash,split,start,stop,snr):
    if (algorithm['status']!='algorithm_preregistered_before_structure_results'
            or allocation['status']!='allocation_frozen_before_structure_results'
            or allocation['protocol_sha256']!=phash or allocation['blocks']!=list(range(255))
            or allocation['SNR']!=[7,8,9] or allocation['arms']!=['M_'+a for a in ARMS]):
        raise ValueError('structure registry mismatch')
    group=algorithm['group']
    if (group['iterations_max'],group['absolute_tolerance'],group['relative_tolerance'])!=(2000,1e-7,1e-6):
        raise ValueError('group solver contract changed')
    if type(start) is not int or type(stop) is not int or not 0<=start<stop:
        raise ValueError('invalid block range')
    if split=='engineering':
        if (start,stop,snr)!=(17,18,8):raise ValueError('only engineering block17/SNR8 four-arm wiring authorized')
    elif split=='mechanism':
        if stop>255 or snr not in (7,8,9):raise ValueError('outside frozen255-block structure allocation')
    else:raise ValueError('invalid structure split')


def locate_normal(directories,block,split,snr,phash):
    matches=[]
    for root in directories:
        path=Path(root)/f'normal-full-{block:06d}.json'
        if path.exists():
            row=json.loads(path.read_text())
            if (row['split'],row['SNR'],row['block_id'])==(split,snr,block):
                if row['protocol_sha256']!=phash or row['call_type']!='full' or row['failure'] is not None:
                    raise ValueError('invalid normal full provenance')
                matches.append(path)
    if len(matches)!=1:raise ValueError('normal input must resolve uniquely')
    return matches[0]


def terminal_record(prepared,result,run_id,config_hash,sources,snapshot,geometry):
    normal=prepared['normal'];s=prepared['snapshot'];r=copy.deepcopy(normal)
    ids=result['atom_ids'];H=result['Hfit'];sigma=result['sigma2_terminal'];llr=result['llr'];coded=s['coded']
    raw=np.r_[result['x_hard'].real<0,result['x_hard'].imag<0]
    norm=float(np.linalg.norm(s['Htrue'])**2)
    if norm<=0:raise ValueError('channel NMSE needs nonzero truth')
    r.update(run_id=run_id,config_sha256=config_hash,source_sha256=sources,
        device=result['device'],dtype={'fit':'complex128','terminal':'complex128'},
        arm_id=result['arm_id'],call_type='terminal',candidate_eligible=False,
        truth_access_level='geometry_oracle',oracle_information=result['oracle_information'],
        H_cancel_source={'source':'restricted_Hfit','sha256':result['Hfit_sha256']},
        H_data_source={'source':'restricted_Hfit','sha256':result['Hfit_sha256']},
        H_cov_source={'source':'fresh_BP_scalar_noise','H_sha256':result['Hfit_sha256']},
        sigma_source='unchanged normal B_star sigma2_terminal',sigma_value=sigma,
        S_initial=ids,S_submitted=ids,K_nominal=len(ids),
        K_effective=int(np.count_nonzero(result['coefficients'])),
        S_submitted_semantics='common I, coefficients fitted only on I; no added atom',
        normal_support_provenance=normal['S_submitted'],normal_B_star_provenance=normal['arm_id'],
        normal_record_sha256=prepared['normal_record_sha256'],
        physical_group_count=int(prepared['basis'].shape[1]),physical_group_status='true geometry slots for offline audit only; not supplied to free fit or estimated paths',
        graph_edges_each_stage=result['graphs'],raw_bit_errors=int(np.count_nonzero(raw!=coded)),
        coded_bit_errors=result['info_errors'],FER=result['FER'],
        decoded_codeword_bit_errors=int(np.count_nonzero(result['decoded']!=coded)),
        hard_output_hash=array_hash(result['decoded']),decoder_status={'syndrome_ok':result['decode_ok'],'maxiter':50},
        channel_error={'actual_nmse':float(np.linalg.norm(s['Htrue']-H)**2/norm),
                       'scope':'restricted Hfit; common support omissions retained'},
        posterior_audit={'mu':summarize(result['mu']),'var':summarize(result['var']),'llr':summarize(llr),
                         'semantics':'actual terminal BP Gaussian aggregate'},
        message_confidence={'groups':confidence_groups(llr,coded),
            'bit_NLL':float(np.logaddexp(0,-(1-2*coded.astype(float))*llr).mean()),
            'bit_Brier':float(np.mean((1/(1+np.exp(llr))-coded)**2)),'evaluation_only':True},
        pilot_cancellation_identity_check={'relative_error':result['residual']['relative_vector_closure'],'tolerance':1e-10},
        pilot_residual={'cancel_error_energy':result['residual']['energies']['pilot_channel_error']},
        data_residual=result['residual'],elapsed_seconds=result['terminal_seconds'],
        process_cpu_seconds=result['terminal_cpu_seconds'],peak_gpu_bytes=result['peak_gpu_bytes'],
        fit_seconds=result['fit_seconds'],fit_cpu_seconds=result['fit_cpu_seconds'],
        fit_diagnostics=result['fit_diagnostics'],transfer_seconds=None,inclusive_seconds=None,
        timing_scope='restricted CE and terminal measured separately; regeneration/writes included in run resources',
        snapshot=snapshot,geometry_snapshot=geometry,z_hash=result['z_sha256'],
        support_trace=[],capacity_trace=[],initial_estimator=None,recipe=None,
        failure=None,retry_of=None,offline_truth_access='geometry diagnostic container only; fit receives no true gain/data/H')
    for k in ('offline_audit_seconds','offline_audit_cpu_seconds','budget'):r.pop(k,None)
    return validate_record(json_value(r),expected_inputs=normal['input_hashes'],deployable=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','algorithm-registry','allocation-registry','out','ledger'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--normal-dir',type=Path,action='append',required=True)
    p.add_argument('--split',choices=('engineering','mechanism'),required=True)
    p.add_argument('--start',type=int,required=True);p.add_argument('--stop',type=int,required=True)
    p.add_argument('--snr',type=int,required=True);p.add_argument('--deadline-unix',type=float,required=True)
    p.add_argument('--device',default='cuda');args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    terminal_key='engineering_terminal' if args.split=='engineering' else 'structure_terminal'
    calls={'structure_CE':0,terminal_key:0};completed=dict(calls);records=[];normal_provenance=[]
    reserved=False;active=None;peak=0
    def resources():
        elapsed=time.monotonic()-START_WALL
        return {'host_seconds':elapsed,'gpu_seconds':elapsed if args.device.startswith('cuda') else 0,
                'cpu_core_seconds':time.process_time()-START_CPU}
    def done(key,path):
        nonlocal active
        publish_json(args.out/f'completed-{key}-{calls[key]:06d}.json',dict(active,record=str(path),
            record_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        completed[key]+=1;records.append(str(path));active=None
    try:
        duration=args.deadline_unix-time.time()
        if not math.isfinite(duration) or duration<=0:raise ValueError('future finite deadline required')
        cores=sorted(os.sched_getaffinity(0))
        if not 1<=len(cores)<=4:raise ValueError('CPU affinity must contain at most four cores')
        if args.ledger.resolve()!=(args.out.parent/'resource-ledger.json').resolve():raise ValueError('shared campaign ledger required')
        protocol=json.loads(args.protocol.read_text());phash=hashlib.sha256(args.protocol.read_bytes()).hexdigest()
        algorithm=json.loads(args.algorithm_registry.read_text());allocation=json.loads(args.allocation_registry.read_text())
        admission(algorithm,allocation,phash,args.split,args.start,args.stop,args.snr)
        inputs={b:locate_normal(args.normal_dir,b,args.split,args.snr,phash) for b in range(args.start,args.stop)}
        limits={key:4*(args.stop-args.start) for key in calls}
        reserve_many(args.ledger,args.out.name,campaign_id=protocol['campaign_id'],protocol_sha256=phash,
            calls=limits,resources={'host_seconds':duration,'gpu_seconds':duration if args.device.startswith('cuda') else 0,
                                   'cpu_core_seconds':duration*len(cores)})
        reserved=True
        def deadline(signum,frame):raise TimeoutError('registered structure deadline reached')
        signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,max(.001,args.deadline_unix-time.time()))
        sources=source_manifest()
        contract={'protocol_sha256':phash,'algorithm_registry_sha256':hashlib.sha256(args.algorithm_registry.read_bytes()).hexdigest(),
            'allocation_registry_sha256':hashlib.sha256(args.allocation_registry.read_bytes()).hexdigest(),
            'source_sha256':sources,'split':args.split,'blocks':list(inputs),'SNR':args.snr,
            'normal_inputs':{str(b):str(v) for b,v in inputs.items()},'calls_reserved':limits,
            'affinity':cores,'command':[sys.executable]+sys.argv,'no_inplace_resume':True}
        config_hash=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest();publish_json(args.out/'contract.json',contract)
        dev=torch.device(args.device)
        if dev.type=='cuda' and not torch.cuda.is_available():raise ValueError('CUDA unavailable; no fallback')
        torch.set_num_threads(1);system=_make_config_a(1024,2.,8,10.,4.);code=build_code();data=CampaignData(args.protocol,code)
        for block,path in inputs.items():
            if time.time()>=args.deadline_unix:raise TimeoutError('deadline before geometry regeneration')
            started=time.perf_counter();prepared=prepare(path,system,data);regeneration=time.perf_counter()-started
            geometry=publish_snapshot(args.out/f'geometry-{block:06d}.npz',dict(
                I=prepared['I'],L_I=prepared['basis'],incidence=prepared['basis']!=0,
                S_true=np.asarray(prepared['truth_support']),**{k:np.asarray(v) for k,v in prepared['geometry'].items()}))
            normal_provenance.append({'path':str(path),'sha256':prepared['normal_record_sha256'],
                'geometry_snapshot':geometry,'regeneration_seconds':regeneration,'pairing_verified':prepared['pairing_verified']})
            order=list(ARMS);campaign_rng(args.split,block,'order').shuffle(order)
            for arm in order:
                def before(kind,which):
                    nonlocal active
                    if which!=arm:raise AssertionError('unexpected structure arm')
                    key='structure_CE' if kind=='CE' else terminal_key
                    if kind not in ('CE','terminal'):raise ValueError('unknown call kind')
                    if time.time()>=args.deadline_unix:raise TimeoutError('deadline before structure call')
                    if calls[key]>=limits[key]:raise RuntimeError('structure call reservation exhausted')
                    calls[key]+=1;active={'call_key':key,'ordinal':calls[key],'block':block,'arm':arm,'started_unix':time.time()}
                    publish_json(args.out/f'started-{key}-{calls[key]:06d}.json',active)
                def on_fit(fitted,seconds,cpu_seconds):
                    shot=publish_snapshot(args.out/f'CE-{block:06d}-{arm}.npz',{'I':np.asarray(fitted['atom_ids']),
                        'coefficients':fitted['coefficients']})
                    record={'call_type':'CE','arm_id':'M_'+arm,'block_id':block,'split':args.split,'SNR':args.snr,
                        'fit_diagnostics':fitted['diagnostics'],'snapshot':shot,'geometry_snapshot':geometry,
                        'elapsed_seconds':seconds,'CPU_seconds':cpu_seconds,'source_sha256':sources,'protocol_sha256':phash,
                        'config_sha256':config_hash,'normal_record_sha256':prepared['normal_record_sha256'],
                        'input_hashes':prepared['normal']['input_hashes'],'failure':None,'candidate_eligible':False}
                    dest=args.out/f'CE-{block:06d}-{arm}.json';publish_json(dest,json_value(record));done('structure_CE',dest)
                started=time.perf_counter();result=run_arm(prepared,system,code,arm,device=dev,before_call=before,on_fit=on_fit)
                whole_arm=time.perf_counter()-started;peak=max(peak,result['peak_gpu_bytes'])
                shot=publish_snapshot(args.out/f'terminal-{block:06d}-{arm}.npz',
                    {k:result[k] for k in ('Hfit','coefficients','mu','var','llr','decoded','info_hat','x_hard')})
                row=terminal_record(prepared,result,args.out.name,config_hash,sources,shot,geometry)
                row['whole_arm_instrumented_seconds']=whole_arm
                dest=args.out/f'terminal-{block:06d}-{arm}.json';publish_json(dest,row);done(terminal_key,dest)
        publish_json(args.out/'complete.json',{'status':'complete','calls_attempted':calls,'calls_completed':completed,
            'resources':resources(),'records':records,'record_sha256':{v:hashlib.sha256(Path(v).read_bytes()).hexdigest() for v in records},
            'normal_provenance':normal_provenance,'peak_gpu_bytes':peak,**contract})
        settle_many(args.ledger,args.out.name,calls=calls,resources=resources(),evidence=str(args.out/'complete.json'),status='complete');reserved=False
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        publish_json(args.out/'failure.json',{'status':'failed','exception':type(exc).__name__,'message':str(exc),
            'traceback':traceback.format_exc(),'calls_attempted':calls,'calls_completed':completed,'active_attempt':active,
            'completed_records':records,'normal_provenance':normal_provenance,'resources':resources()})
        if reserved:settle_many(args.ledger,args.out.name,calls=calls,resources=resources(),evidence=str(args.out/'failure.json'),status='failed')
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':main()
