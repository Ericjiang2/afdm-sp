#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 5 ]; then
    echo "Usage: $0 PYTHON FREEZE_COMMIT LAUNCH_COMMIT LAUNCH_MANIFEST MANIFEST_SHA256" >&2
    exit 2
fi
cd -- "$(dirname -- "$0")"
out="$PWD/out/main_20261119"
mkdir -- "$out"
result=STOPPED
publish_status() {
    printf '%s\n' "$result" > "$out/STATUS.part"
    mv -- "$out/STATUS.part" "$out/STATUS"
    if [ -n "${TMUX:-}" ]; then
        tmux wait-for -S edit_budget_main_20261119_done
    fi
}
trap publish_status EXIT
mkdir -- "$out/tmp"
export CUDA_VISIBLE_DEVICES="" COPYFILE_DISABLE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR="$out/tmp"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
unset PYTHONPATH

"$1" -B -u run_main.py --freeze-commit "$2" --launch-commit "$3" \
    --manifest "$4" --manifest-sha256 "$5" > "$out/run.log" 2>&1
test -s "$out/results.json"
test -s "$out/RESULTS.md"
test -s "$out/REMOTE_ROWS_MD5.txt"
test -s "$out/cpu.txt"
result=DONE
