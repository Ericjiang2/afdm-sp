#!/usr/bin/env bash
set -uo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
/home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/profile-cost02-prior79-v1.py run --contract-sha256 e0b2b2d137e848a3961c3163c110d0fb7c2de52393a9be737829da27a43761b7 > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/cost02-prior79-profile-v1.log 2>&1
rc=$?
printf '%s\n' "$rc" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/cost02-prior79-profile-v1.exit
exit "$rc"
