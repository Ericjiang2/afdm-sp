#!/usr/bin/env bash
set -uo pipefail
set -o noclobber
export TMPDIR=/data/guoyikun/tmp PYTHONDONTWRITEBYTECODE=1
/home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/audit-s01-candidates-v2.py --stage first > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/s01-candidate-first-audit-v2.log 2>&1
code=$?
printf '%s\n' "$code" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/s01-candidate-first-audit-v2.exit
exit "$code"
