"""Small fixed-fixture chart and persistence tests; no research observations."""
import tempfile
from pathlib import Path
import unittest

import numpy as np
from scipy.special import i0e, logsumexp

from experiments.afdm_efficient_information.prior_likelihood import actual_signal_covariance, angular_density
from experiments.afdm_efficient_information.prior_refinement import FixedChartPrior, endpoint_nodes, save_components
from experiments.afdm_shared_channel_20261004.production_prior import normalize_gain


class FixedChartTests(unittest.TestCase):
    theta = np.array([.035, .35, 0., np.log(.8)])
    fixture = np.array([[.2+.4j, -.3+.1j, .5-.2j, .1+.7j]])

    def test_positive_jacobian_preserves_uniform_sphere_moments(self):
        unitary = np.array([[1., 1j], [1j, 1.]])/np.sqrt(2)
        rule = endpoint_nodes(unitary, 8, 16, power=4)
        self.assertTrue(np.all(rule['weights'] > 0))
        self.assertAlmostEqual(rule['weights'].sum(), 1., places=13)
        np.testing.assert_allclose(np.sum(abs(rule['nodes'])**2, axis=1), 1., atol=1e-14)
        covariance = np.einsum('b,bi,bj->ij', rule['weights'], rule['nodes'], rule['nodes'].conj())
        np.testing.assert_allclose(covariance, np.eye(2)/2, atol=1e-13)

    def test_fixed_chart_full_score_fd_and_immutable_nodes(self):
        model = FixedChartPrior(self.theta, 12, 24)
        before = model.nodes.copy(); weights = model.weights.copy()
        score = model.evaluate(self.fixture, self.theta, 1e-5)['score'][0]
        finite = []
        for axis in range(4):
            plus, minus = self.theta.copy(), self.theta.copy()
            plus[axis] += 2e-5; minus[axis] -= 2e-5
            finite.append((model.logpdf(self.fixture, plus)[0]-model.logpdf(self.fixture, minus)[0])/4e-5)
        np.testing.assert_allclose(score, finite, rtol=5e-5, atol=2e-7)
        np.testing.assert_array_equal(model.nodes, before)
        np.testing.assert_array_equal(model.weights, weights)
        with self.assertRaises(ValueError):
            model.nodes[0, 0] = 0

    def test_actual_covariance_retains_pdp_density_after_rotation(self):
        model = FixedChartPrior(self.theta, 32, 64)
        branch = model.branch(self.theta)
        gains = normalize_gain(model.nodes, branch['geometry']['gram'])
        response = gains@branch['geometry']['g0'].T
        weights = model.weights*angular_density(model.nodes, branch['pdp']['pdp'], branch['pdp']['weights'])
        covariance = np.einsum('b,bi,bj->ij', weights, response, response.conj())
        np.testing.assert_allclose(covariance, actual_signal_covariance(model, self.theta), atol=5e-6)

    def test_saved_components_are_exact_used_arrays_and_reintegrate(self):
        model = FixedChartPrior(self.theta, 4, 8)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'already been evaluated'):
                save_components(output, 'test__base', model, self.theta, 1e-5)
            result = model.evaluate(self.fixture, self.theta, 1e-5)
            cost = dict(model.cost)
            save_components(output, 'test__base', model, self.theta, 1e-5)
            self.assertEqual(cost, model.cost)
            with np.load(output/'test__base_components.npz') as saved:
                means, logweights = saved['means'], saved['logweights']
                np.testing.assert_array_equal(means, model._components(self.theta, 1e-5)['means'])
                self.assertEqual(saved['derivatives'].shape, (3, len(means), 4))
                sigma = np.exp(self.theta[3]); y = self.fixture[0]
                kappa = 2*abs(means@y.conj())/sigma
                logs = logweights-(np.vdot(y, y).real+np.sum(abs(means)**2, axis=1))/sigma
                logs += np.log(i0e(kappa))+kappa-4*np.log(np.pi*sigma)
                self.assertAlmostEqual(logsumexp(logs), result['logpdf'][0], places=12)

    def test_independent_rule_has_new_directions_and_same_measure(self):
        a = FixedChartPrior(self.theta, 8, 16, rule='sobol', seed=17, phase_shift=.137)
        b = FixedChartPrior(self.theta, 8, 16, rule='sobol', seed=18, phase_shift=.137)
        self.assertFalse(np.array_equal(a.nodes, b.nodes))
        self.assertTrue(np.all(a.weights > 0))
        np.testing.assert_allclose(np.sum(abs(a.nodes)**2, axis=1), 1., atol=1e-14)


if __name__ == '__main__':
    unittest.main()
