#!/bin/bash
# Gain-weighted soft-label retrain pipeline.
# Stage 1: re-cache with y_soft field (~3.7 hr).
# Stage 2: retrain 3 seeds (s20260507/508/509) with --use-soft-labels (~15 min total).
# Stage 3: eval each retrained ckpt at canonical iter=5 + iter=10 (~30 min total).
# Total: ~4.5 hr.
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CACHE_OUT="afdm_sp_joint_unrolled/outputs_loop13_4B_cache_softlabels"
mkdir -p "$CACHE_OUT"

# ──────────── Stage 1: re-cache ────────────
echo "=== Stage 1: re-cache with y_soft (4 SNR, 27000 frames total) ==="
python afdm_sp_joint_unrolled/loop9_cache_features.py \
  --n-total 1024 --v-mean 2.0 --p-paths 8 --tau-ms 10.0 --fs-factor 4.0 \
  --M 48 --p-pad 64 \
  --n-10 3000 --n-15 6000 --n-20 6000 --n-25 12000 \
  --seed-base 2026042201 \
  --out "$CACHE_OUT" 2>&1 | tee "$CACHE_OUT/cache.log"
echo "=== Stage 1 complete ==="

# ──────────── Stage 2: retrain 3 seeds ────────────
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
  # Wrap state_dict with cand_active_rel. prefix
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

# ──────────── Stage 3: eval at canonical iter=5 and iter=10 ────────────
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
echo "=== softlabel pipeline DONE ==="
