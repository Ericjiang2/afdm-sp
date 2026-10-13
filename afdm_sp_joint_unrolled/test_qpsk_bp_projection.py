"""Analytic edge moments versus explicit four-symbol sums and unchanged BP."""
import unittest
import numpy as np
import torch
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch, _qpsk_edge_moments


class QPSKProjectionTests(unittest.TestCase):
    def setUp(self):
        self.c = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])

    def test_moments_against_enumerated_distribution(self):
        rng = np.random.default_rng(445)
        natural = np.r_[rng.normal(size=200)+1j*rng.normal(size=200), 0, 1e3+1e3j, -1e3j]
        priors = rng.normal(size=(2, natural.size))*8
        for temperature in (.5, 1., 2., 100.):
            for prior in (None, priors):
                logits = 2*(natural.conj()[:, None]*self.c).real/temperature
                if prior is not None:
                    logits += .5*(prior[0, :, None]*np.sign(self.c.real)+prior[1, :, None]*np.sign(self.c.imag))
                probability = np.exp(logits-logits.max(axis=1, keepdims=True))
                probability /= probability.sum(axis=1, keepdims=True)
                expected = probability@self.c
                args = (None, None) if prior is None else tuple(torch.from_numpy(x) for x in prior)
                mean, variance = _qpsk_edge_moments(torch.from_numpy(natural), temperature, *args)
                np.testing.assert_allclose(mean.numpy(), expected, rtol=1e-13, atol=1e-13)
                np.testing.assert_allclose(variance.numpy(), np.maximum(.5-np.abs(expected)**2, 1e-10), rtol=1e-12, atol=1e-13)

    def test_complete_bp_soft_and_hard_outputs(self):
        rng = np.random.default_rng(446)
        h = (rng.normal(size=(17, 17))+1j*rng.normal(size=(17, 17)))/4
        h[np.abs(h) < .3] = 0
        y = rng.normal(size=17)+1j*rng.normal(size=17)
        for matrix in (h, np.eye(17, dtype=complex), np.zeros((17, 17), dtype=complex)):
            for prior in (None, np.zeros(34), rng.normal(size=34)*3):
                for temperature in (None, 1., 2.):
                    a, b = [], []
                    common = dict(return_soft=True, n_iter=12, code_prior=prior, message_temperature=temperature)
                    old = mp_detect_bp_torch(y, matrix, .2, self.c, message_observer=a.append if prior is not None else None, **common)
                    new = mp_detect_bp_torch(y, matrix, .2, self.c, edge_projection='qpsk_tanh', message_observer=b.append if prior is not None else None, **common)
                    np.testing.assert_array_equal(old[0], new[0])
                    for left, right in zip(old[1:], new[1:]):
                        np.testing.assert_allclose(left, right, rtol=1e-10, atol=1e-10)
                    for left, right in zip(a, b):
                        for key in ('channel_llr', 'posterior_mean', 'posterior_variance', 'prior_llr'):
                            np.testing.assert_allclose(left[key], right[key], rtol=1e-10, atol=1e-10)

    def test_default_remains_exact(self):
        y = np.array([.3+.1j, -.1+.2j])
        args = (y, np.array([[1., .3j], [.2, 1.]]), .2, self.c)
        a = mp_detect_bp_torch(*args, return_soft=True)
        b = mp_detect_bp_torch(*args, return_soft=True, edge_projection=None)
        for left, right in zip(a, b):
            np.testing.assert_array_equal(left, right)

    def test_invalid_projection_boundaries(self):
        for options in (dict(edge_projection='bad'), dict(edge_projection=True),
                        dict(edge_projection='qpsk_tanh', noncircular=True, code_prior=np.zeros(4)),
                        dict(edge_projection='qpsk_tanh', cavity_observer=lambda x: None)):
            with self.assertRaises(ValueError):
                mp_detect_bp_torch(np.ones(2, complex), np.eye(2), .2, self.c, **options)
        for c in (self.c*2, self.c[::-1], self.c+1e-7):
            with self.assertRaises(ValueError):
                mp_detect_bp_torch(np.ones(2, complex), np.eye(2), .2, c, edge_projection='qpsk_tanh')


if __name__ == '__main__':
    unittest.main()
