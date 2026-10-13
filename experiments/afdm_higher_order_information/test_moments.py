"""Independent small contracts; registered studies are deliberately not run here."""
import itertools

import numpy as np
import pytest

from experiments.afdm_higher_order_information.moments import (
    FiniteControl, control_T_mean, cross_power_from_inputs, finite_weights,
    feature_values, gaussian_power_product, information_projection, input_moments, time_transform,
)
from experiments.afdm_higher_order_information.theory_study import (
    independent_integrated_moments, independent_log_density, independent_transform, independent_words,
)
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk


def test_frozen_transform_and_CPP_full_wrap():
    for n in (4, 5):
        for delay in (0, n-1):
            actual = time_transform(n, .37/n, .13/n**2, delay)
            direct = independent_transform(n, .37/n, .13/n**2, delay)
            np.testing.assert_allclose(actual, direct, atol=2e-14)
            np.testing.assert_allclose(actual @ actual.conj().T, np.eye(n), atol=2e-14)
            np.testing.assert_allclose(abs(actual), 1/np.sqrt(n), atol=2e-14)


@pytest.mark.parametrize('delay', [0, 3])
@pytest.mark.parametrize('delta', [0., .0001, .07, .4])
def test_fourth_identity_independent_complete_N4(delay, delta):
    n=4; words=independent_words(n); weights=np.full(256, 1/256)
    v=words @ independent_transform(n, .37/n, .13/n**2, delay).T
    second, fourth=independent_integrated_moments(v, weights, delta, -.37, 1.3, .4)
    np.testing.assert_allclose(second, 1.7*np.eye(n), atol=1e-13)
    for a, b in [(1, 2), (1, 3), (2, 3)]:
        assert abs(fourth[0, a]-fourth[0, b]-control_T_mean(n, a, b, delta**2, 1.3)) < 1e-13


def test_non_equal_modulus_and_correlated_inputs_break_simplification():
    words=independent_words(4)
    assert abs(np.mean(abs(words[:, 0])**2*abs(words[:, 1])**2)-.75) > .2
    same=np.repeat(np.array([1+1j, 1-1j, -1+1j, -1-1j])[:, None]/np.sqrt(2), 4, axis=1)
    v=same @ independent_transform(4, .37/4, .13/16, 0).T
    assert abs(np.mean(abs(v[:, 0])**2*abs(v[:, 1])**2)-.75) > .01


def test_single_sided_q_score_and_independent_mixture():
    model=FiniteControl.uniform(4, delay=3)
    y=np.array([[.1+.2j, .3-.4j, .7+.1j, -.2+.8j], [.9-.7j, 1.2+.3j, -.6+.1j, .4-1j]])
    params=[0., .23, 1.3, .5]
    logp, score=model.evaluate(y, *params)
    reference=independent_log_density(y, independent_words(4), independent_transform(4, .37/4, .13/16, 3), *params)
    np.testing.assert_allclose(logp, reference, atol=1e-13)
    errors=[]
    for h in (1e-3, 1e-4, 1e-5, 1e-6):
        p=params.copy(); p[0]=h
        lp,_=model.evaluate(y, *p, score=False)
        errors.append(np.max(abs((lp-logp)/h-score[:, 0])))
    assert errors[-1] < .002*errors[0]
    assert errors[-1] < .003
    for j in (1, 2, 3):
        left=params.copy(); right=params.copy(); left[j]-=1e-5; right[j]+=1e-5
        lm,_=model.evaluate(y, *left, score=False); lp,_=model.evaluate(y, *right, score=False)
        np.testing.assert_allclose((lp-lm)/2e-5, score[:, j], atol=1e-7)


def test_gaussian_power_product_repeated_indices_and_joint_rank():
    covariance=np.diag([2., 3., 4.])
    assert gaussian_power_product(covariance, [0, 0, 1, 1]) == 4*2**2*3**2
    assert gaussian_power_product(covariance, [0, 0, 1, 2]) == 2*2**2*3*4
    model=FiniteControl.uniform(4, delay=3)
    mean, cov=model.exact_feature_moments([(1, 2), (1, 3), (2, 3)], 0., .23, 1.3, .5)
    np.testing.assert_allclose(mean, 0, atol=3e-14)
    assert min(np.diag(cov)) > 0
    np.testing.assert_allclose(cov @ np.array([1, -1, 1]), 0, atol=3e-12)
    # T13=T12+T23 is an algebraic dependence, not three independent samples.
    assert np.linalg.matrix_rank(cov, tol=1e-10) == 2


def test_information_projection_keeps_singular_nuisance_span():
    x=np.array([-2., -1., 0., 1., 2., 3.])
    score=np.column_stack([x*x, x, 2*x, np.zeros_like(x)])
    info=information_projection(score)
    assert info['rank'] == 1
    assert 0 < info['effective'] < info['raw']
    np.testing.assert_allclose(info['orthogonality'], 0., atol=1e-13)
    zero=information_projection(np.column_stack([np.zeros_like(x), x, x, x]))
    assert zero['raw'] == zero['effective'] == 0


def test_general_nonuniform_improper_and_coded_input_moments():
    words,bits=enumerate_qpsk(4, amplitude=1/np.sqrt(2))
    incoming=np.array([1.1, -.4, .7, -1.2, -.3, 1.5, -.8, .2])
    repetition=np.all(bits[:, :4]==bits[:, :1], axis=1)&np.all(bits[:, 4:]==bits[:, 4:5], axis=1)
    transform=time_transform(4, .37/4, .13/16, 3)
    for code in (np.ones(len(words), bool), repetition):
        weights=finite_weights(bits[code], incoming)
        x=words[code] @ transform.T
        moments=input_moments(x, weights)
        second, fourth=independent_integrated_moments(x, weights, .12, .23, 1.3, .5)
        general=cross_power_from_inputs(moments['second'], moments['fourth'], .12**2, 1.3, .5)
        np.testing.assert_allclose(general, fourth, atol=1e-12)
        assert np.linalg.norm(moments['pseudo']) > .01
        own=finite_weights(bits[code], incoming, exclude=[0])
        change=incoming.copy(); change[0]+=9
        np.testing.assert_array_equal(own, finite_weights(bits[code], change, exclude=[0]))


def test_same_y_posterior_requires_explicit_site_removal():
    bits=np.array(list(itertools.product([0, 1], repeat=2)))
    base=finite_weights(bits, [.3, -.7]); site=np.array([.2, 1.3, .5, 2.])
    posterior=base*site; posterior/=posterior.sum()
    restored=posterior/site; restored/=restored.sum()
    np.testing.assert_allclose(restored, base)
    assert np.max(abs(posterior-base)) > .1
    # Without a strictly positive known site, this inversion is not identified.
    site[0]=0
    alternative=base.copy(); alternative[0]+=.1
    alternative[1:] *= (1-alternative[0])/(1-base[0])
    posterior_one=base*site; posterior_one/=posterior_one.sum()
    posterior_two=alternative*site; posterior_two/=posterior_two.sum()
    assert np.max(abs(alternative-base)) > .09
    np.testing.assert_allclose(posterior_one, posterior_two)


@pytest.mark.parametrize('params', [[-.1, .2, 1., .5], [0., .2, 0., .5], [0., .2, 1., 0.], [0., np.nan, 1., .5]])
def test_invalid_control_parameters_fail(params):
    with pytest.raises(ValueError):
        FiniteControl.uniform(4).covariances(*params)


def test_invalid_lag_and_external_factors_fail():
    with pytest.raises(ValueError):
        feature_values(np.ones((2, 4)), [[1, 1]])
    with pytest.raises(ValueError):
        finite_weights([[0, 1], [1, 0]], [0., np.nan])
    with pytest.raises(ValueError):
        time_transform(4, .1, .1, 4)
