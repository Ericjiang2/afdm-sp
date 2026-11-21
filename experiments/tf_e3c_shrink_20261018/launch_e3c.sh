#!/usr/bin/env bash
# Main owns tmux, source freeze, resource checks and the persistent shared budget.
set -euo pipefail
MODE=${1:?usage: launch_e3c.sh gate\|chain ROOT [NPROC]}
ROOT=${2:?new output root required}
NPROC=${3:-24}
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON=${E3C_PYTHON:-python}
BUDGET=${E3C_BUDGET_DIR:?set a shared E3C_BUDGET_DIR for every attempt}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
if ! [[ "$NPROC" =~ ^[0-9]+$ ]] || ((NPROC<1 || NPROC>24)); then
  echo 'NPROC must be 1..24' >&2; exit 2
fi
pids=()
cleanup() {
  local pid
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
}
trap cleanup INT TERM
run_shards() {
  local kind=$1 count=$2 lease=$3 out=$4 shard status=0
  shift 4
  mkdir -p "$out"
  pids=()
  for ((shard=0;shard<count;shard++)); do
    "$PYTHON" "$HERE/e3c_driver.py" --mode "$kind" --out "$out" --budget-dir "$BUDGET" \
      --shard "$shard" --nshard "$count" --lease-seconds "$lease" "$@" >"$out/shard$(printf '%03d' "$shard").log" 2>&1 &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do if ! wait "$pid"; then status=1; fi; done
  pids=()
  ((status==0))
}
if [[ "$MODE" == gate ]]; then
  if [[ -e "$ROOT" ]]; then echo 'ROOT exists; use a new attempt root and the same budget directory' >&2; exit 2; fi
  "$PYTHON" "$HERE/e3c_gate.py" unit --root "$ROOT" --budget-dir "$BUDGET"
  NGATE=$NPROC; ((NGATE<=20)) || NGATE=20
  NSMOKE=$NPROC; ((NSMOKE<=12)) || NSMOKE=12
  run_shards gate "$NGATE" "${E3C_GATE_LEASE_SECONDS:-1800}" "$ROOT/gate"
  run_shards run "$NSMOKE" "${E3C_SMOKE_LEASE_SECONDS:-1800}" "$ROOT/smoke" --smoke
  "$PYTHON" "$HERE/e3c_gate.py" merge --root "$ROOT" --budget-dir "$BUDGET"
elif [[ "$MODE" == chain ]]; then
  "$PYTHON" "$HERE/e3c_gate.py" freeze-check --root "$ROOT" --budget-dir "$BUDGET"
  if [[ -e "$ROOT/main" ]]; then echo 'main output exists; refusing overwrite' >&2; exit 2; fi
  REMAINING=$("$PYTHON" "$HERE/e3c_gate.py" remaining --root "$ROOT" --budget-dir "$BUDGET")
  LEASE=$("$PYTHON" -c 'import math,sys; print(math.floor(float(sys.argv[1])/int(sys.argv[2]))-2)' "$REMAINING" "$NPROC")
  if ((LEASE<=0)); then echo 'no remaining per-process budget' >&2; exit 3; fi
  run_shards run "$NPROC" "$LEASE" "$ROOT/main" --freeze-root "$ROOT"
  "$PYTHON" "$HERE/e3c_agg.py" --out "$ROOT/main" >"$ROOT/main/aggregation.log" 2>&1
  (cd "$ROOT/main" && sha256sum rows_shard*.jsonl config_shard*.json summary.json > RAW_SHA256.txt)
  gzip "$ROOT"/main/rows_shard*.jsonl
  (cd "$ROOT/main" && sha256sum rows_shard*.jsonl.gz > COMPRESSED_SHA256.txt)
  printf 'complete\n' > "$ROOT/STATUS"
else
  echo 'mode must be gate or chain' >&2; exit 2
fi
