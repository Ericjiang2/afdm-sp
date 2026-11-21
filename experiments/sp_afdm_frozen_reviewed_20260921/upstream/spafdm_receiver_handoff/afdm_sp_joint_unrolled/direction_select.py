"""Read-only BASE-02 selection from complete paired D_design and engineering timing."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
from pathlib import Path

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.direction_logging import validate_record, validate_pair


def read(path):
    raw=Path(path).read_bytes()
    value=json.loads(raw)
    # Reject nonstandard NaN/Infinity accepted by Python's JSON reader.
    json.dumps(value,allow_nan=False)
    return value,hashlib.sha256(raw).hexdigest()


def paired_interval(first,second,comparisons):
    """Simultaneous 95% CI for FER_first - FER_second, CP marginal union bound."""
    from scipy.stats import beta
    if len(first)!=len(second) or not first or comparisons<1:
        raise ValueError('invalid paired contrast')
    if any(type(v) is not int or v not in (0,1) for v in first+second):
        raise ValueError('binary FER events required')
    n=len(first)
    wins=sum(a==1 and b==0 for a,b in zip(first,second))
    losses=sum(a==0 and b==1 for a,b in zip(first,second))
    tail=.05/(4*comparisons)
    def bounds(k):
        return (0. if k==0 else float(beta.ppf(tail,k,n-k+1)),
                1. if k==n else float(beta.ppf(1-tail,k+1,n-k)))
    wl,wu=bounds(wins);ll,lu=bounds(losses)
    return {'n':n,'wins':wins,'losses':losses,'delta':(wins-losses)/n,
            'interval':[wl-lu,wu-ll],'confidence_family':.95,'comparisons':comparisons,
            'tail_alpha':tail,'definition':'FER_first - FER_second',
            'method':'Bonferroni over all pairs and four CP marginal tails; no independent-arm assumption'}


def pareto_and_choice(metrics,intervals):
    names=sorted(metrics)
    rank=lambda name:(metrics[name]['FER'],metrics[name]['mean_seconds'],name)
    best=min(names,key=rank)
    pareto=[a for a in names if not any(
        metrics[b]['FER']<=metrics[a]['FER'] and metrics[b]['mean_seconds']<=metrics[a]['mean_seconds']
        and (metrics[b]['FER']<metrics[a]['FER'] or metrics[b]['mean_seconds']<metrics[a]['mean_seconds'])
        for b in names if b!=a)]
    uncertain=[]
    for other in pareto:
        if other==best:continue
        ci=intervals[tuple(sorted((best,other)))]['interval']
        if ci[0]<=0<=ci[1]:uncertain.append(other)
    # Retain the lowest-cost nondominated unresolved contender, not an arbitrary winner.
    second=sorted(uncertain,key=lambda a:(metrics[a]['mean_seconds'],metrics[a]['FER'],a))[:1]
    return {'B_star_operational':best,'all_Pareto':pareto,'representatives':[best]+second,
            'unresolved_Pareto_contenders':uncertain,
            'not_eliminated':sorted(set(pareto)-{best,*second}),
            'all_baselines_retained_in_evidence':names,'statistically_eliminated':[],
            'dominance_is_point_estimate_only':True,
            'selection_rule':'lowest design FER; ties by engineering mean latency then lexical ID',
            'formal_cost_status':'unverified_A2_denominator_and_COST02_not_available',
            'scope':'Operational development choice only. Instrumented six-sample timing is not isolated formal latency. Remaining Pareto contenders are not statistically eliminated.',
            'FREEZE01_required':'Resolve representative baseline plus prototype within at most three confirmation arms; do not drop a strong comparator silently.'}


def load_run(root,protocol_hash,recipes,split):
    root=Path(root)
    if (root/'failure.json').exists():
        raise ValueError(f'failed run cannot supply completed selection evidence: {root}')
    complete,chash=read(root/'complete.json');contract,khash=read(root/'run-contract.json')
    count=complete['calls_attempted']
    if complete['status']!='complete' or count!=complete['calls_completed']:
        raise ValueError('incomplete or failed call accounting')
    if complete['protocol_sha256']!=protocol_hash or contract['protocol_sha256']!=protocol_hash:
        raise ValueError('protocol mismatch')
    canonical=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    if complete['config_sha256']!=canonical or complete['source_sha256']!=contract['source_sha256']:
        raise ValueError('source/config manifest mismatch')
    expected_files={Path(p).name for p in complete['records']}
    actual_files={p.name for p in root.glob('frame-*.json')}
    if len(expected_files)!=count or actual_files!=expected_files:
        raise ValueError('frame files do not match complete call ledger')
    if len(list(root.glob('call-*-started.json')))!=count or len(list(root.glob('call-*-completed.json')))!=count:
        raise ValueError('missing started/completed call ledger')
    record_hashes={Path(p).name:h for p,h in complete['record_sha256'].items()}
    rows=[];hashes={};seen=set()
    for ordinal in range(1,count+1):
        start,_=read(root/f'call-{ordinal:06d}-started.json')
        end,_=read(root/f'call-{ordinal:06d}-completed.json')
        if any(end[k]!=v for k,v in start.items()) or start['attempt']!=ordinal:
            raise ValueError('call completion does not bind its start')
        name=Path(end['record']).name
        if name not in actual_files or name in seen:raise ValueError('duplicate or unknown completed frame')
        seen.add(name)
        row,digest=read(root/name)
        validate_record(row,deployable=True)
        if (digest!=end['record_sha256'] or digest!=record_hashes[name]
                or row['protocol_sha256']!=protocol_hash or row['config_sha256']!=canonical
                or row['source_sha256']!=contract['source_sha256']):
            raise ValueError('record hash/protocol/source/config mismatch')
        if (row['split']!=split or row['SNR']!=8 or row['call_type']!='full'
                or row['failure'] is not None or row['arm_id'] not in recipes
                or row['recipe']!=recipes[row['arm_id']]
                or row['input_hashes']!=start['input_hashes']
                or row['block_id']!=start['block'] or row['arm_id']!=start['arm_id']):
            raise ValueError('invalid split/recipe/call identity in selected record')
        rows.append(row);hashes[name]=digest
    return rows,{'directory':str(root),'complete_sha256':chash,'contract_file_sha256':khash,
                 'config_sha256':canonical,'source_sha256':contract['source_sha256'],
                 'record_sha256':hashes,'calls_attempted':count,'calls_completed':count,
                 'failed_calls':0,'failure_files':[]}


def indexed(rows,recipes,blocks,split):
    table={}
    for row in rows:
        key=(row['block_id'],row['arm_id'])
        if key in table:raise ValueError('duplicate block/arm across supplied runs')
        table[key]=row
    expected=set(itertools.product(blocks,recipes))
    if set(table)!=expected:raise ValueError(f'{split} must contain every prescribed block/recipe exactly once')
    for block in blocks:validate_pair([table[block,arm] for arm in recipes])
    return table


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--design-dir',type=Path,action='append',required=True)
    p.add_argument('--timing-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    protocol,phash=read(args.protocol)
    if protocol['campaign_id']!='afdm-direction-20260908-v1' or protocol['splits']['design']['blocks']!=192:
        raise ValueError('unrecognized campaign design contract')
    recipes={r['id']:r for r in protocol['design']['recipes']}
    if len(recipes)!=8:raise ValueError('requires all eight frozen design recipes')
    rows=[];provenance=[]
    for root in args.design_dir:
        chunk,source=load_run(root,phash,recipes,'design');rows.extend(chunk);provenance.append(source)
    design=indexed(rows,recipes,range(192),'design')
    timings,tsource=load_run(args.timing_dir,phash,recipes,'engineering')
    timing=indexed(timings,recipes,range(9,17),'engineering timing')
    # Source content must be common across arms and both datasets, not merely HEAD.
    manifests=[s['source_sha256'] for s in provenance]+[tsource['source_sha256']]
    if any(m!=manifests[0] for m in manifests):raise ValueError('selection mixes source snapshots')
    metrics={}
    fer={}
    for arm in sorted(recipes):
        fer[arm]=[design[b,arm]['FER'] for b in range(192)]
        costs=[timing[b,arm]['elapsed_seconds'] for b in range(11,17)]
        metrics[arm]={'errors':sum(fer[arm]),'n':192,'FER':sum(fer[arm])/192,
                      'mean_seconds':sum(costs)/len(costs),'timing_raw_seconds':costs,
                      'warmup_blocks':[9,10],'timing_blocks':list(range(11,17)),
                      'timing_scope':'six instrumented engineering samples, not COST02 or A2 cost eligibility'}
    pairs=list(itertools.combinations(sorted(recipes),2))
    intervals={pair:paired_interval(fer[pair[0]],fer[pair[1]],len(pairs)) for pair in pairs}
    result={'status':'complete','evidence_kind':'paired_design_selection_with_engineering_microtiming',
        'protocol_sha256':phash,'selection_protocol':protocol['design']['selection'],
        'metrics':metrics,'selection':pareto_and_choice(metrics,intervals),
        'paired_simultaneous_CIs':[dict(first=a,second=b,**intervals[a,b]) for a,b in pairs],
        'design_provenance':provenance,'timing_provenance':tsource,
        'design_calls':sum(s['calls_attempted'] for s in provenance),'timing_calls':tsource['calls_attempted'],
        'failed_calls_in_supplied_runs':0,'failure_scope':'All supplied runs must be complete with no failed calls. This reader does not erase or adjudicate other campaign failures in the shared ledger.',
        'limitations':['No old holdout read. Engineering FER never used for selection.',
                       'A2 formal cost eligibility unknown; B_star is provisional, not lowest FER proven within formal cost.',
                       'CP union-bound intervals are conservative and include nonzero uncertainty for zero-error/tied samples. Failure to distinguish is not equivalence.']}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    publish_json(args.out,result)


if __name__=='__main__':main()
