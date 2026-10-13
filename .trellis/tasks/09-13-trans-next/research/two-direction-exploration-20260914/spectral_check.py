"""Reproduce two-direction planning evidence; no receiver, channel samples, or BER runs.

Requires NumPy. Output JSON to stdout; keep each saved result immutable.
"""

import hashlib
import json
import platform
from pathlib import Path

import numpy as np


def calculate():
    n = 256
    fs = 4000.0
    max_doppler = 16.0
    width = max_doppler / fs
    samples = np.arange(n)
    lag = samples[:, None] - samples[None, :]

    # Flat band covariance: its leading eigenvectors are the DPSS subspace.
    uniform_cov = np.sinc(2 * width * lag)
    eigenvalues, vectors = np.linalg.eigh(uniform_cov)
    basis = vectors[:, ::-1]

    def angle_covariance(points):
        angle = 2 * np.pi * np.arange(points) / points
        correlation = np.cos(
            2 * np.pi * width * samples[:, None] * np.cos(angle)[None, :]
        ).mean(axis=1)
        return correlation[np.abs(lag)]

    angle_cov = angle_covariance(4096)
    quadrature_error = float(np.max(np.abs(angle_cov - angle_covariance(2048))))
    if quadrature_error > 1e-12:
        raise ValueError(f"Angular quadrature not converged: {quadrature_error}")
    if not np.allclose(basis.T @ basis, np.eye(n), atol=1e-12, rtol=0):
        raise ValueError("DPSS basis is not orthonormal")

    frequencies = np.linspace(-width, width, 2001)
    responses = np.exp(2j * np.pi * samples[:, None] * frequencies[None, :])
    rows = []
    for rank in (3, 5, 7):
        bins = np.arange(-(rank // 2), rank // 2 + 1)
        fourier = np.exp(2j * np.pi * samples[:, None] * bins[None, :] / n) / np.sqrt(n)
        row = {"rank": rank}
        for name, subspace in (("dpss", basis[:, :rank]), ("fixed_fourier", fourier)):
            mean_error = 1 - np.trace(subspace.conj().T @ angle_cov @ subspace).real / n
            grid_error = 1 - np.sum(np.abs(subspace.conj().T @ responses) ** 2, axis=0) / n
            if mean_error < -1e-12 or np.min(grid_error) < -1e-12:
                raise ValueError("Projection error below floating-point tolerance")
            row[name] = {
                "mean_relative_error_angle_spectrum": float(mean_error),
                "max_relative_error_on_frequency_grid": float(np.max(grid_error)),
                "mean_relative_error_uniform_spectrum": float(
                    1 - np.trace(subspace.conj().T @ uniform_cov @ subspace).real / n
                ),
            }
        rows.append(row)

    return {
        "evidence_level": "deterministic_single_delay_subspace_calculation",
        "scope": "Planning evidence; not noisy estimation, adaptive OMP, receiver BER, or cost evidence.",
        "config": {
            "N": n, "Fs_hz": fs, "max_doppler_hz": max_doppler,
            "frequency_model": "nu = 16*cos(theta); theta uniform on [0,2*pi)",
            "angle_quadrature_points": 4096, "frequency_grid_points": 2001,
            "DPSS_design": "leading eigenvectors of sinc(2*max_doppler/Fs*(m-n))",
            "fourier_bins": "centered consecutive integer bins, same rank",
        },
        "rows": rows,
        "checks": {
            "quadrature_2048_vs_4096_max_abs": quadrature_error,
            "min_uniform_cov_eigenvalue": float(eigenvalues[0]),
            "orthogonality_max_abs": float(np.max(np.abs(basis.T @ basis - np.eye(n)))),
        },
        "limitations": [
            "Known public Doppler bound; no path-specific Doppler given to basis design.",
            "DPSS optimality is for the flat-band design covariance, not arbitrary spectra or FER.",
            "The angle-spectrum mean is a deterministic quadrature, not Monte Carlo evidence.",
            "The 2001-point maximum is not a certified continuous worst-case bound.",
            "No pilot observability, noisy coefficient fit, multi-delay inference, or detector evaluated.",
        ],
        "provenance": {
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "python": platform.python_version(), "numpy": np.__version__,
        },
    }


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=False, indent=2, allow_nan=False))
