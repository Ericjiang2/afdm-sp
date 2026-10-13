#!/usr/bin/env bash
set -u

readonly ROOT="/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/reviewed_pipeline_20260921"
readonly OUT="$EVIDENCE/driver_smoke_v1"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
readonly TIMEOUT_SECONDS=2400

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

mkdir -p "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME" \
  "$EVIDENCE/driver_smoke_command_v1"
test ! -e "$OUT" || exit 91
cd "$ROOT" || exit 90
command_dir="$EVIDENCE/driver_smoke_command_v1"
printf '%q ' "$PYTHON" -B src/run_local.py --phase development --frames 1 --arms \
  P_M24_I20 I1_BP12_r0 N_ep_2_r1 ABL_fresh_APP --cell 2 --out "$OUT" \
  > "$command_dir/argv.txt"
printf '\n' >> "$command_dir/argv.txt"
start_epoch="$(date +%s)"
deadline_epoch="$((start_epoch + TIMEOUT_SECONDS))"
printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\ntimeout_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" "$TIMEOUT_SECONDS" \
  > "$command_dir/lifecycle.txt"
timeout --signal=TERM --kill-after=60s "${TIMEOUT_SECONDS}s" \
  /usr/bin/time -v -o "$command_dir/time.txt" \
  "$PYTHON" -B src/run_local.py --phase development --frames 1 \
  --arms P_M24_I20 I1_BP12_r0 N_ep_2_r1 ABL_fresh_APP --cell 2 --out "$OUT" \
  > "$command_dir/stdout.log" 2> "$command_dir/stderr.log"
rc=$?
end_epoch="$(date +%s)"
printf '%s\n' "$rc" > "$command_dir/exit_code.txt"
printf 'end_utc=%s\nend_epoch=%s\nelapsed_wall_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$end_epoch" "$((end_epoch - start_epoch))" \
  >> "$command_dir/lifecycle.txt"
exit "$rc"
