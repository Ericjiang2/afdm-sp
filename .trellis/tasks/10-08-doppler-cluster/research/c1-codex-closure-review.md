# Review: Codex joint finite-time closure (2026-10-10)

Object: `.trellis/tasks/10-05-method-advantage/research/20261009-c1-review/CODEX_JOINT_FINITE_TIME_CLOSURE.md`, script
`check_joint_finite_time.py`, results `joint_finite_time_checks.json` (commit 38d6678a). Reviewer: main session (Opus).

## Verdict
Correct, reproducible, and the right correction to my round 1. Not a predictive law: it says so and gives none.
Main value: (i) it replaces my fixed-point algebra with exact finite-T identities; (ii) it pins down the hidden
assumptions in my two-term law; (iii) it gives a cheap per-frame diagnostic (J12) that tells which term carries the
excess.

## Checked
- Re-derived by hand: J3 (residual identity from eq 14), J4 (eq 20), J6-J8 (finite-step normal equations with the four
  dynamic terms), J11 (difference of two ridge solutions), J12 (ratio expansion), J21, J23 (non-normal gain), J24
  (Gaussian Stein identity for the residual covariance), J26 (joint vs fixed-gain natural parameters).
- Reran `check_joint_finite_time.py` locally: passed, 1192 checks, 0 failures, 3.5 s; restored the committed JSON
  afterwards. The scripts behind the earlier 1e-15 claims are now saved (closes my earlier provenance request).

## What I accept (corrections to my records)
1. My section 1 ("the round-1 output is a ridge regression") is a fixed-point identity only. T = 20 needs J6-J8; the J
   run's Q1 failure agrees.
2. The fixed-gain probe (V = 0) is not the joint detector (J26), so probe slopes are not joint gains.
3. A channel change is not just an additive observation perturbation. It also moves the adjoint term H(dh)^H s and the
   precisions. So c = beta d_span is not an identity, and my line "the extra gain comes from the refit, not the detector"
   is withdrawn.
4. A_B is J24 plus one extra assumption. J24 gives residual energy = q v + n0 (1 - 2 d_Y), with d_Y the divergence of the
   estimated signal with respect to Y. My A_B equals this exactly when the detector's effective input noise is pure
   thermal noise (n_r = G w, so d = q v / n0); otherwise it does not. Section 2(c) is a candidate approximation, not
   DERIVED.
5. The J statistic compares two estimators: joint h_T against a plain refit h_I. My theory modelled an alternating-map
   output, closer to h_S (plain refit on own symbols). In the J tables e_soft / e_indep_mse is 1.24-2.13 while
   e* / e_indep_mse is 1.18-2.34, so the algorithm-difference term in J12 is large and mostly reduces the error.
6. Scope: the 10-round cliff (K ~ 180) is a finite-round cliff, not T -> infinity. A5 shows start dependence for one
   observation under a genie start, not two asymptotically stable attractors. 1 - logloss is information minus a
   calibration loss.

## Where it stops short
- J17/J22 are exact local response models along a reference trajectory. The "prediction" (central differences shrink
  as eps^2) checks the numerics, not the physics.
- It gives no reduced law and no account of the rho trend. It says the trend needs signed contributions of all terms.

## Next step (main-session judgment)
Run J12 on the J frames: store h_T, h_S, h_I, h_true per frame plus the four J7 terms at T = 20, and h_T at
T = 10/40/80. One rerun of the J probe, about 2-3 server-minutes, no LDPC. It shows whether the excess and its rho trend
sit in the regression change (own vs independent symbols), in the joint-vs-plain algorithm difference, or in their
cross terms. If the algorithm difference dominates, stop the search for a scalar kappa mechanism and keep the calibrated
kappa = w law.
