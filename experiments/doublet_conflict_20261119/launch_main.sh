#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/out/main_20261119"
mkdir "$out"

finish() {
    local code=$? status=STOPPED
    if (( code == 0 )); then
        status=DONE
    fi
    printf '%s\n' "$code" > "$out/exit_code"
    printf '%s\n' "$status" > "$out/STATUS"
}
trap finish EXIT
exec > "$out/run.log" 2>&1

export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=/data/guoyikun/tmp
# A 16-worker pool and its parent can use at most 3.944 core-hours in 835 seconds.
timeout --kill-after=5s 830s python -B -u "$here/run_main.py" --out "$out" "$@"
