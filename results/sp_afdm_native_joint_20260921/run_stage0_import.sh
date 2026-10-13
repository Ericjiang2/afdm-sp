#!/usr/bin/env bash
# Original supplied qualification, in an isolated copy. No new radio campaign.
set -u
readonly SOURCE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_stage0_import_20260921
readonly BASE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921
readonly OUT=/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_native_joint_20260921/stage0_import
readonly PYTHON=/home/guoyikun/.conda/envs/AFDM/bin/python
readonly TIMEOUT_SECONDS=3600
test -d "$SOURCE/src" && test -d "$BASE/src" || exit 90
test ! -e "$OUT" || exit 91

export SPAFDM_BASELINE_ROOT="$BASE"
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$OUT/tmp" MPLCONFIGDIR="$OUT/matplotlib"
export XDG_CACHE_HOME="$OUT/cache" TORCH_HOME="$OUT/cache"
mkdir -p "$OUT" "$TMPDIR" "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$TORCH_HOME"
{
  for name in SPAFDM_BASELINE_ROOT CUDA_VISIBLE_DEVICES OPENBLAS_NUM_THREADS OMP_NUM_THREADS \
      MKL_NUM_THREADS NUMEXPR_NUM_THREADS PYTHONDONTWRITEBYTECODE TMPDIR MPLCONFIGDIR \
      XDG_CACHE_HOME TORCH_HOME; do printf '%s=%s\n' "$name" "${!name}"; done
  printf 'PYTHON=%s\nSOURCE=%s\n' "$PYTHON" "$SOURCE"
} > "$OUT/environment.txt"
start_epoch="$(date +%s)"
deadline_epoch="$((start_epoch + TIMEOUT_SECONDS))"
printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\ntimeout_seconds=%s\nlauncher_pid=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" "$TIMEOUT_SECONDS" "$$" \
  > "$OUT/lifecycle.txt"
cd "$SOURCE" || exit 90
for script in test_contractions.py test_twofft.py test_checkpoint_contract.py audit_outputs.py benchmark_fourfft.py; do
  name="${script%.py}"
  folder="$OUT/$name"
  mkdir "$folder"
  printf '%q ' "$PYTHON" -B "$SOURCE/tests/$script" > "$folder/argv.txt"
  printf '\n' >> "$folder/argv.txt"
  remaining="$((deadline_epoch - $(date +%s)))"
  if [ "$remaining" -le 0 ]; then printf '124\n' > "$folder/exit_code.txt"; exit 124; fi
  timeout --signal=TERM --kill-after=60s "${remaining}s" \
    /usr/bin/time -v -o "$folder/time.txt" "$PYTHON" -B "$SOURCE/tests/$script" \
    > "$folder/stdout.log" 2> "$folder/stderr.log" &
  child_pid=$!
  printf 'script=%s\nchild_pid=%s\nstarted_utc=%s\n' "$script" "$child_pid" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$OUT/lifecycle.txt"
  wait "$child_pid"
  rc=$?
  printf '%s\n' "$rc" > "$folder/exit_code.txt"
  printf 'script=%s exit=%s finished_utc=%s\n' "$script" "$rc" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$OUT/lifecycle.txt"
  if [ "$rc" -ne 0 ]; then exit "$rc"; fi
done
printf 'completed_utc=%s\nelapsed_wall_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(( $(date +%s) - start_epoch ))" \
  >> "$OUT/lifecycle.txt"
