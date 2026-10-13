#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
root=issues/20261001-afdm-innovation-exploration
while tmux has-session -t g_innovation_frontier 2>/dev/null; do sleep 20; done
for block in 0 1 2 3; do test "$(cat "$root/experiments/frontier_${block}_v1.exit")" = 0; done
bash "$root/experiments/launch_noncircular.sh"
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/issues/20261001-afdm-innovation-exploration/scratch
export MPLCONFIGDIR="$TMPDIR/matplotlib" XDG_CACHE_HOME="$TMPDIR/cache"
for kind in confirmation repairs; do
 taskset -c 64 /home/guoyikun/.conda/envs/AFDM/bin/python "$root/analysis/score_new_runs.py" "$kind" > "$root/analysis/${kind}_scored_v2.json" 2> "$root/analysis/${kind}_scored_v2.log"
done
for kind in frontier noncircular; do
 taskset -c 64 /home/guoyikun/.conda/envs/AFDM/bin/python "$root/analysis/score_${kind}.py" > "$root/analysis/${kind}_scored.json" 2> "$root/analysis/${kind}_scored.log"
done
