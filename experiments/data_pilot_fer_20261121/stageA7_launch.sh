#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 MODE FREEZE_COMMIT   (MODE = gate | run)" >&2
    exit 2
fi
MODE="$1"
FREEZE_COMMIT="$2"

REPO="/data/guoyikun/00inbox/AFDM-channel-estimation"
HERE="$REPO/experiments/data_pilot_fer_20261121"
OUT="$HERE/out/stageA7"
GATE_JSON="$HERE/out/stageA7_gate.json"
mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels

LOCKDIR="$OUT/.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
    echo "ERROR: lock $LOCKDIR already held" >&2
    exit 1
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

cd "$REPO"
set +u
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
set -u

PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
if [ "$(which python)" != "$PY" ]; then
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
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gate_cpu.txt" \
        timeout --kill-after=5s 600s "$PY" -B -u "$HERE/stageA7.py" \
        gate --out "$GATE_JSON" --workers 16 \
        > "$OUT/gate.log" 2>&1
    exit $?
fi

if [ "$MODE" = "run" ]; then
    if [ -f "$OUT/results.json" ]; then
        rmdir "$LOCKDIR" 2>/dev/null || true
        echo "ERROR: $OUT/results.json already exists; refuse to overwrite confirmation run" >&2
        exit 1
    fi
    status=STOPPED
    cleanup() {
        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
        rmdir "$LOCKDIR" 2>/dev/null || true
    }
    trap cleanup EXIT

    # Python enforces stage CPU <= 1.0 core-hour; wall cap 900s outer safety net
    set +e
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/run_cpu.txt" \
        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/stageA7.py" \
        run --gate "$GATE_JSON" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 28 \
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

echo "Unknown MODE: $MODE" >&2
exit 2
