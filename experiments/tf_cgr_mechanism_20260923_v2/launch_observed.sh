#!/usr/bin/env bash
# Prepared only. Run requires separate approval after the preserved failed attempt.
set -Eeuo pipefail

ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation
cd "$ROOT"
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
export CUDA_VISIBLE_DEVICES=
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TMPDIR=/data/guoyikun/tmp/tf_cgr_v2

BASE=results/tf_cgr_mechanism_20260923_v2
test ! -e "$BASE/observed"
printf '%s\n' "$$" > "$BASE/launch.pid"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$BASE/launch.started_utc"

status=0
timeout --signal=INT --kill-after=20s 1800s python experiments/tf_cgr_mechanism_20260923_v2/run_observed.py \
    --source experiments/sp_afdm_native_joint_reviewed_20260921 \
    --baseline experiments/sp_afdm_frozen_reviewed_20260921 \
    --geometry experiments/tf_cstate_validation_20260922 \
    --witness-root "$BASE/witnesses" \
    --witness-manifest "$BASE/witnesses/witness_manifest.json" \
    --witness-receipt "$BASE/witness_receipt.json" \
    --source-bindings "$BASE/qualification/source_bindings_v1.json" \
    --qualification "$BASE/qualification/local_v1/qualification.json" \
    --registration "$BASE/registration.json" \
    --out "$BASE/observed" \
    --seconds 1800 --bytes-cap 2147483648 > "$BASE/launch.log" 2>&1 || status=$?
printf '%s\n' "$status" > "$BASE/launch.exit_code"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$BASE/launch.finished_utc"
exit "$status"
