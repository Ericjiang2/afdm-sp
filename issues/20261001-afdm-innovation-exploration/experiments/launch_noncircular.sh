#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
root=issues/20261001-afdm-innovation-exploration
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/issues/20261001-afdm-innovation-exploration/scratch
export MPLCONFIGDIR="$TMPDIR/matplotlib" XDG_CACHE_HOME="$TMPDIR/cache"
for stage in smoke dev; do
 args=(--project /data/guoyikun/00inbox/AFDM-channel-estimation)
 if [[ "$stage" == smoke ]]; then args+=(--smoke); fi
 set +e
 timeout --kill-after=10s 2760s taskset -c 64 /home/guoyikun/.conda/envs/AFDM/bin/python -u "$root/experiments/run_noncircular.py" "${args[@]}" > "$root/experiments/noncircular_${stage}_v1.log" 2>&1
 code=$?
 printf '%s\n' "$code" > "$root/experiments/noncircular_${stage}_v1.exit"
 set -e
 if [[ "$code" != 0 ]]; then exit "$code"; fi
done
