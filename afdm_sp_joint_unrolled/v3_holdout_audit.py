"""Read-only all-artifact and reliability audit after the frozen holdout packet."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.e1_ldpc import qpsk_map
from afdm_sp_joint_unrolled.feedback_diagnostics import reliability_statistics
from afdm_sp_joint_unrolled.v3_statistics import residual_decomposition


def run(args):
    start=time.time();gate=json.loads((args.root/'holdout-freeze.json').read_text());rows=[];reliability=[];manifest=[]
    q=json.loads((args.root/'packet/queue-status.json').read_text())
    if not q['complete'] or any(x['exit_code']!=0 for x in q['runs']):raise ValueError('packet incomplete or failed; do not discard failures')
    paths=sorted((args.root/'results').glob('*/frame-*.json'))
    if len(paths)!=1536:raise ValueError('four complete core methods required')
    for i,p in enumerate(paths):
        r=json.loads(p.read_text());identity=f"{r['replicate']}:{r['frame_index']}"
        if r['input_hashes']!=gate['inputs'][identity] or r['split']!='D_v3_hold':raise ValueError('holdout identity changed')
        a=r['arms']['a0'];assert a['finite'] and not a['support_repair_enabled'] and len(a['bp_graphs'])==11
        assert len(r['outer_trace'])==9
        for field in ('state_snapshot','terminal_snapshot'):
            s=Path(r[field]['path']);digest=hashlib.sha256(s.read_bytes()).hexdigest()
            if digest!=r[field]['sha256']:raise ValueError('snapshot changed')
            manifest.append(dict(path=str(s),sha256=digest,bytes=s.stat().st_size))
        with np.load(r['terminal_snapshot']['path'],allow_pickle=False) as npz:
            terminal={k:npz[k] for k in npz.files}
        for k,ref in (('H','output_h_sha256'),):assert array_hash(terminal[k])==a[ref]
        assert float(terminal['sigma2'])==a['sigma2_final'] and array_hash(terminal['H_true'])==r['input_hashes']['H']
        for k in ('y','pilot','info','coded'):assert array_hash(terminal[k])==r['input_hashes'][k]
        saved=torch.load(r['state_snapshot']['path'],map_location='cpu',weights_only=False)
        assert saved['input_hashes']==r['input_hashes'] and [s['outer_iter'] for s in saved['states']]==list(range(1,10))
        assert saved['initial_support']==r['v3_initial']['support']
        data=np.sqrt(.5)*qpsk_map(terminal['coded'])
        for s in saved['states']:
            if not all(torch.isfinite(s[k]).all() for k in ('mu','finite_variance','sigma2','probabilities')):raise ValueError('nonfinite saved state')
            stats=reliability_statistics(s['probabilities'].numpy(),s['constellation'].numpy(),data,.5)
            item=dict(family=r['family'],replicate=r['replicate'],frame_index=r['frame_index'],outer=s['outer_iter'],sigma2=float(s['sigma2']),reliability=stats)
            if s['outer_iter'] in (3,6):
                assert s['H'].shape==(1024,1024) and s['A'].shape[0]==1024
                d=residual_decomposition(terminal['y'],terminal['H_true'],s['H'].numpy(),terminal['pilot'],data,s['mu'].numpy())
                if d['relative_vector_closure']>1e-10:raise ValueError('residual identity does not close')
                item['residual']=d
            reliability.append(item)
        compact={k:r[k] for k in ('family','parameter','replicate','frame_index','input_hashes','terminal_snapshot','state_snapshot','FER','information_bits','v3_initial','initial_error','outer_trace')}
        compact['arm']={k:v for k,v in a.items() if k not in ('bp_graphs','capacity_trace')}
        compact['BP_edges']=sum(x['edges'] for x in a['bp_graphs']);rows.append(compact)
        if (i+1)%128==0:print(json.dumps(dict(audited=i+1,total=1536)),flush=True)
    result=dict(rows=rows,reliability=reliability,snapshots=manifest,frames=1536,states=len(reliability),full_receiver_calls=0,terminal_calls=0,wall_seconds=time.time()-start,all_input_and_snapshot_hashes_match=True,scope='read-only all-file audit; no receiver rerun; state t is immediately before DA-LS')
    with args.out.open('x') as f:json.dump(result,f,allow_nan=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);run(p.parse_args())
