#!/usr/bin/env bash
set -euo pipefail
set -o noclobber
exec > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/eng-gpu.log 2>&1
trap 'status=$?; printf "%s\n" "$status" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/eng-gpu.exit' EXIT
printf "%s\n" "$$" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/eng-gpu.pid
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/source-v1
export PYTHONPATH=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/source-v1/source
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=GPU-fe13c694-2050-c9f0-2904-b806f6f6b0c2
export TMPDIR=/data/guoyikun/tmp
export TEMP=/data/guoyikun/tmp
export TMP=/data/guoyikun/tmp
export NUMBA_CACHE_DIR=/data/guoyikun/tmp/adjacent-numba
export XDG_CACHE_HOME=/data/guoyikun/tmp/adjacent-cache
export MPLCONFIGDIR=/data/guoyikun/tmp/adjacent-matplotlib
export TORCH_HOME=/data/guoyikun/tmp/adjacent-torch
taskset -c 2 timeout --signal=TERM --kill-after=15s 3599s /home/guoyikun/.conda/envs/AFDM/bin/python -B -m afdm_sp_joint_unrolled.supplement_adjacent_run --manifest /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/source-v1/inputs/run-scope-engineering-v1.json --manifest-sha256 5bd56703217d5bfa52378b5a9cddda2c9103b7c87e4f7b0ffb6794a33c00c0a4 --purpose engineering --out /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/eng-gpu --start 33 --stop 34 --snrs 7 8 9 --repeats 0 1 2 --device cuda:0 --bytes-reserved 2000000000 --deadline-unix 1789140218.863163
