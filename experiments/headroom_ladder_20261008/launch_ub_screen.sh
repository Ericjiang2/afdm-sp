#!/usr/bin/env bash
# Upper-bound screen, full run exactly as frozen (spec research/ub-screen-20261015.md sections 4-7) + report-only columns, on deinlab inside tmux g_ub_screen.
#   tmux new-session -d -s g_ub_screen "bash /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/launch_ub_screen.sh"
# 1 decision (L {28,30,31,32,34,35,38,40,43}; MODEL 8192 frames, PHYS 4096, RAY 4096; one run per reference)   2 ro (ratios 1.0/1.5/2.0, 512 frames, 3 refs, + 9.5 dB)
# 3 grid (RAY only, 64 frames, L 4..96, + 9.5 dB)   4 aggregation   5 gzip rows + md5.   <= NSH (default 20) concurrent single-thread shards (contention x1.5 measured), >= 16 cores kept free.
set -Eeuo pipefail
CODE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
OUT=$CODE/out/ub_screen
NSH=${NSH:-20}
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/cache_headroom MPLCONFIGDIR=/data/guoyikun/tmp/cache_headroom
cd "$CODE"
load=$(cut -d' ' -f1 /proc/loadavg); cores=$(nproc --all)
echo "preflight: nproc=$cores load1=$load shards=$NSH $(date -u +%FT%TZ)" | tee "$OUT/logs/preflight_ub.txt"
busy=$(awk -v l="$load" -v n="$NSH" 'BEGIN { printf "%d", l + n + 0.5 }')
(( busy + 16 <= cores )) || { echo "refused: load $load + $NSH shards leaves < 16 free cores" >&2; exit 5; }
run_stage() {  # dir stage frames Ls refs extra...
  local dir=$1 stage=$2 frames=$3 Ls=$4 refs=$5; shift 5
  local pids=() fail=0
  for ((i = 0; i < NSH; i++)); do
    "$PY" -B ub_screen_run.py --stage "$stage" --frames "$frames" --Ls "$Ls" --refs "$refs" --out "$OUT/$dir" --shard "$i" --nshard "$NSH" "$@" > "$OUT/logs/${dir}_shard$(printf %02d "$i").log" 2>&1 &
    pids+=("$!")
  done
  for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
  echo "$dir shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle_ub.txt"
  (( fail == 0 ))
}
DEC=$("$PY" -B -c "import ub_screen_core as U; print(','.join(str(x) for x in U.decision_Ls()))")
RO=$("$PY" -B -c "import ub_screen_core as U; print(','.join(str(x) for x in U.ro_Ls()))")
GRID=$("$PY" -B -c "import ib_screen_core as C; print(','.join(str(x) for x in C.LGRID))")
echo "start $(date -u +%FT%TZ) NSH=$NSH decision L: $DEC ro L: $RO" >> "$OUT/logs/lifecycle_ub.txt"
run_stage decision_MODEL decision 8192 "$DEC" MODEL
run_stage decision_PHYS decision 4096 "$DEC" PHYS
run_stage decision_RAY decision 4096 "$DEC" RAY
run_stage ro ro 512 "$RO" MODEL,PHYS,RAY --with-9p5
run_stage grid grid 64 "$GRID" RAY --with-9p5
"$PY" -B ub_screen_agg.py --decision "$OUT/decision_MODEL" "$OUT/decision_PHYS" "$OUT/decision_RAY" --ro "$OUT/ro" --grid "$OUT/grid" --out "$OUT/screen" > "$OUT/logs/analysis.log" 2>&1 \
  && echo "analysis ok" >> "$OUT/logs/lifecycle_ub.txt" || echo "analysis FAILED" >> "$OUT/logs/lifecycle_ub.txt"
# gzip rows after aggregation; md5 of the .gz and line counts verified (zcat) against the plain files
: > "$OUT/REMOTE_ROWS_MD5.txt"
for d in decision_MODEL decision_PHYS decision_RAY ro grid; do
  for f in "$OUT/$d"/rows_shard*.jsonl; do
    n=$(wc -l < "$f")
    gzip -9 "$f"
    m=$(zcat "$f.gz" | wc -l)
    if [[ "$n" != "$m" ]]; then echo "LINECOUNT MISMATCH $f.gz plain=$n gz=$m" >> "$OUT/logs/lifecycle_ub.txt"; exit 6; fi
    echo "$(md5sum "$f.gz" | cut -d' ' -f1)  ${f#$OUT/}.gz  lines=$n" >> "$OUT/REMOTE_ROWS_MD5.txt"
  done
done
echo "done $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle_ub.txt"
