#!/usr/bin/env bash
# Exactly one source-bound f197 diagnostic allocation. Run only after Git freeze.
set -Eeuo pipefail

project=/data/guoyikun/00inbox/AFDM-channel-estimation
cd "$project"
resume=results/cstate_necessity_stageB_resume_20260928
out="$resume/f197_reproduction_v1"
launch="$resume/f197_reproduction_launch_v1"
script=experiments/cstate_necessity_stageB_resume_20260928/f1_reproduce.py
python=/home/guoyikun/.conda/envs/AFDM/bin/python

export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR="$project/$launch/scratch" XDG_CACHE_HOME="$project/$launch/scratch/xdg"
export MPLCONFIGDIR="$project/$launch/scratch/mpl" TORCH_HOME="$project/$launch/scratch/torch"

if [[ "${1:-}" != --inner ]]; then
  [[ ! -e "$out" && ! -e "$launch" ]] || { echo 'Existing diagnostic output' >&2; exit 3; }
  mkdir -p "$launch/scratch/xdg" "$launch/scratch/mpl" "$launch/scratch/torch"
  printf '{"schema":"stage-b-f1-resume-launch/1","start_epoch":%s,"cpu":64,"aggregate_timeout_seconds":120,"per_process_timeout_seconds":30}\n' \
    "$(date +%s)" > "$launch/launch_started.json"
  printf 'taskset -c 64 timeout --signal=INT --kill-after=5s 115s bash %q --inner\n' "$0" > "$launch/argv.txt"
  started=$(date +%s)
  set +e
  taskset -c 64 timeout --signal=INT --kill-after=5s 115s bash "$0" --inner > "$launch/runner.log" 2>&1
  code=$?
  set -e
  printf '{"schema":"stage-b-f1-resume-launch/1","exit_code":%s,"end_epoch":%s,"wall_seconds":%s}\n' \
    "$code" "$(date +%s)" "$(($(date +%s)-started))" > "$launch/launch_exit.json"
  exit "$code"
fi

args=(--resume-registration "$resume/DIAGNOSTIC_REGISTRATION.json"
  --stage-a-registration results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json
  --stage-b-registration results/cstate_necessity_stageB_20260928/STAGE_B_MANIFEST.json
  --plan "$resume/F1_REPRODUCTION_PLAN.md"
  --stage-a-observed results/cstate_necessity_stageA_20260928/observed
  --stage-a-raw results/cstate_necessity_stageA_20260928/observed/raw/s650_f0197_C.npz
  --stopped-fast-raw results/cstate_necessity_stageB_20260928/observed_f1_matched_v1/raw/s650_f0197_Cfast.npz
  --stopped-fast-decision results/cstate_necessity_stageB_20260928/observed_f1_matched_v1/decisions/s650_f0197_Cfast.json
  --population-observed results/tf_cstate_prospective_20260923/population_observed
  --source experiments/sp_afdm_native_joint_reviewed_20260921
  --baseline experiments/sp_afdm_frozen_reviewed_20260921
  --out "$out")

run_mode() {
  printf '%s\n' "$1" >> "$launch/phase_started.txt"
  timeout --signal=INT --kill-after=5s 25s "$python" "$script" "${args[@]}" --mode "$1"
}

run_mode direct-fast
run_mode wrapper-fast
run_mode direct-reference

branch=$("$python" - "$out" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
direct=json.loads((root/'direct_fast.json').read_text())['records'][0]['coordinate_scores']
wrapper=json.loads((root/'wrapper_fast.json').read_text())['records'][0]['coordinate_scores']
print('focused' if 1002 in (direct,wrapper) else 'history')
PY
)
run_mode "$branch"

# The branch is fixed by saved initial outputs; no further acquisition is allowed.
"$python" - "$out" "$branch" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
branch=sys.argv[2]
attempts=[json.loads(line) for line in (root/'attempts.jsonl').read_text().splitlines()]
expected=5 if branch=='focused' else 12
if len(attempts)!=expected or not (root/f'{branch}.json').is_file():
    raise SystemExit('incomplete fixed diagnostic allocation')
(root/'allocation_summary.json').write_text(json.dumps({
    'schema':'stage-b-f1-resume-allocation/1','status':'complete',
    'branch':branch,'f1_acquisitions':len(attempts),'full_wrappers':1,
    'truth_reads':0,'population_receiver_run':False},sort_keys=True)+'\n')
PY
