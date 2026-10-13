"""Independent dense checks for post-seal physical operator diagnostics."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from derive_physical import (dense_reference_check, geometry_diagnostics, operator_difference_power,
                             operator_power, paths, selected_geometry_projection)


def dense_physical_atom(n: int, delay: int, doppler: float,
                        c1: float = .037, c2: float = .011) -> np.ndarray:
    """Direct AFDM matrix A M A^H; independent of delay-group formula."""
    t = np.arange(n)
    fourier = np.exp(-2j * np.pi * t[:, None] * t[None, :] / n) / np.sqrt(n)
    transform = (np.exp(2j * np.pi * c2 * t**2)[:, None] * fourier *
                 np.exp(2j * np.pi * c1 * t**2)[None, :])
    time_action = np.zeros((n, n), complex)
    for row in range(n):
        wrap = np.exp(2j * np.pi * c1 * (n * n + 2 * n * (row - delay))) if row < delay else 1
        time_action[row, (row - delay) % n] = wrap * np.exp(2j * np.pi * doppler * row / n)
    return transform @ time_action @ transform.conj().T


def dense_channel(n: int, geometry: tuple) -> np.ndarray:
    delays, dopplers, gains = geometry
    return sum((gain * dense_physical_atom(n, int(delay), float(doppler))
                for delay, doppler, gain in zip(delays, dopplers, gains)),
               np.zeros((n, n), complex))


@pytest.mark.parametrize("n", [7, 13])
def test_exact_operator_and_projection_against_independent_dense_ls(n):
    truth = paths([1, 1, 3], [-.6, .37, 1.2],
                  [1 + .4j, -.3 + .7j, .8 - .2j], n)
    selected = paths([1, 1, 2], [-.52, .29, -.1],
                     [.1 + .2j, 1.1 - .3j, .2j], n)
    direct_truth = dense_channel(n, truth)
    direct_fit = dense_channel(n, selected)
    assert operator_power(n, *truth) == pytest.approx(np.linalg.norm(direct_truth)**2,
                                                        rel=1e-12, abs=1e-12)
    assert operator_difference_power(n, selected, truth) == pytest.approx(
        np.linalg.norm(direct_fit - direct_truth)**2, rel=1e-12, abs=1e-12)

    projected = selected_geometry_projection(n, truth, selected)
    atoms = np.column_stack([dense_physical_atom(n, int(delay), float(doppler)).ravel()
                             for delay, doppler in zip(selected[0], selected[1])])
    dense_gains = np.linalg.lstsq(atoms, direct_truth.ravel(), rcond=None)[0]
    dense_residual = np.linalg.norm(atoms @ dense_gains - direct_truth.ravel())**2
    assert projected["residual_frobenius_squared"] == pytest.approx(
        dense_residual, rel=1e-11, abs=1e-11)
    assert projected["gains"] == pytest.approx(dense_gains, rel=1e-11, abs=1e-11)
    assert projected["residual_frobenius_squared"] <= operator_difference_power(
        n, selected, truth) + 1e-10


def test_repeated_delay_cross_terms_and_missing_power_are_distinct():
    n = 11
    truth = paths([2, 2, 4], [.0, .0, .5], [1, -1, .5j], n)
    selected = paths([2, 4], [0., .5], [0., 0.], n)
    summary, components = geometry_diagnostics(n, truth, selected)
    # Two coincident true components cancel; naive sum |gain|² would be wrong.
    assert operator_power(n, *truth) == pytest.approx(n * .25, abs=1e-10)
    assert summary["selected_geometry_projection_nmse"] == pytest.approx(0, abs=1e-11)
    assert summary["saved_gain_operator_mismatch_nmse"] == pytest.approx(1, abs=1e-11)
    assert summary["delay_multiplicity_l1"] == 1
    assert summary["true_min_same_delay_doppler_gap"] == 0
    assert summary["true_same_delay_pairs_within_quarter_bin"] == 1
    assert summary["missing_distinct_delay_gain_power"] == 0
    assert len(components) == 3


def test_missing_delay_is_unrepresentable_and_absent_gains_are_explicit():
    n = 9
    truth = paths([1, 3], [.2, -.5], [1, .5j], n)
    selected = paths([1], [.2], None, n)
    summary, components = geometry_diagnostics(n, truth, selected)
    assert summary["missing_distinct_delay_gain_power"] == pytest.approx(.25)
    assert summary["selected_geometry_projection_nmse"] == pytest.approx(.2)
    assert summary["saved_gain_operator_mismatch_nmse"] is None
    assert summary["saved_gain_unavailable_reason"]
    assert components[1]["nearest_same_delay_slot"] is None


def test_invalid_geometry_rejected():
    with pytest.raises(ValueError, match="invalid delay"):
        paths([12], [0], [1], 8)
    with pytest.raises(ValueError, match="invalid physical gains"):
        paths([1], [0], [np.nan], 8)


def test_production_dense_reference_receipt():
    check = dense_reference_check()
    assert check["status"] == "pass"
    assert check["comparisons"] == 6
    assert check["maximum_absolute_squared_norm_error"] < 1e-10
