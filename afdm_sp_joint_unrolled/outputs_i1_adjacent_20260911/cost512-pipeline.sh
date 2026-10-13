#!/usr/bin/env bash
set -euo pipefail
set -o noclobber
exec > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/cost512-pipeline.log 2>&1
trap 'status=$?; export ADJACENT_COST_EXIT_CODE="$status"; /home/guoyikun/.conda/envs/AFDM/bin/python -B -c '"'"'import json,os,sys,time
from pathlib import Path
root=Path('"'"'"'"'"'"'"'"'/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911'"'"'"'"'"'"'"'"')
status=int(os.environ['"'"'"'"'"'"'"'"'ADJACENT_COST_EXIT_CODE'"'"'"'"'"'"'"'"'])
now=time.time()
live=[]
for path in root.glob('"'"'"'"'"'"'"'"'cost*-runtime.json'"'"'"'"'"'"'"'"'):
 info=json.loads(path.read_text())
 proc=Path('"'"'"'"'"'"'"'"'/proc'"'"'"'"'"'"'"'"')/str(info['"'"'"'"'"'"'"'"'pid'"'"'"'"'"'"'"'"'])/'"'"'"'"'"'"'"'"'stat'"'"'"'"'"'"'"'"'
 if proc.exists() and int(proc.read_text().rsplit('"'"'"'"'"'"'"'"')'"'"'"'"'"'"'"'"',1)[1].split()[19])==info['"'"'"'"'"'"'"'"'start_ticks'"'"'"'"'"'"'"'"']:
  live.append(dict(pid=info['"'"'"'"'"'"'"'"'pid'"'"'"'"'"'"'"'"'],start_ticks=info['"'"'"'"'"'"'"'"'start_ticks'"'"'"'"'"'"'"'"'],runtime_file=str(path)))
if status==0 and (now>1789191669.2092395 or live):status=124
result=dict(schema='"'"'"'"'"'"'"'"'adjacent-cost512-final-exit-v1'"'"'"'"'"'"'"'"',started_at_unix=1789155669.2092395,
 finished_at_unix=now,elapsed_seconds=now-1789155669.2092395,deadline_unix=1789191669.2092395,
 exitcode=status,within_ten_hours=now-1789155669.2092395<=36000,within_global_deadline=now<=1789209000.,
 remaining_owned_processes=live,scope='"'"'"'"'"'"'"'"'Includes launcher, admission, collection, audits, statistics and final process cleanup.'"'"'"'"'"'"'"'"')
(root/'"'"'"'"'"'"'"'"'cost512-pipeline-exit-v1.json'"'"'"'"'"'"'"'"').open('"'"'"'"'"'"'"'"'x'"'"'"'"'"'"'"'"').write(json.dumps(result,indent=2))
(root/'"'"'"'"'"'"'"'"'cost512-pipeline.exit'"'"'"'"'"'"'"'"').open('"'"'"'"'"'"'"'"'x'"'"'"'"'"'"'"'"').write(str(status)+'"'"'"'"'"'"'"'"'\n'"'"'"'"'"'"'"'"')
sys.exit(status)
'"'"'' EXIT
printf "%s\n" "$$" > /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/cost512-pipeline.pid
cd /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/cost-runtime-v1
export TMPDIR=/data/guoyikun/tmp
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
timeout --signal=TERM --kill-after=5s 35989s /home/guoyikun/.conda/envs/AFDM/bin/python -B /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911/cost-runtime-v1/cost512-pipeline-v1.py --root /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_i1_adjacent_20260911 --started-unix 1789155669.2092395 --deadline-unix 1789191669.2092395 --bundle-sha256 9c50bca4b6eb6cea83143fa38b39c9132b9a1a506b77415bf4a1b3eab7645faa
