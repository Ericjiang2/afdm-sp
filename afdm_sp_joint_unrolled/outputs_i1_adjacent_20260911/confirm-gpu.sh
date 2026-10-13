#!/usr/bin/env bash
set -euo pipefail
set -o noclobber
exec > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/confirm-gpu.log 2>&1
trap 'status=$?; printf "%s\n" "$status" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/confirm-gpu.exit' EXIT
printf "%s\n" "$$" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/confirm-gpu.pid
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
taskset -c 2 timeout --signal=TERM --kill-after=15s 25199s /home/guoyikun/.conda/envs/AFDM/bin/python -B -m afdm_sp_joint_unrolled.supplement_adjacent_run --manifest /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/confirmation-admission-v1.json --manifest-sha256 53c573be7793472be19503d38d3abca48bc7233d0232a642aece4023f80f2f58 --purpose confirm --out /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/confirm-gpu --start 0 --stop 2048 --snrs 7 8 9 --repeats 0 --device cuda:0 --bytes-reserved 96000000000 --deadline-unix 1789164639.5521364
