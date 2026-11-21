#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/out"
mkdir -p "$out"

finish() {
    local code=$? status=STOPPED
    if (( code == 0 )); then
        status=DONE
    fi
    printf '%s\n' "$code" > "$out/exit_code"
    printf '%s\n' "$status" > "$out/STATUS"
}
# Keep pre-existing launch evidence if the same output directory is reused.
( set -o noclobber; : > "$out/run.log" )
trap finish EXIT
exec >> "$out/run.log" 2>&1
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=/data/guoyikun/tmp
# Eight single-thread workers and their parent, at most 790 seconds including
# forced termination. This bounds the replay to 1.975 core-hours.
/usr/bin/time -o "$out/cpu_time.txt" -f '%U %S' timeout --kill-after=5s 785s python -B -u "$here/run.py" --out "$out" "$@"
