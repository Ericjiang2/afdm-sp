#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 6 ]; then
    echo "Usage: $0 PYTHON FREEZE_COMMIT HEADER_COMMIT PRODUCING_COMMIT SOURCE_MANIFEST MANIFEST_SHA256" >&2
    exit 2
fi
here=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd -- "$here"
out="$here/out/main_20261119"
mkdir -- "$out"
status=STOPPED
trap 'printf "%s\n" "$status" > "$out/STATUS.part"; mv -- "$out/STATUS.part" "$out/STATUS"' EXIT
mkdir -- "$out/tmp"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" TMPDIR="$out/tmp"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1

# 24 single-thread workers, the coordinator and the resource tracker can use
# at most 26 × (1375 + 2) CPU seconds before group termination (under 10 hours).
/usr/bin/time -q -f '%U %S %e' -o "$out/cpu.txt" \
    timeout --kill-after=2s 1375s "$1" -B -u "$here/run_main.py" \
    --freeze-commit "$2" --header-commit "$3" --producing-commit "$4" \
    --source-manifest "$5" --manifest-sha256 "$6" \
    --glue-reason 'Launch, budget accounting, and rendering of the frozen verdicts.' \
    > "$out/run.log" 2>&1
test -s "$out/results.json"
test -s "$out/RESULTS.md"
test -s "$out/cpu.txt"
status=DONE
