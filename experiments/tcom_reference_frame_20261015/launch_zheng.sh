#!/usr/bin/env bash
# P2a part 1 (Zheng et al. 2025 reproduction in its own regime) on deinlab: CPU, single-thread shards, tmux g_tcom_zheng.
#   bash launch_zheng.sh        # main run (4 points, 2000 frames), c2 = 0 sensitivity run, then the gates
#   STAGES=alt,gates bash launch_zheng.sh   # DIAGNOSTIC only (not a gate): the alternative reading of eq. (29) with delta = 0.9 (delta weighting the OLD message), then regenerate the gates
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo, CPU only, >= 16 cores kept free.
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/tcom_reference_frame_20261015"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
SESSION="${SESSION:-g_tcom_zheng}"
NSH="${NSH:-16}"
OUT="$CODE/out/zheng_rows"
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom
if [[ "${ZHENG_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  tmux new-session -d -s "$SESSION" "ZHENG_INNER=1 NSH=$NSH bash $CODE/launch_zheng.sh > $OUT/logs/launcher.log 2>&1"
  echo "launched tmux $SESSION (NSH=$NSH); log $OUT/logs/launcher.log"
  exit 0
fi
source "$PROJECT/experiments/headroom_ladder_20261008/env_single.sh"
cd "$CODE"
load=$(cut -d' ' -f1 /proc/loadavg); cores=$(nproc --all)
echo "preflight: nproc=$cores load1=$load shards=$NSH $(date -u +%FT%TZ)"
busy=$(awk -v l="$load" -v n="$NSH" 'BEGIN { printf "%d", l + n + 0.5 }')
(( busy + 16 <= cores )) || { echo "refused: load $load + $NSH shards leaves < 16 free cores" >&2; exit 5; }
STAGES="${STAGES:-main,c2zero,gates}"
if [[ ",$STAGES," == *,main,* ]] && compgen -G "$OUT/main/rows_shard*.jsonl" > /dev/null && [[ "${RESUME:-0}" != 1 ]]; then
  echo "refused: $OUT/main already holds rows (set RESUME=1 to resume the same configuration)" >&2; exit 4
fi
run_stage() {  # name, extra driver args...
  local name="$1"; shift
  local pids=() fail=0
  for ((i = 0; i < NSH; i++)); do
    "$PY" -B zheng_repro.py run --out "$OUT/$name" --frames 2000 --shard "$i" --nshard "$NSH" "$@" > "$OUT/logs/${name}_shard$(printf %03d "$i").log" 2>&1 &
    pids+=("$!")
  done
  for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
  echo "$name shards_failed=$fail $(date -u +%FT%TZ)"
  (( fail == 0 ))
}
[[ ",$STAGES," == *,main,* ]] && run_stage main
[[ ",$STAGES," == *,c2zero,* ]] && run_stage c2zero --points p50M8 --snr-d 17 --c2 0
[[ ",$STAGES," == *,alt,* ]] && run_stage alt_delta09 --points p50M8 --delta 0.9
if [[ ",$STAGES," == *,gates,* ]]; then
  ALT_ARGS=()
  if compgen -G "$OUT/alt_delta09/rows_shard*.jsonl" > /dev/null; then ALT_ARGS=(--alt-rows "$OUT/alt_delta09"); fi
  "$PY" -B zheng_repro.py gates --rows "$OUT/main" --c2-rows "$OUT/c2zero" ${ALT_ARGS[@]+"${ALT_ARGS[@]}"} --out "$CODE/out/zheng_gates" > "$OUT/logs/gates.log" 2>&1 && echo "gates written" || echo "gates FAILED"
fi
echo done
