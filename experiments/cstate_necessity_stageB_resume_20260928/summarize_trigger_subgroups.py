"""Post-analysis F2 trigger-cohort tables from sealed primary CSVs only.

No raw, truth, receiver, or decoder input is opened here.  This is an additive
summary of the independently Git-gated primary analysis, never a new cohort.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from analyze_method_closure import stage_a

N = 1024
POLICIES = ("F0", "B", "F0_LOCAL", "F2T", "F2E", "F2E_LOCAL", "F2E_CSTATE")
GROUPS = {
    "original_F0_trigger_40": ("F0", ("B", "F0_LOCAL", "F2T")),
    "F2E_trigger": ("F2E", ("F2E_LOCAL", "F2E_CSTATE")),
}
DEADLINES = (0.5, 1.0)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bool(text: str) -> bool:
    if text not in ("True", "False"):
        raise ValueError(f"invalid saved Boolean: {text!r}")
    return text == "True"


def _number(text: str) -> float:
    value = float(text)
    if not np.isfinite(value) or value < 0:
        raise ValueError("nonfinite or negative saved metric")
    return value


def _index(path: Path, *, deadlines: bool = False) -> dict[tuple[str, str, float | None], dict[str, str]]:
    indexed: dict[tuple[str, str, float | None], dict[str, str]] = {}
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["campaign"] != "F2" or row["arm_or_policy"] not in POLICIES:
                raise ValueError(f"wrong F2 campaign/policy in {path.name}")
            frame = int(row["frame"])
            if not 0 <= frame < N or row["observation_id"] != f"s650_f{frame:04d}":
                raise ValueError(f"noncanonical 6.5-dB frame identity in {path.name}")
            deadline = float(row["deadline_seconds"]) if deadlines else None
            if deadlines and deadline not in DEADLINES:
                raise ValueError("unregistered deadline")
            key = row["arm_or_policy"], row["observation_id"], deadline
            if key in indexed:
                raise ValueError(f"duplicate saved policy/frame/deadline in {path.name}")
            indexed[key] = row
    expected = {(policy, f"s650_f{frame:04d}", deadline)
                for policy in POLICIES for frame in range(N)
                for deadline in (DEADLINES if deadlines else (None,))}
    if set(indexed) != expected:
        raise ValueError(f"incomplete fixed F2 policy denominator in {path.name}")
    return indexed


def _group(ids: list[str], policies: tuple[str, ...],
           outcomes: dict, components: dict, deadlines: dict) -> dict[str, Any]:
    size = len(ids)
    rows: dict[str, Any] = {}
    for policy in policies:
        selected = [outcomes[policy, stem, None] for stem in ids]
        costs = [components[policy, stem, None] for stem in ids]
        correct = [_bool(row["info_correct"]) for row in selected]
        coded_errors = [int(row["coded_errors"]) for row in selected]
        syndrome = [int(row["syndrome_weight"]) for row in selected]
        valid_wrong = [_bool(row["valid_but_wrong"]) for row in selected]
        if (any(not 0 <= errors <= 2048 for errors in coded_errors)
                or any(weight < 0 for weight in syndrome)
                or any(flag and (weight != 0 or ok)
                       for flag, weight, ok in zip(valid_wrong, syndrome, correct))):
            raise ValueError("invalid F2 saved correctness diagnostics")
        complete = [_number(row["complete_latency_seconds"]) for row in costs]
        branch = [_number(row["branch_complete_seconds"]) for row in costs]
        by_deadline = {}
        for deadline in DEADLINES:
            saved = [deadlines[policy, stem, deadline] for stem in ids]
            ready = [_bool(row["ready"]) for row in saved]
            right = [_bool(row["correct"]) for row in saved]
            if any(ok and not available for ok, available in zip(right, ready)):
                raise ValueError("correct deadline decision without a ready checkpoint")
            by_deadline[str(deadline)] = {
                "n": size, "correct": sum(right),
                "wrong_ready": sum(available and not ok
                                   for available, ok in zip(ready, right)),
                "missing": sum(not available for available in ready),
            }
        rows[policy] = {
            "n": size,
            "information_failures": sum(not value for value in correct),
            "information_FER": (sum(not value for value in correct) / size
                                if size else None),
            "coded_bit_errors": sum(coded_errors),
            "coded_BER": (sum(coded_errors) / (2048 * size) if size else None),
            "syndrome_nonzero": sum(weight != 0 for weight in syndrome),
            "valid_but_wrong": sum(valid_wrong),
            "complete_seconds": stage_a.distribution(complete, expected=size) if size else None,
            "branch_complete_seconds": stage_a.distribution(branch, expected=size) if size else None,
            "deadlines": by_deadline,
        }
    pairs = {}
    for first_index, first in enumerate(policies):
        for second in policies[first_index + 1:]:
            pair = (stage_a.paired_table(
                np.asarray([_bool(outcomes[first, stem, None]["info_correct"])
                            for stem in ids], dtype=bool),
                np.asarray([_bool(outcomes[second, stem, None]["info_correct"])
                            for stem in ids], dtype=bool)) if size else None)
            pairs[f"{first}_vs_{second}"] = {
                "first": first, "second": second,
                "direction": "second_only_correct rescues second versus first; first_only_correct harms second versus first",
                "table": pair,
            }
    return {"n": size, "observation_ids": ids, "policies": rows, "paired": pairs}


def summarize(analysis_root: Path, out: Path) -> dict[str, Any]:
    analysis_root = analysis_root.resolve()
    out = out.resolve()
    if (out.exists() or out.is_relative_to(analysis_root)
            or out.parent != analysis_root.parent):
        raise ValueError("new additive output must be a fresh sibling of primary analysis")
    filenames = ("report.json", "frame_outcomes.csv", "component_timing.csv",
                 "deadline_decisions.csv")
    hashes = {name: _sha(analysis_root / name) for name in filenames}
    report = json.loads((analysis_root / "report.json").read_text())
    if (report.get("schema") != "method-closure-offline-analysis/1"
            or report.get("campaign") != "f2" or report.get("status") != "pass"
            or report.get("git_attestation_verified_before_truth") is not True
            or report.get("population_numerical_failures") != 0
            or set(report.get("summary", {}).get("arms", {})) != set(POLICIES)):
        raise ValueError("complete seven-policy primary F2 analysis required")
    outcomes = _index(analysis_root / "frame_outcomes.csv")
    components = _index(analysis_root / "component_timing.csv")
    deadlines = _index(analysis_root / "deadline_decisions.csv", deadlines=True)
    for policy in POLICIES:
        rows = [outcomes[policy, f"s650_f{frame:04d}", None] for frame in range(N)]
        primary = report["summary"]["arms"][policy]
        if (primary["n"] != N or
                primary["information_failures"] != sum(not _bool(row["info_correct"])
                                                        for row in rows) or
                primary["coded_bit_errors"] != sum(int(row["coded_errors"])
                                                   for row in rows) or
                primary["triggered_prefix_nonzero"] != sum(_bool(row["triggered"])
                                                           for row in rows)):
            raise ValueError("primary report and saved per-frame outcomes differ")
    groups = {}
    for title, (parent, policies) in GROUPS.items():
        ids = [f"s650_f{frame:04d}" for frame in range(N)
               if _bool(outcomes[parent, f"s650_f{frame:04d}", None]["triggered"])]
        if parent == "F0" and len(ids) != 40:
            raise ValueError("original F0 trigger cohort is not the locked 40")
        selected = set(ids)
        for policy in policies:
            if any(_bool(outcomes[policy, f"s650_f{frame:04d}", None]["triggered"])
                   != (f"s650_f{frame:04d}" in selected) for frame in range(N)):
                raise ValueError("matched policy trigger identities differ")
        groups[title] = _group(ids, policies, outcomes, components, deadlines)
    result = {
        "schema": "method-closure-f2-trigger-subgroups/1", "status": "pass",
        "source": "saved primary F2 analysis CSV/report only; zero raw/truth/receiver reads",
        "input_sha256": hashes, "script_sha256": _sha(Path(__file__)),
        "groups": groups,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.analysis_root, args.out)


if __name__ == "__main__":
    main()
