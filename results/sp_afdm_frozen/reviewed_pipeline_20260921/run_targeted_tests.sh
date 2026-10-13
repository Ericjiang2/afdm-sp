#!/usr/bin/env bash
set -u

readonly ROOT="/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/reviewed_pipeline_20260921"
readonly PYTHON="/home/guoyikun/.conda/envs/AFDM/bin/python"

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

mkdir -p "$TMPDIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$XDG_CACHE_HOME" "$EVIDENCE/targeted_tests"
cd "$ROOT" || exit 90

tests=(
  test_evidence_contract.py
  test_protocol.py
  test_fallback.py
  test_decoder_observer.py
  test_fresh_decoder_accounting.py
)
for test_name in "${tests[@]}"; do
  command_dir="$EVIDENCE/targeted_tests/${test_name%.py}"
  mkdir -p "$command_dir"
  printf '%q ' "$PYTHON" -B "tests/$test_name" > "$command_dir/argv.txt"
  printf '\n' >> "$command_dir/argv.txt"
  /usr/bin/time -v -o "$command_dir/time.txt" \
    timeout --signal=TERM --kill-after=30s 600s "$PYTHON" -B "tests/$test_name" \
    > "$command_dir/stdout.log" 2> "$command_dir/stderr.log"
  rc=$?
  printf '%s\n' "$rc" > "$command_dir/exit_code.txt"
  if [ "$rc" -ne 0 ]; then
    exit "$rc"
  fi
done
