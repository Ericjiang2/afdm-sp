"""Development-only full coded receiver runner for frozen simple baselines."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame,build_receiver,run_frame
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.v3_initial import InitialEstimator
from afdm_sp_joint_unrolled.v3_metrics import initial_error
from afdm_sp_joint_unrolled.v3_holdout import make_holdout_frame


def run(args):
    holdout=args.dataset=='holdout'
    observing=holdout or args.observe_states
    if args.replicate not in ((0,1,2) if holdout else (30,31,32)) or not 0<=args.start<args.stop<=(128 if holdout else 64):
        raise ValueError('unregistered dataset identity')
    gate=None
    if holdout:
        if args.freeze is None:raise ValueError('holdout needs completed recipe/identity freeze')
        gate=json.loads(args.freeze.read_text())
        if not gate['sigma_frozen'] or gate['action_included'] or not gate['identity_audit_passed']:
            raise ValueError('four-core holdout freeze gate failed')
        recipe=gate['recipes'][args.family]
        if recipe['parameter']!=args.parameter:raise ValueError('not the frozen family parameter')
    if args.device=='cuda' and not torch.cuda.is_available():
        raise RuntimeError('registered GPU unavailable')
    if args.device=='cpu' and torch.cuda.is_available():
        raise RuntimeError('CPU runner must hide CUDA from legacy final-BP shim')
    estimator=InitialEstimator(args.family,args.parameter)
    args.out.mkdir(parents=True,exist_ok=False)
    system=_make_config_a(1024,2,8,10,4)
    model=build_receiver(args.checkpoint,system,1024,args.device,receiver_shell='direct40',active_cap=40)
    code=build_code(2048,d_v=3,d_c=6,seed=20260726)
    code_hash=hashlib.sha256(code['G'].tobytes()).hexdigest()
    if code_hash!='bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af':
        raise ValueError('frozen actual LDPC generator changed')
    if (system.l_max_cap,system.k_max_cap)!=(102,2):raise ValueError('dictionary changed')
    publish_json(args.out/'contract.json',dict(dataset='D_v3_hold' if holdout else 'D_fit',replicate=args.replicate,start=args.start,stop=args.stop,
      family=args.family,parameter=args.parameter,code_sha256=code_hash,device=args.device,
      checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
      downstream='A0; support repair disabled; actual 10 outer / 20 BP / 50 LDPC',
      initial_scope='observable only; simulation truth restricted to evaluation'))
    started=time.time()
    for index in range(args.start,args.stop):
        frame=(make_holdout_frame(system,code,args.replicate,index) if holdout
               else make_frame(system,code,args.replicate,index,8.,split=2))
        states=[]
        def observe(state):states.append(state)
        terminal={}
        def capture(value):terminal.update(value)
        record=run_frame(model,system,code,frame,None,['a0'],args.replicate,index,8.,
                         active_cap=40,receiver_shell='direct40',initial_estimator=estimator,
                         terminal_observer=capture,graph_observe=True,
                         dals_state_observer=observe if observing else None)
        metric=initial_error(system,frame,estimator.coefficients,estimator.record['support'])
        if holdout:
            expected=gate['inputs'][f'{args.replicate}:{index}']
            if record['input_hashes']!=expected:raise ValueError('holdout input differs from preregistered hashes')
        if observing:
            if [v['outer_iter'] for v in states]!=list(range(1,10)):raise ValueError('incomplete outer observation')
            trace=[]
            for state in states:
                truth=torch.as_tensor(frame['H'],device=state['H'].device,dtype=state['H'].dtype)
                trace.append(dict(outer=state['outer_iter'],sigma2=float(state['sigma2']),
                    H_nmse=float((state['H']-truth).abs().square().sum()/truth.abs().square().sum()),
                    support=(state['support_delays']*5+state['support_dopplers']+2).tolist()))
                if state['outer_iter'] not in (3,6):
                    for key in ('H','A','y'):state.pop(key,None)
            state_path=args.out/f'states-{index:03d}.pt'
            with state_path.open('xb') as stream:
                torch.save(dict(states=states,initial_coefficients=estimator.coefficients,
                    initial_support=estimator.record['support'],input_hashes=record['input_hashes']),stream)
            record.update(outer_trace=trace,state_snapshot=dict(path=str(state_path),sha256=hashlib.sha256(state_path.read_bytes()).hexdigest()))
        snapshot=args.out/f'terminal-{index:03d}.npz'
        # Snapshot is published only once. It is a terminal intervention input,
        # not a new invocation of BP and not an independent receiver result.
        with snapshot.open('xb') as stream:
            np.savez_compressed(stream,H=terminal['H'],sigma2=terminal['sigma2'],
                y=terminal['y'],pilot=terminal['pilot'],constellation=terminal['constellation'],
                info=frame['info'],coded=frame['coded'],H_true=frame['H'])
        record.update(v3_initial=estimator.record,initial_error=metric,
          terminal_snapshot=dict(path=str(snapshot),sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest()),
          family=args.family,parameter=args.parameter,FER=int(record['arms']['a0']['info_errors']>0),
          information_bits=code['k'])
        publish_json(args.out/f'frame-{index:03d}.json',record)
        print(json.dumps(dict(frame=index,FER=record['FER'],initial_K=metric['K'],
            receiver_seconds=record['arms']['a0']['receiver_seconds'],elapsed=time.time()-started)),flush=True)
    publish_json(args.out/'complete.json',dict(full_receiver_calls=args.stop-args.start,
        wall_seconds=time.time()-started,complete=True))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',choices=['fit','holdout'],default='fit')
    p.add_argument('--freeze',type=Path)
    p.add_argument('--observe-states',action='store_true',help='registered development observer parity only')
    p.add_argument('--family',choices=['b0','size','ridge','sbl'],required=True)
    p.add_argument('--parameter',type=float)
    p.add_argument('--replicate',type=int,required=True)
    p.add_argument('--start',type=int,required=True);p.add_argument('--stop',type=int,required=True)
    p.add_argument('--device',choices=['cuda','cpu'],required=True)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    run(p.parse_args())
