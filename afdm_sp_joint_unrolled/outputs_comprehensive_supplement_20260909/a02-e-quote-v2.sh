#!/bin/bash
set -u
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-a02-e-quote-v2 || exit 1
export PYTHONPATH=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-a02-e-quote-v2/source
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp
export MPLCONFIGDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp/matplotlib
export XDG_CACHE_HOME=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp/cache
timeout --signal=TERM --kill-after=15s 2715s /home/guoyikun/.conda/envs/AFDM/bin/python -m afdm_sp_joint_unrolled.supplement_bridge_quote --input-manifest /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-a02-e-quote-v2/inputs/a02-e-quote-cache-bindings-v1.json --input-manifest-sha256 81093a39359cedc21f924932b9d21dfa2101fb904bc28a8ec520f5b81be6f3b0 --out /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-e-quote-v2 --deadline-unix 1788966822 --device cpu > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-e-quote-v2.log 2>&1
printf "%s\n" "$?" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-e-quote-v2.exit
