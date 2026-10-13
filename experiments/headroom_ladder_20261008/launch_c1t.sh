#!/usr/bin/env bash
# Launch N single-thread CPU shards of driver_c1t.py (C1-TDL realism experiment) inside tmux (deinlab only).
#   launch_c1t.sh <generate> <out_dir> <nshard> [driver_c1t.py args...]
# Example (smoke): launch_c1t.sh generate $RR/experiments/headroom_ladder_20261008/out/c1_smoke 8 --Ls 4,32 --rho-list 0.2,0.5 \
#   --snr-list 8 --frames 8 --entropy-hex <64 hex>   (merge runs automatically when all shards succeed)
#
# Rules (project CLAUDE.md): only /data/guoyikun, scratch /data/guoyikun/tmp, tmux name g_*, no sudo,
# CPU only (CUDA hidden) so no GPU check is needed; leave >= 16 cores free (<= 100 shards).
set -Eeuo pipefail
PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CODE="$PROJECT/experiments/headroom_ladder_20261008"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
SESSION="${SESSION:-g_c1t}"
MODE="$1"; OUT="$2"; NSHARD="$3"; shift 3
case "$OUT" in /data/guoyikun/*) ;; *) echo "OUT must be under /data/guoyikun" >&2; exit 2;; esac
(( NSHARD >= 1 && NSHARD <= 64 )) || { echo "nshard must be 1..64" >&2; exit 2; }
mkdir -p "$OUT/logs" /data/guoyikun/tmp/cache_headroom

if [[ "${HEADROOM_INNER:-0}" != 1 ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then echo "tmux session $SESSION exists" >&2; exit 3; fi
  printf '%q ' bash "$CODE/launch_c1t.sh" "$MODE" "$OUT" "$NSHARD" "$@" > "$OUT/logs/launch_argv.txt"
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
  "$PY" -B "$CODE/driver_c1t.py" --mode "$MODE" --out "$OUT" --shard "$i" --nshard "$NSHARD" "$@" \
    > "$OUT/logs/shard_$(printf %03d "$i").log" 2>&1 &
  pids+=("$!")
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
if (( fail == 0 )); then
  "$PY" -B "$CODE/driver_c1t.py" --mode merge --out "$OUT" > "$OUT/logs/merge.log" 2>&1 \
    && echo "merge ok" >> "$OUT/logs/lifecycle.txt" || echo "merge FAILED" >> "$OUT/logs/lifecycle.txt"
fi
echo "done" >> "$OUT/logs/lifecycle.txt"
