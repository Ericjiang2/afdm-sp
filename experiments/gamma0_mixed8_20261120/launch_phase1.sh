#!/usr/bin/env bash
set -Eeuo pipefail
set -o noclobber
code=$(cd "$(dirname "$0")" && pwd)
out="$code/out"
root=$(cd "$code/../.." && pwd)
python=/home/guoyikun/.conda/envs/AFDM/bin/python
cd "$root"
source experiments/headroom_ladder_20261008/env_single.sh
if [[ ${1:-} == inside ]]; then
    if [[ ${2:-} != resume ]]; then
        "$python" -B -u "$code/audit.py" --site deinlab > "$out/frame_audit_deinlab.json"
        "$python" -B -u "$code/audit.py" --merge "$out/frame_audit_local.json" "$out/frame_audit_deinlab.json" > "$out/g3.json"
    fi
    "$python" -B -u "$code/qualify.py" archive --out "$out"
    "$python" -B -u "$code/qualify.py" gates --out "$out" --audit "$out/g3.json"
    exit 0
fi

finish() {
    local rc=$? line
    trap - EXIT
    case "$rc" in
        0) line=DONE ;;
        124) line='STOPPED: Phase 1 deadline' ;;
        *) line="STOPPED: exit $rc" ;;
    esac
    printf '%s\n' "$line" > "$out/STATUS"
    tmux wait-for -S gamma0m-phase1-20261120
    exit "$rc"
}
trap finish EXIT
exec > "$out/run.log" 2>&1
# All processes in the chain are serial and numerics use one CPU thread.
# This conservative wall bound is also below the one-core-hour Phase 1 cap.
/usr/bin/time -f 'phase1_wall=%e phase1_user=%U phase1_system=%S' \
    timeout --kill-after=5s 1200s bash "$code/launch_phase1.sh" inside "${1:-}"
