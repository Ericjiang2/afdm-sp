#!/usr/bin/env bash
# P1 gates on deinlab (CPU, single-thread processes, tmux session g_tcom_p1g): G1 (8 shards) + G2 + G3 in parallel,
# then G4 (timing probe) alone in one quiet process, then merge.  Refuses to start if load + 10 leaves < 16 free cores.
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/tcom_reference_frame_20261015"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
OUT="$CODE/out/p1_gates"
SESSION="${SESSION:-g_tcom_p1g}"
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom
if [[ "${P1G_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  tmux new-session -d -s "$SESSION" "P1G_INNER=1 bash $CODE/launch_p1_gates.sh > $OUT/logs/launcher.log 2>&1"
  echo "launched tmux $SESSION; log $OUT/logs/launcher.log"
  exit 0
fi
source "$PROJECT/experiments/headroom_ladder_20261008/env_single.sh"
cd "$CODE"
load=$(cut -d' ' -f1 /proc/loadavg); cores=$(nproc --all)
echo "preflight: nproc=$cores load1=$load $(date -u +%FT%TZ)"
busy=$(awk -v l="$load" 'BEGIN { printf "%d", l + 10 + 0.5 }')
(( busy + 16 <= cores )) || { echo "refused: load $load + 10 shards leaves < 16 free cores" >&2; exit 5; }
run() { local name="$1"; shift; "$PY" -B "$CODE/p1_gates.py" "$@" > "$OUT/logs/$name.log" 2>&1; }
pids=()
for ((i = 0; i < 8; i++)); do
  run "g1_$i" --stage g1 --shard "$i" --nshard 8 --frames 64 &
  pids+=("$!")
done
run g2 --stage g2 --frames 32 &
pids+=("$!")
run g3 --stage g3 &
pids+=("$!")
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "g1-g3 failed=$fail $(date -u +%FT%TZ)"
(( fail == 0 )) || { echo "stop: a gate stage crashed"; exit 6; }
echo "g4 start loadavg=$(cut -d' ' -f1-3 /proc/loadavg) $(date -u +%FT%TZ)"
run g4 --stage g4 --frames 16
echo "g4 done loadavg=$(cut -d' ' -f1-3 /proc/loadavg) $(date -u +%FT%TZ)"
"$PY" -B "$CODE/p1_gates.py" --stage merge > "$OUT/logs/merge.log" 2>&1 && echo "merge ok" || echo "merge FAILED"
echo done
