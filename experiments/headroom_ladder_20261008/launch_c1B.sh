#!/usr/bin/env bash
# Remote-only B0/B1 launcher. Run from a shell on deinlab; SSH callers use ssh -n.
# launch_c1B.sh b0|generate|merge /data/guoyikun/... [nshard]
set -Eeuo pipefail

PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/headroom_ladder_20261008"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
SCRIPT="$CODE/launch_c1B.sh"

if [[ "${1:-}" == '--inner' ]]; then
  shift
  INNER=1
else
  INNER=0
fi
MODE="${1:-}"
OUT="${2:-}"
NSHARD="${3:-1}"
[[ "$MODE" == b0 || "$MODE" == generate || "$MODE" == merge ]] || { echo 'mode must be b0|generate|merge' >&2; exit 2; }
case "$OUT" in /data/guoyikun/*) ;; *) echo 'out must be under /data/guoyikun' >&2; exit 2;; esac
[[ "$NSHARD" =~ ^[0-9]+$ ]] && (( NSHARD >= 1 && NSHARD <= 32 )) || { echo 'nshard must be 1..32' >&2; exit 2; }
[[ -f "$CODE/driver_c1B.py" && -f "$CODE/c1B_rx.py" ]] || { echo 'B sources missing on remote' >&2; exit 2; }
mkdir -p "$OUT/logs"

if (( INNER == 0 )) && [[ "$MODE" != merge ]]; then
  SESSION="${SESSION:-g_B$(date -u +%Y%m%dT%H%M%S)_$$}"
  [[ "$SESSION" == g_B* && "$SESSION" =~ ^[A-Za-z0-9_]+$ ]] || { echo 'session must begin g_B and contain alnum/_' >&2; exit 2; }
  SOCKET="$OUT/logs/tmux.sock"
  if tmux -S "$SOCKET" has-session -t "$SESSION" 2>/dev/null; then
    echo "tmux session exists: $SESSION" >&2
    exit 3
  fi
  printf -v TMUX_COMMAND '%q ' bash "$SCRIPT" --inner "$MODE" "$OUT" "$NSHARD"
  printf -v LAUNCH_LOG '%q' "$OUT/logs/launcher.log"
  tmux -S "$SOCKET" new-session -d -s "$SESSION" "$TMUX_COMMAND > $LAUNCH_LOG 2>&1"
  printf '%s\n' "$SESSION" > "$OUT/logs/session.txt"
  echo "launched $SESSION; $OUT/logs/lifecycle.jsonl"
  exit 0
fi

export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
SCRATCH=$(mktemp -d /data/guoyikun/tmp/c1B_XXXXXXXX)
export TMPDIR="$SCRATCH" XDG_CACHE_HOME="$SCRATCH/cache" MPLCONFIGDIR="$SCRATCH/cache"
export TORCH_HOME="$SCRATCH/cache"
on_exit() {
  code=$?
  if [[ -n "${STATUS:-}" ]]; then
    printf '{"event":"launcher_exit","exit_code":%d,"utc":"%s"}\n' "$code" "$(date -u +%FT%TZ)" >> "$STATUS"
  fi
  rm -rf -- "$SCRATCH"
}
trap on_exit EXIT
cd "$CODE"

if [[ "$MODE" == merge ]]; then
  "$PY" -B "$CODE/driver_c1B.py" --mode merge --out "$OUT"
  exit 0
fi

STATUS="$OUT/logs/lifecycle.jsonl"
exec 9> "$OUT/.c1B.lock"
flock -n 9 || { echo 'output directory already has an active B job' >&2; exit 3; }
printf '{"event":"start","mode":"%s","nshard":%d,"pid":%d,"utc":"%s"}\n' \
  "$MODE" "$NSHARD" "$$" "$(date -u +%FT%TZ)" >> "$STATUS"
# GNU nproc observes OMP_NUM_THREADS; query affinity capacity independently
# of the one-thread numerical setting used by every shard.
CORES=$(env -u OMP_NUM_THREADS -u OMP_THREAD_LIMIT nproc)
(( CORES >= 17 && NSHARD <= CORES - 16 )) || { echo 'would leave fewer than 16 CPUs free' >&2; exit 3; }
pids=()
for ((i = 0; i < NSHARD; i++)); do
  # Respect other users' measured load as well as the hard shard ceiling.
  deadline=$((SECONDS + 1200))
  while ! awk -v cap="$((CORES - 16))" '{exit !($1 + 1 <= cap)}' /proc/loadavg; do
    if (( SECONDS >= deadline )); then
      printf '{"event":"load_guard_timeout","shard":%d,"utc":"%s"}\n' "$i" "$(date -u +%FT%TZ)" >> "$STATUS"
      exit 4
    fi
    sleep 10
  done
  shard=$(printf %03d "$i")
  "$PY" -B "$CODE/driver_c1B.py" --mode "$MODE" --out "$OUT" --shard "$i" --nshard "$NSHARD" \
    > "$OUT/logs/shard_${shard}.log" 2>&1 &
  pid=$!
  pids+=("$pid")
  printf '{"event":"shard_start","shard":%d,"pid":%d,"utc":"%s"}\n' \
    "$i" "$pid" "$(date -u +%FT%TZ)" >> "$STATUS"
done

failed=0
for ((i = 0; i < NSHARD; i++)); do
  code=0
  wait "${pids[$i]}" || code=$?
  printf '{"event":"shard_exit","shard":%d,"pid":%d,"exit_code":%d,"utc":"%s"}\n' \
    "$i" "${pids[$i]}" "$code" "$(date -u +%FT%TZ)" >> "$STATUS"
  (( code == 0 )) || failed=$((failed + 1))
done
if (( failed != 0 )); then
  printf '{"event":"failed","shards_failed":%d,"utc":"%s"}\n' "$failed" "$(date -u +%FT%TZ)" >> "$STATUS"
  exit 5
fi
code=0
"$PY" -B "$CODE/driver_c1B.py" --mode merge --out "$OUT" > "$OUT/logs/merge.log" 2>&1 || code=$?
printf '{"event":"merge_exit","exit_code":%d,"utc":"%s"}\n' "$code" "$(date -u +%FT%TZ)" >> "$STATUS"
exit "$code"
