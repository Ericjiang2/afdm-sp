"""Tiny deterministic contract fixtures; no scientific simulation or fitting."""
import inspect
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_efficient_information import prior_likelihood
from . import core
from .geometry import c2_derivative, moments, recover


class FixedRng:
    """Deterministic arrays replace every RNG call in the generator fixture."""
    def choice(self, size, count, p):
        return np.zeros(count, dtype=int)

    def standard_normal(self, shape):
        return (np.arange(np.prod(shape)).reshape(shape)+1)/8

    def integers(self, low, high, shape):
        return np.arange(np.prod(shape)).reshape(shape) % 4


class CoreContracts(unittest.TestCase):
    def test_observation_only_and_exact_statistics(self):
        self.assertEqual(list(inspect.signature(core.c2).parameters), ['y'])
        powers = np.array([[4, 1, 2, 1], [2, 1, 5, 1], [1, 3, 1, 2], [4, 2, 3, 1]], float)
        d = powers[:, [0, 2]]-powers[:, [1, 3]]
        result = core.c2(np.sqrt(powers))
        covariance = np.cov(d.T, ddof=1)
        expected_q = len(d)*d.mean(0)@np.linalg.solve(covariance, d.mean(0))
        expected_u = sum(d[i]@d[j] for i in range(4) for j in range(4) if i != j)/12
        self.assertEqual(result['status'], 'ok')
        np.testing.assert_allclose(result['covariance'], covariance, atol=1e-14)
        self.assertAlmostEqual(result['Q'], expected_q)
        self.assertAlmostEqual(result['U'], expected_u)

    def test_explicit_failures_without_jitter(self):
        result = core.c2(np.ones((4, 4)))
        self.assertEqual(result['rank'], 0)
        self.assertIsNone(result['Q'])
        self.assertEqual(result['U'], 0)
        self.assertEqual(core.c2(np.full((4, 4), np.nan))['failure'], 'nonfinite_observation')
        with self.assertRaises(ValueError):
            core.c2(np.ones((4, 3)))
        with self.assertRaises(TypeError):
            core.c2(np.ones((4, 4)), truth={})

    def test_generator_latent_replay_and_mode_isolation(self):
        model = prior_likelihood.ActualPrior.__new__(prior_likelihood.ActualPrior)
        model.n, model.model, model.pdp = 4, 'g0', 'marginal'
        response = np.array([[1, 1], [1, -1], [1, 1j], [1, -1j]], complex)
        branch = dict(pdp=dict(pdp=np.array([[1., .7]]), weights=np.ones(1)),
                      geometry=dict(gram=np.eye(2), g0=response, weights=response,
                                    dopplers=np.array([.29, .33])))
        model.branch = lambda theta: branch
        theta = np.array([.02, .31, 0., np.log(.2)])
        with patch.object(np.random, 'default_rng', side_effect=lambda seed: FixedRng()), \
             patch.object(core, 'daft', side_effect=lambda n: np.eye(n)), \
             patch.object(prior_likelihood, 'daft', side_effect=lambda n: np.eye(n)):
            iid = core.generate_group(model, theta, 4, [1, 2, 3], 'iid')
            coherent = core.generate_group(model, theta, 4, [1, 2, 4], 'coherent')
        self.assertEqual(iid['H'].shape, (4, 4))
        self.assertEqual(coherent['H'].shape, (1, 4))
        self.assertEqual(iid['gains'].shape, (4, 2))
        # Independently reconstruct the full saved iid Y from its replayed H.
        symbols = np.exp(1j*(np.pi/4+np.pi/2*FixedRng().integers(0, 4, (4, 4))))
        noise = (1+1j)*FixedRng().standard_normal((4, 4))/np.sqrt(2)
        np.testing.assert_allclose(iid['Y'], iid['H']*symbols+np.sqrt(.2)*noise)
        np.testing.assert_allclose(coherent['Y'], coherent['H']*symbols+np.sqrt(.2)*noise)

    def test_exact_prony_fixture_and_derivative_exception(self):
        n = 4
        nodes = np.array([4., 4.5])
        weights = np.array([1+.2j, -.4+.7j])
        mm = np.array([sum(weights*nodes**j) for j in range(3)])
        nu, qualification = recover(n, mm)
        np.testing.assert_allclose(nu, np.sort(4/np.pi*np.arctan(1/nodes)), atol=1e-12)
        self.assertNotEqual(qualification['determinant'], 0)
        self.assertLess(qualification['relative_reconstruction_residual'], 1e-12)
        self.assertEqual(moments(4, np.ones(3)).shape, (3,))
        np.testing.assert_array_equal(c2_derivative(.31, 1., [1., .7]), np.zeros(2))
        with self.assertRaises(ValueError):
            c2_derivative(.31, 1., [1., -1.])
        with self.assertRaises(ValueError):
            recover(4, np.array([2., 8.5, 36.25]))

    def test_prony_rejects_near_singular_and_wrong_branch(self):
        nodes = np.array([4., 4.5])
        weights = np.array([1., 1.+1e-14j])
        mm = np.array([sum(weights*nodes**j) for j in range(3)])
        with self.assertRaisesRegex(ValueError, 'near-singular'):
            recover(4, mm)
        nodes = np.array([1., 2.])
        weights = np.array([1.+.2j, -.4+.7j])
        mm = np.array([sum(weights*nodes**j) for j in range(3)])
        with self.assertRaisesRegex(ValueError, 'branch'):
            recover(4, mm)


if __name__ == '__main__':
    unittest.main()
