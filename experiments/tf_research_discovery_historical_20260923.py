"""Bridge frozen Part-B frame evidence into a separate discovery-pack namespace.

This reads existing CSV/JSONL evidence only. Earlier Part-B observations and the
fresh prospective population remain distinct; textual frame IDs are not joins.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


OLD_CAMPAIGN = "sp_afdm_pd1q_part_b_20260921"
FRESH_CAMPAIGN = "tf_cstate_prospective_20260923"
OLD_TRUTH_FIELDS = {
    "final_error", "info_errors", "coded_errors", "valid_wrong_word",
    "round1_info_errors", "round1_coded_errors", "round2_rescue", "round2_harm",
    "true_path_count", "true_distinct_delay_count", "missed_distinct_delay_count",
    "missed_distinct_delay_energy_fraction", "true_same_delay_multiplicity",
    "represented_same_delay_underfit", "truth_sha256",
}
EXPECTED = [f"s{snr}_f{frame:04d}" for snr in (600, 650, 700)
            for frame in range(1024)]


def value(text: str):
    if text == "":
        return None
    if text in ("True", "False"):
        return text == "True"
    if text[0] in "[{":
        return json.loads(text)
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("x") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def build(old_csv: Path, fresh_jsonl: Path, out: Path) -> None:
    if out.exists():
        raise FileExistsError(out)
    with old_csv.open(newline="") as stream:
        old = [{key: value(item) for key, item in row.items()}
               for row in csv.DictReader(stream)]
    fresh = [json.loads(line) for line in fresh_jsonl.read_text().splitlines()]
    if ([row["observation_id"] for row in old] != EXPECTED or
            [row["observation_id"] for row in fresh] != EXPECTED):
        raise ValueError("historical/fresh frame allocation differs")
    if not all(row["input_sha256"] and row["observation_hash"] for row in fresh):
        raise ValueError("fresh observation identity missing")
    if not all(row["input_sha256"] for row in old):
        raise ValueError("historical observation hash missing")
    historical_observed = []
    historical_truth = []
    index = []
    for row in old:
        identity = {"campaign_id": OLD_CAMPAIGN,
                    "observation_id": row["observation_id"],
                    "snr_centi_db": row["snr_centi_db"], "frame": row["frame"]}
        historical_observed.append({**identity, **{
            key: item for key, item in row.items() if key not in OLD_TRUTH_FIELDS
        }})
        historical_truth.append({**identity, "diagnostic_non_deployable": True,
            **{key: row[key] for key in OLD_TRUTH_FIELDS}})
        index.append({**identity, "input_sha256": row["input_sha256"],
            "observation_hash": None, "observed_table": "historical_frame_table.jsonl",
            "outcome_table": "historical_truth_annotations.jsonl",
            "truth_table": "historical_truth_annotations.jsonl",
            "selection": "complete original Part-B TF population",
            "pooling_status": "separate_population_no_cross_campaign_fer_pooling"})
    for row in fresh:
        identity = {"campaign_id": FRESH_CAMPAIGN,
                    "observation_id": row["observation_id"],
                    "snr_centi_db": row["snr_centi_db"], "frame": row["frame"]}
        index.append({**identity, "input_sha256": row["input_sha256"],
            "observation_hash": row["observation_hash"],
            "observed_table": "frame_table.jsonl",
            "outcome_table": "frame_outcomes.csv",
            "truth_table": "truth_annotations.jsonl",
            "selection": "complete fresh prospective population",
            "pooling_status": "separate_population_no_cross_campaign_fer_pooling"})
    if len({(r["campaign_id"], r["observation_id"], r["input_sha256"])
            for r in index}) != 6144:
        raise ValueError("duplicate campaign-qualified frame identity")
    out.mkdir(parents=True)
    write_jsonl(out / "historical_frame_table.jsonl", historical_observed)
    write_jsonl(out / "historical_truth_annotations.jsonl", historical_truth)
    write_jsonl(out / "frame_index.jsonl", index)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--fresh", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.historical, args.fresh, args.out)
