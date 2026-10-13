# Results: SP-AFDM under same-delay Doppler clusters (2026-10-08)

Focus (user): primary contribution = NEW PROBLEM + explanatory MODEL; method = enabler.
Code/outputs: experiments/headroom_ladder_20261008/ (out/f1_clustered, f2_order, m1_dpss, f3_diversity, m2_test,
m2_test_pb16). Commits: a5e51ad0 (F1), 58c393bb (F2), 8aaa935d (M1), 809019fc (F3), 9b3e226c (before M2), this one (after M2).
Channel: universal clustered fractional-Doppler law, 4 taps (exp PDP), rays/tap 1+Poisson(lambda-1), nu = 2cos(theta),
angular spread 5deg (N*a) / 20deg (N*b) / Jakes (J*); D1 = 1 ray/tap; S16 = 16 separable paths. N=1024, rho .5, QPSK,
LDPC (3,6) n2048, physical CPP operator. F1/F2/M1: realized per-frame power normalization; F3/M2: expected-power law.

## Problem (F1, F2)
- Paper's production SP receiver B (one slot per distinct delay, cap 8) collapses on clustered channels: FER @9 dB
  B / true H = .873 / .002 (Jakes, F1). Under expected law B never reaches FER 1e-1 by 11 dB on 20deg/Jakes (M2).
- Strongest existing parametric receiver PS (same-delay slots, cap 8): gap to true H @1e-1 .58 (20deg), 2.89 (Jakes-4),
  > 3.48 dB (Jakes-8) (M2). Cap 16 without stopping rule (PB16): .80 / .58 dB at 3.4x PS cost; more slots != better.

## Model (F2, M1, F3)
- Effective order: predicted per-tap order from Doppler-covariance eigenvalues (gamma_k > 1) 2.0/2.7/3.6 vs free-frequency
  oracle needed ~2/3/3-4 (N4a/N4b/J4) (F2). DPSS basis needs 1/3/4/8 (cost ~ min(rays, 2W+1)) (M1).
- Diversity (F3, true H, expected law): coded slopes D1 3.3, 5deg 3.7, 20deg 4.0 vs Jakes-4 6.6, Jakes-8 6.8, S16 7.1.
  Intra-tap Doppler spread is real AFDM diversity (4 Jakes taps ~ 16 separable paths); sub-resolution clusters add ~none.
  Group-level only; slope not proportional to hard P_eff count.
- Conditioning: same-delay doublet Gram cond ~ delta^-2 (486 at delta .05) vs confluent/DPSS basis bounded (3.29).
- Punchline: the channels richest in AFDM diversity are exactly where parametric SP receivers fail.

## Method enabler (M2, 1000 test frames/config, SNR 6-11, dev-tuned on disjoint frames, frozen config 8f3b0486)
DPSS-BEM per acquired tap (W 2.5 bins, D 8) inside the SP joint gain/data estimator with Slepian-eigenvalue prior.
Gap to true H @1e-1 (dB): D1 .41, N4a .46, N4b .36, J4 .46, J8 .46 (M_full); M_adapt .41/.41/.29/.53/.54.
Cost .75 s/frame vs PS 1.6-1.8, B .8-1.1, PB16 5.6.
Pre-registered gates: S1 FAIL (J4 .53 > .3), S2 FAIL (D1 M_adapt - B = .17 > .1), S3 FAIL (N4b .29 < .3; J4 2.36 pass),
S4 FAIL (adaptivity .01-.05 dB). -> adaptivity claim dropped; method = SP-AFDM DPSS-BEM with Slepian prior (combination).
Post-hoc observation (not pre-registered): M_full worst-case gap over all 5 classes .46 dB vs B/PS > 3.48 dB.
Residual .3-.4 dB consistent with variance law 10log10(1 + 2*64/2048) = .26 dB (64 complex coefficients).

## Limits
One delay/PDP law (4 taps), nu_max 2 bins, N 1024, rho .5, sigma2 known, TF detector (not ML), 2 coded rounds. Closest
prior art: Benzine-Bemani-Ksairi-Slock arXiv 2504.13762 (DPSS-BEM per DD grid point, embedded pilots, AFDM compared) ->
method novelty minimal; problem + diversity/estimation duality + receiver-failure evidence are the contribution.
Paper's existing generator has a stale delay-cap defect (../10-08-headroom-ladder/RESULTS.md).

## C1 bootstrapping DoF budget (c1_boot 0b1088b8; c1_map + c1_tdl 35225b4c; detail research/distinction-v3.md)
- SP loop-start cliff with universal first-pass SINR threshold g ~ 1.37; K* = b/((1-b)s) = kappa N; in-sample ~12%,
  out-of-sample (5/6.5 dB) within CI. Richness U-shape confirmed at 6.5 dB (rho .3), not at 5 dB.
- 3GPP TDL-A/B/C at N 1024, nu_max 2 bins: genie-support SP below cliff (K/K* .29-.91) but .11-.39 FER above true H at
  8 dB; count-blind SP acquisition-limited; production B FER >= .96 everywhere.
- Untested: K* proportional to N (N 256 predicted past cliff for TDL); g from first principles (EXIT).

## C1 mechanism closure and round-1 loop law (2026-10-09; research/c1-scalar-closure.md, research/c1-round1-loop-theory.md)
- T2 1-D error closure (frozen 1dfb182c) FAILED; dropped. Code threshold universal in MI: I* = .577 (D2, ac08735a).
- Interventions (bdad1a06): round budget moves the cliff; channel init forgotten; frozen channel fails.
- EXIT staircase from measured Phi_K (frozen 9473a774): Kc within |ln| .07 at 6.5 dB R1-R4 and 8 dB R1-R2 (6/6; 6b3ebda9).
  Fold near K 224 at 6.5 dB rho .3; bistability beyond the fold not established.
- Round-1 law (2d0a2f90): e* = e_ind/(1-c)^2, c = kappa beta d, link q = eta a (1-e)/(n+e); bracket kappa in [0,1] holds in
  56/56 cells; kappa = w post hoc (I_1 within .036 on 12 points). V1-V5 spec + frozen V3 predictions; runs pending approval.
- Draft card res-20261009-01; overview https://claude.ai/artifact/DRksCUG1sNMpKVBWi61prv (private).
- A4 fold run: mean map closed with CI at K 224/256/288, bistable (CI-robust at 224/256); 10-round FER .61/.85/.95 at
  K 192/224/256, bimodal end states; mean-map staircase right to R6, optimistic for long runs near the fold (L24 clause failed).
- A5 (per-frame maps + R10 at L16/20 and on the EXIT frames): Kc_R10 = 180 [176, 185], saturating after R5; frames with a
  closed own map never decode (0/459), open ones decode 29-49%; 62-70% of stalled frames decode within 2 rounds from an
  injected start below I* (start dependence under a genie start; stability not shown). A5-2 failed on the class-O clause.
- Round-1 law V1/V3: V1 fails (LMMSE link closer than T2 in 33/56 < .75; LMMSE low by .016, T2 high by .020).
  V3 blind 20 cells: I_1 within .042 (20/20), bracket 20/20, e* within ln .3 16/20 (biased high), Kc_R1 within
  ln .25 in 3/3 groups by the section-5 definition (-.247 at 6.5 dB rho .2, no margin). Codex derivation reviewed.
- V2: refit law holds (P2a 6/6); self-absorption mechanism rejected (P2b-d 0/6: probe gain .51-.67 would give 4-9x
  excess, observed 1.2-1.7x vs matched independent errors). Effective kappa .21-.56, falls with rho, ~.7 w. The law
  is a calibrated predictor with one effective constant, not a derived mechanism.
- Joint-FP theory round 1 (J run, 10 cells): noise absorption by the soft symbols offsets most of the image feedback
  (magnitude right: closed form with the reported Stein divergence within ln .2 in 7/10; dense-AMP absorption rejected
  10/10). Fixed-point premise fails (ridge identity off 1.4-7%, probe slopes overstate realised gains, phase gain
  ~.9); Q1/Q2/Q3/Q5 fail. Codex eqs 12-20 verified at N = 1024. Hand-off to Codex written.
- J12 (Codex J12 split, 10 cells): the excess is mainly the structure of the receiver's own symbol errors (D_reg
  +.29 to +.62 dominates in 9/10; joint-vs-plain D_alg -.06 to -.27) and D_reg carries the rho trend. Round-1 output is
  mid-transient: 40/80 inner updates lower the perp channel error to .64-.98 / .49-1.00 of the T = 20 value.
- Round 2 (R2, fresh frames): J12 split replicates (9/10). The scalar component model fails (P2'-P5'); exact
  attribution: image +1.0 to +1.6 against intrinsic -.3 to -1.2, absorption -.05 to -.45, design +.12 to +.30. The
  kappa-mechanism derivation stops here.
- IB (inner budget, 6.5 dB rho .3, frames 0-299): 40 inner updates per round instead of 20 move the cliff at every
  round: Kc x1.23 (R1), 1.16 (R2), 1.10 (R3), 1.12 (R4), CIs exclude 1; 80 adds nothing; ~1.5x compute. R4 at 40
  updates (187.5) at least matches R10 at 20 updates (180.1).
- IB2: replicated in 5 more conditions (Kc x1.08-1.40 by round at T = 40; all CIs > 1); saturates at T 30-40;
  10-round cliff 180 -> 214; R10/T20 dominated by R4/T30 at ~55% compute. Draft card res-20261010-01.
