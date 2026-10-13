#!/usr/bin/env bash
# One bounded CPU Part A attribution process. Invoke after producer freeze.
set -u
readonly SOURCE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921
readonly BASE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921
readonly ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_a_20260921
readonly E1=/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_native_direction_20260921/stage_D
readonly PYTHON=/home/guoyikun/.conda/envs/AFDM/bin/python
readonly SCRIPT="$ROOT/campaign/run.py"
readonly OUT="$ROOT/attribution_v2"
readonly MODE="${PARTA_REPLAY_ONLY:-0}"
if [[ "$MODE" != 0 && "$MODE" != 1 ]]; then exit 93; fi
if [[ "$MODE" == 1 ]]; then
  readonly RECEIPT="$ROOT/launch_replay"
else
  readonly RECEIPT="$ROOT/launch_attribution"
fi
readonly LIMIT=3600
readonly COMMIT="${SOURCE_COMMIT:?source freeze commit required}"
if [[ ! -d "$SOURCE/src" || ! -d "$BASE/src" || ! -f "$SCRIPT" || ! -f "$E1/manifest.json" ]]; then exit 91; fi
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
args=("$PYTHON" -B "$SCRIPT" --source "$SOURCE" --baseline "$BASE" --e1-run "$E1" \
  --out "$OUT" --source-commit "$COMMIT")
if [[ "$MODE" == 1 ]]; then args+=(--replay-only); fi
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
