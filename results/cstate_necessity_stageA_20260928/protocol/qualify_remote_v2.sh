#!/usr/bin/env bash
set -euo pipefail
cd /data/guoyikun/00inbox/AFDM-channel-estimation
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export STAGE_A_SOURCE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921
export STAGE_A_BASELINE=/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921
export TMPDIR=/data/guoyikun/00inbox/AFDM-channel-estimation/results/cstate_necessity_stageA_20260928/scratch
export XDG_CACHE_HOME="$TMPDIR/cache" MPLCONFIGDIR="$TMPDIR/matplotlib" TORCH_HOME="$TMPDIR/torch"
export PYTHONPATH="$STAGE_A_SOURCE/src:$STAGE_A_BASELINE/src"
mkdir -p "$XDG_CACHE_HOME" "$MPLCONFIGDIR" "$TORCH_HOME"
/home/guoyikun/.conda/envs/AFDM/bin/python - <<'CHECK'
from pathlib import Path
import json,hashlib,physical,twofft,evidence,sys,numpy,scipy,torch,os
r=Path('results/cstate_necessity_stageA_20260928')
j=json.loads((r/'protocol/qualification_source_sha256.json').read_text())
for n,h in j.items():
 assert hashlib.sha256((Path('experiments/cstate_necessity_stageA_20260928')/n).read_bytes()).hexdigest()==h,n
assert Path(physical.__file__).resolve().parent==Path(os.environ['STAGE_A_BASELINE'])/'src'
assert Path(twofft.__file__).resolve().parent==Path(os.environ['STAGE_A_SOURCE'])/'src'
print(json.dumps({'source_files':len(j),'python':sys.version,'numpy':numpy.__version__,'scipy':scipy.__version__,'torch':torch.__version__,'physical':physical.__file__,'twofft':twofft.__file__,'evidence':evidence.__file__,'scope':'synthetic only; no production receiver'},indent=2))
CHECK
/home/guoyikun/.conda/envs/AFDM/bin/python experiments/cstate_necessity_stageA_20260928/qualify_f1.py --out results/cstate_necessity_stageA_20260928/qualification/F1_UNIT_TESTS_remote.json
