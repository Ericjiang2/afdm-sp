"""Tiny source-reconciliation fixtures, not F2 receiver qualification."""

import numpy as np

from f2_algebra import (complex_adjoint, gaussian_input_posterior,
                        gaussian_output_precision)


def test_prior_variance_not_precision():
    u, v_u, delta = 1 + 2j, 0.5, 2.0
    mean, variance = gaussian_input_posterior(u, v_u, delta)
    np.testing.assert_allclose(mean, u * delta / (delta + v_u))
    np.testing.assert_allclose(variance, delta * v_u / (delta + v_u))
    assert abs(mean - u / (delta * v_u + 1)) > 0.1
    assert abs(variance - v_u / (delta * v_u + 1)) > 0.1


def test_printed_output_variance_is_negative():
    beta, v_p = 4.0, 0.2
    precision = gaussian_output_precision(beta, v_p)
    derivative = -precision
    literal_v_s = v_p * derivative
    assert precision > 0 and literal_v_s < 0
    np.testing.assert_allclose(precision, 1 / (1 / beta + v_p))


def test_complex_model_requires_conjugate_adjoint():
    phi = np.array([[1 + 2j, 2 - 1j], [3 + 1j, -1 + 4j]])
    h = np.array([0.2 + 0.6j, -0.4 + 0.1j])
    s = np.array([0.7 - 0.3j, 0.1 + 0.9j])
    np.testing.assert_allclose(np.vdot(phi @ h, s), np.vdot(h, complex_adjoint(phi, s)))
    assert not np.allclose(complex_adjoint(phi, s), phi.T @ s)


def test_beta_mode_uses_observation_dimension_not_grid_size():
    n, grid_size, receive_antennas = 3, 2, 1
    d, e = 1.1, 0.1
    gaussian_mode = (n * receive_antennas + d - 1) / e
    printed_mode = (grid_size * receive_antennas + d - 1) / e
    def log_joint(beta: float) -> float:
        return float((n * receive_antennas + d - 1) * np.log(beta) - e * beta)
    assert gaussian_mode == 31.0 or np.isclose(gaussian_mode, 31.0)
    assert np.isclose(printed_mode, 21.0)
    assert log_joint(gaussian_mode) > log_joint(printed_mode)


def test_grid_quadratic_requires_covariance_transpose_for_complex_model():
    derivative_columns = np.array([[1 + 0j, 1j]])
    mean = np.array([1 + 0j, 1j])
    displacement = np.array([1.0, 1.0])
    gram = derivative_columns.conj().T @ derivative_columns
    second_moment = np.outer(mean, mean.conj())
    direct = float(np.linalg.norm(derivative_columns @ (displacement * mean)) ** 2)
    printed = float(displacement @ np.real(gram * second_moment) @ displacement)
    transposed = float(displacement @ np.real(gram * second_moment.T) @ displacement)
    assert direct == 0.0
    assert printed == 4.0
    assert transposed == direct
