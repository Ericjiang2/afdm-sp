"""Deterministic small-reference F2 checks; no observed frame or receiver call."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"))
sys.path.insert(0, str(ROOT / "experiments/tf_cstate_validation_20260922"))
sys.path.insert(0, str(ROOT / "experiments/cstate_necessity_stageB_20260928"))

from physical import Channel, regressors  # noqa: E402
import f2_estimator as f2  # noqa: E402
from geometry_validation import reopen_geometry, Path as GeometryPath  # noqa: E402
from f2_core import corrected_gamp_posterior, full_gesbl_posterior  # noqa: E402


def _constants(n: int) -> tuple[float, float]:
    return 5 / (2 * n), (np.sqrt(2) - 1) / (2 * n * n)


def test_single_integer_and_multi_fractional_same_delay() -> None:
    n = 16
    c1, c2 = _constants(n)
    x = np.full(n, 0.5 + 0.5j)
    for delays, nus, gains in (
        ([2], [1.0], [0.6 + 0.2j]),
        ([2, 2, 4], [0.25, 1.25, -1.5], [0.6 + 0.2j, -0.1 + 0.4j, 0.3 - 0.2j]),
    ):
        channel = Channel(n, c1, c2, delays, nus, gains)
        phi = regressors(x, channel.delays, channel.dopplers, c1, c2)
        assert phi.shape == (n, channel.p)
        assert np.allclose(phi @ channel.gains, channel.apply(x), atol=1e-10, rtol=1e-10)
        assert np.allclose(f2.dense_channel(channel) @ x, channel.apply(x),
                           atol=1e-10, rtol=1e-10)
        if channel.p > 1:
            assert channel.delays[0] == channel.delays[1]
            assert not np.array_equal(phi[:, 0], phi[:, 1])


def test_gamp_scalar_variance_is_declared_approximation() -> None:
    """Even Phi=[1] has a GAMP variance fixed point distinct from exact Bayes."""
    phi = np.array([[1 + 0j]])
    y = np.array([1 + 0.25j])
    delta = np.array([2.0])
    beta = 4.0
    config = f2.F2Config(qmax=100, epsilon_q=0.0)
    full_mean, full_cov, _ = f2._posterior(phi, y, delta, beta, "full", config)
    gamp_mean, gamp_var, details = f2._posterior(phi, y, delta, beta, "gamp", config)

    exact_var = 1 / (beta + 1 / delta[0])
    assert abs(full_cov[0, 0] - exact_var) <= 1e-12
    assert abs(full_mean[0] - beta * exact_var * y[0]) <= 1e-12
    # Independent literal variance recursion of the corrected Alg.3. The
    # Onsager V_P term re-enters V_U, so this is not the exact covariance.
    variance = delta[0]
    for _ in range(details["iterations"]):
        v_u = 1 / beta + variance
        variance = delta[0] * v_u / (delta[0] + v_u)
    assert abs(gamp_var[0] - variance) <= 1e-12
    assert abs(gamp_var[0] - exact_var) > 0.1
    assert np.isfinite(gamp_mean).all() and gamp_var[0] > 0


def test_old_dense_variance_discrepancy_is_same_declared_recursion() -> None:
    rng = np.random.default_rng(928)
    phi = (rng.normal(size=(32, 8)) + 1j * rng.normal(size=(32, 8))) / np.sqrt(64)
    y = rng.normal(size=32) + 1j * rng.normal(size=32)
    delta = np.full(8, 0.8)
    full_mean, full_cov = full_gesbl_posterior(phi, y, delta, 2.5)
    old_mean, old_var = corrected_gamp_posterior(
        phi, y, delta, 2.5, iterations=200, damping_s=.5, damping_h=.5)
    new_mean, new_var, inner = f2._posterior(
        phi, y, delta, 2.5, "gamp", f2.F2Config(qmax=200, epsilon_q=0))
    assert 2 <= inner["iterations"] <= 200
    assert np.allclose(new_mean, old_mean, rtol=0, atol=1e-12)
    assert np.allclose(new_var, old_var, rtol=0, atol=1e-12)
    assert np.linalg.norm(full_mean - old_mean) / np.linalg.norm(full_mean) < 1e-8
    discrepancy = np.linalg.norm(np.diag(full_cov).real - old_var) / \
        np.linalg.norm(np.diag(full_cov).real)
    assert 0.03 < discrepancy < 0.04  # original 0.0363 is reproducible


def test_support_activation_deactivation_and_ties() -> None:
    # n=8, m=4 gives Rbar=floor(8/log 4)=4, so use n=4 -> Rbar=2.
    first = f2.active_indices(np.array([0.8, 0.6, 0.4, 0.2]), 4)
    second = f2.active_indices(np.array([0.8, 0.1, 0.9, 0.2]), 4)
    tie = f2.active_indices(np.array([1.0, 1.0, 0.5, 0.1]), 4)
    assert first.tolist() == [0, 1]
    assert second.tolist() == [2, 0]  # atom 1 exits; atom 2 enters
    assert tie.tolist() == [0, 1]


def test_grid_expected_loss_quadratic() -> None:
    n = 16
    c1, c2 = _constants(n)
    x = np.full(n, 0.5 - 0.5j)
    delays = np.array([1, 1, 3])
    nus = np.array([0.0, 1.0, -1.0])
    phi = regressors(x, delays, nus, c1, c2)
    derivative = Channel(n, c1, c2, delays, nus, np.ones(3)).regressors(
        x, derivative=True)
    mean = np.array([0.6 + 0.2j, -0.3 + 0.1j, 0.1 - 0.2j])
    covariance = np.array([[0.5, 0.1j, 0], [-0.1j, 0.4, 0.05],
                           [0, 0.05, 0.3]], dtype=complex)
    y = phi @ mean + np.linspace(-0.1, 0.1, n)
    captured: dict = {}

    def capture(q, alpha, bounds, _config):
        captured.update(q=q.copy(), alpha=alpha.copy(), bounds=bounds)
        return np.zeros(3), {"iterations": 0, "objective": 0.0,
                             "max_shift": 0.0, "termination_reason": "synthetic"}

    with patch.object(f2, "_solve_grid_qp", capture):
        updated, _ = f2._grid_update(y, x, phi, delays, nus, mean, covariance,
                                     np.arange(3), c1, c2, -2, 2, f2.FROZEN)
    assert np.array_equal(updated, nus)
    kappa = np.array([0.15, -0.2, 0.08])
    shifted = phi + derivative * kappa
    def expected_loss(matrix):
        residual = y - matrix @ mean
        return float(np.vdot(residual, residual).real +
                     np.trace(matrix @ covariance @ matrix.conj().T).real)
    direct_change = expected_loss(shifted) - expected_loss(phi)
    quadratic_change = float(kappa @ captured["q"] @ kappa -
                             2 * captured["alpha"] @ kappa)
    assert abs(direct_change - quadratic_change) <= 1e-10
    assert np.linalg.eigvalsh(captured["q"]).min() >= -1e-10


def test_em_hyperparameters_pilot_feedback_and_caps() -> None:
    n = 16
    c1, c2 = _constants(n)
    pilot = np.full(n, 0.5 + 0.5j)
    truth = Channel(n, c1, c2, [1], [0.0], [0.8 + 0.1j])
    y = truth.apply(pilot + np.full(n, 0.5 - 0.5j))
    sigma2 = 0.1
    config = f2.F2Config(qmax=2, imax=1, tmax=2)

    def no_grid(_y, _x, _phi, _delays, nus, _mean, _covariance, _selected,
                _c1, _c2, _lo, _hi, _config):
        return nus.copy(), {"iterations": 0, "objective": 0.0,
                             "max_shift": 0.0, "termination_reason": "synthetic",
                             "original_kkt_projected_inf": 0.0,
                             "scaled_kkt_projected_inf": 0.0}

    with patch.object(f2, "_grid_update", no_grid):
        result = f2.estimate(y, pilot, sigma2, c1, c2, max_delay=1,
                             nu_min=-1, nu_max=1, config=config)
    assert len(result["passes"]) == 2
    assert np.array_equal(result["passes"][0]["feedback"], np.zeros(n))
    assert np.all(np.isin(result["passes"][1]["feedback"].real, [-0.5, 0.5]))
    assert np.all(np.isin(result["passes"][1]["feedback"].imag, [-0.5, 0.5]))
    assert result["timing"]["component_calls"]["lmmse"] == 1
    assert result["timing"]["component_calls"]["grid"] == 2
    assert result["cap_hits"]["em"] == 2 and result["cap_hits"]["data"]
    assert result["cap_hits"]["gamp"] >= 1
    assert np.isfinite(result["delta"]).all() and np.all(result["delta"] > 0)
    assert np.isfinite(result["beta"]) and result["beta"] > 0

    delays, nus = f2.initial_grid(1, -1, 1)
    phi = regressors(pilot, delays, nus, c1, c2)
    m = len(nus)
    delta0 = max(1e-12, n * max(float(np.vdot(y, y).real) / n - sigma2,
                                sigma2) / (m * float(np.vdot(pilot, pilot).real)))
    initial_delta = np.full(m, delta0)
    mean0, variance0, _ = f2._posterior(phi, y, initial_delta, 1 / sigma2,
                                        "gamp", config)
    energy = abs(mean0) ** 2 + variance0
    b = 1e-6 / delta0
    expected_delta = np.maximum(2 * energy / (np.sqrt(1 + 4 * b * energy) + 1),
                                max(1e-15, 1e-12 * delta0))
    residual = y - phi @ mean0
    expected_beta = n / (1e-6 * sigma2 + float(np.vdot(residual, residual).real)
                         + float(np.dot(np.sum(abs(phi) ** 2, axis=0), variance0)))
    with patch.object(f2, "_grid_update", no_grid):
        single = f2.estimate(y, pilot, sigma2, c1, c2, max_delay=1,
                             nu_min=-1, nu_max=1,
                             config=f2.F2Config(qmax=2, imax=1, tmax=1))
    assert np.allclose(single["delta"], expected_delta, rtol=1e-12, atol=1e-12)
    assert np.isclose(single["beta"], expected_beta, rtol=1e-12, atol=1e-12)


def test_p155_local_and_cstate_entry_contract() -> None:
    """Check actual frozen geometry front door without a TF/decoder or edit search."""
    n = 1024
    c1, c2 = _constants(n)
    delays, nus = f2.initial_grid(102, -3, 3)
    paths = [GeometryPath(int(delay), float(nu))
             for delay, nu in zip(delays[:155], nus[:155], strict=True)]
    pilot = np.full(n, 0.5 + 0.5j)
    time_observed = np.zeros(n, dtype=complex)
    variance = np.full(n, 0.25)
    common = dict(c1=c1, c2=c2, ridge=0.1, max_delay=102,
                  doppler_min=-3., doppler_max=3., grid_step=.25,
                  max_edits=0, local_passes=0, duplicate_tolerance=1e-6)
    for strategy in ("direct", "compact"):
        result = reopen_geometry(time_observed, pilot, variance, paths,
                                 strategy=strategy, **common)
        assert len(result.paths) == len(result.gains) == 155
        assert result.paths == paths
        assert np.isfinite(result.gains).all()
        assert result.diagnostics["numerical_fallback"] is False


if __name__ == "__main__":
    test_single_integer_and_multi_fractional_same_delay()
    test_gamp_scalar_variance_is_declared_approximation()
    test_old_dense_variance_discrepancy_is_same_declared_recursion()
    test_support_activation_deactivation_and_ties()
    test_grid_expected_loss_quadratic()
    test_em_hyperparameters_pilot_feedback_and_caps()
    test_p155_local_and_cstate_entry_contract()
    print("F2 extended small-reference qualification passed; zero real receiver calls")
