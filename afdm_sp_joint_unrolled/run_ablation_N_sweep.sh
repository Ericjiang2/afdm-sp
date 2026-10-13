#!/bin/bash
# N-sweep ablation: prove the AFDM-under-UWA-fractional-Doppler N>=256 floor.
# Hypothesis: at small N, (l_max+1)*(2*k_max+1) approaches N, OMP sparsity
# prior collapses, and tau_spread*fs >> N time-aliases the channel, so BER
# diverges. Expected curve: N=64/128 high/exploding, N>=256 converges to the
# canonical 1024 floor.
#
# Reuses canonical s20260509 ckpt, fixed eval seed, 100 frames per SNR.
# Total wall: ~20-30 min on a 4090. No retrain.
#
# Each call wrapped with || true so a small-N crash does not abort the loop.
cd /data/guoyikun/00inbox/AFDM-channel-estimation

CKPT="afdm_sp_joint_unrolled/outputs_canonical_grid_s20260509/ckpt_c2rel.pt.force_topk"

for N in 64 128 256 512 1024; do
  OUT="afdm_sp_joint_unrolled/outputs_ablation_N_sweep_n${N}"
  mkdir -p "$OUT"
  echo ""
  echo "=== N-sweep N=${N} -> ${OUT} ==="
  python afdm_sp_joint_unrolled/paired_learned_eval.py \
    --ckpt "$CKPT" --variant C2-rel \
    --mp-mode bp --pic-damp 0.5 --p-paths 8 \
    --tau-spread 0.010 --n-total "$N" --v-mean 2.0 \
    --snr-list 15 20 25 --frames-per-snr 100 \
    --fs-factor 4.0 --seed 20260423 --cdtype complex64 \
    --n-outer-iter 5 \
    --out "$OUT" 2>&1 | tee "$OUT/run.log" \
    || echo "FAILED at N=${N} (expected for small N - the failure IS the data point)"
done

echo ""
echo "=== N-sweep DONE ==="
echo "Per-N summaries:"
for N in 64 128 256 512 1024; do
  RES="afdm_sp_joint_unrolled/outputs_ablation_N_sweep_n${N}/results.json"
  if [ -f "$RES" ]; then
    echo "--- N=${N} ---"
    python -c "import json; r=json.load(open('$RES')); [print(f\"  SNR={s['snr']:>4} dB  classical_BER={s.get('classical_ber','NA'):.3e}  learned_BER={s.get('learned_ber','NA'):.3e}\") for s in r.get('per_snr', r if isinstance(r,list) else [])]" 2>/dev/null \
      || echo "  (json schema mismatch — check $RES manually)"
  else
    echo "--- N=${N}: NO results.json (job crashed) ---"
  fi
done
