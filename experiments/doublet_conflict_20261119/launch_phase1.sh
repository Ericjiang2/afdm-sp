#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/out/${1:?usage: launch_phase1.sh phase1_attempt_id}"
mkdir -p "$here/out"
mkdir "$out"
finish() {
    code=$?
    printf '%s\n' "$code" > "$out/exit_code"
    if (( code == 0 )); then
        printf 'DONE\n' > "$out/STATUS"
    else
        printf 'STOPPED\n' > "$out/STATUS"
    fi
}
trap finish EXIT
exec > "$out/run.log" 2>&1

export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=/data/guoyikun/tmp
# 16 workers + parent, 200 s with a 5 s KILL grace: at most 3,485 CPU seconds.
timeout --kill-after=5s 200s python "$here/run_phase1.py" --out "$out/receipt"
(
    cd "$out/receipt"
    md5sum *.json *.jsonl > MD5SUMS.txt
)
