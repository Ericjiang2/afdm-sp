#!/usr/bin/env bash
set -u
R=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
export TMPDIR="$R/tmp" TEMP="$R/tmp" TMP="$R/tmp" NUMBA_CACHE_DIR="$R/tmp/numba" MPLCONFIGDIR="$R/tmp/matplotlib" XDG_CACHE_HOME="$R/tmp/cache"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$R/source-v5"
cd "$R/source-v5"
printf '%s\n' "$$" > "$R/engineering-v5.pid"
DEADLINE=$(( $(date +%s) + 1800 ))
timeout --signal=TERM --kill-after=15s 1815s /home/guoyikun/.conda/envs/AFDM/bin/python "$R/engineering-v5.py" --protocol "$R/data-protocol.json" --checkpoint /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk --out "$R/engineering-v5" --device cuda:0 --start 0 --stop 2 --snr 8 --recipes '[{"id":"b0-s1","family":"b0","parameter":null,"terminal_scale":1},{"id":"sbl-s1","family":"sbl","parameter":0.001,"terminal_scale":1}]' --max-full-calls 4 --deadline-unix "$DEADLINE" > "$R/engineering-v5.log" 2>&1
printf '%s\n' "$?" > "$R/engineering-v5.exit"
