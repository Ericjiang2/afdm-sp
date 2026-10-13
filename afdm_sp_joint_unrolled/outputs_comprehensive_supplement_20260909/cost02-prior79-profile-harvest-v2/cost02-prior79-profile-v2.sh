#!/usr/bin/env bash
set -uo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
/home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/profile-cost02-prior79-v2.py run --contract-sha256 1a85cf34d0266b48fd63c6dc5e8492b5ef97f84815d470192f99acb64b2433ef > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/cost02-prior79-profile-v2.log 2>&1
rc=$?
printf '%s\n' "$rc" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/cost02-prior79-profile-v2.exit
exit "$rc"
