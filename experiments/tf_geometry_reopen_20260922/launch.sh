#!/usr/bin/env bash
set -Eeuo pipefail
REOPEN_PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
REOPEN_CODE="$REOPEN_PROJECT/experiments/tf_geometry_reopen_20260922"
REOPEN_ROOT="$REOPEN_PROJECT/results/tf_geometry_reopen_20260922"
REOPEN_NATIVE="$REOPEN_PROJECT/experiments/sp_afdm_native_joint_reviewed_20260921"
REOPEN_BASE="$REOPEN_PROJECT/experiments/sp_afdm_frozen_reviewed_20260921"
REOPEN_RUN="$REOPEN_PROJECT/results/sp_afdm_pd1q_part_b_20260921/run"
REOPEN_A="$REOPEN_PROJECT/results/tf_production_gap_audit_20260922/A/receipt.json"
REOPEN_PY=/home/guoyikun/.conda/envs/AFDM/bin/python
REOPEN_PHASE="${1:?qualification, observed or analysis required}"
case "$REOPEN_PHASE" in
  qualification|observed|analysis) ;;
  *) exit 2 ;;
esac
REOPEN_LOG="$REOPEN_ROOT/launch_$REOPEN_PHASE"
test ! -e "$REOPEN_LOG"
mkdir -p "$REOPEN_ROOT/tmp" "$REOPEN_ROOT/cache"
mkdir "$REOPEN_LOG"
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$REOPEN_ROOT/tmp" XDG_CACHE_HOME="$REOPEN_ROOT/cache"
export MPLCONFIGDIR="$REOPEN_ROOT/cache" TORCH_HOME="$REOPEN_ROOT/cache"
export SPAFDM_BASELINE_ROOT="$REOPEN_BASE"
export PYTHONPATH="$REOPEN_NATIVE/src:$REOPEN_BASE/src:$REOPEN_CODE:$REOPEN_PROJECT/experiments/tf_production_gap_audit_20260922"
for name in CUDA_VISIBLE_DEVICES OPENBLAS_NUM_THREADS OMP_NUM_THREADS MKL_NUM_THREADS NUMEXPR_NUM_THREADS TMPDIR XDG_CACHE_HOME MPLCONFIGDIR TORCH_HOME PYTHONPATH; do
  printf '%s=%s\n' "$name" "${!name}"
done > "$REOPEN_LOG/environment.txt"
printf 'pid=%s\nstart_epoch=%s\n' "$$" "$(date +%s)" > "$REOPEN_LOG/lifecycle.txt"
finish() {
  REOPEN_EXIT="$?"
  printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$REOPEN_EXIT" >> "$REOPEN_LOG/lifecycle.txt"
  printf '%s\n' "$REOPEN_EXIT" > "$REOPEN_LOG/exit_code.txt"
}
trap finish EXIT
cd "$REOPEN_CODE"
if [[ "$REOPEN_PHASE" == qualification ]]; then
  command=("$REOPEN_PY" -B "$REOPEN_CODE/qualify_reopening.py"
    --run "$REOPEN_RUN" --source "$REOPEN_NATIVE" --baseline "$REOPEN_BASE"
    --a-receipt "$REOPEN_A" --out "$REOPEN_ROOT/qualification")
elif [[ "$REOPEN_PHASE" == observed ]]; then
  test "$(cat "$REOPEN_ROOT/launch_qualification/exit_code.txt")" = 0
  "$REOPEN_PY" -B -c 'import hashlib,json,pathlib; p=json.load(open("online_payload_sha256.json")); assert all(hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest()==h for n,h in p.items()); print("online payload hashes match",len(p))' > "$REOPEN_LOG/source_check.log" 2>&1
  command=("$REOPEN_PY" -B "$REOPEN_CODE/run_reopening.py"
    --run "$REOPEN_RUN" --source "$REOPEN_NATIVE" --baseline "$REOPEN_BASE"
    --a-receipt "$REOPEN_A" --qualification "$REOPEN_ROOT/qualification/receipt.json"
    --out "$REOPEN_ROOT/observed" --seconds 3600)
else
  test "$(cat "$REOPEN_ROOT/launch_observed/exit_code.txt")" = 0
  test -f "$REOPEN_ROOT/seal_binding.json"
  REOPEN_COMMIT=$("$REOPEN_PY" -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["git_commit"])' "$REOPEN_ROOT/seal_binding.json")
  command=("$REOPEN_PY" -B "$REOPEN_CODE/analyze_reopening.py"
    --original-run "$REOPEN_RUN" --source "$REOPEN_NATIVE" --baseline "$REOPEN_BASE"
    --a-receipt "$REOPEN_A" --qualification "$REOPEN_ROOT/qualification/receipt.json"
    --observed-root "$REOPEN_ROOT/observed" --seal-commit "$REOPEN_COMMIT"
    --seal-binding "$REOPEN_ROOT/seal_binding.json"
    --prior-b "$REOPEN_PROJECT/results/tf_production_gap_audit_20260922/B"
    --out "$REOPEN_ROOT/analysis")
fi
printf '%q ' "${command[@]}" > "$REOPEN_LOG/argv.txt"
printf '\n' >> "$REOPEN_LOG/argv.txt"
timeout --signal=TERM --kill-after=30s 3600 /usr/bin/time -v -o "$REOPEN_LOG/time.txt" \
  "${command[@]}" > "$REOPEN_LOG/stdout.log" 2> "$REOPEN_LOG/stderr.log"
