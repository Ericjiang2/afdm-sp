#!/usr/bin/env bash
set -euo pipefail

here=$(cd -- "$(dirname -- "$0")" && pwd)
attempt=$1
commit=$2
fresh_local=$(realpath -- "$3")
fresh_deinlab=$(realpath -- "$4")
seconds=$5
[[ $attempt == phase1_* && $attempt != */* && $seconds =~ ^[1-9][0-9]*$ && $seconds -le 540 ]]
out="$here/out/$attempt"
mkdir -- "$out"
cd -- "$out"

export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export TMPDIR=/data/guoyikun/tmp

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
# Eight workers, a coordinator and a resource tracker: at most 10 CPU threads.
# At the maximum deadline the qualification can charge at most 1.52 core-hours.
python -B -m unittest discover -s "$here" -p test_verdict.py -v > verdict_tests.log 2>&1
/usr/bin/time -f 'user_seconds=%U\nsystem_seconds=%S\nwall_seconds=%e' -o cpu_time.txt \
    timeout -k 5s "${seconds}s" python -B -u "$here/run_phase1.py" --out "$out" \
    --fresh-local "$fresh_local" --fresh-deinlab "$fresh_deinlab" \
    --model gpt-6.2-sol --base-commit "$commit" > run.log 2>&1
