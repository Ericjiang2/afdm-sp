# Oracle Browser R1 — NARRATIVE_REPORT.md Review

- **Date**: 2026-04-23
- **Reviewer**: gpt-5.4-pro (browser, 35m10s, 12.75k Δ tokens, 5 files attached)
- **Score**: **6 / 10** ("good foundation, but not A-grade with editing yet. Needs more than editing.")
- **Files attached**: NARRATIVE_REPORT.md, paper/CLAUDE.md, NARRATIVE_REPORT_TEMPLATE.md, Instructions on Project reports 22Feb16.pdf, Exemplar Report 1.pdf

## Overall verdict
"Closer to a good conference-paper pitch than to a cautious MSc report plan. Macro-structure mostly compatible with UoG requirements. Current narrative overstates novelty in places, under-proves two core technical claims, and needs a tighter literature rewrite to survive a serious communications reviewer."

## §1 Structural compliance — mostly yes, with caveats

**Current 6-chapter map matches UoG logic** (Intro/LitReview → Methods → Results → Discussion → Conclusions).

**Problem**: Chapters 2 and 3 split like a journal paper ("Theory" + "Proposed Method"). Should be **one Materials & Methods block** with "System Model" + "Receiver Design" sub-sections, matching the exemplar's structure.

**Missing examiner-facing scaffolding**:
- Explicit research-question / objective paragraph at end of Chapter 1
- **Evaluation-protocol subsection**: seeds, bit budget, confidence intervals, paired testing, stopping criteria, train/val/test separation
- **Baseline-selection / fairness subsection**: why these baselines are the right ones
- Results needs **light analytic statements**, not raw data dumping ("Pure data, no interpretation" is too literal for UoG rubric)

**Literature survey ~800 words** too thin for A-grade × 5 Technical Content. Needs more argumentative depth, not checklist.

## §2 Narrative integrity — coherent but 3 logical gaps

Arc is clean enough for B1. Three gaps:

1. **"OMP-once is enough" is asserted, not shown.** BER convergence ≠ support correctness. Need direct **support-stability evidence**: Jaccard overlap between iterations, fraction of atoms changed after iter 1, support precision/recall, how often re-OMP materially changes support.

2. **Learned-head mechanism is inferred, not demonstrated.** Claim says it fixes Dirichlet-leakage atoms — need **support-recovery analysis** showing exactly which atoms the head adds.

3. **Story mixes algorithmic and 4B oversampling contributions.** Best number is driven by oversampling + retraining. Risks looking like "changed physical config and won" rather than "sharper receiver idea."

## §3 Claim defensibility

### Claim 3 (pooled 2B BER reductions)
- Defensible IF always paired with absolute BERs: "20 dB: 3.00e-3 → 1.87e-3, relative reduction 37.7%; 25 dB: 1.40e-3 → 8.35e-4, ~40%".
- McNemar needs paired-bit framing + total error counts / tested bits.

### Claim 4 (5.58e-6 at 25 dB, 4B retrained)
**Shakiest in presentation, not result.**
- Frame as "**observed BER over X tested bits**", not universal performance.
- **"Reaches PCSI+MMSE lower bound" is WRONG wording.** PCSI+MMSE is an oracle reference, not info-theoretic/detector-optimal lower bound. "0 errors" is finite-sample censoring. **Correct**: "approaches the oracle PCSI+MMSE reference within the tested bit budget."

### Complexity argument — **least watertight**
- O(PNQ) → O(PN²) transition needs **explicit derivation of Q = O(N)** under UWA assumptions (τ_spread × Δf gives l_max = O(N)). Shown, not implied.
- **"Complexity-optimal" is too strong.** Only shown "complexity preservation relative to classical sparse baseline." Use **"complexity-efficient"** or **"complexity-preserving"**.
- LMMSE as O(N³) only fair for dense direct inversion. Structured/iterative solvers weaken contrast.
- **MAC table internally inconsistent**: classical 18.6M, learned "20M + 0.9M" → not 1.08×. Either 20M already includes head, or overhead > 8%. Fix units.

## §4 Literature gap — needs biggest rewrite

7-category skeleton plausible, but synthesized gap is **too broad and outdated**. Recent AFDM work ALREADY includes:

| Missing paper / area | arXiv / venue | Impact on our claims |
|---|---|---|
| **AFDM + SP** — "Channel Estimation for AFDM With Superimposed Pilots" | arXiv 2404.10232 | SP-AFDM with iterative CE/D already exists |
| **AFDM GI-free iterative CE/detection** — "GI-Free Pilot-Aided Channel Estimation for AFDM" | arXiv 2404.01088 | Iterative interference cancellation already published |
| **AFDM joint CE+SD** | ScienceDirect S187449072400315X (Phys. Comm. 2025) | Weakens "learning is detection-only" framing |
| **AFDM + oversampled joint CE/DD** | arXiv 2410.05088 | **Directly threatens Claim 4** — oversampling already covered |
| **AFDM + UWA / MSML + AFDM-OMP** | arXiv 2405.02660 | UWA AFDM with OMP already published |
| **AFDM + fractional-Doppler CE** — diagonal reconstruction, attention-based | arXiv 2206.12822 | Direct competitor for leakage-atom story |

**Defensible narrowed gap** (rewrite to exactly this):
> "To our knowledge, no prior AFDM work studies a UWA-style sparse fractional-Doppler SP receiver that (i) uses OMP only once, (ii) performs joint LS/MP refinement iteratively, and (iii) adds a very small learned module only for support refinement while preserving the sparse-baseline complexity class."

## §5 Known weaknesses

**Missing (must add)**:
- **Physics realism for UWA** — fractional-Doppler sparse DD vs full Doppler time-scaling / MSML
- **No comparison to recent AFDM SP / GI-free / joint CE-DD baselines** (internal baselines alone insufficient)
- **Confounded retraining ablation** (15k vs 27k changes BOTH data size AND SNR coverage)
- **Complexity only MACs** — no runtime / memory / latency
- **No robustness sweeps** over ρ, v, τ, P, modulation

**Not a weakness (defend it)**:
- "Learning only helps for SNR ≥ 15 dB" — this IS the design mechanism (high SNR = support-selection limited regime). Don't apologize.

**Scope limitations (mention, don't inflate)**:
- Single antenna (1T1R)
- QPSK only

**Genuine concessions**:
- Post-hoc force_topk bias patch
- Lack of ρ sweep
- 4B hardware cost
- Limited realism / generalisation evidence

## §6 Figure budget — reallocate

- Total (8 in-text + 3 tables) is fine, << 30 cap
- **Drop**: complexity bar chart (redundant with T3)
- **Drop or move to appendix**: NMSE waterfall (optional)
- **Add mechanism figure** (one of):
  - Support-recovery ablation
  - "Atoms added vs true missed atoms"
  - Support precision/recall vs SNR

## §7 Writing order

- Method → Results → Discussion → Intro: **OK**
- **Theory at position 4 is TOO LATE** — risks back-fitting math to code
- **Fix**: write short Chapter 2 skeleton FIRST (notation, signal model, SP model, dictionary, assumptions), then Chapter 3 methods
- Abstract last: absolutely yes

## Top 3 Blocking Issues

1. **Novelty/literature framing too broad and partially outdated** — narrow to SP-AFDM + OMP-once + sub-dominant learned refinement gap
2. **Two central claims under-proven**: direct "OMP-once is enough" evidence + finite-sample CI for 5.58e-6 + consistent complexity accounting
3. **Best-result confounded**: oversampling + retraining + SNR coverage all move simultaneously. Need tighter ablations + ≥1 external AFDM baseline

## Path to A-grade

Fix top 3 → B1 realistic, A-range plausible.
