#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/18736049201eric"
PROJ="${ROOT}/afdm_joint_param_unrolled"
LEGACY="${ROOT}/afdm_sp_joint_unrolled"

TRAD_OUT="${PROJ}/outputs_traditional_param"
STAGE6_OUT="${PROJ}/outputs_joint_param_ablation"
LOG_DIR="${TRAD_OUT}/logs"

mkdir -p "${TRAD_OUT}" "${LOG_DIR}"

echo "=============================================================="
echo "Stage 7: Traditional Param-Joint vs Stage 6"
echo "=============================================================="
echo "project      : ${PROJ}"
echo "legacy       : ${LEGACY}"
echo "trad_out     : ${TRAD_OUT}"
echo "stage6_out   : ${STAGE6_OUT}"
echo "log_dir      : ${LOG_DIR}"
echo

echo "[1/6] Train TradParam fixed"
python "${PROJ}/train_traditional_param.py" \
  --dataset-source teacher_cache \
  --teacher-cache "${LEGACY}/outputs_joint_unrolled/teacher_sparse_traj_cache.pt" \
  --stats "${LEGACY}/outputs_n512/global_stats.pkl" \
  --traditional-dir "${TRAD_OUT}" \
  --frames-per-snr 20 \
  --snr-list 5 10 15 20 25 \
  --epochs 1 \
  --batch-size 32 \
  --val-batch-size 64 \
  --num-outer-iters 5 \
  --pic-iters 15 \
  --max-active-atoms 25 \
  --k-leak 2 \
  --learned-param-set fixed \
  2>&1 | tee "${LOG_DIR}/train_traditional_fixed.log"
echo

echo "[2/6] Train TradParam classical_full"
python "${PROJ}/train_traditional_param.py" \
  --dataset-source teacher_cache \
  --teacher-cache "${LEGACY}/outputs_joint_unrolled/teacher_sparse_traj_cache.pt" \
  --stats "${LEGACY}/outputs_n512/global_stats.pkl" \
  --traditional-dir "${TRAD_OUT}" \
  --frames-per-snr 20 \
  --snr-list 5 10 15 20 25 \
  --epochs 1 \
  --batch-size 32 \
  --val-batch-size 64 \
  --num-outer-iters 5 \
  --pic-iters 15 \
  --max-active-atoms 25 \
  --k-leak 2 \
  --learned-param-set classical_full \
  2>&1 | tee "${LOG_DIR}/train_traditional_classical_full.log"
echo

echo "[3/6] Verify TradParam fixed"
python "${PROJ}/verify_traditional_param.py" \
  --traditional-dir "${TRAD_OUT}" \
  --baseline-dir "${LEGACY}/outputs_n512" \
  --frames 100 \
  --snr 15 20 25 \
  --num-outer-iters 5 \
  --pic-iters 15 \
  --max-active-atoms 25 \
  --k-leak 2 \
  --learned-param-set fixed \
  2>&1 | tee "${LOG_DIR}/verify_traditional_fixed.log"
echo

echo "[4/6] Verify TradParam classical_full"
python "${PROJ}/verify_traditional_param.py" \
  --traditional-dir "${TRAD_OUT}" \
  --baseline-dir "${LEGACY}/outputs_n512" \
  --frames 100 \
  --snr 15 20 25 \
  --num-outer-iters 5 \
  --pic-iters 15 \
  --max-active-atoms 25 \
  --k-leak 2 \
  --learned-param-set classical_full \
  2>&1 | tee "${LOG_DIR}/verify_traditional_classical_full.log"
echo

echo "[5/6] Compare JointOMPMP vs TradParam classical_full vs Stage6 lambda_alpha_beta"
python "${PROJ}/compare_joint_families.py" \
  --stage6-dir "${STAGE6_OUT}" \
  --traditional-dir "${TRAD_OUT}" \
  --baseline-dir "${LEGACY}/outputs_n512" \
  --frames 100 \
  --snr 15 20 25 \
  --num-outer-iters 5 \
  --num-mp-layers 6 \
  --pic-iters 15 \
  --max-active-atoms 25 \
  --k-leak 2 \
  --stage6-param-set lambda_alpha_beta \
  --traditional-param-set classical_full \
  2>&1 | tee "${LOG_DIR}/compare_full.log"
echo

echo "[6/6] Compare JointOMPMP vs TradParam fixed vs Stage6 fixed"
python "${PROJ}/compare_joint_families.py" \
  --stage6-dir "${STAGE6_OUT}" \
  --traditional-dir "${TRAD_OUT}" \
  --baseline-dir "${LEGACY}/outputs_n512" \
  --frames 100 \
  --snr 15 20 25 \
  --num-outer-iters 5 \
  --num-mp-layers 6 \
  --pic-iters 15 \
  --max-active-atoms 25 \
  --k-leak 2 \
  --stage6-param-set fixed \
  --traditional-param-set fixed \
  2>&1 | tee "${LOG_DIR}/compare_fixed.log"
echo

echo "=============================================================="
echo "Done"
echo "=============================================================="
echo "Logs:"
echo "  ${LOG_DIR}/train_traditional_fixed.log"
echo "  ${LOG_DIR}/train_traditional_classical_full.log"
echo "  ${LOG_DIR}/verify_traditional_fixed.log"
echo "  ${LOG_DIR}/verify_traditional_classical_full.log"
echo "  ${LOG_DIR}/compare_full.log"
echo "  ${LOG_DIR}/compare_fixed.log"
echo
echo "Key results:"
echo "  ${TRAD_OUT}/traditional_param_fixed_results.pkl"
echo "  ${TRAD_OUT}/traditional_param_classical_full_results.pkl"
echo "  ${TRAD_OUT}/traditional_param_fixed_verify_results.pkl"
echo "  ${TRAD_OUT}/traditional_param_classical_full_verify_results.pkl"
echo "  ${TRAD_OUT}/joint_family_compare_results.pkl"
