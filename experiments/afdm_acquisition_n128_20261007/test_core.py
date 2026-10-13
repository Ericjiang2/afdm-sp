"""Fixed algebra fixtures; no random performance sampling."""
import unittest

import numpy as np
from scipy.special import logsumexp

from .core import estimate, gain_grid, profile_likelihood
from experiments.afdm_acquisition_performance_20261007.core import QPSK


class N128Contracts(unittest.TestCase):
    def test_grid_contains_coarse_grid_and_closes_n128_rotations(self):
        gains = gain_grid()
        self.assertEqual(len(gains), 96)
        circle = np.concatenate([gains*np.exp(.5j*np.pi*k) for k in range(4)])
        for k in range(128):
            rotated = gains*np.exp(2j*np.pi*k/128)
            self.assertLess(np.max(np.min(abs(rotated[:, None]-circle[None, :]), axis=1)), 1e-12)

    def test_fixed_shortlist_matches_full_shared_scores(self):
        n = 64
        y = np.exp(.173j*np.arange(n))[None, :]
        v = np.exp(.027j*np.arange(n)**3)
        screen = estimate(y, v, .3, 'SCREEN512')
        full = estimate(y, v, .3, 'FULL')
        self.assertEqual(screen['likelihood_hypotheses'], 512)
        self.assertEqual(screen['gain_grid_evaluations'], 49152)
        wanted = np.sort(np.argsort(-screen['fourth_scores'].ravel(), kind='stable')[:512])
        np.testing.assert_array_equal(screen['hypotheses'], wanted)
        np.testing.assert_allclose(screen['profile_scores'], full['profile_scores'][wanted], rtol=0, atol=1e-10)
        np.testing.assert_array_equal(screen['best_gain_indices'], full['best_gain_indices'][wanted])
        self.assertGreaterEqual(full['objective']+1e-8, screen['objective'])

    def test_profile_equals_explicit_qpsk_mixture(self):
        n, sigma2 = 8, .7
        x = (.3+.4j)*np.exp(.217j*np.arange(n))[None, :]
        v = np.exp(.139j*np.arange(n)**2)
        hypotheses = np.array([0, 5, 11])
        scores, chosen = profile_likelihood(x, v, sigma2, hypotheses)
        for i, candidate in enumerate(hypotheses):
            a, delay = divmod(candidate, n//4)
            j = (np.arange(n)-a) % n
            z = (x*np.conj(v[j])*np.exp(2j*np.pi*delay*j/n)).ravel()
            values = []
            for gain in gain_grid():
                terms = -abs(z[:, None]-gain*QPSK[None, :])**2/sigma2
                values.append(float(np.sum(logsumexp(terms, axis=1)-np.log(4)+abs(z)**2/sigma2)))
            self.assertAlmostEqual(scores[i], max(values), places=11)
            self.assertEqual(chosen[i], int(np.argmax(values)))

    def test_ties_and_invalid_inputs(self):
        y, v = np.zeros((1, 8), complex), np.ones(8, complex)
        for method in ('SCREEN512', 'FULL'):
            out = estimate(y, v, 1., method)
            self.assertEqual((out['a'], out['delay']), (0, 0))
            with self.assertRaises(ValueError):
                estimate(y, 2*v, 1., method)
        with self.assertRaises(ValueError):
            estimate(y, v, 1., 'SCREEN128')


if __name__ == '__main__':
    unittest.main()
