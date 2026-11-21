#!/usr/bin/env bash
# Information-budget screen, full run exactly as frozen (spec research/info-budget-screen-20261014.md section 4, 7) + report-only columns, on deinlab inside tmux g_ib_screen.
#   tmux new-session -d -s g_ib_screen "bash /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/launch_ib_screen.sh"
# 1 locate (decision: 64 frames, L 4..96 step 4, 5 conditions, MODEL + PHYS)   2 confirm plan from the locate LCBs   3 confirm (512 independent frames, planned L only)
# 4 report-only locate run (same seeds, + RAY, LMMSE-GMI, 9.5 dB)   5 analysis.  <= 20 concurrent single-thread shards (contention x1.5 measured), >= 16 cores kept free.
set -Eeuo pipefail
CODE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
OUT=$CODE/out/ib_screen
NSH=${NSH:-20}
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/cache_headroom MPLCONFIGDIR=/data/guoyikun/tmp/cache_headroom
cd "$CODE"
load=$(cut -d' ' -f1 /proc/loadavg); cores=$(nproc --all)
echo "preflight: nproc=$cores load1=$load shards=$NSH $(date -u +%FT%TZ)" | tee "$OUT/logs/preflight_screen.txt"
busy=$(awk -v l="$load" -v n="$NSH" 'BEGIN { printf "%d", l + n + 0.5 }')
(( busy + 16 <= cores )) || { echo "refused: load $load + $NSH shards leaves < 16 free cores" >&2; exit 5; }
run_stage() {  # dir stage frames Ls extra...
  local dir=$1 stage=$2 frames=$3 Ls=$4; shift 4
  local pids=() fail=0
  for ((i = 0; i < NSH; i++)); do
    "$PY" -B ib_screen_run.py --stage "$stage" --frames "$frames" --Ls "$Ls" --out "$OUT/$dir" --shard "$i" --nshard "$NSH" "$@" > "$OUT/logs/${dir}_shard$(printf %02d "$i").log" 2>&1 &
    pids+=("$!")
  done
  for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
  echo "$dir shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle_screen.txt"
  (( fail == 0 ))
}
GRID=$("$PY" -B -c "import ib_screen_core as C; print(','.join(str(x) for x in C.LGRID))")
echo "start $(date -u +%FT%TZ)" > "$OUT/logs/lifecycle_screen.txt"
run_stage locate locate 64 "$GRID" --refs MODEL,PHYS
"$PY" -B ib_screen_agg.py --locate "$OUT/locate" --plan > "$OUT/logs/plan.txt" 2>&1
cat "$OUT/logs/plan.txt" >> "$OUT/logs/lifecycle_screen.txt"
CL=$("$PY" -B -c "import json; print(','.join(str(x) for x in json.load(open('$OUT/locate/confirm_plan.json'))['union']))")
echo "confirm L: $CL" >> "$OUT/logs/lifecycle_screen.txt"
run_stage confirm confirm 512 "$CL" --refs MODEL,PHYS
run_stage locate_ro locate 64 "$GRID" --refs MODEL,PHYS --ray --gmi --with-9p5
"$PY" -B ib_screen_agg.py --locate "$OUT/locate" --confirm "$OUT/confirm" --report-only "$OUT/locate_ro" --out "$OUT/screen" > "$OUT/logs/analysis.log" 2>&1 \
  && echo "analysis ok" >> "$OUT/logs/lifecycle_screen.txt" || echo "analysis FAILED" >> "$OUT/logs/lifecycle_screen.txt"
echo "done $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle_screen.txt"
