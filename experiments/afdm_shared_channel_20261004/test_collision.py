"""Independent covariance, information and observation-only estimation contracts."""
import inspect
import unittest

import numpy as np

from experiments.afdm_shared_channel_20261004.collision import (
    CollisionModel, effective_information, estimate, moments, objective_and_gradient, SEARCH)
from experiments.sp_afdm_frozen_20260920.src.physical import Channel, daft


class CollisionTests(unittest.TestCase):
    def setUp(self):
        self.n = 8; self.c1 = 5.3/16; self.c2 = .017
        self.rng = np.random.default_rng(812)
        self.mean = self.rng.normal(size=8)+1j*self.rng.normal(size=8)
        self.model = CollisionModel(8, self.c1, self.c2, 7, self.mean, np.linspace(.1, .4, 8))

    def test_cpp_covariance_independent_dense_operator(self):
        center, gap, power, noise = -.31, .17, 1.3, .2
        X = np.outer(self.mean, self.mean.conj())+np.diag(self.model.variance)
        expected = noise*np.eye(self.n, dtype=complex)
        for nu in [center-gap, center+gap]:
            channel = Channel(8, self.c1, self.c2, [7], [nu], [1.])
            U = np.column_stack([channel.apply(e) for e in np.eye(8)])
            expected += .5*power*U@X@U.conj().T
        transform = daft(np.eye(8), self.c1, self.c2)
        actual = transform@self.model.covariance(center, gap**2, power, noise)@transform.conj().T
        np.testing.assert_allclose(actual, expected, atol=5e-14, rtol=2e-14)

    def test_q_expansion_and_all_nuisance_derivatives(self):
        params = [.23, .02, 1.1, .3]
        K, D = self.model.covariance(*params, True)
        for derivative, slot in zip(D, [1, 0, 2, 3]):
            errors = []
            for eps in [1e-3, 3e-4, 1e-4]:
                plus = params.copy(); minus = params.copy(); plus[slot] += eps; minus[slot] -= eps
                fd = (self.model.covariance(*plus)-self.model.covariance(*minus))/(2*eps)
                errors.append(np.linalg.norm(fd-derivative))
            self.assertLess(errors[-1], 3e-6)
        K0, D0 = self.model.covariance(.23, 0, 1.1, .3, True)
        errors = [np.linalg.norm(self.model.covariance(.23, q, 1.1, .3)-K0-q*D0[0]) for q in [1e-3, 1e-4]]
        self.assertGreater(errors[0]/errors[1], 95.)

    def test_schur_projection_and_complex_fisher_metric(self):
        K, D = self.model.covariance(.2, 0., 1., .3, True)
        result = effective_information(K, D)
        inverse = np.linalg.inv(K)
        direct = np.array([[np.trace(inverse@a@inverse@b).real for b in D] for a in D])
        np.testing.assert_allclose(result['fisher'], direct, atol=2e-11)
        self.assertAlmostEqual(result['effective_projection'], result['effective_schur'], places=9)
        self.assertGreater(result['effective_projection'], 1.)
        # An explicit nuisance span containing K_q absorbs every q direction.
        absorbed = effective_information(K, [D[0], D[0], D[2], D[3]])
        self.assertLess(absorbed['effective_projection'], 1e-22)

    def test_uniform_no_pilot_has_exact_zero_second_moment_information(self):
        model = CollisionModel(8, self.c1, self.c2, 7, np.zeros(8), np.full(8, .5))
        for gap in [0, .2, .6]:
            K, D = model.covariance(-.4, gap**2, 1.2, .3, True)
            np.testing.assert_array_equal(K, (1.2*.5+.3)*np.eye(8))
            info = effective_information(K, D)
            self.assertEqual(info['effective_projection'], 0.)
            self.assertEqual(info['fisher'][0, 0], 0.)
        fit, _ = estimate(model, self.mean)
        self.assertFalse(fit['identifiable']); self.assertIsNone(fit['q'])

    def test_delta_chain_rule_and_nonregular_boundary(self):
        gap = .07
        K, D = self.model.covariance(.2, gap**2, 1., .3, True)
        iq = effective_information(K, D)
        idelta = effective_information(K, [2*gap*D[0], *D[1:]])
        self.assertAlmostEqual(idelta['effective_projection'], 4*gap**2*iq['effective_projection'], places=10)
        with self.assertRaises(ValueError):
            self.model.covariance(.2, -1e-12, 1., .3)

    def test_positive_raw_information_can_be_absorbed_by_power_and_noise(self):
        model = CollisionModel(2, .13, .02, 1, np.array([1., 0.]), np.zeros(2))
        K, D = model.covariance(.17, .01, 1., .2, True)
        info = effective_information(K, D)
        self.assertGreater(info['fisher'][0, 0], 1.)
        self.assertLess(info['effective_projection'], 1e-24)
        self.assertLess(abs(info['effective_schur']), 1e-12)

    def test_objective_gradient(self):
        point = np.array([.2, .013, np.log(1.2), np.log(.3)])
        value, grad = objective_and_gradient(self.model, self.mean, point)
        for slot in range(4):
            direction = np.eye(4)[slot]*1e-6
            fd = (objective_and_gradient(self.model, self.mean, point+direction)[0]
                  -objective_and_gradient(self.model, self.mean, point-direction)[0])/2e-6
            self.assertAlmostEqual(grad[slot], fd, places=5)

    def test_estimators_share_grid_physical_domain_and_have_no_truth_argument(self):
        self.assertEqual(list(inspect.signature(estimate).parameters), ['model', 'y', 'coordinates', 'search'])
        search = dict(SEARCH, center_points=5, gap_points=4, starts=2, maxiter=30)
        fits = []
        for coordinates in ['center_q', 'two_path']:
            fit, grid = estimate(self.model, self.mean, coordinates, search)
            fits.append((fit, grid))
            self.assertGreaterEqual(fit['q'], 0.)
            self.assertLessEqual(fit['q'], search['half_gap_max']**2+1e-7)
            self.assertLessEqual(fit['objective'], grid[:, 0].min()+1e-9)
            self.assertEqual(len(fit['fits']), 2)
        np.testing.assert_array_equal(fits[0][1], fits[1][1])

    def test_soft_cavity_is_legal_fixed_qpsk_moments(self):
        mean, variance = moments(8, 'fixed_soft_cavity', self.rng)
        pilot = .65*np.exp(.31j*np.arange(8)); soft = mean-pilot
        self.assertTrue(np.all(abs(soft.real) <= .5)); self.assertTrue(np.all(abs(soft.imag) <= .5))
        np.testing.assert_allclose(variance, .5-abs(soft)**2)


if __name__ == '__main__':
    unittest.main()
