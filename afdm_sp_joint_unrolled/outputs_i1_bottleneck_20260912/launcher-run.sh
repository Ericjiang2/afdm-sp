#!/usr/bin/env bash
set -eu
exec /home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_bottleneck_20260912/launch-pilot.py > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_bottleneck_20260912/logs/launcher.log 2>&1
