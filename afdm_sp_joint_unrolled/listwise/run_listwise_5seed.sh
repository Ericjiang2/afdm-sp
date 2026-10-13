#!/usr/bin/env bash
# run_listwise_5seed.sh — train 5 listwise seeds sequentially.
#
# Closes FYP R3 W-2 (single trained checkpoint, no retraining variance) plus
# R3 W-3 (BCE+rank-hinge train vs top-K_add deploy misalignment) in one pass:
# the 5 seeds give a retraining envelope, and the listwise loss aligns the
# training objective with the deployment top-K ranker.
#
# Per-seed wall: ~25s on RTX 4090 (8 epochs, 27k frames). Total ~2 min.
#
# Usage (run from project root in tmux session g_listwise_5seed):
#   bash afdm_sp_joint_unrolled/listwise/run_listwise_5seed.sh

set -euo pipefail

CACHE=afdm_sp_joint_unrolled/outputs_loop13_4B_cache
LOSS=listnet
EPOCHS=8
PATIENCE=5     # ListNet val_bce is still dropping at ep 8 in trial; high patience.
OUT_BASE=afdm_sp_joint_unrolled/outputs_listwise_5seed

SEEDS=(20260501 20260502 20260503 20260504 20260505)

mkdir -p "$OUT_BASE"
echo "[run_listwise_5seed] cache=$CACHE  loss=$LOSS  epochs=$EPOCHS  out=$OUT_BASE"

for seed in "${SEEDS[@]}"; do
  out="$OUT_BASE/seed_${seed}"
  if [[ -f "$out/ckpt_listwise.pt" ]]; then
    echo "[skip] $out already has a checkpoint"
    continue
  fi
  echo "=========================================="
  echo "[seed=$seed] starting"
  echo "=========================================="
  python afdm_sp_joint_unrolled/listwise/train_listwise.py \
      --cache-dir "$CACHE" \
      --out "$out" \
      --loss "$LOSS" \
      --epochs "$EPOCHS" \
      --patience "$PATIENCE" \
      --seed "$seed"
done

echo "[run_listwise_5seed] all 5 seeds done. ckpt summary:"
for seed in "${SEEDS[@]}"; do
  out="$OUT_BASE/seed_${seed}"
  ber=$(python -c "import json; d=json.load(open('$out/train_log.json')); print(d[-1].get('bce', 'na'))" 2>/dev/null || echo "n/a")
  echo "  seed=$seed  best_bce=$ber  ckpt=$out/ckpt_listwise.pt"
done
