#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
stage_a_commit="$1"
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/results/cstate_necessity_stageA_20260928/scratch
export XDG_CACHE_HOME="$TMPDIR/cache" MPLCONFIGDIR="$TMPDIR/matplotlib" TORCH_HOME="$TMPDIR/torch"
/home/guoyikun/.conda/envs/AFDM/bin/python - <<'START'
from pathlib import Path
import json,time,os
p=Path('results/cstate_necessity_stageA_20260928/launch_started.json')
with p.open('x') as f:json.dump({'epoch':time.time(),'launcher_pid':os.getpid(),'mode':'single_once_no_retry','cpu_affinity':[64]},f)
START
set +e
timeout --signal=TERM --kill-after=10s 10860s taskset -c 64 /home/guoyikun/.conda/envs/AFDM/bin/python -u experiments/cstate_necessity_stageA_20260928/run_stage_a.py \
 --registration results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json \
 --registration-commit "$stage_a_commit" \
 --historical-registration results/tf_cstate_prospective_20260923/protocol/registration.json \
 --population-observed results/tf_cstate_prospective_20260923/population_observed \
 --historical-observed results/tf_cstate_prospective_20260923/observed \
 --historical-frame-outcomes results/tf_cstate_prospective_20260923/recovery_20260923/analysis/frame_outcomes.csv \
 --source experiments/sp_afdm_native_joint_reviewed_20260921 \
 --baseline experiments/sp_afdm_frozen_reviewed_20260921 \
 --preregistration results/cstate_necessity_stageA_20260928/protocol/STAGE_A_PREREGISTRATION.md \
 --f1-spec results/cstate_necessity_stageA_20260928/protocol/F1_NOMP_AFDM_SPEC.md \
 --out results/cstate_necessity_stageA_20260928/observed \
 --seconds-limit 10800.0
stage_a_exit=$?
export STAGE_A_EXIT_CODE="$stage_a_exit"
/home/guoyikun/.conda/envs/AFDM/bin/python - <<'DONE'
from pathlib import Path
import json,time,os
r=Path('results/cstate_necessity_stageA_20260928')
exit_code=int(os.environ['STAGE_A_EXIT_CODE'])
sealed=(r/'observed/observed_seal.json').is_file()
with (r/'launch_exit.json').open('x') as f:json.dump({'epoch':time.time(),'exit_code':exit_code,'observed_seal_present':sealed,'status':'complete' if exit_code==0 and sealed else 'stopped_no_retry'},f,indent=2)
DONE
exit "$stage_a_exit"
