#!/usr/bin/env bash
# C1 T1 EXIT addendum: 48 single-thread shards of c1_t1_exit.py then merge (tmux g_c1t1x). Usage: launch_c1t1_exit.sh <out_dir> [nshard]
set -Eeuo pipefail
CODE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
OUT="$1"; NSHARD="${2:-48}"
case "$OUT" in /data/guoyikun/*) ;; *) echo "OUT must be under /data/guoyikun" >&2; exit 2;; esac
if [[ "${HEADROOM_INNER:-0}" != 1 ]]; then
  tmux new-session -d -s g_c1t1x "HEADROOM_INNER=1 bash $CODE/launch_c1t1_exit.sh $OUT $NSHARD > $OUT/logs/exit_launcher.log 2>&1"; echo launched; exit 0
fi
source "$CODE/env_single.sh"; cd "$CODE"
pids=(); fail=0
for ((i = 0; i < NSHARD; i++)); do "$PY" -B c1_t1_exit.py --mode run --out "$OUT" --shard "$i" --nshard "$NSHARD" > "$OUT/logs/exit_shard_$(printf %03d "$i").log" 2>&1 & pids+=("$!"); done
for p in "${pids[@]}"; do wait "$p" || fail=$((fail + 1)); done
echo "exit shards_failed=$fail $(date -u +%FT%TZ)" >> "$OUT/logs/lifecycle.txt"
(( fail == 0 )) && "$PY" -B c1_t1_exit.py --mode merge --out "$OUT" > "$OUT/logs/exit_merge.log" 2>&1 && echo "exit merge ok" >> "$OUT/logs/lifecycle.txt"
