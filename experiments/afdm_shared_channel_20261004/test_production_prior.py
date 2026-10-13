"""Actual G0 normalization identities, independent of receiver performance."""
from types import SimpleNamespace
import json

import numpy as np
import pytest

from experiments.afdm_shared_channel_20261004 import production_prior as prior


def small_system(n=16):
    env, _, _ = prior.frozen_components()
    system = env.__new__(env)
    values = dict(N_total=n, c1=2.5/n, c2=.1/n**2, l_max_cap=min(3, n-1), k_max_cap=2,
                  k_guard=0, k_leak=2, frac_prune_rel_thres=.01,
                  gen_h_daft_convention='python', use_frac_doppler=True)
    system.__dict__.update(values)
    return system


def test_g0_gram_matches_real_dense_source_with_complex_cross_terms():
    system = small_system()
    gram, weights = prior.normalization_gram(system, np.array([0, 0, 2]), [.23, .49, -.63])
    np.testing.assert_allclose(gram, prior.dense_gram(system, weights), rtol=1e-13, atol=1e-13)
    assert abs(gram[0, 1]) > .1
    assert abs(gram[0, 1].imag) > .01
    assert abs(gram[0, 2]) < 1e-14
    # Pruning/edge clipping is after the full per-path weight normalization.
    assert np.max(abs(np.diag(gram)-1)) > .001


def test_normalization_cancels_first_radial_norm_and_pdp_common_scale():
    rng = np.random.default_rng(1)
    z = rng.normal(size=(17, 3))+1j*rng.normal(size=(17, 3))
    g = np.array([[1., .1j, 0], [-.1j, .9, .04], [0, .04, .8]])
    direct = prior.normalize_gain(z, g)
    first = prior.normalize_gain(z, np.eye(3))
    np.testing.assert_allclose(prior.normalize_gain(first, g), direct, rtol=2e-15, atol=2e-15)
    np.testing.assert_allclose(np.einsum('bi,ij,bj->b', direct.conj(), g, direct), 1, atol=1e-14)
    w = np.full(len(z), 1/len(z)); d = np.array([1., .3, .02])
    a, aw = prior.pushforward_nodes(first, w, d, g)
    b, bw = prior.pushforward_nodes(first, w, 5*d, g)
    np.testing.assert_allclose(a, b, atol=1e-14)
    np.testing.assert_array_equal(aw, bw)


def test_isotropic_special_case_is_sphere_but_anisotropic_pdp_is_not():
    sphere, w = prior.independent_nodes(2, 1., 11, 31, normalized=True)
    same, _ = prior.pushforward_nodes(sphere, w, [1., 1.], np.eye(2))
    np.testing.assert_allclose(same, sphere, atol=1e-14)
    anisotropic, _ = prior.pushforward_nodes(sphere, w, [1., .01], np.eye(2))
    assert w@abs(anisotropic[:, 0])**2 > .9
    assert abs(w@abs(sphere[:, 0])**2-.5) < .01


@pytest.mark.parametrize('gram', [np.zeros((2, 2)), np.diag([1., -1.]), np.array([[1., 1.], [0., 1.]])])
def test_invalid_normalization_is_explicit(gram):
    with pytest.raises(ValueError):
        prior.normalize_gain(np.ones((2, 2)), gram)


def test_saved_first_cluster_scale_from_actual_g0_gram():
    from experiments.afdm_inference_causal_20261002.oracle_comparison import _load
    evidence = _load('prior_test_evidence', prior.ROOT/'experiments/sp_afdm_frozen_20260920/src/evidence.py')
    truth, _ = evidence.load_artifact(prior.OLD/'population/truth/data/development_f000000.npz')
    registration = json.loads((prior.OLD/'runtime_registration.json').read_text())
    system = small_system(1024)
    for key, value in registration['runtime_binding']['system'].items():
        setattr(system, key, value)
    system.k_guard = 4
    gram, _ = prior.normalization_gram(system, truth['l_i'], truth['k_real'])
    raw = truth['g_i']/truth['diagnostics']['g0_fro_scale']
    np.testing.assert_allclose(np.vdot(raw, raw).real, 1., atol=1e-14)
    np.testing.assert_allclose(prior.normalize_gain(raw[None, :], gram)[0], truth['g_i'], atol=1e-13)


def test_analytic_gaussian_and_sphere_projection_moments():
    directions = np.column_stack((np.array([1., 0.]), np.array([1., 1j])/np.sqrt(2)))
    for sphere, fourth in ((False, .5), (True, 1/3)):
        nodes, w = prior.independent_nodes(2, 1., 12, 13, normalized=sphere)
        moments = prior.gain_moments(nodes, w, directions)
        np.testing.assert_allclose(moments['second'], .5, rtol=.015)
        np.testing.assert_allclose(moments['fourth'], fourth, rtol=.015)


def test_positive_laplace_quadrature_recovers_exact_sphere_moments():
    directions = np.eye(3)
    result = prior.diagonal_laplace_moments(np.ones(3), np.eye(3), directions, 64)
    np.testing.assert_allclose(result['second'], 1/3, atol=1e-13)
    np.testing.assert_allclose(result['fourth'], 1/6, atol=1e-13)
    np.testing.assert_allclose(result['energy_mean'], 1, atol=1e-13)
    np.testing.assert_allclose(result['energy_second'], 1, atol=1e-13)
    non_diagonal = np.array([[1., .1j], [-.1j, 1.]])
    with pytest.raises(ValueError, match='diagonal'):
        prior.diagonal_laplace_moments(np.ones(2), non_diagonal, np.eye(2), 64)
