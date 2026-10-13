"""Fixed, synthetic-only qualification for the corrected F2 specialization."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"))

from physical import Channel  # noqa: E402
from twofft import scalar_joint  # noqa: E402
from f2_estimator import (  # noqa: E402
    F2Config, channel_change_squared, dense_channel, estimate, hard_qpsk,
    lmmse_hard_data,
)


def qpsk(rng: np.random.Generator, n: int) -> np.ndarray:
    return 0.5 * rng.choice([-1, 1], n) + 0.5j * rng.choice([-1, 1], n)


def case_q1() -> dict:
    n = 32
    rng = np.random.default_rng(2026092801)
    c1, c2 = 5 / (2 * n), (np.sqrt(2) - 1) / (2 * n * n)
    channel = Channel(n, c1, c2, [1, 1, 3], [0.25, 1.25, -1.5],
                      [0.75 + 0.2j, 0.3 - 0.1j, 0.5 + 0.4j])
    pilot = qpsk(rng, n)
    # Fourth-order stencil avoids the frozen two-point verifier's O(h^2)
    # truncation while keeping its original rtol/atol gate unchanged.
    h = 1e-3
    columns = channel.regressors(pilot)
    dense = dense_channel(channel)
    action_error = np.linalg.norm(dense @ pilot - columns @ channel.gains)
    adjoint_error = np.linalg.norm(dense.conj().T @ pilot - channel.adjoint(pilot))
    derivative = channel.regressors(pilot, derivative=True)
    numerical = np.empty_like(derivative)
    for j in range(channel.p):
        def response(offset: float, column: int = j) -> np.ndarray:
            shifted = channel.dopplers.copy()
            shifted[column] += offset
            return Channel(n, c1, c2, channel.delays, shifted,
                           channel.gains).regressors(pilot)[:, column]
        numerical[:, j] = (-response(2 * h) + 8 * response(h)
                           - 8 * response(-h) + response(-2 * h)) / (12 * h)
    derivative_error = np.linalg.norm(derivative - numerical) / np.linalg.norm(derivative)
    assert np.allclose(dense @ pilot, columns @ channel.gains, rtol=1e-10, atol=1e-10)
    assert np.allclose(dense.conj().T @ pilot, channel.adjoint(pilot),
                       rtol=1e-10, atol=1e-10)
    assert np.allclose(derivative, numerical, rtol=1e-10, atol=1e-10)
    return {"action_error": float(action_error), "adjoint_error": float(adjoint_error),
            "derivative_relative_error": float(derivative_error)}


def case_q2() -> dict:
    rng = np.random.default_rng(2026092802)
    raw = rng.normal(size=(12, 4)) + 1j * rng.normal(size=(12, 4))
    phi, _ = np.linalg.qr(raw)
    y = rng.normal(size=12) + 1j * rng.normal(size=12)
    delta = np.array([0.4, 0.8, 1.2, 0.6])
    from f2_estimator import _posterior  # noqa: PLC0415 - exact local qualification
    full_mean, full_cov, _ = _posterior(phi, y, delta, 5.0, "full", F2Config())
    gamp_mean, gamp_variance, details = _posterior(phi, y, delta, 5.0,
                                                   "gamp", F2Config())
    assert np.isfinite(full_mean).all() and np.isfinite(gamp_mean).all()
    assert np.all(np.diag(full_cov).real > 0) and np.all(gamp_variance > 0)
    return {"mean_relative_error": float(np.linalg.norm(full_mean - gamp_mean)
                                         / np.linalg.norm(full_mean)),
            "full_residual": float(np.linalg.norm(y - phi @ full_mean)),
            "gamp_residual": float(np.linalg.norm(y - phi @ gamp_mean)),
            "variance_relative_error": float(np.linalg.norm(np.diag(full_cov).real
                                                              - gamp_variance)
                                             / np.linalg.norm(np.diag(full_cov).real)),
            "full_support": np.argsort(-abs(full_mean)).tolist(),
            "gamp_support": np.argsort(-abs(gamp_mean)).tolist(),
            "gamp_iterations": details["iterations"]}


def case_q3() -> dict:
    n = 64
    rng = np.random.default_rng(2026092803)
    c1, c2 = 5 / (2 * n), (np.sqrt(2) - 1) / (2 * n * n)
    pilot = qpsk(rng, n)
    data = qpsk(rng, n)
    truth = Channel(n, c1, c2, [1, 3], [-1.0, 2.0],
                    [0.75 + 0.2j, 0.5 + 0.4j])
    sigma2 = 0.1
    noise = np.sqrt(sigma2 / 2) * (rng.normal(size=n) + 1j * rng.normal(size=n))
    y = truth.apply(pilot + data) + noise
    config = F2Config(tmax=2)  # fixed synthetic one-feedback slice of frozen method
    kwargs = dict(max_delay=4, nu_min=-2.0, nu_max=2.0, config=config)
    full = estimate(y, pilot, sigma2, c1, c2, mode="full", **kwargs)
    gamp = estimate(y, pilot, sigma2, c1, c2, mode="gamp", **kwargs)
    heff_error = float(np.sqrt(channel_change_squared(gamp["channel"], full["channel"])))
    full_residual = full["passes"][-1]["predictive_residual"]
    gamp_residual = gamp["passes"][-1]["predictive_residual"]
    residual_error = abs(gamp_residual - full_residual) / max(full_residual, 1e-30)
    variance_error = float(np.median(abs(gamp["posterior_variance"]
                                         - full["posterior_variance"])
                                     / np.maximum(full["posterior_variance"], 1e-30)))
    assert np.isfinite([heff_error, residual_error, variance_error]).all()
    assert np.all(gamp["dopplers"] >= -2 - 1e-12)
    assert np.all(gamp["dopplers"] <= 2 + 1e-12)
    assert len(full["passes"]) == len(gamp["passes"]) == 2
    assert heff_error <= 0.10
    assert residual_error <= 0.10
    assert variance_error <= 0.20
    return {"heff_relative_error": heff_error,
            "predictive_residual_relative_error": residual_error,
            "median_diagonal_variance_relative_error": variance_error,
            "support_symmetric_difference": sorted(set(full["selected"].tolist())
                                                   ^ set(gamp["selected"].tolist())),
            "full_cap_hits": full["cap_hits"], "gamp_cap_hits": gamp["cap_hits"],
            "full_passes": len(full["passes"]), "gamp_passes": len(gamp["passes"]),
            "full_timing": full["timing"], "gamp_timing": gamp["timing"]}


def case_q4() -> dict:
    sigma2 = 0.2
    y = np.array([0, 1 + 0.2j, -0.5 + 0.4j, 0.3 - 1j,
                  0.2 + 0.1j, -0.8 - 0.5j, 0.01 + 0j, -1j])
    hard, estimate_data = lmmse_hard_data(y, np.zeros(8, complex),
                                          np.eye(8, dtype=complex), sigma2)
    expected = y / (1 + 2 * sigma2)
    error = float(np.max(abs(estimate_data - expected)))
    assert error <= 1e-12
    assert hard[0] == 0.5 + 0.5j
    assert hard_qpsk(np.array([0j]))[0] == 0.5 + 0.5j
    return {"analytic_shrink_error": error, "ridge": 2 * sigma2}


def case_q5() -> dict:
    n = 32
    rng = np.random.default_rng(2026092805)
    c1, c2 = 5 / (2 * n), (np.sqrt(2) - 1) / (2 * n * n)
    pilot = qpsk(rng, n)
    channel = Channel(n, c1, c2, np.arange(9), np.zeros(9),
                      np.full(9, 0.1 + 0.05j))
    observed = channel.apply(pilot + qpsk(rng, n))
    result = scalar_joint(observed, pilot, channel, 0.1, pd=0.5,
                          prior=np.zeros(2 * n), iterations=1,
                          damping=0.3, gain_mode="joint")
    assert channel.p == 9 and len(result["mu"]) == n
    assert len(result["gains"]) == 9
    return {"path_count_in": channel.p, "path_count_out": len(result["gains"]),
            "posterior_symbols": len(result["mu"])}


def main() -> None:
    output = {}
    for key, func in (("Q1", case_q1), ("Q2", case_q2), ("Q3", case_q3),
                      ("Q4", case_q4), ("Q5", case_q5)):
        output[key] = func()
    print(json.dumps({"schema": "f2-synthetic-qualification-result/1",
                      "status": "pass", "real_observations_read": False,
                      "receiver_calls": 0, "cases": output}, indent=2))


if __name__ == "__main__":
    main()
