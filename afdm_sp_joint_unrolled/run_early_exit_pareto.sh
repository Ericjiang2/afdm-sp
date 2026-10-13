#!/bin/bash
# W8 Path A Phase 3 — Pareto curve eval for early-exit gate.
#
# Runs paired_learned_eval at several thresholds τ ∈ {0.1, 0.3, 0.5, 0.7, 0.9},
# plus baseline at τ=∞ (gate off, i.e. fixed iter=10). For each τ records
# avg_iter (gate-driven) and BER vs the canonical TCOM headline.
#
# Output paths: outputs_early_exit_pareto_tau{tau}/results.json
#
# Budget: ~1.5 GPU·h on shared 4090 (5 thresholds × 200 frames × 3 SNRs × ~1
# sec/frame at max-iter=10, possibly less at low τ).
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk"
GATE="afdm_sp_joint_unrolled/outputs_early_exit_gate_v0/gate.json"

EVAL_ARGS=(
  --ckpt "$CKPT"
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
  --n-outer-iter 10
)

# Baseline: gate OFF (full iter=10)
OUT="afdm_sp_joint_unrolled/outputs_early_exit_pareto_baseline_iter10"
mkdir -p "$OUT"
echo "=== baseline (gate OFF, iter=10) -> ${OUT} ==="
python afdm_sp_joint_unrolled/paired_learned_eval.py \
  "${EVAL_ARGS[@]}" \
  --out "$OUT" 2>&1 | tee "$OUT/run.log"

# Sweep thresholds
for TAU in 0.1 0.3 0.5 0.7 0.9; do
  OUT="afdm_sp_joint_unrolled/outputs_early_exit_pareto_tau${TAU}"
  mkdir -p "$OUT"
  echo "=== tau=${TAU} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${EVAL_ARGS[@]}" \
    --early-exit-gate "$GATE" \
    --early-exit-threshold "$TAU" \
    --early-exit-min-iter 2 \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done

echo "=== Pareto sweep complete ==="
