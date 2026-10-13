#!/usr/bin/env bash
# Launch N single-thread CPU shards of driver_c1ib2.py (C1 inner-update budget, second batch IB2) inside tmux (deinlab only).
#   launch_c1ib2.sh <generate> <out_dir> <nshard> [driver_c1ib2.py args...]
# IB2 runs (REM = /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008; <= 100 concurrent shards in total):
#   quiet timing reference first (alone, 10 frames x 4 arms x 7 L):
#     SESSION=g_c1ib2_time bash $REM/launch_c1ib2.sh generate $REM/out/c1ib2_time 10 --preset time
#   then, concurrently (50 + 20 + 30 = 100 shards):
#     SESSION=g_c1ib2_rep   bash $REM/launch_c1ib2.sh generate $REM/out/c1ib2_rep   50 --preset rep
#     SESSION=g_c1ib2_sweep bash $REM/launch_c1ib2.sh generate $REM/out/c1ib2_sweep 20 --preset sweep
#     SESSION=g_c1ib2_r10   bash $REM/launch_c1ib2.sh generate $REM/out/c1ib2_r10   30 --preset r10
#   IB2-0 internal determinism set (after the rep run; 10 shards x 1 frame):
#     SESSION=g_c1ib2_det   bash $REM/launch_c1ib2.sh generate $REM/out/c1ib2_det   10 --preset det
# Smoke: SESSION=g_c1ib2_smoke bash launch_c1ib2.sh generate /data/guoyikun/tmp/c1ib2_smoke 2 --cells '8:0.3:12,24' --arms R4T20,R4T40 --frames 2
#   (merge runs automatically when all shards succeed)
#
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo, CPU only (CUDA hidden).
# Guard: refuses to start if the driver_c1ib2 shards already running plus N exceed MAX_TOTAL (default 100), or if fewer than 16 cores remain
# idle by max(1-minute load average, running shards) + N (override LOAD_GUARD=0 only for a deliberate decision).
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/headroom_ladder_20261008"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
SESSION="${SESSION:-g_c1ib2}"
MAX_TOTAL="${MAX_TOTAL:-100}"
MODE="$1"; OUT="$2"; NSHARD="$3"; shift 3
case "$OUT" in /data/guoyikun/*) ;; *) echo "OUT must be under /data/guoyikun" >&2; exit 2;; esac
(( NSHARD >= 1 && NSHARD <= 100 )) || { echo "nshard must be 1..100" >&2; exit 2; }
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom

if [[ "${HEADROOM_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  running=$(pgrep -fc "driver_c1ib2.py --mode generate" || true)
  cores=$(nproc)
  load=$(cut -d' ' -f1 /proc/loadavg)
  echo "preflight: nproc=$cores load1=$load running_c1ib2_shards=$running requested=$NSHARD" | tee "$OUT/logs/preflight.txt"
  (( running + NSHARD <= MAX_TOTAL )) || { echo "refused: $running running + $NSHARD > MAX_TOTAL=$MAX_TOTAL" >&2; exit 4; }
  if [[ "${LOAD_GUARD:-1}" == 1 ]]; then
    busy=$(awk -v l="$load" -v r="$running" -v n="$NSHARD" 'BEGIN { m = (l > r) ? l : r; printf "%d", m + n + 0.5 }')
    (( busy + 16 <= cores )) || { echo "refused: load1 $load + $NSHARD shards leaves < 16 of $cores cores free (LOAD_GUARD=0 to override)" >&2; exit 5; }
  fi
  printf '%q ' bash "$CODE/launch_c1ib2.sh" "$MODE" "$OUT" "$NSHARD" "$@" > "$OUT/logs/launch_argv.txt"
  tmux new-session -d -s "$SESSION" "HEADROOM_INNER=1 $(cat "$OUT/logs/launch_argv.txt") > $OUT/logs/launcher.log 2>&1"
  echo "launched tmux $SESSION; log $OUT/logs/launcher.log"
  exit 0
fi

export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/cache_headroom
export MPLCONFIGDIR=/data/guoyikun/tmp/cache_headroom TORCH_HOME=/data/guoyikun/tmp/cache_headroom
cd "$CODE"
echo "start $(date -u +%FT%TZ) mode=$MODE nshard=$NSHARD out=$OUT" > "$OUT/logs/lifecycle.txt"
pids=()
for ((i = 0; i < NSHARD; i++)); do
  "$PY" -B "$CODE/driver_c1ib2.py" --mode "$MODE" --out "$OUT" --shard "$i" --nshard "$NSHARD" "$@" \
    > "$OUT/logs/shard_$(printf %03d "$i").log" 2>&1 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
if (( fail == 0 )); then
  "$PY" -B "$CODE/driver_c1ib2.py" --mode merge --out "$OUT" > "$OUT/logs/merge.log" 2>&1 \
    && echo "merge ok" >> "$OUT/logs/lifecycle.txt" || echo "merge FAILED" >> "$OUT/logs/lifecycle.txt"
fi
echo "done" >> "$OUT/logs/lifecycle.txt"
