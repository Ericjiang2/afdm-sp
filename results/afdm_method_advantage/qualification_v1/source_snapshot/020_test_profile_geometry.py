import importlib.util
from pathlib import Path
import numpy as np
import pytest
from profile_geometry import ProfileGeometry, channel_jacobian, realify

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('physical_geo_validation', ROOT / 'experiments/sp_afdm_frozen_20260920/src/physical.py')
physical = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(physical)


def test_profile_matches_direct_augmented_least_squares():
    rng = np.random.default_rng(903)
    for rank_deficient in (False, True):
        for lam in (0., .07, 5.):
            j = rng.normal(size=(12, 4))
            if rank_deficient:
                j[:, 3] = j[:, 0]
            variance = np.linspace(.3, .8, 12)
            p = np.diag([lam, lam, 0., lam])
            geom = ProfileGeometry(j, variance, p)
            for r in rng.normal(size=(10, 12)):
                b = np.vstack((j / np.sqrt(variance[:, None]), geom.root))
                target = np.r_[-r / np.sqrt(variance), np.zeros(4)]
                delta = np.linalg.lstsq(b, target, rcond=geom.rtol)[0]
                direct = np.linalg.norm(b @ delta - target)**2
                np.testing.assert_allclose(geom.nuisance_step(r), delta, atol=1e-11)
                np.testing.assert_allclose(geom.value(r), direct, atol=1e-11)
                np.testing.assert_allclose(r @ geom.apply(r), direct, atol=1e-11)
            w = geom.apply(np.eye(12))
            np.testing.assert_allclose(w, w.T, atol=1e-12)
            assert np.linalg.eigvalsh(w).min() > -1e-11
            assert np.linalg.eigvalsh(np.diag(1 / variance) - w).min() > -1e-11


def test_degenerate_and_penalty_limits():
    j = np.array([[1., 1.], [0., 0.]])
    unpenalized = ProfileGeometry(j, 1.)
    assert unpenalized.rank == 1
    assert unpenalized.value(np.array([3., 0.])) < 1e-25
    np.testing.assert_allclose(unpenalized.value(np.array([0., 3.])), 9.)
    values = [ProfileGeometry(j, 1., lam * np.eye(2)).value(np.ones(2)) for lam in (0., .1, 1., 1000.)]
    assert np.all(np.diff(values) > 0)
    np.testing.assert_allclose(ProfileGeometry(np.zeros((3, 2)), .5).apply(np.ones(3)), 2.)


def make_channel(n=16):
    return physical.Channel(n, 3 / (2*n), 1 / (n*n), np.array([0, 2]), np.array([.23, -.41]), np.array([.7+.2j, -.2+.4j]))


def moved(ch, step):
    p = ch.p
    return physical.Channel(ch.n, ch.c1, ch.c2, ch.delays, ch.dopplers+step[2*p:], ch.gains+step[:p]+1j*step[p:2*p])


def test_physical_jacobian_finite_difference_and_local_remainder():
    rng = np.random.default_rng(904)
    ch = make_channel()
    pilot = rng.normal(size=ch.n) + 1j*rng.normal(size=ch.n)
    data = rng.normal(size=ch.n) + 1j*rng.normal(size=ch.n)
    x = pilot + data
    j = channel_jacobian(ch, x)
    h = 1e-6
    for col in range(3*ch.p):
        step = np.eye(3*ch.p)[col] * h
        finite = realify((moved(ch, step).apply(x)-moved(ch, -step).apply(x))/(2*h))
        np.testing.assert_allclose(j[:, col], finite, atol=2e-8, rtol=2e-8)
    direction = rng.normal(size=3*ch.p) * .1
    dx = rng.normal(size=ch.n) + 1j*rng.normal(size=ch.n)
    remainders = []
    for eps in (.02, .01, .005):
        exact = moved(ch, eps*direction).apply(x+eps*dx)-ch.apply(x)
        linear = realify(ch.apply(eps*dx)) + j @ (eps*direction)
        remainders.append(np.linalg.norm(realify(exact)-linear))
    assert 3.8 < remainders[0] / remainders[1] < 4.2
    assert 3.8 < remainders[1] / remainders[2] < 4.2
    assert np.linalg.norm(j-channel_jacobian(ch, data)) > .1  # pilot belongs in J


def test_complex_real_noise_scaling_and_batch():
    z = np.array([1+2j, 3-4j])
    sigma2 = .7
    geom = ProfileGeometry(np.zeros((4, 1)), sigma2/2)
    np.testing.assert_allclose(.5*geom.value(realify(z)), np.vdot(z, z).real / sigma2)
    batch = np.column_stack((realify(z), 2*realify(z)))
    np.testing.assert_allclose(geom.value(batch), [geom.value(batch[:, 0]), geom.value(batch[:, 1])])


def test_invalid_inputs_surface():
    with pytest.raises(ValueError):
        ProfileGeometry(np.eye(2), 0.)
    with pytest.raises(ValueError):
        ProfileGeometry(np.eye(2), 1., np.diag([1., -1.]))
    with pytest.raises(ValueError):
        ProfileGeometry(np.eye(2), 1., np.array([[1., 2.], [0., 1.]]))
    with pytest.raises(ValueError):
        ProfileGeometry(np.eye(2), 1.).value(np.ones(3))
