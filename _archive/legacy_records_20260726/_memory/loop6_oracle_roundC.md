According to a document from April 21, 2026, the honest call for the current **N=1024, v=2, P=8, τ=10 ms** regime is: **accept the null**. Your fresh paired hard rerun shows learned and classical are statistically indistinguishable at both 20 and 25 dB, and your N=256 probe is not a “weak classical” regime but a shared truncation/error-floor regime where both arms are boxed in by `k_max_cap=1`.

1. **Highest-ranked lever:** `v = 2.5 m/s` at **N=1024, P=8, τ=10 ms, ρ=0.5**, with everything else held fixed.

Why this is my top pick:

* It changes the regime in the direction most aligned with **C1’s actual mechanism**: larger fractional-Doppler mismatch (`κ≈0.44` in your table) **without** collapsing the representable Doppler budget into the N=256-style truncation wall.
* The trainer recomputes `k_max_cap` from `v_mean`, so a `v`-only change is a clean way to alter the geometry while keeping the rest of the pipeline identical.
* C1 is explicitly an **off-support add-a-path** head: it forms a detached data-matched sensing matrix, scores inactive atoms by off-support correlation, and adds candidate path corrections before reconstruction. That is exactly the sort of bias you expect to become systematic when the true Doppler is fractional but still representable by a small neighborhood of integer bins.

Why I rank the others lower for the *next* run:

* `ρ=0.3` mostly adds pilot starvation/noise and can weaken both arms, not specifically the off-support leakage pattern C1 targets.
* `τ=20 ms` and `P=12` raise support complexity/path load, but they entangle multiple failure modes at once and make attribution murkier on the very first regime test.
* `v=1.5` is a reasonable second choice, but `v=2.5` is the stronger, cleaner stressor.

2. **Yes, do the two-panel regime study**, but frame it as **negative control + targeted stress test**, not as “the learned method works here and not there.”

The honest framing is:

* **Panel A:** near-integer Doppler regime (`v=2`, `κ≈0.048`): null under paired hard evaluation.
* **Panel B:** fractional-but-untruncated regime (`v=2.5`, `κ≈0.44`): test whether off-support correction becomes useful when the physics actually create off-grid leakage inside the available dictionary budget.

Two refinements make that story reviewer-safe:

* Keep **N, P, τ, ρ, mp-mode, training recipe, eval mode, and paired test** fixed; vary **only `v`**. The trainer already supports hard checkpoint selection via `--eval-hard` and gate-style checkpointing via `--checkpoint-score gate`, which is the right discipline for this comparison.
* In the figure, headline the **within-panel learned-vs-classical gap** and paired significance, not raw BER across panels. Absolute BER will move when you change regimes; the honest question is whether the head opens a gap *inside* each regime. Your paired evaluator is already set up for that with hard/soft flip control plus bit-level `n10/n01` and one-sided McNemar logging.

If `v=2.5` is also null, I would stop selling C1 as a gain mechanism and keep the whole thing as a strong negative-result/pipeline paper section.

3. **B1 revival: yes in principle, no as the next single experiment.**

Why **yes in principle**:

* B1 is not just a detector-side clone of C1. Its own docstring says it targets “oracle_x headroom”: it runs **inside each outer iteration**, takes `(x_mp_t, residual_t, |h_col|²_t)`, and adds `Δx_t` **before symbol damping** so the next DA-LS update sees cleaner data symbols.
* In the forward pass, B1 literally computes `residual_t = y - H_hat @ (x_pilot + x_mp)` and modifies `x_mp` before the `γ_x` damping update, so it can change the detector-to-estimator feedback loop on the next iteration.

Why **not next**:

* C1 is detached from the LS solve by design: its candidate construction and provisional gains are detached, and it adds `H_corr` after the active-support estimate is formed. So its null result at `v=2` tells you only that **this CE-side off-support correction is not helpful in that near-integer regime**; it does not yet tell you whether the detector-side pool is rich enough to exploit there.
* But if you want to revive the detector-side family after the `v=2.5` C1 test, I would actually rank **B2 ahead of raw B1**. B2 explicitly targets late-iteration overshoot, and your trainer already contains a **best-iterate supervised pretrain** for it using `x_soft_history[t*]` as the target. That is a lower-variance way to test detector-side headroom than throwing B1 first.

So my answer is: **B1 has an independent error pool, but I would not spend the next run on it before testing the fractional-`v` regime.**

4. **Structural head I would recommend for the fractional-Doppler regime:** a **local fractional-Doppler stencil/interpolator head**.

C1 currently treats candidate off-support atoms mostly independently: top-M inactive atoms, provisional gains `b_j`, then a per-candidate scalar modulation via MLP.
That is reasonable, but it is not ideal for true fractional Doppler, where the missed energy is usually a **structured local cluster** across neighboring Doppler bins on the same delay row.

I would try this instead:

* For each active `(l,k)` path after DA-LS, gather a **local neighborhood** on the same delay row, say `Δk ∈ {-2,-1,0,1,2}`.
* Feed the local residual correlations plus current gain/variance/margin features into a shared head.
* Predict either:

  * a **continuous offset** `ε ∈ [-0.5, 0.5]` plus amplitude/phase correction, then spread gain with a fixed interpolation kernel; or
  * a small **complex stencil** over the neighboring integer bins, constrained to be identity at zero-init.

Why this is the right “new” head now:

* Your probe is already instrumented to ask whether the strongest off-support energy sits on **±1/±2 Doppler neighbors** and to compare `|c_act|` against off-support correlation strength. That is exactly the diagnostic you need to justify a neighborhood/stencil head rather than a global candidate list.
* I did not push this in the earlier near-integer setup because with `κ≈0`, there is little reason to spend model capacity on off-grid interpolation. In a `v=2.5` regime, there is.

5. **Honesty + technical rigor score: 9.5/10.**

This round was excellent on discipline:

* You reran with **fresh seeds** and switched from loose BER reading to **paired bit-level McNemar**, which is the correct correction for the oversell risk you had at 20 dB.
* You explicitly corrected the prior **Wilson-CI prose error** instead of burying it.
* You did the **identity check** in the new N=256 regime before interpreting anything learned-side.
* Most importantly, you refused the tempting N=256 story and called it what it is: a **both-fail truncation regime**.

The 0.5-point deduction is only because the earlier prose/JSON discrepancy happened at all. But the way you handled it afterward was exactly what I’d want from a serious group.

6. **Next single experiment to run**

Run **the exact same C1 recipe** at:

**N=1024, v=2.5, P=8, τ=10 ms, ρ=0.5, same mp-mode/pic_damp, same hard checkpoint selection, same paired hard eval.**

Concretely, I would keep:

* the same C1 architecture and zero-init identity discipline,
* `--eval-hard`,
* `--checkpoint-score gate`,
* one-axis-only deviation (`--v-mean 2.5`),
* paired hard evaluation at 10/15/20/25 dB, with the McNemar-heavy frame budget concentrated at 20 and 25 dB if runtime is limited.

My stop rule would be explicit:

* If `v=2.5` produces a real paired gap, you have an honest **regime-conditional** result.
* If `v=2.5` is also null, I would stop iterating C1 and either pivot to **B2-pretrained detector-side selection** or write up the negative result/pipeline rather than keep turning knobs.

That is my brutally honest recommendation: **fractional-`v` regime first, B1 not first, and keep the current `v=2` result as a published null control.**

Based on your Round-3 briefing and the updated code.     
