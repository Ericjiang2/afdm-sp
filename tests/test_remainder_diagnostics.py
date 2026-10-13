"""Analytic bilinear-remainder contracts, no receiver or stochastic simulation."""
from pathlib import Path
import sys
import unittest
import numpy as np
from numpy.testing import assert_allclose

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.afdm_inference_causal_20261002.remainder_diagnostics import remainder_moments


class RemainderTests(unittest.TestCase):
    def test_known_gain_and_known_data_zero_remainder(self):
        ops = np.array([np.eye(2), [[0, 1j], [1, 0]]], complex)
        words = np.array([[.5+.5j, -.5j], [-.5+.5j, .5j]])
        h = np.array([.2j, .3])
        known_h = remainder_moments(ops, [0, .1], words, [.4, .6],
                                    np.tile(h, (2, 1)), np.zeros((2, 2, 2)), .5)
        self.assertEqual(known_h['metrics']['t_energy'], 0)
        self.assertEqual(known_h['metrics']['cross'], 0)
        known_d = remainder_moments(ops, [0, .1], words[:1], [1.], h[None],
                                    np.eye(2)[None]/2, .5)
        self.assertEqual(known_d['metrics']['t_energy'], 0)
        self.assertEqual(known_d['metrics']['independent_energy'], 0)

    def test_independent_gaussian_exact_quadrature(self):
        # Two-point Hermite in each real coordinate integrates all second moments
        # of proper Gaussian d exactly; conditional Gaussian h is integrated analytically.
        import itertools
        signs = np.array(list(itertools.product([-1., 1.], repeat=4)))
        f = np.array([[.6, 0], [.1j, .4]], complex)
        words = (signs[:, :2]+1j*signs[:, 2:]) @ f.T / np.sqrt(2)
        c = np.array([[.3, .04j], [-.04j, .5]])
        ops = np.array([np.eye(2), [[0, 1j], [.8, 0]]], complex)
        r = remainder_moments(ops, [.2j, .3], words, np.full(16, 1/16),
                              np.tile([.2, .1j], (16, 1)), np.tile(c, (16, 1, 1)), .2)
        cd = f @ f.conj().T
        expected = sum(c[p,q]*np.trace(ops[q].conj().T@ops[p]@cd)
                       for p in range(2) for q in range(2)).real
        assert_allclose(r['metrics']['t_energy'], expected, atol=1e-14)
        assert_allclose(r['metrics']['independent_energy'], expected, atol=1e-14)
        assert_allclose(r['arrays']['t_mean'], 0, atol=1e-14)
        assert_allclose(r['metrics']['cross'], 0, atol=1e-14)

    def test_correlated_finite_mixture_counterexample(self):
        # h=d with asymmetric probabilities: correlation creates a large nonzero
        # remainder mean and negative linear/remainder cross term.
        r = remainder_moments(np.ones((1, 1, 1)), [.2], [[-1], [1]], [.25, .75],
                              [[-1], [1]], np.zeros((2, 1, 1)), .5)
        m = r['metrics']
        assert_allclose(m['t_energy'], 1.3125, atol=1e-14)
        assert_allclose(m['independent_energy'], .5625, atol=1e-14)
        assert_allclose(m['cross'], -1.8, atol=1e-14)
        assert_allclose(m['linear_energy'], 1.08, atol=1e-14)
        assert_allclose(m['direct_energy'], .5925, atol=1e-14)
        assert_allclose(m['direct_centered_variance'], .03, atol=1e-14)
        assert_allclose(r['arrays']['t_mean'], [.75], atol=1e-14)
        self.assertFalse(m['local_screen_pass'])

    def test_path_permutation_and_decomposition(self):
        ops = np.array([np.eye(2), [[0, 1j], [1, 0]]], complex)
        words = np.array([[.2j, .4], [.3, -.1j]])
        hs = np.array([[.2j, .3], [.4, -.2j]])
        cs = np.array([[[.2, .03j],[-.03j,.4]],[[.3,.04],[.04,.2]]])
        r = remainder_moments(ops, [.1, .2j], words, [.3,.7], hs, cs, .2)
        perm = [1, 0]
        other = remainder_moments(ops[perm], [.1, .2j], words, [.3,.7], hs[:,perm],
                                  cs[:,perm][:,:,perm], .2)
        assert_allclose(r['metrics']['direct_energy'], r['metrics']['expanded_energy'], atol=1e-14)
        assert_allclose(r['metrics']['t_energy'], other['metrics']['t_energy'], atol=1e-14)
        assert_allclose(r['arrays']['t_mean'], other['arrays']['t_mean'], atol=1e-14)
        assert_allclose(r['arrays']['linear_mean'], 0, atol=1e-14)

    def test_invalid_weights_and_covariance(self):
        base = (np.ones((1,1,1)), [0], [[-1],[1]], [.5,.5], [[0],[0]], np.ones((2,1,1)), .5)
        for index, value in [(3,[1,1]), (5,-np.ones((2,1,1))), (6,0)]:
            args = list(base);args[index]=value
            with self.assertRaises(ValueError):remainder_moments(*args)


if __name__ == '__main__':
    unittest.main()
