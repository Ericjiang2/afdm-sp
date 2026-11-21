#!/bin/bash
# E-1 launcher (modelled on tcom_genie_support_20261016/launch_a1.sh).  Run inside tmux g_e1 on deinlab; CPU only, single-thread shards.
#   MODE=gate  (default)  select triggered keys + real-state gates G1-G5 on frames 0..19 (20 shards, all 8 SNRs) + a 12-unit run-mode smoke
#   MODE=run              main run: select, NSHARD single-thread run shards over all triggered keys, gzip rows, md5 manifest, e1_agg
#   SNR_LIST=4.5,...,8.0 (default: full P1 grid = primary unit set, PROTOCOL.md section 10 O1; the 6.5..8.0 subset is the pre-declared
#   secondary and is analysed from the same rows by e1_agg.py).
# Keeps >= 16 cores free (aborts if load + shards > nproc - 16).
set -u
MODE=${MODE:-gate}
NSHARD=${NSHARD:-64}
SNR_LIST=${SNR_LIST:-4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
need=$([ "$MODE" = gate ] && echo 21 || echo "$NSHARD")
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$need" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
  echo "abort: load $(cat /proc/loadavg) + $need shards would leave < 16 cores free" >&2; exit 1
fi
if [ "$MODE" = gate ]; then
  mkdir -p out/gate out/select out/smoke
  python e1_driver.py --mode select --snr-list "$SNR_LIST" --out out/select > out/select/select.log 2>&1
  for s in $(seq 0 19); do
    python e1_driver.py --mode gate --out out/gate --frames 20 --shard $s --nshard 20 > out/gate/gate_shard$(printf %03d $s).log 2>&1 &
  done
  python e1_driver.py --mode run --keys out/select/triggered_keys.json --out out/smoke --max-units 12 > out/smoke/shard000.log 2>&1 &
  wait
  python e1_driver.py --mode gate-merge --out out/gate > out/gate/merge.log 2>&1
  python e1_agg.py --rows out/smoke --out out/smoke/analysis --boot 2000 > out/smoke/analysis.log 2>&1
  echo "gate+smoke done $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/gate/STATUS.txt
else
  mkdir -p out/main out/select
  python e1_driver.py --mode select --snr-list "$SNR_LIST" --out out/select > out/select/select.log 2>&1
  echo "start NSHARD=$NSHARD SNR_LIST=$SNR_LIST $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/main/STATUS.txt
  for s in $(seq 0 $((NSHARD - 1))); do
    python e1_driver.py --mode run --keys out/select/triggered_keys.json --out out/main --shard $s --nshard $NSHARD > out/main/shard$(printf %03d $s).log 2>&1 &
  done
  wait
  echo "shards done $(date -u +%FT%TZ)" >> out/main/STATUS.txt
  (cd out/main && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
  (cd out/select && md5sum triggered_keys.json > REMOTE_KEYS_MD5.txt)
  python e1_agg.py --rows out/main --keys out/select/triggered_keys.json --gates out/gate/gates.json --out out/main/analysis > out/main/analysis.log 2>&1
  echo "run done $(date -u +%FT%TZ)" >> out/main/STATUS.txt
fi
