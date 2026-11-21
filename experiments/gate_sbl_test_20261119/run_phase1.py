"""Run only archived controls and smoke qualification for the draft gate test."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
import multiprocessing
import os
from pathlib import Path
import platform
import re
from statistics import mean
import subprocess
import sys

import numpy as np
import scipy

import s_gates
from gate_verdict import paired_interval

HERE = Path(__file__).resolve().parent
THREADS = ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS",
           "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
S_BUDGET = 25.0
COST_FACTOR = 1.3


def fresh_receipts(local, remote):
    audits = {}
    for scope, path in (("local", local), ("deinlab", remote)):
        raw = path.read_bytes()
        receipt = json.loads(raw)
        if (receipt["scope"] != scope or receipt["status"] != "PASS"
                or receipt["S"]["interval_inclusive"] != [5800, 6199]
                or receipt["S"]["base_interval_inclusive"] != [5800, 5999]
                or receipt["S"]["base_status"] != "PASS"
                or receipt["X"]["interval_inclusive"] != [1600, 2199]
                or receipt["X"]["status"] != "PASS"):
            raise ValueError(f"Unqualified fresh-frame audit: {scope}")
        audits[scope] = dict(sha256=sha256(raw).hexdigest(), S=receipt["S"]["status"],
                             S_base=receipt["S"]["base_status"], X=receipt["X"]["status"])
    return audits


def archive_leverage(rows):
    keys = sorted(rows)
    differences = []
    for key in keys:
        variants = rows[key]["variants"]
        scores = [variants[arm] for arm in ("S-isolo", "S-lo")]
        if any(score["fer"] != int(score["info_errors"] > 0) for score in scores):
            raise s_gates.FrozenEvidenceError(f"Invalid archived FER inputs: {key}")
        differences.append(scores[0]["fer"] - scores[1]["fer"])
    result = paired_interval(differences, [key[3] for key in keys])
    half_width = result["ci_width"] / 2
    return dict(result, contrast="S-isolo minus S-lo", keys=len(keys),
                isolo_only=differences.count(1), slo_only=differences.count(-1),
                half_width_2400_pp=100 * half_width, projected_half_width_4800_pp=100 * half_width / 2**.5)


def projection(s_seconds, x_cost, audits):
    per_key = mean(s_seconds)
    s_4800 = COST_FACTOR * per_key * 4800 / 3600
    s_2400 = COST_FACTOR * per_key * 2400 / 3600
    x_600 = x_cost["projected_600_core_hours_x1p3"]
    full_fresh = all(audit["S"] == "PASS" for audit in audits.values())
    total_full = s_4800 + x_600
    total_base = s_2400 + x_600
    block = None
    if full_fresh and total_full <= S_BUDGET:
        block = [5800, 6199]
    elif total_base <= S_BUDGET:
        block = [5800, 5999]
    return dict(multiplier=COST_FACTOR, core_hour_limit=S_BUDGET,
                measured_s_cpu_seconds=s_seconds, measured_s_keys=len(s_seconds) // 2,
                s_seconds_per_key=per_key, x_measurement=x_cost,
                s_core_hours_4800=s_4800, s_core_hours_2400=s_2400, x_core_hours_600=x_600,
                total_core_hours_4800=total_full, total_core_hours_2400=total_base,
                s_full_audit_passed=full_fresh, selected_s_frame_block=block,
                selected_x_frame_block=[1600, 2199] if block else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fresh-local", type=Path, required=True)
    parser.add_argument("--fresh-deinlab", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--model", choices=["gpt-6.2-sol"], required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.parent != HERE / "out" or not out.name.startswith("phase1_"):
        raise ValueError("Output must be a Phase 1 directory under the experiment out/")
    if platform.system() != "Linux" or not re.fullmatch(r"[a-f0-9]{40}", args.base_commit):
        raise ValueError("Phase 1 requires deinlab Linux and a full base commit")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or any(os.environ.get(v) != "1" for v in THREADS):
        raise ValueError("Phase 1 requires CPU-only one-thread processes")

    audits = fresh_receipts(args.fresh_local, args.fresh_deinlab)
    workers = 8
    config = dict(_argv=sys.argv, _config=dict(phase=1, model=args.model, base_commit=args.base_commit,
                  workers=workers, threads_per_process=1, fresh_audits=audits,
                  platform=platform.platform(), python=sys.version, numpy=np.__version__,
                  scipy=scipy.__version__, source_sha256={
                      path.name: sha256(path.read_bytes()).hexdigest()
                      for path in sorted(HERE.glob("*.py"))
                  }))
    s_gates.write_json(out, "config.json", config)
    rows, provenance = s_gates.load_archive()
    leverage = archive_leverage(rows)
    s_gates.write_json(out, "leverage.json", leverage)
    # SBL imports additional frozen geometry modules. MIXED8 must load in a
    # fresh interpreter to reproduce the original loaded-source inventory.
    print("MIXED8 G2/G5: archived frames 1000–1019", flush=True)
    subprocess.run([sys.executable, "-B", "-u", str(HERE / "x_gates.py"), str(out)], check=True)
    x = json.loads((out / "x_qualification.json").read_text())
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        s = s_gates.run(pool, rows, provenance, out)

    cost = projection(s["smoke_cpu_seconds"], x["cost"], audits)
    s_gates.write_json(out, "cost.json", cost)
    s_gates.write_json(out, "results.json", dict(
        **config, audits=audits, s_archive=provenance, x_archive=x["source"],
        leverage=leverage, cost=cost, gates={
            "G1": "sbl_g1.json", "G2": ["sbl_g2.json", "x_g2.json"],
            "G3": "sbl_g3.json", "G4": "sbl_g4.json", "G5": "x_g5.json",
        }))
    if cost["selected_s_frame_block"] is None:
        raise RuntimeError("The audited S block and X leg exceed the 25-core-hour cap")


if __name__ == "__main__":
    main()
