"""Prospectively fixed Stage A allocation gate; no receiver calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from common import attach, plan
from verify import validate_run


def decision_error(row, deadline=None):
    if deadline is None:
        checkpoints = row["checkpoints"]
    else:
        checkpoints = [item for item in row["checkpoints"] if item["ready"] <= deadline]
    return int(not checkpoints or checkpoints[-1]["info_errors"] != 0)


def arm_stats(rows, arm, deadline):
    selected = sorted((r for r in rows if r["arm"] == arm), key=lambda r: r["frame"])
    times = np.asarray([r["seconds"] for r in selected], dtype=float)
    return {"arm": arm, "frames": [r["frame"] for r in selected],
            "deadline_errors": int(sum(decision_error(r, deadline) for r in selected)),
            "unrestricted_errors": int(sum(decision_error(r) for r in selected)),
            "median_seconds": float(np.median(times)),
            "p90_seconds": float(np.quantile(times, .9, method="linear")),
            "numerical_failures": int(sum(r["status"] != "ok" for r in selected))}


def build_gate(stage_a_run, source, baseline):
    root = Path(stage_a_run).resolve()
    checked = validate_run(root, source, baseline, require_complete=True)
    manifest = checked["manifest"]
    if manifest["stage"] != "A" or len(checked["records"]) != 70:
        raise ValueError("Stage A gate requires exactly 70 completed attempts")
    rows = checked["records"]
    by_key = {(r["frame"], r["arm"]): r for r in rows}
    reference = np.asarray([by_key[(frame, "EP2_SOFT_R2")]["seconds"]
                            for frame in range(12)], dtype=float)
    deadline = float(1.2 * np.median(reference))
    ep_ids = ("EP2_SOFT_R2", "EP2_MEAN_R2", "EP4_MEAN_R2")
    statistics = {arm: arm_stats(rows, arm, deadline) for arm in plan()["arms"]}
    selected_ep = min(ep_ids, key=lambda arm: (
        statistics[arm]["deadline_errors"], statistics[arm]["median_seconds"], arm))
    tf, ep = statistics["TF_J20_R2"], statistics[selected_ep]
    rescues = harms = 0
    for frame in range(12):
        tf_error = decision_error(by_key[(frame, "TF_J20_R2")], deadline)
        ep_error = decision_error(by_key[(frame, selected_ep)], deadline)
        rescues += int(ep_error == 1 and tf_error == 0)
        harms += int(ep_error == 0 and tf_error == 1)
    median_ratio = tf["median_seconds"] / ep["median_seconds"]
    p90_ratio = tf["p90_seconds"] / ep["p90_seconds"]
    informative = 2 <= ep["unrestricted_errors"] <= 10
    no_numerical_failure = all(row["status"] == "ok" for row in rows)
    accuracy_route = (rescues - harms >= 2 and median_ratio <= 1.2 and p90_ratio <= 1.5)
    speed_route = (tf["unrestricted_errors"] <= ep["unrestricted_errors"]
                   and median_ratio <= .75 and p90_ratio <= 1.0)
    advance = (informative and no_numerical_failure and harms <= 1
               and (accuracy_route or speed_route))
    evidence = attach(source, baseline)
    seeds = []
    for frame in range(12):
        from common import identity
        truth, _ = evidence.load_artifact(root / "frames" / f"s650_f{frame:03d}_truth.npz",
            identity(checked["run_identity_sha256"], "frame_truth", 650, frame))
        seeds.append(truth["seed"]["channel_seed"])
    return {"schema": "spafdm-native-joint-stage-a-gate/1",
            "stage_a_run": str(root), "stage_a_run_identity_sha256": checked["run_identity_sha256"],
            "stage_a_manifest_sha256": evidence.artifact_sha256(root / "manifest.json"),
            "stage_a_ledger_sha256": evidence.artifact_sha256(root / "ledger.jsonl"),
            "stage_a_channel_seeds": seeds, "source_commit": manifest["source_commit"],
            "source_hashes": manifest["source_hashes"], "baseline_source_hashes": manifest["baseline_source_hashes"],
            "deadline_seconds": deadline, "selected_ep": selected_ep,
            "statistics": statistics, "paired": {"frames": 12, "rescues": rescues,
                         "harms": harms, "net_rescues": rescues - harms},
            "median_ratio": median_ratio, "p90_ratio": p90_ratio,
            "informative": informative, "no_numerical_failure": no_numerical_failure,
            "accuracy_route": accuracy_route, "speed_route": speed_route,
            "decision": "advance" if advance else ("uninformative" if not informative else "stop")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("gate output already exists")
    value = build_gate(args.run, args.source, args.baseline)
    args.out.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"decision": value["decision"], "selected_ep": value["selected_ep"],
                      "deadline_seconds": value["deadline_seconds"], "paired": value["paired"]}))
