#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")"
out="${1:?new Phase 1 output directory}"
frozen_slot="${2:?frozen slot-mismatch snapshot}"
archive="${3:?slot-mismatch archive}"
local_scan="${4:?local freshness inventory receipt}"
mkdir "$out"
exec > >(tee "$out/run.log") 2>&1
trap 'rc=$?; if (( rc )); then status="STOPPED $rc"; else status="DONE"; fi; echo "$status" | tee "$out/STATUS"' EXIT
export TMPDIR=/data/guoyikun/tmp PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
for gate in g1 g2 g3 history; do
    timeout 120s python -u phase1.py "$gate" --out "$out" --frozen-slot "$frozen_slot" --archive "$archive" --local-scan "$local_scan"
done
timeout 18m python -u phase1.py calibration --out "$out" --frozen-slot "$frozen_slot" --archive "$archive"
