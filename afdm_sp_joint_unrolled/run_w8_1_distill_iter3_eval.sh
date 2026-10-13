#!/bin/bash
# W8 #1 Knowledge distillation iter=10 → iter=3.
# The "softlabel" ckpts at outputs_softlabel_train_s2026050{7,8,9} were trained
# with --use-soft-labels (BCE on teacher-iter=10 per-candidate posteriors)
# — that IS distillation training. They were evaluated at iter=5 and iter=10
# but NEVER at iter=3, which is the W8 #1 target.
#
# This script: paired-eval all 3 softlabel ckpts at --n-outer-iter 3.
# Wall-clock: ~30 min total (3 ckpts × 10 min for 200f × 3 SNR at iter=3).
#
# Acceptance gates (per W8 plan §1):
#   D1: student iter=3 BER ≤ 1.2× teacher iter=10 BER at SNR=20
#   D2: student iter=3 beats classical iter=3 by McNemar p<0.05 + ΔBER ≤ -50%
#   D3: 3-seed pool BER within ±20% of teacher iter=10 BER
#
# Baseline to beat: B+ all variant iter=3 unweighted (-55% rel ΔBER vs classical
# iter=3 at SNR=20, per QA #28). Teacher iter=10 canonical = -85.71% (QA #26 pool).
# Distillation target: close 30pp of the (-55%, -85.71%) gap.
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

COMMON_ARGS=(
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --cdtype complex64
  --n-outer-iter 3
)

for SEED in 20260507 20260508 20260509; do
  CKPT="afdm_sp_joint_unrolled/outputs_softlabel_train_s${SEED}/ckpt_c2rel.pt.force_topk"
  OUT="afdm_sp_joint_unrolled/outputs_softlabel_eval_s${SEED}_iter3"
  if [ ! -f "$CKPT" ]; then
    echo "[!! WARN] ckpt not found: $CKPT — skipping seed $SEED"
    continue
  fi
  mkdir -p "$OUT"
  echo "=== W8#1 distill eval seed=${SEED} iter=3 -> ${OUT} ==="
  # Use the same eval-frame seed as the existing iter=5/iter=10 evals for paired comparison.
  EVAL_SEED=20260423
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    --ckpt "$CKPT" \
    --seed "$EVAL_SEED" \
    "${COMMON_ARGS[@]}" \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done
echo "=== W8 #1 distillation iter=3 eval complete ==="
