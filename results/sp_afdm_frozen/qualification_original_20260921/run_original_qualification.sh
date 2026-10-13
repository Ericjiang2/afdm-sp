#!/usr/bin/env bash
set -u

readonly WORKTREE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/qualification_original_20260921/worktree"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/qualification_original_20260921"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"
readonly TIMEOUT_SECONDS=7200

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

mkdir -p "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME" "$EVIDENCE/commands"
cd "$WORKTREE" || exit 90

{
  printf 'qualification_started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'hostname=%s\n' "$(hostname)"
  printf 'worktree=%s\n' "$WORKTREE"
  printf 'python=%s\n' "$PYTHON"
  printf 'timeout_seconds=%s\n' "$TIMEOUT_SECONDS"
  env | LC_ALL=C sort | grep -E '^(CUDA_VISIBLE_DEVICES|OPENBLAS_NUM_THREADS|OMP_NUM_THREADS|MKL_NUM_THREADS|NUMEXPR_NUM_THREADS|PYTHONDONTWRITEBYTECODE|TMPDIR|MPLCONFIGDIR|TORCH_HOME|XDG_CACHE_HOME)='
  uname -a
  lscpu
} > "$EVIDENCE/environment.txt"

"$PYTHON" -B - <<'PY' > "$EVIDENCE/python_environment.stdout.log" 2> "$EVIDENCE/python_environment.stderr.log"
import json
import os
import platform
import sys

import matplotlib
import numpy
import scipy
import torch

initial_num_threads = torch.get_num_threads()
initial_num_interop_threads = torch.get_num_interop_threads()
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
payload = {
    "python": sys.version,
    "platform": platform.platform(),
    "numpy": numpy.__version__,
    "scipy": scipy.__version__,
    "torch": torch.__version__,
    "matplotlib": matplotlib.__version__,
    "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    "torch_cuda_available": torch.cuda.is_available(),
    "test_process_thread_contract": "separate Python processes use the exported BLAS/OpenMP limits; this probe's explicit Torch settings are process-local",
    "torch_initial_num_threads_from_environment": initial_num_threads,
    "torch_initial_num_interop_threads": initial_num_interop_threads,
    "torch_probe_num_threads_after_explicit_set": torch.get_num_threads(),
    "torch_probe_num_interop_threads_after_explicit_set": torch.get_num_interop_threads(),
}
print(json.dumps(payload, indent=2, sort_keys=True))
if payload["torch_cuda_available"]:
    raise SystemExit("CUDA must be unavailable for qualification")
if payload["torch_probe_num_threads_after_explicit_set"] != 1 or payload["torch_probe_num_interop_threads_after_explicit_set"] != 1:
    raise SystemExit("PyTorch effective thread counts must both equal one")
PY
environment_rc=$?
printf '%s\n' "$environment_rc" > "$EVIDENCE/python_environment.exit_code.txt"
if [ "$environment_rc" -ne 0 ]; then
  printf 'environment_failed exit_code=%s\n' "$environment_rc" > "$EVIDENCE/qualification_status.txt"
  exit "$environment_rc"
fi

run_one() {
  local ordinal="$1"
  local script="$2"
  local label
  local command_dir
  local start_epoch
  local deadline_epoch
  local child_pid
  local rc
  local end_epoch

  label="$(printf '%02d_%s' "$ordinal" "$(basename "$script" .py)")"
  command_dir="$EVIDENCE/commands/$label"
  mkdir -p "$command_dir"
  printf '%q %q %q\n' "$PYTHON" -B "$script" > "$command_dir/argv.txt"
  start_epoch="$(date +%s)"
  deadline_epoch="$((start_epoch + TIMEOUT_SECONDS))"
  printf 'start_utc=%s\nstart_epoch=%s\ndeadline_epoch=%s\ntimeout_seconds=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$start_epoch" "$deadline_epoch" "$TIMEOUT_SECONDS" \
    > "$command_dir/lifecycle.txt"

  timeout --signal=TERM --kill-after=60s "${TIMEOUT_SECONDS}s" \
    /usr/bin/time -v -o "$command_dir/time.txt" \
    "$PYTHON" -B "$script" \
    > "$command_dir/stdout.log" 2> "$command_dir/stderr.log" &
  child_pid=$!
  printf 'launcher_pid=%s\n' "$child_pid" >> "$command_dir/lifecycle.txt"
  wait "$child_pid"
  rc=$?
  end_epoch="$(date +%s)"
  printf '%s\n' "$rc" > "$command_dir/exit_code.txt"
  printf 'end_utc=%s\nend_epoch=%s\nelapsed_wall_seconds=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$end_epoch" "$((end_epoch - start_epoch))" \
    >> "$command_dir/lifecycle.txt"

  if [ "$rc" -ne 0 ]; then
    printf 'failed_command=%s\nexit_code=%s\n' "$label" "$rc" > "$EVIDENCE/qualification_status.txt"
    return "$rc"
  fi
  return 0
}

tests=(
  tests/test_core.py
  tests/test_baselines.py
  tests/test_bilinear.py
  tests/test_cache.py
  tests/test_fallback.py
  tests/test_integration.py
  tests/test_native.py
  tests/benchmark_kernels.py
)

ordinal=1
for test_script in "${tests[@]}"; do
  run_one "$ordinal" "$test_script" || exit $?
  ordinal=$((ordinal + 1))
done

printf 'passed=8\nqualification_finished_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$EVIDENCE/qualification_status.txt"
