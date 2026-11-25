#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 MODE FREEZE_COMMIT   (MODE = gate | run)" >&2
    exit 2
fi
MODE="$1"
FREEZE_COMMIT="$2"

REPO="/data/guoyikun/00inbox/AFDM-channel-estimation"
HERE="$REPO/experiments/sameframe_cd2_20261125"
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
        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/sameframe_cd2.py" \
        gate --out "$OUT" --workers 16 \
        > "$OUT/gate.log" 2>&1
    exit $?
fi

if [ "$MODE" = "run" ]; then
    if [ -d "$OUT/raw" ] && ls "$OUT/raw"/partA_shard*.jsonl* >/dev/null 2>&1; then
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

    # Part A: Python enforces cumulative CPU <= 6.0 core-hours; wall cap 1800s outer safety net
    set +e
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/partA_cpu.txt" \
        timeout --kill-after=5s 1800s "$PY" -B -u "$HERE/sameframe_cd2.py" \
        partA --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
        > "$OUT/partA.log" 2>&1
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

    # Part B: Pick quietest idle CPU (< 10% util) BEFORE starting Python, then pin via taskset
    read -r QUIET_CPU QUIET_UTIL < <("$PY" -c '
import os, sys, time
from pathlib import Path
def rd():
    d = {}
    for ln in Path("/proc/stat").read_text().splitlines():
        n, *v = ln.split()
        if n.startswith("cpu") and n[3:].isdigit():
            f = [int(x) for x in v[:8]]
            d[int(n[3:])] = (sum(f), f[3] + f[4])
    return d
a = rd(); time.sleep(1.0); b = rd()
u = {c: 100.0 * ((b[c][0]-a[c][0]) - (b[c][1]-a[c][1])) / max(b[c][0]-a[c][0], 1) for c in os.sched_getaffinity(0)}
best = min(u, key=lambda c: (u[c], c))
if u[best] >= 10.0:
    sys.stderr.write(f"ERROR: no idle CPU available (quietest cpu {best} util={u[best]:.2f}% >= 10%)\n")
    sys.exit(1)
print(best, f"{u[best]:.2f}")
')
    export HS_QUIET_CPU_UTIL="$QUIET_UTIL"

    set +e
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/timing_cpu.txt" \
        timeout --kill-after=5s 1785s taskset -c "$QUIET_CPU" "$PY" -B -u "$HERE/sameframe_cd2.py" \
        timing --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
        > "$OUT/timing.log" 2>&1
    trc=$?
    set -e
    if [ "$trc" -eq 124 ] || [ "$trc" -eq 137 ]; then
        status=STOPPED_BUDGET
        exit 124
    fi
    if [ "$trc" -ne 0 ]; then
        exit "$trc"
    fi
    test -s "$OUT/timing_summary.json"
    test -s "$OUT/RESULTS.md"
    status=DONE
    exit 0
fi

rmdir "$LOCKDIR" 2>/dev/null || true
echo "Unknown MODE: $MODE" >&2
exit 2
