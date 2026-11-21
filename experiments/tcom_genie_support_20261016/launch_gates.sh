#!/bin/bash
# Gates S1-S6 (protocol.md section 4): S1-S3 on frames 0..19 (20 single-thread shards), then a 20-frame gs_driver smoke
# (S4 asserted per row) and the smoke stage (S5, S6).  Run inside tmux g_gs on deinlab.
set -u
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tcom_genie_support_20261016
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
mkdir -p out/gates out/smoke
for s in $(seq 0 19); do
  python gs_gates.py --stage s123 --out out/gates --shard $s --nshard 20 > out/gates/s123_shard$(printf %03d $s).log 2>&1 &
  python gs_driver.py --out out/smoke --frames 20 --shard $s --nshard 20 > out/smoke/shard$(printf %03d $s).log 2>&1 &
done
wait
python gs_gates.py --stage merge --out out/gates > out/gates/merge.log 2>&1
python gs_gates.py --stage smoke --out out/gates --smoke-dir out/smoke > out/gates/smoke.log 2>&1
echo "gates done $(date -u +%FT%TZ)" >> out/gates/STATUS.txt
