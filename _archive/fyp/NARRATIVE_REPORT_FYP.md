# Narrative Report

**Project**: AFDM Receiver Design for Underwater Acoustic Communication: From Joint OMP-MP Diagnostics to Teacher-Margin-Gated Decision Fusion (Round 8)  
**Document Target**: Final Year Project Report / Dissertation-Style Technical Report  
**Assessment Context**: UESTC / University of Glasgow Final Report Marking Rubric  
**Date**: 2026-03-31

---

## 1. Executive Summary

This project studies receiver design for affine frequency division multiplexing (AFDM) under underwater-style doubly selective channels. The work developed in two phases. The midterm phase established a traditional AFDM receiver pipeline (joint OMP support locking with iterative MP refinement, with a superimposed-pilot frame format on both MATLAB and Python and the canonical 10-path UWA channel) based on one-shot sparse support estimation followed by iterative refinement. The later phase moved to a Python evaluation framework and investigated whether detector-side learning could recover additional performance beyond the strongest traditional and learned baselines.

The original positive story, namely that smooth detector-side mean-residual distillation improves bit error rate (BER), did not survive corrected evaluation. A detailed decision audit then showed that the remaining recoverable performance headroom is sparse, concentrated near decision boundaries, and most concentrated on the **disagreement set** between the receiver hard decision and a stronger teacher (oracle-aligned MP/SIC) decision. This led to the **final Round 8 method**: a teacher-margin gate plus a 4-parameter logistic-regression fusion that operates only on this disagreement set. An earlier 12-feature observable BCE-trained MLP corrector is retained only as a prior baseline against which the final method is compared.

The final contribution of the project is therefore not a new end-to-end AFDM receiver architecture. Instead, it is a technically grounded project outcome with three linked components:  
1. a clarified and stronger traditional baseline inherited from the midterm AFDM receiver line;  
2. a corrected negative result showing why mean-residual correction is not decision-effective in this setting, plus a positive diagnosis showing that the remaining headroom lives on the receiver-vs-teacher disagreement set;  
3. a final **teacher-margin gate + 4-parameter learned fusion** method (Round 8) that delivers an aggregate BER gain of $\sim 1.46 \times 10^{-2}$ over the learned backbone — an order of magnitude larger than the prior 12-feature BCE corrector ($\sim 1.06 \times 10^{-3}$) — while still being train-once / test-on-many on untouched caches.

This report should be written as a technical final-year project report, not as a journal submission. The emphasis should be on system understanding, methodological development, corrected experimental reasoning, honest limitations, and quality of technical analysis.

---

## 2. Report Positioning

This document should **not** be framed as any of the following:

- not a claim of a wholly new AFDM receiver architecture,
- not a pure positive-results paper,
- not merely a negative-results story,
- not a broad generalization claim beyond the current AFDM simulator family.

The correct framing is:

### A technical project report with a diagnostic-plus-method arc

The report should show that:

1. the project began with a classical AFDM joint receiver design for underwater acoustic communication;
2. later learned detector-side improvements were investigated in a more rigorous Python pipeline;
3. the originally promising residual-distillation route failed after corrected evaluation;
4. the failure mechanism was analyzed rather than hidden;
5. that analysis led to a simpler and more reliable decision-level corrector;
6. the final method provides modest but reproducible BER improvements and meaningful packet-level utility in several positive regimes;
7. the method also has a clear and honest failure boundary under harsh path-count shift.

The report should therefore read as a coherent engineering and research trajectory:  
**build baseline → test a stronger idea → discover an evaluation correction and a negative result → diagnose why → redesign method accordingly → evaluate gains and limitations honestly.**

---

## 3. Core Problem Setting

The project studies AFDM receivers under underwater-style doubly selective channels, where significant delay spread, Doppler effects, sparsity, and uncertainty make reliable detection difficult. The central technical question is:

> In the current AFDM joint receiver setting, what kind of receiver-side intervention can still produce real BER gains after the evaluation protocol is corrected?

The work starts from two main foundations:

- a **traditional AFDM receiver family** built around sparse support estimation and iterative refinement;
- a **stronger learned AFDM backbone receiver**, on top of which detector-side post-hoc refinement methods were explored.

The original research hypothesis was that detector-side oracle headroom could be exploited through a learned mean-level residual correction. That hypothesis eventually failed. The final project outcome came from understanding why it failed.

---

## 4. Background and System Setting

### 4.1 Why underwater-style AFDM reception is difficult

Underwater acoustic communication is challenging because the channel is both delay-selective and time-varying. Relative motion, medium fluctuations, and multipath propagation create a difficult detection problem. In such channels, receiver performance depends not only on waveform structure but also on how well the receiver can estimate or exploit sparse delay-Doppler structure and uncertainty in iterative detection.

The project adopts AFDM as the waveform context because AFDM is designed to structure doubly selective channel effects through affine-Fourier-domain processing. In practice, however, good waveform structure alone does not solve the whole problem. Receiver design still matters.

### 4.2 AFDM receiver context in this project

The report should describe the AFDM communication chain at a system level:

- transmit bits are mapped to symbols,
- AFDM modulation is applied,
- the signal passes through an underwater-style doubly selective channel,
- the receiver performs channel-related inference and symbol detection,
- the final output is evaluated by BER and packet-level utility proxies.

The report should explain clearly that this project is primarily about **receiver design and receiver correction**, not about inventing a new modulation waveform.

### 4.3 Two project phases

The project has two distinct development phases:

#### Phase 1: Midterm MATLAB receiver line
This phase implemented a full AFDM-UWA simulation chain in MATLAB and developed a classical joint receiver based on:
- sparse support identification by OMP,
- iterative message passing or related iterative detection,
- least-squares style gain refinement on fixed support.

The canonical MATLAB implementation lives in `matlab/AFDM_UWA_acoustic.m` (the project's authoritative MATLAB simulator). Earlier internal references to a `LEO_frac_switch`-style file are obsolete and should not be cited as the main MATLAB entry point.

The MATLAB and Python pilots use the **same superimposed-pilot (SP) scheme**: known pilot symbols are linearly added on top of the data symbols in the chirp domain, sharing the same time-frequency resources rather than occupying disjoint embedded slots. Both pipelines use the SP definition described in Section 4.

This phase established the interpretability and initial technical foundation of the project.

#### Phase 2: Final Python evaluation and correction phase
This phase moved the work into a stricter Python evaluation environment with improved reproducibility and corrected testing rules. The Python simulator uses the **canonical 10-path UWA configuration** (`P_paths = 10`) as its training and evaluation regime. This is the reference UWA configuration for all final quantitative claims; the larger absolute Python BER values relative to earlier prototypes simply reflect this canonical 10-path setting and the corrected evaluation protocol. The earlier "Python BER is 6-7\% only because the Python channel is harsher than MATLAB" framing has been retired — it confused a simulator-configuration choice (path count and noise reference) with a physical channel difference, and is no longer used in the report.

In that setting, multiple detector-side improvement ideas were reassessed, including:
- learned backbone variants,
- recalibration variants,
- detector-side residual distillation,
- decision-level correction methods.

The Python pipeline becomes the authoritative source for final quantitative claims.

---

## 5. Midterm Traditional Receiver Line

### 5.1 What the midterm work really contributed

The midterm project should be presented as a receiver-design contribution, not as a generic simulation exercise. Its key technical line was a traditional AFDM joint receiver family that used:
- one-shot OMP support locking,
- iterative refinement over that support,
- gain updates and detection feedback.

The report should make clear that the midterm contribution was the construction and validation of this **joint OMP-MP style AFDM receiver pipeline** under underwater-style conditions.

### 5.2 Why the final report does not reuse MATLAB BER numbers directly

The final report should state explicitly that the MATLAB stage remains historically important, but the final numerical claims are unified under the later Python evaluation protocol. This is necessary because:
- the pipelines are not identical,
- later reproducibility and evaluation controls are stronger,
- direct mixing of old MATLAB absolute BER values with final Python numbers would weaken consistency.

### 5.3 Best traditional representative in the final report

The final report should present the strongest traditional representative of the midterm line in the final Python evaluation, rather than over-emphasizing the historically earliest implementation.

Use the following positioning:

- `JointOMPMP`: historical classical baseline,
- `TRADPARAM FIXED`: strongest strict traditional scaffold in the final Python-aligned protocol,
- `TRADPARAM CLASSICAL_FULL`: related variant with learnable classical scalars.

The report should explain that `TRADPARAM FIXED` is the cleanest final representative of the traditional line because it preserves interpretability while outperforming the older `JointOMPMP` baseline at the verified SNR points.

### 5.4 Strengths and limitations of the traditional line

The traditional line should be described as having these strengths:
- interpretable structure,
- explicit sparse-support reasoning,
- stable low-SNR behavior,
- clear engineering logic.

Its limitation is that it eventually reaches a ceiling. This motivated the later investigation into learned detector-side improvement.

---

## 6. Transition to the Final Python Pipeline

The final report should explain that the Python pipeline is not just an implementation rewrite. It matters scientifically because it introduced:
- corrected evaluation rules,
- cleaner train/test separation,
- improved reproducibility,
- more careful baseline comparisons,
- cache-based regime-shift testing.

This transition is essential to the final project outcome because the corrected Python evaluation invalidated the earlier positive interpretation of detector-side residual distillation.

---

## 7. Diagnostic Pivot: Why the Original Learned Route Failed

### 7.1 The original positive story collapsed

The first strong lesson of the final phase is that the original detector-side mean-residual distillation story does not hold under corrected evaluation.

After the evaluation bug related to pilot-format / same-test-set handling was corrected, the following methods became nearly indistinguishable in BER under the same protocol:
- the learned AFDM backbone `CurrentJoint`,
- the uncertainty-recalibrated variant `vx_recal_v1`,
- the cleaned mean-residual model `distill_pure_iter0`.

This should be written as a scientifically important correction, not as an embarrassment. The report should emphasize that the project improved in quality by rejecting a claim that no longer held under stricter evaluation.

### 7.2 Why the failure was informative

The failure of mean-residual distillation was not random. It revealed a mismatch between the learning target and the actual recoverable error structure.

Decision-oracle analysis showed that:
- teacher disagreement exists,
- oracle-beneficial flips exist,
- some low-confidence bits are recoverable,
- but the recoverable headroom is sparse and concentrated near decision boundaries,
- smooth mean-level residuals do not move enough hard decisions to matter in BER.

This is the central scientific pivot of the report.

### 7.3 What earlier learned attempts showed

Before the final method was fixed, several earlier learned correction routes were tested and ruled out:
- linear confidence-style flip gating (too weak; collapsed to threshold $\approx 0.5$),
- split-specific direct bit-level correction (informative but split-bound),
- a frozen 12-feature observable BCE-trained MLP corrector (the previous "final" candidate).

The 12-feature BCE corrector is described in Section 8 only as a **prior baseline** that the new final method is compared against.

The decisive insight from these tests was:
- linear confidence-style gating cannot exploit the recoverable headroom,
- the BCE corrector captured only $\sim 1 \times 10^{-3}$ absolute BER gain even on nominal caches,
- the **teacher (oracle-aligned MP/SIC variant) carries a much larger margin signal that the BCE corrector was not trained to exploit**,
- therefore the right design target is to gate teacher decisions by their own confidence margin, and (optionally) fuse a tiny number of features to choose between the receiver's own decision and the teacher's, rather than learning a generic flip classifier on receiver-side observables alone.

---

## 8. Final Method: Teacher-Margin Gate with 4-Parameter Learned Fusion (Round 8)

### 8.1 Diagnosis that motivated Round 8

The 12-feature BCE corrector is treated only as a prior baseline. Its limitation, exposed by the decision-oracle and headroom-decomposition probes, is that:
- the receiver-side observable feature set saturates at a small ($\sim 10^{-3}$) absolute BER gain,
- the recoverable headroom that remains after the receiver has converged is concentrated on the **disagreement set** $\{b : \hat{s}_b \neq s_b^{\text{teacher}}\}$ between the receiver hard decision and a stronger teacher (oracle-aligned MP/SIC) decision,
- on this disagreement set, the **teacher's own posterior margin** $|\mu^{\text{teacher}}_b|$ is a sharp, almost monotone signal of which side is correct,
- the BCE corrector ignores this signal because it never sees the teacher decision or the teacher margin.

Round 8 was designed to act exactly where this headroom lives: only on the receiver-vs-teacher disagreement set, gated by teacher confidence.

### 8.2 High-level idea

The final method has two stages, both intentionally minimal:

1. **Teacher-margin gate** (1 parameter, no training of a network):
   $$\tilde{s}_b = \begin{cases} s_b^{\text{teacher}} & \text{if } \hat{s}_b \neq s_b^{\text{teacher}} \text{ and } |\mu^{\text{teacher}}_b| > \tau \\ \hat{s}_b & \text{otherwise} \end{cases}$$
   The single threshold $\tau$ is selected on the dedicated training cache by minimizing BER. The trained value used in the report is $\tau^{*} = 0.1$.

2. **4-parameter learned fusion** (logistic regression on the disagreement set):
   On the same disagreement set, a tiny logistic regression takes 3 standardized features
   $$\mathbf{x}_b = \big[\,|\mu^{\text{teacher}}_b|,\;|\ell^{(T)}_b|,\;\snr_{\text{frame}}\,\big]$$
   and outputs the probability that copying the teacher bit is beneficial. With a bias term it has $3 + 1 = 4$ trainable parameters. At inference, $\tilde{s}_b = s_b^{\text{teacher}}$ if the probability $\ge 0.5$, else $\tilde{s}_b = \hat{s}_b$. Both stages are train-once on the dedicated nominal cache and frozen afterwards.

This method should be presented as:
- diagnosis-driven (acts only where the headroom is shown to be),
- extremely small (1 threshold parameter, plus a 4-parameter logistic regression),
- interpretable (each feature has a direct receiver-side meaning),
- train-once and frozen at deployment.

### 8.3 Why this method fits the diagnostic finding

The method directly reflects the conclusion of the decision audit and the headroom-decomposition probe:
- restricting the action to the disagreement set isolates the bits where useful signal actually exists,
- gating by teacher margin aligns the correction with the most discriminative observable on that set,
- the 4-parameter fusion adds just enough capacity to combine teacher confidence, receiver confidence, and operating SNR without re-introducing the over-parameterized failure mode of the BCE corrector,
- the design is the minimal interface that converts the diagnosed disagreement-set headroom into BER.

### 8.4 Inputs

The method uses only observable, deployment-available quantities:
- the receiver's hard decision $\hat{s}_b$ and final-iteration LLR $\ell^{(T)}_b$,
- the teacher's hard decision $s_b^{\text{teacher}}$ and posterior margin $|\mu^{\text{teacher}}_b|$ from the same teacher pipeline used for label generation,
- the frame-level SNR estimate $\snr_{\text{frame}}$.

No oracle bits and no test-time adaptation are used at inference. The teacher is the same MP/SIC variant used to produce the training labels; at deployment it is run alongside the backbone receiver on the same received frame.

### 8.5 Model form

The final method is intentionally tiny:
- the gate stage is a single scalar threshold $\tau^{*} = 0.1$ tuned on the train cache,
- the fusion stage is a logistic regression with 4 trainable parameters (3 weights + 1 bias),
- no hidden layers; an optional 1-hidden-layer MLP variant (`hidden > 0`) is supported in code but not used as the headline final method.

The point of the method is **targeted, minimum-capacity correction on a diagnosed actionable set**, not receiver replacement. The total added capacity is dominated by the teacher pipeline that was already required for training.

### 8.6 Train-once / test-on-many rule

This rule is preserved from the previous "final method" position and remains central to the final claim:
- $\tau^{*}$ is selected once on the dedicated nominal training cache,
- the 4-parameter logistic regression is trained once on the disagreement-set bits of the same training cache (with the BCE objective `1` if `bit_teacher == bit_true`, `0` otherwise),
- both are then frozen and evaluated on untouched nominal and regime-shifted caches.

This distinguishes the final method from split-specific probing or test-adapted post-processing.

### 8.7 Headline Round 8 numbers (3 untouched test caches, full-SNR aggregate)

| Method | BER mean | gain vs `pred` |
|---|---:|---:|
| `pred` (CurrentJoint hard decision) | `6.5000e-02` | — |
| teacher (always copy on disagreement) | `5.7057e-02` | `+7.94e-03` |
| fixed-$\tau$ gate ($\tau^{*}=0.1$) | `5.1359e-02` | `+1.36e-02` |
| **4-parameter learned fusion** | **`5.0417e-02`** | **`+1.46e-02`** |

For comparison, the prior 12-feature BCE corrector (the previous "final method") gives only $\sim 1.06 \times 10^{-3}$ absolute BER gain on the same family of nominal caches. The Round 8 gate alone is **about an order of magnitude larger**, and the 4-parameter fusion adds a further $\sim 9.4 \times 10^{-4}$ on top of the gate.

Per-SNR, the Round 8 fusion delivers `+2.17e-02` at 5 dB, `+2.16e-02` at 10 dB, `+1.48e-02` at 15 dB, `+8.59e-03` at 20 dB, `+6.18e-03` at 25 dB. The gain is largest where the receiver is weakest, exactly the regime that the project cares about.

---

## 9. Experimental Protocol

### 9.1 General principle

The report should describe the experiments as a careful evaluation of:
- classical baselines (`JointOMPMP`, `TRADPARAM FIXED`, `TRADPARAM CLASSICAL_FULL`),
- corrected detector-side variants (`CurrentJoint`, `vx_recal_v1`, cleaned `distill_pure_iter0`),
- the prior 12-feature BCE corrector (reference baseline only),
- the final Round 8 method (teacher-margin gate $\tau^{*}=0.1$ + 4-parameter learned fusion),
- transfer behavior on untouched test caches,
- diagnostic plots of the disagreement set and teacher margin.

### 9.2 Important reporting rule

The report must not invent system parameters that are not verified.  
Where exact simulator parameters are already fixed in code, logs, or tables, they should be extracted faithfully.  
Where a parameter is not yet confirmed in this narrative file, the writer should mark it for insertion from the verified experiment configuration instead of fabricating a number.

### 9.3 Cache-based evaluation

A “cache” denotes a fixed collection of independently generated AFDM frames under a specified regime. The training cache is disjoint from all reported test caches. This should be stated clearly.

### 9.4 Confidence intervals

Paired-bootstrap confidence intervals are used for regime-level gain estimates. The report should describe the confidence intervals as part of the evidence for reproducibility and not merely as decorative statistics.

### 9.5 Regimes of interest

The Round 8 final method is evaluated on **3 untouched nominal test caches** drawn from the canonical 10-path UWA configuration, across SNR $\in \{5, 10, 15, 20, 25\}$ dB.

The four regime-shift caches characterized for the prior 12-feature BCE corrector are:

- higher Doppler severity,
- integer-Doppler structural shift,
- lower pilot-power fraction (`rho = 0.4`),
- severe path-count shift (`P_paths = 15`).

These are documented in this report only as the previously characterized regime-shift behavior of the prior BCE-corrector baseline. Re-running them under the Round 8 gate-plus-fusion is listed as future work in Section 18.

---

## 10. Main Claims and Evidence

### Claim 1  
**Detector-side mean-residual correction is not decision-effective under corrected evaluation.**

**Evidence**
- After corrected protocol alignment, `CurrentJoint`, `vx_recal_v1`, and cleaned `distill_pure_iter0` showed no meaningful BER separation.
- Decision audit showed that useful headroom is concentrated in sparse flips near hard boundaries, not broad mean-level shifts.

---

### Claim 2  
**Simple linear confidence-style flip gating is too weak to provide stable BER gains.**

**Evidence**
- Observable linear flip-gating baselines did not deliver strong or stable gains.
- A later train-calibrated confidence gate collapsed to threshold `0.5`, effectively reproducing the ungated decision rule.

---

### Claim 3  
**A 1-parameter teacher-margin gate ($\tau^{*} = 0.1$) on the receiver-vs-teacher disagreement set gives reproducible BER gains over the learned backbone that are an order of magnitude larger than the prior 12-feature BCE corrector.**

**Evidence (3 untouched test caches, full SNR aggregate)**
- backbone (`pred`) BER mean: `6.5000e-02`
- teacher-only (always copy on disagreement): `5.7057e-02`, gain `+7.94e-03`
- fixed-$\tau$ gate ($\tau^{*}=0.1$): `5.1359e-02`, gain `+1.36e-02`
- prior 12-feature BCE corrector (reference baseline): aggregate gain only `+1.06e-03`

---

### Claim 4  
**Adding a tiny 4-parameter logistic-regression fusion on the disagreement set ([|μ_teacher|, |LLR_model|, snr_db]) further improves the gate.**

**Evidence**
- 4-parameter learned fusion: BER mean `5.0417e-02`, gain `+1.46e-02`
- improvement over fixed-$\tau$ gate: $\sim +9.4 \times 10^{-4}$
- per-SNR gain: `+2.17e-02` (5 dB), `+2.16e-02` (10 dB), `+1.48e-02` (15 dB), `+8.59e-03` (20 dB), `+6.18e-03` (25 dB)
- gain std across 3 untouched caches: `1.66e-04`

---

### Claim 5  
**The Round 8 method is interpretable and minimum-capacity.**

**Evidence**
- the gate has 1 trainable scalar ($\tau$),
- the fusion has 4 trainable parameters (3 weights + 1 bias),
- the only required deployment-time additions are the teacher MP/SIC decision and its posterior margin, both already present in the training pipeline,
- no per-bit MLP, no test-time adaptation, no oracle access.

---

### Claim 6 (retained from earlier diagnostics)  
**The method has an explicit and honest scope boundary inherited from the underlying receiver and teacher.**

**Evidence**
- Severe path-count shift (`P_paths = 15`) was previously shown to break the BCE corrector (BER regression `-7.99e-03`); the Round 8 gate inherits the teacher's degradation in that regime and should be re-evaluated under the same shift before any positive transfer claim is made.
- The paired-bootstrap analyses that confirmed the BCE corrector's failure boundary are still applicable to the teacher pipeline; Round 8 does not invalidate them.

---

### Claim 7 (reference, prior 12-feature BCE corrector)  
**Small BER gains can still matter operationally through packet-level utility amplification.**

The packet-level utility numbers below were measured for the prior 12-feature BCE corrector and are retained here only as reference. Because the Round 8 method delivers an order-of-magnitude larger BER gain, the corresponding packet-level amplification is expected to be much larger; quantifying it is listed as future work in Section 18.

**Reference evidence (prior BCE corrector)**
- `64`-bit packets:
  - nominal relative goodput gain: `+5.22%`
  - higher Doppler: `+4.06%`
  - integer-Doppler shift: `+5.72%`
  - `rho = 0.4`: `+3.62%`
- `256`-bit packets:
  - nominal: `+10.76%`
  - higher Doppler: `+8.77%`
  - integer-Doppler shift: `+11.33%`
  - `rho = 0.4`: `+4.97%`
- `256`-bit `P_paths = 15`: `0` gain

---

## 11. Quantitative Result Summary

### 11.1 Final Method (Round 8) — Aggregate BER on 3 Untouched Test Caches

| Method | BER mean | BER std | Gain vs `pred` |
|---|---:|---:|---:|
| `pred` (CurrentJoint) | `6.5000e-02` | `8.79e-04` | — |
| teacher (always copy on disagreement) | `5.7057e-02` | `6.30e-04` | `+7.94e-03` |
| fixed-$\tau$ gate ($\tau^{*}=0.1$) | `5.1359e-02` | `1.93e-04` | `+1.36e-02` |
| **4-param learned fusion (final)** | **`5.0417e-02`** | **`1.66e-04`** | **`+1.46e-02`** |

### 11.2 Final Method — Per-SNR Gain vs `pred` (3-seed mean)

| Method | 5 dB | 10 dB | 15 dB | 20 dB | 25 dB |
|---|---:|---:|---:|---:|---:|
| teacher | `+1.16e-02` | `+4.90e-03` | `+8.83e-03` | `+8.18e-03` | `+6.18e-03` |
| fixed-$\tau$ gate | `+2.16e-02` | `+1.86e-02` | `+1.36e-02` | `+8.33e-03` | `+6.16e-03` |
| 4-param learned fusion | `+2.17e-02` | `+2.16e-02` | `+1.48e-02` | `+8.59e-03` | `+6.18e-03` |

### 11.3 Reference: prior 12-feature BCE corrector (baseline that Round 8 replaces)

| Regime | Prior BCE corrector gain |
|-------|---:|
| Nominal untouched caches | `1.0590e-03` |
| Higher Doppler severity | `8.4310e-04` |
| Integer-Doppler shift | `1.3249e-03` |
| Lower pilot power (`rho=0.4`) | `1.6699e-03` |
| Severe path-count shift (`P_paths=15`) | `-7.9883e-03` |

The Round 8 final method delivers $\sim 14\times$ the BCE corrector's nominal-cache gain. The BCE-corrector regime-shift table is retained here only to document the prior baseline; regime-shift evaluation of the Round 8 gate and fusion is listed as future work in Section 18.

---

## 12. What the Report Should Emphasize

The final report should emphasize the following strengths:

1. **A coherent project trajectory**  
   The work did not jump randomly between methods. It evolved logically from a traditional AFDM receiver baseline to a corrected final method.

2. **Technical honesty**  
   A previously attractive learned result was rejected after corrected evaluation.

3. **Methodological maturity**  
   The final method was not chosen because it was flashy, but because it matched the diagnosed failure mechanism.

4. **Reproducibility and transfer**  
   The final claim is supported by untouched nominal caches, regime-shifted caches, confidence intervals, ablation, and packet-level utility translation.

5. **Explicit limitations**  
   The severe path-count shift failure boundary is part of the result, not something to hide.

---

## 13. What the Report Should Not Claim

The report must avoid the following overclaims:

1. Do **not** claim a new major AFDM receiver architecture.
2. Do **not** claim broad generalization outside the current AFDM simulator family.
3. Do **not** rewrite the project as if the failed residual-distillation route never happened.
4. Do **not** hide the `P_paths = 15` failure regime.
5. Do **not** describe the packet/goodput utility as a fully coded communication-stack result. It is an uncoded contiguous-packet ARQ-style proxy.
6. Do **not** exaggerate small BER gains into a claim of dramatic receiver redesign success.

---

## 14. Proposed Figures

### Figure 1: Project Trajectory / Hero Figure
A single overview figure that shows:
- the base learned AFDM receiver (`pred`),
- the teacher MP/SIC pipeline,
- the receiver-vs-teacher disagreement set as the actionable region,
- the Round 8 teacher-margin gate followed by the 4-parameter learned fusion,
- the prior 12-feature BCE corrector marked explicitly as a baseline that the new final method replaces.

The caption should emphasize that the final useful intervention is **decision-level, train-once / test-on-many, minimum-capacity (5 trainable parameters total), and acts only on the diagnosed disagreement set**.

### Figure 2: Traditional Baseline Comparison
A figure or table showing why `TRADPARAM FIXED` is the strongest traditional representative of the midterm line compared with `JointOMPMP` and related classical variants.

### Figure 3: Round 8 Per-SNR BER Gains
A line plot of the per-SNR BER gain over `pred` for:
- teacher,
- fixed-$\tau$ gate ($\tau^{*} = 0.1$),
- 4-param learned fusion,

across SNR $\in \{5, 10, 15, 20, 25\}$ dB. The figure should support the claim that gain peaks at low SNR.

### Figure 4: Disagreement-Set Headroom Diagnosis
A diagnostic plot showing, on the disagreement set $\{\hat{s}_b \neq s_b^{\text{teacher}}\}$:
- the empirical probability that the teacher decision is correct, as a function of $|\mu^{\text{teacher}}_b|$,
- justifying both the existence of the headroom and the use of $|\mu^{\text{teacher}}|$ as the gate variable.

### Figure 5: Round 8 vs Prior BCE Corrector Comparison
A bar chart comparing aggregate gain on 3 untouched test caches:
- prior 12-feature BCE corrector ($\sim 1.06 \times 10^{-3}$),
- Round 8 fixed-$\tau$ gate ($\sim 1.36 \times 10^{-2}$),
- Round 8 4-param fusion ($\sim 1.46 \times 10^{-2}$).

The figure should make the order-of-magnitude jump from the BCE baseline to the Round 8 final method visually obvious.

---

## 15. Proposed Tables

### Table 1: Traditional Receiver Summary
A concise summary of:
- `JointOMPMP`
- `TRADPARAM FIXED`
- `TRADPARAM CLASSICAL_FULL`

The table should explain role, key idea, and verified BER comparison.

### Table 2: Final Method Comparison
Compare:
- `CurrentJoint` (`pred`)
- `vx_recal_v1`
- cleaned distillation line
- prior 12-feature BCE corrector (baseline only)
- Round 8 teacher-margin gate ($\tau^{*}=0.1$)
- Round 8 4-parameter learned fusion (final)

The point is not only which method wins, but why the narrative changed: first because corrected evaluation rejected mean-residual distillation, then because diagnosing the disagreement-set headroom led to a much smaller, more targeted final method.

### Table 3: Scope and Claim Matrix
For each supported claim, list:
- supporting experiment,
- quantitative evidence,
- limitation.

This is especially useful for automated writing because it helps the generated report stay disciplined.

---

## 16. Recommended Final Report Structure

The generated report should follow a **technical dissertation-style structure**, not a journal-paper structure.

Recommended chapter logic:

1. **Introduction and Project Scope**  
   Motivate underwater-style AFDM receiver design and state the project objectives.

2. **Background and System Model**  
   Explain underwater-style doubly selective channels, AFDM receiver context, and the receiver-design problem.

3. **Midterm Traditional AFDM Receiver**  
   Present the MATLAB joint OMP-MP line, its logic, and its strongest final representative under the Python-aligned protocol.

4. **Transition to Corrected Python Evaluation**  
   Explain why the later Python pipeline became authoritative and what changed scientifically.

5. **Diagnostic Pivot and Final Round 8 Method**  
   Explain why mean-residual distillation failed, why the prior 12-feature BCE corrector saturated near $\sim 10^{-3}$, how the decision audit and disagreement-set diagnosis changed the design target, and how the teacher-margin gate plus 4-parameter learned fusion was built.

6. **Experimental Setup**  
   Describe cache construction, evaluation regimes, confidence intervals, and reporting rules. State explicitly that the Python pipeline uses the canonical 10-path UWA configuration and the same superimposed-pilot scheme as MATLAB (`matlab/AFDM_UWA_acoustic.m`).

7. **Results**  
   Present baseline comparisons (including the prior 12-feature BCE corrector as a reference), the Round 8 aggregate and per-SNR gains, and the disagreement-set diagnostic plot.

8. **Discussion and Limitations**  
   Explain why Round 8 works, why a 1-parameter gate already beats the BCE corrector by an order of magnitude, why the 4-parameter fusion adds further gain, and what the open scope-boundary questions (regime-shift transfer of the Round 8 method) are.

9. **Conclusion and Future Work**  
   Summarize the final project outcome and propose next steps.

10. **Appendix**  
   Use appendices for implementation alignment, extra tables, detailed feature definitions, or additional methodological details.

---

## 17. Discussion Guidance for the Writer

The discussion chapter should answer these questions explicitly:

1. **Why did the original residual-distillation story fail?**  
   Because the recoverable headroom is not well modeled as a smooth mean residual.

2. **Why did the prior 12-feature BCE corrector saturate near $\sim 1 \times 10^{-3}$?**  
   Because it tried to learn a generic flip classifier from receiver-side observables only and never used the teacher decision or the teacher posterior margin, which is where the residual headroom is most concentrated.

3. **Why does the Round 8 teacher-margin gate + 4-parameter fusion work better?**  
   Because it acts only on the diagnosed disagreement set $\{\hat{s}_b \neq s_b^{\text{teacher}}\}$ and gates by the most discriminative observable on that set ($|\mu^{\text{teacher}}_b|$). The fusion adds the minimum capacity needed to combine teacher confidence, receiver confidence, and SNR. This converts the diagnosed headroom into BER without re-introducing over-parameterization.

4. **Why is the gain biggest at low SNR?**  
   Because that is where the receiver and teacher disagree most, and where teacher confidence carries the largest information advantage. The Round 8 fusion gives `+2.17e-02` at 5 dB and `+2.16e-02` at 10 dB, versus `+6.18e-03` at 25 dB.

5. **What is the engineering value of the final method?**  
   It is interpretable, train-once / test-on-many, has only 5 trainable parameters in total (1 threshold + 4 logistic-regression parameters), and can be layered on top of an existing learned backbone whenever a teacher MP/SIC pipeline is available — which it already is in the project's training pipeline.

---

## 18. Future Work Guidance

The report should end with realistic future work, such as:

- evaluating the Round 8 teacher-margin gate and 4-parameter fusion under the same regime shifts (higher Doppler, integer-Doppler, lower pilot power, severe `P_paths=15`) on which the prior BCE corrector was characterized,
- studying robustness of the Round 8 method to teacher pipeline degradation (since the gate inherits the teacher's failure modes),
- exploring whether a slightly larger but still interpretable fusion (e.g. adding teacher-residual features, or adding a tiny 1-hidden-layer MLP variant) can extend the gain without regressing to BCE-corrector overfitting,
- testing whether the Round 8 design transfers across broader AFDM/UWA simulator families and across different pilot ratios under the canonical 10-path configuration,
- investigating whether the disagreement-set + margin-gate design can be pushed earlier into the iterative receiver loop, rather than only as a post-detection fusion stage.

Future work should remain consistent with the project's actual findings. It should not suddenly claim that the Round 8 method is a universal AFDM solution.

---

## 19. Writing Style Constraints for the Auto Writer

The automatic writing system should follow these rules:

1. Write in a **technical report** style, not in a hype-heavy journal style.
2. Prefer clear engineering explanation over exaggerated novelty language.
3. Keep the project chronology because it is scientifically important.
4. Present negative results honestly.
5. Use internal method names only when needed, and introduce each one with a readable scientific description.
6. Do not invent missing implementation numbers.
7. Do not overuse reviewer-oriented language.
8. Make the report readable for an examiner who did not see the repository.
9. Emphasize technical analysis, methodology, and evidence more than stylistic flourish.
10. Keep limitations explicit.

---

## 20. Suggested Keywords

AFDM, underwater acoustic communication, superimposed pilot, joint OMP-MP receiver, sparse support estimation, model-driven receiver, teacher-margin gate, disagreement-set fusion, decision-level correction, post-hoc correction, train-once / test-on-many, regime shift, low-SNR receiver gain

---

## 21. Deliverables Needed for Writing Pipeline

1. `PAPER_PLAN.md`
2. figure data files
3. final figures in PDF or PNG form
4. optional LaTeX include files for figure reuse
5. report source files
6. bibliography file
7. appendices or supplementary tables if needed

---

## 22. Final One-Paragraph Story for Abstract-Level Use

This project investigates AFDM receiver design for underwater-style doubly selective channels through a two-stage development process. The midterm stage established a traditional AFDM joint receiver family based on one-shot OMP support locking and iterative MP refinement, using a superimposed-pilot frame format on both the canonical MATLAB simulator (`matlab/AFDM_UWA_acoustic.m`) and the Python pipeline (canonical 10-path UWA channel). The final stage re-evaluated detector-side learning in a corrected Python framework. After the evaluation protocol was fixed, the original mean-residual distillation hypothesis no longer delivered meaningful BER gains. A decision audit then showed that the remaining recoverable headroom is sparse, concentrated near decision boundaries, and most concentrated on the receiver-vs-teacher disagreement set. Guided by that finding, the **final method (Round 8) is a 1-parameter teacher-margin gate ($\tau^{*}=0.1$) followed by a 4-parameter logistic-regression fusion over $[|\mu_{\text{teacher}}|, |\ell^{(T)}|, \snr]$ on the disagreement set**. The method is train-once / test-on-many, achieves an aggregate BER gain of $\sim 1.46 \times 10^{-2}$ over the learned backbone — about an order of magnitude larger than the prior 12-feature BCE corrector ($\sim 1.06 \times 10^{-3}$), which is now retained only as a baseline. The largest gains occur at low SNR ($\sim +2.17 \times 10^{-2}$ at 5 dB), exactly the regime that matters most for underwater operation. The final project outcome is therefore a clarified classical baseline, a diagnosed disagreement-set headroom, and a minimum-capacity decision-level fusion method supported by reproducible evidence.
