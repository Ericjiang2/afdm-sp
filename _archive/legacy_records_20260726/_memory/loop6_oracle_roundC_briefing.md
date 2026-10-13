# Loop 6 — Round 3 briefing for Oracle (honest null-result at N=1024 + regime study)

Third review in this loop. Your Round-2 warning ("do not oversell the
−1.55 % at 20 dB") was prophetic. Under a fresh seed with McNemar
bit-level paired test, the gain disappears. Below is honest evidence.
We also explored the user's N=256 regime idea and found it is
error-floor dominated by k_max_cap=1, so it does not expose exploitable
headroom. We need your guidance on which parameter lever to pull next.

## What you asked us to run (Round-2 top recommendation)

> "Rerun the N=1024, P=8 hard paired eval at 20 and 25 dB, but log paired
>  discordant outcomes and analyze the paired difference directly."

Done. Added bit-level **McNemar n10 / n01 + one-sided binomial p-value**
to `paired_learned_eval.py`. Identical C1 checkpoint from Round 2.
New seeds (20251, 20252).

### Results — N=1024 v=2 τ=10ms P=8, same C1 ckpt, hard eval

| SNR | Frames | cum_bits | classical BER | learned BER | Δ rel | **McNemar n10** | **McNemar n01** | **p (learned better)** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 dB | 600 | 1 228 800 | 3.270e-03 | 3.272e-03 | **+0.07 %** | 396 | 399 | **0.556** |
| 25 dB | 400 |   819 200 | 7.996e-04 | 7.886e-04 | **−1.37 %** | 136 | 127 | **0.311** |

**McNemar verdict:** learned is *statistically indistinguishable* from
classical at both 20 and 25 dB. The Round-2 −1.55 % @ 20 dB was seed-
dependent noise, not a real effect. You were right to flag this.

## Fix of the 25 dB CI arithmetic error you caught

You correctly noted the Round-2 briefing's prose said Wilson-CI separation
at 25 dB while the JSON audit said not. The briefing was wrong; the JSON
was right. In both the Round-2 results and this Round-3 rerun, **no
SNR is CI-separated at 95 % under Wilson or McNemar.**

Mea culpa — apologies for the discrepancy.

## User's N=256 regime exploration (per your Round-2 approval)

We ran `dead_feature_probe` + identity check at N=256 v=2 P=8:

### Identity check: **PASS** (bit-exact between `heads=()` and `heads=(off_support_corr)` with zero-init at N=256, 9/9 frames).

### Regime observation: **N=256 v=2 τ=10ms is an error-floor regime**.
- `k_max_cap = 1` (vs 4 at N=1024), because scale-invariant Doppler quota
  `N · v · fc / (c · fs) = 0.512` at N=256 (true fractional Doppler!).
- Classical BER at SNR 25 dB ≈ 5–11 % (frame-to-frame noisy). BER
  decreases only 2× from SNR 5 to SNR 25 → classic error floor behaviour.
- `κ = 0.488` (vs 0.048 at N=1024) → the integer-k dictionary is
  structurally unable to represent the true channel.
- **Critical:** the same k_max cap limits C1's dictionary too. Neither
  classical nor learned can push past the floor in this regime.

**So N=256 at v=2 does NOT give the "weak-classical" story you endorsed.
It gives a "both-fail" story.** The lever needs to shift classical, not
wall out both arms with dictionary truncation.

## Where I think headroom might live

Config axes to bend without going "too far" (user's constraint):

| Axis | Value now | Proposed alt. | k_real | κ | Notes |
|------|-----------|---------------|--------|---|-------|
| `v` (m/s) | 2.0 | **2.5** | 2.56 | 0.44 | fractional Doppler at N=1024, dictionary NOT truncated (k_max_cap=5). Classical DA-LS gains bias from fractional-k leakage. Most promising imo. |
| `v` | 2.0 | 1.5 | 1.536 | 0.46 | likewise fractional; lower detector SNR trivially. |
| `ρ` (pilot) | 0.5 | 0.3 | — | — | less pilot energy → noisier OMP → weaker H_hat. Classical pays first. |
| `τ` (ms) | 10 | 20 | — | — | larger l_max tail → more paths to OMP → higher risk classical misses. Adds more support-mismatch opportunity for C1. |
| `P` (paths) | 8 | 12 | — | — | higher sparsity → harder for OMP; but we saw diminishing returns already. |

All other config held fixed. Same C1 head, same training recipe (you
endorsed it in R2). I would NOT combine multiple levers in the first
test: one axis at a time so any gain is attributable.

## Other head families worth trying (user's question)

We have the following heads already in `classical_joint_unrolled.py`:
- `scalars` (5 lam_raw + others) — tested, no gain.
- `strategy` (per-iter MLP multipliers on γ, λ_ls, pic_damp).
- `symbol_refiner` — final-symbol post filter.
- `per_iter_refiner` (B1) — detector-side Δx each outer iter.
- `iter_residual_selector` (B2) — weighted blend of x_soft_history.
- `channel_tap_corrector` (B3) — dead feature, deprecated.
- `off_support_corr` (C1) — your Round-1 recommendation; null at this config.

**User asks:** Should we actually try **B1** (detector-side Δx) now?
You ranked its analogue "per-symbol reliability ensemble" second-best
in Round 1 with live signal under hard eval. User suspects B1 might
have value we haven't explored.

## Questions for you (Round 3)

1. **Given the null McNemar, what parameter lever do you rank highest?**
   Pick one of the alternatives in the table (or propose a different
   small deviation). Briefly why.

2. **Should we train and eval C1 at one alternative lever and then
   compare to N=1024 v=2 directly (two-panel regime plot)?** That matches
   your Round-2 recommendation of a "regime study". Any refinement to
   the story framing to make this honest — especially given one scenario
   (the current v=2) shows null?

3. **B1 revival — worth trying?** Given C1 is inserted CE-side and hits
   an observation-limit wall, does a detector-side `per_iter_refiner`
   (per-iter Δx on x_mp before damping) have an independent error-pool
   to work on, or are the two coupled and equally bottlenecked?

4. **Structural suggestion.** Is there a specific head architecture
   (not in our current list) you would recommend trying at a
   fractional-Doppler regime (v=2.5 say) that you did NOT propose in
   R1 because we were still in an integer-Doppler setup?

5. **Score** this round's *honesty + technical rigor*, separate from the
   result quality. We detected the regression, re-ran with paired test,
   and reported null — give a grade for that discipline.

6. **Next single experiment** to run.

## Supporting numeric evidence

- `figures/loop6/loop6_c1_p8_ber_mse.png` — N=1024 P=8 BER+NMSE (Round-2)
- `afdm_sp_joint_unrolled/outputs_loop6_c1_p8/classical_joint_unrolled_best.pt` — C1 ckpt (iter 39 of 240, best of training)
- `outputs_loop6_c1_p8_mcnemar_snr20/results.md` — R3 null McNemar @ 20 dB
- `outputs_loop6_c1_p8_mcnemar_snr25/results.md` — R3 null McNemar @ 25 dB
- `outputs_loop6_n256_probe_p8/probe_summary.md` — N=256 regime observation
- `afdm_sp_joint_unrolled/dead_feature_probe.py` — probe source
- `afdm_sp_joint_unrolled/classical_joint_unrolled.py` — includes C1 head
- `afdm_sp_joint_unrolled/paired_learned_eval.py` — now with McNemar + paired-t logging

Be brutally honest again. If the right call is "accept the null, publish
pipeline + negative result", tell us. If the right call is "fractional-v
regime", tell us that specifically.
