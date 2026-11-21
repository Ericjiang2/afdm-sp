"""Select on a complete, identity-validated development run and freeze confirmation."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from evidence import artifact_sha256, source_hashes, validate_run, write_json_atomic


ROOT = Path(__file__).resolve().parents[1]


def deadline_error(record, deadline):
    if isinstance(deadline, bool) or not isinstance(deadline, (int, float)) or not math.isfinite(deadline) or deadline < 0:
        raise ValueError("deadline must be finite and nonnegative")
    timeline = record.get("timeline", [])
    if not isinstance(timeline, list):
        raise ValueError("timeline must be a list")
    eligible = []
    last = -1.0
    for event in timeline:
        elapsed = event.get("elapsed") if isinstance(event, dict) else None
        errors = event.get("info_errors") if isinstance(event, dict) else None
        if (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
                or not math.isfinite(elapsed) or elapsed < last or elapsed < 0
                or type(errors) is not int or errors < 0):
            raise ValueError("invalid decision timeline")
        last = elapsed
        if elapsed <= deadline:
            eligible.append(event)
    if eligible:
        return int(eligible[-1]["info_errors"] > 0)
    seconds = record.get("seconds")
    if seconds is not None and (isinstance(seconds, bool) or not isinstance(seconds, (int, float))
                                or not math.isfinite(seconds) or seconds < 0):
        raise ValueError("complete time must be finite and nonnegative")
    if record.get("status") != "ok":
        return 1
    if seconds is None:
        raise ValueError("successful record lacks complete time")
    return int(record["info_errors"] > 0) if seconds <= deadline else 1


def create_lock(records, manifest, protocol, catalog, development_dir):
    reference = [record["seconds"] for record in records
                 if record["arm"] == protocol["reference_runtime_arm"]]
    if not reference:
        raise ValueError("reference arm has no complete attempts")
    reference_seconds = float(np.median(reference))
    if not math.isfinite(reference_seconds) or reference_seconds <= 0:
        raise ValueError("reference median time must be finite and positive")
    deadline = reference_seconds * protocol["primary_deadline_multiplier"]
    families = sorted({value["family"] for value in catalog.values()} - {"ablation"})
    scores = {}
    for ident in catalog:
        rows = [record for record in records if record["arm"] == ident]
        complete_costs = [record["seconds"] for record in rows]
        scores[ident] = (
            float(np.mean([deadline_error(record, deadline) for record in rows])),
            float(np.median(complete_costs)),
        )
    selected = {}
    for family in families:
        identifiers = [ident for ident in catalog if catalog[ident]["family"] == family]
        selected[family] = min(identifiers, key=lambda ident: (*scores[ident], ident))
    classical = [ident for family, ident in selected.items() if family != "proposed"]
    cell_info = []
    for cell in protocol["development_cells"]:
        risks = {
            ident: float(np.mean([deadline_error(record, deadline) for record in records
                                  if record["cell"] == cell["id"] and record["arm"] == ident]))
            for ident in classical
        }
        best = min(risks, key=lambda ident: (risks[ident], scores[ident][1], ident))
        cell_info.append(dict(**cell, baseline=best, development_baseline_fer=risks[best]))
    chosen = []
    for target in (0.20, 0.05):
        choices = [cell for cell in cell_info if cell["id"] not in {item["id"] for item in chosen}]
        chosen.append(min(choices, key=lambda cell: (abs(cell["development_baseline_fer"] - target), cell["id"])))
    if not any(0.02 <= cell["development_baseline_fer"] <= 0.4 for cell in chosen):
        raise ValueError("development did not locate a useful transition; register an expanded grid")
    serializable_scores = {
        ident: {"deadline_fer": value[0],
                "median_complete_seconds": None if not math.isfinite(value[1]) else value[1]}
        for ident, value in scores.items()
    }
    return {
        "version": protocol["version"],
        "source_hashes": manifest["source_hashes"],
        "environment": manifest["environment"],
        "development_manifest_sha256": artifact_sha256(development_dir / "manifest.json"),
        "development_ledger_sha256": artifact_sha256(development_dir / "ledger.jsonl"),
        "selected_by_family": selected,
        "configurations": list(selected.values()) + protocol["ablations"],
        "cells": chosen,
        "frames_per_cell": protocol["confirmation_frames_per_cell"],
        "reference_seconds": reference_seconds,
        "primary_deadline": deadline,
        "secondary_deadlines": [reference_seconds * value for value in protocol["secondary_deadline_multipliers"]],
        "primary_method": selected["proposed"],
        "primary_baseline_by_cell": {str(cell["id"]): cell["baseline"] for cell in chosen},
        "selection_scores": serializable_scores,
        "statistical_contract": protocol["minimum_evidence"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    protocol = json.loads((ROOT / "protocol" / "protocol.json").read_text())
    catalog = json.loads((ROOT / "protocol" / "configurations.json").read_text())
    checked = validate_run(args.development, require_complete=True)
    manifest = checked["manifest"]
    if manifest["phase"] != "development" or manifest["source_hashes"] != source_hashes(ROOT):
        raise ValueError("development source identity differs from current frozen sources")
    if (manifest["cells"] != protocol["development_cells"]
            or manifest["configurations"] != catalog
            or manifest["frames"] != protocol["development_frames_per_cell"]):
        raise ValueError("development registration differs from the frozen protocol")
    lock = create_lock(checked["records"], manifest, protocol, catalog, args.development)
    write_json_atomic(args.out, lock)
    print("SEALED", args.out, "primary deadline", lock["primary_deadline"], "seconds")


if __name__ == "__main__":
    main()
