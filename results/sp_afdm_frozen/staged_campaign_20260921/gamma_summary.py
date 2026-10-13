#!/usr/bin/env python3
"""Derived local report for the four frozen refinement variants; no receiver calls."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np


ARMS = ("ABL_mean", "ABL_scalar", "P_M24_I20", "P_M16_I8")


def describe(values):
    clean = [float(value) for value in values if value is not None]
    return {"count": len(clean), "mean": statistics.mean(clean) if clean else None,
            "median": statistics.median(clean) if clean else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--stage1", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("derived Gamma report already exists")
    sys.path.insert(0, str(args.source / "src"))
    import evidence

    manifest = json.loads((args.stage1 / "manifest.json").read_text())
    rows = [json.loads(line) for line in (args.stage1 / "ledger.jsonl").read_text().splitlines()]
    gate = json.loads((args.stage1 / "stage1_gate.json").read_text())
    if manifest["stage"] != 1 or len(rows) != 260:
        raise ValueError("report requires complete paired Stage 1")
    run_hash = gate["stage1_run_identity_sha256"]
    grouped = {}
    for row in rows:
        arm = row["arm"]
        if arm not in ARMS:
            continue
        if row["status"] != "ok":
            raise ValueError("Gamma comparison has numerical failure; report explicitly")
        cell = row["cell"]
        path = args.stage1 / "compact" / f"c{cell:02d}_f{row['absolute_frame']:06d}_{arm}.npz"
        identity = {"schema": "sp-afdm-staged-compact-v1", "run_identity_sha256": run_hash,
                    "kind": "arm", "cell": cell, "absolute_frame": row["absolute_frame"],
                    "arm": arm}
        payload, _ = evidence.load_artifact(path, identity)
        if evidence.artifact_sha256(path) != row["artifact_sha256"]:
            raise ValueError("Gamma compact artifact hash differs from ledger")
        diag = payload["diagnostics"]
        gamma = diag["ce_gamma"]
        trace = None if gamma is None else complex(np.trace(gamma))
        grouped.setdefault((cell, arm), []).append({
            "absolute_frame": row["absolute_frame"],
            "complete_seconds": row["seconds"], "information_bit_errors": row["info_errors"],
            "channel_nmse": diag["channel_nmse"],
            "gamma_trace_real": None if trace is None else trace.real,
            "gamma_trace_imag": None if trace is None else trace.imag,
            "gamma_offdiag_fro_ratio": diag["ce_gamma_offdiag_fro_ratio"],
            "objective_initial_final": diag["ce_objective_initial_final"],
            "ce_evaluations": diag["ce_evaluations"],
        })
    output = {"schema": "sp-afdm-stage1-gamma-derived-v1",
              "stage1_run_identity_sha256": run_hash,
              "stage1_ledger_sha256": gate["stage1_ledger_sha256"],
              "scope": "Stage 1 exploratory; ABL_mean/ABL_scalar/P_M24_I20 matched M24/I20, P_M16_I8 smaller budget",
              "by_cell_arm": {}}
    for (cell, arm), items in sorted(grouped.items()):
        if len(items) != 10:
            raise ValueError("Gamma arm-cell lacks ten fresh frames")
        output["by_cell_arm"][f"c{cell:02d}:{arm}"] = {
            "cell": cell, "arm": arm, "frames": items,
            "frame_errors": sum(item["information_bit_errors"] > 0 for item in items),
            "information_bit_errors": sum(item["information_bit_errors"] for item in items),
            "information_ber": sum(item["information_bit_errors"] for item in items) / 10240,
            **{name: describe(item[field] for item in items) for name, field in (
                ("complete_seconds", "complete_seconds"),
                ("channel_nmse", "channel_nmse"),
                ("gamma_trace_real", "gamma_trace_real"),
                ("gamma_offdiag_fro_ratio", "gamma_offdiag_fro_ratio"),
                ("ce_evaluations", "ce_evaluations"))},
            "max_abs_gamma_trace_imag": max(abs(item["gamma_trace_imag"] or 0) for item in items),
        }
    args.out.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(f"Gamma derived report: {len(output['by_cell_arm'])} paired arm-cells")


if __name__ == "__main__":
    main()
