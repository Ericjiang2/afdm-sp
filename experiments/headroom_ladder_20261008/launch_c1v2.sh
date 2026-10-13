#!/usr/bin/env bash
# Launch N single-thread CPU shards of driver_c1v2.py (C1 V2 mechanism probe of the round-1 law) inside tmux (deinlab only).
#   launch_c1v2.sh <generate> <out_dir> <nshard> [driver_c1v2.py args...]
# V2 run (6 cells x 40 frames = 240 probes; 20 shards x 2 frames; defaults of driver_c1v2.py = 8 dB, rho .2/.3/.5, L 8/24, frames 600-639):
#   launch_c1v2.sh generate $REM/out/c1v2 20
# Smoke: launch_c1v2.sh generate /data/guoyikun/tmp/c1v2_smoke 2 --frames 2 --frame-offset 600
#   (merge runs automatically when all shards succeed)
#
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo,
# CPU only (CUDA hidden) so no GPU check is needed; <= 24 shards (the server is shared; another job may be running).
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/headroom_ladder_20261008"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
SESSION="${SESSION:-g_c1v2}"
MODE="$1"; OUT="$2"; NSHARD="$3"; shift 3
case "$OUT" in /data/guoyikun/*) ;; *) echo "OUT must be under /data/guoyikun" >&2; exit 2;; esac
(( NSHARD >= 1 && NSHARD <= 24 )) || { echo "nshard must be 1..24" >&2; exit 2; }
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom

if [[ "${HEADROOM_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  printf '%q ' bash "$CODE/launch_c1v2.sh" "$MODE" "$OUT" "$NSHARD" "$@" > "$OUT/logs/launch_argv.txt"
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
  "$PY" -B "$CODE/driver_c1v2.py" --mode "$MODE" --out "$OUT" --shard "$i" --nshard "$NSHARD" "$@" \
    > "$OUT/logs/shard_$(printf %03d "$i").log" 2>&1 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
if (( fail == 0 )); then
  "$PY" -B "$CODE/driver_c1v2.py" --mode merge --out "$OUT" > "$OUT/logs/merge.log" 2>&1 \
    && echo "merge ok" >> "$OUT/logs/lifecycle.txt" || echo "merge FAILED" >> "$OUT/logs/lifecycle.txt"
fi
echo "done" >> "$OUT/logs/lifecycle.txt"
