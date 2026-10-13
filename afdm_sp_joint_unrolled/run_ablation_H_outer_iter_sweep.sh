#!/bin/bash
# Ablation H: outer-iter sweep K ∈ {1, 2, 3, 5, 7, 10}
# Runs paired_learned_eval (classical vs learned) at canonical config for each K.
# Total budget: ~60 min wall-clock at fs=4B / N=1024 / 200 frames × 3 SNRs.
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

for K in 1 2 3 5 7 10; do
  OUT="afdm_sp_joint_unrolled/outputs_ablation_H_outer_iter_${K}"
  mkdir -p "$OUT"
  echo "=== ablation H outer_iter=${K} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${COMMON_ARGS[@]}" \
    --n-outer-iter "$K" \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done
echo "=== ablation H complete ==="
