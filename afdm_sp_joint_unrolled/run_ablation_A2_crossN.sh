#!/bin/bash
# Ablation A2: Cross-N zero-shot generalization. Train at N=1024, deploy at
# N ∈ {512, 1024, 2048}. Same ckpt; the cand_active_rel head ingests scalar
# per-candidate features (residual-MF / pilot-MF / pair-coherence) which are
# N-invariant in dimension. Tests: does the head's gain survive N change?
# Wall-clock budget: ~45-90 min total (rate-limited by N=2048 cell which is
# 4× N²-slower than N=512).
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s20260509/ckpt_c2rel.pt.force_topk"
COMMON_ARGS=(
  --ckpt "$CKPT"
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
)

for N in 512 1024 2048; do
  OUT="afdm_sp_joint_unrolled/outputs_ablation_A2_crossN_N${N}"
  mkdir -p "$OUT"
  echo "=== ablation A2 cross-N N=${N} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${COMMON_ARGS[@]}" \
    --n-total "$N" \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done
echo "=== ablation A2 complete ==="
