#!/bin/bash
# Extended H sweep: iter ∈ {15, 20} to test whether classical can "catch up"
# to learned iter=10 if given more outer iterations.
# Definitively answers "is learned just trading compute for accuracy?"
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s20260509/ckpt_c2rel.pt.force_topk"
COMMON_ARGS=(
  --ckpt "$CKPT"
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
)

for ITER in 15 20; do
  OUT="afdm_sp_joint_unrolled/outputs_ablation_H_outer_iter_${ITER}"
  mkdir -p "$OUT"
  echo "=== H extended outer_iter=${ITER} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${COMMON_ARGS[@]}" \
    --n-outer-iter "$ITER" \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done
echo "=== H extended complete ==="
