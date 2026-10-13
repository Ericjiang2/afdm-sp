#!/usr/bin/env bash
set -Eeuo pipefail
AUDIT_PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
AUDIT_CODE="$AUDIT_PROJECT/experiments/tf_production_gap_audit_20260922"
AUDIT_ROOT="$AUDIT_PROJECT/results/tf_production_gap_audit_20260922"
AUDIT_BASE="$AUDIT_PROJECT/experiments/sp_afdm_frozen_reviewed_20260921"
AUDIT_NATIVE="$AUDIT_PROJECT/experiments/sp_afdm_native_joint_reviewed_20260921"
AUDIT_PY=/home/guoyikun/.conda/envs/AFDM/bin/python
test "$(cat "$AUDIT_ROOT/launch_B/exit_code.txt")" = 0
test ! -e "$AUDIT_ROOT/launch_C"
test ! -e "$AUDIT_ROOT/C"
mkdir "$AUDIT_ROOT/launch_C"
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$AUDIT_ROOT/tmp" XDG_CACHE_HOME="$AUDIT_ROOT/cache"
export MPLCONFIGDIR="$AUDIT_ROOT/cache" TORCH_HOME="$AUDIT_ROOT/cache"
export PYTHONPATH="$AUDIT_NATIVE/src:$AUDIT_BASE/src:$AUDIT_CODE"
printf 'pid=%s\nstart_epoch=%s\n' "$$" "$(date +%s)" > "$AUDIT_ROOT/launch_C/lifecycle.txt"
finish() {
  code="$?"
  printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$code" >> "$AUDIT_ROOT/launch_C/lifecycle.txt"
  printf '%s\n' "$code" > "$AUDIT_ROOT/launch_C/exit_code.txt"
}
trap finish EXIT
cd "$AUDIT_CODE"
"$AUDIT_PY" -B -c 'import hashlib,json,pathlib; p=json.load(open("C_payload_sha256.json")); assert all(hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest()==h for n,h in p.items()); print("C payload hashes match",len(p))' > "$AUDIT_ROOT/launch_C/source_check.log" 2>&1
printf '%s\n' "$AUDIT_PY -B $AUDIT_CODE/witness_analysis.py --run $AUDIT_PROJECT/results/sp_afdm_pd1q_part_b_20260921/run --source $AUDIT_NATIVE --baseline $AUDIT_BASE --selection $AUDIT_ROOT/A/selection.json --b-output $AUDIT_ROOT/B --out $AUDIT_ROOT/C" > "$AUDIT_ROOT/launch_C/argv.txt"
timeout --signal=TERM --kill-after=30s 3600 /usr/bin/time -v -o "$AUDIT_ROOT/launch_C/time.txt" \
  "$AUDIT_PY" -B "$AUDIT_CODE/witness_analysis.py" \
  --run "$AUDIT_PROJECT/results/sp_afdm_pd1q_part_b_20260921/run" \
  --source "$AUDIT_NATIVE" --baseline "$AUDIT_BASE" \
  --selection "$AUDIT_ROOT/A/selection.json" --b-output "$AUDIT_ROOT/B" --out "$AUDIT_ROOT/C" \
  > "$AUDIT_ROOT/launch_C/stdout.log" 2> "$AUDIT_ROOT/launch_C/stderr.log"
