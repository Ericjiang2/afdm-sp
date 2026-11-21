#!/bin/bash
# Amendment A1 (post hoc): MODE=gate -> A1-G2 on frames 0..19 + 20-frame smoke (A1-G1 per row, A1-G3 timing);
# MODE=run -> GS+C on frames 0..1999, NSHARD single-thread shards.  Run inside tmux g_gs on deinlab (keep >= 16 cores free).
set -u
MODE=${MODE:-gate}
NSHARD=${NSHARD:-96}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tcom_genie_support_20261016
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
if [ "$MODE" = gate ]; then
  mkdir -p out/a1_gates out/a1_smoke
  for s in $(seq 0 19); do
    python gs_cstate.py --mode gate --out out/a1_gates --frames 20 --shard $s --nshard 20 > out/a1_gates/g2_shard$(printf %03d $s).log 2>&1 &
    python gs_cstate.py --mode run --out out/a1_smoke --frames 20 --shard $s --nshard 20 > out/a1_smoke/shard$(printf %03d $s).log 2>&1 &
  done
  wait
  echo "a1 gates done $(date -u +%FT%TZ)" >> out/a1_gates/STATUS.txt
else
  mkdir -p out/a1
  echo "start NSHARD=$NSHARD $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/a1/STATUS.txt
  for s in $(seq 0 $((NSHARD - 1))); do
    python gs_cstate.py --mode run --out out/a1 --frames 2000 --shard $s --nshard $NSHARD > out/a1/shard$(printf %03d $s).log 2>&1 &
  done
  wait
  echo "a1 done $(date -u +%FT%TZ)" >> out/a1/STATUS.txt
fi
