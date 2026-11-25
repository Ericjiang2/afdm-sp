#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 MODE FREEZE_COMMIT   (MODE = gate | run)" >&2
    exit 2
fi
MODE="$1"
FREEZE_COMMIT="$2"

REPO="/data/guoyikun/00inbox/AFDM-channel-estimation"
HERE="$REPO/experiments/sameframe_hg_20261124"
OUT="$HERE/out"
mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels

LOCKDIR="$OUT/.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
    echo "ERROR: lock $LOCKDIR already held" >&2
    exit 1
fi

cd "$REPO"
set +u
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
set -u

PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
if [ "$(which python)" != "$PY" ]; then
    rmdir "$LOCKDIR" 2>/dev/null || true
    echo "ERROR: active python $(which python) != $PY" >&2
    exit 1
fi

export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export TMPDIR="/data/guoyikun/tmp"
export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

if [ "$MODE" = "gate" ]; then
    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gate_cpu.txt" \
        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/sameframe.py" \
        gate --out "$OUT" --workers 16 \
        > "$OUT/gate.log" 2>&1
    exit $?
fi

if [ "$MODE" = "run" ]; then
    if [ -d "$OUT/raw" ] && ls "$OUT/raw"/part*_shard*.jsonl* >/dev/null 2>&1; then
        rmdir "$LOCKDIR" 2>/dev/null || true
        echo "ERROR: $OUT/raw already contains shards; refuse to overwrite" >&2
        exit 1
    fi
    status=STOPPED
    cleanup() {
        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
        rmdir "$LOCKDIR" 2>/dev/null || true
    }
    trap cleanup EXIT

    # Python enforces live cumulative CPU <= 16.0 core-hours; wall timeout 3600s is outer safety net
    set +e
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/run_cpu.txt" \
        timeout --kill-after=5s 3600s "$PY" -B -u "$HERE/sameframe.py" \
        run --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
        > "$OUT/run.log" 2>&1
    rc=$?
    set -e
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
        status=STOPPED_BUDGET
        exit 124
    fi
    if [ "$rc" -ne 0 ]; then
        exit "$rc"
    fi
    test -s "$OUT/results.json"
    test -s "$OUT/RESULTS.md"
    status=DONE
    exit 0
fi

rmdir "$LOCKDIR" 2>/dev/null || true
echo "Unknown MODE: $MODE" >&2
exit 2
