"""Strict descriptive S2 analysis. This development table cannot pass G1/G2."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import binomtest


ARMS = ('baseline','keep','unprotected','oracle_gains','oracle_data','wide_pool')


def read_matrix(base):
    rows, statuses = [], []
    for snr in (7,8,9):
        for rep in range(3):
            directory = Path(base)/f'dev-snr{snr}-rep{rep}'
            status = json.loads((directory/'status.json').read_text())
            batch = [json.loads(x) for x in (directory/'frames.jsonl').read_text().splitlines()]
            if not status['complete'] or status.get('failure') or status['completed_frames']!=64 or len(batch)!=64:
                raise ValueError(f'incomplete diagnostic batch: {directory}')
            if [(r['snr'],r['replicate'],r['frame_index']) for r in batch] != [(snr,rep,i) for i in range(64)]:
                raise ValueError('unexpected/duplicate frame identities')
            if any(r['split']!='D_dev' or set(r['arms'])!=set(ARMS) for r in batch):
                raise ValueError('wrong split or arms')
            if any(not a['finite'] for r in batch for a in r['arms'].values()):
                raise ValueError('invalid receiver frame retained in success set')
            rows.extend(batch)
            statuses.append(status)
    for key in ('checkpoint_sha256','ldpc_sha256','source_sha256','device'):
        if any(s[key]!=statuses[0][key] for s in statuses):
            raise ValueError(f'mixed provenance: {key}')
    for snr in (7,8,9):
        hashes={s['calibration_sha256'] for s in statuses if s['config']['snr']==snr}
        if len(hashes)!=1:
            raise ValueError('replicates used different calibration within one SNR')
    validate_clusters(rows)
    return rows,statuses


def validate_clusters(rows):
    by_cluster = {}
    for r in rows:
        key = (r['replicate'],r['frame_index'])
        by_cluster.setdefault(key,[]).append(r)
    for cluster in by_cluster.values():
        if sorted(r['snr'] for r in cluster)!=[7,8,9]:
            raise ValueError('cross-SNR cluster missing or duplicate condition')
        for name in ('H','noise','info','coded','pilot'):
            if len({r['input_hashes'][name] for r in cluster})!=1:
                raise ValueError(f'cross-SNR source mismatch: {name}')
    seeds = [c[0]['channel_seed'] for c in by_cluster.values()]
    if len(set(seeds))!=len(seeds):
        raise ValueError('duplicate channel seed across independent development frames')


def physical_matches(params,pairs):
    truth = np.column_stack([params['l_i'],params['k_real']])
    predicted = np.asarray(pairs,dtype=float).reshape(-1,2)
    if not len(predicted):
        return 0
    dl = np.abs(truth[:,None,0]-predicted[None,:,0])
    dk = np.abs(truth[:,None,1]-predicted[None,:,1])
    valid = (dl==0)&(dk<=.5)
    i,j = linear_sum_assignment(np.where(valid,dk,1000.))
    return int(valid[i,j].sum())


def summarize(rows,arm):
    errors = np.array([r['arms'][arm]['info_errors'] for r in rows])
    ref = np.array([r['arms']['baseline']['info_errors'] for r in rows])
    x,y = errors>0,ref>0
    n = len(rows)
    ci = binomtest(int(x.sum()),n).proportion_ci(method='exact')
    table = {'n00':int((~x&~y).sum()),'n10':int((x&~y).sum()),
             'n01':int((~x&y).sum()),'n11':int((x&y).sum())}
    active = [len(r['arms'][arm]['support']['expanded']) for r in rows]
    physical = [physical_matches(r['channel_parameters'],r['arms'][arm]['support']['expanded']) for r in rows]
    paths = sum(r['physical_paths'] for r in rows)
    true_columns = [set(r['truth_unique_columns']) for r in rows]
    first_pools = [set(r['arms'][arm]['rounds'][0]['candidate_ids']) for r in rows]
    initial = [set(r['arms'][arm]['support']['raw']) for r in rows]
    true_total = sum(map(len,true_columns))
    return dict(frames=n,frame_errors=int(x.sum()),fer=float(x.mean()),fer_exact95=[ci.low,ci.high],
                paired_table=table,fer_difference=float(x.mean()-y.mean()),
                fer_ratio=float(x.sum()/y.sum()) if y.any() else None,
                information_bit_errors=int(errors.sum()),
                raw_bit_errors=sum(r['arms'][arm]['raw_errors'] for r in rows),
                information_error_wins=int((errors<ref).sum()),information_error_harms=int((errors>ref).sum()),
                mean_nmse=float(np.mean([r['arms'][arm]['nmse'] for r in rows])),
                mean_active_atoms=float(np.mean(active)),
                matched_physical_paths=sum(physical),physical_path_denominator=paths,
                matched_path_fraction=sum(physical)/paths,
                initial_true_column_recall=sum(len(t&s) for t,s in zip(true_columns,initial))/true_total,
                initial_plus_pool_true_column_recall=sum(len(t&(s|p)) for t,s,p in zip(true_columns,initial,first_pools))/true_total,
                mean_first_pool_size=float(np.mean(list(map(len,first_pools)))),
                diagnostic_seconds=sum(r['arms'][arm]['standalone_seconds_estimate'] for r in rows))


def analyze(rows,statuses):
    conditions = {}
    for snr in (7,8,9):
        subset = [r for r in rows if r['snr']==snr]
        conditions[str(snr)] = dict(
            pooled={a:summarize(subset,a) for a in ARMS},
            replicates={str(rep):{a:summarize([r for r in subset if r['replicate']==rep],a) for a in ARMS}
                        for rep in range(3)})
        for arm in ARMS:
            values=[conditions[str(snr)]['replicates'][str(rep)][arm]['fer'] for rep in range(3)]
            conditions[str(snr)]['pooled'][arm].update(seed_fer_mean=float(np.mean(values)),
                                                      seed_fer_std=float(np.std(values,ddof=1)))
    cases = {}
    for arm in ARMS[1:]:
        categorized = {'beneficial':[],'harmful':[],'uncorrected':[]}
        for r in rows:
            ref,alt = r['arms']['baseline'],r['arms'][arm]
            tag = ('beneficial' if alt['info_errors']<ref['info_errors'] else
                   'harmful' if alt['info_errors']>ref['info_errors'] else
                   'uncorrected' if alt['info_errors']>0 else None)
            if tag:
                categorized[tag].append(dict(snr=r['snr'],replicate=r['replicate'],frame=r['frame_index'],
                                            input_hashes=r['input_hashes'],baseline=ref,intervention=alt))
        cases[arm]={k:dict(total=len(v),examples=v[:3],insufficient_examples=len(v)<3) for k,v in categorized.items()}
    return dict(scope='exploratory paired diagnostics; not confirmatory improvement',
                snr_frame_records=len(rows),independent_exogenous_frames=192,
                no_cross_snr_independence_assumed=True,conditions=conditions,cases=cases,
                formal_G1_passed=False,formal_G2_passed=False,
                limitations=['legacy expanded-entry oracle capacity','oracle arms are not deployable',
                             'physical matching is to integer atoms, not uniquely identifiable path gains',
                             'CI is marginal exact FER; no RR coverage or simultaneous claim',
                             'parallel instrumented times are resource accounting only'],
                provenance=[{k:s[k] for k in ('checkpoint_sha256','ldpc_sha256','calibration_sha256','device','config','elapsed_seconds')} for s in statuses])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    rows,statuses=read_matrix(args.base)
    result=analyze(rows,statuses)
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'bottleneck-table.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    lines=['# S2 开发诊断','', '192组独立外生帧 × 3 SNR；仅探索，不通过G1/G2。','',
           '| SNR | Arm | FER (errors/192) | RR vs A2 | FER wins/harms | Mean active atoms |',
           '|---|---|---|---|---|---|']
    for snr,condition in result['conditions'].items():
        for arm,r in condition['pooled'].items():
            ratio='undefined' if r['fer_ratio'] is None else f"{r['fer_ratio']:.3f}"
            t=r['paired_table']
            lines.append(f"| {snr} | {arm} | {r['fer']:.4f} ({r['frame_errors']}/192) | {ratio} | {t['n01']}/{t['n10']} | {r['mean_active_atoms']:.1f} |")
    (args.out/'bottleneck-table.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__=='__main__':
    main()
