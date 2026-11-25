#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 MODE FREEZE_COMMIT   (MODE = gate | run | timing)" >&2
    exit 2
fi
MODE="$1"
FREEZE_COMMIT="$2"

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

REPO="/data/guoyikun/00inbox/AFDM-channel-estimation"
HERE="$REPO/experiments/data_pilot_fer_20261121"
OUT="$HERE/out/stageA9"
GATE_JSON="$HERE/out/stageA9_gate.json"
LEDGER_JSONL="$OUT/cpu_ledger.jsonl"
LOCKFILE="$OUT/.exec.flock"
mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels

export A9_ATTEMPT_ID="${MODE}_$$_$(date +%s)"
child_pgid=""
cpu_file=""
PY=""
attempt_registered=0
forced_sigkill=0
reserved_hours="0.0"
run_status=""
write_run_status=0

reap_process_group() {
    local pgid="$1"
    if kill -0 -- "-$pgid" 2>/dev/null; then
        kill -TERM -- "-$pgid" 2>/dev/null || true
        local i
        for i in $(seq 1 25); do
            if ! kill -0 -- "-$pgid" 2>/dev/null; then
                break
            fi
            sleep 0.2
        done
        if kill -0 -- "-$pgid" 2>/dev/null; then
            forced_sigkill=1
            kill -KILL -- "-$pgid" 2>/dev/null || true
            for i in $(seq 1 25); do
                if ! kill -0 -- "-$pgid" 2>/dev/null; then
                    break
                fi
                sleep 0.1
            done
        fi
    fi
    wait "$pgid" 2>/dev/null || true
}

settle_ledger() {
    if [ "$attempt_registered" -ne 1 ] || [ -z "$PY" ]; then
        return 0
    fi
    "$PY" -B - "$LEDGER_JSONL" "$A9_ATTEMPT_ID" "$MODE" "$cpu_file" "$reserved_hours" "$forced_sigkill" <<'PYEOF' || true
import json, os, pathlib, sys, time
lp = pathlib.Path(sys.argv[1])
aid, mode, cpu_f = sys.argv[2], sys.argv[3], sys.argv[4]
res_h, forced_kill = float(sys.argv[5]), int(sys.argv[6])
py_reaped_clean = False
py_cpu_h = 0.0
if lp.is_file():
    for ln in lp.read_text(encoding='utf-8').splitlines():
        if ln.strip():
            r = json.loads(ln)
            if r.get('attempt_id') == aid and r.get('status') not in ('STARTED', 'SHELL_SETTLED'):
                py_cpu_h = max(py_cpu_h, float(r.get('cpu_hours', 0.0)))
                if bool(r.get('reaped_all_workers', False)):
                    py_reaped_clean = True
time_v_h = 0.0
if cpu_f and pathlib.Path(cpu_f).is_file():
    parts = pathlib.Path(cpu_f).read_text(encoding='utf-8').strip().split()
    if len(parts) >= 2:
        try:
            time_v_h = (float(parts[0]) + float(parts[1])) / 3600.0
        except ValueError:
            time_v_h = 0.0
# Release excess reservation ONLY when forced_kill == 0 AND Python explicitly verified all workers were reaped clean.
if forced_kill == 0 and py_reaped_clean:
    settled_h = max(py_cpu_h, time_v_h)
else:
    settled_h = max(res_h, py_cpu_h, time_v_h)
rec = dict(
    ts=round(time.time(), 3),
    pid=os.getpid(),
    attempt_id=aid,
    mode=mode,
    status='SHELL_SETTLED',
    cpu_hours=max(0.0, float(settled_h)),
    reserved_hours=max(0.0, res_h),
    reaped_all_workers=bool(forced_kill == 0 and py_reaped_clean),
)
lp.parent.mkdir(parents=True, exist_ok=True)
with lp.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, allow_nan=False) + '\n')
    fh.flush()
    os.fsync(fh.fileno())
PYEOF
}

cleanup() {
    if [ -n "$child_pgid" ]; then
        reap_process_group "$child_pgid"
        child_pgid=""
    fi
    settle_ledger
    if [ "$write_run_status" -eq 1 ] && [ -n "$run_status" ]; then
        printf "%s\n" "$run_status" > "$OUT/STATUS.$$.part"
        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    fi
    exec 9>&- 2>/dev/null || true
}

on_term() {
    if [ "$write_run_status" -eq 1 ]; then
        run_status="STOPPED_SIGNAL"
    fi
    exit 143
}

# Acquire canonical flock (inherited across setsid group so SIGKILL on supervisor still holds lock until last worker exits!)
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    echo "ERROR: Stage A9 execution lock $LOCKFILE already held" >&2
    exit 1
fi
trap cleanup EXIT
trap on_term INT TERM
export A9_EXEC_FLOCK_HELD=1
export A9_EXEC_FLOCK_FD=9
export A9_SUPERVISED_BY_LAUNCH_SH=1

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

admit_and_reserve() {
    local w="$1"
    local admit_out
    admit_out=$("$PY" -B "$HERE/stageA9.py" admit \
        --mode "$MODE" \
        --freeze-commit "$FREEZE_COMMIT" \
        --attempt-id "$A9_ATTEMPT_ID" \
        --workers "$w")
    read -r reserved_hours outer_timeout_sec <<< "$admit_out"
    attempt_registered=1
    export A9_ADMITTED_BY_LAUNCH_SH=1
}

if [ "$MODE" = "gate" ]; then
    GATE_W="${A9_WORKERS:-8}"
    admit_and_reserve "$GATE_W"
    cpu_file="$OUT/gate_cpu.txt"
    rm -f "$cpu_file"
    set +e
    setsid /usr/bin/time -q -f '%U %S %e' -o "$cpu_file" \
        timeout --foreground --signal=TERM --kill-after=15s "${outer_timeout_sec}s" "$PY" -B -u "$HERE/stageA9.py" \
        gate --out "$GATE_JSON" --workers "$GATE_W" \
        > "$OUT/gate.log" 2>&1 &
    child_pgid=$!
    wait "$child_pgid"
    rc=$?
    if [ "$rc" -eq 137 ]; then forced_sigkill=1; fi
    reap_process_group "$child_pgid"
    child_pgid=""
    set -e
    exit "$rc"
fi

if [ "$MODE" = "run" ]; then
    RUN_W="${A9_WORKERS:-32}"
    admit_and_reserve "$RUN_W"
    write_run_status=1
    run_status="STOPPED"
    cpu_file="$OUT/run_cpu.txt"
    rm -f "$cpu_file"

    set +e
    setsid /usr/bin/time -q -f '%U %S %e' -o "$cpu_file" \
        timeout --foreground --signal=TERM --kill-after=15s "${outer_timeout_sec}s" "$PY" -B -u "$HERE/stageA9.py" \
        run --gate "$GATE_JSON" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers "$RUN_W" \
        > "$OUT/run.log" 2>&1 &
    child_pgid=$!
    wait "$child_pgid"
    rc=$?
    if [ "$rc" -eq 137 ]; then forced_sigkill=1; fi
    reap_process_group "$child_pgid"
    child_pgid=""
    set -e
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
        run_status="STOPPED_BUDGET"
        exit 124
    fi
    if [ "$rc" -ne 0 ]; then
        exit "$rc"
    fi
    test -s "$OUT/results.json"
    test -s "$OUT/RESULTS.md"
    run_status="DONE"
    exit 0
fi

if [ "$MODE" = "timing" ]; then
    read -r IDLE_CPU BUSY_PCT < <("$PY" -B -c "
import os, pathlib, sys, time
allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else list(range(128))
allowed_set = set(allowed)
pref = os.environ.get('A9_QUIET_CPU', '').strip()
if pref:
    c0 = int(pref)
    if c0 not in allowed_set:
        sys.stderr.write(f'Requested A9_QUIET_CPU={c0} not in allowed affinity {allowed}\n'); sys.exit(1)
    cands = [c0]
else:
    high = [c for c in allowed if 64 <= c < 128]
    rest = [c for c in allowed if c not in high]
    cands = list(reversed(high)) + list(reversed(rest))

def sibs(cid):
    p = pathlib.Path(f'/sys/devices/system/cpu/cpu{cid}/topology/thread_siblings_list')
    if not p.is_file():
        return [cid]
    out = []
    for part in p.read_text(encoding='utf-8').strip().split(','):
        part = part.strip()
        if not part: continue
        if '-' in part:
            a, b = part.split('-', 1); out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out)) or [cid]

def snap():
    out = {}
    for ln in open('/proc/stat', 'r', encoding='utf-8'):
        if ln.startswith('cpu') and ln[3:4].isdigit():
            ps = ln.split(); cid = int(ps[0][3:]); vals = [int(x) for x in ps[1:]]
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
            out[cid] = (sum(vals), idle)
    return out

s0 = snap(); time.sleep(0.5); s1 = snap()
best = None
seen_phys = set()
for c in cands:
    sb = tuple(sibs(c))
    if sb in seen_phys:
        continue
    seen_phys.add(sb)
    if any(x not in s0 or x not in s1 for x in sb):
        continue
    max_b = 0.0
    for x in sb:
        dt = max(1, s1[x][0] - s0[x][0])
        di = max(0, s1[x][1] - s0[x][1])
        max_b = max(max_b, 100.0 * (1.0 - di / float(dt)))
    if max_b < 5.0:
        best = (c, max_b); break
    if best is None or max_b < best[1]:
        best = (c, max_b)
if best is None or best[1] >= 10.0:
    sys.stderr.write(f'No quiet physical core (<10% max sibling busy) found, best={best}\n'); sys.exit(1)
print(f'{best[0]} {best[1]:.2f}')
")
    export A9_MEASURED_CPU_BUSY_PCT="$BUSY_PCT"
    admit_and_reserve 1
    cpu_file="$OUT/timing_cpu.txt"
    rm -f "$cpu_file"
    set +e
    setsid /usr/bin/time -q -f '%U %S %e' -o "$cpu_file" \
        timeout --foreground --signal=TERM --kill-after=5s "${outer_timeout_sec}s" taskset -c "$IDLE_CPU" "$PY" -B -u "$HERE/stageA9.py" \
        timing --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
        > "$OUT/timing.log" 2>&1 &
    child_pgid=$!
    wait "$child_pgid"
    rc=$?
    if [ "$rc" -eq 137 ] || [ "$rc" -eq 152 ]; then forced_sigkill=1; fi
    reap_process_group "$child_pgid"
    child_pgid=""
    set -e
    if [ "$rc" -ne 0 ]; then
        exit "$rc"
    fi
    test -s "$OUT/timing_summary.json"
    exit 0
fi

echo "Unknown MODE: $MODE" >&2
exit 2
