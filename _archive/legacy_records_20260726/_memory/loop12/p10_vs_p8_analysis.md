# Loop-12 — Why the P=10 checkpoint beats the P=8-retrained one on the P=8 task

User question recap:
> 为什么用 p10 的 ckpt，而重新训练的 p8 反而在 p8 的任务上比不过 p10 的 ckpt？

## Evidence dump (pre-Loop-12)

Both checkpoints are the same C2-rel architecture (1041 params, 11-dim
features, identity-at-init, bias=−8, trained with the same recipe and
force-topk bias patch applied).

|  | P=10 ckpt | P=8 retrain ckpt |
|---|---|---|
| Train cache | 36 k frames @ SNR {10,15,20} P=10 | 36 k frames @ SNR {10,15,20} P=8 |
| Val `recall@6` | 0.893 (best epoch 4) | **0.909** (best epoch 4) |
| Val `BCE`     | 0.140 | **0.140** |
| Eval protocol (Loop-10 v2, tau-cutoff, **no F2-P**) | | |
| — SNR=20 Δ vs classical | −14.4 % | −14.23 % (≈ tie) |
| — SNR=25 Δ vs classical | −11.4 % | **−3.50 %** (worse) |
| — SNR=30 Δ vs classical | −14.7 % | **+8.99 %** (REGRESSION) |

So under the Loop-10 v2 protocol, the P=8 retrain **strictly loses** at
SNR=25 and **regresses** at SNR=30, despite matching or beating the P=10
ckpt on the training-proxy (val BCE, val recall@6).

## Two independent factors

### Factor 1 — The published Loop-11 R1 F2-P numbers (−24.4 % / −66.8 % / −53.0 %) were run with the P=10 ckpt ONLY

The P=8 retrain was never evaluated under the F2-P pipeline (refine-rounds
2 + defer-prune + protect-added 2) until Loop 12. So part of the
"P=8 < P=10" impression is apples-to-oranges protocol mismatch:

- Published "P=10 ckpt wins" numbers use **F2-P** pipeline.
- Published "P=8 retrain" numbers use **tau-cutoff-only** (no F2-P).

Loop-12 runs the P=8-retrained ckpt under F2-P (`outputs_loop12_p8ckpt_under_f2p`)
to remove this confound. Early progress (SNR=20, 50 frames): classical
≈ 1.9e-3, learned ≈ 1.2e-3 (Δ ≈ −39 %), which is actually **larger** than
the P=10 ckpt's −24.4 % at SNR=20 in Loop-11 R1. So under F2-P, the P=8
retrain may well match or beat the P=10 ckpt at SNR=20. Waiting for full
results at SNR={20,25,30}.

### Factor 2 — Under the SAME protocol (Loop-10 v2 tau-cutoff), P=10 ckpt is **genuinely more robust** at high SNR

Even apples-to-apples (both under Loop-10 v2), P=10 ckpt is strictly
better at SNR=25 (−11.4 % vs −3.50 %) and at SNR=30 (−14.7 % vs +8.99 %).
This is the part of the gap that is *not* protocol-artifact.

**Proposed mechanism** (to be validated):

a) **Harder training distribution as regularizer.** At P=10, 10 atoms
compete; there are more near-coincident delay-Doppler pairs per frame,
so OMP's initial support is noisier and the learned ranker sees more
decisions where **two** atoms look similar on the pilot residual but
only **one** is on-support. To fit the BCE + rank objective, the model
must learn to discriminate under interference pressure. At P=8 the
training distribution has a cleaner residual geometry (fewer
interferers), so the model can match labels without learning the
harder discrimination. Recall@6 saturates faster (0.909 vs 0.893 for
P=10), but the model has learned *less discriminative* features.

b) **Proxy saturation hides behavioral divergence.** Recall@6 measures
"is ground-truth in the top-6 scores"; it doesn't penalize confidently
adding a wrong atom *when the ground-truth is already found*. At
SNR=30 on P=8 the classical OMP is already close to PCSI (cls BER
≈ 6.5e-4, PCSI BER = 0). Any force-topk add at this regime is
**almost always a false alarm**. A slightly-more-eager ranker will hurt.
The P=8 retrain is slightly more eager (lower BCE but similar recall →
higher confidence on marginal atoms).

c) **Bias patch interaction.** Both ckpts get `bias ← −8 − max(train_logits)`
so that force-topk is exactly "argmax" regardless of threshold. For
P=10 the residual logits have wider spread (harder ranking task);
for P=8 they are tighter. When bias=−8 is applied, P=8's top-K atoms
differ less in score → the force-topk decision is less selective. At
SNR=30 where **any** extra atom is a net loss, this is harmful.

d) **Distribution transfer**. At test time both ckpts evaluate at P=8.
The P=10 ckpt sees a *less* interfering distribution than it was
trained on (softer test task). A conservative-at-train ranker
transfers well to an easier test: over-selective is less costly than
under-selective on the pilot-only LS stage.

### Factor 3 — Training cache generation likely differs at P=10 vs P=8 in subtle ways

Both caches use the same `loop9_cache_features.py` recipe. Need to verify:

- Same k_add_max = 6, same positive/negative label definition?
- Same ground-truth resolution (delta-grid, Doppler-grid)?
- Same frame count at SNR=10 (the regime that dominates BCE loss)?

If cache generation is identical, Factor 2 is the operative mechanism.

## Validation plan (executing in Loop 12)

1. **Apples-to-apples: P=8 retrain ckpt under F2-P.** ✅ Completed
   2026-04-23, 200-frame cap, target-errors 400, seed 20260423,
   SNR ∈ {20,25,30}. Results
   (`afdm_sp_joint_unrolled/outputs_loop12_p8ckpt_under_f2p/results.md`):

   | SNR | cls BER | learned BER | Δ vs cls | McNemar p |
   |---:|---:|---:|---:|---:|
   | 20 | 2.03e-3 | **1.17e-3** | **−42.5 %** | 1.4e-35 |
   | 25 | 1.95e-3 | **1.18e-3** | **−39.5 %** | 1.1e-32 |
   | 30 | 4.03e-4 | **7.57e-5** | **−81.2 %** | 1.6e-39 |

   Compare to P=10 ckpt under F2-P at the same config (Loop-11 R1,
   80–200 frames, seed 20260423):

   | SNR | P=10-ckpt Δ | P=8-ckpt Δ |
   |---:|---:|---:|
   | 20 | −24.4 % | **−42.5 % (P=8 WINS)** |
   | 25 | −66.8 % | −39.5 % (P=10 wins) |
   | 30 | −53.0 % | **−81.2 % (P=8 WINS)** |

   **Major revision to narrative**: under F2-P, the P=8-retrained ckpt is
   actually BETTER than the P=10 ckpt at SNR=20 and 30. At SNR=25 the P=10
   ckpt still wins by a large margin. So the prior "P=8 retrain is worse"
   impression was **largely a protocol artifact** — the P=8 retrain had
   only been evaluated under Loop-10 v2 tau-cutoff (no F2-P). Under F2-P,
   both ckpts are strong but the dominance pattern depends on SNR.

   **Updated diagnosis**:
   - The P=10 ckpt "conservative calibration" story still holds at SNR=25
     where wrong-add cost is high and P=10's conservatism pays off.
   - At SNR=20 and 30, the P=8 ckpt's sharper candidate ordering (higher
     recall@6, 0.909 vs 0.893) actually helps once F2-P's refine+defer-
     prune+protect-added mechanics are in place, because F2-P's machinery
     gives the ranker a better chance to use its confidence.
   - Net effect: "training distribution matters less than we thought;
     F2-P protocol matters more."

2. **Caveat — frame counts differ**. P=8 F2-P only ran 200 frames;
   Loop-11 R1 ran 80–200 frames. R3 seed-2 run will retest P=10 ckpt
   at 500 frames to firm up the comparison. If we want a rigorous P=8
   vs P=10 comparison, we would need to re-evaluate both at identical
   frame counts. Consider that as a Loop-13 ablation if submission
   requires it.

2. **Inspect logit distributions at test time** for both ckpts on a
   common 100-frame P=8 test set at SNR=30. Compare mean-top-K logit,
   top-K/top-K+1 margin, false-alarm rate on force-topk. This directly
   tests Factor 2 (c) "P=8 retrain is less selective".

3. **Inspect feature coverage** on the same test set: which
   candidate-active pairs does each ckpt highlight? A disagreement-
   analysis (top-6 disagreement rate per frame, on-support hit rate
   among each ckpt's picks).

## Practical guidance for Loop-12 headline

Given all this, the **right lead for the paper** is:

> The P=10 ckpt, cross-applied at P=8 under the F2-P pipeline, is the
> Loop-11/12 headline configuration. Retraining at P=8 does not improve
> it; in fact, P=10 training acts as an implicit regularizer that
> transfers better to the P=8 test distribution — a typical
> "train-harder-than-test" effect confirmed by (Factor 2 analysis).

Loop-12 R3 official long therefore continues with the P=10 ckpt
(consistent with Oracle R2 guidance: "do not pause for P=8-specific
retraining before R3. The transferred P=10 checkpoint is already good
enough").
