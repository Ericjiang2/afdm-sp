"""Small deterministic interface fixtures; never the scientific pilot."""
import unittest

import numpy as np

from .core import estimate, fractional_scores, waveform


class Contracts(unittest.TestCase):
    def test_fft_matches_direct_dft(self):
        z = np.array([[1+.2j, -.3+.8j, .7-.1j, -.4-.2j]])
        a = .17
        n = z.shape[1]
        f = np.exp(-2j*np.pi*np.outer(np.arange(n), np.arange(n))/n)/np.sqrt(n)
        x = (z*np.exp(-2j*np.pi*a*np.arange(n)/n))@f.T
        actual = fractional_scores(z, [a])
        self.assertAlmostEqual(actual[0], float(np.sum(abs(x)**4)), places=13)

    def test_single_frame_noiseless_recovery_and_grid_objective(self):
        n = 4
        r, c = waveform(n, 1/(8*n))
        symbols = np.exp(1j*(np.pi/4+np.pi/2*np.array([[0, 1, 1, 3]])))
        nu = 1.23
        y = np.exp(.4j)*np.exp(2j*np.pi*nu*np.arange(n)/n)*r*np.fft.ifft(symbols*c, norm='ortho')
        analytic = estimate(y, r, c, method='analytic')
        grid = estimate(y, r, c, method='grid', grid_size=8)
        error = (analytic['frequency']-nu+n/2) % n-n/2
        self.assertAlmostEqual(error, 0., places=12)
        self.assertFalse(analytic['flat'])
        self.assertFalse(analytic['near_tie'])
        self.assertLessEqual(analytic['objective'], grid['objective']+1e-13)
        self.assertEqual(analytic['counts']['search_objective_evaluations'], 3)
        self.assertEqual(analytic['counts']['fft_vectors'], 7)

    def test_integer_correlation_sign(self):
        n = 4
        r, c = waveform(n, 1/(8*n))
        symbols = np.exp(1j*np.pi/4)*np.array([[1, 1j, -1, -1j]])
        y = r*np.exp(2j*np.pi*2*np.arange(n)/n)*np.fft.ifft(symbols*c, norm='ortho')
        result = estimate(y, r, c)
        self.assertAlmostEqual(result['frequency'], 2., places=12)
        self.assertEqual(int(np.argmax(result['integer_scores'])), 2)

    def test_zero_chirp_ties_and_zero_data_not_identified(self):
        n = 4
        r, c = waveform(n, 0.)
        y = np.array([[1+.1j, -.2+.7j, .3-.4j, .5+.6j]])
        tied = estimate(y, r, c)
        self.assertTrue(tied['near_tie'])
        self.assertEqual(tied['near_tie_count'], n)
        zero = estimate(np.zeros((1, n)), r, c)
        self.assertTrue(zero['flat'])
        self.assertTrue(zero['near_tie'])
        self.assertFalse(zero['identified'])
        self.assertEqual(zero['frequency'], 0.)
        with self.assertRaises(ValueError):
            estimate(np.full((1, n), np.nan), r, c)


if __name__ == '__main__':
    unittest.main()
