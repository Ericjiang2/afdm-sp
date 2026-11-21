#!/usr/bin/env bash
# DDST Stage 0 (protocol section 2): geometry of M_prior per L (parallel single-thread processes), combine, law.  Run on deinlab inside tmux g_ddst_s0.
#   tmux new-session -d -s g_ddst_s0 "bash /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/launch_ddst_s0.sh"
set -Eeuo pipefail
CODE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
OUT=$CODE/out/ddst_s0
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/cache_headroom
export MPLCONFIGDIR=/data/guoyikun/tmp/cache_headroom TORCH_HOME=/data/guoyikun/tmp/cache_headroom
cd "$CODE"
echo "start $(date -u +%FT%TZ) load=$(cut -d' ' -f1 /proc/loadavg)" > "$OUT/logs/lifecycle.txt"
pids=()
for L in 4 8 12 16 20 24 28 32 36 40 48; do
  "$PY" -B ddst_s0.py geometry --L "$L" > "$OUT/logs/geometry_L$(printf %02d "$L").log" 2>&1 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "geometry_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
(( fail == 0 ))
"$PY" -B ddst_s0.py combine > "$OUT/logs/combine.log" 2>&1
"$PY" -B ddst_s0.py law > "$OUT/logs/law.log" 2>&1
echo "done $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
