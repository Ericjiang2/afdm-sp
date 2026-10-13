#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(cd "${ROOT_DIR}/.." && pwd)"

OUT_DIR="${AFDM_OUT_DIR:-${ROOT_DIR}/outputs_joint_unrolled}"
BASELINE_DIR="${AFDM_BASELINE_DIR:-${ROOT_DIR}/outputs_n512}"
RAW_TEACHER="${AFDM_RAW_TEACHER:-${OUT_DIR}/teacher_labels/teacher_all_snr_traj.npz}"
TEACHER_CACHE="${AFDM_TEACHER_CACHE:-${OUT_DIR}/teacher_sparse_traj_cache.pt}"
STATS_PATH="${AFDM_STATS_PATH:-${BASELINE_DIR}/global_stats.pkl}"
CE_CKPT="${AFDM_CE_CKPT:-${BASELINE_DIR}/dnn_ce_model.pt}"

FRAMES_PER_SNR="${AFDM_FRAMES_PER_SNR:-100}"
VERIFY_FRAMES="${AFDM_VERIFY_FRAMES:-100}"
SUPPORT_EPOCHS="${AFDM_SUPPORT_EPOCHS:-0}"
DETECTOR_EPOCHS="${AFDM_DETECTOR_EPOCHS:-6}"
JOINT_EPOCHS="${AFDM_JOINT_EPOCHS:-6}"
HARD_EPOCHS="${AFDM_HARD_EPOCHS:-4}"
BATCH_SIZE="${AFDM_BATCH_SIZE:-64}"
VAL_BATCH_SIZE="${AFDM_VAL_BATCH_SIZE:-64}"
NUM_WORKERS="${AFDM_NUM_WORKERS:-4}"
NUM_OUTER_ITERS="${AFDM_NUM_OUTER_ITERS:-5}"
NUM_MP_LAYERS="${AFDM_NUM_MP_LAYERS:-6}"
MAX_ACTIVE_ATOMS="${AFDM_MAX_ACTIVE_ATOMS:-25}"
K_LEAK="${AFDM_K_LEAK:-2}"
HARD_LR="${AFDM_HARD_LR:-2e-4}"
HARD_SNR_LIST="${AFDM_HARD_SNR_LIST:-5 25}"
ENABLE_TF32="${AFDM_ENABLE_TF32:-1}"
FORCE_TEACHER="${AFDM_FORCE_TEACHER:-0}"
SNR_LIST="${AFDM_SNR_LIST:-5 10 15 20 25}"

LOG_DIR="${OUT_DIR}/logs"
mkdir -p "${LOG_DIR}" "$(dirname "${RAW_TEACHER}")"

cd "${WORK_DIR}"

TF32_FLAG=""
if [[ "${ENABLE_TF32}" == "1" ]]; then
  TF32_FLAG="--enable-tf32"
fi

FORCE_FLAG=""
if [[ "${FORCE_TEACHER}" == "1" ]]; then
  FORCE_FLAG="--force-generate"
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
TEACHER_LOG="${LOG_DIR}/01_prepare_teacher_${STAMP}.log"
TRAIN_LOG="${LOG_DIR}/02_train_joint_${STAMP}.log"
VERIFY_LOG="${LOG_DIR}/03_verify_joint_${STAMP}.log"

echo "==> [1/3] Prepare trajectory teacher cache"
python -m afdm_sp_joint_unrolled.prepare_teacher_sparse \
  --raw-teacher "${RAW_TEACHER}" \
  --cache "${TEACHER_CACHE}" \
  --stats "${STATS_PATH}" \
  --snr-list ${SNR_LIST} \
  --frames-per-snr "${FRAMES_PER_SNR}" \
  --rho 0.5 \
  --batch-size 256 \
  ${FORCE_FLAG} | tee "${TEACHER_LOG}"

echo "==> [2/3] Train sparse joint unrolled receiver"
python -m afdm_sp_joint_unrolled.train_joint_unrolled \
  --out-dir "${OUT_DIR}" \
  --teacher-cache "${TEACHER_CACHE}" \
  --raw-teacher "${RAW_TEACHER}" \
  --stats "${STATS_PATH}" \
  --ce-ckpt "${CE_CKPT}" \
  --batch-size "${BATCH_SIZE}" \
  --val-batch-size "${VAL_BATCH_SIZE}" \
  --num-workers "${NUM_WORKERS}" \
  --support-epochs "${SUPPORT_EPOCHS}" \
  --detector-epochs "${DETECTOR_EPOCHS}" \
  --joint-epochs "${JOINT_EPOCHS}" \
  --hard-epochs "${HARD_EPOCHS}" \
  --support-lr 2e-3 \
  --detector-lr 5e-4 \
  --joint-lr 5e-4 \
  --hard-lr "${HARD_LR}" \
  --frames-per-snr "${FRAMES_PER_SNR}" \
  --snr-list ${SNR_LIST} \
  --hard-snr-list ${HARD_SNR_LIST} \
  --num-outer-iters "${NUM_OUTER_ITERS}" \
  --num-mp-layers "${NUM_MP_LAYERS}" \
  --max-active-atoms "${MAX_ACTIVE_ATOMS}" \
  --k-leak "${K_LEAK}" \
  ${TF32_FLAG} | tee "${TRAIN_LOG}"

echo "==> [3/3] Verify against baselines"
python -m afdm_sp_joint_unrolled.verify_joint_unrolled \
  --joint-dir "${OUT_DIR}" \
  --baseline-dir "${BASELINE_DIR}" \
  --frames "${VERIFY_FRAMES}" \
  --snr ${SNR_LIST} | tee "${VERIFY_LOG}"

echo
echo "Done."
echo "  Teacher log: ${TEACHER_LOG}"
echo "  Train log  : ${TRAIN_LOG}"
echo "  Verify log : ${VERIFY_LOG}"
