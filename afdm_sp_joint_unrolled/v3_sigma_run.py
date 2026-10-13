"""Terminal-only sigma intervention on hashed frozen receiver snapshots."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.e1_ldpc import build_code,demap_llr,decode_llr,extract_info
from afdm_sp_joint_unrolled.loop9_cache_features import _fast_bp


def terminal(snapshot,sigma2,code):
    if not np.isfinite(sigma2) or sigma2<=0:raise ValueError('positive variance required')
    started=time.perf_counter()
    _,mu,var=_fast_bp(snapshot['y']-snapshot['H']@snapshot['pilot'],snapshot['H'],sigma2,
                     snapshot['constellation'],n_iter=20,threshold=1e-4,damp=.5,return_soft=True)
    llr=demap_llr(mu,var,np.sqrt(.5/2))
    decoded,ok=decode_llr(code,llr,maxiter=50)
    if not all(np.isfinite(v).all() for v in (mu,var,llr)):raise FloatingPointError('nonfinite terminal result')
    errors=int((extract_info(code,decoded)!=snapshot['info']).sum())
    return dict(info_errors=errors,FER=int(errors>0),decode_ok=bool(ok),
        final_bp_mu_sha256=array_hash(mu),final_bp_var_sha256=array_hash(var),
        final_llr_sha256=array_hash(llr),decoded_bits_sha256=array_hash(decoded),
        final_bit_nll=float(np.logaddexp(0,-(1-2*snapshot['coded'].astype(float))*llr).mean()),
        final_bit_brier=float(np.mean((1/(1+np.exp(llr))-snapshot['coded'])**2)),
        terminal_seconds=time.perf_counter()-started)


def load_snapshot(row):
    p=Path(row['terminal_snapshot']['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest()!=row['terminal_snapshot']['sha256']:
        raise ValueError('snapshot hash changed')
    with np.load(p,allow_pickle=False) as data:
        # H_true is deliberately never loaded by this intervention.
        s={k:data[k] for k in ('H','sigma2','y','pilot','constellation','info','coded')}
    if array_hash(s['H'])!=row['arm']['output_h_sha256']:raise ValueError('H identity changed')
    if float(s['sigma2'])!=row['arm']['sigma2_final']:raise ValueError('reference variance changed')
    for k in ('y','pilot','info','coded'):
        if array_hash(s[k])!=row['input_hashes'][k]:raise ValueError(f'{k} identity changed')
    return s


def run(args):
    holdout=args.dataset=='holdout'
    n=128 if holdout else 64
    if args.replicate not in ((0,1,2) if holdout else (30,31,32)):raise ValueError('unregistered terminal dataset')
    recipes=json.loads(args.recipes.read_text());best=recipes['strongest_simple']
    rows=json.loads(args.rows.read_text())
    selected=[r for r in rows if r['replicate']==args.replicate and
        (r['family']=='b0' or (r['family']==best['family'] and r['parameter']==best['parameter']))]
    if len(selected)!=2*n:raise ValueError('missing paired terminal snapshots')
    args.out.mkdir(parents=True,exist_ok=False)
    code=build_code(2048,d_v=3,d_c=6,seed=20260726)
    if hashlib.sha256(code['G'].tobytes()).hexdigest()!='bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af':raise ValueError('LDPC changed')
    started=time.time();calls=0
    fields=('info_errors','final_bp_mu_sha256','final_bp_var_sha256','final_llr_sha256','decoded_bits_sha256','final_bit_nll','final_bit_brier')
    for index in range(n):
        pair={('b0' if r['family']=='b0' else 'simple'):r for r in selected if r['frame_index']==index}
        if len(pair)!=2 or pair['b0']['input_hashes']!=pair['simple']['input_hashes']:raise ValueError('unpaired input')
        snapshots={k:load_snapshot(v) for k,v in pair.items()};results=[]
        for family in ('b0','simple'):
            row=pair[family];s=snapshots[family];reference=float(s['sigma2'])
            # Original outputs remain audit references. Every c=1 is replayed
            # because CUDA scatter reductions need not be bitwise repeatable.
            # No tolerance is used to turn unequal output hashes into matches.
            cache={}
            cells=[('own',c,reference*c) for c in (.5,1.,2.)]
            cells.append(('cross',None,float(snapshots['simple' if family=='b0' else 'b0']['sigma2'])))
            for kind,c,variance in cells:
                if variance in cache:
                    result=cache[variance];origin='identical_H_sigma_deduplicated'
                else:
                    result=terminal(s,variance,code);cache[variance]=result;calls+=1;origin='computed_terminal_only'
                audit=({k:dict(original=row['arm'][k],replayed=result[k],exact_equal=row['arm'][k]==result[k]) for k in fields} if kind=='own' and c==1 else None)
                results.append(dict(family=family,kind=kind,multiplier=c,sigma2=variance,c1_original_audit=audit,
                    reference_sigma2=reference,H_hash=array_hash(s['H']),origin=origin,**result))
        publish_json(args.out/f'frame-{index:03d}.json',dict(replicate=args.replicate,frame_index=index,
            input_hashes=pair['b0']['input_hashes'],cells=results,terminal_calls_so_far=calls,
            reset='local stateless BP, original prior each call; all c=1 replayed; unequal output hashes are retained, no tolerance waiver'))
        print(json.dumps(dict(frame=index,terminal_calls=calls,elapsed=time.time()-started)),flush=True)
    publish_json(args.out/'complete.json',dict(terminal_calls=calls,design_cells=8*n,wall_seconds=time.time()-started,complete=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['fit','holdout'],default='fit');p.add_argument('--replicate',type=int,required=True)
    p.add_argument('--rows',type=Path,required=True);p.add_argument('--recipes',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);run(p.parse_args())
