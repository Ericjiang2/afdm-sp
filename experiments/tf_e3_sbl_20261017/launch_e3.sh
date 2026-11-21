#!/bin/bash
# E-3 launcher (modelled on tf_cstate_e2_20261017/launch_e2.sh).  Run inside tmux g_e3* on deinlab; CPU only, single-thread shards, keeps >= 16 cores free.
#   MODE=gate       T3 + convention/data-scaling checks + T2 on a real frame + T4 on P1 frames 0..19 (20 shards), then two smoke runs (SMOKE ONLY):
#                   all 4 variants on 8 frames x 4 cells at a provisional 8 dB (frames 8000..8007), and an L-hard-only calibration timing run
#   MODE=calibrate  L-hard only, frames 6000..6099, candidate SNR 4..14 dB, 4 cells -> out/calibrate/GRID.json (+ md5)
#   MODE=run        main run: frames 4000..4399, SNR grid per cell from out/calibrate/GRID.json, all 4 variants -> out/main
#   MODE=riter      report-only R-iter robustness check (PROTOCOL.md section 11 O2), AFTER the main run: the frozen 200-key subsample (seed 20261017,
#                   stratified over cell x SNR), L-diag and L-cov only, max_iter = 400 -> out/riter
#   MODE=agg        e3_agg.py over out/main (+ out/riter when present)
# NSHARD defaults: gate 20 (+6 processes), calibrate 48, run 48, riter 48; calibrate / run / riter refuse NSHARD > 48 (PROTOCOL.md section 11 O1).
set -u
MODE=${MODE:-gate}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_e3_sbl_20261017
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
case "$MODE" in
  gate) NSHARD=${NSHARD:-20}; need=$((NSHARD + 6)) ;;
  calibrate) NSHARD=${NSHARD:-48}; need=$NSHARD ;;
  run) NSHARD=${NSHARD:-48}; need=$NSHARD ;;
  riter) NSHARD=${NSHARD:-48}; need=$NSHARD ;;
  agg) NSHARD=1; need=1 ;;
  *) echo "unknown MODE $MODE" >&2; exit 2 ;;
esac
case "$MODE" in calibrate|run|riter)
  if [ "$NSHARD" -gt 48 ]; then echo "abort: NSHARD=$NSHARD exceeds the cap of 48 (PROTOCOL.md section 11 O1)" >&2; exit 4; fi ;;
esac
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$need" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
  echo "abort: load $(cat /proc/loadavg) + $need processes would leave < 16 cores free" >&2; exit 1
fi
case "$MODE" in
  gate)
    mkdir -p out/gate out/smoke_run out/smoke_cal
    for s in $(seq 0 $((NSHARD - 1))); do
      python e3_driver.py --mode gate --out out/gate --frames 20 --frame-offset 0 --shard $s --nshard $NSHARD > out/gate/gate_shard$(printf %03d $s).log 2>&1 &
    done
    for s in 0 1 2 3; do
      python e3_driver.py --mode run --smoke --smoke-snr 8 --frame-offset 8000 --frames 8 --shard $s --nshard 4 --out out/smoke_run > out/smoke_run/shard$(printf %03d $s).log 2>&1 &
    done
    for s in 0 1; do
      python e3_driver.py --mode calibrate --smoke --snr-list 6,10 --frame-offset 8100 --frames 4 --shard $s --nshard 2 --out out/smoke_cal > out/smoke_cal/shard$(printf %03d $s).log 2>&1 &
    done
    wait
    python e3_driver.py --mode gate-merge --out out/gate > out/gate/merge.log 2>&1
    echo "gate+smoke done $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/gate/STATUS.txt ;;
  calibrate)
    mkdir -p out/calibrate
    echo "start NSHARD=$NSHARD $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/calibrate/STATUS.txt
    for s in $(seq 0 $((NSHARD - 1))); do
      python e3_driver.py --mode calibrate --out out/calibrate --frame-offset 6000 --frames 100 --shard $s --nshard $NSHARD > out/calibrate/shard$(printf %03d $s).log 2>&1 &
    done
    wait
    python e3_driver.py --mode calibrate-merge --out out/calibrate > out/calibrate/merge.log 2>&1
    md5sum out/calibrate/GRID.json > out/calibrate/GRID_MD5.txt
    echo "calibration done $(date -u +%FT%TZ)" >> out/calibrate/STATUS.txt ;;
  run)
    [ -f out/calibrate/GRID.json ] || { echo "abort: out/calibrate/GRID.json missing (run MODE=calibrate first)" >&2; exit 3; }
    mkdir -p out/main
    echo "start NSHARD=$NSHARD grid_md5=$(md5sum out/calibrate/GRID.json | cut -d' ' -f1) $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/main/STATUS.txt
    for s in $(seq 0 $((NSHARD - 1))); do
      python e3_driver.py --mode run --out out/main --grid out/calibrate/GRID.json --frame-offset 4000 --frames 400 --shard $s --nshard $NSHARD > out/main/shard$(printf %03d $s).log 2>&1 &
    done
    wait
    echo "shards done $(date -u +%FT%TZ)" >> out/main/STATUS.txt
    (cd out/main && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
    echo "run done $(date -u +%FT%TZ)" >> out/main/STATUS.txt ;;
  riter)
    [ -f out/calibrate/GRID.json ] || { echo "abort: out/calibrate/GRID.json missing" >&2; exit 3; }
    [ -f out/main/STATUS.txt ] && grep -q "run done" out/main/STATUS.txt || { echo "abort: the main run has not finished (out/main/STATUS.txt lacks 'run done')" >&2; exit 5; }
    mkdir -p out/riter
    echo "start NSHARD=$NSHARD grid_md5=$(md5sum out/calibrate/GRID.json | cut -d' ' -f1) $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/riter/STATUS.txt
    for s in $(seq 0 $((NSHARD - 1))); do
      python e3_driver.py --mode riter --out out/riter --grid out/calibrate/GRID.json --shard $s --nshard $NSHARD > out/riter/shard$(printf %03d $s).log 2>&1 &
    done
    wait
    echo "shards done $(date -u +%FT%TZ)" >> out/riter/STATUS.txt
    (cd out/riter && md5sum rows_shard*.jsonl config_shard*.json > REMOTE_ROWS_MD5.txt)
    echo "riter done $(date -u +%FT%TZ)" >> out/riter/STATUS.txt ;;
  agg)
    mkdir -p out/analysis
    RITER=""; [ -d out/riter ] && grep -q "riter done" out/riter/STATUS.txt 2>/dev/null && RITER="--riter out/riter"
    python e3_agg.py --rows out/main --grid out/calibrate/GRID.json --gates out/gate/gates.json $RITER --out out/analysis > out/analysis/agg.log 2>&1
    echo "agg done $(date -u +%FT%TZ)" >> out/analysis/STATUS.txt ;;
esac
