#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
# 18 workers, coordinator and tracker × (250 + 2) seconds = 1.40 core-hours.
timeout --kill-after=2s 250s "$1" -u phase1.py --out out/phase1 --workers 18 || {
    status=$?
    echo "STOPPED (exit $status)"
    exit "$status"
}
