#!/bin/bash
set -u
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-a02-development-v2 || exit 1
export PYTHONPATH=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-a02-development-v2/source
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export CUDA_VISIBLE_DEVICES=GPU-fe13c694-2050-c9f0-2904-b806f6f6b0c2
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp
export TEMP=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp
export TMP=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp
export NUMBA_CACHE_DIR=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp/numba
export MPLCONFIGDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp/matplotlib
export XDG_CACHE_HOME=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/tmp/cache
timeout --signal=TERM --kill-after=15s 1815s /home/guoyikun/.conda/envs/AFDM/bin/python -m afdm_sp_joint_unrolled.supplement_baseline_run --protocol /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-a02-development-v2/inputs/data-protocol.json --checkpoint /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk --out /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-development-098-114 --stage A-02 --a02-protocol /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-a02-development-v2/inputs/a02-development-protocol-v1.json --a02-protocol-sha256 cdd9e6fba5dfaaf20793e9bd218df257b40a59fdfe210000ba7403e480971bf9 --split design --start 98 --stop 114 --snr 8 --max-full-calls 144 --max-output-bytes 4865392640 --deadline-unix 1788970646 --device cuda:0 > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-development-098-114.log 2>&1
printf "%s\n" "$?" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a02-development-098-114.exit
