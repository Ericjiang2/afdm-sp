#!/usr/bin/env bash
set -u
R=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
export TMPDIR="$R/tmp" TEMP="$R/tmp" TMP="$R/tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
printf '%s\n' "$$" > "$R/baseline-queue-v1.pid"
/home/guoyikun/.conda/envs/AFDM/bin/python "$R/baseline-queue-v1.py" --manifest "$R/baseline-queue-plan.json" --state-dir "$R/baseline-queue-v1" --deadline-unix "$1" > "$R/baseline-queue-v1.log" 2>&1
printf '%s\n' "$?" > "$R/baseline-queue-v1.exit"
