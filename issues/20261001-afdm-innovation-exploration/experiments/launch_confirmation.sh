#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
root=issues/20261001-afdm-innovation-exploration
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/issues/20261001-afdm-innovation-exploration/scratch
export MPLCONFIGDIR="$TMPDIR/matplotlib" XDG_CACHE_HOME="$TMPDIR/cache"
for stage in generate receive; do
 set +e
 timeout --kill-after=10s 2760s taskset -c 64 /home/guoyikun/.conda/envs/AFDM/bin/python -u "$root/experiments/run_confirmation.py" --project /data/guoyikun/00inbox/AFDM-channel-estimation --"$stage" > "$root/experiments/confirmation_$stage.log" 2>&1
 exit_code=$?
 printf '%s\n' "$exit_code" > "$root/experiments/confirmation_$stage.exit"
 set -e
 if [[ "$exit_code" != 0 ]]; then exit "$exit_code"; fi
done
