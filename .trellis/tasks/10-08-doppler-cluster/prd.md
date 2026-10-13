# SP-AFDM under same-delay Doppler clusters: effective-order receiver

## Goal (paper-level)
Elevate the paper from "structured SP-AFDM receiver" to a new problem: in universal multipath fractional-Doppler
channels, several rays share a delay bin with sub-resolution Doppler spread. Intra-tap Doppler spread is AFDM's
diversity source but breaks fixed-order parametric estimators. Target contributions:
1. Problem: characterize this regime (measured: res F1, `../10-08-headroom-ladder/`).
2. Model/theory: SNR-dependent effective order P_eff (per-tap Doppler-Gram rank at noise tolerance) governing
   (a) diversity, (b) estimation cost, (c) misfit floor of fixed-order receivers; conditioning of doublet vs confluent
   bases (cond ~ delta^-2 vs bounded).
3. Method: SP data-aided turbo receiver estimating each tap in an order-adaptive subspace (centroid + confluent/DPSS or
   1-bin sub-path grid), dimension chosen from spread x T and SNR.

## Focus decision (user, 2026-10-08)
One primary contribution, high level: NEW PROBLEM + explanatory MODEL (P_eff: intra-tap Doppler spread is both the
diversity source and the estimation burden; fixed-order parametric SP-AFDM receivers fail exactly there).
Method = enabler only (show solvable near true-H at reasonable cost); combination-level acceptable, no method-novelty
claim. Central evidence: F1/F2 (problem), F3 diversity-vs-P_eff and order prediction (model), M2 (solvability).
M2 gate S4 (adaptivity) non-critical.

## Evidence so far
- F1 (commit a5e51ad0): 4 taps, rays/tap 1+Poisson(lambda-1), nu = 2cos(theta). FER @9 dB production B / true H:
  discrete 0/0; 5deg .123/.075; 20deg .365/.034; Jakes .873/.002. B uses one slot per delay (max 8).
- Literature: DPSS-BEM per DD grid point for sub-paths (Benzine, Bemani, Ksairi, Slock, arXiv 2504.13762) = closest
  prior art (embedded pilot CS, no SP, no conditioning/floor theory). Wideband AFDM I/O = prior art (arXiv 2507.03537).

## Next (F2, decisive before method build)
Arms on configs D1, N4a, N4b, J4: B; strongest existing parametric with multiple same-delay slots (keep_slots/F1);
oracle per-tap D-exponential 1-bin-grid fits D in {1,2,3,5} with fixed-H TF detection; true H.
Questions: (a) does a strong parametric receiver close the gap (=> B design limit only)? (b) what D suffices (=> P_eff)?

## Acceptance (this task)
- [ ] F2 results with CIs; route decision (method worth building or not).
- [ ] If yes: estimated (non-oracle) order-adaptive SP receiver vs B, strong parametric, on-grid DPSS-BEM baseline
      (Benzine-style, SP-adapted), true H; coded FER + cost.
- [ ] Theory note: P_eff definition, diversity link, conditioning, floor formula; checked numerically.

## Constraints
Remote rules per project CLAUDE.md; frozen modules untouched; new code in experiments/headroom_ladder_20261008/ or a
sibling dir; commit before/after runs; STATE.md only with user approval.
