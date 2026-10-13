#!/usr/bin/env bash
# One audited 0..197 full-wrapper history reproduction; no population seal.
set -Eeuo pipefail
if [[ $# -ne 2 || ! "$1" =~ ^[0-9a-f]{64}$ || ! "$2" =~ ^[0-9]+$ ]]; then
  echo 'usage: f1_prefix_launch_once.sh <diagnostic-manifest-sha256> <idle-cpu-id>' >&2
  exit 2
fi
manifest_sha=$1
cpu=$2
project=/data/guoyikun/00inbox/AFDM-channel-estimation
cd "$project"
resume=results/cstate_necessity_stageB_resume_20260928
launch="$resume/prefix_history_launch_v1"
out="$resume/prefix_history_v1"
[[ ! -e "$launch" && ! -e "$out" ]] || { echo 'prefix output exists; no retry' >&2; exit 3; }
mkdir -p "$launch/scratch/xdg" "$launch/scratch/mpl" "$launch/scratch/torch"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR="$project/$launch/scratch" XDG_CACHE_HOME="$project/$launch/scratch/xdg"
export MPLCONFIGDIR="$project/$launch/scratch/mpl" TORCH_HOME="$project/$launch/scratch/torch"
/home/guoyikun/.conda/envs/AFDM/bin/python - "$resume/F1_PREFIX_DIAGNOSTIC_MANIFEST.json" "$0" "$manifest_sha" <<'PY'
import hashlib,json,sys
from pathlib import Path
raw=Path(sys.argv[1]).read_bytes()
if hashlib.sha256(raw).hexdigest()!=sys.argv[3]:
    raise ValueError('diagnostic manifest SHA differs')
manifest=json.loads(raw)
if manifest['launcher_sha256']!=hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest():
    raise ValueError('diagnostic launcher SHA differs')
PY
old_commit=a8aaa5dedd420660ff34cda94cd7f9bc95a32821
args=(taskset -c "$cpu" timeout --signal=INT --kill-after=5s 295s
  /home/guoyikun/.conda/envs/AFDM/bin/python
  experiments/cstate_necessity_stageB_resume_20260928/f1_prefix_reproduce.py
  --diagnostic-manifest "$resume/F1_PREFIX_DIAGNOSTIC_MANIFEST.json"
  --diagnostic-manifest-sha256 "$manifest_sha"
  --registration results/cstate_necessity_stageB_20260928/STAGE_B_MANIFEST.json
  --registration-commit "$old_commit"
  --protocol results/cstate_necessity_stageB_20260928/F1_EQUIVALENCE_TIMING_PROTOCOL.md
  --stage-a-registration results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json
  --stage-a-observed results/cstate_necessity_stageA_20260928/observed
  --population-observed results/tf_cstate_prospective_20260923/population_observed
  --source experiments/sp_afdm_native_joint_reviewed_20260921
  --baseline experiments/sp_afdm_frozen_reviewed_20260921
  --out "$out" --seconds-limit 2400.0)
printf '%q ' "${args[@]}" > "$launch/argv.txt"
printf '\n' >> "$launch/argv.txt"
printf '{"cpu":%s,"maximum_attempts":409,"hard_wall_seconds":300,"start_epoch":%s}\n' \
  "$cpu" "$(date +%s)" > "$launch/launch_started.json"
set +e
"${args[@]}" > "$launch/runner.log" 2>&1
code=$?
set -e
printf '{"exit_code":%s,"end_epoch":%s,"diagnostic_prefix_present":%s}\n' \
  "$code" "$(date +%s)" \
  "$(if [[ -f "$out/diagnostic_prefix.json" ]]; then echo true; else echo false; fi)" \
  > "$launch/launch_exit.json"
exit "$code"
