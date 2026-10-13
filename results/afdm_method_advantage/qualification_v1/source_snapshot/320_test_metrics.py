"""Small algebra checks; these fixtures are not receiver performance evidence."""

import pathlib
import sys
import unittest

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"))
sys.path.insert(0, str(HERE))

from physical import Channel, daft
from metrics import (axial_grid_starts, exact_code_moments, final_refit_bounds, fit_true_data, isotropic_real_controls,
                     operator_mismatch, real_tangent_projection, response_matrix,
                     score_geometry, search_geometry,
                     transplant_legal_error_contrast)


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.n = 9
        self.c1, self.c2 = 0.13 / self.n, 0.07 / self.n
        self.l = np.array([1, 1, 3])
        self.nu = np.array([-0.8, 0.5, 1.2])
        self.h = np.array([0.6 + 0.2j, -0.3 + 0.5j, 0.1 - 0.4j])
        self.rng = np.random.default_rng(41)
        self.x = self.rng.normal(size=self.n) + 1j * self.rng.normal(size=self.n)
        self.c = Channel(self.n, self.c1, self.c2, self.l, self.nu, self.h)

    def test_response_and_real_doppler_derivative(self):
        B, dB = response_matrix(self.x, self.l, self.nu, self.c1, self.c2, derivative=True)
        np.testing.assert_allclose(B @ self.h, daft(self.c.apply(self.x), self.c1, self.c2, True), atol=1e-12)
        eps = 1e-6
        for j in range(len(self.l)):
            plus, minus = self.nu.copy(), self.nu.copy()
            plus[j] += eps
            minus[j] -= eps
            fd = (response_matrix(self.x, self.l, plus, self.c1, self.c2)[:, j]
                  - response_matrix(self.x, self.l, minus, self.c1, self.c2)[:, j]) / (2 * eps)
            np.testing.assert_allclose(dB[:, j], fd, atol=1e-9)
        # Direct CPP sample construction, before DAFT, agrees with both helpers.
        xt = daft(self.x, self.c1, self.c2, True)
        k = np.arange(self.n)
        direct = []
        for l, nu in zip(self.l, self.nu):
            wrap = k - l
            cp = np.where(wrap < 0, np.exp(2j * np.pi * self.c1 * (self.n**2 + 2 * self.n * wrap)), 1)
            direct.append(cp * np.exp(2j * np.pi * k * nu / self.n) * xt[wrap % self.n])
        np.testing.assert_allclose(B, np.column_stack(direct), atol=1e-12)

    def test_profiles_and_dense_gaussian_covariance(self):
        B = response_matrix(self.x, self.l, self.nu, self.c1, self.c2)
        Y = B @ self.h + 0.1 * (self.rng.normal(size=self.n) + 1j * self.rng.normal(size=self.n))
        sigma2, lam = 0.17, 0.32
        s = score_geometry(Y, B, sigma2, conditional_gains=self.h, ridge_lambda=lam)
        np.testing.assert_allclose(s["profile_score"], np.linalg.norm(Y - B @ np.linalg.lstsq(B, Y, rcond=None)[0])**2 / sigma2)
        np.testing.assert_allclose(s["conditional_score"], np.linalg.norm(Y - B @ self.h)**2 / sigma2)
        # Explicit augmented complex LS is independent of the SVD ridge formula.
        A_aug = np.vstack((B, np.sqrt(lam) * np.eye(B.shape[1])))
        y_aug = np.concatenate((Y, np.zeros(B.shape[1])))
        h_aug = np.linalg.lstsq(A_aug, y_aug, rcond=None)[0]
        np.testing.assert_allclose(s["ridge_gains"], h_aug, atol=1e-11)
        np.testing.assert_allclose(s["ridge_score"], np.linalg.norm(y_aug - A_aug @ h_aug)**2 / sigma2)
        C = sigma2 * np.eye(self.n) + (B @ B.conj().T) / B.shape[1]
        sign, logdet = np.linalg.slogdet(C / sigma2)
        self.assertGreater(sign, 0)
        dense = np.vdot(Y, np.linalg.solve(C, Y)).real + logdet
        np.testing.assert_allclose(s["marginal_score"], dense, atol=1e-11)
        np.testing.assert_allclose(s["response_gram_eigenvalues"], np.linalg.eigvalsh(B.conj().T @ B), atol=1e-11)
        duplicated = np.column_stack((B[:, 0], B[:, 0]))
        deficient = score_geometry(Y, duplicated, sigma2)
        self.assertEqual(deficient["profile_rank"], 1)
        np.testing.assert_allclose(duplicated @ deficient["profile_gains"],
                                   duplicated @ np.linalg.lstsq(duplicated, Y, rcond=None)[0])

    def test_operator_and_sp_mismatch(self):
        other = Channel(self.n, self.c1, self.c2, self.l, self.nu + [0.1, -0.1, 0.05], self.h * 0.9)
        pilot = self.x
        value = operator_mismatch(other, self.c, pilot, data_covariance=0.5)
        eye = np.eye(self.n)
        H = np.column_stack([other.apply(eye[:, j]) - self.c.apply(eye[:, j]) for j in range(self.n)])
        np.testing.assert_allclose(value["operator_frobenius_squared"], np.linalg.norm(H)**2, atol=1e-11)
        np.testing.assert_allclose(value["pilot_mismatch"], np.linalg.norm(H @ pilot)**2, atol=1e-11)
        np.testing.assert_allclose(value["sp_weighted_mismatch"], np.linalg.norm(H @ pilot)**2 + 0.5 * np.linalg.norm(H)**2, atol=1e-11)
        covariance = np.diag(np.linspace(0.1, 0.9, self.n))
        full = operator_mismatch(other, self.c, pilot, data_covariance=covariance)
        np.testing.assert_allclose(full["data_mismatch"], np.trace(H @ covariance @ H.conj().T).real, atol=1e-11)
        mean = self.rng.normal(size=self.n)
        biased = operator_mismatch(other, self.c, pilot, data_covariance=covariance, data_mean=mean)
        np.testing.assert_allclose(biased["pilot_mismatch"], np.linalg.norm(H @ (pilot + mean))**2, atol=1e-11)
        with self.assertRaises(ValueError):
            operator_mismatch(other, self.c, pilot, data_covariance=-np.eye(self.n))

    def test_real_tangent_gain_and_projection(self):
        B, dB = response_matrix(self.x, self.l, self.nu, self.c1, self.c2, derivative=True)
        alpha = self.rng.normal(size=len(self.h))
        beta = self.rng.normal(size=len(self.h))
        dnu = self.rng.normal(size=len(self.h))
        tangent = B @ alpha + 1j * B @ beta + (dB * self.h[None, :]) @ dnu
        result = real_tangent_projection(tangent, B, dB, self.h)
        np.testing.assert_allclose(result["projection_fraction"], 1.0, atol=1e-11)
        self.assertLessEqual(result["tangent_rank"], 3 * len(self.h))
        controls = isotropic_real_controls(tangent, B, dB, self.h, count=8, seed=1)
        self.assertEqual(controls.shape, (8,))
        self.assertTrue(np.all((controls >= 0) & (controls <= 1 + 1e-12)))

    def test_search_and_validation(self):
        pilot = self.x
        symbols = self.rng.normal(size=self.n) + 1j * self.rng.normal(size=self.n)
        c = Channel(self.n, self.c1, self.c2, self.l, self.nu, self.h)
        y = c.apply(pilot + symbols)
        center = self.nu + [0.08, -0.05, 0.05]
        bounds = np.column_stack((center - 0.2, center + 0.2))
        fit = fit_true_data(y, pilot, symbols, self.l, center, bounds,
                            self.c1, self.c2, 0.2, passes=3, maxiter=16)
        self.assertGreater(fit["evaluations"], fit["starts_count"])
        self.assertLess(fit["score"], 1e-3)
        self.assertEqual(fit["objective"], "profile")
        self.assertTrue(np.all(fit["dopplers"] >= bounds[:, 0]))
        self.assertTrue(np.all(fit["dopplers"] <= bounds[:, 1]))
        with self.assertRaises(ValueError):
            axial_grid_starts(center, bounds[::-1])
        with self.assertRaises(ValueError):
            search_geometry(np.ones(self.n), self.x, self.l, center, bounds,
                            self.c1, self.c2, 0.2, objective="ridge")
        with self.assertRaises(ValueError):
            score_geometry(np.ones(self.n), np.zeros((self.n, 1)), 0.2)
        with self.assertRaises(ValueError):
            operator_mismatch(c, c, pilot, data_covariance=-1)
        np.testing.assert_array_equal(final_refit_bounds([2.8, -2.8]), [[2.05, 3], [-3, -2.05]])
        np.testing.assert_array_equal(final_refit_bounds([2.8], expanded=True), [[-3, 3]])

    def test_matched_legal_error_transplant(self):
        truth = np.zeros(2 * self.n, dtype=np.uint8)
        wrong = truth.copy()
        wrong[:2] = 1
        success = truth.copy()
        success[2:4] = 1
        mapper = lambda b: ((1 - 2 * b[0::2].astype(float)) +
                            1j * (1 - 2 * b[1::2].astype(float))) / np.sqrt(2)
        legal = lambda b: np.count_nonzero(b) % 2 == 0
        control = transplant_legal_error_contrast(truth, wrong, success,
                    is_legal=legal, bits_to_symbols=mapper, success_channel=self.c)
        self.assertEqual(control["hamming_weight"], 2)
        self.assertTrue(legal(control["bits"]))
        expected = daft(self.c.apply(mapper(success) - mapper(control["bits"])),
                        self.c1, self.c2, True)
        np.testing.assert_allclose(control["contrast_time"], expected)

    def test_exact_code_sparse_covariance_and_operator(self):
        # Six coded bits map to three QPSK symbols, with a repeated I/Q row.
        G = np.eye(6, dtype=np.uint8)
        G[4] = G[0]
        pd = 0.5
        moments = exact_code_moments(G, pd)
        self.assertTrue(moments['zero_mean'])
        self.assertFalse(moments['scalar_covariance'])
        self.assertEqual(moments['covariance_offdiagonal_count'], 2)
        C = pd * np.eye(3, dtype=complex)
        sparse = moments['covariance']
        for i, j, value in zip(sparse['rows'], sparse['cols'], sparse['values']):
            C[i, j] += value
        np.testing.assert_allclose(C[0, 1], -0.25j)
        # Monte Carlo over all uniform information words is an independent
        # check of the generator-row covariance derivation.
        words = np.array([[(v >> bit) & 1 for bit in range(6)] for v in range(64)], np.uint8)
        coded = (words @ G.T) % 2
        mapped = np.sqrt(pd / 2) * ((1 - 2 * coded[:, :3].astype(float)) +
                                    1j * (1 - 2 * coded[:, 3:].astype(float)))
        np.testing.assert_allclose(mapped.mean(axis=0), moments['mean'], atol=1e-14)
        np.testing.assert_allclose(mapped.T @ mapped.conj() / 64, C, atol=1e-14)
        other = Channel(self.n, self.c1, self.c2, self.l, self.nu + 0.1, self.h * 0.9)
        # Pad the small code's exact covariance with independent symbols.
        sparse_padded = dict(diagonal=pd, rows=sparse['rows'], cols=sparse['cols'],
                             values=sparse['values'])
        dense = pd * np.eye(self.n, dtype=complex)
        dense[:3, :3] = C
        expected = operator_mismatch(other, self.c, self.x, data_covariance=dense)
        actual = operator_mismatch(other, self.c, self.x, data_covariance=sparse_padded)
        np.testing.assert_allclose(actual['sp_weighted_mismatch'], expected['sp_weighted_mismatch'], atol=1e-11)
        indefinite = dict(diagonal=pd, rows=np.array([0, 1]), cols=np.array([1, 0]),
                          values=np.array([1.0, 1.0]))
        with self.assertRaises(ValueError):
            operator_mismatch(other, self.c, self.x, data_covariance=indefinite)


if __name__ == "__main__":
    unittest.main()
