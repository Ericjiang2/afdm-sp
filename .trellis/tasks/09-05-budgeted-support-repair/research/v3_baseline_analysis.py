"""Audit complete development families and freeze choices before holdout access."""
import argparse,collections,hashlib,json,tarfile
from pathlib import Path
import numpy as np


def records(path,marker):
    with tarfile.open(path) as t:
        return [json.load(t.extractfile(m)) for m in t.getmembers() if m.isfile() and marker in m.name and m.name.endswith('.json')]


def analyze(root):
    rows=records(root/'baseline-fit-results.tar.gz','/frame-')+records(root/'baseline-pilot-results.tar.gz','/frame-')
    assert len(rows)==1920
    groups=collections.defaultdict(list)
    for row in rows:groups[row['family'],row['parameter']].append(row)
    assert len(groups)==10 and all(len(g)==192 for g in groups.values())
    b0={(r['replicate'],r['frame_index']):r for r in groups['b0',None]}
    for key,g in groups.items():
        assert len({(r['replicate'],r['frame_index']) for r in g})==192
        for r in g:
            base=b0[r['replicate'],r['frame_index']]
            assert r['input_hashes']==base['input_hashes']
            assert r['v3_initial']['original_support']==base['v3_initial']['support']
            assert r['arms']['a0']['finite'] and not r['arms']['a0']['support_repair_enabled']
            assert len(r['arms']['a0']['bp_graphs'])==11
            assert len(r['v3_initial']['support'])<=40
            if key[0]=='ridge':assert r['v3_initial']['support']==base['v3_initial']['support']
    # Compare B0 against the complete original raw development anchor.
    old=[]
    with tarfile.open('issues/2026-09-06_13-47-38-afdm-plan-v2/evidence/fit192-runtime-validation.tar.gz') as t:
        for m in t.getmembers():
            if m.isfile() and m.name.endswith('/frames.jsonl'):old.extend(json.loads(x) for x in t.extractfile(m).read().splitlines())
    for r in old:
        new=b0[r['replicate'],r['frame_index']]
        assert r['input_hashes']==new['input_hashes']
        for field in ('output_h_sha256','sigma2_final','info_errors'):
            assert r['arms']['a0'][field]==new['arms']['a0'][field],(r['replicate'],r['frame_index'],field)
    summaries=[]
    baseline_median=float(np.median([r['arms']['a0']['standalone_seconds_estimate'] for r in groups['b0',None]]))
    for (family,param),g in groups.items():
        times=np.array([r['arms']['a0']['standalone_seconds_estimate'] for r in g])
        summary=dict(family=family,parameter=param,frames=192,wrong_frames=sum(r['FER'] for r in g),
            FER=sum(r['FER'] for r in g)/192,BER=sum(r['arms']['a0']['info_errors'] for r in g)/sum(r['information_bits'] for r in g),
            mean_seconds=float(times.mean()),median_seconds=float(np.median(times)),P95_seconds=float(np.quantile(times,.95)),
            cost_ratio_median=float(np.median(times))/baseline_median,cost_feasible=bool(np.median(times)<=3*baseline_median),
            mean_K=float(np.mean([r['initial_error']['K'] for r in g])),
            initial_nmse=float(np.mean([r['initial_error']['nmse'] for r in g])),
            missing_energy=float(np.mean([r['initial_error']['energies']['missing'] for r in g])),
            false_energy=float(np.mean([r['initial_error']['energies']['false'] for r in g])),
            weak_missing_energy=float(np.mean([r['initial_error']['weak_missing_energy'] for r in g])),
            mean_total_BP_edges=float(np.mean([sum(e['edges'] for e in r['arms']['a0']['bp_graphs']) for r in g])),
            sbl_unconverged=sum(not r['v3_initial'].get('converged',True) for r in g),failures=0)
        summaries.append(summary)
    order=lambda r:(not r['cost_feasible'],r['wrong_frames'],r['median_seconds'],r['family'],str(r['parameter']))
    selected={f:min([r for r in summaries if r['family']==f],key=order) for f in ('size','ridge','sbl')}
    strongest=min(selected.values(),key=order)
    compact=[{k:r[k] for k in ('family','parameter','replicate','frame_index','input_hashes','terminal_snapshot','FER','information_bits','v3_initial','initial_error')}|dict(arm={k:v for k,v in r['arms']['a0'].items() if k not in ('bp_graphs','capacity_trace')}) for r in rows]
    result=dict(dataset='D_fit only',frames_per_config=192,configs=10,full_receiver_calls=1920,
        all_inputs_paired=True,all_B0_hash_sigma_errors_match_history=True,all_ridge_supports_match_B0=True,
        initial_original_supports_common=True,all_11_BP_calls_recorded=True,summaries=summaries,
        selected=selected,strongest_simple=strongest,holdout_access=False,
        selection_rule='contract and 3x B0 median cost gate; FER first; median cost tie break; name last',
        source_archive_sha256=hashlib.sha256((root/'baseline-fit-results.tar.gz').read_bytes()).hexdigest())
    (root/'BASE-04-development-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    (root/'BASE-04-compact-rows.json').write_text(json.dumps(compact)+'\n')
    (root/'frozen-recipes.json').write_text(json.dumps(dict(selected=selected,strongest_simple=strongest,
        holdout_access=False,development_audit_sha256=hashlib.sha256((root/'BASE-04-development-audit.json').read_bytes()).hexdigest(),
        covariance_revision='actual coded augmented real G for COLOR only; receiver working statistics unchanged'),indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();r=analyze(a.root)
    print(json.dumps(dict(summaries=r['summaries'],selected={k:v['parameter'] for k,v in r['selected'].items()},strongest=r['strongest_simple']['family']),indent=2))
