"""Focused contract tests; no scientific receiver calls."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import compact
import run_stage
import select_stage


SOURCE = Path(os.environ.get("STAGED_SOURCE", Path(__file__).parents[3] /
                             "experiments" / "sp_afdm_frozen_20260920"))


class CompactContract(unittest.TestCase):
    def test_packed_bits_recount_and_identity_tamper(self):
        bits = np.tile(np.array([0, 1, 1, 0, 1], dtype=np.uint8), 205)[:1024]
        packed = compact.pack_bits(bits)
        np.testing.assert_array_equal(compact.unpack_bits(packed), bits)
        broken = {"length": packed["length"] - 2, "bytes": packed["bytes"].copy()}
        with self.assertRaises(ValueError):
            compact.unpack_bits(broken)
        with tempfile.TemporaryDirectory() as folder:
            evidence = compact.attach_source(SOURCE)
            path = Path(folder) / "one.npz"
            identity = compact.artifact_identity("a" * 64, "arm", 1, 100000, "I1_BP12_r0")
            evidence.save_artifact(path, {"decoded": packed}, identity)
            payload, _ = evidence.load_artifact(path, identity)
            np.testing.assert_array_equal(compact.unpack_bits(payload["decoded"]), bits)
            with self.assertRaises(ValueError):
                evidence.load_artifact(path, dict(identity, absolute_frame=100001))

    def test_seed_independence_and_audit_coordinates(self):
        evidence = compact.attach_source(SOURCE)
        descriptor1 = evidence.frame_seed_descriptor(evidence.seed_contract(1), 1, 100000)
        descriptor2 = evidence.frame_seed_descriptor(evidence.seed_contract(1), 3, 100000)
        descriptor3 = evidence.frame_seed_descriptor(evidence.seed_contract(1), 1, 200000)
        self.assertEqual(len({descriptor1["channel_seed"], descriptor2["channel_seed"],
                              descriptor3["channel_seed"]}), 3)
        plan = compact.load_plan()
        self.assertEqual((plan["stage1"]["audit_absolute_frame"],
                          plan["stage2"]["audit_absolute_frame"]), (100000, 200000))

    def test_deadline_uses_last_completed_decision(self):
        row = {"status": "ok", "timeline": [
            {"elapsed": .2, "info_errors": 0},
            {"elapsed": .4, "info_errors": 1},
            {"elapsed": .8, "info_errors": 0}]}
        self.assertEqual(select_stage.deadline_error(row, .3), 0)
        self.assertEqual(select_stage.deadline_error(row, .5), 1)
        self.assertEqual(select_stage.deadline_error(row, .9), 0)
        self.assertEqual(select_stage.deadline_error(
            {"status": "ok", "timeline": [], "seconds": .4, "info_errors": 0}, .5), 0)
        self.assertEqual(select_stage.deadline_error(
            {"status": "ok", "timeline": [], "seconds": .6, "info_errors": 0}, .5), 1)

    def test_invalid_checkpoint_times_fail_closed(self):
        for timeline in (
            [{"elapsed": -.1, "info_errors": 0}],
            [{"elapsed": .4, "info_errors": 0}, {"elapsed": .3, "info_errors": 1}],
            [{"elapsed": .6, "info_errors": 0}],
        ):
            with self.assertRaises(ValueError):
                compact.validate_timeline(timeline, .5)

    def synthetic(self, *, dominate=False, informative=True, faster_i1=True):
        plan = compact.load_plan()
        arms = plan["stage1"]["arms"]
        cells = plan["stage1"]["cells"]
        frames = list(range(100000, 100010))
        index = {}
        for cell in cells:
            for j, frame in enumerate(frames):
                for arm in arms:
                    errors = 1 if j in (0, 1, 2) else 0
                    seconds = 1.0
                    if arm == "I1_BP12_r0":
                        seconds = 1.5
                    if arm == "I1_BP8_r1":
                        seconds = .7 if faster_i1 else 2.0
                    if arm == "ABL_mean":
                        seconds = 1.3
                        errors = 1 if j in (0, 1, 2, 3) else 0
                    if arm == "P_M16_I8":
                        errors = 1 if j in (0, 1) else 0
                    if arm == "N_ep_2_r2":
                        errors = 1 if j in (0, 1) else 0
                        seconds = .9
                    if dominate and arm == "N_ep_2_r2":
                        errors = 0
                        seconds = .4
                    index[(cell["id"], frame, arm)] = {
                        "cell": cell["id"], "absolute_frame": frame, "arm": arm,
                        "status": "ok", "seconds": seconds,
                        "info_errors": errors, "coded_errors": errors,
                        "timeline": [{"elapsed": seconds, "info_errors": errors}],
                    }
        checked = {"manifest": {"stage": 1, "cells": cells, "arms": arms,
                                "absolute_frames": frames},
                   "index": index, "run_identity_sha256": "r" * 64,
                   "frame_cache": {(cell["id"], frame): ({"seed": {"channel_seed":
                       cell["id"] * 100000 + frame}}, None, None, "hash")
                       for cell in cells for frame in frames}}
        return checked

    def gate(self, checked):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / "ledger.jsonl").write_text("synthetic\n")
            (run / "manifest.json").write_text("{}\n")
            with patch.object(select_stage, "validate_run", return_value=checked):
                return select_stage.build_gate(run, SOURCE)

    def test_dominated_stop_preserves_elimination_and_future_cost(self):
        gate = self.gate(self.synthetic(dominate=True))
        self.assertEqual(gate["decision"], "stop")
        self.assertIn("dominance", gate["reason"])
        self.assertIn("family_leaders", gate)
        self.assertIn("eliminated", gate)
        self.assertIn("prospective_stage2_calls", gate)

    def test_survive_best_i1_and_fresh_stage2_gate(self):
        gate = self.gate(self.synthetic(dominate=False, informative=True))
        self.assertEqual(gate["selected_i1_anchor"], "I1_BP8_r1")
        self.assertEqual(gate["stage1_deadline_reference"], "I1_BP12_r0")
        self.assertEqual(gate["decision"], "advance")
        self.assertEqual(gate["stage2_arms"][0], "I1_BP8_r1")
        self.assertEqual(gate["stage2_cells"], compact.load_plan()["stage1"]["cells"])
        self.assertEqual(len(gate["stage1_channel_seeds"]), 20)

    def test_no_surviving_external_is_explicit_stop(self):
        checked = self.synthetic()
        for (cell, frame, arm), row in checked["index"].items():
            if arm == "P_M16_I8":
                row["info_errors"] = 0
                row["timeline"][0]["info_errors"] = 0
                row["seconds"] = .2
        gate = self.gate(checked)
        self.assertEqual(gate["decision"], "stop")
        self.assertEqual(gate["reason"], "no_nondominated_external_family")
        self.assertIsNone(gate["best_ranked_external"])

    def test_stage2_external_is_ranked_on_stage2_only(self):
        cells = [{"id": 1}, {"id": 3}]
        def cell(errors, seconds):
            return {"deadline_errors": errors, "unrestricted_errors": errors,
                    "info_bit_errors": errors, "complete_seconds": [seconds] * 32,
                    "median_complete_seconds": seconds}
        stats = {"old_stage1_leader": {"1": cell(4, .5), "3": cell(4, .5)},
                 "new_stage2_leader": {"1": cell(2, .8), "3": cell(2, .8)}}
        self.assertEqual(select_stage.choose_ranked(stats, list(stats), cells), "new_stage2_leader")

    def test_orphan_preserves_heavy_and_warmup_append(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            heavy = out / "heavy"
            heavy.mkdir()
            marker = out / "compact.npz"
            arm = heavy / "c01_f100000_I1_BP12_r0.npz"
            error = heavy / "c01_f100000_I1_BP12_r0_exception.json"
            for path in (marker, arm, error):
                path.write_text(path.name)
            class Digest:
                @staticmethod
                def artifact_sha256(path):
                    import hashlib
                    return hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (marker, arm, error):
                receipt = run_stage.preserve_orphan(out, path, Digest)
                self.assertFalse(path.exists())
                self.assertTrue((out / receipt["preserved"]).exists())
            orphan_without_marker = heavy / "c01_f100001_I1_BP12_r0.npz"
            orphan_without_marker.write_text("heavy-only")
            receipt = run_stage.preserve_orphan(out, orphan_without_marker, Digest)
            self.assertTrue((out / receipt["preserved"]).exists())
            compact.append_jsonl(out / "warmups.jsonl", {"seconds": 1.0})
            compact.append_jsonl(out / "warmups.jsonl", {"seconds": 2.0})
            self.assertEqual(len((out / "warmups.jsonl").read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
