# Paper Plan

**Title**: When Mean-Residual Distillation Fails: Frozen Decision-Level Correction for AFDM Joint Receivers
**Venue**: IEEE_JOURNAL
**Type**: empirical diagnostic-plus-method paper
**Date**: 2026-03-31
**Page budget**: target `12-14` total pages including references
**Section count**: 7 main sections plus optional appendix

## Claims-Evidence Matrix

| Claim | Evidence | Status | Section |
|-------|----------|--------|---------|
| Mean-residual detector correction is not decision-effective in corrected AFDM evaluation | corrected same-test-set comparison; decision audit | Supported | Sec. III, Sec. V-B |
| Linear confidence gating is too weak | observable gating baselines; train-calibrated confidence threshold collapses to `0.5` | Supported | Sec. V-B |
| Frozen observable bit-level correction gives reproducible BER gains | untouched independent caches; nominal mean gain `1.0590e-03` | Supported | Sec. IV, Sec. V-C |
| The gain transfers across meaningful regime shifts | Doppler, integer-Doppler, `rho=0.4` results with positive CIs | Supported | Sec. V-D |
| The method has an explicit failure boundary | `P_paths=15` BER regression and negative CI | Supported | Sec. V-D, Sec. VI |
| The method is not just LLR thresholding | feature-group ablation; `LLR-only` much weaker | Supported | Sec. V-E |
| Small BER gains can become meaningful packet/goodput gains | `64`-bit and `256`-bit packet endpoint analysis | Supported | Sec. V-F |

## Structure

### Sec. I: Introduction

- **Opening hook**: AFDM receivers can have nontrivial oracle headroom even after strong iterative processing, but exploiting that headroom with learned residual corrections is harder than BER curves alone suggest.
- **Gap**: Prior work and our own early attempts implicitly assume that useful improvement is a smooth residual-estimation problem. In the corrected AFDM evaluation, that assumption fails.
- **Approach overview**: We first diagnose why detector-side mean-residual correction fails, then introduce a frozen train-once/test-on-many bit-level corrector that acts on observable receiver trajectory features.
- **Contributions**:
  1. We show that the useful headroom in this AFDM setting is decision-level rather than mean-level.
  2. We design a lightweight frozen direct-bit corrector that yields reproducible BER gains on untouched caches and three regime shifts.
  3. We quantify feature dependence, confidence intervals, and an explicit structural failure boundary.
  4. We translate bit-level gains into packet/goodput utility under contiguous uncoded packet endpoints.
- **Results preview**: mention nominal gain `1.0590e-03`, integer-Doppler gain `1.3249e-03`, `256`-bit nominal goodput gain `10.76%`, and `P_paths=15` failure boundary.
- **Hero figure**: Fig. 1 overview showing failed mean-residual route vs successful frozen decision-level route plus positive and negative regimes.
- **Estimated length**: `1.5` pages
- **Key citations**: original AFDM paper, AFDM channel estimation papers, deep/model-driven receiver papers

### Sec. II: Related Work

- **Subtopics**:
  1. AFDM modulation and AFDM channel estimation/detection
  2. Deep or model-driven wireless receivers
  3. Post-detection refinement and reliability-aware correction
- **Positioning**:
  - Unlike AFDM estimator/detector redesign papers, this paper focuses on post-hoc decision correction on top of a fixed joint receiver.
  - Unlike general deep receiver papers, the paper's main contribution is a diagnostic-to-method transition rather than a larger learned architecture.
  - Unlike pure calibration stories, the endpoint is BER and packet/goodput, not calibration alone.
- **Minimum length**: at least `1` full page

### Sec. III: AFDM Receiver Setting and Diagnostic Motivation

- **Notation**:
  - received AFDM frame, pilot/data partition, detector output LLRs, uncertainty signals, receiver trajectory observables
- **Problem formulation**:
  - given a fixed base receiver, can post-hoc detector-side corrections improve the final hard decisions?
- **Diagnostic story**:
  - corrected evaluation invalidates original distillation claim
  - decision audit reveals sparse oracle-beneficial flips
  - therefore the intervention target should be decision-level
- **Formal object to define**:
  - observable feature vector for the corrector
  - regime-shift evaluation protocol
- **Estimated length**: `1.5-2` pages

### Sec. IV: Frozen Decision-Level Corrector

- **Method description**:
  - small MLP
  - train once on a dedicated cache
  - freeze and deploy on untouched test caches
  - inputs restricted to observable receiver trajectory features
  - no teacher trajectories at test time
- **Why this design follows the diagnosis**:
  - target is final bit correction, not mean residual
  - frozen evaluation prevents per-split overfitting
  - observables retain deployment realism inside the current simulator family
- **Implementation details**:
  - training cache and untouched test-cache protocol
  - feature groups
  - no adaptive gating added in the final method
- **Estimated length**: `1.5` pages

### Sec. V: Experiments and Main Results

- **Sec. V-A Setup**:
  - AFDM system
  - compared methods
  - seeds/caches
  - metrics: BER gain, paired bootstrap CI, packet success, relative goodput
- **Sec. V-B From failed residuals to decision-level correction**:
  - same-test-set corrected comparison
  - decision audit
  - weak linear gating
- **Sec. V-C Nominal train-once/test-on-many evaluation**:
  - frozen corrector nominal result
- **Sec. V-D Regime-shift transfer and failure boundary**:
  - Doppler
  - integer-Doppler
  - pilot-power shift
  - `P_paths=15`
- **Sec. V-E Feature ablation**:
  - full vs feature-drop vs `LLR-only`
- **Sec. V-F System impact**:
  - `64`-bit and `256`-bit packet/goodput gains
- **Estimated length**: `4-5` pages

### Sec. VI: Discussion and Limitations

- **Discussion points**:
  - why mean-residual learning failed
  - why frozen correction is scientifically cleaner than adaptive retuning
  - why positive gains remain modest in BER
- **Limitations**:
  - evidence remains inside current AFDM simulator family
  - endpoint analysis uses uncoded contiguous packets with an ARQ proxy
  - method fails under `P_paths=15`
- **Future work**:
  - out-of-family transfer
  - coded endpoints
  - stronger but still simple frozen correctors
- **Estimated length**: `1` page

### Sec. VII: Conclusion

- **Restatement**:
  - the key issue is not lack of oracle headroom but mismatch between residual-level learning and decision-level utility
- **Takeaway**:
  - frozen decision-level correction is a better abstraction for this AFDM setting
- **Estimated length**: `0.5` pages

## Figure Plan

| ID | Type | Description | Data Source | Priority |
|----|------|-------------|-------------|----------|
| Fig. 1 | Hero illustration | Base receiver, failed mean-residual path, frozen corrector path, positive regimes, failure boundary | `figures/data/hero_figure_spec.json` + Gemini illustration | HIGH |
| Fig. 2 | Error-bar bar chart | BER gain by regime with `95%` CI, including negative `P_paths=15` bar | `figures/data/regime_gain_summary.json` | HIGH |
| Fig. 3 | Grouped bar chart | Relative goodput gain for `64`-bit and `256`-bit packets across regimes | `figures/data/system_impact_summary.json` | HIGH |
| Fig. 4 | Bar chart | Feature-group ablation with `full`, `LLR-only`, and drop-one variants | `figures/data/feature_ablation_summary.json` | MEDIUM |
| Table I | LaTeX table | Method evolution and headline results from failed residual route to frozen corrector | `figures/data/method_comparison_summary.json` | HIGH |
| Table II | LaTeX table | Claim-scope matrix with supported claims, positive regimes, and failure boundary | `figures/data/claim_scope_matrix.json` | MEDIUM |

### Detailed Hero Figure Specification

- **Left group**: `CurrentJoint` base receiver with AFDM frame input and iterative trajectory outputs.
- **Top middle red path**: failed residual-distillation route labeled "mean-residual correction" with a note "does not move enough hard decisions".
- **Bottom middle green path**: frozen direct-bit corrector route labeled "observable decision-level correction".
- **Right side**: two grouped boxes:
  - positive regimes: nominal, higher Doppler, integer-Doppler, lower pilot power
  - failure boundary: severe path-count shift (`P_paths=15`)
- **Bottom strip**: packet-level utility summary for `64` and `256` bits.
- **Caption draft**: "In the corrected AFDM evaluation, useful headroom is concentrated in sparse decision-boundary crossings rather than smooth mean-level residual shifts. This motivates a frozen observable bit-level corrector, which improves BER across untouched and shifted regimes while retaining an explicit failure boundary under severe path-count shift."

## Citation Plan

- **Sec. I Intro**:
  - AFDM introduction/original modulation paper
  - one AFDM channel-estimation paper
  - one model-driven wireless receiver paper
- **Sec. II Related Work**:
  - AFDM modulation and AFDM channel estimation papers
  - deep MIMO detection
  - model-driven deep receiver / turbo receiver
- **Sec. III-IV Method and setup**:
  - only baseline or architectural citations if directly needed
- **Sec. V Experiments**:
  - mostly self-contained; cite baseline families where referenced

## Reviewer Feedback to Reflect

- The paper became convincing only after the original overclaim was narrowed.
- Main-text claims must match the evidence exactly.
- The failure boundary is a strength, not something to hide.
- Packet-level significance is the last piece that made the story honest.

## Next Steps

- [ ] Create `figures/data/*.json` from the validated result summary
- [ ] Generate Fig. 2-4 and Table I-II with `/paper-figure` logic
- [ ] Generate Fig. 1 via Gemini-based illustration workflow
- [ ] Draft LaTeX under `paper/`
- [ ] Build PDF with IEEE journal template
