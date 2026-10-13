# C1 scalar-closure plan (2026-10-09, main session; pre-registered before T0/T1 outputs exist)

Source of the route: user-approved Claude/Codex exchange; Codex audit `../../10-05-method-advantage/research/20261009-c1-review/REVIEW.md` §C (commit 39eb9885).
Status labels: bistability, strict pilot orthogonality, "AFDM capacity shrinks by kappa" = UNVERIFIED hypotheses / refuted (orthogonality: max |C_ij| .150 on [0,30]).
Claim under test (two layers, Codex C6):
- Main: a scalar feedback map built only from non-SP calibration (fixed code on AWGN; true-H receiver) predicts per-round
  SP errors and a pre-specified reliability boundary without refitting to SP cliffs.
- Mechanism: if that map has two stable fixed points, the real receiver shows initialization dependence on the same
  observation consistent with the predicted basin boundary.

## T-1 Frozen definitions
- Physical normalisation: total TX power 1, data power a = 1-rho, sigma2 = n = 10^(-SNR/10), channel energy E = 1 (expected law).
  Data Es/N0 q_data = a/n. Receiver internally sees the rho=.5 shim (pd = .5); all errors reported in physical units.
- Load k = K/N, K = 8L (genie delays, D = 8 DPSS per tap), N = 1024.
- Error stages per outer round r (driver_c1 eps_of): eps_ce_r = refit output, eps_det_r = after the 20 inner joint updates
  (detector-level, no decoder in the loop within round r), all ||H - H^||_F^2 / N.
- Soft symbols for refit: m = moments(clip(APP, +-20), pd).mu (native_twofft.py:26); reported variance v_rep = pd - |m|^2.
  Detector prior for the next round: clip(check-extrinsic, +-20). Decoder input: clip(detector extrinsic, +-20). BP: sum-product,
  maxiter 50, syndrome early stop, code e1_ldpc n2048 dv3 dc6 seed 20260726 (G sha256 bfd42472...).
- Correctness: round-r decode correct iff coded errors == 0 (NOT syndrome == 0); frame success iff info_errors == 0.
- Endpoints kept separate: (i) model fold k_fold (smooth-curve tangency), (ii) scheduled-receiver FER = .5 crossing at the
  given round count, (iii) old first-pass proxy K*. Never merged into one "K*".

## T0 (screen only; existing c1_boot + c1_map rows on server; no new simulation)
Per (SNR, rho, L), arm SPg_flat (others secondary): stage-error quantiles split by outcome; transitions r1-correct ->
final-correct (rescue / regression); syndrome-zero-but-wrong counts; binned stage maps eps_ce1 -> eps_det1 and
eps_det1 -> eps_ce2 by r1 outcome; log10 eps_det2 histograms; strata by realised energy and A3 outcome. Bimodality is a
lead, not a decision (Codex C1/C6).

## T1 (fixed-code transfer curves; AWGN QPSK; no SP)
Grid q (data Es/N0) dense around the BP threshold. Measure per q: FER, BER, iterations; for channel-LLR (uncoded), APP and
check-extrinsic soft symbols: v = E|d-m|^2, r = E|m|^2, z = E[(d-m)m*], v_rep = E[pd-|m|^2], closure residual
pd - (v + r + 2Re z), calibration v/v_rep; logloss (1 - MI per coded bit) of channel LLR. Outputs M_unc(q), M_app(q),
J_unc(q) = 1 - logloss(q).

## eta rule (frozen before any eta number is computed)
Per cell (SNR, rho, L): eta = J_unc^{-1}(1 - mean_frames A3.r1_ll_in) / q_data. Uses A3 (true H) only; no SP rows.

## T2 model (frozen structure; numbers only after T1)
Two-stage map, physical units, s(v) = (n + a v) / ((rho + a (1 - v)) N), refit F(v) = K s/(1 + K s):
- Inner (code-free): e_{i+1} = F(M_unc(eta a/(n + e_i)) / pd-normalised), iterate from e_ce1 = F(1) to its fixed point
  -> predicted eps_det1.
- Outer: v_r = M_app(eta a/(n + eps_det_r)) -> eps_ce_{r+1} = F(v_r) -> inner (round >= 2 inner with decoder prior is
  approximated by the same inner map started at eps_ce_{r+1}).
- Fixed points / stability of the composite outer map e -> e'; fold = tangency (Codex C3-C4). FER read-out: frame fails
  iff predicted final e above the unstable fixed point; per-frame randomness only through the realised first-pass error
  (empirical eps_ce1 spread), frozen before comparison.
- Predictions (to be frozen in a file before intervention runs): per-cell predicted eps_det1, eps_ce2 mean; fold k;
  FER = .5 crossing per (SNR, rho); basin boundary e_sep(k) for warm starts. Engineering bar |ln(K_pred/K_obs)| <= .15 in
  >= 80% of cells, uncertainty from T1 MC and eta propagated. Passing is not a novelty claim.

## Paired intervention (driver_c1i.py; same observations as c1_map 6.5 dB rho .3)
L in {8, 12, 16, 20, 24} (K/K*_old .48-1.43), frames 0-399. Arms: FULL_R4 (rounds 4; rounds 1-2 must reproduce stored
SPg_flat rows), FROZEN (first refit H^_1 fixed: gain_mode fixed + refit cached, rounds 2), WARM_lambda (first refit output
replaced by (1 - lambda) c^_1 + lambda c_true_proj, lambda in {.25,.5,.75,1}; algorithm unchanged afterwards; rounds 4).
Inner-only (no decoder feedback into estimation) = round-1 decision of FULL. Per round: eps_ce_r, eps_det_r, coded errors.
Genie warm start is a mechanism probe only, never a receiver-performance claim.
Run only after T2 predictions are frozen. Bistability evidence requires: same observation, warm start inside the predicted
good basin stays good through round 4 while pilot-only start stays bad, and the split location matches e_sep(k).

## Kill / demotion rules (Codex C6)
- One-step prediction of eps_ce2 / eps_det_r fails with history-dependent bias -> drop the 1-D closure (feedback gain kept).
- Warm starts that cross the predicted boundary still merge after round 4 -> weaken the bistability claim.
- Only an empirical equivalent-SNR map left -> separate increment review, no Transactions presumption.

## Amendment A1 (2026-10-09, before any T0/T1 output was read)
- Round >= 2 inner stage: detector carries the decoder check-extrinsic prior; Gaussian-approximation combining
  v_inner = M_unc(q(e) + q_pr), q_pr = M_unc^{-1}(v_ext). Reason: the original rule discarded the decoder prior and erased the
  good fixed point in a synthetic unit test (c1_t2_model.py; inner disabled reproduces Codex C5 exactly: FPs e_L stable,
  ~b unstable, e_U stable; pilot-only flip K = N k_- +-1 at 6.5/8/11 dB).
- T1 also records check-extrinsic soft-symbol stats split by decode outcome (two-branch read-out uses v_app|wrong, v_ext|wrong).
- Synthetic check flagged that the code-free inner stage with eta = 1 may be optimistic (pilot-only 0.394 -> 0.054 at
  K = 233, 8 dB rho .3, vs measured ~3x drops). NOT tuned. Pre-registered variants:
  A (primary, zero-SP): everything from T1 curves + eta rule.
  B (secondary, labelled SP-informed): round-1 eps_det1 := observed SP median eps_det1 per cell (pre-decoding state, no SP
    outcome); all later stages as A. First closure check for A = predicted vs observed eps_det1 per cell.

## T0 outcome (screen; out/c1_t0/T0_SCREEN.md) and amendment A2 (2026-10-09, after T0, before T1/T2 numbers)
- 0 regressions (r1 correct -> final fail) and 0 syndrome-zero-but-wrong in every cell/arm; info_errors vs syndrome FER differ
  in 2 frames total. Near the old cliff round 1 almost never decodes (8 dB rho .3 L24: FER_r1 .973, final .424; rescued
  among r1-fail .26-.91 across near-cliff cells) => success near the cliff is decoder-feedback rescue, not first-decode success.
- Decoder-feedback map splits by r1 outcome: r1-correct eps_ce2 ~ .02 flat; r1-fail eps_ce2 ~ .9 eps_det1.
- No separated eps_det2 clusters (screen only; not evidence either way).
- Realised channel energy E_real dominates frame outcome (8 dB rho .2 L24 FER by E tertile .91/.62/.12; eps_ce1 ~ E,
  Spearman ~.8). A2: the per-frame FER read-out uses q = eta a E_real / (n + e) and the refit error for a frame of energy
  E (flat shrinker: e(E) = K(K E + alpha)/(K + alpha)^2, alpha = 1/s at v). E_real is a channel property, not an SP outcome.
  The cell-level mean-field analysis (fold, K_flip) keeps E = 1. A2 is post-T0 and is labelled as such in every report.

## T2 outcome (frozen predictions 1dfb182c vs observed; out/c1_t2/COMPARE.md)
- Variant A (zero-SP) FAILS the first closure check: observed eps_det1 / predicted = 1.55-3.03 (median per group). The code-free
  inner stage is far weaker than "soft symbols as extra pilots".
- Variant B (observed eps_det1) FAILS at the decoder-feedback stage: on r1-fail frames observed eps_ce2 ~ eps_det1
  (6.5 dB L24 .202 vs .206; 8 dB rho .3 L24 .145 vs .170) while AWGN-calibrated v_app|wrong predicts .113 / .062.
  Round-1 FER also under-predicted (6.5 dB L12 obs .654 vs B .317).
- Cliffs: Kc obs / A / B = 134 / 228 / 192 (6.5 dB), 161 / 232 / 216 (8 dB rho .5); A and B predict no crossing up to K 256 at
  8 dB rho .2/.3 (obs 186/201). Kill rule applied: the 1-D error closure is dropped (level bias at both stages; no
  history-dependence test needed to reject it). Feedback gain stays established (T0 rescue).
- Driver smoke (48 frames): round-1 inner loop forgets the injected channel (L24 frame 1: eps_ce1 .37 -> ~0 changes eps_det1
  only .233 -> .225; FER identical for FULL and every WARM_l). Channel is not a persistent state; decoder belief is.

## Amendment A3 (after T2 failure; Codex C3: add a reliability state only after the parsimonious model fails)
- State = decoder belief (MI), not channel error. Measure the SP joint receiver's EXIT curve T_K(I_A): round-1 front state
  replaced by a genie consistent-Gaussian prior LLR of MI I_A on the true coded bits (detector prior AND refit soft
  symbols = moments of that LLR), one round, output MI = 1 - logloss of the decoder-input LLR. Decoder curve D(I) from the
  fixed code on AWGN (check-extrinsic MI vs input MI). Prediction (frozen before the EXIT arm runs on the cliff grid):
  staircase I_0 = 0 -> T_K -> D -> ... ; decode in round r iff T_K(I_{r-1}) >= I* (input MI at AWGN FER .5); Kc_EXIT(R=2).
  Genie prior = component measurement, never a receiver-performance claim.
- Diagnostics from stored rows: SP detector LLR calibration vs A3; P(r1 decode | input MI) for SP and A3 vs AWGN at equal MI.
- Intervention run keeps FULL_R4 (round budget), FROZEN (re-estimation value), WARM_1.0 (init-forgetting at 400 frames);
  WARM_.25/.5/.75 dropped (smoke shows no effect).
- A3 refinement (before any EXIT-arm grid run): decoder curve on AWGN = full BP (<= 50 it) transfer: I* = input MI at FER .5
  = 0.577 (FER .1: 0.606). Round >= 2 feeds the detector prior with check-extrinsic (MI I_ext) and the refit with APP
  (MI I_app > I_ext), so the injection is parametrised by the previous decoder-input MI I_r: prior MI = I_ext(I_r), refit
  LLR = prior + independent consistent Gaussian with total MI I_app(I_r) (T1 "exit" table). Measured return map
  I_{r+1} = Phi_K(I_r) (round-1 decoder-input MI after injection); pilot-only start I_1 = Phi_K(none).
  Frozen prediction rule: iterate Phi_K (linear interpolation in I_r) from I_1; decode at round r iff I_r >= I*;
  Kc_EXIT(R) = K where the R-round staircase crosses I* (linear in K between grid L). Bistability claim requires a stable
  fixed point of Phi_K below I* together with Phi_K(I) > I on an interval reaching I*, i.e. a closed tunnel that a start
  above the unstable point escapes; D2 (decoder closure in MI space for SP inputs) must hold or the AWGN D is not valid.

## Stage diagnostics D1-D3 (stored rows; out/c1_t0/diag/DIAG.md)
- D2 decoder closure HOLDS in MI space: input MI at P(round-1 decode) = .5 is .576-.578 for SPg_flat in every cell
  (8/11 dB, rho .2/.3/.5; 5/6.5 dB), for true-H A3 (.575-.578) and for AWGN (.577-.578, T1). Zero fitted parameters.
  => the old proxy threshold g = 1.37 was a coordinate artefact; the code threshold is universal in MI coordinates
  (I* = .577 from the code alone). SP failure = detector-output MI deficit: near-cliff SP I_in .39-.66 vs A3 .70-.93;
  paired dI -.07 to -.51, growing with K (8 dB rho .3 L16/24/32: SP I_in .597/.486/.394). Caveat: SPg_slep/flat03 at
  11 dB decode at logloss-MI .49-.56 (mis-scaled LLRs make logloss-MI understate usable information); flat arm clean.
- D1: SP LLRs are not over-confident (logloss observed/implied .61-.94; SP mean |LLR| near cliff 1.7-3.2 vs A3 3.5-13.7).
- D3: inner-loop gain weakens with K: median eps_det1/eps_ce1 .16 -> .63 over K 32 -> 256 (8 dB rho .2), ~.42-.56 at
  K/K* ~ 1, and rises with rho at fixed K.
- Consequence: the open problem is now one curve, the SP joint detector's output MI vs K and decoder feedback (return map
  Phi_K, Amendment A3). The decoder side is closed by the code's own AWGN curve.

## Paired intervention outcome (out/c1i/analysis/c1i_analysis.md; 6.5 dB rho .3, frames 0-399)
- FULL_R4 rounds 1-2 reproduce stored c1_map rows exactly (2000 pairs, diff 0).
- Round budget matters strongly: FER R1/R2/R3/R4 = L8 .407/.138/.090/.077, L16 .900/.468/.295/.233, L20 .993/.752/.505/.417,
  L24 1.00/.943/.815/.745; R2 vs R4 McNemar b/c 24-134 / 0 (p <= 1.2e-7). The 2-round "cliff" is largely a round-budget
  boundary; increments shrink (L20: -.24, -.25, -.09) = slow escape, consistent with a narrow tunnel; trap vs slow climb is
  decided by the return map, not by FER alone.
- WARM_1.0 (exact-projection channel start) = FULL within noise at R1-R4 (only L24 R2 p .008, 8/0): channel init forgotten.
- FROZEN (no re-estimation) FER .965-1.00: re-estimation is essential.
- EXIT grid point .40 -> .42 (T1 I_in range starts .414; no extrapolation).

## EXIT return-map outcome (out/c1e/analysis; frames 500-599 disjoint from validation; predictor frozen 9473a774)
Kc = K at which the R-round staircase of the measured return map reaches I* = .577 (AWGN code threshold):
| SNR / round | Kc predicted | Kc observed (source) | ln(pred/obs) |
| 6.5 R1 | 77.7 | 75.7 (c1i FULL_R4, 400 fr) | +.026 |
| 6.5 R2 | 136.4 | 134 [131,137] (c1_map, 1000 fr) | +.018 |
| 6.5 R3 | 158.5 | 159.2 (c1i) | -.004 |
| 6.5 R4 | 180.3 | 168.1 (c1i) | +.070 |
| 8 R1 | 138.8 | 141 (c1_boot) | -.016 |
| 8 R2 | 203.5 | 201 (c1_boot) | +.012 |
Pre-registered bar (|ln| <= .15 in >= 80% of cells) PASSED 6/6. Status label: component-calibrated, not zero-SP: Phi is
measured on the SP receiver (genie consistent-Gaussian decoder beliefs, disjoint frames), decoder side = code-only AWGN
I*; nothing fitted to FER. R1 is near-tautological given D2; the content is the R2-R4 composition (round-budget law).
Tunnel geometry (6.5 dB rho .3): min (Phi - I) on [.42,.57]: L24 +.023 (CI excludes 0, open, slow escape) -> L28 within
+-.011 of the diagonal over .42-.53 (CIs touch it; only I .50 marginally below) = at the tangency. 8 dB L28 still open
(min +.076). => finite-round cliff = narrowing tunnel (slow escape); asymptotic cliff = tangent fold near K ~ 224 at 6.5 dB.
Bistability BEYOND the fold is NOT yet established (needs K > fold, more frames, long runs).
Mechanism statement supported: channel estimate carries no memory (init forgotten); decoder belief is the state; the
code threshold is universal in MI; the SP joint detector's MI transfer Phi_K narrows with K.

## Next object: round-1 loop law (2026-10-09)
Derivation, retrodiction and V1-V5 verification spec in `c1-round1-loop-theory.md` (commit 2d0a2f90); reader's overview
`c1-overview.html`.

## Amendment A4 — fold / bistability run (2026-10-09; user-approved; written before any A4 row exists)
Runs (6.5 dB, rho .3, entropy c1_map, same receiver):
- EXIT-D (dense return map): `driver_c1e.py`, L {28, 32, 36}, frames 1000-1299 (disjoint from every earlier run),
  Ir {none, .42, .44, .46, .48, .50, .52, .54, .56, .58, .60, .62, .65} (T1 range starts .414; no extrapolation).
- FULL-R10: `driver_c1i.py --arms FULL_R10`, L {24, 28, 32}, frames 0-299 (same observations as c1i / c1_map).
Frozen numbers: `out/c1f/predictions_frozen.json` (`c1f_predict.py`, from the old map, frames 500-599):
staircase Kc by round R5..R10 = 187 / 196 / 209 / 210 / 210 / 210; L24 first decode at round 6 (I_6 = .599);
L28 trapped at stable FP .437 with unstable FP .523 (point estimates; old CIs touch the diagonal).
Pre-registered checks:
- A4-0 (determinism): FULL_R10 L24 rounds 1-4 equal the stored c1i FULL_R4 rows frame by frame (cerr, ierr, dsha, ll_in).
- A4-1 (tunnel): min over I in [.42, .57] of Phi_K(I) - I on the dense grid: L28 bootstrap CI contains 0 or lies below 0;
  L32 and L36 have an interval where the upper CI is below 0 (tunnel closed).
- A4-2 (bistability of the map, frozen c1e_predict rule): bistable = True for L32 and L36, i.e. a stable fixed point below
  I* AND Phi > I on an interval between the higher unstable fixed point and I*. CI-robust version: the closed interval and the
  escape interval each have a CI excluding 0. If Phi < I all the way to I*, the map has a single (trapping) state: report
  "no escape region", not bistability.
- A4-3 (trajectories): L24 FER by round decreasing with FER_R10 <= .5. L28 and L32 FER_R10 > .5, and the frame-mean round MI
  (1 - ll_in_r) plateaus (|I_10 - I_8| < .01) within +-.03 of the stable fixed point of the dense map for the same L
  (cross-frame population prediction: map frames 1000-1299, trajectories 0-299).
- Kc by round: FULL-R10 FER .5 crossing in K (L 24/28/32, plus stored L 8-24 R1-R4) vs the frozen staircase, |ln| <= .15.
Scope: a map with two stable states plus stalled pilot-start trajectories is evidence for a bistable map. Same-frame start
dependence (hysteresis) needs injected-start multi-round runs; not in this batch.

## A4 outcome (out/c1f/analysis/c1f.md; row md5 in out/c1f_exit, out/c1f_r10; 0 error rows)
- A4-0 PASS: FULL_R10 L24 rounds 1-4 identical to stored c1i FULL_R4 (300 frames, 0 mismatches, ll_in diff 0).
- A4-1 PASS: tunnel closed with CI at L28 (min Phi-I -.018 [-.023,-.013] at .50; closed .44-.52), L32 (-.044), L36 (-.075).
  The old 100-frame map put L28 at the tangency; 300 fresh frames put it inside the closed region. Mean-map fold between
  K 192 (old L24 open, +.023) and 224; linear estimate ~210 (frame sets differ).
- A4-2: bistable by the frozen rule at L28 (stable .421 / unstable .533), L32 (.389 / .547), L36 (.351 / .559).
  CI-robust: L28 yes (escape .54, .56), L32 yes (escape .56 only), L36 no (no escape point below I*; D(.56) = +.003, CI spans 0).
  Low-FP positions for L32/L36 come from the interpolated segment [0, .42]; existence holds by continuity (Phi(0) > 0,
  Phi(.42) < .42), position is not measured. The unstable point climbs toward I* with K, so the upper basin shrinks to the
  decoding region itself.
- A4-3: pilot-start runs stall. FER_R10 .610 / .853 / .953 (L24/28/32); MI gain R8->R10 < .006; no success is ever lost.
  L24 clause FAILS (pre-registered FER_R10 <= .5; frozen staircase said first decode at round 6). L28/L32 FER_R10 > .5 PASS.
  Plateau vs stable FP: L28 all frames +.0325 (marginal FAIL of +-.03; still-failing frames -.024), L32 -.011 PASS.
  Final MI_10 is bimodal at every L with an empty gap: stalled mode ~.40-.42, decoded mode ~.78.
- Kc by round: R1-R6 within |ln| .15 (PASS). R7-R10 INCONCLUSIVE: observed 171-172 with the conservative L20 anchor (|ln| .20)
  and 185-186 with the other bound (|ln| .12). L20 was not run beyond round 4 (design gap).
- Note: out/c1f/analysis/exit/c1e_phi.md says "frames 500-599" (hard-coded text in c1e_analyze.py); the rows are frames 1000-1299.
Interpretation (main session):
1. The mean return map is bistable from about K 224 at 6.5 dB, rho .3 (CI-robust at 224 and 256); at 288 the escape region
   below I* is gone.
2. The mean-map staircase predicts finite-round cliffs up to R6 but overstates long-run success near the fold. The L24 mean
   map is open, yet 61% of frames stall. Frames differ (realised energy), so near the fold the long-run FER is the share of
   frames whose own tunnel is closed. The mean map averages a bimodal per-frame response and sits above the median frame:
   asymptotic cliff ~172-186, below the mean-map fold ~210.
3. Bimodal end states with an empty gap fit two attractors, but frame heterogeneity alone can also produce them. Same-frame
   hysteresis is not shown.
Proposed next (not run): (i) zero-cost per-frame two-step analysis on EXIT-D rows (Ir just below vs above the unstable
point); (ii) FULL_R10 at L 16/20 to settle Kc R5-R10; (iii) injected-start multi-round runs on stalled frames (hysteresis).

## Amendment A5 — per-frame maps, same-frame start dependence, long-run Kc (2026-10-09; user said "go on" to (i)+(ii); written before any A5 row exists and before any per-frame look at EXIT-D rows)
Runs (6.5 dB, rho .3, entropy c1_map, `driver_c1i.py --arms FULL_R10`, unmodified receiver, 10 rounds):
- R10-LO: L {16, 20}, frames 0-299 (settles Kc R5-R10; same observations as c1i / A4 R10).
- R10-X: L {28, 32}, frames 1000-1299 = the EXIT-D frames (added by the main session: turns the per-frame map test from a
  population comparison into a frame-by-frame one; ~10 CPU-min).
Per-frame map (EXIT-D rows, L 28/32, report-only for 36): Phi_f(0) := mi_in1 of EXIT_none, Phi_f(I) := mi_in1 at Ir = I;
D_f(I) = Phi_f(I) - I. Escape grid G = {.42, .44, ..., .56} (all below I* = .577). Classes:
O (open) D_f > 0 on all of G; B (bistable) D_f(.56) > 0 and D_f < 0 somewhere on G; C (closed) D_f(.56) <= 0.
u_f = highest - to + crossing on G (linear). M2 = c1e_predict.staircase on the frame's own map (grid 0 + full Ir grid,
10 rounds, decoded by round R iff traj >= I*). M0 = the same rule on the mean map (contrast). Decode = ierr_r == 0.
Checks:
- A5-0 (determinism): R10-X rounds 1-2 equal EXIT_none rounds 1-2 frame by frame (cerr, ierr, ll_in); R10-LO rounds 1-4 equal
  stored c1i FULL_R4 (L 16/20). Failure voids A5-2/A5-3 (observations would differ).
- A5-1 (Kc by round): FER .5 crossing in K from FULL_R10 L 16-32 (frames 0-299; c1i L 8-12 for R1-R4). Formal: frozen
  mean-map staircase, |ln| <= .15 (A4 rule; R7-R10 expected to FAIL per A4). Prediction from the A4 bracket:
  Kc_R10 in [172, 186], i.e. FER_R10(L20) in [.02, .43].
- A5-2 (frame's own tunnel decides the long run; R10-X, same frames): decode-by-R10 rate >= .8 in class O and <= .2 in
  B u C, at L28 and L32 (a class with < 10 frames is pooled over L). M2 FER_R10 within +-.06 of observed FER_R10 at
  both L.
- A5-3 (same-frame start dependence): among R10-X frames that fail at round 10, the share with at least one injected start
  Ir in G (below I*) that decodes within 2 rounds (ierr2 == 0). Start dependence shown at an L if the Wilson lower bound
  > .10. Direction check, class B, (frame, Ir) pairs with |Ir - u_f| >= .02: the second step (mi_in2 - mi_in1; decode by
  round 2 counts as up) has the sign of D_f(Ir) in >= 80% of pairs, separately below and above u_f.
Scope: genie consistent-Gaussian starts are not real decoder states; injected horizon 2 rounds; injection noise w is
shared across Ir within a frame, so per-frame curves are smooth but class edges carry MI-estimate noise (reported via
the count of frames with > 1 sign change on G). A5-3 PASS = start-dependent outcome for one observation, i.e. two
attractors per frame under a genie start; it does not show that a real receiver state reaches the upper basin.

## A5 outcome (out/c1g/analysis/c1g.md; row md5 in out/c1g_r10lo, out/c1g_r10x; 0 error rows)
- A5-0 PASS: R10-X rounds 1-2 = EXIT_none (600 frames, 0 mismatches, ll_in diff 0); R10-LO rounds 1-4 = c1i FULL_R4 (600, 0).
- A5-1: Kc by round R1-R10 = 76.8 / 131.7 / 159.0 / 167.2 / 172.3 / 176.0 / 177.4 / 178.2 / 179.6 / 180.1. Frozen mean-map
  staircase PASS R1-R6, FAIL R7-R10 (ln +.152 to +.163; the .15 bar lies inside the R10 CI), as A4 implied. A5 prediction
  PASS: FER_R10(L20) = .313 [.263, .368]; Kc_R10 = 180.1 [176.2, 184.8] inside [172, 186].
- Classes on G: L28 O/B/C = 99/141/60, L32 42/168/90, L36 4/151/145; median u_f .542 / .542 / .548. Frames with > 1 sign
  change on G: 54 / 26 / 11 (all class B).
- A5-2 FAIL (class O clause): decode by R10 in B u C 0/201 (L28), 0/258 (L32) PASS; in O 49/99 = .495 and 12/42 = .286 (needs
  >= .8) FAIL. M2 FER_R10 .743 vs observed .837 (L28, diff -.093 [-.127, -.060]) FAIL; .913 vs .960 (L32) PASS. Frame-level
  agreement .893 / .947; M2 errors one-sided (predicts a decode that does not happen: 30 and 15 frames, vs 2 and 1).
  M0 never decodes at L28-36. Failing O frames start lower (mi_none median .385 vs .420 for decoding O frames, L28) and stall
  near .44 (mi10 median .441 L28, .438 L32): 12/50 and 11/30 below .42 (unmeasured interval), the rest where their own
  genie map lies above the diagonal.
- A5-3 PASS: among frames failing at R10, an injected start in G (below I*) decodes within 2 rounds for 176/251 = .701
  [.642, .754] (L28) and 180/288 = .625 [.568, .679] (L32). By class: O 50/50, 30/30; B 126/141, 149/168; C 0/60, 1/90.
  Direction (class B, |Ir - u_f| >= .02): below u_f .829 / .911, above .975 / .980. D_f > 0 points below u_f mostly step
  down at step 2 (up in 29/94 and 12/50).
- Report-only: R10-X FER_R10 vs A4 frames 0-299: .837 vs .853, .960 vs .953 (frame sets agree). Stalled B/C frames end within
  median .026 (L28) / .029 (L32) of their own lower crossing s_f.
Interpretation (main session):
1. Long-run cliff Kc ~ 180 [176, 185] at 6.5 dB, rho .3. Kc saturates after round 5 (172 -> 180); the mean-map fold (~210)
   overstates it by ~15%.
2. A frame whose own map is closed below I* never decodes from the pilot start (0/459). An open own map is necessary, not
   sufficient (29-49% decode): the consistent-Gaussian map runs slightly above real trajectories, which decides frames with a
   low start and a narrow tunnel.
3. Same observation, two end states: 62-70% of stalled frames decode within 2 rounds from a start below I*, while their
   pilot start stalls; frames without an escape region do not (1/150). Per-frame bistability under a genie start is shown.
   Whether a real receiver state can reach the upper basin is not shown.
4. The cliff is heterogeneity x bistability: long-run FER(K) is the share of frames whose pilot-start trajectory stays in
   its own lower basin. The mean map mixes the two basins and so misplaces the long-run cliff.

## Scope correction (2026-10-10, after review of Codex's joint finite-time closure; supersedes wording above)
- "Long-run cliff" in the A5 outcome means the 10-round cliff (Kc_R10 ~ 180); no T -> infinity claim.
- "Per-frame bistability under a genie start is shown" (A5 reading 3) is narrowed: A5 shows start dependence of the
  10-round outcome for one observation under a genie start. Asymptotic stability of the stalled state, fold conditions,
  and reachability by real receiver states are not shown. "Heterogeneity x bistability" (reading 4) reads
  "heterogeneity x start dependence".
