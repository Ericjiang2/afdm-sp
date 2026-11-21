#!/bin/bash
# CRB gates on deinlab (protocol section 6): local-stage gates, remote-stage gates, 20-frame smoke run (4 shards) + G6/G8.
set -u
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tcom_channel_crb_20261016
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
source ~/.bashrc; conda activate AFDM
python crb_gates.py --stage local --out out/gates_remote > out/gates_local_on_remote.log 2>&1; echo local=$? >> out/gates_status.txt
python crb_gates.py --stage remote --out out/gates_remote > out/gates_remote.log 2>&1; echo remote=$? >> out/gates_status.txt
for s in 0 1 2 3; do python crb_driver.py --out out/smoke --frames 20 --shard $s --nshard 4 > out/smoke_shard$s.log 2>&1 & done; wait
python crb_gates.py --stage smoke --smoke-dir out/smoke --out out/gates_remote > out/gates_smoke.log 2>&1; echo smoke=$? >> out/gates_status.txt
echo done >> out/gates_status.txt
