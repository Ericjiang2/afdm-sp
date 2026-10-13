#!/usr/bin/env bash
set -u

readonly SOURCE_ROOT="${1:?usage: run_cost_screen.sh FINAL_SOURCE_ROOT}"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/cost_screen_20260921"
readonly OUT="$EVIDENCE/cost_screen_run"
readonly LOG="$EVIDENCE/cost_screen_command"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
readonly TIMEOUT_SECONDS=14400
readonly SOURCE_BOUNDARY_COMMIT="31d5ec0d"

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

mkdir -p "$LOG" "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME"
test -f "$SOURCE_ROOT/src/run_local.py" || exit 90
test ! -e "$OUT" || exit 91

catalog_count="$($PYTHON -B -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' \
  "$SOURCE_ROOT/protocol/configurations.json")"
test "$catalog_count" = 59 || exit 93

cd "$SOURCE_ROOT" || exit 90
printf '%q ' "$PYTHON" -B src/run_local.py --phase development --frames 1 --cell 2 --out "$OUT" \
  > "$LOG/argv.txt"
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
printf '%s\n' "$SOURCE_ROOT" > "$LOG/source_root.txt"
printf '%s\n' "$SOURCE_BOUNDARY_COMMIT" > "$LOG/source_boundary_commit.txt"
start_epoch="$(date +%s)"
deadline_epoch="$((start_epoch + TIMEOUT_SECONDS))"
printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\ntimeout_seconds=%s\nlauncher_pid=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" "$TIMEOUT_SECONDS" "$$" \
  > "$LOG/lifecycle.txt"

timeout --signal=TERM --kill-after=60s "${TIMEOUT_SECONDS}s" \
  /usr/bin/time -v -o "$LOG/time.txt" \
  "$PYTHON" -B src/run_local.py --phase development --frames 1 --cell 2 --out "$OUT" \
  > "$LOG/stdout.log" 2> "$LOG/stderr.log" &
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
