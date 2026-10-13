#!/usr/bin/env bash
set -u
readonly DATA=/data/guoyikun/00inbox/AFDM-channel-estimation
readonly ROOT="$DATA/results/sp_afdm_pd1q_part_a_20260921"
readonly SOURCE="$DATA/experiments/sp_afdm_native_joint_reviewed_20260921"
readonly BASE="$DATA/experiments/sp_afdm_frozen_reviewed_20260921"
readonly E1="$DATA/results/sp_afdm_native_direction_20260921/stage_D"
readonly PYTHON=/home/guoyikun/.conda/envs/AFDM/bin/python
readonly RECEIPT="$ROOT/launch_migration"
if [[ -e "$RECEIPT" || -e "$ROOT/attribution_v2" ]]; then exit 92; fi
mkdir -p "$RECEIPT" "$ROOT/tmp" "$ROOT/cache" "$ROOT/matplotlib"
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$ROOT/tmp" XDG_CACHE_HOME="$ROOT/cache" TORCH_HOME="$ROOT/cache" MPLCONFIGDIR="$ROOT/matplotlib"
export SPAFDM_BASELINE_ROOT="$BASE"
for name in CUDA_VISIBLE_DEVICES OPENBLAS_NUM_THREADS OMP_NUM_THREADS MKL_NUM_THREADS \
    NUMEXPR_NUM_THREADS PYTHONDONTWRITEBYTECODE TMPDIR XDG_CACHE_HOME TORCH_HOME \
    MPLCONFIGDIR SPAFDM_BASELINE_ROOT; do
  printf '%s=%s\n' "$name" "${!name}"
done > "$RECEIPT/environment.txt"
args=("$PYTHON" -B "$ROOT/campaign/migrate_replay_scores.py" --source "$SOURCE" \
  --baseline "$BASE" --e1-run "$E1" --old "$ROOT/attribution" \
  --out "$ROOT/attribution_v2" --source-commit 2d130b4d)
printf '%q ' "${args[@]}" > "$RECEIPT/argv.txt"
printf '\n' >> "$RECEIPT/argv.txt"
start="$(date +%s)"
printf 'launcher_pid=%s\nstart_epoch=%s\ndeadline_epoch=%s\n' "$$" "$start" "$((start+600))" > "$RECEIPT/lifecycle.txt"
timeout --signal=TERM --kill-after=30s 600s /usr/bin/time -v -o "$RECEIPT/time.txt" \
  "${args[@]}" > "$RECEIPT/stdout.log" 2> "$RECEIPT/stderr.log" &
child=$!
printf 'child_pid=%s\n' "$child" >> "$RECEIPT/lifecycle.txt"
wait "$child"
rc=$?
printf '%s\n' "$rc" > "$RECEIPT/exit_code.txt"
printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$rc" >> "$RECEIPT/lifecycle.txt"
exit "$rc"
