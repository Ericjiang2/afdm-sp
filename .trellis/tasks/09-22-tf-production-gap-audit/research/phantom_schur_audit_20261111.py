"""Deterministic complex matrix checks for exact and near duplicate Schur gains."""

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np


TOL = 5e-12
ENERGIES = (0.2, 1.0, 4.0)
UNCERTAINTIES = (0.05, 0.4, 2.0)
RIDGES = (0.01, 0.05, 0.6)
MODELS = ("scalar", "full")


def normal_system(operators, pilot, y, u, ridge, model):
    waveforms = np.column_stack([op @ pilot for op in operators])
    q = waveforms.conj().T @ waveforms
    if model == "full":
        flat = operators.reshape(len(operators), -1)
        q += (u / len(pilot)) * (flat.conj() @ flat.T)
    else:
        q += u * np.eye(len(operators))
    q += np.diag(np.broadcast_to(ridge, (len(operators),)))
    return q, waveforms.conj().T @ y


def objective_reduction(q, b, *, singular=False):
    fit = np.linalg.pinv(q, hermitian=True) @ b if singular else np.linalg.solve(q, b)
    return np.vdot(b, fit).real


def schur_gain(q, b):
    retained = q[:-1, :-1]
    cross = q[:-1, -1]
    residual = b[-1] - np.vdot(cross, np.linalg.solve(retained, b[:-1]))
    denominator = q[-1, -1].real - np.vdot(cross, np.linalg.solve(retained, cross)).real
    assert denominator > 0
    return abs(residual) ** 2 / denominator


def direct_gain(q, b):
    return objective_reduction(q, b) - objective_reduction(q[:-1, :-1], b[:-1])


def operators_for_audit(n):
    index = np.arange(n)
    identity = np.eye(n, dtype=complex)
    shift = np.roll(identity, 1, axis=0)
    modulation = np.diag(np.exp(2j * np.pi * 0.31 * index / n))
    return np.array([identity, modulation, shift @ modulation])


def exact_duplicate_checks():
    n = 16
    operators = operators_for_audit(n)
    index = np.arange(n)
    pilot_shape = np.cos(0.37 * index) + 1j * np.sin(0.61 * index)
    pilot_shape /= np.linalg.norm(pilot_shape)
    y = (np.sin(0.23 * index) + 1j * np.cos(0.43 * index)) / np.sqrt(n)
    errors = {"schur_vs_direct": 0.0, "schur_vs_closed": 0.0}
    count = 0
    for size, energy, u, ridge, model in product(
        (1, 3), ENERGIES, UNCERTAINTIES, RIDGES, MODELS
    ):
        retained = operators[:size]
        for j in range(size):
            augmented = np.concatenate((retained, retained[j : j + 1]))
            q, b = normal_system(augmented, np.sqrt(energy) * pilot_shape, y, u, ridge, model)
            retained_q = q[:-1, :-1]
            z_j = np.linalg.solve(retained_q, b[:-1])[j]
            a_j = np.linalg.solve(retained_q, np.eye(size)[:, j])[j].real
            delta = u + ridge if model == "scalar" else ridge
            closed = delta * abs(z_j) ** 2 / (2 - delta * a_j)
            schur = schur_gain(q, b)
            errors["schur_vs_direct"] = max(errors["schur_vs_direct"], abs(schur - direct_gain(q, b)))
            errors["schur_vs_closed"] = max(errors["schur_vs_closed"], abs(schur - closed))
            count += 1
    assert max(errors.values()) < TOL, errors
    return {"cases": count, "max_absolute_error": errors}


def pair_scores(identity, shift, pilot, hs, hw, u, ridge, model):
    y = hs * (identity @ pilot) + hw * (shift @ pilot)
    return [
        schur_gain(*normal_system(np.array([identity, op]), pilot, y, u, ridge, model))
        for op in (identity, shift)
    ]


def threshold_checks():
    identity = np.eye(16, dtype=complex)
    shift = np.roll(identity, 1, axis=0)
    max_tie_error = 0.0
    count = 0
    for energy, u, ridge, model in product(ENERGIES, UNCERTAINTIES, RIDGES, MODELS):
        pilot = np.sqrt(energy) * identity[:, 0]
        threshold = (
            1 + 2 * energy / (u + ridge)
            if model == "scalar"
            else 1 + 2 * (energy + u) / ridge
        )
        for multiplier in (0.9, 1.0, 1.1):
            dup, weak = pair_scores(identity, shift, pilot, np.sqrt(multiplier * threshold), 1, u, ridge, model)
            if multiplier == 1:
                max_tie_error = max(max_tie_error, abs(dup - weak))
            else:
                assert (dup - weak) * (multiplier - 1) > 0
            count += 1
    assert max_tie_error < TOL, max_tie_error
    return {"cases": count, "max_absolute_tie_error": max_tie_error}


def phase_counterexample():
    identity = np.eye(16, dtype=complex)
    shift = np.roll(identity, 1, axis=0)
    pilot = np.sqrt(0.8) * identity[:, 0] + np.sqrt(0.2) * identity[:, 1]
    kappa = np.vdot(pilot, shift @ pilot).real
    assert abs(kappa - 0.4) < TOL and np.trace(shift) == 0
    results = {
        model: {
            sign: dict(zip(("duplicate", "weak"), pair_scores(identity, shift, pilot, 1, hw, 0.4, 0.05, model)))
            for sign, hw in (("positive_hw", 0.4), ("negative_hw", -0.4))
        }
        for model in MODELS
    }
    scalar = results["scalar"]
    assert scalar["positive_hw"]["duplicate"] < scalar["positive_hw"]["weak"]
    assert scalar["negative_hw"]["duplicate"] > scalar["negative_hw"]["weak"]
    return {"kappa": kappa, "gain_ratio": 1 / 0.4**2, "scores": results}


def doppler_limit():
    n = 16
    index = np.arange(n)
    identity = np.eye(n, dtype=complex)
    pilot = np.exp(1j * 0.19 * index) / np.sqrt(n)
    energy, u, ridge = 1.0, 0.4, 0.05
    hs = 0.9 + 0.3j
    y = hs * pilot
    k = energy + u + ridge
    gaps = (0.1, 0.01, 0.001, 0.0001)
    results = {}
    for model in MODELS:
        a = u + ridge if model == "scalar" else ridge
        c = k - a
        limit = schur_gain(*normal_system(np.array([identity, identity]), pilot, y, u, ridge, model))
        rows = []
        for gap in gaps:
            phase = np.exp(2j * np.pi * gap * index / n)
            near_duplicate = np.diag(phase)
            gain = schur_gain(*normal_system(np.array([identity, near_duplicate]), pilot, y, u, ridge, model))
            d_squared = abs(phase.mean()) ** 2
            closed = energy**2 * abs(hs)**2 * d_squared * a**2 / (k * (k**2 - c**2 * d_squared))
            rows.append({
                "gap": gap, "gain": gain, "relative_error": abs(gain - limit) / limit,
                "finite_closed_gain": closed, "finite_closed_absolute_error": abs(gain - closed),
            })
        errors = [row["relative_error"] for row in rows]
        max_closed_error = max(row["finite_closed_absolute_error"] for row in rows)
        assert all(a > b for a, b in zip(errors, errors[1:])) and errors[-1] < 5e-6
        assert max_closed_error < TOL, max_closed_error
        results[model] = {
            "limit_gain": limit, "gap_sequence": rows,
            "max_finite_closed_absolute_error": max_closed_error,
        }
    results["finite_closed_formula"] = "E^2 |Hs|^2 |D|^2 a^2 / [k (k^2 - c^2 |D|^2)]"
    results["finite_closed_scope"] = "Requires kappa_dup = D, as in this constant-time-energy pilot with pure modulation and y = Hs * pilot."
    return results


def matched_prior_checks():
    identity = np.eye(16, dtype=complex)
    pilot = identity[:, 0]
    y = (1 + 0.7j) * pilot
    u, ridge = 0.4, 0.05
    results = {}
    for model in MODELS:
        q, b = normal_system(np.array([identity]), pilot, y, u, ridge, model)
        retained_reduction = objective_reduction(q, b)
        gains = {}
        for label, penalty in (
            ("independent_ridge", ridge),
            ("doubled_ridge", 2 * ridge),
            ("doubled_scalar_total_penalty", 2 * ridge + u if model == "scalar" else 2 * ridge),
        ):
            aug_q, aug_b = normal_system(np.array([identity, identity]), pilot, y, u, penalty, model)
            gains[label] = objective_reduction(aug_q, aug_b) - retained_reduction
        assert gains["independent_ridge"] > 0
        assert abs(gains["doubled_scalar_total_penalty"]) < TOL
        if model == "full":
            assert abs(gains["doubled_ridge"]) < TOL
        else:
            assert gains["doubled_ridge"] > 0
        results[model] = gains
    q, b = normal_system(np.array([identity, identity]), pilot, y, u, 0, "full")
    assert np.linalg.matrix_rank(q) == 1
    singular_gain = objective_reduction(q, b, singular=True) - objective_reduction(q[:1, :1], b[:1])
    assert abs(singular_gain) < TOL
    results["full_zero_ridge_pseudoinverse_gain"] = singular_gain
    return results


def main():
    result = {
        "_argv": sys.argv,
        "_config": {"dimension": 16, "E": ENERGIES, "u": UNCERTAINTIES, "lambda": RIDGES, "absolute_tolerance": TOL},
        "fixture": "deterministic unitary operators and synthetic complex vectors; no AFDM receiver or channel runs",
        "exact_duplicate_formula": "delta * abs((Q^-1 b)[j])^2 / (2 - delta * (Q^-1)[j,j])",
        "exact_duplicate": exact_duplicate_checks(),
        "threshold_formula": {"scalar": "1+2E/(u+lambda)", "full": "1+2(E+u)/lambda"},
        "orthogonal_thresholds": threshold_checks(),
        "phase_counterexample": phase_counterexample(),
        "doppler_gap_limit": doppler_limit(),
        "matched_prior": matched_prior_checks(),
    }
    Path(__file__).with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
