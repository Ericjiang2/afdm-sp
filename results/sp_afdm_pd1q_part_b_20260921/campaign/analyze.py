#!/usr/bin/env python3
"""Frozen Part-B analysis of a complete, independently recounted saved run.

No receiver, decoder, radio generator, or numerical source function is called.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import beta


PRIMARY = ("TF_J20_R2", "EP2_MEAN_R2", "EP4_MEAN_R2")
CONTROLS = (("TF_POINT20_R2", 128), ("PBI8_SOFT_R2", 32))
SNRS = (600, 650, 700)
FRAMES = 1024
TOTAL_CALLS = 9696
E1_EP2 = "EP2_MEAN_R2"


def args_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--e1-run", type=Path, required=True)
    parser.add_argument("--recount-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True,
                        help="new or empty analysis output directory")
    return parser.parse_args()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_seconds(value, label, *, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or value < 0 or (positive and value == 0)):
        raise ValueError(f"{label} must be finite {'positive' if positive else 'nonnegative'} seconds")
    return float(value)


def cp_lower(events, n, tail):
    if not 0 <= events <= n or n <= 0 or not 0 < tail < 1:
        raise ValueError("invalid exact-binomial endpoint inputs")
    return 0.0 if events == 0 else float(beta.ppf(tail, events, n-events+1))


def cp_upper(events, n, tail):
    if not 0 <= events <= n or n <= 0 or not 0 < tail < 1:
        raise ValueError("invalid exact-binomial endpoint inputs")
    return 1.0 if events == n else float(beta.ppf(1-tail, events+1, n-events))


def cp_two_sided(events, n, alpha=.05):
    return [cp_lower(events, n, alpha/2), cp_upper(events, n, alpha/2)]


def decision_error(row, deadline=None):
    """Latest valid completed checkpoint may survive a later paid failure."""
    checkpoints = row["checkpoints"]
    if deadline is not None:
        checkpoints = [cp for cp in checkpoints if cp["ready"] <= deadline]
    return int(not checkpoints or checkpoints[-1]["info_errors"] != 0)


def last_decision(row):
    return row["checkpoints"][-1] if row["checkpoints"] else None


def expected_coordinates():
    for snr in SNRS:
        for frame in range(FRAMES):
            for arm in PRIMARY:
                yield (snr, frame, arm)
            for arm, count in CONTROLS:
                if frame < count:
                    yield (snr, frame, arm)


def quantile(values, q):
    return float(np.quantile(np.asarray(values, float), q, method="linear"))


def latency_point(values):
    values = np.asarray(values, float)
    if values.size == 0 or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("invalid complete-cost series")
    return {"median_seconds": quantile(values, .5),
            "p90_seconds": quantile(values, .9),
            "p95_seconds": quantile(values, .95),
            "sum_seconds": float(values.sum())}


def paired_counts(left, right, *, primary, alpha=.05, multiplicity=6):
    if len(left) != len(right) or not left:
        raise ValueError("paired FER arrays must be nonempty and equal")
    a, b = np.asarray(left, bool), np.asarray(right, bool)
    n = len(a)
    harm = int(np.count_nonzero(a & ~b))
    rescue = int(np.count_nonzero(~a & b))
    tail = alpha/(2*multiplicity)
    result = {"n": n, "harm_TF_wrong_comparator_correct": harm,
            "rescue_TF_correct_comparator_wrong": rescue,
            "both_wrong": int(np.count_nonzero(a & b)),
            "both_correct": int(np.count_nonzero(~a & ~b)),
            "delta_fer_TF_minus_comparator": (harm-rescue)/n}
    result.update({
        "upper_excess_fer_six_upper_family":
            cp_upper(harm, n, tail)-cp_lower(rescue, n, tail) if primary else "",
        "lower_excess_fer_separate_six_lower_family":
            cp_lower(harm, n, tail)-cp_upper(rescue, n, tail) if primary else "",
        "bound_tail_probability": tail if primary else ""})
    return result


def classify_primary(rows, contract):
    required = {(snr, arm) for snr in SNRS for arm in PRIMARY[1:]}
    present = {(row["snr_centi_db"], row["comparator"]) for row in rows}
    if len(rows) != 6 or present != required:
        raise ValueError("six primary paired comparisons required")
    tolerances = contract["reliability_tolerances"]
    reliability_supported = all(row["upper_excess_fer_six_upper_family"] <=
                                tolerances[str(row["snr_centi_db"])] for row in rows)
    ep2 = [row for row in rows if row["comparator"] == "EP2_MEAN_R2"]
    speed_supported = all(row["median_ratio_bootstrap_upper95"] < .8 and
                          row["ratio_of_p90_seconds"] <= 1 for row in ep2)
    adverse = any(row["lower_excess_fer_separate_six_lower_family"] >
                  tolerances[str(row["snr_centi_db"])] for row in rows)
    speed_falsified = any(row["median_ratio_bootstrap_lower5"] >= .8 or
                          row["p90_ratio_bootstrap_lower5"] > 1 for row in ep2)
    verdict = ("supported" if reliability_supported and speed_supported else
               "falsified" if adverse or speed_falsified else "inconclusive")
    return verdict, reliability_supported, speed_supported, adverse, speed_falsified


def circular_block_indices(n, block, rng):
    if n <= 0 or block <= 0 or n % block:
        raise ValueError("fixed circular block allocation differs")
    starts = rng.integers(0, n, size=n//block)
    return ((starts[:, None]+np.arange(block)[None, :]) % n).reshape(-1)


def bootstrap_primary(series, snr, contract):
    """Whole paired frames, circular blocks, same indices across all primary arms."""
    rule = contract["latency_bootstrap"]
    block, repeats, seed = rule["block_frames"], rule["replicates"], rule["seed"]
    if (block, repeats, seed) != (32, 2000, 941002):
        raise ValueError("prospective latency bootstrap contract differs")
    if set(series) != set(PRIMARY) or any(len(series[arm]) != FRAMES for arm in PRIMARY):
        raise ValueError("bootstrap requires all paired primary complete costs")
    values = {arm: np.asarray(series[arm], float) for arm in PRIMARY}
    if any(not np.isfinite(item).all() or np.any(item <= 0) for item in values.values()):
        raise ValueError("paired latency ratios require positive finite complete costs")
    rng = np.random.default_rng(np.random.SeedSequence([seed, snr]))
    measures = defaultdict(list)
    for _ in range(repeats):
        indices = circular_block_indices(FRAMES, block, rng)
        sampled = {arm: values[arm][indices] for arm in PRIMARY}
        for arm in PRIMARY:
            point = latency_point(sampled[arm])
            for metric in ("median_seconds", "p90_seconds", "p95_seconds"):
                measures[(arm, metric)].append(point[metric])
        tf = sampled[PRIMARY[0]]
        for comparator in PRIMARY[1:]:
            other = sampled[comparator]
            measures[(comparator, "ratio_of_medians")].append(
                quantile(tf, .5)/quantile(other, .5))
            measures[(comparator, "ratio_of_p90")].append(
                quantile(tf, .9)/quantile(other, .9))
            measures[(comparator, "median_paired_ratio")].append(
                quantile(tf/other, .5))
    return {key: {"percentile_2_5": quantile(samples, .025),
                  "percentile_97_5": quantile(samples, .975),
                  "one_sided_lower_5": quantile(samples, .05),
                  "one_sided_upper_95": quantile(samples, .95)}
            for key, samples in measures.items()}


def bootstrap_subset(tf, other, snr, comparator, contract):
    """Fixed-index controls use shorter prospectively registered circular blocks."""
    n = len(tf)
    block_by_n = {128: 16, 32: 4}
    expected = {"primary_1024": 32, "POINT_128": 16, "PBi_32": 4}
    if (n not in block_by_n or len(other) != n or
            contract["latency_bootstrap"]["subset_block_frames"] != expected):
        raise ValueError("prospective subset bootstrap block contract differs")
    tf, other = np.asarray(tf, float), np.asarray(other, float)
    if (not np.isfinite(tf).all() or not np.isfinite(other).all() or
            np.any(tf <= 0) or np.any(other <= 0)):
        raise ValueError("subset paired latency requires positive finite complete costs")
    arm_index = 1 if comparator == "TF_POINT20_R2" else 2
    rng = np.random.default_rng(np.random.SeedSequence([941002, snr, arm_index]))
    samples = defaultdict(list)
    for _ in range(2000):
        indices = circular_block_indices(n, block_by_n[n], rng)
        a, b = tf[indices], other[indices]
        for arm, values in ((PRIMARY[0], a), (comparator, b)):
            point = latency_point(values)
            for metric in ("median_seconds", "p90_seconds", "p95_seconds"):
                samples[(arm, metric)].append(point[metric])
        samples["ratio_of_medians"].append(quantile(a, .5)/quantile(b, .5))
        samples["ratio_of_p90"].append(quantile(a, .9)/quantile(b, .9))
        samples["median_paired_ratio"].append(quantile(a/b, .5))
    return {name: {"percentile_2_5": quantile(values, .025),
                   "percentile_97_5": quantile(values, .975),
                   "one_sided_lower_5": quantile(values, .05),
                   "one_sided_upper_95": quantile(values, .95)}
            for name, values in samples.items()}


def e1_deadlines(e1_run, manifest, plan, evidence):
    old_manifest_path = e1_run / "manifest.json"
    old_ledger_path = e1_run / "ledger.jsonl"
    if (manifest["e1_manifest_sha256"] != plan["e1_manifest_sha256"] or
            manifest["e1_ledger_sha256"] != plan["e1_ledger_sha256"]):
        raise ValueError("Part B E1 deadline source identity differs")
    if (sha(old_manifest_path) != plan["e1_manifest_sha256"] or
            sha(old_ledger_path) != plan["e1_ledger_sha256"]):
        raise ValueError("frozen E1 deadline source hashes differ")
    old_manifest = json.loads(old_manifest_path.read_text())
    if (old_manifest["stage"] != "D" or old_manifest["source_commit"] != manifest["source_commit"] or
            old_manifest["source_hashes"] != manifest["source_hashes"] or
            old_manifest["baseline_source_hashes"] != manifest["baseline_source_hashes"]):
        raise ValueError("E1 numerical source differs from Part B")
    if old_manifest["environment"]["hostname"] != manifest["environment"]["hostname"]:
        raise ValueError("E1 deadline machine differs; no timing calibration authorized")
    rows = [json.loads(line) for line in old_ledger_path.read_text().splitlines()]
    values = {}
    for snr in SNRS:
        ep = {row["frame"]: finite_seconds(row["seconds"], "E1 EP2 complete cost")
              for row in rows if row["snr_centi_db"] == snr and row["arm"] == E1_EP2}
        if set(ep) != set(range(32)):
            raise ValueError("E1 EP2 full32 deadline reference incomplete")
        values[str(snr)] = quantile([ep[frame] for frame in range(32)], .5)
        if not math.isclose(values[str(snr)], plan["e1_ep2_median_seconds"][str(snr)],
                            rel_tol=0, abs_tol=1e-12):
            raise ValueError("predeclared E1 EP2 median differs from saved ledger")
    if values != manifest["e1_ep2_median_seconds"]:
        raise ValueError("Part B manifest deadline reference differs")
    return values


def write_csv(path, rows):
    if not rows:
        raise ValueError("empty analysis table")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = args_parser()
    run, source, baseline, e1_run, receipt_path, out = (
        item.resolve() for item in (args.run, args.source, args.baseline,
                                    args.e1_run, args.recount_receipt, args.out))
    if out.exists() and any(out.iterdir()):
        raise ValueError("Part B analysis output must be new or empty")
    contract_path = Path(__file__).resolve().parents[1] / "statistical_contract.json"
    contract = json.loads(contract_path.read_text())
    if (contract["schema"] != "spafdm-pd1q-partb-statistical-contract/1" or
            contract["total_receiver_calls"] != TOTAL_CALLS or
            contract["total_observations"] != 3072):
        raise ValueError("Part B statistical contract differs")
    qualification_path = contract_path.with_name("qualification_reference_manifest.json")
    qualification = json.loads(qualification_path.read_text())
    if (qualification["status"] != "reused completed Part A evidence, not new Part B measurements" or
            qualification["numerical_source"] != "2d130b4d"):
        raise ValueError("prior qualification reference differs")
    plan_path = Path(__file__).with_name("plan.json")
    plan = json.loads(plan_path.read_text())
    manifest_path = run / "manifest.json"
    ledger_path = run / "ledger.jsonl"
    manifest = json.loads(manifest_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    sys.path[:0] = [str(source / "src"), str(baseline / "src")]
    import evidence

    if (manifest["source_commit"] != "2d130b4d" or
            manifest["baseline_commit"] != "31d5ec0d" or
            manifest["source_hashes"] != evidence.source_hashes(source) or
            manifest["baseline_source_hashes"] != evidence.source_hashes(baseline)):
        raise ValueError("frozen numerical/baseline identity differs")
    if (plan["statistical_contract_sha256"] != sha(contract_path) or
            manifest["statistical_contract_sha256"] != sha(contract_path) or
            manifest["plan_sha256"] != sha(plan_path)):
        raise ValueError("predeclared Part B plan/statistical contract differs")
    run_hash = evidence.canonical_hash(manifest)
    if (receipt["status"] != "pass" or receipt["run_identity_sha256"] != run_hash or
            receipt["records"] != TOTAL_CALLS or
            receipt["manifest_sha256"] != sha(manifest_path) or
            receipt["ledger_sha256"] != sha(ledger_path)):
        raise ValueError("independent saved-array recount receipt differs")
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    expected = set(expected_coordinates())
    index = {(row["snr_centi_db"], row["frame"], row["arm"]): row for row in rows}
    if len(rows) != TOTAL_CALLS or len(index) != TOTAL_CALLS or set(index) != expected:
        raise ValueError("Part B 9696 attempt allocation incomplete/duplicated")
    deadlines = e1_deadlines(e1_run, manifest, plan, evidence)
    for row in rows:
        finite_seconds(row["seconds"], "complete attempt")
        if row["status"] not in ("ok", "numerical_failure"):
            raise ValueError("integrity attempt status in completed run")
        previous = -1.
        for cp in row["checkpoints"]:
            ready = finite_seconds(cp["ready"], "checkpoint ready")
            if not previous <= ready <= row["seconds"]:
                raise ValueError("checkpoint chronology differs")
            previous = ready
            if not isinstance(cp["info_errors"], int) or cp["info_errors"] < 0:
                raise ValueError("invalid completed checkpoint info errors")

    cells = []
    pairs = []
    latency_uncertainty = []
    latency_stages = []
    primary_result = []
    for snr in SNRS:
        full = {arm: [index[(snr, frame, arm)] for frame in range(FRAMES)] for arm in PRIMARY}
        series = {arm: [row["seconds"] for row in full[arm]] for arm in PRIMARY}
        boot = bootstrap_primary(series, snr, contract)
        for (arm, metric), limits in sorted(boot.items()):
            latency_uncertainty.append({"snr_centi_db": snr, "arm_or_comparator": arm,
                "metric": metric, **limits, "replicates": 2000,
                "block_frames": 32, "subset_n": 1024, "analysis_seed": 941002,
                "scope": "pointwise paired circular block bootstrap; no multiplicity correction"})
        arms = {arm: full[arm] for arm in PRIMARY}
        for arm, count in CONTROLS:
            arms[arm] = [index[(snr, frame, arm)] for frame in range(count)]
        for arm, arm_rows in arms.items():
            n = len(arm_rows)
            errors = [decision_error(row) for row in arm_rows]
            cost = latency_point([row["seconds"] for row in arm_rows])
            decisions = [last_decision(row) for row in arm_rows]
            known = [cp for cp in decisions if cp is not None]
            cell = {"snr_centi_db": snr, "arm": arm, "n": n,
                    "subset": "all1024" if arm in PRIMARY else f"first{n}",
                    "frame_errors": sum(errors), "fer": sum(errors)/n,
                    "codeword_frame_errors": sum(cp is None or cp["coded_errors"] != 0
                                                 for cp in decisions),
                    "fer_cp95_lower": cp_two_sided(sum(errors), n)[0],
                    "fer_cp95_upper": cp_two_sided(sum(errors), n)[1],
                    "numerical_failures": sum(row["status"] == "numerical_failure" for row in arm_rows),
                    "frames_without_decision": n-len(known),
                    "info_bit_errors_known": sum(cp["info_errors"] for cp in known),
                    "coded_bit_errors_known": sum(cp["coded_errors"] for cp in known),
                    "info_bits_observed": len(known)*1024,
                    "coded_bits_observed": len(known)*2048,
                    "info_bits_unknown": (n-len(known))*1024,
                    "coded_bits_unknown": (n-len(known))*2048,
                    **cost}
            for factor in contract["deadline_fractions"]:
                key = f"deadline_{factor:g}_frame_errors"
                deadline = factor*deadlines[str(snr)]
                cell[key] = sum(decision_error(row, deadline) for row in arm_rows)
            cells.append(cell)

            named = {"pilot": 0., "ce": 0., "inference": 0., "decoder": 0.}
            missing_pilot = 0
            for row in arm_rows:
                if row.get("pilot_seconds") is None:
                    missing_pilot += 1
                else:
                    named["pilot"] += finite_seconds(row["pilot_seconds"], "pilot stage")
                for cp in row["checkpoints"]:
                    for name in ("ce", "inference", "decoder"):
                        named[name] += finite_seconds(cp["event"][name], name)
            numerical_failures = sum(row["status"] == "numerical_failure" for row in arm_rows)
            stage_row = {"snr_centi_db": snr, "arm": arm, "n": n,
                         "complete_seconds_sum": cost["sum_seconds"],
                         "failure_seconds_sum": sum(row["seconds"] for row in arm_rows
                             if row["status"] == "numerical_failure"),
                         "missing_pilot_stage_attempts": missing_pilot,
                         "unknown_partial_stage_attempts": numerical_failures,
                         **{f"known_{name}_seconds_sum": value for name, value in named.items()},
                         "complete_minus_known_stages_seconds":
                             "" if missing_pilot or numerical_failures else cost["sum_seconds"]-sum(named.values()),
                         "scope": "complete includes setup/checkpoint/failure work; unreported failure stage is unknown, not zero"}
            latency_stages.append(stage_row)

        tf = arms[PRIMARY[0]]
        for comparator in (*PRIMARY[1:], *(arm for arm, _ in CONTROLS)):
            compared = arms[comparator]
            n = len(compared)
            tf_matched = tf[:n]
            counts = paired_counts([decision_error(row) for row in tf_matched],
                                   [decision_error(row) for row in compared],
                                   primary=n == FRAMES)
            tf_cost = np.asarray([row["seconds"] for row in tf_matched], float)
            other_cost = np.asarray([row["seconds"] for row in compared], float)
            if np.any(other_cost <= 0):
                raise ValueError("paired latency denominator is zero")
            ratio = tf_cost/other_cost
            median_ratio = quantile(tf_cost, .5)/quantile(other_cost, .5)
            p90_ratio = quantile(tf_cost, .9)/quantile(other_cost, .9)
            paired = {"snr_centi_db": snr, "tf_arm": PRIMARY[0],
                      "comparator": comparator, "subset": f"first{n}", **counts,
                      "ratio_of_medians": median_ratio,
                      "ratio_of_p90_seconds": p90_ratio,
                      "median_of_paired_complete_time_ratios": quantile(ratio, .5),
                      "p90_paired_complete_time_ratio": quantile(ratio, .9),
                      "p95_paired_complete_time_ratio": quantile(ratio, .95),
                      "reliability_scope": "six simultaneous one-sided upper family" if n == FRAMES else "exploratory fixed subset; not six-comparison primary family"}
            if n == FRAMES:
                median_limits = boot[(comparator, "ratio_of_medians")]
                p90_limits = boot[(comparator, "ratio_of_p90")]
                paired.update(median_ratio_bootstrap_upper95=median_limits["one_sided_upper_95"],
                              median_ratio_bootstrap_lower5=median_limits["one_sided_lower_5"],
                              p90_ratio_bootstrap_lower5=p90_limits["one_sided_lower_5"],
                              p90_ratio_bootstrap_upper95=p90_limits["one_sided_upper_95"])
                primary_result.append(paired)
            else:
                subset_boot = bootstrap_subset(tf_cost, other_cost, snr, comparator, contract)
                for key, limits in sorted(subset_boot.items(), key=lambda item: str(item[0])):
                    label, metric = key if isinstance(key, tuple) else (comparator, key)
                    latency_uncertainty.append({"snr_centi_db": snr,
                        "arm_or_comparator": label, "metric": metric, **limits,
                        "replicates": 2000, "block_frames": 16 if n == 128 else 4,
                        "subset_n": n,
                        "analysis_seed": 941002,
                        "scope": "pointwise fixed-index subset paired circular block bootstrap; no multiplicity correction"})
                median_limits = subset_boot["ratio_of_medians"]
                p90_limits = subset_boot["ratio_of_p90"]
                paired.update(median_ratio_bootstrap_upper95=median_limits["one_sided_upper_95"],
                              median_ratio_bootstrap_lower5=median_limits["one_sided_lower_5"],
                              p90_ratio_bootstrap_lower5=p90_limits["one_sided_lower_5"],
                              p90_ratio_bootstrap_upper95=p90_limits["one_sided_upper_95"])
            pairs.append(paired)

    verdict, reliability_supported, speed_supported, adverse, speed_falsified = (
        classify_primary(primary_result, contract))
    out.mkdir(parents=True, exist_ok=True)
    paths = {"cells": out / "cells.csv", "paired_counts": out / "paired_counts.csv",
             "latency_uncertainty": out / "latency_uncertainty.csv",
             "latency_stage_summary": out / "latency_stage_summary.csv"}
    for name, data in (("cells", cells), ("paired_counts", pairs),
                       ("latency_uncertainty", latency_uncertainty),
                       ("latency_stage_summary", latency_stages)):
        write_csv(paths[name], data)
    provenance = {"schema": "spafdm-pd1q-partb-analysis/1", "status": "pass",
                  "verdict": verdict, "source_commit": manifest["source_commit"],
                  "run_identity_sha256": run_hash, "attempts": len(rows),
                  "frames": 3072, "recount_receipt": str(receipt_path),
                  "e1_ep2_median_seconds": deadlines,
                  "deadline_fractions": contract["deadline_fractions"],
                  "bootstrap": contract["latency_bootstrap"],
                  "reliability_supported": reliability_supported,
                  "speed_supported": speed_supported,
                  "adverse_reliability_bound": adverse,
                  "speed_lower_bound_falsified": speed_falsified,
                  "sha256": {"script": sha(__file__), "statistical_contract": sha(contract_path),
                             "plan": sha(plan_path), "manifest": sha(manifest_path),
                             "prior_qualification_reference": sha(qualification_path),
                             "ledger": sha(ledger_path), "recount_receipt": sha(receipt_path),
                             "e1_manifest": sha(e1_run / "manifest.json"),
                             "e1_ledger": sha(e1_run / "ledger.jsonl"),
                             **{name: sha(path) for name, path in paths.items()}}}
    (out / "analysis_manifest.json").write_text(json.dumps(provenance, indent=2,
                                                            allow_nan=False) + "\n")
    limits = ("Part B adds fresh paired observations; Part A qualification and E1 deadline evidence are reused prior evidence. "
              "The six excess-FER upper bounds form one simultaneous one-sided 95% family. "
              "The six lower bounds are a separate one-sided 95% family, not a joint two-sided interval. "
              "Bootstrap intervals are pointwise and do not adjust multiplicity. "
              "POINT/PBi are fixed-index exploratory subsets. No new receiver calls or scope extensions.\n")
    (out / "claims_and_limits.md").write_text(
        f"# Part B claim and limits\n\nVerdict: **{verdict}** under the frozen statistical contract.\n\n"+limits)
    (out / "RESULTS.md").write_text(
        f"# PD1-Q Part B\n\nValidated {len(rows)} fresh receiver attempts on 3072 independent paired observations. "
        f"Frozen verdict: **{verdict}**.\n\n"
        f"Reliability condition: {'passed' if reliability_supported else 'not established'}; "
        f"EP2 complete-cost speed condition: {'passed' if speed_supported else 'not established'}. "
        f"EP4 and all POINT/PBi fixed subsets are retained in `cells.csv` and `paired_counts.csv`. "
        "Part A numerical/kernel/memory qualification is reused through `../qualification_reference_manifest.json`; "
        "E1 supplies only the predeclared deadline references.\n\n"
        "Machine-readable results: `cells.csv`, `paired_counts.csv`, "
        "`latency_uncertainty.csv`, `latency_stage_summary.csv`, `analysis_manifest.json`.\n")
    print(json.dumps({"status": "pass", "verdict": verdict, "attempts": len(rows),
                      "cells": len(cells), "pairs": len(pairs)}))


if __name__ == "__main__":
    main()
