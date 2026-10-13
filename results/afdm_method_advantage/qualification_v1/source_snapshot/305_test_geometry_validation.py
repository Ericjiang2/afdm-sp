"""Zero-receiver contracts for the instrumented CSTATE geometry engine."""

import sys
from pathlib import Path as FilePath

import numpy as np
import pytest

ROOT = FilePath(__file__).resolve().parents[2]
for source in ("experiments/sp_afdm_frozen_20260920/src",
               "experiments/sp_afdm_native_joint_20260921/src",
               "experiments/tf_geometry_reopen_20260922",
               "experiments/tf_cstate_validation_20260922"):
    sys.path.insert(0, str(ROOT / source))

import geometry_reopen as old  # noqa: E402
import geometry_validation as new  # noqa: E402
from compact_state import CPPField  # noqa: E402


def fixture():
    rng = np.random.default_rng(22209)
    n = 19
    Y = rng.normal(size=n) + 1j * rng.normal(size=n)
    x = rng.normal(size=n) + 1j * rng.normal(size=n)
    v = rng.random(n) * .2
    paths = [old.Path(1, -.4), old.Path(1, .8), old.Path(7, 1.2)]
    args = dict(c1=.031, c2=.011, ridge=.2, max_delay=9,
                max_edits=2, local_passes=2)
    return Y, x, v, paths, args


def compare_to_old(reference, result, tolerance=2e-10):
    assert [(e["slot"], e["new"]) for e in result.edits] == [
        (e["slot"], e["new"]) for e in reference.edits]
    assert len(result.paths) == len(reference.paths)
    assert [p.delay for p in result.paths] == [p.delay for p in reference.paths]
    np.testing.assert_allclose([p.doppler for p in result.paths],
                               [p.doppler for p in reference.paths], atol=tolerance, rtol=0)
    np.testing.assert_allclose(result.gains, reference.gains, atol=tolerance, rtol=0)
    np.testing.assert_allclose(result.objective_after, reference.objective_after,
                               atol=tolerance, rtol=0)
    assert len(result.global_trace) == len(reference.global_trace)
    for actual, expected in zip(result.global_trace, reference.global_trace):
        np.testing.assert_array_equal(actual["valid"], expected["valid"])
        np.testing.assert_allclose(actual["scores"], expected["scores"],
                                   atol=tolerance, rtol=0)
        assert actual["selected"]["slot"] == expected["selected"]["slot"]
        assert actual["selected"]["replacement"] == expected["selected"]["replacement"]
        assert (actual["accepted"] is None) == (expected["accepted"] is None)
        assert len(actual["top_k"]) == len(expected["top_k"])
    if result.diagnostics["strategy"] == "compact" and not result.diagnostics["numerical_fallback"]:
        assert result.evaluations["global_candidate_columns"] == sum(
            step["candidate_columns"] for step in result.global_trace)


@pytest.mark.parametrize("strategy", ["direct", "compact"])
def test_full_grid_and_local_parity_with_frozen_production(strategy):
    Y, x, v, paths, args = fixture()
    reference = old.reopen_geometry(Y, x, v, paths, **args)
    result = new.reopen_geometry(Y, x, v, paths, strategy=strategy, **args)
    compare_to_old(reference, result)
    assert result.diagnostics["selection_order"] == "score,slot,delay,doppler"
    assert result.diagnostics["numerical_fallback"] is False
    assert len(result.local_trace) == len(reference.local_trace)
    assert result.evaluations["local_trials"] == reference.evaluations["local_trials"]
    for actual, expected in zip(result.local_trace, reference.local_trace):
        assert actual["bounds"] == expected["bounds"]
        np.testing.assert_allclose(actual["endpoint"]["doppler"],
                                   expected["endpoint"]["doppler"], atol=2e-10, rtol=0)


def test_local_arm_shared_pipeline_and_timing_sum():
    Y, x, v, paths, args = fixture()
    args.update(max_edits=0)
    direct = new.reopen_geometry(Y, x, v, paths, strategy="direct", **args)
    compact = new.reopen_geometry(Y, x, v, paths, strategy="compact", **args)
    assert direct.paths == compact.paths
    np.testing.assert_array_equal(direct.gains, compact.gains)
    assert direct.global_trace == compact.global_trace == []
    for result in (direct, compact):
        timing = result.diagnostics["stage_timing"]
        assert set(timing["exclusive_seconds"]) == set(new.STAGES)
        assert all(value >= 0 for value in timing["exclusive_seconds"].values())
        assert timing["total_seconds"] == sum(timing["exclusive_seconds"].values())
        assert result.elapsed_seconds == timing["total_seconds"]
        assert timing["exclusive_seconds"]["local_refinement"] > 0
        assert timing["exclusive_seconds"]["geometry_finalization"] > 0


def test_cpp_field_matches_production_response_all_atoms():
    from physical import daft
    Y, x, v, _, args = fixture()
    xt = daft(x, args["c1"], args["c2"], True)
    nus = np.arange(-1, 1.01, .25)
    field = CPPField(xt, args["c1"], 9, nus)
    bank = [old.Path(delay, float(nu)) for delay in range(10) for nu in nus]
    B = old._responses(xt, bank, args["c1"], args["c2"])
    np.testing.assert_allclose(field.correlate(Y), B.conj().T @ Y,
                               atol=2e-12, rtol=0)


def test_same_delay_validity_and_zero_observation_ties():
    Y, x, v, paths, args = fixture()
    paths = [old.Path(1, -.5), old.Path(1, .75), old.Path(7, 1.25)]
    args.update(max_edits=1, local_passes=0, doppler_min=-1.5, doppler_max=1.5)
    reference = old.reopen_geometry(np.zeros_like(Y), x, v, paths, **args)
    result = new.reopen_geometry(np.zeros_like(Y), x, v, paths,
                                 strategy="compact", **args)
    compare_to_old(reference, result)
    assert result.global_trace[0]["accepted"] is None
    assert result.global_trace[0]["duplicate_rejections"] > 0
    assert len(result.global_trace[0]["top_k"]) == 20
    assert result.global_trace[0]["selected"]["slot"] == 0
    assert result.global_trace[0]["selected"]["replacement"] == {
        "delay": 0, "doppler": -1.5}


def test_extreme_condition_falls_back_to_original_full_grid():
    rng = np.random.default_rng(123456)
    n = 64
    x = rng.normal(size=n) + 1j * rng.normal(size=n)
    Y = rng.normal(size=n) + 1j * rng.normal(size=n)
    v = np.zeros(n)
    paths = [old.Path(1, .2), old.Path(1, .2000011), old.Path(6, -.4)]
    args = dict(c1=.137/n, c2=.01, ridge=1e-10, max_delay=8,
                doppler_min=-1., doppler_max=1., grid_step=.25,
                max_edits=2, local_passes=0)
    direct = new.reopen_geometry(Y, x, v, paths, strategy="direct", **args)
    compact = new.reopen_geometry(Y, x, v, paths, strategy="compact", **args)
    compare_to_old(direct, compact)
    assert compact.diagnostics["numerical_fallback"] is True
    assert compact.evaluations["fallback_calls"] == 1
    assert compact.evaluations["discarded_compact_evaluations"] is not None
    assert compact.diagnostics["stage_timing"]["exclusive_seconds"]["structural_fallback_direct"] > 0
    assert compact.diagnostics["stage_timing"]["discarded_compact_seconds"] > 0


def test_compact_algebra_assertion_is_not_converted_to_fallback(monkeypatch):
    Y, x, v, paths, args = fixture()

    def fail_algebra(*_args):
        raise AssertionError("algebra mismatch")

    monkeypatch.setattr(new, "exchange_scores", fail_algebra)
    with pytest.raises(AssertionError, match="algebra mismatch"):
        new.reopen_geometry(Y, x, v, paths, strategy="compact", **args)


def test_qualification_api_and_serializable_full_trace(tmp_path):
    from dataclasses import asdict
    from evidence import load_artifact, save_artifact
    Y, x, v, paths, args = fixture()
    trace, result = new.score_entering_state(Y, x, v, paths, strategy="compact", **args)
    assert trace["scores"].shape == trace["valid"].shape == (3, 250)
    assert len(result.global_trace) == 1
    target = tmp_path / "result.npz"
    save_artifact(target, asdict(result), {"schema": "cstate-test"})
    restored, _ = load_artifact(target, {"schema": "cstate-test"})
    np.testing.assert_array_equal(restored["global_trace"][0]["scores"], trace["scores"])
    assert restored["diagnostics"]["stage_timing"]["total_seconds"] == result.elapsed_seconds


def test_top_k_observer_does_not_change_geometry_or_scores():
    Y, x, v, paths, args = fixture()
    with_trace = new.reopen_geometry(Y, x, v, paths, strategy="compact", top_k=20, **args)
    without_top = new.reopen_geometry(Y, x, v, paths, strategy="compact", top_k=0, **args)
    assert with_trace.paths == without_top.paths
    np.testing.assert_array_equal(with_trace.gains, without_top.gains)
    assert with_trace.objective_after == without_top.objective_after
    for a, b in zip(with_trace.global_trace, without_top.global_trace):
        np.testing.assert_array_equal(a["scores"], b["scores"])
        np.testing.assert_array_equal(a["valid"], b["valid"])
        assert a["selected"] == b["selected"]
        assert len(a["top_k"]) == 20 and b["top_k"] == []


def test_direct_rebuilds_chunk_paths_and_checks_duplicates_per_slot(monkeypatch):
    """The timed direct control retains the executed adapter's work shape."""
    Y, x, v, paths, args = fixture()
    groups = []
    duplicate_calls = 0
    original_responses = new._responses
    original_duplicate = new._duplicate

    def responses(signal, group, c1, c2):
        groups.append(tuple(group))
        return original_responses(signal, group, c1, c2)

    def duplicate(path, others, tolerance):
        nonlocal duplicate_calls
        duplicate_calls += 1
        return original_duplicate(path, others, tolerance)

    monkeypatch.setattr(new, "_responses", responses)
    monkeypatch.setattr(new, "_duplicate", duplicate)
    result = new.reopen_geometry(Y, x, v, paths, strategy="direct", **args)
    assert len(result.global_trace) == 2
    chunks_per_step = 4  # 250 atoms in the declared fixture, chunk size 64.
    assert len(groups) == 2 * chunks_per_step
    assert groups[0][0] is not groups[chunks_per_step][0]
    assert duplicate_calls >= 2 * len(paths) * 250


def test_invalid_strategy_and_input_fail_explicitly():
    Y, x, v, paths, args = fixture()
    with pytest.raises(ValueError):
        new.reopen_geometry(Y, x, v, paths, strategy="other", **args)
    with pytest.raises(ValueError):
        new.reopen_geometry(Y, x, -v, paths, strategy="compact", **args)
