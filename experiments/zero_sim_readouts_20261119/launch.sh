#!/usr/bin/env bash
set -euo pipefail
umask 077
here=$(cd -- "$(dirname -- "$0")" && pwd)
base=$(dirname -- "$here")
out="$here/out"
exec > "$out/run.log" 2>&1
finish() {
    local status=$?
    if [[ ! -f "$out/STATUS" ]]; then
        echo "STOPPED exit=$status" | tee "$out/STATUS"
    fi
}
trap finish EXIT
export TMPDIR=/data/guoyikun/tmp CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
/home/guoyikun/.conda/envs/AFDM/bin/python -u "$here/run.py" --out "$out" \
    --admission-source /data/guoyikun/tmp/admission-law-main-8d7afd0a71d3 \
    --admission-archive "$base/admission_law_20261118/out/main_20261118" \
    --slot-archive "$base/slot_mismatch_20261019/out/main_20261118" \
    --frozen-slot /data/guoyikun/tmp/slotmm-9b633ce9df02/experiments/slot_mismatch_20261019
