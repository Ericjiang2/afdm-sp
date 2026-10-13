#!/usr/bin/env bash
set -euo pipefail
root=/data/guoyikun/afdm_sp_collapsed_20261007_math01_d3b2f1d8
process="$root/artifact/process-COLLAPSED-MATH-01"
mkdir "$process"
exec > "$process/stdout.log" 2>&1
printf '%s\n' "$$" > "$process/pid.txt"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=''
export TMPDIR="$root/runtime/tmp" XDG_CACHE_HOME="$root/runtime/cache" MPLCONFIGDIR="$root/runtime/mpl"
conda activate AFDM
cd "$root/source"
date -u +%FT%TZ > "$process/start.txt"
set +e
/usr/bin/time -v -o "$process/resource.txt" timeout --signal=TERM --kill-after=10 150 python -m experiments.afdm_sp_fractional_receiver_20261007.collapsed_diagnostic --stage COLLAPSED-MATH-01 --artifact-root "$root/artifact"
code=$?
set -e
printf '%s\n' "$code" > "$process/exit.txt"
date -u +%FT%TZ > "$process/end.txt"
exit "$code"
