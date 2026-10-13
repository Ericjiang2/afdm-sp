"""Deterministic method contracts; no new random scientific observations."""
import inspect
import json
import unittest

import numpy as np

from experiments.afdm_method_advantage import methods
from experiments.afdm_collision_resolution.collision_teacher import CollisionTeacher, exact_moment_system
from experiments.afdm_efficient_information.prior_likelihood import (
    ActualPrior, actual_signal_covariance,
)


def fixed_observations():
    family = methods.cached_family()
    theta = np.array([.31, 0., np.log(.35)])
    m0 = family.point(theta)['m0']
    index = np.arange(len(m0))[:, None]
    coordinate = np.arange(4)[None, :]
    phase = np.exp(2j*np.pi*index/17)
    # Fixed trigonometric fixture, explicitly not a Gaussian research sample.
    noise = (np.sin((index+1)*(coordinate+1)*1.137)
             +1j*np.cos((index+3)*(coordinate+2)*.973))
    return m0*phase+np.sqrt(.35)*noise


class MethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.family = methods.cached_family()
        cls.y = fixed_observations()
        cls.config = dict(starts_mu=[.24, .31, .40], starts_signal_fraction=[.5])

    def test_null_likelihood_and_all_scores_match_frozen_teacher(self):
        y = self.y[:5]
        for mu in (.27, .35):
            for sigma2 in (.2, 1.):
                with self.subTest(mu=mu, sigma2=sigma2):
                    old = CollisionTeacher(mu, sigma2=sigma2).evaluate(y)
                    new = self.family.density(y, [mu, 0., np.log(sigma2)], tangent=True)
                    np.testing.assert_allclose(new['logpdf'], old['logpdf'], rtol=0, atol=2e-12)
                    np.testing.assert_allclose(new['score'], old['score'], rtol=2e-12, atol=2e-11)

    def test_all_finite_moments_and_derivatives_match_frozen_teacher(self):
        for mu, tau, sigma2 in ((.27, 1., .2), (.35, 1., 1.), (.31, .7, .35)):
            old = exact_moment_system(CollisionTeacher(mu, tau, sigma2))
            new = self.family.moments([mu, np.log(tau), np.log(sigma2)], covariance=True, tangent=True)
            np.testing.assert_allclose(new['mean'], old['mean'], rtol=2e-13, atol=2e-13)
            np.testing.assert_allclose(new['covariance'], old['covariance'], rtol=2e-12, atol=3e-11)
            np.testing.assert_allclose(new['derivatives'], old['derivatives'], rtol=3e-12, atol=3e-11)

    def test_null_fit_crosses_pdp_boundary_without_tangent_clipping(self):
        boundary = 18/67
        point = np.array([boundary, 0., np.log(.5)])
        result = self.family.density(self.y[:5], point)
        self.assertTrue(np.isfinite(result['logpdf']).all())
        self.assertTrue(np.isfinite(self.family.moments(point)['mean']).all())
        with self.assertRaisesRegex(methods.TangentUnavailable, 'PDP branch'):
            self.family.density(self.y[:5], point, tangent=True)
        for side in (-1, 1):
            nearby = point.copy(); nearby[0] += side*1e-6
            result = self.family.density(self.y[:5], nearby, tangent=True)
            self.assertGreater(result['tangent_metadata']['pdp_branch_margin'], 1e-9)
            self.assertEqual(nearby[0], boundary+side*1e-6)

    def test_analytic_optimization_jacobians_across_null_pdp_threshold(self):
        for mu in (.22+1e-3, 18/67, .31, .42-1e-3):
            point = np.array([mu, np.log(.7), np.log(.35)])
            actual = self.family.density(self.y[:5], point)['score']
            moment = self.family.moments(point)
            for axis in range(3):
                plus, minus = point.copy(), point.copy()
                plus[axis] += 1e-6; minus[axis] -= 1e-6
                density_fd = (self.family.density(self.y[:5], plus)['logpdf']
                              -self.family.density(self.y[:5], minus)['logpdf'])/2e-6
                moment_fd = (self.family.moments(plus)['mean']-self.family.moments(minus)['mean'])/2e-6
                np.testing.assert_allclose(actual[:, axis], density_fd, rtol=2e-6, atol=2e-7)
                np.testing.assert_allclose(moment['jacobian'][:, axis], moment_fd, rtol=2e-6, atol=2e-7)

    def test_null_mle_and_independent_two_step_gmm_converge_on_fixture(self):
        mle = methods.fit_null_mle(self.y, self.config, self.family)
        gmm = methods.fit_null_m14(self.y, self.config, self.family)
        self.assertTrue(mle['success'], str(mle))
        self.assertTrue(gmm['success'], str(gmm))
        self.assertEqual(len(mle['starts']), 3)
        self.assertEqual(len(gmm['first']['starts']), 3)
        self.assertIsNotNone(gmm['second'])
        self.assertNotEqual(mle['theta'].tolist(), gmm['theta'].tolist())
        for fit in (mle, gmm):
            self.assertGreater(fit['total_evaluations'], 0)
            self.assertGreater(fit['seconds'], 0)

    def test_saved_statistics_are_replayable_from_sufficient_arrays(self):
        result = methods.evaluate_methods(self.y, self.config)
        json.dumps(result, allow_nan=False)
        self.assertFalse(result['failures'], str(result['failures']))
        full = result['diagnostics']['full_score']
        gram, beta, sums = map(np.asarray, (full['gram'], full['beta'], full['score_sum']))
        variance = gram[0, 0]-2*beta@gram[1:, 0]+beta@gram[1:, 1:]@beta
        numerator = sums[0]-beta@sums[1:]
        self.assertAlmostEqual(result['statistics']['full_score'], numerator/np.sqrt(len(self.y)*variance), places=10)
        self.assertAlmostEqual(full['raw_numerator']-full['numerator'], beta@sums[1:], places=10)
        moment = result['diagnostics']['moment']
        v = np.asarray(moment['covariance_matrix']); residual = np.asarray(moment['observed_mean_residual'])
        witness = np.asarray(moment['witness'])
        self.assertAlmostEqual(result['statistics']['moment_score'],
                               np.sqrt(len(self.y))*(witness@residual)/np.sqrt(witness@v@witness), places=10)
        inverse, _ = methods.psd_inverse(v, 1e-10)
        self.assertAlmostEqual(result['statistics']['moment_j'], len(self.y)*residual@inverse@residual, places=10)
        self.assertLess(np.max(abs(np.asarray(moment['witness_nuisance']))), 1e-9)
        self.assertEqual(set(result['statistics']), set(result['costs']['per_method_seconds']))
        self.assertGreater(result['costs']['joint_complete_seconds'], 0)

    def test_optimizer_failure_remains_explicit(self):
        result = methods.evaluate_methods(self.y, {**self.config, 'optimizer':dict(maxiter=1)})
        self.assertIsNone(result['statistics']['full_score'])
        self.assertIsNone(result['statistics']['moment_score'])
        self.assertIsNone(result['statistics']['moment_j'])
        self.assertGreaterEqual(len(result['failures']), 2)
        self.assertFalse(result['fits']['mle']['success'])
        self.assertFalse(result['fits']['m14']['success'])
        self.assertIsNotNone(result['statistics']['second_moment'])

    def test_second_moment_pair_indices_and_finite_separation_symmetry(self):
        result = methods.second_moment_test(self.y)
        powers = abs(self.y)**2
        np.testing.assert_allclose(result['mean'], (powers[:, [0, 2]]-powers[:, [1, 3]]).mean(axis=0))
        self.assertFalse(result['nuisance_identifiable'])
        # Exact P2 covariance identities only; no observations or quadrature.
        model = ActualPrior(n=4)
        for mu in (.27, .31, .35):
            for delta in (0., .025, .06, .12):
                diagonal = np.diag(actual_signal_covariance(model, [delta, mu, 0., 0.])).real
                np.testing.assert_allclose(diagonal[[0, 2]], diagonal[[1, 3]], rtol=0, atol=3e-12)

    def test_local_estimate_branch_flags_preserve_signed_estimates(self):
        margin = .01
        maximum = margin**2*np.log(1/margin**2)
        metadata = dict(pdp_branch_margin=margin)
        for estimate, outside in ((-.2, False), (maximum/2, False),
                                  (maximum, True), (maximum*2, True)):
            result = methods.local_estimate_diagnostics(estimate, metadata)
            self.assertEqual(result['unconstrained'], estimate)
            self.assertEqual(result['one_sided'], max(0., estimate))
            self.assertEqual(result['outside_fitted_local_branch'], outside)
            self.assertEqual(result['unconstrained_below_zero'], estimate < 0)
            self.assertAlmostEqual(result['r_branch_max'], maximum)
            self.assertEqual(result['fitted_delta_branch_radius'], margin)
        with self.assertRaises(ValueError):
            methods.local_estimate_diagnostics(.1, dict(pdp_branch_margin=0.))

    def test_local_diagnostics_do_not_change_statistics_or_estimates(self):
        result = methods.evaluate_methods(self.y, self.config)
        full = result['diagnostics']['full_score']
        moment = result['diagnostics']['moment']
        expected_full = full['numerator']/len(self.y)/full['effective_second_moment']
        expected_moment = moment['numerator']/len(self.y)/moment['witness_target']
        for name, expected, diagnostic in (('full_score', expected_full, full),
                                           ('moment_score', expected_moment, moment)):
            estimate = result['r_hat'][name]
            self.assertAlmostEqual(estimate['unconstrained'], expected, places=14)
            margin = diagnostic['tangent_metadata']['pdp_branch_margin']
            self.assertAlmostEqual(estimate['r_branch_max'], margin**2*np.log(1/margin**2), places=14)
            self.assertAlmostEqual(result['statistics'][name],
                                   diagnostic['numerator']/diagnostic['denominator'], places=12)

    def test_invalid_inputs_domains_and_no_jitter(self):
        for y in (np.empty((0, 4)), np.ones((8, 3)), np.full((8, 4), np.nan)):
            with self.assertRaises(ValueError):
                methods.evaluate_methods(y)
        for config in ({'truth_mu':.31}, {'starts_mu':[.1]}, {'rcond':0}, {'bounds':[[.1,.42],[-1,0],[-1,0]]}):
            with self.assertRaises(ValueError):
                methods.settings(config)
        with self.assertRaises(ValueError):
            methods.psd_inverse(np.diag([1., -1.]), 1e-10)
        with self.assertRaises(ValueError):
            methods.fit_null_m14(np.ones((8, 4), complex), self.config)
        self.assertEqual(list(inspect.signature(methods.evaluate_methods).parameters), ['y', 'config'])


if __name__ == '__main__':
    unittest.main()
