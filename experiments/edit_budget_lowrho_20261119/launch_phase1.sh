#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out=$1
mkdir "$out"
mkdir "$out/tmp"
export TMPDIR="$PWD/$out/tmp" PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 COPYFILE_DISABLE=1
# One process with a 240-second wall limit, plus two seconds to terminate.
/usr/bin/time -f '%U %S %e' -o "$out/cpu.txt" timeout --kill-after=2s 240s \
    "$2" -u qualify.py --out "$out" > "$out/run.log" 2>&1 && {
    echo DONE > "$out/STATUS"
    exit 0
}
status=$?
echo "STOPPED ($status)" > "$out/STATUS"
exit "$status"
