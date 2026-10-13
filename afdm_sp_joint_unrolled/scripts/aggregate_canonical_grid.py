"""Aggregate the 3 train-seed x 3 eval-seed canonical-head retraining grid.

Reads outputs_canonical_grid/t{tseed}_e{eseed}/results.json for
tseed in {20260507, 20260508, 20260509}, eseed in {20260423, 20260424, 20260425},
SNR in {20, 25, 30}. Reports per-cell rel-Δ%, per-train-seed pool across
3 eval seeds, and cross-train-seed mean ± std at each SNR. Pooled McNemar
n10/n01 sums are produced alongside.

Usage:
    python aggregate_canonical_grid.py
"""
from __future__ import annotations
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # afdm_sp_joint_unrolled
GRID_ROOT = ROOT / "outputs_canonical_grid"
TRAIN_SEEDS = [20260507, 20260508, 20260509]
EVAL_SEEDS = [20260423, 20260424, 20260425]
SNRS = ["20", "25", "30"]


def main() -> int:
    grid = {}  # grid[tseed][eseed][snr] = row dict
    for ts in TRAIN_SEEDS:
        grid[ts] = {}
        for es in EVAL_SEEDS:
            jp = GRID_ROOT / f"t{ts}_e{es}" / "results.json"
            if not jp.exists():
                print(f"[ERR] missing {jp}", file=sys.stderr)
                return 1
            with open(jp) as f:
                grid[ts][es] = json.load(f)

    # Per-cell summary
    print("# Per-cell rel-Δ% (learned vs classical)")
    print("| train_seed | eval_seed | SNR | frames | cls_errs | lrn_errs | rel-Δ% |")
    print("|---|---|---|---:|---:|---:|---:|")
    for ts in TRAIN_SEEDS:
        for es in EVAL_SEEDS:
            for snr in SNRS:
                r = grid[ts][es].get(snr)
                if r is None:
                    continue
                cls = r.get("classical_errs", 0)
                lrn = r.get("learned_errs", 0)
                f_ = r.get("frames", 0)
                if cls == 0:
                    rel = float("nan")
                    rel_str = "—"
                else:
                    rel = (lrn - cls) / cls * 100.0
                    rel_str = f"{rel:+.2f}%"
                print(f"| {ts} | {es} | {snr} | {f_} | {cls} | {lrn} | {rel_str} |")
    print()

    # Per-train-seed pool across 3 eval seeds
    print("# Per-train-seed pooled rel-Δ (across 3 eval seeds)")
    print("| train_seed | SNR | sum_frames | sum_cls | sum_lrn | pooled rel-Δ% | pool_n10 | pool_n01 |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    per_ts_per_snr = {}
    for ts in TRAIN_SEEDS:
        per_ts_per_snr[ts] = {}
        for snr in SNRS:
            sum_f = 0
            sum_c = 0
            sum_l = 0
            sum_n10 = 0
            sum_n01 = 0
            for es in EVAL_SEEDS:
                r = grid[ts][es].get(snr, {})
                sum_f += r.get("frames", 0)
                sum_c += r.get("classical_errs", 0)
                sum_l += r.get("learned_errs", 0)
                sum_n10 += r.get("mcnemar_n10", 0) or 0
                sum_n01 += r.get("mcnemar_n01", 0) or 0
            rel = (sum_l - sum_c) / sum_c * 100.0 if sum_c else float("nan")
            per_ts_per_snr[ts][snr] = rel
            print(f"| {ts} | {snr} | {sum_f} | {sum_c} | {sum_l} | {rel:+.2f}% | {sum_n10} | {sum_n01} |")
    print()

    # Cross-train-seed mean ± std at each SNR
    print("# Cross-train-seed mean ± std rel-Δ% (at each SNR)")
    print("| SNR | mean rel-Δ% | std | range |")
    print("|---|---:|---:|---:|")
    for snr in SNRS:
        vals = [per_ts_per_snr[ts][snr] for ts in TRAIN_SEEDS if not math.isnan(per_ts_per_snr[ts][snr])]
        if not vals:
            print(f"| {snr} | — | — | — |")
            continue
        m = sum(vals) / len(vals)
        v = sum((x - m) ** 2 for x in vals) / max(len(vals) - 1, 1)
        s = math.sqrt(v)
        rng = max(vals) - min(vals)
        print(f"| {snr} | {m:+.2f}% | {s:.2f} | {rng:.2f} |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
