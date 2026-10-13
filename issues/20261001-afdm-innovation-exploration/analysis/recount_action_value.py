"""Recount paired archived decisions and costs; oracle labels are analysis-only."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import statistics


BASE = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
F2 = BASE / 'results/cstate_necessity_stageB_resume_20260928'
A = BASE / 'results/cstate_necessity_stageA_20260928'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    return list(csv.DictReader(path.open()))


def main():
    table_path = F2/'population_five_analysis_v2/frame_outcomes.csv'
    deadline_path = F2/'population_five_analysis_v2/deadline_decisions.csv'
    policy_path = F2/'population_five_v1/policy_ledger.jsonl'
    seal_path = F2/'population_five_v1/observed_seal.json'
    table = read_csv(table_path)
    policies = [json.loads(x) for x in policy_path.read_text().splitlines()]
    seal = json.loads(seal_path.read_text())
    assert seal['status'] == 'pass' and seal['files']['policy_ledger.jsonl'] == sha(policy_path)
    index = {(r['observation_id'],r['arm_or_policy']):r for r in table}
    ledger = {(r['observation_id'],r['policy']):r for r in policies}
    assert len(table) == len(index) == len(policies) == len(ledger) == 5120
    arms = ('F0','F0_LOCAL','B','F2T','F2E')
    ids = [f's650_f{i:04d}' for i in range(1024)]
    stage = {r['observation_id']:r for r in read_csv(A/'analysis/frame_outcomes.csv')}
    stage_rows = [json.loads(x) for x in (A/'observed/ledger.jsonl').read_text().splitlines()]
    stage_ledger = {(r['observation_id'],r['arm']):r for r in stage_rows}
    stage_seal = json.loads((A/'observed/observed_seal.json').read_text())
    assert stage_seal['files']['ledger.jsonl'] == sha(A/'observed/ledger.jsonl')
    for stem in ids:
        assert len({ledger[stem,arm]['input_sha256'] for arm in arms}) == 1
        assert ledger[stem,'F0']['input_sha256'] == stage_ledger[stem,'A']['input_sha256']
        for arm in arms:
            r, l = index[stem,arm], ledger[stem,arm]
            assert l['status'] == 'ok'
            assert int(r['syndrome_weight']) == l['final_syndrome_weight']
            assert r['valid_but_wrong'] == 'False'
            assert (r['info_correct'] == 'True') == (int(r['coded_errors']) == 0)
        for old,new in [('A','F0'),('B','B')]:
            assert int(stage[stem][old+'_info_correct']) == int(index[stem,new]['info_correct']=='True')
            assert stage_ledger[stem,old]['final_decoded_sha256'] == ledger[stem,new]['final_decoded_sha256']

    correct = {arm:{stem for stem in ids if index[stem,arm]['info_correct']=='True'} for arm in arms}
    metrics = {arm:{'n':1024,'correct':len(correct[arm]),'errors':1024-len(correct[arm]),
                    'fer':(1024-len(correct[arm]))/1024,
                    'mean_complete_seconds':statistics.mean(ledger[s,arm]['complete_latency_seconds'] for s in ids)}
               for arm in arms}
    pairs = []
    for left,right in itertools.combinations(arms,2):
        pairs.append({'left':left,'right':right,'left_only':len(correct[left]-correct[right]),
                      'right_only':len(correct[right]-correct[left]),
                      'both_wrong':1024-len(correct[left]|correct[right])})
    current = ('F0','F0_LOCAL','B')
    success_union = set().union(*(correct[a] for a in current))
    assert success_union == correct['B']
    # Perfect label-aware choice among independently measured logical policies.
    # This is not implementable online and excludes any gate/feature cost.
    chosen=[]
    for stem in ids:
        admissible=[a for a in current if stem in correct[a]] or list(current)
        winner=min(admissible,key=lambda a:ledger[stem,a]['complete_latency_seconds'])
        chosen.append({'observation_id':stem,'oracle_action':winner,
                       'correct':stem in correct[winner],
                       'seconds':ledger[stem,winner]['complete_latency_seconds']})
    deadlines = read_csv(deadline_path)
    assert len(deadlines) == 10240
    deadline_index={(r['observation_id'],r['arm_or_policy'],r['deadline_seconds']):r for r in deadlines}
    deadline_oracles=[]
    for deadline in ('0.5','1.0'):
        sets={a:{s for s in ids if deadline_index[s,a,deadline]['ready']=='True' and
                 deadline_index[s,a,deadline]['correct']=='True'} for a in current}
        union=set().union(*sets.values())
        deadline_oracles.append({'deadline_seconds':float(deadline),
                                 'individual_correct':{a:len(x) for a,x in sets.items()},
                                 'oracle_correct':len(union),'oracle_extra_vs_B':len(union-sets['B']),
                                 'oracle_missing_or_wrong':1024-len(union)})
    f1_trigger=[r for r in stage.values() if int(r['C_final_syndrome_weight'])!=0]
    assert len(f1_trigger)==12 and all(int(r['E_run'])==1 for r in f1_trigger)
    f1={'n':1024,'F1_errors':sum(int(r['C_info_correct'])==0 for r in stage.values()),
        'F1_CSTATE_errors':sum(int(r['D_info_correct'])==0 for r in stage.values()),
        'LOCAL_trigger_count':len(f1_trigger),
        'LOCAL_trigger_correct':sum(int(r['E_info_correct']) for r in f1_trigger),
        'LOCAL_population_timed_arm':False}
    source_paths=[table_path,deadline_path,policy_path,seal_path,A/'analysis/frame_outcomes.csv',
                  A/'observed/ledger.jsonl',A/'observed/observed_seal.json']
    result={'schema':'afdm-archived-action-value/1','receiver_calls':0,
            'evidence_class':'paired old exposed developmental labels; no new receiver execution',
            'source_hashes':{str(p.relative_to(BASE)):sha(p) for p in source_paths},
            'binding':'all 5120 policies share per-frame input SHA; F0/B decoded SHA equal Stage-A A/B',
            'metrics':metrics,'pairs':pairs,'current_family':list(current),
            'final_oracle':{'errors':1024-len(success_union),'extra_correct_vs_B':0,
                            'mean_complete_seconds_excluding_selection_cost':statistics.mean(r['seconds'] for r in chosen),
                            'action_counts':{a:sum(r['oracle_action']==a for r in chosen) for a in current},
                            'failure_ids':sorted(set(ids)-success_union)},
            'deadline_oracles':deadline_oracles,'F1':f1,
            'deployable_policy':{'name':'native nonzero syndrome -> CSTATE, otherwise STOP',
                                  'same_as_B':True,'oracle_labels_used':False,
                                  'additional_gate_trained':False},
            'limitations':['Outcome counts are recomputed from saved analysis CSV; original raw-to-truth recount exists in prior independent receipt.',
                           'No new learned/risk threshold gate is fitted on exposed labels.',
                           'Oracle cost omits selection cost and knows correctness; it is not achievable evidence.',
                           'Deadline oracle switches whole logged policies; it is not a tested scheduling system.',
                           'F1 timings belong to another campaign and are not combined here.']}
    (OUT/'action_value_recount.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (OUT/'action_oracle_per_frame.json').write_text(json.dumps(chosen,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('metrics','final_oracle','deadline_oracles','F1')},indent=2))


if __name__=='__main__':
    main()
