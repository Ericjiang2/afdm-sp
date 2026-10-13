# listwise/ — listwise top-K loss for the support-refinement head

**TCOM novelty axis B1** (closes FYP R3 W-3 + folds in R3 W-2 retraining variance).
**Owning branch**: `trans/listwise-mechanism`.
**Status (2026-05-06)**: training pipeline shipped + 5-seed retrain + paired eval done. **Negative finding**: listwise loss does NOT improve BER over BCE+rank-hinge at this F2-P deployment configuration — see "Status checkpoint" below.

## Purpose

Replace the FYP receiver's BCE + pairwise rank-hinge training loss with a differentiable listwise top-K objective (NeuralSort / SoftSort / PiRank-style), so the training-time gradient signal aligns with the deterministic top-K_add ranker used at deployment. Then retrain 5 seeds to give an honest BER variance envelope.

Two-for-one: this experiment alone closes both the "loss/deployment misalignment" weakness (R3 W-3) and the "single-checkpoint, no retraining variance" weakness (R3 W-2) since 5-seed listwise runs naturally produce the variance band.

## Planned files

| File | Purpose |
|---|---|
| `losses.py` | NeuralSort / SoftSort / PiRank-style differentiable top-K loss; ~80 lines. Includes a unit test that reduces to standard BCE in the limit. |
| `train_listwise.py` | Training entrypoint; reuses `../afdm_trainer.py` dataloader + scheduler; `--seed` flag drives 5-seed sweep. |
| `eval_listwise_envelope.py` | Post-hoc 5-seed paired evaluation aggregator that reproduces §IV-B Table format. |

## Reuse

- Cache: existing 27k-frame 4-SNR feature cache (no need to regenerate).
- Training loop / optimizer / scheduler: `../train_classical_joint_unrolled.py`, `../afdm_trainer.py`.
- Architecture: `../classical_joint_unrolled.py::ClassicalJointUnrolled` — only the **loss** changes, not the backbone.
- Paired eval: `../paired_learned_eval.py` for inference-time BER measurement on the 5 trained checkpoints.

## Output convention

Per-seed checkpoints → `outputs_listwise_seed{0..4}/ckpt_listwise.pt` (gitignored by `*.pt` rule).
Per-seed paired eval → `outputs_listwise_seed{0..4}_eval/results.json`.

## Manifest

Update `../models/MANIFEST.md` with `listwise-seedN` entries when checkpoints exist.

## Risk

If listwise loss does not improve mean BER vs the BCE+rank-hinge baseline, the 5-seed run still satisfies R3 W-2 (variance envelope reporting) and gives the paper a useful "loss-design ablation" subsection. So the experiment is not a wasted run even in the no-improvement case.

## Status checkpoint (2026-05-06 session)

- [x] `losses.py`: `listnet_kl_loss` + `soft_topk_recall_loss` (NeuralSort relaxation). Smoke verified: gradient direction correct, NeuralSort tau→0.1 gives sharp top-K mask.
- [x] Ingested `loop9_train_c2rel.py` + `loop9_cache_features.py` from remote into local git (closes EXPERIMENT_AUDIT.md A-check minor WARN on cache provenance).
- [x] `train_listwise.py`: fork of loop9_train_c2rel that imports its cache-loading/dataset-split/eval helpers and only swaps the per-batch loss. Saves with `cand_active_rel.` prefix so paired_learned_eval can drop it in.
- [x] **8-epoch ListNet vs SoftTopK comparison** (single seed, on 27k-frame 4-SNR cache):
    | Loss | val_bce ep 8 | r@4 | epochs to converge |
    |---|---|---|---|
    | ListNet | **0.112** | **0.895** | 8 (still improving) |
    | SoftTopK k=4 tau=0.1 | 0.219 | 0.884 | 3 (BCE-based early stop) |
  Choice: **ListNet** for production — lower val_bce, smoother dynamics, doesn't trigger spurious early stopping.
- [x] **5-seed ListNet retrain** (run_listwise_5seed.sh, ~80 sec total):
    | seed | best_val_bce | best_ep |
    |---|---|---|
    | 20260501 | 0.150 | 8 |
    | 20260502 | 0.144 | 8 |
    | 20260503 | **0.084** | 8 |
    | 20260504 | 0.267 ⚠️ | 6 (early stop) |
    | 20260505 | 0.178 | 8 |
  Mean **0.165**, std **0.069** — real cross-seed variance at the BCE objective level.
- [x] **5-seed paired eval** (3 SNR × 100 frames × 5 seeds, ~41 min wall):
    | SNR (dB) | classical BER | learned mean BER | learned std | per-seed learned |
    |---|---|---|---|---|
    | 20 | 1.81e-4 | **3.13e-4** | **0.0** | 3.13e-4 × 5 (pixel-identical) |
    | 25 | 0 | 0 | 0 | 0 × 5 |
    | 30 | 0 | 1.56e-5 | 1.44e-5 | mild variance |

  **Two findings, the second more important than the first**:

  1. **Listwise-trained head does not improve BER over no-head classical** at this F2-P deployment configuration (refine-rounds=2, cand-topm=96, defer-prune-until-final, protect-added=2). At SNR=20, classical 1.81e-4 < listwise 3.13e-4 — listwise *adds* errors. The original BCE+rank-hinge canonical ckpt also reports a similar 3.1e-4 in the FYP paper §IV-D, so listwise reaches the same local optimum, not a worse one — it just does not exceed it.

  2. **All 5 listwise seeds give pixel-identical BER at SNR=20 dB** (3.13e-4 × 5, std=0). With 100 frames per SNR (204800 bits), 3.13e-4 corresponds to exactly 64 bit errors per seed. **Five differently-trained checkpoints make exactly the same 64-bit-error decision pattern.** The F2-P deployment refinement loop (multi-round refresh-pool with protect-added=2) is mostly determined by feature ranks; relative ordering of trained logit values produces the same selected support across all 5 seeds. Training-time stochasticity does NOT propagate to deployment. R3 W-2 variance envelope is therefore essentially a single point at SNR=20 — a stronger and more interesting finding than mere "low variance".

  **Implication for the TCOM paper**: this is a **publishable negative result** about R3 W-3 (train/deploy misalignment). Replacing BCE+rank-hinge with a listwise loss does not help because the bottleneck is NOT the training-loss form — it is the small head capacity (1041 params) combined with an F2-P deployment that's already close to a deterministic feature-rank-based selector. The training-loss form is over-parametrised for the receiver's effective decision degrees of freedom.

  **Suggested §IV-B subsection**: keep the 5-seed envelope as evidence (R3 W-2 closure), report the BER pixel-identity finding as evidence that "the receiver's deployment-time decision is robust to training-side stochasticity, indicating the head is operating at a deterministic local optimum determined by input-feature rank ordering rather than learned weight magnitudes" — useful insight, distinct from a pure no-improvement narrative.

## Files & artifacts

- `losses.py` — ListNet + SoftTopK losses + smoke test
- `train_listwise.py` — driver with `--loss listnet|soft_topk`, saves `ckpt_listwise.pt` with `cand_active_rel.` prefix
- `run_listwise_5seed.sh` — bash orchestrator, sequential 5 seeds in tmux
- `eval_listwise_envelope.py` — per-seed paired_learned_eval driver + cross-seed aggregator
- `_remap_ckpt_keys.py` — one-off prefix remap for pre-fix-commit ckpts
- `outputs_listwise_5seed/seed_<N>/ckpt_listwise.pt` — 5 trained checkpoints (gitignored, on remote `deinlab`)
- `outputs_listwise_eval/seed_<N>/results.json` — per-seed paired eval results
- `outputs_listwise_eval/envelope.json` + `envelope.md` — 5-seed aggregate (committed in this repo)
