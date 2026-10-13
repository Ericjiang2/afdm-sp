"""Synthetic algebra checks only; no receiver, scientific trial or performance claim."""
from itertools import product
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    rng = np.random.default_rng(20260912)
    # Uniform even-parity toy code: the same positive scale preserves joint MAP.
    words = np.array([b for b in product((0, 1), repeat=4) if sum(b) % 2 == 0])
    symbols = 1.0 - 2.0 * words
    channel = rng.normal(size=(6, 4)) + 1j * rng.normal(size=(6, 4))
    pilot = rng.normal(size=4) + 1j * rng.normal(size=4)
    y = channel @ (pilot + symbols[3]) + 0.4 * (
        rng.normal(size=6) + 1j * rng.normal(size=6)
    )
    distances = np.sum(abs(y[None, :] - (pilot + symbols) @ channel.T) ** 2, axis=1)
    temperatures = (0.15, 0.4, 1.0, 3.0)
    winners = [int(np.argmax(-distances / value)) for value in temperatures]
    assert len(set(winners)) == 1

    # Gaussian elimination identity and monotonicity under extra nuisance precision.
    design = rng.normal(size=(13, 6))
    precision = design.T @ design + np.eye(6)
    prior_factor = rng.normal(size=(4, 4))
    prior = prior_factor.T @ prior_factor
    a, b, d = precision[:2, :2], precision[:2, 2:], precision[2:, 2:]
    effective0 = a - b @ np.linalg.solve(d, b.T)
    effective1 = a - b @ np.linalg.solve(d + prior, b.T)
    min_gain = float(np.linalg.eigvalsh(effective1 - effective0).min())
    assert min_gain >= -1e-12
    augmented = precision.copy()
    augmented[2:, 2:] += prior
    schur_error = float(np.max(abs(np.linalg.inv(augmented)[:2, :2] - np.linalg.inv(effective1))))
    assert schur_error < 1e-12

    # Fixed atom-span least squares certifies Frobenius error, not FER optimality.
    n = 8
    atoms = [np.diag(np.exp(2j * np.pi * rng.random(n))) @ np.roll(np.eye(n), shift, axis=0)
             for shift in (0, 1, 3, 5)]
    basis = np.column_stack([atom.reshape(-1) for atom in atoms[:3]])
    truth = sum(gain * atom for gain, atom in zip((1.0, 0.6j, -0.2, 0.3j), atoms))
    old = sum(gain * atom for gain, atom in zip((0.8, 0.4j, -0.1), atoms[:3]))
    gains = np.linalg.lstsq(basis, truth.reshape(-1), rcond=None)[0]
    projected = (basis @ gains).reshape(n, n)
    residual = (truth - projected).reshape(-1)
    orthogonality = float(np.max(abs(basis.conj().T @ residual)))
    assert orthogonality < 1e-12
    old_error = float(np.linalg.norm(truth - old) ** 2)
    projection_error = float(np.linalg.norm(truth - projected) ** 2)
    assert projection_error <= old_error + 1e-12

    source = Path(__file__)
    output = source.with_suffix('.json')
    result = {
        'scope': 'synthetic finite algebra checks; no AFDM receiver performance or independent review',
        'seed': 20260912,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'joint_MAP_winners': winners,
        'positive_temperatures': temperatures,
        'schur_inverse_max_error': schur_error,
        'minimum_effective_precision_gain': min_gain,
        'projection_orthogonality_max_error': orthogonality,
        'old_Frobenius_squared_error': old_error,
        'projected_Frobenius_squared_error': projection_error,
        'new_F': 0,
        'new_T': 0,
        'status': 'PASS',
    }
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
