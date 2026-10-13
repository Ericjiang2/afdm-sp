#!/usr/bin/env bash
set -u
R=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
export TMPDIR="$R/tmp" TEMP="$R/tmp" TMP="$R/tmp" NUMBA_CACHE_DIR="$R/tmp/numba" MPLCONFIGDIR="$R/tmp/matplotlib" XDG_CACHE_HOME="$R/tmp/cache"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$R/source-profile-v2"
cd "$R/source-profile-v2" || { printf "125\n" > "$R/a2-equivalence-v2.exit"; exit 125; }
printf '%s\n' "$$" > "$R/a2-equivalence-v2.pid"
DEADLINE=$(( $(date +%s) + 600 ))
timeout --signal=TERM --kill-after=15s 615s /home/guoyikun/.conda/envs/AFDM/bin/python "$R/a2-equivalence-v1.py" --protocol "$R/data-protocol.json" --checkpoint /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk --prior /data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/v2_prior400-1788678282/prior400/cache_snr8.pt --out "$R/a2-equivalence-v2" --deadline-unix "$DEADLINE" > "$R/a2-equivalence-v2.log" 2>&1
printf '%s\n' "$?" > "$R/a2-equivalence-v2.exit"
