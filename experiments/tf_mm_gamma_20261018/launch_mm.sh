#!/bin/bash
# Model-matched Gamma check launcher (task 10-18-model-matched-gamma).  Run inside a tmux session named g_mm* on deinlab; CPU only, single-thread processes.
#   MODE=gate   unit tests (test_mm.py, test_mm_agg.py) + gates G1-G4 (NSHARD shards, default 8) -> out/unit, out/gate/gates.json
#   MODE=smoke  6 smoke keys (frames 8300..8302 x U/G, 7 dB; SMOKE ONLY, never analysed) -> out/smoke + smoke_counts.json
#   MODE=chain  unattended: run (300 keys, NSHARD default 8, cost stop) -> agg -> gzip/md5 -> "MM CHAIN DONE|STOPPED <utc>" in out/main/STATUS.txt
# Limits: at most 8 concurrent processes (NSHARD > 8 aborts), >= 16 cores kept free, cost stop at COST_CAP_H core-hours (default 3) on the committed cost of all shards.
# Environment knobs of the chain (defaults = the frozen design): NSHARD=8  REPS=3  AUX_REPS=REPS (S-hard/S-genie draws; cost option)  COST_CAP_H=3
set -u
MODE=${MODE:-gate}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_mm_gamma_20261018
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
E3_ROWS=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_e3_sbl_20261017/out/main
NSHARD=${NSHARD:-8}
REPS=${REPS:-3}
AUX_REPS=${AUX_REPS:-$REPS}
COST_CAP_H=${COST_CAP_H:-3}
case "$MODE" in
  gate) need=$NSHARD ;;
  smoke) NSHARD=6; need=6 ;;
  chain) need=$NSHARD ;;
  *) echo "unknown MODE $MODE" >&2; exit 2 ;;
esac
if [ "$NSHARD" -gt 8 ]; then echo "abort: NSHARD=$NSHARD exceeds the cap of 8 processes" >&2; exit 4; fi
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$need" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
  echo "abort: load $(cat /proc/loadavg) + $need processes would leave < 16 cores free" >&2; exit 1
fi
utc() { date -u +%FT%TZ; }
case "$MODE" in
  gate)
    mkdir -p out/unit out/gate
    python test_mm.py --out out/unit > out/unit/test_mm.log 2>&1 || echo "test_mm FAILED" >> out/gate/STATUS.txt
    python test_mm_agg.py --out out/unit > out/unit/test_mm_agg.log 2>&1 || echo "test_mm_agg FAILED" >> out/gate/STATUS.txt
    pids=()
    for s in $(seq 0 $((NSHARD - 1))); do
      python mm_driver.py --mode gate --out out/gate --shard $s --nshard $NSHARD > out/gate/gate_shard$(printf %03d $s).log 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do wait "$p" || echo "gate shard pid $p exit nonzero" >> out/gate/STATUS.txt; done
    python mm_driver.py --mode gate-merge --out out/gate --unit-dir out/unit > out/gate/merge.log 2>&1
    echo "gate done $(utc) load: $(cat /proc/loadavg)" >> out/gate/STATUS.txt ;;
  smoke)
    mkdir -p out/smoke
    pids=()
    for s in $(seq 0 5); do
      python mm_driver.py --mode run --smoke --out out/smoke --shard $s --nshard 6 > out/smoke/shard$(printf %03d $s).log 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do wait "$p" || echo "smoke shard pid $p exit nonzero" >> out/smoke/STATUS.txt; done
    python mm_agg.py --smoke-counts --rows out/smoke --out out/smoke > out/smoke/smoke_counts.log 2>&1
    (cd out/smoke && md5sum rows_shard*.jsonl config_shard*.json > REMOTE_MD5.txt)
    echo "smoke done $(utc) load: $(cat /proc/loadavg)" >> out/smoke/STATUS.txt ;;
  chain)
    python - <<'EOF' || { echo "abort: out/gate/gates.json missing or not all_pass" >&2; exit 3; }
import json, sys
sys.exit(0 if json.load(open('out/gate/gates.json')).get('all_pass') is True else 1)
EOF
    mkdir -p out/main out/analysis
    if grep -q "MM CHAIN" out/main/STATUS.txt 2>/dev/null; then echo "abort: out/main/STATUS.txt already holds a finished chain (move out/main away to rerun)" >&2; exit 5; fi
    rm -f out/main/COST_STOP
    CAP_S=$(awk -v h="$COST_CAP_H" 'BEGIN{printf "%d", h * 3600}')
    echo "start NSHARD=$NSHARD REPS=$REPS AUX_REPS=$AUX_REPS cost_cap_s=$CAP_S gates_md5=$(md5sum out/gate/gates.json | cut -d' ' -f1) $(utc) load: $(cat /proc/loadavg)" >> out/main/STATUS.txt
    pids=(); bad=0
    for s in $(seq 0 $((NSHARD - 1))); do
      python mm_driver.py --mode run --out out/main --shard $s --nshard $NSHARD --reps $REPS --aux-reps $AUX_REPS --cost-cap-seconds $CAP_S >> out/main/shard$(printf %03d $s).log 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do wait "$p" || bad=$((bad + 1)); done
    echo "shards done $(utc) nonzero_exits=$bad" >> out/main/STATUS.txt
    python mm_agg.py --rows out/main --gates out/gate/gates.json --e3-rows "$E3_ROWS" --reps $REPS --aux-reps $AUX_REPS --out out/analysis > out/analysis/agg.log 2>&1
    agg_rc=$?
    echo "agg exit $agg_rc $(utc)" >> out/main/STATUS.txt
    (cd out/main && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt)
    (cd out/analysis && md5sum mm_summary.json mm_summary.md > SUMMARY_MD5.txt 2>/dev/null)
    n_rows=$(zcat out/main/rows_shard*.jsonl.gz | wc -l)
    interp=$(python -c "import json; print(json.load(open('out/analysis/mm_summary.json'))['interpretable'])" 2>/dev/null || echo unknown)
    echo "rows=$n_rows interpretable=$interp verdict=$(python -c "import json; print(json.load(open('out/analysis/mm_summary.json'))['final_verdict'])" 2>/dev/null || echo unknown)" >> out/main/STATUS.txt
    if [ -f out/main/COST_STOP ]; then
      echo "MM CHAIN STOPPED $(utc) (cost cap ${COST_CAP_H} core-h reached; $n_rows of 300 rows; $(cat out/main/COST_STOP | head -1))" >> out/main/STATUS.txt
    elif [ "$bad" -ne 0 ] || [ "$agg_rc" -ne 0 ] || [ "$n_rows" -ne 300 ] || [ "$interp" != "True" ]; then
      echo "MM CHAIN STOPPED $(utc) (nonzero_exits=$bad agg_rc=$agg_rc rows=$n_rows of 300 interpretable=$interp)" >> out/main/STATUS.txt
    else
      echo "MM CHAIN DONE $(utc) (300 rows, agg exit 0)" >> out/main/STATUS.txt
    fi ;;
esac
