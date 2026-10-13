"""Synthetic, receiver-free contracts for the post-seal method-closure reader."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import analyze_method_closure as reader


class ReaderContracts(unittest.TestCase):
    def test_three_snr_subset_requires_exact_index_and_id(self) -> None:
        rows = [
            {"snr_centi_db": snr, "frame": index,
             "observation_id": f"s{snr}_f{index:04d}"}
            for snr in (600, 650, 700) for index in range(reader.N)
        ]
        self.assertEqual(len(reader._subset(rows)), reader.N)
        wrong = [dict(row) for row in rows]
        wrong[reader.N + 11]["frame"] = 12
        with self.assertRaisesRegex(ValueError, "1024-ID"):
            reader._subset(wrong)
        with self.assertRaisesRegex(ValueError, "three-SNR"):
            reader._subset(rows[:reader.N])

    def test_f1_order_and_full_denominator(self) -> None:
        self.assertEqual(reader._f1_schedule(0), ("B", "Cref", "Ccompat"))
        self.assertEqual(reader._f1_schedule(16), ("B", "Ccompat", "Cref"))
        rows = []
        for frame in range(reader.N):
            for arm in reader._f1_schedule(frame):
                rows.append({"status": "ok", "attempt_index": len(rows) + 1,
                             "observation_id": f"s650_f{frame:04d}", "arm": arm})
        grouped = reader._index_f1(rows)
        self.assertEqual(len(rows), 2112)
        self.assertEqual(sum("Cref" in group for group in grouped.values()), 64)
        rows[1]["arm"] = "Ccompat"
        with self.assertRaises(ValueError):
            reader._index_f1(rows)

    def test_inventory_has_same_pass_sha_md5_size_path(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "raw" / "fixture.npz"
            path.parent.mkdir()
            path.write_bytes(b"synthetic payload")
            seal = {"files": {"raw/fixture.npz": hashlib.sha256(
                path.read_bytes()).hexdigest()}}
            got = reader._inventory(root, seal)["raw/fixture.npz"]
            self.assertEqual(got["sha256"], seal["files"]["raw/fixture.npz"])
            self.assertEqual(got["md5"], hashlib.md5(path.read_bytes()).hexdigest())
            self.assertEqual(got["size_bytes"], 17)
            self.assertEqual(got["path"], str(path.resolve()))
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                reader._inventory(root, seal)

    def test_deadline_latest_durable_and_paired_denominator(self) -> None:
        records = {}
        for frame in range(reader.N):
            correct = frame % 2 == 0
            records[f"s650_f{frame:04d}"] = {
                "B": {"info_correct": correct, "coded_correct": correct,
                      "coded_errors": 0 if correct else 1,
                      "syndrome_weight": 0 if correct else 1,
                      "valid_but_wrong": False, "triggered": False,
                      "components": {"complete_latency_seconds": .6},
                      "checkpoints": [
                          {"round": 0, "ready_seconds": .4, "info_correct": False},
                          {"round": 1, "ready_seconds": .6, "info_correct": correct}]},
                "Ccompat": {"info_correct": True, "coded_correct": True,
                            "coded_errors": 0, "syndrome_weight": 0,
                            "valid_but_wrong": False, "triggered": False,
                            "components": {"complete_latency_seconds": .4},
                            "checkpoints": [
                                {"round": 0, "ready_seconds": .2, "info_correct": True}]},
            }
        report = reader._summarize(records)
        self.assertEqual(report["arms"]["B"]["information_failures"], 512)
        self.assertEqual(report["arms"]["B"]["deadlines"]["0.5"]["correct"], 0)
        self.assertEqual(report["arms"]["B"]["deadlines"]["1.0"]["correct"], 512)
        self.assertEqual(report["arms"]["Ccompat"]["deadlines"]["0.5"]["correct"], 1024)
        self.assertEqual(report["paired"]["B_vs_Ccompat"]["n"], 1024)

    def test_git_failure_precedes_truth_open(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            observed = root / "observed"
            observed.mkdir()
            registration = root / "registration.json"
            stage = root / "stage.json"
            registration.write_text(json.dumps({"schema":
                "cstate-necessity-stage-b-f1-compat/1", "status": "locked"}))
            stage.write_text('{"status":"locked"}')
            (observed / "manifest.json").write_text('{"registration_commit":"x"}')
            args = argparse.Namespace(campaign="f1", out=root / "new-output",
                f1_observed=observed, population_observed=root / "population",
                population_truth=root / "truth-does-not-exist",
                f1_registration=registration, stage_a_registration=stage,
                f1_git_attestation=root / "attestation.json",
                f1_git_attestation_sha256="bad", f1_observed_commit="bad",
                f1_seal_repo_path="bad")
            with patch.object(reader, "_attest", side_effect=ValueError("Git gate")):
                with self.assertRaisesRegex(ValueError, "Git gate"):
                    reader.verify_pretruth(args)

    def test_actual_producer_prefix_and_branch_envelopes_parse(self) -> None:
        """Real artifact codec and producer wrappers; synthetic stub, zero receiver calls."""
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
                               "experiments/sp_afdm_frozen_20260920/src"))
        import f2_run_population as producer
        import evidence

        decoded = np.zeros(2048, np.uint8)
        decoded[0] = 1
        arrays = {"r0_decoded": decoded.copy(), "r1_decoded": decoded.copy(),
                  "r1_app": np.zeros(2048), "r1_check": np.zeros(2048)}
        H = np.zeros((1, 2048), np.uint8)
        H[0, 0] = 1
        free = np.arange(1024, 2048)

        def native_receive(_obs, _system, _code, *, checkpoint_sink, **_kw):
            for index in (0, 1):
                checkpoint_sink({"round": index}, decoded)
            return {"decoded": decoded}, arrays, {"events": []}

        @dataclass
        class Result:
            evaluations: dict
            paths: list[int]

        def branch_stub(_obs, _system, _code, _native, _kernel, _arrays, _mode):
            return {"result": Result({"trials": 0}, []),
                    "decoder": {"decoded": np.zeros(2048, np.uint8), "iterations": 1},
                    "detector": {"extrinsic": np.zeros(2048)},
                    "exclusive_stages": {"tf": .01, "ldpc": .01},
                    "decision_ready_at": producer.time.perf_counter()}

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for subdir in ("raw", "checkpoints", "decisions"):
                (root / subdir).mkdir()
            (root / "attempts.jsonl").touch()
            (root / "ledger.jsonl").touch()
            stem = "s650_f0000"
            input_row = {"observation_id": stem, "observation_sha256": "synthetic",
                         "observation_hash": "synthetic-hash", "stream_ids": {}}
            bound = {"evidence": SimpleNamespace(save_artifact=evidence.save_artifact),
                     "native": SimpleNamespace(receive=native_receive),
                     "branch": branch_stub, "kernel": object(), "system": object(),
                     "code": object(), "H": H,
                     "extract_info": lambda _code, _bits: np.zeros(1024, np.uint8),
                     "previous_f0": {stem: {"baseline_syndrome_weight": 1}}}
            observation = {"y": np.zeros(1024, complex),
                           "pilot": np.ones(1024, complex), "sigma2": .1}
            with patch.object(producer, "_input", return_value=observation):
                prefix = producer._prefix(root, SimpleNamespace(), bound, input_row,
                                          "F0", 1, arrays)
            branch = producer._branch(root, bound, input_row, prefix, "F0_LOCAL", 2)

            def load(relative: str, expected: str) -> dict:
                path = root / relative
                self.assertEqual(reader.stage_a.sha256(path), expected)
                return evidence.load_artifact(path)[0]

            pre_row = prefix["record"]
            branch_row = branch["record"]
            pre_raw = load(pre_row["raw_path"], pre_row["raw_sha256"])
            branch_raw = load(branch_row["raw_path"], branch_row["raw_sha256"])
            for record, raw, expected_weight in ((pre_row, pre_raw, 1),
                                                 (branch_row, branch_raw, 0)):
                decision = json.loads((root / record["decision_path"]).read_text())
                bits, info, weight = reader._bits(raw, decision, H, free)
                self.assertEqual(weight, expected_weight)
                self.assertEqual(bits.shape, (2048,))
                self.assertEqual(info.shape, (1024,))
                for cp in record["checkpoints"]:
                    parsed = reader._checkpoint(load, cp, H, free,
                        np.zeros(1024, np.uint8), clock_key="durable_seconds",
                        coded=np.zeros(2048, np.uint8))
                    self.assertEqual(parsed["round"], cp["round"])
                    self.assertEqual(parsed["syndrome_weight"], cp["syndrome_weight"])
            self.assertEqual(pre_raw["observation_hash"], input_row["observation_hash"])
            self.assertEqual(branch_raw["stream_ids"], input_row["stream_ids"])


if __name__ == "__main__":
    unittest.main()
