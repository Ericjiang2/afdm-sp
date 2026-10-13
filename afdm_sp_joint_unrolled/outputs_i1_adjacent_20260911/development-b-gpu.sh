#!/usr/bin/env bash
set -euo pipefail
set -o noclobber
exec > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/development-b-gpu.log 2>&1
trap 'status=$?; printf "%s\n" "$status" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/development-b-gpu.exit' EXIT
printf "%s\n" "$$" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/development-b-gpu.pid
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/pool-source-v1
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
taskset -c 3 timeout --signal=TERM --kill-after=15s 7199s /home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/pool-source-v1/supplement_adjacent_pool_run.py --root /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911 --out /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/development-b-gpu --manifest /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/development-b-admission-v1.json --manifest-sha256 b29390e00a612d8074ca12302c5c689607e493649ac1eb3719ad2f737dbce9a2 --device cuda:0 --bytes-reserved 14000000000 --deadline-unix 1789154472.7876925
