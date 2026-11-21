#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
export TMP=/data/guoyikun/tmp/generator_snr_audit_20261019
export TMPDIR="$TMP"
export TEMP="$TMP"
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=''
export PYTHONPYCACHEPREFIX="$TMP/pycache"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MPLCONFIGDIR="$TMP/mpl"
export XDG_CACHE_HOME="$TMP/cache"
export TORCH_HOME="$TMP/torch"
mkdir -p "$TMP" "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$TORCH_HOME"
finish() {
  status=$?
  if [ "$status" -eq 0 ]; then word=DONE; else word=STOPPED; fi
  printf '%s exit=%s\n' "$word" "$status" > experiments/generator_snr_audit_20261019/out/main/STATUS.txt
  if [ -n "${AUDIT_COMPLETION_FIFO:-}" ]; then printf '%s\n' "$status" > "$AUDIT_COMPLETION_FIFO"; fi
}
trap finish EXIT
python experiments/generator_snr_audit_20261019/audit.py --out experiments/generator_snr_audit_20261019/out/main --freeze-revision "${AUDIT_FREEZE_REVISION:?freeze commit required}"
