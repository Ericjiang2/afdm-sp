"""Prespecified 20 color contrasts; paired channel-cluster bootstrap."""
import argparse,json
from pathlib import Path
import numpy as np


def analyze(rows):
    identities=sorted({(r['stream'],r['frame']) for r in rows})
    if len(identities)!=48 or len(rows)!=2304:raise ValueError('incomplete color matrix')
    values={}
    for arm in ('A','G','W'):
        for k in (16,40):
            for power in (1.,.25):
                v=[]
                for stream,frame in identities:
                    matches=[r for r in rows if (r['stream'],r['frame'],r['arm'],r['capacity'],r['power'])==(stream,frame,arm,k,power)]
                    if len(matches)!=4 or {r['repetition'] for r in matches}!={0,1,2,3}:raise ValueError('missing paired repeated draws')
                    v.append(np.mean([r['metrics']['nmse'] for r in matches]))
                values[arm,k,power]=np.array(v)
    contrasts=[]
    def add(name,difference,control=None):contrasts.append((name,difference,control))
    for power in (1.,.25):
        for k in (16,40):
            add(f'G-W_K{k}_beta{power}',values['G',k,power]-values['W',k,power],values['W',k,power])
            add(f'A-G_K{k}_beta{power}',values['A',k,power]-values['G',k,power],values['G',k,power])
        for a,b in (('G','W'),('A','G')):
            add(f'capacity_interaction_{a}-{b}_beta{power}',(values[a,40,power]-values[b,40,power])-(values[a,16,power]-values[b,16,power]))
    for arm in ('A','G','W'):
        for k in (16,40):add(f'power_{arm}_K{k}',values[arm,k,.25]-values[arm,k,1.],values[arm,k,1.])
    for k in (16,40):add(f'color_power_interaction_K{k}',(values['G',k,.25]-values['W',k,.25])-(values['G',k,1.]-values['W',k,1.]))
    assert len(contrasts)==20
    resamples=np.random.default_rng(20260907).integers(0,48,size=(20000,48))
    results=[]
    for name,difference,control in contrasts:
        relative=control is not None and control.mean()>=1e-4
        samples=difference[resamples].mean(1);point=float(difference.mean())
        margin=.001 if control is None else .0001
        if relative:
            samples=samples/control[resamples].mean(1);point/=float(control.mean());margin=.05
        low,high=np.quantile(samples,[.05/40,1-.05/40])
        decision=('POSITIVE_BEYOND_MARGIN' if low>margin else 'NEGATIVE_BEYOND_MARGIN' if high<-margin
                  else 'EQUIVALENT_WITHIN_MARGIN' if low>=-margin and high<=margin else 'INCONCLUSIVE')
        results.append(dict(name=name,estimate=point,interval=[float(low),float(high)],margin=margin,
                            scale='relative' if relative else 'absolute NMSE',decision=decision))
    return dict(channels=48,repetitions_per_H=4,bootstrap_draws=20000,analysis_seed=20260907,
                simultaneous_family=20,nominal_family_confidence=.95,method='paired H-cluster percentile bootstrap with Bonferroni; approximate coverage',
                scope='development mechanism matrix; augmented real G matches R/P; W proper isotropic',
                means={f'{a}_K{k}_beta{p}':float(v.mean()) for (a,k,p),v in values.items()},contrasts=results,
                shadow_baselines='pending BASE-04; no final route or novelty claim')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    result=analyze(json.loads(a.input.read_text()));a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(means=result['means'],decisions=[(r['name'],r['decision']) for r in result['contrasts']]),indent=2))
