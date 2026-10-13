#!/usr/bin/env python3
"""Recount one completed stage without pooling adaptive stages as independent data."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from compact import attach_source, directory_bytes, load_plan, validate_run
from select_stage import arm_stats, choose_ranked, deadline_error, rescue_counts


def summarize(run_dir, source, gate_path=None):
    checked = validate_run(run_dir, source, require_complete=True)
    plan = load_plan()
    manifest, index = checked["manifest"], checked["index"]
    stage, cells, arms, frames = (manifest[key] for key in
                                 ("stage", "cells", "arms", "absolute_frames"))
    if stage == 1:
        from select_stage import build_gate

        gate = build_gate(run_dir, source)
        deadlines = gate["deadlines_stage1_seconds"]
        gate_ref = None
    else:
        gate_file = Path(gate_path or manifest["selection_gate_path"])
        evidence = attach_source(source)
        if evidence.artifact_sha256(gate_file) != manifest["selection_gate_sha256"]:
            raise ValueError("Stage 2 gate differs")
        gate = json.loads(gate_file.read_text())
        deadlines = gate["deadlines_stage1_seconds"]
        gate_ref = str(gate_file.resolve())
    stats = arm_stats(index, cells, frames, arms, deadlines)
    anchor = plan["stage1_deadline_reference"] if stage == 1 else gate["selected_i1_anchor"]
    secondary = {}
    for cell in cells:
        cid = str(cell["id"])
        ref = statistics.median(index[(cell["id"], frame, anchor)]["seconds"]
                                for frame in frames) if stage == 1 else deadlines[cid] / 1.5
        secondary[cid] = {arm: {str(multiplier): sum(deadline_error(
            index[(cell["id"], frame, arm)], multiplier * ref) for frame in frames)
            for multiplier in plan["deadline_multipliers"]} for arm in arms}
    summary = {"schema": "sp-afdm-staged-summary-v1", "stage": stage,
               "stage_independent_only": True,
               "run_identity_sha256": checked["run_identity_sha256"],
               "selection_gate": gate_ref,
               "cells": cells, "arms": arms, "frames_per_cell": len(frames),
               "absolute_frames": frames,
               "records": len(index),
               "deadlines_stage1_seconds": deadlines,
               "arm_stats": stats,
               "secondary_deadline_errors": secondary,
               "total_receiver_seconds": sum(row["seconds"] for row in checked["records"]),
               "total_generation_seconds_per_paired_frame": sum(
                   index[(cell["id"], frame, anchor)]["generation_seconds"]
                   for cell in cells for frame in frames),
               "total_scoring_storage_seconds": sum(row["scoring_storage_seconds"]
                                                    for row in checked["records"]),
               "total_bytes": directory_bytes(run_dir),
               "heavy_bytes": sum(path.stat().st_size for path in (Path(run_dir) / "heavy").glob("*")
                                  if path.is_file()),
               "numerical_failures": [{key: row[key] for key in ("cell", "absolute_frame", "arm", "seconds")}
                                      for row in checked["records"] if row["status"] != "ok"],
               "channel_nmse": {arm: {str(cell["id"]): [index[(cell["id"], frame, arm)]["channel_nmse"]
                                                      for frame in frames]
                                     for cell in cells} for arm in arms},
               "memory_scope": "shared-process per-call RSS/HWM snapshots; not isolated receiver peaks"}
    if stage == 1:
        summary["selection_gate_preview"] = {key: gate[key] for key in
            ("decision", "reason", "selected_proposed", "selected_i1_anchor",
             "family_leaders", "best_ranked_external",
             "eliminated", "cell_informativeness", "prospective_external_rivals",
             "prospective_stage2_calls")}
    else:
        proposed = gate["selected_proposed"]
        if not gate["prospective_external_rivals"]:
            summary["provisional_signal"] = {"heuristic_met": False,
                "reason": "no surviving external family; no external comparison estimable",
                "scope": "exploratory heuristic; not significance, equivalence or confirmation"}
            return summary
        external = choose_ranked(stats, gate["prospective_external_rivals"], cells)
        per_cell = {}
        for cell in cells:
            c = [cell]
            rescues, harms = rescue_counts(stats, proposed, external, c)
            per_cell[str(cell["id"])] = {"rescues": rescues, "harms": harms,
                                        "net_rescues": rescues - harms,
                                        "proposed_median_seconds": stats[proposed][str(cell["id"])]["median_complete_seconds"],
                                        "external_median_seconds": stats[external][str(cell["id"])]["median_complete_seconds"]}
        costs = [value["proposed_median_seconds"] / value["external_median_seconds"]
                 for value in per_cell.values()]
        nets = [value["net_rescues"] for value in per_cell.values()]
        first_signal = bool(nets and max(nets) >= 4 and all(value >= -2 for value in nets)
                            and all(ratio <= 1.2 for ratio in costs))
        cheaper_signal = all(ratio <= .8 for ratio in costs) and all(
            stats[proposed][str(cell["id"])]["deadline_errors"]
            <= stats[external][str(cell["id"])]["deadline_errors"] + 1 for cell in cells)
        i1_guard = all(stats[proposed][str(cell["id"])]["deadline_errors"]
                       <= stats[gate["selected_i1_anchor"]][str(cell["id"])]["deadline_errors"] + 2
                       for cell in cells)
        summary["provisional_signal"] = {"selected_proposed": proposed,
                                         "strongest_external": external,
                                         "per_cell": per_cell,
                                         "four_net_rescues_with_cost": first_signal,
                                         "lower_cost_with_at_most_one_extra_error": cheaper_signal,
                                         "selected_i1_guard": i1_guard,
                                         "heuristic_met": (first_signal or cheaper_signal) and i1_guard,
                                         "scope": "exploratory heuristic; not significance, equivalence or confirmation"}
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--gate", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    result = summarize(args.run, args.source, args.gate)
    evidence = attach_source(args.source)
    if args.out.exists() and json.loads(args.out.read_text()) != result:
        raise ValueError("existing summary differs from fresh recount")
    evidence.write_json_atomic(args.out, result)
    print(json.dumps({key: result[key] for key in ("stage", "records", "total_receiver_seconds",
                  "total_bytes", "numerical_failures")}, indent=2))


if __name__ == "__main__":
    main()
