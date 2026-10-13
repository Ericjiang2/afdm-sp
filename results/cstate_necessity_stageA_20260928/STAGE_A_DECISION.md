# Stage A decision — developmental, 2026-09-28

**Overall: U for the stronger claim that global model-space reopening remains necessary after F1.** This does not erase the clear measured benefit of the complete CSTATE continuation. F1 alone did not replace economical F0+TF+CSTATE on this population. F1+TF+CSTATE reached 0/1024 errors, but matched LOCAL already rescued 11 of the 12 F1 failures. The one remaining D-over-LOCAL discordant frame is `s650_f0113`; this is insufficient to establish the broader global-reopening mechanism claim.

This adjudicates the already studied, fixed 6.5-dB 1024-observation population. It is **not fresh confirmation**, universal necessity, or evidence of zero population FER. No F2, new observation, parameter change, or additional receiver run was made after the registered campaign.

## What the frozen tests say

| Question | Saved result | Interpretation |
|---|---|---|
| Does stronger acquisition improve F0? | A→C: 40→12 errors; 30 rescues, 2 harms; conservative upper bound on FER_C−FER_A = −1.281 pp | Yes, in this developmental population. |
| Does F1 absorb the historical rescue set? | 26/34 original B-only rescues decoded by C | The frozen ≥26 threshold passes; this is outcome absorption, not causal attribution to grouping loss. |
| Can F1 alone substitute for F0+CSTATE? | C vs B: 12 vs 6 errors; mean 0.6675 vs 0.3625 s; p95 0.7362 vs 0.4361 s | No observed risk-cost domination by C. C's excess-FER upper bound is 1.682 pp, above the frozen 1 pp margin. |
| Does the complete CSTATE branch still help after F1? | C→D: 12→0 errors, 12 rescues/0 harms; upper bound FER_D−FER_C = −0.2474 pp; exact paired p = 0.0004883 | The frozen incremental-effect criterion passes. This is evidence about the whole continuation, including its extra refinement/TF/decoder round. |
| Is that effect beyond matched LOCAL? | On all 12 C triggers: D correct 12, LOCAL correct 11; 1 discordance; exact p = 1 | Insufficient evidence for a general advantage of global reopening over continuation alone. No equivalence claim either. |
| Are tight deadlines interchangeable with final FER? | At 0.5 s: B 994 correct/0 missing; C 307/599; D 382/516, each denominator 1024 | No. F1's front-end cost substantially changes this deadline operating point. D's eventual zero errors becomes 1 error at 1 s. |

Bounds use the preregistered conservative Clopper–Pearson component construction, not a normal approximation; `pp` means percentage points. All six paired tables and both deadline tables are in [the frozen primary report](analysis/report.json) and [results](STAGE_A_RESULTS.md).

## K / S / C / E / U

- **K not established:** only rescue absorption passes; the excess-risk, residual-gain, mean-cost and p95-cost requirements fail. Failure to prove K is not proof of universal CSTATE necessity.
- **S not established as “D approximately C”:** the registered D−C incremental-effect test is positive. A compact rescue role for the economical F0 architecture remains supported as a scoped engineering description.
- **C only partially supported:** stronger acquisition and complete-branch incremental gain are supported; superiority beyond matched LOCAL is unresolved. Therefore do not promote “global complementarity survives” as a complete mechanism finding.
- **E has a descriptive cost pattern, not a completed formal category:** C costs 1.841× B in complete mean and 1.688× in p95, while its observed FER is higher. Communication comparability within the frozen 1 pp bound was not established. No post-hoc definition of “comparable” or “material” is introduced.
- **U is the final categorical disposition:** uncertainty concerns the stronger global-reopening claim and performance comparability, not an inability to measure the four arms.

## F2 and next evidence

F2 is **not required or justified for implementation by this result alone**. F1 recovered a majority of original rescues (26/34), so the frozen failed-majority plus identified early-information-gap route does not apply. The earlier acquisition-lineage audit remains A4; no specific capability absent from F1 and supplied by F2 was established here. This does not demonstrate that F2 could not improve performance.

A separately authorized fresh campaign is scientifically justified only to confirm the surviving **risk-cost comparison**, with the full CSTATE branch and matched LOCAL distinguished explicitly. The present result does not select a new front-end policy or authorize that campaign. Freeze policy, margins, comparison count and budget separately before any fresh observations. Do not modify CSTATE to preserve its narrative.

## Reviewer path and boundaries

Question → [frozen hypotheses and margins](../cstate_necessity_audit_20260925/STAGE_A_PREREGISTRATION.md) → [registered arms and clocks](ARM_DEFINITIONS.md) → [implementation qualification](IMPLEMENTATION_RECEIPT.md) → [observed seal](observed/observed_seal.json) → [Git-before-truth attestation](OBSERVED_GIT_ATTESTATION.json) → [frame outcomes](analysis/frame_outcomes.csv) / [costs](analysis/component_timing.csv) → [independent recount](independent/recount.json) / [coverage and comparison](independent/COMPARISON.json) → [provenance](PROVENANCE.json).

Physical capture is not inferred from outcome absorption. The [saved-geometry addendum](analysis/structural_addendum.json) finds the historical target delay already present in F1 for51/64 edits, increasing to55/64 after D's branch; these are edit counts across34 rescued frames, not causal percentages. There was no frozen Doppler-distance threshold for “captured”; delay presence, multiplicity and nearest Doppler distance remain descriptive. Same-delay multiplicity also retains the already documented scalar-reaction approximation limitation; F1 is the frozen hostile comparator, not a new exact Bayesian receiver. No historical timing was substituted into these comparisons.
