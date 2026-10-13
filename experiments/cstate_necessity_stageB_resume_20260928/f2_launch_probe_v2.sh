#!/usr/bin/env bash
# One versioned F2E first-frame probe after the fixed grid-QP coordinate repair.
set -Eeuo pipefail
project=/data/guoyikun/00inbox/AFDM-channel-estimation
cd "$project"
resume=results/cstate_necessity_stageB_resume_20260928
launch="$resume/probe_f0000_launch_v2"
out="$resume/probe_f0000_v2"
python=/home/guoyikun/.conda/envs/AFDM/bin/python
manifest_sha=${1:?committed manifest SHA required}
[[ "$manifest_sha" =~ ^[0-9a-f]{64}$ ]] || exit 2
[[ ! -e "$launch" && ! -e "$out" ]] || { echo 'Existing F2 probe output' >&2; exit 3; }
mkdir -p "$launch/scratch/xdg" "$launch/scratch/mpl" "$launch/scratch/torch"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR="$project/$launch/scratch" XDG_CACHE_HOME="$project/$launch/scratch/xdg"
export MPLCONFIGDIR="$project/$launch/scratch/mpl" TORCH_HOME="$project/$launch/scratch/torch"
"$python" - "$resume/F2_PROBE_V2_MANIFEST.json" "$0" "$manifest_sha" <<'PY'
import hashlib,json,sys
from pathlib import Path
raw=Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(raw).hexdigest()==sys.argv[3], 'manifest SHA differs'
assert json.loads(raw)['launcher_sha256']==hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(), 'launcher SHA differs'
PY
args=(taskset -c 64 timeout --signal=INT --kill-after=5s 115s "$python"
  experiments/cstate_necessity_stageB_resume_20260928/f2_probe.py
  --manifest "$resume/F2_PROBE_V2_MANIFEST.json" --manifest-sha256 "$manifest_sha"
  --source experiments/sp_afdm_native_joint_reviewed_20260921
  --baseline experiments/sp_afdm_frozen_reviewed_20260921
  --population-observed results/tf_cstate_prospective_20260923/population_observed
  --out "$out")
printf '%q ' "${args[@]}" > "$launch/argv.txt"
printf '\n' >> "$launch/argv.txt"
started=$(date +%s)
printf '{"start_epoch":%s,"cpu":64,"maximum_calls":1,"hard_wall_seconds":120}\n' "$started" > "$launch/launch_started.json"
set +e
"${args[@]}" > "$launch/runner.log" 2>&1
code=$?
set -e
ended=$(date +%s)
printf '{"exit_code":%s,"end_epoch":%s,"wall_seconds":%s}\n' "$code" "$ended" "$((ended-started))" > "$launch/launch_exit.json"
exit "$code"
