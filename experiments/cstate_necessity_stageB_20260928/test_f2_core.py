"""Small, deterministic reference checks; no receiver or decoder."""

import numpy as np
from pathlib import Path
import sys

from f2_core import corrected_gamp_posterior, full_gesbl_posterior

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sp_afdm_frozen_20260920/src"))
from physical import Channel  # noqa: E402


def test_siso_cpp_measurement_columns_match_channel_apply():
    n = 63
    rng = np.random.default_rng(929)
    x = rng.normal(size=n) + 1j * rng.normal(size=n)
    c1, c2 = 5 / (2 * n), (np.sqrt(2) - 1) / (2 * n * n)
    channel = Channel(n, c1, c2, [4, 4, 15], [-1.3, 0.7, 2.1],
                      [0.4 + 0.1j, -0.2j, 0.3 - 0.5j])
    np.testing.assert_allclose(channel.regressors(x) @ channel.gains,
                               channel.apply(x), rtol=0, atol=2e-13)


def test_siso_full_posterior_and_gamp_mean_on_complex_diagonal():
    phi = np.diag(np.array([1 + 0.4j, -0.6 + 0.8j, 0.5 - 0.2j]))
    y = np.array([0.2 - 0.9j, 1.1 + 0.3j, -0.4 + 0.2j])
    delta = np.array([0.8, 1.3, 0.4])
    beta = 2.5
    exact_mean, covariance = full_gesbl_posterior(phi, y, delta, beta)
    expected = delta * phi.diagonal().conj() * y / (
        abs(phi.diagonal()) ** 2 * delta + 1 / beta)
    np.testing.assert_allclose(exact_mean, expected, rtol=0, atol=1e-14)
    np.testing.assert_allclose(np.diag(covariance).real,
        delta / (1 + beta * abs(phi.diagonal()) ** 2 * delta), rtol=0, atol=1e-14)
    approximate_mean, approximate_variance = corrected_gamp_posterior(
        phi, y, delta, beta, iterations=100, damping_s=0.5, damping_h=0.5)
    np.testing.assert_allclose(approximate_mean, exact_mean, rtol=0, atol=1e-10)
    assert np.all(approximate_variance > 0)


def test_full_reference_preserves_hermitian_covariance():
    phi = np.array([[1 + 1j, 0.2], [0.1 - 0.3j, 1 - 0.4j], [0.5, -0.2j]])
    y = np.array([0.4 + 0.2j, -0.8j, 0.1])
    mean, covariance = full_gesbl_posterior(phi, y, np.array([0.8, 1.1]), 3.0)
    np.testing.assert_allclose(covariance, covariance.conj().T, atol=1e-14)
    assert np.isfinite(mean).all() and np.linalg.eigvalsh(covariance).min() > 0


def test_small_dense_siso_gamp_vs_full_reference():
    rng = np.random.default_rng(928)
    phi = (rng.normal(size=(32, 8)) + 1j * rng.normal(size=(32, 8))) / np.sqrt(64)
    y = rng.normal(size=32) + 1j * rng.normal(size=32)
    delta = np.full(8, 0.8)
    exact_mean, exact_covariance = full_gesbl_posterior(phi, y, delta, 2.5)
    approximate_mean, approximate_variance = corrected_gamp_posterior(
        phi, y, delta, 2.5, iterations=200, damping_s=0.5, damping_h=0.5)
    mean_relative_error = np.linalg.norm(exact_mean - approximate_mean) / np.linalg.norm(exact_mean)
    variance_relative_error = (np.linalg.norm(np.diag(exact_covariance).real - approximate_variance)
                               / np.linalg.norm(np.diag(exact_covariance).real))
    assert mean_relative_error < 1e-8
    assert variance_relative_error < 0.1  # GAMP diagonal approximation, not exact covariance
