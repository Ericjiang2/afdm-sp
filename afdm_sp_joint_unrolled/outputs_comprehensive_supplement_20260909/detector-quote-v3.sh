#!/usr/bin/env bash
set -u
R=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
export TMPDIR="$R/tmp" TEMP="$R/tmp" TMP="$R/tmp" XDG_CACHE_HOME="$R/tmp/cache" MPLCONFIGDIR="$R/tmp/matplotlib"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$R/source-detector-run-v2"
cd "$R/source-detector-run-v2" || exit 2
printf '%s\n' "$$" > "$R/detector-quote-v3.pid"
DEADLINE=$(( $(date +%s) + 900 ))
timeout --signal=TERM --kill-after=15s 915s /home/guoyikun/.conda/envs/AFDM/bin/python -m afdm_sp_joint_unrolled.supplement_detector_run --stage quote --caches '[{"original_root":"/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/baseline-smoke-v1","local_root":"/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/baseline-smoke-v1","record":"/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/baseline-smoke-v1/frame-000-B0-p3-s1.json"}]' --detectors '["stable-EP-40-d0.5","QPSK-MF-40-d1"]' --device cuda --max-terminal-calls 2 --deadline-unix "$DEADLINE" --max-output-bytes 33554432 --out "$R/detector-quote-v3" > "$R/detector-quote-v3.log" 2>&1
printf '%s\n' "$?" > "$R/detector-quote-v3.exit"
