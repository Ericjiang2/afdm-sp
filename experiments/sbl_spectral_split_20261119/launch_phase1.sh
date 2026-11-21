#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")"
out="out/${1:?pass a new attempt directory name}"
[[ "$(dirname "$out")" == out && "${out##*/}" != '..' ]]
mkdir -p out
mkdir "$out"
exec >"$out/run.log" 2>&1
trap 'rc=$?; printf "%s\n" "$rc" >"$out/exit_code"; exit "$rc"' EXIT
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export TMPDIR="$PWD/$out"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
timeout --kill-after=10s 35m python -u phase1.py --out "$out" --workers 12
