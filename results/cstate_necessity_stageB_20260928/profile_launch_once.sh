#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
stageb_root=results/cstate_necessity_stageB_20260928
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/results/cstate_necessity_stageB_20260928/scratch
export XDG_CACHE_HOME="$TMPDIR/cache" MPLCONFIGDIR="$TMPDIR/matplotlib" TORCH_HOME="$TMPDIR/torch"
/home/guoyikun/.conda/envs/AFDM/bin/python - <<'PY'
import json,os,time
from pathlib import Path
p=Path('results/cstate_necessity_stageB_20260928/profile_launch_started.json')
with p.open('x') as f:json.dump({'epoch':time.time(),'pid':os.getpid(),'mode':'single_once_no_retry','cpu_affinity':[64],'maximum_f1_only_calls':17},f)
PY
set +e
timeout --signal=TERM --kill-after=5s 295s taskset -c 64 /home/guoyikun/.conda/envs/AFDM/bin/python -u experiments/cstate_necessity_stageB_20260928/profile_f1.py \
 --plan results/cstate_necessity_stageB_20260928/F1_PROFILE_PLAN.md \
 --plan-sha256 05c9293dd9a26d6e0c790204f128deda53cb184e2291f7f2ea9ff4bb9f001a2b \
 --registration results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json \
 --population-observed results/tf_cstate_prospective_20260923/population_observed \
 --stage-a-observed results/cstate_necessity_stageA_20260928/observed \
 --stage-a-observed-seal-sha256 eb261e6183b8266220eb2abb7faec5bdf65ba253959374bed121f34523d65afa \
 --stage-a-source experiments/cstate_necessity_stageA_20260928 \
 --source experiments/sp_afdm_native_joint_reviewed_20260921 \
 --baseline experiments/sp_afdm_frozen_reviewed_20260921 \
 --out results/cstate_necessity_stageB_20260928/profile_run_v1 \
 > "$stageb_root/profile_run.log" 2>&1
profile_exit=$?
export STAGE_B_PROFILE_EXIT_CODE="$profile_exit"
/home/guoyikun/.conda/envs/AFDM/bin/python - <<'PY'
import json,os,time
from pathlib import Path
r=Path('results/cstate_necessity_stageB_20260928')
code=int(os.environ['STAGE_B_PROFILE_EXIT_CODE'])
with (r/'profile_launch_exit.json').open('x') as f:json.dump({'epoch':time.time(),'exit_code':code,'status':'complete' if code==0 and (r/'profile_run_v1/F1_PROFILE_RAW.json').is_file() else 'stopped_no_retry'},f,indent=2)
PY
exit "$profile_exit"
