#!/usr/bin/env bash
set -euo pipefail
umask 077
source_dir=$1
commit=$2
base=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments
out="$base/admission_law_20261118/out/main_20261118"
frozen=/data/guoyikun/tmp/slotmm-9b633ce9df02
export TMPDIR=/data/guoyikun/tmp CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir "$out"
exec > "$out/run.log" 2>&1
finish() {
    local rc=$?
    if [[ ! -f "$out/STATUS" ]]; then
        echo 'STOPPED launcher_error unknown' | tee "$out/STATUS.pending"
        mv "$out/STATUS.pending" "$out/STATUS"
    fi
    exit "$rc"
}
trap finish EXIT
(cd "$frozen" && sha256sum -c SHA256SUMS)
python -u "$source_dir/run_main.py" --out "$out" --commit "$commit" \
    --frozen-slot "$frozen/experiments/slot_mismatch_20261019" --archive "$base/slot_mismatch_20261019/out/main_20261118"
