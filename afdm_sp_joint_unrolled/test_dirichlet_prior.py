"""Unit contracts for the fixed-support Dirichlet shrinkage prior."""

import numpy as np
import pytest

from afdm_sp_joint_unrolled.dirichlet_prior import (
    _dirichlet_coefficients, build_precision, covariance,
)


def test_covariance_coefficients_match_direct_dft_with_physical_sign():
    n = 1024
    offsets = np.array([-2, -1, 0, 1, 3])
    time = np.arange(n)
    kappa_sample = 0.23
    direct_sample = np.exp(
        2j * np.pi * (kappa_sample - offsets[:, None]) * time / n
    ).mean(axis=1)
    closed_sample = _dirichlet_coefficients(
        n, offsets, np.array([kappa_sample])
    )[0]
    np.testing.assert_allclose(closed_sample, direct_sample, atol=4e-14, rtol=4e-14)
    wrong_sample = np.exp(
        2j * np.pi * (kappa_sample + offsets[:, None]) * time / n
    ).mean(axis=1)
    assert np.max(abs(closed_sample - wrong_sample)) > 0.4

    nodes, weights = np.polynomial.legendre.leggauss(128)
    kappa = nodes / 2
    direct = np.stack([
        np.exp(2j * np.pi * (kappa_i - offsets[:, None]) * time / n).mean(axis=1)
        for kappa_i in kappa
    ])
    expected = direct.T @ ((weights / 2)[:, None] * direct.conj())
    np.testing.assert_allclose(covariance(n, offsets), expected, atol=4e-14, rtol=4e-14)


@pytest.mark.parametrize("kind", ["dirichlet", "diagonal"])
def test_precision_is_positive_and_globally_trace_matched(kind):
    result = build_precision(
        1024,
        delays=[0, 0, 0, 3, 3],
        dopplers=[-1, 0, 2, 4, 5],
        initial_gains=[1, 3, 2, 2j, 1],
        kind=kind,
    )
    precision = result["precision"]
    prior_covariance = result["covariance"]
    np.testing.assert_allclose(precision, precision.conj().T, atol=1e-14)
    np.testing.assert_allclose(prior_covariance, prior_covariance.conj().T, atol=1e-14)
    assert np.linalg.eigvalsh(precision).min() > 0
    assert np.linalg.eigvalsh(prior_covariance).min() >= 0.05 - 1e-13
    assert np.trace(precision).real == pytest.approx(5.0)
    assert np.trace(prior_covariance).real == pytest.approx(5.25)
    if kind == "diagonal":
        np.testing.assert_array_equal(prior_covariance, np.diag(np.diag(prior_covariance)))


def test_delay_blocks_are_separate_and_ridge_is_exact_identity():
    arguments = dict(
        n=1024,
        delays=[2, 7, 2, 7],
        dopplers=[0, 3, 1, 4],
        initial_gains=[2, 4, 1, 1],
    )
    structured = build_precision(**arguments)
    np.testing.assert_array_equal(structured["covariance"][np.ix_([0, 2], [1, 3])], 0)
    np.testing.assert_array_equal(structured["precision"][np.ix_([0, 2], [1, 3])], 0)
    ridge = build_precision(**arguments, kind="ridge")
    np.testing.assert_array_equal(ridge["covariance"], np.eye(4))
    np.testing.assert_array_equal(ridge["precision"], np.eye(4))


def test_centres_use_gain_argmax_smallest_bin_tie_and_are_permutation_equivariant():
    delays = np.array([4, 1, 4, 1, 4])
    dopplers = np.array([3, 8, -2, 5, 0])
    gains = np.array([2, 7, -2j, -7j, 0.5])
    result = build_precision(1024, delays, dopplers, gains)
    np.testing.assert_array_equal(result["centers"], [-2, 5, -2, 5, -2])

    permutation = np.array([3, 0, 4, 1, 2])
    permuted = build_precision(1024, delays[permutation], dopplers[permutation], gains[permutation])
    np.testing.assert_array_equal(permuted["centers"], result["centers"][permutation])
    np.testing.assert_allclose(
        permuted["covariance"], result["covariance"][np.ix_(permutation, permutation)]
    )
    np.testing.assert_allclose(
        permuted["precision"], result["precision"][np.ix_(permutation, permutation)]
    )


def test_precision_matches_direct_augmented_least_squares_objective():
    torch = pytest.importorskip("torch")
    from afdm_sp_joint_unrolled.classical_joint_unrolled import soft_gain_update

    rng = np.random.default_rng(91)
    a = rng.normal(size=(12, 4)) + 1j * rng.normal(size=(12, 4))
    y = rng.normal(size=12) + 1j * rng.normal(size=12)
    previous = rng.normal(size=4) + 1j * rng.normal(size=4)
    precision = build_precision(
        1024, [0, 0, 2, 2], [-1, 0, 3, 5], [1, 2, 4, 1]
    )["precision"]
    strength, proximal = 0.17, 0.03
    values, vectors = np.linalg.eigh(precision)
    square_root = np.sqrt(values)[:, None] * vectors.conj().T
    augmented_a = np.vstack((a, np.sqrt(strength) * square_root, np.sqrt(proximal) * np.eye(4)))
    augmented_y = np.concatenate((y, np.zeros(4), np.sqrt(proximal) * previous))
    expected = np.linalg.lstsq(augmented_a, augmented_y, rcond=None)[0]

    actual = soft_gain_update(
        torch.as_tensor(a, dtype=torch.complex128),
        torch.as_tensor(y, dtype=torch.complex128),
        torch.as_tensor(previous, dtype=torch.complex128),
        torch.tensor(proximal, dtype=torch.float64),
        Q=torch.as_tensor(strength * precision, dtype=torch.complex128),
    )
    np.testing.assert_allclose(actual.detach().numpy(), expected, atol=2e-12, rtol=2e-12)


@pytest.mark.parametrize(
    "call",
    [
        lambda: covariance(0, [0]),
        lambda: covariance(16.0, [0]),
        lambda: covariance(16, [0, 0]),
        lambda: covariance(16, [0.2]),
        lambda: covariance(16, [0], quadrature=0),
        lambda: build_precision(16, [0], [0], [1], kind="unknown"),
        lambda: build_precision(16, [0], [0], [1], kind=[]),
        lambda: build_precision(16, [0, 0], [1, 1], [1, 2]),
        lambda: build_precision(16, [0, 0], [-1, 15], [1, 2]),
        lambda: build_precision(16, [-1], [0], [1]),
        lambda: build_precision(16, [16], [0], [1]),
        lambda: build_precision(16, [0], [np.inf], [1]),
        lambda: build_precision(16, [0], [0], [np.nan]),
        lambda: build_precision(16, [0], [0], [1], epsilon=0),
        lambda: build_precision(16, [0, 1], [0], [1, 2]),
    ],
)
def test_invalid_inputs_fail_explicitly(call):
    with pytest.raises(ValueError):
        call()
