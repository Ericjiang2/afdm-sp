#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")"
commit="${1:?pass the pre-run producing commit}"
out="out/main_20261119"
mkdir "$out"
exec >"$out/run.log" 2>&1
trap 'rc=$?; printf "%s\n" "$rc" >"$out/exit_code"; if (( rc == 0 )); then status=DONE; else status=STOPPED; fi; printf "%s\n" "$status" >"$out/STATUS.pending"; mv "$out/STATUS.pending" "$out/STATUS"; exit "$rc"' EXIT
export TMPDIR="$PWD/$out" PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
# Twelve receiver workers and one coordinator, including a ten-second kill grace.
timeout --kill-after=10s 8250s python -u run_main.py --producing-commit "$commit" \
    --out "$out" --workers 12 --wall-seconds 8250
