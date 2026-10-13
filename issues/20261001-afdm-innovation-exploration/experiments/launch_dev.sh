#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
mode="$1"
run_id="$2"
root=issues/20261001-afdm-innovation-exploration
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/issues/20261001-afdm-innovation-exploration/scratch
export MPLCONFIGDIR="$TMPDIR/matplotlib" XDG_CACHE_HOME="$TMPDIR/cache"
args=(--project /data/guoyikun/00inbox/AFDM-channel-estimation --out "$root/experiments/$run_id" --registration "$root/experiments/dev_registration.json")
if [[ "$mode" == qualify ]]; then
 args+=(--qualify)
elif [[ "$mode" == run ]]; then
 args+=(--run --qualification "$root/experiments/qualify_v1")
else
 exit 2
fi
set +e
timeout --kill-after=10s 2760s taskset -c 64 /home/guoyikun/.conda/envs/AFDM/bin/python -u "$root/experiments/run_development.py" "${args[@]}" > "$root/experiments/$run_id.log" 2>&1
exit_code=$?
printf '%s\n' "$exit_code" > "$root/experiments/$run_id.exit"
exit "$exit_code"
