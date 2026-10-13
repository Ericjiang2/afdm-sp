#!/usr/bin/env bash
set -u

readonly ROOT="/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_corrected_20260921"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/corrected_pipeline_20260921"
readonly LOG_ROOT="$EVIDENCE/regression_final"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
readonly COMMAND_TIMEOUT=600

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

mkdir -p "$LOG_ROOT" "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME"
cd "$ROOT" || exit 90

commands=(
  tests/test_decoder_observer.py
  tests/test_evidence_contract.py
  tests/test_core.py
  tests/test_baselines.py
  tests/test_bilinear.py
  tests/test_cache.py
  tests/test_fallback.py
  tests/test_integration.py
  tests/test_native.py
  tests/benchmark_kernels.py
  tests/test_protocol.py
)

printf 'start_utc=%s\nlauncher_pid=%s\ncommand_timeout_seconds=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$$" "$COMMAND_TIMEOUT" > "$LOG_ROOT/lifecycle.txt"
: > "$LOG_ROOT/summary.tsv"

index=0
for script in "${commands[@]}"; do
  index=$((index + 1))
  name="$(basename "$script" .py)"
  command_dir="$LOG_ROOT/$(printf '%02d_%s' "$index" "$name")"
  mkdir -p "$command_dir"
  printf '%q %q %q\n' "$PYTHON" -B "$script" > "$command_dir/argv.txt"
  start_epoch="$(date +%s)"
  deadline_epoch="$((start_epoch + COMMAND_TIMEOUT))"
  printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" \
    > "$command_dir/lifecycle.txt"
  timeout --signal=TERM --kill-after=30s "${COMMAND_TIMEOUT}s" \
    /usr/bin/time -v -o "$command_dir/time.txt" \
    "$PYTHON" -B "$script" > "$command_dir/stdout.log" 2> "$command_dir/stderr.log" &
  child_pid=$!
  printf 'child_pid=%s\n' "$child_pid" >> "$command_dir/lifecycle.txt"
  wait "$child_pid"
  rc=$?
  end_epoch="$(date +%s)"
  printf '%s\n' "$rc" > "$command_dir/exit_code.txt"
  printf 'end_utc=%s\nend_epoch=%s\nelapsed_wall_seconds=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$end_epoch" "$((end_epoch - start_epoch))" \
    >> "$command_dir/lifecycle.txt"
  printf '%02d\t%s\t%s\t%s\n' "$index" "$script" "$rc" "$((end_epoch - start_epoch))" \
    >> "$LOG_ROOT/summary.tsv"
  if [ "$rc" -ne 0 ]; then
    printf 'failed_script=%s\nfailed_exit=%s\n' "$script" "$rc" >> "$LOG_ROOT/lifecycle.txt"
    exit "$rc"
  fi
done

printf 'end_utc=%s\nstatus=pass\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG_ROOT/lifecycle.txt"
