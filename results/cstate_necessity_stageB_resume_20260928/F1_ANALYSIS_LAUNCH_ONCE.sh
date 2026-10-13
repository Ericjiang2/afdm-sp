#!/usr/bin/env bash
set -euo pipefail

project=/data/guoyikun/00inbox/AFDM-channel-estimation
run="$project/results/cstate_necessity_stageB_resume_20260928"
out="$run/analysis_f1_compat_v1"
scratch="$run/scratch_f1_analysis"
cd "$project"

[[ ! -e "$out" ]] || { echo 'F1 analysis output already exists' >&2; exit 3; }
[[ "$(sha256sum experiments/cstate_necessity_stageB_resume_20260928/analyze_method_closure.py | cut -d' ' -f1)" == db02ac1f4ebcb41d01a5a6fea895de0c8aeca1d5aceae7baf3cb59517f6904ff ]]
[[ "$(sha256sum "$run/F1_GIT_ATTESTATION.json" | cut -d' ' -f1)" == 5892a14612ff5a953ca76cc92e5b631348dc1cd7805f70eb818de44d231dc644 ]]
mkdir -p "$scratch"
export TMPDIR="$scratch" XDG_CACHE_HOME="$scratch" MPLCONFIGDIR="$scratch" TORCH_HOME="$scratch"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
date -u +'%Y-%m-%dT%H:%M:%SZ' > "$run/F1_ANALYSIS_STARTED_UTC.txt"
set +e
taskset -c 64 timeout --signal=INT --kill-after=5s 595s \
  /home/guoyikun/.conda/envs/AFDM/bin/python \
  experiments/cstate_necessity_stageB_resume_20260928/analyze_method_closure.py \
  --campaign f1 \
  --f1-observed "$run/observed_f1_compat_v1" \
  --f1-registration "$run/F1_COMPAT_MANIFEST.json" \
  --population-observed "$project/results/tf_cstate_prospective_20260923/population_observed" \
  --population-truth "$project/results/tf_cstate_prospective_20260923/population_truth" \
  --stage-a-registration "$project/results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json" \
  --baseline "$project/experiments/sp_afdm_frozen_reviewed_20260921" \
  --f1-git-attestation "$run/F1_GIT_ATTESTATION.json" \
  --f1-git-attestation-sha256 5892a14612ff5a953ca76cc92e5b631348dc1cd7805f70eb818de44d231dc644 \
  --f1-observed-commit 64893916d5de5e81fd720946d666d9dbe313fb0d \
  --f1-seal-repo-path 00_Inbox/AFDM-channel-estimation/results/cstate_necessity_stageB_resume_20260928/observed_f1_compat_v1/observed_seal.json \
  --out "$out" > "$run/F1_ANALYSIS_RUN.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$run/F1_ANALYSIS_EXIT_CODE.txt"
date -u +'%Y-%m-%dT%H:%M:%SZ' > "$run/F1_ANALYSIS_ENDED_UTC.txt"
exit "$status"
