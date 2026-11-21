#!/bin/bash
# Bounded CPU pilot; run from this experiment directory on deinlab.
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_three_mode_20261020
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
OUT=${OUT:-/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1}
mkdir -p "$OUT"
python driver.py --out "$OUT" --shard 0 --gate-only > "$OUT/gate.log" 2>&1
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v c="$(nproc --all)" 'BEGIN{exit !(l+12>c-16)}'; then
  echo 'insufficient spare CPU capacity' >&2; exit 1
fi
pids=()
for shard in $(seq 0 11); do
  python driver.py --out "$OUT" --shard "$shard" --nshard 12 > "$OUT/shard$(printf %03d "$shard").log" 2>&1 &
  pids+=("$!")
done
trap 'kill "${pids[@]}" 2>/dev/null || true' EXIT
status=0
for pid in "${pids[@]}"; do
  wait "$pid" || status=1
done
if (( status != 0 )); then
  echo 'incomplete: at least one shard failed' >&2; exit 1
fi
python aggregate.py --rows "$OUT" --out "$OUT/summary.json" > "$OUT/aggregate.log" 2>&1
trap - EXIT
