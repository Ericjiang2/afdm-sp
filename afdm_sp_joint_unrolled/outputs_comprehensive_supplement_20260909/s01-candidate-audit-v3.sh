#!/usr/bin/env bash
set -u -o noclobber
S01_AUDIT_ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
S01_AUDIT_STEM="$S01_AUDIT_ROOT/s01-candidate-audit-v3"
for suffix in .log .pid .exit; do
    if [ -e "$S01_AUDIT_STEM$suffix" ]; then exit 125; fi
done
if [ -e "$S01_AUDIT_ROOT/s01-candidate-raw-audit-v3" ]; then exit 125; fi
exec > "$S01_AUDIT_STEM.log" 2>&1
trap 'code=$?; printf "%s\n" "$code" > "$S01_AUDIT_STEM.exit"' EXIT
printf '%s\n' "$$" > "$S01_AUDIT_STEM.pid"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR=/data/guoyikun/tmp TEMP=/data/guoyikun/tmp TMP=/data/guoyikun/tmp
export NUMBA_CACHE_DIR=/data/guoyikun/tmp/afdm-numba-cache MPLCONFIGDIR=/data/guoyikun/tmp/afdm-mpl-cache
timeout --signal=TERM --kill-after=15s 3615s \
  /home/guoyikun/.conda/envs/AFDM/bin/python -B \
  "$S01_AUDIT_ROOT/audit-s01-candidates-v3.py" --stage complete
