"""Offline, post-seal cohort and qualified failure-evidence derivation.

Inputs are the already exported research pack. This module never imports a
receiver, generator, or optimizer. All truth-dependent columns are prefixed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

EXPECTED_SNRS = (600, 650, 700)
EXPECTED_PER_SNR = 1024
EXPECTED_COHORTS = {"A_remaining_failure": 72, "B_rescued": 194,
                    "C_easy_success": 2806}
OUTPUTS = ("cohort_index.csv", "remaining_failure_index.csv",
           "fresh_frame_table.csv", "failure_taxonomy.csv",
           "cohort_comparison.md", "cohort_derivation_summary.json")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def jsonl(path: Path) -> list[dict]:
    require(path.is_file(), f"missing input: {path}")
    with path.open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def csv_rows(path: Path) -> list[dict]:
    require(path.is_file(), f"missing input: {path}")
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def by_id(rows: list[dict], name: str) -> dict[str, dict]:
    ids = [row.get("observation_id") for row in rows]
    require(all(isinstance(value, str) and value for value in ids),
            f"{name}: missing observation ID")
    require(len(set(ids)) == len(ids), f"{name}: duplicate observation ID")
    return dict(zip(ids, rows))


def boolean(value: object, name: str) -> bool:
    require(value in (True, False, "True", "False"),
            f"{name}: invalid boolean {value!r}")
    return value is True or value == "True"


def number(value: object, name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: nonnumeric value {value!r}") from exc
    require(math.isfinite(result), f"{name}: nonfinite value")
    return result


def scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, bool, int, float))


def select_cohort(outcome: dict) -> str:
    trigger = boolean(outcome["trigger"], "trigger")
    tf_correct = boolean(outcome["tf_correct"], "tf_correct")
    combined_correct = boolean(outcome["combined_correct"], "combined_correct")
    rescue = boolean(outcome["rescue"], "rescue")
    failure = boolean(outcome["remaining_triggered_failure"], "remaining_triggered_failure")
    require(not (rescue and failure), "rescue/failure overlap")
    if failure:
        require(trigger and not tf_correct and not combined_correct,
                "remaining-failure label inconsistent with paired outcome")
        return "A_remaining_failure"
    if rescue:
        require(trigger and not tf_correct and combined_correct,
                "rescue label inconsistent with paired outcome")
        return "B_rescued"
    require(not trigger and tf_correct and combined_correct,
            "frame outside registered A/B/C allocation")
    return "C_easy_success"


def quantiles(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "mean": None, "median": None, "p10": None,
                "p90": None, "minimum": None, "maximum": None}
    ordered = sorted(values)
    def q(fraction: float) -> float:
        position = (len(ordered) - 1) * fraction
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return {"n": len(values), "mean": statistics.fmean(values),
            "median": q(.5), "p10": q(.1), "p90": q(.9),
            "minimum": ordered[0], "maximum": ordered[-1]}


def write_csv(path: Path, rows: list[dict]) -> None:
    require(bool(rows), f"empty output: {path.name}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def scalar_columns(row: dict, prefix: str, *, exclude: set[str] | None = None) -> dict:
    exclude = exclude or set()
    return {prefix + key: value for key, value in row.items()
            if key not in exclude and scalar(value)}


def rank_summary(rows: list[dict]) -> dict:
    """Retain both rank and availability; ranks are post-seal diagnostics."""
    first_step = [row for row in rows if int(row["global_step"]) == 0]
    ranks = [int(row["best_global_rank"]) for row in first_step
             if row.get("best_global_rank") is not None]
    missing = sum(boolean(row["missing_or_all_slots_masked"], "rank missing")
                  for row in first_step)
    return {"offline_truth_rank_min_step0": min(ranks, default=None),
            "offline_truth_rank_path_count_step0": len(first_step),
            "offline_truth_rank_unavailable_paths_step0": missing,
            "offline_truth_rank_outside_top20_paths_step0": sum(rank > 20 for rank in ranks),
            "offline_truth_rank_step_count": len({int(row["global_step"]) for row in rows})}


def nearest_observable_control(anchor_id: str, cohort: str,
                               obs_by: dict[str, dict],
                               cohort_by: dict[str, str]) -> str:
    """Recount exporter's frozen SNR/syndrome/time/ID control rule."""
    anchor = obs_by[anchor_id]
    snr = int(anchor["snr_centi_db"])
    candidates = [identifier for identifier, value in cohort_by.items()
                  if value == cohort and int(obs_by[identifier]["snr_centi_db"]) == snr]
    require(bool(candidates), f"no observable control: {anchor_id}/{cohort}")
    syndrome = number(anchor["baseline_syndrome_weight"], "baseline_syndrome_weight")
    seconds = number(anchor["tf_complete_seconds"], "tf_complete_seconds")
    require(syndrome is not None and seconds is not None, "missing observed match feature")
    def distance(identifier: str) -> tuple[float, float, str]:
        observed = obs_by[identifier]
        candidate_syndrome = number(observed["baseline_syndrome_weight"],
                                    "baseline_syndrome_weight")
        candidate_seconds = number(observed["tf_complete_seconds"], "tf_complete_seconds")
        require(candidate_syndrome is not None and candidate_seconds is not None,
                "missing observed control feature")
        return abs(candidate_syndrome - syndrome), abs(candidate_seconds - seconds), identifier
    return min(candidates, key=distance)


def compare_markdown(rows: list[dict], metrics: list[str], counts: dict) -> tuple[str, dict]:
    def fmt(value: float | None) -> str:
        return "—" if value is None else f"{value:.4g}"

    summaries: dict[str, dict] = {}
    lines = ["# Fresh cohort comparison", "",
             "Descriptive, post-seal analysis of one 3,072-frame prospective campaign. "
             "A/B/C labels use saved outcomes; controls were selected without physical truth. "
             "Differences are associations, not causal attribution or deployable triggers.", "",
             "| Cohort | 6 dB | 6.5 dB | 7 dB | Total |", "|---|---:|---:|---:|---:|"]
    for cohort in EXPECTED_COHORTS:
        cells = [counts[cohort][snr] for snr in EXPECTED_SNRS]
        lines.append(f"| {cohort} | {cells[0]} | {cells[1]} | {cells[2]} | {sum(cells)} |")
    lines += ["", "For each metric, `n` is the available count. Values are mean "
              "[p10, median, p90]; the range exposes outliers. Blank means the "
              "quantity was not exported or cannot be computed for that cohort.", ""]
    for metric in metrics:
        lines += [f"## `{metric}`", "", "| Cohort | n | mean [p10, median, p90] | range |",
                  "|---|---:|---:|---:|"]
        summaries[metric] = {}
        for cohort in EXPECTED_COHORTS:
            values = [number(row.get(metric), metric) for row in rows if row["cohort"] == cohort]
            stats = quantiles([v for v in values if v is not None])
            summaries[metric][cohort] = stats
            lines.append(f"| {cohort} | {stats['n']} | {fmt(stats['mean'])} "
                         f"[{fmt(stats['p10'])}, {fmt(stats['median'])}, {fmt(stats['p90'])}] "
                         f"| {fmt(stats['minimum'])}–{fmt(stats['maximum'])} |")
        a = summaries[metric]["A_remaining_failure"]["median"]
        b = summaries[metric]["B_rescued"]["median"]
        c = summaries[metric]["C_easy_success"]["median"]
        if a is not None and b is not None and c is not None:
            lines.append(f"\nMedian differences A−B={a-b:.4g}, A−C={a-c:.4g}; "
                         "raw units, no significance test.")
        lines.append("")
    lines += ["Missing per-iteration detector state vectors, complete LDPC-message "
              "trajectories, and per-candidate timing remain unavailable when absent "
              "from the frozen producer. Physical truth and rank diagnostics are "
              "post-seal and nondeployable.", ""]
    return "\n".join(lines), summaries


def derive(pack: Path, *, physical_path: Path | None = None,
           expected_per_snr: int = EXPECTED_PER_SNR,
           expected_cohorts: dict[str, int] | None = None) -> dict:
    """Validate identities before writing; output files are append-free."""
    pack = pack.resolve()
    expected_cohorts = expected_cohorts or EXPECTED_COHORTS
    paths = {name: pack / name for name in ("frame_table.jsonl", "frame_outcomes.csv",
             "truth_annotations.jsonl", "truth_candidate_ranks.jsonl",
             "cstate_landscape.jsonl")}
    observed = jsonl(paths["frame_table.jsonl"])
    outcomes = csv_rows(paths["frame_outcomes.csv"])
    truth = jsonl(paths["truth_annotations.jsonl"])
    ranks = jsonl(paths["truth_candidate_ranks.jsonl"])
    landscape = jsonl(paths["cstate_landscape.jsonl"])
    obs_by, outcome_by, truth_by, landscape_by = (
        by_id(observed, "observed"), by_id(outcomes, "outcomes"),
        by_id(truth, "truth"), by_id(landscape, "landscape"))
    ids = [row["observation_id"] for row in observed]
    expected_ids = [f"s{snr}_f{frame:04d}" for snr in EXPECTED_SNRS
                    for frame in range(expected_per_snr)]
    require(ids == expected_ids, "fresh observation order/allocation differs")
    require(set(ids) == set(outcome_by) == set(truth_by), "population join differs")
    cohort_by = {identifier: select_cohort(outcome_by[identifier]) for identifier in ids}
    require(len(landscape) == sum(boolean(row["trigger"], "trigger") for row in outcomes),
            "landscape/trigger count differs")
    require(set(landscape_by) == {row["observation_id"] for row in outcomes
                                   if boolean(row["trigger"], "trigger")},
            "landscape identity differs")
    rank_by: dict[str, list[dict]] = defaultdict(list)
    for row in ranks:
        identifier = row["observation_id"]
        require(identifier in landscape_by, "truth rank belongs to non-triggered frame")
        rank_by[identifier].append(row)
    require(set(rank_by) == set(landscape_by), "trigger/rank identity differs")
    for identifier, rows in rank_by.items():
        n_true = int(truth_by[identifier]["true_path_count"])
        steps = int(landscape_by[identifier]["step_count"])
        require(len(rows) == n_true * steps and
                {int(row["global_step"]) for row in rows} == set(range(steps)),
                f"incomplete rank rows: {identifier}")

    if physical_path is None:
        candidate = pack / "truth_diagnostics" / "frame_diagnostics.jsonl"
        physical_path = candidate if candidate.is_file() else None
    physical_by: dict[str, dict] = {}
    if physical_path is not None:
        physical_by = by_id(jsonl(physical_path), "physical diagnostics")
        require(set(physical_by) == set(ids), "physical diagnostic population differs")

    dossiers_dir = pack / "remaining_failure_dossiers"
    require(dossiers_dir.is_dir(), "missing failure dossiers")
    cohorts, table, failures, taxonomy = [], [], [], []
    counts: dict[str, Counter] = {name: Counter() for name in EXPECTED_COHORTS}
    metric_names = ["observed_baseline_syndrome_weight", "observed_tf_complete_seconds",
                    "observed_combined_complete_seconds", "observed_cstate_score_gain",
                    "postseal_tf_info_errors", "postseal_combined_info_errors",
                    "postseal_true_path_count", "postseal_missing_gain_power_fraction",
                    "offline_truth_rank_min_step0"]
    physical_metric_names: set[str] = set()
    for identifier in ids:
        obs, outcome, truth_row = obs_by[identifier], outcome_by[identifier], truth_by[identifier]
        cohort = cohort_by[identifier]
        snr = int(obs["snr_centi_db"])
        require(snr == int(outcome["snr_centi_db"]) == int(truth_row["snr_centi_db"]),
                f"SNR join differs: {identifier}")
        counts[cohort][snr] += 1
        cohorts.append({"observation_id": identifier, "snr_centi_db": snr,
                        "frame": int(obs["frame"]), "cohort": cohort,
                        "selection_basis": "post_seal_paired_information_word_outcome"})
        row = {"observation_id": identifier, "snr_centi_db": snr,
               "frame": int(obs["frame"]), "cohort": cohort,
               "observed_observation_path": obs["observation_path"],
               "observed_tf_trace_path": f"tf_traces/{identifier}.npz",
               "observed_cstate_path": f"cstate_landscape/{identifier}.npz"
               if identifier in landscape_by else None,
               "postseal_truth_payload_path": truth_row["truth_payload_path"],
               "offline_physical_missing_reason": None if identifier in physical_by else
               "physical_derivation_not_supplied"}
        row.update(scalar_columns(obs, "observed_", exclude={"observation_id", "snr_centi_db", "frame"}))
        row.update(scalar_columns(outcome, "postseal_", exclude={"observation_id", "snr_centi_db", "frame"}))
        row.update(scalar_columns(truth_row, "postseal_", exclude={"observation_id", "snr_centi_db"}))
        if identifier in landscape_by:
            row.update(scalar_columns(landscape_by[identifier], "observed_landscape_",
                                      exclude={"observation_id"}))
            before = number(landscape_by[identifier].get("objective_before"), "objective_before")
            after = number(landscape_by[identifier].get("objective_after"), "objective_after")
            row["observed_cstate_score_gain"] = None if before is None or after is None else before - after
            row.update(rank_summary(rank_by[identifier]))
        else:
            row.update({key: None for key in rank_summary([])})
            row["observed_cstate_score_gain"] = None
        if identifier in physical_by:
            for key, value in scalar_columns(physical_by[identifier], "offline_physical_",
                                             exclude={"observation_id"}).items():
                require(key not in row, f"duplicate physical column: {key}")
                row[key] = value
                if isinstance(value, (float, int)) and not isinstance(value, bool):
                    physical_metric_names.add(key)
        physical = physical_by.get(identifier)
        projection_nmse = (number(physical.get("final_selected_geometry_projection_nmse"),
                                  "final_selected_geometry_projection_nmse")
                           if physical is not None else None)
        saved_gain_nmse = (number(physical.get("final_saved_gain_operator_mismatch_nmse"),
                                 "final_saved_gain_operator_mismatch_nmse")
                           if physical is not None else None)
        excess_nmse = (saved_gain_nmse - projection_nmse
                       if saved_gain_nmse is not None and projection_nmse is not None else None)
        row["offline_final_saved_gain_excess_nmse"] = excess_nmse
        if excess_nmse is not None:
            physical_metric_names.add("offline_final_saved_gain_excess_nmse")
        table.append(row)
        if cohort != "A_remaining_failure":
            continue
        dossier_path = dossiers_dir / f"{identifier}.json"
        require(dossier_path.is_file(), f"missing dossier: {identifier}")
        dossier = json.loads(dossier_path.read_text())
        require(dossier["observation_id"] == identifier, "dossier identity differs")
        rescued_id, easy_id = dossier["rescued_control_id"], dossier["easy_control_id"]
        for control_id, wanted in ((rescued_id, "B_rescued"), (easy_id, "C_easy_success")):
            require(control_id in outcome_by and cohort_by[control_id] == wanted and
                    int(obs_by[control_id]["snr_centi_db"]) == snr,
                    f"control mismatch: {identifier} -> {control_id}")
            require(control_id == nearest_observable_control(identifier, wanted, obs_by, cohort_by),
                    f"control is not nearest by observed fields: {identifier} -> {control_id}")
        failures.append({"observation_id": identifier, "snr_centi_db": snr,
                         "dossier_path": str(dossier_path.relative_to(pack)),
                         "rescued_control_id": rescued_id, "easy_control_id": easy_id,
                         "control_matching": dossier["matching_rule"],
                         "physical_diagnostic_status": "available" if identifier in physical_by else "unavailable"})
        missing_delays = truth_row.get("missing_distinct_delays")
        best_rank = row["offline_truth_rank_min_step0"]
        physical_missing_delays = (physical.get("final_missing_distinct_delay_count")
                                   if physical is not None else None)
        if physical_missing_delays is not None:
            require(isinstance(physical_missing_delays, int) and
                    not isinstance(physical_missing_delays, bool) and
                    physical_missing_delays >= 0,
                    f"invalid final missing-delay count: {identifier}")
        full_class_reason = (physical.get("full_class_optimum_unavailable_reason")
                             if physical is not None else "physical_derivation_not_supplied")
        if physical is not None:
            require(isinstance(full_class_reason, str) and bool(full_class_reason),
                    f"missing full-class optimum limitation: {identifier}")
        if projection_nmse is not None and saved_gain_nmse is not None:
            inference_indicator = "fixed_geometry_projection_and_saved_gain_available"
        elif projection_nmse is not None:
            inference_indicator = "fixed_geometry_projection_only_saved_gain_unavailable"
        else:
            inference_indicator = "physical_projection_unavailable"
        taxonomy.append({"observation_id": identifier, "snr_centi_db": snr,
            "nonexclusive_qualified_evidence": True,
            "representation_gap_indicator": "missing_working_delay" if missing_delays else
                ("none_by_delay_only" if missing_delays == [] else "unavailable"),
            "representation_gap_scope": "working delay coverage and final saved-geometry projection are diagnostics; global fixed-cardinality optimum is uncomputed",
            "structural_rank_indicator": "nearest_truth_outside_top20" if best_rank is not None and best_rank > 20 else
                ("nearest_truth_in_top20" if best_rank is not None else "rank_unavailable"),
            "structural_rank_scope": "first saved step; nearest path rank does not prove a jointly recoverable geometry",
            "in_span_inference_indicator": inference_indicator,
            "in_span_inference_scope": "saved gains minus best complex-gain projection at fixed final delays/Dopplers; finite difference is descriptive, not causal",
            "communication_objective_indicator": "score_improved_without_decode" if
                row["observed_cstate_score_gain"] is not None and row["observed_cstate_score_gain"] > 0 else
                "score_gain_unavailable_or_nonpositive",
            "communication_objective_scope": "observed score gain and failed decoding coexist; no causal claim",
            "low_information_indicator": "unresolved_without_matched_fresh_oracle",
            "physical_diagnostic_status": "available" if identifier in physical_by else "unavailable",
            "final_selected_geometry_projection_nmse": projection_nmse,
            "final_saved_gain_operator_mismatch_nmse": saved_gain_nmse,
            "final_saved_gain_excess_nmse": excess_nmse,
            "final_missing_distinct_delay_count": physical_missing_delays,
            "full_class_optimum_unavailable_reason": full_class_reason,
            "postseal_missing_distinct_delays": json.dumps(missing_delays),
            "postseal_missing_gain_power_fraction": truth_row.get("missing_gain_power_fraction"),
            "offline_truth_rank_min_step0": best_rank,
            "observed_cstate_score_gain": row["observed_cstate_score_gain"],
            "exclusive_causal_class": "unassigned"})
    require({name: sum(cells.values()) for name, cells in counts.items()} == expected_cohorts,
            "A/B/C cohort counts differ")
    require(all(sum(counts[name][snr] for name in counts) == expected_per_snr
                for snr in EXPECTED_SNRS), "SNR coverage differs")
    require(len(failures) == expected_cohorts["A_remaining_failure"], "failure index differs")
    require(len(list(dossiers_dir.glob("*.json"))) == len(failures), "dossier directory differs")
    metric_names += sorted(physical_metric_names)
    comparison, distributions = compare_markdown(table, metric_names, counts)
    for name in OUTPUTS:
        require(not (pack / name).exists(), f"derived output exists: {name}")
    write_csv(pack / "cohort_index.csv", cohorts)
    write_csv(pack / "remaining_failure_index.csv", failures)
    write_csv(pack / "fresh_frame_table.csv", table)
    write_csv(pack / "failure_taxonomy.csv", taxonomy)
    (pack / "cohort_comparison.md").write_text(comparison)
    source_hashes = {str(path.relative_to(pack)): sha256(path) for path in paths.values()}
    if physical_path is not None:
        source_hashes[str(physical_path)] = sha256(physical_path)
    summary = {"schema": "tf-research-discovery-cohorts/1", "fresh_observations": len(ids),
               "cohort_counts": {name: dict(counts[name]) for name in counts},
               "trigger_count": len(landscape), "failure_dossiers": len(failures),
               "physical_diagnostics": "complete" if physical_by else "not_supplied",
               "input_sha256": source_hashes, "distributions": distributions,
               "outputs_sha256": {name: sha256(pack / name) for name in OUTPUTS[:-1]},
               "limits": ["post-seal truth is nondeployable", "cohorts selected by outcomes",
                          "nonexclusive taxonomy is descriptive, not causal",
                          "no post-hoc significance testing"]}
    (pack / "cohort_derivation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--physical", type=Path,
                        help="optional complete frame_diagnostics.jsonl")
    args = parser.parse_args()
    result = derive(args.pack, physical_path=args.physical)
    print(json.dumps({key: result[key] for key in ("fresh_observations", "cohort_counts",
          "trigger_count", "failure_dossiers", "physical_diagnostics")}, indent=2))


if __name__ == "__main__":
    main()
