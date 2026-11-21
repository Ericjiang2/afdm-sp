#!/bin/bash
# E-3b launcher (modelled on tf_e3_sbl_20261017/launch_e3.sh).  Run inside tmux g_e3b* on deinlab; CPU only, single-thread shards, at most 24 concurrent
# processes, keeps >= 16 cores free (load check).  Never reads stdin.
#   MODE=gate    unit tests + G1 (20 keys vs the E-3 rows, 20 shards) + G2 / G3 on real keys + merge                    -> out/unit, out/gate
#   MODE=smoke   16 smoke keys on frames >= 8300 (16 shards, on-grid check on), counts + timing, merge with G4           -> out/smoke, out/gate/gates.json
#   MODE=chain   unattended: gates.json all_pass check -> run (23 shards, + the transient cost check = at most 24 processes) with a cost stop (projection at ~10% / 50% of the rows, limit 30 core-h)
#                -> agg -> gzip + md5 manifests; ends with "E3B CHAIN DONE <utc>" or "E3B CHAIN STOPPED <reason>" in out/main/STATUS.txt
#   MODE=agg     e3b_agg.py only (re-run of the analysis)
# Start the chain:   mkdir -p out/main; tmux new-session -d -s g_e3b 'MODE=chain bash launch_e3b.sh >> out/main/launch_chain.log 2>&1'
# A stopped chain (cost stop / failed shard) keeps its rows; rerunning the same command resumes (finished keys are skipped).
set -u
MODE=${MODE:-chain}
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_e3b_offgrid_20261017
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source /opt/anaconda3/etc/profile.d/conda.sh; conda activate AFDM
E3ROWS=../tf_e3_sbl_20261017/out/main
LIMIT=30
TOTAL=2400
case "$MODE" in
  gate) NSHARD=${NSHARD:-20} ;;
  smoke) NSHARD=${NSHARD:-16} ;;
  chain) NSHARD=${NSHARD:-23} ;;   # 23 shards + the transient cost-check process = at most 24 concurrent processes
  agg) NSHARD=1 ;;
  *) echo "unknown MODE $MODE" >&2; exit 2 ;;
esac
if [ "$NSHARD" -gt 24 ]; then echo "abort: NSHARD=$NSHARD exceeds the cap of 24 concurrent processes" >&2; exit 4; fi
if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v n="$NSHARD" -v c="$(nproc --all)" 'BEGIN{exit !(l + n > c - 16)}'; then
  echo "abort: load $(cat /proc/loadavg) + $NSHARD processes would leave < 16 cores free" >&2; exit 1
fi
shard_name() { printf %03d "$1"; }

case "$MODE" in
  gate)
    mkdir -p out/gate out/unit
    python test_e3b.py --out out/unit > out/unit/test_e3b.log 2>&1 </dev/null; echo "test_e3b exit $?" >> out/unit/exit_codes.txt
    python test_e3b_agg.py > out/unit/test_e3b_agg.log 2>&1 </dev/null; echo "test_e3b_agg exit $?" >> out/unit/exit_codes.txt
    python e3b_driver.py --mode gate-prep --out out/gate --e3-rows $E3ROWS > out/gate/prep.log 2>&1 </dev/null || { echo "abort: gate-prep failed" >&2; exit 5; }
    for s in $(seq 0 $((NSHARD - 1))); do
      python e3b_driver.py --mode gate --out out/gate --shard $s --nshard $NSHARD > out/gate/gate_shard$(shard_name $s).log 2>&1 </dev/null &
    done
    wait
    python e3b_driver.py --mode gate-merge --out out/gate --unit out/unit/test_e3b.json > out/gate/merge.log 2>&1 </dev/null
    echo "gate done $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/gate/STATUS.txt ;;
  smoke)
    mkdir -p out/smoke
    for s in $(seq 0 $((NSHARD - 1))); do
      python e3b_driver.py --mode run --smoke --out out/smoke --shard $s --nshard $NSHARD > out/smoke/shard$(shard_name $s).log 2>&1 </dev/null &
    done
    wait
    python e3b_driver.py --mode smoke-counts --out out/smoke > out/smoke/counts.log 2>&1 </dev/null
    python e3b_driver.py --mode gate-merge --out out/gate --unit out/unit/test_e3b.json --smoke-dir out/smoke > out/gate/merge_with_smoke.log 2>&1 </dev/null
    (cd out/smoke && md5sum rows_shard*.jsonl config_shard*.json SMOKE_COUNTS.md > REMOTE_MD5.txt)
    echo "smoke done $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> out/smoke/STATUS.txt ;;
  chain)
    mkdir -p out/main out/analysis
    [ -f out/main/REMOTE_ROWS_MD5.txt ] && { echo "abort: out/main is already finalised (REMOTE_ROWS_MD5.txt exists; the raw rows were gzipped)" >&2; exit 6; }
    ST=out/main/STATUS.txt
    stop() { echo "E3B CHAIN STOPPED $1" >> $ST; exit 1; }
    md5sum -c CODE_MD5.txt > out/main/code_md5_check.log 2>&1 || stop "code md5 differs from CODE_MD5.txt (see out/main/code_md5_check.log)"
    [ -f out/gate/gates.json ] && python -c "import json,sys; sys.exit(0 if json.load(open('out/gate/gates.json')).get('all_pass') is True else 1)" </dev/null \
      || stop "out/gate/gates.json missing or not all_pass"
    echo "start NSHARD=$NSHARD gates_md5=$(md5sum out/gate/gates.json | cut -d' ' -f1) code_md5=$(md5sum CODE_MD5.txt | cut -d' ' -f1) $(date -u +%FT%TZ) load: $(cat /proc/loadavg)" >> $ST
    pids=()
    for s in $(seq 0 $((NSHARD - 1))); do
      python e3b_driver.py --mode run --out out/main --shard $s --nshard $NSHARD >> out/main/shard$(shard_name $s).log 2>&1 </dev/null &
      pids+=($!)
    done
    c10=0; c50=0
    while :; do
      alive=0
      for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && alive=1; done
      [ "$alive" -eq 0 ] && break
      rows=$(cat out/main/rows_shard*.jsonl 2>/dev/null | wc -l)
      if { [ "$c10" -eq 0 ] && [ "$rows" -ge $((TOTAL / 10)) ]; } || { [ "$c50" -eq 0 ] && [ "$rows" -ge $((TOTAL / 2)) ]; }; then
        [ "$rows" -ge $((TOTAL / 2)) ] && c50=1
        c10=1
        proj=$(python e3b_driver.py --mode cost-check --out out/main --total $TOTAL --limit $LIMIT </dev/null)
        rc=$?
        echo "cost check at $rows rows: $proj" >> $ST
        if [ "$rc" -ne 0 ]; then
          for p in "${pids[@]}"; do kill "$p" 2>/dev/null; done
          wait 2>/dev/null
          if [ "$rc" -eq 3 ]; then stop "cost projection above $LIMIT core-h at $rows rows: $proj"; else stop "cost check failed (exit $rc) at $rows rows"; fi
        fi
      fi
      sleep 60
    done
    bad=""
    for i in "${!pids[@]}"; do wait "${pids[$i]}"; rc=$?; [ "$rc" -ne 0 ] && bad="$bad shard$i:exit$rc"; done
    echo "shards done $(date -u +%FT%TZ)${bad:+ (failures:$bad)}" >> $ST
    [ -z "$bad" ] || stop "shard failure(s):$bad"
    python e3b_agg.py --rows out/main --e3-rows $E3ROWS --gates out/gate/gates.json --out out/analysis > out/analysis/agg.log 2>&1 </dev/null || stop "e3b_agg.py failed (see out/analysis/agg.log)"
    echo "agg done $(date -u +%FT%TZ)" >> $ST
    (cd out/main && for f in rows_shard*.jsonl; do gzip -9 -f "$f"; done; md5sum rows_shard*.jsonl.gz config_shard*.json > REMOTE_ROWS_MD5.txt) \
      && (cd out/analysis && md5sum e3b_summary.json e3b_summary.md agg.log > ANALYSIS_MD5.txt) \
      || stop "gzip / md5 manifest failed"
    echo "E3B CHAIN DONE $(date -u +%FT%TZ)" >> $ST ;;
  agg)
    mkdir -p out/analysis
    python e3b_agg.py --rows out/main --e3-rows $E3ROWS --gates out/gate/gates.json --out out/analysis > out/analysis/agg.log 2>&1 </dev/null
    echo "agg done $(date -u +%FT%TZ)" >> out/analysis/STATUS.txt ;;
esac
