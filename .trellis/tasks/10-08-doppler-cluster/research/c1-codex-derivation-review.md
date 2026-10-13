# Review: Codex independent derivation of the round-1 information model

Date 2026-10-09 (main session, Opus). Object: `.trellis/tasks/10-05-method-advantage/research/20261009-c1-review/
CODEX_FIRST_ROUND_INFORMATION_DERIVATION.md` (commit 8931ccac). Compared with `c1-round1-loop-theory.md` (this folder).

## Verdict
Correct where checked, careful about scope, and useful as an exact reference and as a diagnostic source. It is not a
predictive model of I_1(K): it gives no reduced law, no K-curve and no number checked against SP rows, and it says so.
Complementary to the round-1 law: Codex = exact, non-reduced object; c1r1 = reduced, predictive, partly post hoc
(kappa = w). A reduced law has to approximate Codex's exact object; V2/V3 test whether ours does.

## Checked by hand (all hold)
- Eq 2: `1 - logloss = I(b; L) - E KL(P(b|L) || Q_L)` for uniform bits (cross-entropy = conditional entropy + KL).
- Eq 5: ridge `lambda_K = K (n0 + P_d)` is the flat-prior LMMSE with data as noise. Eq 7: `E[(h0 - h*) d^H] =
  P_d W_p H*`, `E[(h0 - h*) w^H] = n0 W_p`. Eqs 9-11: eigenvalue forms of tr Q_p, tr Q_p^2; with an equal Gram,
  `d_p/N = k beta` (beta = 1/(1 + K s(1)) of our 3.1), so data-signal retention is `1 - k beta (2 - beta)`
  (6.5 dB, rho .3, K 192: .84).
- Eqs 21-22, 25: first inner update (a_0 = P_d q_0 + P_p + P_d because V_0 = 1, v_0 = P_d; the -p is the data-side
  Onsager term). LLR = ratio of quadratic forms in Y.
- Eqs 26-28: ridge normal equation `B_p^H T_p Y = lambda h_0`, first gain update `h_1 = coef * h_0`, negative iff
  `k < (P_d - P_p)/(n0 + P_d)`; bounds .432960 (6.5 dB) and .465935 (8 dB) reproduce.
- Eqs 30-31 (generalised chi-square, rank <= 2K), 32-33 (ratio moments by exponential tilting; complex Gaussian
  fourth moment), 35 (1/ln 2 Lipschitz bound plus Cauchy-Schwarz), 39 (marginal-likelihood Wirtinger gradient;
  `S^-1 B C = B C_post / n0`, `S^-1 Y = (Y - B h_bar)/n0`).
- Eqs 12-20 (exact rewrite of the 20 inner updates) not re-derived line by line; Codex reports 1e-15 agreement with the
  kernel at N = 32, K 8/16/24, T 1/2/4/20.

## Problems (none invalidates the math)
1. Provenance: the numerical checks (1e-15 table) have no saved script; they cannot be rerun from the repo.
2. Eq 34 is the definition of the measured quantity (a Monte Carlo of the receiver). Calling it the "complete
   information model" adds no predictive content beyond simulation.
3. Eq 35 is correct but vacuous here: an RMS LLR error of .5 already bounds |dI| by .72, larger than the MI range in play.
4. Section 5 (exact distribution) is for the first inner update, which is never decoded; its link to the 20-step output
   is unquantified.
5. The phase flip (eq 27) is real inside the kernel: the residual of step 2 uses the undamped h_1 (eq 14), and at
   6.5 dB, rho .3, K 192 (q_0 ~ beta = .634) h_1 ~ -.17 h_0 while the damped mean is h_bar_1 ~ .65 h_0. Its effect
   on I_1 after 20 steps is not shown (monostable convergence and the forgotten warm start suggest it washes out).
6. `E[H* H*^H | geometry] = I` needs unitary ray operators and unit total ray power: true on average; per-frame energy
   varies (our A2 convention uses E_real).

## What it adds to our work
1. Calibration split (eq 2). Our "MI" is MI minus an LLR-calibration loss. The EXIT closure is self-consistent (I* and
   I_1 in the same metric), but the law's output `J_unc(q)` assumes calibrated LLRs, so receiver miscalibration lands
   in the model residual. The first inner step is under-confident by construction (damping factor .3 in eq 25 and the
   prior-sized V_0 = 1 inside D_0); whether the 20-step output is calibrated is unknown. Action: V2 report-only R1
   (best-scale logloss gap).
2. Data leakage into the pilot estimate (eqs 7-10). The pilot-only channel error is correlated with the data being
   detected, so part of the data signal is cancelled coherently instead of acting as independent interference. Our
   link (3.2) assumes independence; at the pilot-only state the absorbed share is ~ k beta (2 - beta) of the
   data-signal energy, not small at K ~ 200. This is the first candidate if V1 fails. Action: V2 report-only R2 (exact
   d_p from the pilot Gram).
3. Route to derive kappa. Eq 7 generalised to soft regressors gives the cross-covariance of the refit error with the
   soft-symbol error, i.e. a derived replacement for the post-hoc H_w. Most valuable lead; to compare with V2's c_hat.
4. Kernel map (eqs 12-20). Shows exactly where the scalar Onsager terms sit (-u V x_bar data side, -u N v h_bar gain
   side, b s_{t-1} residual). The terms are isotropic scalars, which supports 3.4's argument that they cannot remove a
   structured coherent image of dh; eq 39 states the full matrix correction V(C_post). Reference for V2 and for any
   reduced state evolution.
5. Independent agreement on the qualitative mechanism: no closure may drop the cross-correlation terms (our T2 failure,
   kappa > 0). Cross-validation of the mechanism, not of H_w.

## Outcome of the two diagnostics (V2, report-only)
- Calibration (eq 2): round-1 LLR calibration loss .003-.013 bit, LLRs under-confident by 15-32%. Real, small.
- Leakage (eqs 9-10): exact pilot absorption within 3% of k beta; retention .82-.94. At the round-1 output the LMMSE
  link with the measured error is already within .018 bit, so leakage needs no separate link term there.
- V2 rejected the alternating-map self-absorption mechanism; the receiver's effective kappa needs the joint recursion,
  which is Codex's eqs 12-20. That raises the value of the exact recursion as the base for the next derivation.

## Requests to Codex
Save the verification scripts behind the 1e-15 table. Optional next derivation: the soft-regressor version of eq 7 at
the round-1 fixed point, giving kappa without fitting.
