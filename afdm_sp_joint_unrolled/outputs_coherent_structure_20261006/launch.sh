#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_coherent_structure_20261006
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
conda activate AFDM
stage_args=(--artifact-root "$study_output" --config "$study_output/control/STUDY_CONFIG.json")
case "${1:?geometry or cohorts required}" in
  geometry)
    python -m experiments.afdm_coherent_structure_20261006.study "${stage_args[@]}" --phase geometry --stage geometry_v1 --wall-seconds 300
    ;;
  cohorts)
    python - "$study_output" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])/'execution/geometry_v1'
assert json.loads((p/'attempt.json').read_text())['status']=='complete'
assert json.loads((p/'results.json').read_text())['all_passed']
PY
    for condition in 0 1 2 3 4 5; do
      printf -v stage 'calibration_%02d_v1' "$condition"
      python -m experiments.afdm_coherent_structure_20261006.study "${stage_args[@]}" --phase calibration --stage "$stage" --condition "$condition" --wall-seconds 600
    done
    for condition in 0 1 2 3; do
      printf -v stage 'evaluation_%02d_v1' "$condition"
      python -m experiments.afdm_coherent_structure_20261006.study "${stage_args[@]}" --phase evaluation --stage "$stage" --condition "$condition" --wall-seconds 600
    done
    python -m experiments.afdm_coherent_structure_20261006.study "${stage_args[@]}" --phase summary --stage summary_v1 --wall-seconds 300
    ;;
  *) exit 2 ;;
esac
