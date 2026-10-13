"""Hash-only holdout identity gate; no estimator, BP, or decoded outcomes."""
import argparse,hashlib,json,time
from pathlib import Path
import torch
from afdm_sp_joint_unrolled.v3_holdout import make_holdout_frame
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash


def run(args):
    prior=json.loads(args.used.read_text());used={k:set(v) for k,v in prior['hashes'].items()};seeds=set(prior['channel_seeds'])
    cache=torch.load(args.prior_cache,map_location='cpu',weights_only=False)
    seeds.update(map(int,cache['seed'].tolist()))
    system=_make_config_a(1024,2,8,10,4);code=build_code(2048,d_v=3,d_c=6,seed=20260726)
    assert hashlib.sha256(code['G'].tobytes()).hexdigest()=='bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af'
    seen={k:set() for k in used};inputs={};new_seeds=set();started=time.time()
    for rep in range(3):
        for index in range(128):
            frame=make_holdout_frame(system,code,rep,index)
            if frame['channel_seed'] in seeds|new_seeds:raise ValueError('channel seed collision: do not silently reseed')
            hashes={k:array_hash(frame[k]) for k in ('y','H','noise','info','coded','pilot')}
            for k in used:
                if hashes[k] in used[k]|seen[k]:raise ValueError(f'{k} input collision: do not silently reseed')
                seen[k].add(hashes[k])
            new_seeds.add(frame['channel_seed']);inputs[f'{rep}:{index}']=hashes
        print(json.dumps(dict(stream=rep,hash_only_frames=len(inputs))),flush=True)
    with args.out.open('x') as f:json.dump(dict(inputs=inputs,identity_audit_passed=True,frames=384,
        old_hash_counts={k:len(v) for k,v in used.items()},old_channel_seeds=len(seeds),new_unique_channel_seeds=len(new_seeds),
        code_sha256=hashlib.sha256(code['G'].tobytes()).hexdigest(),prior_cache_sha256=hashlib.sha256(args.prior_cache.read_bytes()).hexdigest(),
        used_manifest_sha256=hashlib.sha256(args.used.read_bytes()).hexdigest(),scope='hash-only; D_test unopened; no receiver evaluation',wall_seconds=time.time()-started),f,indent=2)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--used',type=Path,required=True);p.add_argument('--prior-cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);run(p.parse_args())
