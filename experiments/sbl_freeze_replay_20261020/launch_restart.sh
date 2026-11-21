#!/bin/bash
# One bounded CPU-only RP extension, including representative engineering gates.
set -euo pipefail
if [[ ${RP_BOUNDED:-0} != 1 ]]; then
  export RP_BOUNDED=1
  exec timeout --kill-after=5s 845s bash "$0"
fi
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_freeze_replay_20261020
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
OLD=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2
OUT=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/restart_point1
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v c="$(nproc --all)" 'BEGIN{exit !(l+12>c-16)}'; then
  echo 'insufficient spare CPU capacity' >&2; exit 1
fi
mkdir "$OUT"
python restart_point.py --old-rows "$OLD" --out "$OUT" --shard 0 --gate-only > "$OUT/gate.log" 2>&1
pids=()
trap 'kill "${pids[@]}" 2>/dev/null || true' EXIT
for shard in $(seq 0 11); do
  python restart_point.py --old-rows "$OLD" --out "$OUT" --shard "$shard" > "$OUT/shard$(printf %03d "$shard").log" 2>&1 &
  pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do
  wait "$pid" || status=1
done
if (( status != 0 )); then
  echo 'incomplete: at least one RP shard failed' >&2; exit 1
fi
python aggregate_restart.py --old-rows "$OLD" --rows "$OUT" --out "$OUT/summary.json" > "$OUT/aggregate.log" 2>&1
trap - EXIT
