"""Regression for cancellation in the exact structured trace normalization."""
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sp_afdm_frozen_20260920/src"))
from structured_stop import StructuredLE, old


class StructuredTraceTest(unittest.TestCase):
    def test_small_variance_and_cyclic_border(self):
        rng = np.random.default_rng(17)
        n = 16
        matrix = sparse.eye(n, format="csc", dtype=complex) + 0.4 * sparse.coo_matrix(
            (np.exp(1j * np.arange(n)), (np.arange(n), (np.arange(n) - 3) % n)), shape=(n, n))
        y = rng.normal(size=n) + 1j * rng.normal(size=n)
        mean = rng.normal(size=n) + 1j * rng.normal(size=n)
        for variance in (0.3, 1e-8, 1e-10):
            with self.subTest(variance=variance):
                actual, tau = StructuredLE(matrix, y, 0.2, 3).extrinsic(mean, variance)
                expected, expected_tau = old.LinearOAMP(matrix, y, 0.2).extrinsic(mean, variance)
                np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-10)
                np.testing.assert_allclose(tau, expected_tau, rtol=1e-9, atol=1e-10)

    def test_identity_and_dense_border(self):
        matrix = sparse.eye(8, format="csc", dtype=complex) * 2
        y = np.arange(8) * (1 + 1j)
        for bandwidth in (0, 4):
            with self.subTest(bandwidth=bandwidth):
                center, tau = StructuredLE(matrix, y, 0.2, bandwidth).extrinsic(y, 1e-10)
                np.testing.assert_allclose(center, y / 2, rtol=1e-9, atol=1e-10)
                np.testing.assert_allclose(tau, 0.05, rtol=1e-9, atol=1e-10)


if __name__ == "__main__":
    unittest.main()
