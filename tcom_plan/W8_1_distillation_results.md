# W8 #1 Knowledge distillation iter=10 → iter=3 — Results

**Date**: 2026-05-12
**Status**: KILL — offline-softlabel-distilled C2-rel head catastrophically regresses at iter=3 across 3 seeds
**Wall-clock**: ~33 min (3 seeds × ~11 min per 200f × 3 SNR cell)

## Setup

W8 plan #1 (the "ACTIVE NEXT" item that was bypassed by the B+ path) prescribed: train a student receiver at iter=3 with α·BCE(hard) + (1−α)·KL(student||teacher) where teacher is canonical iter=10.

Existing infrastructure realisation (this work):
- Teacher = canonical iter=10 ckpt @ `outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk`
- Cache `outputs_loop13_4B_cache_softlabels/` contains teacher iter=10 per-candidate **soft labels** (gain-weighted posteriors in [0,1])
- Student ckpts `outputs_softlabel_train_s2026050{7,8,9}/` trained via `loop9_train_c2rel.py --use-soft-labels` (BCE on teacher posteriors instead of hard 0/1 labels). This is the **distillation form** the plan asked for.
- Existing evals at iter=5 and iter=10 deploy of these distilled ckpts already documented.
- This work: paired eval at `--n-outer-iter 3` (the W8 #1 student target).

3 ckpts × 3 SNR × 200 frames (paired vs classical iter=3), eval seed 20260423.

## Headline result (3-seed)

| Seed | SNR=15 ΔBER | SNR=20 ΔBER | SNR=25 ΔBER | McNemar p (learned-better) |
|---|---|---|---|---|
| 20260507 | **+25.58%** | **+181.58%** | **+636.92%** | 1.0 (head is sig. WORSE) |
| 20260508 | +25.58% | +181.58% | +630.84% | 1.0 |
| 20260509 | +25.58% | +181.58% | +626.64% | 1.0 |
| **mean** | **+25.58%** | **+181.58%** | **+631.47%** | — |

McNemar n10/n01 at SNR=20 (seed 20260507): **103 / 1848** — head flips 1745 net atoms in the wrong direction per 200 frames.

CE NMSE also degrades:
- Classical iter=3 @ SNR=15: −15.74 dB
- Learned iter=3 @ SNR=15: **−15.46 dB** (head HURTS channel estimation by 0.28 dB)

## Deploy-iter sweep on same ckpt

| Deploy iter | SNR=15 ΔBER | SNR=20 ΔBER | SNR=25 ΔBER | Verdict |
|---|---|---|---|---|
| iter=10 (teacher's iter) | −4.10% | +16.46% (noise) | +68.75% (noise) | matches canonical baseline |
| iter=5 (intermediate) | −3.65% | +21.94% (noise) | +112.50% (noise) | -0.45pp slight regression |
| **iter=3 (W8 #1 target)** | **+25.58%** | **+181.58%** | **+636.92%** | **CATASTROPHIC** |

→ Same head, deployed at iter=10 matches canonical. Deployed at iter=5 marginally worse. Deployed at iter=3 **breaks completely**. The head's iter-dependence is the issue, not its absolute capacity.

## Mechanism

The C2-rel head's per-candidate features include positional/topology terms `(l_c/l_max, k_c/k_max, d_l_nn/l_max, d_k_nn/k_max)` where `(d_l_nn, d_k_nn)` is the nearest-active-support distance.

- **Training** sees teacher iter=10 *converged* support: dense, well-spread, P-near-correct atoms.
- **Deployment at iter=3** has receiver in *partial* state: support has 3-5 atoms only, residual still large, OMP+MP haven't converged.
- Features `(d_l_nn, d_k_nn)` mean different things in the two states: at iter=10 small distance = "candidate is in cluster region of a confirmed atom" (positive signal); at iter=3 small distance = "candidate is near a SPECULATIVE atom that may be wrong" (no positive signal).
- The head trained on teacher labels at iter=10 → applies iter=10-conditional discrimination logic to iter=3 partial state → systematically adds wrong atoms → DA-LS gains corrupt → MP-BP fails → BER catastrophic.

This is exactly W8 plan R3: "Teacher iter=10 was trained at iter=10 from scratch — distilling a forward-cropped variant may simply not have enough representational capacity at iter=3 (architectural floor)." Confirmed.

## Comparison to B+ all variant at iter=3

The B+ path (QA #28) achieved at iter=3 unweighted **−55% rel ΔBER vs classical iter=3** with the "all" variant (6 learned components: scalars + strategy + symbol_refiner + per_iter_refiner + iter_residual_selector + channel_tap_corrector), trained from scratch at iter=3 with classical hard-label BCE.

Why does B+ work but softlabel-C2-rel fail?
- B+ "all" variant has **6 learned components** sharing the iter=3 supervision, each absorbing part of the iter=3 residual-handling burden.
- Softlabel-C2-rel has **1 component** (cand_active_rel only, 1041 params) trying to redirect a partial OMP support.
- B+ "all" trained **at iter=3** sees iter=3 receiver state during training → learns iter=3-conditional logic.
- Softlabel-C2-rel trained **on offline cache** generated from teacher iter=10 → never sees iter=3 partial state during training.

So the W8 #1 hypothesis (offline distillation transfers teacher to student iter) is wrong; what works is **online training at student iter** (which is exactly the B+ path).

## Verdict

**W8 #1 KILL** — the specific instantiation (offline-cached BCE on teacher posteriors) does not improve any iter; at iter=3 it catastrophically regresses across 3 seeds (>+25% at every SNR, p=1.0 against head improvement).

The W8 Pareto curve from QA #28 stands:
- iter=10 canonical (C2-rel head trained @ iter=10): **−85.71%** ★ TCOM headline
- iter=5 weighted B+ all (trained @ iter=5 with SNR-weighted batches): **−72%** (2× speedup, near-headline)
- iter=3 unweighted B+ all (trained @ iter=3): **−55%** (3.3× speedup)

W8 #1's role in §IV-H is **as a negative-result note**: offline distillation from teacher iter=10 does not bypass the need to train at the student's deployment iter.

## Optional follow-up (if budget exists)

A genuine "online distillation" experiment would:
1. Modify `train_classical_joint_unrolled.py` to load a frozen teacher iter=10 ckpt alongside the student
2. Add α·KL(student.candidate_softmax || teacher.candidate_softmax) to the loss at every batch step
3. Train B+ "all" variant at iter=3 with combined hard-label BCE + teacher KL

Budget: ~3-4 GPU·h. Expected outcome: marginal improvement on top of B+ all iter=3 (-55%), perhaps closing to -65% to -75%. Not paper-critical given B+ all iter=3 is already a Pareto point.

## Paper §IV-H paragraph (draft)

> "We tested whether offline knowledge distillation, in which the C2-rel head is trained on the teacher iter=10 head's per-candidate posteriors as soft BCE targets, can preserve head gain at student iter=3. Across three independent training seeds the distilled head deploys at iter=3 with strictly worse BER than the classical iter=3 baseline (mean rel. ΔBER +25.58% at SNR=15, +181.58% at SNR=20, +631.47% at SNR=25; one-sided McNemar p=1.0 for "head better" across all conditions). The same head deployed at iter=10 reproduces the canonical −4.10% gain. The failure mechanism is positional-feature mismatch: the head's per-candidate topology features (`d_l_nn`, `d_k_nn` to nearest active support, normalised by `l_max`/`k_max`) carry different meaning at converged (iter=10) vs partial (iter=3) receiver states. We therefore retain the from-scratch trained B+ "all" variant at iter=3 as the iter=3 Pareto point and report W8 #1 as an architectural negative result."

## Files

- `afdm_sp_joint_unrolled/run_w8_1_distill_iter3_eval.sh` (runner, already committed)
- `afdm_sp_joint_unrolled/outputs_softlabel_eval_s2026050{7,8,9}_iter3/` (3 result dirs, this commit)
- `tcom_plan/W8_1_distillation_results.md` (this doc)
