#!/bin/bash
# 3-seed pool with F2-P flags — apples-to-apples vs run_3seed_pool_iter5_iter10.sh.
#
# Question: does F2-P (--refine-rounds 2 --cand-topm 96 --defer-prune-until-final
# --protect-added 2 + --use-hard) improve over the vanilla TCOM headline?
#
# Existing vanilla 3-seed pool (run_3seed_pool_iter5_iter10.sh, QA #22):
#   iter=5  -4.10% pooled   |  iter=10 -85.71% pooled (cross-seed std ≤ 5.6e-6)
#
# Hypothesis: F2-P at iter=10 may beat -85.71% (FYP F2-P at iter=5 gave -48% vs
# vanilla iter=5 only -7.84%; the F2-P contribution might compound with iter).
#
# Total budget: ~3-4 GPU·h on solo 4090 (F2-P refine adds work per frame).
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

# IDENTICAL to vanilla launcher except F2-P + use-hard added:
EVAL_ARGS=(
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
  # F2-P (paper-era) flag bundle:
  --use-hard
  --refine-rounds 2 --cand-topm 96
  --defer-prune-until-final --protect-added 2
)

for SEED in 20260507 20260508 20260509; do
  CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s${SEED}/ckpt_c2rel.pt.force_topk"
  for ITER in 5 10; do
    OUT="afdm_sp_joint_unrolled/outputs_3seed_F2P_s${SEED}_iter${ITER}"
    mkdir -p "$OUT"
    echo "=== 3-seed F2-P pool seed=${SEED} iter=${ITER} -> ${OUT} ==="
    python afdm_sp_joint_unrolled/paired_learned_eval.py \
      --ckpt "$CKPT" \
      "${EVAL_ARGS[@]}" \
      --n-outer-iter "$ITER" \
      --out "$OUT" 2>&1 | tee "$OUT/run.log"
  done
done
echo "=== 3-seed F2-P pool complete ==="
