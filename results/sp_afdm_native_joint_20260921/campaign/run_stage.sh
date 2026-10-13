#!/usr/bin/env bash
# One bounded CPU producer process. Invoke from g_native_* tmux after source freeze.
set -u
readonly STAGE="${1:?A or B}"
readonly SOURCE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921
readonly BASE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921
readonly ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_native_joint_20260921
readonly PYTHON=/home/guoyikun/.conda/envs/AFDM/bin/python
readonly SCRIPT="$ROOT/campaign/run.py"
readonly OUT="$ROOT/stage_${STAGE}"
readonly RECEIPT="$ROOT/launch_${STAGE}"
readonly LIMIT=1800
readonly COMMIT="${SOURCE_COMMIT:?source freeze commit required}"
if [[ "$STAGE" != A && "$STAGE" != B ]]; then exit 90; fi
if [[ ! -d "$SOURCE/src" || ! -d "$BASE/src" || ! -f "$SCRIPT" ]]; then exit 91; fi
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
args=("$PYTHON" -B "$SCRIPT" --source "$SOURCE" --baseline "$BASE" --stage "$STAGE" \
  --out "$OUT" --source-commit "$COMMIT")
if [[ "$STAGE" == B ]]; then args+=(--gate "$ROOT/stage_A_gate.json"); fi
printf '%q ' "${args[@]}" > "$RECEIPT/argv.txt"
printf '\n' >> "$RECEIPT/argv.txt"
start="$(date +%s)"
printf 'launcher_pid=%s\nstart_epoch=%s\ndeadline_epoch=%s\n' "$$" "$start" "$((start + LIMIT))" > "$RECEIPT/lifecycle.txt"
timeout --signal=TERM --kill-after=60s "${LIMIT}s" /usr/bin/time -v -o "$RECEIPT/time.txt" \
  "${args[@]}" > "$RECEIPT/stdout.log" 2> "$RECEIPT/stderr.log" &
child=$!
printf 'child_pid=%s\n' "$child" >> "$RECEIPT/lifecycle.txt"
wait "$child"
rc=$?
printf '%s\n' "$rc" > "$RECEIPT/exit_code.txt"
printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$rc" >> "$RECEIPT/lifecycle.txt"
exit "$rc"
