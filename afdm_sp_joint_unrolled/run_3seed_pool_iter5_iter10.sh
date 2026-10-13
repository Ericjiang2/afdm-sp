#!/bin/bash
# 3-seed pool re-establishment.
# Eval 3 train seeds (s20260507/508/509) at:
#   * canonical iter=5 (matches Step 3 ablations baseline)
#   * iter=10 (H ablation headline; iter=10 SNR=20 single-seed showed -85.7%)
# Goal: establish multi-seed error bars on the iter=10 headline.
# Total budget: ~1.8 GPU·h on solo 4090.
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

EVAL_ARGS=(
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
)

for SEED in 20260507 20260508 20260509; do
  CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s${SEED}/ckpt_c2rel.pt.force_topk"
  for ITER in 5 10; do
    OUT="afdm_sp_joint_unrolled/outputs_3seed_s${SEED}_iter${ITER}"
    mkdir -p "$OUT"
    echo "=== 3-seed pool seed=${SEED} iter=${ITER} -> ${OUT} ==="
    python afdm_sp_joint_unrolled/paired_learned_eval.py \
      --ckpt "$CKPT" \
      "${EVAL_ARGS[@]}" \
      --n-outer-iter "$ITER" \
      --out "$OUT" 2>&1 | tee "$OUT/run.log"
  done
done
echo "=== 3-seed pool complete ==="
