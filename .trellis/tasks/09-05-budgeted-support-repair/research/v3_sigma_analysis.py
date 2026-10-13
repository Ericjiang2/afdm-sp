"""Frozen six-contrast terminal analysis; development alone selects scale."""
import argparse,json,tarfile,math
import numpy as np
from pathlib import Path
from afdm_sp_joint_unrolled.v3_protocol import paired_fer_interval,classify_interval


def analyze(rows,development=True,scales=None):
    rows=sorted(rows,key=lambda r:(r['replicate'],r['frame_index']))
    expected=192 if development else 384
    if len(rows)!=expected or len({(r['replicate'],r['frame_index']) for r in rows})!=expected:raise ValueError('missing unique paired rows')
    groups={}
    for h in ('b0','simple'):
        for label in (.5,1.,2.,'cross'):
            group=[]
            for row in rows:
                cells=[c for c in row['cells'] if c['family']==h and (c['kind']=='cross' if label=='cross' else c['kind']=='own' and c['multiplier']==label)]
                if len(cells)!=1:raise ValueError('missing design cell')
                group.append(cells[0])
            groups[h,label]=group
    summary={f'{h}:{c}':dict(wrong_frames=sum(x['FER'] for x in g),FER=sum(x['FER'] for x in g)/expected,BER=sum(x['info_errors'] for x in g)/(expected*1024),NLL=sum(x['final_bit_nll'] for x in g)/expected,Brier=sum(x['final_bit_brier'] for x in g)/expected) for (h,c),g in groups.items()}
    if development:
        scales={h:min((.5,1.,2.),key=lambda c:(summary[f'{h}:{c}']['wrong_frames'],c!=1,abs(math.log2(c)),c)) for h in ('b0','simple')}
    if scales is None:raise ValueError('holdout cannot select scales')
    contrasts=[]
    def compare(name,reference,candidate):
        r=paired_fer_interval([bool(x['FER']) for x in reference],[bool(x['FER']) for x in candidate],comparisons=6)
        contrasts.append(dict(name=name,**r,decision=classify_interval(r['interval'],.01)))
    for h in ('b0','simple'):
        for c in (.5,2.):compare(f'{h}:scale{c}-scale1',groups[h,1.],groups[h,c])
    for x,y in zip(groups['b0',1.],groups['simple','cross']):assert x['sigma2']==y['sigma2']
    for x,y in zip(groups['b0','cross'],groups['simple',1.]):assert x['sigma2']==y['sigma2']
    compare('H_simple-H_B0_at_sigma_B0',groups['b0',1.],groups['simple','cross'])
    compare('H_simple-H_B0_at_sigma_simple',groups['b0','cross'],groups['simple',1.])
    c1=[x for h in ('b0','simple') for x in groups[h,1.]]
    interaction=np.array([s['FER']-b_cross['FER']-s_cross['FER']+b['FER'] for b,s,b_cross,s_cross in zip(groups['b0',1.],groups['simple',1.],groups['b0','cross'],groups['simple','cross'])],dtype=float)
    draws=np.random.default_rng(20260907).integers(0,expected,(20000,expected))
    interaction_summary=dict(estimate=float(interaction.mean()),interval=np.quantile(interaction[draws].mean(1),[.025,.975]).tolist(),scope='secondary descriptive paired H bootstrap; not an extra independent confirmation; not mediation fraction')
    return dict(frames=expected,dataset='D_fit' if development else 'D_v3_hold',scales=scales,summary=summary,contrasts=contrasts,
        c1_audit=dict(cells=len(c1),decoded_bit_mismatches=sum(not c['c1_original_audit']['decoded_bits_sha256']['exact_equal'] for c in c1),info_error_mismatches=sum(not c['c1_original_audit']['info_errors']['exact_equal'] for c in c1),soft_hash_mismatches=sum(not c['c1_original_audit']['final_bp_mu_sha256']['exact_equal'] for c in c1),max_NLL_delta=max(abs(c['c1_original_audit']['final_bit_nll']['original']-c['final_bit_nll']) for c in c1)),
        controlled_interaction=interaction_summary,
        inference='terminal controlled direct effect; no mediation percentage; cross sigma diagnostic requires both trajectories')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with tarfile.open(a.archive) as t:
        q=json.load(t.extractfile('packet/queue-status.json'));assert q['complete'] and all(r['exit_code']==0 for r in q['runs'])
        rows=[json.load(t.extractfile(m)) for m in t.getmembers() if '/frame-' in m.name and m.name.endswith('.json')]
    r=analyze(rows);a.output.write_text(json.dumps(r,indent=2));print(json.dumps(dict(scales=r['scales'],summary=r['summary'],c1=r['c1_audit']),indent=2))
