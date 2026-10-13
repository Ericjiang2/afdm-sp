"""Four frozen core methods: paired FER and H-cluster continuous intervals."""
import argparse,json
from pathlib import Path
import numpy as np
from afdm_sp_joint_unrolled.v3_protocol import paired_fer_interval,classify_interval


def analyze(audit):
    rows=audit['rows'];assert len(rows)==1536 and audit['all_input_and_snapshot_hashes_match']
    groups={f:sorted([r for r in rows if r['family']==f],key=lambda r:(r['replicate'],r['frame_index'])) for f in ('b0','size','ridge','sbl')}
    assert all(len(g)==384 for g in groups.values())
    base=groups['b0'];summary={};contrasts=[];continuous=[]
    draw=np.random.default_rng(20260907).integers(0,384,(20000,384))
    getters=dict(initial_nmse=lambda r:r['initial_error']['nmse'],terminal_nmse=lambda r:r['arm']['nmse'],missing_energy=lambda r:r['initial_error']['energies']['missing'],false_energy=lambda r:r['initial_error']['energies']['false'],weak_missing_energy=lambda r:r['initial_error']['weak_missing_energy'],BP_edges=lambda r:r['BP_edges'],seconds=lambda r:r['arm']['standalone_seconds_estimate'])
    for f,g in groups.items():
        for a,b in zip(base,g):assert (a['replicate'],a['frame_index'],a['input_hashes'])==(b['replicate'],b['frame_index'],b['input_hashes'])
        values={k:np.array([fn(r) for r in g]) for k,fn in getters.items()}
        summary[f]=dict(frames=384,wrong_frames=sum(r['FER'] for r in g),FER=sum(r['FER'] for r in g)/384,BER=sum(r['arm']['info_errors'] for r in g)/(384*1024),failure_frames=0,means={k:float(v.mean()) for k,v in values.items()},runtime=dict(mean=float(values['seconds'].mean()),median=float(np.median(values['seconds'])),p95=float(np.quantile(values['seconds'],.95))),streams=[dict(replicate=rep,frames=128,wrong_frames=sum(r['FER'] for r in g if r['replicate']==rep),info_errors=sum(r['arm']['info_errors'] for r in g if r['replicate']==rep)) for rep in range(3)])
        if f=='b0':continue
        result=paired_fer_interval([bool(r['FER']) for r in base],[bool(r['FER']) for r in g],comparisons=4)
        contrasts.append(dict(candidate=f,reference='b0',**result,decision=classify_interval(result['interval'],.01)))
        for k,v in values.items():
            d=v-np.array([getters[k](r) for r in base]);ci=np.quantile(d[draw].mean(1),[.05/42,1-.05/42]).tolist()
            continuous.append(dict(method=f,metric=k,paired_difference=float(d.mean()),interval=ci))
    equivalence=[]
    for f in ('size','ridge'):
        r=paired_fer_interval([bool(x['FER']) for x in groups['sbl']],[bool(x['FER']) for x in groups[f]],comparisons=2)
        equivalence.append(dict(candidate=f,reference='development_frozen_sbl',**r,decision=classify_interval(r['interval'],.01)))
    return dict(dataset='independent D_v3_hold; not D_test',frames_per_method=384,full_receiver_calls=1536,summary=summary,FER_contrasts=contrasts,simple_equivalence=equivalence,continuous_contrasts=continuous,continuous_method='21 simultaneous paired H-cluster percentile intervals; 20000 draws, seed20260907; approximate coverage',inference='natural complete-trajectory total effects; not additive with fixed-H sigma or old A2 gain oracle',cost_scope='measured with observers and concurrent jobs; no formal G2 claim',recipe_selection_on_holdout=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('audit',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=analyze(json.loads(a.audit.read_text()));a.output.write_text(json.dumps(r,indent=2));print(json.dumps(dict(summary=r['summary'],FER_contrasts=r['FER_contrasts'],equivalence=r['simple_equivalence']),indent=2))
