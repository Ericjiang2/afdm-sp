#!/bin/bash
# Loop 10 — pre-staged commands. Run manually when Oracle R1 says GO.
# All commands are meant to be pasted in a deinlab tmux session after `conda activate AFDM`.

export PROJ=/data/guoyikun/00inbox/AFDM-channel-estimation

############################################
# PATH A — retrain C2-rel on P=8 cache (Plan A)
############################################
# Step 1 — generate P=8 feature cache at SNRs {10, 15, 20} (30k total frames)
python $PROJ/afdm_sp_joint_unrolled/loop9_cache_features.py \
  --n-total 1024 --v-mean 2.0 --p-paths 8 --tau-ms 10.0 \
  --M 48 --p-pad 64 \
  --n-10 10000 --n-15 10000 --n-20 10000 \
  --seed-base 2026042210 \
  --out $PROJ/afdm_sp_joint_unrolled/outputs_loop10_cache_p8 \
  --print-every 200

# Step 2 — train C2-rel on that cache
python $PROJ/afdm_sp_joint_unrolled/loop9_train_c2rel.py \
  --cache-dir $PROJ/afdm_sp_joint_unrolled/outputs_loop10_cache_p8 \
  --out $PROJ/afdm_sp_joint_unrolled/outputs_loop10_c2rel_train_p8 \
  --lr 1e-3 --wd 1e-4 --batch 512 --epochs 4 \
  --rank-weight 0.5 --patience 2 --k-add-max 4 \
  --train-frac 0.9 --seed 13579

# Step 2b — bias-patch ckpt for force-topk (bias += 18) if we keep Loop-9 commit rule
python - <<'EOF'
import torch
p = "/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_loop10_c2rel_train_p8"
ckpt = torch.load(p + "/ckpt_c2rel.pt", map_location="cpu", weights_only=False)
sd = ckpt.get('state_dict') or ckpt.get('module') or ckpt
bias_key = [k for k in sd.keys() if 'scorer' in k and 'bias' in k and '.1.' not in k][-1]
print("bias before:", sd[bias_key].item())
sd[bias_key] = sd[bias_key] + 18.0
print("bias after:", sd[bias_key].item())
torch.save({'state_dict': sd}, p + "/ckpt_c2rel_force_topk.pt")
print("saved ckpt_c2rel_force_topk.pt")
EOF

############################################
# PATH B — safe-swap eval on P=10-trained ckpt at P=8 (Plan C — no retrain)
############################################
# Assumes Loop-9 ckpt is still at outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt
python $PROJ/afdm_sp_joint_unrolled/paired_learned_eval.py \
  --ckpt $PROJ/afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
  --variant C2-rel --mp-mode bp --pic-damp 0.5 \
  --p-paths 8 --tau-spread 0.010 --n-total 1024 --v-mean 2.0 \
  --snr-list 10 15 20 25 30 \
  --frames-per-snr 600 --target-errors 800 --min-frames 50 \
  --seed 20260422 --cdtype complex64 --use-hard \
  --with-pcsi \
  --safe-swap --safe-swap-eps-r 0.01 \
  --out $PROJ/afdm_sp_joint_unrolled/outputs_loop10_safeswap_official_p8

############################################
# PATH C — safe-swap + retrained P=8 ckpt (Plan A + C combined)
############################################
# Run PATH A first, then:
python $PROJ/afdm_sp_joint_unrolled/paired_learned_eval.py \
  --ckpt $PROJ/afdm_sp_joint_unrolled/outputs_loop10_c2rel_train_p8/ckpt_c2rel_force_topk.pt \
  --variant C2-rel --mp-mode bp --pic-damp 0.5 \
  --p-paths 8 --tau-spread 0.010 --n-total 1024 --v-mean 2.0 \
  --snr-list 10 15 20 25 30 \
  --frames-per-snr 600 --target-errors 800 --min-frames 50 \
  --seed 20260422 --cdtype complex64 --use-hard \
  --with-pcsi \
  --safe-swap --safe-swap-eps-r 0.01 \
  --out $PROJ/afdm_sp_joint_unrolled/outputs_loop10_retrain_safeswap_p8
