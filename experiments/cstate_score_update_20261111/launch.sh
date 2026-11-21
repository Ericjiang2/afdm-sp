#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
code=$(cd "$(dirname "$0")" && pwd)
out=${1:-afdm_sp_joint_unrolled/outputs_cstate_score_update_20261111}
py=/home/guoyikun/.conda/envs/AFDM/bin/python
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES="" PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$PWD/$out/mpl" TMPDIR="$PWD/$out/tmp"
mkdir "$TMPDIR"
start=$SECONDS
trap 'rc=$?; printf "%s exit=%s wall_s=%s\n" "$([ "$rc" = 0 ] && echo DONE || echo STOPPED)" "$rc" "$((SECONDS-start))" > "$out/STATUS.txt"' EXIT
sha256sum "$code"/*.py "$code/launch.sh" "$code/PROTOCOL.md" experiments/tf_cstate_e1_20261017/out/select/triggered_keys.json > "$out/SOURCES.txt"
"$py" "$code/replay.py" "$out" --gate
workers=()
for ((i=0; i<12; i++)); do
    timeout --kill-after=10s 7m "$py" "$code/replay.py" "$out" --shard "$i" --shards 12 > "$out/worker-$i.log" 2>&1 &
    workers+=("$!")
done
failed=0
for pid in "${workers[@]}"; do
    wait "$pid" || failed=1
done
if ((failed)); then exit 1; fi
"$py" "$code/replay.py" "$out" --summarize
md5sum "$out"/rows-*.jsonl > "$out/RAW_MD5.txt"
