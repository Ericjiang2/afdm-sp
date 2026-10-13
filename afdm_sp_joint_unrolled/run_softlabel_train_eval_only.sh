#!/bin/bash
# Re-launch Stage 2 (retrain) + Stage 3 (eval) only — cache already done.
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CACHE_OUT="afdm_sp_joint_unrolled/outputs_loop13_4B_cache_softlabels"

echo "=== Stage 2: retrain 3 seeds with --use-soft-labels ==="
for SEED in 20260507 20260508 20260509; do
  TRAIN_OUT="afdm_sp_joint_unrolled/outputs_softlabel_train_s${SEED}"
  mkdir -p "$TRAIN_OUT"
  echo "  --- train seed=${SEED} ---"
  python afdm_sp_joint_unrolled/loop9_train_c2rel.py \
    --cache-dir "$CACHE_OUT" \
    --out "$TRAIN_OUT" \
    --lr 0.001 --batch 512 --epochs 5 \
    --rank-weight 0.5 --patience 2 \
    --k-add-max 4 --train-frac 0.9 --seed "$SEED" \
    --use-soft-labels 2>&1 | tee "$TRAIN_OUT/train.log"
  python - <<PYEOF
import torch
src = "$TRAIN_OUT/ckpt_c2rel.pt"
dst = src + ".force_topk"
ck = torch.load(src, map_location="cpu", weights_only=False)
ck["state_dict"] = {f"cand_active_rel.{k}": v for k, v in ck["state_dict"].items()}
torch.save(ck, dst)
print(f"wrapped -> {dst}")
PYEOF
done
echo "=== Stage 2 complete ==="

echo "=== Stage 3: eval each ckpt at iter ∈ {5, 10} ==="
for SEED in 20260507 20260508 20260509; do
  CKPT="afdm_sp_joint_unrolled/outputs_softlabel_train_s${SEED}/ckpt_c2rel.pt.force_topk"
  for ITER in 5 10; do
    EVAL_OUT="afdm_sp_joint_unrolled/outputs_softlabel_eval_s${SEED}_iter${ITER}"
    mkdir -p "$EVAL_OUT"
    echo "  --- eval seed=${SEED} iter=${ITER} ---"
    python afdm_sp_joint_unrolled/paired_learned_eval.py \
      --ckpt "$CKPT" --variant C2-rel \
      --mp-mode bp --pic-damp 0.5 --p-paths 8 \
      --tau-spread 0.010 --n-total 1024 --v-mean 2.0 \
      --snr-list 15 20 25 --frames-per-snr 200 \
      --fs-factor 4.0 --seed 20260423 --cdtype complex64 \
      --n-outer-iter "$ITER" \
      --out "$EVAL_OUT" 2>&1 | tee "$EVAL_OUT/run.log"
  done
done
echo "=== Stage 3 complete ==="
