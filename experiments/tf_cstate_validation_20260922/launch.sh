#!/usr/bin/env bash
set -Eeuo pipefail
VALIDATION_PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
VALIDATION_CODE="$VALIDATION_PROJECT/experiments/tf_cstate_validation_20260922"
VALIDATION_ROOT="$VALIDATION_PROJECT/results/tf_cstate_validation_20260922"
VALIDATION_NATIVE="$VALIDATION_PROJECT/experiments/sp_afdm_native_joint_reviewed_20260921"
VALIDATION_BASE="$VALIDATION_PROJECT/experiments/sp_afdm_frozen_reviewed_20260921"
VALIDATION_RUN="$VALIDATION_PROJECT/results/sp_afdm_pd1q_part_b_20260921/run"
VALIDATION_PRIOR="$VALIDATION_PROJECT/results/tf_geometry_reopen_20260922/observed"
VALIDATION_PRIOR_CODE="$VALIDATION_PROJECT/experiments/tf_geometry_reopen_20260922"
VALIDATION_A="$VALIDATION_PROJECT/results/tf_production_gap_audit_20260922/A/receipt.json"
VALIDATION_PY=/home/guoyikun/.conda/envs/AFDM/bin/python
VALIDATION_PHASE="${1:?qualification, local-audit, observed or analysis required}"
case "$VALIDATION_PHASE" in
  qualification|local-audit|observed|analysis) ;;
  *) exit 2 ;;
esac
VALIDATION_LOG="$VALIDATION_ROOT/launch_$VALIDATION_PHASE"
test ! -e "$VALIDATION_LOG"
mkdir -p "$VALIDATION_ROOT/tmp" "$VALIDATION_ROOT/cache"
mkdir "$VALIDATION_LOG"
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$VALIDATION_ROOT/tmp" XDG_CACHE_HOME="$VALIDATION_ROOT/cache"
export MPLCONFIGDIR="$VALIDATION_ROOT/cache" TORCH_HOME="$VALIDATION_ROOT/cache"
export SPAFDM_BASELINE_ROOT="$VALIDATION_BASE"
export PYTHONPATH="$VALIDATION_NATIVE/src:$VALIDATION_BASE/src:$VALIDATION_CODE:$VALIDATION_PRIOR_CODE:$VALIDATION_PROJECT/experiments/tf_production_gap_audit_20260922"
for name in CUDA_VISIBLE_DEVICES OPENBLAS_NUM_THREADS OMP_NUM_THREADS MKL_NUM_THREADS NUMEXPR_NUM_THREADS TMPDIR XDG_CACHE_HOME MPLCONFIGDIR TORCH_HOME PYTHONPATH; do
  printf '%s=%s\n' "$name" "${!name}"
done > "$VALIDATION_LOG/environment.txt"
printf 'pid=%s\nstart_epoch=%s\n' "$$" "$(date +%s)" > "$VALIDATION_LOG/lifecycle.txt"
finish() {
  VALIDATION_EXIT="$?"
  printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$VALIDATION_EXIT" >> "$VALIDATION_LOG/lifecycle.txt"
  printf '%s\n' "$VALIDATION_EXIT" > "$VALIDATION_LOG/exit_code.txt"
}
trap finish EXIT
cd "$VALIDATION_CODE"
if [[ "$VALIDATION_PHASE" == qualification ]]; then
  command=("$VALIDATION_PY" -B "$VALIDATION_CODE/qualify_validation.py"
    --run "$VALIDATION_RUN" --source "$VALIDATION_NATIVE" --baseline "$VALIDATION_BASE"
    --a-receipt "$VALIDATION_A" --prior-observed "$VALIDATION_PRIOR" --out "$VALIDATION_ROOT/qualification")
elif [[ "$VALIDATION_PHASE" == local-audit ]]; then
  test "$(cat "$VALIDATION_ROOT/launch_qualification/exit_code.txt")" = 0
  command=("$VALIDATION_PY" -B "$VALIDATION_CODE/audit_local_trials.py"
    --run "$VALIDATION_RUN" --source "$VALIDATION_NATIVE" --baseline "$VALIDATION_BASE"
    --a-receipt "$VALIDATION_A" --prior-observed "$VALIDATION_PRIOR"
    --qualification "$VALIDATION_ROOT/qualification/receipt.json"
    --out "$VALIDATION_ROOT/local_trial_audit")
elif [[ "$VALIDATION_PHASE" == observed ]]; then
  test "$(cat "$VALIDATION_ROOT/launch_qualification/exit_code.txt")" = 0
  test "$(cat "$VALIDATION_ROOT/launch_local-audit/exit_code.txt")" = 0
  "$VALIDATION_PY" -B -c 'import hashlib,json,pathlib; p=json.load(open("online_payload_sha256.json")); assert all(hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest()==h for n,h in p.items()); print("online payload hashes match",len(p))' > "$VALIDATION_LOG/source_check.log" 2>&1
  command=("$VALIDATION_PY" -B "$VALIDATION_CODE/run_validation.py"
    --run "$VALIDATION_RUN" --source "$VALIDATION_NATIVE" --baseline "$VALIDATION_BASE"
    --a-receipt "$VALIDATION_A" --prior-observed "$VALIDATION_PRIOR" --qualification "$VALIDATION_ROOT/qualification/receipt.json"
    --local-audit "$VALIDATION_ROOT/local_trial_audit/receipt.json"
    --out "$VALIDATION_ROOT/observed" --seconds 3600)
else
  test "$(cat "$VALIDATION_ROOT/launch_observed/exit_code.txt")" = 0
  test -f "$VALIDATION_ROOT/seal_binding.json"
  VALIDATION_COMMIT=$("$VALIDATION_PY" -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["git_commit"])' "$VALIDATION_ROOT/seal_binding.json")
  command=("$VALIDATION_PY" -B "$VALIDATION_CODE/analyze_validation.py"
    --run "$VALIDATION_RUN" --source "$VALIDATION_NATIVE" --baseline "$VALIDATION_BASE"
    --a-receipt "$VALIDATION_A" --prior-observed "$VALIDATION_PRIOR" --qualification "$VALIDATION_ROOT/qualification/receipt.json"
    --local-audit "$VALIDATION_ROOT/local_trial_audit/receipt.json"
    --observed "$VALIDATION_ROOT/observed" --seal-commit "$VALIDATION_COMMIT"
    --seal-binding "$VALIDATION_ROOT/seal_binding.json"
    --prior-b "$VALIDATION_PROJECT/results/tf_production_gap_audit_20260922/B"
    --out "$VALIDATION_ROOT/analysis")
fi
printf '%q ' "${command[@]}" > "$VALIDATION_LOG/argv.txt"
printf '\n' >> "$VALIDATION_LOG/argv.txt"
timeout --signal=TERM --kill-after=30s 3600 /usr/bin/time -v -o "$VALIDATION_LOG/time.txt" \
  "${command[@]}" > "$VALIDATION_LOG/stdout.log" 2> "$VALIDATION_LOG/stderr.log"
