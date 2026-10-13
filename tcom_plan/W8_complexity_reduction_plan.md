# W8 Complexity Reduction — 4-Direction Exploration Plan

**Created**: 2026-05-11
**Status**: #1 ACTIVE NEXT — #2/#3/#4 PARKED (revisit after #1 lands)
**Motivation**: TCOM headline iter=10 vanilla -85.71% (QA #22/#26, 3-seed pooled, p=4.2e-29) accuracy is paper-grade, but 10 outer iters per frame is computationally heavy. User question: can we reach same-or-better BER with fewer iters via end-to-end learning ideas?

---

## Direction priority (ranked feasibility vs reviewer-risk)

| # | Direction | Where in pipeline | Reviewer risk | GPU·h | Status |
|---|-----------|-------------------|---------------|-------|--------|
| 1 | **Iter=10 → iter=3 distillation** | head + iter-train loss | Low — pure post-training trick | ~4-6 | ACTIVE NEXT |
| 2 | Early-exit per-frame gate | new 1-2 param classifier per outer iter | Low — keeps worst-case ≤10 | ~3-5 | PARKED |
| 3 | Learnable c1/c2 lite (channel-statistics-aware) | DAFT chirp params via tiny MLP | Medium — extends Bemani §III-C | ~6-10 | PARKED |
| 4 | Full learnable DAFT/IDAFT (user's original idea) | learnable unitary replacing chirp | High — "you broke AFDM" attack | ~15-25 | PARKED |

**Sequencing rule**: do #1 first. If #1 delivers iter=3 ≥ iter=10 BER → §IV-H is done, #2/#3/#4 become R1 reserve. If #1 stalls (e.g., iter=3 floor still 2× iter=10) → #2 early-exit is the natural fallback (no architecture change, just avg-iter reduction).

---

## Direction #1 — Knowledge distillation iter=10 → iter=3 [ACTIVE]

### Goal

Train a student receiver with `n_outer_iter=3` (or 5) that matches teacher iter=10 BER, achieving 3.3× (or 2×) inference cost reduction without architectural change.

### Why this is the right first cut

- **Zero architecture risk**: identical model class, identical AFDM frame, only changes training loss. Reviewers cannot attack "you changed the system".
- **Cheap to falsify**: 4-6 GPU·h, single seed first; if iter=3 student stays at +20% BER vs teacher → kill it fast.
- **Existing infrastructure 95% reusable**: teacher checkpoint already trained (canonical iter=10 ckpts in `outputs_canonical_grid_s2026050{7,8,9}/`); paired_learned_eval already supports `--n-outer-iter` (QA #22 H ablation flag).

### Mechanism (why distillation might work here)

Teacher iter=10 vanilla has n10/n01 = 126/0 wrong-flips: head is precision-bounded by classical convergence at iter=10. At iter=3, classical residual is 5-10× larger (~711 errs at iter=5 vs ~49 at iter=10, QA #26), so head has *less reliable* candidate ranking signal. Distillation transfers teacher's *final-iter posterior* into the student's iter-3 prediction loss, giving student access to teacher's confidence on candidates that student couldn't justify from raw iter-3 signal alone.

This is NOT a "more iters = strictly more info" trade-off — empirically iter=3 classical has *high recall but low precision*; the candidate set covers the right atoms, but ranking them needs teacher supervision.

### Concrete file plan

1. **`afdm_sp_joint_unrolled/distill_iter_student.py`** (NEW, ~250 lines)
   - Load teacher: canonical iter=10 ckpt (e.g., `outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk`)
   - Build student: same `CandidateActiveRelationHead` class + same backbone, but the receiver's outer loop will stop at `student_iter` (default 3) at training time
   - **Loss**:
     - L_hard = BCE(student.candidate_logits at iter=N_student, ground_truth_active_indicator) — existing C2-rel BCE
     - L_distill = KL(student.candidate_softmax || teacher.candidate_softmax) — teacher's softmax over candidates at its iter=10, student matches at its iter=3
     - L_total = α · L_hard + (1−α) · L_distill, α=0.3 default (distillation-heavy, since hard labels noisy at iter=3 residual)
   - Reuse existing cache pipeline `loop9_train_c2rel.py` `--feature-mask` extraction path
   - Per-batch: forward teacher (eval mode, no grad) + forward student (train mode) → compute loss → optimizer step on student-only params
   - Save `outputs_distill_iter3_from_iter10/{ckpt_distilled.pt, train_log.json}`

2. **`afdm_sp_joint_unrolled/paired_learned_eval.py`** (~10 lines)
   - No new CLI flag needed — student ckpt is loaded via existing `--ckpt`, and student's iter count is set via existing `--n-outer-iter 3`
   - Add `_config['distillation_teacher']` to results.json metadata when teacher path is in ckpt's saved metadata (optional, for traceability)

3. **`afdm_sp_joint_unrolled/run_distill_iter3.sh`** (NEW)
   - Mirror `run_3seed_pool_iter5_iter10.sh` structure for the 3-seed × distillation A/B comparison

4. **`afdm_sp_joint_unrolled/tests/test_distill_smoke.py`** (NEW, ~50 lines)
   - 1-epoch smoke: assert (a) student ckpt loads in paired_learned_eval, (b) BCE loss strictly decreases on first 100 batches, (c) distillation KL loss strictly decreases, (d) student's final-iter candidate softmax KL to teacher < initial KL by ≥0.1

### Acceptance gates

| ID | Test | Pass criterion | Decision |
|---|------|----------------|----------|
| D0 | Smoke `test_distill_smoke.py` | losses decrease, ckpt round-trips | Required before D1 |
| D1 | Eval student iter=3 vs teacher iter=10 (200f × 3 SNR × seed 20260507) | student iter=3 BER ≤ 1.2× teacher iter=10 BER at SNR=20 | If yes → D2; if no → diagnose (loss weight, KL temperature, more student capacity, or kill) |
| D2 | Paired eval student iter=3 vs classical iter=3 baseline | student strictly beats classical iter=3 by McNemar p<0.05 + relative gain ≥ -50% at SNR=20 | Confirms distillation is the dominant driver, not just iter=3 baseline lift |
| D3 | 3-seed pool (s2026050{7,8,9}, 200f × 3 SNR) | pooled student iter=3 BER within ±20% of pooled teacher iter=10 BER | Paper-grade evidence; promotes to §IV-H |
| D4 | Complexity check: wall-time student iter=3 ≈ 3.3× faster than teacher iter=10 | Measure on shared 4090, log to `outputs_distill_iter3_from_iter10/runtime.json` | Required for §IV-H complexity claim |

### Budget

| Step | Frames / epochs | GPU·h |
|------|----------------|-------|
| D0 smoke (1 epoch × 100 frames) | 100 | 0.2 |
| D1 single-seed eval | 600 frames | 0.3 |
| Training (teacher iter=10 frozen, student iter=3, 27k cache, ~30 epochs) | 27k × 30 epochs | 3-4 |
| D3 3-seed pool eval | 600 × 3 = 1800 frames | 1.0 |
| **Total #1** | | **~4.5-5.5 GPU·h** |

### Production command (after D2 passes)

```bash
# Train distilled student (single seed first, then expand)
python afdm_sp_joint_unrolled/distill_iter_student.py \
    --teacher-ckpt afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk \
    --teacher-iter 10 --student-iter 3 \
    --cache-dir afdm_sp_joint_unrolled/cache_canonical_s20260507/ \
    --alpha 0.3 --kl-temperature 2.0 \
    --epochs 30 --lr 1e-4 --batch-size 64 \
    --out afdm_sp_joint_unrolled/outputs_distill_iter3_from_iter10_s20260507

# Eval (existing pipeline)
python afdm_sp_joint_unrolled/paired_learned_eval.py \
    --ckpt afdm_sp_joint_unrolled/outputs_distill_iter3_from_iter10_s20260507/ckpt_distilled.pt.force_topk \
    --variant C2-rel --mp-mode bp --pic-damp 0.5 --p-paths 8 \
    --tau-spread 0.010 --n-total 1024 --v-mean 2.0 \
    --snr-list 15 20 25 --frames-per-snr 200 \
    --fs-factor 4.0 --seed 20260423 --cdtype complex64 \
    --n-outer-iter 3 \
    --out afdm_sp_joint_unrolled/outputs_distill_iter3_eval
```

### Risks

- **R1**: Teacher's iter=10 candidate softmax is near-one-hot (n01=0 = teacher is "certain"). KL with α=0 may collapse student to teacher's argmax with no signal on confidence shape. **Mitigation**: temperature softening (T=2 or 4) on teacher softmax before KL.
- **R2**: At iter=3 the candidate pool may not even contain teacher's chosen atoms (different cluster-expand state). KL between disjoint supports is undefined. **Mitigation**: zero-padding on the union of student/teacher candidate sets, then renormalize; if union too sparse, fall back to BCE on hard labels only and report negative D1 result honestly.
- **R3**: Teacher iter=10 was trained at iter=10 from scratch — distilling a forward-cropped variant may simply not have enough representational capacity at iter=3 (architectural floor). **Mitigation**: if D1 fails, try `student_iter=5` instead of 3 before killing — 5 → 2× speedup is still useful paper material.

---

## Direction #2 — Early-exit per-frame gate [PARKED]

### Concept

Most frames at iter=3 already have converged classical residual (single-path channel, high SNR, clean QPSK). Only a minority (low SNR + multi-path + cluster-collision) need the full iter=10. Add a tiny gate (1-2 params) after each outer iter that decides "stop here" or "continue".

### Sketch

- Per outer iter, after head's candidate rerank, compute a confidence statistic (e.g., max-min margin of candidate logits, or normalized residual energy `||r||² / ||y||²`).
- Train a logistic regression on `(margin, residual_norm) → P(further-iter-improves-BER)` from a calibration set of (state-at-iter-i, BER-at-iter-10) pairs.
- At inference, if `P < τ` for the current iter, stop and emit current `x_hat`.

### Expected outcome

- Avg iters drops from 10 → ~4-5 on canonical test set
- Worst-case still iter=10, so no BER regression
- Paper-grade complexity-vs-accuracy curve

### Reviewer attack surface

Low — "we added an early-exit gate" is a textbook complexity-saving trick (DyNet, BERT early-exit lit). Defensible.

### Estimated budget

3-5 GPU·h (calibration set construction + gate training + eval).

### Resume conditions

- After D3 passes for #1 — natural follow-on for §IV-H if iter=3 student still 1.0-1.2× teacher (i.e., #1 helps but doesn't fully close gap).
- Independent of #1 — could be evaluated in parallel by future me.

---

## Direction #3 — Learnable c1/c2 lite (channel-statistics-aware) [PARKED]

### Concept

AFDM's chirp slopes `c1 = (2·k_max+1)/(2N)` and `c2` are picked deterministically from a worst-case Doppler `f_dmax` per Bemani 2023 §III-C. In our UWA channel, channel statistics (v_mean=2 m/s, τ_spread=0.010, p_paths=8) are known a priori. Instead of conservative worst-case c1, c2, learn a tiny `MLP(v_mean, τ_spread, p_paths, SNR) → (c1_offset, c2_offset)` from a calibration set.

### Why "lite" only

The chirp form `e^{j·2π·(c1·n²+c2·m²)}` must stay — that's what guarantees DD-domain sparsity. Only c1/c2 *values* learnable. This keeps AFDM's structural identity intact while removing a 30+ year-old worst-case-design conservatism.

### Sketch

- Build a 3-layer MLP, ~200 params total: input 4-dim (v_mean, τ_spread, p_paths, SNR), output 2-dim (Δc1, Δc2) clipped to ±20% of analytical c1, c2
- Train jointly with existing head: at each batch, set DAFT chirps to `c1_nominal + Δc1` and `c2_nominal + Δc2`, then run forward + BCE loss
- Eval: for each test SNR, the MLP outputs SNR-adaptive c1/c2

### Expected outcome

- iter=10 vanilla BER at SNR=20 → -10% to -30% (head + learnable-c1/c2 stack)
- Or: iter=5 with learnable-c1/c2 → on par with iter=10 vanilla (more attractive for §IV-H)

### Reviewer attack surface

Medium — "you tuned c1/c2 to the channel" is a fair attack. **Defense**: c1/c2 in Bemani's original paper *already* depend on `f_dmax`; we're just making the dependence data-driven instead of analytical worst-case. Cite Bemani 2023 §III-C explicitly in the paper §III sub-paragraph that introduces c1/c2.

### Estimated budget

6-10 GPU·h (calibration grid sweep + joint training + eval).

### Resume conditions

- After #1 and #2 land — if #1 + #2 combined achieve iter=3-4 = teacher iter=10, #3 is unnecessary.
- If #1 fails and #2 only saves 1.5× iters, #3 becomes the next attempt with stronger expected gain.

### Risk

R-3a: Trained c1/c2 may exhibit sharp dependence on `v_mean` (Doppler spread), and at inference v_mean is rarely known exactly. **Mitigation**: train MLP with v_mean noise injection ±20%, eval on off-grid v_mean test.

---

## Direction #4 — Full learnable DAFT/IDAFT (user's original idea) [PARKED, HIGH RISK]

### Concept

Replace the analytical DAFT chirp transform `A_n = Λ_c2 · F · Λ_c1` (Bemani Eq.5) with a learned unitary `A_θ` parameterized by ~1000-5000 params (e.g., a Householder reflection product or a learned phase-only DFT variant). Joint train with channel estimation + detection.

### Why this is HIGH RISK

1. **Theoretical**: AFDM's DD-domain sparsity guarantee in §III (Bemani 2023 Eq.18) hinges on the analytical chirp form. A learned `A_θ` makes this analysis impossible; reviewer will ask "what is the new compressed-sensing RIP?".
2. **System identity**: "AFDM" by definition is "Affine Frequency Division Multiplexing", and the affine part *is* the chirp. Replace it and a senior reviewer says "this is a learned-OFDM variant, retitle the paper".
3. **Compatibility**: the OMP+MP joint receiver — the very thing we benchmark against — relies on `Φ = A_n D(x_pilot) Δ` being structured. Learned `A_θ` breaks this; baseline OMP regresses; the comparison becomes apples-vs-oranges.

### When to consider this

- For a follow-up paper, NOT this TCOM submission. Maybe ICC/Globecom 2027.
- Or as a tiny ablation in §IV-H showing "even full learnable DAFT only saves ~1 more iter beyond #1+#2+#3 — diminishing returns" — and document as a negative result.

### Sketch (for future reference)

- Parameterize A_θ as `A_θ = D_θ1 · F · D_θ2` where D_θi is a learned diagonal phase matrix with ~N free params. Keeps the structure unitary by construction.
- Joint train: end-to-end backprop through A_θ, channel estimation (existing iterative receiver as fixed graph), final BER/BCE loss.
- Baseline OMP receiver must be re-derived for the learned A_θ — paper-equivalent OMP uses analytical Φ structure, so this is non-trivial.

### Estimated budget

15-25 GPU·h (mostly because needs retraining whole pipeline from scratch + baseline rederivation + sanity tests).

### Resume conditions

- After #1+#2+#3 all complete and at-least-one delivers good §IV-H paper material.
- Or: when user explicitly requests a follow-up paper on "learned waveform for AFDM".

---

## Cross-direction notes

- **Combine #1 + #2** is natural: train iter=3 student via distillation, then add early-exit at iter=2 for the easy frames. Combined avg iter ≈ 2.5, worst case 3.
- **Don't combine #3 + #4**: they conflict on c1/c2 — #3 keeps chirp form with learned values, #4 abandons chirp form entirely.
- **§IV-H "Complexity-Accuracy Frontier" paper section**: the natural deliverable from this exploration is a 2D plot of (avg iters, BER) Pareto curve, with points for {iter=3 vanilla, iter=10 vanilla = current headline, iter=3 distilled, iter=3 distilled + early-exit, iter=5 + learnable-c1/c2}.

---

## Decision log

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2026-05-11 | Pick #1 as ACTIVE, park #2/#3/#4 | User confirmed step-wise exploration; #1 has zero architecture risk + cheapest budget + reuses existing infra. |
