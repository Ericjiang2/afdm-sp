# Inner-update budget: does a longer round-1 inner loop move the cliff? (IB run)

Date 2026-10-10 (main session, Opus). User approved ("both"). Motivation: J12 showed the 20-update inner loop is
mid-transient; 40/80 updates lower the perp channel error to .64-.98 / .49-1.00 of the T = 20 value. Receiver-side lever.

## Design (FROZEN; written before any IB row exists)
- Receiver: unmodified SPg_flat FULL receiver (genie delays, flat prior, K = 8L) through
  `interventions._instrumented(..., rounds=4, iterations=T, gain_mode='joint')`. Only `iterations` changes, and it
  applies to every round. No frozen file is edited.
- Cells: 6.5 dB, rho .3, L {8, 12, 16, 20, 24} (K 64-192; covers the R1 to R4 cliffs at 77 / 132 / 159 / 167).
- Frames 0-299 (same observations as c1i FULL_R4). T in {40, 80}. T = 20 is stored (c1i FULL_R4). A T = 20 re-run on
  frames 0-29 at every L is the determinism check.
- Per frame and round r = 1..4: ierr_r, ll_in_r (I_r = 1 - ll_in_r), eps_det_r, eps_ce_r, seconds.
Checks and predictions:
- IB-0: the T = 20 re-run equals the stored c1i FULL_R4 rows exactly (cerr, ierr, dsha, ll_in, rounds 1-4).
- IB-1: round-1 channel error falls with T. Median eps_det1(40)/eps_det1(20) in [.80, .97] at every L (J12 total-error
  ratios at 6.5/8 dB: .78-.96), and the median for T = 80 is no larger than for T = 40.
- IB-2: link consistency. Cell mean of I_1(T) - I_1(20) against the LMMSE-link prediction from each frame's own
  eps_det1 change (q = eta a (E_real - e)/(n + e), eta of the c1_map cell): |pred - obs| <= .01 in >= 4/5 cells.
- IB-3 (the practical question; the definition is frozen, the outcome is not): Kc_R(T) for R = 1..4, the FER .5 crossing
  linear in K, with a frame-bootstrap CI (B = 2000). "The inner budget moves the cliff" if, at some R,
  Kc_R(80) / Kc_R(20) - 1 >= .05 with the bootstrap CI of the ratio excluding 1.
  Expectation stated before the run: the R1 shift is small (<= 6%). Rounds 2-4 have no prediction.
- Report-only: FER and I by round and T; cost per frame (seconds) by T; round-4 eps_det at T = 80 vs T = 20.
Cost estimate: about 16 CPU-h (T = 40 and 80, 5 L x 300 frames x 4 rounds), about 10-15 min on <= 90 shards.

## Outcome (2026-10-10; `out/c1ib/analysis/ib.md`; 3000 + 150 rows, 0 error rows; commit 52df712c)
- IB-0 PASS: T = 20 re-run equals stored c1i FULL_R4 exactly (150 cells, rounds 1-4, incl. eps).
- IB-1 FAIL (second clause): median eps_det1(40)/eps_det1(20) = .895-.936, inside [.80, .97] at every L. But T = 80 is
  not below T = 40 at 4/5 L (.890-.938): the gain saturates by ~40 updates.
- IB-2 FAIL: the observed I_1 gain exceeds the LMMSE-link prediction by ~.01 at L >= 16 (T = 40: 2/5 cells within
  .01; T = 80: 1/5). At L8, T = 80 lowers I_1 (-.019) while FER_1 improves (.407 -> .347), which points to an LLR
  calibration change.
- IB-3: the inner budget MOVES THE CLIFF at every round (paired frame-bootstrap CI, lower ends 1.07-1.14):

| round | Kc at T = 20 | Kc at T = 40 | ratio [95% CI] | Kc at T = 80 | ratio [95% CI] |
|---|---|---|---|---|---|
| R1 | 76.8 | 94.1 | 1.225 [1.142, 1.350] | 92.3 | 1.202 [1.125, 1.326] |
| R2 | 131.7 | 152.2 | 1.156 [1.108, 1.237] | 154.5 | 1.173 [1.118, 1.260] |
| R3 | 159.0 | 175.1 | 1.101 [1.072, 1.140] | 175.3 | 1.103 [1.071, 1.143] |
| R4 | 167.2 | 187.5 | 1.121 [1.090, 1.167] | 189.8 | 1.135 [1.098, 1.177] (upper CI censored at 192) |

  The stated expectation (R1 shift <= 6%) was wrong: +20%.
- Cost per row (4 rounds): T = 40 is 1.3-1.7x and T = 80 is 2.4-3.0x the T = 20 time, with a load caveat.
Reading (main session): with the default 20 inner updates, the receiver stops its inner loop mid-transient. About 40
updates per round recover 10-22% in K at every round, at about 1.5x the compute. Same frames: R4 at T = 40 (187.5
[182.4, 192.0]) at least matches R10 at T = 20 (180.1 [176.2, 184.8], A5), at about 60% of its inner-update compute.
Scope: one condition (6.5 dB, rho .3), frames 0-299, K <= 192; replication and a finer T sweep are needed before any
claim.

## IB2: replication, T sweep, 10 rounds, compute frontier (FROZEN 2026-10-10; user approved; before any IB2 row exists)
Receiver unchanged, as in IB (only `iterations` and `rounds` vary). Driver: driver_c1ib.py extended or a sibling.
Runs:
- REP (replication; rounds 4, T in {20, 40}, frames 0-199):
  6.5 dB rho .2 L {8,12,16,20,24,28}; 8 dB rho .2 L {12,16,20,24,28,32,36}; 8 dB rho .3 L {12,...,36};
  8 dB rho .5 L {8,12,...,32}; 9.5 dB rho .3 L {16,20,...,40}.
- SWEEP (6.5 dB rho .3; rounds 4; T in {30, 50}; L {8,...,24}; frames 0-299). T = 20/40 come from IB.
- R10 (6.5 dB rho .3; rounds 10; T = 40; L {16,20,24,28,32}; frames 0-299). T = 20 comes from A4 c1f_r10
  (L24-32) and A5 c1g_r10lo (L16/20), same frames.
Checks and predictions:
- IB2-0: T = 20 rounds 1-2 equal the stored SPg_flat rows of c1_boot / c1_map for the same frames and cells (cerr, ierr,
  ll_in), where they exist; 6.5 dB rho .2 and 9.5 dB have no stored rows (V3 used frames 3000+), so these are checked
  for internal T = 20 determinism on 10 frames only.
- IB2-1 (replication): at each REP condition, Kc_R(40)/Kc_R(20) - 1 >= .05 with paired frame-bootstrap CI lower end > 1
  at R1 and at R2. Pass if this holds in >= 4/5 conditions. Censored crossings count as bounds (as in IB).
- IB2-2 (saturation): Kc_R(30) lies between Kc_R(20) and Kc_R(40) (point estimates) at every R = 1..4, and the paired
  CI of Kc_R(50)/Kc_R(40) contains 1 at every R.
- IB2-3 (10 rounds): Kc_R10(40)/Kc_R10(20) has a paired CI with lower end > 1. Stated expectation: +5% to +15%.
- IB2-4 (compute frontier, report-only, no prediction): at 6.5 dB rho .3, the highest Kc reached at equal measured
  compute (mean seconds per frame summed over rounds, and inner-update count R x T), over all (R, T) with
  R = 1..10 and T in {20, 40} (plus R = 1..4 at T 30/50). Also, at equal inner-update budget, whether
  (R, 40) beats (2R, 20).
Report-only: FER and I by round, T and condition; eps_det ratios; the L8-type I_1 drop at large T (calibration).
Shard budget: <= 100 concurrent shards, keeping >= 16 cores free; run the three groups in sequence if needed.
IB2 amendment (2026-10-10, after a 2-4-frame smoke, before the full run; disclosed): at 6.5 dB rho .2 and 8 dB rho .5
the R1 cliff lies at or below L8 (smoke FER_1 ~ .5 at L8). The R1 clause of IB2-1 could not pass by construction
(censored, ratio pinned near 1). Add L4 (K 32) to both REP grids; nothing else changes. Censored crossings stay
bounds, and a censored ratio of ~1 is reported as uninformative, not as a null.

## IB2 outcome (2026-10-10; `out/c1ib2/analysis/ib2.md`; 19,400 new rows, 0 error rows; commit e94d0464)
- IB2-0 PASS: R4T20 equals stored c1_boot rows (2800 pairs); c1i / c1f_r10 / c1g_r10lo equal c1_map (3000 pairs);
  internal T = 20 determinism (220 cells); 10-round rounds 1-4 equal the 4-round rows (1800 pairs).
- IB2-1 PASS 5/5. Kc_R(40)/Kc_R(20), paired CIs all above 1:

| condition | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| 6.5 dB rho .2 | 1.40 | 1.21 | 1.15 | 1.18 |
| 8 dB rho .2 | 1.34 | 1.20 | 1.15 | 1.14 |
| 8 dB rho .3 | 1.26 | 1.19 | 1.17 | 1.15 |
| 8 dB rho .5 | 1.14 | 1.08 | 1.14 | 1.14 |
| 9.5 dB rho .3 | 1.27 | 1.19 | 1.16 | >= 1.11 (censored at K 320) |
| 6.5 dB rho .3 (IB) | 1.23 | 1.16 | 1.10 | 1.12 |

- IB2-2 PASS: T = 30 captures most of the gain (R1 1.19 of 1.23); T50/T40 = 1.000-1.008, CI contains 1 at every round.
- IB2-3 PASS: the 10-round cliff moves from 180.1 to 213.6, ratio 1.186 [1.153, 1.221]. That is above the stated
  expectation (+5-15%). The ratio grows with rounds (R5 1.15 to R10 1.19): at T = 20, rounds 5-10 add 8 in K; at
  T = 40 they add 16.
- IB2-4 compute frontier (6.5 dB rho .3; receiver-clock seconds from a quiet 10-shard reference run; ranking, not
  absolute seconds):
  - The default schedule R10/T20 (Kc 180.1 at 1.80 s) is dominated. R4/T30 reaches 185.4 at 0.99 s (55% of the
    compute), and R5/T40 reaches 197.7 at 1.50 s.
  - At equal inner-update budget, (R, 40)/(2R, 20) = .71 / .91 / .995 / 1.05 / 1.10 for R = 1..5. Extra rounds win
    for budgets up to ~80 updates; deeper inner loops win from ~120 updates on.
- Report-only: the eps_det gains concentrate near each round's cliff (median eps_det_r ratios down to .48-.53). An I_1
  drop with no FER loss appears only at the smallest K (L4/L8): a calibration effect at tiny channel error.
Reading (main session):
1. Replicated in all 6 conditions: the intra-round joint-update budget is a first-order determinant of the
   SP-AFDM cliff, +8-40% in K by round at T = 40, saturating near T = 30-40.
2. The allocation answer depends on the budget. Few rounds should spend compute on rounds; beyond ~4 rounds, extra
   rounds stall (the fold/tunnel limit, A4/A5) and only a deeper inner loop moves the cliff. That is the return-map
   picture: rounds iterate the map; the inner budget raises it.
3. The equal-compute result is evidence for Trans option (b) (R4/T30 beats R10/T20 at ~55% compute) and for a
   design rule (c). Open before any claim: a targeted prior-art check on iteration scheduling (C1-C07), a
   map-based prediction of the shift (return map measured at T = 40), and the frontier at a second condition.
