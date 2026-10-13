"""Read-only common-pool legacy/projected prior comparison from saved B0 states."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver,load_prior
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch,residual_data_covariance
from afdm_sp_joint_unrolled.common_score import prepare_geometry_scores,rank_candidates


def run(args):
    start=time.time();system=_make_config_a(1024,2,8,10,4)
    cfg=build_receiver(args.checkpoint,system,1024,'cpu',receiver_shell='direct40',active_cap=40).cfg
    prior,metadata=load_prior(args.prior,8.,1024,l_max=102,k_max=2,nomination_cap=40,receiver_shell='direct40')
    pilot=torch.as_tensor(np.sqrt(.5)*system._zc_seq,dtype=cfg.dtype);records=[];sources=[]
    for rep in range(3):
        for index in range(16):
            p=args.root/f'rep{rep}'/f'states-{index:02d}.pt';record_path=p.with_name(f'frame-{index:02d}.json')
            saved=torch.load(p,map_location='cpu',weights_only=False);record=json.loads(record_path.read_text())
            if saved['input_hashes']!=record['input_hashes']:raise ValueError('state identity mismatch')
            sources.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),record_sha256=hashlib.sha256(record_path.read_bytes()).hexdigest()))
            for state in saved['states']:
                t=state['outer_iter'];original=next(x for x in record['pool'] if x['outer']==t)
                ids=original['support'];candidates=original['views'][-1]['pool']
                phi=construct_sensing_matrix_torch(1024,pilot+state['mu'],cfg.c1,cfg.c2,102,2,cdtype=cfg.dtype)
                C=residual_data_covariance(state['H'],state['finite_variance'],state['sigma2'])
                table=prepare_geometry_scores(state['y'],phi,C,ids,candidates,lookup=prior,k_max=2,K_per_l=5,prior_reference='same frozen prior400 both score arms')
                labels={x['id']:x['missing'] for x in original['views'][-1]['candidates']}
                for M in (16,32,96):
                    pool=candidates[:M];entries=[r for r in table['candidates'] if r['id'] in set(pool)]
                    for mode in ('legacy_stats_prior','projected_stats_prior','ols_no_prior'):
                        ranked=sorted((r for r in entries if r['eligible']),key=lambda r:-r[mode])
                        labels_ranked=[bool(labels[r['id']]) for r in ranked]
                        tp=np.cumsum(labels_ranked);positives=sum(labels_ranked)
                        precision=(tp/np.arange(1,len(tp)+1)).tolist()
                        recall=(tp/positives).tolist() if positives else None
                        records.append(dict(replicate=rep,frame_index=index,outer=t,M=M,mode=mode,
                            pool=pool,ranked=[r['id'] for r in ranked],labels=labels_ranked,precision=precision,recall=recall,
                            average_precision=float(np.sum(np.asarray(precision)*labels_ranked)/positives) if positives else None,
                            top4_hits=sum(labels_ranked[:4]),top4_count=min(4,len(ranked)),
                            no_true_candidate=positives==0,prior_hash=table['prior_hash'],current_rank_valid=table['valid_current'],
                            score_values=[float(r[mode]) for r in ranked]))
            print(json.dumps(dict(replicate=rep,frame=index,score_views=len(records))),flush=True)
    with args.out.open('x') as f:json.dump(dict(rows=records,sources=sources,prior_sha256=hashlib.sha256(args.prior.read_bytes()).hexdigest(),wall_seconds=time.time()-start,
        scope='same saved B0 states and frozen pools; CPU shadow; same geometric prior and rank mask; no receiver rerun; no truth in scores',
        final_retention='B0 never changes support; all nominated missing atoms remain absent in this observed trajectory'),f)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);run(p.parse_args())
