#!/usr/bin/env bash
set -euo pipefail
study_output=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_coherent_structure_20261006
cd "$study_output/source_v1"
export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/cache
export MPLCONFIGDIR=/data/guoyikun/tmp/matplotlib NUMBA_CACHE_DIR=/data/guoyikun/tmp/numba
export TORCH_HOME=/data/guoyikun/tmp/torch PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
python -B -m experiments.afdm_coherent_structure_20261006.audit \
  --artifact-root "$study_output" --config "$study_output/control/STUDY_CONFIG.json" \
  --summary-stage summary_v1 --stage raw_audit_v1 --wall-seconds 1200
