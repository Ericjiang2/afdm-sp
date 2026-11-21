#!/bin/bash
# One unattended, bounded gate -> twelve shards -> saved-output aggregation chain.
set -euo pipefail
if [[ ${FRESH_COHORT_BOUNDED:-0} != 1 ]]; then
  export FRESH_COHORT_BOUNDED=1
  exec timeout --kill-after=5s 845s bash "$0"
fi
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_freeze_replay_20261020
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
OLD=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2
THREE=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1
FULL=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_cohort1
OUT=/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1
mkdir "$OUT"
export TMPDIR="$OUT/tmp" TMP="$OUT/tmp" TEMP="$OUT/tmp" MPLCONFIGDIR="$OUT/mplconfig" XDG_CACHE_HOME="$OUT/cache"
export PYTHONPYCACHEPREFIX="$OUT/pycache"
mkdir -p "$TMPDIR" "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$PYTHONPYCACHEPREFIX"
: "${FRESH_COHORT_COMMIT:?set full producing commit before launch}"
pids=()
finish() {
  exit_code=$?
  trap - EXIT
  if (( exit_code != 0 )); then
    if (( ${#pids[@]} > 0 )); then kill "${pids[@]}" 2>/dev/null || true; fi
    printf 'STOPPED exit=%s\n' "$exit_code" > "$OUT/STATUS.txt"
  fi
  exit "$exit_code"
}
trap finish EXIT
capacity() {
  if awk -v l="$(cut -d' ' -f1 /proc/loadavg)" -v c="$(nproc --all)" 'BEGIN{exit !(l+12>c-16)}'; then
    echo 'insufficient spare CPU capacity' >&2; exit 1
  fi
}
capacity
printf 'GATE\n' > "$OUT/STATUS.txt"
timeout --kill-after=2s 138s python fresh_cohort.py --old-rows "$OLD" --three-rows "$THREE" --full-rows "$FULL" --producing-commit "$FRESH_COHORT_COMMIT" --out "$OUT" --shard 0 --gate-only > "$OUT/gate.log" 2>&1
capacity
printf 'RUNNING\n' > "$OUT/STATUS.txt"
for shard in $(seq 0 11); do
  timeout --kill-after=2s 698s python fresh_cohort.py --old-rows "$OLD" --three-rows "$THREE" --full-rows "$FULL" --producing-commit "$FRESH_COHORT_COMMIT" --out "$OUT" --shard "$shard" --deadline-seconds 690 > "$OUT/shard$(printf %03d "$shard").log" 2>&1 &
  pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do
  code=0
  wait "$pid" || code=$?
  printf '%s %s\n' "$pid" "$code" >> "$OUT/SHARD_EXIT_CODES.txt"
  if (( code != 0 )); then status=1; fi
done
if (( status != 0 )); then echo 'incomplete cohort: at least one shard failed' >&2; exit 1; fi
printf 'AGGREGATING\n' > "$OUT/STATUS.txt"
python aggregate_fresh_cohort.py --out "$OUT" > "$OUT/aggregate.log" 2>&1
printf 'DONE\n' > "$OUT/STATUS.txt"
trap - EXIT
