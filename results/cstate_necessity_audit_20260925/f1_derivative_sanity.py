"""One synthetic AFDM response/score derivative check; no receiver or observations."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
from physical import daft, regressors  # noqa: E402


def main():
    n, delay, nu, sigma2 = 31, 3, 0.37, 0.17
    c1, c2 = 5 / (2 * n), (np.sqrt(2) - 1) / (2 * n * n)
    rng = np.random.default_rng(924)
    pilot = rng.normal(size=n) + 1j * rng.normal(size=n)
    y = rng.normal(size=n) + 1j * rng.normal(size=n)
    t = np.arange(n)
    a = daft(pilot, c1, c2, inverse=True)
    z = daft(y, c1, c2, inverse=True)
    cpp = np.where(t < delay, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (t - delay))), 1)

    def response(v):
        return a[(t - delay) % n] * cpp * np.exp(2j * np.pi * t * v / n)

    b = response(nu)
    b1 = (2j * np.pi * t / n) * b
    b2 = -(2 * np.pi * t / n) ** 2 * b
    energy = float(np.vdot(pilot, pilot).real)
    denom = sigma2 * (energy + sigma2)

    def score(v):
        q = np.vdot(response(v), z)
        return float(abs(q) ** 2 / denom)

    q, q1, q2 = np.vdot(b, z), np.vdot(b1, z), np.vdot(b2, z)
    analytic1 = 2 * np.real(np.conj(q) * q1) / denom
    analytic2 = 2 * (abs(q1) ** 2 + np.real(np.conj(q) * q2)) / denom
    h1, h2 = 1e-5, 1e-4
    result = {
        "fixture": "synthetic_only",
        "n": n,
        "seed": 924,
        "regressor_max_abs_error": float(np.max(np.abs(daft(b, c1, c2) - regressors(pilot, [delay], [nu], c1, c2)[:, 0]))),
        "energy_abs_error": float(abs(np.vdot(b, b).real - energy)),
        "first_derivative_abs_error": float(abs((score(nu + h1) - score(nu - h1)) / (2 * h1) - analytic1)),
        "second_derivative_abs_error": float(abs((score(nu + h2) - 2 * score(nu) + score(nu - h2)) / h2**2 - analytic2)),
        "receiver_or_observation_used": False,
    }
    assert result["regressor_max_abs_error"] < 1e-11
    assert result["energy_abs_error"] < 1e-11
    assert result["first_derivative_abs_error"] < 1e-6
    assert result["second_derivative_abs_error"] < 1e-4
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
