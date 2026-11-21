"""P1 pilot: path B and narrow-block LOCAL, full-Gamma, and scalar-Gamma rescue."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from block import BlockBank

HERE=Path(__file__).resolve().parent
REFERENCE=HERE.parent/'dpss_p1_narrow_20261110'
spec=importlib.util.spec_from_file_location('narrow_p1',REFERENCE/'run.py')
ref=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)
p1, m2, paired = ref.p1, ref.m2, ref.p1_replay
FRAMES=128
ARMS=('B','NARROW','LOCAL','FULL','SCALAR')


def bank_for(ctx):
    s=ctx.system
    return BlockBank(s.N_total,s.c1,s.c2,s.l_max_cap,m2.dpss_rx.tap_columns,m2.tapchannel)


def prefix(ctx,obs):
    refine=ref.NarrowRefine()
    with m2.dpss_rx.vector_prior(ctx.native):
        result=ctx.wrappers._instrumented(ctx.native,obs,ctx.system,ctx.code,arm='NARROW',rounds=2,
            iterations=20,gain_mode='joint',refine_override=refine)
    return result, refine


def score(ctx,dec,truth):
    return dict(errors=int(np.count_nonzero(ctx.extract_info(ctx.code,dec['decoded'])!=truth['info'])),
                syndrome=ctx.hd.syndrome_weight(ctx,dec['decoded']),
                logloss=ctx.arms.logloss_bits(dec['incoming_llr'],truth['coded']),
                decoded_sha256=ctx.hd.decoded_sha(dec['decoded']))


def rescue(ctx,bank,obs,truth,result,refine):
    from messages import moments
    mu,v,_=moments(np.clip(result.arrays['r1_app'],-20,20),1-ctx.system.rho)
    check=np.clip(result.arrays['r1_check'],-20,20)
    initial=tuple(5*t['delay']+int(t['c'])+2 for t in refine.prev['taps'])
    prepared=bank.prepare(obs,mu,v)
    supports={'LOCAL':initial,'FULL':bank.exchange(initial,prepared,True),
              'SCALAR':bank.exchange(initial,prepared,False)}
    rows={}
    cache={}
    for arm, groups in supports.items():
        if groups not in cache:
            c=bank.channel(groups,prepared)
            d=m2.dpss_rx.scalar_joint_cols(obs['y'],obs['pilot'],c,obs['sigma2'],
                np.full(c.p,1/c.p),pd=1-ctx.system.rho,prior=check,iterations=20)
            decoded=ctx.native.decoder_messages(ctx.code,np.clip(d['extrinsic'],-20,20),maxiter=50)
            cache[groups]=score(ctx,decoded,truth)
        rows[arm]=cache[groups] | dict(groups=groups)
    return rows


def run(out,shard,shards,smoke):
    ctx=paired.context(out)
    bank=bank_for(ctx)
    old=ref.load_rows((REFERENCE/'out').glob('rows-*.jsonl'))
    control=ref.load_rows((paired.HERE/'out').glob('rows-*.jsonl'))
    seed=p1.make_seed_fn()
    with (out/('smoke.jsonl' if smoke else f'rows-{shard:02d}.jsonl')).open('x') as handle:
        for frame in (range(2) if smoke else range(shard,FRAMES,shards)):
            for scenario in p1.SCENARIOS:
                base,diag=p1.generate(ctx,scenario,paired.RHO,ref.SNR[0],frame,seed)
                for snr in ((4.5,) if smoke else ref.SNR):
                    raw,d=ctx.reuse_at_snr(base,diag,snr)
                    truth=ctx.hd.truth_from_raw(raw,d)
                    obs=ctx.hd.observe(raw,paired.RHO,snr)
                    key=scenario,snr,frame
                    pair=hashlib.sha256(obs['y'].tobytes()+obs['pilot'].tobytes()+
                                        np.float64(obs['sigma2']).tobytes()).hexdigest()
                    assert pair==old[key]['pair']==control[key]['pair']
                    b=p1.compute_arms(ctx,obs,truth,('F0','B'))
                    assert b['F0']['decoded_sha256']==control[key]['arms']['F0']['decoded_sha256']
                    assert b['B']['status']=='ok'
                    result,refine=prefix(ctx,obs)
                    n=score(ctx,result.decoder,truth)
                    assert n['errors']==old[key]['info_errors'] and n['syndrome']==old[key]['syndrome']
                    assert abs(n['logloss']-old[key]['logloss_bits'])<1e-12
                    branches=rescue(ctx,bank,obs,truth,result,refine) if n['syndrome'] else {
                        a:n for a in ('LOCAL','FULL','SCALAR')}
                    rows={'B':dict(errors=b['B']['info_errors'],syndrome=b['B']['syndrome'],
                                   logloss=b['B']['logloss_bits']),
                          'NARROW':n,**branches}
                    print(json.dumps(dict(scenario=scenario,snr=snr,frame=frame,pair=pair,arms=rows),
                                     allow_nan=False),file=handle,flush=True)
            if smoke or frame//shards%8==0:
                print(f'shard {shard} frame {frame}',flush=True)


def summarize(out):
    rows={}
    for path in sorted(out.glob('rows-*.jsonl')):
        for line in path.read_text().splitlines():
            r=json.loads(line)
            key=r['scenario'],r['frame'],r['snr']
            assert key not in rows
            rows[key]=r['arms']
    assert len(rows)==2*FRAMES*len(ref.SNR)
    resample=np.random.default_rng(20261110).integers(0,FRAMES,(10000,FRAMES))
    report={}
    for scene in p1.SCENARIOS:
        data=[[rows[scene,f,s] for s in ref.SNR] for f in range(FRAMES)]
        err={a:np.array([[r[a]['errors']>0 for r in line] for line in data]) for a in ARMS}
        trig=np.array([[r['NARROW']['syndrome']!=0 for r in line] for line in data])
        den=trig.sum(axis=1)[resample].sum(axis=1)
        loss={a:np.array([[r[a]['logloss'] for r in line] for line in data]) for a in ARMS}
        comparisons={}
        for a,b in (('FULL','LOCAL'),('SCALAR','FULL'),('FULL','B')):
            diff=err[b].astype(int)-err[a]
            dloss=loss[a]-loss[b]
            if a=='SCALAR':
                v=(diff*trig).sum(axis=1)[resample].sum(axis=1)/den
                point=float((diff*trig).sum()/trig.sum())
            else:
                v=diff.mean(axis=1)[resample].mean(axis=1)
                point=float(diff.mean())
            comparisons[f'{a}-{b}']=dict(
                rescue=int((err[b]&~err[a]).sum()),harm=int((err[a]&~err[b]).sum()),
                error_rate_improvement=point,ci97p5=np.quantile(v,[.0125,.9875]).tolist(),
                delta_logloss=float(dloss.mean()),
                logloss_ci97p5=np.quantile(dloss.mean(axis=1)[resample].mean(axis=1),[.0125,.9875]).tolist())
        edits=([r['FULL']['groups']!=r['LOCAL']['groups'] for line in data for r in line
                if r['NARROW']['syndrome']], [r['SCALAR']['groups']!=r['FULL']['groups'] for line in data
                for r in line if r['NARROW']['syndrome']])
        report[scene]=dict(snr_db=ref.SNR,frames=FRAMES,triggered=int(trig.sum()),
            errors={a:e.sum(axis=0).tolist() for a,e in err.items()},
            full_exchanges=sum(edits[0]),scalar_changes_selection=sum(edits[1]),comparisons=comparisons)
    result=json.dumps(report,indent=2,allow_nan=False)
    (out/'summary.json').write_text(result+'\n')
    print(result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path)
    parser.add_argument('--shard',type=int,default=0)
    parser.add_argument('--shards',type=int,default=1)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--summarize',action='store_true')
    args=parser.parse_args()
    if args.summarize:
        summarize(args.out)
    else:
        run(args.out,args.shard,args.shards,args.smoke)
