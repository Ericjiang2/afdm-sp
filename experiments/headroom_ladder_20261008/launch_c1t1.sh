#!/usr/bin/env bash
# C1 T1 transfer curves (c1_t1_transfer.py) on deinlab: checks -> stage A shards -> select -> stage B shards -> merge, inside tmux.
#   launch_c1t1.sh <out_dir> <nshard> [c1_t1_transfer.py grid/frames args...]
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo, CPU only; <= 48 shards.
# FG=1 runs the chain in the foreground (smoke); default launches a detached tmux session (SESSION, default g_c1t1).
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/headroom_ladder_20261008"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
SESSION="${SESSION:-g_c1t1}"
OUT="$1"; NSHARD="$2"; shift 2
case "$OUT" in /data/guoyikun/*) ;; *) echo "OUT must be under /data/guoyikun" >&2; exit 2;; esac
(( NSHARD >= 1 && NSHARD <= 48 )) || { echo "nshard must be 1..48" >&2; exit 2; }
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom

if [[ "${HEADROOM_INNER:-0}" != 1 && "${FG:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  printf '%q ' bash "$CODE/launch_c1t1.sh" "$OUT" "$NSHARD" "$@" > "$OUT/logs/launch_argv.txt"
  tmux new-session -d -s "$SESSION" "HEADROOM_INNER=1 $(cat "$OUT/logs/launch_argv.txt") > $OUT/logs/launcher.log 2>&1"
  echo "launched tmux $SESSION; log $OUT/logs/launcher.log"
  exit 0
fi

source "$CODE/env_single.sh"
cd "$CODE"
S="$CODE/c1_t1_transfer.py"
echo "start $(date -u +%FT%TZ) nshard=$NSHARD out=$OUT args=$*" > "$OUT/logs/lifecycle.txt"
"$PY" -B "$S" --mode checks --out "$OUT" "$@" > "$OUT/logs/checks.log" 2>&1
echo "checks ok $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
run_stage() {
  local st="$1"; shift; local pids=(); local fail=0
  for ((i = 0; i < NSHARD; i++)); do
    "$PY" -B "$S" --mode run --stage "$st" --shard "$i" --nshard "$NSHARD" --out "$OUT" "$@" \
      > "$OUT/logs/stage${st}_shard_$(printf %03d "$i").log" 2>&1 &
    pids+=("$!")
  done
  for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
  echo "stage $st shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
  (( fail == 0 ))
}
run_stage A "$@"
"$PY" -B "$S" --mode select --out "$OUT" "$@" > "$OUT/logs/select.log" 2>&1
run_stage B "$@"
"$PY" -B "$S" --mode merge --out "$OUT" "$@" > "$OUT/logs/merge.log" 2>&1 \
  && echo "merge ok" >> "$OUT/logs/lifecycle.txt" || echo "merge FAILED" >> "$OUT/logs/lifecycle.txt"
echo "done $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
