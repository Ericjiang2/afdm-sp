"""Deterministic engineering contracts; not scientific performance evidence."""
import inspect
import unittest

import numpy as np
from scipy.special import logsumexp

from .core import QPSK, estimate, fourth_scores, gain_grid, profile_likelihood, row_chirp, simulate


class AcquisitionContracts(unittest.TestCase):
    def setUp(self):
        self.n = 8
        self.v = np.exp(.137j*np.arange(8)**3)
        self.states = np.arange(24).reshape(3, 8) % 4

    def test_physical_model_against_dense_matrix_and_joint_coordinate(self):
        n, delay, cfo = self.n, 1, 7
        h = .91*np.exp(.27j)
        y = simulate(self.states, np.zeros((3, n), complex), self.v, delay, cfo, h, .1)
        fourier = np.exp(-2j*np.pi*np.outer(np.arange(n), np.arange(n))/n)/np.sqrt(n)
        signal = (np.diag(row_chirp(n))@fourier.conj().T@np.diag(self.v)@QPSK[self.states].T).T
        expected = np.array([h*np.exp(2j*np.pi*cfo*(t*(n+n//4)+np.arange(n))/n)*
                             np.roll(signal[t], delay) for t in range(3)])
        np.testing.assert_allclose(y, expected, atol=1e-13)
        x = np.fft.fft(y*np.conj(row_chirp(n)), axis=1, norm='ortho')
        a = (cfo+5*delay) % n
        j = (np.arange(n)-a) % n
        expected_x = (h*np.exp(-5j*np.pi*delay**2/n)*np.exp(2j*np.pi*cfo*np.arange(3)*(n+n//4)/n)[:, None]*
                      self.v[j]*np.exp(-2j*np.pi*delay*j/n)*QPSK[self.states[:, j]])
        np.testing.assert_allclose(x, expected_x, atol=2e-13)

    def test_fft_against_every_direct_hypothesis_and_wrap(self):
        x = (np.arange(24).reshape(3, 8)-9+1j*np.cos(np.arange(24)).reshape(3, 8))/10
        fft = fourth_scores(x, self.v)
        expected = np.empty_like(fft)
        for a in range(8):
            for delay in range(2):
                expected[a, delay] = abs(np.sum(np.mean(x**4, axis=0)*
                    np.conj(self.v[(np.arange(8)-a) % 8]**4)*np.exp(8j*np.pi*delay*np.arange(8)/8)))
        np.testing.assert_allclose(fft, expected, atol=1e-12)

    def test_profile_against_explicit_four_gaussians(self):
        x = (np.arange(24).reshape(3, 8)-9+1j*np.sin(np.arange(24)).reshape(3, 8))/10
        sigma2 = .31
        hypotheses = np.array([0, 3, 9, 15])
        scores, indices = profile_likelihood(x, self.v, sigma2, hypotheses)
        explicit = []
        for item in hypotheses:
            a, delay = divmod(int(item), 2)
            j = (np.arange(8)-a) % 8
            z = x*np.conj(self.v[j])*np.exp(2j*np.pi*delay*j/8)
            values = []
            for gain in gain_grid():
                mixture = logsumexp(-np.abs(z[..., None]-gain*QPSK)**2/sigma2, axis=2)-np.log(4)
                values.append(float(mixture.sum()+np.sum(np.abs(z)**2)/sigma2))
            explicit.append(values)
        explicit = np.array(explicit)
        np.testing.assert_allclose(scores, explicit.max(axis=1), atol=1e-11)
        np.testing.assert_array_equal(indices, explicit.argmax(axis=1))

    def test_contiguous_frame_factor_disappears_only_modulo_C4(self):
        for n in (8, 12):
            for cfo in range(n):
                phase = np.exp(2j*np.pi*cfo*(n+n//4)*np.arange(4)/n)
                np.testing.assert_allclose(phase**4, 1., atol=2e-13)

    def test_noiseless_recovery_and_gain_gauge(self):
        delay, cfo = 1, 7
        # Choose an effective gain on-grid; physical h includes chirp phase.
        effective = gain_grid()[19]
        h = effective*np.exp(5j*np.pi*delay**2/8)
        y = simulate(self.states, np.zeros((3, 8), complex), self.v, delay, cfo, h, .02)
        for method in ('FOURTH', 'SCREEN32', 'FULL'):
            answer = estimate(y, self.v, .02, method)
            self.assertEqual((answer['delay'], answer['cfo']), (delay, cfo))
            if method == 'FOURTH':
                self.assertIsNone(answer['physical_gain_mod_C4'])
            else:
                np.testing.assert_allclose(answer['physical_gain_mod_C4'], [h.real, h.imag], atol=1e-12)

    def test_screen_is_subset_and_full_dominates(self):
        n = 16
        v = np.exp(.071j*np.arange(n)**3)
        y = np.cos(np.arange(2*n)).reshape(2, n)+1j*np.sin(np.arange(2*n)*.3).reshape(2, n)
        full, screen = [estimate(y, v, .5, method) for method in ('FULL', 'SCREEN32')]
        self.assertEqual(len(screen['hypotheses']), 32)
        np.testing.assert_allclose(screen['profile_scores'], full['profile_scores'][screen['hypotheses']], atol=1e-11)
        self.assertGreaterEqual(full['objective']+1e-10, screen['objective'])

    def test_stable_ties_and_input_boundary(self):
        y = np.zeros((1, 8), complex)
        for method in ('FOURTH', 'SCREEN32', 'FULL'):
            result = estimate(y, self.v, .1, method)
            self.assertEqual((result['a'], result['delay']), (0, 0))
            self.assertEqual(result['exact_ties'], 16)
        for variance in (0, -1, np.nan):
            with self.assertRaises(ValueError):
                estimate(y, self.v, variance, 'FULL')
        with self.assertRaises(ValueError):
            estimate(y, self.v*2, .1, 'FULL')
        self.assertEqual(list(inspect.signature(estimate).parameters), ['y', 'v', 'sigma2', 'method'])


if __name__ == '__main__':
    unittest.main()
