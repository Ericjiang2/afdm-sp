"""Small matrix algebra tests; no receiver or full simulation calls."""
import unittest
import numpy as np
from afdm_sp_joint_unrolled.direction_cancel import working_factor, transform


class CancellationTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(193)
        self.A = rng.normal(size=(6, 3)) + 1j*rng.normal(size=(6, 3))
        self.P = rng.normal(size=(6, 3)) + 1j*rng.normal(size=(6, 3))
        self.sigma = .3

    def test_factor_matches_independent_linear_solve(self):
        result = working_factor(self.A, self.P, self.sigma)
        gram = self.A.conj().T @ self.A
        lam = .01*np.trace(gram).real/3
        reference = self.sigma*self.P @ np.linalg.solve(gram+lam*np.eye(3), self.P.conj().T)
        B = result['B']
        np.testing.assert_allclose(B @ B.conj().T, reference, rtol=1e-12, atol=1e-12)
        self.assertEqual(B.dtype, np.complex128)

    def test_lowrank_whitens_full_covariance(self):
        B = working_factor(self.A, self.P, self.sigma)['B']
        result = transform(np.arange(6), np.eye(6), B, self.sigma, 'lowrank')
        W = result['H']
        C = self.sigma*np.eye(6) + B @ B.conj().T
        np.testing.assert_allclose(W @ C @ W.conj().T, self.sigma*np.eye(6), atol=1e-12)
        np.testing.assert_allclose(result['z'], W @ np.arange(6), atol=1e-12)

    def test_diagonal_normalizes_heteroscedastic_diagonal(self):
        B = np.array([[1, 0], [0, 3], [2, 1j]], dtype=complex)
        result = transform(np.ones(3), np.eye(3), B, self.sigma, 'diagonal')
        W = result['H']
        C = self.sigma*np.eye(3)+B @ B.conj().T
        np.testing.assert_allclose(np.diag(W @ C @ W.conj().T), self.sigma, atol=1e-12)
        self.assertNotEqual(W[0, 0], W[1, 1])
        self.assertGreater(abs((W @ C @ W.conj().T)[0, 2]), 0)

    def test_scalar_trace_and_zero_support(self):
        B = working_factor(self.A, self.P, self.sigma)['B']
        result = transform(np.ones(6), np.eye(6), B, self.sigma, 'scalar')
        self.assertAlmostEqual(result['sigma_out'], self.sigma+np.sum(abs(B)**2)/6)
        np.testing.assert_array_equal(result['H'], np.eye(6))
        zero = working_factor(np.zeros((6, 0)), np.zeros((6, 0)), self.sigma)['B']
        for mode in ('scalar', 'diagonal', 'lowrank'):
            result = transform(np.ones(6), np.eye(6), zero, self.sigma, mode)
            np.testing.assert_array_equal(result['H'], np.eye(6))
            np.testing.assert_array_equal(result['z'], np.ones(6))
            self.assertEqual(result['sigma_out'], self.sigma)

    def test_invalid_inputs_fail(self):
        for sigma in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                working_factor(self.A, self.P, sigma)
        for A, P in ((np.zeros((6, 1)), np.ones((6, 1))),
                     (self.A, self.P[:5]), (np.ones((6, 41)), np.ones((6, 41))),
                     (self.A*np.nan, self.P)):
            with self.assertRaises(ValueError):
                working_factor(A, P, self.sigma)
        with self.assertRaises(ValueError):
            transform(np.ones(6), np.eye(6), self.P, self.sigma, 'unknown')
        with self.assertRaises(ValueError):
            transform(np.ones(5), np.eye(6), self.P, self.sigma, 'lowrank')


if __name__ == '__main__':
    unittest.main()
