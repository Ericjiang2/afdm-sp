"""Synthetic offline equality and cost checks; no truth or receiver runtime."""
from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent/'sp_afdm_frozen_20260920'/'src')]
import analyze_validation as analysis  # noqa: E402


def raw():
    paths = [dict(delay=2,doppler=.25),dict(delay=2,doppler=-.25)]
    step = dict(entering_paths=deepcopy(paths),
        candidate_delays=np.array([1,2]),candidate_dopplers=np.array([0.,.25]),
        valid=np.array([[True,True],[True,False]]),
        scores=np.array([[3.,2.],[4.,5.]]),
        top_k=[dict(rank=1,slot=0,replacement=dict(delay=2,doppler=.25),
                    paths=deepcopy(paths),frozen_score=2.)],
        selected=dict(rank=1,slot=0,replacement=dict(delay=2,doppler=.25),
                      paths=deepcopy(paths),frozen_score=2.),
        accepted=dict(slot=0,old=dict(delay=2,doppler=.25),
                      new=dict(delay=2,doppler=.25),
                      frozen_score=2.,direct_score=2.,decrease=1.))
    local = dict(pass_index=0,slot=0,local_phase_entering_paths=deepcopy(paths),
        start=dict(delay=2,doppler=.25),
        endpoint=dict(delay=2,doppler=.25),accepted=False,trial_count=1,
        rejected_duplicate_trials=0,
        center=.25,bounds=(-.5,1.),start_objective=2.,endpoint_objective=2.,
        trials=[dict(valid=True,doppler=.25,score=2.)])
    geometry = dict(global_trace=[step],local_trace=[local],paths=paths,
        gains=np.array([.3+.1j,.4-.1j]),objective_before=3.,
        objective_after=2.,edits=[dict(step=0,slot=0,
            old=dict(delay=2,doppler=.25),new=dict(delay=2,doppler=.25))])
    detector = {key:np.array([.1,.2]) for key in
                ('gains','mu','variance','extrinsic','app','gain_variance')}
    decoder = {key:np.array([.3,.4]) for key in
               ('incoming_llr','raw_app','raw_check_extrinsic')}
    decoder['decoded'] = np.zeros(2, np.uint8)
    return dict(geometry_result=geometry,detector=detector,decoder=decoder)


def test_exact_control_accepts_qualified_tiny_numeric_difference():
    direct, compact = raw(), raw()
    compact['geometry_result']['gains'][0] += 1e-11
    compact['geometry_result']['global_trace'][0]['scores'][0,0] += 1e-11
    compact['decoder']['raw_app'][0] += 1e-11
    assert analysis.compare_exact_control(direct,compact)['global_steps'] == 1


def test_exact_control_rejects_discrete_or_final_bit_difference():
    direct, compact = raw(), raw()
    compact['geometry_result']['edits'][0]['slot'] = 1
    with pytest.raises(ValueError,match='replacement sequence'):
        analysis.compare_exact_control(direct,compact)
    compact = raw()
    compact['decoder']['decoded'][0] = 1
    with pytest.raises(ValueError,match='final decoded bits'):
        analysis.compare_exact_control(direct,compact)


def test_exact_control_uses_qualified_absolute_tolerance_on_valid_scores():
    direct, compact = raw(), raw()
    compact['geometry_result']['global_trace'][0]['scores'][0, 0] += 3e-10
    with pytest.raises(ValueError, match='full candidate scores'):
        analysis.compare_exact_control(direct, compact)
    direct, compact = raw(), raw()
    compact['geometry_result']['global_trace'][0]['scores'][1, 1] += 1.
    analysis.compare_exact_control(direct, compact)


def test_exact_control_rejects_changed_local_trial_schedule():
    direct, compact = raw(), raw()
    compact['geometry_result']['local_trace'][0]['trials'][0]['score'] += 3e-10
    with pytest.raises(ValueError, match='local trial'):
        analysis.compare_exact_control(direct, compact)


def test_previous_final_requires_continuous_and_bit_parity():
    old, new = raw(), raw()
    analysis.compare_previous_final(old,new,'GLOBAL20')
    new['detector']['gains'][0] += 1e-8
    with pytest.raises(ValueError,match='continuous mismatch'):
        analysis.compare_previous_final(old,new,'GLOBAL20')


def test_stage_costs_are_exclusive_and_report_share():
    rows = []
    for arm in ('LOCAL20','GLOBAL20','CSTATE20'):
        for index in range(43):
            rows.append(dict(arm=arm,kind='trigger',
                added_complete_branch_seconds=2.,
                branch_exclusive_stages={name:2./len(analysis.STAGES)
                    for name in analysis.STAGES},
                setup_seconds=.1,native_two_rounds_seconds=.2,
                baseline_parity_seconds=.3,
                native_checkpoint_write_seconds=.01,
                wrapper_bookkeeping_seconds=.02))
    costs = analysis.stage_costs(rows)
    assert len(costs) == 3*(len(analysis.STAGES)+5)
    entry = next(c for c in costs if c['arm']=='CSTATE20' and c['stage']=='tf')
    assert entry['count']==43
    assert np.isclose(entry['mean_share_of_complete_branch'],1/len(analysis.STAGES))


def test_discarded_compact_cost_is_reported_as_nested_with_reason():
    rows = [dict(arm=arm, observation_id='f0', numerical_fallback=arm=='CSTATE20',
                 discarded_compact_seconds=.12 if arm=='CSTATE20' else 0.,
                 fallback_reason='ill-conditioned' if arm=='CSTATE20' else None)
            for arm in ('LOCAL20','GLOBAL20','CSTATE20')]
    summary = analysis.discarded_compact_summary(rows)
    assert summary['CSTATE20']['count'] == 1
    assert summary['CSTATE20']['seconds']['mean_seconds'] == .12
    assert summary['CSTATE20']['reasons'] == [dict(observation_id='f0',reason='ill-conditioned')]
    assert summary['CSTATE20']['nested_in_exclusive_stages'] is True
    assert summary['GLOBAL20']['count'] == 0
