"""Independent contracts for the classical geometry exchange adapter."""

import sys
from pathlib import Path as FilePath

import numpy as np
import pytest

ROOT = FilePath(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"))

from geometry_reopen import Path, reopen_geometry  # noqa: E402


def _dense_action(n, delay, doppler, c1):
    row = np.arange(n)
    col = (row - delay) % n
    U = np.zeros((n, n), complex)
    phase = np.exp(2j * np.pi * row * doppler / n)
    phase *= np.where(row < delay,
                      np.exp(2j * np.pi * c1 * (n * n + 2 * n * (row - delay))), 1)
    U[row, col] = phase
    return U


def _dense_score(Y, x, v, paths, c1, c2, ridge):
    n = len(Y)
    j = np.arange(n)
    F = np.exp(-2j * np.pi * np.outer(j, j) / n) / np.sqrt(n)
    A = np.exp(2j * np.pi * c2 * j * j)[:, None] * F * np.exp(2j * np.pi * c1 * j * j)[None, :]
    U = [_dense_action(n, p.delay, p.doppler, c1) for p in paths]
    B = np.column_stack([u @ A.conj().T @ x for u in U])
    V = np.diag(v)
    G = np.array([[np.trace(ui.conj().T @ uj @ A.conj().T @ V @ A)
                   for uj in U] for ui in U])
    Q = B.conj().T @ B + G + ridge * np.eye(len(paths))
    b = B.conj().T @ Y
    return float(np.vdot(Y, Y).real - np.vdot(b, np.linalg.solve(Q, b)).real)


def _fixture(n=9):
    rng = np.random.default_rng(22209)
    x = rng.normal(size=n) + 1j * rng.normal(size=n)
    Y = rng.normal(size=n) + 1j * rng.normal(size=n)
    v = rng.random(n) * .3
    return Y, x, v, [Path(1, -.5), Path(1, .75)], .031, .011, .19


def _run(**overrides):
    Y, x, v, paths, c1, c2, ridge = _fixture()
    args = dict(c1=c1, c2=c2, ridge=ridge, max_delay=3,
                doppler_min=-1, doppler_max=1, grid_step=.5,
                max_edits=1, local_passes=0, top_k=20)
    args.update(overrides)
    return reopen_geometry(Y, x, v, paths, **args)


def test_all_slot_schur_scores_against_independent_dense_refits():
    Y, x, v, paths, c1, c2, ridge = _fixture()
    result = _run()
    trace = result.global_trace[0]
    scores = trace["scores"]
    valid = trace["valid"]
    assert scores.shape == valid.shape == (2, 20)
    for slot in range(2):
        for candidate, (delay, doppler) in enumerate(zip(
                trace["candidate_delays"], trace["candidate_dopplers"])):
            trial = paths.copy()
            trial[slot] = Path(int(delay), float(doppler))
            expected = _dense_score(Y, x, v, trial, c1, c2, ridge)
            np.testing.assert_allclose(scores[slot, candidate], expected, rtol=0, atol=2e-10)
            duplicate = any(delay == p.delay and abs(doppler - p.doppler) < 1e-6
                            for i, p in enumerate(paths) if i != slot)
            assert valid[slot, candidate] is not None
            assert bool(valid[slot, candidate]) == (not duplicate)
    eligible = np.where(valid, scores, np.inf)
    np.testing.assert_allclose(result.objective_after,
                               min(_dense_score(Y, x, v, paths, c1, c2, ridge),
                                   float(eligible.min())), rtol=0, atol=2e-10)
    assert trace["selected"]["frozen_score"] == float(eligible.min())


def test_same_delay_preservation_and_observer_noninterference():
    result = _run(top_k=20, local_passes=1)
    alternate = _run(top_k=0, local_passes=1)
    assert len(result.paths) == len(alternate.paths) == 2
    assert any(p.delay == 1 for p in result.paths)
    assert result.paths == alternate.paths
    np.testing.assert_allclose(result.gains, alternate.gains, rtol=0, atol=0)
    assert result.objective_after == alternate.objective_after
    assert len(result.global_trace[0]["top_k"]) == 20
    assert len(alternate.global_trace[0]["top_k"]) == 0
    assert alternate.global_trace[0]["selected"] == result.global_trace[0]["selected"]
    assert result.evaluations["top_k_extra_solves"] == 0


def test_stable_ranking_ties_and_rejected_step_are_logged():
    Y, x, v, paths, c1, c2, ridge = _fixture()
    zero = np.zeros_like(Y)
    a = reopen_geometry(zero, x, v, paths, c1=c1, c2=c2, ridge=ridge,
                        max_delay=3, doppler_min=-1, doppler_max=1,
                        grid_step=.5, max_edits=2, local_passes=0)
    b = reopen_geometry(zero, x, v, paths, c1=c1, c2=c2, ridge=ridge,
                        max_delay=3, doppler_min=-1, doppler_max=1,
                        grid_step=.5, max_edits=2, local_passes=0)
    assert len(a.global_trace) == 1
    trace = a.global_trace[0]
    assert trace["accepted"] is None
    assert trace["selected"] is not None
    assert a.evaluations["global_rejected_steps"] == 1
    assert trace["slot_tests"] == 40
    assert trace["duplicate_rejections"] > 0
    assert [e["replacement"] for e in trace["top_k"]] == [
        e["replacement"] for e in b.global_trace[0]["top_k"]]
    keys = [(e["frozen_score"], e["slot"], e["replacement"]["delay"],
             e["replacement"]["doppler"]) for e in trace["top_k"]]
    assert keys == sorted(keys)


def test_local_windows_trials_and_evidence_roundtrip(tmp_path):
    from dataclasses import asdict
    from evidence import load_artifact, save_artifact
    result = _run(max_edits=0, local_passes=2)
    assert result.global_trace == []
    assert len(result.local_trace) == 4
    assert result.evaluations["local_trials"] == sum(t["trial_count"] for t in result.local_trace)
    for t in result.local_trace:
        assert t["trial_count"] <= 16
        assert t["bounds"][0] <= t["endpoint"]["doppler"] <= t["bounds"][1]
        assert t["center"] == t["local_phase_entering_paths"][t["slot"]]["doppler"]
    evidence = asdict(result)
    assert evidence["diagnostics"]["gamma"].shape == (2, 2)
    assert evidence["evaluations"]["joint_gain_solves"] >= 2
    target = tmp_path / "exchange.npz"
    save_artifact(target, evidence, {"kind": "geometry-test"})
    loaded, _ = load_artifact(target, {"kind": "geometry-test"})
    np.testing.assert_array_equal(loaded["gains"], result.gains)
    assert loaded["local_trace"][0]["trial_count"] == result.local_trace[0]["trial_count"]


def test_global_trace_evidence_roundtrip(tmp_path):
    from dataclasses import asdict
    from evidence import load_artifact, save_artifact
    result = _run()
    target = tmp_path / "exchange.npz"
    save_artifact(target, asdict(result), {"kind": "geometry-test"})
    loaded, _ = load_artifact(target, {"kind": "geometry-test"})
    np.testing.assert_array_equal(loaded["global_trace"][0]["scores"],
                                  result.global_trace[0]["scores"])
    np.testing.assert_array_equal(loaded["global_trace"][0]["valid"],
                                  result.global_trace[0]["valid"])
    assert loaded["global_trace"][0]["top_k"] == result.global_trace[0]["top_k"]


def test_duplicate_local_trials_are_counted_without_gain_solves():
    result = _run(max_edits=0, local_passes=1, duplicate_tolerance=1.2)
    rejected = sum(t["rejected_duplicate_trials"] for t in result.local_trace)
    assert rejected > 0
    assert result.evaluations["local_duplicate_rejections"] == rejected
    assert result.evaluations["local_trials"] == sum(t["trial_count"] for t in result.local_trace)
    assert result.evaluations["joint_gain_solves"] == (
        2 + result.evaluations["local_trials"] - rejected)


@pytest.mark.parametrize("change", [
    dict(ridge=0), dict(grid_step=0), dict(top_k=-1), dict(max_delay=9),
    dict(doppler_min=1, doppler_max=-1), dict(chunk_size=0),
    dict(local_max_evals=0), dict(c1=float("nan")), dict(max_edits=3),
])
def test_invalid_configuration_rejected(change):
    with pytest.raises(ValueError):
        _run(**change)


def test_invalid_data_and_duplicate_start_rejected():
    Y, x, v, paths, c1, c2, ridge = _fixture()
    with pytest.raises(ValueError):
        reopen_geometry(Y, x, -v, paths, c1=c1, c2=c2, ridge=ridge, max_delay=3)
    with pytest.raises(ValueError):
        reopen_geometry(Y, x, v, [paths[0], paths[0]],
                        c1=c1, c2=c2, ridge=ridge, max_delay=3)
    with pytest.raises(ValueError):
        reopen_geometry(Y, x, v, paths, c1=c1, c2=c2,
                        ridge=ridge, max_delay=3, top_k=True)
