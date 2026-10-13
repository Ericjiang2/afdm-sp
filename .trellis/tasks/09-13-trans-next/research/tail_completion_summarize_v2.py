"""Local, reproducible synthesis of frozen TAIL v2 rows; no raw receiver run."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

import numpy as np

ARMS=('oracle_true_core_mixed_true_centre',
      'oracle_actual_core_mixed_true_centre',
      'deploy_actual_core_actual_centre')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,text):
    if not ok:raise ValueError(text)


def arm_stats(rows,arm,t):
    a=[r for r in rows if r['arm']==arm and r['t']==t]
    need(len(a)==64,'arm/t work-point inventory differs')
    out={}
    for label,prefix in (('H','H_NMSE'),('response','response_NMSE')):
        baseline=float(np.mean([r['scores'][prefix+'_baseline'] for r in a]))
        completed=float(np.mean([r['scores'][prefix+'_completed'] for r in a]))
        delta=completed-baseline
        out[label]=dict(baseline_mean=baseline,completed_mean=completed,
                        delta_mean=delta,relative_reduction_of_means=(baseline-completed)/baseline,
                        comparisons_better=sum(r['scores'][label+'_delta']<0 for r in a),
                        comparisons_worse=sum(r['scores'][label+'_delta']>0 for r in a))
    return out


def legal_endpoints(rows):
    idx={(r['block'],r['snr'],r['t']):r for r in rows if r['arm']==ARMS[2]}
    need(len(idx)==128,'legal endpoint inventory differs')
    values=np.empty((32,4))
    keys=((1,'H_delta'),(1,'response_delta'),(9,'H_delta'),(9,'response_delta'))
    for b in range(32):
        for j,(t,key) in enumerate(keys):
            values[b,j]=(idx[b,7,t]['scores'][key]+idx[b,8,t]['scores'][key])/2
    rng=np.random.default_rng(202609150701)
    draw=rng.integers(0,32,size=(20000,32))
    boot=values[draw].mean(axis=1)
    names=('t1_H','t1_response','t9_H','t9_response')
    return {n:dict(mean=float(values[:,j].mean()),
                   simultaneous_95_percentile=[float(v) for v in np.quantile(boot[:,j],[.00625,.99375])])
            for j,n in enumerate(names)}


def coverage_and_finite_geometry(rows,t):
    legal=[r for r in rows if r['arm']==ARMS[2] and r['t']==t]
    need(len(legal)==64,'coverage work-point inventory differs')
    core=collections.Counter()
    potential_shifts=[]
    for r in legal:
        core.update(r['core_count_per_selected_delay'].values())
        delays=[int(x) for x in r['core_count_per_selected_delay']]
        # S union T contains all k=-5..5 for precisely these selected delays.
        potential_shifts.append(len({(5*l+k)%1024 for l in delays for k in range(-5,6)}))
    counts={key:sum(r['mixed_oracle_coverage'][key] for r in rows
                    if r['arm']==ARMS[1] and r['t']==t)
            for key in ('unique','missing','multi','replaced')}
    hits=sum(r['actual_centre_hits_on_unique_true_delays'] for r in legal)
    need(hits==counts['unique']-counts['replaced'],'actual centre hit count differs')
    def distribution(name):
        v=np.array([r[name] for r in legal],dtype=float)
        return dict(mean=float(v.mean()),median=float(np.median(v)),
                    minimum=float(v.min()),maximum=float(v.max()))
    return dict(selected_delay_core_count_occurrences={str(k):int(v) for k,v in sorted(core.items())},
        selected_delay_occurrences=int(sum(core.values())),
        mixed_oracle_coverage=counts,
        actual_centre_hits_on_unique_true_delays=hits,
        actual_centre_hit_fraction_on_unique_true_delays=hits/counts['unique'],
        projection_residual_S=distribution('projection_residual_S'),
        projection_residual_S_union_T=distribution('projection_residual_S_union_T'),
        finite_tail_coverable_energy=distribution('finite_tail_coverable_energy'),
        new_tail_atoms=distribution('T_atoms'),
        new_nonzero_tail_atoms=distribution('nonzero_tail_atoms'),
        saved_A_relative_reconstruction_error=distribution('saved_A_relative_reconstruction_error'),
        saved_lifecycle_H_vs_current_core_action_relative=distribution('saved_lifecycle_H_vs_current_core_action_relative'),
        completed_possible_unique_row_shifts=dict(mean=float(np.mean(potential_shifts)),
            minimum=int(min(potential_shifts)),maximum=int(max(potential_shifts))),
        completed_possible_H_matrix_positions_mean=float(np.mean(potential_shifts))*1024,
        new_tail_atom_entry_contributions_mean=distribution('T_atoms')['mean']*1024,
        edge_scope='completed possible H positions from distinct shifts; original S all k and actual detector graph not in saved rows, so exact incremental/detection edges unmeasured')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ce-root',type=Path,required=True)
    p.add_argument('--research-dir',type=Path,required=True)
    a=p.parse_args();ce=a.ce_root;r=a.research_dir
    out=ce/'runs/tail-completion-v2'
    rows=json.loads((out/'rows.json').read_text())
    summ=json.loads((out/'summary.json').read_text())
    audit=json.loads((out/'raw-audit.json').read_text())
    admission=json.loads((out/'engineering-admission.json').read_text())
    engineering=json.loads((out/'engineering-rows.json').read_text())
    v1=json.loads((ce/'evidence/tail-completion-v1-exit.json').read_text())
    v2=json.loads((ce/'evidence/tail-completion-v2-exit.json').read_text())
    contract=json.loads((r/'tail_completion_contract_v2.json').read_text())
    need(summ['status']=='COMPLETE' and audit['status']=='PASS'
         and admission['status']=='PASS' and v1['exit_code']==1
         and v2['exit_code']==0 and not v2['timed_out'],
         'run/audit/admission/supervisor status differs')
    need(sha(out/'summary.json')==audit['summary_sha256']
         and sha(out/'rows.json')==audit['rows_sha256']==summ['rows_sha256']
         and sha(out/'engineering-rows.json')==admission['rows_sha256']
         and rows[:24]==engineering and len(rows)==384 and len(engineering)==24,
         'raw/engineering rows hash or inventory differs')
    need(sha(r/'tail_completion_v2.py')==summ['script_sha256']
         and sha(r/'tail_completion_contract_v2.json')==summ['contract_sha256']
         and sha(ce/'evidence/tail-completion-v1-exit.json')
             ==contract['v1_failed_engineering_attempt']['supervisor_exit_sha256'],
         'frozen method/failed attempt SHA differs')
    need({(x['block'],x['snr'],x['t'],x['arm']) for x in rows}
         =={(b,s,t,arm) for b in range(32) for s in (7,8)
            for t in (1,9) for arm in ARMS},
         '384 layer-internal pair inventory differs')
    for x in rows:
        z=x['scores']
        for prefix,key in (('H_NMSE','H_delta'),('response_NMSE','response_delta')):
            need(abs(z[prefix+'_completed']-z[prefix+'_baseline']-z[key])<=1e-12,
                 'saved paired score does not close')
    idx={(x['block'],x['snr'],x['t'],x['arm']):x for x in rows}
    for b in range(32):
        for s in (7,8):
            for t in (1,9):
                actual=idx[b,s,t,ARMS[2]];mixed=idx[b,s,t,ARMS[1]]
                need(actual['used_core_sha256']==mixed['used_core_sha256']
                     and all(abs(actual['scores'][name]-mixed['scores'][name])<=1e-12
                     for name in ('H_NMSE_baseline','response_NMSE_baseline')),
                     'actual-core oracle/legitimate baseline changed core')
                oracle=idx[b,s,t,ARMS[0]]
                need(abs(oracle['scores']['H_NMSE_baseline']-oracle['projection_residual_S'])<=1e-12,
                     'true-core own F=0 baseline differs from original S projection')
    endpoints=legal_endpoints(rows)
    need(all(abs(endpoints[k]['mean']-summ['legal_four_endpoints'][k]['mean'])<=1e-12
             and np.allclose(endpoints[k]['simultaneous_95_percentile'],
                             summ['legal_four_endpoints'][k]['simultaneous_95_percentile'],
                             rtol=0,atol=1e-12) for k in endpoints),
         'independent local 32-cluster endpoint recomputation differs')
    detail={arm:{str(t):arm_stats(rows,arm,t) for t in (1,9)} for arm in ARMS}
    coverage={str(t):coverage_and_finite_geometry(rows,t) for t in (1,9)}
    calls=summ['calls'];again=audit['reread_calls']
    need(calls==again and calls['score_pairs']==384 and calls['F_matrix_solves']==39,
         'producer/self-audit actual math call meter differs')
    result=dict(schema='tail-completion-results-v2',status='COMPLETE_SAME_PROCESS_RAW_AUDIT_PASS',
        source_binding=summ['input_binding'],
        artifact_hashes=dict(rows_sha256=sha(out/'rows.json'),summary_sha256=sha(out/'summary.json'),
                             raw_audit_sha256=sha(out/'raw-audit.json'),
                             engineering_admission_sha256=sha(out/'engineering-admission.json')),
        three_layer_by_t=detail,legal_four_32cluster_endpoints=endpoints,
        coverage_and_finite_geometry=coverage,
        accounting=dict(v1_failed_supervisor_wall_seconds=v1['wall_seconds'],
            v2_pass_supervisor_wall_seconds=v2['wall_seconds'],
            total_attempt_supervisor_wall_seconds=v1['wall_seconds']+v2['wall_seconds'],
            v1_failed_before_pair_count=0,v1_before_guard_A_F_reads=[1,1],
            v2_producer_wall_seconds=summ['wall_seconds'],
            v2_self_audit_additional_wall_seconds=audit['total_wall_seconds']-summ['wall_seconds'],
            producer_calls=calls,self_audit_recomputation_calls=again,
            actual_F_matrix_solves_all=78,mathematical_pair_evaluations_all=768,
            new_receiver_F_CE_BP_LDPC=[0,0,0,0],
            peak_resident_bytes=summ['peak_resident_bytes']),
        inference='exposed 32 G1 development physical channels, finite same-delay W5, nominal q=.01; legal H/true-noiseless-response risk only, no FER, deployment, independent CONF or detector BP cost',
        summary_script_sha256=sha(__file__))
    jp=r/'tail-completion-results-v2.json';jp.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'json':str(jp),'endpoints':endpoints,'wall_seconds':result['accounting']['total_attempt_supervisor_wall_seconds']}))


if __name__=='__main__':main()
