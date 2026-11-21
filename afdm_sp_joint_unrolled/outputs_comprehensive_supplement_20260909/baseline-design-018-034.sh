#!/usr/bin/env bash
set -u
R=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909
export TMPDIR="$R/tmp" TEMP="$R/tmp" TMP="$R/tmp" NUMBA_CACHE_DIR="$R/tmp/numba" MPLCONFIGDIR="$R/tmp/matplotlib" XDG_CACHE_HOME="$R/tmp/cache"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$R/source-baseline-run-v1"
cd "$R/source-baseline-run-v1" || exit 2
printf '%s\n' "$$" > "$R/baseline-design-018-034.pid"
DEADLINE=$(( $(date +%s) + 1800 ))
timeout --signal=TERM --kill-after=15s 1815s /home/guoyikun/.conda/envs/AFDM/bin/python "$R/baseline-smoke-v1.py" --protocol "$R/data-protocol.json" --checkpoint /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk --out "$R/baseline-design-018-034" --device cuda:0 --start 18 --stop 34 --snr 8 --split design --recipes '["B0-p0-s0.5","B0-p0-s1","B0-p1-s0.5","B0-p1-s1","B0-p2-s0.5","B0-p2-s1","B0-p3-s0.5","B0-p3-s1","ridge-p0-s0.5","ridge-p0-s1","ridge-p1-s0.5","ridge-p1-s1","ridge-p2-s0.5","ridge-p2-s1","ridge-p3-s0.5","ridge-p3-s1","SBL-p0-s0.5","SBL-p0-s1","SBL-p1-s0.5","SBL-p1-s1","SBL-p2-s0.5","SBL-p2-s1","SBL-p3-s0.5","SBL-p3-s1","group-p0-s0.5","group-p0-s1","group-p1-s0.5","group-p1-s1","group-p2-s0.5","group-p2-s1","group-p3-s0.5","group-p3-s1","bounded-param-p0-s0.5","bounded-param-p0-s1","bounded-param-p1-s0.5","bounded-param-p1-s1","bounded-param-p2-s0.5","bounded-param-p2-s1","bounded-param-p3-s0.5","bounded-param-p3-s1"]' --max-full-calls 640 --max-output-bytes 17179869184 --deadline-unix "$DEADLINE" > "$R/baseline-design-018-034.log" 2>&1
printf '%s\n' "$?" > "$R/baseline-design-018-034.exit"
