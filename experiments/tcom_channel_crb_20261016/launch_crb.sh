#!/bin/bash
# CRB reference main run (protocol.md section 7 step 3): P1 frames 0..499, 30 single-thread shards, GD on frames < 100.
# Run inside tmux g_crb on deinlab; rows stay remote (gzip + md5 after the run).
set -u
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tcom_channel_crb_20261016
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source ~/.bashrc; conda activate AFDM
NSHARD=30
mkdir -p out/main
for s in $(seq 0 $((NSHARD - 1))); do
  python crb_driver.py --out out/main --frames 500 --gd-frames 100 --shard $s --nshard $NSHARD > out/main/shard$(printf %03d $s).log 2>&1 &
done
wait
echo "main done $(date -u +%FT%TZ)" >> out/main/STATUS.txt
