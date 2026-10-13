#!/bin/bash
# Ablation E: SP pilot/data power split rho ∈ {0.3, 0.4, 0.5, 0.6, 0.7}
# Eval-only sweep. Trained head was learned at rho=0.5; this characterises
# sensitivity to the SP power split. The classical arm is also impacted —
# both arms see the new rho.
# Total budget: ~75 min wall-clock at canonical config.
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
)

for RHO in 0.3 0.4 0.5 0.6 0.7; do
  TAG="${RHO/./p}"
  OUT="afdm_sp_joint_unrolled/outputs_ablation_E_rho_${TAG}"
  mkdir -p "$OUT"
  echo "=== ablation E rho=${RHO} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    "${COMMON_ARGS[@]}" \
    --rho-override "$RHO" \
    --out "$OUT" 2>&1 | tee "$OUT/run.log"
done
echo "=== ablation E complete ==="
