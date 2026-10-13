# Narrative Report

**Project**: AFDM Joint Receiver Diagnostics and Frozen Decision-Level Correction
**Venue Target**: IEEE Journal
**Date**: 2026-03-31

## One-Sentence Contribution

We show that, in the current AFDM joint-receiver setting, oracle-beneficial improvements arise from sparse decision-boundary crossings rather than smooth mean-level residual correction, and we convert that diagnostic finding into a frozen train-once/test-on-many bit-level corrector that yields reproducible BER gains, survives three regime shifts, improves packet-level utility, and exposes an explicit failure boundary under harsh structural shift.

## Paper Positioning

This paper is not a claim about a new receiver architecture.
It is also not merely a negative-results paper.
The right framing is a diagnostic-plus-method paper:

1. The original detector-side residual-distillation story fails under corrected evaluation.
2. The failure is informative: mean residual changes do not move enough hard decisions.
3. A simpler decision-level intervention, trained once and frozen, works reproducibly.
4. The gains are small in BER but operationally meaningful at packet and goodput level.
5. The method has an explicit scope boundary under a harsher path-count shift.

## Problem Setting

We study AFDM joint channel-estimation-and-detection receivers under underwater-style doubly selective channels.
The starting point is a learned joint receiver (`CurrentJoint`) together with a classical iterative baseline (`JointOMPMP`) and several intermediate learned or calibrated detector-side variants.
The original research goal was to exploit detector-side oracle headroom through learned residual correction.
That goal eventually failed, but the failure mechanism led to a better method design.

## Final Story Arc

### Stage A: The original positive story collapsed

After the pilot-format evaluation bug was corrected, `CurrentJoint`, `vx_recal_v1`, and cleaned `distill_pure_iter0` showed essentially no meaningful BER separation on the same test protocol.
This invalidated the original headline claim that detector-side mean-residual distillation improves BER in the corrected AFDM evaluation.

### Stage B: The failure mechanism was identified

Decision-oracle analysis showed that:

- teacher disagreement exists but is sparse,
- oracle-beneficial flips exist,
- some low-confidence decisions are recoverable,
- but learned mean-level residuals do not move enough hard decisions.

This pointed away from smooth residual regression and toward explicit decision-level correction.

### Stage C: Simple gating was not enough

Two observable baselines were tested:

- linear confidence-style flip gating,
- split-specific direct bit-level correction.

The first was too weak.
The second gave consistent gains and established that the decision-level route was viable.

### Stage D: The frozen corrector became the final method

A lightweight MLP corrector was trained once on one dedicated cache and then frozen.
The input used only observable receiver trajectory features, including final LLR, uncertainty, and trajectory statistics.
This frozen corrector was evaluated on untouched independent caches and regime-shifted caches.

### Stage E: The claim was elevated from BER to endpoint utility

To address the remaining reviewer objection that the BER gain is small, the same frozen predictions were translated into contiguous packet success and an ARQ-style goodput proxy.
This showed that the bit-level gains can amplify into meaningful packet-level utility in the positive regimes.

## Claims and Evidence

### Claim 1

Detector-side mean-residual correction is not decision-effective in the corrected AFDM evaluation.

**Evidence**

- Corrected same-test-set comparison showed no meaningful BER separation between `CurrentJoint`, `vx_recal_v1`, and clean distillation.
- Decision audit showed that the useful headroom is concentrated in sparse bit flips rather than broad mean-level shifts.

### Claim 2

Simple linear confidence-style flip gating is too weak to recover meaningful BER gains.

**Evidence**

- Observable linear flip-gating baselines did not deliver a strong or stable gain.
- Later train-calibrated confidence gating collapsed to threshold `0.5`, effectively reproducing the ungated method.

### Claim 3

A lightweight frozen bit-level corrector using only observable receiver trajectory features yields reproducible BER gains over `CurrentJoint`.

**Evidence**

- Untouched nominal caches:
  - baseline BER mean: `6.3553e-02`
  - corrected BER mean: `6.2493e-02`
  - mean gain: `1.0590e-03`
- Gain standard deviation across the three untouched caches: `5.5328e-05`

### Claim 4

The same frozen corrector transfers across multiple AFDM regime shifts.

**Evidence**

- Higher Doppler severity: mean gain `8.4310e-04`
- Integer-Doppler structural shift: mean gain `1.3249e-03`, `95% CI [1.1621e-03, 1.4958e-03]`
- Lower pilot-power fraction (`rho=0.4`): mean gain `1.6699e-03`
- Positive-regime paired-bootstrap confidence intervals are cleanly above zero

### Claim 5

The method has a clear and honest scope boundary.

**Evidence**

- Severe path-count shift (`P_paths=15`) causes BER regression `-7.9883e-03`
- The paired-bootstrap interval for this regime is cleanly below zero
- Packet-level benefit vanishes or becomes endpoint-dependent under this harsh shift

### Claim 6

The method is not merely an LLR thresholding trick.

**Evidence**

- Feature-group ablation:
  - `full`: `1.1133e-03`
  - `LLR-only`: `2.1267e-04`
- Removing final LLR, `v_x`, `sigma_eff`, or SNR all hurts relative to the full feature set

### Claim 7

Small BER gains can still matter operationally in this setting.

**Evidence**

- `64`-bit packets:
  - nominal relative goodput gain: `+5.22%`
  - Doppler shift: `+4.06%`
  - integer-Doppler shift: `+5.72%`
  - `rho=0.4` shift: `+3.62%`
- `256`-bit packets:
  - nominal: `+10.76%`
  - Doppler shift: `+8.77%`
  - integer-Doppler shift: `+11.33%`
  - `rho=0.4` shift: `+4.97%`
- `256`-bit `P_paths=15`: exactly zero gain

## What We Should Not Claim

1. We should not claim a new major receiver architecture.
2. We should not claim broad generalization outside the current AFDM simulator family.
3. We should not present the work as a pure positive method paper without the diagnostic failure story.
4. We should not hide the `P_paths=15` failure boundary.
5. We should not describe the system-level utility as a coded-stack result; it is an uncoded contiguous-packet ARQ proxy.

## Quantitative Result Summary

### Main BER Summary

| Regime | Baseline BER | Corrected BER | Gain |
|-------|--------------|---------------|------|
| Nominal untouched caches | `6.3553e-02` | `6.2493e-02` | `1.0590e-03` |
| Higher Doppler severity | - | - | `8.4310e-04` |
| Integer-Doppler shift | `3.0672e-02` | `2.9347e-02` | `1.3249e-03` |
| Lower pilot power (`rho=0.4`) | - | - | `1.6699e-03` |
| Severe path-count shift (`P_paths=15`) | - | - | `-7.9883e-03` |

### Bootstrap Confidence Intervals

| Regime | Gain 95% CI |
|-------|-------------|
| Nominal | `[8.4196e-04, 1.2674e-03]` |
| Higher Doppler | `[5.6966e-04, 1.1296e-03]` |
| Integer-Doppler | `[1.1621e-03, 1.4958e-03]` |
| Lower pilot power | `[1.3249e-03, 2.0280e-03]` |
| `P_paths=15` | `[-1.1357e-02, -4.7751e-03]` |

### Packet-Level Utility

| Endpoint | Nominal | Higher Doppler | Integer-Doppler | `rho=0.4` | `P_paths=15` |
|---------|---------|----------------|-----------------|-----------|--------------|
| `64`-bit relative goodput gain | `+5.22%` | `+4.06%` | `+5.72%` | `+3.62%` | no reliable positive effect |
| `256`-bit relative goodput gain | `+10.76%` | `+8.77%` | `+11.33%` | `+4.97%` | `0` gain |

## Proposed Figures

### Figure 1: Hero Figure

An overview figure that combines:

- the base `CurrentJoint` receiver,
- the failed mean-residual route,
- the successful frozen bit-level corrector route,
- the four positive regimes and one failure boundary.

The caption should emphasize that the useful intervention is decision-level, frozen, and scope-bounded.

### Figure 2: Regime-Level BER Gains

A regime comparison figure showing mean BER gain and `95%` confidence intervals across:

- nominal,
- higher Doppler,
- integer-Doppler,
- lower pilot power,
- `P_paths=15`.

### Figure 3: Packet-Level Utility

A grouped bar chart showing relative goodput gain for `64`-bit and `256`-bit packets across all regimes.

### Figure 4: Feature Ablation

A bar chart showing full-feature versus feature-drop and `LLR-only` performance.

### Table 1: Main Method Comparison

Compare:

- `JointOMPMP`
- `CurrentJoint`
- `vx_recal_v1`
- failed distillation line
- frozen direct-bit corrector

The point is not only who wins, but why the narrative changed.

### Table 2: Scope and Claim Matrix

A compact table stating:

- supported claim,
- supporting experiment,
- quantitative evidence,
- explicit limitation.

## Proposed Section Logic

1. Introduction
2. Related Work
3. AFDM Receiver Setting and Diagnostic Motivation
4. Frozen Decision-Level Corrector
5. Experiments
6. Discussion and Limitations
7. Conclusion

This structure is better than a pure "method then experiments" paper because the diagnostic failure is essential to understanding why the final method looks the way it does.

## Related Work Buckets

The related work should be organized into:

1. AFDM modulation and AFDM channel estimation/detection
2. Model-driven or unfolded wireless receivers
3. Reliability-aware or post-detection refinement methods

The paper should position itself as distinct from both:

- direct end-to-end receiver redesign, and
- purely diagnostic failure analysis without a deployable method.

## Reviewer-Aligned Framing

The external review trajectory ended at `7.5/10`.
The reviewer conclusion was that the paper became convincing only after:

1. the failed original claim was honestly narrowed,
2. frozen train-once/test-on-many evaluation was added,
3. multi-regime transfer was demonstrated,
4. failure boundaries were made explicit,
5. bit-level gains were translated into packet/goodput utility.

The paper should reflect that progression directly instead of trying to hide the earlier failed route.

## Suggested Keywords

AFDM, joint receiver, model-driven receiver, decision-level correction, post-hoc correction, regime shift, packet success, goodput, uncertainty features, wireless communications

## Deliverables Needed for Writing

1. `PAPER_PLAN.md`
2. `figures/data/*.json`
3. `figures/*.pdf`
4. `figures/latex_includes.tex`
5. `paper/main.tex` and section files
6. `paper/references.bib`

