"""Pure NumPy algebra fixtures; no receiver, decoder, SciPy or remote execution."""
import copy
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('__representation_probe_test', Path(__file__).with_name('representation_probe.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class RepresentationProbeTest(unittest.TestCase):
    def test_adjacent_duplicates_and_prior_pushforward(self):
        h = np.array([.7+.1j, -.25+.4j])
        delays, dopplers, duplicated = p.duplicate([1, 1], [.25, -.45], h)
        np.testing.assert_array_equal(delays, [1, 1, 1, 1])
        np.testing.assert_array_equal(dopplers, [.25, .25, -.45, -.45])
        np.testing.assert_array_equal(p.aggregate(duplicated), h)
        D = np.kron(np.eye(2), np.ones((1, 2)))
        np.testing.assert_array_equal(D @ (np.eye(4)/4) @ D.T, np.eye(2)/2)
        self.assertAlmostEqual(np.linalg.norm(duplicated)**2, np.linalg.norm(h)**2/2)
        # Keeping the coordinate prior unchanged would change the physical prior.
        self.assertFalse(np.allclose(D @ (np.eye(4)/2) @ D.T, np.eye(2)/2))

    def test_first_update_formula_and_onsager_aggregation(self):
        h = np.array([.7+.1j, -.25+.4j])
        a = np.array([.4-.8j, -.9+.3j])
        d = np.array([.07+.01j, -.025+.04j])
        tau, q = .5, .7
        original, duplicated, delta = p.first_update(h, a, d, tau, q)
        g = np.repeat(h, 2)/2
        rh = g+q*(np.repeat(a, 2)-np.repeat(d, 2)/2)
        actual = p.aggregate((tau/2)/(tau/2+q)*rh)
        np.testing.assert_allclose(duplicated, actual, rtol=p.RTOL, atol=p.ATOL)
        np.testing.assert_allclose(duplicated-original, delta, rtol=p.RTOL, atol=p.ATOL)
        np.testing.assert_allclose(p.aggregate(np.repeat(d, 2)/2), d)
        wrong = tau/(tau+2*q)*(h+2*q*a-2*q*d)
        self.assertGreater(np.linalg.norm(wrong-actual), 1e-4)
        # Zero bracket is an uninformative first update, not grounds to replace a case.
        a_zero = (h-q*d)/tau
        original, duplicated, delta = p.first_update(h, a_zero, d, tau, q)
        np.testing.assert_allclose(duplicated, original, atol=p.ATOL)
        np.testing.assert_allclose(delta, 0., atol=p.ATOL)

    def test_frozen_synthetic_dense_operator_and_gaussian_posterior(self):
        fixture, atoms = p.synthetic_fixture()
        second, second_atoms = p.synthetic_fixture()
        np.testing.assert_array_equal(fixture['y'], second['y'])
        np.testing.assert_array_equal(atoms, second_atoms)
        np.testing.assert_allclose(atoms[0].conj().T @ atoms[0], np.eye(32), rtol=p.RTOL, atol=p.ATOL)
        h = fixture['gains']
        original = np.einsum('p,pij->ij', h, atoms)
        duplicated = np.einsum('p,pij->ij', np.repeat(h, 2)/2, np.repeat(atoms, 2, axis=0))
        np.testing.assert_allclose(original, duplicated, rtol=p.RTOL, atol=p.ATOL)
        gram = np.einsum('pij,qij->pq', atoms.conj(), atoms)/32
        expected_cross = np.exp(2j*np.pi*np.arange(32)*(-.45-.25)/32).mean()
        np.testing.assert_allclose(gram[0, 1], expected_cross, rtol=p.RTOL, atol=p.ATOL)
        np.testing.assert_allclose(np.vdot(h, gram @ h).real, np.linalg.norm(original)**2/32,
                                   rtol=p.RTOL, atol=p.ATOL)
        result = p.synthetic_posterior(fixture, atoms)
        self.assertTrue(result['passed'])
        B = np.column_stack([atom @ fixture['x'] for atom in atoms])
        D = np.kron(np.eye(2), np.ones((1, 2)))
        _, covariance = p.gaussian_posterior(B, fixture['y'], .5, fixture['sigma2'])
        _, wrong_covariance = p.gaussian_posterior(B @ D, fixture['y'], .5, fixture['sigma2'])
        self.assertFalse(np.allclose(D @ wrong_covariance @ D.T, covariance, rtol=p.RTOL, atol=p.ATOL))
        large = copy.deepcopy(fixture)
        large['n'] = 1024
        with self.assertRaises(ValueError):
            p.dense_atoms(large)

    def test_parity_rejects_nonfinite_and_shape_broadcast(self):
        for actual, expected in (([np.inf], [np.inf]), ([np.nan], [np.nan]), ([1., 1.], [1.])):
            with self.assertRaises(AssertionError):
                p.close(actual, expected, 'invalid parity')
        self.assertIsNone(p.difference(np.zeros(2), np.zeros(2))['relative_l2'])


if __name__ == '__main__':
    unittest.main()
