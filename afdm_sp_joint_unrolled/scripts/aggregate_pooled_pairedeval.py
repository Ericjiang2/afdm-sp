"""Aggregate pooled paired-eval BER for the 4B headline of Section 3 Table tab:ber4b.

Pools the three independent paired-McNemar paired-eval seed blocks at the
canonical operating point (N=1024, P=8, fs=4B, ZC pilot r=7, rho_p=0.5,
F2-P deployment with refine_rounds=2, cand_topm=96, protect_added=2)
and prints the pooled relative BER reductions of LearnedHead vs ClassicalJoint.

The three source JSONs are committed under afdm_sp_joint_unrolled/:
  outputs_loop12_r3_official/results.json        (seed-block A)
  outputs_loop12_seed2_s20_s25_s30/results.json  (seed-block B)
  outputs_loop12_matched_f2p_s20_30/results.json (seed-block C)

Reproduces the headline pooled relative reductions of -37.7/-40.2/-37.6 %
at SNR = 20/25/30 dB to the precision printed in Table tab:ber4b.

Usage:
    python aggregate_pooled_pairedeval.py
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # afdm_sp_joint_unrolled
SOURCES = [
    ROOT / "outputs_loop12_r3_official" / "results.json",
    ROOT / "outputs_loop12_seed2_s20_s25_s30" / "results.json",
    ROOT / "outputs_loop12_matched_f2p_s20_30" / "results.json",
]
SNR_LIST = ["20", "25", "30"]


def main() -> int:
    blocks = []
    for path in SOURCES:
        if not path.exists():
            print(f"[ERR] missing source JSON: {path}", file=sys.stderr)
            return 1
        with open(path) as f:
            blocks.append(json.load(f))

    print(f"# Pooled paired-eval (3 seed blocks)\n")
    print(
        f"| SNR (dB) | "
        f"sum frames | "
        f"sum classical errs | "
        f"sum learned errs | "
        f"pooled rel-Δ |"
    )
    print(f"|---|---:|---:|---:|---:|")
    for snr in SNR_LIST:
        total_frames = sum(b[snr]["frames"] for b in blocks)
        total_cls = sum(b[snr]["classical_errs"] for b in blocks)
        total_lrn = sum(b[snr]["learned_errs"] for b in blocks)
        if total_cls == 0:
            rel_delta = 0.0
        else:
            rel_delta = (total_lrn - total_cls) / total_cls * 100.0
        print(
            f"| {snr} | {total_frames} | {total_cls} | {total_lrn} | "
            f"{rel_delta:+.2f}% |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
