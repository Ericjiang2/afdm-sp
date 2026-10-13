#!/bin/bash
# Re-eval portion of ablation B-reduced after wrapping ckpts with cand_active_rel prefix.
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

EVAL_ARGS=(
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
)

declare -A MASKS=( ["no_residual_mf"]="no-residual-mf" ["no_pair_coh"]="no-pair-coh" )

for TAG in no_residual_mf no_pair_coh; do
  MASK="${MASKS[$TAG]}"
  CKPT="afdm_sp_joint_unrolled/outputs_ablation_B_train_${TAG}/ckpt_c2rel.pt.force_topk"
  EVAL_OUT="afdm_sp_joint_unrolled/outputs_ablation_B_eval_${TAG}"
  mkdir -p "$EVAL_OUT"
  echo "=== B-reduced EVAL feature_mask=${MASK} ckpt=${CKPT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    --ckpt "$CKPT" \
    "${EVAL_ARGS[@]}" \
    --feature-mask "$MASK" \
    --out "$EVAL_OUT" 2>&1 | tee "$EVAL_OUT/run.log"
done
echo "=== B-reduced eval complete ==="
