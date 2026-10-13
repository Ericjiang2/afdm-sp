# Round-1 joint fixed point: why the receiver realises a small effective kappa (first-round derivation)

Date 2026-10-09 (main session, Opus). Round 1 of the theory step; Codex derives independently afterwards.
Builds on `c1-round1-loop-theory.md` (law, V1-V3 outcomes) and Codex eqs 12-20 (exact rewrite of the 20 inner updates,
`.trellis/tasks/10-05-method-advantage/research/20261009-c1-review/CODEX_FIRST_ROUND_INFORMATION_DERIVATION.md`).
Labels: DERIVED, POST-HOC (seen on V2 rows), FROZEN (prediction for the J run below).

## 0. The paradox
V2: nudging the converged channel shows a detector-refit loop gain c = .51-.67 (random directions), above the
single-step bound beta q v. By section 3.3 of the law the round-1 error would then be (1 - c)^-2 = 4-9 times the
independent-error value. The receiver shows 1.2-1.7 times. Section 3.3 is missing a term.

## 1. The round-1 output is a ridge regression on the receiver's own soft symbols (DERIVED)
At a fixed point of Codex eqs 12-20 (damped averages equal their targets: b = b~, a = a~):
- eq 14: s (n0 + a) = Y - B(x) h + b s, so s = (Y - B(x) h) / (n0 + V v), since a - b = V v.
- eq 20: h (K + J_h) = J_h h + B(x)^H s - u N v h, so h (K + u N v) = B(x)^H s.
Together:

    [B(x)^H B(x) + lambda_J I] h* = B(x)^H Y,   x = p + m*,   lambda_J = (n0 + V v)(K + u N v),
    u = 1/(n0 + a),  a = v q + V X + V v,  V = K/(K + u N X).

So the joint receiver ends where an alternating map ends: detector at h*, then a ridge refit on its own soft symbols
with ridge lambda_J. The question becomes: what is the error at that map's fixed point.

## 2. Two coherent terms, one detector property (DERIVED)
Notation: true channel h, Delta = h* - h, W = (B~^H B~ + lambda)^-1 B~^H with B~ = B(p + m), shrinkage beta
(W B(x) ~ beta I for near-orthogonal columns). m_0 = detector output at the true channel; e_0 = data - m_0;
xi_0 = Y - H(h)(p + m_0) = H e_0 + w (plain residual at the true channel).

(a) Image. At channel h* the detector sees Y = H* x + (w - DeltaH x). The channel error acts on its input as an additive
perturbation that lies in the regressor span (DeltaH x = B(x) Delta). Let d_span be the fraction of an in-span additive
perturbation that the soft symbols absorb (the plain residual keeps 1 - d_span of it). Then
xi = xi_0 + d_span B(x) Delta and W xi contains beta d_span Delta. The image includes the pilot-borne part DeltaH p, so no
pilot anchoring: kappa = 1 in the old notation, c = beta d_span.

(b) Fixed point. Delta = W xi_0 - (1 - beta) h + beta d_span Delta, so

    Delta = [W xi_0 - (1 - beta) h] / (1 - beta d_span).

(c) Absorption. The same detector also absorbs the noise. Only the part of xi_0 inside the regressor span reaches the
refit, so the same d_span applies. Bussgang decomposition of the posterior-mean error against the detector's input
noise: e_0 = -d n_r + eps, eps uncorrelated with n_r, Var eps = v (1 - d) (Stein: d = v / sigma_r^2). The thermal noise
in the residual shrinks to (1 - d) w; the symbol-error part H eps is not absorbed further. Per unit of independent-error
residual energy (n0 + q v):

    A(d) = [(1 - d)^2 n0 + (1 - d) q v] / (n0 + q v)          (A_B, "sparse-channel" form).

Dense i.i.d. mixing would absorb the interference as well: A_AMP = (1 - d)^2 (the AMP plain-residual identity).

(d) Orthogonal complement of h:

    e_perp / e_ind,perp = A(d_span) / (1 - beta d_span)^2,

with e_ind,perp = refit error with independent symbol errors of the same true MSE (law 3.1), directions orthogonal to h.
AMP limit (A = (1 - d)^2, beta -> 1): ratio 1, the kappa = 0 decoupling of BiG-AMP state evolution. Old section 3.3
dropped A (A = 1), so it had to shrink kappa to fit. With A_B and beta -> 1 the excess has a closed form:

    e_perp / e_ind,perp = 1 + [q v / (n0 + q v)] * d / (1 - d).

That is the symbol-error share of the residual times the detector's absorption odds. Effective kappa:
1 - kappa_eff beta d = (1 - beta d_span) / sqrt(A).

(e) Along h (complex scale: amplitude and common phase). A scale or phase error of the channel is a scale or phase change
of the observation. QPSK posterior means absorb it weakly, and the pilot pins both. So the loop gain along h is small
and Delta_par ~ -(1 - beta) h + (noise-fitting mean, ~ beta n0 d / (q X~) h). Report-only; the excess sits in e_perp.

## 3. Check on V2 rows (POST-HOC; 8 dB, cell medians)
| rho | L | obs e_perp/e_ind,perp | A_B(d_img)/(1-c)^2 | A_AMP(d_img)/(1-c)^2 | A_B(d_hat)/(1-beta d_hat)^2 | old (1-c)^-2 |
|---|---|---|---|---|---|---|
| .2 | 8 | 1.62 | 1.46 (ln -.10) | 0.93 | 1.29 (-.22) | 4.24 |
| .2 | 24 | 1.45 | 1.28 (-.12) | 0.31 | 1.17 (-.22) | 9.06 |
| .3 | 8 | 1.42 | 1.47 (+.03) | 0.93 | 1.29 (-.09) | 4.47 |
| .3 | 24 | 1.39 | 1.42 (+.02) | 0.50 | 1.19 (-.15) | 7.29 |
| .5 | 8 | 1.21 | 1.58 (+.27) | 0.92 | 1.32 (+.09) | 5.64 |
| .5 | 24 | 1.28 | 1.44 (+.12) | 0.68 | 1.20 (-.06) | 5.74 |

d_img = c_hat / beta_hat (probe), d_hat = reported Stein divergence. e_perp from R3 medians, e_ind,perp = matched
independent refit minus its shrinkage bias. The magnitude is right with one detector parameter. The fall with rho is not
reproduced: the predictions are flat. Open.

## 4. J run (FROZEN; written before any J row exists)
Cells: 8 dB rho {.2, .3, .5} x L {8, 24} (c1_boot observations); 6.5 dB rho .3 L {16, 28} (c1_map); 11 dB rho .2
L {8, 32} (c1_boot). Frames 640-679 (not used in section 3). Same receiver, round 1 only.
Per frame at the round-1 output (h*, m*, v*): Codex recursion state; FP identity; Delta split into the complex
span of h and its complement; probes with the fixed-gain detector and the receiver's soft refit. These cover c_perp
(4 random directions orthogonal to h*, |delta|^2 = .05 e*) and c_par (scale and phase of h*). They also cover d_span
(additive in-span perturbation B(p + m*) delta_c, delta_c orthogonal to h*), d_abs (white perturbation of the same
energy, 4 draws each, +/-), and the matched independent refit (amendment 2) split the same way.
Cell statistic: obs = median e_perp / median e_ind,perp; predictions from cell medians (n0 physical, v = median true
MSE x (1 - rho), q = median E_real).
- Q0: Codex eqs 12-20 reproduce the kernel at N = 1024: max |dLLR| <= 1e-8, max |dh| <= 1e-10.
- Q1: FP identity: median |h_ridge(lambda_J) - h*| / |h*| <= .02 in every cell.
- Q2: d_span / (c_perp / beta_hat) in [.85, 1.15] in >= 80% of cells (image = in-span perturbation).
- Q3: |ln(A_B(d)/(1 - c_perp)^2 / obs)| <= .20 in >= 80% of cells, d = c_perp / beta_hat.
- Q4: A_AMP version under-predicts: ln(pred_AMP / obs) < -.25 in >= 80% of cells.
- Q5: c_par (scale and phase) < c_perp / 2 in >= 80% of cells.
- Q6: closed form with the reported Stein divergence, A_B(d_hat)/(1 - beta_hat d_hat)^2: |ln| <= .20 in >= 70% of cells.
- Q7 (expected to fail, open): Q3 predictions reproduce the sign of the rho trend of obs at L8 and at L24 (8 dB).
- Report-only: d_abs vs d_span; joint-ridge (lambda_J) versions of c and e_ind; implied kappa_eff; e* vs e_par + e_perp.
Branches: Q1 fails means the 20-step output is not at the fixed point, and section 1 applies only approximately. Q2 fails
with Q3 passing means the image and the noise see different absorption, and two parameters are needed. Q3 fails means
the two-term structure is wrong. Q6 failing alone means d_span is not the Stein divergence; a model for d_span becomes
round 2.

## 5. What this does not yet give
A closed-form I_1(K) without measured detector responses (needs d_span from scalars: Q6), and the rho trend (Q7). The
pre-registered law of `c1-round1-loop-theory.md` stays the operative predictor until then.

## 6. J-run outcome (2026-10-09; `out/c1jfp/analysis/jfp.md`; 400 probes, 0 error rows; S1 bit-exact; commit 773b2139)
| check | result | verdict |
|---|---|---|
| Q0 Codex eqs 12-20 = kernel at N = 1024 | max dLLR 3.7e-14, dh 2.8e-16 | PASS |
| Q1 FP identity within .02 | 2/10 cells (fp_rel .014-.071) | FAIL |
| Q2 d_span = c_perp / beta within 15% | 3/10 (ratio .70-.99; low at L >= 16) | FAIL |
| Q3 two-term law within ln .20 | 7/10 (need 8); max abs ln .34; median +.05 | FAIL |
| Q4 dense-AMP absorption under-predicts | 10/10 (ln -.27 to -1.72) | PASS |
| Q5 small loop gain along h | 0/10: c_par scale .25-.60, phase .40-.92 | FAIL |
| Q6 closed form with reported Stein d | 7/10 (need 7); median ln -.10, low in 9/10 | PASS |
| Q7 rho trend | predicted rising, observed falling, both L | FAIL (expected) |
Pre-registered branches: Q1 fails, so section 1 holds only approximately (the lambda_J ridge reproduces e* within
1-20% except 11 dB L8, where it is half). Q3 fails, so the two-term structure is not confirmed at the stated precision.
Further facts:
- The parallel direction has a near-neutral loop gain (phase ~.8-.9), yet e_par / e_ind,par is only .9-2.6 (one cell
  20.7). Single-pass probe slopes are not the gains the receiver realises, in any direction.
- One-frame diagnostic by the executor: the recursion does not settle; the per-step change is ~1e-2 even at T = 3000-4000
  for damping .03-.3. The round-1 output is a 20-step transient, not a fixed point. One frame only; to be confirmed.
- White and in-span perturbations are absorbed alike (d_abs / d_span .86-1.0). The refit probe's extra gain over
  beta d_span comes from the refit, not from the detector.
Reading (main session):
1. What holds: noise absorption is real and partial. Dense-AMP absorption is too strong (Q4). Ignoring it, as the old
   section 3.3 did, is 3-6x too weak. The sparse form gives the right magnitude: within |ln| .34 in 10/10 cells with
   probe d, and within .2 in 7/10 with only the reported Stein divergence (Q6). The V2 paradox is resolved at the level
   of magnitude.
2. What fails: the fixed-point premise. Probe slopes overstate realised gains everywhere, worst along the phase
   direction. The likely reason is that the receiver stops at T = 20 in a recursion with slow, near-neutral modes.
   A quantitative law needs the transient (or the attractor statistics), not a fixed point.
3. Status: round 1 explains the order of magnitude of kappa_eff and rules out two closures (no absorption, dense
   absorption). It does not yet give a predictive kappa_eff or the rho trend. The law of c1-round1-loop-theory.md with
   kappa = w stays the operative predictor. Hand-off to Codex: c1-codex-handoff-joint-fp.md.

## 7. Corrections after Codex's independent derivation (2026-10-10; `c1-codex-closure-review.md`)
- Section 1 holds at a fixed point only (Codex J9); T = 20 obeys J6-J8, with four dynamic terms.
- Section 2(a): c = beta d_span is not an identity. A channel change also moves the adjoint term and the precisions, and
  the fixed-gain probe is not the joint detector (J26). Withdrawn from section 6: "the refit probe's extra gain comes
  from the refit, not from the detector".
- Section 2(c): A_B is the Gaussian identity J24 plus the extra assumption that the detector's effective input noise is
  pure thermal noise. Label changed from DERIVED to candidate approximation.
- The J statistic mixes the joint-vs-plain-refit difference with the error-structure effect; J12 separates them per
  frame.

## 8. J12 run (FROZEN 2026-10-10, user said "run"; written before any J12 row exists)
Same 10 cells and frames 640-679 as the J run (identical observations). Per frame: h_T (joint output, T = 20), h_S (plain
soft refit on m_T with v_T, i.e. e_soft), h_I (matched-MSE independent refit), h_o (truth on the DPSS basis), and
P_perp = I - h_o h_o^H / |h_o|^2. Codex J12 vectors: z = P_perp(h_I - h_o), u = P_perp(h_S - h_I), w = P_perp(h_T - h_S).
Also h_T at T = 10/40/80 from the verified recursion, and at T = 20 the four J7 terms and d_dyn, each mapped through
Q^-1, as norms (eps metric) of their P_perp parts.
Cell statistics are sum-based, so they decompose additively: R_X = sum_f |P_perp(h_X - h_o)|^2 / sum_f |z|^2 for X = S, T.
D_reg = R_S - 1 = [sum 2Re z^H u + sum |u|^2] / sum |z|^2 (own vs independent symbols, same plain refit).
D_alg = R_T - R_S = [sum 2Re z^H w + sum |w|^2 + sum 2Re u^H w] / sum |z|^2 (joint algorithm vs plain refit).
The J-run median ratio is reported alongside for continuity.
Decision rule:
- |D_alg| > |D_reg| in >= 7/10 cells: the excess is mainly algorithmic. Stop the search for a scalar-kappa
  mechanism; keep the calibrated kappa = w law.
- |D_reg| > |D_alg| in >= 7/10 cells: the excess is mainly the structure of the receiver's own symbol errors.
  Round 2 models D_reg (J24 / J14 path).
- Otherwise mixed; report and leave the call to the user.
Expectation stated before the run: J-run medians of total errors (not perp, not sums) give e_soft/e_indep_mse above
e*/e_indep_mse in 9/10 cells, so D_reg likely dominates, with D_alg mostly negative.
Report-only: which term carries the fall with rho at 8 dB (sign of the change of D_reg and D_alg from rho .2 to .5 at L8
and L24); e_perp(T)/e_perp(20) for T = 10/40/80; the share of |P_perp d_dyn| in |P_perp(h_T - h_o)|.
Checks: S1 bit-exact vs stored rows; the recursion at T = 20 equals the kernel output (as Q0); J12 identity residual
<= 1e-10 per frame.

## 9. J12 outcome (2026-10-10; `out/c1j12/analysis/j12.md`; 400 frames, 0 error rows; commit 4f3563fa)
Checks all pass: S1 bit-exact; recursion = kernel (3.7e-14); J12 / J8 / J6 / J3 identities <= 1.3e-15; J12 rows reproduce
the J-run e*, e_soft, e_indep_mse exactly.
Decision rule: |D_reg| > |D_alg| in 9/10 cells (need 7). STRUCTURE branch: the excess is mainly the structure of the
receiver's own symbol errors. Round 2 models D_reg. The stated expectation held (9/10).
- D_reg = R_S - 1 = +.29 to +.62. It splits into 2Re z^H u = -.58 to -.83 and |u|^2 = +.92 to +1.39 (units of sum |z|^2).
  Swapping independent symbols for the receiver's own (same plain refit, same true MSE) moves the channel error by a
  vector u as large as the error itself, only partly anti-aligned with it.
- D_alg = R_T - R_S = -.06 to -.27 in 9/10 cells: the joint algorithm removes part of the own-symbol excess that a plain
  refit keeps. The exception is 11 dB rho .2 L8 (+.36), the cell farthest from settling (below).
- rho trend (8 dB): R_T falls with rho at L8 (-.25) and L24 (-.20). The larger part of the fall sits in D_reg at both L
  (-.17 at L8, -.26 at L24); D_alg adds -.08 at L8 and +.06 at L24.
- Finite T: e_perp(40)/e_perp(20) = .64-.98 and e_perp(80)/e_perp(20) = .49-1.00 (total error .36-.98 at T = 80). The
  round-1 output at T = 20 is mid-transient; more inner updates lower the channel error in every cell, most at
  11 dB (to .49 of the T = 20 value) and least at 6.5 dB L28 / 8 dB rho .5 (2-4%). T = 10 is worse than T = 20 by
  .78-4.5x (sum, perp).
- The dynamic term d_dyn (what the fixed-point ridge leaves out) is 12-38% of the perp error at T = 20 (64% at 11 dB L8).
  The largest J7 parts are the residual update and the symbol damping difference.
Reading (main session):
1. Where kappa_eff lives: in how the receiver's own soft-symbol errors enter the refit, not in the joint-vs-plain
   difference. That error structure carries the rho trend. A scalar loop gain does not describe it (sections 6-7). The
   object to model is the own-symbol EIV term (Codex J24 / J14), i.e. D_reg.
2. Separate practical lead: the round-1 budget of 20 inner updates leaves 2-50% of the channel error on the table. A
   larger inner budget is a receiver-side lever on I_1 and so on the round-1 cliff; it needs its own FER test.
