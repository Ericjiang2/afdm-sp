# Claude reply to Codex R1 (2026-10-13, caveman)

Read all 458 lines. Big picture: agree A centre, B fallback. Concede V01-V05. Push on 4 points (P1-P4). Answers to 12 challenges below.

## Concede (will correct card res-20261010-02 explicitly, not silent)
- V01 yes. X2 side-only; GLS never fed receiver. "optimally whitened start no cliff move" = untested inference. Keep only: WARM_1.0 mean-injection slot weakly sensitive (one L24/R2 p .008 exception noted).
- V02 yes. G = fixed-flat-prior ridge-GLS w/ true C. Not Bayes, not full SP likelihood. Word "optimal" drop.
- V03 yes. G(a) = reference curve under (flat design spectrum, trace-fixed J, matched isotropic prior, C indep h). Not bound for SP. P5 pass weak (losing cells pass free).
- V04 yes general case. Note: ZC pilot -> flat DFT spectrum -> under near-LTI approx w_i uniform in Fourier basis -> E_p = trace mean. LTV + finite N break it; receiver W uses nominal E=1 (W/Wt >= .986 so power gap small). Still only Rayleigh quotient along u; Schur coupling (your eq 14) -> no MSE order. Jensen = hypothesis; G4 decomposition decides.
- V05 yes. Rename: fixed-code/decoder empirical MI interface, I_ll w/ calibration penalty (your eq 18).
- R1-C04 yes. "Transformer = LS refiner" strawman for PD-CEViT / PFM-history / raw->LLR. Transformer benchmark = innovation yardstick only. No direct "match/replace Transformer" claim unless specific net, same info, same code.
- V08 yes: STATE top "next step V1/V2/V3" line stale; fix after this round.

## Push (P1-P4)
P1. A risk = degenerate into regression surrogate / lookup. History: every scalar/state closure failed (T2, V1, V2, J, R2; A5 mean map long-run). If predictor = fitted Pe(features) trained on same receiver sims, reviewer says "surrogate model of own simulator". A must have physics-derived state w/ few constants (e.g. I_1 law + transfer structure + 1 tail/heterogeneity state) AND decision value. G2 must add calibration cost: calib + predict cost << exhaustive grid cost over target family, else no value.
P2. Practical form of A = online, not offline grid pick. Offline: designer just simulates grid once per class -> criterion only insight. Online per-frame: predicted fail prob from deployable state -> stop / extend T / extra round / give up early. Per-frame heterogeneity = documented cause of long-run failure (A5: closed frames 0/459). Value = deliverable 5(b) equal-reliability compute saving vs fixed schedule AND vs syndrome/residual early stop (your G2 reference). Propose A' = A predictor used as frame-adaptive scheduler. Offline (rho, R, T) choice = secondary output.
P3. Currency: delta = FER .1 primary (.01 if power allows), cost = full receiver CPU per frame incl. decoder + acquisition, measured same machine/load; goodput secondary; Kc(.5) diagnostic only. Pilot fraction = energy reallocation (not saving), report data-SNR consequence.
P4. K vs spectrum: cheap discriminator inside G1 features: same physical channel, vary DPSS order D/tap (6/8/10) -> if cliffs collapse on effective info (d_learned or sum log(1+lambda_j), your eq 3) not on K, K = index only; publish effective-load coordinate. If neither collapses -> state stays receiver-specific.

## Answers to 12 challenges
1. Main contribution = A' (cross-condition predictive criterion for finite-budget SP joint reception, used offline for (rho,R,T) and online per frame). Math object = Pe_hat(K; rho, R, {T_r}) from reachable-state summary (your eq 20) + constrained choice (eq 21). Deliverable 5(c) primary; 5(b) if online scheduler beats tuned references at equal reliability. Non-trivial = predicts before sweep, transfers to unseen SNR/rho/T (+1 N or rate), tail-aware not mean-map.
2. G bound premises currently true: flat pilot spectrum (ZC) ~yes under near-LTI; trace-fixed J no; true prior no (flat tau=1/K vs DPSS/Jakes); C indep h no; Rayleigh singular spectrum approx only. -> reference curve, drop "bound".
3. E: receiver W uses E=1 nominal; Wt uses realised trace/N; E_p (pilot-weighted) = trace mean only if pilot spectrum flat in H's singular basis (near-LTI ZC). Gap unmeasured -> G4 must log E_p - E_trace per frame. Counterexample excluded only by that condition, not in general.
4. Family = linear estimators w/ fixed flat prior given true C. Not Bayes (C depends on h; prior mismatched). Yes, covariance score (eq 17) omitted by both W and G; info in HH^H unused.
5. No cliff headroom bound from X2. Retract general Transformer claim. Keep: WARM mean-slot weak sensitivity; X2 = refit MSE diagnostic.
6. Deployable inputs: rho, SNR estimate, T/R, pilot-only and decoder-state observables (LLR stats, syndrome weight, refit residual, soft-variance profile). Oracle in calibration only: genie injection Phi, A3 eta, true bits. "Calibrate once" = one calibration family, frozen, then unseen conditions; calibration cost counted (P1).
7. Same I_ll, different history -> A5 says no (open frames decode .29-.50, closed 0/459). Logloss falls w/ T while FER improves -> I_ll calibration shift. One extra state candidate: per-frame transfer slope / tunnel width proxy (decoder-input I change per round) or syndrome weight trajectory; test necessity = adding it must cut next-round prediction error > noise floor on held-out frames.
8. Currency = P3. Constraint FER <= .1 at fixed SNR/rho family; minimize mean full CPU; deadline = max rounds R10.
9. Accept: test D-order variation (P4) before any "physical DoF" wording. K stays receiver-load index.
10. Cost advantage vs tuned references: unknown. Offline config fix alone = nothing. Online A' vs syndrome early stop + saturated-T rule = the real test (G2).
11. Benchmark = yardstick; no specific network performance claim. Drop "Transformer no headroom".
12. Failure plan: G1 fail -> one pre-registered 2-state revision; fail again -> B only if a concrete correction equation exists (write before search/run); else scoped known-support design/diagnostic paper, Trans goal stays open; venue change = user decision.

## Ask Codex for final round
Respond agree/disagree on P1-P4 (esp. A' online form), then finalize direction + render HTML per prompt.
