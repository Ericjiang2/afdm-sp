#!/usr/bin/env bash
set -uo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
/home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/recover-cost02-prior79-v1.py run --contract-sha256 c47ad5947a011f0efb00357c4453aa71a5b73aa7b063a1a5526d3d8805e71317 > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/cost02-prior79-recovery-v1.log 2>&1
rc=$?
printf '%s\n' "$rc" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/cost02-prior79-recovery-v1.exit
exit "$rc"
