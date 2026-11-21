"""Matched FER/latency frontiers from a small fixed/early budget screen."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from screen import FRAMES, K, SCENARIOS, SNRS
from p1_agg import HIGH, LOW, crossing


def rows(path):
    return [json.loads(row) for row in path.read_text().splitlines()]


def bound(x):
    return ('+inf' if x > 0 else '-inf') if np.isinf(x) else float(x)


def q(x,p):
    i=math.ceil(len(x)*p)-1
    return float(np.partition(x,i)[i])


def brackets(samples,n):
    x,stat=crossing(samples,n,np.asarray(SNRS)/100.)
    return np.where(stat==LOW,-np.inf,x),np.where(stat==HIGH,np.inf,x),stat


def selected_rounds(syndrome):
    first=np.where((syndrome==0).any(axis=-1),(syndrome==0).argmax(axis=-1),K-1)
    return np.minimum(first[...,None],np.arange(K))


def latency(values):
    return dict(mean_ms=float(np.mean(values)*1000),median_ms=float(np.median(values)*1000),
                p95_ms=float(np.quantile(values,.95)*1000))


def profile(timing):
    assert len(timing)==48
    wanted={(s,f,g) for s in SCENARIOS for f in FRAMES[:12] for g in (650,700)}
    assert {(r['scenario'],r['frame'],r['snr']) for r in timing}==wanted
    native=[r['stats']['native2'] for r in timing]
    parts={'pilot':[x['pilot_seconds'] for x in native]}
    parts.update({name:[sum(e[field] for e in x['events']) for x in native]
                  for name,field in [('ce','ce'),('detector','inference'),('ldpc','decoder')]})
    total=np.array([x['seconds'] for x in native])
    parts['remaining']=total-np.sum(list(parts.values()),axis=0)
    means={name:float(np.mean(x)) for name,x in parts.items()}
    return dict(total=latency(total),parts={n:dict(mean_ms=t*1000,share=t/total.mean()) for n,t in means.items()},
                ldpc_iterations={str(k+1):float(np.mean([x['events'][k]['decoder_iterations'] for x in native]))
                                 for k in range(2)})


def extract_time(r,policy,k):
    stats=r['stats'][policy]
    events=stats['events']
    return stats['seconds'] if len(events)<=k else events[k-1]['complete']


def analyse(out):
    trials=[r for file in sorted(out.glob('rows-*.jsonl')) for r in rows(file)]
    by={(r['scenario'],r['frame'],r['snr']):r for r in trials}
    n=len(FRAMES)
    assert len(by)==len(trials)==2*n*len(SNRS)
    boot=np.random.default_rng(20261118).multinomial(n,np.full(n,1/n),size=10000).astype(float)
    timed=rows(out/'timing.jsonl')
    all_results={}
    for s in SCENARIOS:
        err,syn=(np.asarray([[by[s,i,g][field] for g in SNRS] for i in FRAMES])
                 for field in ('errors','syndrome'))
        assert np.shape(err)==(n,len(SNRS),K)
        assert np.all(err>=0) and np.all(syn>=0)
        errors=err>0
        stop_at=selected_rounds(syn)
        early=np.take_along_axis(errors,stop_at,axis=-1)
        early_syn=np.take_along_axis(syn,stop_at,axis=-1)
        profiles={}
        for policy,sample in (('fixed',errors),('early',early)):
            for k in range(1,K+1):
                x=sample[:,:,k-1].astype(float)
                lower,upper,stat=brackets(np.vstack([x.mean(axis=0),boot@x/n]),n)
                profiles[policy,k]=(lower,upper,stat,np.count_nonzero(x,axis=0).tolist())
        ref0,ref1,_,_=profiles['fixed',K]
        series={}
        timed_s=[r for r in timed if r['scenario']==s]
        for (policy,k),(lower,upper,stat,failures) in profiles.items():
            gap_lo=lower-ref1
            gap_hi=upper-ref0
            if (policy,k)==('fixed',K):
                gap_lo=np.zeros_like(lower)
                gap_hi=np.zeros_like(upper)
            d=dict(errors=failures,point=[bound(lower[0]),bound(upper[0])],
                   ci95=[bound(q(lower[1:],.025)),bound(q(upper[1:],.975))],
                   gap=[bound(gap_lo[0]),bound(gap_hi[0])],
                   gap_ci95=[bound(q(gap_lo[1:],.025)),bound(q(gap_hi[1:],.975))],
                   left_censored=int((stat[1:]==LOW).sum()),right_censored=int((stat[1:]==HIGH).sum()),
                   latency=latency([extract_time(r,policy,k) for r in timed_s]))
            if policy=='early':
                d.update(mean_rounds=float(stop_at[:,:,k-1].mean()+1),
                         round1_stops=int((syn[:,:,0]==0).sum()),
                         undetected=int((early[:,:,k-1] & (early_syn[:,:,k-1]==0)).sum()))
            series[f'{policy}_{k}']=d
        plateau=all(profiles['fixed',k][2][0]==0 and ref0[0]==ref1[0]
                    and abs(profiles['fixed',k][0][0]-ref0[0])<=.2 for k in (8,9))
        def endpoint(row,index):
            return float(row['gap_ci95'][index])

        shallow=[name for name,d in series.items() if int(name.split('_')[1])<=2 and endpoint(d,1)<=.2]
        no_shallow=all(endpoint(d,0)>.2 for name,d in series.items() if int(name.split('_')[1])<=4)
        verdict=('shallow_sufficient' if plateau and shallow else
                 'depth_bottleneck' if plateau and no_shallow else 'inconclusive')
        all_results[s]=dict(series=series,long_budget_stable=bool(plateau),
                            shallow_meeting_bound=shallow,verdict=verdict)
    return dict(keys=len(trials),frames=n,snr_db=[g/100 for g in SNRS],by_scenario=all_results,
                pinned_cpu=timed[0]['cpu'],timing_keys=len(timed),native_f0_profile=profile(timed))


def figure(doc,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig,axes=plt.subplots(1,2,figsize=(10,4.3),sharey=True,layout='constrained')
    wanted={'fixed':('#294b76','o','Fixed budget'),'early':('#b54831','s','Syndrome early stop')}
    for ax,(s,result) in zip(axes,doc['by_scenario'].items(),strict=True):
        for policy,(color,marker,label) in wanted.items():
            points=[]
            annotations=set()
            for k in range(1,K+1):
                row=result['series'][f'{policy}_{k}']
                lo,hi=row['point']
                if lo==hi:
                    points.append((row['latency']['mean_ms'],lo,k))
                else:
                    y,x=(hi,'≤') if lo=='-inf' else (lo,'≥')
                    t=row['latency']['mean_ms']
                    ax.scatter([t],[y],color=color,marker='v' if x=='≤' else '^',facecolors='none')
                    if x=='≤' and policy=='early' and 'lower' not in annotations:
                        ax.annotate(f'K≥{k}',(t,y),xytext=(5,8),textcoords='offset points',
                                    color=color,fontsize=8)
                        annotations.add('lower')
            if points:
                xs,ys,ks=zip(*points,strict=True)
                ax.plot(xs,ys,color=color,marker=marker,label=label,linewidth=1)
                named=[]
                for x,y,k in points:
                    if k==1 and policy=='early':
                        continue
                    if k in (1,2,5,10) and all(abs(x-x0)>18 or abs(y-y0)>.04 for x0,y0 in named):
                        dy = (5 if k==5 else -12) if policy=='early' else 5
                        ax.annotate(str(k),(x,y),xytext=(4,dy),
                                    textcoords='offset points',color=color,fontsize=8)
                        named.append((x,y))
        ax.set_title(f'{s}, physical ρ = .3')
        ax.set_xlabel('Mean latency at 6.5 and 7 dB (ms)')
        ax.grid(alpha=.22)
    axes[0].set_ylabel('SNR for 1% FER (dB)')
    axes[0].legend(frameon=False,fontsize=8)
    fig.suptitle('Classical F0 outer-round budget\nOpen triangles mark censored SNR bounds',fontsize=12)
    fig.savefig(out/'frontier.png',dpi=170)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    p.add_argument('--plot',action='store_true')
    a=p.parse_args()
    if a.plot:
        figure(json.loads((a.out/'summary.json').read_text()),a.out)
    else:
        doc=analyse(a.out)
        (a.out/'summary.json').write_text(json.dumps(doc,indent=2,allow_nan=False)+'\n')
