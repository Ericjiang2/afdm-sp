"""Fixed algebra fixtures; no random observation or performance sampling."""
import unittest

import numpy as np

from .core import estimate
from experiments.afdm_acquisition_performance_20261007 import core as original


class ScreeningContract(unittest.TestCase):
    def test_fixed_shortlist_and_identical_full_candidate_scores(self):
        n = 32
        y = np.exp(.173j*np.arange(2*n).reshape(2, n))
        v = np.exp(.027j*np.arange(n)**3)
        screen = estimate(y, v, .3, 'SCREEN128')
        full = estimate(y, v, .3, 'FULL')
        old = original.estimate(y, v, .3, 'FULL')
        self.assertEqual(screen['likelihood_hypotheses'], 128)
        self.assertEqual(screen['gain_grid_evaluations'], 6144)
        fourth = screen['fourth_scores'].ravel()
        wanted = np.sort(np.argsort(-fourth, kind='stable')[:128])
        np.testing.assert_array_equal(screen['hypotheses'], wanted)
        np.testing.assert_allclose(screen['profile_scores'], full['profile_scores'][wanted], rtol=0, atol=1e-10)
        np.testing.assert_array_equal(screen['best_gain_indices'], full['best_gain_indices'][wanted])
        np.testing.assert_array_equal(full['profile_scores'], old['profile_scores'])
        self.assertGreaterEqual(full['objective']+1e-8, screen['objective'])

    def test_same_tie_order_and_invalid_input(self):
        y, v = np.zeros((1, 32), complex), np.ones(32, complex)
        for method in ('SCREEN128', 'FULL'):
            result = estimate(y, v, 1., method)
            self.assertEqual((result['a'], result['delay']), (0, 0))
            with self.assertRaises(ValueError):
                estimate(y, 2*v, 1., method)
        with self.assertRaises(ValueError):
            estimate(y, v, 1., 'SCREEN32')


if __name__ == '__main__':
    unittest.main()
