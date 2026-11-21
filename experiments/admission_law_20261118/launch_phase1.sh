#!/usr/bin/env bash
# Invoke under bash -lc after activating AFDM, in tmux session g_admlaw.
set -euo pipefail
umask 077
cd "$(dirname "$0")"
out="${1:?pass a new gate output directory}"
frozen_slot="${2:?pass the producing slot-mismatch snapshot directory}"
archive="${3:?pass the slot-mismatch archive directory}"
mkdir "$out"
exec > >(tee "$out/run.log") 2>&1
trap 'rc=$?; if (( rc )); then echo "STOPPED $rc"; else echo "DONE"; fi' EXIT
export TMPDIR=/data/guoyikun/tmp PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
for gate in g1 g2 g3 smoke; do
    timeout 120s python -u gates.py "$gate" --out "$out/$gate.json" --frozen-slot "$frozen_slot" --archive "$archive"
done
