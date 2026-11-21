#!/bin/bash
# E-2 launcher (modelled on tf_cstate_e1_20261017/launch_e1.sh).  Run inside tmux g_e2 on deinlab; CPU only, single-thread shards, keeps >= 16 cores free.
#   MODE=gate       cgate (CG1-CG3, 1 process) + real-state gates G1-G5 on P1 frames 0..19 (20 shards) + two smoke runs of 12 triggered
#                   units each (R: P1 frames 0..19 at 5.0/6.0/7.0 dB; C: frames 9000.. at a provisional 10 dB, SMOKE ONLY), all 8 arms
#   MODE=calibrate  C family, F0 only, frames 5000..5099, candidate SNR 6..20 step 2, both rho (NSHARD shards) -> out/calibrate/GRID.json
#   MODE=run_R      family R main run: P1 frames 3000..3999, all 32000 keys get F0, triggered keys get the 8 arms -> out/main_R
#   MODE=run_C      family C main run: frames 0..999, SNR grid from out/calibrate/GRID.json -> out/main_C
#   MODE=agg        e2_agg.py over out/main_R and out/main_C
# NSHARD defaults: gate 20 (+3 processes), calibrate 50, run_R 64, run_C 32 (run_R and run_C may run at the same time: 96 shards).
set -u
MODE=${MODE:-gate}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_cstate_e2_20261017
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
case "$MODE" in
  gate) NSHARD=${NSHARD:-20}; need=$((NSHARD + 3)) ;;
  calibrate) NSHARD=${NSHARD:-50}; need=$NSHARD ;;
  run_R) NSHARD=${NSHARD:-64}; need=$NSHARD ;;
  run_C) NSHARD=${NSHARD:-32}; need=$NSHARD ;;
  agg) NSHARD=1; need=1 ;;
  *) echo "unknown MODE $MODE" >&2; exit 2 ;;
esac
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$need" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
  echo "abort: load $(cat /proc/loadavg) + $need processes would leave < 16 cores free" >&2; exit 1
fi
pack() {  # gzip rows + md5 manifest of one output directory
  (cd "$1" && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
}
case "$MODE" in
  gate)
    mkdir -p out/gate out/smoke_R out/smoke_C
    python e2_driver.py --mode cgate --out out/gate > out/gate/cgate.log 2>&1 &
    for s in $(seq 0 $((NSHARD - 1))); do
      python e2_driver.py --mode gate --out out/gate --frames 20 --shard $s --nshard $NSHARD > out/gate/gate_shard$(printf %03d $s).log 2>&1 &
    done
    python e2_driver.py --mode run --family R --smoke --snr-list 5.0,6.0,7.0 --frame-offset 0 --frames 20 --max-triggered 12 --out out/smoke_R > out/smoke_R/shard000.log 2>&1 &
    python e2_driver.py --mode run --family C --smoke --smoke-snr 10 --frame-offset 9000 --frames 12 --max-triggered 12 --out out/smoke_C > out/smoke_C/shard000.log 2>&1 &
    wait
    python e2_driver.py --mode gate-merge --out out/gate > out/gate/merge.log 2>&1
    echo "gate+smoke done $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/gate/STATUS.txt ;;
  calibrate)
    mkdir -p out/calibrate
    echo "start NSHARD=$NSHARD $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/calibrate/STATUS.txt
    for s in $(seq 0 $((NSHARD - 1))); do
      python e2_driver.py --mode calibrate --family C --out out/calibrate --frame-offset 5000 --frames 100 --shard $s --nshard $NSHARD > out/calibrate/shard$(printf %03d $s).log 2>&1 &
    done
    wait
    python e2_driver.py --mode calibrate-merge --out out/calibrate > out/calibrate/merge.log 2>&1
    md5sum out/calibrate/GRID.json > out/calibrate/GRID_MD5.txt
    echo "calibration done $(date -u +%FT%TZ)" >> out/calibrate/STATUS.txt ;;
  run_R)
    mkdir -p out/main_R
    echo "start NSHARD=$NSHARD $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/main_R/STATUS.txt
    for s in $(seq 0 $((NSHARD - 1))); do
      python e2_driver.py --mode run --family R --out out/main_R --frame-offset 3000 --frames 1000 --shard $s --nshard $NSHARD > out/main_R/shard$(printf %03d $s).log 2>&1 &
    done
    wait
    echo "shards done $(date -u +%FT%TZ)" >> out/main_R/STATUS.txt
    pack out/main_R
    echo "run_R done $(date -u +%FT%TZ)" >> out/main_R/STATUS.txt ;;
  run_C)
    [ -f out/calibrate/GRID.json ] || { echo "abort: out/calibrate/GRID.json missing (run MODE=calibrate first)" >&2; exit 3; }
    mkdir -p out/main_C
    echo "start NSHARD=$NSHARD grid_md5=$(md5sum out/calibrate/GRID.json | cut -d' ' -f1) $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/main_C/STATUS.txt
    for s in $(seq 0 $((NSHARD - 1))); do
      python e2_driver.py --mode run --family C --out out/main_C --grid out/calibrate/GRID.json --frame-offset 0 --frames 1000 --shard $s --nshard $NSHARD > out/main_C/shard$(printf %03d $s).log 2>&1 &
    done
    wait
    echo "shards done $(date -u +%FT%TZ)" >> out/main_C/STATUS.txt
    pack out/main_C
    echo "run_C done $(date -u +%FT%TZ)" >> out/main_C/STATUS.txt ;;
  agg)
    mkdir -p out/analysis
    python e2_agg.py --rows-R out/main_R --rows-C out/main_C --grid out/calibrate/GRID.json --gates out/gate/gates.json --cgates out/gate/cgates.json --out out/analysis > out/analysis/agg.log 2>&1
    echo "agg done $(date -u +%FT%TZ)" >> out/analysis/STATUS.txt ;;
esac
