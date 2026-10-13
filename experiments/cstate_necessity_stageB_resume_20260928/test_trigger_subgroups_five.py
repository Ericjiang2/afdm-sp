"""Synthetic saved-table five-policy subgroup contract; no raw or truth reads."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile

import pytest

from summarize_trigger_subgroups_five import EXCLUDED, POLICIES, summarize


def _fixture(root: Path) -> None:
    root.mkdir()
    outcomes, components, deadlines = [], [], []
    arms = {}
    for policy in POLICIES:
        failures = 0
        for frame in range(1024):
            stem = f"s650_f{frame:04d}"
            triggered = frame < 40 if policy != "F2E" else frame < 2
            wrong = policy == "B" and frame in (0, 1)
            failures += int(wrong)
            common = {"campaign": "F2", "frame": frame,
                      "observation_id": stem, "arm_or_policy": policy}
            outcomes.append({**common, "info_correct": not wrong,
                             "coded_correct": not wrong, "coded_errors": int(wrong),
                             "syndrome_weight": int(wrong),
                             "valid_but_wrong": False, "triggered": triggered})
            branch = .2 if triggered and policy in ("B", "F0_LOCAL", "F2T") else 0.0
            components.append({**common, "complete_latency_seconds": .4 + branch,
                               "branch_complete_seconds": branch})
            for deadline in (.5, 1.0):
                ready = deadline == 1.0 or branch == 0
                deadlines.append({**common, "deadline_seconds": deadline,
                                  "ready": ready, "correct": ready and not wrong,
                                  "round": 2 if branch else 1})
        arms[policy] = {"n": 1024, "information_failures": failures,
                        "coded_bit_errors": failures,
                        "triggered_prefix_nonzero": 2 if policy == "F2E" else 40}
    (root / "report.json").write_text(json.dumps({
        "schema": "method-closure-five-policy-analysis/1", "campaign": "f2",
        "status": "pass", "git_attestation_verified_before_truth": True,
        "population_numerical_failures": 0, "summary": {"arms": arms},
        "excluded_policies": EXCLUDED,
        "excluded_policy_outcomes": {name: "unavailable" for name in EXCLUDED}}))
    for name, rows in (("frame_outcomes.csv", outcomes),
                       ("component_timing.csv", components),
                       ("deadline_decisions.csv", deadlines)):
        with (root / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def test_only_original_40_has_subgroup_and_exclusions_are_unavailable() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _fixture(root / "analysis")
        result = summarize(root / "analysis", root / "subgroups.json")
        assert set(result["groups"]) == {"original_F0_trigger_40"}
        group = result["groups"]["original_F0_trigger_40"]
        assert group["n"] == 40
        assert set(group["policies"]) == {"B", "F0_LOCAL", "F2T"}
        assert group["policies"]["B"]["information_failures"] == 2
        assert result["F2E_trigger_comparison"] == {
            name: "unavailable_not_admitted_frozen_interface" for name in EXCLUDED}
        report_path = root / "analysis/report.json"
        report = json.loads(report_path.read_text())
        report["summary"]["arms"]["F2E_LOCAL"] = {"n": 1024}
        report_path.write_text(json.dumps(report))
        with pytest.raises(ValueError, match="five-policy"):
            summarize(root / "analysis", root / "invalid.json")
