# Insights

## Core Mechanism (Round 8 update — supersedes "capped at 7.5/10" framing)

- The real bottleneck is not feature insufficiency within the 12 receiver-side observables; it is **privileged information**: teacher confidence `|mu_teacher|` is the nearly-perfect beneficial-vs-harmful separator on the disagreement set (bits_pred != bits_teacher), and the old corrector is blind to it.
- Global tail@0.4% ≈ 0.64 matches beneficial/total ≈ 0.63 → 12-feat set is at slice-agnostic Bayes, **but conditioning on teacher `|mu|` strictly reveals higher slice-local ceilings** (|mu|>0.3 → 94% beneficial; |mu|<0.1 → 33% beneficial).
- The headroom gain is not a feature-engineering problem. It is a **fusion problem** between two complementary receivers: the learned CurrentJoint and the classical joint OMP-MP teacher.

## What still fails (confirmed)

- The frozen 12-feature BCE corrector has `slice_AUC ≈ 0.5` on the actionable set: no beneficial-vs-harmful separation. Its `~1e-3` gain is pure prevalence-following, not ranking.
- Observable-side feature additions all failed (F2 neighbour LLR, DAFT residual-patch). Loss redesign (focal, rank, topk_bce) also failed. CJ fine-tune at 10/15 dB just reallocated ceiling between CJ and corrector.

## What now works (new, Round 8)

- **1-parameter teacher-margin gate** `pred → teacher if pred != teacher and |mu_teacher| > τ`:
  - τ* = 0.1 on full-SNR K=10 train cache.
  - 3-seed untouched test gain: **+1.36e-2** BER (12× the frozen corrector's +1.11e-3).
  - Beats rate-matched random flip-on-disagreement by 2-3× at every SNR → margin ranking is causal.
  - Beats unconditional teacher replacement at 5-20 dB (teacher alone +7.94e-3; gate +1.36e-2); matches teacher at 25 dB (teacher already nearly perfect).
- **4-parameter logistic fusion** over `[|mu_teacher|, |LLR_model|, snr_db]` on actionable bits:
  - 3-seed untouched test gain: **+1.46e-2** BER — beats fixed gate by +0.94e-3.
  - Learned weights are physically interpretable: +0.82 teacher-confidence, −0.54 model-confidence, +0.40 SNR, bias +0.525.
  - Biggest margin over fixed gate at 10 dB (+3e-3 on top of the gate).

## Framing Insight (new)

- Paper scope: **"Mechanism-driven fusion of learned and classical AFDM receivers"**. Not "post-hoc corrector". The contribution is:
  1. a causal diagnostic (slice-AUC ≈ 0.5 on 12-feat);
  2. identification of teacher-confidence as the privileged-information axis;
  3. a 4-parameter learned fusion rule that outperforms both single paths and a fixed-threshold gate across 5–25 dB on untouched test seeds.
- The learned receiver is not obsolete at high SNR: at 5–20 dB the fusion STRICTLY beats both classical-only and learned-only. Only at 25 dB does teacher match fusion (teacher at BER 0 on this test size).

## Score progression (Round 8)

- 7.5/10 → **8.4/10** ("Ready for submission" per Codex).
- Remaining nice-to-have (not blocker): zero-shot robustness of learned fusion on existing shift caches (rho=0.4, integer Doppler, higher Doppler, P_paths=15).

## Archived insights (pre-Round-8)



## (Pre-Round-8 archived — still historically valid as scoped to observable-side features)

## What Fails

- Detector-side mean-residual correction is not decision-effective in this AFDM setup.
- Simple linear confidence-style flip gating is also too weak.
- Even on top of the frozen corrector, train-calibrated confidence gating does not improve over the ungated model; the best threshold is `0.5`.
- Per-SNR separate direct-bit probes are worse than the global direct-bit corrector, so the result is not just a trivial SNR lookup.

## What Works

- A lightweight bit-level corrector using only observable receiver trajectory features can recover a small, reproducible subset of beneficial flips.
- The strongest evidence is the frozen train-once/test-on-many evaluation:
  - mean BER gain `1.0590e-03`
  - low cross-cache variance
  - consistent benefits from `10` dB through `25` dB
- The same frozen corrector also survives two meaningful regime shifts:
- The same frozen corrector also survives three meaningful regime shifts:
  - higher Doppler severity: mean gain `8.4310e-04`
  - integer-Doppler structural mode: mean gain `1.3249e-03`, `95% CI [1.1621e-03, 1.4958e-03]`
  - lower pilot-power fraction (`rho=0.4`): mean gain `1.6699e-03`
- The new bootstrap package strengthens the story materially:
  - nominal, Doppler-shift, integer-Doppler, and `rho=0.4` gains all have positive `95%` CIs above zero
  - the `P_paths=15` failure boundary has a clean negative `95%` CI below zero
- Feature-group ablation explains why the method is not just an LLR heuristic:
  - `LLR-only` keeps only `2.1267e-04`
  - the full feature set is best
  - final LLR, `v_x`, `sigma_eff`, and SNR all contribute
- System-level translation is now part of the supported story:
  - the same frozen corrector produces `64`-bit relative goodput gains of about `3.6%` to `5.7%` in the positive regimes
  - the same frozen corrector produces `256`-bit relative goodput gains of about `5.0%` to `11.3%` in the positive regimes
  - this is the first evidence that made the reviewer accept an honest `7.5`

## Framing Insight

- The paper should be framed as diagnostic-plus-method.
- The honest positive claim is modest:
  - not a new receiver architecture
  - a small post-hoc decision corrector with reproducible gains
- Scope limits are now part of the contribution:
  - `P_paths=15` is an explicit failure boundary
  - the method is robust, but not universally robust
  - the remaining criticism is now importance beyond the AFDM-local simulator family, not lack of within-family robustness
  - packet-level utility is endpoint-dependent: harsh BER failure does not necessarily map one-to-one to every short-packet endpoint

## Upgrade Path

- To move beyond low-end `7/10`, the remaining issue was practical significance rather than credibility.
- Safety-first evidence work plus a broader structural transfer axis can still help:
  - packaging moved the score from `7.0` to `7.2`
  - integer-Doppler transfer moved it further to `7.4`
- system-level packet/goodput evidence moved it further to `7.5`
- The cheap calibration space is basically exhausted:
  - confidence gating adds nothing
  - a `5` dB disable rule changes aggregate gain only at the `1e-05` to `1e-04` level
- The next high-value experiments are the ones that either:
  - produce a larger gain with the same frozen idea
  - show transfer outside the current AFDM simulator family
  - or demonstrate stronger deployment realism than the current simple ARQ proxy
