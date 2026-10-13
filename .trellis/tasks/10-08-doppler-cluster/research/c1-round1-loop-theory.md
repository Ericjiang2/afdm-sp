# C1 round-1 joint loop: information law I_1(K) — derivation and verification spec

Date 2026-10-09 (main session, Opus). Canonical spec for the user and Codex; the HTML overview
(`c1-overview.html`, same folder) is a reader's version of this file and defers to it.
Model code: `experiments/headroom_ladder_20261008/c1r1_model.py` (frozen in the commit that adds this file).
Status labels used below: DERIVED (follows from stated assumptions), CHECKED (agrees with stored rows),
POST-HOC (chosen after seeing the stored rows; hypothesis only), FROZEN (prediction for data that do not exist yet).

## 1. Object and why it matters

`I_1(K)` = frame mean of `1 - logloss` of the round-1 decoder-input LLR with a pilot-only start
(= `Phi_K(none)` in `out/c1e`). The EXIT closure (`c1-scalar-closure.md`, 6/6 pass) says:
- round-1 decode succeeds about half the time when `I_1 = I* = .577` (code-only constant, D2), so the R1 cliff is
  `I_1(Kc_R1) = I*`;
- rounds 2..R follow the staircase of the measured return map `Phi_K`, which starts at `I_1`.
So `I_1(K)` is the entry point of every cliff and the one curve still measured, not predicted. This note derives it.

## 2. Setup (round 1 only, code-free)

- `y = H(h) (p + x) + w`, `H(h) = sum_k h_k B_k` (K = 8L DPSS-BEM operators on genie delays), and
  `A(s) = [B_1 s, ..., B_K s]` so that `H(h) s = A(s) h`.
- Physical energies: pilot `rho`, data `a = 1 - rho`, noise `n = 10^(-SNR/10)`, channel `E|h|^2 = 1`,
  flat prior variance `1/K` per coefficient, N = 1024.
- Round 1: pilot-only refit (`mu = 0`) -> `scalar_joint` 20 joint updates -> decoder input.
  `scalar_joint` (`sp_afdm_native_joint_20260921/src/twofft.py:30-80`) is a scalar-variance bilinear message
  passing loop with Onsager-type terms (`ph = z - s*bar`; `rx`, `rh` corrections). It resets the gain variance to
  the prior `1/P` at entry (line 46), so the channel initialisation enters only as a starting mean.

## 3. Derivation

### 3.1 Refit with soft regressors (DERIVED, CHECKED)
Given soft symbols `x^` with normalised MSE `v`: `y = A(p + x^) h + r`, `r = H(x - x^) + w`.
Treat `r` as white with variance `n + a v`; columns near-orthogonal (max |corr| .150), so
`A^H A ~ N (rho + a (1 - v)) I`. The flat-prior LMMSE gain per coefficient is `beta = 1/(1 + K s)` with

    s(v) = (n + a v) / ((rho + a (1 - v)) N),        e_ind(v) = K s / (1 + K s).

`e_ind` holds for any split of the unit channel energy over coefficients: the error of the flat-prior linear
estimator is `(1 - beta)^2 * 1 + K beta^2 s = K s / (1 + K s)`.
Check: `v = 1` (pilot only) reproduces the observed median `eps_ce1` within 3% in 56/56 stored cells.

### 3.2 Detector link (DERIVED)
LMMSE orthogonality: `h = h^ + dh`, `E[h^^H dh] = 0`, `|h^|^2 = 1 - e`. The detector sees
`y - H^ p = H^ x + dH (p + x) + w`: useful energy `a (1 - e)`, interference plus noise `e + n`. Hence

    q(e) = eta a (1 - e) / (n + e).

`eta` = true-H detector efficiency from the frozen T2 rule (non-SP calibration; `e = 0` reproduces the true-H
receiver by construction). T2 used `eta a / (n + e)`; the missing `(1 - e)` matters once `e ~ .2-.4`.
Soft-symbol quality: `v(e) = M_unc(q(e))` (T1 AWGN QPSK curve). Output: `I_1 = J_unc(q(e*))`.

### 3.3 Self-absorption of the channel error (DERIVED)
Linearise the alternating maps (detector, refit) at the fixed point.
- Detector: `x^ = E[x | z]` with equalised `z = x + G dH s + noise`. Stein's identity for Gaussian `z` gives
  `E[d x^_m / d z_m] = Var(x_m | z) / sigma_z^2`, whose mean is `d = q v` (QPSK, per real component).
  So the soft symbols carry a linear image of the current channel error: `delta x^ ~ d G dH s`.
- Refit: that image enters the residual as `-d H G dH s ~ -d A(s) dh`, which lies in the regressors'
  column space; the LMMSE refit returns it with weight `beta`. Hence

      dh_new = c dh + dh_fresh,      c = kappa beta d,  0 <= kappa <= 1.

- At the fixed point the realisation `(x, w)` is the same on every pass, so `dh_fresh` is the same vector each pass and
  amplitudes add: `dh* = dh_fresh / (1 - c)`, giving

      e* = e_ind(v(e*)) / (1 - c)^2           (not 1/(1 - c^2), which needs independent fresh errors).

- Limits. `kappa = 0`: soft-symbol errors independent of the channel error (exact extrinsic / Onsager decoupling, the
  i.i.d.-mixing state-evolution picture; this is the failed T2 structure). `kappa = 1`: posterior soft symbols fed back
  with no correction (full coherent absorption).
- Bracket (parameter-free): `e*(kappa=0) <= eps_det1 <= e*(kappa=1)`. CHECKED: observed median `eps_det1` lies inside
  the bracket in 56/56 cells, under both links.

### 3.4 Surviving fraction: hypothesis H_w (POST-HOC)
`scalar_joint`'s Onsager terms are exact only for i.i.d. mixing. In SP-AFDM the coherent term `d G dH s` is a
deterministic linear image of `dh`, not an incoherent O(1/N) per-symbol term, so the scalar correction removes only
part of it. An errors-in-variables reading: pilot regressors are exact and anchor the refit; the contamination enters
through the soft-symbol regressors, weighted by their share of the refit Gram:

    kappa = w(v) = a (1 - v) / (rho + a (1 - v)).

Provenance: chosen after a per-cell fit of `kappa` to stored `eps_det1` under the T2 link (fitted kappa .31-.97,
median .54, tracking rho).
Not derived line by line from the code. V2 measures `c` directly; V3 tests H_w on cells nobody has simulated.

### 3.5 The law
    G(e) = e_ind(v(e)) / (1 - w(v) beta d)^2,    e* = lim G^t(e_pilot),  e_pilot = e_ind(1),
    I_1(K) = J_unc(q(e*)),                         Kc_R1:  I_1(Kc_R1) = I*.
Inputs: SNR, rho, K, N, `eta` (true-H), T1 curves `M_unc`, `J_unc`, `I*`. No SP row enters.

## 4. Consequences (DERIVED from 3.5 unless marked)

1. Per-coefficient information cost. For small `K s`: `e* ~ (K/N) Lambda_0`,
   `Lambda_0 = (n + a v_0) / ((rho + a (1 - v_0)) (1 - w_0 d_0)^2)` at the true-H SINR `q_0 = eta a / n`.
   It sits between genie data (`n`) and pilot only (`(n + a)/rho`). Example 6.5 dB, rho .3: `Lambda_0 = .99`,
   independent-error value `.49`, pilot-only `3.08`, genie `.22`. Self-absorption roughly doubles the cost of each
   coefficient, so the loop closes 44% of the log gap between pilot-only and genie data instead of 71%
   (8 dB: 55% vs 77%; 11 dB: 73% vs 85%).
2. K/N law. Every term depends on (K, N) only through K/N (`s ~ 1/N`). If `eta` and `kappa` do not depend on N,
   `I_1(K; N) = Psi(K/N)` and `Kc_R1 ~ N`. Conditional; untested (frozen interface hard-codes N = 1024).
3. Monostability. `G` has a single fixed point for every stored (SNR, rho) up to K = 1024 (scan step 16), and
   `G'(e*) <= .75` (median .17), so 20 damped updates converge. Together with the gain-variance reset this explains
   why the channel initialisation is forgotten (WARM_1.0 = FULL). The round-1 loop has no code-free fold in this
   regime. The cliff is a smooth decline of `I_1` crossing a sharp code threshold. The sharpness comes from the code
   (logistic slope ~240 per unit MI, D2), not from the loop.
4. D3 explained. `eps_det1/eps_ce1` rises with K because pilot-only error saturates (`K s/(1+K s)`), while the
   data-aided error grows ~ linearly in K/N and is amplified by falling SINR and by `(1 - c)^-2`.
5. Extension (not done). With a decoder prior of MI `I_ext`: `v <- M_unc(q + q_pr)` and `w`, `d` evaluated with the
   prior. That would give a model of the whole return map `Phi_K`, not only `Phi_K(none)`.

## 5. Retrodiction on stored rows (POST-HOC; `out/c1r1/RETRO.md`)

| check | independent (k=0) | H_w | coherent (k=1) |
|---|---|---|---|
| eps_det1, 56 cells: median ln(pred/obs), LMMSE link | -.54 | +.12 | +.77 |
| eps_det1: fraction abs ln <= .30 | .02 | .79 | .07 |
| I_1 vs Phi_K(none), 12 points (6.5/8 dB, rho .3): max abs error | .184 (too high) | .036 | .179 (too low) |
| Kc_R1, 7 groups: abs ln(pred/obs) | no crossing in 5/7 | .03-.21 | .64-.89 |

Kc_R1 (obs / H_w): 8 dB rho .2 132/118, .3 141/133, .5 100/97; 11 dB .2 190/157, .3 220/178, .5 225/249; 6.5 dB .3 76/62.
H_w is pessimistic at 11 dB with low rho. With the T2 link (no `1 - e`), H_w fits eps better (.95 within .30) but
overstates `I_1` at large K (error up to .081). The LMMSE link is kept because it is derived, not because it fits.

## 6. Prior art (calibrate the distinction; no veto)
- Bilinear message passing and its state evolution under i.i.d. mixing: BiG-AMP (Parker, Schniter, Cevher, IEEE TSP 2014);
  replica analysis of joint channel-and-data estimation (Takeuchi, Vehkaperä, Tanaka, Müller, IEEE T-IT, 2012 — verify).
  These are the `kappa = 0` world.
- Onsager corrections for structured operators: OAMP (Ma, Ping 2017), VAMP (Rangan, Schniter, Fletcher, IEEE T-IT 2019).
- Training cost with K unknowns: Hassibi, Hochwald, IEEE T-IT 2003. Iterative superimposed-pilot receivers and density
  evolution: Liang, Rave, Fettweis (SP-OFDM; closest). EXIT: ten Brink 2001.
- Candidate distinction (unverified): a closed-form round-1 information law for a structured SP-AFDM bilinear loop, with
  an explicit coherent self-absorption factor `(1 - c)^-2` and a K/N load law. Literature check before any novelty
  sentence (Haiku find, Sonnet extract, Opus judge).

## 7. Verification plan (for the user and Codex)

Common rules: dispatch prompts start with `Active task: .trellis/tasks/10-08-doppler-cluster`; code only in
`experiments/headroom_ladder_20261008/`; frozen receiver modules untouched; commit before and after each run; rows stay
remote with md5; every results JSON carries `_argv` and `_config`. `I_1` per cell = frame mean of `1 - logloss` of the
round-1 decoder-input LLR (identical to c1e `mi_in1` for `none`).

### V1 — link check (no new frames; server rows of c1_boot + c1_map, SPg_flat)
Per frame: `q = eta a (E_real - e) / (n + e)` with the frame's `eps_det1` as `e` and realised channel energy `E_real`
(amendment A2 convention); predicted `I = J_unc(q)` vs the frame's round-1 `1 - logloss`. Same with the T2 link
`eta a E_real / (n + e)`.
- Pass: per-cell median abs(I_pred - I_obs) <= .03 under the LMMSE link in >= 80% of cells, and the LMMSE link is closer
  than the T2 link in >= 75% of cells (paired, per frame).
- Fail: the link, not the loop, carries the error; revisit 3.2 before anything else.

### V2 — mechanism probe (6 cells x 40 frames; CPU minutes)
Cells 8 dB, rho {.2, .3, .5} x L {8, 24}; frames 600-639 (disjoint from all stored runs).
1. Run round 1 with `record_states=True`; keep the final `(h*, mu*, v*)` and the detector's final `vr`.
2. Refits with the receiver's own soft refit function on the same `y`:
   `e_soft` with `(mu*, v*)`; `e_true` with true data (`v = 0`); `e_indep` with soft symbols computed from an independent
   AWGN observation of the true data at the SINR that gives the same mean reported variance as `v*`.
3. Linear response: 4 random coefficient-space directions `delta_j`, `|delta_j|^2 = .05 e*`. Run
   `scalar_joint(gain_mode='fixed')` at `h* +- delta_j` (20 updates), refit each,
   `c_hat = mean_j Re<h^(+delta_j) - h^(-delta_j), delta_j> / (2 |delta_j|^2)`.
   Also log `d_hat = mean(posterior variance)/vr` (internal units), `w_hat` = soft-data share of the refit Gram,
   `beta_hat` = realised refit shrinkage.
- P2a: `e_indep` within abs ln <= .20 of `e_ind(v_meas)` (independent-error refit law).
- P2b: `e_soft / e_indep` within 25% of `(1 - c_hat)^-2` (fixed-point algebra).
- P2c: `0 <= c_hat <= beta_hat d_hat` in every cell (bracket).
- P2d (H_w): per cell, median `c_hat / (beta_hat d_hat)` within +-25% of `w_hat`, and it rises as rho falls.
- Branches. P2a-c pass, P2d fails: keep the law with `kappa` measured as one operator constant and drop H_w.
  P2a fails: the refit law is wrong. P2b fails: the deficit is not linear self-absorption (look at soft-symbol
  quality) and the framework is rejected.
- Caveat: the probe measures the alternating detector-refit map, which is the theory's object. The receiver updates
  jointly, so the probe calibrates the theory, not the receiver's dynamics.

V2 amendment (2026-10-09, before any V2 row exists):
- Aggregation (left open above): every P2 quantity is a per-cell median over the 40 frames; P2a, P2b, P2d pass if they
  hold in >= 5 of 6 cells; P2c must hold in all 6. "Rises as rho falls" = monotone in rho at each L.
- Definitions: v_meas = true normalised MSE of the soft symbols used in a refit; e_ind evaluated at the v_meas of the
  independent soft symbols; d_hat = mean posterior variance / detector pseudo-variance 1/J_x; w_hat = ||mu*||^2 /
  (||p||^2 + ||mu*||^2); beta_hat = tr[(B^H B + lambda I)^-1 B^H B] / K for the receiver's own soft refit at (mu*, v*).
- Report-only additions from the Codex review (`.trellis/tasks/10-05-method-advantage/research/20261009-c1-review/
  CODEX_FIRST_ROUND_INFORMATION_DERIVATION.md`): R1 calibration loss of the round-1 decoder-input LLR,
  max_alpha (1 - logloss(alpha L)) - (1 - logloss(L)), alpha on a 41-point log grid [.25, 4]; R2 exact pilot-regression
  absorption d_p/N = tr Q_p / N and data-signal retention 1 - 2 d_p/N + tr Q_p^2 / N (Codex eqs 9-10) vs the
  equal-Gram values k beta and 1 - k beta (2 - beta), beta = 1/(1 + K s(1)).
- Report-only R3 (added after V1 failed its second clause, before any V2 row exists): link geometry at the round-1
  output h*: scale alpha = Re<h*, h> / |h*|^2 and matched energy U = |<h*, h>|^2 / |h*|^2 (eps metric), against the
  LMMSE value E_real - e* (alpha = 1); and I_1 under q = eta a U / (n + E_real - U) next to the LMMSE and T2 links.

V2 amendment 2 (after a 2-frame-per-cell smoke, before the full run; disclosed): the smoke shows c_hat .50-.71 above
beta_hat d_hat (kappa_hat 1.3-2.3) and e_soft/e_indep 1.1-1.7 against (1 - c_hat)^-2 of 4.6-11; the reported v*
overstates the true MSE of mu* (L8 ~ .28 vs .19), so e_indep (matched on reported variance) uses worse symbols than mu*.
P2a-P2d stay binding as written. Report-only additions: (A) e_indep_mse = refit with independent soft symbols whose true
MSE equals v_meas(mu*), fed the same reported variance v* as mu* (only the error structure differs from e_soft);
(B) kappa_eff = (1 - (e_soft / e_indep_mse)^-1/2) / (beta_hat d_hat), and the same with e* in place of e_soft, against
w_hat. Note: frames 600-639 are c1_boot observations (the spec's "disjoint" was wrong; harmless for a probe, and check
S1 uses the stored rows). Working reading before the run: the 20-step detector is itself iterative, so its derivative
exceeds the single-step Stein value q v; the probe's alternating map then over-states the loop gain the joint receiver
actually realises.

### V3 — blind test on new cells (FROZEN in this commit)
Groups: 9.5 dB rho .3, L {8, 12, 16, 20, 24, 28, 32}; 8 dB rho .4, same L; 6.5 dB rho .2, L {4, 8, 12, 16, 20, 24}.
200 frames each, frame offset 3000, arms SPg_flat and A3 (`driver_c1.py`, rounds 2; only round 1 is scored).
`eta` from the new A3 rows via the frozen T2 rule; model `c1r1_model.py`, mode H_w with the LMMSE link.
Reference numbers with interpolated `eta`: `out/c1r1/predictions_fresh.json` (Kc_R1 ~ 163 / 125 / 63).
- P3a: abs(I_1 pred - obs) <= .05 in >= 80% of cells.
- P3b: abs ln(e* / median eps_det1) <= .30 in >= 75% of cells.
- P3c: abs ln(Kc_R1 pred / obs) <= .25 in every group that crosses I* inside the grid.
- P3d: `e*(kappa=0) <= eps_det1 <= e*(kappa=1)` in >= 95% of cells.
- Kill. P3a or P3c fails: drop H_w; the bracket (P3d) is what survives. P3d fails: reject the self-absorption framework.

### V4 — K/N law (deferred; only after V2 and V3 pass)
N = 512 through a non-frozen copy of the receiver; same SNR and rho; test `Kc_R1(512) = Kc_R1(1024)/2` within abs ln <= .15.

### V5 — round-1 monostability (optional, cheap if V3 runs)
WARM_1.0 vs pilot-only start at the largest K of each V3 group: predicted round-1 `I_1` difference <= .01.

## 8. Division of work
Codex or a Sonnet sub-session: V1 (analysis script on server rows), V2 (probe script), V3 (launch + compare script).
Opus: review anomalies, judge V2 branches, decide on H_w and on V4. User: approve runs and any asset-card promotion.

## V1 / V3 outcome (2026-10-09; `out/c1r1/verify/{v1,v3}.md`, script `c1r1_verify.py`; 0 error rows)
- V1 FAIL (second clause). LMMSE link median |I_pred - I_obs| <= .03 in 45/56 cells (.804, bar .80, pass); LMMSE closer
  than T2 in 33/56 (.589, bar .75, FAIL; three readings of "closer" give the same count). Median |err| .0205 (LMMSE)
  vs .0322 (T2); median signed error -.016 (LMMSE under-predicts) vs +.020 (T2 over-predicts). LMMSE wins at larger
  K/N, T2 at small L; 9 of the 11 cells above .03 are at 11 dB. Pre-registered branch: revisit 3.2. Reading: the
  round-1 output is not LMMSE-orthogonal, so the useful energy lies between E - e and E. Report-only R3 in V2
  measures the scale and matched energy directly.
- V3 (20 fresh cells, 200 frames, offset 3000; eta from each cell's own A3 rows, the path reproduces stored eta exactly):
  P3a PASS 20/20 (max |dI_1| .042; H_w low in 18/20, median -.023). P3b PASS 16/20 (median ln(e*/eps_det1) +.21;
  fails 6.5 dB rho .2 L8/L12, 9.5 dB rho .3 L12/L16). P3d PASS 20/20 (bracket). P3c: Kc_R1 ln(pred/obs) with obs =
  FER_r1 .5 crossing, the definition section 5 used: -.247 (6.5/.2), -.057 (8/.4), -.081 (9.5/.3), PASS by .003 in the
  first group; with obs = I_1 crossing I*: -.276 / -.030 / -.096, FAIL. Main-session call: the frozen statistic is the
  section 5 one, so P3c passes and the H_w kill rule does not fire, but with no margin at low SNR and low rho. The
  dispatch prompt, not the spec, introduced the I_1 reading. Realised eta / reference eta .98-1.04.
Reading: blind, the law predicts I_1 to .042 and the parameter-free bracket holds everywhere. H_w over-predicts the
channel error (e* high by ~23%) and the LMMSE link is pessimistic, so the law is biased low, most at low rho and low
SNR, where the flat I_1(K) curve turns a .03 bias into a 25% cliff error. V2 decides kappa; R3 decides the link.

## V2 outcome (2026-10-09; `out/c1v2/analysis/v2.md`; 240 probes, 0 error rows; S1 bit-exact vs stored c1_boot rows)
Binding: P2a PASS 6/6 (independent-error refit law, |ln| .06-.17). P2b FAIL 0/6: e_soft/e_indep 1.10-1.53 against
(1 - c_hat)^-2 of 4.2-9.1. P2c FAIL 0/6: c_hat .51-.67 > beta_hat d_hat .32-.42 (kappa_hat 1.31-2.08). P2d FAIL.
Pre-registered branch: the excess error is not linear self-absorption at the measured loop gain; the self-absorption
mechanism as written in 3.3-3.4 is rejected.
Report-only (amendment 2, R1-R3):
- Matched control: e*/e_indep_mse 1.17-1.65 and e_soft/e_indep_mse 1.22-1.85, i.e. a real excess over independent
  errors of equal true MSE; effective c = 1 - ratio^-1/2 ~ .07-.22. kappa_eff(e*) .56/.53 (rho .2), .41/.37 (.3),
  .29/.21 (.5) at L8/L24: falls with rho, ~ .7 w (w .74/.66, .62/.54, .39/.33).
- Soft symbols are under-confident: reported v* .28-.52 vs true MSE .20-.48.
- R1: round-1 LLR calibration loss .003-.013 bit (best scale 1.15-1.32: under-confident).
- R2: exact pilot absorption d_p/N .048-.147, within 3% of the equal-Gram value; data-signal retention .82-.94.
- R3: at the round-1 output the LMMSE link with the measured e* is within .010-.018 bit; T2 errs by .03-.10 at L24;
  the geometric link adds nothing (U ~ E - e*). The estimate is slightly over-scaled (alpha .93-.97; |h*|^2 > E at L8).
Reading (main session):
1. The alternating detector-refit map has a large coherent gain (c ~ .5-.7, above the single-step bound beta q v:
   the 20-step detector is itself iterative). The joint receiver realises only c_eff ~ .07-.22, so its gain-variance
   and Onsager terms cancel roughly three quarters of that gain. Scalar corrections remove most, not all, of the
   coherent image; the remainder is not set by the alternating map.
2. What survives of the law: refit law 3.1 (P2a), LMMSE link 3.2 where the error is large (R3, V1 at large K/N), the
   bracket kappa in [0, 1] for the receiver's effective kappa (V3 P3d 20/20). kappa = w is an over-estimate (~1.4x) and
   not a mechanism; V3's +23% e* bias and pessimistic I_1 follow from it.
3. Status: the round-1 law is a calibrated predictor (blind I_1 within .042) with one effective constant, not a
   derived mechanism. Deriving kappa_eff needs the joint dynamics (Codex eqs 12-20), not the alternating map.
