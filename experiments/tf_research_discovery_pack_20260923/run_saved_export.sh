#!/bin/sh
# Offline-only readout of the preregistered, sealed prospective campaign.
set -eu
umask 077

PROJECT=/data/guoyikun/00inbox/AFDM-channel-estimation
CAMPAIGN=$PROJECT/results/tf_cstate_prospective_20260923
RUNTIME=$PROJECT/results/tf_research_discovery_pack_20260923_runtime
OUTPUT=$PROJECT/results/tf_research_discovery_pack_20260923_raw
NATIVE=$PROJECT/experiments/sp_afdm_native_joint_reviewed_20260921
BASELINE=$PROJECT/experiments/sp_afdm_frozen_reviewed_20260921
PYTHON=/home/guoyikun/.conda/envs/AFDM/bin/python

if [ -e "$OUTPUT" ]; then
    echo 'Offline export output exists; refusing overwrite' >&2
    exit 17
fi
mkdir -p "$RUNTIME/tmp" "$RUNTIME/cache"
export CUDA_VISIBLE_DEVICES=
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$RUNTIME/tmp"
export XDG_CACHE_HOME="$RUNTIME/cache"
export MPLCONFIGDIR="$RUNTIME/cache"
export TORCH_HOME="$RUNTIME/cache"
export SPAFDM_BASELINE_ROOT="$BASELINE"
export PYTHONPATH="$NATIVE/src:$BASELINE/src:$PROJECT/experiments/tf_cstate_prospective_20260923:$PROJECT/experiments/tf_cstate_validation_20260922:$PROJECT/experiments/tf_geometry_reopen_20260922:$PROJECT/experiments/tf_production_gap_audit_20260922"

set +e
"$PYTHON" -B "$PROJECT/experiments/tf_research_discovery_pack_20260923/export_pack.py" \
    --registration "$CAMPAIGN/protocol/registration.json" \
    --population-observed "$CAMPAIGN/population_observed" \
    --truth-root "$CAMPAIGN/population_truth" \
    --observed "$CAMPAIGN/observed" \
    --recovery "$CAMPAIGN/recovery_20260923" \
    --evidence-git "$CAMPAIGN/evidence_git" \
    --source "$NATIVE" \
    --baseline "$BASELINE" \
    --out "$OUTPUT" \
    --registration-commit 1d7254f5e6627b8726f9c4806147c994077cf01f \
    --seal-commit 929c679b4797de18271065b8e8bf35b67b6de13f \
    > "$RUNTIME/export.stdout.log" 2> "$RUNTIME/export.stderr.log"
status=$?
set -e
printf '%s\n' "$status" > "$RUNTIME/export.exit_code"
exit "$status"
