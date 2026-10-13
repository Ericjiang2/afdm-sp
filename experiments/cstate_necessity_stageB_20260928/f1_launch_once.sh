#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 || ! "$1" =~ ^[0-9a-f]{40}$ || ! "$2" =~ ^[0-9]+$ ]]; then
  echo 'usage: f1_launch_once.sh <registration-commit-full40> <available-cpu-id>' >&2
  exit 2
fi
registration_commit="$1"
cpu_id="$2"
project=/data/guoyikun/00inbox/AFDM-channel-estimation
cd "$project"
run_root="$project/results/cstate_necessity_stageB_20260928"
out="$run_root/observed_f1_matched_v1"
launch_root="$run_root/launch_f1_matched_v1"
if [[ -e "$out" || -e "$launch_root" ]]; then
  echo 'Stage-B observed or launch root already exists; no implicit retry' >&2
  exit 3
fi
mkdir -p "$launch_root/scratch"
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR="$launch_root/scratch"
export XDG_CACHE_HOME="$launch_root/scratch/xdg"
export MPLCONFIGDIR="$launch_root/scratch/mpl"
export TORCH_HOME="$launch_root/scratch/torch"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$MPLCONFIGDIR" "$TORCH_HOME"
printf '{"registration_commit":"%s","cpu_id":%s,"started_utc":"%s","hard_timeout_seconds":2400}\n' \
  "$registration_commit" "$cpu_id" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" > "$launch_root/launch_started.json"

set +e
taskset -c "$cpu_id" timeout --signal=INT --kill-after=5s 2395s \
  /home/guoyikun/.conda/envs/AFDM/bin/python \
  experiments/cstate_necessity_stageB_20260928/f1_run_stage_b.py \
  --registration results/cstate_necessity_stageB_20260928/STAGE_B_MANIFEST.json \
  --registration-commit "$registration_commit" \
  --protocol results/cstate_necessity_stageB_20260928/F1_EQUIVALENCE_TIMING_PROTOCOL.md \
  --stage-a-registration results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json \
  --stage-a-observed results/cstate_necessity_stageA_20260928/observed \
  --population-observed results/tf_cstate_prospective_20260923/population_observed \
  --source experiments/sp_afdm_native_joint_reviewed_20260921 \
  --baseline experiments/sp_afdm_frozen_reviewed_20260921 \
  --out "$out" --seconds-limit 2400.0 \
  > "$launch_root/runner.log" 2>&1
exit_code=$?
set -e
printf '{"exit_code":%s,"ended_utc":"%s","observed_seal_present":%s}\n' \
  "$exit_code" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  "$(if [[ -f "$out/observed_seal.json" ]]; then echo true; else echo false; fi)" \
  > "$launch_root/launch_exit.json"
exit "$exit_code"
