#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_acquisition_performance_20261007
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
trap 'study_exit=$?; printf "%s\n" "$study_exit" > "$study_output/launcher_exit.log"' EXIT
cd source_v1
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
for study_phase in D P A; do
  /usr/bin/time -v python -m experiments.afdm_acquisition_performance_20261007.study --artifact-root "$study_output" --phase "$study_phase"
done
