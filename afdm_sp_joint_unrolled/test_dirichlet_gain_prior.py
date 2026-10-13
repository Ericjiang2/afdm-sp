"""Actual small coded receiver integration; not full N1024 qualification."""
import tempfile
import numpy as np
import pytest
import torch
from .dirichlet_gain_prior import DirichletGainPrior
from .test_supplement_feedback_adapter import tiny_adapter
from .e1_ldpc import build_code
from .supplement_feedback import CodeFeedback
from .trans_next_stop_run import same_receiver_state


def test_frozen_prior_reaches_same_gain_objective_and_default_unchanged():
    with tempfile.TemporaryDirectory() as cache:
        code = build_code(n=64, d_v=2, d_c=4, seed=91, cache_dir=cache)
        receiver = tiny_adapter(code)
        receiver.estimator.lstsq_driver = 'gels'
        rng = np.random.default_rng(912)
        obs = dict(y=rng.normal(size=32)+1j*rng.normal(size=32), pilot=np.ones(32, complex)/2,
                   sigma2=.2, constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        def run(**kw):
            return receiver.run(obs, audit=True, code_feedback=CodeFeedback(code, checkpoint=0, retain_messages=True), **kw)
        old = run()
        same_receiver_state(run(dals_prior=None), old)
        ridge = run(dals_mode='zero_ridge', dals_strength=.1)
        prior = DirichletGainPrior('ridge', .1)
        actual = run(dals_prior=prior)
        for key in ('H','gains','llr','info_hat','support'):
            np.testing.assert_array_equal(actual[key], ridge[key])
        assert prior.record['penalty_calls'] == len(actual['dals'])
        for state in actual['dals']:
            a,y,g,prev = [torch.as_tensor(state[k]) for k in ('A','y','g_solution','g_previous')]
            q = torch.as_tensor(state['Q'])
            lam = torch.as_tensor(state['regularization'])
            residual = a.conj().T@(a@g-y)+q@g+lam*(g-prev)
            assert float(torch.linalg.norm(residual)/max(1.,float(torch.linalg.norm(a.conj().T@y)))) < 2e-5
        with pytest.raises(ValueError, match='one-use'):
            run(dals_prior=prior)
        model = receiver.receiver.model.model
        for name in ('channel_tap_corrector', 'off_support_corr'):
            previous = getattr(model, name)
            setattr(model, name, torch.nn.Identity())
            try:
                with pytest.raises(ValueError, match='fixed discrete prior'):
                    run(dals_prior=DirichletGainPrior())
            finally:
                setattr(model, name, previous)


def test_fixed_prior_rejects_changed_support_and_continuous_values():
    prior = DirichletGainPrior()
    prior.begin()
    d = torch.tensor([0,0])
    k = torch.tensor([0,1])
    g = torch.tensor([1+0j,.2+0j])
    prior.initialize(32,d,k,g)
    with pytest.raises(ValueError, match='support changed'):
        prior.penalty(torch.ones((32,2),dtype=torch.complex64),d,k+1)
    assert prior.record['continuous_parameter_fits'] == 0


@pytest.mark.parametrize('strength', [True, False, None, '0.1', np.nan, np.inf, -1.])
def test_invalid_strength_is_explicit(strength):
    with pytest.raises(ValueError):
        DirichletGainPrior(strength=strength)
