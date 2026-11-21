#!/bin/bash
# DDST zero-sim screen (protocol commit c53641e6 + amendment 14e18ba3)
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008
source env_single.sh
source ~/.bashrc >/dev/null 2>&1 || true
conda activate AFDM
python ddst_screen.py geometry 2>&1 | tee out/ddst_screen/geometry_run.log
python ddst_screen.py law 2>&1 | tee out/ddst_screen/law_run.log
echo DDST_DONE
