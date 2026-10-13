#!/usr/bin/env bash
set -Eeuo pipefail
AUDIT_PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
AUDIT_CODE="$AUDIT_PROJECT/experiments/tf_production_gap_audit_20260922"
AUDIT_ROOT="$AUDIT_PROJECT/results/tf_production_gap_audit_20260922"
AUDIT_BASE="$AUDIT_PROJECT/experiments/sp_afdm_frozen_reviewed_20260921"
AUDIT_NATIVE="$AUDIT_PROJECT/experiments/sp_afdm_native_joint_reviewed_20260921"
AUDIT_PY=/home/guoyikun/.conda/envs/AFDM/bin/python
test ! -e "$AUDIT_ROOT/launch_B"
test ! -e "$AUDIT_ROOT/B"
mkdir "$AUDIT_ROOT/launch_B"
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$AUDIT_ROOT/tmp" XDG_CACHE_HOME="$AUDIT_ROOT/cache"
export MPLCONFIGDIR="$AUDIT_ROOT/cache" TORCH_HOME="$AUDIT_ROOT/cache"
export SPAFDM_BASELINE_ROOT="$AUDIT_BASE"
export PYTHONPATH="$AUDIT_NATIVE/src:$AUDIT_BASE/src:$AUDIT_CODE"
for name in CUDA_VISIBLE_DEVICES OPENBLAS_NUM_THREADS OMP_NUM_THREADS MKL_NUM_THREADS NUMEXPR_NUM_THREADS TMPDIR XDG_CACHE_HOME MPLCONFIGDIR TORCH_HOME PYTHONPATH; do
  printf '%s=%s\n' "$name" "${!name}"
done > "$AUDIT_ROOT/launch_B/environment.txt"
printf 'pid=%s\nstart_epoch=%s\n' "$$" "$(date +%s)" > "$AUDIT_ROOT/launch_B/lifecycle.txt"
finish() {
  code="$?"
  printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$code" >> "$AUDIT_ROOT/launch_B/lifecycle.txt"
  printf '%s\n' "$code" > "$AUDIT_ROOT/launch_B/exit_code.txt"
}
trap finish EXIT
cd "$AUDIT_CODE"
"$AUDIT_PY" -B -c 'import hashlib,json,pathlib; p=json.load(open("B_payload_sha256.json")); assert all(hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest()==h for n,h in p.items()); print("payload hashes match",len(p))' > "$AUDIT_ROOT/launch_B/source_check.log" 2>&1
"$AUDIT_PY" -B -c 'import physical,twofft,unittest,test_metrics; suite=unittest.defaultTestLoader.loadTestsFromModule(test_metrics); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(0 if result.wasSuccessful() else 1)' > "$AUDIT_ROOT/launch_B/tests.log" 2>&1
printf '%s\n' "$AUDIT_PY -B $AUDIT_CODE/run_interventions.py --run $AUDIT_PROJECT/results/sp_afdm_pd1q_part_b_20260921/run --source $AUDIT_NATIVE --baseline $AUDIT_BASE --selection $AUDIT_ROOT/A/selection.json --out $AUDIT_ROOT/B --seconds 3600" > "$AUDIT_ROOT/launch_B/argv.txt"
timeout --signal=TERM --kill-after=30s 3600 /usr/bin/time -v -o "$AUDIT_ROOT/launch_B/time.txt" \
  "$AUDIT_PY" -B "$AUDIT_CODE/run_interventions.py" \
  --run "$AUDIT_PROJECT/results/sp_afdm_pd1q_part_b_20260921/run" \
  --source "$AUDIT_NATIVE" --baseline "$AUDIT_BASE" \
  --selection "$AUDIT_ROOT/A/selection.json" --out "$AUDIT_ROOT/B" --seconds 3600 \
  > "$AUDIT_ROOT/launch_B/stdout.log" 2> "$AUDIT_ROOT/launch_B/stderr.log"
