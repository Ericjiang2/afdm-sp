# Results: headroom ladder + pilot-fraction sweep (2026-10-08)

Code: `experiments/headroom_ladder_20261008/` (driver/arms/analyze; commit 767d3764 before run).
Outputs (small, local+remote): `experiments/headroom_ladder_20261008/out/{e_ladder,e_rho}/`
(ANALYSIS.md, analysis.json, results.json, summary.md, fer_curves.png, logs). Row shards remote only,
md5 in `REMOTE_ROWS_MD5.txt`. World: physical G1 CPP channel, P=8, N=1024, LDPC (3,6) n2048,
count-blind production receiver B = F0+TF+CSTATE20. Frame-block bootstrap B=20000.

## E-ladder (rho .5, existing random prospective population, 3x1024 frames)
A0 bit-matches stored prospective decisions 3072/3072.
- B -> true H (A3): 0.31 dB [0.17, 0.48] @FER 1e-2.
- Local Doppler step (A1->A2): 0.13 [-0.02, 0.28] dB @1e-2. Genie geometry+gains step (A2->A3) 0.27 [0.14, 0.39].
- Failure predictor: same_delay_underfit AUC .65 pooled / .76 within-SNR; pass-1 E_miss .55 (n.s.).

## E-rho (fresh paired population: 2000 frames x rho{.2,.3,.4,.5} x SNR 4.5..8.0; channel/bits/noise shared)
Production B crossing SNR (dB):

| rho | FER 1e-1 | FER 1e-2 |
|---|---|---|
| .2 | < 4.5 | 6.07 [5.61, 7.09] (error floor) |
| .3 | 4.61 [4.58, 4.64] | 5.40 [5.22, 5.72] |
| .4 | 5.17 [5.14, 5.20] | 5.82 [5.69, 5.96] |
| .5 | 5.86 [5.83, 5.90] | 6.59 [6.42, 6.81] |

- **rho .5 -> .3: -1.26 dB [-1.28, -1.23] @1e-1; -1.19 dB [-1.34, -0.98] @1e-2.** Pre-registered rho rule (>= .3 dB, CI excl 0): PASS.
- P1 (interior optimum): PASS. argmin rho = .3 at 5.0-6.0 dB (.4 at 6.5/7.5, ties at high SNR); rho .2 best only at FER ~1e-1 / 4.5 dB, then floors (F0 FER .032 at 8 dB) -> optimum is FER-target dependent.
- P2 (PCSI shift = 10log10((1-r1)/(1-r2))): PASS. .5->.3 obs -1.48 vs -1.46; .5->.4 -0.82 vs -0.79 (residual CI within .15 dB).
- P3 (per-frame pass-1 weak-path threshold explains failures): FAIL mostly. E_miss AUC .56-.58 per rho, within-SNR < .5 at rho .3/.4. Receiver missed-energy predicts only at rho .2 (AUC .73). same_delay_underfit within-SNR AUC .64-.77 at all rho.
- B gap to true H grows as rho falls (@1e-2): .41 (.5), .45 (.4), .69 (.3) dB.
- Local Doppler step A1->A2 @1e-1: .07 (.5), .03 (.4), -.02 (.3) dB -> negligible (T1 confirmed).
- A2 (genie geometry, TF-only, all 8 slots forced) is ill-conditioned at low rho (1e-2 crossing 7.27 dB at rho .3): not a valid bound; ignore as ladder rung.
- PAPR cost: mean 7.99/8.22/8.41/8.55 dB, p99 9.65/9.95/10.18/10.34 dB for rho .5/.4/.3/.2.

## Route decision
1. Local Doppler-uncertainty / pair-covariance / collapsed-VB line: CLOSED for this regime (<= .13 dB, CI touches 0; total B->PCSI headroom only .14-.41 dB at rho .5).
2. Pilot fraction is the first-order lever: ~1.2 dB at equal total power for the unchanged production receiver.
   Theory status: data-power term exact (P2); interior optimum + low-rho floor observed (P1); per-frame threshold
   mechanism NOT confirmed (P3) -> the low-rho floor/optimum mechanism is open (candidate: same-delay multiplicity
   resolution + acquisition at very low rho).
3. Limits: one channel model (P=8 PDP), N=1024 only (frozen guard), receiver constants tuned at rho .5 (low-rho
   results likely conservative), equal total power (PAPR +~.4-.5 dB), sigma2 known. Prior art: SP-OTFS SINR-optimal
   pilot power ~.30-.36 (Mishra et al., TWC 2022) -> rho ~.3 optimum is consistent with, not novel vs, that line.

## Open decisions for user
- Adopt rho as a design variable in the paper (changes production reference .5)? Requires user decision.
- If yes: next = (a) mechanism of low-rho floor (multiplicity/acquisition), (b) N/PDP scaling of rho*, (c) receiver retune at low rho.

## Generator defect found (2026-10-08, affects paper channel law)
`run_classical_baselines_python.py:76-78` computes `max_delay_idx_bar_supported` with Ts=125 us (fs=8k); `loop9_cache_features.py:64-67`
then sets fs=16 kHz / Ts=62.5 us without recomputing it -> cap = 54 samples (3.375 ms) instead of 107. `afdm_env.py:346-354`:
rejection sampling (32 tries) then `np.minimum(idx_bar, 54)` fallback. Measured on E-rho population: 417/2000 = 20.8% frames
have >= 2 paths stacked at the capped delay (l ~ 51); accepted frames are biased to delay span <= 3.4 ms. Doppler law
v ~ |N(2, .5^2)| -> all paths within ~1.0 +- .26 bins, so stacked paths are unresolvable doublets.
B failure enrichment in clip-stacked frames only ~1.4-1.5x (rho .3: 3.4% vs 2.2% pooled SNR); >= 70% of B failures are in
non-clip frames -> artifact contributes, does not explain the floor. Paper's G0/G1 results inherit this law (disclose or fix).
