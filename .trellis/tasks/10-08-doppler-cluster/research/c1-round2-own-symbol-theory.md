# Round 2: the receiver's own symbol errors in the refit (D_reg)

Date 2026-10-10 (main session, Opus). Follows the J12 verdict (`c1-joint-fp-theory.md` section 9): the round-1 excess
is mainly D_reg, the change of the plain refit's error when the receiver's own soft symbols replace independent ones of
equal true MSE. Base: Codex J11, J13, J14, J24, J27 (`CODEX_JOINT_FINITE_TIME_CLOSURE.md`). Labels: EXACT (algebra),
MODEL (assumption stated), FROZEN (prediction for the R2 run, written before any R2 row exists).

## 1. Exact split of the plain refit (EXACT)
Plain refit with a common ridge lambda = K (n0 + v_T): h_X = Q_X^-1 B_X^H Y, B_X = B(p + m_X), X in {S (own m_T),
I (independent m_I)}. True symbols x = p + d, symbol error e_X = d - m_X, truth h_o, H_o = H(h_o),
Y = B(x) h_o + w + r_mis (r_mis = DPSS projection misfit, ~1e-4). Since B(x) = B_X + B(e_X) and B(e) h_o = H_o e:

    h_X - h_o = Q_X^-1 [B_X^H H_o e_X + B_X^H (w + r_mis)] - lambda Q_X^-1 h_o.

Projected on the complement of h_o, with R_X = P_perp Q_X^-1 B_X^H:
noise path n_X = R_X w, symbol path g_X = R_X H_o e_X, bias b_X = -lambda P_perp Q_X^-1 h_o (Codex J13), misfit m_X.
J12's z = n_I + g_I + b_I + m_I and z + u = n_S + g_S + b_S + m_S.

## 2. Three mechanisms in g_S (MODEL)
For independent symbols, e_I is independent of w and has a calibrated posterior-mean error (J27 with its own AWGN draw),
so Re<g_I, n_I> ~ 0 and g_I is a white symbol-error image of energy sigma_I^2.
For the receiver's own symbols, e_S = d - m_T has three parts:
(a) Absorption. m_T is a function of Y, so e_S carries a noise-driven part. By J24 restricted to the regressor span, the
    span component of H_o e_S has projection -d_Y on the span noise. Model: Re<g_S, n_S> = -alpha |n_S|^2, alpha ~ d_span
    (the measured in-span absorption share of the detector, J run M4).
(b) Image. The detector worked at the receiver's own channel h_T. Its channel error enters its input as -dH x and is
    partly absorbed into m_T. That puts a component along Delta_T = P_perp(h_T - h_o) into g_S. Model coefficient
    gamma ~ beta d_span. Codex B notes the adjoint and precision paths are left out, so this is the least certain part.
(c) Intrinsic. What remains is the posterior-mean error not driven by w or the image. By J27, its energy relative to an
    independent error of equal MSE is (1 - d), with d the single-denoiser divergence (reported Stein d_hat). Model:
    |r_S|^2 ~ (1 - d_hat) |g_I|^2, r_S = g_S + alpha n_S - gamma Delta_T (per-frame least squares on [n_S, Delta_T]).
Assumption A1: Q_S ~ Q_I (Gram difference second order), so n_S ~ n_I and b_S ~ b_I. Measured and reported.

## 3. Consequence for D_reg (MODEL)
With A1 and (a)-(c), D_reg = R_S - 1 is
[ (alpha^2 - 2 alpha) |n|^2 + gamma^2 |Delta_T|^2 - 2 alpha gamma Re<n, Delta_T> + 2 gamma Re<n + b, Delta_T>
  + |r_S|^2 - |g_I|^2 - 2 alpha Re<n, b> ] / |z|^2  (sums over frames; cross terms of r_S, g_I with n, b, Delta_T ~ 0).
Absorption lowers D_reg (alpha < 1 gives alpha^2 - 2 alpha < 0). The intrinsic part lowers it by d_hat |g_I|^2. The image
raises it through gamma^2 |Delta_T|^2 and through Delta_T's shared noise component. So the sign and size of D_reg is a
balance between the image and the other two parts. The rho trend should therefore come from the image term:
Delta_T and its noise loading, scaled by gamma.

## 4. R2 run (FROZEN)
Same 10 cells as J / J12 on fresh frames 680-719 (unseen). Per frame, J12 vectors plus n_S, n_I, g_S, g_I, b_S, b_I,
Delta_T, |Q_S - Q_I|_F / |Q_I|_F, and the J-run d_span, d_abs and d_hat measurements (same M4 procedure).
Per-frame least squares of g_S on [n_S, Delta_T] gives alpha, gamma and r_S; g_I is regressed the same way (control).
Predictions:
- P1 (J12 replication): |D_reg| > |D_alg| in >= 7/10 cells on the new frames.
- P2 (absorption): cell median alpha within +-20% of cell median d_span in >= 8/10 cells; independent control
  |alpha_I| <= .05 in >= 8/10.
- P3 (image): cell median gamma within +-30% of beta_hat x d_span in >= 7/10 cells.
- P4 (intrinsic): sum |r_S|^2 / sum |g_I|^2 within +-25% of 1 - median d_hat in >= 7/10 cells.
- P5 (assembly): D_reg rebuilt from section 3 with the predicted coefficients (alpha = d_span, gamma = beta d_span,
  |r_S|^2 = (1 - d_hat)|g_I|^2) and the measured vectors n, b, Delta_T, g_I: |ln((1 + D_pred)/(1 + D_reg))| <= .15 in
  >= 8/10 cells. Accounting check (report-only): the same with the fitted coefficients and the dropped cross terms
  restored must close to <= 1e-10.
- P6 (rho trend, 8 dB): the term carrying most of the fall of D_reg with rho at L8 and at L24 is the image term
  (gamma^2 |Delta_T|^2 plus its noise cross term).
- A1: |Q_S - Q_I|_F / |Q_I|_F <= .05 (median) in every cell; if not, report the Gram-difference term of J11 separately.
Branches: P2 and P4 hold but P3 fails means the image path needs the adjoint and precision terms (Codex B); that is
round 3. P5 fails while P2-P4 hold means the dropped cross terms matter; report them. P2 fails means the
absorption is not the span divergence, and J24 needs the full direction weights (J14).

## 5. What a pass would give
D_reg and its rho trend explained from detector divergences (d_span, d_hat), refit shrinkage beta and the receiver's
own channel error. That is not yet a closed law in (SNR, rho, K/N), because it uses measured d_span and Delta_T. The
closed law is the step after.

## 6. Amendment after the smoke (2026-10-10; 1 frame per cell; before the full run; disclosed)
The smoke shows two defects in section 4.
(i) The least squares on Delta_T is circular. The plain refit on own symbols lands almost on the joint output
(h_S ~ h_T), so g_S ~ Delta_T - n_S - b_S, and the fit returns gamma ~ 1 and r_S ~ 0 by construction. The smoke
indeed gave gamma ~ 1.0 and r_S / g_I .05-.12 at L >= 16.
(ii) A1 is false. |Q_S - Q_I|_F / |Q_I|_F is .08-.50, roughly the random off-diagonal Gram fluctuation of order
sqrt(K/N). The design-change terms (Codex J11) move D_reg by up to .39. That falsifies A1 as a modelling
assumption; it is recorded as such.
Replacement, the counterfactual split of the own-symbol error. Using the fixed-gain detector m_F(h) (same Y, 20 updates):
e_S = (d - m_F(h_o)) + (m_F(h_o) - m_F(h_T)) + (m_F(h_T) - m_T), giving g_S = g_0 + g_img + g_det through R_S H_o.
g_0 is the error at the true channel (absorption plus intrinsic); g_img is the pure channel-error image (same
detector, h_T versus h_o); g_det is joint versus fixed detector at the same channel. The frozen numeric targets and
tolerances are kept and applied to these components:
- P2': alpha_0 = -Re<g_0, n_S>/|n_S|^2 within +-20% of d_span in >= 8/10 cells. Control
  alpha_I = -Re<g_I, n_I>/|n_I|^2 (single regressor) with |median| <= .05 in >= 8/10.
- P3': gamma' = Re<g_img, Delta_T>/|Delta_T|^2 within +-30% of beta_hat d_span in >= 7/10. Also report the share of
  |g_img|^2 not along Delta_T.
- P4': |g_0 + alpha_0 n_S|^2 / |g_I|^2 within +-25% of 1 - d_hat in >= 7/10 (sums over frames).
- P5': D_reg rebuilt with measured n, b and m for both S and I (no A1) and measured g_I and g_det. g_0 and g_img come
  from the predictions: g_0 = -d_span n_S + r with |r|^2 = (1 - d_hat)|g_I|^2 and r orthogonal to everything, and
  g_img = beta_hat d_span Delta_T. Pass if |ln((1 + D_pred)/(1 + D_reg))| <= .15 in >= 8/10. The size of g_det is
  reported.
- P6': which component (g_0 absorption, g_0 intrinsic, g_img, g_det, design) carries the fall of D_reg with rho at 8 dB
  L8 and L24. The model says g_img.
- P1 unchanged. The frozen section-4 statistics are still computed and reported as "frozen version (circular)".

## 7. R2 outcome (2026-10-10; `out/c1r2/analysis/r2.md`; 400 rows, 0 error rows; commit 7e49125d)
Checks all pass: S1, noise reconstruction (1.5e-15), exact refit split, J12 identity, g_0 + g_img + g_det = g_S,
exact attribution closure (<= 5.5e-15).
| test | result | verdict |
|---|---|---|
| P1 J12 replication on fresh frames | 9/10 | PASS |
| P2' absorption alpha_0 ~ d_span | 0/10: alpha_0 .09-.40 vs d_span .24-.65 (~.65x); control alpha_I ok 10/10 | FAIL |
| P3' image gamma' ~ beta d_span | 6/10 (need 7): gamma' .20-.77 vs .24-.49 | FAIL |
| P4' intrinsic (1 - d_hat) | 0/10: .06-.42 vs .56-.76 | FAIL |
| P5' assembled D_reg | 2/10; predicted D low (ln -.07 to -.39) | FAIL |
| P6' image carries the rho trend | L24 yes (1.12 of the fall); L8 no (absorption carries it) | FAIL |
| A1 | falsified (median .315) | - |
Exact attribution of D_reg (measured components, units of sum |z|^2):
- Image +1.00 to +1.56 (+.45 at 11 dB L8)
- Intrinsic -.31 to -1.15
- Absorption -.05 to -.45
- Design (Gram difference) +.12 to +.30
- Detector difference ~0 (+.08 to +.19 at L8 and 11 dB)
At the true channel, the receiver's own error feeds the refit far less than an independent error of equal MSE does
(P4'). The channel-error image then adds more than everything else removes.
Reading (main session): the sign structure is now measured exactly. Image up, absorption down, own-error structure
down, design up. The magnitudes are not set by the detector scalars (d_span, d_hat): three of the four component
predictions fail. A scalar closed form for kappa_eff is not in reach with these quantities. Recommendation: stop the
kappa-mechanism derivation here. Keep the calibrated kappa = w law as the predictor and the exact attribution as the
mechanism record. Codex audit optional, not needed for any current claim.
