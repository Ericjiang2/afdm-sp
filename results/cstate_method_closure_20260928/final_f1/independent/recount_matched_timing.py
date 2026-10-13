import json, math, hashlib, pathlib, subprocess, sys
from itertools import permutations
import numpy as np

base=pathlib.Path('results/cstate_method_closure_20260928/final_f1')
obs=base/'observed_matched64_v1'
ana=base/'analysis_matched64_v2'
paths={
    'observed_seal':obs/'observed_seal.json',
    'manifest':obs/'manifest.json',
    'attempts':obs/'attempts.jsonl',
    'ledger':obs/'ledger.jsonl',
    'primary_report':ana/'report.json',
    'producer_source':pathlib.Path('experiments/cstate_method_closure_20260928/final_f1/f1_matched_timing.py'),
}
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p): return sha_bytes(p.read_bytes())
def jl(p): return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]

seal=json.loads(paths['observed_seal'].read_text())
manifest=json.loads(paths['manifest'].read_text())
attempts=jl(paths['attempts'])
ledger=jl(paths['ledger'])
primary=json.loads(paths['primary_report'].read_text())
ids=manifest['observation_ids']
arms=('F0','Cref','Ccompat')
metrics=('acquisition_seconds','complete_latency_seconds','decision_record_seconds','decoder_seconds','native_seconds','raw_serialization_seconds','refit_seconds','tf_seconds')
checks={
    'seal_schema_and_pass':seal.get('schema')=='f1-final-matched64-timing/1' and seal.get('status')=='pass',
    'manifest_schema':manifest.get('schema')=='f1-final-matched64-timing/1',
    'manifest_expected_calls':manifest.get('expected_calls')==192,
    'manifest_64_unique_ids':len(ids)==64 and len(set(ids))==64,
    'ledger_192_rows':len(ledger)==192,
    'attempts_192_rows':len(attempts)==192,
    'all_ledger_ok':all(r.get('status')=='ok' for r in ledger),
    'all_receiver_started':all(r.get('receiver_started') is True for r in ledger),
    'ledger_attempt_indices_1_to_192':[r.get('attempt_index') for r in ledger]==list(range(1,193)),
    'attempt_log_indices_1_to_192':[r.get('attempt_index') for r in attempts]==list(range(1,193)),
    'attempts_match_ledger_order':all((a.get('attempt_index'),a.get('observation_id'),a.get('arm'))==(r.get('attempt_index'),r.get('observation_id'),r.get('arm')) for a,r in zip(attempts,ledger)),
    'branch_policy_no_cstate':manifest.get('branch_policy')=='F0 only, no CSTATE; F1 arms have no branch',
    'exact_arm_set':set(r.get('arm') for r in ledger)==set(arms),
    'primary_schema_pass':primary.get('schema')=='f1-final-matched64-timing-analysis/1' and primary.get('status')=='pass',
    'primary_count_binding':primary.get('matched_frames')==64 and primary.get('paid_calls')==192,
}
by_id={oid:[] for oid in ids}
for row in ledger:
    if row.get('observation_id') in by_id:
        by_id[row['observation_id']].append(row)
checks['all_64_manifest_frames_once']=all(len(rows)==3 for rows in by_id.values()) and all(row.get('observation_id') in by_id for row in ledger)
checks['each_frame_exactly_3_arms']=all({r.get('arm') for r in rows}==set(arms) and len(rows)==3 for rows in by_id.values())
checks['paired_input_and_observation_hashes']=all(len({r.get('input_sha256') for r in rows})==1 and len({r.get('observation_hash') for r in rows})==1 for rows in by_id.values())
checks['ledger_groups_follow_manifest_order']=[r['observation_id'] for r in ledger[::3]]==ids and all(len({r['observation_id'] for r in ledger[i:i+3]})==1 for i in range(0,192,3))
# Frozen source defines counterbalanced order as itertools.permutations(ARMS)[ordinal % 6].
source_sha=sha(paths['producer_source'])
source_expected=manifest.get('source_hashes',{}).get('f1_matched_timing.py')
checks['producer_schedule_source_hash_matches_manifest']=source_sha==source_expected
schedule=tuple(permutations(arms))
actual_orders=[tuple(r['arm'] for r in by_id[oid]) for oid in ids]
expected_orders=[schedule[i%6] for i in range(64)]
checks['counterbalanced_schedule_matches_frozen_source']=actual_orders==expected_orders
checks['all_timing_values_finite_nonnegative']=all(math.isfinite(float(r[m])) and float(r[m])>=0 for r in ledger for m in metrics)

def summary(values):
    a=np.asarray(values,dtype=np.float64)
    return {'n':int(a.size),'min':float(np.min(a)),'max':float(np.max(a)),'mean':float(np.mean(a)),'median':float(np.median(a)),'p95':float(np.quantile(a,.95)),'p99':float(np.quantile(a,.99))}

arm_rows={arm:[r for r in ledger if r['arm']==arm] for arm in arms}
arm_stats={arm:{metric:summary([r[metric] for r in arm_rows[arm]]) for metric in metrics} for arm in arms}
pair_defs={'Ccompat_minus_F0':('Ccompat','F0'),'Cref_minus_Ccompat':('Cref','Ccompat'),'Cref_minus_F0':('Cref','F0')}
pair_stats={}
for label,(left,right) in pair_defs.items():
    lm={r['observation_id']:r for r in arm_rows[left]}
    rm={r['observation_id']:r for r in arm_rows[right]}
    assert set(lm)==set(rm)==set(ids)
    pair_stats[label]={metric:summary([float(lm[oid][metric])-float(rm[oid][metric]) for oid in ids]) for metric in ('acquisition_seconds','complete_latency_seconds')}
means={arm:{metric:arm_stats[arm][metric]['mean'] for metric in ('acquisition_seconds','complete_latency_seconds')} for arm in arms}
ratios={
    'acquisition_excess_seconds':means['Cref']['acquisition_seconds']-means['F0']['acquisition_seconds'],
    'complete_latency_reduction_fraction':(means['Cref']['complete_latency_seconds']-means['Ccompat']['complete_latency_seconds'])/means['Cref']['complete_latency_seconds'],
    'removable_acquisition_fraction':(means['Cref']['acquisition_seconds']-means['Ccompat']['acquisition_seconds'])/(means['Cref']['acquisition_seconds']-means['F0']['acquisition_seconds']),
    'remaining_measured_acquisition_fraction':(means['Ccompat']['acquisition_seconds']-means['F0']['acquisition_seconds'])/(means['Cref']['acquisition_seconds']-means['F0']['acquisition_seconds']),
}
actual={'arm_timing':arm_stats,'paired_differences':pair_stats,**ratios}
expected={'arm_timing':primary['arm_timing'],'paired_differences':primary['paired_differences'],**{k:primary[k] for k in ratios}}
diffs=[]
def compare(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b:
                diffs.append({'path':f'{path}.{k}'.strip('.'),'kind':'missing_key','independent_present':k in a,'primary_present':k in b})
            else:
                compare(a[k],b[k],f'{path}.{k}'.strip('.'))
    elif isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
        delta=float(a)-float(b)
        if delta!=0.0:
            diffs.append({'path':path,'independent':a,'primary':b,'delta':delta,'abs_delta':abs(delta)})
    elif a!=b:
        diffs.append({'path':path,'independent':a,'primary':b,'kind':'value_mismatch'})
compare(actual,expected)
maxdelta=max((x.get('abs_delta',0.0) for x in diffs),default=0.0)
local_hash={name:sha(path) for name,path in paths.items() if name!='producer_source'}
obs_commit='09abb05632a682176954250b783b787a5cfdddac'
primary_commit='2f81d00514508d938202c1dfef2fb4026a2a1a40'
repo=pathlib.Path('.').resolve().parents[1]
relroot='00_Inbox/AFDM-channel-estimation/'
def gitblob(commit,rel):
    q=subprocess.run(['git','show',f'{commit}:{relroot}{rel}'],cwd=str(repo),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return {'returncode':q.returncode,'sha256':sha_bytes(q.stdout) if q.returncode==0 else None}
anc=subprocess.run(['git','merge-base','--is-ancestor',obs_commit,primary_commit],cwd=str(repo))
git={
    'observed_commit_is_primary_ancestor':anc.returncode==0,
    'observed_seal_blob':gitblob(obs_commit,'results/cstate_method_closure_20260928/final_f1/observed_matched64_v1/observed_seal.json'),
    'primary_report_blob':gitblob(primary_commit,'results/cstate_method_closure_20260928/final_f1/analysis_matched64_v2/report.json'),
}
git['seal_blob_matches_local']=git['observed_seal_blob']['sha256']==local_hash['observed_seal']
git['report_blob_matches_local']=git['primary_report_blob']['sha256']==local_hash['primary_report']
checks['expected_observed_seal_sha']=local_hash['observed_seal']=='765fb8147fd20ba4673681578716656ea1f030138bcbfa45f160d5791283a6a4'
checks['expected_primary_report_sha']=local_hash['primary_report']=='bbe31f2f117932555e59bec54825a5af88b3e53a63b47b5c4360c9af018793af'
checks['primary_binds_observed_commit_and_seal']=primary.get('observed_commit')==obs_commit and primary.get('observed_seal_sha256')==local_hash['observed_seal']
checks['git_lineage_and_blob_matches']=git['observed_commit_is_primary_ancestor'] and git['seal_blob_matches_local'] and git['report_blob_matches_local']
order_counts={','.join(order):actual_orders.count(order) for order in schedule}
receipt={
    'schema':'f1-matched64-independent-timing-recount/1',
    'status':'pass' if all(checks.values()) else 'fail',
    'scope':'Independent arithmetic over sealed timing ledger rows for 64 archived frames x 3 arms; no raw NPZ, truth, receiver, or decoder access.',
    'observed_git_commit':obs_commit,
    'primary_git_commit':primary_commit,
    'local_input_sha256':local_hash,
    'producer_schedule_source_sha256':source_sha,
    'environment':{'python':sys.version.split()[0],'numpy':np.__version__},
    'counts':{'ledger_rows':len(ledger),'attempt_rows':len(attempts),'frames':len(ids),'rows_per_arm':{arm:len(arm_rows[arm]) for arm in arms},'receiver_started_rows':sum(r.get('receiver_started') is True for r in ledger)},
    'schedule':{'expected':'itertools.permutations((F0,Cref,Ccompat))[frame_ordinal % 6]','order_counts':order_counts,'arm_set':list(arms),'branch_policy':manifest.get('branch_policy'),'all_64_frame_groups_match':checks['counterbalanced_schedule_matches_frozen_source'],'frame_ids':ids},
    'checks':checks,
    'git_checks':git,
    'independent_arm_timing':arm_stats,
    'independent_paired_differences':pair_stats,
    'independent_ratios':ratios,
    'primary_comparison':{'numeric_paths_compared':214,'exact_equal':len(diffs)==0,'difference_count':len(diffs),'maximum_absolute_numeric_delta':maxdelta,'all_nonzero_differences':diffs},
    'reader_assumption_note':'An initial local check incorrectly required identical arm order per frame. Frozen producer source defines six counterbalanced permutations; the final check validates each of the 64 ordinals against that source schedule.',
    'limitations':['This recount aggregates saved ledger timing values; it does not independently re-open raw/checkpoint artifacts.','No truth or FER/BER scoring was read or recalculated.','All nonzero differences against the frozen primary are recorded exactly; zero differences are reported as exact equality.'],
}
out=base/'independent'/'TIMING_RECOUNT.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'output':str(out),'checks':checks,'difference_count':len(diffs),'maximum_absolute_delta':maxdelta},indent=2))
