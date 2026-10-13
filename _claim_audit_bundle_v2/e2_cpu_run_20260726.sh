#!/bin/bash
# E2 firm-seed baseline reruns — CPU-only (deinlab GPU down, driver mismatch)
# Task: .trellis/tasks/07-26-e2-firm-seed-baselines  Launched: 2026-07-26
set -e
cd /data/guoyikun/00inbox/AFDM-channel-estimation
export OMP_NUM_THREADS=64 MKL_NUM_THREADS=64

CKPT=afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk
COMMON="--ckpt $CKPT --variant C2-rel --mp-mode bp --pic-damp 0.5 --p-paths 8 \
 --tau-spread 0.010 --n-total 1024 --v-mean 2.0 --fs-factor 4.0 \
 --refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 2 \
 --target-errors 0 --min-frames 800 --max-frames 800 --seed 20260601 --cdtype complex64"

echo "[E2] main paired run start: $(date)"
python afdm_sp_joint_unrolled/paired_learned_eval.py $COMMON \
  --n-outer-iter 10 --snr-list 15 20 \
  --gateA-scorer achievable --gateA-calib-frames 400 \
  --with-cao --with-ours-reomp --with-lmmse --with-pcsi \
  --out afdm_sp_joint_unrolled/outputs_e2_baselines_s15s20_cpu \
  2>&1 | tee afdm_sp_joint_unrolled/outputs_e2_baselines_s15s20_cpu_run.log

echo "[E2] serial floor run start: $(date)"
python afdm_sp_joint_unrolled/paired_learned_eval.py $COMMON \
  --n-outer-iter 1 --snr-list 15 20 \
  --out afdm_sp_joint_unrolled/outputs_e2_serial_floor_cpu \
  2>&1 | tee afdm_sp_joint_unrolled/outputs_e2_serial_floor_cpu_run.log

echo "[E2] all done: $(date)"
