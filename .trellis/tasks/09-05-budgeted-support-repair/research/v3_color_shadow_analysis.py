"""Frozen-family shadow audit; secondary simultaneous H-cluster contrasts."""
import argparse,json
from pathlib import Path
import numpy as np


def analyze(core,shadow):
    if len(core)!=2304 or len(shadow)!=1728:raise ValueError('incomplete matrices')
    base={(r['stream'],r['frame'],r['repetition'],r['arm']):r for r in core if r['capacity']==40 and r['power']==1}
    fields=('H_hash','pilot_hash','noise_hash','data_hash','gaussian_hash','y_hash')
    for r in shadow:
        b=base[r['stream'],r['frame'],r['repetition'],r['arm']]
        if any(r[k]!=b[k] for k in fields):raise ValueError('shadow input differs from core')
        if not r['finite']:raise ValueError('shadow failure')
    allrows=[dict(r,family='b0') for r in base.values()]+shadow
    identities=sorted({(r['stream'],r['frame']) for r in allrows});assert len(identities)==48
    def metric(r,k):
        if k=='nmse':return r['metrics']['nmse']
        if k=='weak_missing':return r['metrics']['weak_missing_energy']
        return r['metrics']['energies'][k]
    values={};means={};costs={}
    for f in ('b0','size','ridge','sbl'):
        for a in ('A','G','W'):
            g=[r for r in allrows if r['family']==f and r['arm']==a];assert len(g)==192
            for k in ('nmse','missing','false','weak_missing'):
                v=[]
                for identity in identities:
                    entries=[r for r in g if (r['stream'],r['frame'])==identity]
                    assert len(entries)==4 and len({r['repetition'] for r in entries})==4
                    v.append(np.mean([metric(r,k) for r in entries]))
                values[f,a,k]=np.array(v);means[f'{f}:{a}:{k}']=float(np.mean(v))
            times=[r['initial_seconds'] for r in g];costs[f'{f}:{a}']=dict(mean=float(np.mean(times)),median=float(np.median(times)),p95=float(np.quantile(times,.95)))
    # All 3 families x (G-W,A-G, and each arm vs B0) x 4 metrics.
    # 60 secondary intervals, not additional independent confirmations.
    pairs=[]
    for f in ('size','ridge','sbl'):
        pairs.extend([(f'{f}:G-W',(f,'G'),(f,'W')),(f'{f}:A-G',(f,'A'),(f,'G'))])
        pairs.extend((f'{f}-{a}-B0',(f,a),('b0',a)) for a in ('A','G','W'))
    draw=np.random.default_rng(20260907).integers(0,48,(20000,48));contrasts=[]
    for name,x,y in pairs:
        for k in ('nmse','missing','false','weak_missing'):
            a,b=values[(*x,k)],values[(*y,k)];d=a-b;samples=d[draw].mean(1);point=float(d.mean());scale='absolute';margin=.001
            if k=='nmse':
                margin=.0001
                if b.mean()>=1e-4:samples/=b[draw].mean(1);point/=float(b.mean());margin=.05;scale='relative'
            ci=np.quantile(samples,[.05/120,1-.05/120]).tolist()
            contrasts.append(dict(name=name,metric=k,estimate=point,interval=ci,scale=scale,margin=margin))
    return dict(channels=48,draws_per_channel=4,initial_calls=1728,all_inputs_match_core=True,failures=0,means=means,costs=costs,contrasts=contrasts,
        interval_scope='60 secondary paired H-cluster Bonferroni percentile intervals; 20000 draws seed20260907; approximate coverage; primary20 unchanged',
        interpretation='development shadow only; same frozen parameters across A/G/W; not deployment BER/FER; working point only')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('core',type=Path);p.add_argument('shadow',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=analyze(json.loads(a.core.read_text()),json.loads(a.shadow.read_text()));a.output.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r['means'].items() if k.endswith(':nmse')},indent=2))
