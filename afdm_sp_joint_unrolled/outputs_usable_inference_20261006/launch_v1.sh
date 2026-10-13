#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_usable_inference_20261006
export TMPDIR=/data/guoyikun/tmp
export XDG_CACHE_HOME=/data/guoyikun/tmp/cache
export MPLCONFIGDIR=/data/guoyikun/tmp/matplotlib
export NUMBA_CACHE_DIR=/data/guoyikun/tmp/numba
export TORCH_HOME=/data/guoyikun/tmp/torch
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$MPLCONFIGDIR" "$NUMBA_CACHE_DIR" "$TORCH_HOME"
study_output="$PWD"
cd source_v1
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
stage_args=(--artifact-root "$study_output" --config "$study_output/control/STUDY_CONFIG.json")
study_phase="${1:?algebra, sensitivity, contrast or symmetry required}"
case "$study_phase" in
  algebra|sensitivity|contrast|symmetry) ;;
  *) exit 2 ;;
esac
python -m experiments.afdm_usable_inference_20261006.study "${stage_args[@]}" --phase "$study_phase" --stage "${study_phase}_v1" --wall-seconds 600
