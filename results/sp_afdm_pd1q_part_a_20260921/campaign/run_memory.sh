#!/usr/bin/env bash
set -u
readonly DATA=/data/guoyikun/00inbox/AFDM-channel-estimation
readonly ROOT="$DATA/results/sp_afdm_pd1q_part_a_20260921"
readonly SOURCE="$DATA/experiments/sp_afdm_native_joint_reviewed_20260921"
readonly BASE="$DATA/experiments/sp_afdm_frozen_reviewed_20260921"
readonly E1="$DATA/results/sp_afdm_native_direction_20260921/stage_D"
readonly PYTHON=/home/guoyikun/.conda/envs/AFDM/bin/python
readonly RECEIPT="$ROOT/launch_memory"
if [[ -e "$RECEIPT" ]]; then exit 92; fi
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
start="$(date +%s)"
printf 'launcher_pid=%s\nstart_epoch=%s\ndeadline_epoch=%s\n' "$$" "$start" "$((start+3600))" > "$RECEIPT/lifecycle.txt"
for arm in TF_J20_R2 EP2_MEAN_R2 EP4_MEAN_R2 PBI8_SOFT_R2; do
  args=("$PYTHON" -B "$ROOT/campaign/isolated_memory.py" --source "$SOURCE" \
    --baseline "$BASE" --e1-root "$E1" --out "$ROOT/memory/$arm" --arm "$arm")
  printf '%q ' "${args[@]}" > "$RECEIPT/${arm}_argv.txt"
  printf '\n' >> "$RECEIPT/${arm}_argv.txt"
  printf 'arm=%s\narm_start_epoch=%s\n' "$arm" "$(date +%s)" >> "$RECEIPT/lifecycle.txt"
  timeout --signal=TERM --kill-after=30s 900s /usr/bin/time -v -o "$RECEIPT/${arm}_time.txt" \
    "${args[@]}" > "$RECEIPT/${arm}_stdout.log" 2> "$RECEIPT/${arm}_stderr.log" &
  child=$!
  printf 'arm=%s\nchild_pid=%s\n' "$arm" "$child" >> "$RECEIPT/lifecycle.txt"
  wait "$child"
  rc=$?
  printf '%s\n' "$rc" > "$RECEIPT/${arm}_exit_code.txt"
  printf 'arm=%s\narm_finish_epoch=%s\narm_exit_code=%s\n' "$arm" "$(date +%s)" "$rc" >> "$RECEIPT/lifecycle.txt"
  if [[ "$rc" != 0 ]]; then
    printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$rc" >> "$RECEIPT/lifecycle.txt"
    exit "$rc"
  fi
done
printf 'finish_epoch=%s\nexit_code=0\n' "$(date +%s)" >> "$RECEIPT/lifecycle.txt"
