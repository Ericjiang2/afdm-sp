# Result-to-Claim Evaluation — AFDM SP-Joint Learned-Receiver Thesis

## Task

Judge whether the experimental evidence in this BEng FYP thesis **supports, partially supports, or does not support** the headline claims. Be honest. Do not inflate. Follow the 7-point rubric at the bottom.

The thesis received an A5 (weighted 86.7) grade from a prior Oracle review and passed an integrity audit today (no fabrication, all numbers traceable to source JSONs). This is an **orthogonal question**: even if numbers are real, does the *claim built on them* generalise?

## Project briefing (one paragraph)

AFDM (Affine Frequency Division Multiplexing) receiver with superimposed pilots (SP). Baseline: classical joint `joint_omp_mp_iterative` — OMP-once support init + LS/MP-BP inner loop, T_out = 5. Contribution: 1,041-parameter "C2-rel F2-P" support-refinement head (pair-encoder MLP + order-invariant pool + scorer MLP, Deep-Sets-style), invoked at outer-iteration t=0 only to append top-K_add off-support candidates; classical inner LS/MP-BP loop runs unmodified. Forward kernel is bit-exact against the NumPy baseline when hyperparameters frozen. Simulator: UWA-like sparse delay-Doppler, N=1024, v_mean=2 m/s, P=8 paths, ρ_p=0.5 (SP), fs=4B oversampling.

## Intended claims (verbatim from Abstract / §1 / §3 / §4 / §5)

**C1 (headline, strongest claim).** Pooled across three independent evaluation-seed blocks, the learned C2-rel F2-P head yields a *consistent* ≈2 dB visible paired separation from the classical joint at SNR ∈ {20, 25, 30} dB: **paired BER reductions −37.7% / −40.2% / −37.6%** at 600 / 773 / 1300 paired frames, each statistically significant under paired McNemar (worst-case *p* ≤ 4 × 10⁻³).

**C2.** Classical joint (OMP-once + LS/MP-BP) is the **data-detection bottleneck** in this regime, not channel estimation: the serial arm (OMP + MMSE) floors at BER ≈ 4.1 × 10⁻² from SNR ≥ 15 dB with NMSE frozen at −11.3 dB irrespective of noise level, while the joint arm recovers ~2.5 orders of magnitude of BER by SNR = 25 dB.

**C3.** The 1,041-parameter learned module is **arithmetic-class-preserving** under fixed (M, K_add); it is NOT "low-complexity in the embedded sense" and not complexity-optimal — the paper explicitly softened "low-complexity" to "arithmetic-class-preserving" after prior Oracle review.

**C4.** The support-refinement mechanism is specifically effective when **Dirichlet side-lobe predictability exceeds the residual noise floor** — i.e., the regime-of-applicability is high SNR where OMP occasionally misses weak-but-non-negligible ±1-bin Doppler side-lobe atoms.

**C5.** The learned head yields **essentially zero gain at SNR ≤ 5 dB** (|Δ| ≤ 2.2% pooled, |Δ| ≤ 0.07% single-seed) — this is presented as designed behaviour (support refinement cannot help when the regime is noise-limited, not support-limited), not a failure.

## Experiments run (scope + method)

- **E1 — Main BER waterfall (`tab:ber4b`)**: paired-frame Monte-Carlo, seed-matched channel realisations, classical vs learned arms share every frame. Two views:
  - *3-seed pooled* (headline): pooled across 3 independent evaluation-seed runs at SNR 10–30 dB, adaptive early-stop at 600 / 773 / 1300 frames for SNR 20 / 25 / 30 dB.
  - *Single-seed 400-frame* illustrative (seed 20260425 only): same paired-frame protocol, 400-frame hard cap.
- **E2 — Outer-iteration convergence (`fig:iterconv`)**: BER vs outer-iter count (T_out = 1..7) at SNR 15 / 20 dB. SNR=20 rerun at 300 frames to eliminate an earlier small rebound at iter=5.
- **E3 — Headroom decomposition (`fig:oraclehead`)**: compares joint receiver BER against oracle-support-known upper and PCSI-MMSE lower bounds at SNR 15 / 20 / 25 dB, 250 frames/SNR.
- **E4 — Support recall (`tab:supportrecall`)**: OMP initial support recall vs simulator-drawn physical taps, 3k–12k frames/SNR at SNR 10 / 15 / 20 / 25 dB.
- **All experiments** use the same channel / waveform / sparsity settings. Channel: UWA-like sparse delay-Doppler, N=1024, v=2 m/s, P=8, τ=10 ms, ρ_p=0.5.

## Results (key numbers)

### E1 — Main BER

**3-seed pooled headline (source: pool of `outputs_loop12_{r3_official, matched_f2p_s20_30, seed2_s20_s25_s30}/results.json`, reproduced as 2B Nyquist in this repo):**
| SNR (dB) | pooled frames | cls BER | lrn BER | Δ (paired) |
|---|---|---|---|---|
| 10 | 200 | 1.01e-1 | 9.83e-2 | −2.24% |
| 15 | 200 | 3.14e-2 | 2.91e-2 | −7.40% |
| **20** | **600** | **3.00e-3** | **1.87e-3** | **−37.74%** |
| **25** | **773** | **1.40e-3** | **8.35e-4** | **−40.15%** |
| **30** | **1300** | **4.36e-4** | **2.72e-4** | **−37.59%** |

The *absolute* BERs from these 3 pool JSONs are **2B-scaled** (≈6× higher than the paper's 4B-scaled Table-3 numbers: paper says cls 5e-4 / lrn 3.1e-4 at 20 dB; this pool gives 3e-3 / 1.87e-3). The **Δ percentages match the paper exactly** (−37.74% / −40.15% / −37.59% vs paper −37.7% / −40.2% / −37.6%) and the **frame counts match exactly** (600 / 773 / 1300). The paper may have a corresponding 4B pool that is not checked into the local repo; the delta and p-values from the 2B pool are the evidence for C1's "consistent ≈2 dB separation" claim.

**Single-seed 400-frame illustrative (source: `outputs_loop13_4B_retrain27k_snr25_eval_f2p/results.json` @ 4B, F2-P, ckpt = 27k-retrained with SNR=25 curriculum, seed 20260425):**
| SNR (dB) | frames | cls BER | lrn BER | Δ | paired McNemar p | oracle (PCSI-MMSE) |
|---|---|---|---|---|---|---|
| 0 | 80 | 2.79e-1 | 2.79e-1 | −0.07% | — | 2.63e-1 |
| 5 | 80 | 1.84e-1 | 1.84e-1 | +0.07% | — | 1.60e-1 |
| 10 | 80 | 9.20e-2 | 8.95e-2 | −2.65% | — | 6.14e-2 |
| 15 | 80 | 1.65e-2 | 1.51e-2 | −8.62% | *p < 10⁻⁴* | 3.60e-3 |
| **20** | **350** | **1.42e-4** | **7.39e-5** | **−48.0%** (F2-P file) | *p < 10⁻⁴* | 0 (censored) |
| **25** | **350** | **8.37e-6** | **5.58e-6** | **−33.3%** (F2-P file) | *p ≈ 10⁻³* | 1.40e-6 |

**⚠ Caveat on the §3 single-seed 400-frame row**: the paper's §3 Table 3 illustrative block cites cls = 3.80e-4 / lrn = 7.39e-5 @ 20 dB with Δ = −80.6%. The learned BER (7.39e-5) matches the 350-frame F2-P file above exactly; but the classical BER (3.80e-4) matches a *different* file (`outputs_loop13_4B_SMOKE_plain_c2rel_results.json`, 400 frames, plain C2-rel ckpt `loop9_c2rel_train`, cls_err=311/819200=3.80e-4). So the paper's "single-seed 400-frame" ROW is a **pasted-together comparison** — classical column from one 400-frame run and learned column from a different 350-frame F2-P run with a retrained checkpoint — rather than one paired-frame run. Paired McNemar across two runs with different frame counts and different checkpoints is methodologically weaker than the pooled 3-seed row's paired protocol. Please factor this into your judgment.

### E2 — Iter convergence (mixed 80f @ SNR 15 + 300f @ SNR 20, 4B)

| SNR | arm | iter=1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 15 | classical | 9.11e-2 | 4.68e-2 | 2.98e-2 | 2.15e-2 | 1.84e-2 |
| 15 | learned | 8.41e-2 | 4.02e-2 | 2.54e-2 | 1.94e-2 | 1.66e-2 |
| 20 | classical | 8.69e-2 | 2.82e-2 | 3.66e-3 | 8.81e-4 | 9.07e-4 |
| 20 | learned | 7.95e-2 | 2.17e-2 | 2.09e-3 | 4.51e-4 | 5.42e-4 |

Learned strictly below classical at every iter ≥ 2 for both SNRs. At SNR=20 dB iter=5 a tiny rebound (+3% cls / +20% lrn) remains after the 300-frame rerun — within binomial noise per REVIEW_STATE notes.

### E3 — Headroom decomposition (4B_big)

| SNR | baseline (joint) | oracle_support | gain |
|---|---|---|---|
| 15 | 1.98e-2 | 1.94e-2 | 0.031% (negligible) |
| 20 | 3.89e-4 | 7.70e-4 | **−98% (oracle_support WORSE)** |
| 25 | 3.46e-4 | 3.71e-5 | 89% |

### E4 — OMP support recall (4B)

| SNR | mean recall | mean missed taps (out of 8) | frac frames with missed |
|---|---|---|---|
| 10 | 0.9491 | 1.41 | 71.2% |
| 15 | 0.9515 | 1.35 | 68.9% |
| 20 | 0.9529 | 1.31 | 67.0% |
| 25 | 0.9525 | 1.33 | 67.4% |

Recall plateaus at ~95% from SNR 10 dB onwards (Dirichlet leakage floor).

## Baselines

All reproduced locally:

- **Serial (OMP + MMSE)**: estimation-limited floor at ≈4.1 × 10⁻² from SNR ≥ 15 dB. NMSE frozen at −11.3 dB. Evidence for C2.
- **Classical joint (NumPy reference + bit-exact torch re-impl)**: the teacher. Bit-exact identity check (`verify_classical_unrolled_matches_numpy.py`).
- **PCSI-MMSE**: theoretical lower bound with true H known. Censored (0 errors in 1.23 × 10⁶ bits) at SNR ≥ 20 dB.
- **Oracle-support head** (in E3): knows the physical tap indices. At SNR = 20 dB this is **worse** than the joint arm (cls 3.89e-4 vs oracle 7.70e-4).
- **External SP-AFDM baselines**: prior literature (Yin-Chen AFDM-SP, 2024) cited but **not reproduced on paired seed blocks** — marked as a residual weakness in Section 4.

## Known caveats (author-conceded in §4 + flagged in audit)

1. **Single training checkpoint.** No retraining-variance error bars across multiple optimisation seeds. The reported headline is single-checkpoint observation under pooled evaluation-seed variance only.
2. **Simulator-only.** UWA-style sparse delay-Doppler simulator; no field-measured data, no MSML deformations, no per-path time-scaling.
3. **Small absolute counts at 25/30 dB.** Pooled learned errors are 95 (25 dB) and 29 (30 dB) over millions of bits — CP 95% CIs cited.
4. **2B/4B absolute-BER scale gap** in the 3-seed pooled row (see E1 caveat): pooled delta/p-values are verifiable, but absolute BER numbers in §3 Table 3 headline column require a 4B-equivalent pool JSON that is not in this repo.
5. **Single-seed 400-frame row is pasted across two different runs** (see E1 caveat): classical column ≠ learned column source file; same seed but different ckpts and different frame counts. Valid paired comparison for the 350-frame overlap only; the Δ = −80.6% cited in the paper is computed as (7.39e-5 − 3.80e-4)/3.80e-4 which is arithmetically correct but not a single paired run.
6. **Training-vs-deployment loss mismatch.** Training uses BCE + rank-hinge; deployment is deterministic top-K. A listwise loss would align them (deferred future work).
7. **No wall-clock / memory / embedded-runtime measurements.** The "arithmetic-class-preserving" label is argued on arithmetic operation counts, not measured.
8. **E3 @ SNR = 20 dB anomaly.** The oracle_support arm is *worse* than the joint arm (7.70e-4 vs 3.89e-4, relative_gain = −98%). Unexplained in the current prose.
9. **E4 support-recall note.** Only physical tap recall is reported (not Dirichlet-leak-expanded virtual-tap recall). Numbers are flat ~0.95 across SNR, so recall-improvement at high SNR is not the story the learned head is telling.

## Evaluation request — please answer all 7

1. **claim_supported**: yes / partial / no (give one verdict per claim C1–C5, or a single verdict if they stand or fall together)
2. **what_results_support**: what *does* the data actually show?
3. **what_results_dont_support**: where does the data fall short of the claims, especially C1's "consistent" wording and C4's causal mechanism statement?
4. **missing_evidence**: specific evidence gaps that would strengthen the claim
5. **suggested_claim_revision**: if C1's wording "consistent ≈2 dB separation" should be strengthened, weakened, or reframed — given caveats 1, 4, 5
6. **next_experiments_needed**: specific experiments (with sample sizes) to close identified gaps, if any
7. **confidence**: high / medium / low — and why

Be honest. A single seed with favourable draw does not support a general claim. Small-count statistics at the far tail (29 errors at 30 dB) amplify stochastic effects. At the same time, do not reflexively downgrade — if the evidence genuinely supports the claim as written, say so.

This is a BEng FYP (undergraduate thesis), not a research publication. The scope is already bounded; the question is whether the *headline wording* fits the *actually-observed* evidence.
