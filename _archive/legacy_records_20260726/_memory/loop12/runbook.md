# Loop-12 runbook — stashed CLI for sequential execution after R3

All commands assume `cd /data/guoyikun/00inbox/AFDM-channel-estimation && conda activate AFDM`.
Banner printed by `paired_learned_eval.py` reads N, v, P, tau, ckpt at start of each run.

## R3 official long (RUNNING as `g_loop12_r3`)
```
python -u -m afdm_sp_joint_unrolled.paired_learned_eval \
    --variant C2-rel --mp-mode bp --pic-damp 0.5 --p-paths 8 --tau-ms 10.0 \
    --n-total 1024 --v-mean 2.0 --snr-list 10 15 20 25 30 \
    --frames-per-snr 500 --target-errors 800 --min-frames 200 \
    --seed 20260423 --cdtype complex64 --use-hard --with-pcsi \
    --ckpt afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
    --refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 2 \
    --out afdm_sp_joint_unrolled/outputs_loop12_r3_official
```

## Seed-2 @ SNR {20, 25} (LAUNCH AFTER R3 completes)

Tmux: `g_loop12_seed2`
```
python -u -m afdm_sp_joint_unrolled.paired_learned_eval \
    --variant C2-rel --mp-mode bp --pic-damp 0.5 --p-paths 8 --tau-ms 10.0 \
    --n-total 1024 --v-mean 2.0 --snr-list 20 25 \
    --frames-per-snr 400 --target-errors 800 --min-frames 200 \
    --seed 20260424 --cdtype complex64 --use-hard --with-pcsi \
    --ckpt afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
    --refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 2 \
    --out afdm_sp_joint_unrolled/outputs_loop12_seed2_s20_s25
```

## Classical-ablation (LAUNCH AFTER R3)

Strips learned scorer (tau > max logits so no adds) while keeping F2-P
mechanics (refine 2 + defer-prune). `--protect-added 0` because no adds
exist to protect.

Tmux: `g_loop12_classical_ablation`
```
python -u -m afdm_sp_joint_unrolled.paired_learned_eval \
    --variant C2-rel --mp-mode bp --pic-damp 0.5 --p-paths 8 --tau-ms 10.0 \
    --n-total 1024 --v-mean 2.0 --snr-list 20 25 30 \
    --frames-per-snr 300 --target-errors 600 --min-frames 150 \
    --seed 20260423 --cdtype complex64 --use-hard --with-pcsi \
    --ckpt afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
    --tau-lookup 20:100,25:100,30:100 \
    --refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 0 \
    --out afdm_sp_joint_unrolled/outputs_loop12_classical_ablation
```

## Frame bootstrap CI (run on laptop or remote after R3)

```
python -m afdm_sp_joint_unrolled._loop12_frame_bootstrap \
    --results afdm_sp_joint_unrolled/outputs_loop12_r3_official/results.json \
    --n-boot 10000 --seed 42 \
    --out afdm_sp_joint_unrolled/outputs_loop12_r3_official/bootstrap_ci.md
```

## Audit + figure

```
python afdm_sp_joint_unrolled/_loop11_audit.py \
    --results afdm_sp_joint_unrolled/outputs_loop12_r3_official/results.json
python afdm_sp_joint_unrolled/_loop10_plot.py \
    --results afdm_sp_joint_unrolled/outputs_loop12_r3_official/results.json \
    --out figures/loop12/loop12_final_ber_mse.png \
    --title-suffix "Loop-12 R3 official — N=1024 v=2 P=8 tau=10ms (seed 20260423)"
```
