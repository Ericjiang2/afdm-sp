"""Bounded initial-only COLOR packets; no BP, no decoder, no test-set access."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch,omp_sparse_torch
from afdm_sp_joint_unrolled.e1_ldpc import build_code,encode,qpsk_map
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.v3_color import augmented_factor,matched_observations
from afdm_sp_joint_unrolled.v3_metrics import initial_error
from afdm_sp_joint_unrolled.v3_protocol import seed_words,color_cells
from afdm_sp_joint_unrolled.v3_initial import InitialEstimator


def run(args):
    if not 0<=args.start<args.stop<= (8 if args.dataset=='color_engineering' else 48):
        raise ValueError('unregistered color channel range')
    args.out.mkdir(parents=True,exist_ok=False)
    system=_make_config_a(1024,2,8,10,4)
    code=build_code(2048,d_v=3,d_c=6,seed=20260726)
    digest=hashlib.sha256(code['G'].tobytes()).hexdigest()
    if digest!='bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af':
        raise ValueError('actual coded generator differs from frozen moment certificate')
    if (system.l_max_cap,system.k_max_cap)!=(102,2):
        raise ValueError('physical dictionary changed')
    pilot=np.sqrt(.5)*system._zc_seq
    pt=torch.as_tensor(pilot,dtype=torch.complex64)
    Phi=construct_sensing_matrix_torch(1024,pt,system.c1,system.c2,102,2,cdtype=torch.complex64)
    started=time.time();completed=0
    recipes=json.loads(args.recipes.read_text())['selected'] if args.recipes else None
    if recipes and args.dataset!='color_repeat':raise ValueError('frozen shadow uses core identities only')
    cells=([dict(arm=arm,capacity=40,power=1.,family=f,parameter=recipes[f]['parameter'])
            for arm in ('A','G','W') for f in ('size','ridge','sbl')] if recipes else color_cells())
    publish_json(args.out/'contract.json',dict(dataset=args.dataset,start=args.start,stop=args.stop,
       repeats=2 if args.dataset=='color_engineering' else 4,code_sha256=digest,
       gaussian='approved augmented real matched R and P',cells=cells,scientific=args.dataset=='color_repeat'))
    for h_index in range(args.start,args.stop):
        stream,index=(0,h_index) if args.dataset=='color_engineering' else (30+h_index//16,h_index%16)
        frame=make_frame(system,code,stream,index,8.,split=2)
        if args.dataset=='color_engineering':
            rng=np.random.default_rng(seed_words(args.dataset,stream,index,'channel'))
            np.random.seed(int(rng.integers(0,2**31)))
            frame['H'],_,frame['params']=system.generate_channel_matrix()
        factor=augmented_factor(frame['H'],code['G'],.5)
        for repetition in range(2 if args.dataset=='color_engineering' else 4):
            rng=lambda component:np.random.default_rng(seed_words(args.dataset,stream,index,component,repetition))
            info=rng('message').integers(0,2,size=code['k']).astype(np.uint8)
            data=np.sqrt(.5)*qpsk_map(encode(code,info))
            noise_rng=rng('noise')
            noise=np.sqrt(10**(-.8)/2)*(noise_rng.normal(size=1024)+1j*noise_rng.normal(size=1024))
            xi=rng('gaussian').normal(size=2048)
            observations={power:matched_observations(frame['H'],pilot,data,noise,xi,factor,power)[0] for power in (1.,.25)}
            order=rng('order').permutation(len(cells))
            for cell_index in order:
                cell=cells[cell_index];y=observations[cell['power']][cell['arm']]
                t=time.perf_counter()
                yt=torch.as_tensor(y,dtype=torch.complex64)
                if recipes:
                    estimator=InitialEstimator(cell['family'],cell['parameter'])
                    h,support=estimator(yt,Phi,40,10**(-.8))
                else:
                    h,support=omp_sparse_torch(yt,Phi,cell['capacity'])
                elapsed=time.perf_counter()-t
                metric=initial_error(system,frame,h.numpy(),support)
                record=dict(stream=stream,frame=index,repetition=repetition,**cell,
                    H_hash=array_hash(frame['H']),pilot_hash=array_hash(pilot),noise_hash=array_hash(noise),
                    data_hash=array_hash(data),gaussian_hash=array_hash(xi),y_hash=array_hash(y),
                    initial_seconds=elapsed,metrics=metric,finite=True)
                publish_json(args.out/f'H{h_index:03d}-r{repetition}-c{cell_index:02d}.json',record)
                completed+=1
            print(json.dumps(dict(channel=h_index,repetition=repetition,completed=completed,elapsed=time.time()-started)),flush=True)
    publish_json(args.out/'complete.json',dict(initial_calls=completed,wall_seconds=time.time()-started,complete=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',choices=['color_engineering','color_repeat'],required=True)
    parser.add_argument('--start',type=int,required=True);parser.add_argument('--stop',type=int,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--recipes',type=Path)
    run(parser.parse_args())
