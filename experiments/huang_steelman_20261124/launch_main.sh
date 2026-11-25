#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 MODE FREEZE_COMMIT   (MODE = gates | main)" >&2
    exit 2
fi
MODE="$1"
FREEZE_COMMIT="$2"

HERE="/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124"
OUT="$HERE/out"
mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels

# Acquire a single shared exclusive lock across gates and main BEFORE touching any log or STATUS file
LOCKDIR="$OUT/.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
    echo "ERROR: lock $LOCKDIR already held (concurrent launch blocked)" >&2
    exit 1
fi

cd /data/guoyikun/tmp
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

if [ "$MODE" = "gates" ]; then
    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gates_cpu.txt" \
        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/gates.py" \
        --out "$OUT" --workers 16 \
        > "$OUT/gates.log" 2>&1
    exit $?
fi

if [ "$MODE" = "main" ]; then
    if [ -d "$OUT/raw" ] && ls "$OUT/raw"/rows_shard*.jsonl* >/dev/null 2>&1; then
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

    # 24 single-thread workers + coordinator + resource tracker <= 26 procs.
    # Wall limit 1650s + 5s kill grace = 1655s; 26 * 1655s = 43,030 CPU-s = 11.95 core-hours (< 12.0h).
    set +e
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/main_cpu.txt" \
        timeout --kill-after=5s 1650s "$PY" -B -u "$HERE/run_main.py" \
        --gate "$OUT/gate.json" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
        > "$OUT/main.log" 2>&1
    rc=$?
    set -e
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
        status=STOPPED_BUDGET
        exit 124
    fi
    if [ "$rc" -ne 0 ]; then
        exit "$rc"
    fi
    test -s "$OUT/summary.json"
    test -s "$OUT/RESULTS.md"

    # Pick quietest CPU BEFORE starting Python, then pin via taskset (<= 0.5 core-hours = 1800s incl. grace)
    read -r QUIET_CPU QUIET_UTIL < <("$PY" -c '
import os, time
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
print(best, f"{u[best]:.2f}")
')
    export HS_QUIET_CPU_UTIL="$QUIET_UTIL"

    set +e
    /usr/bin/time -q -f '%U %S %e' -o "$OUT/timing_cpu.txt" \
        timeout --kill-after=5s 1785s taskset -c "$QUIET_CPU" "$PY" -B -u "$HERE/timing.py" \
        --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
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
    status=DONE
    exit 0
fi

rmdir "$LOCKDIR" 2>/dev/null || true
echo "Unknown MODE: $MODE" >&2
exit 2
