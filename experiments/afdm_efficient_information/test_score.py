import itertools

import numpy as np
import pytest

from experiments.afdm_efficient_information.score import (
    conditional_scores,linear_information,score_information,select_regressor,
)
from experiments.afdm_efficient_information.features import canonical_phase,observed_features,expected_features,sufficient_outer,feature_catalog
from experiments.afdm_higher_order_information.moments import FiniteControl


def test_four_state_noncommuting_compression_counterexample():
    x,z=np.array(list(itertools.product([-1.,1.],repeat=2))).T
    score=np.column_stack([x,x+z])
    full=score_information(score)
    compressed,mass,at_state=conditional_scores(score,x)
    correct=score_information(compressed,mass)
    wrong,_,_=conditional_scores(full['residual'][:,None],x)
    assert full['effective']==.5
    assert correct['effective']==0
    assert np.dot(mass,wrong[:,0]**2)==.25
    full_nuisance_residual=at_state[:,1:] @ np.array([.5])
    np.testing.assert_allclose(at_state[:,0]-full_nuisance_residual,.5*x)


def test_exact_compression_loss_decomposition():
    x,z=np.array(list(itertools.product([-1.,1.],repeat=2))).T
    scores=np.column_stack([x,x+z]); full=score_information(scores)
    compressed,w,at_state=conditional_scores(scores,x)
    comp=score_information(compressed,w)
    projected,_,on_states=conditional_scores(full['residual'][:,None],x)
    lost=np.mean((full['residual']-on_states[:,0])**2)
    nuisance=np.mean(on_states[:,0]**2)-comp['effective']
    assert abs(full['effective']-comp['effective']-lost-nuisance)<1e-15
    assert lost==nuisance==.25


def test_linear_bound_distinct_from_full_nonlinear_feature_information():
    # Phi=X retains the whole four-state observation, but its linear span cannot
    # capture a quadratic score orthogonal to X. Nuisance is an independent Z.
    x,z=np.array(list(itertools.product([-2.,-1.,1.,2.],[-1.,1.]))).T
    sq=x*x-2.5; scores=np.column_stack([sq,z])
    linear=linear_information(x[:,None],scores)
    rich=linear_information(np.column_stack([x,x*x]),scores)
    assert linear['effective']<1e-14
    assert abs(rich['effective']-score_information(scores)['effective'])<1e-14


def test_nested_features_dense_values_and_phase_invariance():
    y=np.array([[.3+.4j,1-.2j,-.5+.9j,.7+.1j],[-.6+.2j,.4+.8j,1.1-.5j,.1+.3j]])
    values,cost=observed_features(y)
    assert cost['dimensions']=={'energy':1,'old_T':4,'powers':18,'phase':90}
    p=abs(y)**2
    np.testing.assert_allclose(values['old_T'],np.column_stack([p.mean(axis=1),(p*p).mean(axis=1),p[:,0]*(p[:,1]-p[:,2]),p[:,0]*(p[:,1]-p[:,3])]))
    rotated,_=observed_features(y*np.exp(.37j))
    np.testing.assert_allclose(values['phase'],rotated['phase'],atol=1e-14)
    for level in ['energy','old_T','powers']:
        np.testing.assert_array_equal(values[level],values['phase'][:,:values[level].shape[1]])
    outer=sufficient_outer(y)
    np.testing.assert_allclose(outer,sufficient_outer(y*np.exp(.37j)),atol=1e-14)


def test_exact_polynomial_mean_matches_independent_gaussian_rule():
    # One complex Gaussian covariance, product Gauss-Hermite in 8 real dimensions.
    from numpy.polynomial.hermite import hermgauss
    n=4; nodes,weights=hermgauss(3)
    ids=np.array(list(itertools.product(range(3),repeat=2*n)))
    z=nodes[ids[:,:n]]+1j*nodes[ids[:,n:]]
    w=np.prod(weights[ids]/np.sqrt(np.pi),axis=1)
    covariance=np.array([[1.,.2+.1j,.1,0],[.2-.1j,1.2,.1j,.2],[.1,-.1j,.8,.1],[0,.2,.1,1.1]])
    y=z @ np.linalg.cholesky(covariance).T
    values,_=observed_features(y)
    expected=expected_features(covariance[None],np.ones(1))
    np.testing.assert_allclose(w @ values['phase'],expected['phase'],atol=3e-14)


def test_global_phase_likelihood_and_outer_sufficiency():
    model=FiniteControl.uniform(4)
    y=np.array([[.3+.4j,1-.2j,-.5+.9j,.7+.1j]])
    for q in [0.,.04]:
        logp,_=model.evaluate(y,q,.2,1.1,.4)
        rotated,_=model.evaluate(y*np.exp(1.3j),q,.2,1.1,.4)
        np.testing.assert_allclose(logp,rotated,atol=2e-14)
    outer=sufficient_outer(y)[0]; anchor=1
    recovered=outer[:,anchor]/np.sqrt(outer[anchor,anchor].real)
    np.testing.assert_allclose(sufficient_outer(recovered[None])[0],outer,atol=1e-14)


def test_canonical_phase_equivalence_ties_zero_and_non_circular_counterexample():
    y=np.array([[0j,0j,0j,0j],[1j,1.,0.,0.],[.3+.4j,1-.2j,-.5+.9j,.7+.1j]])
    z,index=canonical_phase(y); rotated,_=canonical_phase(y*np.exp(.8j))
    assert index[0]==index[1]==0
    np.testing.assert_allclose(z,rotated,atol=1e-14)
    np.testing.assert_allclose(sufficient_outer(y),sufficient_outer(z),atol=1e-14)
    assert np.all(z[np.arange(3),index].real>=0)
    coherent=np.array([1.+0j]); observed=np.array([1.+0j]); other=observed*1j
    assert not np.isclose(np.sum(abs(observed-coherent)**2),np.sum(abs(other-coherent)**2))


def test_exact_effective_score_itself_retains_effective_information():
    x,z=np.array(list(itertools.product([-1.,1.],repeat=2))).T
    scores=np.column_stack([x,x+z]); full=score_information(scores)
    compressed,w,_=conditional_scores(scores,full['residual'])
    assert abs(score_information(compressed,w)['effective']-full['effective'])<1e-15


def test_score_regression_validation_does_not_fit_test_labels():
    x=np.linspace(-1,1,64)
    train=np.column_stack([x,x*x,np.ones_like(x)])
    score=np.column_stack([2*x+.5*x*x,-x])
    model,trace=select_regressor(train,score,train[::2],score[::2],[0.,.01,1.])
    assert model.ridge==0
    np.testing.assert_allclose(model.predict(train),score,atol=1e-14)
    assert model.rank==2 and len(trace)==3


def test_invalid_partition_and_features_fail():
    with pytest.raises(ValueError): conditional_scores(np.ones((4,2)),[0,1])
    with pytest.raises(ValueError): feature_catalog(3)
    with pytest.raises(ValueError): observed_features([[np.nan,0,0,0]])


def test_small_qualification_split_has_finite_uncertainty():
    from experiments.afdm_efficient_information.features_study import evaluate_layer
    t=np.linspace(-1,1,24); features=np.column_stack([t,t*t])
    scores=np.column_stack([t*t,t,t*t*t,np.sin(t)])
    _,result,_=evaluate_layer(features[:12],features[12:16],features[16:],scores[:12],scores[12:16],scores[16:],[.01],2,[1,2])
    assert np.isfinite(result['score_mse_batch_se']).all()
