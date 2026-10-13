"""Synthetic saved-table contracts; no raw, truth, receiver, or decoder reads."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from summarize_trigger_subgroups import POLICIES, summarize


def _fixture(root: Path, *, f2e_triggers: tuple[int, ...]) -> None:
    root.mkdir()
    outcomes, components, deadlines = [], [], []
    report_arms = {}
    for policy in POLICIES:
        failures = 0
        for frame in range(1024):
            stem = f"s650_f{frame:04d}"
            f0 = frame < 40
            f2e = frame in f2e_triggers
            triggered = f2e if policy.startswith("F2E") else f0
            wrong = ((policy == "B" and frame in (0, 1)) or
                     (policy == "F0_LOCAL" and frame == 0) or
                     (policy == "F2E_LOCAL" and frame == 0 and f2e) or
                     (policy == "F2E_CSTATE" and frame == 1 and f2e))
            failures += wrong
            shared = {"campaign": "F2", "frame": frame,
                      "observation_id": stem, "arm_or_policy": policy}
            outcomes.append({**shared, "info_correct": not wrong,
                             "coded_correct": not wrong, "coded_errors": int(wrong),
                             "syndrome_weight": int(wrong),
                             "valid_but_wrong": False, "triggered": triggered})
            branch = .2 if triggered and policy not in ("F0", "F2E") else 0.0
            components.append({**shared, "complete_latency_seconds": .4 + branch,
                               "branch_complete_seconds": branch})
            for deadline in (.5, 1.0):
                ready = deadline == 1.0 or branch == 0
                deadlines.append({**shared, "deadline_seconds": deadline,
                                  "ready": ready, "correct": ready and not wrong,
                                  "round": 2 if branch else 1})
        report_arms[policy] = {"n": 1024, "information_failures": failures,
                               "coded_bit_errors": failures,
                               "triggered_prefix_nonzero": (
                                   len(f2e_triggers) if policy.startswith("F2E") else 40)}
    (root / "report.json").write_text(json.dumps({
        "schema": "method-closure-offline-analysis/1", "campaign": "f2",
        "status": "pass", "git_attestation_verified_before_truth": True,
        "population_numerical_failures": 0,
        "summary": {"arms": report_arms}}))
    for name, rows in (("frame_outcomes.csv", outcomes),
                       ("component_timing.csv", components),
                       ("deadline_decisions.csv", deadlines)):
        with (root / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


class TriggerSubgroupContracts(unittest.TestCase):
    def test_locked_40_and_f2e_matched_pairs_and_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            _fixture(base / "analysis", f2e_triggers=(0, 1))
            result = summarize(base / "analysis", base / "subgroups.json")
            original = result["groups"]["original_F0_trigger_40"]
            self.assertEqual(original["n"], 40)
            self.assertEqual(original["policies"]["B"]["information_failures"], 2)
            self.assertEqual(original["policies"]["B"]["coded_BER"], 2/(40*2048))
            self.assertAlmostEqual(
                original["policies"]["B"]["branch_complete_seconds"]["mean"], .2)
            self.assertEqual(original["policies"]["B"]["deadlines"]["0.5"],
                             {"n": 40, "correct": 0, "wrong_ready": 0, "missing": 40})
            pair = original["paired"]["B_vs_F2T"]["table"]
            self.assertEqual((pair["second_only_correct"], pair["first_only_correct"]),
                             (2, 0))
            f2e = result["groups"]["F2E_trigger"]
            self.assertEqual(f2e["n"], 2)
            pair = f2e["paired"]["F2E_LOCAL_vs_F2E_CSTATE"]["table"]
            self.assertEqual((pair["second_only_correct"], pair["first_only_correct"]),
                             (1, 1))

    def test_zero_f2e_trigger_and_wrong_id_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            _fixture(base / "analysis", f2e_triggers=())
            result = summarize(base / "analysis", base / "subgroups.json")
            empty = result["groups"]["F2E_trigger"]
            self.assertEqual(empty["n"], 0)
            self.assertIsNone(empty["policies"]["F2E_LOCAL"]["information_FER"])
            self.assertIsNone(empty["paired"]["F2E_LOCAL_vs_F2E_CSTATE"]["table"])
            report_path = base / "analysis/report.json"
            report = json.loads(report_path.read_text())
            report["summary"]["arms"]["F2E_LOCAL"]["triggered_prefix_nonzero"] = 1
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "primary report"):
                summarize(base / "analysis", base / "bad-trigger.json")
            report["summary"]["arms"]["F2E_LOCAL"]["triggered_prefix_nonzero"] = 0
            report_path.write_text(json.dumps(report))
            path = base / "analysis/frame_outcomes.csv"
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["observation_id"] = "s650_f0999"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "noncanonical"):
                summarize(base / "analysis", base / "new-subgroups.json")


if __name__ == "__main__":
    unittest.main()
