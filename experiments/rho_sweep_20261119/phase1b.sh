#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
# 16 workers, coordinator and tracker × (190 + 2)s leaves 144 core-seconds for analysis.
timeout --kill-after=2s 190s "$1" -u phase1b.py --out out/phase1b --workers 16 || {
    status=$?
    echo "STOPPED (exit $status)"
    exit "$status"
}
