#!/usr/bin/env bash
set -u
R=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
export TMPDIR="$R/tmp" TEMP="$R/tmp" TMP="$R/tmp" NUMBA_CACHE_DIR="$R/tmp/numba" MPLCONFIGDIR="$R/tmp/matplotlib" XDG_CACHE_HOME="$R/tmp/cache"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$R/source-profile-v1"
cd "$R/source-profile-v1"
printf '%s\n' "$$" > "$R/profile-v1.pid"
DEADLINE=$(( $(date +%s) + 1800 ))
timeout --signal=TERM --kill-after=15s 1815s /home/guoyikun/.conda/envs/AFDM/bin/python "$R/profile-v1.py" --protocol "$R/data-protocol.json" --checkpoint /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk --out "$R/profile-v1" --prior /data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/v2_prior400-1788678282/prior400/cache_snr8.pt --device cuda:0 --start 0 --stop 1 --snr 8 --arms '["A2","B0","old-Bstar"]' --max-full-calls 3 --max-terminal-calls 3 --max-ce-calls 3 --deadline-unix "$DEADLINE" > "$R/profile-v1.log" 2>&1
printf '%s\n' "$?" > "$R/profile-v1.exit"
