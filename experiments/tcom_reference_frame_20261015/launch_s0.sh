#!/usr/bin/env bash
# S0 gates on deinlab (CPU, single-thread processes, tmux session g_tcom_s0).
#   launch_s0.sh numax   : estimate nu_max (1 process); freeze the value in gen_fixed.py afterwards
#   launch_s0.sh gates   : G-S0a (11 shards) + G-S0b + G-S0c + G-S0d + smoke (15 processes), then merge
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo, <= 16 processes.
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/tcom_reference_frame_20261015"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
OUT="$CODE/out/s0"
SESSION="${SESSION:-g_tcom_s0}"
PHASE="$1"
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom

if [[ "${S0_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  tmux new-session -d -s "$SESSION" "S0_INNER=1 bash $CODE/launch_s0.sh $PHASE > $OUT/logs/launcher_$PHASE.log 2>&1"
  echo "launched tmux $SESSION; log $OUT/logs/launcher_$PHASE.log"
  exit 0
fi

source "$PROJECT/experiments/headroom_ladder_20261008/env_single.sh"
cd "$CODE"
run() { local name="$1"; shift; "$PY" -B "$CODE/s0_gates.py" "$@" > "$OUT/logs/$name.log" 2>&1; }
pids=()
case "$PHASE" in
  numax)
    run numax --stage numax --frames 200000 &
    pids+=("$!") ;;
  gates)
    NSHARD=11
    for ((i = 0; i < NSHARD; i++)); do
      run "a_$(printf %03d "$i")" --stage a --shard "$i" --nshard "$NSHARD" --frames 1000 --rho3-frames 50 &
      pids+=("$!")
    done
    run b --stage b --mc-frames 100000 --mc-frames-frozen 40000 &
    pids+=("$!")
    run c --stage c --frames 20 &
    pids+=("$!")
    run d --stage d --frames 200 &
    pids+=("$!")
    run smoke --stage smoke --frames 8 &
    pids+=("$!") ;;
  *) echo "unknown phase $PHASE" >&2; exit 2 ;;
esac
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "phase=$PHASE failed=$fail $(date -u +%FT%TZ)"
if [[ "$PHASE" == gates && "$fail" == 0 ]]; then
  "$PY" -B "$CODE/s0_gates.py" --stage merge > "$OUT/logs/merge.log" 2>&1 && echo "merge ok" || echo "merge FAILED"
fi
echo done
