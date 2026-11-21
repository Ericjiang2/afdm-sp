#!/usr/bin/env bash
# P1 confirmation (protocol.md section 3 + A1) on deinlab, CPU only, inside tmux g_tcom_p1.  NOT to be started before the
# user's go-ahead and the pre-run commit.
#   bash launch_p1.sh main      # 2 scenarios x rho {.3,.5} x SNR 4.5..8.0 x 2000 frames; NSH shards (default 30); then p1_agg; then gzip rows + md5
#   bash launch_p1.sh timing    # quiet timing subset: same grid, 100 NEW frames (offset 2000) per cell, NSH shards (default 8); gzip rows + md5
#   DRYRUN=1 bash launch_p1.sh main    # preflight + print the plan, start nothing
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo, CPU only (CUDA hidden),
# single-thread shards, >= 16 cores kept free (preflight refuses otherwise; contention x1.5 measured in P1-G4).
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/tcom_reference_frame_20261015"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
MODE="${1:-main}"
SESSION="${SESSION:-g_tcom_p1}"
case "$MODE" in
  main)   OUT="$CODE/out/p1";        FRAMES=2000; OFFSET=0;    NSH="${NSH:-30}" ;;
  timing) OUT="$CODE/out/p1_timing"; FRAMES=100;  OFFSET=2000; NSH="${NSH:-8}" ;;
  *) echo "usage: launch_p1.sh main|timing" >&2; exit 2 ;;
esac
(( NSH >= 1 && NSH <= 100 )) || { echo "NSH must be 1..100" >&2; exit 2; }
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom

if [[ "${P1_INNER:-0}" != 1 && "${DRYRUN:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  tmux new-session -d -s "$SESSION" "P1_INNER=1 NSH=$NSH bash $CODE/launch_p1.sh $MODE > $OUT/logs/launcher.log 2>&1"
  echo "launched tmux $SESSION ($MODE, NSH=$NSH); log $OUT/logs/launcher.log"
  exit 0
fi

source "$PROJECT/experiments/headroom_ladder_20261008/env_single.sh"
cd "$CODE"
load=$(cut -d' ' -f1 /proc/loadavg); cores=$(nproc --all)
echo "preflight: mode=$MODE nproc=$cores load1=$load shards=$NSH $(date -u +%FT%TZ)" | tee -a "$OUT/logs/preflight.txt"
busy=$(awk -v l="$load" -v n="$NSH" 'BEGIN { printf "%d", l + n + 0.5 }')
(( busy + 16 <= cores )) || { echo "refused: load $load + $NSH shards leaves < 16 free cores" >&2; exit 5; }
if [[ "${DRYRUN:-0}" == 1 ]]; then
  echo "dry run OK: would run $NSH shards of p1_driver.py --out $OUT --frames $FRAMES --frame-offset $OFFSET --label $MODE"
  exit 0
fi
if compgen -G "$OUT/rows_shard*.jsonl*" > /dev/null && [[ "${RESUME:-0}" != 1 ]]; then
  echo "refused: $OUT already holds rows (set RESUME=1 to resume the same configuration)" >&2; exit 4
fi

echo "start $(date -u +%FT%TZ) mode=$MODE NSH=$NSH frames=$FRAMES offset=$OFFSET" >> "$OUT/logs/lifecycle.txt"
pids=()
for ((i = 0; i < NSH; i++)); do
  "$PY" -B "$CODE/p1_driver.py" --out "$OUT" --frames "$FRAMES" --frame-offset "$OFFSET" --shard "$i" --nshard "$NSH" --label "$MODE" \
    > "$OUT/logs/shard_$(printf %03d "$i").log" 2>&1 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
(( fail == 0 )) || { echo "stop: $fail shard(s) failed; no aggregation" >> "$OUT/logs/lifecycle.txt"; exit 6; }

if [[ "$MODE" == main ]]; then
  TIMING_ARGS=()
  if compgen -G "$CODE/out/p1_timing/rows_shard*.jsonl*" > /dev/null; then TIMING_ARGS=(--timing "$CODE/out/p1_timing"); fi
  "$PY" -B p1_agg.py --rows "$OUT" --out "$OUT/analysis" --boot 20000 ${TIMING_ARGS[@]+"${TIMING_ARGS[@]}"} > "$OUT/logs/analysis.log" 2>&1 \
    && echo "analysis ok" >> "$OUT/logs/lifecycle.txt" || echo "analysis FAILED" >> "$OUT/logs/lifecycle.txt"
fi

# gzip rows after aggregation; md5 of the .gz and line counts verified (zcat) against the plain files
: > "$OUT/REMOTE_ROWS_MD5.txt"
for f in "$OUT"/rows_shard*.jsonl; do
  n=$(wc -l < "$f")
  gzip -9 "$f"
  m=$(zcat "$f.gz" | wc -l)
  if [[ "$n" != "$m" ]]; then echo "LINECOUNT MISMATCH $f.gz plain=$n gz=$m" >> "$OUT/logs/lifecycle.txt"; exit 7; fi
  echo "$(md5sum "$f.gz" | cut -d' ' -f1)  ${f#$OUT/}.gz  lines=$n" >> "$OUT/REMOTE_ROWS_MD5.txt"
done
echo "done $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
