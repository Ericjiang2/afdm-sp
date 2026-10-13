#!/usr/bin/env bash
# One admitted90F quote; source, deadline and reservation are immutable.
set -u -o noclobber
if [ "$#" -ne 2 ]; then exit 64; fi
R=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
COST2_ROOT="$R/source-cost02-full-arm-v2"
COST2_STEM="$R/cost02-full-arm-quote-v1"
for suffix in '' .log .pid .exit; do
    if [ -e "$COST2_STEM$suffix" ]; then exit 125; fi
done
exec > "$COST2_STEM.log" 2>&1
trap 'code=$?; printf "%s\n" "$code" > "$COST2_STEM.exit"' EXIT
printf '%s\n' "$$" > "$COST2_STEM.pid"
cd "$COST2_ROOT" || exit 125
export PYTHONPATH="$COST2_ROOT/source"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export CUDA_VISIBLE_DEVICES=GPU-fe13c694-2050-c9f0-2904-b806f6f6b0c2
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR=/data/guoyikun/tmp TEMP=/data/guoyikun/tmp TMP=/data/guoyikun/tmp
export NUMBA_CACHE_DIR="$R/tmp/numba" MPLCONFIGDIR="$R/tmp/matplotlib" XDG_CACHE_HOME="$R/tmp/cache"
timeout --signal=TERM --kill-after=15s 1815s \
  /home/guoyikun/.conda/envs/AFDM/bin/python -B -m afdm_sp_joint_unrolled.supplement_timing \
  --mode timing-pilot \
  --protocol "$COST2_ROOT/inputs/cost-data-protocol.json" \
  --checkpoint /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk \
  --representative-freeze "$COST2_ROOT/inputs/A02-representatives.json" \
  --representative-freeze-sha256 851bc2de457f63a348473d85d695929a2401f5b9158da7894092d4a134668c38 \
  --global-freeze "$COST2_ROOT/inputs/global-freeze.json" \
  --global-freeze-sha256 0525e450ea290cbbe46809f7f76512e3d8aa2708f5b72c60b214fa029f3cd4eb \
  --timing-manifest "$COST2_STEM-admission.json" \
  --timing-manifest-sha256 "$2" \
  --timing-ledger "$R/cost02-timing-ledger" \
  --out "$COST2_STEM" --deadline-unix "$1" --max-output-bytes 1073741824 --device cuda:0
