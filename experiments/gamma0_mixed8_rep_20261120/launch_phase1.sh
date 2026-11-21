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
    "$python" -B -u "$code/audit.py" --site deinlab > "$out/frame_audit_deinlab.json"
    "$python" -B -u "$code/audit.py" --merge "$out/frame_audit_local.json" "$out/frame_audit_deinlab.json" > "$out/g3.json"
    "$python" -B -u "$code/qualify.py" --audit "$out/g3.json" --out "$out"
    exit 0
fi

finish() {
    local rc=$? status
    trap - EXIT
    case "$rc" in
        0) status=DONE ;;
        124) status='STOPPED: Phase 1 wall limit' ;;
        *) status="STOPPED: exit $rc" ;;
    esac
    printf '%s\n' "$status" > "$out/STATUS"
    tmux wait-for -S gamma0r-phase1-20261120
    exit "$rc"
}
trap finish EXIT
exec > "$out/run.log" 2>&1
# The audit and receiver run serially with single-thread numerical libraries.
# Even treating all wall time as CPU leaves room under the half-core-hour cap.
/usr/bin/time -f 'phase1_wall=%e phase1_user=%U phase1_system=%S' \
    timeout --kill-after=5s 1500s bash "$code/launch_phase1.sh" inside
