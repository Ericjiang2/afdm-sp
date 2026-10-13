#!/usr/bin/env python3
"""Derive Part A tables from independently recounted saved ledgers, no receiver."""
import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


MEMORY_ARMS = ("TF_J20_R2", "EP2_MEAN_R2", "EP4_MEAN_R2", "PBI8_SOFT_R2")


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def quantile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    rank = (len(values)-1)*fraction
    lo = math.floor(rank)
    return values[lo] + (values[math.ceil(rank)]-values[lo])*(rank-lo)


def write_csv(path, data, fields):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--part-a-root", type=Path, required=True)
    parser.add_argument("--e1-ledger", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.part_a_root.resolve(), args.out.resolve()
    if out.exists():
        raise ValueError("analysis output must be new")
    if (json.loads((root / "independent_recount_report.json").read_text())["status"] != "pass"
            or json.loads((root / "e1_recount.json").read_text())["status"] != "pass"):
        raise ValueError("independent saved-decision recount has not passed")
    manifest = json.loads((root / "attribution_v2" / "manifest.json").read_text())
    new = rows(root / "attribution_v2" / "ledger.jsonl")
    old = rows(args.e1_ledger)
    if len(new) != 91 or len(old) != 252:
        raise ValueError("Part A/E1 allocation count differs")
    if any(row["status"] != "ok" for row in new):
        raise ValueError("Part A numerical failure requires separate accounting")
    ni = {(r["snr_centi_db"], r["frame"], r["arm"]): r for r in new}
    oi = {(r["snr_centi_db"], r["frame"], r["arm"]): r for r in old}
    if len(ni) != 91 or len(oi) != 252:
        raise ValueError("duplicate call coordinate")
    if any(ni[(snr, 0, "TF_REPLAY")]["input_hash"] != oi[(snr, 0, "TF_J20_R2")]["input_hash"]
           for snr in (600, 650, 700)):
        raise ValueError("replay observation pairing differs")
    cells = []
    by_cell = {}
    for snr in (600, 650, 700):
        for arm in ("TF_J20_R2", "TF_POINT20_R2", "TF_FIXED20_R2",
                    "TF_NO_FEEDBACK20_R2", "TF_NO_GEOMETRY20_R2",
                    "EP2_MEAN_R2", "EP4_MEAN_R2", "PBI8_SOFT_R2"):
            if arm.startswith("TF_NO") and snr != 650:
                continue
            if arm == "TF_J20_R2":
                sample = [oi[(snr, f, arm)] for f in range(16)]
                source = "E1_D_existing_first16"
            elif arm == "TF_POINT20_R2":
                sample = [oi[(snr, f, arm)] if f < 8 else ni[(snr, f, arm)]
                          for f in range(16)]
                source = "E1_D_existing_first8_plus_PartA_new_last8_mixed_process"
            elif arm.startswith("TF_NO"):
                sample = [ni[(snr, f, arm)] for f in range(8)]
                source = "PartA_new_first8"
            elif arm == "TF_FIXED20_R2":
                sample = [ni[(snr, f, arm)] for f in range(16)]
                source = "PartA_new_first16"
            else:
                sample = [oi[(snr, f, arm)] for f in range(16 if arm == "EP2_MEAN_R2"
                          else 8 if arm == "EP4_MEAN_R2" else 4)]
                source = "E1_D_existing_prefix"
            by_cell[(snr, arm)] = sample
            n = len(sample)
            cells.append({"snr_centi_db": snr, "arm": arm, "frames": n, "source": source,
                "info_frame_errors": sum(r["info_errors"] > 0 for r in sample),
                "coded_frame_errors": sum(r["coded_errors"] > 0 for r in sample),
                "info_bit_errors": sum(r["info_errors"] for r in sample),
                "coded_bit_errors": sum(r["coded_errors"] for r in sample),
                "info_bit_denominator": n*1024, "coded_bit_denominator": n*2048,
                "median_complete_seconds": statistics.median(r["seconds"] for r in sample),
                "p90_complete_seconds_linear": quantile([r["seconds"] for r in sample], .9),
                "sum_complete_seconds": sum(r["seconds"] for r in sample)})
    paired = []
    pairs = (("TF_J20_R2", "TF_POINT20_R2"),
             ("TF_J20_R2", "TF_FIXED20_R2"),
             ("TF_POINT20_R2", "TF_FIXED20_R2"),
             ("TF_J20_R2", "TF_NO_FEEDBACK20_R2"),
             ("TF_J20_R2", "TF_NO_GEOMETRY20_R2"))
    for snr in (600, 650, 700):
        for reference, comparison in pairs:
            if (snr, comparison) not in by_cell:
                continue
            target = by_cell[(snr, comparison)]
            base = by_cell[(snr, reference)][:len(target)]
            if any(a["frame"] != b["frame"] or a["input_hash"] != b["input_hash"]
                   for a, b in zip(base, target)):
                raise ValueError("paired control observation differs")
            for kind in ("info", "coded"):
                key = f"{kind}_errors"
                rescues = sum(a[key] > 0 and b[key] == 0 for a, b in zip(base, target))
                harms = sum(a[key] == 0 and b[key] > 0 for a, b in zip(base, target))
                paired.append({"snr_centi_db": snr, "reference_arm": reference,
                    "comparison_arm": comparison, "error_unit": kind, "paired_frames": len(target),
                    "comparison_rescues": rescues, "comparison_harms": harms,
                    "net_comparison_rescues": rescues-harms,
                    "reference_frame_errors": sum(a[key] > 0 for a in base),
                    "comparison_frame_errors": sum(b[key] > 0 for b in target)})
    stages = []
    for (snr, arm), sample in by_cell.items():
        for name in ("pilot", "ce", "inference", "decoder", "residual_including_hooks"):
            values = []
            for row in sample:
                event = row["checkpoints"]
                stage_sum = sum(sum(cp["event"][k] for k in ("ce", "inference", "decoder"))
                                for cp in event)
                if name == "pilot":
                    value = row.get("pilot_seconds")
                elif name == "residual_including_hooks":
                    value = row["seconds"]-stage_sum
                else:
                    value = sum(cp["event"][name] for cp in event)
                if value is not None:
                    values.append(value)
            stages.append({"snr_centi_db": snr, "arm": arm, "stage": name,
                           "available_frames": len(values),
                           "median_seconds": None if not values else statistics.median(values),
                           "p90_seconds_linear": quantile(values, .9),
                           "scope": "complete online includes initial pilot and checkpoint hooks; residual is not pure pilot"})
    memory = []
    for arm in MEMORY_ARMS:
        path = root / "memory" / arm
        summary = json.loads((path / "memory_summary.json").read_text())
        attempts = rows(path / "ledger.jsonl")
        if len(attempts) != 2 or any(a["status"] != "ok" for a in attempts):
            raise ValueError("isolated memory attempt count/status differs")
        memory.append({"arm": arm,
            "baseline_current_rss_kib": summary["baseline_current_rss_kib"],
            "total_process_peak_rss_kib": summary["total_process_peak_rss_kib"],
            "max_visible_numpy_bytes_lower_bound": max(a["visible_arrays"]["max_visible_bytes_at_sample"] for a in attempts),
            "warmup_probe_wall_seconds": attempts[0]["probe_wall_seconds"],
            "measured_probe_wall_seconds": attempts[1]["probe_wall_seconds"],
            "scope": "fresh process peak includes static setup+warmup+measured; probe wall is not ordinary latency"})
    kernel = json.loads((root / "kernel_v2" / "kernel_qualification.json").read_text())
    if kernel["status"] != "all_state_and_llr_parity_passed_before_timing":
        raise ValueError("kernel numerical qualification failed")
    out.mkdir(parents=True)
    write_csv(out / "cells.csv", cells, list(cells[0]))
    write_csv(out / "paired_counts.csv", paired, list(paired[0]))
    write_csv(out / "latency_stage_summary.csv", stages, list(stages[0]))
    write_csv(out / "isolated_memory.csv", memory, list(memory[0]))
    lock = {"schema": "spafdm-pd1q-parta-allocation-lock/1",
            "source_commit": manifest["source_commit"],
            "source_hashes": manifest["source_hashes"],
            "baseline_commit": manifest["baseline_commit"],
            "baseline_source_hashes": manifest["baseline_source_hashes"],
            "e1_manifest_sha256": manifest["e1_manifest_sha256"],
            "e1_run_identity_sha256": manifest["e1_run_identity_sha256"],
            "part_a_run_identity_sha256": json.loads((root / "attribution_v2" / "completion.json").read_text())["run_identity_sha256"],
            "coordinates": manifest["coordinates"], "attribution_calls": 91,
            "isolated_memory_arms": list(MEMORY_ARMS), "isolated_memory_calls": 8,
            "new_radio_observations": 0, "primary_replay_calls_reused_after_score_migration": 3}
    (out / "allocation_lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    full = out / "full_attempt_ledger.jsonl"
    with full.open("w") as handle:
        for row in new:
            handle.write(json.dumps({"scope": "attribution", "record": row}, sort_keys=True) + "\n")
        for arm in MEMORY_ARMS:
            for row in rows(root / "memory" / arm / "ledger.jsonl"):
                handle.write(json.dumps({"scope": "instrumented_isolated_memory", "arm": arm,
                                         "record": row}, sort_keys=True) + "\n")
    failures = [
        {"kind": "qualification_harness_failure", "stage": "kernel_initial",
         "receiver_calls": 0, "receipt": "launch_kernel_failed", "cause": "internal s coordinate compared across domains; fixed harness only"},
        {"kind": "producer_scoring_integrity_failure", "stage": "primary_replay_initial",
         "receiver_calls": 3, "receipt": "launch_replay_failed",
         "cause": "packed truth dict compared directly; original ledger preserved, checkpoint decisions re-signed and rescored offline without receiver rerun"},
    ]
    with (out / "failure_fallback_ledger.jsonl").open("w") as handle:
        for row in failures:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    report = {"schema": "spafdm-pd1q-parta-summary/1", "status": "qualified_and_recounted",
              "attribution_attempts": 91, "isolated_memory_attempts": 8,
              "receiver_calls_total": 99, "new_radio_observations": 0,
              "attribution_complete_seconds_sum": sum(r["seconds"] for r in new),
              "isolated_memory_probe_wall_seconds_sum": sum(
                  a["probe_wall_seconds"] for arm in MEMORY_ARMS
                  for a in rows(root / "memory" / arm / "ledger.jsonl")),
              "memory_probe_scope": "instrumented; excluded from attribution latency",
              "kernel_cases": len(kernel["results"]), "kernel_dense_cases": sum(
                  r["dense_status"] == "qualified_and_timed" for r in kernel["results"]),
              "kernel_median_two_over_four_ratios": [
                  {"n": r["n"], "paths": r["paths"],
                   "ratio": r["median_seconds"]["tensor_free_2fft"] / r["median_seconds"]["competent_4fft"]}
                  for r in kernel["results"]],
              "e1_recount": json.loads((root / "e1_recount.json").read_text()),
              "part_a_recount": json.loads((root / "independent_recount_report.json").read_text()),
              "cells": cells, "paired_counts": paired, "isolated_memory": memory,
              "limitations": ["POINT first8 timing is reused E1 D and last8 new Part A process; mixed-batch latency is descriptive",
                              "isolated memory probe wall includes sys.setprofile and persistence and is not comparable to ordinary receiver latency",
                              "three saved replay calls were rescored offline after producer packed-truth scoring bug; original failed run preserved"]}
    (out / "summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "calls": report["receiver_calls_total"],
                      "files": sorted(p.name for p in out.iterdir())}))


if __name__ == "__main__":
    main()
