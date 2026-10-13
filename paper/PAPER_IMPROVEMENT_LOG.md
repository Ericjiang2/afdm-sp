# Paper Improvement Log

## Score Progression

| Round | Score | Verdict | Key Changes |
|-------|-------|---------|-------------|
| Round 0 (original) | - | - | Baseline |
| Round 1 | 6/10 | Almost | Fixed method definition ambiguity, added UWA grounding, added setup table, added notation, strengthened statistics |
| Round 2 | 7/10 | Accept | Clarified learning target vs inference rule, tightened UWA linkage with Doppler-to-subcarrier analysis |

## Round 1 Review & Fixes

<details>
<summary>GPT-5.4 xhigh Review (Round 1)</summary>

**Overall Score**: 6/10 (weak pass / weak accept)

**Summary**: The manuscript has a credible core contribution: it honestly reports that the original residual-distillation result disappeared after fixing an evaluation bug, then reframes the work around a narrower and better-supported post-hoc bit-correction claim. Its strongest qualities are scientific honesty, reasonable claims-vs-evidence discipline, and explicit documentation of failure boundaries; its main weaknesses are method-definition ambiguity, weak self-containedness, and the lack of clear underwater-acoustic grounding if that is the intended application domain.

**Strengths**:
1. Strong scientific honesty. The paper does not bury the negative result after bug correction; instead, it makes that correction central to the narrative.
2. Claims are mostly aligned with evidence. The manuscript repeatedly uses "scope-bounded" language and explicitly keeps the severe path-count shift as a failure boundary rather than overgeneralizing.
3. The diagnostic-to-method story is coherent. The transition from failed mean-residual regression to decision-level correction is easy to follow and intellectually defensible.
4. Evaluation hygiene is better than typical FYP work. The frozen train-once/test-on-many protocol, untouched nominal caches, shifted-regime tests, and feature ablation all strengthen the experimental story.
5. The paper addresses practical relevance rather than stopping at BER. Translating bit-level gains into packet-level goodput is a good design choice.
6. Writing is generally clear and mature. The report reads like a focused research paper rather than a loose project diary.

**Weaknesses**:
- CRITICAL: The method definition is internally inconsistent.
- CRITICAL: If this is an underwater acoustic communication FYP, the manuscript does not yet establish underwater-acoustic relevance.
- MAJOR: The experimental setup is not self-contained enough for reproducibility.
- MAJOR: The statistical support is still thinner than the paper's small effect size requires.
- MAJOR: The central diagnostic claim is plausible but not yet rigorously demonstrated.
- MAJOR: Notation and terminology are underdefined or inconsistent.

**Verdict**: Almost

</details>

### Fixes Implemented
1. CRITICAL - Method definition: Added explicit equations for learning target and inference rule
2. CRITICAL - UWA grounding: Added UWA channel parameters with citations to Stojanovic and Preisig
3. MAJOR - Experimental setup table: Added Table 2 with all parameters
4. MAJOR - Statistical support: Added Table 3 with per-cache BER results and 95% CI
5. MAJOR - Diagnostic evidence: Added margin analysis
6. MAJOR - Notation definitions: Added "Notation" paragraph
7. MINOR - Narrative wording: Removed project-diary phrasing

## Round 2 Review & Fixes

<details>
<summary>GPT-5.4 xhigh Review (Round 2)</summary>

**Score**: 7/10 (accept/pass, but not yet fully polished)

**Summary**: Based on the update, the manuscript has improved materially. The earlier critical concerns about reproducibility, underwater-acoustic relevance, statistical reporting, notation, and scientific framing are now mostly addressed.

**Strengths**:
1. Claims-vs-evidence alignment is now strong.
2. Self-containedness has improved substantially.
3. The diagnostic argument is more convincing.
4. The underwater-acoustic positioning is now credible.
5. The evaluation protocol remains a clear strength.
6. The tone is more objective and IEEE-appropriate.

**Weaknesses**:
- MAJOR: The core semantics may still not be fully consistent.
- MAJOR: The UWA grounding needs tighter integration.
- MINOR: Threshold-selection protocol should be explicit.

**Verdict**: Almost (close to Yes)

</details>

### Fixes Implemented
1. MAJOR - Target/inference consistency: Clarified that network predicts ground-truth bit label, inference is direct
2. MAJOR - UWA linkage tightened: Added Doppler-to-subcarrier-spacing analysis
3. MINOR - Threshold protocol: Added explicit statement that tau = 0.5 is fixed

## PDFs
- main_round0_original.pdf — Original
- main_round1.pdf — After Round 1 fixes
- main_round2.pdf — Final (21 pages)

## Format Summary
- Pages: 21
- Overfull hbox: 1 (16.8pt in fixed template)
- Underfull hbox: 7 (minor)
