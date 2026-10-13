#!/bin/bash
# Forensic: F2-P + hard decision iter convergence sweep.
# Apples-to-apples with H-ablation vanilla data (same ckpt, same seed).
#
# Tests the claim: "iter=5 plateau in paper Fig 6 holds at F2-P config across iter=5..15"
#
# F2-P config (paper-era recipe from QA #25/26):
#   --use-hard --refine-rounds 2 --cand-topm 96
#   --defer-prune-until-final --protect-added 2
#
# Vs H-ablation vanilla baseline: outputs_ablation_H_outer_iter_{3,5,7,10,15}
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s20260509/ckpt_c2rel.pt.force_topk"
COMMON_ARGS=(
  --ckpt "$CKPT"
  --variant C2-rel
  --mp-mode bp --pic-damp 0.5 --p-paths 8
  --tau-spread 0.010 --n-total 1024 --v-mean 2.0
  --snr-list 15 20 25 --frames-per-snr 200
  --fs-factor 4.0 --seed 20260423 --cdtype complex64
  --use-hard --refine-rounds 2 --cand-topm 96
  --defer-prune-until-final --protect-added 2
)

for K in 3 5 7 10 15; do
  OUT="afdm_sp_joint_unrolled/outputs_f2p_iter_${K}"
  mkdir -p "$OUT"
  echo "=== F2-P iter=${K} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${COMMON_ARGS[@]}" \
    --n-outer-iter "$K" \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done
echo "=== F2-P iter sweep complete ==="
