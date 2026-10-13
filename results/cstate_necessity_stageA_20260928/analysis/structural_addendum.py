"""Saved-geometry description for the 34 historical B-only rescues; no receiver calls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def geometry(paths: list[dict] | dict, target_delay: int, target_doppler: float) -> dict:
    if isinstance(paths, dict):
        delays = np.asarray(paths["delays"], dtype=np.int64)
        dopplers = np.asarray(paths["dopplers"], dtype=float)
        gains = np.asarray(paths["gains"])
    else:
        delays = np.asarray([path["delay"] for path in paths], dtype=np.int64)
        dopplers = np.asarray([path["doppler"] for path in paths], dtype=float)
        gains = None
    eligible = np.flatnonzero(delays == target_delay)
    if not len(eligible):
        return dict(delay_present=False, multiplicity=0, nearest_abs_delta_nu=None,
                    nearest_slot_1based=None, nearest_gain_magnitude_rank=None)
    index = int(eligible[np.argmin(np.abs(dopplers[eligible] - target_doppler))])
    gain_rank = None
    if gains is not None:
        gain_rank = 1 + int(np.count_nonzero(np.abs(gains) > abs(gains[index])))
    return dict(delay_present=True, multiplicity=int(len(eligible)),
                nearest_abs_delta_nu=float(abs(dopplers[index] - target_doppler)),
                nearest_slot_1based=index + 1,
                nearest_gain_magnitude_rank=gain_rank)


def main(args: argparse.Namespace) -> None:
    sys.path.insert(0, str(args.baseline / "src"))
    import evidence  # type: ignore[import-not-found]

    current = {(row["observation_id"], row["arm"]): row
               for row in rows(args.observed / "ledger.jsonl")}
    historical = {(row["observation_id"], row["arm"]): row
                  for row in rows(args.historical / "ledger.jsonl")}
    with args.frame_outcomes.open(newline="") as stream:
        rescues = [row for row in csv.DictReader(stream)
                   if row["original_B_only_rescue"] == "1"]
    if len(rescues) != 34:
        raise ValueError("historical rescue cohort is not 34")

    def raw(root: Path, row: dict) -> dict:
        path = root / row["raw_path"]
        if sha(path) != row["raw_sha256"]:
            raise ValueError(f"sealed raw hash differs: {path}")
        return evidence.load_artifact(path)[0]

    detail = []
    for frame in rescues:
        stem = frame["observation_id"]
        old_row = historical[(stem, "TF_CSTATE")]
        old = raw(args.historical, old_row)
        c = raw(args.observed, current[(stem, "C")])
        d = raw(args.observed, current[(stem, "D")])
        if old["input_sha256"] != c["input_sha256"] or c["input_sha256"] != d["input_sha256"]:
            raise ValueError("historical rescue input identity differs")
        edits = old["geometry_result"]["edits"] if old["geometry_result"] else []
        for edit in edits:
            target = edit["new"]
            delay, doppler = int(target["delay"]), float(target["doppler"])
            c_final = dict(delays=c["baseline_arrays"]["r1_delays"],
                           dopplers=c["baseline_arrays"]["r1_dopplers"],
                           gains=c["baseline_arrays"]["r1_gains"])
            d_final = (d["geometry_result"]["paths"]
                       if d["geometry_result"] is not None else
                       dict(delays=d["baseline_arrays"]["r1_delays"],
                            dopplers=d["baseline_arrays"]["r1_dopplers"],
                            gains=d["baseline_arrays"]["r1_gains"]))
            detail.append(dict(observation_id=stem, historical_edit_step=int(edit["step"]),
                historical_new_delay=delay, historical_new_doppler=doppler,
                historical_edit_decrease=float(edit["decrease"]),
                C_info_correct=frame["C_info_correct"] == "1",
                D_info_correct=frame["D_info_correct"] == "1",
                F1_initial=geometry(c["initial_geometry"], delay, doppler),
                F1_TF_entering=geometry(c["entering_geometry"], delay, doppler),
                F1_native_final=geometry(c_final, delay, doppler),
                F1_D_after_branch=geometry(d_final, delay, doppler),
                D_branch_applied=d["geometry_result"] is not None))

    report = dict(schema="cstate-necessity-stage-a-structural-addendum/1",
                  scope="read-only saved geometry, not a capture or causal success test",
                  original_rescue_frames=34, original_rescue_edits=len(detail),
                  original_rescue_frames_without_edits=34-len({x["observation_id"] for x in detail}),
                  APP_path_rank="NA_not_saved_as_a_path_metric",
                  pilot_gain_rank="descriptive rank of nearest same-delay saved slot by abs(gain); not a capture threshold",
                  nearest_delta_nu_rule="nearest saved slot at exactly the historical target delay; absent delay is NA",
                  source_seal_sha256=dict(current=sha(args.observed / "observed_seal.json"),
                                          historical=sha(args.historical / "observed_seal.json")),
                  details=detail)
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("observed", "historical", "baseline", "frame-outcomes", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(parser.parse_args())
