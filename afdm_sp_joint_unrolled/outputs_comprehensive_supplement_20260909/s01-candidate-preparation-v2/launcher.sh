#!/usr/bin/env bash
set -uo pipefail
set -o noclobber
ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR=/data/guoyikun/tmp MPLCONFIGDIR=/data/guoyikun/tmp/afdm-mpl-cache
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
cd "$ROOT" || exit 90
/home/guoyikun/.conda/envs/AFDM/bin/python -B prepare-s01-candidates-v2.py > s01-candidate-preparation-v2.log 2>&1
code=$?
printf '%s\n' "$code" > s01-candidate-preparation-v2.exit
exit "$code"
