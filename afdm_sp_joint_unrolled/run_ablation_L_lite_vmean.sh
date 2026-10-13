#!/bin/bash
# Ablation L-lite: off-grid Doppler robustness via v_mean sweep.
# Trained ckpt was learned at v_mean=2.0 m/s; deployment at higher v_mean
# pushes Doppler bins further off-grid (Dirichlet kernel sidelobes broaden).
# v=2 is the canonical baseline (already covered by ablation F at SNR ∈ {15,20,25}).
# v=4 and v=8 are the "mismatch" severities.
# Total budget: ~30 min wall-clock.
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s20260509/ckpt_c2rel.pt.force_topk"
COMMON_ARGS=(
  --ckpt "$CKPT"
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
)

for VMEAN in 2.0 4.0 8.0; do
  TAG="${VMEAN/./p}"
  OUT="afdm_sp_joint_unrolled/outputs_ablation_L_lite_vmean_${TAG}"
  mkdir -p "$OUT"
  echo "=== ablation L-lite v_mean=${VMEAN} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${COMMON_ARGS[@]}" \
    --v-mean "$VMEAN" \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done
echo "=== ablation L-lite complete ==="
