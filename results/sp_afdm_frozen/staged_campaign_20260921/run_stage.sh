#!/usr/bin/env bash
# One timed numerical process for exactly one predeclared stage invocation.
set -u

readonly SOURCE_ROOT="${1:?reviewed source root required}"
readonly STAGE="${2:?stage 1 or 2 required}"
readonly OUT="${3:?output directory required}"
readonly LOG="${4:?unique log directory required}"
readonly GATE="${5:--}"
readonly MODE="${6:-full}"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
readonly CAMPAIGN="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/staged_campaign_20260921"

case "$STAGE" in 1) TIMEOUT_SECONDS=2400;; 2) TIMEOUT_SECONDS=3600;; *) exit 92;; esac
case "$MODE" in audit|full) ;; *) exit 92;; esac
case "$SOURCE_ROOT" in
  /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921) ;;
  *) echo 'reviewed source root required' >&2; exit 92;;
esac
case "$OUT" in "$CAMPAIGN"/*) ;; *) exit 92;; esac
case "$LOG" in "$CAMPAIGN"/*) ;; *) exit 92;; esac
test -f "$CAMPAIGN/run_stage.py" || exit 90
test -f "$SOURCE_ROOT/src/receiver.py" || exit 90
if [ "$STAGE" = 2 ]; then test -f "$GATE" || exit 91; fi
if [ "$STAGE" = 1 ] && [ "$GATE" != - ]; then exit 92; fi
test ! -e "$LOG" || exit 93

export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$CAMPAIGN/tmp" MPLCONFIGDIR="$CAMPAIGN/matplotlib"
export TORCH_HOME="$CAMPAIGN/cache" XDG_CACHE_HOME="$CAMPAIGN/cache"
mkdir -p "$LOG" "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME"

args=("$PYTHON" -B "$CAMPAIGN/run_stage.py" --source "$SOURCE_ROOT" --stage "$STAGE" --out "$OUT")
if [ "$STAGE" = 2 ]; then args+=(--gate "$GATE"); fi
if [ "$MODE" = audit ]; then args+=(--audit-only); fi
printf '%q ' "${args[@]}" > "$LOG/argv.txt"
printf '\n' >> "$LOG/argv.txt"
{
  printf 'CUDA_VISIBLE_DEVICES=%s\n' "$CUDA_VISIBLE_DEVICES"
  printf 'OPENBLAS_NUM_THREADS=%s\nOMP_NUM_THREADS=%s\nMKL_NUM_THREADS=%s\nNUMEXPR_NUM_THREADS=%s\n' \
    "$OPENBLAS_NUM_THREADS" "$OMP_NUM_THREADS" "$MKL_NUM_THREADS" "$NUMEXPR_NUM_THREADS"
  printf 'PYTHONDONTWRITEBYTECODE=%s\nTMPDIR=%s\nMPLCONFIGDIR=%s\nTORCH_HOME=%s\nXDG_CACHE_HOME=%s\n' \
    "$PYTHONDONTWRITEBYTECODE" "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME"
  printf 'PYTHON=%s\n' "$PYTHON"
} > "$LOG/environment.txt"
printf '%s\n' "$SOURCE_ROOT" > "$LOG/source_root.txt"
printf '%s\n' "$STAGE" > "$LOG/stage.txt"
start_epoch="$(date +%s)"
deadline_epoch="$((start_epoch + TIMEOUT_SECONDS))"
printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\ntimeout_seconds=%s\nlauncher_pid=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" "$TIMEOUT_SECONDS" "$$" \
  > "$LOG/lifecycle.txt"
cd "$CAMPAIGN" || exit 90
timeout --signal=TERM --kill-after=60s "${TIMEOUT_SECONDS}s" \
  /usr/bin/time -v -o "$LOG/time.txt" "${args[@]}" \
  > "$LOG/stdout.log" 2> "$LOG/stderr.log" &
child_pid=$!
printf 'child_pid=%s\n' "$child_pid" >> "$LOG/lifecycle.txt"
wait "$child_pid"
rc=$?
printf '%s\n' "$rc" > "$LOG/exit_code.txt"
end_epoch="$(date +%s)"
printf 'end_utc=%s\nend_epoch=%s\nelapsed_wall_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$end_epoch" "$((end_epoch - start_epoch))" \
  >> "$LOG/lifecycle.txt"
exit "$rc"
