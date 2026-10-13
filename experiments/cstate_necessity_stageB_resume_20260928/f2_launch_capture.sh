#!/usr/bin/env bash
# One frozen F2E estimator-prefix failure capture; no wrapper or truth read.
set -Eeuo pipefail
project=/data/guoyikun/00inbox/AFDM-channel-estimation
cd "$project"
resume=results/cstate_necessity_stageB_resume_20260928
launch="$resume/failure_capture_launch_v1"
out="$resume/failure_capture_v1"
python=/home/guoyikun/.conda/envs/AFDM/bin/python
manifest_sha=${1:?committed capture-manifest SHA required}
[[ "$manifest_sha" =~ ^[0-9a-f]{64}$ ]] || exit 2
[[ ! -e "$launch" && ! -e "$out" ]] || { echo 'Existing QP capture output' >&2; exit 3; }
mkdir -p "$launch/scratch/xdg" "$launch/scratch/mpl" "$launch/scratch/torch"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR="$project/$launch/scratch" XDG_CACHE_HOME="$project/$launch/scratch/xdg"
export MPLCONFIGDIR="$project/$launch/scratch/mpl" TORCH_HOME="$project/$launch/scratch/torch"
"$python" - "$resume/F2_QP_CAPTURE_MANIFEST.json" "$0" "$manifest_sha" <<'PY'
import hashlib,json,sys
from pathlib import Path
raw=Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(raw).hexdigest()==sys.argv[3], 'capture manifest SHA differs'
manifest=json.loads(raw)
assert manifest['launcher_sha256']==hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(), 'launcher SHA differs'
assert manifest['capture_script_sha256']==hashlib.sha256(Path('experiments/cstate_necessity_stageB_resume_20260928/f2_capture_qp.py').read_bytes()).hexdigest(), 'capture script SHA differs'
assert manifest['maximum_estimator_calls']==1 and manifest['maximum_wall_seconds']==60
PY
args=(taskset -c 64 timeout --signal=INT --kill-after=5s 55s "$python"
  experiments/cstate_necessity_stageB_resume_20260928/f2_capture_qp.py
  --probe-manifest "$resume/F2_PROBE_MANIFEST.json"
  --probe-manifest-sha256 713346fc4ef9a871654154f34276aba24efb7a4834f5dd08172d1574cc098d9a
  --capture-manifest "$resume/F2_QP_CAPTURE_MANIFEST.json"
  --capture-manifest-sha256 "$manifest_sha"
  --source experiments/sp_afdm_native_joint_reviewed_20260921
  --baseline experiments/sp_afdm_frozen_reviewed_20260921
  --population-observed results/tf_cstate_prospective_20260923/population_observed
  --out "$out")
printf '%q ' "${args[@]}" > "$launch/argv.txt"
printf '\n' >> "$launch/argv.txt"
started=$(date +%s)
printf '{"start_epoch":%s,"cpu":64,"maximum_estimator_calls":1,"hard_wall_seconds":60}\n' "$started" > "$launch/launch_started.json"
set +e
"${args[@]}" > "$launch/runner.log" 2>&1
code=$?
set -e
ended=$(date +%s)
printf '{"exit_code":%s,"end_epoch":%s,"wall_seconds":%s}\n' "$code" "$ended" "$((ended-started))" > "$launch/launch_exit.json"
exit "$code"
