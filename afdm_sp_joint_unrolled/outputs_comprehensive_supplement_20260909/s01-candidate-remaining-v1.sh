#!/usr/bin/env bash
set -uo pipefail
set -o noclobber
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-s01-candidate-v2 || exit 90
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TMPDIR=/data/guoyikun/tmp
export TEMP=/data/guoyikun/tmp
export TMP=/data/guoyikun/tmp
export MPLCONFIGDIR=/data/guoyikun/tmp/afdm-mpl-cache
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-s01-candidate-v2/source
/home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/continue-s01-candidates-v1.py run > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/s01-candidate-remaining-v1.log 2>&1
code=$?
printf '%s\n' "$code" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/s01-candidate-remaining-v1.exit
exit "$code"
