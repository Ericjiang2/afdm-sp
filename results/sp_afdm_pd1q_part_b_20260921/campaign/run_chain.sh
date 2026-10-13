#!/usr/bin/env bash
# One-shot prospective Part B: qualification, production, recount, analysis, inventory.
set -Eeuo pipefail
readonly DATA=/data/guoyikun/00inbox/AFDM-channel-estimation
readonly ROOT="$DATA/results/sp_afdm_pd1q_part_b_20260921"
readonly SOURCE="$DATA/experiments/sp_afdm_native_joint_reviewed_20260921"
readonly BASE="$DATA/experiments/sp_afdm_frozen_reviewed_20260921"
readonly E1="$DATA/results/sp_afdm_native_direction_20260921/stage_D"
readonly PYTHON=/home/guoyikun/.conda/envs/AFDM/bin/python
readonly CAMPAIGN="$ROOT/campaign"
readonly LAUNCH="$ROOT/launch"
readonly LIMIT=28800
if [[ -e "$LAUNCH" || -e "$ROOT/preflight.json" || -e "$ROOT/run" ]]; then
  echo 'Part B already attempted; automatic retry is forbidden' >&2
  exit 92
fi
if [[ ! -f "$ROOT/approved_ticket.md" || ! -f "$ROOT/statistical_contract.json" ||
      ! -f "$ROOT/qualification_reference_manifest.json" || ! -f "$E1/manifest.json" ||
      ! -d "$SOURCE/src" || ! -d "$BASE/src" ]]; then
  echo 'Part B frozen inputs are missing' >&2
  exit 91
fi
mkdir "$LAUNCH"
mkdir -p "$ROOT/tmp" "$ROOT/cache" "$ROOT/matplotlib"
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$ROOT/tmp" XDG_CACHE_HOME="$ROOT/cache" TORCH_HOME="$ROOT/cache" MPLCONFIGDIR="$ROOT/matplotlib"
export SPAFDM_BASELINE_ROOT="$BASE"
for name in CUDA_VISIBLE_DEVICES OPENBLAS_NUM_THREADS OMP_NUM_THREADS MKL_NUM_THREADS \
    NUMEXPR_NUM_THREADS PYTHONDONTWRITEBYTECODE TMPDIR XDG_CACHE_HOME TORCH_HOME \
    MPLCONFIGDIR SPAFDM_BASELINE_ROOT; do
  printf '%s=%s\n' "$name" "${!name}"
done > "$LAUNCH/environment.txt"
start="$(date +%s)"
deadline="$((start + LIMIT))"
printf 'launcher_pid=%s\nstart_epoch=%s\ndeadline_epoch=%s\n' "$$" "$start" "$deadline" > "$LAUNCH/lifecycle.txt"
finish() {
  rc="$?"
  printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$rc" >> "$LAUNCH/lifecycle.txt"
  printf '%s\n' "$rc" > "$LAUNCH/exit_code.txt"
  if (( rc != 0 )); then
    count=0
    if [[ -f "$ROOT/run/ledger.jsonl" ]]; then
      count="$(wc -l < "$ROOT/run/ledger.jsonl")"
    fi
    printf '{"status":"integrity_blocked","failed_stage":"%s","exit_code":%s,"ledger_records":%s,"stdout":"%s/%s_stdout.log","stderr":"%s/%s_stderr.log"}\n' \
      "${CURRENT_STAGE:-launcher}" "$rc" "$count" "$LAUNCH" "${CURRENT_STAGE:-launcher}" \
      "$LAUNCH" "${CURRENT_STAGE:-launcher}" > "$ROOT/blocked.json"
    printf '# Part B blocked\n\nPart B stopped before a validated prospective conclusion.\n\nFailed stage: %s\nExit code: %s\nSaved ledger records: %s\nLogs: %s/%s_stdout.log and %s/%s_stderr.log\nNo statistical verdict is claimed.\n' \
      "${CURRENT_STAGE:-launcher}" "$rc" "$count" "$LAUNCH" "${CURRENT_STAGE:-launcher}" \
      "$LAUNCH" "${CURRENT_STAGE:-launcher}" > "$ROOT/RESULTS.md"
  fi
}
trap finish EXIT
run_step() {
  name="$1"; shift
  CURRENT_STAGE="$name"
  remaining="$((deadline - $(date +%s)))"
  if (( remaining <= 0 )); then echo 'Part B global deadline reached' >&2; return 124; fi
  printf '%q ' "$@" > "$LAUNCH/${name}_argv.txt"
  printf '\n' >> "$LAUNCH/${name}_argv.txt"
  printf 'step=%s\npid=%s\nstart_epoch=%s\nremaining_seconds=%s\n' \
    "$name" "$$" "$(date +%s)" "$remaining" > "$LAUNCH/${name}_lifecycle.txt"
  set +e
  timeout --signal=TERM --kill-after=60s "${remaining}s" \
    /usr/bin/time -v -o "$LAUNCH/${name}_time.txt" "$@" \
    > "$LAUNCH/${name}_stdout.log" 2> "$LAUNCH/${name}_stderr.log" &
  child="$!"
  printf 'child_pid=%s\n' "$child" >> "$LAUNCH/${name}_lifecycle.txt"
  wait "$child"
  rc="$?"
  set -e
  printf 'finish_epoch=%s\nexit_code=%s\n' "$(date +%s)" "$rc" >> "$LAUNCH/${name}_lifecycle.txt"
  printf '%s\n' "$rc" > "$LAUNCH/${name}_exit_code.txt"
  if (( rc != 0 )); then return "$rc"; fi
}
run_step preflight "$PYTHON" -B "$CAMPAIGN/preflight.py" --source "$SOURCE" \
  --baseline "$BASE" --e1-run "$E1" --root "$ROOT" --source-commit 2d130b4d
run_step producer "$PYTHON" -B "$CAMPAIGN/run.py" --source "$SOURCE" \
  --baseline "$BASE" --root "$ROOT" --source-commit 2d130b4d
run_step recount "$PYTHON" -B "$CAMPAIGN/recount.py" --run "$ROOT/run" \
  --source "$SOURCE" --baseline "$BASE" --out "$ROOT/recount_receipt.json"
run_step analysis "$PYTHON" -B "$CAMPAIGN/analyze.py" --run "$ROOT/run" \
  --source "$SOURCE" --baseline "$BASE" --e1-run "$E1" \
  --recount-receipt "$ROOT/recount_receipt.json" --out "$ROOT/analysis"
cp "$ROOT/analysis/RESULTS.md" "$ROOT/RESULTS.md"
run_step inventory "$PYTHON" -B "$CAMPAIGN/inventory.py" --root "$ROOT" \
  --out "$ROOT/remote_inventory.json"
