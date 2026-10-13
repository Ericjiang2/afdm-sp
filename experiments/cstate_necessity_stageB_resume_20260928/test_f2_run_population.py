"""Synthetic scheduler/cost regression; no receiver, truth, or observation data."""

from __future__ import annotations

from dataclasses import dataclass
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"))
sys.path.insert(0, str(ROOT / "experiments/cstate_necessity_stageB_resume_20260928"))
import f2_run_population as runner  # noqa: E402
import evidence  # noqa: E402


def test_shared_prefix_allocation_and_logical_clocks() -> None:
    rows = [{"observation_id": f"s650_f{i:04d}", "observation_sha256": f"sha{i}"}
            for i in range(1024)]
    historical = {row["observation_id"]: {
        "raw_path": "irrelevant",
        "baseline_syndrome_weight": int(int(row["observation_id"][-4:]) < 40)}
        for row in rows}
    calls: list[tuple[str, str, str]] = []

    class FakeEvidence:
        def load_artifact(self, _path):
            return {"baseline_arrays": {}}, {}

    manifest = {"producer_source_hashes": {},
                "population_observed_seal_sha256": "synthetic",
                "stage_a_observed_seal_sha256": "synthetic",
                "policy_names": list(runner.POLICIES),
                "maximum_wall_seconds": 60,
                "maximum_f0_continuations": 120,
                "maximum_f2e_continuations": 2048,
                "per_call_cap_seconds": {name: 10 for name in runner.POLICIES}}
    bound = {"manifest": manifest, "rows": rows, "previous_f0": historical,
             "evidence": FakeEvidence(), "environment": {}}

    def fake_prefix(_out, _args, _bound, row, arm, _attempt, _old_arrays=None):
        frame = int(row["observation_id"][-4:])
        trigger = (arm == "F0" and frame < 40) or (arm == "F2E" and frame < 5)
        calls.append((row["observation_id"], "prefix", arm))
        return {"record": {"arm": arm, "raw_sha256": "prefix",
                "raw_path": "synthetic-prefix", "complete_latency_seconds": 0.4,
                "final_syndrome_weight": int(trigger),
                "checkpoints": [{"round": 0, "decision_ready_seconds": 0.08,
                                 "durable_seconds": 0.1, "path": "r0", "sha256": "a",
                                 "syndrome_weight": 1},
                                {"round": 1, "decision_ready_seconds": 0.18,
                                 "durable_seconds": 0.2, "path": "r1", "sha256": "b",
                                 "syndrome_weight": int(trigger)}]},
                "final_bits": np.zeros(2048, np.uint8),
                "final_info": np.zeros(1024, np.uint8)}

    def fake_branch(_out, _bound, row, prefix, policy, _attempt):
        calls.append((row["observation_id"], "branch", policy))
        assert prefix["record"]["final_syndrome_weight"] == 1
        return {"record": {"arm": policy, "raw_sha256": "branch",
                "raw_path": "synthetic-branch", "complete_latency_seconds": 0.3,
                "final_syndrome_weight": 0,
                "checkpoints": [{"round": 2, "decision_ready_seconds": 0.15,
                                 "durable_seconds": 0.2, "path": "r2", "sha256": "c",
                                 "syndrome_weight": 0}]},
                "final_bits": np.zeros(2048, np.uint8),
                "final_info": np.zeros(1024, np.uint8)}

    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "synthetic"
        args = SimpleNamespace(out=out, manifest_sha256="synthetic",
                               historical_observed=Path(directory))
        with (patch.object(runner, "preflight", return_value=bound),
              patch.object(runner, "_prefix", fake_prefix),
              patch.object(runner, "_branch", fake_branch)):
            runner.run(args)
        seal = json.loads((out / "observed_seal.json").read_text())
        assert seal["actual_prefix_calls"] == 2048
        assert seal["actual_continuation_calls"] == 130
        assert seal["f0_trigger_frames"] == 40
        assert seal["f2e_trigger_frames"] == 5
        assert seal["logical_policy_rows"] == 7168
        policies = [json.loads(line) for line in
                    (out / "policy_ledger.jsonl").read_text().splitlines()]
        assert len(policies) == 7168
        assert all(row["complete_latency_seconds"] == 0.7 for row in policies
                   if row["branch_arm"] is not None)
        assert all(row["complete_latency_seconds"] == 0.4 for row in policies
                   if row["branch_arm"] is None)
        assert all(np.isclose(row["checkpoints"][-1]["durable_seconds"], 0.6) for row in policies
                   if row["branch_arm"] is not None)
        assert [arm for _stem, kind, arm in calls if kind == "prefix"].count("F0") == 1024
        assert [arm for _stem, kind, arm in calls if kind == "prefix"].count("F2E") == 1024


def test_complete_prefix_artifact_roundtrip() -> None:
    n = 1024
    arrays = {f"r{index}_decoded": np.zeros(2 * n, np.uint8)
              for index in (0, 1)}
    arrays.update(r1_app=np.zeros(2 * n), r1_check=np.ones(2 * n),
                  r1_delays=np.arange(155) % 103,
                  r1_dopplers=np.linspace(-3, 3, 155),
                  r1_gains=np.ones(155, complex))

    def fake_receive(_observation, _system, _code, *, checkpoint_sink, **_kwargs):
        for index in (0, 1):
            checkpoint_sink({"round": index, "decoded": arrays[f"r{index}_decoded"]},
                            arrays[f"r{index}_decoded"])
        return {"decoded": arrays["r1_decoded"]}, arrays, {"events": []}

    def fake_f2e(_observation, _system, _code, *, checkpoint_sink):
        for index in (0, 1):
            checkpoint_sink({"round": index, "decoded": arrays[f"r{index}_decoded"]},
                            arrays[f"r{index}_decoded"])
        channel = SimpleNamespace(p=155, delays=arrays["r1_delays"],
                                  dopplers=arrays["r1_dopplers"],
                                  gains=arrays["r1_gains"])
        return {"decoded": arrays["r1_decoded"]}, arrays, {
            "timing": {"events": []}, "estimator": {"channel": channel,
                                                   "passes": [{"iteration": 1}]}}

    class FakeEvidence:
        save_artifact = staticmethod(evidence.save_artifact)

    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory)
        for folder in ("raw", "checkpoints", "decisions"):
            (out / folder).mkdir()
        (out / "attempts.jsonl").touch()
        (out / "ledger.jsonl").touch()
        bound = {"evidence": FakeEvidence(),
                 "native": SimpleNamespace(receive=fake_receive),
                 "receive_f2e": fake_f2e, "system": object(), "code": object(),
                 "H": np.zeros((1, 2 * n), np.uint8),
                 "extract_info": lambda _code, _bits: np.zeros(n, np.uint8),
                 "previous_f0": {"synthetic": {"baseline_syndrome_weight": 0}}}
        row = {"observation_id": "synthetic", "observation_sha256": "synthetic",
               "observation_hash": "synthetic", "stream_ids": {}}
        with patch.object(runner, "_input", return_value={"y": np.zeros(n, complex),
                                                        "pilot": np.ones(n, complex),
                                                        "sigma2": 0.1}):
            for arm in ("F0", "F2E"):
                result = runner._prefix(out, SimpleNamespace(), bound, row, arm, 1,
                                        arrays if arm == "F0" else None)
                raw, _ = evidence.load_artifact(out / result["record"]["raw_path"])
                assert np.array_equal(raw["final_decoded"], arrays["r1_decoded"])
                assert len(result["record"]["checkpoints"]) == 2
                assert result["record"]["complete_latency_seconds"] >= \
                    result["record"]["checkpoints"][-1]["durable_seconds"]
                parts = result["record"]
                assert np.isclose(parts["complete_latency_seconds"],
                    parts["input_seconds"] +
                    parts["receiver_seconds_including_checkpoint"] +
                    parts["post_receiver_serialization_and_validation_seconds"],
                    atol=1e-9)


def test_complete_continuation_artifact_and_ready_clock() -> None:
    @dataclass
    class Result:
        evaluations: dict
        paths: list[int]

    def fake_branch(_observation, _system, _code, _native, _kernel,
                    arrays, arm):
        assert arm == "LOCAL20" and arrays["r1_app"][0] == 0
        arrays["r1_app"][0] = 17
        return {"result": Result({"trials": 0}, list(range(155))),
                "decoder": {"decoded": np.zeros(2048, np.uint8), "iterations": 2},
                "detector": {"extrinsic": np.zeros(2048)},
                "exclusive_stages": {"tf": 0.01, "ldpc": 0.01},
                "decision_ready_at": time.perf_counter()}

    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory)
        for folder in ("raw", "checkpoints", "decisions"):
            (out / folder).mkdir()
        (out / "attempts.jsonl").touch()
        (out / "ledger.jsonl").touch()
        arrays = {"r1_app": np.zeros(2048), "r1_check": np.ones(2048)}
        prefix = {"record": {"arm": "F2E", "raw_sha256": "synthetic",
                             "final_syndrome_weight": 1},
                  "observation": {"y": np.zeros(1024, complex),
                                  "pilot": np.ones(1024, complex), "sigma2": 0.1},
                  "arrays": arrays}
        bound = {"evidence": SimpleNamespace(save_artifact=evidence.save_artifact),
                 "branch": fake_branch, "native": object(), "kernel": object(),
                 "system": object(), "code": object(),
                 "H": np.zeros((1, 2048), np.uint8),
                 "extract_info": lambda _code, _bits: np.zeros(1024, np.uint8)}
        row = {"observation_id": "synthetic", "observation_sha256": "synthetic",
               "observation_hash": "synthetic", "stream_ids": {}}
        branch = runner._branch(out, bound, row, prefix, "F2E_LOCAL", 1)
        record = branch["record"]
        raw, _ = evidence.load_artifact(out / record["raw_path"])
        cp = record["checkpoints"][0]
        assert raw["arm"] == "F2E_LOCAL"
        assert raw["observation_hash"] == "synthetic"
        assert record["observation_hash"] == "synthetic"
        assert cp["decision_ready_seconds"] <= cp["durable_seconds"] <= \
            record["complete_latency_seconds"]
        assert np.isclose(record["complete_latency_seconds"],
            record["branch_setup_and_deepcopy_seconds"] +
            record["receiver_seconds_including_checkpoint"] +
            record["post_receiver_serialization_and_validation_seconds"], atol=1e-9)
        assert arrays["r1_app"][0] == 0


def test_interrupted_call_keeps_charged_failure_receipt() -> None:
    row = {"observation_id": "s650_f0000", "observation_sha256": "synthetic"}
    bound = {"manifest": {"producer_source_hashes": {},
                          "population_observed_seal_sha256": "synthetic",
                          "stage_a_observed_seal_sha256": "synthetic",
                          "policy_names": list(runner.POLICIES),
                          "maximum_wall_seconds": 10,
                          "per_call_cap_seconds": {name: 10 for name in runner.POLICIES}},
             "rows": [row], "previous_f0": {"s650_f0000": {"raw_path": "old"}},
             "environment": {}, "evidence": SimpleNamespace(
                 load_artifact=lambda _path: ({"baseline_arrays": {}}, {}))}
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "interrupted"
        args = SimpleNamespace(out=out, manifest_sha256="synthetic",
                               historical_observed=Path(directory))
        with (patch.object(runner, "preflight", return_value=bound),
              patch.object(runner, "_prefix", side_effect=KeyboardInterrupt)):
            try:
                runner.run(args)
            except KeyboardInterrupt:
                pass
            else:
                raise AssertionError("interrupt was swallowed")
        failed = json.loads((out / "failure.json").read_text())
        charged = json.loads((out / "failed_calls.jsonl").read_text().strip())
        assert failed["status"] == "invalid_partial"
        assert failed["failed_call"] == charged
        assert charged["arm"] == "F0" and charged["charged_seconds"] >= 0
        assert not (out / "observed_seal.json").exists()


if __name__ == "__main__":
    test_shared_prefix_allocation_and_logical_clocks()
    test_complete_prefix_artifact_roundtrip()
    print("F2 shared-prefix accounting fixture passed; zero real receiver calls")
