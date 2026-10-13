"""Deterministic qualification fixtures; no new random research observations."""
import itertools

import numpy as np
import pytest

from experiments.afdm_efficient_information.inference import (
    MomentBank,aggregate_rows,calibrate,evaluate_grid,grid_statistics,
    load_score_model,upper_order_statistic,
)
from experiments.afdm_efficient_information.score import ScoreRegressor


def test_cached_objective_matches_independent_dense_quadratic():
    train=np.array([[1.,0.],[-1.,0.],[0.,2.],[0.,-2.]])
    means=np.array([[.1,.4],[.4,.2],[-.3,.7]])
    bank=MomentBank(train,np.zeros_like(train),means)
    observed=np.array([[.1,.6],[-.2,.3]])
    objective,cost=bank.objective(observed,4)
    inverse=np.linalg.inv(train.T@train/len(train))
    direct=np.array([[4*(y-m)@inverse@(y-m) for m in means] for y in observed])
    np.testing.assert_allclose(objective,direct,atol=2e-15)
    assert cost['new_candidate_response_values']==0


def test_zero_variance_feature_bank_is_explicitly_information_free():
    bank=MomentBank(np.ones((4,2)),np.ones((4,2)),np.ones((3,2)))
    objective,_=bank.objective(np.ones((2,2)),1)
    np.testing.assert_array_equal(objective,np.zeros((2,3)))
    assert bank.rank['rank']==0
    with pytest.raises(ValueError): MomentBank(np.empty((0,2)),np.empty((0,2)),np.ones((3,2)))


def test_prefix_repeats_share_exact_observation_ids():
    rows=np.arange(24).reshape(12,2)
    np.testing.assert_array_equal(aggregate_rows(rows,3,4,1),rows[[0,4,8]])
    np.testing.assert_array_equal(aggregate_rows(rows,3,4,4,mean=False),rows.reshape(3,4,2).sum(axis=1))
    with pytest.raises(ValueError): aggregate_rows(rows,4,4,1)


def test_profile_nuisance_and_coordinate_relabel_keep_candidate_ids():
    candidates=np.array([[0.,-1.],[0.,1.],[.04,-1.],[.04,1.]])
    objective=np.array([[7.,4.,6.,1.],[.2,3.,1.,2.]])
    actual=grid_statistics(objective,candidates,0.)
    np.testing.assert_array_equal(actual['index'],[3,0])
    np.testing.assert_allclose(actual['detection'],[3.,0.])
    delta=candidates.copy(); delta[:,0]=np.sqrt(delta[:,0])
    np.testing.assert_array_equal(grid_statistics(objective,delta,0.)['index'],actual['index'])


def test_split_order_statistic_exact_exchangeability_rank_and_ties():
    # All assignments of four distinct pooled scores to 3 calibration and one
    # future observation. Rejection rank gives exactly alpha=1/4 marginally.
    rejected=[]
    for assignment in itertools.permutations([0.,1.,2.,3.]):
        cutoff,rank=upper_order_statistic(assignment[:3],.25)
        assert rank==3
        rejected.append(assignment[3]>cutoff)
    assert np.mean(rejected)==.25
    assert upper_order_statistic(np.ones(19),.05)==(1.,19)
    with pytest.raises(ValueError): upper_order_statistic(np.arange(8),.05)


def test_calibration_takes_worst_null_and_all_true_grid_cutoffs():
    candidates=np.array([[0.,0.],[0.,1.],[.04,0.],[.04,1.]])
    base=np.array([[1.,2.,0.,4.],[2.,3.,0.,5.],[3.,4.,0.,6.]])
    objectives=[base,base+np.array([0.,2.,0.,0.]),base,base]
    calibration=calibrate(objectives,candidates,0.,.25)
    assert calibration['detection_cutoff']==3.
    assert calibration['confidence_cutoff']==6.
    result,raw=evaluate_grid(base,candidates,3,0.,calibration,unidentifiable=(1,))
    assert result['joint_grid_coverage']==1.
    assert result['parameter_rmse'][1] is None
    assert result['empty_grid_sets']==0
    assert np.all(raw['grid_confidence_set'][:,3])


def test_frozen_score_model_roundtrip_without_truth_arguments(tmp_path):
    t=np.linspace(-1.,1.,24); features=np.column_stack([t,t*t])
    scores=np.column_stack([t,2*t,t*t,-t*t])
    model=ScoreRegressor(.01).fit(features,scores)
    path=tmp_path/'model.npz'
    np.savez(path,**model.state(),efficient_beta=np.array([1.,2.,3.]),public_theta=[0.,.4,1.3,.7])
    loaded=load_score_model(path)
    from experiments.afdm_efficient_information.features_actual import load_regressor
    proxy,metadata=load_regressor(path)
    np.testing.assert_array_equal(loaded.predict(features),model.predict(features))
    np.testing.assert_array_equal(proxy.predict(features),model.predict(features))
    np.testing.assert_array_equal(metadata['efficient_beta'],[1.,2.,3.])
