"""COST-01 paired A2/B0 microcost in one legacy harness, not COST-02 evidence."""
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

START_WALL=time.monotonic()
START_CPU=time.process_time()
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[_key]='1'

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver, load_prior, run_frame
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch
from afdm_sp_joint_unrolled.direction_data import CampaignData, campaign_rng, source_manifest
from afdm_sp_joint_unrolled.direction_receiver import CHECKPOINT_HASH, terminal_decode
from afdm_sp_joint_unrolled.direction_run import json_value
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.v3_initial import InitialEstimator


def summary(values):
    a=np.asarray(values,dtype=float)
    if a.ndim!=1 or not len(a) or not np.isfinite(a).all() or np.any(a<0):
        raise ValueError('finite nonnegative microcost samples required')
    return {'n':len(a),'raw':a.tolist(),'mean':float(a.mean()),
            'p95':float(np.quantile(a,.95)),
            'scope':'microcost descriptive quantile; not formal deployment tail estimate'}


def legacy_frame(frame):
    """Truth needed ONLY for the old harness evaluator; deployment arm has no oracle."""
    meta=frame.metadata
    return dict(frame._truth,y=frame.observed['y'],pilot=frame.observed['pilot'],
        sigma2=frame.observed['sigma2'],channel_seed=meta['channel_seed'],
        uncoded=False,split_id=90,dataset='engineering',
        order_seed_words=meta['rng_words']['order'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','checkpoint','prior','ledger','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--deadline-unix',type=float,required=True)
    parser.add_argument('--pairs',type=int,choices=(6,8),default=6)
    parser.add_argument('--device',choices=('cuda',),default='cuda')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    wall0=START_WALL;cpu0=START_CPU
    calls={'engineering_full':0,'engineering_terminal':0,'structure_CE':0}
    reserved=False;active=None;samples=[];peak=0;init={}
    # Imports are explicit: an older single-key ledger cannot silently bypass cost accounting.
    from afdm_sp_joint_unrolled.direction_budget import reserve_many,settle_many
    def resources():
        elapsed=time.monotonic()-wall0
        return {'host_seconds':elapsed,'gpu_seconds':elapsed,'cpu_core_seconds':time.process_time()-cpu0}
    def begin(key,label,block):
        nonlocal active
        if time.time()>=args.deadline_unix:raise TimeoutError('microcost deadline before call')
        if calls[key]>=limits[key]:raise RuntimeError('reserved microcost call cap exhausted')
        calls[key]+=1
        active={'kind':key,'label':label,'block':block,'ordinal':calls[key],
                'started_unix':time.time(),'purpose':'engineering_cost_probe'}
        publish_json(args.out/f"started-{key}-{calls[key]:03d}.json",active)
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        return time.perf_counter(),time.process_time()
    def finish(start,record):
        nonlocal active,peak
        torch.cuda.synchronize()
        current=int(torch.cuda.max_memory_allocated());peak=max(peak,current)
        record.update(attempt=active,external_seconds=time.perf_counter()-start[0],
                      CPU_seconds=time.process_time()-start[1],peak_gpu_bytes=current)
        record=json_value(record)
        publish_json(args.out/f"sample-{active['kind']}-{active['ordinal']:03d}.json",record)
        samples.append(record);active=None
    try:
        duration=args.deadline_unix-time.time()
        if not math.isfinite(duration) or duration<=0:raise ValueError('future finite deadline required')
        cores=sorted(os.sched_getaffinity(0))
        if len(cores)!=4:raise ValueError('microcost requires exactly four CPU affinity cores')
        if args.ledger.resolve()!=(args.out.parent/'resource-ledger.json').resolve():
            raise ValueError('shared sibling campaign ledger required')
        if not torch.cuda.is_available():raise ValueError('CUDA required; no fallback')
        torch.set_num_threads(1)
        protocol=json.loads(args.protocol.read_text())
        phash=hashlib.sha256(args.protocol.read_bytes()).hexdigest()
        limits={'engineering_full':2*(args.pairs+2),
                'engineering_terminal':args.pairs,'structure_CE':args.pairs}
        reserve_many(args.ledger,args.out.name,campaign_id=protocol['campaign_id'],
            protocol_sha256=phash,calls=limits,resources={'host_seconds':duration,
                'gpu_seconds':duration,'cpu_core_seconds':duration*4})
        reserved=True
        def timeout(signum,frame):raise TimeoutError('registered microcost deadline reached')
        signal.signal(signal.SIGALRM,timeout)
        signal.setitimer(signal.ITIMER_REAL,max(.001,args.deadline_unix-time.time()))
        if hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()!=CHECKPOINT_HASH:
            raise ValueError('checkpoint mismatch')
        if hashlib.sha256(args.prior.read_bytes()).hexdigest()!='74f23844a95ea36ea90490f7aa5fca76bd14ff8a97f954f4387a4e85c852444e':
            raise ValueError('original A2 prior400 hash mismatch')
        contract={'campaign_id':protocol['campaign_id'],'protocol_sha256':phash,
            'source_sha256':source_manifest(),'prior_sha256':hashlib.sha256(args.prior.read_bytes()).hexdigest(),
            'checkpoint_sha256':CHECKPOINT_HASH,'affinity':cores,'device':'cuda',
            'warmup_blocks':[0,1],'measurement_blocks':list(range(2,args.pairs+2)),
            'snr':8,'calls_reserved':limits,'purpose':'engineering_cost_probe',
            'CE_budget_source':'deducted from structure_CE total; not a structural experiment',
            'A2':'legacy run_frame baseline, achievable prior400, M96, two rounds, direct40',
            'B0':'legacy run_frame a0 + InitialEstimator(b0), direct40, terminal scale1',
            'timer_scope':'same legacy device-ready-y through terminal BP/LLR/LDPC and information-error comparison; graph and terminal-observer copies included',
            'excluded':'host sensing/scorer prep and transfers outside receiver_seconds; external_seconds measures whole legacy call including them and evaluator/audit',
            'audit_cost':'All reported timings are instrumented; graph snapshots and terminal copies are inside full timing. c_T/c_E external timing also includes output hashing/transfer.',
            'wrapper_difference':'ObservedReceiver uses direct terminal_decode and no truth evaluator; not used for paired comparison',
            'not_COST02':'2 warmups and6/8 pairs do not meet10 warmups/1000 samples/10 blocks formal gate',
            'command':[sys.executable]+sys.argv}
        publish_json(args.out/'contract.json',contract)
        t=time.perf_counter();system=_make_config_a(1024,2.,8,10.,4.)
        init['system_seconds']=time.perf_counter()-t
        t=time.perf_counter();code=build_code();data=CampaignData(args.protocol,code)
        init['code_data_seconds']=time.perf_counter()-t
        t=time.perf_counter();model=build_receiver(args.checkpoint,system,1024,'cuda',receiver_shell='direct40',active_cap=40)
        torch.cuda.synchronize();init['model_seconds']=time.perf_counter()-t
        t=time.perf_counter();prior,prior_meta=load_prior(args.prior,8,1024,l_max=102,k_max=2,
            nomination_cap=40,receiver_shell='direct40')
        init['prior_seconds']=time.perf_counter()-t
        publish_json(args.out/'initialization.json',dict(init,prior_metadata=json_value(prior_meta)))
        for block in range(args.pairs+2):
            if time.time()>=args.deadline_unix:raise TimeoutError('deadline before generator')
            t=time.perf_counter();frame=data.make_frame(system,'engineering',block,8)
            generation=time.perf_counter()-t
            paired=legacy_frame(frame)
            order=['A2','B0'];campaign_rng('engineering',block,'order').shuffle(order)
            terminal_state=None
            for name in order:
                arm='baseline' if name=='A2' else 'a0'
                captured=[]
                start=begin('engineering_full',name,block)
                raw=run_frame(model,system,code,paired,prior,[arm],0,block,8,
                    observe=True,active_cap=40,receiver_shell='direct40',graph_observe=True,
                    initial_estimator=InitialEstimator('b0') if name=='B0' else None,
                    terminal_observer=lambda state:captured.append(state))
                result=raw['arms'][arm]
                if raw['input_hashes']!={k:frame.metadata['input_hashes'][k] for k in raw['input_hashes']}:
                    raise AssertionError('A2/B0 frame pairing failed')
                if result['oracle'] or len(captured)!=1:
                    raise AssertionError('microcost needs deployable arm and one terminal state')
                if name=='B0':terminal_state=captured[0]
                finish(start,{'name':name,'warmup':block<2,'input_hashes':raw['input_hashes'],
                    'generation_seconds':generation,'receiver_seconds':result['receiver_seconds'],
                    'scorer_preparation_seconds':result['shared_scorer_preparation_seconds'],
                    'receiver_plus_preparation_seconds':result['standalone_seconds_estimate'],
                    'capacity_trace':result['capacity_trace'],'graph':result['bp_graphs'],
                    'legacy_raw':raw,'K_final':len(result['capacity_trace'][-1]['atom_ids'])})
            if block<2:continue
            if terminal_state is None:raise AssertionError('missing B0 terminal snapshot')
            s=terminal_state
            start=begin('engineering_terminal','c_T',block)
            terminal=terminal_decode(s['y']-s['H']@s['pilot'],s['H'],s['sigma2'],
                                     s['constellation'],code,device='cuda',audit=True)
            finish(start,{'name':'c_T','warmup':False,'sigma2':s['sigma2'],
                'H_sha256':array_hash(s['H']),'decoded_sha256':array_hash(terminal['decoded']),
                'graphs':terminal['graphs'],'input_hashes':frame.metadata['input_hashes'],
                'scope':'terminal cancellation/BP/LLR/LDPC; device transfer inside actual terminal API'})
            t=time.perf_counter()
            cfg=model.cfg
            y=torch.tensor(frame.observed['y'],dtype=cfg.dtype,device='cuda')
            p=torch.tensor(frame.observed['pilot'],dtype=cfg.dtype,device='cuda')
            sigma=torch.tensor(frame.observed['sigma2'],dtype=cfg.rdtype,device='cuda')
            Phi=construct_sensing_matrix_torch(1024,p,cfg.c1,cfg.c2,102,2,cdtype=cfg.dtype)
            torch.cuda.synchronize();ce_prepare=time.perf_counter()-t
            estimator=InitialEstimator('b0')
            start=begin('structure_CE','c_E',block)
            with torch.no_grad():h,support=estimator(y,Phi,40,sigma)
            finish(start,{'name':'c_E','warmup':False,'purpose':'engineering_cost_probe',
                'preparation_seconds':ce_prepare,'K':len(support),'support':support,
                'coefficient_sha256':array_hash(h.detach().cpu().numpy()),
                'estimator':estimator.record,'input_hashes':frame.metadata['input_hashes'],
                'scope':'observed-only OMP40+LS, not full channel outer loop or physical structural fit'})
        selected=[s for s in samples if not s['warmup']]
        totals={name:summary([s['receiver_seconds'] if name in ('A2','B0') else s['external_seconds']
                             for s in selected if s['name']==name]) for name in ('A2','B0','c_T','c_E')}
        prep={name:summary([s['receiver_plus_preparation_seconds'] for s in selected if s['name']==name])
              for name in ('A2','B0')}
        result={'status':'complete','calls':calls,'initialization':init,'device_ready_cost':totals,
            'full_including_host_scorer_preparation':prep,'peak_gpu_bytes':peak,
            'resources':resources(),'source_sha256':contract['source_sha256'],
            'prior_sha256':contract['prior_sha256'],'protocol_sha256':phash,
            'sample_files':[str(p) for p in sorted(args.out.glob('sample-*.json'))],
            'interpretation':'COST-01 microcost only; no G2/COST-02 pass or performance conclusion'}
        publish_json(args.out/'complete.json',result)
        settle_many(args.ledger,args.out.name,calls=calls,resources=resources(),
                    evidence=str(args.out/'complete.json'),status='complete')
        reserved=False
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        failure={'status':'failed','exception':type(exc).__name__,'message':str(exc),
                 'traceback':traceback.format_exc(),'calls':calls,'active_attempt':active,
                 'resources':resources(),'peak_gpu_bytes':peak}
        publish_json(args.out/'failure.json',failure)
        if reserved:
            settle_many(args.ledger,args.out.name,calls=calls,resources=resources(),
                        evidence=str(args.out/'failure.json'),status='failed')
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    main()
