#!/bin/bash
# OPERATIONAL wrapper (no scientific content): resume the E-3 main run in waves of the NSHARD=48 shard set, at most 24 processes at a time
# (PROTOCOL.md section 11 O1: cap 60 core-h; the first 1314 rows ran with 48 concurrent shards at x1.9 contention and the run was stopped by hand).
# It calls the frozen e3_driver.py unchanged with the same arguments as launch_e3.sh MODE=run (--nshard 48), so load_done skips finished keys.
#   WAVES="0-23 24-47" bash launch_e3_waves.sh        (default)
# Create out/main/STOP_WAVES to prevent the next wave from starting (cap-stop rule).  Run inside tmux g_e3 on deinlab.
set -u
WAVES=${WAVES:-"0-23 24-47"}
NSHARD=48
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_e3_sbl_20261017
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
[ -f out/calibrate/GRID.json ] || { echo "abort: out/calibrate/GRID.json missing" >&2; exit 3; }
mkdir -p out/main
for wave in $WAVES; do
  lo=${wave%-*}; hi=${wave#*-}; need=$((hi - lo + 1))
  if [ -f out/main/STOP_WAVES ]; then echo "STOP_WAVES present: wave $wave not started" >> out/main/STATUS.txt; exit 6; fi
  if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$need" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
    echo "abort: load $(cat /proc/loadavg) + $need processes would leave < 16 cores free" >&2; exit 1
  fi
  echo "wave $wave start $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/main/STATUS.txt
  for s in $(seq $lo $hi); do
    python e3_driver.py --mode run --out out/main --grid out/calibrate/GRID.json --frame-offset 4000 --frames 400 --shard $s --nshard $NSHARD >> out/main/shard$(printf %03d $s).log 2>&1 &
  done
  wait
  echo "wave $wave done $(date -u +%FT%TZ)" >> out/main/STATUS.txt
done
echo "shards done $(date -u +%FT%TZ)" >> out/main/STATUS.txt
(cd out/main && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
echo "run done $(date -u +%FT%TZ)" >> out/main/STATUS.txt
