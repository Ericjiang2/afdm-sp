"""Observe native F0 fixed and syndrome-stopped outer-round budgets."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP/'tf_cstate_e1_20261017'))
import e1_driver as e1

SCENARIOS = ('U','G')
FRAMES = range(18000,18160)
SNRS = (550,600,650,700,750,800,900)
RHO = .3
K = 10
SOURCE_SHA = '6146ccb48bb64b90c7d1fb8da93b2d0b59e84c6e8100eb2f259e9ee22114168d'
OPTIONS = dict(iterations=20, ce_mode='soft', gain_mode='joint')


def receiver(native, early):
    """Reuse the native source, inserting only the round receipt and optional stop."""
    path = Path(native.__file__)
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Unrecognized native receiver')
    source = inspect.getsource(native.receive)
    mark = '    return dec,arrays,dict(seconds=time.perf_counter()-st,pilot_seconds=tp,events=events)'
    if source.count(mark) != 1:
        raise ValueError('Native return site changed')
    extra = """
        events[-1]['syndrome'] = int(dec['syndrome_trace'][-1]['unsatisfied_checks'])
        events[-1]['complete'] = time.perf_counter()-st
        if outer_early_stop and not events[-1]['syndrome']:
            break
"""
    env = dict(native.receive.__globals__, outer_early_stop=early)
    exec(compile(source.replace(mark,extra+mark), str(path), 'exec'), env)
    return env['receive']


def context():
    ctx = e1.p1ctx.load()
    entries = e1.check_frozen_md5(ctx)
    if any(v['status'] != 'ok' for v in entries.values()):
        raise AssertionError('E-1 source parity failed')
    return ctx, receiver(ctx.native,False), receiver(ctx.native,True)


def base(ctx, scenario, frame):
    return e1.p1ctx.base(ctx,scenario,RHO,frame)


def observe(ctx, base_frame, snr):
    _, obs, truth = e1.gd.observe(ctx,*base_frame,RHO,snr)
    return obs, truth


def run(ctx, fn, obs, rounds):
    return fn(obs,ctx.system,ctx.code,rounds=rounds,**OPTIONS)


def process(ctx, fn, obs, truth):
    _, arrays, stats = run(ctx,fn,obs,K)
    events = stats['events']
    return dict(errors=[e1.gd.score(ctx,arrays[f'r{i}_decoded'],truth) for i in range(K)],
                syndrome=[v['syndrome'] for v in events])


def qualify(ctx, fixed, early):
    receipts = []
    for index,(scenario,snr) in enumerate((('U',550),('G',600),('U',750),('G',900))):
        frame = FRAMES[index]
        obs,_ = observe(ctx,base(ctx,scenario,frame),snr)
        _, full, stats = run(ctx,fixed,obs,K)
        ref = [ctx.hd.syndrome_weight(ctx,full[f'r{i}_decoded']) for i in range(K)]
        assert ref == [v['syndrome'] for v in stats['events']]
        for k in (1,2,5,10):
            orig,_,_ = run(ctx,ctx.native.receive,obs,k)
            np.testing.assert_array_equal(orig['decoded'],full[f'r{k-1}_decoded'])
            got,_,trace = run(ctx,early,obs,k)
            r = next((j for j in range(k) if ref[j] == 0),k-1)
            assert len(trace['events']) == r+1
            np.testing.assert_array_equal(got['decoded'],full[f'r{r}_decoded'])
        receipts.append(dict(scenario=scenario,frame=frame,snr=snr,syndrome=ref))
    return receipts


def shard(out,index,workers):
    ctx,fixed,_ = context()
    path = out/f'rows-{index:02d}.jsonl'
    with path.open('x') as handle:
        for frame in FRAMES[index::workers]:
            for scenario in SCENARIOS:
                one = base(ctx,scenario,frame)
                for snr in SNRS:
                    obs,truth = observe(ctx,one,snr)
                    row = dict(frame=frame,scenario=scenario,snr=snr,**process(ctx,fixed,obs,truth))
                    print(json.dumps(row,allow_nan=False),file=handle,flush=True)
    return index


def pin():
    def counters():
        values={}
        for row in Path('/proc/stat').read_text().splitlines():
            key,*nums=row.split()
            if key.startswith('cpu') and key[3:].isdigit():
                v=[int(x) for x in nums[:8]]
                values[int(key[3:])]=(sum(v),v[3]+v[4])
        return values
    a=counters()
    time.sleep(1)
    b=counters()
    cpu=min(os.sched_getaffinity(0), key=lambda j:((b[j][0]-a[j][0])-(b[j][1]-a[j][1]),j))
    os.sched_setaffinity(0,{cpu})
    return cpu


def timing(out):
    cpu = pin()
    ctx,fixed,early = context()
    obs,_ = observe(ctx,base(ctx,'U',FRAMES[0]),650)
    run(ctx,ctx.native.receive,obs,2)
    with (out/'timing.jsonl').open('x') as handle:
        index=0
        for frame in FRAMES[:12]:
            for scenario in SCENARIOS:
                one = base(ctx,scenario,frame)
                for snr in (650,700):
                    obs,_ = observe(ctx,one,snr)
                    runners = (('fixed',fixed,K),('early',early,K),('native2',ctx.native.receive,2))
                    offset = index % len(runners)
                    row=dict(frame=frame,scenario=scenario,snr=snr,cpu=cpu,stats={})
                    for label,fn,k in runners[offset:]+runners[:offset]:
                        dec,_,stats=run(ctx,fn,obs,k)
                        row['stats'][label]=stats
                    print(json.dumps(row,allow_nan=False),file=handle,flush=True)
                    index+=1
    print('Timing complete: 48 pinned CPU keys',flush=True)


def main(out,commit):
    workers=min(16,len(os.sched_getaffinity(0))-16-math.ceil(os.getloadavg()[0]))
    if workers < 1:
        raise RuntimeError('Insufficient CPU headroom')
    ctx,fixed,early=context()
    gate=qualify(ctx,fixed,early)
    (out/'provenance.json').write_text(json.dumps(dict(commit=commit,workers=workers,environment=ctx.environment,
        source_sha=SOURCE_SHA,gate=gate),indent=2,allow_nan=False)+'\n')
    print(f'Native/early parity passed on {len(gate)} keys. {workers} workers.',flush=True)
    # Spawn clean interpreters rather than forking an initialized torch context.
    import multiprocessing
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as p:
        jobs=[p.submit(shard,out,i,workers) for i in range(workers)]
        for job in as_completed(jobs):
            print(f'Shard {job.result():02d} done',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('main','timing'))
    parser.add_argument('out',type=Path)
    parser.add_argument('--commit')
    args=parser.parse_args()
    if args.mode=='main':
        import re
        if args.commit is None or re.fullmatch(r'[0-9a-f]{40}',args.commit) is None:
            parser.error('main requires the producing Git commit')
        args.out.mkdir(parents=True,exist_ok=False)
        main(args.out,args.commit)
    else:
        timing(args.out)
