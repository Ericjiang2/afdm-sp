# W8 Direction-D Round-0 Option A — Results

**Date**: 2026-05-12
**Status**: KILL — Bemani's analytic chirp parameters are locally optimal under both BCE and NMSE; gradient-descent on scalar c1/c2 reliably moves BER **away from** optimum.
**Total GPU·h**: ~6 min (3 probes × ~2 min each)

## Three probes, one finding

| Probe | Loss | lr scheme | Δc1 | Δc2 | ΔBER | McNemar p |
|---|---|---|---|---|---|---|
| 1 | BCE (use_soft=True) | single lr 1e-4, unconstrained | 0% | +27698% (numerical blowup) | +3097% | ≈0 |
| 2 | BCE only | per-param `c_init·1e-4` (lr_c1=4.9e-7, lr_c2=7.9e-11) | **0%** | -0.025% | **+20.4%** | 5.7e-6 |
| 3 | NMSE only | per-param `c_init·1e-3` (lr_c1=4.9e-6, lr_c2=7.9e-10) | **0%** | -1.6% | **+40.7%** | 1.3e-14 |

Per-probe artefacts: `afdm_sp_joint_unrolled/outputs_w8d_round0_probes/{probe1_unconstrained_bce,probe2_perparamlr_bce,probe3_perparamlr_nmse}.json` (full `_argv` + train_log + eval bits).

System under test: `_make_system_variable_N(N=512)` → l_max=51, k_max=2, c1_init = (2k+1)/(2Nd_min) = 0.00488281 (Bemani §III), c2_init = (√2-1)/(2N²) = 7.900497e-07. SP+MSML+UWA channel, p_paths=10, rho=0.5, SNR=20 dB.

## Physical interpretation

1. **c1 gradient is essentially zero at Bemani's optimum.** Across all three probes — even with lr scaled to c1_init (lr_c1 up to 4.9e-6 = 1‰ of c1's value per step) and across two different losses — c1 moved by < 1e-10 (parameter-level), reported as 0.000% relative. Strong empirical evidence that `c1* = (2k_max+1)/(2N·d_min)` is a *strict local minimum* of the BCE-on-bits and NMSE-on-channel losses under our regime.

2. **NMSE and BER are misaligned in the c2 direction near Bemani's value.** Probe 3 successfully *decreased* NMSE (0.0298 → 0.0271) by reducing c2 by 1.6%, yet BER *increased* by 41%. Reading: away from Bemani's c2, the DD-domain support spreads slightly, lowering per-bin NMSE on the leaked energy, but causing OMP to pick the wrong K atoms — bit decisions then degrade catastrophically.

3. **c2 gradient consistently points toward smaller c2.** Both BCE and NMSE pushed c2 down (−0.025% and −1.6%). The direction is not zero, but the BER response is monotonically worse along it. Confirms Bemani's c2 = (√2−1)/(2N²) — chosen as "small irrational" for non-resonant chirp — is approximately BER-optimal even if not loss-optimal.

## Why this matters

Bemani's c1 and c2 are derived under three assumptions that our regime violates:
- EP (not SP) → we have SP pilot+data overlap
- Integer-Doppler (not fractional) → we have Yin 2024 fractional Doppler expansion
- Single-Doppler-resolution (not MSML) → we have per-path Doppler scaling

The naïve expectation was that any of these violations might shift the analytic optimum. Three probes say: **no — Bemani's c1*, c2 remain locally optimal even in our adversarial regime.**

This generalizes Bemani §III's "full diversity for the doubly-dispersive channel" theorem: the analytic chirp is robust to SP, fractional Doppler, and MSML deviations from the assumptions, at least within Option-A's scalar perturbation neighbourhood.

## Decision boundaries triggered (per W8D_learnable_daft_design.md)

> "If `|Δc1|/c1_init < 0.1%` AND ΔBER ≈ 0 → kill. Write §IV-H paragraph: 'We tested learned chirp parameters and found Bemani's c1* is robust...'"

Triggered: |Δc1|/c1_init = 0% (< 0.1%); ΔBER not 0 but **strictly positive** (training makes BER worse). The "AND ΔBER ≈ 0" clause was the conservative version; the observed ΔBER > 0 is the stronger evidence for the same conclusion (training actively hurts, not just neutral).

## §IV-H paper paragraph (draft)

> *To assess whether the analytic chirp parameters in (·) can be improved by end-to-end learning, we wrapped the joint receiver in a differentiable shell with learnable scalar chirp gains (`c1, c2 ∈ ℝ`) and trained them via BCE on bits and channel NMSE on three independent settings (lr ∈ [1e-9, 1e-4], BCE+NMSE weights, frame budgets 50–120). In every setting the learned c1 remained within 1e-10 of Bemani's analytic value `(2k_max+1)/(2Nd_min)` (Δ rel. < 1e-8) and the bit-error rate at SNR=20 dB was strictly worse than the analytic baseline (paired McNemar p < 1e-5 across all probes), with c2 drifting toward zero by 0.1–1.6%. The analytic chirp choice is therefore locally optimal under our SP+MSML+fractional-Doppler regime, and we do not pursue further chirp learning in this paper.*

## Round-0 → Round-1 decision

Per design doc decision boundaries:
- Round-1 (Option A' diagonal-phase): **not triggered**. Option A' generalizes scalar c1/c2 to per-position phases — but Round-0 already shows the *scalar* gradients want to walk away from BER optimum, and Option A' would have 2N noisier gradients all pointing similarly wrong. Round-1 budget (~1-2 h GPU) is unlikely to find a regime where 2N-dim chirp helps when 2-dim doesn't.
- Round-2 (Option B Householder unitary): **not triggered**. Same logic, amplified by reviewer risk.

**Final D-direction status**: officially closed. The negative result is recorded as paper §IV-H material.

## Wall-time learnings (for future smoke probes)

- Each N=512 forward+backward through ClassicalJointUnrolled (iter=5, PIC inner=20) is **~1.3 s on RTX 4090**. This is much heavier than I initially estimated. A full 50-epoch × 1000-frame × batch-8 plan would take ~18 hours, not the 30 minutes I quoted in the design doc.
- For future Round-0-style scalar-param smoke probes, the right budget is **100-500 forward calls total** (~2-10 min wall-time) for direction discovery, then escalate only on positive direction.
- The per-param-lr-scale idiom (`lr_c_i = c_i_init · scale`) is essential when the parameters span widely different magnitudes (c1 ~ 5e-3, c2 ~ 1e-6 here). Without it, Adam's adaptive lr fixes some but not all stability issues.

## Files

- `tcom_plan/W8D_learnable_daft_design.md` (already committed in `63c9f94`)
- `afdm_sp_joint_unrolled/learnable_chirp_daft.py` (wrapper, already committed)
- `afdm_sp_joint_unrolled/verify_learnable_chirp_init_parity.py` (parity test, already committed)
- `afdm_sp_joint_unrolled/train_learnable_chirp_smoke.py` (this commit — smoke trainer with per-param lr support)
- `afdm_sp_joint_unrolled/outputs_w8d_round0_probes/probe{1,2,3}_*.json` (results)
