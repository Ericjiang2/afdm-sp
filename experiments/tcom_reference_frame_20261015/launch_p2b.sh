#!/usr/bin/env bash
# P2b embedded-pilot comparison on deinlab, CPU only, inside tmux g_tcom_p2b.  The TEST run is NOT to be started before the user's go-ahead
# and the pre-run commit.
#   bash launch_p2b.sh dev    # rho_EP tuning: 500 dev frames at 6.0 dB, EP only, rho_EP in {.05,.1,.2,.3}; NSH shards (default 16); then p2b_agg --dev
#   bash launch_p2b.sh test   # scenario S, SNR 4.5..8.0 x 2000 frames, arms F0,B,A3 (rho .3/.5) + EP + EP-genie at the frozen RHO_EP; NSH (default 30);
#                             # then p2b_agg (H6); then gzip rows + md5
#   DRYRUN=1 bash launch_p2b.sh test   # preflight + plan, starts nothing
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo, CPU only (CUDA hidden),
# single-thread shards, >= 16 cores kept free (preflight refuses otherwise).
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/tcom_reference_frame_20261015"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
MODE="${1:-test}"
SESSION="${SESSION:-g_tcom_p2b}"
case "$MODE" in
  dev)  OUT="$CODE/out/p2b_dev";  FRAMES=500;  SET=dev;  NSH="${NSH:-16}"; ARGS=(--snr-list 6.0 --arms EP --rho-ep-list 0.05,0.10,0.20,0.30) ;;
  test) OUT="$CODE/out/p2b_test"; FRAMES=2000; SET=test; NSH="${NSH:-30}"; ARGS=() ;;
  *) echo "usage: launch_p2b.sh dev|test" >&2; exit 2 ;;
esac
(( NSH >= 1 && NSH <= 100 )) || { echo "NSH must be 1..100" >&2; exit 2; }
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom

if [[ "${P2B_INNER:-0}" != 1 && "${DRYRUN:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  tmux new-session -d -s "$SESSION" "P2B_INNER=1 NSH=$NSH bash $CODE/launch_p2b.sh $MODE > $OUT/logs/launcher.log 2>&1"
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
  echo "dry run OK: would run $NSH shards of p2b_driver.py --out $OUT --set $SET --frames $FRAMES ${ARGS[*]-}"
  exit 0
fi
if compgen -G "$OUT/rows_shard*.jsonl*" > /dev/null && [[ "${RESUME:-0}" != 1 ]]; then
  echo "refused: $OUT already holds rows (set RESUME=1 to resume the same configuration)" >&2; exit 4
fi

echo "start $(date -u +%FT%TZ) mode=$MODE NSH=$NSH frames=$FRAMES" >> "$OUT/logs/lifecycle.txt"
pids=()
for ((i = 0; i < NSH; i++)); do
  "$PY" -B "$CODE/p2b_driver.py" --out "$OUT" --set "$SET" --frames "$FRAMES" --shard "$i" --nshard "$NSH" --label "$MODE" ${ARGS[@]+"${ARGS[@]}"} \
    > "$OUT/logs/shard_$(printf %03d "$i").log" 2>&1 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
(( fail == 0 )) || { echo "stop: $fail shard(s) failed; no aggregation" >> "$OUT/logs/lifecycle.txt"; exit 6; }

if [[ "$MODE" == dev ]]; then
  "$PY" -B p2b_agg.py --dev "$OUT" --out "$OUT/analysis" > "$OUT/logs/analysis.log" 2>&1 \
    && echo "analysis ok" >> "$OUT/logs/lifecycle.txt" || echo "analysis FAILED" >> "$OUT/logs/lifecycle.txt"
else
  "$PY" -B p2b_agg.py --rows "$OUT" --out "$OUT/analysis" --boot 20000 > "$OUT/logs/analysis.log" 2>&1 \
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
