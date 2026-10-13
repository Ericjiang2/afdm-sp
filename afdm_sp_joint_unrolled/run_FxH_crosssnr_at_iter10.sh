#!/bin/bash
# F × H crossover: cross-SNR generalisation at the H-headline iter=10 setting.
# Verifies the iter=10 -85.7% / -33.4% headline at SNR=20/15 propagates to OOD-low (5, 10) and OOD-high (25, 30).
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s20260509/ckpt_c2rel.pt.force_topk"
OUT="afdm_sp_joint_unrolled/outputs_FxH_crosssnr_iter10"
mkdir -p "$OUT"
python afdm_sp_joint_unrolled/paired_learned_eval.py \
  --ckpt "$CKPT" \
  --variant C2-rel \
  --mp-mode bp --pic-damp 0.5 --p-paths 8 \
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0 \
  --snr-list 5 10 15 20 25 30 --frames-per-snr 200 \
  --fs-factor 4.0 --seed 20260423 --cdtype complex64 \
  --n-outer-iter 10 \
  --out "$OUT" 2>&1 | tee "$OUT/run.log"
echo "=== F×H crossover complete ==="
