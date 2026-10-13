#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/18736049201eric"
PROJ="${ROOT}/afdm_joint_param_unrolled"
LEGACY="${ROOT}/afdm_sp_joint_unrolled"
OUT_DIR="${PROJ}/outputs_joint_param_ablation"
LOG_DIR="${OUT_DIR}/logs"

ENV_NAME="myenv"
FRAMES_PER_SNR=20
VERIFY_FRAMES=100
SNR_LIST=(5 10 15 20 25)
VERIFY_SNR_LIST=(15 20 25)
MODES=(fixed lambda_only alpha_beta_only lambda_alpha_beta)

BATCH_SIZE=32
VAL_BATCH_SIZE=64
EPOCHS=1
OUTER_ITERS=5
MP_LAYERS=6
MAX_ACTIVE=25
K_LEAK=2

mkdir -p "${OUT_DIR}" "${LOG_DIR}"

if [ -f /opt/conda/etc/profile.d/conda.sh ]; then
  . /opt/conda/etc/profile.d/conda.sh
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  . "${HOME}/miniconda3/etc/profile.d/conda.sh"
elif [ -f "${HOME}/anaconda3/etc/profile.d/conda.sh" ]; then
  . "${HOME}/anaconda3/etc/profile.d/conda.sh"
else
  echo "ERROR: conda.sh not found"
  exit 1
fi

conda activate "${ENV_NAME}"

echo "==> Stage 6 Ablation First"
echo "    project   = ${PROJ}"
echo "    legacy    = ${LEGACY}"
echo "    out_dir   = ${OUT_DIR}"
echo "    log_dir   = ${LOG_DIR}"
echo

for MODE in "${MODES[@]}"; do
  echo "================================================================"
  echo "==> TRAIN MODE: ${MODE}"
  echo "================================================================"

  python "${PROJ}/train_joint_param.py" \
    --dataset-source teacher_cache \
    --teacher-cache "${LEGACY}/outputs_joint_unrolled/teacher_sparse_traj_cache.pt" \
    --stats "${LEGACY}/outputs_n512/global_stats.pkl" \
    --joint-dir "${OUT_DIR}" \
    --frames-per-snr "${FRAMES_PER_SNR}" \
    --snr-list "${SNR_LIST[@]}" \
    --epochs "${EPOCHS}" \
    --batch-size "${BATCH_SIZE}" \
    --val-batch-size "${VAL_BATCH_SIZE}" \
    --num-outer-iters "${OUTER_ITERS}" \
    --num-mp-layers "${MP_LAYERS}" \
    --max-active-atoms "${MAX_ACTIVE}" \
    --k-leak "${K_LEAK}" \
    --learned-param-set "${MODE}" \
    2>&1 | tee "${LOG_DIR}/train_${MODE}.log"

  echo
  echo "----------------------------------------------------------------"
  echo "==> VERIFY MODE: ${MODE}"
  echo "----------------------------------------------------------------"

  python "${PROJ}/verify_joint_param.py" \
    --joint-dir "${OUT_DIR}" \
    --baseline-dir "${LEGACY}/outputs_n512" \
    --frames "${VERIFY_FRAMES}" \
    --snr "${VERIFY_SNR_LIST[@]}" \
    --num-outer-iters "${OUTER_ITERS}" \
    --num-mp-layers "${MP_LAYERS}" \
    --max-active-atoms "${MAX_ACTIVE}" \
    --k-leak "${K_LEAK}" \
    --learned-param-set "${MODE}" \
    2>&1 | tee "${LOG_DIR}/verify_${MODE}.log"

  echo
done

echo "==> Done"
echo "Logs:"
echo "    ${LOG_DIR}/train_fixed.log"
echo "    ${LOG_DIR}/train_lambda_only.log"
echo "    ${LOG_DIR}/train_alpha_beta_only.log"
echo "    ${LOG_DIR}/train_lambda_alpha_beta.log"
echo "    ${LOG_DIR}/verify_fixed.log"
echo "    ${LOG_DIR}/verify_lambda_only.log"
echo "    ${LOG_DIR}/verify_alpha_beta_only.log"
echo "    ${LOG_DIR}/verify_lambda_alpha_beta.log"
echo
echo "Results:"
echo "    ${OUT_DIR}/param_joint_fixed_results.pkl"
echo "    ${OUT_DIR}/param_joint_lambda_only_results.pkl"
echo "    ${OUT_DIR}/param_joint_alpha_beta_only_results.pkl"
echo "    ${OUT_DIR}/param_joint_lambda_alpha_beta_results.pkl"
echo "    ${OUT_DIR}/param_joint_fixed_verify_results.pkl"
echo "    ${OUT_DIR}/param_joint_lambda_only_verify_results.pkl"
echo "    ${OUT_DIR}/param_joint_alpha_beta_only_verify_results.pkl"
echo "    ${OUT_DIR}/param_joint_lambda_alpha_beta_verify_results.pkl"
