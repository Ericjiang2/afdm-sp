#!/usr/bin/env bash
set -euo pipefail

here=$(cd -- "$(dirname -- "$0")" && pwd)
attempt=$1
case "${3:-1}" in
    1) runner=run_phase1.py ;;
    1b) runner=run_phase1b.py ;;
    *) printf 'Unknown qualification phase\n' >&2; exit 2 ;;
esac
fresh=$(realpath -- "$2")
cpu_start=$SECONDS
out="$here/out/$attempt"
mkdir -- "$out"
cd -- "$out"

export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
# 7 workers, a coordinator, and a resource tracker. Even if all nine consume
# CPU throughout, the timeout and kill grace total less than 3 core-hours.
finish() {
    status=$?
    trap - EXIT
    printf '%d\n' "$status" > exit_code
    if [[ "$status" == 0 ]]; then
        printf 'DONE (%ds)\n' "$((SECONDS - cpu_start))" > STATUS
    else
        printf 'STOPPED (%d; %ds)\n' "$status" "$((SECONDS - cpu_start))" > STATUS
    fi
    find . -maxdepth 1 -type f ! -name MD5SUMS.txt -print0 |
        sort -z | xargs -0 md5sum > MD5SUMS.txt
    exit "$status"
}
trap finish EXIT

timeout -k 10s 1050s python -B "$here/$runner" \
    --workers 7 --fresh "$fresh" --out "$out" > run.log 2>&1
