#!/usr/bin/env bash
set -euo pipefail

here=$(cd -- "$(dirname -- "$0")" && pwd)
out="$here/out/phase1c_20261119"
fresh_local=$(realpath -- "$1")
fresh_deinlab=$(realpath -- "$2")
mkdir -- "$out"
cd -- "$out"

export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
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
# Eight one-thread workers and their startup helpers, plus the coordinator
# and tracker. The time limit bounds their use below the phase CPU cap.
/usr/bin/time -f 'user_seconds=%U\nsystem_seconds=%S\nwall_seconds=%e' -o cpu_time.txt \
    timeout -k 5s 245s python -B "$here/run_phase1c.py" \
    --fresh-local "$fresh_local" --fresh-deinlab "$fresh_deinlab" --base-commit "$3" > run.log 2>&1
