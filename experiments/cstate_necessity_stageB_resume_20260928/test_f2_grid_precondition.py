"""Synthetic algebra check for the versioned grid-QP coordinate change."""

from __future__ import annotations

import numpy as np
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"))

from f2_estimator import FROZEN, _solve_grid_qp  # noqa: E402


def test_grid_qp_diagonal_change_preserves_objective_and_box() -> None:
    quadratic = np.array([[1000.0, 0.3], [0.3, 2.0]])
    alpha = np.array([500.0, 1.0])
    bounds = [(-0.5, 0.5), (-0.5, 0.5)]
    kappa, diagnostic = _solve_grid_qp(quadratic, alpha, bounds, FROZEN)
    scale = np.sqrt(np.diag(quadratic))
    z = scale * kappa
    objective = float(kappa @ quadratic @ kappa - 2 * alpha @ kappa)
    transformed = float(z @ ((quadratic / scale[:, None]) / scale[None, :]) @ z
                        - 2 * (alpha / scale) @ z)
    assert np.isclose(objective, transformed, rtol=0, atol=1e-12)
    assert np.max(abs(kappa - np.linalg.solve(quadratic, alpha))) <= 1e-6
    assert all(lo - 1e-12 <= value <= hi + 1e-12
               for value, (lo, hi) in zip(kappa, bounds))
    assert diagnostic["iterations"] <= FROZEN.qp_maxiter
    assert diagnostic["termination_reason"]
    assert diagnostic["original_kkt_projected_inf"] <= 1e-6
    assert np.isfinite(diagnostic["scaled_kkt_projected_inf"])
