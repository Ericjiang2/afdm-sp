#!/usr/bin/env bash
set -u
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/tmp
export MPLCONFIGDIR=/data/guoyikun/tmp/afdm-mpl-cache
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
/home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/prepare-cost02-prior79-v1.py run --contract-sha256 d862fd326881ea47215431945d5049fe03ffe3ec5cbeee12916493d092b73823 >/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/cost02-prior79-v1.log 2>&1
status=$?
printf '%s\n' "$status" >/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/cost02-prior79-v1.exit
exit "$status"
