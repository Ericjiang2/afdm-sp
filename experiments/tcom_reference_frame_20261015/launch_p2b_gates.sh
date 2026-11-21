#!/usr/bin/env bash
# P2b gates on deinlab (CPU, single-thread processes, tmux session g_tcom_p2bg): G0, G1, G2, G4, G5 and the two driver runs (all arms incl. the
# report-only SPG arm) in parallel (7 processes), then the G3 (regression vs ref/g3_prev) and G6 comparisons, then the timing probe and the SPG
# timing probe, each alone in one quiet process, then merge.
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/tcom_reference_frame_20261015"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
OUT="$CODE/out/p2b_gates"
SESSION="${SESSION:-g_tcom_p2bg}"
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom
if [[ "${P2BG_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  tmux new-session -d -s "$SESSION" "P2BG_INNER=1 bash $CODE/launch_p2b_gates.sh > $OUT/logs/launcher.log 2>&1"
  echo "launched tmux $SESSION; log $OUT/logs/launcher.log"
  exit 0
fi
source "$PROJECT/experiments/headroom_ladder_20261008/env_single.sh"
cd "$CODE"
load=$(cut -d' ' -f1 /proc/loadavg); cores=$(nproc --all)
echo "preflight: nproc=$cores load1=$load $(date -u +%FT%TZ)"
busy=$(awk -v l="$load" 'BEGIN { printf "%d", l + 7 + 0.5 }')
(( busy + 16 <= cores )) || { echo "refused: load $load + 7 processes leaves < 16 free cores" >&2; exit 5; }
[[ -f "$OUT/ref/g3_prev/rows_shard000.jsonl" ]] || { echo "refused: $OUT/ref/g3_prev (rows stored before the shared LMMSE core) is missing" >&2; exit 4; }
rm -rf "$OUT/g3_a" "$OUT/g3_b"
run() { local name="$1"; shift; "$PY" -B "$CODE/p2b_gates.py" "$@" > "$OUT/logs/$name.log" 2>&1; }
pids=()
run g0 --stage g0 --frames 100 --mc-frames 100000 & pids+=("$!")
run g1 --stage g1 --frames 20 & pids+=("$!")
run g2 --stage g2 --frames 50 & pids+=("$!")
run g4 --stage g4 --frames 100 & pids+=("$!")
run g5 --stage g5 --frames 20 & pids+=("$!")
for tag in a b; do
  "$PY" -B "$CODE/p2b_driver.py" --out "$OUT/g3_$tag" --set dev --frames 16 --frame-offset 3000 --snr-list 6.0 --arms F0,B,A3,SPG,EP,EPG \
    --rho-ep-list 0.1 --label g3 > "$OUT/logs/g3_$tag.log" 2>&1 & pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "parallel gates failed=$fail $(date -u +%FT%TZ)"
(( fail == 0 )) || { echo "stop: a gate stage crashed"; exit 6; }
run g3cmp --stage g3cmp --dir-a "$OUT/g3_a" --dir-b "$OUT/g3_b" --dir-ref "$OUT/ref/g3_prev"
run g6cmp --stage g6cmp --dir-a "$OUT/g3_a" --dir-b "$OUT/g3_b"
echo "timing start loadavg=$(cut -d' ' -f1-3 /proc/loadavg) $(date -u +%FT%TZ)"
run timing --stage timing --frames 16
echo "timing done loadavg=$(cut -d' ' -f1-3 /proc/loadavg) $(date -u +%FT%TZ)"
run timing_spg --stage timing_spg --frames 16
echo "timing_spg done loadavg=$(cut -d' ' -f1-3 /proc/loadavg) $(date -u +%FT%TZ)"
"$PY" -B "$CODE/p2b_gates.py" --stage merge > "$OUT/logs/merge.log" 2>&1 && echo "merge ok" || echo "merge FAILED"
echo done
