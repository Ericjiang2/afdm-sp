#!/usr/bin/env bash
set -u
R=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
export TMPDIR="$R/tmp" TEMP="$R/tmp" TMP="$R/tmp" XDG_CACHE_HOME="$R/tmp/cache" MPLCONFIGDIR="$R/tmp/matplotlib"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$R/source-baseline-selector-v1"
cd "$R/source-baseline-selector-v1" || exit 2
printf '%s\n' "$$" > "$R/baseline-selection-v1.pid"
timeout --signal=TERM --kill-after=15s 3600s /home/guoyikun/.conda/envs/AFDM/bin/python -m afdm_sp_joint_unrolled.supplement_baseline_select --runs "$(cat "$R/baseline-selection-inputs-v1/runs.json")" --selection-protocol "$R/source-baseline-selector-v1/baseline-selection-protocol.json" --a2-quote "$R/baseline-selection-inputs-v1/a2-quote.json" --out "$R/baseline-selection-v1" > "$R/baseline-selection-v1.log" 2>&1
printf '%s\n' "$?" > "$R/baseline-selection-v1.exit"
