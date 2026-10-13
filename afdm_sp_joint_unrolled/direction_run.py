"""Immutable, budgeted direction-campaign full-receiver diagnostic runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
import traceback

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash, project_channel_on_support
from afdm_sp_joint_unrolled.direction_data import CampaignData, campaign_rng, source_manifest
from afdm_sp_joint_unrolled.direction_receiver import ObservedReceiver
from afdm_sp_joint_unrolled.direction_logging import validate_record, validate_pair, publish_snapshot, confidence_groups
from afdm_sp_joint_unrolled.direction_budget import reserve, settle
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.v3_metrics import initial_error
from afdm_sp_joint_unrolled.v3_statistics import residual_decomposition


def json_value(value):
    if isinstance(value,np.ndarray):
        if np.iscomplexobj(value):
            return {'real':value.real.tolist(),'imag':value.imag.tolist()}
        return value.tolist()
    if isinstance(value,np.generic):
        return json_value(value.item())
    if isinstance(value,complex):
        return {'real':value.real,'imag':value.imag}
    if isinstance(value,dict):
        return {k:json_value(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):
        return [json_value(v) for v in value]
    return value


def summarize(value):
    if isinstance(value,(np.ndarray,np.generic)):
        a=np.asarray(value)
        if not np.isfinite(a).all():
            raise FloatingPointError('nonfinite observer state')
        return {'shape':list(a.shape),'dtype':str(a.dtype),'sha256':array_hash(a),
                'norm':float(np.linalg.norm(a)),
                'value':json_value(a) if a.size<=1 else None}
    if isinstance(value,dict):
        return {k:summarize(v) for k,v in value.items()}
    return json_value(value)


def channel_audit(system,frame,result):
    Hhat=np.asarray(result['H'],dtype=np.complex128)
    ids=np.asarray(result['support'],dtype=int)
    projected,g=project_channel_on_support(torch.from_numpy(Hhat),torch.tensor(ids//5),
        torch.tensor(ids%5-2),system.c1,system.c2,2)
    projected=projected.numpy()
    coefficients=np.zeros(515,complex)
    coefficients[ids]=g.numpy()
    truth=frame._truth
    ledger=initial_error(system,{'params':truth['params'],'H':truth['H']},coefficients,ids.tolist())
    denominator=float(np.linalg.norm(truth['H'])**2)
    error=truth['H']-projected
    outside=projected-Hhat
    outside_energy=float(np.linalg.norm(outside)**2/denominator)
    cross=float(2*np.vdot(error,outside).real/denominator)
    actual=float(np.linalg.norm(truth['H']-Hhat)**2/denominator)
    closure=actual-ledger['nmse']-outside_energy-cross
    if abs(closure)>1e-8*max(1.,actual):
        raise AssertionError('projected channel plus outside-span error failed closure')
    return {'actual_nmse':actual,'projected_estimate_ledger':ledger,
            'projection_residual_relative_to_actual':float(np.linalg.norm(outside)/max(np.linalg.norm(Hhat),np.finfo(float).tiny)),
            'outside_support_span_energy':outside_energy,'cross_with_projected_error':cross,
            'actual_nmse_closure':closure,
            'scope':'Analytic Frobenius projection of actual Hhat; ledger applies to projection. Outside-span error/cross retained explicitly.'}


def frame_record(run_id,frame,result,recipe,system,out,device,cpu_seconds,peak,config_hash):
    meta,truth,obs=frame.metadata,frame._truth,frame.observed
    Hhat=result['H']
    Hhash=array_hash(Hhat)
    cancelled=obs['y']-Hhat@obs['pilot']
    # Separate cancellation-path identity from the full three-term residual ledger.
    identity=cancelled-(truth['H']@truth['data']+
                           (truth['H']-Hhat)@obs['pilot']+
                           np.sqrt(obs['sigma2'])*truth['noise'])
    identity_error=float(np.linalg.norm(identity)/max(1.,np.linalg.norm(obs['y'])))
    decomposition=residual_decomposition(obs['y'],truth['H'],Hhat,obs['pilot'],truth['data'],result['x_soft'])
    if identity_error>1e-10 or decomposition['relative_vector_closure']>1e-10:
        raise AssertionError('pilot cancellation or residual decomposition failed')
    raw_bits=np.concatenate((result['x_hard'].real<0,result['x_hard'].imag<0)).astype(np.uint8)
    raw_errors=int(np.count_nonzero(raw_bits!=truth['coded']))
    info_errors=int(np.count_nonzero(result['info_hat']!=truth['info']))
    transform=result.get('cancellation_transform')
    extra_arrays={} if transform is None else {
        'detector_H':transform['H'],'detector_z':transform['z'],
        'cancellation_B':transform['B'],
        'sigma2_terminal_base':np.array(result['sigma2_terminal_base'])}
    refit=result.get('channel_refit')
    if refit is not None:
        extra_arrays.update(H_before_refit=refit['H_before'],gains_before_refit=refit['gains_before'],
                            gains_after_refit=result['gains'])
    snapshot=publish_snapshot(out/f"terminal-{meta['block']:06d}-{recipe['id']}.npz",{**extra_arrays,
        'Hhat':Hhat,'Htrue':truth['H'],'y':obs['y'],'pilot':obs['pilot'],
        'constellation':obs['constellation'],'sigma2':np.array(result['sigma2']),
        'sigma2_terminal':np.array(result['sigma2_terminal']),'sigma2_thermal':np.array(obs['sigma2']),
        'info':truth['info'],'coded':truth['coded'],'data':truth['data'],'noise':truth['noise'],
        'support':np.asarray(result['support'],dtype=np.int64),'mu':result['mu'],'var':result['var'],
        'llr':result['llr'],'decoded':result['decoded'],'info_hat':result['info_hat'],
        'x_soft':result['x_soft'],'x_hard':result['x_hard']})
    initial=result['initial_estimator']['support']
    truth_sign=1-2*truth['coded'].astype(float)
    confidence={'bit_NLL':float(np.logaddexp(0,-truth_sign*result['llr']).mean()),
                'bit_Brier':float(np.mean((1/(1+np.exp(result['llr']))-truth['coded'])**2)),
                'abs_llr_mean':float(np.abs(result['llr']).mean()),
                'confidence_error_groups':confidence_groups(result['llr'],truth['coded']),
                'evaluation_only':True}
    record={'run_id':run_id,'split':meta['split'],'block_id':meta['block'],
        'channel_seed':meta['channel_seed'],'data_seed':meta['data_seed'],
        'noise_seed':{'seed_words':meta['rng_words']['noise']},'code_id':meta['code_id'],
        'interleaver_id':meta['interleaver_id'],'SNR':meta['snr_db'],'rho':.5,'P_phys':8,
        'generator_id':'real_UWA_generate_channel_matrix','truncation_id':'k_leak2-relative_power_prune0.01-clip2-global_Frobenius',
        'source_sha256':result['source_sha256'],'config_sha256':config_hash,'prior_sha256':None,
        'device':str(device),'dtype':{'outer':'complex64','terminal_BP':'complex128'},
        'library_versions':{'numpy':np.__version__,'torch':torch.__version__},
        'deterministic_flags':{'torch_algorithms':torch.are_deterministic_algorithms_enabled(),
            'cudnn_deterministic':torch.backends.cudnn.deterministic,'cudnn_benchmark':torch.backends.cudnn.benchmark},
        'raw_y_hash':meta['input_hashes']['y'],'pilot_hash':meta['input_hashes']['pilot'],
        'H_true_hash':meta['input_hashes']['H'],'truth_access_level':'none','arm_id':recipe['id'],
        'H_cancel_source':{'stage':'final_estimate','sha256':Hhash},
        'H_data_source':{'stage':'final_estimate','sha256':Hhash},
        'H_cov_source':{'stage':'scalar_BP_no_explicit_C','H_sha256':Hhash,
                        'outer_sources':[s['H']['sha256'] for s in map(summarize,result['dals'])]},
        'sigma_source':'final_receiver_sigma2 * frozen terminal_scale',
        'sigma_value':result['sigma2_terminal'],'sigma_estimated':result['sigma2'],
        'sigma_thermal':obs['sigma2'],'terminal_scale':result['terminal_scale'],
        'pilot_cancellation_identity_check':{'relative_error':identity_error,'tolerance':1e-10},
        'S_initial':initial,'S_submitted':result['support'],'K_nominal':len(result['support']),
        'K_effective':int(np.count_nonzero(np.abs(result['gains'])>0)),
        'physical_group_count':None,'physical_group_status':'independent_atoms_no_estimated_physical_slots',
        'graph_edges_each_stage':result['graphs'],'raw_bit_errors':raw_errors,
        'coded_bit_errors':info_errors,'decoded_codeword_bit_errors':int(np.count_nonzero(result['decoded']!=truth['coded'])),
        'raw_bits_denominator':len(truth['coded']),'coded_bits_denominator':len(truth['info']),
        'FER':int(info_errors>0),'hard_output_hash':array_hash(result['decoded']),
        'decoder_status':{'syndrome_ok':result['decode_ok'],'maxiter':50},
        'channel_error':channel_audit(system,frame,result),
        'posterior_audit':{'mu':summarize(result['mu']),'var':summarize(result['var']),
                           'llr':summarize(result['llr']),'semantics':'Gaussian BP aggregate; not finite-alphabet posterior moments',
                           'dals':[summarize(s) for s in result['dals']]},
        'pilot_residual':{'cancel_error_energy':float(np.mean(abs((truth['H']-Hhat)@obs['pilot'])**2))},
        'data_residual':decomposition,'message_confidence':confidence,'call_type':'full',
        'elapsed_seconds':result['seconds'],'process_cpu_seconds':cpu_seconds,
        'transfer_seconds':result['transfer_seconds'],'inclusive_seconds':result['inclusive_seconds'],
        'timing_scope':'instrumented diagnostic; not isolated A2 mean/p95 deployment cost gate',
        'peak_gpu_bytes':peak,'failure':None,'retry_of':None,'snapshot':snapshot,
        'input_hashes':meta['input_hashes'],'protocol_sha256':meta['protocol_sha256'],
        'rng_words':meta['rng_words'],
        'capacity_trace':result['capacity_trace'],'support_trace':result['support_trace'],
        'initial_estimator':result['initial_estimator'],'recipe':recipe,
        'actual_tx_energy':meta['actual_tx_energy'],'pilot_data_cross_term':meta['pilot_data_cross_term'],
        'data_snr_db':meta['data_snr_db'],'offline_truth_access':'logger/evaluator only, never passed to observed receiver'}
    if transform is not None:
        record.update(H_cov_source='observed_final_support_working_gain_covariance',
            H_data_source='estimated_H_after_registered_left_transform',
            sigma_source='registered_cancellation_working_model',
            cancellation_transform=transform['diagnostics'],
            detector_H_sha256=array_hash(transform['H']),
            detector_z_sha256=array_hash(transform['z']),
            cancellation_B_sha256=array_hash(transform['B']),
            sigma2_terminal_base=result['sigma2_terminal_base'])
    if refit is not None:
        record['physical_refit']=refit['diagnostics']
        record['H_cancel_source']={'stage':'observed_physical_refit','sha256':Hhash}
        record['H_data_source']={'stage':'observed_physical_refit','sha256':Hhash}
    record=json_value(record)
    return validate_record(record,expected_inputs=meta['input_hashes'],deployable=True)


def physical_engineering_registry(path, split, start, stop, snr, max_calls):
    """Population data remain locked until a separate reviewed M admission."""
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != 'a935882dca5bf6d7face0df68a8010481f698b82ef0ae39c2f784608f16bf084':
        raise ValueError('physical registry differs from frozen contract')
    if (split!='engineering' or snr!=8 or not 22<=start<stop<=26
            or not 1<=max_calls<=18):
        raise ValueError('physical stage admits engineering blocks22..25 at8dB only')
    registry=json.loads(raw)
    if set(registry['arms'])!={'m-group','m-param-budget','m-param-reference','m-soft'}:
        raise ValueError('physical arm registry mismatch')
    return registry


def validate_cancellation_admission(path, expected_sha, registry, protocol, ledger, chosen):
    """Require a source-bound engineering/cost decision before development data."""
    if path is None or not expected_sha:
        raise ValueError('design requires cancellation engineering admission and hash')
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise ValueError('cancellation admission hash mismatch')
    decision=json.loads(raw)
    if (decision['status']!='approved_for_design'
            or decision['registry_sha256']!=hashlib.sha256(Path(registry).read_bytes()).hexdigest()
            or decision['protocol_sha256']!=hashlib.sha256(Path(protocol).read_bytes()).hexdigest()
            or decision['source_sha256']!=source_manifest()):
        raise ValueError('cancellation admission provenance/status mismatch')
    allowed=decision['allowed_modes']
    if (not allowed or len(allowed)!=len(set(allowed))
            or not set(allowed)<= {'scalar','diagonal','lowrank'}
            or any(arm not in ['cancel-'+mode for mode in allowed] for arm in chosen)):
        raise ValueError('unapproved cancellation mode')
    evidence=decision['engineering_complete']
    complete_raw=Path(evidence['path']).read_bytes()
    if hashlib.sha256(complete_raw).hexdigest()!=evidence['sha256']:
        raise ValueError('engineering complete evidence hash mismatch')
    complete=json.loads(complete_raw)
    if (complete['status']!='complete' or complete['calls_attempted']!=20
            or complete['calls_completed']!=20 or complete['source_sha256']!=decision['source_sha256']):
        raise ValueError('engineering full-call/source evidence incomplete')
    state=json.loads(Path(ledger).read_text())
    required=decision['required_remaining_resources']
    if set(required)!=set(state['limits']):raise ValueError('incomplete resource projection')
    for key,cap in state['limits'].items():
        amount=required[key]
        if (type(amount) not in (int,float) or not math.isfinite(amount) or amount<=0
                or amount+sum(row[key] for row in state['completed']+state['reservations'])>cap):
            raise ValueError('cancellation continuation resource projection no longer fits')
    return decision


PHYSICAL_DEVELOPMENT_SHA256='3a4816a591e4951285b6f994757815d1ef482a1f5810637760c18bf54f8ab393'


def _bound_json(evidence):
    raw=Path(evidence['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=evidence['sha256']:
        raise ValueError('bound evidence hash mismatch: '+str(evidence['path']))
    return json.loads(raw)


def validate_physical_admission(path, expected_sha, registry, protocol, ledger,
                                chosen, start, stop, snr, max_calls):
    """Validate frozen development authority and metadata-only baseline reuse."""
    if path is None or not expected_sha:
        raise ValueError('design requires physical admission and hash')
    decision=_bound_json(dict(path=path,sha256=expected_sha))
    prereg=decision['preregister']
    if prereg['sha256']!=PHYSICAL_DEVELOPMENT_SHA256:
        raise ValueError('physical development preregistration changed')
    plan=_bound_json(prereg)
    if (decision['status']!='approved_for_design'
            or decision['source_sha256']!=source_manifest()
            or decision['algorithm_sha256']!=plan['algorithm_sha256']
            or decision['algorithm_sha256']!=hashlib.sha256(Path(registry).read_bytes()).hexdigest()
            or decision['protocol_sha256']!=plan['protocol_sha256']
            or decision['protocol_sha256']!=hashlib.sha256(Path(protocol).read_bytes()).hexdigest()):
        raise ValueError('physical admission provenance/status mismatch')
    if (start!=plan['block_start'] or stop!=plan['block_stop'] or snr!=plan['SNR']
            or len(chosen)!=len(plan['new_arms']) or set(chosen)!=set(plan['new_arms'])
            or max_calls!=plan['new_full_calls']):
        raise ValueError('physical design requires complete frozen anchor and four arms')
    evidence=decision['engineering_audit']
    if evidence['sha256']!=plan['engineering_audit_sha256']:
        raise ValueError('physical engineering audit differs from preregistration')
    audit=_bound_json(evidence)
    if (audit['exit_code']!=0 or audit['records']!=18
            or sum(job['calls'] for job in audit['jobs'].values())!=18
            or audit['jobs']['physical-engineering-v9']['calls']!=16
            or not all(audit[k] is True for k in ('same_parent_state_each_block',
                'single_terminal_graph_and_H_consumption_verified',
                'independent_H_assembly_and_fitted_residual_verified'))):
        raise ValueError('physical engineering integration incomplete')
    engineering=_bound_json(decision['engineering_complete'])
    if (decision['engineering_complete']['sha256']!=audit['jobs']['physical-engineering-v9']['complete_sha256']
            or engineering['status']!='complete' or engineering['calls_attempted']!=16
            or engineering['calls_completed']!=16):
        raise ValueError('physical engineering source evidence incomplete')
    numerical=lambda manifest:{k:v for k,v in manifest.items()
        if k!='direction_run.py' and not Path(k).name.startswith('test_')}
    if numerical(engineering['source_sha256'])!=numerical(decision['source_sha256']):
        raise ValueError('physical numerical source changed since engineering')
    state=json.loads(Path(ledger).read_text())
    rows=state['completed']+state['reservations']
    if (state['campaign_id']!=plan['campaign_id'] or state['protocol_sha256']!=plan['protocol_sha256']
            or max_calls+sum(r.get('calls',{}).get('prototype_full',0) for r in rows)>state['calls_caps']['prototype_full']):
        raise ValueError('physical development call budget/protocol mismatch')
    required=decision['required_remaining_resources']
    minimum=plan['resources']['anchor_deadline_seconds']
    floor=dict(host_seconds=minimum,gpu_seconds=minimum,cpu_core_seconds=4*minimum)
    if set(required)!=set(state['limits']) or set(required)!=set(floor):
        raise ValueError('incomplete physical resource projection')
    for key,cap in state['limits'].items():
        amount=required[key]
        if (type(amount) not in (int,float) or not math.isfinite(amount)
                or amount<floor[key] or amount+sum(r[key] for r in rows)>cap):
            raise ValueError('physical development resource projection no longer fits')
    cache={}
    if len(decision['baseline_cache'])!=2:
        raise ValueError('physical development requires both original baseline segments')
    for segment in decision['baseline_cache']:
        complete=_bound_json(segment['complete'])
        if (complete['status']!='complete' or complete['calls_completed']!=768 or complete['calls_attempted']!=768
                or len(segment['records'])!=96
                or complete['source_sha256']!=segment['source_sha256']
                or complete['config_sha256']!=segment['config_sha256']
                or complete['protocol_sha256']!=plan['protocol_sha256']):
            raise ValueError('cached baseline completion provenance mismatch')
        for entry in segment['records']:
            if complete['record_sha256'].get(entry['path'])!=entry['sha256']:
                raise ValueError('cached baseline record is not bound by completion')
            row=_bound_json(entry)
            block=row['block_id']
            if (type(block) is not int or block in cache or not start<=block<stop
                    or row['split']!='design' or row['SNR']!=snr or row['arm_id']!='sbl-s0.5'
                    or row['source_sha256']!=segment['source_sha256']
                    or row['config_sha256']!=segment['config_sha256']
                    or row['protocol_sha256']!=plan['protocol_sha256'] or row['failure'] is not None
                    or set(row['input_hashes'])!={'y','H','info','coded','noise','pilot','data'}):
                raise ValueError('cached baseline frame provenance mismatch')
            snapshot=row['snapshot']
            with Path(snapshot['path']).open('rb') as stream:
                digest=hashlib.sha256()
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
            if digest.hexdigest()!=snapshot['sha256']:
                raise ValueError('cached baseline snapshot hash mismatch')
            cache[block]=row['input_hashes']
    if set(cache)!=set(range(start,stop)):
        raise ValueError('cached baseline does not cover complete anchor')
    return decision,cache


def validate_physical_pair(frame, cache):
    if frame.metadata['input_hashes']!=cache[frame.metadata['block']]:
        raise ValueError('physical development input hashes differ from cached baseline')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--split',choices=('engineering','design','mechanism'),required=True)
    parser.add_argument('--start',type=int,required=True)
    parser.add_argument('--stop',type=int,required=True)
    parser.add_argument('--snr',type=float,required=True)
    parser.add_argument('--recipes',required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--device',default='cuda')
    parser.add_argument('--deadline-unix',type=float,required=True)
    parser.add_argument('--max-full-calls',type=int,required=True)
    parser.add_argument('--ledger',type=Path,required=True)
    parser.add_argument('--physical-registry',type=Path)
    parser.add_argument('--physical-admission',type=Path)
    parser.add_argument('--physical-admission-sha256')
    parser.add_argument('--cancellation-registry',type=Path)
    parser.add_argument('--cancellation-admission',type=Path)
    parser.add_argument('--cancellation-admission-sha256')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();cpu_started=time.process_time()
    calls=0;completed=0;peak=0;records=[];active=None;reserved=False;status='failed'
    try:
        if not math.isfinite(args.deadline_unix) or args.deadline_unix<=time.time():
            raise ValueError('deadline must be finite and in the future')
        if args.start<0 or args.stop<=args.start or args.max_full_calls<1:
            raise ValueError('invalid block range/call budget')
        def deadline(signum,frame):
            raise TimeoutError('registered wall deadline reached')
        signal.signal(signal.SIGALRM,deadline)
        signal.setitimer(signal.ITIMER_REAL,args.deadline_unix-time.time())
        protocol=json.loads(args.protocol.read_text())
        cap_key={'engineering':'engineering_full','design':'baseline_full','mechanism':'mechanism_full'}[args.split]
        physical_registry=None
        if args.physical_registry is not None:
            if args.cancellation_registry is not None:
                raise ValueError('cannot combine two separately frozen routes')
            if args.split=='design':
                physical_registry=json.loads(args.physical_registry.read_text())
                cap_key='prototype_full'
            else:
                physical_registry=physical_engineering_registry(args.physical_registry,args.split,
                    args.start,args.stop,args.snr,args.max_full_calls)
        elif args.physical_admission is not None or args.physical_admission_sha256:
            raise ValueError('physical admission requires physical registry')
        cancellation_registry=None
        if args.cancellation_registry is not None:
            if hashlib.sha256(args.cancellation_registry.read_bytes()).hexdigest()!='dbb3b9dd675359772a3b45b50e21927c628175f64ab23a8d380d83ed14e01b3a':
                raise ValueError('cancellation registry differs from frozen contract')
            cancellation_registry=json.loads(args.cancellation_registry.read_text())
            if args.split not in ('engineering','design') or args.snr!=8:
                raise ValueError('cancellation only admits engineering/design at8dB')
            if cancellation_registry['arms']!=['cancel-scalar','cancel-diagonal','cancel-lowrank']:
                raise ValueError('cancellation arms differ from preregistration')
            if args.split=='design':cap_key='prototype_full'
            if args.max_full_calls>(20 if args.split=='engineering' else 576):
                raise ValueError('cancellation stage call cap exceeded')
            if args.split=='engineering' and not (17<=args.start<args.stop<=22):
                raise ValueError('cancellation engineering requires preregistered blocks17..21')
        if args.max_full_calls>protocol['budget']['calls_caps'][cap_key]:
            raise ValueError('per-run reservation exceeds frozen stage full-call cap')
        recipe_map={r['id']:r for r in protocol['design']['recipes']}
        if cancellation_registry is not None:
            recipe_map={r['id']:r for r in protocol['design']['recipes'] if r['id']=='sbl-s0.5'}
            recipe_map.update({f'cancel-{mode}':dict(id=f'cancel-{mode}',family='sbl',parameter=.001,terminal_scale=.5,cancellation_mode=mode) for mode in ('scalar','diagonal','lowrank')})
        if physical_registry is not None:
            recipe_map={arm:dict(id=arm,family='sbl',parameter=.001,terminal_scale=.5,physical_arm=arm)
                        for arm in physical_registry['arms']}
        chosen=list(recipe_map) if args.recipes=='all' else args.recipes.split(',')
        if cancellation_registry is not None and args.split=='design' and 'sbl-s0.5' in chosen:
            raise ValueError('design baseline uses existing cache, not extra full repetitions')
        if not chosen or len(set(chosen))!=len(chosen) or any(r not in recipe_map for r in chosen):
            raise ValueError('only unique preregistered recipes may run')
        admission=None
        physical_admission=None;physical_cache=None
        if physical_registry is not None and args.split=='design':
            physical_admission,physical_cache=validate_physical_admission(args.physical_admission,
                args.physical_admission_sha256,args.physical_registry,args.protocol,args.ledger,
                chosen,args.start,args.stop,args.snr,args.max_full_calls)
        if cancellation_registry is not None and args.split=='design':
            admission=validate_cancellation_admission(args.cancellation_admission,
                args.cancellation_admission_sha256,args.cancellation_registry,args.protocol,
                args.ledger,chosen)
        if (args.stop-args.start)*len(chosen)>args.max_full_calls:
            raise ValueError('requested calls exceed max-full-calls')
        if args.ledger.resolve()!=(args.out.parent/'resource-ledger.json').resolve():
            raise ValueError('all sibling runs must use their shared campaign ledger')
        cores=len(os.sched_getaffinity(0))
        if cores>4:raise ValueError('run requires registered affinity of at most four CPU cores')
        duration=args.deadline_unix-time.time()
        reserve(args.ledger,args.out.name,campaign_id=protocol['campaign_id'],
            protocol_sha256=hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
            cap_key=cap_key,calls=args.max_full_calls,resources=dict(host_seconds=duration,
                gpu_seconds=duration if args.device.startswith('cuda') else 0,
                cpu_core_seconds=duration*cores),
            allocation=({'id':'physical-design-anchor-v1','cap':768} if physical_admission is not None else
                {'id':'physical-engineering-v1','cap':18} if physical_registry is not None else None) if cancellation_registry is None else {
                'id':'classical-cancellation-'+args.split+'-v1',
                'cap':20 if args.split=='engineering' else 576})
        reserved=True
        config={'arguments':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
                'recipes':[recipe_map[r] for r in chosen],'protocol_sha256':hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
                'source_sha256':source_manifest(),'call_budget':args.max_full_calls,
                'retry_policy':'no in-place resume; every rerun uses new output and all started ledgers count'}
        if cancellation_registry is not None:
            config['cancellation_registry_sha256']=hashlib.sha256(args.cancellation_registry.read_bytes()).hexdigest()
            config['cancellation_registry']=cancellation_registry
            config['cancellation_admission']=admission
            config['cancellation_admission_sha256']=args.cancellation_admission_sha256
        if physical_registry is not None:
            config['physical_registry_sha256']=hashlib.sha256(args.physical_registry.read_bytes()).hexdigest()
            config['physical_registry']=physical_registry
            config['physical_admission']=physical_admission
            config['physical_admission_sha256']=args.physical_admission_sha256
        config_hash=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
        publish_json(args.out/'run-contract.json',config)
        device=torch.device(args.device)
        if device.type=='cuda' and not torch.cuda.is_available():
            raise ValueError('requested CUDA unavailable')
        system=_make_config_a(1024,2.,8,10.,4.)
        code=build_code()
        data=CampaignData(args.protocol,code)
        for block in range(args.start,args.stop):data._validate_request(args.split,block,args.snr)
        receiver=ObservedReceiver.build(args.checkpoint,system,code,device=args.device)
        for block in range(args.start,args.stop):
            if time.time()>=args.deadline_unix:raise TimeoutError('deadline before frame generation')
            frame=data.make_frame(system,args.split,block,args.snr)
            if physical_cache is not None:validate_physical_pair(frame,physical_cache)
            order=list(chosen);campaign_rng(args.split,block,'order').shuffle(order)
            paired=[]
            for arm in order:
                if calls>=args.max_full_calls:raise RuntimeError('full-call budget exhausted')
                if time.time()>=args.deadline_unix:raise TimeoutError('deadline before full call')
                recipe=recipe_map[arm];calls+=1
                active={'attempt':calls,'block':block,'arm_id':arm,'started_unix':time.time(),
                        'call_type':'full','input_hashes':frame.metadata['input_hashes']}
                publish_json(args.out/f'call-{calls:06d}-started.json',active)
                if device.type=='cuda':torch.cuda.reset_peak_memory_stats(device)
                c0=time.process_time()
                transform_kwargs={}
                if 'cancellation_mode' in recipe:
                    from afdm_sp_joint_unrolled.direction_cancel_receiver import CancellationTransform
                    transform_kwargs['terminal_transform']=CancellationTransform(system,recipe['cancellation_mode'])
                if 'physical_arm' in recipe:
                    from afdm_sp_joint_unrolled.direction_physical_receiver import PhysicalChannelRefit
                    transform_kwargs['channel_refit']=PhysicalChannelRefit(system,recipe['physical_arm'])
                result=receiver.run(frame.observed,family=recipe['family'],parameter=recipe['parameter'],
                                    terminal_scale=recipe['terminal_scale'],audit=True,**transform_kwargs)
                call_cpu=time.process_time()-c0
                call_peak=int(torch.cuda.max_memory_allocated(device)) if device.type=='cuda' else 0
                peak=max(peak,call_peak)
                audit_started=time.perf_counter();audit_cpu_started=time.process_time()
                row=frame_record(args.out.name,frame,result,recipe,system,args.out,device,call_cpu,call_peak,config_hash)
                row['offline_audit_seconds']=time.perf_counter()-audit_started
                row['offline_audit_cpu_seconds']=time.process_time()-audit_cpu_started
                row['budget']={'attempt':calls,'max_full_calls':args.max_full_calls,'deadline_unix':args.deadline_unix}
                destination=args.out/f'frame-{block:06d}-{arm}.json'
                publish_json(destination,row)
                publish_json(args.out/f'call-{calls:06d}-completed.json',dict(active,record=str(destination),
                    record_sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
                completed+=1;records.append(str(destination));paired.append(row);active=None
                del result
            validate_pair(paired)
        publish_json(args.out/'complete.json',{'status':'complete','calls_attempted':calls,
            'calls_completed':completed,'CPU_seconds':time.process_time()-cpu_started,
            'wall_seconds':time.monotonic()-started,'peak_gpu_bytes':peak,'records':records,
            'record_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in records},
            'source_sha256':config['source_sha256'],'config_sha256':config_hash,
            'protocol_sha256':data.protocol_sha256,'timing_scope':'instrumented diagnostic, not A2 gate',
            'command':[sys.executable]+sys.argv})
        status='complete'
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        publish_json(args.out/'failure.json',{'status':'failed','exception':type(exc).__name__,
            'message':str(exc),'traceback':traceback.format_exc(),'calls_attempted':calls,
            'calls_completed':completed,'active_attempt':active,'completed_records':records,
            'CPU_seconds':time.process_time()-cpu_started,'wall_seconds':time.monotonic()-started,
            'peak_gpu_bytes':peak,'command':[sys.executable]+sys.argv})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        if reserved:
            wall=time.monotonic()-started
            settle(args.ledger,args.out.name,calls=calls,resources=dict(host_seconds=wall,
                gpu_seconds=wall if args.device.startswith('cuda') else 0,
                cpu_core_seconds=time.process_time()-cpu_started),
                evidence=str(args.out/('complete.json' if status=='complete' else 'failure.json')),
                status=status)


if __name__=='__main__':
    main()
