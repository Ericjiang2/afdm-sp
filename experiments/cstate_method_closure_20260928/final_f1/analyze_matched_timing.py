#!/usr/bin/env python3
"""Observed-ledger-only timing analysis for the final matched F1 comparison."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np

from f1_matched_timing import ARMS, SCHEMA, schedule


METRICS = ("acquisition_seconds", "complete_latency_seconds", "native_seconds",
           "refit_seconds", "tf_seconds", "decoder_seconds",
           "raw_serialization_seconds", "decision_record_seconds")
OBSERVED_REPO_PATH = (
    "results/cstate_method_closure_20260928/final_f1/observed_matched64_v1/observed_seal.json")
REGISTRATION_REPO_PATH = (
    "results/cstate_method_closure_20260928/final_f1/F1_MATCHED64_TIMING_REGISTRATION.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(values: list[float]) -> dict:
    a = np.asarray(values, dtype=np.float64)
    if a.shape != (64,) or not np.isfinite(a).all():
        raise ValueError("timing distribution requires 64 finite matched values")
    return dict(n=64, mean=float(np.mean(a)), median=float(np.median(a)),
                p95=float(np.quantile(a, .95)), p99=float(np.quantile(a, .99)),
                max=float(np.max(a)), min=float(np.min(a)))


def summarize(rows: list[dict]) -> dict:
    expected = [(f"s650_f{i:04d}", arm)
                for ordinal, i in enumerate(range(0, 1024, 16))
                for arm in schedule(ordinal)]
    if (len(rows) != 192
            or [(row.get("observation_id"), row.get("arm")) for row in rows] != expected
            or any(row.get("status") != "ok" or row.get("triggered") is not False
                   or not math.isfinite(row.get("reference_max_difference", math.nan))
                   or row.get("reference_max_difference", math.inf) > 2e-10
                   for row in rows)):
        raise ValueError("matched timing allocation, status or reference gate differs")
    by_id = {(row["observation_id"], row["arm"]): row for row in rows}
    for row in rows:
        if (row.get("complete_latency_seconds", math.nan) <= 0
                or row["complete_latency_seconds"] > 30
                or row.get("acquisition_seconds", math.nan) < 0
                or row["acquisition_seconds"] > row["native_seconds"]
                or row["native_seconds"] > row["complete_latency_seconds"]):
            raise ValueError("measured clock nesting or cap differs")
        if any(not math.isfinite(row[key]) or row[key] < 0 for key in METRICS):
            raise ValueError("nonfinite or negative timing component")
    arm_stats = {arm: {metric: distribution([
        by_id[(f"s650_f{i:04d}", arm)][metric] for i in range(0, 1024, 16)])
        for metric in METRICS} for arm in ARMS}
    pairs = {}
    for first, second in (("Cref", "Ccompat"), ("Ccompat", "F0"), ("Cref", "F0")):
        pairs[f"{first}_minus_{second}"] = {
            metric: distribution([
                by_id[(f"s650_f{i:04d}", first)][metric]
                - by_id[(f"s650_f{i:04d}", second)][metric]
                for i in range(0, 1024, 16)])
            for metric in ("acquisition_seconds", "complete_latency_seconds")}
    ref = arm_stats["Cref"]["acquisition_seconds"]["mean"]
    fast = arm_stats["Ccompat"]["acquisition_seconds"]["mean"]
    f0 = arm_stats["F0"]["acquisition_seconds"]["mean"]
    excess = ref - f0
    if excess <= 0:
        raise ValueError("F1 reference has no positive acquisition excess over F0")
    removed = (ref-fast)/excess
    remaining = (fast-f0)/excess
    complete_ref = arm_stats["Cref"]["complete_latency_seconds"]["mean"]
    complete_fast = arm_stats["Ccompat"]["complete_latency_seconds"]["mean"]
    complete_reduction = (complete_ref-complete_fast)/complete_ref
    return dict(schema="f1-final-matched64-timing-analysis/1", status="pass",
                matched_frames=64, paid_calls=192,
                arm_timing=arm_stats, paired_differences=pairs,
                acquisition_excess_seconds=excess,
                removable_acquisition_fraction=removed,
                remaining_measured_acquisition_fraction=remaining,
                complete_latency_reduction_fraction=complete_reduction,
                legacy_operational_python_bound_rule=(removed > .5 and complete_reduction >= .10),
                interpretation_limit="remaining measured gap is not an intrinsic-work estimate")


def git_gate(project: Path, observed_commit: str, registration_commit: str,
             seal_path: Path, registration_path: Path) -> None:
    if (len(observed_commit) != 40 or len(registration_commit) != 40
            or any(ch not in "0123456789abcdef" for ch in observed_commit+registration_commit)):
        raise ValueError("full Git commit IDs required")
    proc = subprocess.run(["git", "-C", str(project), "show",
                           f"{observed_commit}:{OBSERVED_REPO_PATH}"],
                          check=True, stdout=subprocess.PIPE)
    if proc.stdout != seal_path.read_bytes():
        raise ValueError("observed seal differs from actual Git blob")
    registered = subprocess.run(["git", "-C", str(project), "show",
                                 f"{registration_commit}:{REGISTRATION_REPO_PATH}"],
                                check=True, stdout=subprocess.PIPE)
    if registered.stdout != registration_path.read_bytes():
        raise ValueError("registration differs from actual Git blob")
    ancestry = subprocess.run(["git", "-C", str(project), "merge-base", "--is-ancestor",
                               registration_commit, observed_commit], check=False)
    if ancestry.returncode:
        raise ValueError("observed Git commit does not descend from registration")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--observed", required=True, type=Path)
    parser.add_argument("--observed-commit", required=True)
    parser.add_argument("--registration", required=True, type=Path)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("matched timing analysis output already exists")
    if sha256(args.registration) != args.registration_sha256:
        raise ValueError("timing registration SHA differs")
    registration = json.loads(args.registration.read_text())
    observed = args.observed
    seal_path = observed / "observed_seal.json"
    seal = json.loads(seal_path.read_text())
    manifest = json.loads((observed / "manifest.json").read_text())
    if (registration.get("schema") != SCHEMA or registration.get("status") != "locked"
            or seal.get("status") != "pass" or seal.get("calls") != 192
            or seal.get("observations") != 64
            or seal.get("registration_sha256") != args.registration_sha256
            or manifest.get("registration_sha256") != args.registration_sha256
            or manifest.get("source_hashes") != registration.get("source_hashes")):
        raise ValueError("matched observed seal, manifest or registration differs")
    git_gate(args.project, args.observed_commit, manifest["registration_commit"],
             seal_path, args.registration)
    for name in ("manifest.json", "attempts.jsonl", "ledger.jsonl"):
        if seal["files"].get(name) != sha256(observed / name):
            raise ValueError(f"matched sealed metadata differs: {name}")
    attempts = [json.loads(line) for line in (observed / "attempts.jsonl").read_text().splitlines()]
    rows = [json.loads(line) for line in (observed / "ledger.jsonl").read_text().splitlines()]
    if (len(attempts) != 192 or [r["attempt_index"] for r in attempts] != list(range(1, 193))
            or [r["attempt_index"] for r in rows] != list(range(1, 193))):
        raise ValueError("attempt reservation sequence differs")
    for attempt, row in zip(attempts, rows, strict=True):
        if (attempt["observation_id"] != row["observation_id"] or attempt["arm"] != row["arm"]
                or seal["files"].get(row["raw_path"]) != row["raw_sha256"]
                or seal["files"].get(row["decision_path"]) != row["decision_sha256"]
                or any(seal["files"].get(cp["path"]) != cp["artifact_sha256"]
                       for cp in row["checkpoints"])):
            raise ValueError("matched attempt/raw/decision/checkpoint identity differs")
    report = summarize(rows)
    report.update(observed_commit=args.observed_commit, observed_seal_sha256=sha256(seal_path),
                  registration_sha256=args.registration_sha256,
                  reader_sha256=sha256(Path(__file__)))
    args.out.mkdir(parents=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True,
                                                 allow_nan=False) + "\n")
    with (args.out / "timing.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("scope", "arm_or_pair", "metric", "n", "mean_seconds",
                         "median_seconds", "p95_seconds", "p99_seconds", "max_seconds", "min_seconds"))
        for scope, group in (("matched_64", report["arm_timing"]),
                             ("paired_difference", report["paired_differences"])):
            for name, metrics in group.items():
                for metric, values in metrics.items():
                    writer.writerow((scope, name, metric, *(values[k] for k in (
                        "n", "mean", "median", "p95", "p99", "max", "min"))))
    (args.out / "analysis_receipt.json").write_text(json.dumps(dict(
        status="pass", report_sha256=sha256(args.out / "report.json"),
        timing_sha256=sha256(args.out / "timing.csv"),
        reader_sha256=sha256(Path(__file__)), observed_commit=args.observed_commit,
        observed_seal_sha256=sha256(seal_path)), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
