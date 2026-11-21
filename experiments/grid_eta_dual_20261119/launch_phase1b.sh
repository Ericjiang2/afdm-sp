#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
out="$PWD/out/$1"
mkdir -- "$out"
export COPYFILE_DISABLE=1 CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
finish() {
    status=$?
    if [[ "$status" == 0 ]]; then
        printf 'DONE\n' > "$out/STATUS"
    else
        printf 'STOPPED (%s)\n' "$status" > "$out/STATUS"
    fi
}
trap finish EXIT
# At most ten Python processes. The 450-second ceiling is at most 1.25 core-hours.
/usr/bin/time -f 'user_seconds=%U\nsystem_seconds=%S\nwall_seconds=%e' -o "$out/cpu_time.txt" \
    timeout -k 5s 445s /home/guoyikun/.conda/envs/AFDM/bin/python -B phase1b.py \
    --out "$out" --base-commit "$2" --model "$3" > "$out/run.log" 2>&1
