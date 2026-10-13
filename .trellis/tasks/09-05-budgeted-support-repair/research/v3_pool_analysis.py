"""Paired B0 trajectory candidate visibility and preregistered ACTION gate."""
import argparse,json
from pathlib import Path
import numpy as np


def analyze(rows):
    rows=sorted(rows,key=lambda r:(r['replicate'],r['frame_index']))
    if len(rows)!=48 or len({(r['replicate'],r['frame_index']) for r in rows})!=48:raise ValueError('48 unique trajectories required')
    arrays={};summary={};sample=np.random.default_rng(20260907).integers(0,48,(20000,48))
    for t in (0,3,6):
        for m in (16,32,96):
            views=[next(v for v in next(s for s in r['pool'] if s['outer']==t)['views'] if v['M']==m) for r in rows]
            a=np.array([[v['current']['recall_weight'],v['current']['missing_weight'],v['current']['top4_hits'],v['current']['top4_count'],v['current']['random_pool_prevalence'],v['fixed_t0']['top4_hits'],v['fixed_t0']['missing_count']] for v in views])
            if a[:,1].sum()==0 or a[:,6].sum()==0:raise ValueError('undefined missing denominator')
            point=np.array([a[:,0].sum()/a[:,1].sum(),a[:,2].sum()/a[:,3].sum()-a[:,4].mean(),a[:,5].sum()/a[:,6].sum()])
            b=a[sample];draws=np.stack((b[:,:,0].sum(1)/b[:,:,1].sum(1),b[:,:,2].sum(1)/b[:,:,3].sum(1)-b[:,:,4].mean(1),b[:,:,5].sum(1)/b[:,:,6].sum(1)),1)
            arrays[t,m]=(point,draws)
            summary[f't{t}_M{m}']=dict(weighted_recall=float(point[0]),top4_precision=float(a[:,2].sum()/a[:,3].sum()),random_pool_prevalence=float(a[:,4].mean()),fixed_missing_hit_fraction=float(point[2]),no_missing_frames=int((a[:,1]==0).sum()),full_scan_columns=515)
    gates=[]
    # Six joint requirements: three at each of the two registered times.
    # Bonferroni two-sided intervals keep selection across t3/t6 explicit.
    for t in (3,6):
        point,draws=arrays[t,32];p0,d0=arrays[0,32]
        estimates=[point[0],point[1],point[2]-p0[2]]
        samples=[draws[:,0],draws[:,1],draws[:,2]-d0[:,2]]
        ci=[np.quantile(x,[.05/12,1-.05/12]).tolist() for x in samples]
        passed=ci[0][0]>=.8 and ci[1][0]>=.1 and ci[2][0]>=.1
        gates.append(dict(t=t,estimates=dict(zip(('weighted_recall','precision_excess','fixed_missing_hit_improvement'),map(float,estimates))),intervals=ci,passed=passed))
    return dict(frames=48,views=432,trajectory='actual shared B0 t0/t3/t6; D_dev rep0/1/2',summary=summary,gates=gates,
        action_eligible=any(g['passed'] for g in gates),chosen_time=next((g['t'] for g in gates if g['passed']),None),
        bootstrap='20000 paired H resamples, seed20260907; six simultaneous requirements; approximate percentile coverage',
        scope='consistent scorer visibility; historical scorer comparison still pending; no oracle-terminal ranking claim')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    r=analyze(json.loads(a.input.read_text()));a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r['gates'],indent=2))
