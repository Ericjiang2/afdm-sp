"""Small deterministic mathematical tests; no receiver or FER experiment."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
from numpy.testing import assert_allclose

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.afdm_inference_causal_20261002.exact_oracle import (
    enumerate_qpsk, exact_posterior,
)


class ExactOracleTests(unittest.TestCase):
    def setUp(self):
        self.words, self.bits = enumerate_qpsk(2)
        self.ops = np.array([np.eye(2), [[0, 1j], [1, 0]]], complex)
        self.pilot = np.array([.4 + .1j, -.2j])
        self.mean = np.array([.3 + .2j, -.1 + .1j])
        self.cov = np.array([[.4, .08j], [-.08j, .3]])
        self.y = np.array([.7 - .1j, -.3 + .5j])

    def run_oracle(self, **changes):
        args = dict(y=self.y, operators=self.ops, pilot=self.pilot,
                    candidates=self.words, gain_mean=self.mean,
                    gain_cov=self.cov, noise_variance=.6, bits=self.bits)
        args.update(changes)
        return exact_posterior(**args)

    def test_known_data_precision_form(self):
        d = self.words[[3]]
        result = self.run_oracle(candidates=d, bits=self.bits[[3]])
        b = np.stack([u @ (self.pilot + d[0]) for u in self.ops], axis=1)
        covariance = np.linalg.inv(np.linalg.inv(self.cov) + b.conj().T @ b / .6)
        mean = covariance @ (np.linalg.solve(self.cov, self.mean) + b.conj().T @ self.y / .6)
        assert_allclose(result.h_mean, mean, atol=1e-13)
        assert_allclose(result.h_cov, covariance, atol=1e-13)
        assert_allclose(result.d_cov, 0, atol=1e-15)
        assert_allclose(result.h_d_cov, 0, atol=1e-15)
        self.assertTrue(np.isinf(result.llr).all())

    def test_project_grouped_bit_order(self):
        words, bits = enumerate_qpsk(3)
        assert_allclose(words.real, .5 * (1 - 2*bits[:, :3]))
        assert_allclose(words.imag, .5 * (1 - 2*bits[:, 3:]))

    def test_known_channel_direct_likelihood(self):
        result = self.run_oracle(gain_cov=np.zeros((2, 2)))
        hmat = np.einsum('p,pij->ij', self.mean, self.ops)
        residual = self.y - (self.words + self.pilot) @ hmat.T
        likelihood = np.exp(-np.sum(abs(residual)**2, axis=1) / .6)
        assert_allclose(result.probabilities, likelihood / likelihood.sum(), atol=1e-14)
        assert_allclose(result.h_mean, self.mean, atol=1e-14)
        assert_allclose(result.h_cov, 0, atol=1e-14)

    def test_normalization_independent_precision_determinant_lemma(self):
        result = self.run_oracle()
        values = []
        inv_prior = np.linalg.inv(self.cov)
        for d in self.words:
            b = np.stack([u @ (self.pilot + d) for u in self.ops], axis=1)
            j = inv_prior + b.conj().T @ b / .6
            e = self.y - b @ self.mean
            z = b.conj().T @ e / .6
            quadratic = (np.vdot(e, e) / .6 - np.vdot(z, np.linalg.solve(j, z))).real
            determinant = (.6**2 * np.linalg.det(self.cov) * np.linalg.det(j)).real
            values.append(np.exp(-quadratic) / (np.pi**2 * determinant))
        values = np.array(values)
        assert_allclose(result.probabilities, values / values.sum(), atol=2e-14)
        assert_allclose(np.exp(result.log_evidence), values.mean(), rtol=1e-13)

    def test_scalar_gauss_hermite_integration(self):
        words, bits = enumerate_qpsk(1)
        result = exact_posterior([.2 + .1j], np.ones((1, 1, 1)), [.1], words,
                                 [.2j], [[.15]], .8, bits=bits)
        nodes, weights = np.polynomial.hermite.hermgauss(24)
        gain = .2j + np.sqrt(.15) * (nodes[:, None] + 1j * nodes[None, :])
        weight = weights[:, None] * weights[None, :] / np.pi
        integrals, hfirst, hsecond = [], [], []
        for d in words[:, 0]:
            likelihood = np.exp(-abs(.2 + .1j - gain * (.1 + d))**2 / .8) / (np.pi * .8)
            integrals.append(np.sum(weight * likelihood))
            hfirst.append(np.sum(weight * likelihood * gain))
            hsecond.append(np.sum(weight * likelihood * abs(gain)**2))
        integrals = np.asarray(integrals)
        assert_allclose(result.probabilities, integrals / integrals.sum(), atol=1e-13)
        assert_allclose(result.h_mean[0], sum(hfirst) / sum(integrals), atol=1e-13)
        assert_allclose(result.h_cov[0, 0], sum(hsecond) / sum(integrals) - abs(result.h_mean[0])**2, atol=1e-13)

    def test_singular_prior_and_path_permutation(self):
        covariance = np.diag([.4, 0.])
        result = self.run_oracle(gain_cov=covariance)
        self.assertEqual(result.prior_support_rank, 1)
        assert_allclose(result.component_h_mean[:, 1], self.mean[1], atol=1e-14)
        assert_allclose(result.h_cov[1], 0, atol=1e-14)
        perm = [1, 0]
        other = self.run_oracle(operators=self.ops[perm], gain_mean=self.mean[perm],
                                gain_cov=covariance[np.ix_(perm, perm)])
        assert_allclose(other.h_mean, result.h_mean[perm], atol=1e-13)
        assert_allclose(other.h_cov, result.h_cov[np.ix_(perm, perm)], atol=1e-13)
        assert_allclose(other.h_d_cov, result.h_d_cov[perm], atol=1e-13)
        assert_allclose(other.llr, result.llr, atol=1e-13)

    def test_small_positive_prior_not_thresholded(self):
        result = self.run_oracle(gain_cov=np.diag([1e-20, 0]))
        self.assertEqual(result.prior_support_rank, 1)
        self.assertGreater(result.h_cov[0, 0].real, 0)

    def test_no_pilot_phase_ambiguity(self):
        words, bits = enumerate_qpsk(2)
        result = exact_posterior([.7j, .2], np.eye(2)[None], np.zeros(2),
                                 words, [0], [[1]], .3, bits=bits)
        assert_allclose(result.llr, 0, atol=1e-13)
        assert_allclose(result.h_mean, 0, atol=1e-13)
        assert_allclose(result.d_mean, 0, atol=1e-13)
        self.assertGreater(np.linalg.norm(result.h_d_pseudo_cov), .01)

    def test_short_code_prior_and_mixture_cross_covariance(self):
        words, bits = enumerate_qpsk(2, parity_check=[[1, 1, 1, 1]])
        self.assertEqual(len(words), 8)
        prior = np.arange(1, 9, dtype=float)
        prior /= prior.sum()
        r = self.run_oracle(candidates=words, bits=bits, prior_probabilities=prior)
        ddev = words - r.d_mean
        hdev = r.component_h_mean - r.h_mean
        expected = sum(w * np.outer(h, d.conj()) for w, h, d in zip(r.probabilities, hdev, ddev))
        assert_allclose(r.h_d_cov, expected, atol=1e-14)
        self.assertGreater(np.linalg.norm(r.h_d_cov), .001)
        self.assertTrue(np.all((bits.sum(axis=1) % 2) == 0))

    def test_stable_extreme_llr_and_zero_prior_mass(self):
        words, bits = enumerate_qpsk(1)
        r = exact_posterior([100], np.ones((1, 1, 1)), [0], words,
                            [1], [[0]], 1e-4, bits=bits)
        self.assertTrue(np.isfinite(r.llr).all())
        self.assertGreater(abs(r.llr[0]), 1e5)
        r = exact_posterior([0], np.ones((1, 1, 1)), [0], words,
                            [1], [[0]], 1, bits=bits, prior_probabilities=[1, 0, 0, 0])
        assert_allclose(r.probabilities, [1, 0, 0, 0])
        self.assertTrue(np.isposinf(r.llr).all())

    def test_actual_cpp_fractional_operator(self):
        path = ROOT / 'experiments/sp_afdm_frozen_20260920/src/physical.py'
        spec = importlib.util.spec_from_file_location('oracle_frozen_physical', path)
        physical = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = physical
        spec.loader.exec_module(physical)
        n = 2
        ls, nus = [0, 1], [.31, -.27]
        c1, c2 = np.sqrt(3) / (2*n), np.sqrt(2)/n
        ops = np.stack([np.column_stack([physical.Channel(n, c1, c2, [l], [nu], [1]).apply(e)
                                         for e in np.eye(n)]) for l, nu in zip(ls, nus)])
        channel = physical.Channel(n, c1, c2, ls, nus, self.mean)
        assert_allclose(np.einsum('p,pij->ij', self.mean, ops) @ self.pilot,
                        channel.apply(self.pilot), atol=1e-14)
        r = self.run_oracle(operators=ops)
        self.assertAlmostEqual(r.probabilities.sum(), 1, places=14)
        self.assertGreaterEqual(np.linalg.eigvalsh(r.h_cov).min(), -1e-14)

    def test_invalid_inputs(self):
        cases = [dict(noise_variance=0), dict(noise_variance=np.nan),
                 dict(noise_variance=1+0j),
                 dict(gain_cov=np.diag([-.1, .2])), dict(gain_cov=[[1, 1], [0, 1]]),
                 dict(y=[1]), dict(candidates=np.zeros((0, 2))),
                 dict(gain_mean=[np.nan, 0]), dict(bits=np.zeros((16, 2)) + .5),
                 dict(prior_probabilities=np.zeros(16)),
                 dict(prior_probabilities=np.ones(16)),
                 dict(prior_probabilities=np.ones(16)/16 + .01j),
                 dict(candidates=np.repeat(self.words[[0]], 16, axis=0))]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_oracle(**kwargs)
        for kwargs in [dict(n=0), dict(n=20), dict(n=2, parity_check=[[.5, 0, 0, 0]])]:
            with self.assertRaises(ValueError):
                enumerate_qpsk(**kwargs)


if __name__ == '__main__':
    unittest.main()
