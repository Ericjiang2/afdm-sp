#!/usr/bin/env bash
# Sweep --tau-lookup across {0, 1, 2, 5, 10} on the canonical ckpt at
# F2-P deployment. Records per-SNR BER for each tau setting; downstream
# pick_best_tau.py picks the per-SNR minimum.
#
# Usage:  bash afdm_sp_joint_unrolled/threshold_gate/run_tau_sweep.sh
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
# Robust conda init for non-interactive bash. Avoids `Run 'conda init'`
# error when ~/.bashrc skips conda hook in non-interactive mode.
eval "$(conda shell.bash hook)"
conda activate AFDM

CKPT="${CKPT:-afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt}"
SEED="${SEED:-20260423}"   # match listwise envelope eval seed → channel realisations identical
OUT_ROOT="${OUT_ROOT:-afdm_sp_joint_unrolled/outputs_threshold_sweep}"

mkdir -p "$OUT_ROOT"

# Uniform tau values to sweep. Starts at 0 (current default) and grows;
# tau >= 10 effectively turns the head into a no-op (logits are all < 10
# at the trained head's bias init -8 plus learned offsets).
# Override via TAUS_STR="0 2 10" env var (space-separated).
TAUS_STR="${TAUS_STR:-0 1 2 5 10}"
read -r -a TAUS <<<"$TAUS_STR"

for tau in "${TAUS[@]}"; do
  out="$OUT_ROOT/tau_${tau}"
  if [ -f "$out/results.json" ]; then
    echo "[skip] $out already has results.json"
    continue
  fi
  mkdir -p "$out"
  echo "=== tau=$tau (uniform across SNRs) ===" | tee "$out/run.log"
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    --ckpt "$CKPT" \
    --variant C2-rel \
    --mp-mode bp --pic-damp 0.5 \
    --p-paths 8 --tau-spread 0.010 \
    --n-total 1024 --v-mean 2.0 --fs-factor 4.0 \
    --snr-list 20 25 30 \
    --frames-per-snr 100 \
    --refine-rounds 2 --cand-topm 96 \
    --defer-prune-until-final --protect-added 2 \
    --tau-lookup "20:${tau},25:${tau},30:${tau}" \
    --seed "$SEED" \
    --cdtype complex64 \
    --out "$out" 2>&1 | tee -a "$out/run.log"
done
echo "[sweep] all done; results in $OUT_ROOT/tau_*/results.json"
