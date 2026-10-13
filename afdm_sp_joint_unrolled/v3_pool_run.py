"""48-frame B0 gap capture and read-only t0/t3/t6 candidate diagnostics."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame,build_receiver,run_frame
from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch,residual_data_covariance,reconstruct_H_torch
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.projected_gls import projected_add_statistics
from afdm_sp_joint_unrolled.representation_ledger import merged_truth_ledger
from afdm_sp_joint_unrolled.v3_initial import InitialEstimator


def shadow_state(state,pilot,cfg,truth,fixed_missing):
    y=state['y'];support=(state['support_delays']*5+state['support_dopplers']+2).tolist()
    phi=construct_sensing_matrix_torch(cfg.N,pilot+state['mu'],cfg.c1,cfg.c2,102,2,cdtype=y.dtype)
    if 'A' in state and not torch.allclose(phi[:,support],state['A'],rtol=1e-5,atol=1e-6):
        raise ValueError('shadow dictionary differs from actual DA-LS input')
    A=phi[:,support]
    gains=torch.linalg.lstsq(A,y[:,None]).solution.squeeze(1) if support else y[:0]
    residual=y-A@gains
    raw=(phi.mH@residual).abs().square()/phi.abs().square().sum(0)
    raw[support]=-torch.inf
    nominations=torch.argsort(raw,descending=True,stable=True)[:96].tolist()
    C=residual_data_covariance(state['H'],state['finite_variance'],state['sigma2'])
    scores=projected_add_statistics(y,phi,C,support,nominations)
    rows=scores['candidates'];missing=set(truth)-set(support)
    weights={i:abs(g)**2 for i,g in truth.items()}
    results=[]
    for M in (16,32,96):
        pool=nominations[:M];poolset=set(pool)
        eligible=[r for r in rows[:M] if r['accepted']]
        ranked=sorted(eligible,key=lambda r:-float(r['D']))
        top=[r['id'] for r in ranked[:4]]
        def measure(target):
            energy=sum(weights[i] for i in target)
            return dict(missing_count=len(target),missing_weight=energy,
                        recall_count=len(target&poolset),recall_weight=sum(weights[i] for i in target&poolset),
                        top4_hits=len(target&set(top)),top4_count=len(top),
                        random_pool_prevalence=len(target&poolset)/M,
                        weighted_recall=sum(weights[i] for i in target&poolset)/energy if energy else None)
        results.append(dict(M=M,pool=pool,top4=top,valid_current=scores['valid_current'],
            rank=scores['rank'],current=measure(missing),fixed_t0=measure(fixed_missing),
            scorer='fixed-state projected GLS D; no truth used for ranking',
            candidates=[dict(id=r['id'],eligible=r['accepted'],D=float(r['D']) if r['accepted'] else None,
                             missing=r['id'] in missing) for r in rows[:M]]))
    return dict(outer=state['outer_iter'],support=support,views=results,full_scan_columns=phi.shape[1],
                nomination='normalized matched filter on common OLS residual',covariance='working diagonal finite variance',
                truth_scope='offline in-domain merged atoms only; out-of-domain representation separate')


def run(args):
    if args.replicate not in (0,1,2):raise ValueError('only registered 48 B0 development frames')
    args.out.mkdir(parents=True,exist_ok=False)
    system=_make_config_a(1024,2,8,10,4);code=build_code(2048,d_v=3,d_c=6,seed=20260726)
    model=build_receiver(args.checkpoint,system,1024,'cuda',receiver_shell='direct40',active_cap=40)
    cfg=model.cfg;started=time.time()
    for index in range(16):
        frame=make_frame(system,code,args.replicate,index,8.,split=1)
        estimator=InitialEstimator('b0');states=[]
        def capture(state):
            if state['outer_iter'] in (3,6):states.append(state)
        record=run_frame(model,system,code,frame,None,['a0'],args.replicate,index,8.,active_cap=40,
                         receiver_shell='direct40',initial_estimator=estimator,dals_state_observer=capture)
        if [s['outer_iter'] for s in states]!=[3,6]:raise ValueError('B0 stages missing')
        support=estimator.record['support'];h=torch.as_tensor(estimator.coefficients,dtype=cfg.dtype,device='cuda')
        dl=torch.tensor([i//5 for i in support],device='cuda');dk=torch.tensor([i%5-2 for i in support],device='cuda')
        H0=reconstruct_H_torch(1024,dl,dk,h[support],cfg.c1,cfg.c2,2,cdtype=cfg.dtype)
        states.insert(0,dict(outer_iter=0,y=torch.as_tensor(frame['y'],dtype=cfg.dtype,device='cuda'),
            mu=torch.zeros(1024,dtype=cfg.dtype,device='cuda'),H=H0,finite_variance=torch.full((1024,),.5,device='cuda'),
            sigma2=torch.tensor(frame['sigma2'],device='cuda'),support_delays=dl,support_dopplers=dk))
        entries=merged_truth_ledger(frame['params'],2)['entries']
        truth={e['column']:complex(e['real'],e['imag']) for e in entries
               if e['column'] is not None and e['delay']<=102 and complex(e['real'],e['imag'])!=0}
        fixed=set(truth)-set(support);pilot=torch.as_tensor(frame['pilot'],dtype=cfg.dtype,device='cuda')
        with (args.out/f'states-{index:02d}.pt').open('xb') as stream:
            torch.save(dict(states=states,input_hashes=record['input_hashes']),stream)
        t=time.perf_counter();views=[shadow_state(s,pilot,cfg,truth,fixed) for s in states]
        torch.cuda.synchronize()
        record.update(pool=views,shadow_seconds=time.perf_counter()-t)
        publish_json(args.out/f'frame-{index:02d}.json',record)
        print(json.dumps(dict(replicate=args.replicate,frame=index,elapsed=time.time()-started)),flush=True)
    publish_json(args.out/'complete.json',dict(full_receiver_calls=16,views=144,complete=True,wall_seconds=time.time()-started))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replicate',type=int,required=True)
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    run(p.parse_args())
