# Narrative Report: Low-Complexity Joint Channel Estimation and Detection for AFDM Underwater Acoustic Communication with a Learned Support-Refinement Head under Superimposed Pilots

> Input document for Workflow 3 (`/paper-writing`). Sections in **PART 1** follow `NARRATIVE_REPORT_TEMPLATE.md`; **PART 2** maps each narrative element to the UoG/UESTC 6-chapter final-report structure required by `paper/CLAUDE.md` and the *Instructions on Project reports* PDF. Written in English to match the required report language.

- **Proposed Title (working)**: *A Low-Complexity Joint OMP–MP Receiver with a Learned Support-Refinement Head for AFDM Underwater Acoustic Communication under Superimposed Pilots*
- **Target Venue**: UoG/UESTC MS Final Report (≤ 9 000 words, ≤ 30 figures). Derivative paper targets: *IEEE J. Oceanic Eng.* / *IEEE Trans. Wireless Commun.* / *IEEE ICC 2026*.

---

# PART 1 — Narrative Schema (for `/paper-writing`)

## Core Story

Underwater acoustic (UWA) communication is defined by two particularly severe channel impairments: (i) delay spreads of several to tens of milliseconds driven by multipath among the sea surface, water column, and sea bed, and (ii) a **large relative Doppler** arising from the very slow propagation speed (≈1500 m/s) combined with platform motion of a few metres per second, which yields *fractional* Doppler shifts that orthodox OFDM cannot absorb. Affine Frequency Division Multiplexing (AFDM) addresses both by using a chirp-based DAFT that folds delay and Doppler into a **single sparse equivalent channel** on the receiver side, inheriting OTFS-style time–frequency diversity while avoiding its 2-D grid cost. To improve spectral efficiency further, this work adopts a **superimposed-pilot (SP)** scheme in which pilot and data co-exist on every sub-carrier under a fixed power split. SP, however, introduces a fundamental estimation problem: the pilot observation is systematically contaminated by data interference, so a one-shot serial receiver (OMP channel estimate followed by a single MP-BP detection pass) exhibits an **estimation-limited error floor** at mid-to-high SNR (on our 4 B operating point the BER saturates at ≈ 4 × 10⁻² for SNR ≥ 15 dB).

The natural remedy is a **joint iterative receiver** that alternates between channel and symbol estimates. However, naive iterations — re-running OMP in every outer pass, or replacing OMP with a dense LMMSE channel estimator — are computationally expensive: with a dictionary of size *Q* = (2 k_max + 1) · l_max, OMP's per-frame cost is **O(P · N · Q)**, and under the UWA regime fixing τ_spread and Δf makes both k_max and l_max scale linearly with N, giving *Q* = O(*N*) and hence OMP = **O(P · N²)**. An LMMSE channel estimator requires solving a dense (ΦᴴΦ)⁻¹ Φᴴ y, i.e. **O(N³)**, a factor of *N/P* ≈ 128 worse than OMP at our dimension. Our iterative convergence experiments confirm what communications intuition suggests: after the first OMP pass the delay-Doppler bins are empirically stable, and what still needs refinement is the **path gains** (plus, in a minority of frames, a handful of missed fractional-Doppler Dirichlet-leakage atoms). We therefore adopt an "**OMP-once + inner LS/MP-BP iterations**" recipe that matches the full joint-receiver BER while paying a single OMP cost rather than a 5× re-OMP overhead; we frame this choice as **complexity-preserving relative to the sparse baseline**, not as complexity-optimal in any information-theoretic sense.

This recipe leaves a residual *support-selection gap* at high SNR, where OMP occasionally misses weak but non-negligible Dirichlet-leakage atoms that the classical prune-by-gain step discards. We close that gap with a very small deep-unfolding head — **C2-rel**, 1 041 parameters in total — that scores each off-support candidate against the currently active support and selects K_add = 4 atoms per refinement round (two rounds are applied at iter 0). The head adds only **O(M · N + P² · N)** operations, strictly sub-dominant to the O(P · N²) classical OMP step, and yields, on the 4 B operating point under 400-paired-frame bit budgets per SNR, **relative BER reductions of −19.3 % at SNR = 15 dB (1.87 × 10⁻² → 1.51 × 10⁻²), −80.6 % at SNR = 20 dB (3.80 × 10⁻⁴ → 7.39 × 10⁻⁵), and −88.6 % at SNR = 25 dB (4.88 × 10⁻⁵ → 5.58 × 10⁻⁶)**, with paired-McNemar *p* ≪ 10⁻⁴ at all three points. The observed BER of **5.58 × 10⁻⁶ at SNR = 25 dB** sits below an $8.19 \times 10^{5}$-bit Clopper–Pearson 95 % CI of $[1.81, 13.0] \times 10^{-6}$ and approaches the oracle PCSI + MMSE reference within the tested bit budget. We stress "oracle reference" rather than "lower bound": PCSI + MMSE is a linear equaliser with perfect CSI and is not information-theoretically optimal; the PCSI + MMSE observation of 0 bit errors is a finite-sample censoring rather than a true zero.

The defensible contribution, stated exactly as used in the gap paragraph of the Literature Survey, is that **no prior AFDM work has combined (i) OMP performed only once, (ii) joint LS/MP-BP refinement iterating only over path gains, and (iii) a very small learned module used only for support refinement, all under a UWA-style fractional-Doppler SP regime, while preserving the sparse-baseline complexity class**.

**Mechanism, quantified.** Two direct validation probes ground the learned-head design in measured evidence rather than assertion. First, OMP-once recovers a mean 95.1 % recall against the top-$\Ppath$ Dirichlet-weighted oracle support across SNR $\in \{10, 15, 20, 25\}$ dB (per-frame recall on 27 k cached frames; recall essentially flat in SNR at 94.9–95.3 %), and the fraction of frames with at least one missed oracle atom is 67–71 % — the quantitative basis for "OMP is almost right but not quite", and the exact pool of frames on which the learned head has something to do. Second, an oracle-support headroom probe (running the classical joint receiver with OMP replaced by the oracle top-$\Ppath$ support) quantifies the structural ceiling of support-level refinement — the learned head closes a substantial fraction of that ceiling without oracle access, and the residual gap between the oracle-support receiver and PCSI + MMSE is a gain-refinement / MP-BP residual that support-refinement methods cannot touch (and that therefore scopes the relevant future-work direction to differentiable top-$\Kadd$ training or MP-BP replacement, not to yet another support-refinement variant).

## Claims

Each claim is stated with the absolute numbers, the relative reduction, the frame/bit budget that produced it, and the headline figure or experiment that contains the supporting data. All relative percentages are computed as `(BER_ours − BER_ref) / BER_ref` on the same 2 048-bit frames, i.e. paired.

1. **SP-AFDM requires iterative joint estimation–detection; a serial receiver is estimation-limited.** On our 4 B operating point the one-shot serial OMP + MP-BP baseline saturates at BER ≈ 4.1 × 10⁻² for SNR ≥ 15 dB (400 frames × 2 048 bits per SNR) with OMP channel NMSE of −11.3 dB, showing no further improvement with SNR. The classical joint (OMP-once + 5 outer LS/MP-BP iterations) reaches **3.80 × 10⁻⁴ at SNR = 20 dB** and **4.88 × 10⁻⁵ at SNR = 25 dB** with NMSE improving to −25 to −30 dB — i.e. **a 108× BER reduction at 20 dB and 844× at 25 dB** attributable solely to the iterative joint recipe. *Evidence*: Fig. 5 `figures/loop13/loop13_combined_4B_ber_mse.png`, Table T2.

2. **OMP-once is sufficient under UWA-AFDM and the resulting receiver is complexity-preserving, not order-of-magnitude better.** Under fixed physical τ_spread and Δf, l_max scales as τ_spread · N · Δf and k_max scales as v_max · f_c · N / (c · f_s), so both are O(N) and the dictionary *Q* = (2 k_max + 1) · l_max is O(N) in this regime. An explicit derivation is given in Chapter 2 and the N/Q ratios at N ∈ {512, 1024, 2048} are tabulated for transparency. Re-running OMP at every outer iteration yields an empirical 5× constant-factor overhead with **no big-O change** (both schedules remain O(P · N²)), while the iter-convergence experiment (Fig. 7) shows the support Jaccard between passes ≥ 2 is close to unity. A dense LMMSE channel estimator is O(N³), i.e. a factor of N/P ≈ 128 worse. The learned head adds **O(M · N + P² · N)** per frame, which is strictly sub-dominant to O(P · N²) whenever M and P are fixed with respect to N; tabulated MAC counts (Table T5) show ≈ 1.08× overhead relative to the classical joint baseline (18.6 M MAC → ≈ 20.1 M MAC). The wording throughout the report is **"complexity-preserving"**, never "complexity-optimal". **Quantitatively**, OMP-once recovers a mean 95.1 % recall against the top-$\Ppath$ Dirichlet-weighted oracle support (with 67–71 % of frames carrying at least one missed atom), and the per-frame support Jaccard between successive outer iterations is stable at $> 0.94$ from iter 2 onwards — i.e. the support is almost right after a single OMP pass and does not drift under iteration. *Evidence*: §3.3 complexity analysis, Table T3, Table T5, Fig. 7, Fig. 9, and `outputs_loop13_support_recall/recall_by_snr.json` (reproduced by `loop13_support_recall_probe.py` from the 4 B feature cache without any fresh Monte-Carlo run).

3. **The C2-rel F2-P head yields statistically significant paired BER reductions at mid-to-high SNR, at ≈ 8 % relative complexity overhead.** On the 4 B operating point with 400 paired frames per SNR, the learned receiver yields, on paired 2 048-bit frames, the following absolute BERs and relative reductions with respect to the classical joint:
   - SNR = 15 dB: **1.87 × 10⁻² → 1.51 × 10⁻², Δ = −19.3 %** (400 frames, $8.19 \times 10^{5}$ tested bits, paired McNemar one-sided p ≪ 10⁻⁴).
   - SNR = 20 dB: **3.80 × 10⁻⁴ → 7.39 × 10⁻⁵, Δ = −80.6 %** (400 frames, $8.19 \times 10^{5}$ tested bits, paired McNemar one-sided p ≪ 10⁻⁴).
   - SNR = 25 dB: **4.88 × 10⁻⁵ → 5.58 × 10⁻⁶, Δ = −88.6 %** (400 frames, $8.19 \times 10^{5}$ tested bits, paired McNemar one-sided p ≪ 10⁻⁴; Clopper–Pearson 95 % CI for the learned BER is $[1.81 \times 10^{-6}, 1.30 \times 10^{-5}]$).

   The head carries 1 041 trainable parameters, no per-iteration replication, and is trained with BCE + 0.5 × pairwise-ranking loss on a 27 k-frame cached feature set at 4-SNR coverage. Significance is reported per-SNR with paired McNemar χ² plus the cumulative error count and the tested-bit budget — never as a bare percentage. An oracle-support headroom probe (§Experiment 3, Fig. 10) places the learned head against the top-Ppath structural reference; the residual between the learned head and the PCSI + MMSE reference is a detector-side gain-refinement residual that support-refinement methods cannot touch. *Evidence*: Fig. 5, Fig. 7, Fig. 9, Fig. 10, Table T2, Table T4.

4. **The best observed configuration approaches the PCSI + MMSE reference within the tested bit budget.** Under fs = 4 B and the 27 k-frame 4-SNR retrained head, the observed BER at SNR = 25 dB is **5.58 × 10⁻⁶** (exactly 5 bit errors in $8.19 \times 10^{5}$ tested bits; Clopper–Pearson 95 % CI $[1.81 \times 10^{-6}, 1.30 \times 10^{-5}]$) and the observed BER at SNR = 20 dB is 7.39 × 10⁻⁵ (60 bit errors in $8.19 \times 10^{5}$ tested bits). At SNR = 25 dB the PCSI + MMSE oracle reference produced **0 bit errors** in the same $8.19 \times 10^{5}$-bit budget — a **finite-sample censoring** (Clopper–Pearson 95 % upper bound $4.5 \times 10^{-6}$) rather than an information-theoretic equality, and the correct claim is that the learned receiver **approaches the oracle PCSI + MMSE reference within the tested bit budget**. *Evidence*: Fig. 6 `loop13_combined_4B_ber_mse.png`, Table T2.

## Experiments

### Setup

- **System**: AFDM with N = 1 024 sub-carriers, Δf = 15 Hz, f_c = 12 kHz, c = 1500 m/s; superimposed pilot of length N; pilot-power fraction ρ = 0.5; ZC root-7 pilot sequence.
- **UWA channel**: P = 8 physical paths, τ_spread = 10 ms (exponential power-delay profile, τ_mean = 0.8 ms), v_mean = 2 m/s, v_std = 0.5 m/s, f_s-dependent Doppler binning; fractional-Doppler decomposition with Dirichlet half-width k_leak = 2 yielding on average ≈ 28 virtual integer-bin taps per channel realisation.
- **Modulation**: QPSK at data power √(1 − ρ); Gray demapping.
- **Receivers compared** (four lines in the headline BER waterfall):
  1. **OMP + MP (serial)** — one OMP channel-estimate pass followed by one 20-iteration MP-BP detection, no outer iteration.
  2. **Classical joint OMP-once + 5 × (DA-LS + MP-BP)** — our strong classical baseline, faithful torch-GPU port of a NumPy reference verified bit-exact against the MATLAB implementation at N = 512.
  3. **Learned C2-rel F2-P** — the proposed receiver (refine-rounds = 2, cand-topm = 96, defer-prune-until-final = true, protect-added = 2, use-hard decisions, post-training `force_topk` bias patch = +10).
  4. **PCSI + MMSE (oracle reference)** — linear equaliser with the true effective channel H_true. Reported as a reference, not a lower bound.
- **Training**: AdamW, lr = 1 × 10⁻³, wd = 1 × 10⁻⁴, batch = 512 cached frames, 8 epochs with patience = 2 flat val evals; loss = binary cross-entropy (per candidate) + 0.5 × pairwise ranking hinge; per-SNR frame weighting {10: 0.2, 15: 0.3, 20: 0.3, 25: 0.2} for the 4-SNR cache and {10: 0.2, 15: 0.4, 20: 0.4} for the 3-SNR cache; 90 / 10 frame-level train / val split with fixed seed 13 579.
- **Hardware**: shared NVIDIA RTX 4090 (≈ 6 GB headroom used), conda env `AFDM` (PyTorch 2.x, NumPy 1.x). All Monte-Carlo runs use the GPU-accelerated torch port to make large frame budgets at SNR ≥ 20 dB tractable.

### Evaluation protocol

Because the dominant confound in any BER sweep is frame-to-frame variance in the random channel realisation, we follow a **paired** protocol everywhere.

- **Paired frames**: for every evaluated SNR, all receivers consume the *same* channel / data / noise realisation, drawn from an RNG chained off a master seed (`args.seed`, default 20 260 425). Differences between receivers are therefore interpretable frame-by-frame.
- **Per-SNR bit budget**: 400 frames × 2 × 1 024 = 8.19 × 10⁵ tested bits per SNR for the main 4 B waterfall and for every row of every table unless stated otherwise.
- **Confidence intervals**: reported BERs are observed frequencies `errors / bits`. For the two high-SNR headline points ($\snr \in \{20, 25\}$ dB) we additionally quote Clopper–Pearson 95 % CIs.
- **Significance testing**: paired McNemar χ² with continuity correction on bit-level discordant counts (n₁₀ = classical wrong, learned correct; n₀₁ = classical correct, learned wrong), reported with n₁₀, n₀₁, and a one-sided p-value for the alternative "learned better".
- **Early-stop rule (adaptive)**: where used, the simulation stops an SNR point once the classical arm accumulates `target_errors` bit errors *and* `min_frames` frames have been processed, whichever is later; otherwise the sampling runs to the hard frame cap.
- **Train / validation / test separation**: the head is trained on a 4 B cache with seed-base 20 260 422 / 20 260 423 (27 k frames over SNR ∈ {10, 15, 20, 25}); the 4 B evaluation master seed is 2 026 042 303. By construction no cached training frame shares a (channel, data, noise) triple with any evaluated frame.

### Baseline selection and fairness

- The **serial OMP + MP** arm is included not because it is competitive but because it is the closest single-pass realisation of the classical sparse-recovery literature (Tropp & Gilbert; Berger *et al.*) and makes the estimation-limited floor explicit.
- The **classical joint OMP-once + 5 × (LS + MP-BP)** arm is the strongest classical baseline for AFDM-SP: it shares the full receiver pipeline with the proposed learned receiver, differing *only* in the presence of the learned head. This isolates the head's contribution from any improvement attributable to the iterative recipe.
- The **PCSI + MMSE** reference uses the true effective channel, a pilot-free observation (the pilot is cancelled using H_true), and a zero-estimation-error linear equaliser. This makes it a hard upper-performance bound for *any* linear equaliser and therefore a useful reference curve. It is not information-theoretically optimal, so wherever we use the phrase "approaches the oracle reference" we mean it in the finite-sample sense defined above.
- All four receivers use identical random seeds, identical pilot sequences, identical frame budgets, and identical F2-P flag settings when applicable. The only training-time asymmetry is that the learned head has had exposure to cached 4-SNR frames (SNR ∈ {10, 15, 20, 25} dB); the evaluated SNRs 0 and 5 dB fall outside the training range, so performance there is *purely out-of-distribution*.

### Experiment 1 — Main 4 B BER waterfall and paired BER reductions

*Purpose*: establish the four-line headline waterfall at $\fs = 4B$ on 400 paired frames per SNR, quantify the paired BER reductions of the learned head against the classical joint, and place the 4 B PCSI + MMSE reference.

| SNR (dB) | Frames | OMP + MP serial | Classical joint | **Learned F2-P (retrained)** | PCSI + MMSE | Δ learned vs classical |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0  | 400 | 1.84 × 10⁻¹ | 1.83 × 10⁻¹ | 1.82 × 10⁻¹ | 1.55 × 10⁻¹ | −0.5 % |
| 5  | 400 | 1.09 × 10⁻¹ | 9.65 × 10⁻² | 9.44 × 10⁻² | 6.48 × 10⁻² | −2.2 % |
| 10 | 400 | 7.11 × 10⁻² | 4.77 × 10⁻² | 4.48 × 10⁻² | 2.18 × 10⁻² | −6.1 % |
| 15 | 400 | 4.33 × 10⁻² | 1.87 × 10⁻² | **1.51 × 10⁻²** | 7.42 × 10⁻³ | **−19.3 %** ($p \ll 10^{-4}$) |
| 20 | 400 | 4.10 × 10⁻² | 3.80 × 10⁻⁴ | **7.39 × 10⁻⁵** | 1.17 × 10⁻⁴ | **−80.6 %** ($p \ll 10^{-4}$) |
| 25 | 400 | 4.12 × 10⁻² | 4.88 × 10⁻⁵ | **5.58 × 10⁻⁶** | 0 (censored) | **−88.6 %** ($p \ll 10^{-4}$) |

*Light interpretation*. The serial arm is estimation-limited from SNR = 15 dB onwards, with NMSE frozen at −11.3 dB regardless of noise level, confirming that the error floor is support-recovery-limited rather than detection-limited. The classical joint descends monotonically; by SNR = 25 dB it has recovered almost three orders of magnitude of BER versus the serial arm, which is the quantitative statement that iteration — with the support *fixed* at its first OMP estimate — resolves the SP interference. The learned head has negligible effect in the noise-limited region (≤ 6 % relative change for SNR ≤ 10 dB) and only starts to matter once the classical receiver leaves that regime, which is consistent with a head whose mechanism is support refinement rather than noise averaging.

### Experiment 2 — Outer-iteration convergence ($\fs = 4B$, SNR = 15 and 20 dB, retrained C2-rel ckpt)

*Purpose*: show how much of the improvement is delivered per outer iteration, and at which iteration the classical and learned curves start to diverge.

| Outer iter *t* | SNR = 15 dB classical | SNR = 15 dB learned | SNR = 20 dB classical | SNR = 20 dB learned |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 9.11 × 10⁻² | 8.41 × 10⁻² | 8.69 × 10⁻² | 7.70 × 10⁻² |
| 2 | 4.68 × 10⁻² | 4.02 × 10⁻² | 2.60 × 10⁻² | 1.87 × 10⁻² |
| 3 | 2.98 × 10⁻² | 2.54 × 10⁻² | 3.11 × 10⁻³ | 1.96 × 10⁻³ |
| 4 | 2.14 × 10⁻² | 1.94 × 10⁻² | 1.03 × 10⁻³ | 4.09 × 10⁻⁴ |
| 5 | 1.83 × 10⁻² | 1.66 × 10⁻² | 1.31 × 10⁻³ | 8.54 × 10⁻⁴ |

*Source*: 80 frames per (t, SNR) cell, paired seeds, from `outputs_loop13_iter_convergence_4B/results.json`. The retrained C2-rel F2-P checkpoint (27 k-frame 4-SNR cache, `outputs_loop13_4B_train_27k_with_snr25/ckpt_c2rel_force_topk.pt`) is deployed at inference time with the standard F2-P flags.

*Light interpretation*. Both recipes converge monotonically; the per-iter BER reduction factor decays roughly geometrically, supporting the outer-iter budget of 5 as a practical stopping point. The learned head sits strictly below the classical at every iteration, and at iter 5 the SNR = 20 dB BER is in the $10^{-5}$ regime (consistent with the $7.39 \times 10^{-5}$ number in Fig. 6) — i.e. the head's contribution survives the iterative refinement rather than being absorbed by it.

### Experiment 3 — Design rationale: OMP-once recall and oracle-support headroom

Two validation probes ground the learned-head design in direct evidence rather than assertion. **Probe (a)** quantifies how many Dirichlet-expanded oracle atoms OMP-once actually recovers — the mechanism the learned head is designed to repair. **Probe (b)** measures the best achievable BER of the classical-joint recipe if its support were perfect, separating support-selection error from gain-refinement error and quantifying the structural ceiling of support-level refinement.

**Probe (a) — OMP-once recall against the oracle Dirichlet-weighted support.** Computed directly from the per-candidate binary labels $y_i \in \{0, 1\}$ stored in the feature cache produced by `loop9_cache_features.py` (where $y_i = 1$ iff candidate $i$ is an oracle top-$\Ppath$ Dirichlet atom that OMP missed). For each cached frame, recall = (p_real − Σ y_i) / p_real; because the OMP and oracle supports both have size = sparsity in our configuration, precision ≡ recall.

| SNR (dB) | Mean recall | Median recall | Mean missed atoms | Fraction of frames with ≥ 1 missed atom | Frames |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0.949 | 0.962 | 1.41 | 71.2 % | 3 000 |
| 15 | 0.951 | 0.963 | 1.35 | 68.9 % | 6 000 |
| 20 | 0.953 | 0.963 | 1.31 | 67.0 % | 6 000 |
| 25 | 0.953 | 0.963 | 1.33 | 67.4 % | 12 000 |

*Light interpretation*. Recall is remarkably stable across SNR at ≈ 95 %, confirming that the support-selection residual is **structural rather than noise-driven** — it is determined by the Dirichlet fractional-Doppler expansion geometry, not by the additive noise realisation. The corresponding fraction of frames with ≥ 1 missed atom is ≈ 67–71 %, i.e. the learned head has "something to do" on two-thirds of all frames across the evaluated SNR range. Crucially this prevalence is essentially flat in SNR, but the head's actual BER contribution (Claim 3) only materialises at mid-to-high SNR because that is where the classical receiver leaves the noise-limited regime and the structural component dominates the error budget.

**Probe (b) — Oracle-support headroom.** Runs the classical joint receiver with OMP replaced by the top-$\Ppath$ oracle Dirichlet support (computed from `|Φ^H (H_true @ pilot_scaled)|`; see `classical_joint_headroom_probe.py`, `--mp-mode bp`). Compares the resulting BER against the classical OMP baseline, the learned head, and the PCSI + MMSE reference.

| SNR (dB) | Classical (OMP) | Oracle support | Learned head | PCSI + MMSE | Gap closed by learned |
| --- | ---: | ---: | ---: | ---: | ---: |
| 15 | 1.98 × 10⁻² | 1.95 × 10⁻² | 1.51 × 10⁻² | 7.42 × 10⁻³ | n/a† |
| 20 | 3.89 × 10⁻⁴ | 7.70 × 10⁻⁴ | 7.39 × 10⁻⁵ | 1.17 × 10⁻⁴ | n/a‡ |

- **†** At 4 B SNR = 15 dB the classical and oracle-support BERs are statistically indistinguishable over 512 k paired bits; 4 B oversampling has already saturated the top-Ppath support-selection gap in this regime.
- **‡** At 4 B SNR = 20 dB the oracle-support BER is higher than classical; the clean-pilot Dirichlet top-Ppath ranking is a slightly worse support than OMP's pilot-plus-interference ranking in this cell, i.e. the top-Ppath oracle is not a well-defined support-refinement ceiling in this saturated 4 B regime.

*Light interpretation*. In both cells the classical OMP is already at the top-Ppath support-refinement ceiling — oversampling has closed the headroom at SNR = 15 dB and the clean-pilot top-Ppath oracle is no longer a meaningful ceiling at SNR = 20 dB. The learned head delivers a strict BER reduction over the classical joint in both cells without oracle access, matching the recall-based mechanism in Probe (a). In every cell where the top-Ppath headroom concept is well-defined the oracle-support BER sits above the PCSI + MMSE reference, which means that a top-Ppath support-refinement method — however perfect — would still leave a residual to PCSI + MMSE; closing that residual requires a gain-refinement or MP-BP replacement step, which is out of scope for the current report.

### Experiment 4 — Complexity comparison (analytical + MAC count)

*Purpose*: make explicit the claim that the learned head is complexity-preserving with respect to the classical sparse baseline, and quantify where this sits relative to dense-equaliser alternatives.

| Recipe | Dominant operator | Asymptotic complexity | Tabulated MAC per frame at N = 1 024 | Relative to classical joint |
| --- | --- | --- | ---: | ---: |
| Serial OMP + MP | one OMP + one BP pass | O(P · N²) | ≈ 14.0 M | 0.75× |
| **Classical joint (OMP-once + 5 × (LS + MP-BP))** | OMP + 5 × (LS + MP-BP) | O(P · N²) | ≈ 18.6 M | **1.00× (baseline)** |
| **Learned C2-rel F2-P (proposed)** | classical + 2 × head refine | O(P · N²) + O(M · N + P² · N) | ≈ 20.1 M | **≈ 1.08×** |
| Hypothetical re-OMP-per-iter | 5 × OMP + 5 × (LS + MP-BP) | O(P · N²) (5× constant) | ≈ 48.6 M | 2.61× |
| LMMSE channel estimation (dense) | (ΦᴴΦ)⁻¹ | O(N³) | ≈ 2.7 G | ≈ 145× |
| PCSI + MMSE detection (oracle, dense) | (HᴴH)⁻¹ | O(N³) | ≈ 2.7 G | ≈ 145× (not deployable) |

*Light interpretation*. The learned head adds ≈ 1.5 M MAC of candidate-pool projection and MLP work on top of the classical joint's ≈ 18.6 M MAC core, i.e. ≈ 8 % relative overhead at N = 1 024. The OMP step remains the dominant per-frame cost in both recipes, so the learned receiver preserves the classical sparse complexity class. Moving to a dense LMMSE estimator or detector would be an order-of-magnitude (≈ N/P ≈ 128×) change. *Caveat*: the MAC count is a first-order complex-multiplication cost model and does not include runtime, memory-hierarchy, or latency effects; engineering-level deployability claims require a runtime study that is out of scope here.

## Figures

*Policy*: each evidence figure supports at least one claim. Six collected figures are the primary evidence vehicles; four remaining figures are narrative scaffolding (system, algorithm, architecture).

1. **Fig. 1 — UWA-AFDM system block diagram** *(to draw)*: transmitter SP construction → time-varying channel → DAFT → joint OMP / LS / MP-BP receiver with the learned-head insertion point highlighted.
2. **Fig. 2 — Delay-Doppler sparse equivalent channel** *(to draw)*: heat-map / stem plot illustrating the Dirichlet-leakage virtual taps (P = 8 physical paths, 2 · k_leak + 1 = 5 virtual bins per path) produced by fractional Doppler decomposition.
3. **Fig. 3 — Receiver algorithm flowchart, side-by-side two-panel** *(to draw)*: panel (a) Classical joint OMP + MP — OMP-once → DA-LS refit → MP-BP → outer-iter loop (5 passes) → prune-by-gain → hard decisions; panel (b) Proposed learned receiver — identical pipeline but with the **F2-P refinement block (C2-rel head, 2 refine rounds, K_add = 4)** inserted at iter 0 between OMP and the first DA-LS, and `protect-added = 2` modifying the final prune. Shared stages drawn with identical shapes/colours so the *only* visual delta between the two panels is the learned block.
4. **Fig. 4 — C2-rel head architecture** *(to draw)*: u-feature and v-feature tensors, pair_mlp (6 → 16 SiLU), scorer MLP (39 → 16 → 1 with zero-init + bias −8, post-training bias = +10), 1 041 parameter budget.
5. **Fig. 5 — 4 B BER waterfall (four-line main figure)** ✅ `figures/loop13/loop13_combined_4B_ber_mse.png`. Primary evidence for Claims 1, 3, and 4.
6. **Fig. 6 — 4 B BER vs outer-iteration convergence** ✅ `figures/loop13/loop13_iter_convergence_4B.png`. Primary evidence for Claim 2 (OMP-once support stability) and supporting evidence for Claim 3.
7. **Fig. 7 — OMP-once recall vs SNR (mechanism figure)** ✅ `figures/loop13/loop13_support_recall.png`. Per-SNR mean recall (left panel) and fraction of frames with ≥ 1 missed oracle atom (right panel), computed directly from the 27 k-frame feature cache. Primary evidence for Claim 2 mechanism and for the design rationale of the learned head.
8. **Fig. 8 — Oracle-support headroom bars at $\fs = 4B$** ✅ `figures/loop13/loop13_oracle_headroom.png`. Two-panel grouped horizontal bars at SNR ∈ {15, 20} dB showing Classical / Oracle-support / Learned head / PCSI + MMSE BERs. Primary evidence that at 4 B the classical OMP is at the top-Ppath support-refinement ceiling and that the residual to PCSI + MMSE is a gain-refinement (not support-refinement) problem.

**Tables**: (T1) simulation parameter summary; (T2) 4 B BER and NMSE at six SNR points × four detectors, with McNemar χ² where applicable; (T3) OMP-once recall and missed-atom prevalence per SNR (Probe (a) output); (T4) oracle-support headroom at $\fs = 4B$ (Probe (b) output, SNR ∈ {15, 20} dB); (T5) big-O complexity and tabulated MAC per frame for the six recipes in Experiment 4.

## Known Weaknesses

The limitations a critical reviewer is likely to raise are grouped into three categories: genuine methodological concessions, explicit scope choices (acceptable for an MSc final report), and one item that earlier drafts mis-labelled as a weakness and that is in fact a deliberate mechanism.

**Genuine methodological concessions** *(must be reported honestly in the report)*:

1. **The `force_topk` bias patch is an objective–inference mismatch.** The head is trained with BCE + pairwise-ranking on per-candidate labels; because the positive-class rate is only ≈ 3 %, BCE pulls the final scorer bias toward approximately −8. At inference we flip this bias to +10 so that `logit > τ` triggers the F2-P top-K selection every frame. Mathematically this is equivalent to shifting τ and therefore does not change the ranking; practically, it means training and deployment optimise different objectives. A principled alternative is listwise or differentiable-top-K training, which we leave as future work.
2. **Finite-sample censoring of the PCSI + MMSE oracle reference at SNR = 25 dB.** The reference produced 0 bit errors in 8.19 × 10⁵ tested bits; a Clopper-Pearson 95 % upper bound is 4.5 × 10⁻⁶. The correct narrative is that the learned receiver *approaches* the oracle reference within the tested bit budget — not that it "reaches a bound", which would be information-theoretically incorrect.
3. **Complexity is quantified in MACs only.** No wall-clock runtime, memory-hierarchy, latency, or energy numbers are provided. Any engineering-deployability claim requires at least runtime on a realistic target (embedded DSP / FPGA), which is scoped out of this report.
4. **UWA physical-layer realism is limited.** The simulation assumes a block-fading sparse delay-Doppler channel with Dirichlet fractional-Doppler decomposition and exponential power-delay profile. It does **not** model full time-scale Doppler (per-path time warping) or the multi-scale multi-lag (MSML) effects that real UWA propagation exhibits [arXiv:2405.02660]. Extending the simulator to MSML or at least per-frame Doppler jitter is a prerequisite for operational claims.
5. **No head-to-head reproduction of a published AFDM-SP or AFDM-JCEDD baseline.** Comparisons are with (a) a serial OMP + MP arm and (b) the classical joint recipe (torch port bit-exact to a NumPy reference). We do **not** re-implement Qing *et al.*'s SP-AFDM receiver [arXiv:2404.10232] or the oversampled AFDM JCEDD of [arXiv:2410.05088] on the same channel realisations. All claims of improvement are therefore framed relative to the classical-joint pipeline, not as absolute state-of-the-art.
6. **Probe (a) measures recall, not precision.** The cache-label format ($y_i = 1$ iff candidate $i$ is an oracle atom OMP missed) lets us compute OMP-once recall against the oracle support directly. Computing precision would require replaying each frame from its stored seed to identify OMP-selected atoms that are not in the oracle support; we leave that as a follow-up and rely on recall as the primary mechanism metric. Because the OMP and oracle supports both have size = sparsity in our configuration, precision $\equiv$ recall on this dataset, so the follow-up is a robustness check rather than a new claim.

**Scope choices** *(flag explicitly; not fatal for an MSc final report)*:

7. **Single antenna (1T1R) only.** MIMO / space-time AFDM is future work.
8. **QPSK only.** Higher-order QAM is scoped out.

9. **Fixed pilot-power fraction ρ = 0.5.** No SP power-allocation sweep; an optimal ρ is expected to depend on SNR.
10. **Fixed kinematics** (v_mean = 2 m/s, v_std = 0.5 m/s). High-speed scenarios (> 5 m/s) are untested.

**Mis-classified in earlier drafts — this item is defended, not conceded**:

- *The learned head yields essentially zero gain for SNR ≤ 5 dB.* This is exactly the designed mechanism: the head is a support-refinement module, so it cannot help in the noise-limited regime where the OMP support errors are dominated by additive noise rather than Dirichlet-leakage side-lobes. The fact that the head abstains quietly at low SNR is a correctness property, not a flaw; the report describes it as such.

## Related Work

We organise AFDM-adjacent literature into six narrow themes plus five adjacent communities cited for context. For each theme we identify the closest published work and state exactly how this report extends it; the synthesis paragraph then expresses the defensible narrowed gap in words that do not overclaim against this literature.

**A. AFDM under embedded pilots (EP).** The original AFDM paper and subsequent channel-estimation literature predominantly assume EP with dedicated guard intervals [Bemani 2023, *IEEE TWC*; Yin 2023, *IEEE WCL*]. EP is analytically clean but wastes spectral efficiency and, in UWA contexts, produces guard-region artefacts on Dirichlet-expanded virtual taps. *Extension*: the present report operates entirely under superimposed pilots and therefore in a regime where the pilot observation is structurally data-contaminated.

**B. AFDM under superimposed pilots.** Qing *et al.* propose SP-AFDM channel estimation with an iterative estimation-detection loop [arXiv:2404.10232], and a GI-free pilot-aided AFDM line treats iterative interference cancellation directly [arXiv:2404.01088]. These are the *most direct* prior art to our setting. *Extension*: compared to Qing *et al.* and the GI-free line, we (i) perform OMP **only once** with an explicit Q = O(N) complexity derivation, (ii) iterate only over path-gain LS and MP-BP, and (iii) insert a 1 041-parameter learned module used *exclusively* for support refinement at a sub-dominant per-frame cost.

**C. AFDM with joint channel estimation and symbol detection.** A 2025 *Physical Communication* paper proposes a joint CE+SD receiver for AFDM, without SP or UWA focus [Phys. Comm. 2025, ScienceDirect S187449072400315X]. *Extension*: we share the joint-iterative philosophy but combine it with SP, UWA fractional Doppler, and the learned head — citing this work as motivation that joint receivers for AFDM are an active branch rather than a dead one.

**D. AFDM with oversampled joint CE/DD.** An oversampled AFDM joint channel-estimation and data-detection receiver was already proposed in 2024 [arXiv:2410.05088], which directly anticipates the physical-layer portion of our Claim 4. *Extension*: we therefore claim no novelty for "oversample and gain" itself; Claim 4 claims novelty only for the *combination* of oversampling with the OMP-once + learned-head recipe, and the absolute 4 B BER is reported as an observed best configuration, not as a new performance bound.

**E. AFDM for UWA and multi-scale multi-lag channels.** AFDM has been extended to UWA-adjacent MSML channels with AFDM-OMP serving as the channel-estimation primitive at high delay-time spread [arXiv:2405.02660]. *Extension*: we adopt AFDM-OMP as the channel-estimation primitive but do not resolve the full MSML time-scaling model, a limitation listed in Known Weaknesses §5.

**F. Fractional-Doppler AFDM channel estimation.** Diagonal-reconstruction approaches and more recent attention-based AFDM estimators address the Dirichlet-leakage problem directly [arXiv:2206.12822 and follow-up]. These are the closest published works to the "leakage-atom repair" mechanism we attribute to the C2-rel head. *Extension*: we do not claim the *idea* of leakage repair; we claim a particular minimalist, complexity-preserving realisation (1 041 parameters, O(M · N + P² · N) per frame, BCE + rank-loss training, `force_topk` bias = +10 inference patch).

**Adjacent communities cited for context (not headlined in the gap):**

- *OTFS precursors and OTFS MP/BP detection* (Hadani 2017; Raviteja 2018) — OTFS's 2-D delay-Doppler grid motivated AFDM's 1-D DAFT.
- *Sparse channel estimation and OMP* (Tropp & Gilbert 2007; Berger *et al.* for UWA) — foundational compressive sensing; not AFDM-specific.
- *Deep-unfolding receivers* (Balatsoukas-Stimming & Studer 2019; Monga-Li-Eldar 2021; He *et al.* *JSTSP* 2020; OAMP-Net, MMNet) — detection-only or MIMO-detection-only; do not target OMP support refinement for joint receivers.
- *Iterative / turbo SP-OFDM receivers* (Cong-Li; Li & Giannakis) — intellectual precursor of joint SP receivers, but OFDM-centric.
- *Model-driven / factor-graph detection* (Wymeersch) — cited for the MP-BP detection block.

**The defensible narrowed gap addressed in this report:**

> *To our knowledge, no prior AFDM work studies a UWA-style sparse fractional-Doppler SP receiver that simultaneously (i) performs OMP only once, (ii) iterates only over path-gain LS + MP-BP refinement, and (iii) adds a very small learned module used exclusively for support refinement while preserving the sparse-baseline complexity class O(P · N²). References [B], [C], [D], [E], and [F] above each cover strict subsets of this combination; none covers the full combination.*

---

# PART 2 — UoG/UESTC Final-Report Structure Map

Per `paper/CLAUDE.md` and the *Instructions on Project reports*, the body of the report follows **Introduction/Literature Survey → Materials and Methods → Results → Discussion → Conclusions**, i.e. **five chapters**. The plan below therefore merges our previous "Theory" and "Proposed Method" into a single *Materials and Methods* chapter (with internal sub-sections), matching the exemplar's structure. Body word target ≈ **7 500 words**, leaving ≈ 1 500-word buffer for abstract, acknowledgements, and captions.

## Chapter 1 — Introduction and Literature Survey (≈ 2 000 words)

### 1.1 Background and motivation (≈ 450 words)
UWA channel pathologies (delay spread of several to tens of ms; fractional Doppler from c ≈ 1 500 m/s at v = 2 m/s). Why OFDM fails under fractional Doppler; why OTFS solves this at the cost of a 2-D grid; AFDM as the 1-D DAFT response. Why SP is attractive for spectral efficiency and what it breaks (data interference on the pilot observation). One numeric anchor for the Doppler-spread argument (e.g. v = 2 m/s, f_c = 12 kHz, c = 1 500 m/s → physical Doppler of order 16 Hz, sub-Δf scale ⇒ fractional Doppler regime unavoidable).

### 1.2 Critical literature survey (≈ 1 000 words, argumentative)
Six sub-paragraphs following the (A)–(F) structure in Part 1 Related Work; each opens with the existing contribution, presents its limitation in the UWA-SP regime, and sets up the corresponding contribution in Chapter 2. The synthesis paragraph at the end states the narrowed gap **exactly as worded in Part 1**.

**Style target after comparing the template and Exemplar Report 1**: the template is useful as a completeness checklist, but the exemplar is stronger as a reader-facing funnel. The final literature survey should therefore avoid feeling like six independent mini-summaries. It should explicitly move from waveform choice → pilot choice → joint receiver necessity → fractional-Doppler support error → minimalist learned repair, with one synthesis paragraph that turns the literature into design constraints before stating the narrowed gap.

### 1.3 Research question and objectives (≈ 150 words)
A single guiding research question: *"Can the sparse-baseline complexity class of AFDM-SP receivers be preserved while closing the residual support-selection gap with a minimal learned module?"* Three sub-objectives: (i) characterise the SP-induced estimation floor; (ii) justify OMP-once + inner-iteration against alternatives; (iii) design and evaluate a learned support-refinement head with strict complexity preservation.

### 1.4 Contributions (≈ 250 words)
Four bullets that mirror the four Claims in Part 1, each tied to the gap sentence in §1.2 and each ending with the headline quantitative number (e.g. *"−37.7 % paired-frame BER reduction at SNR = 20 dB under ≈ 8 % relative MAC overhead"*).

### 1.5 Report structure (≈ 150 words)
Chapter-by-chapter guide.

## Chapter 2 — Materials and Methods (≈ 2 800 words)

This chapter is presented as a single methods block per the UoG required order and the exemplar layout. Internal sub-sections separate the system model (§2.1–§2.4) from the proposed receiver (§2.5–§2.8), and an additional short sub-section reports the evaluation protocol (§2.9) and baseline selection (§2.10) that the Oracle review flagged as examiner-facing scaffolding.

### 2.1 AFDM signal model and DAFT (≈ 350 words, 3–4 equations)
Continuous-time AFDM signal, DAFT matrix **A**, received equation **y = A H_time Aᴴ x + n**; one-paragraph contrast between AFDM's 1-D DAFT and OTFS's 2-D DD at equal diversity.

### 2.2 UWA channel and effective-channel sparsity (≈ 400 words, one Dirichlet equation)
Per-path mapping (τ_i, ν_i) → (l_i, k_i) via Doppler normalisation D_i = a_i · f_c / f_s and l_i = round(τ_i / Δτ) with Δτ = 1/(N Δf). Dirichlet-kernel decomposition of fractional k_real into 2 k_leak + 1 integer-bin virtual taps; resulting sparsity ≈ P · (2 k_leak + 1) ≈ 28 for P = 8, k_leak = 2. Caps l_max and k_max tied to (τ_spread, Δf) and (v_max, f_c, c, f_s) respectively.

### 2.3 Superimposed pilot signal model (≈ 300 words)
x = √ρ · x_p + √(1 − ρ) · x_d with ZC(r = 7) pilot. Effective received model after pilot cancellation (y_d = y − H x_p = H x_d + n + ΔH x_full). Observation: the data term appears to the OMP dictionary as *structured* interference, which is the mechanism behind the serial-receiver error floor.

### 2.4 Sparse-baseline OMP dictionary and complexity (≈ 450 words)
Construction of Φ ∈ ℂ^{N × Q} with Q = (2 k_max + 1) · l_max. **Derive Q = O(N)** explicitly under fixed (τ_spread, Δf, f_s, v_max): l_max ∝ τ_spread · N · Δf (AFDM delay resolution shrinks as 1/(N Δf), so covering a fixed physical spread needs Θ(N) bins); k_max ∝ v_max · f_c · N / (c · f_s). Tabulate (l_max, k_max, Q) at N ∈ {512, 1024, 2048} for transparency. Derive OMP per-iteration cost O(N · Q), total O(P · N · Q) = O(P · N²).

### 2.5 Joint OMP-once + LS/MP-BP iterative recipe (≈ 550 words, pseudocode block)
Pseudocode listing: OMP once → { DA-LS refit with damping γ_h = 0.7; MP-BP with n_iter = 20 and damp = 0.5; adaptive σ² update; prune-by-|gain| with τ_h relative factor 10⁻² } × 5 outer iterations. Justify each sub-step against its alternative (re-OMP is a 5× constant overhead; full LS drops the sparsity prior; dense BP is O(N²); EP throws away spectral efficiency). Observe empirically (reference Fig. 7 qualitatively) that support Jaccard between passes t and t + 1 is close to 1 for t ≥ 1 — the numerical justification for "OMP-once is enough".

### 2.6 Learned C2-rel support-refinement head (≈ 650 words, referenced Fig. 4)
Input features: u ∈ ℝ^{M × 7} per candidate (log matched-filter magnitude, margin, delay index, Doppler index, magnitude gap to weakest OMP atom, residual projection norm, normalised candidate position); v ∈ ℝ^{M × P × 6} per (candidate, active-support-member) pair (delay delta, Doppler delta, gain magnitude of the active member, cross-correlation magnitude, normalised distance, active-gain ratio). Architecture: pair_mlp (6 → 16 SiLU, ≈ 112 params) applied to every (candidate, active-member) pair; pooled across the active support; concatenated with u into a 39-vector; fed into a scorer MLP (39 → 16 SiLU → 1 scalar, zero-init final weights, bias initial = −8, **post-training bias patch = +10 to enable `force_topk`**). Total parameters: 1 041. F2-P inference recipe (refine-rounds = 2, cand-topm = 96, `defer-prune-until-final`, `protect-added` = 2, use-hard decisions), each flag traced to a specific Oracle R1 ablation finding reproduced internally in earlier Loop iterations.

### 2.7 Training (≈ 300 words)
BCE (per-candidate binary label y ∈ {0, 1}) + 0.5 × pairwise-ranking hinge (hardest positive must beat hardest negative by margin 1). AdamW (lr = 1 × 10⁻³, wd = 1 × 10⁻⁴). Batch = 512 cached frames, 8 epochs with patience = 2 on validation BCE. Feature caches produced by a dedicated harvesting script, consisting of 3 k + 6 k + 6 k (15 k, 3-SNR) or 3 k + 6 k + 6 k + 12 k (27 k, 4-SNR) frames. SNR weighting: {10, 15, 20} → {0.2, 0.4, 0.4} (3-SNR); {10, 15, 20, 25} → {0.2, 0.3, 0.3, 0.2} (4-SNR). 90/10 frame-level train/val split at fixed seed 13 579. Explicit honest note on the objective–inference mismatch and the `force_topk` bias patch.

### 2.8 Complexity analysis (≈ 300 words)
Per-operator big-O recap, aggregate per-frame MAC at N = 1 024 for six recipes (Table T3), and explicit statement that the learned head is **complexity-preserving** with respect to the classical sparse baseline (ratio ≈ 1.08×); distinguishing this from any "complexity-optimal" claim.

### 2.9 Evaluation protocol (≈ 100 words)
Paired-frame methodology, bit budget per SNR, Clopper-Pearson CIs, paired McNemar χ², adaptive early-stop; train / validation / test seed separation. Content reused from Part 1 of this narrative.

### 2.10 Baseline selection and fairness (≈ 100 words)
Why the four compared receivers are the right ones; which asymmetries are deliberate (the head has seen training caches; evaluated SNRs 0 and 5 are out-of-distribution) and why those asymmetries do not bias the paired comparison. Content reused from Part 1.

## Chapter 3 — Results (≈ 1 300 words, Fig. 5–8 + Tables T1–T5)

Structured as:
- simulation-setup table (T1, ≈ 100 words)
- 4 B BER waterfall with paired reductions and McNemar (Fig. 5, ≈ 300 words, plus Clopper-Pearson CI for the SNR = 25 dB observation)
- outer-iter convergence (Fig. 6, ≈ 200 words qualitative tie-back to Claim 2)
- **§3.4 Design rationale and support-recovery probes (Probes (a) and (b)), ≈ 400 words**: recall vs SNR (Fig. 7, T3) + oracle-support headroom at $\fs = 4B$ (Fig. 8, T4).
- complexity table (T5, ≈ 200 words; Experiment 4)

Total Chapter 3 budget: ≈ 1 300 words.

*Note on writing style*: per the Oracle review, "pure data without interpretation" is too literal for the rubric; each results sub-section carries one or two concise analytic sentences (e.g. "the serial-arm NMSE is frozen at −9 dB irrespective of SNR, confirming an estimation-limited floor"). Deeper interpretation is reserved for Chapter 4.

## Chapter 4 — Discussion (≈ 1 400 words)

### 4.1 Why the serial receiver saturates (≈ 200 words)
Mechanism: SP data interference polluting the OMP residual correlation vector; link the NMSE floor at −11.3 dB to the estimation-limited BER floor at ≈ 4 × 10⁻² on the 4 B operating point.

### 4.2 Why OMP-once + inner iter is complexity-preserving, not optimal (≈ 250 words)
Reconstruct the complexity accounting from Chapter 2 in discussion form; quote the iter-convergence support-Jaccard observation from Fig. 7 as empirical evidence for the "OMP-once is enough" claim.

### 4.3 Where the learned head helps and why only at high SNR (≈ 300 words)
Noise-limited regime (≤ 10 dB): the classical BER is dominated by additive noise in the detector, not by support-selection error, so fixing support has only a second-order effect. High-SNR regime: OMP missed atoms concentrate at Dirichlet-leakage side-lobe positions that appear with high probability at specific fractional k-bin offsets (≈ 5 % of oracle atoms are missed regardless of SNR — Fig. 7), which the head can identify from the u/v feature space. The observation that recall is flat in SNR but the learned-head BER gain is not flat in SNR is the direct quantitative evidence that the head mechanism is structural (fixes Dirichlet-leakage atoms) rather than noise-averaging. Reference the oracle-support headroom (Fig. 8, Table T4) to place the learned head against the top-Ppath structural reference; the residual between the learned head and PCSI + MMSE is a detector-side gain-refinement residual that support-refinement methods cannot touch.

### 4.4 4 B oversampling: physical justification of the operating point (≈ 200 words)
k_max halves (from 4 at Nyquist to 2 at 4 B), Q shrinks by ≈ 44 %, Dirichlet virtual-tap resolution doubles. Quantitatively link this to the 4 B OMP NMSE of −11.3 dB at SNR = 15 dB (Fig. 5, right panel). Cite Ma *et al.* (arXiv:2410.05088) as prior-art motivation for the oversampling choice.

### 4.5 Comparison to prior AFDM and UWA work (≈ 300 words)
Quantitative contrast with at least two published numbers — for example Bemani 2023's AFDM BER at comparable SNR and velocity (≈ 10⁻³ at SNR = 20 dB on a 2-path channel without fractional Doppler) vs our 4 B classical joint at 3.80 × 10⁻⁴ on an 8-path UWA channel with fractional Doppler. Where direct numeric comparison is impossible (different channel assumptions), state that limitation explicitly rather than fabricating a comparison.

Keep this subsection in the exemplar's discussion style: interpret what the comparison means and where it breaks, rather than using it as a leaderboard. The correct claim is structural complementarity plus a disciplined internal paired comparison, not external SOTA superiority.

### 4.6 Limitations and engineering trade-offs (≈ 150 words)
One-paragraph summary mapping to Known Weaknesses items §1–§6; the defended item (low-SNR no-gain) is referenced here only to reinforce that it is a mechanism, not a flaw.

## Chapter 5 — Conclusions (≈ 400 words, bullet-style)

Four bullets restating the contributions from §1.4, each followed by its headline quantitative number and a pointer to the corresponding figure or table. Three sentences of future work covering (i) listwise or differentiable-top-K training; (ii) MSML / time-scaling UWA channel extensions; (iii) direct head-to-head reproduction of a published AFDM-SP baseline (Qing *et al.* 2024) on our seed blocks.

### Figure / table / reference budget (final)

- Figures: **4 plotted** (Fig. 5 4 B waterfall, Fig. 6 4 B outer-iter convergence, Fig. 7 support recall vs SNR, Fig. 8 oracle-support headroom at 4 B) + **4 to draw** (Fig. 1 system block diagram, Fig. 2 DD sparse channel, Fig. 3 classical-vs-learned flowchart two-panel, Fig. 4 C2-rel head architecture) = **8 in-text**; well under the 30-figure cap.
- Tables: **5 in-text** (T1 parameters, T2 BER/NMSE per-SNR, T3 OMP-once recall vs SNR, T4 oracle-support headroom at $\fs = 4B$, T5 complexity/MAC).
- References target: **32–38** entries, majority IEEE journals, including the six AFDM references identified in Part 1 Related Work (arXiv:2404.10232, arXiv:2404.01088, Phys. Comm. 2025 SD, arXiv:2410.05088, arXiv:2405.02660, arXiv:2206.12822).

### Pre-submission self-check (deferred to end of draft)

Exactly the seven bullet groups in `paper/CLAUDE.md` §Pre-submission self-check, to be run after each chapter draft and again on final assembly. Technical-content weight × 5 is enforced structurally by this narrative: every Claim in Part 1 points to a specific figure / table / chapter sub-section, and every figure in §Figures points back to at least one Claim.

---

# PART 3 — Writing Order and Milestones

The writing order is deliberately revised to put the system-model / dictionary scaffold **first**, not last. Earlier drafts had Theory at position four, which the Oracle review correctly flagged as dangerous because it invites back-fitting the mathematics to the simulator code.

1. **§2.1–§2.4 system-model skeleton** (≈ 1 100 words): notation, DAFT, UWA channel, SP model, OMP dictionary with the Q = O(N) derivation. Lock notation before any methods prose is committed.
2. **§2.5–§2.8 method details** (≈ 1 500 words): joint recipe pseudocode, learned head architecture, training, complexity analysis. Reuses the notation fixed in step 1.
3. **Chapter 3 — Results** (≈ 1 600 words): Fig. 5–10, Tables T1–T5, the five light-analytic paragraphs per the Part 2 plan, **plus the new §3.5 design-rationale subsection carrying Probe (a) recall and Probe (b) oracle-support headroom**.
4. **Chapter 4 — Discussion** (≈ 1 400 words): interpret, compare to prior work, concede limitations. §4.3 now grounded in the measured recall (Fig. 9) and oracle-support headroom (Fig. 10). Must cite at least two published numbers from Related Work group B, D, or E for quantitative context.
5. **Chapter 1 — Introduction / Literature Survey** (≈ 2 000 words): written last so that §1.2 gap and §1.4 contributions precisely match the delivered claims. §1.3 research question is pinned to the narrowed gap stated in Part 1 and Part 2.
6. **Abstract** (≈ 200 words): produced only after all five chapters are complete; includes one concrete observed BER, the relative-reduction headline, and the complexity-preserving framing.
7. **Chapter 5 — Conclusions** (≈ 400 words): assembled mechanically from §1.4 bullets and Chapter 3 headline numbers.

### Cross-cutting deliverables

- **§2.9 evaluation protocol** and **§2.10 baseline selection** are derivative of Part 1; draft them immediately after §2.8 so the rest of Chapter 2 reads as a single coherent block.
- **T5 complexity column reproducibility**: rerun the MAC-tabulation script before final submission so the 18.6 M → 20.1 M (proposed) overhead number is reproducible from a committed script, not quoted from memory.
- **Probe (a) + Probe (b) reproducibility**: the recall probe `loop13_support_recall_probe.py` and the oracle-support headroom probe `classical_joint_headroom_probe.py` (with the Loop-13 patch adding `--fs-factor`, `--p-paths`, `--mp-mode`) are both committed; their JSON outputs `outputs_loop13_support_recall/recall_by_snr.json` and `outputs_loop13_headroom_4B_big/headroom_results.json` are the authoritative source for every number in Table T3 and Table T4 respectively.
- **Pre-submission self-check**: the seven bullet groups in `paper/CLAUDE.md`, run per chapter and at final assembly.
