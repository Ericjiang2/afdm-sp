"""Summarize previously bound states; exploratory association is not causation."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact, rankdata


OUT = Path(__file__).resolve().parent
BASE = OUT.parents[2]


def stats(values):
    a = np.asarray(values, float)
    return {'n': len(a), 'min': float(a.min()), 'median': float(np.median(a)),
            'mean': float(a.mean()), 'p95': float(np.quantile(a, .95)), 'max': float(a.max())}


def association(values, error):
    values, error = np.asarray(values, float), np.asarray(error, bool)
    n1, n0 = int(error.sum()), int((~error).sum())
    auc = float((rankdata(values)[error].sum() - n1*(n1+1)/2)/(n1*n0)) if n1 and n0 else None
    return {'errors': n1, 'correct': n0, 'auc_high_value_predicts_error': auc,
            'error_values': stats(values[error]) if n1 else None,
            'correct_values': stats(values[~error]) if n0 else None,
            'status': 'posthoc descriptive; no threshold selected, no out-of-sample validation'}


def main():
    path = OUT/'archived_population_diagnostics.json'
    d = json.loads(path.read_text())
    rows = d['rows']
    assert len(rows) == d['full_denominator'] == d['complete_rows'] == 1024
    assert [r['frame'] for r in rows] == list(range(1024))
    stage_path=BASE/'results/cstate_necessity_stageA_20260928/analysis/frame_outcomes.csv'
    stage={r['observation_id']:r for r in csv.DictReader(stage_path.open())}
    for row in rows:
        for arm in ('A','C'):
            assert row['arms'][arm]['rounds']['1']['labels']['decoded_coded_errors']==int(stage[row['observation_id']][arm+'_coded_errors'])
    errors = {key:np.array([int(stage[r['observation_id']][key+'_info_correct'])==0 for r in rows]) for key in ('A','B','C','D')}
    physical={}
    for field in ('same_delay_pair_count','pairs_gap_le_025','pairs_gap_le_05','pairs_gap_le_1'):
        present=np.array([r['physical_geometry'][field]>0 for r in rows])
        groups={}
        for arm in ('A','B','C'):
            e=errors[arm]
            table=[[int((present&e).sum()),int((present&~e).sum())],
                   [int((~present&e).sum()),int((~present&~e).sum())]]
            groups[arm]={'present_errors':table[0][0],'present_n':int(present.sum()),
                         'absent_errors':table[1][0],'absent_n':int((~present).sum()),
                         'fisher_two_sided_p':float(fisher_exact(table).pvalue)}
        physical[field]={'frames':int(present.sum()),'fraction':float(present.mean()),'outcomes':groups}
    estimated={}
    closure_summary={}
    mode_coverage={}
    for arm in ('A','C'):
        estimated[arm]={}
        closure_summary[arm]={}
        for round_id in ('0','1'):
            entries=[r['arms'][arm]['rounds'][round_id] for r in rows]
            estimated[arm][round_id]={field:sum(r['geometry'][field]>0 for r in entries)
                                      for field in ('same_delay_pair_count','pairs_gap_le_025','pairs_gap_le_05','pairs_gap_le_1')}
            closure_summary[arm][round_id]={field:{'all':stats([r['closure'][field] for r in entries]),
                                                      'native_error_association':association([r['closure'][field] for r in entries],errors[arm])}
                                                    for field in ('nonscalar_fro_ratio','directional_eh_over_sh')}
        first={r['observation_id'] for r in rows if r['arms'][arm]['rounds']['0']['labels']['decoded_coded_errors']==0}
        final={r['observation_id'] for r in rows if r['arms'][arm]['rounds']['1']['labels']['decoded_coded_errors']==0}
        app={r['observation_id'] for r in rows if any(r['arms'][arm]['rounds'][q]['labels']['app_hard_coded_errors']==0 for q in ('0','1'))}
        mode_coverage[arm]={'round0_correct':len(first),'round1_correct':len(final),
                            'round0_only_correct':len(first-final),'round1_only_correct':len(final-first),
                            'either_round_oracle_correct':len(first|final),
                            'either_round_plus_app_hard_oracle_correct':len(first|final|app),
                            'additional_vs_round1':len((first|final|app)-final),
                            'qualifier':'Only two already saved single-word decisions and APP signs; no OSD/list/multimode bank was saved.'}
    result={'schema':'afdm-innovation-diagnostics-summary/1',
            'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'source_rows':1024,'receiver_calls':0,'missing_observations':0,
            'physical_collision':physical,'estimated_geometry':estimated,
            'closure':closure_summary,'existing_decision_coverage':mode_coverage,
            'missing_metrics':{
                'actual_TF_iteration_JVP_or_state_defect':'not saved; ce_gamma and ce_gains are CE-stage quantities, not TF-state perturbations',
                'posterior_multi_codeword_geometry_coverage':'no candidate list, normalized mode weights, or joint mode truth coverage in this raw schema',
                'near_collision_causal_effect':'observational old cohort, no randomized intervention or frozen capture threshold',
                'population_F1_LOCAL_time':'only 12 trigger branch calls, not a complete independent timed population arm'},
            'scientific_scope':'Exploratory old-population association; significance descriptive, no multiplicity-adjusted confirmation.'}
    (OUT/'archived_diagnostics_summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='closure'},indent=2))
    for arm in ('A','C'):
        for q in ('0','1'):
            for metric,v in closure_summary[arm][q].items():
                print(arm,q,metric,v['all'],'AUC',v['native_error_association']['auc_high_value_predicts_error'])


if __name__=='__main__':
    main()
