#!/bin/bash
# Genie-support main run (protocol.md section 5 step 4): P1 frames 0..1999, both arms, NSHARD single-thread shards.
# Run inside tmux g_gs on deinlab after checking free cores (keep >= 16 free); rows stay remote (gzip + md5 after the run).
set -u
NSHARD=${NSHARD:-96}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tcom_genie_support_20261016
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
mkdir -p out/main
echo "start NSHARD=$NSHARD $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/main/STATUS.txt
for s in $(seq 0 $((NSHARD - 1))); do
  python gs_driver.py --out out/main --frames 2000 --shard $s --nshard $NSHARD > out/main/shard$(printf %03d $s).log 2>&1 &
done
wait
echo "main done $(date -u +%FT%TZ)" >> out/main/STATUS.txt
