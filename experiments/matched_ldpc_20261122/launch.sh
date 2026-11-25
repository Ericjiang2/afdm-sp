#!/usr/bin/env bash
set -eo pipefail

experiment_dir=$(cd -- "$(dirname -- "$0")" && pwd)
run_name=${1:?provide a fresh run directory name}
commit=${2:?provide the committed producing revision}
[[ "$run_name" =~ ^[A-Za-z0-9_]+$ && "$commit" =~ ^[a-f0-9]{40}$ ]]
[[ "$experiment_dir" == /data/guoyikun/* ]]
mkdir -p "$experiment_dir/out" /data/guoyikun/tmp
set -o noclobber
exec >"$experiment_dir/out/${run_name}_run.log" 2>&1

export TMPDIR=/data/guoyikun/tmp
export XDG_CACHE_HOME="$experiment_dir/out/.cache"
export MPLCONFIGDIR="$XDG_CACHE_HOME/matplotlib"
export CUDA_VISIBLE_DEVICES=''
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p "$MPLCONFIGDIR"
conda activate AFDM
cd "$experiment_dir/../.."
exec python -B "$experiment_dir/run.py" --out "$experiment_dir/out/$run_name" --commit "$commit" "${@:3}"
