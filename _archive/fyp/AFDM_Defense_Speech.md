# AFDM Transceiver Design for Underwater Acoustic Communication

**Defense speech, English, paired slide-by-slide with `AFDM_Defense_Yikun_Guo.pptx`.**
Target running time: **~13 minutes** (≈ 1700 words). Pace ≈ 130 WPM.
Symbols **[CLICK]** mark slide advances. Bracketed *[stage]* notes are for me only.

---

## Slide 1 — Title (≈ 25 s)

Good morning, everyone. My name is Yikun Guo, and the project I'm presenting today is called
**"AFDM Transceiver Design for Underwater Acoustic Communication."**
The technical contribution is a **low-complexity joint OMP–LS/MP receiver, augmented with a deep-unfolded support-refinement head**.

I'll walk you through it in six pieces — the channel and waveform background, the system model, why an iterative receiver is unavoidable, the two receivers I built, the results, and my conclusions.

**[CLICK]**

## Slide 2 — Outline (≈ 20 s)

These six pieces are the spine of the talk. Sections one and two set up the problem. Section three is the engineering pivot — the moment I had to choose between three plausible iterative recipes. Sections four and five are my two main contributions: a classical joint receiver, and a learned-head version of it. Section six pulls the experimental story together and closes.

**[CLICK]**

## Slide 3 — Why UWA channels are hard (≈ 50 s)

Underwater acoustic channels are difficult for two reasons that almost never co-occur in radio.

First, the **delay spread is enormous** — surface, water-column, and bottom multipath at 4 to 12 kHz acoustic bands push the delay spread to about 10 ms, which means hundreds of resolvable delay bins.

Second, the **Doppler effect is fractional, not integer** — sound travels at 1500 metres per second, so even a few metres-per-second of platform motion gives a relative Doppler around `10⁻³`, three to four orders of magnitude larger than in RF. That fractional Doppler corrupts sub-carrier orthogonality in a way no single-tap equaliser can repair.

Conventional OFDM cannot absorb either pathology cleanly. A cyclic prefix long enough for the full delay spread eats too much spectrum, and even a fraction of a sub-carrier of Doppler is fatal for the orthogonality assumption. **The goal,** which I want you to keep in mind throughout this talk, **is reception that handles BOTH dispersions at low complexity.**

**[CLICK]**

## Slide 4 — AFDM in one chirp-domain effective channel (≈ 65 s)

This is where AFDM enters. AFDM places information on a chirp basis defined by the **Discrete Affine Fourier Transform**, with two tunable chirp coefficients `c₁` and `c₂`. When you choose those two coefficients to align with the channel's delay–Doppler geometry, every physical path collapses into a single localised atom in the chirp-domain effective channel, instead of producing dense leakage as it would in OFDM.

The transmit waveform is the **inverse DAFT** at the top of the slide, and the chirp-domain received vector is just `y = H_eff · x + n`, with Gaussian noise `n`. Note that **when c₁ and c₂ are both zero, the IDAFT collapses to the inverse DFT**, and AFDM degenerates to OFDM — so AFDM is genuinely a strict generalisation.

The right-hand picture shows the consequence I care about most: the chirp-domain effective channel is **sparse**. With eight physical paths and a fractional-Doppler half-width of two, only about 28 virtual taps out of a thousand-cell lattice are non-negligible. **That sparsity is what makes orthogonal matching pursuit a natural channel-estimation primitive** — and it is the prior every receiver in this report builds on.

**[CLICK]**

## Slide 5 — Superimposed pilots and the estimation floor (≈ 75 s)

To save spectrum, I use a **superimposed-pilot frame**, shown at the top of the slide:

> Every chirp sub-carrier carries data and pilot **simultaneously**, weighted by `√ρ` and `√(1-ρ)`. In my evaluation `ρ = 0.5`.

This doubles the data capacity compared with embedded pilots — but it introduces a new problem.

When the receiver projects onto the pilot to start channel estimation, the projection has three terms: the pilot–pilot signal, an AWGN noise term, and the data-interference term `√(1-ρ) · xpᴴ H_eff x_d`. The data interference scales with the channel norm, and **it does not shrink with SNR.**

The practical consequence is on the right: a one-shot OMP+MP-BP receiver — that is, OMP once for channel estimation, then one pass of message-passing detection — saturates at a BER of about **5 × 10⁻²** from 15 dB SNR onwards. The channel-estimation NMSE freezes near −11.3 dB regardless of how clean the noise becomes. **The interference floor — not the noise — is the engineering enemy.**

**[CLICK]**

## Slide 6 — Three iteration options (≈ 65 s)

Because the floor is structured, the receiver must iterate channel estimation and detection. There are three plausible ways to do that.

**Option A — re-run OMP at every outer iteration.** This is the obvious choice and it's what existing SP-AFDM iterative receivers do. The asymptotic complexity is the same, but it costs `5×` per frame at five outer iterations. And empirically, the support Jaccard from one OMP pass to the next is already above 0.94 from iteration two onwards. So you re-solve a near-identical problem five times per frame — pure waste.

**Option B — replace OMP with a dense LMMSE channel estimator.** The complexity is `𝒪(N³)` per frame — at `N = 1024` that is about 145 times the cost of the classical joint receiver, two orders of magnitude too expensive for embedded UWA modems. And it throws away the chirp-domain sparsity prior we just paid for.

**Option C — and the one I propose: run OMP only once, lock the support, and iterate only the cheap downstream blocks** — a damped data-aided least-squares gain refit, plus sparse MP-BP detection on the chirp-domain factor graph. **This stays in `𝒪(P · N²)` — the same asymptotic class as a single OMP pass.** But this is only a sound design *if* the first OMP pass actually finds (almost) all of the support — which I have to demonstrate before I can defend it.

**[CLICK]**

## Slide 7 — Why OMP-once is enough (≈ 50 s)

Here's the direct measurement. I compare the support OMP recovers in a single pass against the full Dirichlet-expanded virtual-tap oracle — that is, every non-negligible virtual tap from every physical path.

The mean recall sits at **about 95 %**, and **it's flat across SNR** from 10 to 25 dB. That flatness is the key fact: the missing 5 % is structural, set by the Dirichlet kernel geometry, **not** by additive noise. Re-running OMP cannot find what isn't in the dictionary's main-lobe pattern.

So Option C is justified empirically: one OMP pass is sufficient for the support, and iterating the cheap LS / MP-BP blocks on top of that locked support is enough.

**[CLICK]**

## Slide 8 — Method 1: classical joint receiver (≈ 80 s)

This is the first deliverable — the **classical OMP-once + iterative LS / MP-BP joint receiver**.

The block diagram on the left is Algorithm 1 in pictures. Inputs go in; OMP runs **once** and produces a support and an initial set of path gains; the data symbols are initialised by an LMMSE solve on that support. Then the dashed outer loop runs five times, doing four things per iteration:

1. **Form a data-cancellation residual** (the equation on the right under the algorithm panel) —
   `r⁽ᵗ⁾ = y − √(1−ρ) · H_eff(ĥ⁽ᵗ⁻¹⁾) · x̂_d⁽ᵗ⁻¹⁾`.
2. **Damped data-aided LS gain refit on the locked support** — the second equation —
   `ĥ⁽ᵗ⁾ = (1−γ_h)·ĥ⁽ᵗ⁻¹⁾ + γ_h · Φ_Ŝ⁺ · r⁽ᵗ⁾`.
3. **Sparse MP-BP detection** on the chirp-domain factor graph for 20 inner iterations with damping 0.5.
4. **Adaptive `σ²` update and gain pruning**, keeping the top-`P` atoms.

After five outer iterations, hard-decide with a Gray-coded QPSK demap.

The bottom row summarises the engineering: per-frame complexity is `𝒪(P · N²)` — **same class as a single OMP**; this receiver recovers two to three orders of magnitude in BER over the one-shot baseline at SNR = 25 dB; and at `N = 1024` the per-frame MAC count is about 18.6 million, against 48.6 million for re-OMP-per-iteration and 2.7 billion for dense LMMSE.

**[CLICK]**

## Slide 9 — Why a learned head: the structural 5 % (≈ 60 s)

Now — the classical receiver still leaves the structural 5 % on the table. What does that residual actually look like?

For each physical path, the fractional Doppler residual `κ` spreads energy onto integer-bin neighbours through the Dirichlet — that's the aliased-sinc — kernel shown on the right. **At the worst-case κ = 0.5, two adjacent integer bins each carry about 41 % of the path's energy**, and the next pair another 4.4 %. These side-lobes are weak but **structurally predictable**: they sit at deterministic `(0, ±1)` Doppler offsets from already-active atoms.

That predictability is exactly what makes the residual learnable. The decision **"is this off-support candidate a Dirichlet side-lobe of an active atom, or just noise?"** is a non-linear ranking problem on an integer `(Δl, Δk)` lattice, conditioned on neighbour gains. Closed-form thresholds on `|Φᴴr|` cannot separate them — but a small learned model can, because the geometry is simple enough that very few parameters suffice. Deep unfolding keeps the resulting receiver small and explainable.

**[CLICK]**

## Slide 10 — Method 2: learned support-refinement head (≈ 60 s)

Here is the second deliverable — the integration diagram.

The receiver stays exactly the same, except for **one slot** at `t = 0`, between OMP-once and the first iteration of the inner LS / MP-BP loop. In that slot I plug in a **learned support head**. It builds residual- and support-derived features for the top 96 off-support candidates, scores them, and **deterministically appends the top 4 atoms** to the active support. The chip row at the bottom summarises it: 1 041 trainable parameters total, an extra 1.5 million MAC per frame, about 8 % overhead — and the receiver stays in the same `𝒪(P · N²)` class as one OMP pass. The head augments OMP-once; **it does not replace it**.

**[CLICK]**

## Slide 11 — Inside the head (≈ 50 s)

Inside, the head has three stages.

For each candidate `i` we build **a 7-dimensional self feature** `u_i` — matched-filter strength, margin against the weakest active atom, normalised lattice indices, residual-normalised projection, candidate rank, and a Dirichlet-neighbour binary flag. For each pair of (candidate, active atom), we build **a 6-dimensional pair feature** `v_{i,s}` — integer offsets `(Δl, Δk)`, the active atom's log-gain and prominence, dictionary coherence, and normalised geometric distance.

A shared **pair encoder MLP** maps `ℝ⁶ → ℝ¹⁶ → ℝ¹⁶` (384 parameters). Its outputs are pooled across the support set with channel-wise max **and** mean — order-invariant, because the support has no canonical ordering. The pooled descriptor is concatenated with the self feature, and a shared **scorer MLP** maps the resulting `ℝ³⁹` vector to a scalar logit (657 parameters). Inference is purely top-K ranking — `K = 4`. Training combines binary cross-entropy with a pairwise hinge.

**[CLICK]**

## Slide 12 — Results: BER waterfall (≈ 70 s)

This is the headline experiment.

The left panel shows the BER waterfall for the four receivers at the `f_s = 4B` operating point. The grey curve — serial OMP+MP — saturates at `≈ 5 × 10⁻²` from 15 dB onwards, exactly the estimation-limited floor we predicted. The blue curve, my classical joint receiver, descends monotonically; by 25 dB it has gained two to three orders of magnitude over the serial baseline. The red curve, the learned-head version, sits **strictly below the blue curve at every high-SNR cell**, producing a consistent visible **≈ 2 dB paired separation**.

The right table — pooled across three independent evaluation seed blocks — gives the per-cell relative gains: **−37.7 % at 20 dB, −40.2 % at 25 dB, −37.6 % at 30 dB**. All three are paired McNemar-significant at `p < 10⁻⁶`. The right-panel NMSE plot tells the same story from the channel-estimation side.

**[CLICK]**

## Slide 13 — Mechanism: how much of the achievable gap is closed (≈ 60 s)

The natural follow-up question is: **how much of the gap is the head actually closing?** I can answer that exactly.

I run a **top-`P` physical-support oracle** — that is, I replace OMP's selected support with the simulator's true main-lobe indices, ranked by gain. This is a valid ceiling for any top-`P` support-refinement strategy on the same dictionary. At 20 dB and 25 dB the oracle reaches censored-zero BER on more than half a million paired bits per cell.

Against that ceiling, the learned head closes
**61 % of the gap at 15 dB, 81 % at 20 dB, and 98 % at 25 dB.**
At the highest SNR, my head sits within a **single percentage point** of the tightest support-oracle ceiling on this dictionary. **That decisively attributes the BER reduction to support refinement** — not to a generic noise-averaging effect.

**[CLICK]**

## Slide 14 — Complexity (≈ 50 s)

Finally, the complexity ledger.

The proposed classical joint costs about **18.6 M MAC** per frame. The learned-head version adds about **1.5 M MAC** on top — a relative overhead of **8 %**. Both proposed receivers stay in **`𝒪(P · N²)`**.

For comparison: re-OMP-per-iteration is 2.6× the cost without changing the asymptotic class, dense LMMSE is **145 × the cost** at `N = 1024`, and the PCSI+MMSE oracle is the same `𝒪(N³)` and not deployable in any case. **The learned head is the only point on this table that delivers a non-trivial BER reduction without leaving the sparse-recovery complexity class.**

**[CLICK]**

## Slide 15 — Conclusions and future work (≈ 55 s)

To summarise the three contributions:

**One — a low-complexity classical joint receiver** for AFDM-SP under a UWA-style fractional-Doppler regime, with two-to-three orders of magnitude of BER recovery over the serial baseline at 25 dB.

**Two — a 1 041-parameter deep-unfolded support-refinement head** that adds a consistent ≈ 2 dB paired BER separation at high SNR, with all three Δ values significant under paired McNemar at `p < 10⁻⁶`.

**Three — a mechanism-grounded explanation**: the first OMP pass already captures ~95 % of the Dirichlet-expanded oracle support, and the learned head closes 61 / 81 / 98 % of the baseline-to-physical-oracle gap. The gain is **attributable** to support refinement, not to anything else.

For future work, I see four natural directions: extending to multi-scale multi-lag UWA channels, replacing the bias-shift inference patch with a properly differentiable top-K loss, running embedded-deployment latency / energy benchmarks, and validating on field-recorded UWA datasets.

**[CLICK]**

## Slide 16 — Thank you (≈ 10 s)

Thank you. I'd be happy to take any questions.

---

## Anticipated questions  *(not part of the speech — for my own preparation)*

- **Why ρ = 0.5?** It minimises the Cramér–Rao bound for SP under equispaced equipowered placement (Cui & Tellambura 2007, Orozco-Lugo 2011), and our sweep confirms it on this UWA configuration.
- **Why no comparison against a learned detector (e.g., AMGNN, DeepSIC)?** Those modify the *detector*; my work modifies the *channel-support-selection step*. Different slot, different ablation. That's the literature gap that motivates the design.
- **What happens at higher path counts (`P_paths > 8`)?** The Dirichlet geometry holds; the support sparsity loosens. The head's training distribution would have to cover that regime — explicitly listed under future work.
- **Why ranking-only deployment with a bias patch?** Practical alignment between BCE training and top-K inference. The patch is rank-preserving and only changes the no-op gate fire rate. A differentiable top-K loss is the principled fix and is acknowledged as future work.
- **`f_s = 4B` instead of `2B`?** Ranasinghe et al. 2024 show that 2× oversampling improves the matched-filter contrast on the chirp-domain dictionary; my own NMSE/BER measurements confirm it. Trade-off: dictionary size grows, but `Q = 𝒪(N)` either way.
- **Why not just use a transformer?** This is a domain where the structural prior (Dirichlet `(0, ±1)` lattice) is strong and well-understood. A 1 041-parameter model that reproduces 98 % of an oracle is tighter and far more deployable than a million-parameter transformer that would over-fit a 27 k-frame cache.

---

## Pacing checklist

| Slide | Target | Hard cap |
|-------|--------|----------|
| 1     | 25 s   | 35 s     |
| 2     | 20 s   | 30 s     |
| 3     | 50 s   | 60 s     |
| 4     | 65 s   | 75 s     |
| 5     | 75 s   | 85 s     |
| 6     | 65 s   | 75 s     |
| 7     | 50 s   | 60 s     |
| 8     | 80 s   | 95 s     |
| 9     | 60 s   | 70 s     |
| 10    | 60 s   | 70 s     |
| 11    | 50 s   | 60 s     |
| 12    | 70 s   | 80 s     |
| 13    | 60 s   | 70 s     |
| 14    | 50 s   | 60 s     |
| 15    | 55 s   | 65 s     |
| 16    | 10 s   | 15 s     |
| **Total** | **~13 min** | **~15 min** |

The whole talk fits comfortably inside 13 minutes if you respect the pacing column, with about 2 minutes of headroom before the 15-minute hard cap. Slides 8 and 12 are your two longest — the rest can absorb the slack if you slip.
