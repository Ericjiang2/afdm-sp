"""Small algebra contracts for O2; no saved or live receiver calls."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


SPEC = importlib.util.spec_from_file_location('oracle_ce_runner_v1', Path(__file__).with_name('oracle_ce_runner_v1.py'))
oracle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(oracle)


class OracleCEAlgebra(unittest.TestCase):
    def setUp(self):
        self.HS = np.diag([1.+0j, 0.+0j])
        self.R = np.array([[0., .2j], [.1, .3]], dtype=complex)
        self.H = self.HS + self.R
        self.g = np.array([1.+0j])
        self.p = np.array([.7+.1j, .2-.3j])
        self.d = np.array([.2+.4j, -.1+.2j])
        self.mu = np.array([-.1+.1j, .05-.1j])
        self.noise = np.array([.01j, -.02+.01j])
        self.previous = np.array([.4+.2j])

    def arm(self, mu, feedback):
        x = self.p + mu
        A = (self.HS @ x).reshape(2, 1)
        mapping = oracle.affine(A, self.previous, .3)
        y = self.H @ (self.p + self.d) + self.noise
        solution = mapping['B'] @ y + mapping['c']
        return oracle.account(A, mapping['B'], mapping['c'], self.g, self.R, self.H,
                              x, self.d, mu, self.noise, solution, feedback=feedback)

    def test_ordinary_four_terms_and_six_cross_terms_close(self):
        value = self.arm(self.mu, True)
        self.assertEqual(set(value['terms']), {'map', 'tail', 'noise', 'feedback'})
        self.assertEqual(len(value['cross']), 6)
        self.assertLess(value['closure_relative'], 1e-13)
        self.assertAlmostEqual(sum(value['squared'].values()) + sum(value['cross'].values()),
                               value['actual_error'])

    def test_true_data_three_terms_and_three_cross_terms_close(self):
        value = self.arm(self.d, False)
        self.assertEqual(set(value['terms']), {'map', 'tail', 'noise'})
        self.assertEqual(len(value['cross']), 3)
        self.assertLess(value['closure_relative'], 1e-13)

    def test_affine_proximal_center_and_schur(self):
        A = np.array([[1.+0j], [.5j]])
        mapping = oracle.affine(A, np.array([.7+0j]), .4)
        self.assertGreater(abs(mapping['c'][0]), 0)
        full = np.column_stack((A, np.array([.1, 1.])))
        result = oracle.schur(A, full, np.array([0]))
        self.assertEqual(result['extra_algebra_solves'], 1)
        self.assertGreater(result['schur'][0], 0)
        self.assertTrue(result['increment_valid'][0])

    def test_rank_deficient_schur_is_explicitly_undefined(self):
        A = np.array([[1.+0j], [2.+0j]])
        result = oracle.schur(A, np.column_stack((A, A)), np.array([0]))
        self.assertFalse(result['increment_valid'][0])
        self.assertEqual(result['white_variance_increment'][0], 0.)
        self.assertEqual(result['increment_invalid_reason'], 'schur_at_or_below_float64_rank_tolerance')


if __name__ == '__main__':
    unittest.main()
