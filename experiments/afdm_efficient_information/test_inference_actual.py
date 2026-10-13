"""Deterministic actual-law integration qualification, no research draws."""
import json

import numpy as np
import pytest

from experiments.afdm_efficient_information.inference_actual import (
    CONFIG_PATH,mean_validation,public_candidates,second_gaussian_logpdf,
)
from experiments.afdm_efficient_information.prior_likelihood import ActualPrior,daft,actual_signal_covariance


def test_registered_actual_grid_has_locally_legal_nonplatform_support():
    config=json.loads(CONFIG_PATH.read_text()); candidates=public_candidates(config)
    model=ActualPrior(n=4,model='g0',pdp='marginal',order=4,phases=8)
    branches=[model.branch(theta) for theta in candidates]
    assert len(candidates)==16
    assert all(not b['platform'] and b['eigenvalues'][0]>0 for b in branches)
    # Public candidates can cross conditional PDP branches; each reference law
    # is computed at its own candidate and each local derivative point is regular.
    for theta,branch in zip(candidates,branches):
        for axis in (0,1):
            for sign in (-1,1):
                nearby=theta.copy(); nearby[axis]+=sign*1e-4
                assert model.branch(nearby)['signature']==branch['signature']
    assert 16*(256+128+32*4+64*4)==config['new_observations']


def test_actual_second_observation_covariance_removes_offdiagonal_channel_terms():
    import itertools
    symbols=np.array([1+1j,1-1j,-1+1j,-1-1j])/np.sqrt(2)
    states=np.array(list(itertools.product(symbols,repeat=4)))@daft(4).conj()
    symbol_second=states.T@states.conj()/len(states)
    np.testing.assert_allclose(symbol_second,np.eye(4),atol=2e-15)
    model=ActualPrior(n=4,model='g0',pdp='marginal',order=4,phases=8)
    theta=np.array([.18,.34,np.log(.8),np.log(.7)])
    y=np.array([[.3+.4j,1-.2j,-.5+.9j,.7+.1j],[-.6+.2j,.4+.8j,1.1-.5j,.1+.3j]])
    channel=actual_signal_covariance(model,theta)
    expected=channel*symbol_second+np.exp(theta[3])*np.eye(4)
    logpdf,variance=second_gaussian_logpdf(y,model,theta)
    chol=np.linalg.cholesky(expected)
    dense=-4*np.log(np.pi)-2*np.log(chol.diagonal().real).sum()-np.sum(abs(np.linalg.solve(chol,y.T))**2,axis=0)
    np.testing.assert_allclose(logpdf,dense,atol=3e-14)
    np.testing.assert_allclose(np.diag(expected),variance,atol=2e-15)
    assert np.ptp(variance)>1e-4  # actual geometry cannot be replaced by scalar I


def test_independent_candidate_mean_audit_keeps_discrepancy():
    train=np.array([[0.,1.],[1.,2.],[2.,3.]])
    validation=train+np.array([1.,-1.])
    result=mean_validation(train,validation)
    np.testing.assert_allclose(result['difference'],[1.,-1.])
    np.testing.assert_allclose(result['standard_error'],np.sqrt(2/3))
    assert result['maximum_absolute_se_ratio']>1.
    with pytest.raises(ValueError): mean_validation(np.zeros((3,2)),np.ones((3,2)))


def test_component_artifacts_reuse_exact_cache_without_new_nodes(tmp_path):
    from experiments.afdm_efficient_information.component_artifacts import save_used_components
    model=ActualPrior(n=4,model='g0',pdp='marginal',order=4,phases=8)
    theta=np.array([.2,.35,0.,0.]); y=np.array([[.3+.4j,1-.2j,-.5+.9j,.7+.1j]])
    path=tmp_path/'used.npz'
    with pytest.raises(ValueError): save_used_components(path,model,theta,1e-4)
    model.evaluate(y,theta,step=1e-4); costs=dict(model.cost)
    artifact=save_used_components(path,model,theta,1e-4)
    assert model.cost==costs and artifact['new_nodes']==0
    with np.load(path) as saved:
        used=model._cache[(tuple(theta),1e-4)]
        for field in ['means','logweights','derivatives']:
            np.testing.assert_array_equal(saved[field],used[field])
        np.testing.assert_array_equal(saved['nodes'],model.nodes)
