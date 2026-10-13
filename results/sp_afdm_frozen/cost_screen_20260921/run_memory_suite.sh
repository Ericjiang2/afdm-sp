#!/usr/bin/env bash
set -u

readonly SOURCE_ROOT="${1:?usage: run_memory_suite.sh FINAL_SOURCE_ROOT}"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/cost_screen_20260921"
readonly SCREEN="$EVIDENCE/cost_screen_run"
readonly LOG_ROOT="$EVIDENCE/memory"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
readonly ARM_TIMEOUT_SECONDS=3600

printf '%s\n' "$SOURCE_ROOT" | grep -Eq \
  '^/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/[A-Za-z0-9._-]+$' || {
  echo "source root must be a simple-name directory in the compliant /data experiments root" >&2
  exit 92
}

export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$EVIDENCE/tmp"
export MPLCONFIGDIR="$EVIDENCE/matplotlib"
export TORCH_HOME="$EVIDENCE/cache"
export XDG_CACHE_HOME="$EVIDENCE/cache"

test "$(cat "$EVIDENCE/cost_screen_command/exit_code.txt")" = 0 || exit 94
test -f "$SCREEN/arrays/c02_f00000_input.npz" || exit 95
test -f "$SCREEN/manifest.json" || exit 95
test ! -e "$LOG_ROOT" || exit 91
mkdir -p "$LOG_ROOT" "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME"
{
  printf 'CUDA_VISIBLE_DEVICES=%s\n' "$CUDA_VISIBLE_DEVICES"
  printf 'OPENBLAS_NUM_THREADS=%s\n' "$OPENBLAS_NUM_THREADS"
  printf 'OMP_NUM_THREADS=%s\n' "$OMP_NUM_THREADS"
  printf 'MKL_NUM_THREADS=%s\n' "$MKL_NUM_THREADS"
  printf 'NUMEXPR_NUM_THREADS=%s\n' "$NUMEXPR_NUM_THREADS"
  printf 'PYTHONDONTWRITEBYTECODE=%s\n' "$PYTHONDONTWRITEBYTECODE"
  printf 'TMPDIR=%s\n' "$TMPDIR"
  printf 'MPLCONFIGDIR=%s\n' "$MPLCONFIGDIR"
  printf 'TORCH_HOME=%s\n' "$TORCH_HOME"
  printf 'XDG_CACHE_HOME=%s\n' "$XDG_CACHE_HOME"
  printf 'PYTHON=%s\n' "$PYTHON"
} > "$LOG_ROOT/environment.txt"
printf '%s\n' "$SOURCE_ROOT" > "$LOG_ROOT/source_root.txt"
printf 'start_utc=%s\nlauncher_pid=%s\narm_timeout_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$$" "$ARM_TIMEOUT_SECONDS" > "$LOG_ROOT/lifecycle.txt"
: > "$LOG_ROOT/summary.tsv"

mapfile -t arms < <("$PYTHON" -B -c \
  'import json,sys; print("\n".join(x["id"] for x in json.load(open(sys.argv[1]))["arms"]))' \
  "$EVIDENCE/memory_arms.json")
test "${#arms[@]}" = 10 || exit 96

index=0
for arm in "${arms[@]}"; do
  index=$((index + 1))
  arm_dir="$LOG_ROOT/$(printf '%02d_%s' "$index" "$arm")"
  mkdir -p "$arm_dir"
  cp "$LOG_ROOT/environment.txt" "$arm_dir/environment.txt"
  printf '%q ' "$PYTHON" -B "$EVIDENCE/run_memory_arm.py" --source "$SOURCE_ROOT" \
    --screen "$SCREEN" --arm "$arm" --out "$arm_dir/result.json" > "$arm_dir/argv.txt"
  printf '\n' >> "$arm_dir/argv.txt"
  start_epoch="$(date +%s)"
  deadline_epoch="$((start_epoch + ARM_TIMEOUT_SECONDS))"
  printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" \
    > "$arm_dir/lifecycle.txt"
  timeout --signal=TERM --kill-after=60s "${ARM_TIMEOUT_SECONDS}s" \
    /usr/bin/time -v -o "$arm_dir/time.txt" \
    "$PYTHON" -B "$EVIDENCE/run_memory_arm.py" --source "$SOURCE_ROOT" \
    --screen "$SCREEN" --arm "$arm" --out "$arm_dir/result.json" \
    > "$arm_dir/stdout.log" 2> "$arm_dir/stderr.log" &
  child_pid=$!
  printf 'child_pid=%s\n' "$child_pid" >> "$arm_dir/lifecycle.txt"
  wait "$child_pid"
  rc=$?
  end_epoch="$(date +%s)"
  printf '%s\n' "$rc" > "$arm_dir/exit_code.txt"
  printf 'end_utc=%s\nend_epoch=%s\nelapsed_wall_seconds=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$end_epoch" "$((end_epoch - start_epoch))" \
    >> "$arm_dir/lifecycle.txt"
  printf '%02d\t%s\t%s\t%s\n' "$index" "$arm" "$rc" "$((end_epoch - start_epoch))" \
    >> "$LOG_ROOT/summary.tsv"
  if [ "$rc" -ne 0 ]; then
    printf 'failed_arm=%s\nfailed_exit=%s\n' "$arm" "$rc" >> "$LOG_ROOT/lifecycle.txt"
    exit "$rc"
  fi
done

printf 'end_utc=%s\nstatus=pass\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG_ROOT/lifecycle.txt"
