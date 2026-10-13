"""Ideal single-path algebra audit, NOT an AFDM receiver/BER experiment.

Unit mean path-gain power; uniform fractional offset; known integer centre;
independent, zero-mean core coefficient error of covariance q I.  The
miscentred cases deliberately violate the centre assumption.  No kappa is
estimated: every completion is a fixed complex linear map on integer bins.
"""

import hashlib
import json
from pathlib import Path

import numpy as np


def coefficients(n, offsets, kappa):
    x = kappa[:, None] - offsets[None, :]
    return np.exp(1j * np.pi * (n - 1) * x / n) * np.sinc(x) / np.sinc(x / n)


def quadrature(count):
    nodes, weights = np.polynomial.legendre.leggauss(count)
    return nodes / 2, weights / 2


def moments(n, offsets, width, count=128, centre_error=0):
    nodes, weights = quadrature(count)
    coef = coefficients(n, offsets, nodes - centre_error)
    core = coef[:, np.abs(offsets) <= width]
    tail = coef[:, np.abs(offsets) > width]
    rss = core.T @ (weights[:, None] * core.conj())
    rts = tail.T @ (weights[:, None] * core.conj())
    energy = float(np.sum(weights[:, None] * np.abs(tail) ** 2))
    return rss, rts, energy, core, tail, weights


def predictor(rss, rts, q):
    return np.linalg.solve(rss + q * np.eye(len(rss)), rts.conj().T).conj().T


def integrated_risk(f, core, tail, weights, q):
    # Different quadrature from design; noise integrated analytically.
    structural = float(np.sum(weights[:, None] * abs(tail - core @ f.T) ** 2))
    return structural + q * float(np.linalg.norm(f) ** 2)


def main():
    n = 1024
    offsets = np.arange(-n // 2, n // 2)
    rows = []
    maximum_risk_discrepancy = 0.0
    for width in [0, 1, 2]:
        rss, rts, tail_energy, *_ = moments(n, offsets, width)
        _, _, _, cs, ct, weights = moments(n, offsets, width, count=257)
        for q in [0.0001, 0.001, 0.01, 0.1, 1.0]:
            f = predictor(rss, rts, q)
            gain = float(np.trace(f @ rts.conj().T).real)
            mse = tail_energy - gain
            check = integrated_risk(f, cs, ct, weights, q)
            maximum_risk_discrepancy = max(maximum_risk_discrepancy, abs(mse - check))
            rows.append({
                "core_bins": 2 * width + 1,
                "coefficient_error_variance_over_path_power": q,
                "uncompleted_tail_mse": tail_energy,
                "completed_tail_mse": mse,
                "tail_mse_reduction_fraction": gain / tail_energy,
                "linear_noise_gain": float(np.linalg.norm(f) ** 2),
            })

    rss, rts, tail_energy, *_ = moments(n, offsets, 1)
    q_design = 0.01
    f = predictor(rss, rts, q_design)
    wrong_centre = []
    for shift in [-1, 0, 1]:
        _, _, baseline, cs, ct, weights = moments(n, offsets, 1, 257, shift)
        mse = integrated_risk(f, cs, ct, weights, q_design)
        wrong_centre.append({"centre_error_bins": shift, "baseline": baseline, "completion": mse})
    noise_gain = float(np.linalg.norm(f) ** 2)
    structural_risk = wrong_centre[1]["completion"] - q_design * noise_gain
    crossover = (tail_energy - structural_risk) / noise_gain
    good_gain = wrong_centre[1]["baseline"] - wrong_centre[1]["completion"]
    bad_gain = wrong_centre[0]["baseline"] - wrong_centre[0]["completion"]
    centre_probability_crossover = -bad_gain / (good_gain - bad_gain)

    nodes, _ = quadrature(257)
    time_signals = np.exp(2j * np.pi * nodes[:, None] * np.arange(n)[None, :] / n)
    brute = np.fft.fft(time_signals, axis=1) / n
    closed = coefficients(n, offsets, nodes)
    dft_error = float(np.max(abs(closed - brute[:, offsets % n])))
    parseval_error = float(np.max(abs(np.sum(abs(closed) ** 2, axis=1) - 1)))
    assert dft_error < 1e-12
    assert parseval_error < 1e-12
    assert maximum_risk_discrepancy < 1e-11
    for q_check in [0.001, 0.1, 0.2]:
        _, _, _, cs, ct, weights = moments(n, offsets, 1, 257)
        actual = integrated_risk(f, cs, ct, weights, q_check)
        assert abs(actual - (structural_risk + q_check * noise_gain)) < 1e-11

    result = {
        "evidence_type": "ideal_single_path_quadrature_and_algebra_not_receiver_performance",
        "numpy_version": np.__version__, "N": n,
        "design_quadrature": 128, "verification_quadrature": 257,
        "coefficient_convention": "alpha(-m,kappa,N); verified against finite DFT",
        "assumptions": ["uniform kappa in [-0.5,0.5]", "unit mean path power", "one path", "correct centre except explicit counterexamples", "independent zero-mean qI core coefficient error"],
        "rows": rows,
        "frozen_three_bin_predictor": {
            "design_q": q_design, "noise_gain": noise_gain,
            "structural_tail_mse": structural_risk,
            "noise_variance_crossover": crossover,
            "centre_counterexamples": wrong_centre,
            "centre_correct_probability_crossover_if_remaining_errors_are_pm1": centre_probability_crossover,
        },
        "verification": {"DFT_max_error": dft_error, "parseval_max_error": parseval_error, "risk_max_difference": maximum_risk_discrepancy},
        "receiver_calls": 0, "BP_calls": 0, "LDPC_calls": 0,
        "not_claimed": ["G1 gain", "FER gain", "oracle centre available online", "independent prospective validation", "new Wiener formula", "zero extra detection cost"],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    output = Path(__file__).with_suffix(".json")
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output), "verification": result["verification"], "frozen_three_bin_predictor": result["frozen_three_bin_predictor"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
