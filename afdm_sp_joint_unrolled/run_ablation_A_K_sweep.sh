#!/bin/bash
# Ablation A: K-sweep K ∈ {1, 2, 3, 4, 6, 8} for the learned head's k_add_max cap.
# Eval-only; the trained ckpt's k_add_max is overridden at inference time.
# K=4 is the canonical trained value (baked into the ckpt).
# Total budget: ~50 min wall-clock at canonical config.
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

for K in 1 2 3 4 6 8; do
  OUT="afdm_sp_joint_unrolled/outputs_ablation_A_kaddmax_${K}"
  mkdir -p "$OUT"
  echo "=== ablation A k_add_max=${K} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${COMMON_ARGS[@]}" \
    --k-add-max-override "$K" \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done
echo "=== ablation A complete ==="
