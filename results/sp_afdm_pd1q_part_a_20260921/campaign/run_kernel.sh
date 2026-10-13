#!/usr/bin/env bash
set -u
readonly ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_a_20260921
readonly SOURCE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921
readonly BASE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921
readonly PYTHON=/home/guoyikun/.conda/envs/AFDM/bin/python
readonly ATTEMPT="${KERNEL_ATTEMPT:-1}"
if [[ "$ATTEMPT" == 1 ]]; then
  readonly RECEIPT="$ROOT/launch_kernel"
  readonly OUT="$ROOT/kernel"
elif [[ "$ATTEMPT" == 2 ]]; then
  readonly RECEIPT="$ROOT/launch_kernel_v2"
  readonly OUT="$ROOT/kernel_v2"
else
  exit 93
fi
if [[ -e "$RECEIPT" ]]; then exit 92; fi
mkdir -p "$RECEIPT" "$ROOT/tmp" "$ROOT/cache" "$ROOT/matplotlib"
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$ROOT/tmp" XDG_CACHE_HOME="$ROOT/cache" TORCH_HOME="$ROOT/cache" MPLCONFIGDIR="$ROOT/matplotlib"
for name in CUDA_VISIBLE_DEVICES OPENBLAS_NUM_THREADS OMP_NUM_THREADS MKL_NUM_THREADS \
    NUMEXPR_NUM_THREADS PYTHONDONTWRITEBYTECODE TMPDIR XDG_CACHE_HOME TORCH_HOME MPLCONFIGDIR; do
  printf '%s=%s\n' "$name" "${!name}"
done > "$RECEIPT/environment.txt"
args=("$PYTHON" -B "$ROOT/campaign/kernel_qualification.py" --source "$SOURCE" --baseline "$BASE" --out "$OUT")
printf '%q ' "${args[@]}" > "$RECEIPT/argv.txt"
printf '\n' >> "$RECEIPT/argv.txt"
start="$(date +%s)"
printf 'launcher_pid=%s\nstart_epoch=%s\ndeadline_epoch=%s\n' "$$" "$start" "$((start+1200))" > "$RECEIPT/lifecycle.txt"
timeout --signal=TERM --kill-after=60s 1200s /usr/bin/time -v -o "$RECEIPT/time.txt" \
  "${args[@]}" > "$RECEIPT/stdout.log" 2> "$RECEIPT/stderr.log" &
child=$!
printf 'child_pid=%s\n' "$child" >> "$RECEIPT/lifecycle.txt"
wait "$child"
rc=$?
printf '%s\n' "$rc" > "$RECEIPT/exit_code.txt"
printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$rc" >> "$RECEIPT/lifecycle.txt"
exit "$rc"
