#!/bin/bash
set -u
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909 || exit 1
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp
export TMP=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp
export TEMP=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp
export MPLCONFIGDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp/matplotlib
export XDG_CACHE_HOME=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp/cache
export NUMBA_CACHE_DIR=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp/numba
timeout --signal=TERM --kill-after=15s 9300s /home/guoyikun/.conda/envs/AFDM/bin/python /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/run-a02-development-remaining-v1.py --plan /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-remaining-development-resource-v1.json --plan-sha256 afa3f2e9abab4cadf64a03a057cd88fe10ecd71cdb4fe6785fe67f915d41fa5e --first-audit /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-first-raw-audit-v2.json --first-audit-sha256 e2a3099aca18be6a324a93de3ce62fd90a767d77644a4d18c36bc8f25b03a76f --launcher-sha256 083e71a7d45c0701a7955b06bbe89c7546cdeebaa9ab07a7d9e7d1566c62cd48 --auditor-sha256 86188c27a053982cf6ec4762b117ee238bf6ad84a3ed84a92caeadf24206545e > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-development-remaining-controller-v1.log 2>&1
printf "%s\n" "$?" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-development-remaining-controller-v1.exit
