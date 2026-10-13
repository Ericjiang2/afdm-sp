#!/usr/bin/env bash
set -u

readonly SOURCE_ROOT="${1:?usage: run_development_report.sh FINAL_SOURCE_ROOT}"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/cost_screen_20260921"
readonly RUN="$EVIDENCE/cost_screen_run"
readonly OUT="$EVIDENCE/analysis_v1"
readonly LOG="$EVIDENCE/analysis_command"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
readonly TIMEOUT_SECONDS=1800

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

mkdir -p "$LOG" "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME"
test -f "$RUN/manifest.json" || exit 95
test ! -e "$OUT" || exit 91
printf '%q ' "$PYTHON" -B "$EVIDENCE/development_report.py" --source "$SOURCE_ROOT" \
  --run "$RUN" --out "$OUT" > "$LOG/argv.txt"
printf '\n' >> "$LOG/argv.txt"
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
} > "$LOG/environment.txt"
start_epoch="$(date +%s)"
deadline_epoch="$((start_epoch + TIMEOUT_SECONDS))"
printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\ntimeout_seconds=%s\nlauncher_pid=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" "$TIMEOUT_SECONDS" "$$" \
  > "$LOG/lifecycle.txt"
timeout --signal=TERM --kill-after=60s "${TIMEOUT_SECONDS}s" \
  /usr/bin/time -v -o "$LOG/time.txt" \
  "$PYTHON" -B "$EVIDENCE/development_report.py" --source "$SOURCE_ROOT" \
  --run "$RUN" --out "$OUT" > "$LOG/stdout.log" 2> "$LOG/stderr.log" &
child_pid=$!
printf 'child_pid=%s\n' "$child_pid" >> "$LOG/lifecycle.txt"
wait "$child_pid"
rc=$?
end_epoch="$(date +%s)"
printf '%s\n' "$rc" > "$LOG/exit_code.txt"
printf 'end_utc=%s\nend_epoch=%s\nelapsed_wall_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$end_epoch" "$((end_epoch - start_epoch))" \
  >> "$LOG/lifecycle.txt"
exit "$rc"
