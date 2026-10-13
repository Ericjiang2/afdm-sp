#!/usr/bin/env bash
set -u
readonly ROOT="/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/reviewed_pipeline_20260921"
readonly RUN="$EVIDENCE/driver_smoke_v1"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$EVIDENCE/tmp" MPLCONFIGDIR="$EVIDENCE/matplotlib"
export TORCH_HOME="$EVIDENCE/cache" XDG_CACHE_HOME="$EVIDENCE/cache"
cd "$ROOT" || exit 90
/usr/bin/time -v -o "$EVIDENCE/recount.time.txt" \
  "$PYTHON" -B "$EVIDENCE/verify_driver_smoke.py" --source "$ROOT" --run "$RUN" \
  --out "$EVIDENCE/driver_smoke_v1_recount.json" \
  > "$EVIDENCE/recount.stdout.log" 2> "$EVIDENCE/recount.stderr.log"
rc=$?
printf '%s\n' "$rc" > "$EVIDENCE/recount.exit"
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
/usr/bin/time -v -o "$EVIDENCE/fresh_accounting.time.txt" \
  "$PYTHON" -B "$EVIDENCE/verify_fresh_smoke.py" --source "$ROOT" --run "$RUN" \
  --out "$EVIDENCE/driver_smoke_v1_fresh_accounting.json" \
  > "$EVIDENCE/fresh_accounting.stdout.log" 2> "$EVIDENCE/fresh_accounting.stderr.log"
rc=$?
printf '%s\n' "$rc" > "$EVIDENCE/fresh_accounting.exit"
exit "$rc"
