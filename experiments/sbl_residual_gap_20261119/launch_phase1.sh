#!/usr/bin/env bash
set -euo pipefail

here=$(cd -- "$(dirname -- "$0")" && pwd)
attempt=$1
base_commit=$2
fresh_local=$(realpath -- "$3")
fresh_deinlab=$(realpath -- "$4")
out="$here/out/$attempt"
mkdir -- "$out"
cd -- "$out"

export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
# 8 workers, coordinator, resource tracker. The inventory deadline and two
# attempts at this deadline fit within 1.5 core-hours, including timeout.
finish() {
    status=$?
    trap - EXIT
    printf '%d\n' "$status" > exit_code
    if [[ "$status" == 0 ]]; then
        printf 'DONE\n' > STATUS
    else
        printf 'STOPPED (%d)\n' "$status" > STATUS
    fi
    find . -maxdepth 1 -type f ! -name MD5SUMS.txt -print0 |
        sort -z | xargs -0 md5sum > MD5SUMS.txt
    exit "$status"
}
trap finish EXIT
/usr/bin/time -f 'user_seconds=%U\nsystem_seconds=%S\nwall_seconds=%e' -o cpu_time.txt \
    timeout -k 5s 225s python -B "$here/run_phase1.py" --workers 8 \
    --fresh-local "$fresh_local" --fresh-deinlab "$fresh_deinlab" --out "$out" \
    --model gpt-6.2-sol --base-commit "$base_commit" > run.log 2>&1
