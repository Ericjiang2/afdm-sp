#!/usr/bin/env bash
set -euo pipefail

here=$(cd -- "$(dirname -- "$0")" && pwd)
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export TMPDIR=/data/guoyikun/tmp

# Signal the SSH waiter only after the supervisor has written its final receipt.
trap 'tmux wait-for -S gate-sbl-main-finished' EXIT
python -B -u "$here/run_main.py" "$@"
