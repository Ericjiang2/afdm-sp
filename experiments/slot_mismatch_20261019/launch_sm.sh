#!/bin/bash
# slot_mismatch launcher (modelled on tf_cstate_e2_20261017/launch_e2.sh).  Run inside tmux g_sm on deinlab; CPU only, single-thread shards, keeps >= 16 cores free.
#   MODE=gate   G1/G2/G4 gates (NSHARD shards, default 24) -> out/gate/gates.json
#   Optional env: OUT (default out/$MODE) and EXTRA (extra sm_driver args, e.g. a different pilot slice).
#   MODE=gate-k4  kernel-variant gate (1 process): variant with max_edits=2 reproduces the saved pilot-2 A1/A2 -> $OUT/gates_k4_shard000.json
#   MODE=pilot3   pilot-2 keys again with A1e4/A2e4 (max_edits=4) on F0_s-triggered keys, then sm_agg3.py (OUT=out/pilot3, EXTRA = the pilot-2 slice arguments)
#   MODE=gate4    call-path gate for pilot4 (1 process): frozen 10-18 process_key_k reproduces saved K-diag / K-diag-fullfix decoded sha -> $OUT/gate4_shard000.json
#   MODE=pilot4   detector-clue mini simulation (A2-prod / A2-fix / A2-merge on pilot-2 cap-8 triggered keys with an A2 co-delay pair), then sm_agg4.py
#   MODE=pilot  exploratory slice: family M, s in {8,12}, scenarios G,U, rho .3, SNR 6.0/6.5/7.0, frames 7800..7999 (NSHARD default 40) -> out/pilot, then sm_agg.py
set -u
MODE=${MODE:-gate}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/slot_mismatch_20261019
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
case "$MODE" in
  gate) NSHARD=${NSHARD:-24} ;;
  pilot|pilot3|pilot4) NSHARD=${NSHARD:-40} ;;
  gate-k4|gate4) NSHARD=1 ;;
  *) echo "unknown MODE $MODE" >&2; exit 2 ;;
esac
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$NSHARD" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
  echo "abort: load $(cat /proc/loadavg) + $NSHARD processes would leave < 16 cores free" >&2; exit 1
fi
OUT=${OUT:-out/$MODE}
mkdir -p $OUT
echo "start MODE=$MODE NSHARD=$NSHARD $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> $OUT/STATUS.txt
for s in $(seq 0 $((NSHARD - 1))); do
  python sm_driver.py --mode $MODE --out $OUT --shard $s --nshard $NSHARD ${EXTRA:-} > $OUT/shard$(printf %03d $s).log 2>&1 &
done
wait
echo "shards done $(date -u +%FT%TZ)" >> $OUT/STATUS.txt
case "$MODE" in
  gate) python sm_driver.py --mode gate-merge --out $OUT > $OUT/merge.log 2>&1 ;;
  gate-k4|gate4) ;;
  pilot4) (cd $OUT && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
          python sm_agg4.py --pilot2 out/pilot2 --pilot4 $OUT --out $OUT/pilot4_summary.json > $OUT/agg.log 2>&1 ;;
  pilot3) (cd $OUT && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
          python sm_agg3.py --pilot2 out/pilot2 --pilot3 $OUT --out $OUT/pilot3_summary.json > $OUT/agg.log 2>&1 ;;
  pilot) (cd $OUT && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
         python sm_agg.py --rows $OUT --out $OUT/pilot_summary.json > $OUT/agg.log 2>&1 ;;
esac
echo "$MODE done $(date -u +%FT%TZ)" >> $OUT/STATUS.txt
