# Paper Plan — FYP Dissertation

**Title**: Design and Diagnostic Evaluation of an AFDM Receiver for Underwater Acoustic Communication
**Subtitle (technical)**: From Joint OMP-MP Diagnostics to Frozen Decision-Level Correction
**One-sentence contribution** (plain language): A small frozen post-processor using only signals already observable inside the AFDM receiver gives consistent BER improvements across several tested operating shifts, while clearly failing under severe path-count change.
**Venue**: FYP Dissertation — UESTC / University of Glasgow
**Assessment context**: UESTC / University of Glasgow Final Year Project Marking Rubric
**Type**: Empirical / Diagnostic + Method (technical engineering dissertation)
**Date**: 2026-04-02
**Page budget**: ~60–80 pages / 12,000–13,000 words (main text cap; references counted in total)
**Section count**: 8 chapters + Appendix (Ch. 4 merged into Ch. 5 per reviewer feedback)

---

## Claims-Evidence Matrix

| # | Claim | Evidence | Status | Chapter |
|---|-------|----------|--------|---------|
| C1 | Mean-residual correction is **not** decision-effective under corrected evaluation | After protocol fix: `CurrentJoint`, `vx_recal_v1`, `distill_pure_iter0` indistinguishable; decision audit shows headroom sparse and boundary-local | Fully supported | Ch. 5 |
| C2 | Simple linear confidence-style flip gating is too weak | Linear gating baselines failed; calibrated gate collapsed to threshold `0.5` | Fully supported | Ch. 5 |
| C3 | Frozen corrector delivers **reproducible** BER gains | Nominal: gain `1.0590e-03`, CI `[8.42e-04, 1.27e-03]`; std `5.53e-05` across 3 untouched caches | Fully supported | Ch. 6–7 |
| C4 | Gain **transfers** across 3 regime shifts | Doppler `8.43e-04`, int-Doppler `1.32e-03`, rho=0.4 `1.67e-03`; all CIs above zero | Fully supported | Ch. 7 |
| C5 | Explicit **failure boundary** at `P_paths=15` | Regression `−7.99e-03`, CI `[−1.14e-02, −4.78e-03]`; packet gain = 0 | Fully supported | Ch. 7–8 |
| C6 | Corrector is **not** merely LLR thresholding | Ablation: `LLR-only` = `2.13e-04` vs `full` = `1.11e-03`; removing `v_x`, `sigma_eff`, SNR all hurts | Fully supported | Ch. 7 |
| C7 | Small BER gains translate into useful packet-level improvement **under the chosen uncoded ARQ proxy** | 64-bit nominal `+5.22%`, 256-bit nominal `+10.76%`; consistent in positive regimes | Fully supported (under stated proxy) | Ch. 7 |
| C8 | `TRADPARAM FIXED` is the **strongest traditional representative** | Outperforms `JointOMPMP` at verified SNR points under Python-aligned protocol — verified in Table 1 | Supported (Table 1 required) | Ch. 3 |

**Reviewer note on C7**: claim is valid under the chosen 64/256-bit uncoded contiguous-packet proxy. State this framing explicitly — do not claim it as a full coded communication-stack result.

---

## Structure

### Abstract (250–350 words, strict 4-sentence template)

1. **Problem**: AFDM receivers for underwater-style doubly selective channels must handle delay spread, Doppler, and path uncertainty — traditional pipelines hit a performance ceiling, and detector-side learning is a natural candidate for further improvement.
2. **Failed initial path + correction**: An initial detector-side mean-residual distillation approach appeared promising but proved BER-neutral after an evaluation protocol correction; decision-oracle analysis then identified that the remaining recoverable headroom is sparse and concentrated at decision boundaries rather than in smooth residual shifts.
3. **Final method + key result**: A lightweight frozen direct-bit corrector using 12-dimensional observable receiver trajectory features (train-once, no teacher needed at test time) achieves a nominal BER gain of `1.059e-03` (95% CI `[8.42e-04, 1.27e-03]`) and transfers positively across three tested regime shifts, with 256-bit relative goodput gains up to `+10.76%` under an uncoded contiguous-packet proxy.
4. **Explicit limitation**: The corrector fails under severe path-count shift (`P_paths=15`, BER regression `−7.99e-03`), marking a clear scope boundary that is part of the reported result.

- **Self-contained check**: yes — accessible to an examiner without reading the full report.

---

### Chapter 1 — Introduction and Project Scope (6–8 pages)

- **Opening hook**: Underwater acoustic communication is doubly selective; AFDM structures the channel response through affine-Fourier-domain processing, but receiver design still matters and traditional pipelines have a performance ceiling.
- **Gap**: It is not known which receiver-side intervention survives corrected evaluation when learned improvements are tested under stricter protocols in this doubly-selective AFDM setting.
- **Research questions**:
  1. What is the strongest traditional AFDM joint receiver under the corrected Python-aligned protocol?
  2. Does detector-side mean-residual distillation deliver gains under corrected evaluation?
  3. What is the structure of the recoverable decision headroom?
  4. Can a frozen decision-level corrector provide reproducible gains and transfer across regime shifts?
- **Project aims and contributions** (dissertation framing — 5 items):
  1. *System implementation*: a full AFDM-UWA simulation and evaluation chain in MATLAB and Python.
  2. *Traditional baseline study*: construction and comparison of `JointOMPMP`, `TRADPARAM FIXED`, `TRADPARAM CLASSICAL_FULL`, with `TRADPARAM FIXED` identified as the strongest clean representative.
  3. *Protocol correction*: identification and correction of an evaluation bug that invalidated earlier positive residual-distillation claims.
  4. *Diagnostic negative result*: demonstration that mean-residual correction is not decision-effective in this setting, with mechanistic explanation.
  5. *Final correction method with explicit limits*: a frozen lightweight direct-bit corrector with reproducible gains, positive transfer, and a clearly stated failure boundary.
- **Results preview**: Nominal gain `1.059e-03` (CI `[8.42e-04, 1.27e-03]`); 256-bit goodput `+10.76%`; explicit failure at `P_paths=15`.
- **Chapter roadmap** (1 page, required per reviewer): table/text mapping RQ1–RQ4 to chapters and claims C1–C8.
- **Development timeline figure/table**: one short table showing Phase 1 (MATLAB midterm), Phase 2 (Python/corrected evaluation), and current stage.
- **Hero figure**: Fig. 1 (see Figure Plan).
- **Estimated length**: 6–8 pages
- **Key citations [VERIFY]**: AFDM (Bemani et al.), UWA channel model, OMP sparse recovery, message-passing detection, underwater acoustic waveform design.

---

### Chapter 2 — Background and System Model (7–8 pages, cap; overflow → Appendix)

- **Subtopics**:
  1. Doubly selective channels and underwater-style model (delay, Doppler, P_paths, fractional Doppler, ρ).
  2. AFDM modulation and receiver chain (DAFT/IDAFT, pilot/data structure, pilot fraction).
  3. Sparse channel estimation: OMP and variants.
  4. Iterative detection: message-passing and refinement principles.
  5. Learned detector-side methods: what "post-hoc correction" means in this receiver context.
- **Notation**: h (channel taps), P_paths, v_mean, v_std, ρ, SNR, LLR, hard decisions, BER, goodput proxy.
- **Problem formulation**: received AFDM frame → joint channel estimation + detection → BER and packet-level utility.
- **Positioning**: project focuses on receiver-side post-hoc correction, not new modulation or new estimation algorithm.
- **Chapter-end signpost**: "having established the system model, Chapter 3 presents the traditional receiver baselines that set the initial performance level and motivate the investigation of learned improvements."
- **Estimated length**: 7–8 pages (cap; overflow to Appendix A)

---

### Chapter 3 — Midterm Traditional AFDM Receiver (8–10 pages)

- **Contents**:
  1. MATLAB simulation chain: encoding, AFDM modulation, UWA channel, receiver.
  2. OMP support locking: one-shot sparse support estimation.
  3. Iterative message-passing refinement and gain update.
  4. Three variants: `JointOMPMP`, `TRADPARAM FIXED`, `TRADPARAM CLASSICAL_FULL` — role, logic, BER comparison (Table 1 — required to close C8).
  5. Why `TRADPARAM FIXED` is the strongest clean representative (interpretable, stable, outperforms `JointOMPMP`).
  6. Performance ceiling: motivation for further exploration.
- **Why MATLAB numbers are not reused directly**: different pipeline; final numerical claims unified under Python-aligned protocol. State this explicitly.
- **Chapter-end signpost**: "the traditional line reaches a performance ceiling. Chapter 4–5 investigates whether detector-side learning can go further — and why the initial attempt had to be corrected."
- **Figures**: Table 1 (traditional receiver comparison — BER at verified SNR points), Fig. 2 (BER vs SNR line chart).
- **Estimated length**: 8–10 pages

---

### Chapter 4 — (MERGED INTO CHAPTER 5)

*Per reviewer recommendation: Ch. 4 "Transition to Python Evaluation" merged into Ch. 5 to improve flow and page control.*

---

### Chapter 5 — Evaluation Protocol Correction and Diagnostic Pivot (10–12 pages)

*(Combines the protocol correction transition + diagnostic failure analysis, previously Ch. 4 + Ch. 5)*

- **Sec. 5.1 Transition to the corrected Python evaluation** (≈3 pages):
  - Why the Python pipeline became authoritative: corrected test-set separation, stricter reproducibility, cache-based regime testing.
  - What changed scientifically: pilot-format / same-test-set handling bug → correction invalidated earlier positive residual-distillation result.
  - Cache-based framework: training cache disjoint from all test caches.
  - Statistical reporting: paired-bootstrap CIs.
- **Sec. 5.2 Why mean-residual correction failed** (≈4 pages):
  - Original positive story collapsed after protocol correction (C1).
  - Decision-oracle analysis: teacher disagreement `5.2051e-02`, oracle-beneficial flip rate `3.1543e-02`.
  - Audit finding: useful headroom is sparse, boundary-local, not captured by smooth mean residuals.
  - Linear confidence-style gating: too weak (C2); calibrated gate collapsed to `0.5`.
- **Sec. 5.3 Design implication** (≈1 page):
  - Corrector must target hard-decision flips, not smooth output shifts.
  - This section bridges directly to Chapter 6.
- **Chapter-end signpost**: "having identified sparse boundary-local headroom as the actionable target, Chapter 6 presents the final method designed to exploit it."
- **Figures**: comparison showing `CurrentJoint` / `vx_recal_v1` / `distill_pure_iter0` convergence after correction; decision audit summary table.
- **Estimated length**: 10–12 pages

---

### Chapter 6 — Final Method: Frozen Decision-Level Corrector (6–8 pages)

- **Contents**:
  1. High-level design: lightweight MLP placed post-hoc on top of the learned backbone. Modest in scope; interpretable in role.
  2. Input features: 12-dimensional observable receiver trajectory features (final LLR, LLR magnitude, initial LLR, initial magnitude, LLR trajectory change, uncertainty statistics, effective noise σ_eff, SNR). Definitions from verified code — do not invent unverified values. Mark any unconfirmed field `[INSERT FROM CODE]`.
  3. Model architecture: 2-hidden-layer MLP (exact dimensions from verified implementation).
  4. Train-once / test-on-many protocol: trained on one dedicated nominal cache, frozen, deployed on untouched nominal and shifted caches.
  5. Why this follows the diagnostic: sparse boundary-local headroom → direct flip prediction; frozen deployment prevents per-split overfitting.
  6. **Complexity and overhead analysis** (required per reviewer): parameter count, approximate inference cost/runtime, memory overhead. Note: training is offline; deployment is frozen.
- **Figures**: architecture schematic.
- **Chapter-end signpost**: "Chapter 7 evaluates this corrector against baselines, across regime shifts, and under feature ablation."
- **Estimated length**: 6–8 pages

---

### Chapter 7 — Experimental Results (12–14 pages)

- **Sec. 7.1 Setup**: AFDM simulator parameters (cite verified config; mark unconfirmed values `[INSERT FROM CODE/LOG]`). Cache construction, regime definitions, baseline list.
- **Sec. 7.2 Traditional baseline comparison**: `JointOMPMP`, `TRADPARAM FIXED`, `CurrentJoint` at representative SNR (Table 1 cross-reference, per-SNR BER plot).
- **Sec. 7.3 Nominal train-once/test-on-many result** (C3): gain `1.0590e-03`, std `5.53e-05`, CI `[8.42e-04, 1.27e-03]`. Per-SNR result plot for `CurrentJoint` vs corrected receiver in nominal regime (required per reviewer).
- **Sec. 7.4 Regime-shift transfer** (C4): Doppler, integer-Doppler, rho=0.4 — all positive with CIs.
- **Sec. 7.5 Failure boundary** (C5): `P_paths=15`, gain `−7.99e-03`, CI `[−1.14e-02, −4.78e-03]`. Per-SNR result in `P_paths=15` regime.
- **Sec. 7.6 Feature ablation** (C6): full vs LLR-only vs drop-one variants.
- **Sec. 7.7 Correction-behavior analysis** (required per reviewer): fraction of bits flipped, fraction helpful, fraction harmful, for nominal and `P_paths=15`. This shows the mechanism directly and is examinable.
- **Sec. 7.8 Packet-level utility** (C7): 64-bit and 256-bit packets, 5 regimes.
- **Rule**: Do not invent simulator parameters. Mark all unconfirmed values `[INSERT FROM CODE/LOG]`.
- **Figures**: Fig. 2 (BER vs SNR — traditional baselines), Fig. 3 (regime BER gain + CI, 5 regimes), Fig. 4 (feature ablation bar), Fig. 5 (packet utility grouped bar), Table 1 (traditional comparison), Table 2 (main method comparison), Table 3 (scope/claim matrix).
- **Estimated length**: 12–14 pages

---

### Chapter 8 — Discussion and Limitations (6–8 pages)

- **Questions answered explicitly**:
  1. Why did mean-residual distillation fail? (recoverable headroom not smooth mean-level)
  2. Why does the frozen corrector work better? (targets sparse boundary-local errors)
  3. Why are gains modest but operationally meaningful? (amplified at packet level)
  4. Why is `P_paths=15` a true failure boundary? (trained under one structural family; correction-behavior analysis shows harmful flips dominate)
  5. What is the engineering value? (simple, frozen, observable features, layers over existing backbone without redesign)
- **Engineering cost context**: inference complexity, deployment realism (offline train, frozen deploy).
- **Limitations stated explicitly**:
  - Scope inside current AFDM simulator family only.
  - `P_paths=15` structural shift breaks the corrector.
  - Packet-level proxy is uncoded contiguous ARQ-style; not a full coded communication-stack result (C7 framing).
  - Small BER effect sizes; not a claim of dramatic architectural improvement.
  - One frozen trained instance — further seed variation not fully characterized.
- **Estimated length**: 6–8 pages

---

### Chapter 9 — Conclusion and Future Work (3–4 pages)

- **Restatement** (not copy-pasted from intro): summarize the project arc and the five contributions in project-report language.
- **Future work (concrete, 5 directions)**:
  1. Robustness to `P_paths` structural shift via support-aware or path-count-conditioned features.
  2. Integration of richer uncertainty-aware or iterative-aware features.
  3. Testing within broader AFDM/UWA simulator families.
  4. Replacing MLP with a lightweight structured classifier.
  5. Pushing decision-level correction earlier into the iterative receiver loop.
- **Estimated length**: 3–4 pages

---

### Appendix

- **A**: Background derivation overflow (AFDM signal model details, if Ch. 2 capped).
- **B**: Full verified feature vector definitions (12 dimensions from code).
- **C**: Additional BER tables / supplementary regime plots.
- **D**: Paired bootstrap CI methodology (brief, with formula and reference).
- **E**: Implementation alignment notes (Python pipeline vs MATLAB stage).

---

## Figure Plan

| ID | Type | Description | Data source | Priority |
|----|------|-------------|-------------|----------|
| Fig. 1 | Dissertation arc / hero | Project map (not a publication splash): baseline receiver → failed residual path → diagnostic evidence → final corrector → positive regimes + P_paths=15 failure. Examiner-readable at first glance. | Manual / schematic | HIGH |
| Fig. 2 | BER vs SNR line | `JointOMPMP` vs `TRADPARAM FIXED` vs `TRADPARAM CLASSICAL_FULL` + `CurrentJoint` under Python protocol. Closes C8. | Verified experiment logs | HIGH |
| Fig. 3 | Forest/bar + CI | Mean BER gain + 95% CI for all 5 regimes. P_paths=15 bar visually below zero. Per-SNR inset optional. | CLAIMS_FROM_RESULTS.md | HIGH |
| Fig. 4 | Horizontal bar | Feature ablation: full, LLR-only, -v_x, -sigma_eff, -SNR. | Ablation logs | HIGH |
| Fig. 5 | Grouped bar | Relative goodput gain, 64-bit and 256-bit packets, 5 regimes. P_paths=15 = 0. | Packet-level results | HIGH |
| Table 1 | Comparison | Traditional receiver family: method, key idea, absolute BER at verified SNR points, notes. Required to close C8. | Verified logs | HIGH |
| Table 2 | Main comparison | `CurrentJoint`, `vx_recal_v1`, `distill_pure_iter0`, frozen corrector. BER gain, CI, transfer summary. Shows before/after correction narrative. | CLAIMS_FROM_RESULTS.md | HIGH |
| Table 3 | Scope/claim matrix | C1–C7: claim, experiment, quantitative evidence, limitation. | NARRATIVE + CLAIMS | MEDIUM |
| Table 4 (NEW) | Complexity/overhead | Corrector param count, inference cost, memory. Shows deployment realism. | Verified code | MEDIUM |
| Fig. 6 (NEW) | Correction-behavior | Fraction of bits flipped / helpful / harmful: nominal vs P_paths=15. Shows mechanism directly. | Correction-behavior analysis logs | HIGH |

**Hero figure (Fig. 1) detail** (dissertation arc, not paper splash):
- Row 1: `AFDM backbone` → [dashed red] `mean-residual distillation` → ✗ "BER-neutral after protocol correction"
- Row 2: `AFDM backbone` → `decision-oracle analysis` → "sparse boundary-local headroom"
- Row 3: `AFDM backbone` → `frozen MLP corrector (12-dim observable features)` → [green] `nominal / Doppler / int-Doppler / ρ=0.4` ✓ → [red] `P_paths=15` ✗
- Development timeline strip at bottom (Phase 1 MATLAB → Phase 2 Python → corrected evaluation → final corrector).
- Caption: "Project arc. The final frozen direct-bit corrector is post-hoc, train-once, and scope-bounded. The mean-residual path (top) proved BER-neutral after evaluation correction. The corrector (bottom) targets sparse decision-boundary errors and transfers across three regime shifts with a clear failure at P_paths=15."

---

## Citation Plan

- **Ch. 1 Introduction**: AFDM (Bemani et al. [VERIFY]), UWA channel model [VERIFY], OMP (Tropp & Gilbert [VERIFY]), message-passing detection [VERIFY], UWA waveform design [VERIFY].
- **Ch. 2 Background**: Doubly dispersive channels [VERIFY], DAFT/IDAFT [VERIFY], belief-propagation detection [VERIFY], model-driven / learned receivers [VERIFY].
- **Ch. 3 Traditional Receiver**: OMP [VERIFY], iterative gain refinement [VERIFY], AFDM structure [VERIFY].
- **Ch. 5 Diagnostic**: Decision oracle / bit-flip analysis [VERIFY], neural calibration / uncertainty [VERIFY].
- **Ch. 6 Method**: MLP post-processing [VERIFY], post-hoc correction in deep learning [VERIFY].
- **Ch. 7 Results**: Paired bootstrap CI (Efron [VERIFY]), ARQ/goodput proxy metric [VERIFY].

**Rule**: All BibTeX verified before inclusion. Never generated from memory. Unverified refs marked `[VERIFY]`.

---

## Reviewer Feedback Summary (GPT-5.4 xhigh, 2026-04-02)

**Scores**: Flow 8/10 | Claim-evidence 8/10 | Missing analysis 6/10 | Dissertation positioning 7/10 | Page budget 7/10 | Front-matter strength 7/10

**Applied fixes**:
- [x] Merged Ch. 4 into Ch. 5 ("Evaluation Protocol Correction and Diagnostic Pivot")
- [x] Tightened C7 to explicitly state "under the chosen uncoded ARQ proxy"
- [x] Added `Table 4` (complexity/overhead analysis) as new required output
- [x] Added `Fig. 6` (correction-behavior analysis: flip fraction helpful/harmful, nominal vs P_paths=15)
- [x] Retitled to dissertation engineering framing
- [x] One-sentence contribution rewritten in plain language
- [x] Abstract restructured as strict 4-sentence template
- [x] Added chapter-end signposts to all chapters
- [x] Added development timeline figure/table to Ch. 1
- [x] Added chapter roadmap (RQ→chapter→claim map) to Ch. 1
- [x] Capped Ch. 2 at 7–8 pages; overflow to Appendix A

**Remaining soft spots**:
- C8 can only be fully closed once Table 1 is populated with verified absolute BER values.
- Per-SNR result plots for nominal and P_paths=15 should be generated (Sec. 7.3 / 7.5).
- Correction-behavior analysis (Sec. 7.7, Fig. 6) needs to be extracted from existing logs or run as a lightweight post-hoc analysis.

---

## Next Steps

- [ ] Cross-review complete ✓
- [ ] Extract correction-behavior statistics (flip fraction helpful/harmful) from existing logs for Fig. 6 / Sec. 7.7
- [ ] Populate Table 1 with verified absolute BER values for C8
- [ ] `/paper-figure` — generate Fig. 1–6 and Table 1–4
- [ ] `/paper-write` — draft LaTeX chapter by chapter (dissertation template)
- [ ] `/paper-compile` — build PDF
- [ ] Verify all BibTeX entries before final submission
