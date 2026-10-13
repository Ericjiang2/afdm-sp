#!/usr/bin/env python3
"""Synthetic-only tests for the I-01 development raw auditor."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "audit_i01_development", HERE / "audit-i01-development-v1.py")
audit_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_module)


def write_json(path, value):
    with Path(path).open("w") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)


def digest_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


class SyntheticBatch:
    """Small-array fixture with the real 18-identity one-block schema."""

    def __init__(self, root, block=0):
        self.root = Path(root)
        self.root.mkdir()
        self.block = block
        self.bindings = {
            "files": {key: digest_text(key) for key in audit_module.FILE_BINDINGS},
            "source_sha256": {
                "supplement_feedback_run.py": digest_text("synthetic runner source"),
                "supplement_baseline_run.py": digest_text("synthetic terminal source"),
            },
        }
        identities = sorted(
            (block, snr, arm) for snr in audit_module.SNRS for arm in audit_module.ARMS)
        contract = {
            "schema": "supplement-I01-development-batch-contract-v1",
            "campaign_id": "synthetic-campaign",
            "identities": [list(identity) for identity in identities],
            "bindings": self.bindings,
            "device": "cpu",
            "threads": 1,
            "start": block,
            "stop": block + 1,
            "max_full_calls": len(identities),
            "calls_reserved": {"F": len(identities), "T": 0, "E": 0},
            "deadline_unix": 9999999999.0,
            "max_output_bytes": 100000000,
            "estimated_output_bytes": 70000000,
            "code_sha256": {"G": digest_text("G"), "H": digest_text("parity H")},
            "versions": {"python": "synthetic", "numpy": "synthetic", "torch": "synthetic"},
            "command": ["synthetic-no-receiver"],
            "policy": "no overwrite, automatic retry, reclaim, replacement, or FER-based schedule selection",
        }
        contract["config_sha256"] = hashlib.sha256(json.dumps(
            contract, sort_keys=True, allow_nan=False).encode()).hexdigest()
        contract["ledger"] = "/synthetic/read-only-ledger"
        self.contract = contract
        write_json(self.root / "contract.json", contract)

        records = []
        for index, identity in enumerate(identities, 1):
            write_json(self.root / f"call-{index:05d}-started.json",
                       {"identity": list(identity), "attempt": index})
            record = self._record(identity, index)
            frame = self.root / f"frame-{index:05d}.json"
            write_json(frame, record)
            records.append({"identity": list(identity), "path": str(frame),
                            "sha256": audit_module.sha256(frame)})
        self.summary = {
            "status": "complete", "exitcode": 0,
            "calls_attempted": 18, "calls_completed": 18,
            "records": records, "failures": [], "missing_or_failed_identities": [],
            "config_sha256": contract["config_sha256"], "ledger": contract["ledger"],
        }
        write_json(self.root / "summary.json", self.summary)

    def _arrays(self):
        coded = np.array([0, 1, 0, 1, 1, 0, 1, 0], dtype=np.uint8)
        info = np.array([0, 1, 1, 0], dtype=np.uint8)
        x_hard = np.array([1+1j, -1-1j, 1-1j, -1+1j], dtype=np.complex64)
        return {
            "H": np.eye(4, dtype=np.complex64),
            "x_soft": x_hard.copy(), "gains": np.array([1+0j], np.complex64),
            "support": np.array([2], np.int64), "sigma2": np.array(.2, np.float32),
            "sigma2_terminal": np.array(.2, np.float32),
            "mu": x_hard.copy(), "var": np.ones(4, np.float64),
            "llr": np.ones(8, np.float32), "decoded": coded.copy(),
            "info_hat": info.copy(), "x_hard": x_hard,
            "y": np.arange(4, dtype=np.complex64),
            "pilot": np.ones(4, np.complex64),
            "constellation": np.array([1+1j, 1-1j, -1+1j, -1-1j], np.complex64),
            "sigma2_thermal": np.array(.2, np.float32),
            "info": info, "coded": coded,
        }

    def _record(self, identity, index):
        block, snr, arm = identity
        arrays = self._arrays()
        terminal_path = self.root / f"terminal-{index:05d}.npz"
        np.savez_compressed(terminal_path, **arrays)
        terminal = {
            "path": str(terminal_path), "bytes": terminal_path.stat().st_size,
            "uncompressed_bytes": sum(value.nbytes for value in arrays.values()),
            "sha256": audit_module.sha256(terminal_path),
            "md5": hashlib.md5(terminal_path.read_bytes()).hexdigest(),
            "fields": sorted(arrays),
            "truth_access": "info/coded for offline scoring only",
            "transfer_policy": "synthetic raw stays local",
        }
        data = np.sqrt(.5) * audit_module.qpsk_map(arrays["coded"])
        noise = np.zeros(4, np.complex64)
        inputs = {
            "H": audit_module.array_hash(np.eye(4, dtype=np.complex64)),
            "coded": audit_module.array_hash(arrays["coded"]),
            "data": audit_module.array_hash(data),
            "info": audit_module.array_hash(arrays["info"]),
            "noise": audit_module.array_hash(noise),
            "pilot": audit_module.array_hash(arrays["pilot"]),
            "y": audit_module.array_hash(arrays["y"]),
        }
        count = audit_module.BP_COUNTS[arm]
        feedback = arm in audit_module.FEEDBACK_ARMS
        oracle = arm in audit_module.ORACLE_ARMS
        record = {
            "schema": "supplement-I01-development-frame-v1",
            "campaign_id": "synthetic-campaign", "identity": list(identity),
            "config_sha256": self.contract["config_sha256"],
            "bindings": self.bindings, "input_hashes": inputs,
            "truth_labels": {key: {"sha256": inputs[key], "shape": [4]}
                             for key in ("H", "info", "coded", "data", "noise")},
            "truth_access_level": "true_symbols_oracle" if oracle else "none",
            "baseline_recipe": "B0-p2-s0.5", "baseline_eligible": True,
            "initial_estimator": {},
            "bp_schedule": {
                "outer_iterations": 10, "outer_bp_iterations": count,
                "final_bp_iterations": 20, "final_ldpc_maxiter": 50,
                "calls": [{"outer_iter": outer, "requested_iterations": count,
                           "executed_iterations": count, "edges": 1}
                          for outer in range(10)],
            },
            "actual_detector_consumers": ([{"stage": "detector_consume",
                                              "truth_access": "none"} for _ in range(10)]
                                            if feedback else []),
            "decoder_checkpoint_records": ([{"stage": "decoder", "iteration": 1,
                                                "control": audit_module.CONTROLS[arm],
                                                "truth_access": "none"}]
                                              if feedback else []),
            "actual_CE_feedback_consumers": ([{"stage": "CE_consume",
                                                 "truth_access": "none"} for _ in range(9)]
                                               if feedback else []),
            "actual_CE_consumers": [
                {"outer_iter": outer, "oracle_mean": oracle and outer == 2,
                 "H": {"array_sha256": digest_text(f"ce-{outer}"),
                       "dtype": "complex64", "shape": [4, 4]}}
                for outer in range(1, 10)],
            "actual_BP_graphs": ([{"stage": "outer_bp", "outer_iter": outer}
                                   for outer in range(10)] + [{"stage": "final_bp"}]),
            "diagnostic_consumption_records": ([{
                "tag": arm, "status": "consumed", "checkpoint": 1, "outer_iter": 2,
                "truth_access": "true_symbols_oracle", "legal_receiver_input": False,
                "variance": 0.0, "variance_used_by_CE": False,
                "supplied_sha256": audit_module.array_hash(data),
                "consumed_mean_sha256": audit_module.array_hash(data.astype(np.complex64)),
            }] if oracle else []),
            "capacity_trace": {}, "support_trace": [], "complete_chain_cost": {},
            "device": "cpu", "threads": 1, "failure": None, "retry_of": None,
            "terminal": terminal,
        }
        record.update(audit_module.recount_errors(arrays))
        return record

    def load_record(self, index):
        return json.loads((self.root / f"frame-{index:05d}.json").read_text())

    def save_record(self, index, record):
        path = self.root / f"frame-{index:05d}.json"
        write_json(path, record)
        self.summary["records"][index-1]["sha256"] = audit_module.sha256(path)
        write_json(self.root / "summary.json", self.summary)


class DevelopmentAuditSyntheticTests(unittest.TestCase):
    def test_accepts_exact_supplied_batch_and_multiple_batch_list(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = SyntheticBatch(base / "b000", 0)
            second = SyntheticBatch(base / "b001", 1)
            result = audit_module.audit([first.root, second.root], max_records=36)
            self.assertEqual(result["status"], "passed")
            self.assertEqual((result["F_audited"], result["batch_count"]), (36, 2))
            self.assertEqual((result["audit_F"], result["audit_T"]), (0, 0))
            self.assertIn("does not reconstruct actual CE matrices", result["scope"])

    def test_rejects_error_recount_and_terminal_hash_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = SyntheticBatch(Path(directory) / "batch")
            record = fixture.load_record(1)
            record["FER"] = 1 - record["FER"]
            fixture.save_record(1, record)
            with self.assertRaisesRegex(ValueError, "error recount"):
                audit_module.audit([fixture.root])

        with tempfile.TemporaryDirectory() as directory:
            fixture = SyntheticBatch(Path(directory) / "batch")
            record = fixture.load_record(1)
            record["terminal"]["sha256"] = "0" * 64
            fixture.save_record(1, record)
            with self.assertRaisesRegex(ValueError, "terminal SHA-256"):
                audit_module.audit([fixture.root])

    def test_rejects_unpaired_six_arm_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = SyntheticBatch(Path(directory) / "batch")
            record = fixture.load_record(2)
            changed = digest_text("different synthetic noise")
            record["input_hashes"]["noise"] = changed
            record["truth_labels"]["noise"]["sha256"] = changed
            fixture.save_record(2, record)
            with self.assertRaisesRegex(ValueError, "six arms are not paired"):
                audit_module.audit([fixture.root])

    def test_rejects_missing_failure_duplicate_and_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = SyntheticBatch(Path(directory) / "batch")
            fixture.summary["missing_or_failed_identities"] = [[0, 7, "I0"]]
            write_json(fixture.root / "summary.json", fixture.summary)
            with self.assertRaisesRegex(ValueError, "summary is incomplete"):
                audit_module.audit([fixture.root])

        with tempfile.TemporaryDirectory() as directory:
            fixture = SyntheticBatch(Path(directory) / "batch")
            fixture.summary["records"][1] = copy.deepcopy(fixture.summary["records"][0])
            write_json(fixture.root / "summary.json", fixture.summary)
            with self.assertRaisesRegex(ValueError, "duplicate or unexpected"):
                audit_module.audit([fixture.root])

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = SyntheticBatch(base / "first")
            second = SyntheticBatch(base / "second")
            with self.assertRaisesRegex(ValueError, "overlap"):
                audit_module.audit([first.root, second.root])

    def test_rejects_incomplete_execution_and_audit_structures(self):
        mutations = (
            (1, lambda row: row["actual_CE_consumers"].pop(), "nine actual CE"),
            (1, lambda row: row["actual_BP_graphs"].pop(), "eleven actual BP"),
            (1, lambda row: row["bp_schedule"]["calls"].pop(), "ten-call BP"),
            (2, lambda row: row["decoder_checkpoint_records"][0].update(iteration=4),
             "decoder checkpoint"),
        )
        for index, mutate, message in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                fixture = SyntheticBatch(Path(directory) / "batch")
                # Sorted identities put I1 in frame 2, while frame 1 is I0.
                record = fixture.load_record(index)
                mutate(record)
                fixture.save_record(index, record)
                with self.assertRaisesRegex(ValueError, message):
                    audit_module.audit([fixture.root])

    def test_finite_cap_and_source_binding_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = SyntheticBatch(Path(directory) / "batch")
            with self.assertRaisesRegex(ValueError, "finite record cap"):
                audit_module.audit([fixture.root], max_records=17)
            contract = json.loads((fixture.root / "contract.json").read_text())
            del contract["bindings"]["source_sha256"]["supplement_feedback_run.py"]
            # Rebind config so the test reaches source validation rather than digest validation.
            payload = {key: value for key, value in contract.items()
                       if key not in ("config_sha256", "ledger")}
            contract["config_sha256"] = hashlib.sha256(json.dumps(
                payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
            write_json(fixture.root / "contract.json", contract)
            with self.assertRaisesRegex(ValueError, "source manifest"):
                audit_module.audit([fixture.root])


if __name__ == "__main__":
    unittest.main()
