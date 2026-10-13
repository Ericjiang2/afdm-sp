#!/usr/bin/env python3
"""Two full calls on engineering block0@8; fixed A2 adapter equivalence gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import traceback
from unittest.mock import patch

sys.dont_write_bytecode=True

for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'

import numpy as np
import torch
from afdm_sp_joint_unrolled import budgeted_support_eval as legacy
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.direction_receiver import CHECKPOINT_HASH
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.supplement_data import SupplementData, CAMPAIGN_ID
from afdm_sp_joint_unrolled.supplement_profile import (
    A2Model, A2Receiver, A2_SOURCE, PRIOR_HASH, reserve_profile, assert_content_unchanged)
from afdm_sp_joint_unrolled.supplement_run import sha, sources, array_hash, json_value


def compare(old,new):
    rows={}
    for key in ('H','sigma2','llr'):
        a,b=np.asarray(old[key]),np.asarray(new[key])
        if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('invalid paired shape or finite state: '+key)
        absolute=float(np.linalg.norm((a-b).ravel()))
        denominator=float(np.linalg.norm(a.ravel()))
        # Relative L2 with no absolute floor. Zero reference requires exact zero error.
        relative=absolute/denominator if denominator else (0. if absolute==0 else None)
        rows[key]=dict(old_sha256=array_hash(a),new_sha256=array_hash(b),
            absolute_l2=absolute,reference_l2=denominator,relative_l2=relative,
            max_absolute=float(np.max(np.abs(a-b))),
            passed=relative is not None and relative<=1e-6)
    a,b=np.asarray(old['decoded']),np.asarray(new['decoded'])
    if a.ndim!=1 or a.shape!=b.shape or any(not np.isin(v,(0,1)).all() for v in (a,b)):
        raise ValueError('decoded shape/binary contract failed')
    ah,bh=array_hash(a),array_hash(b)
    rows['decoded']=dict(old_sha256=ah,new_sha256=bh,
        differing_bits=int(np.count_nonzero(a!=b)),passed=np.array_equal(a,b) and ah==bh)
    return dict(status='passed' if all(r['passed'] for r in rows.values()) else 'failed',
        comparisons=rows,tolerance_relative_l2=1e-6,
        decoded_rule='identical shape, every bit and dtype/shape/content hash',
        raw_error_rule='not compared: legacy uses outer x_soft; adapter uses terminal hard decisions')


def snapshot(path,old,new):
    fd,temporary=tempfile.mkstemp(prefix='.a2-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            np.savez_compressed(stream,**{side+'_'+key:np.asarray(value[key])
                for side,value in [('old',old),('new',new)] for key in ('H','sigma2','llr','decoded')})
            stream.flush();os.fsync(stream.fileno())
        os.link(temporary,path)
    finally:
        os.unlink(temporary)
    return dict(path=str(path.resolve()),sha256=sha(path),
        md5=hashlib.md5(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,
        transfer_policy='no automatic transfer; artifacts larger than10MB remain at this path')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','checkpoint','prior','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--deadline-unix',type=float,required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    tempfile.tempdir=str(args.out.resolve())
    os.environ['TMPDIR']=str(args.out.resolve())
    counts=dict(F=0,T=0,E=0);active=None;completed=[]
    previous=signal.getsignal(signal.SIGALRM)
    started=time.perf_counter();cpu0=time.process_time()
    command=[sys.executable,*sys.argv]
    try:
        if not math.isfinite(args.deadline_unix) or args.deadline_unix<=time.time():
            raise ValueError('future finite deadline required')
        def timeout(_signal,_frame):raise TimeoutError('A2 equivalence deadline')
        signal.signal(signal.SIGALRM,timeout)
        signal.setitimer(signal.ITIMER_REAL,args.deadline_unix-time.time())
        if not torch.cuda.is_available():raise ValueError('CUDA required; no fallback')
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        torch.cuda.set_per_process_memory_fraction(.25,0)
        if sha(args.checkpoint)!=CHECKPOINT_HASH or sha(args.prior)!=PRIOR_HASH:
            raise ValueError('frozen A2 checkpoint/prior mismatch')
        contract=dict(campaign_id=CAMPAIGN_ID,split='engineering',scenario='G0',block=0,snr=8,
            source_sha256=sources(),script_sha256=sha(__file__),protocol_sha256=sha(args.protocol),
            checkpoint_sha256=sha(args.checkpoint),prior_sha256=sha(args.prior),A2_source=A2_SOURCE,
            calls_reserved=dict(F=2,T=0,E=0),max_full_calls=2,deadline_unix=args.deadline_unix,
            device='cuda:0',gpu_memory_fraction=.25,threads=1,command=command,
            tolerance={'H_relative_l2':1e-6,'sigma2_relative_l2':1e-6,'llr_relative_l2':1e-6,
                       'decoded':'every bit and hash identical','zero_reference':'absolute error must be zero'},
            scope='A2 legacy versus observed adapter on one paired engineering frame; not COST02',
            truth_boundary='legacy run_frame evaluator only; active_cap40/direct40 fixes receiver capacity; adapter gets observed mapping only',
            raw_errors='not compared: outer x_soft versus terminal hard differ in definition')
        (args.out/'code-cache').mkdir()
        code=build_code(cache_dir=args.out/'code-cache')
        contract['code_sha256']={k:array_hash(code[k]) for k in ('G','H')}
        contract['config_sha256']=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
        contract['ledger']=reserve_profile(args.out,contract)
        publish_json(args.out/'contract.json',contract)
        def unchanged():
            assert_content_unchanged(args,contract)
            if sha(__file__)!=contract['script_sha256']:raise ValueError('script changed during check')
        system=_make_config_a(1024,2.,8,10.,4.)
        data=SupplementData(args.protocol,code)
        active=dict(kind='generation',block=0,snr=8,split='engineering')
        publish_json(args.out/'generation-started.json',active)
        unchanged()
        frame=data.make_frame(system,'engineering',0,8)
        unchanged()
        publish_json(args.out/'input.json',json_value(frame.metadata))
        prior,_=legacy.load_prior(args.prior,8,1024,l_max=102,k_max=2,
                                  nomination_cap=40,receiver_shell='direct40')
        def call(label,fn):
            nonlocal active
            unchanged()
            if counts['F']>=2 or time.time()>=args.deadline_unix:
                raise RuntimeError('2F budget/deadline exhausted')
            counts['F']+=1
            active=dict(kind='F',label=label,ordinal=counts['F'],block=0,
                        input_hashes=frame.metadata['input_hashes'])
            publish_json(args.out/f'started-{counts["F"]}.json',active)
            torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
            w,c=time.perf_counter(),time.process_time()
            value=fn()
            torch.cuda.synchronize()
            timing=dict(seconds=time.perf_counter()-w,CPU_seconds=time.process_time()-c,
                        peak_gpu_bytes=torch.cuda.max_memory_allocated())
            unchanged()
            publish_json(args.out/f'completed-{counts["F"]}.json',dict(active,**timing))
            completed.append(label);active=None
            return value
        model=legacy.build_receiver(args.checkpoint,system,1024,'cuda',receiver_shell='direct40',active_cap=40)
        captured={}
        original_demap,original_decode=legacy.demap_llr,legacy.decode_llr
        def demap(*a,**kw):
            value=original_demap(*a,**kw);captured['llr']=np.array(value,copy=True);return value
        def decode(*a,**kw):
            value=original_decode(*a,**kw);captured['decoded']=np.array(value[0],copy=True);return value
        def old_call():
            paired=dict(frame._truth,y=frame.observed['y'],pilot=frame.observed['pilot'],
                sigma2=frame.observed['sigma2'],channel_seed=frame.metadata['channel_seed'],
                uncoded=False,split_id=90,dataset='engineering',order_seed_words=frame.metadata['rng_words']['order'])
            terminals=[]
            with patch.object(legacy,'demap_llr',demap),patch.object(legacy,'decode_llr',decode):
                raw=legacy.run_frame(model,system,code,paired,prior,['baseline'],0,0,8,
                    observe=True,active_cap=40,receiver_shell='direct40',graph_observe=True,
                    terminal_observer=terminals.append)
            if len(terminals)!=1 or raw['arms']['baseline']['oracle']:
                raise AssertionError('legacy arm/terminal boundary violated')
            if raw['input_hashes']!={k:frame.metadata['input_hashes'][k] for k in raw['input_hashes']}:
                raise AssertionError('legacy exogenous pairing mismatch')
            captured.update(H=terminals[0]['H'],sigma2=terminals[0]['sigma2'])
            publish_json(args.out/'legacy-record.json',json_value(raw))
            return dict(captured)
        old=call('legacy-baseline',old_call)
        # Fresh checkpoint-loaded model prevents previous mutable hook/state carryover.
        del model
        model=legacy.build_receiver(args.checkpoint,system,1024,'cuda',receiver_shell='direct40',active_cap=40)
        adapter=A2Receiver(A2Model(model,system,prior),code)
        new=call('observed-A2',lambda:adapter.run(frame.observed,family='b0',parameter=None,
                                               terminal_scale=1.,audit=True))
        new_state={k:new[k] for k in ('H','llr','decoded')};new_state['sigma2']=new['sigma2_terminal']
        evidence=snapshot(args.out/'paired-terminal.npz',old,new_state)
        result=compare(old,new_state)
        result.update(evidence=evidence,config_sha256=contract['config_sha256'],counts=counts)
        publish_json(args.out/'comparison.json',json_value(result))
        if result['status']!='passed':raise AssertionError('fixed A2 equivalence tolerance/decoded gate failed')
        unchanged();signal.setitimer(signal.ITIMER_REAL,0)
        publish_json(args.out/'complete.json',dict(status='complete',exitcode=0,counts=counts,
            comparison_sha256=sha(args.out/'comparison.json'),config_sha256=contract['config_sha256'],
            command=command,wall_seconds=time.perf_counter()-started,CPU_seconds=time.process_time()-cpu0))
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        publish_json(args.out/'failure.json',dict(status='failed',exitcode=130 if isinstance(exc,KeyboardInterrupt) else 1,
            exception=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),
            counts=counts,active_attempt=active,completed=completed,command=command))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)


if __name__=='__main__':
    sys.exit(main())
