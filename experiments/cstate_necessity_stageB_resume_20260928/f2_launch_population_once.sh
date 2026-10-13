#!/usr/bin/env bash
# One locked, observed-only 1024-frame shared-prefix campaign attempt.
set -Eeuo pipefail
project=/data/guoyikun/00inbox/AFDM-channel-estimation
cd "$project"
resume=results/cstate_necessity_stageB_resume_20260928
launch="$resume/population_launch_v1"
out="$resume/population_v1"
python=/home/guoyikun/.conda/envs/AFDM/bin/python
manifest_sha=${1:?locked manifest SHA required}
[[ "$manifest_sha" =~ ^[0-9a-f]{64}$ ]] || exit 2
[[ ! -e "$launch" && ! -e "$out" ]] || { echo 'Existing F2 population attempt' >&2; exit 3; }
mkdir -p "$launch/scratch/xdg" "$launch/scratch/mpl" "$launch/scratch/torch"
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TMPDIR="$project/$launch/scratch" XDG_CACHE_HOME="$project/$launch/scratch/xdg"
export MPLCONFIGDIR="$project/$launch/scratch/mpl" TORCH_HOME="$project/$launch/scratch/torch"
outer=$("$python" - "$resume/F2_POPULATION_MANIFEST.json" "$0" "$manifest_sha" <<'PY'
import hashlib, json, sys
from pathlib import Path
data = Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(data).hexdigest() == sys.argv[3], 'manifest SHA differs'
manifest = json.loads(data)
assert manifest['launcher_sha256'] == hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(), 'launcher SHA differs'
outer = manifest['outer_hard_wall_seconds']
inner = manifest['maximum_wall_seconds']
assert type(outer) is int and type(inner) is int and 0 < inner < outer <= 604800
print(outer - 5)
PY
)
[[ "$outer" =~ ^[0-9]+$ ]] || exit 4
args=(taskset -c 64 timeout --signal=INT --kill-after=5s "${outer}s" "$python"
  experiments/cstate_necessity_stageB_resume_20260928/f2_run_population.py
  --manifest "$resume/F2_POPULATION_MANIFEST.json"
  --manifest-sha256 "$manifest_sha"
  --source experiments/sp_afdm_native_joint_reviewed_20260921
  --baseline experiments/sp_afdm_frozen_reviewed_20260921
  --population-observed results/tf_cstate_prospective_20260923/population_observed
  --historical-observed results/cstate_necessity_stageA_20260928/observed
  --branch-qualification "$resume/branch_qualification_v2"
  --out "$out")
printf '%q ' "${args[@]}" > "$launch/argv.txt"
printf '\n' >> "$launch/argv.txt"
started=$(date +%s)
printf '{"start_epoch":%s,"cpu":64,"maximum_prefix_calls":2048,"locked_outer_hard_wall_seconds":%s}\n' "$started" "$((outer+5))" > "$launch/launch_started.json"
set +e
"${args[@]}" > "$launch/runner.log" 2>&1
code=$?
set -e
ended=$(date +%s)
printf '{"exit_code":%s,"end_epoch":%s,"wall_seconds":%s}\n' "$code" "$ended" "$((ended-started))" > "$launch/launch_exit.json"
exit "$code"
