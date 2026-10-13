#!/bin/bash
# W8 Path A v2 — short Pareto sweep with gate v2 (6 features + slack=5).
# Only 3 thresholds to validate gate v2 quickly (~1 hr).
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk"
GATE="afdm_sp_joint_unrolled/outputs_early_exit_gate_v2/gate.json"

EVAL_ARGS=(
  --ckpt "$CKPT"
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
  --n-outer-iter 10
)

# baseline_iter10 already exists from v1 — skip rerun.

# Sweep 3 thresholds for v2
for TAU in 0.3 0.5 0.7; do
  OUT="afdm_sp_joint_unrolled/outputs_early_exit_v2_tau${TAU}"
  mkdir -p "$OUT"
  echo "=== v2 tau=${TAU} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${EVAL_ARGS[@]}" \
    --early-exit-gate "$GATE" \
    --early-exit-threshold "$TAU" \
    --early-exit-min-iter 2 \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done

echo "=== v2 short Pareto complete ==="
