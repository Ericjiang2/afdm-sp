"""Small deterministic FEATURE/EST contracts; no registered experiment launches."""
import numpy as np
import pytest

from experiments.afdm_higher_order_information.features import (
    CandidateBank, collision_jacobian, control_mean, covariance_metric,
    nuisance_projection, observed_features,
)
from experiments.afdm_higher_order_information.estimation import draw_observations, group_means
from experiments.afdm_higher_order_information.moments import FiniteControl
from experiments.afdm_higher_order_information.theory_study import independent_transform


def test_observed_features_match_independent_dense_transform():
    n=16; k=np.arange(5*n).reshape(5,n)
    y=np.cos(k*.31)+1j*np.sin(k*.47)
    fast,cost=observed_features(y,.37/n,.13/n**2,[(4,8),(4,12)])
    r=y @ independent_transform(n,.37/n,.13/n**2,0).T
    p=abs(r)**2
    direct=np.array([[x.mean(),np.mean(x*x),x[0]*(x[4]-x[8]),x[0]*(x[4]-x[12])] for x in p])
    np.testing.assert_allclose(fast,direct,atol=3e-12)
    assert cost['inverse_daft_vectors']==len(y)
    assert cost['truth_inputs']==0


def test_control_mean_matches_complete_finite_input_Wick():
    # N4 independently integrates every symbol word; no simulation comparison.
    model=FiniteControl.uniform(4)
    for q in (0.,.01,.09):
        params=np.array([[q,1.3,.5]])
        actual=control_mean(4,[(1,2),(1,3)],params)[0]
        covariance=model.covariances(q,.23,1.3,.5)
        diagonals=np.diagonal(covariance,axis1=1,axis2=2).real
        power=float(model.weights @ diagonals.mean(axis=1))
        fourth=float(model.weights @ (2*diagonals**2).mean(axis=1))
        cross=diagonals[:,:1]*diagonals+abs(covariance[:,0,:])**2
        t=model.weights @ np.column_stack((cross[:,1]-cross[:,2],cross[:,1]-cross[:,3]))
        np.testing.assert_allclose(actual,[power,fourth,*t],atol=4e-13)


def test_collision_jacobian_and_nuisance_projection():
    n=16; lags=[(4,8),(4,12)]; tau=1.; noise=.5
    j=collision_jacobian(n,lags,tau,noise)
    base=control_mean(n,lags,[[0,tau,noise]])[0]
    for parameter,column in [(0,0),(1,2),(2,3)]:
        point=np.array([0.,tau,noise]); point[parameter]+=1e-7
        fd=(control_mean(n,lags,[point])[0]-base)/1e-7
        np.testing.assert_allclose(fd,j[:,column],atol=2e-5)
    cov=np.array([[2.,.4,.2,.1],[.4,3.,.3,-.1],[.2,.3,4.,.5],[.1,-.1,.5,2.]])
    w,info=nuisance_projection(cov,j)
    assert info['identifiable']
    np.testing.assert_allclose(w @ j[:,1:],0,atol=1e-12)
    np.testing.assert_allclose(w[:2],0,atol=1e-12)
    assert abs(info['feature_information']-j[2:,0] @ np.linalg.solve(cov[2:,2:],j[2:,0]))<1e-11


def test_rank_degeneracy_is_recorded_and_zero_q_information_explicit():
    cov=np.diag([1.,2.,3.,0.]); inverse,record=covariance_metric(cov)
    assert record['rank']==3 and record['discarded_directions']==1
    assert inverse[-1,-1]==0
    j=np.zeros((4,4)); j[0,2]=1; j[1,3]=1
    _,info=nuisance_projection(cov,j)
    assert not info['identifiable'] and info['feature_information']==0
    with pytest.raises(ValueError):
        covariance_metric(np.diag([1.,-1.]))


def test_q_and_original_delta_share_candidates_and_solution():
    q=np.linspace(0,.16,33); tau=np.linspace(.3,2.,5); noise=np.linspace(.1,1.5,4)
    cov=np.diag([1.,8.,5.,6.]); lags=[(4,8),(4,12)]
    qbank=CandidateBank(16,lags,q,tau,noise,cov,'q')
    dbank=CandidateBank(16,lags,q,tau,noise,cov,'delta')
    # Observation-only vectors on and away from the candidate manifold.
    observed=qbank.means[[0,250,658]].copy(); observed[1]+=[.1,-.2,.3,-.4]
    a=qbank.estimate(observed); b=dbank.estimate(observed)
    np.testing.assert_array_equal(a['parameters'],b['parameters'])
    np.testing.assert_allclose(a['objectives'],b['objectives'],atol=2e-13)
    assert a['boundary'][0,0]
    assert a['cost']['candidate_objectives']==len(observed)*len(qbank.parameters)


def test_R_prefix_and_prior_exogenous_pairing():
    config=dict(n=16,c1=.37/16,c2=.13/16**2)
    first,a=draw_observations(config,16,[12,34],'Gaussian',.05,1.,.5)
    second,b=draw_observations(config,16,[12,34],'sphere2',.05,1.,.5)
    assert a['exogenous_hash']==b['exogenous_hash']
    assert not np.array_equal(first,second)
    f,_=observed_features(first,config['c1'],config['c2'],[(4,8),(4,12)])
    grouped=group_means(f,4,[1,4])
    np.testing.assert_array_equal(grouped[1],f[::4])
    np.testing.assert_allclose(grouped[4],f.reshape(4,4,4).mean(axis=1))


def test_exact_G0_phase_reduction_does_not_depend_on_gap():
    config=dict(n=16,c1=.37/16,c2=.13/16**2)
    y,_=draw_observations(config,4,[56,78],'G0_rank1',0.,1.,.5)
    changed,_=draw_observations(config,4,[56,78],'G0_rank1',.07,1.,.5)
    np.testing.assert_array_equal(y,changed)


def test_input_errors_fail_explicitly():
    with pytest.raises(ValueError):
        observed_features(np.ones((2,16)),.1,.2,[(4,4)])
    with pytest.raises(ValueError):
        control_mean(16,[(4,8)],[[0.,-1.,.5]])
    with pytest.raises(ValueError):
        group_means(np.zeros((6,4)),2,[1,4])
    with pytest.raises(ValueError):
        CandidateBank(16,[(4,8)],[0,.1,.1],[1.],[.5],np.eye(3))
