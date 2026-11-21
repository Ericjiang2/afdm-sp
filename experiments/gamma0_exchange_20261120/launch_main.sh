#!/usr/bin/env bash
set -Eeuo pipefail
set -o noclobber
code=$(cd "$(dirname "$0")" && pwd)
out="$code/out/main_20261120"
python=/home/guoyikun/.conda/envs/AFDM/bin/python

if [[ $# != 2 || -e "$out/run.log" || -e "$out/STATUS" ]]; then
    echo "Expected freeze and producing revisions, with an unused output directory" >&2
    exit 2
fi

finish() {
    local result=$? status
    trap - EXIT
    case "$result" in
        0) status="DONE" ;;
        124) status="STOPPED: wall clock deadline" ;;
        137) status="STOPPED: process killed at a resource limit or by SIGKILL" ;;
        *) status="STOPPED: exit $result ($(tail -n 1 "$out/run.log"))" ;;
    esac
    printf '%s\n' "$status" > "$out/STATUS.tmp"
    mv "$out/STATUS.tmp" "$out/STATUS"
    tmux wait-for -S gamma0-main-20261120
    exit "$result"
}
trap finish EXIT

export CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/cache_headroom
export MPLCONFIGDIR="$XDG_CACHE_HOME" TORCH_HOME="$XDG_CACHE_HOME"
exec > "$out/run.log" 2>&1
cd "$code"
timeout --kill-after=5s 1795s "$python" -B -u "$code/run_main.py" --out "$out" \
    --freeze-revision "$1" --producing-revision "$2"
