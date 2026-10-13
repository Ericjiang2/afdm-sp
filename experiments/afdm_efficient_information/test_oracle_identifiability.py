"""Deterministic saved-reader contracts; fixtures are not research observations."""
import itertools
import json

import numpy as np
import pytest

from experiments.afdm_efficient_information import oracle_identifiability as module
from experiments.afdm_efficient_information.oracle_identifiability import (
    ambiguity,check_calibration,grouped_logpdf,known_eta_mle,moment_equivalence,
    np_oracle,oracle_pairs,paired_decisions,structural_status,
)


def test_oracle_pairs_match_nuisance_and_keep_original_ids():
    candidates=np.array([[0.,.1,1.],[0.,.2,1.],[.04,.1,1.],[.04,.2,1.],[.16,.1,1.],[.16,.2,1.]])
    np.testing.assert_array_equal(oracle_pairs(candidates,0.),[[0,2],[1,3],[0,4],[1,5]])
    with pytest.raises(ValueError): oracle_pairs(candidates[[0,2,3]],0.)
    with pytest.raises(ValueError): oracle_pairs(np.repeat(candidates[:1],2,axis=0),0.)


def test_saved_actual_offset_and_R_prefixes_are_explicit():
    matrix=np.arange(48.).reshape(16,3)
    slices=np.array([[100,108],[108,116]])
    one=grouped_logpdf(matrix,slices,2,4,1,100)
    four=grouped_logpdf(matrix,slices,2,4,4,100)
    np.testing.assert_array_equal(one,matrix[[0,4,8,12]].reshape(2,2,3))
    np.testing.assert_array_equal(four,matrix.reshape(2,2,4,3).sum(axis=2))
    with pytest.raises(ValueError): grouped_logpdf(matrix,slices,2,4,1,101)


def test_np_oracle_threshold_sign_and_independent_calibration_scope():
    calibration=np.column_stack([np.zeros(19),np.arange(19.)])
    null=np.array([[0.,18.],[0.,19.],[0.,-3.]])
    alternative=np.array([[0.,20.],[0.,22.],[0.,18.]])
    result,raw=np_oracle(calibration,null,alternative,0,1,.05)
    assert result['cutoff']==18. and result['rank']==19
    assert result['false_alarm']['count']==1 and result['power']['count']==2
    assert result['calibration_marginal_error_bound']==.05
    np.testing.assert_array_equal(raw['null_rejected'],[False,True,False])
    # Changing only held-out alternative values must never refit the cutoff.
    changed,_=np_oracle(calibration,null,alternative+np.array([0.,1000.]),0,1,.05)
    assert changed['cutoff']==result['cutoff']
    assert 'not an empirical upper bound' in result['scope']


def test_exchangeability_rank_bound_and_paired_group_denominators():
    rejected=[]
    for order in itertools.permutations([0.,1.,2.,3.]):
        calibration=np.column_stack([np.zeros(3),order[:3]])
        evaluation=np.array([[0.,order[3]],[0.,order[3]]])
        result,raw=np_oracle(calibration,evaluation,evaluation,0,1,.25)
        rejected.append(bool(raw['null_rejected'][0]))
    assert np.mean(rejected)==.25
    paired=paired_decisions([True,True,False,False],[True,False,True,False])
    assert [paired[x] for x in ['both_reject','oracle_only','original_only','neither']]==[1,1,1,1]
    assert paired['oracle_minus_original']['mean']==0


def test_known_eta_mle_restricts_only_labelled_oracle_not_original_grid():
    candidates=np.array([[0.,.1],[0.,.2],[.04,.1],[.04,.2]])
    logpdf=np.array([[1.,100.,2.,90.],[3.,100.,3.,90.]])
    frozen=logpdf.copy()
    result,selected,squared,allowed=known_eta_mle(logpdf,candidates,0,'q')
    np.testing.assert_array_equal(allowed,[0,2]);np.testing.assert_array_equal(selected,[2,0])
    np.testing.assert_allclose(squared,[.04,0.]);assert result['delta_rmse']==pytest.approx(np.sqrt(.02))
    np.testing.assert_array_equal(logpdf,frozen)
    # The original whole-grid argmax remains nuisance .2 and is never overwritten.
    np.testing.assert_array_equal(logpdf.argmax(axis=1),[1,1])


def test_exact_versus_machine_ties_and_target_versus_nuisance_ambiguity():
    candidates=np.array([[0.,.1],[0.,.2],[.04,.1],[.04,.2]])
    eps=np.finfo(float).eps
    objective=np.array([[0.,0.,2.,3.],[1.,2.,1.+32*eps,4.],[0.,2.,0.,4.]])
    result,raw=ambiguity(objective,candidates,objective.argmin(axis=1),64)
    np.testing.assert_array_equal(raw['exact_joint_counts'],[2,1,2])
    np.testing.assert_array_equal(raw['exact_interest_counts'],[1,1,2])
    np.testing.assert_array_equal(raw['exact_nuisance_counts'],[2,1,1])
    np.testing.assert_array_equal(raw['tolerance_interest_counts'],[1,2,2])
    assert result['exact']['joint_multiple']['count']==2
    assert result['tolerance']['interest_multiple']['count']==2
    with pytest.raises(ValueError): ambiguity(objective,candidates,[1,0,0],64)


def test_moment_polynomial_equivalence_in_precision_nullspace():
    means=np.array([[1.,0.],[1.,7.],[2.,0.]])
    precision=np.diag([1.,0.])
    result,raw=moment_equivalence(means,precision,64)
    assert result['exact_classes']==[[0,1],[2]]
    np.testing.assert_array_equal(raw['exact_class_ids'],[0,0,1])
    for observed in [np.array([.2,-3.]),np.array([4.,8.])]:
        values=np.array([(observed-m)@precision@(observed-m) for m in means])
        assert values[0]==values[1]


def test_machine_neighborhoods_are_not_closed_transitively():
    step=64*np.finfo(float).eps*.75
    result,raw=moment_equivalence(np.array([[0.],[step],[2*step]]),np.eye(1),64)
    assert result['exact_class_count']==3
    assert result['nearby_candidate_sets']==[[0,1],[0,1,2],[1,2]]
    assert raw['nearby_matrix'][0,1] and raw['nearby_matrix'][1,2] and not raw['nearby_matrix'][0,2]


def test_original_calibration_is_fully_replayed_not_refitted():
    candidates=np.array([[0.,.1],[.04,.1]])
    scores=np.array([[[0.,1.],[0.,2.],[0.,3.]],[[1.,0.],[2.,0.],[3.,0.]]])
    record=dict(detection_cutoff=0.,confidence_cutoff=0.,conditions=[
        dict(condition=0,groups=3,rank=3,confidence_cutoff=0.,null_cutoff=0.),
        dict(condition=1,groups=3,rank=3,confidence_cutoff=0.,null_cutoff=None)])
    assert check_calibration(scores,candidates,0.,.25,record,1e-10)==0.
    changed=dict(record,detection_cutoff=1.)
    with pytest.raises(ValueError): check_calibration(scores,candidates,0.,.25,changed,1e-10)


def test_physical_identifiability_is_not_inferred_from_sample_ties():
    assert structural_status('control','powers')['coordinates']==[1]
    assert structural_status('control','second_gaussian')['coordinates']==[0,1]
    assert structural_status('actual','second_gaussian')['status']=='not_established'
    assert structural_status('control','exact')['status']=='not_established'


def test_record_binding_and_raw_hash_reject_mutation(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'ARTIFACT',tmp_path)
    folder=tmp_path/'fixture';folder.mkdir()
    raw=folder/'data.json';raw.write_text('{"fixture":true}')
    reg=folder/'registration.json';reg.write_text(json.dumps(dict(git_head='fixture',config={},source_sha256={})))
    attempt=folder/'attempt.json';attempt.write_text(json.dumps(dict(status='complete',artifact_sha256={
        str(p.relative_to(tmp_path)):module.sha(p) for p in [raw,reg]})))
    bound={p.name:module.sha(p) for p in [reg,attempt]};bound['git_head']='fixture'
    reader=module.SavedStage('fixture',bound)
    assert reader.json('data.json')=={'fixture':True}
    raw.write_text('{"fixture":false}')
    with pytest.raises(ValueError): reader.json('data.json')
    attempt.write_text('{}')
    with pytest.raises(ValueError): module.SavedStage('fixture',bound)


def test_complete_reader_on_deterministic_saved_fixture_and_stable_pools(tmp_path,monkeypatch):
    """Exercise full writer/schema with artificial arrays, never a scientific run."""
    from experiments.afdm_efficient_information.inference import calibrate,evaluate_grid
    from threadpoolctl import threadpool_info
    import scipy  # Recorder imports this before freezing its pool inventory.
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'ARTIFACT',tmp_path)
    folder=tmp_path/'fixture';folder.mkdir();output=tmp_path/'output';output.mkdir()
    candidates=np.array([[0.,.1],[.04,.1]])
    cal_slices=np.array([[0,6],[6,12]]);eval_slices=np.array([[12,18],[18,24]])
    logpdf=np.column_stack([-np.linspace(0,1,24),-np.linspace(1,0,24)])
    np.savez(folder/'observations.npz',candidates=candidates,calibration_slices=cal_slices,evaluation_slices=eval_slices)
    np.savez(folder/'likelihoods.npz',exact_logpdf=logpdf)
    np.savez(folder/'bank_powers.npz',means=[[0.],[1.]],inverse=[[1.]])
    methods=['exact','powers'];rows=[];records={}
    for repeats in [1,2]:
        cal=-2*grouped_logpdf(logpdf,cal_slices,3,2,repeats,0)
        evaluation=-2*grouped_logpdf(logpdf,eval_slices,3,2,repeats,0)
        for method in methods:
            record=calibrate(cal,candidates,0.,.25);records[f'{method}_R{repeats}']=record
            np.savez(folder/f'calibration_{method}_R{repeats}.npz',objectives=cal)
            for condition in range(2):
                row,raw=evaluate_grid(evaluation[condition],candidates,condition,0.,record,interest='q')
                rows.append(dict(method=method,repeats=repeats,condition=condition,**row))
                np.savez(folder/f'evaluation_{method}_R{repeats}_c{condition:02d}.npz',objective=evaluation[condition],**raw)
    values={'results.json':dict(methods=methods,repeats=[1,2],independent_reference_max_error=0.),
        'cases.json':rows,'calibration.json':records,
        'registration.json':dict(git_head='fixture',config=dict(calibration_groups=3,evaluation_groups=3,alpha=.25),source_sha256={})}
    for name,value in values.items(): (folder/name).write_text(json.dumps(value))
    attempt=dict(status='complete',artifact_sha256={str(path.relative_to(tmp_path)):module.sha(path) for path in folder.iterdir()})
    (folder/'attempt.json').write_text(json.dumps(attempt))
    bound={name:module.sha(folder/name) for name in ('registration.json','attempt.json')};bound['git_head']='fixture'
    expected=dict(oracle_pairs=2,paired_decisions=8,known_eta_mle=4,paired_estimation=8,ambiguity=8,moment_equivalence=1)
    config=dict(inputs={'control':dict(stage='fixture',records=bound,observations='observations.npz',likelihood_key='exact_logpdf',
        reference_method='exact',moment_methods=['powers'],interest='q')},expected_rows=expected,
        machine_epsilon_multiplier=64,saved_objective_absolute_tolerance=1e-10)
    path=tmp_path/'fixture_config.json';path.write_text(json.dumps(config));monkeypatch.setattr(module,'CONFIG_PATH',path)
    before=threadpool_info();result=module.calculate(output);after=threadpool_info()
    assert before==after and result['rows']==expected and result['new_observations']==0
    with np.load(output/'oracle_control.npz') as raw:
        assert raw['calibration_llr'].shape==(2,1,3)
        assert raw['null_rejected'].shape==(2,1,3)
    assert len(json.loads((output/'ambiguity_cases.json').read_text()))==8
