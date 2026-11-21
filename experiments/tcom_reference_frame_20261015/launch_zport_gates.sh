#!/usr/bin/env bash
# Zheng-port gates on deinlab (CPU, single-thread processes, tmux g_tcom_zpg): G1, G2 (U and G), G5 (U and G), G3 and the two G4 driver runs in parallel (8 processes),
# then the G4 comparison, then the timing probe alone in one quiet process, then merge.
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/tcom_reference_frame_20261015"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
OUT="$CODE/out/zport_gates"
SESSION="${SESSION:-g_tcom_zpg}"
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom
if [[ "${ZPG_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  tmux new-session -d -s "$SESSION" "ZPG_INNER=1 bash $CODE/launch_zport_gates.sh > $OUT/logs/launcher.log 2>&1"
  echo "launched tmux $SESSION; log $OUT/logs/launcher.log"
  exit 0
fi
source "$PROJECT/experiments/headroom_ladder_20261008/env_single.sh"
cd "$CODE"
load=$(cut -d' ' -f1 /proc/loadavg); cores=$(nproc --all)
echo "preflight: nproc=$cores load1=$load $(date -u +%FT%TZ)"
busy=$(awk -v l="$load" 'BEGIN { printf "%d", l + 8 + 0.5 }')
(( busy + 16 <= cores )) || { echo "refused: load $load + 8 processes leaves < 16 free cores" >&2; exit 5; }
compgen -G "$PROJECT/experiments/tcom_reference_frame_20261015/out/p1/rows_shard*.jsonl.gz" > /dev/null || { echo "refused: P1 rows (out/p1/rows_shard*.jsonl.gz) missing" >&2; exit 4; }
rm -rf "$OUT/g4_a" "$OUT/g4_b"
run() { local name="$1"; shift; "$PY" -B "$CODE/zport_gates.py" "$@" > "$OUT/logs/$name.log" 2>&1; }
pids=()
run g1 --stage g1 --frames 200 --channels 20 & pids+=("$!")
run g2_U --stage g2 --scenario U --frames 20 & pids+=("$!")
run g2_G --stage g2 --scenario G --frames 20 & pids+=("$!")
run g5_U --stage g5 --scenario U --frames 20 & pids+=("$!")
run g5_G --stage g5 --scenario G --frames 20 & pids+=("$!")
run g3 --stage g3 --frames 16 & pids+=("$!")
for tag in a b; do
  "$PY" -B "$CODE/zport_driver.py" --out "$OUT/g4_$tag" --frames 8 --scenarios U,G --rho-list 0.3 --snr-list 6.0 --label g4 > "$OUT/logs/g4_$tag.log" 2>&1 & pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "parallel gates failed=$fail $(date -u +%FT%TZ)"
(( fail == 0 )) || { echo "stop: a gate stage crashed"; exit 6; }
run g4cmp --stage g4cmp --dir-a "$OUT/g4_a" --dir-b "$OUT/g4_b"
echo "timing start loadavg=$(cut -d' ' -f1-3 /proc/loadavg) $(date -u +%FT%TZ)"
run timing --stage timing --frames 8
echo "timing done loadavg=$(cut -d' ' -f1-3 /proc/loadavg) $(date -u +%FT%TZ)"
"$PY" -B "$CODE/zport_gates.py" --stage merge > "$OUT/logs/merge.log" 2>&1 && echo "merge ok" || echo "merge FAILED"
echo done
