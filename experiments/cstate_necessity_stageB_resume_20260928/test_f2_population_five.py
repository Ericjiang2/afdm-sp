"""Synthetic five-policy accounting and pre-truth gates; zero real receiver calls."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

import analyze_method_closure_five as reader
import f2_run_population_five as runner


def _synthetic_prefix(row, arm):
    frame = int(row["observation_id"][-4:])
    triggered = int(arm == "F0" and frame < 40)
    return {"record": {"arm": arm, "raw_sha256": "prefix", "raw_path": "prefix.npz",
            "complete_latency_seconds": .4, "final_syndrome_weight": triggered,
            "checkpoints": [{"round": index, "decision_ready_seconds": .05 + .1 * index,
                             "durable_seconds": .1 + .1 * index,
                             "path": f"r{index}", "sha256": f"h{index}",
                             "syndrome_weight": triggered}
                            for index in (0, 1)]},
            "final_bits": np.zeros(2048, np.uint8),
            "final_info": np.zeros(1024, np.uint8)}


def _synthetic_branch(policy):
    return {"record": {"arm": policy, "raw_sha256": "branch",
            "raw_path": "branch.npz", "complete_latency_seconds": .3,
            "final_syndrome_weight": 0,
            "checkpoints": [{"round": 2, "decision_ready_seconds": .15,
                             "durable_seconds": .2, "path": "r2", "sha256": "h2",
                             "syndrome_weight": 0}]},
            "final_bits": np.zeros(2048, np.uint8),
            "final_info": np.zeros(1024, np.uint8)}


def test_full_five_policy_allocation_and_no_excluded_calls() -> None:
    rows = [{"observation_id": f"s650_f{i:04d}", "observation_sha256": f"sha{i}"}
            for i in range(1024)]
    previous = {row["observation_id"]: {"raw_path": "unused",
                "baseline_syndrome_weight": int(i < 40)}
                for i, row in enumerate(rows)}
    calls = []
    bound = {"manifest": {"producer_source_hashes": {},
             "population_observed_seal_sha256": "synthetic",
             "stage_a_observed_seal_sha256": "synthetic",
             "maximum_wall_seconds": 60,
             "per_call_cap_seconds": {name: 10 for name in runner.POLICIES}},
             "rows": rows, "previous_f0": previous, "environment": {},
             "evidence": SimpleNamespace(load_artifact=lambda _path:
                                         ({"baseline_arrays": {}}, {}))}

    def prefix(_out, _args, _bound, row, arm, _attempt, _old=None):
        calls.append(arm)
        return _synthetic_prefix(row, arm)

    def branch(_out, _bound, _row, _prefix, policy, _attempt):
        calls.append(policy)
        return _synthetic_branch(policy)

    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "five"
        args = SimpleNamespace(out=out, manifest_sha256="synthetic",
                               historical_observed=Path(directory))
        with (patch.object(runner, "preflight", return_value=bound),
              patch.object(runner.base, "_prefix", prefix),
              patch.object(runner.base, "_branch", branch)):
            runner.run(args)
        seal = json.loads((out / "observed_seal.json").read_text())
        assert seal["actual_prefix_calls"] == 2048
        assert seal["actual_continuation_calls"] == 120
        assert seal["actual_total_calls"] == 2168
        assert seal["logical_policy_rows"] == 5120
        assert seal["f0_trigger_frames"] == 40
        assert seal["excluded_policies"] == runner.EXCLUDED
        assert len(calls) == 2168
        assert not (set(calls) & set(runner.EXCLUDED))
        policies = [json.loads(line) for line in
                    (out / "policy_ledger.jsonl").read_text().splitlines()]
        assert len(policies) == 5120
        assert {row["policy"] for row in policies} == set(runner.POLICIES)
        assert sum(row["branch_arm"] is not None for row in policies) == 120
        assert all(row["schema"] == runner.SCHEMA for row in policies)


def test_reader_refuses_uncommitted_observed_before_truth_open() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        registration = root / "registration.json"
        stage = root / "stage.json"
        observed = root / "observed"
        truth = root / "truth"
        observed.mkdir()
        truth.mkdir()
        registration.write_text(json.dumps({"schema": runner.SCHEMA,
            "status": "locked", "policy_names": list(runner.POLICIES),
            "excluded_policies": runner.EXCLUDED}))
        stage.write_text('{"status":"locked"}')
        (observed / "manifest.json").write_text('{}')
        args = SimpleNamespace(f2_observed=observed, f2_registration=registration,
            stage_a_registration=stage, out=root / "analysis",
            population_observed=root / "population", population_truth=truth,
            f2_git_attestation=root / "missing", f2_git_attestation_sha256="0" * 64,
            f2_registration_commit="a" * 40, f2_observed_commit="b" * 40,
            f2_seal_repo_path="observed/observed_seal.json")
        with patch.object(reader.shared, "_attest", side_effect=ValueError("Git gate")):
            with pytest.raises(ValueError, match="Git gate"):
                reader.verify_pretruth(args)
        assert list(truth.iterdir()) == []


def test_trigger_plan_excludes_f2e_branches() -> None:
    assert runner.continuation_plan(0, 0) == ()
    assert set(runner.continuation_plan(1, 1)) == {"B", "F0_LOCAL", "F2T"}
    assert not set(runner.continuation_plan(1, 40)) & set(runner.EXCLUDED)


def test_call_budget_respects_remaining_campaign_wall() -> None:
    with patch.object(runner.time, "perf_counter", return_value=95.5):
        assert runner.call_budget_seconds(0.0, 100, 120) == 4.5
        assert runner.call_budget_seconds(0.0, 100, 2) == 2.0
    with patch.object(runner.time, "perf_counter", return_value=101.0):
        with pytest.raises(TimeoutError, match="campaign wall cap"):
            runner.call_budget_seconds(0.0, 100, 120)


def test_reader_validates_cumulative_rss_and_logical_paid_costs() -> None:
    ledger = [
        {"attempt": 1, "observation_id": "s650_f0000", "kind": "prefix",
         "arm": "F0", "rss_peak_kib_cumulative": 100},
        {"attempt": 2, "observation_id": "s650_f0000", "kind": "prefix",
         "arm": "F2E", "rss_peak_kib_cumulative": 120},
    ]
    rows, peak = reader.memory_ledger(
        ledger, {"campaign_rss_peak_kib_cumulative": 125})
    assert len(rows) == 2 and peak == 125
    assert rows[-1]["rss_peak_kib_cumulative"] == 120
    with pytest.raises(ValueError, match="RSS"):
        reader.memory_ledger(ledger, {"campaign_rss_peak_kib_cumulative": 119})
    ledger[1]["rss_peak_kib_cumulative"] = 99
    with pytest.raises(ValueError, match="RSS"):
        reader.memory_ledger(ledger, {"campaign_rss_peak_kib_cumulative": 125})

    parent = {"raw_sha256": "parent", "complete_latency_seconds": .4}
    branch = {"raw_sha256": "branch", "complete_latency_seconds": .3}
    logical = {"prefix_raw_sha256": "parent", "branch_raw_sha256": "branch",
               "prefix_complete_seconds": .4, "branch_complete_seconds": .3,
               "complete_latency_seconds": .7}
    assert reader.validate_logical_cost(logical, parent, branch) == .3
    bad = {**logical, "branch_raw_sha256": "other"}
    with pytest.raises(ValueError, match="source or complete cost"):
        reader.validate_logical_cost(bad, parent, branch)
    bad = {**logical, "prefix_complete_seconds": .41}
    with pytest.raises(ValueError, match="source or complete cost"):
        reader.validate_logical_cost(bad, parent, branch)
    no_branch = {**logical, "branch_raw_sha256": None,
                 "branch_complete_seconds": 0.0, "complete_latency_seconds": .4}
    assert reader.validate_logical_cost(no_branch, parent, None) == 0.0
