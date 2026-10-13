#!/usr/bin/env bash
set -u

readonly WORKTREE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/qualification_original_20260921/worktree"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/qualification_original_20260921"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
readonly COMMAND_DIR="$EVIDENCE/commands/09_verify_saved_decisions"
readonly TIMEOUT_SECONDS=600

export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$EVIDENCE/tmp"
export MPLCONFIGDIR="$EVIDENCE/matplotlib"
export TORCH_HOME="$EVIDENCE/torch"
export XDG_CACHE_HOME="$EVIDENCE/cache"

mkdir -p "$COMMAND_DIR"
cd "$WORKTREE" || exit 90
cp -p results/recount.json "$EVIDENCE/historical_recount_before_qualification.json"
printf '%q %q %q\n' "$PYTHON" -B tests/verify_saved_decisions.py > "$COMMAND_DIR/argv.txt"
start_epoch="$(date +%s)"
deadline_epoch="$((start_epoch + TIMEOUT_SECONDS))"
printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\ntimeout_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" "$TIMEOUT_SECONDS" \
  > "$COMMAND_DIR/lifecycle.txt"
timeout --signal=TERM --kill-after=60s "${TIMEOUT_SECONDS}s" \
  /usr/bin/time -v -o "$COMMAND_DIR/time.txt" \
  "$PYTHON" -B tests/verify_saved_decisions.py \
  > "$COMMAND_DIR/stdout.log" 2> "$COMMAND_DIR/stderr.log" &
child_pid=$!
printf 'launcher_pid=%s\n' "$child_pid" >> "$COMMAND_DIR/lifecycle.txt"
wait "$child_pid"
rc=$?
end_epoch="$(date +%s)"
printf '%s\n' "$rc" > "$COMMAND_DIR/exit_code.txt"
printf 'end_utc=%s\nend_epoch=%s\nelapsed_wall_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$end_epoch" "$((end_epoch - start_epoch))" \
  >> "$COMMAND_DIR/lifecycle.txt"
if [ "$rc" -eq 0 ]; then
  cp -p results/recount.json "$EVIDENCE/fresh_saved_decisions_recount.json"
fi
exit "$rc"
