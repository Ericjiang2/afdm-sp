#!/bin/bash
# sbl_joint_detector launcher (modelled on slot_mismatch_20261019/launch_sm.sh).  Run inside tmux g_sj on deinlab; CPU only, single-thread shards, keeps >= 16 cores free.
#   MODE=gate    24 saved E-3 keys, 1 process -> $OUT/gate_shard000.json
#   MODE=pilot5  frames 9100..9299, rho .3, U+G, 7/8 dB (NSHARD default 40) -> $OUT, then sj_agg.py
set -u
MODE=${MODE:-gate}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_joint_detector_20261019
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
case "$MODE" in
  gate) NSHARD=${NSHARD:-1} ;;
  pilot5) NSHARD=${NSHARD:-40} ;;
  *) echo "unknown MODE $MODE" >&2; exit 2 ;;
esac
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$NSHARD" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
  echo "abort: load $(cat /proc/loadavg) + $NSHARD processes would leave < 16 cores free" >&2; exit 1
fi
OUT=${OUT:-out/$MODE}
mkdir -p $OUT
echo "start MODE=$MODE NSHARD=$NSHARD $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> $OUT/STATUS.txt
for s in $(seq 0 $((NSHARD - 1))); do
  python sj_driver.py --mode $MODE --out $OUT --shard $s --nshard $NSHARD > $OUT/shard$(printf %03d $s).log 2>&1 &
done
wait
echo "shards done $(date -u +%FT%TZ)" >> $OUT/STATUS.txt
case "$MODE" in
  gate) ;;
  pilot5) (cd $OUT && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
          python sj_agg.py --rows $OUT --out $OUT/pilot5_summary.json > $OUT/agg.log 2>&1 ;;
esac
echo "$MODE done $(date -u +%FT%TZ)" >> $OUT/STATUS.txt
