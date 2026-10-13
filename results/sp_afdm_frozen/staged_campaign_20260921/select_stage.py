#!/usr/bin/env python3
"""Apply the prospectively frozen Stage-1 gate to complete compact evidence."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from compact import attach_source, load_plan, validate_run


FAMILIES = {
    "N_ep_2_r2": "native_ep", "N_ep_8_r2": "native_ep",
    "N_gamp_g1_i30_r2": "native_gamp", "N_gamp_g4_i40_r3": "native_gamp",
    "S_SBL1": "shared_SBL", "N_bilinear_8_r1": "native_bilinear",
    "N_bilinear_8_r2": "native_bilinear",
}
GAMMA_PREFERENCE = {"ABL_mean": 0, "ABL_scalar": 1, "P_M16_I8": 2, "P_M24_I20": 3}


def deadline_error(row, deadline):
    if row["status"] != "ok":
        return 1
    ready = [event for event in row["timeline"] if event["elapsed"] <= deadline]
    if ready:
        return int(ready[-1]["info_errors"] != 0)
    return int(not (not row["timeline"] and row["seconds"] <= deadline
                    and row["info_errors"] == 0))


def unrestricted_error(row):
    return int(row["status"] != "ok" or row["info_errors"] != 0)


def arm_stats(index, cells, frames, arms, deadlines):
    result = {}
    for arm in arms:
        per_cell = {}
        for cell in cells:
            cid = cell["id"]
            records = [index[(cid, frame, arm)] for frame in frames]
            per_cell[str(cid)] = {
                "deadline_vector": [deadline_error(row, deadlines[str(cid)]) for row in records],
                "unrestricted_vector": [unrestricted_error(row) for row in records],
                "deadline_errors": sum(deadline_error(row, deadlines[str(cid)]) for row in records),
                "unrestricted_errors": sum(unrestricted_error(row) for row in records),
                "info_bit_errors": sum(row["info_errors"] if row["info_errors"] is not None
                                       else 1024 for row in records),
                "missing_bit_frames_ranked_worst_case": sum(row["info_errors"] is None for row in records),
                "complete_seconds": [row["seconds"] for row in records],
                "median_complete_seconds": statistics.median(row["seconds"] for row in records),
            }
        result[arm] = per_cell
    return result


def rank_tuple(stats, arm, cells):
    values = [stats[arm][str(cell["id"])] for cell in cells]
    return (sum(value["deadline_errors"] for value in values),
            sum(value["unrestricted_errors"] for value in values),
            sum(value["info_bit_errors"] for value in values),
            statistics.median(second for value in values for second in value["complete_seconds"]), arm)


def choose_ranked(stats, arms, cells, *, gamma_tie=False):
    ranked = sorted(arms, key=lambda arm: rank_tuple(stats, arm, cells))
    best = ranked[0]
    if not gamma_tie:
        return best
    first = rank_tuple(stats, best, cells)
    tied = [arm for arm in ranked if rank_tuple(stats, arm, cells)[:3] == first[:3]
            and max(rank_tuple(stats, arm, cells)[3], first[3])
            <= 1.05 * min(rank_tuple(stats, arm, cells)[3], first[3])]
    return min(tied, key=lambda arm: (GAMMA_PREFERENCE[arm], rank_tuple(stats, arm, cells)))


def rescue_counts(stats, better, worse, cells):
    rescues = harms = 0
    for cell in cells:
        b = stats[better][str(cell["id"])]["deadline_vector"]
        w = stats[worse][str(cell["id"])]["deadline_vector"]
        rescues += sum(x == 0 and y == 1 for x, y in zip(b, w))
        harms += sum(x == 1 and y == 0 for x, y in zip(b, w))
    return rescues, harms


def dominance_reason(stats, better, worse, cells):
    b, w = ([stats[arm][str(cell["id"])] for cell in cells] for arm in (better, worse))
    b, w = list(b), list(w)
    no_worse = all(x[field] <= y[field] for x, y in zip(b, w)
                   for field in ("deadline_errors", "unrestricted_errors", "info_bit_errors"))
    costs80 = all(x["median_complete_seconds"] <= .8 * y["median_complete_seconds"]
                  for x, y in zip(b, w))
    rescues, harms = rescue_counts(stats, better, worse, cells)
    if no_worse and costs80 and rescues - harms >= 2:
        return f"observed_clear_dominance_by:{better};net_rescues={rescues-harms}"
    identical = all(x["deadline_vector"] == y["deadline_vector"]
                    and x["unrestricted_vector"] == y["unrestricted_vector"]
                    and x["info_bit_errors"] <= y["info_bit_errors"] for x, y in zip(b, w))
    costs75 = all(x["median_complete_seconds"] <= .75 * y["median_complete_seconds"]
                  for x, y in zip(b, w))
    if identical and costs75:
        return f"observed_cost_only_duplicate_of:{better}"
    return None


def build_gate(stage1_dir, source):
    plan = load_plan()
    checked = validate_run(stage1_dir, source, require_complete=True)
    manifest, index = checked["manifest"], checked["index"]
    if manifest["stage"] != 1:
        raise ValueError("selection must use complete Stage 1")
    cells, frames, arms = manifest["cells"], manifest["absolute_frames"], manifest["arms"]
    reference = plan["stage1_deadline_reference"]
    deadlines = {str(cell["id"]): 1.5 * statistics.median(
        index[(cell["id"], frame, reference)]["seconds"] for frame in frames) for cell in cells}
    stats = arm_stats(index, cells, frames, arms, deadlines)
    anchor = choose_ranked(stats, plan["stage2_anchor_candidates"], cells)
    proposed = choose_ranked(stats, plan["proposed_candidates"], cells, gamma_tie=True)
    leader = {family: choose_ranked(stats, [arm for arm in arms if FAMILIES.get(arm) == family], cells)
              for family in plan["external_families"]}
    external_sorted = sorted(leader.values(), key=lambda arm: rank_tuple(stats, arm, cells))
    best_ranked_before_exclusion = external_sorted[0]
    eliminated = {}
    for arm in arms:
        if arm == anchor:
            continue
        for competitor in arms:
            if competitor == arm:
                continue
            reason = dominance_reason(stats, competitor, arm, cells)
            if reason:
                eliminated[arm] = reason
                break
    for arm in arms:
        family = FAMILIES.get(arm)
        if family and arm != leader[family] and arm not in eliminated:
            eliminated[arm] = f"family_budget_collapse_to:{leader[family]}"
        if arm in plan["proposed_candidates"] and arm != proposed and arm not in eliminated:
            eliminated[arm] = f"Gamma_budget_selection_to:{proposed}"
    selected_p_elimination = [dominance_reason(stats, arm, proposed, cells)
                              for arm in [anchor, *external_sorted]]
    proposed_dominated = next((reason for reason in selected_p_elimination if reason), None)
    survivors = [arm for arm in external_sorted if arm not in eliminated]
    best_external = survivors[0] if survivors else None
    informative = []
    cell_scores = {}
    for cell in cells:
        cid = str(cell["id"])
        p = stats[proposed][cid]["deadline_vector"]
        e = stats[best_external][cid]["deadline_vector"] if best_external else []
        disagreement = sum(x != y for x, y in zip(p, e)) if best_external else 0
        ext_unrestricted = (stats[best_external][cid]["unrestricted_errors"]
                            if best_external else None)
        cell_scores[cid] = {"paired_deadline_disagreement": disagreement,
                            "best_external_unrestricted_errors": ext_unrestricted,
                            "informative": bool(best_external and
                                (disagreement > 0 or 1 <= ext_unrestricted <= 9))}
        if cell_scores[cid]["informative"]:
            informative.append(cell)
    informative.sort(key=lambda cell: (-cell_scores[str(cell["id"])]["paired_deadline_disagreement"],
                                       abs(cell_scores[str(cell["id"])]["best_external_unrestricted_errors"] / 10 - .3),
                                       cell["id"]))
    selected_external = survivors[:2]
    if len(survivors) >= 3:
        third = survivors[2]
        unique_rescue = any(
            stats[third][str(cell["id"])]["deadline_vector"][j] == 0
            and stats[proposed][str(cell["id"])]["deadline_vector"][j] == 1
            and all(stats[other][str(cell["id"])]["deadline_vector"][j] == 1
                    for other in selected_external)
            for cell in cells for j in range(len(frames)))
        if unique_rescue:
            selected_external.append(third)
    prospective_arms = [anchor, proposed, *selected_external]
    prospective_cells = informative[:2]
    if proposed_dominated:
        decision, reason = "stop", f"selected_proposed_{proposed_dominated}"
    elif not survivors:
        decision, reason = "stop", "no_nondominated_external_family"
    elif not prospective_cells:
        decision, reason = "stop", "uninformative_regime_against_best_ranked_external"
    else:
        decision, reason = "advance", "unresolved_proposed_and_informative_regime"
    evidence = attach_source(source)
    return {
        "schema": "sp-afdm-stage1-gate-v1", "decision": decision, "reason": reason,
        "source_run_dir": str(Path(stage1_dir).resolve()),
        "stage1_run_identity_sha256": checked["run_identity_sha256"],
        "stage1_ledger_sha256": evidence.artifact_sha256(Path(stage1_dir) / "ledger.jsonl"),
        "stage1_manifest_sha256": evidence.artifact_sha256(Path(stage1_dir) / "manifest.json"),
        "stage1_channel_seeds": sorted({value[0]["seed"]["channel_seed"]
                                        for value in checked["frame_cache"].values()}),
        "deadlines_stage1_seconds": deadlines, "arm_stats": stats,
        "ranking": {arm: list(rank_tuple(stats, arm, cells)) for arm in arms},
        "selected_proposed": proposed, "selected_i1_anchor": anchor,
        "stage1_deadline_reference": reference, "family_leaders": leader,
        "best_ranked_external": best_external,
        "best_ranked_external_before_exclusion": best_ranked_before_exclusion,
        "eliminated": eliminated,
        "cell_informativeness": cell_scores,
        "prospective_external_rivals": selected_external,
        "prospective_stage2_cells": prospective_cells,
        "prospective_stage2_arms": prospective_arms,
        "prospective_stage2_calls": len(prospective_arms) * len(prospective_cells) * 32,
        "stage2_cells": prospective_cells if decision == "advance" else [],
        "stage2_arms": prospective_arms if decision == "advance" else [],
        "stage1_only_no_pooled_stage2_inference": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--stage1", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    gate = build_gate(args.stage1, args.source)
    evidence = attach_source(args.source)
    if args.out.exists():
        if json.loads(args.out.read_text()) != gate:
            raise ValueError("existing selection gate differs from validated Stage 1")
    else:
        evidence.write_json_atomic(args.out, gate)
    print(json.dumps({key: gate[key] for key in ("decision", "reason", "selected_proposed",
                  "stage2_cells", "stage2_arms", "prospective_stage2_calls")}, indent=2))


if __name__ == "__main__":
    main()
