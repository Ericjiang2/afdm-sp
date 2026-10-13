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
/home/guoyikun/.conda/envs/AFDM/bin/python -B -m afdm_sp_joint_unrolled.supplement_scene_candidates --out /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/s01-candidates-v1/batch-000-001 --freeze /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-s01-candidate-v2/inputs/candidate-freeze.json --baseline /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-s01-candidate-v2/inputs/baseline-manifest.json --inputs /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-s01-candidate-v2/inputs --source /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-s01-candidate-v2/source --checkpoint /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk --freeze-sha256 a866501e52f4eaf90476b88c9aaf5fec0e072025a7ac8a01553b39d46c4d997e --baseline-sha256 199dfe315ca0741c1e571ba990646ed38679eb2aa31485997f2c2f652d466399 --device cuda:0 --start 0 --stop 1 --deadline-unix 1789079260 --max-output-bytes 51539607552 > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/s01-candidate-first-v2.log 2>&1
code=$?
printf '%s\n' "$code" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/s01-candidate-first-v2.exit
exit "$code"
