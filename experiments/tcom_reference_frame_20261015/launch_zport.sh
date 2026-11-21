#!/usr/bin/env bash
# P2a part 2: the Zheng port run on deinlab, CPU only, inside tmux g_tcom_zport.  NOT to be started before the user's go-ahead and the pre-run commit.
#   bash launch_zport.sh          # P1 frames 0..999 of U and G x rho {.3,.5} x SNR 4.5..8.0, variants Zf01 Zf09 Za01 Za09 Zo01 Zo09 (Z-turbo dropped by the I4 budget rule; VARIANTS=...,Zt to add it), NSH shards (default 30),
#                                 # then z_agg (H5 against P1's B rows), then gzip rows + md5
#   DRYRUN=1 bash launch_zport.sh # preflight + plan, starts nothing
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo, CPU only, single-thread shards, >= 16 cores kept free.
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/tcom_reference_frame_20261015"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
SESSION="${SESSION:-g_tcom_zport}"
NSH="${NSH:-30}"
VARIANTS="${VARIANTS:-Zf01,Zf09,Za01,Za09,Zo01,Zo09}"
OUT="$CODE/out/zport"
(( NSH >= 1 && NSH <= 100 )) || { echo "NSH must be 1..100" >&2; exit 2; }
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom
if [[ "${ZPORT_INNER:-0}" != 1 && "${DRYRUN:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  tmux new-session -d -s "$SESSION" "ZPORT_INNER=1 NSH=$NSH VARIANTS=$VARIANTS bash $CODE/launch_zport.sh > $OUT/logs/launcher.log 2>&1"
  echo "launched tmux $SESSION (NSH=$NSH, variants $VARIANTS); log $OUT/logs/launcher.log"
  exit 0
fi
source "$PROJECT/experiments/headroom_ladder_20261008/env_single.sh"
cd "$CODE"
load=$(cut -d' ' -f1 /proc/loadavg); cores=$(nproc --all)
echo "preflight: nproc=$cores load1=$load shards=$NSH $(date -u +%FT%TZ)" | tee -a "$OUT/logs/preflight.txt"
busy=$(awk -v l="$load" -v n="$NSH" 'BEGIN { printf "%d", l + n + 0.5 }')
(( busy + 16 <= cores )) || { echo "refused: load $load + $NSH shards leaves < 16 free cores" >&2; exit 5; }
compgen -G "$CODE/out/p1/rows_shard*.jsonl.gz" > /dev/null || { echo "refused: P1 rows (out/p1/rows_shard*.jsonl.gz) missing" >&2; exit 4; }
if [[ "${DRYRUN:-0}" == 1 ]]; then
  echo "dry run OK: would run $NSH shards of zport_driver.py --out $OUT --frames 1000 --variants $VARIANTS"
  exit 0
fi
if compgen -G "$OUT/rows_shard*.jsonl*" > /dev/null && [[ "${RESUME:-0}" != 1 ]]; then
  echo "refused: $OUT already holds rows (set RESUME=1 to resume the same configuration)" >&2; exit 4
fi
echo "start $(date -u +%FT%TZ) NSH=$NSH variants=$VARIANTS" >> "$OUT/logs/lifecycle.txt"
pids=()
for ((i = 0; i < NSH; i++)); do
  "$PY" -B "$CODE/zport_driver.py" --out "$OUT" --frames 1000 --shard "$i" --nshard "$NSH" --variants "$VARIANTS" --label port \
    > "$OUT/logs/shard_$(printf %03d "$i").log" 2>&1 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
(( fail == 0 )) || { echo "stop: $fail shard(s) failed; no aggregation" >> "$OUT/logs/lifecycle.txt"; exit 6; }
"$PY" -B z_agg.py --rows "$OUT" --p1 "$CODE/out/p1" --out "$OUT/analysis" --frames 1000 --boot 20000 > "$OUT/logs/analysis.log" 2>&1 \
  && echo "analysis ok" >> "$OUT/logs/lifecycle.txt" || echo "analysis FAILED" >> "$OUT/logs/lifecycle.txt"
: > "$OUT/REMOTE_ROWS_MD5.txt"
for f in "$OUT"/rows_shard*.jsonl; do
  n=$(wc -l < "$f")
  gzip -9 "$f"
  m=$(zcat "$f.gz" | wc -l)
  if [[ "$n" != "$m" ]]; then echo "LINECOUNT MISMATCH $f.gz plain=$n gz=$m" >> "$OUT/logs/lifecycle.txt"; exit 7; fi
  echo "$(md5sum "$f.gz" | cut -d' ' -f1)  ${f#$OUT/}.gz  lines=$n" >> "$OUT/REMOTE_ROWS_MD5.txt"
done
echo "done $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
