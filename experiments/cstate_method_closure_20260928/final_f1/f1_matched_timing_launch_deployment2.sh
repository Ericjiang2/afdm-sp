#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 || ! "$1" =~ ^[0-9a-f]{40}$ || ! "$2" =~ ^[0-9a-f]{64}$ || ! "$3" =~ ^[0-9]+$ ]]; then
  echo 'usage: f1_matched_timing_launch.sh <registration-commit-full40> <registration-sha256> <available-cpu-id>' >&2
  exit 2
fi
registration_commit="$1"
registration_sha256="$2"
cpu_id="$3"
project=/data/guoyikun/00inbox/AFDM-channel-estimation
cd "$project"
run_root="$project/results/cstate_method_closure_20260928/final_f1"
out="$run_root/observed_matched64_v1"
launch_root="$run_root/launch_matched64_deployment2"
if [[ -e "$out" || -e "$launch_root" ]]; then
  echo 'matched timing output or launch root already exists; no implicit retry' >&2
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
printf '{"registration_commit":"%s","registration_sha256":"%s","cpu_id":%s,"started_utc":"%s","hard_timeout_seconds":900}\n' \
  "$registration_commit" "$registration_sha256" "$cpu_id" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  > "$launch_root/launch_started.json"

set +e
taskset -c "$cpu_id" timeout --signal=INT --kill-after=5s 895s \
  /home/guoyikun/.conda/envs/AFDM/bin/python \
  experiments/cstate_method_closure_20260928/final_f1/f1_matched_timing.py \
  --registration results/cstate_method_closure_20260928/final_f1/F1_MATCHED64_TIMING_REGISTRATION.json \
  --protocol results/cstate_method_closure_20260928/final_f1/F1_MATCHED64_TIMING_PROTOCOL.md \
  --registration-commit "$registration_commit" --registration-sha256 "$registration_sha256" \
  --compat-registration results/cstate_necessity_stageB_resume_20260928/F1_COMPAT_MANIFEST.json \
  --compat-protocol results/cstate_necessity_stageB_resume_20260928/F1_COMPAT_PROTOCOL.md \
  --compat-observed results/cstate_necessity_stageB_resume_20260928/observed_f1_compat_v1 \
  --compat-equivalence-receipt results/cstate_necessity_stageB_resume_20260928/F1_FAST_EQUIVALENCE_RECEIPT.json \
  --independent-rehash-receipt results/cstate_method_closure_20260928/final_f1/independent/F1_CCOMPAT_RAW_EQUIVALENCE_RECOUNT.json \
  --stage-a-registration results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json \
  --stage-a-observed results/cstate_necessity_stageA_20260928/observed \
  --population-observed results/tf_cstate_prospective_20260923/population_observed \
  --source experiments/sp_afdm_native_joint_reviewed_20260921 \
  --baseline experiments/sp_afdm_frozen_reviewed_20260921 \
  --out "$out" > "$launch_root/runner.log" 2>&1
exit_code=$?
set -e
printf '{"exit_code":%s,"ended_utc":"%s","observed_seal_present":%s}\n' \
  "$exit_code" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  "$(if [[ -f "$out/observed_seal.json" ]]; then echo true; else echo false; fi)" \
  > "$launch_root/launch_exit.json"
exit "$exit_code"
