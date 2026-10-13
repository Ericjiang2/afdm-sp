"""Synthetic, no-receiver qualification of the frozen F1 and slot handoff."""
from __future__ import annotations

import inspect
import os
from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = Path(os.environ.get('STAGE_A_SOURCE',
    ROOT / 'experiments/sp_afdm_native_joint_20260921'))
BASELINE = Path(os.environ.get('STAGE_A_BASELINE',
    ROOT / 'experiments/sp_afdm_frozen_20260920'))
sys.path[:0] = [str(SOURCE / 'src'), str(BASELINE / 'src'), str(HERE)]

from physical import Channel, daft  # noqa: E402
from twofft import time_refine  # noqa: E402
from f1 import PhysicalF1, NumericalFailure, derivatives, refit, response, score_derivatives  # noqa: E402
from keep_slots import _valid_slots, time_refine_keep_slots  # noqa: E402


def fixture(n=63, seed=928):
    rng = np.random.default_rng(seed)
    c1 = 5 / (2 * n)
    c2 = (np.sqrt(2) - 1) / (2 * n * n)
    pilot = rng.normal(size=n) + 1j * rng.normal(size=n)
    return rng, c1, c2, pilot


def test_a_response_and_cpp_sign():
    rng, c1, c2, pilot = fixture(63)
    time_pilot = daft(pilot, c1, c2, True)
    for delay, nu in ((0, -2.1), (5, .37), (62, 2.81)):
        direct = response(time_pilot, delay, nu, c1)
        channel = Channel(63, c1, c2, [delay], [nu], [1])
        np.testing.assert_allclose(daft(direct, c1, c2), channel.apply(pilot), atol=3e-13, rtol=0)
        np.testing.assert_allclose(np.vdot(direct, direct).real, np.vdot(pilot, pilot).real,
                                   atol=4e-13, rtol=0)


def test_b_first_and_second_score_derivative():
    rng, c1, _, pilot = fixture()
    time_pilot = pilot
    residual = rng.normal(size=63) + 1j * rng.normal(size=63)
    energy, noise, nu = float(np.vdot(pilot, pilot).real), .21, .43

    def value(x):
        return score_derivatives(response(time_pilot, 7, x, c1), residual, energy, noise)[0]

    b = response(time_pilot, 7, nu, c1)
    first, second = derivatives(b)
    step1, step2 = 1e-5, 1e-4
    _, slope, curvature = score_derivatives(b, residual, energy, noise)
    assert np.max(abs(first)) > 0 and np.max(abs(second)) > 0
    assert abs(slope - (value(nu + step1) - value(nu - step1)) / (2 * step1)) < 2e-7
    assert abs(curvature - (value(nu + step2) - 2 * value(nu) + value(nu - step2)) / step2**2) < 3e-5


def test_c_g_single_and_multipath_nonincrease():
    rng, c1, c2, pilot = fixture(63)
    time_pilot = daft(pilot, c1, c2, True)
    for truth in (((3, .4, 1 + .3j),), ((3, .4, 1 + .3j), (10, -1.2, -.4 + .2j))):
        z = sum((gain * response(time_pilot, delay, nu, c1)
                 for delay, nu, gain in truth), np.zeros(63, complex))
        result = PhysicalF1(63, c1, c2, 14).acquire(daft(z, c1, c2), pilot, .05)
        history = result['objective_history']
        assert 1 <= len(result['delays']) <= 8
        assert np.max(np.diff(history)) <= 1e-8
        p = len(result['delays'])
        assert result['counters']['coordinate_visits'] == p * (p + 2)
        assert result['counters']['joint_solves'] >= len(result['delays'])


def test_d_ridge_refit_and_failure():
    rng, c1, _, pilot = fixture()
    z = rng.normal(size=63) + 1j * rng.normal(size=63)
    delays, dopplers, noise = [2, 2, 7], [-1.4, .7, .5], .13
    gains, residual, objective, condition = refit(z, pilot, delays, dopplers, c1, noise)
    B = np.column_stack([response(pilot, delay, nu, c1)
                         for delay, nu in zip(delays, dopplers)])
    expected = np.linalg.solve(B.conj().T @ B + noise * np.eye(3), B.conj().T @ z)
    np.testing.assert_allclose(gains, expected, atol=3e-14, rtol=0)
    np.testing.assert_allclose(residual, z - B @ expected, atol=3e-14, rtol=0)
    assert condition < 1e12 and objective >= 0
    with pytest.raises(NumericalFailure):
        refit(z, pilot, [2, 2], [.5, .5], c1, 1e-14)


def test_e_f_same_delay_handoff_and_duplicate_rule():
    rng, c1, c2, pilot = fixture(63)
    time_pilot = daft(pilot, c1, c2, True)
    z = response(time_pilot, 4, -1.5, c1) + .8 * response(time_pilot, 4, 1.5, c1)
    result = PhysicalF1(63, c1, c2, 4).acquire(daft(z, c1, c2), pilot, .04)
    assert len(result['delays']) >= 2 and len(set(result['delays'])) < len(result['delays'])
    assert not _valid_slots(np.array([4, 4]), np.array([.5, .5 + .5e-6]))
    assert _valid_slots(np.array([4, 4]), np.array([.5, .5 + 2e-6]))
    channel, detail = time_refine_keep_slots(daft(z, c1, c2), pilot, np.zeros(63, complex),
        np.full(63, .5), np.array([4, 4]), np.array([-1.5, 1.5]),
        np.array([1, .8]), c1, c2, .04)
    assert channel.p == 2 and channel.delays.tolist() == [4, 4]
    assert abs(channel.dopplers[0] - channel.dopplers[1]) >= 1e-6
    assert np.all(np.isfinite(detail['gamma']))


def test_g_budget_stop_and_h_no_truth_interface():
    rng, c1, c2, pilot = fixture(31)
    z = rng.normal(size=31) + 1j * rng.normal(size=31)
    result = PhysicalF1(31, c1, c2, 6).acquire(z, pilot, .2)
    assert 1 <= len(result['delays']) <= 8
    assert result['stopping_reason'] in {'eight_slots', 'numerical_no_improvement', 'no_valid_bank_item'}
    assert set(inspect.signature(PhysicalF1.acquire).parameters) == {'self', 'y', 'pilot', 'sigma2'}
    with pytest.raises(TypeError):
        PhysicalF1(31, c1, c2, 6).acquire(z, pilot, .2, truth_delays=[1])


def test_distinct_delay_adapter_parity_two_round_inputs():
    rng, c1, c2, pilot = fixture(63)
    for seed in (929, 930):
        random = np.random.default_rng(seed)
        y = random.normal(size=63) + 1j * random.normal(size=63)
        mu = .1 * (random.normal(size=63) + 1j * random.normal(size=63))
        v = random.uniform(.05, .5, size=63)
        ls, ks, gs = np.array([2, 9]), np.array([-.7, 1.25]), np.array([1 + .1j, .4j])
        old, old_detail = time_refine(y, pilot, mu, v, ls, ks, gs, c1, c2, .2)
        new, detail = time_refine_keep_slots(y, pilot, mu, v, ls, ks, gs, c1, c2, .2)
        np.testing.assert_array_equal(new.delays, old.delays)
        np.testing.assert_allclose(new.dopplers, old.dopplers, atol=2e-10, rtol=0)
        np.testing.assert_allclose(new.gains, old.gains, atol=2e-10, rtol=0)
        np.testing.assert_allclose(detail['gamma'], old_detail['gamma'], atol=2e-10, rtol=0)
        np.testing.assert_allclose(detail['history'], old_detail['history'], atol=2e-10, rtol=0)


def test_numerical_and_boundary_rejections():
    _, c1, c2, pilot = fixture(31)
    with pytest.raises(ValueError):
        PhysicalF1(31, c1, c2, 6).acquire(np.zeros(31), np.zeros(31), .1)
    with pytest.raises(ValueError):
        time_refine_keep_slots(np.zeros(31), pilot, np.zeros(31), np.full(31, .5),
                               [3, 3], [.5, .5 + 1e-7], [1, 1], c1, c2, .1)
