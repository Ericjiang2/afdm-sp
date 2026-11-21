#!/bin/bash
# GSO launcher (task 10-18-gamma-support-only).  Run inside a tmux session named g_gso on deinlab; CPU only, single-thread processes.
#   MODE=gate   unit tests (test_gso.py, test_gso_agg.py) -> gate shards G1-G3 (10 processes) -> smoke (8 keys, frames >= 8500, counts only) -> merge G1-G4
#               -> out/unit, out/gate/gates.json, out/smoke/smoke_counts.json
#   MODE=chain  unattended: verify CODE_MD5 + gates -> run (1200 keys, NSHARD default 16, cost stop) -> agg -> gzip/md5 -> "GSO CHAIN DONE|STOPPED <utc>" in out/main/STATUS.txt
# Limits: at most 16 concurrent processes (NSHARD > 16 aborts), >= 16 cores kept free (load check before start), cost stop at COST_CAP_H core-hours (default 6)
# on the committed cost of all shards.  Environment knobs of the chain: NSHARD=16  COST_CAP_H=6.  Outputs are never overwritten or resumed.
set -u
MODE=${MODE:-gate}
GSO_DIR=${GSO_DIR:-/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_gso_20261018}   # GSO_DIR is only overridden by the sandbox launcher test
cd "$GSO_DIR" || exit 9
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
NSHARD=${NSHARD:-16}
COST_CAP_H=${COST_CAP_H:-6}
NGATE=10
NSMOKE=8
case "$MODE" in
  gate) need=$NGATE ;;
  chain) need=$NSHARD ;;
  *) echo "unknown MODE $MODE" >&2; exit 2 ;;
esac
if [ "$NSHARD" -gt 16 ] || [ "$need" -gt 16 ]; then echo "abort: more than 16 processes requested" >&2; exit 4; fi
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$need" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
  echo "abort: load $(cat /proc/loadavg) + $need processes would leave < 16 cores free" >&2; exit 1
fi
utc() { date -u +%FT%TZ; }
case "$MODE" in
  gate)
    if [ -e out/gate ] || [ -e out/unit ] || [ -e out/smoke ]; then echo "abort: out/gate, out/unit or out/smoke exists (move it away; outputs are never overwritten)" >&2; exit 5; fi
    mkdir -p out/unit out/gate out/smoke
    echo "gate start $(utc) load: $(cat /proc/loadavg)" >> out/gate/STATUS.txt
    python test_gso.py --out out/unit > out/unit/test_gso.log 2>&1 || echo "test_gso FAILED" >> out/gate/STATUS.txt
    python test_gso_agg.py --out out/unit > out/unit/test_gso_agg.log 2>&1 || echo "test_gso_agg FAILED" >> out/gate/STATUS.txt
    pids=()
    for s in $(seq 0 $((NGATE - 1))); do
      python gso_driver.py --mode gate --out out/gate --shard $s --nshard $NGATE > out/gate/gate_shard$(printf %03d $s).log 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do wait "$p" || echo "gate shard pid $p exit nonzero" >> out/gate/STATUS.txt; done
    pids=()
    for s in $(seq 0 $((NSMOKE - 1))); do
      python gso_driver.py --mode run --smoke --out out/smoke --shard $s --nshard $NSMOKE > out/smoke/shard$(printf %03d $s).log 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do wait "$p" || echo "smoke shard pid $p exit nonzero" >> out/smoke/STATUS.txt; done
    python gso_agg.py --smoke-counts --rows out/smoke --out out/smoke > out/smoke/smoke_counts.log 2>&1 || echo "smoke counts FAILED" >> out/gate/STATUS.txt
    python gso_driver.py --mode gate-merge --out out/gate --smoke-dir out/smoke --unit-dir out/unit > out/gate/merge.log 2>&1
    (cd out/gate && md5sum gates.json > GATES_MD5.txt)
    (cd out/smoke && md5sum rows_shard*.jsonl config_shard*.json smoke_counts.json > REMOTE_MD5.txt)
    echo "gate done $(utc) load: $(cat /proc/loadavg)" >> out/gate/STATUS.txt ;;
  chain)
    if ! md5sum -c --quiet CODE_MD5.txt; then echo "abort: CODE_MD5.txt does not match the files on disk" >&2; exit 6; fi
    python - <<'EOF' || { echo "abort: out/gate/gates.json missing or not all_pass" >&2; exit 3; }
import json, sys
sys.exit(0 if json.load(open('out/gate/gates.json')).get('all_pass') is True else 1)
EOF
    mkdir -p out/main out/analysis
    if grep -q "GSO CHAIN" out/main/STATUS.txt 2>/dev/null; then echo "abort: out/main/STATUS.txt already holds a finished chain (move out/main away to rerun)" >&2; exit 5; fi
    if ls out/main/rows_shard* > /dev/null 2>&1; then echo "abort: out/main already holds row files (outputs are never overwritten or resumed)" >&2; exit 5; fi
    rm -f out/main/COST_STOP
    CAP_S=$(awk -v h="$COST_CAP_H" 'BEGIN{printf "%d", h * 3600}')
    echo "start NSHARD=$NSHARD cost_cap_s=$CAP_S gates_md5=$(md5sum out/gate/gates.json | cut -d' ' -f1) code_md5=$(md5sum CODE_MD5.txt | cut -d' ' -f1) $(utc) load: $(cat /proc/loadavg)" >> out/main/STATUS.txt
    pids=(); bad=0
    for s in $(seq 0 $((NSHARD - 1))); do
      python gso_driver.py --mode run --out out/main --shard $s --nshard $NSHARD --cost-cap-seconds $CAP_S >> out/main/shard$(printf %03d $s).log 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do wait "$p" || bad=$((bad + 1)); done
    echo "shards done $(utc) nonzero_exits=$bad" >> out/main/STATUS.txt
    python gso_agg.py --rows out/main --gates out/gate/gates.json --out out/analysis > out/analysis/agg.log 2>&1
    agg_rc=$?
    echo "agg exit $agg_rc $(utc)" >> out/main/STATUS.txt
    (cd out/main && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json completed_shard*.json > REMOTE_ROWS_MD5.txt)
    (cd out/analysis && md5sum gso_summary.json gso_summary.md > SUMMARY_MD5.txt 2>/dev/null)
    n_rows=$(zcat out/main/rows_shard*.jsonl.gz | wc -l)
    interp=$(python -c "import json; print(json.load(open('out/analysis/gso_summary.json'))['interpretable'])" 2>/dev/null || echo unknown)
    label=$(python -c "import json; print((json.load(open('out/analysis/gso_summary.json')).get('verdict') or {}).get('label'))" 2>/dev/null || echo unknown)
    echo "rows=$n_rows interpretable=$interp verdict=$label" >> out/main/STATUS.txt
    if [ -f out/main/COST_STOP ]; then
      echo "GSO CHAIN STOPPED $(utc) (cost cap ${COST_CAP_H} core-h reached; $n_rows of 1200 rows; $(head -1 out/main/COST_STOP))" >> out/main/STATUS.txt
    elif [ "$bad" -ne 0 ] || [ "$agg_rc" -ne 0 ] || [ "$n_rows" -ne 1200 ] || [ "$interp" != "True" ]; then
      echo "GSO CHAIN STOPPED $(utc) (nonzero_exits=$bad agg_rc=$agg_rc rows=$n_rows of 1200 interpretable=$interp)" >> out/main/STATUS.txt
    else
      echo "GSO CHAIN DONE $(utc) (1200 rows, agg exit 0, verdict $label)" >> out/main/STATUS.txt
    fi ;;
esac
