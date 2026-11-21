"""Deterministic algebra checks only; no AFDM receiver or experiment inputs."""

import itertools
import json

import numpy as np


def main():
    rng = np.random.default_rng(20260914)

    def complex_normal(shape):
        return (rng.standard_normal(shape) + 1j * rng.standard_normal(shape)) / np.sqrt(2)

    # Exact second moments over finite Cartesian distributions, not Monte Carlo.
    n, k, data_power, noise_variance = 3, 2, 0.5, 0.07
    q, _ = np.linalg.qr(complex_normal((n * n, k + 1)))
    basis = q[:, :k].T.reshape(k, n, n)
    remainder = 0.3 * q[:, k].reshape(n, n)
    gains = complex_normal(k)
    channel = np.einsum("k,kij->ij", gains, basis) + remainder
    pilot = complex_normal(n)
    design = np.column_stack([b @ pilot for b in basis])
    left_inverse = np.linalg.solve(design.conj().T @ design, design.conj().T)
    bias = left_inverse @ remainder @ pilot
    covariance = data_power * channel @ channel.conj().T + noise_variance * np.eye(n)
    gram = np.array([[np.vdot(bi, bj) for bj in basis] for bi in basis])
    predicted = (
        np.linalg.norm(remainder) ** 2
        + np.vdot(bias, gram @ bias).real
        + np.trace(gram @ left_inverse @ covariance @ left_inverse.conj().T).real
    )
    alphabet = np.sqrt(data_power / 2) * np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j])
    noises = [np.sqrt(n * noise_variance) * np.eye(n)[:, i] * phase
              for i in range(n) for phase in [1, -1, 1j, -1j]]
    risks = []
    for symbols in itertools.product(alphabet, repeat=n):
        for noise in noises:
            y = channel @ (pilot + np.array(symbols)) + noise
            estimate = np.einsum("k,kij->ij", left_inverse @ y, basis)
            risks.append(np.linalg.norm(estimate - channel) ** 2)
    risk_relative_error = abs(np.mean(risks) - predicted) / max(1, predicted)
    assert risk_relative_error < 1e-12

    # Candidate-dependent Gaussian marginal: direct versus Woodbury/determinant lemma.
    marginal_errors, cross_errors = [], []
    for _ in range(32):
        n, k, variance = 7, 3, 0.31
        gain_factor = complex_normal((k, k))
        gamma = gain_factor @ gain_factor.conj().T + 0.2 * np.eye(k)
        pilot_design = complex_normal((n, k))
        data_design = complex_normal((n, k))
        design = pilot_design + data_design
        y = complex_normal(n)
        mean = complex_normal(k)
        residual = y - design @ mean
        covariance = variance * np.eye(n) + design @ gamma @ design.conj().T
        precision = np.linalg.inv(gamma) + design.conj().T @ design / variance
        direct = np.vdot(residual, np.linalg.solve(covariance, residual)).real + np.linalg.slogdet(covariance)[1]
        projected = design.conj().T @ residual
        reduced = (
            np.vdot(residual, residual).real / variance
            - np.vdot(projected, np.linalg.solve(precision, projected)).real / variance**2
            + n * np.log(variance) + np.linalg.slogdet(gamma)[1]
            + np.linalg.slogdet(precision)[1]
        )
        marginal_errors.append(abs(direct - reduced) / max(1, abs(direct)))
        expanded = (variance * np.eye(n)
                    + pilot_design @ gamma @ pilot_design.conj().T
                    + data_design @ gamma @ data_design.conj().T
                    + pilot_design @ gamma @ data_design.conj().T
                    + data_design @ gamma @ pilot_design.conj().T)
        cross_errors.append(np.linalg.norm(expanded - covariance) / np.linalg.norm(covariance))
    assert max(marginal_errors) < 1e-11
    assert max(cross_errors) < 1e-12

    # Scalar unknown gain, two QPSK data symbols: pilot-only LS has a floor,
    # yet every noiseless joint data/gain hypothesis has a different line.
    data_power, amplitude = 1.0, 2.3
    alphabet = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / np.sqrt(2)
    signals = np.array([np.array([amplitude, 0]) + d
                        for d in itertools.product(alphabet, repeat=2)])
    units = signals / np.linalg.norm(signals, axis=1, keepdims=True)
    squared_sines = [1 - abs(np.vdot(units[i], units[j])) ** 2
                     for i in range(len(units)) for j in range(i)]
    assert min(squared_sines) > 0
    gain = 0.8 + 0.3j
    errors = [abs(gain * d / amplitude) ** 2 for d in alphabet]
    floor = abs(gain) ** 2 * data_power / amplitude**2
    assert abs(np.mean(errors) - floor) < 1e-14

    print(json.dumps({
        "scope": "finite-distribution and small-matrix algebra only",
        "afdm_receiver_calls": 0,
        "new_channel_experiment_runs": 0,
        "fixed_design_risk_states": len(risks),
        "fixed_design_risk_relative_error": risk_relative_error,
        "gaussian_marginal_cases": len(marginal_errors),
        "woodbury_metric_max_relative_error": max(marginal_errors),
        "pilot_data_cross_expansion_max_relative_error": max(cross_errors),
        "noiseless_hypothesis_lines": len(signals),
        "minimum_pairwise_squared_sine": min(squared_sines),
        "pilot_only_ls_gain_mse_floor": floor,
        "status": "PASS",
    }, indent=2))


if __name__ == "__main__":
    main()
