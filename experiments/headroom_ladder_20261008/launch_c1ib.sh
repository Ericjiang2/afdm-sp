#!/usr/bin/env bash
# Launch N single-thread CPU shards of driver_c1ib.py (C1 inner-update budget run, IB) inside tmux (deinlab only).
#   launch_c1ib.sh <generate> <out_dir> <nshard> [driver_c1ib.py args...]
# Full run (IB_T40,IB_T80; L 8-24 x frames 0-299 x 2 arms; defaults of driver_c1ib.py; 75 shards x 4 frames):
#   launch_c1ib.sh generate $REM/out/c1ib 75
# Determinism set (IB_T20 vs stored c1i FULL_R4; frames 0-29, 30 shards x 1 frame):
#   SESSION=g_c1ib_det launch_c1ib.sh generate $REM/out/c1ib_det 30 --arms IB_T20 --frames 30
# Smoke: launch_c1ib.sh generate /data/guoyikun/tmp/c1ib_smoke 2 --Ls 8,24 --frames 2 --arms IB_T20,IB_T80
#   (merge runs automatically when all shards succeed)
#
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo,
# CPU only (CUDA hidden) so no GPU check is needed; <= 90 shards (>= 16 of the 128 cores stay free).
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/headroom_ladder_20261008"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
SESSION="${SESSION:-g_c1ib}"
MODE="$1"; OUT="$2"; NSHARD="$3"; shift 3
case "$OUT" in /data/guoyikun/*) ;; *) echo "OUT must be under /data/guoyikun" >&2; exit 2;; esac
(( NSHARD >= 1 && NSHARD <= 90 )) || { echo "nshard must be 1..90" >&2; exit 2; }
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom

if [[ "${HEADROOM_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  printf '%q ' bash "$CODE/launch_c1ib.sh" "$MODE" "$OUT" "$NSHARD" "$@" > "$OUT/logs/launch_argv.txt"
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
  "$PY" -B "$CODE/driver_c1ib.py" --mode "$MODE" --out "$OUT" --shard "$i" --nshard "$NSHARD" "$@" \
    > "$OUT/logs/shard_$(printf %03d "$i").log" 2>&1 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
if (( fail == 0 )); then
  "$PY" -B "$CODE/driver_c1ib.py" --mode merge --out "$OUT" > "$OUT/logs/merge.log" 2>&1 \
    && echo "merge ok" >> "$OUT/logs/lifecycle.txt" || echo "merge FAILED" >> "$OUT/logs/lifecycle.txt"
fi
echo "done" >> "$OUT/logs/lifecycle.txt"
