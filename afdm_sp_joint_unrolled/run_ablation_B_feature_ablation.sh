#!/bin/bash
# Ablation B-reduced: feature ablation (train+eval).
# Retrains the C2-rel head with specific feature dims masked, then evaluates
# at canonical config to compare against the all-features baseline.
#
# Three configs:
#   * all (canonical, ckpt already exists at outputs_canonical_grid_s20260509)
#   * no-residual-mf (zero u[..., 0:2] = log_mf, margin)
#   * no-pair-coh (zero v[..., 0:2] = coh, log_alpha_coh)
#
# Total budget: 2 retrains × ~2 min + 2 evals × ~12 min ≈ 30 min wall-clock.
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CACHE="afdm_sp_joint_unrolled/outputs_loop13_4B_cache"
TRAIN_ARGS=(
  --cache-dir "$CACHE"
  --lr 0.001 --batch 512 --epochs 5
  --rank-weight 0.5 --patience 2
  --k-add-max 4 --train-frac 0.9 --seed 20260509
)
EVAL_ARGS=(
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
)

for MASK in no-residual-mf no-pair-coh; do
  TAG="${MASK//-/_}"
  TRAIN_OUT="afdm_sp_joint_unrolled/outputs_ablation_B_train_${TAG}"
  EVAL_OUT="afdm_sp_joint_unrolled/outputs_ablation_B_eval_${TAG}"
  mkdir -p "$TRAIN_OUT" "$EVAL_OUT"

  echo "=== ablation B-reduced TRAIN feature_mask=${MASK} -> ${TRAIN_OUT} ==="
  python afdm_sp_joint_unrolled/loop9_train_c2rel.py \
    "${TRAIN_ARGS[@]}" \
    --out "$TRAIN_OUT" \
    --feature-mask "$MASK" 2>&1 | tee "$TRAIN_OUT/train.log"

  CKPT="$TRAIN_OUT/ckpt_c2rel.pt"
  if [ ! -f "$CKPT" ]; then
    echo "FATAL: ckpt $CKPT not produced; aborting"
    exit 1
  fi

  echo "=== ablation B-reduced EVAL feature_mask=${MASK} -> ${EVAL_OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    --ckpt "$CKPT" \
    "${EVAL_ARGS[@]}" \
    --feature-mask "$MASK" \
    --out "$EVAL_OUT" 2>&1 | tee "$EVAL_OUT/run.log"
done
echo "=== ablation B-reduced complete ==="
